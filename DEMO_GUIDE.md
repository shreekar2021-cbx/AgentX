# Five-minute hackathon demo

## Before the room opens

Start the backend and frontend using [SETUP.md](SETUP.md). Keep `DEMO_MODE=true` and `APP_SEED_DEMO_DATA=true`. Check `/api/health` returns `demo_mode: true`. Visit the app online once so the PWA shell can install. Have a Chrome or Edge browser ready and keep the local network available for map tiles and optional weather. Use a private browser profile if you want an empty offline queue.

The report screen has a **Load synthetic sample** button. It loads the bundled generated cotton leaf image with visible whitefly-like insects (`public/demo/cotton-whitefly-synthetic.png`); its report is labelled synthetic. You can use a real crop photo instead, with the owner's consent. Never describe the bundled image as a real field photograph.

If `MISTRAL_API_KEY` is configured in `backend/.env`, the app tries backend Mistral vision. It may still use a labelled fallback if the provider fails. Without a key, the entire demo still runs with text-only local knowledge. `OGD_API_KEY` is optional; the market fallback is dated synthetic data.

## Presenter sequence

| Time | Screen and action | What to say |
| --- | --- | --- |
| 0:00–0:35 | Home | “This is one field workspace. The seeded farm and network records are synthetic; the counts come from the API.” Point to reports, clusters, weather source, market source, and waiting-to-sync. |
| 0:35–1:35 | Report Problem | Load the synthetic sample, enter “Small white insects beneath cotton leaves and yellow speckling,” keep the Shamshabad/Rangareddy coordinates, then submit. Explain that the image and text go to Mistral only when the backend key and provider are available. |
| 1:35–2:15 | Crop Result | Read the source pill first. If `AI LIVE`, explain the image was assessed. If `LOCAL KNOWLEDGE`, explain that the image was **not** assessed and the result is a low-confidence text match. Show weather provenance, nearby matches, deterministic risk, expert verification, and the labelled synthetic cluster evidence. |
| 2:15–2:45 | Nearby Alerts and Notifications | Show the map's coarse synthetic cotton cluster and the in-app sample alert. A strong live analysis can create a possible-cluster notification; the fallback deliberately cannot. These are signals for verification, not confirmed outbreaks. |
| 2:45–3:30 | Market | Show dated modal prices, 7/30-day chart, nearby mandi comparison, and the `FALLBACK · SYNTHETIC` badge if OGD is unavailable. Request a trend summary, then enter quantity and costs for the deterministic estimated net return. Avoid implying the sample price is current. |
| 3:30–4:00 | Farm Profile and Seed & Fertilizer | Show the labelled sample soil profile and saved crop fields. Open recommendations; point out missing-input notes and that no exact fertilizer dose or product is fabricated. |
| 4:00–4:35 | Offline resilience | While on Report Problem, disconnect the browser in DevTools Network (or use the browser's offline control). Enter a new observation and submit. My Reports shows **Waiting to Sync** from IndexedDB. Reconnect and show automatic sync, or press Sync now. The entry clears after analysis. |
| 4:35–5:00 | Admin dashboard | Show 192 synthetic farmers, 192 farms, eight clusters, the geospatial map, and recent provider health. Explain these are reproducible demo metrics, not production surveillance. |

## Reliable fallback talking points

- Mistral 429, timeout, missing key, or invalid JSON: the result says `LOCAL KNOWLEDGE` or `LIMITED MODE`, states the image was not analyzed, and avoids an AI-backed outbreak signal.
- Weather failure: a stale cache is labelled, or the UI shows no current weather value. It does not invent a temperature.
- OGD failure: stale cache or dated synthetic fallback is labelled and carries an observation date.
- Notification persistence failure: report analysis still completes; provider health records the notification failure.
- Offline browser: the report and image wait in IndexedDB. Keep site data until synchronization finishes.
- Map tiles may not load offline; the cluster list and source labels still explain the data.

## Quick reset

Restarting the backend refreshes fixed-seed network report times and keeps local edits. For a clean personal demo workspace, use a new local SQLite path in `LOCAL_DATABASE_PATH` and a fresh browser profile; do not delete a database or browser site data that contains someone else's unsynced reports. The synthetic market file is regenerated with `python scripts/generate_market_data.py` when needed.
