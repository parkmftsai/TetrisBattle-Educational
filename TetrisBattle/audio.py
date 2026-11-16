"""Optional recorded-audio packs with reliable fallback to bundled sounds.

Pack layout:
  assets/tetris sounds/sfx/                 bundled fallback (original + tiered Combo WAVs)
  assets/tetris sounds/sfx_packs/<name>/    licensed recordings (partial sets OK)
  assets/tetris sounds/sfx_packs/active_pack.json

Flash assets from the user-supplied archive are stored separately in a selectable pack.
Confirm rights before redistributing third-party game resources.
"""
import json
import os
import re
import time
from pathlib import Path

import pygame

from .settings import MUSIC_PATH, ROOT

SFX_DIR = os.path.join(ROOT, "assets", "tetris sounds", "sfx")
SFX_PACKS_DIR = os.path.join(ROOT, "assets", "tetris sounds", "sfx_packs")
SFX_NAMES = (
    "move", "rotate", "hard_drop", "hold", "lock", "line_clear",
    "tetris", "combo", "attack", "warning", "ko", "win", "lose",
    "pause", "menu", "soft_drop", "tspin", "back_to_back",
    "perfect_clear", "bomb_ready", "bomb_arm", "bomb_explode",
    "garbage_cancel", "bomb_chain",
)
COMBO_VARIANTS = tuple("combo_{}".format(n) for n in range(1, 11))
EXTENDED_SFX = ('line_clear_2', 'line_clear_3', 'bomb_chain_3', 'bomb_chain_4')
ALL_SFX = SFX_NAMES + COMBO_VARIANTS + EXTENDED_SFX
PACK_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
# Quiet repeated movement input, but never suppress important one-shot events.
SFX_COOLDOWN = {"move": 0.028, "soft_drop": 0.065, "warning": 0.15}


def active_pack_name(packs_dir=None):
    path = Path(packs_dir or SFX_PACKS_DIR) / "active_pack.json"
    try:
        name = json.loads(path.read_text(encoding="utf-8")).get("name")
        return name if isinstance(name, str) and PACK_NAME.fullmatch(name) else None
    except (OSError, ValueError, TypeError):
        return None


def resolve_sfx_file(name, pack="auto", fallback_dir=None, packs_dir=None):
    """Resolve an explicitly named event, never a path supplied by gameplay."""
    if name not in ALL_SFX:
        raise ValueError("Unknown sound event: {}".format(name))
    root = Path(packs_dir or SFX_PACKS_DIR)
    if pack == "auto" or pack is None:
        pack = active_pack_name(root)
    if pack not in ("original", "default", "none") and pack is not None:
        if not isinstance(pack, str) or not PACK_NAME.fullmatch(pack):
            raise ValueError("Invalid audio pack name: {!r}".format(pack))
        replacement = root / pack / (name + ".wav")
        if replacement.is_file():
            return replacement
        # A licensed one-sound combo recording may serve all tiers, while
        # per-tier recordings override it when the user imports them.
        if name in COMBO_VARIANTS:
            base_combo = root / pack / "combo.wav"
            if base_combo.is_file():
                return base_combo
    return Path(fallback_dir or SFX_DIR) / (name + ".wav")


def resolve_music_file(pack="auto", packs_dir=None):
    """Prefer original Flash BattleMp in the selected pack when available."""
    root = Path(packs_dir or SFX_PACKS_DIR)
    if pack == "auto" or pack is None:
        pack = active_pack_name(root)
    if pack in (None, "original", "default", "none"):
        return Path(MUSIC_PATH)
    if not isinstance(pack, str) or not PACK_NAME.fullmatch(pack):
        raise ValueError("Invalid audio pack name: {!r}".format(pack))
    source = root / pack / "battle_music.mp3"
    return source if source.is_file() else Path(MUSIC_PATH)


