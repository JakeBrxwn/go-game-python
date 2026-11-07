"""
Replays seeded random games against sgfmill, an independent Go implementation.
The eval fails on any different board or final score margin, and on any
different legality answer at the points it checks: every point on sweep moves,
and the points near the last move in between.
"""
import random
from collections import Counter

import pytest
from sgfmill import boards

from go_python.go import Go

PLAYERS = {"b": 1, "w": 2, None: None}
COLOURS = {1: "b", 2: "w"}

# Every legality check costs a sgfmill board copy, so full sweeps are spaced out
SWEEP_EVERY = {4: 1, 5: 1, 9: 5, 13: 10, 19: 25}

# Too few of these would mean the games never reached what the eval is checking
MIN_KO_POINTS = 100
MIN_SUPERKO_BANS = 10

def grid_of(board: boards.Board) -> list[list[int | None]]:
    """
    Converts a sgfmill board to the format of Go.grid.

    Args:
        board: The sgfmill board

    Returns: The board as a list of lists
    """
    return [[PLAYERS[board.get(r, c)] for c in range(board.side)]
            for r in range(board.side)]

def frozen(board: boards.Board) -> tuple[int | None, ...]:
    """
    Converts a sgfmill board to something that can sit in a set.

    Args:
        board: The sgfmill board

    Returns: The board as a flat tuple
    """
    return tuple(piece for row in grid_of(board) for piece in row)

def oracle_legal(board: boards.Board, pos: tuple[int, int], colour: str,
                 ko_point: tuple[int, int] | None,
                 history: set[tuple[int | None, ...]] | None) -> bool:
    """
    Decides whether a move is legal using only sgfmill.

    Args:
        board: The sgfmill board
        pos: The position to check
        colour: The colour to move
        ko_point: The point sgfmill says simple ko forbids, if any
        history: Every board so far under superko, or None under simple ko

    Returns: True if the move is legal
    """
    row, col = pos
    if board.get(row, col) is not None or pos == ko_point:
        return False
    trial = board.copy()
    trial.play(row, col, colour)
    if trial.get(row, col) is None:
        return False
    return history is None or frozen(trial) not in history

def neighbourhood(pos: tuple[int, int], side: int) -> list[tuple[int, int]]:
    """
    Finds the points near a move, which is where its effects on legality are.

    Args:
        pos: The last move
        side: The size of the board

    Returns: The points within two steps of the move
    """
    row, col = pos
    return [(r, c) for r in range(max(row - 2, 0), min(row + 3, side))
            for c in range(max(col - 2, 0), min(col + 3, side))]

def play_game(side: int, seed: int, superko: bool) -> Counter[str]:
    """
    Plays one random game in Go and sgfmill side by side.

    Args:
        side: The size of the board
        seed: The seed of the random moves
        superko: Whether the game uses superko

    Returns: Counts of what the game checked
    """
    rng = random.Random(seed)
    go = Go(side, 2, superko)
    board = boards.Board(side)
    history = {frozen(board)} if superko else None
    points = [(r, c) for r in range(side) for c in range(side)]
    ko_point = None
    near_last_move: list[tuple[int, int]] = []
    stats: Counter[str] = Counter(games=1)

    for move_number in range(3 * side * side):
        colour = COLOURS[go.turn]
        sweep = move_number % SWEEP_EVERY[side] == 0
        for pos in points if sweep else near_last_move:
            expected = oracle_legal(board, pos, colour, ko_point, history)
            assert go.legal_move(pos) == expected, (side, seed, move_number, pos)
            stats["legality checks"] += 1
            if not expected and oracle_legal(board, pos, colour, ko_point, None):
                stats["superko bans"] += 1

        if ko_point is not None:
            assert not go.legal_move(ko_point), (side, seed, move_number)
            stats["ko points"] += 1

        rng.shuffle(points)
        move = next((pos for pos in points if go.legal_move(pos)), None)
        if move is None:
            break

        go.apply_move(move)
        ko_point = board.play(*move, colour)
        near_last_move = neighbourhood(move, side)
        if history is not None:
            history.add(frozen(board))
        assert go.grid == grid_of(board), (side, seed, move_number)
        stats["moves"] += 1

    scores = go.scores()
    assert scores[1] - scores[2] == board.area_score(), (side, seed)
    return stats

@pytest.mark.parametrize("side, games", [(9, 250), (13, 150), (19, 100)])
def test_simple_ko_games_agree(side: int, games: int) -> None:
    """Check 500 games in all against sgfmill, move by move"""
    stats: Counter[str] = Counter()
    for seed in range(games):
        stats += play_game(side, 1000 + seed, False)
    print(f"\nrules oracle {side}x{side}: {dict(stats)}, 0 disagreements")
    assert stats["ko points"] >= MIN_KO_POINTS

def test_superko_games_agree() -> None:
    """
    Check superko against a history of sgfmill boards kept here. Random games
    on larger boards never repeat a position except through simple ko, so the
    small boards are the ones that reach what only superko forbids.
    """
    stats: Counter[str] = Counter()
    for side, games in ((4, 300), (5, 300), (9, 50)):
        for seed in range(games):
            stats += play_game(side, 2000 + seed, True)
    print(f"\nsuperko oracle: {dict(stats)}, 0 disagreements")
    assert stats["ko points"] >= MIN_KO_POINTS
    assert stats["superko bans"] >= MIN_SUPERKO_BANS
