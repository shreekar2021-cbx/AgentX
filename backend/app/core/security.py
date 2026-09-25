from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.core.config import Settings, get_settings
from app.core.errors import AppError


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    token: str
    is_demo: bool = False


DEMO_USER_ID = "00000000-0000-4000-8000-000000000001"


@lru_cache(maxsize=8)
def jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(f"{url.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_jwk_set=True, lifespan=600, timeout=5)


def verify_user_token(token: str, settings: Settings) -> Principal:
    if not settings.supabase_url:
        raise AppError(503, "auth_unavailable", "Authentication is not configured.")
    if not token or len(token) > 8192:
        raise AppError(401, "invalid_token", "A valid sign-in token is required.")
    try:
        # Supabase Auth's asymmetric JWKS endpoint. No service-role credential is used.
        jwks = jwks_client(settings.supabase_url)
        key = jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=["RS256", "ES256"], audience="authenticated", issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1")
        user_id = str(UUID(claims["sub"]))
        metadata = claims.get("app_metadata") or {}
        role = metadata.get("role", "farmer") if isinstance(metadata, dict) else "farmer"
        return Principal(user_id=user_id, role=role, token=token)
    except PyJWKClientConnectionError as exc:
        raise AppError(503, "auth_unavailable", "Authentication is temporarily unavailable.") from exc
    except (PyJWKClientError, jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise AppError(401, "invalid_token", "A valid sign-in token is required.") from exc


def require_user(authorization: Annotated[str | None, Header()] = None, settings: Settings = Depends(get_settings)) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(401, "authentication_required", "Sign in to access this resource.")
    return verify_user_token(authorization[7:], settings)


def require_admin(principal: Principal = Depends(require_user)) -> Principal:
    if principal.role != "admin":
        raise AppError(403, "forbidden", "Administrator access is required.")
    return principal


def current_principal(authorization: Annotated[str | None, Header()] = None, settings: Settings = Depends(get_settings)) -> Principal:
    if settings.local_demo_mode:
        return Principal(user_id=DEMO_USER_ID, role="farmer", token="", is_demo=True)
    return require_user(authorization, settings)
