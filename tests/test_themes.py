"""Palette invariants for the bundled themes.

Every theme is dark and readable, and every colour it declares is a real hex
value, so a new palette cannot ship a typo or an unreadable pairing.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tubeamp.themes import (
    COLOR_FIELDS,
    DEFAULT_THEME_KEY,
    THEMES,
    Theme,
    get_theme,
    get_theme_names,
    normalize_key,
    theme_keys,
    to_textual_theme,
)
from tubeamp.widgets._color import contrast_ratio, relative_luminance, sample_gradient

HEX = re.compile(r"^#[0-9a-f]{6}$")

ALL_THEMES = list(THEMES.values())
THEME_IDS = list(THEMES)


def _ids(themes: list[Theme]) -> list[str]:
    return [theme.key for theme in themes]


class TestPalette:
    def test_ten_themes(self) -> None:
        assert len(THEMES) == 10

    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_every_color_is_hex(self, theme: Theme) -> None:
        for field in COLOR_FIELDS:
            value = getattr(theme, field)
            assert HEX.match(value), f"{theme.key}.{field} = {value!r}"

    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_key_matches_registry(self, theme: Theme) -> None:
        assert THEMES[theme.key] is theme
        assert normalize_key(theme.name) or theme.key

    def test_names_and_keys_unique(self) -> None:
        names = get_theme_names()
        assert len(set(names)) == len(names)
        assert len(set(theme_keys())) == len(theme_keys())


class TestReadability:
    """The thresholds are WCAG ratios; text is AA, decoration is AA-large."""

    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_background_is_dark(self, theme: Theme) -> None:
        assert relative_luminance(theme.background) < 0.05
        assert relative_luminance(theme.background_light) < 0.10

    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_text_is_readable(self, theme: Theme) -> None:
        assert contrast_ratio(theme.text, theme.background) >= 4.5
        assert contrast_ratio(theme.text_dim, theme.background) >= 3.0
        assert contrast_ratio(theme.selection_fg, theme.selection_bg) >= 4.5

    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_accents_stand_out(self, theme: Theme) -> None:
        for field in ("primary", "primary_bright", "playing", "shuffle_active"):
            ratio = contrast_ratio(getattr(theme, field), theme.background)
            assert ratio >= 3.0, f"{theme.key}.{field} = {ratio:.2f}"
        assert contrast_ratio(theme.border, theme.background) >= 2.5

    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_divider_is_subdued(self, theme: Theme) -> None:
        # Visible against the background, but never competing with the text
        ratio = contrast_ratio(theme.divider, theme.background)
        assert 1.1 <= ratio <= 3.0, f"{theme.key} divider = {ratio:.2f}"


class TestLookup:
    def test_key_lookup(self) -> None:
        assert get_theme("dracula").key == "dracula"

    def test_display_name_lookup(self) -> None:
        """Two-word names used to fall through to the default silently."""
        assert get_theme("Gruvbox Dark").key == "gruvbox"

    def test_normalization(self) -> None:
        assert get_theme("  GRUVBOX_DARK ").key == "gruvbox"

    def test_every_display_name_resolves(self) -> None:
        for theme in ALL_THEMES:
            assert get_theme(theme.name).key == theme.key

    @pytest.mark.parametrize(
        ("retired", "successor"),
        [
            ("retro", "amber"),
            ("monokai", "dracula"),
            ("Solarized Dark", "ayu"),
            ("nord", "ayu"),
        ],
    )
    def test_retired_theme_maps_onto_its_successor(
        self, retired: str, successor: str
    ) -> None:
        """An existing config.toml still names a theme that was dropped."""
        assert get_theme(retired).key == successor

    def test_unknown_falls_back(self) -> None:
        assert get_theme("no-such-theme").key == DEFAULT_THEME_KEY


class TestSpectrumStops:
    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_three_distinct_stops(self, theme: Theme) -> None:
        stops = theme.spectrum_stops
        assert len(stops) == 3
        assert sample_gradient(stops, 0.0) == stops[0]
        assert sample_gradient(stops, 1.0) == stops[2]
        assert sample_gradient(stops, 0.5) == stops[1]

    def test_gradient_is_clamped(self) -> None:
        stops = ("#000000", "#808080", "#ffffff")
        assert sample_gradient(stops, -1.0) == "#000000"
        assert sample_gradient(stops, 2.0) == "#ffffff"

    def test_two_stops_still_work(self) -> None:
        assert sample_gradient(("#000000", "#ffffff"), 0.5) == "#7f7f7f"


class TestTextualTheme:
    @pytest.mark.parametrize("theme", ALL_THEMES, ids=THEME_IDS)
    def test_conversion(self, theme: Theme) -> None:
        converted = to_textual_theme(theme)
        assert converted.dark is True
        assert converted.name == f"tubeamp-{theme.key}"
        assert converted.background == theme.background
        assert converted.foreground == theme.text
        assert converted.warning == theme.warning
        assert converted.error == theme.error
        assert converted.variables["scrollbar"] == theme.divider


class TestNoHardcodedColors:
    """The palette is only the single source of truth if nothing bypasses it.

    Widgets and the stylesheet used to carry their own hex values, which is
    why themes could only ever change accents on a permanently black surface.
    """

    ALLOWED = {"_color.py"}  # a black fallback for an empty gradient

    def test_widgets_and_stylesheet_are_colourless(self) -> None:
        root = pathlib.Path(__file__).resolve().parent.parent / "src" / "tubeamp"
        sources = [
            path
            for path in [*(root / "widgets").glob("*.py"), *(root / "styles").glob("*.tcss")]
            if path.name not in self.ALLOWED
        ]
        assert sources, "no sources found to scan"

        offenders = {
            path.name: re.findall(r"#[0-9a-fA-F]{3,8}\b", path.read_text())
            for path in sources
        }
        assert not {k: v for k, v in offenders.items() if v}
