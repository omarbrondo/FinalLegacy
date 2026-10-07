"""Incursión de cazas enemigos sobre el barco: pasadas de bombardeo que se esquivan moviéndose y se derriban con el antiaéreo (F)."""
import math
import pygame
import random
from .common import H, W, bearing, clamp, dist, draw_circ, glow, vec
from .convoy import FLAK_CD, FLAK_R, PLANE_SHAPE

RAID_BOMB_DMG = 5.0          # casco que resta cada bomba que cae sobre el barco (castigo moderado)
RAID_PTS = 150               # puntos por caza derribado
RAID_BONUS = 300             # bonus si los derribás a todos


class AirRaidMixin:
    def raid_reset_timer(self):
        self.raid_t = max(50.0, random.uniform(70, 100) - 3 * self.wave) * self.wprof()['raid']

    def begin_raid(self):
        n = 2 if self.wave < 4 else (3 if self.wave < 6 else 4)
        a = random.uniform(0, 6.28)
        planes = []
        for i in range(n):
            px, py = self.sx + math.cos(a) * 1300 + i * 80, self.sy + math.sin(a) * 1300 + i * 60
            planes.append(self.raid_plane(px, py))
        self.raid = dict(planes=planes, bombs=[], flak_cd=0.0, flak_fx=None, total=n, down=0, hits=0, t=0.0)
        self.audio.play('alarm')
        self.banner('¡CAZAS ENEMIGOS!', 'Esquivá las bombas moviéndote y derribalos con F (antiaéreo)', (255, 190, 90), 4.0)

    def raid_plane(self, px, py):
        h = bearing(self.sx - px, self.sy - py)
        vx, vy = vec(h, 430)
        return dict(x=px, y=py, h=h, vx=vx, vy=vy, bombs=3, cd=0.0, hp=1.5, life=22.0, flash=0.0, down=None, passes=1, away=False)

    def raid_flak(self):
        r = self.raid
        if r is None:
            self.toast('No hay convoy ni cazas a los que disparar', (255, 200, 120))
            return
        if r['flak_cd'] > 0:
            self.toast('Antiaéreo recargando: %d s' % math.ceil(r['flak_cd']), (255, 200, 120))
            return
        r['flak_cd'] = FLAK_CD
        r['flak_fx'] = [self.sx, self.sy, 0.0]
        self.audio.play('cannon', .5)
        self.audio.play('boom_s', .4)
        self.shake = max(self.shake, 4)
        hit = 0
        for b in r['bombs'][:]:
            if dist(b['x'], b['y'], self.sx, self.sy) < FLAK_R:
                r['bombs'].remove(b)
                self.fxm.add('glow', b['x'], b['y'], life=.4, r0=8, r1=36, col=(255, 230, 160))
                hit += 1
        for p in r['planes']:
            if p['down'] is None and dist(p['x'], p['y'], self.sx, self.sy) < FLAK_R + 80:
                p['hp'] -= 1.6
                p['flash'] = 0.3
                if p['hp'] <= 0:
                    p['down'] = 0.0
                    r['down'] += 1
                    self.add_score(RAID_PTS)
                    self.audio.play('boom_s', .5)
                    self.fxm.add('glow', p['x'], p['y'], life=.5, r0=12, r1=44, col=(255, 150, 60))
                    self.pop('+%d' % RAID_PTS, p['x'] - self.cam[0], p['y'] - self.cam[1] - 30, (255, 230, 140))
                hit += 1
        if hit:
            self.pop('¡ANTIAÉREO!', self.sx - self.cam[0], self.sy - self.cam[1] - 50, (255, 230, 140))

    def upd_raid(self, dt):
        r = self.raid
        r['t'] += dt
        r['flak_cd'] = max(0.0, r['flak_cd'] - dt)
        if r['flak_fx']:
            r['flak_fx'][2] += dt
            if r['flak_fx'][2] > 0.7:
                r['flak_fx'] = None
        for p in r['planes'][:]:
            p['flash'] = max(0.0, p['flash'] - dt)
            if p['down'] is not None:
                p['down'] += dt
                p['x'] += p['vx'] * dt * 0.5
                p['y'] += p['vy'] * dt * 0.5
                if random.random() < dt * 20:
                    self.fxm.add('smoke', p['x'], p['y'], 0, 0, 1.2, 5, 16, (50, 50, 50))
                if p['down'] > 1.4:
                    r['planes'].remove(p)
                continue
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt
            p['cd'] -= dt
            d = dist(p['x'], p['y'], self.sx, self.sy)
            if p['bombs'] > 0 and p['cd'] <= 0 and d < 150:
                p['bombs'] -= 1
                p['cd'] = 0.28
                T = 1.5
                lx, ly = vec(self.sh, self.sv * T)
                tx, ty = self.sx + lx + random.uniform(-26, 26), self.sy + ly + random.uniform(-26, 26)
                r['bombs'].append(dict(x0=p['x'], y0=p['y'], x=p['x'], y=p['y'], tx=tx, ty=ty, t=0.0, T=T))
                self.audio.play('blip', .3)
            if d > 700 and not p['away'] and p['bombs'] <= 0:         # terminó la pasada: se aleja y vuelve una vez más
                p['away'] = True
            if p['away'] and d > 900:
                if p['passes'] < 2 and p['life'] > 6:
                    fresh = self.raid_plane(p['x'], p['y'])
                    p.update(h=fresh['h'], vx=fresh['vx'], vy=fresh['vy'], bombs=2, passes=2, away=False)
                else:
                    r['planes'].remove(p)
                    continue
            if p['life'] <= 0:
                r['planes'].remove(p)
        for b in r['bombs'][:]:
            b['t'] += dt
            k = clamp(b['t'] / b['T'], 0, 1)
            b['x'], b['y'] = b['x0'] + (b['tx'] - b['x0']) * k, b['y0'] + (b['ty'] - b['y0']) * k
            if b['t'] >= b['T']:
                r['bombs'].remove(b)
                self.fxm.add('glow', b['tx'], b['ty'], life=.5, r0=14, r1=60, col=(255, 190, 90))
                for _ in range(6):
                    self.fxm.add('foam', b['tx'] + random.uniform(-26, 26), b['ty'] + random.uniform(-26, 26), life=1.0, r0=6, r1=22, col=(235, 245, 255))
                self.audio.play('boom_s', .5)
                if dist(b['tx'], b['ty'], self.sx, self.sy) < 62:
                    r['hits'] += 1
                    self.hull = max(1.0, self.hull - RAID_BOMB_DMG)
                    self.shake = max(self.shake, 6)
                    self.pop('-%d' % RAID_BOMB_DMG, self.sx - self.cam[0], self.sy - self.cam[1] - 40, (255, 140, 110))
        if not r['planes'] and not r['bombs']:
            self.raid_end()

    def raid_end(self):
        r = self.raid
        self.raid = None
        self.raid_reset_timer()
        if r['down'] >= r['total']:
            self.add_score(RAID_BONUS)
            self.banner('¡CAZAS DERRIBADOS!', 'Los %d cazas cayeron  |  Bonus +%d' % (r['total'], RAID_BONUS), (120, 255, 160), 3.4)
        elif r['down']:
            self.toast('Los cazas se retiraron: derribaste %d de %d' % (r['down'], r['total']), (255, 220, 130))
        else:
            self.toast('Los cazas se retiraron sin que derribaras ninguno', (255, 190, 120))

    def draw_raid(self, cv, cx, cy):
        r = self.raid
        t = self.t
        for b in r['bombs']:
            k = b['t'] / b['T']
            tx, ty = b['tx'] - cx, b['ty'] - cy
            draw_circ(cv, tx, ty, 62 * (1 - 0.5 * k) + 6, (255, 80, 60), 160, 2)
            draw_circ(cv, tx, ty, 62, (255, 80, 60), 24)
            pygame.draw.circle(cv, (40, 40, 44), (int(b['x'] - cx), int(b['y'] - cy - (1 - k) * 70)), 5)
        for p in r['planes']:
            px, py = p['x'] - cx, p['y'] - cy
            if not (-100 < px < W + 100 and -100 < py < H + 100):
                if p['down'] is None:
                    self.draw_pointer(cv, cx, cy, p['x'], p['y'], 'CAZA', (255, 190, 90), 0.5 + 0.5 * math.sin(t * 8))
                continue
            a = math.radians(p['h'])
            ca, sa = math.cos(a), math.sin(a)
            draw_circ(cv, px + 12, py + 16, 22, (0, 0, 0), 50)
            pts = [(px + lx * ca - ly * sa, py + lx * sa + ly * ca) for lx, ly in PLANE_SHAPE]
            pygame.draw.polygon(cv, (210, 214, 220) if p['flash'] > 0 else (92, 100, 112), pts)
            pygame.draw.polygon(cv, (30, 34, 40), pts, 2)
            if p['down'] is not None:
                glow(cv, px, py, 30, (255, 140, 50), 0.8)
        if r['flak_fx']:
            fx_ = r['flak_fx']
            k = fx_[2] / 0.7
            draw_circ(cv, fx_[0] - cx, fx_[1] - cy, FLAK_R * k, (255, 230, 150), 160 * (1 - k), 3)
            for i in range(10):
                a = i * 0.628 + fx_[2] * 3
                glow(cv, fx_[0] - cx + math.cos(a) * FLAK_R * k, fx_[1] - cy + math.sin(a) * FLAK_R * k, 16, (255, 220, 140), 1 - k)
        px, yy = W - 244, 158
        self.panel(cv, (px - 230, yy, 460, 54), 190)
        left = sum(1 for p in r['planes'] if p['down'] is None)
        self.text(cv, 'CAZAS ENEMIGOS: %d  |  caídos %d/%d' % (left, r['down'], r['total']), self.f_s, (255, 200, 120), px, yy + 6, 'c')
        rdy = 1 - clamp(r['flak_cd'] / FLAK_CD, 0, 1)
        pygame.draw.rect(cv, (8, 12, 24), (px - 205, yy + 32, 410, 12), border_radius=4)
        pygame.draw.rect(cv, (120, 255, 160) if rdy >= 1 else (255, 200, 80), (px - 204, yy + 33, int(408 * rdy), 10), border_radius=4)
