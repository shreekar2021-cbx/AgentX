# AgriVision AI — Phase 3 complete

## Completed features

- Replaced the Phase 1 market, farm profile, crop portfolio, seed/fertilizer, notifications, admin health, and settings previews with API-backed screens while retaining the existing dark responsive shell. Phase 2 report, result, weather, and nearby alert screens remain connected.
- Added owner-scoped local persistence for partial farm/soil profiles, crop portfolio entries, and in-app notifications. My Crops links the latest matching field report and risk score, displays a short report timeline, and stores a farmer-authored next action.
- Added English, Telugu, and Hindi local interface dictionaries for navigation and essential report/settings actions. The selected language persists on the device. Long agricultural result text remains in its original source language.
- Added browser Web Speech recognition behind `src/lib/voice.ts` for English, Telugu, and Hindi where supported. The farmer can edit the transcription and must choose to add it to symptoms; typing always remains available.

## Market providers and dataset

`OGDMarketProvider` calls the Government of India [daily mandi resource](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi) when `OGD_API_KEY` is configured. It normalizes commodity, variety, state, district, mandi, min/max/modal price, and observation date. The service returns fresh cache, then live API data on cache miss, then stale cache, then a dated local fallback. Every response carries `LIVE`, `CACHED`, or `FALLBACK`, observed/fetched dates, stale status, provenance, and `is_synthetic`.

The fallback dataset in `backend/app/knowledge/market_demo.json` contains **4,800 fixed-seed synthetic observations**: 16 commodities × 10 sample mandis × 30 days ending 31 August 2026. `scripts/generate_market_data.py` regenerates it. The UI prominently labels these prices as dated synthetic examples, not current official quotes. Approximate sample coordinates support demo distances; real provider records without coordinates show distance as unknown.

The Market screen offers commodity and district filters, nearby mandi list, two-mandi price comparison, 7/30-day historical charts, source/timestamps, and a return estimator. `MarketIntelligenceAgent` sends normalized recent history to the backend-only Mistral adapter to classify `RISING`, `STABLE`, or `FALLING`. It validates the structured response, caches it, and rate limits model calls. If Mistral is unavailable, a labelled deterministic history rule provides the direction. No future price is guaranteed. Python `Decimal` calculates quantity-based gross revenue, transport, handling, storage, estimated spoilage, total cost, and estimated net return from farmer-entered values.

## Farm and recommendation architecture

Farm profiles store crop, season, soil type, pH, N/P/K values with explicit kg/ha fields, micronutrient values, farmer-supplied lab categories, previous crop, irrigation, area, budget, planting date, and coordinates. All are optional; missing measurements remain unknown.

`SeedRecommendationAgent` uses curated crop seasons and supplied farm/weather context to recommend suitability characteristics and review points. It does not invent commercial brands. `FertilizerAgent` records measured values but only identifies a possible nutrient deficiency from a supplied **low** laboratory category. It offers priorities, soil considerations, general corrective direction, and monitoring without exact chemical doses. Both expose missing inputs and provenance.

## Notifications, PWA, offline sync, and voice

`NotificationService` stores report completion notifications in SQLite. Delivery failure is caught so crop analysis still completes. Notifications can be marked read. The provider health UI shows recent Mistral, weather, market, database, and notification states as Healthy, Degraded, Cached, Fallback, or Unavailable; it summarizes observed operations rather than running continuous external probes.

`vite-plugin-pwa` generates an installable manifest and service worker. The build precaches the app shell, icons, and `public/knowledge/essential-crops.json`; the crop list reads this curated file when the API is offline. Private API data and images are not service-worker cached. The top bar shows online/offline state and queued count.

Offline reports and images are saved in IndexedDB as **Waiting to Sync**. Reconnection or the My Reports action retries each item. The queue stores the server ID before analysis, preserves failed items, and removes entries only after completion. A stable `client_mutation_id` and unique owner-scoped SQLite index prevent duplicate report creation; changed content under the same ID returns 409. Speech input is optional and browser-dependent. [MDN](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition) notes limited Web Speech support and possible remote audio processing, so offline speech is not promised.

## Verification

- **29 backend tests passed**: OGD live normalization; market cache, stale cache, and synthetic fallback; Mistral and deterministic trend paths; exact financial calculations; farm, soil, portfolio, and notification persistence; recommendation behavior with partial data; notification failure isolation; offline replay idempotency/conflict; Phase 3 HTTP flow; and the Phase 2 crop/weather/security tests.
- **4 frontend tests passed**: offline report storage, failed sync recovery and online resynchronization without duplicate POST, voice fallback and language selection, and use of the precached crop catalog during API outage.
- `npm run lint` and `npm run build` passed. The PWA build generated `dist/sw.js`, `dist/manifest.webmanifest`, and 40 precache entries; the service worker manifest includes both icons, `index.html`, and the essential crop JSON.
- Uvicorn started successfully. Direct HTTP requests returned health 200, market prices 200 with `FALLBACK`/`is_synthetic=true`, farm profile 200, and provider health 200.

## Environment and limitations

Backend additions: `OGD_API_KEY`, `OGD_MARKET_RESOURCE_ID`, `MARKET_CACHE_MINUTES`, `MARKET_TIMEOUT_SECONDS`, and `MARKET_TREND_RATE_LIMIT_PER_HOUR`; existing Mistral, Open-Meteo, Supabase, local database, and report settings remain in `backend/.env.example`. Do not put provider keys in `VITE_` variables.

- No OGD or Mistral key was supplied. Live market and model paths were tested with mocked HTTP responses; local operation used labelled synthetic market data and deterministic trend guidance.
- No Supabase project was connected. The authenticated production repository, sign-in UI, migration application, and RLS verification remain open. Protected Phase 2/3 routes fail closed when local demo mode is disabled; the fixed development identity and SQLite store must not be exposed publicly.
- Open-Meteo's [free API terms](https://open-meteo.com/en/terms) need licensing review before commercial deployment. Synthetic prices and crop clusters are demonstrations, not live market or surveillance evidence.
- PWA offline use requires an initial successful visit and browser support. Clearing site data removes unsynced IndexedDB reports. Speech support varies by browser and language. A browser automation surface was unavailable here, so screenshot/device visual QA remains open.
- The Phase 1 Home and Intelligence preview content still contains explicit demo examples. Production auth, licensed providers, real-user operations, and final repository audit are outside Phase 3.

## Phase 4 handoff

Only after an explicit Phase 4 request: connect authenticated production persistence and private storage with tested RLS; verify provider licenses and real-key integration; perform browser/device, accessibility, offline/PWA, and deployment QA; then audit and polish the repository. Do not infer real farm health or market prices from synthetic fallback content.
