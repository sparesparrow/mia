#!/bin/bash
set -euo pipefail

python3 tools/scripts/build_variant.py business-car business
python3 tools/scripts/build_variant.py gonzo-car gonzo
python3 tools/scripts/build_variant.py family-car family
python3 tools/scripts/build_variant.py dj-car musicians

echo "✅ All variants built successfully"
