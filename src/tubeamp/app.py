"""TubeAmp — main Textual application."""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import random
import threading
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any, TypeVar, cast

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget

from tubeamp.config import AppConfig
from tubeamp.player import PlaybackState, Player, TrackInfo
from tubeamp.playlist_session import PlaylistSession
from tubeamp.themes import get_theme, get_theme_names
from tubeamp.theming import apply_theme
from tubeamp.visualizer import BaseVisualizer, create_visualizer
from tubeamp.widgets.controls import ControlsWidget
from tubeamp.widgets.playlist import PlaylistEntry, PlaylistWidget
from tubeamp.widgets.search import SearchScreen
from tubeamp.widgets.separators import (
    PanelDivider,
    PanelSeparator,
    SectionSeparator,
)
from tubeamp.widgets.spectrum import SpectrumWidget
from tubeamp.widgets.theme_picker import ThemePickerScreen
from tubeamp.widgets.track_info import TrackInfoWidget
from tubeamp.widgets.volume import VolumeWidget
from tubeamp.youtube import YouTubeService, YouTubeTrack

logger = logging.getLogger(__name__)

CSS_PATH = Path(__file__).parent / "styles" / "tubeamp.tcss"

SEEK_THROTTLE_INTERVAL = 0.1  # seconds between seeks
LAZY_LOAD_THRESHOLD = 5  # tracks from end to trigger lazy load

_CONTROL_STATES = {
    PlaybackState.STOPPED: "stopped",
    PlaybackState.PLAYING: "playing",
    PlaybackState.PAUSED: "paused",
}

W = TypeVar("W", bound=Widget)


