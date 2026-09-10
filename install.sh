#!/usr/bin/env bash
# TubeAmp installer.
#
# Two ways in, one script:
#
#   curl -fsSL https://raw.githubusercontent.com/tomekceszke/tubeamp/main/install.sh | bash
#       Installs the released package from PyPI into its own environment under
#       ~/.local/share/tubeamp and links it into ~/.local/bin.
#
#   ./install.sh   (from a clone)
#       Installs the checkout in editable mode into .venv, for development.
#
# The mode is decided by whether a pyproject.toml sits next to the script, so a
# clone behaves the way it always has and a piped copy never touches it.
#
# Nothing is installed without saying so first: every package-manager command is
# printed and confirmed. Pass --yes to skip the prompts, --dry-run to see the
# whole plan without running any of it.

set -euo pipefail

APP_DIR="$HOME/.local/share/tubeamp"
BIN_DIR="$HOME/.local/bin"
BIN_LINK="$BIN_DIR/tubeamp"

# Overridable so a release candidate can be rehearsed before it is on PyPI
PIP_SPEC="${TUBEAMP_PIP_SPEC:-tubeamp}"

ASSUME_YES=0
DRY_RUN=0
ACTION=install
MODE=pypi
SOURCE_DIR=""

# ── Output ──────────────────────────────────────────────────────

say()  { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
TubeAmp installer

Usage:
  install.sh [--yes] [--dry-run]
  install.sh --uninstall
  install.sh --help

Options:
  --yes        Do not ask before installing system packages or editing PATH
  --dry-run    Print every command that would run, change nothing
  --uninstall  Remove the installed copy, leaving ~/.config/tubeamp alone
EOF
}

# Print a command, then run it — unless this is a rehearsal
run() {
    say "    \$ $*"
    [ "$DRY_RUN" -eq 1 ] && return 0
    "$@"
}

# Ask on the terminal, not on stdin: under `curl … | bash` stdin is the script
# itself, and a plain `read` would swallow the rest of it.
confirm() {
    [ "$ASSUME_YES" -eq 1 ] && return 0
    [ "$DRY_RUN" -eq 1 ] && return 0
    # `-r /dev/tty` is not enough: the device node exists in a detached process
    # but opening it fails, which would spill raw shell errors over the output
    if ! { : > /dev/tty; } 2>/dev/null; then
        warn "no terminal to ask on; re-run with --yes to accept this step"
        return 1
    fi
    printf '%s [y/N] ' "$1" > /dev/tty
    local reply
    read -r reply < /dev/tty
    case "$reply" in
        [yY] | [yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

# ── Mode ────────────────────────────────────────────────────────

detect_mode() {
    # ${BASH_SOURCE[0]} is not a readable file when the script arrives on a
    # pipe, so this deliberately proves the checkout rather than assuming it
    local self="${BASH_SOURCE[0]:-}"
    if [ -n "$self" ] && [ -f "$self" ]; then
        local dir
        dir="$(cd "$(dirname "$self")" && pwd)"
        if [ -f "$dir/pyproject.toml" ] && [ -d "$dir/src/tubeamp" ]; then
            MODE=source
            SOURCE_DIR="$dir"
        fi
    fi
}

# ── Python ──────────────────────────────────────────────────────

PYTHON=""

# macOS ships a python3 shim that only prompts for the Xcode tools, and distros
# vary in how far ahead of 3.11 they are, so pick a real interpreter by asking.
find_python() {
    local candidate
    for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
            >/dev/null 2>&1 || continue
        PYTHON="$candidate"
        return 0
    done
    return 1
}

check_python() {
    step "Checking Python"
    if ! find_python; then
        if [ "$(uname -s)" = "Darwin" ]; then
            die "Python 3.11+ not found. Install it with: brew install python@3.13"
        fi
        die "Python 3.11+ not found. Install your distribution's python3 package."
    fi
    say "    $PYTHON ($("$PYTHON" -c 'import platform; print(platform.python_version())'))"

    # Debian and Ubuntu ship ensurepip separately, and `python3 -m venv` fails
    # without it even though the venv module itself imports fine
    if ! "$PYTHON" -c 'import ensurepip' >/dev/null 2>&1; then
        local version
        version="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
        say "    ensurepip is missing, so virtual environments cannot be created"
        install_packages "python${version}-venv" || die "cannot continue without ensurepip"
    fi
}

# ── System dependencies ─────────────────────────────────────────

# python-mpv loads libmpv through ctypes rather than linking against it, so the
# only honest check is to ask ctypes whether it can find it.
has_libmpv() {
    [ -n "$PYTHON" ] || return 1
    "$PYTHON" - <<'PY' >/dev/null 2>&1
import ctypes.util
import sys

sys.exit(0 if ctypes.util.find_library("mpv") else 1)
PY
}

# Run the platform's package manager for the named packages, asking first
install_packages() {
    local packages="$*"
    case "$(uname -s)" in
        Darwin)
            command -v brew >/dev/null 2>&1 \
                || die "Homebrew not found. Install it from https://brew.sh, then run this again."
            say "    TubeAmp needs: $packages"
            confirm "Run 'brew install $packages'?" || return 1
            # shellcheck disable=SC2086
            run brew install $packages
            ;;
        Linux)
            local command_line=""
            if command -v apt-get >/dev/null 2>&1; then
                command_line="sudo apt-get install -y $packages"
            elif command -v dnf >/dev/null 2>&1; then
                command_line="sudo dnf install -y $packages"
            elif command -v pacman >/dev/null 2>&1; then
                command_line="sudo pacman -S --needed --noconfirm $packages"
            elif command -v zypper >/dev/null 2>&1; then
                command_line="sudo zypper install -y $packages"
            else
                warn "unknown package manager; install these yourself: $packages"
                return 1
            fi
            say "    TubeAmp needs: $packages"
            say "    This step needs administrator rights."
            confirm "Run '$command_line'?" || return 1
            if command -v apt-get >/dev/null 2>&1; then
                run sudo apt-get update -qq
            fi
            # shellcheck disable=SC2086
            run $command_line
            ;;
        *)
            die "unsupported system: $(uname -s). On Windows, run TubeAmp under WSL2."
            ;;
    esac
}

