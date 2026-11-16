# How to record gameplay GIFs

## GIFs already included

- `docs/media/gameplay_single_demo.gif`
- `docs/media/gameplay_double_demo.gif`

These animations were scripted from the real Python TetrisBattle board/game-state logic and drawn with a small custom UI. They **do not record Pygame screen output**. Source: `tools/render_game_state_gif.py`. Generate them with Pillow and NumPy installed:

```bash
python tools/render_game_state_gif.py --mode single --output docs/media/gameplay_single_demo.gif
python tools/render_game_state_gif.py --mode double --output docs/media/gameplay_double_demo.gif
```

## Capture the actual game window on your computer

The included `tools/record_live_gameplay.py` captures the **real Pygame display surface** while you play, without requiring OBS/FFmpeg. It needs a computer with a working graphical display and `pygame`, `numpy`, `Pillow` installed. The recording excludes sound because GIF does not support audio.

```bash
python -m pip install -r requirements.txt
python -m pip install Pillow
python tools/record_live_gameplay.py --mode single --seconds 12 --fps 8 --output docs/media/live_single.gif
python tools/record_live_gameplay.py --mode double --seconds 12 --fps 8 --output docs/media/live_double.gif
```

Press gameplay keys while the game window is in focus. Close the window normally or let the recorder finish the configured clip duration; the recording is saved when the game session exits. For large GIFs lower the FPS or reduce the output width. Once you personally verify the live files, update the two README image URLs to use `docs/media/live_single.gif` and `docs/media/live_double.gif`, and relabel them as actual Pygame recordings.

**Media rights:** If live footage displays source-derived copyrighted assets, verify publication rights before posting publicly.
