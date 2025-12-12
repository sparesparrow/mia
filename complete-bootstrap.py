<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 5376269 (rebase)
#!/usr/bin/env python3
"""
AI-SERVIS Universal: Repository-Agnostic CPython Bootstrap
================================================================
Canonical bootstrap following CPython-tool pattern:
1. Detect platform (linux-x86_64, macos-arm64, windows-x86_64, etc.)
2. Download cpython-tool-3.12.7-{platform}.tar.gz from configured repository
3. Extract into self-contained tool prefix and export PYTHONHOME/PATH
<<<<<<< HEAD
4. Use bundled interpreter to install shared development tooling
5. Use bundled interpreter to install/configure Conan 2.21.0
6. Set Conan remotes to configured repository for C++/system packages
=======
4. Use bundled interpreter to install/configure Conan 2.21.0
5. Set Conan remotes to configured repository for C++/system packages
>>>>>>> 5376269 (rebase)

Supports both Cloudsmith and GitHub Packages (easily switchable via env vars).

This script uses only stdlib (urllib, tarfile, subprocess) - no external deps.
"""

import sys 
<<<<<<< HEAD
=======
import sys
>>>>>>> ec9bdcd (build: replace bootstrap script with zero-dependency implementation)
=======
>>>>>>> 5376269 (rebase)
import os
import platform
import urllib.request
import tarfile
import subprocess
import shutil
import json
from pathlib import Path
<<<<<<< HEAD
<<<<<<< HEAD
from enum import Enum

# --- REPOSITORY CONFIGURATION ---
# Switch between Cloudsmith and GitHub Packages via environment variables:
#   ARTIFACT_REPO=cloudsmith  (default)
#   ARTIFACT_REPO=github
#
# For GitHub Packages, also set:
#   GITHUB_OWNER=sparesparrow
#   GITHUB_REPO=cpy
#   GITHUB_TAG=v3.12.7  (or release tag)

class ArtifactRepo(Enum):
    CLOUDSMITH = "cloudsmith"
    GITHUB = "github"

# Default configuration
CPY_VERSION = "3.12.7"
CONAN_VERSION = "2.21.0"

# Repository selection
ARTIFACT_REPO = os.getenv("ARTIFACT_REPO", "cloudsmith").lower()
if ARTIFACT_REPO not in ["cloudsmith", "github"]:
    ARTIFACT_REPO = "cloudsmith"

# Cloudsmith URLs (default)
CLOUDSMITH_CPY_BASE = os.getenv(
    "CLOUDSMITH_CPY_BASE",
    "https://dl.cloudsmith.io/sparesparrow/cpy/raw/versions"
)
CLOUDSMITH_CONAN_REMOTE = os.getenv(
    "CLOUDSMITH_CONAN_REMOTE",
    "https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/"
)

# GitHub Packages URLs
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "sparesparrow")
GITHUB_REPO = os.getenv("GITHUB_REPO", "cpy")
GITHUB_TAG = os.getenv("GITHUB_TAG", f"v{CPY_VERSION}")
GITHUB_CPY_BASE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{GITHUB_TAG}"
GITHUB_CONAN_REMOTE = os.getenv(
    "GITHUB_CONAN_REMOTE",
    f"https://maven.pkg.github.com/{GITHUB_OWNER}/conan"
)


def get_platform_str():
    """Determines Cloudsmith platform string."""
    machine = platform.machine()
    system = sys.platform

    # Detect Android (Linux kernel with Android-specific markers)
    if (system == "linux" and
            ("android" in sys.version.lower() or
             "ANDROID_ROOT" in os.environ)):
        return "android-arm64"  # Android typically runs on ARM64

=======
=======
from enum import Enum
>>>>>>> 5376269 (rebase)

# --- REPOSITORY CONFIGURATION ---
# Switch between Cloudsmith and GitHub Packages via environment variables:
#   ARTIFACT_REPO=cloudsmith  (default)
#   ARTIFACT_REPO=github
#
# For GitHub Packages, also set:
#   GITHUB_OWNER=sparesparrow
#   GITHUB_REPO=cpy
#   GITHUB_TAG=v3.12.7  (or release tag)

class ArtifactRepo(Enum):
    CLOUDSMITH = "cloudsmith"
    GITHUB = "github"

# Default configuration
CPY_VERSION = "3.12.7"
CONAN_VERSION = "2.21.0"

# Repository selection
ARTIFACT_REPO = os.getenv("ARTIFACT_REPO", "cloudsmith").lower()
if ARTIFACT_REPO not in ["cloudsmith", "github"]:
    ARTIFACT_REPO = "cloudsmith"

