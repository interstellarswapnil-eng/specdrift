from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from specdrift.config import SpecDriftConfig


@dataclass(frozen=True)
class SlackAlert:
	severity: str
	section_id: str
	section_title: str
	signal_type: str
	detail: str | None
	linked_jira: list[str]
	linked_prs: list[str]
	dashboard_url: str


_SIGNAL_LABELS: dict[str, str] = {
	"prd_changed_tickets_stale": "PRD changed, tickets are stale",
	"tickets_done_prd_not_closed": "Tickets done, PRD not closed",
	"unlinked_pr_merged": "Unlinked PR merged",
}


def _severity_emoji(severity: str) -> str:
	sev = (severity or "").lower()
	if sev == "high":
		return "🔴"
	if sev == "medium":
		return "🟡"
	# we intentionally don't alert on low by default, but keep it readable.
	return "⚪"


def _plain_english_signal_type(signal_type: str) -> str:
	s = (signal_type or "").strip()
	if not s:
		return "Unknown drift signal"
	if s in _SIGNAL_LABELS:
		return _SIGNAL_LABELS[s]
	# fallback: snake_case -> Title Case
	return " ".join(w.capitalize() for w in s.replace("-", "_").split("_"))


def _resolve_env_template(value: str | None) -> str | None:
	"""Resolve strings like "${VAR_NAME}" into os.environ[VAR_NAME]."""
	if not value:
		return value
	v = value.strip()
	if v.startswith("${") and v.endswith("}") and len(v) > 3:
		return os.environ.get(v[2:-1])
	return v


def get_slack_webhook_url(config: SpecDriftConfig) -> str | None:
	# Env var wins.
	env = os.environ.get("SLACK_WEBHOOK_URL")
	if env and env.strip():
		return env.strip()

	alerts = (config.raw or {}).get("alerts")
	if not isinstance(alerts, dict):
		return None

	url = alerts.get("slack_webhook_url")
	if not isinstance(url, str):
		return None
	return _resolve_env_template(url)


def get_notify_on_severities(config: SpecDriftConfig) -> set[str]:
	alerts = (config.raw or {}).get("alerts")
	if not isinstance(alerts, dict):
		return {"high", "medium"}

	notify_on = alerts.get("notify_on")
	if notify_on is None:
		return {"high", "medium"}
	if not isinstance(notify_on, list):
		return {"high", "medium"}

	vals: set[str] = set()
	for v in notify_on:
		if isinstance(v, str) and v.strip():
			vals.add(v.strip().lower())
	return vals or {"high", "medium"}


def get_dashboard_url(config: SpecDriftConfig) -> str:
	"""Best-effort dashboard URL.

	Defaults to GitHub Pages convention: https://{org}.github.io/{repo}/
	"""
	repo = (config.project.github_repo or "").strip()
	if "/" in repo:
		org, name = repo.split("/", 1)
		return f"https://{org}.github.io/{name}/"
	return ""


def iter_slack_alerts(report: dict[str, Any], *, dashboard_url: str) -> Iterable[SlackAlert]:
	for sec in report.get("sections", []) or []:
		sec_id = str(sec.get("id") or "")
		title = str(sec.get("title") or "")
		for sig in sec.get("drift_signals") or []:
			yield SlackAlert(
				severity=str(sig.get("severity") or ""),
				section_id=sec_id,
				section_title=title,
				signal_type=str(sig.get("type") or ""),
				detail=sig.get("detail"),
				linked_jira=list(sig.get("linked_jira") or []),
				linked_prs=list(sig.get("linked_prs") or sec.get("linked_prs") or []),
				dashboard_url=dashboard_url,
			)


def _format_alert_text(a: SlackAlert) -> str:
	emoji = _severity_emoji(a.severity)
	signal_label = _plain_english_signal_type(a.signal_type)

	refs: list[str] = []
	if a.linked_jira:
		refs.append("Jira: " + ", ".join(a.linked_jira))
	if a.linked_prs:
		refs.append("PRs: " + ", ".join(a.linked_prs))

	refs_line = ("\n*Links:* " + " | ".join(refs)) if refs else ""
	detail_line = f"\n*Detail:* {a.detail}" if a.detail else ""

	section = a.section_title or a.section_id
	# Keep it Slack-friendly: markdown, concise.
	msg = (
		f"{emoji} *SpecDrift* — *{signal_label}*\n"
		f"*Section:* {section}"
		f"{detail_line}"
		f"{refs_line}"
	)
	# Include dashboard link at bottom
	if a.dashboard_url:
		msg += f"\n*Dashboard:* {a.dashboard_url}"
	return msg


def post_to_slack(webhook_url: str, *, text: str) -> None:
	payload = {"text": text}
	data = json.dumps(payload).encode("utf-8")
	req = urllib.request.Request(
		webhook_url,
		data=data,
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
		# Consume response for completeness
		resp.read()


def send_slack_alerts(report: dict[str, Any], config: SpecDriftConfig) -> int:
	"""Send Slack alerts for any drift signals matching config severity filters.

	Returns number of alerts sent.
	"""
	webhook_url = get_slack_webhook_url(config)
	if not webhook_url:
		return 0

	notify_on = get_notify_on_severities(config)
	dashboard_url = get_dashboard_url(config)

	sent = 0
	for alert in iter_slack_alerts(report, dashboard_url=dashboard_url):
		sev = (alert.severity or "").lower()
		if sev not in notify_on:
			continue
		text = _format_alert_text(alert)
		post_to_slack(webhook_url, text=text)
		sent += 1

	return sent
