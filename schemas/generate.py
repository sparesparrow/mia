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


def generate_bindings(schema_file, output_dir, language, extra_flags=None):
    """Generate bindings for a given language from a FlatBuffers schema.

    Args:
        schema_file: Path to .fbs schema file
        output_dir: Output directory for generated code
        language: flatc flag (e.g., '--python', '--cpp', '--kotlin', '--ts', '--rust')
        extra_flags: Additional flatc flags (list of strings)

    Returns:
        True on success, False on failure
    """
    flatc = find_flatc()
    if not flatc:
        print("Error: flatc compiler not found. Install with: sudo apt install flatbuffers-compiler")
        return False

    schema_path = Path(schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_file}")
        return False

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cmd = [flatc, language, '-o', str(output_path)]
    if extra_flags:
        cmd.extend(extra_flags)
    cmd.append(str(schema_path))

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


def find_all_schemas(project_root):
    """Find all .fbs files in schemas/ and protos/ directories."""
    schemas = []
    for search_dir in ['schemas', 'protos']:
        schema_dir = project_root / search_dir
        if schema_dir.exists():
            for fbs in sorted(schema_dir.glob('*.fbs')):
                schemas.append(fbs)
    return schemas


def main():
    parser = argparse.ArgumentParser(description='Generate FlatBuffers bindings')
    parser.add_argument('--python', action='store_true', default=False,
                       help='Generate Python bindings')
    parser.add_argument('--cpp', action='store_true', default=False,
                       help='Generate C++ bindings')
    parser.add_argument('--kotlin', action='store_true', default=False,
                       help='Generate Kotlin bindings')
    parser.add_argument('--ts', action='store_true', default=False,
                       help='Generate TypeScript bindings')
    parser.add_argument('--rust', action='store_true', default=False,
                       help='Generate Rust bindings')
    parser.add_argument('--all-schemas', action='store_true', default=False,
                       help='Process all .fbs files in schemas/ and protos/')
    parser.add_argument('--output-dir', default='..',
                       help='Output directory relative to schemas/ (default: ..)')
    parser.add_argument('--schema', default='mia.fbs',
                       help='Schema file to process (default: mia.fbs)')

    args = parser.parse_args()

    # If no language flags specified, default to python + cpp
    if not any([args.python, args.cpp, args.kotlin, args.ts, args.rust]):
        args.python = True
        args.cpp = True

    # Get script directory and resolve paths
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    output_dir = (script_dir / args.output_dir).absolute()

    # Determine which schemas to process
    if args.all_schemas:
        schema_files = find_all_schemas(project_root)
    else:
        schema_files = [script_dir / args.schema]

    print(f"FlatBuffers Schema Generation (flatc {FLATC_VERSION})")
    print(f"Output: {output_dir}")
    print(f"Schemas: {len(schema_files)} file(s)")
    print("-" * 50)

    success = True

    for schema_file in schema_files:
        print(f"\nProcessing: {schema_file.name}")

        if args.python:
            if not generate_bindings(schema_file, output_dir, '--python'):
                success = False

        if args.cpp:
            cpp_output = output_dir / "platforms" / "cpp" / "core"
            if not generate_bindings(schema_file, cpp_output, '--cpp',
                                     ['--gen-mutable', '--scoped-enums']):
                success = False

        if args.kotlin:
            kotlin_output = output_dir / "generated" / "kotlin"
            if not generate_bindings(schema_file, kotlin_output, '--kotlin'):
                success = False

        if args.ts:
            ts_output = output_dir / "generated" / "ts"
            if not generate_bindings(schema_file, ts_output, '--ts'):
                success = False

        if args.rust:
            rust_output = output_dir / "generated" / "rust"
            if not generate_bindings(schema_file, rust_output, '--rust'):
                success = False

    if success:
        print("\n" + "-" * 50)
        print("All bindings generated successfully!")
    else:
        print("\n" + "-" * 50)
        print("Some bindings failed to generate. Check errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
