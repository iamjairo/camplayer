import asyncio
import socket
from typing import AsyncIterator, Callable, Optional

from .result import CameraDiscoveryResult
from . import hikvision, reolink, onvif_probe


async def get_local_subnet() -> str:
    """Return the local IP's /24 subnet string (e.g. '192.168.1.0/24')."""
    try:
        # Connect to an external address without sending data to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        parts = local_ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    except Exception:
        return "192.168.1.0/24"


async def ping_host(ip: str, timeout: float = 0.5) -> bool:
    """Non-root async reachability check via TCP connect to common camera ports."""
    for port in (80, 554, 8080, 443):
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=timeout
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            continue
    return False


async def _probe_host(
    ip: str,
    username: str = "admin",
    password: str = "",
) -> Optional[CameraDiscoveryResult]:
    """Try all known probes against a live host; return first match or None."""
    probes = [
        hikvision.probe(ip, username, password),
        reolink.probe(ip, username, password),
        onvif_probe.probe_host(ip, username, password),
    ]
    results = await asyncio.gather(*probes, return_exceptions=True)
    for r in results:
        if isinstance(r, CameraDiscoveryResult):
            return r
    return None


async def scan_subnet(
    subnet: Optional[str] = None,
    username: str = "admin",
    password: str = "",
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> AsyncIterator[CameraDiscoveryResult]:
    """
    Scan local subnet for cameras. Yields results as found.

    1. Ping sweep (concurrent, 50 at a time) via TCP connect.
    2. For live hosts: try Hikvision, Reolink, ONVIF probes concurrently.
    """
    if subnet is None:
        subnet = await get_local_subnet()

    # Build list of IPs for the /24
    base = subnet.rsplit(".", 1)[0]
    ips = [f"{base}.{i}" for i in range(1, 255)]
    total = len(ips)
    scanned = 0

    semaphore = asyncio.Semaphore(50)
    result_queue: asyncio.Queue = asyncio.Queue()

    async def check_and_probe(ip: str) -> None:
        nonlocal scanned
        async with semaphore:
            alive = await ping_host(ip)
            scanned += 1
            if progress_cb:
                try:
                    progress_cb(scanned, total)
                except Exception:
                    pass
            if alive:
                result = await _probe_host(ip, username, password)
                if result:
                    await result_queue.put(result)
            await result_queue.put(None)  # sentinel per host

    tasks = [asyncio.create_task(check_and_probe(ip)) for ip in ips]

    remaining = total
    while remaining > 0:
        item = await result_queue.get()
        if item is None:
            remaining -= 1
        else:
            yield item

    # Ensure all tasks are cleaned up
    await asyncio.gather(*tasks, return_exceptions=True)
