import os
import subprocess
import sys
from typing import Any

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static
from textual.containers import Horizontal, Vertical
from textual import work

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.ini_manager import IniManager
from config.system_config import SystemConfig


_TIMEZONES = [
    "UTC",
    "America/New_York", "America/Chicago", "America/Denver",
    "America/Los_Angeles", "America/Toronto", "America/Vancouver",
    "America/Sao_Paulo", "America/Buenos_Aires", "America/Mexico_City",
    "Europe/London", "Europe/Dublin", "Europe/Paris", "Europe/Berlin",
    "Europe/Amsterdam", "Europe/Madrid", "Europe/Rome", "Europe/Warsaw",
    "Europe/Moscow", "Europe/Istanbul",
    "Asia/Dubai", "Asia/Karachi", "Asia/Kolkata", "Asia/Dhaka",
    "Asia/Bangkok", "Asia/Singapore", "Asia/Shanghai", "Asia/Tokyo",
    "Asia/Seoul", "Asia/Hong_Kong",
    "Australia/Sydney", "Australia/Melbourne", "Australia/Perth",
    "Pacific/Auckland", "Pacific/Honolulu",
    "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos",
]

_ROTATE_OPTIONS = [
    ("0° (normal)", "0"),
    ("90° clockwise", "90"),
    ("180° (flipped)", "180"),
    ("270° counter-clockwise", "270"),
]

_HEVC_OPTIONS = [
    ("1 – Off", "1"),
    ("2 – Auto", "2"),
    ("3 – FHD (1080p)", "3"),
    ("4 – UHD (4K)", "4"),
]

_AUDIO_OPTIONS = [
    ("HDMI", "hdmi"),
    ("Analog (3.5mm)", "analog"),
    ("Off", "off"),
]

_QUALITY_OPTIONS = [
    ("1 – Low", "1"),
    ("2 – Auto", "2"),
    ("3 – High", "3"),
]

_CHANGEOVER_OPTIONS = [
    ("1 – Normal", "1"),
    ("2 – Prebuffer", "2"),
    ("3 – Smooth", "3"),
]

_BACKGROUND_OPTIONS = [
    ("1 – Hide (black)", "1"),
    ("2 – Static image", "2"),
    ("3 – Dynamic", "3"),
    ("4 – Off", "4"),
]


