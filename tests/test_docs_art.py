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


def test_the_readme_mock_up_is_rectangular() -> None:
    """Every row of the captured player is the same width."""
    readme = (REPO_ROOT / "README.md").read_text()
    match = re.search(r"\n```\n([┏┌].*?)\n```\n", readme, re.DOTALL)
    assert match, "no art block in README.md"

    lines = match.group(1).splitlines()
    widths = {len(line) for line in lines}
    assert len(widths) == 1, f"ragged art: widths {sorted(widths)}"
    assert len(lines) > 10, "the art looks truncated"
