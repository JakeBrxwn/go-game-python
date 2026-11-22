"""Original board sounds synthesized as 16-bit, little-endian mono PCM."""

import sys
from array import array
from math import exp, sin, tau

RATE = 22050


def _wood(t: float, pitch: float) -> float:
    # The bright contact dies away before the body of the board.
    phase = tau * pitch * t
    return (.29 * exp(-39 * t) * sin(phase)
            + .17 * exp(-86 * t) * sin(2.73 * phase)
            + .13 * exp(-255 * t) * sin(8.14 * phase + .7 * sin(2.1 * phase)))


def _bell(t: float, pitch: float) -> float:
    phase = tau * pitch * t
    return (.24 * exp(-5.6 * t) * sin(phase)
            + .080 * exp(-9 * t) * sin(2.68 * phase)
            + .035 * exp(-14 * t) * sin(4.14 * phase))


def _horn(t: float, pitch: float) -> float:
    # Breath opens the tone slowly; the pair of horns settle into a fifth.
    breath = 1 - exp(-14 * t)
    phase = tau * pitch * t + .05 * sin(tau * 4.4 * t)
    return breath * (.18 * sin(phase) + .082 * sin(2 * phase)
                     + breath * (.055 * sin(3 * phase) + .027 * sin(4 * phase)))


def _drum(t: float, pitch: float) -> float:
    # A yielding drum skin drops in pitch just after each soft strike.
    phase = tau * (pitch * t + .9 * (1 - exp(-42 * t)))
    return (.33 * exp(-11 * t) * sin(phase)
            + .13 * exp(-19 * t) * sin(1.57 * phase)
            + .07 * exp(-60 * t) * sin(3.84 * phase))


# Each strike has an onset, pitch, duration and relative strength.
_SCORES = {
    "place": (_wood, ((0., 186., .15, 1.),)),
    "capture": (_bell, ((0., 784., .63, .93),)),
    "loss": (_bell, ((0., 392., .46, .88), (.17, 294., .61, .90))),
    "win": (_horn, ((0., 196., .55, .82), (.30, 247., .46, .86),
                    (.59, 294., .98, .91), (.66, 196., .90, .55))),
    "defeat": (_drum, ((0., 142., .44, .92), (.29, 106., .46, .95),
                       (.60, 142., .48, .50))),
}


def render(cue: str) -> bytes:
    """Render one cue from its score, including a short taper at each end."""
    voice, notes = _SCORES[cue]
    length = max(round(start * RATE) + round(duration * RATE)
                 for start, _, duration, _ in notes)
    mix = [0.] * length
    for start, pitch, duration, gain in notes:
        offset = round(start * RATE)
        frames = round(duration * RATE)
        release = RATE * (.18 if voice is _horn else .021)
        for i in range(frames):
            taper = min(1., i / 18, (frames - 1 - i) / release)
            mix[offset + i] += gain * taper * voice(i / RATE, pitch)
    pcm = array("h", (round(32767 * sample) for sample in mix))
    if sys.byteorder == "big":
        pcm.byteswap()
    return pcm.tobytes()
