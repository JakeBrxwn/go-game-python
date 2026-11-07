"""
Bot players for a go board.
"""
import random
import click
from go_python.go import Go

class Random:
    """
    Creates bots that can play the game with random moves.
    """

    _name: str
    wins: int

    def __init__(self, name: str, wins: int = 0):
        """
        Constructs a bot.

        Args:
            name: Bot name
            wins: amount of wins for the bot
        """
        self._name = name
        self.wins = wins

    def move(self, go_game: Go, turn: int) -> tuple[int, int] | None:
        """
        Tells the bot where to place.

        Returns:
            tuple: The coordinates of the move.
        """
        moveset = go_game.available_moves
        if len(moveset) != 0:
            return random.choice(moveset)
        return None

class Smart:
    """
    Creates a smart bot. Plays the game using a prediction algorithm.
    """

    _name: str
    wins: int

    def __init__(self, name: str, wins: int = 0):
        """
        Constructs a bot.

        Args:
            name: Bot name
            wins: amount of wins for the bot
        """
        self._name = name
        self.wins = wins

    def move(self, go_game: Go, turn: int) -> tuple[int, int] | None:
        """
        Tells the bot where to place based on what accumulates the most points.

        Returns:
            tuple: The coordinates of the decided move.
        """
        moveset = go_game.available_moves
        # Returns none to signify a pass if moveset is empty.
        if len(moveset) == 0:
            return None
        return max(moveset,
                   key=lambda move: go_game.simulate_move(move).scores()[turn])

def bots_only(bots: dict[str, Random | Smart], games: int, size: int) -> int:
    """
    Runs a few games of Go using only two bot players.

    Args:
        go_game: Go Game Board to play on.
        bots: Dictionary of bots that map bot names to a Bot object
        games: Number of games.
        size: Size of the board.

    Returns:
        int: Total moves accreted from every game simulated.
    """
    game_moves = 0
    all_moves = 0
    for _ in range(games):
        go = Go(size, 2)

        cur_player = bots['Bot1']

        while not go.done:
            if game_moves >= 256:
                break
            played_pos = cur_player.move(go, go.turn)
            if played_pos is not None:
                go.apply_move(played_pos)
            else:
                go.pass_turn()

            cur_player = (bots['Bot2'] if cur_player == bots['Bot1']
                          else bots['Bot1'])
            game_moves += 1

        if game_moves >= 256:
            scores = go.scores()
            if scores[1] > scores[2]:
                bots['Bot1'].wins += 1
            elif scores[1] < scores[2]:
                bots['Bot2'].wins += 1
        else:
            winner = go.outcome
            if len(winner) < 2:
                win_val = winner.pop()
                if win_val == 1:
                    bots['Bot1'].wins += 1
                else:
                    bots['Bot2'].wins += 1
        all_moves += game_moves
        game_moves = 0
    return all_moves


@click.command(name="Go-Bots")
@click.option('-n', '--num-games', type=click.INT, default=20)
@click.option('-s', '--size', type=click.INT, default=6)
@click.option('-1', '--player1',
              type=click.Choice(['random', 'smart'], case_sensitive=False),
              default='random')
@click.option('-2', '--player2',
              type=click.Choice(['random', 'smart'], case_sensitive=False),
              default='random')
def cmd(num_games: int, size: int, player1: str, player2: str) -> None:
    """
    Takes user input and starts the simulation.

    Args:
        games: Number of games to play
    """
    bots: dict[str, Random | Smart]
    bot_num_one: Random | Smart
    bot_num_two: Random | Smart

    # Instantiate bot players
    if player1 == 'random':
        bot_num_one = Random('bot_one')
    elif player1 == 'smart':
        bot_num_one = Smart('bot_one')
    else:
        # We should never get here, but this exists just in case.
        raise ValueError('Not applicable bot strategy')
    if player2 == 'random':
        bot_num_two = Random('bot_two')
    elif player2 == 'smart':
        bot_num_two = Smart('bot_two')
    else:
        # We should never get here, but this exists just in case.
        raise ValueError('Not applicable bot strategy')

    # Log bot players by key in dictionary and start simulation.
    bots = {'Bot1': bot_num_one, 'Bot2': bot_num_two}
    total_moves = bots_only(bots, num_games, size)

    # Grab the results from the simulation and do needed math.
    bot_one_wins = bots['Bot1'].wins
    bot_two_wins = bots['Bot2'].wins
    ties = num_games - (bot_one_wins + bot_two_wins)
    bot_one_win_rate = round(100 * (bot_one_wins / num_games), 2)
    bot_two_win_rate = round(100 * (bot_two_wins / num_games), 2)
    tie_rate = round(100 * (ties / num_games), 2)

    # Outputs the results of the simulation.
    print(f'Player 1 wins: {bot_one_win_rate}%')
    print(f'Player 2 wins: {bot_two_win_rate}%')
    print(f'Ties: {tie_rate}%')
    print('Average moves:', total_moves / num_games)

if __name__ == "__main__":
    cmd()
