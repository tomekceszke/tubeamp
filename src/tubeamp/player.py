"""mpv-based audio player with playback controls and event emission."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import mpv

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    BUFFERING = auto()


@dataclass
class TrackInfo:
    """Metadata for the currently playing track."""

    title: str = "Unknown"
    artist: str = "Unknown"
    duration: float = 0.0
    url: str = ""
    thumbnail_url: str = ""


class Player:
    """Wraps libmpv for audio playback with YouTube integration.

    mpv natively supports yt-dlp via its ytdl_hook script, so we can pass
    YouTube URLs directly and mpv handles resolution + streaming.
    """

    def __init__(
        self,
        volume: int = 80,
        quality: str = "bestaudio",
        audio_device: str | None = None,
    ) -> None:
        self._state = PlaybackState.STOPPED
        self._current_track: TrackInfo | None = None
        self._position: float = 0.0
        self._listeners: dict[str, list[Callable[..., Any]]] = {}

        # Build mpv options
        mpv_kwargs: dict[str, Any] = {
            "video": False,
            "vo": "null",  # Null video output - no window at all
            "force_window": False,  # Don't create a window
            "keep_open": False,  # Don't keep window open
            "ytdl": True,
            "ytdl_format": quality,
            "input_default_bindings": False,
            "input_vo_keyboard": False,
        }

        # If a specific audio device is requested (see [audio] device in config)
        if audio_device:
            mpv_kwargs["audio_device"] = audio_device
            logger.info("mpv audio device: %s", audio_device)

        # Initialize mpv instance
        self._mpv = mpv.MPV(**mpv_kwargs)
        self._mpv.volume = volume

        # Register mpv property observers for reactive updates
        self._mpv.observe_property("time-pos", self._on_time_pos)
        self._mpv.observe_property("pause", self._on_pause_change)
        self._mpv.observe_property("media-title", self._on_title_change)
        self._mpv.observe_property("idle-active", self._on_idle)

    # ── Public API ──────────────────────────────────────────────

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def current_track(self) -> TrackInfo | None:
        return self._current_track

    @property
    def position(self) -> float:
        return self._position

    @property
    def volume(self) -> int:
        return int(self._mpv.volume or 0)

    @volume.setter
    def volume(self, value: int) -> None:
        self._mpv.volume = max(0, min(100, value))
        self._emit("volume_changed", self._mpv.volume)

    def play(self, url: str, track_info: TrackInfo | None = None) -> None:
        """Play a YouTube URL or any URL mpv can handle."""
        logger.info("Playing: %s", url)
        self._current_track = track_info or TrackInfo(url=url)
        self._mpv.play(url)
        self._state = PlaybackState.BUFFERING
        self._emit("track_changed", self._current_track)

    def pause(self) -> None:
        self._mpv.cycle("pause")

    def stop(self) -> None:
        self._mpv.stop()
        self._state = PlaybackState.STOPPED
        self._emit("state_changed", self._state)

    def seek(self, seconds: float, relative: bool = True) -> None:
        mode = "relative" if relative else "absolute"
        self._mpv.seek(seconds, mode)

    def volume_up(self, step: int = 5) -> None:
        self.volume = self.volume + step

    def volume_down(self, step: int = 5) -> None:
        self.volume = self.volume - step

    def quit(self) -> None:
        """Send quit command to mpv."""
        self._mpv.command("quit")

    # ── Event System ────────────────────────────────────────────

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        self._listeners.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args: Any) -> None:
        for cb in self._listeners.get(event, []):
            try:
                cb(*args)
            except Exception:
                logger.exception("Error in event callback for '%s'", event)

    # ── mpv Property Observers ──────────────────────────────────

    def _on_time_pos(self, _name: str, value: float | None) -> None:
        if value is not None:
            self._position = value
            if self._state == PlaybackState.BUFFERING:
                self._state = PlaybackState.PLAYING
                self._emit("state_changed", self._state)
            self._emit("position_changed", value)

    def _on_pause_change(self, _name: str, value: bool | None) -> None:
        if value is True:
            self._state = PlaybackState.PAUSED
        elif value is False and self._current_track:
            self._state = PlaybackState.PLAYING
        self._emit("state_changed", self._state)

    def _on_title_change(self, _name: str, value: str | None) -> None:
        if value and self._current_track:
            self._current_track.title = value
            self._emit("track_changed", self._current_track)

    def _on_idle(self, _name: str, value: bool | None) -> None:
        if value is True and self._state != PlaybackState.STOPPED:
            self._state = PlaybackState.STOPPED
            self._emit("track_ended")

    # ── Lifecycle ───────────────────────────────────────────────

    def shutdown(self) -> None:
        """Clean shutdown of mpv player."""
        logger.info("Shutting down mpv")
        try:
            self._mpv.unobserve_property("time-pos", self._on_time_pos)
            self._mpv.unobserve_property("pause", self._on_pause_change)
            self._mpv.unobserve_property("media-title", self._on_title_change)
            self._mpv.unobserve_property("idle-active", self._on_idle)

            if self._state != PlaybackState.STOPPED:
                self._mpv.command("stop")

            terminate_thread = threading.Thread(target=self._mpv.terminate)
            terminate_thread.daemon = True
            terminate_thread.start()
            terminate_thread.join(timeout=2.0)

            if terminate_thread.is_alive():
                logger.warning("mpv terminate timed out, forcing exit")
        except Exception:
            logger.exception("Error shutting down mpv")


