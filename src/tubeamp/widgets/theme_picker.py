"""Theme picker screen — modal for selecting color themes."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from tubeamp.themes import Theme, get_theme
from tubeamp.widgets._modal import ThemedModal


class ThemePickerScreen(ThemedModal):
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

    def __init__(self, current_theme: Theme, theme_names: list[str], **kwargs: object) -> None:
        super().__init__(current_theme, **kwargs)
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
        theme = self._theme
        self.paint("#theme-dialog", border=theme.primary)
        self.paint("#theme-title", color=theme.primary)
        self.paint("#theme-hint", color=theme.primary_dim)
        theme_list = self.paint("#theme-list", border=theme.primary_dim)
        theme_list.focus()

        for idx, name in enumerate(self._theme_names):
            if name.lower() == theme.name.lower():
                theme_list.highlighted = idx  # type: ignore[attr-defined]
                break

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.dismiss(str(event.option.id))
