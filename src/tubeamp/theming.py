"""Applying a TubeAmp theme to the mounted widget tree."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, cast

from textual.css.query import NoMatches
from textual.widget import Widget

from tubeamp.themes import to_textual_theme
from tubeamp.widgets.controls import ControlsWidget
from tubeamp.widgets.playlist import PlaylistWidget
from tubeamp.widgets.separators import HorizontalRule, PanelDivider
from tubeamp.widgets.spectrum import SpectrumWidget
from tubeamp.widgets.track_info import TrackInfoWidget
from tubeamp.widgets.volume import VolumeWidget

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.app import App

    from tubeamp.themes import Theme


class _Divider(Protocol):
    """Any rule that can be recoloured, however it draws itself."""

    def set_divider_color(self, color: str) -> None: ...


logger = logging.getLogger(__name__)


def _paint_container(widget: Widget, theme: Theme) -> None:
    widget.styles.border = ("heavy", theme.border)
    widget.styles.background = theme.background


def _paint_spectrum(widget: SpectrumWidget, theme: Theme) -> None:
    widget.set_gradient(theme.spectrum_stops)


def _paint_playlist(widget: PlaylistWidget, theme: Theme) -> None:
    widget.set_theme(
        selection_bg=theme.selection_bg,
        selection_fg=theme.selection_fg,
        playing_color=theme.playing,
        divider=theme.divider,
        hint_key=theme.primary,
        hint_text=theme.text_dim,
    )


def _paint_controls(widget: ControlsWidget, theme: Theme) -> None:
    widget.set_theme(
        primary=theme.primary_bright,
        inactive=theme.text_dim,
        shuffle_active=theme.shuffle_active,
        repeat_all=theme.repeat_all,
        repeat_one=theme.repeat_one,
    )


def _paint_track_info(widget: TrackInfoWidget, theme: Theme) -> None:
    widget.set_theme(
        primary=theme.primary_bright,
        primary_dim=theme.primary_dim,
        dim=theme.text_dim,
    )


def _paint_volume(widget: VolumeWidget, theme: Theme) -> None:
    widget.set_theme(
        bar_color=theme.primary_dim,
        bar_color_top=theme.primary_bright,
        dim=theme.text_dim,
    )


# Every themed part of the UI, so adding one is a single row rather than
# another copy of the query-and-guard dance.
THEMED_WIDGETS: tuple[tuple[str, type[Widget], Callable[[Any, Theme], None]], ...] = (
    ("#player-container", Widget, _paint_container),
    ("#spectrum", SpectrumWidget, _paint_spectrum),
    ("#playlist", PlaylistWidget, _paint_playlist),
    ("#controls", ControlsWidget, _paint_controls),
    ("#track-info", TrackInfoWidget, _paint_track_info),
    ("#volume-bar", VolumeWidget, _paint_volume),
)

# The rules come in pairs and by class, so they are queried as a set rather
# than through query_one like the singletons above.
DIVIDER_WIDGETS: tuple[type[Widget], ...] = (PanelDivider, HorizontalRule)


def apply_theme(app: App[Any], theme: Theme) -> None:
    """Recolour every mounted widget, skipping any that are not up yet."""
    for selector, widget_type, paint in THEMED_WIDGETS:
        try:
            widget = app.query_one(selector, widget_type)
        except NoMatches:
            continue
        paint(widget, theme)

    for divider_type in DIVIDER_WIDGETS:
        for rule in app.query(divider_type):
            cast("_Divider", rule).set_divider_color(theme.divider)

    # Register as a Textual theme too, so toasts, scrollbars and the dialogs'
    # $-variables follow along
    try:
        textual_theme = to_textual_theme(theme)
        app.register_theme(textual_theme)
        app.theme = textual_theme.name
    except Exception:
        logger.warning("Failed to register Textual theme")

    logger.info("Theme %s applied", theme.name)
