"""Extract vector SWF DefineShape* shapes to simple SVG/PNG. For assets supplied by the user.
Supports the solid/gradient fills and straight/curved edges used by the selected skins;
SWF sprite animation/morphs are intentionally not treated as static sprites.
"""
import io, zlib, struct, math, xml.sax.saxutils
from pathlib import Path
import cairosvg
class Bits:
 def __init__(self, data, pos=0):self.d=data;self.pos=pos*8
 def u(self,n):
  x=0
  for i in range(n):
   x=(x<<1)|((self.d[self.pos>>3]>>(7-(self.pos&7)))&1);self.pos+=1
  return x
 def s(self,n):
  if n==0:return 0
  v=self.u(n);return v-(1<<n) if v & (1<<(n-1)) else v
 def align(self):self.pos=(self.pos+7)&~7
 def byte(self):self.align();return self.u(8)
 def u16(self):return int.from_bytes(self.get(2),'little')
 def get(self,n):self.align();p=self.pos//8;self.pos+=n*8;return self.d[p:p+n]
 def rect(self):
  nb=self.u(5); vals=tuple(self.s(nb) for _ in range(4));self.align();return vals
 def matrix(self):
  scalex=scaley=1.;rot0=rot1=0.
  if self.u(1):nb=self.u(5);scalex=self.s(nb)/65536.;scaley=self.s(nb)/65536.
  if self.u(1):nb=self.u(5);rot0=self.s(nb)/65536.;rot1=self.s(nb)/65536.
  nb=self.u(5);tx=self.s(nb);ty=self.s(nb);self.align()
  return scalex,rot0,rot1,scaley,tx,ty

def tags(p):
 d=Path(p).read_bytes()
 if d[:3]==b'CWS':d=b'FWS'+d[3:8]+zlib.decompress(d[8:])
 if d[:3]!=b'FWS':raise ValueError('invalid SWF '+str(p))
 v=Bits(d,8);hdr=v.rect();fps=v.get(2);frames=v.get(2)
 ret=[]
 while v.pos//8+2<=len(d):
  n=int.from_bytes(v.get(2),'little');code=n>>6;ln=n&63
  if ln==63:ln=int.from_bytes(v.get(4),'little')
  buf=v.get(ln);ret.append((code,buf))
  if code==0:break
 return hdr,ret

def col(b,alpha=False):
 a=b.get(4 if alpha else 3)
 return '#'+a[:3].hex(),(a[3]/255 if alpha else 1.)

def fill_array(b,alpha):
 count=b.byte(); count=b.u16() if count==255 else count
 fills=[]
 for _ in range(count):
  kind=b.byte()
  if kind==0:fills.append(('solid',col(b,alpha)))
  elif kind in (0x10,0x12,0x13):
   m=b.matrix()
   val=b.byte();num=val&15
   steps=[]
   for j in range(num):steps.append((b.byte()/255,col(b,alpha)))
   if kind==0x13:b.get(2)
   fills.append(('gradient',kind,m,steps))
  elif kind in (0x40,0x41,0x42,0x43):
   mid=b.u16();m=b.matrix();fills.append(('bitmap',mid,m))
  else:raise ValueError('Unsupported fill type '+hex(kind))
 return fills

def line_array(b,alpha,shape4=False):
 count=b.byte();count=b.u16() if count==255 else count
 lines=[]
 for _ in range(count):
  w=b.u16()
  if shape4:
   flags=b.u16()
   if flags&0x8: b.u16() # miterLimit
   if flags&0x0008:pass
   if flags&0x0008:pass
   # hasFillFlag (bit 3 of first byte? shape4 flags in big-endian bit order)
   if (flags>>11)&1:
    ls=fill_array_dummy(b,alpha)
   else:ls=('solid',col(b,True))
  else:ls=('solid',col(b,alpha))
  lines.append((w,ls))
 return lines

def fill_array_dummy(b,alpha):
 kind=b.byte()
 if kind==0:return ('solid',col(b,alpha))
 raise ValueError('complex LineStyle2')

