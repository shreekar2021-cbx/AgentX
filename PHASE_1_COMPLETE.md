# AgriVision AI — Phase 1 complete

## Completed

- Built the React/Vite/TypeScript application with Tailwind, React Router, Zustand, TanStack Query, Framer Motion, Lucide, Recharts, and React Leaflet.
- Added a responsive dark farm intelligence shell with collapsible desktop sidebar, command search, mobile drawer and bottom navigation.
- Added Home, Report Problem, Crop Result, My Crops, Nearby Alerts, My Reports, Market Intelligence, Seed & Fertilizer, Admin Dashboard, Farm Profile, Notifications, Settings, Weather, and Intelligence Center screens.
- Added local demo datasets, map markers and risk circles, market filters and charts, crop/report filters, a report image preview with camera input, validation, an illustrative result journey, and reusable source, severity, loading, and empty state components.
- Built a FastAPI application with Pydantic settings, safe CORS, request IDs, logging, global error handling, health and capability endpoints, and explicit HTTP 501 stubs for unavailable modules.
- Added Supabase user-scoped gateway and repository patterns, service and agent protocols, provider contracts, JWT/admin guard foundations, upload policy, and rate-limit interface.
- Created PostgreSQL/Supabase migration SQL with 21 tables, ownership foreign keys, indexes, RLS policies, private crop image storage, and Auth user mirroring.
- Wrote architecture and startup documentation. All local sample insights are labelled as demo content; no AI or live provider result is presented as real.

## Architecture Decisions

- One modular FastAPI monolith serves one React client. API → service → repository/provider is the dependency direction.
- PostgreSQL RLS is the ownership boundary. Normal database calls use the end user's JWT and the public anon key; the frontend must never receive a service-role key.
- `LIVE`, `CACHED`, `FALLBACK`, and `DEMO` are explicit source states. An unavailable provider must not silently yield invented intelligence.
- Demo data lives in `src/lib/demo.ts` and is consumed only by presentation screens. The API returns 501 for unfinished features.
- Offline sync and agent runs have schema/contracts only. No PWA, delivery integration, or intelligence is active.

## Important Files

- `ARCHITECTURE.md` — module relationships, data flow, contracts, security and future integration rules.
- `src/App.tsx` — shell, navigation, routes and search.
- `src/pages.tsx` — Phase 1 screens.
- `src/lib/demo.ts`, `src/lib/api.ts`, `src/lib/store.ts` — sample data, typed HTTP boundary and UI state.
- `src/components/UI.tsx`, `src/styles*.css` — shared UI and responsive design.
- `backend/app/main.py`, `backend/app/api/routes.py` — FastAPI setup and routes.
- `backend/app/core/`, `backend/app/providers/`, `backend/app/repositories/`, `backend/app/services/`, `backend/app/agents/` — contracts and backend boundaries.
- `supabase/migrations/202609260001_phase1_foundation.sql` — database migration.
- `README.md` — local setup.

## Commands

From the project root, in terminal 1:

```powershell
npm install
npm run dev
```

In terminal 2:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:5173`; health is `http://localhost:8000/api/health`. On this machine, ports 5173 and 8000 were occupied. The verified alternative was backend port 8001 and frontend port 5174 with `$env:VITE_DEV_PROXY_TARGET='http://127.0.0.1:8001'` before `npm run dev -- --port 5174`.

## Database

The migration is written and parsed successfully as PostgreSQL SQL. It has **not** been applied to Supabase because no project connection was supplied. PostGIS and Supabase Auth/Storage schemas are required in the target project. Apply the migration through the Supabase migration workflow and test RLS with real authenticated users before enabling data routes.

## Environment Variables

- Frontend: `VITE_API_BASE_URL` (optional API origin), `VITE_DEV_PROXY_TARGET` (optional local Vite proxy target).
- Backend: `APP_ENV`, `APP_LOG_LEVEL`, `APP_CORS_ORIGINS`, `APP_MAX_UPLOAD_MB`, `APP_RATE_LIMIT_PER_MINUTE`.
- Optional Supabase setup: `SUPABASE_URL`, `SUPABASE_ANON_KEY`. Do not expose a service-role key to the client.
- `backend/.env` contains local non-secret development defaults; `backend/.env.example` documents them.

## Tests

- `npm install` completed with no reported vulnerabilities.
- `npm run build` passed TypeScript and production Vite compilation; `npm run lint` passed.
- Uvicorn started on port 8001; direct `GET /api/health` and `GET /api/capabilities` passed. Vite on port 5174 served the frontend and local asset, and proxied `/api/health` successfully.
- `GET /api/analyses` and `POST /api/reports` returned the intended HTTP 501 contract. Allowed local CORS preflight passed; an unlisted origin received no allow-origin header.
- Upload policy accepted a PNG signature and rejected a MIME/content mismatch.
- PostgreSQL parser accepted the migration; all 21 public tables have RLS enabled.
- Browser automation exposed no available browser, so screenshot based visual QA could not be performed in this environment.

## Known Limitations

- Supabase has no configured project credentials and the migration has not been executed against a live project.
- Authentication UI, real farm/report persistence, AI, real weather/market data, notifications, voice, Telugu, and offline sync are future phases. The admin screen is a labelled demo preview and is not a production administration surface.
- Map base tiles require internet access. The farm image has a local SVG fallback.
- No browser screenshot or device interaction pass was possible here; validate visual layout in a browser before release.

## Phase 2 Instructions

Begin with Supabase migration application and RLS ownership tests, then wire authenticated farm/report APIs through existing service and repository interfaces. Replace `src/lib/demo.ts` screen by screen while preserving source and freshness labels. Add streaming upload validation and a shared rate limiter before any write endpoint goes live. Do not treat the Phase 1 result preview as a real diagnosis.
