"""Autos de la ciudad del tanque: modelo 3D de baja cantidad de polígonos pre-renderizado desde CAR_ANG ángulos
(nuevo, intacto, quemado y aplastado), con el mismo método que los tanques."""
import math
import random
import pygame
from .tk_art import TK_PXU, Solid, disc_x, quad_x, quad_y, render_solids, s_box, s_extrude

CAR_ANG = 64        # vistas pre-renderizadas de autos y bicicletas (más que los tanques, para que giren más suave)
CAR_COLORS = [(176, 36, 34), (34, 82, 168), (222, 188, 60), (200, 204, 210), (36, 124, 84), (212, 112, 36), (28, 30, 36), (120, 60, 140)]
GLASS, GLASS_BROKEN = (52, 76, 98), (16, 18, 20)
TIRE, RIM, CHROME, UNDER = (20, 20, 22), (168, 170, 176), (186, 190, 198), (18, 18, 20)


def quad_z(z, x0, x1, y0, y1, col, nz):
    return ([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], col, (0.0, 0.0, nz))


def s_cyl_x(cx, cy, cz, x0, x1, r, n, col):
    """Rueda: prisma de n lados con eje en x."""
    a = [(x0, cy + math.sin(2 * math.pi * i / n) * r, cz + math.cos(2 * math.pi * i / n) * r) for i in range(n)]
    b = [(x1, y, z) for _, y, z in a]
    f = [(a, col), (b, col)]
    for i in range(n):
        j = (i + 1) % n
        f.append(([a[i], a[j], b[j], b[i]], col))
    return Solid(f)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def build_car_model(color, state, seed=0):
    rnd = random.Random(seed)
    solids = []
    if state == 'crushed':
        body = shade(color, 0.7)
        dark = shade(color, 0.4)
        prof = [(-2.35, 0.06), (-2.35, 0.40), (2.35, 0.32), (2.35, 0.06)]
        solids.append(s_extrude(prof, -1.08, 1.08, body, [dark, body, shade(color, 0.55), dark]))
        solids.append(s_box(-0.82, 0.86, 0.40, 0.58, -1.25, 0.95, (70, 78, 86)))
        for _ in range(4):
            x, z = rnd.uniform(-0.8, 0.8), rnd.uniform(-1.8, 1.8)
            solids.append(s_box(x - 0.3, x + 0.3, 0.38, 0.38 + rnd.uniform(0.1, 0.3), z - 0.35, z + 0.35, shade(color, rnd.uniform(0.35, 0.8))))
        for sx in (-1, 1):
            for z in (-1.5, 1.5):
                x0, x1 = (1.0, 1.32) if sx > 0 else (-1.32, -1.0)
                solids.append(s_box(x0, x1, 0.0, 0.26, z - 0.42, z + 0.42, TIRE))
        solids.append(s_box(-1.02, 1.02, 0.16, 0.34, 2.3, 2.5, (80, 82, 86)))
        return solids
    burnt = state == 'burnt'
    body = (40, 34, 30) if burnt else color
    trim = (26, 24, 24) if burnt else CHROME
    glass = GLASS_BROKEN if burnt else GLASS
    patches = [(46, 38, 32), (74, 44, 26), (30, 28, 28), (88, 52, 28)] if burnt else None

    def pc(c):
        return rnd.choice(patches) if burnt else c
    # carrocería baja (capó con pendiente, baúl corto)
    prof = [(-2.2, 0.30), (-2.2, 0.82), (-2.08, 0.95), (-1.15, 1.0), (1.35, 1.0), (1.92, 0.93), (2.2, 0.80), (2.2, 0.30)]
    solids.append(s_extrude(prof, -0.92, 0.92, pc(body), [pc(body)] * 7 + [UNDER]))
    # habitáculo: parabrisas y luneta inclinados, techo del color de la carrocería
    cab = [(-1.28, 1.0), (-0.82, 1.52), (0.62, 1.52), (1.4, 1.0)]
    solids.append(s_extrude(cab, -0.80, 0.80, glass, [glass, pc(body), glass, pc(body)]))
    for sd in (-1, 1):
        xo = 0.805 * sd
        nx = float(sd)
        solids[1].details.append(quad_x(xo, 1.0, 1.52, -0.02, 0.12, pc(body), nx))                    # pilar central
        solids[1].details.append(quad_x(xo, 1.02, 1.08, -1.2, 1.38, pc(body), nx))                    # umbral
        solids[0].details.append(quad_x(0.925 * sd, 0.36, 0.98, -0.92, -0.88, shade(body, 0.55), nx))  # líneas de puertas
        solids[0].details.append(quad_x(0.925 * sd, 0.36, 0.98, 0.14, 0.18, shade(body, 0.55), nx))
        solids[0].details.append(quad_x(0.925 * sd, 0.36, 0.98, 1.0, 1.04, shade(body, 0.55), nx))
        solids[0].details.append(quad_x(0.925 * sd, 0.80, 0.86, -0.78, -0.55, trim, nx))              # manija
        solids[0].details.append(quad_x(0.925 * sd, 0.80, 0.86, 0.3, 0.52, trim, nx))
        solids[0].details.append(quad_x(0.925 * sd, 0.30, 0.38, -1.7, 1.7, shade(body, 0.4), nx))     # zócalo
    solids[0].details.append(quad_y(1.002, -0.5, 0.5, 1.5, 1.85, shade(body, 0.8)))                     # relieve del capó
    for sd in (-1, 1):
        solids[0].details.append(quad_x(0.927 * sd, 0.94, 0.99, -1.0, 1.95, trim, float(sd)))                                        # cintura cromada
        solids[0].details.append(quad_x(0.927 * sd, 0.30, 0.33, -2.1, 2.1, shade(trim, 0.7), float(sd)))                             # moldura baja
    solids[0].details.append(quad_y(1.002, -0.62, 0.62, -2.0, -1.45, shade(body, 0.85)))                                               # tapa del baúl
    # paragolpes, luces y parrilla
    solids.append(s_box(-0.97, 0.97, 0.28, 0.5, 2.16, 2.34, trim))
    solids.append(s_box(-0.97, 0.97, 0.28, 0.5, -2.34, -2.16, trim))
    for sd in (-1, 1):
        x0, x1 = (0.5, 0.88) if sd > 0 else (-0.88, -0.5)
        solids.append(s_box(x0, x1, 0.6, 0.78, 2.17, 2.24, (70, 62, 56) if burnt else (255, 240, 190)))
        solids.append(s_box(x0, x1, 0.62, 0.8, -2.24, -2.17, (60, 30, 24) if burnt else (212, 30, 28)))
        mx0, mx1 = (0.92, 1.1) if sd > 0 else (-1.1, -0.92)
        solids.append(s_box(mx0, mx1, 1.06, 1.2, 0.85, 1.05, pc(body)))                               # espejo
        bx0, bx1 = (0.48, 0.9) if sd > 0 else (-0.9, -0.48)
        solids.append(s_box(bx0, bx1, 0.56, 0.84, 2.14, 2.2, trim))                                     # marco de los faros
        solids.append(s_box(bx0, bx1, 0.56, 0.84, -2.2, -2.14, trim))
        ex = 0.5 * sd
        solids.append(s_box(ex - 0.07, ex + 0.07, 0.2, 0.3, -2.42, -2.2, UNDER))                        # escape
        ax0, ax1 = (0.5, 0.58) if sd > 0 else (-0.58, -0.5)
        solids.append(s_box(ax0, ax1, 0.62, 0.7, 2.18, 2.26, (255, 170, 40) if not burnt else (60, 40, 20)))   # intermitente
    solids.append(s_box(0.62, 0.68, 0.95, 1.85, -1.9, -1.86, (20, 20, 22)))                              # antena
    solids[0].details.append(quad_z(2.202, -0.4, 0.4, 0.5, 0.72, (14, 14, 16), 1.0))                 # parrilla
    for gx in (-0.3, -0.15, 0.0, 0.15, 0.3):
        solids[0].details.append(quad_z(2.203, gx - 0.015, gx + 0.015, 0.5, 0.72, (70, 70, 74), 1.0))   # barras de la parrilla
    solids[0].details.append(quad_z(-2.202, -0.3, 0.3, 0.48, 0.64, (230, 230, 220) if not burnt else (50, 50, 46), -1.0))   # patente
    # ruedas
    for sd in (-1, 1):
        for z in (-1.42, 1.42):
            x0, x1 = (0.70, 0.94) if sd > 0 else (-0.94, -0.70)
            w = s_cyl_x(0.0, 0.38, z, x0, x1, 0.38, 20, TIRE)
            xo = (x1 + 0.012) if sd > 0 else (x0 - 0.012)
            w.details.append(disc_x(xo, 0.38, z, 0.29, 20, shade(TIRE, 1.5), float(sd)))                           # flanco del neumático
            w.details.append(disc_x(xo + 0.004 * sd, 0.38, z, 0.22, 16, (60, 56, 52) if burnt else RIM, float(sd)))
            w.details.append(disc_x(xo + 0.008 * sd, 0.38, z, 0.15, 12, shade(TIRE, 1.2), float(sd)))
            for k in range(5):
                a = 2 * math.pi * k / 5
                w.details.append(disc_x(xo + 0.010 * sd, 0.38 + math.sin(a) * 0.11, z + math.cos(a) * 0.11, 0.028, 6, CHROME, float(sd)))   # tuercas
            w.details.append(disc_x(xo + 0.012 * sd, 0.38, z, 0.06, 8, CHROME if not burnt else (60, 56, 52), float(sd)))
            solids.append(w)
    return solids


