# Raspberry Pi: deploy, update and operate

> **Audience**: Ops engineers working on an installed MIA Pi

The first install is [Raspberry Pi install (supported)](../install/pi-gateway.md). This page covers what comes after:
updating, checking and troubleshooting a running Pi. Earlier revisions of this page described a manual install from
the old `ai-servis` repository with `rpi/requirements.txt` and `pip --break-system-packages`; none of that applies any
more.

## Layout on the Pi

| Path | What it is |
|---|---|
| `~/mia-src` | Source checkout owned by `mia`. Deploys run from here. |
| `/opt/mia` | The install: code the units run, the venv (`/opt/mia/venv`), run-time data (`/opt/mia/data`, Piper voices). |
| `/opt/mia/bin` | Root-owned tools (`mia-apply-update`, `mia-update-pair`, `mia-enroll`, `mia-phone-registry`), [ADR-0023](../../spec/decisions/0023-phone-driven-software-update.md). |
| `/etc/mia/environment` | `EnvironmentFile` of every unit: `MIA_API_KEY`, `MIA_PYTHON` and per-install settings. Mode 600. |
| `/etc/systemd/system/{zmq-broker,mia-*}.service` | Units copied from `infra/systemd/`. |
| `/var/lib/mia/deployed.json` | The ref and commit of the last successful deploy. |

Do not deploy from a checkout at `/opt/mia` itself: its `bin/` would belong to the checkout's owner, who could then
replace the tool that the phone's sudo rule runs as root.

## Update

```bash
ssh mia@<pi>
sudo ~/mia-src/tools/scripts/deploy-production-rpi.sh
```

The script brings `~/mia-src` to `origin/main`, installs, restarts every enabled MIA unit (broker first) and checks
the API. It exits non-zero when the fetch fails, when local changes in the checkout differ from the target commit
(it lists them and changes nothing), when the API does not answer within 60 s, or when a MIA unit has failed.

| Variable (after `sudo`) | Effect |
|---|---|
| `MIA_DEPLOY_REF=v2.3.0` | Deploy a tag, branch or commit instead of `origin/main`. |
| `MIA_DEPLOY_SKIP_FETCH=1` | Deploy the checkout as it is. |
| `MIA_NO_RESTART=1` | Install only; restart later yourself, `zmq-broker` first. |
| `MIA_SKIP_CLAUDE_TOOLING=1` | Do not run `claude update` and `npm update -g @sparesparrow/mcp-prompts`. |

From another machine, `tools/scripts/deploy-mia-rpi.sh` syncs a working tree and installs its own package list
(REQ-DEP-003); merging the two entry points is issue #132. The phone can update an installed Pi with a release
package ([pi-gateway.md, "Updating an installed Pi from the phone"](../install/pi-gateway.md)).

## Rollback

Deploy the previous commit: it is in `/var/lib/mia/deployed.json` before the update, or in `git -C ~/mia-src reflog`.

```bash
sudo MIA_DEPLOY_REF=<previous sha> ~/mia-src/tools/scripts/deploy-production-rpi.sh
```

## Check

```bash
systemctl list-units 'mia-*' zmq-broker --no-pager
systemctl --failed
curl -H "X-API-Key: $(sudo sed -n 's/^MIA_API_KEY=//p' /etc/mia/environment)" http://localhost:8000/status
cat /var/lib/mia/deployed.json
journalctl -u mia-api -n 50 --no-pager
```

## Per-vehicle settings

Settings that belong to one car go into `/etc/mia/environment` on that Pi, never into the repository. The car's
capabilities and survey data live in `apps/rpi-backend/config/vehicles/`. On a car that is not a Citroën, keep
`mia-citroen-bridge` disabled: it publishes simulated PSA telemetry when no adapter answers.

```bash
sudo systemctl disable --now mia-citroen-bridge
```

## Troubleshooting

- **A unit fails to start**: `journalctl -u <unit> -n 50 --no-pager`. Python import errors usually mean the deploy
  was interrupted; run it again.
- **The API answers 401**: the client's key differs from `MIA_API_KEY` in `/etc/mia/environment`.
- **Serial adapters**: `ls -l /dev/ttyUSB* /dev/obd2`; the udev rules in `infra/deploy/rpi/udev/` create `/dev/obd2`
  for known adapters. The `mia` user is in `dialout`.
- **The journal grows fast**: `journalctl --disk-usage`; a unit that logs in a loop shows in
  `journalctl --since -10min | awk '{print $5}' | sort | uniq -c | sort -rn | head`.

## Backup

```bash
sudo tar -czf mia-backup-$(date +%F).tar.gz /etc/mia /var/lib/mia /opt/mia/data
```
