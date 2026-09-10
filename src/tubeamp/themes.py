"""Theme definitions for TubeAmp UI.

Every colour the player draws comes from a `Theme`. Widgets never hard-code a
hex value: a new colour means a new field here plus a line in `theming.py`,
otherwise the palette stops being the single source of truth and themes with a
non-black base (Solarized, Gruvbox, Dracula) end up painted onto black.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from textual.theme import Theme as TextualTheme


@dataclass(frozen=True)
class Theme:
    """A complete color theme for the application."""

    name: str  # Display name shown in the picker
    key: str  # Lookup key, also what lands in config.toml
    # Primary colors
    primary: str  # Main accent color (bars, active states)
    primary_dim: str  # Dimmed version for bar bases and inactive accents
    primary_bright: str  # Bright version for titles and peaks
    # Background and text
    background: str
    background_light: str  # Panels, dialogs and inputs
    text: str
    text_dim: str  # Secondary text, inactive buttons, empty bar segments
    # Structure
    border: str  # Player frame
    divider: str  # Separator rules and the resting scrollbar
    # Selection and playing
    selection_bg: str  # Selected item background
    selection_fg: str  # Selected item text
    playing: str  # Currently playing track
    # Button states
    shuffle_active: str
    repeat_all: str
    repeat_one: str
    # Toast severities
    warning: str
    error: str
    # Spectrum gradient, bottom row to top row
    spectrum_low: str
    spectrum_mid: str
    spectrum_high: str

    @property
    def spectrum_stops(self) -> tuple[str, str, str]:
        """Gradient stops for the spectrum, from bar base to bar peak."""
        return (self.spectrum_low, self.spectrum_mid, self.spectrum_high)


THEMES: dict[str, Theme] = {
    # ── CRT / retro terminals ───────────────────────────────────
    "classic": Theme(
        name="Classic",
        key="classic",
        primary="#00ff41",
        primary_dim="#026b1c",
        primary_bright="#9dff9d",
        background="#000000",
        background_light="#071007",
        text="#c8f7c8",
        text_dim="#4f8f5a",
        border="#00b32d",
        divider="#14401c",
        selection_bg="#00ff41",
        selection_fg="#001a05",
        playing="#9dff9d",
        shuffle_active="#00e5ff",
        repeat_all="#ffd400",
        repeat_one="#ff5fd2",
        warning="#ffd400",
        error="#ff5f56",
        spectrum_low="#026b1c",
        spectrum_mid="#00ff41",
        spectrum_high="#ccff66",
    ),
    "monochrome": Theme(
        name="Monochrome",
        key="monochrome",
        primary="#ffffff",
        primary_dim="#5a5a5a",
        primary_bright="#ffffff",
        background="#000000",
        background_light="#101010",
        text="#d0d0d0",
        text_dim="#8a8a8a",
        border="#8a8a8a",
        divider="#3a3a3a",
        selection_bg="#e6e6e6",
        selection_fg="#000000",
        playing="#ffffff",
        shuffle_active="#bfbfbf",
        repeat_all="#d9d9d9",
        repeat_one="#9e9e9e",
        warning="#d9d9d9",
        error="#bfbfbf",
        spectrum_low="#4a4a4a",
        spectrum_mid="#b5b5b5",
        spectrum_high="#ffffff",
    ),
    "amber": Theme(
        name="Amber",
        key="amber",
        primary="#ff9e2c",
        primary_dim="#8a4e0b",
        primary_bright="#ffd39b",
        background="#120b02",
        background_light="#1d1206",
        text="#ffb454",
        text_dim="#b07a2a",
        border="#c8711a",
        divider="#3a230c",
        selection_bg="#ff9e2c",
        selection_fg="#140a02",
        playing="#ffd39b",
        shuffle_active="#ffcf8a",
        repeat_all="#ffb454",
        repeat_one="#ff7a3d",
        warning="#ffb454",
        error="#ff7a3d",
        spectrum_low="#8a4e0b",
        spectrum_mid="#ff9e2c",
        spectrum_high="#ffe0b0",
    ),
    "commander": Theme(
        name="Commander",
        key="commander",
        primary="#55ffff",
        primary_dim="#00aaaa",
        primary_bright="#d6ffff",
        background="#00006e",
        background_light="#0000a8",
        text="#c6cfff",
        text_dim="#8c99e0",
        border="#55ffff",
        divider="#2a2ab5",
        selection_bg="#00aaaa",
        selection_fg="#000000",
        playing="#ffff55",
        shuffle_active="#ff55ff",
        repeat_all="#ffff55",
        repeat_one="#55ff55",
        warning="#ffff55",
        error="#ff7b72",
        spectrum_low="#00aaaa",
        spectrum_mid="#55ffff",
        spectrum_high="#ffff55",
    ),
    # ── Neon ────────────────────────────────────────────────────
    "cyberpunk": Theme(
        name="Cyberpunk",
        key="cyberpunk",
        primary="#fcee0a",
        primary_dim="#8a8200",
        primary_bright="#fff685",
        background="#06080d",
        background_light="#0d1119",
        text="#cfe9f0",
        text_dim="#7e949c",
        border="#02d7f2",
        divider="#1a2430",
        selection_bg="#02d7f2",
        selection_fg="#06080d",
        playing="#fcee0a",
        shuffle_active="#ff2e6a",
        repeat_all="#02d7f2",
        repeat_one="#ff2ea6",
        warning="#fcee0a",
        error="#ff2e6a",
        spectrum_low="#02d7f2",
        spectrum_mid="#fcee0a",
        spectrum_high="#ff2e6a",
    ),
    "synthwave": Theme(
        name="Synthwave",
        key="synthwave",
        primary="#ff2e97",
        primary_dim="#8c1257",
        primary_bright="#ff8bc4",
        background="#16082a",
        background_light="#221039",
        text="#e8d7ff",
        text_dim="#9a7ccb",
        border="#b967ff",
        divider="#3a1f5c",
        selection_bg="#ff2e97",
        selection_fg="#16082a",
        playing="#00e5ff",
        shuffle_active="#00e5ff",
        repeat_all="#ffd319",
        repeat_one="#ff8b3d",
        warning="#ffd319",
        error="#ff5f6d",
        spectrum_low="#b967ff",
        spectrum_mid="#ff2e97",
        spectrum_high="#ffd319",
    ),
    # ── Editor classics ─────────────────────────────────────────
    "htop": Theme(
        name="htop",
        key="htop",
        primary="#00c000",
        primary_dim="#00701f",
        primary_bright="#5fff5f",
        background="#0f0f0f",
        background_light="#1b1b1b",
        text="#d0d0d0",
        text_dim="#8a8a8a",
        border="#00cdcd",
        divider="#303030",
        selection_bg="#00cdcd",
        selection_fg="#000000",
        playing="#5fff5f",
        shuffle_active="#cd00cd",
        repeat_all="#cdcd00",
        repeat_one="#00cdcd",
        warning="#cdcd00",
        error="#ff5f5f",
        # The CPU meter's own ramp: low priority blue, normal green, kernel red
        spectrum_low="#3a6fe0",
        spectrum_mid="#00c000",
        spectrum_high="#e04040",
    ),
    "ayu": Theme(
        name="Ayu Dark",
        key="ayu",
        primary="#59c2ff",
        primary_dim="#2f7ea8",
        primary_bright="#a6e0ff",
        background="#05070a",
        background_light="#0f141c",
        text="#d7d5ce",
        text_dim="#7b8394",
        # Blue frame, so the near-black base does not read as htop's cyan one
        border="#59c2ff",
        divider="#1c2230",
        selection_bg="#59c2ff",
        selection_fg="#05070a",
        playing="#aad94c",
        shuffle_active="#d2a6ff",
        repeat_all="#ffb454",
        repeat_one="#f07178",
        warning="#ffb454",
        error="#f07178",
        spectrum_low="#39bae6",
        spectrum_mid="#aad94c",
        spectrum_high="#ffb454",
    ),
    "gruvbox": Theme(
        name="Gruvbox Dark",
        key="gruvbox",
        primary="#fabd2f",
        primary_dim="#b57614",
        primary_bright="#ffd982",
        background="#282828",
        background_light="#3c3836",
        text="#ebdbb2",
        text_dim="#a89984",
        border="#928374",
        divider="#504945",
        selection_bg="#504945",
        selection_fg="#fbf1c7",
        playing="#b8bb26",
        shuffle_active="#8ec07c",
        repeat_all="#fe8019",
        repeat_one="#d3869b",
        warning="#fabd2f",
        error="#fb4934",
        spectrum_low="#b8bb26",
        spectrum_mid="#fabd2f",
        spectrum_high="#fe8019",
    ),
    "dracula": Theme(
        name="Dracula",
        key="dracula",
        primary="#bd93f9",
        primary_dim="#6d4aa8",
        primary_bright="#e9ddff",
        background="#282a36",
        background_light="#343746",
        text="#f8f8f2",
        text_dim="#8b9bcc",
        border="#6272a4",
        divider="#44475a",
        selection_bg="#44475a",
        selection_fg="#f8f8f2",
        playing="#50fa7b",
        shuffle_active="#8be9fd",
        repeat_all="#f1fa8c",
        repeat_one="#ff79c6",
        warning="#ffb86c",
        error="#ff5555",
        spectrum_low="#8be9fd",
        spectrum_mid="#bd93f9",
        spectrum_high="#ff79c6",
    ),
}

DEFAULT_THEME_KEY = "classic"
DEFAULT_THEME = THEMES[DEFAULT_THEME_KEY]

# Names that are not keys: the display name of every theme, plus the themes
# that were folded into another one, so an existing config.toml keeps working.
ALIASES: dict[str, str] = {
    "gruvbox-dark": "gruvbox",
    "ayu-dark": "ayu",
    "retro": "amber",
    # Dropped palettes point at their nearest surviving neighbour
    "monokai": "dracula",
    "solarized": "ayu",
    "solarized-dark": "ayu",
    "nord": "ayu",
}

# Fields that hold a colour, i.e. everything but the two labels
COLOR_FIELDS: tuple[str, ...] = tuple(
    f.name for f in fields(Theme) if f.name not in {"name", "key"}
)


def normalize_key(name: str) -> str:
    """Turn a display name or config value into a THEMES key.

    Display names gained a second word ("Solarized Dark"), so a bare
    `name.lower()` no longer matches the key it came from.
    """
    return name.strip().lower().replace(" ", "-").replace("_", "-")


def get_theme(name: str) -> Theme:
    """Get a theme by key, display name or retired name; default is classic."""
    key = normalize_key(name)
    key = ALIASES.get(key, key)
    return THEMES.get(key, THEMES[DEFAULT_THEME_KEY])


def theme_keys() -> list[str]:
    """Lookup keys of all themes, in picker order."""
    return list(THEMES)


def get_theme_names() -> list[str]:
    """Display names of all themes, in picker order."""
    return [theme.name for theme in THEMES.values()]


def to_textual_theme(theme: Theme) -> TextualTheme:
    """Convert a TubeAmp Theme to a Textual Theme.

    This is what carries the palette into the parts Textual draws itself:
    toasts, scrollbars, the search input's cursor and `$`-variables used by
    widget CSS.
    """
    return TextualTheme(
        name=f"tubeamp-{theme.key}",
        primary=theme.primary,
        secondary=theme.primary_dim,
        warning=theme.warning,
        error=theme.error,
        accent=theme.shuffle_active,
        background=theme.background,
        panel=theme.background_light,
        surface=theme.background_light,
        foreground=theme.text,
        success=theme.playing,
        dark=True,
        variables={
            "border": theme.border,
            "border-blurred": theme.divider,
            "scrollbar": theme.divider,
            "scrollbar-hover": theme.primary,
            "scrollbar-active": theme.primary_bright,
            "scrollbar-background": theme.background,
            "block-cursor-background": theme.selection_bg,
            "block-cursor-foreground": theme.selection_fg,
            "block-cursor-text-style": "bold",
            "input-cursor-background": theme.primary,
            "input-cursor-foreground": theme.background,
            "input-selection-background": f"{theme.primary} 35%",
            "footer-key-foreground": theme.primary,
        },
    )
