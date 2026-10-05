"""Desembarco: apoyo naval (artillería y humo), minas con carteles, morteros fijos, reflectores y bengalas."""
import math
import pygame
import random
from .common import H, W, bearing, clamp, coast_r, dist, draw_circ, glow, vec

SUP_NAMES = ('ARTILLERÍA', 'HUMO')
SUP_CD = (45.0, 30.0)
BARRAGE_DELAY = 1.8
BARRAGE_SHELLS = 6
MORTAR_RANGE = 560
MINE_R = 13


class LandingOpsMixin:
    # ------------------------------------------------------------------ armado
    def lz_free_spot(self, lo, hi, avoid, tries=80):
        g = self.g
        for _ in range(tries):
            a = random.uniform(0, 6.2832)
            d = random.uniform(lo, hi) * coast_r(g['R'], g['seed'], a, 1.0)
            x, y = W / 2 + math.cos(a) * d, H / 2 + math.sin(a) * d
            if all(dist(x, y, ax, ay) > ar for ax, ay, ar in avoid) and \
                    all(dist(x, y, c['x'], c['y']) > c['r'] + 36 for c in g['covers']):
                return x, y
        return None

    def lz_ops_setup(self, spawn):
        g = self.g
        lz = g['lz']
        wx = lz['wx']
        lz.update(sup_cd=18.0, sup_type=0, barrage=None, smoke=[], smoke_shots=[], mines=[], signs=[], mortars=[], mshells=[],
                  flare=None, flares=0, flare_cd=0.0)
        avoid = [(spawn[0], spawn[1], 190), (W / 2, H / 2, 150)] + [(b['x'], b['y'], 110) for b in lz['bunkers']]
        for _ in range(2):                                                # campos minados con carteles de aviso
            spot = self.lz_free_spot(0.40, 0.66, avoid)
            if spot is None:
                continue
            fx, fy = spot
            avoid.append((fx, fy, 110))
            for _k in range(4):
                a, r = random.uniform(0, 6.2832), random.uniform(0, 40)
                lz['mines'].append(dict(x=fx + math.cos(a) * r, y=fy + math.sin(a) * r, alive=True, boom=0.0))
            a0 = bearing(spawn[0] - fx, spawn[1] - fy)
            for side in (-1, 1):
                sx, sy = vec(a0 + side * 70, 64)
                lz['signs'].append(dict(x=fx + sx, y=fy + sy, h=a0 + side * 70))
        n_m = 0 if self.wave < 2 else (1 if self.wave < 4 else 2)
        for _ in range(n_m):                                              # morteros fijos que se activan con la alarma
            spot = self.lz_free_spot(0.22, 0.5, avoid)
            if spot is None:
                continue
            x, y = spot
            avoid.append((x, y, 140))
            hp = float(12 + self.wave)
            m = dict(x=x, y=y, hp=hp, max=hp, alive=True, hit=0.0, flash=0.0, cd=random.uniform(2.0, 4.0), mortar=True, h=bearing(W / 2 - x, H / 2 - y))
            lz['mortars'].append(m)
            g['covers'].append(dict(x=x, y=y, r=22, kind='mortar', seed=0, bunker=m))
        n_s = {'noche': 2, 'tormenta': 1}.get(wx, 0)                      # reflectores (barren con un haz ancho)
        for _ in range(n_s):
            a = random.uniform(0, 6.2832)
            rr = coast_r(g['R'], g['seed'], a, 0.7)
            x, y = W / 2 + math.cos(a) * rr, H / 2 + math.sin(a) * rr
            base = bearing(W / 2 - x, H / 2 - y)
            g['cams'].append(dict(x=x, y=y, base=base, h=base, sw=random.uniform(0, 6.28), det=0.0, hp=3, on=True,
                                  rng=330, fov=24, amp=70, col=(255, 250, 200), search=True))

    # ------------------------------------------------------------------ apoyo naval
    def lz_support_toggle(self):
        lz = self.g['lz']
        lz['sup_type'] ^= 1
        self.audio.play('blip', .5)
        self.toast('Apoyo naval: %s' % SUP_NAMES[lz['sup_type']], (170, 220, 255))

    def lz_support_fire(self):
        g = self.g
        lz = g['lz']
        p = g['p']
        if p['dead'] or g['phase'] != 'play' or lz['intro'] > 0 or lz['stage'] >= 3:
            return
        if lz['sup_cd'] > 0:
            self.toast('Apoyo naval recargando: %d s' % math.ceil(lz['sup_cd']), (255, 200, 120))
            return
        ax, ay = self.ground_aim()
        lz['sup_cd'] = SUP_CD[lz['sup_type']]
        self.audio.play('launch', .8)
        self.audio.play('ping', .6)
        if lz['sup_type'] == 0:
            lz['barrage'] = dict(x=ax, y=ay, t=0.0, n=0, nt=BARRAGE_DELAY)
            self.lz_say('BUQUE', '¡Fuego de artillería en camino! ¡Salgan de la zona!', (255, 210, 130))
        else:
            lz['smoke_shots'].append(dict(x=ax, y=ay, t=0.0))
            self.lz_say('BUQUE', 'Cortina de humo lanzada.', (200, 215, 235))

    def lz_blast(self, x, y, R, dmg):
        """Explosión de apoyo: daña a enemigos, búnkeres, aliados y a vos si estás cerca."""
        g = self.g
        lz = g['lz']
        p = g['p']
        self.g_noise(380, 0.5)
        for e in g['enemies'][:]:
            d = dist(x, y, e['x'], e['y'])
            if d < R:
                e['hp'] -= dmg * (1 - 0.5 * d / R)
                e['hit'] = 0.15
                if e['state'] in ('hold', 'susp') and e['hp'] > 0:
                    self.alert(e)
                if e['hp'] <= 0:
                    self.kill_ground_enemy(e)
        for b in lz['bunkers'] + lz['mortars']:
            d = dist(x, y, b['x'], b['y'])
            if b['alive'] and d < R + 22:
                self.lz_bunker_damage(b, dmg * 0.9 * (1 - 0.4 * d / (R + 22)))
        d = dist(x, y, p['x'], p['y'])
        if not p['dead'] and d < R:
            self.hurt_player(int(18 * (1 - 0.6 * d / R)))
        for a in g['allies']:
            d = dist(x, y, a['x'], a['y'])
            if d < R and not a['down'] and not a['kia']:
                self.lz_hurt_ally(a, int(16 * (1 - 0.6 * d / R)))
        for m in lz['mines']:
            if m['alive'] and dist(x, y, m['x'], m['y']) < R:
                m['alive'], m['boom'] = False, 0.25

    def lz_support_update(self, dt):
        g = self.g
        lz = g['lz']
        lz['sup_cd'] = max(0.0, lz['sup_cd'] - dt)
        br = lz['barrage']
        if br is not None:
            br['t'] += dt
            if br['t'] >= br['nt']:
                if br['n'] < BARRAGE_SHELLS:
                    a, r = random.uniform(0, 6.2832), random.uniform(0, 105)
                    lz['shells'].append(dict(x=br['x'] + math.cos(a) * r, y=br['y'] + math.sin(a) * r, t=0.5, big=True))
                    br['n'] += 1
                    br['nt'] = br['t'] + 0.38
                    self.audio.play('cannon', .35)
                else:
                    lz['barrage'] = None
        for s in lz['smoke_shots'][:]:
            s['t'] += dt
            if s['t'] >= 1.1:
                lz['smoke_shots'].remove(s)
                lz['smoke'].append(dict(x=s['x'], y=s['y'], r=118.0, age=0.0, life=16.0, seed=random.random() * 6.28))
                self.audio.play('boom_s', .4)
                self.fx.add('glow', s['x'], s['y'], life=.25, r0=10, r1=40, col=(210, 220, 230))
        for c in lz['smoke'][:]:
            c['age'] += dt
            if c['age'] > c['life']:
                lz['smoke'].remove(c)

    # ------------------------------------------------------------------ minas
    def lz_mine_blast(self, m):
        g = self.g
        p = g['p']
        m['alive'] = False
        x, y = m['x'], m['y']
        self.fx.explode(x, y, 1.1, True)
        self.audio.play('boom_s', .7)
        self.shake = max(self.shake, 9)
        g['decals'].append((x, y, 22))
        g['decals'] = g['decals'][-40:]
        self.g_noise(320, 0.5)
        d = dist(x, y, p['x'], p['y'])
        if not p['dead'] and d < 72:
            self.hurt_player(int(34 * (1 - 0.5 * d / 72)))
        for a in g['allies']:
            d = dist(x, y, a['x'], a['y'])
            if d < 72 and not a['down'] and not a['kia']:
                self.lz_hurt_ally(a, int(26 * (1 - 0.5 * d / 72)))
        for e in g['enemies'][:]:
            if dist(x, y, e['x'], e['y']) < 60:
                e['hp'] -= 6.0
                e['hit'] = 0.15
                if e['hp'] <= 0:
                    self.kill_ground_enemy(e)
        for o in g['lz']['mines']:
            if o['alive'] and dist(x, y, o['x'], o['y']) < 50:
                o['alive'], o['boom'] = False, 0.2

    def lz_mines_update(self, dt, alive):
        g = self.g
        lz = g['lz']
        p = g['p']
        for m in lz['mines']:
            if m['boom'] > 0:
                m['boom'] -= dt
                if m['boom'] <= 0:
                    m['alive'] = True
                    self.lz_mine_blast(m)
                continue
            if not m['alive']:
                continue
            hit = alive and dist(m['x'], m['y'], p['x'], p['y']) < MINE_R
            if not hit:
                hit = any(not a['down'] and not a['kia'] and dist(m['x'], m['y'], a['x'], a['y']) < MINE_R for a in g['allies'])
            if not hit:
                for b in g['bullets']:
                    if b['own'] in ('p', 'a') and dist(m['x'], m['y'], b['x'], b['y']) < 9:
                        hit = True
                        g['bullets'].remove(b)
                        break
            if hit:
                self.lz_mine_blast(m)

    # ------------------------------------------------------------------ morteros
    def lz_mortars_update(self, dt, alive):
        g = self.g
        lz = g['lz']
        p = g['p']
        active = g['alert_t'] > 0 or lz['stage'] >= 2
        for m in lz['mortars']:
            if not m['alive']:
                if random.random() < dt * 2.5:
                    self.fx.add('smoke', m['x'] + random.uniform(-10, 10), m['y'] + random.uniform(-8, 8), 0, -22, 2.2, 6, 18, (46, 46, 46))
                continue
            m['cd'] -= dt
            m['hit'] = max(0.0, m['hit'] - dt)
            m['flash'] = max(0.0, m['flash'] - dt)
            if alive and active and dist(m['x'], m['y'], p['x'], p['y']) < MORTAR_RANGE:
                m['h'] = bearing(p['x'] - m['x'], p['y'] - m['y'])
                if m['cd'] <= 0:
                    m['cd'] = (3.2 if lz['stage'] >= 2 else 4.4) * max(0.6, 1 - 0.05 * self.wave) + random.uniform(0, 1.0)
                    tx = p['x'] + p['vx'] * 0.45 + random.uniform(-26, 26)
                    ty = p['y'] + p['vy'] * 0.45 + random.uniform(-26, 26)
                    lz['mshells'].append(dict(x=tx, y=ty, t=0.0))
                    m['flash'] = 0.12
                    self.audio.play('launch', .35)
        for s in lz['mshells'][:]:
            s['t'] += dt
            if s['t'] >= 1.5:
                lz['mshells'].remove(s)
                self.fx.explode(s['x'], s['y'], 1.2, True)
                self.audio.play('boom_s', .6)
                self.shake = max(self.shake, 7)
                g['decals'].append((s['x'], s['y'], 30))
                g['decals'] = g['decals'][-40:]
                d = dist(s['x'], s['y'], p['x'], p['y'])
                if alive and d < 62:
                    self.hurt_player(int(24 * (1 - 0.5 * d / 62)))
                for a in g['allies']:
                    d = dist(s['x'], s['y'], a['x'], a['y'])
                    if d < 62 and not a['down'] and not a['kia']:
                        self.lz_hurt_ally(a, int(18 * (1 - 0.5 * d / 62)))
                for e in g['enemies'][:]:
                    if dist(s['x'], s['y'], e['x'], e['y']) < 62:
                        e['hp'] -= 3.0
                        e['hit'] = 0.15
                        if e['hp'] <= 0:
                            self.kill_ground_enemy(e)

    # ------------------------------------------------------------------ bengala
    def lz_flare_update(self, dt, alive, new_alert):
        g = self.g
        lz = g['lz']
        p = g['p']
        lz['flare_cd'] = max(0.0, lz['flare_cd'] - dt)
        if new_alert and lz['flares'] < 2 and lz['flare_cd'] <= 0 and lz['stage'] < 2 and alive:
            foes = [e for e in g['enemies'] if e['state'] == 'combat']
            src = min(foes, key=lambda e: dist(e['x'], e['y'], p['x'], p['y'])) if foes else None
            lz['flares'] += 1
            lz['flare_cd'] = 25.0
            lz['flare'] = dict(x=p['x'], y=p['y'], t=0.0, dur=9.0)
            if src is not None:
                for _ in range(8):
                    self.fx.add('spark', src['x'], src['y'], random.uniform(-20, 20), -random.uniform(80, 160), 0.6, col=(255, 160, 90), drag=1)
            self.audio.play('launch', .5)
            self.lz_say('LUNA', '¡Bengala enemiga! ¡Nos tienen a la vista!', (255, 190, 130))
        fl = lz['flare']
        if fl is not None:
            fl['t'] += dt
            if alive:
                g['last_seen'] = (p['x'], p['y'])
                g['alert_t'] = max(g['alert_t'], 12.0)
            if fl['t'] >= fl['dur']:
                lz['flare'] = None

    # ------------------------------------------------------------------ bucle y dibujo
    def lz_ops_update(self, dt, alive, new_alert):
        self.lz_support_update(dt)
        self.lz_mines_update(dt, alive)
        self.lz_mortars_update(dt, alive)
        self.lz_flare_update(dt, alive, new_alert)

    def lz_smoke_blocks(self, x0, y0, x1, y1):
        lz = self.g.get('lz')
        if not lz or not lz['smoke']:
            return False
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy
        if L2 < 70 * 70:
            return False
        for c in lz['smoke']:
            if c['age'] < 0.8:
                continue
            t = clamp(((c['x'] - x0) * vx + (c['y'] - y0) * vy) / L2, 0, 1)
            if dist(c['x'], c['y'], x0 + vx * t, y0 + vy * t) < c['r'] * 0.8:
                return True
        return False

    def lz_ops_draw_world(self, cv, cx_, cy_):
        g = self.g
        lz = g['lz']
        p = g['p']
        t = self.t
        for m in lz['mines']:
            if not m['alive']:
                continue
            sx, sy = m['x'] - cx_, m['y'] - cy_
            if not (-20 < sx < W + 20 and -20 < sy < H + 20):
                continue
            draw_circ(cv, sx, sy, 8, (60, 46, 30), 150)
            pygame.draw.circle(cv, (44, 48, 44), (int(sx), int(sy)), 4)
            if dist(m['x'], m['y'], p['x'], p['y']) < 130 and int(t * 3) % 2 == 0:
                pygame.draw.circle(cv, (255, 70, 60), (int(sx), int(sy)), 2)
        for s in lz['signs']:
            sx, sy = s['x'] - cx_, s['y'] - cy_
            if not (-40 < sx < W + 40 and -40 < sy < H + 40):
                continue
            pygame.draw.line(cv, (84, 62, 40), (sx, sy + 6), (sx, sy + 18), 3)
            pygame.draw.polygon(cv, (236, 200, 60), [(sx, sy - 14), (sx - 13, sy + 8), (sx + 13, sy + 8)])
            pygame.draw.polygon(cv, (40, 36, 30), [(sx, sy - 14), (sx - 13, sy + 8), (sx + 13, sy + 8)], 2)
            self.text(cv, '!', self.f_s, (40, 30, 24), sx, sy - 10, 'c', shadow=False)
            self.text(cv, 'MINAS', self.f_s, (255, 220, 120), sx, sy + 20, 'c', alpha=180)
        for m in lz['mortars']:
            sx, sy = m['x'] - cx_, m['y'] - cy_
            if not (-100 < sx < W + 100 and -100 < sy < H + 100):
                continue
            if not m['alive']:
                draw_circ(cv, sx, sy, 28, (22, 20, 18), 150)
                draw_circ(cv, sx, sy, 16, (50, 48, 46), 160)
                continue
            for k in range(10):
                a = 6.2832 * k / 10
                pygame.draw.circle(cv, (150, 130, 96) if m['hit'] <= 0 else (230, 220, 200), (int(sx + math.cos(a) * 24), int(sy + math.sin(a) * 24)), 8)
                pygame.draw.circle(cv, (110, 94, 66), (int(sx + math.cos(a) * 24), int(sy + math.sin(a) * 24)), 8, 1)
            pygame.draw.circle(cv, (70, 74, 72), (int(sx), int(sy)), 14)
            ex, ey = vec(m['h'], 22)
            pygame.draw.line(cv, (30, 32, 34), (sx, sy), (sx + ex, sy + ey), 7)
            pygame.draw.circle(cv, (20, 22, 24), (int(sx + ex), int(sy + ey)), 4)
            if m['flash'] > 0:
                glow(cv, sx + ex, sy + ey, 30, (255, 210, 120))
            if m['hp'] < m['max']:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 20, sy - 40, 40, 6))
                pygame.draw.rect(cv, (240, 120, 70), (sx - 19, sy - 39, int(38 * clamp(m['hp'] / m['max'], 0, 1)), 4))
            self.text(cv, 'MORTERO', self.f_s, (255, 190, 140), sx, sy - 56, 'c', alpha=190)
        for s in lz['mshells']:
            sx, sy = s['x'] - cx_, s['y'] - cy_
            k = s['t'] / 1.5
            pul = 0.5 + 0.5 * math.sin(t * 16)
            draw_circ(cv, sx, sy, 62, (255, 60, 50), 22 + 34 * pul)
            draw_circ(cv, sx, sy, 62 * (1 - 0.6 * k) + 8, (255, 90, 70), 190, 2)
            pygame.draw.line(cv, (255, 230, 200), (sx, sy - 260 * (1 - k) - 18), (sx, sy - 260 * (1 - k)), 3)
        br = lz['barrage']
        if br is not None and br['n'] < BARRAGE_SHELLS:
            sx, sy = br['x'] - cx_, br['y'] - cy_
            pul = 0.5 + 0.5 * math.sin(t * 14)
            draw_circ(cv, sx, sy, 118, (255, 190, 70), 24 + 30 * pul)
            draw_circ(cv, sx, sy, 118, (255, 210, 90), 200, 2)
            pygame.draw.line(cv, (255, 210, 90), (sx - 16, sy), (sx + 16, sy), 2)
            pygame.draw.line(cv, (255, 210, 90), (sx, sy - 16), (sx, sy + 16), 2)
        for s in lz['smoke_shots']:
            sx, sy = s['x'] - cx_, s['y'] - cy_
            k = s['t'] / 1.1
            draw_circ(cv, sx, sy, 118, (200, 215, 235), 90, 2)
            pygame.draw.line(cv, (230, 235, 245), (sx, sy - 300 * (1 - k) - 16), (sx, sy - 300 * (1 - k)), 3)
        for c in lz['smoke']:
            sx, sy = c['x'] - cx_, c['y'] - cy_
            if not (-200 < sx < W + 200 and -200 < sy < H + 200):
                continue
            k = clamp(c['age'] / 1.2, 0, 1) * clamp((c['life'] - c['age']) / 3.0, 0, 1)
            for i in range(9):
                a = c['seed'] + i * 0.7 + t * 0.25
                rr = c['r'] * (0.25 + 0.55 * ((i * 37) % 10) / 10)
                draw_circ(cv, sx + math.cos(a) * rr * 0.7, sy + math.sin(a * 1.2) * rr * 0.7, c['r'] * (0.5 + 0.06 * math.sin(t * 1.5 + i)), (196, 202, 210), 54 * k)
            draw_circ(cv, sx, sy, c['r'] * 0.8, (210, 216, 224), 80 * k, 2)
        fl = lz['flare']
        if fl is not None:
            k = fl['t'] / fl['dur']
            sx, sy = fl['x'] - cx_, fl['y'] - cy_ - 150 * (1 - 0.7 * k)
            fk = clamp((1 - k) * 3, 0, 1) * (0.8 + 0.2 * math.sin(t * 30))
            draw_circ(cv, fl['x'] - cx_, fl['y'] - cy_, 300, (255, 230, 170), 26 * fk)
            glow(cv, sx, sy, 90, (255, 235, 180), fk)
            pygame.draw.circle(cv, (255, 250, 220), (int(sx), int(sy)), 4)

    def lz_ops_lights(self, cx_, cy_):
        """Luces extra para la capa nocturna: la bengala ilumina un gran círculo."""
        fl = self.g['lz']['flare']
        if fl is None:
            return []
        k = clamp((1 - fl['t'] / fl['dur']) * 3, 0, 1)
        return [(fl['x'] - cx_, fl['y'] - cy_, int(380 * (0.4 + 0.6 * k)))]

    def lz_ops_hud(self, cv):
        g = self.g
        lz = g['lz']
        if lz['stage'] >= 3:
            return
        x, y = 14, H - 176
        self.panel(cv, (x, y, 330, 44), 160)
        ready = lz['sup_cd'] <= 0
        k = 1.0 if ready else 1 - lz['sup_cd'] / SUP_CD[lz['sup_type']]
        col = (120, 255, 190) if ready else (255, 200, 90)
        self.bar(cv, x + 12, y + 20, 306, 16, k, col, SUP_NAMES[lz['sup_type']])
        self.text(cv, 'APOYO NAVAL', self.f_s, (255, 255, 255), x + 12, y + 2)
        self.text(cv, 'LISTO [T]  cambiar [TAB]' if ready else 'recarga %d s' % math.ceil(lz['sup_cd']), self.f_s, col, x + 318, y + 2, 'r')
