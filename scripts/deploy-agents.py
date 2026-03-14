#!/usr/bin/env python3
"""
Deploy MIA conversational agents to ElevenLabs.

Reads per-agent configs from agents/*/elevenlabs-config.json,
injects system prompts, creates/updates agents via ElevenLabs API,
and writes returned agent IDs back to .env.

Usage:
    python scripts/deploy-agents.py              # Deploy all agents
    python scripts/deploy-agents.py --dry-run    # Print payloads without calling API
    python scripts/deploy-agents.py --agent executor  # Deploy one agent only
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ─── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).parent.parent
AGENTS_DIR  = REPO_ROOT / "agents"
WEB_ASSETS  = REPO_ROOT / "web" / "assets" / "agents"
ENV_FILE    = REPO_ROOT / ".env"

AGENT_NAMES = ["orchestrator", "evaluator", "executor"]
API_BASE    = "https://api.elevenlabs.io/v1"

# ─── Helpers ───────────────────────────────────────────────────────────────────

def load_env() -> dict[str, str]:
    """Read .env file into a dict (doesn't override existing os.environ)."""
    if not ENV_FILE.exists():
        return {}
    result = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def update_env(key: str, value: str) -> None:
    """Update or append a key=value in .env."""
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    pattern = re.compile(r"^" + re.escape(key) + r"=.*$", re.MULTILINE)
    new_line = f"{key}={value}"
    if pattern.search(content):
        content = pattern.sub(new_line, content)
    else:
        content = content.rstrip("\n") + f"\n{new_line}\n"
    ENV_FILE.write_text(content)


def load_agent_payload(name: str, env: dict[str, str]) -> dict:
    """Build the ElevenLabs agent creation payload for one agent."""
    config_path  = AGENTS_DIR / name / "elevenlabs-config.json"
    prompt_path  = AGENTS_DIR / name / "system-prompt.md"
    avatar_path  = WEB_ASSETS / f"{name}.jpg"

    config = json.loads(config_path.read_text())
    prompt = prompt_path.read_text()

    # Inject system prompt
    config["conversation_config"]["agent"]["prompt"]["prompt"] = prompt

    # Inject voice ID from env if set
    voice_key = f"ELEVENLABS_{name.upper()}_VOICE_ID"
    voice_id  = env.get(voice_key, os.getenv(voice_key, ""))
    if voice_id:
        config["conversation_config"]["tts"]["voice_id"] = voice_id

    # Inject avatar URL (publicly hosted required; use placeholder if not set)
    avatar_env_key = f"ELEVENLABS_{name.upper()}_AVATAR_URL"
    avatar_url = env.get(avatar_env_key, os.getenv(avatar_env_key, ""))
    if avatar_url:
        config["platform_settings"]["widget"]["avatar"]["url"] = avatar_url

    return config


def create_or_update_agent(name: str, payload: dict, api_key: str, existing_id: str = "") -> str:
    """Create a new agent or update existing one. Returns agent_id."""
    import httpx

    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    if existing_id:
        # Update existing agent
        url  = f"{API_BASE}/convai/agents/{existing_id}"
        resp = httpx.patch(url, json=payload, headers=headers, timeout=30)
        verb = "Updated"
    else:
        # Create new agent
        url  = f"{API_BASE}/convai/agents/create"
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        verb = "Created"

    if resp.status_code not in (200, 201):
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)

    data     = resp.json()
    agent_id = data.get("agent_id", "")
    print(f"  {verb}: {agent_id}")
    return agent_id


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy MIA agents to ElevenLabs")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without calling API")
    parser.add_argument("--agent", choices=AGENT_NAMES, help="Deploy only this agent")
    args = parser.parse_args()

    env     = load_env()
    api_key = env.get("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY", "")

    if not api_key and not args.dry_run:
        print("ERROR: ELEVENLABS_API_KEY not found in .env or environment.", file=sys.stderr)
        sys.exit(1)

    targets = [args.agent] if args.agent else AGENT_NAMES

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Deploying {len(targets)} agent(s) to ElevenLabs...\n")

    for name in targets:
        print(f"── {name.upper()} ──────────────────────")
        payload = load_agent_payload(name, env)

        if args.dry_run:
            # Print summary without secrets
            summary = {
                "name":          payload.get("name"),
                "voice_id":      payload["conversation_config"]["tts"].get("voice_id") or "(not set)",
                "temperature":   payload["conversation_config"]["agent"]["prompt"]["temperature"],
                "prompt_chars":  len(payload["conversation_config"]["agent"]["prompt"]["prompt"]),
                "first_message": payload["conversation_config"]["agent"]["first_message"][:80] + "...",
            }
            print(json.dumps(summary, indent=2))
            continue

        # Check for existing agent ID to update rather than recreate
        existing_id_key = f"ELEVENLABS_{name.upper()}_AGENT_ID"
        existing_id     = env.get(existing_id_key) or os.getenv(existing_id_key, "")

        agent_id = create_or_update_agent(name, payload, api_key, existing_id)

        # Write agent ID back to .env
        update_env(existing_id_key, agent_id)
        print(f"  Saved {existing_id_key}={agent_id[:12]}... to .env")

    if not args.dry_run:
        print(f"\n✓ Done. Start the API server with:")
        print(f"  uvicorn services.agents_api:app --host 0.0.0.0 --port 8042")
        print(f"\n  Then open http://localhost:8080/agents/ in your browser.")


if __name__ == "__main__":
    main()
