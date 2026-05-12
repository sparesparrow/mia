# MIA Dev Pipeline Backlog

> Last refreshed: 2026-05-11 — Phase 1 Task Creator scan

## URGENT

- [x] ~~**[FIX]** `sensors_i2c.py` hard-fails on `ImportError` for smbus2 instead of degrading to simulation~~ — DONE 2026-05-11
- [x] ~~**[FIX]** `serial_bridge.py` has no simulation/fallback mode~~ — DONE 2026-05-12

## HIGH

- [x] ~~**[TEST]** `arduino.py` needs simulation fallback for CI~~ — DONE 2026-05-12
- [ ] **[TEST]** `gpio.py` (messaging client variant) needs graceful degradation when hardware server is unavailable — source: simulation gap scan
- [ ] **[BUILD]** Android MCP bridge TODOs: DPF status, DPF regen, AdBlue, full diagnostics, DTC reading (5 stubs in MainActivity.kt) — source: TODO scan
- [ ] **[BUILD]** C++ audio worker stubs: whisper STT, piper TTS integration, model loading (3 TODOs in cpp-audio/) — source: TODO scan

## MEDIUM

- [ ] **[BUILD]** C++ voice FSM command execution callback not wired (`voice_control_fsm.cpp:54`) — source: TODO scan
- [ ] **[TEST]** Android instrumented test `DrivingServiceInstrumentedTest.kt` needs IdlingResource + assertions — source: TODO scan
- [ ] **[REFACTOR]** `hardware_manager.py` — add explicit fallback/simulation logging when sub-components fail to initialize — source: simulation gap scan
- [ ] **[DOC]** Schema generator `generate.py` lacks `--dry-run` flag for drift detection — source: pipeline scan

## LOW

- [ ] **[DOC]** `__init__.py` in hardware/ — add simulation/fallback documentation reference — source: simulation gap scan

## HOMEWORK

- [ ] **[DECIDE]** Provider routing for AI audio: Whisper native vs API, Piper vs ElevenLabs — options: local-only / hybrid / cloud-first, recommendation: hybrid
- [ ] **[DECIDE]** Schema evolution strategy for vehicle_telemetry.fbs — additive only vs versioned — recommendation: additive with deprecation markers

---

## Completed

_(none yet)_
