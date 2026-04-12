# Known Discovery Paths

MCP Doctor auto-discovers a small set of high-signal paths before it falls back to recursive `*mcp*.json*` discovery in the workspace.

## Workspace-first paths

- `.cursor/mcp.json`
- `.cursor/mcp.jsonc`
- `.vscode/mcp.json`
- `.vscode/mcp.jsonc`
- `mcp.json`
- `mcp.jsonc`
- `.mcp.json`
- `.mcp.jsonc`
- `claude_desktop_config.json`

## Home-directory paths

- `~/.cursor/mcp.json`
- `~/.cursor/mcp.jsonc`
- `~/Library/Application Support/Claude/claude_desktop_config.json`
- `~/.config/Claude/claude_desktop_config.json`
- `~/AppData/Roaming/Claude/claude_desktop_config.json`

## Resolution rules

- If you pass explicit files, MCP Doctor scans only those files.
- If you pass a directory, MCP Doctor recursively searches it for `*mcp*.json` and `*mcp*.jsonc`, while skipping common heavy directories such as `.git`, `node_modules`, and virtualenv folders.
- Relative script paths inside server definitions are checked against both the config file directory and the workspace root, because real-world configs commonly use both patterns.

## What it does not assume

- It does not assume every client uses the same config path.
- It does not assume remote URLs are healthy just because they parse.
- It does not auto-fix config files for you. The output is intentionally diagnostic first.
