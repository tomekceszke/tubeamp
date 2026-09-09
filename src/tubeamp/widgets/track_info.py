"""Track info widget — displays current track title, artist, and seek bar."""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from tubeamp.utils import format_time, marquee, scroll_offset
from tubeamp.widgets._color import hex_to_rgb, lerp_color


class TrackInfoWidget(Widget):
    """Displays current track metadata and a seek progress bar.

    Layout:
        Title - Artist
        ────────────●──────── 2:34 / 7:09
    """

    DEFAULT_CSS = """
    TrackInfoWidget {
        width: 1fr;
        padding: 0 1;
    }

    """

    class SeekRequested(Message):
        """Fired when user clicks the progress bar to seek."""

        def __init__(self, position: float) -> None:
            super().__init__()
            self.position = position

    title: reactive[str] = reactive("No track loaded")
    artist: reactive[str] = reactive("")
    position: reactive[float] = reactive(0.0)
    duration: reactive[float] = reactive(0.0)
    text_scroll_offset: reactive[int] = reactive(0)

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._scroll_timer = None
        self._primary = "#00ff00"
        self._primary_dim = "#00ff00"

    def set_theme(self, primary: str, primary_dim: str = "") -> None:
        """Set theme colors for the track info."""
        self._primary = primary
        self._primary_dim = primary_dim or primary
        self.refresh()

    def on_mount(self) -> None:
        """Start scrolling timer when mounted."""
        if self._scroll_timer:
            self._scroll_timer.stop()
        self._scroll_timer = self.set_interval(0.3, self._update_scroll)

    def on_unmount(self) -> None:
        """Stop scrolling timer when unmounted."""
        if self._scroll_timer:
            self._scroll_timer.stop()

    def _time_string(self) -> str:
        if self.duration <= 0:
            return ""
        return f"{format_time(self.position)} / {format_time(self.duration)}"

    def _content_width(self) -> int:
        return self.size.width - 2 if self.size.width > 4 else 80

    def _title_width(self) -> int:
        """Columns the title may occupy, once the time display is reserved.

        Both the scroll timer and render() must agree on this. They used to
        compute it differently — and scroll off a different string as well —
        so the marquee jumped whenever a track had an artist set.
        """
        total = self._content_width()
        time_str = self._time_string()
        return max(20, total - (len(time_str) + 2)) if time_str else total

    def _update_scroll(self) -> None:
        self.text_scroll_offset = scroll_offset(
            self.title, self.text_scroll_offset, self._title_width()
        )

    def update_track(self, title: str, artist: str = "", duration: float = 0.0) -> None:
        """Update track metadata."""
        self.title = title
        self.artist = artist
        self.duration = duration
        self.text_scroll_offset = 0

    def update_position(self, pos: float) -> None:
        """Update current playback position."""
        self.position = pos

    def watch_title(self, _: str) -> None:
        self.refresh()

    def watch_artist(self, _: str) -> None:
        self.refresh()

    def watch_position(self, _: float) -> None:
        self.refresh()

    def watch_duration(self, _: float) -> None:
        self.refresh()

    def watch_text_scroll_offset(self, _: int) -> None:
        self.refresh()

    def on_click(self, event: Click) -> None:
        """Handle click on progress bar to seek."""
        if self.duration <= 0:
            return

        # Progress bar is on content row 2 (title row 0, blank row 1, bar row 2)
        if event.y != 2:
            return

        # Map x position to progress fraction
        total_width = self.size.width - 2 if self.size.width > 4 else 80
        bar_width = max(total_width, 10)
        fraction = max(0.0, min(1.0, event.x / bar_width))
        target = fraction * self.duration
        self.post_message(self.SeekRequested(target))

    def render(self) -> RenderableType:
        """Render the title line, the time display and the seek bar."""
        time_str = self._time_string()
        total_width = self._content_width()
        display_title = marquee(self.title, self.text_scroll_offset, self._title_width())

        result = Text()
        spaces_needed = max(2, total_width - len(display_title) - len(time_str))

        result.append(display_title, style=f"bold {self._primary}")
        result.append(" " * spaces_needed)
        result.append(time_str, style="dim")
        result.append("\n\n")  # Blank line before progress bar

        # Progress bar - always show, even when empty
        bar_width = max(total_width, 10)

        if self.duration > 0:
            progress = min(max(self.position / self.duration, 0.0), 1.0)
            filled = int(progress * bar_width)
        else:
            # No track loaded - show empty bar
            filled = 0

        # Progress bar - filled portion with horizontal gradient
        if filled > 0:
            rgb_left = hex_to_rgb(self._primary_dim)
            rgb_right = hex_to_rgb(self._primary)
            for i in range(filled):
                t = i / max(bar_width - 1, 1)
                color = lerp_color(rgb_left, rgb_right, t)
                result.append("█", style=color)
        result.append("░" * (bar_width - filled))

        return result
