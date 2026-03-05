from __future__ import annotations

import os
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from typing import Any


class GitHubLinkerError(RuntimeError):
	pass


_PRD_SECTION_RE = re.compile(r"^\s*PRD-Section\s*:\s*(?P<val>.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_JIRA_RE = re.compile(r"^\s*Jira\s*:\s*(?P<val>.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def fetch_recent_prs(repo: str, days: int = 30) -> list[Any]:
	"""Fetch merged PRs from a GitHub repo using PyGithub.

	Requires env var: GITHUB_TOKEN
	"""
	token = os.environ.get("GITHUB_TOKEN")
	if not token:
		raise GitHubLinkerError("GITHUB_TOKEN env var is required")

	try:
		from github import Github  # type: ignore
	except Exception as e:  # pragma: no cover
		raise GitHubLinkerError(
			"PyGithub dependency not installed. Install optional deps: pip install 'specdrift[engine]'"
		) from e

	gh = Github(token)
	repo_obj = gh.get_repo(repo)

	since = datetime.now(timezone.utc) - timedelta(days=days)
	# PyGithub supports search_issues for merged PRs too, but repo.get_pulls is fine for MVP.
	pulls = repo_obj.get_pulls(state="closed", sort="updated", direction="desc")

	out: list[Any] = []
	for pr in pulls:
		if not getattr(pr, "merged", False):
			continue
		merged_at = getattr(pr, "merged_at", None)
		if merged_at and merged_at.replace(tzinfo=timezone.utc) < since:
			break
		out.append(pr)

	return out


def extract_pr_references(pr: Any) -> dict[str, list[str]]:
	"""Parse PRD-Section and Jira references from a PR body."""
	body = getattr(pr, "body", None)
	if body is None and isinstance(pr, dict):
		body = pr.get("body")
	body = body or ""

	prd_sections: list[str] = []
	jira_ids: list[str] = []

	for m in _PRD_SECTION_RE.finditer(body):
		val = m.group("val")
		prd_sections.extend([v.strip() for v in re.split(r"[,\s]+", val) if v.strip()])
	for m in _JIRA_RE.finditer(body):
		val = m.group("val")
		jira_ids.extend([v.strip() for v in re.split(r"[,\s]+", val) if v.strip()])

	return {"prd_sections": prd_sections, "jira_ids": jira_ids}


def get_changed_files(pr: Any) -> list[str]:
	"""Return a list of file paths changed in a PR."""
	# PyGithub PullRequest exposes get_files(); for mocks accept .files or dict list.
	if hasattr(pr, "get_files"):
		return [f.filename for f in pr.get_files()]
	if isinstance(pr, dict) and "files" in pr:
		files = pr["files"]
		if isinstance(files, list):
			out: list[str] = []
			for f in files:
				if isinstance(f, str):
					out.append(f)
				elif isinstance(f, dict) and "filename" in f:
					out.append(str(f["filename"]))
			return out
	files_attr = getattr(pr, "files", None)
	if isinstance(files_attr, list):
		out2: list[str] = []
		for f in files_attr:
			if isinstance(f, str):
				out2.append(f)
			elif isinstance(f, dict) and "filename" in f:
				out2.append(str(f["filename"]))
		return out2
	return []


def match_files_to_scope(files: list[str], scope_config: dict[str, Any]) -> set[str]:
	"""Match changed files to scoped modules defined in specdrift.yaml.

	Returns a set of PRD section IDs touched by the changed files.
	"""
	scope = scope_config.get("scope", {}) if isinstance(scope_config, dict) else {}
	modules = scope.get("modules", []) if isinstance(scope, dict) else []

	matched_sections: set[str] = set()
	for mod in modules:
		if not isinstance(mod, dict):
			continue
		prd_section = mod.get("prd_section")
		patterns = mod.get("file_patterns") or []
		if not prd_section or not isinstance(patterns, list):
			continue

		for file in files:
			for pat in patterns:
				if not isinstance(pat, str):
					continue
				# Use fnmatch for portability; patterns from spec are glob-like.
				if fnmatch(file, pat) or fnmatch(file, pat.replace("**/", "")):
					matched_sections.add(str(prd_section))

	return matched_sections


def detect_unlinked_prs(prs: list[Any], scope_config: dict[str, Any]) -> list[dict[str, Any]]:
	"""Flag merged PRs that touch scoped files but have no PRD/Jira references."""
	out: list[dict[str, Any]] = []
	for pr in prs:
		refs = extract_pr_references(pr)
		if refs["prd_sections"] or refs["jira_ids"]:
			continue

		files = get_changed_files(pr)
		matched = match_files_to_scope(files, scope_config)
		if not matched:
			continue

		number = getattr(pr, "number", None)
		if number is None and isinstance(pr, dict):
			number = pr.get("number")

		out.append(
			{
				"pr_number": number,
				"signal_type": "unlinked_pr_merged",
				"severity": "high",
				"detail": "Merged PR touches scoped files but has no PRD-Section or Jira reference.",
				"matched_prd_sections": sorted(matched),
				"files": files,
			}
		)

	return out
