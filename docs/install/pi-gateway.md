# Raspberry Pi install (supported)

> **Audience**: Ops engineers, deployment engineers

The Raspberry Pi 4B is MIA's primary runtime ([ADR-0005](../spec/decisions/0005-raspberry-pi-edge-with-fastapi-gateway.md)).
Services run as systemd units from `/opt/mia`; clients reach only the FastAPI gateway on port 8000.
Background and troubleshooting: [Production deployment](../PRODUCTION_DEPLOYMENT.md).

- Hardware: Raspberry Pi 4B, 32 GB+ SD or NVMe, 12 V → 5 V buck converter.
- OS: Raspberry Pi OS 64-bit.
- Vehicle side: the ESP32 runs the default (listen-only) firmware and the CAN transceiver's `TXD` line stays
  disconnected ([ADR-0006](../spec/decisions/0006-passive-vehicle-access-by-default.md),
  [installer checklist](installer-checklist.md)).

## Steps

1. Deploy from a checkout of this repository on the Pi. Keep the checkout outside `/opt/mia` (for example
   `~/mia-src`, owned by the `mia` user), so the install can keep `/opt/mia/bin` root-owned
   ([ADR-0023](../spec/decisions/0023-phone-driven-software-update.md)):
   ```bash
   git clone https://github.com/sparesparrow/mia.git ~/mia-src
   sudo ~/mia-src/tools/scripts/deploy-production-rpi.sh
   ```
   The script:
   - brings the checkout to `origin/main` (or `MIA_DEPLOY_REF`), running git as the checkout's owner. It stops,
     listing the paths, when local changes differ from that commit; it never deletes untracked data;
   - copies the code to `/opt/mia`;
   - installs the API's requirements (`apps/rpi-backend/py-api/requirements.txt`) into the venv
     `/opt/mia/venv`, never into the system Python;
   - points `/usr/local/bin/mia-python` and `MIA_PYTHON` in `/etc/mia/environment` at that venv;
   - installs and enables the core systemd units from `infra/systemd/`, and refreshes every other MIA unit that is
     already installed (voice, BLE, bridges) without enabling it;
   - restarts every enabled MIA unit, the broker first, then checks that the API answers and no unit failed, and
     records the commit in `/var/lib/mia/deployed.json`.

   It works with the Python of Raspberry Pi OS Bookworm (3.11) and Trixie (3.13). Running it again updates the
   code and keeps the venv and the API key. Switches: `MIA_DEPLOY_REF=<tag or commit>`, `MIA_DEPLOY_SKIP_FETCH=1`
   (deploy the checkout as it is), `MIA_NO_RESTART=1`, `MIA_SKIP_CLAUDE_TOOLING=1`. `sudo` resets the environment,
   so pass them after it: `sudo MIA_DEPLOY_REF=v2.3.0 ~/mia-src/tools/scripts/deploy-production-rpi.sh`.

2. Set an API key. The units read `/etc/mia/environment`; these commands replace only the `MIA_API_KEY` line and
   keep the `MIA_PYTHON` line the deploy wrote:
   ```bash
   sudo mkdir -p /etc/mia && sudo touch /etc/mia/environment && sudo chmod 600 /etc/mia/environment
   sudo sed -i '/^MIA_API_KEY=/d' /etc/mia/environment
   python3 -c "import secrets; print('MIA_API_KEY=mia_api_' + secrets.token_hex(16))" | sudo tee -a /etc/mia/environment
   ```

3. Start the broker first, then the API and the workers:
   ```bash
   sudo systemctl start zmq-broker
   sudo systemctl start mia-api mia-gpio-worker mia-serial-bridge mia-obd-worker
   systemctl status zmq-broker mia-api
   ```

4. Check the API with the key:
   ```bash
   curl -H "X-API-Key: <key from /etc/mia/environment>" http://<pi-ip>:8000/status
   ```

5. On the phone, open Settings in the MIA app and enter the Pi's address and the same key
   ([ADR-0016](../spec/decisions/0016-android-reaches-the-pi-over-plain-http.md)). The Cycle 1 card on the
   Dashboard then shows the Pi's telemetry.

## Updating an installed Pi from the phone

The steps above are the one-time bootstrap. Once a Pi is installed, the app can update it
([ADR-0023](../spec/decisions/0023-phone-driven-software-update.md)):

1. On the Pi, once: `sudo bash infra/deploy/rpi/install-update-access.sh`, then `sudo systemctl reload ssh`.
   It creates the `mia-update` user, its one-command sudoers rule and the sshd block. The release you update to
   must contain `bin/mia-apply-update` (it is in the backend bundle from the first release after this change); install
   that file once by hand (`sudo install -m 755 bin/mia-apply-update /opt/mia/bin/`) or re-run the deploy script.
2. Pair the phone. A paired key is root on the Pi by design (it runs the update tool as root), so pairing is done
   by an administrator on the Pi, not through the API. In the app: Settings > Software update shows the phone's public key
   and the command; run it in your SSH session:
   `sudo /opt/mia/bin/mia-update-pair add pixel '<public key>'` (also `list` and `remove <label>`).
   The app can check the result with `GET /admin/update/pair` (admin API key; labels and fingerprints only).
3. In the app: edit the configuration, then Update the Pi.
4. To go back: `sudo /opt/mia/bin/mia-apply-update --rollback` on the Pi. If an update fails during the deploy
   step, files may be half-copied and there is no automatic rollback; `--rollback` returns to the package before
   the current one, so re-run the update with the version you had instead.

An update that changes `apps/rpi-backend/py-api/requirements.txt` is refused; run the full install once.

## Not covered here

`infra/edge/pi-gateway` is an older Docker stack (Mosquitto, mDNS advertiser and simulators) from before
the systemd runtime. It is not covered by the requirements registry and is not how the car install runs; it is
still used by [Dev without a Pi](dev-docker.md).
