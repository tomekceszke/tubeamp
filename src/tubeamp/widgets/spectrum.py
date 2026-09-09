"""Spectrum analyzer widget — renders real-time audio bars using Unicode blocks."""

from __future__ import annotations

import logging

from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from tubeamp.widgets._color import hex_to_rgb, lerp_color

logger = logging.getLogger(__name__)


# Unicode block characters for vertical bar rendering (⅛ increments)
BAR_CHARS = " ▁▂▃▄▅▆▇█"
SPECTRUM_ROWS = 7


class SpectrumWidget(Widget):
    """Real-time spectrum analyzer display.

    Renders audio frequency bars using Unicode block characters.
    The widget receives bar heights (0.0-1.0) from the visualizer
    and renders them as vertical bars with configurable height and color.

    The display uses two rows of block characters for higher vertical
    resolution (16 levels per bar instead of 8).
    """

    DEFAULT_CSS = """
    SpectrumWidget {
        width: 1fr;
        padding: 0 1;
    }
    """

    bar_data: reactive[list[float]] = reactive(list, layout=False)

    def __init__(
        self,
        num_bars: int = 40,
        bar_color: str = "#00ff00",
        bar_color_top: str = "#00ff00",
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._num_bars = num_bars
        self._bar_color = bar_color
        self._bar_color_top = bar_color_top

    def set_gradient(self, color_bottom: str, color_top: str) -> None:
        """Set a vertical gradient from color_bottom (base) to color_top (peaks)."""
        self._bar_color = color_bottom
        self._bar_color_top = color_top
        self.watch_bar_data(self.bar_data)

    def compose(self) -> ComposeResult:
        yield Static(id="spectrum-display")

    def update_bars(self, bars: list[float]) -> None:
        """Update the spectrum with new bar data."""
        self.bar_data = bars

    def watch_bar_data(self, bars: list[float]) -> None:
        """React to bar data changes and re-render."""
        try:
            display = self.query_one("#spectrum-display", Static)
            display.update(self._render_bars(bars, display.size.width))
        except Exception:
            logger.debug("spectrum-display not yet mounted")

    def _render_bars(self, bars: list[float], available_width: int = 0) -> Text:
        """Convert bar heights to Unicode block character display.

        Each bar value (0.0-1.0) is mapped across multiple text rows.
        Bottom rows fill first, top rows fill last.
        """
        if not bars:
            return Text("")

        if available_width <= 0:
            available_width = max(0, self.size.width - 2)
        if available_width <= 0:
            return Text("")

        rows = SPECTRUM_ROWS
        lines: list[str] = []

        # Each bar occupies 2 chars, each gap occupies 1 char
        # Total width = num_bars * 2 + (num_bars - 1) = num_bars * 3 - 1
        # So num_bars = (available_width + 1) // 3
        num_bars = max(1, (available_width + 1) // 3)
        display_bars = self._resample_bars(bars, num_bars)

        for row in range(rows):
            line_chars: list[str] = []
            row_bottom = (rows - 1 - row) / rows
            row_top = (rows - row) / rows

            for i, bar_val in enumerate(display_bars):
                if bar_val >= row_top:
                    ch = BAR_CHARS[8]
                elif bar_val > row_bottom:
                    frac = (bar_val - row_bottom) / (row_top - row_bottom)
                    idx = max(0, min(8, int(frac * 8)))
                    ch = BAR_CHARS[idx]
                else:
                    ch = " "

                line_chars.append(ch)
                line_chars.append(ch)

                if i < num_bars - 1:
                    line_chars.append(" ")

            lines.append("".join(line_chars))

        # Create Rich Text with per-row gradient colors
        text = Text("\n".join(lines))
        rgb_bottom = hex_to_rgb(self._bar_color)
        rgb_top = hex_to_rgb(self._bar_color_top)
        offset = 0
        for row, line in enumerate(lines):
            t = row / max(rows - 1, 1)  # 0 at top (bright), 1 at bottom (dim)
            color = lerp_color(rgb_top, rgb_bottom, t)
            text.stylize(color, offset, offset + len(line))
            offset += len(line) + 1  # +1 for the \n separator
        return text

    @staticmethod
    def _resample_bars(bars: list[float], target_width: int) -> list[float]:
        """Resample bar data to fit the target display width."""
        n = len(bars)
        if n == target_width:
            return bars
        if n == 0:
            return [0.0] * target_width

        result: list[float] = []
        for i in range(target_width):
            # Linear interpolation
            src_pos = i * (n - 1) / max(target_width - 1, 1)
            lo = int(src_pos)
            hi = min(lo + 1, n - 1)
            frac = src_pos - lo
            val = bars[lo] * (1 - frac) + bars[hi] * frac
            result.append(val)

        return result