# Translate "libmpv and ffmpeg" into whatever this system calls them
missing_dependency_packages() {
    local packages=""
    case "$(uname -s)" in
        Darwin)
            # The mpv formula ships libmpv
            has_libmpv || packages="mpv"
            command -v ffmpeg >/dev/null 2>&1 || packages="$packages ffmpeg"
            ;;
        Linux)
            if ! has_libmpv; then
                if command -v apt-get >/dev/null 2>&1; then
                    # The mpv package does not pull the shared library in on
                    # Debian or Ubuntu, and the soname moved with mpv 0.36
                    local libmpv="libmpv2"
                    apt-cache show libmpv2 >/dev/null 2>&1 || libmpv="libmpv1"
                    packages="mpv $libmpv"
                elif command -v dnf >/dev/null 2>&1; then
                    packages="mpv mpv-libs"
                else
                    packages="mpv"
                fi
            fi
            command -v ffmpeg >/dev/null 2>&1 || packages="$packages ffmpeg"
            ;;
    esac
    # Collapse the leading space left when only ffmpeg is missing
    printf '%s' "${packages# }"
}

install_system_dependencies() {
    step "Checking system dependencies"
    local packages
    packages="$(missing_dependency_packages)"
    if [ -z "$packages" ]; then
        say "    libmpv and ffmpeg are already present"
        return 0
    fi
    install_packages "$packages" || warn "continuing without them; TubeAmp will say what is missing"
}

# ── Installing the package ──────────────────────────────────────

install_from_pypi() {
    step "Installing TubeAmp into $APP_DIR"

    # A venv pins itself to one interpreter path, and a Python upgrade leaves
    # that symlink dangling; rebuild rather than fail on a stale one
    if [ -d "$APP_DIR" ] && ! "$APP_DIR/bin/python" -c '' >/dev/null 2>&1; then
        say "    the existing environment is broken, rebuilding it"
        run rm -rf "$APP_DIR"
    fi
    if [ ! -d "$APP_DIR" ]; then
        run "$PYTHON" -m venv "$APP_DIR"
    else
        say "    reusing the existing environment"
    fi

    run "$APP_DIR/bin/python" -m pip install --quiet --upgrade pip
    run "$APP_DIR/bin/python" -m pip install --quiet --upgrade "$PIP_SPEC"

    run mkdir -p "$BIN_DIR"
    if [ -e "$BIN_LINK" ] && [ ! -L "$BIN_LINK" ]; then
        die "$BIN_LINK exists and is not a symlink; move it aside and run this again"
    fi
    run ln -sf "$APP_DIR/bin/tubeamp" "$BIN_LINK"
    say "    linked $BIN_LINK"
}

install_from_source() {
    step "Installing TubeAmp from $SOURCE_DIR in editable mode"
    local venv="$SOURCE_DIR/.venv"

    if [ -d "$venv" ] && ! "$venv/bin/python" -c '' >/dev/null 2>&1; then
        say "    the existing venv is broken, rebuilding it"
        run rm -rf "$venv"
    fi
    if [ ! -d "$venv" ]; then
        run "$PYTHON" -m venv "$venv"
    else
        say "    reusing $venv"
    fi
    run "$venv/bin/python" -m pip install --quiet --upgrade pip
    run "$venv/bin/python" -m pip install --quiet -e "$SOURCE_DIR"
}

# ── PATH ────────────────────────────────────────────────────────

# Which startup file this user's shell actually reads
shell_rc_file() {
    case "$(basename "${SHELL:-}")" in
        zsh)  printf '%s' "$HOME/.zshrc" ;;
        bash)
            # bash reads .bash_profile for login shells, which is what a macOS
            # terminal opens; on Linux the interactive .bashrc is the right file
            if [ "$(uname -s)" = "Darwin" ]; then
                printf '%s' "$HOME/.bash_profile"
            else
                printf '%s' "$HOME/.bashrc"
            fi
            ;;
        *) printf '' ;;
    esac
}

