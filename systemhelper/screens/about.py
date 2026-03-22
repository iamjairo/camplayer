import os
import subprocess
import sys

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Label
from textual.containers import Vertical
from textual import work


def _read_file(path: str, default: str = "") -> str:
    try:
        with open(path) as f:
            return f.read().strip().replace("\x00", "")
    except Exception:
        return default


def _run(cmd: list[str], default: str = "unknown") -> str:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except Exception:
        return default


class AboutScreen(Screen):
    """Version info, Pi hardware details, and software versions."""

    def compose(self) -> ComposeResult:
        yield Static("◉ About Camplayer Systemhelper", classes="title")
        with Vertical(classes="panel"):
            yield Label("Hardware", classes="section-header")
            yield Static(id="hw-info")
            yield Label("Software", classes="section-header")
            yield Static(id="sw-info")
            yield Label("Config Paths", classes="section-header")
            yield Static(id="cfg-info")

    def on_mount(self) -> None:
        self.load_info()

    @work(thread=True)
    def load_info(self) -> None:
        # Hardware
        pi_model = _read_file("/proc/device-tree/model", "Unknown")
        cpu_info = _read_file("/proc/cpuinfo", "")
        serial = ""
        hw = ""
        for line in cpu_info.splitlines():
            if line.startswith("Serial"):
                serial = line.split(":")[1].strip()
            if line.startswith("Hardware"):
                hw = line.split(":")[1].strip()

        gpu_mem = _run(["vcgencmd", "get_mem", "gpu"], "gpu=?")
        hwdec = _run(["vcgencmd", "codec_enabled", "H264"], "H264=?")
        hw_text = (
            f"Model:    {pi_model}\n"
            f"Hardware: {hw or 'N/A'}\n"
            f"Serial:   {serial or 'N/A'}\n"
            f"GPU Mem:  {gpu_mem}\n"
            f"H264 HW:  {hwdec}"
        )

        # Software
        python_ver = _run(["python3", "--version"], "unknown")
        textual_ver = self._pkg_version("textual")
        fastapi_ver = self._pkg_version("fastapi")
        uvicorn_ver = self._pkg_version("uvicorn")
        os_ver = _run(["cat", "/etc/os-release"], "").split("\n")
        os_name = next(
            (l.split("=")[1].strip().strip('"') for l in os_ver if l.startswith("PRETTY_NAME")),
            "unknown"
        )
        sw_text = (
            f"OS:           {os_name}\n"
            f"Python:       {python_ver}\n"
            f"Textual:      {textual_ver}\n"
            f"FastAPI:      {fastapi_ver}\n"
            f"Uvicorn:      {uvicorn_ver}\n"
            f"Systemhelper: open-source (Phase 3)"
        )

        # Config paths
        config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
        cfg_text = (
            f"Camplayer config: {config_path}\n"
            f"System config:    /boot/system-config.ini\n"
            f"Runtime config:   /dev/shm/camplayer-config.ini\n"
            f"Web API:          http://0.0.0.0:8000"
        )

        self.app.call_from_thread(self._update_ui, hw_text, sw_text, cfg_text)

    def _update_ui(self, hw: str, sw: str, cfg: str) -> None:
        try:
            self.query_one("#hw-info", Static).update(hw)
            self.query_one("#sw-info", Static).update(sw)
            self.query_one("#cfg-info", Static).update(cfg)
        except Exception:
            pass

    def _pkg_version(self, package: str) -> str:
        try:
            import importlib.metadata
            return importlib.metadata.version(package)
        except Exception:
            return "not installed"
