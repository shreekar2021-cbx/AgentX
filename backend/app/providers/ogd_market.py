"""Official OGD/data.gov.in AGMARKNET resource adapter; requires an API key."""

from datetime import datetime

import httpx

from app.core.config import Settings
from app.schemas.phase3 import MarketQuote


class MarketProviderError(Exception):
    pass


class OGDMarketProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def quotes(self, commodity: str) -> list[MarketQuote]:
        if not self.settings.ogd_api_key:
            raise MarketProviderError("missing_api_key")
        url = f"https://api.data.gov.in/resource/{self.settings.ogd_market_resource_id}"
        params = {"api-key": self.settings.ogd_api_key, "format": "json", "limit": 500, "filters[commodity]": commodity, "filters[state]": "Telangana"}
        try:
            response = await self.client.get(url, params=params, timeout=self.settings.market_timeout_seconds)
            response.raise_for_status()
            body = response.json()
            records = body["records"]
            if not isinstance(records, list):
                raise ValueError("records_missing")
            normalized: list[MarketQuote] = []
            for row in records:
                try:
                    raw_date = str(row["arrival_date"])
                    try:
                        arrival = datetime.strptime(raw_date, "%d/%m/%Y").date()
                    except ValueError:
                        arrival = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    low, high, modal = float(row["min_price"]), float(row["max_price"]), float(row["modal_price"])
                    if low <= 0 or high <= 0 or modal <= 0 or not low <= modal <= high:
                        continue
                    normalized.append(MarketQuote(
                        commodity=str(row["commodity"]), variety=str(row.get("variety") or "Unspecified"),
                        state=str(row["state"]), district=str(row["district"]), mandi=str(row["market"]),
                        min_price=low, max_price=high, modal_price=modal, date=arrival,
                        source="LIVE", is_synthetic=False,
                        provenance="Government of India OGD / AGMARKNET daily mandi resource",
                    ))
                except (KeyError, TypeError, ValueError):
                    continue
            if not normalized:
                raise MarketProviderError("no_valid_records")
            return normalized
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise MarketProviderError("provider_unavailable") from exc
