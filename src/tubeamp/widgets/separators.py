"""Box-drawing rules that frame the player panels."""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.widgets import Static

DIVIDER_STYLE = "#333333"


class PanelDivider(Widget):
    """Vertical rule between the spectrum and the controls panel."""

    def render(self) -> Text:
        return Text("\n".join(["║"] * max(self.size.height, 1)), style=DIVIDER_STYLE)


class HorizontalRule(Static):
    """Horizontal rule sized to the width it is given.

    INSET trims the rule at each end and sets the floor width; the section
    rules run edge to edge, the ones inside a panel are held off the border.
    """

    INSET = 0
    MIN_WIDTH = 40

    def on_mount(self) -> None:
        self._draw()

    def on_resize(self) -> None:
        self._draw()

    def _draw(self) -> None:
        width = max(self.size.width - self.INSET, self.MIN_WIDTH)
        self.update("─" * width)


class SectionSeparator(HorizontalRule):
    """Rule between the main sections of the player."""


class PanelSeparator(HorizontalRule):
    """Rule inside a panel, inset from its edges."""

    INSET = 2
    MIN_WIDTH = 10
