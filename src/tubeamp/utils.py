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


def scroll_text(text: str, offset: int, width: int) -> int:
    """Return next scroll offset for marquee effect. Returns 0 if text fits."""
    if len(text) > width:
        return (offset + 1) % (len(text) + 10)
    return 0
