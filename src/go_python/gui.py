"""
The Go Python window: a menu, a setup screen, the match and its result.
The window only reads the game; every move goes through a Match.
"""
import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum, auto
from functools import partial
from typing import Any

from go_python import __version__
from go_python.match import (PLAYER_NAMES, SEAT_KINDS, EndReason, GameConfig,
                             Match, MatchResult, MatchState)

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame  # noqa: E402

#
# Layout, colours and timing
#

WIDTH, HEIGHT = 1200, 675
FPS = 30
# Pause before each bot move so a person can follow the game; tests set 0
BOT_DELAY_MS = 600

# The board keeps its original look: off-white backdrop, wood, black lines
BACKDROP = (249, 241, 241)
WOOD = (207, 185, 151)
GRID = (0, 0, 0)
SHADOW = (166, 144, 112)
# Stone colours in turn order, named by PLAYER_NAMES
STONES = ((0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 0, 255))

INK = (43, 36, 36)
MUTED = (118, 104, 104)
CARD = (255, 255, 255)
EDGE = (226, 212, 212)
TINT = (255, 246, 228)
CHOSEN = (246, 226, 186)
GOLD = (186, 130, 20)
ERROR = (176, 28, 28)
# Fill, edge and label colour of each button style
STYLES = {"plain": (CARD, EDGE, INK), "primary": (INK, INK, CARD),
          "chosen": (CHOSEN, GOLD, INK), "off": (EDGE, EDGE, MUTED)}
FONT = "notosans,opensans,dejavusans,liberationsans,arial"

# Where the grid goes; the wood reaches PAD further out on every side
BOARD = pygame.Rect(298, 36, 603, 603)
PAD = 12
LEFT, RIGHT, PANEL = 24, 938, 238
HERO = pygame.Rect(108, 130, 416, 416)
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
               "is your stones plus the empty points only you surround. "
               "When every player passes in a row, the most points wins.")
SEAT_HELP = ("Human: you click the board to play. Random bot: plays any "
             "legal move. Smart bot: looks for the move that gains most.")

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
    action: Callable[[], None]
    style: str = "plain"

#
# Pure helpers
#

