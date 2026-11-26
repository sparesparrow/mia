#!/usr/bin/env bash
# Create the MQTT broker users for the secure stack (ADR-0026): one per role in the ACL file.
#
#   scripts/mqtt-users.sh            create every role that does not have a password yet
#   scripts/mqtt-users.sh ROLE...    create (or, with --rotate, replace) only these roles
#   scripts/mqtt-users.sh --rotate   give every role a new password
#
# Writes services/mosquitto/passwords/credentials (hashed; mounted by docker-compose.secure.yml)
# and one services/mosquitto/passwords/<role>.secret per role (the plain password, mode 600) for
# configuring that client. Never prints a password. MQTT_PASSWORDS_DIR and MQTT_ACL override the
# locations. Uses mosquitto_passwd, or the eclipse-mosquitto:2 image when it is not installed.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
acl="${MQTT_ACL:-$here/services/mosquitto/acl}"
dir="${MQTT_PASSWORDS_DIR:-$here/services/mosquitto/passwords}"
rotate=0
roles=()
for a in "$@"; do
  case "$a" in
    --rotate) rotate=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    -*) echo "unknown option: $a" >&2; exit 2 ;;
    *) roles+=("$a") ;;
  esac
done

mapfile -t known < <(awk '$1 == "user" {print $2}' "$acl")
[ ${#known[@]} -gt 0 ] || { echo "no 'user' lines in $acl" >&2; exit 1; }
[ ${#roles[@]} -gt 0 ] || roles=("${known[@]}")
for r in "${roles[@]}"; do
  printf '%s\n' "${known[@]}" | grep -qxF "$r" || { echo "$r is not a role in $acl" >&2; exit 2; }
done

umask 077
mkdir -p "$dir"
creds="$dir/credentials"
touch "$creds"

hash_file() {  # hash a plain "user:password" file in place
  if command -v mosquitto_passwd >/dev/null 2>&1; then
    mosquitto_passwd -U "$1"
  else
    docker run --rm -v "$(dirname "$1"):/p" eclipse-mosquitto:2 mosquitto_passwd -U "/p/$(basename "$1")"
  fi
}

new="$(mktemp "$dir/.new.XXXXXX")"
trap 'rm -f "$new" "$new.keep"' EXIT
made=()
for r in "${roles[@]}"; do
  if grep -q "^$r:" "$creds" && [ "$rotate" = 0 ]; then
    echo "kept    $r (already has a password; --rotate replaces it)"
    continue
  fi
  pw="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  printf '%s:%s\n' "$r" "$pw" >> "$new"
  printf '%s' "$pw" > "$dir/$r.secret"
  made+=("$r")
done

if [ ${#made[@]} -gt 0 ]; then
  hash_file "$new"
  grep -v -E "^($(IFS='|'; echo "${made[*]}")):" "$creds" > "$new.keep" || true
  cat "$new.keep" "$new" > "$creds"
  for r in "${made[@]}"; do echo "created $r (password in $dir/$r.secret)"; done
  echo "Restart the broker to load them: docker compose -f docker-compose.yml -f docker-compose.secure.yml restart mqtt-broker"
fi
