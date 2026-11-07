import csv
import random
from collections.abc import Callable
from pathlib import Path

import pytest

from go_python.board import Board, BoardGridType, FrozenBoardGridType
from go_python.go import Go

POSITIONS_FILE = Path(__file__).with_name("test_positions.txt")

###
# Helper functions for test functions
###

def apply_moves(game: Go, moves: list[tuple[int, int]]) -> None:
    """
    Helper function to apply a sequence of moves to a Go game.

    Args:
        game (Go): The Go game instance
        moves (list of tuple[int, int]): A list of moves to apply

    """
    for move in moves:
        game.apply_move(move)

def parse_moves(moves_str: str) -> list[tuple[int, ...]]:
    """
    Helper function that splits semicolon-connected string into list of tuples
    Args: moves_str [str] : no whitespace, semicolon-connected string
    of tuples
    Returns: list[tuple[int, ...]] : list of moves
    """
    return [tuple(map(int, t.split(','))) for t in moves_str.split(';') if t]

def set_up_test(g: Go, test_name: str) -> None:
    """
    Helper function that gets string representation of moves needed to set up
    the position for desired test
    Args: test_name [str] : the test name that corresponds to row in test
    positions text file
    """
    with open(POSITIONS_FILE) as file:
        reader = csv.DictReader(file, delimiter = '|')
        moves = []
        for row in reader:
            if row['TEST_NAME'] == test_name:
                moves = parse_moves(row['MOVES'])
                break
        else:
            raise KeyError(f"No position named {test_name}")
        initial_board: BoardGridType = [[None for _ in range(g.side)]
                                        for _ in range(g.side)]
        turn = 1
        for move in moves:
            r, c = move
            initial_board[r][c] = turn
            turn += 1
            if turn > g.num_players:
                turn = 1
        g.load_game(turn, initial_board)


###
# Constructor and properties tests
###

### Property Helper functions
@pytest.mark.parametrize("side, num_players", [
    (9, 2), (9, 3), (9, 4),
    (13, 2), (13, 3), (13, 4),
    (19, 2), (19, 3), (19, 4)
])
def test_side(side: int, num_players: int) -> None:
    """
    Check side initialization
    """
    g = Go(side, num_players)
    assert g.side == side

@pytest.mark.parametrize("side, num_players", [
    (9, 2), (9, 3), (9, 4),
    (13, 2), (13, 3), (13, 4),
    (19, 2), (19, 3), (19, 4)
])
def test_num_players(side: int, num_players: int) -> None:
    """
    Check num_players initialization
    """
    g = Go(side, num_players)
    assert g.num_players == num_players

@pytest.mark.parametrize("side, num_players", [
    (9, 2), (9, 3), (9, 4),
    (13, 2), (13, 3), (13, 4),
    (19, 2), (19, 3), (19, 4)
])
def test_turn(side: int, num_players: int) -> None:
    """
    Check turn initialization
    """
    g = Go(side, num_players)
    assert g.turn == 1

@pytest.mark.parametrize("side, num_players", [
    (9, 2), (13, 2), (19, 2)
])
def test_piece_at(side: int, num_players: int) -> None:
    """
    Check no pieces placed at start
    """
    g = Go(side, num_players)
    for row in range(side):
        for col in range(side):
            assert g.piece_at((row, col)) is None

@pytest.mark.parametrize("side, num_players", [
    (9, 2), (13, 2), (19, 2)
])
def test_legal_move(side: int, num_players: int) -> None:
    """
    Check all moves are legal at start
    """
    g = Go(side, num_players)
    for row in range(side):
        for col in range(side):
            assert g.legal_move((row, col))

@pytest.mark.parametrize("side, num_players", [
    (9, 2), (13, 2), (19, 2)
])
def test_available_moves(side: int, num_players: int) -> None:
    """
    Check all moves are available at start
    """
    g = Go(side, num_players)
    assert len(g.available_moves) == side * side

###
# Tests on placement, capturing, passing, ko/superko, scoring
###

def test_19x19_illegal_move_with_load_game() -> None:
    """Check can't place piece on top of another one using load_game"""
    g = Go(19, 2)  # Initialize the Go game with a 19x19 board and 2 players.

    set_up_test(g, "test_19x19_illegal_move_with_load_game")

    assert not g.legal_move((0, 0))

def test_19x19_pass() -> None:
    """Check pass and turn update"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_pass")
    g.pass_turn()
    assert g.turn == 1

def test_19x19_pass_twice() -> None:
    """Check passing twice ends game"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_pass_twice")
    g.pass_turn()
    g.pass_turn()
    assert g.done

def test_19x19_capture() -> None:
    """Check single capture"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_capture")
    g.apply_move((0, 1))
    assert g.piece_at((0, 0)) is None

def test_19x19_captures() -> None:
    """Check multiple captures"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_captures")
    g.apply_move((0, 2))
    assert g.piece_at((0, 0)) is None and g.piece_at((0, 1)) is None

def test_19x19_ten_captures() -> None:
    """Checks execution of capturing ten pieces"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_ten_captures")
    g.apply_move((0,10))
    for i in range(10):
        assert g.piece_at((0, i)) is None

def test_19x19_ko() -> None:
    """
    Check enforcement of ko
    Note we cannot use set_up_test/load_game here as the game needs memory
    """
    g = Go(19, 2)
    moves = [(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (2, 2), (2, 1), (1, 1)]
    apply_moves(g, moves)
    assert not g.legal_move((2, 1))

def test_19x19_super_ko() -> None:
    """
    Check enforcement of superko
    Note we cannot use set_up_test/load_game here as the game needs memory
    """
    g = Go(19, 2, True)
    moves = [(0, 2), (0, 1), (0, 3), (1, 0), (1, 4), (1, 2), (2, 2), (2, 1),
             (2, 3), (1, 3), (1, 1)]
    apply_moves(g, moves)
    assert not g.legal_move((1, 2))

def test_19x19_scores() -> None:
    """Check scores without territory"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_scores")
    assert g.scores()[1] == 3 and g.scores()[2] == 3