def point_at(mouse: tuple[int, int], board: pygame.Rect,
             size: int) -> tuple[int, int] | None:
    """
    Finds the board point under the mouse. This is the whole of hover.

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

def summary(result: MatchResult, moves: int) -> tuple[str, str]:
    """
    Words for how a match ended.

    Args:
        result: How the match finished
        moves: Number of moves and passes made

    Returns: A headline naming the winner(s), and a line saying why the
    match ended
    """
    names = [PLAYER_NAMES[player - 1] for player in result.winners]
    why = f"{result.reason.value.capitalize()} after {moves} moves."
    if result.reason is EndReason.ABORTED:
        return "Match left", why + " No winner."
    if len(names) > 1:
        return ", ".join(names[:-1]) + f" and {names[-1]} tie", why
    best, second = sorted(result.scores.values(), reverse=True)[:2]
    margin = best - second
    return f"{names[0]} wins", f"By {margin} point{'s' * (margin != 1)}. {why}"

#
# The window
#

class GoGUI:
    """
    The window. The constructor only sets it up; loop() runs it, and tests
    can drive it one frame at a time instead.
    """
    _surface: pygame.Surface
    _clock: pygame.time.Clock
    _fonts: dict[tuple[int, bool], pygame.font.Font]
    _running: bool
    _screen: Screen
    _config: GameConfig
    _match: Match
    _mouse: tuple[int, int]
    _note: str
    _last: tuple[int, int] | None
    _passed: frozenset[int]
    _last_ms: int

    def __init__(self, config: GameConfig | None = None) -> None:
        """
        Constructor. Opens the window without sound, so a missing audio
        device never matters.

        Args:
            config: The match to start at once, or None to open the menu
        """
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption("Go Python")
        self._surface = pygame.display.set_mode((WIDTH, HEIGHT))
        self._clock = pygame.time.Clock()
        self._fonts = {(size, bold): pygame.font.SysFont(FONT, size, bold)
                       for size in (14, 16, 18, 22, 28, 40, 64)
                       for bold in (False, True)}
        self._running = True
        self._screen = Screen.MENU
        self._mouse = (-1, -1)
        self._note = ""
        self._config = config or GameConfig()
        # Never shown until a match starts; it saves a None check everywhere
        self._match = Match(self._config)
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
        while self._running:
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
            self._running = False
        elif event.type == pygame.MOUSEMOTION:
            self._mouse = event.pos
        elif event.type == pygame.WINDOWLEAVE:
            self._mouse = (-1, -1)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._click(event.pos)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._screen is Screen.PLAYING:
                self._leave()
            elif self._screen is not Screen.MENU:
                self._go(Screen.MENU)

    def _click(self, pos: tuple[int, int]) -> None:
        """
        Presses the button under a click, or plays the board point under it.

        Args:
            pos: Where the click was
        """
        for button in self._buttons():
            if button.rect.collidepoint(pos):
                button.action()
                return
        point = point_at(pos, BOARD, self._match.config.size)
        if self._screen is Screen.PLAYING and point is not None:
            self._play(point)

    def _bot_turn(self) -> None:
        """
        Makes a bot's move once it has waited BOT_DELAY_MS, between frames.
        """
        if self._screen is Screen.PLAYING and \
           self._match.state is MatchState.BOT_TURN and \
           pygame.time.get_ticks() - self._last_ms >= BOT_DELAY_MS:
            player = self._match.game.turn
            self._record(player, self._match.step())

    def _hover(self) -> tuple[int, int] | None:
        """
        Returns the point a person would play by clicking where the mouse
        is: a legal point on their turn, otherwise None
        """
        point = point_at(self._mouse, BOARD, self._match.config.size)
        if self._screen is Screen.PLAYING and point is not None and \
           self._match.state is MatchState.HUMAN_TURN and \
           self._match.game.legal_move(point):
            return point
        return None

    #
    # Actions
    #

    def _go(self, screen: Screen) -> None:
        """
        Shows another screen and clears the last message.

        Args:
            screen: The screen to show
        """
        self._screen = screen
        self._note = ""

    def _quit(self) -> None:
        """
        Ends the event loop.
        """
        self._running = False

    def _setup(self, config: GameConfig) -> None:
        """
        Opens the setup screen.

        Args:
            config: The settings it starts from
        """
        self._config = config
        self._go(Screen.SETUP)

    def _set(self, **changes: Any) -> None:
        """
        Changes settings on the setup screen. GameConfig checks them; a
        refused change keeps the old settings and shows GameConfig's message.

        Args:
            changes: The settings to change, by GameConfig field name
        """
        try:
            self._config = replace(self._config, **changes)
            self._note = ""
        except ValueError as err:
            self._note = str(err).capitalize() + "."

    def _seats(self, count: int) -> None:
        """
        Changes the number of players, seating a smart bot in a new seat.

        Args:
            count: The number of players wanted
        """
        seats = self._config.seats
        self._set(seats=seats[:count] + ("smart",) * (count - len(seats)))

    def _seat(self, index: int, kind: str) -> None:
        """
        Changes who sits in one seat.

        Args:
            index: The seat, from 0
            kind: human, random or smart
        """
        seats = self._config.seats
        self._set(seats=seats[:index] + (kind,) + seats[index + 1:])

    def _start(self, config: GameConfig) -> None:
        """
        Starts a match.

        Args:
            config: The settings of the match
        """
        self._config = config
        self._match = Match(config)
        self._last = None
        self._passed = frozenset()
        self._last_ms = pygame.time.get_ticks()
        self._go(Screen.PLAYING)

    def _play(self, pos: tuple[int, int] | None) -> None:
        """
        Makes a person's move, or says why it cannot be made.

        Args:
            pos: The point to play, or None to pass
        """
        game = self._match.game
        if self._match.state is not MatchState.HUMAN_TURN:
            self._note = (f"Wait: {PLAYER_NAMES[game.turn - 1]} is a bot "
                          "and moves by itself.")
        elif pos is not None and game.piece_at(pos) is not None:
            self._note = "That point already has a stone."
        elif pos is not None and not game.legal_move(pos):
            self._note = ("Not allowed: a stone there would be captured "
                          "at once, or break the ko rule.")
        else:
            player = game.turn
            self._match.play(pos)
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
        self._note = ""
        self._last_ms = pygame.time.get_ticks()
        if self._match.state is MatchState.FINISHED:
            self._screen = Screen.GAME_OVER

    def _leave(self) -> None:
        """
        Leaves the match. It ends with no winner.
        """
        self._match.abort()
        self._go(Screen.GAME_OVER)

    def _buttons(self) -> list[Button]:
        """
        Returns the buttons of the current screen
        """
        if self._screen is Screen.MENU:
            return [Button(pygame.Rect(620, 300, 200, 54), "Play",
                           partial(self._setup, GameConfig()), "primary"),
                    Button(pygame.Rect(620, 370, 200, 54), "Watch bots",
                           partial(self._setup, WATCH)),
                    Button(pygame.Rect(620, 440, 200, 54), "Quit",
                           self._quit)]
        if self._screen is Screen.SETUP:
            return self._setup_buttons()
        if self._screen is Screen.PLAYING:
            human = self._match.state is MatchState.HUMAN_TURN
            return [Button(pygame.Rect(RIGHT, 196, PANEL, 56), "Pass",
                           partial(self._play, None),
                           "primary" if human else "off"),
                    Button(pygame.Rect(RIGHT, 332, PANEL, 48),
                           "Leave match (Esc)", self._leave)]
        return [Button(pygame.Rect(RIGHT, 230, PANEL, 56), "Play again",
                       partial(self._start, self._match.config), "primary"),
                Button(pygame.Rect(RIGHT, 298, PANEL, 48), "Menu",
                       partial(self._go, Screen.MENU))]

    def _setup_buttons(self) -> list[Button]:
        """
        Returns the buttons of the setup screen
        """
        config = self._config

        def chosen(on: bool) -> str:
            return "chosen" if on else "plain"

        buttons = [Button(pygame.Rect(64, 204, 44, 44), "−",
                          partial(self._set, size=config.size - 1)),
                   Button(pygame.Rect(226, 204, 44, 44), "+",
                          partial(self._set, size=config.size + 1))]
        for i, size in enumerate((9, 13, 19)):
            buttons.append(Button(pygame.Rect(294 + i * 92, 204, 84, 44),
                                  f"{size} × {size}",
                                  partial(self._set, size=size),
                                  chosen(config.size == size)))
        for i, (label, superko) in enumerate((("Simple ko", False),
                                               ("Superko", True))):
            buttons.append(Button(pygame.Rect(64 + i * 168, 316, 160, 44),
                                  label, partial(self._set, superko=superko),
                                  chosen(config.superko == superko)))
        for count in range(2, len(PLAYER_NAMES) + 1):
            buttons.append(Button(
                pygame.Rect(640 + (count - 2) * 112, 204, 104, 44),
                f"{count} players", partial(self._seats, count),
                chosen(len(config.seats) == count)))
        for i, seat in enumerate(config.seats):
            for j, kind in enumerate(SEAT_KINDS):
                buttons.append(Button(
                    pygame.Rect(752 + j * 128, 272 + i * 54, 122, 42),
                    SEAT_LABELS[kind], partial(self._seat, i, kind),
                    chosen(seat == kind)))
        start = "Start game" if "human" in config.seats else "Start watching"
        return buttons + [
            Button(pygame.Rect(812, 597, 120, 54), "Back",
                   partial(self._go, Screen.MENU)),
            Button(pygame.Rect(944, 597, 192, 54), start,
                   partial(self._start, config), "primary")]

    #
    # Drawing: reads the state and never changes it
    #

    def draw(self) -> None:
        """
        Draws the current screen.
        """
        self._surface.fill(BACKDROP)
        if self._screen is Screen.MENU:
            self._draw_menu()
        elif self._screen is Screen.SETUP:
            self._draw_setup()
        else:
            self._draw_match()
        for button in self._buttons():
            self._draw_button(button)

    def _text(self, text: str, size: int, pos: tuple[float, float],
              color: tuple[int, int, int] = INK, bold: bool = False,
              anchor: str = "topleft", width: int = 0) -> pygame.Rect:
        """
        Draws text.

        Args:
            text: The words
            size: Font size
            pos: Where the anchor point of the text goes
            color: Text colour
            bold: True for bold
            anchor: Which point of the text sits at pos, as a Rect name
            width: Width to wrap at, or 0 for one line

        Returns: Where the text was drawn
        """
        image = self._fonts[size, bold].render(text, True, color,
                                               wraplength=width)
        rect = image.get_rect(**{anchor: pos})
        self._surface.blit(image, rect)
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

    def _draw_button(self, button: Button) -> None:
        """
        Draws a button, a shade darker or lighter under the mouse.

        Args:
            button: The button
        """
        fill, edge, ink = STYLES[button.style]
        shade = pygame.Color(fill)
        if button.style != "off" and button.rect.collidepoint(self._mouse):
            shade = shade.lerp(MUTED, 0.15)
        pygame.draw.rect(self._surface, shade, button.rect, border_radius=10)
        pygame.draw.rect(self._surface, edge, button.rect, 2,
                         border_radius=10)
        self._text(button.label, 18, button.rect.center, ink, True, "center")

    def _draw_board(self, rect: pygame.Rect, size: int) -> None:
        """
        Draws an empty wooden board with its lines and marked points.

        Args:
            rect: Where it goes
            size: Number of points on each side
        """
        spacing = rect.width / size
        pygame.draw.rect(self._surface, WOOD, rect.inflate(2 * PAD, 2 * PAD),
                         border_radius=16)
        width = max(1, round(spacing / 30))
        for i in range(size):
            x, y = center(rect, size, (i, i))
            pygame.draw.line(self._surface, GRID, (rect.x + spacing / 2, y),
                             (rect.right - spacing / 2, y), width)
            pygame.draw.line(self._surface, GRID, (x, rect.y + spacing / 2),
                             (x, rect.bottom - spacing / 2), width)
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
        self._text("Go Python", 64, (616, 128), bold=True)
        self._text("The board game Go for 2 to 4 players. Play people or "
                   "bots, or watch the bots play each other.", 22,
                   (620, 214), MUTED, width=520)
        for button, hint in zip(self._buttons(), MENU_HINTS, strict=True):
            self._text(hint, 16, (button.rect.right + 20,
                                  button.rect.centery), MUTED,
                       anchor="midleft", width=330)
        self._text(f"Version {__version__}", 14, (WIDTH - 24, HEIGHT - 20),
                   MUTED, anchor="bottomright")

    def _draw_setup(self) -> None:
        """
        Draws the setup screen: what each choice means, and any message
        from GameConfig.
        """
        config = self._config
        if "human" in config.seats:
            title, intro = "New game", ("The defaults are ready: press "
                                        "Start game, or change anything "
                                        "first.")
        else:
            title, intro = "Watch bots", ("Every seat is a bot. Press Start "
                                          "watching, then sit back.")
        self._text(title, 40, (64, 30), bold=True)
        self._text(intro, 18, (66, 88), MUTED)

        self._text("Board size", 22, (64, 140), bold=True)
        self._text("Lines on each side. 9 × 9 is quick; 19 × 19 "
                   "is the classic board.", 16, (64, 172), MUTED)
        box = pygame.Rect(114, 204, 106, 44)
        self._card(box)
        self._text(f"{config.size} × {config.size}", 18, box.center,
                   bold=True, anchor="center")

        self._text("Ko rule", 22, (64, 284), bold=True)
        self._text("Simple ko: no move may bring back the board as it was "
                   "one move ago. Superko: no move may bring back any "
                   "earlier board.", 16, (64, 372), MUTED, width=500)

        card = pygame.Rect(64, 436, 500, 148)
        self._card(card)
        self._text("New to Go?", 18, (card.x + 16, card.y + 12), bold=True)
        self._text(HOW_TO_PLAY, 16, (card.x + 16, card.y + 40), MUTED,
                   width=card.width - 32)

        self._text("Players", 22, (640, 140), bold=True)
        self._text("How many play, and who sits in each seat. Black moves "
                   "first.", 16, (640, 172), MUTED)
        for i in range(len(config.seats)):
            y = 272 + i * 54 + 21
            self._draw_stone((656, y), 14, i + 1, on_wood=False)
            self._text(PLAYER_NAMES[i], 18, (680, y), bold=True,
                       anchor="midleft")
        self._text(SEAT_HELP, 16, (640, 280 + len(config.seats) * 54),
                   MUTED, width=496)
        if self._note:
            self._text(self._note, 18, (64, 624), ERROR, bold=True,
                       anchor="midleft")

    def _draw_match(self) -> None:
        """
        Draws a match being played or just finished: the board, the
        players and their scores, then the turn or the result.
        """
        game = self._match.game
        size = self._match.config.size
        radius = BOARD.width / size * 0.47
        self._draw_board(BOARD, size)
        for r, row in enumerate(game.grid):
            for c, player in enumerate(row):
                if player is not None:
                    self._draw_stone(center(BOARD, size, (r, c)), radius,
                                     player)
        if self._last is not None:
            # A dark ring on White's stone, a light ring on the others
            mark = GRID if game.piece_at(self._last) == 2 else CARD
            pygame.draw.aacircle(self._surface, mark,
                                 center(BOARD, size, self._last),
                                 radius * 0.42, max(2, round(radius / 8)))
        hover = self._hover()
        if hover is not None:
            ghost = pygame.Surface((2 * radius + 2, 2 * radius + 2),
                                   pygame.SRCALPHA)
            pygame.draw.aacircle(ghost, (*STONES[game.turn - 1], 140),
                                 (radius + 1, radius + 1), radius)
            self._surface.blit(ghost, ghost.get_rect(
                center=center(BOARD, size, hover)))
        self._draw_players()
        if self._screen is Screen.PLAYING:
            self._draw_turn()
        else:
            self._draw_result()

    def _draw_players(self) -> None:
        """
        Draws a card per player on the left: stone, name, seat, score and
        a status line. The player to move is outlined; at the end, the
        winners are.
        """
        game = self._match.game
        config = self._match.config
        result = self._match.result
        scores = game.scores()
        self._text("Players", 16, (LEFT, 22), MUTED, bold=True)
        for i, seat in enumerate(config.seats):
            player = i + 1
            rect = pygame.Rect(LEFT, 50 + i * 98, PANEL, 88)
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
            self._draw_stone((rect.x + 32, rect.centery), 17, player,
                             on_wood=False)
            self._text(PLAYER_NAMES[i], 22, (rect.x + 60, rect.y + 8),
                       bold=True)
            self._text(SEAT_LABELS[seat], 16, (rect.x + 60, rect.y + 38),
                       MUTED)
            self._text(status, 14, (rect.x + 60, rect.y + 62), color, True)
            self._text(str(scores[player]), 28,
                       (rect.right - 16, rect.y + 8), bold=True,
                       anchor="topright")
            self._text("points", 14, (rect.right - 16, rect.y + 48), MUTED,
                       anchor="topright")
        y = 50 + len(config.seats) * 98 + 4
        ko = "superko" if config.superko else "simple ko"
        self._text(f"{config.size} × {config.size} board, {ko}", 16,
                   (LEFT, y), MUTED)
        self._text(f"Move {self._match.moves} of at most "
                   f"{self._match.move_limit}", 16, (LEFT, y + 24), MUTED)
        self._text("Score: your stones plus the empty points that only "
                   "your stones surround.", 14, (LEFT, HEIGHT - 24), MUTED,
                   anchor="bottomleft", width=PANEL)

    def _draw_turn(self) -> None:
        """
        Draws whose turn it is and what to do, or why a click did nothing,
        on the right.
        """
        player = self._match.game.turn
        seat = self._match.config.seats[player - 1]
        self._card(pygame.Rect(RIGHT, 24, PANEL, 156))
        self._draw_stone((RIGHT + 34, 64), 18, player, on_wood=False)
        self._text(f"{PLAYER_NAMES[player - 1]} to play", 22,
                   (RIGHT + 62, 64), bold=True, anchor="midleft")
        if self._note:
            doing, color = self._note, ERROR
        elif seat == "human":
            doing, color = "Click a point on the board to place a stone.", \
                MUTED
        else:
            doing, color = f"{SEAT_LABELS[seat]} is choosing a move…", MUTED
        self._text(doing, 16, (RIGHT + 16, 98), color, color == ERROR,
                   width=PANEL - 32)
        self._text("Skip your turn. When every player passes in a row, the "
                   "game ends and the most points wins.", 14,
                   (RIGHT, 260), MUTED, width=PANEL)
        self._text("The faint stone shows where yours will go. The ring "
                   "marks the last stone played.", 14,
                   (RIGHT, HEIGHT - 24), MUTED, anchor="bottomleft",
                   width=PANEL)

    def _draw_result(self) -> None:
        """
        Draws who won and why the match ended, on the right.
        """
        result = self._match.result
        assert result is not None
        headline, why = summary(result, self._match.moves)
        self._card(pygame.Rect(RIGHT, 24, PANEL, 190))
        x = RIGHT + 16
        if len(result.winners) == 1:
            self._draw_stone((RIGHT + 34, 64), 18, result.winners[0],
                             on_wood=False)
            x = RIGHT + 62
        rect = self._text(headline, 28, (x, 44), bold=True,
                          width=RIGHT + PANEL - 16 - x)
        self._text("Game over", 14, (RIGHT + 16, rect.bottom + 14), MUTED,
                   bold=True)
        self._text(why, 16, (RIGHT + 16, rect.bottom + 36), INK,
                   width=PANEL - 32)
        self._text("Play again keeps the same board and players.", 14,
                   (RIGHT, 358), MUTED, width=PANEL)

def run(config: GameConfig | None = None) -> None:
    """
    Opens the window and returns when it closes.

    Args:
        config: The match to start at once, or None to open the menu
    """
    GoGUI(config).loop()
    pygame.quit()
