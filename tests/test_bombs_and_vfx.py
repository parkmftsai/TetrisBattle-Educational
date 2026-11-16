"""Regression coverage for optional bomb gameplay and actual event integration."""
import json
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.audio import SFX_DIR, SFX_NAMES
from TetrisBattle.controls import load_keymaps
from TetrisBattle.effects import EVENTS, EffectEngine
from TetrisBattle.settings import GRID_WIDTH
from TetrisBattle.tetris import Tetris, Player, Piece


def make_tetris(mode="single", player=0, enabled=True, grid="none"):
    return Tetris(Player(load_keymaps(mode)[player]), grid, bombs_enabled=enabled)


def event_key(name):
    return SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code(name))


@pytest.mark.parametrize("preset", ["classic", "wasd"])
def test_space_hard_drop_is_mandatory_in_single_player(preset):
    info = load_keymaps("single", preset)[0]
    tetris = Tetris(Player(info), "none")
    tetris.trigger(event_key("space"))
    assert tetris.py >= 16
    assert tetris.check_fallen()


def test_space_kept_when_custom_drop_reassigned(tmp_path):
    f = tmp_path / "keys.json"
    # Test the mapping rather than pygame's key name database; pygame's
    # stub uses a fixed set of keys, so use a key known in both environments.
    f.write_text(json.dumps({"single": {"p1": {"drop": ["q"]}}}))
    mapping = load_keymaps("single", config_path=f)[0]
    assert pygame.K_SPACE in mapping["drop"]
    assert pygame.key.key_code("q") in mapping["drop"]


def test_cannot_rebind_space_to_movement(tmp_path):
    f = tmp_path / "keys.json"
    f.write_text(json.dumps({"single": {"p1": {"left": "space"}}}))
    with pytest.raises(ValueError, match="assigned to both"):
        load_keymaps("single", config_path=f)


def test_bomb_garbage_rows_appear_after_attack_and_never_require_key():
    model = make_tetris("double")
    events = []
    model.on_event = events.append
    assert model.bomb_charges == 0
    assert not model.arm_bomb()
    model.trigger(event_key("b"))
    assert "bomb_arm" not in events
    model.build_garbage(model.grid, 2, bomb_columns=[4, 4])
    assert model.grid[4][-1] == model.grid[4][-2] == 9
    assert all(model.grid[x][-1] == 8 for x in range(GRID_WIDTH) if x != 4)
    assert all(len(column) == 20 for column in model.grid)


def test_piece_lock_above_bomb_clears_whole_line_and_chains():
    model = Tetris(Player(load_keymaps("single")[0]), "none", bombs_enabled=True,
                   modern_controls=True)
    model.build_garbage(model.grid, 2, [4, 4])
    model.block = Piece("O", __import__("TetrisBattle.settings", fromlist=["PIECES_DICT"]).PIECES_DICT["O"])
    model.px = 3
    calls = []
    model.on_event = calls.append
    model.trigger(event_key("space"))
    assert model.check_fallen()
    assert model.last_bomb_rows == 2
    assert not any(cell in (8, 9) for col in model.grid for cell in col)
    assert all(len(col) == 20 for col in model.grid)
    assert "bomb_explode" in calls and "bomb_chain" in calls
    score = model.clear()
    assert score == 0  # two-bomb bonus is separate from line clear score
    assert model.attack_outgoing == 1
    assert model.combo == -1


def test_one_bomb_no_counterattack_and_wrong_column_no_explosion():
    model = make_tetris()
    model.build_garbage(model.grid, 1, [7])
    assert model.detonate_contact_bombs([(4, 18)]) == 0
    assert model.grid[7][-1] == 9
    assert model.detonate_contact_bombs([(7, 18)]) == 1
    model.clear()
    assert model.attack_outgoing == 0
    assert model.last_bomb_rows == 1


