"""Windows IME guard and first-top-out match-ending regression tests.

The fake IMM32 verifies API calls without claiming to emulate a real Windows
IME/keyboard. The match tests use real Tetris logic with mock SDL events.
"""
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.controls import load_keymaps
from TetrisBattle.settings import PIECES_DICT
from TetrisBattle.tetris import Tetris, Player, Piece
from TetrisBattle.windows_input import GameKeyboardMode
from game.tetris_game import TetrisGame


class FakeImmMethod:
    def __init__(self):
        self.calls = []
        self.argtypes = None
        self.restype = None

    def __call__(self, hwnd, context):
        self.calls.append((hwnd.value, None if context is None else context.value))
        return 123456 if len(self.calls) == 1 else None


class FakeWinDLL:
    def __init__(self):
        self.ImmAssociateContext = FakeImmMethod()


class FakePygame:
    error = type('PygameError', (Exception,), {})

    def __init__(self):
        self.stop_count = 0
        self.repeat_count = 0
        self.key = SimpleNamespace(stop_text_input=self._stop, set_repeat=self._repeat)
        self.display = SimpleNamespace(get_wm_info=lambda: {'window': 0x123456789ABC})

    def _stop(self):
        self.stop_count += 1

    def _repeat(self):
        self.repeat_count += 1


def test_win32_ime_is_disabled_only_for_game_hwnd_and_restored():
    library = FakeWinDLL()
    sdl = FakePygame()
    guard = GameKeyboardMode(sdl, platform='win32', win_dll=library)
    assert guard.enable()
    assert library.ImmAssociateContext.calls == [(0x123456789ABC, None)]
    assert sdl.stop_count == 1
    assert sdl.repeat_count == 1
    guard.refresh()
    assert library.ImmAssociateContext.calls[-1] == (0x123456789ABC, None)
    guard.restore()
    assert library.ImmAssociateContext.calls[-1] == (0x123456789ABC, 123456)
    guard.restore()  # idempotent
    assert len(library.ImmAssociateContext.calls) == 3


def test_ime_guard_still_disables_text_input_on_other_platforms():
    sdl = FakePygame()
    guard = GameKeyboardMode(sdl, platform='linux')
    assert not guard.enable()
    assert (sdl.stop_count, sdl.repeat_count) == (1, 1)
    guard.refresh()
    assert sdl.stop_count == 2
    guard.restore()


def test_ime_guard_is_graceful_when_windows_backend_exposes_no_hwnd():
    sdl = FakePygame()
    sdl.display.get_wm_info = lambda: {}
    assert GameKeyboardMode(sdl, platform='win32').enable() is False
    assert sdl.stop_count == 1


def new_model():
    return Tetris(Player(load_keymaps('single')[0]), 'none', modern_controls=True, bombs_enabled=True)


def test_lock_with_blocks_above_the_ceiling_is_instant_topout():
    model = new_model()
    model.block = Piece('O', PIECES_DICT['O'])
    model.px, model.py = 4, -2
    # O occupies (5, -1), (5, 0), (6, -1), (6, 0), so putting
    # occupied cells immediately below makes it lock with a hidden block.
    model.grid[5][1] = 2
    model.grid[6][1] = 2
    model.LAST_FALL_DOWN_TIME = 9999
    assert model.check_fallen()
    assert model.topped_out
    assert model.check_KO()


def test_new_block_overlapping_the_board_marks_topout():
    model = new_model()
    model.grid[5][0] = 2
    model.buffer.now_list.insert(0, Piece('O', PIECES_DICT['O']))
    model.new_block()
    assert model.topped_out
    assert model.check_KO()


def test_hold_into_blocked_spawn_topouts_immediately():
    model = new_model()
    model.grid[5][0] = 1
    model.held = Piece('O', PIECES_DICT['O'])
    model.trigger(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_c if hasattr(pygame, 'K_c') else pygame.key.key_code('c')))
    assert model.topped_out
    assert model.check_KO()


class NullRenderer:
    def __getattr__(self, _name):
        return lambda *a, **k: None


class NullAudio:
    def __init__(self):
        self.events = []

    def __getattr__(self, name):
        return lambda *a, **k: self.events.append((name, a))


