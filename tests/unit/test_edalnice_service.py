"""EdalniceCzService on top of a stubbed EdalniceClient: result mapping, caching and error handling."""

import io
import urllib.error
from datetime import datetime, timezone

import pytest

from services.edalnice_client import Status, VignetteCheckResult
from services.edalnice_service import EdalniceCzService


class StubClient:
    def __init__(self, *results):
        self._results = list(results)
        self.calls = []

    def check_plate(self, plate, country=None):
        self.calls.append((plate, country))
        result = self._results[min(len(self.calls) - 1, len(self._results) - 1)]
        if isinstance(result, Exception):
            raise result
        return result


def make_service(tmp_path, *results):
    client = StubClient(*results)
    return EdalniceCzService(cache_dir=str(tmp_path), client=client), client


VALID = VignetteCheckResult(
    status=Status.VALID,
    valid_from=datetime(2026, 9, 1, tzinfo=timezone.utc),
    valid_until=datetime(2027, 9, 1, tzinfo=timezone.utc),
)


async def test_valid_vignette_maps_to_success(tmp_path):
    service, client = make_service(tmp_path, VALID)
    result = await service.query_vehicle("1p3 5010")

    assert client.calls == [("1P35010", "CZ")]
    assert result["status"] == "success"
    assert result["plate"] == "1P35010"
    assert result["vignette_status"] == "valid"
    assert result["has_valid_vignette"] is True
    assert result["is_exempted"] is False
    assert result["exemption_reason"] is None
    assert result["valid_until"] == "2027-09-01T00:00:00+00:00"


async def test_exempt_vehicle_raises_the_anpr_alert_fields(tmp_path):
    service, _ = make_service(tmp_path, VignetteCheckResult(status=Status.EXEMPT))
    result = await service.query_vehicle("1P35010")

    assert result["is_exempted"] is True
    assert result["exemption_reason"] == EdalniceCzService.STATUS_EXEMPTED


async def test_possibly_exempt_vehicle(tmp_path):
    service, _ = make_service(
        tmp_path, VignetteCheckResult(status=Status.POSSIBLY_EXEMPT, exemption_reason_ids=["reason-a"])
    )
    result = await service.query_vehicle("1P35010")

    assert result["is_exempted"] is False
    assert result["possibly_exempted"] is True
    assert result["exemption_reason_ids"] == ["reason-a"]
    assert result["exemption_reason"] == EdalniceCzService.STATUS_POSSIBLY_EXEMPTED


async def test_success_is_cached_in_memory_and_on_disk(tmp_path):
    service, client = make_service(tmp_path, VALID)
    first = await service.query_vehicle("1P35010")
    second = await service.query_vehicle("1P35010")
    assert second == first
    assert len(client.calls) == 1

    fresh, fresh_client = make_service(tmp_path, VignetteCheckResult(status=Status.INVALID))
    assert (await fresh.query_vehicle("1P35010"))["vignette_status"] == "valid"
    assert fresh_client.calls == []


@pytest.mark.parametrize(
    "error, expected",
    [
        (urllib.error.HTTPError("", 503, "unavailable", {}, io.BytesIO(b"")), "HTTP 503"),
        (urllib.error.URLError("no route to host"), "no route to host"),
        (RuntimeError("credentials not found"), "credentials not found"),
    ],
)
async def test_failures_are_reported_as_unknown_and_not_cached(tmp_path, error, expected):
    service, client = make_service(tmp_path, error, VALID)
    result = await service.query_vehicle("1P35010")

    assert result["status"] == "unknown"
    assert expected in result["error"]

    retried = await service.query_vehicle("1P35010")
    assert retried["status"] == "success"
    assert len(client.calls) == 2
