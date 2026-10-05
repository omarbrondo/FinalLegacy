"""Desembarco épico: escuadra aliada, cuatro fases (playa, interior, antena, extracción), búnkeres y ambiente."""
import math
import pygame
import random
from .common import H, W, angle_diff, bearing, clamp, coast_r, dist, draw_circ, glow, lerp, vec

ALLY_NAMES = ('RAMOS', 'DÍAZ', 'LUNA')
ALLY_COL = (170, 220, 255)
SLOTS = ((-66, 56), (68, 52), (0, 100))              # lugar de cada aliado respecto del jugador
STAGE_NAMES = ('PLAYA', 'INTERIOR', 'ANTENA', 'EXTRACCIÓN')
WX_LABEL = {'dia': 'DÍA DESPEJADO', 'amanecer': 'AMANECER', 'noche': 'NOCHE CERRADA', 'tormenta': 'TORMENTA'}
COMPASS = ('ESTE', 'SUDESTE', 'SUR', 'SUROESTE', 'OESTE', 'NOROESTE', 'NORTE', 'NORESTE')
DEF_TIMES = (0.6, 8.0, 15.0)                         # oleadas enemigas durante la transmisión
BUNKER_RANGE = 360
EXTRACT_TIME = 50.0


class LandingMixin:
    # ------------------------------------------------------------------ armado de la misión
    def lz_setup(self, spawn, seed):
        g = self.g
        R = g['R']
        if self.wave <= 1:
            wx = ('dia', 'amanecer')[(g['island_idx'] or 0) % 2]
        else:
            wx = ('dia', 'amanecer', 'noche', 'tormenta')[(self.wave * 2 + (g['island_idx'] or 0)) % 4]
        bunkers = []
        for side in (-1, 1):
            a = math.pi / 2 + side * random.uniform(0.55, 0.75)
            d = coast_r(R, seed, a, 0.62)
            x, y = W / 2 + math.cos(a) * d, H / 2 + math.sin(a) * d
            g['covers'] = [c for c in g['covers'] if dist(c['x'], c['y'], x, y) > 70]
            hp = float(10 + self.wave)
            b = dict(x=x, y=y, h=bearing(spawn[0] - x, spawn[1] - y), ha=bearing(spawn[0] - x, spawn[1] - y), hp=hp, max=hp,
                     cd=random.uniform(1.0, 2.0), burst=0, bcd=0.0, alive=True, flash=0.0, hit=0.0, tele=0.0, aim=0.0)
            bunkers.append(b)
            g['covers'].append(dict(x=x, y=y, r=26, kind='bunker', seed=0, bunker=b))
        allies = []
        for i, nm in enumerate(ALLY_NAMES):
            allies.append(dict(name=nm, x=float(spawn[0]), y=float(spawn[1] + 240), h=0.0, hp=50.0, max=50.0, cd=random.uniform(0.3, 1.2),
                               ph=0.0, hit=0.0, flash=0.0, down=False, kia=False, bleed=0.0, rev=0.0, burst=0, bcd=0.0, slot=i, mv=False))
        g['allies'] = allies
        g['slow'] = 0.0
        g['lz'] = dict(stage=0, stage_t=0.0, intro=3.6, intro_len=3.6, wx=wx, supp=6.0, cover_t=0.4, shells=[], calls=[],
                       bunkers=bunkers, def_clock=0.0, def_prog=0.0, def_dur=22.0, def_idx=0, ghost=False, boat=(spawn[0], spawn[1] + 300),
                       lost=0, bunker_kills=0, last_alerts=0, say_t=0.0, rain=[(random.random() * W, random.random() * H, random.uniform(0.7, 1.3)) for _ in range(130)],
                       bolt=random.uniform(4, 9), white=0.0, thunder=[], stats=None, t_install=0.0, far_t=0.0, hit_msg=0.0)
        p = g['p']
        p['gren'] = 6
        p['x'], p['y'] = float(spawn[0]), float(spawn[1] + 290)
        self.audio.music('beach', self.wave, 'battle')

    # ------------------------------------------------------------------ utilidades
    def lz_say(self, who, text, col=ALLY_COL):
        lz = self.g['lz']
        lz['calls'].append([who, text, col, 4.2])
        lz['calls'] = lz['calls'][-3:]
        self.audio.play('blip', .3)

    def lz_stage(self):
        lz = self.g.get('lz')
        return lz['stage'] if lz else -1

    def lz_noise_k(self):
        lz = self.g.get('lz')
        return 0.7 if lz and lz['wx'] == 'tormenta' else 1.0

    def lz_set_stage(self, st):
        lz = self.g['lz']
        lz['stage'], lz['stage_t'] = st, 0.0
        self.audio.music(('beach', 'infil', 'holdout', 'extract')[st], self.wave, 'battle')

    def lz_boat_pos(self):
        return self.g['lz']['boat']

    def lz_timer(self):
        """Etiqueta y segundos del reloj grande del desembarco."""
        g = self.g
        lz = g['lz']
        if lz['stage'] == 2:
            return 'DEFENSA', max(0.0, lz['def_dur'] - lz['def_prog'])
        if lz['stage'] == 3:
            return 'LANCHA', max(0.0, g['tleft'])
        return 'TIEMPO', max(0.0, g['tleft'])

    def lz_downed_near(self, x, y, r=52):
        g = self.g
        best = None
        for a in g.get('allies', ()):
            if a['down'] and not a['kia'] and dist(a['x'], a['y'], x, y) < r and (best is None or dist(a['x'], a['y'], x, y) < best[0]):
                best = (dist(a['x'], a['y'], x, y), a)
        return best[1] if best else None

    # ------------------------------------------------------------------ introducción en lancha
    def lz_intro(self, dt):
        g = self.g
        lz = g['lz']
        p = g['p']
        sx, sy0 = g['spawn']
        lz['intro'] -= dt
        k = 1 - clamp(lz['intro'] / lz['intro_len'], 0, 1)
        e = 1 - (1 - k) ** 2
        by = lerp(sy0 + 300, sy0 + 58, e)
        lz['boat'] = (sx, by)
        p['x'], p['y'], p['h'] = float(sx), by - 6, 0.0
        for i, a in enumerate(g['allies']):
            a['x'], a['y'], a['h'] = sx + (-1, 1, 0)[i] * 11, by + 8 + (0, 0, 14)[i], 0.0
        if random.random() < dt * 14:
            self.fx.add('foam', sx + random.uniform(-14, 14), by + 30, random.uniform(-20, 20), 40, 0.8, 4, 12, (230, 245, 255))
        self.lz_cover_fire(dt, intro=True)
        self.lz_shells(dt)
        self.lz_weather(dt)
        self.g_camera(0.0, True)
        g['cam'][1] = max(g['cam'][1], by - 700)           # la cámara acompaña a la lancha mientras se acerca
        self.fx.update(dt)
        if lz['intro'] <= 0:
            lz['intro'] = 0.0
            p['x'], p['y'] = float(sx), float(sy0)
            for i, a in enumerate(g['allies']):
                a['x'], a['y'] = sx + SLOTS[i][0], sy0 + SLOTS[i][1] * 0.1 - 6
            lz['boat'] = (sx, sy0 + 58)
            self.lz_say('RAMOS', '¡A tierra! ¡Cubran la playa!')
            self.toast('Mantené E sobre un aliado herido para auxiliarlo', (170, 220, 255))
            self.shake = max(self.shake, 6)

    # ------------------------------------------------------------------ fuego de cobertura del buque
    def lz_cover_fire(self, dt, intro=False):
        g = self.g
        lz = g['lz']
        if not intro:
            if lz['supp'] <= 0:
                return
            lz['supp'] -= dt
        lz['cover_t'] -= dt
        if lz['cover_t'] > 0:
            return
        lz['cover_t'] = random.uniform(0.5, 0.9) if intro else random.uniform(0.9, 1.5)
        alive_b = [b for b in lz['bunkers'] if b['alive']]
        if not alive_b:
            return
        b = random.choice(alive_b)
        for _ in range(8):
            x, y = b['x'] + random.uniform(-90, 90), b['y'] + random.uniform(-90, 90)
            if dist(x, y, g['p']['x'], g['p']['y']) > 130:
                break
        lz['shells'].append(dict(x=x, y=y, t=0.0))
        self.audio.play('cannon', .25)

    def lz_shells(self, dt):
        g = self.g
        lz = g['lz']
        for s in lz['shells'][:]:
            s['t'] += dt
            if s['t'] >= 0.9:
                lz['shells'].remove(s)
                self.fx.explode(s['x'], s['y'], 1.2, True)
                self.audio.play('boom_s', .5)
                self.shake = max(self.shake, 5)
                g['decals'].append((s['x'], s['y'], 26))
                g['decals'] = g['decals'][-40:]
                for b in lz['bunkers']:
                    if b['alive'] and dist(b['x'], b['y'], s['x'], s['y']) < 70:
                        self.lz_bunker_damage(b, 0.18 * b['max'])

    # ------------------------------------------------------------------ búnkeres
    def lz_bunker_damage(self, b, dmg):
        if not b['alive']:
            return
        b['hp'] -= dmg
        b['hit'] = 0.1
        if b['hp'] > 0:
            return
        g = self.g
        lz = g['lz']
        b['alive'] = False
        lz['bunker_kills'] += 1
        for c in g['covers']:
            if c.get('bunker') is b:
                c['x'] = c['y'] = -99999.0                # mantiene los índices de cobertura de las balas en vuelo
        self.fx.explode(b['x'], b['y'], 1.5, True)
        for _ in range(3):
            self.fx.explode(b['x'] + random.uniform(-26, 26), b['y'] + random.uniform(-26, 26), 1.0, True)
        self.audio.play('boom_l', .7)
        self.shake = max(self.shake, 12)
        g['decals'].append((b['x'], b['y'], 40))
        self.add_score(150)
        self.gpop('+150', b['x'], b['y'] - 30)
        self.g_noise(240, 0.5)
        self.lz_say('LUNA', '¡Búnker eliminado!')

    def lz_bunkers_update(self, dt, alive):
        g = self.g
        lz = g['lz']
        p = g['p']
        for b in lz['bunkers']:
            if not b['alive']:
                if random.random() < dt * 3:
                    self.fx.add('smoke', b['x'] + random.uniform(-14, 14), b['y'] + random.uniform(-10, 10), 0, -22, 2.4, 6, 20, (46, 46, 46))
                continue
            b['cd'] -= dt
            b['flash'] = max(0.0, b['flash'] - dt)
            b['hit'] = max(0.0, b['hit'] - dt)
            if b['burst'] > 0:
                b['bcd'] -= dt
                if b['bcd'] <= 0:
                    b['burst'] -= 1
                    b['bcd'] = 0.085
                    a = b['aim'] + random.uniform(-3.5, 3.5)
                    mx, my = vec(a, 40)
                    vx, vy = vec(a, 470)
                    g['bullets'].append(dict(x=b['x'] + mx, y=b['y'] + my, vx=vx, vy=vy, own='e', dmg=3 + self.wave // 3, life=1.0,
                                             ign=self.g_ign(b['x'], b['y'])))
                    b['flash'] = 0.06
                    if dist(b['x'], b['y'], p['x'], p['y']) < 600:
                        self.audio.play('mg', .2)
                continue
            tgts = ([(p['x'], p['y'])] if alive else []) + [(a['x'], a['y']) for a in g['allies'] if not a['down'] and not a['kia']]
            best = None
            for tx, ty in tgts:
                d = dist(b['x'], b['y'], tx, ty)
                if d < BUNKER_RANGE and abs(angle_diff(b['h'], bearing(tx - b['x'], ty - b['y']))) < 62 and (best is None or d < best[0]) \
                        and self.g_los(b['x'], b['y'], tx, ty):
                    best = (d, tx, ty)
            want = b['h'] + 24 * math.sin(self.t * 0.8 + b['x'])
            if best is not None:
                want = bearing(best[1] - b['x'], best[2] - b['y'])
            b['ha'] = (b['ha'] + clamp(angle_diff(b['ha'], want), -150 * dt, 150 * dt)) % 360
            if lz['supp'] > 0 or lz['intro'] > 0 or best is None:
                b['tele'] = max(0.0, b['tele'] - dt * 2)
                continue
            b['tele'] += dt
            if b['tele'] > 0.5 and b['cd'] <= 0:
                b['burst'], b['bcd'], b['aim'] = 7, 0.0, b['ha']
                b['cd'] = random.uniform(1.6, 2.4)
                b['tele'] = 0.0

    # ------------------------------------------------------------------ aliados
    def lz_hurt_ally(self, a, dmg):
        if a['down'] or a['kia']:
            return
        a['hp'] -= dmg
        a['hit'] = 0.12
        if a['hp'] <= 0:
            a['hp'], a['down'], a['bleed'], a['rev'] = 0.0, True, 28.0, 0.0
            self.lz_say(a['name'], '¡Estoy herido! ¡Ayuda!', (255, 150, 130))
            self.audio.play('hit', .4)

    def lz_revive_update(self, dt, alive, keys):
        g = self.g
        p = g['p']
        tgt = self.lz_downed_near(p['x'], p['y']) if alive else None
        for a in g['allies']:
            if not a['down'] or a['kia']:
                continue
            a['bleed'] -= dt
            if a['bleed'] <= 0:
                a['kia'] = True
                g['lz']['lost'] += 1
                self.lz_say('RAMOS' if a['name'] != 'RAMOS' else 'DÍAZ', 'Perdimos a %s...' % a['name'], (255, 130, 110))
                continue
            if a is tgt and keys[pygame.K_e]:
                a['rev'] += dt / 2.0
                self.g_noise(40, 0.12)
                if a['rev'] >= 1.0:
                    a['down'], a['hp'], a['rev'] = False, 28.0, 0.0
                    self.add_score(100)
                    self.gpop('+100 AUXILIO', a['x'], a['y'] - 34, (140, 255, 200))
                    self.lz_say(a['name'], '¡Gracias, jefe! ¡Sigo!')
                    self.audio.play('pickup', .6)
            else:
                a['rev'] = max(0.0, a['rev'] - dt * 0.6)

    def lz_ally_cover(self, a, tgt):
        """Posición detrás de la cobertura más cercana, del lado opuesto al enemigo."""
        g = self.g
        p = g['p']
        best = None
        for c in g['covers']:
            if c.get('bunker'):
                continue
            d = dist(a['x'], a['y'], c['x'], c['y'])
            if d < 190 and dist(c['x'], c['y'], p['x'], p['y']) < 260 and (best is None or d < best[0]):
                best = (d, c)
        if best is None:
            return None
        c = best[1]
        away = bearing(c['x'] - tgt[0], c['y'] - tgt[1])
        ox, oy = vec(away, c['r'] + 15)
        return c['x'] + ox, c['y'] + oy

    def lz_allies_update(self, dt, alive):
        g = self.g
        lz = g['lz']
        p = g['p']
        foes = [e for e in g['enemies'] if e['state'] == 'combat']
        for a in g['allies']:
            if a['kia'] or a['down']:
                continue
            a['hit'] = max(0.0, a['hit'] - dt)
            a['flash'] = max(0.0, a['flash'] - dt)
            a['cd'] -= dt
            dp = dist(a['x'], a['y'], p['x'], p['y'])
            tgt = None
            bd = 340.0
            for e in foes:
                d = dist(a['x'], a['y'], e['x'], e['y'])
                if d < bd and self.g_los(a['x'], a['y'], e['x'], e['y']):
                    tgt, bd = (e['x'], e['y']), d
            if tgt is None and lz['stage'] == 0:
                for b in lz['bunkers']:
                    d = dist(a['x'], a['y'], b['x'], b['y'])
                    if b['alive'] and d < 380 and lz['supp'] <= 0 and self.g_los(a['x'], a['y'], b['x'] + (a['x'] - b['x']) / (d or 1) * 40, b['y'] + (a['y'] - b['y']) / (d or 1) * 40):
                        tgt = (b['x'], b['y'])
                        break
            goal, sp = None, 118.0
            if dp > 300:
                goal, sp = (p['x'], p['y']), 165.0
                tgt = None
            elif tgt is not None:
                goal = self.lz_ally_cover(a, tgt)
                sp = 125.0
            else:
                sx, sy = SLOTS[a['slot']]
                goal = (p['x'] + sx, p['y'] + sy)
                if dp > 150:
                    sp = 150.0
            moving = False
            if goal is not None and dist(a['x'], a['y'], goal[0], goal[1]) > 14:
                hd = bearing(goal[0] - a['x'], goal[1] - a['y'])
                dx, dy = vec(hd, sp * dt)
                for o in g['allies']:
                    if o is not a and not o['kia'] and dist(a['x'], a['y'], o['x'], o['y']) < 26:
                        dx += (a['x'] - o['x']) * dt * 2
                        dy += (a['y'] - o['y']) * dt * 2
                self.g_step(a, dx, dy)
                a['ph'] += sp * dt / 9.0
                moving = True
                face = hd
            else:
                face = a['h']
            if tgt is not None:
                face = bearing(tgt[0] - a['x'], tgt[1] - a['y'])
                if a['burst'] == 0 and a['cd'] <= 0:
                    a['burst'], a['bcd'], a['cd'] = 3, 0.0, random.uniform(1.0, 1.6)
            elif p['dead'] is False and not moving and dp < 200:
                face = p['h']
            a['h'] = (a['h'] + clamp(angle_diff(a['h'], face), -420 * dt, 420 * dt)) % 360
            a['mv'] = moving
            if a['burst'] > 0:
                a['bcd'] -= dt
                if tgt is None:
                    a['burst'] = 0
                elif a['bcd'] <= 0:
                    a['burst'] -= 1
                    a['bcd'] = 0.11
                    ang = bearing(tgt[0] - a['x'], tgt[1] - a['y']) + random.uniform(-5, 5)
                    mx, my = vec(ang, 38)
                    vx, vy = vec(ang, 540)
                    g['bullets'].append(dict(x=a['x'] + mx, y=a['y'] + my, vx=vx, vy=vy, own='a', dmg=1.0 * self.up_dmg(), life=0.8,
                                             ign=self.g_ign(a['x'], a['y'])))
                    a['flash'] = 0.06
                    if dp < 520:
                        self.audio.play('mg', .1)
        # los enemigos también disparan a los aliados que tienen más cerca que al jugador
        for e in g['enemies']:
            if e['state'] != 'combat' or e['kind'] in ('dog', 'sniper', 'gren'):
                continue
            e['acd'] = e.get('acd', random.uniform(0.4, 1.4)) - dt
            if e['acd'] > 0:
                continue
            best = None
            for a in g['allies']:
                if a['down'] or a['kia']:
                    continue
                d = dist(e['x'], e['y'], a['x'], a['y'])
                if d < 300 and (best is None or d < best[0]) and self.g_los(e['x'], e['y'], a['x'], a['y']):
                    best = (d, a)
            dpl = dist(e['x'], e['y'], p['x'], p['y']) if alive else 9999.0
            if best is not None and (best[0] + 25 < dpl or not self.g_los(e['x'], e['y'], p['x'], p['y'])):
                a = best[1]
                ang = bearing(a['x'] - e['x'], a['y'] - e['y']) + random.uniform(-6, 6)
                mx, my = vec(ang, 40)
                vx, vy = vec(ang, 330)
                g['bullets'].append(dict(x=e['x'] + mx, y=e['y'] + my, vx=vx, vy=vy, own='e', dmg=3, life=1.1, ign=self.g_ign(e['x'], e['y'])))
                e['flash'] = 0.06
                e['acd'] = random.uniform(1.0, 1.7)
            else:
                e['acd'] = 0.6

    def lz_bullet_hits_ally(self, b):
        for a in self.g['allies']:
            if not a['down'] and not a['kia'] and dist(b['x'], b['y'], a['x'], a['y']) < 12:
                self.lz_hurt_ally(a, int(b['dmg']))
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25, col=(255, 120, 90), drag=2)
                return True
        return False

    def lz_bullet_hits_bunker(self, b, cover):
        bk = cover.get('bunker')
        if bk is None:
            return
        if b['own'] in ('p', 'a'):
            self.lz_bunker_damage(bk, b['dmg'] * 0.35)

    def lz_nade(self, x, y, R, own):
        g = self.g
        if own == 'p':
            for b in g['lz']['bunkers']:
                d = dist(x, y, b['x'], b['y'])
                if b['alive'] and d < R + 20:
                    self.lz_bunker_damage(b, 7.0 * self.up_dmg() * (1 - 0.35 * d / (R + 20)))
        else:
            for a in g['allies']:
                d = dist(x, y, a['x'], a['y'])
                if d < R and not a['down'] and not a['kia']:
                    self.lz_hurt_ally(a, int(14 * (1 - 0.6 * d / R)))

    # ------------------------------------------------------------------ fases
    def lz_update(self, dt, alive, keys):
        g = self.g
        lz = g['lz']
        p = g['p']
        if g['phase'] != 'play':
            return
        lz['stage_t'] += dt
        lz['say_t'] = max(0.0, lz['say_t'] - dt)
        for c in lz['calls']:
            c[3] -= dt
        lz['calls'] = [c for c in lz['calls'] if c[3] > 0]
        self.lz_weather(dt)
        self.lz_shells(dt)
        self.lz_cover_fire(dt)
        self.lz_bunkers_update(dt, alive)
        self.lz_allies_update(dt, alive)
        self.lz_revive_update(dt, alive, keys)
        if g['alerts'] != lz['last_alerts']:
            lz['last_alerts'] = g['alerts']
            if lz['stage'] < 2 and lz['say_t'] <= 0:
                lz['say_t'] = 6.0
                self.lz_say('DÍAZ', '¡Nos descubrieron! ¡Cubrimos!', (255, 190, 130))
        if lz['stage'] == 0:
            if all(not b['alive'] for b in lz['bunkers']):
                g['tleft'] += 15.0
                self.gpop('+15 s', p['x'], p['y'] - 50, (140, 255, 200))
                self.lz_set_stage(1)
                self.banner('PLAYA ASEGURADA', 'Infiltrate tierra adentro hasta la antena (centro de la isla)', (120, 255, 190), 3.2)
                self.lz_say('RAMOS', 'Playa despejada. Avanzamos con cuidado.')
            elif dist(p['x'], p['y'], W / 2, H / 2) < g['R'] * 0.5:
                self.lz_set_stage(1)
                self.banner('LÍNEA DE BÚNKERES SUPERADA', 'Seguí hasta la antena sin ser detectado', (255, 220, 120), 3.0)
                self.lz_say('LUNA', 'Los búnkeres quedan atrás. Silencio.')
        elif lz['stage'] == 2:
            self.lz_defense(dt, alive)
        elif lz['stage'] == 3:
            self.lz_extract(dt, alive)
        if lz['stage'] >= 2:
            g['alert_t'] = 0.0

    def lz_install_done(self):
        """La antena quedó instalada: empieza la transmisión y hay que defender la posición."""
        g = self.g
        lz = g['lz']
        lz['ghost'] = g['alerts'] == 0
        lz['t_install'] = max(0.0, g['tleft'])
        g['inst'] = 0.0
        lz['def_clock'], lz['def_prog'], lz['def_idx'] = 0.0, 0.0, 0
        lz['def_dur'] = 22.0
        self.lz_set_stage(2)
        for e in g['enemies']:
            if e['state'] != 'combat':
                e['state'], e['excl'], e['det'] = 'combat', 1.0, 1.0
        self.audio.play('alarm', .6)
        self.shake = max(self.shake, 8)
        g['slow'] = 0.5
        self.banner('¡ANTENA TRANSMITIENDO!', 'Defendé la posición %d segundos: quedate cerca de la antena' % lz['def_dur'], (110, 230, 255), 3.6)
        self.lz_say('RAMOS', '¡Señal enviada! ¡Nos van a caer encima!', (255, 210, 130))

    def lz_def_wave(self, i):
        g = self.g
        n = min(7, 3 + self.wave // 2 + (1 if i == 2 else 0))
        idxs = random.sample(range(3), 2 if i == 1 else 1) if i != 2 else [0, 1, 2]
        for k in range(n):
            kind = 'gren' if (i == 2 and k == 0 and self.wave >= 2) else 'rifle'
            self.spawn_ground_enemy(kind, idxs[k % len(idxs)])
        g['total'] += n
        a = g['angs'][idxs[0]]
        deg = math.degrees(math.atan2(math.sin(a), math.cos(a))) % 360
        self.lz_say('LUNA', '¡Llegan lanchas por el %s!' % COMPASS[int(((deg + 22.5) % 360) // 45)], (255, 190, 130))
        self.audio.play('alarm', .3)

    def lz_defense(self, dt, alive):
        g = self.g
        lz = g['lz']
        p = g['p']
        lz['def_clock'] += dt
        while lz['def_idx'] < len(DEF_TIMES) and lz['def_clock'] >= DEF_TIMES[lz['def_idx']]:
            self.lz_def_wave(lz['def_idx'])
            lz['def_idx'] += 1
        near = alive and dist(p['x'], p['y'], W / 2, H / 2) < 150
        if near:
            lz['def_prog'] += dt
            lz['far_t'] = 0.0
        else:
            lz['def_prog'] = max(0.0, lz['def_prog'] - dt * 0.5)
            lz['far_t'] += dt
            if alive and lz['far_t'] > 2.0 and lz['say_t'] <= 0:
                lz['say_t'] = 5.0
                self.toast('¡La señal se pierde! Volvé a la antena', (255, 120, 100))
        if int(lz['def_clock'] * 2) != int((lz['def_clock'] - dt) * 2) and random.random() < 0.35:
            self.fx.add('glow', W / 2 + random.uniform(-40, 40), H / 2 + random.uniform(-40, 40), life=.25, r0=8, r1=26, col=(120, 230, 255))
        if lz['def_prog'] >= lz['def_dur']:
            self.lz_start_extract()

    def lz_start_extract(self):
        g = self.g
        self.lz_set_stage(3)
        g['tleft'] = EXTRACT_TIME
        self.add_score(500)
        self.audio.play('win', .7)
        self.shake = max(self.shake, 8)
        g['slow'] = 0.5
        for e in g['enemies']:
            if e['state'] != 'combat':
                e['state'], e['excl'], e['det'] = 'combat', 1.0, 1.0
        n = min(6, 2 + self.wave // 2)
        for i in range(3):
            for _ in range(n // 3 + (1 if i < n % 3 else 0)):
                self.spawn_ground_enemy('rifle', i)
        g['total'] += n
        g['crates'].append(dict(x=W / 2 + 40, y=H / 2 + 36, t=0.0, kind='med'))
        g['crates'].append(dict(x=W / 2 - 40, y=H / 2 + 36, t=0.0, kind='gren'))
        self.banner('¡ANTENA OPERATIVA! +500', '¡Volvé a la lancha antes de que se acabe el tiempo!', (120, 255, 160), 3.6)
        self.lz_say('RAMOS', '¡Transmisión completa! ¡A la lancha, ya!', (255, 220, 130))

    def lz_extract(self, dt, alive):
        g = self.g
        p = g['p']
        g['tleft'] -= dt
        if g['tleft'] < 10 and int(g['tleft']) != int(g['tleft'] + dt):
            self.audio.play('blip', .45)
        bx, by = g['spawn'][0], g['spawn'][1] + 20
        if alive and dist(p['x'], p['y'], bx, by) < 70:
            self.lz_finish(True)
        elif g['tleft'] <= 0:
            g['tleft'] = 0.0
            g['phase'], g['fail'], g['pt'] = 'result', True, 0.0
            self.audio.play('lose', .6)
            self.banner('¡LA LANCHA SE FUE!', 'No llegaste a tiempo a la extracción', (255, 80, 70), 3.0)

    def lz_finish(self, ok):
        g = self.g
        lz = g['lz']
        g['phase'], g['fail'], g['pt'] = 'result', not ok, 0.0
        if not ok:
            return
        allies_ok = sum(1 for a in g['allies'] if not a['kia'])
        lines = []
        bonus = 300
        lines.append(('Bajas enemigas', '%d' % g['kills'], 0))
        if lz['ghost']:
            bonus += 800
            lines.append(('Infiltración perfecta', 'FANTASMA', 800))
        else:
            bonus += 300
            lines.append(('Alarmas disparadas', '%d' % g['alerts'], 300))
        if g['takedowns']:
            lines.append(('Noqueos silenciosos', '%d' % g['takedowns'], 120 * g['takedowns']))
            bonus += 120 * g['takedowns']
        if lz['bunker_kills']:
            lines.append(('Búnkeres destruidos', '%d' % lz['bunker_kills'], 0))
        t_bonus = min(int(lz['t_install']), 90) * 3
        lines.append(('Tiempo sobrante', '%ds' % int(lz['t_install']), t_bonus))
        bonus += t_bonus
        lines.append(('Escuadra a salvo', '%d/%d' % (allies_ok, len(g['allies'])), 150 * allies_ok))
        bonus += 150 * allies_ok
        lz['stats'] = lines
        lz['bonus'] = bonus
        self.add_score(bonus)
        self.audio.play('win', .7)
        self.banner('¡ISLA ASEGURADA!' if lz['ghost'] else '¡MISIÓN CUMPLIDA!', 'Escuadra a salvo: %d/%d   Bonus +%d' % (allies_ok, len(g['allies']), bonus), (120, 255, 160), 3.6)

    # ------------------------------------------------------------------ clima y ambiente
    def lz_weather(self, dt):
        lz = self.g['lz']
        lz['white'] = max(0.0, lz['white'] - dt * 2.2)
        if lz['wx'] != 'tormenta':
            return
        lz['bolt'] -= dt
        if lz['bolt'] <= 0:
            lz['bolt'] = random.uniform(4, 10)
            lz['white'] = 1.0
            lz['thunder'].append(random.uniform(0.3, 1.2))
        for i in range(len(lz['thunder'])):
            lz['thunder'][i] -= dt
        if any(t <= 0 for t in lz['thunder']):
            lz['thunder'] = [t for t in lz['thunder'] if t > 0]
            self.audio.play('boom_l', .25)
            self.shake = max(self.shake, 3)

    def lz_light(self, r):
        cache = self.__dict__.setdefault('_lz_lights', {})
        s = cache.get(r)
        if s is None:
            n, half = 24, max(8, r // 2)
            sm = pygame.Surface((half * 2, half * 2), pygame.SRCALPHA)
            for i in range(n):
                k = 1 - i / n
                a = int(255 * (1 - k) ** 1.2)
                pygame.draw.circle(sm, (0, 0, 0, a), (half, half), max(1, int(half * k)))
            s = cache[r] = pygame.transform.smoothscale(sm, (r * 2, r * 2))
        return s

    def lz_draw_ambient(self, cv, cx_, cy_):
        g = self.g
        lz = g['lz']
        wx = lz['wx']
        if wx == 'amanecer':
            cv.fill((30, 13, 0), special_flags=pygame.BLEND_RGB_ADD)
        elif wx == 'tormenta':
            self.dim(cv, 30)
            t = self.t
            for i, (rx, ry, sp) in enumerate(lz['rain']):
                x = (rx + t * 70 * sp) % W
                y = (ry + t * 800 * sp) % H
                pygame.draw.line(cv, (150, 172, 200), (x, y), (x - 2, y - 17 * sp), 1)
        elif wx == 'noche':
            ov = self.__dict__.get('_lz_ov')
            if ov is None:
                ov = self._lz_ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((6, 10, 36, 168))
            p = g['p']
            lights = [(p['x'] - cx_, p['y'] - cy_, 300)]
            lights += [(a['x'] - cx_, a['y'] - cy_, 130) for a in g['allies'] if not a['kia']]
            lights += [(e['x'] - cx_, e['y'] - cy_, 110) for e in g['enemies'] if e['flash'] > 0][:10]
            lights += [(b['x'] - cx_, b['y'] - cy_, 120) for b in lz['bunkers'] if b['alive'] and (b['flash'] > 0 or b['tele'] > 0)]
            lights.append((W // 2 - cx_, H // 2 - cy_, 120))
            for x, y, r in lights:
                if -r < x < W + r and -r < y < H + r:
                    ov.blit(self.lz_light(r), (int(x) - r, int(y) - r), special_flags=pygame.BLEND_RGBA_SUB)
            cv.blit(ov, (0, 0))
        if lz['white'] > 0:
            v = int(150 * min(1.0, lz['white']))
            cv.fill((v, v, v + 10 if v < 245 else v), special_flags=pygame.BLEND_RGB_ADD)

    # ------------------------------------------------------------------ dibujo del mundo
    def lz_draw_world(self, cv, cx_, cy_):
        g = self.g
        lz = g['lz']
        for b in lz['bunkers']:
            sx, sy = b['x'] - cx_, b['y'] - cy_
            if not (-120 < sx < W + 120 and -120 < sy < H + 120):
                continue
            if not b['alive']:
                draw_circ(cv, sx, sy, 32, (22, 20, 18), 160)
                draw_circ(cv, sx, sy, 20, (56, 52, 48), 170)
                continue
            if lz['stage'] == 0 and lz['intro'] <= 0:
                red = b['tele'] > 0.05 or b['burst'] > 0
                self.draw_cone(cv, sx, sy, b['ha'], 338, 40, (255, 70, 60) if red else (255, 200, 90))
            draw_circ(cv, sx + 5, sy + 7, 31, (0, 0, 0), 80)
            hit = b['hit'] > 0
            pygame.draw.circle(cv, (150, 154, 150) if hit else (98, 102, 100), (int(sx), int(sy)), 29)
            pygame.draw.circle(cv, (210, 214, 210) if hit else (132, 136, 132), (int(sx), int(sy)), 25)
            pygame.draw.circle(cv, (86, 90, 88), (int(sx), int(sy)), 25, 2)
            for k in range(8):
                a = 6.2832 * k / 8
                pygame.draw.line(cv, (110, 114, 112), (sx + math.cos(a) * 14, sy + math.sin(a) * 14), (sx + math.cos(a) * 24, sy + math.sin(a) * 24), 1)
            ex, ey = vec(b['ha'], 34)
            mx, my = vec(b['ha'], 16)
            pygame.draw.line(cv, (24, 26, 30), (sx + mx, sy + my), (sx + ex, sy + ey), 6)
            pygame.draw.circle(cv, (50, 54, 60), (int(sx), int(sy)), 12)
            pygame.draw.circle(cv, (24, 26, 30), (int(sx), int(sy)), 12, 2)
            if b['flash'] > 0:
                ex, ey = vec(b['ha'], 40)
                glow(cv, sx + ex, sy + ey, 26, (255, 210, 120))
            if b['hp'] < b['max']:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 20, sy - 42, 40, 6))
                pygame.draw.rect(cv, (240, 120, 70), (sx - 19, sy - 41, int(38 * clamp(b['hp'] / b['max'], 0, 1)), 4))
            if lz['stage'] == 0:
                self.text(cv, 'BÚNKER', self.f_s, (255, 190, 140), sx, sy - 58, 'c', alpha=200)
        for s in lz['shells']:
            sx, sy = s['x'] - cx_, s['y'] - cy_
            k = s['t'] / 0.9
            draw_circ(cv, sx, sy, 40, (255, 90, 70), 20 + 40 * k, 2)
            yy = sy - 380 * (1 - k)
            pygame.draw.line(cv, (240, 240, 230), (sx, yy - 20), (sx, yy), 3)
        if lz['stage'] == 2:
            pad = (W // 2 - cx_, H // 2 - cy_)
            pr = clamp(lz['def_prog'] / lz['def_dur'], 0, 1)
            for j in range(3):
                ph = (self.t * 0.9 + j / 3) % 1
                draw_circ(cv, pad[0], pad[1], 30 + ph * 150, (110, 230, 255), 140 * (1 - ph), 2)
            draw_circ(cv, pad[0], pad[1], 150, (110, 230, 255), 36, 1)
            pygame.draw.arc(cv, (120, 255, 200), (pad[0] - 66, pad[1] - 66, 132, 132), math.pi / 2, math.pi / 2 + 6.2832 * pr, 6)
        if lz['stage'] == 3:
            bx, by = g['spawn'][0] - cx_, g['spawn'][1] + 20 - cy_
            pul = 0.5 + 0.5 * math.sin(self.t * 6)
            draw_circ(cv, bx, by, 70, (120, 255, 160), 30 + 50 * pul, 2)
            glow(cv, bx, by, 60, (120, 255, 160), 0.4 + 0.3 * pul)
            self.text(cv, 'EXTRACCIÓN', self.f_s, (150, 255, 190), bx, by - 94, 'c')

    def lz_draw_ally(self, cv, a, sx, sy):
        if a['kia']:
            self.blit_soldier(cv, 'a', sx, sy, a['h'], 0, dead=True)
            return
        if a['down']:
            self.blit_soldier(cv, 'a', sx, sy, a['h'], 0, dead=True)
            pul = 0.5 + 0.5 * math.sin(self.t * 6)
            draw_circ(cv, sx, sy, 34 + 3 * pul, (255, 120, 100), 100 + 80 * pul, 2)
            self.text(cv, '%s  %ds' % (a['name'], math.ceil(a['bleed'])), self.f_s, (255, 150, 130), sx, sy - 40, 'c')
            p = self.g['p']
            if dist(a['x'], a['y'], p['x'], p['y']) < 70:
                self.text(cv, 'MANTENÉ E: AUXILIAR', self.f_s, (255, 240, 170), sx, sy - 58, 'c')
            if a['rev'] > 0:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 20, sy + 22, 40, 7))
                pygame.draw.rect(cv, (120, 255, 190), (sx - 19, sy + 23, int(38 * a['rev']), 5))
            return
        self.blit_soldier(cv, 'a', sx, sy, a['h'], int(a['ph']) % 4 if a['mv'] else 0, a['hit'])
        if a['flash'] > 0:
            fx_, fy_ = vec(a['h'], 46)
            glow(cv, sx + fx_, sy + fy_, 20, (255, 230, 150))
        if self.g['lz']['intro'] <= 0:
            self.text(cv, a['name'], self.f_s, ALLY_COL, sx, sy - 34, 'c', alpha=170)
        if a['hp'] < a['max']:
            pygame.draw.rect(cv, (8, 12, 24), (sx - 14, sy - 24, 28, 5))
            pygame.draw.rect(cv, (110, 220, 150), (sx - 13, sy - 23, int(26 * a['hp'] / a['max']), 3))

    # ------------------------------------------------------------------ HUD
    def lz_draw_hud(self, cv):
        g = self.g
        lz = g['lz']
        p = g['p']
        t = self.t
        st = lz['stage']
        objs = ('Despejá la playa: destruí los 2 búnkeres (granadas) o avanzá tierra adentro',
                'Infiltrate hasta la antena (centro) y mantené E para instalarla',
                'Defendé la antena mientras transmite: no te alejes',
                '¡Volvé a la lancha antes de que se acabe el tiempo!')
        lab = 'FASE %d/4 · %s' % (st + 1, STAGE_NAMES[st])
        w1, w2 = self.f_s.size(lab)[0], self.f_s.size(objs[st])[0]
        x0 = W // 2 - (w1 + w2 + 44) // 2
        self.panel(cv, (x0, 180, w1 + w2 + 44, 30), 170)
        self.text(cv, lab, self.f_s, (255, 220, 120), x0 + 12, 187)
        self.text(cv, objs[st], self.f_s, (210, 230, 250), x0 + 32 + w1, 187)
        # escuadra
        self.panel(cv, (14, 72, 250, 46 + 20 * len(g['allies'])), 150)
        self.text(cv, 'ESCUADRA', self.f_s, (170, 200, 230), 26, 76)
        for i, a in enumerate(g['allies']):
            y = 98 + i * 20
            self.text(cv, a['name'], self.f_s, ALLY_COL if not a['kia'] else (120, 120, 120), 26, y)
            if a['kia']:
                self.text(cv, 'BAJA', self.f_s, (150, 100, 100), 150, y)
            elif a['down']:
                self.text(cv, 'HERIDO %ds' % math.ceil(a['bleed']), self.f_s, (255, 130, 110) if int(t * 4) % 2 else (255, 200, 120), 100, y)
            else:
                pygame.draw.rect(cv, (8, 12, 24), (100, y + 2, 150, 10))
                pygame.draw.rect(cv, (110, 220, 150), (101, y + 3, int(148 * a['hp'] / a['max']), 8))
        # llamadas por radio
        for i, (who, txt, col, life) in enumerate(lz['calls']):
            al = int(255 * clamp(life * 2, 0, 1))
            y = 222 + i * 22
            self.text(cv, who + ':', self.f_s, col, W // 2 - 200, y, alpha=al)
            self.text(cv, txt, self.f_s, (240, 244, 250), W // 2 - 200 + 12 + self.f_s.size(who + ':')[0], y, alpha=al)
        if st == 2:
            pr = clamp(lz['def_prog'] / lz['def_dur'], 0, 1)
            far = lz['far_t'] > 0.4
            self.bar(cv, W // 2 - 210, 292, 420, 26, pr, (240, 90, 80) if far else (110, 230, 255),
                     '¡VOLVÉ A LA ANTENA!' if far else 'TRANSMITIENDO %d%%' % int(pr * 100))
        elif st == 3 and not p['dead']:
            bx, by = g['spawn'][0], g['spawn'][1] + 20
            d = dist(p['x'], p['y'], bx, by)
            ang = bearing(bx - p['x'], by - p['y'])
            ax, ay = vec(ang, 74)
            sx, sy = p['x'] - g['cam'][0] + ax, p['y'] - g['cam'][1] + ay
            hx, hy = vec(ang, 12)
            lx, ly = vec(ang + 140, 9)
            rx, ry = vec(ang - 140, 9)
            pygame.draw.polygon(cv, (120, 255, 160), [(sx + hx, sy + hy), (sx + lx, sy + ly), (sx + rx, sy + ry)])
            self.text(cv, 'LANCHA %d m' % int(d / 3), self.f_s, (150, 255, 190), sx, sy + 16, 'c')
        self.text(cv, WX_LABEL[lz['wx']], self.f_s, (170, 195, 230), 26, 98 + 20 * len(g['allies']))
        # resumen final
        if g['phase'] == 'result' and not g['fail'] and lz['stats']:
            n = len(lz['stats'])
            x0, y0 = W // 2 - 220, 290
            k = clamp(g['pt'] / 0.6, 0, 1)
            self.panel(cv, (x0, y0, 440, 84 + 26 * n), int(210 * k))
            self.text(cv, 'INFORME DE MISIÓN', self.f_m, (255, 230, 140), W // 2, y0 + 8, 'c', alpha=int(255 * k))
            for i, (lab, val, pts) in enumerate(lz['stats']):
                if g['pt'] < 0.5 + 0.35 * i:
                    break
                y = y0 + 44 + 26 * i
                self.text(cv, lab, self.f_s, (200, 220, 245), x0 + 20, y)
                self.text(cv, val, self.f_s, (255, 255, 255), x0 + 270, y, 'r')
                if pts:
                    self.text(cv, '+%d' % pts, self.f_s, (130, 255, 170), x0 + 420, y, 'r')
            if g['pt'] >= 0.5 + 0.35 * n:
                self.text(cv, 'TOTAL  +%d' % lz['bonus'], self.f_m, (130, 255, 170), W // 2, y0 + 48 + 26 * n, 'c')
