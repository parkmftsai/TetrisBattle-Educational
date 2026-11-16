> Historical project notes. For current instructions use [README](../README.md).

# **TetrisBattle**

This project is to reproduce the popular Facebook game -- Tetris Battle (Not available playing online now). I also offer the environment of the game for training AI agent.

It is a highly restored version of original game, with features as follow: <br/>
- 2 players <br/>
- UI  <br/>
- T spin and Tetris <br/>
- back to back <br/>
- garbage lines <br/>
- alarm for attacks <br/>

Note that some of them are credited to https://github.com/xuyuwei/tetris-battle.

The repository contains:

1. Single player mode
2. Two players mode
3. Environments for training AI agent, wrapped as OpenAI [gym](https://github.com/openai/gym) environment. (e.g. `tetris_env.py`)

## **Demo**


### Single player mode

demo the fuctions: tspin and back to back.

![single player](imgs/demo_single.gif)

### Two players mode

demo the functions: tetris, combo and ko.

![two player](imgs/demo_double.gif)

## **Requirements**
```
python3 
pygame 
Linux system 
```

Note that pygame might have conflicts with macOS. <br/>

In my case, the program works well on macOS 10.14.6 with `pygame==2.0.0.dev1` and `python==3.7.4`. However, it breaks with `pygame==1.9.4`.

## **Installation**
```
python setup.py develop
```

## **Usage**

### Single player mode

```
python -m game.tetris_game --mode single
```

### Two players mode

```
python -m game.tetris_game --mode double
```

### Usage for environments
Please refer to `example.py`.

Note: You can define your reward function in `reward_func` in `tetris_interface.py`

## **Disclaimer**

This work is based on the following repos: <br/>
1. https://github.com/xuyuwei/tetris-battle

## **Contact**
Yi-Lin Sung, r06942076@ntu.edu.tw
## Extended playable edition (2026)

This distribution keeps the original sprite artwork, background music, map
presets, UI, single-/two-player modes, combo, T-Spin, back-to-back, garbage,
KO, and optional legacy Gym environment.

New **playable** features (not available in the original ZIP):

* Space hard drops in **all single-player key presets** (cannot be removed by
  custom keyboard JSON configuration). P2 retains W as hard drop.
* **Original Facebook Battle-style garbage bombs** (default for human 2P):
  incoming garbage rows have a bomb target instead of a hole. Drop a piece
  onto the target to remove its whole row. Vertically aligned targets can
  chain; two bombs send one counterattack, three send two. There is no B/Y
  power-up or 3×3 blast. F4 or `--no-bombs` selects solid garbage instead.
* Particle rings, spark bursts, flashes, bomb-cell indicators, and combo/
  attack announcements. Toggle with `F3`.
* Original-synthesis placeholder sounds, including **10 different Combo
  levels** and a bomb-chain tone, plus the existing background music. These
  sounds are **NOT recordings from any YouTube video**. `M` toggles music; `N` toggles SFX;
  `-`/`=` adjust volume.
* `TAB` switches between 1P/2P from the main menu, `F2` toggles 1P key
  layout, `F4` toggles bombs for the upcoming round, `F1` shows controls,
  `P` pauses, `R` restarts the round and `ESC` returns to the menu.
* Fairer simultaneous 2P attack handling: outgoing power first cancels pending
  garbage; simultaneous attacks are applied after both players' turns.
* Optional `--no-bombs`, `--no-effects`, `--no-audio`, `--keymap FILE` flags.

**Current English controls guide:** [English controls guide](INSTRUCTIONS.md)

```sh
python -m pip install -r requirements.txt
python -m game.tetris_game --mode single
python -m game.tetris_game --mode single --controls wasd
python -m game.tetris_game --mode double
python -m pytest -q tests
```

Windows: launch `start_menu_windows.bat` / `start_double_windows.bat`.
Linux/macOS: use the corresponding `.sh` scripts.

**Source/accuracy note:** The original source and previous ZIP provide no
bomb mechanic or prior copyrighted special-effects pack. The bombs in this
edition are newly specified and implemented, not a claim of exact parity with
the discontinued Facebook product. The original AI/Gym action set remains
unchanged, and the game now separates playable additions from legacy behavior.

### Recorded/local sound-effect import (additional feature)

This fork supports independently licensed recorded SFX packs, e.g. recordings
extracted from video files you are authorized to use. See `docs/INSTRUCTIONS.md`,
section 10, and `audio_cues/`. An event cue is written to `sfx_packs/<pack>/<event>.wav`
by `tools/import_recorded_sfx.py`; the audio engine selects it on actual game
events and falls back to the original 23 synthesized effects for absent cues.
Recording sources and proprietary sounds are NOT bundled. FFmpeg is required
for importing but not for normal gameplay.

### Control responsiveness fix (2026-11-16)

- Single player: **Space is an immediate hard drop from the first playable frame**; it also detects Space already held during the map-to-game transition. A held Space cannot drop subsequent pieces until released and re-pressed.
- Human game: instant horizontal movement and rotation on keydown; time-based **DAS 120ms, ARR 25ms**, soft drop 30ms. SRS wall kicks and 3-corner T-Spin recognition are enabled for human-controlled games only; legacy AI/Gym timing and action IDs remain unchanged.
- Optional CLI controls: `--das-ms 90 --arr-ms 18 --soft-drop-ms 20` for faster movement. Defaults are 120 / 25 / 30 milliseconds.
- **Current English changelog and launch instructions**: [Changelog](../CHANGELOG.md).

### Keyboard-unresponsive-at-start fix (2026-11-16)

Keyboard-only map selection now works: arrow keys or WASD choose maps,
number keys 1–4 select immediately, and Enter **starts the match** instead of
returning to the menu. Game input synchronizes all held keys (not only Space),
handles KEYUP during pause, and visibly pauses when keyboard focus is lost.

To **start single-player directly with Space immediately usable**, skip the
menu and map chooser:

```sh
python -m game.tetris_game --mode single --map none --debug-input
```

On Windows run `start_single_windows.bat` for the same quick-start and input
diagnostics. Read [Troubleshooting guide](INSTRUCTIONS.md) for all keys and troubleshooting.
When confirming a map *with* Space, release and press it again for Hard Drop.
This release does not claim to have passed a physical keyboard/GUI test in this
non-Pygame environment; it does include synthetic Pygame event-loop tests.

## Original Facebook Flash audio resources (2026-11-16)

The user-supplied `tetrisfb-assets-main(1).zip` contains embedded sound effects in
`data1.81.0/flash/binary/FacebookMainframe.swf`.  This distribution includes
an optional, **activated** `original_facebook` sound pack, with 54 named original
sounds extracted to WAV and 31 event sound files mapped to gameplay.  Original
Flash Battle music is included; existing fallback sounds remain available.

Run `python -m game.tetris_game --mode single --map none` or
`python -m game.tetris_game --mode double --map none` to hear the activated
bank.  Use `--sfx-pack original` for the previous fallback sounds.

See **[Optional original asset notes](ORIGINAL_ASSETS.md)** for provenance,
exact Combo/Bomb mappings, extraction instructions, licensing cautions, and
limits of the original-gameplay reconstruction.
