"""Test harness for ai-platform-controllers/linux: ProcessInfo, SystemManager.

Covers ProcessInfo dataclass construction, execute_command() success + timeout paths,
and SystemManager.platform attribute.

aiohttp and websockets are mocked before module load.
"""

import asyncio
import importlib.util
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock aiohttp + websockets before loading the module
# ---------------------------------------------------------------------------
sys.modules.setdefault("aiohttp", MagicMock())
sys.modules.setdefault("websockets", MagicMock())

_LINUX_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "ai-platform-controllers",
    "linux",
    "main.py",
)

_linux_spec = importlib.util.spec_from_file_location("ai_platform_linux_main", _LINUX_PATH)
_linux_module = importlib.util.module_from_spec(_linux_spec)
_linux_module.__package__ = "modules.ai_platform_controllers.linux"
sys.modules.setdefault("modules.ai_platform_controllers", MagicMock())
sys.modules.setdefault("modules.ai_platform_controllers.linux", MagicMock())
_linux_spec.loader.exec_module(_linux_module)

ProcessInfo = _linux_module.ProcessInfo
SystemManager = _linux_module.SystemManager


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestProcessInfo:
    """ProcessInfo dataclass construction."""

    def test_basic_construction(self):
        p = ProcessInfo(pid=1234, name="python3", status="running", cpu_percent=2.5, memory_mb=128.0)
        assert p.pid == 1234
        assert p.name == "python3"
        assert p.status == "running"
        assert p.cpu_percent == 2.5
        assert p.memory_mb == 128.0

    def test_zero_resource_usage(self):
        p = ProcessInfo(pid=1, name="systemd", status="sleeping", cpu_percent=0.0, memory_mb=0.0)
        assert p.cpu_percent == 0.0
        assert p.memory_mb == 0.0

    def test_high_cpu_process(self):
        p = ProcessInfo(pid=9999, name="ffmpeg", status="running", cpu_percent=99.9, memory_mb=512.0)
        assert p.cpu_percent == 99.9


@pytest.mark.unit
class TestSystemManagerPlatform:
    """SystemManager platform attribute."""

    def test_platform_is_linux(self):
        manager = SystemManager()
        assert manager.platform == "linux"


@pytest.mark.unit
class TestSystemManagerExecuteCommand:
    """SystemManager.execute_command() with mocked subprocess."""

    def setup_method(self):
        self.manager = SystemManager()

    @pytest.mark.asyncio
    async def test_successful_command_returns_stdout(self):
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"hello world", b""))

        with patch("asyncio.create_subprocess_shell", return_value=mock_process):
            result = await self.manager.execute_command("echo hello world")

        assert result["success"] is True
        assert result["returncode"] == 0
        assert result["stdout"] == "hello world"
        assert result["stderr"] == ""
        assert result["command"] == "echo hello world"

    @pytest.mark.asyncio
    async def test_failed_command_returns_success_false(self):
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"error: not found"))

        with patch("asyncio.create_subprocess_shell", return_value=mock_process):
            result = await self.manager.execute_command("false")

        assert result["success"] is False
        assert result["returncode"] == 1
        assert "error: not found" in result["stderr"]

    @pytest.mark.asyncio
    async def test_timeout_kills_process_and_reports_error(self):
        mock_process = MagicMock()
        mock_process.kill = MagicMock()
        # Make communicate block until timeout
        async def _slow_communicate():
            await asyncio.sleep(10)
            return b"", b""
        mock_process.communicate = _slow_communicate

        with patch("asyncio.create_subprocess_shell", return_value=mock_process):
            result = await self.manager.execute_command("sleep 10", timeout=0)

        assert result["success"] is False
        assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_during_command_returns_error(self):
        with patch("asyncio.create_subprocess_shell", side_effect=OSError("permission denied")):
            result = await self.manager.execute_command("restricted_cmd")

        assert result["success"] is False
        assert "permission denied" in result["error"]
