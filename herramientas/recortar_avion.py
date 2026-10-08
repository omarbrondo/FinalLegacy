"""Quita el fondo (liso o de tablero gris falso) de la imagen de un avión generada con IA y la recorta al contorno.

Uso:  python herramientas/recortar_avion.py entrada.jpg salida.png [tolerancia_gris=6] [radio_apertura=9] [tolerancia_rojo=0] ["x0,y0,x1,y1 ..." cajas con fondo atrapado a borrar] [erosion_anticolado=0]
Después se reduce a ~640 px de ancho y se guarda en aviones/ (ver aviones/LEEME.txt). Necesita: pip install pillow numpy scipy
"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
src=sys.argv[1]; out=sys.argv[2]
im=Image.open(src).convert('RGB')
a=np.asarray(im).astype(int)
lum=a.mean(axis=2)
tol=int(sys.argv[3]) if len(sys.argv)>3 else 6
red=int(sys.argv[5]) if len(sys.argv)>5 else 0
neutral=(np.abs(a[:,:,1]-a[:,:,2])<=tol)&((a[:,:,0]-a[:,:,1])<=max(tol,red))&((a[:,:,1]-a[:,:,0])<=tol)
edge=np.concatenate([lum[:30].ravel(),lum[-30:].ravel(),lum[:,:30].ravel(),lum[:,-30:].ravel()])
lo,hi=np.percentile(edge,1)-8,np.percentile(edge,99)+8                    # rango de grises del tablero (oscuro o claro), medido en los bordes
passable=neutral&(lum>=lo)&(lum<=hi)
leak=int(sys.argv[7]) if len(sys.argv) > 7 else 0                       # si el fondo se 'cuela' por un hueco del contorno, se separa erosionando antes de etiquetar
core=ndi.binary_erosion(passable,iterations=leak,border_value=1) if leak else passable
lab,n=ndi.label(core)
border=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
bg=np.isin(lab,list(border))
if leak:
    bg=ndi.binary_dilation(bg,iterations=leak+1)&passable
lab=ndi.label(passable)[0]
pockets=np.zeros_like(bg)
for bx in (sys.argv[6].split() if len(sys.argv) > 6 else []):          # fondo atrapado dentro del avión: cajas 'x0,y0,x1,y1' de la imagen original donde se borran los grises claros
    x0,y0,x1,y1=[int(v) for v in bx.split(',')]
    box=np.zeros_like(bg); box[y0:y1,x0:x1]=True
    pockets|=box&(np.abs(a[:,:,1]-a[:,:,2])<=tol)&(np.abs(a[:,:,0]-a[:,:,1])<=tol)&(lum>=lo)
alpha=~bg
lab2,n2=ndi.label(alpha)
sizes=ndi.sum(alpha,lab2,range(1,n2+1))
alpha=lab2==(1+int(np.argmax(sizes)))
alpha=ndi.binary_fill_holes(alpha)
r=int(sys.argv[4]) if len(sys.argv)>4 else 9
yy,xx=np.ogrid[-r:r+1,-r:r+1]
disk=(xx*xx+yy*yy)<=r*r
alpha&=~pockets                                                      # los bolsillos de fondo se quitan después de rellenar huecos
alpha=ndi.binary_opening(alpha,structure=disk)
lab3,n3=ndi.label(alpha)
alpha=lab3==(1+int(np.argmax(ndi.sum(alpha,lab3,range(1,n3+1)))))
alpha=ndi.binary_erosion(alpha,iterations=2)
print('cobertura',round(float(alpha.mean()),3))
al=ndi.gaussian_filter(alpha.astype(float),1.2)
rgba=np.dstack([a.astype(np.uint8),(np.clip(al*255,0,255)).astype(np.uint8)])
img=Image.fromarray(rgba,'RGBA')
bb=img.getbbox(); print('bbox',bb)
img=img.crop(bb)
img.save(out)
prev=Image.new('RGBA',img.size,(40,90,150,255)); prev.alpha_composite(img)
prev.thumbnail((1000,1000)); prev.save(out.replace('.png','_prev.png'))
