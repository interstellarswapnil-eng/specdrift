# SpecDrift — Project Specification
### Know when your product drifts before your stakeholders do.

**Version:** 0.1 — Initial Spec  
**Author:** Swapnil Khalekar  
**Status:** Pre-build · Open Source

---

## 1. Problem Statement

PRDs change. Jira tickets drift. Shipped code diverges. And nobody notices until a stakeholder asks *"I thought we agreed on this?"*

The root cause isn't carelessness — it's that PRDs, tickets, and code live in completely separate systems with zero native linkage. Drift is invisible until it's already painful and expensive to fix.

**SpecDrift makes drift visible in real time.**

---

## 2. Vision

An open-source tool that links PRD sections (Google Docs) to Jira epics/stories and GitHub PRs, detects alignment gaps as they happen, and surfaces them on a clean visual dashboard — so PMs, tech leads, and engineering managers can catch drift *before* it becomes conflict.

---

## 3. Target Users

| User | Pain Today | Value from SpecDrift |
|---|---|---|
| Product Manager | Manually tracks PRD vs. ticket alignment in spreadsheets | Live drift map with one-click visibility |
| Engineering Lead | Doesn't know if PRs map to current requirements | PR merge warnings for unlinked changes |
| Scrum Master / Delivery Manager | Sprint review reveals gaps that should have been caught weeks ago | Drift score per sprint / per PRD section |
| Open Source PM Community | No free tool exists for this problem | Drop-in tool, no vendor lock-in |

---

## 4. Core Concepts

### 4.1 The PRD as Source of Truth

SpecDrift treats the PRD as the canonical definition of what should be built. Every other artifact (Jira story, GitHub PR) is either **linked** to a PRD section or **flagged** as potentially drifted.

### 4.2 Sections as the Atomic Unit

A **Section** is a top-level or second-level heading block in the PRD template (e.g. `## 3. Functional Requirements > 3.1 Authentication`). Sections are the units that get linked, versioned, and drift-checked.

### 4.3 Drift Signals

There are three drift conditions SpecDrift detects:

| Signal | Trigger | Severity |
|---|---|---|
| 🔴 **PRD Changed, Tickets Stale** | A PRD section was edited (Google Docs revision history) but linked Jira stories have not been updated since | High |
| 🟡 **Tickets Done, PRD Not Closed** | Jira stories are marked Done but linked PRD section status is still In Progress or has no completion marker | Medium |
| 🔴 **Unlinked PR Merged** | A GitHub PR was merged touching files in scoped modules without a Jira or PRD reference in the PR description | High |

---

## 5. PRD Template Standard

SpecDrift is **template-based**. Users author their PRDs using the SpecDrift PRD Template, which defines a predictable section structure the parser can reliably read.

### 5.1 Required Template Sections

```
# [Product / Feature Name] — PRD

## 1. Overview
## 2. Goals & Success Metrics
## 3. Functional Requirements
   ### 3.1 [Feature Area]
   ### 3.2 [Feature Area]
## 4. Non-Functional Requirements
## 5. Out of Scope
## 6. Open Questions
## 7. Revision History
```

### 5.2 Section Metadata Block

Each section heading can optionally include a metadata comment block (HTML comment in Google Docs, invisible to readers):

```
<!-- specdrift
jira: PROJ-101, PROJ-102
status: in-progress
last-reviewed: 2025-03-01
-->
```

This is the **linking convention** — lightweight, human-readable, and copy-pasteable. SpecDrift writes these blocks automatically when you link from the dashboard.

### 5.3 Template Distribution

The SpecDrift PRD Template will be provided as:
- A Google Docs template (shareable link, copy to Drive)
- A Markdown version for GitHub-native teams
- A Notion import version (post-MVP)

---

## 6. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     SpecDrift Engine                     │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │  PRD Parser  │   │ Jira Linker  │   │  GH Linker  │  │
│  │ (Google Docs)│   │  (REST API)  │   │  (REST API) │  │
│  └──────┬───────┘   └──────┬──────┘   └──────┬──────┘  │
│         │                  │                  │          │
│         └──────────────────┼──────────────────┘          │
│                            ▼                             │
│                  ┌──────────────────┐                    │
│                  │  Drift Detector  │                    │
│                  └────────┬─────────┘                    │
│                           │                              │
│                           ▼                              │
│                  ┌──────────────────┐                    │
│                  │   State Store    │                    │
│                  │   (JSON / SQLite)│                    │
│                  └────────┬─────────┘                    │
└───────────────────────────┼──────────────────────────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
      ┌─────────────┐  ┌─────────┐  ┌──────────┐
      │  Dashboard  │  │  Slack  │  │  GitHub  │
      │ (React SPA) │  │  Alert  │  │ PR Comment│
      └─────────────┘  └─────────┘  └──────────┘
