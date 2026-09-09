"""Spectrum visualizer backends.

Backends:
  analyzed  — Default. Fetches audio via yt-dlp + ffmpeg, runs FFT analysis
              offline, and replays bar data synchronized to playback position.
              No audio routing or extra system setup required.

  simulated — Animated placeholder bars. No audio analysis.
"""

from __future__ import annotations

import contextlib
import logging
import math
import random
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Abstract base ───────────────────────────────────────────────

class BaseVisualizer(ABC):

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def get_bars(self) -> list[float]: ...

    @property
    @abstractmethod
    def num_bars(self) -> int: ...

    # Optional hooks — no-op by default, overridden by AnalyzedVisualizer

    def analyze_track(self, url: str, video_id: str) -> None:
        """Called when a new track starts playing. Override to pre-analyze audio."""

    def set_position(self, position: float) -> None:
        """Called on each position update. Override to sync bar data to playback."""

    def set_playing(self, is_playing: bool) -> None:
        """Called on playback state changes. Override to pause/resume visualization."""


# ── Analyzed visualizer ─────────────────────────────────────────

class AnalyzedVisualizer(BaseVisualizer):
    """Pre-analyzes audio tracks and replays bar data synchronized to position.

    When a track starts, fetches the audio stream URL via yt-dlp, decodes it
    with ffmpeg, runs windowed FFT analysis, and caches results per video ID.
    During playback, get_bars() returns the frame matching the current position.
    Falls back to SimulatedVisualizer while analysis is in progress.

    Cache location: ~/.config/tubeamp/viz_cache/{video_id}_{bars}bars.npy
    """

    SAMPLE_RATE = 22050  # Hz — good enough for visualization, fast to process
    FFT_SIZE = 2048      # frequency resolution; hop = SAMPLE_RATE // fps

    # Level mapping. Bars are driven in dB, not linear magnitude: a linear scale
    # spends almost its whole range on the loudest transients, which is why a
    # naive normalization pins every bar to the ceiling.
    DYNAMIC_RANGE_DB = 48.0   # dB below the track reference that maps to an empty bar
    REFERENCE_PCTL = 99.0     # percentile of all band levels taken as "loud"
    HEADROOM = 0.92           # reference level maps here, leaving room for peaks
    TILT_DB_PER_OCTAVE = 3.0  # pink-ish tilt so treble stays visible under bass
    SILENCE_FLOOR_DB = -90.0  # absolute dBFS floor; below this a bar reads empty

    # Envelope time constants, in seconds. Converted to per-frame coefficients
    # against the actual frame interval, so behaviour no longer changes with fps.
    ATTACK_TAU = 0.025
    RELEASE_TAU = 0.18

    # Position is refreshed by mpv at ~19 Hz while bars render at `fps`. Between
    # updates the position is extrapolated with a monotonic clock, capped so a
    # stall or a seek cannot run the index away from reality.
    MAX_EXTRAPOLATION = 0.25  # seconds

    CACHE_VERSION = 2  # bump when the analysis or normalization changes

    def __init__(
        self,
        bars: int = 40,
        fps: int = 20,
        sensitivity: int = 100,
        cookies_browser: str | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._bars = bars
        self._fps = fps
        self._gain = max(1, sensitivity) / 100.0
        self._cookies_browser = cookies_browser
        self._cache_dir = cache_dir or (Path.home() / ".config" / "tubeamp" / "viz_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Analysis hops by whole samples, so the true frame rate is not exactly
        # `fps`. Index by the real rate or long tracks drift out of sync.
        self._hop = max(1, self.SAMPLE_RATE // fps)
        self._frame_rate = self.SAMPLE_RATE / self._hop

        self._frames: list[list[float]] = []
        self._position: float = 0.0
        self._position_ts: float = time.monotonic()
        self._lock = threading.Lock()
        self._running = False
        self._is_playing = False
        self._current_video_id: str | None = None
        self._band_edges: list[int] | None = None
        self._simulated = SimulatedVisualizer(bars=bars)

        # Envelope follower state. Fast attack so transients land on the beat,
        # slower release so bars fall away musically instead of strobing.
        self._display: list[float] = [0.0] * bars
        dt = 1.0 / fps
        self._rise = 1.0 - math.exp(-dt / self.ATTACK_TAU)
        self._fall = 1.0 - math.exp(-dt / self.RELEASE_TAU)

    def start(self) -> None:
        self._running = True
        self._simulated.start()

    def stop(self) -> None:
        self._running = False
        self._current_video_id = None  # signals running analysis threads to exit
        self._simulated.stop()
        with self._lock:
            self._frames = []

    def analyze_track(self, url: str, video_id: str) -> None:
        """Start background analysis for a newly selected track."""
        self._current_video_id = video_id
        self._display = [0.0] * self._bars
        with self._lock:
            self._frames = []

        cache_path = self._cache_dir / self._cache_name(video_id)
        t = threading.Thread(
            target=self._load_or_analyze,
            args=(url, video_id, cache_path),
            daemon=True,
        )
        t.start()

    def set_position(self, position: float) -> None:
        self._position = position
        self._position_ts = time.monotonic()

    def _effective_position(self) -> float:
        """Position extrapolated to now.

        mpv reports `time-pos` at roughly 19 Hz while bars are rendered at
        `fps`, so using the raw value replays each analysis frame two or three
        times and the display visibly steps behind the music.
        """
        if not self._is_playing:
            return self._position
        drift = time.monotonic() - self._position_ts
        return self._position + min(max(drift, 0.0), self.MAX_EXTRAPOLATION)

    def set_playing(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self._simulated.set_playing(is_playing)

    def get_bars(self) -> list[float]:
        if not self._is_playing:
            # Decay smoothly to silence rather than snapping to zero
            self._display = [v * (1 - self._fall) for v in self._display]
            return self._render(self._display)

        target = self._target_bars()

        # Envelope follower: asymmetric attack/release
        d = self._display
        r, f = self._rise, self._fall
        self._display = [
            d[i] + (target[i] - d[i]) * (r if target[i] > d[i] else f)
            for i in range(self._bars)
        ]

        return self._render(self._display)

    def _target_bars(self) -> list[float]:
        """Bar values for the current position, or simulated ones if unavailable."""
        with self._lock:
            frames = self._frames

        if not frames:
            return self._simulated.get_bars()

        idx = int(self._effective_position() * self._frame_rate)
        if idx < 0 or idx >= len(frames):
            # Before the first frame, or past what has been analysed so far —
            # holding the last frame would freeze the display, so keep moving.
            return self._simulated.get_bars()
        return frames[idx]

    def _render(self, values: list[float]) -> list[float]:
        """Blend each bar with its neighbours for a flowing, connected curve.

        Applied to the returned copy only. Writing the blur back into
        `self._display` would re-blur an already blurred spectrum on every
        frame, and within about a second the bars collapse into a flat hump.
        """
        n = len(values)
        if n < 3:
            return list(values)
        return [
            values[i] * 0.7
            + (values[i - 1] if i > 0 else values[i]) * 0.15
            + (values[i + 1] if i < n - 1 else values[i]) * 0.15
            for i in range(n)
        ]

    @property
    def num_bars(self) -> int:
        return self._bars

    # ── Internal: cache + analysis ──────────────────────────────

    def _load_or_analyze(self, url: str, video_id: str, cache_path: Path) -> None:
        if cache_path.exists():
            try:
                import numpy as np
                arr = np.load(cache_path).astype(np.float32)
                if self._current_video_id == video_id:
                    with self._lock:
                        self._frames = arr.tolist()
                    logger.info("Loaded viz cache for %s (%d frames)", video_id, len(arr))
                return
            except Exception:
                logger.warning("Corrupted viz cache for %s, re-analyzing", video_id)
                with contextlib.suppress(OSError):
                    cache_path.unlink()

        self._prune_stale_cache(video_id)
        self._analyze(url, video_id, cache_path)

    def _cache_name(self, video_id: str) -> str:
        """Cache key. Frame data is only valid for the bar count, frame rate and
        normalization it was produced with, so all three belong in the name."""
        return f"{video_id}_{self._bars}b_{self._fps}fps_v{self.CACHE_VERSION}.npy"

    def _prune_stale_cache(self, video_id: str) -> None:
        """Drop cache files for this video that a previous format left behind."""
        keep = self._cache_name(video_id)
        for stale in self._cache_dir.glob(f"{video_id}_*.npy"):
            if stale.name != keep:
                with contextlib.suppress(OSError):
                    stale.unlink()

    def _get_band_edges(self) -> list[int]:
        if self._band_edges is None:
            self._band_edges = _compute_band_edges(
                self.SAMPLE_RATE, self.FFT_SIZE, self._bars,
            )
        return self._band_edges

    def _analyze(self, url: str, video_id: str, cache_path: Path) -> None:
        """Full analysis pipeline: yt-dlp | ffmpeg → FFT → normalize → cache.

        Pipes yt-dlp stdout directly into ffmpeg stdin so yt-dlp handles all
        YouTube-specific streaming (auth, DASH segments, etc.) transparently.
        """
        import numpy as np

        logger.info("Starting audio analysis for %s", video_id)

        ydl_cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--no-playlist",
            "-o", "-",   # stream to stdout
            url,
        ]
        if self._cookies_browser:
            ydl_cmd += ["--cookies-from-browser", self._cookies_browser]

        ffmpeg_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",
            "-f", "f32le", "-ac", "1", "-ar", str(self.SAMPLE_RATE),
            "pipe:1",
        ]

        ydl_proc: subprocess.Popen[bytes] | None = None
        ffmpeg_proc: subprocess.Popen[bytes] | None = None

        try:
            ydl_proc = subprocess.Popen(
                ydl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=ydl_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # Hand off ydl stdout ownership to ffmpeg; we read from ffmpeg only
            ydl_proc.stdout.close()  # type: ignore[union-attr]
        except Exception:
            logger.exception("Failed to start yt-dlp/ffmpeg pipeline for %s", video_id)
            return

        hop = self._hop
        window = np.hanning(self.FFT_SIZE)
        band_edges = self._get_band_edges()

        buffer = np.empty(0, dtype=np.float32)
        raw_frames: list[list[float]] = []
        bytes_per_hop = hop * 4  # float32 = 4 bytes each

        try:
            while self._current_video_id == video_id and self._running:
                raw = ffmpeg_proc.stdout.read(bytes_per_hop)  # type: ignore[union-attr]
                if not raw:
                    break

                samples = np.frombuffer(raw, dtype=np.float32)
                buffer = np.concatenate([buffer, samples])

                while len(buffer) >= self.FFT_SIZE and self._current_video_id == video_id:
                    frame_data = buffer[: self.FFT_SIZE] * window
                    buffer = buffer[hop:]

                    spectrum = np.abs(np.fft.rfft(frame_data)) / (self.FFT_SIZE / 2.0)
                    bands = _spectrum_to_bands(spectrum, band_edges, self._bars)
                    raw_frames.append(bands)

                    # Progressively expose frames (every ~1 s worth of audio).
                    # These carry raw magnitudes, so they need the same dB
                    # mapping as the final result or the bars stay flat.
                    if len(raw_frames) % self._fps == 0:
                        partial = self._normalize(
                            np.array(raw_frames, dtype=np.float32)
                        ).tolist()
                        with self._lock:
                            self._frames = partial

        finally:
            for proc in (ffmpeg_proc, ydl_proc):
                if proc is None:
                    continue
                with contextlib.suppress(Exception):
                    proc.terminate()
                with contextlib.suppress(Exception):
                    proc.wait(timeout=3)

            # Log any ffmpeg errors to help diagnose failures
            if ffmpeg_proc and ffmpeg_proc.stderr:
                stderr_out = ffmpeg_proc.stderr.read().decode("utf-8", errors="replace").strip()
                if stderr_out:
                    logger.warning("ffmpeg stderr for %s: %s", video_id, stderr_out)

        if not raw_frames:
            logger.warning("Analysis produced no frames for %s — pipeline likely failed", video_id)
            return

        if self._current_video_id != video_id:
            return  # track changed mid-analysis; discard

        arr = self._normalize(np.array(raw_frames, dtype=np.float32))

        with self._lock:
            self._frames = arr.tolist()

        logger.info("Analysis complete for %s: %d frames", video_id, len(raw_frames))

        # Cache as float16 to halve storage
        try:
            np.save(cache_path, arr.astype(np.float16))
            logger.info("Saved viz cache: %s", cache_path.name)
        except Exception:
            logger.warning("Failed to save viz cache for %s", video_id)


    def _normalize(self, arr: Any) -> Any:
        """Map raw band magnitudes onto 0.0-1.0 bar heights.

        Works in dB against a single reference level for the whole track. An
        earlier version normalized each band by its own 95th percentile, which
        stretched every band to full height independently — quiet treble bands
        ended up taller than the bass driving the track, and the bars sat
        permanently near the ceiling.
        """
        import numpy as np

        db = 20.0 * np.log10(np.maximum(arr, 1e-10))

        # Pink-ish tilt: music loses roughly 3 dB per octave going up, so lift
        # the upper bands by the same slope to keep them legible. Bands are
        # already log-spaced, so the tilt is linear across the band index.
        octaves = np.log2(
            np.maximum(np.arange(1, self._bars + 1, dtype=np.float32), 1.0)
        )
        db = db + octaves * self.TILT_DB_PER_OCTAVE

        # The reference is relative to the track, so a silent or near-silent
        # input would otherwise be stretched up to full-height bars. Anchor it
        # against an absolute floor as well. Real music references around
        # -16 dB and pure tones around -26 dB, both far above this clamp.
        reference = float(np.percentile(db, self.REFERENCE_PCTL))
        reference = max(reference, self.SILENCE_FLOOR_DB + self.DYNAMIC_RANGE_DB)
        floor = reference - self.DYNAMIC_RANGE_DB
        norm = (db - floor) / self.DYNAMIC_RANGE_DB * self.HEADROOM
        norm *= self._gain

        return np.clip(norm, 0.0, 1.0).astype(np.float32)


# ── FFT helpers ─────────────────────────────────────────────────

def _compute_band_edges(sample_rate: int, fft_size: int, num_bands: int) -> list[int]:
    """Compute FFT bin index boundaries for N log-spaced frequency bands.

    Bands are spaced logarithmically from ~50 Hz to ~10 kHz.
    """
    import numpy as np

    freq_min = 50.0
    freq_max = min(10_000.0, sample_rate / 2.0 * 0.95)
    freqs = np.logspace(np.log10(freq_min), np.log10(freq_max), num_bands + 1)
    bins = (freqs * fft_size / sample_rate).astype(int)
    bins = np.clip(bins, 0, fft_size // 2)
    return [int(b) for b in bins]


def _spectrum_to_bands(
    spectrum: Any,
    band_edges: list[int],
    num_bands: int,
) -> list[float]:
    """Average FFT magnitude bins into frequency bands.

    Returns raw linear magnitudes. Compression happens once, later, in
    `_normalize()` on the dB scale — compressing here as well used to stack two
    curves on top of each other and push every bar towards the ceiling.
    """
    bands: list[float] = []
    for i in range(num_bands):
        lo = band_edges[i]
        hi = band_edges[i + 1] if i + 1 < len(band_edges) else lo + 1
        hi = max(hi, lo + 1)
        hi = min(hi, len(spectrum))
        bands.append(float(spectrum[lo:hi].mean()) if hi > lo else 0.0)

    return bands


# ── Simulated visualizer ────────────────────────────────────────

class SimulatedVisualizer(BaseVisualizer):
    """Animated placeholder bars — no audio analysis.

    Used as the fallback inside AnalyzedVisualizer while analysis is running,
    or explicitly via config: [visualizer] backend = "simulated"
    """

    def __init__(self, bars: int = 40) -> None:
        self._bars = bars
        self._bar_data: list[float] = [0.0] * bars
        self._running = False
        self._is_playing = False
        self._tick = 0

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._bar_data = [0.0] * self._bars

    def set_playing(self, is_playing: bool) -> None:
        self._is_playing = is_playing

    def get_bars(self) -> list[float]:
        if not self._running or not self._is_playing:
            return [0.0] * self._bars
        self._tick += 1
        return [
            max(0.0, min(1.0,
                (0.3 * math.sin(self._tick * 0.05 + i * 0.3)
                 + 0.2 * math.sin(self._tick * 0.08 + i * 0.15)
                 + 0.15 * math.sin(self._tick * 0.12 + i * 0.5)
                 + 0.65) * 0.7 + random.uniform(0, 0.03)
            ))
            for i in range(self._bars)
        ]

    @property
    def num_bars(self) -> int:
        return self._bars


# ── Factory ─────────────────────────────────────────────────────

def create_visualizer(
    bars: int = 40,
    framerate: int = 30,
    sensitivity: int = 100,
    backend: str = "analyzed",
    cookies_browser: str | None = None,
) -> BaseVisualizer:
    """Create a visualizer for the requested backend.

    Backends:
      "analyzed"  — Default. FFT analysis + position-sync. No system setup needed.
      "simulated" — Pure animation, no audio.
    """
    if backend == "analyzed":
        logger.info("Using analyzed visualizer (fps=%d, bars=%d)", framerate, bars)
        return AnalyzedVisualizer(
            bars=bars,
            fps=framerate,
            sensitivity=sensitivity,
            cookies_browser=cookies_browser,
        )

    # "simulated" or unknown
    logger.info("Using simulated visualizer")
    return SimulatedVisualizer(bars=bars)
