# MIA: Active Backlog

Lean architecture remains the baseline: ZeroMQ + FlatBuffers + FastAPI, with Raspberry Pi as the primary runtime edge and Android, web, and orchestration layers consuming normalized runtime surfaces.

Last reviewed: 2026-04-08

## Review Outcome

This file was previously trying to do too many jobs at once: historical milestone tracking, speculative roadmap, platform-specific implementation notes, and a live execution backlog. That made it unreliable.

Recommendations applied in this revision:

- Keep the root TODO focused on current cross-repo priorities.
- Keep detailed platform-specific plans in the owning surface, not duplicated here.
- Only mark work complete after code and validation have landed.
- Keep speculative or optional work separate from the active backlog.
- Treat historical summaries as documentation, not as acceptance evidence.

## Backlog Rules

- Use this file for repo-wide priorities and integration work.
- Use [apps/android/TODO.md](apps/android/TODO.md) for detailed Android implementation work.
- Use [docs/automotive/raspberry-pi-audi-integration.md](docs/automotive/raspberry-pi-audi-integration.md) for Audi-specific runtime notes and validation detail.
- Keep generated artifacts, site output, and vendor-specific experiments out of the root backlog unless they block delivery.
- If a task is complete but not validated, leave it unchecked and note the missing validation.

## Current Repo Snapshot

- Runtime apps live under `apps/`
- Orchestration and MCP modules live under `orchestration/`
- Deployment assets live under `infra/`
- Shared contracts live under `schemas/`, `protos/`, and generated bindings under `Mia/`
- Android is already a Kotlin/Jetpack Compose app under `apps/android/`
- Audi/VAG support is currently a read-only scaffold and not yet a validated production path

## Immediate Issue Seeds

### ISSUE P0-ARM64-1: Fix ARM64 Conan Host Setup

- Goal: make Raspberry Pi ARM64 builds stop inheriting x86_64-only flags and toolchain assumptions.
- Done when:
	- ARM64 host profile no longer emits `-m64`
	- `conan create . --build=missing` succeeds on the target Pi environment
	- the confirmed build recipe is documented

### ISSUE P0-ANDROID-1: Restore Android Debug Build

- Goal: restore a repeatable local and CI `assembleDebug` path for `apps/android`.
- Done when:
	- `cd apps/android && ./gradlew assembleDebug` succeeds
	- required JDK, SDK, and Gradle versions are documented
	- CI workflow inputs match the actual Gradle project

### ISSUE P0-OPS-1: Add Core Pi Smoke Test

- Goal: prove the deployment order and health path for the Raspberry Pi stack.
- Done when:
	- broker, API, and transport workers can be started in the intended order
	- one smoke test verifies startup through HTTP `/status`
	- the smoke test is documented and runnable outside a full production deploy

### ~~ISSUE P1-CONTRACT-1: Normalize Vehicle Telemetry Payload~~ (contract and fixtures landed)

- Goal: define one stable vehicle telemetry shape across producers and consumers.
- Done when:
	- [x] transport producers emit the normalized payload (serial bridge wired)
	- [x] FastAPI, WebSocket, Android, and orchestration consumers use the same field set
	- [x] replay fixtures cover nominal and degraded telemetry cases

### ~~ISSUE P1-AUDI-1: Add Adapter Capability Reporting~~ (landed)

- Goal: distinguish generic PID-only adapters from UDS-capable adapters before deeper Audi work.
- Done when:
	- [x] transport capability is reported in runtime status
	- [x] Audi/VAG logic checks capability before enabling UDS work
	- [x] degraded behavior is documented for generic-only adapters

## Priority 0: Stabilize Build and Deployment

### P0.1 ARM64 C++ and Conan

- [ ] Update Conan host profiles so ARM64 builds do not inherit x86_64-only flags such as `-m64`
- [ ] Fix Conan/CMake dependency discovery issues on Raspberry Pi builds, including `jsoncpp`
- [ ] Resolve `libgpiod` API compatibility for the target Raspberry Pi distro
- [ ] Verify `conan create . --build=missing` succeeds on the supported ARM64 target
- [ ] Verify `cd platforms/cpp && cmake -B build && cmake --build build` succeeds on the supported ARM64 target
- [ ] Document one confirmed ARM64 build recipe in [docs/ARM64_BUILD_REQUIREMENTS.md](docs/ARM64_BUILD_REQUIREMENTS.md) or [docs/conan-setup.md](docs/conan-setup.md)

### P0.2 Android Build Health

- [x] Restore a successful `cd apps/android && ./gradlew assembleDebug`
- [ ] Align Android CI workflow inputs, outputs, and environment assumptions with the current Gradle project
- [x] Capture the minimum supported JDK, Android SDK, and toolchain versions for contributors and CI

### P0.3 Deployment Wiring

- [x] Validate Compose files under `infra/docker/` with `docker compose ... config`
- [x] Validate systemd startup ordering for `zmq-broker`, `mia-api`, `mia-serial-bridge`, `mia-obd-worker`, and related workers
- [x] Add or refresh one smoke-test path that verifies the core Pi stack from broker startup to HTTP `/status`

## Priority 1: Lock Runtime Contracts

### P1.1 Normalized Vehicle Telemetry

- [x] Define one normalized vehicle telemetry payload shape for producers and consumers
- [x] Keep FastAPI, WebSocket, Android, and orchestration clients protocol-agnostic
- [x] Add replay fixtures for generic OBD telemetry and transport edge cases

