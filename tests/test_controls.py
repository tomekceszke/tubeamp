"""Tests for the playback controls widget's responsive layout."""

import pytest

from tubeamp.widgets.controls import (
    _BOX_WIDTH,
    _BUTTONS,
    _Layout,
    _resolve_layout,
)


def _row_width(layout: _Layout) -> int:
    """Rendered width of one row for this layout."""
    return layout.left_pad + layout.cell_width * len(_BUTTONS) + sum(layout.gaps)


@pytest.mark.parametrize("width", range(1, 121))
def test_layout_never_exceeds_available_width(width: int) -> None:
    """Overflowing rows wrap, which pushes the bottom border out of the widget."""
    layout = _resolve_layout(width)
    assert _row_width(layout) <= width or layout.cell_width == 1


def test_wide_player_keeps_the_boxed_layout() -> None:
    layout = _resolve_layout(80)
    assert layout.style == "boxed"
    assert layout.cell_width == _BOX_WIDTH
    assert layout.gaps == (2, 2, 4, 2)


def test_gaps_tighten_before_boxes_are_dropped() -> None:
    """A slightly narrow player should lose whitespace, not its borders."""
    layout = _resolve_layout(40)
    assert layout.style == "boxed"
    assert sum(layout.gaps) < 10


def test_narrow_player_falls_back_to_compact_styles() -> None:
    assert _resolve_layout(34).style == "bracket"
    assert _resolve_layout(12).style == "glyph"


def test_layout_is_centred() -> None:
    layout = _resolve_layout(80)
    used = layout.cell_width * len(_BUTTONS) + sum(layout.gaps)
    assert layout.left_pad == (80 - used) // 2


def test_positions_are_ordered_and_disjoint() -> None:
    """Click regions must follow the drawn order without overlapping."""
    for width in (100, 47, 40, 35, 28, 20, 12):
        spans = _resolve_layout(width).positions()
        ordered = [spans[b.name] for b in _BUTTONS]
        for (_, prev_end), (next_start, _) in zip(ordered[:-1], ordered[1:], strict=True):
            assert prev_end < next_start, f"overlap at width {width}"


def test_positions_cover_every_button() -> None:
    spans = _resolve_layout(100).positions()
    assert set(spans) == {b.name for b in _BUTTONS}
    for start, end in spans.values():
        assert end - start + 1 == _BOX_WIDTH


def test_degenerate_width_still_resolves() -> None:
    """Nothing fits, but the widget must still render rather than raise."""
    layout = _resolve_layout(1)
    assert layout.cell_width == 1
    assert layout.left_pad == 0
