# Changelog

All notable changes to TubeAmp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffold
- Project architecture and documentation
- Textual-based TUI application skeleton
- mpv player wrapper with playback controls
- yt-dlp YouTube service (search, playlist extraction)
- Offline FFT spectrum visualizer (ffmpeg decode + NumPy analysis, cached per video) with simulated fallback
- Spectrum, TrackInfo, Controls, Playlist, and Volume widgets
- Keyboard shortcut system
- Retro-styled Textual CSS theme
- 6 built-in color themes (Classic, Amber, Monochrome, Cyberpunk, Synthwave, Retro)
- Theme picker modal
- Lazy-loading playlist support
- `install.sh` portable installer script
- `run.sh` and `install.sh` rebuild the venv automatically when a Python upgrade leaves its
  interpreter symlinks dangling

### Changed
- Visualizer bars are mapped in dB against a single per-track reference level instead of
  a per-band 95th percentile, which had stretched every band to full height on its own —
  quiet treble bands rendered taller than the bass driving the track, and 39% of frames
  sat above 80% height (now ~5%)
- Removed the second compression stage in `_spectrum_to_bands()`; log compression there
  plus percentile normalization afterwards stacked two curves on the same data
- Neighbour blending is applied to the returned bar copy only. It used to be written back
  into the envelope state, re-blurring an already blurred spectrum on every frame, which
  flattened in-frame contrast from 0.51 to 0.17
- Envelope attack/release are time constants converted against the real frame interval,
  so response no longer changes with `[visualizer] framerate`; measured display lag on a
  real track dropped from 100 ms to 33 ms
- Playback position is extrapolated with a monotonic clock between mpv's ~19 Hz updates,
  so bars no longer step behind the music at 30 fps
- `[visualizer] sensitivity` is applied instead of being accepted and ignored
- Visualizer cache key now includes frame rate and a format version; stale files for the
  same video are pruned on re-analysis
- Consolidated `_apply_theme()` — replaced 7 individual try/except blocks with `_query_widget` helper
- Extracted `_update_volume()` helper to deduplicate volume up/down logic
- Extracted magic numbers to named constants (`SEEK_THROTTLE_INTERVAL`, `LAZY_LOAD_THRESHOLD`, `SPECTRUM_ROWS`, `FIXED_COLUMN_WIDTH`)
- Consolidated player shutdown logging into single `logger.info("Shutting down mpv")`
- Reduced YouTube search logging from 6 statements to 2 per operation
- Fixed all f-string logger calls to use %-style formatting (lazy evaluation)
- Updated README with Quick Start section, complete keybindings, and system requirements
- Updated ARCHITECTURE.md, README.md and CLAUDE.md to reflect the offline FFT visualizer

### Fixed
- Playback and spectrum analysis no longer depend on a system-wide `yt-dlp`. The
  visualizer spawns `yt-dlp` by name and mpv's `ytdl_hook` looks it up on `PATH`, but
  launching the console script does not activate the virtualenv, so its copy was
  invisible. Startup now prepends the interpreter's `bin` directory to `PATH`.
  Verified on Ubuntu 26.04, where the apt copy (2026.03.17) fails with `HTTP Error 403`
  while the pinned one (2026.08.19) works
- `install.sh` installs the libmpv runtime package on Linux. Ubuntu's `mpv` package does
  not depend on it, so `import mpv` failed with "Cannot find libmpv in the usual places"
  even with mpv installed
- `install.sh` installs `python3.X-venv` when `ensurepip` is missing. `import venv`
  succeeds on Debian/Ubuntu without it, but `python3 -m venv` then fails
- `install.sh` no longer pipes `pip install yt-dlp` into `/dev/null` with `|| true`,
  which silently swallowed the PEP 668 `externally-managed-environment` error on
  Debian 12+ and reported a successful install with no yt-dlp present
- `install.sh` verifies libmpv, ffmpeg and the package import before reporting success
- Control button borders no longer wrap when the player is narrower than the 45-column
  button row. Rich wrapped each row onto the next line, which pushed the middle row down
  and dropped the bottom border out of the three-row widget. Gaps now tighten first, then
  the layout falls back to bracketed glyphs and finally bare glyphs
- Control buttons are centred correctly — `_buttons_left_pad()` subtracted the widget
  padding a second time, but `Widget.size` already excludes it
- Click regions are derived from the same layout that draws the buttons, so they cannot
  drift apart; verified against every button at eight widths
- `mypy` runs again: `python_version = "3.11"` made it parse numpy 2.x's PEP 695 stubs as
  3.11 syntax and abort the whole check. numpy stubs are no longer followed

### Removed
- `--dev` / `-d` CLI flag and all dev mode code (~80 lines)
- `--offline-test` / `-o` CLI flag and all offline test mode code (~120 lines)
- `mock_data.py` module (only used by dev mode)
- Unused imports: `Worker`, `get_current_worker`, `Theme`, `check_multi_output_device`, `Horizontal` (search.py), `ComposeResult` (volume.py, track_info.py), `Static` (track_info.py)
- Unused `ControlsWidget` Message subclasses (`PlayPause`, `NextTrack`, `PrevTrack`, `ShuffleToggle`, `RepeatToggle`, `VolumeChange`)
- Unused `color_scheme` fields from `UIConfig` and `VisualizerConfig`
- Redundant per-widget debug logs in `_apply_theme()`
- Noisy frame debug logs in the visualizer
- ~30 temporary development scripts, docs, and screenshot files from root directory
- cava backend and all references to it — the visualizer analyses the audio offline, so no
  loopback capture is needed
- BlackHole / Multi-Output Device setup requirement (macOS) and its startup warning
