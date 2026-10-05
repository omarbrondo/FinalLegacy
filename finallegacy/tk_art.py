"""Texturas y modelo 3D de tanques para el combate urbano en primera persona."""
import math
import pygame
import random
from .common import clamp, lerp, shade


TK_FOG = (96, 64, 92)        # color de la bruma del atardecer


TK_NL = 10                   # niveles de bruma por distancia


def _grain(s, base, var, rnd, step=2):
    w, h = s.get_size()
    for y in range(0, h, step):
        for x in range(0, w, step):
            d = rnd.randint(-var, var)
            pygame.draw.rect(s, (clamp(base[0] + d, 0, 255), clamp(base[1] + d, 0, 255), clamp(base[2] + d, 0, 255)),
                             (x, y, step, step))


def _window(s, x, y, w, h, rnd, lit=None, frame=(150, 146, 140), arch=False):
    pygame.draw.rect(s, shade(frame, -60), (x - 2, y - 2, w + 4, h + 4), border_radius=3 if arch else 1)
    pygame.draw.rect(s, frame, (x - 1, y - 1, w + 2, h + 2), border_radius=3 if arch else 1)
    lit = rnd.random() < 0.34 if lit is None else lit
    for i in range(h):
        f = i / max(1, h - 1)
        if lit:
            c = (int(lerp(255, 214, f)), int(lerp(224, 150, f)), int(lerp(150, 70, f)))
        else:
            c = (int(lerp(60, 18, f)), int(lerp(86, 28, f)), int(lerp(124, 52, f)))
        pygame.draw.line(s, c, (x, y + i), (x + w - 1, y + i))
    if not lit:
        pygame.draw.line(s, (130, 160, 200), (x + 2, y + h - 3), (x + w // 2, y + 2), 1)
    pygame.draw.line(s, shade(frame, -40), (x + w // 2, y), (x + w // 2, y + h - 1), 1)
    pygame.draw.rect(s, shade(frame, 24), (x - 3, y + h, w + 6, 3))


def tex_brick(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    s.fill((78, 66, 60))
    base = rnd.choice(((150, 70, 52), (138, 82, 58), (120, 60, 56)))
    for r in range(0, 128, 8):
        off = 8 if (r // 8) % 2 else 0
        for c in range(-16, 128, 16):
            d = rnd.randint(-16, 16)
            pygame.draw.rect(s, (clamp(base[0] + d, 0, 255), clamp(base[1] + d // 2, 0, 255), clamp(base[2] + d // 2, 0, 255)),
                             (c + off, r, 15, 7))
    for wx in (16, 82):
        for wy in (12, 70):
            _window(s, wx, wy, 30, 40, rnd)
    return s


def tex_concrete(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    _grain(s, rnd.choice(((132, 134, 140), (150, 148, 142), (118, 124, 132))), 9, rnd)
    for x in (0, 64):
        pygame.draw.line(s, (80, 82, 88), (x, 0), (x, 127), 2)
    for y in (0, 64):
        pygame.draw.line(s, (80, 82, 88), (0, y), (127, y), 2)
    for by in (14, 78):
        for bx in range(8, 120, 38):
            _window(s, bx, by, 26, 30, rnd, frame=(196, 196, 200))
    return s


def tex_glass(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    for gy in range(0, 128, 32):
        for gx in range(0, 128, 32):
            lit = rnd.random() < 0.3
            for i in range(32):
                f = (gy + i) / 128
                if lit:
                    c = (int(lerp(255, 220, f)), int(lerp(230, 170, f)), int(lerp(160, 90, f)))
                else:
                    c = (int(lerp(88, 24, f)), int(lerp(150, 70, f)), int(lerp(180, 110, f)))
                pygame.draw.line(s, c, (gx, gy + i), (gx + 31, gy + i))
            if not lit:
                pygame.draw.line(s, (200, 230, 245), (gx + 4, gy + 28), (gx + 20, gy + 4), 2)
    for k in range(0, 128, 32):
        pygame.draw.line(s, (26, 32, 40), (k, 0), (k, 127), 3)
        pygame.draw.line(s, (26, 32, 40), (0, k), (127, k), 3)
    return s


def tex_sand(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    base = rnd.choice(((190, 164, 118), (176, 150, 108)))
    _grain(s, base, 8, rnd)
    for r in range(0, 128, 16):
        pygame.draw.line(s, shade(base, -46), (0, r), (127, r), 1)
        off = 0 if (r // 16) % 2 else 24
        for c in range(off, 128, 48):
            pygame.draw.line(s, shade(base, -46), (c, r), (c, r + 15), 1)
    for wx in (20, 80):
        for wy in (22, 78):
            _window(s, wx, wy, 26, 34, rnd, frame=(224, 214, 190), arch=True)
    return s


def tex_hall(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    _grain(s, (206, 212, 226), 6, rnd)
    for x in range(0, 128, 32):
        pygame.draw.rect(s, (236, 240, 248), (x, 0, 8, 128))
        pygame.draw.rect(s, (150, 156, 172), (x + 8, 0, 2, 128))
        pygame.draw.rect(s, (252, 220, 140), (x - 2, 0, 12, 6))
        pygame.draw.rect(s, (252, 220, 140), (x - 2, 122, 12, 6))
    for x in range(8, 128, 32):
        for y in (14, 74):
            for i in range(44):
                f = i / 43
                pygame.draw.line(s, (int(lerp(255, 230, f)), int(lerp(236, 170, f)), int(lerp(170, 90, f))),
                                 (x + 3, y + i), (x + 22, y + i))
            pygame.draw.rect(s, (252, 220, 140), (x + 2, y - 1, 21, 46), 1)
    pygame.draw.line(s, (252, 220, 140), (0, 60), (127, 60), 3)
    return s


def tex_missile():
    s = pygame.Surface((64, 64))
    for y in range(64):
        v = int(lerp(236, 120, abs(y - 28) / 40))
        pygame.draw.line(s, (v, v, min(255, v + 10)), (0, y), (63, y))
    pygame.draw.rect(s, (214, 50, 40), (0, 20, 64, 8))
    pygame.draw.rect(s, (40, 40, 46), (0, 38, 64, 4))
    return s


def tex_car(col, seed):
    """Carrocería de auto: faldón oscuro abajo, pintura con brillo y línea de luces."""
    rnd = random.Random(seed)
    s = pygame.Surface((64, 32))
    s.fill(col)
    for y in range(32):
        k = 1.0 + 0.22 * math.sin(y / 31 * 3.1416) - 0.1
        pygame.draw.line(s, tuple(clamp(int(c * k), 0, 255) for c in col), (0, y), (63, y))
    pygame.draw.rect(s, (24, 24, 28), (0, 24, 64, 8))
    for wx in (12, 46):
        pygame.draw.circle(s, (10, 10, 12), (wx, 26), 7)
        pygame.draw.circle(s, (120, 124, 130), (wx, 26), 3)
    pygame.draw.rect(s, (250, 240, 190), (1, 14, 4, 4))
    pygame.draw.rect(s, (200, 40, 40), (59, 14, 4, 4))
    pygame.draw.line(s, tuple(clamp(c + 50, 0, 255) for c in col), (0, 8), (63, 8))
    for _ in range(18):
        s.set_at((rnd.randrange(64), rnd.randrange(24)), tuple(clamp(c + rnd.randint(-14, 14), 0, 255) for c in col))
    return s


def tex_cabin():
    s = pygame.Surface((64, 32))
    s.fill((38, 56, 74))
    for y in range(32):
        pygame.draw.line(s, (int(lerp(70, 28, y / 31)), int(lerp(96, 44, y / 31)), int(lerp(120, 60, y / 31))), (0, y), (63, y))
    pygame.draw.polygon(s, (150, 190, 214), [(8, 0), (22, 0), (10, 31), (0, 31)])
    pygame.draw.rect(s, (30, 32, 36), (30, 0, 3, 32))
    pygame.draw.rect(s, (30, 32, 36), (0, 0, 64, 3))
    return s


def tex_crushed(seed, burnt=False):
    rnd = random.Random(seed)
    s = pygame.Surface((64, 32))
    base = (34, 30, 28) if burnt else (96, 100, 108)
    _grain(s, base, 14, rnd)
    for _ in range(9):
        x, y = rnd.randrange(64), rnd.randrange(32)
        pygame.draw.line(s, (12, 12, 14), (x, y), (x + rnd.randint(-18, 18), y + rnd.randint(-10, 10)), 2)
    if burnt:
        for _ in range(10):
            pygame.draw.circle(s, (rnd.randint(150, 230), rnd.randint(50, 100), 20), (rnd.randrange(64), rnd.randrange(32)), rnd.randint(1, 3))
    else:
        pygame.draw.rect(s, (24, 24, 28), (0, 24, 64, 8))
    return s


def tex_pole():
    s = pygame.Surface((8, 32))
    for x in range(8):
        v = int(lerp(90, 190, x / 7)) if x < 4 else int(lerp(190, 70, (x - 4) / 3))
        pygame.draw.line(s, (v, v, v + 6), (x, 0), (x, 31))
    return s


def tex_lamp():
    s = pygame.Surface((16, 8))
    s.fill((255, 238, 180))
    pygame.draw.rect(s, (255, 252, 230), (2, 2, 12, 4))
    pygame.draw.rect(s, (90, 90, 96), (0, 0, 16, 1))
    return s


def tex_bike():
    s = pygame.Surface((32, 32))
    s.fill((20, 22, 26))
    pygame.draw.rect(s, (200, 50, 40), (0, 6, 32, 8))
    pygame.draw.rect(s, (170, 174, 180), (0, 22, 32, 2))
    return s


def tk_entry(tile, reps):
    tw, th = tile.get_size()
    tall = pygame.Surface((tw, th * reps))
    for r in range(reps):
        tall.blit(tile, (0, r * th))
    tall = tall.convert()
    var = []
    for L in range(TK_NL):
        f = L / (TK_NL - 1) * 0.9
        row = []
        for side_shade in (1.0, 0.6):
            v = tall.copy()
            m = int(255 * side_shade * (1 - f))
            v.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
            v.fill(tuple(int(c * f) for c in TK_FOG), special_flags=pygame.BLEND_RGB_ADD)
            row.append(v)
        var.append(row)
    return dict(tw=tw, th=th, reps=reps, var=var)


def make_tk_textures():
    T = {}
    T['bld'] = [tk_entry(tex_brick(1), 4), tk_entry(tex_brick(2), 4), tk_entry(tex_concrete(3), 4),
                tk_entry(tex_concrete(4), 4), tk_entry(tex_glass(5), 4), tk_entry(tex_sand(6), 4)]
    T['hall'] = tk_entry(tex_hall(7), 4)
    T['missile'] = tk_entry(tex_missile(), 1)
    cols = [(188, 46, 40), (40, 90, 170), (214, 196, 70), (210, 212, 216), (44, 130, 90), (210, 120, 40)]
    T['car'] = [tk_entry(tex_car(c, i), 1) for i, c in enumerate(cols)]
    T['cabin'] = tk_entry(tex_cabin(), 1)
    T['crushed'] = tk_entry(tex_crushed(5), 1)
    T['burnt'] = tk_entry(tex_crushed(6, True), 1)
    T['pole'] = tk_entry(tex_pole(), 1)
    T['lamp'] = tk_entry(tex_lamp(), 1)
    T['bike'] = tk_entry(tex_bike(), 1)
    return T


TK_PXU = 32.0       # píxeles por unidad de mundo en los sprites pre-renderizados


TK_ANG = 32         # ángulos de vista pre-renderizados


TK_PITCH = 12.0     # inclinación de la cámara (grados)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


class Solid:
    """Sólido convexo: caras (vértices, color) con normales hacia afuera, más detalles planos."""

    def __init__(self, faces, details=()):
        pts = [v for f, _ in faces for v in f]
        self.c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), sum(p[2] for p in pts) / len(pts))
        self.faces = []
        for verts, col in faces:
            n = _unit(_cross(_sub(verts[1], verts[0]), _sub(verts[2], verts[0])))
            fc = (sum(v[0] for v in verts) / len(verts), sum(v[1] for v in verts) / len(verts), sum(v[2] for v in verts) / len(verts))
            if n[0] * (fc[0] - self.c[0]) + n[1] * (fc[1] - self.c[1]) + n[2] * (fc[2] - self.c[2]) < 0:
                n = (-n[0], -n[1], -n[2])
            self.faces.append((verts, col, n))
        self.details = list(details)


def s_box(x0, x1, y0, y1, z0, z1, col):
    v = lambda x, y, z: (x, y, z)
    f = [([v(x0, y0, z0), v(x1, y0, z0), v(x1, y1, z0), v(x0, y1, z0)], col), ([v(x0, y0, z1), v(x1, y0, z1), v(x1, y1, z1), v(x0, y1, z1)], col),
         ([v(x0, y0, z0), v(x0, y0, z1), v(x0, y1, z1), v(x0, y1, z0)], col), ([v(x1, y0, z0), v(x1, y0, z1), v(x1, y1, z1), v(x1, y1, z0)], col),
         ([v(x0, y0, z0), v(x1, y0, z0), v(x1, y0, z1), v(x0, y0, z1)], col), ([v(x0, y1, z0), v(x1, y1, z0), v(x1, y1, z1), v(x0, y1, z1)], col)]
    return Solid(f)


def s_extrude(profile, x0, x1, col, top_cols=None):
    """Perfil convexo (z, y) extruido a lo ancho entre x0 y x1."""
    n = len(profile)
    f = [([(x1, y, z) for z, y in profile], col), ([(x0, y, z) for z, y in profile], col)]
    for i in range(n):
        (za, ya), (zb, yb) = profile[i], profile[(i + 1) % n]
        c = top_cols[i] if top_cols else col
        f.append(([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)], c))
    return Solid(f)


def s_frustum(cx, cz, y0, y1, r0, r1, n, cols, rot=0.0, sx=1.0, sz=1.0):
    """Tronco de cono vertical (n lados); sx/sz lo achatan en elipse."""
    a = [(cx + math.cos(rot + 2 * math.pi * i / n) * r0 * sx, y0, cz + math.sin(rot + 2 * math.pi * i / n) * r0 * sz) for i in range(n)]
    b = [(cx + math.cos(rot + 2 * math.pi * i / n) * r1 * sx, y1, cz + math.sin(rot + 2 * math.pi * i / n) * r1 * sz) for i in range(n)]
    f = [(a, cols[0]), (b, cols[0])]
    for i in range(n):
        j = (i + 1) % n
        f.append(([a[i], a[j], b[j], b[i]], cols[i % len(cols)]))
    return Solid(f)


def s_cyl_z(cx, cy, z0, z1, r0, r1, n, col):
    """Cilindro/cono a lo largo del eje z (cañones)."""
    a = [(cx + math.cos(2 * math.pi * i / n) * r0, cy + math.sin(2 * math.pi * i / n) * r0, z0) for i in range(n)]
    b = [(cx + math.cos(2 * math.pi * i / n) * r1, cy + math.sin(2 * math.pi * i / n) * r1, z1) for i in range(n)]
    f = [(a, col), (b, col)]
    for i in range(n):
        j = (i + 1) % n
        f.append(([a[i], a[j], b[j], b[i]], col))
    return Solid(f)


def disc_x(x, y, z, r, n, col, nx):
    return ([(x, y + math.sin(2 * math.pi * i / n) * r, z + math.cos(2 * math.pi * i / n) * r) for i in range(n)], col, (nx, 0.0, 0.0))


def quad_x(x, y0, y1, z0, z1, col, nx):
    return ([(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)], col, (nx, 0.0, 0.0))


def quad_y(y, x0, x1, z0, z1, col):
    return ([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], col, (0.0, 1.0, 0.0))


def build_tank_model(heavy, seed):
    rnd = random.Random(seed)
    if heavy:
        base, camo = (74, 82, 96), [(74, 82, 96), (58, 64, 78), (90, 98, 112), (66, 72, 86)]
        trim, barrel_c, S = (232, 140, 36), (52, 56, 66), 1.22
    else:
        base, camo = (96, 104, 62), [(96, 104, 62), (74, 82, 48), (128, 112, 70), (84, 70, 50)]
        trim, barrel_c, S = (200, 190, 120), (58, 62, 50), 1.0
    track_c, rubber, hub = (34, 34, 36), (20, 20, 22), (110, 112, 104)
    hull, tur = [], []

    def camo_c():
        return rnd.choice(camo)
    # cascos: carrocería inclinada, cada franja de la cubierta con un parche de camuflaje distinto
    prof = [(-3.2, 0.40), (-3.2, 1.12), (-2.45, 1.40), (1.55, 1.40), (3.3, 0.98), (3.3, 0.50), (2.75, 0.40)]
    tops = [camo_c() for _ in prof]
    hull.append(s_extrude(prof, -1.40, 1.40, base, tops))
    for sd in (-1, 1):
        xa, xb = (1.38, 2.04) if sd > 0 else (-2.04, -1.38)
        tprof = [(-3.1, 0.0), (3.0, 0.0), (3.65, 0.42), (3.65, 0.78), (3.05, 1.16), (-3.05, 1.16), (-3.55, 0.82), (-3.55, 0.34)]
        det = []
        xo = xb + 0.012 if sd > 0 else xa - 0.012
        nx = 1.0 if sd > 0 else -1.0
        for zc in (-2.35, -1.4, -0.45, 0.5, 1.45, 2.4):
            det.append(disc_x(xo, 0.52, zc, 0.43, 14, rubber, nx))
            det.append(disc_x(xo + nx * 0.01, 0.52, zc, 0.26, 12, hub, nx))
            det.append(disc_x(xo + nx * 0.02, 0.52, zc, 0.08, 8, rubber, nx))
        det.append(disc_x(xo, 0.62, -3.15, 0.46, 14, rubber, nx))
        det.append(disc_x(xo + nx * 0.01, 0.62, -3.15, 0.3, 12, hub, nx))
        det.append(disc_x(xo, 0.58, 3.15, 0.40, 14, rubber, nx))
        det.append(disc_x(xo + nx * 0.01, 0.58, 3.15, 0.24, 12, hub, nx))
        for k in range(-13, 14):
            z = k * 0.235
            det.append(quad_x(xo, 1.0, 1.15, z - 0.04, z + 0.04, (14, 14, 16), nx))
            det.append(quad_x(xo, 0.0, 0.14, z - 0.04, z + 0.04, (14, 14, 16), nx))
        tr = s_extrude(tprof, xa, xb, track_c)
        tr.details = det
        hull.append(tr)
        fx0, fx1 = (1.3, 2.12) if sd > 0 else (-2.12, -1.3)
        hull.append(s_box(fx0, fx1, 1.13, 1.27, -3.0, 3.25, base))
        if heavy:
            skx0, skx1 = (2.1, 2.2) if sd > 0 else (-2.2, -2.1)
            sk = s_box(skx0, skx1, 0.30, 1.12, -2.9, 2.5, camo_c())
            for k in range(7):
                z = -2.5 + k * 0.8
                sk.details.append(quad_x(skx1 + 0.01 if sd > 0 else skx0 - 0.01, 0.35, 0.95, z, z + 0.04, (20, 20, 24), nx))
            hull.append(sk)
        bx0, bx1 = (1.55, 1.95) if sd > 0 else (-1.95, -1.55)
        hull.append(s_box(bx0, bx1, 1.27, 1.52, -2.2, -1.5, (50, 52, 46)))
        hull.append(s_cyl_z(1.05 * sd, 1.18, -3.28, -3.02, 0.14, 0.12, 8, (28, 28, 30)))
        hull.append(s_cyl_z(0.95 * sd, 0.92, 3.3, 3.36, 0.14, 0.14, 8, (255, 232, 160)))
    deck = [quad_y(1.405, -1.1, 1.1, -2.35 + k * 0.38, -2.35 + k * 0.38 + 0.2, (24, 24, 26)) for k in range(5)]
    hull[0].details += deck
    hull[0].details.append(quad_y(1.41, -0.5, 0.5, 1.0, 1.4, (60, 60, 56)))
    hull.append(s_box(-0.32, 0.32, 1.40, 1.58, 1.05, 1.5, base))
    hull.append(s_box(-0.9, 0.9, 0.62, 1.0, 3.2, 3.32, base))
    # torreta redonda con cúpula y cañón largo (todo girable aparte)
    tc = [camo_c() for _ in range(14)]
    tur.append(s_frustum(0.0, 0.1, 1.40, 1.78, 1.45 * S, 1.52 * S, 14, tc, 0.0, 1.0, 1.1))
    tur.append(s_frustum(0.0, 0.1, 1.78, 2.22, 1.52 * S, 1.30 * S, 14, tc, 0.0, 1.0, 1.1))
    tur.append(s_frustum(0.0, 0.1, 2.22, 2.58, 1.30 * S, 0.86 * S, 14, [camo_c() for _ in range(14)], 0.0, 1.0, 1.1))
    mant = s_box(-0.52 * S, 0.52 * S, 1.80, 2.34, 1.35 * S, 1.80 * S, base)
    tur.append(mant)
    tur.append(s_cyl_z(0.0, 2.08, 1.8 * S, 4.2 * S, 0.17 * S, 0.15 * S, 10, barrel_c))
    tur.append(s_cyl_z(0.0, 2.08, 2.9 * S, 3.2 * S, 0.215 * S, 0.215 * S, 10, (70, 74, 64)))
    tur.append(s_cyl_z(0.0, 2.08, 4.2 * S, 5.5 * S, 0.15 * S, 0.14 * S, 10, barrel_c))
    tur.append(s_cyl_z(0.0, 2.08, 5.25 * S, 5.55 * S, 0.22 * S, 0.22 * S, 10, (44, 48, 42)))
    tur.append(s_frustum(0.55, -0.25, 2.58, 2.86, 0.38, 0.34, 10, [(84, 90, 58)]))
    tur.append(s_cyl_z(0.55, 2.97, -0.15, 0.6, 0.045, 0.045, 6, (30, 30, 30)))
    tur.append(s_frustum(-0.5, -0.1, 2.58, 2.66, 0.34, 0.34, 10, [(60, 64, 50)]))
    tur.append(s_box(-0.95 * S, 0.95 * S, 1.78, 2.34, -2.1 * S, -1.5 * S, base))
    tur.append(s_box(-0.05, 0.05, 2.56, 4.5, -1.6 * S, -1.5 * S, (30, 30, 30)))
    for sd in (-1, 1):
        for k in range(3):
            tur.append(s_cyl_z(1.28 * S * sd, 2.05 + k * 0.1, 0.35, 0.65, 0.07, 0.07, 6, (40, 40, 40)))
    if heavy:
        tur.append(s_box(-0.7, 0.7, 2.58, 2.86, -1.2, -0.3, trim))
        tur.append(s_box(-1.52 * S, -1.34 * S, 1.6, 2.4, -0.6, 0.8, camo_c()))
        tur.append(s_box(1.34 * S, 1.52 * S, 1.6, 2.4, -0.6, 0.8, camo_c()))
    return hull, tur


def render_solids(solids, rel_deg, size, px, pitch=TK_PITCH, shadow=False):
    W_, H_ = size
    SS = 2
    surf = pygame.Surface((W_ * SS, H_ * SS), pygame.SRCALPHA)
    a, p = math.radians(rel_deg), math.radians(pitch)
    ca, sa, cp, sp_ = math.cos(a), math.sin(a), math.cos(p), math.sin(p)
    cx0, gy = W_ / 2.0, H_ * 0.80
    L = _unit((0.50, 0.72, -0.46))
    if shadow:
        sw, sh_ = 8.4 * px * SS, 8.4 * px * SS * math.sin(p) * 0.9
        sx0 = cx0 * SS - sw / 2
        pygame.draw.ellipse(surf, (0, 0, 0, 105), (sx0, gy * SS - sh_ / 2, sw, sh_))

    def tr(v):
        x1, z1 = v[0] * ca + v[2] * sa, -v[0] * sa + v[2] * ca
        return x1, v[1] * cp + z1 * sp_, z1 * cp - v[1] * sp_

    def trn(n):
        return tr(n)

    order = []
    for s in solids:
        order.append((tr(s.c)[2], s))
    order.sort(key=lambda q: -q[0])
    for _, s in order:
        items = [(f[0], f[1], f[2], False) for f in s.faces] + [(d[0], d[1], d[2], True) for d in s.details]
        for verts, col, n, is_detail in items:
            nv = trn(n)
            if nv[2] >= -0.02:
                continue
            sh = 0.36 + 0.64 * max(0.0, nv[0] * L[0] + nv[1] * L[1] + nv[2] * L[2])
            c = (min(255, int(col[0] * sh)), min(255, int(col[1] * sh)), min(255, int(col[2] * sh)))
            pts = []
            for v in verts:
                x, y, z = tr(v)
                pts.append(((cx0 + x * px) * SS, (gy - y * px) * SS))
            pygame.draw.polygon(surf, c, pts)
            if not is_detail:
                pygame.draw.lines(surf, (int(c[0] * .55), int(c[1] * .55), int(c[2] * .55)), True, pts, 1)
    out = pygame.transform.smoothscale(surf, (W_, H_))
    return out, cx0, gy


def make_tank_sprites():
    """Pre-renderiza cada tanque (casco y torreta por separado) desde TK_ANG ángulos."""
    size = (380, 250)
    out = {}
    for kind, heavy in (('tank', False), ('super', True)):
        hull, tur = build_tank_model(heavy, 11 if not heavy else 23)
        px = TK_PXU * (0.92 if heavy else 1.0)
        parts = {'px': px}
        for name, solids in (('hull', hull), ('tur', tur)):
            lst = []
            for i in range(TK_ANG):
                img, ax, ay = render_solids(solids, i * 360.0 / TK_ANG, size, px, shadow=(name == 'hull'))
                r = img.get_bounding_rect()
                if r.w < 2 or r.h < 2:
                    r = pygame.Rect(0, 0, 2, 2)
                lst.append((img.subsurface(r).copy().convert_alpha(), ax - r.x, ay - r.y))
            parts[name] = lst
        out[kind] = parts
    return out
