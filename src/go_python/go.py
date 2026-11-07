"""
Go class
"""
from collections.abc import Sequence
from copy import copy
from typing import cast

from go_python.board import (Board, BoardGridType, FrozenBoardGridType,
                              ListMovesType)

class Go:
    """
    A class-based implementation of Go.
    """
    _side: int
    _players: int
    _superko: bool
    _grid: Board
    _turn: int
    _prior_boards: frozenset[FrozenBoardGridType]
    _passes: int
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

        Raises:
            ValueError: If side or players is not a whole number of at
            least one.
        """
        if type(side) is not int or type(players) is not int or \
           side < 1 or players < 1:
            raise ValueError("A game needs a board and a player")

        self._side = side
        self._players = players
        self._superko = superko
        self._grid = Board(side, side)
        self._turn = 1
        self._prior_boards = frozenset()
        self._passes = 0
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
        return self._grid.copy().grid

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

        If the game is over, the list is empty.
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

        scores = self.scores()
        winning_score = max(scores.values())
        return [player for player, score in scores.items()
                if score == winning_score]

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

    def _is_player(self, value: object) -> bool:
        """
        Checks that a value is the number of a player in this game. Equal
        values of other types do not count, so 1.0 and True are refused.

        Args:
            value: The value to check.

        Returns: True if the value is a player number.
        """
        return type(value) is int and 1 <= value <= self._players

    def _valid_neighbors(self, r: int, c: int) \
    -> list[tuple[int, int]]:
        """
        Finds the valid neighbors to any valid position on the board.

        Args:
            r: The row number of the position to be assessed.
            c: The column number of the position to be assessed.

        Returns: a list of the positions of the valid neighbors.
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
            src_c: The column coordinate of the source piece.

        Returns: a set containing the positions of the group of same-value
        contiguous pieces and a set of all piece values along the edges.
        """
        src_value = self._grid.get(src_r, src_c)
        halt_flag = src_value is not None

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
        Performs the necessary capture checks for a placed piece in the
        necessary order, first checking the surrounding pieces of a different
        player and then checking if there was a self capture.

        Args:
            pos: the position of the piece that was just placed.
        """
        src_r, src_c = pos
        captured: set[tuple[int, int]] = set()

        # Found first, then removed, so one capture cannot save another group
        for neigh_r, neigh_c in self._valid_neighbors(src_r, src_c):
            neigh_value = self._grid.get(neigh_r, neigh_c)
            if neigh_value not in (None, self._turn):
                grouping, _ = self._find_contiguous(neigh_r, neigh_c)
                captured |= grouping

        for r, c in captured:
            self._grid.set(r, c, None)

        grouping, _ = self._find_contiguous(src_r, src_c)
        for r, c in grouping:
            self._grid.set(r, c, None)

    def _place_stone(self, pos: tuple[int, int]) -> None:
        """
        Puts a stone of the current player on the board and resolves captures.

        Args:
            pos: the position of the new stone.
        """
        r, c = pos
        self._grid.set(r, c, self._turn)
        self._capture_pieces(pos)

    def _copy(self) -> Go:
        """
        Returns an independent copy of the game. The copy shares _prior_boards,
        which is safe because that set is immutable.
        """
        new_go = copy(self)
        new_go._grid = self._grid.copy()
        return new_go

    def piece_at(self, pos: tuple[int, int]) -> int | None:
        """
        Returns the piece at a given location

        Args:
            pos: Position on the board

        Raises:
            ValueError: If pos is not a position, or is outside
            the bounds of the board.

        Returns: If there is a piece at the specified location,
        return the number of the player (players are numbered
        from 1). Otherwise, return None.
        """
        if not isinstance(pos, tuple):
            raise ValueError(f"{pos} is not a position")

        r, c = pos
        return self._grid.get(r, c)

    def legal_move(self, pos: tuple[int, int]) -> bool:
        """
        Checks if a move is legal.

        Args:
            pos: Position on the board

        Raises:
            ValueError: If pos is not a position, or is outside
            the bounds of the board.

        Returns: If the current player (as returned by the turn
        method) could place a piece in the specified position,
        return True. Otherwise, return False. Once the game is
        over, no move is legal.
        """

        space = self.piece_at(pos)

        # Valid square check
        if self._done or space is not None:
            return False

        trial = self._copy()
        trial._place_stone(pos)

        # Suicide check: a capture of your own group takes the new stone too
        if trial.piece_at(pos) is None:
            return False

        # Ko rule check
        return trial.frozengrid not in self._prior_boards

    def apply_move(self, pos: tuple[int, int]) -> None:
        """
        Place a piece of the current player (as returned
        by the turn method) on the board.

        After applying the move, the turn is updated to the
        next player.

        Args:
            pos: Position on the board

        Raises:
            ValueError: If pos is not a position, is outside
            the bounds of the board, or is not a legal move.
            Once the game is over, no move is legal.

        Returns: None
        """
        if not self.legal_move(pos):
            raise ValueError(f"{pos} is not a legal move")

        prior_board = self.frozengrid

        # Reset passes
        self._passes = 0

        self._place_stone(pos)

        # Remember the board this move replaced, since ko forbids returning to it
        if self._superko:
            self._prior_boards = self._prior_boards | {prior_board}
        else:
            self._prior_boards = frozenset({prior_board})

        # Update Turn
        self._increment_turn()

    def pass_turn(self) -> None:
        """
        Causes the current player to pass their turn.

        If all players pass consecutively (with no
        moves between the passes), the game will be
        over.

        Raises:
            ValueError: If the game is already over.

        Returns: Nothing
        """
        if self._done:
            raise ValueError("The game is over")

        self._passes += 1

        # Checks if all players have passed
        if self._passes == self._players:
            self._done = True

        self._increment_turn()

    def scores(self) -> dict[int, int]:
        """
        Computes the current score for each player
        (the number of intersections in their area)

        Returns: Dictionary mapping player numbers to scores
        """

        scores = {i: 0 for i in range(1, self._players + 1)}
        visited_empty: set[tuple[int, int]] = set()

        for r in range(self._side):
            for c in range(self._side):
                value = self._grid.get(r, c)
                if value is None and (r, c) not in visited_empty:
                    empty_group, border_values = self._find_contiguous(r, c)
                    visited_empty |= empty_group
                    if len(border_values) == 1:
                        scores[cast(int, border_values.pop())] += len(empty_group)
                elif value is not None:
                    scores[value] += 1

        return scores

    def load_game(self, turn: int,
                  grid: Sequence[Sequence[int | None]]) -> None:
        """
        Loads a new board into the game.

        Note: This will wipe the history of prior board states,
              so violations of the ko rule may not be detected
              after loading a game. A finished game becomes a
              game in progress. A group with no liberties is not
              an error: it stays on the board and scores as alive.

        Args:
            turn: The player number of the player that
            would make the next move ("whose turn is it?")
            Players are numbered from 1.
            grid: The state of the board as a sequence of rows
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
        if not (self._is_player(turn) and isinstance(grid, Sequence) and
                len(grid) == self._side and
                all(isinstance(row, Sequence) and len(row) == self._side
                    for row in grid) and
                all(piece is None or self._is_player(piece)
                    for row in grid for piece in row)):

            raise ValueError("The turn or the grid does not fit this game")

        self._turn = turn
        self._grid.set_grid(grid)
        self._prior_boards = frozenset()
        self._passes = 0
        self._done = False

    def simulate_move(self, pos: tuple[int, int] | None) -> Go:
        """
        Simulates the effect of making a move,
        **without** altering the state of the game (instead,
        returns a new object with the result of applying
        the provided move).

        Args:
            pos: Position on the board, or None for a pass

        Raises:
            ValueError: If pos is not a position, is outside
            the bounds of the board or is not a legal move,
            or if the game is already over.

        Returns: An object of the same type as the object
        the method was called on, reflecting the state
        of the game after applying the provided move.
        """
        new_go = self._copy()
        if pos is not None:
            new_go.apply_move(pos)
        else:
            new_go.pass_turn()
        return new_go
