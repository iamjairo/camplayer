import asyncio
import os
import sys

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Checkbox, DataTable, Label, Static
from textual.containers import Horizontal, Vertical
from textual import work

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cec_control import CecControl
from config.ini_manager import IniManager
from config.system_config import SystemConfig


class CecScreen(Screen):
    """
    HDMI-CEC configuration and live control:
    - Enable/disable CEC
    - TV standby on camplayer stop
    - TV wakeup on camplayer start
    - Scan CEC bus → show devices in DataTable
    - Test: TV On / TV Standby buttons
    """

    def compose(self) -> ComposeResult:
        yield Static("◉ HDMI-CEC Configuration", classes="title")
        with Horizontal():
            with Vertical(id="cec-config-panel", classes="panel"):
                yield Label("CEC Settings", classes="section-header")
                yield Checkbox("Enable HDMI-CEC", id="chk-cec-enabled", value=True)
                yield Checkbox("Standby TV when camplayer stops", id="chk-cec-standby", value=True)
                yield Checkbox("Wake TV when camplayer starts", id="chk-cec-wakeup", value=True)
                yield Button("💾 Save CEC Settings", id="btn-save", variant="primary")
                yield Static(id="save-status")

            with Vertical(id="cec-control-panel", classes="panel"):
                yield Label("Live CEC Control", classes="section-header")
                yield Static(id="cec-avail", classes="status-warn")
                with Horizontal():
                    yield Button("📺 TV On", id="btn-tv-on", variant="success")
                    yield Button("💤 TV Standby", id="btn-tv-standby", variant="default")
                    yield Button("🔍 Scan CEC Bus", id="btn-scan", variant="primary")
                yield Static(id="cec-result")
                yield Label("CEC Devices", classes="section-header")
                yield DataTable(id="cec-table")

    def on_mount(self) -> None:
        table = self.query_one("#cec-table", DataTable)
        table.add_columns("Address", "Device", "Vendor", "OSD Name")
        self._load_settings()
        self._check_cec_availability()

    def _check_cec_availability(self) -> None:
        available = CecControl.is_available()
        msg = "cec-client found — CEC control available." if available else \
              "cec-client not installed — CEC commands will not work."
        classes = "status-ok" if available else "status-warn"
        status = self.query_one("#cec-avail", Static)
        status.update(msg)
        status.remove_class("status-ok", "status-warn", "status-error")
        status.add_class(classes)

    def _load_settings(self) -> None:
        try:
            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)
            sys_cfg = SystemConfig.from_ini(mgr.read_system())
            self.query_one("#chk-cec-enabled", Checkbox).value = sys_cfg.cec_enabled
            self.query_one("#chk-cec-standby", Checkbox).value = sys_cfg.cec_standby
            self.query_one("#chk-cec-wakeup", Checkbox).value = sys_cfg.cec_wakeup
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-save":
            self._save_settings()
        elif btn_id == "btn-tv-on":
            self._cec_action("on")
        elif btn_id == "btn-tv-standby":
            self._cec_action("standby")
        elif btn_id == "btn-scan":
            self._scan_cec()

    @work(thread=True)
    def _save_settings(self) -> None:
        try:
            enabled = self.app.call_from_thread(
                lambda: self.query_one("#chk-cec-enabled", Checkbox).value
            )
            standby = self.app.call_from_thread(
                lambda: self.query_one("#chk-cec-standby", Checkbox).value
            )
            wakeup = self.app.call_from_thread(
                lambda: self.query_one("#chk-cec-wakeup", Checkbox).value
            )

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)
            cp = mgr.read_system()
            sys_cfg = SystemConfig.from_ini(cp)
            sys_cfg.cec_enabled = bool(enabled)
            sys_cfg.cec_standby = bool(standby)
            sys_cfg.cec_wakeup = bool(wakeup)
            sys_cfg.to_ini(cp)
            mgr.write_system(cp)
            msg = "✓ CEC settings saved."
        except Exception as exc:
            msg = f"✗ {exc}"
        self.app.call_from_thread(
            self.query_one("#save-status", Static).update, msg
        )

    @work(exclusive=True)
    async def _cec_action(self, action: str) -> None:
        result_widget = self.query_one("#cec-result", Static)
        result_widget.update(f"Sending CEC '{action}' command…")
        if action == "on":
            ok = await CecControl.tv_power_on()
            status = await CecControl.get_tv_power_status()
            msg = f"TV power command sent. Current status: {status}"
        elif action == "standby":
            await CecControl.tv_standby()
            msg = "TV standby command sent."
        else:
            msg = f"Unknown action: {action}"
        result_widget.update(msg)

    @work(exclusive=True)
    async def _scan_cec(self) -> None:
        result_widget = self.query_one("#cec-result", Static)
        result_widget.update("Scanning CEC bus…")
        raw = await CecControl.scan()

        table = self.query_one("#cec-table", DataTable)
        table.clear()

        # Parse cec-client scan output
        current: dict = {}
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("device #"):
                if current:
                    table.add_row(
                        current.get("address", "?"),
                        current.get("device", "?"),
                        current.get("vendor", "?"),
                        current.get("osd", "?"),
                    )
                current = {}
            elif ":" in line:
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()
                if "address" in key:
                    current["address"] = val
                elif "device" in key or "type" in key:
                    current["device"] = val
                elif "vendor" in key:
                    current["vendor"] = val
                elif "osd" in key or "name" in key:
                    current["osd"] = val

        if current:
            table.add_row(
                current.get("address", "?"),
                current.get("device", "?"),
                current.get("vendor", "?"),
                current.get("osd", "?"),
            )

        count = table.row_count
        result_widget.update(f"Scan complete. Found {count} device(s).")
