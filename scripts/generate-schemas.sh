#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FLATC=$(command -v flatc || echo "")
if [ -z "$FLATC" ]; then
    echo "Error: flatc not found. Install with: sudo apt install flatbuffers-compiler"
    exit 1
fi

echo "Generating FlatBuffers bindings..."

# Python bindings from vehicle.fbs
if [ -f "$PROJECT_ROOT/protos/vehicle.fbs" ]; then
    $FLATC --python -o "$PROJECT_ROOT" "$PROJECT_ROOT/protos/vehicle.fbs"
    echo "Generated: Mia/Vehicle/*.py"
fi

# C++ headers from webgrab.fbs
if [ -f "$PROJECT_ROOT/platforms/cpp/core/webgrab.fbs" ]; then
    $FLATC --cpp --gen-mutable \
        -o "$PROJECT_ROOT/platforms/cpp/core/" \
        "$PROJECT_ROOT/platforms/cpp/core/webgrab.fbs"
    echo "Generated: platforms/cpp/core/webgrab_generated.h"
fi

echo "FlatBuffers generation complete."
