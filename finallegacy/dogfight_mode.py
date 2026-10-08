"""Base aérea: salida en F-16 con dos alas aliados. Combate cenital sobre el mar, con el mismo manejo que el barco (W/S velocidad, A/D giro)."""
import math
import random
import pygame
from .common import H, W, Particles, angle_diff, bearing, clamp, dist, draw_circ, glow, vec

STAGES = 4
SPAWN_R = 820


def _wrap_turn(h, want, rate, dt):
    d = angle_diff(h, want)
    return (h + clamp(d, -rate * dt, rate * dt)) % 360


class DogfightMixin:
    def jet_init(self):
        self.jet_sorties = 1

    def jet_new_wave(self):
        self.jet_sorties = min(3, getattr(self, 'jet_sorties', 0) + 1)

    # ------------------------------------------------------------------ inicio
    def jet_launch(self):
        if not self.near_helipad():
            self.toast('Acercate a la base aérea (isla con la H) para despegar el F-16', (255, 220, 130))
            return
        if getattr(self, 'jet_sorties', 0) <= 0:
            self.toast('Sin salidas de F-16: se repone una por oleada', (255, 200, 120))
            return
        if self.attack is not None or self.warned:
            self.toast('Hay un ataque en curso: no es momento de despegar', (255, 150, 110))
            return
        self.jet_sorties -= 1
        self.start_jets()

    def start_jets(self):
        w = self.wave
        hp = 100.0
        self.fx = Particles()
        self.jt = dict(
            p=dict(x=0.0, y=0.0, h=0.0, v=230.0, hp=hp, max=hp, gcd=0.0, mcd=0.0, msl=6, flares=5, fcd=0.0, boost=1.0, bank=0.0, hit=0.0, lock=None, warn=0.0),
            allies=[dict(x=-90.0, y=70.0, h=0.0, v=230.0, hp=45.0, max=45.0, cd=0.0, id=0), dict(x=90.0, y=70.0, h=0.0, v=230.0, hp=45.0, max=45.0, cd=0.0, id=1)],
            foes=[], bullets=[], missiles=[], flares=[], flak=[], spawns=[], stage=0, phase='intro', pt=0.0, t=0.0, kills=0, pts=0, cx=0.0, cy=0.0, lost=0, tr=0.0)
        self.jt_stage_setup()
        self.go('jets')
        self.audio.play('alarm', .4)
        self.banner('¡F-16 EN EL AIRE!', 'W/S velocidad  A/D girar  Clic: cañón  Q/clic der.: misil  F: bengalas  Shift: postquemador', (150, 220, 255), 4.8)
        self.say('piloto', 'Escuadrón en formación, capitán. Dos alas conmigo. Cazas al frente y, abajo, barcos y submarinos con misiles antiaéreos: usá bengalas y no vueles en línea recta.', 'info')

    def jt_stage_setup(self):
        jt = self.jt
        w, s = self.wave, jt['stage']
        sp = []
        def add(kind, n, t0, gap, side=None):
            a0 = random.uniform(0, 360) if side is None else side
            for i in range(n):
                sp.append((t0 + i * gap, kind, (a0 + random.uniform(-18, 18)) % 360))
        if s == 0:
            add('viper', 3 + w // 3, 1.0, 1.4)
            if w >= 2:
                add('destroyer', 1, 2.0, 1.0)
        elif s == 1:
            add('viper', 2 + w // 3, 1.0, 1.2)
            add('stealth', 2 + w // 4, 4.0, 1.8)
            add('sub', 1 + (w >= 5), 2.5, 2.0)
        elif s == 2:
            add('bomber', 1 + (w >= 5), 1.0, 5.0)
            add('viper', 3 + w // 3, 3.0, 1.3)
            add('destroyer', 1 + (w >= 4), 4.0, 2.0)
        else:
            add('ace', 1, 1.0, 1.0)
            add('stealth', 2, 3.5, 1.5)
            add('viper', 2 + w // 4, 7.0, 1.3)
            add('sub', 1, 5.0, 1.0)
            add('destroyer', 1, 6.0, 1.0)
        jt['spawns'] = sorted(sp)
        jt['st'] = 0.0

    def jt_spawn(self, kind, a):
        jt = self.jt
        p = jt['p']
        w = self.wave
        dx, dy = vec(a, SPAWN_R if kind not in ('destroyer', 'sub') else random.uniform(520, 700))
        x, y = p['x'] + dx, p['y'] + dy
        h = bearing(p['x'] - x, p['y'] - y)
        d = dict(kind=kind, x=x, y=y, h=h, cd=random.uniform(0.5, 1.5), mcd=random.uniform(4, 7), burst=0, hp=1.0, v=235.0, r=24, jk=0.0, jd=1, tgt='p', flash=0.0)
        if kind == 'viper':
            d.update(hp=4.0 + w // 2, v=240.0, turn=62 + 2 * w, r=24)
        elif kind == 'stealth':
            d.update(hp=8.0 + w, v=270.0, turn=78 + 2 * w, r=22)
        elif kind == 'bomber':
            d.update(hp=36.0 + 5 * w, v=120.0, turn=22, r=60)
        elif kind == 'ace':
            d.update(hp=60.0 + 8 * w, v=290.0, turn=95 + 2 * w, r=30)
        elif kind == 'destroyer':
            d.update(hp=30.0 + 4 * w, v=30.0, r=44, h=(h + random.uniform(-60, 60)) % 360, aa=random.uniform(3, 5), fk=random.uniform(1.5, 3))
        elif kind == 'sub':
            d.update(hp=22.0 + 3 * w, v=22.0, r=30, surf=False, st=random.uniform(2, 5), h=random.uniform(0, 360), aa=2.0, n=0)
        d['max'] = d['hp']
        jt['foes'].append(d)

    # ------------------------------------------------------------------ utilidades de combate
    def jt_shoot(self, x, y, h, own, dmg, speed=720.0, life=0.9, spread=1.5):
        a = h + random.uniform(-spread, spread)
        vx, vy = vec(a, speed)
        self.jt['bullets'].append(dict(x=x, y=y, vx=vx, vy=vy, life=life, own=own, dmg=dmg))

    def jt_missile(self, x, y, h, own, tgt, dmg):
        self.jt['missiles'].append(dict(x=x, y=y, h=h, v=330.0, life=5.0, own=own, tgt=tgt, dmg=dmg, t=0.0))

    def jt_hurt_p(self, n):
        p = self.jt['p']
        p['hp'] -= n
        p['hit'] = 0.25
        self.shake = max(self.shake, 2 + n * 0.25)
        self.audio.play('hit', .35)

    def jt_kill(self, f):
        jt = self.jt
        f['dead'] = True
        jt['kills'] += 1
        pts = {'viper': 100, 'stealth': 250, 'bomber': 900, 'ace': 1500, 'destroyer': 450, 'sub': 500}[f['kind']]
        jt['pts'] += pts
        big = f['kind'] in ('bomber', 'ace', 'destroyer', 'sub')
        if f['kind'] in ('destroyer', 'sub'):
            self.fx.splash(f['x'], f['y'], 1.6)
        self.fx.explode_art(f['x'], f['y'], 2.0 if big else 1.0, True)
        self.audio.play('boom_l' if big else 'boom_s', .8 if big else .5)
        for _ in range(8 if big else 3):
            self.fx.add('smoke', f['x'] + random.uniform(-16, 16), f['y'] + random.uniform(-16, 16), random.uniform(-30, 30), random.uniform(-30, 30), random.uniform(1.2, 2.4), 6, 22, (46, 44, 44))
        if big:
            self.shake = max(self.shake, 9)

    def jt_dmg(self, f, dmg):
        f['hp'] -= dmg
        f['flash'] = 0.1
        if f['hp'] <= 0 and not f.get('dead'):
            self.jt_kill(f)

    def jt_targets(self):
        """Blancos de los enemigos: el jugador y los alas vivos."""
        jt = self.jt
        return [jt['p']] + [a for a in jt['allies'] if a['hp'] > 0]

    # ------------------------------------------------------------------ actualización
    def upd_jets(self, dt):
        jt = self.jt
        p = jt['p']
        jt['t'] += dt
        self.fx.update(dt)
        jt['cx'] += (p['x'] - jt['cx']) * min(1.0, dt * 6)
        jt['cy'] += (p['y'] - jt['cy']) * min(1.0, dt * 6)
        p['hit'] = max(0.0, p['hit'] - dt)
        ph = jt['phase']
        if ph in ('win', 'lose'):
            jt['pt'] += dt
            self.jt_move_world(dt, False)
            if ph == 'lose' and random.random() < dt * 8:
                self.fx.explode_art(p['x'] + random.uniform(-30, 30), p['y'] + random.uniform(-30, 30), 1.0, True)
            if jt['pt'] > 3.2:
                self.end_jets(ph == 'win')
            return
        if ph == 'intro':
            jt['pt'] += dt
            if jt['pt'] > 2.5:
                jt['phase'], jt['pt'] = 'play', 0.0
        elif ph == 'break':
            jt['pt'] += dt
            if jt['pt'] > 4.0:
                jt['stage'] += 1
                jt['phase'], jt['pt'] = 'play', 0.0
                p['hp'] = min(p['max'], p['hp'] + 15)
                p['msl'] = min(6, p['msl'] + 3)
                p['flares'] = min(5, p['flares'] + 2)
                self.jt_stage_setup()
                self.banner('OLEADA %d/%d' % (jt['stage'] + 1, STAGES), '¡El as enemigo entra en combate!' if jt['stage'] == STAGES - 1 else 'Más cazas al frente', (255, 200, 110), 2.4)
        else:
            jt['st'] += dt
            while jt['spawns'] and jt['spawns'][0][0] <= jt['st']:
                _, kind, a = jt['spawns'].pop(0)
                self.jt_spawn(kind, a)
        self.jt_player(dt)
        self.jt_move_world(dt, True)
        if ph == 'play':
            if p['hp'] <= 0:
                p['hp'] = 0.0
                jt['phase'], jt['pt'] = 'lose', 0.0
                self.audio.play('boom_l', 1.0)
                self.banner('¡F-16 DERRIBADO!', 'El piloto se eyectó', (255, 100, 90), 3.0)
                return
            if not jt['spawns'] and not [f for f in jt['foes'] if not f.get('dead')]:
                if jt['stage'] >= STAGES - 1:
                    jt['phase'], jt['pt'] = 'win', 0.0
                    self.audio.play('fanfare', .8)
                    self.banner('¡CIELO LIMPIO!', 'Misión cumplida, regresamos a la base', (130, 255, 190), 3.0)
                else:
                    jt['phase'], jt['pt'] = 'break', 0.0
                    self.audio.play('win', .6)
                    self.banner('OLEADA %d SUPERADA' % (jt['stage'] + 1), 'Recarga: +15 casco, +3 misiles, +2 bengalas', (130, 255, 190), 2.6)

    def jt_player(self, dt):
        jt = self.jt
        p = jt['p']
        keys = pygame.key.get_pressed()
        btn = pygame.mouse.get_pressed()
        thr = (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0) - (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0)
        turn = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
        ab = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and p['boost'] > 0.02 and jt['phase'] != 'lose'
        vmin, vcru, vmax = 150.0, 235.0, 330.0
        target = vcru + thr * (vmax - vcru if thr > 0 else vcru - vmin)
        if ab:
            target = 430.0
            p['boost'] = max(0.0, p['boost'] - dt * 0.28)
        else:
            p['boost'] = min(1.0, p['boost'] + dt * 0.1)
        p['v'] += clamp(target - p['v'], -160 * dt, 130 * dt)
        rate = 118 * clamp(1.25 - p['v'] / 430, 0.45, 1.0)           # más lento = gira más cerrado
        if jt['phase'] == 'lose':
            turn = 0
        p['h'] = (p['h'] + turn * rate * dt) % 360
        p['bank'] += (turn * 38 - p['bank']) * min(1.0, dt * 7)
        dx, dy = vec(p['h'], p['v'] * dt)
        p['x'] += dx
        p['y'] += dy
        self.fuel = max(0.0, self.fuel - dt * 0.02)
        self.audio.engine_vol(0.25 + 0.5 * p['v'] / 430)
        # estela
        jt['tr'] -= dt
        if jt['tr'] <= 0:
            jt['tr'] = 0.04
            bx, by = vec(p['h'], -30)
            self.fx.add('foam', p['x'] + bx, p['y'] + by, 0, 0, 0.9, 4, 12, (235, 240, 250))
        # blanco fijado: el más cercano delante del morro
        best, bd_ = None, 1e9
        for f in jt['foes']:
            if f.get('dead'):
                continue
            d = dist(p['x'], p['y'], f['x'], f['y'])
            if f['kind'] == 'sub' and not f['surf']:
                continue
            if d < 950 and abs(angle_diff(bearing(f['x'] - p['x'], f['y'] - p['y']), p['h'])) < 38 and d < bd_:
                best, bd_ = f, d
        p['lock'] = best
        p['gcd'] = max(0.0, p['gcd'] - dt)
        p['mcd'] = max(0.0, p['mcd'] - dt)
        p['fcd'] = max(0.0, p['fcd'] - dt)
        live = jt['phase'] in ('play', 'break', 'intro') and p['hp'] > 0
        if live and (btn[0] or keys[pygame.K_SPACE]) and p['gcd'] <= 0:
            p['gcd'] = 0.075
            for off in (-9, 9):
                ox, oy = vec(p['h'] + 90, off)
                fx_, fy_ = vec(p['h'], 26)
                self.jt_shoot(p['x'] + ox + fx_, p['y'] + oy + fy_, p['h'], True, 1.6)
            if int(jt['t'] * 13) % 2 == 0:
                self.audio.play('mg', .2)
        if live and (btn[2] or keys[pygame.K_q]) and p['mcd'] <= 0 and p['msl'] > 0:
            p['mcd'] = 0.8
            p['msl'] -= 1
            fx_, fy_ = vec(p['h'], 20)
            self.jt_missile(p['x'] + fx_, p['y'] + fy_, p['h'], True, p['lock'], 22.0)
            self.audio.play('launch', .6)
        if live and keys[pygame.K_f] and p['fcd'] <= 0 and p['flares'] > 0:
            p['fcd'] = 0.5
            p['flares'] -= 1
            for k in range(3):
                a = p['h'] + 180 + (k - 1) * 40
                vx, vy = vec(a, 70)
                jt['flares'].append(dict(x=p['x'], y=p['y'], vx=vx + 0.4 * (p['v'] and 0), vy=vy, life=3.2))
            self.audio.play('pickup', .4)

    def jt_move_world(self, dt, live):
        jt = self.jt
        p = jt['p']
        w = self.wave
        tg = self.jt_targets()
        # alas aliados
        for a in jt['allies']:
            if a['hp'] <= 0:
                continue
            foes = [f for f in jt['foes'] if not f.get('dead')]
            a['cd'] = max(0.0, a['cd'] - dt)
            if foes and live:
                f = min(foes, key=lambda f: dist(f['x'], f['y'], a['x'], a['y']))
                want = bearing(f['x'] - a['x'], f['y'] - a['y'])
                a['h'] = _wrap_turn(a['h'], want, 75, dt)
                a['v'] += (255 - a['v']) * dt
                d = dist(f['x'], f['y'], a['x'], a['y'])
                if d < 420 and abs(angle_diff(want, a['h'])) < 9 and a['cd'] <= 0:
                    a['cd'] = 0.14
                    self.jt_shoot(a['x'], a['y'], a['h'], True, 1.1, spread=2.5)
            else:
                want = bearing(p['x'] + (-110 if a['id'] == 0 else 110) - a['x'], p['y'] + 110 - a['y'])
                dd = dist(p['x'], p['y'], a['x'], a['y'])
                a['h'] = _wrap_turn(a['h'], bearing(p['x'] - a['x'], p['y'] - a['y']) if dd > 220 else p['h'], 90, dt)
                a['v'] += (clamp(p['v'] + (dd - 160) * 0.8, 160, 360) - a['v']) * dt * 2
            dx, dy = vec(a['h'], a['v'] * dt)
            a['x'] += dx
            a['y'] += dy
        # enemigos
        for f in jt['foes']:
            f['flash'] = max(0.0, f.get('flash', 0.0) - dt)
            if f.get('dead'):
                continue
            k = f['kind']
            if not live:
                continue
            if k in ('destroyer', 'sub'):
                self.jt_ship_ai(f, dt)
                continue
            f['cd'] -= dt
            f['mcd'] -= dt
            tgt = min(tg, key=lambda t_: dist(t_['x'], t_['y'], f['x'], f['y']) * (0.6 if t_ is p else 1.0))
            dd = dist(f['x'], f['y'], tgt['x'], tgt['y'])
            want = bearing(tgt['x'] - f['x'], tgt['y'] - f['y'])
            if k == 'bomber':
                # vuela en línea hacia el jugador, sin maniobrar; su torreta dispara a lo que tenga cerca
                f['h'] = _wrap_turn(f['h'], bearing(p['x'] - f['x'], p['y'] - f['y']) if dd > 300 else f['h'], f['turn'], dt)
                if f['cd'] <= 0 and dd < 560:
                    f['cd'] = 0.45
                    aim = bearing(tgt['x'] - f['x'], tgt['y'] - f['y'])
                    self.jt_shoot(f['x'], f['y'], aim, False, 4.0, speed=520, life=1.3, spread=5)
                if f['mcd'] <= 0 and dd < 700:
                    f['mcd'] = 8.0
                    self.jt_missile(f['x'], f['y'], want, False, tgt, 16.0)
            else:
                f['jk'] -= dt
                if dd < 170:                                       # pasada: se aleja y vuelve
                    want = (want + 150 * f['jd']) % 360
                elif f['jk'] <= 0 and k in ('stealth', 'ace'):
                    f['jk'] = random.uniform(1.6, 3.2)
                    f['jd'] = random.choice((-1, 1))
                f['h'] = _wrap_turn(f['h'], want, f['turn'], dt)
                if f['cd'] <= 0 and dd < 440 and abs(angle_diff(want, f['h'])) < 10:
                    f['cd'] = 0.11 if f['burst'] > 0 else random.uniform(1.4, 2.4) * max(0.7, 1 - 0.03 * w)
                    f['burst'] = f['burst'] - 1 if f['burst'] > 0 else 5
                    self.jt_shoot(f['x'], f['y'], f['h'], False, 2.2 if k == 'viper' else 3.0, speed=600, life=0.9, spread=2.2)
                if k in ('stealth', 'ace') and f['mcd'] <= 0 and 160 < dd < 760 and abs(angle_diff(want, f['h'])) < 25:
                    f['mcd'] = random.uniform(6, 9) if k == 'stealth' else random.uniform(4, 6)
                    self.jt_missile(f['x'], f['y'], f['h'], False, tgt, 18.0)
                    if tgt is p:
                        self.audio.play('alarm', .3)
            sp = f['v']
            dx, dy = vec(f['h'], sp * dt)
            f['x'] += dx
            f['y'] += dy
        jt['foes'] = [f for f in jt['foes'] if not f.get('dead')]
        # balas
        for b in jt['bullets']:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if b['own']:
                for f in jt['foes']:
                    if not f.get('dead') and dist(b['x'], b['y'], f['x'], f['y']) < f['r'] and not (f['kind'] == 'sub' and not f['surf']):
                        self.jt_dmg(f, b['dmg'] * (0.3 if f['kind'] in ('destroyer', 'sub') else 1.0))
                        b['life'] = 0
                        self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25, col=(255, 220, 130))
                        break
            else:
                for t_ in tg:
                    if dist(b['x'], b['y'], t_['x'], t_['y']) < 20:
                        b['life'] = 0
                        if t_ is p:
                            self.jt_hurt_p(b['dmg'])
                        else:
                            t_['hp'] -= b['dmg']
                            if t_['hp'] <= 0:
                                self.jt_ally_down(t_)
                        break
        jt['bullets'] = [b for b in jt['bullets'] if b['life'] > 0]
        # bengalas
        for fl in jt['flares']:
            fl['x'] += fl['vx'] * dt
            fl['y'] += fl['vy'] * dt
            fl['vx'] *= 1 - 1.2 * dt
            fl['vy'] *= 1 - 1.2 * dt
            fl['life'] -= dt
            if random.random() < dt * 20:
                self.fx.add('glow', fl['x'], fl['y'], 0, 0, 0.3, 6, 18, (255, 220, 140))
        jt['flares'] = [fl for fl in jt['flares'] if fl['life'] > 0]
        for fk in jt['flak']:
            fk['t'] += dt
            if fk['t'] >= 0.9 and not fk.get('done'):
                fk['done'] = True
                self.fx.explode_art(fk['x'], fk['y'], 0.7, False)
                self.audio.play('boom_s', .4)
                if dist(fk['x'], fk['y'], p['x'], p['y']) < 58 and p['hp'] > 0:
                    self.jt_hurt_p(8.0)
        jt['flak'] = [fk for fk in jt['flak'] if fk['t'] < 1.0]
        # misiles
        p['warn'] = 0.0
        for m in jt['missiles']:
            m['t'] += dt
            m['life'] -= dt
            tgt = m['tgt']
            if not m['own']:
                fls = [fl for fl in jt['flares'] if dist(fl['x'], fl['y'], m['x'], m['y']) < 360]
                if fls and (not isinstance(tgt, dict) or tgt is p or True):
                    tgt = min(fls, key=lambda fl: dist(fl['x'], fl['y'], m['x'], m['y']))
                if tgt is p:
                    p['warn'] = 1.0
            if tgt is not None and (tgt.get('dead') or tgt.get('hp', 1) <= 0 and 'kind' in tgt):
                tgt = None
                m['tgt'] = None
            if tgt is not None:
                want = bearing(tgt['x'] - m['x'], tgt['y'] - m['y'])
                m['h'] = _wrap_turn(m['h'], want, 115 if m['own'] else 85, dt)
            m['v'] = min(520.0, m['v'] + 260 * dt)
            dx, dy = vec(m['h'], m['v'] * dt)
            m['x'] += dx
            m['y'] += dy
            if random.random() < dt * 40:
                bx, by = vec(m['h'], -12)
                self.fx.add('smoke', m['x'] + bx, m['y'] + by, 0, 0, 0.7, 3, 9, (200, 200, 200))
            hit = None
            if m['own']:
                for f in jt['foes']:
                    if not f.get('dead') and dist(m['x'], m['y'], f['x'], f['y']) < f['r'] + 8 and not (f['kind'] == 'sub' and not f['surf']):
                        hit = f
                        break
            else:
                for fl in jt['flares']:
                    if dist(m['x'], m['y'], fl['x'], fl['y']) < 18:
                        hit = fl
                        fl['life'] = 0
                        break
                if hit is None:
                    for t_ in tg:
                        if dist(m['x'], m['y'], t_['x'], t_['y']) < 24:
                            hit = t_
                            break
            if hit is not None and m['t'] > 0.25:
                m['life'] = 0
                self.fx.explode_art(m['x'], m['y'], 0.9, False)
                self.audio.play('boom_s', .5)
                if m['own']:
                    self.jt_dmg(hit, m['dmg'])
                elif hit is p:
                    self.jt_hurt_p(m['dmg'])
                elif 'hp' in hit and 'kind' not in hit and 'life' not in hit:
                    hit['hp'] -= m['dmg']
                    if hit['hp'] <= 0:
                        self.jt_ally_down(hit)
        jt['missiles'] = [m for m in jt['missiles'] if m['life'] > 0]

    def jt_ship_ai(self, f, dt):
        """Barcos y submarinos: navegan lento y disparan misiles antiaéreos y fuego de artillería antiaérea (con aviso rojo)."""
        jt = self.jt
        p = jt['p']
        dx, dy = vec(f['h'], f['v'] * dt)
        f['x'] += dx
        f['y'] += dy
        dd = dist(f['x'], f['y'], p['x'], p['y'])
        if dd > 1100:                                         # se quedó muy lejos: vuelve hacia el jugador
            f['h'] = _wrap_turn(f['h'], bearing(p['x'] - f['x'], p['y'] - f['y']), 30, dt)
        if random.random() < dt * 5:
            bx, by = vec(f['h'], -f['r'])
            self.fx.add('foam', f['x'] + bx, f['y'] + by, 0, 0, 1.2, 4, 12, (235, 244, 255))
        if f['kind'] == 'destroyer':
            f['aa'] -= dt
            f['fk'] -= dt
            if f['aa'] <= 0 and dd < 760:
                f['aa'] = random.uniform(5.0, 7.5) * max(0.7, 1 - 0.03 * self.wave)
                self.jt_missile(f['x'], f['y'], bearing(p['x'] - f['x'], p['y'] - f['y']), False, p, 16.0)
                self.audio.play('launch', .35)
                self.audio.play('alarm', .25)
            if f['fk'] <= 0 and dd < 650:
                f['fk'] = random.uniform(2.6, 3.6)
                lead = vec(p['h'], p['v'] * 0.9)
                jt['flak'].append(dict(x=p['x'] + lead[0] + random.uniform(-30, 30), y=p['y'] + lead[1] + random.uniform(-30, 30), t=0.0))
        else:
            f['st'] -= dt
            if f['st'] <= 0:
                f['surf'] = not f['surf']
                f['st'] = 5.5 if f['surf'] else 5.0
                f['n'] = 0
                if f['surf']:
                    self.fx.splash(f['x'], f['y'], 1.2)
            if f['surf']:
                f['aa'] -= dt
                if f['aa'] <= 0 and f['n'] < 2 and dd < 800:
                    f['aa'] = 2.4
                    f['n'] += 1
                    self.jt_missile(f['x'], f['y'], bearing(p['x'] - f['x'], p['y'] - f['y']), False, p, 15.0)
                    self.audio.play('launch', .3)

    def jt_ally_down(self, a):
        if a.get('down'):
            return
        a['down'] = True
        a['hp'] = 0
        self.jt['lost'] += 1
        self.fx.explode_art(a['x'], a['y'], 1.2, True)
        self.audio.play('boom_s', .6)
        self.say('piloto', '¡Perdimos un ala! Sigan peleando, capitán.', 'bad')

    # ------------------------------------------------------------------ cierre
    def end_jets(self, won):
        jt = self.jt
        self.go('map')
        if won:
            bonus = 400 + 120 * self.wave + jt['pts']
            self.add_score(bonus)
            self.ammo = min(40, self.ammo + 8)
            self.hull = min(self.hull_max, self.hull + 20)
            self.fuel = min(100.0, self.fuel + 25)
            self.banner('¡ESCUADRÓN VICTORIOSO!', '+%d puntos  |  +8 munición, +20 casco, +25 combustible' % bonus, (130, 255, 190), 4.4)
            self.say('piloto', 'Aterrizamos sin novedad. Buen vuelo, capitán.' if not jt['lost'] else 'Aterrizamos... pero con bajas. Buen vuelo, capitán.', 'ok')
        else:
            self.banner('MISIÓN FRACASADA', 'El F-16 se perdió. Se repone una salida por oleada', (255, 120, 100), 4.0)
            self.say('piloto', 'Piloto eyectado y rescatado. Mejor suerte la próxima.', 'bad')

    # ------------------------------------------------------------------ dibujo
    def jt_plane(self, cv, spr, x, y, h, k=1.0, bank=0.0, nose_down=False, shadow=True):
        ang = (180 - h) if nose_down else -h
        r = pygame.transform.rotozoom(spr, ang, k * (1.0 - abs(bank) / 380))
        if shadow:
            sh = pygame.mask.from_surface(r).to_surface(setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0))
            cv.blit(sh, (int(x) - sh.get_width() // 2 + 22, int(y) - sh.get_height() // 2 + 30))
        cv.blit(r, (int(x) - r.get_width() // 2, int(y) - r.get_height() // 2))

    def draw_jets(self, cv):
        jt = self.jt
        p = jt['p']
        cx, cy = jt['cx'] - W / 2, jt['cy'] - H / 2
        shx = random.uniform(-1, 1) * self.shake * 0.5 if self.shake > 0 else 0
        self.draw_ocean(cv, cx, cy, self.t)
        # nubes (parallax alto)
        A = self.air
        for gx in range(int(cx // 520) - 1, int((cx + W) // 520) + 2):
            for gy in range(int(cy // 480) - 1, int((cy + H) // 480) + 2):
                rnd = random.Random(gx * 7919 + gy * 104729)
                if rnd.random() < 0.55:
                    cl = A['clouds'][rnd.randrange(len(A['clouds']))][0]
                    par = 1.35
                    x = gx * 520 + rnd.uniform(0, 400) - (cx * (par - 1))
                    y = gy * 480 + rnd.uniform(0, 380) - (cy * (par - 1))
                    sh = cl.copy()
                    sh.set_alpha(150)
                    cv.blit(sh, (int(x - cx - cl.get_width() / 2), int(y - cy - cl.get_height() / 2)))
        self.fx.draw(cv, cx, cy)
        # bengalas
        for fl in jt['flares']:
            sx, sy = fl['x'] - cx, fl['y'] - cy
            glow(cv, sx, sy, 16, (255, 220, 150), 0.9)
        # enemigos
        for f in jt['foes']:
            sx, sy = f['x'] - cx, f['y'] - cy
            if f['kind'] == 'destroyer':
                self.blit_ship(cv, 'e_map', f['x'], f['y'], f['h'], cx, cy)
            elif f['kind'] == 'sub':
                self.blit_ship(cv, 's_map', f['x'], f['y'], f['h'], cx, cy, alpha=255 if f['surf'] else 70)
                if not f['surf']:
                    continue
            elif f['kind'] == 'viper':
                self.jt_plane(cv, A['viper'], sx, sy, f['h'], 0.95, nose_down=True)
            elif f['kind'] == 'stealth':
                self.jt_plane(cv, A['stealth'], sx, sy, f['h'], 1.0, nose_down=True)
            elif f['kind'] == 'bomber':
                self.jt_plane(cv, A['bomber'], sx, sy, f['h'], 0.9, nose_down=True)
            else:
                self.jt_plane(cv, A['stealth'], sx, sy, f['h'], 1.45, nose_down=True)
                draw_circ(cv, sx, sy, 40, (255, 70, 60), 40, 2)
            if f.get('flash', 0) > 0:
                glow(cv, sx, sy, f['r'] + 10, (255, 255, 255), 0.5)
            if f['kind'] in ('bomber', 'ace') or f['hp'] < f['max']:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 28, sy - f['r'] - 16, 56, 6))
                pygame.draw.rect(cv, (240, 80, 70), (sx - 27, sy - f['r'] - 15, int(54 * max(0, f['hp']) / f['max']), 4))
        for fk in jt['flak']:
            k_ = fk['t'] / 0.9
            draw_circ(cv, fk['x'] - cx, fk['y'] - cy, 58 * (1.15 - 0.25 * min(1.0, k_)), (255, 70, 60), 40 + 120 * min(1.0, k_), 2)
        # alas
        for a in jt['allies']:
            if a['hp'] > 0:
                self.jt_plane(cv, A['f16'], a['x'] - cx, a['y'] - cy, a['h'], 0.62)
                draw_circ(cv, a['x'] - cx, a['y'] - cy, 24, (110, 255, 160), 60, 1)
        # jugador
        if p['hp'] > 0:
            self.jt_plane(cv, A['f16'], p['x'] - cx, p['y'] - cy, p['h'], 0.82, p['bank'])
            bx, by = vec(p['h'], -34)
            ab = p['v'] > 340
            glow(cv, p['x'] - cx + bx, p['y'] - cy + by, 16 if not ab else 28, (255, 190, 120) if ab else (140, 200, 255), 0.8)
        for m in jt['missiles']:
            sx, sy = m['x'] - cx, m['y'] - cy
            ex, ey = vec(m['h'], 14)
            pygame.draw.line(cv, (230, 230, 230) if m['own'] else (255, 140, 110), (sx - ex, sy - ey), (sx + ex, sy + ey), 4)
            glow(cv, sx - ex, sy - ey, 10, (255, 200, 120), 0.8)
        for b in jt['bullets']:
            sx, sy = b['x'] - cx, b['y'] - cy
            pygame.draw.line(cv, (255, 240, 150) if b['own'] else (255, 120, 90), (sx, sy), (sx - b['vx'] * 0.03, sy - b['vy'] * 0.03), 3)
        # marcador de blanco fijado
        lk = p['lock']
        if lk is not None and not lk.get('dead'):
            sx, sy = lk['x'] - cx, lk['y'] - cy
            ph_ = 0.5 + 0.5 * math.sin(self.t * 10)
            pygame.draw.rect(cv, (255, 90 + int(120 * ph_), 70), (sx - 34, sy - 34, 68, 68), 2)
        # flechas hacia enemigos fuera de pantalla
        for f in jt['foes']:
            sx, sy = f['x'] - cx, f['y'] - cy
            if -20 < sx < W + 20 and -20 < sy < H + 20:
                continue
            a = math.atan2(sy - H / 2, sx - W / 2)
            ex_, ey_ = W / 2 + math.cos(a) * (min(W, H) / 2 - 36), H / 2 + math.sin(a) * (min(W, H) / 2 - 36)
            col = (255, 90, 80) if f['kind'] in ('bomber', 'ace') else (255, 170, 90)
            pts = [(ex_ + math.cos(a) * 12, ey_ + math.sin(a) * 12), (ex_ + math.cos(a + 2.5) * 10, ey_ + math.sin(a + 2.5) * 10), (ex_ + math.cos(a - 2.5) * 10, ey_ + math.sin(a - 2.5) * 10)]
            pygame.draw.polygon(cv, col, pts)
        self.jt_hud(cv, cx, cy)

    def jt_hud(self, cv, cx, cy):
        jt = self.jt
        p = jt['p']
        self.bar(cv, W // 2 - 200, 20, 400, 22, max(0.0, p['hp']) / p['max'], (110, 235, 150) if p['hp'] > 35 else (255, 110, 90), 'F-16')
        self.text(cv, 'OLEADA %d/%d' % (jt['stage'] + 1, STAGES), self.f_m, (255, 225, 140), W // 2, 50, 'c')
        left = len([f for f in jt['foes'] if not f.get('dead')]) + len(jt['spawns'])
        self.text(cv, 'ENEMIGOS %d   |   ALAS %d/2' % (left, len([a for a in jt['allies'] if a['hp'] > 0])), self.f_s, (255, 170, 150), W // 2, 76, 'c')
        self.bar(cv, 30, H - 110, 240, 16, p['boost'], (255, 190, 100), 'POSTQUEMADOR (SHIFT)')
        self.text(cv, 'MISILES %d  (Q / clic der.)' % p['msl'], self.f_s, (200, 230, 255), 30, H - 84)
        self.text(cv, 'BENGALAS %d  (F)' % p['flares'], self.f_s, (255, 230, 170), 30, H - 60)
        self.text(cv, 'VELOCIDAD %d' % int(p['v']), self.f_s, (170, 255, 200), 30, H - 36)
        self.text(cv, 'Puntos: %d' % jt['pts'], self.f_s, (200, 225, 250), W - 30, H - 36, 'r')
        # radar
        rx, ry, rr = W - 90, H - 100, 70
        draw_circ(cv, rx, ry, rr, (10, 40, 30), 150)
        pygame.draw.circle(cv, (80, 220, 150), (rx, ry), rr, 1)
        pygame.draw.circle(cv, (80, 220, 150), (rx, ry), rr // 2, 1)
        for f in jt['foes']:
            dx, dy = (f['x'] - p['x']) / 1400 * rr, (f['y'] - p['y']) / 1400 * rr
            d = math.hypot(dx, dy)
            if d > rr - 3:
                dx, dy = dx / d * (rr - 3), dy / d * (rr - 3)
            if f['kind'] in ('destroyer', 'sub'):
                pygame.draw.rect(cv, (255, 170, 70) if f['kind'] == 'destroyer' or f['surf'] else (120, 120, 130), (int(rx + dx) - 3, int(ry + dy) - 3, 6, 6))
            else:
                pygame.draw.circle(cv, (255, 80, 70), (int(rx + dx), int(ry + dy)), 4 if f['kind'] in ('bomber', 'ace') else 3)
        for a in jt['allies']:
            if a['hp'] > 0:
                dx, dy = (a['x'] - p['x']) / 1400 * rr, (a['y'] - p['y']) / 1400 * rr
                if math.hypot(dx, dy) < rr - 3:
                    pygame.draw.circle(cv, (110, 255, 160), (int(rx + dx), int(ry + dy)), 3)
        ex, ey = vec(p['h'], 10)
        pygame.draw.circle(cv, (255, 255, 255), (rx, ry), 3)
        if p['warn'] > 0 and int(self.t * 6) % 2 == 0:
            self.text(cv, '¡MISIL ENTRANTE! (F: BENGALAS)', self.f_m, (255, 90, 80), W // 2, 140, 'c')
        ph = jt['phase']
        if ph == 'intro':
            self.text(cv, 'DESPEGANDO...', self.f_xl, (150, 220, 255), W // 2, 190, 'c')
        elif ph == 'break':
            self.text(cv, 'CAMBIO DE OLEADA', self.f_l, (150, 230, 255), W // 2, 170, 'c')
        if p['hit'] > 0:
            self.hurt_surf.set_alpha(int(255 * clamp(p['hit'] * 3, 0, 1) * 0.45))
            cv.blit(self.hurt_surf, (0, 0))
