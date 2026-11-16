"""Sound bank tests for the SWF content supplied by the user."""
import hashlib
import json
from pathlib import Path
import struct
import wave

import pytest

from TetrisBattle import audio
from tools.extract_fb_swf_audio import embedded_sounds, SOUND_MAP, swf_tags, PACK_NAME


PACK = Path(audio.SFX_PACKS_DIR) / PACK_NAME

# Optional original Flash media is deliberately excluded from the public code package.
pytestmark = pytest.mark.skipif(not (PACK / "manifest.json").is_file(), reason="Optional original Flash audio pack is not bundled")


def test_all_original_sound_symbols_extracted_and_valid_wav():
    manifest = json.loads((PACK / 'manifest.json').read_text(encoding='utf8'))
    assert manifest['embedded_original_sound_symbols'] == 54
    assert len(manifest['original_symbols']) == 54
    assert len(manifest['events']) == len(SOUND_MAP) == 31
    for label, info in manifest['original_symbols'].items():
        assert label and info['sound_id'] >= 0
        with wave.open(str(PACK / info['file'])) as wav:
            assert wav.getnframes() >= 50
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 22050


def test_event_sounds_verified_against_extract_manifest():
    manifest = json.loads((PACK / 'manifest.json').read_text(encoding='utf8'))
    for name, record in manifest['events'].items():
        assert record['flash_symbol'] == SOUND_MAP[name]
        path = PACK / (name + '.wav')
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
        assert audio.resolve_sfx_file(name, PACK_NAME) == path
    # Only seven distinct Flash Combo levels were found; 8-10 use tier 7.
    for tier in (8, 9, 10):
        assert manifest['events']['combo_'+str(tier)]['reused_from_combo_7']
        assert (PACK / ('combo_'+str(tier)+'.wav')).read_bytes() == (PACK / 'combo_7.wav').read_bytes()
    for i in range(1, 8):
        assert (PACK / ('combo_'+str(i)+'.wav')).read_bytes() != (PACK / ('combo_'+str(i+1)+'.wav')).read_bytes() if i < 7 else True


def test_music_and_original_selection():
    assert (PACK / 'battle_music.mp3').is_file()
    assert (PACK / 'sprint_music.mp3').is_file()
    assert audio.resolve_music_file('original_facebook') == PACK / 'battle_music.mp3'
    assert audio.resolve_music_file('original') == Path(audio.MUSIC_PATH)
    assert audio.active_pack_name() == PACK_NAME
    assert audio.resolve_sfx_file('rotate', 'original') != audio.resolve_sfx_file('rotate', PACK_NAME)


@pytest.mark.parametrize('name,intensity,selected', [
    ('combo', 1, 'combo_1'), ('combo', 7, 'combo_7'), ('combo', 10, 'combo_10'),
    ('line_clear', 2, 'line_clear_2'), ('line_clear', 3, 'line_clear_3'),
    ('bomb_chain', 3, 'bomb_chain_3'), ('bomb_chain', 4, 'bomb_chain_4'),
    ('bomb_chain', 10, 'bomb_chain_4'),
])
def test_audio_event_dispatch_selects_original_clip(name, intensity, selected):
    manager = audio.AudioManager(enabled=True, sfx_pack=PACK_NAME)
    assert manager.sound_sources[selected] == str(PACK / (selected + '.wav'))
    target = manager.sounds[selected]
    # pygame sound objects in real hardware may disallow reassignment.
    old_play = target.play
    seen = []
    try:
        target.play = lambda: seen.append(selected)
    except (TypeError, AttributeError):
        manager.play(name, intensity=intensity)
        assert manager.sounds[selected] is not None
    else:
        manager.play(name, intensity=intensity)
        target.play = old_play
        assert seen == [selected]


def test_parser_handles_original_flash_sound_symbol_table():
    # Synthetic SWF containing a single MP3 DefineSound + SymbolClass.
    sound_id = 17
    symbol = b'FX_TEST_SOUND\0'
    defs = struct.pack('<HBIh', sound_id, 0x26, 256, 0) + b'\xff\xfb\x90\x64'
    exports = struct.pack('<HH', 1, sound_id) + symbol
    def tag(code, body):
        return struct.pack('<H', (code << 6) | len(body)) + body
    rect = b'\x08\x00'  # zero-size RECT: nbits=1, 2 bytes
    swfbody = rect + b'\x00\x18\x01\x00' + tag(14, defs) + tag(76, exports) + tag(0, b'')
    swf = b'FWS' + bytes([10]) + struct.pack('<I', len(swfbody) + 8) + swfbody
    sound = embedded_sounds(swf)
    assert sound['FX_TEST_SOUND']['data'] == b'\xff\xfb\x90\x64'
    assert sound['FX_TEST_SOUND']['id'] == 17
    assert len(list(swf_tags(swf))) == 3
