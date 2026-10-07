"""Variedad por oleada: clima (niebla, noche, tormenta), corrientes marinas, ciudades con rol y eventos especiales de oleada."""
import math
import pygame
import random
from .common import CITY_DEFS, H, W, WORLD_H, WORLD_W, clamp, dist, draw_circ, glow

# clima y evento de cada oleada (la 1 es de práctica: aguas calmas)
PROFILES = {
    1: dict(title='AGUAS CALMAS', desc='', fog=False, night=False, storm=False, nests=0, subs=0, enemies=0, raid=1.0, convoy2=False, cur=0),
    2: dict(title='NIEBLA', desc='Radar reducido a la mitad  |  CONVOY DOBLE', fog=True, night=False, storm=False, nests=0, subs=0, enemies=0, raid=1.0, convoy2=True, cur=2),
    3: dict(title='NOCHE', desc='Poca visibilidad, enemigos menos atentos  |  MÁS INCURSIONES DE CAZAS', fog=False, night=True, storm=False, nests=0, subs=0, enemies=0, raid=0.5, convoy2=False, cur=2),
    4: dict(title='TORMENTA', desc='Olas y rayos  |  BATERÍAS COSTERAS POR TODOS LADOS', fog=False, night=False, storm=True, nests=4, subs=0, enemies=0, raid=1.0, convoy2=False, cur=3),
    5: dict(title='NIEBLA NOCTURNA', desc='Radar reducido y oscuridad  |  MANADA DE SUBMARINOS', fog=True, night=True, storm=False, nests=0, subs=2, enemies=0, raid=0.7, convoy2=True, cur=3),
    6: dict(title='TORMENTA NOCTURNA', desc='Olas, rayos y oscuridad  |  ASALTO FINAL', fog=False, night=True, storm=True, nests=2, subs=1, enemies=2, raid=0.5, convoy2=False, cur=4),
}
ROLES = {'PUERTO BRONDO': 'fuel', 'NUEVA ESPERANZA': 'repair', 'FORT LEGACY': 'ammo', 'BAHIA AZUL': 'all'}
ROLE_TXT = {'fuel': 'COMBUSTIBLE', 'repair': 'REPARACIONES', 'ammo': 'MUNICIÓN', 'all': 'TODO'}
CUR_W, CUR_L = 240.0, 1200.0
OFF_ROLE = 0.4              # una ciudad tiene solo el 40 % de los recursos que no son los suyos


