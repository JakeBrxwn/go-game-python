"""Original board sounds for the game window."""
import wave
from functools import cache
from io import BytesIO

import pygame

from go_python.voices import RATE, render


@cache
def _wav(cue: str) -> bytes:
    # The WAV header lets SDL convert mono PCM to the open device's format.
    buffer = BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        output.writeframes(render(cue))
    return buffer.getvalue()


class SoundBank:
    """Load each cue once per window. A missing device leaves the game silent."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init()
            self._sounds = {
                cue: pygame.mixer.Sound(file=BytesIO(_wav(cue)))
                for cue in ("place", "capture", "loss", "win", "defeat")
            }
        except pygame.error:
            return

    def play(self, cue: str) -> None:
        if self._sounds:
            # Prioritize the latest event even when all channels are occupied.
            channel = pygame.mixer.find_channel(force=True)
            if channel is not None:
                channel.play(self._sounds[cue])

    def stop(self) -> None:
        for sound in self._sounds.values():
            sound.stop()
