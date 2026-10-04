"""Peligros y apoyo en infantería y puerto: nubes tóxicas (con máscara antigás) y ataques de misil Tomahawk."""
import math
import pygame
import random
from .common import H, W, clamp, dist, draw_circ, glow

GAS_FROM_WAVE = 3
TOM_DELAY = 1.7


class HazardMixin:
    # ------------------------------------------------------------ comunes
    def hz_state(self, store):
        st = store.get('hz')
        if st is None:
            st = store['hz'] = dict(gas=[], shells=[], strikes=[], t=random.uniform(9, 14), mask=0.0, tom=self.up_n('tomahawk'),
                                    tcd=0.0, cough=0.0)
        return st

    def tomahawk(self):
        """T / LB: pide un ataque de misil Tomahawk sobre el punto apuntado (infantería y puerto)."""
        if self.state == 'ground' and not self.g['stealth']:
            st = self.hz_state(self.g)
            tx, ty = self.ground_aim()
        elif self.state == 'port':
            st = self.hz_state(self.pt)
            tx, ty = self.aim[0] + self.pt['cam'], self.PT_GR
        else:
            return
        if self.up_n('tomahawk') <= 0:
            self.toast('Sin Tomahawk: elegilo como mejora entre oleadas', (255, 200, 120))
        elif st['tom'] <= 0:
            self.toast('Sin misiles Tomahawk en esta misión', (255, 150, 110))
        elif st['tcd'] > 0:
            self.toast('Tomahawk recargando: %d s' % math.ceil(st['tcd']), (255, 200, 120))
        else:
            st['tom'] -= 1
            st['tcd'] = 4.0
            st['strikes'].append(dict(x=tx, y=ty, t=0.0))
            self.audio.play('launch', .8)
            self.audio.play('ping', .6)
            (self.gpop if self.state == 'ground' else self.pop)('¡TOMAHAWK EN CAMINO!', *( (tx, ty - 30) if self.state == 'ground' else (self.aim[0], 300) ), (255, 200, 90))

    # ------------------------------------------------------------ INFANTERÍA
    def ground_hazards(self, dt, alive):
        g = self.g
        if g['mode'] != 'invasion':
            return
        p = g['p']
        st = self.hz_state(g)
        st['mask'] = max(0.0, st['mask'] - dt)
        st['tcd'] = max(0.0, st['tcd'] - dt)
        st['cough'] = max(0.0, st['cough'] - dt)
        if self.wave >= GAS_FROM_WAVE and g['phase'] == 'play':
            st['t'] -= dt
            if st['t'] <= 0:
                st['t'] = random.uniform(15, 22)
                for _ in range(20):
                    a, r = random.uniform(0, 6.28), random.uniform(90, 250)
                    x, y = p['x'] + math.cos(a) * r, p['y'] + math.sin(a) * r
                    if dist(x, y, W / 2, H / 2) < g['R'] * 0.85:
                        break
                st['shells'].append(dict(x=x, y=y, t=0.0))
                self.audio.play('alarm', .4)
                self.toast('¡ALERTA QUÍMICA!', (150, 255, 90))
        for s in st['shells'][:]:
            s['t'] += dt
            if s['t'] >= 1.5:
                st['shells'].remove(s)
                st['gas'].append(dict(x=s['x'], y=s['y'], r=100.0, age=0.0, life=13.0))
                self.audio.play('boom_s', .5)
                self.fx.add('glow', s['x'], s['y'], life=.3, r0=20, r1=70, col=(170, 255, 90))
                for _ in range(20):
                    a, r = random.uniform(0, 6.28), random.uniform(150, 230)
                    qx, qy = p['x'] + math.cos(a) * r, p['y'] + math.sin(a) * r
                    if dist(qx, qy, s['x'], s['y']) > 130 and dist(qx, qy, W / 2, H / 2) < g['R'] * 0.9:
                        g['crates'].append(dict(x=qx, y=qy, t=0.0, kind='mask'))
                        break
        for c in st['gas'][:]:
            c['age'] += dt
            if c['age'] > c['life']:
                st['gas'].remove(c)
                continue
            if alive and st['mask'] <= 0 and dist(c['x'], c['y'], p['x'], p['y']) < c['r']:
                p['hp'] -= 5.0 * dt
                g['hurt'] = max(g['hurt'], 0.2)
                if st['cough'] <= 0:
                    st['cough'] = 0.8
                    self.gpop('-GAS', p['x'], p['y'] - 26, (170, 255, 90))
            for e in g['enemies'][:]:
                if dist(c['x'], c['y'], e['x'], e['y']) < c['r']:
                    e['hp'] -= 2.5 * dt
                    if e['hp'] <= 0:
                        self.kill_ground_enemy(e)
        for s in st['strikes'][:]:
            s['t'] += dt
            if s['t'] >= TOM_DELAY:
                st['strikes'].remove(s)
                self.ground_tomahawk_hit(s)

    def ground_tomahawk_hit(self, s):
        g = self.g
        p = g['p']
        R = 150 * self.up_blast()
        x, y = s['x'], s['y']
        self.fx.explode(x, y, 2.4, True)
        self.fx.add('glow', x, y, life=.5, r0=R * 0.3, r1=R * 1.1, col=(255, 210, 130))
        self.audio.play('boom_l')
        self.shake = max(self.shake, 16)
        g['decals'].append((x, y, R * 0.5))
        g['decals'] = g['decals'][-40:]
        for e in g['enemies'][:]:
            d = dist(x, y, e['x'], e['y'])
            if d < R:
                e['hp'] -= 14 * self.up_dmg() * (1 - 0.4 * d / R)
                e['hit'] = 0.2
                if e['state'] in ('hold', 'susp'):
                    self.alert(e)
                if e['hp'] <= 0:
                    self.kill_ground_enemy(e)
        if not p['dead'] and dist(x, y, p['x'], p['y']) < R * 0.6:
            self.hurt_player(16)

    def ground_hazards_draw(self, cv, cx_, cy_):
        st = self.g.get('hz')
        if not st:
            return
        t = self.t
        for c in st['gas']:
            k = 1.0
            if c['age'] > c['life'] - 3:
                k = max(0.0, (c['life'] - c['age']) / 3)
            sx, sy = c['x'] - cx_, c['y'] - cy_
            for i in range(7):
                a = t * 0.6 + i * 0.9
                ox, oy = math.cos(a) * c['r'] * 0.45, math.sin(a * 1.3) * c['r'] * 0.45
                draw_circ(cv, sx + ox, sy + oy, c['r'] * (0.55 + 0.08 * math.sin(t * 2 + i)), (120, 220, 60), 46 * k)
            draw_circ(cv, sx, sy, c['r'], (150, 255, 90), 80 * k, 2)
        for s in st['shells']:
            sx, sy = s['x'] - cx_, s['y'] - cy_
            pulse = 0.5 + 0.5 * math.sin(t * 14)
            draw_circ(cv, sx, sy, 100, (170, 255, 90), 90 * pulse, 2)
            yy = sy - 300 * (1 - s['t'] / 1.5)
            pygame.draw.line(cv, (200, 255, 120), (sx, yy - 22), (sx, yy), 4)
        for s in st['strikes']:
            sx, sy = s['x'] - cx_, s['y'] - cy_
            k = s['t'] / TOM_DELAY
            r = 150 * self.up_blast()
            draw_circ(cv, sx, sy, r, (255, 90, 70), 30 + 40 * (0.5 + 0.5 * math.sin(t * 16)), 2)
            pygame.draw.line(cv, (255, 90, 70), (sx - 14, sy), (sx + 14, sy), 2)
            pygame.draw.line(cv, (255, 90, 70), (sx, sy - 14), (sx, sy + 14), 2)
            if k > 0.45:
                yy = sy - 700 * (1 - (k - 0.45) / 0.55)
                pygame.draw.line(cv, (255, 235, 200), (sx, yy - 40), (sx, yy), 5)
                glow(cv, sx, yy, 24, (255, 180, 90))

    def ground_hazards_hud(self, cv):
        st = self.g.get('hz')
        p = self.g['p']
        y = H - 126 - 22
        if st and st['mask'] > 0:
            self.text(cv, 'MÁSCARA %.0fs' % st['mask'], self.f_s, (170, 255, 120), 26, y)
            y -= 22
        n = self.up_n('tomahawk')
        if n and not self.g['stealth']:
            left = st['tom'] if st else n
            col = (255, 200, 90) if left > 0 else (150, 150, 150)
            self.text(cv, 'TOMAHAWK x%d  [T]' % left, self.f_s, col, 26, y)
        if st:
            for c in st['gas']:
                if dist(c['x'], c['y'], p['x'], p['y']) < c['r'] and st['mask'] <= 0:
                    vg = pygame.Surface((W, H), pygame.SRCALPHA)
                    vg.fill((90, 200, 40, 36))
                    cv.blit(vg, (0, 0))
                    break

    # ------------------------------------------------------------ PUERTO
    def port_hazards(self, dt, alive):
        pt = self.pt
        p = pt['p']
        st = self.hz_state(pt)
        GR = self.PT_GR
        st['mask'] = max(0.0, st['mask'] - dt)
        st['tcd'] = max(0.0, st['tcd'] - dt)
        st['cough'] = max(0.0, st['cough'] - dt)
        if self.wave >= GAS_FROM_WAVE and pt['phase'] == 'play' and pt['lock'] is None:
            st['t'] -= dt
            if st['t'] <= 0:
                st['t'] = random.uniform(16, 24)
                x = clamp(p['x'] + random.uniform(180, 420), pt['cam'] + 200, pt['cam'] + W - 120)
                st['shells'].append(dict(x=x, t=0.0))
                self.audio.play('alarm', .4)
                self.toast('¡ALERTA QUÍMICA!', (150, 255, 90))
        for s in st['shells'][:]:
            s['t'] += dt
            if s['t'] >= 1.5:
                st['shells'].remove(s)
                st['gas'].append(dict(x=s['x'], r=135.0, age=0.0, life=12.0))
                self.audio.play('boom_s', .5)
                pt['items'].append(dict(x=clamp(p['x'] - random.choice((-1, 1)) * random.uniform(160, 300), 120, self.PT_LEN - 200),
                                        y=float(GR - 30), kind='mask', t=0.0))
        for c in st['gas'][:]:
            c['age'] += dt
            if c['age'] > c['life']:
                st['gas'].remove(c)
                continue
            if alive and st['mask'] <= 0 and abs(p['x'] - c['x']) < c['r'] and p['y'] > GR - 70:
                p['hp'] -= 5.0 * dt
                pt['hurt'] = max(pt['hurt'], 0.15)
                if st['cough'] <= 0:
                    st['cough'] = 0.8
                    self.pop('-GAS', p['x'] - pt['cam'], p['y'] - 90, (170, 255, 90))
            for e in pt['enemies'][:]:
                if e['kind'] not in ('tank', 'turret') and abs(e['x'] - c['x']) < c['r'] and e['y'] > GR - 70:
                    self.pt_hit_enemy(e, 2.5 * dt, True)
        for s in st['strikes'][:]:
            s['t'] += dt
            if s['t'] >= TOM_DELAY:
                st['strikes'].remove(s)
                self.pt_blast(s['x'], GR - 4, 170 * self.up_blast(), 14 * self.up_dmg(), 16, 'p')
                self.fx.add('glow', s['x'], GR - 40, life=.5, r0=60, r1=200, col=(255, 210, 130))
                self.shake = max(self.shake, 16)
                self.audio.play('boom_l')

    def port_hazards_draw(self, cv, cam):
        st = self.pt.get('hz')
        if not st:
            return
        t = self.t
        GR = self.PT_GR
        for c in st['gas']:
            k = 1.0 if c['age'] < c['life'] - 3 else max(0.0, (c['life'] - c['age']) / 3)
            sx = c['x'] - cam
            if not (-250 < sx < W + 250):
                continue
            for i in range(6):
                ox = math.sin(t * 0.8 + i * 1.7) * c['r'] * 0.6
                oy = math.cos(t * 1.1 + i) * 14
                draw_circ(cv, sx + ox, GR - 40 + oy, 70 + 10 * math.sin(t * 2 + i), (120, 220, 60), 44 * k)
            draw_circ(cv, sx, GR - 36, c['r'], (150, 255, 90), 36 * k, 2)
        for s in st['shells']:
            sx = s['x'] - cam
            pulse = 0.5 + 0.5 * math.sin(t * 14)
            draw_circ(cv, sx, GR - 10, 130, (170, 255, 90), 90 * pulse, 2)
            yy = GR - 20 - 520 * (1 - s['t'] / 1.5)
            pygame.draw.line(cv, (200, 255, 120), (sx, yy - 22), (sx, yy), 4)
        for s in st['strikes']:
            sx = s['x'] - cam
            k = s['t'] / TOM_DELAY
            r = 170 * self.up_blast()
            draw_circ(cv, sx, GR - 4, r, (255, 90, 70), 26 + 34 * (0.5 + 0.5 * math.sin(t * 16)), 2)
            pygame.draw.line(cv, (255, 90, 70), (sx, GR - 4), (sx, GR - 120), 2)
            if k > 0.4:
                yy = (GR - 4) - 800 * (1 - (k - 0.4) / 0.6)
                pygame.draw.line(cv, (255, 235, 200), (sx, yy - 44), (sx, yy), 6)
                glow(cv, sx, yy, 26, (255, 180, 90))

    def port_hazards_hud(self, cv):
        st = self.pt.get('hz')
        p = self.pt['p']
        y = H - 34 - 24
        if st and st['mask'] > 0:
            self.text(cv, 'MÁSCARA %.0fs' % st['mask'], self.f_s, (170, 255, 120), W - 24, y, 'r')
            y -= 22
        n = self.up_n('tomahawk')
        if n:
            left = st['tom'] if st else n
            self.text(cv, 'TOMAHAWK x%d  [T]' % left, self.f_s, (255, 200, 90) if left > 0 else (150, 150, 150), W - 24, y, 'r')
        if st and st['mask'] <= 0:
            for c in st['gas']:
                if abs(p['x'] - c['x']) < c['r'] and p['y'] > self.PT_GR - 70:
                    vg = pygame.Surface((W, H), pygame.SRCALPHA)
                    vg.fill((90, 200, 40, 36))
                    cv.blit(vg, (0, 0))
                    break
