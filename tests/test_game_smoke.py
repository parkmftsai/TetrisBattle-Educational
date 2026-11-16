"""Exercise the actual match event loop with a drawable stand-in.

This verifies game-state integration without claiming real SDL rendering/audio.
"""
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.controls import load_keymaps
from game.tetris_game import TetrisGame


class FakeRenderer:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeAudio:
    def __init__(self):
        self.calls = []
    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args))
            return True
        return record


class FakeScreen:
    def copy(self):
        return self


class FakeClock:
    def tick(self, value):
        return value


@pytest.mark.parametrize("mode, key_batches, result, expected_pause", [
    ("single", [[("key", "p")], [], [("key", "p")], [("key", "r")]], "restart", True),
    ("single", [[("key", "f1")], [("key", "f1")], [("key", "escape")]], "menu", True),
    ("single", [[("key", "m"), ("key", "n"), ("key", "=")], [("key", "escape")]], "menu", False),
    ("double", [[], [("key", "escape")]], "menu", False),
])
def test_match_event_loop_handles_shortcuts(monkeypatch, mode, key_batches, result, expected_pause):
    game = TetrisGame.__new__(TetrisGame)
    game.mode = mode
    game.num_players = 1 if mode == "single" else 2
    game.keymaps = load_keymaps(mode)
    game.audio = FakeAudio()
    game.renderer = FakeRenderer()
    game.screen = FakeScreen()
    game.clock = FakeClock()
    game._footnote = lambda value: None
    overlay_calls = []
    game._pause_overlay = lambda snapshot, help_visible: overlay_calls.append(help_visible)
    batches = iter(key_batches)

    def events():
        try:
            batch = next(batches)
        except StopIteration:
            batch = [("key", "escape")]
        return [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code(name))
                for kind, name in batch]

    monkeypatch.setattr(pygame, "event", SimpleNamespace(get=events), raising=False)
    monkeypatch.setattr(pygame, "display", SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, "draw", SimpleNamespace(rect=lambda *a: None), raising=False)
    # This runs TetrisGame._run_match with REAL Tetris instances and controls,
    # and only substitutes actual drawing and OS event delivery.
    assert game._run_match("none") == result
    assert (len(overlay_calls) > 0) is expected_pause
    assert "start_music" in [item[0] for item in game.audio.calls]
    assert "stop_music" in [item[0] for item in game.audio.calls]
    if result == "restart":
        assert ("pause_music", (True,)) in game.audio.calls
        assert ("pause_music", (False,)) in game.audio.calls


def test_live_model_bomb_chain_inside_real_match_loop(monkeypatch):
    """Live input -> hard drop -> placed piece on real bomb garbage -> SFX."""
    import game.tetris_game as game_mod
    from TetrisBattle.tetris import Piece
    from TetrisBattle.settings import PIECES_DICT

    original = game_mod.Tetris

    def seeded_model(*args, **kwargs):
        obj = original(*args, **kwargs)
        obj.build_garbage(obj.grid, 2, bomb_columns=[4, 4])
        obj.block = Piece("O", PIECES_DICT["O"])
        obj.px = 3
        return obj

    monkeypatch.setattr(game_mod, "Tetris", seeded_model)
    game = TetrisGame.__new__(TetrisGame)
    game.mode = "single"
    game.num_players = 1
    game.keymaps = load_keymaps("single")
    game.audio = FakeAudio()
    game.renderer = FakeRenderer()
    game.screen = FakeScreen()
    game.clock = FakeClock()
    game.bombs_enabled = True
    game._footnote = lambda value: None
    game._pause_overlay = lambda *args: None
    game.effects = None
    key_batches = iter([["space"], ["escape"]])

    def events():
        return [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code(name))
                for name in next(key_batches, ["escape"])]

    monkeypatch.setattr(pygame, "event", SimpleNamespace(get=events), raising=False)
    monkeypatch.setattr(pygame, "display", SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, "draw", SimpleNamespace(rect=lambda *a: None), raising=False)
    assert game._run_match("none") == "menu"
    played = [args[0] for name, args in game.audio.calls if name == "play"]
    assert all(event in played for event in ("hard_drop", "lock", "bomb_explode", "bomb_chain"))
    assert "bomb_arm" not in played


def test_visual_toggle_key_inside_match(monkeypatch):
    game = TetrisGame.__new__(TetrisGame)
    game.mode = "single"
    game.num_players = 1
    game.keymaps = load_keymaps("single")
    game.audio = FakeAudio()
    game.renderer = FakeRenderer()
    game.screen = FakeScreen()
    game.clock = FakeClock()
    game._footnote = lambda value: None
    game.effects = None
    game.visual_effects_enabled = True
    events_batches = iter([["f3"], ["escape"]])
    def events():
        return [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code(k))
                for k in next(events_batches, ["escape"])]
    monkeypatch.setattr(pygame, "event", SimpleNamespace(get=events), raising=False)
    monkeypatch.setattr(pygame, "display", SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, "draw", SimpleNamespace(rect=lambda *a: None), raising=False)
    assert game._run_match("none") == "menu"
    assert game.visual_effects_enabled is False
