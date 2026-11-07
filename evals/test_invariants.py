"""
Checks what must stay true in any game of two to four players, using a capture
rule, a liberty count and a history written here rather than the engine's own.
"""
import random

import pytest

from go_python.go import Go

GAMES_WITH_REPEATS = 300
MIN_BANS = 40
PASS_CHANCE = 0.1

GridType = list[list[int | None]]

def neighbours(grid: GridType, row: int, col: int) -> list[tuple[int, int]]:
    """
    Finds the points next to a point.

    Args:
        grid: The board as a list of lists
        row: The row of the point
        col: The column of the point

    Returns: The points one step away that are on the board
    """
    side = len(grid)
    return [(r, c) for r, c in ((row + 1, col), (row - 1, col),
                                (row, col + 1), (row, col - 1))
            if 0 <= r < side and 0 <= c < side]

def group_of(grid: GridType, row: int, col: int) \
        -> tuple[set[tuple[int, int]], bool]:
    """
    Finds the group of stones at a point.

    Args:
        grid: The board as a list of lists
        row: The row of a stone
        col: The column of a stone

    Returns: The points of the group, and whether it has a liberty
    """
    group = {(row, col)}
    stack = [(row, col)]
    has_liberty = False
    while stack:
        r, c = stack.pop()
        for nr, nc in neighbours(grid, r, c):
            if grid[nr][nc] is None:
                has_liberty = True
            elif grid[nr][nc] == grid[row][col] and (nr, nc) not in group:
                group.add((nr, nc))
                stack.append((nr, nc))
    return group, has_liberty

def groups_have_liberties(grid: GridType) -> bool:
    """
    Checks that no group of stones on a grid is out of liberties.

    Args:
        grid: The board as a list of lists

    Returns: True if every group has at least one liberty
    """
    seen: set[tuple[int, int]] = set()
    for row in range(len(grid)):
        for col in range(len(grid)):
            if grid[row][col] is None or (row, col) in seen:
                continue
            group, has_liberty = group_of(grid, row, col)
            if not has_liberty:
                return False
            seen |= group
    return True

def board_after(grid: GridType, row: int, col: int,
                player: int) -> GridType | None:
    """
    Plays a stone on a copy of a grid. Every enemy group left without a liberty
    is removed at once, and then the move is refused if it is suicide.

    Args:
        grid: The board as a list of lists
        row: The row of the move
        col: The column of the move
        player: The player who moves

    Returns: The new grid, or None if the point is taken or the move is suicide
    """
    if grid[row][col] is not None:
        return None

    after = [line[:] for line in grid]
    after[row][col] = player
    captured: set[tuple[int, int]] = set()
    for r, c in neighbours(after, row, col):
        if after[r][c] not in (None, player):
            group, has_liberty = group_of(after, r, c)
            if not has_liberty:
                captured |= group

    for r, c in captured:
        after[r][c] = None
    return after if group_of(after, row, col)[1] else None

def frozen(grid: GridType) -> tuple[tuple[int | None, ...], ...]:
    """
    Makes a grid hashable.

    Args:
        grid: The board as a list of lists

    Returns: The rows as tuples
    """
    return tuple(map(tuple, grid))

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

            move = rng.choice(available)
            go.apply_move(move)
            moves += 1

            grid = go.grid
            scores = go.scores()
            assert grid == board_after(before, *move, turn), seed
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
    Check every legality answer and every board against a capture rule and a
    history kept here, with passes mixed in, on boards small enough for
    positions to come back.
    """
    bans = 0
    for seed in range(GAMES_WITH_REPEATS):
        rng = random.Random(4000 + seed)
        side = rng.choice((3, 4, 5))
        go = Go(side, players, superko)
        forbidden: set[tuple[tuple[int | None, ...], ...]] = set()
        passes = 0

        for _ in range(4 * side * side):
            grid = go.grid
            legal = []
            for row in range(side):
                for col in range(side):
                    after = board_after(grid, row, col, go.turn)
                    banned = after is not None and frozen(after) in forbidden
                    is_legal = after is not None and not banned
                    assert go.legal_move((row, col)) == is_legal, seed
                    bans += banned
                    if is_legal:
                        legal.append((row, col))

            available = go.available_moves
            assert available == legal, seed
            if not available:
                break

            if passes < players - 1 and rng.random() < PASS_CHANCE:
                go.pass_turn()
                passes += 1
                continue

            move = rng.choice(available)
            expected = board_after(grid, *move, go.turn)
            go.apply_move(move)
            passes = 0
            assert go.grid == expected, seed
            forbidden = forbidden | {frozen(grid)} if superko else {frozen(grid)}

    print(f"\nrepeats, {players} players, superko={superko}: {bans} bans")
    assert bans >= MIN_BANS