@pytest.mark.parametrize('losing_players,expected_winner', [({0}, 1), ({1}, 0), ({0, 1}, None)])
def test_two_player_match_ends_on_the_first_topout(monkeypatch, losing_players, expected_winner):
    import game.tetris_game as game_mod
    actual_model = game_mod.Tetris

    def seeded(*args, **kwargs):
        model = actual_model(*args, **kwargs)
        if model.get_id() in losing_players:
            model.grid[0][0] = 3
        return model

    monkeypatch.setattr(game_mod, 'Tetris', seeded)
    game = TetrisGame.__new__(TetrisGame)
    game.mode = 'double'
    game.num_players = 2
    game.controls = 'classic'
    game.keymap = None
    game.keymaps = load_keymaps('double')
    game.audio = NullAudio()
    game.renderer = NullRenderer()
    game.screen = SimpleNamespace(copy=lambda: None)
    game.clock = SimpleNamespace(tick=lambda _: 10)
    game.effects = None
    game.bombs_enabled = True
    game._footnote = lambda _: None
    seen = []
    game._end_match = lambda entries, winner=None, lost=False: (seen.append((winner, lost)) or 'match_end')
    polls = []

    def event_get():
        polls.append(True)
        if len(polls) > 2:
            pytest.fail('Did not stop at first top-out')
        return []

    monkeypatch.setattr(pygame, 'event', SimpleNamespace(get=event_get), raising=False)
    monkeypatch.setattr(pygame, 'display', SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, 'draw', SimpleNamespace(rect=lambda *a: None), raising=False)
    assert game._run_match('none') == 'match_end'
    assert seen == [(expected_winner, False)]
    assert len(polls) == 1
    ko_events = [a for name, a in game.audio.events if name == 'play' and a and a[0] == 'ko']
    assert len(ko_events) == len(losing_players)


def test_one_player_topout_ends_match_without_waiting(monkeypatch):
    import game.tetris_game as mod
    actual = mod.Tetris

    def seeded(*args, **kwargs):
        obj = actual(*args, **kwargs)
        obj.grid[0][0] = 7
        return obj
    monkeypatch.setattr(mod, 'Tetris', seeded)
    game = TetrisGame.__new__(TetrisGame)
    game.mode = 'single'
    game.num_players = 1
    game.keymaps = load_keymaps('single')
    game.audio = NullAudio()
    game.renderer = NullRenderer()
    game.screen = SimpleNamespace(copy=lambda: None)
    game.clock = SimpleNamespace(tick=lambda _: 10)
    game.effects = None
    game._end_match = lambda entries, winner=None, lost=False: 'lost' if lost else 'unexpected'
    monkeypatch.setattr(pygame, 'event', SimpleNamespace(get=lambda: []), raising=False)
    assert game._run_match('none') == 'lost'


def test_double_ko_after_hard_drop_above_visible_ceiling(monkeypatch):
    """A human hard-drop lock above the ceiling ends 2P in that SAME frame."""
    import game.tetris_game as mod
    original = mod.Tetris

    def seeded(*args, **kwargs):
        obj = original(*args, **kwargs)
        if obj.get_id() == 0:
            obj.block = Piece('O', PIECES_DICT['O'])
            obj.px, obj.py = 4, -2
            obj.grid[5][1] = 2
            obj.grid[6][1] = 2
        return obj

    monkeypatch.setattr(mod, 'Tetris', seeded)
    game = TetrisGame.__new__(TetrisGame)
    game.mode = 'double'
    game.num_players = 2
    game.controls = 'classic'
    game.keymap = None
    game.keymaps = load_keymaps('double')
    game.audio = NullAudio()
    game.renderer = NullRenderer()
    game.screen = SimpleNamespace(copy=lambda: None)
    game.clock = SimpleNamespace(tick=lambda _: 10)
    game.effects = None
    game.bombs_enabled = True
    game._footnote = lambda _: None
    results = []
    game._end_match = lambda entries, winner=None, lost=False: (results.append(winner) or 'finish')
    polls = []

    def event_get():
        polls.append(True)
        return [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)] if len(polls) == 1 else []

    monkeypatch.setattr(pygame, 'event', SimpleNamespace(get=event_get), raising=False)
    monkeypatch.setattr(pygame, 'display', SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, 'draw', SimpleNamespace(rect=lambda *a: None), raising=False)
    assert game._run_match('none') == 'finish'
    assert results == [1]
    assert len(polls) == 1
