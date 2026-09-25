<!-- One approved slice per pull request. See spec/README.md for the three-part model and the control plane. -->

## What changes

<!-- One or two sentences. -->

## Requirements and decisions

- Requirements: <!-- REQ-AREA-NNN, and whether this PR adds, changes or promotes their evidence state -->
- Decisions: <!-- ADR-NNNN, or "none" -->
- Issues: <!-- Closes #NNN -->

## Claim
<!-- What now works. -->

## Proof
<!-- Commands, test names (tagged with the requirement) or capture files that show it. -->

## Not proven
<!-- What this does not cover yet: hardware, a live service, a phone, the vehicle. -->

## Safety
<!-- What cannot transmit on a vehicle bus or actuate anything, and how that is enforced. "n/a" only if nothing here touches hardware. -->

## Next owner
<!-- Who acts next (Evaluator review, bench validation, a follow-up issue). -->

## Checklist

- [ ] New behaviour has a requirement in `spec/requirements/`; new tests carry `@pytest.mark.req(...)` or `// @req`
- [ ] `python tools/ci/traceability.py check` passes, and no requirement claims more evidence than exists
- [ ] Bench, hardware or vehicle claims have a record in `spec/evidence/<REQ-ID>/`
