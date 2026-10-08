"""Corta árbol, contenedor, cajas, granada, antena y 4 autos extra de la hoja de elementos cenitales -> soldados/*.png (autos2.png = 4 celdas de 90x170).
Uso: python herramientas/elementos_cenital.py hoja.png     Necesita: pip install pillow numpy scipy"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ITEMS = {'arbol': (23, 46, 178, 200), 'contenedor': (841, 79, 1012, 157), 'caja_med': (70, 282, 129, 352), 'caja_gren': (253, 282, 324, 351),
         'caja_mask': (446, 282, 507, 351), 'granada': (621, 296, 659, 335), 'antena': (10, 422, 73, 558)}
CARS = [(538, 33, 613, 201), (614, 33, 686, 201), (687, 33, 762, 201), (763, 33, 840, 201)]
def main(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(float)
    bg = ndi.median_filter(a[::4, ::4], size=(15, 15, 1)); bg = np.kron(bg, np.ones((4, 4, 1)))[:a.shape[0], :a.shape[1]]
    fg = np.abs(a - bg).sum(axis=2) > 60
    def cut(box):
        x0, y0, x1, y1 = box
        lab, n = ndi.label(ndi.binary_dilation(fg[y0:y1, x0:x1], iterations=3))
        k = np.bincount(lab.ravel())[1:].argmax() + 1
        m = ndi.binary_fill_holes((lab == k) & ndi.binary_dilation(fg[y0:y1, x0:x1], iterations=1))
        sp = Image.fromarray(np.dstack([a[y0:y1, x0:x1], m * 255]).astype(np.uint8), 'RGBA'); return sp.crop(sp.getbbox())
    for name, b in ITEMS.items(): cut(b).save(os.path.join(out, name + '.png'))
    strip = Image.new('RGBA', (90 * 4, 170), (0, 0, 0, 0))
    for i, b in enumerate(CARS):
        sp = cut(b); strip.alpha_composite(sp, (90 * i + (90 - sp.width) // 2, (170 - sp.height) // 2))
    strip.save(os.path.join(out, 'autos2.png'))
if __name__ == '__main__':
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados'))