def test_19x19_scores_with_territory() -> None:
    """Check scores with territory"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_scores_with_territory")
    assert g.scores()[1] == 4 and g.scores()[2] == 2

def test_19x19_multiple_territories_two_player() -> None:
    """Check scoring of multiple territories"""
    g=Go(19,2)
    set_up_test(g, "test_19x19_multiple_territories_two_player")
    assert g.scores()[1] == 7 and g.scores()[2] == 7

def test_19x19_multiple_territories_three_player() -> None:
    """Check scoring of multiple territories"""
    g = Go(19,3)
    set_up_test(g, "test_19x19_multiple_territories_three_player")
    assert g.scores()[1] == 5 and g.scores()[2] == 4 and g.scores()[3] == 4

def test_19x19_outcome() -> None:
    """Check outcome of a finished two player game"""
    g = Go(19, 2)
    set_up_test(g, "test_19x19_outcome")
    g.pass_turn()
    g.pass_turn()
    assert g.outcome == [1]

def test_19x19_three_player() -> None:
    """
    Check piece placement for three player
    Note we cannot use load game as test function needs to know which moves
    were played
    """
    g = Go(19, 3)
    moves = [(0, 0), (1, 1), (2,2)]
    apply_moves(g, moves)
    for move in moves:
        assert g.piece_at(move) is not None

def test_19x19_three_player_pass() -> None:
    """Check that three passes results in game over"""
    g = Go(19, 3)
    set_up_test(g, "test_19x19_three_player_pass")
    g.pass_turn()
    g.pass_turn()
    g.pass_turn()
    assert g.done

###
# Tests on grid property
###

def test_grid_1() -> None:
    """Check that grid for an empty game is exported correctly"""
    go = Go(19, 2)
    grid = go.grid
    for row in range(go.side):
        for col in range(go.side):
            assert grid[row][col] is None


def test_grid_2() -> None:
    """
    Check that grid returns a deep copy of the board's grid,
    and that modifying grid's return value doesn't modify
    the game's board
    """
    go = Go(19, 2)
    grid = go.grid
    grid[5][5] = 1
    assert go.piece_at((5, 5)) is None, (
        "grid() returned a shallow copy of the game's board. "
        "Modifying the return value of grid() should not "
        "affect the game's board."
    )

def test_grid_3() -> None:
    """
    Check that grid returns a correct copy of the board after making
    a few moves (none of the moves will result in a capture)
    """
    go = Go(19, 2)
    set_up_test(go, "test_grid_3")
    grid = go.grid
    for row in range(go.side):
        for col in range(go.side):
            assert grid[row][col] == go.piece_at((row, col))

###
# Tests on simulate_move
###

def test_simulate_move_1() -> None:
    """
    Test that simulating a move creates a new game
    """
    go = Go(19, 2)
    new_go = go.simulate_move((5, 5))

    # Check that the original Go object has not been modified
    assert go.piece_at((5, 5)) is None
    assert go.turn == 1

    # Check that the move was applied in the new Go object
    assert new_go.piece_at((5, 5)) == 1
    assert new_go.turn == 2

def test_simulate_move_2() -> None:
    """
    After making a few moves, check that simulating a move
    correctly creates a new game.
    Note that we cannot use load_game here since the function requires knowing
    the move list
    """
    initial_moves = [
        (3, 3),
        (6, 16),
        (1, 1),
        (13, 0),
        (16, 1),
        (18, 15),
        (13, 14),
        (2, 10),
        (1, 17),
        (3, 13),
        (11, 2),
        (2, 8),
        (13, 11),
        (11, 0),
        (4, 17),
        (3, 6),
        (16, 2),
        (5, 2),
        (14, 8),
        (13, 2),
    ]

    go = Go(19, 2)
    for move in initial_moves:
        go.apply_move(move)
    new_go = go.simulate_move((5, 5))

    # Check that the original Go object has not been modified
    assert go.piece_at((5, 5)) is None
    for move in initial_moves:
        assert go.piece_at(move) is not None
    assert go.turn == 1

    # Check that the move was applied in the new Go object
    assert new_go.piece_at((5, 5)) == 1
    for move in initial_moves:
        assert new_go.piece_at(move) is not None
    assert new_go.turn == 2


def test_simulate_move_3() -> None:
    """
    Apply simulate move to result in a piece capture. Verify that the piece has
    not been captured in the original board, and only in the simulated board
    """
    go = Go(19, 2)
    set_up_test(go, "test_simulate_move_3")

    assert go.piece_at((0,0)) == 2

    new_go = go.simulate_move((1, 0))

    # Check that the original Go object has not been modified
    assert go.piece_at((0, 0)) == 2
    assert go.piece_at((1, 0)) is None
    assert go.turn == 1

    # Check that the move was applied in the new Go object
    assert new_go.piece_at((0, 0)) is None
    assert new_go.piece_at((1, 0)) == 1
    assert new_go.turn == 2


def test_simulate_move_4() -> None:
    """
    Check that simulating a pass works correctly.
    """
    go = Go(19, 2)
    new_go = go.simulate_move(None)

    # Check that the original Go object has not been modified
    assert go.turn == 1

    # Check that the pass was applied in the new Go object
    assert new_go.turn == 2


def test_simulate_move_5() -> None:
    """
    Check that simulating two consecutive passes works correctly.
    """
    go = Go(19, 2)
    new_go = go.simulate_move(None).simulate_move(None)

    # Check that the original Go object has not been modified
    assert go.turn == 1
    assert not go.done

    # Check that the passes were applied in the new Go object
    assert new_go.done

###
# Tests on bounds, passing, scoring and outcomes
###

@pytest.mark.parametrize("row, col", [
    (-1, -1), (-1, 5), (-1, 19), (5, -1), (5, 19), (19, -1), (19, 5), (19, 19),
    (21, 0), (0, 21)
])
def test_legal_move_invalid_location(row: int, col: int) -> None:
    """Check that a position off the board raises an exception"""
    go = Go(19, 2)
    with pytest.raises(ValueError):
        go.legal_move((row, col))

def test_available_moves_excludes_occupied() -> None:
    """Check that available_moves drops played points and nothing else"""
    moves = [(3, 3), (6, 16), (1, 1), (13, 0), (16, 1)]
    go = Go(19, 2)
    apply_moves(go, moves)
    available = go.available_moves
    assert len(available) == 19 * 19 - len(moves)
    for move in moves:
        assert move not in available

def test_pass_on_second_players_turn() -> None:
    """Check that a pass by player 2 returns the turn to player 1"""
    go = Go(19, 2)
    apply_moves(go, [(5, 5), (6, 6), (7, 7)])
    go.pass_turn()
    assert go.turn == 1

def test_passes_with_stones_on_board_end_game() -> None:
    """Check that two passes end a game that already has stones on it"""
    go = Go(19, 2)
    apply_moves(go, [(5, 5), (6, 6), (7, 7)])
    go.pass_turn()
    go.pass_turn()
    assert go.done

def test_move_between_passes_keeps_game_going() -> None:
    """Check that passes only count when no move separates them"""
    go = Go(19, 2)
    apply_moves(go, [(5, 5), (6, 6), (7, 7)])
    go.pass_turn()
    go.apply_move((8, 8))
    go.pass_turn()
    assert not go.done

def test_scores_empty_board() -> None:
    """Check that an empty board scores nothing for anyone"""
    assert Go(19, 2).scores() == {1: 0, 2: 0}

def test_scores_open_board() -> None:
    """Check that open space bordered by both players scores for neither"""
    go = Go(19, 2)
    apply_moves(go, [(5, 5), (5, 8), (5, 6)])
    assert go.scores() == {1: 2, 2: 1}

def test_lone_stone_owns_the_board() -> None:
    """Check that one stone scores every empty point, since it alone borders them"""
    go = Go(9, 2)
    go.apply_move((4, 4))
    assert go.scores() == {1: 81, 2: 0}

def test_outcome_empty_until_done() -> None:
    """Check that a game in progress has no winners"""
    go = Go(19, 2)
    go.apply_move((5, 5))
    assert go.outcome == []

def test_outcome_empty_board_ties() -> None:
    """Check that two passes on an empty board tie"""
    go = Go(19, 2)
    go.pass_turn()
    go.pass_turn()
    assert go.outcome == [1, 2]

def test_outcome_second_player_wins() -> None:
    """Check that player 2 can win on stones"""
    go = Go(19, 2)
    go.apply_move((5, 6))
    go.apply_move((5, 8))
    go.pass_turn()
    go.apply_move((5, 9))
    go.pass_turn()
    go.pass_turn()
    assert go.outcome == [2]

def test_outcome_tie_on_stones() -> None:
    """Check that equal stones tie"""
    go = Go(19, 2)
    apply_moves(go, [(5, 6), (5, 8), (6, 6), (6, 8)])
    go.pass_turn()
    go.pass_turn()
    assert go.outcome == [1, 2]

###
# Rule tests. Every test_regression_* here fails on the code before its fix
###

@pytest.mark.parametrize("pos", [(9, 0), (0, 9), (9, 9)])
def test_regression_piece_at_off_board(pos: tuple[int, int]) -> None:
    """Check that the row and column past the edge raise ValueError"""
    with pytest.raises(ValueError):
        Go(9, 2).piece_at(pos)

@pytest.mark.parametrize("pos", [(-1, 0), (0, -1)])
def test_piece_at_negative_position(pos: tuple[int, int]) -> None:
    """Check that negative positions do not wrap around the board"""
    with pytest.raises(ValueError):
        Go(9, 2).piece_at(pos)

@pytest.mark.parametrize("row, col", [(3, 0), (0, 4), (3, 4), (-1, 0), (0, -1)])
def test_regression_board_bounds(row: int, col: int) -> None:
    """Check that a board that is not square checks each axis at both ends"""
    board = Board(3, 4)
    with pytest.raises(ValueError):
        board.get(row, col)
    with pytest.raises(ValueError):
        board.set(row, col, 1)

KO_SHAPE = [(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (2, 2), (2, 1), (1, 1)]

def test_regression_ko_blocks_immediate_recapture() -> None:
    """Check that the stone that started a ko cannot retake it at once"""
    go = Go(9, 2)
    apply_moves(go, KO_SHAPE)
    assert go.piece_at((2, 1)) is None
    assert not go.legal_move((2, 1))
    assert (2, 1) not in go.available_moves

def test_superko_blocks_immediate_recapture() -> None:
    """Check that superko forbids everything simple ko does"""
    go = Go(9, 2, True)
    apply_moves(go, KO_SHAPE)
    assert not go.legal_move((2, 1))

def test_ko_lifts_after_play_elsewhere() -> None:
    """Check that a ko threat exchange makes the recapture legal again"""
    go = Go(9, 2)
    apply_moves(go, KO_SHAPE)
    apply_moves(go, [(7, 7), (7, 8)])
    assert go.legal_move((2, 1))
    go.apply_move((2, 1))
    assert go.piece_at((1, 1)) is None

# After these moves, simple ko allows (1, 2) but superko bans it
SUPERKO_ONLY_BAN = [(0, 2), (0, 1), (0, 3), (1, 0), (1, 4), (1, 2), (2, 2),
                    (2, 1), (2, 3), (1, 3), (1, 1)]

def test_superko_forbids_any_earlier_board_not_just_the_last() -> None:
    """Check that superko blocks what simple ko allows"""
    simple, superko = Go(19, 2), Go(19, 2, True)
    apply_moves(simple, SUPERKO_ONLY_BAN)
    apply_moves(superko, SUPERKO_ONLY_BAN)
    assert simple.legal_move((1, 2))
    assert not superko.legal_move((1, 2))

def test_simulated_move_keeps_superko() -> None:
    """Check that the game simulate_move returns still plays by superko"""
    go = Go(19, 2, True)
    apply_moves(go, SUPERKO_ONLY_BAN[:-1])
    simulation = go.simulate_move(SUPERKO_ONLY_BAN[-1])
    assert not simulation.legal_move((1, 2))

def board_with(side: int, stones: dict[tuple[int, int], int]) \
-> list[list[int | None]]:
    """
    Helper function that builds a grid for load_game.

    Args:
        side: The size of the board
        stones: Maps each occupied position to its player

    Returns: The grid as a list of lists
    """
    grid: list[list[int | None]] = [[None] * side for _ in range(side)]
    for (row, col), player in stones.items():
        grid[row][col] = player
    return grid

@pytest.mark.parametrize("superko", [False, True])
def test_single_stone_suicide_is_illegal(superko: bool) -> None:
    """Check that a stone cannot fill the last liberty of itself"""
    go = Go(9, 2, superko)
    go.load_game(2, board_with(9, {(0, 1): 1, (1, 0): 1}))
    assert not go.legal_move((0, 0))
    assert (0, 0) not in go.available_moves

def test_regression_group_suicide_is_illegal() -> None:
    """Check that a move cannot remove its own group"""
    go = Go(9, 2)
    go.load_game(1, board_with(9, {
        (0, 0): 1, (1, 0): 2, (1, 1): 2, (0, 2): 2,
    }))
    assert not go.legal_move((0, 1))
    assert (0, 1) not in go.available_moves

def test_capture_that_looks_like_suicide_is_legal() -> None:
    """Check that captures come off before the mover's liberties are counted"""
    go = Go(9, 2)
    go.load_game(1, board_with(9, {
        (0, 1): 2, (1, 0): 2, (1, 1): 1, (0, 2): 1, (2, 0): 1,
    }))
    assert go.legal_move((0, 0))
    go.apply_move((0, 0))
    assert go.piece_at((0, 0)) == 1
    assert go.piece_at((0, 1)) is None
    assert go.piece_at((1, 0)) is None

