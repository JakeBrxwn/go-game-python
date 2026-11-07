"""
Drives the real window with scripted events, on a display that shows nothing.
"""
import pygame
import pytest

from go_python.gui import GoGUI

def test_two_clicks_in_one_frame_play_one_stone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that the second click of a frame does not replay the first move"""
    windows: list[GoGUI] = []
    draw_window = GoGUI._draw_window

    def remember_window(window: GoGUI) -> None:
        windows.append(window)
        draw_window(window)

    click = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)
    frames = iter([[], [click, click], [pygame.event.Event(pygame.QUIT)]])

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr(GoGUI, "_draw_window", remember_window)
    monkeypatch.setattr(pygame.event, "get", lambda: next(frames))
    monkeypatch.setattr(pygame.mouse, "get_pos",
                        lambda: windows[0]._intersections[2][2])

    with pytest.raises(SystemExit):
        GoGUI(2, 9, False)

    assert windows[0].board.piece_at((2, 2)) == 1
    assert windows[0].board.turn == 2
