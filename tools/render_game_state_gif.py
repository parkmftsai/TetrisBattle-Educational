#!/usr/bin/env python3
"""Create a GIF from the actual TetrisBattle Python game-state engine.

This is a scripted game-state demonstration, *not* a capture of the
Pygame window. Only bundled code + original custom PIL UI are used.
Requires Pillow and NumPy, NOT pygame, on the build machine.
"""
from pathlib import Path
import sys, types, random, argparse
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pygame_stub = types.ModuleType('pygame')
pygame_stub.KEYDOWN=101; pygame_stub.KEYUP=102
sys.modules.setdefault('pygame', pygame_stub)
from TetrisBattle.tetris import Tetris, Player, hardDrop
from TetrisBattle.settings import GRID_DEPTH, GRID_WIDTH

KEYS={'left':12, 'right':13,'down':14,'rotate_right':15,'rotate_left':16,'drop':17,'hold':18}
COLORS={1:'#14cee8',2:'#ecca40',3:'#417eea',4:'#e99e30',5:'#ec5471',6:'#5cdd8b',7:'#b076f1',8:'#59677d',9:'#f6b34e'}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
if not Path(FONT).exists(): FONT='DejaVuSans.ttf'; BOLD='DejaVuSans-Bold.ttf'
F12=ImageFont.truetype(FONT,12); F16=ImageFont.truetype(FONT,16); F22=ImageFont.truetype(BOLD,22); F32=ImageFont.truetype(BOLD,32)

def new_tetris(seed, p):
    random.seed(seed)
    keys={'id':p,**KEYS}
    return Tetris(Player(keys),'none', bombs_enabled=True, modern_controls=True)

def send(t,action):
    key=KEYS[action]
    t.trigger(types.SimpleNamespace(type=101,key=key))
    t.trigger(types.SimpleNamespace(type=102,key=key))

def settle(t):
    if t.check_fallen():
        t.clear();t.new_block()

def do_action(t,action):
    if t.check_KO():return
    if action=='hard':
        send(t,'drop');settle(t)
    elif action in KEYS:
        send(t,action)

def colorhex(c):
    c=c.lstrip('#');return tuple(int(c[i:i+2],16) for i in (0,2,4))

def draw_tile(draw,x,y,kind,s=18, ghost=False):
    if kind==0:return
    color=colorhex(COLORS.get(kind,'#ddd'))
    if ghost:
        draw.rectangle([x+2,y+2,x+s-3,y+s-3],outline=tuple(min(255,i+62) for i in color),width=2)
    else:
        draw.rounded_rectangle([x+1,y+1,x+s-2,y+s-2],3,fill=color)
        draw.line((x+4,y+4,x+s-5,y+4),fill=tuple(min(255,i+38) for i in color),width=2)
        if kind==9:
            draw.ellipse([x+5,y+5,x+s-6,y+s-6],fill='#442d25')
            draw.ellipse([x+7,y+5,x+9,y+7],fill='#ffffff')

def board(d,t,x,y, label,score_text='',s=18):
    w=s*10;h=s*20
    d.rounded_rectangle((x-7,y-7,x+w+7,y+h+7),radius=11,fill='#121d33',outline='#536380',width=2)
    d.rectangle((x,y,x+w,y+h),fill='#0b1425')
    for cx in range(11):d.line((x+cx*s,y,x+cx*s,y+h),fill='#1c2b43',width=1)
    for cy in range(21):d.line((x,y+cy*s,x+w,y+cy*s),fill='#1c2b43',width=1)
    extra=len(t.grid[0])-20
    for ix in range(10):
        for iy in range(20):
            kind=t.grid[ix][extra+iy]
            if kind:draw_tile(d,x+ix*s,y+iy*s,kind,s)
    try:
        ghost_d=hardDrop(t.grid,t.block,t.px,t.py)
        for ix,iy,kind in t.block.return_pos_color(t.px,t.py+ghost_d):
            vis=iy-extra
            if 0<=ix<10 and 0<=vis<20 and t.grid[ix][extra+vis]==0:
                draw_tile(d,x+ix*s,y+vis*s,kind,s,ghost=True)
    except Exception:pass
    for ix,iy,kind in t.block.return_pos_color(t.px,t.py):
        vis=iy-extra
        if 0<=ix<10 and 0<=vis<20:
            draw_tile(d,x+ix*s,y+vis*s,kind,s)
    d.text((x,y-38),label,font=F22,fill='#eaf2ff')
    if score_text:d.text((x,y+h+14),score_text,font=F12,fill='#b6c8e2')

