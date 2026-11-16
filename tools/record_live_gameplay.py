#!/usr/bin/env python3
"""Capture a real Pygame display during live play as an animated GIF.

Unlike render_game_state_gif.py, this captures actual drawn screen pixels.
The user controls the game, and recording is finalized when the game exits.
Requires pygame, Pillow and a working desktop graphical environment.
"""
import argparse
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
from PIL import Image
from game.tetris_game import TetrisGameSingle, TetrisGameDouble


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=('single', 'double'), default='single')
    ap.add_argument('--seconds', type=float, default=12)
    ap.add_argument('--fps', type=int, default=8)
    ap.add_argument('--output', default='docs/media/live_gameplay.gif')
    ap.add_argument('--width', type=int, default=720)
    args = ap.parse_args()
    if args.seconds <= 0 or not 1 <= args.fps <= 30 or args.width <= 0:
        ap.error('seconds, fps and width must be positive; fps <= 30')

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    created = time.monotonic()
    next_capture = created
    last_capture = created
    original_flip = pygame.display.flip
    original_update = pygame.display.update
    max_frames = int(args.seconds * args.fps)
    warned = False

    def capture():
        nonlocal next_capture, last_capture, warned
        now = time.monotonic()
        if len(frames) >= max_frames or now < next_capture:
            return
        surface = pygame.display.get_surface()
        if surface is None:
            return
        try:
            data = pygame.image.tostring(surface, 'RGB')
            frame = Image.frombytes('RGB', surface.get_size(), data)
            h = max(1, round(frame.height * args.width / frame.width))
            frame = frame.resize((args.width, h), Image.Resampling.BILINEAR)
            frames.append(frame)
            last_capture = now
            next_capture = now + 1.0 / args.fps
            if len(frames) == max_frames and not warned:
                print('Recording length reached. You can finish playing or close the game window to save.')
                warned = True
        except pygame.error:
            pass

    def flip(*a, **kw):
        result = original_flip(*a, **kw)
        capture()
        return result

    def update(*a, **kw):
        result = original_update(*a, **kw)
        capture()
        return result

    pygame.display.flip = flip
    pygame.display.update = update
    try:
        game_class = TetrisGameSingle if args.mode == 'single' else TetrisGameDouble
        game = game_class(start_map='none')
        game.play()
    finally:
        pygame.display.flip = original_flip
        pygame.display.update = original_update
        if frames:
            frames[0].save(str(out), save_all=True, append_images=frames[1:],
                           duration=round(1000 / args.fps), loop=0,
                           optimize=True, disposal=2)
            print(f'Saved {len(frames)} actual Pygame screen frames to {out}')
        else:
            print('No live screen frames captured; check that Pygame opened a display.')


if __name__ == '__main__':
    main()
