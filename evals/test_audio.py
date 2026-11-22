"""Measure the rendered cues in the time and frequency domains."""
from array import array
from math import cos, tau
from statistics import fmean
from struct import iter_unpack

import pytest

from go_python.voices import RATE, render


@pytest.fixture(scope="module")
def sounds() -> dict[str, array[int]]:
    return {name: array("h", (sample for sample, in iter_unpack("<h", render(name))))
            for name in ("place", "capture", "loss", "win", "defeat")}


def bell_pitch(samples: array[int], seconds: float) -> int:
    """Estimate the strongest bell partial in a 50 ms window with Goertzel."""
    start = round(RATE * seconds)
    frame = samples[start:start + RATE // 20]

    def energy(hz: int) -> float:
        coefficient = 2 * cos(tau * hz / RATE)
        previous = older = 0.
        for sample in frame:
            current = sample + coefficient * previous - older
            previous, older = current, previous
        return previous ** 2 + older ** 2 - coefficient * previous * older

    return max(range(120, 1600, 10), key=energy)


def test_headroom_and_clean_ends(sounds: dict[str, array[int]]) -> None:
    for name, samples in sounds.items():
        assert 0 < max(map(abs, samples)) < 32767, name
        assert max(abs(samples[0]), abs(samples[-1])) < 328, name


def test_wood_attack_and_horn_sustain(sounds: dict[str, array[int]]) -> None:
    wood = sounds["place"]
    peak = max(range(len(wood)), key=lambda i: abs(wood[i]))
    assert peak < .03 * RATE
    horn = sounds["win"]
    assert len(horn) > max(len(sounds[name]) for name in ("place", "capture", "loss"))
    middle = horn[len(horn) // 2:len(horn) * 3 // 4]
    assert fmean(map(abs, middle)) > .1 * max(map(abs, horn))


def test_bells_differ_in_register_and_direction(sounds: dict[str, array[int]]) -> None:
    first = bell_pitch(sounds["loss"], .04)
    later = bell_pitch(sounds["loss"], .30)
    assert later < .9 * first
    assert bell_pitch(sounds["capture"], .04) > 1.2 * first


def test_defeat_has_separate_drum_strikes(sounds: dict[str, array[int]]) -> None:
    drum = sounds["defeat"]
    width = RATE // 50
    energy = [fmean(map(abs, drum[i:i + width])) for i in range(0, len(drum), width)]
    # A second attack must rise clearly above the intervening decay.
    assert any(max(energy[i + 1:]) > 2 * energy[i] > 0
               and max(energy[:i]) > 2 * energy[i]
               for i in range(1, len(energy) - 1))
