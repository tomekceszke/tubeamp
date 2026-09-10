"""Escape leaves the app from the main screen, but only cancels an open dialog."""

from __future__ import annotations

from tubeamp.app import TubeAmpApp
from tubeamp.widgets.search import SearchScreen


async def test_escape_on_the_main_screen_quits() -> None:
    app = TubeAmpApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app._exit, "the app is still running"


async def test_escape_in_a_dialog_only_closes_the_dialog() -> None:
    app = TubeAmpApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SearchScreen)
        assert not app._exit, "escape in the dialog quit the whole app"
