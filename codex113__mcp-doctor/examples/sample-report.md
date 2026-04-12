# Sample MCP Doctor Report

- Workspace: `/workspace/project`
- Status: `error`
- Configs: `1`
- Servers: `2`
- Errors: `2`
- Warnings: `1`
- Info: `0`

## /workspace/project/examples/broken-workspace.mcp.jsonc

- Source: `explicit-file`
- Status: `error`
- Root key: `mcpServers`
- Parse note: Removed 1 JSONC comment block(s) before parsing
- Parse note: Removed 2 trailing comma(s) before parsing

### Servers

#### filesystem

- Status: `error`
- Transport: `stdio`
- Command: `python3 missing/server.py`
- Env keys: `API_KEY`

- `error` `script_missing` (filesystem): Server filesystem references a missing script: `/workspace/project/missing/server.py`
  Hint: Fix the relative path or ship the script next to the config
- `warning` `placeholder_env_value` (filesystem): Server filesystem still uses a placeholder value for API_KEY
  Hint: Replace the placeholder with a real secret or an environment reference

#### ghost

- Status: `error`
- Transport: `stdio`
- Command: `definitely-not-a-real-binary`

- `error` `command_not_found` (ghost): Server ghost points to a command that is not available: definitely-not-a-real-binary
  Hint: Install the binary, fix the path, or switch to a command that exists on PATH
