#!/usr/bin/env python3
"""
MIA Universal: Complete Bootstrap Script
Direct download bootstrap with Cloudsmith/GitHub Packages support
"""

import os
import sys
import json
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.error
import hashlib
import tempfile
import shutil
import platform
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RepositoryConfig:
    """Repository configuration"""
    name: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    priority: int = 0

@dataclass
class PackageInfo:
    """Package information"""
    name: str
    version: str
    url: str
    sha256: Optional[str] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

class BootstrapManager:
    """Manages the complete bootstrap process"""

    def __init__(self, target_dir: str = "."):
        self.target_dir = Path(target_dir).resolve()
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()

        # Repository configurations
        self.repositories = self._load_repository_configs()

        # Package database
        self.packages = self._load_package_database()

        # Downloaded packages cache
        self.download_cache = {}

    def _load_repository_configs(self) -> Dict[str, RepositoryConfig]:
        """Load repository configurations"""
        repos = {}

        # Cloudsmith repository
        repos["cloudsmith"] = RepositoryConfig(
            name="cloudsmith",
            url="https://cloudsmith.io/~sparetools/repos/sparetools/packages/",
            username=os.environ.get("CLOUDSMITH_USERNAME"),
            password=os.environ.get("CLOUDSMITH_API_KEY"),
            priority=1
        )

        # GitHub Packages fallback
        repos["github"] = RepositoryConfig(
            name="github",
            url="https://maven.pkg.github.com/sparetools",
            username=os.environ.get("GITHUB_USERNAME"),
            password=os.environ.get("GITHUB_TOKEN"),
            priority=0
        )

        return repos

    def _load_package_database(self) -> Dict[str, PackageInfo]:
        """Load package database"""
        # This would normally be loaded from a remote database
        # For now, we'll define key packages inline
        packages = {}

        # Conan package
        conan_version = "2.0.0"
        packages["conan"] = PackageInfo(
            name="conan",
            version=conan_version,
            url=self._get_conan_download_url(conan_version),
            dependencies=[]
        )

        # Python dependencies
        packages["websockets"] = PackageInfo(
            name="websockets",
            version="11.0.3",
            url="https://pypi.org/simple/websockets/",
            dependencies=[]
        )

        packages["aiohttp"] = PackageInfo(
            name="aiohttp",
            version="3.9.1",
            url="https://pypi.org/simple/aiohttp/",
            dependencies=["multidict", "yarl", "aiosignal"]
        )

        return packages

    def _get_conan_download_url(self, version: str) -> str:
        """Get Conan download URL for current platform"""
        base_url = "https://github.com/conan-io/conan/releases/download"

        if self.system == "linux":
            if "x86_64" in self.machine:
                return f"{base_url}/{version}/conan-{version}-x86_64-linux-gnu.tar.gz"
            elif "aarch64" in self.machine:
                return f"{base_url}/{version}/conan-{version}-armv8-linux-gnu.tar.gz"
        elif self.system == "darwin":  # macOS
            if "arm64" in self.machine:
                return f"{base_url}/{version}/conan-{version}-armv8-macos.tar.gz"
            else:
                return f"{base_url}/{version}/conan-{version}-x86_64-macos.tar.gz"
        elif self.system == "windows":
            return f"{base_url}/{version}/conan-{version}-x86_64-windows-msvc.zip"

        raise RuntimeError(f"Unsupported platform: {self.system}/{self.machine}")

    def download_file(self, url: str, destination: Path, sha256: Optional[str] = None) -> bool:
        """Download file with integrity verification"""
        try:
            logger.info(f"Downloading {url} to {destination}")

            # Create destination directory
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Download file
            with urllib.request.urlopen(url) as response:
                with open(destination, 'wb') as f:
                    shutil.copyfileobj(response, f)

            # Verify SHA256 if provided
            if sha256:
                calculated_sha256 = self._calculate_sha256(destination)
                if calculated_sha256 != sha256:
                    logger.error(f"SHA256 verification failed for {destination}")
                    logger.error(f"Expected: {sha256}")
                    logger.error(f"Calculated: {calculated_sha256}")
                    return False

            logger.info(f"Successfully downloaded {destination}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def extract_archive(self, archive_path: Path, extract_to: Path) -> bool:
        """Extract archive based on file extension"""
        try:
            if archive_path.suffix == '.tar':
                import tarfile
                with tarfile.open(archive_path) as tar:
                    tar.extractall(extract_to)
            elif archive_path.suffix == '.gz' and archive_path.suffixes[-2] == '.tar':
                import tarfile
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(extract_to)
            elif archive_path.suffix == '.zip':
                import zipfile
                with zipfile.ZipFile(archive_path) as zf:
                    zf.extractall(extract_to)
            else:
                logger.error(f"Unsupported archive format: {archive_path.suffix}")
                return False

            logger.info(f"Successfully extracted {archive_path} to {extract_to}")
            return True

        except Exception as e:
            logger.error(f"Failed to extract {archive_path}: {e}")
            return False

    def install_conan(self) -> bool:
        """Install Conan package manager"""
        try:
            package = self.packages["conan"]
            download_dir = Path(tempfile.gettempdir()) / "mia_bootstrap"
            download_dir.mkdir(exist_ok=True)

            archive_path = download_dir / f"conan-{package.version}.tar.gz"

            # Download Conan
            if not self.download_file(package.url, archive_path):
                return False

            # Extract to temporary location
            extract_dir = download_dir / "conan_extract"
            if not self.extract_archive(archive_path, extract_dir):
                return False

            # Find Conan binary
            conan_bin = None
            for root, dirs, files in os.walk(extract_dir):
                if 'conan' in files:
                    conan_bin = Path(root) / 'conan'
                    break

            if not conan_bin:
                logger.error("Could not find Conan binary in extracted archive")
                return False

            # Install to system or user directory
            install_dir = self.target_dir / "tools" / "conan"
            install_dir.mkdir(parents=True, exist_ok=True)

            # Copy Conan installation
            conan_dir = conan_bin.parent
            for item in conan_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, install_dir / item.name)
                else:
                    shutil.copytree(item, install_dir / item.name, dirs_exist_ok=True)

            # Add to PATH
            bin_dir = install_dir
            self._add_to_path(str(bin_dir))

            logger.info(f"Conan installed to {install_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to install Conan: {e}")
            return False

    def _add_to_path(self, path: str):
        """Add directory to system PATH"""
        current_path = os.environ.get('PATH', '')
        if path not in current_path:
            os.environ['PATH'] = f"{path}:{current_path}"
            logger.info(f"Added {path} to PATH")

    def install_python_packages(self) -> bool:
        """Install Python packages"""
        try:
            # Use pip to install packages
            packages_to_install = [
                "websockets>=11.0.0",
                "aiohttp>=3.9.0",
                "pydantic>=2.0.0",
                "fastapi>=0.104.0",
                "uvicorn>=0.24.0"
            ]

            for package in packages_to_install:
                logger.info(f"Installing Python package: {package}")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", package
                ], capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f"Failed to install {package}: {result.stderr}")
                    return False

            logger.info("Python packages installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install Python packages: {e}")
            return False

    def configure_repositories(self) -> bool:
        """Configure package repositories"""
        try:
            # Configure Cloudsmith repository
            cloudsmith = self.repositories["cloudsmith"]
            if cloudsmith.username and cloudsmith.password:
                logger.info("Configuring Cloudsmith repository")

                # Add Cloudsmith remote
                result = subprocess.run([
                    "conan", "remote", "add", "sparetools",
                    cloudsmith.url, "--force"
                ], capture_output=True, text=True)

                if result.returncode != 0:
                    logger.warning(f"Failed to add Cloudsmith remote: {result.stderr}")

                # Login to Cloudsmith
                result = subprocess.run([
                    "conan", "remote", "login", "sparetools",
                    cloudsmith.username
                ], input=cloudsmith.password, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.warning(f"Failed to login to Cloudsmith: {result.stderr}")
                else:
                    logger.info("Successfully configured Cloudsmith repository")

            # Configure GitHub Packages as fallback
            github = self.repositories["github"]
            if github.username and github.password:
                logger.info("Configuring GitHub Packages repository")

                result = subprocess.run([
                    "conan", "remote", "add", "github-sparetools",
                    github.url, "--force"
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info("Successfully configured GitHub Packages repository")

            return True

        except Exception as e:
            logger.error(f"Failed to configure repositories: {e}")
            return False

    def bootstrap_project(self) -> bool:
        """Run the complete bootstrap process"""
        logger.info("Starting MIA Universal bootstrap process")

        success = True

        # Step 1: Install Conan
        if not self.install_conan():
            logger.error("Failed to install Conan")
            success = False

        # Step 2: Install Python packages
        if not self.install_python_packages():
            logger.error("Failed to install Python packages")
            success = False

        # Step 3: Configure repositories
        if not self.configure_repositories():
            logger.warning("Failed to configure some repositories, continuing...")

        # Step 4: Verify installation
        if success:
            logger.info("Bootstrap completed successfully!")
            logger.info("You can now run:")
            logger.info("  conan install . --build=missing -r sparetools")
            logger.info("  python modules/core-orchestrator/main.py")

        return success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="MIA Universal Bootstrap Script")
    parser.add_argument("--target-dir", default=".",
                       help="Target directory for installation")
    parser.add_argument("--verify-only", action="store_true",
                       help="Only verify current installation")
    parser.add_argument("--force", action="store_true",
                       help="Force reinstallation of all components")

    args = parser.parse_args()

    # Initialize bootstrap manager
    bootstrap = BootstrapManager(args.target_dir)

    if args.verify_only:
        # TODO: Implement verification logic
        logger.info("Verification not yet implemented")
        return 0

    # Run bootstrap
    if bootstrap.bootstrap_project():
        logger.info("Bootstrap completed successfully!")
        return 0
    else:
        logger.error("Bootstrap failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())