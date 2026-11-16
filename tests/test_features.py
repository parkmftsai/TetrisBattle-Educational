import json
import wave
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.audio import AudioManager, SFX_NAMES, ALL_SFX, SFX_DIR
from TetrisBattle.controls import load_keymaps, describe_keymaps
from TetrisBattle.settings import PIECES_DICT
from TetrisBattle.tetris import Tetris, Player, Piece


def keys_for(binding):
    return set(binding) if isinstance(binding, (tuple, list)) else {binding}


def test_original_classic_keys_preserved_and_extended():
    player1, player2 = load_keymaps("double")
    assert pygame.key.key_code("c") in keys_for(player1["hold"])
    assert pygame.key.key_code("space") in keys_for(player1["drop"])
    assert pygame.key.key_code("up") in keys_for(player1["rotate_right"])
    assert pygame.key.key_code("z") in keys_for(player1["rotate_left"])
    assert pygame.key.key_code("x") in keys_for(player1["rotate_right"])
    assert pygame.key.key_code("e") in keys_for(player2["hold"])
    assert pygame.key.key_code("w") in keys_for(player2["drop"])
    assert pygame.key.key_code("u") in keys_for(player2["rotate_right"])
    assert pygame.key.key_code("q") in keys_for(player2["rotate_left"])
    assert pygame.key.key_code("i") in keys_for(player2["rotate_right"])
    assert pygame.key.key_code("h") in keys_for(player2["left"])
    assert pygame.key.key_code("k") in keys_for(player2["right"])
    assert pygame.key.key_code("j") in keys_for(player2["down"])
    assert len(describe_keymaps([player1, player2])) == 2


def test_wasd_presets_and_mode_constraint():
    mapping = load_keymaps("single", "wasd")[0]
    assert pygame.key.key_code("a") in keys_for(mapping["left"])
    assert pygame.key.key_code("d") in keys_for(mapping["right"])
    assert pygame.key.key_code("s") in keys_for(mapping["down"])
    assert pygame.key.key_code("w") in keys_for(mapping["rotate_right"])
    with pytest.raises(ValueError, match="single-player"):
        load_keymaps("double", "wasd")


def test_json_override_and_conflict_validation(tmp_path):
    path = tmp_path / "keys.json"
    path.write_text(json.dumps({"single": {"p1": {"left": "a"}}}), encoding="utf8")
    result = load_keymaps("single", config_path=path)[0]
    assert result["left"] == pygame.key.key_code("a")
    path.write_text(json.dumps({"double": {"p1": {"left": ["h"]}}}), encoding="utf8")
    with pytest.raises(ValueError, match="assigned to both"):
        load_keymaps("double", config_path=path)
    path.write_text(json.dumps({"single": {"p1": {"right": "p"}}}), encoding="utf8")
    with pytest.raises(ValueError, match="reserved shortcut"):
        load_keymaps("single", config_path=path)
    path.write_text(json.dumps({"single": {"p1": {"right": "unknown key"}}}), encoding="utf8")
    with pytest.raises(ValueError, match="Unknown pygame key"):
        load_keymaps("single", config_path=path)


def test_player_actions_and_audio_events():
    first = Tetris(Player(load_keymaps("single")[0]), "none")
    first.block = Piece("T", PIECES_DICT["T"])
    calls = []
    first.on_event = calls.append
    first.LAST_ROTATE_TIME = 100
    original_rotation = first.block.current_shape_id
    first.trigger(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code("x")))
    assert first.block.current_shape_id != original_rotation
    assert "rotate" in calls

    first.LAST_MOVE_SHIFT_TIME = 100
    start_x = first.px
    first.trigger(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code("right")))
    first.move()
    assert first.px == start_x + 1
    assert "move" in calls
    first.trigger(SimpleNamespace(type=pygame.KEYUP, key=pygame.key.key_code("right")))
    assert first.pressedRight is False
    first.trigger(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.key.key_code("c")))
    assert first.held is not None
    assert "hold" in calls
    first.trigger(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE))
    assert "hard_drop" in calls
    assert first.check_fallen() is True
    assert "lock" in calls
    first.release_movement()
    assert first.pressedRight is first.pressedLeft is first.pressedDown is False


def test_scoring_attack_and_tetris_events():
    tetris = Tetris(Player(load_keymaps("single")[0]), "none")
    calls = []
    tetris.on_event = calls.append
    tetris.add_attacked(2)
    assert "warning" in calls
    tetris.clear()
    assert tetris.attacked == 0
    for x in range(10):
        for y in (-1, -2, -3, -4):
            tetris.grid[x][y] = 2
    scores = tetris.clear()
    assert scores >= 4
    assert tetris.cleared == 4
    assert "tetris" in calls


def test_audio_manager_and_control_hotkeys():
    sound = AudioManager(enabled=True)
    assert sound.available
    assert len(sound.sounds) == len(ALL_SFX)
    sound.play("rotate")
    assert sound.sounds["rotate"].get_volume() >= 0 if hasattr(sound.sounds["rotate"], "get_volume") else sound.sounds["rotate"].count == 1
    sound.start_music()
    sound.pause_music(True)
    sound.pause_music(False)
    assert sound.toggle_sfx() is False
    assert sound.toggle_sfx() is True
    assert sound.toggle_music() is False
    assert sound.toggle_music() is True
    sound.adjust_volume(-100)
    assert sound.music_volume == sound.sfx_volume == 0.0
    sound.adjust_volume(100)
    assert sound.music_volume == sound.sfx_volume == 1.0
    sound.stop_music()
    assert AudioManager(enabled=False).available is False


@pytest.mark.parametrize("name", SFX_NAMES)
def test_generated_wav_is_valid(name):
    path = Path(SFX_DIR) / (name + ".wav")
    assert path.is_file()
    with wave.open(str(path)) as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 22050
        assert wav.getnframes() > 300
        assert len(wav.readframes(10)) == 20


def test_game_entrypoint_can_import_and_timer_ticks_once():
    from game.tetris_game import TetrisGame
    obj = TetrisGame.__new__(TetrisGame)
    assert obj.update_time(1000.0) == 990.0
    assert obj.update_time(0) == 0


def test_audio_falls_back_when_device_is_unavailable(monkeypatch):
    def fail():
        raise pygame.error("No audio output device")

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    monkeypatch.setattr(pygame.mixer, "init", fail)
    audio = AudioManager(enabled=True)
    assert audio.available is False
    audio.play("rotate")   # No exception; the game remains usable silently.
    audio.start_music()
    audio.stop_music()
