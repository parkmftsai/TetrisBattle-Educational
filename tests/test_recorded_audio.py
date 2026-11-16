"""Checks event-to-audio mapping and a real FFmpeg local-video extraction."""
import json
import shutil
import subprocess
import wave
from pathlib import Path

import pygame
import pytest

from TetrisBattle import audio
from tools.import_recorded_sfx import read_cues, main


def test_all_recorded_game_events_have_known_fallback():
    for name in audio.SFX_NAMES:
        path = audio.resolve_sfx_file(name, 'original')
        assert path.is_file()
    assert len(audio.ALL_SFX) == 38


def test_pack_selection_per_sound_and_active_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, 'SFX_PACKS_DIR', str(tmp_path))
    package = tmp_path / 'real_audio'
    package.mkdir()
    src = Path(audio.SFX_DIR) / 'bomb_explode.wav'
    (package / 'bomb_explode.wav').write_bytes(src.read_bytes())
    assert audio.resolve_sfx_file('bomb_explode', 'real_audio') == package / 'bomb_explode.wav'
    assert audio.resolve_sfx_file('rotate', 'real_audio') == Path(audio.SFX_DIR) / 'rotate.wav'
    (tmp_path / 'active_pack.json').write_text('{"name":"real_audio"}', encoding='utf8')
    assert audio.active_pack_name() == 'real_audio'
    assert audio.resolve_sfx_file('bomb_explode', 'auto') == package / 'bomb_explode.wav'
    sound_manager = audio.AudioManager(enabled=True, sfx_pack='auto')
    assert sound_manager.sound_sources['bomb_explode'] == str(package / 'bomb_explode.wav')
    assert sound_manager.sound_sources['rotate'] == str(Path(audio.SFX_DIR) / 'rotate.wav')
    assert sound_manager.load_sfx_pack('original') >= 34


@pytest.mark.parametrize('bad', ['../escape', '/tmp', 'xx:yy', '..\\evil', 'not okay', ''])
def test_reject_malicious_pack_paths(bad):
    with pytest.raises(ValueError):
        audio.resolve_sfx_file('rotate', bad)


def test_invalid_cues_are_rejected(tmp_path):
    local = Path(audio.SFX_DIR) / 'move.wav'
    path = tmp_path / 'cues.json'
    for obj in [
        {'events': {'not_a_sound': {'file': str(local)}}},
        {'events': {'move': {'file': str(local), 'start': 3, 'end': 2}}},
        {'events': {'move': {'file': 'https://third-party/video.mp4'}}},
        {'events': {'move': {'file': '/does/not/exist.mp4'}}},
    ]:
        path.write_text(json.dumps(obj), encoding='utf8')
        with pytest.raises((ValueError, FileNotFoundError)):
            read_cues(path)


def test_import_local_video_to_event_and_activate(tmp_path):
    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg not installed')
    # This tiny video is generated locally for testing; it is not a third-party
    # recording and therefore does not imply that real Tetris audio was ripped.
    video = tmp_path / 'testclip.mp4'
    src = Path(audio.SFX_DIR) / 'bomb_explode.wav'
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
           'color=c=black:s=32x32:r=25:d=0.70', '-i', str(src),
           '-t', '0.65', '-c:v', 'mpeg4', '-c:a', 'aac', str(video)]
    subprocess.run(cmd, check=True, capture_output=True)
    cues = tmp_path / 'cues.json'
    cues.write_text(json.dumps({'source_description': 'local generated test video',
                                 'license_or_permission': 'test only',
                                 'events': {'bomb_explode': {'start': 0.10, 'end': 0.54},
                                            'move': {'start': 0.0, 'end': 0.08}}}), encoding='utf8')
    output = tmp_path / 'packs'
    arguments = ['--cue-sheet', str(cues), '--input', str(video),
                 '--pack', 'test_recording', '--output-root', str(output), '--activate']
    assert main(arguments + ['--dry-run']) == 0
    assert not output.exists()
    # Explicit rights flag is required for import.
    with pytest.raises(SystemExit):
        main(arguments)
    assert main(arguments + ['--confirm-rights']) == 0
    for name in ('move', 'bomb_explode'):
        with wave.open(str(output / 'test_recording' / (name + '.wav'))) as clip:
            assert clip.getnchannels() == 1
            assert clip.getframerate() == 22050
            assert clip.getsampwidth() == 2
            assert clip.getnframes() > 500
    assert json.loads((output / 'active_pack.json').read_text())['name'] == 'test_recording'
    assert (output / 'test_recording' / 'recording_manifest.json').is_file()
    assert main(arguments + ['--confirm-rights']) == 1  # don't overwrite by default
    assert main(arguments + ['--confirm-rights', '--overwrite']) == 0
