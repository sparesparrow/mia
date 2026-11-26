# REQ-DEP-008: hardware_tested

- Date: 2026-11-26
- By: Claude Code (Opus 5.5) for sparesparrow, over SSH from the owner's phone
- State claimed: hardware_tested
- Build / commit: edb4a78af80f985c3176128ab0a7c4538b04eb20 (main after #298, #299, #300)

## Setup
- Raspberry Pi 4 Model B Rev 1.4, 1.8 GiB RAM, Debian GNU/Linux 13 (trixie), kernel 6.18.50+rpt-rpi-v8, Python 3.13.5,
  git 2.47.3. Installed in the prototype car (Audi A4 Cabriolet 8H); on the bench supply for this run, no OBD adapter
  or ESP32 attached (`lsusb`: USB hub only).
- Source checkout `~/mia-src` owned by `mia`, previously at 54accbd (17 commits behind main); install `/opt/mia` with an
  existing venv `/opt/mia/venv`, 14 MIA units installed and running.
- Before the run: config backup (`/etc/mia`, `/var/lib/mia`, unit files) to `~/backups/mia-pre-deploy-20261126-195953.tar.gz`
  (mode 600); `mia-citroen-bridge` disabled because the car is not a Citroën (it published simulated PSA telemetry).
- Because the checkout still held the pre-#298 script, `~/mia-src` was first brought to origin/main by hand as `mia`
  (`git fetch && git checkout --detach origin/main`), as the review of #298 recommends for the first run.

## Procedure
```bash
sudo MIA_SKIP_CLAUDE_TOOLING=1 MIA_DEPLOY_REF=origin/main bash ~/mia-src/tools/scripts/deploy-production-rpi.sh
```
`MIA_SKIP_CLAUDE_TOOLING=1` because three Claude Code sessions were running on the Pi. Then, on the Pi:
`systemctl list-units 'mia-*' zmq-broker`, `systemctl show -p NRestarts`, `stat` of `/opt/mia/bin`,
`/etc/mia/environment` keys, `hciconfig hci0`, `curl -H "X-API-Key: …" localhost:8000/status`, and the MIA Android app
(`cz.mia.app.debug`, built from b7e225a) pointed at the Pi over the phone's hotspot.

## Capture
Deploy log on the Pi: `~mia/mia-stage/20261126-195953/deploy.log` (189 lines; not committed, it lists the Pi's package
versions). Its milestones:

```
[INFO] Step 1: Bringing /home/mia/mia-src to origin/main...
[INFO] Deploying edb4a78
[INFO] Step 2: Setting up BLE services...
[INFO] Step 3: Installing code, venv and units...
Copying the code to /opt/mia...
Installing /home/mia/mia-src/apps/rpi-backend/py-api/requirements.txt into /opt/mia/venv...
Pointing /usr/local/bin/mia-python and MIA_PYTHON at /opt/mia/venv...
  - Installed zmq-broker.service … mia-obd-worker.service, mia-bt-agent.service (not enabled)
  - Updated mia-audio-capture.service … mia-wake-word.service (13 already-installed units)
MIA_SKIP_CLAUDE_TOOLING=1: leaving the Claude Code CLI and mcp-prompts as they are.
[INFO] Step 5: Restarting services, broker first...
[SUCCESS] API answers at http://127.0.0.1:8000/status
[SUCCESS] Deployment completed: edb4a78… (origin/main), recorded in /var/lib/mia/deployed.json
```

## Result
| Acceptance criterion | Observed |
|---|---|
| Unit paths exist, API imports from the install | all 14 enabled units `active running`, `NRestarts=0` 15 min after the deploy; `/status` → `healthy` |
| Venv gets the API's requirements; no system pip | installed into `/opt/mia/venv` only |
| `mia-python` / `MIA_PYTHON` run the venv; key kept; no PYTHONHOME | wrapper execs `/opt/mia/venv/bin/python`; `MIA_API_KEY` line kept (1), `MIA_PYTHON=/opt/mia/venv/bin/python`, no `PYTHONHOME` |
| A re-run keeps the venv | the existing venv was reused (no "Creating" line) |
| aarch64, Python 3.13 (Trixie) | as above, on the target Pi |
| Checkout brought to a pinned commit as its owner | `~/mia-src` detached at edb4a78, owned by `mia`; no dubious-ownership error |
| Installed units refreshed, broker restarted first | 13 non-core units updated, none newly enabled; broker active 20:03:25, API 20:04:14 |
| `/opt/mia/bin` root-owned | `root:root 755` directory and tools |
| Deploy does not make Bluetooth discoverable | **Partly.** The deploy scripts no longer run `piscan`, but the adapter is `PSCAN ISCAN` afterwards because `services/ble_advertiser.py` runs `hciconfig hci0 piscan` itself when `mia-ble-advertiser` starts. Not pairable (`Pairable: no`). Tracked as an issue. |

Also observed: `mia-obd-worker` logged 0 "Operation not supported" lines after the restart (it logged one every 100 ms
before #299). The phone app showed "Pi online" and Cycle 1 telemetry (simulation source) and the API log showed
`WebSocket /ws/telemetry [accepted]` from the phone once the app had the API key (403 before).

Not covered by this run: a first install on a clean SD card; the failure paths (a fetch error, differing local changes,
a crash-looping unit — the last one is not caught yet, see the hardening follow-up to #298).

## Safety
No vehicle bus was attached; the deploy installs and restarts services only. The VAG bridge runs with
`VAG_ENABLE_UDS_POLLING=false` and read services 19/22 only; nothing can transmit or actuate.