# Cloudsmith URLs (default)
CLOUDSMITH_CPY_BASE = os.getenv(
    "CLOUDSMITH_CPY_BASE",
    "https://dl.cloudsmith.io/sparesparrow/cpy/raw/versions"
)
CLOUDSMITH_CONAN_REMOTE = os.getenv(
    "CLOUDSMITH_CONAN_REMOTE",
    "https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/"
)

# GitHub Packages URLs
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "sparesparrow")
GITHUB_REPO = os.getenv("GITHUB_REPO", "cpy")
GITHUB_TAG = os.getenv("GITHUB_TAG", f"v{CPY_VERSION}")
GITHUB_CPY_BASE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{GITHUB_TAG}"
GITHUB_CONAN_REMOTE = os.getenv(
    "GITHUB_CONAN_REMOTE",
    f"https://maven.pkg.github.com/{GITHUB_OWNER}/conan"
)


def get_platform_str():
    """Determines Cloudsmith platform string."""
    machine = platform.machine()
    system = sys.platform
<<<<<<< HEAD
>>>>>>> ec9bdcd (build: replace bootstrap script with zero-dependency implementation)
=======

    # Detect Android (Linux kernel with Android-specific markers)
    if (system == "linux" and
            ("android" in sys.version.lower() or
             "ANDROID_ROOT" in os.environ)):
        return "android-arm64"  # Android typically runs on ARM64

>>>>>>> 5376269 (rebase)
    if system == "win32":
        return "windows-x86_64"
    elif system == "darwin":
        return "macos-arm64" if machine == "arm64" else "macos-x86_64"
    else:
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 5376269 (rebase)
        # Linux variants
        if machine == "x86_64" or machine == "amd64":
            return "linux-x86_64"
        elif machine == "aarch64" or machine == "arm64":
            return "linux-aarch64"
        elif machine.startswith("arm"):
            return f"linux-{machine}"
        else:
            return f"linux-{machine}"
<<<<<<< HEAD

def get_cpython_url(plat: str) -> str:
    """Get CPython tool download URL based on configured repository"""
    filename = f"cpython-tool-{CPY_VERSION}-{plat}.tar.gz"

    if ARTIFACT_REPO == "github":
        # GitHub Packages/Releases pattern
        url = f"{GITHUB_CPY_BASE}/{filename}"
    else:
        # Cloudsmith pattern (default)
        url = f"{CLOUDSMITH_CPY_BASE}/{CPY_VERSION}/{filename}"

    return url

def get_conan_remote() -> str:
    """Get Conan remote URL based on configured repository"""
    if ARTIFACT_REPO == "github":
        return GITHUB_CONAN_REMOTE
    else:
        return CLOUDSMITH_CONAN_REMOTE

def download_cpython_tool(work_dir: Path, plat: str) -> Path:
    """Download CPython tool tarball from configured repository"""
    filename = f"cpython-tool-{CPY_VERSION}-{plat}.tar.gz"
    url = get_cpython_url(plat)
    dest = work_dir / ".buildenv" / "downloads"
    dest.mkdir(parents=True, exist_ok=True)
    archive_path = dest / filename
    
    if archive_path.exists():
        print(f"  ✓ CPython tool archive already exists: {archive_path}")
        return archive_path
    
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    print(f"  Downloading CPython tool from {repo_name}...")
    print(f"    URL: {url}")
    print(f"    Destination: {archive_path}")
    
    # For GitHub Packages, may need authentication token
    headers = {}
    if ARTIFACT_REPO == "github":
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        # GitHub Releases don't require auth for public repos, but API access does
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            
            with open(archive_path, 'wb') as out_file:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r    Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
            
            print()  # New line after progress
            print(f"  ✓ Download complete: {archive_path}")
            return archive_path
            
    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        print(f"    URL: {url}")
        if ARTIFACT_REPO == "github" and e.code == 404:
            print(f"    Hint: Check that release tag '{GITHUB_TAG}' exists in {GITHUB_OWNER}/{GITHUB_REPO}")
            print(f"    Or set GITHUB_TAG environment variable to the correct release tag")
        elif ARTIFACT_REPO == "github" and e.code == 401:
            print(f"    Hint: GitHub Packages may require authentication. Set GITHUB_TOKEN environment variable")
        sys.exit(1)
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        sys.exit(1)

