"""Corta los autos cenitales verticales (frente hacia arriba) de la hoja en soldados/autos.png: 7 colores y 3 quemados, celdas de 90x170.
Uso: python herramientas/autos_cenital.py hoja.webp     Necesita: pip install pillow numpy scipy"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
BOXES = [(14, 407, 93, 565), (95, 407, 172, 565), (176, 407, 255, 565), (256, 407, 337, 565), (338, 407, 417, 565), (419, 407, 497, 565), (499, 407, 577, 565),
         (632, 407, 718, 566), (762, 408, 848, 564), (893, 410, 972, 566)]
CW, CH = 90, 170
def main(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(float)
    bg = ndi.median_filter(a[::4, ::4], size=(15, 15, 1)); bg = np.kron(bg, np.ones((4, 4, 1)))[:a.shape[0], :a.shape[1]]
    fg = np.abs(a - bg).sum(axis=2) > 60; fg[:405] = False
    lab, n = ndi.label(ndi.binary_dilation(fg, iterations=3))
    strip = Image.new('RGBA', (CW * len(BOXES), CH), (0, 0, 0, 0))
    for i, (x0, y0, x1, y1) in enumerate(BOXES):
        k = np.bincount(lab[y0:y1, x0:x1].ravel())[1:].argmax() + 1
        m = ndi.binary_fill_holes((lab[y0:y1, x0:x1] == k) & ndi.binary_dilation(fg[y0:y1, x0:x1], iterations=1))
        sp = Image.fromarray(np.dstack([a[y0:y1, x0:x1], m * 255]).astype(np.uint8), 'RGBA'); sp = sp.crop(sp.getbbox())
        strip.alpha_composite(sp, (CW * i + (CW - sp.width) // 2, (CH - sp.height) // 2))
    strip.save(os.path.join(out, 'autos.png'))
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
