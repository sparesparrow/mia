import os
import socket
from time import sleep
from zeroconf import IPVersion, ServiceInfo, Zeroconf

name = os.getenv("SERVICE_NAME", "ai-servis-pi")
stype = os.getenv("SERVICE_TYPE", "_mqtt._tcp.local.")
port = int(os.getenv("SERVICE_PORT", "1883"))
txt = os.getenv("SERVICE_TXT", "path=/").encode("utf-8")


def get_host_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


ip = get_host_ip()
desc = {"note": txt}
z = Zeroconf(ip_version=IPVersion.V4Only)
info = ServiceInfo(
    type_=stype,
    name=f"{name}.{stype}",
    addresses=[socket.inet_aton(ip)],
    port=port,
    properties=desc,
    server=f"{name}.local.",
)

try:
    z.register_service(info)
    while True:
        sleep(60)
finally:
    try:
        z.unregister_service(info)
    except Exception:
        pass
    z.close()


