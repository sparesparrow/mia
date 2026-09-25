---
name: mia-project-scaffold
description: Exemplar-driven file creation for MIA. Use when adding a new file or small feature and you need it to match the repo's existing patterns, wiring, and validation flow.
---

# MIA Project Scaffold

Use this skill when creating new files in MIA. The goal is to generate the smallest valid file set that matches existing patterns in the owning surface instead of inventing a new structure.

## Best Fit

- new Android screens, managers, or tests
- new backend workers, services, or support modules
- new MCP module files or shared helpers
- new web pages or generator-backed content
- new operational scripts or workflow helpers

Do not use this skill when there are no good exemplars in the repo. In that case, define the pattern first with the user instead of guessing.

## Workflow

### 1. Parse the Request

Extract:

- file type
- target surface
- intended name
- purpose
- expected wiring, if any

Ask at most one clarifying question if the target surface or file type is ambiguous.

### 2. Find Exemplars

Find two or three nearby examples from the same platform area. Prefer same-directory or sibling-directory files over distant examples.

For each exemplar, capture:

- file naming style
- import style
- export style
- test location and naming
- initialization and error-handling pattern
- registration or wiring points

### 3. Determine the Smallest File Set

Generate only what the surface already uses. Typical possibilities:

- main file
- test file
- companion types or config file
- registry, barrel, route, or workflow update

Do not add empty placeholder files, stub tests with no assertions, or extra supporting files the surface does not already use.

### 4. Generate From the Closest Pattern

The new file should:

- follow the exemplar structure closely
- use real names and meaningful logic
- be importable or executable immediately
- avoid placeholder comments and dead scaffolding

### 5. Wire It In

If the exemplars are registered somewhere, wire the new file into the same places. Common MIA registration points include:

- Android navigation or dependency injection setup
- backend route tables or worker registration
- orchestration module registries
- web generator inputs or page indexes
- scripts referenced by workflows or bootstrap paths

Never invent a new registration point just to fit the new file.

### 6. Validate

Run the smallest relevant validation for the touched surface and fix obvious breakage before stopping.

Typical commands:

```bash
pytest tests/ -m "not hardware"
cd apps/android && ./gradlew assembleDebug testDebugUnitTest lint
cd web && npm run build
cd platforms/cpp && cmake -B build && cmake --build build
docker compose -f infra/docker/docker-compose.yml config
```

## Surface Notes

### Android

- Prefer exemplars under `apps/android/`
- Keep Compose UI thin and push logic into managers, repositories, or data layers

### RPi Backend and Python

- Match existing `status` and `message` payload style where relevant
- Preserve simulation fallback for hardware-facing code

### Contracts and Schemas

- Edit source schema or contract definitions, then regenerate derived artifacts
- Do not hand-edit generated code in `Mia/`

### Web

- Edit source files under `web/`, not generated output under `web/dist/`
- Rebuild if template, i18n, or generator inputs change

### Ops and Automation

- Keep `/opt/mia`, systemd names, workflow paths, and script entry points aligned with the real tree

## Completion Output

End with a short scaffold summary:

- files created
- files updated for wiring
- exemplars used
- validation run

If exemplar coverage was weak, say so explicitly instead of pretending the pattern was well established.