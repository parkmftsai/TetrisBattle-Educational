# Changelog — TetrisBattle Educational Edition

This is a feature-level summary assembled from the project snapshots, not a reconstructed upstream Git history. Dates reflect the adaptation work and release packaging.

## 2026-11-17 — English GitHub release and gameplay demonstrations

- Standardized public-facing documentation and launch script names in English.
- Added two **scripted game-state GIFs** generated from the current Python Tetris model, with clear disclosure that they are not live-window captures.
- Added `tools/record_live_gameplay.py` for capturing a real Pygame session to a GIF on a supported computer.
- Retained citations and separation of upstream MIT code and third-party media rights.

## 2026-11-17 — Windows IME and immediate top-out

- Attempt to disable composition in the focused Pygame window without changing global Windows input-language preferences.
- Detect new-piece collision, hold-spawn collision, and garbage overflow; end a two-player match on its first top-out.
- Treat simultaneous top-outs as a draw.

## 2026-11-17 — Original-style visuals, phase 1

- Extracted and integrated Classic/Default/Neon mino styles and selected ghost/bomb images from a user-provided SWF archive.
- Added reconstructed explosions, Combo, and T-Spin effects; these are **not** original complete Flash animation timelines.
- Added F5–F8 visual switching and a fallback when optional media is absent.

## 2026-11-16 — Audio integration

- Extracted 54 named sound symbols from a user-provided `FacebookMainframe.swf`, mapped sounds to events, and retained fallback audio.
- Original Flash symbols include Combo levels 1–7, bomb variants, line-clear sounds, T-Spin, Hard Drop, Hold and win/lose cues.
- Added a workflow for importing authorized clips.

## 2026-11-16 — Gameplay and stability

- Replaced the experimental B/Y 3×3 bomb inventory with garbage-row bomb contacts and chain reactions.
- Improved SRS-style T-piece rotation, held movement timing (DAS/ARR), and first-frame keyboard controls.
- Preserved single-player Space Hard Drop, keyboard mapping overrides, pause/restart and audio toggles.
- Fixed a missing `BOMB_CELL` import in the status display.

## Verification caveats

Past snapshots reported 140 automated tests for the full package (and 119 passes / 21 skips for the code-only package). Those are historical results, **not** a claim of live Windows/Pygame validation. Actual audio, IME behavior, frame rendering and real play must still be tested on a compatible machine.
