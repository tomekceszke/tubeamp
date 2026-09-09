"""Tests for the analyzed visualizer's level mapping and envelope behaviour."""

from typing import Any

import numpy as np

from tubeamp.visualizer import AnalyzedVisualizer


def _viz(bars: int = 16, fps: int = 30, **kwargs: Any) -> AnalyzedVisualizer:
    return AnalyzedVisualizer(bars=bars, fps=fps, **kwargs)


def test_normalize_leaves_headroom() -> None:
    """Bars must not sit at the ceiling — that was the old per-band p95 bug."""
    viz = _viz()
    rng = np.random.default_rng(0)
    # Music-like input: a falling spectral tilt plus loud and quiet passages.
    # Measured on real tracks, band levels span roughly 28 dB between the
    # median and the 99th percentile, so a flat noise field would not exercise
    # the mapping honestly.
    tilt = np.logspace(-1.3, -2.6, 16)
    envelope = 10 ** (rng.normal(0.0, 0.7, size=(600, 1)))
    raw = np.abs(rng.normal(0.0, 1.0, size=(600, 16))) * tilt * envelope

    norm = np.asarray(viz._normalize(raw.astype(np.float32)))

    assert norm.max() <= 1.0
    assert norm.mean() < 0.6, "bars are scaled too high"
    assert np.mean(norm >= 0.999) < 0.02, "too many bars clipped at full height"


def test_normalize_preserves_spectral_balance() -> None:
    """A bass-heavy signal must render bass taller than treble."""
    viz = _viz()
    raw = np.zeros((200, 16), dtype=np.float32)
    raw[:, :4] = 0.10   # loud low bands
    raw[:, 12:] = 0.001  # quiet high bands

    norm = np.asarray(viz._normalize(raw))

    assert norm[:, :4].mean() > norm[:, 12:].mean()


def test_normalize_silence_is_empty() -> None:
    """Silence has no reference level of its own; the absolute floor catches it."""
    viz = _viz()
    raw = np.zeros((100, 16), dtype=np.float32)

    norm = np.asarray(viz._normalize(raw))

    assert norm.max() == 0.0


def test_render_does_not_compound_blur() -> None:
    """Neighbour blending must not be fed back into the envelope state.

    Re-blurring an already blurred spectrum every frame collapsed the bars
    into a flat hump within about a second.
    """
    viz = _viz()
    spike = [0.0] * 16
    spike[8] = 1.0
    viz._frames = [spike] * 400
    viz.start()
    viz.set_playing(True)

    out = []
    for frame in range(200):
        viz.set_position(frame / 30.0)
        out.append(viz.get_bars())

    settled = out[-1]
    assert settled[8] > 0.6, "peak was smeared away"
    assert settled[8] - settled[0] > 0.5, "spectrum flattened out"


def test_envelope_attack_is_fast() -> None:
    """A transient should reach most of its height within ~100 ms."""
    viz = _viz()
    loud = [1.0] * 16
    viz._frames = [loud] * 100
    viz.start()
    viz.set_playing(True)

    for frame in range(3):  # 3 frames at 30 fps = 100 ms
        viz.set_position(frame / 30.0)
        bars = viz.get_bars()

    assert min(bars) > 0.7


def test_envelope_constants_track_framerate() -> None:
    """Attack and release are times, not per-frame constants."""
    slow, fast = _viz(fps=15), _viz(fps=60)
    assert slow._rise > fast._rise
    assert slow._fall > fast._fall


def test_cache_name_covers_format() -> None:
    """Frames are only valid for the bars/fps/normalization they came from."""
    a = _viz(bars=16, fps=30)._cache_name("vid")
    b = _viz(bars=32, fps=30)._cache_name("vid")
    c = _viz(bars=16, fps=60)._cache_name("vid")
    assert a != b != c and a != c
    assert a.endswith(f"_v{AnalyzedVisualizer.CACHE_VERSION}.npy")


def test_position_extrapolation_is_capped() -> None:
    """A stalled position update must not run the frame index away."""
    viz = _viz()
    viz.set_playing(True)
    viz.set_position(10.0)
    viz._position_ts -= 60.0  # pretend the last update was a minute ago

    assert viz._effective_position() <= 10.0 + viz.MAX_EXTRAPOLATION


def test_sensitivity_scales_bars() -> None:
    viz_low, viz_high = _viz(sensitivity=50), _viz(sensitivity=150)
    raw = np.full((100, 16), 0.02, dtype=np.float32)

    assert np.asarray(viz_low._normalize(raw)).mean() < np.asarray(
        viz_high._normalize(raw)
    ).mean()