def test_regression_neighbouring_captures_are_simultaneous() -> None:
    """Check that one capture does not free a touching enemy group"""
    go = Go(9, 3)
    go.load_game(1, board_with(9, {
        (0, 0): 2, (0, 1): 2, (1, 1): 3, (0, 2): 1, (1, 2): 1, (2, 1): 1,
    }))
    go.apply_move((1, 0))
    assert go.piece_at((1, 1)) is None
    assert go.piece_at((0, 0)) is None
    assert go.piece_at((0, 1)) is None

def test_regression_apply_move_rejects_occupied_point() -> None:
    """Check that a stone cannot replace a stone"""
    go = Go(9, 2)
    go.apply_move((4, 4))
    with pytest.raises(ValueError):
        go.apply_move((4, 4))
    assert go.piece_at((4, 4)) == 1
    assert go.turn == 2

def test_regression_apply_move_rejects_ko_recapture() -> None:
    """Check that apply_move enforces what legal_move reports"""
    go = Go(9, 2)
    apply_moves(go, KO_SHAPE)
    before = go.grid
    with pytest.raises(ValueError):
        go.apply_move((2, 1))
    assert go.grid == before

def test_regression_apply_move_rejects_suicide() -> None:
    """Check that a suicide leaves the board and the turn alone"""
    go = Go(9, 2)
    go.load_game(1, board_with(9, {
        (0, 0): 1, (1, 0): 2, (1, 1): 2, (0, 2): 2,
    }))
    before = go.grid
    with pytest.raises(ValueError):
        go.apply_move((0, 1))
    assert go.grid == before
    assert go.turn == 1