ensure_path() {
    case ":${PATH}:" in
        *":$BIN_DIR:"*) return 0 ;;
    esac

    step "$BIN_DIR is not on your PATH"
    local line="export PATH=\"\$HOME/.local/bin:\$PATH\""
    local rc
    rc="$(shell_rc_file)"

    if [ -z "$rc" ]; then
        say "    Add this to your shell's startup file:"
        say ""
        say "        $line"
        return 0
    fi

    # A second run with PATH not yet reloaded would otherwise append it again
    if [ -f "$rc" ] && grep -qF "$line" "$rc"; then
        say "    $(basename "$rc") already sets it — open a new terminal, or run:"
        say ""
        say "        source $rc"
        return 0
    fi

    if confirm "Add it to $(basename "$rc")?"; then
        if [ "$DRY_RUN" -eq 1 ]; then
            say "    \$ echo '$line' >> $rc"
        else
            printf '\n# Added by the TubeAmp installer\n%s\n' "$line" >> "$rc"
            say "    added to $rc — open a new terminal for it to take effect"
        fi
    else
        say "    Not changed. Add this yourself, or run TubeAmp as $BIN_LINK:"
        say ""
        say "        $line"
    fi
}

# ── Verify ──────────────────────────────────────────────────────

verify() {
    step "Verifying"
    [ "$DRY_RUN" -eq 1 ] && { say "    skipped in a dry run"; return 0; }

    local python_bin tubeamp_bin
    if [ "$MODE" = source ]; then
        python_bin="$SOURCE_DIR/.venv/bin/python"
        tubeamp_bin="$SOURCE_DIR/.venv/bin/tubeamp"
    else
        python_bin="$APP_DIR/bin/python"
        tubeamp_bin="$APP_DIR/bin/tubeamp"
    fi

    local failed=0
    if "$python_bin" -c 'import mpv' >/dev/null 2>&1; then
        say "    libmpv loads"
    else
        say "    MISSING: python-mpv cannot load libmpv, so nothing will play"
        failed=1
    fi
    if command -v ffmpeg >/dev/null 2>&1; then
        say "    ffmpeg found"
    else
        say "    MISSING: ffmpeg, so the spectrum bars stay simulated"
        failed=1
    fi
    if "$tubeamp_bin" --version >/dev/null 2>&1; then
        say "    $("$tubeamp_bin" --version)"
    else
        die "the tubeamp command did not install correctly"
    fi
    return "$failed"
}

# ── Uninstall ───────────────────────────────────────────────────

uninstall() {
    step "Removing TubeAmp"
    if [ -L "$BIN_LINK" ]; then
        run rm -f "$BIN_LINK"
        say "    removed $BIN_LINK"
    fi
    if [ -d "$APP_DIR" ]; then
        run rm -rf "$APP_DIR"
        say "    removed $APP_DIR"
    else
        say "    nothing installed at $APP_DIR"
    fi
    say ""
    say "Your settings and cached spectrum data are untouched, in ~/.config/tubeamp."
    say "Remove that directory too if you want no trace left."
    say "mpv and ffmpeg were installed with your package manager; remove them there."
    say "A PATH line the installer added to your shell's startup file also stays;"
    say "it is harmless, and removing it is your call."
}

# ── Main ────────────────────────────────────────────────────────

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --yes | -y) ASSUME_YES=1 ;;
            --dry-run | -n) DRY_RUN=1 ;;
            --uninstall) ACTION=uninstall ;;
            --help | -h) usage; return 0 ;;
            *) die "unknown option: $1 (try --help)" ;;
        esac
        shift
    done

    detect_mode

    if [ "$ACTION" = uninstall ]; then
        uninstall
        return 0
    fi

    say "=== TubeAmp installer ==="
    [ "$DRY_RUN" -eq 1 ] && say "(dry run — nothing will be changed)"
    if [ "$MODE" = source ]; then
        say "Source checkout at $SOURCE_DIR — installing in editable mode."
    else
        say "Installing the released package into $APP_DIR."
    fi

    # Python comes first: finding libmpv means asking ctypes, which needs it
    check_python
    install_system_dependencies

    if [ "$MODE" = source ]; then
        install_from_source
    else
        install_from_pypi
        ensure_path
    fi

    local incomplete=0
    verify || incomplete=1

    say ""
    say "=== Done ==="
    if [ "$incomplete" -eq 1 ]; then
        say "Some dependencies are missing — see above. TubeAmp starts either way and"
        say "will tell you what to install."
    fi
    say ""
    if [ "$MODE" = source ]; then
        say "Run it with:  ./run.sh"
    else
        say "Run it with:  tubeamp"
    fi
    say "Then press '/' to search YouTube or paste a playlist URL, and 'h' for help."
}

# The test suite sources this file to exercise the platform branches with
# stubbed package managers, which it cannot do if installing starts on load
if [ "${TUBEAMP_INSTALL_SOURCE_ONLY:-0}" != 1 ]; then
    main "$@"
fi
