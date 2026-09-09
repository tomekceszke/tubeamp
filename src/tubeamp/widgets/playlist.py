"""Playlist widget — scrollable list of tracks with selection."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from rich.text import Text

logger = logging.getLogger(__name__)
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from tubeamp.utils import marquee, scroll_offset

# Fixed-width columns: prefix(1) + selector(1) + num(3) + ". "(2) + " "(1) + dur(8) = 16
FIXED_COLUMN_WIDTH = 16


@dataclass
class PlaylistEntry:
    """A single entry in the playlist."""

    title: str
    channel: str
    duration_str: str
    url: str
    video_id: str = ""


class PlaylistWidget(Widget):
    """Scrollable playlist display with selection and now-playing indicator.

    Layout:
        ▶ 1. Around the World — Daft Punk          7:09
          2. Da Funk — Daft Punk                    5:28
          3. Revolution 909 — Daft Punk             5:26
          ...
    """

    DEFAULT_CSS = """
    PlaylistWidget {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
        layout: vertical;
    }

    #playlist-scroll {
        height: 1fr;
        width: 1fr;
        scrollbar-size-vertical: 1;
        scrollbar-gutter: auto;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
        scrollbar-color: #006400;
        scrollbar-color-hover: #008000;
        scrollbar-color-active: #00ff00;
    }

    #playlist-content {
        width: 1fr;
    }

    #playlist-spacer {
        height: 2;
        background: transparent;
    }
    """

    selected_index: reactive[int] = reactive(0)
    playing_index: reactive[int] = reactive(-1)
    text_scroll_offset: reactive[int] = reactive(0)

    # ── Messages ────────────────────────────────────────────────

    class TrackSelected(Message):
        """Fired when user confirms selection on a track."""

        def __init__(self, index: int, entry: PlaylistEntry) -> None:
            super().__init__()
            self.index = index
            self.entry = entry

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._entries: list[PlaylistEntry] = []
        self._scroll_timer = None
        self._spinner_timer = None
        self._spinner_frames = ["|", "/", "-", "\\"]
        self._spinner_index = 0
        self._is_loading = False
        # Theme colors
        self._selection_bg = "#00ff00"
        self._selection_fg = "#000000"
        self._playing_color = "#00ff00"

    def set_theme(self, selection_bg: str, selection_fg: str, playing_color: str) -> None:
        """Set theme colors for the playlist."""
        self._selection_bg = selection_bg
        self._selection_fg = selection_fg
        self._playing_color = playing_color

        # Update scrollbar colors - use very dim color for subtle appearance
        try:
            scroll = self.query_one("#playlist-scroll")
            # Use very dim color (20% opacity approximation) for thin line appearance
            scroll.styles.scrollbar_color = "#333333"
            scroll.styles.scrollbar_color_hover = playing_color
            scroll.styles.scrollbar_color_active = playing_color
        except Exception:
            pass

        self._refresh_display()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="playlist-scroll", can_focus=False):
            yield Static("No playlist loaded. Press / to search.", id="playlist-content")
        yield Static("", id="playlist-spacer")

    def set_entries(self, entries: list[PlaylistEntry], reset: bool = False) -> None:
        """Replace the entire playlist.

        Args:
            entries: New playlist entries.
            reset: If True, reset selection to first item and scroll to top.
        """
        self._entries = list(entries)
        if reset:
            self.selected_index = 0
            self.playing_index = -1
            try:
                scroll = self.query_one("#playlist-scroll", VerticalScroll)
                scroll.scroll_to(y=0, animate=False)
            except Exception:
                logger.debug("Could not scroll playlist to top")
        elif self.selected_index >= len(self._entries):
            self.selected_index = max(0, len(self._entries) - 1)
        self._refresh_display()

    def append_entry(self, entry: PlaylistEntry) -> None:
        """Add a track to the end of the playlist."""
        self._entries.append(entry)
        self._refresh_display()

    def set_loading(self, loading: bool) -> None:
        """Set loading state to show/hide spinner."""
        self._is_loading = loading
        self._refresh_display()

    def select_next(self) -> None:
        if self._entries:
            self.selected_index = min(self.selected_index + 1, len(self._entries) - 1)

    def select_prev(self) -> None:
        if self._entries:
            self.selected_index = max(self.selected_index - 1, 0)

    def select_page_down(self) -> None:
        """Move selection down by one page."""
        if not self._entries:
            return
        page_size = max(1, self.size.height - 1)  # -1 for padding
        self.selected_index = min(self.selected_index + page_size, len(self._entries) - 1)

    def select_page_up(self) -> None:
        """Move selection up by one page."""
        if not self._entries:
            return
        page_size = max(1, self.size.height - 1)  # -1 for padding
        self.selected_index = max(self.selected_index - page_size, 0)

    def select_first(self) -> None:
        """Move selection to the first track."""
        if self._entries:
            self.selected_index = 0

    def select_last(self) -> None:
        """Move selection to the last track."""
        if self._entries:
            self.selected_index = len(self._entries) - 1

    def confirm_selection(self) -> None:
        """Trigger playback of the selected track."""
        if 0 <= self.selected_index < len(self._entries):
            entry = self._entries[self.selected_index]
            self.post_message(self.TrackSelected(self.selected_index, entry))

    def watch_selected_index(self, _: int) -> None:
        self.text_scroll_offset = 0  # Reset scroll when selection changes
        self._refresh_display()
        self._scroll_to_selected()

    def watch_playing_index(self, _: int) -> None:
        self._refresh_display()

    def on_mount(self) -> None:
        """Ensure display refreshes after widget is properly sized."""
        self._refresh_display()
        if self._scroll_timer:
            self._scroll_timer.stop()
        self._scroll_timer = self.set_interval(0.3, self._update_scroll)
        if self._spinner_timer:
            self._spinner_timer.stop()
        self._spinner_timer = self.set_interval(0.1, self._update_spinner)

    def on_unmount(self) -> None:
        """Stop scrolling timer when unmounted."""
        if self._scroll_timer:
            self._scroll_timer.stop()
        if self._spinner_timer:
            self._spinner_timer.stop()

    def on_resize(self) -> None:
        """Refresh display when widget is resized."""
        self._refresh_display()

    def on_click(self, event: Click) -> None:
        """Handle mouse clicks on playlist items."""
        if not self._entries:
            return

        try:
            scroll = self.query_one("#playlist-scroll", VerticalScroll)
            clicked_line = event.y + int(scroll.scroll_y)
        except Exception as e:
            logger.debug("Could not get scroll position: %s", e)
            clicked_line = event.y

        if 0 <= clicked_line < len(self._entries):
            self.selected_index = clicked_line
            self.confirm_selection()

    def _info_width(self) -> int:
        widget_width = self.size.width - 2 if self.size.width > 20 else 116
        return widget_width - FIXED_COLUMN_WIDTH

    def _update_scroll(self) -> None:
        """Advance the marquee on the selected entry."""
        if not self._entries or self.selected_index < 0:
            return

        self.text_scroll_offset = scroll_offset(
            self._entries[self.selected_index].title,
            self.text_scroll_offset,
            self._info_width(),
        )

    def watch_text_scroll_offset(self, _: int) -> None:
        self._refresh_display()

    def _update_spinner(self) -> None:
        """Update spinner animation frame."""
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        if self._is_loading:
            self._refresh_display()

    def _scroll_to_selected(self) -> None:
        """Scroll the widget to ensure the selected item is visible."""
        if not self._entries or self.selected_index < 0:
            return

        try:
            scroll_container = self.query_one("#playlist-scroll", VerticalScroll)
        except Exception as e:
            logger.debug("Could not scroll to selected: %s", e)
            return

        # Each line is 1 row tall in the terminal
        line_y = self.selected_index

        # Get the visible height and current scroll position
        visible_height = scroll_container.size.height
        current_scroll = scroll_container.scroll_y

        # Calculate the visible range
        visible_start = current_scroll
        visible_end = current_scroll + visible_height - 1

        # Only scroll if the selected line is outside the visible range
        if line_y < visible_start:
            # Selected line is above visible area - scroll up to show it at top
            scroll_container.scroll_to(y=line_y, animate=False)
        elif line_y > visible_end:
            # Selected line is below visible area - scroll down to show it at bottom
            scroll_container.scroll_to(y=line_y - visible_height + 1, animate=False)

    def _refresh_display(self) -> None:
        try:
            content = self.query_one("#playlist-content", Static)
        except Exception:
            return

        if not self._entries:
            if self._is_loading:
                spinner = self._spinner_frames[self._spinner_index]
                content.update(f"{spinner} Loading default playlist...")
            else:
                content.update("No playlist loaded. Press / to search.")
            return

        # Calculate available width for playlist items
        # Widget width minus padding (2 chars left/right) and scrollbar space (2 chars)
        # Use actual width if available (> 20), otherwise use generous default
        widget_width = self.size.width - 2 if self.size.width > 20 else 116

        lines: list[Text] = []
        for i, entry in enumerate(self._entries):
            # Playing indicator
            prefix = "▶" if i == self.playing_index else " "

            # Selection indicator
            selector = "›" if i == self.selected_index else " "

            # Track number (padded)
            num = f"{i + 1:>3}"

            # Duration right-aligned (8 chars: " HH:MM:SS" or "  MM:SS")
            dur = f"{entry.duration_str:>8}"

            info = entry.title
            available_for_info = widget_width - FIXED_COLUMN_WIDTH

            if i == self.selected_index:
                info = marquee(info, self.text_scroll_offset, available_for_info)
            elif len(info) > available_for_info:
                info = info[:available_for_info - 3] + "..."

            # Build the line with proper spacing (as plain text)
            # Left part: indicators + number + info
            left_part = f"{prefix}{selector}{num}. {info}"
            # Right part: duration
            # Calculate spaces needed to push duration to the right
            spaces_needed = widget_width - len(left_part) - len(dur)
            if spaces_needed < 1:
                spaces_needed = 1

            line_content = f"{left_part}{' ' * spaces_needed}{dur}"

            # Create Rich Text object and apply styling
            text_obj = Text(line_content)

            # Apply styling to the entire line
            if i == self.selected_index:
                # Selected item with theme colors
                text_obj.stylize(f"bold {self._selection_fg} on {self._selection_bg}")
            elif i == self.playing_index:
                # Currently playing track with theme color
                text_obj.stylize(self._playing_color)

            lines.append(text_obj)

        # Add loading indicator at the bottom if loading more tracks
        if self._is_loading:
            spinner = self._spinner_frames[self._spinner_index]
            loading_text = Text(f"\n{spinner} Loading more tracks...", style="dim italic")
            lines.append(loading_text)

        # Join Text objects properly
        combined = Text("\n").join(lines)
        content.update(combined)
