# AgriVision AI — Phase 2 complete

## Completed features

- Connected the existing Report Problem → FastAPI report creation → streamed analysis stages → Crop Result flow. My Reports, Weather, and Nearby Alerts now read typed API responses while preserving the Phase 1 shell and visual language.
- Added owner-scoped report listing, report detail, and image routes; multipart image checks for MIME, signature, full decode, 10 MB maximum, and 30 million pixel maximum; safe errors; atomic analysis claim; idempotent completed-result return; and a persistent hourly analysis limit.
- Implemented browser or manual coordinates, coordinate validation, Haversine distance, a configurable 10 km default radius, nearby matching by crop/issue/recency/severity/distance, and coarse public cluster centers requiring three distinct owners.
- Implemented deterministic individual/community risk scoring and conservative outbreak signals. Low-confidence findings cannot trigger a cluster alert. Synthetic matches never raise a real community score; synthetic and real clusters are aggregated separately and labelled.
- Added a durable local SQLite development adapter with report/image storage, AI and weather caches, rate windows, and synthetic seed data. The fixed development identity is disabled when Supabase is configured or `APP_ENV=production`.

## Mistral implementation

`MistralProvider` is the sole application AI adapter behind the `AIProvider` protocol. It sends image plus field text and context to the vision model using Mistral chat completions, requests a strict JSON schema, and validates output with Pydantic. It handles missing keys, 429, timeouts, network errors, unavailable models, malformed JSON, and invalid schema output. Transient errors receive bounded exponential retries. Model results are cached by image/report input plus season and weather context; a hit is labelled `AI CACHED`.

Configured defaults: `MISTRAL_MODEL_GENERAL=mistral-medium-latest`, `MISTRAL_MODEL_FAST=ministral-8b-latest`, and `MISTRAL_MODEL_VISION=mistral-small-latest`. Only the vision model is called in Phase 2. The model ID and timeout/retry settings are configurable. With no Mistral key or a failed provider, `CropHealthAgent` returns `LOCAL KNOWLEDGE` or `LIMITED MODE`, caps text match strength, sets `image_assessed=false`, and states that the image was not analyzed. The UI calls the output a possible issue and requests expert verification. See [Mistral vision](https://docs.mistral.ai/studio/conversations/vision) and [structured output](https://docs.mistral.ai/studio/conversations/structured-output/custom).

## Provider and knowledge fallback

`WeatherService` uses [Open-Meteo](https://open-meteo.com/en/docs) current, hourly, and daily fields. A fresh cache is returned immediately; on a miss or expiry, the service requests live data. Failure returns a labelled stale cache or a local advisory with no invented current conditions. Responses include source, provider, observation/fetch timestamps, and stale status. The Weather screen displays [Open-Meteo attribution](https://open-meteo.com/en/terms).

The curated catalog covers 18 crops and 54 common pest, disease, or nutrient issue patterns with stages, seasons, symptoms, weather sensitivity, spread, prevention, monitoring, and provenance. It is static field triage knowledge, not official live data or a confirmed diagnosis. Reference material includes [TNAU IPM](https://agritech.tnau.ac.in/crop_protection/crop_prot_ipm.html) and [ICAR Kharif advisories](https://www.icar.gov.in/sites/default/files/2025-10/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf).

`scripts/generate_demo_data.py` uses a fixed seed and fixed default timestamp to produce 192 synthetic farmers, 192 farms, 384 reports, and eight geographic clusters plus outbreak scenarios. Every generated farmer, farm, report, and cluster is marked `is_synthetic=true`. Runtime local seeding refreshes timestamps for nearby demo examples; production mode never seeds or serves this dataset.

## Agent workflow

The orchestrator performs validation/claim → weather → crop health → nearby matching → risk → outbreak → persistence and streams real progress events. Distances, filtering, counts, thresholds, dates, and scores use deterministic Python. Mistral is used only for crop image/text interpretation. A failed or cancelled run is marked retryable; persisted results are returned on duplicate analysis calls.

## Verification

- Backend: **19 pytest tests passed**, covering Mistral success, 429 and bounded retry, unavailable/model errors, network/timeout, malformed and schema-invalid output, missing key, AI cache and local fallback; weather live/cache/stale/unavailable; Haversine; nearby owner exclusion, coarse privacy, synthetic labels; outbreak thresholds and distinct owners; upload decode/size; atomic claim, rate limit, owner-private image; end-to-end HTTP report streaming; and generator reproducibility.
- Frontend: `npm run build` and `npm run lint` passed after UI integration.
- Uvicorn started successfully. Direct HTTP smoke check returned health 200, crop catalog 200, report creation 201, analysis 200, private image 200, nearby alerts 200, and weather 200. The analysis source was correctly `LOCAL KNOWLEDGE` with no Mistral key; weather was `CACHED`.
- Generator wrote the expected 192 farmers, 192 farms, 384 reports, and eight clusters.

## Environment variables

Copy `backend/.env.example` to `backend/.env`. Relevant values: `APP_ENV`, `APP_CORS_ORIGINS`, `APP_MAX_UPLOAD_MB`, `MISTRAL_API_KEY`, `MISTRAL_MODEL_GENERAL`, `MISTRAL_MODEL_FAST`, `MISTRAL_MODEL_VISION`, `MISTRAL_TIMEOUT_SECONDS`, `MISTRAL_MAX_RETRIES`, `WEATHER_TIMEOUT_SECONDS`, `WEATHER_CACHE_MINUTES`, `NEARBY_RADIUS_KM`, `LOCAL_DATABASE_PATH`, `APP_SEED_DEMO_DATA`, and `ANALYSIS_RATE_LIMIT_PER_HOUR`. The frontend uses `VITE_API_BASE_URL` or the Vite `/api` proxy. Keep `MISTRAL_API_KEY` backend-only; do not add it to `VITE_` variables.

## Known limitations

- No Mistral credential was supplied, so the real hosted model call was validated with mocked HTTP responses; local end-to-end runs used the clearly labelled text-only fallback.
- No Supabase project/credentials were supplied. The authenticated Phase 2 Supabase report repository is not implemented or tested; configured/production report routes fail closed with 503 after auth instead of using the development identity. The Phase 1 migration has not been applied to a live project.
- The development UI has no production authentication flow. The local fixed identity and SQLite database must not be publicly exposed. Phase 1 pages outside the connected crop/weather/alert screens still display synthetic examples.
- Open-Meteo's free API has [noncommercial terms](https://open-meteo.com/en/terms); confirm a production license or provider before commercial deployment.
- Browser automation did not expose a browser in this environment, so visual and device interaction QA remains to be done before release. The weather/provider tests use mocked live responses; the direct smoke check returned an existing weather cache entry.

## Phase 3 handoff

Start by adding a production repository using authenticated user-scoped storage, private image access, shared cache/rate limits, safe nearby aggregation, and verified RLS. Add sign-in UI and production provider licensing before real farmers use the report flow. Keep source, freshness, and synthetic labels in every new surface. Then build only the Phase 3 features requested in the next phase; market, seed/fertilizer agents, PWA/offline sync, notifications, voice, and final audit were deliberately not implemented here.