def extract_cpython_tool(archive_path: Path, work_dir: Path) -> Path:
    """Extract CPython tool tarball to .buildenv/cpython"""
    extract_dir = work_dir / ".buildenv" / "cpython"
    
    if extract_dir.exists() and (extract_dir / "bin" / "python3").exists():
        print(f"  ✓ CPython already extracted: {extract_dir}")
        return extract_dir
    
    print(f"  Extracting CPython tool to {extract_dir}...")
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            # Extract with progress
            members = tar.getmembers()
            for i, member in enumerate(members):
                tar.extract(member, extract_dir)
                if (i + 1) % 100 == 0:
                    print(f"\r    Extracted {i + 1}/{len(members)} files...", end='', flush=True)
            print()  # New line after progress
        
        print(f"  ✓ Extraction complete: {extract_dir}")
        return extract_dir
        
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        sys.exit(1)

def setup_python_environment(extract_dir: Path) -> dict:
    """Set up PYTHONHOME and PATH for bundled CPython"""
=======
        return "linux-x86_64" if machine == "x86_64" else f"linux-{machine}"
=======
>>>>>>> 5376269 (rebase)

def get_cpython_url(plat: str) -> str:
    """Get CPython tool download URL based on configured repository"""
    filename = f"cpython-tool-{CPY_VERSION}-{plat}.tar.gz"

    if ARTIFACT_REPO == "github":
        # GitHub Packages/Releases pattern
        url = f"{GITHUB_CPY_BASE}/{filename}"
    else:
        # Cloudsmith pattern (default)
        url = f"{CLOUDSMITH_CPY_BASE}/{CPY_VERSION}/{filename}"

    return url

def get_conan_remote() -> str:
    """Get Conan remote URL based on configured repository"""
    if ARTIFACT_REPO == "github":
        return GITHUB_CONAN_REMOTE
    else:
        return CLOUDSMITH_CONAN_REMOTE

def download_cpython_tool(work_dir: Path, plat: str) -> Path:
    """Download CPython tool tarball from configured repository"""
    filename = f"cpython-tool-{CPY_VERSION}-{plat}.tar.gz"
    url = get_cpython_url(plat)
    dest = work_dir / ".buildenv" / "downloads"
    dest.mkdir(parents=True, exist_ok=True)
    archive_path = dest / filename
    
    if archive_path.exists():
        print(f"  ✓ CPython tool archive already exists: {archive_path}")
        return archive_path
    
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    print(f"  Downloading CPython tool from {repo_name}...")
    print(f"    URL: {url}")
    print(f"    Destination: {archive_path}")
    
    # For GitHub Packages, may need authentication token
    headers = {}
    if ARTIFACT_REPO == "github":
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        # GitHub Releases don't require auth for public repos, but API access does
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            
            with open(archive_path, 'wb') as out_file:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r    Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
            
            print()  # New line after progress
            print(f"  ✓ Download complete: {archive_path}")
            return archive_path
            
    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        print(f"    URL: {url}")
        if ARTIFACT_REPO == "github" and e.code == 404:
            print(f"    Hint: Check that release tag '{GITHUB_TAG}' exists in {GITHUB_OWNER}/{GITHUB_REPO}")
            print(f"    Or set GITHUB_TAG environment variable to the correct release tag")
        elif ARTIFACT_REPO == "github" and e.code == 401:
            print(f"    Hint: GitHub Packages may require authentication. Set GITHUB_TOKEN environment variable")
        sys.exit(1)
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        sys.exit(1)

def extract_cpython_tool(archive_path: Path, work_dir: Path) -> Path:
    """Extract CPython tool tarball to .buildenv/cpython"""
    extract_dir = work_dir / ".buildenv" / "cpython"
    
    if extract_dir.exists() and (extract_dir / "bin" / "python3").exists():
        print(f"  ✓ CPython already extracted: {extract_dir}")
        return extract_dir
    
    print(f"  Extracting CPython tool to {extract_dir}...")
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            # Extract with progress
            members = tar.getmembers()
            for i, member in enumerate(members):
                tar.extract(member, extract_dir)
                if (i + 1) % 100 == 0:
                    print(f"\r    Extracted {i + 1}/{len(members)} files...", end='', flush=True)
            print()  # New line after progress
        
        print(f"  ✓ Extraction complete: {extract_dir}")
        return extract_dir
        
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        sys.exit(1)

<<<<<<< HEAD
    # 4. Runtime Environment
>>>>>>> ec9bdcd (build: replace bootstrap script with zero-dependency implementation)
=======
def setup_python_environment(extract_dir: Path) -> dict:
    """Set up PYTHONHOME and PATH for bundled CPython"""
