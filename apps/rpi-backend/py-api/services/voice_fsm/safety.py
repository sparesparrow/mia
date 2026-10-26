"""The safety fragment that starts every spoken car warning, in every persona (ADR-0015, REQ-VOICE-019).

A fragment names the reading with its value and unit and then says what to do. No persona can change it or put
anything before it; a persona may only add one short sentence after it (``personas``). The wording and units
match the phone's warnings (``apps/android/.../core/rules/WarningText.kt``), whose limits decide when a warning
is raised: coolant above 105 °C, battery below 11.5 V or above 14.8 V, engine speed above 6000 rpm.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

SAFETY_FRAGMENTS: Dict[str, Dict[str, str]] = {
    "en": {
        "warning.coolant_high": "Coolant at {value} degrees. Stop when it is safe and switch the engine off.",
        "warning.battery_low": "Battery at {value} volts. Have the battery and charging checked.",
        "warning.battery_high": "Battery at {value} volts, above normal. Have the charging regulator checked.",
        "warning.rpm_high": "Engine speed {value} RPM. Ease off the throttle.",
    },
    "cs": {
        "warning.coolant_high": "Teplota motoru {value} stupňů. Zastavte, až to bude bezpečné, a vypněte motor.",
        "warning.battery_low": "Napětí baterie {value} voltu. Nechte zkontrolovat baterii a dobíjení.",
        "warning.battery_high": "Napětí baterie {value} voltu, nad normou. Nechte zkontrolovat regulátor dobíjení.",
        "warning.rpm_high": "Otáčky {value} za minutu. Uberte plyn.",
    },
}

WARNING_KEYS = frozenset(SAFETY_FRAGMENTS["en"])

# Said when a warning arrives that has no fragment yet, or no usable value: still a warning, never silence.
GENERIC_WARNING = {
    "en": "Car warning. Check the dashboard.",
    "cs": "Varování z auta. Podívejte se na přístroje.",
}

_DECIMAL = {"warning.battery_low", "warning.battery_high"}


def _value(key: str, value: Any, language: str) -> Optional[str]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if key in _DECIMAL:
        text = f"{value:.1f}"
        return text.replace(".", ",") if language == "cs" else text
    return str(int(value))


def render_fragment(key: str, params: Mapping[str, Any], language: str) -> str:
    """The fragment for warning ``key`` in ``language`` (English if that language has none)."""
    fragments = SAFETY_FRAGMENTS.get(language, SAFETY_FRAGMENTS["en"])
    template = fragments.get(key)
    value = _value(key, params.get("value"), language)
    if template is None or value is None:
        return GENERIC_WARNING.get(language, GENERIC_WARNING["en"])
    return template.format(value=value)
