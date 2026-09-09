"""Theme picker screen — modal for selecting color themes."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from tubeamp.themes import Theme, get_theme


class ThemePickerScreen(ModalScreen[str | None]):
    """Modal screen for selecting a color theme.

    Returns the selected theme name, or None if cancelled.
    """

    DEFAULT_CSS = """
    ThemePickerScreen {
        align: center middle;
    }

    #theme-dialog {
        width: 50;
        height: 20;
        background: #0a0a0a;
        padding: 1 2;
    }

    #theme-title {
        text-style: bold;
        width: 100%;
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
    }

    #theme-list {
        width: 100%;
        height: 1fr;
        background: #1a1a1a;
    }

    #theme-hint {
        margin-top: 1;
        text-align: center;
        width: 100%;
        height: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_theme: Theme, theme_names: list[str], **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._current_theme_obj = current_theme
        self._current_theme = current_theme.name
        self._theme_names = theme_names

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-dialog"):
            yield Label("🎨 Select Theme", id="theme-title")
            # Create options with each theme name colored in its primary color
            options = []
            for name in self._theme_names:
                theme = get_theme(name.lower())
                # Create Rich Text with theme color
                colored_name = Text(name, style=f"bold {theme.primary}")
                options.append(Option(colored_name, id=name.lower()))
            yield OptionList(*options, id="theme-list")
            yield Label("Enter to select · Esc to cancel", id="theme-hint")

    def on_mount(self) -> None:
        # Apply current theme colors to dialog
        dialog = self.query_one("#theme-dialog")
        dialog.styles.border = ("solid", self._current_theme_obj.primary)
        dialog.refresh()

        title = self.query_one("#theme-title", Label)
        title.styles.color = self._current_theme_obj.primary
        title.refresh()

        theme_list = self.query_one("#theme-list", OptionList)
        theme_list.styles.border = ("solid", self._current_theme_obj.primary_dim)
        theme_list.refresh()
        theme_list.focus()

        hint = self.query_one("#theme-hint", Label)
        hint.styles.color = self._current_theme_obj.primary_dim
        hint.refresh()

        # Highlight current theme
        for idx, name in enumerate(self._theme_names):
            if name.lower() == self._current_theme.lower():
                theme_list.highlighted = idx
                break

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle theme selection."""
        if event.option.id:
            self.dismiss(str(event.option.id))

    def action_cancel(self) -> None:
        self.dismiss(None)
