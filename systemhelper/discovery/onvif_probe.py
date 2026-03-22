import asyncio
import socket
import uuid
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

from .result import CameraDiscoveryResult

WS_DISCOVERY_ADDR = ("239.255.255.250", 3702)
WS_DISCOVERY_PORT = 0  # OS-assigned source port

PROBE_MSG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{uuid}</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>
</e:Envelope>"""

ONVIF_GET_STREAM_URI = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetStreamUri>
      <trt:StreamSetup>
        <tt:Stream>RTP-Unicast</tt:Stream>
        <tt:Transport><tt:Protocol>RTSP</tt:Protocol></tt:Transport>
      </trt:StreamSetup>
      <trt:ProfileToken>{profile}</trt:ProfileToken>
    </trt:GetStreamUri>
  </s:Body>
</s:Envelope>"""

ONVIF_GET_PROFILES = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
  <s:Body><trt:GetProfiles/></s:Body>
</s:Envelope>"""


async def ws_discovery(timeout: float = 3.0) -> list[str]:
    """
    Send a WS-Discovery UDP multicast probe and collect ONVIF device XAddrs.
    Returns a list of ONVIF service endpoint URLs.
    """
    probe_msg = PROBE_MSG_TEMPLATE.format(uuid=str(uuid.uuid4())).encode("utf-8")
    xaddrs: list[str] = []

    loop = asyncio.get_event_loop()

    # Create UDP socket for multicast
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 3)
    sock.setblocking(False)

    try:
        sock.sendto(probe_msg, WS_DISCOVERY_ADDR)
    except Exception:
        sock.close()
        return xaddrs

    deadline = loop.time() + timeout
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                data = await asyncio.wait_for(
                    loop.run_in_executor(None, sock.recv, 65535),
                    timeout=min(remaining, 0.5),
                )
                found = _parse_xaddrs(data.decode("utf-8", errors="replace"))
                xaddrs.extend(found)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
    finally:
        sock.close()

    return list(set(xaddrs))


def _parse_xaddrs(xml_text: str) -> list[str]:
    """Extract XAddr values from a WS-Discovery ProbeMatch response."""
    addrs: list[str] = []
    try:
        root = ET.fromstring(xml_text)
        # Search for XAddrs elements anywhere in the tree
        for el in root.iter():
            if el.tag.endswith("}XAddrs") or el.tag == "XAddrs":
                if el.text:
                    for addr in el.text.split():
                        if addr.startswith("http"):
                            addrs.append(addr)
    except ET.ParseError:
        pass
    return addrs


async def get_stream_uri(
    xaddr: str, username: str = "admin", password: str = ""
) -> Optional[CameraDiscoveryResult]:
    """
    Use ONVIF GetProfiles + GetStreamUri (pure HTTP SOAP) to get RTSP URLs.
    No python-onvif library needed.
    """
    auth = (username, password) if username else None

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            # Get profiles
            profiles_resp = await client.post(
                xaddr,
                content=ONVIF_GET_PROFILES.encode("utf-8"),
                headers={
                    "Content-Type": "application/soap+xml; charset=utf-8",
                    "SOAPAction": '"http://www.onvif.org/ver10/media/wsdl/GetProfiles"',
                },
                auth=auth,
            )

        if profiles_resp.status_code not in (200, 401):
            return None

        profile_tokens = _parse_profile_tokens(profiles_resp.text)
        if not profile_tokens:
            return None

        streams: list[str] = []
        async with httpx.AsyncClient(timeout=4.0) as client:
            for token in profile_tokens[:2]:
                body = ONVIF_GET_STREAM_URI.format(profile=token).encode("utf-8")
                uri_resp = await client.post(
                    xaddr,
                    content=body,
                    headers={
                        "Content-Type": "application/soap+xml; charset=utf-8",
                        "SOAPAction": '"http://www.onvif.org/ver10/media/wsdl/GetStreamUri"',
                    },
                    auth=auth,
                )
                uri = _parse_stream_uri(uri_resp.text)
                if uri:
                    streams.append(uri)

        if not streams:
            return None

        ip = _extract_ip(xaddr)
        return CameraDiscoveryResult(
            ip=ip,
            brand="onvif",
            name=f"ONVIF {ip}",
            main_stream=streams[0],
            sub_stream=streams[1] if len(streams) > 1 else "",
            auth_required=bool(username),
            username=username,
            password=password,
        )

    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, OSError):
        return None
    except Exception:
        return None


async def probe_host(
    ip: str, username: str = "admin", password: str = ""
) -> Optional[CameraDiscoveryResult]:
    """Directly probe a known IP for ONVIF service on common ports."""
    for port in (80, 8080, 8899, 8000):
        xaddr = f"http://{ip}:{port}/onvif/device_service"
        result = await get_stream_uri(xaddr, username, password)
        if result:
            return result
    return None


def _parse_profile_tokens(xml_text: str) -> list[str]:
    tokens: list[str] = []
    try:
        root = ET.fromstring(xml_text)
        for el in root.iter():
            if el.tag.endswith("}Profiles") or el.tag == "Profiles":
                token = el.get("token")
                if token:
                    tokens.append(token)
    except ET.ParseError:
        pass
    return tokens


def _parse_stream_uri(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
        for el in root.iter():
            if el.tag.endswith("}Uri") or el.tag == "Uri":
                if el.text and el.text.startswith("rtsp://"):
                    return el.text.strip()
    except ET.ParseError:
        pass
    return ""


def _extract_ip(url: str) -> str:
    """Extract the host/IP portion from a URL."""
    try:
        # Remove scheme
        without_scheme = url.split("://", 1)[1]
        # Remove path
        host = without_scheme.split("/")[0]
        # Remove port
        return host.split(":")[0]
    except Exception:
        return url
