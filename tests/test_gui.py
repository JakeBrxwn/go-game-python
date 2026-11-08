"""
Drives the real window with posted pygame events, on a display that shows
nothing: menu, setup, play and game over.
"""
import random
from collections.abc import Iterator
from typing import Any

import pygame
import pytest

from go_python import gui
from go_python.gui import (BOARD, GoGUI, Screen, center, point_at,
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
    rects = [button.rect for button in window._buttons()
             if button.label == label]
    click(window, rects[nth].center)

def spot(window: GoGUI, point: tuple[int, int]) -> tuple[float, float]:
    """Returns where a board point is drawn in the current match"""
    return center(BOARD, window._match.config.size, point)

def escape(window: GoGUI) -> None:
    """Presses Esc, then runs a frame"""
    post(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    window.frame()

#
# Pure helpers
#

@pytest.mark.parametrize("mouse, point", [
    ((298, 36), (0, 0)),
    ((900, 638), (8, 8)),
    ((600, 337), (4, 4)),
    ((297, 300), None),
    ((901, 300), None),
    ((600, 35), None),
    ((600, 639), None),
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

@pytest.mark.parametrize("result, moves, headline, why", [
    (MatchResult(EndReason.PASSES, (2,), {1: 38, 2: 43}), 86,
     "White wins", "By 5 points. Every player passed after 86 moves."),
    (MatchResult(EndReason.MOVE_LIMIT, (1,), {1: 10, 2: 9, 3: 2}), 108,
     "Black wins",
     "By 1 point. The move limit was reached after 108 moves."),
    (MatchResult(EndReason.PASSES, (1, 2), {1: 0, 2: 0}), 2,
     "Black and White tie", "Every player passed after 2 moves."),
    (MatchResult(EndReason.PASSES, (1, 3, 4), {1: 5, 2: 1, 3: 5, 4: 5}),
     9, "Black, Red and Blue tie", "Every player passed after 9 moves."),
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
    assert window._screen is Screen.MENU
    post(pygame.QUIT)
    window.loop()
    assert not window._running

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
    assert windows[0]._screen is Screen.PLAYING
    assert windows[0]._match.config == config

#
# Menu and setup
#

def test_menu_offers_play_watch_bots_and_quit() -> None:
    """Check the menu's buttons, and that Quit ends the loop"""
    window = GoGUI()
    window.frame()
    assert [b.label for b in window._buttons()] == ["Play", "Watch bots",
                                                    "Quit"]
    press(window, "Quit")
    assert not window._running

def test_play_starts_with_the_defaults_in_one_click() -> None:
    """Check Play opens setup on the defaults and Start begins at once"""
    window = GoGUI()
    press(window, "Play")
    assert window._screen is Screen.SETUP
    assert window._config == GameConfig()
    press(window, "Start game")
    assert window._screen is Screen.PLAYING
    assert window._match.config == GameConfig()
    assert window._match.state is MatchState.HUMAN_TURN

def test_watch_bots_presets_bot_seats_and_plays_to_the_end() -> None:
    """Check Watch bots seats only bots, who then play a whole match"""
    random.seed(3)
    window = GoGUI()
    press(window, "Watch bots")
    assert "human" not in window._config.seats
    press(window, "Start watching")
    assert window._match.state is MatchState.BOT_TURN
    for _ in range(1000):
        if window._screen is Screen.GAME_OVER:
            break
        window.frame()
    result = window._match.result
    assert window._screen is Screen.GAME_OVER and result is not None
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
    assert window._config == GameConfig(
        13, True, ("human", "human", "random", "smart"))
    press(window, "−")
    assert window._config.size == 12
    press(window, "+")
    press(window, "+")
    press(window, "3 players")
    press(window, "Simple ko")
    press(window, "Start game")
    assert window._match.config == GameConfig(
        14, False, ("human", "human", "random"))

def test_setup_shows_the_gameconfig_message_and_keeps_the_size() -> None:
    """Check a refused size shows GameConfig's words and changes nothing"""
    window = GoGUI()
    press(window, "Play")
    press(window, "19 × 19")
    for _ in range(11):
        press(window, "+")
    assert window._config.size == 30 and window._note == ""
    press(window, "+")
    assert window._config.size == 30
    assert window._note == "Size must be a whole number from 6 to 30."
    press(window, "9 × 9")
    assert window._note == ""
    for _ in range(4):
        press(window, "−")
    assert window._config.size == 6
    assert window._note.startswith("Size must be")

def test_back_and_escape_return_to_the_menu() -> None:
    """Check Back and Esc leave setup, and Esc on the menu does nothing"""
    window = GoGUI()
    press(window, "Play")
    press(window, "Back")
    assert window._screen is Screen.MENU
    press(window, "Play")
    escape(window)
    assert window._screen is Screen.MENU
    escape(window)
    assert window._screen is Screen.MENU and window._running

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
    assert window._match.game.piece_at((2, 2)) == 1
    assert window._match.game.turn == 2
    assert window._note == "That point already has a stone."

def test_only_the_left_button_plays() -> None:
    """Check right, middle and wheel clicks place no stone"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    x, y = (round(v) for v in spot(window, (2, 2)))
    for button in (2, 3, 4, 5):
        post(pygame.MOUSEBUTTONUP, pos=(x, y), button=button)
    post(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)
    window.frame()
    assert window._match.moves == 0

def test_hover_shows_only_on_legal_points() -> None:
    """Check the preview shows on an empty legal point and nowhere else"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    move(window, spot(window, (4, 4)))
    assert window._hover() == (4, 4)
    click(window, spot(window, (4, 4)))
    assert window._hover() is None
    for pos in [(8, 8), (0, 1), (8, 7), (1, 0)]:
        click(window, spot(window, pos))
    move(window, spot(window, (0, 0)))
    assert window._hover() is None
    click(window, spot(window, (0, 0)))
    assert window._match.game.piece_at((0, 0)) is None
    assert window._note.startswith("Not allowed")
    move(window, (100, 100))
    assert window._hover() is None

def test_mouse_leaving_the_window_clears_the_hover() -> None:
    """Check no preview stays behind once the mouse leaves the window"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    move(window, spot(window, (4, 4)))
    post(pygame.WINDOWLEAVE)
    window.frame()
    assert window._hover() is None

def test_pass_and_every_player_passing_end_the_game() -> None:
    """Check Pass, the result after all pass, Play again and Menu"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    click(window, spot(window, (4, 4)))
    press(window, "Pass")
    assert window._passed == {2} and window._match.game.turn == 1
    press(window, "Pass")
    result = window._match.result
    assert window._screen is Screen.GAME_OVER and result is not None
    assert result.reason is EndReason.PASSES and result.winners == (1,)
    assert result.scores == {1: 81, 2: 0}
    press(window, "Play again")
    assert window._screen is Screen.PLAYING and window._match.moves == 0
    assert window._match.config == GameConfig(9, False, ("human", "human"))
    press(window, "Leave match (Esc)")
    assert window._match.result is not None
    assert window._match.result.reason is EndReason.ABORTED
    press(window, "Menu")
    assert window._screen is Screen.MENU

def test_a_stone_clears_the_run_of_passes() -> None:
    """Check the cards stop showing passes once someone plays a stone"""
    window = GoGUI(GameConfig(9, False, ("human", "human", "human")))
    press(window, "Pass")
    press(window, "Pass")
    assert window._passed == {1, 2}
    click(window, spot(window, (4, 4)))
    assert window._passed == set()
    assert window._screen is Screen.PLAYING

def test_escape_leaves_the_match_through_abort() -> None:
    """Check Esc ends the match as left, with no winner, then goes home"""
    window = GoGUI(GameConfig(9, False, ("human", "smart")))
    click(window, spot(window, (2, 2)))
    window.frame()
    assert window._match.moves == 2
    escape(window)
    result = window._match.result
    assert window._screen is Screen.GAME_OVER and result is not None
    assert result.reason is EndReason.ABORTED and result.winners == ()
    escape(window)
    assert window._screen is Screen.MENU

def test_bots_wait_their_pause_and_clicks_meanwhile_get_a_message(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a bot waits BOT_DELAY_MS, and a person who clicks is told why"""
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 10 ** 6)
    window = GoGUI(GameConfig(9, False, ("random", "human")))
    move(window, spot(window, (4, 4)))
    assert window._match.moves == 0 and window._hover() is None
    click(window, spot(window, (4, 4)))
    assert window._match.game.piece_at((4, 4)) is None
    assert window._note == "Wait: Black is a bot and moves by itself."
    window._note = ""
    press(window, "Pass")
    assert window._note.startswith("Wait") and window._match.moves == 0
    monkeypatch.setattr(gui, "BOT_DELAY_MS", 0)
    window.frame()
    assert window._match.moves == 1 and window._note == ""
    assert window._match.state is MatchState.HUMAN_TURN

def test_regression_superko_config_starts() -> None:
    """Check a superko match starts; --super-ko on its own used to raise"""
    window = GoGUI(GameConfig(9, True, ("human", "human")))
    click(window, spot(window, (4, 4)))
    assert window._match.config.superko
    assert window._match.game.piece_at((4, 4)) == 1

@pytest.mark.parametrize("players", [2, 3, 4])
def test_regression_every_seat_count_draws(players: int) -> None:
    """Check 2 to 4 players all draw; over 8 overran the old colour table"""
    window = GoGUI(GameConfig(9, False, ("human",) * players))
    for i in range(players):
        click(window, spot(window, (0, 2 * i)))
    assert [window._match.game.piece_at((0, 2 * i))
            for i in range(players)] == list(range(1, players + 1))
    escape(window)
    window.frame()
    assert window._screen is Screen.GAME_OVER

#
# Drawing and robustness
#

def draw_changes_nothing(window: GoGUI) -> bool:
    """Draws once and tells if the window and the game stayed the same"""
    before = dict(vars(window))
    board = window._match.game.frozengrid
    window.draw()
    return vars(window) == before and window._match.game.frozengrid == board

def test_drawing_changes_no_state() -> None:
    """Check drawing every screen leaves the window and the game as they were"""
    window = GoGUI(GameConfig(9, False, ("human", "human")))
    click(window, spot(window, (3, 3)))
    click(window, spot(window, (3, 3)))
    move(window, spot(window, (4, 4)))
    assert window._note and window._hover() == (4, 4)
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
        seen.add(window._screen)
        window._running = True
    assert seen == set(Screen)
