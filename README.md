# SpecDrift

**Know when your product drifts before your stakeholders do.**

SpecDrift is an open-source tool that links PRD sections (Google Docs) to Jira epics/stories and GitHub PRs, detects alignment gaps as they happen, and surfaces them in a simple dashboard.

## Status

This repo is scaffolded from the v0.1 spec. The initial focus is Phase 1 (foundation): config, Google Docs parsing, SQLite state store, and a `specdrift sync` CLI.

## Quick start (dev)

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

specdrift --help
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

## Configuration

Copy the example config:

```bash
cp specdrift.yaml.example specdrift.yaml
```

## License

MIT
