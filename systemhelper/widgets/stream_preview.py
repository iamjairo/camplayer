from textual.app import ComposeResult
from textual.widgets import Label, Static
from textual.containers import Horizontal


class StreamPreviewWidget(Static):
    """
    Compact stream status widget showing stream ID, URL, and a colored status dot.

    Dot colors:
      ● green  = active/playing
      ● yellow = connecting
      ● red    = error / unreachable
      ● gray   = unconfigured
    """

    DEFAULT_CSS = """
    StreamPreviewWidget {
        height: 1;
        padding: 0 1;
    }
    StreamPreviewWidget .dot-active  { color: #22cc44; }
    StreamPreviewWidget .dot-warn    { color: #ffaa00; }
    StreamPreviewWidget .dot-error   { color: #ff4444; }
    StreamPreviewWidget .dot-idle    { color: #666666; }
    """

    def __init__(
        self,
        stream_id: str = "",
        url: str = "",
        status: str = "idle",   # "active" | "warn" | "error" | "idle"
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.stream_id = stream_id
        self.url = url
        self.status = status

    def render(self) -> str:
        dot_map = {
            "active": "●",
            "warn": "●",
            "error": "●",
            "idle": "○",
        }
        color_map = {
            "active": "[#22cc44]",
            "warn": "[#ffaa00]",
            "error": "[#ff4444]",
            "idle": "[#666666]",
        }
        dot = dot_map.get(self.status, "○")
        color = color_map.get(self.status, "[#666666]")
        end = "[/]"
        url_display = self.url[:50] + "…" if len(self.url) > 51 else self.url
        return f"{color}{dot}{end} [{self.stream_id}] {url_display}"

    def update_status(self, status: str, url: str = "") -> None:
        self.status = status
        if url:
            self.url = url
        self.refresh()
