import base64
import io
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pytest

from services import edalnice_client as ed
from services.edalnice_client import (
    CountryNotFoundError,
    CredentialsNotFoundError,
    EdalniceClient,
    Status,
)

pytestmark = pytest.mark.req("REQ-ANPR-002")

CZ_ID = "3906ba89-153c-4038-8e36-0ca1deb76076"
COUNTRIES = {"items": [{"id": CZ_ID, "code": "CZ"}, {"id": "de-id", "code": "DE"}]}

VALID_PAYLOAD = {"registrations": [{"validFrom": "2026-01-01T00:00:00Z", "validTo": "2027-01-01T00:00:00Z"}]}


class FakeResponse:
    def __init__(self, body):
        if isinstance(body, str):
            body = body.encode()
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code, payload=None):
    body = json.dumps(payload or {"type": "ERROR", "title": "http error"}).encode()
    return urllib.error.HTTPError("", code, "HTTP Error", {}, io.BytesIO(body))


def url_of(obj):
    return getattr(obj, "full_url", obj)


class FakeOpener:
    def __init__(self):
        self.calls = []
        self._routes = []

    def add(self, matcher, response):
        self._routes.append((matcher, response))
        return self

    def __call__(self, url, timeout=15):
        self.calls.append(url)
        for matcher, response in self._routes:
            if matcher(url):
                if callable(response) and not isinstance(response, FakeResponse):
                    response = response(url)
                if isinstance(response, Exception):
                    raise response
                return response
        raise AssertionError(f"no route for {url_of(url)!r}")


def matches_token(url):
    return url_of(url) == ed.AUTH_TOKEN_URL


def matches_countries(url):
    return url_of(url).startswith(ed.API_BASE + "/api/v3/enums/countries")


def matches_registrations(url):
    return url_of(url).startswith(ed.API_BASE + "/api/v3/charge_registrations/")


def is_post(obj):
    return isinstance(obj, urllib.request.Request)


def sequenced(*items):
    state = {"i": 0}

    def factory(_url):
        item = items[min(state["i"], len(items) - 1)]
        state["i"] += 1
        return item

    return factory


def happy_opener(payload=VALID_PAYLOAD):
    opener = FakeOpener()
    opener.add(matches_token, FakeResponse({"access_token": "tok-1", "expires_in": 3600}))
    opener.add(matches_countries, FakeResponse(COUNTRIES))
    opener.add(matches_registrations, FakeResponse(payload))
    return opener


def make_client(opener, clock=lambda: 0.0, **kwargs):
    kwargs.setdefault("credentials", "eshop.client:test-secret")
    return EdalniceClient(opener=opener, clock=clock, **kwargs)


def test_credentials_from_environment_skips_js_scrape(monkeypatch):
    monkeypatch.setenv(ed.ENV_CREDENTIALS, "eshop.client:env-secret")
    opener = happy_opener()
    client = EdalniceClient(opener=opener)
    result = client.check_plate("1P35010")
    assert result.status == Status.VALID
    assert all(url_of(c) != ed.SITE_BASE + "/cs" for c in opener.calls)


def test_credentials_discovered_from_js_chunk(monkeypatch):
    monkeypatch.delenv(ed.ENV_CREDENTIALS, raising=False)
    chunk_path = "/_next/static/chunks/abc123.js"
    homepage = f'<html><script src="{chunk_path}"></script></html>'
    js = 'var x = "eshop.client:discovered-secret";'
    opener = happy_opener()
    opener.add(lambda u: url_of(u) == ed.SITE_BASE + "/cs", FakeResponse(homepage))
    opener.add(lambda u: url_of(u) == ed.SITE_BASE + chunk_path, FakeResponse(js))

    client = EdalniceClient(opener=opener)
    client.check_plate("1P35010")

    posts = [c for c in client.opener.calls if is_post(c) and matches_token(c)]
    expected = "Basic " + base64.b64encode(b"eshop.client:discovered-secret").decode()
    assert posts[0].get_header("Authorization") == expected


def test_credentials_not_found_raises(monkeypatch):
    monkeypatch.delenv(ed.ENV_CREDENTIALS, raising=False)
    opener = FakeOpener()
    opener.add(
        lambda u: url_of(u) == ed.SITE_BASE + "/cs", FakeResponse('<script src="/_next/static/chunks/a.js"></script>')
    )
    opener.add(lambda u: url_of(u).endswith("a.js"), FakeResponse("var x=1;"))
    client = EdalniceClient(opener=opener)
    with pytest.raises(CredentialsNotFoundError):
        client.check_plate("1P35010")


def test_token_cached_for_lifetime():
    opener = happy_opener()
    client = make_client(opener)
    client.check_plate("1P35010")
    client.check_plate("2B12345")
    token_posts = [c for c in opener.calls if is_post(c) and matches_token(c)]
    assert len(token_posts) == 1


