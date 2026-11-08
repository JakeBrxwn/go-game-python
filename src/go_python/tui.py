"""
The text frontend: a prompt menu, setup questions, and a board printed before
every turn. Points are named Go style, a column letter then a row number such
as D4. It reads only with input(), writes only with print(), and never
imports pygame.
"""
import re
import time
from enum import Enum

from colorama import Fore

from go_python.go import Go
from go_python.match import (PLAYER_NAMES, GameConfig, Match, MatchResult,
                             MatchState)

#
# Display
#

# Seconds to wait before each bot move, so a person can follow the game
BOT_DELAY_S = 0.5

# Column labels: Go boards skip I, and boards over 25 go on with two letters
COLUMNS = (*"ABCDEFGHJKLMNOPQRSTUVWXYZ", "AA", "AB", "AC", "AD", "AE")

# Each player's stone. A colour is reset to the terminal's own colour, never
# to black, so the board stays readable on dark and light backgrounds.
STONES = ("●", "○", Fore.RED + "●" + Fore.RESET,
          Fore.LIGHTBLUE_EX + "●" + Fore.RESET)

def _label(pos: tuple[int, int], side: int) -> str:
    """
    Names a point the way the board labels it.

    Args:
        pos: Row and column on the board, counted from the top left
        side: The size of the board

    Returns: The column letter and row number, such as "D4"
    """
    return f"{COLUMNS[pos[1]]}{side - pos[0]}"

def _who(player: int) -> str:
    """
    Names a player with their stone.

    Args:
        player: The player number, from 1

    Returns: The name and stone, such as "White ○"
    """
    return f"{PLAYER_NAMES[player - 1]} {STONES[player - 1]}"

def board_text(game: Go) -> str:
    """
    Draws the board with column letters above and below it and row numbers
    on both sides, row 1 at the bottom.

    Args:
        game: The game to draw

    Returns: The board as lines of text
    """
    side = game.side
    width = len(COLUMNS[side - 1])
    letters = "   " + " ".join(label.ljust(width) for label in COLUMNS[:side])
    lines = [letters]
    for r, row in enumerate(game.grid):
        points = (" " * width).join(STONES[piece - 1] if piece else "·"
                                    for piece in row)
        lines.append(f"{side - r:>2} {points} {side - r}")
    lines.append(letters)
    return "\n".join(lines)

#
# Commands
#

class Command(Enum):
    """
    A word typed instead of a move.
    """
    PASS = "pass"
    HINT = "hint"
    QUIT = "quit"

def parse_command(text: str, side: int) -> tuple[int, int] | Command | str:
    """
    Reads what a person typed on their turn. Case does not matter.

    Args:
        text: The typed line, such as "d4", "Q16" or "pass"
        side: The size of the board

    Returns: The row and column of a move, a Command, or a message saying
    what is wrong with the text
    """
    word = text.strip().upper()
    if word in Command.__members__:
        return Command[word]
    # At most three digits, so int() never meets a huge number
    found = re.fullmatch(r"([A-Z]+) ?([0-9]{1,3})", word)
    if found is None:
        return ("Not a move: type a column letter and a row number, like D4, "
                "or pass, hint or quit.")
    letters, number = found.groups()
    if letters == "I":
        return "There is no column I: Go boards skip it, so J follows H."
    if letters not in COLUMNS[:side] or not 1 <= int(number) <= side:
        return (f"{letters}{number} is off the board: columns run "
                f"A to {COLUMNS[side - 1]} and rows 1 to {side}.")
    return side - int(number), COLUMNS.index(letters)

#
# Match
#

def _ask_move(match: Match) -> tuple[int, int] | Command:
    """
    Asks the person whose turn it is until they give a legal move, pass or
    quit. Hints and mistakes are answered on the way.

    Args:
        match: The match, waiting for a person

    Returns: The legal move, Command.PASS or Command.QUIT
    """
    game = match.game
    while True:
        command = parse_command(
            input(f"{_who(game.turn)} to play (e.g. D4, pass, hint, quit): "),
            game.side)
        if isinstance(command, str):
            print(command)
        elif command is Command.HINT:
            hint = match.hint()
            print("Hint: " + ("pass" if hint is None
                              else _label(hint, game.side)))
        elif not isinstance(command, tuple):
            return command
        elif game.piece_at(command) is not None:
            print(f"{_label(command, game.side)} already has a stone.")
        elif not game.legal_move(command):
            print(f"{_label(command, game.side)} is not allowed: it would "
                  "leave your stones with no liberty or repeat the board "
                  "(ko).")
        else:
            return command

