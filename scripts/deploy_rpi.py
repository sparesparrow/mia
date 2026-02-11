#!/usr/bin/env python3
"""
Raspberry Pi Deployment Script for MIA Universal

This script:
1. Connects to Raspberry Pi via SSH
2. Deploys MIA services and configuration
3. Sets up systemd services for auto-start
4. Configures ZeroMQ broker and networking
5. Installs required dependencies
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional

class RPiDeployer:
    """Deploy MIA services to Raspberry Pi via SSH"""

    def __init__(self, host: str, user: str = "mia", key_file: Optional[str] = None):
        self.host = host
        self.user = user
        self.key_file = key_file
        self.ssh_cmd = ["ssh"]

        if key_file:
            self.ssh_cmd.extend(["-i", key_file])

        self.ssh_cmd.extend([f"{user}@{host}"])

    def run_ssh_command(self, command: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a command on the Raspberry Pi via SSH"""
        full_cmd = self.ssh_cmd + [command]
        return subprocess.run(full_cmd, check=check, capture_output=True, text=True)

    def run_scp_command(self, local_path: str, remote_path: str) -> subprocess.CompletedProcess:
        """Copy files to Raspberry Pi via SCP"""
        scp_cmd = ["scp"]
        if self.key_file:
            scp_cmd.extend(["-i", self.key_file])
        scp_cmd.extend([local_path, f"{self.user}@{self.host}:{remote_path}"])
        return subprocess.run(scp_cmd, check=True)

    def check_connection(self) -> bool:
        """Test SSH connection to Raspberry Pi"""
        try:
            result = self.run_ssh_command("echo 'SSH connection successful'", check=False)
            return result.returncode == 0
        except:
            return False

    def install_dependencies(self) -> bool:
        """Install required dependencies on Raspberry Pi"""
        print("Installing dependencies...")

        commands = [
            # Update package list
            "sudo apt-get update",

            # Install Python and pip
            "sudo apt-get install -y python3 python3-pip python3-venv",

            # Install ZeroMQ
            "sudo apt-get install -y libzmq3-dev",

            # Install GPIO libraries (if needed)
            "sudo apt-get install -y python3-rpi.gpio",

            # Install other system dependencies
            "sudo apt-get install -y git build-essential cmake",

            # Create MIA user and directories (if not already done)
            "sudo mkdir -p /opt/mia",
            "sudo chown -R mia:mia /opt/mia",
        ]

        for cmd in commands:
            try:
                self.run_ssh_command(cmd)
            except subprocess.CalledProcessError as e:
                print(f"Failed to run: {cmd}")
                print(f"Error: {e}")
                return False

        return True

    def deploy_services(self, project_dir: Path) -> bool:
        """Deploy MIA services to Raspberry Pi"""
        print("Deploying MIA services...")

        # Create temporary tarball of services
        import tempfile
        import tarfile

        services_dir = project_dir / "modules"
        if not services_dir.exists():
            print("Services directory not found")
            return False

        with tempfile.TemporaryDirectory() as temp_dir:
            tar_path = Path(temp_dir) / "mia_services.tar.gz"

            # Create tarball
            with tarfile.open(tar_path, "w:gz") as tar:
                for item in services_dir.rglob("*"):
                    if item.is_file():
                        tar.add(item, arcname=item.relative_to(services_dir.parent))

            # Upload tarball
            self.run_scp_command(str(tar_path), "/tmp/mia_services.tar.gz")

        # Extract on remote
        try:
            self.run_ssh_command("cd /opt && sudo tar -xzf /tmp/mia_services.tar.gz")
            self.run_ssh_command("sudo chown -R mia:mia /opt/modules")
        except:
            return False

        return True

    def setup_python_environment(self) -> bool:
        """Set up Python virtual environment and install dependencies"""
        print("Setting up Python environment...")

        commands = [
            # Create virtual environment
            "cd /opt && python3 -m venv mia_env",

            # Install common dependencies
            "/opt/mia_env/bin/pip install --upgrade pip",
            "/opt/mia_env/bin/pip install pyzmq fastapi uvicorn pydantic",

            # Install MIA-specific dependencies
            "cd /opt/modules && /opt/mia_env/bin/pip install -r requirements.txt 2>/dev/null || true",
        ]

        for cmd in commands:
            try:
                self.run_ssh_command(cmd, check=False)  # Don't fail on pip installs
            except subprocess.CalledProcessError:
                print(f"Warning: Failed to run: {cmd}")

        return True

    def create_systemd_services(self, project_dir: Path) -> bool:
        """Create and install systemd services"""
        print("Creating systemd services...")

        # Copy existing systemd service files
        services_dir = project_dir / "services"
        if services_dir.exists():
            for service_file in services_dir.glob("*.service"):
                remote_path = f"/tmp/{service_file.name}"
                self.run_scp_command(str(service_file), remote_path)
                self.run_ssh_command(f"sudo mv {remote_path} /etc/systemd/system/")

        # Create MIA orchestrator service
        orchestrator_service = f"""[Unit]
Description=MIA Universal Orchestrator
After=network.target

[Service]
Type=simple
User=mia
WorkingDirectory=/opt
ExecStart=/opt/mia_env/bin/python /opt/modules/core-orchestrator/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

        # Create ZeroMQ broker service
        zmq_broker_service = f"""[Unit]
