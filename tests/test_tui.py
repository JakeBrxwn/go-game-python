"""
Tests for the text frontend: what it accepts as a move, how it draws the
board, and whole sessions typed through stdin.
"""
import io
import random
import re
import subprocess
import sys
import time

import pytest
from colorama import Fore

from go_python import tui
from go_python.go import Go
from go_python.match import GameConfig
from go_python.tui import Command, board_text, parse_command

NOT_A_MOVE = ("Not a move: type a column letter and a row number, like D4, "
              "or pass, hint or quit.")
NO_I = "There is no column I: Go boards skip it, so J follows H."

@pytest.fixture(autouse=True)
def no_bot_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lets bots move at once in every test"""
    monkeypatch.setattr(tui, "BOT_DELAY_S", 0)

def session(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
            lines: list[str], config: GameConfig | None = None) -> str:
    """
    Runs the TUI with typed lines, then end of input.

    Args:
        monkeypatch: Replaces stdin
        capsys: Captures what the TUI prints, prompts included
        lines: What the person types, one entry per Enter
        config: The settings of one match, or None for the menu

    Returns: Everything printed
    """
    monkeypatch.setattr(sys, "stdin", io.StringIO("".join(
        line + "\n" for line in lines)))
    tui.run(config)
    return capsys.readouterr().out

#
# parse_command
#

@pytest.mark.parametrize("text, side, expected", [
    ("D4", 19, (15, 3)),
    ("d4", 19, (15, 3)),
    ("  q16 ", 19, (3, 15)),
    ("D 4", 9, (5, 3)),
    ("D04", 9, (5, 3)),
    ("A1", 6, (5, 0)),
    ("F6", 6, (0, 5)),
    ("J9", 9, (0, 8)),
    ("T19", 19, (0, 18)),
    ("Z25", 25, (0, 24)),
    ("aa1", 26, (25, 25)),
    ("AE30", 30, (0, 29)),
    ("pass", 19, Command.PASS),
    ("PASS", 19, Command.PASS),
    (" Hint ", 19, Command.HINT),
    ("quit", 19, Command.QUIT),
    ("", 19, NOT_A_MOVE),
    ("   ", 19, NOT_A_MOVE),
    ("10 10", 19, NOT_A_MOVE),
    ("9 9", 9, NOT_A_MOVE),
    ("4D", 19, NOT_A_MOVE),
    ("D", 19, NOT_A_MOVE),
    ("D-4", 19, NOT_A_MOVE),
    ("D4.5", 19, NOT_A_MOVE),
    ("passs", 19, NOT_A_MOVE),
    ("D1000", 19, NOT_A_MOVE),
    ("D" + "9" * 5000, 19, NOT_A_MOVE),
    ("I5", 19, NO_I),
    ("i5", 19, NO_I),
    ("K9", 9, "K9 is off the board: columns run A to J and rows 1 to 9."),
    ("J10", 9, "J10 is off the board: columns run A to J and rows 1 to 9."),
    ("D0", 9, "D0 is off the board: columns run A to J and rows 1 to 9."),
    ("d999", 6, "D999 is off the board: columns run A to F and rows 1 to 6."),
    ("AA1", 25,
     "AA1 is off the board: columns run A to Z and rows 1 to 25."),
    ("AF1", 30,
     "AF1 is off the board: columns run A to AE and rows 1 to 30."),
])
def test_parse_command(text: str, side: int,
                       expected: tuple[int, int] | Command | str) -> None:
    """Check each kind of typed text gives a move, a command or a message"""
    assert parse_command(text, side) == expected

#
# Board
#

@pytest.mark.parametrize("side", range(6, 31))
def test_every_printed_label_parses_to_its_point(side: int) -> None:
    """Check every label the board prints is a coordinate for the point
    under it, on every size, with letters above and below"""
    lines = board_text(Go(side, 2)).splitlines()
    letters = lines[0].split()
    columns = [found.start() for found in re.finditer(r"\S+", lines[0])]
    assert lines[-1] == lines[0]
    assert len(letters) == side and "I" not in letters
    assert len(lines) == side + 2
    for r, line in enumerate(lines[1:-1]):
        number = line.split()[0]
        assert line.split()[-1] == number
        assert [i for i, ch in enumerate(line) if ch == "·"] == columns
        for c, column in enumerate(letters):
            assert parse_command(column + number, side) == (r, c)

def test_board_shows_each_players_stone() -> None:
    """Check four players' stones land on the points that name them"""
    game = Go(6, 4)
    for pos in [(0, 0), (0, 5), (5, 0), (5, 5)]:
        game.apply_move(pos)
    lines = board_text(game).splitlines()
    assert lines[1].startswith(" 6 ●") and lines[1].endswith("○ 6")
    assert lines[6].startswith(" 1 " + tui.STONES[2])
    assert lines[6].endswith(tui.STONES[3] + " 1")

