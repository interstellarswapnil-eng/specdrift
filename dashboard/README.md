# SpecDrift Dashboard

React + Vite dashboard for visualising the `specdrift report --format json` output.

## Local dev

From repo root:

```bash
cd dashboard
npm install

# generate a report file the SPA can read
specdrift report --format json --output dashboard/public/drift-report.json

npm run dev
```

The app fetches the report from:

- `GET /drift-report.json` (served from `dashboard/public/drift-report.json`)

## Production / GitHub Pages

A GitHub Actions workflow builds `dashboard/` and deploys `dashboard/dist` to GitHub Pages.

Note: the build sets `BASE_PATH=/<repo>/` so assets resolve correctly on Pages.