class SystemScreen(Screen):
    """
    System settings:
    - Timezone (timedatectl)
    - Display resolution + rotate (config.txt hdmi_mode)
    - HEVC mode, audio mode, stream quality, changeover type, background
    """

    def compose(self) -> ComposeResult:
        yield Static("◉ System Settings", classes="title")
        with Horizontal():
            with Vertical(id="display-panel", classes="panel"):
                yield Label("Display", classes="section-header")
                yield Label("Width (px):")
                yield Input(id="inp-width", placeholder="1920")
                yield Label("Height (px):")
                yield Input(id="inp-height", placeholder="1080")
                yield Label("Rotation:")
                yield Select(
                    [(l, v) for l, v in _ROTATE_OPTIONS],
                    id="sel-rotate", value="0", prompt="Select rotation"
                )
                yield Label("Timezone:")
                yield Select(
                    [(tz, tz) for tz in _TIMEZONES],
                    id="sel-timezone", value="UTC", prompt="Select timezone"
                )
                yield Button("💾 Apply Display & TZ", id="btn-display", variant="primary")
                yield Static(id="display-status")

            with Vertical(id="stream-panel", classes="panel"):
                yield Label("Stream Settings", classes="section-header")
                yield Label("HEVC Mode:")
                yield Select(
                    [(l, v) for l, v in _HEVC_OPTIONS],
                    id="sel-hevc", value="1", prompt="Select HEVC mode"
                )
                yield Label("Audio Output:")
                yield Select(
                    [(l, v) for l, v in _AUDIO_OPTIONS],
                    id="sel-audio", value="hdmi", prompt="Select audio"
                )
                yield Label("Stream Quality:")
                yield Select(
                    [(l, v) for l, v in _QUALITY_OPTIONS],
                    id="sel-quality", value="1", prompt="Select quality"
                )
                yield Label("Changeover Type:")
                yield Select(
                    [(l, v) for l, v in _CHANGEOVER_OPTIONS],
                    id="sel-changeover", value="1", prompt="Select changeover"
                )
                yield Label("Background:")
                yield Select(
                    [(l, v) for l, v in _BACKGROUND_OPTIONS],
                    id="sel-background", value="1", prompt="Select background"
                )
                yield Button("💾 Apply Stream Settings", id="btn-stream", variant="primary")
                yield Static(id="stream-status")

    def on_mount(self) -> None:
        self._load_settings()

    def _load_settings(self) -> None:
        try:
            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)
            sys_cfg = SystemConfig.from_ini(mgr.read_system())

            self.query_one("#inp-width", Input).value = str(sys_cfg.display_width)
            self.query_one("#inp-height", Input).value = str(sys_cfg.display_height)
            try:
                self.query_one("#sel-rotate", Select).value = str(sys_cfg.display_rotate)
            except Exception:
                pass
            try:
                self.query_one("#sel-timezone", Select).value = sys_cfg.timezone
            except Exception:
                pass
            try:
                self.query_one("#sel-audio", Select).value = sys_cfg.audio_output
            except Exception:
                pass

            # Load ADVANCED section from camplayer-config.ini
            cp = mgr.read_camplayer()
            if cp.has_section("ADVANCED"):
                adv = cp["ADVANCED"]
                for sel_id, key in [
                    ("#sel-hevc", "hevc_mode"),
                    ("#sel-quality", "stream_quality"),
                    ("#sel-changeover", "changeover_type"),
                    ("#sel-background", "background"),
                ]:
                    val = adv.get(key, "")
                    if val:
                        try:
                            self.query_one(sel_id, Select).value = val
                        except Exception:
                            pass
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-display":
            self._apply_display()
        elif event.button.id == "btn-stream":
            self._apply_stream_settings()

    @work(thread=True)
    def _apply_display(self) -> None:
        try:
            width = int(self.app.call_from_thread(lambda: self.query_one("#inp-width", Input).value.strip()) or "1920")
            height = int(self.app.call_from_thread(lambda: self.query_one("#inp-height", Input).value.strip()) or "1080")
            rotate = self.app.call_from_thread(lambda: self.query_one("#sel-rotate", Select).value)
            timezone = self.app.call_from_thread(lambda: self.query_one("#sel-timezone", Select).value)
        except Exception as exc:
            self.app.call_from_thread(
                self.query_one("#display-status", Static).update, f"✗ Invalid values: {exc}"
            )
            return

        errors: list[str] = []

        # Apply timezone
        if isinstance(timezone, str) and timezone != "UTC":
            try:
                subprocess.run(
                    ["timedatectl", "set-timezone", timezone],
                    capture_output=True, timeout=5
                )
            except Exception as exc:
                errors.append(f"TZ: {exc}")

        # Save to system-config.ini
        try:
            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)
            cp = mgr.read_system()
            sys_cfg = SystemConfig.from_ini(cp)
            sys_cfg.display_width = width
            sys_cfg.display_height = height
            sys_cfg.display_rotate = int(rotate) if isinstance(rotate, str) else 0
            sys_cfg.timezone = timezone if isinstance(timezone, str) else "UTC"
            sys_cfg.to_ini(cp)
            mgr.write_system(cp)
        except Exception as exc:
            errors.append(f"Config: {exc}")

        msg = "✓ Display settings saved." if not errors else "✗ " + "; ".join(errors)
        self.app.call_from_thread(
            self.query_one("#display-status", Static).update, msg
        )

    @work(thread=True)
    def _apply_stream_settings(self) -> None:
        try:
            hevc = self.app.call_from_thread(lambda: self.query_one("#sel-hevc", Select).value)
            audio = self.app.call_from_thread(lambda: self.query_one("#sel-audio", Select).value)
            quality = self.app.call_from_thread(lambda: self.query_one("#sel-quality", Select).value)
            changeover = self.app.call_from_thread(lambda: self.query_one("#sel-changeover", Select).value)
            background = self.app.call_from_thread(lambda: self.query_one("#sel-background", Select).value)
        except Exception as exc:
            self.app.call_from_thread(
                self.query_one("#stream-status", Static).update, f"✗ {exc}"
            )
            return

        try:
            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)

            # Update system-config.ini for audio
            cp_sys = mgr.read_system()
            sys_cfg = SystemConfig.from_ini(cp_sys)
            if isinstance(audio, str):
                sys_cfg.audio_output = audio
            sys_cfg.to_ini(cp_sys)
            mgr.write_system(cp_sys)

            # Update camplayer-config.ini [ADVANCED]
            cp = mgr.read_camplayer()
            if not cp.has_section("ADVANCED"):
                cp.add_section("ADVANCED")
            for key, val in [
                ("hevc_mode", hevc), ("stream_quality", quality),
                ("changeover_type", changeover), ("background", background),
                ("audio_mode", "1" if audio == "hdmi" else "0"),
            ]:
                if isinstance(val, str):
                    cp.set("ADVANCED", key, val)
            mgr.write_camplayer(cp)
            msg = "✓ Stream settings saved."
        except Exception as exc:
            msg = f"✗ {exc}"

        self.app.call_from_thread(
            self.query_one("#stream-status", Static).update, msg
        )
