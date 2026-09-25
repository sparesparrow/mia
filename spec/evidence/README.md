# Evidence records

A requirement can claim `bench_tested`, `hardware_tested` or `vehicle_installed` only when a
record for it exists here, in `spec/evidence/<REQ-ID>/<YYYY-MM-DD>-<state>.md`. CI cannot
produce this evidence ([ADR-0010](../decisions/0010-evidence-based-requirement-status.md)).

No records exist yet: nothing in MIA has been validated on a bench, on target hardware or in
the vehicle.

## Record template

```markdown
# REQ-AUTO-012: bench_tested

- Date: YYYY-MM-DD
- By: name
- State claimed: bench_tested | hardware_tested | vehicle_installed
- Build / commit: <sha>

## Setup
Hardware, wiring, firmware build flags, what was connected to what.

## Procedure
Steps taken.

## Capture
Path to the capture or log committed alongside this record (for example `capture.jsonl`).

## Result
What was observed against each acceptance criterion; anything that failed or was skipped.

## Safety
What was checked to be unable to transmit or actuate, and how.
```
