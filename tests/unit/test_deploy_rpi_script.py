"""Focused tests for the deploy_rpi script."""

import importlib.util
import subprocess
import sys
from pathlib import Path


def load_deploy_rpi_module():
    """Import the deploy_rpi script module for unit testing."""
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "deploy_rpi.py"
    spec = importlib.util.spec_from_file_location("deploy_rpi_script", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_check_connection_returns_false_on_ssh_error(monkeypatch):
    """Connection checks should fail cleanly when SSH execution raises."""
    module = load_deploy_rpi_module()
    deployer = module.RPiDeployer("pi.local")

    def fake_run_ssh_command(*args, **kwargs):
        raise OSError("ssh unavailable")

    monkeypatch.setattr(deployer, "run_ssh_command", fake_run_ssh_command)

    assert deployer.check_connection() is False


def test_check_deployment_marks_checks_false_on_remote_failure(monkeypatch):
    """Deployment checks should report False instead of raising on remote command failures."""
    module = load_deploy_rpi_module()
    deployer = module.RPiDeployer("pi.local")

    def fake_run_ssh_command(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=args[0])

    monkeypatch.setattr(deployer, "run_ssh_command", fake_run_ssh_command)

    checks = deployer.check_deployment()

    assert checks["mia-zeromq-broker_active"] is False
    assert checks["port_5555_listening"] is False
    assert checks["python_env"] is False


def test_create_systemd_services_uses_tempfile_without_name_error(tmp_path, monkeypatch):
    """Systemd service creation should succeed with tempfile available at module scope."""
    module = load_deploy_rpi_module()
    deployer = module.RPiDeployer("pi.local")

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    monkeypatch.setattr(deployer, "run_scp_command", lambda *args, **kwargs: None)
    monkeypatch.setattr(deployer, "run_ssh_command", lambda *args, **kwargs: None)

    assert deployer.create_systemd_services(project_dir) is True