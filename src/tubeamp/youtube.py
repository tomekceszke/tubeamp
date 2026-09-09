"""YouTube integration via yt-dlp for search, playlist extraction, and metadata."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import yt_dlp

from tubeamp.utils import format_time

logger = logging.getLogger(__name__)


@dataclass
class YouTubeTrack:
    """Represents a single YouTube video/track."""

    video_id: str
    title: str
    channel: str
    duration: int  # seconds
    url: str
    thumbnail_url: str = ""

    @property
    def display_duration(self) -> str:
        """Format duration as MM:SS or H:MM:SS."""
        return format_time(self.duration)

    @property
    def watch_url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


class YouTubeService:
    """Provides YouTube search, playlist extraction, and metadata resolution."""

    def __init__(self, cookies_browser: str | None = None) -> None:
        self._cookies_browser = cookies_browser

    def _extract(self, opts: dict[str, Any], url: str, **kwargs: Any) -> dict[str, Any] | None:
        """Run yt-dlp extract_info and return the result dict, or None on failure."""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False, **kwargs)
        except Exception:
            logger.exception("yt-dlp extraction failed for: %s", url)
            return None

    def _make_opts(self, **overrides: Any) -> dict[str, Any]:
        """Build yt-dlp options, gracefully handling cookies."""
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            **overrides,
        }

        # Only add cookies if configured — don't let it break everything
        if self._cookies_browser:
            try:
                opts["cookiesfrombrowser"] = (self._cookies_browser,)
            except Exception:
                logger.warning("Could not set cookies from browser: %s", self._cookies_browser)

        return opts

    def search(self, query: str, max_results: int = 20) -> list[YouTubeTrack]:
        """Search YouTube and return a list of tracks."""
        search_url = f"ytsearch{max_results}:{query}"
        logger.info("Searching YouTube: %s (max=%d)", query, max_results)

        # For search, use extract_flat to get results fast,
        # but we need 'in_playlist' to get durations
        opts = self._make_opts(extract_flat="in_playlist")

        result = self._extract(opts, search_url)
        if result is None:
            return self._search_no_cookies(query, max_results)

        if not result.get("entries"):
            logger.warning("Search returned no results for: %s", query)
            return []

        tracks = [self._entry_to_track(e) for e in result["entries"] if e]
        logger.info("Search returned %d tracks for: %s", len(tracks), query)
        return tracks

    def _search_no_cookies(self, query: str, max_results: int) -> list[YouTubeTrack]:
        """Fallback search without browser cookies."""
        search_url = f"ytsearch{max_results}:{query}"
        logger.info("Retrying search without cookies")

        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
        }

        result = self._extract(opts, search_url)
        if not result or "entries" not in result:
            return []

        tracks = [self._entry_to_track(e) for e in result["entries"] if e]
        logger.info("Search (no cookies) returned %d tracks", len(tracks))
        return tracks



    def get_playlist(self, playlist_url: str, max_items: int | None = None) -> list[YouTubeTrack]:
        """Extract tracks from a YouTube playlist URL.

        Args:
            playlist_url: The YouTube playlist URL
            max_items: Maximum number of items to fetch (None = all items)
        """
        logger.info("Extracting playlist: %s (max_items=%s)", playlist_url, max_items)
        opts = self._make_opts(
            extract_flat="in_playlist",
            playlistend=max_items if max_items else None,
        )

        result = self._extract(opts, playlist_url)
        if not result or "entries" not in result:
            return []

        tracks = [self._entry_to_track(e) for e in result["entries"] if e]
        logger.info("Extracted %d tracks from playlist", len(tracks))
        return tracks

    def get_track_info(self, url: str) -> YouTubeTrack | None:
        """Get full metadata for a single YouTube URL."""
        opts = self._make_opts()

        info = self._extract(opts, url)
        if not info:
            return None
        return self._entry_to_track(info)

    @staticmethod
    def _entry_to_track(entry: dict[str, Any]) -> YouTubeTrack:
        """Convert a yt-dlp info dict to a YouTubeTrack."""
        return YouTubeTrack(
            video_id=entry.get("id", ""),
            title=entry.get("title", "Unknown"),
            channel=entry.get("channel", entry.get("uploader", "Unknown")),
            duration=int(entry.get("duration") or 0),
            url=entry.get("url", entry.get("webpage_url", "")),
            thumbnail_url=entry.get("thumbnail", ""),
        )
