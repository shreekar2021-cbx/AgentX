# AgriVision Phase 4 checkpoint — 2026-09-26

## Application status

**Local hackathon demo ready. Production deployment is not ready.** Explicit `DEMO_MODE=true` runs a localhost SQLite workspace with labelled synthetic records and live provider calls when available. `APP_ENV=production` rejects demo mode; authenticated feature routes fail closed until a production repository and sign-in are implemented.

## Features implemented

- Crop report upload, MIME/size/pixel validation, private owner-scoped image retrieval, streamed analysis stages, Mistral vision or text-only fallback, weather context, nearby matching, deterministic risk, conservative cluster signal, persistent result and notifications.
- Market live/cache/stale/synthetic fallback, dated price charts, mandi comparison, optional Mistral historical direction, deterministic decimal net-return estimate.
- Saved farm/soil profile, crop portfolio, conservative seed and nutrient guidance, notification read state, provider health, synthetic geospatial admin map.
- PWA shell and curated crop reference precache; IndexedDB report and image queue, idempotent replay, automatic reconnect sync, retry, optional browser voice with text fallback.
- Connected home and intelligence screens; source and synthetic badges; responsive mobile/tablet layouts and reduced-motion CSS.
- Bundled generated cotton demo image marked synthetic throughout its report flow.

## Architecture

React/TypeScript/Vite SPA → typed FastAPI routes → orchestrator and specialized agents/services → Mistral, Open-Meteo, OGD, and owner-scoped SQLite development repository. Deterministic tools handle risk thresholds, soil rules, distance, and money. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Models used

Backend-only Mistral vision model `mistral-small-latest` for optional crop image analysis; `ministral-8b-latest` for optional market direction. Model names are configurable. Tests use mock provider responses. A live attempt during browser QA returned a labelled 429 fallback; successful live Mistral operation was **not** verified in this environment.

## Live APIs

[Open-Meteo](https://open-meteo.com/en/docs) weather was observed in the connected browser UI. Optional [Mistral](https://docs.mistral.ai/studio/conversations/vision) and [OGD mandi resource](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi) depend on backend keys and provider availability. No live Supabase deployment was available.

## Cached sources

SQLite caches AI result hashes, weather by rounded location, and market observations. Each cached response carries a source/freshness label; stale weather and market data are disclosed.

## Static datasets

18-crop/54-issue curated local knowledge and essential offline JSON. These are reference data, not live surveillance or a confirmed diagnosis.

## Synthetic datasets

Fixed seed `260926`: 192 farmers, 192 farms, 384 network reports, eight clusters, a demo farm/portfolio/sample report and notifications. Dated market fallback: 4,800 quotes across 16 commodities, 10 sample mandis, and 30 dates through 2026-08-31. The bundled generated cotton image is synthetic. Seeded records and fallbacks have explicit labels. Admin report counts can rise as the demo user submits more records.

## Environment variables

`backend/.env.example` is the source of truth. Required for local demo: `APP_ENV=development`, `DEMO_MODE=true`, `APP_SEED_DEMO_DATA=true`. Optional `MISTRAL_API_KEY` and `OGD_API_KEY` remain backend-only. `SUPABASE_URL`/`SUPABASE_ANON_KEY` alone do not complete production integration. Root `.env.example` controls optional Vite API base/proxy. Local `.env` and SQLite data are ignored by `.gitignore`.

## Frontend build result

`npm run build` **passed**: TypeScript and Vite 7.3.6, 2,699 modules transformed; PWA generated `dist/sw.js` and `dist/manifest.webmanifest`, 34 precache entries (1,140.56 KiB). `npm run lint` **passed**. `npm run test` **passed: 4 tests in 3 files**.

## Backend test result

`..\.venv\Scripts\python.exe -m pytest -q` from `backend` **passed: 32 tests**; one dependency deprecation warning from Starlette/TestClient. Uvicorn started on localhost. `/api/health`, demo overview, profile, reports, and provider health responded. Browser QA covered 42 route/viewport combinations at 390, 768, and 1440 pixels with no horizontal page overflow, missing headings, or page exceptions. Browser flow verified offline queue → reconnect → sync and a synthetic image submission → labelled crop result. A source scan found no obvious keys in application source; local `.env` contents were not displayed.

## Known external limitations

- Production Supabase repository, sign-in UX, private production image storage, applied migrations and live RLS verification are outstanding. The SQL schema was statically reviewed only.
- Shared multi-worker rate limiting, reverse-proxy request body limits, operational backups, and provider terms/licensing need a deployment environment.
- Mistral live success and OGD live prices were not verified; model/provider failures were verified through automated mocks and labelled browser fallback.
- Map base tiles and optional Web Speech may depend on connectivity/browser support. The generated demo photo is served online and excluded from the PWA precache.

## Demo instructions

Use [DEMO_GUIDE.md](DEMO_GUIDE.md). Start on the connected dashboard, load the synthetic sample image on Report Problem, inspect source labels in Crop Result, then show nearby clusters, market, soil guidance, offline queue/sync, and admin map. Never present synthetic observations as live farmer data.

## Deployment instructions

Follow [SETUP.md](SETUP.md) for localhost. Before a public release, implement and test the authenticated production repository and image storage, run migrations and two-user RLS checks in Supabase, configure HTTPS/CORS and provider terms, add shared rate limiting and proxy body limits, and repeat end-to-end tests against deployed services. Keep `DEMO_MODE=false` in production.
