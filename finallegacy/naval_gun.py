"""Ametralladora automática del barco: apunta y dispara sola a aviones, cazas, escoltas, minas y al enemigo si está cerca.
Hace poco daño (apoya a los misiles) y se recalienta: tras una ráfaga larga se traba unos segundos."""
import pygame
import random
from .common import H, W, angle_diff, bearing, clamp, dist, glow, vec

MG_RANGE = 380
MG_RATE = 0.085
MG_HEAT = 0.035
MG_JAM = 2.6
AFT = -36.0                    # torreta de popa (la ametralladora): distancia al centro del casco, hacia atrás


class NavalGunMixin:
    def ng_init(self):
        self.c['mg'] = dict(heat=0.0, jam=0.0, cd=0.0, ang=0.0, flash=0.0, bullets=[], shots=0, on=False)

    # ------------------------------------------------------------------ objetivos
    def ng_target(self):
        c = self.c
        p, e = c['p'], c['e']
        best = None

        def consider(pri, x, y):
            nonlocal best
            d = dist(p['x'], p['y'], x, y)
            if d < MG_RANGE and (best is None or (pri, d) < best[:2]):
                best = (pri, d, x, y)
        for j in c['jets']:
            consider(0, j['x'], j['y'])
        for pl in c['planes']:
            consider(0, pl['x'], pl['y'])
        for b in c['boats']:
            consider(1, b['x'], b['y'])
        if e['sink'] is None and not (c['sub'] and not e['surf']):
            consider(2, e['x'], e['y'])
        if self.nb_alive():
            consider(2, c['bat']['x'], c['bat']['y'])
        for m in c['mines']:
            consider(3, m['x'], m['y'])
        return best

    # ------------------------------------------------------------------ actualización
    def ng_update(self, dt):
        c = self.c
        mg = c['mg']
        p = c['p']
        mg['flash'] = max(0.0, mg['flash'] - dt)
        if p['sink'] is not None:
            mg['on'] = False
            return
        mg['cd'] -= dt
        if mg['jam'] > 0:
            mg['jam'] -= dt
            if mg['jam'] <= 0:
                mg['heat'] = 0.5
        tgt = self.ng_target() if mg['jam'] <= 0 else None
        mg['on'] = tgt is not None
        ax_, ay_ = vec(p['h'], AFT)
        tx0, ty0 = p['x'] + ax_, p['y'] + ay_
        if tgt is None:                                   # sin blanco la torreta de popa vuelve a mirar al frente
            mg['ang'] = (mg['ang'] + clamp(angle_diff(mg['ang'], p['h']), -240 * dt, 240 * dt)) % 360
        if tgt is not None:
            want = bearing(tgt[2] - tx0, tgt[3] - ty0)
            mg['ang'] = (mg['ang'] + clamp(angle_diff(mg['ang'], want), -520 * dt, 520 * dt)) % 360
            if abs(angle_diff(mg['ang'], want)) < 12 and mg['cd'] <= 0:
                mg['cd'] = MG_RATE
                mg['shots'] += 1
                a = mg['ang'] + random.uniform(-3.0, 3.0)
                ox, oy = vec(mg['ang'], 20)
                vx, vy = vec(a, 700)
                mg['bullets'].append(dict(x=tx0 + ox, y=ty0 + oy, vx=vx, vy=vy, life=0.56))
                mg['flash'] = 0.05
                mg['heat'] += MG_HEAT
                if mg['shots'] % 3 == 0:
                    self.audio.play('mg', .1)
                if mg['heat'] >= 1.0:
                    mg['jam'] = MG_JAM
                    mg['heat'] = 1.0
                    self.audio.play('hit', .3)
                    self.fx.add('smoke', p['x'], p['y'], 0, -20, 1.5, 4, 14, (210, 210, 214))
        else:
            mg['heat'] = max(0.0, mg['heat'] - 0.22 * dt)
        if tgt is not None:
            mg['heat'] = max(0.0, mg['heat'] - 0.06 * dt)
        self.ng_bullets(dt)

    def ng_bullets(self, dt):
        c = self.c
        e = c['e']
        mg = c['mg']
        boss = c['is_boss']
        for b in mg['bullets'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if b['life'] <= 0 or not (-20 < b['x'] < W + 20 and -20 < b['y'] < H + 20):
                mg['bullets'].remove(b)
                continue
            hit = False
            for j in c['jets'][:]:
                if dist(j['x'], j['y'], b['x'], b['y']) < 15:
                    c['jets'].remove(j)
                    self.fx.explode(j['x'], j['y'], 0.8)
                    self.audio.play('boom_s', .4)
                    self.add_score(50)
                    self.pop('+50', j['x'], j['y'] - 16, (255, 255, 160))
                    hit = True
                    break
            if not hit:
                for pl in c['planes']:
                    if dist(pl['x'], pl['y'], b['x'], b['y']) < 20:
                        pl['hp'] -= 0.5
                        self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25, col=(255, 230, 150), drag=2)
                        if pl['hp'] <= 0:
                            c['planes'].remove(pl)
                            self.fx.explode(pl['x'], pl['y'], 0.8)
                            self.audio.play('boom_s', .4)
                            self.add_score(60)
                            self.pop('+60', pl['x'], pl['y'] - 16, (255, 255, 160))
                        hit = True
                        break
            if not hit:
                for bt in c['boats'][:]:
                    if dist(bt['x'], bt['y'], b['x'], b['y']) < (26 if bt['kind'] == 'boat' else 30):
                        bt['hp'] -= 0.3 * self.up_dmg()
                        self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25, col=(255, 200, 140), drag=2)
                        if bt['hp'] <= 0:
                            c['boats'].remove(bt)
                            self.fx.explode(bt['x'], bt['y'], 1.5, True)
                            self.audio.play('boom_s', .7)
                            self.add_score(120)
                            self.pop('+120', bt['x'], bt['y'] - 20, (255, 255, 160))
                            self.call_out('¡ESCOLTA HUNDIDA!', (255, 230, 130), 'boatkill', 2.5)
                        hit = True
                        break
            if not hit:
                for m in c['mines'][:]:
                    if dist(m['x'], m['y'], b['x'], b['y']) < 14:
                        c['mines'].remove(m)
                        self.fx.explode(m['x'], m['y'], 0.7)
                        self.audio.play('boom_s', .3)
                        hit = True
                        break
            if not hit and self.nb_mg_hit(b['x'], b['y']):
                hit = True
            if not hit and e['sink'] is None and not (c['sub'] and not e['surf']):
                h_, core = self.ship_hit(e, b['x'], b['y'], boss)
                if h_:
                    dmg = (0.13 if core else 0.1) * self.up_dmg() * (0.5 if boss else 1.0)
                    e['hp'] -= dmg
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25, col=(255, 220, 140), drag=2)
                    self.na_charge(0.5)
                    hit = True
            if hit:
                mg['bullets'].remove(b)

    # ------------------------------------------------------------------ dibujo
    def ng_draw(self, cv):
        c = self.c
        mg = c['mg']
        p = c['p']
        if p['sink'] is not None and p['sink'] > 0.3:
            return
        ax_, ay_ = vec(p['h'], AFT)
        tx0, ty0 = p['x'] + ax_, p['y'] + ay_
        self.blit_turret(cv, self.tur_p, tx0, ty0, mg['ang'], 255 if p['sink'] is None else 140)    # torreta de popa (la misma del casco)
        if mg['flash'] > 0:
            fx_, fy_ = vec(mg['ang'], 24)
            glow(cv, tx0 + fx_, ty0 + fy_, 18, (255, 220, 140), 0.9)
        for b in mg['bullets']:
            pygame.draw.line(cv, (255, 240, 150), (b['x'], b['y']), (b['x'] - b['vx'] * 0.03, b['y'] - b['vy'] * 0.03), 2)

    def ng_hud(self, cv):
        mg = self.c['mg']
        jam = mg['jam'] > 0
        x0, y0 = W // 2 + 74, H - 41
        col = (255, 90, 80) if jam else ((255, 200, 80) if mg['heat'] > 0.7 else (140, 230, 255))
        pygame.draw.rect(cv, (8, 12, 24), (x0, y0, 80, 10))
        pygame.draw.rect(cv, col, (x0 + 1, y0 + 1, int(78 * (1.0 if jam else mg['heat'])), 8))
        self.text(cv, 'MG TRABADA' if jam else 'MG AUTO', self.f_s, col, x0 + 86, y0 - 4)
