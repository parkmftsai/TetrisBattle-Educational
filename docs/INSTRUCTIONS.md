# Installation, controls and troubleshooting

## Install

From the project root, with Python 3.10–3.12 installed:

```bash
python -m pip install -r requirements.txt
```

## Launch

```bash
python -m game.tetris_game --mode single --map none
python -m game.tetris_game --mode double --map none
python -m game.tetris_game --mode single --controls wasd
```

Windows shortcut files: `start_single_windows.bat`, `start_double_windows.bat`, `start_menu_windows.bat`. POSIX shortcuts: `start_single_linux_macos.sh`, `start_double_linux_macos.sh`, `start_menu_linux_macos.sh`.

## Gameplay controls

| Action | Player 1 | Player 2 |
|:--|:--|:--|
| Left/right | `←` / `→` | `H` / `K` |
| Soft drop | `↓` | `J` |
| Rotate clockwise | `↑`, `X` | `U`, `I` |
| Rotate counterclockwise | `Z` | `Q` |
| Hard drop | **Space** | `W` |
| Hold | `C`, Left Shift | `E` |

`F1` help; `P` pause; `R` restart; `Esc` menu; `F2` change single-player preset in menu; `Tab` change mode in menu; `F3` effects; `F4` garbage bombs; `F5`–`F8` visual styles; `M` music; `N` sound; `-`/`=` volume.

## Windows IME

The game attempts to disable IME composition on its window when active. It does not permanently change the OS language. If keys still fail, click the window and run `python -m game.tetris_game --mode single --map none --debug-input`. If needed, use `Win + Space` to temporarily select an English keyboard.

## Rules and limitations

The two-player game ends immediately when one player tops out, including spawn collision or garbage overflow. Bombs are part of incoming garbage lines; they are not activated by a dedicated B/Y key. Visuals and effects are optional. Available sounds and skins depend on installed assets and media rights.

## Test

```bash
python -m pip install pytest
python -m pytest -q
```

Live Pygame/IME/audio validation is still necessary on Windows. Tests without a graphical display validate logic and interfaces only.
