"""
TUI for Go
"""
import sys
import time
from typing import Optional

import click
from colorama import Fore, Style

from go_python.base import GoBase, BoardGridType
from go_python.go import Go
from go_python.bot import Smart

colors: dict[int, tuple[str, str]] = {1 : (Fore.RED, 'Red'),
        2 : (Fore.BLUE, 'Blue'), 3 : (Fore.GREEN, 'Green'),
        4 : (Fore.BLACK, 'Black'), 5 : (Fore.WHITE, 'White'),
        6 : (Fore.YELLOW, 'Yellow'), 7 : (Fore.CYAN, 'Cyan'),
        8 : (Fore.MAGENTA, 'Magenta')}

def get_move(go_game: GoBase) -> Optional[tuple[int, int]]:
    """
    Gets a valid move from the player whose turn it is
    by prompting that player for a row and colunmn.

    Args:
        go_game: The current game of Go

    Returns: a tuple of ints representing the player's selection
        or None if they passed the turn
    """
    while True:
        text = "It is {}'s turn. Please enter a move [press Enter key to pass or type 'hint' for a hint]:\n> "
        response = input(text.format(colors[go_game.turn][1].lower()))
        if response == "hint":
            smart = Smart("smart-bot")
            suggested_move = smart.move(go_game, go_game.turn)
            if suggested_move is None:
                print("Pass your turn")
            else:
                print(f"Suggested Move: {suggested_move[0], suggested_move[1]}")
            continue
        elif len(response) == 3 and response[0].isnumeric() and \
           response[1] == " " and response[2].isnumeric() and \
           go_game.legal_move((int(response[0]), int(response[2]))):
            return int(response[0]), int(response[2])
        elif response == "":
            return None

def print_board(grid: BoardGridType) -> None:
    """
    Prints the board to the screen

    Args:
        grid: The board to print

    Returns: None
    """
    n_rows, n_cols = len(grid), len(grid[0])

    for r in range(n_rows):
        row_str = ''
        for c in range(n_cols):
            piece = grid[r][c]
            if not piece:
                if c == 0:
                    if r == 0:
                        row_str += '┌─'
                    elif r == n_rows - 1:
                        row_str += '└─'
                    else:
                        row_str += '├─'
                elif c == n_cols - 1:
                    if r == 0:
                        row_str += '┐'
                    elif r == n_rows - 1:
                        row_str += '┘'
                    else:
                        row_str += '┤'
                else:
                    if r == 0:
                        row_str += '┬─'
                    elif r == n_rows - 1:
                        row_str += '┴─'
                    else:
                        row_str += '┼─'
            else:
                if c == n_cols - 1:
                    row_str += colors[piece][0] + '●' + Fore.BLACK
                else:
                    row_str += colors[piece][0] + '●' + Fore.BLACK + '─'

        print(row_str)
        if r != n_rows - 1:
            connecting = ''
            for _ in range(n_cols):
                connecting += '│ '
            print(connecting)

def play_go(go_game: GoBase) -> None:
    """
    Continuously asks the current player to make a move and updates
    the state of the board until the game ends.

    Args:
        go_game: The current game of Go
    """
    while not go_game.done:
        print_board(go_game.grid)
        valid_move = get_move(go_game)
        if valid_move is None:
            print(f'{colors[go_game.turn][1]} has passed their turn.')
            go_game.pass_turn()
        else:
            go_game.apply_move(valid_move)
    print_board(go_game.grid)

    winner_list = go_game.outcome
    if len(winner_list) == 1:
        print(f'The winner is {colors[winner_list[0]][1]}!')
    else:
        res = "It's a tie! The winners are "
        for i in range(len(winner_list) - 1):
            res += f'{colors[winner_list[i]][1]}, '
        print(res + f'and {colors[winner_list[len(winner_list) - 1]][1]}.')
    for player, score in go_game.scores().items():
        print(colors[player][1] + ': ' + str(score))

@click.command("tui")
@click.option("-n", "--num-players", default=2)
@click.option("-s", "--size", default=19)
@click.option("--simple-ko", is_flag=True)
@click.option("--super-ko", is_flag=True)
def cmd(num_players: int, size: int, simple_ko: bool, super_ko: bool) -> None:
    """
    Takes in command line parameters to adjust the details of the game.

    Args:
        num_players: The number of players
        size: The size of the board
        simple_ko: Whether or not the simple ko rule will apply
        super_ko: Whether or not the super ko rule will apply
    """

    if size < 6 or size > 30:
        print("Error: Please specify a board size between 6 and 30")
        sys.exit()
    ko_type = False
    if simple_ko:
        ko_type = True
    elif super_ko:
        ko_type = False
    go_game = Go(size, num_players, ko_type)

    play_go(go_game)

if __name__ == "__main__":
    cmd()
