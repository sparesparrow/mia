---
description: "Use when working on native C++ code, Conan and CMake builds, hardware-server binaries, or cross-platform native integrations under apps/rpi-backend/cpp-audio, platforms/cpp, mcp-cpp-bridge, or conan-recipes."
name: "C++ Platform Guidance"
applyTo:
  - "apps/rpi-backend/cpp-audio/**"
  - "platforms/cpp/**"
  - "mcp-cpp-bridge/**"
  - "conan-recipes/**"
  - "infra/conan/**"
  - "scripts/build-hardware-server*.sh"
  - "scripts/build-raspberry-pi.sh"
---
# C++ Platform Guidance

- Treat `apps/rpi-backend/cpp-audio/` as the newer runtime-side native surface, but assume `platforms/cpp/` is still live. Several scripts, generation steps, and legacy build flows still point at `platforms/cpp`, so keep compatibility unless the task explicitly completes the migration.
- Prefer existing build entry points over ad hoc compiler invocations:
  - `conan create . --build=missing`
  - `cd platforms/cpp && cmake -B build && cmake --build build`
  - `bash scripts/build-hardware-server-rpi.sh --clean` for the minimal Raspberry Pi GPIO server path
- Preserve `WITH_HARDWARE` and minimal-build behavior. Host builds should stay possible without forcing `libgpiod`, `mosquitto`, or Raspberry Pi-only assumptions unless the task is explicitly hardware-only.
- Do not quietly rename or replace expected outputs such as `hardware-server`, `voice-server`, or the core libraries. Shell scripts, Python bridges, and deployment assets already assume those names.
- If you change the TCP or JSON interface of the hardware server, audit the paired Python clients under `orchestration/mcp/modules/hardware-bridge/` and any wrapper scripts under `scripts/`.
- Generated FlatBuffers headers are not hand-authored C++ sources. Regenerate them from the `.fbs` source instead of patching generated headers directly.
- Prefer smoke validation over compile-only when touching entry points, CLI flags, or daemon startup behavior.
- Useful validation:
  - `conan create . --build=missing`
  - `cd platforms/cpp && cmake -B build && cmake --build build`
  - `bash scripts/build-hardware-server-rpi.sh`
- Related docs: [docs/ARM64_BUILD_REQUIREMENTS.md](../../docs/ARM64_BUILD_REQUIREMENTS.md), [docs/conan-setup.md](../../docs/conan-setup.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and [../copilot-instructions.md](../copilot-instructions.md).