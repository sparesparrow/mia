# Install MIA on a car / Pair vehicle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The phone finds a Pi that shipped with a device key, gets a server-signed grant from the MIA auth server, installs/updates MIA on the Pi, runs first-time setup, and leaves phone and Pi paired (SSH key, Bluetooth bond, Wi-Fi, stored phone MAC, Pi hotspot with DHCP/DNS).

**Architecture:** Trust comes from the auth server, not from the radio link. The server knows each Pi's device-key fingerprint (ADR-0024) and gives the user's phone a short-lived **grant** (signed with an SSH ed25519 key) binding {account, Pi fingerprint, phone public-key fingerprint, plan, expiry}. The Pi verifies the grant offline with `ssh-keygen -Y verify` against a server public key baked into the image, then accepts the phone key through the existing `bin/mia-update-pair` path (ADR-0023 forced command). Billing is Stripe, server-side only: the Pi and phone see only the entitlement claim in the grant.

**Tech Stack:** Kotlin/Compose/Hilt (existing `core/update/`, `core/networking/`), Python 3 stdlib on the Pi (like `bin/mia-apply-update`), `ssh-keygen -Y`, NetworkManager `nmcli`, systemd, pytest, JUnit.

**Spec:** `spec/decisions/0025-vehicle-onboarding.md` (written in Task 1; extends 0023 and 0024). Requirements in `spec/requirements/onboarding.yaml`.

Branch: `fix/obd-scan-full-flow`. Step 0, before Task 1: `gh pr create --draft` for the existing one-commit branch; all tasks below land in that PR.

## Assumptions to confirm (the user's words were short)
- "SSH key preinstalled on the Pi, known to the auth server" = the Pi's **device identity key** (ADR-0024 key pair); sshd on the Pi exposes one forced-command user `mia-enroll` for first contact; its authorization is the grant, not the SSH layer.
- "Unique key provided with the Android app" = a per-user **activation key** the app exchanges at the auth server for a grant.
- **The auth server and Stripe integration do not exist** (ADR-0024: no enrollment service). They are a separate plan. This plan builds the client contract, a fake server for tests, and the Pi/phone sides. Anything needing the real server stays "unverified".

## Global Constraints
- Ruling R1: ADR-0023 says pairing is an administrator action; ADR-0025 must state that a verified server grant now also authorizes pairing, and only through `mia-enroll`.
- ADR-0023: config is data (YAML on phone → JSON on Pi), never executed, never interpolated into a command line; Pi-owned state (`voice_settings.json`) is never written by install/update.
- ADR-0023: phone key can run only `sudo /opt/mia/bin/mia-apply-update` (forced command); the phone never keeps a general shell.
- ADR-0024: account ID, billing (Stripe customer) ID, VIN and Pi identity are separate; no VIN in the hostname; local Whisper stays default; Stripe never touches the Pi.
- Secrets (API key, host keys) are generated on the Pi, never placed in phone-edited YAML, never logged.
- Phone MAC is stored for a DHCP reservation only, never as authentication (Android randomizes MACs per SSID).
- Android 10+: Wi-Fi suggestions and Bluetooth bonding need a user-approved system dialog; the UI must say so before triggering them.
- `android-adb-test.sh` matches the strings "OBD pairing", "OBD-II Connection", "Scan"; renames update it in the same commit.
- Pi `wlan0` is the uplink for the current live voice test: the hotspot script must refuse to run unless `--i-know-this-drops-wlan0` is given.
- Traceability: every new REQ has a test marked `@pytest.mark.req(...)` or the Android equivalent; `tools/ci/traceability.py` passes.

## Review Focus
- Expired or replayed grant (same `jti` used twice) → Pi refuses, state unchanged.
- Grant for a different Pi fingerprint or different phone key → refused.
- Auth server unreachable (phone offline or captive hotspot) → wizard shows a retry state, never installs unauthenticated.
- Bare Pi has no internet (phone hotspot only) → release package comes from the phone's download cache; wizard must say so.
- Phone MAC changes after pairing → reservation updated by key fingerprint, not by MAC lookup; old MAC not trusted.
- User cancels the Bluetooth or Wi-Fi system dialog mid-wizard → wizard resumes at that step, no half-registered phone on the Pi.

