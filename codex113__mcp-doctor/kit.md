---
schema: kit/1.0
owner: codex113
slug: mcp-doctor
title: MCP Doctor
summary: >-
  Diagnose broken MCP configs across Cursor, Claude Desktop, and local
  workspaces by catching bad JSON, missing binaries, stale paths, and risky
  secrets.
version: 1.0.2
license: MIT
tags:
  - mcp
  - diagnostics
  - agent-tools
  - cursor
  - claude
  - codex
  - config
  - debugging
  - developer-tools
model:
  provider: openai
  name: gpt-4o
  hosting: cloud API - managed by the agent runtime
tools:
  - terminal
  - filesystem
skills:
  - mcp-doctor
tech:
  - python
  - json
  - jsonc
  - mcp
parameters:
  - name: workspace
    value: .
    description: Workspace root used for discovery and relative path resolution
  - name: include_home
    value: 'true'
    description: Scan known home-directory config locations in addition to workspace files
  - name: format
    value: text
    description: 'Output mode. Supported values are text, markdown, and json'
  - name: fail_on_warnings
    value: 'false'
    description: Exit with code 2 when warnings should fail CI or automation
failures:
  - problem: >-
      JSONC config files often include comments or trailing commas that break
      naive JSON parsers
    resolution: >-
      MCP Doctor normalizes JSONC before parsing and records what it had to
      strip
    scope: general
  - problem: 'MCP configs drift after folders move, leaving local script paths broken'
    resolution: >-
      The scanner checks relative scripts against both the config directory and
      workspace root
    scope: environment
  - problem: >-
      Teams copy example configs that still contain YOUR_API_KEY style
      placeholders
    resolution: >-
      The scanner flags placeholder secrets and literal secrets stored directly
      in JSON
    scope: general
  - problem: >-
      One client reads a home config while another reads a workspace config,
      leading to duplicate server names
    resolution: >-
      MCP Doctor compares server names across files and warns when the same name
      is defined twice
    scope: general
  - problem: >-
      Remote MCP endpoints are sometimes configured with plain HTTP even outside
      localhost
    resolution: >-
      The scanner warns on non-local HTTP endpoints so they can be upgraded to
      HTTPS
    scope: general
useCases:
  - scenario: Audit a new workspace right after pasting MCP config from docs
    constraints:
      - Python 3.9 or newer must be available locally
    notFor:
      - >-
        Verifying that a remote MCP server is semantically healthy after it
        starts
  - scenario: Explain why an MCP server works in one client but not another
    constraints:
      - You need access to the relevant workspace and or home config files
    notFor:
      - Editing every client config automatically without review
  - scenario: 'Produce a Markdown report for a teammate, ticket, or AI agent to act on'
    constraints:
      - The issue must be visible from local config and path inspection
    notFor:
      - Redacting secrets from git history
inputs:
  - name: workspace_path
    description: Root directory to scan for MCP configs
  - name: explicit_paths
    description: Optional config files or directories to scan directly
  - name: output_format
    description: Desired report format for humans or downstream agents
outputs:
  - name: diagnostic_report
    description: Structured report with config-level and server-level findings
  - name: findings
    description: 'Errors, warnings, and info items with concrete fix hints'
  - name: inventory
    description: 'Normalized list of discovered configs, servers, transports, and env keys'
fileManifest:
  - path: pyproject.toml
    role: config
    description: Local packaging metadata and CLI entrypoint
  - path: setup.py
    role: config
    description: Compatibility shim for older editable installs
  - path: LICENSE
    role: docs
    description: MIT license text for the bundle
  - path: src/mcp_doctor/__init__.py
    role: source
    description: Package version marker
  - path: src/mcp_doctor/__main__.py
    role: source
    description: Module entrypoint for python -m mcp_doctor
  - path: src/mcp_doctor/analyzer.py
    role: source
    description: Core MCP config diagnostics and server validation logic
  - path: src/mcp_doctor/cli.py
    role: source
    description: Command-line interface and built-in self-test
  - path: src/mcp_doctor/discovery.py
    role: source
    description: Workspace and home-directory config discovery logic
  - path: src/mcp_doctor/jsonc.py
    role: source
    description: JSONC normalization for comments and trailing commas
  - path: src/mcp_doctor/models.py
    role: source
    description: Structured report models and summary helpers
  - path: src/mcp_doctor/reporting.py
    role: source
    description: 'Text, Markdown, and JSON report rendering'
prerequisites:
  - name: Python 3.9+
    check: python3 --version
dependencies:
  runtime:
    python: 3.9+
verification:
  command: PYTHONPATH=src python3 -m mcp_doctor --self-test --format text
  expected: MCP Doctor
selfContained: true
environment:
  runtime: python
  os: 'macos, linux, windows'
  platforms:
    - cursor
    - claude-desktop
    - codex
    - generic
  adaptationNotes: >-
    Default discovery covers standard Cursor and Claude Desktop locations on
    macOS, Linux, and Windows. Other clients can still be audited by passing
    explicit file paths or directories.
---

## Goal

Diagnose the most common MCP configuration failures before the user wastes time guessing: wrong JSON shape, broken local script paths, missing executables, placeholder secrets, duplicate server names across files, and insecure remote endpoints. The kit is intentionally local-first and reproducible. It gives agents and humans a concrete report they can act on immediately instead of another generic checklist.

## When to Use

Use MCP Doctor when a user says an MCP server is not loading, only works in one client, disappears after moving a workspace, or needs a quick audit before onboarding teammates. It is also a strong preflight step after copying config from documentation into Cursor, Claude Desktop, or a repo-local `mcp.json`.

