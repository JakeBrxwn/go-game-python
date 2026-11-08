"""
The Go Python window: a menu, a setup screen, the match and its result.
The window only reads the game; every move goes through a Match.
"""
import os
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import Enum, auto
from functools import partial
from typing import Any, NamedTuple

from go_python import __version__
from go_python.match import (PLAYER_NAMES, SEAT_KINDS, EndReason, GameConfig,
                             Match, MatchResult, MatchState)

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame  # noqa: E402
import pygame.freetype  # noqa: E402

#
# Layout, colours and timing
#

WIDTH, HEIGHT = 1200, 675
FPS = 30
# Pause before each bot move so a person can follow the game; tests set 0
BOT_DELAY_MS = 600
# A press this soon after the screen changed or a person moved is the
# second half of a double-click, so it is ignored; tests set 0
DOUBLE_CLICK_MS = 500

# The board keeps its original look: off-white backdrop, wood, black lines
BACKDROP = (249, 241, 241)
WOOD = (207, 185, 151)
GRID = (0, 0, 0)
SHADOW = (166, 144, 112)
# Stone colours in turn order, named by PLAYER_NAMES. Red and blue are
# softened from pure primaries and keep 3:1 against the wood and Black.
STONES = ((0, 0, 0), (255, 255, 255), (190, 35, 35), (40, 90, 200))

INK = (43, 36, 36)
MUTED = (118, 104, 104)
CARD = (255, 255, 255)
EDGE = (226, 212, 212)
# Button borders and the gold fill both keep 3:1 or more against white
LINE = (150, 136, 136)
GOLD = (150, 100, 20)
TINT = (255, 246, 228)
ERROR = (176, 28, 28)
# Fill, edge and label colour of each button style
STYLES = {"plain": (CARD, LINE, INK), "primary": (INK, INK, CARD),
          "chosen": (GOLD, GOLD, CARD), "off": (EDGE, EDGE, MUTED)}

# Where the grid goes; the wood reaches PAD further out on every side
BOARD = pygame.Rect(36, 36, 603, 603)
PREVIEW = pygame.Rect(72, 150, 312, 312)
HERO = pygame.Rect(108, 130, 416, 416)
PAD = 12
# The sidebar beside the board while a match is on
SIDE, SIDE_W = 680, 496
HERO_STONES = (((2, 2), 1), ((2, 6), 2), ((6, 2), 3), ((6, 6), 4),
               ((3, 2), 1), ((2, 3), 1), ((4, 4), 1), ((3, 6), 2),
               ((2, 5), 2), ((4, 5), 2), ((5, 2), 3), ((6, 3), 3),
               ((5, 6), 4), ((6, 5), 4), ((5, 4), 3))

SEAT_LABELS = {"human": "Human", "random": "Random bot",
               "smart": "Smart bot"}
WATCH = GameConfig(size=9, seats=("smart", "random"))
MENU_HINTS = ("Set up a game against people, bots or both.",
              "Pick some bots and watch them play each other.",
              "Close the window.")
HOW_TO_PLAY = ("Take turns placing a stone where two lines cross. Stones "
               "with no empty point next to them are captured. Your score "
               "is your area: your stones plus the empty points only you "
               "surround. When every player passes in a row, the most "
               "area wins.")
LEAVE_ASK = ("Press Esc or Leave match again to leave. Anything else "
             "keeps the match going.")
SEAT_HELP = ("Black moves first. Human: you click the board to play. "
             "Random bot: plays any legal move. Smart bot: looks for the "
             "move that gains most.")

class Screen(Enum):
    """
    What the window shows.
    """
    MENU = auto()
    SETUP = auto()
    PLAYING = auto()
    GAME_OVER = auto()

@dataclass(frozen=True)
class Button:
    """
    A box to click. Drawing and clicks read the same list of buttons.
    """
    rect: pygame.Rect
    label: str
    action: Callable[[], None] = field(compare=False)
    style: str = field(default="plain", compare=False)

