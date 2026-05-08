"""
Fake implementations of GoBase.

We provide a GoStub implementation, and you must
implement a GoFake implementation.
"""
from copy import deepcopy
from base import GoBase, BoardGridType, ListMovesType

class GoStub(GoBase):
    """
    Stub implementation of GoBase.

    This stub implementation behaves according to the following rules:

    - It only supports two players and boards of size 2x2 and above.

    - The board is always initialized with four pieces in the four
      corners of the board. Player 1 has pieces in the northeast and
      southwest corners of the board, and Player 2 has pieces in the
      southeast and northwest corners of the board.
    - Players are allowed to place pieces in any position of the board
      they want, even if there is already a piece in that position
      (placing a piece in such a position replaces the previous piece
      with the new one). The ko and superko rule do not apply.
    - The game ends after four moves. Whatever player has a piece in
      position (0,1) wins. If there is no piece in that position,
      the game ends in a tie.
    - The scores are always reported as 100 for Player 1 and 200 for
      Player 2. Note how the scores do not play a role in determining
      the outcome of the game.
    - It does not validate board positions. If a method is called with
      a position outside the board, the method will likely cause an exception.
    - It does not implement the load_game or simulate_moves method.
    """

    _grid: BoardGridType
    _turn: int
    _num_moves: int

    def __init__(self, side: int, players: int, superko: bool = False):
        """
        See GoBase.__init__
        """
        if players != 2:
            raise ValueError(
                "The stub implementation " "only supports two players"
            )

        super().__init__(side, players, superko)

        self._grid = [[None] * side for _ in range(side)]
        self._grid[0][-1] = 1
        self._grid[-1][0] = 1
        self._grid[0][0] = 2
        self._grid[-1][-1] = 2

        self._turn = 1
        self._num_moves = 0

    @property
    def grid(self) -> BoardGridType:
        """
        See GoBase.grid
        """
        return deepcopy(self._grid)

    @property
    def turn(self) -> int:
        """
        See GoBase.turn
        """
        return self._turn

    @property
    def available_moves(self) -> ListMovesType:
        """
        See GoBase.available_moves
        """
        moves = []
        for r in range(self._side):
            for c in range(self._side):
                moves.append((r, c))

        return moves

    @property
    def done(self) -> bool:
        """
        See GoBase.done
        """
        return self._num_moves == 4

    @property
    def outcome(self) -> list[int]:
        """
        See GoBase.outcome
        """
        if not self.done:
            return []

        if self._grid[0][1] is None:
            return [1, 2]
        else:
            return [self._grid[0][1]]

    def piece_at(self, pos: tuple[int, int]) -> int | None:
        """
        See GoBase.piece_at
        """
        r, c = pos
        return self._grid[r][c]

    def legal_move(self, pos: tuple[int, int]) -> bool:
        """
        See GoBase.legal_move
        """
        return True

    def apply_move(self, pos: tuple[int, int]) -> None:
        """
        See GoBase.apply_move
        """
        r, c = pos
        self._grid[r][c] = self._turn
        self.pass_turn()

    def pass_turn(self) -> None:
        """
        See GoBase.pass_turn
        """
        self._turn = 2 if self._turn == 1 else 1
        self._num_moves += 1

    def scores(self) -> dict[int, int]:
        """
        See GoBase.scores
        """
        return {1: 100, 2: 200}

    def load_game(self, turn: int, grid: BoardGridType) -> None:
        """
        See GoBase.load_game
        """
        raise NotImplementedError

    def simulate_move(self, pos: tuple[int, int] | None) -> "GoBase":
        """
        See GoBase.simulate_move
        """
        raise NotImplementedError


#
# Your GoFake implementation goes here
#


