"""
Tests for the bots: they pick legal moves, keep their own eyes, and repeat
themselves when seeded. Smart's rules each get a small board that shows them.
"""
import random

import pytest

from go_python.bot import Random, Smart, is_own_eye
from go_python.go import Go

def load(rows: list[str], turn: int = 1) -> Go:
    """
    Builds a two-player game from rows of text.

    Args:
        rows: One string per row, "." for empty and a digit for a stone
        turn: The player to move

    Returns: The game
    """
    go = Go(len(rows), 2)
    go.load_game(turn, [[None if ch == "." else int(ch) for ch in row]
                        for row in rows])
    return go

# Player 1 has two eyes and nothing else; player 2 has no legal move
ONLY_EYES = ["1.1", "111", "1.1"]

@pytest.mark.parametrize("pos, expected", [
    ((0, 1), True),
    ((2, 1), True),
])
def test_is_own_eye_on_an_edge(pos: tuple[int, int], expected: bool) -> None:
    """Check that an edge point surrounded by the mover's stones is an eye"""
    assert is_own_eye(load(ONLY_EYES), pos) == expected

def test_is_own_eye_needs_every_neighbor() -> None:
    """Check that one empty or enemy neighbor stops a point being an eye"""
    go = load(["1.1", "1.2", "..."])
    assert not is_own_eye(go, (0, 1))
    assert not is_own_eye(go, (2, 0))

def test_is_own_eye_belongs_to_the_mover() -> None:
    """Check that the opponent's eye is not the mover's eye"""
    assert not is_own_eye(load(ONLY_EYES, turn=2), (0, 1))

@pytest.mark.parametrize("bot", [Random(), Smart()])
def test_bot_passes_when_only_its_eyes_are_left(bot: Random | Smart) -> None:
    """Check that a bot passes rather than fill its own eyes"""
    assert bot.move(load(ONLY_EYES)) is None

@pytest.mark.parametrize("bot", [Random(), Smart()])
def test_bot_passes_with_no_legal_move(bot: Random | Smart) -> None:
    """Check that a bot passes when every point is illegal for it"""
    assert bot.move(load(ONLY_EYES, turn=2)) is None

@pytest.mark.parametrize("bot", [Random(), Smart()])
@pytest.mark.parametrize("players, superko", [(2, False), (4, True)])
def test_bot_moves_are_legal_and_keep_eyes(bot: Random | Smart, players: int,
                                           superko: bool) -> None:
    """Check every move in a seeded game is legal and fills no own eye"""
    random.seed(4)
    go = Go(7, players, superko)
    for _ in range(3 * 7 * 7):
        if go.done:
            break
        pos = bot.move(go)
        if pos is not None:
            assert go.legal_move(pos)
            assert not is_own_eye(go, pos)
        go = go.simulate_move(pos)

def test_bot_does_not_change_the_game() -> None:
    """Check that choosing a move leaves the game as it was"""
    go = load(["12.", "...", "..."])
    before = go.frozengrid, go.turn
    for bot in (Random(), Smart()):
        bot.move(go)
        assert (go.frozengrid, go.turn) == before

@pytest.mark.parametrize("bot", [Random(), Smart()])
def test_bot_repeats_when_seeded(bot: Random | Smart) -> None:
    """Check that the same seed gives the same game"""
    def moves() -> list[tuple[int, int] | None]:
        random.seed(11)
        go = Go(6, 2)
        played: list[tuple[int, int] | None] = []
        while not go.done:
            played.append(bot.move(go))
            go = go.simulate_move(played[-1])
        return played

    assert moves() == moves()

#
# Smart's rules
#

@pytest.mark.parametrize("rows, expected", [
    # Takes a free capture
    ([".....", ".....", "..1..", ".121.", "....."], (4, 2)),
    # Takes two stones even though its stone is left in atari
    ([".112.", "122.2", ".112.", ".....", "....."], (1, 3)),
    # Saves a stone in atari
    ([".....", "..2..", ".212.", ".....", "....."], (3, 2)),
    # Saves a chain whose only other liberty is its own eye
    (["1.1..", "1112.", "222..", ".....", "....."], (0, 3)),
])
def test_smart_plays_the_tactical_move(rows: list[str],
                                       expected: tuple[int, int]) -> None:
    """Check Smart captures and saves stones before anything else"""
    assert Smart().move(load(rows)) == expected

def test_smart_presses_the_weakest_enemy_chain() -> None:
    """Check Smart takes a liberty of the enemy chain that has fewest"""
    go = load(["......", ".1111.", "122221", ".11...", "......",
               "......"])
    assert Smart().move(go) in {(3, 3), (3, 4)}

@pytest.mark.parametrize("side", [6, 19, 30])
def test_smart_opens_off_the_edge(side: int) -> None:
    """Check Smart's first move on an empty board is off the two edge lines"""
    r, c = Smart().move(Go(side, 2)) or (0, 0)
    assert min(r, c, side - 1 - r, side - 1 - c) >= 2

def test_smart_does_not_fill_its_eye_to_save_a_stone() -> None:
    """Check Smart leaves its own eye empty even when filling it would save
    the stone in atari next to it"""
    assert Smart().move(load(["1.1.", "21..", "2...", "...."])) != (0, 1)

def test_smart_does_not_put_itself_in_atari() -> None:
    """Check Smart passes rather than play a stone that could be captured
    at once, though the move is legal"""
    go = load(["..22", "2222", "2222", "2222"])
    assert go.legal_move((0, 1))
    assert Smart().move(go) is None

def test_smart_does_not_take_a_ko() -> None:
    """Check Smart leaves a one-stone capture that its opponent could take
    straight back"""
    go = load([".12.", "12.2", ".12.", "...."])
    assert go.legal_move((1, 2))
    assert Smart().move(go) != (1, 2)

def test_smart_passes_once_the_game_is_over() -> None:
    """Check Smart passes on a finished game, where no move is legal"""
    assert Smart().move(Go(6, 2).simulate_move(None).simulate_move(None)) \
        is None
