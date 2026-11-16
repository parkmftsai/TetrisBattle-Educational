"""Regenerate copyright-independent, synthesized TetrisBattle effects.

Usage: python tools/generate_sfx.py
No dependencies beyond the Python standard library.
"""
import math
import random
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "TetrisBattle/assets/tetris sounds/sfx"
SAMPLE_RATE = 22050
random.seed(304)

# (duration, a list of (start, duration, start Hz, end Hz, amplitude), noise)
SOUNDS = {
    "move": (0.065, [(0, .060, 360, 400, .17)], 0),
    "rotate": (.105, [(0, .100, 420, 750, .23)], .015),
    "hard_drop": (.190, [(0, .185, 250, 67, .36)], .13),
    "hold": (.170, [(0, .075, 430, 440, .20), (.077, .088, 650, 670, .20)], 0),
    "lock": (.100, [(0, .092, 180, 110, .24)], .04),
    "line_clear": (.290, [(0, .10, 523, 523, .22), (.075, .10, 659, 659, .22), (.15, .135, 784, 784, .24)], .012),
    "tetris": (.530, [(0, .16, 523, 659, .24), (.12, .17, 659, 784, .25), (.26, .26, 784, 1046, .27)], .013),
    "combo": (.230, [(0, .12, 660, 750, .17), (.09, .135, 880, 1000, .21)], 0),
    "attack": (.190, [(0, .185, 220, 120, .29)], .09),
    "warning": (.350, [(0, .16, 780, 710, .23), (.18, .16, 780, 710, .23)], .005),
    "ko": (.530, [(0, .18, 440, 330, .24), (.15, .18, 300, 220, .28), (.30, .22, 170, 95, .30)], .07),
    "win": (.740, [(0, .18, 523, 523, .20), (.14, .19, 659, 659, .23), (.30, .20, 784, 784, .24), (.44, .28, 1046, 1046, .25)], 0),
    "lose": (.650, [(0, .23, 400, 320, .20), (.19, .23, 310, 230, .22), (.38, .25, 200, 100, .25)], .018),
    "pause": (.110, [(0, .103, 620, 450, .18)], 0),
    "menu": (.085, [(0, .075, 530, 680, .18)], 0),
    "soft_drop": (.06, [(0, .055, 230, 185, .09)], .01),
    "tspin": (.46, [(0, .16, 580, 900, .23), (.16, .22, 800, 1100, .23)], .03),
    "back_to_back": (.45, [(0, .17, 800, 1000, .18), (.16, .27, 980, 1180, .18)], .015),
    "perfect_clear": (.78, [(0, .25, 540, 740, .24), (.23, .23, 770, 950, .23), (.43, .30, 1100, 1500, .25)], .02),
    "bomb_ready": (.27, [(0, .11, 540, 620, .24), (.12, .15, 830, 940, .25)], .0),
    "bomb_arm": (.25, [(0, .11, 380, 480, .23), (.10, .14, 510, 640, .22)], .045),
    "bomb_explode": (.68, [(0, .48, 180, 38, .40), (.12, .51, 100, 30, .23)], .32),
    "garbage_cancel": (.27, [(0, .11, 790, 600, .20), (.11, .13, 630, 390, .20)], .055),
}


def synthesize(duration, notes, noise):
    total = int(duration * SAMPLE_RATE)
    samples = []
    for n in range(total):
        t = n / SAMPLE_RATE
        value = 0.0
        for start, length, freq0, freq1, amp in notes:
            pos = t - start
            if not (0 <= pos < length):
                continue
            u = pos / length
            frequency = freq0 + (freq1 - freq0) * u
            phase = 2 * math.pi * (freq0 * pos + (freq1 - freq0) * pos * u / 2)
            # Soft attack, short percussive exponential decay.
            envelope = min(1.0, pos / .007) * (1 - u) ** 1.65
            value += amp * envelope * (math.sin(phase) + .15 * math.sin(2 * phase))
        if noise:
            tail = (1 - t / duration) ** 3
            value += noise * random.uniform(-1, 1) * tail
        samples.append(struct.pack("<h", round(max(-1, min(1, value)) * 32767)))
    return b"".join(samples)


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, (duration, notes, noise) in SOUNDS.items():
        with wave.open(str(TARGET / (name + ".wav")), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(synthesize(duration, notes, noise))
        print(name + ".wav")


if __name__ == "__main__":
    main()
