"""
Checks what must stay true in any game of two to four players, against a
capture rule, an area score and a history written here rather than the
engine's own.
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
        -> tuple[set[tuple[int, int]], set[int | None]]:
    """
    Finds the connected points of the same kind as a point: a group of stones,
    or a region of empty points.

    Args:
        grid: The board as a list of lists
        row: The row of the point
        col: The column of the point

    Returns: The points, and what borders them. A group has a liberty if None
    borders it, and an empty region bordered by one player is that player's.
    """
    group = {(row, col)}
    stack = [(row, col)]
    border: set[int | None] = set()
    while stack:
        r, c = stack.pop()
        for nr, nc in neighbours(grid, r, c):
            if grid[nr][nc] != grid[row][col]:
                border.add(grid[nr][nc])
            elif (nr, nc) not in group:
                group.add((nr, nc))
                stack.append((nr, nc))
    return group, border

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
            group, border = group_of(grid, row, col)
            if None not in border:
                return False
            seen |= group
    return True

def area_scores_and_owners(grid: GridType, players: int) \
        -> tuple[dict[int, int], dict[tuple[int, int], int]]:
    """
    Scores a board by area: each player's stones, plus every empty region
    that only that player's stones border.

    Args:
        grid: The board as a list of lists
        players: The number of players

    Returns: Each player's score and the owners of empty points
    """
    scores = dict.fromkeys(range(1, players + 1), 0)
    owners: dict[tuple[int, int], int] = {}
    seen: set[tuple[int, int]] = set()
    for row in range(len(grid)):
        for col in range(len(grid)):
            piece = grid[row][col]
            if piece is not None:
                scores[piece] += 1
            elif (row, col) not in seen:
                region, border = group_of(grid, row, col)
                seen |= region
                if len(border) == 1:
                    owner = border.pop()
                    assert owner is not None
                    scores[owner] += len(region)
                    owners.update(dict.fromkeys(region, owner))
    return scores, owners

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
            group, border = group_of(after, r, c)
            if None not in border:
                captured |= group

    for r, c in captured:
        after[r][c] = None
    return after if None in group_of(after, row, col)[1] else None

def frozen(grid: GridType) -> tuple[tuple[int | None, ...], ...]:
    """
    Makes a grid hashable.

    Args:
        grid: The board as a list of lists

    Returns: The rows as tuples
    """
    return tuple(map(tuple, grid))

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
            assert simulated.grid == board_after(before, *available[0], turn)
            assert simulated.turn == turn % players + 1

            move = rng.choice(available)
            go.apply_move(move)
            moves += 1

            grid = go.grid
            assert grid == board_after(before, *move, turn), seed
            assert go.turn == turn % players + 1
            assert groups_have_liberties(grid), seed
            scores, owners = area_scores_and_owners(grid, players)
            assert go.scores() == scores, seed
            assert go.owners() == owners, seed

        for _ in range(players):
            go.pass_turn()

        scores, owners = area_scores_and_owners(go.grid, players)
        assert go.owners() == owners
        assert go.done
        assert go.available_moves == []
        assert go.scores() == scores
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
            playable = []
            for row in range(side):
                for col in range(side):
                    after = board_after(grid, row, col, go.turn)
                    banned = after is not None and frozen(after) in forbidden
                    is_legal = after is not None and not banned
                    assert go.legal_move((row, col)) == is_legal, seed
                    bans += banned
                    if is_legal:
                        legal.append((row, col))
                    if after is not None:
                        playable.append((row, col))

            # Loading wipes the history, the passes and the end of a game, so
            # only captures and suicide decide what a loaded copy may play
            loaded = go.simulate_move(None)
            loaded.load_game(go.turn, grid)
            assert loaded.available_moves == playable, seed
            for _ in range(players - 1):
                loaded.pass_turn()
            assert not loaded.done, seed

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


@pytest.mark.parametrize("players", [1, 2, 3, 4, 8])
def test_loaded_board_ownership_agrees_with_oracle(players: int) -> None:
    """Check independent dense, sparse, empty and full board scenarios."""
    checked = 0
    for seed in range(100):
        rng = random.Random(5000 + seed)
        size = rng.choice((1, 3, 6, 9, 19, 30))
        density = rng.choice((0, 0.1, 0.5, 0.9, 1))
        grid = [[rng.randint(1, players) if rng.random() < density else None
                 for _ in range(size)] for _ in range(size)]
        go = Go(size, players)
        go.load_game(1, grid)
        scores, owners = area_scores_and_owners(grid, players)
        assert go.owners() == owners, (players, seed)
        assert go.scores() == scores, (players, seed)
        checked += size * size
    print(f"\nownership oracle, {players} players: {checked} points, 0 disagreements")
