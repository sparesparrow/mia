---
description: "Use when working on native C++ code, Conan and CMake builds, hardware-server binaries, or cross-platform native integrations under apps/rpi-backend/cpp-audio, apps/rpi-backend/cpp-mcp-bridge, infra/conan, or conan-recipes."
name: "C++ Platform Guidance"
applyTo:
  - "apps/rpi-backend/cpp-audio/**"
  - "apps/rpi-backend/cpp-mcp-bridge/**"
  - "conan-recipes/**"
  - "infra/conan/**"
  - "tools/scripts/build-hardware-server*.sh"
  - "tools/scripts/build-raspberry-pi.sh"
---
# C++ Platform Guidance

- `apps/rpi-backend/cpp-audio/` is the native runtime surface CI builds. The old `platforms/cpp/` tree is gone; its generated headers now live in `schemas/generated/cpp/`.
- Prefer existing build entry points over ad hoc compiler invocations (the ARM64 Conan recipe is broken and tracked in #125):
  - `cmake -S apps/rpi-backend/cpp-audio -B build/cpp -DWITH_HARDWARE=OFF && cmake --build build/cpp`
  - `bash tools/scripts/build-hardware-server-rpi.sh --clean` for the minimal Raspberry Pi GPIO server path
- Preserve `WITH_HARDWARE` and minimal-build behavior. Host builds should stay possible without forcing `libgpiod`, `mosquitto`, or Raspberry Pi-only assumptions unless the task is explicitly hardware-only.
- Do not quietly rename or replace expected outputs such as `hardware-server`, `voice-server`, or the core libraries. Shell scripts, Python bridges, and deployment assets already assume those names.
- If you change the TCP or JSON interface of the hardware server, audit the paired Python clients under `orchestration/mcp/modules/hardware-bridge/` and any wrapper scripts under `tools/scripts/`.
- Generated FlatBuffers headers are not hand-authored C++ sources. Regenerate them from the `.fbs` source instead of patching generated headers directly.
- Prefer smoke validation over compile-only when touching entry points, CLI flags, or daemon startup behavior.
- Useful validation:
  - `cmake -S apps/rpi-backend/cpp-audio -B build/cpp -DWITH_HARDWARE=OFF && cmake --build build/cpp`
  - `bash tools/scripts/build-hardware-server-rpi.sh`
- Related docs: [docs/ARM64_BUILD_REQUIREMENTS.md](../../docs/ARM64_BUILD_REQUIREMENTS.md), [docs/conan-setup.md](../../docs/conan-setup.md), [spec/architecture/README.md](../../spec/architecture/README.md), and [../copilot-instructions.md](../copilot-instructions.md).