"""
FastAPI Authentication Dependencies
Provides dependency injection for route protection.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.requests import HTTPConnection

from .api_key import get_api_key_auth, APIKeyInfo

logger = logging.getLogger(__name__)

# API key can be provided via header or query parameter
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query)
) -> Optional[str]:
    """
    Extract API key from request (header or query parameter).
    Header takes precedence over query parameter.
    """
    return api_key_header or api_key_query


async def get_current_user(
    api_key: Optional[str] = Depends(get_api_key)
) -> Optional[APIKeyInfo]:
    """
    Get the current authenticated user/key info.
    Returns None if not authenticated (for optional auth routes).
    """
    auth = get_api_key_auth()
    
    if not auth.enabled:
        # Auth disabled, return dummy user
        return APIKeyInfo(
            key_id="disabled",
            name="Auth Disabled",
            created_at=__import__('datetime').datetime.now(),
            scopes=["admin", "read", "write"]
        )
    
    if not api_key:
        return None
    
    return auth.verify(api_key)


async def require_auth(
    user: Optional[APIKeyInfo] = Depends(get_current_user)
) -> APIKeyInfo:
    """
    Require authentication for a route.
    Raises 401 if not authenticated.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: APIKeyInfo = Depends(require_auth)):
            return {"user": user.name}
    """
    auth = get_api_key_auth()
    
    if not auth.enabled:
        return user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return user


async def optional_auth(
    user: Optional[APIKeyInfo] = Depends(get_current_user)
) -> Optional[APIKeyInfo]:
    """
    Optional authentication for a route.
    Returns None if not authenticated, but doesn't raise error.
    
    Usage:
        @app.get("/public")
        async def public_route(user: Optional[APIKeyInfo] = Depends(optional_auth)):
            if user:
                return {"message": f"Hello, {user.name}"}
            return {"message": "Hello, anonymous"}
    """
    return user


def require_scope(scope: str):
    """
    Factory for scope-checking dependency.
    
    Usage:
        @app.delete("/admin/resource")
        async def admin_route(user: APIKeyInfo = Depends(require_scope("admin"))):
            return {"deleted": True}
    """
    async def scope_checker(
        user: APIKeyInfo = Depends(require_auth)
    ) -> APIKeyInfo:
        auth = get_api_key_auth()
        
        if not auth.enabled:
            return user
        
        if scope not in user.scopes and "admin" not in user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {scope}"
            )
        
        return user
    
    return scope_checker


# Pre-built scope checkers
require_admin = require_scope("admin")
require_write = require_scope("write")
require_read = require_scope("read")


# --- App-wide enforcement -------------------------------------------------
#
# Applied to every HTTP route via ``FastAPI(dependencies=[Depends(enforce_api_auth)])``
# and called explicitly by the WebSocket handlers (a WebSocket cannot raise
# HTTPException before accept()).
#
# Policy: authentication is enforced as soon as at least one key is configured
# (MIA_API_KEY / MIA_API_KEYS). With no key configured the API stays open so
# existing clients keep working, but that is logged loudly, once. Operators opt
# out explicitly with MIA_AUTH_DISABLED=1. GET/HEAD need the "read" scope,
# everything else "write"; "admin" satisfies both.

PUBLIC_PATHS = frozenset({"/", "/auth/status", "/docs", "/redoc", "/openapi.json"})
_READ_METHODS = frozenset({"GET", "HEAD"})
_VERIFIED_TTL_S = 300.0
_verified: dict = {}
_warned_open = False


def auth_configured() -> bool:
    """True when requests must carry a valid key."""
    auth = get_api_key_auth()
    return auth.enabled and bool(auth.list_keys())


def _warn_open_once() -> None:
    global _warned_open
    auth = get_api_key_auth()
    if auth.enabled and not _warned_open:
        _warned_open = True
        logger.warning(
            "API authentication is NOT enforced: no API key configured. "
            "Set MIA_API_KEY (or MIA_AUTH_DISABLED=1 to silence this)."
        )


def _verify_cached(key: str) -> Optional[APIKeyInfo]:
    """Argon2 verification is deliberately slow; remember successes briefly."""
    import hashlib
    import time

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    now = time.monotonic()
    hit = _verified.get(digest)
    if hit and hit[1] > now:
        return hit[0]
    info = get_api_key_auth().verify(key)
    if info is not None:
        if len(_verified) > 256:
            _verified.clear()
        _verified[digest] = (info, now + _VERIFIED_TTL_S)
    return info


def _has_scope(info: APIKeyInfo, scope: str) -> bool:
    return scope in info.scopes or "admin" in info.scopes


async def enforce_api_auth(conn: HTTPConnection) -> None:
    """HTTP dependency: see the policy comment above.

    Reads the key from the connection directly instead of through the
    ``APIKeyHeader`` security schemes: FastAPI also applies app-level
    dependencies to WebSocket routes, where those schemes cannot resolve.
    """
    if conn.scope["type"] != "http":
        return  # WebSockets call authenticate_websocket() themselves
    api_key = conn.headers.get("x-api-key") or conn.query_params.get("api_key")
    request_method = conn.scope.get("method", "GET")
    if request_method == "OPTIONS" or conn.scope["path"] in PUBLIC_PATHS:
        return
    if not auth_configured():
        _warn_open_once()
        return
    info = _verify_cached(api_key) if api_key else None
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    needed = "read" if request_method in _READ_METHODS else "write"
    if not _has_scope(info, needed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required scope: {needed}",
        )


async def authenticate_websocket(websocket) -> bool:
    """Call before ``websocket.accept()``; closes the socket and returns False on failure.

    Only the ``X-API-Key`` header is accepted: a key in the query string ends up in
    logs and browser history.
    """
    if not auth_configured():
        _warn_open_once()
        return True
    key = websocket.headers.get("x-api-key")
    info = _verify_cached(key) if key else None
    if info is None or not _has_scope(info, "read"):
        await websocket.close(code=1008)
        return False
    return True