def test_regression_no_move_after_game_over() -> None:
    """Check that a finished game takes no more moves"""
    go = Go(9, 2)
    go.pass_turn()
    go.pass_turn()
    assert not go.legal_move((4, 4))
    assert go.available_moves == []
    with pytest.raises(ValueError):
        go.apply_move((4, 4))
    assert go.piece_at((4, 4)) is None

def test_regression_no_pass_after_game_over() -> None:
    """Check that a finished game takes no more passes"""
    go = Go(9, 2)
    go.pass_turn()
    go.pass_turn()
    with pytest.raises(ValueError):
        go.pass_turn()

def test_regression_simulate_move_rejects_illegal_move() -> None:
    """Check that simulating follows the same rules as playing"""
    go = Go(9, 2)
    go.apply_move((4, 4))
    with pytest.raises(ValueError):
        go.simulate_move((4, 4))

def test_simulate_move_off_board() -> None:
    """Check that simulating a position off the board raises an exception"""
    with pytest.raises(ValueError):
        Go(9, 2).simulate_move((9, 9))

def test_simulate_move_keeps_history_apart() -> None:
    """Check that a simulated game cannot change the real game's history"""
    go = Go(9, 2, True)
    apply_moves(go, [(0, 0), (1, 1)])
    history = set(go._prior_boards)
    go.simulate_move((2, 2)).simulate_move((3, 3))
    assert go._prior_boards == history

@pytest.mark.parametrize("side, players", [
    (0, 2), (-1, 2), (9, 0), (9, -1), (0, 1), (0, 0)
])
def test_regression_impossible_game(side: int, players: int) -> None:
    """Check that a game needs a board and a player"""
    with pytest.raises(ValueError):
        Go(side, players)

@pytest.mark.parametrize("turn", [0, -1])
def test_regression_load_game_rejects_bad_turn(turn: int) -> None:
    """Check that the player to move has to exist"""
    with pytest.raises(ValueError):
        Go(9, 2).load_game(turn, board_with(9, {}))

def test_load_game_rejects_turn_past_last_player() -> None:
    """Check that the turn cannot name a player after the last one"""
    with pytest.raises(ValueError):
        Go(9, 2).load_game(3, board_with(9, {}))

@pytest.mark.parametrize("piece", [0, 3, 5, -1])
def test_regression_load_game_rejects_bad_piece(piece: int) -> None:
    """Check that every stone has to belong to a player"""
    with pytest.raises(ValueError):
        Go(9, 2).load_game(1, board_with(9, {(4, 4): piece}))

def test_regression_load_game_rejects_ragged_rows() -> None:
    """Check that every row has to be as long as the board"""
    grid = board_with(9, {})
    grid[8] = [None] * 3
    with pytest.raises(ValueError):
        Go(9, 2).load_game(1, grid)

