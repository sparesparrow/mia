# 0023. The phone updates the Pi: a verified package streamed over SSH

- Status: Proposed
- Date: 2026-11-20
- Requirements: REQ-UPD-001, REQ-UPD-002, REQ-UPD-003, REQ-UPD-004, REQ-UPD-005, REQ-UPD-006, REQ-UPD-007

## Context
The Pi sits in the car with no internet of its own. The phone has one (mobile data) and reaches the Pi over the
car's Wi-Fi, a LAN or a USB tether. Updating the Pi today means a shell on it, a checkout of the repository
and `deploy-production-rpi.sh`. `/opt/mia` is a git checkout on the Pi, so an update cannot simply be unpacked over it.
The user also wants to change a few settings from the phone and have them reach the Pi with the new code.

Two risks shape the design: a stolen or compromised phone key must not become a root shell on the Pi, and a
package built against other FlatBuffers schemas than the app speaks would break the wire between them (ADR-0004).

Scope: **updating an already-installed Pi**. A fresh Pi is a one-time bootstrap by hand
(`docs/install/pi-gateway.md`, then `infra/deploy/rpi/install-update-access.sh`).

## Decision
- **The phone builds a `.miapkg` and streams it on the standard input of one SSH command.** It is an
  uncompressed tar with four members: the release backend tarball `mia-rpi-backend-<version>.tar.gz`, that
  tag's `SHA256SUMS`, `config.yaml`, and `manifest.json` `{version, package, package_sha256, schema_hash}`.
  The release tarball carries `tools/scripts/deploy-raspberry-pi.sh` and `bin/mia-apply-update` (REQ-UPD-006), so
  the script that runs is the one the checksum covers, never a bare script from the phone.
- **`schema_hash`** is the SHA-256 over `schemas/*.fbs`: for each file name in sorted order,
  `name\n<sha256 of the content>\n`. The phone computes it from the schemas it was built with
  (`SchemaHash.kt`, value set by Gradle into `BuildConfig`) and refuses to push a backend whose hash differs.
  The Pi recomputes it from the bundle and refuses a manifest that disagrees (REQ-UPD-002).
- **`bin/mia-apply-update`** (Python standard library only) is the only thing the phone's key can run:
  1. stage the package under `/var/lib/mia/update/staging` (size cap, four named members only);
  2. check the bundle against `SHA256SUMS` and the manifest, and the schema hash;
  3. parse `config.yaml` with a strict YAML subset and validate it against
     `schemas/json/mia-user-config.schema.json` (REQ-UPD-003);
  4. unpack the bundle member by member (regular files and directories, nothing absolute, `..` or linked),
     check that the Python requirements are unchanged (the install runs `--skip-packages`, no apt or pip);
  5. run the bundle's `tools/scripts/deploy-raspberry-pi.sh --skip-packages` as an argument list, never through a shell;
  6. write the config as JSON to `/etc/mia/config.d/50-phone.json`, restart the core units, keep the previous
     package in `previous/`.
  Nothing on the Pi changes before step 5, and a failing step 5 leaves the config and `current/` as they were.
  The last stdout line is machine readable: `{"ok", "step", "version", "error"}`.
- **Rollback** is `sudo /opt/mia/bin/mia-apply-update --rollback`, run by an administrator on the Pi (the forced
  command cannot pass arguments): it re-verifies the previous package and applies it with its own config.
- **Config is data.** YAML on the phone, validated on both ends against one JSON Schema, stored as JSON, and
  read by services as data. It is never `source`d, executed or put into a command line. The strict YAML subset
  (no tags, anchors, flow style or comments after values) removes the parser as an attack surface and the
  dependency on PyYAML. No Pi service reads `/etc/mia/config.d` yet; wiring each setting is separate work.
- **Ownership.** The update owns `/opt/mia` code and `/etc/mia/config.d/50-phone.json`. Pi-owned state under
  `$MIA_STATE_DIR` (`voice_settings.json`, ADR-0019) is never read or written by it (REQ-UPD-005).
- **Transport and access (REQ-UPD-004).** SSH user `mia-update` with a locked password. sshd runs a forced
  command through the user's shell with `-c`, so a `nologin` shell would refuse it; the shell is `/bin/sh` and
  the keys are what restrict it: each entry is
  `command="sudo /opt/mia/bin/mia-apply-update",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding`,
  and sshd's `Match User mia-update` block repeats the bans. `/etc/sudoers.d/mia-update` allows
  `mia-update` exactly `/opt/mia/bin/mia-apply-update ""` (the empty argument list forbids arguments). sudo
  resets the environment, so the SSH user cannot set the script's `MIA_*` overrides. The tool is installed
  root-owned, mode 755. sshd reads the key list through `AuthorizedKeysCommand /bin/cat /etc/mia/update_authorized_keys`
  as the API's service user, because `StrictModes` would reject a key file the API can write inside the
  user's home.
- **Pairing.** The phone makes its own key pair and sends the public key to `POST /admin/update/pair` with an
  `admin` API key (`require_scope("admin")`). Only a bare ed25519, ECDSA or RSA key is accepted, at most eight
  phones, `DELETE /admin/update/pair/{label}` revokes. The phone pairs once, over the API it already uses.
- **Phone key storage.** minSdk is 22. The key is an EC P-256 pair (`ecdsa-sha2-nistp256`) made with the platform's `KeyPairGenerator` and kept
  encrypted in the app's no-backup storage; on API 23 and later the encryption key is an Android Keystore AES
  key, on API 22 a random key held in app-private no-backup files (software-held: root or a debugger
  on the phone can read it). The Keystore cannot hold the SSH private key itself in a form sshj can use. Either
  way the key can only run the update command, and the user revokes it from the Pi.
- **SSH library.** sshj (with its BouncyCastle) runs on API 22 and gives `exec` with a streamed standard input.
  Its effect on the APK size was **not measured**: Gradle could not run where this was written.
- **Version coupling.** The phone downloads the tarball and `SHA256SUMS` of the release tag it offers, through
  OkHttp, and verifies one against the other before it signs anything into a manifest. A release that
  predates this change has no deploy script or updater and is refused.

## Consequences
- An update is one command from the phone, and a failure at any check leaves the Pi as it was.
- The phone refuses a backend that speaks other schemas; a schema change needs a new app and a new backend together.
- The update cannot install new Python packages or system packages. A release that changes
  `apps/rpi-backend/py-api/requirements.txt` makes the update stop at step 4 and ask for the full install once.
- The deploy script copies code into `/opt/mia`; where it is a git checkout, `git status` there shows changes.
- Trust rests on the release checksum file that the phone downloads from the same place as the tarball, which
  catches damage but not a compromised release. Signing the release is open work.
- A phone key that leaks can run the update command, with a package that passes all checks above and nothing else.
- Not proven: sshd, sudo and the units on a real Pi; the Android code has not been compiled.

## Sources
- `bin/mia-apply-update`, `tools/scripts/deploy-raspberry-pi.sh`, `.github/workflows/release.yml`
- `apps/rpi-backend/py-api/api/routers/update_pairing.py`, `infra/deploy/rpi/install-update-access.sh`
- `schemas/json/mia-user-config.schema.json`, `apps/android/app/src/main/java/cz/mia/app/core/update/`
- `tests/unit/tools/test_mia_apply_update.py`, `tests/unit/rpi_backend/test_update_pairing.py`
