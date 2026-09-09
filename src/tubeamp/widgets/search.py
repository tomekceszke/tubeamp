"""Search screen — modal input for YouTube search queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.widgets import Input, Label, Static

from tubeamp.widgets._modal import ThemedModal

if TYPE_CHECKING:
    from textual.app import ComposeResult



class SearchScreen(ThemedModal):
    """Modal screen for entering a YouTube search query.

    Returns the search query string, or None if cancelled.
    """

    DEFAULT_CSS = """
    SearchScreen {
        align: center middle;
    }

    #search-dialog {
        width: 80;
        height: 11;
        background: #0a0a0a;
        padding: 1 2;
    }

    #search-title {
        text-style: bold;
        width: 100%;
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
    }

    #search-input {
        margin-top: 1;
        height: 3;
        width: 100%;
        background: #1a1a1a;
    }

    #search-hint {
        margin-top: 1;
        text-align: center;
        width: 100%;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="search-dialog"):
            yield Label("🔍 Search YouTube", id="search-title")
            yield Input(
                placeholder="artist, song, playlist URL...",
                id="search-input",
            )
            yield Static("Enter to search · Esc to cancel", id="search-hint")

    def on_mount(self) -> None:
        theme = self._theme
        self.paint("#search-dialog", border=theme.primary)
        self.paint("#search-title", color=theme.primary)
        self.paint("#search-hint", color=theme.primary_dim)
        self.paint(
            "#search-input", color=theme.primary, border=theme.primary_dim
        ).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.dismiss(query)
        else:
            self.dismiss(None)
