"""
Authentication Module for MIA API
Provides API key and optional JWT authentication.
"""
from .api_key import (
    APIKeyAuth,
    get_api_key_auth,
    verify_api_key,
    generate_api_key
)
from .dependencies import (
    get_current_user,
    require_auth,
    optional_auth
)

__all__ = [
    'APIKeyAuth',
    'get_api_key_auth',
    'verify_api_key',
    'generate_api_key',
    'get_current_user',
    'require_auth',
    'optional_auth'
]
