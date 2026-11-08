"""
Runs the go-python command the way a user would.
"""
import random

import pytest
from click.testing import CliRunner

from go_python import __version__
from go_python.cli import main

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
