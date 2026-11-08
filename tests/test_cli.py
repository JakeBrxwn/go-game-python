"""
Runs the go-python command the way a user would.
"""
import random
import subprocess
import sys

import pytest
from click.testing import CliRunner

from go_python import __version__
from go_python import gui, tui
from go_python.cli import main, tui_main
from go_python.match import GameConfig, SeriesResult

def test_version() -> None:
    """Check the command reports its version"""
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.output == f"go-python, version {__version__}\n"

def test_bots_print_the_totals() -> None:
    """Check a bot series prints win rates, ties and average moves"""
    random.seed(0)
    result = CliRunner().invoke(main, ["bots", "-n", "2", "-1", "smart"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert [line.split(":")[0] for line in lines] == [
        "Player 1 wins", "Player 2 wins", "Ties", "Average moves"]

@pytest.mark.parametrize("size", ["0", "-1", "5", "31"])
def test_bots_refuse_a_board_out_of_range(size: str) -> None:
    """Check a bad size exits 2 with a message, not a traceback"""
    result = CliRunner().invoke(main, ["bots", "-s", size, "-n", "1"])
    assert result.exit_code == 2
    assert "size must be" in result.output

def test_bots_refuse_no_games() -> None:
    """Check a series of no games exits 2 rather than dividing by zero"""
    result = CliRunner().invoke(main, ["bots", "-n", "0"])
    assert result.exit_code == 2
    assert "--num-games" in result.output

def test_bots_refuse_an_unknown_bot() -> None:
    """Check only the two bots are accepted"""
    result = CliRunner().invoke(main, ["bots", "-2", "human"])
    assert result.exit_code == 2
    assert "--player2" in result.output

def test_bots_print_exact_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check the totals, their rounding, and the settings the series gets"""
    seen: list[tuple[GameConfig, int]] = []

    def fake_series(config: GameConfig, games: int) -> SeriesResult:
        seen.append((config, games))
        return SeriesResult(games, {1: 2, 2: 0}, 1, 300)

    monkeypatch.setattr("go_python.cli.run_series", fake_series)
    result = CliRunner().invoke(main, ["bots", "-n", "3", "-1", "SMART"])
    assert result.exit_code == 0, result.output
    assert result.output == ("Player 1 wins: 66.67%\nPlayer 2 wins: 0.0%\n"
                             "Ties: 33.33%\nAverage moves: 100.0\n")
    assert seen == [(GameConfig(6, False, ("smart", "random")), 3)]

    CliRunner().invoke(main, ["bots"])
    assert seen[-1] == (GameConfig(6, False, ("random", "random")), 20)

def test_bots_help_describes_each_option() -> None:
    """Check the help shows the summary and one line per option, not the
    docstring's Args block"""
    result = CliRunner().invoke(main, ["bots", "--help"])
    assert "Args:" not in result.output
    assert "The bot that moves first." in result.output
    assert "The bot that moves second." in result.output

def test_bots_round_each_rate_once(monkeypatch: pytest.MonkeyPatch) \
        -> None:
    """Check a rate is rounded from the exact percentage: 23 of 160 games
    is 14.375%, which prints as 14.38%"""
    monkeypatch.setattr("go_python.cli.run_series",
                        lambda config, games: SeriesResult(
                            160, {1: 23, 2: 49}, 88, 1000))
    result = CliRunner().invoke(main, ["bots", "-n", "160"])
    assert result.output == ("Player 1 wins: 14.38%\nPlayer 2 wins: 30.62%\n"
                             "Ties: 55.0%\nAverage moves: 6.25\n")

#
# Starting the window and the terminal
#

def remember_runs(monkeypatch: pytest.MonkeyPatch) \
        -> list[tuple[str, GameConfig | None]]:
    """
    Replaces the window and the terminal app with stand-ins that record how
    they were started.

    Args:
        monkeypatch: The pytest fixture

    Returns: The list each start is added to: which app, and its settings
    """
    runs: list[tuple[str, GameConfig | None]] = []
    monkeypatch.setattr(gui, "run",
                        lambda config=None: runs.append(("gui", config)))
    monkeypatch.setattr(tui, "run",
                        lambda config=None: runs.append(("tui", config)))
    return runs

def test_no_command_opens_the_window_menu(monkeypatch: pytest.MonkeyPatch) \
        -> None:
    """Check go-python on its own opens the window on its menu"""
    runs = remember_runs(monkeypatch)
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 0, result.output
    assert runs == [("gui", None)]

def test_tui_command_opens_the_terminal_menu(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check go-python-tui opens the terminal app on its menu"""
    runs = remember_runs(monkeypatch)
    result = CliRunner().invoke(tui_main, [])
    assert result.exit_code == 0, result.output
    assert runs == [("tui", None)]

@pytest.mark.parametrize("app", ["gui", "tui"])
def test_match_commands_pass_their_settings(monkeypatch: pytest.MonkeyPatch,
                                            app: str) -> None:
    """Check the test commands start one match with the settings given"""
    runs = remember_runs(monkeypatch)
    result = CliRunner().invoke(main, [app, "-s", "9", "--ko", "super",
                                       "--seats", "Human, random,smart"])
    assert result.exit_code == 0, result.output
    assert runs == [(app, GameConfig(9, True, ("human", "random", "smart")))]

@pytest.mark.parametrize("app", ["gui", "tui"])
def test_match_commands_take_any_letter_case(monkeypatch: pytest.MonkeyPatch,
                                             app: str) -> None:
    """Check --ko takes capitals, as the bot and seat choices do"""
    runs = remember_runs(monkeypatch)
    result = CliRunner().invoke(main, [app, "--ko", "SUPER"])
    assert result.exit_code == 0, result.output
    assert runs == [(app, GameConfig(19, True, ("human", "smart")))]

@pytest.mark.parametrize("command", [[], ["gui"], ["tui"], ["bots"]])
def test_help_shows_the_size_range_and_no_args(command: list[str]) -> None:
    """Check each help page gives the board sizes and hides the docstring's
    Args block"""
    result = CliRunner().invoke(main, [*command, "--help"])
    assert result.exit_code == 0
    assert "Args:" not in result.output
    assert command == [] or "6 to 30" in result.output

@pytest.mark.parametrize("app", ["gui", "tui"])
def test_match_commands_default_to_a_person_against_smart(
        monkeypatch: pytest.MonkeyPatch, app: str) -> None:
    """Check the defaults of the test commands"""
    runs = remember_runs(monkeypatch)
    CliRunner().invoke(main, [app])
    assert runs == [(app, GameConfig(19, False, ("human", "smart")))]

@pytest.mark.parametrize("args, message", [
    (["--seats", "human,robot"], "seats must be"),
    (["--seats", "human"], "seats must be"),
    (["-s", "40"], "size must be"),
    (["--ko", "japanese"], "--ko"),
])
@pytest.mark.parametrize("app", ["gui", "tui"])
def test_match_commands_refuse_bad_settings(monkeypatch: pytest.MonkeyPatch,
                                            app: str, args: list[str],
                                            message: str) -> None:
    """Check a bad setting exits 2 with a message and starts nothing"""
    runs = remember_runs(monkeypatch)
    result = CliRunner().invoke(main, [app, *args])
    assert result.exit_code == 2
    assert message in result.output
    assert runs == []

@pytest.mark.parametrize("command", [
    "import go_python.cli",
    "from go_python.cli import main; main(['tui', '--help'])",
])
def test_terminal_commands_never_load_pygame(command: str) -> None:
    """Check the terminal package can ship without pygame"""
    code = (f"import sys\ntry:\n    {command}\nexcept SystemExit:\n"
            "    pass\nassert 'pygame' not in sys.modules")
    subprocess.run([sys.executable, "-c", code], check=True,
                   capture_output=True)
