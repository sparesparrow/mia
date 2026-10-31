# Raspberry Pi 4B GPIO pin map (car install)

> **Status: design guidance, not hardware-validated.** Nothing in this document has been
> tested on a physical Pi or in a vehicle. Requirement: REQ-HW-010 (software guard only);
> REQ-CAR-001 (ignition shutdown, tested with a mocked GPIO). Check every connection with a
> multimeter before powering the Pi.

The Pi 4B GPIO is **3.3 V logic and is not 5 V tolerant**. A 12 V car line (nominally 12-14.4 V, with
load-dump spikes far higher) connected directly to a GPIO pin destroys the SoC.

## Software guard

`hardware/gpio_policy.py` is enforced by the REST API (`/gpio/configure`, `/gpio/set`, `/gpio/{pin}`),
by `hardware/gpio_worker.py` and by the simulation client.

| Result | HTTP |
| --- | --- |
| Pin or direction denied by the policy | 403 |
| Malformed pin (not BCM 0-27), direction or value | 422 |
| GPIO worker did not answer in 5 s | 504 |
| GPIO worker answered with an error | 502 |

Override the default list with `MIA_GPIO_POLICY_FILE` (YAML) or `MIA_GPIO_ALLOWED_PINS`:

```yaml
# MIA_GPIO_POLICY_FILE=/etc/mia/gpio-policy.yaml
pins:
  4: [input, output]
  5: [input]
```

```bash
MIA_GPIO_ALLOWED_PINS="4:io,5:i"   # i = input, o = output
```

The file replaces the default list rather than extending it. An invalid override denies every pin and
logs an error. The reserved pins below and any output on the ignition pin cannot be allowed by an
override. Set the variables for both `mia-api` and `mia-gpio-worker`; the worker checks again.

## BCM pin roles

| BCM | Physical | Role | Policy |
| --- | --- | --- | --- |
| 0, 1 | 27, 28 | ID EEPROM (HAT identification) | always denied |
| 2, 3 | 3, 5 | I2C1 SDA/SCL: BME280, SHT30, ADS1115 (`hardware/sensors_i2c.py`) | always denied |
| 7-11 | 26, 24, 21, 19, 23 | SPI0 CE1, CE0, MISO, MOSI, SCLK | always denied |
| 14, 15 | 8, 10 | UART0 TXD/RXD (serial console) | always denied |
| 17 | 11 | Ignition sense (optocoupler), read by `services/power_monitor.py` | input only |
| 4, 5, 6, 12, 13, 16, 18-27 except 17 | various | General purpose | input and output |

BCM 18 doubles as PWM0 and PCM clock; BCM 12/13 as PWM. Keep them for general use only if no audio
HAT or PWM device is attached. The default list is a starting point: trim it to the pins your
harness actually uses via the override.

## Ignition on BCM17

`services/power_monitor.py` configures BCM17 as an input with the internal pull-up and, on a stable
falling edge (2 s debounce), publishes a shutdown notice, waits `SHUTDOWN_DELAY` and runs
`systemctl poweroff`. Pin and delay come from `IGNITION_GPIO_PIN` and `SHUTDOWN_DELAY`.

Wiring as described in the `power_monitor.py` header:

```
ACC 12 V --[1 kOhm]-- optocoupler LED+ ; LED- -- chassis GND
Pi 3V3 --[10 kOhm]-- BCM17 --- optocoupler collector ; emitter -- Pi GND
```

`power_monitor.py` treats HIGH as ignition on and LOW as ignition off, and fires on the falling edge.
**That header and this wiring disagree:** with the collector tied to BCM17 and a pull-up, a conducting
optocoupler (ignition on) pulls the pin LOW, so ignition off reads HIGH and no falling edge happens
at key-off. Before enabling the service, bench-test the stage you build and make sure the pin reads
HIGH with ignition on and falls to LOW at key-off (for example an inverting driver stage). Do not
trust the header diagram.

Use an optocoupler rated for the 12 V line with a series resistor
sized for the LED current (a few mA), and a series diode or TVS on the ACC side against reverse
polarity and transients. The optocoupler isolates the car ground from the Pi.

## Sensing 12 V

Never connect a 12 V line to a GPIO. Two accepted ways:

1. **Divider plus ADC.** A resistor divider (for example 33 kOhm / 10 kOhm, about 3.3 V at 14.2 V;
   recompute for your tolerance) feeding an ADS1115 input over I2C (`ADS1115Sensor` in
   `hardware/sensors_i2c.py`). The ADS1115 supply is 3.3 V so its inputs must never exceed 3.3 V:
   add a clamp (Zener or Schottky pair) at the input. Calibrate against a multimeter.
2. **Optocoupler** for on/off signals, as for the ignition above.

## Relays and loads

Drive loads through a **relay or driver board** (opto-isolated or with a transistor stage), never
from a GPIO directly: a pin sources only a few mA and is 3.3 V.

- Flyback protection across every inductive load (relay coil, solenoid, motor): a diode, or use a
  board that includes one.
- A **fuse on every 12 V branch** sized for the wire, close to the source.
- Power the Pi from a proper 12 V to 5 V converter rated for automotive transients (see
  [Wiring and power](../wiring.md)), not from a GPIO or OBD pin 16.
- Make outputs fail safe: choose the relay contact (NO or NC) so a Pi crash or poweroff leaves the
  load in its safe state. Boot-time pin states are undefined for a moment.

## Enabling `mia-power-monitor`

`mia-power-monitor` runs `systemctl poweroff` on a stable BCM17 falling edge. With no optocoupler
wired, the internal pull-up keeps the pin HIGH, but a floating or mis-wired input, a bad ground or
an inverted stage can power the Pi off on its own, or never. **Enable and start the service only
once the ignition wiring exists and has been checked.** `tools/scripts/deploy-mia-rpi.sh` enables
it by default, so run `sudo systemctl disable --now mia-power-monitor` on a bench Pi without that
wiring.

## What has and has not been checked

| Checked in CI (simulation) | Not checked |
| --- | --- |
| The policy, its overrides, and the HTTP status codes | Behaviour on physical Pi pins |
| The ignition callback with a mocked GPIO and mocked `poweroff` | Optocoupler or divider values, polarity, noise |
| | Anything in a real vehicle |
