# MCP Doctor

Use this skill when a user says an MCP server is not showing up, fails to launch, works in one client but not another, or wants a quick audit of local MCP config hygiene.

## What this skill does

It runs the bundled `mcp-doctor` CLI against likely config locations, turns the output into a clean diagnosis, and helps the agent fix the highest-leverage issues first.

## Trigger phrases

- "my MCP server is broken"
- "Cursor sees it but Claude doesn't"
- "check my MCP config"
- "why won't this MCP server start"
- "audit my MCP setup"

## Standard workflow

1. Start at the workspace root.
2. Run the local bundle directly if it is not installed:

```bash
PYTHONPATH=src python3 -m mcp_doctor --format text
```

3. If the problem looks client-specific, scan the exact client config file too:

```bash
PYTHONPATH=src python3 -m mcp_doctor ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

4. If the user needs a shareable artifact, export Markdown:

```bash
PYTHONPATH=src python3 -m mcp_doctor --format markdown --write mcp-doctor-report.md
```

5. Fix issues in this order:
   - parse errors and wrong root keys
   - missing binaries and missing local scripts
   - duplicate server names across files
   - placeholder secrets and literal secrets committed into config
   - insecure remote HTTP endpoints

6. Re-run until the report is healthy or only contains intentional warnings.

## How to interpret findings

- `command_not_found`: the executable is missing from PATH or the command path is wrong
- `script_missing`: the config points at a local script that moved or was never shipped
- `placeholder_env_value`: an example token like `YOUR_API_KEY` is still in use
- `literal_secret_in_config`: a real-looking secret appears to be committed into JSON
- `conflicting_server_name`: multiple files define the same server name differently
- `remote_http_url`: a non-local endpoint is using plain HTTP

## Guardrails

- Never echo secret values back to the user
- If a literal secret appears in a committed config, recommend rotation after cleanup
- Treat disabled servers as informational unless the user expected them to load
- Do not auto-delete duplicate definitions until you understand which client actually reads which file
