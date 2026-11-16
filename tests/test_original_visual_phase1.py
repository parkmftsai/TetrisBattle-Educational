"""Stage-1 original SWF visual assets: load, swap, fallback, events.

These tests do not claim that a physical SDL window has been exercised.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from TetrisBattle.visuals import OriginalVisuals, SKINS, next_skin, ROOT, PIECES
from TetrisBattle.effects import EffectEngine
from TetrisBattle.renderer import Renderer
from game.tetris_game import TetrisGame

# Skip source-specific image tests when unlicensed original Flash media is omitted.
pytestmark = pytest.mark.skipif(not (ROOT / "manifest.json").is_file(), reason="Optional Flash visual assets are not bundled")


def test_art_assets_present_and_shaped_as_source_vectors():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    for variant in ('classic','default','neon'):
        assert len(manifest['mino'][variant]['shapes'])==8
        for piece in PIECES:
            p=ROOT/'minos'/variant/(piece+'.png')
            blob=p.read_bytes()
            assert blob[:8]==b'\x89PNG\r\n\x1a\n',p
            assert int.from_bytes(blob[16:20],'big')==18
            assert int.from_bytes(blob[20:24],'big')==18
    for category,names in (('ghosts',('outline','shadow','ghost')),
                           ('bombs',('bomb','thunder','smiley'))):
        for name in names:
            assert (ROOT/category/(name+'.png')).stat().st_size>100
    for effect,count in (('bomb',8),('combo',6),('tspin',6)):
        for i in range(count):
            assert (ROOT/'effects'/('%s_%02d.png'%(effect,i))).is_file()
    assert 'static poses' in manifest['extraction']


def test_visual_source_provenance_and_skin_map():
    m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    assert m['mino']['classic']['shapes']['Z']==1
    assert m['mino']['classic']['shapes']['I']==23
    assert m['mino']['neon']['shapes']['T']==35
    assert m['bomb']['bomb']['shape']==3
    assert 'not original' in m['effects']['combo']['note']
    assert (ROOT/'ui'/'facebook_battle_logo.png').is_file()


def test_cycle_has_legacy_fallback():
    for typ,choices in SKINS.items():
        assert next_skin(typ,choices[-1])==choices[0]
        assert next_skin(typ,choices[0])==choices[1]
    with pytest.raises(KeyError):
        next_skin('not_a_skin','classic')


class Surface:
    def __init__(self,w=18,h=18,path=''):
        self.w=w;self.h=h;self.path=str(path)
    def get_width(self):return self.w
    def get_height(self):return self.h


class Screen:
    def __init__(self):self.calls=[]
    def blit(self,*args):self.calls.append(args)


def stub_pygame_art(monkeypatch):
    paths=[]
    def load(path):
        if not Path(path).exists():raise OSError(path)
        paths.append(path)
        name=Path(path).name
        return Surface(215,190,path) if name=='facebook_battle_logo.png' else Surface(80,80,path) if name.startswith(('bomb_','combo_','tspin_')) else Surface(18,18,path)
    monkeypatch.setattr(pygame,'image',SimpleNamespace(load=load),raising=False)
    monkeypatch.setattr(pygame,'transform',SimpleNamespace(smoothscale=lambda surf,size:Surface(*size,surf.path)),raising=False)
    return paths


def base_images():
    blocks={piece:Surface(18,18,'old-'+piece) for piece in PIECES}
    return {'piecepics':blocks,'resizepics':blocks.copy(),'nextpics':blocks.copy(),'ghost':Surface(18,18,'old-ghost')}


def test_skin_switch_updates_all_board_hold_next_and_ghost_images(monkeypatch):
    stub_pygame_art(monkeypatch)
    imgs=base_images()
    old=imgs['piecepics']
    visual=OriginalVisuals(imgs)
    assert visual.mino=='classic'
    assert visual.bomb_sprite is not None
    assert visual.logo.get_width()==61
    for piece in PIECES:
        assert ('classic/'+piece+'.png') in imgs['piecepics'][piece].path.replace('\\','/')
        assert imgs['resizepics'][piece].get_width()==12
        assert imgs['nextpics'][piece].get_width()==8
    visual.cycle('mino')
    assert visual.mino=='default'
    assert 'default/I.png' in imgs['piecepics']['I'].path.replace('\\','/')
    visual.cycle('ghost')
    assert 'shadow.png' in imgs['ghost'].path
    visual.cycle('bomb')
    assert 'thunder.png' in visual.bomb_sprite.path
    visual.enabled=False;visual.apply()
    assert imgs['piecepics'] is old
    assert imgs['ghost'].path=='old-ghost'
    assert visual.bomb_sprite is None
    visual.enabled=True;visual.apply()
    assert imgs['piecepics'] is not old


def test_missing_optional_images_do_not_crash_game(monkeypatch,tmp_path):
    stub_pygame_art(monkeypatch)
    imgs=base_images();old=imgs['piecepics']
    visual=OriginalVisuals(imgs,asset_dir=tmp_path)
    assert imgs['piecepics'] is old
    assert visual.bomb_sprite is None
    assert visual.logo is None
    visual.set_skins(mino='legacy',ghost='legacy',bomb='legacy')
    assert imgs['piecepics'] is old
    with pytest.raises(ValueError,match='Unknown'):
        visual.set_skins(mino='fake')


def test_actual_renderer_uses_selected_bomb_image(monkeypatch):
    stub_pygame_art(monkeypatch)
    imgs=base_images();screen=Screen()
    renderer=Renderer(screen,imgs)
    renderer.drawBlock(100,140,2,3,9)
    assert len(screen.calls)==2
    assert screen.calls[0][1]==(136,194)
    assert screen.calls[1][0] is renderer.visuals.bomb_sprite
    renderer.drawBlock(100,140,2,3,1)
    assert screen.calls[-1][0] is imgs['piecepics']['I']


def test_logo_is_drawn_only_when_original_art_enabled(monkeypatch):
    stub_pygame_art(monkeypatch)
    sc=Screen();r=Renderer(sc,base_images())
    r.draw_facebook_brand()
    assert sc.calls[-1][1]==(369,5)
    n=len(sc.calls)
    r.visuals.enabled=False;r.draw_facebook_brand()
    assert len(sc.calls)==n


def test_flash_vector_effect_events_are_used_only_when_art_exists(monkeypatch):
    stub_pygame_art(monkeypatch)
    engine=EffectEngine()
    assert engine.load_source_visuals()
    for name,tag in (('bomb_explode','bomb'),('bomb_chain','bomb'),('combo','combo'),('tspin','tspin')):
        engine.event(name,(100,120,180,360))
        assert engine.source_overlays[-1][0]==tag
    engine.tick()
    assert all(item[3]==23 for item in engine.source_overlays)
    engine.clear(); assert engine.source_overlays==[]
    assert engine.load_source_visuals('/nonexistent') is False
    engine.event('bomb_explode',(100,120,180,360))
    assert engine.source_overlays==[]


def test_f5_f6_f7_f8_hotkeys_keep_game_modes_unchanged():
    class Visual:
        enabled=True
        def __init__(self):self.called=[]
        def cycle(self,group):self.called.append(group)
        def apply(self):self.called.append('apply')
    game=TetrisGame.__new__(TetrisGame)
    game.renderer=SimpleNamespace(visuals=Visual())
    game.audio=None
    game.mode='single';game.num_players=1
    for k in (pygame.K_F5,pygame.K_F6,pygame.K_F7,pygame.K_F8):
        assert game._visual_hotkey(k)
    assert game.renderer.visuals.called==['mino','ghost','bomb','apply']
    assert game.renderer.visuals.enabled is False
    assert game.mode=='single' and game.num_players==1
    assert not game._visual_hotkey(pygame.K_SPACE)
