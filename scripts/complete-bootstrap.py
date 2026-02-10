#!/usr/bin/env python3
"""
complete-bootstrap.py - Zero-dependency bootstrap for MIA v2.0.0

This script establishes a reproducible environment using only stdlib.
It downloads and configures bundled CPython, Conan, and all dependencies
without requiring system Python packages.

Usage:
    python3 scripts/complete-bootstrap.py \\
        --platform linux-aarch64 \\
        --python-version 3.12.7 \\
        --conan-version 2.21.0 \\
        --cloudsmith-repo sparesparrow/cpy \\
        --output-dir ~/.ai-servis

Success markers:
- ~/.ai-servis/cpython/bin/python3 (executable)
- ~/.ai-servis/conan/bin/conan (executable)
- ~/.ai-servis/summary.json (metadata)
- ~/.ai-servis/validation-report.json (tests)
- ~/.ai-servis/success.marker (completion flag)
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class BootstrapError(Exception):
    """Bootstrap-specific error"""
    pass


class MIABootstrap:
    """Zero-dependency bootstrap for MIA"""

    def __init__(self, args):
        self.args = args
        self.output_dir = Path(args.output_dir).expanduser().resolve()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mia-bootstrap-"))
        self.summary = {
            "platform": args.platform,
            "python_version": args.python_version,
            "conan_version": args.conan_version,
            "timestamp": time.time(),
            "components": {}
        }

    def run(self) -> bool:
        """Run complete bootstrap process"""
        try:
            print("🚀 Starting MIA v2.0.0 Bootstrap")
            print("=" * 50)

            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Output directory: {self.output_dir}")

            # Bootstrap CPython
            if not self._bootstrap_cpython():
                return False

            # Bootstrap Conan
            if not self._bootstrap_conan():
                return False

            # Validate installation
            if not self._validate_installation():
                return False

            # Create success marker
            self._create_success_marker()

            print("\n🎉 Bootstrap completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Bootstrap failed: {e}")
            return False
        finally:
            # Cleanup
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")

    def _bootstrap_cpython(self) -> bool:
        """Download and setup bundled CPython"""
        print("\n🐍 Bootstrapping CPython...")

        # Download CPython bundle
        bundle_url = f"https://dl.cloudsmith.io/public/{self.args.cloudsmith_repo}/raw/versions/{self.args.python_version}/python-{self.args.python_version}-{self.args.platform}.tar.gz"
        bundle_path = self.temp_dir / f"python-{self.args.python_version}.tar.gz"

        print(f"📦 Downloading CPython from: {bundle_url}")
        if not self._download_file(bundle_url, bundle_path):
            return False

        # Extract bundle
        cpython_dir = self.output_dir / "cpython"
        print(f"📦 Extracting to: {cpython_dir}")
        if not self._extract_tar(bundle_path, cpython_dir):
            return False

        # Verify Python executable
        python_bin = cpython_dir / "bin" / "python3"
        if not python_bin.exists():
            print(f"❌ Python executable not found at: {python_bin}")
            return False

        # Test Python functionality
        if not self._test_python(python_bin):
            return False

        self.summary["components"]["cpython"] = {
            "version": self.args.python_version,
            "path": str(cpython_dir),
            "executable": str(python_bin)
        }

        print("✅ CPython bootstrap complete")
        return True

    def _bootstrap_conan(self) -> bool:
        """Download and setup Conan"""
        print("\n📦 Bootstrapping Conan...")

        # Download Conan
        conan_url = f"https://github.com/conan-io/conan/releases/download/{self.args.conan_version}/conan-{self.args.conan_version}-{self.args.platform}.tar.gz"
        conan_path = self.temp_dir / f"conan-{self.args.conan_version}.tar.gz"

        print(f"📦 Downloading Conan from: {conan_url}")
        if not self._download_file(conan_url, conan_path):
            return False

        # Extract Conan
        conan_dir = self.output_dir / "conan"
        print(f"📦 Extracting to: {conan_dir}")
        if not self._extract_tar(conan_path, conan_dir):
            return False

        # Create wrapper script
        conan_bin = conan_dir / "bin" / "conan"
        if not conan_bin.exists():
            print(f"❌ Conan executable not found at: {conan_bin}")
            return False

        # Test Conan
        if not self._test_conan(conan_bin):
            return False

        self.summary["components"]["conan"] = {
            "version": self.args.conan_version,
            "path": str(conan_dir),
            "executable": str(conan_bin)
        }

        print("✅ Conan bootstrap complete")
        return True

    def _validate_installation(self) -> bool:
        """Validate complete installation"""
        print("\n🔍 Validating installation...")

        python_bin = Path(self.summary["components"]["cpython"]["executable"])
        conan_bin = Path(self.summary["components"]["conan"]["executable"])

        validation_results = {
            "python_executable": python_bin.exists(),
            "conan_executable": conan_bin.exists(),
            "python_ssl": False,
            "python_sqlite": False,
            "python_zlib": False,
            "conan_version": False
        }

        # Test Python stdlib modules
        try:
            result = subprocess.run([str(python_bin), "-c", "import ssl, sqlite3, zlib; print('OK')"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                validation_results["python_ssl"] = True
                validation_results["python_sqlite"] = True
                validation_results["python_zlib"] = True
        except subprocess.TimeoutExpired:
            pass

        # Test Conan version
        try:
            result = subprocess.run([str(conan_bin), "--version"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and self.args.conan_version in result.stdout:
                validation_results["conan_version"] = True
        except subprocess.TimeoutExpired:
            pass

        # Save validation results
        validation_file = self.output_dir / "validation-report.json"
        with open(validation_file, 'w') as f:
            json.dump(validation_results, f, indent=2)

        # Check all validations passed
        all_passed = all(validation_results.values())

        if all_passed:
            print("✅ All validations passed")
        else:
            print("❌ Some validations failed:")
            for test, passed in validation_results.items():
                if not passed:
                    print(f"   - {test}: FAILED")

        return all_passed

    def _create_success_marker(self):
        """Create success marker file"""
        marker_file = self.output_dir / "success.marker"
        with open(marker_file, 'w') as f:
            f.write(f"MIA Bootstrap Success\nTimestamp: {time.time()}\n")

        # Save summary
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(self.summary, f, indent=2)

        print(f"📋 Summary saved to: {summary_file}")

    def _download_file(self, url: str, dest: Path, retries: int = 3) -> bool:
        """Download file with retries"""
        for attempt in range(retries):
            try:
                print(f"📥 Download attempt {attempt + 1}/{retries}")
                with urllib.request.urlopen(url, timeout=30) as response:
                    with open(dest, 'wb') as f:
                        shutil.copyfileobj(response, f)
                print(f"✅ Downloaded: {dest.name}")
                return True
            except (urllib.error.URLError, ssl.SSLError) as e:
                print(f"❌ Download failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
        return False

    def _extract_tar(self, tar_path: Path, dest: Path) -> bool:
        """Extract tar.gz file"""
        try:
            with tarfile.open(tar_path, 'r:gz') as tar:
                tar.extractall(dest)
            print(f"✅ Extracted: {tar_path.name}")
            return True
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return False

    def _test_python(self, python_bin: Path) -> bool:
        """Test Python functionality"""
        try:
            result = subprocess.run([str(python_bin), "--version"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("❌ Python version check failed")
                return False

            print(f"✅ Python: {result.stdout.strip()}")

            # Test basic import
            result = subprocess.run([str(python_bin), "-c", "import sys; print('OK')"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("❌ Python basic import failed")
                return False

            return True
        except subprocess.TimeoutExpired:
            print("❌ Python test timed out")
            return False

    def _test_conan(self, conan_bin: Path) -> bool:
        """Test Conan functionality"""
        try:
            result = subprocess.run([str(conan_bin), "--version"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("❌ Conan version check failed")
                return False

            print(f"✅ Conan: {result.stdout.strip()}")
            return True
        except subprocess.TimeoutExpired:
            print("❌ Conan test timed out")
            return False


def main():
    parser = argparse.ArgumentParser(description="MIA v2.0.0 Bootstrap")
    parser.add_argument("--platform", required=True,
                       help="Target platform (e.g., linux-aarch64)")
    parser.add_argument("--python-version", required=True,
                       help="Python version to bootstrap (e.g., 3.12.7)")
    parser.add_argument("--conan-version", required=True,
                       help="Conan version to bootstrap (e.g., 2.21.0)")
    parser.add_argument("--cloudsmith-repo", required=True,
                       help="Cloudsmith repository for CPython (e.g., sparesparrow/cpy)")
    parser.add_argument("--output-dir", required=True,
                       help="Output directory for bootstrap (e.g., ~/.ai-servis)")
    parser.add_argument("--retry-after", type=int, default=60,
                       help="Retry delay for rate limited requests")

    args = parser.parse_args()

    # Validate platform
    if platform.system().lower() == "linux":
        if platform.machine() in ["aarch64", "arm64"]:
            expected_platform = "linux-aarch64"
        elif platform.machine() in ["x86_64", "amd64"]:
            expected_platform = "linux-x86_64"
        else:
            expected_platform = f"linux-{platform.machine()}"

        if args.platform != expected_platform:
            print(f"⚠️  Platform mismatch: specified {args.platform}, detected {expected_platform}")

    bootstrap = MIABootstrap(args)
    success = bootstrap.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()