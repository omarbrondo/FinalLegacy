"""Corta las 6 islas de la hoja (fondo de mar liso) en soldados/isla_0..5.png (con transparencia en el mar) y soldados/islas.json (centro y radio de la costa por ángulo).
Orden: chica, mediana, grande, muy grande, con ciudad 90, con ciudad 110.   Uso: python herramientas/islas_cenital.py hoja.webp   Necesita: pillow numpy scipy"""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
CELLS = [(0, 30, 345, 285), (345, 30, 690, 285), (690, 30, 1024, 285), (0, 318, 345, 572), (345, 318, 690, 572), (690, 318, 1024, 572)]
def main(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(float)
    ocean = np.median(a[40:70, 330:345].reshape(-1, 3), axis=0); print('mar', ocean)
    meta = {}
    for i, (x0, y0, x1, y1) in enumerate(CELLS):
        c = a[y0:y1, x0:x1]
        d = np.abs(c - ocean).sum(axis=2)
        al = np.clip((d - 14) / 46.0, 0, 1)
        land = ((c[:, :, 0] > c[:, :, 2] - 5) | (c[:, :, 1] > c[:, :, 2] + 4)) & (c.min(axis=2) < 200) & (d > 60)
        land = ndi.binary_opening(ndi.binary_closing(land, iterations=2), iterations=2)
        lab, n = ndi.label(land); k = np.bincount(lab.ravel())[1:].argmax() + 1; land = ndi.binary_fill_holes(lab == k)
        cy, cx = ndi.center_of_mass(land)
        ra = []
        for t in range(360):
            th = np.radians(t); r = 0
            for rr in np.arange(2, 250, 0.5):
                px, py = int(cx + rr * np.cos(th)), int(cy + rr * np.sin(th))
                if 0 <= py < land.shape[0] and 0 <= px < land.shape[1] and land[py, px]: r = rr
            ra.append(float(r))
        meta['isla_%d' % i] = dict(cx=float(cx), cy=float(cy), ra=ra)
        print(i, 'centro', round(cx), round(cy), 'radio medio', round(float(np.mean(ra)), 1))
        Image.fromarray(np.dstack([c, al * 255]).astype(np.uint8), 'RGBA').save(os.path.join(out, 'isla_%d.png' % i))
    json.dump(meta, open(os.path.join(out, 'islas.json'), 'w'))
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