def make_car_sprites():
    """{(variante, estado): lista de CAR_ANG cuadros (img, ancla x, ancla y)}; variante = índice de color."""
    size = (230, 150)
    out = {}
    jobs = [(i, 'ok') for i in range(len(CAR_COLORS))] + [(0, 'burnt'), (0, 'crushed'), (3, 'crushed')]
    for var, state in jobs:
        solids = build_car_model(CAR_COLORS[var], state, 7 + var)
        frames = []
        for i in range(CAR_ANG):
            img, ax, ay = render_solids(solids, i * 360.0 / CAR_ANG, size, TK_PXU, shadow=True, shadow_w=4.8)
            r = img.get_bounding_rect()
            if r.w < 2 or r.h < 2:
                r = pygame.Rect(0, 0, 2, 2)
            frames.append((img.subsurface(r).copy().convert_alpha(), ax - r.x, ay - r.y))
        out[(var, state)] = frames
    return out


# ------------------------------------------------------------------ bicicletas
BIKE_COLORS = [(196, 48, 44), (46, 96, 176), (226, 190, 60), (52, 150, 100), (232, 128, 44), (120, 70, 150)]
BIKE_RIM, BIKE_SEAT, BIKE_STEEL = (170, 172, 178), (24, 24, 28), (150, 154, 160)


