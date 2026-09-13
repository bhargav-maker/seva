"""
vdak-host/utils/vm_discover.py
Auto-discovers the VM's IP address on the local subnet (192.168.31.x).
Scans for an open port 8765 (V-DAK VM WebSocket server).
Run this before starting the host if you don't know the VM's IP.

Usage:
    python -m utils.vm_discover
"""

import asyncio
import ipaddress
import logging
import os
import socket
import sys
from pathlib import Path

logger = logging.getLogger("vdak.discover")
logging.basicConfig(level=logging.INFO, format="%(message)s")

HOST_IP    = os.getenv("HOST_IP", "192.168.31.42")
VM_PORT    = int(os.getenv("HOST_WS_PORT", "8765"))
TIMEOUT    = 0.5    # seconds per IP probe


def get_subnet(host_ip: str) -> str:
    """Derive /24 subnet from host IP. e.g. 192.168.31.42 → 192.168.31.0/24"""
    network = ipaddress.IPv4Network(f"{host_ip}/24", strict=False)
    return str(network)


def probe_ip(ip: str, port: int, timeout: float) -> bool:
    """Return True if port is open on ip."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


async def scan_subnet(subnet: str, port: int) -> list[str]:
    """Scan all IPs in subnet for open port asynchronously."""
    network = ipaddress.IPv4Network(subnet, strict=False)
    loop    = asyncio.get_event_loop()
    tasks   = []

    for host in network.hosts():
        ip = str(host)
        tasks.append(loop.run_in_executor(None, probe_ip, ip, port, TIMEOUT))

    results = await asyncio.gather(*tasks)
    found   = [str(h) for h, ok in zip(network.hosts(), results) if ok]
    return found


def update_env(vm_ip: str):
    """Update VM_WS_URL in vdak-host/.env with discovered IP."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    text = env_path.read_text()
    updated = "\n".join(
        f"VM_WS_URL=ws://{vm_ip}:{VM_PORT}" if line.startswith("VM_WS_URL=") else line
        for line in text.splitlines()
    )
    env_path.write_text(updated)
    logger.info(f"✅ .env updated: VM_WS_URL=ws://{vm_ip}:{VM_PORT}")


async def main():
    subnet = get_subnet(HOST_IP)
    logger.info(f"🔍 Scanning {subnet} for VM on port {VM_PORT}...")
    found = await scan_subnet(subnet, VM_PORT)

    if not found:
        logger.warning(
            f"❌ No VM found on port {VM_PORT} in {subnet}.\n"
            f"   Make sure the VM is running and server.py is started."
        )
        sys.exit(1)

    if len(found) == 1:
        vm_ip = found[0]
        logger.info(f"✅ VM found at: {vm_ip}")
        update_env(vm_ip)
    else:
        logger.info(f"⚠️  Multiple hosts found: {found}")
        logger.info("Choosing the first one. Edit .env manually if wrong.")
        vm_ip = found[0]
        update_env(vm_ip)


if __name__ == "__main__":
    asyncio.run(main())
