"""
A class for representing a game board.
"""
from itertools import chain

# Type for representing the state of the game board (the "grid")
# as a list of lists. Each entry will either be an integer (meaning
# there is a piece at that location for that player) or None,
# meaning there is no piece in that location. Players are
# numbered from 1.
BoardGridType = list[list[int | None]]

# Type for representing lists of moves on the board.
ListMovesType = list[tuple[int, int]]

class Board:
    """
    A class for representing a game board for an arbitrary game played on a
    rectangular board.

    Each piece on the board is represented as either an integer i (meaning a
    piece of type i is in that space) or by None (meaning that space is empty).
    """

    _rows: int
    _cols: int
    _grid: BoardGridType

    def __init__(self, rows: int, cols: int):
        self._rows = rows
        self._cols = cols
        self._grid = []
        for _ in range(rows):
            self._grid.append([None]*cols)

    def _check_bounds(self, row: int, col: int) -> None:
        """
        Checks that a position is on the board.

        Raises:
            ValueError: If the position is outside the bounds of the board.
        """
        if not (0 <= row < self._rows and 0 <= col < self._cols):
            raise ValueError(f"({row}, {col}) is off the board")

    def set(self, row: int, col: int, piece: int|None) -> None:
        """
        Sets the value of the piece in a position on the board.
        """
        self._check_bounds(row, col)
        self._grid[row][col] = piece

    def get(self, row: int, col: int) -> int|None:
        """
        Obtains the value of the piece at a given position on the board.
        """
        self._check_bounds(row, col)
        return self._grid[row][col]

    def copy(self) -> Board:
        """
        Returns an independent copy of the board.
        """
        board = Board(self._rows, self._cols)
        board.set_grid(self._grid)
        return board

    def freeze(self) -> tuple[int, int, tuple[int|None, ...]]:
        """
        Returns a "frozen" (immutable) copy of the gameboard that can hashed
        by Python.

        The frozen copy is a tuple containing the number of rows, then the
        number of columns, and then an inner tuple that is a flattened
        representation of the game board. The number of rows and columns can
        be used to reverse the flattening of the game board.
        """
        return (self._rows, self._cols, tuple(chain.from_iterable(self._grid)))

    @property
    def grid(self) -> BoardGridType:
        """
        Returns the internal representation of the board state.
        """
        return self._grid

    def set_grid(self, grid: BoardGridType) -> None:
        """
        Sets the internal representation of the board state to a copy of grid.
        """
        self._grid = [list(row) for row in grid]
