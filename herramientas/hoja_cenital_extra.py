"""Corta la hoja de coberturas/lancha/perro (fondo liso, rótulos) en soldados/cob_*.png, lancha.png y perro.png (4 cuadros de 64x64).
Uso: python herramientas/hoja_cenital_extra.py hoja.png     Necesita: pip install pillow numpy scipy"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
def cut(a, bg, box):
    x0, y0, x1, y1 = box
    c = a[y0:y1, x0:x1]
    d = np.abs(c - bg).sum(axis=2)
    al = np.clip((d - 45) / 30.0, 0, 1)                       # sombras y fondo -> transparentes
    al = ndi.binary_opening(al > 0.5, iterations=1) * al
    img = Image.fromarray(np.dstack([c.astype(np.uint8), (al * 255).astype(np.uint8)]), 'RGBA')
    return img.crop(img.getbbox())
def main(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(int); bg = a[5, 300]
    d = np.abs(a - bg).sum(axis=2)
    lab, n = ndi.label(ndi.binary_dilation(d > 60, iterations=4))
    boxes = [(s[1].start, s[0].start, s[1].stop, s[0].stop) for s in ndi.find_objects(lab) if s[0].stop - s[0].start > 100]
    top = sorted([b for b in boxes if b[1] < 290], key=lambda b: b[0])
    dogs = sorted([b for b in boxes if b[1] >= 290], key=lambda b: b[0])
    for name, b in zip(('cob_sandbag', 'cob_rock', 'cob_crates', 'lancha'), top):
        cut(a, bg, b).save(os.path.join(out, name + '.png'))
    cell = 64; strip = Image.new('RGBA', (cell * 4, cell), (0, 0, 0, 0))
    for i, b in enumerate(dogs[:4]):
        sp = cut(a, bg, b); k = 46.0 / sp.height
        sp = sp.resize((max(1, round(sp.width * k)), 46), Image.LANCZOS)
        cy, cx = ndi.center_of_mass(np.asarray(sp)[:, :, 3] > 0)
        strip.alpha_composite(sp, (int(round(cell * i + cell / 2 - cx)), int(round(cell / 2 - cy))))
    strip.save(os.path.join(out, 'perro.png'))
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
