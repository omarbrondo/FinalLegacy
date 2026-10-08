"""Corta las explosiones (2 tiras de 5 cuadros) y las balas de la hoja de efectos -> soldados/efecto_boom_s.png, efecto_boom_b.png, efecto_bala_a.png, efecto_bala_e.png.
Uso: python herramientas/efectos_cenital.py hoja.webp     Necesita: pip install pillow numpy"""
import sys, os
import numpy as np
from PIL import Image
CX = [105, 305, 510, 710, 910]
CW, CH = 206, 200
def soft(a, bg):
    d = np.abs(a - bg).sum(axis=2)
    return np.clip((d - 14) / 45.0, 0, 1)
def main(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(float)
    for name, cy in (('s', 124), ('b', 334)):
        bg = np.median(a[cy - 90:cy + 90, 4:30].reshape(-1, 3), axis=0)
        strip = Image.new('RGBA', (CW * 5, CH), (0, 0, 0, 0))
        for i, cx in enumerate(CX):
            c = a[cy - CH // 2:cy + CH // 2, cx - CW // 2:cx + CW // 2]
            al = soft(c, bg)
            strip.alpha_composite(Image.fromarray(np.dstack([c, al * 255]).astype(np.uint8), 'RGBA'), (CW * i, 0))
        strip.save(os.path.join(out, 'efecto_boom_%s.png' % name))
    bgb = np.median(a[500:700, 4:30].reshape(-1, 3), axis=0)
    for name, (x0, y0, x1, y1) in (('a', (40, 520, 220, 590)), ('e', (55, 612, 220, 682))):
        c = a[y0:y1, x0:x1]; al = soft(c, bgb)
        sp = Image.fromarray(np.dstack([c, al * 255]).astype(np.uint8), 'RGBA'); sp = sp.crop(sp.getbbox())
        pad = Image.new('RGBA', (sp.width * 2, sp.height), (0, 0, 0, 0)); pad.alpha_composite(sp, (sp.width, 0))   # la cabeza de la bala queda al centro
        pad.save(os.path.join(out, 'efecto_bala_%s.png' % name))
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
