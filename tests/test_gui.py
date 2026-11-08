"""
Drives the real window with posted pygame events, on a display that shows
nothing: menu, setup, play and game over.
"""
import random
from collections.abc import Iterator
from itertools import combinations
from typing import Any

import pygame
import pytest

from go_python import gui
from go_python.gui import (BOARD, GoGUI, Screen, center, point_at, points,
                           star_points, summary)
from go_python.match import EndReason, GameConfig, MatchResult, MatchState

@pytest.fixture(autouse=True)
def dummy_window(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Use the dummy SDL drivers, and run bots and frames without waiting"""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 0)
    monkeypatch.setattr(gui, "FPS", 0)
    yield
    pygame.quit()

#
# Helpers
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
    """Moves the mouse and clicks the left button there, then runs a frame"""
    x, y = round(pos[0]), round(pos[1])
    post(pygame.MOUSEMOTION, pos=(x, y), rel=(0, 0), buttons=(0, 0, 0))
    post(pygame.MOUSEBUTTONUP, pos=(x, y), button=1)
    window.frame()

def press(window: GoGUI, label: str, nth: int = 0) -> None:
    """Clicks the nth button with this label on the current screen"""
    rects = [button.rect for button in window.buttons()
             if button.label == label]
    click(window, rects[nth].center)

def spot(window: GoGUI, point: tuple[int, int]) -> tuple[float, float]:
    """Returns where a board point is drawn in the current match"""
    return center(BOARD, window.match.config.size, point)

def escape(window: GoGUI) -> None:
    """Presses Esc, then runs a frame"""
    post(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    window.frame()

def layout(window: GoGUI) -> tuple[list[tuple[str, pygame.Rect]],
                                   list[pygame.Rect]]:
    """
    Draws once and records what went where.

    Returns: Each text drawn with its rect, the stones beside it counted as
    text; and each box drawn: panels, buttons and the board's wood
    """
    texts: list[tuple[str, pygame.Rect]] = []
    boxes = [button.rect for button in window.buttons()]
    text, card = GoGUI._text, GoGUI._card
    board, stone = GoGUI._draw_board, GoGUI._draw_stone

    def spy_text(self: GoGUI, words: str, *args: Any,
                 **kwargs: Any) -> pygame.Rect:
        rect = text(self, words, *args, **kwargs)
        if words:
            texts.append((words, rect))
        return rect

    def spy_card(self: GoGUI, rect: pygame.Rect, *args: Any) -> None:
        boxes.append(rect)
        card(self, rect, *args)

    def spy_board(self: GoGUI, rect: pygame.Rect, size: int) -> None:
        boxes.append(rect.inflate(2 * gui.PAD, 2 * gui.PAD))
        board(self, rect, size)

    def spy_stone(self: GoGUI, pos: tuple[float, float], radius: float,
                  player: int, on_wood: bool = True) -> None:
        if not on_wood:
            texts.append((f"stone {player}", pygame.Rect(
                pos[0] - radius, pos[1] - radius, 2 * radius, 2 * radius)))
        stone(self, pos, radius, player, on_wood)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(GoGUI, "_text", spy_text)
        patch.setattr(GoGUI, "_card", spy_card)
        patch.setattr(GoGUI, "_draw_board", spy_board)
        patch.setattr(GoGUI, "_draw_stone", spy_stone)
        window.draw()
    return texts, boxes

def assert_tidy(window: GoGUI) -> list[str]:
    """
    Checks the screen's layout: every text inside the window, either clear
    of a box or inside it with room to spare, no two texts touching, and no
    two boxes overlapping.

    Returns: The texts drawn, for the caller to check
    """
    texts, boxes = layout(window)
    screen = pygame.Rect(0, 0, gui.WIDTH, gui.HEIGHT)
    for words, rect in texts:
        assert screen.contains(rect), words
        for box in boxes:
            assert box.inflate(-8, -4).contains(rect) or \
                not box.colliderect(rect), words
    for (one, a), (two, b) in combinations(texts, 2):
        assert not a.colliderect(b), (one, two)
    for a, b in combinations(boxes, 2):
        assert not a.colliderect(b), (a, b)
    return [words for words, _ in texts]

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

@pytest.mark.parametrize("size, count", [
    (6, 0), (7, 5), (8, 4), (9, 5), (13, 5), (15, 9), (19, 9), (30, 4)])
def test_star_points_sit_on_the_board(size: int, count: int) -> None:
    """Check each board gets its marked points, all distinct and on it"""
    points = star_points(size)
    assert len(set(points)) == len(points) == count
    assert all(0 <= r < size and 0 <= c < size for r, c in points)

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
     "Match left", "The match was left after 4 moves. No winner."),
])
def test_summary_names_the_winners_and_the_reason(
        result: MatchResult, moves: int, headline: str, why: str) -> None:
    """Check each ending is told in words: wins, ties, limit and leaving"""
    assert summary(result, moves) == (headline, why)

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
    """Check exactly the current choices are drawn as chosen"""
    window = GoGUI()
    press(window, "Play")
    press(window, "3 players")
    chosen = [b.label for b in window.buttons() if b.style == "chosen"]
    assert chosen == ["19 × 19", "Simple ko", "3 players", "Human",
                      "Smart bot", "Smart bot"]

def contrast(one: tuple[int, int, int], two: tuple[int, int, int]) -> float:
    """Returns the WCAG contrast ratio of two colours, from 1 to 21"""
    def luminance(color: tuple[int, int, int]) -> float:
        def linear(value: int) -> float:
            v = value / 255
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = map(linear, color)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    light, dark = sorted((luminance(one), luminance(two)), reverse=True)
    return (light + 0.05) / (dark + 0.05)

def test_chosen_options_stand_out_at_three_to_one() -> None:
    """Check a chosen option's fill against a plain one meets WCAG's 3:1
    for controls, and so does a plain button's border on the backdrop"""
    assert round(contrast((0, 0, 0), (255, 255, 255))) == 21
    plain_fill, plain_edge, _ = gui.STYLES["plain"]
    chosen_fill, _, chosen_ink = gui.STYLES["chosen"]
    assert contrast(chosen_fill, plain_fill) >= 3
    assert contrast(chosen_fill, gui.BACKDROP) >= 3
    assert contrast(plain_edge, gui.BACKDROP) >= 3
    assert contrast(chosen_ink, chosen_fill) >= 4.5

def test_setup_shows_the_gameconfig_message_and_keeps_the_size() -> None:
    """Check a refused size shows GameConfig's words and changes nothing"""
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
    press(window, "9 × 9")
    assert window.note == ""
    for _ in range(4):
        press(window, "−")
    assert window.config.size == 6
    assert window.note.startswith("Size must be")

def test_setup_previews_the_board_size(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check the setup screen draws an empty board of the chosen size"""
    sizes: list[int] = []
    draw_board = GoGUI._draw_board

    def spy(self: GoGUI, rect: pygame.Rect, size: int) -> None:
        sizes.append(size)
        draw_board(self, rect, size)

    window = GoGUI()
    press(window, "Play")
    monkeypatch.setattr(GoGUI, "_draw_board", spy)
    press(window, "9 × 9")
    press(window, "+")
    assert sizes == [9, 10]

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
# Play
#

def test_two_clicks_in_one_frame_play_one_stone() -> None:
    """Check that the second click of a frame does not replay the first move"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    x, y = (round(v) for v in spot(window, (2, 2)))
    post(pygame.MOUSEBUTTONUP, pos=(x, y), button=1)
    post(pygame.MOUSEBUTTONUP, pos=(x, y), button=1)
    window.frame()
    assert window.match.game.piece_at((2, 2)) == 1
    assert window.match.game.turn == 2
    assert window.note == "That point already has a stone."

def test_only_the_left_button_plays() -> None:
    """Check right, middle and wheel clicks place no stone"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    x, y = (round(v) for v in spot(window, (2, 2)))
    for button in (2, 3, 4, 5):
        post(pygame.MOUSEBUTTONUP, pos=(x, y), button=button)
    post(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)
    window.frame()
    assert window.match.moves == 0

def test_hover_shows_only_on_legal_points() -> None:
    """Check the preview shows on an empty legal point and nowhere else"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    move(window, spot(window, (4, 4)))
    assert window.hover() == (4, 4)
    click(window, spot(window, (4, 4)))
    assert window.hover() is None
    for pos in [(8, 8), (0, 1), (8, 7), (1, 0)]:
        click(window, spot(window, pos))
    move(window, spot(window, (0, 0)))
    assert window.hover() is None
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
    assert window.hover() is None

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
    press(window, "Play again")
    assert window.screen is Screen.PLAYING and window.match.moves == 0
    assert window.match.config == GameConfig(9, False, ("human", "human"))
    press(window, "Leave match (Esc)")
    assert window.match.result is not None
    assert window.match.result.reason is EndReason.ABORTED
    assert "Match left" in assert_tidy(window)
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

def test_escape_leaves_the_match_through_abort() -> None:
    """Check Esc ends the match as left, with no winner, then goes home"""
    window = GoGUI(GameConfig(9, False, ("human", "smart")))
    click(window, spot(window, (2, 2)))
    window.frame()
    assert window.match.moves == 2
    escape(window)
    result = window.match.result
    assert window.screen is Screen.GAME_OVER and result is not None
    assert result.reason is EndReason.ABORTED and result.winners == ()
    escape(window)
    assert window.screen is Screen.MENU

def test_bots_wait_their_pause_and_clicks_meanwhile_get_a_message(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a bot waits BOT_DELAY_MS, and a person who clicks is told why"""
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 10 ** 6)
    window = GoGUI(GameConfig(9, False, ("random", "human")))
    assert "Random bot is choosing a move…" in assert_tidy(window)
    move(window, spot(window, (4, 4)))
    assert window.match.moves == 0 and window.hover() is None
    click(window, spot(window, (4, 4)))
    assert window.match.game.piece_at((4, 4)) is None
    assert window.note == "Wait: Black is a bot and moves by itself."
    window.note = ""
    press(window, "Pass")
    assert window.note.startswith("Wait") and window.match.moves == 0
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 0)
    window.frame()
    assert window.match.moves == 1 and window.note == ""
    assert window.match.state is MatchState.HUMAN_TURN
    assert "Click a point on the board to place a stone." in \
        assert_tidy(window)

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
    assert [window.match.game.piece_at((0, 2 * i))
            for i in range(players)] == list(range(1, players + 1))
    escape(window)
    window.frame()
    assert window.screen is Screen.GAME_OVER

#
# Layout: every text fits its box, at every size and ending
#

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
    """Check the not-allowed message fits beside a board of any size"""
    window = GoGUI(GameConfig(size, False, ("human",) * 4))
    for point in [(5, 5), (0, 1), (4, 4), (3, 3), (2, 2), (1, 0)]:
        click(window, spot(window, point))
    press(window, "Pass")
    press(window, "Pass")
    click(window, spot(window, (0, 0)))
    assert window.note.startswith("Not allowed")
    texts = assert_tidy(window)
    assert window.note in texts and texts.count("Passed") == 2

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
    texts = assert_tidy(window)
    assert texts.count("Winner") == players
    assert summary(longest, 2700)[1] in texts

def test_a_big_win_on_the_biggest_board_fits() -> None:
    """Check a three-digit score and its margin fit their rows"""
    window = GoGUI(GameConfig(30, False, ("human", "human")))
    click(window, spot(window, (15, 15)))
    press(window, "Pass")
    press(window, "Pass")
    texts = assert_tidy(window)
    assert "900 points" in texts and "Black wins" in texts

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
    press(window, "Menu")
    assert draw_changes_nothing(window)
    press(window, "Play")
    press(window, "+")
    assert draw_changes_nothing(window)

def test_no_click_or_key_crashes_any_screen(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check random clicks, wheels and keys on every screen never raise"""
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 10 ** 6)
    rng = random.Random(2026)
    window = GoGUI()
    seen = set()
    keys = [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_p,
            pygame.K_q, pygame.K_LEFT]
    for _ in range(3000):
        pos = (rng.randrange(-20, gui.WIDTH + 20),
               rng.randrange(-20, gui.HEIGHT + 20))
        roll = rng.random()
        if roll < 0.6:
            post(pygame.MOUSEBUTTONUP, pos=pos, button=rng.choice(
                [1, 1, 1, 2, 3, 4, 5]))
        elif roll < 0.7:
            post(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)
        elif roll < 0.8:
            post(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))
        elif roll < 0.9:
            post(pygame.KEYDOWN, key=rng.choice(keys))
        else:
            post(pygame.MOUSEWHEEL, x=0, y=rng.choice([-1, 1]))
        window.frame()
        seen.add(window.screen)
        window.running = True
    assert seen == set(Screen)
