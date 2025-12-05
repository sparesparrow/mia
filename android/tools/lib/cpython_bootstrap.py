#!/usr/bin/env python3
"""
CPython Bootstrap Module

Provides bundled CPython setup for Android tools.
Downloads and configures standalone CPython builds from Cloudsmith.

Supported platforms:
- Linux (x86_64, aarch64)
- macOS (x86_64, arm64)
- Windows (x86_64)

Usage:
    from lib.cpython_bootstrap import CPythonBootstrap
    
    bootstrap = CPythonBootstrap()
    python_path = bootstrap.ensure_python()
    
    # Or use as context manager
    with CPythonBootstrap() as python_path:
        subprocess.run([python_path, "script.py"])
"""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.request import urlretrieve
from urllib.error import URLError


# CPython version configuration
CPYTHON_VERSION = "3.12.7"

# Cloudsmith distribution URLs
# Format: https://github.com/indygreg/python-build-standalone/releases
CPYTHON_BUILDS = {
    # Linux builds
    ("Linux", "x86_64"): {
        "url": f"https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-{CPYTHON_VERSION}+20241016-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz",
        "sha256": None,  # Will be verified during download if available
        "archive_type": "tar.gz",
    },
    ("Linux", "aarch64"): {
        "url": f"https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-{CPYTHON_VERSION}+20241016-aarch64-unknown-linux-gnu-install_only_stripped.tar.gz",
        "sha256": None,
        "archive_type": "tar.gz",
    },
    # macOS builds
    ("Darwin", "x86_64"): {
        "url": f"https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-{CPYTHON_VERSION}+20241016-x86_64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": None,
        "archive_type": "tar.gz",
    },
    ("Darwin", "arm64"): {
        "url": f"https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-{CPYTHON_VERSION}+20241016-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": None,
        "archive_type": "tar.gz",
    },
    # Windows builds
    ("Windows", "AMD64"): {
        "url": f"https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-{CPYTHON_VERSION}+20241016-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "sha256": None,
        "archive_type": "tar.gz",
    },
}

# Alternative machine name mappings
MACHINE_ALIASES = {
    "x86_64": "x86_64",
    "AMD64": "AMD64",
    "amd64": "AMD64",
    "aarch64": "aarch64",
    "arm64": "arm64",
}


class CPythonBootstrapError(Exception):
    """Exception raised for CPython bootstrap errors."""
    pass


