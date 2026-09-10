"""What the app says for itself on a first run with a dependency missing.

ffmpeg only drives the spectrum analysis, so its absence is not fatal — the
bars silently fall back to the placeholder animation. Silently is the problem:
it reads as a broken visualizer rather than a missing package.
"""

from __future__ import annotations

import shutil
from typing import Any

import pytest

from tubeamp.app import TubeAmpApp


async def _startup_notifications(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    app = TubeAmpApp()
    seen: list[tuple[str, str]] = []

    def record(message: Any, **kwargs: Any) -> None:
        seen.append((str(message), str(kwargs.get("severity", "information"))))

    monkeypatch.setattr(app, "notify", record)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
    return seen


async def test_missing_ffmpeg_is_announced(monkeypatch: pytest.MonkeyPatch) -> None:
    real_which = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda cmd, *a, **k: None if cmd == "ffmpeg" else real_which(cmd, *a, **k),
    )

    notifications = await _startup_notifications(monkeypatch)

    assert any("ffmpeg" in message and severity == "warning" for message, severity in notifications)


async def test_nothing_is_said_when_ffmpeg_is_there(monkeypatch: pytest.MonkeyPatch) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is genuinely missing on this machine")

    notifications = await _startup_notifications(monkeypatch)

    assert not [message for message, _ in notifications if "ffmpeg" in message]