## File Structure
- `spec/decisions/0025-vehicle-onboarding.md`, `spec/requirements/onboarding.yaml` — decision + REQs.
- `schemas/json/mia-grant.schema.json` — grant claims (shared by Pi test and Android test fixtures).
- `bin/mia-enroll` — Pi: verify grant, register phone via `mia-update-pair` logic, write device config. Stdlib only.
- `bin/mia-phone-registry` — Pi: JSON store `/var/lib/mia/phones.json` {label, key fingerprint, last MAC, bond state}.
- `infra/deploy/rpi/setup-nm-hotspot.sh`, `infra/systemd/mia-bt-agent.service` — NM shared hotspot (DHCP+DNS), Bluetooth pairing agent.
- `apps/android/app/src/main/java/cz/mia/app/core/onboarding/` — `AuthServerClient.kt`, `PiDiscovery.kt`, `OnboardingState.kt`, `OnboardingViewModel.kt`, `KnownPiStore.kt`.
- `apps/android/app/src/main/java/cz/mia/app/ui/screens/vehicle/` — `InstallMiaScreen.kt`, `PairVehicleScreen.kt`; `OBDPairingScreen.kt` stays as the adapter step.
- `apps/rpi-backend/py-api/tests/unit/test_mia_enroll.py`, `.../test_phone_registry.py`; `apps/android/app/src/test/java/cz/mia/app/core/onboarding/*Test.kt`.

---

