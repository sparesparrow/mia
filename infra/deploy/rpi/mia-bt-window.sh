#!/usr/bin/env bash
# Bluetooth pairing window for mia-bt-agent.service (ADR-0025, REQ-ONB-006).
#
# Runs bt-agent (bluez-tools) with the NoInputNoOutput capability ("Just Works" bonding) and keeps the adapter
# discoverable and pairable ONLY while the file $MIA_PAIRING_WINDOW exists and the Unix time inside it is still in
# the future. mia-enroll writes that file after a verified grant, 120 s ahead; an expired, unreadable or implausible
# (more than 300 s ahead) file closes the window and is removed. Because NoInputNoOutput has no confirmation step, the
# window is the whole protection: outside it the adapter is neither discoverable nor pairable.
#
#   mia-bt-window.sh          run the agent and watch the window (the service)
#   mia-bt-window.sh --once   apply the window state once and exit (tests; starts no agent)
#
# Overrides: MIA_PAIRING_WINDOW (/run/mia/pairing-window), MIA_BT_ADAPTER (/org/bluez/hci0), MIA_BT_POLL (1, seconds),
# MIA_BT_NOW (fixed clock for tests). Uses busctl (system D-Bus), not bluetoothctl, which is unreliable without a tty.
set -euo pipefail

WINDOW="${MIA_PAIRING_WINDOW:-/run/mia/pairing-window}"
ADAPTER="${MIA_BT_ADAPTER:-/org/bluez/hci0}"
POLL="${MIA_BT_POLL:-1}"
MAX_AHEAD=300
state=""

window_open() {
    local expiry now
    [ -f "$WINDOW" ] || return 1
    expiry="$(head -c 32 "$WINDOW" | tr -d '[:space:]')"
    now="${MIA_BT_NOW:-$(date +%s)}"
    if [[ "$expiry" =~ ^[0-9]{1,12}$ ]] && [ "$expiry" -gt "$now" ] && [ "$((expiry - now))" -le "$MAX_AHEAD" ]; then
        return 0
    fi
    rm -f "$WINDOW"
    return 1
}

apply() { # apply <true|false> only when the state changes
    [ "$state" = "$1" ] && return 0
    busctl set-property org.bluez "$ADAPTER" org.bluez.Adapter1 Pairable b "$1"
    busctl set-property org.bluez "$ADAPTER" org.bluez.Adapter1 Discoverable b "$1"
    state="$1"
}

tick() {
    if window_open; then apply true; else apply false; fi
}

if [ "${1:-}" = "--once" ]; then
    tick
    exit 0
fi

bt-agent -c NoInputNoOutput &
agent=$!
trap 'kill "$agent" 2>/dev/null || true; state=""; apply false || true' EXIT
trap 'exit 0' TERM INT
while kill -0 "$agent" 2>/dev/null; do
    tick
    sleep "$POLL"
done
echo "mia-bt-window: bt-agent exited" >&2
exit 1
