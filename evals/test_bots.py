"""
Holds the bots to their targets: Smart beats Random, bot games end by passing
rather than by the move limit, and Smart answers fast enough for a window.
"""
import random
import statistics
import time

from go_python.bot import Smart
from go_python.go import Go
from go_python.match import EndReason, GameConfig, Match, MatchState

STRENGTH_GAMES = 200
MIN_SMART_WIN_RATE = 0.9
ENDING_GAMES = 60
MIN_PASSING_ENDS = 0.95
EMPTY_BOARD_BUDGET_MS = 100
SLOWEST_MOVE_BUDGET_MS = 250

def play_out(seats: tuple[str, ...], size: int, seed: int) -> Match:
    """
    Plays a bot-only match to the end.

    Args:
        seats: The bots, in turn order
        size: The size of the board
        seed: Seed for the bots' random choices

    Returns: The finished match
    """
    random.seed(seed)
    match = Match(GameConfig(size, False, seats))
    while match.state is MatchState.BOT_TURN:
        match.step()
    return match

def test_smart_beats_random() -> None:
    """Check that Smart wins at least 90% of 9x9 games, moving first or not"""
    wins = 0
    for game in range(STRENGTH_GAMES):
        seats = ("smart", "random") if game % 2 == 0 else ("random", "smart")
        result = play_out(seats, 9, 1000 + game).result
        assert result is not None
        wins += result.winners == (seats.index("smart") + 1,)
    print(f"\nSmart beat Random in {wins} of {STRENGTH_GAMES} games")
    assert wins >= MIN_SMART_WIN_RATE * STRENGTH_GAMES

def test_bot_games_end_by_passing() -> None:
    """Check that at least 95% of bot games end because every bot passed"""
    pairings = [("random", "random"), ("smart", "random"),
                ("random", "smart"), ("smart", "smart")]
    passing = 0
    for pairing in pairings:
        for game in range(ENDING_GAMES):
            result = play_out(pairing, 9, 2000 + game).result
            assert result is not None
            passing += result.reason is EndReason.PASSES
    total = len(pairings) * ENDING_GAMES
    print(f"\n{passing} of {total} bot games ended by passing")
    assert passing >= MIN_PASSING_ENDS * total

def test_smart_answers_fast_on_the_largest_common_board() -> None:
    """Check Smart's time on an empty 19x19 board and in a whole game"""
    empty = Go(19, 2)
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        Smart().move(empty)
        samples.append((time.perf_counter() - start) * 1000)
    empty_ms = statistics.median(samples)

    random.seed(3)
    match = Match(GameConfig(19, False, ("smart", "random")))
    slowest_ms = 0.0
    while match.state is MatchState.BOT_TURN:
        smart_moves = match.game.turn == 1
        start = time.perf_counter()
        match.step()
        if smart_moves:
            slowest_ms = max(slowest_ms, (time.perf_counter() - start) * 1000)

    print(f"\nSmart: empty 19x19 {empty_ms:.1f} ms, slowest move "
          f"{slowest_ms:.1f} ms")
    assert empty_ms <= EMPTY_BOARD_BUDGET_MS
    assert slowest_ms <= SLOWEST_MOVE_BUDGET_MS
