"""Extract licensed/local recordings and bind them to TetrisBattle's game events.

Works with local videos, WAV, MP3, FLAC and OGG via FFmpeg. This tool neither
accesses YouTube nor downloads online audio. You are responsible for obtaining
permission to use the source audio before redistributing any resulting pack.

Example:
  python tools/import_recorded_sfx.py --input authorized_gameplay.mp4 \
      --cue-sheet audio_cues/my_cues.json --pack gameplay --confirm-rights --activate
  python tools/import_recorded_sfx.py --cue-sheet audio_cues/cc0_clips.json \
      --pack cc0 --confirm-rights --activate
"""
import argparse
import array
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

EVENTS = (
    'move', 'rotate', 'hard_drop', 'hold', 'lock', 'line_clear',
    'tetris', 'combo', 'attack', 'warning', 'ko', 'win', 'lose',
    'pause', 'menu', 'soft_drop', 'tspin', 'back_to_back',
    'perfect_clear', 'bomb_ready', 'bomb_arm', 'bomb_explode',
    'garbage_cancel', 'bomb_chain',
) + tuple('combo_{}'.format(i) for i in range(1, 11))
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$')
BASE = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = BASE / 'TetrisBattle/assets/tetris sounds/sfx_packs'


def read_cues(path, default_input=None):
    content = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(content, dict) or not isinstance(content.get('events'), dict):
        raise ValueError('Cue sheet must be a JSON object containing an events object')
    parsed = []
    for name, cue in content['events'].items():
        if name not in EVENTS:
            raise ValueError('Unknown TetrisBattle event: ' + name)
        if not isinstance(cue, dict):
            raise ValueError('Cue entry must be an object: ' + name)
        input_name = cue.get('file', default_input)
        if not isinstance(input_name, str) or not input_name.strip():
            raise ValueError('Missing local recording file for: ' + name)
        if '://' in input_name:
            raise ValueError('Use local recordings, not online URLs: ' + name)
        source = Path(input_name).expanduser()
        if not source.is_absolute():
            source = Path(path).resolve().parent / source
            if not source.is_file() and default_input == input_name:
                source = Path(input_name).resolve()
        if not source.is_file():
            raise FileNotFoundError('Recording not found for {}: {}'.format(name, source))
        start = cue.get('start', 0)
        end = cue.get('end')
        if isinstance(start, bool) or not isinstance(start, (int, float)) or start < 0 or start > 24*3600:
            raise ValueError('Invalid start time for: ' + name)
        if end is not None:
            if isinstance(end, bool) or not isinstance(end, (int, float)) or end <= start:
                raise ValueError('Invalid end time for: ' + name)
            if end - start < .04 or end - start > 12:
                raise ValueError('Clip length must be 0.04–12 seconds: ' + name)
        elif source.suffix.lower() in ('.mp4', '.webm', '.mkv', '.mov', '.avi'):
            raise ValueError('Video clips require start/end times: ' + name)
        parsed.append((name, source, float(start), None if end is None else float(end)))
    if not parsed:
        raise ValueError('No events selected; fill at least one event in your cue sheet')
    return content, parsed


