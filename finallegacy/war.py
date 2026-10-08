"""Huellas de la guerra en el mapa: restos de barcos, manchas de petróleo, escombros, islas chamuscadas y
islotes que cambian de lugar a medida que avanzan las oleadas."""
import math
import random
import pygame
from .common import CITY_DEFS, DECOR_ISLANDS, EXTRA_ISLANDS, H, HELIPAD, W, WORLD_H, WORLD_W, dist, draw_circ, glow

DECOR0 = len(CITY_DEFS) + len(EXTRA_ISLANDS)       # índice del primer islote decorativo en self.islands


class WarMixin:
    def war_reset(self):
        """Nueva partida: devuelve los islotes a su lugar y borra los restos."""
        moved = dict(getattr(self, 'war', {}).get('moved', {}))
        self.war = dict(wrecks=[], slicks=[], debris=[], scars=[], moved={})
        for k in moved:
            x, y, r, s = DECOR_ISLANDS[k]
            self.war_move_island(k, x, y)
        self.war['moved'] = {}
        self._haze = {}

    def decor_now(self):
        """Islotes decorativos en su posición actual (sin el helipuerto, que nunca se mueve)."""
        return [self.islands[DECOR0 + k] for k in range(len(DECOR_ISLANDS)) if DECOR_ISLANDS[k] != HELIPAD]

    def war_move_island(self, k, nx, ny):
        idx = DECOR0 + k
        x, y, r, seed = self.islands[idx]
        m = int(r * 2.1)
        self.land.fill((0, 0, 0, 0), pygame.Rect(int(x) - m, int(y) - m, 2 * m, 2 * m))
        self.islands[idx] = (nx, ny, r, seed)
        for n in getattr(self, 'nests', ()):
            if n.get('isl') == idx:                              # la batería (o sus ruinas) se muda con el islote
                n['x'], n['y'] = nx, ny
        self.paint_island(self.land, nx, ny, r, seed, False)
        self.war['scars'] = [s for s in self.war['scars'] if s['isl'] != idx]
        if (nx, ny) == (DECOR_ISLANDS[k][0], DECOR_ISLANDS[k][1]):
            self.war['moved'].pop(k, None)
        else:
            self.war['moved'][k] = (nx, ny)

    def war_relocate(self, n):
        """Mueve n islotes a otro lugar (solo si su vecindario está libre para no pisar a otra isla)."""
        from .radio_mode import RADAR_IDX
        cand = [k for k in range(len(DECOR_ISLANDS)) if DECOR_ISLANDS[k] != HELIPAD and k not in RADAR_IDX]     # los radares no se mudan
        random.shuffle(cand)
        done = 0
        for k in cand:
            if done >= n:
                break
            x, y, r, seed = self.islands[DECOR0 + k]
            others = [o for i, o in enumerate(self.islands) if i != DECOR0 + k]
            if any(dist(x, y, o[0], o[1]) < 1.7 * (r + o[2]) + 30 for o in others):
                continue                                  # borrarlo dañaría a un vecino
            for _ in range(60):
                nx, ny = random.uniform(260, WORLD_W - 260), random.uniform(260, WORLD_H - 260)
                if dist(nx, ny, self.sx, self.sy) < 700:
                    continue
                if all(dist(nx, ny, o[0], o[1]) > 1.7 * (r + o[2]) + 60 for o in others):
                    self.war_move_island(k, nx, ny)
                    done += 1
                    break
        return done

    def war_advance(self):
        """Al pasar de oleada: más restos, más islas dañadas y algunos islotes cambian de lugar."""
        w = self.wave
        moved = self.war_relocate(2 + (w >= 4))
        wr = self.war
        for _ in range(2 + w // 2):
            for _ in range(60):
                x, y = random.uniform(220, WORLD_W - 220), random.uniform(220, WORLD_H - 220)
                if self.on_land(x, y, 170) or dist(x, y, self.sx, self.sy) < 450:
                    continue
                if any(dist(x, y, c['dock'][0], c['dock'][1]) < 260 for c in self.cities):
                    continue
                wr['wrecks'].append(dict(x=x, y=y, h=random.uniform(0, 360), kind=random.choice(('e', 'e', 'p', 'c')),
                                         fire=random.random() < 0.55, born=w, ph=random.uniform(0, 6.28)))
                for _ in range(random.randint(1, 2)):
                    wr['slicks'].append(dict(x=x + random.uniform(-60, 60), y=y + random.uniform(-60, 60),
                                             w=random.randint(90, 190), h=random.randint(50, 110), rot=random.uniform(0, 180)))
                for _ in range(random.randint(3, 6)):
                    wr['debris'].append(dict(x=x + random.uniform(-90, 90), y=y + random.uniform(-90, 90),
                                             rot=random.uniform(0, 360), kind=random.choice((0, 1, 2)), ph=random.uniform(0, 6.28)))
                break
        helipad_idx = DECOR0 + DECOR_ISLANDS.index(HELIPAD)
        isl = [i for i in range(len(CITY_DEFS), len(self.islands)) if i != helipad_idx]
        for _ in range(2 + w // 2):
            i = random.choice(isl)
            x, y, r, seed = self.islands[i]
            a, d = random.uniform(0, 6.28), random.uniform(0.1, 0.55) * r
            wr['scars'].append(dict(isl=i, dx=math.cos(a) * d, dy=math.sin(a) * d, r=random.uniform(0.12, 0.26) * r + 8, born=w))
        if moved:
            self.toast('La guerra cambió el mapa: %d islote%s se movieron' % (moved, '' if moved == 1 else 's'), (255, 190, 120))

    # ------------------------------------------------------------ vida (humo, fuego)
    def war_update(self, dt):
        wr = getattr(self, 'war', None)
        if not wr:
            return
        cx, cy = self.cam
        for wk in wr['wrecks']:
            if wk['fire'] and cx - 150 < wk['x'] < cx + W + 150 and cy - 150 < wk['y'] < cy + H + 150 and random.random() < dt * 5:
                self.fxm.add('smoke', wk['x'] + random.uniform(-14, 14), wk['y'] + random.uniform(-10, 10), random.uniform(-6, 6), -22,
                             random.uniform(2.0, 3.4), 6, 26, (46, 44, 44))
        for s in wr['scars']:
            if s['born'] < self.wave - 2:
                continue
            x, y = self.islands[s['isl']][0] + s['dx'], self.islands[s['isl']][1] + s['dy']
            if cx - 150 < x < cx + W + 150 and cy - 150 < y < cy + H + 150 and random.random() < dt * 2.5:
                self.fxm.add('smoke', x, y, random.uniform(-5, 5), -18, random.uniform(2.2, 3.6), 5, 22, (58, 54, 52))

    # ------------------------------------------------------------ dibujo
    def war_sprite(self, kind):
        cache = self.__dict__.setdefault('_wspr', {})
        s = cache.get(kind)
        if s is None:
            key = 'p_map' if kind == 'p' else 'e_map'
            base = self.ships[key][0]
            k = 1.7 if kind == 'c' else 1.3
            s = pygame.transform.smoothscale(base, (int(base.get_width() * k), int(base.get_height() * k))).convert_alpha()
            s.fill((78, 70, 66, 255), special_flags=pygame.BLEND_RGBA_MULT)
            w_, h_ = s.get_size()
            pygame.draw.polygon(s, (0, 0, 0, 0), [(0, h_ * 0.46), (w_ * 0.4, h_ * 0.52), (w_ * 0.2, h_ * 0.6), (w_ * 0.7, h_ * 0.5),
                                                  (w_, h_ * 0.56), (w_, h_ * 0.44), (w_ * 0.6, h_ * 0.4), (w_ * 0.3, h_ * 0.45)])
            for i in range(5):
                pygame.draw.circle(s, (20, 18, 16, 255), (int(w_ * (0.2 + 0.15 * i)), int(h_ * (0.3 + 0.07 * (i % 3)))), 3)
            cache[kind] = s
        return s

    def war_slick(self, w, h):
        cache = self.__dict__.setdefault('_wslk', {})
        s = cache.get((w, h))
        if s is None:
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (6, 10, 14, 105), (0, 0, w, h))
            pygame.draw.ellipse(s, (60, 50, 90, 38), (w * 0.12, h * 0.15, w * 0.76, h * 0.7))
            pygame.draw.ellipse(s, (12, 18, 20, 80), (w * 0.3, h * 0.3, w * 0.4, h * 0.4))
            cache[(w, h)] = s.convert_alpha()
            s = cache[(w, h)]
        return s

    def war_draw(self, cv, cx, cy):
        wr = getattr(self, 'war', None)
        if not wr:
            return
        t = self.t
        for sl in wr['slicks']:
            sx, sy = sl['x'] - cx, sl['y'] - cy
            if -220 < sx < W + 220 and -220 < sy < H + 220:
                spr = pygame.transform.rotate(self.war_slick(sl['w'], sl['h']), sl['rot'])
                cv.blit(spr, (sx - spr.get_width() // 2, sy - spr.get_height() // 2))
        for s in wr['scars']:
            x = self.islands[s['isl']][0] + s['dx'] - cx
            y = self.islands[s['isl']][1] + s['dy'] - cy
            if -120 < x < W + 120 and -120 < y < H + 120:
                draw_circ(cv, x, y, s['r'] * 1.25, (26, 22, 20), 120)
                draw_circ(cv, x, y, s['r'], (14, 12, 12), 170)
                draw_circ(cv, x, y, s['r'] * 0.55, (70, 56, 44), 120)
                if s['born'] >= self.wave - 1:
                    glow(cv, x, y, s['r'] * 1.4, (255, 110, 40), 0.35 + 0.15 * math.sin(t * 9 + s['dx']))
        for d in wr['debris']:
            sx, sy = d['x'] - cx + math.sin(t * 0.9 + d['ph']) * 4, d['y'] - cy + math.cos(t * 0.7 + d['ph']) * 3
            if -30 < sx < W + 30 and -30 < sy < H + 30:
                col = ((92, 70, 48), (60, 62, 66), (28, 26, 26))[d['kind']]
                a = math.radians(d['rot'] + t * 4)
                dx, dy = math.cos(a) * 9, math.sin(a) * 9
                pygame.draw.line(cv, col, (sx - dx, sy - dy), (sx + dx, sy + dy), 4 if d['kind'] == 0 else 3)
        for wk in wr['wrecks']:
            sx, sy = wk['x'] - cx, wk['y'] - cy
            if not (-160 < sx < W + 160 and -160 < sy < H + 160):
                continue
            spr = pygame.transform.rotate(self.war_sprite(wk['kind']), -wk['h'])
            bob = math.sin(t * 1.3 + wk['ph']) * 2
            cv.blit(spr, (sx - spr.get_width() // 2, sy - spr.get_height() // 2 + bob))
            draw_circ(cv, sx, sy + bob, spr.get_width() * 0.5, (230, 245, 255), 55, 2)
            if wk['fire']:
                glow(cv, sx, sy, 38 + 6 * math.sin(t * 8 + wk['ph']), (255, 120, 40), 0.55)

    def war_haze(self, cv):
        """Bruma de humo sobre todo el mapa, más densa cuanto más avanzó la guerra."""
        a = min(34, 7 * (self.wave - 1))
        if a <= 0:
            return
        hz = self.__dict__.setdefault('_haze', {})
        s = hz.get(a)
        if s is None:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((70, 56, 48, a))
            s = hz[a] = s.convert_alpha()
        cv.blit(s, (0, 0))
