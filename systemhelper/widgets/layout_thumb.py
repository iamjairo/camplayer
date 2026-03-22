from textual.widgets import Static

# ASCII art thumbnails for each layout type.
# Each thumbnail is 7 wide × 4 tall characters (inside a border).
_LAYOUTS: dict[int, str] = {
    1: (
        "┌─────┐\n"
        "│     │\n"
        "│  1  │\n"
        "└─────┘"
    ),
    4: (
        "┌──┬──┐\n"
        "│1 │2 │\n"
        "│3 │4 │\n"
        "└──┴──┘"
    ),
    6: (
        "┌───┬─┐\n"
        "│   │2│\n"
        "│ 1 │3│\n"
        "└───┴─┘"
    ),
    7: (
        "┌─┬─┬─┐\n"
        "│ 1 │2│\n"
        "│3│4│5│\n"
        "└─┴─┴─┘"
    ),
    8: (
        "┌───┬─┐\n"
        "│   │2│\n"
        "│ 1 │─┤\n"
        "│   │3│\n"
        "└───┴─┘"
    ),
    9: (
        "┌─┬─┬─┐\n"
        "│1│2│3│\n"
        "│4│5│6│\n"
        "│7│8│9│\n"
        "└─┴─┴─┘"
    ),
    10: (
        "┌──┬─┬─┐\n"
        "│  │2│3│\n"
        "│1 │─┼─│\n"
        "│  │4│5│\n"
        "└──┴─┴─┘"
    ),
    13: (
        "┌──┬┬┬┐\n"
        "│  │││6│\n"
        "│1 │││─│\n"
        "└──┴┴┴┘"
    ),
    16: (
        "┌─┬─┬─┬─┐\n"
        "│1│2│3│4│\n"
        "│5│6│7│8│\n"
        "└─┴─┴─┴─┘"
    ),
}

_LAYOUT_NAMES: dict[int, str] = {
    1: "Single",
    4: "2×2 Grid",
    6: "PiP 1+5",
    7: "PiP 3+4",
    8: "PiP 1+7",
    9: "3×3 Grid",
    10: "PiP 2+8",
    13: "PiP 1+12",
    16: "4×4 Grid",
}


class LayoutThumbWidget(Static):
    """
    ASCII-art layout thumbnail widget.
    Renders a compact visual preview of a given layout type.
    """

    DEFAULT_CSS = """
    LayoutThumbWidget {
        border: solid #1a2a4a;
        padding: 0 1;
        margin: 0 1;
        color: #4488ff;
        width: 12;
        height: 7;
    }
    LayoutThumbWidget.selected {
        border: solid #4488ff;
        color: #ffffff;
    }
    """

    def __init__(self, layout_id: int, selected: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.layout_id = layout_id
        self.selected = selected
        if selected:
            self.add_class("selected")

    def render(self) -> str:
        art = _LAYOUTS.get(self.layout_id, "?")
        name = _LAYOUT_NAMES.get(self.layout_id, f"Layout {self.layout_id}")
        return f"{name}\n{art}"

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")
        self.refresh()
