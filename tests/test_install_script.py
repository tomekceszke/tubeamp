"""The installer is the first thing most users run, and it is not Python.

It cannot be exercised for real from a test — it installs packages — so this
drives it with `--dry-run` and with stubbed package managers on `PATH`, which
is the only way to reach the Linux branches from a macOS or CI runner.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER = REPO_ROOT / "install.sh"
# Absolute, because several tests hand the script a PATH with no shell on it
BASH = shutil.which("bash") or "/bin/bash"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell script")


def _run(*args: str, stdin: str | None = None, env: dict[str, str] | None = None) -> str:
    """Run the installer, returning stdout and stderr together.

    Piping to bash means the script arrives on stdin, so its own options have
    to come after `--` or bash claims them for itself.
    """
    command = [BASH, "-s", "--"] if stdin is not None else [BASH, str(INSTALLER)]
    result = subprocess.run(
        [*command, *args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={**os.environ, **(env or {})},
        timeout=120,
    )
    return result.stdout + result.stderr


def test_help_needs_no_arguments_beyond_itself() -> None:
    assert "TubeAmp installer" in _run("--help")


class TestModeDetection:
    """One file, two jobs: a clone installs itself, a piped copy fetches a release."""

    def test_a_checkout_installs_in_editable_mode(self) -> None:
        output = _run("--dry-run")
        assert f"Source checkout at {REPO_ROOT}" in output
        assert "-e" in output
        assert ".venv" in output

    def test_a_piped_copy_installs_the_release(self) -> None:
        output = _run("--dry-run", stdin=INSTALLER.read_text())
        assert ".local/share/tubeamp" in output
        assert ".local/bin/tubeamp" in output
        assert "editable" not in output

    def test_a_dry_run_creates_nothing(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        home.mkdir()

        _run("--dry-run", stdin=INSTALLER.read_text(), env={"HOME": str(home)})

        assert list(home.iterdir()) == []


class TestLinuxPackageSelection:
    """The distro-specific package names are where an installer usually lies.

    Debian and Ubuntu do not pull the shared library in with `mpv`, and the
    soname moved between releases, so the name has to be probed rather than
    assumed. Reaching those branches from a macOS or CI runner means sourcing
    the script and standing in for both `uname` and the package manager.
    """

    DRIVER = """
set -euo pipefail
export TUBEAMP_INSTALL_SOURCE_ONLY=1
# shellcheck source=/dev/null
source "$1"
DRY_RUN=1
ASSUME_YES=1
PYTHON=python3
has_libmpv() { return 1; }   # pretend the runtime library is not installed
install_system_dependencies
"""

    def _plan(self, tmp_path: Path, manager: str, libmpv2: bool = True) -> str:
        """Run the dependency step against a stubbed distro."""
        stubs = tmp_path / "stubs"
        stubs.mkdir()
        (stubs / "uname").write_text("#!/bin/sh\necho Linux\n")
        (stubs / manager).write_text("#!/bin/sh\nexit 0\n")
        (stubs / "sudo").write_text("#!/bin/sh\nexit 0\n")
        if manager == "apt-get":
            # `apt-cache show libmpv2` decides which soname this release carries
            (stubs / "apt-cache").write_text(f"#!/bin/sh\nexit {0 if libmpv2 else 1}\n")
        for stub in stubs.iterdir():
            stub.chmod(0o755)

        driver = tmp_path / "driver.sh"
        driver.write_text(self.DRIVER)

        result = subprocess.run(
            [BASH, str(driver), str(INSTALLER)],
            capture_output=True,
            text=True,
            timeout=120,
            env={
                "HOME": str(tmp_path / "home"),
                # Nothing but the stubs: on a real Linux runner /usr/bin holds
                # a genuine apt-get and ffmpeg, which would answer before the
                # stand-ins and quietly test the host instead of the branch
                "PATH": str(stubs),
            },
        )
        return result.stdout + result.stderr

    def test_debian_gets_the_separate_shared_library(self, tmp_path: Path) -> None:
        assert "sudo apt-get install -y mpv libmpv2 ffmpeg" in self._plan(tmp_path, "apt-get")

    def test_older_debian_falls_back_to_libmpv1(self, tmp_path: Path) -> None:
        plan = self._plan(tmp_path, "apt-get", libmpv2=False)
        assert "libmpv1" in plan
        assert "libmpv2" not in plan

    def test_fedora_names_mpv_libs(self, tmp_path: Path) -> None:
        assert "sudo dnf install -y mpv mpv-libs ffmpeg" in self._plan(tmp_path, "dnf")

    def test_arch_ships_libmpv_inside_mpv(self, tmp_path: Path) -> None:
        plan = self._plan(tmp_path, "pacman")
        assert "sudo pacman -S --needed --noconfirm mpv ffmpeg" in plan

    def test_an_unknown_manager_says_what_to_install(self, tmp_path: Path) -> None:
        plan = self._plan(tmp_path, "true")
        assert "unknown package manager" in plan
        assert "mpv" in plan


class TestPrompting:
    """Under `curl | bash` stdin is the script, so questions go to /dev/tty.

    A detached process has a /dev/tty node it cannot open, which `test -r`
    happily reports as readable — the script has to try opening it instead, or
    raw shell errors end up in the middle of the output.
    """

    DRIVER = """
set -euo pipefail
export TUBEAMP_INSTALL_SOURCE_ONLY=1
# shellcheck source=/dev/null
source "$1"
ensure_path
"""

    def test_it_does_not_guess_when_there_is_no_terminal(self, tmp_path: Path) -> None:
        driver = tmp_path / "driver.sh"
        driver.write_text(self.DRIVER)
        home = tmp_path / "home"
        home.mkdir()

        result = subprocess.run(
            [BASH, str(driver), str(INSTALLER)],
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
            # A PATH without ~/.local/bin is what makes ensure_path speak up
            env={"HOME": str(home), "PATH": "/usr/bin:/bin", "SHELL": "/bin/zsh"},
        )
        output = result.stdout + result.stderr

        assert "no terminal to ask on" in output
        assert "export PATH=" in output
        # The raw shell error this used to spill instead
        assert "Device not configured" not in output
        # Declining must leave the startup file alone
        assert not (home / ".zshrc").exists()
