"""
Builds the two standalone apps into dist/ with PyInstaller, each one file
named for this OS and machine:

- go-python-<os>-<arch> opens the game window.
- go-python-tui-<os>-<arch> is the terminal game, built without pygame.

Run it from the repo root after pip install ".[release]":

    python scripts/freeze.py
"""
import platform
from pathlib import Path

SYSTEMS = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}
MACHINES = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "arm64",
            "aarch64": "arm64"}

# Each app's function in go_python.cli, and the options only it gets
APPS = {
    # Both are console apps, so the test commands can print. On Windows a
    # double-click still hides the console, as nobody types there.
    "go-python": ("main", ["--hide-console", "hide-early"]),
    # The window code is imported only inside functions, which PyInstaller
    # cannot tell apart, so it is left out by name
    "go-python-tui": ("tui_main", ["--exclude-module", "pygame",
                                   "--exclude-module", "go_python.gui"]),
}

def binary_name(app: str) -> str:
    """
    Names an app's binary for this OS and machine. PyInstaller adds .exe on
    Windows.

    Args:
        app: go-python or go-python-tui

    Raises:
        KeyError: If this OS or machine has no release name

    Returns: The name, like go-python-linux-x86_64
    """
    return (f"{app}-{SYSTEMS[platform.system()]}-"
            f"{MACHINES[platform.machine().lower()]}")

def main() -> None:
    """
    Builds both apps, writing PyInstaller's work files to build/.
    """
    # Imported here so the smoke test's tests can name the apps without it
    import PyInstaller.__main__

    build = Path("build")
    build.mkdir(exist_ok=True)
    # The Linux Python on CI keeps its debug symbols: 11 MB in each app
    strip = ["--strip"] if platform.system() == "Linux" else []
    for app, (function, options) in APPS.items():
        entry = build / f"{app}.py"
        entry.write_text(f"from go_python.cli import {function}\n"
                         f"{function}()\n", encoding="utf-8")
        # UTF-8 mode, as a frozen app ignores PYTHONUTF8: without it, output
        # piped on Windows is cp1252, which cannot show the stones.
        # The launcher ignores signals: Ctrl+C already reaches the game from
        # the terminal, and passed on as well, it arrives twice and can quit
        # the game from its own Ctrl+C handling. So to stop an app, signal its
        # process group, as a terminal does: a signal to the launcher alone
        # no longer reaches the game.
        PyInstaller.__main__.run([
            str(entry), "--onefile", "--noconfirm", "--clean",
            "--name", binary_name(app), "--distpath", "dist",
            "--workpath", str(build / app), "--specpath", str(build),
            "--python-option", "X utf8", "--bootloader-ignore-signals",
            *strip, *options])

if __name__ == "__main__":
    main()
