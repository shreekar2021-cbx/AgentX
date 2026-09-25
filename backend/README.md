# AgriVision FastAPI backend

## Run locally

Use Python 3.11 or newer. Activation is optional; these commands work even when PowerShell blocks activation scripts.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave the three Supabase settings blank for local foundation work. Set all three together to enable database access. `CORS_ORIGINS` is a comma-separated list of frontend origins; `AGRIVISION_DEBUG` controls debug mode. HTTP calls and readiness have a configurable `HTTP_TIMEOUT_SECONDS` limit (default 10 seconds).

`GET /api/health` is a process liveness check and does not need credentials. `GET /api/health/ready` checks Supabase using the service key and requires the initial migration to have been applied. OpenAPI docs are at `/docs` outside production.

## Database

Apply `../supabase/migrations/202609250001_initial_schema.sql` to a Supabase project before enabling readiness. Keep keys in the ignored local `.env`; do not commit them. The service-role key stays in the backend and bypasses RLS, so request repositories must use the caller's verified JWT with an anon key.

The initial migration creates 16 tables, constraints, indexes, RLS policies, column write grants, a signup profile trigger, four canonical commodities, and the private `crop-images` bucket. Apply it once to a new project using the Supabase SQL editor or your migration workflow. Subsequent schema changes belong in new migrations. No local command applies this migration automatically.

The `app.repositories.interfaces` module defines boundaries. `SupabaseRepository` is a deliberately small PostgREST base; feature-specific repository methods and routes arrive with their implementation phase. `APP_MODE` defaults to `live`; demo fixture behavior will be added with the feature adapters.

## Module boundaries

- `app/main.py`: app factory, lifespan, shared async HTTP pool, CORS, request IDs, errors.
- `app/config.py`: validated environment settings.
- `app/database.py`: asynchronous Supabase client factory. Await `user_client(verified_token)` for normal repositories; `service_client()` is explicitly privileged. Clients share a transport pool with separate authorization headers. JWT verification must be implemented before adding protected routes.
- `app/schemas/`: response envelopes, enums, domain request and record models.
- `app/services/`: service protocols and health service.
- `app/repositories/`: repository protocols and initial RLS-scoped reads.
- `app/api/`: only liveness and readiness routes are registered.

## Verify locally

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q app tests
```

The checks exercise lifespan startup/shutdown, health/readiness, CORS, error envelopes, configuration, and Supabase request credential isolation using an in-memory transport. They do not contact Supabase or apply SQL. To smoke-check a running server, use `Invoke-RestMethod http://127.0.0.1:8000/api/health`; expect `status: healthy`. Readiness returns 503 with `not_configured` until credentials are supplied, or `unavailable` if the database cannot be reached.
