#!/usr/bin/env python3
"""
FlatBuffers Schema Generation Script

This script generates Python and C++ bindings from FlatBuffers schema files.
It extends the existing generation process to include the new MIA schemas.

Usage:
    python schemas/generate.py [--python] [--cpp] [--output-dir DIR]

Options:
    --python        Generate Python bindings (default: True)
    --cpp          Generate C++ bindings (default: True)
    --output-dir   Output directory (default: project root)
    --help         Show this help message
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

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

def generate_python_bindings(schema_file, output_dir):
    """Generate Python bindings from FlatBuffers schema"""
    flatc = find_flatc()
    if not flatc:
        print("Error: flatc compiler not found. Install with: sudo apt install flatbuffers-compiler")
        return False

    schema_path = Path(schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_file}")
        return False

    output_path = Path(output_dir)

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        flatc,
        '--python',
        '-o', str(output_path),
        str(schema_path)
    ]

    print(f"Generating Python bindings: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir)
        if result.returncode == 0:
            print(f"✓ Python bindings generated successfully in {output_path}")
            return True
        else:
            print(f"✗ Failed to generate Python bindings: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error generating Python bindings: {e}")
        return False

def generate_cpp_bindings(schema_file, output_dir):
    """Generate C++ bindings from FlatBuffers schema"""
    flatc = find_flatc()
    if not flatc:
        print("Error: flatc compiler not found. Install with: sudo apt install flatbuffers-compiler")
        return False

    schema_path = Path(schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_file}")
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
        str(schema_path)
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

def main():
    parser = argparse.ArgumentParser(description='Generate FlatBuffers bindings')
    parser.add_argument('--python', action='store_true', default=True,
                       help='Generate Python bindings (default: True)')
    parser.add_argument('--cpp', action='store_true', default=True,
                       help='Generate C++ bindings (default: True)')
    parser.add_argument('--output-dir', default='..',
                       help='Output directory relative to schemas/ (default: ..)')
    parser.add_argument('--schema', default='mia.fbs',
                       help='Schema file to process (default: mia.fbs)')

    args = parser.parse_args()

    # Get script directory and resolve paths
    script_dir = Path(__file__).parent.absolute()
    schema_file = script_dir / args.schema
    output_dir = (script_dir / args.output_dir).absolute()

    print(f"FlatBuffers Schema Generation")
    print(f"Schema: {schema_file}")
    print(f"Output: {output_dir}")
    print("-" * 50)

    success = True

    if args.python:
        print("Generating Python bindings...")
        if not generate_python_bindings(schema_file, output_dir):
            success = False

    if args.cpp:
        print("Generating C++ bindings...")
        cpp_output = output_dir / "platforms" / "cpp" / "core"
        if not generate_cpp_bindings(schema_file, cpp_output):
            success = False

    if success:
        print("-" * 50)
        print("✓ All bindings generated successfully!")
        print("\nNext steps:")
        print("1. Update your import statements to use the new Mia namespace")
        print("2. Update existing code to use the new message types")
        print("3. Run tests to verify compatibility")
    else:
        print("-" * 50)
        print("✗ Some bindings failed to generate. Check errors above.")
        sys.exit(1)

if __name__ == '__main__':
    main()