"""Theme picker screen — modal for selecting color themes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from tubeamp.themes import Theme, get_theme
from tubeamp.theming import apply_theme
from tubeamp.widgets._modal import ThemedModal

if TYPE_CHECKING:
    from textual.app import ComposeResult


# Widest display name plus breathing room, so the swatches line up in a column
_NAME_WIDTH = 16
_SWATCH = "██"


class ThemePickerScreen(ThemedModal):
    """Modal screen for selecting a color theme.

    Returns the selected theme key, or None if cancelled. Moving the highlight
    repaints the player behind the dialog, so a theme is judged on the real UI
    rather than on its name; cancelling puts the original back.
    """

    DEFAULT_CSS = """
    ThemePickerScreen {
        align: center middle;
    }

    #theme-dialog {
        width: 50;
        height: 20;
        background: $surface;
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
        background: $panel;
    }

    /* The default block cursor paints a solid bar in the theme's own accent,
       which swallows an option whose name is drawn in that same accent. A
       tint keeps every name and swatch legible on the highlighted row. */
    #theme-list > .option-list--option-highlighted {
        background: $primary 30%;
        text-style: bold;
    }

    #theme-list:focus > .option-list--option-highlighted {
        background: $primary 45%;
    }

    #theme-hint {
        margin-top: 1;
        text-align: center;
        width: 100%;
        height: 1;
    }
    """

    def __init__(self, current_theme: Theme, theme_keys: list[str], **kwargs: Any) -> None:
        super().__init__(current_theme, **kwargs)
        self._theme_keys = theme_keys

    @staticmethod
    def _option_label(theme: Theme) -> Text:
        """Theme name followed by a strip of its palette."""
        label = Text(theme.name.ljust(_NAME_WIDTH), style=f"bold {theme.primary}")
        for color in (
            theme.primary,
            theme.primary_bright,
            theme.shuffle_active,
            theme.selection_bg,
            theme.background_light,
        ):
            label.append(_SWATCH, style=color)
        return label

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-dialog"):
            yield Label("🎨 Select Theme", id="theme-title")
            options = [
                Option(self._option_label(get_theme(key)), id=key)
                for key in self._theme_keys
            ]
            yield OptionList(*options, id="theme-list")
            yield Label("Enter to select · Esc to cancel", id="theme-hint")

    def on_mount(self) -> None:
        theme = self._theme
        self.paint("#theme-dialog", border=theme.primary)
        self.paint("#theme-title", color=theme.primary)
        self.paint("#theme-hint", color=theme.primary_dim)
        theme_list = self.paint("#theme-list", border=theme.primary_dim)
        theme_list.focus()

        for idx, key in enumerate(self._theme_keys):
            if key == theme.key:
                theme_list.highlighted = idx  # type: ignore[attr-defined]
                break

    def _preview(self, theme: Theme) -> None:
        """Repaint the player under the dialog, and the dialog with it."""
        apply_theme(self.app, theme)
        self.paint("#theme-dialog", border=theme.primary)
        self.paint("#theme-title", color=theme.primary)
        self.paint("#theme-hint", color=theme.primary_dim)
        self.paint("#theme-list", border=theme.primary_dim)

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if event.option.id:
            self._preview(get_theme(str(event.option.id)))

    def action_cancel(self) -> None:
        self._preview(self._theme)
        super().action_cancel()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.dismiss(str(event.option.id))