### Task 1: ADR-0025 and requirements
**Files:** Create `spec/decisions/0025-vehicle-onboarding.md`, `spec/requirements/onboarding.yaml`; Modify `spec/decisions/README.md`.
**Interfaces:** Produces REQ ids `REQ-ONB-001..008` used by later tasks: 001 grant verified offline; 002 grant bound to Pi fingerprint + phone key; 003 replay refused; 004 phone key limited to forced command; 005 secrets generated on Pi; 006 hotspot DHCP/DNS; 007 phone registry by key fingerprint; 008 wizard states and resume.
- [ ] Step 1: Write ADR (Status: Proposed) stating: bare-Pi/first-contact now in scope (changes 0023's scope line), grant format, trust model, Stripe boundary, MAC rule. Copy requirement fields from `spec/requirements/update.yaml`; mark each `planned`.
- [ ] Step 2: Run `python tools/ci/traceability.py` — Expected: PASS (planned REQs need no tests yet).
- [ ] Step 3: Commit `docs(adr): 0025 vehicle onboarding`.

### Task 2: Grant schema and `bin/mia-enroll`
**Files:** Create `schemas/json/mia-grant.schema.json`, `bin/mia-enroll`, `infra/deploy/rpi/install-enroll-access.sh` (mirrors `install-update-access.sh`: SSH user `mia-enroll`, forced command `sudo /opt/mia/bin/mia-enroll`, sudoers exact-match, sshd `Match User` block; `shellcheck` clean), test `apps/rpi-backend/py-api/tests/unit/test_mia_enroll.py`.
**Interfaces:** Produces `verify_grant(grant: bytes, signature: bytes, allowed_signers: Path, device_fp: str, phone_fp: str, now: int, seen_jti: set[str]) -> Claims` raising `GrantError(reason: str)`; `Claims` fields `account_id, jti, plan, entitlement_exp, exp, phone_fp, device_fp`. CLI reads `{grant, signature, phone_public_key}` as one JSON line on stdin and prints `{"ok","step","error"}` as its last line (same convention as `mia-apply-update`).
- [ ] Step 1: Write failing tests (with a throwaway key made by `ssh-keygen -t ed25519` in a tmp dir): `test_valid_grant_accepted`, `test_expired_grant_refused` (now > exp), `test_wrong_device_fingerprint_refused`, `test_wrong_phone_fingerprint_refused`, `test_replayed_jti_refused`, `test_bad_signature_refused`, `test_unknown_claim_ignored_but_missing_claim_refused`, each `@pytest.mark.req("REQ-ONB-00x")`.
- [ ] Step 2: Run `pytest apps/rpi-backend/py-api/tests/unit/test_mia_enroll.py -v` — Expected: FAIL (module missing).
- [ ] Step 3: Implement `verify_grant` using `subprocess.run(["ssh-keygen","-Y","verify",...], shell=False)` with namespace `mia-grant`; JSON parsed with `json`, claims validated against the schema's required list by hand (stdlib only). `jti` list persisted at `/var/lib/mia/enroll/seen_jti`.
- [ ] Step 4: Implement CLI path: on success call the pairing function of `bin/mia-update-pair` (import by path, label from `phone_fp[:12]`), generate the device API key with `secrets.token_urlsafe(32)` into `/etc/mia/environment` (mode 600, never printed), write `/etc/mia/config.d/60-billing.json` `{account_id, plan, entitlement_exp}`.
- [ ] Step 5: Run tests — Expected: PASS. Commit `feat(rpi): mia-enroll verifies server grant`.

### Task 3: Phone registry and network
**Files:** Modify `bin/mia-enroll` (call `registry.upsert` after a successful grant); Create `bin/mia-phone-registry`, `infra/deploy/rpi/setup-nm-hotspot.sh`, `infra/systemd/mia-bt-agent.service`, test `.../tests/unit/test_phone_registry.py`.
**Interfaces:** Consumes `Claims.phone_fp`. Produces `registry.upsert(phone_fp: str, mac: str, bonded: bool) -> None`, `registry.lookup_by_fp(phone_fp: str) -> Entry | None`; CLI `mia-phone-registry upsert|list|remove`.
- [ ] Step 1: Tests: `test_upsert_new_phone`, `test_mac_change_updates_same_entry` (same fp, new MAC → one entry), `test_unknown_mac_not_trusted` (lookup by MAC alone returns none), file mode 600, atomic write.
- [ ] Step 2: Run — Expected FAIL. Step 3: Implement (JSON file under `/var/lib/mia/`, `fcntl.flock`, atomic rename). Step 4: Run — PASS.
- [ ] Step 5: `setup-nm-hotspot.sh`: `nmcli connection add type wifi … 802-11-wireless.mode ap ipv4.method shared` (shared = NM-run DHCP+DNS), SSID `MIA-Car`, PSK generated on the Pi and written to `/etc/mia/hotspot.psk` (mode 600); reads `phones.json` to add a `dnsmasq` reservation fragment in `/etc/NetworkManager/dnsmasq-shared.d/`; refuses without `--i-know-this-drops-wlan0`; `--disable` reverts. Verify: `shellcheck infra/deploy/rpi/setup-nm-hotspot.sh` clean; on a test Pi `nmcli -g GENERAL.STATE con show MIA-Car` = `activated`.
- [ ] Step 6: `mia-bt-agent.service`: `bluetoothctl` NoInputNoOutput agent running as the `mia` user, discoverable only while `/run/mia/pairing-window` exists (created by `mia-enroll`, removed after 120 s). Commit.

### Task 4: Android auth client with fake server
**Files:** Create `core/onboarding/AuthServerClient.kt`, test `core/onboarding/AuthServerClientTest.kt` (MockWebServer).
**Interfaces:** Produces `class AuthServerClient(baseUrl: String, client: OkHttpClient)` with `fun requestGrant(activationKey: String, devicePublicFp: String, phonePublicKeyLine: String): Result<Grant>`; `data class Grant(val json: String, val signature: String, val plan: String, val entitlementExp: Long)`; `fun checkoutUrl(activationKey: String): Result<String>` (Stripe Checkout URL the server returns; the app only opens it in the browser).
- [ ] Step 1: Tests: `grantIsReturnedForValidActivationKey`, `unauthorizedKeyGivesReadableError`, `serverDownGivesRetryableError` (never throws), `activationKeyNeverLogged` (capture log output).
- [ ] Step 2: Run `./gradlew :app:testDebugUnitTest --tests '*AuthServerClientTest'` — FAIL. Step 3: Implement; the activation key travels only in an `Authorization` header over HTTPS. Step 4: PASS. Commit.

### Task 5: Discovery of the Pi
**Files:** Create `core/onboarding/PiDiscovery.kt`, test `PiDiscoveryTest.kt`. Reuse `core/networking/MdnsDiscovery.kt`.
**Interfaces:** Produces `sealed interface Transport { Usb; Hotspot; MiaWifi; Bluetooth }`, `data class FoundPi(val host: String, val transport: Transport, val deviceFp: String?)`, `suspend fun PiDiscovery.find(timeoutMs: Long): List<FoundPi>`. `deviceFp` comes from the Pi's SSH host-key fingerprint, compared with the fingerprint the auth server returned for this account (no TOFU).
- [ ] Step 1: Tests with a fake `MdnsDiscovery`: `findsPiByMdnsOnHotspot`, `rejectsPiWhoseFingerprintDiffersFromServer`, `returnsEmptyListOnTimeout`. Steps 2–4: run (FAIL), implement, run (PASS). Commit.

### Task 6: Wizard state machine and screens
**Files:** Create `OnboardingState.kt`, `OnboardingViewModel.kt`, `KnownPiStore.kt`, `ui/screens/vehicle/InstallMiaScreen.kt`, `PairVehicleScreen.kt`; Modify `MainActivity.kt:141`, `ui/screens/MoreScreen.kt` (entry "OBD pairing" → "Install MIA on a car"), `OBDPairingScreen.kt` (becomes the "Pair OBD adapter" step, title and the three test strings unchanged).
**Interfaces:** Consumes Tasks 4–5 and `core/update/{SshKeyStore,ReleaseDownloader,PackageBuilder,SshUploader,UpdatePairing}`. Produces `sealed interface OnboardingState { Welcome; EnterActivationKey; FindingPi; Authorizing; Installing(sent: Int, total: Int); FirstSetup; PairingPhone; PairAdapter; Done; Failed(step: String, retryable: Boolean) }` and `class OnboardingViewModel { val state: StateFlow<OnboardingState>; fun submitActivationKey(key: String); fun resume() }`; `KnownPiStore.save(fp: String, host: String)` / `known(): List<KnownPi>`.
- [ ] Step 1: Tests: `happyPathReachesDone`, `authServerDownStaysRetryableNeverInstalls`, `cancelledSystemDialogResumesSameStep`, `forgetsNothingOnFailure` (a failed step leaves `KnownPiStore` unchanged), `firstSetupFormProducesSchemaValidYaml` (against `mia-user-config.schema.json`).
- [ ] Step 2: Run — FAIL. Step 3: Implement the ViewModel as a pure state machine over injected interfaces (auth client, discovery, uploader), screens only render state; first-setup form builds `UpdateConfig` (existing) — no secrets in it. Step 4: Run — PASS. Step 5: `./gradlew :app:assembleDebug` succeeds. Commit.

### Task 7: ADB test script
**Files:** Modify `.claude/skills/android-adb-test/scripts/android-adb-test.sh`.
- [ ] Step 1: Add `scenario_install_wizard` (opens "Install MIA on a car", asserts the activation-key field is visible, takes a screenshot) and update `scenario_full_flow` to chain it before `scenario_ble_scan`. Keep `scenario_ble_scan`/`scenario_obd_pairing` working through the wizard's adapter step.
- [ ] Step 2: Run on the g54: `bash …/android-adb-test.sh full-flow` — Expected: exit 0, screenshots written. (Needs the phone; otherwise "unverified".)
- [ ] Step 3: Commit.

### Task 8: Evaluation and PR hygiene
- [ ] After each of Tasks 2, 3, 6: a fresh `evaluator` scores against that task's REQs with quoted evidence (command output); BLOCKED/FAIL stops the next task.
- [ ] Flip REQ status from `planned` only to what the tests prove (`implemented_and_ci_tested`); the real-server and bare-Pi paths stay `planned`.
- [ ] Draft PR → ready only after CI green and the owner's yes.

## Verification
- CI: Android Tests, `traceability.py`, schema validation, pytest unit.
- Pi: `mia-enroll` refuses expired/replayed/mis-bound grants; paired phone key can only run the forced command (`ssh … id` refused); hotspot hands out a lease and resolves `mia.local`.
- End to end on a **bare** Pi (spare SD/second Pi, or the current Pi after the voice test) with the **real** auth server and Stripe: **unverified until both exist**.

## Self-review
- Spec coverage: grant trust model (T1–2), Stripe boundary (T1, T4), phone registry/MAC rule (T3), DHCP/DNS hotspot (T3), BT bond (T3, T6), wizard + adapter step (T6), test script (T7). Gap: auth server and Stripe backend (separate plan).
- Types: `Claims.phone_fp`/`device_fp` (T2) = `phone_fp` in registry (T3) = `devicePublicFp` in client (T4) = `FoundPi.deviceFp` (T5).
- Parked, unchanged: live voice end-to-end test (waits for "ready"), `rpi-dev` HOLD, follow-up PR items (av pin, installer `claude update`, Piper path, `deploy.sh` verify order, `test-script.md` line 32).
