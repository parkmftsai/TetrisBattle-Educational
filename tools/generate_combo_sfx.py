"""Generate original *placeholder* Combo tiers and bomb-chain sound.

These are custom-synthesized effects, NOT audio from the linked YouTube video.
Run this file to rebuild the default WAVs without requiring downloaded media.
"""
import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "TetrisBattle/assets/tetris sounds/sfx"
SAMPLE_RATE = 22050


def write_sfx(name, freqs, beat_sec=.095, duration=None):
    duration = duration or (len(freqs) * beat_sec + .12)
    pcm = bytearray()
    count = int(duration * SAMPLE_RATE)
    for j in range(count):
        t = j / SAMPLE_RATE
        i = min(len(freqs) - 1, int(t / beat_sec))
        phase = t - i * beat_sec
        # Chirped 8-bit arcade-style tones, tremolo and a quick soft release.
        freq = freqs[i] * (1.0 + .12 * math.exp(-16 * max(0, phase)))
        env = min(1, phase * 90) * math.exp(-5.5 * max(0, phase))
        if t > duration - .085:
            env *= max(0, (duration - t) / .085)
        tone = (math.sin(2 * math.pi * freq * phase) * .72 +
                math.sin(2 * math.pi * freq * 2.0 * phase) * .18 +
                math.sin(2 * math.pi * freq * 3.01 * phase) * .1)
        tremolo = .83 + .17 * math.sin(2 * math.pi * 12.7 * t)
        sample = int(max(-1, min(1, tone * env * tremolo * .58)) * 32767)
        pcm.extend(struct.pack("<h", sample))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT / (name + ".wav")), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(pcm)


def main():
    for level in range(1, 11):
        base = 340 + level * 48
        steps = [base, base * 1.25, base * 1.5] if level >= 5 else [base, base * 1.33]
        if level >= 8:
            steps.append(base * 2)
        write_sfx("combo_{}".format(level), steps, beat_sec=.078)
    write_sfx("bomb_chain", [155, 235, 355, 505, 710], beat_sec=.067)
    print("Generated 10 distinct Combo tiers + bomb-chain placeholder (NOT video recordings).")

if __name__ == "__main__":
    main()
