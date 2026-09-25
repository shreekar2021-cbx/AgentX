"""Weather endpoint, adapter, and cache tests with controlled provider responses."""

import asyncio
from contextlib import AsyncExitStack
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.adapters.weather import OpenMeteoAdapter
from app.api.weather import get_weather_service
from app.config import Settings
from app.database import SupabaseConnection
from app.main import create_app
from app.repositories.weather_cache import SupabaseWeatherCacheRepository
from app.schemas.weather import WeatherLocation, WeatherSnapshot
from app.services.weather import WeatherService

LOCATION = WeatherLocation(latitude=17.39, longitude=78.49)


def provider_payload():
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    return {
        "utc_offset_seconds": 0,
        "current_units": {"time": "iso8601", "interval": "seconds", "temperature_2m": "°C",
                          "relative_humidity_2m": "%", "rain": "mm", "wind_speed_10m": "km/h"},
        "daily_units": {"time": "iso8601", "temperature_2m_min": "°C", "temperature_2m_max": "°C",
                        "rain_sum": "mm", "wind_speed_10m_max": "km/h"},
        "current": {"time": now.replace(tzinfo=None).isoformat(), "interval": 900,
                    "temperature_2m": 30.5, "relative_humidity_2m": 78, "rain": 0, "wind_speed_10m": 12},
        "daily": {
            "time": [(now.date() + timedelta(days=i)).isoformat() for i in range(7)],
            "temperature_2m_min": [23] * 7, "temperature_2m_max": [34] * 7,
            "rain_sum": [0, 2, 15, 0, 1, 0, 0], "wind_speed_10m_max": [20] * 7,
        },
    }


class WeatherTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.stack = AsyncExitStack()
        self.addAsyncCleanup(self.stack.aclose)
        self.requests = []
        self.payload = provider_payload()
        self.provider_status = 200
        self.clock = datetime.now(timezone.utc)

        def respond(request):
            self.requests.append(request)
            return httpx.Response(self.provider_status, json=self.payload)

        http_client = await self.stack.enter_async_context(httpx.AsyncClient(
            transport=httpx.MockTransport(respond)
        ))
        self.adapter = OpenMeteoAdapter(http_client)
        self.cache = AsyncMock()
        self.cache.get.return_value = None
        self.service = WeatherService(self.adapter, self.cache, now=lambda: self.clock)
        settings = Settings(_env_file=None, supabase_url=None, supabase_anon_key=None, supabase_service_key=None)
        app = create_app(settings)
        app.dependency_overrides[get_weather_service] = lambda: self.service
        self.client = await self.stack.enter_async_context(httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ))
        # Avoid real waiting in deterministic retry tests.
        self.sleep = self.stack.enter_context(patch("app.adapters.weather.asyncio.sleep", new_callable=AsyncMock))

    async def fetch(self, lat="17.385", lng="78.4867"):
        return await self.client.get("/api/weather", params={"lat": lat, "lng": lng})

    async def prime_cache(self, age=timedelta(minutes=31)):
        response = await self.fetch()
        self.assertEqual(response.status_code, 200)
        self.clock = datetime.fromisoformat(response.json()["meta"]["sources"][0]["fetched_at"].replace("Z", "+00:00")) + age
        return response.json()

    async def test_live_normalization_and_fresh_cache(self):
        first = await self.fetch()
        self.assertEqual(first.status_code, 200)
        body = first.json()
        self.assertEqual(body["data"]["current"]["temperature_c"], 30.5)
        self.assertEqual(body["data"]["current"]["humidity_pct"], 78)
        self.assertEqual(body["data"]["current"]["interval_seconds"], 900)
        self.assertEqual(body["data"]["current"]["measurement_kind"], "model_estimate")
        self.assertIsNone(body["data"]["recent_observed_rain_48h_mm"])
        self.assertEqual(len(body["data"]["forecast_7day"]), 7)
        self.assertEqual(body["data"]["forecast_7day"][2]["rain_mm"], 15)
        self.assertEqual(body["meta"]["sources"][0]["status"], "live")
        self.assertEqual(body["meta"]["request_id"], first.headers["x-request-id"])
        # Advance from the provider's fetch time, not setup time.
        self.clock = datetime.now(timezone.utc)
        second = (await self.fetch()).json()
        self.assertEqual(second["meta"]["sources"][0]["status"], "cached")
        self.assertFalse(second["meta"]["sources"][0]["is_stale"])
        self.assertEqual(len(self.requests), 1)
        self.cache.put.assert_awaited_once()
        self.assertEqual(self.requests[0].url.params["timezone"], "UTC")
        self.assertEqual(self.requests[0].url.params["latitude"], "17.39")
        self.assertEqual(self.requests[0].extensions["timeout"]["read"], 5)

    async def test_stale_fallback_preserves_original_timestamps(self):
        original = await self.prime_cache()
        self.provider_status = 503
        response = await self.fetch()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        source = body["meta"]["sources"][0]
        self.assertEqual(source["status"], "cached")
        self.assertTrue(source["is_stale"])
        self.assertEqual(source["fetched_at"], original["meta"]["sources"][0]["fetched_at"])
        self.assertEqual(source["expires_at"], original["meta"]["sources"][0]["expires_at"])
        self.assertIn("stale_weather", [w["code"] for w in body["meta"]["warnings"]])
        self.assertEqual(len(self.requests), 3)

    async def test_cache_over_24_hours_is_rejected(self):
        await self.prime_cache(age=timedelta(hours=25))
        self.provider_status = 503
        response = await self.fetch()
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json()["error"]["retryable"])

    async def test_cold_outage_returns_error_envelope(self):
        self.provider_status = 503
        response = await self.fetch()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "dependency_unavailable")
        self.assertEqual(len(self.requests), 2)

    async def test_validation_prevents_provider_call(self):
        for lat, lng in (("91", "0"), ("0", "181"), ("nan", "0"), ("0", "inf"), ("oops", "0")):
            with self.subTest(lat=lat, lng=lng):
                self.assertEqual((await self.fetch(lat, lng)).status_code, 422)
        self.assertEqual((await self.client.get("/api/weather")).status_code, 422)
        self.assertEqual(len(self.requests), 0)

    async def test_provider_400_does_not_retry_or_leak_details(self):
        self.provider_status = 400
        self.payload = {"error": True, "reason": "private provider diagnostics"}
        response = await self.fetch()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private provider diagnostics", response.text)
        self.assertEqual(len(self.requests), 1)

    async def test_bad_payloads_are_unavailable_without_retry(self):
        invalid = [[], {}, {**provider_payload(), "current": None}]
        wrong_units = provider_payload()
        wrong_units["current_units"]["temperature_2m"] = "°F"
        invalid.append(wrong_units)
        incomplete = provider_payload()
        incomplete["daily"]["rain_sum"] = [0]
        invalid.append(incomplete)
        missing_value = provider_payload()
        missing_value["current"]["rain"] = None
        invalid.append(missing_value)
        old = provider_payload()
        old["current"]["time"] = (self.clock - timedelta(days=2)).isoformat()
        invalid.append(old)
        for payload in invalid:
            with self.subTest(payload_type=type(payload).__name__):
                self.payload = payload
                self.requests.clear()
                self.assertEqual((await self.fetch()).status_code, 503)
                self.assertEqual(len(self.requests), 1)

    async def test_cache_failures_do_not_block_live_result(self):
        self.cache.get.side_effect = RuntimeError("database unavailable")
        self.cache.put.side_effect = RuntimeError("database unavailable")
        response = await self.fetch()
        self.assertEqual(response.status_code, 200)
        codes = {w["code"] for w in response.json()["meta"]["warnings"]}
        self.assertEqual(codes, {"weather_cache_unavailable", "weather_cache_write_failed"})
        self.clock = datetime.now(timezone.utc)
        self.assertEqual((await self.fetch()).json()["meta"]["sources"][0]["status"], "cached")

    async def test_persistent_cache_survives_service_recreation(self):
        await self.fetch()
        snapshot = self.cache.put.call_args.args[1]
        self.cache.get.return_value = snapshot
        self.clock = datetime.now(timezone.utc)
        replacement = WeatherService(self.adapter, self.cache, now=lambda: self.clock)
        result = await replacement.get_weather(LOCATION)
        self.assertEqual(result.status, "cached")
        self.assertFalse(result.is_stale)
        self.assertEqual(len(self.requests), 1)

    async def test_cache_for_wrong_location_is_rejected(self):
        await self.fetch()
        self.cache.get.return_value = self.cache.put.call_args.args[1]
        self.provider_status = 503
        self.assertEqual((await self.fetch("20", "70")).status_code, 503)

    async def test_memory_cache_is_bounded(self):
        self.service = WeatherService(self.adapter, max_memory_entries=1)
        await self.fetch("10", "20")
        await self.fetch("11", "20")
        await self.fetch("10", "20")
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(len(self.service._memory), 1)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def run_adapter(self, handler, **kwargs):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await OpenMeteoAdapter(client, **kwargs).get_weather(LOCATION)

    async def test_transient_failure_then_success(self):
        attempts = []
        def handler(request):
            attempts.append(request)
            return httpx.Response(503 if len(attempts) == 1 else 200, json=provider_payload())
        with patch("app.adapters.weather.asyncio.sleep", new_callable=AsyncMock) as sleep:
            result = await self.run_adapter(handler)
        self.assertEqual(result.status, "live")
        self.assertEqual(len(attempts), 2)
        sleep.assert_awaited_once()

    async def test_timeouts_retry_once(self):
        attempts = []
        def handler(request):
            attempts.append(request)
            raise httpx.ReadTimeout("simulated", request=request)
        with patch("app.adapters.weather.asyncio.sleep", new_callable=AsyncMock):
            result = await self.run_adapter(handler)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.warnings[0].code, "weather_timeout")
        self.assertEqual(len(attempts), 2)

    async def test_actual_attempt_deadline(self):
        attempts = []
        async def handler(request):
            attempts.append(request)
            await asyncio.sleep(1)
            return httpx.Response(200, json=provider_payload())
        result = await self.run_adapter(handler, timeout_seconds=0.01, operation_budget_seconds=0.05)
        self.assertEqual(result.warnings[0].code, "weather_timeout")
        self.assertEqual(len(attempts), 1)

    async def test_retry_after_respected(self):
        attempts = []
        def handler(request):
            attempts.append(request)
            return httpx.Response(429, headers={"Retry-After": "2"})
        with patch("app.adapters.weather.asyncio.sleep", new_callable=AsyncMock) as sleep:
            result = await self.run_adapter(handler)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(len(attempts), 2)
        sleep.assert_awaited_once_with(2.0)

    async def test_retry_after_beyond_budget_does_not_retry(self):
        attempts = []
        def handler(request):
            attempts.append(request)
            return httpx.Response(429, headers={"Retry-After": "120"})
        with patch("app.adapters.weather.asyncio.sleep", new_callable=AsyncMock) as sleep:
            await self.run_adapter(handler)
        self.assertEqual(len(attempts), 1)
        sleep.assert_not_awaited()
        date_header = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=60))
        self.assertGreater(OpenMeteoAdapter._retry_after(date_header), 58)


class PersistentCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_repository_round_trip_with_mock_supabase(self):
        now = datetime.now(timezone.utc)
        data = OpenMeteoAdapter._normalize(provider_payload(), LOCATION, now)
        snapshot = WeatherSnapshot(data=data, fetched_at=now, expires_at=now + timedelta(minutes=30))
        stored = {}
        def handler(request):
            import json
            self.assertEqual(request.url.path, "/rest/v1/service_cache")
            if request.method == "POST":
                stored.update(json.loads(request.content))
                self.assertEqual(request.url.params["on_conflict"], "cache_key")
                return httpx.Response(201, json=[stored])
            self.assertEqual(request.url.params["cache_key"], f"eq.{LOCATION.cache_key}")
            self.assertEqual(request.url.params["provider"], "eq.open-meteo")
            self.assertEqual(request.url.params["schema_version"], "eq.1")
            return httpx.Response(200, json=[stored])
        settings = Settings(_env_file=None, supabase_url="https://example.supabase.co",
                            supabase_anon_key="test-anon", supabase_service_key="test-service")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            repo = SupabaseWeatherCacheRepository(SupabaseConnection(settings, client))
            await repo.put(LOCATION.cache_key, snapshot)
            loaded = await repo.get(LOCATION.cache_key)
        self.assertEqual(loaded, snapshot)


if __name__ == "__main__":
    unittest.main()
