#!/usr/bin/env bash
# MIA-Car hotspot as a NetworkManager shared connection (ADR-0025, REQ-ONB-006): ipv4.method shared makes NM run
# DHCP and DNS (its own dnsmasq) for the phones. Phones with a registered MAC (bin/mia-phone-registry, keyed by key
# fingerprint) get a fixed address through a dnsmasq-shared.d fragment.
#
#   setup-nm-hotspot.sh --i-know-this-drops-wlan0 [--dry-run]    create/refresh and bring up the hotspot
#   setup-nm-hotspot.sh --disable [--dry-run]                    take it down, delete it, remove the fragment
#
# wlan0 becomes the access point, so the Pi loses it as an uplink: the flag is mandatory for enabling. --dry-run
# prints the nmcli command lines and the fragment and changes nothing (the passphrase is shown as <redacted>).
# The passphrase is generated here on the Pi (kept if the file exists, so paired phones keep working), mode 600, and
# never printed. It is never an argument of any command either (it would show in `ps`): the connection is rendered
# by `nmcli --offline connection add ...` (stdout only, touches nothing) into a root-only keyfile, the passphrase is
# inserted into that file by a small python step that reads the passphrase file, then `nmcli connection reload`.
# Registry entries are validated before anything is emitted: an invalid MAC or fingerprint is skipped with a warning.
#
# Overrides (tests use a tmp dir and a stub nmcli on PATH): MIA_HOTSPOT_PSK_FILE (/etc/mia/hotspot.psk),
# MIA_NM_CONNECTIONS_DIR (/etc/NetworkManager/system-connections),
# MIA_DNSMASQ_SHARED_DIR (/etc/NetworkManager/dnsmasq-shared.d), MIA_PHONES_FILE (/var/lib/mia/phones.json),
# MIA_HOTSPOT_IFNAME (wlan0), MIA_HOTSPOT_ADDRESS (192.168.4.1/24).
set -euo pipefail

SSID="MIA-Car"
CON="MIA-Car"
IFNAME="${MIA_HOTSPOT_IFNAME:-wlan0}"
ADDRESS="${MIA_HOTSPOT_ADDRESS:-192.168.4.1/24}"
PSK_FILE="${MIA_HOTSPOT_PSK_FILE:-/etc/mia/hotspot.psk}"
FRAGMENT_DIR="${MIA_DNSMASQ_SHARED_DIR:-/etc/NetworkManager/dnsmasq-shared.d}"
PHONES_FILE="${MIA_PHONES_FILE:-/var/lib/mia/phones.json}"
FRAGMENT="$FRAGMENT_DIR/mia-phones.conf"
KEYFILE_DIR="${MIA_NM_CONNECTIONS_DIR:-/etc/NetworkManager/system-connections}"
KEYFILE="$KEYFILE_DIR/$CON.nmconnection"

confirmed=0 disable=0 dry=0
for arg in "$@"; do
    case "$arg" in
        --i-know-this-drops-wlan0) confirmed=1 ;;
        --disable) disable=1 ;;
        --dry-run) dry=1 ;;
        *) echo "setup-nm-hotspot: unknown argument: $arg" >&2; exit 2 ;;
    esac
done

if [ "$disable" -eq 0 ] && [ "$confirmed" -ne 1 ]; then
    echo "setup-nm-hotspot: refusing: this turns $IFNAME into an access point and drops it as the Pi's uplink." >&2
    echo "Run again with --i-know-this-drops-wlan0 if that is what you want." >&2
    exit 2
fi

