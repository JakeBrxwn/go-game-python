"""
Drives the real window with posted pygame events, on a display that shows
nothing: menu, setup, play and game over. What the window shows is checked
from its pixels and from the list of what draw() put where.
"""
import random
from collections.abc import Iterator
from itertools import combinations, pairwise
from typing import Any

import pygame
import pytest

from go_python import __version__, gui
from go_python.gui import (BOARD, GoGUI, Screen, center, point_at, points,
                           star_points, summary)
from go_python.match import EndReason, GameConfig, MatchResult, MatchState

Color = tuple[int, int, int]

@pytest.fixture(autouse=True)
def dummy_window(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Use the dummy SDL drivers, and run bots, clicks and frames without
    waiting"""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 0)
    monkeypatch.setattr(gui, "DOUBLE_CLICK_MS", 0)
    monkeypatch.setattr(gui, "FPS", 0)
    yield
    pygame.quit()

#
# Helpers: input
#

def post(kind: int, **attrs: Any) -> None:
    """Posts one real pygame event"""
    pygame.event.post(pygame.event.Event(kind, **attrs))

def move(window: GoGUI, pos: tuple[float, float]) -> None:
    """Moves the mouse, then runs a frame"""
    post(pygame.MOUSEMOTION, pos=(round(pos[0]), round(pos[1])),
         rel=(0, 0), buttons=(0, 0, 0))
    window.frame()

def click(window: GoGUI, pos: tuple[float, float]) -> None:
    """Moves the mouse, presses and releases the left button there, then
    runs a frame"""
    x, y = round(pos[0]), round(pos[1])
    post(pygame.MOUSEMOTION, pos=(x, y), rel=(0, 0), buttons=(0, 0, 0))
    post(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)
    post(pygame.MOUSEBUTTONUP, pos=(x, y), button=1)
    window.frame()

def button(window: GoGUI, label: str, nth: int = 0) -> pygame.Rect:
    """Returns where the nth button with this label is"""
    return [b.rect for b in window.buttons() if b.label == label][nth]

def press(window: GoGUI, label: str, nth: int = 0) -> None:
    """Clicks the nth button with this label on the current screen"""
    click(window, button(window, label, nth).center)

def spot(window: GoGUI, point: tuple[int, int]) -> tuple[float, float]:
    """Returns where a board point is drawn in the current match"""
    return center(BOARD, window.match.config.size, point)

def key(window: GoGUI, which: int) -> None:
    """Presses a key, then runs a frame"""
    post(pygame.KEYDOWN, key=which)
    window.frame()

def escape(window: GoGUI) -> None:
    """Presses Esc, then runs a frame"""
    key(window, pygame.K_ESCAPE)

def leave(window: GoGUI) -> None:
    """Leaves the match: Esc, then Esc again to confirm"""
    escape(window)
    escape(window)

#
# Helpers: what is on the screen
#

def screen() -> pygame.Surface:
    """Returns what the window shows"""
    surface = pygame.display.get_surface()
    assert surface is not None
    return surface

def pixel(pos: tuple[float, float]) -> Color:
    """Returns the colour on the screen at a position"""
    r, g, b, _ = screen().get_at((round(pos[0]), round(pos[1])))
    return (r, g, b)

def on_point(window: GoGUI, point: tuple[int, int]) -> Color:
    """Returns the colour inside a board point's stone, clear of the lines,
    the shine, the last-move ring and the star points"""
    x, y = spot(window, point)
    step = BOARD.width / window.match.config.size * 0.2
    return pixel((x + step, y + step))

def count(rect: pygame.Rect, color: Color) -> int:
    """Counts the screen pixels of exactly this colour inside rect"""
    area = screen().subsurface(rect)
    return int(pygame.mask.from_threshold(area, color, (1, 1, 1, 255))
               .count())

def texts(window: GoGUI) -> list[str]:
    """Draws once and returns the words of every text drawn"""
    return [d.text for d in window.draw() if d.kind == "text"]

def box_around(window: GoGUI, words: str) -> pygame.Rect:
    """Draws once and returns the box that holds the text with these words"""
    drawn = window.draw()
    rect = next(d.rect for d in drawn if d.kind == "text" and d.text == words)
    return next(d.rect for d in drawn
                if d.kind == "box" and d.rect.contains(rect))

def edge(rect: pygame.Rect) -> Color:
    """Returns a box's border colour, read at the middle of its top edge"""
    return pixel((rect.centerx, rect.y))

def fill(rect: pygame.Rect) -> Color:
    """Returns a button's fill colour, read left of its label"""
    return pixel((rect.x + 6, rect.centery))

def contrast(one: Color, two: Color) -> float:
    """Returns the WCAG contrast ratio of two colours, from 1 to 21"""
    def luminance(color: Color) -> float:
        def linear(value: int) -> float:
            v = value / 255
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = map(linear, color)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    light, dark = sorted((luminance(one), luminance(two)), reverse=True)
    return (light + 0.05) / (dark + 0.05)

def assert_tidy(window: GoGUI) -> list[str]:
    """
    Draws once and checks the layout: every text and side stone inside the
    window, either clear of a box or inside it with room to spare, no two
    of them touching, and no two boxes overlapping.

    Returns: The texts drawn, for the caller to check
    """
    drawn = window.draw()
    marks = [d for d in drawn if d.kind != "box"]
    boxes = [d.rect for d in drawn if d.kind == "box"]
    bounds = pygame.Rect(0, 0, gui.WIDTH, gui.HEIGHT)
    for mark in marks:
        assert bounds.contains(mark.rect), mark
        for box in boxes:
            assert box.inflate(-8, -4).contains(mark.rect) or \
                not box.colliderect(mark.rect), (mark, box)
    for one, two in combinations(marks, 2):
        assert not one.rect.colliderect(two.rect), (one, two)
    for a, b in combinations(boxes, 2):
        assert not a.colliderect(b), (a, b)
    return [d.text for d in marks if d.kind == "text"]

#
# Pure helpers
#

@pytest.mark.parametrize("mouse, point", [
    ((36, 36), (0, 0)),
    ((638, 638), (8, 8)),
    ((337, 337), (4, 4)),
    ((35, 300), None),
    ((639, 300), None),
    ((337, 35), None),
    ((337, 639), None),
    ((-1, -1), None),
])
def test_point_at_finds_the_point_under_the_mouse(
        mouse: tuple[int, int], point: tuple[int, int] | None) -> None:
    """Check the corners, the centre and each side just off the board"""
    assert point_at(mouse, BOARD, 9) == point

@pytest.mark.parametrize("size", [6, 9, 19, 30])
def test_every_point_is_found_at_its_own_centre(size: int) -> None:
    """Check hover and drawing agree on every point of every board size"""
    for r in range(size):
        for c in range(size):
            x, y = center(BOARD, size, (r, c))
            assert point_at((round(x), round(y)), BOARD, size) == (r, c)

@pytest.mark.parametrize("size, total", [
    (6, 0), (7, 5), (8, 4), (9, 5), (13, 5), (15, 9), (19, 9), (30, 4)])
def test_star_points_sit_on_the_board(size: int, total: int) -> None:
    """Check each board gets its marked points, all distinct and on it"""
    found = star_points(size)
    assert len(set(found)) == len(found) == total
    assert all(0 <= r < size and 0 <= c < size for r, c in found)

def test_points_says_point_only_for_one() -> None:
    """Check the score words agree with the number"""
    assert [points(n) for n in (0, 1, 2, 900)] == [
        "0 points", "1 point", "2 points", "900 points"]

@pytest.mark.parametrize("result, moves, headline, why", [
    (MatchResult(EndReason.PASSES, (2,), {1: 38, 2: 43}), 86,
     "White wins", "By 5 points. Every player passed after 86 moves."),
    (MatchResult(EndReason.MOVE_LIMIT, (1,), {1: 10, 2: 9, 3: 2}), 108,
     "Black wins",
     "By 1 point. The move limit was reached after 108 moves."),
    (MatchResult(EndReason.PASSES, (1, 2), {1: 0, 2: 0}), 2,
     "It's a tie", "Black and White share the top score. Every player "
     "passed after 2 moves."),
    (MatchResult(EndReason.PASSES, (1, 3, 4), {1: 5, 2: 1, 3: 5, 4: 5}),
     9, "It's a tie", "Black, Red and Blue share the top score. Every "
     "player passed after 9 moves."),
    (MatchResult(EndReason.ABORTED, (), {1: 3, 2: 1}), 4,
     "You left the match", "The match was left after 4 moves. No winner."),
])
def test_summary_names_the_winners_and_the_reason(
        result: MatchResult, moves: int, headline: str, why: str) -> None:
    """Check each ending is told in words: wins, ties, limit and leaving"""
    assert summary(result, moves) == (headline, why)

def test_colours_keep_three_to_one() -> None:
    """Check WCAG's 3:1 for controls: a chosen option against a plain one
    and the backdrop, a plain button's border, and the stones on the wood;
    Red and Blue also against Black's stones"""
    assert round(contrast((0, 0, 0), (255, 255, 255))) == 21
    plain_fill, plain_edge, _ = gui.STYLES["plain"]
    chosen_fill, _, chosen_ink = gui.STYLES["chosen"]
    assert contrast(chosen_fill, plain_fill) >= 3
    assert contrast(chosen_fill, gui.BACKDROP) >= 3
    assert contrast(plain_edge, gui.BACKDROP) >= 3
    assert contrast(chosen_ink, chosen_fill) >= 4.5
    black, _, red, blue = gui.STONES
    assert min(contrast(stone, gui.WOOD) for stone in (black, red, blue)) >= 3
    assert min(contrast(stone, black) for stone in (red, blue)) >= 3

#
# Starting and stopping
#

def test_regression_constructor_returns_and_the_loop_is_separate() -> None:
    """Check the constructor returns; the old one ran the loop forever"""
    window = GoGUI()
    assert window.screen is Screen.MENU
    post(pygame.QUIT)
    window.loop()
    assert not window.running

def test_run_opens_the_menu_and_returns_when_the_window_closes() -> None:
    """Check closing the window returns from run, with pygame shut down"""
    pygame.display.init()
    post(pygame.QUIT)
    gui.run()
    assert not pygame.display.get_init()

def test_run_with_a_config_starts_that_match(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check run(config) skips the menu and starts the match"""
    windows: list[GoGUI] = []

    def remember(window: GoGUI) -> None:
        windows.append(window)

    monkeypatch.setattr(GoGUI, "loop", remember)
    config = GameConfig(9, False, ("human", "random"))
    gui.run(config)
    assert windows[0].screen is Screen.PLAYING
    assert windows[0].match.config == config

#
# Menu and setup
#

def test_menu_offers_play_watch_bots_and_quit() -> None:
    """Check the menu's buttons, and that Quit ends the loop"""
    window = GoGUI()
    window.frame()
    assert [b.label for b in window.buttons()] == ["Play", "Watch bots",
                                                   "Quit"]
    press(window, "Quit")
    assert not window.running

def test_the_menu_says_what_each_button_does() -> None:
    """Check the menu draws its title, its introduction, a hint beside each
    button and the version"""
    window = GoGUI()
    assert {"Go Python", "The board game Go for 2 to 4 players. Play people "
            "or bots, or watch the bots play each other.", *gui.MENU_HINTS,
            f"Version {__version__}"} <= set(texts(window))

def test_setup_explains_every_choice() -> None:
    """Check setup draws its title, its introduction and the help for the
    size, the ko rule and the seats, for a game and for watching bots"""
    window = GoGUI()
    press(window, "Play")
    assert {"New game", "The defaults are ready: press Start game, or "
            "change anything first.", "New to Go?", gui.HOW_TO_PLAY,
            "Board size", "Lines on each side. 9 × 9 is quick; 19 × 19 is "
            "the classic board.", "Ko rule", "Simple ko: no move may bring "
            "back the board as it was one move ago. Superko: no move may "
            "bring back any earlier board.", "Players",
            gui.SEAT_HELP} <= set(texts(window))
    press(window, "Back")
    press(window, "Watch bots")
    assert {"Watch bots", "Every seat is a bot. Press Start watching, then "
            "sit back.", "Start watching"} <= set(texts(window))

def test_buttons_change_shade_under_the_mouse() -> None:
    """Check the hover shade shows on a dark and on a light button"""
    window = GoGUI()
    play, watch = button(window, "Play"), button(window, "Watch bots")
    move(window, (5, 5))
    dark, light = fill(play), fill(watch)
    assert dark == gui.INK and light == gui.CARD
    move(window, play.center)
    assert contrast(fill(play), dark) >= 1.5
    move(window, watch.center)
    assert contrast(fill(watch), light) >= 1.25 and fill(play) == dark

def test_play_starts_with_the_defaults_in_one_click() -> None:
    """Check Play opens setup on the defaults and Start begins at once"""
    window = GoGUI()
    press(window, "Play")
    assert window.screen is Screen.SETUP
    assert window.config == GameConfig()
    press(window, "Start game")
    assert window.screen is Screen.PLAYING
    assert window.match.config == GameConfig()
    assert window.match.state is MatchState.HUMAN_TURN

def test_watch_bots_presets_bot_seats_and_plays_to_the_end() -> None:
    """Check Watch bots seats only bots, who then play a whole match"""
    random.seed(3)
    window = GoGUI()
    press(window, "Watch bots")
    assert "human" not in window.config.seats
    press(window, "Start watching")
    assert window.match.state is MatchState.BOT_TURN
    for _ in range(1000):
        if window.screen is Screen.GAME_OVER:
            break
        window.frame()
    result = window.match.result
    assert window.screen is Screen.GAME_OVER and result is not None
    assert result.reason in (EndReason.PASSES, EndReason.MOVE_LIMIT)

def test_setup_changes_every_setting() -> None:
    """Check size, ko rule, player count and seats all reach the match"""
    window = GoGUI()
    press(window, "Play")
    press(window, "13 × 13")
    press(window, "Superko")
    press(window, "4 players")
    press(window, "Human", 1)
    press(window, "Random bot", 2)
    assert window.config == GameConfig(
        13, True, ("human", "human", "random", "smart"))
    press(window, "−")
    assert window.config.size == 12
    press(window, "+")
    press(window, "+")
    press(window, "3 players")
    press(window, "Simple ko")
    press(window, "Start game")
    assert window.match.config == GameConfig(
        14, False, ("human", "human", "random"))

def test_setup_marks_the_chosen_options() -> None:
    """Check exactly the current choices are filled gold"""
    window = GoGUI()
    press(window, "Play")
    press(window, "3 players")
    move(window, (5, 5))
    chosen = [b.label for b in window.buttons() if fill(b.rect) == gui.GOLD]
    assert chosen == ["19 × 19", "Simple ko", "3 players", "Human",
                      "Smart bot", "Smart bot"]

def test_setup_shows_the_gameconfig_message_under_the_size() -> None:
    """Check a refused size shows GameConfig's words, in red, just under
    the size row, and changes nothing"""
    window = GoGUI()
    press(window, "Play")
    press(window, "19 × 19")
    for _ in range(11):
        press(window, "+")
    assert window.config.size == 30 and window.note == ""
    press(window, "+")
    assert window.config.size == 30
    assert window.note == "Size must be a whole number from 6 to 30."
    assert window.note in assert_tidy(window)
    message = next(d.rect for d in window.draw() if d.text == window.note)
    gap = message.top - button(window, "+").bottom
    assert 0 <= gap <= 16 and count(message, gui.ERROR) > 50
    press(window, "9 × 9")
    assert window.note == ""
    for _ in range(4):
        press(window, "−")
    assert window.config.size == 6
    assert window.note.startswith("Size must be")

def test_setup_shows_the_size_as_plain_text() -> None:
    """Check the size between − and + is plain text on the backdrop, with
    no box that would make it look like a button"""
    window = GoGUI()
    press(window, "Play")
    press(window, "13 × 13")
    press(window, "+")
    drawn = window.draw()
    size = next(d.rect for d in drawn if d.text == "14 × 14")
    assert button(window, "−").right < size.left
    assert size.right < button(window, "+").left
    assert not [d for d in drawn if d.kind == "box" and
                d.rect.colliderect(size)]
    assert pixel((size.left - 4, size.centery)) == gui.BACKDROP

def test_setup_previews_the_board_size() -> None:
    """Check the setup screen draws an empty board with the chosen number
    of lines, counted along a row of its pixels"""
    def lines(window: GoGUI) -> int:
        wood = next(d.rect for d in window.draw() if d.kind == "box")
        grid = wood.inflate(-2 * gui.PAD, -2 * gui.PAD)
        y = grid.y + grid.height / window.config.size
        dark = [sum(pixel((x, y))) < 100
                for x in range(grid.left, grid.right)]
        return sum(1 for a, b in pairwise([False, *dark]) if b and not a)

    window = GoGUI()
    press(window, "Play")
    press(window, "9 × 9")
    assert lines(window) == 9
    press(window, "+")
    assert lines(window) == 10

def test_setup_seats_show_each_players_stone() -> None:
    """Check each seat row has its player's stone in that player's colour"""
    window = GoGUI()
    press(window, "Play")
    press(window, "4 players")
    stones = [d for d in window.draw() if d.kind == "stone"]
    assert [d.text for d in stones] == ["Black", "White", "Red", "Blue"]
    assert [pixel(d.rect.center) for d in stones] == list(gui.STONES)

def test_back_and_escape_return_to_the_menu() -> None:
    """Check Back and Esc leave setup, and Esc on the menu does nothing"""
    window = GoGUI()
    press(window, "Play")
    press(window, "Back")
    assert window.screen is Screen.MENU
    press(window, "Play")
    escape(window)
    assert window.screen is Screen.MENU
    escape(window)
    assert window.screen is Screen.MENU and window.running

#
# Clicks
#

def test_two_clicks_in_one_frame_play_one_stone() -> None:
    """Check that the second click of a frame does not replay the first move"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    x, y = (round(v) for v in spot(window, (2, 2)))
    for _ in range(2):
        post(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)
        post(pygame.MOUSEBUTTONUP, pos=(x, y), button=1)
    window.frame()
    assert window.match.game.piece_at((2, 2)) == 1
    assert window.match.game.turn == 2
    assert window.note == "That point already has a stone."

def test_only_the_left_button_plays() -> None:
    """Check right, middle and wheel clicks, and a press of one button
    released with another, place no stone"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    x, y = (round(v) for v in spot(window, (2, 2)))
    for down, up in [(2, 2), (3, 3), (4, 4), (5, 5), (3, 1), (1, 3)]:
        post(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=down)
        post(pygame.MOUSEBUTTONUP, pos=(x, y), button=up)
    window.frame()
    assert window.match.moves == 0

def double_click(window: GoGUI, pos: tuple[float, float], frames: int,
                 clock: list[int]) -> None:
    """Double-clicks the way a person does: press and release, then again
    33 ms per frame later, the time at 30 frames a second"""
    x, y = round(pos[0]), round(pos[1])
    clock[0] += 1000
    for _ in range(2):
        post(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)
        post(pygame.MOUSEBUTTONUP, pos=(x, y), button=1)
        window.frame()
        for _ in range(frames):
            clock[0] += 33
            window.frame()

@pytest.mark.parametrize("frames", [0, 3])
def test_regression_a_double_click_never_reaches_the_next_screen(
        frames: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check the second click of a double-click lands on nothing: it used
    to leave a match just started, pass at once after Play again, and seat
    a Human after Watch bots"""
    clock = [10 ** 6]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: clock[0])
    monkeypatch.setattr(gui, "DOUBLE_CLICK_MS", 500)
    window = GoGUI()
    double_click(window, button(window, "Watch bots").center, frames, clock)
    assert window.screen is Screen.SETUP and window.config == gui.WATCH
    clock[0] += 1000
    press(window, "Back")
    double_click(window, button(window, "Play").center, frames, clock)
    assert window.screen is Screen.SETUP and window.config == GameConfig()
    double_click(window, button(window, "Start game").center, frames, clock)
    assert window.screen is Screen.PLAYING and window.match.moves == 0
    assert gui.LEAVE_ASK not in texts(window)
    leave(window)
    double_click(window, button(window, "Play again").center, frames, clock)
    assert window.screen is Screen.PLAYING and window.match.moves == 0

@pytest.mark.parametrize("frames", [0, 3])
def test_regression_a_double_click_plays_once(
        frames: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a double-click on the board places one stone with no message,
    and one on Pass passes once, for White only: its second half used to
    pass for Black too and end the match"""
    clock = [10 ** 6]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: clock[0])
    monkeypatch.setattr(gui, "DOUBLE_CLICK_MS", 500)
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    double_click(window, spot(window, (4, 4)), frames, clock)
    assert window.match.moves == 1 and window.note == ""
    double_click(window, button(window, "Pass").center, frames, clock)
    assert window.screen is Screen.PLAYING and window.match.moves == 2
    assert window.match.game.turn == 1
    assert texts(window).count("Passed") == 1
    assert box_around(window, "Passed") == box_around(window, "White")

def test_a_quick_reply_to_a_bot_counts(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a click 100 ms after a bot's move plays: only a person's own
    move starts the double-click pause"""
    clock = [10 ** 6]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: clock[0])
    monkeypatch.setattr(gui, "DOUBLE_CLICK_MS", 500)
    window = GoGUI(GameConfig(9, False, ("random", "human")))
    clock[0] += 1000
    window.frame()
    assert window.match.moves == 1
    clock[0] += 100
    point = next((r, c) for r in range(9) for c in range(9)
                 if window.match.game.piece_at((r, c)) is None)
    click(window, spot(window, point))
    assert window.match.game.piece_at(point) == 2

def test_regression_a_drag_between_targets_does_nothing() -> None:
    """Check a press on one thing released on another acts on neither: a
    press on the board released on Leave match used to leave"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    board = spot(window, (4, 4))
    targets = [board, button(window, "Leave match (Esc)").center,
               button(window, "Pass").center, board]
    for start, end in pairwise(targets):
        post(pygame.MOUSEBUTTONDOWN, pos=start, button=1)
        post(pygame.MOUSEBUTTONUP, pos=end, button=1)
        window.frame()
    assert window.screen is Screen.PLAYING and window.match.moves == 0
    assert window.note == "" and gui.LEAVE_ASK not in texts(window)

def test_one_press_makes_one_click() -> None:
    """Check a release with no press of its own, as when a press outside the
    window is released over Pass, does not pass again"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    press(window, "Pass")
    post(pygame.MOUSEBUTTONUP, pos=button(window, "Pass").center, button=1)
    window.frame()
    assert window.screen is Screen.PLAYING and window.match.game.turn == 2

#
# Play
#

def test_stones_show_in_their_players_colours() -> None:
    """Check each played stone is drawn at its point in its colour, and
    the last one carries a ring: light on dark stones, dark on White"""
    window = GoGUI(GameConfig(9, False, ("human",) * 4))
    window.frame()
    played = [(2, 2), (2, 6), (6, 2), (6, 6)]
    assert [on_point(window, point) for point in played] == [gui.WOOD] * 4
    for i, point in enumerate(played):
        click(window, spot(window, point))
        x, y = spot(window, point)
        ring = pixel((x + BOARD.width / 9 * 0.17, y))
        assert ring == (gui.GRID if i == 1 else gui.CARD), ring
        if i:
            x, y = spot(window, played[i - 1])
            assert pixel((x + BOARD.width / 9 * 0.17, y)) == \
                gui.STONES[i - 1]
    assert [on_point(window, point) for point in played] == \
        list(gui.STONES)

@pytest.mark.parametrize("size", [6, 9])
def test_grid_lines_are_thin_on_small_boards(size: int) -> None:
    """Check a line of a small board is one pixel wide, read across it
    halfway between two points"""
    window = GoGUI(GameConfig(size, False, ("human", "human")))
    window.frame()
    x, y = spot(window, (1, 1))
    y += BOARD.width / size / 2
    across = [sum(pixel((col, y))) < 100
              for col in range(int(x) - 8, int(x) + 9)]
    assert sum(across) == 1, across

def test_star_points_are_drawn() -> None:
    """Check a 9 x 9 board marks its star points and only them"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    window.frame()
    for r, c in [(2, 2), (2, 6), (4, 4), (6, 2), (6, 6), (3, 3)]:
        x, y = spot(window, (r, c))
        dark = sum(pixel((x + 3, y + 3))) < 100
        assert dark == ((r, c) in star_points(9)), (r, c)

def test_hover_shows_only_on_legal_points() -> None:
    """Check the preview shows on an empty legal point, in the colour of
    the player to move, and nowhere else"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    move(window, spot(window, (4, 4)))
    assert window.hover() == (4, 4)
    assert sum(on_point(window, (4, 4))) < sum(gui.WOOD) - 100
    click(window, spot(window, (4, 4)))
    assert window.hover() is None
    move(window, spot(window, (4, 5)))
    assert window.hover() == (4, 5)
    white = on_point(window, (4, 5))
    assert all(a > b for a, b in zip(white, gui.WOOD, strict=True)), white
    for pos in [(8, 8), (0, 1), (8, 7), (1, 0)]:
        click(window, spot(window, pos))
    move(window, spot(window, (0, 0)))
    assert window.hover() is None and on_point(window, (0, 0)) == gui.WOOD
    click(window, spot(window, (0, 0)))
    assert window.match.game.piece_at((0, 0)) is None
    assert window.note.startswith("Not allowed")
    move(window, (100, 100))
    assert window.hover() is None

def test_mouse_leaving_the_window_clears_the_hover() -> None:
    """Check no preview stays behind once the mouse leaves the window"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    move(window, spot(window, (4, 4)))
    post(pygame.WINDOWLEAVE)
    window.frame()
    assert window.hover() is None and on_point(window, (4, 4)) == gui.WOOD

def test_the_sidebar_shows_whose_turn_it_is() -> None:
    """Check the headline, the mover's stone beside it, and the mover's row
    outlined in ink with "To play", the others plain"""
    window = GoGUI(GameConfig(9, False, ("human", "human", "human")))
    for name, turn in (("Black", 0), ("White", 1)):
        assert f"{name} to play" in texts(window)
        stones = [d for d in window.draw() if d.kind == "stone"]
        assert [d.text for d in stones] == [name, "Black", "White", "Red"]
        assert pixel(stones[0].rect.center) == gui.STONES[turn]
        row = box_around(window, "To play")
        assert edge(row) == gui.INK and row.collidepoint(stones[turn + 1]
                                                         .rect.center)
        other = box_around(window, ["White", "Black"][turn])
        assert edge(other) == gui.EDGE
        press(window, "Pass")
    assert texts(window).count("Passed") == 2

def test_the_sidebar_states_the_facts_of_the_match() -> None:
    """Check the details count the moves and name the size and the ko rule,
    each row names who sits there, and the captions explain area and Pass"""
    window = GoGUI(GameConfig(13, True, ("human", "smart")))
    click(window, spot(window, (3, 3)))
    assert window.match.moves == 2
    assert {"13 × 13 board · superko · 2 of at most 507 moves played",
            "Area: your stones plus the empty points only your stones "
            "surround. One stone alone claims the whole empty board, so "
            "early numbers swing.", "Pass skips your turn. When every "
            "player passes in a row, the game ends and the most area "
            "wins."} <= set(texts(window))
    assert box_around(window, "Human") == box_around(window, "Black")
    assert box_around(window, "Smart bot") == box_around(window, "White")

def test_the_result_shows_the_winners_stone() -> None:
    """Check a single winner's stone is drawn beside the headline in their
    colour, and the caption says what Play again does"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    press(window, "Pass")
    click(window, spot(window, (4, 4)))
    press(window, "Pass")
    press(window, "Pass")
    drawn = window.draw()
    stones = [d.rect for d in drawn if d.kind == "stone"]
    headline = next(d.rect for d in drawn if d.text == "White wins")
    assert [d.text for d in drawn if d.kind == "stone"] == [
        "White", "Black", "White"]
    assert pixel(stones[0].center) == gui.STONES[1]
    assert stones[0].right < headline.left and \
        abs(stones[0].centery - headline.centery) <= 2
    assert "Play again keeps the same board and players." in texts(window)

def test_stones_on_the_board_cast_a_shadow() -> None:
    """Check a stone played on the board has its shadow on the wood"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    x, y = spot(window, (4, 4))
    around = pygame.Rect(x - 40, y - 40, 80, 80)
    window.frame()
    assert count(around, gui.SHADOW) == 0
    click(window, (x, y))
    assert count(around, gui.SHADOW) > 100

def test_refusals_show_in_red() -> None:
    """Check a refused click is explained in red in the status card"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    card = box_around(window, "Black to play")
    assert count(card, gui.ERROR) == 0
    click(window, spot(window, (4, 4)))
    click(window, spot(window, (4, 4)))
    assert window.note == "That point already has a stone."
    assert box_around(window, window.note) == card
    assert count(card, gui.ERROR) > 100

def test_pass_and_every_player_passing_end_the_game() -> None:
    """Check Pass, the result after all pass, Play again and Menu"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    click(window, spot(window, (4, 4)))
    press(window, "Pass")
    assert window.match.game.turn == 1
    assert "Passed" in assert_tidy(window)
    press(window, "Pass")
    result = window.match.result
    assert window.screen is Screen.GAME_OVER and result is not None
    assert result.reason is EndReason.PASSES and result.winners == (1,)
    assert result.scores == {1: 81, 2: 0}
    assert "Black wins" in assert_tidy(window)
    assert edge(box_around(window, "Winner")) == gui.GOLD
    press(window, "Play again")
    assert window.screen is Screen.PLAYING and window.match.moves == 0
    assert window.match.config == GameConfig(9, False, ("human", "human"))
    press(window, "Leave match (Esc)")
    press(window, "Leave match (Esc)")
    assert window.match.result is not None
    assert window.match.result.reason is EndReason.ABORTED
    assert "You left the match" in assert_tidy(window)
    press(window, "Menu")
    assert window.screen is Screen.MENU

def test_a_stone_clears_the_run_of_passes() -> None:
    """Check the rows stop showing passes once someone plays a stone"""
    window = GoGUI(GameConfig(9, False, ("human", "human", "human")))
    press(window, "Pass")
    press(window, "Pass")
    assert assert_tidy(window).count("Passed") == 2
    click(window, spot(window, (4, 4)))
    assert "Passed" not in assert_tidy(window)
    assert window.screen is Screen.PLAYING

def test_escape_leaves_the_match_through_abort_when_asked_twice() -> None:
    """Check the first Esc asks, in red, and the second leaves with no
    winner; Esc on the result then goes home"""
    window = GoGUI(GameConfig(9, False, ("human", "smart")))
    click(window, spot(window, (2, 2)))
    window.frame()
    assert window.match.moves == 2
    card = box_around(window, "Black to play")
    escape(window)
    assert window.screen is Screen.PLAYING and window.match.result is None
    assert gui.LEAVE_ASK in assert_tidy(window)
    assert count(card, gui.ERROR) > 100
    # The question takes two lines: the second is drawn below the first
    ask = next(d.rect for d in window.draw() if d.text == gui.LEAVE_ASK)
    second = pygame.Rect(ask.x, ask.centery, ask.width, ask.height // 2)
    assert ask.height > 30 and count(second, gui.ERROR) > 50
    escape(window)
    result = window.match.result
    assert window.screen is Screen.GAME_OVER and result is not None
    assert result.reason is EndReason.ABORTED and result.winners == ()
    escape(window)
    assert window.screen is Screen.MENU

def test_anything_else_keeps_the_match_going() -> None:
    """Check a click or another key between two asks cancels leaving, and
    the Leave button asks the same way as Esc"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    escape(window)
    click(window, spot(window, (4, 4)))
    assert gui.LEAVE_ASK not in texts(window)
    escape(window)
    key(window, pygame.K_a)
    escape(window)
    assert window.screen is Screen.PLAYING
    assert gui.LEAVE_ASK in texts(window)
    press(window, "Leave match (Esc)")
    assert window.screen is Screen.GAME_OVER

def test_a_bot_move_keeps_the_question_to_leave() -> None:
    """Check bots moving between the two asks does not cancel leaving"""
    window = GoGUI(GameConfig(9, False, ("smart", "random")))
    escape(window)
    window.frame()
    window.frame()
    assert window.match.moves >= 2 and gui.LEAVE_ASK in texts(window)
    escape(window)
    assert window.screen is Screen.GAME_OVER

def test_bots_wait_their_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a bot waits BOT_DELAY_MS before it moves, with Pass dimmed"""
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 10 ** 6)
    window = GoGUI(GameConfig(9, False, ("random", "human")))
    move(window, spot(window, (4, 4)))
    assert window.match.moves == 0 and window.hover() is None
    assert "Random bot is choosing a move…" in assert_tidy(window)
    assert fill(button(window, "Pass")) == gui.EDGE
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 0)
    window.frame()
    assert window.match.moves == 1
    assert window.match.state is MatchState.HUMAN_TURN
    assert "Click a point on the board to place a stone." in \
        assert_tidy(window)
    move(window, (5, 5))
    assert fill(button(window, "Pass")) == gui.INK

@pytest.mark.parametrize("act", ["board", "Pass"])
def test_clicks_on_a_bots_turn_say_why_nothing_happens(
        act: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a click on the board or on Pass during a bot's turn is
    explained, and the bot's move clears the explanation"""
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 10 ** 6)
    window = GoGUI(GameConfig(9, False, ("random", "human")))
    if act == "board":
        click(window, spot(window, (4, 4)))
    else:
        press(window, "Pass")
    assert window.match.moves == 0
    assert window.note == "Wait: Black is a bot and moves by itself."
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 0)
    window.frame()
    assert window.match.moves == 1 and window.note == ""

def test_regression_superko_config_starts() -> None:
    """Check a superko match starts; --super-ko on its own used to raise"""
    window = GoGUI(GameConfig(9, True, ("human", "human")))
    click(window, spot(window, (4, 4)))
    assert window.match.config.superko
    assert window.match.game.piece_at((4, 4)) == 1

@pytest.mark.parametrize("players", [2, 3, 4])
def test_regression_every_seat_count_draws(players: int) -> None:
    """Check 2 to 4 players all draw; over 8 overran the old colour table"""
    window = GoGUI(GameConfig(9, False, ("human",) * players))
    for i in range(players):
        click(window, spot(window, (0, 2 * i)))
    assert [on_point(window, (0, 2 * i)) for i in range(players)] == \
        list(gui.STONES[:players])
    leave(window)
    window.frame()
    assert window.screen is Screen.GAME_OVER

#
# Layout: every text fits its box, at every size and ending
#

def letter_gaps(window: GoGUI, words: str) -> list[int]:
    """Draws once and returns the widths of the blank columns between the
    letters of a text, left to right, word spaces included"""
    rect = next(d.rect for d in window.draw() if d.text == words)
    inked = [any(sum(pixel((x, y))) < 600 for y in range(rect.top,
                                                            rect.bottom))
             for x in range(rect.left, rect.right)]
    gaps, blank = [], 0
    for ink in inked:
        if ink and blank:
            gaps.append(blank)
        blank = 0 if ink else blank + 1
    return gaps

def test_regression_letters_sit_evenly_apart() -> None:
    """Check the gaps between the letters of two button labels differ by at
    most a pixel; pygame.font drew "Super ko", and freetype's kerning
    "Watch bot s" too"""
    window = GoGUI()
    bots = letter_gaps(window, "Watch bots")[-3:]
    assert max(bots) - min(bots) <= 1, bots
    press(window, "Play")
    superko = letter_gaps(window, "Superko")
    assert max(superko) - min(superko) <= 1, superko

def test_menu_and_setup_layouts_are_tidy() -> None:
    """Check the menu, and setup with 2 and 4 players and only bots"""
    window = GoGUI()
    assert_tidy(window)
    press(window, "Play")
    assert_tidy(window)
    press(window, "4 players")
    assert "New to Go?" in assert_tidy(window)
    press(window, "Back")
    press(window, "Watch bots")
    assert "Watch bots" in assert_tidy(window)

@pytest.mark.parametrize("size", [6, 19, 30])
def test_the_longest_message_fits_at_every_board_size(size: int) -> None:
    """Check the not-allowed message and the question to leave fit beside a
    board of any size"""
    window = GoGUI(GameConfig(size, False, ("human",) * 4))
    for point in [(5, 5), (0, 1), (4, 4), (3, 3), (2, 2), (1, 0)]:
        click(window, spot(window, point))
    press(window, "Pass")
    press(window, "Pass")
    click(window, spot(window, (0, 0)))
    assert window.note.startswith("Not allowed")
    found = assert_tidy(window)
    assert window.note in found and found.count("Passed") == 2
    escape(window)
    assert gui.LEAVE_ASK in assert_tidy(window)

@pytest.mark.parametrize("players", [2, 3, 4])
def test_a_tie_of_every_player_fits_with_the_longest_reason(
        players: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check 2, 3 and 4 winners fit, with the reason as long as it gets:
    the move limit reached after 2700 moves on a 30 x 30 board"""
    window = GoGUI(GameConfig(30, False, ("human",) * players))
    for _ in range(players):
        press(window, "Pass")
    result = window.match.result
    assert result is not None and len(result.winners) == players
    assert "It's a tie" in assert_tidy(window)
    longest = MatchResult(EndReason.MOVE_LIMIT, result.winners,
                          result.scores)
    monkeypatch.setattr(gui, "summary",
                        lambda _, __: summary(longest, 2700))
    found = assert_tidy(window)
    assert found.count("Winner") == players
    assert summary(longest, 2700)[1] in found

def test_a_big_win_on_the_biggest_board_fits() -> None:
    """Check a three-digit area and its margin fit their rows"""
    window = GoGUI(GameConfig(30, False, ("human", "human")))
    click(window, spot(window, (15, 15)))
    found = assert_tidy(window)
    scores = [t for t in found if t == "Area" or t.isdigit()]
    assert scores == ["900", "Area", "0", "Area"]
    press(window, "Pass")
    press(window, "Pass")
    found = assert_tidy(window)
    assert "900" in found and "Black wins" in found

#
# Drawing and robustness
#

def draw_changes_nothing(window: GoGUI) -> bool:
    """Draws once and tells if the window and the game stayed the same"""
    before = dict(vars(window))
    board = window.match.game.frozengrid
    window.draw()
    return vars(window) == before and window.match.game.frozengrid == board

def test_drawing_changes_no_state() -> None:
    """Check drawing any screen leaves the window and the game as they were"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    click(window, spot(window, (3, 3)))
    click(window, spot(window, (3, 3)))
    move(window, spot(window, (4, 4)))
    assert window.note and window.hover() == (4, 4)
    assert draw_changes_nothing(window)
    escape(window)
    assert draw_changes_nothing(window)
    escape(window)
    assert draw_changes_nothing(window)
    press(window, "Menu")
    assert draw_changes_nothing(window)
    press(window, "Play")
    press(window, "+")
    assert draw_changes_nothing(window)

def test_no_click_or_key_crashes_any_screen(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check random clicks, drags, wheels and keys on every screen never
    raise"""
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 10 ** 6)
    rng = random.Random(2026)
    window = GoGUI()
    seen = set()
    keys = [pygame.K_ESCAPE, pygame.K_ESCAPE, pygame.K_ESCAPE,
            pygame.K_RETURN, pygame.K_SPACE, pygame.K_p, pygame.K_LEFT]
    for _ in range(3000):
        pos = (rng.randrange(-20, gui.WIDTH + 20),
               rng.randrange(-20, gui.HEIGHT + 20))
        roll = rng.random()
        if roll < 0.6:
            which = rng.choice([1, 1, 1, 2, 3, 4, 5])
            post(pygame.MOUSEBUTTONDOWN, pos=pos, button=which)
            post(pygame.MOUSEBUTTONUP, pos=pos, button=which)
        elif roll < 0.7:
            post(rng.choice([pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]),
                 pos=pos, button=1)
        elif roll < 0.8:
            post(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))
        elif roll < 0.9:
            post(pygame.KEYDOWN, key=rng.choice(keys))
        else:
            post(pygame.MOUSEWHEEL, x=0, y=rng.choice([-1, 1]))
        window.frame()
        seen.add(window.screen)
    assert seen == set(Screen)
