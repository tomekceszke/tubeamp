# TubeAmp

A retro-styled terminal music player that streams audio from YouTube. Think Winamp meets the terminal.

```
┌──────────────────────────────────────────┐
│  ▁▃▅▇▆▄▂▁▃▅▇█▇▅▃▁▂▄▆▇▅▃▁▂▄▆▇▅▃▁▂▄▆█▇▅ │
│  ▁▃▅▇█▇▅▃▁▂▄▆▇▅▃▁▂▄▆█▇▅▃▁▂▄▆▇▅▃▁▃▅▇▆▄ │
├──────────────────────────────────────────┤
│  Daft Punk - Around the World            │
│  ───────────────●──────── 2:34 / 7:09    │
├──────────────────────────────────────────┤
│  ■  ▶  ⏸   S  R    VOL: ████████░░ 80%  │
├──────────────────────────────────────────┤
│  ▶ 1. Around the World          7:09     │
│    2. Da Funk                    5:28     │
│    3. Revolution 909             5:26     │
└──────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/tomekceszke/tubeamp.git
cd tubeamp
./install.sh
./run.sh
```

## Features

- Stream audio directly from YouTube (via yt-dlp + mpv)
- Real-time spectrum visualizer (offline FFT analysis, synced to playback)
- YouTube playlist import, search, and lazy-loading queue
- Full keyboard-driven TUI (via Textual)
- 6 color themes: Classic, Amber, Monochrome, Cyberpunk, Synthwave, Retro
- Shuffle, repeat (off/all/one), and volume controls
- Configurable via TOML (`~/.config/tubeamp/config.toml`)

## System Requirements

- **Python 3.11+**
- **libmpv** — Audio playback engine, loaded through ctypes (required)
- **ffmpeg** — Audio decoding for the spectrum visualizer (required)

`yt-dlp` is a Python dependency and is installed into the virtualenv, so it does not
need to be installed system-wide. TubeAmp puts the virtualenv's `bin` directory on
`PATH` at startup so mpv's `ytdl_hook` finds that copy rather than an older
distribution package.

### Installing Dependencies

```bash
# macOS — the mpv formula ships libmpv
brew install mpv ffmpeg

# Arch Linux — the mpv package ships libmpv
sudo pacman -S mpv ffmpeg

# Ubuntu/Debian — the mpv package does NOT pull the shared library in,
# and ensurepip lives in a separate package
sudo apt install mpv libmpv2 ffmpeg python3-venv

# Fedora
sudo dnf install mpv mpv-libs ffmpeg
```

Without the libmpv runtime package, startup fails with
`OSError: Cannot find libmpv in the usual places`. `./install.sh` handles all of this
and verifies the result before finishing.

## Installation

```bash
# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or use the installer script which handles everything:

```bash
./install.sh
```

## Usage

```bash
# Launch the player
tubeamp

# Or use the launcher script
./run.sh
```

Once running, press `/` to search YouTube or paste a playlist URL.

## Keybindings

| Key           | Action                |
|---------------|-----------------------|
| `Space`       | Play / Pause          |
| `x`           | Stop                  |
| `Up` / `Down` | Navigate playlist     |
| `j` / `k`     | Navigate playlist     |
| `Enter`       | Play selected track   |
| `Left` / `Right` | Seek -/+ 10s      |
| `-` / `+`     | Volume down / up      |
| `,` / `.`     | Previous / next track |
| `s`           | Toggle shuffle        |
| `r`           | Cycle repeat mode     |
| `t`           | Theme picker          |
| `/`           | Search YouTube        |
| `[` / `]`     | Decrease / increase bars |
| `Page Up/Down`| Scroll playlist page  |
| `Home` / `End`| Jump to first/last    |
| `F12`         | Save screenshot (SVG) |
| `h`           | Show help             |
| `q`           | Quit                  |

## Configuration

Global config at `~/.config/tubeamp/config.toml` (auto-created):

```toml
[audio]
volume = 80
quality = "bestaudio"

[visualizer]
backend = "analyzed"        # "analyzed" (FFT) or "simulated"
bars = 16
framerate = 30
sensitivity = 100           # percent gain on bar height

[youtube]
cookies_browser = ""        # "firefox", "chrome", etc.
default_playlist = ""       # auto-load on startup

[ui]
theme = "classic"
```

Local overrides in `local.toml` (not committed, see `local.toml.example`).

Logging goes to `~/.config/tubeamp/tubeamp.log` at INFO level; set
`TUBEAMP_LOG_LEVEL=DEBUG` for per-frame detail.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install the pre-commit hooks
pre-commit install

# Lint, type-check, test
ruff check src/ tests/
mypy src/ tests/
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

MIT
