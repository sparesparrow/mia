"""The MQTT contract's command safety classes agree with the secure broker's ACL (issue #282).

spec/interfaces/topics.md classifies every command topic as `direct` (publish without asking)
or `confirm` (a human yes first). The ACL (ADR-0026) must not let the phone assistant write
anything that is not `direct`, and only the Pi may write vehicle commands.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("REQ-SEC-004")]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOPICS = REPO_ROOT / "spec" / "interfaces" / "topics.md"
ACL = REPO_ROOT / "infra" / "edge" / "pi-gateway" / "services" / "mosquitto" / "acl"


def section(md: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    assert m, f"topics.md has no '## {heading}' section"
    return m.group(1)


def light_table() -> dict[str, str]:
    """topic template -> safety class, from the Home Lights table."""
    rows = {}
    for line in section(TOPICS.read_text(encoding="utf-8"), "Home Lights and the Phone Assistant").splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) == 5 and cells[0].startswith("`"):
            rows[cells[0].strip("`")] = re.match(r"`(\w+)`", cells[4]).group(1)
    return rows


def acl_writes() -> dict[str, list[str]]:
    """user -> topic patterns it may write (write or readwrite)."""
    writes: dict[str, list[str]] = {}
    user = None
    for line in ACL.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts[:1] == ["user"]:
            user = parts[1]
            writes.setdefault(user, [])
        elif parts[:1] == ["topic"] and user and parts[1] in ("write", "readwrite"):
            writes[user].append(parts[2])
    return writes


def sample(template: str) -> str:
    """vehicle/cmd/{vin}/io -> vehicle/cmd/vin/io: a concrete topic to match against the ACL."""
    return re.sub(r"\{([^}]+)\}", r"\1", template)


def matches(pattern: str, topic: str) -> bool:
    """MQTT wildcard match: + is one level, a trailing # is any number of levels (also none)."""
    p, t = pattern.split("/"), topic.split("/")
    for i, part in enumerate(p):
        if part == "#":
            return True
        if i >= len(t) or (part != "+" and part != t[i]):
            return False
    return len(p) == len(t)


def test_every_light_topic_has_a_known_class():
    table = light_table()
    assert {"mia/lights/mood", "mia/lights/effect", "mia/lights/off", "mia/lights/sound"} <= set(table)
    assert set(table.values()) <= {"direct", "confirm"}


def test_direct_class_is_only_the_light_engine_topics():
    direct = {t for t, c in light_table().items() if c == "direct"}
    assert direct and all(t.startswith("mia/lights/") for t in direct)


def test_vehicle_commands_and_zigbee_need_confirmation():
    table = light_table()
    assert table["vehicle/cmd/{vin}/io"] == "confirm"
    assert table["zigbee2mqtt/{ieee-address}/set"] == "confirm"


def test_phone_assistant_acl_allows_exactly_the_direct_topics():
    table = light_table()
    phone = acl_writes()["phone-assistant"]
    assert phone, "the ACL has no writable topic for phone-assistant"
    for topic, cls in table.items():
        allowed = any(matches(p, sample(topic)) for p in phone)
        assert allowed == (cls == "direct"), f"phone-assistant {'may' if allowed else 'may not'} write {topic} ({cls})"
    # and nothing outside the light engine's prefix, whatever the table lists
    assert all(p.startswith("mia/lights/") for p in phone)


def test_only_the_pi_may_write_vehicle_commands():
    cmd = sample("vehicle/cmd/{vin}/io")
    writers = {u for u, pats in acl_writes().items() if any(matches(p, cmd) for p in pats)}
    assert writers == {"pi-backend"}


@pytest.mark.parametrize(
    "pattern, topic, ok",
    [
        ("mia/lights/#", "mia/lights/mood", True),
        ("mia/lights/#", "mia/lights", True),
        ("mia/lights/#", "mia/other", False),
        ("vehicle/telemetry/+/obd", "vehicle/telemetry/vin/obd", True),
        ("vehicle/telemetry/+/obd", "vehicle/telemetry/vin/io", False),
        ("device/health/+", "device/health/a/b", False),
    ],
)
def test_wildcard_matching(pattern, topic, ok):
    assert matches(pattern, topic) is ok
