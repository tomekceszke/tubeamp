"""Toasts that carry text the app did not write must not be read as markup.

The help toast lists ``[`` and ``]`` as keys, and yt-dlp prefixes its errors
with the extractor in brackets (``[youtube]``). Textual parses a toast as
markup by default, so the first crashed the app and the second lost the prefix.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets._toast import Toast

from tubeamp.app import TubeAmpApp

if TYPE_CHECKING:
    import pytest

_YTDLP_ERROR = "ERROR: [youtube] abc: Video unavailable [/end]"


def _rendered_toasts(app: TubeAmpApp) -> str:
    toasts = app.query(Toast)
    assert toasts, "no toast appeared"
    return "".join(str(toast.render()) for toast in toasts)


async def test_help_toast_shows_the_bracket_keys() -> None:
    app = TubeAmpApp()
    async with app.run_test(size=(178, 50), notifications=True) as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        rendered = _rendered_toasts(app)

    assert "[/]=Bars" in rendered, rendered


async def test_search_error_is_shown_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    app = TubeAmpApp()

    def fail(*_: Any) -> list[Any]:
        raise RuntimeError(_YTDLP_ERROR)

    monkeypatch.setattr(app, "_do_search", fail)
    async with app.run_test(size=(178, 50), notifications=True) as pilot:
        await pilot.pause()
        await app._handle_search_result("anything")
        await pilot.pause()
        rendered = _rendered_toasts(app)

    assert _YTDLP_ERROR in rendered, rendered


async def test_load_more_error_is_shown_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    app = TubeAmpApp()

    def fail(*_: Any) -> list[Any]:
        raise RuntimeError(_YTDLP_ERROR)

    monkeypatch.setattr(app, "_fetch_page", fail)
    async with app.run_test(size=(178, 50), notifications=True) as pilot:
        await pilot.pause()
        app._session.start_search("anything")
        await app._load_more_tracks()
        await pilot.pause()
        rendered = _rendered_toasts(app)

    assert _YTDLP_ERROR in rendered, rendered