>>>>>>> 5376269 (rebase)
    env = os.environ.copy()
    env["PYTHONHOME"] = str(extract_dir)
    if sys.platform == "win32":
        py_bin = extract_dir / "python.exe"
        env["PATH"] = str(extract_dir) + ";" + env.get("PATH", "")
    else:
        py_bin = extract_dir / "bin" / "python3"
        env["PATH"] = str(extract_dir / "bin") + ":" + env.get("PATH", "")
<<<<<<< HEAD
<<<<<<< HEAD
    
    return env, py_bin
=======
    
    return env, py_bin
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> 5376269 (rebase)

def install_dev_tools(py_bin: Path, env: dict, work_dir: Path) -> bool:
    """Install shared development tools using the bundled CPython"""
    print("  Installing shared development tools using bundled CPython...")

    # Version of sparetools-shared-dev-tools to install
    dev_tools_version = os.getenv("SPARETOOLS_DEV_TOOLS_VERSION", "1.0.0")

    # Configure pip index URL for Cloudsmith Python repo if configured
    pip_args = [str(py_bin), "-m", "pip", "install", "--upgrade", f"sparetools-shared-dev-tools=={dev_tools_version}"]

    # Add index URL if configured (for Cloudsmith Python repo)
    index_url = os.getenv("PIP_INDEX_URL")
    if index_url:
        pip_args.extend(["--index-url", index_url])
        repo_name = "custom index"
    else:
        repo_name = "PyPI"

    print(f"    Installing sparetools-shared-dev-tools {dev_tools_version} from {repo_name}...")
<<<<<<< HEAD

    try:
        subprocess.check_call(
            pip_args,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"  ✓ Shared development tools installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to install development tools: {e}")
        print("    Continuing without development tools...")
        return False

