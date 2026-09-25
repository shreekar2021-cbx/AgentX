# Setup and deployment gates

## Local demo

1. Install Node.js 22+ and Python 3.11+.
2. From the project root run `npm install`, `python -m venv .venv`, and `.\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt`.
3. Copy `backend/.env.example` to `backend/.env`. Keep `APP_ENV=development`, `DEMO_MODE=true`, and `APP_SEED_DEMO_DATA=true`.
4. Start `cd backend; ..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
5. In a second terminal, from the root, run `npm run dev` and open `http://127.0.0.1:5173`.

The first backend startup creates `backend/.data/agrivision.sqlite3` and idempotently seeds 192 synthetic farmers, 192 farms, 384 network crop reports, eight clusters, a sample farm/portfolio/report, and two sample notifications. Startup refreshes network report times for a current demo; the generated identities and issue pattern use a fixed seed. Existing user edits to the demo profile and crop portfolio are preserved. The market fallback file has 4,800 fixed synthetic quotes dated through 2026-08-31.

The root `.env.example` documents `VITE_API_BASE_URL` and `VITE_DEV_PROXY_TARGET`. Keep `VITE_API_BASE_URL` empty for the dev proxy or same-origin deployment. Do not put private keys in any `VITE_` setting. Vite dev and preview bind to localhost by default.

## Optional providers

| Variable | Purpose |
| --- | --- |
| `MISTRAL_API_KEY` | Backend-only crop vision and market direction; blank gives labelled local fallback. |
| `MISTRAL_MODEL_VISION`, `MISTRAL_MODEL_FAST` | Model names used by those two tasks. |
| `OGD_API_KEY` | Optional Government of India mandi resource. Blank uses dated synthetic fallback. |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Future authenticated integration; setting these does not enable production feature persistence. |
| `APP_CORS_ORIGINS` | Exact allowed frontend origins. Production requires HTTPS origins. |
| `APP_MAX_UPLOAD_MB`, `APP_RATE_LIMIT_PER_MINUTE`, `ANALYSIS_RATE_LIMIT_PER_HOUR` | Upload and local demo limits. |

Open-Meteo does not need a key. Provider timeouts, retry counts, and cache periods are documented in `backend/.env.example` and `backend/app/core/config.py`.

## Validation commands

```powershell
npm run test
npm run lint
npm run build
cd backend
..\.venv\Scripts\python -m pytest -q
```

The backend health endpoint is `GET /api/health`; `/api/capabilities` states which flows are available. `npm run build` creates `dist/manifest.webmanifest`, `dist/sw.js`, and the app assets. A PWA needs an online first visit and service worker installation before offline shell loading. Browser site data holds unsynced image Blobs; clearing it loses the local queue.

## Production deployment gate

**Do not deploy this demo as a public authenticated service yet.** `APP_ENV=production` rejects `DEMO_MODE=true` and wildcard/non-HTTPS CORS. With demo off, protected routes require a JWT and return 503 because the runtime production repository and sign-in UX are unfinished. The Phase 1 Supabase SQL migration is a schema foundation only; it was not applied to a Supabase project in this workspace.

Before public deployment: implement the feature repository and private image storage using the caller's token and RLS; apply and test the SQL migration with two real users and an admin; verify provider credentials and terms; add a shared multi-worker rate limiter and reverse-proxy body limit; configure HTTPS, origin restrictions, backups, monitoring, and sign-in; run a full end-to-end test against that environment. Do not switch the local SQLite identity into production.
