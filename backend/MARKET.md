# MarketService

The only new route is `GET /api/market/prices?commodity_id=<uuid>&state=Telangana`. Optional filters are `district`, `variety`, `limit` (1–100; default 20), and opaque `cursor`. The query follows `ARCHITECTURE.md`; prediction, history, and ranking endpoints are outside this phase.

## Configure

Set `DATA_GOV_API_KEY` and `DATA_GOV_RESOURCE_ID` in the ignored `backend/.env` to enable the live [AGMARKNET dataset on data.gov.in](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi). The resource ID is the UUID of the chosen price resource from that catalog. Both values stay on the backend. Apply the existing Supabase migration and set its three credentials to enable commodity lookup and stored prices. No new migration is needed.

`MARKET_CSV_PATH` optionally points to the local fallback file; it defaults to `backend/data/market_prices.csv`. That file is created after a successful live fetch and is ignored by Git. [market_prices.example.csv](data/market_prices.example.csv) is the header template if you need to import a verified local snapshot yourself. Keep actual dates and sources when importing; do not label a sample or old price as current. The CSV can work without Supabase if its rows include the requested `commodity_id` and `commodity_code`.

## Result and source order

Success uses the existing `{data, meta}` envelope. `data.source_status` and `meta.sources[0].status` are exactly `LIVE`, `CACHED`, or `FALLBACK`:

1. `LIVE`: one data.gov.in/AGMARKNET request, with a total 3-second deadline. The adapter validates commodity, region, date, ordering, amounts, and units. Valid rows are saved to `mandis` and `market_prices` with idempotent upserts, and to the CSV snapshot. Cache write failures are warnings; the live result remains usable.
2. `CACHED`: on live failure or missing live configuration, read previously stored observations from Supabase `market_prices`. Preserve each original `price_date`, provider source, and `fetched_at`.
3. `FALLBACK`: if no database rows are available, read the local CSV snapshot. An absent/empty/invalid CSV yields a 503 dependency error. The service never fabricates prices.

Every price has the same shape from all three sources: canonical commodity ID/code, market identity and region, variety/grade, minimum/modal/maximum prices as decimal strings in INR per quintal, price date, provider source, fetch time, and `is_stale`. A price older than seven Indian calendar days is flagged stale. `data.as_of` is the newest observation date. A stale observation can be displayed as history but should not be used as a current ranking price. `next_cursor` supports subsequent pages.

The live feed requires a canonical commodity match. Supabase stores provider aliases in `commodities.provider_aliases`; CSV-only mode can derive a basic commodity name from an existing local row. Without Supabase metadata or a local row for the requested ID, the service cannot safely map the ID to a provider crop name and returns an unavailable response.

## Verify

From `backend/`:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -q
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The tests cover a successful normalized data.gov.in response, a forced provider failure served from Supabase, a forced provider and database failure served from CSV, invalid records, and a cold 503. Provider and Supabase transports are simulated because this workspace has no data.gov.in or Supabase credentials. Live integration requires those settings plus an applied migration. Keep HTTPX INFO request logging disabled: data.gov.in puts the API key in its URL.
