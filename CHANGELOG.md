# Changelog

All notable changes to TubeAmp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.5] - 2026-09-10

### Added

- `Esc` quits from the main screen, alongside `q`. Inside the search and theme
  dialogs it still only closes the dialog, because a screen's own binding takes
  precedence over the app's

### Changed

- The pause button shows `Ⅱ` (U+2161) instead of `‖` (U+2016), which drew as a
  tall thin double rule in most terminal fonts and did not read as pause. It is
  one column wide, so the boxed layout and the click regions are unchanged. The
  README screenshot is re-captured

### Fixed

- `h` crashed the app with `MarkupError: auto closing tag ('[/]') has nothing to
  close`. The help toast lists `[` and `]` as the bar-count keys, and Textual reads
  a toast as markup, so `[/]` was a closing tag with nothing to close
- Error toasts for a failed search or a failed playlist page carry the yt-dlp
  message verbatim. yt-dlp prefixes its errors with the extractor in brackets
  (`[youtube]`), which the markup parser silently swallowed, and a stray closing
  tag in one would have crashed the app the same way `h` did

## [0.1.4] - 2026-09-10

### Changed

- The Homebrew tap is `tomekceszke/homebrew-tap`, not `homebrew-tubeamp`. Homebrew
  addresses a formula as `<user>/<tap>/<formula>`, so the old name made it
  `tomekceszke/tubeamp/tubeamp`, saying the project twice. It now reads
  `brew install tomekceszke/tap/tubeamp`
- The README opens with what a first-time reader needs and nothing else: one line
  of description, the install command, and a screenshot of the player. Features
  follow, then a Quick Start that is two commands per platform. The detail that
  used to sit between them — other distributions, WSL2, what the install script
  does, where releases come from, building from source — is folded into
  collapsible sections, which GitHub and PyPI both render

## [0.1.3] - 2026-09-10

### Fixed

- The Homebrew instructions named a tap that does not exist. The formula lives in
  `tomekceszke/homebrew-tubeamp`, so the command is
  `brew install tomekceszke/tubeamp/tubeamp` — the printed one would have failed
  for anyone who tried it

## [0.1.2] - 2026-09-10

### Changed

- The README leads with a real screenshot, `docs/player.png`, instead of a block
  of box characters. Text art lines up only while every glyph in it comes from
  one font: PyPI's stack substitutes for some of the blocks and rules, so the
  player's right edge came out wavy there even though GitHub rendered it
  cleanly. A picture renders identically on both, and carries the colour the
  code block never could. `scripts/capture_player_shot.py` produces it — Textual
  exports the screen as SVG, headless Chrome rasterises it

## [0.1.1] - 2026-09-10

### Fixed

- The pause button used U+23F8, which belongs to the emoji families but declares
  itself one column wide. Rich, Textual and every width calculation downstream
  believed the declaration while browsers and emoji-capable terminals drew it
  across two columns, so the README mock-up rendered crooked on GitHub and PyPI
  and `ControlsWidget` was one column out wherever a terminal reached for an
  emoji font. It is now U+2016, which measures the same everywhere
- The README mock-up is no longer drawn by hand. It is captured from the running
  player by `scripts/capture_player_art.py`, so it shows the spectrum the widget
  actually renders rather than an invented two-row wave, and its columns line up
  because nobody is counting them
- The architecture diagram was rebuilt: its rows ran between 57 and 60 columns,
  and the connectors between layers pointed at columns the stubs above them did
  not occupy

## [0.1.0] - 2026-09-10

First public release.

### Added

- Streams audio from YouTube through libmpv, which invokes yt-dlp internally, so
  there is no separate download or stream-extraction pipeline to manage
- Search YouTube, or load a playlist or single-video URL directly
- Playlists page in as you scroll towards the end, sized to the viewport
- Spectrum visualizer driven by offline FFT analysis: the track is decoded with
  ffmpeg, analysed with NumPy, cached per video, and replayed in sync with the
  playback position. No loopback device or audio routing is involved, and
  analysis runs far faster than real time — a 3:46 track takes about two seconds
- Keyboard-driven interface with shuffle, three repeat modes, seeking,
  volume control and an adjustable bar count
- Ten dark colour themes (Classic, Monochrome, Amber, Commander, Cyberpunk,
  Synthwave, htop, Ayu Dark, Gruvbox Dark, Dracula) applied across every widget,
  including toasts and scrollbars. `themes.py` is the only place a colour is
  written down, and a test fails the build if a widget grows one of its own
- An empty playlist shows what to press: `/` to search or paste a playlist URL,
  `h` for the full keybinding list, `t` for themes
- `tubeamp --version` and `tubeamp --help` answer without starting the TUI
- A missing libmpv is reported as one sentence naming the package to install for
  the platform in hand, instead of the import-time traceback python-mpv raises
- A missing ffmpeg is called out at startup, so the placeholder spectrum reads as
  a missing dependency rather than a broken visualizer
- Configuration in TOML at `~/.config/tubeamp/config.toml`. A `local.toml` in a
  source checkout overrides it, and is only read when a `pyproject.toml` sits
  beside it, so an installed copy never picks one up from the working directory.
  `TUBEAMP_LOG_LEVEL` controls log verbosity
- Published to PyPI from a tagged commit through Trusted Publishing, with PEP 740
  attestations, so every file traces back to the workflow run that built it
- `install.sh` works two ways from one file: piped from `curl` it installs the
  released package into `~/.local/share/tubeamp` and links it into `~/.local/bin`,
  while from a checkout it installs the working tree in editable mode. It installs
  the system dependencies for macOS, Debian/Ubuntu, Arch, Fedora and openSUSE,
  shows and confirms every command needing `sudo`, offers to put `~/.local/bin` on
  `PATH`, and verifies that libmpv, ffmpeg and the package all load before reporting
  success. `--dry-run`, `--yes` and `--uninstall` are supported
- `run.sh` rebuilds the virtualenv automatically if a Python upgrade has left
  its interpreter symlinks dangling

### Known limitations

- The audio output device is fixed to the system default; `Player` accepts a
  device name but nothing exposes it in the configuration
- Test coverage of the application layer stops at startup and the dependency
  warnings; the mpv wrapper and the YouTube service are covered only through
  their data models

[Unreleased]: https://github.com/tomekceszke/tubeamp/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/tomekceszke/tubeamp/releases/tag/v0.1.5
[0.1.4]: https://github.com/tomekceszke/tubeamp/releases/tag/v0.1.4
[0.1.3]: https://github.com/tomekceszke/tubeamp/releases/tag/v0.1.3
[0.1.2]: https://github.com/tomekceszke/tubeamp/releases/tag/v0.1.2
[0.1.1]: https://github.com/tomekceszke/tubeamp/releases/tag/v0.1.1
[0.1.0]: https://github.com/tomekceszke/tubeamp/releases/tag/v0.1.0
