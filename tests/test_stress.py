"""Deterministic, high-volume state-machine stress test without SDL."""
import random
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.controls import load_keymaps
from TetrisBattle.tetris import Tetris, Player
from TetrisBattle.settings import GRID_WIDTH


@pytest.mark.parametrize("map_name", ["none", "classic", "comboking", "lunchbox"])
def test_bomb_gameplay_stays_in_bounds_over_randomized_pieces(map_name):
    rng = random.Random(101)
    model = Tetris(Player(load_keymaps("single")[0]), map_name, bombs_enabled=True)
    options = ["left", "right", "down", "up", "x", "z", "c", "space"]
    events_seen = []
    model.on_event = events_seen.append
    for _ in range(1600):
        if rng.random() < .27:
            chosen = rng.choice(options)
            model.trigger(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code(chosen)))
        if rng.random() < .21:
            chosen = rng.choice(["left", "right", "down"])
            model.trigger(SimpleNamespace(type=pygame.KEYUP, key=pygame.key.key_code(chosen)))
        model.natural_down()
        model.move()
        if model.check_fallen():
            model.clear()
            if model.check_KO():
                model.clear_garbage()
            model.new_block()
        model.increment_timer()
        assert len(model.grid) == GRID_WIDTH
        assert len({len(column) for column in model.grid}) == 1
        assert all(isinstance(cell, int) and 0 <= cell <= 9 for col in model.grid for cell in col)
        assert model.bomb_charges == 0
        assert model.attack_outgoing >= 0
    assert "hard_drop" in events_seen
    assert "bomb_arm" not in events_seen
