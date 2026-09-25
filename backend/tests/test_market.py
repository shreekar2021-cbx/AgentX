"""Market source priority and normalization checks with no external credentials."""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock
from uuid import UUID

import httpx

from app.adapters.market import DataGovMarketAdapter
from app.api.market import get_market_service
from app.config import Settings
from app.database import SupabaseConnection
from app.main import create_app
from app.repositories.market import SupabaseMarketRepository
from app.repositories.market_csv import CsvMarketRepository
from app.schemas.market import CommodityIdentity, MarketPrice, MarketQuery
from app.services.market import MarketService

COMMODITY_ID = UUID("11111111-1111-4111-8111-111111111111")
RESOURCE_ID = "22222222-2222-4222-8222-222222222222"


def query() -> MarketQuery:
    return MarketQuery(commodity_id=COMMODITY_ID, state="Telangana", limit=20)


def commodity() -> CommodityIdentity:
    return CommodityIdentity(
        id=COMMODITY_ID, code="tomato", name_en="Tomato",
        provider_aliases={"data.gov.in": ["Tomato"]},
    )


def live_payload():
    return {"total": 1, "records": [{
        "_id": 42, "state": "Telangana", "district": "Warangal",
        "market": "Warangal", "commodity": "Tomato", "variety": "Local",
        "grade": "FAQ", "arrival_date": date.today().strftime("%d/%m/%Y"),
        "min_price": "2,100", "max_price": "2,800", "modal_price": "2450",
    }]}


class MarketServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.csv = CsvMarketRepository(Path(self.temp.name) / "prices.csv")
        self.requests = []
        self.status = 200
        self.payload = live_payload()

        def respond(request):
            self.requests.append(request)
            return httpx.Response(self.status, json=self.payload)

        self.provider_http = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        self.addAsyncCleanup(self.provider_http.aclose)
        self.adapter = DataGovMarketAdapter(
            self.provider_http, api_key="private-test-key", resource_id=RESOURCE_ID
        )
        self.database = AsyncMock()
        self.database.get_commodity.return_value = commodity()
        self.database.get_prices.return_value = ([], False)
        self.service = MarketService(self.adapter, self.database, self.csv)
        app = create_app(Settings(_env_file=None, supabase_url=None,
                                  supabase_anon_key=None, supabase_service_key=None))
        app.dependency_overrides[get_market_service] = lambda: self.service
        self.api = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        self.addAsyncCleanup(self.api.aclose)

    async def get(self):
        return await self.api.get("/api/market/prices", params={
            "commodity_id": str(COMMODITY_ID), "state": "Telangana"
        })

    async def test_live_normalizes_and_saves_both_caches(self):
        response = await self.get()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["source_status"], "LIVE")
        self.assertEqual(body["meta"]["sources"][0]["status"], "LIVE")
        self.assertEqual(body["meta"]["sources"][0]["provider"], "data.gov.in/AGMARKNET")
        row = body["data"]["prices"][0]
        self.assertEqual((row["min_price"], row["modal_price"], row["max_price"]),
                         ("2100", "2450", "2800"))
        self.assertEqual((row["currency"], row["unit"]), ("INR", "quintal"))
        self.assertEqual(row["price_date"], date.today().isoformat())
        self.assertFalse(row["is_stale"])
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].url.params["api-key"], "private-test-key")
        self.assertEqual(self.requests[0].url.params["filters[commodity]"], "Tomato")
        self.assertEqual(self.requests[0].extensions["timeout"]["read"], 3)
        self.database.save_prices.assert_awaited_once()
        self.assertEqual((await self.csv.get_prices(query()))[0][0].modal_price, Decimal("2450"))

    async def test_forced_failure_uses_supabase_cache_then_csv(self):
        await self.get()  # Persist a verified snapshot for both lower tiers.
        cached_row = (await self.csv.get_prices(query()))[0][0]
        self.status = 503
        self.database.get_prices.return_value = ([cached_row], False)
        cached = await self.get()
        self.assertEqual(cached.status_code, 200)
        self.assertEqual(cached.json()["data"]["source_status"], "CACHED")
        self.assertEqual(cached.json()["meta"]["sources"][0]["provider"], "supabase")
        self.database.get_prices.side_effect = RuntimeError("forced database failure")
        fallback = await self.get()
        self.assertEqual(fallback.status_code, 200)
        self.assertEqual(fallback.json()["data"]["source_status"], "FALLBACK")
        self.assertEqual(fallback.json()["meta"]["sources"][0]["status"], "FALLBACK")
        self.assertEqual(fallback.json()["meta"]["sources"][0]["provider"], "local_csv")
        self.assertIn("market_local_fallback", [w["code"] for w in fallback.json()["meta"]["warnings"]])
        self.assertEqual(fallback.json()["data"]["prices"][0]["price_date"], cached_row.price_date.isoformat())

    async def test_csv_fallback_works_without_database_or_api_key(self):
        await self.get()
        self.service = MarketService(None, None, self.csv)
        result = await self.get()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["data"]["source_status"], "FALLBACK")

    async def test_cold_failure_returns_503(self):
        self.status = 503
        response = await self.get()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "dependency_unavailable")

    async def test_rejects_bad_unit_price_and_filter(self):
        for mutation in (
            {"unit": "INR/kg"},
            {"modal_price": "3000"},
            {"arrival_date": "01/01/2099"},
            {"state": "Other"},
        ):
            with self.subTest(mutation=mutation):
                self.payload = live_payload()
                self.payload["records"][0].update(mutation)
                result = await self.get()
                self.assertEqual(result.status_code, 503)
        self.assertEqual((await self.api.get("/api/market/prices", params={
            "commodity_id": str(COMMODITY_ID), "state": " ", "limit": 101,
        })).status_code, 422)

    async def test_old_local_price_is_marked_stale(self):
        await self.get()
        rows, _ = await self.csv.get_prices(query())
        old = rows[0].model_copy(update={"price_date": date.today() - timedelta(days=8)})
        stale_csv = CsvMarketRepository(Path(self.temp.name) / "old.csv")
        await stale_csv.save_prices([old])
        self.service = MarketService(None, None, stale_csv)
        result = await self.get()
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()["data"]["is_stale"])
        self.assertTrue(result.json()["data"]["prices"][0]["is_stale"])


class SupabaseMarketRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_then_read_normalized_prices(self):
        now = datetime.now(timezone.utc)
        price = MarketPrice(
            commodity_id=COMMODITY_ID, commodity_code="tomato",
            provider_key="agmarknet:telangana:warangal:warangal",
            market_name="Warangal", district="Warangal", state="Telangana",
            variety_code="Local", grade="FAQ", min_price="2100",
            max_price="2800", modal_price="2450", price_date=date.today(),
            source="data.gov.in/AGMARKNET", fetched_at=now,
        )
        mandi_id = "33333333-3333-4333-8333-333333333333"
        stored = {}

        def respond(request):
            import json
            if request.url.path.endswith("/mandis") and request.method == "POST":
                return httpx.Response(201, json=[{"id": mandi_id, "provider_key": price.provider_key}])
            if request.url.path.endswith("/market_prices") and request.method == "POST":
                self.assertIn("mandi_id,commodity_id", request.url.params["on_conflict"])
                stored.update(json.loads(request.content)[0])
                return httpx.Response(201, json=[stored])
            if request.url.path.endswith("/market_prices") and request.method == "GET":
                self.assertEqual(request.url.params["mandis.state"], "eq.Telangana")
                return httpx.Response(200, json=[{
                    **stored,
                    "mandis": {"provider_key": price.provider_key, "market_name": "Warangal",
                               "district": "Warangal", "state": "Telangana"},
                    "commodities": {"code": "tomato"},
                }])
            raise AssertionError(f"Unexpected Supabase request: {request.method} {request.url.path}")

        settings = Settings(_env_file=None, supabase_url="https://example.supabase.co",
                            supabase_anon_key="anon", supabase_service_key="service")
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            repo = SupabaseMarketRepository(SupabaseConnection(settings, client))
            await repo.save_prices([price])
            rows, more = await repo.get_prices(query())
        self.assertFalse(more)
        self.assertEqual(rows[0].modal_price, Decimal("2450"))
        self.assertEqual(rows[0].mandi_id, UUID(mandi_id))


if __name__ == "__main__":
    unittest.main()
