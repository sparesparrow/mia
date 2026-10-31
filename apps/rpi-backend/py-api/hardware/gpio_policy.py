"""GPIO pin policy: which BCM pins the API and the GPIO worker may touch, and how.

Design guidance, not hardware-validated. The Raspberry Pi 4B GPIO is 3.3 V and NOT
5 V tolerant; see docs/hardware/gpio-pin-map.md for the wiring rules.

Self-contained on purpose (stdlib + optional PyYAML): it is imported by the API
(``from hardware import gpio_policy``) and by ``hardware/gpio_worker.py`` run as a
script (``import gpio_policy``).

Policy sources, strongest first:
  1. Hard-deny set (not overridable): ID EEPROM 0/1, I2C 2/3, SPI0 7-11, UART 14/15
     and everything outside BCM 0-27.
  2. The ignition pin (``IGNITION_GPIO_PIN``, default 17) is input-only, always.
  3. ``MIA_GPIO_POLICY_FILE`` (YAML) replaces the default allowlist::

         pins:
           4: [input, output]
           17: [input]

     or ``MIA_GPIO_ALLOWED_PINS`` (compact form) ``"4:io,5:o,17:i"``. The file wins
     when both are set.
  4. Default allowlist of general-purpose pins.

An invalid override fails closed: every pin is denied and the error is logged.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, FrozenSet, Optional

logger = logging.getLogger(__name__)

INPUT = "input"
OUTPUT = "output"
DIRECTIONS = (INPUT, OUTPUT)

MAX_BCM_PIN = 27

HARD_DENIED: Dict[int, str] = {
    0: "ID EEPROM (ID_SD)",
    1: "ID EEPROM (ID_SC)",
    2: "I2C1 SDA (sensors, ADS1115)",
    3: "I2C1 SCL (sensors, ADS1115)",
    7: "SPI0 CE1",
    8: "SPI0 CE0",
    9: "SPI0 MISO",
    10: "SPI0 MOSI",
    11: "SPI0 SCLK",
    14: "UART0 TXD (serial console)",
    15: "UART0 RXD (serial console)",
}

DEFAULT_IGNITION_PIN = 17

DEFAULT_ALLOWED: FrozenSet[int] = frozenset({4, 5, 6, 12, 13, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27})

DENIED_PREFIX = "GPIO policy: "


class GPIOPolicyError(ValueError):
    """The policy configuration is invalid."""


class PinInvalid(ValueError):
    """The pin or direction value is malformed (HTTP 422)."""


class PinDenied(PermissionError):
    """The pin or direction is not allowed by the policy (HTTP 403)."""


def ignition_pin() -> int:
    try:
        return int(os.environ.get("IGNITION_GPIO_PIN", str(DEFAULT_IGNITION_PIN)))
    except ValueError:
        return DEFAULT_IGNITION_PIN


def _validate_pin_number(pin) -> int:
    if isinstance(pin, bool) or not isinstance(pin, int):
        raise PinInvalid(f"pin must be an integer, got {pin!r}")
    if pin < 0 or pin > MAX_BCM_PIN:
        raise PinInvalid(f"pin {pin} is outside BCM 0-{MAX_BCM_PIN}")
    return pin


class GPIOPolicy:
    def __init__(self, allowed: Dict[int, FrozenSet[str]], ignition: int = DEFAULT_IGNITION_PIN):
        self.ignition = ignition
        self._allowed: Dict[int, FrozenSet[str]] = {}
        for pin, dirs in allowed.items():
            try:
                _validate_pin_number(pin)
            except PinInvalid as exc:
                raise GPIOPolicyError(str(exc)) from None
            if pin in HARD_DENIED:
                raise GPIOPolicyError(f"pin {pin} is reserved ({HARD_DENIED[pin]}) and cannot be allowed")
            if not dirs or set(dirs) - set(DIRECTIONS):
                raise GPIOPolicyError(f"pin {pin}: invalid directions {sorted(dirs)}")
            self._allowed[pin] = frozenset(dirs)
        # The ignition pin is a system input: never an output, whatever the override says.
        if ignition in self._allowed:
            self._allowed[ignition] = frozenset({INPUT})

    def allowed_directions(self, pin: int) -> FrozenSet[str]:
        return self._allowed.get(pin, frozenset())

    def check(self, pin, direction) -> int:
        """Return the pin if ``direction`` ('input'/'output') is allowed, else raise.

        PinInvalid -> malformed value (422); PinDenied -> valid but not permitted (403).
        """
        pin = _validate_pin_number(pin)
        if direction not in DIRECTIONS:
            raise PinInvalid(f"direction must be one of {list(DIRECTIONS)}, got {direction!r}")
        if pin in HARD_DENIED:
            raise PinDenied(f"{DENIED_PREFIX}pin {pin} is reserved: {HARD_DENIED[pin]}")
        if pin == self.ignition and direction != INPUT:
            raise PinDenied(f"{DENIED_PREFIX}pin {pin} is the ignition input; output is denied")
        if direction not in self.allowed_directions(pin):
            raise PinDenied(f"{DENIED_PREFIX}pin {pin} does not allow {direction}")
        return pin

    def check_read(self, pin) -> int:
        """Reading is allowed on any pin that allows input or output."""
        pin = _validate_pin_number(pin)
        if pin in HARD_DENIED:
            raise PinDenied(f"{DENIED_PREFIX}pin {pin} is reserved: {HARD_DENIED[pin]}")
        if not self.allowed_directions(pin):
            raise PinDenied(f"{DENIED_PREFIX}pin {pin} is not in the allowlist")
        return pin

    def as_dict(self) -> Dict[int, list]:
        return {p: sorted(d) for p, d in sorted(self._allowed.items())}


def _parse_directions(value) -> FrozenSet[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        raise GPIOPolicyError(f"directions must be a list, got {value!r}")
    dirs = set()
    for item in value:
        if item not in DIRECTIONS:
            raise GPIOPolicyError(f"unknown direction {item!r}")
        dirs.add(item)
    return frozenset(dirs)


def _parse_compact(text: str) -> Dict[int, FrozenSet[str]]:
    letters = {"i": INPUT, "o": OUTPUT}
    result: Dict[int, FrozenSet[str]] = {}
    for item in filter(None, (s.strip() for s in text.split(","))):
        pin_text, sep, flags = item.partition(":")
        try:
            pin = int(pin_text)
        except ValueError:
            raise GPIOPolicyError(f"bad pin in MIA_GPIO_ALLOWED_PINS: {item!r}") from None
        if not sep or not flags or any(c not in "io" for c in flags.lower()):
            raise GPIOPolicyError(f"bad directions in MIA_GPIO_ALLOWED_PINS: {item!r} (use i, o or io)")
        result[pin] = frozenset(letters[c] for c in flags.lower())
    if not result:
        raise GPIOPolicyError("MIA_GPIO_ALLOWED_PINS is empty")
    return result


def _load_file(path: str) -> Dict[int, FrozenSet[str]]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise GPIOPolicyError("PyYAML is required for MIA_GPIO_POLICY_FILE") from exc
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except OSError as exc:
        raise GPIOPolicyError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise GPIOPolicyError(f"cannot parse {path}: {exc}") from exc
    pins = data.get("pins") if isinstance(data, dict) else None
    if not isinstance(pins, dict) or not pins:
        raise GPIOPolicyError(f"{path}: expected a non-empty 'pins' mapping")
    result: Dict[int, FrozenSet[str]] = {}
    for key, value in pins.items():
        if isinstance(key, bool) or not isinstance(key, int):
            raise GPIOPolicyError(f"{path}: pin key {key!r} is not an integer")
        result[key] = _parse_directions(value)
    return result


def build_policy(env=None) -> GPIOPolicy:
    """Build the policy from the environment; raises GPIOPolicyError when invalid."""
    env = os.environ if env is None else env
    ignition = ignition_pin()
    path = env.get("MIA_GPIO_POLICY_FILE", "").strip()
    compact = env.get("MIA_GPIO_ALLOWED_PINS", "").strip()
    if path:
        allowed = _load_file(path)
    elif compact:
        allowed = _parse_compact(compact)
    else:
        allowed = {pin: frozenset(DIRECTIONS) for pin in DEFAULT_ALLOWED}
        allowed[ignition] = frozenset({INPUT})
    return GPIOPolicy(allowed, ignition)


_policy: Optional[GPIOPolicy] = None


def get_policy() -> GPIOPolicy:
    """Cached process-wide policy; an invalid configuration fails closed (deny all)."""
    global _policy
    if _policy is None:
        try:
            _policy = build_policy()
        except GPIOPolicyError as exc:
            logger.error("Invalid GPIO policy configuration, denying every pin: %s", exc)
            _policy = GPIOPolicy({}, ignition_pin())
    return _policy


def reset_policy() -> None:
    """Drop the cached policy (tests, config reload)."""
    global _policy
    _policy = None
