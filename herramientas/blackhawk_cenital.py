"""Corta el Blackhawk (fuselaje en lienzo de 130x152 con el mástil en (65,76)), el rotor y los objetivos aire-tierra de la hoja -> soldados/bh_*.png y soldados/heli_<tipo>_<parte>.png.
Las partes de los objetivos se guardan recortadas; el juego las ajusta al tamaño y al pivote de las originales (heli_art.make_heli_targets).
Uso: python herramientas/blackhawk_cenital.py hoja.png     Necesita: pillow numpy scipy"""
import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'soldados')
# (clave, parte): punto dentro del cuadro en la hoja; fracción vertical del pivote (para las partes que giran)
POINTS = {'bh': (100, 160), 'rotor': (305, 92),
          ('aa', 'base'): (55, 323), ('aa', 'top'): (194, 314), ('aa', 'wreck'): (337, 322),
          ('bunker', 'base'): (65, 500), ('bunker', 'top'): (222, 485), ('bunker', 'wreck'): (380, 500),
          ('sam', 'base'): (63, 637), ('sam', 'top'): (205, 626), ('sam', 'wreck'): (347, 640),
          ('depot', 'base'): (75, 830), ('depot', 'wreck'): (245, 811),
          ('radar', 'base'): (54, 953), ('radar', 'top'): (195, 941), ('radar', 'wreck'): (335, 952)}
YMAX = {('bunker', 'base'): 548, ('depot', 'base'): 866, ('sam', 'base'): 690, ('bunker', 'wreck'): 560}     # recorte de los rótulos que tocan el dibujo


def main(src):
    a = np.asarray(Image.open(src).convert('RGB')).astype(float)
    bg = ndi.median_filter(a[::4, ::4], size=(15, 15, 1)); bg = np.kron(bg, np.ones((4, 4, 1)))[:a.shape[0], :a.shape[1]]
    fg = np.abs(a - bg).sum(axis=2) > 45
    white = a.min(axis=2) > 205
    lab, n = ndi.label(ndi.binary_dilation(fg & ~white, iterations=3)); sl = ndi.find_objects(lab)
    def cut(pt, ymax=None):
        best = None
        for i, q in enumerate(sl, 1):
            if q[1].start <= pt[0] < q[1].stop and q[0].start <= pt[1] < q[0].stop and (q[0].stop - q[0].start) > 18:
                ar = (q[0].stop - q[0].start) * (q[1].stop - q[1].start)
                if best is None or ar < best[0]: best = (ar, i, q)
        _, i, q = best
        sub = (lab[q] == i) & ndi.binary_dilation(fg[q] & ~white[q], iterations=1)
        if ymax is not None:
            sub[max(0, ymax - q[0].start):, :] = False
        al = np.clip(np.abs(a[q] - bg[q]).sum(axis=2) / 70.0, 0, 1) * ndi.binary_dilation(sub, iterations=2)
        img = Image.fromarray(np.dstack([a[q], al * 255]).astype(np.uint8), 'RGBA')
        return img.crop(img.getbbox())
    for key, pt in POINTS.items():
        if key in ('bh', 'rotor'):
            continue
        cut(pt, YMAX.get(key)).save(os.path.join(OUT, 'heli_%s_%s.png' % key))
    f = cut(POINTS["bh"]); k = 0.83                                         # fuselaje: mástil en (65,76) de un lienzo de 130x152
    f = f.resize((round(f.width * k), round(f.height * k)), Image.LANCZOS)
    hub = (59.3 * k, 94.3 * k)
    can = Image.new('RGBA', (130, 152), (0, 0, 0, 0)); can.alpha_composite(f, (round(65 - hub[0]), round(76 - hub[1])))
    can.save(os.path.join(OUT, 'bh_fuselaje.png'))
    r = cut(POINTS['rotor']); side = max(r.size); sq = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    sq.alpha_composite(r, ((side - r.width) // 2, (side - r.height) // 2)); sq.save(os.path.join(OUT, 'bh_rotor.png'))
if __name__ == '__main__':
    main(sys.argv[1])
