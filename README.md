# SpecDrift

**Know when your product drifts before your stakeholders do.**

SpecDrift links your PRD sections (Google Docs) to Jira stories and GitHub PRs, detects drift signals automatically, and renders a clean dashboard so PMs and engineering leads can spot misalignment early.

> Drift isn’t a failure — it’s invisible until it’s expensive. SpecDrift makes drift visible.

---

## Dashboard (screenshot)

> Screenshot placeholder — add `docs/assets/dashboard.png` and update this link.

![SpecDrift Dashboard Screenshot](docs/assets/dashboard.png)

---

## Quickstart (5 steps)

### 1) Install

```bash
pip install specdrift
```

### 2) Initialise your project

Run the interactive wizard in your repo:

```bash
specdrift init
```

This writes:
- `specdrift.yaml`
- `.github/workflows/specdrift-sync.yml`
- `.github/workflows/specdrift-pr-check.yml`

### 3) Add GitHub Actions secrets

In your GitHub repo: **Settings → Secrets and variables → Actions**

- `GOOGLE_CREDENTIALS`
- `JIRA_SERVER`, `JIRA_EMAIL`, `JIRA_TOKEN`
- `SLACK_WEBHOOK_URL` (optional)

### 4) Run your first sync

```bash
specdrift sync
```

### 5) View the dashboard

The dashboard is a static site deployed via GitHub Pages (see the workflow files created by `specdrift init`).

---

## What SpecDrift detects (drift signals)

SpecDrift flags three common drift situations:

- 🔴 **PRD changed, tickets are stale** — the PRD section changed, but linked Jira stories haven’t been updated since.
- 🟡 **Tickets done, PRD not closed** — Jira work is marked done, but the PRD section still looks “in progress”.
- 🔴 **Unlinked PR merged** — a merged PR touched scoped code paths but didn’t include a Jira or PRD reference.

---

## Tech stack

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-vite-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TailwindCSS](https://img.shields.io/badge/tailwindcss-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![GitHub Actions](https://img.shields.io/badge/github%20actions-ci-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)

---

## Badges

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT © Swapnil Khalekar — see [LICENSE](LICENSE).
