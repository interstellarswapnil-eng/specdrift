from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from specdrift.config import load_config
from specdrift.detector.detector import generate_drift_report
from specdrift.gh_linker.gh_linker import fetch_recent_prs
from specdrift.jira_linker.jira_linker import fetch_project_issues
from specdrift.parser.gdocs import fetch_doc, parse_sections
from specdrift.store import SQLiteStateStore


def _print_table(rows: list[dict[str, Any]]) -> None:
	# Minimal pretty table (no external dependency).
	headers = ["Section", "Status", "Last Changed"]
	cols = [
		[max(len(headers[0]), *(len(r["title"]) for r in rows)) if rows else len(headers[0])],
		[max(len(headers[1]), *(len((r.get("metadata", {}).get("status") or "").strip() or "-") for r in rows)) if rows else len(headers[1])],
		[max(len(headers[2]), *(len(r.get("last_synced", "")) for r in rows)) if rows else len(headers[2])],
	]

	def fmt(values: list[str]) -> str:
		return " | ".join(v.ljust(cols[i]) for i, v in enumerate(values))

	click.echo(fmt(headers))
	click.echo("-+-".join("-" * c for c in cols))
	for r in rows:
		status = (r.get("metadata", {}).get("status") or "").strip() or "-"
		click.echo(fmt([r["title"], status, r.get("last_synced", "-")]))


def _health_icon(health: str) -> str:
	return {"red": "🔴", "amber": "🟡", "green": "🟢"}.get(health, "?")


def _print_drift_report(report: dict[str, Any]) -> None:
	click.echo(f"SpecDrift report for PRD: {report.get('prd_doc_id')} (generated_at={report.get('generated_at')})")
	click.echo("")

	for sec in report.get("sections", []):
		icon = _health_icon(sec.get("overall_health"))
		title = sec.get("title")
		sec_id = sec.get("id")
		click.echo(f"{icon} [{sec_id}] {title}")

		signals = sec.get("drift_signals") or []
		if not signals:
			click.echo("  - no drift signals")
			continue
		for sig in signals:
			sev = (sig.get("severity") or "").upper()
			type_ = sig.get("type")
			detail = sig.get("detail")
			linked_jira = sig.get("linked_jira") or []
			linked_prs = sig.get("linked_prs") or sec.get("linked_prs") or []
			refs = []
			if linked_jira:
				refs.append("Jira: " + ", ".join(linked_jira))
			if linked_prs:
				refs.append("PRs: " + ", ".join(linked_prs))
			ref_str = (" (" + " | ".join(refs) + ")") if refs else ""
			click.echo(f"  - [{sev}] {type_}: {detail}{ref_str}")
		click.echo("")

	sum_ = report.get("summary", {})
	click.echo(
		f"Summary: total={sum_.get('total_sections')} drifted={sum_.get('drifted')} at_risk={sum_.get('at_risk')} healthy={sum_.get('healthy')}"
	)


@click.group(help="SpecDrift CLI")
@click.option(
	"--config",
	"config_path",
	type=click.Path(dir_okay=False, path_type=Path),
	default=Path("specdrift.yaml"),
	show_default=True,
	help="Path to specdrift.yaml",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path):
	ctx.ensure_object(dict)
	ctx.obj["config_path"] = config_path