class Drawn(NamedTuple):
    """
    One thing draw() put on the screen.
    """
    kind: str  # "text", "box" (a panel, button or board) or "stone"
    rect: pygame.Rect
    text: str = ""  # the words of a text, the player of a stone

#
# Pure helpers
#

def point_at(mouse: tuple[int, int], board: pygame.Rect,
             size: int) -> tuple[int, int] | None:
    """
    Finds the board point under the mouse.

    Args:
        mouse: Position of the mouse in the window
        board: Where the board is drawn
        size: Number of points on each side

    Returns: The (row, column) nearest the mouse, or None off the board
    """
    spacing = board.width / size
    row = int((mouse[1] - board.y) // spacing)
    col = int((mouse[0] - board.x) // spacing)
    return (row, col) if 0 <= row < size and 0 <= col < size else None

def center(board: pygame.Rect, size: int,
           point: tuple[int, int]) -> tuple[float, float]:
    """
    Finds where a board point is drawn.

    Args:
        board: Where the board is drawn
        size: Number of points on each side
        point: The (row, column) of the point

    Returns: The window position of the point
    """
    spacing = board.width / size
    return (board.x + (point[1] + 0.5) * spacing,
            board.y + (point[0] + 0.5) * spacing)

def star_points(size: int) -> list[tuple[int, int]]:
    """
    Finds the marked points of a board, as on a real Go board.

    Args:
        size: Number of points on each side

    Returns: The corner points, the centre of an odd board, and the side
    points from 15 x 15 up. Boards under 7 x 7 have none.
    """
    if size < 7:
        return []
    near, far = (2, size - 3) if size < 13 else (3, size - 4)
    points = [(r, c) for r in (near, far) for c in (near, far)]
    if size % 2:
        mid = size // 2
        points.append((mid, mid))
        if size >= 15:
            points += [(near, mid), (mid, near), (mid, far), (far, mid)]
    return points

def points(count: int) -> str:
    """
    Words for a number of points.

    Args:
        count: The number of points

    Returns: The number followed by point or points
    """
    return f"{count} point{'s' * (count != 1)}"

def summary(result: MatchResult, moves: int) -> tuple[str, str]:
    """
    Words for how a match ended.

    Args:
        result: How the match finished
        moves: Number of moves and passes made

    Returns: A short headline, and a line naming the winners and saying why
    the match ended
    """
    names = [PLAYER_NAMES[player - 1] for player in result.winners]
    why = f"{result.reason.value.capitalize()} after {moves} moves."
    if result.reason is EndReason.ABORTED:
        return "You left the match", why + " No winner."
    if len(names) > 1:
        tied = ", ".join(names[:-1]) + f" and {names[-1]}"
        return "It's a tie", f"{tied} share the top score. {why}"
    best, second = sorted(result.scores.values(), reverse=True)[:2]
    margin = best - second
    return f"{names[0]} wins", f"By {points(margin)}. {why}"

#
# The window
#

class GoGUI:
    """
    The window. The constructor only sets it up; loop() runs it, and tests
    can drive it one frame at a time instead. The public attributes are for
    reading; only the window's own actions change them.
    """
    screen: Screen
    config: GameConfig
    match: Match
    note: str
    running: bool
    _surface: pygame.Surface
    _clock: pygame.time.Clock
    _fonts: dict[int, pygame.freetype.Font]
    _log: list[Drawn]
    _mouse: tuple[int, int]
    _down: Button | tuple[int, int] | None
    _acted_ms: int
    _inputs: int
    _asked: int
    _last: tuple[int, int] | None
    _passed: frozenset[int]
    _last_ms: int

    def __init__(self, config: GameConfig | None = None) -> None:
        """
        Constructor. Opens the window without sound, so a missing audio
        device never matters, and with the font bundled with pygame, so it
        looks the same on every machine.

        Args:
            config: The match to start at once, or None to open the menu
        """
        pygame.display.init()
        pygame.freetype.init()
        pygame.display.set_caption("Go Python")
        self._surface = pygame.display.set_mode((WIDTH, HEIGHT))
        self._clock = pygame.time.Clock()
        # Kerning stays off: freetype's kerning spaces this font unevenly
        self._fonts = {}
        for size in (15, 18, 21, 25, 38, 66):
            self._fonts[size] = pygame.freetype.Font(None, size)
            self._fonts[size].origin = True
        self._log = []
        self.running = True
        self.screen = Screen.MENU
        self._mouse = (-1, -1)
        self._down = None
        self._acted_ms = 0
        self._inputs = 0
        self._asked = -2
        self.note = ""
        self.config = config or GameConfig()
        # Never shown until a match starts; it saves a None check everywhere,
        # and gives Play its first settings
        self.match = Match(self.config)
        self._last = None
        self._passed = frozenset()
        self._last_ms = 0
        if config is not None:
            self._start(config)

    #
    # Running
    #

    def loop(self) -> None:
        """
        Runs the one event loop until the window closes or Quit is clicked.
        """
        while self.running:
            self.frame()

    def frame(self) -> None:
        """
        Handles waiting events, lets a bot move, then draws.
        """
        for event in pygame.event.get():
            self._handle(event)
        self._bot_turn()
        self.draw()
        pygame.display.flip()
        self._clock.tick(FPS)

    def _handle(self, event: pygame.event.Event) -> None:
        """
        Acts on one event. Anything not listed here is ignored.

        Args:
            event: The event to act on
        """
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEMOTION:
            self._mouse = event.pos
        elif event.type == pygame.WINDOWLEAVE:
            self._mouse = (-1, -1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            soon = pygame.time.get_ticks() - self._acted_ms < DOUBLE_CLICK_MS
            self._down = None if soon else self._target(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._inputs += 1
            # A button acts only if pressed and released on it; the board
            # plays where the mouse is let go, as its preview shows
            down, self._down = self._down, None
            target = self._target(event.pos)
            if isinstance(target, Button) and target == down:
                target.action()
            elif isinstance(target, tuple) and isinstance(down, tuple):
                self._play(target)
        elif event.type == pygame.KEYDOWN:
            self._inputs += 1
            if event.key != pygame.K_ESCAPE:
                return
            if self.screen is Screen.PLAYING:
                self._leave()
            elif self.screen is not Screen.MENU:
                self._go(Screen.MENU)

    def _target(self, pos: tuple[int, int]) -> Button | tuple[int, int] | None:
        """
        Finds what a click at a position would press.

        Args:
            pos: Where the mouse is

        Returns: The button there; else, during or after a match, the board
        point there; else None
        """
        for button in self.buttons():
            if button.rect.collidepoint(pos):
                return button
        if self.screen in (Screen.PLAYING, Screen.GAME_OVER):
            return self._point(pos)
        return None

    def _point(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        """
        Finds the board point under the mouse in a match. The wood beyond the
        edge points counts as the nearest edge point.

        Args:
            pos: Where the mouse is

        Returns: The (row, column), or None off the wood
        """
        if not BOARD.inflate(2 * PAD, 2 * PAD).collidepoint(pos):
            return None
        x = min(max(pos[0], BOARD.left), BOARD.right - 1)
        y = min(max(pos[1], BOARD.top), BOARD.bottom - 1)
        return point_at((x, y), BOARD, self.match.config.size)

    def _bot_turn(self) -> None:
        """
        Makes a bot's move once it has waited BOT_DELAY_MS, between frames.
        """
        if self.screen is Screen.PLAYING and \
           self.match.state is MatchState.BOT_TURN and \
           pygame.time.get_ticks() - self._last_ms >= BOT_DELAY_MS:
            player = self.match.game.turn
            self._record(player, self.match.step())

    def hover(self) -> tuple[int, int] | None:
        """
        Returns the point a person would play by clicking where the mouse
        is: a legal point on their turn, otherwise None
        """
        point = self._point(self._mouse)
        if self.screen is Screen.PLAYING and point is not None and \
           self.match.state is MatchState.HUMAN_TURN and \
           self.match.game.legal_move(point):
            return point
        return None

    #
    # Actions
    #

    def _go(self, screen: Screen) -> None:
        """
        Shows another screen and clears the last message. Presses in the
        next DOUBLE_CLICK_MS are ignored.

        Args:
            screen: The screen to show
        """
        self.screen = screen
        self.note = ""
        self._acted_ms = pygame.time.get_ticks()

    def _quit(self) -> None:
        """
        Ends the event loop.
        """
        self.running = False

    def _setup(self, config: GameConfig) -> None:
        """
        Opens the setup screen.

        Args:
            config: The settings it starts from
        """
        self.config = config
        self._go(Screen.SETUP)

    def _set(self, **changes: Any) -> None:
        """
        Changes settings on the setup screen. GameConfig checks them; a
        refused change keeps the old settings and shows GameConfig's message.

        Args:
            changes: The settings to change, by GameConfig field name
        """
        try:
            self.config = replace(self.config, **changes)
            self.note = ""
        except ValueError as err:
            self.note = str(err).capitalize() + "."

    def _seats(self, count: int) -> None:
        """
        Changes the number of players, seating a smart bot in a new seat.

        Args:
            count: The number of players wanted
        """
        seats = self.config.seats
        self._set(seats=seats[:count] + ("smart",) * (count - len(seats)))

    def _seat(self, index: int, kind: str) -> None:
        """
        Changes who sits in one seat.

        Args:
            index: The seat, from 0
            kind: human, random or smart
        """
        seats = self.config.seats
        self._set(seats=seats[:index] + (kind,) + seats[index + 1:])

    def _start(self, config: GameConfig) -> None:
        """
        Starts a match.

        Args:
            config: The settings of the match
        """
        self.config = config
        self.match = Match(config)
        self._last = None
        self._passed = frozenset()
        self._last_ms = pygame.time.get_ticks()
        self._go(Screen.PLAYING)

    def _play(self, pos: tuple[int, int] | None) -> None:
        """
        Makes a person's move, or says why it cannot be made. Presses in the
        next DOUBLE_CLICK_MS after a move are ignored. A bot's move starts
        no such pause, so a quick reply to it still counts.

        Args:
            pos: The point to play, or None to pass
        """
        game = self.match.game
        if self.match.state is MatchState.FINISHED:
            self.note = "The match is over: Play again or Menu."
        elif self.match.state is not MatchState.HUMAN_TURN:
            self.note = (f"Wait: {PLAYER_NAMES[game.turn - 1]} is a bot "
                         "and moves by itself.")
        elif pos is not None and game.piece_at(pos) is not None:
            self.note = "That point already has a stone."
        elif pos is not None and not game.legal_move(pos):
            self.note = ("Not allowed: a stone there would be captured at "
                         "once, or break the ko rule.")
        else:
            player = game.turn
            self.match.play(pos)
            self._acted_ms = pygame.time.get_ticks()
            self._record(player, pos)

    def _record(self, player: int, pos: tuple[int, int] | None) -> None:
        """
        Notes a move that was just made, and shows the result if it ended
        the match. A stone clears the run of passes.

        Args:
            player: Who moved
            pos: Where they played, or None for a pass
        """
        if pos is None:
            self._passed |= {player}
        else:
            self._passed = frozenset()
            self._last = pos
        self.note = ""
        self._last_ms = pygame.time.get_ticks()
        if self.match.state is MatchState.FINISHED:
            self._go(Screen.GAME_OVER)

    def _leave(self) -> None:
        """
        Asks to confirm leaving the match; leaves if the key press or click
        just before this one asked too. A match left ends with no winner.
        """
        if self._asked == self._inputs - 1:
            self.match.abort()
            self._go(Screen.GAME_OVER)
        else:
            self._asked = self._inputs

    def buttons(self) -> list[Button]:
        """
        Returns the buttons of the current screen
        """
        if self.screen is Screen.MENU:
            # Play offers the last match's settings: the defaults at first
            return [Button(pygame.Rect(604, 300, 200, 54), "Play",
                           partial(self._setup, self.match.config),
                           "primary"),
                    Button(pygame.Rect(604, 370, 200, 54), "Watch bots",
                           partial(self._setup, WATCH)),
                    Button(pygame.Rect(604, 440, 200, 54), "Quit",
                           self._quit)]
        if self.screen is Screen.SETUP:
            return self._setup_buttons()
        left = pygame.Rect(SIDE, 595, 240, 56)
        right = pygame.Rect(SIDE + 248, 595, SIDE_W - 248, 56)
        if self.screen is Screen.PLAYING:
            human = self.match.state is MatchState.HUMAN_TURN
            return [Button(left, "Pass", partial(self._play, None),
                           "primary" if human else "off"),
                    Button(right, "Leave match (Esc)", self._leave)]
        return [Button(left, "Play again",
                       partial(self._start, self.match.config), "primary"),
                Button(right, "Menu", partial(self._go, Screen.MENU))]

    def _setup_buttons(self) -> list[Button]:
        """
        Returns the buttons of the setup screen
        """
        config = self.config

        def chosen(on: bool) -> str:
            """
            Picks the style of an option button.

            Args:
                on: True if the option is the current setting

            Returns: chosen if on, else plain
            """
            return "chosen" if on else "plain"

        buttons = [Button(pygame.Rect(456, 80, 44, 44), "−",
                          partial(self._set, size=config.size - 1)),
                   Button(pygame.Rect(622, 80, 44, 44), "+",
                          partial(self._set, size=config.size + 1))]
        for i, size in enumerate((9, 13, 19)):
            buttons.append(Button(pygame.Rect(690 + i * 120, 80, 112, 44),
                                  f"{size} × {size}",
                                  partial(self._set, size=size),
                                  chosen(config.size == size)))
        for i, (label, superko) in enumerate((("Simple ko", False),
                                               ("Superko", True))):
            buttons.append(Button(pygame.Rect(456 + i * 178, 234, 170, 44),
                                  label, partial(self._set, superko=superko),
                                  chosen(config.superko == superko)))
        for count in range(2, len(PLAYER_NAMES) + 1):
            buttons.append(Button(
                pygame.Rect(600 + (count - 2) * 176, 294, 168, 44),
                f"{count} players", partial(self._seats, count),
                chosen(len(config.seats) == count)))
        for i, seat in enumerate(config.seats):
            for j, kind in enumerate(SEAT_KINDS):
                buttons.append(Button(
                    pygame.Rect(600 + j * 176, 390 + i * 48, 168, 40),
                    SEAT_LABELS[kind], partial(self._seat, i, kind),
                    chosen(seat == kind)))
        start = "Start game" if "human" in config.seats else "Start watching"
        return buttons + [
            Button(pygame.Rect(836, 597, 130, 54), "Back",
                   partial(self._go, Screen.MENU)),
            Button(pygame.Rect(978, 597, 174, 54), start,
                   partial(self._start, config), "primary")]

    #
    # Drawing: reads the state and never changes it
    #

    def draw(self) -> list[Drawn]:
        """
        Draws the current screen.

        Returns: Each text, box and stone beside the board, in the order
        drawn, so tests can check the layout
        """
        self._log = []
        self._surface.fill(BACKDROP)
        if self.screen is Screen.MENU:
            self._draw_menu()
        elif self.screen is Screen.SETUP:
            self._draw_setup()
        else:
            self._draw_match()
        for button in self.buttons():
            self._draw_button(button)
        return self._log

    def _text(self, text: str, size: int, pos: tuple[float, float],
              color: tuple[int, int, int] = INK, anchor: str = "topleft",
              width: int = 0) -> pygame.Rect:
        """
        Draws text, wrapping at the last space that fits.

        Args:
            text: The words
            size: Font size in pixels
            pos: Where the anchor point of the text goes
            color: Text colour
            anchor: Which point of the text sits at pos, as a Rect name
            width: Width to wrap at, or 0 for one line

        Returns: Where the text was drawn
        """
        font = self._fonts[size]
        lines = [""]
        for word in text.split():
            joined = f"{lines[-1]} {word}".strip()
            if width and lines[-1] and font.get_rect(joined).width > width:
                lines.append(word)
            else:
                lines[-1] = joined
        height = font.get_sized_height(size)
        rect = pygame.Rect(0, 0, max(font.get_rect(line).width
                                     for line in lines), height * len(lines))
        setattr(rect, anchor, pos)
        for i, line in enumerate(lines):
            font.render_to(self._surface, (rect.x, rect.y + i * height +
                                           font.get_sized_ascender(size)),
                           line, color)
        if text:
            self._log.append(Drawn("text", rect, text))
        return rect

    def _card(self, rect: pygame.Rect, edge: tuple[int, int, int] = EDGE,
              width: int = 1, fill: tuple[int, int, int] = CARD) -> None:
        """
        Draws a rounded panel.

        Args:
            rect: Where it goes
            edge: Border colour
            width: Border width
            fill: Inside colour
        """
        pygame.draw.rect(self._surface, fill, rect, border_radius=12)
        pygame.draw.rect(self._surface, edge, rect, width, border_radius=12)
        self._log.append(Drawn("box", rect))

    def _draw_button(self, button: Button) -> None:
        """
        Draws a button: under the mouse, a light one darker and a dark one
        lighter.

        Args:
            button: The button
        """
        fill, edge, ink = STYLES[button.style]
        shade = pygame.Color(fill)
        if button.style != "off" and button.rect.collidepoint(self._mouse):
            shade = shade.lerp(MUTED, 0.2 if sum(fill) > 384 else 0.5)
        pygame.draw.rect(self._surface, shade, button.rect, border_radius=10)
        pygame.draw.rect(self._surface, edge, button.rect, 2,
                         border_radius=10)
        self._log.append(Drawn("box", button.rect))
        self._text(button.label, 21, button.rect.center, ink, "center")

    def _draw_board(self, rect: pygame.Rect, size: int) -> None:
        """
        Draws an empty wooden board with its lines and marked points.

        Args:
            rect: Where the grid goes
            size: Number of points on each side
        """
        spacing = rect.width / size
        wood = rect.inflate(2 * PAD, 2 * PAD)
        pygame.draw.rect(self._surface, WOOD, wood, border_radius=16)
        self._log.append(Drawn("box", wood))
        for i in range(size):
            x, y = center(rect, size, (i, i))
            pygame.draw.line(self._surface, GRID, (rect.x + spacing / 2, y),
                             (rect.right - spacing / 2, y))
            pygame.draw.line(self._surface, GRID, (x, rect.y + spacing / 2),
                             (x, rect.bottom - spacing / 2))
        for point in star_points(size):
            pygame.draw.aacircle(self._surface, GRID,
                                 center(rect, size, point),
                                 max(2.5, spacing / 10))

    def _draw_stone(self, pos: tuple[float, float], radius: float,
                    player: int, on_wood: bool = True) -> None:
        """
        Draws a stone with a rim, a shine and, on the board, a shadow.

        Args:
            pos: Centre of the stone
            radius: Radius of the stone
            player: Whose stone, from 1
            on_wood: True to draw its shadow on the board
        """
        color = pygame.Color(STONES[player - 1])
        x, y = pos
        if on_wood:
            pygame.draw.aacircle(self._surface, SHADOW,
                                 (x + radius / 8, y + radius / 6), radius)
        else:
            self._log.append(Drawn("stone", pygame.Rect(
                x - radius, y - radius, 2 * radius, 2 * radius),
                PLAYER_NAMES[player - 1]))
        pygame.draw.aacircle(self._surface, color, pos, radius)
        pygame.draw.aacircle(self._surface, color.lerp(GRID, 0.4), pos,
                             radius, max(1, round(radius / 14)))
        pygame.draw.aacircle(self._surface, color.lerp(CARD, 0.3),
                             (x - radius / 3, y - radius / 3), radius / 4)

    def _draw_menu(self) -> None:
        """
        Draws the menu: a sample board, the title and what each button does.
        """
        self._draw_board(HERO, 9)
        for point, player in HERO_STONES:
            self._draw_stone(center(HERO, 9, point), HERO.width / 9 * 0.47,
                             player)
        self._text("Go Python", 66, (600, 136))
        self._text("The board game Go for 2 to 4 players. Play people or "
                   "bots, or watch the bots play each other.", 21,
                   (604, 214), MUTED, width=540)
        for button, hint in zip(self.buttons(), MENU_HINTS, strict=True):
            self._text(hint, 18, (button.rect.right + 20,
                                  button.rect.centery), MUTED,
                       "midleft", 330)
        self._text(f"Version {__version__}", 15, (WIDTH - 24, HEIGHT - 20),
                   MUTED, "bottomright")

    def _draw_setup(self) -> None:
        """
        Draws the setup screen: a preview of the board, what each choice
        means, and GameConfig's message under the control that caused it.
        """
        config = self.config
        if "human" in config.seats:
            title, intro = "New game", ("The defaults are ready: press "
                                        "Start game, or change anything "
                                        "first.")
        else:
            title, intro = "Watch bots", ("Every seat is a bot. Press Start "
                                          "watching, then sit back.")
        self._text(title, 38, (48, 24))
        self._text(intro, 18, (48, 76), MUTED, width=360)
        self._draw_board(PREVIEW, config.size)

        card = pygame.Rect(48, 494, 360, 157)
        self._card(card)
        self._text("New to Go?", 21, (card.x + 16, card.y + 14))
        self._text(HOW_TO_PLAY, 15, (card.x + 16, card.y + 40), MUTED,
                   width=card.width - 32)

        self._text("Board size", 25, (456, 24))
        self._text("Lines on each side. 9 × 9 is quick; 19 × 19 "
                   "is the classic board.", 15, (456, 56), MUTED)
        # The size between − and +, as plain text: it is not a button
        self._text(f"{config.size} × {config.size}", 21, (561, 102),
                   anchor="center")
        # Only the size can be refused; every other control offers valid
        # choices only
        self._text(self.note, 15, (456, 132), ERROR)

        self._text("Ko rule", 25, (456, 160))
        self._text("Simple ko: no move may bring back the board as it was "
                   "one move ago. Superko: no move may bring back any "
                   "earlier board.", 15, (456, 192), MUTED, width=696)

        self._text("Players", 25, (456, 302))
        self._text(SEAT_HELP, 15, (456, 346), MUTED, width=696)
        for i in range(len(config.seats)):
            y = 390 + i * 48 + 20
            self._draw_stone((470, y), 13, i + 1, on_wood=False)
            self._text(PLAYER_NAMES[i], 21, (492, y), anchor="midleft")

    def _draw_match(self) -> None:
        """
        Draws a match being played or just finished: the board on the left,
        then the sidebar with the turn or the result, the players and their
        scores, and what the buttons below do.
        """
        game = self.match.game
        config = self.match.config
        radius = BOARD.width / config.size * 0.47
        self._draw_board(BOARD, config.size)
        for r, row in enumerate(game.grid):
            for c, player in enumerate(row):
                if player is not None:
                    self._draw_stone(center(BOARD, config.size, (r, c)),
                                     radius, player)
        if self._last is not None:
            # A dark ring on White's stone, a light ring on the others
            mark = GRID if game.piece_at(self._last) == 2 else CARD
            pygame.draw.aacircle(self._surface, mark,
                                 center(BOARD, config.size, self._last),
                                 radius * 0.42, max(2, round(radius / 8)))
        hover = self.hover()
        if hover is not None:
            ghost = pygame.Surface((2 * radius + 2, 2 * radius + 2),
                                   pygame.SRCALPHA)
            pygame.draw.aacircle(ghost, (*STONES[game.turn - 1], 140),
                                 (radius + 1, radius + 1), radius)
            # A rim darker than a stone's keeps even White at 3:1 on the wood
            rim = pygame.Color(STONES[game.turn - 1]).lerp(GRID, 0.7)
            pygame.draw.aacircle(ghost, rim, (radius + 1, radius + 1), radius,
                                 max(2, round(radius / 14)))
            self._surface.blit(ghost, ghost.get_rect(
                center=center(BOARD, config.size, hover)))

        self._draw_status()
        self._draw_players()
        # The details follow straight after the last player's row
        y = 182 + len(config.seats) * 64
        ko = "superko" if config.superko else "simple ko"
        self._text(f"{config.size} × {config.size} board · {ko} · "
                   f"{self.match.moves} of at most {self.match.move_limit} "
                   "moves played", 15, (SIDE, y), MUTED)
        swing = (" One stone alone claims the whole empty board, so early "
                 "numbers swing." if self.screen is Screen.PLAYING else "")
        self._text("Area: your stones plus the empty points only your "
                   "stones surround." + swing, 15, (SIDE, y + 24), MUTED,
                   width=SIDE_W)
        color = MUTED
        if self.screen is Screen.GAME_OVER:
            caption = "Play again keeps the same board and players."
            if self.note:
                # A click on the finished board is answered by the buttons
                caption, color = self.note, ERROR
        elif "human" in config.seats:
            caption = ("Pass skips your turn. When every player passes in "
                       "a row, the game ends and the most area wins.")
        else:
            caption = ("The bots play on their own. When every player "
                       "passes in a row, the game ends and the most area "
                       "wins.")
        self._text(caption, 15, (SIDE, 585), color, "bottomleft", SIDE_W)

    def _draw_status(self) -> None:
        """
        Draws the top of the sidebar: whose turn it is and what to do, why
        a click did nothing, or how to confirm leaving; at the end, who won
        and why.
        """
        result = self.match.result
        player: int | None
        if result is None:
            player = self.match.game.turn
            seat = self.match.config.seats[player - 1]
            headline = f"{PLAYER_NAMES[player - 1]} to play"
            asking = self._asked == self._inputs
            line = LEAVE_ASK if asking else self.note or (
                "Click a point on the board to place a stone."
                if seat == "human" else
                f"{SEAT_LABELS[seat]} is choosing a move…")
            color = ERROR if asking or self.note else MUTED
        else:
            headline, line = summary(result, self.match.moves)
            color = INK
            player = result.winners[0] if len(result.winners) == 1 else None
        self._card(pygame.Rect(SIDE, 24, SIDE_W, 136))
        x = SIDE + 20
        if player is not None:
            self._draw_stone((SIDE + 42, 66), 22, player, on_wood=False)
            x = SIDE + 76
        self._text(headline, 38, (x, 66), anchor="midleft")
        self._text(line, 18, (SIDE + 20, 104), color, width=SIDE_W - 40)

    def _draw_players(self) -> None:
        """
        Draws a row per player: stone, name, seat, status and area. The
        player to move is outlined; at the end, the winners are, in gold.
        """
        game = self.match.game
        result = self.match.result
        scores = game.scores()
        for i, seat in enumerate(self.match.config.seats):
            player = i + 1
            rect = pygame.Rect(SIDE, 172 + i * 64, SIDE_W, 56)
            status, color = "", INK
            if result is not None and player in result.winners:
                self._card(rect, GOLD, 3, TINT)
                status, color = "Winner", GOLD
            elif result is None and game.turn == player:
                self._card(rect, INK, 3, TINT)
                status = "To play"
            else:
                self._card(rect)
                if result is None and player in self._passed:
                    status, color = "Passed", MUTED
            y = rect.centery
            self._draw_stone((rect.x + 30, y), 15, player, on_wood=False)
            self._text(PLAYER_NAMES[i], 21, (rect.x + 56, y), anchor="midleft")
            self._text(SEAT_LABELS[seat], 15, (rect.x + 136, y), MUTED,
                       "midleft")
            self._text(status, 15, (rect.x + 256, y), color, "midleft")
            self._text(str(scores[player]), 21, (rect.right - 16, y),
                       anchor="midright")
            # Room for three digits keeps the labels in one column
            self._text("Area", 15, (rect.right - 60, y), MUTED, "midright")

def run(config: GameConfig | None = None) -> None:
    """
    Opens the window and returns when it closes.

    Args:
        config: The match to start at once, or None to open the menu
    """
    GoGUI(config).loop()
    pygame.quit()
