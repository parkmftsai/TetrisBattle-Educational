"""Lightweight, original TetrisBattle VFX drawn entirely with pygame.

Particles, bursts, announcements and flashes are visual only.  No image files,
threads, timing APIs or mutation of the game model are needed.  Simulation can
be paused without consuming effect duration.
"""
import math
import random
from pathlib import Path

import pygame

from .settings import GRID_DEPTH

BLOCK_PIXELS = 18
EVENTS = {
    "hard_drop": ("DROP!", (109, 211, 255), 5),
    "lock": ("", (156, 171, 193), 3),
    "line_clear": ("LINE CLEAR", (91, 222, 239), 14),
    "tetris": ("TETRIS!", (255, 224, 102), 29),
    "combo": ("COMBO!", (249, 119, 255), 13),
    "tspin": ("T-SPIN!", (176, 115, 255), 23),
    "back_to_back": ("BACK TO BACK!", (255, 197, 74), 19),
    "perfect_clear": ("PERFECT CLEAR!", (255, 255, 255), 37),
    "attack": ("ATTACK!", (255, 95, 111), 17),
    "warning": ("INCOMING!", (255, 65, 75), 12),
    "ko": ("K.O.!", (255, 97, 101), 37),
    "bomb_ready": ("BOMB READY", (255, 212, 75), 17),
    "bomb_arm": ("BOMB ARMED", (255, 166, 48), 15),
    "bomb_explode": ("BOMB CLEAR!", (255, 175, 56), 42),
    "bomb_chain": ("BOMB CHAIN!", (255, 212, 72), 38),
    "garbage_cancel": ("BLOCKED!", (136, 226, 255), 11),
}


