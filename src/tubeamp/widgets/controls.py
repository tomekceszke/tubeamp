"""Playback controls widget — stop, play, pause, next, shuffle, repeat."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from rich.text import Text
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

if TYPE_CHECKING:
    from rich.console import RenderableType
    from textual.events import Click


_BOX_WIDTH = 7  # "┌─────┐"

# Gap tiers, widest first: (gap between buttons, gap between the transport and
# mode groups). The widest tier that fits the content area wins, so the boxed
# layout survives down to a 35-column player before the compact fallbacks.
_GAP_TIERS: tuple[tuple[int, int], ...] = ((2, 4), (1, 2), (1, 1), (0, 1), (0, 0))


class _Button(NamedTuple):
    name: str
    glyph: str


_BUTTONS: tuple[_Button, ...] = (
    _Button("stop", "■"),
    _Button("play_pause", "▶"),
    _Button("pause", "⏸"),
    _Button("shuffle", "S"),
    _Button("repeat", "R"),
)

# The wider gap goes after this button, splitting transport from mode controls
_GROUP_BREAK_AFTER = "pause"


class _Layout(NamedTuple):
    """Resolved button geometry for one content width."""

    style: str          # "boxed" | "bracket" | "glyph"
    cell_width: int
    left_pad: int
    gaps: tuple[int, ...]   # gap following each button except the last

    def positions(self) -> dict[str, tuple[int, int]]:
        """Start/end column of every button, in content-area coordinates."""
        spans: dict[str, tuple[int, int]] = {}
        x = self.left_pad
        for i, button in enumerate(_BUTTONS):
            spans[button.name] = (x, x + self.cell_width - 1)
            x += self.cell_width + (self.gaps[i] if i < len(self.gaps) else 0)
        return spans


def _resolve_layout(width: int) -> _Layout:
    """Pick the richest button layout that fits `width` columns without wrapping.

    The widget is a fixed three rows tall. Anything wider than the content area
    is wrapped by Rich onto the next line, which pushes the middle row down and
    drops the bottom border off the bottom of the widget — so the layout has to
    shrink instead of overflowing.
    """
    for cell, style in ((_BOX_WIDTH, "boxed"), (3, "bracket"), (1, "glyph")):
        for gap, group_gap in _GAP_TIERS:
            gaps = tuple(
                group_gap if b.name == _GROUP_BREAK_AFTER else gap
                for b in _BUTTONS[:-1]
            )
            total = cell * len(_BUTTONS) + sum(gaps)
            if total <= width:
                return _Layout(style, cell, max(0, (width - total) // 2), gaps)

    # Narrower than even bare glyphs with no gaps — render what fits and crop.
    return _Layout("glyph", 1, 0, tuple(0 for _ in _BUTTONS[:-1]))


class ControlsWidget(Widget):
    """Playback control bar with visual state indicators.

    Layout:
        ┌─────┐  ┌─────┐  ┌─────┐    ┌─────┐  ┌─────┐
        │  ■  │  │  ▶  │  │  ⏸  │    │  S  │  │  R  │
        └─────┘  └─────┘  └─────┘    └─────┘  └─────┘

    Gaps tighten as the player narrows, then the boxes are dropped for
    bracketed and finally bare glyphs, so the borders never wrap.
    """

    DEFAULT_CSS = """
    ControlsWidget {
        height: 3;
        width: 1fr;
        padding: 0 1;
    }
    """

    class StopClicked(Message):
        """Fired when the stop button is clicked."""

    class PlayPauseClicked(Message):
        """Fired when the play/pause button is clicked."""

    class ShuffleClicked(Message):
        """Fired when the shuffle button is clicked."""

    class RepeatClicked(Message):
        """Fired when the repeat button is clicked."""

    playback_state: reactive[str] = reactive("stopped")  # stopped, playing, paused
    shuffle: reactive[bool] = reactive(False)
    repeat_mode: reactive[str] = reactive("off")  # off, all, one
    volume: reactive[int] = reactive(80)

    _MESSAGES = {
        "stop": StopClicked,
        "play_pause": PlayPauseClicked,
        "pause": PlayPauseClicked,
        "shuffle": ShuffleClicked,
        "repeat": RepeatClicked,
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Theme colors
        self._primary = "#00ff00"
        self._shuffle_active = "#00ffff"
        self._repeat_all = "#ffff00"
        self._repeat_one = "#ff00ff"

    def set_theme(
        self, primary: str, shuffle_active: str, repeat_all: str, repeat_one: str
    ) -> None:
        """Set theme colors for the controls."""
        self._primary = primary
        self._shuffle_active = shuffle_active
        self._repeat_all = repeat_all
        self._repeat_one = repeat_one
        self.refresh()

    def watch_playback_state(self, _: str) -> None:
        self.refresh()

    def watch_shuffle(self, _: bool) -> None:
        self.refresh()

    def watch_repeat_mode(self, _: str) -> None:
        self.refresh()

    def watch_volume(self, _: int) -> None:
        self.refresh()

    def on_resize(self) -> None:
        self.refresh()

    def _layout(self) -> _Layout:
        # `size` is the content area, padding already excluded.
        return _resolve_layout(self.size.width)

    def on_click(self, event: Click) -> None:
        """Handle mouse clicks on control buttons."""
        # Click coordinates include the widget's padding; the layout is in
        # content coordinates, so shift by the left padding.
        x = event.x - self.styles.padding.left
        for name, (x_start, x_end) in self._layout().positions().items():
            if x_start <= x <= x_end:
                self.post_message(self._MESSAGES[name]())
                return

    def _active_color(self, name: str) -> str | None:
        """Theme color for a button that is currently engaged, else None."""
        if name == "stop" and self.playback_state == "stopped":
            return self._primary
        if name == "play_pause" and self.playback_state == "playing":
            return self._primary
        if name == "pause" and self.playback_state == "paused":
            return self._primary
        if name == "shuffle" and self.shuffle:
            return self._shuffle_active
        if name == "repeat" and self.repeat_mode == "all":
            return self._repeat_all
        if name == "repeat" and self.repeat_mode == "one":
            return self._repeat_one
        return None

    def _cell(self, button: _Button, layout: _Layout, row: int) -> str:
        """One button's text for the given row of the three-row band."""
        if layout.style == "boxed":
            text = ("┌─────┐", f"│  {button.glyph}  │", "└─────┘")[row]
        elif layout.style == "bracket":
            text = "   " if row != 1 else f"[{button.glyph}]"
        else:
            text = " " if row != 1 else button.glyph

        color = self._active_color(button.name)
        if color is None:
            return text
        # Escape nothing here: glyphs and box characters carry no markup
        return f"[bold {color}]{text}[/]"

    def render(self) -> RenderableType:
        """Render Winamp-style control buttons, sized to the current width."""
        layout = self._layout()
        pad = " " * layout.left_pad

        rows: list[str] = []
        for row in range(3):
            parts: list[str] = [pad]
            for i, button in enumerate(_BUTTONS):
                parts.append(self._cell(button, layout, row))
                if i < len(layout.gaps):
                    parts.append(" " * layout.gaps[i])
            rows.append("".join(parts))

        text = Text.from_markup("\n".join(rows))
        # Belt and braces: never let a wide row wrap into the row below it.
        text.no_wrap = True
        text.overflow = "crop"
        return text
