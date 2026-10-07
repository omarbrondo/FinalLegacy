"""Asalto al puerto enemigo: acción lateral estilo Metal Slug."""
import math
import pygame
import random
from .common import ENEMY_PORT, FEM_CHANCE, H, PLAYER_FEMALE, PLAYER_HP, Particles, W, WIN_WAVE, clamp, dist, glow, lerp
from .pt_art import (
    PT_AX, PT_AY, build_pt_art, build_pt_bg,
    build_pt_bunker, build_pt_containers, build_pt_decor, build_pt_tank)


from .comms import PORT_LINES


class PortMixin:
    # ---------------------------------------------------------- ASALTO AL PUERTO ENEMIGO (vista lateral, estilo Metal Slug)
    PT_GR = 640          # y del suelo del muelle

    PT_LEN = 9600        # largo del nivel (más largo: 8 pantallas de combate y el jefe)

    def nearest_port(self):
        x, y, r, _s = ENEMY_PORT
        if self.port_done or self.port_tries >= 2:
            return None
        return ENEMY_PORT if dist(self.sx, self.sy, x, y) < r * 1.3 + 190 else None

    def start_port(self):
        if self.port_tries >= 2:
            self.toast('Sin intentos de asalto en esta oleada', (255, 140, 90))
            return
        self.port_tries += 1
        rnd = random.Random(self.wave * 977 + self.port_tries * 13)
        L, GR, w = self.PT_LEN, self.PT_GR, self.wave
        plats = []
        x = 700
        while x < L - 1800:
            hh = rnd.choice((1, 1, 2))
            plats.append(dict(x=x, w=rnd.choice((150, 150, 225)), top=GR - 64 * hh, h=64 * hh, ci=rnd.randrange(5)))
            x += rnd.randint(520, 780)
        ex = w // 2
        groups = []

        def grp(xt, spec, lock=False):
            groups.append(dict(x=xt, spec=spec, lock=lock, done=False, lx=0.0))
        grp(500, [('rifle', 'R'), ('rifle', 'R'), ('rifle', 'S')] + [('rifle', 'R')] * ex)
        grp(1450, [('rifle', 'R'), ('knife', 'R'), ('rifle', 'L'), ('shield', 'R')] + [('knife', 'R')] * ex)
        grp(2350, [('gren', 'R'), ('rifle', 'R'), ('rifle', 'S'), ('rifle', 'S'), ('knife', 'L')] + [('shield', 'R')] * (1 + ex // 2))
        grp(3250, [('knife', 'R'), ('flame', 'R'), ('gren', 'R'), ('rifle', 'L'), ('sniper', 'P')] + [('flame', 'R')] * (ex // 2) + [('rifle', 'R')] * ex, True)
        grp(4200, [('shield', 'R'), ('rifle', 'S'), ('rifle', 'S'), ('gren', 'R'), ('gren', 'L'), ('sniper', 'P'), ('flame', 'R')] + [('knife', 'L')] * ex, True)
        grp(5100, [('rifle', 'R')] * 3 + [('knife', 'R'), ('knife', 'L'), ('gren', 'R'), ('sniper', 'P'), ('rifle', 'S'), ('rifle', 'S')] + [('rifle', 'R')] * ex)
        grp(5900, [('shield', 'R'), ('shield', 'R'), ('flame', 'R'), ('gren', 'L'), ('gren', 'R'), ('sniper', 'P'), ('rifle', 'S'), ('rifle', 'S')] + [('flame', 'R')] * (ex // 2) + [('knife', 'L')] * ex, True)
        grp(6800, [('rifle', 'R'), ('rifle', 'L'), ('rifle', 'R'), ('rifle', 'L'), ('knife', 'R'), ('knife', 'R'), ('sniper', 'P'), ('rifle', 'S'), ('rifle', 'S'), ('rifle', 'S')] + [('shield', 'R')] * (1 + ex // 2))
        grp(7600, [('flame', 'R'), ('flame', 'R'), ('shield', 'R'), ('shield', 'R'), ('gren', 'R'), ('gren', 'L'), ('sniper', 'P'), ('sniper', 'P'), ('rifle', 'S'), ('rifle', 'S'), ('knife', 'L')] + [('knife', 'R')] * ex, True)
        grp(L - 1500, [('tank', 'R')], True)
        self.pt = dict(pfem=self.roll_player_fem(),
            plats=plats, groups=groups, cam=0.0, lock=None, t=0.0, phase='play', pt=0.0, fail=False, kills=0,
            p=dict(x=120.0, y=float(GR), vx=0.0, vy=0.0, ground=True, hp=PLAYER_HP, face=1, cd=0.0, gren=6, hmg=0.0, inv=0.0,
                   ph=0.0, crouch=False, dead=False, gcd=0.0, flash=0.0, thr=0.0, dead_t=0.0, dust=0.0),
            enemies=[], bul=[], ebul=[], nades=[], items=[], go_t=0.0, boss=None, hurt=0.0, score0=self.score,
            cas=[], corpses=[], wrecks=[], decor=[], puddles=[], barrels=[], pows=[], mort=[], freeze=0.0, taken=0, pow_n=0, rank=None)
        drnd = random.Random(self.wave * 31 + 5)
        dec = self.pt['decor']
        for lx in range(300, L, 640):
            dec.append(dict(kind='lamp', x=float(lx + drnd.randint(-60, 60))))
        for _ in range(68):
            kind = drnd.choice(('crates', 'bollard', 'sandbags', 'fence', 'fence'))
            dec.append(dict(kind=kind, x=float(drnd.randint(200, L - 200))))
        dec.sort(key=lambda d: {'fence': 0, 'lamp': 1}.get(d['kind'], 2))
        self.pt['puddles'] = [(float(drnd.randint(100, L - 100)), drnd.randint(70, 140)) for _ in range(26)]
        self.pt['barrels'] = [dict(x=float(bx), y=float(GR), hp=2, fuse=-1.0) for bx in sorted(drnd.sample(range(900, L - 1700, 60), 16))]
        for bx_, kind_ in zip((1250, 2900, 4500, 6200, 7400), ('hmg', 'gren', 'med', 'hmg', 'med')):
            self.pt['pows'].append(dict(x=float(bx_), state='tied', t=0.0, item=kind_))
        self.pt_art_init()
        for xi, kind in ((1000, 'med'), (1900, 'gren'), (2750, 'hmg'), (3700, 'med'), (4600, 'gren'), (5100, 'med'), (6300, 'med'), (7100, 'gren'), (7900, 'med')):
            self.pt['items'].append(dict(x=float(xi), y=float(GR - 30), kind=kind, t=0.0))
        for xt in (2650, 3900, 4800, 5700, 6500, 7300):
            self.pt['enemies'].append(self.pt_enemy('turret', xt, GR, -1))
        self.pt_epic_setup()
        self.fx = Particles()
        self.aim = [W / 2, 300.0]
        self.go('port')
        self.banner('¡ASALTO AL PUERTO ENEMIGO!', 'Tomá el puerto', (255, 120, 90), 3.0)
        self.say('soldado', 'Asalto al puerto. A/D para moverte, W o ESPACIO para saltar, S para agacharte, clic para disparar y G para granada.', 'info')

    def pt_enemy(self, kind, x, y, face):
        hp = {'rifle': 3, 'knife': 2, 'gren': 3, 'sniper': 4, 'shield': 6, 'flame': 5, 'turret': 12, 'tank': 70 + 24 * self.wave}[kind]
        if kind in ('rifle', 'knife', 'gren', 'shield', 'flame'):
            hp += self.wave // 3
        return dict(kind=kind, x=float(x), y=float(y), vx=0.0, vy=0.0, hp=float(hp), max=float(hp), face=face, cd=random.uniform(0.6, 1.8),
                    fem=(kind in ('rifle', 'knife', 'sniper') and random.random() < FEM_CHANCE), burst=0, bcd=0.0, tele=0.0, ph=random.uniform(0, 6), hit=0.0, ground=True, plat=None, state='walk',
                    st=0.0, atk=0, mcd=0.0, ph0=random.uniform(0, 6), kneel=random.random() < 0.4, thr=0.0, slash=0.0, flash=0.0,
                    moving=False, recoil=0.0, fire=0.0, fcd=0.0, para=False, stag=0.0)

    def pt_spawn_group(self, g):
        pt = self.pt
        cam = pt['cam']
        for kind, side in g['spec']:
            if kind == 'tank':
                e = self.pt_enemy('tank', cam + W + 200, self.PT_GR, -1)
                e['state'] = 'enter'
                e['variant'] = 'heli' if self.wave % 2 == 0 else 'tank'
                if e['variant'] == 'heli':
                    e['y'] = self.PT_GR - 150.0
                    e['rot'] = 0.0
                    e['hp'] = e['max'] = e['max'] * 0.8
                pt['boss'] = e
                pt['enemies'].append(e)
                self.audio.play('alarm')
                if e['variant'] == 'heli':
                    self.banner('¡HELICÓPTERO DE ASALTO!', 'Disparale hacia arriba', (255, 90, 70), 2.6)
                    self.say('soldado', '¡Helicóptero de asalto! Disparale hacia arriba y cubrite de los misiles.', 'bad')
                    self.say('jefe_puerto_heli', PORT_LINES['heli'][0], 'bad', pose='', name='PILOTO ENEMIGO')
                else:
                    self.banner('¡TANQUE DE PUERTO!', 'Tanque enemigo', (255, 90, 70), 2.6)
                    self.say('soldado', '¡Tanque en el puerto! Saltá sus proyectiles y no pares de disparar.', 'bad')
                    self.say('jefe_puerto_tanque', PORT_LINES['tank'][0], 'bad', pose='', v=self.wave // 2 % 2 + 1, name='COMANDANTE DEL TANQUE')
                continue
            if kind == 'sniper':
                ahead = [pl for pl in pt['plats'] if cam + 200 < pl['x'] < cam + W - 100] or pt['plats'][:1]
                pl = random.choice(ahead)
                e = self.pt_enemy('sniper', pl['x'] + pl['w'] / 2, pl['top'], -1)
                e['plat'] = pl
            elif side == 'S':
                e = self.pt_enemy(kind, cam + random.uniform(160, W - 160), -70.0, -1)
                e['para'] = True
            else:
                sx = cam + W + 40 + random.uniform(0, 160) if side == 'R' else cam - 40 - random.uniform(0, 120)
                e = self.pt_enemy(kind, sx, self.PT_GR, -1 if side == 'R' else 1)
            g.setdefault('ids', []).append(e)
            pt['enemies'].append(e)

    def pt_jump(self):
        p = self.pt['p']
        if p['ground'] and not p['dead'] and self.pt['phase'] == 'play':
            p['vy'] = -760.0
            p['ground'] = False
            self.audio.play('blip', .5)

    def pt_throw(self):
        pt = self.pt
        p = pt['p']
        if p['dead'] or p['gren'] <= 0 or p['gcd'] > 0 or pt['phase'] != 'play':
            return
        p['gren'] -= 1
        p['gcd'] = 0.5
        p['thr'] = 0.32
        sx = p['x'] - pt['cam']
        a = math.atan2(self.aim[1] - (p['y'] - 50), self.aim[0] - sx)
        sp = clamp(dist(sx, p['y'] - 50, self.aim[0], self.aim[1]) * 1.45, 260, 640)
        pt['nades'].append(dict(x=p['x'], y=p['y'] - 56, vx=math.cos(a) * sp, vy=math.sin(a) * sp - 120, t=0.0, own='p'))
        self.audio.play('blip', .8)

    def pt_hurt(self, dmg):
        pt = self.pt
        p = pt['p']
        if p['dead'] or p['inv'] > 0 or pt['phase'] != 'play':
            return
        p['hp'] -= dmg
        pt['taken'] += dmg
        p['inv'] = 0.55
        pt['hurt'] = 0.4
        self.shake = max(self.shake, 4 + dmg * 0.3)
        self.audio.play('hit', .5)
        self.pop('-%d' % dmg, p['x'] - pt['cam'], p['y'] - 80, (255, 110, 100))

    def pt_land(self, o, dt):
        """Gravedad y suelo/plataformas (de un solo sentido) para jugador y enemigos."""
        pt = self.pt
        prev = o['y']
        o['vy'] += 1900 * dt
        o['y'] += o['vy'] * dt
        o['ground'] = False
        if o['y'] >= self.PT_GR:
            o['y'], o['vy'], o['ground'] = float(self.PT_GR), 0.0, True
            return
        if o['vy'] >= 0:
            for pl in pt['plats']:
                if pl['x'] - 8 < o['x'] < pl['x'] + pl['w'] + 8 and prev <= pl['top'] + 6 and o['y'] >= pl['top']:
                    o['y'], o['vy'], o['ground'] = float(pl['top']), 0.0, True
                    return

    def pt_kill(self, e, blast=False):
        pt = self.pt
        if e not in pt['enemies']:
            return
        pt['enemies'].remove(e)
        pt['kills'] += 1
        big = e['kind'] in ('tank', 'turret')
        pts = {'rifle': 100, 'knife': 100, 'gren': 150, 'sniper': 200, 'shield': 150, 'flame': 200, 'turret': 250, 'tank': 2000}[e['kind']]
        if e['kind'] == 'tank' and e.get('variant') != 'heli':
            pt['wrecks'].append(dict(kind='tank', x=e['x'], y=e['y']))
            pt['freeze'] = 0.9
        elif e['kind'] == 'turret':
            pt['wrecks'].append(dict(kind='turret', x=e['x'], y=e['y']))
        else:
            c = dict(kind=e['kind'], fem=e.get('fem', False), x=e['x'], y=e['y'], face=e['face'], t=0.0, vx=-e['face'] * random.uniform(60, 150), air=False, vy=0.0, spin=0.0)
            if e['para']:                                   # muerto en el aire: cae al piso y el paracaídas se desinfla
                c.update(air=True, vy=40.0, vx=0.0, spin=0.0)
                pt['chutes'].append(dict(x=e['x'], y=e['y'] - 160, t=0.0, vx=random.uniform(-16, 16)))
            elif blast or e['kind'] == 'flame':
                c.update(air=True, vy=-random.uniform(380, 520), vx=(1 if e['x'] > pt['p']['x'] else -1) * random.uniform(120, 280), spin=random.uniform(-560, 560))
            pt['corpses'].append(c)
        if not blast or e['kind'] != 'tank':
            self.fx.explode(e['x'], e['y'] - (50 if e['kind'] == 'tank' else 24), 2.0 if e['kind'] == 'tank' else (1.1 if big else (0.7 if blast else 0.45)), big or blast)
        self.audio.play('boom_s', .6 if not big else .9)
        self.add_score(pts)
        self.pop('+%d' % pts, e['x'] - pt['cam'], e['y'] - 78, (255, 232, 150))
        self.pt_combo_kill(e)
        if e['kind'] in ('rifle', 'gren', 'knife', 'shield', 'flame') and random.random() < 0.22 and not e['para']:
            pt['items'].append(dict(x=e['x'], y=e['y'] - 30, kind=random.choice(('med', 'gren', 'gren', 'shot', 'rkt')), t=0.0))
        if e['kind'] == 'flame':
            self.pt_blast(e['x'], e['y'] - 30, 80, 4, 14, 'b')
        if e['kind'] == 'tank':
            pt['boss'] = None
            if e.get('variant') == 'heli':
                self.say('jefe_puerto_heli', PORT_LINES['heli'][1], 'warn', pose='bad', name='PILOTO ENEMIGO')
            else:
                self.say('jefe_puerto_tanque', PORT_LINES['tank'][1], 'warn', pose='bad', v=self.wave // 2 % 2 + 1, name='COMANDANTE DEL TANQUE')
            self.shake = 22
            for _ in range(6):
                self.fx.explode(e['x'] + random.uniform(-110, 110), e['y'] - random.uniform(10, 90), 1.4, True)

    def pt_hit_enemy(self, e, dmg, blast=False):
        e['hp'] -= dmg
        e['hit'] = 0.1
        e['stag'] = 0.1
        if e['kind'] not in ('tank', 'turret') and not blast:
            e['x'] += (1 if e['x'] > self.pt['p']['x'] else -1) * 3
        if e['hp'] <= 0:
            self.pt_kill(e, blast)

    def pt_blast(self, x, y, R, dmg_e, dmg_p, own='p'):
        """Explosión: daña a enemigos (si no es de ellos), al jugador y enciende barriles cercanos."""
        pt = self.pt
        p = pt['p']
        self.fx.explode(x, y, R / 95.0, True)
        self.audio.play('boom_s', .8)
        self.shake = max(self.shake, 7)
        if own != 'm':
            for e in pt['enemies'][:]:
                d = dist(x, y, e['x'], e['y'] - 28) - (60 if e['kind'] == 'tank' else 0)
                if d < R and (own != 'e'):
                    self.pt_hit_enemy(e, dmg_e * (1.3 if e['kind'] == 'tank' else 1.0) * (1 - 0.35 * max(0.0, d) / R), True)
        d = dist(x, y, p['x'], p['y'] - 28)
        if not p['dead'] and d < R * (0.75 if own == 'p' else 1.0):
            self.pt_hurt(int(dmg_p * (1 - 0.5 * d / R)))
        for b in pt['barrels']:
            if b['fuse'] < 0 and dist(x, y, b['x'], b['y'] - 20) < R * 0.95:
                b['fuse'] = 0.14

    def pt_box(self, e):
        w, h = {'tank': (280, 140), 'turret': (62, 60), 'sniper': (28, 66), 'shield': (40, 72), 'flame': (34, 72)}.get(e['kind'], (28, 72))
        return e['x'] - w / 2, e['y'] - h, w, h

    def pt_ebullet(self, x, y, ang, sp, dmg, life=1.6):
        a = math.radians(ang)
        self.pt['ebul'].append(dict(x=x, y=y, vx=math.cos(a) * sp, vy=math.sin(a) * sp, dmg=dmg, life=life, big=dmg >= 20))

    def pt_casing(self, x, y, face):
        self.pt['cas'].append(dict(x=x, y=y, vx=-face * random.uniform(40, 120), vy=-random.uniform(140, 240), rot=random.uniform(0, 6), vr=random.uniform(-14, 14), t=0.0))

    def pt_ai(self, e, dt):
        pt = self.pt
        p = pt['p']
        alive = not p['dead']
        cam = pt['cam']
        k = e['kind']
        e['cd'] -= dt
        e['hit'] = max(0.0, e['hit'] - dt)
        e['flash'] = max(0.0, e['flash'] - dt)
        e['slash'] = max(0.0, e['slash'] - dt)
        e['recoil'] = max(0.0, e['recoil'] - 70 * dt)
        dx = p['x'] - e['x']
        ad = abs(dx)
        if alive and k != 'tank':
            e['face'] = 1 if dx > 0 else -1
        # fuera de la pantalla actúan poco (solo caminan hacia el jugador)
        onscreen = cam - 60 < e['x'] < cam + W + 60
        py = p['y'] - 30
        if e['para']:
            e['y'] += 150 * dt
            e['x'] += math.sin(pt['t'] * 1.7 + e['ph0']) * 22 * dt
            fl_ = self.pt_floor(e['x'], e['y'] - 4)
            if e['y'] >= fl_:
                e['y'], e['vy'], e['para'] = float(fl_), 0.0, False
                for _ in range(6):
                    self.fx.add('smoke', e['x'] + random.uniform(-16, 16), e['y'] - 3, random.uniform(-60, 60), random.uniform(-26, -6), 0.6, 4, 12, (190, 170, 150), drag=2)
            return
        e['stag'] = max(0.0, e['stag'] - dt)
        if k in ('rifle', 'knife', 'gren', 'shield', 'flame'):
            self.pt_land(e, dt)
            if k == 'knife':
                sp = self.pt_knife_move(e, dt, ad, alive)
            elif k == 'shield':
                sp = 78.0 if ad > 70 else 0.0
            elif k == 'flame':
                sp = 88.0 if ad > 215 else (-60.0 if ad < 130 else 0.0)
                if e['fire'] > 0:
                    sp = 0.0
            elif k == 'rifle':
                sp = 95.0 if ad > 440 else (-70.0 if ad < 230 else 0.0)
            else:
                sp = 80.0 if ad > 560 else (-90.0 if ad < 330 else 0.0)
            if e['thr'] > 0:
                sp = 0.0
            if not onscreen:
                sp = 110.0
            e['x'] += sp * (1 if dx > 0 else -1) * dt
            if pt['lock'] is not None:
                e['x'] = clamp(e['x'], cam - 30, cam + W - 40)
            e['moving'] = sp != 0
            e['ph'] += abs(sp) * dt / 12.7
            if k == 'knife':
                pass
            elif k == 'shield':
                if ad < 84 and abs(p['y'] - e['y']) < 60 and e['cd'] <= 0 and alive:
                    e['cd'] = 1.1
                    e['slash'] = 0.3
                    self.pt_hurt(16)
                    p['vx'] += 0
                    self.audio.play('hit', .4)
            elif k == 'flame':
                if onscreen and alive:
                    if e['fire'] > 0:
                        e['fire'] -= dt
                        e['fcd'] -= dt
                        gy = e['y'] - 44
                        ang = math.atan2((p['y'] - 40) - gy, dx)
                        ang = clamp(ang, -0.6, 0.6) if dx > 0 else (ang if abs(ang) > 2.54 else math.copysign(2.54, ang))
                        for _ in range(3):
                            sp_ = random.uniform(200, 330)
                            a_ = ang + random.uniform(-0.12, 0.12)
                            self.fx.add('glow', e['x'] + math.cos(ang) * 44, gy + math.sin(ang) * 44, math.cos(a_) * sp_, math.sin(a_) * sp_ - 20, 0.42, 9, 26,
                                        random.choice(((255, 170, 60), (255, 120, 40), (255, 220, 120))), drag=1.4)
                        if random.random() < 0.3:
                            self.fx.add('smoke', e['x'] + e['face'] * 150, gy - 20, e['face'] * 40, -50, 0.9, 8, 22, (40, 36, 36))
                        if e['fcd'] <= 0:
                            e['fcd'] = 0.2
                            if ad < 240 and abs((p['y'] - 36) - gy) < 46:
                                self.pt_hurt(4)
                        e['flash'] = 0.06
                        if e['fire'] <= 0:
                            e['cd'] = random.uniform(1.8, 2.6)
                    elif e['cd'] <= 0 and ad < 280:
                        e['fire'] = 1.4
                        self.audio.play('launch', .3)
            elif onscreen and alive:
                if e['thr'] > 0:
                    e['thr'] -= dt
                    if e['thr'] <= 0:
                        T = clamp(ad / 380.0, 0.8, 1.5)
                        vx = dx / T
                        vy = (py - (e['y'] - 56) - 0.5 * 900 * T * T) / T
                        pt['nades'].append(dict(x=e['x'], y=e['y'] - 56, vx=vx, vy=vy, t=0.0, own='e'))
                elif e['burst'] > 0:
                    e['bcd'] -= dt
                    if e['bcd'] <= 0:
                        e['burst'] -= 1
                        e['bcd'] = 0.13
                        pv = e.get('pv') or (e['x'], e['y'] - (50 if (e['kneel'] and not e['moving']) else 67))
                        mx_, my_, ux, uy = self.pt_muzzle(k, pv, e['face'], p['x'], py)
                        ang = math.degrees(math.atan2(uy, ux)) + random.uniform(-6, 6)
                        self.pt_ebullet(mx_, my_, ang, 560, 7)
                        e['flash'] = 0.06
                        self.pt_casing(pv[0] + ux * 22, pv[1] + uy * 22, e['face'])
                        self.audio.play('mg', .15)
                elif e['cd'] <= 0 and k == 'rifle' and ad < 700:
                    e['cd'] = random.uniform(1.3, 2.3)
                    e['burst'], e['bcd'] = random.choice((2, 3)), 0.0
                elif e['cd'] <= 0 and k == 'gren' and 250 < ad < 760:
                    e['cd'] = random.uniform(2.6, 3.6)
                    e['thr'] = 0.45
        elif k == 'sniper':
            if onscreen and alive:
                if e['tele'] > 0:
                    e['tele'] -= dt
                    if e['tele'] <= 0:
                        pv = e.get('pv') or (e['x'], e['y'] - 50)
                        mx_, my_, ux, uy = self.pt_muzzle('sniper', pv, e['face'], p['x'], py)
                        ang = math.degrees(math.atan2(uy, ux))
                        self.pt_ebullet(mx_, my_, ang, 1100, 20, 2.0)
                        e['flash'] = 0.08
                        self.pt_casing(pv[0] + ux * 22, pv[1] + uy * 22, e['face'])
                        self.audio.play('cannon', .35)
                        e['cd'] = random.uniform(2.2, 3.0)
                elif e['cd'] <= 0:
                    e['tele'] = 0.9
        elif k == 'turret':
            if onscreen and alive and ad < 760:
                if e['burst'] > 0:
                    e['bcd'] -= dt
                    if e['bcd'] <= 0:
                        e['burst'] -= 1
                        e['bcd'] = 0.11
                        ang = math.degrees(math.atan2(py - (e['y'] - 50), dx)) + random.uniform(-5, 5)
                        self.pt_ebullet(e['x'] + (62 if dx > 0 else -62), e['y'] - 50, ang, 520, 7)
                        self.audio.play('mg', .15)
                elif e['cd'] <= 0:
                    e['cd'] = random.uniform(2.2, 3.2)
                    e['burst'], e['bcd'] = 6, 0.0
        elif k == 'tank':
            self.pt_ai_tank(e, dt)

    def pt_ai_heli(self, e, dt):
        pt = self.pt
        p = pt['p']
        alive = not p['dead']
        cam = pt['cam']
        home = (pt['lock'] if pt['lock'] is not None else cam) + W - 300
        e['st'] += dt
        e['rot'] += dt * 40
        ratio = e['hp'] / e['max']
        e['flash'] = max(0.0, e['flash'] - dt)
        gy = self.PT_GR
        if e['state'] == 'enter':
            e['x'] -= 170 * dt
            if e['x'] <= home:
                e['state'], e['st'], e['cd'] = 'fight', 0.0, 1.4
        elif e['state'] == 'fight':
            e['x'] = max(home + math.sin(e['st'] * 0.6) * 150, (pt['lock'] or cam) + 460)
            e['y'] += (gy - 160 + math.sin(e['st'] * 1.3) * 18 - e['y']) * min(1.0, dt * 3)
            if e['burst'] > 0:
                e['bcd'] -= dt
                if e['bcd'] <= 0:
                    e['burst'] -= 1
                    e['bcd'] = 0.09
                    ang = math.degrees(math.atan2(p['y'] - 36 - (e['y'] - 20), p['x'] - (e['x'] - 120))) + random.uniform(-6, 6)
                    self.pt_ebullet(e['x'] - 120, e['y'] - 20, ang, 560, 6)
                    self.audio.play('mg', .2)
            elif e['cd'] <= 0 and alive:
                e['atk'] += 1
                e['cd'] = random.uniform(1.6, 2.4) * (0.75 if ratio < 0.5 else 1.0)
                if ratio < 0.5 and e['atk'] % 4 == 0:
                    e['state'], e['st'] = 'dive', 0.0
                    self.pop('¡EN PICADA!', W / 2, 300, (255, 90, 70))
                elif e['atk'] % 3 == 0:
                    for off in (-210, 0, 210):
                        pt['mort'].append(dict(x=p['x'] + off + random.uniform(-40, 40), t=0.0))
                    self.pop('¡MISILES!', W / 2, 300, (255, 160, 60))
                    self.audio.play('ping', .6)
                else:
                    e['burst'], e['bcd'] = 12, 0.0
        elif e['state'] == 'dive':
            tx = p['x'] + 20
            e['x'] += clamp(tx - e['x'], -380 * dt, 380 * dt)
            e['y'] += (gy - 95 - e['y']) * min(1.0, dt * 4)
            if abs(p['x'] - e['x']) < 120 and p['y'] > e['y'] - 150 and alive and e['st'] > 0.5:
                self.pt_hurt(22)
                e['state'], e['st'] = 'climb', 0.0
            if e['st'] > 2.2:
                e['state'], e['st'] = 'climb', 0.0
        elif e['state'] == 'climb':
            e['y'] += (gy - 200 - e['y']) * min(1.0, dt * 3)
            e['x'] += (home - e['x']) * min(1.0, dt * 1.5)
            if e['st'] > 1.4:
                e['state'], e['st'] = 'fight', 0.0

    def pt_draw_heli(self, cv, sx, fy, e):
        t = self.t
        hit = e['hit'] > 0
        body = (210, 210, 210) if hit else (58, 70, 56)
        dark = (150, 150, 150) if hit else (36, 44, 36)
        pygame.draw.ellipse(cv, (40, 36, 44), (sx - 110, self.PT_GR - 6, 220, 12))
        # cola
        pygame.draw.polygon(cv, dark, [(sx + 40, fy - 62), (sx + 190, fy - 70), (sx + 190, fy - 56), (sx + 40, fy - 36)])
        pygame.draw.polygon(cv, body, [(sx + 175, fy - 66), (sx + 205, fy - 100), (sx + 214, fy - 96), (sx + 192, fy - 56)])
        # cuerpo
        pygame.draw.ellipse(cv, body, (sx - 140, fy - 92, 230, 80))
        pygame.draw.ellipse(cv, dark, (sx - 140, fy - 92, 230, 80), 3)
        pygame.draw.ellipse(cv, (120, 190, 215) if not hit else (255, 255, 255), (sx - 134, fy - 84, 84, 44))
        pygame.draw.ellipse(cv, (200, 235, 245), (sx - 124, fy - 80, 36, 16))
        # armas
        pygame.draw.rect(cv, dark, (sx - 112, fy - 22, 70, 12), border_radius=4)
        pygame.draw.rect(cv, (24, 24, 28), (sx - 138, fy - 20, 40, 7))
        for k in range(3):
            pygame.draw.rect(cv, (30, 34, 30), (sx - 20 + k * 16, fy - 34, 12, 26), border_radius=3)
        # patines
        pygame.draw.line(cv, dark, (sx - 80, fy - 4), (sx + 50, fy - 4), 4)
        pygame.draw.line(cv, dark, (sx - 50, fy - 14), (sx - 54, fy - 4), 3)
        pygame.draw.line(cv, dark, (sx + 20, fy - 14), (sx + 24, fy - 4), 3)
        # rotor principal
        pygame.draw.line(cv, (24, 24, 28), (sx - 20, fy - 92), (sx - 20, fy - 106), 4)
        rl = 190
        a1 = math.cos(e['rot'])
        pygame.draw.ellipse(cv, (96, 98, 108), (sx - 20 - rl, fy - 114, rl * 2, 14), 1)
        pygame.draw.line(cv, (200, 202, 208), (sx - 20 - rl * a1, fy - 108), (sx - 20 + rl * a1, fy - 108), 3)
        pygame.draw.line(cv, (200, 202, 208), (sx - 20 - rl * math.sin(e['rot']) * 0.9, fy - 106),
                         (sx - 20 + rl * math.sin(e['rot']) * 0.9, fy - 106), 2)
        # rotor de cola
        ra = 30 * math.cos(e['rot'] * 1.3)
        pygame.draw.line(cv, (200, 202, 208), (sx + 208, fy - 98 - ra), (sx + 208, fy - 98 + ra), 3)
        if int(t * 3) % 2 == 0:
            glow(cv, sx + 196, fy - 62, 14, (255, 60, 50), 0.8)
        if e['burst'] > 0 and e['bcd'] > 0.04:
            self.pt_flash(cv, sx - 138, fy - 17, 0, False)
        if e['hp'] < e['max'] * 0.5 and random.random() < 0.4:
            self.fx.add('smoke', e['x'] + random.uniform(-30, 30), fy - 50, random.uniform(-10, 10), -40, 1.6, 8, 26, (40, 40, 44))

    def pt_ai_tank(self, e, dt):
        if e.get('variant') == 'heli':
            return self.pt_ai_heli(e, dt)
        pt = self.pt
        p = pt['p']
        alive = not p['dead']
        cam = pt['cam']
        home = (pt['lock'] if pt['lock'] is not None else cam) + W - 260
        e['st'] += dt
        ratio = e['hp'] / e['max']
        e['flash'] = max(0.0, e['flash'] - dt)
        if e['state'] == 'enter':
            e['x'] -= 140 * dt
            if e['x'] <= home:
                e['state'] = 'fight'
                e['st'] = 0.0
                e['cd'] = 1.4
        elif e['state'] == 'fight':
            e['mcd'] = e['mcd'] - dt if e['mcd'] > 0 else (e['mcd'] if ratio >= 0.6 else 0.0)
            if ratio < 0.6 and e['mcd'] <= 0 and e['burst'] == 0 and e['tele'] <= 0 and alive:
                e['mcd'] = 6.5
                for off in (-190, 0, 190):
                    pt['mort'].append(dict(x=p['x'] + off + random.uniform(-40, 40), t=0.0))
                self.pop('¡MORTEROS!', W / 2, 300, (255, 160, 60))
                self.audio.play('ping', .6)
            e['x'] = home + math.sin(e['st'] * 0.7) * 80
            e['x'] = max(e['x'], (pt['lock'] or cam) + 520)
            if e['burst'] > 0:
                e['bcd'] -= dt
                if e['bcd'] <= 0:
                    e['burst'] -= 1
                    e['bcd'] = 0.1
                    ang = math.degrees(math.atan2(p['y'] - 36 - (e['y'] - 74), p['x'] - (e['x'] - 152))) + random.uniform(-7, 7)
                    self.pt_ebullet(e['x'] - 152, e['y'] - 74, ang, 600, 7)
                    self.audio.play('mg', .2)
            if e['tele'] > 0:
                e['tele'] -= dt
                if e['tele'] <= 0:
                    self.pt_ebullet(e['x'] - 226, e['y'] - 111, 180, 640, 24, 2.4)
                    self.audio.play('cannon', .6)
                    e['recoil'] = 20.0
                    e['flash'] = 0.1
                    self.fx.explode(e['x'] - 230, e['y'] - 111, 0.6)
                    self.shake = max(self.shake, 6)
            elif e['burst'] == 0 and e['cd'] <= 0 and alive:
                e['atk'] += 1
                e['cd'] = random.uniform(1.8, 2.6) * (0.75 if ratio < 0.5 else 1.0)
                if ratio < 0.5 and e['atk'] % 3 == 0:
                    e['state'] = 'charge'
                    e['st'] = 0.0
                    self.pop('¡EMBISTE!', W / 2, 300, (255, 90, 70))
                elif e['atk'] % 2 == 0:
                    e['burst'], e['bcd'] = 9, 0.0
                else:
                    e['tele'] = 0.75
        elif e['state'] == 'charge':
            e['x'] -= 330 * dt
            if abs(p['x'] - e['x']) < 150 and p['y'] > e['y'] - 100 and alive:
                self.pt_hurt(28)
            if e['x'] < cam + 120 or e['st'] > 2.6:
                e['state'] = 'return'
        elif e['state'] == 'return':
            e['x'] += 190 * dt
            if e['x'] >= home:
                e['state'] = 'fight'
                e['st'] = 0.0

    def upd_port(self, dt):
        pt = self.pt
        p = pt['p']
        if pt['freeze'] > 0:
            pt['freeze'] -= dt
            dt *= 0.25
        keys = pygame.key.get_pressed()
        pt['t'] += dt
        pt['hurt'] = max(0.0, pt['hurt'] - dt)
        L = self.PT_LEN
        alive = not p['dead']
        p['inv'] = max(0.0, p['inv'] - dt)
        p['cd'] = max(0.0, p['cd'] - dt)
        p['gcd'] = max(0.0, p['gcd'] - dt)
        p['flash'] = max(0.0, p['flash'] - dt)
        p['hmg'] = max(0.0, p['hmg'] - dt)
        p['thr'] = max(0.0, p['thr'] - dt)
        pt['go_t'] = max(0.0, pt['go_t'] - dt)
        cam = pt['cam']
        if alive and pt['phase'] == 'play':
            mv = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            p['crouch'] = bool(keys[pygame.K_s] or keys[pygame.K_DOWN]) and p['ground']
            sp = 0.0 if p['crouch'] else 235.0
            p['vx'] = mv * sp
            p['x'] += p['vx'] * dt
            if mv:
                p['ph'] += abs(p['vx']) * dt / 12.7
            sx = p['x'] - cam
            p['face'] = 1 if self.aim[0] >= sx else -1
            if pygame.mouse.get_pressed()[0] or keys[pygame.K_j]:
                self.pt_shoot()
        was_air = not p['ground']
        vy0 = p['vy']
        self.pt_land(p, dt)
        if was_air and p['ground'] and vy0 > 380 and alive:
            for _ in range(7):
                self.fx.add('smoke', p['x'] + random.uniform(-14, 14), p['y'] - 3, random.uniform(-70, 70), random.uniform(-30, -6), 0.6, 5, 15, (190, 170, 150), drag=2)
        if alive and p['ground'] and abs(p['vx']) > 1:
            p['dust'] -= dt
            if p['dust'] <= 0:
                p['dust'] = 0.13
                self.fx.add('smoke', p['x'] - p['face'] * 14, p['y'] - 3, random.uniform(-20, 20) - p['vx'] * 0.2, random.uniform(-26, -8), 0.5, 3, 11, (190, 170, 150), drag=2)
        if p['dead']:
            p['dead_t'] += dt
        for c in pt['cas'][:]:
            c['t'] += dt
            c['vy'] += 1400 * dt
            c['x'] += c['vx'] * dt
            c['y'] += c['vy'] * dt
            c['rot'] += c['vr'] * dt
            if c['y'] > self.PT_GR - 2:
                c['y'] = self.PT_GR - 2
                c['vy'] *= -0.35
                c['vx'] *= 0.5
            if c['t'] > 1.6:
                pt['cas'].remove(c)
        for c in pt['corpses'][:]:
            if c['air']:
                c['vy'] += 1500 * dt
                c['y'] += c['vy'] * dt
                c['x'] += c['vx'] * dt
                c['spin'] *= 0.995
                fl_ = self.pt_floor(c['x'], c['y'] - 10)
                if c['y'] >= fl_ and c['vy'] > 0:
                    c['y'], c['air'], c['t'] = float(fl_), False, 0.0
                    self.fx.add('smoke', c['x'], c['y'] - 4, 0, -20, 0.6, 5, 16, (190, 170, 150), drag=2)
                continue
            c['t'] += dt
            c['x'] += c['vx'] * dt
            c['vx'] *= max(0.0, 1 - 5 * dt)
            if c['t'] > 4.8:
                pt['corpses'].remove(c)
        for w_ in pt['wrecks']:
            if random.random() < dt * 9:
                self.fx.add('smoke', w_['x'] + random.uniform(-40, 40) * (3 if w_['kind'] == 'tank' else 0.7), w_['y'] - (110 if w_['kind'] == 'tank' else 50),
                            random.uniform(-8, 8), -45, 2.2, 8, 30, (34, 34, 38))
        lo = cam + 24
        hi = (pt['lock'] + W - 30) if pt['lock'] is not None else min(L - 30, cam + W - 30)
        p['x'] = clamp(p['x'], lo, hi)
        # bloqueos de pantalla (estilo Metal Slug) y cámara
        for g in pt['groups']:
            if g['done']:
                continue
            if g['lock']:
                if pt['lock'] is None and p['x'] > g['x'] - 300:
                    pt['lock'] = pt['cam']
                    g['active'] = True
                    g['done'] = True
                    self.pt_spawn_group(g)
                    self.audio.play('ping', .6)
            elif pt['cam'] + W > g['x']:
                g['done'] = True
                self.pt_spawn_group(g)
        if pt['lock'] is not None:
            pending = [e for g in pt['groups'] if g.get('active') for e in g.get('ids', []) if e in pt['enemies']]
            if not pending and not any(e['kind'] == 'tank' for e in pt['enemies']):
                pt['lock'] = None
                pt['go_t'] = 4.0
        target = clamp(p['x'] - W * 0.38, 0, L - W)
        if pt['lock'] is not None:
            target = min(target, pt['lock'])
        if target > cam:
            pt['cam'] = cam + (target - cam) * min(1, dt * 6)
        pt['cam'] = clamp(pt['cam'], 0, L - W)
        # enemigos
        for e in pt['enemies'][:]:
            self.pt_ai(e, dt)
            if e['kind'] in ('knife', 'rifle', 'gren') and e['x'] < pt['cam'] - 700:
                pt['enemies'].remove(e)
        # balas del jugador
        for b in pt['bul'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            hit = None
            for e in pt['enemies']:
                x0, y0, w, h = self.pt_box(e)
                if x0 <= b['x'] <= x0 + w and y0 <= b['y'] <= y0 + h:
                    hit = e
                    break
            brl = None
            for br in pt['barrels']:
                if abs(b['x'] - br['x']) < 17 and br['y'] - 44 <= b['y'] <= br['y'] and br['fuse'] < 0:
                    brl = br
                    break
            if brl is not None:
                pt['bul'].remove(b)
                brl['hp'] -= 1
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-120, 0), 0.25, col=(255, 230, 150), drag=2, grav=300)
                if brl['hp'] <= 0:
                    brl['fuse'] = 0.1
            elif hit is not None and hit['kind'] == 'shield' and b['vx'] * hit['face'] < 0 and abs(b['vy']) < 0.8 * abs(b['vx']) and b['y'] > hit['y'] - 58:
                pt['bul'].remove(b)
                for _ in range(3):
                    self.fx.add('spark', b['x'], b['y'], hit['face'] * random.uniform(60, 200), random.uniform(-160, 40), 0.3, col=(200, 230, 255), drag=2, grav=500)
                self.audio.play('ping', .25)
            elif hit is not None:
                pt['bul'].remove(b)
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-120, 0), 0.25, col=(255, 230, 150), drag=2, grav=300)
                self.pt_hit_enemy(hit, b['dmg'])
            elif b['life'] <= 0 or b['y'] > self.PT_GR + 20:
                pt['bul'].remove(b)
        # balas enemigas
        pbox = (p['x'] - 14, p['y'] - (46 if p['crouch'] else 70), 28, 46 if p['crouch'] else 70)
        for b in pt['ebul'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if alive and pbox[0] <= b['x'] <= pbox[0] + pbox[2] and pbox[1] <= b['y'] <= pbox[1] + pbox[3]:
                pt['ebul'].remove(b)
                self.pt_hurt(int(b['dmg']))
            elif any(abs(b['x'] - br['x']) < 17 and br['y'] - 44 <= b['y'] <= br['y'] and br['fuse'] < 0 for br in pt['barrels']):
                pt['ebul'].remove(b)
                for br in pt['barrels']:
                    if abs(b['x'] - br['x']) < 17 and br['fuse'] < 0:
                        br['fuse'] = 0.1
            elif b['life'] <= 0 or b['y'] > self.PT_GR + 10 or b['x'] < pt['cam'] - 100 or b['x'] > pt['cam'] + W + 100:
                pt['ebul'].remove(b)
        # granadas
        for n in pt['nades'][:]:
            n['t'] += dt
            n['vy'] += 900 * dt
            n['x'] += n['vx'] * dt
            n['y'] += n['vy'] * dt
            boom = n['y'] >= self.PT_GR - 4 or n['t'] > 2.2
            if not boom:
                if n['own'] != 'p':                               # las granadas del jugador atraviesan contenedores y plataformas
                    for pl in pt['plats']:
                        if pl['x'] < n['x'] < pl['x'] + pl['w'] and pl['top'] - 6 < n['y'] < pl['top'] + 10 and n['vy'] > 0:
                            boom = True
                if n['own'] == 'p':
                    for e in pt['enemies']:
                        x0, y0, w, h = self.pt_box(e)
                        if x0 <= n['x'] <= x0 + w and y0 <= n['y'] <= y0 + h:
                            boom = True
            if boom:
                pt['nades'].remove(n)
                if n['own'] == 'p':
                    self.pt_blast(n['x'], min(n['y'], self.PT_GR - 4), 95 * self.up_blast(), 6 * self.up_dmg(), 10, 'p')
                else:
                    self.pt_blast(n['x'], min(n['y'], self.PT_GR - 4), 95, 0, 28, 'e')
        # barriles explosivos
        for br in pt['barrels'][:]:
            if br['fuse'] >= 0:
                br['fuse'] -= dt
                if br['fuse'] < 0:
                    pt['barrels'].remove(br)
                    self.pt_blast(br['x'], br['y'] - 22, 110, 7, 26, 'b')
            elif br['hp'] <= 1 and random.random() < dt * 8:
                self.fx.add('smoke', br['x'] + random.uniform(-6, 6), br['y'] - 44, 0, -50, 0.9, 4, 12, (40, 40, 44))
        # prisioneros
        for pw in pt['pows']:
            pw['t'] += dt
            if pw['state'] == 'tied' and alive and abs(p['x'] - pw['x']) < 46 and abs(p['y'] - self.PT_GR) < 80:
                pw['state'] = 'free'
                pw['t'] = 0.0
                pt['pow_n'] += 1
                self.add_score(500)
                self.audio.play('win', .6)
                self.pop('¡GRACIAS! +500', pw['x'] - pt['cam'], self.PT_GR - 110, (140, 255, 170))
                pt['items'].append(dict(x=pw['x'] + 30, y=float(self.PT_GR - 30), kind=pw['item'], t=0.0))
            elif pw['state'] == 'free':
                pw['x'] += 190 * dt
        # morteros del jefe
        for m in pt['mort'][:]:
            m['t'] += dt
            if m['t'] >= 1.45:
                pt['mort'].remove(m)
                self.pt_blast(m['x'], self.PT_GR - 4, 90, 0, 24, 'm')
        # objetos
        for it in pt['items'][:]:
            it['t'] += dt
            if alive and abs(p['x'] - it['x']) < 36 and abs((p['y'] - 30) - it['y']) < 60:
                pt['items'].remove(it)
                self.audio.play('pickup', .8)
                if it['kind'] == 'med':
                    p['hp'] = min(PLAYER_HP, p['hp'] + 40)
                    self.pop('+40 VIDA', p['x'] - pt['cam'], p['y'] - 80, (120, 255, 160))
                elif it['kind'] == 'mask':
                    self.hz_state(pt)['mask'] = 14.0
                    self.pop('¡MÁSCARA ANTIGÁS!', p['x'] - pt['cam'], p['y'] - 80, (170, 255, 120))
                elif it['kind'] == 'gren':
                    p['gren'] = min(9, p['gren'] + 4)
                    self.pop('+4 GRANADAS', p['x'] - pt['cam'], p['y'] - 80, (255, 220, 120))
                elif it['kind'] in ('shot', 'rkt'):
                    self.pt_weapon_pick(it['kind'])
                else:
                    p['hmg'] = 14.0
                    p['wpn'] = None
                    self.pop('¡AMETRALLADORA!', p['x'] - pt['cam'], p['y'] - 80, (255, 160, 90))
        self.pt_epic_update(dt, alive, keys)
        self.port_hazards(dt, alive)
        self.fx.update(dt)
        # fin de la misión
        if not p['dead'] and p['hp'] <= 0:
            p['dead'] = True
            self.audio.play('boom_s')
            self.shake = 12
            if pt['phase'] == 'play':
                pt['phase'], pt['fail'], pt['pt'] = 'result', True, -0.6
                self.banner('¡SOLDADO CAÍDO!', 'El asalto fracasó', (255, 80, 70), 3.0)
        boss_dead = pt['boss'] is None and pt['groups'][-1]['done'] and not any(e['kind'] == 'tank' for e in pt['enemies'])
        if pt['phase'] == 'play' and boss_dead:
            pt['phase'], pt['pt'] = 'result', 0.0
            hpf = p['hp'] / PLAYER_HP
            pts_ = (hpf >= 0.6) + (pt['t'] < 240) + (pt['pow_n'] >= 4) + (pt['taken'] < 100)
            rank = 'S' if pts_ >= 4 else ('A' if pts_ == 3 else ('B' if pts_ == 2 else 'C'))
            pt['rank'] = rank
            bonus = 1500 + 300 * self.wave + {'S': 1500, 'A': 800, 'B': 300, 'C': 0}[rank]
            pt['bonus'] = bonus
            self.add_score(bonus)
            self.audio.play('win', .8)
            self.banner('¡PUERTO TOMADO!', 'Rango %s  |  Bonus +%d' % (rank, bonus), (120, 255, 160), 3.4)
        if pt['phase'] == 'result':
            pt['pt'] += dt
            if pt['pt'] > (3.4 if pt['fail'] else 6.0):
                self.end_port()

    PT_MUZ = {'sniper': 106, 'flame': 62, 'player': 70}

    def pt_muzzle(self, kind, pv, face, tx, ty):
        """Boca del arma: parte del hombro (pivote del brazo dibujado) y sigue la inclinación real del arma (±80°).
        Devuelve (x, y, dirx, diry) en coordenadas de mundo."""
        px, py = pv
        dx, dy = tx - px, ty - py
        right = face > 0
        th = math.atan2(dy, dx if right else -dx)
        th = clamp(th, -math.radians(80), math.radians(80))
        dirx, diry = (math.cos(th) if right else -math.cos(th)), math.sin(th)
        ln = self.PT_MUZ.get(kind, 74)
        return px + dirx * ln, py + diry * ln, dirx, diry

    def pt_shoot(self):
        pt = self.pt
        p = pt['p']
        if p['cd'] > 0 or p['dead']:
            return
        if p['wpn']:
            return self.pt_shoot_special()
        hmg = p['hmg'] > 0
        p['cd'] = (0.075 if hmg else 0.115) * self.up_reload()
        p['flash'] = 0.05
        pv = p.get('pv') or (p['x'], p['y'] - (50 if p['crouch'] else 67))
        mx, my, dx, dy = self.pt_muzzle('player', pv, p['face'], self.aim[0] + pt['cam'], self.aim[1])
        a = math.atan2(dy, dx)
        a += math.radians(random.uniform(-3.5, 3.5) if hmg else random.uniform(-1.2, 1.2))
        pt['bul'].append(dict(x=mx, y=my, vx=math.cos(a) * 980, vy=math.sin(a) * 980, dmg=1.0 * self.up_dmg(), life=0.9))
        self.audio.play('mg', .3)
        if random.random() < 0.7:
            self.pt_casing(pv[0] + dx * 24, pv[1] + dy * 24, p['face'])

    def end_port(self):
        pt = self.pt
        if pt['fail']:
            self.hull = max(0.0, self.hull - 20)
            self.ammo = max(0, self.ammo - 4)
            left = 2 - self.port_tries
            self.toast('Asalto fallido: -20 casco, -4 munición (intentos: %d)' % left, (255, 140, 90))
            if self.hull <= 0:
                return self.lose_ship('Tu barco se hundió')
        else:
            self.port_done = True
            self.hull = min(self.hull_max, self.hull + 30)
            self.fuel = 100.0
            self.ammo = 40
            for en in self.enemies:
                if en.get('is_boss'):
                    en['hp'] = max(1.0, en['hp'] * 0.75)
            self.toast('Puerto enemigo tomado: reabastecimiento total y el jefe pierde 25% de casco', (120, 255, 160))
        self.go('map')

    # ---- dibujo del asalto
    def pt_art_prebuild(self):
        """Pre-renderiza el arte del asalto en segundo plano para que no haya pausa al empezar."""
        import threading
        if hasattr(self, '_pt_thread'):
            return
        self._pt_thread = threading.Thread(target=self.pt_art_init, daemon=True)
        self._pt_thread.start()

    def pt_art_init(self):
        if getattr(self, '_pt_ready', False):
            return
        th = getattr(self, '_pt_thread', None)
        import threading
        if th is not None and th is not threading.current_thread() and th.is_alive():
            th.join()
        if getattr(self, '_pt_ready', False):
            return
        self.pt_art = build_pt_art()
        self.pt_tk = build_pt_tank()
        self.pt_bk = build_pt_bunker()
        self.pt_ct = build_pt_containers()
        self.pt_dc = build_pt_decor()
        self.pt_bg = build_pt_bg(W, self.PT_GR, self.PT_LEN)
        self.pt_cache = {}
        g = self.pt_bk['gun']
        pad = pygame.Surface((g.get_width() * 2, g.get_height() * 2), pygame.SRCALPHA)
        pad.blit(g, (pad.get_width() // 2 - 8, pad.get_height() // 2 - 12))
        self.pt_bk['gunpad'] = pad
        sh = pygame.Surface((56, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), (0, 0, 56, 14))
        pygame.draw.ellipse(sh, (0, 0, 0, 50), (8, 3, 40, 8))
        self.pt_shadow = sh
        vg = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(60):
            a = int(60 * (1 - i / 60) ** 2)
            pygame.draw.rect(vg, (10, 6, 24, a), (i * 3, i * 2, W - i * 6, H - i * 4), 6)
        self.pt_vig = vg
        self._pt_ready = True

    def pt_floor(self, x, y):
        """Altura de la superficie bajo (x, y): suelo o la plataforma más cercana por debajo."""
        best = self.PT_GR
        for pl in self.pt['plats']:
            if pl['x'] - 8 < x < pl['x'] + pl['w'] + 8 and y - 6 <= pl['top'] < best:
                best = pl['top']
        return best

    def pt_char(self, cv, kind, sx, fy, face, pose, fi, aim=None, arm='gun', hit=0.0, alpha=255, shadow=True, flash=False, rot_deg=0.0, fem=False):
        """Dibuja un soldado pre-renderizado (cuerpo + brazos/arma rotados). aim=(dx, dy) hacia donde apunta."""
        art = self.pt_art
        base = kind
        if (kind == 'player' and self.pt.get('pfem')) or fem:
            if kind + '_f' in art['body']:
                kind = kind + '_f'
        frames = art['body'][kind][pose]
        fi %= len(frames)
        spr, shx, shy = frames[fi]
        if shadow:
            fl_ = self.pt_floor(sx + self.pt['cam'], fy)
            if fl_ - fy < 200:
                sh_ = self.pt_shadow
                if fl_ - fy > 4:
                    k_ = max(0.45, 1 - (fl_ - fy) / 260)
                    sh_ = pygame.transform.smoothscale(sh_, (int(56 * k_), int(14 * k_)))
                cv.blit(sh_, (sx - sh_.get_width() // 2, fl_ - 8 * sh_.get_height() // 14))
        right = face > 0
        key = (kind, pose, fi, right)
        img = self.pt_cache.get(key)
        if img is None:
            img = spr if right else pygame.transform.flip(spr, True, False)
            self.pt_cache[key] = img
        if hit > 0 or alpha < 255:
            img = img.copy()
            if hit > 0:
                img.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            if alpha < 255:
                img.set_alpha(alpha)
        if rot_deg:
            th = math.radians(rot_deg)
            rim = pygame.transform.rotate(img, rot_deg)
            cx_, cy_ = sx - 14 * math.sin(th), fy - 30 - 14 * math.cos(th)
            cv.blit(rim, (cx_ - rim.get_width() // 2, cy_ - rim.get_height() // 2))
            return None
        cv.blit(img, (sx - PT_AX, fy - PT_AY))
        if not arm or arm not in art['arm'][kind] or pose == 'die':
            return None
        layer = art['arm'][kind][arm]
        if aim is not None and arm in ('gun', 'knife'):
            dx, dy = aim
            rot = -math.degrees(math.atan2(dy, dx)) if right else math.degrees(math.atan2(dy, -dx))
            rot = clamp(rot, -80, 80)
        else:
            rot = 0.0
        rk = (kind, arm, right, int(rot / 3))
        rimg = self.pt_cache.get(rk)
        if rimg is None:
            base = layer if right else pygame.transform.flip(layer, True, False)
            rimg = pygame.transform.rotate(base, rot)
            self.pt_cache[rk] = rimg
        if hit > 0 or alpha < 255:
            rimg = rimg.copy()
            if hit > 0:
                rimg.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            if alpha < 255:
                rimg.set_alpha(alpha)
        px = sx + (shx if right else -shx)
        py = fy - shy
        cv.blit(rimg, (px - rimg.get_width() // 2, py - rimg.get_height() // 2))
        if flash and arm == 'gun':
            ln = {'sniper': 106, 'flame': 62, 'player': 70}.get(base, 74)
            th = math.radians(-rot if right else rot)
            mx = px + (math.cos(th) if right else -math.cos(th)) * ln
            my = py + math.sin(th) * ln
            self.pt_flash(cv, mx, my, -rot if right else rot, right)
        return px, py

    def pt_flash(self, cv, x, y, ang, right):
        a = math.radians(ang)
        d = 1 if right else -1
        glow(cv, x, y, 26, (255, 200, 110), 0.8)
        pts = []
        for i in range(10):
            r = random.uniform(16, 26) if i % 2 == 0 else 5
            t = -1.2 + 2.4 * i / 9
            pts.append((x + d * math.cos(a + t * d) * r, y + math.sin(a + t * d) * r))
        pygame.draw.polygon(cv, (255, 236, 160), pts)
        pygame.draw.circle(cv, (255, 255, 235), (int(x), int(y)), 5)

    def pt_tank_img(self, e):
        """Compone el tanque (mirando a la izquierda): orugas animadas, torreta y cañón con retroceso."""
        T = self.pt_tk
        hull = T['hull'][int((e['x'] % 14) / 14 * 8) % 8]
        comp = pygame.Surface((520, 190), pygame.SRCALPHA)
        ox = 70
        comp.blit(hull, (ox, 0))
        comp.blit(T['turret'], (ox, 0))
        px, py = T['pivot']
        comp.blit(T['barrel'], (ox + px - 6 - int(e.get('recoil', 0)), py - 30))
        img = pygame.transform.flip(comp, True, False)
        if e['hit'] > 0:
            img.fill((44, 44, 44, 0), special_flags=pygame.BLEND_RGB_ADD)
        return img

    def draw_port(self, cv):
        pt = self.pt
        p = pt['p']
        cam = pt['cam']
        bg = self.pt_bg
        GR = self.PT_GR
        t = self.t
        cv.blit(bg['sky'], (0, 0))
        cv.blit(bg['sea'], (0, 410))
        for i in range(10):
            yy = 430 + i * 20
            xx = (i * 191 + t * (9 + i * 2)) % (W + 160) - 80
            pygame.draw.line(cv, (255, 206, 160), (xx, yy), (xx + 40 + i * 5, yy), 2)
        cv.blit(bg['far'], (0, 330), area=pygame.Rect(int(cam * 0.18), 0, W, 230))
        cv.blit(bg['mid'], (0, GR - 330), area=pygame.Rect(int(cam * 0.5), 0, W, 330))
        # muelle
        for y in range(GR, H, 4):
            f = (y - GR) / (H - GR)
            pygame.draw.rect(cv, (int(lerp(112, 66, f)), int(lerp(108, 62, f)), int(lerp(122, 78, f))), (0, y, W, 4))
        pygame.draw.rect(cv, (150, 146, 156), (0, GR, W, 6))
        pygame.draw.rect(cv, (60, 58, 70), (0, GR + 6, W, 3))
        for x in range(-int(cam) % 130, W, 130):
            pygame.draw.line(cv, (62, 60, 72), (x, GR + 10), (x - 22, H), 2)
        for y in (GR + 56, GR + 112):
            pygame.draw.line(cv, (62, 60, 72), (0, y), (W, y), 1)
        for x in range(-int(cam) % 260, W, 260):
            pygame.draw.rect(cv, (240, 200, 50), (x, GR + 3, 70, 3))
        for px_, pw_ in pt['puddles']:
            xx = px_ - cam
            if -80 < xx < W:
                pygame.draw.ellipse(cv, (190, 130, 120), (xx, GR + 26, pw_, 12))
                pygame.draw.ellipse(cv, (240, 170, 130), (xx + pw_ * 0.2, GR + 29, pw_ * 0.4, 4))
        # decorado de fondo
        D = self.pt_dc
        for d in pt['decor']:
            sx = d['x'] - cam
            if not (-200 < sx < W + 200):
                continue
            spr = D[d['kind']]
            if d['kind'] == 'lamp':
                cv.blit(spr, (sx - 30, GR - 186))
            elif d['kind'] == 'fence':
                cv.blit(spr, (sx, GR - 56))
            else:
                cv.blit(spr, (sx - spr.get_width() // 2, GR - spr.get_height() + 4))
        # plataformas (contenedores)
        for pl in pt['plats']:
            x0 = pl['x'] - cam
            if x0 > W or x0 + pl['w'] < 0:
                continue
            spr = self.pt_ct[(pl['ci'], pl['w'])]
            for row in range(pl['h'] // 64):
                y0 = pl['top'] + row * 64
                cv.blit(spr, (x0, y0))
                if row:
                    sh_ = pygame.Surface((pl['w'], 64), pygame.SRCALPHA)
                    sh_.fill((0, 0, 20, 40))
                    cv.blit(sh_, (x0, y0))
            pygame.draw.rect(cv, (0, 0, 0), (x0, GR - 3, pl['w'], 3))
        # objetos
        for it in pt['items']:
            sx = it['x'] - cam
            if not (-40 < sx < W + 40):
                continue
            bob = math.sin(it['t'] * 5) * 3
            col = {'med': (236, 240, 236), 'gren': (96, 120, 70), 'hmg': (250, 170, 70), 'mask': (70, 100, 70), 'shot': (236, 200, 110), 'rkt': (240, 130, 100)}[it['kind']]
            glow(cv, sx, it['y'] + bob, 32, (120, 255, 160) if it['kind'] == 'med' else (255, 210, 80), 0.5)
            pygame.draw.rect(cv, (24, 26, 30), (sx - 15, it['y'] - 15 + bob, 30, 30), border_radius=5)
            pygame.draw.rect(cv, col, (sx - 13, it['y'] - 13 + bob, 26, 26), border_radius=4)
            if it['kind'] == 'med':
                pygame.draw.rect(cv, (220, 50, 50), (sx - 8, it['y'] - 3 + bob, 16, 6))
                pygame.draw.rect(cv, (220, 50, 50), (sx - 3, it['y'] - 8 + bob, 6, 16))
            elif it['kind'] == 'mask':
                pygame.draw.ellipse(cv, (30, 36, 30), (sx - 8, it['y'] - 7 + bob, 16, 14))
                pygame.draw.circle(cv, (170, 255, 120), (sx - 3, int(it['y'] - 2 + bob)), 2)
                pygame.draw.circle(cv, (170, 255, 120), (sx + 3, int(it['y'] - 2 + bob)), 2)
                pygame.draw.circle(cv, (130, 140, 130), (sx, int(it['y'] + 4 + bob)), 3)
            elif it['kind'] == 'gren':
                pygame.draw.circle(cv, (50, 70, 40), (sx, int(it['y'] + 2 + bob)), 8)
                pygame.draw.circle(cv, (150, 180, 110), (sx - 2, int(it['y'] + bob)), 2)
            else:
                self.text(cv, {'shot': 'S', 'rkt': 'R'}.get(it['kind'], 'H'), self.f_m, (60, 30, 10), sx, it['y'] - 12 + bob, 'c', shadow=False)
        # restos
        for w_ in pt['wrecks']:
            sx = w_['x'] - cam
            if not (-300 < sx < W + 300):
                continue
            if w_['kind'] == 'tank':
                img = self.pt_tank_img(dict(x=w_['x'], hit=0.0, recoil=0))
                img.fill((70, 64, 62, 255), special_flags=pygame.BLEND_RGBA_MULT)
                cv.blit(img, (sx - 260, w_['y'] - 176))
                for k in range(4):
                    ph = (t * 1.6 + k * 0.27) % 1
                    glow(cv, sx - 60 + k * 44, w_['y'] - 110 - ph * 40, 26 - 10 * ph, (255, 150, 60), 1 - ph)
            else:
                spr = self.pt_bk['base'].copy()
                spr.fill((60, 56, 54, 255), special_flags=pygame.BLEND_RGBA_MULT)
                cv.blit(spr, (sx - 55, w_['y'] - 66))
                ph = (t * 1.4 + w_['x']) % 1
                glow(cv, sx, w_['y'] - 50 - ph * 30, 18, (255, 140, 60), 1 - ph)
        self.pt_epic_draw_back(cv, cam)
        for c in pt['corpses']:
            sx = c['x'] - cam
            if not (-100 < sx < W + 100):
                continue
            if c['air']:
                c['rot'] = c.get('rot', 0.0) + c['spin'] * 0.016
                self.pt_char(cv, c['kind'], int(sx), int(c['y']), c['face'], 'die', 1, None, None, 0.0, 255, False, False, c['rot'], c.get('fem', False))
                continue
            fi = min(5, int(c['t'] * 12))
            al = 255 if c['t'] < 3.5 else int(255 * clamp(1 - (c['t'] - 3.5) / 1.2, 0, 1))
            self.pt_char(cv, c['kind'], int(sx), int(c['y']), c['face'], 'die', fi, None, None, 0.0, al, True, False, 0.0, c.get('fem', False))
        # barriles explosivos
        brl = D['barrel']
        for br in pt['barrels']:
            sx = br['x'] - cam
            if -40 < sx < W + 40:
                cv.blit(brl, (sx - brl.get_width() // 2, br['y'] - brl.get_height() + 4))
                pygame.draw.polygon(cv, (250, 210, 40), [(sx, br['y'] - 54), (sx - 9, br['y'] - 40), (sx + 9, br['y'] - 40)])
                self.text(cv, '!', self.f_s, (40, 30, 10), sx, br['y'] - 52, 'c', shadow=False)
                if br['fuse'] >= 0 and int(t * 30) % 2 == 0:
                    glow(cv, sx, br['y'] - 22, 34, (255, 230, 150), 0.9)
        # prisioneros de guerra
        for pw in pt['pows']:
            sx = pw['x'] - cam
            if not (-60 < sx < W + 60):
                continue
            if pw['state'] == 'tied':
                self.pt_char(cv, 'pow', int(sx), self.PT_GR, -1, 'crouch', 0, None, None)
                pygame.draw.line(cv, (140, 100, 56), (sx - 8, self.PT_GR - 36), (sx + 8, self.PT_GR - 30), 3)
                pygame.draw.line(cv, (140, 100, 56), (sx - 8, self.PT_GR - 30), (sx + 8, self.PT_GR - 36), 3)
                if int(t * 2.5) % 2 == 0:
                    self.text(cv, '¡AYUDA!', self.f_s, (255, 240, 150), sx, self.PT_GR - 82, 'c')
            elif pw['state'] == 'free' and pw['t'] < 2.4:
                self.pt_char(cv, 'pow', int(sx), self.PT_GR, 1, 'run', int(pw['t'] * 14), None, None, 0.0, int(255 * clamp(1 - (pw['t'] - 1.6) / 0.8, 0, 1)))
        # morteros
        for m in pt['mort']:
            sx = m['x'] - cam
            k_ = m['t'] / 1.45
            rr = 78 - 28 * k_
            pygame.draw.ellipse(cv, (255, 70, 60), (sx - rr, GR - 8, rr * 2, 16), 3)
            pygame.draw.ellipse(cv, (255, 70, 60, 90), (sx - 6, GR - 3, 12, 6))
            if m['t'] > 1.1:
                y = lerp(-70, GR, (m['t'] - 1.1) / 0.35)
                pygame.draw.line(cv, (255, 220, 160), (sx, y - 80), (sx, y), 5)
                pygame.draw.circle(cv, (255, 250, 220), (int(sx), int(y)), 7)
                glow(cv, sx, y, 24, (255, 170, 80), 0.8)
            else:
                self.text(cv, 'v', self.f_m, (255, 90, 70), sx, GR - 70 - (int(t * 6) % 2) * 6, 'c')
        self.port_hazards_draw(cv, cam)
        # enemigos
        pcx = p['x'] - cam
        for e in pt['enemies']:
            sx = e['x'] - cam
            if not (-340 < sx < W + 340):
                continue
            k = e['kind']
            fy = int(e['y'])
            if k == 'tank' and e.get('variant') == 'heli':
                self.pt_draw_heli(cv, sx, fy, e)
                continue
            elif k == 'tank':
                img = self.pt_tank_img(e)
                cv.blit(img, (sx - 260, fy - 176))
                if e['tele'] > 0:
                    glow(cv, sx - 224, fy - 111, 30 + 12 * math.sin(e['st'] * 30), (255, 160, 70))
                if e['flash'] > 0:
                    self.pt_flash(cv, sx - 224, fy - 111, 0, False)
                if e['burst'] > 0 and e['bcd'] > 0.05:
                    self.pt_flash(cv, sx - 152, fy - 74, 0, False)
                if e['hp'] < e['max'] * 0.5 and random.random() < 0.3:
                    self.fx.add('smoke', e['x'] - 20 + random.uniform(-30, 30), fy - 140, random.uniform(-10, 10), -40, 1.6, 8, 26, (40, 40, 44))
                continue
            if k == 'turret':
                bk = self.pt_bk
                cv.blit(bk['base'], (sx - 55, fy - 66))
                right = p['x'] > e['x']
                dx, dy = p['x'] - e['x'], (p['y'] - 40) - (fy - 50)
                ang = clamp(-math.degrees(math.atan2(dy, abs(dx))), -60, 60)
                pad = bk['gunpad'] if right else pygame.transform.flip(bk['gunpad'], True, False)
                rimg = pygame.transform.rotate(pad, ang if right else -ang)
                gx, gy = sx + (6 if right else -6), fy - 50
                if e['hit'] > 0:
                    rimg = rimg.copy()
                    rimg.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
                cv.blit(rimg, (gx - rimg.get_width() // 2, gy - rimg.get_height() // 2))
                if e['burst'] > 0 and e['bcd'] > 0.05:
                    a_ = math.radians(ang)
                    self.pt_flash(cv, gx + (66 * math.cos(a_)) * (1 if right else -1), gy - 66 * math.sin(a_), ang if right else -ang, right)
                continue
            moving = e.get('moving', False)
            if e['stag'] > 0:
                sx -= e['face'] * 2
            if e['para']:
                self.pt_char(cv, 'rifle', int(sx), fy, e['face'], 'fall', 0, None, None, 0.0, 255, False, False, 0.0, e.get('fem', False))
                top = fy - 168
                pygame.draw.arc(cv, (236, 236, 226), (sx - 54, top, 108, 70), 0, 3.14159, 40)
                pygame.draw.polygon(cv, (226, 90, 70), [(sx - 54, top + 35), (sx - 18, top + 4), (sx - 6, top + 4), (sx - 22, top + 38)])
                pygame.draw.polygon(cv, (236, 236, 226), [(sx - 22, top + 38), (sx - 6, top + 4), (sx + 6, top + 4), (sx + 22, top + 38)])
                pygame.draw.polygon(cv, (226, 90, 70), [(sx + 22, top + 38), (sx + 6, top + 4), (sx + 18, top + 4), (sx + 54, top + 35)])
                pygame.draw.arc(cv, (40, 36, 40), (sx - 54, top, 108, 70), 0, 3.14159, 3)
                for ox in (-52, -20, 20, 52):
                    pygame.draw.line(cv, (40, 36, 40), (sx + ox, top + 36), (sx, fy - 54), 1)
                continue
            if k == 'shield':
                pose = 'run' if moving else 'idle'
                fi = int(e['ph']) if moving else int(t * 3 + e['ph0'])
                self.pt_char(cv, 'shield', int(sx + (e['face'] * 6 if e['slash'] > 0.15 else 0)), fy, e['face'], pose, fi, None, 'shield', e['hit'])
                if e['hp'] < e['max']:
                    pygame.draw.rect(cv, (8, 12, 24), (sx - 15, fy - 86, 30, 5))
                    pygame.draw.rect(cv, (240, 80, 70), (sx - 14, fy - 85, int(28 * e['hp'] / e['max']), 3))
                continue
            pvx, pvy = e.get('pv') or (e['x'], fy - 62)
            tgt_aim = (p['x'] - pvx, (p['y'] - 30) - pvy)
            if k == 'knife':
                pose = 'run' if moving else 'idle'
                arm = 'knife'
                aim = (e['face'] * 1.0, -0.15 + (0.5 - e['slash'] / 0.3) * 1.6 if e['slash'] > 0 else 0.1)
            elif k == 'gren':
                pose = 'run' if moving else 'idle'
                arm = 'gun'
                aim = tgt_aim
                if e['thr'] > 0:
                    arm = 'wind' if e['thr'] > 0.14 else 'rel'
            elif k == 'sniper':
                pose = 'crouch'
                arm = 'gun'
                aim = tgt_aim
            else:
                pose = 'run' if moving else ('crouch' if e['kneel'] else 'idle')
                arm = 'gun'
                aim = tgt_aim
            if k == 'flame':
                pose = 'run' if moving else 'idle'
                arm = 'gun'
                aim = tgt_aim
            fi = int(e['ph']) if pose == 'run' else int(t * 3 + e['ph0'])
            r_ = self.pt_char(cv, k, int(sx), fy, e['face'], pose, fi, aim, arm, e['hit'], 255, True, e['flash'] > 0 and k != 'flame', 0.0, e.get('fem', False))
            if r_:
                e['pv'] = (r_[0] + cam, r_[1])
            if k == 'sniper' and e['tele'] > 0:
                ay = e['y'] - 34
                pygame.draw.line(cv, (255, 40, 40), (sx, ay), (p['x'] - cam, p['y'] - 36), 1)
                self.text(cv, '!', self.f_m, (255, 70, 60), sx, fy - 92, 'c')
            if e['hp'] < e['max']:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 15, fy - 84, 30, 5))
                pygame.draw.rect(cv, (240, 80, 70), (sx - 14, fy - 83, int(28 * e['hp'] / e['max']), 3))
        # jugador
        if not p['dead']:
            if not (p['inv'] > 0 and int(t * 20) % 2 == 0):
                pv_ = p.get('pv') or (p['x'], p['y'] - (50 if p['crouch'] else 67))
                aim = (self.aim[0] + cam - pv_[0], self.aim[1] - pv_[1])
                if not p['ground']:
                    pose, fi = ('jump' if p['vy'] < 0 else 'fall'), 0
                elif p['crouch']:
                    pose, fi = 'crouch', 0
                elif abs(p['vx']) > 1:
                    pose, fi = 'run', int(p['ph'])
                else:
                    pose, fi = 'idle', int(t * 3)
                arm = 'gun'
                if p['thr'] > 0:
                    arm = 'wind' if p['thr'] > 0.16 else 'rel'
                r_ = self.pt_char(cv, 'player', int(pcx - (p['face'] * 2 if p['flash'] > 0 else 0)), int(p['y']), p['face'], pose, fi, aim, arm, 0.0, 255, True, p['flash'] > 0)
                if r_:
                    p['pv'] = (r_[0] + cam, r_[1])
        else:
            fi = min(5, int(p['dead_t'] * 12))
            self.pt_char(cv, 'player', int(pcx), int(p['y']), p['face'], 'die', fi, None, None)
        self.pt_epic_draw_front(cv, cam)
        # proyectiles y casquillos
        for c in pt['cas']:
            sx, sy = c['x'] - cam, c['y']
            pygame.draw.line(cv, (240, 200, 90), (sx, sy), (sx + math.cos(c['rot']) * 4, sy + math.sin(c['rot']) * 4), 2)
        for b in pt['bul']:
            sx, sy = b['x'] - cam, b['y']
            ex, ey = sx - b['vx'] * 0.03, sy - b['vy'] * 0.03
            pygame.draw.line(cv, (255, 200, 90), (sx, sy), (ex, ey), 5)
            pygame.draw.line(cv, (255, 250, 210), (sx, sy), (sx - b['vx'] * 0.018, sy - b['vy'] * 0.018), 2)
        for b in pt['ebul']:
            sx, sy = b['x'] - cam, b['y']
            col = (255, 90, 70) if not b['big'] else (255, 170, 60)
            r = 4 if not b['big'] else 9
            glow(cv, sx, sy, 14 if not b['big'] else 26, col, 0.7)
            pygame.draw.line(cv, col, (sx, sy), (sx - b['vx'] * 0.03, sy - b['vy'] * 0.03), 3 if not b['big'] else 8)
            pygame.draw.circle(cv, col, (int(sx), int(sy)), r)
            pygame.draw.circle(cv, (255, 240, 220), (int(sx), int(sy)), max(1, r - 2))
        for n in pt['nades']:
            sx, sy = n['x'] - cam, n['y']
            pygame.draw.circle(cv, (24, 30, 20), (int(sx), int(sy)), 7)
            pygame.draw.circle(cv, (70, 100, 56), (int(sx), int(sy)), 6)
            pygame.draw.circle(cv, (250, 220, 90) if n['own'] == 'p' else (255, 90, 70), (int(sx), int(sy)), 7, 2)
            pygame.draw.circle(cv, (160, 190, 120), (int(sx - 2), int(sy - 2)), 2)
        self.fx.draw(cv, cam, 0)
        # luces de las farolas
        for d in pt['decor']:
            if d['kind'] == 'lamp':
                sx = d['x'] - cam
                if -120 < sx < W + 120:
                    glow(cv, sx - 18, GR - 170, 70, (255, 214, 140), 0.55)
        sc = (self.wave - 1) % 3
        if sc:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((6, 10, 40, 120) if sc == 1 else (30, 36, 50, 95))
            cv.blit(ov, (0, 0))
            if sc == 1:
                for d in pt['decor']:
                    if d['kind'] == 'lamp' and -120 < d['x'] - cam < W + 120:
                        glow(cv, d['x'] - cam - 18, GR - 170, 130, (255, 214, 140), 0.55)
            else:
                for i in range(70):
                    rx = (i * 97 + t * 420 + i * i * 13) % (W + 100) - 50
                    ry = (i * 61 + t * 900 + i * 29) % H
                    pygame.draw.line(cv, (170, 190, 215), (rx, ry), (rx - 9, ry + 22), 1)
                if int(t * 0.7) != int(t * 0.7 - 0.016) and random.random() < 0.15:
                    pt['flash_t'] = 0.18
                pt['flash_t'] = max(0.0, pt.get('flash_t', 0.0) - 0.016)
                if pt['flash_t'] > 0:
                    cv.fill((90, 90, 110), special_flags=pygame.BLEND_RGB_ADD)
        cv.blit(self.pt_vig, (0, 0))
        self.port_hazards_hud(cv)
        # HUD
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   BAJAS %d' % (self.wave, WIN_WAVE, pt['kills']), self.f_s, (160, 200, 240), 26, 42)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        self.text(cv, 'PUERTO ENEMIGO', self.f_m, (255, 140, 110), W // 2, 16, 'c')
        boss = pt['boss']
        if boss is not None:
            self.bar(cv, W // 2 - 210, 44, 420, 26, boss['hp'] / boss['max'], (240, 80, 70), 'HELICÓPTERO DE ASALTO' if boss.get('variant') == 'heli' else 'TANQUE DE PUERTO')
        else:
            self.bar(cv, W // 2 - 210, 44, 420, 26, clamp(p['x'] / (self.PT_LEN - 1500), 0, 1), (255, 190, 90), 'AVANCE')
        self.panel(cv, (14, H - 126, 330, 112), 190)
        hp = clamp(p['hp'] / PLAYER_HP, 0, 1)
        self.bar(cv, 26, H - 114, 306, 22, hp, (80, 230, 110) if hp > 0.5 else ((255, 200, 70) if hp > 0.25 else (240, 80, 70)), 'SOLDADO %d' % max(0, p['hp']))
        self.text(cv, 'GRANADAS %d' % p['gren'], self.f_s, (255, 230, 150), 26, H - 84)
        if p['hmg'] > 0:
            self.bar(cv, 26, H - 56, 306, 16, p['hmg'] / 14.0, (255, 160, 80), 'AMETRALLADORA %.1f' % p['hmg'])
        self.pt_epic_hud(cv)
        if pt['go_t'] > 0 and pt['phase'] == 'play' and int(t * 3) % 2 == 0:
            self.text(cv, 'ADELANTE  >>>', self.f_l, (255, 230, 120), W - 180, 330, 'c')
        if pt['hurt'] > 0:
            hs = pygame.Surface((W, H), pygame.SRCALPHA)
            hs.fill((255, 30, 30, int(110 * pt['hurt'] / 0.4)))
            cv.blit(hs, (0, 0))
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (20, 20, 24), (ax, ay), 15, 4)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 14, 2)
        for dx_, dy_ in ((-22, 0), (22, 0), (0, -22), (0, 22)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx_ // 2, ay + dy_ // 2), (ax + dx_, ay + dy_), 2)
        if pt['phase'] == 'result' and pt['fail']:
            self.dim(cv, 60)
        elif pt['phase'] == 'result' and pt['rank'] and pt['pt'] > 0.8:
            k_ = clamp((pt['pt'] - 0.8) / 0.5, 0, 1)
            self.panel(cv, (W // 2 - 220, 230, 440, 250), int(215 * k_))
            self.text(cv, 'MISIÓN CUMPLIDA', self.f_l, (120, 255, 160), W // 2, 240, 'c', alpha=int(255 * k_))
            rows = [('Bajas', '%d' % pt['kills']), ('Prisioneros', '%d / 5' % pt['pow_n']), ('Tiempo', '%d s' % pt['t']),
                    ('Daño recibido', '%d' % pt['taken']), ('Bonus', '+%d' % pt.get('bonus', 0))]
            for i, (a_, b_) in enumerate(rows):
                self.text(cv, a_, self.f_m, (200, 215, 235), W // 2 - 190, 292 + i * 30, alpha=int(255 * k_))
                self.text(cv, b_, self.f_m, (255, 240, 170), W // 2 + 190, 292 + i * 30, 'r', alpha=int(255 * k_))
            rc = {'S': (255, 220, 90), 'A': (140, 255, 170), 'B': (150, 200, 255), 'C': (200, 200, 210)}[pt['rank']]
            self.text(cv, 'RANGO  %s' % pt['rank'], self.f_l, rc, W // 2, 440, 'c', alpha=int(255 * k_))
