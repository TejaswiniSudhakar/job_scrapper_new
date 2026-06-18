# Job Scraper Dashboard

Frontend dashboard for a private job scraping pipeline that collects and scores jobs from LinkedIn, Naukri, Indeed, and future job sources.

The frontend is safe to publish publicly. It does not need scraper credentials, browser profiles, database files, or raw backend secrets. It reads job data through local Next.js API routes that can point to a private backend folder on your machine.

## What This Dashboard Does

- Shows real scraped jobs from the backend `jobs.csv` file.
- Displays KPI cards for total jobs found, active jobs, jobs scraped today, and scraper success rate.
- Shows scraper analytics by source, including LinkedIn, Naukri, and Indeed counts.
- Renders an AG Grid job table with sorting, filtering, pagination, resizing, sticky columns, and bulk selection.
- Lets you filter jobs by source, work mode, posted date range, and minimum GPT score.
- Supports global search across job title, company, location, source, and description.
- Opens a detailed drawer for each job with score breakdown, GPT summary, GPT reasoning, description, skills, and status.
- Lets you change job status locally, such as `UNAPPLIED`, `APPLIED`, `INTERVIEW`, `REJECTED`, `OFFER`, `EXPIRED`, and `SAVED`.
- Exports the currently filtered job list to CSV.
- Includes saved search presets for fast filtering.
- Supports light and dark themes.
- Shows toast notifications for exports, apply-link clicks, and optional realtime events.

## Data Flow

The private backend writes scraped jobs to:

```text
jobs.csv
jobs.db
log.txt
```

The frontend reads only `jobs.csv` through:

```text
app/api/jobs/route.ts
```

That API route maps backend CSV columns into the dashboard `Job` model:

- `title` -> `jobTitle`
- `company` -> `company`
- `job_url` -> `applyLink`
- `source` -> `source`
- `experience_required` -> `experienceRequired`
- `job_description` -> `description`
- `final_score` / `gpt_score` / `pre_score` -> dashboard score fields
- `reason` -> GPT reasoning
- `created_at` -> scraped and posted timestamps

Analytics are generated from the same real job list through:

```text
app/api/analytics/route.ts
```

## Backend Folder Configuration

By default, the frontend looks for the backend data folder here:

```text
C:\Users\Nishant Chandraker\Downloads\private-job-scraper-main\private-job-scraper-main
```

To use another backend path, create `.env.local` in the frontend root:

```powershell
JOB_SCRAPER_DATA_DIR=C:\path\to\private-job-scraper-main
```

An example file is included:

```text
.env.local.example
```

Do not commit `.env.local`; it is ignored by Git.

## Run The App

Install dependencies:

```powershell
cd "C:\Users\Nishant Chandraker\Documents\Codex\2026-06-04\help-me-di-all-the-libraries\outputs\job-scraper-dashboard"
npm install
```

Start the scraper and frontend together:

```powershell
npm run dev
```

This command runs:

- Python scraper backend from `main.py`
- Next.js dashboard at `http://localhost:3000`

Open:

```text
http://localhost:3000
```

Stop both processes from the same terminal:

```text
Ctrl+C
```

If the scraper does not stop on Windows, use:

```text
Ctrl+Break
```

Run only the frontend:

```powershell
npm run dev:frontend
```

Run only the scraper:

```powershell
npm run dev:scraper
```

## Verify Real Backend Data

With the dev server running, open:

```text
http://localhost:3000/api/jobs
```

You should see JSON containing real scraped jobs from the backend CSV.

Open:

```text
http://localhost:3000/api/analytics
```

You should see counts grouped by scraper source.

## Optional Mock Realtime Events

The app includes a mock realtime event simulator from the prototype stage. It is disabled by default so it does not show fake "new job scraped" popups.

To enable mock events for UI demos:

```powershell
NEXT_PUBLIC_ENABLE_MOCK_REALTIME=true
```

Keep this disabled for real scraper usage unless you intentionally want demo events.

## Main Frontend Files

```text
app/page.tsx                         Main dashboard page
app/api/jobs/route.ts                Reads and maps backend jobs.csv
app/api/analytics/route.ts           Builds dashboard analytics from real jobs
components/jobs/job-grid.tsx         AG Grid job table
components/jobs/filters-bar.tsx      Source, work mode, date, and score filters
components/jobs/job-details-drawer.tsx
components/dashboard/kpi-strip.tsx
components/dashboard/scraper-analytics.tsx
hooks/use-live-jobs.ts               Optional mock realtime subscription
lib/api/jobs.ts                      Client-side API calls
store/dashboard-store.ts             Zustand dashboard state
types/jobs.ts                        Shared dashboard types
```

## Tech Stack

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- AG Grid
- TanStack Query
- Zustand
- Recharts
- Framer Motion
- Lucide React

## Public Repository Safety

This frontend can be pushed to the public repository:

```text
https://github.com/nishant73/Job-Scrapper-LinkedIn-Naukri-Indeed-
```

The frontend `.gitignore` excludes generated files, local env files, backend databases, backend CSV exports, logs, Python caches, and virtual environments.

The private backend repository should keep credentials and scraper runtime data separate:

```text
https://github.com/nishant73/private-job-scraper
```

Even for a private repo, avoid committing API keys unless you deliberately want that risk.

## Push Frontend To GitHub

```powershell
cd "C:\Users\Nishant Chandraker\Documents\Codex\2026-06-04\help-me-di-all-the-libraries\outputs\job-scraper-dashboard"

git add .
git commit -m "Clean README and gitignore"
git push
```

## Troubleshooting

If the dashboard shows zero jobs:

- Confirm the backend has a `jobs.csv` file.
- Confirm `JOB_SCRAPER_DATA_DIR` points to the folder containing `jobs.csv`.
- Open `/api/jobs` and check for an error message.
- Restart `npm run dev` after changing `.env.local`.

If the job count appears but table rows do not render:

- Make sure `ag-grid-community` and `ag-grid-react` are installed.
- The grid registers `AllCommunityModule` and uses `theme="legacy"` for AG Grid v33 CSS theme compatibility.

If you see only popup notifications:

- Keep `NEXT_PUBLIC_ENABLE_MOCK_REALTIME` unset or set to `false`.
- Real jobs come from `/api/jobs`, not the mock realtime simulator.
