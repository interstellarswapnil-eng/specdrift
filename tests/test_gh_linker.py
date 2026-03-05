from __future__ import annotations

from specdrift.gh_linker.gh_linker import (
	detect_unlinked_prs,
	extract_pr_references,
	get_changed_files,
	match_files_to_scope,
)


def test_extract_pr_references_parses_prd_section_and_jira():
	pr = {
		"body": """
This changes auth.

PRD-Section: 3.1
Jira: PROJ-101, PROJ-102
""",
	}
	refs = extract_pr_references(pr)
	assert refs["prd_sections"] == ["3.1"]
	assert refs["jira_ids"] == ["PROJ-101", "PROJ-102"]


def test_get_changed_files_from_mock_dict():
	pr = {"files": [{"filename": "src/auth/login.ts"}, {"filename": "README.md"}]}
	assert get_changed_files(pr) == ["src/auth/login.ts", "README.md"]


def test_match_files_to_scope_matches_globs():
	scope_config = {
		"scope": {
			"modules": [
				{
					"name": "Authentication",
					"prd_section": "3.1",
					"file_patterns": ["src/auth/**", "src/login/**"],
				}
			]
		}
	}
	files = ["src/auth/login.ts", "src/other/x.ts"]
	matched = match_files_to_scope(files, scope_config)
	assert matched == {"3.1"}


def test_detect_unlinked_prs_flags_when_no_refs_and_scoped_files_touched():
	scope_config = {
		"scope": {
			"modules": [
				{
					"name": "Authentication",
					"prd_section": "3.1",
					"file_patterns": ["src/auth/**"],
				}
			]
		}
	}
	prs = [
		{
			"number": 45,
			"body": "No references here",
			"files": [{"filename": "src/auth/login.ts"}],
		},
		{
			"number": 46,
			"body": "PRD-Section: 3.1\nJira: PROJ-1",
			"files": [{"filename": "src/auth/logout.ts"}],
		},
	]

	flags = detect_unlinked_prs(prs, scope_config)
	assert len(flags) == 1
	assert flags[0]["pr_number"] == 45
	assert flags[0]["signal_type"] == "unlinked_pr_merged"
	assert flags[0]["matched_prd_sections"] == ["3.1"]
