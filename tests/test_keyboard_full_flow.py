"""Regressions for the specific user report: keyboard unusable on starting 1P.

Exercises menu -> map -> first playable frame, not just a Tetris object.
Uses synthetic SDL events with real game flow and logic; it cannot substitute
for a real focused Pygame window / physical keyboard test.
"""
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.controls import load_keymaps
from TetrisBattle.tetris import Player, Tetris
from game.tetris_game import TetrisGame
from test_game_smoke import FakeRenderer, FakeAudio, FakeScreen, FakeClock


def ev(name, down=True):
    return SimpleNamespace(type=pygame.KEYDOWN if down else pygame.KEYUP,
                           key=pygame.key.key_code(name))


def model():
    return Tetris(Player(load_keymaps("single")[0]), "none", modern_controls=True)


def stub_game():
    game = TetrisGame.__new__(TetrisGame)
    game.mode = "single"
    game.num_players = 1
    game.controls = "classic"
    game.keymap = None
    game.keymaps = load_keymaps("single")
    game.audio = FakeAudio()
    game.renderer = FakeRenderer()
    game.screen = FakeScreen()
    game.clock = FakeClock()
    game.bombs_enabled = False
    game.effects = None
    game._last_gridchoice = None
    game._quit_requested = False
    game.start_map = None
    game._footnote = lambda _: None
    game._pause_overlay = lambda *_: None
    return game


def setup_sdl(monkeypatch, batches):
    queue = iter(batches)
    monkeypatch.setattr(pygame, "event", SimpleNamespace(get=lambda: next(queue, [ev("escape")])), raising=False)
    monkeypatch.setattr(pygame, "display", SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, "draw", SimpleNamespace(rect=lambda *args: None), raising=False)
    monkeypatch.setattr(pygame, "mouse", SimpleNamespace(get_pos=lambda: (-1, -1)), raising=False)


def audio_events(game):
    return [args[0] for name, args in game.audio.calls if name == "play"]


def test_keyboard_can_reach_game_from_menu_without_clicking(monkeypatch):
    game = stub_game()
    setup_sdl(monkeypatch, [
        [ev("return")],  # choose Start from menu
        [ev("right")],   # choose map 2 with keyboard
        [ev("return")],  # CONFIRM, must not silently return to menu
        [ev("left"), ev("x"), ev("space")],  # first playable frame
        [ev("escape")],
    ])
    assert game.menu() == "start"
    assert game.start() == "menu"  # escape after first PLAYABLE frame
    assert game._last_gridchoice == "classic"
    played = audio_events(game)
    for name in ("move", "rotate", "hard_drop", "lock"):
        assert name in played, "No first-frame gameplay action: " + name


def test_map_selection_numbers_and_space_confirmation(monkeypatch):
    game = stub_game()
    setup_sdl(monkeypatch, [[ev("4")]])
    assert game.setmap() == "lunchbox"

    game = stub_game()
    setup_sdl(monkeypatch, [[ev("space")]])
    assert game.setmap() == "none"
    assert game._suppress_initial_space is True


def test_poll_all_keys_if_menu_swallowed_first_keydown(monkeypatch):
    game = stub_game()
    setup_sdl(monkeypatch, [[], [ev("escape")]])
    class Physical:
        def __getitem__(self, key):
            return key in {pygame.K_LEFT, pygame.K_SPACE}
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: Physical(), raising=False)
    assert game._run_match("none") == "menu"
    for name in ("move", "hard_drop", "lock"):
        assert name in audio_events(game)


def test_all_actions_synced_on_first_frame_not_just_space():
    tetris = model()
    keys = {
        pygame.key.key_code("left"), pygame.key.key_code("x"),
        pygame.key.key_code("c"),
    }
    class Physical:
        def __getitem__(self, code):
            return code in keys
    events = []
    tetris.on_event = events.append
    tetris.sync_pressed_keys(Physical())
    assert "move" in events
    assert "rotate" in events
    assert "hold" in events
    assert tetris.held is not None
    assert tetris._held_actions.issuperset(keys)
    x = tetris.px
    tetris.sync_pressed_keys(Physical())
    assert tetris.px == x  # do not repeat first action every frame


def test_pause_release_then_repress_is_not_stuck():
    tetris = model()
    tetris.trigger(ev("left"))
    assert tetris.px == 3
    tetris.release_movement()  # pause
    tetris.trigger(ev("left", down=False))  # KEYUP processed while paused
    tetris.trigger(ev("left"))  # first press on resume
    assert tetris.px == 2


def test_resume_held_direction_restores_repeat_without_dropping_again():
    tetris = model()
    tetris.trigger(ev("left"))
    tetris.trigger(ev("space"))
    tetris.release_movement()
    tetris.check_fallen()
    tetris.new_block()
    class Physical:
        def __getitem__(self, code):
            return code in {pygame.K_LEFT, pygame.K_SPACE}
    tetris.sync_pressed_keys(Physical())
    assert tetris.py == -2, "Resume must not hard-drop a second block"
    assert tetris._direction_keys["left"]
    x = tetris.px
    tetris.move(100)
    tetris.move(20)
    assert tetris.px == x - 1


def test_space_used_as_map_confirm_requires_new_press(monkeypatch):
    game = stub_game()
    game._suppress_initial_space = True
    setup_sdl(monkeypatch, [[], [ev("escape")]])
    class Physical:
        def __getitem__(self, key):
            return key == pygame.K_SPACE
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: Physical(), raising=False)
    assert game._run_match("none") == "menu"
    assert "hard_drop" not in audio_events(game)


def test_quick_start_bypasses_menu_and_map(monkeypatch):
    game = stub_game()
    game.start_map = "none"
    routes = []
    game.start = lambda reuse_map=False: (routes.append(("start", reuse_map)) or "exit")
    game.menu = lambda: (_ for _ in ()).throw(AssertionError("menu must be bypassed"))
    game.setmap = lambda: (_ for _ in ()).throw(AssertionError("map must be bypassed"))
    monkeypatch.setattr(pygame, "quit", lambda: None, raising=False)
    game.play()
    assert routes == [("start", False)]


def test_focus_loss_pauses_and_regain_restores_keys(monkeypatch):
    game = stub_game()
    setup_sdl(monkeypatch, [[], [ev("space")], [ev("escape")]])
    focus_checks = iter([False, True])
    game._keyboard_focused = lambda: next(focus_checks, True)
    prompts = []
    game._focus_overlay = lambda snapshot: prompts.append("click to focus")
    assert game._run_match("none") == "menu"
    assert prompts == ["click to focus"]
    assert "hard_drop" in audio_events(game)


def test_quick_start_real_match_accepts_space_immediately(monkeypatch):
    game = stub_game()
    game.start_map = "none"
    setup_sdl(monkeypatch, [[ev("space")], [ev("escape")]])
    game.setmap = lambda: (_ for _ in ()).throw(AssertionError("should skip map"))
    assert game.start() == "menu"
    assert game._last_gridchoice == "none"
    assert "hard_drop" in audio_events(game)


def test_key_release_synchronization_recovers_next_press():
    tetris = model()
    tetris.trigger(ev("space"))
    tetris.check_fallen()
    tetris.new_block()
    class Physical:
        def __init__(self, pressed):
            self.pressed = pressed
        def __getitem__(self, code):
            return code in self.pressed
    tetris.sync_pressed_keys(Physical(set()))  # miss KEYUP, but physical says released
    assert pygame.K_SPACE not in tetris._held_actions
    tetris.sync_pressed_keys(Physical({pygame.K_SPACE}))
    assert tetris.py > -2, "Next press must hard-drop without event delivery"
