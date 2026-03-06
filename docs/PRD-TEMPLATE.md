# [Product / Feature Name] — PRD

> This is the SpecDrift PRD template. Use this structure so SpecDrift can reliably parse and drift-check sections.

---

## 1. Overview

<!-- specdrift
jira: PROJ-101, PROJ-102
status: in-progress
last-reviewed: 2025-03-01
-->

Describe the customer problem, context, and what you’re building.

---

## 2. Goals & Success Metrics

<!-- specdrift
jira: PROJ-110
status: in-progress
last-reviewed: 2025-03-01
-->

- Goal 1:
- Goal 2:

Success metrics:
- Metric 1:
- Metric 2:

---

## 3. Functional Requirements

### 3.1 [Feature Area]

<!-- specdrift
jira: PROJ-201, PROJ-202
status: in-progress
last-reviewed: 2025-03-01
-->

Requirements:
- …

### 3.2 [Feature Area]

<!-- specdrift
jira: PROJ-210
status: in-progress
last-reviewed: 2025-03-01
-->

Requirements:
- …

---

## 4. Non-Functional Requirements

<!-- specdrift
jira: PROJ-301
status: in-progress
last-reviewed: 2025-03-01
-->

Examples:
- Performance targets
- Reliability / SLOs
- Security constraints
- Accessibility requirements

---

## 5. Out of Scope

Call out what this PRD explicitly does *not* include.

---

## 6. Open Questions

- Question 1
- Question 2

---

## 7. Revision History

| Date | Author | Change |
|---|---|---|
| YYYY-MM-DD | Name | Summary of change |

---

## Notes on the metadata block

Each section heading can include a SpecDrift metadata block (HTML comment):

```html
<!-- specdrift
jira: PROJ-101, PROJ-102
status: in-progress
last-reviewed: 2025-03-01
-->
```

- `jira:` is a comma-separated list of Jira issue keys linked to this section.
- `status:` is the PRD section status (e.g. `in-progress`, `done`, `shipped`).
- `last-reviewed:` is the last time this section was reviewed/updated.
