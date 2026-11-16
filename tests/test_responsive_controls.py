"""Regressions for first-frame hard drop, responsive DAS/ARR, and SRS T-spins.

Tests run on pygame's real key codes when pygame is installed; otherwise the
project's event stub is used (no GUI/audio test claims).
"""
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.controls import load_keymaps
from TetrisBattle.settings import PIECES_DICT
from TetrisBattle.tetris import Piece, Player, Tetris, rotate_srs
from game.tetris_game import TetrisGame
from test_game_smoke import FakeAudio, FakeRenderer, FakeClock, FakeScreen


def event(kind, name):
    return SimpleNamespace(type=pygame.KEYDOWN if kind == "down" else pygame.KEYUP,
                           key=pygame.key.key_code(name))


def modern(preset="classic"):
    return Tetris(Player(load_keymaps("single", preset)[0]), "none", modern_controls=True)


def test_first_input_moves_immediately_and_respects_das_arr():
    model = modern()
    model.trigger(event("down", "left"))
    assert model.px == 3, "First press must move immediately, even at frame zero"
    for _ in range(11):
        model.move(10)
    assert model.px == 3, "No autorepeat before the DAS delay"
    model.move(10)
    assert model.px == 2, "DAS repeat starts after 120ms"
    model.move(25)
    assert model.px == 1, "Held movement repeats every 25ms"
    model.trigger(event("up", "left"))
    for _ in range(15):
        model.move(10)
    assert model.px == 1, "Key release must stop continued movement"


def test_opposite_direction_takes_priority_and_reverses_without_delay():
    model = modern()
    model.trigger(event("down", "left"))
    assert model.px == 3
    model.trigger(event("down", "right"))
    assert model.px == 4
    model.trigger(event("up", "right"))
    assert model.px == 3, "Return to still-held direction without sticky delay"
    model.trigger(event("up", "left"))
    assert model._horizontal_active is None


def test_rotation_on_first_frame_and_rapid_taps():
    model = modern()
    model.block = Piece("T", PIECES_DICT["T"])
    model.trigger(event("down", "x"))
    assert model.block.current_shape_id == 1, "No 10-frame initial lockout"
    model.trigger(event("down", "x"))
    assert model.block.current_shape_id == 1, "Ignore held-key auto repeats"
    model.trigger(event("up", "x"))
    model.trigger(event("down", "x"))
    assert model.block.current_shape_id == 2, "Fast separate key presses must work"
    model.trigger(event("up", "x"))
    model.trigger(event("down", "z"))
    assert model.block.current_shape_id == 1, "Reverse rotation must work instantly"


def test_srs_uses_wall_kicks_to_escape_obstacle():
    model = modern()
    model.block = Piece("T", PIECES_DICT["T"])
    model.px = 4
    model.py = 14
    model.grid[5][17] = 3  # Blocks raw 0->R, but not a left kick.
    model.trigger(event("down", "x"))
    assert model.block.current_shape_id == 1
    assert model.px == 3, "SRS must try (-1,0) kick after obstructed rotation"


def test_srs_rotation_fails_safely_if_all_kicks_blocked():
    model = modern()
    model.block = Piece("T", PIECES_DICT["T"])
    model.px, model.py = 4, 14
    # Placing solid blocks everywhere prevents all valid kicks.
    for x in range(10):
        for y in range(20):
            model.grid[x][y] = 2
    previous = (model.px, model.py, model.block.current_shape_id)
    model.trigger(event("down", "x"))
    assert (model.px, model.py, model.block.current_shape_id) == previous


def test_t_spin_requires_last_rotation_and_three_corners():
    model = modern()
    model.block = Piece("T", PIECES_DICT["T"])
    model.px, model.py = 4, 15
    for x, y in ((4, 16), (6, 16), (6, 18)):
        model.grid[x][y] = 2
    model.trigger(event("down", "x"))
    assert model.block.current_shape_id == 1
    model.LAST_FALL_DOWN_TIME = 40
    assert model.check_fallen()
    assert model.tspin == 1

    other = modern()
    other.block = Piece("T", PIECES_DICT["T"])
    other.px, other.py = 4, 15
    other.grid[6][18] = 2
    other.trigger(event("down", "x"))
    other.LAST_FALL_DOWN_TIME = 40
    assert other.check_fallen()
    assert other.tspin == 0, "A single occupied corner is not a T-Spin"


