#!/usr/bin/env python3
"""Print the schema hash the Android build and bin/mia-apply-update compare (ADR-0023, REQ-UPD-002).

    python3 tools/ci/schema_hash.py [schemas-dir]      # default: <repo>/schemas

Docker builds whose context lacks ../../schemas pass it on: docker build --build-arg MIA_SCHEMA_HASH=$(python3 tools/ci/schema_hash.py) apps/android
"""

import hashlib
import sys
from pathlib import Path


def schema_hash(directory: Path) -> str:
    files = sorted(directory.glob("*.fbs"))
    if not files:
        raise SystemExit(f"no *.fbs files in {directory}")
    digest = hashlib.sha256()
    for f in files:
        digest.update(f"{f.name}\n{hashlib.sha256(f.read_bytes()).hexdigest()}\n".encode())
    return digest.hexdigest()


if __name__ == "__main__":
    print(schema_hash(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "schemas"))
