from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from screens.dashboard import DashboardScreen
from screens.camera_manager import CameraManagerScreen
from screens.layout_editor import LayoutEditorScreen
from screens.network import NetworkScreen
from screens.system import SystemScreen
from screens.cec import CecScreen
from screens.speedtest import SpeedtestScreen
from screens.about import AboutScreen


class SystemhelperApp(App):
    """Camplayer Systemhelper — configure cameras, layouts, network, CEC."""

    CSS = """
    Screen {
        background: #0a0a0a;
    }
    .title {
        text-style: bold;
        color: #4488ff;
        padding: 0 1;
    }
    .section-header {
        background: #1a2a4a;
        color: #ffffff;
        padding: 0 1;
        text-style: bold;
    }
    .status-ok    { color: #22cc44; }
    .status-warn  { color: #ffaa00; }
    .status-error { color: #ff4444; }
    .panel {
        border: solid #1a2a4a;
        margin: 0 1;
    }
    Button {
        margin: 0 1 0 0;
    }
    Input {
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("1", "push_screen('dashboard')", "Dashboard", show=True),
        Binding("2", "push_screen('cameras')", "Cameras", show=True),
        Binding("3", "push_screen('layouts')", "Layouts", show=True),
        Binding("4", "push_screen('network')", "Network", show=True),
        Binding("5", "push_screen('system')", "System", show=True),
        Binding("6", "push_screen('cec')", "CEC", show=True),
        Binding("7", "push_screen('speedtest')", "Speedtest", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "pop_screen", "Back", show=False),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "cameras": CameraManagerScreen,
        "layouts": LayoutEditorScreen,
        "network": NetworkScreen,
        "system": SystemScreen,
        "cec": CecScreen,
        "speedtest": SpeedtestScreen,
        "about": AboutScreen,
    }

    def __init__(self, config_path: str, **kwargs):
        super().__init__(**kwargs)
        self.config_path = config_path

    def on_mount(self) -> None:
        self.push_screen("dashboard")
