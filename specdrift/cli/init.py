from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import click
import yaml


_GDOC_ID_PATTERNS = [
	# https://docs.google.com/document/d/<DOC_ID>/edit
	re.compile(r"docs\.google\.com/document/d/(?P<id>[a-zA-Z0-9_-]+)"),
	# https://drive.google.com/open?id=<DOC_ID>
	re.compile(r"[?&]id=(?P<id>[a-zA-Z0-9_-]+)"),
]


def extract_gdoc_id(value: str) -> str:
	v = (value or "").strip()
	for pat in _GDOC_ID_PATTERNS:
		m = pat.search(v)
		if m:
			return m.group("id")
	# allow pasting the raw doc id
	if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", v):
		return v
	raise click.ClickException(
		"Could not extract Google Doc ID. Paste a full Docs URL like https://docs.google.com/document/d/<id>/edit or paste the raw doc id."
	)


def _write_file(path: Path, content: str) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(content, encoding="utf-8")


_SPEC_DRIFT_SYNC_WORKFLOW = """name: SpecDrift Sync

on:
  schedule:
    - cron: '0 9 * * 1-5'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install specdrift

      - name: Sync
        run: |
          specdrift sync
        env:
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
          JIRA_SERVER: ${{ secrets.JIRA_SERVER }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
"""


_SPEC_DRIFT_PR_CHECK_WORKFLOW = """name: SpecDrift PR check

on:
  pull_request:
    types: [closed]

jobs:
  check:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install specdrift[engine]

      - name: Check PR
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          specdrift check-pr --pr ${{ github.event.number }}
"""


@click.command(help="Interactive setup wizard for SpecDrift (writes specdrift.yaml + workflows).")
@click.option(
	"--force",
	is_flag=True,
	help="Overwrite existing specdrift.yaml and workflow files if present.",
)
def init(force: bool) -> None:
	click.echo("SpecDrift init — interactive setup\n")

	prd_url = click.prompt("Google Doc PRD URL (or doc id)")
	prd_doc_id = extract_gdoc_id(prd_url)

	jira_server = click.prompt("Jira server URL (e.g. https://yourcompany.atlassian.net)")
	jira_project_key = click.prompt("Jira project key (e.g. PROJ)")

	github_repo = click.prompt("GitHub repo (org/repo)")
	if "/" not in github_repo:
		raise click.ClickException("GitHub repo must be in org/repo format")

	db_path = click.prompt("Database path", default="./specdrift.db", show_default=True)

	slack_webhook = click.prompt(
		"Slack webhook URL (optional; press Enter to skip)",
		default="",
		show_default=False,
	)

	config_path = Path("specdrift.yaml")
	if config_path.exists() and not force:
		raise click.ClickException("specdrift.yaml already exists. Re-run with --force to overwrite.")

	cfg: dict[str, Any] = {
		"project": {
			"name": "SpecDrift",
			"prd_doc_id": prd_doc_id,
			"jira_project_key": jira_project_key,
			"github_repo": github_repo,
		},
		"jira": {"server_url": jira_server},
		"sync": {"db_path": db_path, "schedule": "0 9 * * 1-5"},
	}

	if slack_webhook.strip():
		cfg["alerts"] = {
			"slack_webhook_url": slack_webhook.strip(),
			"notify_on": ["high", "medium"],
		}

	_write_file(config_path, yaml.safe_dump(cfg, sort_keys=False))

	wf_dir = Path(".github/workflows")
	wf_sync = wf_dir / "specdrift-sync.yml"
	wf_pr = wf_dir / "specdrift-pr-check.yml"
	for wf_path, wf_content in [
		(wf_sync, _SPEC_DRIFT_SYNC_WORKFLOW),
		(wf_pr, _SPEC_DRIFT_PR_CHECK_WORKFLOW),
	]:
		if wf_path.exists() and not force:
			raise click.ClickException(
				f"{wf_path} already exists. Re-run with --force to overwrite."
			)
		_write_file(wf_path, wf_content)

	click.echo("\n✅ SpecDrift initialised successfully\n")
	click.echo("Wrote:")
	click.echo(f"- {config_path}")
	click.echo(f"- {wf_sync}")
	click.echo(f"- {wf_pr}\n")

	click.echo("Next steps:")
	click.echo("1) Set your secrets in GitHub repo settings (Actions → Secrets):")
	click.echo("   - GOOGLE_CREDENTIALS")
	click.echo("   - JIRA_SERVER, JIRA_EMAIL, JIRA_TOKEN")
	click.echo("   - SLACK_WEBHOOK_URL (optional)")
	click.echo("2) Run your first sync locally:")
	click.echo("   specdrift sync")
