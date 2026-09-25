# WeatherService

Only `GET /api/weather?lat=17.385&lng=78.4867` is added. It needs no Open-Meteo key and works without Supabase credentials. See [Open-Meteo's forecast contract](https://open-meteo.com/en/docs) for provider fields and units.

## Run and verify

From `backend/`, use the existing virtual environment:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
Invoke-RestMethod 'http://127.0.0.1:8000/api/weather?lat=17.385&lng=78.4867'
```

The access log is disabled in this example because request URLs contain location coordinates. Do not enable HTTPX INFO request logging in production for the same reason.

## Contract

Success uses the existing `{data, meta}` envelope:

- `data.location`: queried coordinates rounded to two decimal places (approximately 1 km).
- `data.timezone`: `UTC`; the seven forecast days are UTC dates, not local-calendar days.
- `data.current`: `temperature_c`, `humidity_pct`, `rain_mm`, `wind_kmh`, `observed_at`, `interval_seconds`, and `measurement_kind: model_estimate`. Rain covers the returned current interval; it is not a 24-hour or 48-hour total.
- `data.forecast_7day`: seven consecutive dated entries with `temperature_min_c`, `temperature_max_c`, `rain_mm`, and `wind_max_kmh`.
- `data.recent_observed_rain_48h_mm`: `null`. This integration does not supply historical station observations or treat forecast rainfall as observed evidence.
- `meta.sources[0]`: provider `open-meteo`, status `live|cached`, `observed_at`, `fetched_at`, `expires_at`, `is_stale`.
- `meta.warnings`: explicit provider/cache failures and `stale_weather` when applicable. The original fetch and expiry timestamps are preserved on cache reads.

Invalid/missing coordinates return the standard 422 error envelope. A provider failure without usable cache returns the standard 503 error envelope (`dependency_unavailable`, `retryable: true`). Provider diagnostics are not exposed.

## Reliability and cache

The adapter uses the application's shared async HTTP client. Each attempt has a 5-second total deadline and HTTP timeouts. At most one retry is allowed for transport timeouts/errors, 429, or 500/502/503/504. Backoff starts at 250 ms plus jitter; `Retry-After` is respected, including HTTP dates. A 12-second provider budget bounds both attempts and waiting; if a requested retry delay does not fit, the service falls back immediately. Invalid units, malformed/incomplete data, non-transient statuses, or outdated provider timestamps are not retried.

Weather is fresh for 30 minutes. After expiry, refresh is attempted; if refresh fails, a snapshot no more than 24 hours old may be returned with `is_stale: true`. Both fetch time and current-condition time are checked. Older snapshots are unavailable. Consumers must exclude stale weather from risk bonuses and weather-specific dosing advice.

The service has a 256-entry memory cache. With Supabase configured, it also reads/upserts normalized snapshots in the existing backend-only `service_cache` table using the service-role context. Keys include schema version, rounded coordinates, and timezone. Database operations have a 2-second deadline each; cache outages do not block live results. There is no new migration. Without Supabase, the cache lasts only for the current process. Persistence is best effort, not a readiness requirement.

No AI summary, geocoding, historical-observation API, farmer data writes, or demo substitution is introduced. The deterministic tests simulate provider outages, retries, malformed data, expired caches, persistent cache failures, and stale responses; they do not contact external services.
