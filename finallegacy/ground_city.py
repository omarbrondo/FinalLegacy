"""Distrito urbano de la invasión anfibia: manzanas, calles, edificios con colisión y navegación por flujo.
El mapa es una isla grande con una ciudad a escala de los soldados; el ayuntamiento del centro es el objetivo."""
import math
import random
from collections import deque
import pygame
from .common import H, W, bearing, clamp, coast_r, vec

GC_R = 680                  # radio de la isla en la invasión de una ciudad
PITCH, BLK, SWALK = 200, 140, 7
SOL_SCALE = 0.78            # los soldados se dibujan más chicos para que la ciudad no parezca de juguete
ATT_R = 150                 # a esta distancia del ayuntamiento los invasores atacan la ciudad
NAV = 16                    # tamaño de celda del campo de navegación
RCS = 120                   # tamaño de celda de la grilla de colisiones
CAR_L, CAR_W = 54, 26         # los autos son más grandes que un soldado
HALL = (-44, -34, 88, 68)   # ayuntamiento (u, v, ancho, alto), relativo al centro

PALS = [
    dict(wall=(104, 112, 128), roof=(168, 174, 182), roof2=(158, 164, 172), hi=(218, 222, 228), lo=(110, 116, 126)),
    dict(wall=(134, 78, 64), roof=(186, 124, 100), roof2=(176, 114, 92), hi=(222, 168, 140), lo=(120, 74, 60)),
    dict(wall=(164, 144, 108), roof=(214, 198, 160), roof2=(204, 188, 150), hi=(238, 226, 196), lo=(150, 134, 100)),
    dict(wall=(56, 92, 138), roof=(112, 152, 192), roof2=(100, 140, 182), hi=(170, 202, 230), lo=(60, 92, 130)),
    dict(wall=(78, 84, 96), roof=(128, 134, 146), roof2=(118, 124, 136), hi=(176, 182, 192), lo=(84, 88, 98)),
]
# carácter de cada ciudad: manzanas (interior < 330 px del centro / exterior), paletas de edificios, autos y barricadas
THEMES = {
    'port': dict(inner=(('tower', 'split', 'quad', 'park'), (30, 25, 20, 5)), outer=(('quad', 'park', 'parking', 'docks', 'split'), (8, 8, 14, 55, 15)),
                 dock_min=300, pals=(0, 4, 1, 4), cars=None, bars=9),
    'resid': dict(inner=(('tower', 'split', 'quad', 'park'), (4, 26, 45, 25)), outer=(('quad', 'park', 'parking', 'split'), (40, 35, 10, 15)),
                  dock_min=9999, pals=(1, 2, 1, 2, 0), cars=None, bars=7),
    'resort': dict(inner=(('tower', 'split', 'quad', 'park'), (24, 34, 26, 16)), outer=(('quad', 'park', 'parking', 'split'), (30, 32, 10, 28)),
                   dock_min=9999, pals=(3, 2, 3, 0), cars=[(240, 240, 244), (70, 150, 200), (240, 200, 70), (236, 120, 120), (80, 190, 170)], bars=7),
    'fort': dict(inner=(('tower', 'split', 'quad', 'park'), (22, 42, 36, 0)), outer=(('quad', 'parking', 'docks', 'split'), (20, 22, 20, 38)),
                 dock_min=380, pals=(4, 0, 4), cars=[(86, 98, 66), (110, 116, 100), (70, 76, 84), (96, 88, 62)], bars=18),
}
THEME_BY_NAME = {'PUERTO BRONDO': 'port', 'NUEVA ESPERANZA': 'resid', 'BAHIA AZUL': 'resort', 'FORT LEGACY': 'fort'}
CAR_COLS = [(190, 60, 54), (60, 100, 168), (214, 200, 70), (220, 220, 224), (70, 76, 84), (60, 140, 96), (230, 130, 50)]
BOX_COLS = [(184, 62, 52), (58, 100, 162), (212, 152, 52), (70, 140, 92), (150, 152, 158)]


