"""Canonical commodity lookup and stored AGMARKNET price history."""

import asyncio
from datetime import date
from uuid import UUID

from app.database import SupabaseConnection
from app.schemas.market import CommodityIdentity, MarketCommodity, MarketPrice, MarketQuery


class SupabaseMarketRepository:
    def __init__(self, connection: SupabaseConnection) -> None:
        self._connection = connection

    async def get_commodity(self, commodity_id: UUID) -> CommodityIdentity | None:
        async with asyncio.timeout(2):
            client = await self._connection.service_client()
            result = await (client.table("commodities")
                            .select("id,code,name_en,provider_aliases")
                            .eq("id", str(commodity_id)).limit(1).execute())
        return CommodityIdentity.model_validate(result.data[0]) if result.data else None

    async def get_commodities(self) -> list[MarketCommodity]:
        async with asyncio.timeout(2):
            client = await self._connection.service_client()
            result = await (client.table("commodities").select("id,code,name_en")
                            .order("name_en").limit(100).execute())
        return [MarketCommodity.model_validate(row) for row in result.data or []]

    async def get_mandi_details(self, provider_keys: list[str]) -> dict[str, dict]:
        if not provider_keys:
            return {}
        async with asyncio.timeout(2):
            client = await self._connection.service_client()
            result = await (client.table("mandis").select("id,provider_key,latitude,longitude")
                            .in_("provider_key", provider_keys).execute())
        return {row["provider_key"]: row for row in result.data or []}

    async def get_prices(self, query: MarketQuery) -> tuple[list[MarketPrice], bool]:
        async with asyncio.timeout(2):
            client = await self._connection.service_client()
            builder = (client.table("market_prices")
                       .select("commodity_id,mandi_id,variety_code,grade,min_price,max_price,modal_price,currency,unit,price_date,source,source_record_id,fetched_at,original_unit,mandis!inner(id,provider_key,market_name,district,state,latitude,longitude),commodities!inner(code)")
                       .eq("commodity_id", str(query.commodity_id))
                       .eq("mandis.state", query.state)
                       .order("price_date", desc=True))
            if query.district:
                builder = builder.eq("mandis.district", query.district)
            if query.variety:
                builder = builder.eq("variety_code", query.variety)
            result = await builder.range(query.offset, query.offset + query.limit).execute()
        rows: list[MarketPrice] = []
        for record in result.data or []:
            mandi, commodity = record["mandis"], record["commodities"]
            rows.append(MarketPrice.model_validate({
                **{key: value for key, value in record.items() if key not in {"mandis", "commodities"}},
                **{key: value for key, value in mandi.items() if key not in {"latitude", "longitude"}},
                "mandi_latitude": mandi["latitude"],
                "mandi_longitude": mandi["longitude"],
                "commodity_code": commodity["code"],
            }))
        return rows[:query.limit], len(rows) > query.limit

    async def get_history(
        self,
        commodity_id: UUID,
        from_date: date,
        *,
        mandi_id: UUID | None = None,
        variety: str | None = None,
        grade: str | None = None,
    ) -> list[MarketPrice]:
        async with asyncio.timeout(3):
            client = await self._connection.service_client()
            builder = (client.table("market_prices")
                       .select("commodity_id,mandi_id,variety_code,grade,min_price,max_price,modal_price,currency,unit,price_date,source,source_record_id,fetched_at,original_unit,mandis!inner(id,provider_key,market_name,district,state,latitude,longitude),commodities!inner(code)")
                       .eq("commodity_id", str(commodity_id))
                       .gte("price_date", from_date.isoformat())
                       .order("price_date", desc=True).limit(1000))
            if mandi_id:
                builder = builder.eq("mandi_id", str(mandi_id))
            if variety:
                builder = builder.eq("variety_code", variety)
            if grade:
                builder = builder.eq("grade", grade)
            result = await builder.execute()
        rows: list[MarketPrice] = []
        for record in result.data or []:
            mandi, commodity = record["mandis"], record["commodities"]
            rows.append(MarketPrice.model_validate({
                **{key: value for key, value in record.items() if key not in {"mandis", "commodities"}},
                "mandi_latitude": mandi["latitude"], "mandi_longitude": mandi["longitude"],
                **{key: value for key, value in mandi.items() if key not in {"latitude", "longitude"}},
                "commodity_code": commodity["code"],
            }))
        return rows

    async def save_prices(self, prices: list[MarketPrice]) -> None:
        """Upsert provider identities and observations; each call is idempotent."""
        if not prices:
            return
        async with asyncio.timeout(2):
            client = await self._connection.service_client()
            mandis = {
                price.provider_key: {
                    "provider_key": price.provider_key, "market_name": price.market_name,
                    "district": price.district, "state": price.state,
                } for price in prices
            }
            saved_mandis = await client.table("mandis").upsert(
                list(mandis.values()), on_conflict="provider_key"
            ).execute()
            ids = {row["provider_key"]: row["id"] for row in saved_mandis.data or []}
            if len(ids) != len(mandis):
                raise ValueError("Mandi upsert did not return every ID")
            records = []
            for price in prices:
                records.append({
                    "mandi_id": ids[price.provider_key],
                    "commodity_id": str(price.commodity_id),
                    "variety_code": price.variety_code, "grade": price.grade,
                    "min_price": str(price.min_price), "max_price": str(price.max_price),
                    "modal_price": str(price.modal_price), "currency": "INR", "unit": "quintal",
                    "price_date": price.price_date.isoformat(), "source": price.source,
                    "source_record_id": price.source_record_id,
                    "fetched_at": price.fetched_at.isoformat(),
                    "original_unit": price.original_unit,
                })
            await client.table("market_prices").upsert(
                records,
                on_conflict="mandi_id,commodity_id,variety_code,grade,price_date,source",
            ).execute()
