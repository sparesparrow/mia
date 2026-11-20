# 0025. Vehicle onboarding: a server-signed grant authorizes first contact and pairing

- Status: Proposed
- Date: 2026-11-20
- Requirements: REQ-ONB-001, REQ-ONB-002, REQ-ONB-003, REQ-ONB-004, REQ-ONB-005, REQ-ONB-006, REQ-ONB-007, REQ-ONB-008

## Context

ADR-0023 lets a phone update an already-installed Pi, but only after an administrator has paired the phone key by
hand with `bin/mia-update-pair` and bootstrapped the Pi. ADR-0024 defines a per-Pi identity key pair whose
fingerprint a future central service records against an account. The user wants the phone to find a new Pi, install
or update MIA on it, run first-time setup and leave phone and Pi paired, with billing handled by Stripe.

The radio link (Wi-Fi, Bluetooth, USB tether) proves nothing about who is on the other end. Trust has to come from the
auth server that knows the account, the Pi fingerprint and the plan. The auth server and the Stripe integration do
not exist yet (ADR-0024 records no enrollment service); they are a separate piece of work. This ADR fixes the client
contract so the phone and Pi sides can be built and tested against a fake server.

## Decision

### Scope (extends ADR-0023 and ADR-0024)
- **First contact is in scope.** ADR-0023's scope line ("updating an already-installed Pi; a fresh Pi is a one-time
  bootstrap by hand") is changed: the phone now also enrolls a Pi that has never met it. Ruling on what "bare Pi"
  means: the **factory image carries the MIA base install** (OS, `/opt/mia` baseline with its venv, the device host
  key, `mia-enroll` access, and the grant-signer public key in `allowed_signers`). `mia-apply-update` refuses a Pi
  with no install, so the phone enrolls and updates; it does not build a system from nothing.
- **Pairing authority is amended.** ADR-0023 says pairing is an administrator action. A verified server grant now also
  authorizes pairing, and only through `mia-enroll`. Root on the Pi using `mia-update-pair` directly remains
  available. The API still cannot authorize a key (REQ-UPD-004).

### Grant
- A grant is a UTF-8 JSON object (the exact bytes are signed; the Pi verifies those bytes before parsing):
  `{v, account_id, jti, device_fp, phone_fp, plan, entitlement_exp, iat, exp}`.
  - `v` is 1. `account_id` is the opaque MIA account ID of ADR-0024. `jti` is a unique grant ID.
  - `device_fp` is the Pi's identity-key fingerprint; `phone_fp` the phone's enrollment public-key fingerprint.
  - `plan` is the entitlement tier name; `entitlement_exp` and `exp`/`iat` are Unix seconds. `exp` is short
    (minutes); `entitlement_exp` is when the paid entitlement ends and is not the grant's validity.
  - Unknown claims are ignored; a missing claim is refused.
- **Signature.** SSH signature, ed25519, namespace `mia-grant`, produced by the server with `ssh-keygen -Y sign` and
  checked on the Pi with `ssh-keygen -Y verify -n mia-grant` against `allowed_signers` baked into the image. Offline:
  the Pi needs no network to verify (REQ-ONB-001). The signature travels as the armored `-----BEGIN SSH SIGNATURE-----`
  text. Signer-key rotation is a new image or an update that adds a line to `allowed_signers`; not solved here.
- **Fingerprint format (R2).** Every `*_fp` is the OpenSSH form `SHA256:<base64>` exactly as `ssh-keygen -lf` prints
  it. The `mia-update-pair` label is `phone-` plus the first 12 hex characters of the SHA-256 of the raw public-key
  blob, and must match `^[A-Za-z0-9._-]{1,32}$`.
- **Checks on the Pi, in order.** Signature valid; `iat <= now < exp` (plus a small skew allowance set in code);
  `device_fp` equals this Pi's own identity fingerprint; `phone_fp` equals the fingerprint of the key offered in the
  request; `jti` not seen before. Any failure refuses the request and changes no state (REQ-ONB-002, REQ-ONB-003).
  `jti` values (`^[A-Za-z0-9._:-]{1,128}$`, one per line) are persisted so a replay of a still-unexpired grant is refused. The
  `jti` is recorded before the key is paired (fail closed): a failed enrollment burns the grant and the phone requests a new one.

### Auth server HTTP contract (R3)
Three endpoints, which the phone client and the fake test server both follow:
- `POST /v1/grants`, `Authorization: Bearer <activation key>`, body `{device_fp, phone_public_key}` returns
  `200 {grant, signature}`, `401` (bad activation key) or `403` (device unknown to this account).
- `GET /v1/devices` (same Bearer) returns `{devices:[{fp, label}]}`. The phone compares the Pi's SSH host-key
  fingerprint with this list before it sends anything to the Pi.
- `POST /v1/checkout` (same Bearer) returns `{url}`: a hosted payment page opened in the browser.
The activation key is the per-user key shipped with the app; it is exchanged for grants and is never sent to the Pi.

