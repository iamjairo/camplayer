import itertools
import asyncio

from textual.app import ComposeResult
from textual.widgets import Static
from textual import work


class SpinnerWidget(Static):
    """
    Animated spinner widget for indicating async task progress.

    Call start() to begin spinning and stop() to halt with an optional message.
    """

    FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    INTERVAL = 0.1

    DEFAULT_CSS = """
    SpinnerWidget {
        height: 1;
        color: #4488ff;
    }
    """

    def __init__(self, label: str = "Working…", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self._running = False
        self._task: asyncio.Task | None = None

    def render(self) -> str:
        return self._current_text

    def on_mount(self) -> None:
        self._current_text = ""

    def start(self, label: str | None = None) -> None:
        if label:
            self.label = label
        self._running = True
        self._spin()

    def stop(self, message: str = "") -> None:
        self._running = False
        self._current_text = message
        self.refresh()

    @work(exclusive=True)
    async def _spin(self) -> None:
        for frame in itertools.cycle(self.FRAMES):
            if not self._running:
                break
            self._current_text = f"{frame} {self.label}"
            self.refresh()
            await asyncio.sleep(self.INTERVAL)
