import csv
from pathlib import Path

import pytest

from go_python.board import Board
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
    Helper function that gets string represention of moves needed to set up
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
        initial_board = [[None for _ in range(g.side)] for _ in range(g.side)]
        turn = 1
        for move in moves:
            row, col = move
            initial_board[row][col] = turn
            turn += 1
            if turn > g.num_players:
                turn = turn % g.num_players
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
    (9, 2), (13, 2), (19, 2)
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
    """Check scoring of multiple terrirtories"""
    g = Go(19,3)
    set_up_test(g, "test_19x19_multiple_territories_three_player")
    assert g.scores()[1] == 5 and g.scores()[2] == 4 and g.scores()[3] == 4

def test_19x19_outcome() -> None:
    """Check outcome for three player"""
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
    (-1, -1), (-1, 5), (-1, 19), (5, -1), (5, 19), (19, -1), (19, 5), (19, 19)
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
# Regression tests: each of these fails on the code before its fix
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
    """Check that a board that is not square checks each axis on its own"""
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

def test_superko_forbids_any_earlier_board_not_just_the_last() -> None:
    """Check that superko blocks what simple ko allows"""
    moves = [(0, 2), (0, 1), (0, 3), (1, 0), (1, 4), (1, 2), (2, 2), (2, 1),
             (2, 3), (1, 3), (1, 1)]
    simple, superko = Go(19, 2), Go(19, 2, True)
    apply_moves(simple, moves)
    apply_moves(superko, moves)
    assert simple.legal_move((1, 2))
    assert not superko.legal_move((1, 2))

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

def test_single_stone_suicide_is_illegal() -> None:
    """Check that a stone cannot fill the last liberty of itself"""
    go = Go(9, 2)
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

@pytest.mark.parametrize("side, players", [(0, 2), (-1, 2), (9, 0), (9, -1)])
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

def test_load_game_rejects_wrong_row_count() -> None:
    """Check that the grid has to be as tall as the board"""
    with pytest.raises(ValueError):
        Go(9, 2).load_game(1, board_with(9, {})[:8])

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
    go.load_game(1, board_with(9, {}))
    assert not go.done
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