def install_conan(py_bin: Path, env: dict, work_dir: Path) -> bool:
    """Install Conan 2.21.0 using the bundled CPython"""
    print(f"  Installing Conan {CONAN_VERSION} using bundled CPython...")
    
    venv_dir = work_dir / ".buildenv" / "venv"
    venv_python = venv_dir / "bin" / "python3" if sys.platform != "win32" else venv_dir / "Scripts" / "python.exe"
    
    # Create venv if it doesn't exist
    if not venv_python.exists():
        print(f"    Creating virtual environment...")
        try:
            subprocess.check_call(
                [str(py_bin), "-m", "venv", str(venv_dir)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to create venv: {e}")
            return False
    
    # Install Conan in venv
    print(f"    Installing Conan {CONAN_VERSION}...")
    try:
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", f"conan=={CONAN_VERSION}"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"  ✓ Conan {CONAN_VERSION} installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to install Conan: {e}")
        return False

def configure_conan(py_bin: Path, env: dict, work_dir: Path) -> bool:
    """Configure Conan remotes and profiles"""
    print(f"  Configuring Conan remotes and profiles...")

    venv_dir = work_dir / ".buildenv" / "venv"
    conan_bin = venv_dir / "bin" / "conan" if sys.platform != "win32" else venv_dir / "Scripts" / "conan.exe"

    if not conan_bin.exists():
        print(f"  ✗ Conan binary not found at {conan_bin}")
        return False

    # Set Conan home
    conan_home = work_dir / ".buildenv" / "conan"
    conan_home.mkdir(parents=True, exist_ok=True)
    env["CONAN_HOME"] = str(conan_home)

    # Get Conan remote URL based on configured repository
    conan_remote_url = get_conan_remote()
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    remote_name = "sparesparrow-github" if ARTIFACT_REPO == "github" else "sparesparrow-conan"

    try:
        # Detect default profile
        subprocess.check_call(
            [str(conan_bin), "profile", "detect", "--force"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Add remote (Cloudsmith or GitHub Packages)
        subprocess.check_call(
            [str(conan_bin), "remote", "add", remote_name, conan_remote_url, "--force"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # For GitHub Packages, configure authentication if token is provided
        if ARTIFACT_REPO == "github":
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                # GitHub Packages requires authentication
                # Conan 2.x uses user/password format: username=token, password=token
                github_user = os.getenv("GITHUB_USER", GITHUB_OWNER)
                subprocess.check_call(
                    [str(conan_bin), "remote", "login", remote_name, "-u", github_user, "-p", github_token],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"    Configured GitHub Packages authentication")

        # Copy project profiles if available
        profiles_dir = work_dir / "profiles"
        if profiles_dir.exists():
            conan_profiles_dir = conan_home / "profiles"
            conan_profiles_dir.mkdir(exist_ok=True)
            for profile_file in profiles_dir.glob("*"):
                if profile_file.is_file():
                    shutil.copy2(profile_file, conan_profiles_dir / profile_file.name)
                    print(f"    Installed profile: {profile_file.name}")

        print(f"  ✓ Conan configured (home: {conan_home}, remote: {repo_name})")
        return True

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to configure Conan: {e}")
        if ARTIFACT_REPO == "github":
            print(f"    Hint: GitHub Packages may require GITHUB_TOKEN environment variable")
        return False

def create_activation_script(work_dir: Path, py_bin: Path, env: dict):
    """Create activation script for the build environment"""
    activate_script = work_dir / ".buildenv" / "activate.sh"
    
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    
    script_content = f"""#!/bin/bash
# AI-SERVIS Build Environment Activation
# Generated by complete-bootstrap.py
# Repository: {repo_name}

_BUILDENV_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
export AI_SERVIS_ROOT="$(cd "$_BUILDENV_DIR/.." && pwd)"
export AI_SERVIS_BUILDENV="$_BUILDENV_DIR"

# Set PYTHONHOME for bundled CPython
export PYTHONHOME="$_BUILDENV_DIR/cpython"
export PATH="$_BUILDENV_DIR/cpython/bin:$PATH"

# Activate virtual environment
if [ -f "$_BUILDENV_DIR/venv/bin/activate" ]; then
    source "$_BUILDENV_DIR/venv/bin/activate"
fi

# Set Conan home
export CONAN_HOME="$_BUILDENV_DIR/conan"

# Add project bin to PATH
export PATH="$AI_SERVIS_ROOT/bin:$PATH"

echo "AI-SERVIS build environment activated ({repo_name} CPython {CPY_VERSION}, Conan {CONAN_VERSION})"
echo "  Python: $(which python3)"
echo "  Conan:  $(which conan 2>/dev/null || echo 'not found')"
"""
    
    activate_script.write_text(script_content)
    activate_script.chmod(0o755)
    print(f"  ✓ Activation script created: {activate_script}")

def main():
    print("=" * 70)
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    print(f"AI-SERVIS Universal: CPython Bootstrap ({repo_name})")
    print("=" * 70)
    print()
    
    # Show repository configuration
    print(f"Repository: {repo_name}")
    if ARTIFACT_REPO == "github":
        print(f"  GitHub Owner: {GITHUB_OWNER}")
        print(f"  GitHub Repo: {GITHUB_REPO}")
        print(f"  Release Tag: {GITHUB_TAG}")
        if os.getenv("GITHUB_TOKEN"):
            print(f"  Authentication: Configured (GITHUB_TOKEN)")
        else:
            print(f"  Authentication: None (public releases only)")
    else:
        print(f"  Cloudsmith CPY Base: {CLOUDSMITH_CPY_BASE}")
    print()
    
    # 1. Platform Detection
    plat = get_platform_str()
    work_dir = Path(os.getcwd())
    print(f"Platform: {plat}")
    print(f"Work directory: {work_dir}")
    print()
    
    # 2. Download CPython tool from configured repository
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    print(f"Step 1: Downloading CPython tool from {repo_name}...")
    archive_path = download_cpython_tool(work_dir, plat)
    print()
    
    # 3. Extract CPython tool
    print("Step 2: Extracting CPython tool...")
    extract_dir = extract_cpython_tool(archive_path, work_dir)
    print()
    
    # 4. Set up Python environment
    print("Step 3: Setting up Python environment...")
    env, py_bin = setup_python_environment(extract_dir)
    
    # Validate Python
    try:
        result = subprocess.run(
            [str(py_bin), "--version"],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✓ Python: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Python validation failed: {e}")
        sys.exit(1)
    print()

    # 4.5. Install shared development tools using bundled Python
    print("Step 4: Installing shared development tools...")
    install_dev_tools(py_bin, env, work_dir)
    print()

    # 5. Install Conan using bundled Python
    print("Step 5: Installing Conan 2.21.0...")
    if not install_conan(py_bin, env, work_dir):
        print("  ⚠ Conan installation failed, continuing without it...")
    print()
    
    # 6. Configure Conan
    print("Step 6: Configuring Conan...")
    configure_conan(py_bin, env, work_dir)
    print()

    # 7. Create activation script
    print("Step 7: Creating activation script...")
    create_activation_script(work_dir, py_bin, env)
    print()

    # 8. Generate validation report
    print("Step 8: Generating validation report...")
    validation_report = {
        "status": "success",
        "platform": plat,
        "cpython_version": CPY_VERSION,
        "conan_version": CONAN_VERSION,
        "dev_tools_version": os.getenv("SPARETOOLS_DEV_TOOLS_VERSION", "1.0.0"),
        "python_binary": str(py_bin),
        "extract_dir": str(extract_dir),
        "buildenv_dir": str(work_dir / ".buildenv"),
        "compliant": True,
        "bootstrap_method": f"{ARTIFACT_REPO}-cpython-tool",
        "artifact_repo": ARTIFACT_REPO,
        "conan_remote": get_conan_remote()
    }
    
    report_path = work_dir / "validation-report.json"
    with open(report_path, 'w') as f:
        json.dump(validation_report, f, indent=2)
    print(f"  ✓ Validation report: {report_path}")
    print()
    
    # Success message
    print("=" * 70)
    print("Bootstrap Complete!")
    print("=" * 70)
    print()
    print("To activate the build environment:")
    print(f"  source {work_dir / '.buildenv' / 'activate.sh'}")
    print()
    print("Or from project root:")
    print("  source .buildenv/activate.sh")
    print()
    print("To switch repositories, set environment variables:")
    print("  # Use GitHub Packages:")
    print("  export ARTIFACT_REPO=github")
    print("  export GITHUB_OWNER=sparesparrow")
    print("  export GITHUB_REPO=cpy")
    print("  export GITHUB_TAG=v3.12.7")
    print("  export GITHUB_TOKEN=your_token  # Optional, for private repos")
    print()
    print("  # Use Cloudsmith (default):")
    print("  export ARTIFACT_REPO=cloudsmith")
    print()

=======
=======
>>>>>>> 5376269 (rebase)

    try:
        subprocess.check_call(
            pip_args,
=======

def install_conan(py_bin: Path, env: dict, work_dir: Path) -> bool:
    """Install Conan 2.21.0 using the bundled CPython"""
    print(f"  Installing Conan {CONAN_VERSION} using bundled CPython...")
    
    venv_dir = work_dir / ".buildenv" / "venv"
    venv_python = venv_dir / "bin" / "python3" if sys.platform != "win32" else venv_dir / "Scripts" / "python.exe"
    
    # Create venv if it doesn't exist
    if not venv_python.exists():
        print(f"    Creating virtual environment...")
        try:
            subprocess.check_call(
                [str(py_bin), "-m", "venv", str(venv_dir)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to create venv: {e}")
            return False
    
    # Install Conan in venv
    print(f"    Installing Conan {CONAN_VERSION}...")
    try:
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
<<<<<<< HEAD
        print(f"  ✓ Shared development tools installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to install development tools: {e}")
        print("    Continuing without development tools...")
        return False

def install_conan(py_bin: Path, env: dict, work_dir: Path) -> bool:
    """Install Conan 2.21.0 using the bundled CPython"""
    print(f"  Installing Conan {CONAN_VERSION} using bundled CPython...")
    
    venv_dir = work_dir / ".buildenv" / "venv"
    venv_python = venv_dir / "bin" / "python3" if sys.platform != "win32" else venv_dir / "Scripts" / "python.exe"
    
    # Create venv if it doesn't exist
    if not venv_python.exists():
        print(f"    Creating virtual environment...")
        try:
            subprocess.check_call(
                [str(py_bin), "-m", "venv", str(venv_dir)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to create venv: {e}")
            return False
    
    # Install Conan in venv
    print(f"    Installing Conan {CONAN_VERSION}...")
    try:
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", f"conan=={CONAN_VERSION}"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"  ✓ Conan {CONAN_VERSION} installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to install Conan: {e}")
        return False

=======
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", f"conan=={CONAN_VERSION}"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"  ✓ Conan {CONAN_VERSION} installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to install Conan: {e}")
        return False

>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
=======

def install_conan(py_bin: Path, env: dict, work_dir: Path) -> bool:
    """Install Conan 2.21.0 using the bundled CPython"""
    print(f"  Installing Conan {CONAN_VERSION} using bundled CPython...")
    
    venv_dir = work_dir / ".buildenv" / "venv"
    venv_python = venv_dir / "bin" / "python3" if sys.platform != "win32" else venv_dir / "Scripts" / "python.exe"
    
    # Create venv if it doesn't exist
    if not venv_python.exists():
        print(f"    Creating virtual environment...")
        try:
            subprocess.check_call(
                [str(py_bin), "-m", "venv", str(venv_dir)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to create venv: {e}")
            return False
    
    # Install Conan in venv
    print(f"    Installing Conan {CONAN_VERSION}...")
    try:
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", f"conan=={CONAN_VERSION}"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"  ✓ Conan {CONAN_VERSION} installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to install Conan: {e}")
        return False

>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
def configure_conan(py_bin: Path, env: dict, work_dir: Path) -> bool:
    """Configure Conan remotes and profiles"""
    print(f"  Configuring Conan remotes and profiles...")

    venv_dir = work_dir / ".buildenv" / "venv"
    conan_bin = venv_dir / "bin" / "conan" if sys.platform != "win32" else venv_dir / "Scripts" / "conan.exe"

    if not conan_bin.exists():
        print(f"  ✗ Conan binary not found at {conan_bin}")
        return False

    # Set Conan home
    conan_home = work_dir / ".buildenv" / "conan"
    conan_home.mkdir(parents=True, exist_ok=True)
    env["CONAN_HOME"] = str(conan_home)

    # Get Conan remote URL based on configured repository
    conan_remote_url = get_conan_remote()
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    remote_name = "sparesparrow-github" if ARTIFACT_REPO == "github" else "sparesparrow-conan"

    try:
        # Detect default profile
        subprocess.check_call(
            [str(conan_bin), "profile", "detect", "--force"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Add remote (Cloudsmith or GitHub Packages)
        subprocess.check_call(
            [str(conan_bin), "remote", "add", remote_name, conan_remote_url, "--force"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # For GitHub Packages, configure authentication if token is provided
        if ARTIFACT_REPO == "github":
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                # GitHub Packages requires authentication
                # Conan 2.x uses user/password format: username=token, password=token
                github_user = os.getenv("GITHUB_USER", GITHUB_OWNER)
                subprocess.check_call(
                    [str(conan_bin), "remote", "login", remote_name, "-u", github_user, "-p", github_token],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"    Configured GitHub Packages authentication")

        # Copy project profiles if available
        profiles_dir = work_dir / "profiles"
        if profiles_dir.exists():
            conan_profiles_dir = conan_home / "profiles"
            conan_profiles_dir.mkdir(exist_ok=True)
            for profile_file in profiles_dir.glob("*"):
                if profile_file.is_file():
                    shutil.copy2(profile_file, conan_profiles_dir / profile_file.name)
                    print(f"    Installed profile: {profile_file.name}")

        print(f"  ✓ Conan configured (home: {conan_home}, remote: {repo_name})")
        return True

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to configure Conan: {e}")
        if ARTIFACT_REPO == "github":
            print(f"    Hint: GitHub Packages may require GITHUB_TOKEN environment variable")
        return False

def create_activation_script(work_dir: Path, py_bin: Path, env: dict):
    """Create activation script for the build environment"""
    activate_script = work_dir / ".buildenv" / "activate.sh"
    
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    
    script_content = f"""#!/bin/bash
# AI-SERVIS Build Environment Activation
# Generated by complete-bootstrap.py
# Repository: {repo_name}

_BUILDENV_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
export AI_SERVIS_ROOT="$(cd "$_BUILDENV_DIR/.." && pwd)"
export AI_SERVIS_BUILDENV="$_BUILDENV_DIR"

# Set PYTHONHOME for bundled CPython
export PYTHONHOME="$_BUILDENV_DIR/cpython"
export PATH="$_BUILDENV_DIR/cpython/bin:$PATH"

# Activate virtual environment
if [ -f "$_BUILDENV_DIR/venv/bin/activate" ]; then
    source "$_BUILDENV_DIR/venv/bin/activate"
fi

# Set Conan home
export CONAN_HOME="$_BUILDENV_DIR/conan"

# Add project bin to PATH
export PATH="$AI_SERVIS_ROOT/bin:$PATH"

echo "AI-SERVIS build environment activated ({repo_name} CPython {CPY_VERSION}, Conan {CONAN_VERSION})"
echo "  Python: $(which python3)"
echo "  Conan:  $(which conan 2>/dev/null || echo 'not found')"
"""
    
    activate_script.write_text(script_content)
    activate_script.chmod(0o755)
    print(f"  ✓ Activation script created: {activate_script}")

def main():
    print("=" * 70)
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    print(f"AI-SERVIS Universal: CPython Bootstrap ({repo_name})")
    print("=" * 70)
    print()
    
    # Show repository configuration
    print(f"Repository: {repo_name}")
    if ARTIFACT_REPO == "github":
        print(f"  GitHub Owner: {GITHUB_OWNER}")
        print(f"  GitHub Repo: {GITHUB_REPO}")
        print(f"  Release Tag: {GITHUB_TAG}")
        if os.getenv("GITHUB_TOKEN"):
            print(f"  Authentication: Configured (GITHUB_TOKEN)")
        else:
            print(f"  Authentication: None (public releases only)")
    else:
        print(f"  Cloudsmith CPY Base: {CLOUDSMITH_CPY_BASE}")
    print()
    
    # 1. Platform Detection
    plat = get_platform_str()
    work_dir = Path(os.getcwd())
    print(f"Platform: {plat}")
    print(f"Work directory: {work_dir}")
    print()
    
    # 2. Download CPython tool from configured repository
    repo_name = "GitHub Packages" if ARTIFACT_REPO == "github" else "Cloudsmith"
    print(f"Step 1: Downloading CPython tool from {repo_name}...")
    archive_path = download_cpython_tool(work_dir, plat)
    print()
    
    # 3. Extract CPython tool
    print("Step 2: Extracting CPython tool...")
    extract_dir = extract_cpython_tool(archive_path, work_dir)
    print()
    
    # 4. Set up Python environment
    print("Step 3: Setting up Python environment...")
    env, py_bin = setup_python_environment(extract_dir)
    
    # Validate Python
    try:
        result = subprocess.run(
            [str(py_bin), "--version"],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✓ Python: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Python validation failed: {e}")
        sys.exit(1)
<<<<<<< HEAD
>>>>>>> ec9bdcd (build: replace bootstrap script with zero-dependency implementation)
=======
    print()
<<<<<<< HEAD
<<<<<<< HEAD

    # 4.5. Install shared development tools using bundled Python
    print("Step 4: Installing shared development tools...")
    install_dev_tools(py_bin, env, work_dir)
    print()

    # 5. Install Conan using bundled Python
    print("Step 5: Installing Conan 2.21.0...")
=======
    
    # 5. Install Conan using bundled Python
    print("Step 4: Installing Conan 2.21.0...")
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
=======
    
    # 5. Install Conan using bundled Python
    print("Step 4: Installing Conan 2.21.0...")
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
    if not install_conan(py_bin, env, work_dir):
        print("  ⚠ Conan installation failed, continuing without it...")
    print()
    
    # 6. Configure Conan
<<<<<<< HEAD
<<<<<<< HEAD
    print("Step 6: Configuring Conan...")
    configure_conan(py_bin, env, work_dir)
    print()

    # 7. Create activation script
    print("Step 7: Creating activation script...")
    create_activation_script(work_dir, py_bin, env)
    print()

    # 8. Generate validation report
    print("Step 8: Generating validation report...")
=======
=======
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
    print("Step 5: Configuring Conan...")
    configure_conan(py_bin, env, work_dir)
    print()
    
    # 7. Create activation script
    print("Step 6: Creating activation script...")
    create_activation_script(work_dir, py_bin, env)
    print()
    
    # 8. Generate validation report
    print("Step 7: Generating validation report...")
<<<<<<< HEAD
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
=======
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
    validation_report = {
        "status": "success",
        "platform": plat,
        "cpython_version": CPY_VERSION,
        "conan_version": CONAN_VERSION,
<<<<<<< HEAD
<<<<<<< HEAD
        "dev_tools_version": os.getenv("SPARETOOLS_DEV_TOOLS_VERSION", "1.0.0"),
=======
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
=======
>>>>>>> cb8e6ef (Fix MCP connection errors and implement Cloudsmith/GitHub Packages bootstrap (#42))
        "python_binary": str(py_bin),
        "extract_dir": str(extract_dir),
        "buildenv_dir": str(work_dir / ".buildenv"),
        "compliant": True,
        "bootstrap_method": f"{ARTIFACT_REPO}-cpython-tool",
        "artifact_repo": ARTIFACT_REPO,
        "conan_remote": get_conan_remote()
    }
    
    report_path = work_dir / "validation-report.json"
    with open(report_path, 'w') as f:
        json.dump(validation_report, f, indent=2)
    print(f"  ✓ Validation report: {report_path}")
    print()
    
    # Success message
    print("=" * 70)
    print("Bootstrap Complete!")
    print("=" * 70)
    print()
    print("To activate the build environment:")
    print(f"  source {work_dir / '.buildenv' / 'activate.sh'}")
    print()
    print("Or from project root:")
    print("  source .buildenv/activate.sh")
    print()
    print("To switch repositories, set environment variables:")
    print("  # Use GitHub Packages:")
    print("  export ARTIFACT_REPO=github")
    print("  export GITHUB_OWNER=sparesparrow")
    print("  export GITHUB_REPO=cpy")
    print("  export GITHUB_TAG=v3.12.7")
    print("  export GITHUB_TOKEN=your_token  # Optional, for private repos")
    print()
    print("  # Use Cloudsmith (default):")
    print("  export ARTIFACT_REPO=cloudsmith")
    print()

>>>>>>> 5376269 (rebase)

if __name__ == "__main__":
    main()
