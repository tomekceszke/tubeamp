"""The ASCII art has to survive being rendered by a browser.

The trap is narrow: a character from the emoji families that nonetheless
*declares* itself one column wide. Rich, Textual and every width calculation
downstream believe the declaration, while browsers and emoji-capable terminals
draw the glyph across two columns. One of those in a box-drawn frame pushes a
single row wider than its neighbours, which is how the README mock-up came out
crooked, and how ControlsWidget would have mislaid its buttons.

Honest wide emoji (U+1F50D, U+23E9) are fine and stay allowed: they measure as
two columns everywhere, so nothing is surprised.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pytest
from rich.cells import cell_len

REPO_ROOT = Path(__file__).resolve().parent.parent

# Ranges whose members browsers commonly render through an emoji font. Not the
# whole Extended_Pictographic set — just the neighbourhoods a terminal UI is
# tempted to shop in. U+23F8 PAUSE lives in the first one.
EMOJI_RANGES = (
    (0x231A, 0x231B),    # watch, hourglass
    (0x23E9, 0x23FA),    # media transport controls
    (0x25FD, 0x25FE),    # small squares
    (0x2614, 0x2615),    # umbrella, coffee
    (0x2648, 0x2653),    # zodiac
    (0x267F, 0x267F),    # wheelchair
    (0x2693, 0x2693),    # anchor
    (0x26A1, 0x26A1),    # high voltage
    (0x1F000, 0x1FAFF),  # everything modern
)

SCANNED = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "ARCHITECTURE.md",
    *sorted((REPO_ROOT / "src").rglob("*.py")),
]


def _liars(text: str) -> list[str]:
    """Emoji-family characters that claim to be one column wide."""
    return [
        ch for ch in text
        if any(low <= ord(ch) <= high for low, high in EMOJI_RANGES)
        and cell_len(ch) == 1
    ]


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: p.name)
def test_no_emoji_width_traps(path: Path) -> None:
    found = _liars(path.read_text())
    assert not found, ", ".join(
        f"U+{ord(ch):04X} {unicodedata.name(ch, '?')}" for ch in dict.fromkeys(found)
    )


def test_the_readme_shows_a_real_screenshot() -> None:
    """The hero image has to survive PyPI, which needs an absolute source.

    A relative path renders on GitHub and breaks on the package page, and a
    block of box characters renders on GitHub and comes out wavy on PyPI, where
    the font stack substitutes for some of the glyphs. A PNG does neither.
    """
    readme = (REPO_ROOT / "README.md").read_text()
    match = re.search(r"!\[[^\]]+\]\((https://[^)]+/docs/player\.png)\)", readme)
    assert match, "no absolute link to docs/player.png in README.md"

    shot = REPO_ROOT / "docs" / "player.png"
    assert shot.is_file(), "docs/player.png is missing"
    assert shot.stat().st_size > 10_000, "the screenshot looks truncated"
    assert shot.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"


def test_no_hand_drawn_frame_came_back() -> None:
    """Box-drawn art is what the screenshot replaced; it must not return."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert not re.search(r"```\n[┏┌]", readme), (
        "a box-drawn block is back in README.md; run scripts/capture_player_shot.py"
    )
