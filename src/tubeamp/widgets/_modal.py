"""Shared frame for the app's modal dialogs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.screen import ModalScreen

if TYPE_CHECKING:
    from textual.widget import Widget

    from tubeamp.themes import Theme


class ThemedModal(ModalScreen[str | None]):
    """A modal that dismisses with a string result, or None when cancelled.

    Both dialogs paint the same parts in the same way — a bordered frame, a
    coloured title, a dimmed hint and a focused body — so the repetition of
    `styles.x = …; refresh()` lives here rather than in each screen.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, theme: Theme, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._theme = theme

    def paint(self, selector: str, *, color: str = "", border: str = "") -> Widget:
        """Apply theme colours to one part of the dialog and return it."""
        widget = self.query_one(selector)
        if color:
            widget.styles.color = color
        if border:
            widget.styles.border = ("solid", border)
        widget.refresh()
        return widget

    def action_cancel(self) -> None:
        self.dismiss(None)
