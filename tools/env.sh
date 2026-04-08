#!/bin/bash
# AI-SERVIS environment activation wrapper
# Source this from project root: source tools/env.sh

is_sourced() {
    [[ "${BASH_SOURCE[0]}" != "$0" ]]
}

fail_activation() {
    echo "$1" >&2
    if is_sourced; then
        return 1
    fi

    exit 1
}

if ! is_sourced; then
    echo "This script must be sourced: source tools/env.sh" >&2
    exit 1
fi

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"

if [ -f "$_PROJECT_ROOT/.buildenv/activate.sh" ]; then
    source "$_PROJECT_ROOT/.buildenv/activate.sh"
else
    fail_activation "Build environment not set up. Run: ./tools/init.sh"
fi
