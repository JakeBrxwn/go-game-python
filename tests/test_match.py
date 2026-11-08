"""
Tests for Match: its states, how it ends, and the settings it accepts.
"""
import random
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from go_python.bot import Random, Smart
from go_python.match import (EndReason, GameConfig, Match, MatchState,
                             run_series)

Move = tuple[int, int] | None

#
# GameConfig
#

@pytest.mark.parametrize("size, superko, seats", [
    (6, False, ("human", "human")),
    (30, True, ("random", "smart", "human", "smart")),
    (19, False, ("smart", "random", "human")),
])
def test_config_accepts_every_edge(size: int, superko: bool,
                                   seats: tuple[str, ...]) -> None:
    """Check the smallest and largest settings are accepted"""
    config = GameConfig(size, superko, seats)
    assert (config.size, config.superko, config.seats) == (size, superko, seats)

@pytest.mark.parametrize("settings, field", [
    ({"size": 5}, "size"),
    ({"size": 31}, "size"),
    ({"size": 9.0}, "size"),
    ({"size": True}, "size"),
    ({"superko": 1}, "superko"),
    ({"superko": None}, "superko"),
    ({"seats": ("human",)}, "seats"),
    ({"seats": ("human",) * 5}, "seats"),
    ({"seats": ("human", "alien")}, "seats"),
    ({"seats": ["human", "human"]}, "seats"),
])
def test_config_refuses_bad_settings(settings: dict[str, object],
                                     field: str) -> None:
    """Check each bad setting is refused with a message naming it"""
    with pytest.raises(ValueError, match=field):
        GameConfig(**settings)  # type: ignore[arg-type]

#
# States
#

@pytest.mark.parametrize("seats, state", [
    (("human", "smart"), MatchState.HUMAN_TURN),
    (("random", "human"), MatchState.BOT_TURN),
    (("smart", "random"), MatchState.BOT_TURN),
])
def test_first_state_follows_the_first_seat(seats: tuple[str, ...],
                                            state: MatchState) -> None:
    """Check the match waits for whoever sits in seat one"""
    match = Match(GameConfig(9, False, seats))
    assert match.state is state
    assert match.result is None

def test_play_hands_the_turn_to_a_bot_and_back() -> None:
    """Check play moves to the bot's turn and step comes back"""
    match = Match(GameConfig(9, False, ("human", "random")))
    match.play((4, 4))
    assert match.state is MatchState.BOT_TURN
    pos = match.step()
    assert pos is not None and match.game.piece_at(pos) == 2
    assert match.state is MatchState.HUMAN_TURN
    assert match.moves == 2

def test_people_take_turns_with_each_other() -> None:
    """Check a match between people stays on a person's turn"""
    match = Match(GameConfig(9, False, ("human", "human", "human")))
    for pos in [(0, 0), (1, 1), (2, 2)]:
        match.play(pos)
        assert match.state is MatchState.HUMAN_TURN
    assert match.game.turn == 1

def test_bots_take_turns_with_each_other() -> None:
    """Check a match between bots stays on a bot's turn"""
    match = Match(GameConfig(9, False, ("random", "smart")))
    match.step()
    match.step()
    assert match.state is MatchState.BOT_TURN
    assert match.moves == 2

def test_play_on_a_bot_turn_changes_nothing() -> None:
    """Check a person cannot move for a bot"""
    match = Match(GameConfig(9, False, ("smart", "human")))
    with pytest.raises(ValueError, match="person"):
        match.play((0, 0))
    with pytest.raises(ValueError, match="person"):
        match.hint()
    assert match.game.piece_at((0, 0)) is None
    assert match.moves == 0

def test_step_on_a_human_turn_changes_nothing() -> None:
    """Check a bot cannot move for a person"""
    match = Match(GameConfig(9, False, ("human", "smart")))
    with pytest.raises(ValueError, match="bot"):
        match.step()
    assert match.game.grid == Match(match.config).game.grid
    assert match.moves == 0