class WaveWorldMixin:
    # ------------------------------------------------------------------ perfil y reinicio
    def wprof(self, wave=None):
        return PROFILES[min(max(1, wave or self.wave), max(PROFILES))]

    def wx_reset(self):
        self.wx = dict(currents=[], flash=0.0, thunder=None, bolt_t=random.uniform(8, 14), bolt=None, convoy2_done=False, rain_seed=random.random())
        self._fogs = None

    def wx_fog_flag(self):
        return bool(getattr(self, 'wx', None)) and self.wprof()['fog']

    def wx_radar_range(self):
        return 550 if self.wx_fog_flag() else 1100

    def wx_chase_mul(self):
        p = self.wprof()
        return (0.75 if p['night'] else 1.0) * (0.85 if p['fog'] else 1.0)

    def wx_next_convoy_t(self):
        """Tras un convoy: en las oleadas de convoy doble sale el segundo enseguida."""
        if self.wprof()['convoy2'] and not self.wx['convoy2_done']:
            self.wx['convoy2_done'] = True
            return 14.0
        return random.uniform(75, 105)

    def wx_wave_start(self, banner=True):
        """Nueva oleada: sortea las corrientes y avisa del clima y del evento."""
        p = self.wprof()
        self.wx['convoy2_done'] = False
        self.wx['flash'], self.wx['bolt'] = 0.0, None
        cur = []
        docks = [c['dock'] for c in self.cities]
        for _ in range(p['cur']):
            for _t in range(40):
                x, y = random.uniform(500, WORLD_W - 500), random.uniform(400, WORLD_H - 400)
                if all(dist(x, y, d[0], d[1]) > 480 for d in docks):
                    break
            a = random.uniform(0, 360)
            cur.append(dict(x=x, y=y, a=a, spd=60.0 + 6 * self.wave))
        self.wx['currents'] = cur
        self.raid_reset_timer()
        if banner and self.wave > 1:
            self.banner('OLEADA %d: %s' % (self.wave, p['title']), p['desc'], (150, 220, 255), 5.0)

    # ------------------------------------------------------------------ ciudades con rol
    def city_role(self, c):
        return ROLES.get(c['name'], 'all')

    def city_cap(self, c, key=None):
        """Tope de suministros: 100 (menos si la ciudad está dañada). Cada ciudad tiene el 100 % de su recurso y el 40 % del resto;
        la ciudad de rol TODO tiene el 100 % de los tres."""
        base = 100.0 * (0.5 + 0.5 * clamp(c['hp'] / 100.0, 0.0, 1.0))
        if key is None:
            return base
        role = self.city_role(c)
        return base if role == 'all' or key == role else base * OFF_ROLE

    def city_stock(self, c):
        return dict(fuel=self.city_cap(c, 'fuel'), repair=self.city_cap(c, 'repair'), ammo=self.city_cap(c, 'ammo'))

    def city_refill(self, c, amount):
        base = self.city_cap(c)
        for k in c['stock']:
            cap = self.city_cap(c, k)
            c['stock'][k] = min(cap, c['stock'][k] + amount * cap / max(1.0, base))

    def city_level(self, c):
        """Reservas que le importan a la ciudad: su recurso (o el más bajo de los tres en la ciudad de rol TODO)."""
        role = self.city_role(c)
        return min(c['stock'].values()) if role == 'all' else c['stock'][role]

    def city_full(self, c):
        return all(c['stock'][k] >= self.city_cap(c, k) - 1 for k in c['stock'])

    # ------------------------------------------------------------------ actualización
    def wx_update(self, dt):
        wx = self.wx
        p = self.wprof()
        t = self.t
        for cu in wx['currents']:
            if self.wx_in_current(cu, self.sx, self.sy):
                vx, vy = math.cos(math.radians(cu['a'])) * cu['spd'], math.sin(math.radians(cu['a'])) * cu['spd']
                self.sx = clamp(self.sx + vx * dt, 40, WORLD_W - 40)
                self.sy = clamp(self.sy + vy * dt, 40, WORLD_H - 40)
                if self.t - getattr(self, '_cur_toast', -99) > 25:
                    self._cur_toast = self.t
                    self.toast('Corriente marina: te arrastra', (150, 220, 255))
        wx['flash'] = max(0.0, wx['flash'] - dt * 3.0)
        if p['storm']:
            self.sx = clamp(self.sx + math.cos(t * 0.6) * 16 * dt, 40, WORLD_W - 40)               # oleaje
            self.sy = clamp(self.sy + math.sin(t * 0.47) * 16 * dt, 40, WORLD_H - 40)
            self.shake = max(self.shake, 1.4)
            wx['bolt_t'] -= dt
            if wx['bolt_t'] <= 0 and wx['bolt'] is None:
                wx['bolt_t'] = random.uniform(12, 20)
                a = random.uniform(0, 6.28)
                d = random.uniform(80, 260)
                wx['bolt'] = dict(x=self.sx + math.cos(a) * d, y=self.sy + math.sin(a) * d, t=0.0)
                self.audio.play('ping', .5)
            b = wx['bolt']
            if b is not None:
                b['t'] += dt
                if b['t'] >= 1.0:
                    wx['bolt'] = None
                    wx['flash'] = 1.0
                    wx['thunder'] = 0.35
                    self.shake = max(self.shake, 9)
                    self.fxm.add('glow', b['x'], b['y'], life=.5, r0=20, r1=90, col=(220, 230, 255))
                    if dist(b['x'], b['y'], self.sx, self.sy) < 75:
                        self.hull = max(1.0, self.hull - 6)
                        self.pop('-6', self.sx - self.cam[0], self.sy - self.cam[1] - 40, (255, 240, 150))
            if wx['thunder'] is not None:
                wx['thunder'] -= dt
                if wx['thunder'] <= 0:
                    wx['thunder'] = None
                    self.audio.play('boom_l', .3)

    def wx_in_current(self, cu, x, y):
        a = math.radians(cu['a'])
        dx, dy = x - cu['x'], y - cu['y']
        u = dx * math.cos(a) + dy * math.sin(a)
        v = -dx * math.sin(a) + dy * math.cos(a)
        return abs(u) < CUR_L / 2 and abs(v) < CUR_W / 2

    # ------------------------------------------------------------------ dibujo
    def wx_fog_surface(self):
        if self._fogs is None:
            R = 1100
            s = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
            for r in range(R, 250, -12):
                k = clamp((r - 250) / 330.0, 0.0, 1.0)
                pygame.draw.circle(s, (170, 184, 200, int(200 * k)), (R, R), r)
            self._fogs = s.convert_alpha()
        return self._fogs

    def wx_draw_currents(self, cv, cx, cy):
        t = self.t
        for cu in self.wx['currents']:
            a = math.radians(cu['a'])
            ca, sa = math.cos(a), math.sin(a)
            for lane in (-80, 0, 80):
                for i in range(-6, 7):
                    u = (i * 100 + (t * cu['spd'] * 0.9) % 100) - 50
                    if abs(u) > CUR_L / 2:
                        continue
                    px = cu['x'] + ca * u - sa * lane - cx
                    py = cu['y'] + sa * u + ca * lane - cy
                    if not (-60 < px < W + 60 and -60 < py < H + 60):
                        continue
                    fade = 1 - abs(u) / (CUR_L / 2)
                    col = (170, 225, 255)
                    p1 = (px - ca * 16 - sa * 9, py - sa * 16 + ca * 9)
                    p2 = (px + ca * 16, py + sa * 16)
                    p3 = (px - ca * 16 + sa * 9, py - sa * 16 - ca * 9)
                    draw_circ(cv, px, py, 3, col, 50 * fade)
                    pygame.draw.lines(cv, tuple(int(c * (0.35 + 0.35 * fade)) + 40 for c in col), False, [p1, p2, p3], 2)

    def wx_draw_weather(self, cv, cx, cy):
        p = self.wprof()
        wx = self.wx
        t = self.t
        sx, sy = self.sx - cx, self.sy - cy
        if p['fog']:
            fs = self.wx_fog_surface()
            cv.blit(fs, (sx - fs.get_width() // 2, sy - fs.get_height() // 2))
            for i in range(5):                                                   # jirones de niebla a la deriva
                bx = (i * 331 + t * 14 * (1 + i % 2)) % (W + 400) - 200
                by = 120 + i * 140 + math.sin(t * 0.3 + i) * 30
                draw_circ(cv, bx, by, 170, (210, 220, 232), 26)
        if p['storm']:
            cv.fill((170, 176, 196), special_flags=pygame.BLEND_RGB_MULT)
            for i in range(120):
                x = (i * 53.7 + t * 260) % (W + 80) - 40
                y = (i * 97.3 + t * 820) % (H + 40) - 20
                pygame.draw.line(cv, (170, 190, 215), (x, y), (x - 6, y + 16), 1)
            b = wx['bolt']
            if b is not None:
                bx, by = b['x'] - cx, b['y'] - cy
                pul = 0.5 + 0.5 * math.sin(t * 24)
                draw_circ(cv, bx, by, 75, (255, 240, 140), 40 + 50 * pul)
                draw_circ(cv, bx, by, 75, (255, 240, 140), 170, 2)
        if p['night']:
            cv.fill((78, 92, 150), special_flags=pygame.BLEND_RGB_MULT)
            for c in self.cities:
                if not c['dead']:
                    glow(cv, c['x'] - cx, c['y'] - cy, c['r'] * 1.5, (255, 214, 130), 0.75)
                    glow(cv, c['dock'][0] - cx, c['dock'][1] - cy, 70, (120, 255, 200), 0.6)
            ha = math.radians(self.sh)
            glow(cv, sx + math.sin(ha) * 70, sy - math.cos(ha) * 70, 150, (210, 230, 255), 0.55)         # reflector del barco
            for en in self.enemies:
                ex, ey = en['x'] - cx, en['y'] - cy
                if -80 < ex < W + 80 and -80 < ey < H + 80:
                    glow(cv, ex, ey, 46, (255, 90, 70) if not en.get('is_boss') else (255, 90, 230), 0.55 + 0.25 * math.sin(t * 5 + ex))
            for nst in self.nests:
                if nst['alive'] and (nst['seen'] or self.radar_t > 0):
                    glow(cv, nst['x'] - cx, nst['y'] - cy, 60, (255, 90, 60), 0.5 + 0.3 * math.sin(t * 4))
            for wk in self.war['wrecks']:
                if wk['fire']:
                    glow(cv, wk['x'] - cx, wk['y'] - cy, 70, (255, 150, 60), 0.5)
            for i in range(70):                                                    # reflejos de la luna sobre el agua
                x = (i * 197 - cx * 0.9) % W
                y = (i * 131 - cy * 0.9) % H
                k = 0.5 + 0.5 * math.sin(t * 2.2 + i * 1.7)
                if k > 0.6:
                    cv.fill((int(150 * k), int(180 * k), int(230 * k)), (x, y, 2, 2), special_flags=pygame.BLEND_RGB_ADD)
        if wx['flash'] > 0:
            fl = pygame.Surface((W, H))
            fl.fill((int(210 * wx['flash']),) * 3)
            cv.blit(fl, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def wx_tag(self):
        p = self.wprof()
        return '' if p['title'] == 'AGUAS CALMAS' else p['title']
