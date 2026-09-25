# For testers

*Pro testery.* How to run MIA's checks, and how a result becomes evidence.

## What counts as evidence

Every requirement in [`spec/requirements/`](https://github.com/sparesparrow/mia/tree/main/spec/requirements) has an evidence state (ADR-0010). CI can support states up to `simulation_tested`. Bench, hardware and vehicle states need a record under `spec/evidence/<REQ-ID>/`. See [evidence records](../spec/evidence/README.md) for the format.

The most useful contribution right now is a bench or in-vehicle record for a requirement that is only CI-tested.

## Automated tests

- Test layout and markers: [`tests/README.md`](https://github.com/sparesparrow/mia/blob/main/tests/README.md) on GitHub.
- Run everything that does not need hardware: `pytest tests/ -m "not hardware"`.
- [OBD simulator automation](../OBD_SIMULATOR_AUTOMATION.md): the ELM327 digital twin and CAN replay.
- [VM testing guide](../vm-testing-guide.md).

## Manual and device testing

- [Android device setup](../android-device-setup.md).
- [ANPR quick start](../ANPR_QUICK_START.md) and [ANPR implementation](../ANPR_IMPLEMENTATION.md).
- [Installer checklist](../install/installer-checklist.md) for bench and in-car setups.
- [Citroën testing checklist](../automotive/citroen-testing-checklist.md) (legacy vehicle).

## Reporting

File findings as [GitHub issues](https://github.com/sparesparrow/mia/issues). Name the requirement ID, the build or commit, and the hardware used.
