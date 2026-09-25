#!/usr/bin/env python3
"""Replay a Cycle 1 CAN JSONL trace and emit the canonical envelope."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RPI_ROOT = ROOT / "apps" / "rpi-backend"
if str(RPI_ROOT) not in sys.path:
    sys.path.insert(0, str(RPI_ROOT))

from shared.telemetry.can_replay import Cycle1CANDecoder


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--device-id", default="cycle1-bench")
    p.add_argument("--source", default="replay.can")
    p.add_argument("--confidence", type=float, default=1.0)
    p.add_argument("--expect-complete", action="store_true")
    p.add_argument("--delay-ms", type=int, default=0)
    args = p.parse_args()
    decoder = Cycle1CANDecoder(device_id=args.device_id, source=args.source, confidence=args.confidence)
    emitted = 0
    for number, line in enumerate(args.input.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            envelope = decoder.consume_payload(json.loads(line))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise SystemExit(f"{args.input}:{number}: invalid CAN frame: {exc}") from exc
        if envelope is not None:
            print(json.dumps(envelope, separators=(",", ":"), sort_keys=True))
            emitted += 1
        if args.delay_ms:
            time.sleep(args.delay_ms / 1000)
    if args.expect_complete and emitted == 0:
        print("ERROR: no complete Cycle 1 envelope", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
