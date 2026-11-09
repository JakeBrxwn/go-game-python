"""
A match of Go: whose turn it is, when the match ends and why. Every
frontend drives a Match, and only a Match changes the game.
"""
from dataclasses import dataclass
from enum import Enum

from go_python.bot import Random, Smart
from go_python.go import Go

#
# Settings
#

# Names every frontend uses for the players, in turn order
PLAYER_NAMES = ("Black", "White", "Red", "Blue")
SEAT_KINDS = ("human", "random", "smart")

@dataclass(frozen=True)
class GameConfig:
    """
    The settings of a match, checked once when they are made.

    Args:
        size: Number of points on each side of the board, 6 to 30.
        superko: True for superko, False for simple ko.
        seats: One entry per player, 2 to 4 of them, each "human",
        "random" or "smart".

    Raises:
        ValueError: If any setting is out of range, naming the setting.
    """
    size: int = 19
    superko: bool = False
    seats: tuple[str, ...] = ("human", "smart")

    def __post_init__(self) -> None:
        """Refuses any setting outside the ranges above"""
        if type(self.size) is not int or not 6 <= self.size <= 30:
            raise ValueError("size must be a whole number from 6 to 30")
        if type(self.superko) is not bool:
            raise ValueError("superko must be True or False")
        if not isinstance(self.seats, tuple) or \
           not 2 <= len(self.seats) <= len(PLAYER_NAMES) or \
           any(seat not in SEAT_KINDS for seat in self.seats):
            raise ValueError("seats must be 2 to 4 of "
                             + ", ".join(SEAT_KINDS))

#
# One match
#

class MatchState(Enum):
    """
    What the match is waiting for.
    """
    HUMAN_TURN = "human turn"
    BOT_TURN = "bot turn"
    FINISHED = "finished"

class EndReason(Enum):
    """
    Why a match finished.
    """
    PASSES = "every player passed"
    MOVE_LIMIT = "the move limit was reached"
    ABORTED = "the match was left"

@dataclass(frozen=True)
class MatchResult:
    """
    How a match finished. Winners are player numbers, from 1, and scores map
    each player number to its area. An aborted match has no winners.
    """
    reason: EndReason
    winners: tuple[int, ...]
    scores: dict[int, int]

class Match:
    """
    One game of Go between seats that are people or bots.
    """
    _config: GameConfig
    _game: Go
    _bots: dict[int, Random | Smart]
    _moves: int
    _result: MatchResult | None

    def __init__(self, config: GameConfig) -> None:
        """
        Constructor

        Args:
            config: The settings of the match
        """
        self._config = config
        self._game = Go(config.size, len(config.seats), config.superko)
        self._bots = {player: Smart() if seat == "smart" else Random()
                      for player, seat in enumerate(config.seats, start=1)
                      if seat != "human"}
        self._moves = 0
        self._result = None

    #
    # Properties
    #

    @property
    def config(self) -> GameConfig:
        """
        Returns the settings of the match
        """
        return self._config

    @property
    def game(self) -> Go:
        """
        Returns the game, for reading. Change it only through the match.
        """
        return self._game

    @property
    def moves(self) -> int:
        """
        Returns the number of moves and passes made so far
        """
        return self._moves

    @property
    def move_limit(self) -> int:
        """
        Returns the number of moves and passes after which the match ends,
        3 x size x size, the same cap the Michi engine uses
        """
        return 3 * self._config.size * self._config.size

    @property
    def state(self) -> MatchState:
        """
        Returns what the match is waiting for, worked out from the game and
        the seats so it can never disagree with them
        """
        if self._result is not None:
            return MatchState.FINISHED
        if self._game.turn in self._bots:
            return MatchState.BOT_TURN
        return MatchState.HUMAN_TURN

    @property
    def result(self) -> MatchResult | None:
        """
        Returns how the match finished, or None while it is going
        """
        return self._result

    #
    # METHODS
    #

    def play(self, pos: tuple[int, int] | None) -> None:
        """
        Makes a person's move.

        Args:
            pos: Position on the board, or None to pass

        Raises:
            ValueError: If it is not a person's turn, or the move is not
            legal. Nothing changes.
        """
        if self.state is not MatchState.HUMAN_TURN:
            raise ValueError("It is not a person's turn")
        self._act(pos)

    def step(self) -> tuple[int, int] | None:
        """
        Makes the move of the bot whose turn it is.

        Raises:
            ValueError: If it is not a bot's turn. Nothing changes.

        Returns: The position the bot played, or None if it passed
        """
        if self.state is not MatchState.BOT_TURN:
            raise ValueError("It is not a bot's turn")
        pos = self._bots[self._game.turn].move(self._game)
        self._act(pos)
        return pos

    def hint(self) -> tuple[int, int] | None:
        """
        Suggests a move for the person whose turn it is.

        Raises:
            ValueError: If it is not a person's turn.

        Returns: The position the smart bot would play, or None to pass
        """
        if self.state is not MatchState.HUMAN_TURN:
            raise ValueError("It is not a person's turn")
        return Smart().move(self._game)

    def abort(self) -> None:
        """
        Ends the match with no winners. A finished match keeps its result.
        """
        if self._result is None:
            self._finish(EndReason.ABORTED)

    def _act(self, pos: tuple[int, int] | None) -> None:
        """
        Applies a move or a pass, then ends the match if it is over.

        Args:
            pos: Position on the board, or None to pass
        """
        if pos is None:
            self._game.pass_turn()
        else:
            self._game.apply_move(pos)
        self._moves += 1

        if self._game.done:
            self._finish(EndReason.PASSES)
        elif self._moves >= self.move_limit:
            self._finish(EndReason.MOVE_LIMIT)

    def _finish(self, reason: EndReason) -> None:
        """
        Records how the match ended.

        Args:
            reason: Why it ended
        """
        scores = self._game.scores()
        winners: tuple[int, ...] = ()
        if reason is not EndReason.ABORTED:
            best = max(scores.values())
            winners = tuple(player for player, score in scores.items()
                            if score == best)
        self._result = MatchResult(reason, winners, scores)

#
# Bot series
#

@dataclass(frozen=True)
class SeriesResult:
    """
    The totals of a series of bot-only matches. Wins map each player number,
    from 1, to the matches that player won alone; the rest are ties.
    """
    games: int
    wins: dict[int, int]
    ties: int
    moves: int

def run_series(config: GameConfig, games: int) -> SeriesResult:
    """
    Plays bot-only matches back to back, with no display.

    Args:
        config: The settings of every match. Every seat must be a bot.
        games: Number of matches to play

    Raises:
        ValueError: If a seat is human, or games is less than one.

    Returns: The wins of each player, the ties and the total moves
    """
    if "human" in config.seats:
        raise ValueError("Every seat in a series must be a bot")
    if games < 1:
        raise ValueError("A series needs at least one game")

    wins = {player: 0 for player in range(1, len(config.seats) + 1)}
    ties = 0
    moves = 0
    for _ in range(games):
        match = Match(config)
        while match.state is MatchState.BOT_TURN:
            match.step()
        result = match.result
        assert result is not None
        if len(result.winners) == 1:
            wins[result.winners[0]] += 1
        else:
            ties += 1
        moves += match.moves
    return SeriesResult(games, wins, ties, moves)
