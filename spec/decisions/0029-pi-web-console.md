# 0029. The Pi serves its own web console, read-only toward the car, local by default

- Status: Proposed
- Date: 2026-11-28
- Requirements: REQ-WEB-006

## Context
Only the Android app faces the user: it holds the voice console, the settings and the onboarding. Without a phone,
nobody can configure MIA or watch the voice machine (issue 330). The Pi already has what such a view needs. mia-api
serves `/status`, `/telemetry` and `/audio/settings` (REQ-VOICE-030). `/ws/voice` carries the console protocol
(`spec/interfaces/voice.md`), which sends every event of the voice machine to each open session. Its settings
commands (SetVerbosity, SwitchPersona, SetLanguage) are already allowed from a peer (ADR-0019).

A browser cannot speak that protocol as it stands. The frames are FlatBuffers, and a browser WebSocket cannot send
the `X-API-Key` header that `/ws/voice` requires (REQ-SEC-001). Exposure matters too. mia-api listens on every
interface of the car's network, and with no key configured the API is open (#313, #139). A new page that is
reachable from the car's Wi-Fi without a key would add one more way into the car.

## Decision
- **mia-api serves the console at `/console/`.** It is one static page with no build step. `index.html`,
  `console.js` and `console.css` live in `apps/rpi-backend/py-api/api/console/` and are served by name, nothing
  else from that directory. They ship with the backend (`deploy-raspberry-pi.sh` copies `py-api`, and the release
  tarball holds `apps/rpi-backend`). The page loads nothing from another host, because the Pi in the car has no
  internet of its own. It is sent with `Content-Security-Policy: default-src 'self'` (no inline script, no
  framing), `nosniff` and `no-referrer`.
- **The page uses the API's own routes and two new ones** (`api/web_console.py`):
  - `GET /console/voice/events` streams the voice machine as newline-delimited JSON. The API opens a session of its
    own on the machine: in process with `VOICE_CONSOLE_BACKEND=sim`, or as a DEALER on the router's loopback socket
    with `router`, as `voice_relay` does. It sends that session no command, so the stream only watches. The
    decoding into JSON happens on the Pi, so the browser needs no FlatBuffers. The line format is in
    `spec/interfaces/voice.md`.
  - `POST /console/voice/settings` sends only SetVerbosity, SwitchPersona and SetLanguage, on a short session of
    its own. The machine checks them and stores them as it does for the phone (ADR-0019).
  - Audio settings use `GET` and `PUT /audio/settings`. Status and telemetry use `GET /status` and `GET /telemetry`.
- **Read-only toward the car.** Nothing the console calls writes to a vehicle bus, a GPIO pin, the LEDs, `/command`,
  the OTA or the device registry. A test reads `console.js` and fails if the page names any other API path. The
  page writes text from the Pi with `textContent` only.
- **Authentication is the API key, in the header.** The page asks for the key and keeps it in the tab's
  `sessionStorage`. Every request sends it in `X-API-Key`, never in the URL. Because the stream is a `fetch`, not
  an `EventSource` or a WebSocket, the header can be set. GET needs the read scope and the settings POST needs the
  write scope (the app-wide check). Only the three static page files are public: the browser cannot send a key when
  it navigates to them, and they hold no data.
- **Who may reach it** is checked on every `/console` route, on top of the key:
  - a loopback client (a browser on the Pi's own screen) always. With no key configured, its `Host` header must
    name loopback as well, so a DNS-rebinding page in that browser cannot read the stream;
  - a client on the car's network (10/8, 172.16/12, 192.168/16, 169.254/16, fc00::/7, fe80::/10) only when an
    API key is configured. Until `MIA_API_KEY` is set, the page answers such a client with 403 and says why;
  - any other address never.

  `MIA_WEB_CONSOLE=0` turns every console route off (404). The voice routes also need `VOICE_CONSOLE=1`, the
  switch that already exposes the voice machine over `/ws/voice`.

## Consequences
- MIA can be configured and watched from any browser on the car's network once a key is set, or from the Pi's own
  screen without one. The phone stays the main interface.
- The console adds no exposure to `/status` and `/telemetry` beyond what the API already has. Those routes keep
  their own policy (#313, #139). The gate only covers what this record adds.
- On the car's network the key travels over plain HTTP, as it does for the Android app (ADR-0016). Anyone who can
  watch that network can read it. TLS on the Pi is still open work (#139).
- Each open console holds one session on the voice machine and, with the router backend, one ZeroMQ peer on the
  hub. Nothing limits how many one client opens.
- The page is source-checked in CI, not rendered there. No record yet shows it in a browser on the real Pi.
- Not in this record: the live view of agent handoffs (orchestrator, evaluator and executor with their personas)
  and the onboarding steps. The event stream is where they would join later.

## Sources
- `apps/rpi-backend/py-api/api/web_console.py`, `apps/rpi-backend/py-api/api/console/`
- `apps/rpi-backend/py-api/api/auth/dependencies.py` (`CONSOLE_PAGE_PATHS`)
- `tests/unit/rpi_backend/test_web_console.py`
- `spec/interfaces/voice.md` (the web console's JSON lines)
