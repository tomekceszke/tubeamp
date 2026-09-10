"""The empty playlist is the whole of a new user's first screen.

It has to say what to press, and it has to fit: the panel has a fixed height,
so a wrapped hint row would push the block out of view rather than reflow it.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from tubeamp.themes import THEMES, get_theme
from tubeamp.theming import _paint_playlist
from tubeamp.widgets.playlist import WELCOME_HINTS, PlaylistEntry, PlaylistWidget


class Harness(App[None]):
    def compose(self) -> ComposeResult:
        yield PlaylistWidget(id="playlist")


async def _welcome_lines(size: tuple[int, int], theme_key: str = "classic") -> list[str]:
    app = Harness()
    async with app.run_test(size=size) as pilot:
        widget = app.query_one("#playlist", PlaylistWidget)
        _paint_playlist(widget, get_theme(theme_key))
        await pilot.pause()
        return widget._welcome_text().plain.splitlines()


@pytest.mark.parametrize("size", [(90, 16), (70, 8), (52, 12), (40, 24)])
async def test_block_fits_the_panel(size: tuple[int, int]) -> None:
    lines = await _welcome_lines(size)
    assert len(lines) <= size[1]
    assert max(len(line) for line in lines) <= size[0]


async def test_names_every_hint() -> None:
    body = "\n".join(await _welcome_lines((90, 16)))
    for key, _, _ in WELCOME_HINTS:
        assert f"  {key}   " in body
    assert "paste a YouTube playlist URL" in body


async def test_narrow_terminal_drops_to_short_descriptions() -> None:
    body = "\n".join(await _welcome_lines((44, 16)))
    assert "search or paste a URL" in body
    assert "artist, song" not in body


async def test_hint_colours_come_from_the_theme() -> None:
    app = Harness()
    async with app.run_test(size=(90, 16)) as pilot:
        widget = app.query_one("#playlist", PlaylistWidget)
        theme = THEMES["dracula"]
        _paint_playlist(widget, theme)
        await pilot.pause()
        styles = {str(span.style) for span in widget._welcome_text().spans}
    assert any(theme.primary in style for style in styles)
    assert any(theme.text_dim in style for style in styles)


async def test_entries_replace_the_welcome_block() -> None:
    app = Harness()
    async with app.run_test(size=(90, 16)) as pilot:
        widget = app.query_one("#playlist", PlaylistWidget)
        widget.set_entries([PlaylistEntry(title="Da Funk", duration_str="5:28")])
        await pilot.pause()
        assert widget._entries
