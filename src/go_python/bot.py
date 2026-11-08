"""
Bot players for a game of Go. A bot picks a move and never changes the game.
"""
import random

from go_python.board import BoardGridType
from go_python.go import Go

#
# Shared by both bots
#

# A point on the board, as (row, column)
Point = tuple[int, int]

# A chain: connected stones of one player, and the empty points touching them
Chain = tuple[set[Point], set[Point]]

def _neighbors(pos: Point, side: int) -> list[Point]:
    """
    Lists the points next to a point.

    Args:
        pos: A point on the board.
        side: The size of the board.

    Returns: The points above, below, left and right of pos that are on the
    board.
    """
    r, c = pos
    return [(nr, nc) for nr, nc in ((r, c + 1), (r + 1, c), (r, c - 1),
                                   (r - 1, c))
            if 0 <= nr < side and 0 <= nc < side]

def _chains(grid: BoardGridType) -> dict[Point, Chain]:
    """
    Groups the stones on the board into chains.

    Args:
        grid: The board, as the game's grid property returns it.

    Returns: Every stone mapped to its chain. The stones of one chain share
    one tuple.
    """
    side = len(grid)
    chains: dict[Point, Chain] = {}
    for start in ((r, c) for r in range(side) for c in range(side)):
        player = grid[start[0]][start[1]]
        if player is None or start in chains:
            continue
        chain: Chain = ({start}, set())
        stack = [start]
        while stack:
            pos = stack.pop()
            chains[pos] = chain
            for r, c in _neighbors(pos, side):
                if grid[r][c] is None:
                    chain[1].add((r, c))
                elif grid[r][c] == player and (r, c) not in chain[0]:
                    chain[0].add((r, c))
                    stack.append((r, c))
    return chains

def is_own_eye(game: Go, pos: tuple[int, int]) -> bool:
    """
    Checks if a point is a single-point eye of the player to move: every
    neighbor holds one of their stones.

    Args:
        game: The game to look at.
        pos: An empty point on the board.

    Returns: True if every neighbor of the point is the mover's stone.
    """
    return all(game.piece_at(neigh) == game.turn
               for neigh in _neighbors(pos, game.side))

#
# Random
#

def _takes_ko(game: Go, chains: dict[Point, Chain], pos: Point) -> bool:
    """
    Checks if a move takes a ko: it captures one stone, and every other
    neighbor is another player's stone, so the new stone could be taken
    straight back. Simple ko only bans the immediate retake, so bots that keep
    taking kos can loop until the move limit.

    Args:
        game: The game, with the player to move.
        chains: The board's chains, from _chains.
        pos: An empty point.

    Returns: True if the move takes a ko.
    """
    near = _neighbors(pos, game.side)
    if any(n not in chains or game.piece_at(n) == game.turn for n in near):
        return False
    caught = [len(chains[n][0]) for n in near if len(chains[n][1]) == 1]
    return caught == [1]

class Random:
    """
    A bot that plays a random legal move, but never fills its own eye and
    never takes a ko, under either ko rule.
    """

    def move(self, game: Go) -> tuple[int, int] | None:
        """
        Picks a move for the player whose turn it is.

        Args:
            game: The game to move in. It is not changed.

        Returns: The position to play, or None to pass once only the bot's
        own eyes and kos are left.
        """
        chains = _chains(game.grid)
        moves = [pos for pos in game.available_moves
                 if not is_own_eye(game, pos)
                 and not _takes_ko(game, chains, pos)]
        return random.choice(moves) if moves else None

#
# Smart
#

def _value(game: Go, grid: BoardGridType, chains: dict[Point, Chain],
           pos: Point) -> float | None:
    """
    Rates a move by what it does to the chains next to it. In order of
    weight: stones it captures, own stones it saves from danger, pressure on
    enemy chains (bigger chains with fewer liberties count more), and
    distance from the edge. A random part breaks ties.

    Args:
        game: The game, with the player to move.
        grid: The board, as the game's grid property returns it.
        chains: The board's chains, from _chains.
        pos: An empty point.

    Returns: How good the move is, higher being better, or None if it leaves
    its own chain with fewer than two liberties without capturing at least
    two stones. That also turns down taking a ko, so two kos cannot loop.
    """
    side = len(grid)
    near = _neighbors(pos, side)
    libs = {n for n in near if grid[n[0]][n[1]] is None}
    captured = saved = 0
    pressure = 0.0
    for n in {id(chains[n]): n for n in near if n in chains}.values():
        stones, chain_libs = chains[n]
        if grid[n[0]][n[1]] == game.turn:
            libs |= chain_libs
            # In danger: one liberty, or two where one is an eye it won't fill
            if len(chain_libs) == 1 or len(chain_libs) == 2 and \
               any(is_own_eye(game, lib) for lib in chain_libs):
                saved += len(stones)
        elif len(chain_libs) == 1:
            captured += len(stones)
            libs.add(n)
        else:
            pressure += len(stones) / len(chain_libs)
    libs.discard(pos)
    if len(libs) < 2 and captured < 2:
        return None
    r, c = pos
    edge = min(r, c, side - 1 - r, side - 1 - c, 2)
    return (1000 * captured + 100 * saved + 3 * pressure + edge
            + random.random())

class Smart:
    """
    A bot that rates every move by the chains next to it: it captures,
    saves its own stones, presses on weak enemy chains and keeps off the
    edge. It never takes a ko, and never puts its own chain in atari
    unless that captures two or more stones.
    """

    def move(self, game: Go) -> tuple[int, int] | None:
        """
        Picks a move for the player whose turn it is.

        Args:
            game: The game to move in. It is not changed.

        Returns: The position to play, or None to pass once every move left
        fills its own eye or puts its own stones in atari.
        """
        grid = game.grid
        chains = _chains(grid)
        values = {pos: value for pos in ((r, c) for r in range(game.side)
                                         for c in range(game.side)
                                         if grid[r][c] is None)
                  if (value := _value(game, grid, chains, pos)) is not None}
        # The ratings rule out suicide and simple ko; legal_move adds superko
        # and a finished game
        return next((pos for pos in sorted(values, key=values.__getitem__,
                                           reverse=True)
                     if not is_own_eye(game, pos) and game.legal_move(pos)),
                    None)
