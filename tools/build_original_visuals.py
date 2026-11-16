"""Build static PNGs from supplied Facebook Tetris Battle SWF vector assets.

Copyright notice: The source visuals remain owned by their respective creators.
Only run for assets you have permission to use. The original SWFs aren't required
at game runtime. This tool does not extract proprietary game code.

Requires Pillow and CairoSVG for the conversion step (not for playing).
Usage: python tools/build_original_visuals.py --asset-zip tetrisfb-assets-main.zip
"""
from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw
from swf_vector_extract import parse_shape, svg_shape, tags
import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'TetrisBattle' / 'assets' / 'original_visuals'
TILE_ORDER = {'Z':0,'L':1,'O':2,'S':3,'I':4,'J':5,'T':6}
SWF_BASE = 'data1.81.0/flash/deco/'


def source(z, rel):
    candidates = [n for n in z.namelist() if n.endswith(rel) and not n.endswith('/')]
    if len(candidates) != 1:
        raise FileNotFoundError('Cannot uniquely find '+rel+' in the supplied archive')
    return z.read(candidates[0]),candidates[0]


def to_png_shape(data, ids, desired=18):
    # A custom SWF vector parser preserves original solid colors and geometry.
    # Does not attempt to reproduce sprite-timeline animation or blend filters.
    import tempfile
    import os
    fd, name = tempfile.mkstemp(suffix='.swf')
    os.close(fd)
    p=Path(name)
    try:
        p.write_bytes(data)
        _,alltags=tags(p)
        sh={}
        for code,b in alltags:
            if code in (2,22,32,83):
                try:
                    parsed=parse_shape(b,code)
                    sh[parsed[0]]=parsed
                except (IndexError,ValueError):
                    continue
    finally:
        p.unlink(missing_ok=True)
    parts=[]
    for ident in ids:
        if ident not in sh:raise ValueError(f'SWF shape {ident} unavailable')
        svg=svg_shape(sh[ident],scale=4)
        png=cairosvg.svg2png(bytestring=svg.encode('utf-8'))
        img=Image.open(io.BytesIO(png)).convert('RGBA')
        # The extractor deliberately pads by half a twip/pixel (1px at 4x).
        if img.width>=12 and img.height>=12:
            pad=2
            img=img.crop((pad,pad,img.width-pad,img.height-pad))
        img=img.resize((desired,desired),Image.Resampling.LANCZOS)
        parts.append(img)
    return parts


