"""Foundation regression checks; no Supabase credentials or network required."""

import asyncio
from contextlib import AsyncExitStack
import unittest
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.database import SupabaseConnection
from app.main import create_app
from app.repositories.health import SupabaseHealthRepository
from app.repositories.supabase_repository import SupabaseRepository
from app.services.health import HealthService


def local_settings(**overrides) -> Settings:
    values = dict(
        app_env="test",
        cors_origins="http://localhost:5173",
        supabase_url=None,
        supabase_anon_key=None,
        supabase_service_key=None,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


class SettingsTests(unittest.TestCase):
    def test_default_has_no_database_credentials(self):
        self.assertFalse(local_settings().supabase_configured)

    def test_partial_database_configuration_fails(self):
        with self.assertRaises(ValidationError):
            local_settings(supabase_url="https://example.supabase.co")

    def test_origin_normalization(self):
        settings = local_settings(
            cors_origins=" http://localhost:5173/,http://localhost:5173 "
        )
        self.assertEqual(settings.allowed_origins, ["http://localhost:5173"])

    def test_invalid_origins_fail(self):
        for origin in ("*", "", "https://example.com/path", "https://u:p@example.com"):
            with self.subTest(origin=origin), self.assertRaises(ValidationError):
                local_settings(cors_origins=origin)


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.stack = AsyncExitStack()
        self.addAsyncCleanup(self.stack.aclose)
        self.app = create_app(local_settings())
        await self.stack.enter_async_context(self.app.router.lifespan_context(self.app))
        self.client = await self.stack.enter_async_context(httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        ))

    async def test_health_and_request_id(self):
        request_id = str(uuid4())
        response = await self.client.get("/api/health", headers={"X-Request-ID": request_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})
        self.assertEqual(response.headers["X-Request-ID"], request_id)

    async def test_invalid_request_id_is_replaced(self):
        response = await self.client.get("/api/health", headers={"X-Request-ID": "invalid"})
        UUID(response.headers["X-Request-ID"])

    async def test_unconfigured_readiness(self):
        response = await self.client.get("/api/health/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {
            "status": "not_ready", "dependencies": {"supabase": "not_configured"}
        })

    async def test_configured_readiness_success_and_failure(self):
        repository = AsyncMock()
        self.app.state.health_service = HealthService(repository, configured=True)
        for connected, status_code in ((True, 200), (False, 503)):
            repository.check_database.return_value = connected
            response = await self.client.get("/api/health/ready")
            self.assertEqual(response.status_code, status_code)
            self.assertEqual(response.json()["dependencies"]["supabase"],
                             "connected" if connected else "unavailable")

    async def test_cors(self):
        for origin, status_code in (("http://localhost:5173", 200), ("https://other.test", 400)):
            response = await self.client.options("/api/health", headers={
                "Origin": origin, "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,X-Request-ID",
            })
            self.assertEqual(response.status_code, status_code)
            if status_code == 200:
                self.assertEqual(response.headers["access-control-allow-origin"], origin)
            else:
                self.assertNotIn("access-control-allow-origin", response.headers)

    async def test_unknown_route_uses_error_envelope(self):
        response = await self.client.get("/api/unknown")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
        self.assertEqual(response.json()["meta"]["request_id"], response.headers["X-Request-ID"])

    async def test_openapi_only_has_implemented_routes(self):
        response = await self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()["paths"]), {"/api/health", "/api/health/ready", "/api/weather", "/api/market/prices"})

    async def test_shutdown_closes_shared_http_pool(self):
        http_client = self.app.state.http_client
        self.assertFalse(http_client.is_closed)
        await self.stack.aclose()
        self.assertTrue(http_client.is_closed)


class SupabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_scoped_tokens_and_repository_queries(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=[{"id": "record"}])

        settings = local_settings(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="test-anon-key",
            supabase_service_key="test-service-key",
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http_client:
            connection = SupabaseConnection(settings, http_client)
            first = await connection.user_client("user-one")
            second = await connection.user_client("user-two")
            service = await connection.service_client()
            self.assertIs(await connection.service_client(), service)
            for client in (first, second, service, first):
                rows = await SupabaseRepository(client, "farms").select_many(
                    filters={"farmer_id": "owner"}, limit=200
                )
                self.assertEqual(rows, [{"id": "record"}])
            self.assertNotIn("authorization", http_client.headers)
            with self.assertRaises(ValueError):
                await connection.user_client(" ")

        self.assertEqual([r.headers["authorization"] for r in requests], [
            "Bearer user-one", "Bearer user-two", "Bearer test-service-key", "Bearer user-one"
        ])
        self.assertEqual([r.headers["apikey"] for r in requests], [
            "test-anon-key", "test-anon-key", "test-service-key", "test-anon-key"
        ])
        for request in requests:
            self.assertEqual(request.url.params["farmer_id"], "eq.owner")
            self.assertEqual(request.url.params["limit"], "100")

    async def test_database_failure_becomes_unavailable(self):
        connection = AsyncMock()
        connection.service_client.side_effect = RuntimeError("simulated failure")
        self.assertFalse(await SupabaseHealthRepository(connection).check_database())

    async def test_readiness_deadline(self):
        async def slow_connection():
            await asyncio.sleep(1)

        connection = AsyncMock()
        connection.service_client.side_effect = slow_connection
        repository = SupabaseHealthRepository(connection, timeout_seconds=0.01)
        self.assertFalse(await repository.check_database())


if __name__ == "__main__":
    unittest.main()