### P1.2 Schema Discipline

- [ ] Regenerate `Mia/` whenever `schemas/` changes instead of hand-editing generated bindings
- [x] Add contract checks for consumers affected by automotive telemetry changes
- [ ] Keep schema changes and runtime protocol changes coordinated, not split across unrelated commits

### P1.3 Status and Observability Surfaces

- [x] Extend status and WebSocket payloads with source freshness, adapter type, and whether UDS is disabled or active
- [x] Add structured observability for broker, transport, and bridge health
- [x] Keep `/status`, `/ws`, and client-side assumptions aligned when telemetry fields evolve

## Priority 1: Audi/VAG Read-Only Pilot

### Guardrails

- [x] Keep coding, adaptation, security access, session escalation, and write operations out of scope
- [x] Keep Audi-specific protocol logic on the Raspberry Pi and orchestration layer rather than in Android or web clients

### Landed

- [x] Add a read-only `vag-audi-bridge` scaffold with safe defaults
- [x] Wire Audi-specific read-only intents into `automotive-mcp-bridge`
- [x] Add focused tests for the standalone bridge and orchestration integration path
- [x] Fix fallback loader registration, JSON-safe status serialization, and explicit `aiohttp` startup guard in `automotive-mcp-bridge`
- [x] Add coarse adapter capability reporting and gate read-only UDS behind transport capability class
- [x] Define normalized telemetry payload contract (`apps/rpi-backend/shared/telemetry/normalized_payload.py`)
- [x] Add replay fixtures for generic PID and UDS-capable transport scenarios
- [x] Wire serial bridge adapter metadata into transport telemetry

### Next Steps

- [ ] Choose one known-good adapter for the first Raspberry Pi trial and document why it was selected
- [ ] Decide the primary Pi transport path for Audi work: `mia-serial-bridge`, `mia-obd-worker`, or a dedicated transport agent
- [x] Add transport capability reporting so the Pi can distinguish `generic_pid_only` from `uds_read_only`
- [x] Verify end-to-end generic telemetry flow into the ZeroMQ telemetry path on port `5556` and then into the Audi bridge
- [ ] Validate VIN reading via DID `F190` on one Audi A3 8V MQB target
- [ ] Validate DTC summary reads via UDS service `0x19`
- [ ] Add allowlisted `0x22` DID reads only after VIN and DTC reads are stable
- [ ] Keep cloud-backed Audi Connect style integrations as a separate optional data-source track

### Acceptance Gates Before Widening Scope

- [x] Bench validation with simulated transport payloads on a non-vehicle development machine
- [ ] Raspberry Pi bench validation with the chosen adapter and no write, session, or security traffic
- [ ] In-vehicle passive validation on one Audi A3 8V MQB
- [ ] Controlled VIN and DTC read-only validation with logs captured for review
- [ ] Expansion decision only after the A3 8V path is stable

## Priority 2: Android and Client Integration

- [x] Keep the root TODO at integration level only and move Android implementation detail to [apps/android/TODO.md](apps/android/TODO.md)
- [ ] Decide whether Android should consume normalized vehicle data only or also expose explicit read-only Audi diagnostics views
- [ ] Validate BLE, backend URL, offline, and reconnect flows against a real Pi-backed stack
- [ ] Define a practical device and Android-version validation matrix for CI and manual testing
- [ ] Align Android and web client expectations with the normalized telemetry plan

## Priority 2: Testing and QA

- [x] Establish a non-hardware regression suite that must pass in CI
- [ ] Define hardware-marked acceptance checks for Pi GPIO, serial bridge, OBD, and Android device scenarios
- [ ] Add targeted security scanning and secret hygiene for workflows and deployment assets
- [x] Add regression coverage for startup-order and runtime-contract drift

## Priority 3: Operations and Documentation

- [ ] Keep `/opt/mia` deployment, bundled Python bootstrap, and systemd assets aligned
- [x] Refresh docs that still describe obsolete repo structure or stale runtime assumptions
- [ ] Remove obsolete architecture and TODO documents only after confirming the replacement docs are current
- [ ] Make site and documentation rebuild steps explicit so generated output is updated deliberately, not accidentally

## Recently Landed and Verified

- [x] ZeroMQ broker, FastAPI, and WebSocket runtime foundation exist in the repo
- [x] Android app exists under `apps/android/`
- [x] Read-only Audi/VAG scaffold exists with focused tests
- [x] Kernun proxy MCP tooling landed via Conan recipe and Python client
- [x] CPython bootstrap tooling landed for Android-side tools

## Deferred and Optional Tracks

- [ ] Kubernetes and service-mesh deployment work
- [ ] ML and anomaly-detection features
- [ ] Matter, Zigbee, Z-Wave, and broader IoT ecosystem expansion
- [ ] Enterprise multi-user, rules-engine, and analytics work
- [ ] Cloud-backed Audi Connect style integrations

## Reference Documents

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [README.md](README.md)
- [apps/android/TODO.md](apps/android/TODO.md)
- [docs/automotive/raspberry-pi-audi-integration.md](docs/automotive/raspberry-pi-audi-integration.md)
- [docs/ARM64_BUILD_REQUIREMENTS.md](docs/ARM64_BUILD_REQUIREMENTS.md)
- [docs/conan-setup.md](docs/conan-setup.md)
- [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md)
- [docs/RASPBERRY_PI_SETUP.md](docs/RASPBERRY_PI_SETUP.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
