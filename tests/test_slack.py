from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from specdrift.alerts.slack import get_dashboard_url, send_slack_alerts
from specdrift.config import ProjectConfig, SpecDriftConfig


@dataclass
class _FakeResponse:
	status: int = 200

	def read(self):
		return b"ok"

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		return False


def test_get_dashboard_url_from_github_repo():
	cfg = SpecDriftConfig(
		raw={"project": {}},
		project=ProjectConfig(
			name="SpecDrift",
			prd_doc_id="doc",
			jira_project_key="PROJ",
			github_repo="interstellarswapnil-eng/specdrift",
		),
	)
	assert get_dashboard_url(cfg) == "https://interstellarswapnil-eng.github.io/specdrift/"


def test_send_slack_alerts_filters_by_notify_on_and_posts(monkeypatch):
	posted: list[dict] = []

	def fake_urlopen(req, timeout=10):
		payload = json.loads(req.data.decode("utf-8"))
		posted.append({"url": req.full_url, "payload": payload, "headers": dict(req.header_items())})
		return _FakeResponse()

	monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T000/B000/XXX")
	monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

	cfg = SpecDriftConfig(
		raw={"alerts": {"notify_on": ["high", "medium"]}},
		project=ProjectConfig(
			name="SpecDrift",
			prd_doc_id="doc",
			jira_project_key="PROJ",
			github_repo="interstellarswapnil-eng/specdrift",
		),
	)

	report = {
		"generated_at": "2026-03-06T00:00:00Z",
		"prd_doc_id": "doc",
		"sections": [
			{
				"id": "3.1",
				"title": "Authentication",
				"linked_prs": ["#45"],
				"drift_signals": [
					{
						"type": "prd_changed_tickets_stale",
						"severity": "high",
						"detail": "PRD changed",
						"linked_jira": ["PROJ-1"],
					},
					{
						"type": "tickets_done_prd_not_closed",
						"severity": "medium",
						"detail": "Tickets done",
						"linked_jira": ["PROJ-2"],
					},
					{
						"type": "unlinked_pr_merged",
						"severity": "low",
						"detail": "Low severity shouldn't send",
						"linked_prs": ["#99"],
					},
				],
			}
		],
		"summary": {"total_sections": 1, "drifted": 1, "at_risk": 0, "healthy": 0},
	}

	sent = send_slack_alerts(report, cfg)
	assert sent == 2
	assert len(posted) == 2
	assert all(p["url"].startswith("https://hooks.slack.com/services/") for p in posted)

	# Basic formatting checks
	text0 = posted[0]["payload"]["text"]
	assert "SpecDrift" in text0
	assert "Section:" in text0
	assert "Dashboard:" in text0
	# Ensure emoji for high/medium appear somewhere
	assert any("🔴" in p["payload"]["text"] for p in posted)
	assert any("🟡" in p["payload"]["text"] for p in posted)


def test_send_slack_alerts_no_webhook_noop(monkeypatch):
	monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

	cfg = SpecDriftConfig(
		raw={"alerts": {"notify_on": ["high"]}},
		project=ProjectConfig(
			name="SpecDrift",
			prd_doc_id="doc",
			jira_project_key="PROJ",
			github_repo="interstellarswapnil-eng/specdrift",
		),
	)

	report = {"generated_at": "x", "prd_doc_id": "doc", "sections": [], "summary": {"total_sections": 0, "drifted": 0, "at_risk": 0, "healthy": 0}}
	assert send_slack_alerts(report, cfg) == 0
