from __future__ import annotations

from specdrift.detector.detector import generate_drift_report


def _issue(key: str, *, status: str, updated: str):
	return {
		"key": key,
		"fields": {"status": {"name": status}, "updated": updated, "summary": f"Summary {key}"},
	}


def test_generate_drift_report_aggregates_all_three_signals():
	sections = [
		{
			"id": "3.1",
			"title": "Authentication",
			"metadata": {"jira": "PROJ-1", "changed_at": "2026-03-05T00:00:00+00:00", "status": "in-progress"},
			"linked_jira_ids": ["PROJ-1"],
		},
		{
			"id": "3.2",
			"title": "Payments",
			"metadata": {"jira": "PROJ-2", "status": "in-progress"},
			"linked_jira_ids": ["PROJ-2"],
		},
	]

	jira_issues = [
		_issue("PROJ-1", status="In Progress", updated="2026-03-01T00:00:00+00:00"),
		_issue("PROJ-2", status="Done", updated="2026-03-05T00:00:00+00:00"),
	]

	prs = [
		{
			"number": 45,
			"body": "No references here",
			"files": [{"filename": "src/auth/login.ts"}],
		}
	]

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

	report = generate_drift_report(
		prd_doc_id="doc123",
		sections=sections,
		jira_issues=jira_issues,
		prs=prs,
		scope_config=scope_config,
	)

	assert report["prd_doc_id"] == "doc123"
	assert report["summary"] == {"total_sections": 2, "drifted": 1, "at_risk": 1, "healthy": 0}

	sec31 = next(s for s in report["sections"] if s["id"] == "3.1")
	assert sec31["overall_health"] == "red"
	assert sec31["drift_status"] == "drifted"
	assert {sig["type"] for sig in sec31["drift_signals"]} >= {
		"prd_changed_tickets_stale",
		"unlinked_pr_merged",
	}

	sec32 = next(s for s in report["sections"] if s["id"] == "3.2")
	assert sec32["overall_health"] == "amber"
	assert sec32["drift_status"] == "at_risk"
	assert {sig["type"] for sig in sec32["drift_signals"]} == {"tickets_done_prd_not_closed"}
