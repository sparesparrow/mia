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


def _resolve_generator_python(install_dir: str) -> tuple[str, str]:
    """Mirror ``find_python_bin`` + Python-home detection from the generator.

    ``ensure-bundled-cpython.sh`` selects the first executable interpreter under
    ``<install_dir>/bin`` and derives ``PYTHONHOME`` from that interpreter's
    ``sys.base_prefix``. Computing the same values here keeps the assertions
    tracking the real generator output on any runner (the resolved interpreter
    name and base prefix differ between hosts) instead of a hardcoded ``/usr``
    layout that only happens to hold on some machines.
    """
    bin_dir = Path(install_dir) / "bin"
    candidates = [bin_dir / "python3", bin_dir / "python"]
    candidates += sorted(bin_dir.glob("python3.*"))
    cpython_bin = next((str(c) for c in candidates if os.access(c, os.X_OK)), "")
    if not cpython_bin:
        raise unittest.SkipTest(f"no bundled python interpreter under {bin_dir}")
    base_prefix = subprocess.run(
        [cpython_bin, "-c", "import sys; print(sys.base_prefix)"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return cpython_bin, base_prefix


class TestEnsureBundledCPythonScript(unittest.TestCase):
    def test_script_dry_run_generates_environment_and_wrapper(self):
        cpython_bin, base_prefix = _resolve_generator_python("/usr")
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

            self.assertIn(f"PYTHONHOME={base_prefix}", env_contents)
            self.assertIn(f"MIA_PYTHON={cpython_bin}", env_contents)
            self.assertIn("PYTHONNOUSERSITE=1", env_contents)
            self.assertIn(f'exec "{cpython_bin}" "$@"', wrapper_contents)
            self.assertIn(f'export PYTHONHOME="{base_prefix}"', wrapper_contents)
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