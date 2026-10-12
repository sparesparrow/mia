"""The fixed table of actions and what silence means for each (ADR-0012).

The class of a part comes from this table, keyed by its name. A part may be labelled stricter by the
caller, never looser, and a name that is not in the table is treated as forbidden: a typo or a missing
entry fails closed. Adding an action is a reviewed one-line change here.
"""

from __future__ import annotations

from typing import Dict, Mapping

from .types import DICTATE, SAVE_NOTE, ActionClass

_RANK = {
    ActionClass.READ: 0,
    ActionClass.COMFORT: 1,
    ActionClass.NOTE: 2,
    ActionClass.MESSAGE: 3,
    ActionClass.FORBIDDEN: 4,
}

ACTION_CLASSES: Dict[str, ActionClass] = {
    # Readings from the car
    "read.voltage": ActionClass.READ,
    "read.coolant": ActionClass.READ,
    "read.rpm": ActionClass.READ,
    "read.ignition": ActionClass.READ,
    "dtc.read": ActionClass.READ,
    # The router's existing routes (voice_command_router.ROUTES labels)
    "system status": ActionClass.READ,
    "processor temperature": ActionClass.READ,
    "engine telemetry": ActionClass.READ,
    "connected devices": ActionClass.READ,
    "feature list": ActionClass.READ,
    "turn lights on": ActionClass.COMFORT,
    "turn lights off": ActionClass.COMFORT,
    # Comfort
    "lights.on": ActionClass.COMFORT,
    "lights.off": ActionClass.COMFORT,
    "volume.up": ActionClass.COMFORT,
    "volume.down": ActionClass.COMFORT,
    # Notes
    DICTATE: ActionClass.NOTE,
    SAVE_NOTE: ActionClass.NOTE,
    # Messages and calls: only ever on an explicit yes
    "message.send": ActionClass.MESSAGE,
    "call.place": ActionClass.MESSAGE,
    # Writes to a control unit: refused (ADR-0006)
    "dtc.clear": ActionClass.FORBIDDEN,
    "dpf.regenerate": ActionClass.FORBIDDEN,
    "ecu.write": ActionClass.FORBIDDEN,
}


def stricter(a: ActionClass, b: ActionClass) -> ActionClass:
    return a if _RANK[a] >= _RANK[b] else b


def effective_class(
    name: str, labelled: ActionClass, table: Mapping[str, ActionClass] = ACTION_CLASSES
) -> ActionClass:
    """The class the machine acts on: the stricter of the table and the label, forbidden if unknown."""
    known = table.get(name)
    return ActionClass.FORBIDDEN if known is None else stricter(known, labelled)
