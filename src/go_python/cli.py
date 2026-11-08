"""
The go-python command. It is the only code that reads command-line arguments.
"""
import click

from go_python import __version__
from go_python.match import GameConfig, run_series

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

@click.group()
@click.version_option(__version__, prog_name="go-python")
def main() -> None:
    """
    Go Python: the board game Go, for humans and bots.
    """

@main.command()
@click.option('-n', '--num-games', type=click.IntRange(min=1), default=20,
              help="The number of games to play.")
@click.option('-s', '--size', type=click.INT, default=6,
              help="The size of the board.")
@click.option('-1', '--player1',
              type=click.Choice(['random', 'smart'], case_sensitive=False),
              default='random')
@click.option('-2', '--player2',
              type=click.Choice(['random', 'smart'], case_sensitive=False),
              default='random')
def bots(num_games: int, size: int, player1: str, player2: str) -> None:
    """
    Plays bot-only games with no display and prints the totals. For testing.

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
