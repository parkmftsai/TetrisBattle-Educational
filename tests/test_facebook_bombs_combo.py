"""Additional original-Battle bomb and multi-tier Combo regression tests.

The YouTube clip itself is not present in this test suite; sounds are
placeholder WAVs created by generate_combo_sfx.py, not extracted media.
"""
from pathlib import Path
import wave

import pytest

from TetrisBattle.audio import AudioManager, COMBO_VARIANTS, SFX_DIR, resolve_sfx_file
from TetrisBattle.controls import load_keymaps
from TetrisBattle.settings import GRID_WIDTH
from TetrisBattle.tetris import Player, Tetris


def make_board():
    return Tetris(Player(load_keymaps("single")[0]), "none", bombs_enabled=True)


@pytest.mark.parametrize("rows,expected_attack", [(1, 0), (2, 1), (3, 2), (4, 3)])
def test_bomb_chain_attack_table(rows, expected_attack):
    model = make_board()
    model.build_garbage(model.grid, rows, [4] * rows)
    contact = [(4, GRID_WIDTH + 9 - rows)]  # row above the topmost bomb (row 20-rows-1)
    # Correct row index is 19-rows for a 20-row board.
    contact = [(4, len(model.grid[0]) - rows - 1)]
    assert model.detonate_contact_bombs(contact) == rows
    assert model.clear() == 0
    assert model.attack_outgoing == expected_attack
    assert not any(cell in (8, 9) for col in model.grid for cell in col)


def test_bomb_chain_can_cancel_pending_attack_instead_of_double_spending():
    model = make_board()
    model.build_garbage(model.grid, 3, [4, 4, 4])
    model.add_attacked(1)
    model.detonate_contact_bombs([(4, 16)])
    model.clear()
    assert model.garbage_cancelled == 1
    assert model.attack_outgoing == 1
    assert model.attacked == 0
    assert model.sent == 1


def test_misaligned_bombs_do_not_chain_unrelated_rows():
    model = make_board()
    model.build_garbage(model.grid, 3, [4, 5, 4])
    assert model.detonate_contact_bombs([(4, 16)]) == 1
    assert model.grid[5][-2] == 9
    assert sum(cell == 9 for col in model.grid for cell in col) == 2


def test_combo_levels_produce_distinct_wav_clips():
    unique = set()
    for name in COMBO_VARIANTS:
        with wave.open(str(Path(SFX_DIR) / (name + '.wav')), 'rb') as wav:
            assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (22050, 1, 2)
            unique.add(wav.readframes(wav.getnframes()))
    assert len(COMBO_VARIANTS) == 10
    assert len(unique) == 10


def test_combo_audio_routes_by_level_instead_of_repeating_same_sound():
    manager = AudioManager(enabled=True, sfx_pack="original")
    assert all(name in manager.sounds for name in COMBO_VARIANTS)
    # Tests use a minimal pygame sound fake unless real pygame is installed.
    seen = []
    for level in (1, 3, 7, 10, 15):
        selected = manager.sounds['combo_{}'.format(min(level, 10))]
        original_play = selected.play
        try:
            selected.play = (lambda level=level: seen.append(level))
        except (AttributeError, TypeError):
            # Real pygame's C Sound objects do not permit monkeypatching.
            assert manager.sound_sources['combo_{}'.format(min(level, 10))].endswith('.wav')
            manager.play('combo', intensity=level)
        else:
            manager.play('combo', intensity=level)
            selected.play = original_play
    if seen:
        assert seen == [1, 3, 7, 10, 15]


def test_recorded_combo_base_and_custom_tier_precedence(tmp_path):
    pack = tmp_path / 'legal_recording'
    pack.mkdir()
    (pack / 'combo.wav').write_bytes((Path(SFX_DIR) / 'combo.wav').read_bytes())
    (pack / 'combo_4.wav').write_bytes((Path(SFX_DIR) / 'combo_4.wav').read_bytes())
    assert resolve_sfx_file('combo_2', pack='legal_recording', packs_dir=tmp_path) == pack / 'combo.wav'
    assert resolve_sfx_file('combo_4', pack='legal_recording', packs_dir=tmp_path) == pack / 'combo_4.wav'


def test_ko_garbage_cleanup_removes_all_multi_line_garbage():
    model = make_board()
    model.build_garbage(model.grid, 4, [2, 2, 5, 5])
    model.clear_garbage()
    assert sum(cell in (8, 9) for col in model.grid for cell in col) == 0
    assert all(len(col) == 20 for col in model.grid)


def test_bomb_rows_are_generated_by_actual_opponent_attack():
    p1, p2 = (Tetris(Player(mapping), 'none', bombs_enabled=True)
              for mapping in load_keymaps('double'))
    # A Tetris sends four rows to the opponent.
    for y in (-1, -2, -3, -4):
        for x in range(10):
            p1.grid[x][y] = 1
    assert p1.clear() >= 4
    p2.add_attacked(p1.attack_outgoing)
    p2.clear()  # Resolve the queued garbage after the receiver's next lock.
    bombs = [(x, y) for x in range(10) for y in range(20)
             if p2.grid[x][y] == 9]
    assert len(bombs) == 4
    assert all(len(col) == 20 for col in p2.grid)
