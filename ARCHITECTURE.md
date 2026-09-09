# Architecture

## Overview

TubeAmp is a terminal-based music player that streams audio from YouTube with a retro-styled
visualizer. It follows a layered architecture with clear separation of concerns.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Textual TUI Layer                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Spectrum  │ │TrackInfo │ │ Controls │ │ Playlist  │  │
│  │ Widget    │ │ Widget   │ │ Widget   │ │ Widget    │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       │             │            │              │        │
├───────┼─────────────┼────────────┼──────────────┼────────┤
│       │        Application Core (app.py)        │        │
│       │    ┌────────────────────────────┐       │        │
│       │    │    Event Bus / Reactivity  │       │        │
│       │    └────────────────────────────┘       │        │
├───────┼─────────────────────────────────────────┼────────┤
│  Service Layer                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  player.py   │  │  youtube.py  │  │ visualizer.py │  │
│  │  (mpv wrap)  │  │  (yt-dlp)   │  │ (FFT analysis)│  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
├─────────┼─────────────────┼───────────────────┼──────────┤
│  External Dependencies                                   │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌───────┴───────┐  │
│  │   libmpv     │  │   yt-dlp     │  │   ffmpeg      │  │
│  │   (C lib)    │  │   (Python)   │  │   (binary)    │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Player (`player.py`)

Wraps `python-mpv` to handle audio playback. Responsible for:

- Loading and playing audio streams (URLs resolved by yt-dlp)
- Playback controls: play, pause, stop, seek, next, previous
- Volume management
- Emitting playback events (track changed, position update, state change)
- Audio output device selection (`Player(audio_device=...)`; not exposed in config yet)

**Key design decision:** mpv natively supports yt-dlp integration via `ytdl_hook`.
We pass YouTube URLs directly to mpv which invokes yt-dlp internally. This avoids
managing a separate download/stream pipeline.

### 2. YouTube Service (`youtube.py`)

Wraps `yt-dlp` for metadata operations:

- Search YouTube (`ytsearch:` prefix)
- Resolve playlist contents (title, duration, thumbnail URL per track)
- Extract user playlists (authenticated via browser cookies)
- Provide metadata without downloading (extract_info with download=False)

**Authentication:** Uses `--cookies-from-browser` to leverage the user's YouTube
Premium subscription for higher quality audio and playlist access.

### 3. Visualizer (`visualizer.py`)

Bridges audio output to the spectrum display:

Two backends, selected by `[visualizer] backend` in config:

**`analyzed` (default) — offline FFT, replayed in sync:**
- On track start, resolves the audio stream URL via yt-dlp and decodes it with ffmpeg
- Runs windowed FFT (`FFT_SIZE = 2048`, `SAMPLE_RATE = 22050`) into one bar frame per
  visualizer frame, then caches the result as
  `~/.config/tubeamp/viz_cache/{video_id}_{bars}b_{fps}fps_v{N}.npy` — bar count, frame
  rate and normalization format all change the data, so all three are in the key
- Bars are mapped in **dB**, not linear magnitude: band levels are tilted ~3 dB/octave
  (pink), referenced against a single 99th-percentile level for the whole track, and
  spread over `DYNAMIC_RANGE_DB` with `HEADROOM` left at the top. One shared reference
  keeps the natural spectral balance — bass stays taller than treble
- `SILENCE_FLOOR_DB` anchors the reference absolutely, so a silent track reads as empty
  bars rather than being stretched to full height
- An envelope follower drives the display: fast attack (`ATTACK_TAU`), slower release
  (`RELEASE_TAU`), both converted against the real frame interval so behaviour does not
  change with `framerate`
- Position from mpv arrives at ~19 Hz while bars render at `framerate`, so it is
  extrapolated with a monotonic clock (capped by `MAX_EXTRAPOLATION`) to avoid stepping
- Analysis runs on a daemon thread and is far faster than real time (a 3:46 track takes
  about 2 s); the simulated backend covers the gap until it lands

**`simulated` — animated placeholder bars, no audio analysis.**

No audio routing, loopback device, or extra system setup is required — the visualizer
never touches the playback output.

**Analysis Pipeline:**
```
yt-dlp (stream URL) → ffmpeg (PCM) → FFT → cached frames → position lookup → widget
```

### 4. TUI Widgets

All widgets are Textual `Widget` subclasses using Textual CSS for styling.

- **ControlsWidget** — Playback buttons. The layout is resolved from the current content
  width by `_resolve_layout()`: the boxed row needs 45 columns, so gaps tighten as the
  player narrows and the boxes give way to `[■]` brackets and then bare glyphs. Nothing
  is allowed to overflow — the widget is a fixed three rows tall, and a wrapped row
  pushes the bottom border out of it. Click regions come from the same layout object.

- **SpectrumWidget** — Renders bar visualizer using Unicode block characters (▁▂▃▄▅▆▇█).
  Updates at ~30fps via a timer. Receives bar data from the visualizer service.

- **TrackInfoWidget** — Displays current track title, artist, duration, and a seek bar.
  Reacts to player events.

- **ControlsWidget** — Playback buttons (prev/play-pause/next), shuffle, repeat, volume.
  Sends commands to the player service.

- **PlaylistWidget** — Scrollable list of tracks. Supports selection, reordering,
  and loading from YouTube playlists/search results.

### 5. Application (`app.py`)

The Textual `App` subclass that:
- Composes all widgets into the layout
- Manages keybindings (global shortcuts)
- Coordinates between services (player, youtube, visualizer)
- Handles application lifecycle

## Data Flow

```
User Input (keyboard) → App → Player/YouTube Service
                                    │
YouTube URL → yt-dlp (resolve) → mpv (play audio)
                                    │
                        Audio Output → Visualizer → SpectrumWidget
                        Metadata     → TrackInfoWidget
                        State        → ControlsWidget
```

## Configuration (`config.py`)

TOML-based configuration stored at `~/.config/tubeamp/config.toml`:

```toml
[audio]
volume = 80
quality = "bestaudio"

[visualizer]
bars = 40
framerate = 30
sensitivity = 100

[youtube]
cookies_browser = "firefox"  # or chrome, brave, etc.
default_playlist = ""        # auto-load on startup

[ui]
theme = "classic"  # classic, amber, monochrome, cyberpunk, synthwave, retro
```

## Future Considerations

- **Offline cache:** Download tracks for offline playback
- **Scrobbling:** Last.fm / ListenBrainz integration
- **Equalizer:** Per-band EQ via mpv's af filters
- **Remote control:** Unix socket for external control
- **Album art:** Render album art as ASCII/sixel in compatible terminals
