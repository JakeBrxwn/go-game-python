"""
The text frontend: a prompt menu, setup questions, and a board printed before
every turn. Points are named Go style, a column letter then a row number such
as D4. It reads only with input(), writes only with print(), and never
imports pygame.
"""
import io
import re
import sys
import time
from enum import Enum

from colorama import Fore

from go_python.go import Go
from go_python.match import (PLAYER_NAMES, GameConfig, Match, MatchResult,
                             MatchState)

if sys.platform == "win32":  # pragma: no cover
    import msvcrt
else:
    import termios

#
# Display
#

# Seconds to wait before each bot move, so a person can follow the game
BOT_DELAY_S = 0.5

# Column labels: Go boards skip I, and boards over 25 go on with two letters
COLUMNS = (*"ABCDEFGHJKLMNOPQRSTUVWXYZ", "AA", "AB", "AC", "AD", "AE")

# Each player's stone: a shape of its own, so colour is only a help. A colour
# resets to the terminal's own, never to black, so the board stays readable
# on dark and light backgrounds.
STONES = ("●", "○", Fore.RED + "◆" + Fore.RESET,
          Fore.LIGHTBLUE_EX + "■" + Fore.RESET)

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
    on both sides, row 1 at the bottom. A two-letter column label stands in
    two rows, read top to bottom, so every size fits in 80 columns.

    Args:
        game: The game to draw

    Returns: The board as lines of text
    """
    side = game.side
    labels = [label.rjust(2) for label in COLUMNS[:side]]
    letters = ["   " + " ".join(label[i] for label in labels) for i in (0, 1)]
    letters = [line for line in letters if line.strip()]
    rows = [f"{side - r:>2} "
            + " ".join(STONES[piece - 1] if piece else "·" for piece in row)
            + f" {side - r}" for r, row in enumerate(game.grid)]
    return "\n".join(letters + rows + letters)

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
        return ("Not a move: type a column letter then a row number, like "
                "D4.")
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
            print(f"{_label(command, game.side)} is not allowed: your stones "
                  "would have no liberty, or ko forbids it.")
        else:
            return command

def _print_result(result: MatchResult) -> None:
    """
    Prints why the match ended, who won and every score.

    Args:
        result: How the match finished
    """
    names = [_who(player) for player in result.winners]
    print(f"Game over: {result.reason.value}.")
    if not names:
        print("No winner.")
    elif len(names) == 1:
        print(f"{names[0]} wins.")
    else:
        print(f"Tie between {', '.join(names[:-1])} and {names[-1]}.")
    print("Scores: " + ", ".join(f"{_who(player)} {score}"
                                 for player, score in result.scores.items()))

def _play_match(config: GameConfig) -> None:
    """
    Plays one match to its end, printing the board before every turn and
    each move as it is made. Quit, Ctrl+C or Ctrl+D ends it with no winner.

    Args:
        config: The settings of the match
    """
    match = Match(config)
    size = config.size
    print(f"\nBoard {size}x{size}: columns A to {COLUMNS[size - 1]}, rows 1 "
          f"to {size}. Ko rule: {'superko' if config.superko else 'simple'}.")
    if len(COLUMNS[size - 1]) > 1:
        print("Columns after Z have two letters, read top to bottom.")
    print(", ".join(f"{_who(player)} {seat}"
                    for player, seat in enumerate(config.seats, start=1)))
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
                                  f" plays {_label(pos, size)}."))
    except (KeyboardInterrupt, EOFError):
        print()
    match.abort()  # a finished match keeps its result
    assert match.result is not None
    print(board_text(match.game))
    _print_result(match.result)
    _drop_typeahead()

def _drop_typeahead() -> None:
    """
    Throws away keys pressed while the match ran, such as Enter or Ctrl+D
    while bots played, so they cannot answer the next question.
    """
    if not sys.stdin.isatty():
        return
    if sys.platform == "win32":  # pragma: no cover
        while msvcrt.kbhit():
            msvcrt.getwch()
    else:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)

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
    Asks what to do until the answer is a number, a choice or its first
    word.

    Returns: "play", "watch" or "quit"
    """
    choices = ("play", "watch bots", "quit")
    while True:
        print("\nGo Python: " + "  ".join(
            f"{number}) {choice}"
            for number, choice in enumerate(choices, start=1)))
        answer = _ask("Choose", "1")
        for number, choice in enumerate(choices, start=1):
            if answer in (str(number), choice, choice.split()[0]):
                return choice.split()[0]
        print("Please type 1, 2 or 3.")