#
# Sessions
#

def test_human_against_human_to_the_end(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check two people play a whole game: walls, then both pass"""
    walls = [f"{column}{row}" for row in range(1, 7) for column in "de"]
    out = session(monkeypatch, capsys, walls + ["pass", "pass"],
                  GameConfig(6, False, ("human", "human")))
    assert "Black ● plays D1." in out and "White ○ plays E6." in out
    assert "Black ● passes." in out and "White ○ passes." in out
    assert out.endswith("Game over: every player passed.\n"
                        "Black wins.\nScores: Black 24, White 12\n")

def test_human_against_bot_to_the_end(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a person who keeps passing plays a smart bot to the end"""
    out = session(monkeypatch, capsys, ["pass"] * 200,
                  GameConfig(6, False, ("human", "smart")))
    assert "White ○ plays " in out
    assert "Game over: every player passed.\nWhite wins.\n" in out

def test_watch_bots_from_the_menu(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check watch bots presets two bots, paces and prints every move, and
    returns to the menu"""
    delays: list[float] = []
    monkeypatch.setattr(tui, "BOT_DELAY_S", 0.25)
    monkeypatch.setattr(time, "sleep", delays.append)
    random.seed(3)
    out = session(monkeypatch, capsys, ["2", "6", "super", "", "", "", "3"])
    assert "Black: human, random or smart [smart]: " in out
    assert "White: human, random or smart [random]: " in out
    assert "Press Ctrl+C to stop watching." in out
    turns = re.findall(r"(?:Black ●|White ○) (?:plays [A-F][1-6]|passes)\.",
                       out)
    assert len(turns) == len(delays) > 0 and set(delays) == {0.25}
    assert "Game over: " in out
    assert out.count("Choose [1]: ") == 2

def test_four_seats_from_the_menu(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check Red and Blue join when given a seat, and quit leaves the match
    with every player's score"""
    out = session(monkeypatch, capsys,
                  ["1", "", "", "", "human", "random", "random", "quit"])
    assert "Board size, 6 to 30 [19]: " in out
    assert "Red: human, random, smart or none [none]: " in out
    assert "   A B C D E F G H J K L M N O P Q R S T\n19 · " in out
    assert "Game over: the match was left.\nNo winner.\n" \
           "Scores: Black 0, White 0, Red 0, Blue 0\n" in out

def test_hint_suggests_a_point_or_a_pass(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a hint names a point, and says pass when only eyes are left"""
    out = session(monkeypatch, capsys, ["hint", "quit"],
                  GameConfig(6, False, ("human", "human")))
    assert re.search(r"Hint: [A-F][1-6]\n", out)

    monkeypatch.setattr(tui.Match, "hint", lambda self: None)
    out = session(monkeypatch, capsys, ["hint", "quit"],
                  GameConfig(6, False, ("human", "human")))
    assert "Hint: pass\n" in out

def test_taken_and_illegal_points_get_their_own_message(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a taken point and a suicide each say why and ask again"""
    out = session(monkeypatch, capsys,
                  ["a2", "a2", "f6", "b1", "a1", "quit"],
                  GameConfig(6, False, ("human", "human")))
    assert "White ○ to play (e.g. D4, pass, hint, quit): " \
           "A2 already has a stone.\n" in out
    assert "A1 is not allowed: it would leave your stones with no liberty " \
           "or repeat the board (ko).\n" in out

def test_ko_retake_is_refused(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check retaking a ko at once is refused with the same message"""
    # Black takes at C3 and White may not take straight back at B3
    moves = ["b4", "c4", "a3", "d3", "b2", "c2", "f6", "b3", "c3", "b3",
             "quit"]
    out = session(monkeypatch, capsys, moves,
                  GameConfig(6, False, ("human", "human")))
    assert "B3 is not allowed: it would leave your stones with no liberty " \
           "or repeat the board (ko).\n" in out

def test_tie_names_every_winner(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a tie lists all the tied players"""
    out = session(monkeypatch, capsys, ["pass"] * 3,
                  GameConfig(6, False, ("human",) * 3))
    assert "Tie between Black, White and Red.\n" in out

def test_menu_and_setup_explain_a_bad_answer(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a bad menu choice, ko rule or seat is explained and asked
    again"""
    out = session(monkeypatch, capsys,
                  ["9", "play", "seven", "6", "none", "simple",
                   "alien", "", "", "", "", "", "quit", "3"])
    assert "Please type 1, 2 or 3.\n" in out
    assert "size must be a whole number from 6 to 30\n" in out
    assert "Please type simple or super.\n" in out
    assert "seats must be 2 to 4 of human, random, smart\n" in out
    assert out.count("Black: human, random or smart [human]: ") == 2
    assert "Game over: the match was left." in out

#
# Leaving
#

@pytest.mark.parametrize("typed", range(9))
def test_end_of_input_at_any_prompt_leaves_cleanly(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str], typed: int) -> None:
    """Check Ctrl+D at the menu, in setup or in a match returns quietly"""
    lines = ["1", "6", "", "", "", "", "c3", "hint", "d4"]
    out = session(monkeypatch, capsys, lines[:typed])
    assert out.endswith("\n")
    assert ("Game over: the match was left." in out) == (typed >= 6)

def test_ctrl_c_in_a_match_aborts_it(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check Ctrl+C at a person's prompt or during a bot's pause ends the
    match with no winner and prints the result"""
    def interrupt(*args: object) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrupt)
    tui.run(GameConfig(6, False, ("human", "smart")))
    assert "Game over: the match was left.\nNo winner.\n" in \
           capsys.readouterr().out

    monkeypatch.setattr(time, "sleep", interrupt)
    tui.run(GameConfig(6, False, ("smart", "random")))
    out = capsys.readouterr().out
    assert "Game over: the match was left.\nNo winner.\n" in out
    assert " plays " not in out

def test_ctrl_c_at_the_menu_leaves(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check Ctrl+C at the menu returns instead of raising"""
    def interrupt(*args: object) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrupt)
    tui.run()
    assert capsys.readouterr().out.endswith("\n")

def test_tui_never_imports_pygame() -> None:
    """Check the TUI loads without pygame, in a fresh interpreter"""
    subprocess.run([sys.executable, "-c",
                    "import go_python.tui, sys; "
                    "assert 'pygame' not in sys.modules"], check=True)

#
# Regressions
#

def test_regression_10_10_on_19x19_gets_a_message(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check "10 10" on 19x19 is answered, not silently asked again"""
    out = session(monkeypatch, capsys, ["10 10", "K10", "quit"],
                  GameConfig(19, False, ("human", "human")))
    assert "(e.g. D4, pass, hint, quit): " + NOT_A_MOVE + "\n" in out
    assert "Black ● plays K10." in out

def test_regression_9_9_on_9x9_gets_a_message(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check "9 9" and points past the edge of 9x9 are answered, not a
    crash"""
    out = session(monkeypatch, capsys, ["9 9", "J10", "K9", "J9", "quit"],
                  GameConfig(9, False, ("human", "human")))
    assert NOT_A_MOVE in out
    assert "J10 is off the board" in out and "K9 is off the board" in out
    assert "Black ● plays J9." in out

def test_regression_hint_answers_within_a_second_on_19x19(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a hint on 19x19 comes back in under a second"""
    start = time.perf_counter()
    out = session(monkeypatch, capsys, ["hint", "quit"],
                  GameConfig(19, False, ("human", "human")))
    assert time.perf_counter() - start < 1
    assert re.search(r"Hint: [A-T]\d+\n", out)

def test_regression_colour_reset_is_never_black() -> None:
    """Check every coloured stone resets to the terminal's colour, never
    black, so the board stays visible on a dark terminal"""
    game = Go(6, 4)
    for pos in [(0, 0), (0, 1), (0, 2), (0, 3)]:
        game.apply_move(pos)
    text = board_text(game)
    assert Fore.BLACK not in text
    assert text.count(Fore.RESET) == 2
    assert all(stone.endswith(Fore.RESET) for stone in tui.STONES[2:])

def test_regression_bad_board_size_is_asked_again(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a size out of range is refused by GameConfig and asked again"""
    out = session(monkeypatch, capsys, ["1", "5", "31", "6", "", "", "",
                                        "", "quit", "3"])
    assert out.count("size must be a whole number from 6 to 30\n") == 2
    assert out.count("Board size, 6 to 30 [19]: ") == 3
    assert " 6 · · · · · · 6" in out