def render(players,frame_idx,which):
    img=Image.new('RGB',(800,575),'#071023')
    d=ImageDraw.Draw(img)
    d.rectangle((0,0,800,73), fill='#14243f')
    d.text((31,19),'TETRIS BATTLE',font=F32,fill='#f7fbff')
    d.text((565,27),'EDUCATIONAL EDITION',font=F12,fill='#a4e7ff')
    if which=='single':
        t=players[0]
        board(d,t,315,120,'SINGLE PLAYER',f'LINES  {t.total_lines:02d}     PIECES  {t.n_used_block:02d}')
        d.text((52,185),'CONTROLS',font=F22,fill='#e5eaff')
        for i,msg in enumerate(['← / →  Move','↑ / X  Rotate','Space  Hard drop','C  Hold piece']):d.text((52,228+i*36),msg,font=F16,fill='#c7d4ef')
        d.text((568,185),'NEXT',font=F22,fill='#e5eaff')
        for i,block in enumerate(t.buffer.now_list[:3]):
            d.text((578,230+i*44),block.block_type(),font=F22,fill=colorhex(COLORS.get({'I':1,'O':2,'J':3,'L':4,'Z':5,'S':6,'T':7}[block.block_type()],'#fff')))
    else:
        board(d,players[0],145,120,'PLAYER 1',f'LINES {players[0].total_lines:02d}   SENT {players[0].sent:02d}')
        board(d,players[1],471,120,'PLAYER 2',f'LINES {players[1].total_lines:02d}   SENT {players[1].sent:02d}')
        d.text((362,225),'VS',font=F32,fill='#ffd28b')
        d.text((353,284),'BOMB',font=F12,fill='#ffbf74')
        d.text((347,304),'GARBAGE',font=F12,fill='#ffbf74')
    d.rectangle((0,531,800,575),fill='#101e37')
    d.text((23,547),'SCRIPTED GAME-STATE DEMO  |  Computed from the TetrisBattle Python engine; not a Pygame screen capture',font=F12,fill='#8394b3')
    return img

def simulate(mode):
    random.seed(431)
    players=[new_tetris(127,0)] if mode=='single' else [new_tetris(127,0),new_tetris(319,1)]
    if mode=='double':
        players[1].build_garbage(players[1].grid,2,bomb_columns=[3,3])
    frames=[]
    for f in range(70):
        for p,t in enumerate(players):
            if t.check_KO():continue
            turn=(f+(5*p))
            if turn % 18 == 3: do_action(t,'left')
            if turn % 18 == 6: do_action(t,'right')
            if turn % 18 == 10: do_action(t,'rotate_right')
            if turn % 18 == 14: do_action(t,'hard')
            if f % 3 == 0:
                try:t._modern_step_down()
                except Exception:pass
        frames.append(render(players,f,mode))
    return frames

def save(out,frames):
    out=Path(out); out.parent.mkdir(parents=True,exist_ok=True)
    frames[0].save(out,save_all=True,append_images=frames[1:],duration=95,loop=0,optimize=True,disposal=2)
    print(f'{out}: {out.stat().st_size:,} bytes, {len(frames)} generated game-state frames')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['single','double'],required=True)
    ap.add_argument('--output',required=True)
    args=ap.parse_args();save(args.output,simulate(args.mode))