@pytest.mark.parametrize("grid", [
    [[None] * 9] * 8, [[None] * 9] * 10, [[None] * 10] * 9
])
def test_load_game_rejects_wrong_size(grid: BoardGridType) -> None:
    """Check that the grid has to be exactly the size of the board"""
    with pytest.raises(ValueError):
        Go(9, 2).load_game(1, grid)

def test_regression_load_game_copies_the_grid() -> None:
    """Check that later changes to the caller's grid do not reach the game"""
    go = Go(9, 2)
    grid = board_with(9, {})
    go.load_game(1, grid)
    grid[4][4] = 2
    assert go.piece_at((4, 4)) is None

def test_regression_load_game_restarts_a_finished_game() -> None:
    """Check that loading clears the end of the last game"""
    go = Go(9, 2)
    go.pass_turn()
    go.pass_turn()
    go.load_game(2, board_with(9, {}))
    assert not go.done
    assert go.turn == 2
    assert go.legal_move((4, 4))

def test_regression_load_game_forgets_passes() -> None:
    """Check that a pass before loading does not count afterwards"""
    go = Go(9, 2)
    go.pass_turn()
    go.load_game(2, board_with(9, {}))
    go.pass_turn()
    assert not go.done

def test_load_game_forgets_ko() -> None:
    """Check that loading wipes the history, as its docstring says"""
    go = Go(9, 2)
    apply_moves(go, KO_SHAPE)
    go.load_game(go.turn, go.grid)
    assert go.legal_move((2, 1))

def test_three_player_game_ends_after_three_passes() -> None:
    """Check that two passes are not enough with three players"""
    go = Go(9, 3)
    go.pass_turn()
    go.pass_turn()
    assert not go.done
    go.pass_turn()
    assert go.done

def test_grid_is_a_copy_after_a_capture() -> None:
    """Check that grid reflects captures and stays independent"""
    go = Go(9, 2)
    go.load_game(1, board_with(9, {(0, 0): 2, (0, 1): 1}))
    go.apply_move((1, 0))
    grid = go.grid
    assert grid[0][0] is None
    grid[0][0] = 1
    assert go.piece_at((0, 0)) is None

@pytest.mark.parametrize("turn", [1.0, 2.0, True])
def test_regression_load_game_rejects_turn_of_another_type(turn: int) -> None:
    """Check that a value merely equal to a player number is refused"""
    with pytest.raises(ValueError):
        Go(9, 2).load_game(turn, board_with(9, {}))

@pytest.mark.parametrize("piece", [1.0, 2.0, True])
def test_regression_load_game_rejects_piece_of_another_type(piece: int) -> None:
    """Check that a stone has to be a plain player number"""
    with pytest.raises(ValueError):
        Go(9, 2).load_game(1, board_with(9, {(4, 4): piece}))

def test_regression_load_game_accepts_tuple_rows_it_can_play_on() -> None:
    """Check that tuple rows become a board that can take a move"""
    go = Go(3, 2)
    go.load_game(1, tuple(tuple(row) for row in board_with(3, {})))
    go.apply_move((0, 0))
    assert go.piece_at((0, 0)) == 1

###
# Tests with more than two players, across passes and on refused moves
###

KO_FOR_PLAYERS_1_2 = [".12..", "12.2.", ".12..", ".....", "....."]
KO_FOR_PLAYERS_1_3 = [".13..", "13.3.", ".13..", ".....", "....."]

def parse_board(rows: list[str]) -> BoardGridType:
    """
    Helper function that builds a grid for load_game from a drawing.

    Args:
        rows: One string per row, with "." for an empty point

    Returns: The grid as a list of lists
    """
    return [[None if piece == "." else int(piece) for piece in row]
            for row in rows]

def play(game: Go, actions: list[tuple[int, int] | None]) -> None:
    """
    Helper function to apply a sequence of moves and passes to a Go game.

    Args:
        game: The Go game instance
        actions: The moves to apply, with None for a pass
    """
    for action in actions:
        if action is None:
            game.pass_turn()
        else:
            game.apply_move(action)

@pytest.mark.parametrize("players", [3, 4])
def test_simple_ko_with_more_players(players: int) -> None:
    """Check that ko binds every player count"""
    go = Go(5, players)
    go.load_game(1, parse_board(KO_FOR_PLAYERS_1_2))
    go.apply_move((1, 2))
    assert not go.legal_move((1, 1))
    assert (1, 1) not in go.available_moves
    with pytest.raises(ValueError):
        go.apply_move((1, 1))

@pytest.mark.parametrize("players, actions", [
    (3, [(0, 0), (0, 1), (1, 0), None, (1, 1), None]),
    (4, [(0, 0), (0, 1), (1, 0), None, None, (0, 0), (1, 1), (0, 1)]),
])
def test_superko_with_more_players(players: int,
                                   actions: list[tuple[int, int] | None]) -> None:
    """Check that superko binds every player count"""
    simple, superko = Go(2, players), Go(2, players, True)
    play(simple, actions)
    play(superko, actions)
    assert simple.legal_move((0, 0))
    assert not superko.legal_move((0, 0))

@pytest.mark.parametrize("players", [3, 4])
def test_single_stone_suicide_with_more_players(players: int) -> None:
    """Check that a stone cannot die alone among two other players"""
    go = Go(5, players)
    go.load_game(1, parse_board([".2...", "3....", ".....", ".....", "....."]))
    assert not go.legal_move((0, 0))

@pytest.mark.parametrize("players", [3, 4])
def test_group_suicide_with_more_players(players: int) -> None:
    """Check that a group cannot die among two other players"""
    go = Go(5, players)
    go.load_game(1, parse_board(["1.2..", "23...", ".....", ".....", "....."]))
    assert not go.legal_move((0, 1))

def test_region_touching_two_of_three_players_scores_for_neither() -> None:
    """Check that shared space belongs to nobody"""
    go = Go(3, 3)
    go.load_game(1, parse_board(["1.2", "1.2", "1.2"]))
    assert go.scores() == {1: 3, 2: 3, 3: 0}

def test_territory_counts_with_four_players() -> None:
    """Check that space touching one player belongs to that player"""
    go = Go(3, 4)
    go.load_game(1, parse_board(["4..", "4..", "4.."]))
    assert go.scores() == {1: 0, 2: 0, 3: 0, 4: 9}

