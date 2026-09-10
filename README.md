# TubeAmp

A retro-styled terminal music player that streams audio from YouTube. Think Winamp meets the terminal.

```bash
curl -fsSL https://raw.githubusercontent.com/tomekceszke/tubeamp/main/install.sh | bash
```

macOS and Linux. Installs mpv, ffmpeg and TubeAmp itself, showing every command that
needs `sudo` and asking before it runs. Then type `tubeamp`.

Rather read it before you run it? Sensible:

```bash
curl -fsSL https://raw.githubusercontent.com/tomekceszke/tubeamp/main/install.sh -o install.sh
less install.sh && bash install.sh
```

Windows needs WSL2 first — see [Installation](#installation). Prefer to do it by hand,
or already have Homebrew or uv? [Quick Start](#quick-start) has the manual steps.

![TubeAmp playing a track: the spectrum analyser, the transport controls and the queue](https://raw.githubusercontent.com/tomekceszke/tubeamp/main/docs/player.png)

## Quick Start

The one-liner at the top does all of this for you. By hand, if you would rather:

```bash
# macOS — the formula pulls in mpv and ffmpeg for you
brew install tomekceszke/tap/tubeamp
tubeamp

# Linux — system libraries, a tool installer, then TubeAmp
sudo apt install mpv libmpv2 ffmpeg          # Debian/Ubuntu; see below for others
uv tool install tubeamp                      # or: pipx install tubeamp
tubeamp
```

Windows needs WSL2 first; see [Installation](#installation).

## Features

- Stream audio directly from YouTube (via yt-dlp + mpv)
- Real-time spectrum visualizer (offline FFT analysis, synced to playback)
- YouTube playlist import, search, and lazy-loading queue
- Full keyboard-driven TUI (via Textual)
- 10 dark themes, from CRT phosphor to editor classics (see below)
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

Without the libmpv runtime package TubeAmp refuses to start and names the package to
install for your system. `./install.sh` handles all of this and verifies the result
before finishing.

## Installation

Nothing here is a binary you have to trust on faith. Every release is built from a
tagged commit by a GitHub Actions workflow and published to PyPI through Trusted
Publishing, so PyPI shows a **Verified provenance** marker linking each file back
to the commit and the workflow run that produced it.

### The install script

The one-liner at the top of this page runs [`install.sh`](install.sh), which is short
enough to read in a minute and does exactly four things: finds a Python 3.11+, installs
libmpv and ffmpeg through your own package manager, puts TubeAmp in its own virtualenv
under `~/.local/share/tubeamp`, and links it into `~/.local/bin`.

It shows every command before running it and asks first — including the ones needing
`sudo`, and before it touches your shell's startup file. It never installs Homebrew for
you; on macOS without it, it stops and points you at [brew.sh](https://brew.sh).

```bash
bash install.sh --dry-run     # print the whole plan, change nothing
bash install.sh --yes         # no questions, for scripts and the impatient
bash install.sh --uninstall   # remove it again, leaving ~/.config/tubeamp alone
```

Re-running it upgrades an existing install. The sections below are the same work done
by hand, if you would rather not run someone else's script at all.

### macOS

```bash
brew install tomekceszke/tap/tubeamp
```

The formula declares mpv and ffmpeg, so the system dependencies come along with it.
No Homebrew? Install it from [brew.sh](https://brew.sh) first, or follow the Linux
steps below, which work on macOS too.
If playback stops working after a while, YouTube has most likely moved on from the
pinned yt-dlp; `brew upgrade tubeamp` is the fix.

### Linux, and macOS without Homebrew

First libmpv and ffmpeg from your package manager (see *Installing Dependencies*
above). Then an installer for Python command-line tools, if you do not already have
one — either works, and both keep TubeAmp in its own environment rather than mixed
into your system Python:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv, read it first if you like
# or, from your package manager:
sudo apt install pipx
```

Then TubeAmp itself:

```bash
uv tool install tubeamp     # or: pipx install tubeamp
tubeamp
```

**If `tubeamp` comes back as "command not found"**, the install directory is not on
your `PATH` yet. Both tools install into `~/.local/bin`; `uv tool update-shell` (or
`pipx ensurepath`) adds it, and the change takes effect in a *new* terminal.

Upgrade with `uv tool upgrade tubeamp` — worth doing when a video refuses to play,
since that is usually a stale yt-dlp.

### Windows

Not supported natively: python-mpv loads `libmpv-2.dll` through ctypes, and the
official mpv build for Windows does not ship that library. TubeAmp runs under WSL2
instead, where the Linux instructions apply unchanged and WSLg handles audio — but
be aware that setting WSL2 up is its own detour, and it needs a reboot:

```powershell
wsl --install          # in PowerShell as administrator, then reboot
```

After the reboot, in the Ubuntu shell:

```bash
curl -fsSL https://raw.githubusercontent.com/tomekceszke/tubeamp/main/install.sh | bash
tubeamp
```

### From source

```bash
git clone https://github.com/tomekceszke/tubeamp.git
cd tubeamp
./install.sh
./run.sh
```

It is the same `install.sh`, and it notices the difference: run from a checkout it
installs the working tree in editable mode into `.venv` instead of fetching a release,
so your edits take effect without reinstalling. `run.sh` rebuilds that virtualenv if a
Python upgrade has left its interpreter symlinks dangling.

## First Run

TubeAmp starts with an empty playlist and lists what to press:

- `/` — search YouTube by artist or song, or paste a playlist or video URL
- `h` — every keybinding
- `t` — theme picker

To load a playlist automatically on startup, set `youtube.default_playlist` in
`~/.config/tubeamp/config.toml`.

## Usage

```bash
tubeamp             # launch the player
tubeamp --version   # report the version without starting the TUI
tubeamp --help      # usage, config path, log path

./run.sh            # from a source checkout
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

Working from a source checkout, a `local.toml` beside `pyproject.toml` overrides the
global file — handy for a personal default playlist you do not want committed (it is
in `.gitignore`). It is deliberately ignored anywhere else, so an installed `tubeamp`
never picks up a stray `local.toml` from whatever directory you happen to be in.
See `local.toml.example`.

### Themes

Press `t` to open the picker; each row shows the palette and the player behind
the dialog repaints as you move the highlight, so a theme is judged on the real
UI. `Esc` puts the original back.

| Key | Theme | |
|---|---|---|
| `classic` | Classic | green phosphor terminal |
| `monochrome` | Monochrome | plain white on black |
| `amber` | Amber | amber CRT |
| `commander` | Commander | Midnight Commander blue |
| `cyberpunk` | Cyberpunk | acid yellow, cyan and red |
| `synthwave` | Synthwave | purple, hot pink and sunset yellow |
| `htop` | htop | green meters, cyan header, blue-green-red spectrum |
| `gruvbox` | Gruvbox Dark | |
| `ayu` | Ayu Dark | electric blue on near-black |
| `dracula` | Dracula | |

Every colour on screen comes from the theme, so a palette also sets the
background, the frame and the spectrum gradient. A config naming a dropped
theme still works: `retro` resolves to `amber`, `monokai` to `dracula`, and
`solarized-dark` (like `nord`) to `ayu`.

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

## Disclaimer

TubeAmp is an independent project, not affiliated with, endorsed by or sponsored
by YouTube, Google, Winamp or Llama Group. Winamp is referenced only to describe
the kind of interface this takes after.

Streams are resolved with [yt-dlp](https://github.com/yt-dlp/yt-dlp). Playing
YouTube content outside the official clients may conflict with YouTube's Terms
of Service — check what applies where you are, and use it for content you are
entitled to access.

## License

MIT
