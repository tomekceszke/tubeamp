"""Entry point for `python -m tubeamp` and the `tubeamp` console script."""

from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path

LOG_DIR = Path.home() / ".config" / "tubeamp"
LOG_FILE = LOG_DIR / "tubeamp.log"


def setup_logging() -> None:
    """Configure file-based logging (TUI apps can't log to stdout).

    Defaults to INFO. Set TUBEAMP_LOG_LEVEL=DEBUG for the per-frame and
    per-keypress detail, which is far too noisy to leave on by default.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = os.environ.get("TUBEAMP_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        filename=str(LOG_FILE),
        filemode="w",  # overwrite each run
    )
    # Quiet down noisy libs
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)
    logging.getLogger("mpv").setLevel(logging.WARNING)


def _put_venv_bin_on_path() -> None:
    """Make this interpreter's own bin directory visible to child processes.

    The visualizer shells out to `yt-dlp` and `ffmpeg`, and mpv's ytdl_hook
    looks `yt-dlp` up on PATH as well. Running the console script directly
    (`.venv/bin/tubeamp`, which is what run.sh does) does not activate the
    virtualenv, so a yt-dlp installed only inside it stays invisible to both
    and playback fails with nothing obvious in the log.
    """
    bin_dir = str(Path(sys.executable).parent)
    parts = os.environ.get("PATH", "").split(os.pathsep)
    if bin_dir not in parts:
        os.environ["PATH"] = os.pathsep.join([bin_dir, *parts])


def _hide_from_dock_macos() -> bool:
    """Hide the app from macOS Dock by transforming to background app.

    Returns True if successful, False otherwise.
    """
    try:
        from ctypes import Structure, byref, c_int, c_uint, cdll

        class ProcessSerialNumber(Structure):
            _fields_ = [('highLongOfPSN', c_uint), ('lowLongOfPSN', c_uint)]

        # Load Carbon framework
        carbon = cdll.LoadLibrary('/System/Library/Frameworks/Carbon.framework/Carbon')

        # Get current process serial number
        psn = ProcessSerialNumber()
        get_result = carbon.GetCurrentProcess(byref(psn))

        if get_result != 0:
            return False

        # Transform to UI Element Application (no dock icon, no menu bar)
        # kProcessTransformToUIElementApplication = 4
        transform_result = carbon.TransformProcessType(byref(psn), c_int(4))

        return bool(transform_result == 0)
    except Exception:
        return False


def main() -> None:
    """Launch the TubeAmp application."""
    _put_venv_bin_on_path()

    # On macOS, prevent the app from appearing in the Dock and bouncing
    if platform.system() == "Darwin":
        # Prevent mpv from creating GUI elements
        os.environ["SDL_VIDEODRIVER"] = "dummy"

        # Hide from dock
        _hide_from_dock_macos()

    setup_logging()
    logger = logging.getLogger("tubeamp")
    logger.info("Starting TubeAmp")
    logger.info("Log file: %s", LOG_FILE)

    from tubeamp.app import TubeAmpApp

    app = TubeAmpApp()
    app.run()


if __name__ == "__main__":
    main()
