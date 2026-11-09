"""
Smoke-tests the two apps that scripts/freeze.py built into dist/, on this
OS. Exits with a message at the first failure.

    python scripts/smoke.py
"""
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

from freeze import binary_name
from PyInstaller.archive.readers import CArchiveReader

from go_python import __version__
from go_python.match import EndReason

SUFFIX = ".exe" if sys.platform == "win32" else ""
GUI = str(Path("dist", binary_name("go-python") + SUFFIX))
TUI = str(Path("dist", binary_name("go-python-tui") + SUFFIX))
# SDL's dummy drivers: a window and sound that need no display or speaker
ENV = os.environ | {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
# Longer than the slowest 6x6 bot match, 108 moves at 0.6 s each
TIMEOUT_S = 300
# How long the menu must stay open to show it started
MENU_S = 5
# How a match that was played to its end, not left, is reported
FINISHED = "Game over: (" + "|".join(
    re.escape(reason.value) for reason in EndReason
    if reason is not EndReason.ABORTED) + r")\."
# Watch bots, a 6x6 board, Enter for the ko rule and the three seats, then
# quit at the menu once the match ends
WATCH = "2\n6\n\n\n\n\n3\n"

def run(args: list[str], stdin: str, timeout: float) -> tuple[int | None, str]:
    """
    Runs an app until it ends or the time is up, then stops it.

    Args:
        args: The app and its arguments
        stdin: What to type into the app
        timeout: Seconds to wait for it to end

    Returns: Its exit code, or None if it was still running, and its output
    """
    # A session of its own, so the kill below also reaches the child process
    # a one-file app runs in. Windows ignores it and uses taskkill /T.
    app = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, encoding="utf-8",
                           errors="replace", env=ENV, start_new_session=True)
    try:
        output, _ = app.communicate(stdin, timeout=timeout)
        return app.returncode, output
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(app.pid)],
                           capture_output=True)
        else:
            os.killpg(app.pid, signal.SIGKILL)
        output, _ = app.communicate()
        return None, output

def check(args: list[str], expect: str, stdin: str = "") -> None:
    """
    Runs an app to its end and checks it succeeded and printed some text.

    Args:
        args: The app and its arguments
        expect: A regular expression the output must match
        stdin: What to type into the app

    Raises:
        SystemExit: If the app failed, timed out or printed something else
    """
    code, output = run(args, stdin, TIMEOUT_S)
    if code != 0 or not re.search(expect, output):
        ended = (f"still running after {TIMEOUT_S} s" if code is None
                 else f"exit {code}")
        sys.exit(f"FAIL {' '.join(args)}: {ended}, wanted {expect!r}\n{output}")
    print("ok", *args)

def check_running(args: list[str]) -> None:
    """
    Starts an app that waits for a person, and checks it is still running
    after MENU_S, then stops it.

    Args:
        args: The app and its arguments

    Raises:
        SystemExit: If the app ended by itself
    """
    code, output = run(args, "", MENU_S)
    if code is not None:
        sys.exit(f"FAIL {' '.join(args)}: ended by itself with exit {code}"
                 f"\n{output}")
    print("ok", *args, f"(still open after {MENU_S} s)")

def check_no_pygame(path: str) -> None:
    """
    Checks a one-file app holds no pygame module.

    Args:
        path: The app

    Raises:
        SystemExit: If it holds pygame
    """
    # The app's files, and the modules in its zipped Python archive
    archive = CArchiveReader(path)
    names = list(archive.toc)
    for name in archive.toc:
        if name.endswith(".pyz"):
            names += archive.open_embedded_archive(name).toc
    found = [name for name in names if name.startswith("pygame")]
    if found:
        sys.exit(f"FAIL {path} holds pygame: {found[:5]}")
    print("ok", path, "holds no pygame")

def main() -> None:
    """
    Runs every check.
    """
    check([GUI, "--version"], re.escape(f"go-python, version {__version__}"))
    check([GUI, "bots", "-n", "1", "-s", "6"], "Average moves:")
    check_running([GUI])
    check([GUI, "gui", "-s", "6", "--seats", "random,random",
           "--close-at-end"], FINISHED)
    check([TUI, "--version"],
          re.escape(f"go-python-tui, version {__version__}"))
    check([TUI], FINISHED, stdin=WATCH)
    check_no_pygame(TUI)

if __name__ == "__main__":
    main()