def _print_result(result: MatchResult) -> None:
    """
    Prints why the match ended, who won and every score.

    Args:
        result: How the match finished
    """
    names = [PLAYER_NAMES[player - 1] for player in result.winners]
    print(f"Game over: {result.reason.value}.")
    if not names:
        print("No winner.")
    elif len(names) == 1:
        print(f"{names[0]} wins.")
    else:
        print(f"Tie between {', '.join(names[:-1])} and {names[-1]}.")
    print("Scores: " + ", ".join(f"{PLAYER_NAMES[player - 1]} {score}"
                                 for player, score in result.scores.items()))

def play_match(config: GameConfig) -> None:
    """
    Plays one match to its end, printing the board before every turn and
    each move as it is made. Quit, Ctrl+C or Ctrl+D ends it with no winner.

    Args:
        config: The settings of the match
    """
    match = Match(config)
    if "human" not in config.seats:
        print("Press Ctrl+C to stop watching.")
    try:
        while match.state is not MatchState.FINISHED:
            print(board_text(match.game))
            player = match.game.turn
            if match.state is MatchState.BOT_TURN:
                time.sleep(BOT_DELAY_S)
                pos = match.step()
            else:
                command = _ask_move(match)
                if command is Command.QUIT:
                    break
                pos = command if isinstance(command, tuple) else None
                match.play(pos)
            print(_who(player) + (" passes." if pos is None else
                                  f" plays {_label(pos, config.size)}."))
    except (KeyboardInterrupt, EOFError):
        print()
    match.abort()  # a finished match keeps its result
    assert match.result is not None
    print(board_text(match.game))
    _print_result(match.result)

#
# Menu and setup
#

def _ask(question: str, default: str) -> str:
    """
    Asks a question, keeping the default on Enter.

    Args:
        question: The question, without the default
        default: The answer Enter gives

    Returns: The answer in lower case, trimmed
    """
    return input(f"{question} [{default}]: ").strip().lower() or default

def _menu() -> str:
    """
    Asks what to do until the answer is one of the choices.

    Returns: "play", "watch" or "quit"
    """
    while True:
        print("\nGo Python: 1) play  2) watch bots  3) quit")
        answer = _ask("Choose", "1")
        for number, choice in enumerate(("play", "watch", "quit"), start=1):
            if answer in (str(number), choice):
                return choice
        print("Please type 1, 2 or 3.")

def _setup(defaults: tuple[str, str]) -> GameConfig:
    """
    Asks for the board size, the ko rule and a seat per player. GameConfig
    checks every answer; a refused answer is asked again with its message.

    Args:
        defaults: The seats Enter gives Black and White. Red and Blue
        default to none, which ends the list of players.

    Returns: The settings
    """
    print("Press Enter to keep the answer in brackets.")
    while True:
        answer = _ask("Board size, 6 to 30", "19")
        try:
            # Text that is not a number becomes 0, which GameConfig refuses
            config = GameConfig(int(answer) if answer.isdecimal() else 0)
            break
        except ValueError as err:
            print(err)
    while (ko := _ask("Ko rule, simple or super", "simple")) not in (
            "simple", "super"):
        print("Please type simple or super.")
    while True:
        seats: list[str] = []
        for name, default in zip(PLAYER_NAMES, defaults + ("none", "none"),
                                 strict=True):
            kinds = ("human, random, smart or none" if default == "none"
                     else "human, random or smart")
            seat = _ask(f"{name} player: {kinds}", default)
            if seat == "none":
                break
            seats.append(seat)
        try:
            return GameConfig(config.size, ko == "super", tuple(seats))
        except ValueError as err:
            print(err)

def run(config: GameConfig | None = None) -> None:
    """
    Runs the text frontend. Ctrl+D or Ctrl+C at the menu or in setup leaves.

    Args:
        config: The settings of one match to play before returning, or None
        to show the menu until the player quits
    """
    try:
        if config is not None:
            play_match(config)
            return
        while (choice := _menu()) != "quit":
            play_match(_setup(("smart", "random") if choice == "watch"
                              else ("human", "smart")))
    except (EOFError, KeyboardInterrupt):
        print()
