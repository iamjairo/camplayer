import os
import sys
from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Label, Select, Static
)
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual import work

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from widgets.layout_thumb import LayoutThumbWidget, _LAYOUT_NAMES


_ALL_LAYOUTS = [1, 4, 6, 7, 8, 9, 10, 13, 16]
# Max windows per layout type
_LAYOUT_WINDOWS = {1: 1, 4: 4, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 13: 13, 16: 16}


class LayoutEditorScreen(Screen):
    """
    Per-screen layout selection and window-to-camera assignment editor.

    Left:   screen list (Screen 1, Screen 2, …)
    Centre: layout picker (thumbnails)
    Right:  window assignment grid (Window N → Device/Channel selectors)
    """

    def compose(self) -> ComposeResult:
        yield Static("◉ Layout Editor", classes="title")
        with Horizontal():
            with Vertical(id="screen-list-panel", classes="panel"):
                yield Label("Screens", classes="section-header")
                yield DataTable(id="screen-table")
                with Horizontal():
                    yield Button("+ Add Screen", id="btn-add-screen", variant="success")
                    yield Button("✕ Delete", id="btn-del-screen", variant="error")
            with Vertical(id="layout-pick-panel", classes="panel"):
                yield Label("Layout", classes="section-header")
                yield ScrollableContainer(id="layout-thumbs")
            with Vertical(id="window-assign-panel", classes="panel"):
                yield Label("Window Assignments", classes="section-header")
                yield DataTable(id="window-table")
        with Horizontal(id="editor-actions"):
            yield Button("💾 Save", id="btn-save", variant="primary")
            yield Static(id="save-status")

    def on_mount(self) -> None:
        self._selected_screen: Optional[int] = None
        self._selected_layout: Optional[int] = None
        self._window_assignments: dict[int, tuple[int, int]] = {}  # win_num → (dev_id, ch_num)

        screen_table = self.query_one("#screen-table", DataTable)
        screen_table.add_columns("Screen", "Display", "Layout")
        screen_table.cursor_type = "row"

        window_table = self.query_one("#window-table", DataTable)
        window_table.add_columns("Window", "Device", "Channel")
        window_table.cursor_type = "row"

        self._build_layout_thumbs()
        self._load_screens()

    def _build_layout_thumbs(self) -> None:
        """Render layout thumbnail widgets in the layout picker panel."""
        container = self.query_one("#layout-thumbs", ScrollableContainer)
        for layout_id in _ALL_LAYOUTS:
            thumb = LayoutThumbWidget(layout_id, id=f"thumb-{layout_id}")
            thumb.can_focus = True
            container.mount(thumb)

    def _load_screens(self) -> None:
        table = self.query_one("#screen-table", DataTable)
        table.clear()
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            for screen in cfg.screens:
                layout_name = _LAYOUT_NAMES.get(int(screen.layout), str(int(screen.layout)))
                table.add_row(
                    f"Screen {screen.id}",
                    str(screen.display),
                    layout_name,
                    key=str(screen.id),
                )
        except Exception as exc:
            self.notify(f"Error loading screens: {exc}", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "screen-table":
            return
        try:
            screen_id = int(str(event.row_key.value))
            self._selected_screen = screen_id
            self._load_screen_editor(screen_id)
        except Exception as exc:
            self.notify(f"Error: {exc}", severity="error")

    def _load_screen_editor(self, screen_id: int) -> None:
        """Load layout selector and window assignments for the given screen."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            screen = next((s for s in cfg.screens if s.id == screen_id), None)
            if not screen:
                return

            self._selected_layout = int(screen.layout)
            self._window_assignments = {
                win: (wa.device_id, wa.channel_num)
                for win, wa in screen.windows.items()
                if wa is not None
            }

            # Highlight selected layout thumb
            for layout_id in _ALL_LAYOUTS:
                thumb = self.query_one(f"#thumb-{layout_id}", LayoutThumbWidget)
                thumb.set_selected(layout_id == self._selected_layout)

            self._populate_window_table(cfg)
        except Exception as exc:
            self.notify(f"Error loading screen: {exc}", severity="error")

    def _populate_window_table(self, cfg) -> None:
        window_table = self.query_one("#window-table", DataTable)
        window_table.clear()
        if self._selected_layout is None:
            return

        num_windows = _LAYOUT_WINDOWS.get(self._selected_layout, 1)
        for win_num in range(1, num_windows + 1):
            if win_num in self._window_assignments:
                dev_id, ch_num = self._window_assignments[win_num]
                dev_str = f"Device {dev_id}"
                ch_str = f"Channel {ch_num}"
            else:
                dev_str, ch_str = "—", "—"
            window_table.add_row(f"Window {win_num}", dev_str, ch_str, key=str(win_num))

    def on_layout_thumb_widget_click(self, event) -> None:
        # Handled via on_click below
        pass

    def on_click(self, event) -> None:
        """Select layout when user clicks a thumbnail."""
        widget = event.widget
        if isinstance(widget, LayoutThumbWidget):
            self._selected_layout = widget.layout_id
            for layout_id in _ALL_LAYOUTS:
                try:
                    thumb = self.query_one(f"#thumb-{layout_id}", LayoutThumbWidget)
                    thumb.set_selected(layout_id == self._selected_layout)
                except Exception:
                    pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-save":
            self._save_layout()
        elif btn_id == "btn-add-screen":
            self._add_screen()
        elif btn_id == "btn-del-screen":
            self._delete_screen()

    def _save_layout(self) -> None:
        if self._selected_screen is None or self._selected_layout is None:
            self.notify("Select a screen and layout first.", severity="warning")
            return
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config, serialize_config
            from models import Layout, WindowAssignment

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            for screen in cfg.screens:
                if screen.id == self._selected_screen:
                    screen.layout = Layout(self._selected_layout)
                    screen.windows = {
                        win: WindowAssignment(device_id=dev, channel_num=ch)
                        for win, (dev, ch) in self._window_assignments.items()
                    }
                    break

            serialize_config(cfg, config_path)
            self._load_screens()
            self.query_one("#save-status", Static).update("✓ Saved")
            self.notify("Layout saved.", severity="information")
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")

    def _add_screen(self) -> None:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config, serialize_config
            from models import Screen as CfgScreen, Layout

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            next_id = max((s.id for s in cfg.screens), default=0) + 1
            cfg.screens.append(CfgScreen(id=next_id, display=1, layout=Layout(1), windows={}))
            serialize_config(cfg, config_path)
            self._load_screens()
            self.notify(f"Added Screen {next_id}.", severity="information")
        except Exception as exc:
            self.notify(f"Add failed: {exc}", severity="error")

    def _delete_screen(self) -> None:
        if self._selected_screen is None:
            self.notify("No screen selected.", severity="warning")
            return
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config, serialize_config

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            cfg.screens = [s for s in cfg.screens if s.id != self._selected_screen]
            serialize_config(cfg, config_path)
            self._selected_screen = None
            self._load_screens()
            self.notify("Screen deleted.", severity="information")
        except Exception as exc:
            self.notify(f"Delete failed: {exc}", severity="error")