```

### 6.1 Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend / Engine | Python 3.11+ | Best ecosystem for Google/Jira APIs, readable for PM-developer contributors |
| PRD Parser | `google-api-python-client` | Official Google Docs API |
| Jira Integration | `jira` (Python library) | Jira REST API wrapper |
| GitHub Integration | `PyGithub` | GitHub REST API wrapper |
| State Store | SQLite (via `sqlite3`) | Zero-dependency, file-based, portable |
| Dashboard | React + Vite | Modern, fast, deployable to GitHub Pages |
| Visualisation | Recharts + React Flow | PRD tree map + drift cards |
| Scheduling | GitHub Actions (cron) | No infra needed, free for open source |
| Alerts | Slack Incoming Webhooks | Simple, no Slack app required |
| Deploy | GitHub Pages | Static export from React, zero hosting cost |

---

## 7. Module Breakdown

### Module 1 — PRD Parser (`specdrift/parser/`)

**Responsibility:** Connect to Google Docs, read the PRD using the template structure, detect section changes since last sync.

**Key functions:**
- `fetch_doc(doc_id)` — Pull full document content via Google Docs API
- `parse_sections(doc)` — Extract H1/H2/H3 sections into structured objects
- `extract_metadata(section)` — Parse `<!-- specdrift ... -->` blocks
- `diff_sections(current, previous)` — Compare current snapshot to stored state, return changed sections
- `snapshot_doc(doc_id)` — Store current state to SQLite

**Output:** A list of `Section` objects with: `id`, `title`, `level`, `content_hash`, `metadata`, `changed_at`, `linked_jira_ids`, `status`

---

### Module 2 — Jira Linker (`specdrift/jira_linker/`)

**Responsibility:** Fetch Jira stories, match them to PRD sections, detect status gaps.

**Key functions:**
- `fetch_project_issues(project_key)` — Pull all epics and stories
- `match_to_sections(issues, sections)` — Map via metadata block `jira:` field
- `detect_stale_tickets(sections, issues)` — Flag stories not updated since PRD section changed
- `detect_done_without_close(sections, issues)` — Flag Done stories with un-closed PRD sections

**Jira fields used:** `summary`, `status`, `updated`, `description`, `labels`, `epic_link`

---

### Module 3 — GitHub Linker (`specdrift/gh_linker/`)

**Responsibility:** Fetch merged PRs, detect unlinked merges touching scoped modules.

**Key functions:**
- `fetch_recent_prs(repo, days=30)` — Pull merged PRs
- `extract_pr_references(pr)` — Parse `PRD-Section:` and `Jira:` fields from PR body
- `get_changed_files(pr)` — List files modified in the PR
- `match_files_to_scope(files, scope_config)` — Check if changed files fall within configured scoped modules
- `detect_unlinked_prs(prs, scope_config)` — Flag PRs with no PRD/Jira reference touching scoped files

**Config:** `specdrift.yaml` defines which file paths/patterns belong to which PRD section.

---

### Module 4 — Drift Detector (`specdrift/detector/`)

**Responsibility:** Aggregate signals from Modules 1-3 and produce a drift report.

**Output schema (JSON):**
```json
{
  "generated_at": "2025-03-05T10:00:00Z",
  "prd_doc_id": "abc123",
  "sections": [
    {
      "id": "3.1",
      "title": "Authentication",
      "drift_status": "drifted",
      "drift_signals": [
        {
          "type": "prd_changed_tickets_stale",
          "severity": "high",
          "detail": "PRD section updated 2025-02-28. Linked stories PROJ-101, PROJ-102 not updated since 2025-02-20.",
          "linked_jira": ["PROJ-101", "PROJ-102"]
        }
      ],
      "linked_prs": ["#45"],
      "overall_health": "red"
    }
  ],
  "summary": {
    "total_sections": 12,
    "drifted": 3,
    "at_risk": 2,
    "healthy": 7
  }
}
```

---

### Module 5 — Dashboard (`dashboard/`)

**Responsibility:** Visual web interface showing the full PRD → Ticket → PR linkage map and drift status.

**Views:**
1. **Overview** — Summary health bar, drift count badges, last sync time
2. **PRD Tree** — Expandable section tree, each node colour-coded by health (🟢 🟡 🔴)
3. **Section Detail Panel** — Click a section to see: linked Jira stories, linked PRs, drift signals, last changed date
4. **Drift Feed** — Chronological list of detected drift events
5. **Settings** — Configure Google Doc ID, Jira project, GitHub repo, scoped modules

**Design principles:**
- PM-first: no technical jargon on the dashboard
- Shareable: every section has a permalink
- Exportable: one-click PNG/CSV export of the drift report

---

## 8. Configuration File

All project config lives in `specdrift.yaml` at the repo root:

```yaml
project:
  name: "My Product Name"
  prd_doc_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
  jira_project_key: "PROJ"
  github_repo: "org/repo"

