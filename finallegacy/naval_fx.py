"""Efectos épicos del combate naval: daños persistentes en los cascos, barcos que se parten al hundirse,
cámara lenta en el golpe final, columnas de agua, tormentas con relámpagos, reflectores y locutor."""
import math
import pygame
import random
from .common import H, W, clamp, draw_circ, glow, vec


class NavalFxMixin:
    def nv_init(self):
        c = self.c
        w = self.wave
        if c['is_boss']:
            wx = 'storm'
        elif c['nest']:
            wx = 'night' if w >= 2 else 'clear'
        else:
            wx = 'rain' if w % 3 == 0 else ('storm' if w % 5 == 0 else 'clear')
        c.update(wx=wx, marks={'p': [], 'e': []}, calls=[], call_cd={}, flashes=[], slow=0.0, hs=0.0, white=0.0, bolt=random.uniform(3, 6),
                 thunder=[], light=random.uniform(0, 360), final=False, lowhp=False, rain=[], splashed=set())
        c['rain'] = [(random.random() * W, random.random() * H, random.uniform(0.7, 1.3)) for _ in range(150)]
        if wx != 'clear':
            self.call_out({'storm': '¡TORMENTA!', 'rain': 'LLUVIA CERRADA', 'night': 'ASALTO NOCTURNO'}[wx], (200, 220, 255), 'wx')

    # ------------------------------------------------------------ locutor
    def call_out(self, text, col=(255, 230, 140), key=None, cd=2.0):
        c = self.c
        key = key or text
        if c['t'] < c['call_cd'].get(key, -9):
            return
        c['call_cd'][key] = c['t'] + cd
        c['calls'].append([text, col, 1.5])
        c['calls'] = c['calls'][-3:]

    # ------------------------------------------------------------ daño persistente
    def nv_mark(self, who, ship, x, y, dmg):
        """Agrega una marca de impacto (chamusquina y, si el casco está dañado, un foco de incendio) sobre el casco."""
        c = self.c
        rel = (x - ship['x'], y - ship['y'])
        fx, fy = vec(ship['h'], 1)
        lx, ly = vec(ship['h'] + 90, 1)
        f, l = rel[0] * fx + rel[1] * fy, rel[0] * lx + rel[1] * ly
        lim = 100 if (who == 'e' and c['is_boss']) else 38
        f, l = clamp(f, -lim, lim), clamp(l, -20, 20)
        lst = c['marks'][who]
        lst.append(dict(f=f, l=l, r=random.uniform(6, 10) + dmg * 0.25, fire=False, t=0.0, ph=random.uniform(0, 6)))
        if len(lst) > 16:
            lst.pop(0)

    def nv_mark_fires(self, who, ratio):
        """Cuanto más dañado el casco, más marcas arden."""
        lst = self.c['marks'][who]
        n_fire = int((1 - ratio) * len(lst) * 1.2)
        for i, m in enumerate(lst):
            m['fire'] = i >= len(lst) - n_fire and ratio < 0.75

    def nv_draw_marks(self, cv, who, ship, alpha=255):
        t = self.t
        for m in self.c['marks'][who]:
            ax, ay = vec(ship['h'], m['f'])
            bx, by = vec(ship['h'] + 90, m['l'])
            x, y = ship['x'] + ax + bx, ship['y'] + ay + by
            draw_circ(cv, x, y, m['r'] * 1.2, (18, 16, 14), 150 * alpha / 255)
            draw_circ(cv, x, y, m['r'] * 0.6, (60, 40, 30), 110 * alpha / 255)
            if m['fire'] and ship['sink'] is None:
                k = 0.75 + 0.25 * math.sin(t * 13 + m['ph'])
                glow(cv, x, y, m['r'] * 3.2 * k, (255, 130, 40), 0.85)
                glow(cv, x, y - 4, m['r'] * 1.6, (255, 230, 150), 0.7 * k)
                if random.random() < 0.06:
                    self.fx.add('smoke', x, y, random.uniform(-10, 4), -26, random.uniform(1.4, 2.4), 4, 18, (36, 34, 34))

    # ------------------------------------------------------------ hundimiento: el casco se parte en dos
    def nv_draw_split(self, cv, key, ship, alpha):
        surf = self.ships[key][0]
        w, h = surf.get_size()
        top = surf.subsurface((0, 0, w, h // 2))
        bot = surf.subsurface((0, h // 2, w, h - h // 2))
        s = ship['sink']
        sep = 4 + 18 * min(s, 3.0)
        for half, sign in ((top, 1), (bot, -1)):
            img = pygame.transform.rotate(half, -(ship['h'] + sign * min(s, 3.0) * 7))
            if alpha < 255:
                img.set_alpha(alpha)
            ox, oy = vec(ship['h'], sign * (h / 4 + sep))
            lx, ly = vec(ship['h'] + 90, sign * min(s, 3.0) * 4)
            cv.blit(img, (ship['x'] + ox + lx - img.get_width() // 2, ship['y'] + oy + ly - img.get_height() // 2))
        cx, cy = vec(ship['h'], 0)
        for k in range(3):
            lx, ly = vec(ship['h'] + 90, (k - 1) * w * 0.28)
            glow(cv, ship['x'] + cx + lx, ship['y'] + cy + ly, 30 + 8 * math.sin(self.t * 9 + k), (255, 140, 50), 0.8 * (alpha / 255))
        if random.random() < 0.5:
            self.fx.add('smoke', ship['x'] + random.uniform(-12, 12), ship['y'] + random.uniform(-12, 12), random.uniform(-14, 14), -30,
                        random.uniform(1.4, 2.4), 6, 28, (34, 32, 32))

    # ------------------------------------------------------------ actualización (clima, relámpagos, reflector)
    def nv_update(self, dt):
        c = self.c
        c['white'] = max(0.0, c['white'] - dt * 1.6)
        for cl in c['calls']:
            cl[2] -= dt
        c['calls'] = [cl for cl in c['calls'] if cl[2] > 0]
        c['flashes'] = [[x, y, r, col, k - dt * 5] for x, y, r, col, k in c['flashes'] if k - dt * 5 > 0]
        if c['wx'] in ('storm', 'rain'):
            c['bolt'] -= dt
            if c['bolt'] <= 0:
                c['bolt'] = random.uniform(4, 9) if c['wx'] == 'storm' else random.uniform(9, 16)
                c['white'] = max(c['white'], 0.55)
                c['thunder'].append(random.uniform(0.35, 0.9))
        c['thunder'] = [t_ - dt for t_ in c['thunder']]
        if any(t_ <= 0 for t_ in c['thunder']):
            c['thunder'] = [t_ for t_ in c['thunder'] if t_ > 0]
            self.audio.play('boom_l', .22)
            self.shake = max(self.shake, 2)
        if c['wx'] == 'night' and c['nest']:
            c['light'] = (c['light'] + 38 * dt) % 360
        # fase final del jefe: la música sube
        e = c['e']
        if c['is_boss'] and not c['final'] and e['sink'] is None and e['hp'] < e['max'] * 0.4:
            c['final'] = True
            self.audio.music('bossf', self.wave, 'battle')
            self.call_out('¡FASE FINAL!', (255, 90, 80), 'final', 9)
            self.shake = max(self.shake, 10)
        if not c['lowhp'] and self.hull < 35 and c['p']['sink'] is None:
            c['lowhp'] = True
            self.call_out('¡CASCO EN LLAMAS!', (255, 120, 90), 'lowhp', 9)

    def nv_lit(self):
        """¿Te está iluminando el reflector de la batería? (apuntan mejor)"""
        c = self.c
        if c['wx'] != 'night' or not c['nest']:
            return False
        e, p = c['e'], c['p']
        ang = bearing_to(e, p)
        d = (ang - c['light'] + 180) % 360 - 180
        return abs(d) < 14

    # ------------------------------------------------------------ dibujo de ambiente
    def nv_ocean_tint(self, cv):
        wx = self.c['wx']
        if wx == 'storm':
            self.dim(cv, 38)
        elif wx == 'rain':
            self.dim(cv, 22)
        elif wx == 'night':
            self.dim(cv, 48)

    def nv_draw_light(self, cv):
        c = self.c
        if c['wx'] != 'night' or not c['nest'] or c['e']['sink'] is not None:
            return
        e = c['e']
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        for w_, a in ((14, 26), (9, 34), (4, 46)):
            p1 = vec(c['light'] - w_, 1500)
            p2 = vec(c['light'] + w_, 1500)
            pygame.draw.polygon(ov, (255, 250, 210, a), [(e['x'], e['y']), (e['x'] + p1[0], e['y'] + p1[1]), (e['x'] + p2[0], e['y'] + p2[1])])
        cv.blit(ov, (0, 0))
        glow(cv, e['x'], e['y'], 40, (255, 250, 210), 0.9)

    def nv_draw_weather(self, cv):
        c = self.c
        wx = c['wx']
        t = self.t
        if wx in ('rain', 'storm'):
            n = 110 if wx == 'rain' else 150
            wind = 90 if wx == 'storm' else 40
            for i, (rx, ry, sp) in enumerate(c['rain'][:n]):
                x = (rx + t * wind * sp) % W
                y = (ry + t * 780 * sp) % H
                pygame.draw.line(cv, (150, 172, 200), (x, y), (x - wind * 0.03, y - 18 * sp), 1)
            for i in range(14):
                px = (i * 211 + int(t * 9) * 97) % W
                py = (i * 137 + int(t * 9) * 59) % H
                draw_circ(cv, px, py, 5 + (t * 20 + i) % 6, (200, 220, 240), 60, 1)
        if c['white'] > 0:
            v = int(180 * min(1.0, c['white']))
            cv.fill((v, v, v + 12 if v < 243 else v), special_flags=pygame.BLEND_RGB_ADD)
        if c['hs'] > 0:                                           # golpe grande: chispazo breve en pantalla
            cv.fill((26, 22, 18), special_flags=pygame.BLEND_RGB_ADD)

    def nv_draw_flashes(self, cv):
        for x, y, r, col, k in self.c['flashes']:
            glow(cv, x, y, r, col, clamp(k, 0, 1))

    def nv_draw_calls(self, cv):
        for i, (text, col, life) in enumerate(self.c['calls']):
            a = int(255 * clamp(min(life * 3, 1.0), 0, 1))
            y = 310 + i * 40 - int((1.5 - life) * 14)
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                self.text(cv, text, self.f_l, (20, 10, 6), W // 2 + dx, y + dy, 'c', shadow=False, alpha=a)
            self.text(cv, text, self.f_l, col, W // 2, y, 'c', shadow=False, alpha=a)


def bearing_to(a, b):
    return math.degrees(math.atan2(b['x'] - a['x'], -(b['y'] - a['y']))) % 360
