# For developers

*Pro vývojáře.* Where to start if you want to build, change or integrate with MIA.

MIA is a prototype. Requirements carry an evidence state (ADR-0010), and today nothing goes beyond CI and simulation. Check a requirement's state before you rely on it.

## Run it without a car

1. [Dev environment without a Raspberry Pi](../install/dev-docker.md): Docker stack with simulated hardware.
2. [Quick start](../getting-started/QUICK_START.md).
3. [OBD simulator automation](../OBD_SIMULATOR_AUTOMATION.md): the ELM327 digital twin used in CI.

## How MIA is specified

- [How MIA is specified](../spec/README.md): the requirements, code and tests model.
- [Decisions (ADRs)](../spec/decisions/README.md).
- [Architecture](../spec/architecture/README.md) and the [system overview](../spec/architecture/overview.md).
- [Evidence records](../spec/evidence/README.md).
- Requirement registry: [`spec/requirements/*.yaml`](https://github.com/sparesparrow/mia/tree/main/spec/requirements) on GitHub.

## Interfaces and APIs

- [API & contracts overview](../api/overview.md) and the [API reference](../api/mia-api-reference.md).
- [MQTT topics](../spec/interfaces/topics.md), [events](../spec/interfaces/events.md), [BLE GATT](../spec/interfaces/ble-gatt.md), [ZeroMQ message formats](../spec/interfaces/zeromq-message-formats.md).

## Builds and CI

- [CI/CD and development environment](../ci-cd-setup.md).
- [Conan setup](../conan-setup.md) and [ARM64 build requirements](../ARM64_BUILD_REQUIREMENTS.md).
- [Android device setup](../android-device-setup.md).

## Contributing

Open work lives in [GitHub issues](https://github.com/sparesparrow/mia/issues) with `backlog:*` and `area:*` labels. New behaviour needs a requirement in `spec/requirements/`, and every test names the requirements it checks. See `CLAUDE.md` and the pull request template in the repository.