def test_illegal_move_changes_nothing() -> None:
    """Check an illegal move is refused and not counted"""
    match = Match(GameConfig(9, False, ("human", "human")))
    match.play((0, 0))
    with pytest.raises(ValueError):
        match.play((0, 0))
    assert match.game.turn == 2
    assert match.moves == 1

def test_bot_pass_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check step reports a bot's pass as None"""
    monkeypatch.setattr("go_python.bot.Random.move", lambda self, game: None)
    match = Match(GameConfig(6, False, ("human", "random")))
    match.play(None)
    assert match.step() is None
    assert match.result is not None
    assert match.result.reason is EndReason.PASSES

# Simple ko allows (1, 2) after these moves; superko bans it
SUPERKO_ONLY_BAN = [(0, 2), (0, 1), (0, 3), (1, 0), (1, 4), (1, 2), (2, 2),
                    (2, 1), (2, 3), (1, 3), (1, 1)]

def test_match_plays_by_the_chosen_ko_rule() -> None:
    """Check the ko rule in the settings reaches the game"""
    simple = Match(GameConfig(19, False, ("human", "human")))
    superko = Match(GameConfig(19, True, ("human", "human")))
    for match in (simple, superko):
        for pos in SUPERKO_ONLY_BAN:
            match.play(pos)
    simple.play((1, 2))
    with pytest.raises(ValueError):
        superko.play((1, 2))

def test_hint_suggests_a_legal_move() -> None:
    """Check a hint is a move the person could play"""
    match = Match(GameConfig(9, False, ("human", "smart")))
    pos = match.hint()
    assert pos is not None and match.game.legal_move(pos)
    assert match.moves == 0

def same_seed(choose: Callable[..., Move], seed: int, *args: object) \
        -> Move:
    """
    Runs a bot's choice with the random module seeded.

    Args:
        choose: What picks the move
        seed: The seed
        args: What to pass to choose

    Returns: The move it picked
    """
    random.seed(seed)
    return choose(*args)

@pytest.mark.parametrize("seats", [("random", "smart"), ("smart", "random")])
def test_each_seat_is_played_by_its_own_bot(seats: tuple[str, ...]) -> None:
    """Check every move comes from the bot named for the seat to move"""
    match = Match(GameConfig(9, False, seats))
    for seat in seats * 4:
        bot = Smart() if seat == "smart" else Random()
        expected = same_seed(bot.move, match.moves, match.game)
        assert same_seed(match.step, match.moves) == expected

def test_hint_is_what_smart_would_play() -> None:
    """Check a hint is Smart's move for the person to move"""
    match = Match(GameConfig(9, False, ("human", "random")))
    for seed in range(4):
        expected = same_seed(Smart().move, seed, match.game)
        assert same_seed(match.hint, seed) == expected
        match.play(expected)
        match.step()

#
# Endings
#

def test_every_player_passing_finishes() -> None:
    """Check a match ends when every player passes, with all tied"""
    match = Match(GameConfig(9, False, ("human", "human", "human")))
    for _ in range(3):
        match.play(None)
    assert match.state is MatchState.FINISHED
    assert match.result is not None
    assert match.result.reason is EndReason.PASSES
    assert match.result.winners == (1, 2, 3)
    assert match.result.scores == {1: 0, 2: 0, 3: 0}

def test_winner_has_the_most_area() -> None:
    """Check the player with the most area wins"""
    match = Match(GameConfig(9, False, ("human", "human")))
    match.play((4, 4))
    match.play(None)
    match.play(None)
    assert match.result is not None
    assert match.result.winners == (1,)
    assert match.result.scores == {1: 81, 2: 0}

def test_move_limit_is_three_times_the_area() -> None:
    """Check the move limit follows the board size"""
    assert Match(GameConfig(6)).move_limit == 108
    assert Match(GameConfig(19)).move_limit == 1083

def test_move_limit_finishes_and_scores(monkeypatch: pytest.MonkeyPatch) \
        -> None:
    """Check reaching the move limit ends the match and picks winners"""
    monkeypatch.setattr(Match, "move_limit", property(lambda self: 3))
    match = Match(GameConfig(9, False, ("human", "human")))
    match.play((0, 0))
    match.play(None)
    assert match.state is MatchState.HUMAN_TURN
    match.play((1, 1))
    assert match.result is not None
    assert match.result.reason is EndReason.MOVE_LIMIT
    assert match.result.winners == (1,)
    assert match.result.scores == {1: 81, 2: 0}