def test_token_refetched_after_3600_seconds():
    t = {"now": 0.0}
    opener = happy_opener()
    client = make_client(opener, clock=lambda: t["now"])
    client.check_plate("1P35010")

    t["now"] = 3500.0
    client.check_plate("1P35010")
    n_tokens = sum(1 for c in opener.calls if is_post(c) and matches_token(c))
    assert n_tokens == 1

    t["now"] = 3605.0
    client.check_plate("1P35010")
    n_tokens = sum(1 for c in opener.calls if is_post(c) and matches_token(c))
    assert n_tokens == 2


def test_retry_once_on_401_fetches_new_token():
    opener = FakeOpener()
    opener.add(
        matches_token,
        sequenced(
            FakeResponse({"access_token": "tok-1", "expires_in": 3600}),
            FakeResponse({"access_token": "tok-2", "expires_in": 3600}),
        ),
    )
    opener.add(matches_countries, FakeResponse(COUNTRIES))
    opener.add(
        matches_registrations,
        sequenced(
            http_error(401, {"type": "TOKEN_EXPIRED", "title": "expired"}),
            FakeResponse(VALID_PAYLOAD),
        ),
    )
    client = make_client(opener)
    result = client.check_plate("1P35010")

    assert result.status == Status.VALID
    gets = [c for c in opener.calls if is_post(c) and matches_registrations(c)]
    assert gets[-1].get_header("Authorization") == "Bearer tok-2"


def test_second_401_raises():
    opener = FakeOpener()
    opener.add(matches_token, FakeResponse({"access_token": "tok-1", "expires_in": 3600}))
    opener.add(matches_countries, FakeResponse(COUNTRIES))
    opener.add(matches_registrations, http_error(401, {"type": "X", "title": "x"}))
    client = make_client(opener)
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        client.check_plate("1P35010")
    assert excinfo.value.code == 401


def test_country_lookup_defaults_to_cz():
    opener = happy_opener()
    make_client(opener).check_plate("1P35010")
    reg_calls = [c for c in opener.calls if matches_registrations(c)]
    assert f"/{CZ_ID}/" in url_of(reg_calls[0])


def test_plate_normalized_uppercase_no_spaces():
    opener = happy_opener()
    make_client(opener).check_plate(" 1p3 5010 ")
    reg_calls = [c for c in opener.calls if matches_registrations(c)]
    assert url_of(reg_calls[0]).endswith("/1P35010")


def test_unknown_country_raises():
    client = make_client(happy_opener())
    with pytest.raises(CountryNotFoundError):
        client.check_plate("1P35010", country="XX")


def test_country_list_accepts_bare_list_shape():
    opener = FakeOpener()
    opener.add(matches_token, FakeResponse({"access_token": "t", "expires_in": 3600}))
    opener.add(matches_countries, FakeResponse(COUNTRIES["items"]))
    opener.add(matches_registrations, FakeResponse(VALID_PAYLOAD))
    assert make_client(opener).check_plate("1P35010", country="DE").status == Status.VALID
    reg_calls = [c for c in opener.calls if matches_registrations(c)]
    assert "/de-id/" in url_of(reg_calls[0])


def test_cz_resolved_without_fetching_country_list():
    opener = happy_opener()
    make_client(opener).check_plate("1P35010")
    assert not any(matches_countries(c) for c in opener.calls)


def test_country_list_fetched_once_per_code():
    opener = happy_opener()
    client = make_client(opener)
    client.check_plate("1P35010", country="de")
    client.check_plate("2B12345", country="DE")
    assert sum(1 for c in opener.calls if matches_countries(c)) == 1


NOW = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"isExempt": True, "registrations": []}, Status.EXEMPT),
        ({"state": "EXEMPT", "registrations": []}, Status.EXEMPT),
        ({"isPossiblyExempt": True, "registrations": []}, Status.POSSIBLY_EXEMPT),
        ({"state": "POSSIBLY_EXEMPT", "registrations": []}, Status.POSSIBLY_EXEMPT),
        (VALID_PAYLOAD, Status.VALID),
        ({"registrations": []}, Status.INVALID),
        ({"registrations": [{"validFrom": "2020-01-01T00:00:00Z", "validTo": "2021-01-01T00:00:00Z"}]}, Status.INVALID),
        (
            {"chargeRegistrations": [{"validityFrom": "2026-09-01T00:00:00Z", "validityTo": "2026-10-01T00:00:00Z"}]},
            Status.VALID,
        ),
    ],
)
def test_classify_rule(payload, expected):
    result = EdalniceClient(credentials="x:y").classify(payload, now=NOW)
    assert result.status == expected


