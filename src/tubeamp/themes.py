"""Theme definitions for TubeAmp UI."""

from __future__ import annotations

from dataclasses import dataclass

from textual.theme import Theme as TextualTheme


@dataclass(frozen=True)
class Theme:
    """A complete color theme for the application."""

    name: str
    # Primary colors
    primary: str  # Main accent color (spectrum, bars, active states)
    primary_dim: str  # Dimmed version for borders, inactive elements
    primary_bright: str  # Bright version for highlights
    # Background and text
    background: str
    background_light: str  # Slightly lighter background for containers
    text: str
    text_dim: str  # Dimmed text for secondary info
    # Selection and playing
    selection_bg: str  # Selected item background
    selection_fg: str  # Selected item text
    playing: str  # Currently playing track
    # Button states
    shuffle_active: str
    repeat_all: str
    repeat_one: str


THEMES: dict[str, Theme] = {
    "classic": Theme(
        name="Classic",
        primary="#00ff00",
        primary_dim="#006400",
        primary_bright="#00ff00",
        background="#000000",
        background_light="#0a0a0a",
        text="#ffffff",
        text_dim="#808080",
        selection_bg="#00ff00",
        selection_fg="#000000",
        playing="#00ff00",
        shuffle_active="#00ffff",
        repeat_all="#ffff00",
        repeat_one="#ff00ff",
    ),
    "amber": Theme(
        name="Amber",
        primary="#ffd700",
        primary_dim="#b8860b",
        primary_bright="#ffed4e",
        background="#000000",
        background_light="#1a1200",
        text="#ffd700",
        text_dim="#b8860b",
        selection_bg="#ffd700",
        selection_fg="#000000",
        playing="#ffed4e",
        shuffle_active="#ffa500",
        repeat_all="#ffff00",
        repeat_one="#ff8c00",
    ),
    "monochrome": Theme(
        name="Monochrome",
        primary="#ffffff",
        primary_dim="#606060",
        primary_bright="#ffffff",
        background="#000000",
        background_light="#1a1a1a",
        text="#c0c0c0",
        text_dim="#606060",
        selection_bg="#ffffff",
        selection_fg="#000000",
        playing="#ffffff",
        shuffle_active="#d0d0d0",
        repeat_all="#e0e0e0",
        repeat_one="#b0b0b0",
    ),
    "cyberpunk": Theme(
        name="Cyberpunk",
        primary="#fcee09",
        primary_dim="#b8a000",
        primary_bright="#ffff00",
        background="#0a0a14",
        background_light="#14141e",
        text="#fcee09",
        text_dim="#b8a000",
        selection_bg="#ff1493",
        selection_fg="#000000",
        playing="#00ffff",
        shuffle_active="#ff1493",
        repeat_all="#00ffff",
        repeat_one="#fcee09",
    ),
    "synthwave": Theme(
        name="Synthwave",
        primary="#b026ff",
        primary_dim="#6b0fb3",
        primary_bright="#d896ff",
        background="#0f0520",
        background_light="#1a0a30",
        text="#b026ff",
        text_dim="#6b0fb3",
        selection_bg="#ff006e",
        selection_fg="#000000",
        playing="#00f0ff",
        shuffle_active="#00f0ff",
        repeat_all="#ff006e",
        repeat_one="#ffbe0b",
    ),
    "retro": Theme(
        name="Retro",
        primary="#ff8c00",
        primary_dim="#8b4500",
        primary_bright="#ffa500",
        background="#2b1b0a",
        background_light="#3d2814",
        text="#ffb76b",
        text_dim="#8b6332",
        selection_bg="#ff8c00",
        selection_fg="#2b1b0a",
        playing="#ffa500",
        shuffle_active="#ff7f50",
        repeat_all="#ffd700",
        repeat_one="#ff6347",
    ),
}


def get_theme(name: str) -> Theme:
    """Get a theme by name, defaulting to classic."""
    return THEMES.get(name.lower(), THEMES["classic"])


def get_theme_names() -> list[str]:
    """Get list of available theme names."""
    return [theme.name for theme in THEMES.values()]


def to_textual_theme(theme: Theme) -> TextualTheme:
    """Convert a TubeAmp Theme to a Textual Theme for toast/scrollbar styling."""
    return TextualTheme(
        name=f"tubeamp-{theme.name.lower()}",
        primary=theme.primary,
        secondary=theme.primary_dim,
        warning=theme.primary_dim,
        error=theme.primary_dim,
        accent=theme.primary_bright,
        background=theme.background,
        panel=theme.background_light,
        surface=theme.background_light,
        foreground=theme.text,
        success=theme.primary,
        dark=True,
    )
