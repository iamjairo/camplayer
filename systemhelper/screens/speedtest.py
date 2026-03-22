import json
import subprocess

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, ProgressBar, Label
from textual import work


class SpeedtestScreen(Screen):
    """Run speedtest-cli and display results live."""

    def compose(self) -> ComposeResult:
        yield Static("◉ Speed Test", classes="title")
        yield Button("▶ Run Speed Test", id="btn-run", variant="primary")
        yield ProgressBar(id="progress", total=100, show_eta=False)
        yield Static(id="result-download")
        yield Static(id="result-upload")
        yield Static(id="result-ping")
        yield Static(id="result-server")
        yield Static(id="result-error", classes="status-error")

    def on_mount(self) -> None:
        self._reset_display()

    def _reset_display(self) -> None:
        for widget_id in ("result-download", "result-upload", "result-ping", "result-server", "result-error"):
            try:
                self.query_one(f"#{widget_id}", Static).update("")
            except Exception:
                pass
        try:
            self.query_one("#progress", ProgressBar).update(progress=0)
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-run":
            self._reset_display()
            self.run_speedtest()

    @work(thread=True)
    def run_speedtest(self) -> None:
        """Run speedtest-cli --json in a worker thread, update UI with results."""
        self.app.call_from_thread(
            self.query_one("#progress", ProgressBar).update, progress=10
        )
        self.app.call_from_thread(
            self.query_one("#result-download", Static).update,
            "Running speedtest… (this may take 30–60 seconds)"
        )

        try:
            proc = subprocess.run(
                ["speedtest-cli", "--json", "--secure"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            self.app.call_from_thread(
                self._show_error, "speedtest-cli not installed. Run: pip3 install speedtest-cli"
            )
            return
        except subprocess.TimeoutExpired:
            self.app.call_from_thread(self._show_error, "Speedtest timed out.")
            return
        except Exception as exc:
            self.app.call_from_thread(self._show_error, str(exc))
            return

        self.app.call_from_thread(
            self.query_one("#progress", ProgressBar).update, progress=90
        )

        if proc.returncode != 0:
            self.app.call_from_thread(
                self._show_error, proc.stderr.strip() or f"speedtest-cli exited {proc.returncode}"
            )
            return

        try:
            data = json.loads(proc.stdout)
            dl_mbps = data["download"] / 1_000_000
            ul_mbps = data["upload"] / 1_000_000
            ping_ms = data["ping"]
            server_name = data.get("server", {}).get("name", "unknown")
            server_country = data.get("server", {}).get("country", "")
        except (json.JSONDecodeError, KeyError) as exc:
            self.app.call_from_thread(self._show_error, f"Failed to parse results: {exc}")
            return

        self.app.call_from_thread(self._update_results, dl_mbps, ul_mbps, ping_ms, server_name, server_country)

    def _update_results(
        self,
        dl: float,
        ul: float,
        ping: float,
        server: str,
        country: str,
    ) -> None:
        self.query_one("#result-download", Static).update(
            f"⬇  Download:  {dl:.2f} Mbps"
        )
        self.query_one("#result-upload", Static).update(
            f"⬆  Upload:    {ul:.2f} Mbps"
        )
        self.query_one("#result-ping", Static).update(
            f"⏱  Ping:      {ping:.1f} ms"
        )
        self.query_one("#result-server", Static).update(
            f"🌐 Server:    {server}{', ' + country if country else ''}"
        )
        self.query_one("#progress", ProgressBar).update(progress=100)
        self.query_one("#result-error", Static).update("")

    def _show_error(self, message: str) -> None:
        self.query_one("#result-error", Static).update(f"✗ {message}")
        self.query_one("#result-download", Static).update("")
        self.query_one("#progress", ProgressBar).update(progress=0)
