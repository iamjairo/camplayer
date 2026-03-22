from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Horizontal


class CameraRowWidget(Static):
    """
    A single camera row in the camera list, showing:
    - Index/ID
    - Camera name
    - Main stream URL (truncated)
    - Brand indicator
    """

    DEFAULT_CSS = """
    CameraRowWidget {
        height: 1;
        padding: 0 1;
    }
    CameraRowWidget:hover {
        background: #1a2a4a;
    }
    CameraRowWidget.selected {
        background: #1a3a6a;
        color: #ffffff;
    }
    """

    def __init__(
        self,
        device_id: int,
        channel_num: int,
        name: str = "",
        url: str = "",
        brand: str = "",
        selected: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.device_id = device_id
        self.channel_num = channel_num
        self.cam_name = name
        self.cam_url = url
        self.brand = brand
        self.selected = selected
        if selected:
            self.add_class("selected")

    def render(self) -> str:
        brand_icon = {
            "hikvision": "[H]",
            "reolink": "[R]",
            "dahua": "[D]",
            "onvif": "[O]",
        }.get(self.brand.lower(), "[ ]")

        url_display = self.cam_url[:40] + "…" if len(self.cam_url) > 41 else self.cam_url
        return (
            f"{brand_icon} D{self.device_id}/CH{self.channel_num} "
            f"{self.cam_name:<20} {url_display}"
        )

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")
        self.refresh()
