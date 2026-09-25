# AgriVision AI

AgriVision is a farm field intelligence demo built with React, TypeScript, Vite, FastAPI, and SQLite. A farmer can submit a crop photo and symptoms, view a source-labelled possible issue, weather, nearby reports, risk and cluster signals, compare dated mandi observations, save farm and soil context, and get conservative seed and nutrient guidance. IndexedDB keeps report submissions while the browser is offline.

The application is **hackathon demo ready on localhost** with `DEMO_MODE=true`. Its fixed-seed sample farmers, farms, reports, clusters, notifications, and mandi prices are synthetic and labelled. Open-Meteo can return live weather; a backend-only Mistral key enables image and text analysis and historical market direction; an OGD key enables official mandi observations. Each flow has an explicit fallback or unavailable state.

## Start locally

Requires Node.js 22+ and Python 3.11+. From the project root:

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
Copy-Item backend\.env.example backend\.env
```

In terminal 1:

```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In terminal 2, from the project root:

```powershell
npm run dev
```

Open `http://127.0.0.1:5173`. Check `http://127.0.0.1:8000/api/health` and API documentation at `/docs`. If port 8000 is occupied, set `VITE_DEV_PROXY_TARGET` to the alternate backend URL before starting Vite.

## Environment

`backend/.env.example` documents all backend settings. The minimum demo values are `APP_ENV=development` and `DEMO_MODE=true`. `APP_SEED_DEMO_DATA=true` populates the local SQLite workspace. Optional `MISTRAL_API_KEY` and `OGD_API_KEY` stay in `backend/.env`; never put them in a `VITE_` variable. Open-Meteo needs no key. The root `.env.example` documents the optional frontend API base URL and dev proxy target. Local `.env` files and SQLite data are ignored by `.gitignore`.

`DEMO_MODE=false` disables the fixed demo identity. Protected routes then require a valid Supabase JWT and fail closed with 503 because a production repository and sign-in UI are not implemented. `APP_ENV=production` rejects demo mode and insecure CORS origins at startup. Do not expose the localhost demo server to the public internet.

## Build and tests

```powershell
npm run test
npm run lint
npm run build
cd backend
..\.venv\Scripts\python -m pytest -q
```

`npm run build` runs TypeScript and creates `dist/`, the manifest, and the service worker. The PWA precaches the app shell and essential crop knowledge; private API data and uploaded images are excluded. A disconnected report and image remain in the browser's IndexedDB until replay succeeds. Server-side `client_mutation_id` prevents duplicate reports. Keep browser site data until the queue is empty.

## Architecture and release boundary

The FastAPI report orchestrator coordinates a crop health agent, weather service, nearby report matching, deterministic risk assessment, conservative outbreak detection, and persistent in-app notifications. The market agent summarizes a dated history when Mistral is available; net return and agronomic rule checks are deterministic. Source, observed time, freshness, and synthetic status are exposed in API responses and screens.

The Supabase migration provides a future production schema with RLS, ownership relationships, indexes, and a private image bucket. It has not been applied or live-tested here. The runtime's authenticated production repository, production image storage, sign-in UX, shared production rate limiting, and deployment verification remain outstanding. This repository must not be described as production deployed.

Read [SETUP.md](SETUP.md) for configuration and deployment gates, [ARCHITECTURE.md](ARCHITECTURE.md) for data flow and agent boundaries, [DATA_SOURCES.md](DATA_SOURCES.md) for provenance, [DEMO_GUIDE.md](DEMO_GUIDE.md) for a five-minute walkthrough, and [PROJECT_COMPLETE.md](PROJECT_COMPLETE.md) for the final verification record. Historical phase handoffs remain in `PHASE_1_COMPLETE.md`, `PHASE_2_COMPLETE.md`, and `PHASE_3_COMPLETE.md`.
