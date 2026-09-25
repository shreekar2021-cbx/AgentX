"""Market guidance boundaries: deterministic money and constrained AI trend data."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import unittest
from uuid import UUID

import httpx
from pydantic import ValidationError

from app.adapters.gemini import GeminiAdapter
from app.agents.market_intelligence import MarketIntelligenceAgent
from app.schemas.market import MarketPrice, market_today
from app.schemas.market_intelligence import MarketGuidanceInput, MarketTrend

COMMODITY_ID = UUID("11111111-1111-4111-8111-111111111111")
MANDI_ID = UUID("22222222-2222-4222-8222-222222222222")
OTHER_MANDI_ID = UUID("33333333-3333-4333-8333-333333333333")


def price(*, mandi_id=MANDI_ID, days_ago=0, modal="2000", variety="Local", **changes):
    data = {
        "commodity_id": COMMODITY_ID,
        "commodity_code": "tomato",
        "mandi_id": mandi_id,
        "provider_key": f"agmarknet:{mandi_id}",
        "market_name": "Warangal Mandi",
        "district": "Warangal",
        "state": "Telangana",
        "variety_code": variety,
        "grade": "FAQ",
        "min_price": "1500",
        "max_price": "3000",
        "modal_price": modal,
        "price_date": market_today() - timedelta(days=days_ago),
        "source": "data.gov.in/AGMARKNET",
        "fetched_at": datetime.now(timezone.utc),
    }
    data.update(changes)
    return MarketPrice(**data)


def request(*, history=None, prices=None, **changes):
    data = {
        "commodity_id": COMMODITY_ID,
        "quantity_quintals": "10",
        "location": {"latitude": 17.9689, "longitude": 79.5941},
        "prices": [price()] if prices is None else prices,
        "history": [price(days_ago=day) for day in range(1, 7)] if history is None else history,
        "costs": {"spoilage_fraction": "0.05", "storage_days": 2},
        "distance_overrides": [{"mandi_id": MANDI_ID, "one_way_km": "10"}],
    }
    data.update(changes)
    return MarketGuidanceInput(**data)


def gemini_response(payload):
    return {"candidates": [{"finishReason": "STOP", "content": {
        "parts": [{"text": json.dumps(payload)}]
    }}]}


class MarketIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_gemini_sees_only_normalized_history_and_python_calculates_money(self):
        calls = []

        def respond(provider_request):
            calls.append(provider_request)
            return httpx.Response(200, json=gemini_response({
                "trend": "RISING",
                "confidence": 0.64,
                "reasoning_summary": "Recent observations suggest an upward pattern that may change.",
                "forecast_horizon": "7 calendar days",
            }))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            agent = MarketIntelligenceAgent(GeminiAdapter(
                client, api_key="test-key", model="gemini-test"
            ))
            result = await agent.analyze(request())

        self.assertEqual(result.status, "complete")
        self.assertEqual(len(calls), 1)
        ranking = result.rankings[0]
        self.assertEqual(ranking.gross_revenue, Decimal("20000.00"))
        self.assertEqual(ranking.transport_cost, Decimal("300.00"))
        self.assertEqual(ranking.loading_cost, Decimal("500.00"))
        self.assertEqual(ranking.commission, Decimal("400.00"))
        self.assertEqual(ranking.spoilage_loss, Decimal("1000.00"))
        self.assertEqual(ranking.storage_cost, Decimal("200.00"))
        self.assertEqual(ranking.net_return, Decimal("17600.00"))
        self.assertEqual(ranking.return_per_quintal, Decimal("1760.00"))
        self.assertEqual(ranking.trend.trend, "RISING")
        self.assertEqual(ranking.trend.forecast_horizon, "7 calendar days")
        self.assertEqual(result.model_dump(mode="json")["rankings"][0]["net_return"], "17600.00")
        self.assertIn("not a guaranteed financial outcome", result.disclaimer)

        sent = json.loads(calls[0].content)
        schema = sent["generationConfig"]["responseFormat"]["text"]["schema"]
        self.assertEqual(set(schema["properties"]), {
            "trend", "confidence", "reasoning_summary", "forecast_horizon"
        })
        prompt = sent["contents"][0]["parts"][0]["text"]
        context = json.loads(prompt.split("Price observations: ", 1)[1])
        self.assertEqual(len(context["observations"]), 7)
        self.assertEqual(set(context), {"unit", "forecast_horizon", "observations"})
        self.assertEqual(set(context["observations"][0]), {
            "date", "modal_price_inr_per_quintal"
        })
        self.assertNotIn("quantity_quintals", prompt)
        self.assertNotIn("transport_inr_per_km", prompt)

    async def test_unavailable_gemini_keeps_deterministic_ranking(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _: self.fail("No configured key should make an HTTP request")
        )) as client:
            agent = MarketIntelligenceAgent(GeminiAdapter(
                client, api_key=None, model="gemini-test"
            ))
            result = await agent.analyze(request())

        self.assertEqual(result.status, "partial")
        self.assertIsNone(result.rankings[0].trend)
        self.assertEqual(result.rankings[0].net_return, Decimal("17600.00"))
        self.assertEqual(result.sources[0].status, "unavailable")

    async def test_sparse_history_and_stale_prices_do_not_create_a_forecast_or_ranking(self):
        recent = price()
        stale = price(mandi_id=OTHER_MANDI_ID, days_ago=10, market_name="Old Mandi")

        class NeverCalled:
            model = "gemini-test"

            async def generate_market_trend_json(self, prompt):
                raise AssertionError("Sparse history must not be sent to Gemini")

        result = await MarketIntelligenceAgent(NeverCalled()).analyze(request(
            prices=[recent, stale], history=[]
        ))
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result.rankings), 1)
        self.assertIsNone(result.rankings[0].trend)
        self.assertEqual(result.excluded_markets[0].reason, "stale_price")

    async def test_mixed_varieties_require_a_comparable_selection(self):
        class NeverCalled:
            model = "gemini-test"

            async def generate_market_trend_json(self, prompt):
                raise AssertionError("Ambiguous varieties must not reach Gemini")

        result = await MarketIntelligenceAgent(NeverCalled()).analyze(request(
            prices=[price(), price(mandi_id=OTHER_MANDI_ID, variety="Hybrid")]
        ))
        self.assertEqual(result.status, "needs_input")
        self.assertIn("variety_code", result.missing_fields)
        self.assertFalse(result.rankings)

    def test_model_output_cannot_add_totals_or_guarantees(self):
        valid = {
            "trend": "STABLE", "confidence": 0.7,
            "reasoning_summary": "Recent observations vary little.",
            "forecast_horizon": "7 calendar days",
        }
        with self.assertRaises(ValidationError):
            MarketTrend.model_validate({**valid, "gross_revenue": "999999"})
        with self.assertRaises(ValidationError):
            MarketTrend.model_validate({**valid, "reasoning_summary": "Prices are guaranteed to rise."})
        with self.assertRaises(ValidationError):
            MarketTrend.model_validate({**valid, "trend": "UP"})


if __name__ == "__main__":
    unittest.main()
