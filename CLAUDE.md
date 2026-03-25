# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- **Python**: `E:\MC\anaconda3\python.exe` (3.8–3.10 compatible; tested on 3.11)
- **Node.js**: `D:\Program Files\nodejs\` — must be added to PATH for npm commands in bash:
  ```bash
  PATH="/d/Program Files/nodejs:$PATH" npm run dev
  ```
- **HTTP proxy**: System proxy (Privoxy) intercepts `curl` and `urllib`. To test API endpoints from Python, use `urllib.request.build_opener(urllib.request.ProxyHandler({}))` to bypass it.

## Commands

### Backend

```bash
# Run (production — serves built frontend too)
cd backend && E:\MC\anaconda3\python.exe run.py

# Run (dev with hot reload)
cd backend && E:\MC\anaconda3\python.exe -m uvicorn app.main:app --reload --port 8000

# Install dependencies
E:\MC\anaconda3\Scripts\pip.exe install -r backend/requirements.txt
```

The backend **must be started from the `backend/` directory** — relative paths for `data/` and `logs/` are resolved from cwd.

### Frontend

```bash
cd frontend

# Dev server (proxies /api/* to localhost:8000)
PATH="/d/Program Files/nodejs:$PATH" npm run dev

# Production build (output to frontend/dist/)
PATH="/d/Program Files/nodejs:$PATH" npm run build

# Lint
PATH="/d/Program Files/nodejs:$PATH" npm run lint
```

### Windows convenience scripts (run from repo root)

- `start.bat` — production backend only
- `start-dev.bat` — opens two terminal windows (backend with `--reload`, frontend dev server)

## Architecture

### Overview

Two independent processes in development; one process in production.

- **Dev**: Backend on `:8000`, frontend dev server on `:5173` (webpack-dev-server proxies `/api/*` → `:8000`)
- **Production**: `npm run build` outputs to `frontend/dist/`. Backend detects this directory at startup and mounts it as static files, serving everything from `:8000`.

### Backend (`backend/app/`)

The FastAPI app wires together three layered concerns:

**1. Scheduling layer** (`services/scheduler.py`)
- Wraps APScheduler `BackgroundScheduler` with a `ThreadPoolExecutor` (up to `MAX_CONCURRENT_JOBS` threads).
- On startup, loads all `is_enabled=True` jobs from DB and registers each with APScheduler using `CronTrigger.from_crontab()`. Also resets any jobs stuck in `is_running=True` (crash recovery).
- Each APScheduler job calls a closure `_make_job_fn(job_id)` that fetches fresh DB state on each fire — this avoids stale ORM objects across scheduler ticks.
- `trigger_now()` fires a one-shot `date` trigger for manual runs.
- `next_run_at` is written to the DB by reading it back from APScheduler immediately after `add_job()`.

**2. Execution layer** (`services/executor.py`)
- `run_job()` is called synchronously from scheduler background threads. It owns the full lifecycle: create `JobExecution` record → spawn subprocess → wait → update record → broadcast SSE.
- Platform detection in `_build_command()`: Windows uses `cmd.exe /c` (or `powershell.exe -NonInteractive -Command`); Linux uses `bash -c` (or `sh -c`). Shell type is per-job configurable.
- `_running_procs` dict (execution_id → `Popen`) enables `kill_execution()` from the API.
- stdout/stderr are captured via `proc.communicate()` and truncated to 1MB before storage.
- On failure, if `retry_number < max_retries`, schedules a one-shot APScheduler `date` job for retry.

**3. Real-time layer** (`services/notifier.py`)
- Maintains a `set` of `asyncio.Queue` objects — one per connected SSE client.
- `broadcast()` is called from scheduler threads; uses `loop.call_soon_threadsafe()` to safely enqueue events into the asyncio event loop.
- `GET /api/v1/events` is a `StreamingResponse` that dequeues and yields events. Sends a `: heartbeat` comment every 30s to keep connections alive.

**Data model** (`models/job.py`)
- Two tables: `jobs` and `job_executions` (cascade-delete linked).
- All timestamps stored as UTC ISO8601 strings (SQLite has no native datetime type).
- `environment_vars` stored as a JSON string in a `Text` column; serialized/deserialized at the router layer.
- SQLite is configured with WAL mode and `foreign_keys=ON` via `PRAGMA` on each connection.
- Schema is created via `Base.metadata.create_all()` on startup — no migrations system.

**Routers** (`routers/`)
- `jobs.py`: CRUD + action endpoints. After `add_job()`, calls `_sync_next_run()` to read `next_run_at` back from APScheduler into the same DB session before returning the response.
- `executions.py`: read-only history + kill endpoint.
- `system.py`: `/health`, `/stats` (aggregate queries), `/events` (SSE stream).

**Configuration** (`config.py`)
- Pydantic `BaseSettings` reads from environment variables and optional `.env` file in the backend directory.
- `CORS_ORIGINS` is a comma-separated string split into a list at runtime.

### Frontend (`frontend/src/`)

- **Build tool**: Vue CLI 5 (`@vue/cli-service`) with webpack. Supports Node 16 and Node 24. Config in `vue.config.js`.
- **Framework**: Vue 3 (`<script setup>` Composition API). No TypeScript — plain JS throughout.
- **Routing**: Vue Router 4 with three routes: `/` (Dashboard), `/jobs` (Jobs), `/executions` (Executions). Router in `main.js`.
- **Data fetching**: Plain `ref`/`watch`/`setInterval` polling (10000–15000ms). No TanStack Query.
- **SSE**: `composables/useSSE.js` opens `EventSource('/api/v1/events')`; on `execution_started`/`execution_finished`, calls `emitSSEUpdate()` from `sseEvents.js` (simple Set-based pub/sub). Pages subscribe via `onSSEUpdate()`. Auto-reconnects after 5s.
- **API client**: Axios instance in `api/client.js` with `baseURL: '/api/v1'`. Error interceptor unwraps `response.data.detail` into a plain `Error`.
- **Styling**: Single `styles.css` file (dark theme, CSS custom properties). No component library or Tailwind — all styles are hand-written classes. Imported in `main.js`.
- **HTML entry**: `public/index.html` (Vue CLI convention).

### Key data flows

**Scheduled execution**: APScheduler fires → `_make_job_fn` closure → `executor.run_job()` in thread → subprocess → DB update → `notifier.broadcast()` → SSE queues → `emitSSEUpdate()` → page composables refetch → UI refreshes.

**Manual trigger**: `POST /jobs/{id}/run` → `scheduler.trigger_now()` adds a `date` job → same path as above.

**Job create/update**: Router validates cron via `croniter.is_valid()` → writes to DB → `scheduler.add_job()` registers with APScheduler → `_sync_next_run()` reads `next_run_at` back from APScheduler → returns response with populated `next_run_at`.
