import asyncio
import os
import subprocess
import socket

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Label, Button, DataTable
from textual.containers import Horizontal, Vertical
from textual import work

from widgets.confirm_dialog import ConfirmDialog


def _read_file(path: str, default: str = "") -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default


def _run(cmd: list[str], default: str = "") -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return result.stdout.strip()
    except Exception:
        return default


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "unknown"


class DashboardScreen(Screen):
    """
    Home screen showing:
    - Active streams grid (stream ID, URL, status dot)
    - Network status (IP, WiFi SSID, hostname)
    - CEC status (TV power state)
    - Pi system info (model, temp, uptime)
    - Quick action buttons: Restart Camplayer, Reload Config, Reboot
    """

    def compose(self) -> ComposeResult:
        yield Static("◉ Camplayer Dashboard", classes="title")
        with Horizontal():
            with Vertical(id="streams-panel", classes="panel"):
                yield Label("Streams", classes="section-header")
                yield DataTable(id="stream-table")
            with Vertical(id="status-panel", classes="panel"):
                yield Label("System", classes="section-header")
                yield Static(id="sys-info")
                yield Label("Network", classes="section-header")
                yield Static(id="net-info")
                yield Label("CEC", classes="section-header")
                yield Static(id="cec-info")
        with Horizontal(id="actions"):
            yield Button("Restart Camplayer", id="btn-restart", variant="primary")
            yield Button("Reload Config", id="btn-reload", variant="default")
            yield Button("Reboot Pi", id="btn-reboot", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#stream-table", DataTable)
        table.add_columns("Stream", "URL", "Status")
        self._populate_streams(table)
        self.refresh_data()
        self.set_interval(5.0, self.refresh_data)

    def _populate_streams(self, table: DataTable) -> None:
        """Load configured streams from camplayer-config.ini."""
        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            for device in cfg.devices:
                for ch_num, channel in device.channels.items():
                    for q_idx, url in enumerate(channel.urls):
                        stream_id = f"D{device.id}_CH{ch_num}_Q{q_idx + 1}"
                        url_display = url[:45] + "…" if len(url) > 46 else url
                        table.add_row(stream_id, url_display, "●")
        except Exception as exc:
            table.add_row("—", str(exc)[:60], "?")

    @work(thread=True)
    def refresh_data(self) -> None:
        """Refresh all status data (runs in worker thread)."""
        # System info
        pi_model = _read_file("/proc/device-tree/model", "Unknown Pi").replace("\x00", "")
        uptime_secs = _read_file("/proc/uptime", "0 0").split()[0]
        try:
            uptime_m = int(float(uptime_secs)) // 60
            uptime = f"{uptime_m // 60}h {uptime_m % 60}m"
        except Exception:
            uptime = "unknown"

        temp = _run(["vcgencmd", "measure_temp"], "temp=?").replace("temp=", "")
        sys_text = f"Model:  {pi_model}\nUptime: {uptime}\nTemp:   {temp}"

        # Network info
        local_ip = _get_local_ip()
        ssid = _run(["iwgetid", "-r"], "—")
        hostname = _run(["hostname"], socket.gethostname())
        net_text = f"IP:       {local_ip}\nWiFi:     {ssid}\nHostname: {hostname}"

        # CEC info (run synchronously in thread)
        try:
            cec_status = asyncio.run(_get_cec_status())
        except Exception:
            cec_status = "unavailable"
        cec_text = f"TV power: {cec_status}"

        self.app.call_from_thread(self._update_ui, sys_text, net_text, cec_text)

    def _update_ui(self, sys_text: str, net_text: str, cec_text: str) -> None:
        try:
            self.query_one("#sys-info", Static).update(sys_text)
            self.query_one("#net-info", Static).update(net_text)
            self.query_one("#cec-info", Static).update(cec_text)
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-restart":
            await self._restart_camplayer()
        elif event.button.id == "btn-reload":
            await self._reload_config()
        elif event.button.id == "btn-reboot":
            confirmed = await self.app.push_screen_wait(
                ConfirmDialog(title="Reboot Pi", message="Reboot the Raspberry Pi now?")
            )
            if confirmed:
                subprocess.run(["reboot"], check=False)

    async def _restart_camplayer(self) -> None:
        try:
            subprocess.run(
                ["systemctl", "restart", "camplayer"], check=False, timeout=10
            )
            self.notify("Camplayer service restarted.", severity="information")
        except Exception as exc:
            self.notify(f"Restart failed: {exc}", severity="error")

    async def _reload_config(self) -> None:
        try:
            # Write "reload" to the camplayer command pipe if present
            pipe = "/dev/shm/camplayer-cmd"
            if os.path.exists(pipe):
                with open(pipe, "w") as f:
                    f.write("reload\n")
            self.notify("Config reload signal sent.", severity="information")
        except Exception as exc:
            self.notify(f"Reload failed: {exc}", severity="error")


async def _get_cec_status() -> str:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from cec_control import CecControl
    return await CecControl.get_tv_power_status()
