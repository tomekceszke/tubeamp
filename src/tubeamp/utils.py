"""Shared utility functions."""

from __future__ import annotations


def format_time(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS."""
    total = int(seconds)
    if total >= 3600:
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


MARQUEE_SEPARATOR = "  ·  "


def scroll_offset(text: str, offset: int, width: int) -> int:
    """Return the next marquee offset for `text`, or 0 when it already fits.

    The period must match the string `marquee()` slices, or the window runs
    off the end of it and the text visibly stutters.
    """
    if len(text) <= width:
        return 0
    return (offset + 1) % (len(text) + len(MARQUEE_SEPARATOR))


def marquee(text: str, offset: int, width: int) -> str:
    """Return the visible window of `text` scrolled to `offset`."""
    if len(text) <= width:
        return text
    return (text + MARQUEE_SEPARATOR + text)[offset:offset + width]
