"""
A class for representing a game board.
"""
from base import BoardGridType

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

    def __init__(self, rows: int, cols: int, players: int = 2):
        self._rows = rows
        self._cols = cols
        self._grid = []
        self.points = {i: 0 for i in range(1, players + 1)}
        for _ in range(rows):
            self._grid.append([None]*cols)

    def set(self, row: int, col: int, piece: int|None) -> None:
        """
        Sets the value of the piece in a position on the board.
        """
        assert 0 <= row <= self._rows and 0 <= col <= self._cols
        self._grid[row][col] = piece

    def get(self, row: int, col: int) -> int|None:
        """
        Obtains the value of the piece at a given position on the board.
        """
        assert 0 <= row <= self._rows and 0 <= col <= self._cols
        return self._grid[row][col]

    def freeze(self) -> tuple[int, int, tuple[int|None]]:
        """
        Returns a "frozen" (immutable) copy of the gameboard that can hashed
        by Python.

        The frozen copy is a tuple containing the number of rows, then the
        number of columns, and then an inner tuple that is a flattened
        representation of the game board. The number of rows and columns can
        be used to reverse the flattening of the game board.
        """
        return (self._rows, self._cols, tuple(piece for row in self._grid
                                              for piece in row))

    @property
    def grid(self) -> BoardGridType:
        """
        Returns the internal representation of the board state.
        """
        return self._grid

    def set_grid(self, grid: BoardGridType) -> None:
        """
        Sets the internal representation of the board state.
        """
        self._grid = grid
