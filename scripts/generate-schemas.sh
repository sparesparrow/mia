#!/bin/bash
# Thin wrapper around the unified schema generator.
# Prefer: python schemas/generate.py --all
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Delegating to unified schema generator ..."
python3 "$PROJECT_ROOT/schemas/generate.py" --all "$@"
