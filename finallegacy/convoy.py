"""Convoy épico: escoltas, emboscadas (cazadores, bombarderos, torpedos), apoyo antiaéreo (F) y una descarga que reabastece la ciudad."""
import math
import pygame
import random
from .common import H, W, WORLD_H, WORLD_W, angle_diff, bearing, clamp, coast_r, dist, draw_circ, glow, vec

UNLOAD_T = 1.6
FLAK_R = 300
FLAK_CD = 6.0
PLANE_SHAPE = ((0, -18), (4, -6), (22, 4), (22, 9), (4, 6), (3, 16), (10, 20), (10, 23), (0, 21), (-10, 23), (-10, 20), (-3, 16), (-4, 6), (-22, 9), (-22, 4), (-4, -6))
EVENT_ICON = {'raid1': 'C', 'air': 'A', 'sub': 'T', 'raid2': 'C', 'air2': 'A'}


class ConvoyMixin:
    # ------------------------------------------------------------------ armado
    def cv_need(self, c):
        return min(c['stock'].values()) / max(1.0, self.city_cap(c))

    def cv_say(self, who, text, col=(170, 255, 205)):
        calls = self.convoy['calls']
        calls.append([who, text, col, 4.6])
        del calls[:-3]
        self.audio.play('blip', .3)

    def begin_convoy(self):
        """Convoy aliado hacia la ciudad con menos reservas: escoltas, emboscadas y descarga final."""
        alive = [c for c in self.cities if not c['dead']]
        if len(alive) < 2:
            self.convoy_t = 20.0
            return
        dst = min(alive, key=self.cv_need)
        src = max((c for c in alive if c is not dst), key=lambda c: dist(c['x'], c['y'], dst['x'], dst['y']) + random.uniform(0, 500))
        sx, sy = src['dock']
        dx, dy = dst['dock']
        h0 = bearing(dx - sx, dy - sy)
        escorts = [dict(side=s, x=sx + s * 40.0, y=sy + 30.0, h=h0, hp=24.0, max=24.0, cd=random.uniform(0.3, 1.0), flash=0.0) for s in (-1, 1)]
        events = [dict(f=0.0, kind='raid1', done=False), dict(f=0.32 if self.wave >= 3 else 0.45, kind='air', done=False)]
        if self.wave >= 3:
            events.append(dict(f=0.58, kind='sub', done=False))
        events.append(dict(f=0.8, kind='raid2', done=False))
        if self.wave >= 5:
            events.append(dict(f=0.68, kind='air2', done=False))
        events.sort(key=lambda e: e['f'])
        total = dist(sx, sy, dx, dy)
        self.convoy = dict(x=float(sx), y=float(sy), h=h0, v=0.0, hp=100.0, src=src, dst=dst, t=0.0, total=total, f=0.0, state='sail',
                           escorts=escorts, events=events, planes=[], bombs=[], torps=[], calls=[], flak_cd=0.0, flak_fx=None, boxes=[],
                           unload=0.0, delivered=0.0, shots=[], planes_down=0, took=0.0, hit_t=0.0)
        self.audio.play('alarm', .6)
        low = int(self.cv_need(dst) * 100)
        self.banner('¡CONVOY EN PELIGRO!', 'Carguero de %s a %s (reservas al %d%%)  |  Escoltalo y usá F contra los bombarderos' % (src['name'], dst['name'], low),
                    (120, 255, 190), 4.6)
        self.cv_say('CARGUERO', '¡Zarpamos con suministros para %s!' % dst['name'])

    # ------------------------------------------------------------------ emboscadas
    def cv_spawn_raiders(self, n, ahead=True, hp_mul=1.0):
        c = self.convoy
        dx, dy = c['dst']['dock']
        mh = (9 + 2 * self.wave) * hp_mul
        for _ in range(n):
            if ahead:
                f = random.uniform(0.25, 0.6)
                px, py = c['x'] + (dx - c['x']) * f, c['y'] + (dy - c['y']) * f
            else:
                px, py = dx, dy
            for _k in range(50):
                a, r = random.uniform(0, 6.28), random.uniform(350, 520) if not ahead else random.uniform(0, 350)
                x, y = px + math.cos(a) * r, py + math.sin(a) * r
                if 100 < x < WORLD_W - 100 and 100 < y < WORLD_H - 100 and not self.on_land(x, y, 90) and dist(x, y, self.sx, self.sy) > 450:
                    break
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=mh, max=mh, state='patrol', wp=(px, py), cool=0.0, is_boss=False, raider=True))

    def cv_event(self, ev):
        c = self.convoy
        k = ev['kind']
        if k == 'raid1':
            self.cv_spawn_raiders(2 if self.wave < 4 else 3)
            self.cv_say('ESCOLTA', '¡Cazadores enemigos al frente! Necesitamos apoyo.', (255, 200, 140))
        elif k == 'raid2':
            self.cv_spawn_raiders(2 if self.wave < 4 else 3, ahead=False, hp_mul=1.3)
            self.audio.play('alarm', .5)
            self.cv_say('ESCOLTA', '¡Emboscada junto al puerto! ¡Resistan!', (255, 160, 120))
        elif k in ('air', 'air2'):
            self.audio.play('alarm', .5)
            a = random.uniform(0, 6.28)
            for i in range(2 if self.wave < 5 else 3):
                px, py = c['x'] + math.cos(a) * 1300 + i * 70, c['y'] + math.sin(a) * 1300 + i * 50
                tx, ty = c['x'] + vec(c['h'], c['v'] * 3.0)[0], c['y'] + vec(c['h'], c['v'] * 3.0)[1]
                h = bearing(tx - px, ty - py)
                vx, vy = vec(h, 430)
                c['planes'].append(dict(x=px, y=py, h=h, vx=vx, vy=vy, bombs=3, cd=0.0, hp=2.5, life=7.0, flash=0.0, down=None))
            self.cv_say('ESCOLTA', '¡BOMBARDEROS! Acercate y usá F (antiaéreo).', (255, 200, 140))
        elif k == 'sub':
            side = random.choice((-1, 1))
            ox, oy = vec(c['h'] + 90 * side, 520)
            for i in range(2 if self.wave < 5 else 3):
                x, y = c['x'] + ox + random.uniform(-60, 60), c['y'] + oy + random.uniform(-60, 60)
                lead = 2.4
                tx, ty = c['x'] + vec(c['h'], c['v'] * lead)[0], c['y'] + vec(c['h'], c['v'] * lead)[1]
                h = bearing(tx - x, ty - y) + random.uniform(-3, 3)
                vx, vy = vec(h, 150)
                c['torps'].append(dict(x=x, y=y, vx=vx, vy=vy, t=0.5 * i, life=6.0, h=h))
            self.audio.play('alarm', .5)
            self.cv_say('SONAR', '¡TORPEDOS al agua! Interponete o que los escoltas los frenen.', (255, 190, 150))

    def cv_flak(self):
        """F: fuego antiaéreo del barco: destruye bombas, daña aviones y avisa si no hay convoy."""
        c = self.convoy
        if c is None:
            self.toast('No hay convoy al que cubrir', (255, 200, 120))
            return
        if c['flak_cd'] > 0:
            self.toast('Antiaéreo recargando: %d s' % math.ceil(c['flak_cd']), (255, 200, 120))
            return
        c['flak_cd'] = FLAK_CD
        c['flak_fx'] = [self.sx, self.sy, 0.0]
        self.audio.play('cannon', .5)
        self.audio.play('boom_s', .4)
        self.shake = max(self.shake, 4)
        hit = 0
        for b in c['bombs'][:]:
            if dist(b['x'], b['y'], self.sx, self.sy) < FLAK_R:
                c['bombs'].remove(b)
                self.fxm.add('glow', b['x'], b['y'], life=.4, r0=8, r1=36, col=(255, 230, 160))
                hit += 1
        for p in c['planes']:
            if p['down'] is None and dist(p['x'], p['y'], self.sx, self.sy) < FLAK_R + 80:
                p['hp'] -= 1.6
                p['flash'] = 0.3
                if p['hp'] <= 0:
                    self.cv_plane_down(p)
                hit += 1
        if hit:
            self.pop('¡ANTIAÉREO!', self.sx - self.cam[0], self.sy - self.cam[1] - 50, (255, 230, 140))

    def cv_plane_down(self, p):
        p['down'] = 0.0
        self.convoy['planes_down'] += 1
        self.add_score(150)
        self.audio.play('boom_s', .5)
        self.fxm.add('glow', p['x'], p['y'], life=.5, r0=12, r1=44, col=(255, 150, 60))
        self.cv_say('ESCOLTA', '¡Bombardero derribado!')

    # ------------------------------------------------------------------ bucle
    def upd_convoy(self, dt):
        c = self.convoy
        c['t'] += dt
        c['flak_cd'] = max(0.0, c['flak_cd'] - dt)
        c['hit_t'] = max(0.0, c['hit_t'] - dt)
        for q in c['calls']:
            q[3] -= dt
        c['calls'] = [q for q in c['calls'] if q[3] > 0]
        if c['flak_fx']:
            c['flak_fx'][2] += dt
            if c['flak_fx'][2] > 0.7:
                c['flak_fx'] = None
        dx, dy = c['dst']['dock']
        d = dist(c['x'], c['y'], dx, dy)
        c['f'] = clamp(1 - d / max(1.0, c['total']), 0.0, 1.0)
        for ev in c['events']:
            if not ev['done'] and c['f'] >= ev['f'] and c['state'] == 'sail':
                ev['done'] = True
                self.cv_event(ev)
        # rumbo y velocidad
        vx, vy = (dx - c['x']) / (d or 1.0), (dy - c['y']) / (d or 1.0)
        for ix, iy, ir, sd in self.islands:
            dd = dist(c['x'], c['y'], ix, iy) or 1.0
            is_dst = abs(ix - c['dst']['x']) < 1 and abs(iy - c['dst']['y']) < 1
            lim = coast_r(ir, sd, math.atan2(c['y'] - iy, c['x'] - ix), 1.0 if is_dst else 1.1) + (20 if is_dst else 120)   # al destino se acerca hasta tocar la costa
            if dd < lim:
                k = (lim - dd) / 120
                vx += (c['x'] - ix) / dd * k * 2.6
                vy += (c['y'] - iy) / dd * k * 2.6
        want = bearing(vx, vy)
        c['h'] = (c['h'] + clamp(angle_diff(c['h'], want), -30 * dt, 30 * dt)) % 360
        dcity = dist(c['x'], c['y'], c['dst']['x'], c['dst']['y'])
        dcoast = dcity - coast_r(c['dst']['r'], c['dst']['seed'], math.atan2(c['y'] - c['dst']['y'], c['x'] - c['dst']['x']), 1.0)
        slow = 1.0 if dcoast > 260 else clamp((dcoast - 10) / 250.0, 0.3, 1.0)
        goal_v = (70 * slow if c['t'] > 3 else 0) if c['state'] == 'sail' else 0.0
        c['v'] += (goal_v - c['v']) * min(1, dt * (1.2 if c['state'] == 'sail' else 7.0))
        mx, my = vec(c['h'], c['v'] * dt)
        c['x'] += mx
        c['y'] += my
        if random.random() < dt * 12 and c['v'] > 5:
            bx, by = vec(c['h'], -30)
            self.fxm.add('foam', c['x'] + bx, c['y'] + by, life=1.3, r0=4, r1=12, col=(230, 245, 255))
        # cazadores enemigos sobre el carguero
        atk = [en for en in self.enemies if en.get('raider') and dist(en['x'], en['y'], c['x'], c['y']) < 170]
        if atk:
            near = dist(self.sx, self.sy, c['x'], c['y']) < 230          # tu barco atrae el fuego
            self.cv_damage(6.0 * len(atk) * (0.65 if near else 1.0) * dt, glowfx=True)
            if int(c['t'] * 2) != int((c['t'] - dt) * 2):
                self.audio.play('hit', .25)
        self.cv_escorts(dt)
        self.cv_planes(dt)
        self.cv_torps(dt)
        self.cv_boxes(dt)
        if c['hp'] < 60 and random.random() < dt * 6:
            self.fxm.add('smoke', c['x'], c['y'], 0, -18, 1.8, 5, 18, (60, 60, 60))
        if c['hp'] < 30 and random.random() < dt * 5:
            self.fxm.add('glow', c['x'] + random.uniform(-8, 8), c['y'] + random.uniform(-20, 20), life=.35, r0=6, r1=16, col=(255, 130, 50))
        # llegada y descarga
        c['stuck'] = c.get('stuck', 0.0) + dt if (dcoast < 150 and c['v'] < 8) else 0.0
        if c['state'] == 'sail' and (d < 46 or dcoast < 34 or c['stuck'] > 1.5):   # llegada = tocar el puerto (la costa de la ciudad o el muelle)
            c['state'] = 'unload'
            self.audio.play('win', .6)
            self.shake = max(self.shake, 3)
            self.cv_say('CARGUERO', '¡Llegamos al puerto! Descargando...')
        if c['state'] == 'unload':
            self.cv_unload(dt)
        if c['hp'] <= 0:
            self.end_convoy(False)

    def cv_damage(self, dmg, glowfx=False):
        c = self.convoy
        c['hp'] -= dmg
        c['took'] += dmg
        c['hit_t'] = 0.25
        if glowfx and random.random() < 0.5:
            self.fxm.add('glow', c['x'] + random.uniform(-10, 10), c['y'] + random.uniform(-25, 25), life=.4, r0=6, r1=18, col=(255, 150, 60))

    def cv_escorts(self, dt):
        c = self.convoy
        for e in c['escorts']:
            if e['hp'] <= 0:
                continue
            ox, oy = vec(c['h'] + 90 * e['side'], 62)
            bx, by = vec(c['h'] + 180, 34)
            tx, ty = c['x'] + ox + bx, c['y'] + oy + by
            e['x'] += (tx - e['x']) * min(1, dt * 2.2)
            e['y'] += (ty - e['y']) * min(1, dt * 2.2)
            e['h'] = (e['h'] + clamp(angle_diff(e['h'], c['h']), -60 * dt, 60 * dt)) % 360
            e['flash'] = max(0.0, e['flash'] - dt)
            e['cd'] -= dt
            if e['cd'] <= 0:
                tgt = None
                best = 330.0
                for en in self.enemies:
                    if en.get('raider'):
                        dd = dist(e['x'], e['y'], en['x'], en['y'])
                        if dd < best:
                            tgt, best = en, dd
                if tgt is not None:
                    e['cd'] = 1.1
                    e['flash'] = 0.12
                    tgt['hp'] -= 1.0
                    c['shots'].append([e['x'], e['y'], tgt['x'], tgt['y'], 0.18])
                    if dist(e['x'], e['y'], self.sx, self.sy) < 700:
                        self.audio.play('mg', .15)
                    if tgt['hp'] <= 0 and tgt in self.enemies:
                        self.enemies.remove(tgt)
                        self.fxm.add('glow', tgt['x'], tgt['y'], life=.5, r0=10, r1=40, col=(255, 160, 70))
                        self.add_score(120)
                        self.cv_say('ESCOLTA', '¡Cazador hundido!')
                    continue
                for b in c['bombs']:                                      # antiaéreo de los escoltas
                    if dist(e['x'], e['y'], b['x'], b['y']) < 230 and random.random() < 0.45:
                        e['cd'] = 1.4
                        c['bombs'].remove(b)
                        self.fxm.add('glow', b['x'], b['y'], life=.35, r0=8, r1=30, col=(255, 230, 160))
                        break
                else:
                    for p in c['planes']:
                        if p['down'] is None and dist(e['x'], e['y'], p['x'], p['y']) < 360:
                            e['cd'] = 1.2
                            p['hp'] -= 0.35
                            p['flash'] = 0.15
                            c['shots'].append([e['x'], e['y'], p['x'], p['y'], 0.15])
                            if p['hp'] <= 0:
                                self.cv_plane_down(p)
                            break
        for s in c['shots']:
            s[4] -= dt
        c['shots'] = [s for s in c['shots'] if s[4] > 0]

    def cv_hit_escort(self, x, y, r, dmg):
        for e in self.convoy['escorts']:
            if e['hp'] > 0 and dist(x, y, e['x'], e['y']) < r:
                e['hp'] -= dmg
                if e['hp'] <= 0:
                    self.fxm.add('glow', e['x'], e['y'], life=.6, r0=14, r1=50, col=(255, 140, 60))
                    self.cv_say('ESCOLTA', '¡Perdimos una corbeta!', (255, 150, 120))

    def cv_planes(self, dt):
        c = self.convoy
        for p in c['planes'][:]:
            p['flash'] = max(0.0, p['flash'] - dt)
            if p['down'] is not None:
                p['down'] += dt
                p['x'] += p['vx'] * dt * 0.5
                p['y'] += p['vy'] * dt * 0.5
                if random.random() < dt * 20:
                    self.fxm.add('smoke', p['x'], p['y'], 0, 0, 1.2, 5, 16, (50, 50, 50))
                if p['down'] > 1.4:
                    c['planes'].remove(p)
                continue
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt
            p['cd'] -= dt
            if p['bombs'] > 0 and p['cd'] <= 0 and dist(p['x'], p['y'], c['x'], c['y']) < 150:
                p['bombs'] -= 1
                p['cd'] = 0.28
                T = 1.5
                tx, ty = c['x'] + vec(c['h'], c['v'] * T)[0] + random.uniform(-26, 26), c['y'] + vec(c['h'], c['v'] * T)[1] + random.uniform(-26, 26)
                c['bombs'].append(dict(x0=p['x'], y0=p['y'], x=p['x'], y=p['y'], tx=tx, ty=ty, t=0.0, T=T))
                self.audio.play('blip', .3)
            if p['life'] <= 0:
                c['planes'].remove(p)
        for b in c['bombs'][:]:
            b['t'] += dt
            k = clamp(b['t'] / b['T'], 0, 1)
            b['x'], b['y'] = b['x0'] + (b['tx'] - b['x0']) * k, b['y0'] + (b['ty'] - b['y0']) * k
            if b['t'] >= b['T']:
                c['bombs'].remove(b)
                self.fxm.add('glow', b['tx'], b['ty'], life=.5, r0=14, r1=60, col=(255, 190, 90))
                for _ in range(6):
                    self.fxm.add('foam', b['tx'] + random.uniform(-26, 26), b['ty'] + random.uniform(-26, 26), life=1.0, r0=6, r1=22, col=(235, 245, 255))
                self.audio.play('boom_s', .5)
                if dist(b['tx'], b['ty'], c['x'], c['y']) < 62:
                    self.cv_damage(12.0)
                    self.shake = max(self.shake, 5)
                    self.pop('-12', c['x'] - self.cam[0], c['y'] - self.cam[1] - 40, (255, 140, 110))
                self.cv_hit_escort(b['tx'], b['ty'], 55, 9.0)
                if dist(b['tx'], b['ty'], self.sx, self.sy) < 55:
                    self.hull = max(1.0, self.hull - 5)

    def cv_torps(self, dt):
        c = self.convoy
        for tp in c['torps'][:]:
            tp['t'] += dt
            if tp['t'] < 0:
                continue
            tp['x'] += tp['vx'] * dt
            tp['y'] += tp['vy'] * dt
            tp['life'] -= dt
            boom = None
            if dist(tp['x'], tp['y'], self.sx, self.sy) < 34 and tp['t'] > 0.4:
                boom = 'player'
            elif any(e['hp'] > 0 and dist(tp['x'], tp['y'], e['x'], e['y']) < 28 for e in c['escorts']):
                boom = 'escort'
            elif dist(tp['x'], tp['y'], c['x'], c['y']) < 30:
                boom = 'convoy'
            elif tp['life'] <= 0:
                c['torps'].remove(tp)
                continue
            if boom:
                c['torps'].remove(tp)
                self.fxm.add('glow', tp['x'], tp['y'], life=.6, r0=12, r1=56, col=(255, 200, 120))
                for _ in range(5):
                    self.fxm.add('foam', tp['x'] + random.uniform(-20, 20), tp['y'] + random.uniform(-20, 20), life=1.1, r0=6, r1=24, col=(235, 245, 255))
                self.audio.play('boom_s', .6)
                self.shake = max(self.shake, 6)
                if boom == 'player':
                    self.hull = max(1.0, self.hull - 6)
                    self.add_score(100)
                    self.pop('¡INTERCEPTASTE EL TORPEDO! +100', self.sx - self.cam[0], self.sy - self.cam[1] - 50, (255, 230, 140))
                elif boom == 'escort':
                    self.cv_hit_escort(tp['x'], tp['y'], 40, 12.0)
                else:
                    self.cv_damage(22.0)
                    self.pop('-22', c['x'] - self.cam[0], c['y'] - self.cam[1] - 40, (255, 140, 110))
                    self.cv_say('CARGUERO', '¡Nos dieron! Mantengan el rumbo.', (255, 170, 140))

    # ------------------------------------------------------------------ descarga y reabastecimiento
    def cv_boxes(self, dt):
        c = self.convoy
        for b in c['boxes'][:]:
            b['t'] += dt
            if b['t'] >= 0.9:
                c['boxes'].remove(b)

    def cv_unload(self, dt):
        c = self.convoy
        d = c['dst']
        c['unload'] += dt
        k = clamp(c['hp'] / 100.0, 0.25, 1.0)
        amt = 100.0 * dt / UNLOAD_T * k
        before = min(d['stock'].values())
        self.city_refill(d, amt)
        c['delivered'] += min(amt, max(0.0, self.city_cap(d) - before))
        if random.random() < dt * 9:
            a_ = math.atan2(c['y'] - d['y'], c['x'] - d['x'])
            cr_ = coast_r(d['r'], d['seed'], a_, 1.0)
            c['boxes'].append(dict(x0=c['x'], y0=c['y'], x1=d['x'] + math.cos(a_) * (cr_ - 10) + random.uniform(-20, 20),
                                   y1=d['y'] + math.sin(a_) * (cr_ - 10) + random.uniform(-20, 20),
                                   t=0.0, col=random.choice(((196, 84, 62), (70, 126, 196), (226, 184, 66), (80, 160, 120)))))
        if c['unload'] >= UNLOAD_T:
            self.end_convoy(True)

    def end_convoy(self, ok):
        c = self.convoy
        self.convoy = None
        self.convoy_t = random.uniform(75, 105)
        for en in self.enemies:
            en.pop('raider', None)
        d = c['dst']
        if ok:
            esc = sum(1 for e in c['escorts'] if e['hp'] > 0)
            pts = 600 + 150 * self.wave + 200 * esc + 150 * c['planes_down'] + (500 if c['took'] < 5 else 0)
            self.add_score(pts)
            d['hp'] = min(100.0, d['hp'] + 20)
            self.audio.play('win', .8)
            for i in range(14):                                              # fuegos artificiales sobre la ciudad
                a = random.uniform(0, 6.28)
                self.fxm.add('glow', d['x'] + math.cos(a) * random.uniform(20, 110), d['y'] + math.sin(a) * random.uniform(20, 90) - 40, life=random.uniform(.6, 1.4),
                             r0=10, r1=50, col=random.choice(((255, 220, 90), (120, 255, 190), (255, 130, 130), (140, 190, 255))))
            full = min(d['stock'].values()) >= self.city_cap(d) - 1
            self.banner('¡%s REABASTECIDA!' % d['name'], ('Reservas al %d%%  |  +%d de cada recurso  |  ' % (int(self.cv_need(d) * 100), int(c['delivered'])) +
                                                       'escoltas %d/2, bombarderos derribados %d  |  +%d puntos' % (esc, c['planes_down'], pts)),
                        (120, 255, 160), 4.4)
            if full:
                self.toast('Las reservas de %s están completas' % d['name'], (150, 255, 200))
        else:
            self.audio.play('boom_l')
            self.shake = 10
            self.ammo = max(0, self.ammo - 4)
            part = int(c['delivered'])
            self.banner('¡CONVOY HUNDIDO!', ('Alcanzó a descargar +%d en %s  |  ' % (part, d['name']) if part > 0 else '') + 'Sin suministros: -4 munición', (255, 90, 70), 3.6)

    # ------------------------------------------------------------------ dibujo
    def draw_convoy(self, cv, cx, cy, yy):
        c = self.convoy
        t = self.t
        sx, sy = c['x'] - cx, c['y'] - cy
        dkx, dky = c['dst']['dock'][0] - cx, c['dst']['dock'][1] - cy
        n = 18                                                                      # ruta punteada hacia el puerto
        for i in range(n):
            f0, f1 = (i + (t * 0.8) % 1) / n, (i + 0.5 + (t * 0.8) % 1) / n
            if f1 <= 1:
                pygame.draw.line(cv, (120, 255, 190), (sx + (dkx - sx) * f0, sy + (dky - sy) * f0), (sx + (dkx - sx) * f1, sy + (dky - sy) * f1), 2)
        if -200 < dkx < W + 200 and -200 < dky < H + 200:
            pul = 0.5 + 0.5 * math.sin(t * 4)
            draw_circ(cv, dkx, dky, 56 + 3 * pul, (120, 255, 190), 70, 3)
            self.text(cv, 'REABASTECIMIENTO', self.f_s, (150, 255, 210), dkx, dky - 100, 'c')
        for e in c['escorts']:
            if e['hp'] > 0 and -100 < e['x'] - cx < W + 100 and -100 < e['y'] - cy < H + 100:
                self.blit_ship(cv, 'esc_map', e['x'], e['y'], e['h'], cx, cy)
                if e['flash'] > 0:
                    glow(cv, e['x'] - cx, e['y'] - cy, 22, (255, 220, 140), 0.8)
                if e['hp'] < e['max']:
                    pygame.draw.rect(cv, (8, 12, 24), (e['x'] - cx - 14, e['y'] - cy - 30, 28, 5))
                    pygame.draw.rect(cv, (110, 220, 150), (e['x'] - cx - 13, e['y'] - cy - 29, int(26 * e['hp'] / e['max']), 3))
        for s in c['shots']:
            pygame.draw.line(cv, (255, 235, 150), (s[0] - cx, s[1] - cy), (s[2] - cx, s[3] - cy), 2)
        if -100 < sx < W + 100 and -100 < sy < H + 100:
            self.blit_ship(cv, 'c_map', c['x'], c['y'], c['h'], cx, cy)
            draw_circ(cv, sx, sy, 38, (255, 120, 90) if c['hit_t'] > 0 else (120, 255, 190), 90 if c['hit_t'] > 0 else 70, 2)
            pygame.draw.rect(cv, (8, 12, 24), (sx - 24, sy - 52, 48, 7))
            col = (80, 230, 110) if c['hp'] > 50 else ((255, 200, 70) if c['hp'] > 25 else (240, 80, 70))
            pygame.draw.rect(cv, col, (sx - 23, sy - 51, int(46 * clamp(c['hp'], 0, 100) / 100), 5))
        for b in c['boxes']:
            k = b['t'] / 0.9
            x, y = (b['x0'] + (b['x1'] - b['x0']) * k) - cx, (b['y0'] + (b['y1'] - b['y0']) * k) - cy - math.sin(math.pi * k) * 46
            pygame.draw.rect(cv, b['col'], (x - 4, y - 4, 9, 9))
            pygame.draw.rect(cv, (30, 34, 36), (x - 4, y - 4, 9, 9), 1)
        for tp in c['torps']:
            if tp['t'] < 0:
                continue
            ex, ey = tp['x'] - cx, tp['y'] - cy
            bx, by = vec(tp['h'] + 180, 90)
            pygame.draw.line(cv, (230, 245, 255), (ex, ey), (ex + bx, ey + by), 2)
            pygame.draw.circle(cv, (255, 90, 70), (int(ex), int(ey)), 5)
            glow(cv, ex, ey, 18, (255, 120, 90), 0.6)
        for b in c['bombs']:
            k = b['t'] / b['T']
            tx, ty = b['tx'] - cx, b['ty'] - cy
            draw_circ(cv, tx, ty, 62 * (1 - 0.5 * k) + 6, (255, 80, 60), 160, 2)
            draw_circ(cv, tx, ty, 62, (255, 80, 60), 24)
            pygame.draw.circle(cv, (40, 40, 44), (int(b['x'] - cx), int(b['y'] - cy - (1 - k) * 70)), 5)
        for p in c['planes']:
            if not (-100 < p['x'] - cx < W + 100 and -100 < p['y'] - cy < H + 100):
                continue
            a = math.radians(p['h'])
            ca, sa = math.cos(a), math.sin(a)
            px, py = p['x'] - cx, p['y'] - cy
            draw_circ(cv, px + 12, py + 16, 22, (0, 0, 0), 50)
            pts = [(px + lx * ca - ly * sa, py + lx * sa + ly * ca) for lx, ly in PLANE_SHAPE]
            pygame.draw.polygon(cv, (210, 214, 220) if p['flash'] > 0 else (92, 100, 112), pts)
            pygame.draw.polygon(cv, (30, 34, 40), pts, 2)
            if p['down'] is not None:
                glow(cv, px, py, 30, (255, 140, 50), 0.8)
        if c['flak_fx']:
            fx_ = c['flak_fx']
            k = fx_[2] / 0.7
            draw_circ(cv, fx_[0] - cx, fx_[1] - cy, FLAK_R * k, (255, 230, 150), 160 * (1 - k), 3)
            for i in range(10):
                a = i * 0.628 + fx_[2] * 3
                glow(cv, fx_[0] - cx + math.cos(a) * FLAK_R * k, fx_[1] - cy + math.sin(a) * FLAK_R * k, 16, (255, 220, 140), 1 - k)
        # panel (columna derecha, bajo la amenaza enemiga)
        px, yy = W - 244, 158
        self.panel(cv, (px - 230, yy, 460, 88), 190)
        alive = sum(1 for e in c['escorts'] if e['hp'] > 0)
        self.text(cv, 'CONVOY a %s  |  casco %d%%  |  escoltas %d/2' % (c['dst']['name'], max(0, c['hp']), alive), self.f_s,
                  (150, 255, 200) if c['hp'] > 40 else (255, 120, 100), px, yy + 6, 'c')
        bx0, bw = px - 205, 410
        pygame.draw.rect(cv, (8, 12, 24), (bx0, yy + 30, bw, 12), border_radius=4)
        pygame.draw.rect(cv, (120, 255, 190), (bx0 + 1, yy + 31, int((bw - 2) * c['f']), 10), border_radius=4)
        for ev in c['events']:
            x = bx0 + bw * ev['f']
            col = (120, 120, 120) if ev['done'] else ((255, 120, 90) if ev['kind'] in ('raid1', 'raid2') else ((255, 220, 100) if ev['kind'] in ('air', 'air2') else (150, 190, 255)))
            pygame.draw.polygon(cv, col, [(x, yy + 26), (x + 5, yy + 36), (x, yy + 46), (x - 5, yy + 36)])
        left = dist(c['x'], c['y'], c['dst']['dock'][0], c['dst']['dock'][1])
        if c['state'] == 'unload':
            self.text(cv, 'DESCARGANDO %d%%  |  +%d de cada recurso' % (int(100 * c['unload'] / UNLOAD_T), int(c['delivered'])), self.f_s, (150, 255, 200), px, yy + 50, 'c')
        else:
            self.text(cv, 'Faltan %d m  |  cazadores: %d' % (left, sum(1 for en in self.enemies if en.get('raider'))), self.f_s, (200, 220, 240), px, yy + 50, 'c')
        ready = c['flak_cd'] <= 0
        self.text(cv, 'F: ANTIAÉREO %s' % ('LISTO' if ready else '%d s' % math.ceil(c['flak_cd'])), self.f_s, (255, 230, 140) if ready else (160, 160, 170), px, yy + 68, 'c')
        for i, (who, txt, col, life) in enumerate(c['calls']):
            a = int(255 * clamp(life * 2, 0, 1))
            self.text(cv, who + ': ' + txt, self.f_s, col, px, yy + 96 + i * 20, 'c', alpha=a)
        self.draw_pointer(cv, cx, cy, c['x'], c['y'], 'CONVOY', (120, 255, 190), 0.5 + 0.5 * math.sin(t * 5))
