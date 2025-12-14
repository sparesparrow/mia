"""
FastAPI Authentication Dependencies
Provides dependency injection for route protection.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

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
