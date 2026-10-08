"""Corta los cuadros de muerte de los soldados cenitales (bloque derecho de la hoja: 3 cuadros por fila) en soldados/muerte_<clave>.png (3 cuadros de 120x120).
Uso: python herramientas/muertes_cenital.py hoja.png     Necesita: pip install pillow numpy scipy"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
KEYS = ['p', 'pf', 'a', 'e_rifle', 'e_rpg', 'e_gren', 'e_sniper', 'e_mg']
ROW_Y = [45, 120, 190, 262, 332, 400, 468, 540]
COL_X = [708, 830, 960]
CELL, SC = 120, 0.73
def main(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(float)
    bg = ndi.median_filter(a[::4, ::4], size=(15, 15, 1)); bg = np.kron(bg, np.ones((4, 4, 1)))[:a.shape[0], :a.shape[1]]
    fg = np.abs(a - bg).sum(axis=2) > 60
    lab, n = ndi.label(ndi.binary_dilation(fg, iterations=4)); sl = ndi.find_objects(lab)
    for key, y in zip(KEYS, ROW_Y):
        sheet = Image.new('RGBA', (CELL * 3, CELL), (0, 0, 0, 0))
        for i, x in enumerate(COL_X):
            c = [(k, s) for k, s in enumerate(sl, 1) if s[1].start <= x < s[1].stop and s[0].start <= y < s[0].stop and s[0].stop - s[0].start > 20]
            k, s = min(c, key=lambda t: (t[1][0].stop - t[1][0].start) * (t[1][1].stop - t[1][1].start))
            y0, y1, x0, x1 = s[0].start, s[0].stop, s[1].start, s[1].stop
            m = (lab[y0:y1, x0:x1] == k) & ndi.binary_dilation(fg[y0:y1, x0:x1], iterations=1)
            m = ndi.binary_closing(m, iterations=1)
            sp = Image.fromarray(np.dstack([a[y0:y1, x0:x1], m * 255]).astype(np.uint8), 'RGBA')
            sp = sp.resize((max(1, round(sp.width * SC)), max(1, round(sp.height * SC))), Image.LANCZOS)
            cy, cx = ndi.center_of_mass(np.asarray(sp)[:, :, 3] > 40)
            sheet.alpha_composite(sp, (int(round(CELL * i + CELL / 2 - cx)), int(round(CELL / 2 - cy))))
        sheet.save(os.path.join(out, 'muerte_%s.png' % key)); print(key)
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