class CPythonBootstrap:
    """
    CPython Bootstrap Manager.
    
    Downloads and manages standalone CPython builds for cross-platform use.
    
    Attributes:
        version: CPython version to use
        install_dir: Directory where CPython is installed
        python_path: Path to the Python executable
    """
    
    def __init__(
        self,
        version: str = CPYTHON_VERSION,
        install_dir: Optional[Path] = None,
        force_download: bool = False
    ):
        """
        Initialize CPython bootstrap.
        
        Args:
            version: CPython version to use
            install_dir: Custom installation directory (default: ~/.ai-servis/cpython)
            force_download: Force re-download even if already installed
        """
        self.version = version
        self.force_download = force_download
        
        # Determine installation directory
        if install_dir:
            self.install_dir = Path(install_dir)
        else:
            # Default to user-specific directory
            home = Path.home()
            self.install_dir = home / ".ai-servis" / "cpython" / version
        
        # Detect platform
        self.system = platform.system()
        self.machine = MACHINE_ALIASES.get(platform.machine(), platform.machine())
        
        # Get build configuration
        self.build_config = self._get_build_config()
        
        # Python executable path
        if self.system == "Windows":
            self.python_path = self.install_dir / "python" / "python.exe"
        else:
            self.python_path = self.install_dir / "python" / "bin" / "python3"
    
    def _get_build_config(self) -> Dict:
        """Get build configuration for current platform."""
        key = (self.system, self.machine)
        
        if key not in CPYTHON_BUILDS:
            # Try with alternative machine names
            if self.system == "Darwin" and self.machine == "arm64":
                key = ("Darwin", "arm64")
            elif self.system == "Linux" and self.machine in ("arm64", "aarch64"):
                key = ("Linux", "aarch64")
            
        if key not in CPYTHON_BUILDS:
            raise CPythonBootstrapError(
                f"Unsupported platform: {self.system} {self.machine}. "
                f"Supported platforms: {list(CPYTHON_BUILDS.keys())}"
            )
        
        return CPYTHON_BUILDS[key]
    
    def is_installed(self) -> bool:
        """Check if CPython is already installed."""
        if not self.python_path.exists():
            return False
        
        # Verify it's executable
        try:
            result = subprocess.run(
                [str(self.python_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and self.version in result.stdout
        except (subprocess.TimeoutExpired, OSError):
            return False
    
    def download(self, progress_callback=None) -> Path:
        """
        Download CPython build.
        
        Args:
            progress_callback: Optional callback(downloaded, total) for progress
            
        Returns:
            Path to downloaded archive
        """
        url = self.build_config["url"]
        archive_type = self.build_config["archive_type"]
        
        # Create temp file for download
        suffix = f".{archive_type}"
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        temp_path = Path(temp_path)
        
        print(f"Downloading CPython {self.version} from {url}...")
        
        try:
            if progress_callback:
                def reporthook(count, block_size, total_size):
                    progress_callback(count * block_size, total_size)
                urlretrieve(url, temp_path, reporthook=reporthook)
            else:
                urlretrieve(url, temp_path)
        except URLError as e:
            temp_path.unlink(missing_ok=True)
            raise CPythonBootstrapError(f"Failed to download CPython: {e}")
        
        # Verify SHA256 if provided
        expected_sha256 = self.build_config.get("sha256")
        if expected_sha256:
            actual_sha256 = self._calculate_sha256(temp_path)
            if actual_sha256 != expected_sha256:
                temp_path.unlink(missing_ok=True)
                raise CPythonBootstrapError(
                    f"SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}"
                )
        
        print(f"Downloaded to {temp_path}")
        return temp_path
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def extract(self, archive_path: Path) -> None:
        """
        Extract CPython archive to installation directory.
        
        Args:
            archive_path: Path to downloaded archive
        """
        print(f"Extracting to {self.install_dir}...")
        
        # Create installation directory
        self.install_dir.mkdir(parents=True, exist_ok=True)
        
        archive_type = self.build_config["archive_type"]
        
        if archive_type == "tar.gz":
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(self.install_dir)
        elif archive_type == "zip":
            with zipfile.ZipFile(archive_path, "r") as zip_file:
                zip_file.extractall(self.install_dir)
        else:
            raise CPythonBootstrapError(f"Unsupported archive type: {archive_type}")
        
        # Make Python executable
        if self.system != "Windows":
            self.python_path.chmod(0o755)
            # Also make pip executable
            pip_path = self.python_path.parent / "pip3"
            if pip_path.exists():
                pip_path.chmod(0o755)
        
        print(f"Extracted successfully to {self.install_dir}")
    
    def ensure_python(self) -> Path:
        """
        Ensure CPython is installed and return path to executable.
        
        Returns:
            Path to Python executable
        """
        if self.is_installed() and not self.force_download:
            print(f"Using existing CPython at {self.python_path}")
            return self.python_path
        
        # Clean existing installation if force download
        if self.force_download and self.install_dir.exists():
            print(f"Removing existing installation at {self.install_dir}")
            shutil.rmtree(self.install_dir)
        
        # Download and extract
        archive_path = self.download()
        try:
            self.extract(archive_path)
        finally:
            # Clean up download
            archive_path.unlink(missing_ok=True)
        
        # Verify installation
        if not self.is_installed():
            raise CPythonBootstrapError(
                f"Installation verification failed. Python not found at {self.python_path}"
            )
        
        print(f"CPython {self.version} installed at {self.python_path}")
        return self.python_path
    
    def run_python(self, *args, **kwargs) -> subprocess.CompletedProcess:
        """
        Run Python with the given arguments.
        
        Args:
            *args: Arguments to pass to Python
            **kwargs: Additional kwargs for subprocess.run
            
        Returns:
            CompletedProcess instance
        """
        python_path = self.ensure_python()
        cmd = [str(python_path)] + list(args)
        
        return subprocess.run(cmd, **kwargs)
    
    def run_module(self, module: str, *args, **kwargs) -> subprocess.CompletedProcess:
        """
        Run a Python module with the given arguments.
        
        Args:
            module: Module name to run
            *args: Arguments to pass to the module
            **kwargs: Additional kwargs for subprocess.run
            
        Returns:
            CompletedProcess instance
        """
        return self.run_python("-m", module, *args, **kwargs)
    
    def pip_install(self, *packages, **kwargs) -> subprocess.CompletedProcess:
        """
        Install packages using pip.
        
        Args:
            *packages: Packages to install
            **kwargs: Additional kwargs for subprocess.run
            
        Returns:
            CompletedProcess instance
        """
        return self.run_module("pip", "install", *packages, **kwargs)
    
    def get_site_packages(self) -> Path:
        """
        Get the site-packages directory.
        
        Returns:
            Path to site-packages
        """
        result = self.run_python(
            "-c",
            "import site; print(site.getsitepackages()[0])",
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise CPythonBootstrapError(
                f"Failed to get site-packages: {result.stderr}"
            )
        
        return Path(result.stdout.strip())
    
    def cleanup(self) -> None:
        """Remove the CPython installation."""
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir)
            print(f"Removed CPython installation at {self.install_dir}")
    
    def __enter__(self) -> Path:
        """Context manager entry - ensure Python is installed."""
        return self.ensure_python()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - nothing to cleanup normally."""
        pass


def get_bundled_python() -> Path:
    """
    Get path to bundled Python, downloading if necessary.
    
    Returns:
        Path to Python executable
    """
    bootstrap = CPythonBootstrap()
    return bootstrap.ensure_python()


def run_with_bundled_python(script_path: str, *args) -> int:
    """
    Run a Python script with bundled Python.
    
    Args:
        script_path: Path to the script to run
        *args: Arguments to pass to the script
        
    Returns:
        Exit code
    """
    bootstrap = CPythonBootstrap()
    result = bootstrap.run_python(script_path, *args)
    return result.returncode


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="CPython Bootstrap for MIA Android Tools"
    )
    parser.add_argument(
        "--version",
        default=CPYTHON_VERSION,
        help=f"CPython version (default: {CPYTHON_VERSION})"
    )
    parser.add_argument(
        "--install-dir",
        type=Path,
        help="Custom installation directory"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove existing installation"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show installation info"
    )
    parser.add_argument(
        "script",
        nargs="?",
        help="Python script to run"
    )
    parser.add_argument(
        "script_args",
        nargs="*",
        help="Arguments for the script"
    )
    
    args = parser.parse_args()
    
    try:
        bootstrap = CPythonBootstrap(
            version=args.version,
            install_dir=args.install_dir,
            force_download=args.force
        )
        
        if args.cleanup:
            bootstrap.cleanup()
            print("Cleanup complete")
            sys.exit(0)
        
        if args.info:
            print(f"CPython Version: {bootstrap.version}")
            print(f"System: {bootstrap.system}")
            print(f"Machine: {bootstrap.machine}")
            print(f"Install Directory: {bootstrap.install_dir}")
            print(f"Python Path: {bootstrap.python_path}")
            print(f"Installed: {bootstrap.is_installed()}")
            sys.exit(0)
        
        # Ensure Python is installed
        python_path = bootstrap.ensure_python()
        
        if args.script:
            # Run the provided script
            result = bootstrap.run_python(args.script, *args.script_args)
            sys.exit(result.returncode)
        else:
            # Just print the path
            print(f"Python available at: {python_path}")
            
    except CPythonBootstrapError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