scope:
  modules:
    - name: "Authentication"
      prd_section: "3.1"
      file_patterns:
        - "src/auth/**"
        - "src/login/**"
    - name: "Payments"
      prd_section: "3.2"
      file_patterns:
        - "src/payments/**"
        - "src/billing/**"

alerts:
  slack_webhook_url: "${SLACK_WEBHOOK_URL}"
  notify_on: ["high", "medium"]

sync:
  schedule: "0 9 * * 1-5"  # 9am Mon-Fri
```

---

## 9. CLI Interface

```bash
# First-time setup
specdrift init

# Manual sync (pull all sources, run drift detection, update dashboard)
specdrift sync

# Sync and push dashboard to GitHub Pages
specdrift sync --deploy

# Check status without full sync
specdrift status

# Link a PRD section to Jira stories manually
specdrift link --section "3.1" --jira PROJ-101 PROJ-102

# View current drift report in terminal
specdrift report

# Generate JSON report
specdrift report --format json --output drift-report.json
```

---

## 10. GitHub Actions Integration

Two workflows ship out of the box:

**`specdrift-sync.yml`** — Scheduled sync
```yaml
on:
  schedule:
    - cron: '0 9 * * 1-5'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install specdrift
      - run: specdrift sync --deploy
    env:
      GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
      JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**`specdrift-pr-check.yml`** — PR merge check
```yaml
on:
  pull_request:
    types: [closed]

jobs:
  check:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install specdrift
      - run: specdrift check-pr --pr ${{ github.event.number }}
```

---

## 11. Build Phases

### Phase 1 — Foundation (Week 1–2)
- [ ] Repo scaffold: `specdrift/` Python package + `dashboard/` React app
- [ ] `specdrift.yaml` config loader
- [ ] Google Docs API integration + section parser
- [ ] SQLite state store
- [ ] Basic `specdrift sync` CLI command
- [ ] Unit tests for parser

### Phase 2 — Integrations (Week 3)
- [ ] Jira REST API integration + story fetcher
- [ ] GitHub API integration + PR fetcher
- [ ] Scope matching (file patterns → PRD sections)
- [ ] Full drift detection engine (all 3 signals)
- [ ] JSON report output

### Phase 3 — Dashboard (Week 4–5)
- [ ] React app scaffold (Vite)
- [ ] PRD tree component (React Flow)
- [ ] Section detail panel
- [ ] Drift feed
- [ ] Colour-coded health indicators
- [ ] GitHub Pages deploy via GitHub Actions

### Phase 4 — Polish + Launch (Week 6)
- [ ] Slack alert integration
- [ ] `specdrift init` interactive setup wizard
- [ ] PR comment bot (unlinked PR warning)
- [ ] README, CONTRIBUTING.md, CODE_OF_CONDUCT.md
- [ ] SpecDrift PRD Template (Google Docs + Markdown)
- [ ] Product Hunt launch post
- [ ] Post on r/ProductManagement, LinkedIn, PM Slack communities

---

## 12. Open Source Positioning

**Repo name:** `specdrift`  
**GitHub org:** `interstellarswapnil-eng`  
**License:** MIT  
**Tagline:** *"Know when your product drifts before your stakeholders do."*

**Why PMs will adopt it:**
- Zero vendor lock-in — works with any Google Doc + any Jira project
- Self-hostable in under 30 minutes using GitHub Actions
- PMs can set it up without engineering help
- Visual output shareable in standups and planning sessions
- Extensible via community plugins (Linear, Notion, Confluence post-MVP)

**Differentiation from existing tools:**
- Jira has no native PRD linkage
- Notion has no ticket drift detection
- Linear has no PRD versioning
- No existing open source tool connects all three layers (PRD → Ticket → Code)

---

## 13. Success Metrics (for the open source project)

| Metric | 30-day target | 90-day target |
|---|---|---|
| GitHub Stars | 50 | 300 |
| Forks / Installations | 10 | 75 |
| Community PRs | 2 | 10 |
| PM community mentions | 3 | 15 |
| Product Hunt upvotes | — | Top 5 of the day |

---

*Deployed on GitHub Pages · Open Source under MIT License*