class EffectEngine:
    def __init__(self, seed=413, enabled=True):
        self.random = random.Random(seed)
        self.enabled = bool(enabled)
        self.particles = []
        self.rings = []
        self.labels = []
        self.flashes = []
        self.shake = 0
        self._font = None
        self.source_frames = {}
        self.source_overlays = []

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled:
            self.clear()
        return self.enabled

    def clear(self):
        self.particles.clear()
        self.rings.clear()
        self.labels.clear()
        self.flashes.clear()
        self.shake = 0
        self.source_overlays.clear()

    def load_source_visuals(self, asset_dir=None):
        """Load PNGs traced from Flash vectors; preserve particle-only fallback."""
        root = Path(asset_dir) if asset_dir else Path(__file__).resolve().parent / 'assets' / 'original_visuals'
        for name,nframes in (('bomb',8),('combo',6),('tspin',6)):
            try:
                frames=[pygame.image.load(str(root/'effects'/(name+'_%02d.png'%i))) for i in range(nframes)]
            except (OSError, pygame.error, AttributeError):
                frames=[]
            self.source_frames[name]=frames
        return bool(self.source_frames.get('bomb'))

    def event(self, name, rect, positions=(), total=0):
        """rect: (screen-x, screen-y, width, height) of affected board.

        positions: (col, visible-row) affected by explosions or line clears.
        """
        if not self.enabled or name not in EVENTS:
            return
        title, color, count = EVENTS[name]
        x, y, w, h = rect
        if positions:
            selected = list(positions)
            if len(selected) > 12:
                selected = self.random.sample(selected, 12)
            px = x + sum(p[0] for p in selected) / len(selected) * BLOCK_PIXELS + 9
            py = y + sum(p[1] for p in selected) / len(selected) * BLOCK_PIXELS + 9
        else:
            px, py = x + w / 2, y + h / 2
        py = max(y + 18, min(y + h - 18, py))
        sprite_tag={'bomb_explode':'bomb','bomb_chain':'bomb',
                    'combo':'combo','tspin':'tspin'}.get(name)
        if sprite_tag and self.source_frames.get(sprite_tag):
            self.source_overlays.append([sprite_tag,px,py,24])
        if title:
            if name == 'combo' and total > 1:
                title = f'{total} COMBO!'
            self.labels.append([title, px, max(y + 12, py - 16), 54, color])
        # Opaque particles never cross fully off the screen; no surfaces cached.
        for index in range(count):
            angle = self.random.uniform(0, 2 * math.pi)
            speed = self.random.uniform(0.7, 3.7) * (1.7 if name == "bomb_explode" else 1)
            lifetime = self.random.randrange(18, 45)
            radius = self.random.randrange(2, 6)
            self.particles.append([px, py, math.cos(angle)*speed, math.sin(angle)*speed,
                                   lifetime, lifetime, radius, color])
        if name in ("bomb_explode", "tetris", "ko", "perfect_clear", "attack"):
            self.rings.append([px, py, 4.0, 30 if name == "bomb_explode" else 22, color])
            self.shake = max(self.shake, 10 if name == "bomb_explode" else 5)
        if name in ("line_clear", "tetris", "bomb_explode", "perfect_clear", "warning"):
            self.flashes.append([rect, 11 if name != "bomb_explode" else 17, color])

    def tick(self):
        if not self.enabled:
            return
        updated = []
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.075
            p[4] -= 1
            if p[4] > 0:
                updated.append(p)
        self.particles = updated[-400:]
        for collection, index in ((self.labels, 3), (self.rings, 3), (self.flashes, 1)):
            for item in collection:
                item[index] -= 1
            collection[:] = [item for item in collection if item[index] > 0]
        self.shake = max(0, self.shake - 1)
        for item in self.source_overlays:
            item[3]-=1
        self.source_overlays[:]=[item for item in self.source_overlays if item[3]>0]

    def draw(self, screen):
        if not self.enabled:
            return
        # Brief framebuffer shake on bomb blasts, KO and heavy attacks.
        # The shake never changes model coordinates or collision detection.
        if self.shake and hasattr(screen, "copy"):
            strength = min(4, self.shake)
            dx = self.random.randint(-strength, strength)
            dy = self.random.randint(-strength, strength)
            frame = screen.copy()
            screen.fill((9, 14, 26))
            screen.blit(frame, (dx, dy))
        if self._font is None:
            self._font = pygame.font.SysFont("arial", 21, bold=True)
        for rect, life, color in self.flashes:
            x, y, width, height = rect
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            surface.fill((*color, min(75, life * 5)))
            screen.blit(surface, (x, y))
        for x, y, radius, life, color in self.rings:
            pygame.draw.circle(screen, color, (int(x), int(y)), int(radius + (32 - life) * 3), 3)
        for x, y, vx, vy, life, initial, radius, color in self.particles:
            factor = max(0.35, life / initial)
            pygame.draw.circle(screen, tuple(int(c * factor) for c in color),
                               (int(x), int(y)), max(1, int(radius * factor)))
        for name,x,y,life in self.source_overlays:
            # Source-vector-derived effect; timing rebuilt rather than copied
            # from the original Flash MovieClip timeline.
            frames=self.source_frames[name]
            idx=min(len(frames)-1,(24-life)*len(frames)//24)
            frame=frames[idx]
            screen.blit(frame,(int(x - frame.get_width()/2),int(y - frame.get_height()/2)))
        for title, x, y, life, color in self.labels:
            label = self._font.render(title, True, color)
            alpha = min(255, life * 8)
            label.set_alpha(alpha)
            screen.blit(label, (int(x - label.get_width()/2), int(y - (54 - life) * 0.65)))

    def bomb_glow(self, screen, px, py, grid_length, offset):
        """Indicate that the currently falling piece is armed."""
        if not self.enabled:
            return
        shift = grid_length - GRID_DEPTH
        center = (offset[0] + (px + 1.5) * BLOCK_PIXELS,
                  offset[1] + (py + 1.5 - shift) * BLOCK_PIXELS)
        if offset[1] <= center[1] <= offset[1] + GRID_DEPTH * BLOCK_PIXELS:
            pygame.draw.circle(screen, (255, 195, 68),
                               (int(center[0]), int(center[1])), 16, 3)