class GroundCityMixin:
    # ------------------------------------------------------------------ trazado
    def gc_layout(self, R, seed, theme='port'):
        th = THEMES[theme]
        rnd = random.Random(seed * 7 + 3)
        blocks = {}
        for i in range(-4, 5):
            for j in range(-4, 5):
                u, v = i * PITCH, j * PITCH
                fu, fv = u + 100 * (1 if u >= 0 else -1), v + 100 * (1 if v >= 0 else -1)      # esquina más lejana de la manzana
                if (abs(i) <= 1 and abs(j) <= 1) or math.hypot(fu, fv) < coast_r(R, seed, math.atan2(fv, fu), 0.86):
                    blocks[(i, j)] = 'hall'
        for (i, j) in blocks:
            d = math.hypot(i * PITCH, j * PITCH)
            if (i, j) == (0, 0):
                continue
            kinds, wts = th['inner'] if d < 330 else th['outer']
            kind = rnd.choices(kinds, wts)[0]
            blocks[(i, j)] = 'split' if kind == 'docks' and d < th['dock_min'] else kind
        return blocks

    # ------------------------------------------------------------------ pintura
    def gc_paint(self, land, ext, R, seed, theme='port'):
        """Pinta el distrito sobre la superficie de la isla. Devuelve (rectángulos sólidos en coordenadas de mundo, info)."""
        rnd = random.Random(seed * 13 + 5)
        th = THEMES[theme]
        blocks = self.gc_layout(R, seed, theme)
        pals = [PALS[k] for k in th['pals']]
        self._gc_cols = th['cars'] or CAR_COLS
        X0, Y0 = ext, ext
        solids = []                     # (x, y, w, d) relativos al centro
        builds = []
        props = []

        # calles
        ASPH = (64, 66, 72)
        for (i, j) in blocks:
            pygame.draw.rect(land, ASPH, (X0 + i * PITCH - 100, Y0 + j * PITCH - 100, 200, 200))
        for (i, j) in blocks:
            u, v = X0 + i * PITCH, Y0 + j * PITCH
            for _ in range(80):
                c = rnd.randint(52, 84)
                pygame.draw.rect(land, (c, c + 2, c + 8), (u + rnd.randint(-100, 98), v + rnd.randint(-100, 98), rnd.randint(1, 3), rnd.randint(1, 2)))
            for k in range(2):
                a = rnd.uniform(0, 6.28)
                px, py = u + rnd.randint(-80, 80), v + rnd.randint(-80, 80)
                pygame.draw.line(land, (46, 48, 54), (px, py), (px + math.cos(a) * rnd.randint(10, 24), py + math.sin(a) * rnd.randint(10, 24)), 1)
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (i + di, j + dj) not in blocks:
                    if di:
                        pygame.draw.rect(land, (170, 168, 160), (u + (95 if di > 0 else -100), v - 100, 5, 200))
                    else:
                        pygame.draw.rect(land, (170, 168, 160), (u - 100, v + (95 if dj > 0 else -100), 200, 5))
        YEL, WHT = (224, 190, 58), (212, 212, 206)
        for (i, j) in blocks:
            u, v = X0 + i * PITCH, Y0 + j * PITCH
            if (i + 1, j) in blocks:                                  # calle vertical entre (i,j) y (i+1,j)
                x = u + 100
                for y in range(v - 70, v + 66, 28):
                    pygame.draw.rect(land, YEL, (x - 1, y, 2, 16))
                if (i, j - 1) in blocks and (i + 1, j - 1) in blocks:
                    for k in range(-26, 26, 8):
                        pygame.draw.rect(land, WHT, (x + k, v - 66, 4, 10))
                if (i, j + 1) in blocks and (i + 1, j + 1) in blocks:
                    for k in range(-26, 26, 8):
                        pygame.draw.rect(land, WHT, (x + k, v + 56, 4, 10))
            if (i, j + 1) in blocks:                                  # calle horizontal entre (i,j) y (i,j+1)
                y = v + 100
                for x in range(u - 70, u + 66, 28):
                    pygame.draw.rect(land, YEL, (x, y - 1, 16, 2))
                if (i - 1, j) in blocks and (i - 1, j + 1) in blocks:
                    for k in range(-26, 26, 8):
                        pygame.draw.rect(land, WHT, (u - 66, y + k, 10, 4))
                if (i + 1, j) in blocks and (i + 1, j + 1) in blocks:
                    for k in range(-26, 26, 8):
                        pygame.draw.rect(land, WHT, (u + 56, y + k, 10, 4))
        # autos estacionados y barricadas en los tramos de calle
        segs = []
        for (i, j) in blocks:
            if (i + 1, j) in blocks:
                segs.append((i * PITCH + 100, j * PITCH, 'v'))
            if (i, j + 1) in blocks:
                segs.append((i * PITCH, j * PITCH + 100, 'h'))
        rnd.shuffle(segs)
        far = [s for s in segs if math.hypot(s[0], s[1]) > 190]
        bar = far[:th['bars']]
        spots = []
        for sx, sy, ax in bar:
            side = rnd.choice((-1, 1))
            off = 18 * side
            along = rnd.randint(-30, 30)
            spots.append((sx + off if ax == 'v' else sx + along, sy + along if ax == 'v' else sy + off))
        for sx, sy, ax in segs:
            if (sx, sy, ax) in bar or rnd.random() > 0.6:
                continue
            used = []
            for _ in range(rnd.choice((1, 1, 2))):
                side = rnd.choice((-1, 1))
                along = rnd.randint(-40, 40)
                if any(s_ == side and abs(a_ - along) < 62 for s_, a_ in used):
                    continue
                used.append((side, along))
                cxu, cyv = (sx + 16 * side, sy + along) if ax == 'v' else (sx + along, sy + 16 * side)
                props.append(('car', cxu, cyv, ax == 'h', rnd.randrange(10 ** 6)))

        # manzanas
        for (i, j), kind in blocks.items():
            u, v = i * PITCH, j * PITCH
            pygame.draw.rect(land, (178, 174, 164), (X0 + u - 70, Y0 + v - 70, 140, 140), border_radius=7)
            pygame.draw.rect(land, (136, 132, 124), (X0 + u - 70, Y0 + v - 70, 140, 140), 1, border_radius=7)
            lx, ly = X0 + u - 63, Y0 + v - 63
            if kind == 'hall':
                pygame.draw.rect(land, (206, 200, 188), (lx, ly, 126, 126))
                for a in range(0, 126, 14):
                    for b in range(0, 126, 14):
                        if (a // 14 + b // 14) % 2:
                            pygame.draw.rect(land, (190, 184, 172), (lx + a, ly + b, 14, 14))
                pygame.draw.rect(land, (150, 144, 134), (lx, ly, 126, 126), 2)
                for sx_, sy_ in ((-52, -52), (52, -52), (-52, 52), (52, 52)):
                    props.append(('tree', u + sx_, v + sy_, 13, rnd.randrange(10 ** 6)))
                builds.append((u + HALL[0], v + HALL[1], HALL[2], HALL[3], 24, 'hall', 0))
                pygame.draw.rect(land, (170, 164, 152), (X0 + u - 22, Y0 + v + 34, 44, 7))
                pygame.draw.rect(land, (190, 184, 172), (X0 + u - 18, Y0 + v + 41, 36, 6))
            elif kind in ('tower', 'split', 'quad'):
                pygame.draw.rect(land, (126, 128, 130), (lx, ly, 126, 126))
                if kind == 'tower':
                    builds.append((u - 55, v - 55, 110, 110, rnd.randint(24, 36), rnd.choice(pals), rnd.randrange(10 ** 6)))
                elif kind == 'split':
                    if rnd.random() < 0.5:
                        lots = [(u - 63, v - 59, 58, 118), (u + 5, v - 59, 58, 118)]
                    else:
                        lots = [(u - 59, v - 63, 118, 58), (u - 59, v + 5, 118, 58)]
                    for (bx, by, bw, bd) in lots:
                        builds.append((bx, by, bw, bd, rnd.randint(18, 30), rnd.choice(pals), rnd.randrange(10 ** 6)))
                else:
                    for (bx, by) in ((u - 63, v - 63), (u + 7, v - 63), (u - 63, v + 7), (u + 7, v + 7)):
                        if rnd.random() < 0.18:
                            props.append(('tree', bx + 28, by + 28, 14, rnd.randrange(10 ** 6)))
                        else:
                            builds.append((bx, by, 56, 56, rnd.randint(12, 24), rnd.choice(pals), rnd.randrange(10 ** 6)))
            elif kind == 'park':
                pygame.draw.rect(land, (84, 146, 72), (lx, ly, 126, 126))
                for _ in range(160):
                    g_ = rnd.randint(-14, 14)
                    pygame.draw.circle(land, (84 + g_, 146 + g_, 72 + g_), (lx + rnd.randint(0, 125), ly + rnd.randint(0, 125)), rnd.randint(1, 3))
                pygame.draw.rect(land, (206, 192, 150), (lx + 58, ly, 10, 126))
                pygame.draw.rect(land, (206, 192, 150), (lx, ly + 58, 126, 10))
                pygame.draw.circle(land, (170, 156, 120), (lx + 63, ly + 63), 20)
                pygame.draw.circle(land, (74, 150, 188), (lx + 63, ly + 63), 15)
                pygame.draw.circle(land, (150, 210, 236), (lx + 59, ly + 59), 6)
                pygame.draw.circle(land, (222, 244, 252), (lx + 63, ly + 63), 15, 2)
                for _ in range(7):
                    tx, ty = u + rnd.choice((-1, 1)) * rnd.randint(18, 52), v + rnd.choice((-1, 1)) * rnd.randint(18, 52)
                    props.append(('tree', tx, ty, rnd.randint(11, 16), rnd.randrange(10 ** 6)))
            elif kind == 'parking':
                pygame.draw.rect(land, (74, 76, 82), (lx, ly, 126, 126))
                pygame.draw.rect(land, (210, 210, 204), (lx, ly, 126, 126), 1)
                for k in range(4):
                    xx = lx + 3 + k * 40
                    pygame.draw.line(land, (208, 208, 200), (xx, ly + 2), (xx, ly + 58), 1)
                    pygame.draw.line(land, (208, 208, 200), (xx, ly + 68), (xx, ly + 124), 1)
                for row in (-1, 1):
                    for k in range(3):
                        if rnd.random() < 0.7:
                            props.append(('car', u - 40 + k * 40, v + row * 33, False, rnd.randrange(10 ** 6)))
            else:                                                                  # docks
                pygame.draw.rect(land, (134, 132, 124), (lx, ly, 126, 126))
                pygame.draw.rect(land, (214, 184, 60), (lx + 1, ly + 1, 124, 124), 2)
                for row in (-46, 0, 46):
                    for col in (-31, 31):
                        if rnd.random() < 0.82:
                            props.append(('box', u + col, v + row, rnd.choice(BOX_COLS), rnd.randrange(10 ** 6)))

        # sombras (una sola pasada, alfa uniforme) y edificios
        sh = pygame.Surface(land.get_size(), pygame.SRCALPHA)
        shade = (0, 0, 0, 84)
        for (x, y, w, d, hh, pal, sd) in builds:
            ox, oy = hh * 0.55 + 4, hh * 0.65 + 4
            X, Y = X0 + x, Y0 + y
            pygame.draw.polygon(sh, shade, [(X, Y), (X + w, Y), (X + w + ox, Y + oy), (X + w + ox, Y + d + oy), (X + ox, Y + d + oy), (X, Y + d)])
        for p in props:
            if p[0] == 'tree':
                pygame.draw.circle(sh, shade, (X0 + p[1] + 6, Y0 + p[2] + 8), p[3])
            elif p[0] == 'car':
                horiz = p[3]
                w, d = (CAR_L, CAR_W) if horiz else (CAR_W, CAR_L)
                pygame.draw.rect(sh, shade, (X0 + p[1] - w // 2 + 3, Y0 + p[2] - d // 2 + 4, w, d))
            elif p[0] == 'box':
                pygame.draw.rect(sh, shade, (X0 + p[1] - 28 + 5, Y0 + p[2] - 10 + 6, 56, 20))
        land.blit(sh, (0, 0))
        del sh
        for b in sorted(builds, key=lambda q: q[1]):
            self._gc_building(land, X0, Y0, *b)
            solids.append((b[0], b[1], b[2], b[3]))
        for p in props:
            if p[0] == 'tree':
                self._gc_tree(land, X0 + p[1], Y0 + p[2], p[3], p[4])
            elif p[0] == 'car':
                w, d = (CAR_L, CAR_W) if p[3] else (CAR_W, CAR_L)
                self._gc_car(land, X0 + p[1], Y0 + p[2], p[3], p[4])
                solids.append((p[1] - w // 2, p[2] - d // 2, w, d))
            elif p[0] == 'box':
                self._gc_box(land, X0 + p[1], Y0 + p[2], p[3], p[4])
                solids.append((p[1] - 28, p[2] - 10, 56, 20))
        rects = [(W / 2 + x, H / 2 + y, W / 2 + x + w, H / 2 + y + d) for x, y, w, d in solids]
        return rects, dict(spots=[(W / 2 + a, H / 2 + b) for a, b in spots], hall=(W / 2 + HALL[0], H / 2 + HALL[1], W / 2 + HALL[0] + HALL[2], H / 2 + HALL[1] + HALL[3]),
                           blocks=[(i * PITCH, j * PITCH) for (i, j) in blocks])

    def _gc_tree(self, s, x, y, r, sd):
        rnd = random.Random(sd)
        pygame.draw.circle(s, (34, 84, 46), (x + 1, y + 2), r)
        for _ in range(5):
            a = rnd.uniform(0, 6.28)
            pygame.draw.circle(s, (46, 108, 56), (int(x + math.cos(a) * r * 0.45), int(y + math.sin(a) * r * 0.45)), int(r * 0.6))
        pygame.draw.circle(s, (74, 146, 76), (x - r // 4, y - r // 4), int(r * 0.55))
        pygame.draw.circle(s, (120, 188, 100), (x - r // 3, y - r // 3), max(2, int(r * 0.28)))

    def _gc_car(self, s, x, y, horiz, sd):
        rnd = random.Random(sd)
        burnt = rnd.random() < 0.22
        col = (42, 40, 40) if burnt else rnd.choice(getattr(self, '_gc_cols', CAR_COLS))
        dark = tuple(max(0, c - 50) for c in col)
        w, d = (CAR_L, CAR_W) if horiz else (CAR_W, CAR_L)
        r = pygame.Rect(x - w // 2, y - d // 2, w, d)
        pygame.draw.rect(s, dark, r, border_radius=5)
        pygame.draw.rect(s, col, r.inflate(-2, -2), border_radius=5)
        cab = r.inflate(-12, -4) if horiz else r.inflate(-4, -12)
        pygame.draw.rect(s, (30, 34, 42) if burnt else (122, 170, 200), cab, border_radius=3)
        pygame.draw.rect(s, dark, cab, 1, border_radius=3)
        if horiz:
            pygame.draw.line(s, (255, 236, 150), (r.right - 2, r.top + 4), (r.right - 2, r.top + 7), 2)
            pygame.draw.line(s, (255, 236, 150), (r.right - 2, r.bottom - 7), (r.right - 2, r.bottom - 4), 2)
            pygame.draw.line(s, (200, 40, 40), (r.left + 1, r.top + 3), (r.left + 1, r.top + 5), 2)
            pygame.draw.line(s, (200, 40, 40), (r.left + 1, r.bottom - 5), (r.left + 1, r.bottom - 3), 2)
        else:
            pygame.draw.line(s, (255, 236, 150), (r.left + 3, r.top + 1), (r.left + 5, r.top + 1), 2)
            pygame.draw.line(s, (255, 236, 150), (r.right - 5, r.top + 1), (r.right - 3, r.top + 1), 2)
            pygame.draw.line(s, (200, 40, 40), (r.left + 3, r.bottom - 2), (r.left + 5, r.bottom - 2), 2)
            pygame.draw.line(s, (200, 40, 40), (r.right - 5, r.bottom - 2), (r.right - 3, r.bottom - 2), 2)
        if burnt:
            pygame.draw.circle(s, (24, 22, 22), (x, y), 20, 3)

    def _gc_box(self, s, x, y, col, sd):
        dark = tuple(max(0, c - 60) for c in col)
        r = pygame.Rect(x - 28, y - 10, 56, 20)
        pygame.draw.rect(s, dark, r)
        pygame.draw.rect(s, col, r.inflate(-2, -2))
        for k in range(r.left + 6, r.right - 4, 6):
            pygame.draw.line(s, dark, (k, r.top + 2), (k, r.bottom - 3), 1)
        pygame.draw.line(s, tuple(min(255, c + 40) for c in col), (r.left + 1, r.top + 1), (r.right - 2, r.top + 1), 2)

    def _gc_building(self, s, X0, Y0, x, y, w, d, hh, pal, sd):
        rnd = random.Random(sd)
        X, Y = X0 + x, Y0 + y
        rh = d - hh
        if pal == 'hall':
            wall, roof, hi, lo = (228, 226, 216), (110, 150, 134), (170, 206, 188), (72, 108, 94)
        else:
            wall, roof, hi, lo = pal['wall'], pal['roof'], pal['hi'], pal['lo']
        pygame.draw.rect(s, wall, (X, Y + rh, w, hh))
        pygame.draw.rect(s, tuple(max(0, c - 34) for c in wall), (X, Y + d - 4, w, 4))
        if pal == 'hall':
            for cx in range(X + 6, X + w - 4, 12):
                pygame.draw.rect(s, (252, 250, 242), (cx, Y + rh + 2, 5, hh - 5))
                pygame.draw.rect(s, (170, 166, 154), (cx + 5, Y + rh + 2, 2, hh - 5))
            pygame.draw.rect(s, (60, 48, 40), (X + w // 2 - 8, Y + rh + 6, 16, hh - 6), border_top_left_radius=8, border_top_right_radius=8)
            pygame.draw.rect(s, (214, 210, 198), (X, Y + rh, w, 3))
        else:
            for wy in range(Y + rh + 4, Y + d - 5, 8):
                for wx in range(X + 5, X + w - 6, 9):
                    pygame.draw.rect(s, (255, 226, 130) if rnd.random() < 0.5 else (44, 54, 80), (wx, wy, 5, 4))
        pygame.draw.rect(s, roof, (X, Y, w, rh))
        pygame.draw.rect(s, pal['roof2'] if pal != 'hall' else (98, 138, 122), (X + 4, Y + 4, w - 8, rh - 8))
        pygame.draw.line(s, hi, (X, Y), (X + w - 1, Y), 2)
        pygame.draw.line(s, hi, (X, Y), (X, Y + rh - 1), 2)
        pygame.draw.line(s, lo, (X, Y + rh - 1), (X + w - 1, Y + rh - 1), 2)
        pygame.draw.line(s, lo, (X + w - 1, Y), (X + w - 1, Y + rh - 1), 2)
        if pal == 'hall':
            cx, cy = X + w // 2, Y + rh // 2
            pygame.draw.circle(s, (60, 96, 82), (cx + 3, cy + 4), 21)
            pygame.draw.circle(s, (126, 170, 150), (cx, cy), 20)
            pygame.draw.circle(s, (170, 208, 190), (cx - 4, cy - 4), 12)
            pygame.draw.circle(s, (224, 244, 232), (cx - 7, cy - 7), 4)
            pygame.draw.circle(s, (70, 108, 92), (cx, cy), 20, 2)
            return
        spots = []
        for _ in range(rnd.randint(2, 4)):
            for _t in range(6):
                px, py = rnd.randint(X + 14, X + w - 14), rnd.randint(Y + 12, Y + rh - 12)
                if all(abs(px - a) > 26 or abs(py - b) > 22 for a, b in spots):
                    spots.append((px, py))
                    break
        if hh >= 26 and w >= 100 and rh >= 70 and rnd.random() < 0.5:
            cx, cy = X + w // 2, Y + rh // 2
            rr = min(w, rh) // 2 - 12
            pygame.draw.circle(s, (220, 196, 70), (cx, cy), rr, 2)
            pygame.draw.line(s, (240, 240, 232), (cx - rr // 3, cy - rr // 2), (cx - rr // 3, cy + rr // 2), 3)
            pygame.draw.line(s, (240, 240, 232), (cx + rr // 3, cy - rr // 2), (cx + rr // 3, cy + rr // 2), 3)
            pygame.draw.line(s, (240, 240, 232), (cx - rr // 3, cy), (cx + rr // 3, cy), 3)
            return
        for px, py in spots:
            k = rnd.random()
            if k < 0.4:
                pygame.draw.rect(s, (96, 100, 108), (px - 7, py - 6, 14, 12))
                pygame.draw.rect(s, (156, 160, 168), (px - 6, py - 6, 12, 10))
                pygame.draw.circle(s, (70, 74, 82), (px, py - 1), 4)
            elif k < 0.65:
                pygame.draw.circle(s, (70, 74, 84), (px + 1, py + 2), 10)
                pygame.draw.circle(s, (126, 130, 140), (px, py), 9)
                pygame.draw.circle(s, (170, 174, 184), (px - 2, py - 3), 5)
            elif k < 0.85:
                pygame.draw.rect(s, (110, 164, 196), (px - 9, py - 6, 18, 12))
                pygame.draw.line(s, (60, 100, 130), (px - 9, py), (px + 8, py), 1)
                pygame.draw.rect(s, (60, 100, 130), (px - 9, py - 6, 18, 12), 1)
            else:
                pygame.draw.rect(s, (34, 58, 100), (px - 13, py - 8, 26, 16))
                for gx in range(px - 13, px + 13, 6):
                    pygame.draw.line(s, (92, 124, 176), (gx, py - 8), (gx, py + 7), 1)
                pygame.draw.line(s, (92, 124, 176), (px - 13, py), (px + 12, py), 1)

    # ------------------------------------------------------------------ colisiones (rectángulos)
    def gc_setup(self, rects, info):
        g = self.g
        grid = {}
        for k, (x0, y0, x1, y1) in enumerate(rects):
            for cx in range(int(x0 // RCS), int(x1 // RCS) + 1):
                for cy in range(int(y0 // RCS), int(y1 // RCS) + 1):
                    grid.setdefault((cx, cy), []).append(k)
        g['rects'], g['rgrid'], g['district'] = rects, grid, info
        self.gc_nav_build()

    def gc_near(self, x0, y0, x1, y1):
        g = self.g
        out = set()
        grid = g['rgrid']
        for cx in range(int(x0 // RCS), int(x1 // RCS) + 1):
            for cy in range(int(y0 // RCS), int(y1 // RCS) + 1):
                out.update(grid.get((cx, cy), ()))
        return out

    def gc_push(self, s, m):
        """Saca a un soldado de los edificios y vehículos (círculo contra rectángulo)."""
        g = self.g
        rects = g['rects']
        for _ in range(2):
            for k in self.gc_near(s['x'] - m, s['y'] - m, s['x'] + m, s['y'] + m):
                x0, y0, x1, y1 = rects[k]
                qx, qy = clamp(s['x'], x0, x1), clamp(s['y'], y0, y1)
                dx, dy = s['x'] - qx, s['y'] - qy
                d2 = dx * dx + dy * dy
                if d2 >= m * m:
                    continue
                if d2 > 1e-6:
                    d = math.sqrt(d2)
                    s['x'], s['y'] = qx + dx / d * m, qy + dy / d * m
                else:
                    opts = ((s['x'] - x0, -1, 0), (x1 - s['x'], 1, 0), (s['y'] - y0, 0, -1), (y1 - s['y'], 0, 1))
                    pen, nx, ny = min(opts, key=lambda o: o[0])
                    s['x'] += nx * (pen + m)
                    s['y'] += ny * (pen + m)

    def gc_point_solid(self, x, y):
        g = self.g
        rects = g['rects']
        for k in g['rgrid'].get((int(x // RCS), int(y // RCS)), ()):
            x0, y0, x1, y1 = rects[k]
            if x0 <= x <= x1 and y0 <= y <= y1:
                return True
        return False

    def gc_los(self, ax, ay, bx, by):
        """False si algún edificio o vehículo corta la línea."""
        g = self.g
        rects = g['rects']
        dx, dy = bx - ax, by - ay
        for k in self.gc_near(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)):
            x0, y0, x1, y1 = rects[k]
            t0, t1 = 0.0, 1.0
            ok = True
            for p0, dd, lo, hi in ((ax, dx, x0, x1), (ay, dy, y0, y1)):
                if abs(dd) < 1e-9:
                    if p0 < lo or p0 > hi:
                        ok = False
                        break
                else:
                    ta, tb = (lo - p0) / dd, (hi - p0) / dd
                    if ta > tb:
                        ta, tb = tb, ta
                    t0, t1 = max(t0, ta), min(t1, tb)
                    if t0 > t1:
                        ok = False
                        break
            if ok:
                return False
        return True

    # ------------------------------------------------------------------ navegación
    def gc_blocked(self, x, y, m):
        g = self.g
        rects = g['rects']
        for k in self.gc_near(x - m, y - m, x + m, y + m):
            x0, y0, x1, y1 = rects[k]
            qx, qy = clamp(x, x0, x1), clamp(y, y0, y1)
            if (x - qx) ** 2 + (y - qy) ** 2 < m * m:
                return True
        for c in g['covers']:
            if (x - c['x']) ** 2 + (y - c['y']) ** 2 < (c['r'] + m) ** 2:
                return True
        return False

    def gc_nav_build(self):
        g = self.g
        R, seed = g['R'], g['seed']
        n = int(math.ceil(R * 1.1 / NAV))
        N = 2 * n
        ox, oy = W / 2 - n * NAV, H / 2 - n * NAV
        ok = [False] * (N * N)
        for cy in range(N):
            y = oy + (cy + 0.5) * NAV
            for cx in range(N):
                x = ox + (cx + 0.5) * NAV
                if math.hypot(x - W / 2, y - H / 2) > coast_r(R, seed, math.atan2(y - H / 2, x - W / 2), 0.9):
                    continue
                if not self.gc_blocked(x, y, 13):
                    ok[cy * N + cx] = True
        par = [-1] * (N * N)
        dep = [-1] * (N * N)
        dq = deque()
        for cy in range(N):
            for cx in range(N):
                i = cy * N + cx
                if ok[i] and math.hypot(ox + (cx + 0.5) * NAV - W / 2, oy + (cy + 0.5) * NAV - H / 2) < ATT_R - 10:
                    dep[i] = 0
                    dq.append(i)
        while dq:
            i = dq.popleft()
            cx, cy = i % N, i // N
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < N and 0 <= ny < N):
                    continue
                j = ny * N + nx
                if dep[j] >= 0 or not ok[j]:
                    continue
                if dx and dy and not (ok[cy * N + nx] and ok[ny * N + cx]):
                    continue
                dep[j] = dep[i] + 1
                par[j] = i
                dq.append(j)
        g['nav'] = dict(N=N, ox=ox, oy=oy, par=par, dep=dep)

    def gc_flow(self, e):
        """Rumbo (grados) hacia el ayuntamiento siguiendo las calles; None si no hay camino conocido."""
        nv = self.g['nav']
        N, par, dep = nv['N'], nv['par'], nv['dep']
        cx, cy = int((e['x'] - nv['ox']) // NAV), int((e['y'] - nv['oy']) // NAV)
        if not (0 <= cx < N and 0 <= cy < N):
            return None
        i = cy * N + cx
        if dep[i] < 0:
            best = None
            for r_ in (1, 2):
                for yy in range(max(0, cy - r_), min(N, cy + r_ + 1)):
                    for xx in range(max(0, cx - r_), min(N, cx + r_ + 1)):
                        j = yy * N + xx
                        if dep[j] >= 0 and (best is None or dep[j] < dep[best]):
                            best = j
                if best is not None:
                    break
            if best is None:
                return None
            tx, ty = nv['ox'] + (best % N + 0.5) * NAV, nv['oy'] + (best // N + 0.5) * NAV
            return bearing(tx - e['x'], ty - e['y'])
        p = par[i]
        if p < 0:
            return None
        if par[p] >= 0:
            p = par[p]
        return bearing(nv['ox'] + (p % N + 0.5) * NAV - e['x'], nv['oy'] + (p // N + 0.5) * NAV - e['y'])

    def gc_covers(self, info, seed):
        rnd = random.Random(seed + 77)
        return [dict(x=x, y=y, r=15, kind='sandbag', seed=rnd.randrange(10 ** 6)) for x, y in info['spots']]

    # ------------------------------------------------------------------ efectos
    def gc_fires(self, dt):
        """Humo y llamas sobre el ayuntamiento a medida que baja la vida de la ciudad."""
        g = self.g
        hp = g['city']['hp']
        if hp >= 70:
            return
        hx0, hy0, hx1, hy1 = g['district']['hall']
        sev = 1.0 if hp < 35 else 0.5
        if random.random() < dt * (6 + 10 * sev):
            x, y = random.uniform(hx0, hx1), random.uniform(hy0, hy1)
            self.fx.add('smoke', x, y, random.uniform(-8, 8), -28, 2.4, 6, 30, (46, 46, 48))
        if hp < 55 and random.random() < dt * 12 * sev:
            self.fx.add('glow', random.uniform(hx0, hx1), random.uniform(hy0, hy1), life=.35, r0=8, r1=22, col=(255, 140, 50))

    def gc_draw_overlay(self, cv, cx_, cy_):
        """Marcador del ayuntamiento cuando queda fuera de pantalla."""
        g = self.g
        hx0, hy0, hx1, hy1 = g['district']['hall']
        sx, sy = (hx0 + hx1) / 2 - cx_, (hy0 + hy1) / 2 - cy_
        if 40 < sx < W - 40 and 40 < sy < H - 40:
            return
        mx, my = clamp(sx, 40, W - 40), clamp(sy, 120, H - 150)
        ax, ay = vec(bearing(sx - mx, sy - my))
        pts = [(mx + ax * 16, my + ay * 16), (mx - ax * 8 - ay * 10, my - ay * 8 + ax * 10), (mx - ax * 8 + ay * 10, my - ay * 8 - ax * 10)]
        pygame.draw.polygon(cv, (255, 190, 80), pts)
        pygame.draw.polygon(cv, (60, 40, 10), pts, 2)
        self.text(cv, 'AYUNTAMIENTO', self.f_s, (255, 210, 120), mx - ax * 30, my - ay * 30 - 8, 'c')
