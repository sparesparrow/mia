"""Agent handoffs and the shapes that play the roles, for the web console (ADR-0029, REQ-WEB-007).

The three roles are fixed by function (``agents/AGENTS.md``): the orchestrator plans and talks to the user, the
executor does the work, the evaluator judges it. The personas that play them are a *shape*, and the user defines
the shapes: ``agent_shapes.json`` in ``MIA_STATE_DIR`` holds up to eight, and one of them is active.

- ``GET /console/agents/shapes`` and ``PUT /console/agents/shapes`` (write scope) read and replace that file.
- ``POST /console/agents/events`` (write scope): an agent says that work passed from one role to another.
- ``GET /console/agents/events``: newline-delimited JSON. The recent handoffs first, then new ones as they are
  posted, each with the personas of the shape that was active when it was posted.

Handoffs live in memory only (the last ``BACKLOG`` of them) and are lost on restart. Nothing here reaches the car:
the routes store text and pass it to watchers. The console's client gate (``web_console.console_gate``) applies to
every route.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Deque, Dict, Set

from api.web_console import KEEPALIVE_SEC, console_gate
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("mia.console_agents")

router = APIRouter(tags=["Web console"], dependencies=[Depends(console_gate)])

ROLES = ("orchestrator", "evaluator", "executor")
PARTIES = ROLES + ("human",)
FILE_NAME = "agent_shapes.json"
DEFAULT_STATE_DIR = "/var/lib/mia"
MAX_SHAPES = 8
BACKLOG = 50
SUBSCRIBER_LIMIT = 64
SUMMARY_MAX = 280
TASK_MAX = 80

_ID = re.compile(r"^[a-z][a-z0-9_-]{0,23}$")
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

# The shape this repository ships (agents/AGENTS.md); it is in use until the user stores their own.
DEFAULT_SHAPES: Dict[str, Any] = {
    "active": "crew",
    "shapes": {
        "crew": {
            "label": "The crew",
            "roles": {
                "orchestrator": {"persona": "The Feral Maestro", "color": "#e8a835", "voice": "Brian"},
                "evaluator": {"persona": "The Unhinged Analyst", "color": "#5b8fb9", "voice": "Daniel"},
                "executor": {"persona": "The Obsessive Closer", "color": "#00e5ff", "voice": "Callum"},
            },
        }
    },
}


def shapes_path() -> Path:
    return Path(os.environ.get("MIA_STATE_DIR", DEFAULT_STATE_DIR)) / FILE_NAME


def _text(value: Any, what: str, low: int, high: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{what} must be text")
    value = value.strip()
    if not low <= len(value) <= high:
        raise ValueError(f"{what} must be {low} to {high} characters")
    if _CONTROL.search(value):
        raise ValueError(f"{what} must not hold control characters")
    return value


def validate_shapes(data: Any) -> Dict[str, Any]:
    """The shapes document in its stored form; ValueError says what is wrong with it."""
    if not isinstance(data, dict):
        raise ValueError("shapes must be an object")
    shapes = data.get("shapes")
    if not isinstance(shapes, dict) or not shapes:
        raise ValueError("at least one shape is needed")
    if len(shapes) > MAX_SHAPES:
        raise ValueError(f"at most {MAX_SHAPES} shapes")
    clean: Dict[str, Any] = {}
    for shape_id, shape in shapes.items():
        if not isinstance(shape_id, str) or not _ID.match(shape_id):
            raise ValueError(f"unusable shape id {shape_id!r}")
        if not isinstance(shape, dict) or not isinstance(shape.get("roles"), dict):
            raise ValueError(f"shape {shape_id} needs roles")
        roles = shape["roles"]
        if set(roles) != set(ROLES):
            raise ValueError(f"shape {shape_id} must name exactly the roles {', '.join(ROLES)}")
        clean_roles = {}
        for role in ROLES:
            part = roles[role]
            if not isinstance(part, dict):
                raise ValueError(f"{shape_id}.{role} must be an object")
            color = part.get("color", "#888888")
            if not isinstance(color, str) or not _COLOR.match(color):
                raise ValueError(f"{shape_id}.{role}.color must be #rrggbb")
            clean_roles[role] = {
                "persona": _text(part.get("persona"), f"{shape_id}.{role}.persona", 1, 40),
                "color": color.lower(),
                "voice": _text(part.get("voice", ""), f"{shape_id}.{role}.voice", 0, 40),
            }
        clean[shape_id] = {
            "label": _text(shape.get("label", shape_id), f"{shape_id}.label", 1, 60),
            "roles": clean_roles,
        }
    active = data.get("active")
    if active not in clean:
        raise ValueError("active must name one of the shapes")
    return {"active": active, "shapes": clean}


def load_shapes() -> Dict[str, Any]:
    """The stored shapes; a missing, unreadable or invalid file gives the shipped default."""
    try:
        return validate_shapes(json.loads(shapes_path().read_text(encoding="utf-8")))
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        logger.warning("agent shapes unusable, using the default: %s", exc)
    return json.loads(json.dumps(DEFAULT_SHAPES))


def save_shapes(doc: Dict[str, Any]) -> bool:
    path = shapes_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, partial = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
            os.replace(partial, path)
        except BaseException:
            os.unlink(partial)
            raise
    except OSError as exc:
        logger.warning("agent shapes not saved: %s", exc)
        return False
    return True


def stored() -> bool:
    """True once the user has stored shapes of their own (the setup checklist asks)."""
    return shapes_path().is_file()


class HandoffHub:
    """Recent handoffs and the streams watching them. Everything runs on the API's event loop."""

    def __init__(self, backlog: int = BACKLOG) -> None:
        self.recent: Deque[Dict[str, Any]] = deque(maxlen=backlog)
        self._watchers: Set["asyncio.Queue[Dict[str, Any]]"] = set()
        self._seq = 0

    def publish(self, event: Dict[str, Any], remember: bool = True) -> Dict[str, Any]:
        if remember:
            self._seq += 1
            event = {**event, "seq": self._seq}
            self.recent.append(event)
        for queue in list(self._watchers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # a watcher that stopped reading loses the stream, not the others
                self._watchers.discard(queue)
                logger.warning("agent console: dropping a watcher that is not reading")
        return event

    def watch(self) -> "asyncio.Queue[Dict[str, Any]]":
        queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(maxsize=SUBSCRIBER_LIMIT)
        self._watchers.add(queue)
        return queue

    def unwatch(self, queue: "asyncio.Queue[Dict[str, Any]]") -> None:
        self._watchers.discard(queue)

    def watching(self, queue: "asyncio.Queue[Dict[str, Any]]") -> bool:
        return queue in self._watchers


hub = HandoffHub()


# ── Shapes ────────────────────────────────────────────────────────────────


@router.get("/console/agents/shapes")
async def get_shapes() -> Dict[str, Any]:
    return {**load_shapes(), "roles": list(ROLES), "stored": stored()}


@router.put("/console/agents/shapes")
async def put_shapes(body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        doc = validate_shapes(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    if not save_shapes(doc):
        raise HTTPException(status_code=500, detail="the shapes could not be stored")
    hub.publish({"type": "shapes", **doc}, remember=False)
    return {"status": "ok", "message": "shapes stored", **doc}


# ── Handoffs ──────────────────────────────────────────────────────────────


class HandoffIn(BaseModel):
    from_role: str
    to_role: str
    summary: str = ""
    task: str = ""


def _persona(shape: Dict[str, Any], party: str) -> Dict[str, str]:
    if party == "human":
        return {"persona": "you", "color": "#888888"}
    role = shape["roles"][party]
    return {"persona": role["persona"], "color": role["color"]}


def make_handoff(body: HandoffIn) -> Dict[str, Any]:
    for party in (body.from_role, body.to_role):
        if party not in PARTIES:
            raise ValueError(f"unknown role {party!r}; one of {', '.join(PARTIES)}")
    if body.from_role == body.to_role:
        raise ValueError("a handoff goes from one role to another")
    summary = _text(body.summary, "summary", 0, SUMMARY_MAX)
    task = _text(body.task, "task", 0, TASK_MAX)
    doc = load_shapes()
    shape = doc["shapes"][doc["active"]]
    source, target = _persona(shape, body.from_role), _persona(shape, body.to_role)
    return {
        "type": "handoff",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "shape": doc["active"],
        "from_role": body.from_role,
        "to_role": body.to_role,
        "from_persona": source["persona"],
        "to_persona": target["persona"],
        "from_color": source["color"],
        "to_color": target["color"],
        "task": task,
        "summary": summary,
    }


@router.post("/console/agents/events")
async def post_handoff(body: HandoffIn) -> Dict[str, Any]:
    try:
        event = make_handoff(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return {"status": "ok", "message": "handoff recorded", "event": hub.publish(event)}


def _line(obj: Dict[str, Any]) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


async def handoff_lines(request: Request) -> AsyncIterator[bytes]:
    """The stream behind ``GET /console/agents/events``."""
    queue = hub.watch()
    try:
        yield _line({"type": "hello", **load_shapes()})
        for event in list(hub.recent):
            yield _line(event)
        last = time.monotonic()
        while hub.watching(queue) and not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(queue.get(), 1.0)
            except asyncio.TimeoutError:
                if time.monotonic() - last >= KEEPALIVE_SEC:
                    last = time.monotonic()
                    yield _line({"type": "keepalive"})
                continue
            last = time.monotonic()
            yield _line(event)
        if not hub.watching(queue):
            yield _line({"type": "unavailable", "reason": "this console stopped reading"})
    finally:
        hub.unwatch(queue)


@router.get("/console/agents/events")
async def handoff_events(request: Request) -> StreamingResponse:
    return StreamingResponse(
        handoff_lines(request),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def clear() -> None:
    """Forget every handoff (tests)."""
    hub.recent.clear()
