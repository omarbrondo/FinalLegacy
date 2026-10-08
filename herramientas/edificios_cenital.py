"""Corta el ayuntamiento y los 5 edificios de la hoja -> soldados/edif_hall.png y edif_0..4.png (techo arriba y fachada con ventanas abajo).
Uso: python herramientas/edificios_cenital.py hoja.png     Necesita: pip install pillow numpy scipy"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
BOXES = {'edif_hall': (20, 45, 255, 267), 'edif_0': (293, 45, 491, 204), 'edif_1': (550, 45, 747, 207), 'edif_2': (807, 45, 1003, 207),
         'edif_3': (20, 323, 216, 483), 'edif_4': (293, 323, 489, 483)}
def main(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(float)
    bg = ndi.median_filter(a[::4, ::4], size=(15, 15, 1)); bg = np.kron(bg, np.ones((4, 4, 1)))[:a.shape[0], :a.shape[1]]
    fg = np.abs(a - bg).sum(axis=2) > 60
    for name, (x0, y0, x1, y1) in BOXES.items():
        lab, n = ndi.label(ndi.binary_dilation(fg[y0:y1, x0:x1], iterations=3))
        k = np.bincount(lab.ravel())[1:].argmax() + 1
        m = ndi.binary_fill_holes((lab == k) & ndi.binary_dilation(fg[y0:y1, x0:x1], iterations=1))
        sp = Image.fromarray(np.dstack([a[y0:y1, x0:x1], m * 255]).astype(np.uint8), 'RGBA'); sp.crop(sp.getbbox()).save(os.path.join(out, name + '.png'))
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