### `mia-enroll` access (R5)
- sshd has one extra user, `mia-enroll`, configured only under `Match User mia-enroll`: an `AuthorizedKeysCommand`
  that emits `restrict,command="sudo /opt/mia/bin/mia-enroll" <offered key>` for any ed25519 or ECDSA key (`%t %k`).
  Authorization is the grant, not the SSH layer. The sudoers rule is an exact match for that one command.
- `mia-enroll` reads one JSON line on stdin `{grant, signature, phone_public_key}`, runs the checks above and
  registers only the key in `phone_public_key`, whose fingerprint must equal the grant's `phone_fp`, through the
  `mia-update-pair` logic. The result is one JSON line `{ok, step, error}` on stdout, as in `mia-apply-update`.
  After enrollment the phone uses its ordinary ADR-0023 key (`mia-update` user, forced `mia-apply-update`), so the
  phone keeps no general shell (REQ-ONB-004).
- The device API key is generated on the Pi with `secrets.token_urlsafe(32)` and appended to `/etc/mia/environment`
  unless a non-empty one is set (an empty `MIA_API_KEY=` counts as absent and a new line is appended; the later line
  wins in a systemd EnvironmentFile); existing lines are never rewritten. Secrets (API key, host keys) are never placed in phone-edited
  YAML, never sent by the phone, and never logged (REQ-ONB-005).
- The grant's `account_id`, `plan` and `entitlement_exp` are written as data to `/etc/mia/config.d/60-billing.json`.

### Host key must not regenerate
The server registered the Pi's host-key fingerprint, and the phone trusts the Pi by comparing it with
`GET /v1/devices`. The image therefore must not regenerate SSH host keys on first boot (no `ssh-keygen -A` step, no
first-boot unit that deletes them). A regenerated key makes the Pi look like an unknown device and enrollment stops
at `403`.

### Stripe boundary
Billing is server-side only. Stripe customer IDs, secrets and webhooks live on the auth server (ADR-0024). The phone
only opens the `url` from `/v1/checkout`. The Pi and the grant carry no Stripe identifier: the grant has `plan` and
`entitlement_exp` only. Stripe never touches the Pi.

### Phone MAC rule
The phone's MAC is stored only to give its DHCP lease a stable address. It is never authentication: Android
randomizes MACs per SSID and an attacker can copy one. The phone registry (`/var/lib/mia/phones.json`) is keyed by the
phone key fingerprint; when the MAC changes the reservation is updated for that fingerprint, and the old MAC is not
trusted (REQ-ONB-007).

### Revocation
Removing a phone is two steps: delete its entry from the phone registry and run `mia-update-pair remove <label>` so
the SSH key is gone from the `mia-update` user. Revoking an account server-side stops new grants but does not reach
a Pi that is offline; the registry plus `mia-update-pair remove` is the on-Pi mechanism (REQ-ONB-007).

### Network and wizard
- The Pi's hotspot is a NetworkManager shared connection, so NM's dnsmasq provides DHCP and DNS (REQ-ONB-006). The
  script refuses to run unless `--i-know-this-drops-wlan0` is given, because `wlan0` may be the Pi's uplink.
- The phone's wizard is a state machine (discover Pi, verify against `/v1/devices`, obtain grant, enroll, install or
  update, Bluetooth bond, Wi-Fi, done) that persists its step and resumes there after a cancelled system dialog,
  an unreachable server or a lost connection. It never installs without a verified grant, and it says before
  triggering Android 10+ dialogs that the user must approve them (REQ-ONB-008).

## Consequences

- The Pi's trust in the phone rests on one server-held signing key. Its compromise lets an attacker mint grants
  for any registered Pi whose host the attacker can reach; the baked-in public key makes rotation an update, not a
  server-side fix.
- `mia-enroll` is a second SSH entry point to the Pi, reachable by any ed25519 or ECDSA key. It is safe only because
  the command takes no arguments and refuses everything without a valid grant; its input handling must stay minimal
  and is the part to review.
- Replay protection needs durable `jti` state on the Pi; a reflashed Pi forgets it, but then `exp` still bounds the
  window.
- The Pi's clock must be roughly right to check `exp`. A Pi without an RTC and network may reject a fresh grant; the
  phone can supply the time to display a clear error but must not override the check.
- A bare Pi without internet takes the release package from the phone's download cache; the wizard says so.
- Offline Pi revocation is manual (see Revocation). Nothing here proves the real auth server or Stripe exist; every
  claim about them stays unverified until that service is built.

## Sources

- ADR-0023 (`spec/decisions/0023-phone-driven-software-update.md`), ADR-0024
  (`spec/decisions/0024-account-vehicle-and-pi-identity.md`)
- `bin/mia-update-pair`, `bin/mia-apply-update`, `infra/deploy/rpi/install-update-access.sh`
- `docs/superpowers/plans/2026-11-20-vehicle-onboarding.md`
