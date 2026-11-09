"""
Saves a picture of the game window mid-match, for the README, using the
installed package on SDL's dummy drivers. The same seed gives the same
picture.

    python scripts/screenshot.py go-python-screenshot.png
"""
import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from go_python import gui  # noqa: E402
from go_python.match import GameConfig  # noqa: E402

MOVES = 60

def main(path: str) -> None:
    """
    Lets two bots play MOVES moves on a 13x13 board, or to the end if they
    pass first, then saves the window.

    Args:
        path: Where to save the picture, as PNG
    """
    random.seed(7)
    gui.BOT_DELAY_MS = 0
    gui.FPS = 0
    window = gui.GoGUI(GameConfig(13, False, ("smart", "random")))
    while window.match.moves < MOVES and window.match.result is None:
        window.frame()
    surface = pygame.display.get_surface()
    assert surface is not None  # the window above made it
    pygame.image.save(surface, path)
    pygame.quit()

if __name__ == "__main__":
    main(sys.argv[1])
