#!/usr/bin/env bash
# TubeAmp installer — installs system deps + Python package
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"

echo "=== TubeAmp Installer ==="
echo

# 1. Detect OS and install system deps
install_deps() {
    case "$(uname -s)" in
        Darwin)
            echo "Detected macOS"
            if ! command -v brew &>/dev/null; then
                echo "Error: Homebrew not found. Install from https://brew.sh"
                exit 1
            fi
            echo "Installing system dependencies via Homebrew..."
            # The mpv formula ships libmpv and pulls yt-dlp in as a dependency
            brew install mpv ffmpeg
            ;;
        Linux)
            echo "Detected Linux"
            # python-mpv loads libmpv through ctypes, and the `mpv` package
            # does not always pull that shared library in — on Ubuntu it does
            # not, which surfaces as "Cannot find libmpv in the usual places".
            # yt-dlp is a project dependency and comes from the venv, so it is
            # deliberately not installed system-wide here.
            if command -v apt-get &>/dev/null; then
                echo "Installing system dependencies via apt..."
                export DEBIAN_FRONTEND=noninteractive
                sudo apt-get update -qq
                libmpv_pkg="libmpv2"
                apt-cache show "$libmpv_pkg" &>/dev/null || libmpv_pkg="libmpv1"
                sudo apt-get install -y mpv "$libmpv_pkg" ffmpeg
                # Debian/Ubuntu ship ensurepip separately, and `python3 -m venv`
                # fails without it even though the `venv` module imports fine
                if ! python3 -c 'import ensurepip' &>/dev/null; then
                    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
                    sudo apt-get install -y "python${py_ver}-venv" \
                        || sudo apt-get install -y python3-venv
                fi
            elif command -v pacman &>/dev/null; then
                echo "Installing system dependencies via pacman..."
                sudo pacman -S --needed --noconfirm mpv ffmpeg
            elif command -v dnf &>/dev/null; then
                echo "Installing system dependencies via dnf..."
                sudo dnf install -y mpv mpv-libs ffmpeg
            else
                echo "Unsupported package manager. Please install manually:"
                echo "  mpv (plus its libmpv shared library) and ffmpeg"
            fi
            ;;
        *)
            echo "Unsupported OS: $(uname -s)"
            exit 1
            ;;
    esac
    echo
}

# 2. Check Python version
check_python() {
    if ! command -v python3 &>/dev/null; then
        echo "Error: python3 not found. Install Python 3.11+"
        exit 1
    fi
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "Python version: $PY_VERSION"
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || {
        echo "Error: Python 3.11+ required, found $PY_VERSION"
        exit 1
    }
    python3 -c 'import ensurepip' 2>/dev/null || {
        echo "Error: ensurepip is missing, so 'python3 -m venv' cannot work."
        echo "       On Debian/Ubuntu: sudo apt install python${PY_VERSION}-venv"
        exit 1
    }
}

# 3. Create venv, rebuilding it if its interpreter has gone stale
#    (a Homebrew Python upgrade leaves the venv's symlinks dangling)
setup_venv() {
    if [ -d "$VENV_DIR" ] && ! "$VENV_DIR/bin/python" -c '' 2>/dev/null; then
        echo "Existing venv is broken (interpreter gone) — rebuilding..."
        rm -rf "$VENV_DIR"
    fi
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    else
        echo "Virtual environment already exists"
    fi
}

# 4. Install tubeamp
install_tubeamp() {
    echo "Installing TubeAmp..."
    "$VENV_DIR/bin/pip" install -q -e .
}

# 5. Fail loudly here rather than at first playback
verify() {
    echo "Verifying installation..."
    failed=0
    if ! "$VENV_DIR/bin/python" -c 'import mpv' 2>/dev/null; then
        echo "  FAIL: python-mpv cannot load libmpv."
        echo "        Install your distribution's libmpv runtime package"
        echo "        (Debian/Ubuntu: libmpv2, Fedora: mpv-libs)."
        failed=1
    fi
    if ! command -v ffmpeg &>/dev/null; then
        echo "  FAIL: ffmpeg not found; the spectrum visualizer needs it."
        failed=1
    fi
    if ! "$VENV_DIR/bin/python" -c 'import tubeamp' 2>/dev/null; then
        echo "  FAIL: the tubeamp package did not install."
        failed=1
    fi
    [ "$failed" -eq 0 ] || exit 1
    echo "  All checks passed"
}

# Run installation steps
install_deps
check_python
setup_venv
install_tubeamp
verify

echo
echo "=== Installation Complete ==="
echo
echo "To run TubeAmp:"
echo "  ./run.sh"
echo
echo "Or activate the venv manually:"
echo "  source .venv/bin/activate"
echo "  tubeamp"