def save(tile,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    tile.save(dest)


def create_visuals(asset_zip, output=OUTPUT):
    output=Path(output)
    manifest={'source_archive':Path(asset_zip).name,
              'extraction':'SWF DefineShape vector geometry, static poses; no complete Flash timeline reconstruction',
              'mino':{},'ghost':{},'bomb':{},'ui':{},'effects':{}}
    with zipfile.ZipFile(asset_zip) as z:
        for variant,ids in {
            'classic':[1,8,13,18,23,28,33,38],
            'default':[1,4,5,6,7,8,9,10],
            'neon':[1,10,15,20,25,30,35,40],
        }.items():
            data,path=source(z,SWF_BASE+'mino_'+variant+'.swf')
            images=to_png_shape(data,ids)
            for idx,(typ,subidx) in enumerate(TILE_ORDER.items()):
                save(images[idx],output/'minos'/variant/(typ+'.png'))
            save(images[7],output/'minos'/variant/'G.png')
            manifest['mino'][variant]={'source':path,'shapes':dict(zip(list(TILE_ORDER)+['G'],ids))}
        # Carefully selected single-pose Ghost sprites from actual SWF files.
        for variant,idx in {'outline':2,'shadow':2,'ghost':1}.items():
            data,path=source(z,SWF_BASE+'ghost_'+variant+'.swf')
            save(to_png_shape(data,[idx])[0],output/'ghosts'/(variant+'.png'))
            manifest['ghost'][variant]={'source':path,'shape':idx}
        for variant,idx in {'bomb':3,'thunder':1,'smiley':1}.items():
            data,path=source(z,SWF_BASE+'bomb_'+variant+'.swf')
            save(to_png_shape(data,[idx])[0],output/'bombs'/(variant+'.png'))
            manifest['bomb'][variant]={'source':path,'shape':idx}
        # Reuse a genuine original-era Facebook battle logo as a small HUD mark.
        data,path=source(z,'data1.81.0/graphics/TB_logo_215x190.png')
        logo=Image.open(io.BytesIO(data)).convert('RGBA')
        save(logo,output/'ui'/'facebook_battle_logo.png')
        manifest['ui']['facebook_battle_logo']={'source':path}
        # Frames are a *new* timeline assembled from authentic SWF vectors:
        # not a claim to reproduce every source keyframe, easing or blend mode.
        bomb,source_path=source(z,SWF_BASE+'bomb_bomb.swf')
        core=to_png_shape(bomb,[6],desired=80)[0]
        accent=to_png_shape(bomb,[1],desired=80)[0]
        for frame in range(8):
            canvas=Image.new('RGBA',(80,80))
            radius=12+frame*5
            p=int(255*(1-frame/8))
            circ=core.resize((radius*2,radius*2),Image.Resampling.LANCZOS)
            circ.putalpha(circ.getchannel('A').point(lambda v:(v*p)//255))
            canvas.alpha_composite(circ,((80-circ.width)//2,(80-circ.height)//2))
            ring_r=min(80,34+frame*6)
            outline=accent.resize((ring_r,ring_r),Image.Resampling.LANCZOS)
            outline.putalpha(outline.getchannel('A').point(lambda v:(v*max(0,200-frame*27))//255))
            canvas.alpha_composite(outline,((80-outline.width)//2,(80-outline.height)//2))
            save(canvas,output/'effects'/f'bomb_{frame:02d}.png')
        manifest['effects']['bomb']={'source':source_path,'shapes':[1,6],
                                     'note':'source-vector based 8-frame reconstructed effect, not original SWF timeline'}
        # SWF mino vectors also provide geometric motifs for the *new* Combo
        # and T-Spin glow effects. The original art is the source; the pulse
        # animation itself is reconstructed by this tool, not extracted Flash.
        for tag,source_file,shape_id in [
            ('combo','mino_neon.swf',35),('tspin','mino_classic.swf',33),
        ]:
            art,art_path=source(z,SWF_BASE+source_file)
            emblem=to_png_shape(art,[shape_id],desired=80)[0]
            for n in range(6):
                canvas=Image.new('RGBA',(80,80))
                size=min(78,34+n*8)
                tile=emblem.resize((size,size),Image.Resampling.LANCZOS)
                alpha=max(0,255-n*39)
                tile.putalpha(tile.getchannel('A').point(lambda v:(v*alpha)//255))
                canvas.alpha_composite(tile,((80-size)//2,(80-size)//2))
                save(canvas,output/'effects'/f'{tag}_{n:02d}.png')
            manifest['effects'][tag]={'source':art_path,'shapes':[shape_id],
                         'note':'source-vector derived animation, not original Combo/T-spin SWF timeline'}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest


def make_preview(outdir=OUTPUT):
    """Generate a human-readable image confirming all color-to-piece mappings."""
    outdir=Path(outdir)
    skins=['classic','default','neon'];pieces=['I','O','T','S','Z','J','L','G']
    prev=Image.new('RGB',(760,292),(22,28,45))
    dr=ImageDraw.Draw(prev)
    dr.text((20,12),'FACEBOOK TETRIS BATTLE / SWF VECTOR SKINS',fill='#e5f1ff')
    for r,name in enumerate(skins):
        y=52+r*57;dr.text((20,y+14),name,fill='#efefef')
        for c,piece in enumerate(pieces):
            tile=Image.open(outdir/'minos'/name/(piece+'.png')).convert('RGBA').resize((36,36),Image.Resampling.NEAREST)
            x=136+c*70
            prev.paste(tile,(x,y),tile)
            dr.text((x+11,y+39),piece,fill='#dae8ff')
    dr.text((20,247),'Ghosts / Bombs',fill='#eef7ff')
    for j,(kind,name) in enumerate([('ghosts','outline'),('ghosts','shadow'),('ghosts','ghost'),('bombs','bomb'),('bombs','thunder'),('bombs','smiley')]):
        a=Image.open(outdir/kind/(name+'.png')).convert('RGBA').resize((31,31),Image.Resampling.NEAREST)
        x=161+j*90;prev.paste(a,(x,240),a);dr.text((x,275),name,fill='#bfd3df')
    prev.save(outdir/'preview.jpg',quality=92)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--asset-zip',required=True)
    parser.add_argument('--output',default=str(OUTPUT))
    args=parser.parse_args()
    result=create_visuals(args.asset_zip,args.output)
    make_preview(args.output)
    print(json.dumps({k:list(v) if isinstance(v,dict) else v for k,v in result.items()},ensure_ascii=False,indent=2))
