#!/bin/bash
set -euo pipefail

python3 scripts/build_variant.py business-car business
python3 scripts/build_variant.py gonzo-car gonzo
python3 scripts/build_variant.py family-car family
python3 scripts/build_variant.py dj-car musicians

echo "✅ All variants built successfully"
