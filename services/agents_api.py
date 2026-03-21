"""
MIA Agents API Server

Provides:
  - /api/agents/signed-url  — ElevenLabs signed URL for private agent sessions
  - /api/agents/webhook     — ElevenLabs server tool call handler (MCP bridge)
  - /api/agents/config      — Agent IDs for the web UI
  - /api/agents/status      — Health check for all three agents

Run:
    uvicorn services.agents_api:app --host 0.0.0.0 --port 8042 --reload

Environment variables (from .env):
    ELEVENLABS_API_KEY
    ELEVENLABS_ORCHESTRATOR_AGENT_ID
    ELEVENLABS_EVALUATOR_AGENT_ID
    ELEVENLABS_EXECUTOR_AGENT_ID
    AGENTS_WEBHOOK_SECRET
    MCP_ZIGBEE_ENDPOINT       (optional, for control_lights tool)
    GITHUB_TOKEN              (optional, for git_operation tool)
"""

import hashlib
import hmac
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="MIA Agents API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ─── Configuration ─────────────────────────────────────────────────────────────

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
WEBHOOK_SECRET = os.getenv("AGENTS_WEBHOOK_SECRET", "")

AGENT_IDS: dict[str, str] = {
    "orchestrator": os.getenv("ELEVENLABS_ORCHESTRATOR_AGENT_ID", ""),
    "evaluator":    os.getenv("ELEVENLABS_EVALUATOR_AGENT_ID", ""),
    "executor":     os.getenv("ELEVENLABS_EXECUTOR_AGENT_ID", ""),
}

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/agents/config")
async def get_agent_config() -> dict[str, Any]:
    """Return agent IDs for web UI bootstrap (non-sensitive — IDs are public)."""
    return {
        name: {"agent_id": agent_id, "configured": bool(agent_id)}
        for name, agent_id in AGENT_IDS.items()
    }


@app.get("/api/agents/signed-url")
async def get_signed_url(agent: str = Query(..., description="Agent name: orchestrator | evaluator | executor")) -> dict[str, str]:
    """Generate a signed URL for a private ElevenLabs conversation session."""
    if agent not in AGENT_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent!r}. Valid: {list(AGENT_IDS)}")

    agent_id = AGENT_IDS[agent]
    if not agent_id:
        raise HTTPException(status_code=503, detail=f"Agent '{agent}' has no agent_id configured. Run deploy-agents.py.")

    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=503, detail="ELEVENLABS_API_KEY not configured.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{ELEVENLABS_BASE}/convai/conversation/get-signed-url",
            params={"agent_id": agent_id},
            headers={"xi-api-key": ELEVENLABS_API_KEY},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ElevenLabs API error {resp.status_code}: {resp.text[:200]}")

    return resp.json()


@app.get("/api/agents/status")
async def agent_status() -> dict[str, Any]:
    """Health check — returns configuration status for all agents."""
    return {
        "ok": True,
        "api_key_configured": bool(ELEVENLABS_API_KEY),
        "agents": {
            name: {
                "configured": bool(agent_id),
                "agent_id_preview": agent_id[:12] + "..." if agent_id else None,
            }
            for name, agent_id in AGENT_IDS.items()
        },
    }


@app.post("/api/agents/webhook")
async def handle_webhook(request: Request) -> dict[str, Any]:
    """
    ElevenLabs server tool call webhook.

    ElevenLabs sends a POST with JSON body:
        {
            "tool_name": "control_lights",
            "parameters": { "color": "blue", "brightness": 80 },
            "conversation_id": "...",
            "agent_id": "..."
        }

    We verify the signature, then route to the appropriate MCP server.
    """
    body = await request.body()

    # Verify webhook signature if secret is configured
    if WEBHOOK_SECRET:
        sig_header = request.headers.get("X-ElevenLabs-Signature", "")
        expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, f"sha256={expected}"):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    tool_name = payload.get("tool_name", "")
    parameters = payload.get("parameters", {})

    result = await _route_tool(tool_name, parameters)
    return {"status": "ok", "tool": tool_name, "result": result}


# ─── MCP Bridge (tool routing) ─────────────────────────────────────────────────

async def _route_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Route an ElevenLabs tool call to the appropriate MCP server endpoint."""

    if tool_name == "control_lights":
        return await _tool_control_lights(params)

    if tool_name == "git_operation":
        return await _tool_git_operation(params)

    if tool_name == "deploy_service":
        return await _tool_deploy_service(params)

    if tool_name == "read_file":
        return await _tool_read_file(params)

    # Unknown tool — return graceful error (don't crash the conversation)
    return {"status": "error", "message": f"Unknown tool: {tool_name!r}"}


async def _tool_control_lights(params: dict[str, Any]) -> dict[str, Any]:
    """Control Zigbee smart home lights via MCP zigbee server."""
    endpoint = os.getenv("MCP_ZIGBEE_ENDPOINT", "http://localhost:8081")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{endpoint}/lights/control", json=params)
            return {"status": "ok", "response": resp.json()}
    except Exception as e:
        return {"status": "error", "message": f"Zigbee MCP unreachable: {e}"}


async def _tool_git_operation(params: dict[str, Any]) -> dict[str, Any]:
    """Git operations — status, diff, log (read-only for safety; commits require explicit flag)."""
    import subprocess
    op = params.get("operation", "status")
    repo = params.get("repo", ".")
    allowed = {"status", "diff", "log", "branch"}
    if op not in allowed:
        return {"status": "error", "message": f"Operation {op!r} not allowed. Allowed: {allowed}"}
    try:
        result = subprocess.run(
            ["git", op, "--no-pager"] + params.get("args", []),
            cwd=repo, capture_output=True, text=True, timeout=10
        )
        return {"status": "ok", "stdout": result.stdout[:4000], "returncode": result.returncode}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_deploy_service(params: dict[str, Any]) -> dict[str, Any]:
    """Stub — deployment via unified-dev-tools MCP. Extend with real MCP call."""
    return {
        "status": "ok",
        "message": f"Deploy request for {params.get('service', 'unknown')} received. MCP bridge stub — configure MCP_UNIFIED_DEV_TOOLS_ENDPOINT.",
    }


async def _tool_read_file(params: dict[str, Any]) -> dict[str, Any]:
    """Read a file (safety: only within the MIA project directory)."""
    file_path = params.get("path", "")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_path = os.path.abspath(file_path)
    if not abs_path.startswith(project_root):
        return {"status": "error", "message": "Access denied: path outside project root"}
    try:
        with open(abs_path) as f:
            content = f.read(8000)  # cap at 8KB
        return {"status": "ok", "content": content, "truncated": len(content) == 8000}
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
