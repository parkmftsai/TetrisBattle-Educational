"""Regression test for NameError: BOMB_CELL in the human-play status HUD.

The pre-fix test suite bypassed the HUD by using TetrisGame.__new__ without
setting `_small_font`. Keep the actual status draw path enabled here.
"""
from types import SimpleNamespace
import pygame
import pytest

from game.tetris_game import TetrisGame
from TetrisBattle.settings import BOMB_CELL
from TetrisBattle.tetris import Tetris, Player
from TetrisBattle.controls import load_keymaps


def make_model(*, bombs_enabled=True):
    return Tetris(Player(load_keymaps('single')[0]), 'none',
                  bombs_enabled=bombs_enabled, modern_controls=True)


@pytest.mark.parametrize('bombs_enabled', [True, False])
def test_bomb_counter_in_status_draw_without_nameerror(bombs_enabled):
    model = make_model(bombs_enabled=bombs_enabled)
    model.grid[3][-1] = BOMB_CELL
    model.grid[3][-2] = BOMB_CELL
    game = TetrisGame.__new__(TetrisGame)
    game._small_font = object()
    panels = []
    labels = []
    game._panel = lambda *args: panels.append(args)
    game._text = lambda *args, **kwargs: labels.append(args[0])

    game._draw_status([{'tetris': model}])

    assert len(panels) == 1
    assert any(label.startswith('LINES ') for label in labels)
    if bombs_enabled:
        assert any('BOMBS 2 (AUTO)' in label for label in labels)
    else:
        assert 'SOLID GARBAGE (NO BOMBS)' in labels


@pytest.mark.parametrize('mode', ['single', 'double'])
def test_hud_executes_in_real_match_loop(monkeypatch, mode):
    """Exercise first active game frame rather than only testing a HUD helper."""
    class FakeRenderer:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    class FakeAudio:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    game = TetrisGame.__new__(TetrisGame)
    game.mode = mode
    game.num_players = 1 if mode == 'single' else 2
    game.keymaps = load_keymaps(mode)
    game.audio = FakeAudio()
    game.renderer = FakeRenderer()
    game.screen = SimpleNamespace(copy=lambda: None)
    game.clock = SimpleNamespace(tick=lambda value: value)
    game.effects = None
    game.bombs_enabled = True
    game._small_font = object()
    game._panel = lambda *args, **kwargs: None
    hud_text = []
    game._text = lambda label, *args, **kwargs: hud_text.append(label)
    game._footnote = lambda *args: None
    events = iter([[], [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)]])
    monkeypatch.setattr(pygame, 'event', SimpleNamespace(get=lambda: next(events, [])), raising=False)
    monkeypatch.setattr(pygame, 'display', SimpleNamespace(flip=lambda: None), raising=False)
    monkeypatch.setattr(pygame, 'draw', SimpleNamespace(rect=lambda *args: None), raising=False)

    assert game._run_match('none') == 'menu'
    assert sum(label.startswith('LINES ') for label in hud_text) == game.num_players
    assert sum('BOMBS ' in label for label in hud_text) == game.num_players