def test_bomb_clear_preserves_combo_b2b_without_line_clear():
    model = make_tetris()
    model.combo = 3
    model.now_back2back = 1
    model.build_garbage(model.grid, 2, [5, 5])
    assert model.detonate_contact_bombs([(5, 17)]) == 2
    assert model.clear() == 0
    assert model.combo == 3
    assert model.now_back2back == 1
    # Next ordinary lock without any bomb or regular line clear breaks combo.
    model.detonate_contact_bombs([])
    model.clear()
    assert model.combo == -1


def test_solid_garbage_when_bombs_off():
    model = make_tetris(enabled=False)
    model.build_garbage(model.grid, 3)
    assert all(model.grid[x][y] == 8 for x in range(10) for y in (-1, -2, -3))
    assert not model.arm_bomb()
    assert model.detonate_contact_bombs([(4, 16)]) == 0


def test_bomb_garbage_fixed_height_and_overflow_ko():
    model = make_tetris()
    model.grid[0][0] = 2
    model.build_garbage(model.grid, 2, [0, 1])
    assert model.garbage_overflow
    assert model.check_KO()
    model.clear_garbage()
    assert not model.garbage_overflow
    assert all(len(col) == 20 for col in model.grid)


def test_garbage_cancellation_consumes_attack_before_sending():
    model = make_tetris()
    model.add_attacked(3)
    for y in (-1, -2, -3, -4):
        for x in range(GRID_WIDTH):
            model.grid[x][y] = 2
    score = model.clear()
    assert score >= 4
    assert model.garbage_cancelled == 3
    assert model.attack_outgoing == max(0, score - 3)
    assert model.sent == model.attack_outgoing
    assert model.attacked == 0


def test_vfx_events_and_pause_freeze():
    engine = EffectEngine(enabled=True)
    for name in EVENTS:
        engine.event(name, (112, 138, 180, 360), positions=[(4, 10)], total=3)
    assert engine.labels and engine.particles and engine.flashes
    before = engine.particles[0][4]
    # No effect animation updates during pause; only tick() advances frames.
    assert engine.particles[0][4] == before
    engine.tick()
    assert engine.particles[0][4] == before - 1
    assert engine.toggle() is False
    assert not engine.particles
    engine.event("bomb_explode", (112, 138, 180, 360))
    assert not engine.particles


def test_every_vfx_sound_has_a_file():
    for event in EVENTS:
        assert event in SFX_NAMES
        assert (Path(SFX_DIR) / (event + ".wav")).is_file()


def test_vfx_draw_produces_particles_rings_and_bomb_glow(monkeypatch):
    """Exercise the draw path with a fake framebuffer, no SDL device needed."""
    class FakeFont:
        def render(self, text, aa, color):
            return FakeSurface(width=max(10, len(text) * 8), height=22)
    class FakeSurface:
        def __init__(self, *args, width=0, height=0, **kwargs):
            self.width = width
            self.alpha = None
            self.fill_color = None
        def fill(self, value):
            self.fill_color = value
        def set_alpha(self, value):
            self.alpha = value
        def get_width(self):
            return self.width
    class FakeScreen:
        def __init__(self):
            self.blits = []
        def blit(self, item, pos):
            self.blits.append((item, pos))

    circles = []
    monkeypatch.setattr(pygame, "font", SimpleNamespace(SysFont=lambda *a, **k: FakeFont()), raising=False)
    monkeypatch.setattr(pygame, "SRCALPHA", 99, raising=False)
    monkeypatch.setattr(pygame, "Surface", FakeSurface, raising=False)
    monkeypatch.setattr(pygame, "draw", SimpleNamespace(circle=lambda *a: circles.append(a)), raising=False)
    effect = EffectEngine(enabled=True)
    effect.event("bomb_explode", (112, 138, 180, 360), [(4, 13)], total=2)
    screen = FakeScreen()
    effect.draw(screen)
    effect.bomb_glow(screen, 3, 13, 20, (112, 138))
    assert screen.blits, "Expected translucent blast overlay / announcement text"
    assert len(circles) >= 3, "Expected explosion ring, particles and armed-bomb indicator"
