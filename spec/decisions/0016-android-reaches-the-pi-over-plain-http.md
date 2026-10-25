# 0016. The Android app reaches the Pi over plain HTTP, with the API key in a header

- Status: Accepted
- Date: 2026-10-25
- Requirements: REQ-AND-015, REQ-AND-016, REQ-AND-018, REQ-SEC-001

## Context
The Pi's gateway serves plain HTTP and WebSocket on port 8000 and has no TLS (ADR-0005). Since
Android 9, an app targeting API 28 or later may not use cleartext traffic unless it says so, so the
app's REST calls and the voice console (both OkHttp) were refused outright. The Pi enforces API keys
once `MIA_API_KEY` is set (REQ-SEC-001), but the app had no way to enter one, and only the voice console
sent it.

## Decision
- The manifest sets `usesCleartextTraffic`, so the app can reach the Pi's plain-HTTP API. The owner
  chose this on 2026-10-25 over allowing cleartext in debug builds only, which would leave the release
  app unable to reach a Pi.
- The user enters the Pi's address and API key in Settings. The key is sent only in the
  `X-API-Key` header (REST, the telemetry WebSocket and the voice console), and only to the host that was
  entered with it. It is never put in a URL, never written to the audit log (which records only whether a
  key is set) and never printed by logging (`PiConnection.toString()` and the HTTP logger redact it).
- The key is stored in the app's private preferences. Android backups are off (`allowBackup=false`).

## Consequences
- Anyone who can read traffic on the network between the phone and the Pi can read the key. That is a
  private network, the Pi's own access point or the car's Wi-Fi, not the internet. A WPA2 passphrase on
  that network is the only protection until the Pi serves TLS.
- The permission is app-wide: the manifest cannot limit cleartext to the address typed at run time.
  The app contacts only the configured Pi, the MQTT broker (a raw TCP socket, unaffected by this setting)
  and Android's own services.
- Revisit when the Pi gets TLS or when the authentication ADR (#139) lands: remove the permission and
  require `https://`.

## Sources
`apps/android/app/src/main/AndroidManifest.xml`, `apps/android/app/src/main/java/cz/mia/app/core/networking/`,
`apps/rpi-backend/py-api/api/auth/dependencies.py`.
