#!/usr/bin/env python3
"""Render the real player headlessly and paste it into the README.

The mock-up in the README used to be drawn by hand, which meant it was wrong
twice over: the column counts drifted, and it showed a two-row spectrum the
widget has never produced. This boots the actual app, stages a moment of
playback, and captures what the compositor draws.

    python scripts/capture_player_art.py            # print it
    python scripts/capture_player_art.py --write    # replace the README block
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from tubeamp.app import TubeAmpApp
from tubeamp.widgets.playlist import PlaylistEntry, PlaylistWidget
from tubeamp.widgets.spectrum import SpectrumWidget
from tubeamp.widgets.track_info import TrackInfoWidget
from tubeamp.widgets.volume import VolumeWidget

WIDTH, HEIGHT = 78, 22

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


def mmss(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


async def capture() -> str:
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

        strips = app.screen._compositor.render_strips()
        return "\n".join(strip.text.rstrip() for strip in strips)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="update README.md in place")
    args = parser.parse_args()

    art = asyncio.run(capture())

    widths = {len(line) for line in art.splitlines()}
    if len(widths) != 1:
        print(f"capture is ragged: widths {sorted(widths)}", file=sys.stderr)
        return 1

    if not args.write:
        print(art)
        return 0

    readme = Path(__file__).resolve().parent.parent / "README.md"
    text = readme.read_text()
    # The first fenced block with no language, which is where the art lives
    pattern = re.compile(r"\n```\n[┏┌].*?\n```\n", re.DOTALL)
    if not pattern.search(text):
        print("no art block found in README.md", file=sys.stderr)
        return 1
    readme.write_text(pattern.sub(f"\n```\n{art}\n```\n", text, count=1))
    print(f"README.md updated: {len(art.splitlines())} lines, {widths.pop()} columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
