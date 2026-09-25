#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "$ROOT/tools/vehicle-replay/replay.py" \
  --input "$ROOT/tests/fixtures/cycle1_bench.jsonl" \
  --device-id cycle1-bench \
  --source replay.can \
  --confidence 1.0 \
  --expect-complete
