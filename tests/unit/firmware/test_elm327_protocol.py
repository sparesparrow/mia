"""Host-side contract coverage for the ESP32 ELM327 firmware protocol."""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.req("REQ-HW-008")

ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_DIR = ROOT / "apps" / "esp32" / "elm327-emulator"
PROTOCOL_TEST = ROOT / "tests" / "unit" / "firmware" / "elm327_protocol_test.cpp"


def test_elm327_protocol_contract(tmp_path):
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.fail("g++ is required for the REQ-HW-008 host contract test")

    executable = tmp_path / "elm327_protocol_test"
    subprocess.run(
        [
            compiler,
            "-std=c++11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-I",
            str(FIRMWARE_DIR / "src"),
            str(PROTOCOL_TEST),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run([str(executable)], check=True, capture_output=True, text=True)
