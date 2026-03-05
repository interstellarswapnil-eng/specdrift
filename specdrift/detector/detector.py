from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from specdrift.gh_linker.gh_linker import detect_unlinked_prs
from specdrift.jira_linker.jira_linker import detect_done_without_close, detect_stale_tickets


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def _health_from_signals(signals: list[dict[str, Any]]) -> str:
	sev = {s.get("severity") for s in signals}
	if "high" in sev:
		return "red"
	if "medium" in sev:
		return "amber"
	return "green"


def _status_from_health(health: str) -> str:
	if health == "red":
		return "drifted"
	if health == "amber":
		return "at_risk"
	return "healthy"


def generate_drift_report(
	*,
	prd_doc_id: str,
	sections: list[dict[str, Any]],
	jira_issues: list[Any],
	prs: list[Any],
	scope_config: dict[str, Any],
) -> dict[str, Any]:
	"""Aggregate drift signals from PRD parser + Jira linker + GitHub linker.

	The output matches the schema in the v0.1 spec (Module 4).
	"""

	# Signal 1: PRD changed, tickets stale
	stale_flags = detect_stale_tickets(sections, jira_issues)
	for f in stale_flags:
		f["type"] = f.pop("signal_type")
		f.setdefault("linked_jira", [f.get("issue_key")] if f.get("issue_key") else [])
		f.pop("issue_key", None)
		f.pop("section_id", None)

	# Signal 2: Tickets done, PRD not closed
	done_flags = detect_done_without_close(sections, jira_issues)
	for f in done_flags:
		f["type"] = f.pop("signal_type")
		f.setdefault("linked_jira", [f.get("issue_key")] if f.get("issue_key") else [])
		f.pop("issue_key", None)
		f.pop("section_id", None)

	# Signal 3: Unlinked PR merged
	pr_flags = detect_unlinked_prs(prs, scope_config)
	# Map PR flags to sections they touched.
	prs_by_section: dict[str, list[str]] = {}
	for pf in pr_flags:
		for sec_id in pf.get("matched_prd_sections", []) or []:
			prs_by_section.setdefault(sec_id, []).append(f"#{pf.get('pr_number')}")

	# For per-section signals we convert PR flags into section-scoped signals.
	pr_signals_by_section: dict[str, list[dict[str, Any]]] = {}
	for pf in pr_flags:
		for sec_id in pf.get("matched_prd_sections", []) or []:
			pr_signals_by_section.setdefault(sec_id, []).append(
				{
					"type": pf.get("signal_type"),
					"severity": pf.get("severity"),
					"detail": pf.get("detail"),
					"linked_prs": [f"#{pf.get('pr_number')}"] if pf.get("pr_number") else [],
				}
			)

	# Build per-section blocks
	section_blocks: list[dict[str, Any]] = []

	summary = {"total_sections": 0, "drifted": 0, "at_risk": 0, "healthy": 0}

	# Index original flags by section_id (we need to recompute to attach)
	stale_by_section: dict[str, list[dict[str, Any]]] = {}
	done_by_section: dict[str, list[dict[str, Any]]] = {}

	# Re-run with original section_id preserved (simpler):
	for f in detect_stale_tickets(sections, jira_issues):
		sec_id = str(f.get("section_id"))
		stale_by_section.setdefault(sec_id, []).append(
			{
				"type": f.get("signal_type"),
				"severity": f.get("severity"),
				"detail": f.get("detail"),
				"linked_jira": [f.get("issue_key")] if f.get("issue_key") else [],
			}
		)
	for f in detect_done_without_close(sections, jira_issues):
		sec_id = str(f.get("section_id"))
		done_by_section.setdefault(sec_id, []).append(
			{
				"type": f.get("signal_type"),
				"severity": f.get("severity"),
				"detail": f.get("detail"),
				"linked_jira": [f.get("issue_key")] if f.get("issue_key") else [],
			}
		)

	for s in sections:
		sec_id = str(s.get("id"))
		title = s.get("title") or s.get("title", "")
		# Gather signals
		signals: list[dict[str, Any]] = []
		signals.extend(stale_by_section.get(sec_id, []))
		signals.extend(done_by_section.get(sec_id, []))
		signals.extend(pr_signals_by_section.get(sec_id, []))

		health = _health_from_signals(signals)
		status = _status_from_health(health)

		section_blocks.append(
			{
				"id": sec_id,
				"title": title,
				"drift_status": status,
				"drift_signals": signals,
				"linked_prs": prs_by_section.get(sec_id, []),
				"overall_health": health,
			}
		)

		summary["total_sections"] += 1
		if status == "drifted":
			summary["drifted"] += 1
		elif status == "at_risk":
			summary["at_risk"] += 1
		else:
			summary["healthy"] += 1

	return {
		"generated_at": _utc_now_iso(),
		"prd_doc_id": prd_doc_id,
		"sections": section_blocks,
		"summary": summary,
	}
