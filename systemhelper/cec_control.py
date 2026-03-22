import asyncio
import subprocess
from typing import Optional


class CecControl:
    """HDMI-CEC control via cec-client subprocess (more portable than python-cec)."""

    @staticmethod
    async def send_command(cmd: str, timeout: float = 5.0) -> str:
        """Send a single cec-client command and return response."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "cec-client",
                "-s",
                "-d",
                "1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(input=(cmd + "\n").encode()), timeout=timeout
            )
            return stdout.decode()
        except FileNotFoundError:
            return "cec-client not available"
        except asyncio.TimeoutError:
            return "timeout"
        except Exception as exc:
            return f"error: {exc}"

    @staticmethod
    async def tv_power_on() -> bool:
        result = await CecControl.send_command("on 0")
        return "not available" not in result and "error" not in result

    @staticmethod
    async def tv_standby() -> bool:
        result = await CecControl.send_command("standby 0")
        return "not available" not in result and "error" not in result

    @staticmethod
    async def get_tv_power_status() -> str:
        result = await CecControl.send_command("pow 0")
        if "power status: on" in result:
            return "on"
        elif "power status: standby" in result:
            return "standby"
        elif "not available" in result:
            return "unavailable"
        return "unknown"

    @staticmethod
    async def scan() -> str:
        return await CecControl.send_command("scan")

    @staticmethod
    def is_available() -> bool:
        """Check whether cec-client binary exists on this system."""
        try:
            result = subprocess.run(
                ["which", "cec-client"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False
