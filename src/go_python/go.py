"""
Go class
"""
from copy import deepcopy
from go_python.board import Board, BoardGridType, ListMovesType

FrozenBoardGridType = tuple[int, int, tuple[int|None]]

class Go:
    """
    A class-based implementation of Go.
    """
    _side: int
    _players: int
    _superko: bool
    _grid: "Board"
    _turn: int
    _prior_boards: set[FrozenBoardGridType]
    _passes: list[bool]
    _done: bool

    def __init__(
        self,
        side: int,
        players: int,
        superko: bool = False,
    ):
        """
        Constructor

        Args:
            side: Number of squares on each side of the board
            players: Number of players
            superko: If True, the "super ko" rule is in effect:
            a move cannot result in any past state of the board.
            If False, the "simple ko" rule is in effect: a move
            cannot result in the immediately prior state of the
            board.
        """
        self._side = side
        self._players = players
        self._superko = superko
        self._grid = Board(side, side, players)
        self._turn = 1
        self._prior_boards = set()
        self._passes = [False for _ in range(players)]
        self._done = False

    #
    # Properties
    #

    @property
    def side(self) -> int:
        """
        Returns the size of the board (the number of squares per side)
        """
        return self._side

    @property
    def num_players(self) -> int:
        """
        Returns the number of players
        """
        return self._players

    @property
    def grid(self) -> BoardGridType:
        """
        Returns the state of the game board as a list of lists.
        Each entry can either be an integer (meaning there is a
        piece at that location for that player) or None,
        meaning there is no piece in that location. Players are
        numbered from 1.
        """
        return deepcopy(self._grid.grid)

    @property
    def frozengrid(self) -> FrozenBoardGridType:
        """
        Returns the frozen version of the current grid.
        """
        return self._grid.freeze()

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
    
    @property
    def number_pieces(self) -> dict[int, int]:
        """
        Returns the scores of each player by the amount of pieces on the board.
        """
        return self._grid.points

    #
    # METHODS
    #

    def _increment_turn(self) -> None:
        """
        Increments the turn counter, rolling over the first player once the last
        player has gone.
        """

        self._turn += 1
        if self._turn > self._players:
            self._turn = 1

    def _valid_neighbors(self, r: int, c: int) \
    -> list[tuple[int, int]]:
        """
        Finds the valid neighbors to any valid position on the board.

        Args:
            r: The row number of the position to be assessed.
            c: The column number of the position to be assessed.

        Returns: a list of tuples, with each tuple containing the position of
        a valid neighbor and the value of that neighbor.
        """
        cardinal_directions = ((0, 1), (1, 0), (0, -1) , (-1, 0))
        return [(r + dr, c + dc) for dr, dc in cardinal_directions
                if 0 <= r + dr < self._side and 0 <= c + dc < self._side]

    def _find_contiguous(self, src_r: int, src_c: int) \
    -> tuple[set[tuple[int, int]], set[int|None]]:
        """
        Takes in a source position and finds all connected pieces of the same
        value, also tracking the values of pieces that are adjacent to this
        group. If the value of the source is not None, then this process halts
        prematurely if an adjacent piece has value None and the function returns
        two empty sets.

        Args:
            src_r: The row coordinate of the source piece.
            src_c The column coordinate of the source piece.

        Returns a set of containing the positions of the group of same-value
        contingous pieces and a set of all piece values along the edges.
        """
        src_value = self._grid.get(src_r, src_c)
        if src_value is None:
            halt_flag = False
        else:
            halt_flag = True

        visited: set[tuple[int, int]] = {(src_r, src_c)}
        stack: list[tuple[int, int]] = [(src_r, src_c)]
        adj_values: set[int|None] = set()

        while stack:
            r, c = stack.pop()
            for neigh_r, neigh_c in self._valid_neighbors(r, c):
                if (neigh_r, neigh_c) in visited:
                    continue

                neigh_value = self._grid.get(neigh_r, neigh_c)

                if halt_flag and neigh_value is None:
                    return set(), set()

                if neigh_value == src_value:
                    stack.append((neigh_r, neigh_c))
                    visited.add((neigh_r, neigh_c))
                else:
                    adj_values.add(neigh_value)

        return visited, adj_values


    def _capture_pieces(self, pos: tuple[int, int]) -> None:
        """
        Performs the neccessary capture checks for a placed pieces in the
        necessary order, first checking the surrounding pieces of a different
        player and then checking if there was a self capture.

        Args:
            pos: the position of the piece that was just placed.
        """
        src_r, src_c = pos

        for neigh_r, neigh_c in self._valid_neighbors(src_r, src_c):
            neigh_value = self._grid.get(neigh_r, neigh_c)
            if neigh_value not in (None, self._turn):
                grouping, _ = self._find_contiguous(neigh_r, neigh_c)
                while grouping:
                    r, c = grouping.pop()
                    self._grid.set(r, c, None)
                    self._grid.points[neigh_value] -= 1

        grouping, _ = self._find_contiguous(src_r, src_c)
        while grouping:
            r, c = grouping.pop()
            self._grid.set(r, c, None)

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
        return self._grid.get(r, c)

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
        space = self._grid.get(r, c)

        # Valid square check
        if space is not None:
            return False

        # Ko rule check
        new_game_state = self.simulate_move(pos)
        if new_game_state.frozengrid in self._prior_boards:
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

        # Reset passes
        self._passes = [False for _ in range(self._players)]

        self._grid.set(r, c, self._turn)
        self._grid.points[self._turn] += 1

        self._capture_pieces(pos)

        # Remember board state (according to either ko or superko)
        if self._superko:
            self._prior_boards.add(self.frozengrid)
        else:
            self._prior_boards = {self.frozengrid}

        # Update Turn
        self._increment_turn()

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

        self._increment_turn()

    def scores(self) -> dict[int, int]:
        """
        Computes the current score for each player
        (the number of intersections in their area)

        Returns: Dictionary mapping player numbers to scores
        """

        scores = {i: 0 for i in range(1, self._players + 1)}
        visited_empty = set()

        for r in range(self._side):
            for c in range(self._side):
                value = self._grid.get(r, c)
                if value is None and (r, c) not in visited_empty:
                    empty_group, border_values = self._find_contiguous(r, c)
                    visited_empty = visited_empty.union(empty_group)
                    if len(border_values) == 1:
                        scores[border_values.pop()] += len(empty_group)
                elif value is not None:
                    scores[value] += 1

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
        if (turn > self._players or len(grid) != self._side or
            len(grid[0]) != self._side):

            raise ValueError

        self._turn = turn
        self._grid.set_grid(grid)
        self._prior_boards = set()

    def simulate_move(self, pos: tuple[int, int] | None) -> "Go":
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
