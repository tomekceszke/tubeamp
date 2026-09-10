"""Guards on what a released copy carries and what it reads.

These cover the two things a first release gets wrong quietly: shipping the
author's own configuration, and reading a stray one from whatever directory the
user happened to be standing in.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

from tubeamp.__main__ import _handle_cli_flags, _libmpv_hint, _require_libmpv
from tubeamp.config import AppConfig


@pytest.fixture
def elsewhere(tmp_path: Path) -> Iterator[Path]:
    """A directory that is not a source checkout."""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)


class TestLocalConfigScope:
    LOCAL = b'[youtube]\ndefault_playlist = "https://example.invalid/private"\n'

    def test_local_toml_applies_in_a_source_checkout(self, elsewhere: Path) -> None:
        (elsewhere / "local.toml").write_bytes(self.LOCAL)
        (elsewhere / "pyproject.toml").write_text("[project]\n")

        config = AppConfig.load(path=elsewhere / "absent.toml")

        assert config.youtube.default_playlist == "https://example.invalid/private"

    def test_local_toml_is_ignored_outside_one(self, elsewhere: Path) -> None:
        """An installed tubeamp runs from arbitrary directories."""
        (elsewhere / "local.toml").write_bytes(self.LOCAL)

        config = AppConfig.load(path=elsewhere / "absent.toml")

        assert config.youtube.default_playlist is None


class TestCliFlags:
    def test_version_short_circuits(self, capsys: pytest.CaptureFixture[str]) -> None:
        from tubeamp import __version__

        assert _handle_cli_flags(["--version"]) is True
        assert capsys.readouterr().out.strip() == f"tubeamp {__version__}"

    def test_help_short_circuits(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert _handle_cli_flags(["--help"]) is True
        assert "Usage: tubeamp" in capsys.readouterr().out

    def test_no_flags_launches_the_app(self) -> None:
        assert _handle_cli_flags([]) is False


class TestLibmpvPreflight:
    """python-mpv raises at import time, so the app's own guard never runs.

    A fresh install without the runtime library is the single most likely
    failure, and it used to surface as a stack trace.
    """

    def _without_libmpv(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "mpv":
                raise OSError("Cannot find libmpv in the usual places.")
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(builtins, "__import__", fake_import)

    def test_missing_library_is_reported_not_raised(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._without_libmpv(monkeypatch)

        assert _require_libmpv() is False

        err = capsys.readouterr().err
        assert "could not load libmpv" in err
        assert "ffmpeg" in err

    def test_present_library_passes(self) -> None:
        pytest.importorskip("mpv")
        assert _require_libmpv() is True

    @pytest.mark.parametrize(
        ("system", "expected"),
        [("Darwin", "brew install mpv"), ("Windows", "WSL2")],
    )
    def test_hint_matches_the_platform(
        self, monkeypatch: pytest.MonkeyPatch, system: str, expected: str
    ) -> None:
        monkeypatch.setattr("platform.system", lambda: system)
        assert expected in _libmpv_hint()

    def test_linux_hint_names_the_package_manager(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("platform.system", lambda: "Linux")
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/dnf" if cmd == "dnf" else None)
        assert "dnf install mpv mpv-libs" in _libmpv_hint()

    def test_unknown_linux_still_says_something_useful(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("platform.system", lambda: "Linux")
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        assert "libmpv" in _libmpv_hint()
