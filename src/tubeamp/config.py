"""Application configuration with TOML persistence."""

from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "tubeamp"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"


@dataclass
class AudioConfig:
    volume: int = 80
    quality: str = "bestaudio"


@dataclass
class VisualizerConfig:
    bars: int = 16
    framerate: int = 30
    sensitivity: int = 100  # percent gain on bar height; 100 = neutral
    backend: str = "analyzed"  # "analyzed" | "simulated"


@dataclass
class YouTubeConfig:
    cookies_browser: str | None = None
    default_playlist: str | None = None


@dataclass
class UIConfig:
    theme: str = "classic"


def _filter_fields(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    """Filter a dict to only keys that are valid fields on a dataclass."""
    valid = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in data.items() if k in valid}


@dataclass
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    visualizer: VisualizerConfig = field(default_factory=VisualizerConfig)
    youtube: YouTubeConfig = field(default_factory=YouTubeConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_FILE) -> Self:
        """Load configuration from a TOML file, falling back to defaults.

        Also checks for local.toml in the current directory for repo-local settings.
        """
        config = cls()

        # Load global config from ~/.config/tubeamp/config.toml
        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)
            config = cls(
                audio=AudioConfig(
                    **_filter_fields(AudioConfig, data.get("audio", {})),
                ),
                visualizer=VisualizerConfig(
                    **_filter_fields(VisualizerConfig, data.get("visualizer", {})),
                ),
                youtube=YouTubeConfig(
                    **_filter_fields(YouTubeConfig, data.get("youtube", {})),
                ),
                ui=UIConfig(
                    **_filter_fields(UIConfig, data.get("ui", {})),
                ),
            )

        # Override with local.toml if present (repo-local settings).
        # The lookup is relative to the working directory, so it is gated on a
        # sibling pyproject.toml: an installed `tubeamp` is launched from
        # wherever the user happens to be, and an unrelated local.toml sitting
        # there must not silently rewrite their configuration.
        local_config = Path("local.toml")
        if local_config.exists() and Path("pyproject.toml").exists():
            with open(local_config, "rb") as f:
                local_data = tomllib.load(f)

            # Merge local settings (only override non-empty values)
            if "youtube" in local_data:
                yt_config = local_data["youtube"]
                if "default_playlist" in yt_config:
                    config.youtube.default_playlist = yt_config["default_playlist"]
                if "cookies_browser" in yt_config and yt_config["cookies_browser"]:
                    config.youtube.cookies_browser = yt_config["cookies_browser"]

        return config

    def save(self, path: Path = DEFAULT_CONFIG_FILE) -> None:
        """Persist current configuration to TOML file."""
        import tomli_w

        path.parent.mkdir(parents=True, exist_ok=True)

        data = dataclasses.asdict(self)
        # TOML doesn't support null; convert None values to empty strings
        for section in data.values():
            for k, v in section.items():
                if v is None:
                    section[k] = ""

        with open(path, "wb") as f:
            tomli_w.dump(data, f)
