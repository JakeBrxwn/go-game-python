"""
A stub implementation of a GoStub GUI.
"""

import os
import sys
import pygame
import pygame.gfxdraw
import click

from go_python.go import Go

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"


def is_within_radius(test_pos: tuple[float|int, float|int],
                     center_pos: tuple[float|int, float|int],
                     radius: float|int) -> bool:
    """
    Calculates the euclidian distance between two points and finds whether it
    the position being tested is within some radius of the
    """
    x_1, y_1 = test_pos
    x_2, y_2 = center_pos
    return (x_1 - x_2) ** 2 + (y_1 - y_2) ** 2 <= radius ** 2


FONT_SIZE = 36
# Colors for player pieces, going in the following order: black, white, red,
# green, blue, yellow, pink, cyan.
COLORS = {1: (0, 0, 0),
          2: (255, 255, 255),
          3: (255, 0, 0),
          4: (0, 255, 0),
          5: (0, 0, 255),
          6: (255, 255, 0),
          7: (255, 0, 255),
          8: (0, 255, 255)}

class GoGUI:
    """
    A class for the fake graphical user interface implementation for a game of
    Go.
    """
    ### Pygame attributes
    width: int
    height: int
    border: int
    surface: pygame.surface.Surface
    clock: pygame.time.Clock
    font: pygame.font.Font

    ### Ongoing rendering attributes
    _piece_rad: float
    _button_rad: float

    ### Precalculated rending positions
    # Go board positions
    _grid_dims: tuple[float, float, float, float]
    _line_positions: tuple[tuple[tuple[float, float], tuple[float, float]], ...]
    _intersections: tuple[tuple[tuple[float, float], ...], ...]
    # UI positions
    _score_board: dict[int, tuple[float, float]]
    _pass_position: tuple[float, float]
    _turn_position: tuple[float, float]

    ### Go attributes
    size: int
    players: int
    board: Go
    _current_tile: tuple[int, int]|None
    _scores: dict[int, int]

    def __init__(self, players: int, size: int, super_ko: bool,
                 width: int = 1200, height: int = 675, border: int = 32) -> None:
        if size <= 0:
            raise ValueError("Invalid board size")

        self.width = width
        self.height = height
        self.border = border
        self.size = size
        self.players = players
        self.board = Go(size, self.players, super_ko)
        self._scores = self.board.scores()

        self._precal_gui()

        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption("Go Python")
        self.font = pygame.font.Font(None, size=FONT_SIZE)
        self.surface = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()

        self.event_loop()

    def _precal_gui(self) -> None:
        """
        Calculate the positions and dimensions of all of the GUI elements
        dynamically from the height and width.
        """
        spacing = self.height / self.size
        board_size = self.height

        # Rendering attributes
        self._piece_rad = spacing / 2
        self._button_rad = self.height / 8

        # General grid attributes
        self._grid_dims = ((self.width - board_size) / 2,
                            0,
                            board_size,
                            board_size)

        # Tile positions
        start_x = (self.width - self.height + 2 * self._piece_rad) / 2
        start_y = spacing / 2
        x_positions = [c * spacing + start_x for c in range(self.size)]
        y_positions = [r * spacing + start_y for r in range(self.size)]
        self._line_positions = tuple([((start_x, y), (x_positions[-1], y))
                                      for y in y_positions]
                                     +
                                     [((x, start_y), (x, y_positions[-1]))
                                      for x in x_positions])
        self._intersections = tuple(tuple((x, y) for x in x_positions)
                                    for y in y_positions)

        # Button attributes
        self._pass_position = (self._grid_dims[0] / 2, self.height / 4)
        self._turn_position = (self._grid_dims[0] / 2, 3 * self.height / 4)

        # Scoreboard attributes
        right_center = 3 * self._grid_dims[0] / 2 + self._grid_dims[2]
        text_spacing = self.height / 16
        self._score_board = {}
        for i in range(-1, self.players + 1):
            self._score_board[i] = (right_center, (i + 2) * text_spacing)

    def _draw_labelled_circ(self, radius: float, center: tuple[float, float],
                     label: str|None, label_color: tuple[int, int, int],
                     rim_color: tuple[int, int, int],
                     fill_color: tuple[int, int, int], thickness: int) -> None:
        """
        Draws a button with a specified rim color, fill color, thickness, and
        label.

        Parameters:
            radius : int : radius of circle representing button or node
            center : Tuple[int, int] : center coordinates of circle
            label : str : textual label for button or node
            rim_color: the color of the rim of the button
            fill_color: the color of the inside of the button
            thickness: the thickness of the rim of the button

        Returns: nothing
        """
        pygame.draw.circle(self.surface, fill_color, center, radius)
        pygame.draw.circle(self.surface, rim_color, center, radius, thickness)

        if label is not None:
            label_img = self.font.render(label, True, label_color)
            text_topleft = (center[0] - label_img.get_width() // 2,
                            center[1] - label_img.get_height() // 2)
            self.surface.blit(label_img, text_topleft)

    def _draw_text(self, text: str, center: tuple[float|int, float|int],
                   color: tuple[int, int, int]) -> None:
        """
        Draws text to the window.

        Parameters:
            text: The string to draw on the window
            center: The coordinates of the center of the text
            color: The color of the text
        """
        label_img = self.font.render(text, True, color)
        text_topleft = (center[0] - label_img.get_width() // 2,
                        center[1] - label_img.get_height() // 2)
        self.surface.blit(label_img, text_topleft)

    def _draw_board(self, line_thickness: int) -> None:
        """
        Draws a Go board in the center of the window.

        Parameter:
            line_thickness: The thickness of lines of the Go board
        """
        # Draws an off-white backdrop (regular white is too harsh)
        self.surface.fill((249, 241, 241))

        # Draws the outline of the wooden board with rounded edges.
        pygame.draw.rect(self.surface,
                         (207, 185, 151),
                         self._grid_dims,
                         0,
                         int(self._piece_rad))

        # Draws the black dividing lines of the tiles
        for pos_1, pos_2 in self._line_positions:
            pygame.draw.line(self.surface,
                             (0, 0, 0),
                             pos_1,
                             pos_2,
                             line_thickness)

    def _draw_pieces(self, line_thickness: int) -> None:
        """
        Draws the pieces of the Go board on the window in the correct location.
        It also checks if the mouse is hovering over an intersection that
        where a valid move can be applied. If it is, an indicator is put in that
        intersection.

        Parameters:
            line_thickness: The thickness of the rim of the valid move indicator
        """
        self._current_tile = None
        mouse_pos = pygame.mouse.get_pos()
        for r, row in enumerate(self._intersections):
            for c, tile_pos in enumerate(row):
                space = self.board.piece_at((r, c))
                if space is not None:
                    pygame.draw.circle(self.surface,
                                       COLORS[space],
                                       tile_pos,
                                       self._piece_rad)
                elif is_within_radius(mouse_pos, tile_pos, self._piece_rad) \
                and self.board.legal_move((r, c)):
                    self._current_tile = (r, c)
                    self._draw_labelled_circ(self._piece_rad, tile_pos, "?",
                                             (0, 0, 0), (255, 255, 191),
                                             (255, 255, 191), line_thickness)

    def _draw_ui(self, line_thickness: int) -> None:
        """
        Draws the rest of the UI (that is, the pass button, the turn indicator,
        and the scorebaord) to the sides of the Go board.

        Parameters:
            line_thickness: The thickness of the rim of the pass button and
                turn indicator
        """
        # Draws the pass button
        self._draw_labelled_circ(self._button_rad,
                                 self._pass_position,
                                 "Pass",
                                 (0, 0, 0),
                                 (0, 0, 0),
                                 (196, 2, 52),
                                 line_thickness)

        # Draws turn display
        self._draw_labelled_circ(self._button_rad,
                                 self._turn_position,
                                 "Turn",
                                 (207, 185, 151),
                                 (207, 185, 151),
                                 COLORS[self.board.turn],
                                 line_thickness)

        # Draw scoreboard
        if self.board.done:
            self._draw_text("Game Over!", self._score_board[-1], (0, 0, 0))
        self._draw_text("Scores:", self._score_board[0], (0, 0, 0))
        outcomes = self.board.outcome
        for i in range(1, self.players + 1):
            if i in outcomes:
                score_text = f"Winner! Player {i}: {self._scores[i]}"
            else:
                score_text = f"Player {i}: {self._scores[i]}"
            self._draw_text(score_text, self._score_board[i], (0, 0, 0))

    def _draw_window(self) -> None:
        """Redraws the window."""
        line_thickness = 5

        self._draw_board(line_thickness)

        self._draw_pieces(line_thickness)

        self._draw_ui(line_thickness)

    def event_loop(self) -> None:
        """Handles user interactions and refresh rate."""
        while True:
            self._draw_window()
            pygame.display.update()

            events = pygame.event.get()
            for event in events:

                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONUP and not self.board.done:

                    if self._current_tile is not None:
                        self.board.apply_move(self._current_tile)
                        self._current_tile = None
                        self._scores = self.board.scores()

                    elif is_within_radius(pygame.mouse.get_pos(),
                                          self._pass_position,
                                          self._button_rad):
                        self.board.pass_turn()

            self.clock.tick(24)

@click.command()
@click.option('-n', '--num-players', type = click.INT, default=2,
              help = "The number of players.")
@click.option('-s', '--size', type = click.INT, default=19,
              help = "The size of the board.")
@click.option('--simple-ko', is_flag = True, show_default = True,
              default = True, help = "Starts a simple ko game.")
@click.option('--super-ko', is_flag = True, show_default = True,
              default = False, help = "Starts a super ko game.")
def startGUI(num_players: int, size: int, simple_ko: bool,
             super_ko: bool) -> None:
    if simple_ko and not super_ko:
        GoGUI(num_players, size, False)
    elif not simple_ko and super_ko:
        GoGUI(num_players, size, True)
    else:
        raise ValueError("A game of Go cannot be both simple ko and super ko.")

if __name__ == "__main__":
    startGUI()