def test_load_game_accepts_every_player() -> None:
    """Check that the last player can hold stones and the turn"""
    go = Go(3, 4)
    go.load_game(4, parse_board(["123", "4..", "..."]))
    assert go.turn == 4
    assert go.piece_at((1, 0)) == 4
    assert not go.done

def test_superko_survives_a_pass() -> None:
    """Check that a pass does not clear the history"""
    go = Go(2, 2, True)
    play(go, [(0, 0), (0, 1), (1, 0), (1, 1), None, (1, 0)])
    assert not go.legal_move((0, 0))

def test_ko_survives_a_pass_by_a_third_player() -> None:
    """
    Check that a pass leaves the ko ban in place. A pass does not change the
    board, so the board before the capture is still the immediately prior one.
    """
    go = Go(5, 3)
    go.load_game(1, parse_board(KO_FOR_PLAYERS_1_3))
    go.apply_move((1, 2))
    go.pass_turn()
    assert not go.legal_move((1, 1))

def test_simulate_move_rejects_ko() -> None:
    """Check that a simulation inherits the ko ban"""
    go = Go(9, 2)
    apply_moves(go, KO_SHAPE)
    with pytest.raises(ValueError):
        go.simulate_move((2, 1))

def test_simulate_move_rejects_suicide() -> None:
    """Check that a simulation refuses suicide"""
    go = Go(9, 2)
    go.load_game(2, board_with(9, {(0, 1): 1, (1, 0): 1}))
    with pytest.raises(ValueError):
        go.simulate_move((0, 0))

def test_simple_ko_ban_survives_a_simulation() -> None:
    """Check that simulating a move leaves the real ko ban in place"""
    go = Go(9, 2)
    apply_moves(go, KO_SHAPE)
    go.simulate_move((7, 7))
    assert not go.legal_move((2, 1))

def test_load_game_on_a_simulation_keeps_the_real_ban() -> None:
    """Check that wiping a simulation's history leaves the real game alone"""
    go = Go(9, 2)
    apply_moves(go, KO_SHAPE)
    go.simulate_move(None).load_game(1, go.grid)
    assert not go.legal_move((2, 1))

def test_simulated_move_clears_pending_passes() -> None:
    """Check that a move in a simulation resets the passes before it"""
    go = Go(9, 2)
    go.pass_turn()
    simulation = go.simulate_move((4, 4))
    simulation.pass_turn()
    assert not simulation.done

@pytest.mark.parametrize("superko", [False, True])
def test_simulated_capture_starts_a_ko(superko: bool) -> None:
    """Check that a capture in a simulation bans the recapture there"""
    go = Go(9, 2, superko)
    apply_moves(go, KO_SHAPE[:-1])
    simulation = go.simulate_move((1, 1))
    assert simulation.piece_at((2, 1)) is None
    assert not simulation.legal_move((2, 1))

@pytest.mark.parametrize("superko", [False, True])
def test_simulated_pass_keeps_the_ko(superko: bool) -> None:
    """Check that a pass in a simulation leaves the ko ban in place"""
    go = Go(5, 3, superko)
    go.load_game(1, parse_board(KO_FOR_PLAYERS_1_3))
    go.apply_move((1, 2))
    simulation = go.simulate_move(None)
    assert not simulation.legal_move((1, 1))

@pytest.mark.parametrize("read", [
    lambda go: go.legal_move((0, 0)),
    lambda go: go.available_moves,
    lambda go: go.scores(),
    lambda go: go.simulate_move((0, 0)),
], ids=["legal_move", "available_moves", "scores", "simulate_move"])
def test_reads_keep_the_pass_count(read: Callable[[Go], object]) -> None:
    """Check that looking at a game between two passes changes nothing"""
    go = Go(9, 2)
    go.pass_turn()
    read(go)
    go.pass_turn()
    assert go.done

@pytest.mark.parametrize("rows, cols, row, col", [(3, 4, 0, 3), (4, 3, 3, 0)])
def test_rectangular_corner_is_on_the_board(rows: int, cols: int, row: int,
                                            col: int) -> None:
    """Check that each axis of a board that is not square uses its own limit"""
    assert Board(rows, cols).get(row, col) is None

def test_rectangular_copy_keeps_its_shape() -> None:
    """Check that a copy of a board that is not square keeps each axis"""
    assert Board(2, 3).copy().freeze() == (2, 3, (None,) * 6)

def test_rectangular_set_grid_wants_its_own_shape() -> None:
    """Check that set_grid on a board that is not square checks each axis"""
    board = Board(2, 3)
    board.set_grid([[1, None, 2], [None, None, None]])
    assert board.get(0, 2) == 2
    with pytest.raises(ValueError):
        board.set_grid([[None] * 2] * 2)

@pytest.mark.parametrize("superko", [False, True])
def test_smallest_board_has_no_legal_move(superko: bool) -> None:
    """Check that a stone on a 1x1 board would have no liberty"""
    assert Go(1, 2, superko).available_moves == []

def test_one_player_game_ends_on_one_pass() -> None:
    """Check that the smallest player count works"""
    go = Go(2, 1)
    go.apply_move((0, 0))
    go.pass_turn()
    assert go.done

@pytest.mark.parametrize("pos", [(0.5, 0), (0, 0.5), (1.0, 0), (0, 1.0),
                                 (True, 0), (0, True)])
def test_regression_position_of_another_type(pos: tuple[int, int]) -> None:
    """Check that a position has to be plain numbers, in every entry point"""
    go = Go(9, 2)
    for call in (go.piece_at, go.legal_move, go.apply_move, go.simulate_move):
        with pytest.raises(ValueError, match="is not a point on the board"):
            call(pos)

@pytest.mark.parametrize("pos", [5, {1, 2}, [1, 2]])
def test_regression_position_that_is_not_a_tuple(pos: tuple[int, int]) -> None:
    """Check that only a tuple is a position, in every entry point"""
    go = Go(9, 2)
    for call in (go.piece_at, go.legal_move, go.apply_move, go.simulate_move):
        with pytest.raises(ValueError):
            call(pos)