def parse_shape(data,kind):
 b=Bits(data)
 cid=b.u16();box=b.rect()
 if kind==83:
  edgebox=b.rect(); flags=b.byte()
 alpha=kind in (32,83)
 fills=fill_array(b,alpha)
 lines=line_array(b,alpha,kind==83)
 nf=b.u(4);nl=b.u(4)
 fs0=fs1=ls=0
 x=y=0
 edge_by_fill={}; edge_by_line={}; count=0
 while True:
  if b.pos//8>=len(data):break
  straight=b.u(1)
  if straight:
   is_straight=b.u(1);nb=b.u(4)+2
   if is_straight:
    if b.u(1):dx=b.s(nb);dy=b.s(nb)
    else:
     if b.u(1):dx=0;dy=b.s(nb)
     else:dx=b.s(nb);dy=0
    edge=('L',(x,y),(x+dx,y+dy))
   else:
    cdx=b.s(nb);cdy=b.s(nb);adx=b.s(nb);ady=b.s(nb)
    edge=('Q',(x,y),(x+cdx,y+cdy),(x+cdx+adx,y+cdy+ady))
   x,y=edge[-1]
   if fs1:edge_by_fill.setdefault(fs1,[]).append(edge)
   if fs0:
    rev=('L',edge[-1],edge[1]) if edge[0]=='L' else ('Q',edge[-1],edge[2],edge[1])
    edge_by_fill.setdefault(fs0,[]).append(rev)
   if ls:edge_by_line.setdefault(ls,[]).append(edge)
   count+=1
  else:
   flags=b.u(5)
   if flags==0:break
   # MoveTo is low bit, ordering: new, line, fill1, fill0, move
   if flags&1:
    n=b.u(5);x=b.s(n);y=b.s(n)
   if flags&2:fs0=b.u(nf)
   if flags&4:fs1=b.u(nf)
   if flags&8:ls=b.u(nl)
   if flags&16:
    b.align();fills+=fill_array(b,alpha);lines+=line_array(b,alpha,kind==83)
    nf=b.u(4);nl=b.u(4)
 return cid,box,fills,lines,edge_by_fill,edge_by_line,count

def svg_shape(parsed,scale=1):
 cid,box,fills,lines,edgemap,linemap,ecount=parsed
 xmin,xmax,ymin,ymax=box
 # important prevent clipping at exactly edges
 xmin-=10;xmax+=10;ymin-=10;ymax+=10
 width=(xmax-xmin)/20;height=(ymax-ymin)/20
 body=[];defs=[]
 for fi,edges in sorted(edgemap.items()):
  if fi>len(fills):continue
  fill=fills[fi-1]
  if fill[0]=='solid':
   color,alpha=fill[1];sty=f'fill="{color}" fill-opacity="{alpha}"'
  elif fill[0]=='gradient':
   _,gkind,m,stops=fill
   gname=f'g{cid}_{fi}'
   # SWF gradient coordinate ranges +/-16384 twips; matrix controls final placement
   # SVG maps gradient in objectBoundingBox as visual approximation
   typ='radialGradient' if gkind==0x12 else 'linearGradient'
   attr='cx="50%" cy="50%" r="70%"' if gkind==0x12 else 'x1="0%" x2="100%" y1="0%" y2="0%"'
   defs.append(f'<{typ} id="{gname}" {attr}>'+''.join(f'<stop offset="{int(r*100)}%" stop-color="{c}" stop-opacity="{a}"/>' for r,(c,a) in stops)+f'</{typ}>')
   sty=f'fill="url(#{gname})"'
  else: continue
  # Join edges with same endpoints into closed contours, preserve input order where possible
  paths=[];remaining=list(edges)
  while remaining:
   e=remaining.pop(0); path=[e];start=e[1];end=e[-1]
   while remaining and end!=start:
    match=next((j for j,v in enumerate(remaining) if v[1]==end),None)
    if match is None:break
    nxt=remaining.pop(match);path.append(nxt);end=nxt[-1]
   paths.append(path)
  d=' '
  for path in paths:
   cmds=[f'M {path[0][1][0]} {path[0][1][1]}']
   for e in path:
    if e[0]=='L':cmds.append(f'L {e[-1][0]} {e[-1][1]}')
    else:cmds.append(f'Q {e[2][0]} {e[2][1]} {e[-1][0]} {e[-1][1]}')
   cmds.append('Z')
   d+=' '.join(cmds)+' '
  body.append(f'<path d="{d.strip()}" {sty} fill-rule="evenodd"/>')
 # pure SVG can subsequently rasterize via cairosvg
 header=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width*scale}" height="{height*scale}" viewBox="{xmin} {ymin} {xmax-xmin} {ymax-ymin}">'
 return header+'<defs>'+''.join(defs)+'</defs>'+''.join(body)+'</svg>'

def extract_shapes(p):
 _,alltags=tags(p)
 return [parse_shape(data,code) for code,data in alltags if code in (2,22,32,83)]

if __name__=='__main__':
 import sys
 p=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
 for shape in extract_shapes(p):
  cid=shape[0];svg=svg_shape(shape,4);(out/f'{p.stem}_{cid}.svg').write_text(svg)
  try:cairosvg.svg2png(bytestring=svg.encode(),write_to=str(out/f'{p.stem}_{cid}.png'))
  except Exception as e:print('FAIL',cid,e)
  print(cid,'box',shape[1],'fills',len(shape[2]),'edges',shape[-1])