class AudioManager:
    def __init__(self, enabled=True, music_volume=0.30, sfx_volume=0.55,
                 sfx_pack="auto"):
        self.enabled = bool(enabled)
        self.music_enabled = bool(enabled)
        self.sfx_enabled = bool(enabled)
        self.music_volume = max(0.0, min(1.0, float(music_volume)))
        self.sfx_volume = max(0.0, min(1.0, float(sfx_volume)))
        self.sfx_pack = sfx_pack
        self.sounds = {}
        self.sound_sources = {}
        self.available = False
        self._music_loaded = False
        self._paused = False
        self._last_trigger = {}
        if not self.enabled:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels()))
            self.available = True
        except pygame.error as exc:
            print("[AUDIO] Sound device unavailable; continuing without audio: {}".format(exc))
            return
        self.load_sfx_pack(sfx_pack)

    def load_sfx_pack(self, pack="auto"):
        """Reload a recorded sound bank and fall back individually if missing/bad."""
        self.sfx_pack = pack
        self.sounds = {}
        self.sound_sources = {}
        self._last_trigger.clear()
        self._music_loaded = False  # Refresh track when changing the audio pack.
        if not self.available:
            return 0
        for name in ALL_SFX:
            preferred = resolve_sfx_file(name, pack)
            options = [preferred]
            fallback = Path(SFX_DIR) / (name + ".wav")
            if preferred != fallback:
                options.append(fallback)
            for path in options:
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(self.sfx_volume)
                    self.sounds[name] = sound
                    self.sound_sources[name] = str(path)
                    break
                except (pygame.error, OSError) as exc:
                    print("[AUDIO] Failed to load {} from {}: {}".format(name, path, exc))
        return len(self.sounds)

    def play(self, name, player_index=None, intensity=None):
        """Play one in-game event; ignore invalid/unknown names and audio outages."""
        if not (self.available and self.sfx_enabled):
            return
        selected = name
        if name == "combo" and intensity is not None:
            selected = "combo_{}".format(max(1, min(10, int(intensity))))
        elif name == "line_clear" and intensity is not None and int(intensity) in (2, 3):
            selected = "line_clear_{}".format(int(intensity))
        elif name == "bomb_chain" and intensity is not None and int(intensity) >= 3:
            selected = "bomb_chain_{}".format(min(4, int(intensity)))
        sound = self.sounds.get(selected) or self.sounds.get(name)
        if sound is None:
            return
        cooldown = SFX_COOLDOWN.get(name)
        if cooldown:
            now = time.monotonic()
            if now - self._last_trigger.get((name, player_index), -1e9) < cooldown:
                return
            self._last_trigger[(name, player_index)] = now
        try:
            sound.play()
        except pygame.error:
            pass

    def start_music(self):
        if not self.available:
            return
        try:
            if not self._music_loaded:
                pygame.mixer.music.load(str(resolve_music_file(self.sfx_pack)))
                self._music_loaded = True
            pygame.mixer.music.set_volume(self.music_volume)
            if self.music_enabled:
                pygame.mixer.music.play(-1)
            self._paused = False
        except (pygame.error, OSError) as exc:
            print("[AUDIO] Background music unavailable: {}".format(exc))

    def stop_music(self):
        if self.available:
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
        self._paused = False

    def pause_music(self, paused):
        if self.available:
            try:
                (pygame.mixer.music.pause if paused else pygame.mixer.music.unpause)()
                self._paused = paused
            except pygame.error:
                pass

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        if not self.available:
            return self.music_enabled
        try:
            if self.music_enabled:
                if not self._music_loaded:
                    self.start_music()
                elif not pygame.mixer.music.get_busy():
                    pygame.mixer.music.play(-1)
                if self._paused:
                    pygame.mixer.music.pause()
            else:
                pygame.mixer.music.stop()
        except pygame.error:
            pass
        return self.music_enabled

    def toggle_sfx(self):
        self.sfx_enabled = not self.sfx_enabled
        return self.sfx_enabled

    def adjust_volume(self, delta):
        self.music_volume = max(0.0, min(1.0, round(self.music_volume + delta, 2)))
        self.sfx_volume = max(0.0, min(1.0, round(self.sfx_volume + delta, 2)))
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)
        if self.available:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except pygame.error:
                pass
        return self.music_volume, self.sfx_volume