def convert_recording(source, start, end, target):
    """Decode a local recording; trim, filter rumble, fade; write 22.05kHz PCM WAV."""
    fade = .016 if end is None else min(.016, (end - start) / 5)
    audio_filters = ['highpass=f=55']
    if start or end is not None:
        audio_filters.append('afade=t=in:st=0:d={:.4f}'.format(fade))
    if end is not None:
        duration = end - start
        audio_filters.append('afade=t=out:st={:.4f}:d={:.4f}'.format(duration - fade, fade))
    audio_filters.append('alimiter=limit=0.96')
    cmd = ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error', '-y']
    if start:
        cmd += ['-ss', str(start)]
    cmd += ['-i', str(source)]
    if end is not None:
        cmd += ['-t', str(end - start)]
    cmd += ['-map', '0:a:0', '-vn', '-af', ','.join(audio_filters),
            '-ac', '1', '-ar', '22050', '-sample_fmt', 's16',
            '-c:a', 'pcm_s16le', str(target)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        raise RuntimeError('FFmpeg is required: install ffmpeg and add it to PATH') from exc
    if result.returncode:
        raise RuntimeError('FFmpeg decoding {} failed: {}'.format(source.name, result.stderr[-600:]))
    with wave.open(str(target), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 22050):
            raise RuntimeError('FFmpeg produced unexpected audio format')
        if audio.getnframes() < 100:
            raise RuntimeError('Extracted clip was empty or too short')
        if audio.getnframes() / 22050 > 12.5:
            raise RuntimeError('Sound clip is too long (max 12 seconds)')
        samples = array.array('h')
        samples.frombytes(audio.readframes(audio.getnframes()))
    if sys.byteorder != 'little':
        samples.byteswap()
    peak = max(abs(int(s)) for s in samples)
    if peak == 0:
        raise RuntimeError('Recording contains only silence')
    # Normalize to -3dB peak; protects the 23-effect mix from loud distorted clips.
    factor = min(5.0, 23170.0 / peak)
    if factor != 1.0:
        normalized = array.array('h', (max(-32768, min(32767, round(x * factor))) for x in samples))
        if sys.byteorder != 'little':
            normalized.byteswap()
        with wave.open(str(target), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(22050)
            audio.writeframes(normalized.tobytes())


def main(argv=None):
    parser = argparse.ArgumentParser(description='Import permitted local video/audio SFX into TetrisBattle')
    parser.add_argument('--cue-sheet', help='JSON cue sheet mapping events to local files and time ranges')
    parser.add_argument('--input', help='Default local video/audio file for cues without file field')
    parser.add_argument('--pack', default='recorded', help='New audio pack name (letters/digits/_/-)')
    parser.add_argument('--output-root', default=str(DEFAULT_OUTPUT), help=argparse.SUPPRESS)
    parser.add_argument('--activate', action='store_true', help='Use the pack by default next time the game runs')
    parser.add_argument('--confirm-rights', action='store_true', help='Confirm rights to use and distribute the audio')
    parser.add_argument('--overwrite', action='store_true', help='Allow updating existing pack recordings')
    parser.add_argument('--dry-run', action='store_true', help='Validate and show mappings, without writing audio')
    parser.add_argument('--list-events', action='store_true', help='List all supported event names')
    args = parser.parse_args(argv)
    if args.list_events:
        print('\n'.join(EVENTS))
        return 0
    if not NAME_RE.fullmatch(args.pack):
        parser.error('Invalid --pack name')
    if not args.cue_sheet:
        parser.error('Pass --cue-sheet or --list-events')
    try:
        sheet, cues = read_cues(args.cue_sheet, args.input)
        if args.dry_run:
            for name, src, start, end in cues:
                print('{} <- {} [{:.3f}, {}]'.format(name, src, start, end or 'end'))
            return 0
        if not args.confirm_rights:
            parser.error('Audio reproduction requires --confirm-rights (you must have permission)')
        if not shutil.which('ffmpeg'):
            raise RuntimeError('FFmpeg not found in PATH')
        output_root = Path(args.output_root).resolve()
        destination = output_root / args.pack
        if destination.exists() and not args.overwrite:
            raise FileExistsError('Pack already exists; use --overwrite to add/replace recordings')
        with tempfile.TemporaryDirectory(prefix='tetris-recording-') as temp:
            for name, src, start, end in cues:
                target = Path(temp) / (name + '.wav')
                convert_recording(src, start, end, target)
                print('OK {} <- {}'.format(name, src.name))
            destination.mkdir(parents=True, exist_ok=True)
            for name, *_ in cues:
                os.replace(str(Path(temp) / (name + '.wav')), str(destination / (name + '.wav')))
        metadata = {
            'pack': args.pack,
            'source_description': sheet.get('source_description', ''),
            'license_or_permission': sheet.get('license_or_permission', ''),
            'original_audio_copied_without_reencoding': False,
            'events': {name: {'source_filename': src.name, 'start': start, 'end': end}
                       for name, src, start, end in cues},
            'note': 'Recordings are not Tetris official audio unless licensed and provided by the user.',
        }
        (destination / 'recording_manifest.json').write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        if args.activate:
            (output_root / 'active_pack.json').write_text(
                json.dumps({'name': args.pack}, indent=2), encoding='utf-8')
        print('Imported {} recorded sound(s) into {}'.format(len(cues), destination))
        if not args.activate:
            print('Play with: python -m game.tetris_game --sfx-pack {}'.format(args.pack))
    except (ValueError, OSError, RuntimeError) as exc:
        print('ERROR: {}'.format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
