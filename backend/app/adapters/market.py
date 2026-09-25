"""Bounded data.gov.in adapter for AGMARKNET wholesale price records."""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re

import httpx
from pydantic import ValidationError

from app.schemas.market import CommodityIdentity, MarketPrice, MarketQuery

DATA_GOV_BASE = "https://api.data.gov.in/resource"
SOURCE = "data.gov.in/AGMARKNET"


def _token(value: str) -> str:
    return " ".join(value.casefold().split())


def _fields(record: dict) -> dict[str, object]:
    return {str(key).strip().casefold().replace(" ", "_"): value for key, value in record.items()}


def _date(value: object) -> date:
    text = str(value).strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    raise ValueError("Unsupported market price date")


def _money(value: object) -> Decimal:
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError("Invalid market price") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Invalid market price")
    return amount


class DataGovMarketAdapter:
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, resource_id: str) -> None:
        self._client = client
        self._api_key = api_key
        self._resource_id = resource_id

    async def fetch_prices(
        self, query: MarketQuery, commodity: CommodityIdentity
    ) -> tuple[list[MarketPrice], bool]:
        """Make one request within three seconds; malformed pages fall through to cache."""
        params = {
            "api-key": self._api_key, "format": "json",
            "filters[commodity]": commodity.data_gov_names[0],
            "filters[state]": query.state,
            "limit": query.limit, "offset": query.offset,
        }
        if query.district:
            params["filters[district]"] = query.district
        if query.variety:
            params["filters[variety]"] = query.variety
        async with asyncio.timeout(3):
            response = await self._client.get(
                f"{DATA_GOV_BASE}/{self._resource_id}",
                params=params, timeout=3,
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
            raise ValueError("Invalid data.gov.in records")
        raw_rows = payload["records"]
        if not raw_rows:
            raise ValueError("No live market records")
        fetched_at = datetime.now(timezone.utc)
        prices: list[MarketPrice] = []
        for raw in raw_rows:
            try:
                price = self._normalize(raw, query, commodity, fetched_at)
            except (ValueError, TypeError, KeyError, ValidationError):
                continue
            if price is not None:
                prices.append(price)
        if not prices:
            raise ValueError("No valid live market records")
        total = payload.get("total")
        has_more = (
            isinstance(total, int) and total > query.offset + len(raw_rows)
        ) or (not isinstance(total, int) and len(raw_rows) == query.limit)
        return prices, has_more

    @staticmethod
    def _normalize(
        raw: dict, query: MarketQuery, commodity: CommodityIdentity, fetched_at: datetime
    ) -> MarketPrice | None:
        if not isinstance(raw, dict):
            raise ValueError("Malformed price record")
        row = _fields(raw)
        if _token(str(row["commodity"])) not in {_token(name) for name in commodity.data_gov_names}:
            return None
        if _token(str(row["state"])) != _token(query.state):
            return None
        district = str(row.get("district") or "").strip()
        if query.district and _token(district) != _token(query.district):
            return None
        variety = str(row.get("variety") or "unspecified").strip()
        if query.variety and _token(variety) != _token(query.variety):
            return None
        market = str(row["market"]).strip() if row["market"] is not None else ""
        if not market:
            raise ValueError("Missing market name")
        provider_unit = str(row.get("unit") or row.get("price_unit") or "INR/quintal").strip()
        if _token(provider_unit) not in {
            "inr/quintal", "rs./quintal", "rs/quintal", "rs/qtl", "₹/quintal"
        }:
            raise ValueError("Unsupported price unit")
        provider_key = "agmarknet:" + ":".join(
            re.sub(r"[^a-z0-9]+", "-", part.casefold()).strip("-")
            for part in (str(row["state"]), district, market)
        )
        return MarketPrice(
            commodity_id=commodity.id, commodity_code=commodity.code,
            provider_key=provider_key, market_name=market, district=district or None,
            state=str(row["state"]).strip(), variety_code=variety or "unspecified",
            grade=str(row.get("grade") or "unspecified").strip() or "unspecified",
            min_price=_money(row["min_price"]), max_price=_money(row["max_price"]),
            modal_price=_money(row["modal_price"]),
            price_date=_date(row["arrival_date"]), source=SOURCE,
            source_record_id=str(row.get("_id") or row.get("id") or "") or None,
            fetched_at=fetched_at, original_unit=provider_unit,
        )
