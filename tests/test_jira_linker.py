from __future__ import annotations

from specdrift.jira_linker.jira_linker import (
	detect_done_without_close,
	detect_stale_tickets,
	match_to_sections,
)
from specdrift.parser.gdocs import Section


def _issue(key: str, *, status: str, updated: str):
	return {
		"key": key,
		"fields": {
			"status": {"name": status},
			"updated": updated,
			"summary": f"Summary {key}",
		},
	}


def test_match_to_sections_uses_linked_jira_ids():
	sections = [
		Section(
			id="1",
			title="Overview",
			level=1,
			content="",
			content_hash="h",
			metadata={"jira": "PROJ-1"},
			linked_jira_ids=["PROJ-1", "PROJ-2"],
			status=None,
		),
	]
	issues = [
		_issue("PROJ-1", status="To Do", updated="2026-03-05T10:00:00+00:00"),
		_issue("PROJ-2", status="Done", updated="2026-03-05T10:00:00+00:00"),
	]
	m = match_to_sections(issues, sections)
	assert "1" in m
	assert [i["key"] for i in m["1"]] == ["PROJ-1", "PROJ-2"]


def test_detect_stale_tickets_flags_old_updates():
	sections = [
		{
			"id": "3.1",
			"metadata": {"jira": "PROJ-1", "changed_at": "2026-03-05T00:00:00+00:00"},
			"linked_jira_ids": ["PROJ-1"],
		},
	]
	issues = [
		_issue("PROJ-1", status="In Progress", updated="2026-03-01T00:00:00+00:00"),
	]
	flags = detect_stale_tickets(sections, issues)
	assert len(flags) == 1
	assert flags[0]["signal_type"] == "prd_changed_tickets_stale"
	assert flags[0]["issue_key"] == "PROJ-1"


def test_detect_done_without_close_flags_done_issue_when_section_not_closed():
	sections = [
		{
			"id": "3.1",
			"metadata": {"jira": "PROJ-1", "status": "in-progress"},
			"linked_jira_ids": ["PROJ-1"],
		},
	]
	issues = [
		_issue("PROJ-1", status="Done", updated="2026-03-05T00:00:00+00:00"),
	]
	flags = detect_done_without_close(sections, issues)
	assert len(flags) == 1
	assert flags[0]["signal_type"] == "tickets_done_prd_not_closed"


def test_detect_done_without_close_ignores_closed_section():
	sections = [
		{
			"id": "3.1",
			"metadata": {"jira": "PROJ-1", "status": "done"},
			"linked_jira_ids": ["PROJ-1"],
		},
	]
	issues = [_issue("PROJ-1", status="Done", updated="2026-03-05T00:00:00+00:00")]
	assert detect_done_without_close(sections, issues) == []
