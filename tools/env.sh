#!/bin/bash
# AI-SERVIS environment activation wrapper
# Source this from project root: source tools/env.sh

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"

if [ -f "$_PROJECT_ROOT/.buildenv/activate.sh" ]; then
    source "$_PROJECT_ROOT/.buildenv/activate.sh"
else
    echo "Build environment not set up. Run: ./tools/bootstrap.sh"
    return 1
fi
