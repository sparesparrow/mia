# Task 2 report
Status: DONE_WITH_CONCERNS. Commit: see `git log -1` on fix/obd-scan-full-flow (not pushed).

Built: schemas/json/mia-grant.schema.json, bin/mia-enroll, infra/deploy/rpi/install-enroll-access.sh,
tests/unit/tools/test_mia_enroll.py (14 tests), tests/unit/infra/test_enroll_access.py (2 tests),
spec/requirements/onboarding.yaml (REQ-ONB-001..005 -> implemented_and_ci_tested, not_proven filled in).

Checks: pytest tests/unit/tools/test_mia_enroll.py tests/unit/infra -> 61 passed, 2 skipped, 1 failed
(test_pi_install::test_the_installed_api_imports_under_the_unit_pythonpath: pre-existing, python-multipart vs multipart
in this PC's env, unrelated). traceability check: 0 errors, 5 pre-existing warnings. shellcheck: clean.
Tests were first run failing (module missing), then passing.

Choices where the ADR was silent: signer principal in allowed_signers is `mia-auth-server`; clock skew 60 s applies
to iat only (exp is strict, now >= exp refused); device_fp = fingerprint of /etc/ssh/ssh_host_ed25519_key.pub
(MIA_DEVICE_PUB), since the phone compares the host-key fp; jti is recorded after pairing succeeds, under a flock,
and never pruned; env var name MIA_API_KEY (matches api_key.py); sshd key helper /usr/local/sbin/mia-enroll-authkeys
validates %t/%k and emits restrict,command="sudo /opt/mia/bin/mia-enroll",no-pty,...; bin/mia-enroll has no
`from __future__ import annotations` because dataclass + importlib-by-path breaks with it.
MIA_ENROLL_NOW and MIA_ENROLL_SKIP_CHOWN are test overrides (sudo resets env, as with mia-apply-update).

Concerns: sshd/sudo not exercised for real; a pre-existing /etc/mia/environment with an empty MIA_API_KEY= line is
treated as present; flake8 not installed here so lint unchecked; schema is documentation (claims validated by hand).
Phone registry not called (Task 3).

## Fix round 1

Findings addressed (reviewer + orchestrator rulings):
1. jti restricted to ^[A-Za-z0-9._:-]{1,128}$ in code and schema (refused as "invalid jti"); seen_jti read with splitlines().
2. jti recorded inside the flock block before pair.add (fail closed: failed pairing or billing write burns the grant).
3. main() wraps unexpected exceptions: final JSON line {ok:false, step:"internal", error:"unexpected <ExcClass>"}, exit 1, no exception text.
4. Empty MIA_API_KEY= (also "" and export forms) counts as absent; the last MIA_API_KEY line decides; a new line is appended,
   existing lines never edited; key never printed. ADR-0025 and REQ-ONB-003/005 text updated to match; REQ-ONB-003 not_proven
   now says power-loss between verification and jti write is not simulated.

Covering tests (tests/unit/tools/test_mia_enroll.py, written first, 13 failed before the fix):
test_jti_outside_the_allowed_alphabet_is_refused, test_cli_whitespace_jti_refused_and_nothing_stored,
test_cli_prefix_jti_is_not_a_replay_of_a_longer_one (also valid-jti replay refused), test_cli_failed_pairing_burns_the_grant,
test_cli_failed_billing_write_burns_the_grant, test_cli_empty_api_key_line_counts_as_absent,
test_cli_api_key_set_then_blanked_later_gets_a_new_line, test_cli_always_ends_with_the_json_line_on_internal_errors,
test_internal_error_message_never_contains_environment_file_content.

Command: python -m pytest tests/unit/tools/test_mia_enroll.py tests/unit/infra/test_enroll_access.py -o addopts="" -q
Output: 33 passed, 1 warning in 4.06s
Command: python tools/ci/traceability.py check
Output: traceability: 0 error(s), 5 warning(s) (pre-existing)
