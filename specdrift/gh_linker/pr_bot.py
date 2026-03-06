from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from specdrift.gh_linker.gh_linker import detect_unlinked_prs


class PRBotError(RuntimeError):
	pass


@dataclass(frozen=True)
class PRCheckResult:
	should_comment: bool
	comment_body: str | None
	matched_prd_sections: list[str]
	files: list[str]


def _dashboard_url_from_repo(repo_full_name: str) -> str:
	if "/" not in repo_full_name:
		return ""
	org, name = repo_full_name.split("/", 1)
	return f"https://{org}.github.io/{name}/"


def build_pr_comment(
	*,
	jira_project_key: str,
	matched_prd_sections: list[str],
	files: list[str],
	dashboard_url: str,
) -> str:
	sections_hint = ", ".join(matched_prd_sections) if matched_prd_sections else "<section-id>"
	jira_hint = f"{jira_project_key}-123" if jira_project_key else "PROJ-123"

	file_lines = "\n".join(f"- `{f}`" for f in files) if files else "- (unable to list changed files)"

	dashboard_line = f"\n\nDashboard: {dashboard_url}" if dashboard_url else ""

	return (
		"👋 SpecDrift PR check: this PR touched scoped files but is missing PRD/Jira references in the PR description.\n\n"
		"**What to add to the PR description (copy/paste):**\n\n"
		"```\n"
		f"PRD-Section: {sections_hint}\n"
		f"Jira: {jira_hint}\n"
		"```\n\n"
		"**Why this matters:** it keeps the PRD → Jira → PR linkage intact and prevents drift going unnoticed.\n\n"
		"**Scoped files touched:**\n"
		f"{file_lines}{dashboard_line}"
	)


def post_pr_comment(*, repo: str, pr_number: int, body: str, github_token: str) -> None:
	try:
		from github import Github  # type: ignore
	except Exception as e:  # pragma: no cover
		raise PRBotError(
			"PyGithub dependency not installed. Install optional deps: pip install 'specdrift[engine]'"
		) from e

	gh = Github(github_token)
	repo_obj = gh.get_repo(repo)
	pr = repo_obj.get_pull(int(pr_number))
	pr.create_issue_comment(body)


def check_pr_and_maybe_comment(
	*,
	repo: str,
	pr_number: int,
	scope_config: dict[str, Any],
	jira_project_key: str,
	github_token: str | None = None,
) -> PRCheckResult:
	"""Check one PR. If it is unlinked and touches scoped files, comment with instructions."""
	token = (github_token or os.environ.get("GITHUB_TOKEN") or "").strip()
	if not token:
		raise PRBotError("GITHUB_TOKEN env var is required")

	try:
		from github import Github  # type: ignore
	except Exception as e:  # pragma: no cover
		raise PRBotError(
			"PyGithub dependency not installed. Install optional deps: pip install 'specdrift[engine]'"
		) from e

	gh = Github(token)
	repo_obj = gh.get_repo(repo)
	pr = repo_obj.get_pull(int(pr_number))

	# Only enforce when merged.
	merged = getattr(pr, "merged", False)
	if not merged:
		return PRCheckResult(False, None, [], [])

	flags = detect_unlinked_prs([pr], scope_config)
	if not flags:
		return PRCheckResult(False, None, [], [])

	flag = flags[0]
	matched_prd_sections = list(flag.get("matched_prd_sections") or [])
	files = list(flag.get("files") or [])

	dashboard_url = _dashboard_url_from_repo(repo)
	comment = build_pr_comment(
		jira_project_key=jira_project_key,
		matched_prd_sections=matched_prd_sections,
		files=files,
		dashboard_url=dashboard_url,
	)

	post_pr_comment(repo=repo, pr_number=int(pr_number), body=comment, github_token=token)
	return PRCheckResult(True, comment, matched_prd_sections, files)