Not for: proving a remote server is semantically healthy after startup, load-testing a hosted MCP endpoint, or rewriting every client config automatically without review.

## Inputs

The workflow takes a workspace path, optional explicit files or directories, and an optional output format. Most runs should start with the workspace root and let discovery find both local and known home-directory config locations.

## Setup

### Models

The bundled CLI does not call an LLM. The verified model above is a broadly available reference model for authoring and operating the workflow as an agent skill, not a runtime dependency of the scanner itself.

### Services

No external services are required. Everything runs locally against config files on disk.

### Parameters

- `workspace`: root folder used for discovery and relative path resolution
- `include_home`: whether to inspect known home-directory config files too
- `format`: `text`, `markdown`, or `json`
- `fail_on_warnings`: use when warnings should fail automation or CI

### Environment

Python 3.9 or newer is required. No third-party Python packages, npm modules, API keys, or external registries are needed. The scanner is designed to run inside a normal agent workspace or any developer shell.

## Steps

1. From the bundle root, run the verifier once to confirm the package is healthy:

   ```bash
   PYTHONPATH=src python3 -m mcp_doctor --self-test --format text
   ```

2. For a normal workspace audit, run the scanner from the repo root:

   ```bash
   PYTHONPATH=src python3 -m mcp_doctor --format text
   ```

3. If the issue appears only inside a specific client, pass the exact config path or config directory directly:

   ```bash
   PYTHONPATH=src python3 -m mcp_doctor ~/Library/Application\ Support/Claude/claude_desktop_config.json
   PYTHONPATH=src python3 -m mcp_doctor .cursor
   ```

4. Read the report in priority order:
   - global findings first, because they often explain cross-client conflicts
   - config-level parse failures next
   - server-level command, script, and env issues after that

5. Fix parse and structure problems before touching auth:
   - missing `mcpServers`
   - malformed JSON
   - wrong field types like string `args` instead of list `args`

6. Fix launch failures next:
   - `command_not_found`
   - `script_missing`
   - package runners with no target arguments

7. Fix hygiene and security issues last:
   - placeholder env values
   - literal secrets in config files
   - non-local plain HTTP URLs
   - duplicated server names across files

8. If you need a shareable artifact for chat, tickets, or follow-up automation, export Markdown:

   ```bash
   PYTHONPATH=src python3 -m mcp_doctor --format markdown --write mcp-doctor-report.md
   ```

9. Re-run until the report is healthy or only contains intentionally accepted warnings. When warnings remain on purpose, document why, instead of silently ignoring them.

## Failures Overcome

- **Config files with comments broke strict parsers.** Many real MCP examples use JSONC, not strict JSON. The kit strips comments and trailing commas before parsing, then records that normalization in the report so the user still knows what happened.

- **Relative script paths were ambiguous.** Workspace configs often live in `.cursor/`, but local server scripts frequently live under the workspace root. MCP Doctor checks relative paths against both the config directory and the workspace root to avoid false negatives.

- **Teams left example secrets in place.** The scanner detects placeholder values such as `YOUR_API_KEY` and flags real-looking literal secrets committed into config so users can move them to environment injection.

- **Different clients loaded different files with the same server name.** Duplicate names across workspace and home configs are easy to miss and lead to "it works here but not there" confusion. MCP Doctor groups server names across files and warns when the same name is defined more than once.

- **Agents generated generic debugging advice.** Instead of another prose-only checklist, this kit ships a working CLI and a skill that produces concrete findings with fix hints, so follow-up actions are grounded in the actual files on disk.

## Validation

- `PYTHONPATH=src python3 -m mcp_doctor --self-test --format text` prints an MCP Doctor report and exits successfully
- `python3 -m py_compile src/mcp_doctor/*.py` succeeds with no syntax errors
- Scanning `examples/broken-workspace.mcp.jsonc` reports at least one missing script error, one missing command error, and one placeholder secret warning
- Scanning a healthy config such as `examples/healthy-cursor.mcp.json` produces a healthy server entry with no launch or parse errors

## Outputs

The primary output is a report with three levels of signal:

- global findings for cross-file conflicts
- config-level findings for parse and shape problems
- server-level findings for commands, scripts, env values, URLs, and transport issues

The same report can be rendered as text for terminal use, Markdown for sharing, or JSON for downstream tooling. This makes the kit useful both as a human debugging aid and as a machine-readable preflight in larger agent workflows.

## Constraints

- The scanner reasons from local config files and path availability only. It does not prove that a remote MCP service is logically correct after it starts.
- Discovery intentionally targets a small set of high-signal default locations plus recursive `*mcp*.json*` search. If a client stores config elsewhere, pass the path explicitly.
- Relative path heuristics cover the config directory and workspace root. If a team uses a different convention, pass explicit file paths and interpret the result accordingly.
- The tool warns on secret hygiene problems but does not redact or rotate secrets for you.

## Safety Notes

- Treat config files as sensitive. They may contain credentials, tokens, or internal endpoints. Do not paste raw secrets into chat or issue trackers.
- If MCP Doctor flags a literal secret in a committed file, remove it from the config, rotate it, and then review repository history if the file was versioned.
- A warning about non-local plain HTTP should be taken seriously. Remote MCP transport without TLS is easy to misconfigure and hard to audit later.
- The kit is diagnostic first. Review findings before deleting duplicate configs or changing launch commands, especially when multiple clients read different files.
