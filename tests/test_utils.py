"""Tests for the shared formatting and marquee helpers."""

import pytest

from tubeamp.utils import MARQUEE_SEPARATOR, format_time, marquee, scroll_offset


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "0:00"), (9, "0:09"), (75, "1:15"), (599, "9:59"), (3600, "1:00:00"),
     (7384, "2:03:04")],
)
def test_format_time(seconds: int, expected: str) -> None:
    assert format_time(seconds) == expected


def test_text_that_fits_does_not_scroll() -> None:
    assert scroll_offset("short", 0, 20) == 0
    assert marquee("short", 7, 20) == "short"


def test_offset_period_matches_the_rendered_string() -> None:
    """The offset must wrap exactly when the marquee window returns to the start.

    These used to disagree — the offset wrapped at len(text) + 10 while the
    rendered string repeated every len(text) + 5 — so the window ran past the
    end of it and the title visibly stuttered.
    """
    text = "a much longer track title than the window"
    width = 12

    offset = 0
    seen = []
    for _ in range(len(text) + len(MARQUEE_SEPARATOR)):
        seen.append(marquee(text, offset, width))
        offset = scroll_offset(text, offset, width)

    assert offset == 0, "offset did not return to the start after one period"
    assert seen[0] == text[:width]


def test_marquee_window_is_always_full_width() -> None:
    """A short slice means the offset ran off the end of the extended string."""
    text = "0123456789abcdefghijklmnopqrstuvwxyz"
    width = 10

    offset = 0
    for _ in range(200):
        assert len(marquee(text, offset, width)) == width
        offset = scroll_offset(text, offset, width)


def test_marquee_wraps_through_the_separator() -> None:
    text = "abcdefghij"
    width = 8
    windows = []
    offset = 0
    for _ in range(len(text) + len(MARQUEE_SEPARATOR)):
        windows.append(marquee(text, offset, width))
        offset = scroll_offset(text, offset, width)

    joined = "".join(w[0] for w in windows)
    assert joined == text + MARQUEE_SEPARATOR
