"""
Holds the engine to its speed targets. The worst case is a 19x19 board under
superko, which took 468.6 ms and 110.08 s before the engine stopped deep-copying
the game for every legality check.
"""
import random
import statistics
import time

from go_python.go import Go

AVAILABLE_MOVES_BUDGET_MS = 10
GAME_BUDGET_S = 3.3
SUPERKO_RATIO_BUDGET = 2

def midgame(superko: bool) -> Go:
    """
    Builds a 19x19 game 180 moves in.

    Args:
        superko: Whether the game uses superko

    Returns: The game
    """
    rng = random.Random(7)
    go = Go(19, 2, superko)
    for _ in range(180):
        go.apply_move(rng.choice(go.available_moves))
    return go

def available_moves_ms(go: Go) -> float:
    """
    Times available_moves.

    Args:
        go: The game

    Returns: The median of nine runs in milliseconds
    """
    samples = []
    for _ in range(9):
        start = time.perf_counter()
        assert go.available_moves
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)

def game_seconds(superko: bool) -> float:
    """
    Times a 300-move random game on a 19x19 board.

    Args:
        superko: Whether the game uses superko

    Returns: The median of three runs in seconds
    """
    samples = []
    for _ in range(3):
        rng = random.Random(3)
        go = Go(19, 2, superko)
        start = time.perf_counter()
        for _ in range(300):
            go.apply_move(rng.choice(go.available_moves))
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)

def test_available_moves_budget() -> None:
    """Check the cost of listing moves, and what superko adds to it"""
    simple = available_moves_ms(midgame(False))
    superko = available_moves_ms(midgame(True))
    print(f"\navailable_moves: simple {simple:.2f} ms, superko {superko:.2f} ms")
    assert superko <= AVAILABLE_MOVES_BUDGET_MS
    assert superko <= SUPERKO_RATIO_BUDGET * simple

def test_full_game_budget() -> None:
    """Check the cost of a whole game, and what superko adds to it"""
    simple = game_seconds(False)
    superko = game_seconds(True)
    print(f"\n300-move game: simple {simple:.2f} s, superko {superko:.2f} s")
    assert superko <= GAME_BUDGET_S
    assert superko <= SUPERKO_RATIO_BUDGET * simple
