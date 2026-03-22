from typing import Optional

import httpx

from .result import CameraDiscoveryResult

ISAPI_DEVICE_INFO = "/ISAPI/System/deviceInfo"


async def probe(
    ip: str, username: str = "admin", password: str = ""
) -> Optional[CameraDiscoveryResult]:
    """
    Try Hikvision ISAPI probe.

    Returns a CameraDiscoveryResult if the host responds as a Hikvision device,
    otherwise returns None.
    """
    url = f"http://{ip}{ISAPI_DEVICE_INFO}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, auth=(username, password))

        # Hikvision returns 200 or 401 on this endpoint; anything else is not Hikvision
        if resp.status_code not in (200, 401):
            return None

        # If we get 401 it's still probably Hikvision — mark as auth required
        auth_required = resp.status_code == 401

        model = ""
        name = ""
        if not auth_required:
            # Parse XML response for model and device name
            try:
                import xml.etree.ElementTree as ET

                root = ET.fromstring(resp.text)
                ns = {"h": "http://www.hikvision.com/ver20/XMLSchema"}
                # Try both namespaced and non-namespaced
                model_el = root.find("h:model", ns) or root.find("model")
                name_el = (
                    root.find("h:deviceName", ns) or root.find("deviceName")
                )
                if model_el is not None and model_el.text:
                    model = model_el.text.strip()
                if name_el is not None and name_el.text:
                    name = name_el.text.strip()
            except Exception:
                pass

        cred = f"{username}:{password}@" if (username or password) else ""
        main_stream = f"rtsp://{cred}{ip}/Streaming/Channels/101"
        sub_stream = f"rtsp://{cred}{ip}/Streaming/Channels/102"

        return CameraDiscoveryResult(
            ip=ip,
            brand="hikvision",
            model=model,
            name=name or f"Hikvision {ip}",
            main_stream=main_stream,
            sub_stream=sub_stream,
            auth_required=auth_required,
            username=username,
            password=password,
        )

    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, OSError):
        return None
    except Exception:
        return None