def test_space_first_frame_hard_drops_and_is_edge_triggered():
    model = modern()
    events = []
    model.on_event = events.append
    model.trigger(event("down", "space"))
    assert model.py >= 16
    assert model.check_fallen()
    model.new_block()
    model.trigger(event("down", "space"))
    assert model.py == -2, "Holding Space must not drop subsequent pieces"
    model.trigger(event("up", "space"))
    model.trigger(event("down", "space"))
    assert model.py > -2, "Pressing Space again must immediately hard drop"
    assert events.count("hard_drop") == 2


@pytest.mark.parametrize("preset", ["classic", "wasd"])
def test_held_space_across_map_transition(preset):
    model = modern(preset)
    model.sync_single_space(True)
    assert model.py >= 16
    model.check_fallen()
    model.new_block()
    model.sync_single_space(True)
    assert model.py == -2
    model.sync_single_space(False)
    model.sync_single_space(True)
    assert model.py > -2


def test_real_match_first_frame_space_state_poll(monkeypatch):
    """Integration: simulate a Space KEYDOWN eaten on the map-selection screen."""
    game = TetrisGame.__new__(TetrisGame)
    game.mode = "single"
    game.num_players = 1
    game.keymaps = load_keymaps("single")
    game.audio = FakeAudio()
    game.renderer = FakeRenderer()
    game.screen = FakeScreen()
    game.clock = FakeClock()
    game.bombs_enabled = False
    game.effects = None
    game._footnote = lambda value: None
    batches = iter([[], [event("down", "escape")]])
    monkeypatch.setattr(pygame, "event", SimpleNamespace(get=lambda: next(batches, [event("down", "escape")])), raising=False)
    monkeypatch.setattr(pygame, "display", SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, "draw", SimpleNamespace(rect=lambda *a: None), raising=False)
    class Pressed:
        def __getitem__(self, key):
            return key == pygame.K_SPACE
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: Pressed(), raising=False)
    assert game._run_match("none") == "menu"
    played = [args[0] for method, args in game.audio.calls if method == "play"]
    assert "hard_drop" in played, "Match must recover Space pressed before entering game"
    assert "lock" in played


def test_legacy_ai_rotation_remains_separate():
    model = Tetris(Player(load_keymaps("single")[0]), "none")
    assert not model.modern_controls
    model.block = Piece("T", PIECES_DICT["T"])
    model.trigger(event("down", "x"))
    assert model.block.current_shape_id == 0, "Legacy timer rules preserved for Gym"
    model.LAST_ROTATE_TIME = 100
    model.trigger(event("down", "x"))
    assert model.block.current_shape_id == 1

@pytest.mark.parametrize("grid", ["none", "classic", "comboking", "lunchbox"])
def test_random_modern_keyboard_stress_on_all_maps(grid):
    import random
    rng = random.Random(6133)
    model = Tetris(Player(load_keymaps("single")[0]), grid,
                   modern_controls=True, bombs_enabled=True)
    keys = ["left", "right", "down", "x", "z", "space", "c", "b"]
    held = set()
    for i in range(1800):
        name = rng.choice(keys)
        if name in held:
            model.trigger(event("up", name))
            held.remove(name)
        else:
            model.trigger(event("down", name))
            held.add(name)
        model.natural_down()
        model.move(rng.randint(7, 25))
        if model.check_fallen():
            model.clear()
            if model.check_KO():
                model.clear_garbage()
            model.new_block()
        model.increment_timer()
        assert all(0 <= model.px + dx < 10 for dx, dy in model.block.get_feasible())
        assert model.py < len(model.grid[0])
        assert all(len(col) == len(model.grid[0]) for col in model.grid)


def test_configurable_timing_and_invalid_settings():
    model = Tetris(Player(load_keymaps("single")[0]), "none",
                   modern_controls=True, das_ms=80, arr_ms=20, soft_drop_ms=15)
    model.trigger(event("down", "left"))
    assert model.px == 3
    model.move(80)
    assert model.px == 2
    model.move(20)
    assert model.px == 1
    with pytest.raises(ValueError, match="Input timing"):
        Tetris(Player(load_keymaps("single")[0]), "none", modern_controls=True, arr_ms=0)