class GoFake(GoBase):
    """
    Fake implementation of GoBase.

    This fake implentation behaves according to the following rules:

    - It only supports two players and boards of size 4x4 and above.
    - It supports the Ko and Superko rules.
    - Must raise ValueError exceptions as specified in the GoBase docstrings.
    - A move is legal if the position in the board is empty, and it does not
      violate the ko/superko rule (depending on whether superko was set to False
      or True in the constructor).
    - After placing a piece, if there are any pieces belonging to the other
      player in the positions adjacent (up, down, left, and right) to the piece
      we just placed, those pieces are captured.
    - If a player places a piece in position (0,0), the game ends immediately
      (without capturing any adjacent pieces), and all empty positions in the
      board are updated to contain a piece for that player.
    - Passing turns is supported and, like Go, if all players pass, the game
      will end.
    - The score for each player is equal to the number of pieces that the player
      has on the board. The winner of the game is whoever has the most pieces on
      the board when the game ends.
    - It does not implement the load_game method, but it must implement
      simulate_move. Note that you must still provide a load_game method, (since
      it is an abstract method that needs to be implemented in the child class).
      We suggest that you just have the method include a single raise
      NotImplementedError statement, as in the stub implementation.
    """

    _grid: BoardGridType
    _turn: int
    _prior_boards: list[BoardGridType]
    _passes: list[bool]
    _done: bool

    def __init__(
        self,
        side: int,
        players: int,
        superko: bool = False,
    ):
        if players != 2:
            raise ValueError(
                "The fake implementaion only supports two players"
            )
        if side < 4:
            raise ValueError(
                "The fake implementation requires a board size of at least 4x4"
            )

        super().__init__(side, players, superko)

        self._grid = [[None for _ in range(side)] for _ in range(side)]
        self._turn = 1
        self._prior_boards = []
        self._passes = [False for _ in range(players)]
        self._done = False

    #
    # Properties
    #

    @property
    def grid(self) -> BoardGridType:
        """
        Returns the state of the game board as a list of lists.
        Each entry can either be an integer (meaning there is a
        piece at that location for that player) or None,
        meaning there is no piece in that location. Players are
        numbered from 1.
        """
        return deepcopy(self._grid)

    @property
    def turn(self) -> int:
        """
        Returns the player number for the player who must make
        the next move (i.e., "whose turn is it?"). Players are
        numbered from 1.

        If the game is over, this property will not return
        any meaningful value.
        """
        return self._turn

    @property
    def available_moves(self) -> ListMovesType:
        """
        Returns the list of positions where the current player
        (as returned by the turn method) could place a piece.

        If the game is over, this property will not return
        any meaningful value.
        """
        legal_moves: ListMovesType = [(r, c) for r in range(self._side)
                                      for c in range(self._side)
                                      if self.legal_move((r, c))]
        return legal_moves

    @property
    def done(self) -> bool:
        """
        Returns True if the game is over, False otherwise.
        """
        return self._done

    @property
    def outcome(self) -> list[int]:
        """
        Returns the list of winners for the game. If the game
        is not yet done, will return an empty list.
        If the game is done, will return a list of player numbers
        (players are numbered from 1). If there is a single winner,
        the list will contain a single integer. If there is a tie,
        the list will contain more than one integer (representing
        the players who tied)
        """
        # Not done case
        if not self._done:
            return []

        winner = []
        winning_score = 0
        for player, player_score in self.scores().items():
            if player_score > winning_score:
                winning_score = player_score
                winner = [player]
            elif player_score == winning_score:
                winner.append(player)

        return winner

    #
    # METHODS
    #

    def _finish_game(self) -> None:
        """
        Prematurely ends a game according to the fake implementation rules.
        """
        self._done = True
        for r, row in enumerate(self._grid):
            for c, space in enumerate(row):
                if space is None:
                    self._grid[r][c] = self._turn

    def piece_at(self, pos: tuple[int, int]) -> int | None:
        """
        Returns the piece at a given location

        Args:
            pos: Position on the board

        Raises:
            ValueError: If the specified position is outside
            the bounds of the board.

        Returns: If there is a piece at the specified location,
        return the number of the player (players are numbered
        from 1). Otherwise, return None.
        """
        r, c = pos
        if 0 <= r < self._side and 0 <= c < self._side:
            return self._grid[r][c]
        raise ValueError

    def legal_move(self, pos: tuple[int, int]) -> bool:
        """
        Checks if a move is legal.

        Args:
            pos: Position on the board

        Raises:
            ValueError: If the specified position is outside
            the bounds of the board.

        Returns: If the current player (as returned by the turn
        method) could place a piece in the specified position,
        return True. Otherwise, return False.
        """

        r, c = pos

        # In bounds check
        if 0 > r or r >= self._side or 0 > c or c >= self._side:
            raise ValueError

        # Valid square check
        if self._grid[r][c] is not None:
            return False

        # Ko rule check
        new_game_state = self.simulate_move(pos)
        if new_game_state.grid in self._prior_boards:
            return False
        return True

    def apply_move(self, pos: tuple[int, int]) -> None:
        """
        Place a piece of the current player (as returned
        by the turn method) on the board.

        The provided position is assumed to be a legal
        move (as returned by available_moves, or checked
        by legal_move). The behaviour of this method
        when the position is on the board, but is not
        a legal move, is undefined.

        After applying the move, the turn is updated to the
        next player.

        Args:
            pos: Position on the board

        Raises:
            ValueError: If the specified position is outside
            the bounds of the board.

        Returns: None
        """

        r, c = pos

        # End game check
        if r == 0 and c == 0:
            self._finish_game()
            return

        # Value error check
        if 0 > r or r >= self._side or 0 > c or c >= self._side:
            raise ValueError

        # Remember board state (according to either ko or superko)
        if self._superko:
            self._prior_boards.append(deepcopy(self._grid))
        else:
            self._prior_boards = [deepcopy(self._grid)]

        # Reset passes
        self._passes = [False for _ in range(self._players)]

        # Place token and capture pieces
        self._grid[r][c] = self._turn
        neighbors = ((r + h, c + w)
                     for h, w in ((1, 0), (-1, 0), (0, 1), (0, -1))
                     if 0 <= r + h < self._side and 0 <= c + w < self._side)
        for r_2, c_2 in neighbors:
            if self._grid[r_2][c_2] != self._turn:
                self._grid[r_2][c_2] = None

        # Update Turn
        self._turn += 1
        if self._turn > self._players:
            self._turn = 1


    def pass_turn(self) -> None:
        """
        Causes the current player to pass their turn.

        If all players pass consecutively (with no
        moves between the passes), the game will be
        over.

        Returns: Nothing
        """

        self._passes[self._turn - 1] = True

        # Checks if all players have passed
        if False not in self._passes:
            self._done = True

        self._turn += 1
        if self._turn > self._players:
            self._turn = 1

    def scores(self) -> dict[int, int]:
        """
        Computes the current score for each player
        (the number of intersections in their area)

        Returns: Dictionary mapping player numbers to scores
        """
        scores = {player + 1: 0 for player in range(self._players)}

        for row in self._grid:
            for space in row:
                if space is not None:
                    scores[space] += 1

        return scores

    def load_game(self, turn: int, grid: BoardGridType) -> None:
        """
        Loads a new board into the game.

        Note: This will wipe the history of prior board states,
              so violations of the ko rule may not be detected
              after loading a game.

        Args:
            turn: The player number of the player that
            would make the next move ("whose turn is it?")
            Players are numbered from 1.
            grid: The state of the board as a list of lists
            (same as returned by the grid property)

        Raises:
             ValueError:
             - If the value of turn is inconsistent
               with the _players attribute.
             - If the size of the grid is inconsistent
               with the _side attribute.
             - If any value in the grid is inconsistent
               with the _players attribute.

        Returns: None
        """
        raise NotImplementedError

    def simulate_move(self, pos: tuple[int, int] | None) -> "GoBase":
        """
        Simulates the effect of making a move,
        **without** altering the state of the game (instead,
        returns a new object with the result of applying
        the provided move).

        The provided position is not required to be a legal
        move, as this method could be used to check whether
        making a move results in a board that violates the
        ko rule.

        Args:
            pos: Position on the board, or None for a pass

        Raises:
            ValueError: If any of the specified position
            is outside the bounds of the board.

        Returns: An object of the same type as the object
        the method was called on, reflecting the state
        of the game after applying the provided move.
        """
        new_go = deepcopy(self)
        if pos is not None:
            try:
                new_go.apply_move(pos)
            except ValueError as e:
                raise ValueError from e
        else:
            new_go.pass_turn()
        return new_go
