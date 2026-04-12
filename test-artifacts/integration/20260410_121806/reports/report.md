# MIA Prototype Integration Harness

- Overall status: **fail**
- Scenario: `full-flow`
- Android device: `HT36TW903516`
- Raspberry Pi host: `192.168.200.134` (192.168.200.134)
- Android package: `cz.mia.app`

## Checks

| Check | Status | Message |
| --- | --- | --- |
| config.android_package | pass | Using Android package cz.mia.app and activity .MainActivity |
| config.network_topology | pass | Pi host resolves to 192.168.200.134 |
| local.command.adb | pass | /usr/bin/adb |
| local.command.ssh | pass | /usr/bin/ssh |
| local.command.curl | pass | /usr/bin/curl |
| local.command.bash | pass | /usr/bin/bash |
| android.device.selected | pass | Using Android device HT36TW903516 via USB |
| android.device.ready | pass | One |
| android.device.network | pass | Android Wi-Fi address 192.168.200.130 |
| android.device.root | warning | Root shell not confirmed via adb shell su -c id |
| pi.ssh.access | pass | Remote host reachable over SSH |
| pi.os.release | pass | Remote OS: kali 2025.3 |
| pi.systemd.available | pass | systemd available |
| pi.apt.available | pass | apt-get available |
| pi.sudo.noninteractive | pass | Passwordless sudo available |
| pi.bluetooth.adapter | pass | Bluetooth adapter visible |
| pi.deploy | skip | Pi deploy skipped by configuration |
| pi.service.bluetooth | pass | active |
| pi.service.zmq-broker | warning | activating |
| pi.service.mia-api | warning | activating |
| pi.service.mia-gpio-worker | warning | activating |
| pi.service.mia-ble-advertiser | fail | inactive |
| pi.service.mia-ble-obd | fail | inactive |
| pi.service.mia-serial-bridge | warning | inactive |
| pi.service.mia-obd-worker | warning | inactive |
| pi.api.status | pass | Pi /status responded |
| pi.api.features | warning | Pi /features unavailable |
| android.orchestrator | skip | Android run skipped by configuration |

## Recommendations

- Inspect the collected Pi journal logs and fix inactive systemd services before trusting Android results.
