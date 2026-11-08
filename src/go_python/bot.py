"""
Bot players for a game of Go. A bot picks a move and never changes the game.
"""
import random

from go_python.go import Go

def is_own_eye(game: Go, pos: tuple[int, int]) -> bool:
    """
    Checks if a point is a single-point eye of the player to move: every
    neighbor holds one of their stones.

    Args:
        game: The game to look at.
        pos: An empty point on the board.

    Returns: True if every neighbor of the point is the mover's stone.
    """
    r, c = pos
    neighbors = [(r + dr, c + dc) for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))
                 if 0 <= r + dr < game.side and 0 <= c + dc < game.side]
    return all(game.piece_at(neigh) == game.turn for neigh in neighbors)

class Random:
    """
    A bot that plays a random legal move, but never fills its own eye.
    """

    def move(self, game: Go) -> tuple[int, int] | None:
        """
        Picks a move for the player whose turn it is.

        Args:
            game: The game to move in. It is not changed.

        Returns: The position to play, or None to pass once only the bot's
        own eyes are left.
        """
        moves = [pos for pos in game.available_moves
                 if not is_own_eye(game, pos)]
        return random.choice(moves) if moves else None

class Smart:
    """
    A bot that plays the move giving it the highest score right away.
    """

    def move(self, game: Go) -> tuple[int, int] | None:
        """
        Picks a move for the player whose turn it is.

        Args:
            game: The game to move in. It is not changed.

        Returns: The position to play, or None to pass once only the bot's
        own eyes are left.
        """
        moves = [pos for pos in game.available_moves
                 if not is_own_eye(game, pos)]
        if not moves:
            return None
        return max(moves,
                   key=lambda pos: game.simulate_move(pos).scores()[game.turn])
