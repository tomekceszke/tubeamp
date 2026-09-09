# Changelog

All notable changes to TubeAmp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Six colour themes (Classic, Amber, Monochrome, Cyberpunk, Synthwave, Retro)
  applied across every widget, including toasts and scrollbars
- Configuration in TOML at `~/.config/tubeamp/config.toml`, with optional local
  overrides in `local.toml`. `TUBEAMP_LOG_LEVEL` controls log verbosity
- `install.sh` installs the system dependencies for macOS, Debian/Ubuntu, Arch
  and Fedora, then verifies that libmpv, ffmpeg and the package all load before
  reporting success
- `run.sh` rebuilds the virtualenv automatically if a Python upgrade has left
  its interpreter symlinks dangling

### Known limitations

- The audio output device is fixed to the system default; `Player` accepts a
  device name but nothing exposes it in the configuration
- No test coverage for the application layer, the mpv wrapper, or the YouTube
  service beyond its data model

[Unreleased]: https://github.com/tomekceszke/tubeamp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tomekceszke/tubeamp/releases/tag/v0.1.0
