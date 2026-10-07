"""Arte de la defensa de la ciudad: skyline por capas con luces y reflejos, destructor de perfil detallado y domo del escudo antimisil."""
import math
import random
import pygame
from .common import H, HZ, SKY_W, W, clamp, glow

SHIP_W, SHIP_H = 300, 112
GUN = (232, 56)             # posición de la torreta en el sprite (proa a la derecha)


def make_side_ship():
    """Destructor de perfil (proa a la derecha), dibujado al triple de tamaño y reducido para que quede suave."""
    S = 3
    s = pygame.Surface((SHIP_W * S, SHIP_H * S), pygame.SRCALPHA)

    def P(x, y):
        return (x * S, y * S)

    def poly(col, pts, width=0):
        pygame.draw.polygon(s, col, [P(*p) for p in pts], width)

    def rect(col, x, y, w, h, r=0, width=0):
        pygame.draw.rect(s, col, (x * S, y * S, w * S, h * S), width, border_radius=int(r * S))

    hull = [(8, 64), (278, 64), (298, 48), (284, 80), (262, 104), (30, 104), (10, 92)]
    poly((46, 56, 70), hull)
    poly((70, 84, 104), [(8, 64), (278, 64), (298, 48), (287, 76), (10, 78)])                         # costado iluminado
    poly((30, 38, 52), [(10, 92), (30, 104), (262, 104), (284, 80), (270, 90), (18, 90)])             # fondo del casco
    poly((120, 34, 38), [(22, 98), (264, 98), (270, 92), (16, 92)])                                    # línea de flotación roja
    pygame.draw.line(s, (170, 186, 208), P(10, 64), P(278, 64), 2 * S)                                 # borde de cubierta
    for x in range(30, 270, 22):                                                                       # planchas del casco
        pygame.draw.line(s, (40, 50, 66), P(x, 66), P(x - 4, 90), 1 * S)
    for x in range(40, 250, 30):                                                                       # portillos
        pygame.draw.circle(s, (250, 220, 130), P(x, 76), 2 * S)
    rect((34, 40, 54), 120, 50, 100, 14, 2)                                                            # superestructura
    rect((70, 82, 104), 120, 50, 100, 5, 2)
    rect((92, 104, 128), 140, 36, 62, 14, 3)                                                           # puente
    rect((60, 70, 90), 140, 36, 62, 4, 2)
    for k in range(6):
        rect((255, 226, 140), 146 + k * 9, 42, 6, 5)
    rect((54, 62, 80), 168, 24, 6, 14)                                                                 # mástil
    pygame.draw.line(s, (170, 180, 196), P(171, 24), P(171, 6), 2 * S)
    pygame.draw.ellipse(s, (150, 160, 180), (151 * S, 14 * S, 40 * S, 7 * S))                           # radar giratorio
    pygame.draw.circle(s, (255, 70, 60), P(171, 6), 3 * S)
    rect((70, 78, 94), 102, 36, 16, 28, 2)                                                             # chimenea
    rect((40, 44, 56), 102, 36, 16, 5, 2)
    rect((255, 200, 70), 102, 46, 16, 4)
    for i in range(6):                                                                                 # celdas de misiles en cubierta
        rect((26, 30, 40), 40 + i * 10, 56, 8, 7, 1)
        rect((90, 100, 118), 41 + i * 10, 57, 6, 2)
    rect((60, 66, 80), 220, 52, 30, 12, 3)                                                             # base de la torreta
    pygame.draw.circle(s, (86, 96, 116), P(*GUN), 9 * S)
    pygame.draw.circle(s, (40, 46, 58), P(*GUN), 9 * S, 2 * S)
    return pygame.transform.smoothscale(s, (SHIP_W, SHIP_H)).convert_alpha()


