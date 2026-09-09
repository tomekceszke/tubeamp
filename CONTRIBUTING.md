# Contributing to TubeAmp

Thanks for taking a look. This is a small project, so the process is short.

## Getting set up

```bash
git clone https://github.com/tomekceszke/tubeamp.git
cd tubeamp
./install.sh          # system dependencies + virtualenv
pre-commit install
```

`install.sh` verifies that libmpv, ffmpeg and the package itself load before it
reports success, so if it finishes cleanly the environment is usable.

## Before opening a pull request

```bash
ruff check src/ tests/
mypy src/ tests/
pytest
```

All three are expected to pass with no output. CI runs the same commands.

Where a change affects what the interface looks like or how playback behaves,
run the app as well — the test suite covers the pure logic, not the rendering.

## What the tests do and do not cover

The suite exercises the parts that are worth pinning down: the visualizer's
level mapping and envelope, the control layout at every terminal width, the
marquee geometry, and the configuration defaults. The application layer, the
mpv wrapper and the YouTube service are not covered, so changes there need
manual verification.

If you fix a bug in one of the covered areas, please add a test that fails
without the fix.

## Style

- Match the surrounding code; `ruff` settles the mechanical questions
- Comments should say why, not restate what the line does
- Commit messages: a short imperative summary, then a body explaining the
  reasoning if it is not obvious from the diff

## Reporting bugs

Include your OS, the version from `pip show tubeamp`, and the relevant part
of `~/.config/tubeamp/tubeamp.log`. Re-run with
`TUBEAMP_LOG_LEVEL=DEBUG` if the log at INFO says nothing useful.