def _ask_seat(name: str, default: str, offer: tuple[str, ...]) -> str:
    """
    Asks who sits in one player's seat until GameConfig accepts the answer.

    Args:
        name: The player's name
        default: The seat Enter gives. If it is "none", the player may stay
        out.
        offer: The seats the prompt lists, such as "random bot"

    Returns: "human", "random" or "smart", or "none" for no player
    """
    words = (*offer, "none") if default == "none" else offer
    kinds = ", ".join(words[:-1]) + " or " + words[-1]
    while True:
        seat = _ask(f"{name} player: {kinds}", default).removesuffix(" bot")
        if seat == default == "none":
            return seat
        try:
            # Two of the seat, so GameConfig judges this one answer
            return GameConfig(seats=(seat, seat)).seats[0]
        except ValueError:
            print(f"{name} must play: type {kinds}." if seat == "none"
                  else f"{seat} is not a choice: type {kinds}.")

def _setup(size: str, defaults: tuple[str, str],
           offer: tuple[str, ...]) -> GameConfig:
    """
    Asks for the board size, the ko rule and a seat per player. GameConfig
    checks every answer; a refused answer is asked again with a message.

    Args:
        size: The board size Enter gives
        defaults: The seats Enter gives Black and White. Red and Blue
        default to none, which ends the list of players.
        offer: The seats each prompt lists

    Returns: The settings
    """
    print("Press Enter to keep the answer in brackets.")
    while True:
        answer = _ask("Board size, 6 to 30", size)
        try:
            # Text that is not a number of at most three digits becomes 0,
            # which GameConfig refuses, so int() never meets a huge number
            config = GameConfig(int(answer) if answer.isdecimal()
                                and len(answer) <= 3 else 0)
            break
        except ValueError as err:
            print(err)
    while True:
        # "superko", "super ko" and "super" all name the same rule
        ko = _ask("Ko rule, simple or superko", "simple")
        ko = ko.replace(" ", "").removesuffix("ko")
        if ko in ("simple", "super"):
            break
        print("Please type simple or superko.")
    seats: list[str] = []
    for name, default in zip(PLAYER_NAMES, defaults + ("none", "none"),
                             strict=True):
        seat = _ask_seat(name, default, offer)
        if seat == "none":
            break
        seats.append(seat)
    return GameConfig(config.size, ko == "super", tuple(seats))

# What setup starts from for each menu choice: the board size, Black's and
# White's seats, and the seats on offer. Watching starts small, since a
# 19x19 bot game takes minutes.
PRESETS = {"play": ("19", ("human", "smart"),
                    ("human", "random bot", "smart bot")),
           "watch": ("9", ("smart", "random"), ("random bot", "smart bot"))}

def run(config: GameConfig | None = None) -> None:
    """
    Runs the text frontend. Ctrl+D or Ctrl+C in setup goes back to the
    menu, and at the menu leaves.

    Raises:
        SystemExit: If the terminal cannot show the stones, with a message.

    Args:
        config: The settings of one match to play before returning, or None
        to show the menu until the player quits
    """
    try:
        "".join(STONES).encode(sys.stdout.encoding or "utf-8")
    except UnicodeEncodeError:
        sys.exit("This terminal cannot show the stones: run it with a UTF-8 "
                 "locale, such as LANG=C.UTF-8.")
    # Bytes that are not UTF-8 become a bad answer instead of a crash
    if isinstance(sys.stdin, io.TextIOWrapper):
        sys.stdin.reconfigure(errors="replace")
    try:
        if config is not None:
            _play_match(config)
            return
        while (choice := _menu()) != "quit":
            try:
                _play_match(_setup(*PRESETS[choice]))
            except (EOFError, KeyboardInterrupt):
                print()
    except (EOFError, KeyboardInterrupt):
        print()
