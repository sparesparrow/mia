# Pi cold boot without the Wi-Fi hotspot (manual test, 2026-10-31)

Manual run, not a CI test. It claims nothing in `spec/requirements/`: no requirement covers
"the Pi joins the phone's hotspot", and ADR-0010 needs a linked automated test for any state above
`implemented_and_ci_tested`. See the follow-up issue for making it repeatable.

## Setup
- Raspberry Pi 4B (1.8 GB), Raspberry Pi OS (Debian) 6.18, `/opt/mia` at `4967064` (main), the five MIA
  services enabled (`zmq-broker`, `mia-api`, `mia-gpio-worker`, `mia-obd-worker`, `mia-serial-bridge`).
- Wi-Fi client profile `MIA` (netplan -> NetworkManager, autoconnect on, retries at the default).
- The network `MIA` is the Wi-Fi hotspot of a rooted Motorola G54 (Android 15). The test computer was on the same
  hotspot and reached the Pi over it.
- OBD is emulated; there is no microphone, camera or GPIO wiring on this Pi.

## Procedure
1. Check the services and note the boot id.
2. `systemctl reboot` on the Pi.
3. Ten seconds later, switch the phone's Wi-Fi hotspot off (Settings > Hotspot & tethering).
4. Keep it off for 180 s.
5. Switch it on again and measure how long the Pi takes to answer ping and the API.

## Result
| Time (UTC) | Event |
|---|---|
| 03:21:51 | reboot issued |
| 03:22:13 | hotspot off (Pi booting) |
| 03:22:20 | `mia-api` started, about 29 s after boot, with no network |
| 03:25:24 | hotspot on |
| 03:25:39 | wlan0 associated to `MIA` and activated, 15 s later, same IP as before |

- All five services active after the reboot; `GET /status` healthy, one device, `get_throttled` = `0x0`.
- NetworkManager stayed in `disconnected` for the whole gap and joined by itself; no manual step was needed.
- The Android app was not part of this run.

## Not proven
- A gap of 180 s only. NetworkManager only counts activation attempts, which do not happen while no `MIA` access
  point is visible, so longer gaps are expected to behave the same but were not run.
- A hotspot that is visible but refuses (wrong password, full) is a different case and was not tested.
- Whether the car's real start-up order (Pi powered on ignition, phone later) matches this; power loss at key-off
  was not tested (see issue #202 for the ignition monitor).
- Boot-time services were not checked for what happens when the clock is wrong; the Pi has no RTC.

## Raw log
```
03:21:51 start
03:21:51 reboot issued
03:22:13 hotspot wanted=false now=false
03:22:13 hotspot off; holding 180s
03:25:24 hotspot wanted=true now=true
03:25:24 hotspot on; done
```
Pi journal (local time, UTC+1): `04:22:20` wlan0 `unavailable -> disconnected`; `04:25:39` associating to `MIA`;
`04:25:40` `device activated`.

## Side findings
- `/lib/netplan/00-network-manager-all.yaml` permissions are "too open" (a netplan warning at every boot).
- `eth0` keeps failing DHCP every 45 s because nothing serves it; harmless but noisy in the journal.
