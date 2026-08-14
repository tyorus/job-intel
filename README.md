# Job Intelligence

Personal **Job Intelligence & pipeline tracker**: discover remote jobs from public boards, log LinkedIn roles by hand, track applications, and run a client-prospect pipeline for [Tyorus services](https://tyorus.com/services/).

**No auto-apply. No LinkedIn scraping.** GitHub Pages is not used — the Vue app deploys to Vercel.

## Architecture

```text
career_data/*.yaml     →  jobintel.career (load/validate)
Supabase               →  companies / jobs / applications / prospects / progress_events
FastAPI (Vercel /api)  →  CRUD + progress
Vue 3 (Vercel)         →  tracker dashboard
GitHub Actions hourly  →  jobintel scrape → Supabase
```

```text
Public boards (RemoteOK, Arbeitnow, Greenhouse, Lever, RSS)
        │  hourly, GitHub Actions
        ▼
    Supabase jobs (status=new, dedup url/hash)
        │
Vue  +  FastAPI  →  progress_events, applications, prospects
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12)
- Node 20+ (Vue dashboard)
- A Supabase project
- Vercel project rooted at this folder (not GitHub Pages)

## Setup

```bash
cd job-intelligence
cp .env.example .env
# set SUPABASE_*, TRACKER_API_KEY
uv sync --group dev
```

Apply both SQL files in `supabase/migrations/` via the Supabase SQL editor or `supabase db push`.

## Local development

Without Supabase credentials the API uses SQLite at `data/tracker.sqlite`.

```bash
# API
uv run uvicorn jobintel.api.app:app --reload --app-dir backend --port 8000

# Vue (proxies /api → :8000)
cd frontend && npm install && npm run dev
```

Open http://127.0.0.1:5173 and unlock with `TRACKER_API_KEY` (local default in `.env.example` is `change-me`; this workspace uses `local-dev`).

```bash
uv run python -m jobintel.cli career validate
uv run jobintel scrape --dry-run
uv run ruff check .
uv run pytest
```

## Scrape (public sources only)

Hourly GitHub Action runs `uv run jobintel scrape`. Collectors:

- RemoteOK API
- Arbeitnow job-board API
- Greenhouse / Lever public board JSON (`backend/jobintel/collectors/boards.yaml`)
- RSS (We Work Remotely)

Keyword filter: `SCRAPE_KEYWORDS`. Dedup uses `jobs.url` and `jobs.content_hash`.

LinkedIn postings: **Add job** in the dashboard (`source=linkedin`). Do not crawl LinkedIn.

### GitHub Actions secrets

If this folder is the git root, the workflow is `.github/workflows/scrape.yml`. If it lives inside a parent repo, copy that workflow to the parent `.github/workflows/` and set `working-directory: job-intelligence`.

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Vercel

Project root: this directory. Env vars (Production + Preview):

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TRACKER_API_KEY`
- `TRACKER_CORS_ORIGINS` — optional; same-origin `/api` does not need CORS

Do not put the service role key in `VITE_*` frontend env.

## Career profile

Verified facts live in `career_data/` (seeded from [tyorus.com/resume](https://tyorus.com/resume/) and [LinkedIn](https://www.linkedin.com/in/tyo-suwignyo/)). See `career_data/SOURCES.md`.

## Milestone status

| Milestone | Status |
| --- | --- |
| M1 structure, models, career YAML, SQL schema | **done** |
| Tracker: prospects + progress events | **done** |
| FastAPI CRUD + API key | **done** |
| Vue dashboard (Vercel) | **done** |
| Hourly public scrape (GitHub Actions) | **done** |
| M2 manual/JSON ingestion | superseded by tracker + scrape |
| M3 OpenRouter extraction | pending |
| M4 deterministic scoring | pending |
| M5 React dashboard | replaced by Vue on Vercel |
| M6 resume Edge Function | pending |
| M7 GitHub Actions | scrape workflow **done**; CI tests optional |
| M8 GitHub Pages | **not used** (Vercel hosts the app) |

## License

Private personal project.
