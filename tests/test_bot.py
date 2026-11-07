"""
Runs the bot command the way a user would.
"""
import pytest
from click.testing import CliRunner

from go_python.bot import cmd

@pytest.mark.parametrize("size", ["0", "-1"])
def test_board_with_no_side_is_refused(size: str) -> None:
    """Check that the option is refused with a message, not a traceback"""
    result = CliRunner().invoke(cmd, ["-s", size, "-n", "1"])
    assert result.exit_code == 2
    assert "--size" in result.output

def test_bots_finish_a_game() -> None:
    """Check that two bots play a small game to the end"""
    result = CliRunner().invoke(cmd, ["-s", "6", "-n", "1"])
    assert result.exit_code == 0, result.output
