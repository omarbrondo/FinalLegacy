"""Convierte una hoja de poses (fondo liso, rótulos y línea de suelo) en el atlas PNG + JSON de soldados/. Ver el bloque final para el uso.
Necesita: pip install pillow numpy scipy"""
import sys, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
BG=np.array([56,67,85])
def fg_mask(a):
    near=(np.abs(a-BG).sum(axis=2)<=38)
    red=(a[:,:,0]>=a[:,:,2]-6)&(a[:,:,0]>a[:,:,1]+8)&(a[:,:,0]<150)
    rows=[y for y in range(a.shape[0]) if red[y].sum()>450]
    line=np.zeros_like(near)
    for y in rows:
        for yy in range(y-1,y+2):
            if 0<=yy<a.shape[0]: line[yy]=red[yy]|(a[yy].sum(axis=1)<80)
    fgm=~(near|line)
    return fgm, rows
def find_frames(a, minh=22, zones=()):
    fg,lines=fg_mask(a)
    for (x0,y0,x1,y1) in zones: fg[y0:y1,x0:x1]=False        # zonas con rótulos de texto
    fg=ndi.binary_opening(fg,iterations=1)
    lab,n=ndi.label(fg)
    boxes=[]
    for i,sl in enumerate(ndi.find_objects(lab),1):
        ys,xs=sl; h=ys.stop-ys.start; w=xs.stop-xs.start; area=int((lab[sl]==i).sum())
        if area>=120: boxes.append([xs.start,ys.start,xs.stop,ys.stop,[i]])
    ch=True
    while ch:
        ch=False
        for p in range(len(boxes)):
            for q in range(p+1,len(boxes)):
                A,B=boxes[p],boxes[q]
                if A[0]-8<B[2] and B[0]-8<A[2] and A[1]-8<B[3] and B[1]-8<A[3]:
                    boxes[p]=[min(A[0],B[0]),min(A[1],B[1]),max(A[2],B[2]),max(A[3],B[3]),A[4]+B[4]]; boxes.pop(q); ch=True; break
            if ch: break
    return [dict(box=tuple(b[:4]),ids=b[4]) for b in boxes if (b[3]-b[1])>=minh and (b[2]-b[0])>=14], fg, lab, lines
if __name__=='__main__':
    D='/tmp/claude-0/-home-user-FinalLegacy/ed78837b-9164-5456-a212-e556937b17f3/'
    a=np.asarray(Image.open(D+'images/55.png').convert('RGB')).astype(int)
    comps,fg,lab,lines=find_frames(a,zones=[(0,0,200,26),(0,116,320,132),(0,230,320,246),(520,230,800,248),(0,345,320,362),(0,460,320,476)])
    print('líneas',lines,'cuadros',len(comps))
    rows=[];cur=[]
    for c in sorted(comps,key=lambda c:(c['box'][1]+c['box'][3])/2):
        yc=(c['box'][1]+c['box'][3])/2
        if cur and yc-np.mean([(q['box'][1]+q['box'][3])/2 for q in cur])>40: rows.append(cur);cur=[]
        cur.append(c)
    rows.append(cur)
    for r in rows: print(len(r),[(c['box'][0],c['box'][1],c['box'][3]) for c in sorted(r,key=lambda c:c['box'][0])])