def test_regression_none_is_not_a_position() -> None:
    """Check that None only means a pass to simulate_move"""
    go = Go(9, 2)
    for call in (go.piece_at, go.legal_move, go.apply_move):
        with pytest.raises(ValueError):
            call(None)  # type: ignore[arg-type]

@pytest.mark.parametrize("grid", [
    None, [None, None, None], [1, 2, 3], [{None, 1, 2}] * 3,
    {(None, None, None), (1, None, None), (None, 1, None)}
])
def test_regression_load_game_rejects_grid_of_another_shape(
        grid: BoardGridType) -> None:
    """Check that a grid that is not rows is refused rather than crashing"""
    with pytest.raises(ValueError):
        Go(3, 2).load_game(1, grid)

def test_superko_remembers_the_whole_game() -> None:
    """
    Check every answer in one game against a history kept here. This seed bans
    a board from 89 moves earlier.
    """
    rng = random.Random(323)
    go = Go(4, 2, True)
    seen = {go.frozengrid: 0}
    oldest_ban = 0

    for number in range(1, 400):
        no_history = Go(4, 2)
        no_history.load_game(go.turn, go.grid)
        for move in no_history.available_moves:
            board = no_history.simulate_move(move).frozengrid
            assert go.legal_move(move) == (board not in seen)
            if board in seen:
                oldest_ban = max(oldest_ban, number - seen[board])

        moves = go.available_moves
        if not moves:
            break
        go.apply_move(rng.choice(moves))
        seen.setdefault(go.frozengrid, number)

    assert oldest_ban == 89

@pytest.mark.parametrize("side, players", [
    (9, 2.5), (9, 1.5), (9, float("inf")), (9, 2.0), (9, True), (2.0, 2),
    (True, 2)
])
def test_regression_game_size_of_another_type(side: int, players: int) -> None:
    """Check that the side and the player count have to be plain whole numbers"""
    with pytest.raises(ValueError):
        Go(side, players)

def test_load_game_forgets_superko() -> None:
    """Check that loading wipes the history under superko too"""
    go = Go(9, 2, True)
    apply_moves(go, KO_SHAPE)
    go.load_game(go.turn, go.grid)
    assert go.legal_move((2, 1))

def test_load_game_keeps_superko() -> None:
    """Check that a loaded game still plays by the rule it was made with"""
    go = Go(2, 3, True)
    go.load_game(1, parse_board(["..", ".."]))
    play(go, [(0, 0), (0, 1), (1, 0), None, (1, 1), None])
    assert not go.legal_move((0, 0))

def test_loaded_group_without_liberties_stays_and_scores() -> None:
    """Check that a move diagonal to such a group leaves it alone"""
    go = Go(3, 2)
    go.load_game(1, parse_board([".1.", "121", ".1."]))
    go.apply_move((0, 0))
    assert go.piece_at((1, 1)) == 2
    assert go.scores() == {1: 8, 2: 1}

def test_loaded_group_without_liberties_keeps_its_owner_playing() -> None:
    """Check that its owner may still play anywhere that is not suicide"""
    go = Go(3, 2)
    go.load_game(2, parse_board(["21.", "1..", "..."]))
    assert go.available_moves == [(0, 2), (1, 1), (1, 2), (2, 0), (2, 1),
                                  (2, 2)]

def test_legal_move_off_the_board_after_the_game() -> None:
    """Check that a finished game still refuses a position that cannot exist"""
    go = Go(9, 2)
    go.pass_turn()
    go.pass_turn()
    with pytest.raises(ValueError):
        go.legal_move((9, 9))

def test_simulate_move_keeps_the_type() -> None:
    """Check that a simulation is an object of the same type, as documented"""
    class Variant(Go):
        pass

    assert type(Variant(9, 2).simulate_move((0, 0))) is Variant

def test_freeze_layout() -> None:
    """Check that freeze gives the size and then the rows in order"""
    board = Board(2, 3)
    board.set(0, 1, 1)
    assert board.freeze() == (2, 3, (None, 1, None, None, None, None))

def test_frozengrid_is_the_frozen_board() -> None:
    """Check that a game freezes its board the same way, size first"""
    go = Go(2, 2)
    go.apply_move((0, 1))
    assert go.frozengrid == (2, 2, (None, 1, None, None))

def test_regression_superko_remembers_the_loaded_board() -> None:
    """Check that the board a game was loaded with is banned like any other"""
    go = Go(5, 2, True)
    go.load_game(1, parse_board(KO_FOR_PLAYERS_1_2))
    go.apply_move((1, 2))
    assert not go.legal_move((1, 1))

def test_four_way_tie() -> None:
    """Check that every player tied for the lead is in the outcome"""
    go = Go(3, 4)
    for _ in range(4):
        go.pass_turn()
    assert go.outcome == [1, 2, 3, 4]

def test_regression_simulate_move_after_the_game() -> None:
    """Check that a finished game cannot be simulated forward"""
    go = Go(9, 2)
    go.pass_turn()
    go.pass_turn()
    for pos in ((4, 4), None):
        with pytest.raises(ValueError):
            go.simulate_move(pos)

@pytest.mark.parametrize("pos", [(), (1,), (1, 2, 3)])
def test_position_of_another_length(pos: tuple[int, int]) -> None:
    """Check that a position has exactly a row and a column"""
    go = Go(9, 2)
    for call in (go.piece_at, go.legal_move, go.apply_move, go.simulate_move):
        with pytest.raises(ValueError, match="is not a position"):
            call(pos)

def test_board_grid_is_the_board_itself() -> None:
    """Check that grid gives the internal rows, as documented, not a copy"""
    board = Board(2, 2)
    board.grid[0][0] = 1
    assert board.get(0, 0) == 1

###
# Every refused call leaves the whole game as it was
###

OTHER_GRID = parse_board(["2....", ".....", ".....", ".....", "....."])
BAD_PIECE_GRID = parse_board(["2....", ".....", ".....", ".....", "....7"])

