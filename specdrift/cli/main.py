from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from specdrift.config import load_config
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
	sections = parse_sections(doc)

	store = SQLiteStateStore(str(db_path))
	try:
		store.save_sections(sections)
		rows = store.get_sections()
		click.echo("")
		_print_table(rows)
		click.echo("")
		click.echo(f"Saved {len(rows)} section(s) to {db_path}")
	finally:
		store.close()
