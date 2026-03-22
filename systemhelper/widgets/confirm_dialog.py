from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Static
from textual.containers import Horizontal, Vertical


class ConfirmDialog(ModalScreen[bool]):
    """
    Yes/No modal confirmation dialog.

    Usage:
        async def handle():
            confirmed = await self.app.push_screen_wait(
                ConfirmDialog(title="Reboot?", message="Reboot the Pi now?")
            )
            if confirmed:
                ...
    """

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }
    ConfirmDialog > Vertical {
        background: #1a1a2e;
        border: solid #4488ff;
        padding: 1 2;
        width: 50;
        height: auto;
    }
    ConfirmDialog .dialog-title {
        text-style: bold;
        color: #4488ff;
        margin-bottom: 1;
    }
    ConfirmDialog .dialog-message {
        margin-bottom: 1;
    }
    ConfirmDialog Horizontal {
        align: center middle;
        height: auto;
    }
    """

    def __init__(self, title: str = "Confirm", message: str = "Are you sure?", **kwargs):
        super().__init__(**kwargs)
        self.dialog_title = title
        self.dialog_message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.dialog_title, classes="dialog-title")
            yield Static(self.dialog_message, classes="dialog-message")
            with Horizontal():
                yield Button("✓ Yes", id="btn-yes", variant="error")
                yield Button("✗ No", id="btn-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")
