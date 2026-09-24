"""Read-only client for the Czech electronic vignette check at edalnice.gov.cz.

Mirrors what the site's "Ověření platnosti" form does:

1. ``POST auth.edalnice.gov.cz/auth/connect/token`` (client-credentials grant,
   HTTP Basic as the public web client ``eshop.client``) for a bearer token.
2. ``GET eshop.edalnice.gov.cz/api/v3/charge_registrations/{countryId}/{plate}``.

The client credentials come from ``EDALNICE_CLIENT_CREDENTIALS`` (``id:secret``)
or, failing that, from the site's JavaScript at runtime; none are stored here.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

SITE_BASE = "https://edalnice.gov.cz"
AUTH_TOKEN_URL = "https://auth.edalnice.gov.cz/auth/connect/token"
API_BASE = "https://eshop.edalnice.gov.cz"
API_SCOPE = "eshop.api"

ENV_CREDENTIALS = "EDALNICE_CLIENT_CREDENTIALS"
COUNTRIES_PATH = "/api/v3/enums/countries?include_deleted=false"
REGISTRATIONS_PATH = "/api/v3/charge_registrations/{country_id}/{plate}"

# Country ids observed on the site; others are resolved from the country list.
KNOWN_COUNTRY_IDS = {"CZ": "3906ba89-153c-4038-8e36-0ca1deb76076"}

_CHUNK_RE = re.compile(r"/_next/static/chunks/[A-Za-z0-9_.-]+\.js")
_CREDENTIAL_RE = re.compile(r'"(eshop\.client:[^"\\]+)"')

_TOKEN_SAFETY_SKEW_S = 30

# The live API answers with "charges" / "validSince" / "validUntil"; the other
# names are accepted so a renamed field does not silently read as "invalid".
_REGISTRATION_LIST_KEYS = ("charges", "registrations", "chargeRegistrations", "items")
_VALID_FROM_KEYS = ("validSince", "validFrom", "validityFrom", "valid_from", "from")
_VALID_UNTIL_KEYS = ("validUntil", "validTo", "validityTo", "valid_until", "to", "until")
_COUNTRY_CODE_KEYS = ("code", "countryCode", "iso2", "isoCode", "iso3", "iso")
_COUNTRY_ID_KEYS = ("id", "countryId")


class Status(Enum):
    EXEMPT = "exempt"
    POSSIBLY_EXEMPT = "possibly_exempt"
    VALID = "valid"
    INVALID = "invalid"


@dataclass
class VignetteCheckResult:
    status: Status
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    detail: Optional[str] = None
    exemption_reason_ids: list = field(default_factory=list)


class CredentialsNotFoundError(RuntimeError):
    pass


class CountryNotFoundError(LookupError):
    pass


def _parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _first_present(container, keys):
    for key in keys:
        if key in container and container[key] is not None:
            return container[key]
    return None


class EdalniceClient:
    def __init__(
        self,
        *,
        credentials=None,
        default_country="CZ",
        opener=None,
        clock=time.monotonic,
        timeout=15.0,
    ):
        self._credentials = credentials
        self.default_country = default_country
        self.opener = opener or urllib.request.urlopen
        self.clock = clock
        self.timeout = timeout
        self._token = None
        self._token_expires_at = 0.0
        self._country_ids = dict(KNOWN_COUNTRY_IDS)

    def credentials(self):
        if self._credentials:
            return self._credentials
        env = os.environ.get(ENV_CREDENTIALS)
        if env:
            self._credentials = env
            return env
        self._credentials = self._discover_credentials()
        return self._credentials

    def _discover_credentials(self):
        html = self._fetch_text(f"{SITE_BASE}/cs")
        chunks = sorted(set(_CHUNK_RE.findall(html)))
        for chunk in chunks:
            js = self._fetch_text(SITE_BASE + chunk)
            match = _CREDENTIAL_RE.search(js)
            if match:
                return match.group(1)
        raise CredentialsNotFoundError("eshop.client credentials not found in the site's JavaScript")

    def _get_token(self, *, force=False):
        now = self.clock()
        if not force and self._token and now < self._token_expires_at - _TOKEN_SAFETY_SKEW_S:
            return self._token
        basic = base64.b64encode(self.credentials().encode()).decode()
        request = urllib.request.Request(
            AUTH_TOKEN_URL,
            data=urllib.parse.urlencode({"grant_type": "client_credentials", "scope": API_SCOPE}).encode(),
            headers={
                "Authorization": "Basic " + basic,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        with self.opener(request, timeout=self.timeout) as response:
            payload = json.load(response)
        lifetime = int(payload.get("expires_in", 3600))
        self._token = payload["access_token"]
        self._token_expires_at = now + lifetime
        return self._token

    def _get_json(self, path, *, _retried=False):
        request = urllib.request.Request(
            API_BASE + path,
            headers={
                "Authorization": "Bearer " + self._get_token(),
                "Accept": "application/json",
            },
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 401 and not _retried:
                self._token = None
                self._get_token(force=True)
                return self._get_json(path, _retried=True)
            raise

    def country_id(self, code=None):
        code = (code or self.default_country).upper()
        if code in self._country_ids:
            return self._country_ids[code]
        data = self._get_json(COUNTRIES_PATH)
        items = data.get("items", data) if isinstance(data, Mapping) else data
        for item in items:
            if not isinstance(item, Mapping):
                continue
            item_code = _first_present(item, _COUNTRY_CODE_KEYS)
            if item_code and str(item_code).upper() == code:
                country_id = _first_present(item, _COUNTRY_ID_KEYS)
                self._country_ids[code] = country_id
                return country_id
        raise CountryNotFoundError(f"country code {code!r} not in the site's country list")

    def check_plate(self, plate, country=None):
        country_id = self.country_id(country)
        normalized = plate.upper().replace(" ", "").strip()
        quoted = urllib.parse.quote(normalized, safe="")
        path = REGISTRATIONS_PATH.format(country_id=country_id, plate=quoted)
        try:
            payload = self._get_json(path)
        except urllib.error.HTTPError as error:
            if error.code in (400, 404):
                return VignetteCheckResult(status=Status.INVALID, detail=self._error_detail(error))
            raise
        return self.classify(payload)

    def classify(self, payload, *, now=None):
        """Apply the site's own rule: exempt, possibly exempt, valid, else invalid."""
        now = now or datetime.now(timezone.utc)
        if not isinstance(payload, Mapping):
            raise ValueError(f"unexpected payload type: {type(payload).__name__}")

        state = str(payload.get("state") or payload.get("status") or "").upper()
        reason_ids = list(payload.get("possibleExemptionReasonIds") or [])
        exempt = (
            payload.get("isGivenExemption") is True or bool(payload.get("isExempt")) or payload.get("exempt") is True
        )
        possibly = bool(reason_ids) or bool(payload.get("isPossiblyExempt")) or payload.get("possiblyExempt") is True

        if exempt or state in ("EXEMPT", "EXEMPTED"):
            return VignetteCheckResult(status=Status.EXEMPT)
        if possibly or state in ("POSSIBLY_EXEMPT", "POTENTIALLY_EXEMPT"):
            return VignetteCheckResult(status=Status.POSSIBLY_EXEMPT, exemption_reason_ids=reason_ids)

        windows = self._windows(payload)
        active = [w for w in windows if (w[2] if w[2] is not None else w[0] <= now <= w[1])]
        if active:
            return VignetteCheckResult(
                status=Status.VALID,
                valid_from=min(w[0] for w in active),
                valid_until=max(w[1] for w in active),
            )
        if windows:
            latest = max(windows, key=lambda w: w[1])
            return VignetteCheckResult(status=Status.INVALID, valid_from=latest[0], valid_until=latest[1])
        return VignetteCheckResult(status=Status.INVALID)

    @staticmethod
    def _windows(payload):
        """(start, end, isCurrentlyValid-or-None) for every charge with both dates."""
        raw = _first_present(payload, _REGISTRATION_LIST_KEYS) or []
        if isinstance(raw, Mapping):
            raw = [raw]
        windows = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            start = _parse_datetime(_first_present(item, _VALID_FROM_KEYS))
            end = _parse_datetime(_first_present(item, _VALID_UNTIL_KEYS))
            current = item.get("isCurrentlyValid")
            if start and end:
                windows.append((start, end, current if isinstance(current, bool) else None))
        return windows

    def _fetch_text(self, url):
        with self.opener(url, timeout=self.timeout) as response:
            return response.read().decode("utf-8", "replace")

    @staticmethod
    def _error_detail(error):
        try:
            payload = json.loads(error.read().decode("utf-8", "replace"))
        except Exception:
            return None
        if isinstance(payload, Mapping):
            return payload.get("title") or payload.get("detail") or payload.get("type") or None
        return None


def result_to_dict(result: VignetteCheckResult) -> dict[str, Any]:
    """JSON-friendly form of a check result."""
    return {
        "vignette_status": result.status.value,
        "valid_from": result.valid_from.isoformat() if result.valid_from else None,
        "valid_until": result.valid_until.isoformat() if result.valid_until else None,
        "detail": result.detail,
        "exemption_reason_ids": list(result.exemption_reason_ids),
    }
