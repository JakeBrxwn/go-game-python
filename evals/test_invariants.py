"""
Checks what must stay true in any game of two to four players, using a liberty
count and a history written here rather than the engine's own.
"""
import random

import pytest

from go_python.board import FrozenBoardGridType
from go_python.go import Go

GAMES_WITH_REPEATS = 300
MIN_BANS = 40
PASS_CHANCE = 0.1

def groups_have_liberties(grid: list[list[int | None]]) -> bool:
    """
    Checks that no group of stones on a grid is out of liberties.

    Args:
        grid: The board as a list of lists

    Returns: True if every group has at least one liberty
    """
    side = len(grid)
    seen: set[tuple[int, int]] = set()

    for row in range(side):
        for col in range(side):
            if grid[row][col] is None or (row, col) in seen:
                continue

            has_liberty = False
            stack = [(row, col)]
            seen.add((row, col))
            while stack:
                r, c = stack.pop()
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if not (0 <= nr < side and 0 <= nc < side):
                        continue
                    if grid[nr][nc] is None:
                        has_liberty = True
                    elif grid[nr][nc] == grid[row][col] and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        stack.append((nr, nc))

            if not has_liberty:
                return False

    return True

def stones_of(grid: list[list[int | None]], player: int) -> int:
    """
    Counts one player's stones.

    Args:
        grid: The board as a list of lists
        player: The player number

    Returns: The number of stones on the board
    """
    return sum(row.count(player) for row in grid)

@pytest.mark.parametrize("players", [2, 3, 4])
@pytest.mark.parametrize("superko", [False, True])
def test_invariants_hold_every_move(players: int, superko: bool) -> None:
    """Check seeded games from the first move to the final score"""
    moves = 0
    for seed in range(30):
        rng = random.Random(3000 + seed)
        side = rng.choice((6, 9, 13))
        go = Go(side, players, superko)

        for _ in range(2 * side * side):
            available = go.available_moves
            if not available:
                break

            turn = go.turn
            before = go.grid
            simulated = go.simulate_move(available[0])
            assert go.grid == before and go.turn == turn
            assert simulated.turn == turn % players + 1

            go.apply_move(rng.choice(available))
            moves += 1

            grid = go.grid
            scores = go.scores()
            assert go.turn == turn % players + 1
            assert groups_have_liberties(grid), seed
            assert sum(scores.values()) <= side * side, seed
            for player, score in scores.items():
                assert score >= stones_of(grid, player), seed

        for _ in range(players):
            go.pass_turn()

        scores = go.scores()
        assert go.done
        assert go.available_moves == []
        assert go.outcome == [player for player, score in scores.items()
                              if score == max(scores.values())]

    print(f"\ninvariants, {players} players, superko={superko}: {moves} moves")

@pytest.mark.parametrize("players", [2, 3, 4])
@pytest.mark.parametrize("superko", [False, True])
def test_repeats_are_refused(players: int, superko: bool) -> None:
    """
    Check every legality answer against a history kept here, with passes mixed
    in, on boards small enough for positions to come back.
    """
    bans = 0
    for seed in range(GAMES_WITH_REPEATS):
        rng = random.Random(4000 + seed)
        side = rng.choice((3, 4, 5))
        go = Go(side, players, superko)
        forbidden: set[FrozenBoardGridType] = set()
        passes = 0

        for _ in range(4 * side * side):
            no_history = Go(side, players)
            no_history.load_game(go.turn, go.grid)
            for move in no_history.available_moves:
                banned = no_history.simulate_move(move).frozengrid in forbidden
                assert go.legal_move(move) != banned, seed
                bans += banned

            available = go.available_moves
            if not available:
                break

            if passes < players - 1 and rng.random() < PASS_CHANCE:
                go.pass_turn()
                passes += 1
                continue

            before = go.frozengrid
            go.apply_move(rng.choice(available))
            passes = 0
            assert go.frozengrid not in forbidden, seed
            forbidden = forbidden | {before} if superko else {before}

    print(f"\nrepeats, {players} players, superko={superko}: {bans} bans")
    assert bans >= MIN_BANS