class DefenseArtMixin:
    def def_art_cache(self):
        if getattr(self, '_dfa', None) is None:
            self._dfa = dict(ship=make_side_ship(), bld={}, back={})
        return self._dfa

    # ------------------------------------------------------------------ skyline
    def def_back_layer(self, city):
        """Siluetas lejanas y brumosas detrás de la ciudad (una vez por ciudad)."""
        cache = self.def_art_cache()['back']
        s = cache.get(city['name'])
        if s is None:
            rnd = random.Random(city['seed'] * 7 + 1)
            s = pygame.Surface((W, 220), pygame.SRCALPHA)
            x = -20
            while x < W:
                bw, bh = rnd.randint(26, 60), rnd.randint(44, 150)
                for k in range(bh):
                    t = k / bh
                    pygame.draw.line(s, (int(58 - 22 * t), int(46 - 14 * t), int(88 - 24 * t), 255), (x, 220 - bh + k), (x + bw, 220 - bh + k))
                for j in range(220 - bh + 8, 214, 12):
                    for i in range(x + 5, x + bw - 5, 8):
                        if rnd.random() < 0.22:
                            pygame.draw.rect(s, (200, 170, 130, 255), (i, j, 3, 4))
                x += bw + rnd.randint(-4, 10)
            cache[city['name']] = s = s.convert_alpha()
        return s

    def def_building(self, b, dead):
        """Edificio con degradado, cara lateral, ventanas de varios tonos y remate; se arma una vez por tamaño."""
        cache = self.def_art_cache()['bld']
        key = (b['w'], b['h'], b['s'], dead, b['ant'])
        s = cache.get(key)
        if s is None:
            w, h = b['w'], b['h']
            s = pygame.Surface((w + 10, h + 40), pygame.SRCALPHA)
            ox, oy = 4, 36
            rnd = random.Random(b['s'] * 31 + w)
            wall_t, wall_b = ((26, 30, 54), (12, 14, 30)) if not dead else ((30, 28, 32), (18, 16, 18))
            for k in range(h):
                t = k / max(1, h)
                pygame.draw.line(s, tuple(int(wall_t[i] + (wall_b[i] - wall_t[i]) * t) for i in range(3)), (ox, oy + k), (ox + w - 1, oy + k))
            pygame.draw.rect(s, (46, 52, 84) if not dead else (50, 46, 50), (ox, oy, 4, h))                    # cara iluminada
            pygame.draw.rect(s, (8, 10, 20), (ox + w - 4, oy, 4, h))                                          # cara en sombra
            pygame.draw.line(s, (84, 94, 140) if not dead else (70, 66, 70), (ox, oy), (ox + w - 1, oy), 2)    # cornisa
            if h > 70 and w >= 30 and not dead:                                                                # remate escalonado
                cw = w // 2
                pygame.draw.rect(s, (22, 26, 48), (ox + (w - cw) // 2, oy - 12, cw, 12))
                pygame.draw.line(s, (84, 94, 140), (ox + (w - cw) // 2, oy - 12), (ox + (w + cw) // 2 - 1, oy - 12), 2)
            if not dead:
                cols = ((255, 224, 130), (255, 196, 110), (190, 226, 255), (255, 240, 190))
                for j in range(oy + 8, oy + h - 8, 13):
                    for i in range(ox + 7, ox + w - 8, 9):
                        if rnd.random() < 0.52 and h > 24:
                            c = rnd.choice(cols)
                            pygame.draw.rect(s, c, (i, j, 4, 6))
                            pygame.draw.rect(s, tuple(v // 3 for v in c), (i, j + 6, 4, 1))
            if b['ant'] and h > 60 and not dead:
                top = oy - (12 if h > 70 and w >= 30 else 0)
                pygame.draw.line(s, (36, 40, 62), (ox + w // 2, top), (ox + w // 2, top - 24), 2)
            cache[key] = s = s.convert_alpha()
        return s, 4, 36

    def def_draw_skyline(self, cv, d, t):
        city = d['city']
        dead = city['dead']
        # resplandor del horizonte y capa lejana
        glow(cv, W // 2, HZ - 10, 460, (255, 120, 70), 0.55 if not dead else 0.8)
        cv.blit(self.def_back_layer(city), (0, HZ - 220))
        # costanera y muelle
        pygame.draw.rect(cv, (24, 28, 46), (0, HZ - 6, W, 8))
        pygame.draw.line(cv, (96, 104, 140), (0, HZ - 6), (W, HZ - 6), 2)
        for b in city['sky']:
            spr, ox, oy = self.def_building(b, dead)
            bx = int(d['sky_x'] + b['x'])
            top = HZ - b['h']
            cv.blit(spr, (bx - ox, top - oy))
            if b['ant'] and b['h'] > 60 and not dead and int(t * 2) % 2 == 0:
                glow(cv, bx + b['w'] // 2, top - 24 - (12 if b['h'] > 70 and b['w'] >= 30 else 0), 16, (255, 60, 60), 0.9)
            if not dead:                                                       # titileo de ventanas
                for q in range(2):
                    k = int(t * 3 + b['s'] + q * 7)
                    if k % 5 == 0:
                        cv.fill((255, 230, 150), (bx + 7 + (k * 5) % max(1, b['w'] - 14), top + 12 + (k * 13) % max(1, b['h'] - 24), 4, 6))
        # farolas de la costanera y reflejos en el agua
        x0 = int(d['sky_x']) - 40
        for i, lx in enumerate(range(x0, x0 + SKY_W + 80, 64)):
            on = not city['dead'] or (int(t * 6) + i) % 7 > 1
            col = (255, 214, 140) if on else (80, 70, 60)
            pygame.draw.line(cv, (40, 44, 64), (lx, HZ - 6), (lx, HZ - 20), 2)
            glow(cv, lx, HZ - 20, 22, col, 0.8 if on else 0.2)
            if on:
                for k in range(5):
                    rw = 8 - k
                    ry = HZ + 6 + k * 9 + (math.sin(t * 3 + i + k) * 1.5)
                    cv.fill((90 - k * 12, 62 - k * 8, 30), (lx - rw // 2 + math.sin(t * 2 + k) * 2, ry, rw, 3), special_flags=pygame.BLEND_RGB_ADD)

    # ------------------------------------------------------------------ buque y escudo
    def def_draw_ship(self, cv, sx, sy, t):
        art = self.def_art_cache()
        cv.blit(art['ship'], (sx - 150, sy - 70))
        for k in range(14):                                                    # espuma de proa y estela
            fx = sx - 148 + k * 22 + math.sin(t * 3 + k) * 4
            pygame.draw.line(cv, (200, 225, 245), (fx, sy + 38), (fx + 12, sy + 38), 2)
        pygame.draw.ellipse(cv, (220, 238, 252), (sx + 130, sy + 30, 34, 10), 2)
        pygame.draw.ellipse(cv, (14, 18, 34), (sx - 140, sy + 40, 280, 10))
        glow(cv, sx - 60, sy - 14, 30, (255, 220, 140), 0.25)                  # luz del puente sobre el casco
        return sx + 82, sy - 6                                                   # posición de la torreta (la misma de siempre)

    def def_draw_shield_dome(self, cv, d, sx, sy, t):
        """El escudo cubre toda la ciudad y el buque: cúpula con malla hexagonal que titila."""
        a = 1.0 if d['shield'] > 2 or int(t * 8) % 2 else 0.4
        dome = pygame.Surface((W, HZ), pygame.SRCALPHA)
        cx0, ry = W // 2, 330
        pygame.draw.ellipse(dome, (90, 170, 255, int(34 * a)), (-60, HZ - ry, W + 120, ry * 2))
        pygame.draw.ellipse(dome, (170, 225, 255, int(130 * a)), (-60, HZ - ry, W + 120, ry * 2), 3)
        for i in range(1, 9):
            ang = i * math.pi / 9
            x = cx0 + math.cos(ang) * (W / 2 + 60)
            pygame.draw.line(dome, (150, 210, 255, int(46 * a)), (cx0, HZ - ry - 10), (x, HZ), 1)
        for k in range(1, 5):
            rr = k * 0.22
            pygame.draw.ellipse(dome, (150, 210, 255, int(40 * a)), (-60 + (W + 120) * (1 - (1 - rr)) / 2 * 0 + 0, HZ - ry * (1 - rr * 0.5) - 0, W + 120, ry * 2 * (1 - rr * 0.5)), 1)
        sweep = (t * 0.8) % 1.0
        pygame.draw.ellipse(dome, (210, 240, 255, int(60 * a * (1 - sweep))), (-60 + sweep * 100, HZ - ry + sweep * 60, W + 120 - sweep * 200, ry * 2 - sweep * 120), 2)
        cv.blit(dome, (0, 0))
        draw = pygame.draw.circle
        for rad, al in ((170, 40), (166, 150)):
            s2 = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
            draw(s2, (110, 190, 255, int(al * a)), (rad + 2, rad + 2), rad, 0 if al < 100 else 2)
            cv.blit(s2, (sx - rad - 2, sy - 10 - rad - 2))
