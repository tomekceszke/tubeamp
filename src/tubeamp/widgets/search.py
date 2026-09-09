"""Search screen — modal input for YouTube search queries."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static

from tubeamp.themes import Theme


class SearchScreen(ModalScreen[str | None]):
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

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, theme: Theme, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._theme = theme

    def compose(self) -> ComposeResult:
        with Vertical(id="search-dialog"):
            yield Label("🔍 Search YouTube", id="search-title")
            yield Input(
                placeholder="artist, song, playlist URL...",
                id="search-input",
            )
            yield Static("Enter to search · Esc to cancel", id="search-hint")

    def on_mount(self) -> None:
        dialog = self.query_one("#search-dialog")
        dialog.styles.border = ("solid", self._theme.primary)
        dialog.refresh()

        title = self.query_one("#search-title", Label)
        title.styles.color = self._theme.primary
        title.refresh()

        search_input = self.query_one("#search-input", Input)
        search_input.styles.color = self._theme.primary
        search_input.styles.border = ("solid", self._theme.primary_dim)
        search_input.refresh()

        hint = self.query_one("#search-hint", Static)
        hint.styles.color = self._theme.primary_dim
        hint.refresh()

        search_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.dismiss(query)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
