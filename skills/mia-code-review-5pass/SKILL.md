---
name: mia-code-review-5pass
description: Structured five-pass review for MIA changes. Use for diffs, files, or surface-specific reviews when you need findings ordered by severity and grounded in repo conventions.
---

# MIA Code Review 5-Pass

Use this skill when reviewing code in MIA. The goal is to catch semantic regressions and integration risk that formatters, linters, and type checks will not catch on their own.

## Best Fit

- Pull request reviews
- Local diffs before commit
- Cross-surface changes touching contracts, workflows, or deployment wiring
- Risk-focused review of unfamiliar code

Skip this skill for generated files, lockfiles, or trivial config edits with no runtime effect.

## Review Scope

Support three review modes:

- File review: one file plus nearby dependencies
- Directory review: related source files inside one surface
- Diff review: changed files plus enough surrounding context to reason about impact

Before reviewing, load the repo conventions that apply to the touched surface. In practice that usually means the relevant file in `.github/instructions/` plus any matching worker prompt in `.github/prompts/`.

## The Five Passes

### 1. Correctness

Look for behavior that will be wrong even if the code compiles:

- bad branching or inverted conditions
- broken request or response shapes
- missing awaits or cleanup
- off-by-one or empty-input handling
- broker, worker, route, or task orchestration mismatches

MIA-specific checks:

- ZeroMQ message fields stay compatible across sender and receiver
- FastAPI, WebSocket, and browser clients still agree on payload shape
- schema or config changes are reflected in real consumers, not only docs

### 2. Security

Look for issues that could expose systems, credentials, or control surfaces:

- command injection in scripts or Python subprocess handling
- secrets in source, workflow YAML, or docs
- weak auth or missing guards on routes and control commands
- unsafe parsing or deserialization

MIA-specific checks:

- operational scripts do not assume trusted input without validation
- Android and web clients do not accidentally expose internal endpoints or keys

### 3. Performance

Focus on measurable cost, not style:

- repeated expensive work in loops or polling paths
- unbounded queries, scans, or retries
- unnecessary rebuild or generation steps on hot paths
- chatty broker or telemetry loops that amplify load

MIA-specific checks:

- serial, BLE, and telemetry paths do not add avoidable fan-out or blocking I/O
- web and Android flows do not poll where an existing realtime path already exists

### 4. Readability

Look for code that raises maintenance cost:

- vague naming or mixed abstraction levels
- large functions doing coordination and implementation together
- stale comments, dead branches, or duplicated logic
- hidden assumptions about ports, file paths, or deployment layout

### 5. Consistency

Review against the repo's actual patterns, not generic preferences:

- response payload shape matches surrounding service code
- lifecycle hooks follow existing initialize and shutdown behavior
- generated artifacts are regenerated instead of hand-edited
- platform code respects the owning directory's structure and naming

MIA-specific checks:

- `web/dist/` is not treated as the source of truth
- Raspberry Pi and non-hardware fallback behavior remain consistent
- CI, scripts, and deployment assets still reference real file paths

## Output Format

Always report in this order:

1. Findings
2. Validation Run
3. Residual Risk

For each finding include:

- file path
- exact line or narrow location
- severity: critical, warning, or info
- the concrete problem
- the specific fix or follow-up needed

Keep summaries brief. Findings are the deliverable.

## Validation Guidance

Run only the cheapest meaningful checks for the touched surface. Typical commands:

```bash
pytest tests/ -m "not hardware"
black . && isort . --profile black && flake8 . --max-line-length=120 --extend-ignore=E203,W503
cd apps/android && ./gradlew assembleDebug testDebugUnitTest lint
cd web && npm run build
cd platforms/cpp && cmake -B build && cmake --build build
docker compose -f infra/docker/docker-compose.yml config
pre-commit run --all-files
```

If a check is skipped because hardware, devices, secrets, or remote hosts are unavailable, say so in Residual Risk.