class TubeAmpApp(App[None]):
    """The TubeAmp terminal music player application."""

    TITLE = "♪♫ TubeAmp ♫♪"
    SUB_TITLE = "It really whips the llama's ass!"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pause", show=True),
        Binding("x", "stop", "Stop", show=True),
        Binding("up", "playlist_up", "Up", show=True),
        Binding("down", "playlist_down", "Down", show=True),
        Binding("enter", "playlist_select", "Play", show=True),
        Binding("left", "rewind", "⏪ -10s", show=True),
        Binding("right", "fast_forward", "⏩ +10s", show=True),
        Binding("minus", "volume_down", "Vol-", show=True),
        Binding("plus", "volume_up", "Vol+", show=True),
        Binding("equals_sign", "volume_up", "Vol+", show=False),
        Binding("s", "toggle_shuffle", "Shuffle", show=True),
        Binding("r", "toggle_repeat", "Repeat", show=True),
        Binding("comma", "prev_track", "Prev", show=True),
        Binding("full_stop", "next_track", "Next", show=True),
        Binding("t", "theme_picker", "Theme", show=True),
        Binding("slash", "search", "Search", show=True),
        Binding("n", "playlist_down", "Down", show=False),
        Binding("m", "playlist_up", "Up", show=False),
        Binding("j", "playlist_down", "Down", show=False),
        Binding("k", "playlist_up", "Up", show=False),
        Binding("pageup", "playlist_page_up", "Page Up", show=False),
        Binding("pagedown", "playlist_page_down", "Page Down", show=False),
        Binding("home", "playlist_home", "First Track", show=False),
        Binding("end", "playlist_end", "Last Track", show=False),
        Binding("left_square_bracket", "decrease_bars", "Bars-", show=False),
        Binding("right_square_bracket", "increase_bars", "Bars+", show=False),
        Binding("f12", "screenshot", "Screenshot", show=False),
        Binding("h", "help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config = AppConfig.load()
        self._theme = get_theme(self._config.ui.theme)
        self._player: Player | None = None
        self._youtube: YouTubeService | None = None
        self._visualizer: BaseVisualizer | None = None
        self._widget_cache: dict[str, Widget] = {}
        self._session = PlaylistSession()
        self._shuffle = False
        self._repeat_mode = "off"
        self._last_seek_time: float = 0.0

    def compose(self) -> ComposeResult:
        with Vertical(id="player-container"):
            with Horizontal(id="main-panel"):
                yield SpectrumWidget(
                    num_bars=self._config.visualizer.bars,
                    id="spectrum",
                )
                yield PanelDivider(id="panel-divider")
                with Vertical(id="right-panel"):
                    yield VolumeWidget(id="volume-bar")
                    yield PanelSeparator(classes="panel-separator")
                    yield ControlsWidget(id="controls")
            yield SectionSeparator(classes="section-separator")
            yield TrackInfoWidget(id="track-info")
            yield SectionSeparator(classes="section-separator")
            yield PlaylistWidget(id="playlist")

    async def on_mount(self) -> None:
        """Initialize services after the UI is mounted."""
        await self._init_services()
        self.call_after_refresh(self._apply_theme)

    async def _init_services(self) -> None:
        """Initialize player, YouTube service, and visualizer."""
        try:
            self._player = Player(
                volume=self._config.audio.volume,
                quality=self._config.audio.quality,
            )
            # Player events arrive on mpv's thread, so every handler is
            # marshalled onto the main thread before it touches a widget
            for event, handler in (
                ("track_changed", self._update_track_info),
                ("position_changed", self._update_position),
                ("state_changed", self._update_state),
                ("track_ended", self._play_next),
            ):
                self._player.on(event, partial(self._safe_call, handler))
            logger.info("Player initialized")
        except Exception:
            logger.exception("Failed to initialize player")
            self.notify("mpv not available - install mpv first", severity="error")

        self._youtube = YouTubeService(
            cookies_browser=self._config.youtube.cookies_browser,
        )

        self._visualizer = self._make_visualizer()
        self._visualizer.start()

        self.set_interval(
            1.0 / self._config.visualizer.framerate,
            self._refresh_visualizer,
        )

        self._controls.volume = self._config.audio.volume
        self._volume_bar.volume = self._config.audio.volume

        if self._config.youtube.default_playlist:
            logger.info("Loading default playlist: %s", self._config.youtube.default_playlist)
            self._playlist.set_loading(True)
            self.call_later(lambda: self.run_worker(
                self._handle_search_result(self._config.youtube.default_playlist),
                exclusive=True,
            ))

    # ── Widget Access ──────────────────────────────────────────

    def _widget(self, selector: str, widget_type: type[W]) -> W:
        """Look a widget up once and keep it.

        compose() builds the tree and never changes it, so re-walking it on
        every keypress and every position tick is wasted work.
        """
        cached = self._widget_cache.get(selector)
        if cached is None:
            cached = self.query_one(selector, widget_type)
            self._widget_cache[selector] = cached
        return cast("W", cached)

    @property
    def _playlist(self) -> PlaylistWidget:
        return self._widget("#playlist", PlaylistWidget)

    @property
    def _controls(self) -> ControlsWidget:
        return self._widget("#controls", ControlsWidget)

    @property
    def _track_info(self) -> TrackInfoWidget:
        return self._widget("#track-info", TrackInfoWidget)

    @property
    def _volume_bar(self) -> VolumeWidget:
        return self._widget("#volume-bar", VolumeWidget)

    @property
    def _spectrum(self) -> SpectrumWidget:
        return self._widget("#spectrum", SpectrumWidget)

    # ── Visualizer ──────────────────────────────────────────────

    def _refresh_visualizer(self) -> None:
        """Timer callback: fetch bar data and push to spectrum widget."""
        if self._visualizer:
            self._spectrum.update_bars(self._visualizer.get_bars())

    # ── Player Event Handlers ───────────────────────────────────

    def _safe_call(self, fn: Any, *args: Any) -> None:
        """Call a function on the main thread, handling both same-thread and cross-thread."""
        try:
            if threading.current_thread() is threading.main_thread():
                fn(*args)
            else:
                self.call_from_thread(fn, *args)
        except Exception:
            logger.exception("Error in safe_call for %s", fn.__name__)

    def _update_track_info(self, track: TrackInfo) -> None:
        self._track_info.update_track(
            title=track.title,
            artist=track.artist,
            duration=track.duration,
        )

    def _update_position(self, position: float) -> None:
        self._track_info.update_position(position)
        if self._visualizer:
            self._visualizer.set_position(position)

    def _update_state(self, state: PlaybackState) -> None:
        label = _CONTROL_STATES.get(state)
        if label:
            self._controls.playback_state = label

        if self._visualizer:
            self._visualizer.set_playing(
                state in (PlaybackState.PLAYING, PlaybackState.BUFFERING)
            )

    # ── YouTube Search ──────────────────────────────────────────

    def _do_search(self, query: str) -> list[YouTubeTrack]:
        """Resolve a query in a worker thread (blocking yt-dlp call).

        A query is a playlist URL, a single video URL, or search terms; the
        session records which, so lazy loading knows where to page from.
        """
        if not self._youtube:
            return []

        is_url = query.startswith(("http://", "https://", "www."))

        if is_url and not ("playlist" in query or "list=" in query):
            self._session.start_single_track()
            track = self._youtube.get_track_info(query)
            return [track] if track else []

        batch_size = self._calculate_playlist_batch_size()
        if is_url:
            self._session.start_playlist(query)
            tracks = self._youtube.get_playlist(query, max_items=batch_size)
        else:
            self._session.start_search(query)
            tracks = self._youtube.search(query, max_results=batch_size)

        self._session.loaded_count = len(tracks)
        logger.info("Loaded %d tracks (batch size: %d)", len(tracks), batch_size)
        return tracks

    def _calculate_playlist_batch_size(self) -> int:
        """Calculate optimal batch size based on playlist viewport height."""
        try:
            scroll_container = self._playlist.query_one("#playlist-scroll", VerticalScroll)
            visible_height = scroll_container.size.height

            if visible_height == 0:
                screen_height = self.size.height
                estimated_playlist_height = max(10, screen_height - 17)
                logger.debug(
                    "Playlist not sized yet, estimating height %d from screen %d",
                    estimated_playlist_height, screen_height,
                )
                return estimated_playlist_height

            logger.debug("Playlist viewport height: %d", visible_height)
            return visible_height
        except Exception:
            logger.warning("Could not calculate playlist batch size, using default 15")
            return 15

    async def _handle_search_result(self, query: str) -> None:
        """Execute search and load results into self._playlist."""
        logger.info("Searching: %s", query)

        loop = asyncio.get_running_loop()
        try:
            tracks = await loop.run_in_executor(None, self._do_search, query)
        except Exception as e:
            logger.exception("Search failed")
            self._playlist.set_loading(False)
            self.notify(f"Search failed: {e}", severity="error", timeout=5)
            return

        if not tracks:
            self._playlist.set_loading(False)
            self.notify("No results found", severity="warning", timeout=3)
            return

        self._load_search_results(tracks)
        self._playlist.set_loading(False)

    # ── Playlist Management ─────────────────────────────────────

    def _play_track(self, index: int) -> None:
        """Play a specific track from the playlist by index."""
        if not (0 <= index < len(self._session.tracks)):
            return

        track = self._session.tracks[index]
        self._session.current_index = index

        if self._player:
            track_info = TrackInfo(
                title=track.title,
                artist=track.channel,
                duration=float(track.duration),
                url=track.watch_url,
            )
            self._player.play(track.watch_url, track_info)
            self._playlist.playing_index = index

            # Kick off pre-analysis for the analyzed visualizer backend
            if self._visualizer:
                self._visualizer.analyze_track(track.watch_url, track.video_id)

            logger.info("Now playing: %s", track.title)

    def _play_next(self) -> None:
        """Advance to next track, respecting repeat/shuffle."""
        if not self._session.tracks:
            return

        if self._repeat_mode == "one":
            self._play_track(self._session.current_index)
        elif self._shuffle:
            next_idx = random.randint(0, len(self._session.tracks) - 1)
            self._play_track(next_idx)
        else:
            next_idx = self._session.current_index + 1
            if next_idx >= len(self._session.tracks):
                if self._repeat_mode == "all":
                    next_idx = 0
                else:
                    return
            self._play_track(next_idx)

    def _play_prev(self) -> None:
        """Go to previous track."""
        if not self._session.tracks:
            return
        prev_idx = max(0, self._session.current_index - 1)
        self._play_track(prev_idx)

    @staticmethod
    def _make_playlist_entry(track: YouTubeTrack) -> PlaylistEntry:
        return PlaylistEntry(
            title=track.title,
            duration_str=track.display_duration,
        )

    def _load_search_results(self, tracks: list[YouTubeTrack]) -> None:
        """Load search results into the playlist widget."""
        self._session.tracks = tracks
        self._session.current_index = -1
        self._session.is_loading_more = False
        entries = [self._make_playlist_entry(t) for t in tracks]
        self._playlist.set_entries(entries, reset=True)

    # ── Action Handlers (keybindings) ───────────────────────────

    def action_toggle_play(self) -> None:
        if self._player:
            if self._player.state == PlaybackState.STOPPED and self._session.tracks:
                idx = max(0, self._session.current_index)
                self._play_track(idx)
            else:
                self._player.pause()

    def action_stop(self) -> None:
        if self._player:
            self._player.stop()

    def action_next_track(self) -> None:
        self._play_next()

    def action_prev_track(self) -> None:
        self._play_prev()

    def _seek_relative(self, delta: float) -> None:
        """Seek by delta seconds with throttling."""
        if not self._player or self._player.state == PlaybackState.STOPPED:
            return

        now = time.time()
        if now - self._last_seek_time < SEEK_THROTTLE_INTERVAL:
            return
        self._last_seek_time = now

        try:
            self._player.seek(delta, relative=True)
        except Exception as e:
            logger.debug("Seek failed (likely too fast): %s", e)

    def action_rewind(self) -> None:
        """Rewind 10 seconds."""
        self._seek_relative(-10.0)

    def action_fast_forward(self) -> None:
        """Fast forward 10 seconds."""
        self._seek_relative(10.0)

    def _update_volume(self) -> None:
        """Sync volume display after a volume change."""
        if not self._player:
            return
        self._controls.volume = self._player.volume
        self._volume_bar.volume = self._player.volume
        self._config.audio.volume = self._player.volume

    def action_volume_up(self) -> None:
        if self._player:
            self._player.volume_up()
            self._update_volume()

    def action_volume_down(self) -> None:
        if self._player:
            self._player.volume_down()
            self._update_volume()

    def action_toggle_shuffle(self) -> None:
        self._shuffle = not self._shuffle
        self._controls.shuffle = self._shuffle

    def action_toggle_repeat(self) -> None:
        modes = ["off", "all", "one"]
        current_idx = modes.index(self._repeat_mode)
        self._repeat_mode = modes[(current_idx + 1) % len(modes)]
        self._controls.repeat_mode = self._repeat_mode

    def action_search(self) -> None:
        """Open search modal and query YouTube."""
        self.push_screen(SearchScreen(self._theme), callback=self._on_search_dismissed)

    def _on_search_dismissed(self, query: str | None) -> None:
        """Handle search modal result."""
        if query:
            self._playlist.set_loading(True)
            self.run_worker(self._handle_search_result(query), exclusive=True)

    def action_theme_picker(self) -> None:
        """Open theme picker modal."""
        theme_names = get_theme_names()
        self.push_screen(
            ThemePickerScreen(self._theme, theme_names),
            callback=self._on_theme_selected
        )

    def _on_theme_selected(self, theme_name: str | None) -> None:
        """Handle theme selection."""
        if theme_name:
            self._theme = get_theme(theme_name)
            self._config.ui.theme = theme_name
            self._config.save()
            self._apply_theme()
            self.notify(f"Theme changed to {self._theme.name}", timeout=2)

    def _apply_theme(self) -> None:
        apply_theme(self, self._theme)

    def _move_selection(self, move: Callable[[], None]) -> None:
        """Move the highlight, then page in more tracks if we are near the end."""
        move()
        self._check_lazy_load()

    def action_playlist_down(self) -> None:
        self._move_selection(self._playlist.select_next)

    def action_playlist_up(self) -> None:
        self._move_selection(self._playlist.select_prev)

    def action_playlist_page_down(self) -> None:
        self._move_selection(self._playlist.select_page_down)

    def action_playlist_page_up(self) -> None:
        self._move_selection(self._playlist.select_page_up)

    def action_playlist_home(self) -> None:
        self._move_selection(self._playlist.select_first)

    def action_playlist_end(self) -> None:
        self._move_selection(self._playlist.select_last)

    def _check_lazy_load(self) -> None:
        if not self._session.can_load_more:
            return
        remaining = len(self._session.tracks) - self._playlist.selected_index
        if remaining <= LAZY_LOAD_THRESHOLD:
            self.run_worker(self._load_more_tracks(), exclusive=False)

    def _fetch_page(self, wanted: int) -> list[YouTubeTrack]:
        """Re-fetch the current source asking for `wanted` items.

        yt-dlp exposes no cursor, so paging means asking for a larger prefix
        and keeping the tail we have not seen.
        """
        session = self._session
        if not self._youtube:
            return []
        if session.playlist_url:
            return self._youtube.get_playlist(session.playlist_url, max_items=wanted)
        if session.search_query:
            return self._youtube.search(session.search_query, max_results=wanted)
        return []

    async def _load_more_tracks(self) -> None:
        """Append the next page of the playlist or search results."""
        session = self._session
        if not session.can_load_more:
            return

        session.is_loading_more = True
        self._playlist.set_loading(True)
        self.notify("Loading more tracks...", timeout=2)

        try:
            wanted = session.loaded_count + self._calculate_playlist_batch_size()
            loop = asyncio.get_running_loop()
            fetched = await loop.run_in_executor(None, self._fetch_page, wanted)

            new_tracks = fetched[session.loaded_count:]
            if not new_tracks:
                session.has_more = False
                logger.info("No more tracks to load")
                return

            session.tracks.extend(new_tracks)
            session.loaded_count = len(fetched)
            for track in new_tracks:
                self._playlist.append_entry(self._make_playlist_entry(track))

            logger.info(
                "Loaded %d more tracks (total: %d)",
                len(new_tracks), len(session.tracks),
            )
            self.notify(f"Loaded {len(new_tracks)} more tracks", timeout=2)

        except Exception as e:
            logger.exception("Failed to load more tracks")
            self.notify(f"Failed to load more tracks: {e}", severity="error", timeout=3)
        finally:
            session.is_loading_more = False
            self._playlist.set_loading(False)

    def action_playlist_select(self) -> None:
        self._playlist.confirm_selection()

    def action_screenshot(self) -> None:
        """Save a screenshot of the current UI."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"tubeamp_screenshot_{timestamp}.svg"
        self.save_screenshot(path)
        self.notify(f"Screenshot saved: {path}", severity="information")

    def action_help(self) -> None:
        self.notify(
            "Space=Play/Pause  x=Stop  ,/.=Prev/Next  Up/Down=Navigate  Enter=Play  "
            "Left/Right=Seek  -/+=Vol  [/]=Bars  s=Shuffle  r=Repeat  t=Theme  "
            "/=Search  F12=Screenshot  h=Help  q=Quit",
            timeout=10,
        )

    def _adjust_visualizer_setting(self, attr: str, delta: int, min_val: int, max_val: int) -> None:
        """Adjust a visualizer config setting, restart if changed, and save."""
        old_val = getattr(self._config.visualizer, attr)
        new_val = max(min_val, min(max_val, old_val + delta))
        setattr(self._config.visualizer, attr, new_val)
        self._config.save()
        if old_val != new_val:
            logger.info("Visualizer %s: %d", attr, new_val)
            self._restart_visualizer()
            self.notify(f"{attr.capitalize()}: {new_val}", timeout=1)

    def action_increase_bars(self) -> None:
        """Increase number of visualizer bars."""
        self._adjust_visualizer_setting("bars", 10, 10, 200)

    def action_decrease_bars(self) -> None:
        """Decrease number of visualizer bars."""
        self._adjust_visualizer_setting("bars", -10, 10, 200)

    def _restart_visualizer(self) -> None:
        """Restart visualizer with new settings."""
        self.run_worker(self._do_restart_visualizer(), exclusive=False)

    def _make_visualizer(self) -> BaseVisualizer:
        """Build a visualizer from the current configuration."""
        return create_visualizer(
            bars=self._config.visualizer.bars,
            framerate=self._config.visualizer.framerate,
            sensitivity=self._config.visualizer.sensitivity,
            backend=self._config.visualizer.backend,
            cookies_browser=self._config.youtube.cookies_browser,
        )

    async def _do_restart_visualizer(self) -> None:
        """Rebuild the visualizer after a settings change."""
        if self._visualizer:
            self._visualizer.stop()
            await asyncio.sleep(0.5)

        loop = asyncio.get_running_loop()
        self._visualizer = await loop.run_in_executor(None, self._make_visualizer)
        self._visualizer.start()
        self._spectrum.num_bars = self._config.visualizer.bars

        # A different bar count is a different cache key, so the current track
        # has to be analysed again
        track = self._session.current_track
        if track and self._player and self._player.state != PlaybackState.STOPPED:
            self._visualizer.set_position(self._player.position)
            self._visualizer.analyze_track(track.watch_url, track.video_id)


    # ── Playlist Widget Events ──────────────────────────────────

    async def on_playlist_widget_track_selected(
        self, event: PlaylistWidget.TrackSelected
    ) -> None:
        """Handle track selection from the playlist widget."""
        self._play_track(event.index)


    def on_track_info_widget_seek_requested(
        self, event: TrackInfoWidget.SeekRequested
    ) -> None:
        """Handle click-to-seek from the progress bar."""
        if not self._player or self._player.state == PlaybackState.STOPPED:
            return
        try:
            self._player.seek(event.position, relative=False)
        except Exception as e:
            logger.debug("Seek failed: %s", e)

    def on_controls_widget_stop_clicked(self) -> None:
        self.action_stop()

    def on_controls_widget_play_pause_clicked(self) -> None:
        self.action_toggle_play()

    def on_controls_widget_shuffle_clicked(self) -> None:
        self.action_toggle_shuffle()

    def on_controls_widget_repeat_clicked(self) -> None:
        self.action_toggle_repeat()

    def on_volume_widget_volume_changed(
        self, event: VolumeWidget.VolumeChanged
    ) -> None:
        """Handle click-to-set-volume from the volume bar."""
        if not self._player:
            return
        self._player.volume = event.volume
        self._update_volume()

    # ── Lifecycle ───────────────────────────────────────────────

    def action_quit(self) -> None:
        """Fast shutdown - cleanup happens in background."""
        # Intentionally catching all exceptions for fast exit — OS cleans up processes
        with contextlib.suppress(Exception):
            self._config.save()

        if self._visualizer:
            with contextlib.suppress(Exception):
                self._visualizer.stop()

        if self._player:
            with contextlib.suppress(Exception):
                self._player.quit()

        self.exit()
