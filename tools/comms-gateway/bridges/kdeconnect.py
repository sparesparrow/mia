"""
bridges/kdeconnect.py — KDE Connect helper
──────────────────────────────────────────
SMS gateway via Moto G15 or Windows laptop SIM.
Notifications, sharing, and ping to any paired device.
"""

import asyncio
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import KDECONNECT_MOTO_ID, KDECONNECT_WINDOWS_ID


class SimDevice(Enum):
    MOTO   = KDECONNECT_MOTO_ID
    WINDOWS = KDECONNECT_WINDOWS_ID


def _kdeconnect(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["kdeconnect-cli", *args], capture_output=True, text=True)


def send_sms(destination: str, message: str, device: SimDevice = SimDevice.MOTO) -> bool:
    """Send SMS via KDE Connect through the phone's SIM card."""
    r = _kdeconnect("-d", device.value, "--send-sms", message, "--destination", destination)
    return r.returncode == 0


def send_notification(device_id: str, title: str, body: str) -> bool:
    """Push a notification to a KDE Connect device."""
    # KDE Connect uses share-text for simple notifications (no direct notif push from CLI)
    r = _kdeconnect("-d", device_id, "--share-text", f"{title}: {body}")
    return r.returncode == 0


def ring_device(device_id: str) -> bool:
    r = _kdeconnect("-d", device_id, "--ring")
    return r.returncode == 0


def share_file(device_id: str, path: str) -> bool:
    r = _kdeconnect("-d", device_id, "--share", path)
    return r.returncode == 0


def list_notifications(device_id: str) -> list[dict]:
    r = _kdeconnect("-d", device_id, "--list-notifications")
    lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    return [{"text": l} for l in lines]


def connectivity_report(device_id: str = KDECONNECT_MOTO_ID) -> dict:
    """Get SIM / network type from KDE Connect connectivity plugin."""
    import dbus  # type: ignore
    try:
        bus = dbus.SessionBus()
        path = f"/modules/kdeconnect/devices/{device_id}/connectivity_report"
        obj = bus.get_object("org.kde.kdeconnect", path)
        props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        iface_name = "org.kde.kdeconnect.device.connectivity_report"
        network_type     = str(props.Get(iface_name, "cellularNetworkType"))
        network_strength = int(props.Get(iface_name, "cellularNetworkStrength"))
        return {"cellularNetworkType": network_type, "cellularNetworkStrength": network_strength}
    except Exception as exc:
        return {"error": str(exc)}


async def send_sms_async(destination: str, message: str, device: SimDevice = SimDevice.MOTO) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_sms, destination, message, device)


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        dest, msg = sys.argv[1], sys.argv[2]
        ok = send_sms(dest, msg)
        print("sent" if ok else "failed")
    else:
        print("Usage: python kdeconnect.py +420XXXXXXXXX 'message'")
        print("Connectivity:", connectivity_report())
