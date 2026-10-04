"""Núcleo de Game: recursos, utilidades de UI, partida, eventos, bucle y dibujo común."""
import math
import os
import pygame
import random
import sys
from .common import (
    ANTENNA_ISLANDS, CITY_DEFS, DECOR_ISLANDS, ENEMY_PORT,
    EXTRA_ISLANDS, FPS, H, HZ,
    Particles, W, WIN_WAVE, WORLD_H,
    WORLD_W, blob, clamp, coast_r,
    dist, lerp, shade, vec)
from .audio import Audio
from .sprites import (
    ENEMY_TYPES, draw_cover, make_cargo,
    make_cloud, make_f117, make_f16, make_shadow,
    make_ship, make_soldier_frames, make_sub, make_turret)
from .tk_art import make_tank_sprites, make_tk_textures
from .boss_art import BOSS_TYPES, make_boss_sprite


class CoreMixin:
    def __init__(self):
        pygame.display.set_caption('FINAL LEGACY - Edición Omar Brondo')
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED)
        except pygame.error:                      # sin renderizador: ventana común (sin escalado)
            self.screen = pygame.display.set_mode((W, H))
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        names = 'couriernew,consolas,dejavusansmono,liberationmono,monospace'
        mk = lambda s: pygame.font.SysFont(names, s, bold=True)
        self.f_s, self.f_m, self.f_l, self.f_xl = mk(15), mk(20), mk(32), mk(80)
        self.screen.fill((6, 10, 22))
        self.text(self.screen, 'CARGANDO SONIDOS Y GRAFICOS...', self.f_m, (160, 200, 255), W // 2, H // 2 - 10, 'c')
        pygame.display.flip()
        self.audio = Audio()
        self.build_assets()
        self.panels = {}
        self.fade_surf = pygame.Surface((W, H))
        self.crt_on = True
        self.paused = False
        self.t = 0.0
        self.shake = 0.0
        self.fade = 1.0
        self.toasts = []
        self.banners = []
        self.pops = []
        self.aim = [W / 2, 260.0]
        self.mouse_moved = False
        self.pad_init()
        self.hiscore = self.load_hi()
        self.state = 'title'
        self.end_msg = ''
        self.victory = False
        self.fx = Particles()
        self.fxm = Particles()
        self.reset()
        self.go('title')

    # ------------------------------------------------------------ assets
    def build_assets(self):
        base = pygame.Surface((W, H))
        for y in range(H):
            k = y / H
            pygame.draw.line(base, (int(lerp(18, 9, k)), int(lerp(62, 34, k)), int(lerp(116, 76, k))), (0, y), (W, y))
        self.ocean_base = base.convert()
        rnd = random.Random(5)

        def tile(n, col):
            s = pygame.Surface((256, 256), pygame.SRCALPHA)
            for _ in range(n):
                x, y, w = rnd.randint(8, 200), rnd.randint(8, 230), rnd.randint(14, 44)
                pygame.draw.arc(s, col, (x, y, w, max(4, w // 2)), 0.2, 2.9, 2)
            return s
        self.tileA = tile(50, (150, 205, 235, 62)).convert_alpha()
        self.tileB = tile(36, (255, 255, 255, 40)).convert_alpha()

        # ---- islas / ciudades (mundo)
        land = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        self.islands = []
        allisl = ([(x, y, r, s, True) for (_, x, y, r, s) in CITY_DEFS] + [(x, y, r, s, False) for (x, y, r, s) in EXTRA_ISLANDS]
                  + [(x, y, r, s, False) for (x, y, r, s) in DECOR_ISLANDS] + [(*ENEMY_PORT[:3], ENEMY_PORT[3], False)])
        for (x, y, r, seed, is_city) in allisl:
            self.islands.append((x, y, r, seed))
            self.paint_island(land, x, y, r, seed, is_city)
            if is_city:
                px, py = x, y + coast_r(r, seed, math.pi / 2, 1.0) * 0.96
                pygame.draw.rect(land, (112, 80, 48), (px - 9, py - 6, 18, 56))
                for k in range(6):
                    pygame.draw.rect(land, (70, 48, 30), (px - 11, py + k * 9, 4, 5))
                    pygame.draw.rect(land, (70, 48, 30), (px + 7, py + k * 9, 4, 5))
        self.land = land.convert_alpha()
        rc = random.Random(77)
        self.mclouds = [dict(x=rc.uniform(0, WORLD_W), y=rc.uniform(0, WORLD_H), i=k % 4, s=rc.uniform(1.8, 3.0))
                        for k in range(26)]
        sh_base = [make_cloud(s_)[1] for s_ in (1, 2, 3, 4)]
        for mc in self.mclouds:
            b_ = sh_base[mc['i']]
            mc['spr'] = pygame.transform.smoothscale(b_, (int(b_.get_width() * mc['s']), int(b_.get_height() * mc['s'])))
            mc['spr'].set_alpha(38)
        self.city_surf = {}
        for (name, x, y, r, seed) in CITY_DEFS:
            self.city_surf[name] = (self.make_city(r, seed, False), self.make_city(r, seed, True))

        # ---- naves
        self.ships = {}

        def reg(key, surf):
            self.ships[key] = (surf, make_shadow(surf))
        reg('p_map', make_ship(24, 66, (70, 140, 170), (110, 170, 190), (255, 210, 70)))
        reg('e_map', make_ship(22, 60, (150, 60, 60), (170, 90, 80), (30, 30, 30)))
        reg('p_hull', make_ship(46, 124, (70, 140, 170), (110, 170, 190), (255, 210, 70), False))
        reg('e_hull', make_ship(42, 112, (150, 60, 60), (170, 90, 80), (30, 30, 30), False))
        reg('s_map', make_sub(16, 62))
        reg('s_hull', make_sub(32, 128))
        reg('c_map', make_cargo(26, 70))
        self.tur_p = make_turret(8, (70, 140, 170))
        self.tur_e = make_turret(8, (150, 60, 60))
        self.tur_b = make_turret(12, (150, 160, 178))
        self.tur_b2 = make_turret(10, (150, 160, 178))
        for k_ in range(len(BOSS_TYPES)):
            reg('b%d_map' % k_, make_boss_sprite(k_, 46, 126))
            reg('b%d_hull' % k_, make_boss_sprite(k_, 98, 270))
        self.sol = {'p': make_soldier_frames('rifle', 'p')}
        for kd in ENEMY_TYPES:
            self.sol['e_' + kd] = make_soldier_frames(kd, 'e')
        for f_ in self.sol['e_sniper']:
            f_.fill((140, 170, 120, 255), special_flags=pygame.BLEND_RGBA_MULT)
        hurt = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(70):
            pygame.draw.rect(hurt, (200, 0, 0, int(150 * (1 - i / 70) ** 2)), (i, i, W - 2 * i, H - 2 * i), 1)
        self.hurt_surf = hurt.convert_alpha()
        self.side_ship = self.make_side_ship()
        flip = lambda s: pygame.transform.flip(s, False, True)
        isl, isl_r = [], (55, 72, 90, 110)
        for k, r in enumerate(isl_r):
            sz = int(r * 4.4)
            s_ = pygame.Surface((sz, sz), pygame.SRCALPHA)
            self.paint_island(s_, sz / 2, sz / 2, r, 21 + k, False)
            isl.append(s_.convert_alpha())
        gb = pygame.Surface((80, 80), pygame.SRCALPHA)
        draw_cover(gb, dict(x=40, y=40, r=24, kind='sandbag', seed=3))
        self.air = dict(
            f16=make_f16((170, 182, 196), (108, 120, 138), (60, 100, 200), 0.9),
            viper=flip(make_f16((172, 100, 90), (112, 58, 54), (30, 30, 30), 0.72)),
            stealth=flip(make_f117((220, 70, 56), 0.62)),
            bomber=flip(make_f117((255, 150, 40), 1.7)),
            boss=flip(make_f117((255, 90, 60), 3.0)),
            shadows={}, isl=isl, isl_r=isl_r, gbase=gb.convert_alpha(),
            clouds=[make_cloud(s_) for s_ in (1, 2, 3, 4)])
        self.antenna_gfx = self.make_antenna()
        self.antenna_big = self.make_antenna(1.5)
        self.cockpit = self.make_cockpit()
        self.tk_tex = make_tk_textures()
        self.tk_spr = make_tank_sprites()
        self.pt_art_prebuild()
        self.tk_sky_bg, self.tk_floor_bg, self.tk_moon = self.make_tk_backdrops()

        # ---- cielo de defensa
        sky = pygame.Surface((W, HZ))
        for y in range(HZ):
            k = y / HZ
            if k < .7:
                c = (int(lerp(4, 40, k / .7)), int(lerp(6, 20, k / .7)), int(lerp(26, 64, k / .7)))
            else:
                kk = (k - .7) / .3
                c = (int(lerp(40, 190, kk)), int(lerp(20, 90, kk)), int(lerp(64, 70, kk)))
            pygame.draw.line(sky, c, (0, y), (W, y))
        pygame.draw.circle(sky, (240, 240, 220), (870, 120), 34)
        pygame.draw.circle(sky, (210, 210, 195), (860, 112), 8)
        pygame.draw.circle(sky, (210, 210, 195), (882, 134), 5)
        self.sky = sky.convert()
        r3 = random.Random(2)
        self.stars = [(r3.randint(0, W), r3.randint(0, 380), r3.uniform(0, 6.28)) for _ in range(130)]

        # ---- CRT
        crt = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(crt, (0, 0, 0, 40), (0, y), (W, y))
        for i in range(46):
            pygame.draw.rect(crt, (0, 0, 0, int(110 * (1 - i / 46) ** 2)), (i, i, W - 2 * i, H - 2 * i), 1)
        self.crt = crt.convert_alpha()

    def paint_island(self, land, x, y, r, seed, is_city):
        for sc, a in ((1.55, 30), (1.38, 45), (1.22, 65)):
            pygame.draw.polygon(land, (90, 205, 215, a), blob(x, y, r, seed, sc))
        pygame.draw.polygon(land, (236, 250, 255, 110), blob(x, y, r, seed, 1.1), 3)
        pygame.draw.polygon(land, (222, 204, 148), blob(x, y, r, seed, 1.04))
        pygame.draw.polygon(land, (92, 150, 74), blob(x, y, r, seed, .9))
        pygame.draw.polygon(land, (110, 168, 84), blob(x - 5, y - 5, r, seed, .78))
        pygame.draw.polygon(land, (62, 118, 62), blob(x, y, r, seed, .55))
        rnd2 = random.Random(seed)
        for _ in range(int(r * .55)):
            a, d = rnd2.uniform(0, 6.28), rnd2.uniform(0.2, 0.8) * r
            tx, ty = x + math.cos(a) * d, y + math.sin(a) * d
            if is_city and d < r * 0.5:
                continue
            tr = rnd2.randint(4, 8)
            pygame.draw.circle(land, (30, 80, 44), (int(tx + 2), int(ty + 3)), tr)
            pygame.draw.circle(land, (52, 112, 58), (int(tx), int(ty)), tr)
            pygame.draw.circle(land, (92, 158, 80), (int(tx - 1), int(ty - 2)), max(2, tr // 2))
        if not is_city and r >= 100:
            for _ in range(3):
                a, d = rnd2.uniform(0, 6.28), rnd2.uniform(0.3, 0.6) * r
                hx, hy, hr = x + math.cos(a) * d, y + math.sin(a) * d, rnd2.uniform(0.16, 0.26) * r
                pygame.draw.circle(land, (60, 98, 52), (int(hx + 3), int(hy + 4)), int(hr))
                pygame.draw.circle(land, (116, 124, 96), (int(hx), int(hy)), int(hr))
                pygame.draw.circle(land, (150, 156, 126), (int(hx - hr * .25), int(hy - hr * .3)), int(hr * .58))
                pygame.draw.circle(land, (214, 218, 204), (int(hx - hr * .3), int(hy - hr * .4)), max(2, int(hr * .22)))

    def make_city(self, r, seed, ruined, k=1.0):
        """Ciudad vista desde arriba. k > 1 agranda los edificios (invasión de infantería: a escala de los soldados)."""
        size = int(r * 2.6)
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        rnd = random.Random(seed + 100)
        rad = r * (.56 if k == 1.0 else .78)
        pygame.draw.circle(s, (120, 120, 118) if not ruined else (60, 56, 52), (c, c), int(rad))
        if k != 1.0:
            pygame.draw.circle(s, (92, 92, 96), (c, c), int(rad), 4)
            pygame.draw.circle(s, (104, 104, 104), (c, c), int(rad * .5), 3)
        for a in range(0, 360, 45):
            dx, dy = vec(a, rad)
            pygame.draw.line(s, (80, 80, 84), (c, c), (c + dx, c + dy), 3)
        blds = []
        for _ in range(400 if k != 1.0 else 60):
            a, d = rnd.uniform(0, 6.28), rnd.uniform(0, r * (.46 if k == 1.0 else .62))
            bx, by = c + math.cos(a) * d, c + math.sin(a) * d
            bw, bd = int(rnd.randint(14, 28) * k), int(rnd.randint(8, 14) * k)
            hh = int(rnd.randint(14, 44) * k)
            if all(abs(bx - q[0]) > (bw + q[2]) / 2 + 3 or abs(by - q[1]) > 16 * k for q in blds):
                blds.append((bx, by, bw, bd, hh))
            if len(blds) >= (16 if k == 1.0 else 20):
                break
        for bx, by, bw, bd, hh in blds:
            hh = hh if not ruined else hh // 5
            pygame.draw.rect(s, (0, 0, 0, 80), (bx - bw / 2 + 4 + hh * .4, by - bd, bw, bd + 8))
        for bx, by, bw, bd, hh in sorted(blds, key=lambda q: q[1]):
            hh = hh if not ruined else hh // 5
            wall = (92, 104, 128) if not ruined else (50, 46, 44)
            roof = (176, 190, 210) if not ruined else (80, 72, 66)
            pygame.draw.rect(s, wall, (bx - bw / 2, by - hh, bw, hh))
            pygame.draw.rect(s, roof, (bx - bw / 2, by - hh - bd, bw, bd))
            if not ruined:
                ws = max(3, int(3 * k))
                for wy in range(int(by - hh + 4 * k), int(by - 3 * k), int(7 * k)):
                    for wx in range(int(bx - bw / 2 + 3 * k), int(bx + bw / 2 - 3 * k), int(6 * k)):
                        pygame.draw.rect(s, (255, 226, 130) if rnd.random() < .6 else (40, 50, 76), (wx, wy, ws, ws))
                if k != 1.0:
                    pygame.draw.rect(s, (60, 70, 92), (bx - bw / 2, by - hh, bw, hh), 1)
                    pygame.draw.rect(s, (130, 142, 164), (bx - bw / 2, by - hh - bd, bw, bd), 1)
        if ruined:
            for _ in range(8):
                pygame.draw.circle(s, (30, 26, 24), (int(c + rnd.uniform(-r * .4, r * .4)), int(c + rnd.uniform(-r * .4, r * .4))),
                                   rnd.randint(6, 14))
        return s

    def make_side_ship(self):
        s = pygame.Surface((300, 112), pygame.SRCALPHA)
        pygame.draw.polygon(s, (66, 76, 92), [(10, 70), (282, 70), (300, 58), (262, 106), (34, 106)])
        pygame.draw.polygon(s, (110, 40, 40), [(40, 98), (258, 98), (262, 106), (34, 106)])
        pygame.draw.line(s, (130, 145, 165), (10, 70), (282, 70), 3)
        pygame.draw.rect(s, (92, 104, 122), (110, 42, 76, 28))
        pygame.draw.rect(s, (120, 134, 154), (126, 26, 44, 16))
        for k in range(5):
            pygame.draw.rect(s, (250, 226, 130), (116 + k * 14, 50, 8, 6))
        pygame.draw.line(s, (150, 160, 175), (148, 26), (148, 6), 2)
        pygame.draw.rect(s, (150, 160, 175), (138, 5, 20, 3))
        pygame.draw.rect(s, (60, 66, 78), (192, 46, 18, 24))
        pygame.draw.rect(s, (255, 210, 70), (192, 54, 18, 4))
        pygame.draw.circle(s, (60, 70, 86), (232, 66), 11)
        return s

    def make_antenna(self, scale=1.0):
        S = 4
        w, h = 48 * S, 96 * S
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        base_y, top_y = h - 10 * S, 16 * S
        pygame.draw.ellipse(s, (0, 0, 0, 70), (cx - 20 * S, h - 11 * S, 40 * S, 9 * S))
        pygame.draw.rect(s, (118, 120, 128), (cx - 16 * S, base_y, 32 * S, 7 * S), border_radius=S * 2)
        pygame.draw.rect(s, (170, 172, 180), (cx - 16 * S, base_y, 32 * S, 2 * S), border_radius=S * 2)
        n = 8
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            y0, y1 = base_y + (top_y - base_y) * t0, base_y + (top_y - base_y) * t1
            hw0, hw1 = (12.5 - 10 * t0) * S, (12.5 - 10 * t1) * S
            c = (190, 196, 208)
            pygame.draw.line(s, c, (cx - hw0, y0), (cx + hw1, y1), S)
            pygame.draw.line(s, c, (cx + hw0, y0), (cx - hw1, y1), S)
            pygame.draw.line(s, (150, 156, 170), (cx - hw1, y1), (cx + hw1, y1), S)
        for side in (-1, 1):
            pygame.draw.line(s, (214, 220, 232), (cx + side * 12.5 * S, base_y), (cx + side * 2.5 * S, top_y), int(S * 1.6))
        pygame.draw.rect(s, (96, 100, 112), (cx - 7 * S, 30 * S, 14 * S, 3 * S), border_radius=S)
        pygame.draw.ellipse(s, (232, 236, 244), (cx - 21 * S, 22 * S, 18 * S, 14 * S))
        pygame.draw.ellipse(s, (170, 178, 194), (cx - 19 * S, 24 * S, 14 * S, 10 * S))
        pygame.draw.line(s, (90, 96, 110), (cx - 12 * S, 29 * S), (cx - 2 * S, 29 * S), int(S * 1.2))
        pygame.draw.circle(s, (255, 190, 70), (cx - 4 * S, 29 * S), int(S * 1.4))
        for dx in (3, 6):
            pygame.draw.rect(s, (228, 232, 240), (cx + dx * S, 18 * S, 2 * S, 12 * S), border_radius=S // 2)
        pygame.draw.line(s, (214, 220, 232), (cx, top_y), (cx, 6 * S), int(S * 1.2))
        pygame.draw.circle(s, (255, 70, 60), (cx, 6 * S), int(S * 2.2))
        pygame.draw.circle(s, (255, 190, 170), (cx - S // 2, 6 * S - S // 2), int(S * 0.9))
        return pygame.transform.smoothscale(s, (int(48 * scale), int(96 * scale)))

    def make_cockpit(self):
        vp = self.TK_VP
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(H):
            f = abs(y - vp.centery) / (H / 2)
            pygame.draw.line(s, (int(16 + 16 * (1 - f)), int(22 + 18 * (1 - f)), int(19 + 15 * (1 - f)), 255), (0, y), (W, y))
        for x in range(30, W, 70):
            for y in (10, H - 10):
                pygame.draw.circle(s, (8, 10, 9, 255), (x + 1, y + 1), 4)
                pygame.draw.circle(s, (110, 126, 116, 255), (x, y), 4)
                pygame.draw.circle(s, (170, 184, 174, 255), (x - 1, y - 1), 1)
        for rect in ((28, 14, 380, 92), (W - 408, 14, 380, 92), (28, vp.bottom + 16, 330, 118), (W - 358, vp.bottom + 16, 330, 118),
                     (W // 2 - 185, vp.bottom + 46, 370, 44)):
            pygame.draw.rect(s, (7, 11, 9, 255), rect, border_radius=8)
            pygame.draw.rect(s, (46, 96, 68, 255), rect, 2, border_radius=8)
        pygame.draw.circle(s, (9, 13, 11, 255), (W // 2, 62), 62)
        pygame.draw.circle(s, (30, 38, 33, 255), (W // 2, 62), 62, 8)
        pygame.draw.circle(s, (100, 118, 106, 255), (W // 2, 62), 62, 2)
        pygame.draw.rect(s, (0, 0, 0, 0), vp, border_radius=28)
        pygame.draw.rect(s, (100, 118, 106, 255), vp.inflate(10, 10), 4, border_radius=32)
        pygame.draw.rect(s, (28, 36, 31, 255), vp.inflate(26, 26), 10, border_radius=38)
        return s.convert_alpha()

    # ------------------------------------------------------------ util
    def text(self, dst, s, font, col, x, y, anchor='l', shadow=True, alpha=None):
        img = font.render(s, True, col)
        r = img.get_rect()
        if anchor == 'l':
            r.topleft = (x, y)
        elif anchor == 'c':
            r.midtop = (x, y)
        else:
            r.topright = (x, y)
        if shadow:
            sh = font.render(s, True, (0, 0, 0))
            if alpha is not None:
                sh.set_alpha(alpha)
            dst.blit(sh, (r.x + 2, r.y + 2))
        if alpha is not None:
            img.set_alpha(alpha)
        dst.blit(img, r)
        return r

    def panel(self, dst, rect, alpha=150):
        key = (rect[2], rect[3], alpha)
        s = self.panels.get(key)
        if s is None:
            s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
            pygame.draw.rect(s, (6, 12, 26, alpha), (0, 0, rect[2], rect[3]), border_radius=8)
            pygame.draw.rect(s, (90, 130, 180, 200), (0, 0, rect[2], rect[3]), 2, border_radius=8)
            self.panels[key] = s
        dst.blit(s, (rect[0], rect[1]))

    def dim(self, dst, v, rect=None):
        dst.fill((v, v, v), rect, special_flags=pygame.BLEND_RGB_SUB)

    def bar(self, dst, x, y, w, h, frac, col, label):
        frac = clamp(frac, 0, 1)
        pygame.draw.rect(dst, (8, 12, 24), (x, y, w, h), border_radius=4)
        if frac > 0:
            fw = max(2, int((w - 4) * frac))
            pygame.draw.rect(dst, col, (x + 2, y + 2, fw, h - 4), border_radius=3)
            pygame.draw.rect(dst, shade(col, 70), (x + 2, y + 2, fw, max(2, (h - 4) // 3)), border_radius=3)
        pygame.draw.rect(dst, (100, 125, 160), (x, y, w, h), 1, border_radius=4)
        self.text(dst, label, self.f_s, (235, 245, 255), x + 6, y + (h - 16) // 2)

    def toast(self, s, col=(255, 255, 255)):
        self.toasts.append([s, col, 3.0])
        self.toasts = self.toasts[-4:]

    def banner(self, title, sub='', col=(255, 220, 90), dur=2.6):
        self.banners.append([title, sub, col, dur, dur])

    def pop(self, s, x, y, col=(255, 255, 160)):
        self.pops.append([s, x, y, 1.0, col])

    def load_hi(self):
        try:
            with open(self.hi_path(), 'r') as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def hi_path(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'final_legacy_hiscore.txt')

    def save_hi(self):
        if self.score > self.hiscore:
            self.hiscore = self.score
            try:
                with open(self.hi_path(), 'w') as f:
                    f.write(str(self.score))
            except Exception:
                pass

    def on_land(self, x, y, margin=0):
        for ix, iy, ir, sd in self.islands:
            if dist(x, y, ix, iy) < coast_r(ir, sd, math.atan2(y - iy, x - ix), 1.1) + margin:
                return True
        return False

    def add_score(self, n):
        self.score += n

    # ------------------------------------------------------------ partida
    def reset(self):
        self.score = 0
        self.wave = 1
        self.sx, self.sy = 2400.0, 1350.0
        self.sh, self.sv = 0.0, 0.0
        self.hull, self.fuel, self.ammo = 100.0, 100.0, 30
        self.hull_max = 100.0
        self.up = {}
        self.up_left = 0
        self.antennas = {i: False for i in ANTENNA_ISLANDS}
        self.landing_attempts = {i: 0 for i in range(len(EXTRA_ISLANDS))}
        self.cities = []
        for (name, x, y, r, seed) in CITY_DEFS:
            c = dict(name=name, x=x, y=y, r=r, hp=100.0, dead=False, seed=seed)
            c['sky'] = self.make_skyline(seed)
            c['dock'] = (x, y + coast_r(r, seed, math.pi / 2, 1.04) + 46)
            self.cities.append(c)
        self.enemies = []
        self.crates = []
        self.crate_t = 18.0
        self.strike_t = 50.0
        self.warned = False
        self.strike_city = None
        self.last_strike = None
        self.strike_kind = 'missile'
        self.strike_n = 0
        self.strike_deck = []
        self.heli_init()
        self.attack = None
        self.radar_t = 0.0
        self.nests = []
        self.spawn_nests()
        self.rescue = None
        self.rescue_t = 45.0
        self.convoy = None
        self.convoy_t = 80.0
        self.port_tries = 0
        self.port_done = False
        self.cam = [self.sx - W / 2, self.sy - H / 2]
        self.wake_t = 0.0
        self.dock_t = 0.0
        self.crash_t = 0.0
        self.ammo_acc = 0.0
        self.empty_fuel_aid = False
        self.fxm = Particles()
        self.toasts, self.banners, self.pops = [], [], []
        self.spawn_wave()

    def go(self, state):
        self.state = state
        self.fade = 1.0
        pygame.mouse.set_visible(state in ('upgrade',) or state not in ('defense', 'combat', 'aerial', 'ground', 'tank', 'port', 'heli'))
        self.audio.music({'title': 'calm', 'map': 'calm', 'defense': 'battle', 'combat': 'battle',
                          'aerial': 'battle', 'ground': 'battle', 'hack': 'battle', 'tank': 'battle', 'port': 'battle', 'upgrade': 'calm', 'heli': 'battle', 'helisel': 'calm', 'gameover': None}[state])
        if state not in ('map', 'combat'):
            self.audio.engine_vol(0)

    def start_game(self):
        self.reset()
        self.go('map')
        self.banner('OLEADA 1', 'Hundí la flota enemiga y defendé las ciudades', (120, 220, 255), 3.2)

    def game_over(self, msg, victory=False):
        self.end_msg = msg
        self.victory = victory
        self.save_hi()
        self.audio.play('win' if victory else 'lose')
        self.go('gameover')

    def debug_key(self, key):
        """Atajos de prueba en el mapa: F8 defensa de misiles, F9 subir de oleada, F10 +3000 puntos, F12 reabastecer todo."""
        if key == pygame.K_F8:
            alive = [c for c in self.cities if not c['dead']]
            if alive:
                self.strike_city = random.choice(alive)
                self.warned = False
                self.attack = None
                self.start_defense(self.strike_city)
        elif key == pygame.K_F9:
            self.wave = min(WIN_WAVE, self.wave + 1)
            self.enemies = []
            self.spawn_nests()
            self.spawn_wave()
            self.banner('MODO PRUEBA: OLEADA %d' % self.wave, 'Ahora F2-F8 muestran los modos con la dificultad de esa oleada', (255, 220, 120), 3.0)
        elif key == pygame.K_F10:
            self.add_score(3000)
            self.toast('MODO PRUEBA: +3000 puntos', (255, 220, 120))
        elif key == pygame.K_F12:
            self.hull, self.fuel, self.ammo = float(self.hull_max), 100.0, 40
            for c in self.cities:
                if not c['dead']:
                    c['hp'] = 100.0
            self.toast('MODO PRUEBA: casco, combustible, munición y ciudades al máximo', (255, 220, 120))

    def toggle_fullscreen(self):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    # ------------------------------------------------------------ eventos
    def handle(self, e):
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if e.type == pygame.MOUSEMOTION:
            self.mouse_moved = True
            self.aim = [float(e.pos[0]), float(e.pos[1])]
            if self.state == 'hack':
                self.h['kb'] = False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT):
                self.toggle_fullscreen()
            elif e.key == pygame.K_F1:
                self.crt_on = not self.crt_on
            elif e.key == pygame.K_m:
                self.audio.toggle_mute()
            elif e.key in (pygame.K_F8, pygame.K_F9, pygame.K_F10, pygame.K_F12) and self.state == 'map' and not self.paused:
                self.debug_key(e.key)
            elif e.key == pygame.K_F7 and self.state == 'map' and not self.paused:
                self.port_tries = min(self.port_tries, 1)
                self.start_port()
            elif e.key == pygame.K_F6 and self.state == 'map' and not self.paused:
                if self.convoy is None:
                    self.begin_convoy()
            elif e.key == pygame.K_F5 and self.state == 'map' and not self.paused:
                self.rescue = None
                self.begin_rescue()
            elif e.key in (pygame.K_F2, pygame.K_F3, pygame.K_F4) and self.state == 'map' and not self.paused:
                alive = [c for c in self.cities if not c['dead']]
                if alive:
                    self.strike_city = random.choice(alive)
                    self.warned = False
                    self.attack = None
                    {pygame.K_F2: self.start_tank, pygame.K_F3: self.start_aerial, pygame.K_F4: self.start_ground}[e.key](self.strike_city)
            elif e.key in (pygame.K_p, pygame.K_ESCAPE) and self.state in ('map', 'defense', 'combat', 'ground', 'aerial', 'hack', 'tank', 'port', 'heli'):
                self.paused = not self.paused
            elif e.key == pygame.K_q and self.paused:
                pygame.quit()
                sys.exit()
            elif self.state in ('title', 'gameover') and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()
            elif self.state == 'upgrade' and e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.pick_upgrade(e.key - pygame.K_1)
            elif self.state == 'defense' and e.key == pygame.K_SPACE and not self.paused:
                self.fire_interceptor()
            elif self.state == 'ground' and e.key in (pygame.K_SPACE, pygame.K_g) and not self.paused:
                self.throw_grenade_p()
            elif self.state == 'ground' and e.key == pygame.K_r and not self.paused:
                self.start_reload()
            elif self.state == 'ground' and e.key == pygame.K_q and not self.paused and self.g['stealth']:
                gp = self.g['p']
                if gp['reload'] <= 0:
                    gp['wpn'] = 'pistol' if gp['wpn'] == 'rifle' else 'rifle'
                    self.audio.play('blip', .5)
            elif self.state == 'ground' and e.key == pygame.K_e and not self.paused:
                self.takedown()
            elif self.state == 'map' and e.key == pygame.K_t and not self.paused:
                if self.nearest_port():
                    self.start_port()
            elif self.state == 'port' and not self.paused and e.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE):
                self.pt_jump()
            elif self.state == 'port' and not self.paused and e.key == pygame.K_g:
                self.pt_throw()
            elif self.state == 'map' and e.key == pygame.K_l and not self.paused:
                island = self.nearest_landing_island()
                if island:
                    self.start_landing(island[0])
            elif self.state == 'aerial' and e.key in (pygame.K_b, pygame.K_x) and not self.paused:
                self.air_bomb()
            elif self.state == 'helisel' and e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self.heli_pick(e.key - pygame.K_1)
            elif self.state == 'helisel' and e.key == pygame.K_ESCAPE:
                self.go('map')
            elif self.state == 'map' and e.key == pygame.K_c and not self.paused:
                self.heli_call()
            elif self.state == 'map' and e.key == pygame.K_b and not self.paused:
                self.heli_launch()
            elif self.state == 'heli' and e.key == pygame.K_SPACE and not self.paused:
                self.heli_rocket()
            elif self.state == 'tank' and e.key == pygame.K_SPACE and not self.paused:
                self.tk_fire()
            elif self.state == 'map' and e.key == pygame.K_h and not self.paused:
                self.try_hack()
            elif self.state == 'hack' and not self.paused:
                h = self.h
                if e.key == pygame.K_TAB and h['phase'] == 'play':
                    self.end_hack(False, abort=True)
                elif h['phase'] == 'fail':
                    if h['pt'] > 0.6 and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.hack_retry()
                    elif e.key == pygame.K_TAB:
                        self.end_hack(False)
                elif e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    dx = (e.key == pygame.K_RIGHT) - (e.key == pygame.K_LEFT)
                    dy = (e.key == pygame.K_DOWN) - (e.key == pygame.K_UP)
                    h['cur'] = (clamp(h['cur'][0] + dx, 0, h['cols'] - 1), clamp(h['cur'][1] + dy, 0, h['rows'] - 1))
                    h['kb'] = True
                elif e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                    h['kb'] = True
                    self.hack_rotate(h['cur'], 3 if e.key == pygame.K_z else 1)
            elif self.state == 'combat' and not self.paused:
                if e.key == pygame.K_SPACE:
                    self.fire_shell()
                elif e.key == pygame.K_e:
                    self.flee()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3) and self.state == 'hack' and not self.paused:
            if self.h['phase'] == 'fail':
                if self.h['pt'] > 0.6 and e.button == 1:
                    self.hack_retry()
            else:
                cell = self.hack_cell_at(e.pos)
                if cell:
                    self.hack_rotate(cell, 1 if e.button == 1 else 3)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'port' and not self.paused:
            self.pt_throw()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'ground' and not self.paused:
            self.throw_grenade_p()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'heli' and not self.paused:
            self.heli_rocket()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'aerial' and not self.paused:
            self.air_bomb()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.paused:
            if self.state == 'title' or self.state == 'gameover':
                self.start_game()
            elif self.state == 'defense':
                self.fire_interceptor()
            elif self.state == 'tank':
                self.tk_fire()
            elif self.state == 'helisel':
                for i in range(len(self.heli_cands)):
                    if self.heli_sel_rect(i).collidepoint(e.pos):
                        self.heli_pick(i)
            elif self.state == 'upgrade':
                for i in range(len(self.up_cards)):
                    if self.up_card_rect(i).collidepoint(e.pos):
                        self.pick_upgrade(i)
            elif self.state == 'combat':
                self.fire_shell()

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                self.handle(e)
            self.pad_poll(dt)
            if not self.paused:
                self.update(dt)
            self.draw()

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        self.fade = max(0.0, self.fade - dt * 2.2)
        self.shake *= 0.9 ** (dt * 60)
        for q in self.toasts:
            q[2] -= dt
        self.toasts = [q for q in self.toasts if q[2] > 0]
        for b in self.banners:
            b[3] -= dt
        self.banners = [b for b in self.banners if b[3] > 0]
        for p in self.pops:
            p[3] -= dt
            p[2] -= 30 * dt
        self.pops = [p for p in self.pops if p[3] > 0]
        if self.state == 'map':
            self.upd_map(dt)
        elif self.state == 'defense':
            self.upd_defense(dt)
        elif self.state == 'combat':
            self.upd_combat(dt)
        elif self.state == 'aerial':
            self.upd_aerial(dt)
        elif self.state == 'hack':
            self.upd_hack(dt)
        elif self.state == 'tank':
            self.upd_tank(dt)
        elif self.state == 'upgrade':
            self.upd_upgrade(dt)
        elif self.state == 'heli':
            self.upd_heli(dt)
        elif self.state == 'port':
            self.upd_port(dt)
        elif self.state == 'ground':
            self.upd_ground(dt)
        elif self.state in ('title', 'gameover'):
            self.fxm.update(dt)

    # ------------------------------------------------------------ DIBUJO
    def blit_ship(self, dst, key, x, y, heading, cx=0, cy=0, alpha=255):
        surf, sh = self.ships[key]
        r = pygame.transform.rotate(surf, -heading)
        rs = pygame.transform.rotate(sh, -heading)
        sx, sy = int(x - cx), int(y - cy)
        rs.set_alpha(int(85 * alpha / 255))
        dst.blit(rs, (sx - rs.get_width() // 2 + 5, sy - rs.get_height() // 2 + 7))
        if alpha < 255:
            r.set_alpha(alpha)
        dst.blit(r, (sx - r.get_width() // 2, sy - r.get_height() // 2))

    def nest_gfx(self):
        if not hasattr(self, '_nest_gfx'):
            S = 150
            s = pygame.Surface((S, S), pygame.SRCALPHA)
            c = S // 2
            pygame.draw.circle(s, (0, 0, 0, 50), (c + 4, c + 6), 62)
            pygame.draw.circle(s, (60, 120, 170), (c, c), 68, 3)
            pygame.draw.circle(s, (214, 196, 140), (c, c), 60)
            pygame.draw.circle(s, (86, 128, 78), (c, c), 50)
            rnd = random.Random(5)
            for _ in range(26):
                a, d = rnd.uniform(0, 6.28), rnd.uniform(14, 46)
                pygame.draw.circle(s, (54, 100, 58), (int(c + math.cos(a) * d), int(c + math.sin(a) * d)), rnd.randint(3, 6))
            for k in range(10):
                a = 6.2832 * k / 10
                pygame.draw.circle(s, (176, 150, 100), (int(c + math.cos(a) * 30), int(c + math.sin(a) * 30)), 6)
                pygame.draw.circle(s, (120, 100, 66), (int(c + math.cos(a) * 30), int(c + math.sin(a) * 30)), 6, 1)
            pygame.draw.circle(s, (120, 124, 128), (c, c), 22)
            pygame.draw.circle(s, (80, 84, 90), (c, c), 22, 3)
            self._nest_gfx = s
        return self._nest_gfx

    def blit_turret(self, dst, surf, x, y, ang, alpha=255):
        r = pygame.transform.rotate(surf, -ang)
        if alpha < 255:
            r.set_alpha(alpha)
        dst.blit(r, (int(x) - r.get_width() // 2, int(y) - r.get_height() // 2))

    def draw_ocean(self, dst, cx, cy, t):
        dst.blit(self.ocean_base, (0, 0))
        for tile, sx, px, py in ((self.tileA, 1.0, t * 12, t * 5), (self.tileB, 0.8, -t * 8, t * 4)):
            ox = -((cx * sx + px) % 256)
            oy = -((cy * sx + py) % 256)
            x = ox
            while x < W:
                y = oy
                while y < H:
                    dst.blit(tile, (int(x), int(y)))
                    y += 256
                x += 256

    def draw(self):
        cv = self.canvas
        if self.state in ('title',):
            self.draw_title(cv)
        elif self.state == 'map':
            self.draw_map(cv)
        elif self.state == 'defense':
            self.draw_defense(cv)
        elif self.state == 'combat':
            self.draw_combat(cv)
        elif self.state == 'aerial':
            self.draw_aerial(cv)
        elif self.state == 'hack':
            self.draw_hack(cv)
        elif self.state == 'tank':
            self.draw_tank(cv)
        elif self.state == 'upgrade':
            self.draw_upgrade(cv)
        elif self.state == 'heli':
            self.draw_heli(cv)
        elif self.state == 'helisel':
            self.draw_helisel(cv)
        elif self.state == 'port':
            self.draw_port(cv)
        elif self.state == 'ground':
            self.draw_ground(cv)
        elif self.state == 'gameover':
            self.draw_gameover(cv)
        self.draw_overlays(cv)
        ox = oy = 0
        if self.shake > 0.5:
            ox, oy = int(random.uniform(-self.shake, self.shake)), int(random.uniform(-self.shake, self.shake))
        self.screen.fill((0, 0, 0))
        self.screen.blit(cv, (ox, oy))
        if self.crt_on:
            self.screen.blit(self.crt, (0, 0))
        pygame.display.flip()

    def draw_overlays(self, cv):
        for i, q in enumerate(self.toasts):
            self.text(cv, q[0], self.f_m, q[1], W // 2, 70 + i * 26, 'c', alpha=int(255 * clamp(q[2], 0, 1)))
        if self.banners:
            b = self.banners[0]
            k = b[3] / b[4]
            a = int(255 * clamp(min(k * 6, (1 - k) * 8 + 0.2, 1), 0, 1))
            self.text(cv, b[0], self.f_l, b[2], W // 2, 190, 'c', alpha=a)
            if b[1]:
                self.text(cv, b[1], self.f_m, (235, 240, 255), W // 2, 232, 'c', alpha=a)
        for s, x, y, life, col in self.pops:
            self.text(cv, s, self.f_m, col, int(x), int(y), 'c', alpha=int(255 * clamp(life * 1.5, 0, 1)))
        if self.paused:
            self.dim(cv, 130)
            self.text(cv, 'PAUSA', self.f_xl, (255, 255, 255), W // 2, 260, 'c')
            self.text(cv, 'P / ESC: continuar   |   M: sonido   |   F1: efecto CRT   |   Q: salir', self.f_m, (190, 210, 240),
                      W // 2, 380, 'c')
        if self.fade > 0:
            self.fade_surf.set_alpha(int(255 * self.fade))
            cv.blit(self.fade_surf, (0, 0))

    # ---- título
    def draw_title(self, cv):
        t = self.t
        self.draw_ocean(cv, t * 30, t * 8, t)
        self.dim(cv, 45)
        x = (t * 70) % (W + 300) - 150
        self.blit_ship(cv, 'p_map', x, 640, 90)
        x2 = W + 150 - (t * 55) % (W + 300)
        self.blit_ship(cv, 'e_map', x2, 700, 270)
        for ln, y, col in (('FINAL', 90, (255, 220, 110)), ('LEGACY', 175, (255, 160, 70))):
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-3, -3), (3, 3), (-3, 3), (3, -3)):
                self.text(cv, ln, self.f_xl, (30, 10, 0), W // 2 + dx, y + dy, 'c', shadow=False)
            self.text(cv, ln, self.f_xl, col, W // 2, y, 'c', shadow=False)
        self.text(cv, 'EDICIÓN OMAR BRONDO', self.f_l, (120, 220, 255), W // 2, 275, 'c')
        self.panel(cv, (W // 2 - 380, 320, 760, 270), 170)
        lines = ['MAPA   W/S acelerar-frenar   A/D girar   R (en puerto) reabastecer   L desembarcar',
                 'DEFENSA   Mouse o flechas apuntan   Clic/ESPACIO lanzan interceptor',
                 'COMBATE   Mouse apunta, clic lanza un misil recto (¡adelantate!)   E: huir',
                 'TIERRA   WASD soldado   Clic disparar   R recargar   ESPACIO granada',
                 'TANQUE   W/S avanzar   A/D girar   ESPACIO o clic: cañón',
                 'JEFE   Instalá antenas en las islas (L) y hackeá su escudo con H cerca del buque',
                 'AIRE   WASD mover   ESPACIO disparar   B bomba',
                 'MANDO   Izq. mover  Der. apuntar  RT/A disparar  LT/B granada  X recargar  Y acción',
                 'P pausa  M sonido  F11 pantalla completa  F1 CRT  F2-F10, F12 modo prueba']
        for i, ln in enumerate(lines):
            self.text(cv, ln, self.f_s, (220, 232, 255), W // 2 - 360, 336 + i * 28)
        if int(t * 2) % 2 == 0:
            self.text(cv, 'PRESIONÁ ENTER PARA ZARPAR', self.f_l, (255, 255, 255), W // 2, 610, 'c')
        self.text(cv, 'Récord: %d' % self.hiscore, self.f_m, (255, 230, 120), W // 2, 665, 'c')
        self.text(cv, 'Hundí %d oleadas y salvá al menos una ciudad para ganar' % WIN_WAVE, self.f_s, (160, 190, 220), W // 2, 705, 'c')

    # ---- game over
    def draw_gameover(self, cv):
        self.draw_ocean(cv, self.t * 10, 0, self.t)
        self.dim(cv, 110)
        col = (120, 255, 160) if self.victory else (255, 90, 80)
        self.text(cv, '¡VICTORIA!' if self.victory else 'FIN DE LA PARTIDA', self.f_xl, col, W // 2, 180, 'c')
        self.text(cv, self.end_msg, self.f_l, (255, 255, 255), W // 2, 300, 'c')
        self.text(cv, 'Puntaje: %d' % self.score, self.f_l, (255, 230, 120), W // 2, 380, 'c')
        self.text(cv, 'Récord: %d' % self.hiscore, self.f_m, (200, 220, 255), W // 2, 430, 'c')
        alive = sum(1 for c in self.cities if not c['dead'])
        self.text(cv, 'Ciudades salvadas: %d/4   Oleada: %d' % (alive, self.wave), self.f_m, (200, 220, 255), W // 2, 470, 'c')
        if int(self.t * 2) % 2 == 0:
            self.text(cv, 'ENTER para jugar de nuevo', self.f_l, (255, 255, 255), W // 2, 560, 'c')

    # ---- HUD común
    def draw_hud(self, cv, show_fuel=True):
        self.panel(cv, (14, H - 126, 330, 112), 160)
        self.bar(cv, 26, H - 116, 306, 24, self.hull / self.hull_max, (80, 220, 110) if self.hull > 35 else (240, 80, 70), 'CASCO %d%%' % self.hull)
        if show_fuel:
            self.bar(cv, 26, H - 86, 306, 24, self.fuel / 100, (80, 180, 255) if self.fuel > 20 else (240, 80, 70), 'COMBUSTIBLE %d%%' % self.fuel)
        self.bar(cv, 26, H - 56, 306, 24, self.ammo / 40, (255, 210, 70) if self.ammo > 6 else (240, 80, 70), 'MUNICION %d' % self.ammo)
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, (160, 200, 240), 26, 42)

    def draw_cities_hud(self, cv):
        self.panel(cv, (W - 296, 12, 282, 56), 160)
        for i, c in enumerate(self.cities):
            x = W - 286 + i * 69
            col = (80, 230, 110) if c['hp'] > 60 else ((255, 200, 70) if c['hp'] > 30 else (240, 80, 70))
            if c['dead']:
                col = (90, 90, 90)
            pygame.draw.rect(cv, (8, 12, 24), (x, 22, 60, 12))
            pygame.draw.rect(cv, col, (x + 1, 23, int(58 * c['hp'] / 100), 10))
            self.text(cv, 'ABCD'[i] + ('X' if c['dead'] else ''), self.f_s, (230, 240, 255), x + 22, 38)
