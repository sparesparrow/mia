import sys
import os
import platform
import urllib.request
import tarfile
import subprocess
import shutil
import json
from pathlib import Path

# --- CONFIGURATION ---
CPY_VERSION = "3.12.7"
CLOUDSMITH_BASE = "https://dl.cloudsmith.io/sparesparrow/cpy/raw/versions"


def get_platform_str():
    """Determines Cloudsmith platform string."""
    machine = platform.machine()
    system = sys.platform

    # Detect Android (Linux kernel with Android-specific markers)
    if (system == "linux" and
            ("android" in sys.version.lower() or
             "ANDROID_ROOT" in os.environ)):
        return "android-arm64"  # Android typically runs on ARM64

    if system == "win32":
        return "windows-x86_64"
    elif system == "darwin":
        return "macos-arm64" if machine == "arm64" else "macos-x86_64"
    else:
        return "linux-x86_64" if machine == "x86_64" else f"linux-{machine}"


def main():
    print(">>> [MIA] Starting Multi-Agent Bootstrap...")

    # 1. Platform Detection
    plat = get_platform_str()
    work_dir = Path(os.getcwd())
    tools_dir = work_dir / "tools"
    tools_dir.mkdir(exist_ok=True)

    # 2. Download Artifact
    filename = f"cpython-tool-{CPY_VERSION}-{plat}.tar.gz"
    url = f"{CLOUDSMITH_BASE}/{CPY_VERSION}/{filename}"
    dest = tools_dir / filename

    if not dest.exists():
        print(f"Downloading {url}...")
        try:
            with (urllib.request.urlopen(url) as response,
                  open(dest, 'wb') as out_file):
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            print(f"Download failed: {e}")
            sys.exit(1)

    # 3. Extract & Configure
    extract_dir = tools_dir / "cpython"
    if not extract_dir.exists():
        print(f"Extracting to {extract_dir}...")
        with tarfile.open(dest, 'r:gz') as tar:
            tar.extractall(path=extract_dir)

    # 4. Runtime Environment
    env = os.environ.copy()
    env["PYTHONHOME"] = str(extract_dir)

    # Android-specific environment setup
    if plat.startswith("android"):
        # Android uses Bionic libc, set appropriate library paths
        lib_path = str(extract_dir / "lib")
        env["LD_LIBRARY_PATH"] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
        py_bin = extract_dir / "bin" / "python3"
        bin_path = str(extract_dir / "bin")
        env["PATH"] = f"{bin_path}:{env.get('PATH', '')}"
    elif sys.platform == "win32":
        py_bin = extract_dir / "python.exe"
        env["PATH"] = str(extract_dir) + ";" + env.get("PATH", "")
    else:
        py_bin = extract_dir / "bin" / "python3"
        env["PATH"] = str(extract_dir / "bin") + ":" + env.get("PATH", "")

    # 5. Validation & Handoff
    try:
        # Validate Python version
        subprocess.check_call([str(py_bin), "--version"], env=env)

        # Generate Success Marker for CI
        with open("validation-report.json", "w") as f:
            json.dump({
                "status": "success",
                "platform": plat,
                "binary": str(py_bin),
                "compliant": True
            }, f)
        print(">>> [MIA] Bootstrap Complete. Validation marker written.")

    except subprocess.CalledProcessError as e:
        print(f"!!! Bootstrap Verification Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
