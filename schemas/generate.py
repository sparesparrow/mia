#!/usr/bin/env python3
"""
FlatBuffers Schema Generation Script

This script generates language bindings from FlatBuffers schema files.
Supports Python, C++, Kotlin, TypeScript, and Rust.

Usage:
    python schemas/generate.py [--python] [--cpp] [--kotlin] [--ts] [--rust] [--all-schemas]

Options:
    --python        Generate Python bindings (default: True)
    --cpp           Generate C++ bindings (default: True)
    --kotlin        Generate Kotlin bindings
    --ts            Generate TypeScript bindings
    --rust          Generate Rust bindings
    --all-schemas   Process all .fbs files in schemas/ and protos/
    --output-dir    Output directory (default: project root)
    --schema        Single schema file to process (default: mia.fbs)
    --dry-run       Show expected outputs and detect drift (exit 0=clean, 2=drift)
    --help          Show this help message
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# FlatBuffers compiler version used for this project
FLATC_VERSION = "24.3.25"


def find_flatc():
    """Find the flatc compiler in PATH"""
    try:
        result = subprocess.run(['which', 'flatc'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    # Try common installation paths
    common_paths = [
        '/usr/local/bin/flatc',
        '/usr/bin/flatc',
        '/opt/homebrew/bin/flatc',  # macOS with Homebrew
        'C:\\Program Files\\flatbuffers\\flatc.exe',  # Windows
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None

def _normalize_schema_files(schema_files):
    if isinstance(schema_files, (str, Path)):
        return [Path(schema_files)]
    return [Path(schema_file) for schema_file in schema_files]


def generate_python_bindings(schema_files, output_dir):
    """Generate Python bindings from one or more FlatBuffers schemas."""
    flatc = find_flatc()
    if not flatc:
        print("Error: flatc compiler not found. Install with: sudo apt install flatbuffers-compiler")
        return False

    schema_paths = _normalize_schema_files(schema_files)
    missing = [str(schema_path) for schema_path in schema_paths if not schema_path.exists()]
    if missing:
        print(f"Error: Schema file not found: {', '.join(missing)}")
        return False

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        flatc,
        '--python',
        '-o', str(output_path),
        *[str(schema_path) for schema_path in schema_paths],
    ]

    lang_name = language.lstrip('-')
    print(f"  Generating {lang_name}: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(output_path))
        if result.returncode == 0:
            print(f"  -> {lang_name} bindings generated in {output_path}")
            return True
        else:
            print(f"  -> FAILED {lang_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"  -> ERROR {lang_name}: {e}")
        return False

def generate_cpp_bindings(schema_files, output_dir):
    """Generate C++ bindings from one or more FlatBuffers schemas."""
    flatc = find_flatc()
    if not flatc:
        print("Error: flatc compiler not found. Install with: sudo apt install flatbuffers-compiler")
        return False

    schema_paths = _normalize_schema_files(schema_files)
    missing = [str(schema_path) for schema_path in schema_paths if not schema_path.exists()]
    if missing:
        print(f"Error: Schema file not found: {', '.join(missing)}")
        return False

    output_path = Path(output_dir)

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        flatc,
        '--cpp',
        '--gen-mutable',
        '--scoped-enums',
        '-o', str(output_path),
        *[str(schema_path) for schema_path in schema_paths],
    ]

    print(f"Generating C++ bindings: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir)
        if result.returncode == 0:
            print(f"✓ C++ bindings generated successfully in {output_path}")
            return True
        else:
            print(f"✗ Failed to generate C++ bindings: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error generating C++ bindings: {e}")
        return False

def generate_all(project_root, gen_python=True, gen_cpp=True):
    """Generate bindings from all known FlatBuffers schemas in the project.

    Schema sources and their outputs:
    schemas/vehicle_telemetry.fbs + schemas/mia.fbs -> Mia/*.py / platforms/cpp/core/*.h
    schemas/vehicle_telemetry.fbs + protos/vehicle.fbs -> canonical vehicle bindings with wire wrapper validation
    cpp-audio webgrab.fbs -> webgrab_generated.h (C++ only)
    """
    success = True
    schemas = []

    vehicle_shared_schema = project_root / "schemas" / "vehicle_telemetry.fbs"

    # 1. Core schema (GPIO, sensors, system, LED, vehicle base)
    core_schema = project_root / "schemas" / "mia.fbs"
    if core_schema.exists() and vehicle_shared_schema.exists():
        schemas.append(("core (mia.fbs)", core_schema))
        if gen_python:
            print("\n[core] Generating Python bindings from mia.fbs ...")
            if not generate_python_bindings([vehicle_shared_schema, core_schema], project_root):
                success = False
        if gen_cpp:
            print("\n[core] Generating C++ bindings from mia.fbs ...")
            cpp_out = project_root / "platforms" / "cpp" / "core"
            if not generate_cpp_bindings([vehicle_shared_schema, core_schema], cpp_out):
                success = False
    else:
        print(f"⚠ Schema not found: {core_schema} or {vehicle_shared_schema}")

    # 2. Vehicle wire wrapper (validates root type + file identifier for PUB/SUB telemetry)
    vehicle_schema = project_root / "protos" / "vehicle.fbs"
    if vehicle_schema.exists() and vehicle_shared_schema.exists():
        schemas.append(("vehicle (vehicle.fbs)", vehicle_schema))
        if gen_python:
            print("\n[vehicle] Generating Python bindings from vehicle.fbs ...")
            if not generate_python_bindings([vehicle_shared_schema, vehicle_schema], project_root):
                success = False
    else:
        print(f"⚠ Schema not found: {vehicle_schema} or {vehicle_shared_schema}")

    # 3. C++ protocol schema (webgrab.fbs) — C++ only
    webgrab_schema = project_root / "apps" / "rpi-backend" / "cpp-audio" / "core" / "webgrab.fbs"
    if webgrab_schema.exists():
        schemas.append(("protocol (webgrab.fbs)", webgrab_schema))
        if gen_cpp:
            print("\n[protocol] Generating C++ bindings from webgrab.fbs ...")
            webgrab_out = webgrab_schema.parent
            if not generate_cpp_bindings(webgrab_schema, webgrab_out):
                success = False
    else:
        print(f"⚠ Schema not found: {webgrab_schema}")

    print("\n" + "-" * 50)
    print(f"Schemas processed: {', '.join(name for name, _ in schemas)}")
    return success


def _dry_run(schema_dir, project_root, gen_python, gen_cpp):
    """Report schema sources, expected output paths, and detect drift."""
    import re

    print("DRY-RUN: Schema drift detection")
    print("=" * 60)

    # Collect schema sources
    schemas_found = list(schema_dir.glob("*.fbs"))
    protos_dir = project_root / "protos"
    if protos_dir.is_dir():
        schemas_found.extend(protos_dir.glob("*.fbs"))
    webgrab = project_root / "apps" / "rpi-backend" / "cpp-audio" / "core" / "webgrab.fbs"
    if webgrab.exists():
        schemas_found.append(webgrab)

    print(f"\nSchema sources ({len(schemas_found)}):")
    for s in sorted(schemas_found):
        print(f"  {s.relative_to(project_root)}")

    # Parse tables/structs from schemas to predict output file names
    expected_python = set()
    expected_cpp = set()
    table_pattern = re.compile(r"^\s*(?:table|struct|enum|union)\s+(\w+)", re.MULTILINE)

    for schema_path in schemas_found:
        content = schema_path.read_text(encoding="utf-8", errors="replace")
        # extract namespace
        ns_match = re.search(r"^\s*namespace\s+([\w.]+)\s*;", content, re.MULTILINE)
        namespace = ns_match.group(1) if ns_match else ""
        ns_parts = namespace.split(".") if namespace else []

        for match in table_pattern.finditer(content):
            name = match.group(1)
            if gen_python:
                py_path = project_root / Path(*ns_parts) / f"{name}.py"
                expected_python.add(py_path)
            if gen_cpp:
                expected_cpp.add(name)

    # Check existing bindings
    mia_dir = project_root / "Mia"
    existing_python = set(mia_dir.glob("*.py")) if mia_dir.is_dir() else set()

    drift_issues = []

    if gen_python:
        print(f"\nPython bindings (expected dir: Mia/):")
        print(f"  Expected types: {len(expected_python)}")
        print(f"  Existing files: {len(existing_python)}")

        # Check for orphaned files (exist but no longer in schema)
        expected_names = {p.name for p in expected_python}
        existing_names = {p.name for p in existing_python if p.name != "__init__.py"}
        orphaned = existing_names - expected_names
        missing = expected_names - existing_names

        if orphaned:
            drift_issues.append(f"Orphaned Python bindings (no schema source): {sorted(orphaned)}")
            print(f"  [!] Orphaned: {sorted(orphaned)}")
        if missing:
            drift_issues.append(f"Missing Python bindings (need regeneration): {sorted(missing)}")
            print(f"  [!] Missing: {sorted(missing)}")
        if not orphaned and not missing:
            print("  [ok] No drift detected")

    if gen_cpp:
        cpp_dir = project_root / "platforms" / "cpp" / "core"
        existing_cpp = set(cpp_dir.glob("*_generated.h")) if cpp_dir.is_dir() else set()
        print(f"\nC++ bindings (expected dir: platforms/cpp/core/):")
        print(f"  Expected types: {len(expected_cpp)}")
        print(f"  Existing headers: {len(existing_cpp)}")

    print("\n" + "=" * 60)
    if drift_issues:
        print("DRIFT DETECTED:")
        for issue in drift_issues:
            print(f"  - {issue}")
        sys.exit(2)
    else:
        print("[ok] No schema drift detected.")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Generate FlatBuffers bindings')
    parser.add_argument('--python', action='store_true', default=None,
                       help='Generate Python bindings')
    parser.add_argument('--no-python', action='store_true', default=False,
                       help='Skip Python bindings')
    parser.add_argument('--cpp', action='store_true', default=None,
                       help='Generate C++ bindings')
    parser.add_argument('--no-cpp', action='store_true', default=False,
                       help='Skip C++ bindings')
    parser.add_argument('--all', action='store_true', default=False,
                       help='Generate from all known schemas (mia.fbs, vehicle.fbs, webgrab.fbs)')
    parser.add_argument('--output-dir', default='..',
                       help='Output directory relative to schemas/ (default: ..)')
    parser.add_argument('--schema', default='mia.fbs',
                       help='Schema file to process when not using --all (default: mia.fbs)')
    parser.add_argument('--dry-run', action='store_true', default=False,
                       help='Show what would be generated and detect drift without running flatc')

    args = parser.parse_args()

    gen_python = not args.no_python
    gen_cpp = not args.no_cpp

    script_dir = Path(__file__).parent.resolve()
    project_root = (script_dir / args.output_dir).resolve()

    # --dry-run: report schemas, expected outputs, and drift without invoking flatc
    if args.dry_run:
        return _dry_run(script_dir, project_root, gen_python, gen_cpp)

    print(f"FlatBuffers Schema Generation")
    print(f"Project root: {project_root}")
    print("-" * 50)

    if args.all:
        success = generate_all(project_root, gen_python=gen_python, gen_cpp=gen_cpp)
    else:
        schema_file = script_dir / args.schema
        print(f"Schema: {schema_file}")
        print("-" * 50)

        success = True
        if gen_python:
            print("Generating Python bindings...")
            if not generate_python_bindings(schema_file, project_root):
                success = False
        if gen_cpp:
            print("Generating C++ bindings...")
            cpp_output = project_root / "platforms" / "cpp" / "core"
            if not generate_cpp_bindings(schema_file, cpp_output):
                success = False

    if success:
        print("✓ All bindings generated successfully!")
    else:
        print("✗ Some bindings failed to generate. Check errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
