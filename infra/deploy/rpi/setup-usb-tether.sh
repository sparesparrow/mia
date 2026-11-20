#!/usr/bin/env bash
# Configure the Pi's Android USB-tether interface for DHCP and prefer its route.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
    echo "Run as root: sudo bash $0 <usb-interface>" >&2
    exit 1
fi

iface="${1:-}"
if [[ -z "$iface" ]]; then
    echo "Usage: sudo bash $0 <usb-interface>" >&2
    echo "Find the interface with: ip -br link (often usb0 or enx...)" >&2
    exit 2
fi
if [[ ! "$iface" =~ ^(usb[0-9]+|enx[[:xdigit:]]+)$ ]]; then
    echo "Refusing unexpected interface name: $iface (expected usbN or enx<MAC>)" >&2
    exit 2
fi
if [[ ! -d "/sys/class/net/$iface" ]]; then
    echo "Interface $iface is not present. Enable Android USB tethering, then retry." >&2
    exit 1
fi

if systemctl is-active --quiet NetworkManager; then
    connection="mia-phone-usb-$iface"
    if nmcli connection show "$connection" >/dev/null 2>&1; then
        nmcli connection modify "$connection" \
            connection.interface-name "$iface" \
            connection.autoconnect yes \
            ipv4.method auto ipv4.route-metric 100 \
            ipv6.method auto ipv6.route-metric 100
    else
        nmcli connection add type ethernet \
            con-name "$connection" ifname "$iface" \
            connection.autoconnect yes \
            ipv4.method auto ipv4.route-metric 100 \
            ipv6.method auto ipv6.route-metric 100
    fi
    nmcli connection up "$connection"
elif systemctl is-active --quiet dhcpcd; then
    config=/etc/dhcpcd.conf
    if [[ ! -f "$config" ]]; then
        echo "$config is missing; cannot configure DHCP for $iface" >&2
        exit 1
    fi
    marker="# MIA phone USB tether: $iface"
    if ! grep -Fq "$marker" "$config"; then
        {
            echo
            echo "$marker"
            echo "interface $iface"
            echo "    metric 100"
        } >>"$config"
    fi
    systemctl restart dhcpcd
else
    echo "Neither NetworkManager nor dhcpcd is active. Configure DHCP for $iface with the Pi's network manager." >&2
    exit 1
fi

echo "Configured DHCP for $iface. Check the address with 'ip -br addr' and the selected uplink with 'ip route'."