CW,CH,AX,AY=200,130,100,116
TARGET=88.0
def build_atlas(name, path, layout, zones, mirror_down=False):
    a=np.asarray(Image.open(path).convert('RGB')).astype(int)
    comps,fg,lab,lines=find_frames(a,zones=zones)
    rows=[];cur=[]
    for c in sorted(comps,key=lambda c:(c['box'][1]+c['box'][3])/2):
        yc=(c['box'][1]+c['box'][3])/2
        if cur and yc-np.mean([(q['box'][1]+q['box'][3])/2 for q in cur])>40: rows.append(cur);cur=[]
        cur.append(c)
    rows.append(cur)
    rows=[sorted(r_,key=lambda c:c['box'][0]) for r_ in rows]
    def pick(spec):
        return [rows[ri][ci] for ri,ci in spec]
    poses={k:pick(v) for k,v in layout.items()}
    idle=poses['reposo'][0]['box']; sc=TARGET/(idle[3]-idle[1])
    print(name,'escala',round(sc,3))
    rgb=Image.fromarray(a.astype(np.uint8),'RGB')
    atlas_rows=[];meta={}
    for pose,cs in poses.items():
        frames=[];mz=[]
        for c in cs:
            x0,y0,x1,y1=c['box']
            m=np.isin(lab[y0:y1,x0:x1],c['ids'])&fg[y0:y1,x0:x1]
            m=ndi.binary_closing(m,iterations=1)
            sub=np.dstack([a[y0:y1,x0:x1],(m*255)]).astype(np.uint8)
            fr=Image.fromarray(sub,'RGBA')
            fr=fr.resize((max(1,round(fr.width*sc)),max(1,round(fr.height*sc))),Image.LANCZOS)
            mm=np.asarray(fr)[:,:,3]>40
            ys,xs=np.nonzero(mm); h=ys.max()-ys.min()+1
            if pose=='muerte': ax_=int(xs.mean())
            else:
                sel=(ys>=ys.min()+0.35*h)&(ys<=ys.min()+0.62*h); ax_=int(xs[sel].mean()) if sel.any() else int(xs.mean())
            can=Image.new('RGBA',(CW,CH),(0,0,0,0)); can.alpha_composite(fr,(AX-ax_,AY-fr.height))
            frames.append(can)
            mk=np.asarray(can)[:,:,3]>40; ys2,xs2=np.nonzero(mk); j=xs2.argmax(); mz.append([int(xs2[j]-AX),int(ys2[j]-AY)])
        atlas_rows.append((pose,frames)); meta[pose]=dict(n=len(frames),muzzle=mz)
    Wd=max(len(f) for _,f in atlas_rows)*CW; Ht=len(atlas_rows)*CH
    atlas=Image.new('RGBA',(Wd,Ht),(0,0,0,0))
    for ri,(pose,frames) in enumerate(atlas_rows):
        meta[pose]['row']=ri
        for ci,fr in enumerate(frames): atlas.alpha_composite(fr,(ci*CW,ri*CH))
    atlas.save('/home/user/FinalLegacy/soldados/%s.png'%name,optimize=True)
    meta['_canvas']=[CW,CH,AX,AY]
    json.dump(meta,open('/home/user/FinalLegacy/soldados/%s.json'%name,'w'),indent=1)
    prev=Image.new('RGBA',atlas.size,(60,70,90,255)); prev.alpha_composite(atlas)
    from PIL import ImageDraw
    d=ImageDraw.Draw(prev)
    for ri in range(len(atlas_rows)): d.line([(0,ri*CH+AY),(Wd,ri*CH+AY)],fill=(255,80,80),width=1)
    prev.save('/tmp/claude-0/-home-user-FinalLegacy/ed78837b-9164-5456-a212-e556937b17f3/scratchpad/atlas_%s.png'%name)
if __name__=='__main__':
    D='/tmp/claude-0/-home-user-FinalLegacy/ed78837b-9164-5456-a212-e556937b17f3/'
    zones=[(0,0,200,26),(0,116,320,132),(0,230,320,246),(520,230,800,248),(0,345,320,362),(0,460,320,476)]
    build_atlas('cuchillero',D+'images/55.png',
        {'correr':[(0,i) for i in range(8)],'reposo':[(1,i) for i in range(4)],'agachado':[(2,0)],'salto':[(2,1)],'caida':[(2,2)],
         'granada_preparar':[(2,3)],'granada_lanzar':[(2,4)],'ataque':[(3,0)],
         'muerte':[(4,0),(3,1),(3,2),(3,3),(3,4),(3,6)]},zones)
