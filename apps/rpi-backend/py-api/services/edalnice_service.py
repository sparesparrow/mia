"""
Edalnice.cz Integration Service
Czech toll/vehicle system integration for checking vehicle exemption status
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EdalniceCacheEntry:
    """Cache entry for edalnice.cz lookups"""

    def __init__(self, data: Dict[str, Any], ttl_hours: int = 24):
        self.data = data
        self.timestamp = datetime.now()
        self.ttl = timedelta(hours=ttl_hours)

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - self.timestamp > self.ttl


class EdalniceCzService:
    """Service for querying Czech vehicle exemption status from edalnice.cz"""

    # Edalnice.cz API endpoint (public, no authentication required)
    API_URL = "https://edalnice.cz/api/query"
    API_SEARCH_URL = "https://edalnice.cz/api/search"

    # Status constants
    STATUS_EXEMPTED = "Vozidlo osvobozeno"
    STATUS_OK = "Vozidlo v pořádku"
    STATUS_NOT_FOUND = "Vozidlo nenalezeno"
    STATUS_DEBT = "Vozidlo má dluh"

    def __init__(self, cache_dir: Optional[str] = None, cache_ttl_hours: int = 24):
        """
        Initialize Edalnice service

        Args:
            cache_dir: Directory for local cache
            cache_ttl_hours: Cache TTL in hours (default: 24)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "edalnice"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_hours = cache_ttl_hours
        self._memory_cache: Dict[str, EdalniceCacheEntry] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize HTTP session"""
        if not self._initialized:
            self._initialized = True
            logger.info("Edalnice service initialized")

    async def shutdown(self):
        """Cleanup HTTP session"""
        if self._initialized:
            self._initialized = False
            logger.info("Edalnice service shutdown")

    def _get_cache_key(self, plate: str) -> str:
        """Generate cache key for plate"""
        plate_clean = plate.replace(" ", "").upper()
        return hashlib.sha256(plate_clean.encode()).hexdigest()

    def _load_cache_from_disk(self, plate: str) -> Optional[Dict[str, Any]]:
        """Load cache entry from disk"""
        try:
            cache_key = self._get_cache_key(plate)
            cache_file = self.cache_dir / f"{cache_key}.json"

            if cache_file.exists():
                with open(cache_file) as f:
                    entry_data = json.load(f)
                    entry = EdalniceCacheEntry(entry_data["data"], self.cache_ttl_hours)
                    timestamp = entry_data.get("timestamp")
                    if timestamp:
                        entry.timestamp = datetime.fromisoformat(timestamp)

                    if not entry.is_expired():
                        logger.debug(f"Cache hit for plate {plate}")
                        return entry.data
                    else:
                        # Remove expired cache file
                        cache_file.unlink()
        except Exception as e:
            logger.warning(f"Error loading cache for {plate}: {e}")

        return None

    def _save_cache_to_disk(self, plate: str, data: Dict[str, Any]):
        """Save cache entry to disk"""
        try:
            cache_key = self._get_cache_key(plate)
            cache_file = self.cache_dir / f"{cache_key}.json"

            with open(cache_file, "w") as f:
                json.dump({"plate": plate, "data": data, "timestamp": datetime.now().isoformat()}, f)
        except Exception as e:
            logger.warning(f"Error saving cache for {plate}: {e}")

    async def query_vehicle(self, plate: str) -> Dict[str, Any]:
        """
        Query edalnice.cz for vehicle exemption status

        Args:
            plate: License plate (e.g., "AB 12345 CD")

        Returns:
            Dict with vehicle info and exemption status
        """
        plate_clean = plate.replace(" ", "").upper()

        # Check memory cache first
        cache_key = self._get_cache_key(plate)
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if not entry.is_expired():
                logger.debug(f"Memory cache hit for {plate}")
                return entry.data

        # Check disk cache
        cached_data = self._load_cache_from_disk(plate)
        if cached_data:
            self._memory_cache[cache_key] = EdalniceCacheEntry(cached_data, self.cache_ttl_hours)
            return cached_data

        # Query API
        try:
            if not self._initialized:
                await self.initialize()

            # Try public API first (no authentication)
            result = await self._query_public_api(plate_clean)

            if result and result.get("status") != "error":
                # Cache the result
                self._memory_cache[cache_key] = EdalniceCacheEntry(result, self.cache_ttl_hours)
                self._save_cache_to_disk(plate, result)
                return result

            # Fallback response if API fails
            return {
                "status": "unknown",
                "message": "Could not query edalnice.cz",
                "plate": plate_clean,
                "error": result.get("error") if result else "API request failed",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error querying edalnice.cz for {plate}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "plate": plate_clean,
                "timestamp": datetime.now().isoformat(),
            }

    async def _query_public_api(self, plate: str) -> Optional[Dict[str, Any]]:
        """
        Query public edalnice.cz API

        Args:
            plate: Clean plate text (no spaces)

        Returns:
            API response or None if request fails
        """
        try:
            if not self._initialized:
                await self.initialize()

            data = await asyncio.to_thread(self._post_public_api, plate)
            http_error = data.get("__http_error")
            if not http_error:

                # Parse response
                is_exempted = self._parse_exemption_status(data)

                return {
                    "status": "success",
                    "plate": plate,
                    "is_exempted": is_exempted,
                    "exemption_reason": self._get_exemption_reason(data),
                    "raw_response": data,
                    "timestamp": datetime.now().isoformat(),
                }

            logger.warning(f"API response status: {http_error}")
            return {"status": "error", "error": f"HTTP {http_error}"}

        except TimeoutError:
            logger.warning(f"Timeout querying edalnice.cz for {plate}")
            return {"status": "error", "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error querying API: {e}")
            return {"status": "error", "error": str(e)}

    def _post_public_api(self, plate: str) -> Dict[str, Any]:
        """Post plate lookup request using standard-library HTTP client."""
        payload = json.dumps({"plate": plate}).encode("utf-8")
        request = urllib.request.Request(
            self.API_SEARCH_URL,
            data=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            return {"__http_error": exc.code}

    @staticmethod
    def _parse_exemption_status(response: Dict[str, Any]) -> bool:
        """
        Parse API response to determine if vehicle is exempted

        Args:
            response: API response dict

        Returns:
            True if vehicle is exempted
        """
        if not response:
            return False

        # Check various fields that might indicate exemption
        status_text = response.get("status", "").lower()
        message = response.get("message", "").lower()
        data_text = json.dumps(response).lower()

        exemption_keywords = [
            "osvobozeno",  # exempted
            "osvobozen",   # exempted (variant)
            "vyňat",       # exempt
            "vynecha",     # omitted
            "bezplatně",   # free/exempt
        ]

        for keyword in exemption_keywords:
            if keyword in status_text or keyword in message or keyword in data_text:
                return True

        return False

    @staticmethod
    def _get_exemption_reason(response: Dict[str, Any]) -> Optional[str]:
        """
        Extract exemption reason from API response

        Args:
            response: API response dict

        Returns:
            Exemption reason or None
        """
        # Common fields that might contain reason
        for field in ["reason", "message", "status", "description", "info"]:
            if field in response and isinstance(response[field], str):
                return response[field]

        return None


# Global service instance
_edalnice_service: Optional[EdalniceCzService] = None


def get_edalnice_service() -> EdalniceCzService:
    """Get or create global Edalnice service instance"""
    global _edalnice_service
    if _edalnice_service is None:
        _edalnice_service = EdalniceCzService()
    return _edalnice_service


async def query_plate_status(plate: str) -> Dict[str, Any]:
    """Query vehicle exemption status for a plate"""
    service = get_edalnice_service()
    return await service.query_vehicle(plate)
