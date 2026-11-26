# 0026. MQTT broker: one user per client role, with a topic ACL

- Status: Proposed
- Date: 2026-11-26
- Requirements: REQ-SEC-004

## Context
ADR-0003 keeps MQTT at the edges, and ADR-0017 makes `spec/interfaces/topics.md` the topic contract.
`topics.md` says every topic requires authentication, but:

- The default broker configs (`infra/containers/mosquitto/mosquitto.conf`,
  `infra/edge/pi-gateway/services/mosquitto/mosquitto.conf`) allow anonymous clients, and the gateway listens on
  0.0.0.0.
- The secure overlay (`docker-compose.secure.yml` with `secure.conf`, used by `bootstrap-raspios.sh` when
  `SECURE=1`) refuses anonymous clients, but nothing creates its password file, and a client that logs in may publish
  to any topic, `vehicle/cmd/{vin}/io` included.
- Clients now include the phone assistant (android-assistant's `mqtt_publish`), which publishes `mia/lights/*`
  without a human confirmation and other `mia/` and `zigbee2mqtt/` topics after one (#282). A confirmation enforced
  only in the client is no protection against another process on the network.

The wider authentication decision for the API, WebSocket, Android and web clients is #139. This record covers only
the broker.

## Decision
- The secure broker has one user per client role, and an ACL file
  (`infra/edge/pi-gateway/services/mosquitto/acl`) gives each role only the topics it publishes:

  | Role | May publish |
  |---|---|
  | `pi-backend` | `vehicle/#`, `device/#`, `system/#`, `mia/#`, `hardware/#`; the only role that may send `vehicle/cmd/{vin}/io` |
  | `android` | `vehicle/telemetry/+/obd`, `vehicle/alerts/+`, `vehicle/events/+/anpr`, `device/health/+`, `device/metrics/+`, `system/session/+` |
  | `esp32-obd` | `mia/telemetry/#`, `mia/alerts/#` (legacy prefixes, ADR-0017) |
  | `phone-assistant` | `mia/lights/#` only |

  A user or topic not in the file gets nothing: mosquitto drops the publish and refuses the subscription.
- The phone assistant's confirm-class topics are refused by the broker. A human-confirmed command goes through the
  Pi, which holds the `pi-backend` role, not straight to MQTT.
- `infra/edge/pi-gateway/scripts/mqtt-users.sh` creates the users: a random password per role, hashed into
  `services/mosquitto/passwords/credentials`, the plain password in `<role>.secret` (mode 600) for configuring that
  client. It never prints a password; `passwords/` is git-ignored.
- The ACL changes with the contract: a new topic in `topics.md` that a client publishes gets its ACL line in the
  same change.

## Consequences
- With the secure overlay, a device on the car's network cannot send vehicle commands or switch the lights without
  credentials, and a phone or ESP32 cannot send vehicle commands at all.
- Not every client can log in yet. The Android app reads `MIA_MQTT_USERNAME` and `MIA_MQTT_PASSWORD`; the ESP32 OBD
  firmware (`ai_servis_mqtt.c`) and the Python publishers (flatbuffers gateway, camera service, hardware bridge)
  send no credentials. Until they do, they cannot use the secure broker; the default (anonymous) broker stays as it
  is. These are follow-up issues, as is the legacy-topic migration (#191) and the light topics' place in the
  contract (#282).
- Nothing in this repository consumes `mia/lights/*` yet (#282); the ACL allows it for the phone assistant only.
- `tests/integration/test_mqtt_acl.py` runs a real mosquitto with these settings in CI (the Python test job installs
  `mosquitto` and `mosquitto-clients`).

## Sources
`infra/edge/pi-gateway/services/mosquitto/{acl,secure.conf}`, `infra/edge/pi-gateway/docker-compose.secure.yml`,
`infra/edge/pi-gateway/scripts/mqtt-users.sh`, `spec/interfaces/topics.md`, ADR-0003, ADR-0017, issues #139, #191,
#282, `apps/android/.../core/background/MQTTTopics.kt` and `MQTTManager.kt`,
`apps/esp32/firmware-obd/components/ai_servis_mqtt/ai_servis_mqtt.c`, android-assistant `mcp/server.py`
(`MQTT_DIRECT`, `MQTT_CONFIRM`).
