"""
Edalnice Integration Service
Checks a plate's Czech electronic vignette (or exemption) on edalnice.gov.cz,
with an in-memory and on-disk cache in front of services.edalnice_client.
"""

import asyncio
import hashlib
import json
import logging
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from services.edalnice_client import (
    EdalniceClient,
    Status,
    VignetteCheckResult,
    result_to_dict,
)

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

    # Status texts
    STATUS_EXEMPTED = "Vozidlo osvobozeno"
    STATUS_POSSIBLY_EXEMPTED = "Vozidlo může být osvobozeno"

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_ttl_hours: int = 24,
        client: Optional[EdalniceClient] = None,
        country: str = "CZ",
    ):
        """
        Initialize Edalnice service

        Args:
            cache_dir: Directory for local cache
            cache_ttl_hours: Cache TTL in hours (default: 24)
            client: edalnice.gov.cz client (default: one reading EDALNICE_CLIENT_CREDENTIALS)
            country: Registration country of the plates looked up (default: CZ)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "edalnice"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_hours = cache_ttl_hours
        self._memory_cache: Dict[str, EdalniceCacheEntry] = {}
        self._initialized = False
        self._client = client or EdalniceClient()
        self.country = country

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
        Check the plate's electronic vignette on edalnice.gov.cz

        Args:
            plate: Clean plate text (no spaces)

        Returns:
            Result dict, with "status": "error" if the lookup failed
        """
        try:
            if not self._initialized:
                await self.initialize()

            result = await asyncio.to_thread(self._client.check_plate, plate, self.country)
            info = result_to_dict(result)
            is_exempted = result.status == Status.EXEMPT
            return {
                "status": "success",
                "plate": plate,
                "country": self.country,
                **info,
                "is_exempted": is_exempted,
                "possibly_exempted": result.status == Status.POSSIBLY_EXEMPT,
                "has_valid_vignette": result.status == Status.VALID,
                "exemption_reason": self._exemption_reason(result),
                "timestamp": datetime.now().isoformat(),
            }

        except urllib.error.HTTPError as e:
            logger.warning(f"edalnice.gov.cz answered HTTP {e.code} for {plate}")
            return {"status": "error", "error": f"HTTP {e.code}"}
        except (urllib.error.URLError, TimeoutError) as e:
            logger.warning(f"Could not reach edalnice.gov.cz for {plate}: {e}")
            return {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"Error querying edalnice.gov.cz: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _exemption_reason(result: VignetteCheckResult) -> Optional[str]:
        """Human-readable reason for the ANPR alert, in the site's own wording"""
        if result.status == Status.EXEMPT:
            return EdalniceCzService.STATUS_EXEMPTED
        if result.status == Status.POSSIBLY_EXEMPT:
            return EdalniceCzService.STATUS_POSSIBLY_EXEMPTED
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
