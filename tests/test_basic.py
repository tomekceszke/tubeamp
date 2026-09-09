"""Basic smoke tests for TubeAmp modules."""

from tubeamp import __version__, __app_name__
from tubeamp.config import AppConfig, AudioConfig, VisualizerConfig
from tubeamp.visualizer import SimulatedVisualizer
from tubeamp.youtube import YouTubeTrack


def test_version() -> None:
    assert __version__ == "0.1.0"
    assert __app_name__ == "tubeamp"


def test_default_config() -> None:
    config = AppConfig()
    assert config.audio.volume == 80
    assert config.audio.quality == "bestaudio"
    assert config.visualizer.bars == 16
    assert config.visualizer.framerate == 30


def test_youtube_track_duration() -> None:
    track = YouTubeTrack(
        video_id="abc123",
        title="Test",
        channel="Artist",
        duration=429,
    )
    assert track.display_duration == "7:09"
    assert track.watch_url == "https://www.youtube.com/watch?v=abc123"


def test_youtube_track_long_duration() -> None:
    track = YouTubeTrack(
        video_id="x", title="Long", channel="A", duration=7384
    )
    assert track.display_duration == "2:03:04"


def test_simulated_visualizer() -> None:
    viz = SimulatedVisualizer(bars=20)
    assert viz.num_bars == 20

    bars = viz.get_bars()
    assert len(bars) == 20
    assert all(b == 0.0 for b in bars)  # not started

    viz.start()
    viz.set_playing(True)
    bars = viz.get_bars()
    assert len(bars) == 20
    assert any(b > 0.0 for b in bars)  # should have data now

    viz.stop()
    bars = viz.get_bars()
    assert all(b == 0.0 for b in bars)  # stopped


def test_config_audio_defaults() -> None:
    audio = AudioConfig()
    assert audio.volume == 80
    assert audio.quality == "bestaudio"


def test_visualizer_config_defaults() -> None:
    viz = VisualizerConfig()
    assert viz.bars == 16
    assert viz.framerate == 30
    assert viz.sensitivity == 100
