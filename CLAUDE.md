# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TubeAmp is a retro-styled terminal music player that streams audio from YouTube. It uses:
- **Textual** for the TUI framework
- **python-mpv** (libmpv wrapper) for audio playback
- **yt-dlp** for YouTube metadata and URL resolution
- **ffmpeg** + NumPy FFT for offline audio spectrum analysis

## Development Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the application
tubeamp

# Run linting
ruff check src/

# Run type checking
mypy src/

# Run tests
pytest

# Run a single test file
pytest tests/test_basic.py

# Run tests with verbose output
pytest -v

# Run tests with asyncio debug mode
pytest --asyncio-mode=auto
```

## System Dependencies

The application requires external system tools:
- **libmpv** - Audio playback engine, loaded through ctypes (required)
- **ffmpeg** - Audio decoding for the spectrum visualizer (required)

`yt-dlp` is a Python dependency installed into the virtualenv, not a system tool.
`__main__.main()` prepends the interpreter's `bin` directory to `PATH` so the
visualizer subprocess and mpv's `ytdl_hook` both find that copy rather than an
older distribution package.

## Architecture

### Layered Design

The codebase follows a three-layer architecture:

1. **TUI Layer** (`src/tubeamp/widgets/`)
   - All widgets extend Textual's `Widget` class
   - `SpectrumWidget` - Renders spectrum bars using Unicode blocks
   - `TrackInfoWidget` - Shows current track and progress bar
   - `ControlsWidget` - Playback controls and volume
   - `PlaylistWidget` - Scrollable track list
   - `SearchScreen` - Modal for YouTube search

2. **Application Layer** (`src/tubeamp/app.py`)
   - `TubeAmpApp` - Main Textual application
   - Coordinates all services and widgets
   - Handles keybindings and global state
   - Thread-safe event handling via `_safe_call()`

3. **Service Layer**
   - `player.py` - mpv wrapper with event system
   - `youtube.py` - yt-dlp wrapper for search and metadata
   - `visualizer.py` - Offline FFT analysis, replayed in sync with playback
   - `config.py` - TOML configuration management
   - `playlist_session.py` - What is loaded and where the next page comes from
   - `theming.py` - Applies a theme across the mounted widget tree

### Key Integration Points

**mpv + yt-dlp integration:**
- YouTube URLs are passed directly to mpv
- mpv invokes yt-dlp internally via `ytdl_hook`
- No manual stream extraction needed

**Visualizer (no audio routing involved):**
- `analyzed` (default): yt-dlp resolves the stream URL, ffmpeg decodes it, NumPy runs a
  windowed FFT, and frames are cached to `~/.config/tubeamp/viz_cache/`
- During playback, bars are looked up by player position, not captured from the output
- `simulated`: animated placeholder bars; also covers the gap while analysis runs
- Backend selected via `[visualizer] backend` in config

**Visualizer level mapping — read before touching `_normalize()`:**
- Levels are in dB against **one** reference for the whole track. Normalizing per band
  (as an earlier version did) stretches every band to full height independently, which
  inverts the spectral balance and pins the bars to the ceiling
- Compression happens once. `_spectrum_to_bands()` returns raw magnitudes on purpose —
  compressing there as well stacks two curves and washes the dynamics out
- `_render()` blends neighbouring bars for the returned copy only. Writing the blur back
  into `self._display` re-blurs an already blurred spectrum every frame, and the bars
  collapse into a flat hump within about a second
- Envelope constants are **times** (`ATTACK_TAU`, `RELEASE_TAU`), converted per frame, so
  changing `framerate` does not change the feel
- `CACHE_VERSION` must be bumped whenever the analysis or normalization changes, or
  cached frames from the old format will be replayed

**Thread safety:**
- Player events fire from mpv's background thread
- Use `_safe_call()` to marshal updates to main thread
- Textual requires all UI updates on main thread

### Event Flow

```
User keyboard input → App action_*() methods
                          ↓
YouTube search → yt-dlp (executor) → tracks → PlaylistWidget
                          ↓
Track selection → Player.play(url) → mpv loads → events
                          ↓
mpv events → Player listeners → _safe_call → Widget updates
                          ↓
Position updates → cached FFT frames → SpectrumWidget timer
```

## Code Patterns

### Event System (player.py)

The Player class uses a custom event emitter:
```python
player.on("track_changed", callback)
player.on("position_changed", callback)
player.on("state_changed", callback)
player.on("track_ended", callback)
```

Callbacks fire from mpv's background thread and must be marshaled to main thread.

### Async Operations

Blocking operations (yt-dlp) run in executor:
```python
loop = asyncio.get_running_loop()
tracks = await loop.run_in_executor(None, blocking_function, args)
```

### Configuration

**Global config** stored at `~/.config/tubeamp/config.toml`:
- Auto-created with defaults if missing
- Loaded via `AppConfig.load()`
- Structured as dataclasses for type safety

**Local config** in `local.toml` (repo directory):
- Optional, in `.gitignore` (not committed)
- Overrides global config settings
- Used for personal settings like default playlists
- Example: `local.toml.example`

Configuration priority: `local.toml` > `~/.config/tubeamp/config.toml` > defaults

**Default playlist:**
- Set `youtube.default_playlist` to auto-load on startup
- Can be a YouTube playlist or single video URL
- Loaded asynchronously after app initialization

### Logging

Logs written to `~/.config/tubeamp/tubeamp.log`:
- TUI apps can't use stdout/stderr for logging
- File is overwritten on each run
- Use `logger.info/debug/exception` throughout

## Environment Notes

**Virtual environment:**
- Canonical venv is `.venv` at the repo root; `run.sh` rebuilds it automatically if the
  interpreter symlinks go dangling (a Homebrew Python upgrade does exactly that)
- `python3 -m venv` pins the venv to one interpreter path — never assume an existing
  venv still works, probe it with `.venv/bin/python -c ''`

## Common Tasks

**Adding a new keybinding:**
1. Add to `BINDINGS` in `TubeAmpApp`
2. Implement `action_<name>()` method
3. Update help text in `action_help()`

**Widgets with fixed-width art (ControlsWidget):**
- The widget has a fixed `height`, so any row wider than the content area wraps and
  silently eats a row of the drawing. Resolve a layout from `self.size.width` (which
  already excludes padding) rather than emitting a constant-width string
- Derive click regions from the same layout that renders, or the two drift apart
- Set `no_wrap` / `overflow = "crop"` on the returned `Text` as a backstop

**Adding a new widget:**
1. Create in `src/tubeamp/widgets/`
2. Import and yield in `TubeAmpApp.compose()`
3. Add styles in `src/tubeamp/styles/tubeamp.tcss`
4. Query widget in app: `self.query_one("#id", WidgetClass)` or use `self._query_widget("#id", WidgetClass)` which returns `None` instead of raising

**Modifying player behavior:**
- Player events: `_on_track_changed`, `_on_position_changed`, `_on_state_changed`, `_on_track_ended`
- Always use `_safe_call()` to update UI from player events
- mpv properties accessed via `self._player._mpv["property"]`

**Testing with different audio backends:**
- Set `audio_device` parameter in Player constructor
- Pass `--audio-device=help` to mpv CLI to list devices
- Not exposed in `config.toml` — `AudioConfig` has no `device` field, so the only way in
  is the `Player(audio_device=...)` argument
