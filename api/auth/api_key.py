"""
API Key Authentication
Simple but secure API key authentication for MIA.
"""
import os
import secrets
import logging
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass, field
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """Information about an API key"""
    key_id: str
    name: str
    hashed_key: str
    created_at: datetime
    last_used: Optional[datetime] = None
    scopes: List[str] = field(default_factory=lambda: ["read", "write"])
    enabled: bool = True


class APIKeyAuth:
    """
    API Key authentication manager.
    
    Supports:
    - Multiple API keys with different scopes
    - Key hashing for secure storage
    - Environment variable configuration
    - Development mode (auth disabled)
    
    Usage:
        auth = APIKeyAuth()
        
        # Verify a key
        if auth.verify("mia_api_key_abc123"):
            print("Valid key")
        
        # Generate a new key
        key, info = auth.generate_key("My App")
        print(f"New key: {key}")
    """
    
    def __init__(self):
        self._keys: List[APIKeyInfo] = []  # list of key infos
        self._enabled = True
        self._ph = PasswordHasher()
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Check if auth is disabled
        if os.environ.get('MIA_AUTH_DISABLED', '').lower() in ('1', 'true', 'yes'):
            self._enabled = False
            logger.warning("API authentication is DISABLED (MIA_AUTH_DISABLED=1)")
            return

        # Load master API key from environment
        master_key = os.environ.get('MIA_API_KEY')
        if master_key:
            key_hash = self._hash_key(master_key)
            self._keys.append(APIKeyInfo(
                key_id="master",
                name="Master API Key (env)",
                hashed_key=key_hash,
                created_at=datetime.now(),
                scopes=["admin", "read", "write"]
            ))
            logger.info("Loaded master API key from environment")

        # Load additional keys (comma-separated)
        additional_keys = os.environ.get('MIA_API_KEYS', '')
        for i, key in enumerate(additional_keys.split(','), start=1):
            key = key.strip()
            if key:
                key_hash = self._hash_key(key)
                self._keys.append(APIKeyInfo(
                    key_id=f"env_{i}",
                    name=f"API Key {i} (env)",
                    hashed_key=key_hash,
                    created_at=datetime.now(),
                    scopes=["read", "write"]
                ))

        if not self._keys:
            logger.warning("No API keys configured. Set MIA_API_KEY environment variable.")
    
    @property
    def enabled(self) -> bool:
        """Check if authentication is enabled"""
        return self._enabled
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key for secure storage using Argon2"""
        return self._ph.hash(key)
    
    def verify(self, key: str) -> Optional[APIKeyInfo]:
        """
        Verify an API key.

        Args:
            key: The API key to verify

        Returns:
            APIKeyInfo if valid, None if invalid
        """
        if not self._enabled:
            # Return a dummy info when auth is disabled
            return APIKeyInfo(
                key_id="disabled",
                name="Auth Disabled",
                hashed_key="",
                created_at=datetime.now(),
                scopes=["admin", "read", "write"]
            )

        # Iterate through all keys and verify using Argon2
        for info in self._keys:
            if info.enabled:
                try:
                    self._ph.verify(info.hashed_key, key)
                    info.last_used = datetime.now()
                    return info
                except VerifyMismatchError:
                    continue

        return None
    
    def has_scope(self, key: str, scope: str) -> bool:
        """Check if a key has a specific scope"""
        info = self.verify(key)
        if not info:
            return False
        return scope in info.scopes or "admin" in info.scopes
    
    def add_key(self, key: str, name: str, scopes: Optional[List[str]] = None) -> APIKeyInfo:
        """
        Add a new API key.

        Args:
            key: The raw API key
            name: Human-readable name for the key
            scopes: List of scopes (default: ["read", "write"])

        Returns:
            APIKeyInfo for the new key
        """
        key_hash = self._hash_key(key)
        info = APIKeyInfo(
            key_id=key_hash[:8],
            name=name,
            hashed_key=key_hash,
            created_at=datetime.now(),
            scopes=scopes or ["read", "write"]
        )
        self._keys.append(info)
        logger.info(f"Added API key: {name}")
        return info
    
    def remove_key(self, key: str) -> bool:
        """Remove an API key"""
        # Find the key by verifying it first
        for i, info in enumerate(self._keys):
            if info.enabled:
                try:
                    self._ph.verify(info.hashed_key, key)
                    self._keys.pop(i)
                    return True
                except VerifyMismatchError:
                    continue
        return False
    
    def disable_key(self, key: str) -> bool:
        """Disable an API key without removing it"""
        # Find the key by verifying it first
        for info in self._keys:
            if info.enabled:
                try:
                    self._ph.verify(info.hashed_key, key)
                    info.enabled = False
                    return True
                except VerifyMismatchError:
                    continue
        return False
    
    def list_keys(self) -> List[APIKeyInfo]:
        """List all registered keys (without the actual key values)"""
        return self._keys.copy()


# Singleton instance
_api_key_auth: Optional[APIKeyAuth] = None


def get_api_key_auth() -> APIKeyAuth:
    """Get the global API key auth instance"""
    global _api_key_auth
    if _api_key_auth is None:
        _api_key_auth = APIKeyAuth()
    return _api_key_auth


def verify_api_key(key: str) -> Optional[APIKeyInfo]:
    """Convenience function to verify an API key"""
    return get_api_key_auth().verify(key)


def generate_api_key(prefix: str = "mia") -> str:
    """
    Generate a new secure API key.
    
    Format: {prefix}_api_{random_32_chars}
    Example: mia_api_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
    """
    random_part = secrets.token_hex(16)
    return f"{prefix}_api_{random_part}"
