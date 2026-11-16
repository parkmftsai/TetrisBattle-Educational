"""Optional original-era Facebook Tetris Battle PNG skins for Pygame.

The PNGs are extracted from user-supplied SWF vector art, without loading
Flash in the running game. This module alters *rendering only*: collision,
keyboard input, garbage, sound, attacks and score use the original model.
"""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent / 'assets' / 'original_visuals'
SKINS = {
    'mino': ('classic', 'default', 'neon', 'legacy'),
    'ghost': ('outline', 'shadow', 'ghost', 'legacy'),
    'bomb': ('bomb', 'thunder', 'smiley', 'legacy'),
}
PIECES = ('I', 'O', 'J', 'L', 'S', 'Z', 'T', 'G')


def next_skin(category, current):
    choices=SKINS[category]
    return choices[(choices.index(current)+1)%len(choices)] if current in choices else choices[0]


class OriginalVisuals:
    def __init__(self, images, mino='classic', ghost='outline', bomb='bomb', enabled=True,
                 asset_dir=None):
        self.images=images
        self.asset_dir=Path(asset_dir) if asset_dir else ROOT
        self.legacy={key:images[key] for key in ('piecepics','resizepics','nextpics','ghost')}
        self.legacy_bomb=None
        self.mino='legacy';self.ghost='legacy';self.bomb='legacy'
        self.enabled=bool(enabled)
        self.logo=None
        self.bomb_sprite=None
        self._cache={}
        # If the optional source-derived graphics are missing, stay playable.
        self.set_skins(mino=mino,ghost=ghost,bomb=bomb)
        try:
            self.logo=self._read(self.asset_dir/'ui'/'facebook_battle_logo.png')
            self.logo=pygame.transform.smoothscale(self.logo,(61,54))
        except (OSError,ValueError,pygame.error,AttributeError):
            self.logo=None

    def _read(self, path):
        path=Path(path)
        if path not in self._cache:
            # Do not convert on load; avoids dependency on a display mode
            # for tools/tests that construct Renderer in headless mode.
            self._cache[path]=pygame.image.load(str(path))
        return self._cache[path]

    def set_skins(self, *, mino=None, ghost=None, bomb=None):
        choices={'mino':mino,'ghost':ghost,'bomb':bomb}
        for cat,new in choices.items():
            if new is not None:
                if new not in SKINS[cat]:
                    raise ValueError('Unknown '+cat+' skin: '+str(new))
                setattr(self,cat,new)
        self.apply()
        return self.snapshot()

    def cycle(self,category):
        if category not in SKINS:raise ValueError('Invalid skin category: '+category)
        return self.set_skins(**{category:next_skin(category,getattr(self,category))})

    def snapshot(self):
        return {key:getattr(self,key) for key in SKINS}

    def apply(self):
        if self.enabled and self.mino!='legacy':
            try:
                art={t:self._read(self.asset_dir/'minos'/self.mino/(t+'.png')) for t in PIECES}
                if any(img.get_width()!=18 or img.get_height()!=18 for img in art.values()):
                    raise ValueError('SWF tile size must be 18x18')
                self.images['piecepics']=art
                self.images['resizepics']={t:pygame.transform.smoothscale(img,(12,12)) for t,img in art.items()}
                self.images['nextpics']={t:pygame.transform.smoothscale(img,(8,8)) for t,img in art.items()}
            except (OSError,ValueError,pygame.error,AttributeError):
                # Don't break gameplay if a skin was deleted or corrupted.
                for k in ('piecepics','resizepics','nextpics'):
                    self.images[k]=self.legacy[k]
        else:
            for k in ('piecepics','resizepics','nextpics'):
                self.images[k]=self.legacy[k]
        if self.enabled and self.ghost!='legacy':
            try:
                self.images['ghost']=self._read(self.asset_dir/'ghosts'/(self.ghost+'.png'))
            except (OSError,ValueError,pygame.error,AttributeError):
                self.images['ghost']=self.legacy['ghost']
        else:
            self.images['ghost']=self.legacy['ghost']
        self.bomb_sprite=None
        if self.enabled and self.bomb!='legacy':
            try:self.bomb_sprite=self._read(self.asset_dir/'bombs'/(self.bomb+'.png'))
            except (OSError,ValueError,pygame.error,AttributeError):pass

    def draw_logo(self,screen,at=(369,5)):
        if self.enabled and self.logo:
            screen.blit(self.logo,at)
