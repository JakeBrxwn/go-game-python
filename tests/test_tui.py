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
from go_python.tui import STONES, Command, board_text, parse_command

NOT_A_MOVE = "Not a move: type a column letter then a row number, like D4."
NO_I = "There is no column I: Go boards skip it, so J follows H."
NOT_ALLOWED = "is not allowed: your stones would have no liberty, or ko " \
              "forbids it.\n"
RED, BLUE = f"Red {STONES[2]}", f"Blue {STONES[3]}"

@pytest.fixture(autouse=True)
def no_bot_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lets bots move at once in every test"""
    monkeypatch.setattr(tui, "BOT_DELAY_S", 0)

def session(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
            lines: list[str], config: GameConfig | None = None) -> str:
    """
    Runs the TUI with typed lines, then end of input, and checks no line on
    screen is wider than 80 columns.

    Args:
        monkeypatch: Replaces input() with the typed lines
        capsys: Captures the screen: output, prompts and what was typed
        lines: What the person types, one entry per Enter; "^C" is Ctrl+C
        config: The settings of one match, or None for the menu

    Returns: Everything on screen
    """
    typed = iter(lines)

    def type_line(prompt: str) -> str:
        print(prompt, end="")
        line = next(typed, None)
        if line is None:
            raise EOFError
        print(line)
        if line == "^C":
            raise KeyboardInterrupt
        return line

    monkeypatch.setattr("builtins.input", type_line)
    tui.run(config)
    out = capsys.readouterr().out
    shown = re.sub(r"\x1b\[[0-9;]*m", "", out)
    assert max(len(line) for line in shown.splitlines()) <= 80
    return out

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
    """Check the letters printed over each point, read top to bottom, and
    the row numbers beside it name that point, on every size, within 80
    columns"""
    lines = board_text(Go(side, 2)).splitlines()
    head = (len(lines) - side) // 2
    letters, rows = lines[:head], lines[head:head + side]
    assert lines[-head:] == letters and head in (1, 2)
    assert max(len(line) for line in lines) <= 80
    points = [i for i, ch in enumerate(rows[0]) if ch == "·"]
    columns = ["".join(line[i] for line in letters).strip() for i in points]
    assert len(columns) == side and "I" not in columns
    for r, line in enumerate(rows):
        number = line.split()[0]
        assert line.split()[-1] == number
        assert [i for i, ch in enumerate(line) if ch == "·"] == points
        for c, column in enumerate(columns):
            assert parse_command(column + number, side) == (r, c)

def test_each_player_has_a_shape_of_their_own() -> None:
    """Check four players' stones differ without colour and land on the
    points that name them"""
    shapes = [re.sub(r"\x1b\[[0-9;]*m", "", stone) for stone in STONES]
    assert len(set(shapes)) == 4 and all(len(s) == 1 for s in shapes)
    game = Go(6, 4)
    for pos in [(0, 0), (0, 5), (5, 0), (5, 5)]:
        game.apply_move(pos)
    lines = board_text(game).splitlines()
    assert lines[1].startswith(" 6 ●") and lines[1].endswith("○ 6")
    assert lines[6].startswith(" 1 " + STONES[2])
    assert lines[6].endswith(STONES[3] + " 1")

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
    assert out.startswith("\nBoard 6x6: columns A to F, rows 1 to 6. "
                          "Ko rule: simple.\nBlack ● human, White ○ human\n")
    assert "Black ● plays D1." in out and "White ○ plays E6." in out
    assert "Black ● passes." in out and "White ○ passes." in out
    assert out.endswith("Game over: every player passed.\nBlack ● wins.\n"
                        "Scores: Black ● 24, White ○ 12\n")

def test_human_against_bot_to_the_end(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a person who keeps passing plays a smart bot to the end"""
    out = session(monkeypatch, capsys, ["pass"] * 200,
                  GameConfig(6, True, ("human", "smart")))
    assert "Ko rule: superko.\nBlack ● human, White ○ smart\n" in out
    assert "White ○ plays " in out
    assert "Game over: every player passed.\nWhite ○ wins.\n" in out

