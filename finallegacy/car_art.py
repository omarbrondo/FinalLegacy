"""Autos de la ciudad del tanque: modelo 3D de baja cantidad de polígonos pre-renderizado desde TK_ANG ángulos
(nuevo, intacto, quemado y aplastado), con el mismo método que los tanques."""
import math
import random
import pygame
from .tk_art import TK_ANG, TK_PXU, Solid, disc_x, quad_x, quad_y, render_solids, s_box, s_extrude

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
    prof = [(-2.2, 0.30), (-2.2, 0.94), (-1.15, 1.0), (1.35, 1.0), (2.2, 0.80), (2.2, 0.30)]
    solids.append(s_extrude(prof, -0.92, 0.92, pc(body), [pc(body), pc(body), pc(body), pc(body), pc(body), UNDER]))
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
    solids[0].details.append(quad_y(1.002, -0.5, 0.5, 1.5, 2.0, shade(body, 0.8)))                      # relieve del capó
    # paragolpes, luces y parrilla
    solids.append(s_box(-0.97, 0.97, 0.28, 0.5, 2.16, 2.34, trim))
    solids.append(s_box(-0.97, 0.97, 0.28, 0.5, -2.34, -2.16, trim))
    for sd in (-1, 1):
        x0, x1 = (0.5, 0.88) if sd > 0 else (-0.88, -0.5)
        solids.append(s_box(x0, x1, 0.6, 0.78, 2.17, 2.24, (70, 62, 56) if burnt else (255, 240, 190)))
        solids.append(s_box(x0, x1, 0.62, 0.8, -2.24, -2.17, (60, 30, 24) if burnt else (212, 30, 28)))
        mx0, mx1 = (0.92, 1.1) if sd > 0 else (-1.1, -0.92)
        solids.append(s_box(mx0, mx1, 1.06, 1.2, 0.85, 1.05, pc(body)))                               # espejo
    solids[0].details.append(quad_z(2.202, -0.4, 0.4, 0.5, 0.72, (14, 14, 16), 1.0))                 # parrilla
    solids[0].details.append(quad_z(-2.202, -0.3, 0.3, 0.48, 0.64, (230, 230, 220) if not burnt else (50, 50, 46), -1.0))   # patente
    # ruedas
    for sd in (-1, 1):
        for z in (-1.42, 1.42):
            x0, x1 = (0.70, 0.94) if sd > 0 else (-0.94, -0.70)
            w = s_cyl_x(0.0, 0.38, z, x0, x1, 0.38, 12, TIRE)
            xo = (x1 + 0.012) if sd > 0 else (x0 - 0.012)
            w.details.append(disc_x(xo, 0.38, z, 0.22, 10, (60, 56, 52) if burnt else RIM, float(sd)))
            w.details.append(disc_x(xo + 0.01 * sd, 0.38, z, 0.07, 6, TIRE, float(sd)))
            solids.append(w)
    return solids


def make_car_sprites():
    """{(variante, estado): lista de TK_ANG cuadros (img, ancla x, ancla y)}; variante = índice de color."""
    size = (230, 150)
    out = {}
    jobs = [(i, 'ok') for i in range(len(CAR_COLORS))] + [(0, 'burnt'), (0, 'crushed'), (3, 'crushed')]
    for var, state in jobs:
        solids = build_car_model(CAR_COLORS[var], state, 7 + var)
        frames = []
        for i in range(TK_ANG):
            img, ax, ay = render_solids(solids, i * 360.0 / TK_ANG, size, TK_PXU, shadow=True, shadow_w=4.8)
            r = img.get_bounding_rect()
            if r.w < 2 or r.h < 2:
                r = pygame.Rect(0, 0, 2, 2)
            frames.append((img.subsurface(r).copy().convert_alpha(), ax - r.x, ay - r.y))
        out[(var, state)] = frames
    return out
