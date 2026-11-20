#!/bin/bash
# One-time setup on the Pi for phone-driven software updates (ADR-0023, REQ-UPD-004). Run as root:
#
#   sudo bash infra/deploy/rpi/install-update-access.sh
#
# It creates:
# - the user `mia-update`: locked password, no home login. sshd runs a forced command through the user's shell
#   with `-c`, so the shell is /bin/sh (a nologin shell would refuse it); the key entries allow nothing but
#   `sudo /opt/mia/bin/mia-apply-update`, with no pty, forwarding or agent;
# - /etc/sudoers.d/mia-update: that user may run that one file as root, with no arguments (the empty "" in the
#   rule), checked with visudo -cf before it is put in place;
# - /etc/mia/update_authorized_keys, owned by the API's service user, written by POST /admin/update/pair;
# - /etc/ssh/sshd_config.d/mia-update.conf: sshd reads that file for this user through AuthorizedKeysCommand,
#   so no file in the user's home can add a key.
#
# The MIA_* variables let tests/unit/infra/test_update_access.py run it in a temporary directory.
set -euo pipefail

UPDATE_USER="${MIA_UPDATE_USER:-mia-update}"
SERVICE_USER="${MIA_USER:-mia}"
SUDOERS_FILE="${MIA_SUDOERS_FILE:-/etc/sudoers.d/mia-update}"
SSHD_DROPIN="${MIA_SSHD_DROPIN:-/etc/ssh/sshd_config.d/mia-update.conf}"
KEYS_FILE="${MIA_AUTHORIZED_KEYS:-/etc/mia/update_authorized_keys}"
TOOL="${MIA_UPDATE_TOOL:-/opt/mia/bin/mia-apply-update}"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

if ! id "$UPDATE_USER" >/dev/null 2>&1; then
    useradd -r -m -s /bin/sh "$UPDATE_USER"
fi
passwd -l "$UPDATE_USER" >/dev/null 2>&1 || true

printf '%s ALL=(root) NOPASSWD: %s ""\n' "$UPDATE_USER" "$TOOL" > "$work/sudoers"
visudo -cf "$work/sudoers"
install -m 440 "$work/sudoers" "$SUDOERS_FILE"

mkdir -p "$(dirname "$KEYS_FILE")"
touch "$KEYS_FILE"
chown "$SERVICE_USER:$SERVICE_USER" "$KEYS_FILE"
chmod 600 "$KEYS_FILE"

cat > "$work/sshd.conf" <<CONF
# MIA phone updates (ADR-0023): keys come from the list the API manages; the only thing they can run is the
# forced command written into each entry.
Match User $UPDATE_USER
    AuthorizedKeysFile none
    AuthorizedKeysCommand /bin/cat $KEYS_FILE
    AuthorizedKeysCommandUser $SERVICE_USER
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PermitTTY no
    AllowTcpForwarding no
    X11Forwarding no
    AllowAgentForwarding no
CONF
mkdir -p "$(dirname "$SSHD_DROPIN")"
install -m 644 "$work/sshd.conf" "$SSHD_DROPIN"
if command -v sshd >/dev/null 2>&1; then sshd -t; fi

echo "Done. Reload sshd (systemctl reload ssh), then pair the phone from the app: Settings > Software update."
