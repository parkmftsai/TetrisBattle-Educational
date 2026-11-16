"""Extract user-provided Tetris Battle Flash embedded MP3 sound resources.

No network requests. SWF DefineSound records are decoded from the supplied archive,
using SymbolClass/ExportAssets identifiers to preserve original asset names.  A
portable 22050 Hz mono 16-bit WAV sound pack is built using FFmpeg.  Designed
for private study of the supplied archive; inspect copyright before sharing.

Example:
    python tools/extract_fb_swf_audio.py --source-zip "/path/to/tetrisfb-assets-main.zip" --activate
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave
import zipfile
import zlib

MAIN = 'data1.81.0/flash/binary/FacebookMainframe.swf'
SONGS = {
    'battle_music.mp3': 'data1.81.0/flash/songs/BattleMp.mp3',
    'sprint_music.mp3': 'data1.81.0/flash/songs/SprintMp.mp3',
}
ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / 'TetrisBattle' / 'assets' / 'tetris sounds' / 'sfx_packs'
PACK_NAME = 'original_facebook'

# These event-to-asset assignments use the named Flash sound resources.
# FX_FALL / FX_TOSS meanings inferred from symbolic labels (not independently verified).
SOUND_MAP = {
    'rotate': 'FX_RTA01',
    'hard_drop': 'FX_HRDDP',
    'hold': 'FX_HOLD',
    'lock': 'FX_LCK01',
    'line_clear': 'FX_LNE01',
    'line_clear_2': 'FX_LNE02',
    'line_clear_3': 'FX_LNE03',
    'tetris': 'FX_LNE04',
    'tspin': 'FX_TSPIN',
    'soft_drop': 'FX_FALL',
    'attack': 'FX_TOSS',
    'bomb_explode': 'FX_BOMB01a',
    'bomb_chain': 'FX_BOMB02a',
    'bomb_chain_3': 'FX_BOMB03a',
    'bomb_chain_4': 'FX_BOMB04a',
    'win': 'FX_WIN',
    'lose': 'FX_LOSE',
    'ko': 'FX_KO',
    'menu': 'common.Entities.SoundMan_UiSoundMenuSelect',
    'pause': 'common.Entities.SoundMan_UiSoundConfirm',
    'combo': 'FX_COMBO01',
    **{'combo_{}'.format(n): 'FX_COMBO{:02d}'.format(min(n, 7)) for n in range(1, 11)},
}


def swf_tags(blob):
    if blob[:3] == b'CWS':
        data = blob[:8] + zlib.decompress(blob[8:])
    elif blob[:3] == b'FWS':
        data = blob
    else:
        raise ValueError('Unsupported Flash SWF header: {!r}'.format(blob[:3]))
    if len(data) < 12:
        raise ValueError('Truncated SWF')
    rect_len = (5 + 4 * (data[8] >> 3) + 7) // 8
    pos = 8 + rect_len + 4
    while pos + 2 <= len(data):
        info = int.from_bytes(data[pos:pos+2], 'little'); pos += 2
        kind, size = info >> 6, info & 63
        if size == 63:
            if pos + 4 > len(data):
                raise ValueError('Truncated extended tag')
            size = int.from_bytes(data[pos:pos+4], 'little'); pos += 4
        if pos + size > len(data):
            raise ValueError('Invalid SWF tag size')
        yield kind, data[pos:pos + size]
        pos += size
        if kind == 0:
            break


def embedded_sounds(blob):
    symbols, raw_audio = {}, {}
    for kind, data in swf_tags(blob):
        if kind in (56, 76):  # ExportAssets, SymbolClass
            if len(data) < 2:
                continue
            count = int.from_bytes(data[:2], 'little')
            pos = 2
            for _ in range(count):
                if pos + 2 > len(data):
                    raise ValueError('Invalid symbol mapping')
                sound_id = int.from_bytes(data[pos:pos+2], 'little');pos += 2
                end = data.find(b'\x00', pos)
                if end < 0:
                    raise ValueError('Unterminated symbol name')
                symbols[sound_id] = data[pos:end].decode('utf-8', 'replace')
                pos = end + 1
        if kind == 14:  # DefineSound
            if len(data) < 9:
                raise ValueError('Invalid DefineSound')
            sound_id = int.from_bytes(data[:2], 'little')
            sound_format = data[2] >> 4
            if sound_format != 2:
                continue  # only embedded MP3 supported by this importer
            sample_count = int.from_bytes(data[3:7], 'little')
            seek_samples = int.from_bytes(data[7:9], 'little', signed=True)
            raw_audio[sound_id] = (data[9:], sample_count, seek_samples)
    return {name: {'data': raw_audio[i][0], 'id': i,
                   'samples': raw_audio[i][1], 'seek_samples': raw_audio[i][2]}
            for i, name in symbols.items() if i in raw_audio}


def read_archive_entry(zf, relative):
    suffix = '/' + relative
    matches = [x for x in zf.namelist() if x == relative or x.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError('Expected exactly one {} in supplied zip, found {}'.format(relative, len(matches)))
    return zf.read(matches[0])


def convert_mp3_to_wav(audio, destination, ffmpeg='ffmpeg'):
    with tempfile.TemporaryDirectory(prefix='tetris_flash_sound_') as tmp:
        source = Path(tmp) / 'source.mp3'
        source.write_bytes(audio)
        command = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                   '-i', str(source), '-vn', '-ac', '1', '-ar', '22050', '-c:a',
                   'pcm_s16le', str(destination)]
        proc = subprocess.run(command, capture_output=True, text=True)
        if proc.returncode:
            raise RuntimeError('FFmpeg failed {}: {}'.format(destination.name, proc.stderr.strip()))
        with wave.open(str(destination), 'rb') as sound:
            if sound.getnframes() < 50 or sound.getnchannels() != 1 or sound.getsampwidth() != 2:
                raise RuntimeError('Invalid extracted wave: {}'.format(destination))
            return sound.getnframes() / sound.getframerate()


def extract(source_zip, output_root=PACKS, activate=False, overwrite=False, ffmpeg='ffmpeg'):
    if shutil.which(ffmpeg) is None:
        raise FileNotFoundError('FFmpeg executable not found: {}'.format(ffmpeg))
    source_zip = Path(source_zip).resolve()
    root = Path(output_root).resolve()
    target = root / PACK_NAME
    if target.exists() and not overwrite:
        raise FileExistsError('Sound pack already exists; pass --overwrite to replace: {}'.format(target))
    with zipfile.ZipFile(source_zip) as archive:
        sounds = embedded_sounds(read_archive_entry(archive, MAIN))
        missing = sorted(set(SOUND_MAP.values()) - set(sounds))
        if missing:
            raise ValueError('Missing expected SWF sounds: {}'.format(', '.join(missing)))
        with tempfile.TemporaryDirectory(prefix='tetris_flash_build_') as tmp:
            staging = Path(tmp) / PACK_NAME
            staging.mkdir()
            records = {}
            for event, symbol in SOUND_MAP.items():
                info = sounds[symbol]
                duration = convert_mp3_to_wav(info['data'], staging / (event + '.wav'), ffmpeg)
                records[event] = {'flash_symbol': symbol, 'swf_sound_id': info['id'],
                                  'duration_seconds': round(duration, 4),
                                  'reused_from_combo_7': event in ('combo_8', 'combo_9', 'combo_10'),
                                  'sha256': hashlib.sha256((staging / (event + '.wav')).read_bytes()).hexdigest()}
            # Preserve all 54 original sound definitions for later manual mapping.
            symbol_dir = staging / 'original_symbols'
            symbol_dir.mkdir()
            original_sounds = {}
            for symbol, info in sorted(sounds.items()):
                safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', symbol)
                path = symbol_dir / (safe_name + '.wav')
                duration = convert_mp3_to_wav(info['data'], path, ffmpeg)
                original_sounds[symbol] = {'file': 'original_symbols/' + path.name,
                                           'sound_id': info['id'],
                                           'duration_seconds': round(duration, 4)}
            for target_name, relative in SONGS.items():
                (staging / target_name).write_bytes(read_archive_entry(archive, relative))
            manifest = {
                'pack_name': PACK_NAME,
                'source_zip_name': source_zip.name,
                'source_swf': MAIN,
                'embedded_original_sound_symbols': len(sounds),
                'unique_events': len(records),
                'notes': [
                    'Original asset resources come from a user-provided Flash archive; usage rights not established.',
                    'Only seven distinct FX_COMBO01..FX_COMBO07 sounds are embedded; tiers 8-10 reuse 7.',
                    'Unmapped game events retain their previously bundled fallback sound effects.',
                    'Soft drop and attack use FX_FALL and FX_TOSS by name, subject to further game-code verification.',
                    'Original Flash music tracks are saved as battle_music.mp3 and sprint_music.mp3.',
                ],
                'events': records,
                'original_symbols': original_sounds,
            }
            (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(staging, target)
    if activate:
        (root / 'active_pack.json').write_text(json.dumps({'name': PACK_NAME}, indent=2) + '\n', encoding='utf-8')
    return target, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip', required=True, type=Path, help='Uploaded tetrisfb-assets zip')
    parser.add_argument('--output-root', type=Path, default=PACKS)
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args(argv)
    target, manifest = extract(args.source_zip, args.output_root, args.activate, args.overwrite, args.ffmpeg)
    print('Extracted {} WAV event files from {} original named SWF sounds'.format(
        len(manifest['events']), manifest['embedded_original_sound_symbols']))
    print('Pack:', target)
    print('Activated:', args.activate)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
