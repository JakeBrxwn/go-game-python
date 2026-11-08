"""
The go-python commands. They are the only code that reads command-line
arguments.
"""
from collections.abc import Callable

import click

from go_python import __version__, tui
from go_python.match import SEAT_KINDS, GameConfig, run_series

BOT_KINDS = [kind for kind in SEAT_KINDS if kind != "human"]

#
# Settings of one match
#

# The options of the commands that start one match, outermost first
MATCH_OPTIONS = [
    click.option('-s', '--size', type=click.INT, default=19,
                 show_default=True, help="The size of the board, 6 to 30."),
    click.option('--ko',
                 type=click.Choice(['simple', 'super'], case_sensitive=False),
                 default='simple', show_default=True, help="The ko rule."),
    click.option('--seats', default='human,smart', show_default=True,
                 help="One per player, in turn order, separated by commas: "
                      "human, random or smart."),
]

def match_options(command: Callable[..., None]) -> Callable[..., None]:
    """
    Adds the options that start one match: size, ko and seats.

    Args:
        command: The command function

    Returns: The command function with the options
    """
    for option in reversed(MATCH_OPTIONS):
        command = option(command)
    return command

def make_config(size: int, superko: bool,
                seats: tuple[str, ...]) -> GameConfig:
    """
    Builds the settings of a match, turning a bad setting into a usage error.

    Args:
        size: The size of the board
        superko: True for superko, False for simple ko
        seats: One entry per player: human, random or smart

    Raises:
        click.UsageError: If GameConfig refuses a setting. Click exits 2.

    Returns: The settings
    """
    try:
        return GameConfig(size, superko, seats)
    except ValueError as err:
        raise click.UsageError(str(err)) from err

def match_config(size: int, ko: str, seats: str) -> GameConfig:
    """
    Builds the settings of one match from the match options.

    Args:
        size: The size of the board
        ko: "simple" or "super"
        seats: Seats separated by commas

    Returns: The settings
    """
    return make_config(size, ko == "super",
                       tuple(seat.strip().lower() for seat in seats.split(",")))

#
# go-python
#

@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="go-python")
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    Go Python: the board game Go, for humans and bots. With no command it
    opens the game window.
    \f
    Args:
        ctx: Click's context, which names the command given, if any
    """
    if ctx.invoked_subcommand is None:
        # Imported here so the terminal commands never load pygame
        from go_python import gui
        gui.run()

@main.command(name="gui")
@match_options
def gui_match(size: int, ko: str, seats: str) -> None:
    """
    Starts one match in the window, skipping the menu. For testing.
    \f
    Args:
        size: The size of the board
        ko: "simple" or "super"
        seats: Seats separated by commas
    """
    config = match_config(size, ko, seats)
    from go_python import gui
    gui.run(config)

@main.command(name="tui")
@match_options
def tui_match(size: int, ko: str, seats: str) -> None:
    """
    Plays one match in the terminal, skipping the menu. For testing.
    \f
    Args:
        size: The size of the board
        ko: "simple" or "super"
        seats: Seats separated by commas
    """
    tui.run(match_config(size, ko, seats))

@main.command()
@click.option('-n', '--num-games', type=click.IntRange(min=1), default=20,
              show_default=True, help="The number of games to play.")
@click.option('-s', '--size', type=click.INT, default=6, show_default=True,
              help="The size of the board, 6 to 30.")
@click.option('-1', '--player1',
              type=click.Choice(BOT_KINDS, case_sensitive=False),
              default='random', show_default=True,
              help="The bot that moves first.")
@click.option('-2', '--player2',
              type=click.Choice(BOT_KINDS, case_sensitive=False),
              default='random', show_default=True,
              help="The bot that moves second.")
def bots(num_games: int, size: int, player1: str, player2: str) -> None:
    """
    Plays bot-only games with no display and prints the totals. For testing.
    \f
    Args:
        num_games: Number of games to play
        size: The size of the board
        player1: The bot that moves first
        player2: The bot that moves second
    """
    config = make_config(size, False, (player1, player2))
    series = run_series(config, num_games)

    print(f'Player 1 wins: {round(100 * series.wins[1] / num_games, 2)}%')
    print(f'Player 2 wins: {round(100 * series.wins[2] / num_games, 2)}%')
    print(f'Ties: {round(100 * series.ties / num_games, 2)}%')
    print('Average moves:', series.moves / num_games)

#
# go-python-tui
#

@click.command()
@click.version_option(__version__, prog_name="go-python-tui")
def tui_main() -> None:
    """
    Go Python in the terminal: play or watch Go by typing moves.
    """
    tui.run()
