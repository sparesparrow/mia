"""Regression tests for scripts/ensure-bundled-cpython.sh."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "ensure-bundled-cpython.sh"


def _bash_is_usable() -> bool:
    """Return True when a working POSIX bash is on PATH.

    On Windows the ``bash`` shim often resolves to WSL without an installed
    distribution, which fails for reasons unrelated to the script under test.
    """
    try:
        result = subprocess.run(
            ["bash", "-c", "exit 0"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


BASH_AVAILABLE = _bash_is_usable()


@unittest.skipUnless(BASH_AVAILABLE, "a working bash interpreter is required")
class TestEnsureBundledCPythonScript(unittest.TestCase):
    def test_script_dry_run_generates_environment_and_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env_file = tmp_path / "environment"
            wrapper_file = tmp_path / "mia-python"
            systemd_dir = tmp_path / "systemd"
            systemd_dir.mkdir()

            env = os.environ.copy()
            env.update(
                {
                    "MIA_USE_SUDO": "0",
                    "MIA_ENV_FILE": str(env_file),
                    "MIA_PYTHON_WRAPPER": str(wrapper_file),
                    "MIA_SYSTEMD_DIR": str(systemd_dir),
                }
            )

            result = subprocess.run(
                ["bash", str(SCRIPT_PATH), "/usr"],
                cwd=REPO_ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue(env_file.exists())
            self.assertTrue(wrapper_file.exists())
            self.assertTrue(os.access(wrapper_file, os.X_OK))

            env_contents = env_file.read_text(encoding="utf-8")
            wrapper_contents = wrapper_file.read_text(encoding="utf-8")

            self.assertIn("PYTHONHOME=/usr", env_contents)
            self.assertIn("MIA_PYTHON=/usr/bin/python3", env_contents)
            self.assertIn("PYTHONNOUSERSITE=1", env_contents)
            self.assertIn('exec "/usr/bin/python3" "$@"', wrapper_contents)
            self.assertIn('export PYTHONHOME="/usr"', wrapper_contents)
            self.assertIn("MIA Python setup verified", result.stdout)

    def test_script_remains_shell_syntax_valid(self):
        subprocess.run(
            ["bash", "-n", str(SCRIPT_PATH)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()