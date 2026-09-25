#!/usr/bin/env bash
set -euo pipefail

# Serial device capture with timestamped output
# Usage: serial-capture.sh <device> [baud] [duration_sec] [output_file]

DEVICE="${1:?Usage: $0 <device> [baud] [duration_sec] [output_file]}"
BAUD="${2:-115200}"
DURATION="${3:-30}"
OUTPUT="${4:-/tmp/serial-capture-$(date +%s).txt}"

[[ -e "$DEVICE" ]] || { echo "ERROR: $DEVICE not found"; exit 1; }

echo "Capturing $DEVICE @ ${BAUD}baud for ${DURATION}s → $OUTPUT"

# Configure port
stty -F "$DEVICE" "$BAUD" cs8 -cstopb -parenb raw -echo 2>/dev/null || true

# Capture with timestamps
timeout "$DURATION" stdbuf -oL cat "$DEVICE" 2>/dev/null | while IFS= read -r line; do
  echo "[$(date +'%H:%M:%S.%3N')] $line"
done > "$OUTPUT" 2>&1 || true

LINES=$(wc -l < "$OUTPUT" 2>/dev/null || echo 0)
echo "Captured $LINES lines → $OUTPUT"
