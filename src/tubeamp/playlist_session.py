"""Pagination state for the loaded playlist or search results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tubeamp.youtube import YouTubeTrack


@dataclass
class PlaylistSession:
    """What is currently loaded, and where the next page would come from.

    A session is either backed by a playlist URL or by a search query, never
    both. Keeping the pair in one place removes the mirrored field-by-field
    resets that each branch of the search used to repeat.
    """

    tracks: list[YouTubeTrack] = field(default_factory=list)
    current_index: int = -1

    playlist_url: str | None = None
    search_query: str | None = None
    loaded_count: int = 0
    has_more: bool = False
    is_loading_more: bool = False

    def start_playlist(self, url: str) -> None:
        self._reset(playlist_url=url, has_more=True)

    def start_search(self, query: str) -> None:
        self._reset(search_query=query, has_more=True)

    def start_single_track(self) -> None:
        """A one-off video URL: nothing more to page in."""
        self._reset()

    def _reset(
        self,
        *,
        playlist_url: str | None = None,
        search_query: str | None = None,
        has_more: bool = False,
    ) -> None:
        self.playlist_url = playlist_url
        self.search_query = search_query
        self.loaded_count = 0
        self.has_more = has_more

    @property
    def can_load_more(self) -> bool:
        return (
            self.has_more
            and not self.is_loading_more
            and (self.playlist_url is not None or self.search_query is not None)
        )

    @property
    def current_track(self) -> YouTubeTrack | None:
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None

    def __len__(self) -> int:
        return len(self.tracks)
