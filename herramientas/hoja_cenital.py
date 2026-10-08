"""Convierte la hoja de soldados cenitales (13 filas x 4 cuadros de caminata, fondo liso, rótulos) en soldados/top_<clave>.png (4 cuadros de 84x84).
Uso: python herramientas/hoja_cenital.py hoja.png     Necesita: pip install pillow numpy scipy"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
KEYS = ['p', 'pf', 'a', 'af', 'e_rifle', 'ef_rifle', 'e_rpg', 'ef_rpg', 'e_gren', 'ef_gren', 'e_sniper', 'ef_sniper', 'e_mg']
CELL, SC = 84, 0.85
def main(src, out):
    im = Image.open(src).convert('RGB'); a = np.asarray(im).astype(int)
    fg = np.abs(a - a[2, 300]).sum(axis=2) > 40
    lab, n = ndi.label(ndi.binary_dilation(fg, iterations=3))
    boxes = [s for s in ndi.find_objects(lab) if s[0].stop - s[0].start > 40]
    rows = []
    for s in sorted(boxes, key=lambda s: s[0].start):
        if rows and abs(rows[-1][0][0].start - s[0].start) < 30: rows[-1].append(s)
        else: rows.append([s])
    for key, row in zip(KEYS, rows):
        sheet = Image.new('RGBA', (CELL * 4, CELL), (0, 0, 0, 0))
        for i, s in enumerate(sorted(row, key=lambda s: s[1].start)[:4]):
            y0, y1, x0, x1 = s[0].start - 2, s[0].stop + 2, s[1].start - 2, s[1].stop + 2
            crop = a[y0:y1, x0:x1]
            solid = np.abs(crop - a[2, 300]).sum(axis=2) > 40
            solid = ndi.binary_fill_holes(ndi.binary_closing(solid, iterations=1))
            solid = ndi.binary_opening(solid, iterations=1)
            alpha = (solid * 255).astype(np.uint8)
            rgba = np.dstack([crop.astype(np.uint8), alpha])
            sp = Image.fromarray(rgba, 'RGBA')
            sp = sp.resize((max(1, round(sp.width * SC)), max(1, round(sp.height * SC))), Image.LANCZOS)
            m = np.asarray(sp)[:, :, 3] > 0
            cy, cx = ndi.center_of_mass(m)
            sheet.alpha_composite(sp, (int(round(CELL * i + CELL / 2 - cx)), int(round(CELL / 2 - cy))))
        sheet.save(os.path.join(out, 'top_%s.png' % key))
        print(key, len(row))
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
