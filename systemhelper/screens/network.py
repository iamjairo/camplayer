import os
import subprocess
import sys

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static
from textual.containers import Horizontal, Vertical
from textual import work

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.ini_manager import IniManager
from config.system_config import SystemConfig


_WIFI_COUNTRIES = [
    ("US – United States", "US"),
    ("GB – United Kingdom", "GB"),
    ("DE – Germany", "DE"),
    ("FR – France", "FR"),
    ("AU – Australia", "AU"),
    ("CA – Canada", "CA"),
    ("JP – Japan", "JP"),
    ("CN – China", "CN"),
    ("IN – India", "IN"),
    ("BR – Brazil", "BR"),
    ("ZA – South Africa", "ZA"),
    ("NL – Netherlands", "NL"),
    ("SE – Sweden", "SE"),
    ("NO – Norway", "NO"),
    ("IT – Italy", "IT"),
    ("ES – Spain", "ES"),
    ("PL – Poland", "PL"),
    ("NZ – New Zealand", "NZ"),
    ("SG – Singapore", "SG"),
    ("HK – Hong Kong", "HK"),
]


class NetworkScreen(Screen):
    """
    Network configuration:
    - Current IP addresses (eth0, wlan0)
    - WiFi SSID/password/country + Apply button
    - Hostname + Apply button
    - mDNS status (avahi-daemon / camplayer.local)
    """

    def compose(self) -> ComposeResult:
        yield Static("◉ Network Configuration", classes="title")
        with Horizontal():
            with Vertical(id="left-panel", classes="panel"):
                yield Label("Current Status", classes="section-header")
                yield Static(id="iface-status")
                yield Label("mDNS / Bonjour", classes="section-header")
                yield Static(id="mdns-status")

            with Vertical(id="right-panel", classes="panel"):
                yield Label("WiFi Configuration", classes="section-header")
                yield Label("SSID:")
                yield Input(id="inp-ssid", placeholder="MyNetworkName")
                yield Label("Password:")
                yield Input(id="inp-password", placeholder="WiFi password", password=True)
                yield Label("Country:")
                yield Select(
                    [(label, code) for label, code in _WIFI_COUNTRIES],
                    id="sel-country",
                    value="US",
                    prompt="Select country",
                )
                yield Button("📡 Apply WiFi", id="btn-wifi", variant="primary")
                yield Static(id="wifi-status")

                yield Label("Hostname", classes="section-header")
                yield Input(id="inp-hostname", placeholder="camplayer")
                yield Button("✎ Apply Hostname", id="btn-hostname", variant="default")
                yield Static(id="hostname-status")

    def on_mount(self) -> None:
        self._load_current_settings()
        self.refresh_status()
        self.set_interval(10.0, self.refresh_status)

    def _load_current_settings(self) -> None:
        """Pre-fill form with current values from system-config.ini."""
        try:
            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)
            sys_cfg = SystemConfig.from_ini(mgr.read_system())

            self.query_one("#inp-ssid", Input).value = sys_cfg.wifi_ssid
            self.query_one("#inp-password", Input).value = sys_cfg.wifi_password
            self.query_one("#inp-hostname", Input).value = sys_cfg.hostname
            sel = self.query_one("#sel-country", Select)
            try:
                sel.value = sys_cfg.wifi_country
            except Exception:
                pass
        except Exception:
            pass

    @work(thread=True)
    def refresh_status(self) -> None:
        """Read live interface info."""
        iface_lines: list[str] = []
        for iface in ("eth0", "wlan0"):
            ip = self._get_iface_ip(iface)
            iface_lines.append(f"{iface}: {ip or 'not connected'}")

        ssid = self._run(["iwgetid", "-r"], "—")
        iface_lines.append(f"WiFi SSID: {ssid}")

        mdns_active = self._run(["systemctl", "is-active", "avahi-daemon"], "unknown").strip()
        mdns_text = (
            f"avahi-daemon: {mdns_active}\n"
            f"Accessible as: camplayer.local"
            if mdns_active == "active"
            else f"avahi-daemon: {mdns_active} (mDNS not available)"
        )

        self.app.call_from_thread(
            self.query_one("#iface-status", Static).update,
            "\n".join(iface_lines),
        )
        self.app.call_from_thread(
            self.query_one("#mdns-status", Static).update,
            mdns_text,
        )

    def _get_iface_ip(self, iface: str) -> str:
        try:
            out = subprocess.run(
                ["ip", "-4", "addr", "show", iface],
                capture_output=True, text=True, timeout=3
            ).stdout
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    return line.split()[1].split("/")[0]
        except Exception:
            pass
        return ""

    def _run(self, cmd: list[str], default: str = "") -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip()
        except Exception:
            return default

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-wifi":
            self._apply_wifi()
        elif event.button.id == "btn-hostname":
            self._apply_hostname()

    @work(thread=True)
    def _apply_wifi(self) -> None:
        ssid = self.app.call_from_thread(lambda: self.query_one("#inp-ssid", Input).value.strip())
        password = self.app.call_from_thread(lambda: self.query_one("#inp-password", Input).value)
        country = self.app.call_from_thread(lambda: self.query_one("#sel-country", Select).value)

        if not ssid:
            self.app.call_from_thread(
                self.query_one("#wifi-status", Static).update, "✗ SSID cannot be empty."
            )
            return

        # Write to system-config.ini
        try:
            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)
            cp = mgr.read_system()
            sys_cfg = SystemConfig.from_ini(cp)
            sys_cfg.wifi_ssid = ssid
            sys_cfg.wifi_password = password
            if isinstance(country, str):
                sys_cfg.wifi_country = country
            sys_cfg.to_ini(cp)
            mgr.write_system(cp)
        except Exception as exc:
            self.app.call_from_thread(
                self.query_one("#wifi-status", Static).update, f"✗ Config save failed: {exc}"
            )
            return

        # Write wpa_supplicant.conf
        wpa_conf = (
            f'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n'
            f'update_config=1\n'
            f'country={country if isinstance(country, str) else "US"}\n\n'
            f'network={{\n'
            f'    ssid="{ssid}"\n'
            f'    psk="{password}"\n'
            f'}}\n'
        )
        try:
            with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as f:
                f.write(wpa_conf)
            subprocess.run(["wpa_cli", "-i", "wlan0", "reconfigure"],
                           capture_output=True, timeout=10)
            msg = f"✓ WiFi configured for '{ssid}'. Reconnecting…"
        except PermissionError:
            msg = "✗ Permission denied. Run as root."
        except Exception as exc:
            msg = f"✗ {exc}"

        self.app.call_from_thread(
            self.query_one("#wifi-status", Static).update, msg
        )

    @work(thread=True)
    def _apply_hostname(self) -> None:
        hostname = self.app.call_from_thread(
            lambda: self.query_one("#inp-hostname", Input).value.strip()
        )
        if not hostname:
            self.app.call_from_thread(
                self.query_one("#hostname-status", Static).update, "✗ Hostname cannot be empty."
            )
            return

        try:
            with open("/etc/hostname", "w") as f:
                f.write(hostname + "\n")
            subprocess.run(["hostnamectl", "set-hostname", hostname],
                           capture_output=True, timeout=5)

            # Save to system-config.ini
            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            mgr = IniManager(camplayer_path=config_path)
            cp = mgr.read_system()
            sys_cfg = SystemConfig.from_ini(cp)
            sys_cfg.hostname = hostname
            sys_cfg.to_ini(cp)
            mgr.write_system(cp)

            msg = f"✓ Hostname set to '{hostname}' (restart for full effect)."
        except PermissionError:
            msg = "✗ Permission denied. Run as root."
        except Exception as exc:
            msg = f"✗ {exc}"

        self.app.call_from_thread(
            self.query_one("#hostname-status", Static).update, msg
        )
