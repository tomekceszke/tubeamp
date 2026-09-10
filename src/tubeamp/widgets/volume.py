"""Volume bar widget - horizontal volume indicator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from tubeamp.themes import DEFAULT_THEME
from tubeamp.widgets._color import gradient_steps

if TYPE_CHECKING:
    from textual.events import Click


# Layout: "VOL: " (5 chars) + bar (dynamic) + " NNN%" (5 chars)
_VOL_BAR_START = 5
_VOL_LABEL_WIDTH = 5  # "VOL: "
_VOL_SUFFIX_WIDTH = 5  # " NNN%"


class VolumeWidget(Static):
    """Horizontal volume bar display.

    Shows current volume level with a horizontal bar indicator.
    """

    DEFAULT_CSS = """
    VolumeWidget {
        height: auto;
        width: 100%;
    }
    """

    class VolumeChanged(Message):
        """Fired when user clicks the volume bar to set volume."""

        def __init__(self, volume: int) -> None:
            super().__init__()
            self.volume = volume

    volume: reactive[int] = reactive(80)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._bar_color = DEFAULT_THEME.primary_dim
        self._bar_color_top = DEFAULT_THEME.primary_bright
        self._dim = DEFAULT_THEME.text_dim

    def set_theme(
        self, bar_color: str, bar_color_top: str = "", dim: str = ""
    ) -> None:
        """Set theme colors for the volume bar."""
        self._bar_color = bar_color
        self._bar_color_top = bar_color_top or bar_color
        self._dim = dim or bar_color
        self.update_bar()

    def watch_volume(self, _: int) -> None:
        self.update_bar()

    def _get_bar_width(self) -> int:
        """Calculate dynamic bar width based on container width."""
        content_w = self.size.width - 2 if self.size.width > 10 else 40
        return max(10, content_w - _VOL_LABEL_WIDTH - _VOL_SUFFIX_WIDTH)

    def on_click(self, event: Click) -> None:
        """Handle click on volume bar to set volume."""
        x = event.x
        bar_width = self._get_bar_width()
        if _VOL_BAR_START <= x < _VOL_BAR_START + bar_width:
            fraction = (x - _VOL_BAR_START) / bar_width
            new_volume = int(max(0, min(100, fraction * 100)))
            self.post_message(self.VolumeChanged(new_volume))

    def on_mount(self) -> None:
        """Initialize the bar on mount."""
        self.update_bar()

    def on_resize(self) -> None:
        """Re-render when container resizes."""
        self.update_bar()

    def update_bar(self) -> None:
        """Update the volume bar display."""
        bar_width = self._get_bar_width()
        constrained_volume = max(0, min(100, self.volume))
        filled = int(constrained_volume / 100 * bar_width)

        filled_bar = "".join(
            f"[{color}]█[/]"
            for color in gradient_steps(
                self._bar_color, self._bar_color_top, filled, bar_width
            )
        )
        empty = "░" * (bar_width - filled)
        empty_bar = f"[{self._dim}]{empty}[/]" if empty else ""

        self.update(
            f"[{self._dim}]VOL:[/] {filled_bar}{empty_bar} "
            f"[bold]{constrained_volume:3d}%[/]"
        )
