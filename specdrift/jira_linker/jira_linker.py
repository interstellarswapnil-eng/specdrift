from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any


class JiraLinkerError(RuntimeError):
	pass


def _parse_dt(value: str | None) -> datetime | None:
	if not value or not isinstance(value, str):
		return None
	v = value.strip()
	if not v:
		return None
	# Common Jira format: 2026-03-05T10:20:34.740+0000
	try:
		if v.endswith("Z"):
			return datetime.fromisoformat(v.replace("Z", "+00:00"))
		return datetime.fromisoformat(v)
	except ValueError:
		pass
	for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
		try:
			return datetime.strptime(v, fmt)
		except ValueError:
			continue
	# Date-only (e.g., metadata last-reviewed: 2025-03-01)
	try:
		return datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=timezone.utc)
	except ValueError:
		return None


def _issue_key(issue: Any) -> str | None:
	if isinstance(issue, dict):
		return issue.get("key")
	return getattr(issue, "key", None)


def _issue_fields(issue: Any) -> dict[str, Any]:
	if isinstance(issue, dict):
		return issue.get("fields", {})	
	fields = getattr(issue, "fields", None)
	if fields is None:
		return {}
	# jira library provides attribute-like access, but also dict-ish.
	if isinstance(fields, dict):
		return fields
	# Best effort conversion for tests / unknown shapes
	return fields.__dict__ if hasattr(fields, "__dict__") else {}


def _issue_status_name(issue: Any) -> str | None:
	fields = _issue_fields(issue)
	status = fields.get("status")
	if isinstance(status, dict):
		return status.get("name")	
	return getattr(status, "name", None)


def _issue_updated(issue: Any) -> datetime | None:
	fields = _issue_fields(issue)
	updated = fields.get("updated")
	return _parse_dt(updated)


def _section_dict(section: Any) -> dict[str, Any]:
	if is_dataclass(section):
		return asdict(section)
	if isinstance(section, dict):
		return section
	# Fallback for Section dataclass-like objects
	return {
		"id": getattr(section, "id", None),
		"metadata": getattr(section, "metadata", {}) or {},
		"linked_jira_ids": getattr(section, "linked_jira_ids", []) or [],
		"status": getattr(section, "status", None),
		"changed_at": getattr(section, "changed_at", None),
	}


def fetch_project_issues(project_key: str) -> list[Any]:
	"""Pull epics and stories from Jira.

	Uses env vars:
	- JIRA_SERVER
	- JIRA_EMAIL
	- JIRA_TOKEN
	"""
	server = os.environ.get("JIRA_SERVER")
	email = os.environ.get("JIRA_EMAIL")
	token = os.environ.get("JIRA_TOKEN")
	if not server or not email or not token:
		raise JiraLinkerError(
			"Missing Jira credentials. Set JIRA_SERVER, JIRA_EMAIL, and JIRA_TOKEN."
		)

	try:
		from jira import JIRA  # type: ignore
	except Exception as e:  # pragma: no cover
		raise JiraLinkerError(
			"Jira dependency not installed. Install optional deps: pip install 'specdrift[engine]'"
		) from e

	jira = JIRA(server=server, basic_auth=(email, token))

	jql = f"project = {project_key} ORDER BY updated DESC"
	start_at = 0
	max_results = 100
	issues: list[Any] = []
	while True:
		batch = jira.search_issues(jql, startAt=start_at, maxResults=max_results)
		issues.extend(list(batch))
		if len(batch) < max_results:
			break
		start_at += max_results

	return issues


def match_to_sections(issues: list[Any], sections: list[Any]) -> dict[str, list[Any]]:
	"""Map issues to sections via the section metadata `jira:` field."""
	issue_by_key: dict[str, Any] = {}
	for issue in issues:
		k = _issue_key(issue)
		if k:
			issue_by_key[k] = issue

	mapping: dict[str, list[Any]] = {}
	for section in sections:
		s = _section_dict(section)
		sec_id = s.get("id")
		if not sec_id:
			continue
		jira_ids = s.get("linked_jira_ids")
		if not jira_ids:
			# also allow raw metadata form
			meta = s.get("metadata", {}) or {}
			jira_raw = meta.get("jira")
			if isinstance(jira_raw, str) and jira_raw.strip():
				jira_ids = [j.strip() for j in jira_raw.replace(",", " ").split() if j.strip()]
			else:
				jira_ids = []

		linked = [issue_by_key[j] for j in jira_ids if j in issue_by_key]
		mapping[str(sec_id)] = linked

	return mapping


def detect_stale_tickets(sections: list[Any], issues: list[Any]) -> list[dict[str, Any]]:
	"""Flag stories not updated since the PRD section changed.

	We look for a section change timestamp in one of:
	- section.changed_at
	- section.metadata['changed_at']
	- section.metadata['last-reviewed'] (date)

	If a linked issue's `updated` timestamp is older than that timestamp, it is stale.
	"""
	mapping = match_to_sections(issues, sections)
	out: list[dict[str, Any]] = []

	for section in sections:
		s = _section_dict(section)
		sec_id = str(s.get("id"))
		meta = s.get("metadata", {}) or {}
		changed_at = s.get("changed_at") or meta.get("changed_at") or meta.get("last-reviewed")
		changed_dt = _parse_dt(changed_at)
		if not changed_dt:
			continue

		for issue in mapping.get(sec_id, []):
			upd = _issue_updated(issue)
			if upd and upd < changed_dt:
				out.append(
					{
						"section_id": sec_id,
						"issue_key": _issue_key(issue),
						"signal_type": "prd_changed_tickets_stale",
						"severity": "high",
						"detail": f"Section changed at {changed_dt.isoformat()}; issue last updated at {upd.isoformat()}.",
					}
				)

	return out


def detect_done_without_close(sections: list[Any], issues: list[Any]) -> list[dict[str, Any]]:
	"""Flag Done stories with un-closed PRD sections.

	A section is considered closed if its metadata `status` is one of:
	- done, complete, completed, shipped
	"""
	mapping = match_to_sections(issues, sections)
	out: list[dict[str, Any]] = []
	closed_statuses = {"done", "complete", "completed", "shipped", "closed"}
	jira_done = {"done", "closed", "resolved"}

	for section in sections:
		s = _section_dict(section)
		sec_id = str(s.get("id"))
		meta = s.get("metadata", {}) or {}
		sec_status = (meta.get("status") or s.get("status") or "").strip().lower()
		is_closed = sec_status in closed_statuses
		if is_closed:
			continue

		for issue in mapping.get(sec_id, []):
			st = (_issue_status_name(issue) or "").strip().lower()
			if st in jira_done:
				out.append(
					{
						"section_id": sec_id,
						"issue_key": _issue_key(issue),
						"signal_type": "tickets_done_prd_not_closed",
						"severity": "medium",
						"detail": f"Issue is '{st}' but section status is '{sec_status or 'missing'}'.",
					}
				)

	return out