run() { # print in dry-run, otherwise execute; arguments are never passed through a shell
    if [ "$dry" -eq 1 ]; then
        printf 'DRY-RUN:'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

reservations() { # dhcp-host lines from the registry: one stable address per key fingerprint
    [ -r "$PHONES_FILE" ] || return 0
    python3 - "$PHONES_FILE" "${ADDRESS%.*/*}" <<'PY'
import hashlib, json, re, sys
path, prefix = sys.argv[1], sys.argv[2]
FP_RE = re.compile(r"SHA256:[A-Za-z0-9+/]{43}")  # same as bin/mia-phone-registry
MAC_RE = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}")
try:
    phones = json.load(open(path, encoding="utf-8"))["phones"]
    if not isinstance(phones, dict):
        raise ValueError
except (OSError, ValueError, KeyError, TypeError):
    sys.exit("setup-nm-hotspot: phone registry unreadable, aborting")
used = set()
for index, fp in enumerate(sorted(phones, key=str)):
    entry = phones[fp]
    mac = entry.get("mac", "") if isinstance(entry, dict) else None
    if mac == "":
        continue
    # Only validated values are ever emitted, never raw registry strings (a newline or comma would add dnsmasq options).
    mac = mac.lower() if isinstance(mac, str) else None
    if not isinstance(fp, str) or not FP_RE.fullmatch(fp) or mac is None or not MAC_RE.fullmatch(mac):
        print(f"setup-nm-hotspot: warning: registry entry {index} has an invalid fingerprint or MAC, skipped", file=sys.stderr)
        continue
    n = int.from_bytes(hashlib.sha256(fp.encode()).digest()[:4], "big") % 200
    while n in used:
        n = (n + 1) % 200
    used.add(n)
    print(f"dhcp-host={mac},{prefix}.{20 + n}")
PY
}

# No passphrase here: it is inserted into the keyfile afterwards (see the header).
ADD_ARGS=(nmcli --offline connection add type wifi ifname "$IFNAME" con-name "$CON" autoconnect yes ssid "$SSID"
    802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared ipv4.addresses "$ADDRESS"
    ipv6.method ignore wifi-sec.key-mgmt wpa-psk)

if [ "$disable" -eq 1 ]; then
    run nmcli connection down "$CON" || true
    if [ "$dry" -eq 1 ]; then
        printf 'DRY-RUN: rm -f %q %q\n' "$KEYFILE" "$FRAGMENT"
    else
        rm -f "$KEYFILE" "$FRAGMENT"
    fi
    run nmcli connection reload || true
    exit 0
fi

lines="$(reservations)"
fragment="# MIA phone reservations, generated by setup-nm-hotspot.sh from the phone registry (key fingerprint -> last MAC)"
[ -n "$lines" ] && fragment="$fragment"$'\n'"$lines"

if [ "$dry" -eq 1 ]; then
    echo "DRY-RUN: passphrase file $PSK_FILE: kept if it exists, else generated (mode 600, not printed)"
    echo "DRY-RUN: fragment $FRAGMENT:"
    printf '%s\n' "$fragment"
    printf 'DRY-RUN: keyfile %s (mode 600) = output of the next command plus psk=<redacted> read from %s:\n' "$KEYFILE" "$PSK_FILE"
    run "${ADD_ARGS[@]}"
    run nmcli connection reload
    run nmcli connection up "$CON"
    exit 0
fi

umask 077
if [ ! -s "$PSK_FILE" ]; then
    mkdir -p "$(dirname "$PSK_FILE")"
    python3 -c 'import secrets; print(secrets.token_urlsafe(18))' > "$PSK_FILE.tmp"
    chmod 600 "$PSK_FILE.tmp"
    mv "$PSK_FILE.tmp" "$PSK_FILE"
fi
chmod 600 "$PSK_FILE"

mkdir -p "$FRAGMENT_DIR"
printf '%s\n' "$fragment" > "$FRAGMENT.tmp"
chmod 644 "$FRAGMENT.tmp"
mv "$FRAGMENT.tmp" "$FRAGMENT"

# The keyfile is built in a private temp file in the target directory, never with the passphrase on an argv.
mkdir -p "$KEYFILE_DIR"
tmpkey="$(mktemp "$KEYFILE_DIR/.$CON.XXXXXX")"
trap 'rm -f "$tmpkey"' EXIT
"${ADD_ARGS[@]}" > "$tmpkey"
python3 - "$tmpkey" "$PSK_FILE" <<'PY'
import sys
keyfile, pskfile = sys.argv[1:3]
psk = open(pskfile, encoding="utf-8").read().strip()
lines = open(keyfile, encoding="utf-8").read().splitlines()
out, done = [], False
for line in lines:
    out.append(line)
    if line == "[wifi-security]" and not done:
        out.append("psk=" + psk)
        done = True
if not done:
    sys.exit("setup-nm-hotspot: no [wifi-security] section in the generated keyfile")
open(keyfile, "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
chmod 600 "$tmpkey"
mv "$tmpkey" "$KEYFILE"
trap - EXIT
nmcli connection reload
nmcli connection up "$CON" >/dev/null
echo "hotspot $SSID is up; passphrase is in $PSK_FILE"
