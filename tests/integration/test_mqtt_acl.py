"""The secure broker's ACL (ADR-0026): a real mosquitto with secure.conf's auth settings, the
committed acl file and users made by scripts/mqtt-users.sh, driven with mosquitto_pub/_sub.
"""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.req("REQ-SEC-004")]

ROOT = Path(__file__).resolve().parents[2]
ACL = ROOT / "infra/edge/pi-gateway/services/mosquitto/acl"
SECURE_CONF = ROOT / "infra/edge/pi-gateway/services/mosquitto/secure.conf"
USERS_SCRIPT = ROOT / "infra/edge/pi-gateway/scripts/mqtt-users.sh"
ROLES = ("pi-backend", "android", "esp32-obd", "phone-assistant")
VIN = "WAUZZZ8H04K000001"

needs = [shutil.which(t) for t in ("mosquitto", "mosquitto_pub", "mosquitto_sub", "mosquitto_passwd")]
if not all(needs):
    pytest.skip("mosquitto and its clients are not installed", allow_module_level=True)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


SECRETS = {}
CREDENTIALS = []


@pytest.fixture(scope="module")
def broker(tmp_path_factory):
    d = tmp_path_factory.mktemp("mqtt")
    users = subprocess.run(
        [str(USERS_SCRIPT)],
        env={**os.environ, "MQTT_PASSWORDS_DIR": str(d)},
        capture_output=True,
        text=True,
        check=True,
    )
    passwd = d / "credentials"
    CREDENTIALS[:] = [passwd]
    for role in ROLES:
        SECRETS[role] = (d / f"{role}.secret").read_text()
        assert SECRETS[role] not in users.stdout + users.stderr  # never printed
    port = free_port()
    conf = d / "mosquitto.conf"
    conf.write_text(
        f"listener {port} 127.0.0.1\n"
        "allow_anonymous false\n"
        f"password_file {passwd}\n"
        f"acl_file {ACL}\n"
        "persistence false\n"
    )
    proc = subprocess.Popen(
        ["mosquitto", "-c", str(conf)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("mosquitto did not start: " + proc.stderr.read().decode(errors="replace"))
    yield port
    proc.terminate()
    proc.wait(timeout=5)


def auth(role):
    return ["-u", role, "-P", SECRETS[role]] if role else []


def delivered(port: int, publisher: str, topic: str) -> bool:
    """Does a message `publisher` sends to `topic` reach a pi-backend subscriber?"""
    sub = subprocess.Popen(
        [
            "mosquitto_sub",
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            *auth("pi-backend"),
            "-t",
            topic,
            "-C",
            "1",
            "-W",
            "3",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    time.sleep(0.5)
    subprocess.run(
        [
            "mosquitto_pub",
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            *auth(publisher),
            "-q",
            "1",
            "-t",
            topic,
            "-m",
            "probe",
        ],
        capture_output=True,
        timeout=10,
    )
    out, _ = sub.communicate(timeout=10)
    return out.strip() == "probe"


def test_secure_conf_uses_the_acl_and_refuses_anonymous():
    conf = SECURE_CONF.read_text()
    assert "allow_anonymous false" in conf
    assert "acl_file /mosquitto/config/acl" in conf


def test_users_script_makes_one_hashed_user_per_acl_role(broker):
    lines = [line for line in CREDENTIALS[0].read_text().splitlines() if line]
    assert sorted(line.split(":")[0] for line in lines) == sorted(ROLES)
    assert all(":$7$" in line for line in lines)  # hashed, no plain passwords


def test_wrong_password_is_refused(broker):
    r = subprocess.run(
        [
            "mosquitto_pub",
            "-h",
            "127.0.0.1",
            "-p",
            str(broker),
            "-u",
            "phone-assistant",
            "-P",
            "not-the-password",
            "-t",
            "mia/lights/x",
            "-m",
            "on",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode != 0


def test_anonymous_client_is_refused(broker):
    r = subprocess.run(
        [
            "mosquitto_pub",
            "-h",
            "127.0.0.1",
            "-p",
            str(broker),
            "-t",
            "mia/lights/x",
            "-m",
            "on",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode != 0
    assert "not authori" in (r.stderr + r.stdout).lower()


@pytest.mark.parametrize(
    "role, topic",
    [
        ("phone-assistant", "mia/lights/living-room"),
        ("android", f"vehicle/telemetry/{VIN}/obd"),
        ("android", "system/session/s1"),
        ("esp32-obd", "mia/telemetry/rpm"),
        ("pi-backend", f"vehicle/cmd/{VIN}/io"),
    ],
)
def test_each_role_reaches_its_own_topics(broker, role, topic):
    assert delivered(broker, role, topic)


@pytest.mark.parametrize(
    "role, topic",
    [
        ("phone-assistant", f"vehicle/cmd/{VIN}/io"),
        ("phone-assistant", "mia/telemetry/rpm"),
        ("phone-assistant", "zigbee2mqtt/plug/set"),
        ("android", f"vehicle/cmd/{VIN}/io"),
        ("esp32-obd", f"vehicle/cmd/{VIN}/io"),
        ("esp32-obd", "mia/lights/living-room"),
    ],
)
def test_no_role_but_the_pi_sends_commands_or_strays(broker, role, topic):
    assert not delivered(broker, role, topic)
