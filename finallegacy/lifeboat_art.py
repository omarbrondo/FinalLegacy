"""Arte de la huida en lancha salvavidas (estilo River Raid): orillas con palmeras que se desplazan, arrecifes, lancha detallada,
aviones del combate aéreo y el puerto de la ciudad vista desde arriba."""
import math
import pygame
import random
from .common import H, W, bearing, clamp, draw_circ, glow

BANK_CELL = 150
CITY_H = 360                           # alto de la superficie del puerto
CITY_DOCK_Y = 262                      # y de la pantalla donde queda el muelle central cuando la ciudad está completa
PLANE_KEYS = ('viper', 'stealth', 'bomber')
PLANE_W = {'viper': 78, 'stealth': 74, 'bomber': 96}


def _ss(size, scale=4):
    return pygame.Surface((size[0] * scale, size[1] * scale), pygame.SRCALPHA)


class LifeboatArtMixin:
    # ------------------------------------------------------------------ iconos de vidas
    def life_icon(self):
        if getattr(self, '_life_icon', None) is None:
            s, _ = self.ships['p_map']
            self._life_icon = pygame.transform.smoothscale(pygame.transform.rotate(s, 90), (34, 12))
        return self._life_icon

    def draw_lives(self, cv, x, y):
        ic = self.life_icon()
        for i in range(self.lives):
            cv.blit(ic, (x + i * 37, y))

    # ------------------------------------------------------------------ orillas
    def lb_bank_w(self, y, side):
        yw = y - self.lb['scroll']
        s = 0.0 if side < 0 else 2.1
        w = 84 + 40 * math.sin(yw * 0.0055 + s) + 26 * math.sin(yw * 0.0161 + 1.3 + s) + 12 * math.sin(yw * 0.043 + side)
        return max(0.0, w * self.lb['bank_k'])

    def lb_channel(self, y):
        return self.lb_bank_w(y, -1), W - self.lb_bank_w(y, 1)

    def lb_draw_banks(self, cv, t):
        lb = self.lb
        ys = list(range(-16, H + 24, 8))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        for side in (-1, 1):
            ws = [self.lb_bank_w(y, side) for y in ys]

            def poly(extra, inset=0):
                pts = [((e + extra) if side < 0 else W - (e + extra), y) for e, y in zip(ws, ys)]
                if inset:
                    pts = [(x + inset * (1 if side < 0 else -1), y) for x, y in pts]
                edge = (-10 if side < 0 else W + 10)
                return pts + [(edge, ys[-1]), (edge, ys[0])]
            if max(ws) < 4:
                continue
            pygame.draw.polygon(ov, (70, 170, 190, 70), poly(46))
            pygame.draw.polygon(ov, (110, 200, 210, 90), poly(24))
            pygame.draw.polygon(ov, (214, 196, 146, 255), poly(0))
            pygame.draw.polygon(ov, (62, 118, 72, 255), poly(-14))
            pygame.draw.polygon(ov, (44, 98, 60, 255), poly(-36))
            # espuma en la orilla (animada)
            for y, wv in zip(ys[::2], ws[::2]):
                if wv > 6:
                    xx = wv + 3 + 2 * math.sin(t * 3 + y * 0.05)
                    xx = xx if side < 0 else W - xx
                    pygame.draw.circle(ov, (240, 250, 255, 150), (int(xx), int(y)), 3)
        cv.blit(ov, (0, 0))
        # vegetación y construcciones (deterministas por celda del mundo)
        c0 = int((-60 - lb['scroll']) // BANK_CELL)
        c1 = int((H + 60 - lb['scroll']) // BANK_CELL)
        for cell in range(c0, c1 + 1):
            for side in (-1, 1):
                rnd = random.Random(cell * 131 + (7 if side < 0 else 53))
                for _ in range(rnd.randint(2, 4)):
                    y = cell * BANK_CELL + rnd.random() * BANK_CELL + lb['scroll']
                    wv = self.lb_bank_w(y, side)
                    kind = rnd.choice(('palm', 'palm', 'bush', 'rock', 'hut', 'palm'))
                    fx = rnd.random()
                    if wv < 34:
                        continue
                    xo = 8 + fx * max(4.0, wv - 52)
                    x = xo if side < 0 else W - xo
                    self.lb_deco(cv, kind, x, y, rnd.random(), t)

    def lb_deco(self, cv, kind, x, y, r, t):
        sw = math.sin(t * 1.5 + x * 0.03) * 1.5
        if kind == 'palm':
            draw_circ(cv, x + 6, y + 8, 15, (0, 0, 0), 55)
            for k in range(7):
                a = k * 51 + r * 40
                ex, ey = x + math.cos(math.radians(a)) * 15 + sw, y + math.sin(math.radians(a)) * 15
                pygame.draw.line(cv, (34, 120, 52), (x, y), (ex, ey), 5)
                pygame.draw.line(cv, (70, 170, 80), (x, y), ((x + ex) / 2, (y + ey) / 2), 3)
            pygame.draw.circle(cv, (120, 84, 44), (int(x), int(y)), 3)
        elif kind == 'bush':
            draw_circ(cv, x + 4, y + 6, 12, (0, 0, 0), 50)
            pygame.draw.circle(cv, (36, 100, 54), (int(x), int(y)), 10)
            pygame.draw.circle(cv, (58, 140, 74), (int(x - 3), int(y - 3)), 7)
        elif kind == 'rock':
            pygame.draw.circle(cv, (92, 94, 98), (int(x), int(y)), 9)
            pygame.draw.circle(cv, (136, 138, 142), (int(x - 2), int(y - 2)), 6)
        else:
            draw_circ(cv, x + 5, y + 7, 14, (0, 0, 0), 55)
            pygame.draw.rect(cv, (170, 120, 76), (x - 11, y - 8, 22, 16), border_radius=2)
            pygame.draw.rect(cv, (120, 78, 48), (x - 11, y - 8, 22, 16), 2, border_radius=2)
            pygame.draw.polygon(cv, (200, 150, 90), [(x - 13, y - 9), (x + 13, y - 9), (x, y - 1)])

    # ------------------------------------------------------------------ arrecifes
    def lb_draw_reef(self, cv, rf, t):
        x, y = rf['x'], rf['y']
        pul = 0.5 + 0.5 * math.sin(t * 3 + x)
        draw_circ(cv, x, y, 26 + 3 * pul, (225, 245, 255), 70, 2)
        draw_circ(cv, x + 4, y + 6, 22, (0, 0, 0), 60)
        for dx, dy, rr, col in ((0, 0, 17, (74, 70, 66)), (-9, 6, 11, (92, 88, 82)), (10, 5, 10, (86, 82, 78)), (-3, -6, 10, (120, 116, 108))):
            pygame.draw.circle(cv, col, (int(x + dx), int(y + dy)), rr)
        pygame.draw.circle(cv, (230, 240, 245), (int(x - 5), int(y - 7)), 4)

    # ------------------------------------------------------------------ lancha salvavidas
    def lb_sprite(self):
        if getattr(self, '_lb_spr', None) is None:
            S = 4
            w, h = 44, 92
            s = _ss((w, h), S)

            def P(pts):
                return [(x * S, y * S) for x, y in pts]
            hull = [(22, 1), (31, 9), (38, 24), (41, 50), (40, 76), (36, 88), (8, 88), (4, 76), (3, 50), (6, 24), (13, 9)]
            pygame.draw.polygon(s, (22, 32, 48), P([(x + (x - 22) * 0.07, y) for x, y in hull]))
            pygame.draw.polygon(s, (236, 120, 34), P(hull))
            pygame.draw.polygon(s, (255, 170, 84), P([(22, 3), (13, 10), (7, 25), (5, 50), (7, 74), (10, 84), (16, 84), (14, 60), (14, 30), (18, 12)]))
            pygame.draw.polygon(s, (190, 88, 22), P([(22, 3), (31, 10), (37, 25), (39, 50), (38, 76), (35, 86), (30, 86), (31, 60), (30, 30), (26, 12)]))
            deck = [(22, 8), (30, 18), (34, 30), (35, 50), (34, 76), (31, 84), (13, 84), (10, 76), (9, 50), (10, 30), (14, 18)]
            pygame.draw.polygon(s, (240, 238, 226), P(deck))
            pygame.draw.polygon(s, (170, 168, 158), P(deck), S)
            # banca y consola
            pygame.draw.rect(s, (122, 128, 138), (12 * S, 62 * S, 20 * S, 5 * S), border_radius=S)
            pygame.draw.rect(s, (122, 128, 138), (12 * S, 72 * S, 20 * S, 5 * S), border_radius=S)
            pygame.draw.polygon(s, (52, 62, 78), P([(14, 44), (30, 44), (32, 54), (12, 54)]))
            pygame.draw.polygon(s, (120, 190, 230), P([(16, 45), (28, 45), (29, 51), (15, 51)]))
            pygame.draw.polygon(s, (230, 245, 255), P([(17, 46), (21, 46), (20, 49), (16, 49)]))
            # aro salvavidas en la proa
            pygame.draw.circle(s, (250, 250, 250), (22 * S, 22 * S), 6 * S)
            pygame.draw.circle(s, (220, 50, 40), (22 * S, 22 * S), 6 * S, 2 * S)
            pygame.draw.circle(s, (236, 120, 34), (22 * S, 22 * S), 3 * S)
            for ang in (0, 90, 180, 270):
                a = math.radians(ang + 45)
                pygame.draw.line(s, (220, 50, 40), (22 * S + math.cos(a) * 3 * S, 22 * S + math.sin(a) * 3 * S),
                                 (22 * S + math.cos(a) * 6 * S, 22 * S + math.sin(a) * 6 * S), 2 * S)
            # sobrevivientes con chaleco
            for (px, py, tone) in ((16, 66, (232, 190, 150)), (28, 66, (176, 120, 86)), (16, 76, (206, 160, 120)), (28, 76, (240, 205, 170))):
                pygame.draw.ellipse(s, (255, 130, 20), (px * S - 4 * S, py * S - 3 * S, 8 * S, 6 * S))
                pygame.draw.ellipse(s, (255, 210, 60), (px * S - 2 * S, py * S - 3 * S, 4 * S, 6 * S))
                pygame.draw.circle(s, tone, (px * S, (py - 1) * S), int(2.6 * S))
                pygame.draw.circle(s, (60, 44, 36), (px * S, (py - 2) * S), int(2.6 * S), S)
            # motor fuera de borda
            pygame.draw.rect(s, (36, 40, 46), (17 * S, 85 * S, 10 * S, 6 * S), border_radius=S)
            pygame.draw.rect(s, (90, 98, 108), (19 * S, 86 * S, 6 * S, 3 * S))
            # banderín y luz de proa
            pygame.draw.line(s, (60, 60, 64), (34 * S, 84 * S), (34 * S, 70 * S), S)
            pygame.draw.polygon(s, (230, 50, 44), P([(34, 70), (40, 72), (34, 75)]))
            pygame.draw.circle(s, (255, 230, 120), (22 * S, 5 * S), int(1.4 * S))
            self._lb_spr = pygame.transform.smoothscale(s, (w, h))
        return self._lb_spr

    def lb_plane_sprite(self, key, side):
        cache = self.air.setdefault('lb_spr', {})
        k = (key, side)
        if k not in cache:
            src = self.air[key]
            tw = PLANE_W[key]
            sc = tw / src.get_width()
            spr = pygame.transform.smoothscale(src, (tw, int(src.get_height() * sc)))
            cache[k] = pygame.transform.rotate(spr, 90 if side > 0 else -90)
        return cache[k]

    def lb_ensure_boats(self):
        if not self.ships.get('g_boat'):
            for key, src, k in (('g_boat', 'e_map', 1.55), ('a_ally', 'p_map', 1.5)):
                sf, sh = self.ships[src]
                self.ships[key] = (pygame.transform.rotozoom(sf, 0, k).convert_alpha(), pygame.transform.rotozoom(sh, 0, k).convert_alpha())

    # ------------------------------------------------------------------ puerto visto desde arriba
    def lb_city_surface(self, city):
        cache = getattr(self, '_lb_city', None)
        if cache and cache[0] == city['name']:
            return cache[1]
        rnd = random.Random(city['seed'] * 13 + 5)
        s = pygame.Surface((W, CITY_H), pygame.SRCALPHA)
        QY = 280                                                      # borde del muelle
        pygame.draw.rect(s, (66, 70, 78), (0, 0, W, QY))
        roofs = [(176, 84, 66), (150, 154, 160), (96, 128, 170), (206, 190, 150), (120, 140, 120), (190, 120, 84), (110, 112, 130), (226, 224, 218)]
        # calles
        vx = [0]
        while vx[-1] < W:
            vx.append(vx[-1] + rnd.randint(120, 170))
        hy = [10, 100, 190]
        for y in hy:
            pygame.draw.rect(s, (48, 52, 60), (0, y, W, 22))
            for x in range(0, W, 34):
                pygame.draw.rect(s, (230, 220, 150), (x, y + 10, 18, 2))
        for x in vx:
            pygame.draw.rect(s, (48, 52, 60), (x, 0, 20, QY))
        # manzanas con edificios, sombras y detalles
        for ri in range(len(hy) + 1):
            y0 = 0 if ri == 0 else hy[ri - 1] + 22
            y1 = hy[ri] if ri < len(hy) else QY - 6
            for ci in range(len(vx) - 1):
                x0, x1 = vx[ci] + 20, vx[ci + 1]
                if y1 - y0 < 24 or x1 - x0 < 24:
                    continue
                if rnd.random() < 0.12 and ri > 0:                    # plaza o parque
                    pygame.draw.rect(s, (70, 130, 78), (x0 + 3, y0 + 3, x1 - x0 - 6, y1 - y0 - 6), border_radius=6)
                    pygame.draw.ellipse(s, (70, 150, 190), (x0 + (x1 - x0) // 2 - 22, y0 + (y1 - y0) // 2 - 12, 44, 24))
                    for _ in range(9):
                        pygame.draw.circle(s, (40, 100, 56), (rnd.randint(x0 + 8, x1 - 8), rnd.randint(y0 + 8, y1 - 8)), rnd.randint(4, 8))
                    continue
                bx = x0 + 3
                while bx < x1 - 22:
                    bw = min(rnd.randint(26, 54), x1 - 3 - bx)
                    bh = y1 - y0 - 6 - rnd.randint(0, 10)
                    by = y0 + 3
                    col = rnd.choice(roofs)
                    pygame.draw.rect(s, (0, 0, 0, 80), (bx + 6, by + 8, bw, bh), border_radius=2)
                    pygame.draw.rect(s, col, (bx, by, bw, bh), border_radius=2)
                    pygame.draw.rect(s, tuple(max(0, c - 40) for c in col), (bx, by, bw, bh), 2, border_radius=2)
                    pygame.draw.rect(s, tuple(min(255, c + 24) for c in col), (bx + 3, by + 3, bw - 6, 4))
                    kind = rnd.random()
                    if kind < 0.34 and bw > 28:                       # cajas de aire acondicionado
                        for k in range(rnd.randint(1, 3)):
                            pygame.draw.rect(s, (205, 208, 214), (bx + 6 + k * 12, by + bh // 2, 9, 7))
                            pygame.draw.rect(s, (110, 114, 122), (bx + 6 + k * 12, by + bh // 2, 9, 7), 1)
                    elif kind < 0.52 and bw > 30:                     # paneles solares
                        pygame.draw.rect(s, (40, 70, 130), (bx + 6, by + 12, bw - 12, bh // 2))
                        for gx in range(bx + 6, bx + bw - 6, 7):
                            pygame.draw.line(s, (110, 150, 210), (gx, by + 12), (gx, by + 12 + bh // 2))
                    elif kind < 0.62:                                 # tanque de agua
                        pygame.draw.circle(s, (170, 176, 184), (bx + bw // 2, by + bh // 2), 8)
                        pygame.draw.circle(s, (110, 116, 126), (bx + bw // 2, by + bh // 2), 8, 2)
                    elif kind < 0.68 and bw > 36:                     # helipuerto
                        pygame.draw.circle(s, (60, 64, 72), (bx + bw // 2, by + bh // 2), 13)
                        pygame.draw.circle(s, (240, 220, 80), (bx + bw // 2, by + bh // 2), 13, 2)
                        pygame.draw.line(s, (240, 220, 80), (bx + bw // 2 - 5, by + bh // 2 - 6), (bx + bw // 2 - 5, by + bh // 2 + 6), 2)
                        pygame.draw.line(s, (240, 220, 80), (bx + bw // 2 + 5, by + bh // 2 - 6), (bx + bw // 2 + 5, by + bh // 2 + 6), 2)
                        pygame.draw.line(s, (240, 220, 80), (bx + bw // 2 - 5, by + bh // 2), (bx + bw // 2 + 5, by + bh // 2), 2)
                    bx += bw + rnd.randint(2, 6)
        # arbolitos y autos en las calles
        for _ in range(70):
            x, y = rnd.randint(0, W), rnd.choice(hy) + rnd.choice((-3, 26))
            pygame.draw.circle(s, (40, 104, 58), (x, y), rnd.randint(3, 5))
        for _ in range(26):
            y = rnd.choice(hy) + rnd.choice((3, 13))
            x = rnd.randint(0, W)
            col = rnd.choice(((220, 60, 50), (240, 240, 240), (60, 120, 220), (240, 190, 60), (60, 60, 66)))
            pygame.draw.rect(s, col, (x, y, 12, 6), border_radius=2)
            pygame.draw.rect(s, (24, 28, 36), (x + 7, y + 1, 3, 4))
        # muelle de concreto con bolardos, grúas y contenedores
        pygame.draw.rect(s, (176, 176, 168), (0, QY - 6, W, 32))
        pygame.draw.rect(s, (96, 98, 96), (0, QY + 20, W, 5))
        pygame.draw.rect(s, (60, 62, 62), (0, QY + 25, W, 3))
        for x in range(20, W, 56):
            pygame.draw.circle(s, (52, 56, 60), (x, QY + 15), 4)
        for gx in (W // 2 - 380, W // 2 + 360):
            pygame.draw.rect(s, (0, 0, 0, 70), (gx + 6, QY - 26, 56, 8))
            pygame.draw.rect(s, (240, 190, 40), (gx, QY - 32, 56, 8))
            pygame.draw.rect(s, (240, 190, 40), (gx + 40, QY - 32, 8, 40))
            pygame.draw.rect(s, (110, 84, 20), (gx, QY - 32, 56, 8), 1)
            pygame.draw.rect(s, (60, 64, 70), (gx + 36, QY - 28, 16, 10))
        for k in range(14):
            cx = rnd.randint(40, W - 80)
            if abs(cx - W // 2) < 70:
                continue
            col = rnd.choice(((200, 60, 50), (60, 110, 190), (230, 170, 50), (70, 150, 100), (210, 210, 210)))
            pygame.draw.rect(s, (0, 0, 0, 70), (cx + 3, QY + 1, 38, 12))
            pygame.draw.rect(s, col, (cx, QY - 3, 38, 12))
            pygame.draw.rect(s, tuple(max(0, c - 50) for c in col), (cx, QY - 3, 38, 12), 1)
            for gx2 in range(cx + 6, cx + 36, 7):
                pygame.draw.line(s, tuple(max(0, c - 30) for c in col), (gx2, QY - 3), (gx2, QY + 8))
        # muelles hacia el agua
        for px in (W // 2 - 280, W // 2, W // 2 + 280):
            pygame.draw.rect(s, (0, 0, 0, 80), (px - 27 + 7, QY + 22, 54, 64))
            pygame.draw.rect(s, (160, 158, 148), (px - 27, QY + 20, 54, 62))
            pygame.draw.rect(s, (96, 98, 96), (px - 27, QY + 20, 54, 62), 2)
            for yy in range(QY + 28, QY + 80, 12):
                pygame.draw.line(s, (130, 128, 120), (px - 27, yy), (px + 27, yy))
            for sx in (-22, 22):
                pygame.draw.circle(s, (52, 56, 60), (px + sx, QY + 78), 4)
        # faro
        fx = 70
        pygame.draw.circle(s, (0, 0, 0, 80), (fx + 5, QY - 8 + 6), 22)
        pygame.draw.circle(s, (236, 232, 224), (fx, QY - 8), 20)
        for rr, col in ((16, (214, 60, 52)), (11, (236, 232, 224)), (6, (214, 60, 52))):
            pygame.draw.circle(s, col, (fx, QY - 8), rr)
        pygame.draw.circle(s, (255, 236, 150), (fx, QY - 8), 3)
        self._lb_city = (city['name'], s)
        return s

    def lb_draw_city(self, cv, t, k):
        lb = self.lb
        city = lb['city']
        s = self.lb_city_surface(city)
        top = int(-CITY_H + (CITY_H - 40) * k)                  # con k=1 el muelle central queda cerca de CITY_DOCK_Y
        cv.blit(s, (0, top))
        # luces y haz del faro
        fx, fy = 70, top + 272
        a = t * 1.4
        glow(cv, fx, fy, 70, (255, 240, 170), 0.35)
        pygame.draw.line(cv, (255, 244, 190), (fx, fy), (fx + math.cos(a) * 190, fy + math.sin(a) * 190), 3)
        for px in (W // 2 - 280, W // 2, W // 2 + 280):
            col = (80, 255, 120) if (int(t * 2) + px) % 2 == 0 else (255, 80, 70)
            glow(cv, px - 22, top + 280 + 78, 18, col, 0.9)
            glow(cv, px + 22, top + 280 + 78, 18, (255, 80, 70) if col[0] == 80 else (80, 255, 120), 0.9)
        # rótulo
        if k > 0.85:
            self.text(cv, city['name'].upper(), self.f_l, (255, 255, 255), W // 2, top + 280 + 100, 'c')
        return top + 280 + 82                                     # y de la punta del muelle central

    # ------------------------------------------------------------------ dibujo principal
    def draw_lifeboat(self, cv):
        lb = self.lb
        t = self.t
        spr = self.lb_sprite()
        self.lb_ensure_boats()
        self.draw_ocean(cv, 0, -lb['scroll'], t)
        # estelas de las lanchas y hundimiento del buque en la introducción
        if lb['t'] < LB_INTRO_DRAW:
            k = clamp(lb['t'] / (LB_INTRO_DRAW + 1.0), 0, 1)
            sy = H - 120 + 40 * k + lb['scroll'] * 0
            self.blit_ship(cv, 'p_map', W / 2 - 60, sy, 8 + 40 * k, alpha=int(255 * (1 - k)))
            glow(cv, W / 2 - 60, sy, 60 * (1 - 0.5 * k), (255, 140, 50), 0.7 * (1 - k))
            if random.random() < 0.5:
                self.fxm.add('smoke', W / 2 - 60 + random.uniform(-20, 20), H - 120, random.uniform(-10, 10), -40, 2.0, 6, 26, (40, 40, 44))
        # arrecifes
        for rf in lb['reefs']:
            self.lb_draw_reef(cv, rf, t)
        # lanchas enemigas (salen de detrás de las orillas)
        for b in lb['boats']:
            self.blit_ship(cv, 'g_boat', b['x'], b['y'], 90 if b['vx'] > 0 else 270)
            if b['burst'] > 0:
                glow(cv, b['x'] + math.copysign(10, b['vx']), b['y'], 14, (255, 220, 140), 0.9)
        self.fxm.draw(cv)
        # orillas y ciudad
        self.lb_draw_banks(cv, t)
        kc = clamp((lb['p'] - 0.7) / 0.3, 0, 1)
        if kc > 0:
            lb['dock_y'] = self.lb_draw_city(cv, t, kc)
        # avisos de avión
        for wn in lb['warns']:
            x = 40 if wn['side'] > 0 else W - 40
            if int(t * 8) % 2 == 0:
                pygame.draw.line(cv, (255, 80, 70), (0, wn['y']), (W, wn['y']), 2)
                pygame.draw.polygon(cv, (255, 210, 70), [(x, wn['y'] - 22), (x - 18, wn['y'] + 10), (x + 18, wn['y'] + 10)])
                self.text(cv, '!', self.f_m, (40, 30, 24), x, wn['y'] - 14, 'c', shadow=False)
        # aviones (sprites del combate aéreo)
        for pl in lb['planes']:
            ps = self.lb_plane_sprite(pl['key'], pl['side'])
            draw_circ(cv, pl['x'] + 14, pl['y'] + 24, ps.get_width() // 3, (0, 0, 0), 55)
            cv.blit(ps, (pl['x'] - ps.get_width() // 2, pl['y'] - ps.get_height() // 2))
            d = 1 if pl['vx'] > 0 else -1
            glow(cv, pl['x'] - d * ps.get_width() * 0.5, pl['y'], 12, (255, 170, 80), 0.7)
            if pl['burst'] > 0:
                glow(cv, pl['x'] + d * ps.get_width() * 0.5, pl['y'], 14, (255, 220, 140), 0.9)
        # balas trazadoras
        for b in lb['bullets']:
            pygame.draw.line(cv, (255, 235, 140), (b['x'], b['y']), (b['x'] - b['vx'] * 0.035, b['y'] - b['vy'] * 0.035), 3)
            pygame.draw.circle(cv, (255, 120, 80), (int(b['x']), int(b['y'])), 3)
        # lancha salvavidas
        if lb['phase'] != 'dead' or lb['pt'] < 0.15:
            sp = abs(lb['vx']) + abs(lb['vy'])
            ang = bearing(lb['vx'], lb['vy'] - 40) if sp > 8 else 0.0
            ang = clamp(((ang + 180) % 360) - 180, -28, 28)
            if lb['phase'] != 'dead':
                for sd in (-1, 1):                                # ola de proa en V
                    ln = 26 + (14 if lb['boosting'] else 0)
                    pygame.draw.line(cv, (235, 246, 255), (lb['x'] + sd * 6, lb['y'] - 24), (lb['x'] + sd * (20 + ln * 0.4), lb['y'] + 10 + ln * 0.5), 2)
            r = pygame.transform.rotate(spr, -ang)
            draw_circ(cv, lb['x'] + 6, lb['y'] + 9, 26, (0, 0, 0), 60)
            cv.blit(r, (lb['x'] - r.get_width() // 2, lb['y'] - r.get_height() // 2))
            if lb['hurt'] > 0:
                glow(cv, lb['x'], lb['y'], 36, (255, 80, 60), 0.7)
            if lb['boosting']:
                glow(cv, lb['x'], lb['y'] + 44, 30, (140, 210, 255), 0.9)
        # HUD
        if lb['hurt'] > 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.rect(ov, (255, 40, 30, int(120 * lb['hurt'] / 0.25)), (0, 0, W, H), 14)
            cv.blit(ov, (0, 0))
        self.panel(cv, (W // 2 - 260, 12, 520, 76), 170)
        left = max(0.0, lb['T'] - max(0.0, lb['t'] - LB_INTRO_DRAW))
        col = (255, 90, 80) if left < 10 else (255, 235, 150)
        self.text(cv, 'RUMBO A %s' % lb['city']['name'].upper(), self.f_m, (160, 220, 255), W // 2 - 244, 18)
        self.text(cv, '%d:%02d' % (int(left) // 60, int(left) % 60), self.f_m, col, W // 2 + 244, 18, 'r')
        pygame.draw.rect(cv, (8, 12, 24), (W // 2 - 244, 52, 488, 20), border_radius=4)
        pygame.draw.rect(cv, (255, 160, 60), (W // 2 - 243, 53, int(486 * clamp(lb['p'], 0, 1)), 18), border_radius=4)
        mx = W // 2 - 243 + int(486 * clamp(lb['p'], 0, 1))
        pygame.draw.polygon(cv, (255, 255, 255), [(mx, 50), (mx - 6, 40), (mx + 6, 40)])
        self.panel(cv, (14, H - 96, 330, 82), 160)
        self.bar(cv, 26, H - 86, 306, 24, lb['hp'] / 100.0, (80, 220, 110) if lb['hp'] > 35 else (240, 80, 70), 'LANCHA %d%%' % max(0, lb['hp']))
        bcol = (255, 120, 80) if lb['boost_lock'] else (140, 210, 255)
        self.bar(cv, 26, H - 56, 306, 24, lb['boost'] / 100.0, bcol, 'MOTOR A FONDO' if not lb['boost_lock'] else 'MOTOR RECALENTADO')
        self.panel(cv, (W - 272, H - 58, 258, 44), 160)
        self.text(cv, 'BUQUES', self.f_s, (170, 200, 235), W - 262, H - 46)
        self.draw_lives(cv, W - 200, H - 46)
        if lb['t'] > LB_INTRO_DRAW and lb['phase'] == 'sail':
            self.text(cv, 'WASD mover  |  ESPACIO / SHIFT / clic: motor a fondo (avanzás más rápido)  |  esquivá ráfagas y arrecifes', self.f_s, (200, 220, 255), W // 2, H - 100, 'c')


LB_INTRO_DRAW = 2.4