def game_state(go: Go) -> tuple[object, ...]:
    """
    Helper function that captures everything a refused call must leave alone.

    Args:
        go: The Go game instance

    Returns: The grid, turn, end flag, pass count, history and legal moves
    """
    return (go.grid, go.turn, go.done, go._passes, go._prior_boards,
            go.available_moves)

def game_in_a_ko(superko: bool) -> Go:
    """
    Helper function that builds a three player game where player 3 may not
    retake a ko at (1, 1) or play the suicide at (0, 0), with a pass pending.

    Args:
        superko: Whether the game uses superko

    Returns: The game
    """
    go = Go(5, 3, superko)
    go.load_game(1, parse_board(KO_FOR_PLAYERS_1_3))
    go.apply_move((1, 2))
    go.pass_turn()
    return go

def finished_game(superko: bool) -> Go:
    """
    Helper function that builds a three player game that has ended.

    Args:
        superko: Whether the game uses superko

    Returns: The game
    """
    go = Go(5, 3, superko)
    go.apply_move((2, 2))
    for _ in range(3):
        go.pass_turn()
    return go

REFUSALS = [
    pytest.param(game_in_a_ko, lambda go: go.apply_move((1, 1)), id="ko"),
    pytest.param(game_in_a_ko, lambda go: go.apply_move((0, 0)), id="suicide"),
    pytest.param(game_in_a_ko, lambda go: go.apply_move((1, 0)), id="occupied"),
    pytest.param(game_in_a_ko, lambda go: go.apply_move((5, 0)), id="off board"),
    pytest.param(game_in_a_ko, lambda go: go.simulate_move((1, 1)),
                 id="simulated ko"),
    pytest.param(finished_game, lambda go: go.apply_move((0, 0)),
                 id="move after the end"),
    pytest.param(finished_game, lambda go: go.pass_turn(),
                 id="pass after the end"),
    pytest.param(finished_game, lambda go: go.simulate_move(None),
                 id="simulated pass after the end"),
] + [
    pytest.param(make_game, refusal, id=f"{label} on {make_game.__name__}")
    for make_game in (game_in_a_ko, finished_game)
    for label, refusal in (
        ("load with a bad turn", lambda go: go.load_game(0, OTHER_GRID)),
        ("load with a bad piece", lambda go: go.load_game(1, BAD_PIECE_GRID)),
        ("load with a short grid", lambda go: go.load_game(1, OTHER_GRID[:4])),
        ("load with a ragged grid",
         lambda go: go.load_game(1, OTHER_GRID[:4] + [[None] * 6])),
    )
]

@pytest.mark.parametrize("superko", [False, True])
@pytest.mark.parametrize("make_game, refusal", REFUSALS)
def test_refused_call_changes_nothing(make_game: Callable[[bool], Go],
                                      refusal: Callable[[Go], object],
                                      superko: bool) -> None:
    """Check that a refused call raises ValueError and leaves every part alone"""
    go = make_game(superko)
    before = game_state(go)
    with pytest.raises(ValueError):
        refusal(go)
    assert game_state(go) == before

@pytest.mark.parametrize("grid", [
    [[1]], [[None] * 3] * 3, [[None] * 2, [None]], [[None] * 2] * 3, None,
    [1, 2], [[None] * 2, 5]
])
def test_regression_set_grid_rejects_another_size(grid: BoardGridType) -> None:
    """Check that a board keeps the size it was made with"""
    board = Board(2, 2)
    with pytest.raises(ValueError):
        board.set_grid(grid)
    assert board.grid == [[None, None], [None, None]]

def test_superko_remembers_every_board_of_a_long_game() -> None:
    """
    Check that a game over a thousand moves long still remembers every board
    it has left, so any memory shorter than the game fails
    """
    rng = random.Random(0)
    go = Go(13, 4, True)
    left: set[FrozenBoardGridType] = set()
    while moves := go.available_moves:
        left.add(go.frozengrid)
        go.apply_move(rng.choice(moves))
    assert len(left) == 1076
    assert go._prior_boards == left

@pytest.mark.parametrize("superko", [False, True])
def test_superko_bans_a_board_from_over_a_thousand_moves_back(
        superko: bool) -> None:
    """
    Build ten kos apart from each other, then retake one ko per move in Gray
    code order, so every board is new. After 1,022 retakes, retaking the
    tenth ko would bring back the board from just after the first retake.
    Superko must still refuse it; simple ko allows it. The walk stops short
    of 1,023 retakes, whose board is the one before the last ko was built.
    """
    corners = [(5 * (i // 4), 5 * (i % 4)) for i in range(10)]
    go = Go(19, 2, superko)
    for r, c in corners:
        apply_moves(go, [(r + dr, c + dc) for dr, dc in KO_SHAPE])

    def retake(ko: int, player: int) -> tuple[int, int]:
        """Passes if the other player is to move, then gives the ko point"""
        if go.turn != player:
            go.pass_turn()
        r, c = corners[ko]
        return (r + 2, c + 1) if player == 1 else (r + 1, c + 1)

    for i in range(1, 1023):
        gray = i ^ i >> 1
        flipped = gray ^ (i - 1) ^ (i - 1) >> 1
        go.apply_move(retake(flipped.bit_length() - 1,
                             1 if gray & flipped else 2))

    point = retake(9, 2)
    assert go.legal_move(point) != superko

@pytest.mark.parametrize("superko", [False, True])
@pytest.mark.parametrize("rows, actions, point", [
    (["21.", ".22", "122"], [(1, 0), (0, 0)], (2, 0)),
    (["22.", "112", "11."], [(0, 2), (0, 0), None], (0, 1)),
], ids=["middle-stone-captures", "middle-stone-captures-nothing"])
def test_simple_ko_allows_a_board_from_three_moves_back(
        rows: list[str], actions: list[tuple[int, int] | None],
        point: tuple[int, int], superko: bool) -> None:
    """
    Check that simple ko bans only the board before the last move, whether or
    not the move between captured anything. The third stone brings back the
    board from before the first. Superko must refuse it.
    """
    go = Go(3, 2, superko)
    go.load_game(1, parse_board(rows))
    play(go, actions)
    assert go.legal_move(point) != superko
