#!/usr/bin/env bash

# TubeAmp launcher script
# Activates the venv and runs tubeamp, rebuilding the venv if a Python
# upgrade (e.g. `brew upgrade python`) left its interpreter symlinks dangling.
#
# Usage:
#   ./run.sh

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

rebuild_venv() {
    echo "Rebuilding virtual environment in $VENV_DIR ..." >&2
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q -e "$SCRIPT_DIR"
}

# A dangling interpreter symlink survives `-d` checks, so probe the binary.
if [ ! -x "$VENV_DIR/bin/python" ] || ! "$VENV_DIR/bin/python" -c '' 2>/dev/null; then
    rebuild_venv
fi

# The package itself can go missing if the editable install was clobbered.
if ! "$VENV_DIR/bin/python" -c 'import tubeamp' 2>/dev/null; then
    "$VENV_DIR/bin/pip" install -q -e "$SCRIPT_DIR"
fi

exec "$VENV_DIR/bin/tubeamp" "$@"
