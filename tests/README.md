# MIA test suite

`tests/` is the third of the repository's three parts (see [`spec/README.md`](../spec/README.md)):
it holds the tests that check the production code against the requirements in
`spec/requirements/`, and the simulated environment those tests run against.

## Layout

```
tests/
  conftest.py            import paths for the production code; loaded for every test
  unit/<area>/           fast, isolated tests, grouped by the code root they cover
    rpi_backend/           apps/rpi-backend: FastAPI, hardware drivers, telemetry envelope, Cycle 1 replay
    orchestration/         orchestration/: MCP framework and modules, core orchestrator, voice, mia-agents
    schemas/               schemas/: FlatBuffers and JSON schema contracts
    infra/                 infra/: systemd unit and runtime contracts
    tools/                 tools/: build, bootstrap, deploy and device-detection scripts
    firmware/              apps/esp32, apps/arduino: source-level contracts (for example listen-only CAN)
  integration/           several components together: ZeroMQ broker, OBD simulator, orchestrator routing
  e2e/                   real hardware, phones or a running Pi; marked `hardware`, never run in CI
  fixtures/              recorded captures and payloads (for example cycle1_bench.jsonl)
  env/                   the simulated test environment: Pi simulation compose file, GPIO simulator,
                         driver simulator, Mosquitto config
```

Tests that must build with their own toolchain stay beside that build:

| Code | Tests | Run by |
|---|---|---|
| Android app | `apps/android/app/src/test` (JVM), `apps/android/app/src/androidTest` (device) | `android-test.yml`: `./gradlew testDebugUnitTest`, emulator scenarios via `.claude/skills/android-adb-test` |
| C++ audio core | `apps/rpi-backend/cpp-audio/core/tests` | not in CI yet |
| ESP32 firmware | build-time checks in `ci.yml` (`esp32-obd-build`, including the listen-only `nm` symbol check) | `ci.yml` |

## Running

```bash
pytest tests/ -m "not hardware"                  # what CI runs
pytest tests/unit/rpi_backend -v                 # one area
pytest tests/ -m "not hardware" --cov            # with coverage (.coveragerc sets what is measured)
pytest tests/e2e -m hardware                     # on a Pi with the hardware attached
```

## Markers

Registered in `pytest.ini`; unknown markers fail collection (`--strict-markers`).

| Marker | Meaning |
|---|---|
| `hardware` | needs physical hardware, a phone or a running Pi; deselected in CI |
| `integration` | exercises several components together |
| `slow` | long-running |
| `unit`, `automotive`, `android`, `meta_harness` | grouping only |

## Adding a test

1. Put it in `tests/unit/<area>/` for the code root it covers, `tests/integration/` if it needs
   several components running, or `tests/e2e/` (marked `hardware`) if it needs real devices.
2. Keep file names unique across the tree: pytest imports test files by base name.
3. Load production code the way the neighbouring tests do. `conftest.py` puts the main source
   roots on `sys.path`; hyphenated module directories are loaded with `importlib`.
4. Hardware-dependent code must run against its simulation fallback, never real devices, outside `e2e/`.
5. A test must assert something about production code. A test that only exercises a mock
   defined in the test file, or that cannot fail, is not a test.