@cli.command(help="Sync PRD sections from Google Docs, persist to SQLite, and print a summary.")
@click.option(
	"--db",
	"db_path",
	type=click.Path(dir_okay=False, path_type=Path),
	default=Path("specdrift.db"),
	show_default=True,
	help="SQLite DB path",
)
@click.pass_context
def sync(ctx: click.Context, db_path: Path) -> None:
	config_path: Path = ctx.obj["config_path"]
	config = load_config(config_path)

	click.echo(f"Fetching Google Doc: {config.project.prd_doc_id}")
	doc = fetch_doc(config.project.prd_doc_id)
	sections_obj = parse_sections(doc)

	click.echo(f"Fetching Jira issues for project: {config.project.jira_project_key}")
	jira_issues = fetch_project_issues(config.project.jira_project_key)

	click.echo(f"Fetching recent GitHub PRs for repo: {config.project.github_repo}")
	prs = fetch_recent_prs(config.project.github_repo, days=30)

	# Detector expects plain dicts for sections.
	sections = [
		{
			"id": s.id,
			"title": s.title,
			"metadata": s.metadata,
			"linked_jira_ids": s.linked_jira_ids,
			"status": s.status,
		}
		for s in sections_obj
	]

	report = generate_drift_report(
		prd_doc_id=config.project.prd_doc_id,
		sections=sections,
		jira_issues=jira_issues,
		prs=prs,
		scope_config=config.raw,
	)

	# Fire alerts (best-effort) after drift detection.
	try:
		from specdrift.alerts.slack import send_slack_alerts

		sent = send_slack_alerts(report, config)
		if sent:
			click.echo(f"\nSent {sent} Slack alert(s).")
	except Exception as e:
		# Alerts should never break sync.
		click.echo(f"\nSlack alerting failed (continuing): {e}")

	store = SQLiteStateStore(str(db_path))
	try:
		store.save_sections(sections_obj)
		# Persist drift events for this run.
		generated_at = report.get("generated_at")
		for sec in report.get("sections", []):
			sec_id = sec.get("id")
			for sig in sec.get("drift_signals") or []:
				detail = sig.get("detail") or ""
				# Add lightweight reference hints to the detail string.
				lj = sig.get("linked_jira")
				lp = sig.get("linked_prs")
				if lj:
					detail += f" | Jira: {', '.join(lj)}"
				if lp:
					detail += f" | PRs: {', '.join(lp)}"
				store.save_drift_event(
					section_id=str(sec_id),
					signal_type=str(sig.get("type")),
					severity=str(sig.get("severity")),
					detail=detail,
					detected_at=str(generated_at),
				)
		store.log_sync("success", synced_at=str(generated_at))

		click.echo("")
		_print_drift_report(report)
	finally:
		store.close()


@cli.command(help="Check a specific GitHub PR for missing PRD/Jira references and comment if needed.")
@click.option(
	"--pr",
	"pr_number",
	type=int,
	required=True,
	help="Pull request number",
)
@click.pass_context
def check_pr(ctx: click.Context, pr_number: int) -> None:
	config_path: Path = ctx.obj["config_path"]
	config = load_config(config_path)

	from specdrift.gh_linker.pr_bot import check_pr_and_maybe_comment

	res = check_pr_and_maybe_comment(
		repo=config.project.github_repo,
		pr_number=pr_number,
		scope_config=config.raw,
		jira_project_key=config.project.jira_project_key,
	)

	if res.should_comment:
		click.echo(f"Commented on PR #{pr_number} (sections: {', '.join(res.matched_prd_sections) or '-'})")
	else:
		click.echo(f"No comment needed for PR #{pr_number}")


@cli.command(help="Print the most recently saved drift report from SQLite without re-syncing.")
@click.option(
	"--db",
	"db_path",
	type=click.Path(dir_okay=False, path_type=Path),
	default=Path("specdrift.db"),
	show_default=True,
	help="SQLite DB path",
)
def report(db_path: Path) -> None:
	store = SQLiteStateStore(str(db_path))
	try:
		cur = store.conn.cursor()
		row = cur.execute("SELECT MAX(detected_at) AS ts FROM drift_events").fetchone()
		ts = row["ts"] if row else None
		if not ts:
			raise click.ClickException(f"No drift events found in {db_path}. Run: specdrift sync")

		sections = store.get_sections()
		events = store.get_drift_events(since=ts)
		# The since=ts filter returns >= ts, but we want only the latest snapshot.
		events = [e for e in events if e.get("detected_at") == ts]

		# Group events by section
		events_by_section: dict[str, list[dict[str, Any]]] = {}
		for e in events:
			events_by_section.setdefault(str(e["section_id"]), []).append(
				{
					"type": e["signal_type"],
					"severity": e["severity"],
					"detail": e["detail"],
				}
			)

		# Recompute health + summary
		summary = {"total_sections": 0, "drifted": 0, "at_risk": 0, "healthy": 0}
		sec_blocks: list[dict[str, Any]] = []
		for s in sections:
			signals = events_by_section.get(str(s["id"]), [])
			sevs = {sig.get("severity") for sig in signals}
			if "high" in sevs:
				health = "red"
				status = "drifted"
			elif "medium" in sevs:
				health = "amber"
				status = "at_risk"
			else:
				health = "green"
				status = "healthy"

			sec_blocks.append(
				{
					"id": s["id"],
					"title": s["title"],
					"drift_status": status,
					"drift_signals": signals,
					"linked_prs": [],
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

		config_doc_id = None
		# Best-effort: infer from config file if present.
		try:
			config = load_config(Path("specdrift.yaml"))
			config_doc_id = config.project.prd_doc_id
		except Exception:
			pass

		report_obj = {
			"generated_at": ts,
			"prd_doc_id": config_doc_id,
			"sections": sec_blocks,
			"summary": summary,
		}
		_print_drift_report(report_obj)
	finally:
		store.close()