def test_last_pass_on_the_limit_counts_as_passes(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a game whose final pass is also the last move allowed ended by
    passing"""
    monkeypatch.setattr(Match, "move_limit", property(lambda self: 2))
    match = Match(GameConfig(9, False, ("human", "human")))
    match.play(None)
    match.play(None)
    assert match.result is not None
    assert match.result.reason is EndReason.PASSES

def test_abort_finishes_with_no_winners() -> None:
    """Check leaving a match ends it with nobody winning"""
    match = Match(GameConfig(9, False, ("human", "smart")))
    match.play((2, 2))
    match.abort()
    assert match.state is MatchState.FINISHED
    assert match.result is not None
    assert match.result.reason is EndReason.ABORTED
    assert match.result.winners == ()
    assert match.result.scores == {1: 81, 2: 0}

def test_abort_keeps_a_finished_result() -> None:
    """Check leaving after the end does not change how it ended"""
    match = Match(GameConfig(9, False, ("human", "human")))
    match.play(None)
    match.play(None)
    result = match.result
    match.abort()
    assert match.result is result

def test_finished_match_takes_no_more_moves() -> None:
    """Check nothing can move once the match is over"""
    match = Match(GameConfig(9, False, ("human", "random")))
    match.abort()
    for call in (lambda: match.play((0, 0)), match.step, match.hint):
        with pytest.raises(ValueError):
            call()
    assert match.moves == 0

#
# Series
#

def test_series_refuses_a_human_seat() -> None:
    """Check a headless series cannot wait for a person"""
    with pytest.raises(ValueError, match="bot"):
        run_series(GameConfig(6, False, ("random", "human")), 1)

@pytest.mark.parametrize("games", [0, -3])
def test_series_refuses_no_games(games: int) -> None:
    """Check a series of no games is refused, not reported"""
    with pytest.raises(ValueError, match="one game"):
        run_series(GameConfig(6, False, ("random", "random")), games)

def test_series_counts_every_game() -> None:
    """Check each game is a win for one player or a tie"""
    random.seed(8)
    series = run_series(GameConfig(6, False, ("random", "random")), 6)
    assert series.games == 6
    assert sum(series.wins.values()) + series.ties == 6
    assert series.moves > 6

@pytest.mark.parametrize("moves, wins", [
    ([(0, 0)], {1: 1, 2: 0}),
    ([None, (0, 0)], {1: 0, 2: 1}),
])
def test_series_credits_the_winner(monkeypatch: pytest.MonkeyPatch,
                                   moves: list[tuple[int, int] | None],
                                   wins: dict[int, int]) -> None:
    """Check a win goes to the player who owns the board"""
    played = iter(moves)
    monkeypatch.setattr(Match, "move_limit",
                        property(lambda self: len(moves)))
    monkeypatch.setattr("go_python.bot.Random.move",
                        lambda self, game: next(played))
    series = run_series(GameConfig(6, False, ("random", "random")), 1)
    assert series.wins == wins
    assert series.ties == 0

def test_series_counts_a_tie(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a game with tied winners counts as a tie"""
    monkeypatch.setattr(Match, "move_limit", property(lambda self: 1))
    monkeypatch.setattr("go_python.bot.Random.move", lambda self, game: None)
    series = run_series(GameConfig(6, False, ("random", "random")), 2)
    assert series.ties == 2
    assert series.wins == {1: 0, 2: 0}
    assert series.moves == 2

#
# Ownership
#

def test_only_match_changes_the_game() -> None:
    """Check no other module moves, passes or loads the game behind Match"""
    source = Path(__file__).parent.parent / "src" / "go_python"
    changers = re.compile(r"\.(apply_move|pass_turn|load_game)\(")
    offenders = [path.name for path in sorted(source.glob("*.py"))
                 if path.name not in ("go.py", "match.py")
                 and changers.search(path.read_text())]
    assert offenders == []