def test_watch_bots_from_the_menu(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check watch bots presets two bots on 9x9, paces and prints every
    move, and returns to the menu"""
    delays: list[float] = []
    monkeypatch.setattr(tui, "BOT_DELAY_S", 0.25)
    monkeypatch.setattr(time, "sleep", delays.append)
    random.seed(3)
    out = session(monkeypatch, capsys,
                  ["2", "", "", "", "none", "", "", "3"])
    assert "Board size, 6 to 30 [9]: \n" in out
    assert "Black player: random bot or smart bot [smart]: \n" in out
    assert "White player: random bot or smart bot [random]: none\n" \
           "White must play: type random bot or smart bot.\n" in out
    assert "Red player: random bot, smart bot or none [none]: \n" in out
    assert "Board 9x9: columns A to J, rows 1 to 9. Ko rule: simple.\n" \
           "Black ● smart, White ○ random\n" \
           "Press Ctrl+C to stop watching.\n" in out
    turns = re.findall(r"(?:Black ●|White ○) (?:plays [A-J][1-9]|passes)\.",
                       out)
    assert len(turns) == len(delays) > 0 and set(delays) == {0.25}
    assert "Game over: " in out
    assert out.count("Choose [1]: ") == 2

def test_four_seats_on_the_largest_board(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check Red and Blue join when given a seat, a 30x30 board fits and
    says how to read its two-letter columns, and quit leaves the match with
    every player's score"""
    out = session(monkeypatch, capsys, ["1", "30", "", "", "human", "random",
                                        "Random Bot", "quit"])
    assert "Red player: human, random bot, smart bot or none [none]: " \
           "random\n" in out
    assert "Board 30x30: columns A to AE, rows 1 to 30. Ko rule: simple.\n" \
           "Columns after Z have two letters, read top to bottom.\n" \
           f"Black ● human, White ○ human, {RED} random, {BLUE} random\n" \
           in out
    assert " Z A B C D E\n30 · " in out
    assert "Game over: the match was left.\nNo winner.\n" \
           f"Scores: Black ● 0, White ○ 0, {RED} 0, {BLUE} 0\n" in out

def test_hint_suggests_a_point_or_a_pass(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a hint names a point, and says pass when only eyes are left"""
    out = session(monkeypatch, capsys, ["hint", "quit"],
                  GameConfig(6, False, ("human", "human")))
    assert re.search(r"hint\nHint: [A-F][1-6]\n", out)

    monkeypatch.setattr(tui.Match, "hint", lambda self: None)
    out = session(monkeypatch, capsys, ["hint", "quit"],
                  GameConfig(6, False, ("human", "human")))
    assert "hint\nHint: pass\n" in out

def test_taken_and_illegal_points_get_their_own_message(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a taken point and a suicide each say why and ask again"""
    out = session(monkeypatch, capsys,
                  ["a2", "a2", "f6", "b1", "a1", "quit"],
                  GameConfig(6, False, ("human", "human")))
    assert "White ○ to play (e.g. D4, pass, hint, quit): a2\n" \
           "A2 already has a stone.\n" in out
    assert "a1\nA1 " + NOT_ALLOWED in out

def test_ko_retake_is_refused(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check retaking a ko at once is refused with the same message"""
    # Black takes at C3 and White may not take straight back at B3
    moves = ["b4", "c4", "a3", "d3", "b2", "c2", "f6", "b3", "c3", "b3",
             "quit"]
    out = session(monkeypatch, capsys, moves,
                  GameConfig(6, False, ("human", "human")))
    assert "B3 " + NOT_ALLOWED in out

def test_tie_names_every_winner(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a tie lists all the tied players with their stones"""
    out = session(monkeypatch, capsys, ["pass"] * 3,
                  GameConfig(6, False, ("human",) * 3))
    assert f"Tie between Black ●, White ○ and {RED}.\n" in out

def test_menu_and_setup_explain_a_bad_answer(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a bad menu choice, size or ko rule is explained and asked
    again"""
    out = session(monkeypatch, capsys,
                  ["9", "play", "seven", "6", "none", "simple", "", "", "",
                   "quit", "3"])
    assert "Choose [1]: 9\nPlease type 1, 2 or 3.\n" in out
    assert "[19]: seven\nsize must be a whole number from 6 to 30\n" in out
    assert "[simple]: none\nPlease type simple or superko.\n" in out
    assert "Game over: the match was left." in out

def test_bad_seat_is_refused_at_once(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check GameConfig refuses a bad seat as soon as it is typed, and the
    same player is asked again; Black and White may not be none"""
    out = session(monkeypatch, capsys,
                  ["1", "6", "", "robot", "none", "random", "Smart bot",
                   "dog", "", "quit", "3"])
    bots = "random bot or smart bot"
    black = f"Black player: human, {bots} [human]: "
    white = f"White player: human, {bots} [smart]: "
    red = "Red player: human, random bot, smart bot or none [none]: "
    assert f"{black}robot\nrobot is not a choice: type human, {bots}.\n" \
           f"{black}none\nBlack must play: type human, {bots}.\n" \
           f"{black}random\n{white}Smart bot\n{red}dog\n" \
           "dog is not a choice: type human, random bot, smart bot or none.\n" \
           f"{red}\n" in out
    assert "Black ● random, White ○ smart\n" in out

@pytest.mark.parametrize("typed, rule", [
    ("", "simple"),
    ("Simple", "simple"),
    ("simple ko", "simple"),
    ("super", "superko"),
    ("superko", "superko"),
    ("Super Ko", "superko"),
])
def test_ko_rule_takes_its_usual_spellings(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
        typed: str, rule: str) -> None:
    """Check simple and superko are understood however they are spelt"""
    out = session(monkeypatch, capsys,
                  ["1", "6", typed, "", "", "", "quit", "3"])
    assert f"Ko rule: {rule}.\n" in out

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
    # Leaving setup or a match shows the menu again before Ctrl+D leaves it
    assert out.count("Choose [1]: ") == (1 if typed == 0 else 2)

def test_ctrl_c_in_a_match_aborts_it(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check Ctrl+C at a person's prompt or during a bot's pause ends the
    match with no winner and prints the result"""
    out = session(monkeypatch, capsys, ["^C"],
                  GameConfig(6, False, ("human", "smart")))
    assert "Game over: the match was left.\nNo winner.\n" in out

    def interrupt(*args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(time, "sleep", interrupt)
    tui.run(GameConfig(6, False, ("smart", "random")))
    out = capsys.readouterr().out
    assert "Game over: the match was left.\nNo winner.\n" in out
    assert " plays " not in out

def test_ctrl_c_at_the_menu_leaves(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check Ctrl+C at the menu returns instead of raising"""
    out = session(monkeypatch, capsys, ["^C", "1"])
    assert out.endswith("Choose [1]: ^C\n\n")

@pytest.mark.parametrize("blanks", range(4))
def test_ctrl_c_in_setup_goes_back_to_the_menu(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
        blanks: int) -> None:
    """Check Ctrl+C at any setup question returns to the menu, as it does
    in a match"""
    out = session(monkeypatch, capsys, ["1", *[""] * blanks, "^C", "3"])
    assert out.count("Choose [1]: ") == 2 and "Board 19x19" not in out
    assert out.endswith("^C\n\n\nGo Python: 1) play  2) watch bots  3) quit\n"
                        "Choose [1]: 3\n")

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
    assert "quit): 10 10\n" + NOT_A_MOVE + "\n" in out
    assert "Black ● plays K10." in out

def test_regression_9_9_on_9x9_gets_a_message(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check "9 9" and points past the edge of 9x9 are answered, not a
    crash"""
    out = session(monkeypatch, capsys, ["9 9", "J10", "K9", "J9", "quit"],
                  GameConfig(9, False, ("human", "human")))
    assert "9 9\n" + NOT_A_MOVE in out
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
    assert all(stone.endswith(Fore.RESET) for stone in STONES[2:])

def test_regression_bad_board_size_is_asked_again(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check a size out of range is refused by GameConfig and asked again"""
    out = session(monkeypatch, capsys, ["1", "5", "31", "6", "", "", "",
                                        "", "quit", "3"])
    assert out.count("size must be a whole number from 6 to 30\n") == 2
    assert out.count("Board size, 6 to 30 [19]: ") == 3
    assert " 6 · · · · · · 6" in out

def test_regression_bytes_that_are_not_utf8_get_a_message(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check bytes that are not UTF-8, at the menu or a move prompt, get the
    usual message instead of a crash, through the real input()"""
    typed = b"\xff\n1\n6\n\n\n\n\n\xe9\nquit\n3\n"
    monkeypatch.setattr(sys, "stdin",
                        io.TextIOWrapper(io.BytesIO(typed), encoding="utf-8"))
    tui.run()
    out = capsys.readouterr().out
    assert "Choose [1]: Please type 1, 2 or 3.\n" in out
    assert "quit): " + NOT_A_MOVE + "\n" in out
    assert "Game over: the match was left." in out

def test_regression_a_terminal_without_utf8_stops_with_one_line(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a terminal that cannot show the stones gets one line naming the
    fix and a failing exit, before any prompt and with no traceback"""
    screen = io.TextIOWrapper(io.BytesIO(), encoding="latin-1")
    monkeypatch.setattr(sys, "stdout", screen)
    with pytest.raises(SystemExit) as leaving:
        tui.run()
    assert leaving.value.code == ("This terminal cannot show the stones: run "
                                  "it with a UTF-8 locale, such as "
                                  "LANG=C.UTF-8.")
    screen.flush()
    assert screen.buffer.getvalue() == b""
