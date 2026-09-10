#!/usr/bin/env python3
"""Screenshot the real player for the README.

The README used to carry a hand-drawn mock-up, which was wrong twice over: the
column counts drifted, and it showed a spectrum the widget has never produced.
Capturing the app fixed the content but not the rendering — a block of box
characters lines up only as long as every glyph in it comes from the same font,
and PyPI's font stack substitutes for some of them, so the frame's right edge
came out wavy there while GitHub was fine.

A picture has no such problem, and it carries the colour the code block never
could. Textual exports a real SVG of the screen; headless Chrome turns that into
a PNG that both GitHub and PyPI render identically.

    python scripts/capture_player_shot.py           # write docs/player.png
    python scripts/capture_player_shot.py --svg     # keep the intermediate SVG
"""

from __future__ import annotations

import argparse
import asyncio
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tubeamp.app import TubeAmpApp
from tubeamp.themes import get_theme
from tubeamp.theming import apply_theme
from tubeamp.widgets.playlist import PlaylistEntry, PlaylistWidget
from tubeamp.widgets.spectrum import SpectrumWidget
from tubeamp.widgets.track_info import TrackInfoWidget
from tubeamp.widgets.volume import VolumeWidget

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "player.png"

WIDTH, HEIGHT = 78, 22
THEME = "classic"          # never the reader's own config
SCALE = 2                  # so the PNG still looks sharp scaled down

TRACKS = (
    ("Around the World", 429),
    ("Da Funk", 328),
    ("Revolution 909", 326),
    ("Burnin'", 409),
    ("Rollin' & Scratchin'", 447),
)
POSITION = 154.0

# One believable frame: bass-heavy, falling towards the treble, but alive
# across the whole range the way real music is
SPECTRUM = [0.97, 0.74, 0.89, 0.61, 0.78, 0.52, 0.66, 0.44, 0.57, 0.38, 0.49, 0.33]

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
)


def mmss(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


async def capture_svg() -> str:
    """Stage a moment of playback and export the screen as SVG."""
    app = TubeAmpApp()
    async with app.run_test(size=(WIDTH, HEIGHT)) as pilot:
        await pilot.pause()

        # The app polls the visualizer on a timer, and the widgets run marquee
        # and spinner timers of their own. Every one of them would paint over
        # the frame being staged — and the visualizer, having no analysis to
        # replay here, would blank the spectrum outright.
        for pump in (app, *app.query("*")):
            for timer in list(getattr(pump, "_timers", ())):
                timer.stop()

        apply_theme(app, get_theme(THEME))

        playlist = app.query_one("#playlist", PlaylistWidget)
        playlist.set_entries(
            [PlaylistEntry(title=title, duration_str=mmss(d)) for title, d in TRACKS],
            reset=True,
        )
        playlist.playing_index = 0
        playlist.selected_index = 0
        playlist.set_loading(False)

        info = app.query_one("#track-info", TrackInfoWidget)
        title, duration = TRACKS[0]
        info.update_track(title, "Daft Punk", duration=float(duration))
        info.update_position(POSITION)

        app.query_one("#spectrum", SpectrumWidget).update_bars(list(SPECTRUM))
        app.query_one("#volume-bar", VolumeWidget).volume = 80

        await pilot.pause()
        await pilot.pause()
        return app.export_screenshot(title="TubeAmp")


def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def svg_size(svg: str) -> tuple[int, int]:
    width = re.search(r'width="([\d.]+)"', svg)
    height = re.search(r'height="([\d.]+)"', svg)
    if not width or not height:
        raise SystemExit("the exported SVG declares no size")
    return round(float(width.group(1))), round(float(height.group(1)))


def to_png(svg: str, destination: Path) -> None:
    """Render the SVG with Chrome, which has real font handling."""
    chrome = find_chrome()
    if chrome is None:
        raise SystemExit(
            "no Chrome or Chromium found to rasterise the SVG; "
            f"tried: {', '.join(CHROME_CANDIDATES)}"
        )

    width, height = svg_size(svg)
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "player.svg"
        source.write_text(svg)
        shot = Path(tmp) / "player.png"
        subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--force-device-scale-factor={SCALE}",
                f"--window-size={width},{height}",
                f"--screenshot={shot}",
                source.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(shot, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", action="store_true", help="also keep docs/player.svg")
    args = parser.parse_args()

    svg = asyncio.run(capture_svg())
    if args.svg:
        (OUTPUT.parent / "player.svg").write_text(svg)

    to_png(svg, OUTPUT)
    size = OUTPUT.stat().st_size
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({size // 1024} KB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
