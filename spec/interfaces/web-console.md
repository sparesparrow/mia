# Web console interface

The Pi's own web console (ADR-0029): one static page at `/console/` served by mia-api, and the routes it uses. Every
route below is behind the console's client gate (loopback always; RFC 1918, link-local and unique-local addresses
only once an API key is configured; nothing else) and the API's key check (`X-API-Key`, read scope for GET, write
scope otherwise). `MIA_WEB_CONSOLE=0` answers 404 on all of them. Streams are newline-delimited JSON
(`application/x-ndjson`) read with `fetch`, so the key travels in a header.

| Route | Scope | What |
|---|---|---|
| `GET /console/`, `/console/console.js`, `/console/console.css` | public | the page; no data |
| `GET /console/voice/events` | read | the voice machine live; format in `voice.md`, "Web console stream" |
| `POST /console/voice/settings` | write | verbosity, persona, language (`voice.md`) |
| `GET /console/setup` | read | first-run checklist (REQ-WEB-008) |
| `GET /console/agents/shapes` | read | the agent shapes (REQ-WEB-007) |
| `PUT /console/agents/shapes` | write | replace the agent shapes |
| `POST /console/agents/events` | write | report a handoff |
| `GET /console/agents/events` | read | handoffs live |

The page also reads `GET /auth/status`, `/status`, `/telemetry` and `/audio/settings`, and writes
`PUT /audio/settings`. It calls nothing else.

## Agent shapes

The roles are fixed: `orchestrator`, `evaluator`, `executor` (`agents/AGENTS.md`). A shape gives each a persona.
Stored as `agent_shapes.json` in `MIA_STATE_DIR`:

```json
{
  "active": "dwarf",
  "shapes": {
    "dwarf": {
      "label": "Red Dwarf",
      "roles": {
        "orchestrator": {"persona": "Holly", "color": "#336699", "voice": "Norman"},
        "evaluator": {"persona": "Rimmer", "color": "#aa3333", "voice": ""},
        "executor": {"persona": "Kryten", "color": "#33aa55", "voice": "Robert"}
      }
    }
  }
}
```

- 1 to 8 shapes; a shape id matches `^[a-z][a-z0-9_-]{0,23}$`; `active` names one of them.
- Each shape names exactly the three roles. `persona` 1 to 40 characters, `voice` 0 to 40, `label` 1 to 60, no
  control characters; `color` is `#rrggbb`.
- `PUT` replaces the whole document (422 and nothing stored when any part is wrong). `GET` adds `roles` (the three
  names) and `stored` (false while the shipped shape `crew` is in use).

## Handoffs

`POST /console/agents/events` takes `{from_role, to_role, task?, summary?}`. A party is one of the three roles or
`human`; the two must differ. `task` is at most 80 characters, `summary` at most 280, neither with control
characters. The Pi adds the time, a sequence number and the personas of the active shape, and answers with the event.

`GET /console/agents/events` lines, each with a `type`:

| `type` | Fields | When |
|---|---|---|
| `hello` | `active`, `shapes` | first line |
| `handoff` | `seq`, `at` (UTC, ISO 8601), `shape`, `from_role`, `to_role`, `from_persona`, `to_persona`, `from_color`, `to_color`, `task`, `summary` | the recent ones (up to 50, kept in memory) after `hello`, then each new one |
| `shapes` | `active`, `shapes` | after a `PUT /console/agents/shapes` |
| `keepalive` | none | after 10 s without a line |
| `unavailable` | `reason` | last line: this watcher fell 64 events behind and was dropped |

Producers: the `claude-agent-bridge` reports `orchestrator` to `executor` (task = the agent, summary = the
request) before each dispatch and `executor` to `orchestrator` (the answer, or `failed: <error>`) after it, when
`MIA_CONSOLE_HANDOFFS=1`; summaries are cut to 140 characters. Any other agent with a write key may post.

## Setup checklist

`GET /console/setup` answers `{status, message, done, total, steps}`. Each step is
`{id, title, done, detail, how, action?}`; `done` is `true`, `false` or `null` (the Pi cannot tell). Steps, in
order: `api_key`, `vehicle`, `phone`, `voice_console`, `voice_settings`, `audio_settings`, `agent_shapes`. `action`
(`voice`, `audio`, `agents`) names a form on the page. Values are never returned: only whether they are set, and the
number of enrolled phones.