def test_classify_returns_validity_dates():
    result = EdalniceClient(credentials="x:y").classify(VALID_PAYLOAD, now=NOW)
    assert result.valid_from == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert result.valid_until == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_classify_invalid_reports_last_window():
    payload = {
        "registrations": [
            {"validFrom": "2019-01-01T00:00:00", "validTo": "2020-01-01T00:00:00"},
            {"validFrom": "2021-01-01T00:00:00+00:00", "validTo": "2022-06-01T00:00:00Z"},
        ]
    }
    result = EdalniceClient(credentials="x:y").classify(payload, now=NOW)
    assert result.status == Status.INVALID
    assert result.valid_until == datetime(2022, 6, 1, tzinfo=timezone.utc)


def test_bad_request_maps_to_invalid_with_detail():
    opener = FakeOpener()
    opener.add(matches_token, FakeResponse({"access_token": "t", "expires_in": 3600}))
    opener.add(matches_countries, FakeResponse(COUNTRIES))
    opener.add(
        matches_registrations,
        http_error(400, {"type": "NO_VALID_REGISTRATION", "title": "No valid electronic vignette"}),
    )
    result = make_client(opener).check_plate("ABC")
    assert result.status == Status.INVALID
    assert result.detail == "No valid electronic vignette"


# Response shape of the live API, as returned by the site's validity check
# (GET /api/v3/charge_registrations/{countryId}/{plate}).
def live_payload(**overrides):
    payload = {
        "vehicle": {"licensePlate": "1P35010", "countryId": CZ_ID},
        "isGivenExemption": False,
        "possibleExemptionReasonIds": [],
        "charges": [],
    }
    payload.update(overrides)
    return payload


def charge(since, until, current):
    return {"priceListItemId": "item-1", "validSince": since, "validUntil": until, "isCurrentlyValid": current}


def test_live_shape_no_charges_is_invalid():
    result = EdalniceClient(credentials="x:y").classify(live_payload(), now=NOW)
    assert result.status == Status.INVALID
    assert result.valid_from is None and result.valid_until is None


def test_live_shape_given_exemption():
    result = EdalniceClient(credentials="x:y").classify(live_payload(isGivenExemption=True), now=NOW)
    assert result.status == Status.EXEMPT


def test_live_shape_possible_exemption_keeps_reason_ids():
    payload = live_payload(possibleExemptionReasonIds=["reason-a", "reason-b"])
    result = EdalniceClient(credentials="x:y").classify(payload, now=NOW)
    assert result.status == Status.POSSIBLY_EXEMPT
    assert result.exemption_reason_ids == ["reason-a", "reason-b"]


def test_live_shape_exemption_wins_over_valid_charge():
    payload = live_payload(
        isGivenExemption=True,
        charges=[charge("2026-09-01T00:00:00+02:00", "2026-10-01T00:00:00+02:00", True)],
    )
    assert EdalniceClient(credentials="x:y").classify(payload, now=NOW).status == Status.EXEMPT


def test_live_shape_currently_valid_charge():
    payload = live_payload(charges=[charge("2026-09-01T00:00:00+02:00", "2026-10-01T00:00:00+02:00", True)])
    result = EdalniceClient(credentials="x:y").classify(payload, now=NOW)
    assert result.status == Status.VALID
    assert result.valid_from == datetime(2026, 8, 31, 22, 0, tzinfo=timezone.utc)
    assert result.valid_until == datetime(2026, 9, 30, 22, 0, tzinfo=timezone.utc)


def test_live_shape_trusts_is_currently_valid_over_local_clock():
    # The server's verdict wins: a charge whose dates cover `now` but that the
    # site says is not currently valid does not make the vehicle valid.
    payload = live_payload(charges=[charge("2026-09-01T00:00:00Z", "2026-10-01T00:00:00Z", False)])
    result = EdalniceClient(credentials="x:y").classify(payload, now=NOW)
    assert result.status == Status.INVALID


def test_live_shape_upcoming_charge_is_invalid_with_its_dates():
    payload = live_payload(charges=[charge("2026-10-01T00:00:00Z", "2026-10-11T00:00:00Z", False)])
    result = EdalniceClient(credentials="x:y").classify(payload, now=NOW)
    assert result.status == Status.INVALID
    assert result.valid_from == datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_live_shape_end_to_end():
    payload = live_payload(charges=[charge("2026-09-01T00:00:00Z", "2027-09-01T00:00:00Z", True)])
    result = make_client(happy_opener(payload)).check_plate("1P35010")
    assert result.status == Status.VALID
    assert ed.result_to_dict(result) == {
        "vignette_status": "valid",
        "valid_from": "2026-09-01T00:00:00+00:00",
        "valid_until": "2027-09-01T00:00:00+00:00",
        "detail": None,
        "exemption_reason_ids": [],
    }
