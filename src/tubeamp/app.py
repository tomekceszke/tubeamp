"""TubeAmp — main Textual application."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import Any, TypeVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from tubeamp.config import AppConfig
from tubeamp.player import PlaybackState, Player, TrackInfo
from tubeamp.themes import get_theme, get_theme_names, to_textual_theme
from tubeamp.visualizer import BaseVisualizer, create_visualizer
from tubeamp.widgets.controls import ControlsWidget
from tubeamp.widgets.playlist import PlaylistEntry, PlaylistWidget
from tubeamp.widgets.search import SearchScreen
from tubeamp.widgets.spectrum import SpectrumWidget
from tubeamp.widgets.theme_picker import ThemePickerScreen
from tubeamp.widgets.track_info import TrackInfoWidget
from tubeamp.widgets.volume import VolumeWidget
from tubeamp.youtube import YouTubeService, YouTubeTrack

logger = logging.getLogger(__name__)

CSS_PATH = Path(__file__).parent / "styles" / "tubeamp.tcss"

SEEK_THROTTLE_INTERVAL = 0.1  # seconds between seeks
LAZY_LOAD_THRESHOLD = 5  # tracks from end to trigger lazy load

W = TypeVar("W", bound=Widget)


class PanelDivider(Widget):
    """Vertical box-drawing divider between spectrum and controls panels."""

    def render(self) -> Text:
        h = self.size.height
        return Text("\n".join(["║"] * max(h, 1)), style="#333333")


class SectionSeparator(Static):
    """Horizontal box-drawing separator between sections."""

    def on_mount(self) -> None:
        self._draw()

    def on_resize(self) -> None:
        self._draw()

    def _draw(self) -> None:
        self.update("─" * max(self.size.width, 40))


class PanelSeparator(Static):
    """Thinner horizontal separator for inside panels."""

    def on_mount(self) -> None:
        self._draw()

    def on_resize(self) -> None:
        self._draw()

    def _draw(self) -> None:
        w = max(self.size.width - 2, 10)
        self.update("─" * w)


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
        self._spectrum_widget: SpectrumWidget | None = None
        self._playlist_tracks: list[YouTubeTrack] = []
        self._current_index: int = -1
        self._shuffle = False
        self._repeat_mode = "off"
        self._last_seek_time: float = 0.0

        # Lazy loading state
        self._playlist_url: str | None = None
        self._search_query: str | None = None
        self._playlist_loaded_count: int = 0
        self._playlist_has_more: bool = False
        self._is_loading_more: bool = False

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
            self._player.on("track_changed", self._on_track_changed)
            self._player.on("position_changed", self._on_position_changed)
            self._player.on("state_changed", self._on_state_changed)
            self._player.on("track_ended", self._on_track_ended)
            logger.info("Player initialized")
        except Exception:
            logger.exception("Failed to initialize player")
            self.notify("mpv not available - install mpv first", severity="error")

        self._youtube = YouTubeService(
            cookies_browser=self._config.youtube.cookies_browser,
        )

        self._visualizer = create_visualizer(
            bars=self._config.visualizer.bars,
            framerate=self._config.visualizer.framerate,
            sensitivity=self._config.visualizer.sensitivity,
            backend=self._config.visualizer.backend,
            cookies_browser=self._config.youtube.cookies_browser,
        )
        self._visualizer.start()

        self.set_interval(
            1.0 / self._config.visualizer.framerate,
            self._refresh_visualizer,
        )

        # Cache spectrum widget reference to avoid repeated tree walks
        self._spectrum_widget = self.query_one("#spectrum", SpectrumWidget)

        controls = self.query_one("#controls", ControlsWidget)
        controls.volume = self._config.audio.volume
        volume_widget = self.query_one("#volume-bar", VolumeWidget)
        volume_widget.volume = self._config.audio.volume

        if self._config.youtube.default_playlist:
            logger.info("Loading default playlist: %s", self._config.youtube.default_playlist)
            playlist = self.query_one("#playlist", PlaylistWidget)
            playlist.set_loading(True)
            self.call_later(lambda: self.run_worker(
                self._handle_search_result(self._config.youtube.default_playlist),
                exclusive=True,
            ))

    # ── Widget Query Helper ────────────────────────────────────

    def _query_widget(self, selector: str, widget_type: type[W]) -> W | None:
        """Query a widget, returning None if not found."""
        try:
            return self.query_one(selector, widget_type)
        except Exception:
            return None

    # ── Visualizer ──────────────────────────────────────────────

    def _refresh_visualizer(self) -> None:
        """Timer callback: fetch bar data and push to spectrum widget."""
        if self._visualizer and self._spectrum_widget:
            bars = self._visualizer.get_bars()
            self._spectrum_widget.update_bars(bars)

    # ── Player Event Handlers ───────────────────────────────────

    def _safe_call(self, fn: Any, *args: Any) -> None:
        """Call a function on the main thread, handling both same-thread and cross-thread."""
        import threading
        try:
            if threading.current_thread() is threading.main_thread():
                fn(*args)
            else:
                self.call_from_thread(fn, *args)
        except Exception:
            logger.exception("Error in safe_call for %s", fn.__name__)

    def _on_track_changed(self, track: TrackInfo) -> None:
        """Handle track change from mpv."""
        self._safe_call(self._update_track_info, track)

    def _update_track_info(self, track: TrackInfo) -> None:
        track_info = self.query_one("#track-info", TrackInfoWidget)
        track_info.update_track(
            title=track.title,
            artist=track.artist,
            duration=track.duration,
        )

    def _on_position_changed(self, position: float) -> None:
        """Handle playback position update."""
        self._safe_call(self._update_position, position)

    def _update_position(self, position: float) -> None:
        track_info = self.query_one("#track-info", TrackInfoWidget)
        track_info.update_position(position)
        if self._visualizer:
            self._visualizer.set_position(position)

    def _on_state_changed(self, state: PlaybackState) -> None:
        """Handle playback state change."""
        self._safe_call(self._update_state, state)

    def _update_state(self, state: PlaybackState) -> None:
        controls = self.query_one("#controls", ControlsWidget)
        if state == PlaybackState.STOPPED:
            controls.playback_state = "stopped"
        elif state == PlaybackState.PLAYING:
            controls.playback_state = "playing"
        elif state == PlaybackState.PAUSED:
            controls.playback_state = "paused"

        is_playing = state in (PlaybackState.PLAYING, PlaybackState.BUFFERING)
        if self._visualizer:
            self._visualizer.set_playing(is_playing)

    def _on_track_ended(self) -> None:
        """Handle end of track — advance to next."""
        self._safe_call(self._play_next)

    # ── YouTube Search ──────────────────────────────────────────

    def _do_search(self, query: str) -> list[YouTubeTrack]:
        """Run YouTube search in a worker thread (blocking yt-dlp call)."""
        if not self._youtube:
            return []

        if query.startswith(("http://", "https://", "www.")):
            if "playlist" in query or "list=" in query:
                batch_size = self._calculate_playlist_batch_size()
                self._playlist_url = query
                self._search_query = None
                self._playlist_loaded_count = 0
                self._playlist_has_more = True
                tracks = self._youtube.get_playlist(query, max_items=batch_size)
                self._playlist_loaded_count = len(tracks)
                logger.info(
                    "Initially loaded %d tracks from playlist (batch size: %d)",
                    len(tracks), batch_size,
                )
                return tracks
            else:
                self._playlist_url = None
                self._search_query = None
                self._playlist_has_more = False
                track = self._youtube.get_track_info(query)
                return [track] if track else []
        else:
            batch_size = self._calculate_playlist_batch_size()
            self._playlist_url = None
            self._search_query = query
            self._playlist_loaded_count = 0
            self._playlist_has_more = True
            tracks = self._youtube.search(query, max_results=batch_size)
            self._playlist_loaded_count = len(tracks)
            logger.info(
                "Initially loaded %d search results (batch size: %d)",
                len(tracks), batch_size,
            )
            return tracks

    def _calculate_playlist_batch_size(self) -> int:
        """Calculate optimal batch size based on playlist viewport height."""
        try:
            playlist = self.query_one("#playlist", PlaylistWidget)
            scroll_container = playlist.query_one("#playlist-scroll", VerticalScroll)
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
        """Execute search and load results into playlist."""
        logger.info("Searching: %s", query)
        playlist = self.query_one("#playlist", PlaylistWidget)

        loop = asyncio.get_running_loop()
        try:
            tracks = await loop.run_in_executor(None, self._do_search, query)
        except Exception as e:
            logger.exception("Search failed")
            playlist.set_loading(False)
            self.notify(f"Search failed: {e}", severity="error", timeout=5)
            return

        if not tracks:
            playlist.set_loading(False)
            self.notify("No results found", severity="warning", timeout=3)
            return

        self._load_search_results(tracks)
        playlist.set_loading(False)

    # ── Playlist Management ─────────────────────────────────────

    def _play_track(self, index: int) -> None:
        """Play a specific track from the playlist by index."""
        if not (0 <= index < len(self._playlist_tracks)):
            return

        track = self._playlist_tracks[index]
        self._current_index = index

        if self._player:
            track_info = TrackInfo(
                title=track.title,
                artist=track.channel,
                duration=float(track.duration),
                url=track.watch_url,
            )
            self._player.play(track.watch_url, track_info)

            playlist_widget = self.query_one("#playlist", PlaylistWidget)
            playlist_widget.playing_index = index

            # Kick off pre-analysis for the analyzed visualizer backend
            if self._visualizer:
                self._visualizer.analyze_track(track.watch_url, track.video_id)

            logger.info("Now playing: %s", track.title)

    def _play_next(self) -> None:
        """Advance to next track, respecting repeat/shuffle."""
        if not self._playlist_tracks:
            return

        if self._repeat_mode == "one":
            self._play_track(self._current_index)
        elif self._shuffle:
            import random
            next_idx = random.randint(0, len(self._playlist_tracks) - 1)
            self._play_track(next_idx)
        else:
            next_idx = self._current_index + 1
            if next_idx >= len(self._playlist_tracks):
                if self._repeat_mode == "all":
                    next_idx = 0
                else:
                    return
            self._play_track(next_idx)

    def _play_prev(self) -> None:
        """Go to previous track."""
        if not self._playlist_tracks:
            return
        prev_idx = max(0, self._current_index - 1)
        self._play_track(prev_idx)

    @staticmethod
    def _make_playlist_entry(track: YouTubeTrack) -> PlaylistEntry:
        return PlaylistEntry(
            title=track.title,
            duration_str=track.display_duration,
        )

    def _load_search_results(self, tracks: list[YouTubeTrack]) -> None:
        """Load search results into the playlist widget."""
        self._playlist_tracks = tracks
        self._current_index = -1
        self._is_loading_more = False
        playlist = self.query_one("#playlist", PlaylistWidget)
        entries = [self._make_playlist_entry(t) for t in tracks]
        playlist.set_entries(entries, reset=True)

    # ── Action Handlers (keybindings) ───────────────────────────

    def action_toggle_play(self) -> None:
        if self._player:
            if self._player.state == PlaybackState.STOPPED and self._playlist_tracks:
                idx = max(0, self._current_index)
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

        import time
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
        controls = self._query_widget("#controls", ControlsWidget)
        volume_widget = self._query_widget("#volume-bar", VolumeWidget)
        if controls:
            controls.volume = self._player.volume
        if volume_widget:
            volume_widget.volume = self._player.volume
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
        controls = self.query_one("#controls", ControlsWidget)
        controls.shuffle = self._shuffle

    def action_toggle_repeat(self) -> None:
        modes = ["off", "all", "one"]
        current_idx = modes.index(self._repeat_mode)
        self._repeat_mode = modes[(current_idx + 1) % len(modes)]
        controls = self.query_one("#controls", ControlsWidget)
        controls.repeat_mode = self._repeat_mode

    def action_search(self) -> None:
        """Open search modal and query YouTube."""
        self.push_screen(SearchScreen(self._theme), callback=self._on_search_dismissed)

    def _on_search_dismissed(self, query: str | None) -> None:
        """Handle search modal result."""
        if query:
            playlist = self.query_one("#playlist", PlaylistWidget)
            playlist.set_loading(True)
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
        """Apply the current theme to all widgets."""
        theme = self._theme

        container = self._query_widget("#player-container", Widget)
        if container:
            container.styles.border = ("heavy", theme.primary)

        spectrum = self._query_widget("#spectrum", SpectrumWidget)
        if spectrum:
            spectrum.set_gradient(theme.primary_dim, theme.primary_bright)

        playlist = self._query_widget("#playlist", PlaylistWidget)
        if playlist:
            playlist.set_theme(
                selection_bg=theme.selection_bg,
                selection_fg=theme.selection_fg,
                playing_color=theme.playing,
            )

        controls = self._query_widget("#controls", ControlsWidget)
        if controls:
            controls.set_theme(
                primary=theme.primary_bright,
                shuffle_active=theme.shuffle_active,
                repeat_all=theme.repeat_all,
                repeat_one=theme.repeat_one,
            )

        track_info = self._query_widget("#track-info", TrackInfoWidget)
        if track_info:
            track_info.set_theme(primary=theme.primary_bright, primary_dim=theme.primary_dim)

        volume = self._query_widget("#volume-bar", VolumeWidget)
        if volume:
            volume.set_theme(bar_color=theme.primary_dim, bar_color_top=theme.primary_bright)

        # Register as Textual theme so toasts/scrollbars pick up our colors
        try:
            textual_theme = to_textual_theme(theme)
            self.register_theme(textual_theme)
            self.theme = textual_theme.name
        except Exception:
            logger.warning("Failed to register Textual theme")

        logger.info("Theme %s applied", theme.name)

    def action_playlist_down(self) -> None:
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.select_next()
        self._check_lazy_load()

    def action_playlist_up(self) -> None:
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.select_prev()

    def action_playlist_page_down(self) -> None:
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.select_page_down()
        self._check_lazy_load()

    def action_playlist_page_up(self) -> None:
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.select_page_up()

    def action_playlist_home(self) -> None:
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.select_first()

    def action_playlist_end(self) -> None:
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.select_last()
        self._check_lazy_load()

    def _check_lazy_load(self) -> None:
        """Check if we should load more tracks (lazy loading)."""
        if not self._playlist_has_more or self._is_loading_more:
            return

        playlist = self.query_one("#playlist", PlaylistWidget)
        tracks_remaining = len(self._playlist_tracks) - playlist.selected_index

        if tracks_remaining <= LAZY_LOAD_THRESHOLD:
            self.run_worker(self._load_more_tracks(), exclusive=False)

    async def _load_more_tracks(self) -> None:
        """Load more tracks from the playlist or search results."""
        if not self._youtube or self._is_loading_more:
            return

        if not self._playlist_url and not self._search_query:
            return

        self._is_loading_more = True
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.set_loading(True)
        self.notify("Loading more tracks...", timeout=2)

        try:
            loop = asyncio.get_running_loop()
            batch_size = self._calculate_playlist_batch_size()

            if self._playlist_url:
                new_tracks = await loop.run_in_executor(
                    None,
                    lambda: self._youtube.get_playlist(
                        self._playlist_url,
                        max_items=self._playlist_loaded_count + batch_size
                    )
                )
            else:  # self._search_query
                new_tracks = await loop.run_in_executor(
                    None,
                    lambda: self._youtube.search(
                        self._search_query,
                        max_results=self._playlist_loaded_count + batch_size
                    )
                )

            actual_new_tracks = new_tracks[self._playlist_loaded_count:]

            if actual_new_tracks:
                self._playlist_tracks.extend(actual_new_tracks)
                self._playlist_loaded_count = len(new_tracks)

                for t in actual_new_tracks:
                    playlist.append_entry(self._make_playlist_entry(t))

                logger.info(
                    "Loaded %d more tracks (total: %d)",
                    len(actual_new_tracks), len(self._playlist_tracks),
                )
                self.notify(f"Loaded {len(actual_new_tracks)} more tracks", timeout=2)
            else:
                self._playlist_has_more = False
                logger.info("No more tracks to load")

        except Exception as e:
            logger.exception("Failed to load more tracks")
            self.notify(f"Failed to load more tracks: {e}", severity="error", timeout=3)
        finally:
            self._is_loading_more = False
            playlist = self.query_one("#playlist", PlaylistWidget)
            playlist.set_loading(False)

    def action_playlist_select(self) -> None:
        playlist = self.query_one("#playlist", PlaylistWidget)
        playlist.confirm_selection()

    def action_screenshot(self) -> None:
        """Save a screenshot of the current UI."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"tubeamp_screenshot_{timestamp}.svg"
        self.save_screenshot(path)
        self.notify(f"Screenshot saved: {path}", severity="information")

    def action_help(self) -> None:
        self.notify(
            "Space=Play/Pause  x=Stop  Up/Down=Navigate  Enter=Play  Left/Right=Seek  -/+=Vol  "
            "s=Shuffle  r=Repeat  t=Theme  /=Search  h=Help  q=Quit",
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

    async def _do_restart_visualizer(self) -> None:
        """Actually restart the visualizer (runs in worker thread)."""
        if self._visualizer:
            self._visualizer.stop()
            await asyncio.sleep(0.5)

        logger.info(
            "Restarting visualizer with bars=%d, sensitivity=%d",
            self._config.visualizer.bars,
            self._config.visualizer.sensitivity,
        )

        loop = asyncio.get_running_loop()
        self._visualizer = await loop.run_in_executor(
            None,
            lambda: create_visualizer(
                bars=self._config.visualizer.bars,
                framerate=self._config.visualizer.framerate,
                sensitivity=self._config.visualizer.sensitivity,
                backend=self._config.visualizer.backend,
                cookies_browser=self._config.youtube.cookies_browser,
            ),
        )
        self._visualizer.start()

        spectrum = self.query_one("#spectrum", SpectrumWidget)
        spectrum._num_bars = self._config.visualizer.bars

        # Re-trigger analysis for the current track (new bars count = new cache key)
        if (
            self._visualizer
            and 0 <= self._current_index < len(self._playlist_tracks)
            and self._player
            and self._player.state.name != "STOPPED"
        ):
            track = self._playlist_tracks[self._current_index]
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
