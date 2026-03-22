import json
from typing import Optional

import httpx

from .result import CameraDiscoveryResult


async def probe(
    ip: str, username: str = "admin", password: str = ""
) -> Optional[CameraDiscoveryResult]:
    """
    Try Reolink HTTP API probe.

    Returns a CameraDiscoveryResult if the host responds as a Reolink device,
    otherwise returns None.
    """
    url = f"http://{ip}/api.cgi"
    payload = json.dumps([{"cmd": "GetDevInfo", "action": 0, "param": {}}])

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                url,
                content=payload,
                params={"cmd": "GetDevInfo", "user": username, "password": password},
                headers={"Content-Type": "application/json"},
            )

        if resp.status_code != 200:
            return None

        data = resp.json()
        # Reolink returns a list of command responses
        if not isinstance(data, list) or not data:
            return None

        entry = data[0]
        if entry.get("cmd") != "GetDevInfo":
            return None
        if entry.get("code") != 0:
            return None

        device_info = entry.get("value", {}).get("DevInfo", {})
        model = device_info.get("model", "")
        name = device_info.get("name", f"Reolink {ip}")

        cred = f"{username}:{password}@" if (username or password) else ""
        main_stream = f"rtsp://{cred}{ip}//h264Preview_01_main"
        sub_stream = f"rtsp://{cred}{ip}//h264Preview_01_sub"

        return CameraDiscoveryResult(
            ip=ip,
            brand="reolink",
            model=model,
            name=name,
            main_stream=main_stream,
            sub_stream=sub_stream,
            auth_required=bool(username),
            username=username,
            password=password,
        )

    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, OSError):
        return None
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    except Exception:
        return None
