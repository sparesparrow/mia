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

    args = parser.parse_args()

    gen_python = not args.no_python
    gen_cpp = not args.no_cpp

    script_dir = Path(__file__).parent.absolute()
    project_root = (script_dir / args.output_dir).absolute()

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
