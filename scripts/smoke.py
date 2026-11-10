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
import time
from pathlib import Path

from freeze import binary_name

from go_python import __version__
from go_python.match import EndReason

# SDL's dummy drivers: a window and sound that need no display or speaker
ENV = os.environ | {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
# Longer than the slowest 6x6 bot match, 108 moves at 0.6 s each
TIMEOUT_S = 300
# How long the menu must stay open to show it started
MENU_S = 5
# How long an app may take to quit once asked
QUIT_S = 10
# How a match that was played to its end, not left, is reported
FINISHED = "Game over: (" + "|".join(
    re.escape(reason.value) for reason in EndReason
    if reason is not EndReason.ABORTED) + r")\."
# Watch bots, a 6x6 board, Enter for the ko rule and the three seats, then
# quit at the menu once the match ends
WATCH = "2\n6\n\n\n\n\n3\n"

def start(args: list[str]) -> subprocess.Popen[str]:
    """
    Starts an app with its output captured.

    Args:
        args: The app and its arguments

    Returns: The running app
    """
    # A session of its own, so stop() also reaches the child process a
    # one-file app runs in. Windows ignores it and uses taskkill /T.
    return subprocess.Popen(args, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding="utf-8", errors="replace", env=ENV,
                            start_new_session=True)

def stop(app: subprocess.Popen[str]) -> tuple[int | None, str]:
    """
    Asks a running app to quit, as closing its window does, and kills it if
    it has not quit after QUIT_S. Windows can only kill it.

    Args:
        app: The app

    Returns: Its exit code, or None if it was killed, and its output
    """
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(app.pid)],
                       capture_output=True)
    else:
        # SDL turns it into a quit event, and the one-file app then deletes
        # its unpacked files
        os.killpg(app.pid, signal.SIGTERM)
        try:
            output, _ = app.communicate(timeout=QUIT_S)
            return app.returncode, output
        except subprocess.TimeoutExpired:
            os.killpg(app.pid, signal.SIGKILL)
    output, _ = app.communicate()
    return None, output

def check(args: list[str], expect: str, stdin: str = "",
          interrupt_launcher: bool = False) -> None:
    """
    Runs an app to its end and checks it succeeded and printed some text.

    Args:
        args: The app and its arguments
        expect: A regular expression the output must match
        stdin: What to type into the app
        interrupt_launcher: True to send Ctrl+C's signal, SIGINT, to the
        one-file app's launcher alone after MENU_S, which must not pass it on

    Raises:
        SystemExit: If the app failed, timed out or printed something else
    """
    app = start(args)
    if interrupt_launcher:
        # The terminal sends Ctrl+C to the game too, so a launcher that
        # passed it on would make the game see it twice
        time.sleep(MENU_S)
        os.kill(app.pid, signal.SIGINT)
    try:
        output, _ = app.communicate(stdin, timeout=TIMEOUT_S)
        ended = f"exit {app.returncode}"
        passed = app.returncode == 0 and re.search(expect, output) is not None
    except subprocess.TimeoutExpired:
        _, output = stop(app)
        ended, passed = f"still running after {TIMEOUT_S} s", False
    if not passed:
        sys.exit(f"FAIL {' '.join(args)}: {ended}, wanted {expect!r}\n{output}")
    print("ok", *args)

def check_running(args: list[str]) -> None:
    """
    Starts an app that waits for a person, and checks it is still running
    after MENU_S. Then, except on Windows, checks it quits when asked, which
    a hung app cannot.

    Args:
        args: The app and its arguments

    Raises:
        SystemExit: If the app ended by itself, or did not quit when asked
    """
    app = start(args)
    try:
        output, _ = app.communicate("", timeout=MENU_S)
        sys.exit(f"FAIL {' '.join(args)}: ended by itself with exit "
                 f"{app.returncode}\n{output}")
    except subprocess.TimeoutExpired:
        code, output = stop(app)
    if sys.platform == "win32":
        print("ok", *args, f"(still open after {MENU_S} s)")
    elif code != 0:
        sys.exit(f"FAIL {' '.join(args)}: did not quit when asked: "
                 f"{'killed' if code is None else f'exit {code}'}\n{output}")
    else:
        print("ok", *args, f"(still open after {MENU_S} s, quit when asked)")

def check_no_pygame(path: str) -> None:
    """
    Checks a one-file app holds no pygame module.

    Args:
        path: The app

    Raises:
        SystemExit: If it holds pygame
    """
    # Imported here so tests/test_smoke.py runs without PyInstaller
    from PyInstaller.archive.readers import CArchiveReader

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
    # Named here, not on import, so tests/test_smoke.py runs on machines
    # with no release name
    suffix = ".exe" if sys.platform == "win32" else ""
    gui = str(Path("dist", binary_name("go-python") + suffix))
    tui = str(Path("dist", binary_name("go-python-tui") + suffix))
    # Windows has no SIGINT to send one process
    posix = sys.platform != "win32"
    check([gui, "--version"], re.escape(f"go-python, version {__version__}"))
    check([gui, "bots", "-n", "1", "-s", "6"], "Average moves:")
    check_running([gui])
    check([gui, "gui", "-s", "6", "--seats", "random,random",
           "--close-at-end"], FINISHED, interrupt_launcher=posix)
    check([tui, "--version"],
          re.escape(f"go-python-tui, version {__version__}"))
    check([tui], FINISHED, stdin=WATCH, interrupt_launcher=posix)
    check_no_pygame(tui)

if __name__ == "__main__":
    main()
