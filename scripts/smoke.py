"""
Smoke-tests the two apps that scripts/freeze.py built into dist/, on this
OS. Exits with a message at the first failure.

    python scripts/smoke.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from freeze import binary_name
from PyInstaller.archive.readers import CArchiveReader

from go_python import __version__

SUFFIX = ".exe" if sys.platform == "win32" else ""
GUI = str(Path("dist", binary_name("go-python") + SUFFIX))
TUI = str(Path("dist", binary_name("go-python-tui") + SUFFIX))
# SDL's dummy drivers: a window and sound that need no display or speaker
ENV = os.environ | {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
# How long the window must keep playing bots: about 25 of their moves
WINDOW_S = 15
# Watch bots, a 6x6 board, Enter for the ko rule and the three seats, then
# quit at the menu once the match ends
WATCH = "2\n6\n\n\n\n\n3\n"

def check(args: list[str], expect: str, stdin: str = "") -> None:
    """
    Runs an app to its end and checks it succeeded and printed some text.

    Args:
        args: The app and its arguments
        expect: Text the output must contain
        stdin: What to type into the app
    """
    result = subprocess.run(args, input=stdin, capture_output=True,
                            encoding="utf-8", errors="replace", env=ENV,
                            timeout=300)
    if result.returncode != 0 or expect not in result.stdout:
        sys.exit(f"FAIL {' '.join(args)}: exit {result.returncode}, wanted "
                 f"{expect!r}\n{result.stdout}\n{result.stderr}")
    print("ok", *args)

def check_window(args: list[str]) -> None:
    """
    Starts the window and checks it is still running after WINDOW_S, then
    stops it. Output goes to a file, as a pipe could outlive the app.

    Args:
        args: The app and its arguments
    """
    with tempfile.TemporaryFile("w+", encoding="utf-8") as log:
        app = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                               env=ENV)
        try:
            code = app.wait(timeout=WINDOW_S)
        except subprocess.TimeoutExpired:
            # One-file apps run in a child process. TERM reaches it on
            # Linux and macOS; on Windows only taskkill /T does.
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(app.pid)],
                               check=True, capture_output=True)
            else:
                app.terminate()
            app.wait(timeout=30)
            print("ok", *args, f"(still playing after {WINDOW_S} s)")
            return
        log.seek(0)
        sys.exit(f"FAIL {' '.join(args)}: closed by itself with exit {code}"
                 f"\n{log.read()}")

def check_no_pygame(path: str) -> None:
    """
    Checks a one-file app holds no pygame module.

    Args:
        path: The app
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
    check([GUI, "--version"], f"go-python, version {__version__}")
    check([GUI, "bots", "-n", "1", "-s", "6"], "Average moves:")
    check_window([GUI, "gui", "-s", "6", "--seats", "random,random"])
    check([TUI, "--version"], f"go-python-tui, version {__version__}")
    check([TUI], "Game over:", stdin=WATCH)
    check_no_pygame(TUI)

if __name__ == "__main__":
    main()