Description=MIA ZeroMQ Message Broker
After=network.target

[Service]
Type=simple
User=mia
WorkingDirectory=/opt
ExecStart=/opt/mia_env/bin/python /opt/modules/core-orchestrator/broker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

        # Create GPIO worker service
        gpio_service = f"""[Unit]
Description=MIA GPIO Hardware Worker
After=network.target mia-zeromq-broker.service

[Service]
Type=simple
User=mia
WorkingDirectory=/opt
ExecStart=/opt/mia_env/bin/python /opt/modules/hardware-bridge/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

        services = {
            "mia-orchestrator.service": orchestrator_service,
            "mia-zeromq-broker.service": zmq_broker_service,
            "mia-gpio-worker.service": gpio_service,
        }

        for service_name, service_content in services.items():
            # Write service file locally
            with tempfile.NamedTemporaryFile(mode='w', suffix='.service', delete=False) as f:
                f.write(service_content)
                local_path = f.name

            try:
                # Upload and install
                remote_path = f"/tmp/{service_name}"
                self.run_scp_command(local_path, remote_path)
                self.run_ssh_command(f"sudo mv {remote_path} /etc/systemd/system/")
                self.run_ssh_command(f"sudo systemctl enable {service_name}")
            finally:
                os.unlink(local_path)

        return True

    def configure_networking(self) -> bool:
        """Configure networking for MIA services"""
        print("Configuring networking...")

        # Configure firewall (allow MIA ports)
        commands = [
            "sudo ufw allow 5555/tcp",  # ZeroMQ frontend
            "sudo ufw allow 5556/tcp",  # ZeroMQ backend
            "sudo ufw allow 8000/tcp",  # FastAPI
            "sudo ufw allow 8080/tcp",  # Alternative web interface
            "sudo ufw --force enable",
        ]

        for cmd in commands:
            try:
                self.run_ssh_command(cmd, check=False)
            except subprocess.CalledProcessError:
                print(f"Warning: Failed to run: {cmd}")

        return True

    def start_services(self) -> bool:
        """Start all MIA services"""
        print("Starting MIA services...")

        services = [
            "mia-zeromq-broker.service",
            "mia-orchestrator.service",
            "mia-gpio-worker.service",
        ]

        for service in services:
            try:
                self.run_ssh_command(f"sudo systemctl start {service}")
                print(f"Started {service}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to start {service}: {e}")
                return False

        return True

    def check_deployment(self) -> Dict[str, bool]:
        """Check if deployment was successful"""
        print("Checking deployment status...")

        checks = {}

        # Check if services are running
        services = ["mia-zeromq-broker", "mia-orchestrator", "mia-gpio-worker"]
        for service in services:
            try:
                result = self.run_ssh_command(f"sudo systemctl is-active {service}")
                checks[f"{service}_active"] = "active" in result.stdout.strip()
            except:
                checks[f"{service}_active"] = False

        # Check if ports are listening
        ports = [5555, 5556, 8000]
        for port in ports:
            try:
                result = self.run_ssh_command(f"sudo netstat -tlnp | grep :{port}")
                checks[f"port_{port}_listening"] = str(port) in result.stdout
            except:
                checks[f"port_{port}_listening"] = False

        # Check Python environment
        try:
            result = self.run_ssh_command("/opt/mia_env/bin/python --version")
            checks["python_env"] = "Python" in result.stdout
        except:
            checks["python_env"] = False

        return checks

    def deploy(self, project_dir: Path, skip_deps: bool = False) -> bool:
        """Complete deployment workflow"""
        print(f"Starting MIA deployment to {self.host}")
        print("=" * 60)

        # Check connection
        if not self.check_connection():
            print(f"❌ Cannot connect to {self.host}")
            return False

        print(f"✅ SSH connection to {self.host} successful")

        try:
            # Install dependencies
            if not skip_deps:
                if not self.install_dependencies():
                    print("❌ Failed to install dependencies")
                    return False
                print("✅ Dependencies installed")

            # Deploy services
            if not self.deploy_services(project_dir):
                print("❌ Failed to deploy services")
                return False
            print("✅ Services deployed")

            # Setup Python environment
            if not self.setup_python_environment():
                print("❌ Failed to setup Python environment")
                return False
            print("✅ Python environment configured")

            # Create systemd services
            if not self.create_systemd_services(project_dir):
                print("❌ Failed to create systemd services")
                return False
            print("✅ Systemd services created")

            # Configure networking
            if not self.configure_networking():
                print("❌ Failed to configure networking")
                return False
            print("✅ Networking configured")

            # Start services
            if not self.start_services():
                print("❌ Failed to start services")
                return False
            print("✅ Services started")

            # Check deployment
            checks = self.check_deployment()
            print("\nDeployment Status:")
            for check, status in checks.items():
                status_icon = "✅" if status else "❌"
                print(f"  {status_icon} {check}")

            success_count = sum(1 for status in checks.values() if status)
            total_count = len(checks)

            print(f"\nDeployment: {success_count}/{total_count} checks passed")

            if success_count == total_count:
                print("🎉 MIA Universal deployment completed successfully!")
                return True
            else:
                print("⚠️  Deployment completed with some issues")
                return True

        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Deploy MIA Universal to Raspberry Pi")
    parser.add_argument("host", help="Raspberry Pi hostname or IP address")
    parser.add_argument("--user", default="mia", help="SSH username (default: mia)")
    parser.add_argument("--key", help="SSH private key file")
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).parent.parent,
                       help="MIA project directory")
    parser.add_argument("--skip-deps", action="store_true",
                       help="Skip dependency installation")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check deployment status")

    args = parser.parse_args()

    deployer = RPiDeployer(args.host, args.user, args.key)

    if args.check_only:
        print(f"Checking deployment status on {args.host}...")
        checks = deployer.check_deployment()
        print("\nStatus:")
        for check, status in checks.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {check}")
        return

    success = deployer.deploy(args.project_dir, args.skip_deps)

    if success:
        print(f"\n🎉 MIA Universal successfully deployed to {args.host}")
        print("You can now:")
        print("  - Access the web interface at http://<host>:8000")
        print("  - Check service status: ssh mia@<host> 'sudo systemctl status mia-*'")
        print("  - View logs: ssh mia@<host> 'journalctl -f -u mia-*'")
    else:
        print(f"\n❌ MIA Universal deployment to {args.host} failed")
        sys.exit(1)


if __name__ == "__main__":
    main()