def s_cyl_y(cx, cz, y0, y1, r, n, col, sx=1.0, sz=1.0):
    """Disco horizontal (eje vertical): ruedas aplastadas."""
    a = [(cx + math.cos(2 * math.pi * i / n) * r * sx, y0, cz + math.sin(2 * math.pi * i / n) * r * sz) for i in range(n)]
    b = [(x, y1, z) for x, _, z in a]
    f = [(a, col), (b, col)]
    for i in range(n):
        j = (i + 1) % n
        f.append(([a[i], a[j], b[j], b[i]], col))
    return Solid(f)


def _tube(a, b, t, x0, x1, col):
    """Tubo del cuadro: banda de ancho t entre a y b (puntos z, y) extruida a lo ancho."""
    (za, ya), (zb, yb) = a, b
    dz, dy = zb - za, yb - ya
    ln = math.hypot(dz, dy) or 1.0
    nz, ny = -dy / ln * t / 2, dz / ln * t / 2
    return s_extrude([(za + nz, ya + ny), (zb + nz, yb + ny), (zb - nz, yb - ny), (za - nz, ya - ny)], x0, x1, col)


def build_bike_model(color, state, seed=0, var=0):
    rnd = random.Random(seed)
    solids = []
    dark = shade(color, 0.62)
    if state == 'crushed':
        solids.append(s_cyl_y(-0.12, -0.62, 0.0, 0.05, 0.36, 14, TIRE, 1.0, 0.8))
        solids.append(s_cyl_y(0.22, 0.58, 0.0, 0.05, 0.33, 14, TIRE, 0.7, 1.0))
        solids[0].details.append(([(-0.12 + math.cos(2 * math.pi * i / 14) * 0.27, 0.052, -0.62 + math.sin(2 * math.pi * i / 14) * 0.22) for i in range(14)], BIKE_RIM, (0.0, 1.0, 0.0)))
        for _ in range(6):
            x, z = rnd.uniform(-0.45, 0.45), rnd.uniform(-0.9, 0.9)
            ln = rnd.uniform(0.3, 0.7)
            if rnd.random() < 0.5:
                solids.append(s_box(x - ln / 2, x + ln / 2, 0.05, 0.1, z - 0.025, z + 0.025, color if rnd.random() < 0.7 else dark))
            else:
                solids.append(s_box(x - 0.025, x + 0.025, 0.05, 0.1, z - ln / 2, z + ln / 2, color if rnd.random() < 0.7 else dark))
        solids.append(s_box(-0.3, 0.3, 0.1, 0.14, 0.2, 0.26, BIKE_SEAT))
        solids.append(s_box(0.0, 0.14, 0.05, 0.11, -0.3, -0.1, BIKE_SEAT))
        return solids
    # ruedas con llanta clara, cubierta oscura y rayos
    for z in (-0.62, 0.62):
        w = s_cyl_x(0.0, 0.36, z, -0.035, 0.035, 0.36, 14, TIRE)
        for sd in (-1, 1):
            xo = 0.037 * sd
            w.details.append(disc_x(xo, 0.36, z, 0.30, 14, BIKE_RIM, float(sd)))
            w.details.append(disc_x(xo + 0.002 * sd, 0.36, z, 0.27, 14, (46, 50, 58), float(sd)))
            w.details.append(quad_x(xo + 0.004 * sd, 0.09, 0.63, z - 0.007, z + 0.007, (176, 178, 184), float(sd)))
            w.details.append(quad_x(xo + 0.004 * sd, 0.353, 0.367, z - 0.27, z + 0.27, (176, 178, 184), float(sd)))
            w.details.append(disc_x(xo + 0.006 * sd, 0.36, z, 0.05, 8, BIKE_STEEL, float(sd)))
        solids.append(w)
    bb, st, ht, hb = (-0.05, 0.28), (-0.24, 0.88), (0.40, 0.86), (0.46, 0.62)
    rh, fh = (-0.62, 0.36), (0.62, 0.36)
    for sd in (-1, 1):                                            # vainas y horquilla dobles
        x0, x1 = (0.05, 0.10) if sd > 0 else (-0.10, -0.05)
        solids.append(_tube(rh, bb, 0.05, x0, x1, dark))
        solids.append(_tube(rh, (-0.22, 0.82), 0.045, x0, x1, dark))
        solids.append(_tube(hb, fh, 0.05, x0 + 0.02 * sd, x1 + 0.02 * sd, BIKE_STEEL))
    solids.append(_tube(bb, st, 0.06, -0.035, 0.035, color))
    solids.append(_tube(st, ht, 0.06, -0.035, 0.035, color))
    solids.append(_tube(bb, hb, 0.075, -0.04, 0.04, shade(color, 0.85)))
    solids.append(s_box(-0.04, 0.04, 0.60, 0.9, 0.38, 0.47, shade(color, 0.8)))              # tubo de dirección
    solids.append(s_box(-0.022, 0.022, 0.88, 1.0, 0.34, 0.40, BIKE_STEEL))                   # potencia
    solids.append(s_box(-0.32, 0.32, 0.99, 1.03, 0.35, 0.41, BIKE_STEEL))                    # manubrio
    for sd in (-1, 1):
        x0, x1 = (0.2, 0.33) if sd > 0 else (-0.33, -0.2)
        solids.append(s_box(x0, x1, 0.975, 1.045, 0.33, 0.43, BIKE_SEAT))                    # puños
        solids.append(s_box(0.28 * sd - 0.012, 0.28 * sd + 0.012, 0.93, 1.0, 0.43, 0.5, BIKE_STEEL))   # manetas
    solids.append(s_box(-0.02, 0.02, 0.88, 0.99, -0.27, -0.22, BIKE_STEEL))                   # tija
    solids.append(s_extrude([(-0.46, 0.99), (-0.38, 1.03), (-0.14, 1.03), (-0.06, 1.0), (-0.14, 0.97), (-0.42, 0.97)], -0.07, 0.07, BIKE_SEAT))
    solids.append(s_cyl_x(0.0, 0.28, -0.05, -0.12, 0.12, 0.045, 10, BIKE_STEEL))              # pedalier y pedales
    solids.append(s_box(0.09, 0.19, 0.17, 0.2, -0.12, 0.0, BIKE_SEAT))
    solids.append(s_box(-0.19, -0.09, 0.36, 0.39, -0.1, 0.02, BIKE_SEAT))
    if var % 3 == 0:                                                                          # canasto delantero
        solids.append(s_box(-0.2, 0.2, 0.98, 1.22, 0.5, 0.8, (158, 134, 92)))
        solids[-1].details.append(quad_x(0.201, 1.0, 1.2, 0.52, 0.78, (118, 98, 66), 1.0))
        solids[-1].details.append(quad_x(-0.201, 1.0, 1.2, 0.52, 0.78, (118, 98, 66), -1.0))
    elif var % 3 == 1:                                                                        # portaequipaje con cajón
        solids.append(s_box(-0.15, 0.15, 0.9, 0.93, -0.8, -0.34, BIKE_STEEL))
        solids.append(s_box(-0.14, 0.14, 0.93, 1.12, -0.72, -0.44, shade(color, 0.7)))
    return solids


def make_bike_sprites():
    """{(variante, estado): CAR_ANG cuadros (img, ancla x, ancla y)} de las bicicletas (mismo método que los autos)."""
    size = (150, 120)
    out = {}
    jobs = [(i, 'ok') for i in range(len(BIKE_COLORS))] + [(0, 'crushed'), (1, 'crushed')]
    for var, state in jobs:
        solids = build_bike_model(BIKE_COLORS[var], state, 11 + var, var)
        frames = []
        for i in range(CAR_ANG):
            img, ax, ay = render_solids(solids, i * 360.0 / CAR_ANG, size, TK_PXU, shadow=True, shadow_w=2.6)
            r = img.get_bounding_rect()
            if r.w < 2 or r.h < 2:
                r = pygame.Rect(0, 0, 2, 2)
            frames.append((img.subsurface(r).copy().convert_alpha(), ax - r.x, ay - r.y))
        out[(var, state)] = frames
    return out
