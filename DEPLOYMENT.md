# SigmaCloud AI Deployment Guide

Two supported paths:

- **[A. Render + Vercel](#a-render--vercel)** — managed, free tier, current setup.
- **[B. Docker Compose](#b-docker-compose)** — one host, persistent storage.

---

## A. Render + Vercel

Backend on Render, frontend on Vercel, Postgres managed.

### A1. Create the database

Render Dashboard → **New → PostgreSQL**. Copy the **Internal Database URL**.

> Render's free Postgres expires after a limited period and is then deleted.
> Note the expiry date, or use a Neon / Supabase free tier instead — both are
> longer-lived and work identically.

### A2. Deploy the backend

**New → Web Service** → connect the repo.

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Docker |
| Health Check Path | `/api/health` |

A [`render.yaml`](render.yaml) blueprint is included if you prefer to apply the
whole thing at once.

Environment variables:

| Key | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Internal Database URL from A1 |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GOOGLE_CLIENT_ID` | OAuth client ID from Google Cloud Console |
| `ALLOWED_ORIGINS` | `["https://your-app.vercel.app"]` |
| `WEB_CONCURRENCY` | `1` |
| `MODEL_STORAGE_PATH` | `/app/storage/models` |
| `DATASET_STORAGE_PATH` | `/app/storage/datasets` |

Notes on three of these:

- **`ENVIRONMENT=production`** makes a missing `JWT_SECRET_KEY` a hard startup
  failure rather than a silent fallback to a known constant.
- **`ALLOWED_ORIGINS`** must list your exact frontend origin. Do not widen it to
  all of `vercel.app` — that authorises every site on the platform to call your
  API with credentials.
- **`WEB_CONCURRENCY=1`** because each worker loads the whole
  sklearn/XGBoost/LightGBM stack, which does not fit twice in 512MB.

### A3. Deploy the frontend

Vercel → **Add New → Project** → set **Root Directory** to `frontend`.

Environment variables, set for **Production and Preview**:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://your-api.onrender.com` (no trailing slash, no `/api`) |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Same client ID as the backend |

> `NEXT_PUBLIC_*` values are compiled into the bundle at **build time**.
> Changing one in the dashboard does nothing until you redeploy.

If `NEXT_PUBLIC_API_URL` is unset, the frontend falls back to same-origin
`/api`, which 404s on Vercel — with no error explaining why.

### A4. Google OAuth

Google Cloud Console → Credentials → your OAuth client → **Authorized
JavaScript origins**, add:

- `https://your-app.vercel.app`
- `http://localhost:3000` (for local development)

Preview deployments get random URLs and will not match, so sign-in only works on
production and localhost. That is a Google constraint, not a bug.

### A5. Verify

```bash
curl https://your-api.onrender.com/api/health
```

```json
{"status":"healthy","database":"up","uptime_seconds":12.4,"recently_started":true}
```

`"database":"down"` means `DATABASE_URL` is wrong or the database is unreachable.

### A6. Known free-tier behaviour

**Cold starts.** The service sleeps after ~15 minutes idle; the next request
takes 30-60s to wake it. The app handles this deliberately — the landing page
warns visitors up front, session restore waits and retries instead of signing
users out, and a progress notice explains the delay while it happens.

To avoid it entirely, ping `/api/health` every 10 minutes from an external cron.
Be aware this consumes nearly all of the monthly free instance-hours budget,
leaving no room for a second free service.

**Ephemeral storage.** The disk is wiped on every deploy, restart, and wake.
Database rows survive; dataset and model *files* do not. The app degrades
honestly rather than erroring out:

- Datasets and models show a **file cleared** badge once their file is gone.
- Example datasets are silently rewritten when reloaded.
- Database-backed datasets offer **Resync** to rebuild from the live source.
- Jobs interrupted by a restart are marked failed at startup with an
  explanation, instead of sitting at "running" forever.

For real persistence, attach a Render Disk mounted at `/app/storage` (paid), or
move artifacts to object storage.

---

## B. Docker Compose

Single host, real disk, no cold starts.

### B1. Prerequisites

Docker with either `docker compose` (plugin) or `docker-compose` (standalone).

### B2. Configure

```bash
cp backend/.env.example backend/.env
```

Set at minimum:

```env
ENVIRONMENT=production
JWT_SECRET_KEY=<generated value>
GOOGLE_CLIENT_ID=<your client id>
ALLOWED_ORIGINS=["http://localhost:3000"]
DATABASE_URL=postgresql://sigma:<password>@postgres:5432/sigmacloud
```

Create `.env` beside `docker-compose.yml` for the values Compose itself reads:

```env
POSTGRES_PASSWORD=<strong password>
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<your client id>
```

`NEXT_PUBLIC_*` must be here, not only in the backend env file — Compose passes
them to the frontend image as build args.

### B3. Launch

```bash
docker compose up -d --build
```

### B4. Verify

```bash
curl http://localhost:8000/api/health
curl http://localhost:3000
```

### B5. Firewall

Allow inbound `3000` and `8000`. Block public inbound `5432` and `6379` —
Postgres and Redis should only be reachable inside the Compose network.

### B6. Operations

```bash
docker compose ps
docker compose logs -f backend
docker compose up -d --build      # after a git pull
```

Storage lives in the named volumes `model_storage` and `dataset_storage` and
survives restarts and rebuilds.

---

## Configuration reference

Every backend variable is documented in
[`backend/.env.example`](backend/.env.example).

## Troubleshooting

**`ModuleNotFoundError: No module named 'psycopg2'`**
Dependencies are stale. Rebuild without cache: `docker compose build --no-cache backend`.

**`Can't load plugin: sqlalchemy.dialects:postgres`**
A `postgres://` URL reached SQLAlchemy unrewritten. The app normalises this, so
it means an old build is running — redeploy.

**CORS errors in the browser console**
`ALLOWED_ORIGINS` does not include your frontend origin. It must match scheme,
host, and port exactly, and the backend must be restarted after changing it.

**Sign-in button missing**
`NEXT_PUBLIC_GOOGLE_CLIENT_ID` was not set at build time. Set it and redeploy.

**Everything 404s from the frontend**
`NEXT_PUBLIC_API_URL` is unset, so requests go to Vercel instead of your API.
Set it and redeploy.

**Training jobs stuck at "running"**
The service restarted mid-job. They are reconciled to `failed` on the next
startup, after `STALE_JOB_TIMEOUT_MINUTES` (default 30).
