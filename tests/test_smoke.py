"""
Checks scripts/smoke.py fails broken apps. Small Python programs stand in
for the apps, so these tests need no build.
"""
import importlib
import platform
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import smoke  # noqa: E402

from go_python.match import EndReason  # noqa: E402

FINISHED = "Game over: every player passed."
# A one-file app's shape: a parent waiting on a child that shares its output.
# Both ignore SIGTERM, as a hung app does.
DEAF = """
import signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
subprocess.Popen([sys.executable, "-c", "import signal, time; "
                  "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                  "print('ready', flush=True); time.sleep(600)"])
time.sleep(600)
"""
# Quits cleanly when asked, as SDL does, printing a finished match
POLITE = f"""
import signal, sys, time
def leave(*_):
    print({FINISHED!r})
    sys.exit(0)
signal.signal(signal.SIGTERM, leave)
time.sleep(600)
"""
# Dies of the signal, as Python with no handler does
PLAIN = "import time; time.sleep(600)"

@pytest.fixture(autouse=True)
def short_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Cuts the smoke test's waits to seconds.

    Args:
        monkeypatch: The pytest fixture
    """
    monkeypatch.setattr(smoke, "TIMEOUT_S", 2)
    monkeypatch.setattr(smoke, "MENU_S", 1)
    monkeypatch.setattr(smoke, "QUIT_S", 2)

def app(code: str) -> list[str]:
    """
    Builds the command that runs a stand-in app.

    Args:
        code: The app's Python code

    Returns: The command
    """
    return [sys.executable, "-c", code]

def test_imports_where_no_app_is_released(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check the smoke test, and so these tests, load on a machine with no
    release name, as the sdist's tests run anywhere"""
    monkeypatch.setattr(platform, "machine", lambda: "riscv64")
    importlib.reload(sys.modules["freeze"])
    importlib.reload(smoke)

def test_finished_takes_every_end_but_leaving() -> None:
    """Check a match the player left never counts as played to its end"""
    for reason in EndReason:
        found = re.search(smoke.FINISHED, f"Game over: {reason.value}.")
        assert (found is None) == (reason is EndReason.ABORTED), reason

def test_stop_kills_a_hung_app_and_its_child() -> None:
    """Check stop() also ends the child a one-file app runs in. The child
    holds the output pipe, so stop() would wait for it forever."""
    running = smoke.start(app(DEAF))
    assert running.stdout is not None
    assert running.stdout.readline() == "ready\n"
    assert smoke.stop(running)[0] is None

def test_check_passes_a_finished_match(capsys: pytest.CaptureFixture[str]) \
        -> None:
    """Check a match played to its end passes"""
    smoke.check(app(f"print({FINISHED!r})"), smoke.FINISHED)
    assert capsys.readouterr().out.startswith("ok ")

@pytest.mark.parametrize("code, why", [
    (f"print({FINISHED!r}); raise SystemExit(3)", "exit 3"),
    ("print('Game over: the match was left.')", "exit 0"),
    (DEAF, "still running after 2 s"),
    # It prints a finished match once asked to quit, but it never ended
    (POLITE, "still running after 2 s"),
])
def test_check_fails_a_broken_app(code: str, why: str) -> None:
    """Check a crash, a match left early and a hang all fail"""
    with pytest.raises(SystemExit, match=why):
        smoke.check(app(code), smoke.FINISHED)

# A match lasting past the launcher's interrupt, which Ctrl+C ends early
MATCH = f"""
import time
try:
    time.sleep(1.5)
except KeyboardInterrupt:
    print("Game over: the match was left.")
    raise SystemExit(0)
print({FINISHED!r})
"""

@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows has no SIGINT to send one process")
def test_check_can_interrupt_the_launcher() -> None:
    """Check interrupt_launcher sends the app Ctrl+C's signal: a launcher
    that passed it on would end the match early"""
    smoke.check(app("import signal; signal.signal(signal.SIGINT, "
                    "signal.SIG_IGN)\n" + MATCH), smoke.FINISHED,
                interrupt_launcher=True)
    with pytest.raises(SystemExit, match="exit 0"):
        smoke.check(app(MATCH), smoke.FINISHED, interrupt_launcher=True)

def test_check_running_passes_a_menu_that_quits_when_asked(
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a menu that stays open, then quits when asked, passes"""
    smoke.check_running(app(POLITE))
    assert capsys.readouterr().out.startswith("ok ")

def test_check_running_fails_an_app_that_ends_by_itself() -> None:
    """Check a menu that closes at once fails"""
    with pytest.raises(SystemExit, match="ended by itself with exit 0"):
        smoke.check_running(app("pass"))

@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows can only kill the app")
@pytest.mark.parametrize("code, why", [(DEAF, "killed"), (PLAIN, "exit -15")])
def test_check_running_fails_a_menu_that_does_not_quit_when_asked(
        code: str, why: str) -> None:
    """Check a hung menu fails, and so does one that dies of the signal
    instead of quitting"""
    with pytest.raises(SystemExit, match=f"did not quit when asked: {why}"):
        smoke.check_running(app(code))
