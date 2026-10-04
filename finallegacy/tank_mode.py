"""Combate urbano con tanques en primera persona (estilo Battlezone, texturizado)."""
import math
import pygame
import random
from .common import H, Particles, TK_HP, W, WIN_WAVE, angle_diff, clamp, draw_circ, glow, lerp
from .tk_art import TK_ANG, TK_FOG, TK_NL


class TankMixin:
    # ---------------------------------------------------------- COMBATE URBANO CON TANQUES (estilo Battlezone)
    TK_EYE, TK_F, TK_NEAR, TK_A = 2.3, 560.0, 0.5, 125.0

    TK_VP = pygame.Rect(40, 118, 1020, 520)

    def tk_make_world(self, city):
        rnd = random.Random(city['seed'] * 31 + self.wave)
        blds = [dict(x=0.0, z=0.0, hw=15.0, hd=15.0, h=42.0, hall=True, tx=0, uo=0.0)]
        for i in range(-2, 3):
            for j in range(-2, 3):
                if i == 0 and j == 0 or rnd.random() < 0.1:
                    continue
                cx, cz = i * 46.0, j * 46.0
                if rnd.random() < 0.4:
                    for ox, oz in ((-9.5, -9.5), (9.5, 9.5)):
                        blds.append(dict(x=cx + ox + rnd.uniform(-1.5, 1.5), z=cz + oz + rnd.uniform(-1.5, 1.5),
                                         hw=rnd.uniform(5, 7.5), hd=rnd.uniform(5, 7.5), h=rnd.uniform(6, 24), hall=False,
                                         tx=rnd.randrange(6), uo=rnd.random()))
                else:
                    blds.append(dict(x=cx + rnd.uniform(-4, 4), z=cz + rnd.uniform(-4, 4), hw=rnd.uniform(8, 13),
                                     hd=rnd.uniform(8, 13), h=rnd.uniform(8, 30), hall=False, tx=rnd.randrange(6), uo=rnd.random()))
        mount = [rnd.uniform(14, 46) for _ in range(120)]
        for i in range(1, 119):
            mount[i] = (mount[i - 1] + mount[i] + mount[(i + 1) % 120]) / 3
        sky = dict(mount=mount, city=[(rnd.uniform(0, 360), rnd.uniform(1.2, 3.2), rnd.uniform(10, 70)) for _ in range(90)],
                   stars=[(rnd.uniform(0, 360), rnd.uniform(0.04, 0.9), rnd.randint(1, 2)) for _ in range(110)])
        return blds, sky

    def start_tank(self, city):
        w = self.wave
        blds, sky = self.tk_make_world(city)
        n = min(5 + 2 * w, 16)
        n_super = min(w // 2, 4)
        n_kami = min(w - 1, 4) if w >= 2 else 0
        n_arty = min(w - 2, 3) if w >= 3 else 0
        n_heli = min(w - 3, 3) if w >= 4 else 0
        kinds = (['super'] * n_super + ['kami'] * n_kami + ['arty'] * n_arty + ['heli'] * n_heli +
                 ['tank'] * max(2, n - n_super - n_kami - n_arty) + ['missile'] * (w // 2 if w >= 3 else 0))
        random.shuffle(kinds)
        queue = sorted([(random.uniform(1.5, 10 + n * 2.2), kd) for kd in kinds], key=lambda q: q[0])
        if w % 4 == 0:
            kinds.append('boss')
            queue.append((14 + n, 'boss'))
        wx = ('clear', 'fog', 'night')[(w - 1) % 3]
        self.fx = Particles()
        self.k = dict(city=city, blds=blds, sky=sky, t=0.0, tanks=[], missiles=[], shells=[], pshells=[], debris=[], booms=[],
                      cracks=[], helis=[], wx=wx, queue=queue, total=len(kinds), kills=0, phase='play', pt=0.0, fail=False,
                      city0=city['hp'], hurt=0.0, sweep=0.0, inrange=False, msg_t=0.0, msg='',
                      p=dict(x=0.0, z=-112.0, yaw=0.0, v=0.0, hp=TK_HP, cd=0.0, blocked=0.0, dead=False))
        self.go('tank')
        if wx != 'clear':
            self.tk_say('CLIMA: ' + ('NIEBLA ESPESA' if wx == 'fog' else 'NOCHE CERRADA'))
        self.banner('¡INVASIÓN BLINDADA!', 'Defendé %s desde tu tanque | W/S: avanzar | A/D: girar | ESPACIO: cañón' % city['name'],
                    (120, 255, 160), 4.2)

    def tk_free(self, x, z, r):
        for b in self.k['blds']:
            nx, nz = clamp(x, b['x'] - b['hw'], b['x'] + b['hw']), clamp(z, b['z'] - b['hd'], b['z'] + b['hd'])
            if (x - nx) ** 2 + (z - nz) ** 2 < r * r:
                return False
        return abs(x) < self.TK_A - 3 and abs(z) < self.TK_A - 3

    def tk_move(self, x, z, r):
        lim = self.TK_A - 3
        x, z = clamp(x, -lim, lim), clamp(z, -lim, lim)
        blocked = False
        for b in self.k['blds']:
            nx, nz = clamp(x, b['x'] - b['hw'], b['x'] + b['hw']), clamp(z, b['z'] - b['hd'], b['z'] + b['hd'])
            dx, dz = x - nx, z - nz
            d2 = dx * dx + dz * dz
            if d2 < r * r:
                blocked = True
                if d2 > 1e-9:
                    d = math.sqrt(d2)
                    x, z = nx + dx / d * r, nz + dz / d * r
                else:
                    ox, oz = b['hw'] - abs(x - b['x']), b['hd'] - abs(z - b['z'])
                    if ox < oz:
                        x = b['x'] + math.copysign(b['hw'] + r, x - b['x'])
                    else:
                        z = b['z'] + math.copysign(b['hd'] + r, z - b['z'])
        return x, z, blocked

    def tk_los(self, x0, z0, x1, z1):
        dx, dz = x1 - x0, z1 - z0
        for b in self.k['blds']:
            tmin, tmax = 0.0, 1.0
            for o, d, lo, hi in ((x0, dx, b['x'] - b['hw'], b['x'] + b['hw']), (z0, dz, b['z'] - b['hd'], b['z'] + b['hd'])):
                if abs(d) < 1e-9:
                    if o < lo or o > hi:
                        tmax = -1.0
                        break
                else:
                    t1, t2 = (lo - o) / d, (hi - o) / d
                    if t1 > t2:
                        t1, t2 = t2, t1
                    tmin, tmax = max(tmin, t1), min(tmax, t2)
                    if tmin > tmax:
                        break
            if tmin <= tmax:
                return False
        return True

    def tk_say(self, s):
        self.k['msg'], self.k['msg_t'] = s, 1.4

    def tk_fire(self):
        k = self.k
        p = k['p']
        if self.state != 'tank' or p['dead'] or p['cd'] > 0 or k['phase'] != 'play':
            return
        p['cd'] = 0.7
        sx, sz = math.sin(math.radians(p['yaw'])), math.cos(math.radians(p['yaw']))
        k['pshells'].append(dict(x=p['x'] + sx * 3, y=1.9, z=p['z'] + sz * 3, vx=sx * 95, vz=sz * 95, life=1.5))
        self.audio.play('cannon', .8)
        self.shake = max(self.shake, 3)

    def tk_enemy_shell(self, e, ang, sp=38, dmg=18, life=2.6):
        k = self.k
        a = math.radians(ang)
        k['shells'].append(dict(x=e['x'] + math.sin(a) * 3.4, y=1.9, z=e['z'] + math.cos(a) * 3.4,
                                vx=math.sin(a) * sp, vz=math.cos(a) * sp, life=life, dmg=dmg))
        d = math.hypot(e['x'] - k['p']['x'], e['z'] - k['p']['z'])
        self.audio.play('launch', clamp(1.0 - d / 120, 0.1, 0.7))

    def tk_hurt(self, dmg):
        k = self.k
        p = k['p']
        if p['dead'] or k['phase'] != 'play':
            return
        p['hp'] -= dmg
        k['hurt'] = 0.7
        self.shake = max(self.shake, 10)
        self.audio.play('hit', .8)
        vp = self.TK_VP
        cx, cy = random.uniform(vp.x + 120, vp.right - 120), random.uniform(vp.y + 80, vp.bottom - 80)
        pts = []
        for _ in range(random.randint(5, 7)):
            a = random.uniform(0, 6.283)
            ln = random.uniform(40, 150)
            seg = [(cx, cy)]
            for s_ in range(1, 5):
                seg.append((cx + math.cos(a + random.uniform(-.25, .25)) * ln * s_ / 4, cy + math.sin(a + random.uniform(-.25, .25)) * ln * s_ / 4))
            pts.append(seg)
        k['cracks'] += pts
        self.tk_say('¡IMPACTO!  ARMADURA %d' % max(0, p['hp']))

    def tk_boom(self, x, z, size, life=1.1, y=1.4):
        self.k['booms'].append(dict(x=x, y=y, z=z, size=size, life=life, age=0.0))

    def tk_debris(self, x, z, n):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            sp = random.uniform(4, 15)
            self.k['debris'].append(dict(x=x, y=random.uniform(0.6, 2.2), z=z, vx=math.cos(a) * sp, vy=random.uniform(5, 16),
                                         vz=math.sin(a) * sp, life=random.uniform(0.9, 1.6)))

    def tk_kill(self, e, kind):
        k = self.k
        if e in k['tanks']:
            k['tanks'].remove(e)
        if e in k['missiles']:
            k['missiles'].remove(e)
        if e in k['helis']:
            k['helis'].remove(e)
        k['kills'] += 1
        pts = {'tank': 300, 'super': 600, 'missile': 150, 'heli': 500}[kind]
        if e.get('boss'):
            pts = 3000
        elif e.get('role') == 'arty':
            pts = 450
        self.add_score(pts)
        self.pop('+%d' % pts, W // 2, 180, (120, 255, 160))
        self.audio.play('boom_s', .8)
        self.shake = max(self.shake, 6)
        self.tk_debris(e['x'], e['z'], 22)
        self.tk_boom(e['x'], e['z'], 6.5)
        if e.get('boss'):
            k['p']['hp'] = min(TK_HP, k['p']['hp'] + 60)
            self.tk_say('¡TANQUE JEFE ELIMINADO! +60 ARMADURA')
        elif kind == 'super':
            k['p']['hp'] = min(TK_HP, k['p']['hp'] + 20)
            self.tk_say('REPARACION: +20 ARMADURA')

    def tk_steer(self, e, want, speed, dt, rate):
        chosen = want
        if not self.tk_free(e['x'] + math.sin(math.radians(want)) * 8, e['z'] + math.cos(math.radians(want)) * 8, 3.2):
            for off in (30, 60, 95, 135, 180):
                h = (want + off * e['bias']) % 360
                if self.tk_free(e['x'] + math.sin(math.radians(h)) * 8, e['z'] + math.cos(math.radians(h)) * 8, 3.2):
                    chosen = h
                    break
        diff = angle_diff(e['h'], chosen)
        e['h'] = (e['h'] + clamp(diff, -rate * dt, rate * dt)) % 360
        if abs(diff) < 70:
            a = math.radians(e['h'])
            nx, nz, blk = self.tk_move(e['x'] + math.sin(a) * speed * dt, e['z'] + math.cos(a) * speed * dt, 3.4)
            e['stuck'] = e['stuck'] + dt if blk else max(0.0, e['stuck'] - dt)
            if e['stuck'] > 1.0:
                e['bias'] *= -1
                e['stuck'] = 0.0
            e['x'], e['z'] = nx, nz
            e['tread'] += speed * dt

    def tk_ai(self, e, dt):
        k = self.k
        p = k['p']
        w = self.wave
        alive = not p['dead']
        dx, dz = p['x'] - e['x'], p['z'] - e['z']
        d = math.hypot(dx, dz)
        to_p = math.degrees(math.atan2(dx, dz)) % 360
        to_h = math.degrees(math.atan2(-e['x'], -e['z'])) % 360
        dh = math.hypot(e['x'], e['z'])
        sieging = dh < 40
        role = e.get('role')
        los = alive and d < (135 if role == 'arty' else 85) and self.tk_los(e['x'], e['z'], p['x'], p['z'])
        spd = (8.5 if e['kind'] == 'tank' else 12.0) * (1 + 0.03 * w)
        rate = 42 if e['kind'] == 'tank' else 58
        e['cd'] -= dt
        if role == 'kami':
            # tanque suicida: embiste al jugador
            self.tk_steer(e, to_p if alive else to_h, 21 + w, dt, 95)
            e['tur'] = e['h']
            if alive and d < 5.2:
                self.tk_hurt(36)
                self.tk_boom(e['x'], e['z'], 7.5)
                self.tk_debris(e['x'], e['z'], 26)
                self.audio.play('boom_l', .8)
                if e in k['tanks']:
                    k['tanks'].remove(e)
                    k['kills'] += 1
            elif dh < 9:
                k['city']['hp'] = max(0.0, k['city']['hp'] - 8)
                self.tk_boom(e['x'], e['z'], 7.0)
                if e in k['tanks']:
                    k['tanks'].remove(e)
                    k['kills'] += 1
            return
        if role == 'arty':
            e['tur'] = (e['tur'] + clamp(angle_diff(e['tur'], to_p), -70 * dt, 70 * dt)) % 360
            if d < 70:
                self.tk_steer(e, (to_p + 180) % 360, spd, dt, rate)
            elif d > 100:
                self.tk_steer(e, to_p, spd, dt, rate)
            else:
                self.tk_steer(e, (to_p + 90 * e['sd']) % 360, spd * 0.5, dt, rate)
            if los and e['cd'] <= 0 and abs(angle_diff(e['tur'], to_p)) < 3:
                e['cd'] = random.uniform(5.0, 7.0)
                self.tk_enemy_shell(e, e['tur'] + random.uniform(-1.2, 1.2), 62, 28, 3.2)
                self.tk_say('¡ARTILLERÍA PESADA!')
            e['sd_t'] -= dt
            if e['sd_t'] <= 0:
                e['sd'] *= -1
                e['sd_t'] = random.uniform(2, 5)
            return
        if los:
            if d > 55:
                self.tk_steer(e, to_p, spd, dt, rate)
            elif d < 26:
                self.tk_steer(e, (to_p + 180) % 360, spd * 0.8, dt, rate)
            else:
                self.tk_steer(e, (to_p + 90 * e['sd']) % 360, spd * 0.55, dt, rate)
            e['tur'] = (e['tur'] + clamp(angle_diff(e['tur'], to_p), -95 * dt, 95 * dt)) % 360
            if e['cd'] <= 0 and abs(angle_diff(e['tur'], to_p)) < 4:
                e['cd'] = random.uniform(3.0, 4.6) / (1 + 0.07 * w)
                err = max(1.5, 5.0 - 0.4 * w)
                if e.get('boss'):
                    e['cd'] *= 0.7
                    for off in (-9, 0, 9):
                        self.tk_enemy_shell(e, e['tur'] + off + random.uniform(-2, 2), 40, 20)
                else:
                    self.tk_enemy_shell(e, e['tur'] + random.uniform(-err, err))
        elif sieging:
            e['tur'] = (e['tur'] + clamp(angle_diff(e['tur'], to_h), -95 * dt, 95 * dt)) % 360
            k['city']['hp'] = max(0.0, k['city']['hp'] - (0.6 if e['kind'] == 'tank' else 0.9) * (2.2 if e.get('boss') else 1) * dt)
            if e['cd'] <= 0 and abs(angle_diff(e['tur'], to_h)) < 6:
                e['cd'] = random.uniform(2.2, 3.4)
                self.tk_enemy_shell(e, e['tur'])
        else:
            self.tk_steer(e, to_h, spd, dt, rate)
            e['tur'] = (e['tur'] + clamp(angle_diff(e['tur'], e['h']), -95 * dt, 95 * dt)) % 360
        e['sd_t'] -= dt
        if e['sd_t'] <= 0:
            e['sd'] *= -1
            e['sd_t'] = random.uniform(2, 5)

    def upd_tank(self, dt):
        k = self.k
        p = k['p']
        keys = pygame.key.get_pressed()
        k['t'] += dt
        k['hurt'] = max(0.0, k['hurt'] - dt)
        k['msg_t'] = max(0.0, k['msg_t'] - dt)
        k['sweep'] = (k['sweep'] + dt * 0.8) % 1.0
        p['cd'] = max(0.0, p['cd'] - dt)
        if not p['dead']:
            turn = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            thr = (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0) - (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0)
            p['yaw'] = (p['yaw'] + turn * 68 * dt) % 360
            tgt = 15.0 if thr > 0 else (-8.0 if thr < 0 else 0.0)
            p['v'] += (tgt - p['v']) * min(1.0, dt * 4)
            a = math.radians(p['yaw'])
            nx, nz, blk = self.tk_move(p['x'] + math.sin(a) * p['v'] * dt, p['z'] + math.cos(a) * p['v'] * dt, 2.6)
            p['blocked'] = 0.3 if (blk and thr) else max(0.0, p['blocked'] - dt)
            if blk and thr:
                p['v'] *= 0.5
            p['x'], p['z'] = nx, nz
            self.audio.engine_vol(0.12 + abs(p['v']) / 15 * 0.6 + abs(turn) * 0.1)
            if p['blocked'] > 0:
                self.tk_say('MOVIMIENTO BLOQUEADO POR OBJETO')
        else:
            self.audio.engine_vol(0)
        if k['phase'] == 'play':
            while k['queue'] and k['queue'][0][0] <= k['t'] and len(k['tanks']) + len(k['missiles']) + len(k['helis']) < 6:
                _, kd = k['queue'].pop(0)
                side = random.choice((0, 1, 2, 3))
                u = random.uniform(-100, 100)
                ex, ez = ((u, 118), (u, -118), (118, u), (-118, u))[side]
                if kd == 'missile':
                    k['missiles'].append(dict(x=ex, z=ez, h=0.0, t=0.0, kind='missile'))
                    self.audio.play('alarm', .5)
                    self.tk_say('¡MISIL GUIADO DETECTADO!')
                elif kd == 'heli':
                    k['helis'].append(dict(x=ex, z=ez, h=0.0, hp=2, cd=random.uniform(1.5, 3), ang=random.uniform(0, 6.28),
                                           kind='heli', rot=0.0))
                    self.tk_say('¡HELICÓPTERO DE ATAQUE!')
                    self.audio.play('alarm', .5)
                else:
                    hall = math.degrees(math.atan2(-ex, -ez)) % 360
                    role = kd if kd in ('kami', 'arty') else None
                    boss = kd == 'boss'
                    kind = 'super' if kd in ('super', 'boss') else 'tank'
                    hp = 12 + 2 * self.wave if boss else (2 if kind == 'super' else 1)
                    k['tanks'].append(dict(x=ex, z=ez, h=hall, tur=hall, kind=kind, hp=hp, cd=random.uniform(1.5, 3.5),
                                           bias=random.choice((-1, 1)), sd=random.choice((-1, 1)), sd_t=random.uniform(1, 4),
                                           stuck=0.0, tread=0.0, role=role, boss=boss, rad=6.8 if boss else 4.4,
                                           big=1.5 if boss else 1.0, mhp=hp))
                    if boss:
                        self.banner('¡TANQUE JEFE!', 'Blindaje pesado - apuntá a su torreta', (255, 90, 60), 3.0)
                        self.audio.play('alarm', .7)
        for e in k['tanks'][:]:
            self.tk_ai(e, dt)
        for e in k['helis'][:]:
            e['ang'] += dt * 0.45
            e['rot'] += dt * 30
            tx, tz = p['x'] + math.sin(e['ang']) * 46, p['z'] + math.cos(e['ang']) * 46
            tx, tz = clamp(tx, -110, 110), clamp(tz, -110, 110)
            dx_, dz_ = tx - e['x'], tz - e['z']
            dd = math.hypot(dx_, dz_) or 1
            e['x'] += dx_ / dd * min(dd, 20) * dt * 1.2
            e['z'] += dz_ / dd * min(dd, 20) * dt * 1.2
            e['h'] = math.degrees(math.atan2(p['x'] - e['x'], p['z'] - e['z'])) % 360
            e['cd'] -= dt
            if e['cd'] <= 0 and not p['dead']:
                e['cd'] = random.uniform(1.4, 2.4)
                self.tk_enemy_shell(e, e['h'] + random.uniform(-4, 4), 44, 9)
        for i, a_ in enumerate(k['tanks']):
            for b_ in k['tanks'][i + 1:]:
                d = math.hypot(a_['x'] - b_['x'], a_['z'] - b_['z'])
                if 0 < d < 7.5:
                    push = (7.5 - d) / 2
                    ux, uz = (a_['x'] - b_['x']) / d, (a_['z'] - b_['z']) / d
                    a_['x'], a_['z'] = a_['x'] + ux * push, a_['z'] + uz * push
                    b_['x'], b_['z'] = b_['x'] - ux * push, b_['z'] - uz * push
        for m in k['missiles'][:]:
            m['t'] += dt
            dx, dz = p['x'] - m['x'], p['z'] - m['z']
            want = math.degrees(math.atan2(dx, dz)) + 28 * math.sin(m['t'] * 5)
            m['h'] = (m['h'] + clamp(angle_diff(m['h'], want), -150 * dt, 150 * dt)) % 360
            a = math.radians(m['h'])
            m['x'] += math.sin(a) * 23 * dt
            m['z'] += math.cos(a) * 23 * dt
            if any(abs(m['x'] - b['x']) < b['hw'] and abs(m['z'] - b['z']) < b['hd'] for b in k['blds']):
                k['missiles'].remove(m)
                self.tk_debris(m['x'], m['z'], 12)
                self.tk_boom(m['x'], m['z'], 3.5, 0.9)
                self.audio.play('boom_s', .5)
                continue
            if not p['dead'] and math.hypot(dx, dz) < 3.2:
                k['missiles'].remove(m)
                self.tk_hurt(30)
                self.audio.play('boom_s', .8)
        for s in k['shells'][:]:
            s['x'] += s['vx'] * dt
            s['z'] += s['vz'] * dt
            s['life'] -= dt
            hit_b = any(abs(s['x'] - b['x']) < b['hw'] and abs(s['z'] - b['z']) < b['hd'] for b in k['blds'])
            if s['life'] <= 0 or abs(s['x']) > 140 or abs(s['z']) > 140 or hit_b:
                k['shells'].remove(s)
                if hit_b:
                    self.tk_boom(s['x'], s['z'], 2.2, 0.6)
            elif not p['dead'] and math.hypot(s['x'] - p['x'], s['z'] - p['z']) < 2.9:
                k['shells'].remove(s)
                self.tk_hurt(s.get('dmg', 18))
        for s in k['pshells'][:]:
            s['x'] += s['vx'] * dt
            s['z'] += s['vz'] * dt
            s['life'] -= dt
            gone = s['life'] <= 0 or abs(s['x']) > 140 or abs(s['z']) > 140
            if not gone and any(abs(s['x'] - b['x']) < b['hw'] and abs(s['z'] - b['z']) < b['hd'] for b in k['blds']):
                gone = True
                self.tk_boom(s['x'], s['z'], 2.2, 0.6, s['y'])
                for _ in range(8):
                    a = random.uniform(0, 6.283)
                    k['debris'].append(dict(x=s['x'], y=s['y'], z=s['z'], vx=math.cos(a) * 5, vy=random.uniform(2, 8),
                                            vz=math.sin(a) * 5, life=0.6))
            if not gone:
                for e in k['tanks'] + k['missiles'] + k['helis']:
                    if math.hypot(s['x'] - e['x'], s['z'] - e['z']) < (e.get('rad', 4.4) if e['kind'] != 'missile' else 2.4):
                        gone = True
                        if e['kind'] == 'missile':
                            self.tk_kill(e, 'missile')
                        else:
                            e['hp'] -= 1
                            if e['hp'] <= 0:
                                self.tk_kill(e, e['kind'])
                            else:
                                self.audio.play('hit', .6)
                                self.tk_say('JEFE: %d%%' % (100 * e['hp'] // e['mhp']) if e.get('boss') else 'IMPACTO EN BLINDADO')
                                self.tk_boom(e['x'], e['z'], 2.5, 0.5, 2.5)
                        break
            if gone and s in k['pshells']:
                k['pshells'].remove(s)
        for bm in k['booms'][:]:
            bm['age'] += dt
            if bm['age'] >= bm['life']:
                k['booms'].remove(bm)
        for d_ in k['debris'][:]:
            d_['life'] -= dt
            d_['x'] += d_['vx'] * dt
            d_['z'] += d_['vz'] * dt
            d_['vy'] -= 24 * dt
            d_['y'] = max(0.0, d_['y'] + d_['vy'] * dt)
            if d_['life'] <= 0:
                k['debris'].remove(d_)
        if len(k['debris']) > 260:
            del k['debris'][:60]
        near = [e for e in k['tanks'] if not p['dead'] and math.hypot(e['x'] - p['x'], e['z'] - p['z']) < 75]
        aligned = False
        for e in near:
            if abs(angle_diff(p['yaw'], math.degrees(math.atan2(e['x'] - p['x'], e['z'] - p['z'])))) < 10:
                aligned = True
        if aligned and not k['inrange']:
            self.audio.play('ping', .5)
        k['inrange'] = aligned
        city = k['city']
        if not p['dead'] and p['hp'] <= 0:
            p['dead'] = True
            self.audio.play('boom_l')
            self.shake = 18
            if k['phase'] == 'play':
                k['phase'], k['fail'], k['pt'] = 'result', True, -0.8
                self.banner('¡TANQUE DESTRUIDO!', 'La ciudad queda sin defensa', (255, 80, 70), 3.0)
        if city['hp'] <= 0 and not city['dead']:
            city['dead'] = True
            self.audio.play('boom_l')
            self.shake = 22
            if k['phase'] == 'play':
                k['phase'], k['fail'], k['pt'] = 'result', True, 0.0
            self.banner('¡CIUDAD CAPTURADA!', city['name'], (255, 70, 60), 3.0)
        if k['phase'] == 'play' and not k['queue'] and not k['tanks'] and not k['missiles'] and not k['helis']:
            k['phase'], k['pt'] = 'result', 0.0
            bonus = 400 + (400 if city['hp'] >= k['city0'] - 0.01 else 0)
            self.add_score(bonus)
            self.audio.play('win', .7)
            self.banner('¡CIUDAD DEFENDIDA!', 'Bajas: %d   Bonus +%d' % (k['kills'], bonus), (120, 255, 160), 3.0)
        if k['phase'] == 'result':
            k['pt'] += dt
            if k['pt'] > 3.0:
                self.end_tank()

    def end_tank(self):
        k = self.k
        city = k['city']
        if k['fail'] and not city['dead']:
            city['hp'] = max(0.0, city['hp'] - 30)
            if city['hp'] <= 0:
                city['dead'] = True
        self.warned = False
        self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        if all(c['dead'] for c in self.cities):
            return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---- dibujo en primera persona (texturizado)
    TK_CW = 3

    def make_tk_backdrops(self):
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        sh = hor - vp.y
        sky = pygame.Surface((vp.w, sh))
        for y in range(sh):
            f = y / sh
            if f < 0.55:
                g = f / 0.55
                c = (int(lerp(8, 52, g)), int(lerp(10, 28, g)), int(lerp(32, 78, g)))
            else:
                g = (f - 0.55) / 0.45
                c = (int(lerp(52, 236, g ** 1.4)), int(lerp(28, 124, g ** 1.4)), int(lerp(78, 92, g)))
            pygame.draw.line(sky, c, (0, y), (vp.w, y))
        fh = vp.bottom - hor
        floor = pygame.Surface((vp.w, fh))
        for y in range(fh):
            f = y / fh
            pygame.draw.line(floor, (int(lerp(122, 30, f ** 0.6)), int(lerp(80, 32, f ** 0.6)), int(lerp(104, 40, f ** 0.6))), (0, y), (vp.w, y))
        moon = pygame.Surface((120, 120), pygame.SRCALPHA)
        for r in range(58, 0, -2):
            pygame.draw.circle(moon, (255, 244, 210, int(46 * (1 - r / 58) ** 1.5)), (60, 60), r)
        pygame.draw.circle(moon, (236, 232, 210), (60, 60), 30)
        pygame.draw.circle(moon, (252, 250, 236), (54, 54), 26)
        for ox, oy, rr in ((-9, -6, 7), (10, 8, 9), (4, -14, 4), (-12, 12, 5)):
            pygame.draw.circle(moon, (200, 196, 176), (60 + ox, 60 + oy), rr)
            pygame.draw.circle(moon, (222, 218, 198), (60 + ox - 1, 60 + oy - 1), max(1, rr - 2))
        return sky.convert(), floor.convert(), moon.convert_alpha()

    def tk_prep(self):
        a = math.radians(self.k['p']['yaw'])
        self._ks, self._kc = math.sin(a), math.cos(a)

    def tk_cam(self, x, y, z):
        p = self.k['p']
        dx, dz = x - p['x'], z - p['z']
        return dx * self._kc - dz * self._ks, y - self.TK_EYE, dx * self._ks + dz * self._kc

    def tk_prj(self, c):
        vp = self.TK_VP
        return vp.centerx + self.TK_F * c[0] / c[2], vp.y + int(vp.h * 0.55) - self.TK_F * c[1] / c[2]

    def tk_clip(self, pts):
        near, out = self.TK_NEAR, []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            ain, bin_ = a[2] >= near, b[2] >= near
            if ain:
                out.append(a)
            if ain != bin_:
                t = (near - a[2]) / (b[2] - a[2])
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, near))
        return out

    def tk_clip_seg(self, a, b):
        near = self.TK_NEAR
        if a[2] < near and b[2] < near:
            return None
        if a[2] < near:
            t = (near - a[2]) / (b[2] - a[2])
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, near)
        elif b[2] < near:
            t = (near - b[2]) / (a[2] - b[2])
            b = (b[0] + (a[0] - b[0]) * t, b[1] + (a[1] - b[1]) * t, near)
        return a, b

    def tk_line(self, cv, a, b, col, w=1):
        seg = self.tk_clip_seg(a, b)
        if seg:
            pygame.draw.line(cv, col, self.tk_prj(seg[0]), self.tk_prj(seg[1]), w)

    def tk_ground_poly(self, cv, pts, col, edge=None):
        q = self.tk_clip([self.tk_cam(x, 0, z) for x, z in pts])
        if len(q) < 3:
            return
        sp = [self.tk_prj(v) for v in q]
        pygame.draw.polygon(cv, col, sp)
        if edge:
            pygame.draw.lines(cv, edge, True, sp, 1)

    def tk_face(self, strips, x0, z0, x1, z1, y0, y1, tex, u_scale, uoff, vs, vo, side, ground):
        vp = self.TK_VP
        F, NEAR = self.TK_F, self.TK_NEAR
        p = self.k['p']
        s_, c_ = self._ks, self._kc
        dx0, dz0, dx1, dz1 = x0 - p['x'], z0 - p['z'], x1 - p['x'], z1 - p['z']
        cx0, cz0 = dx0 * c_ - dz0 * s_, dx0 * s_ + dz0 * c_
        cx1, cz1 = dx1 * c_ - dz1 * s_, dx1 * s_ + dz1 * c_
        u0, u1 = 0.0, 1.0
        if cz0 < NEAR and cz1 < NEAR:
            return
        if cz0 < NEAR:
            t = (NEAR - cz0) / (cz1 - cz0)
            cx0, cz0, u0 = cx0 + (cx1 - cx0) * t, NEAR, t
        elif cz1 < NEAR:
            t = (NEAR - cz1) / (cz0 - cz1)
            cx1, cz1, u1 = cx1 + (cx0 - cx1) * t, NEAR, 1 - t
        xa, xb = vp.centerx + F * cx0 / cz0, vp.centerx + F * cx1 / cz1
        ia, ib = 1.0 / cz0, 1.0 / cz1
        if xa > xb:
            xa, xb, ia, ib, u0, u1 = xb, xa, ib, ia, u1, u0
        if xb <= vp.x or xa >= vp.right or xb - xa < 0.5:
            return
        CW = self.TK_CW
        hor = vp.y + int(vp.h * 0.55)
        EYE = self.TK_EYE
        c0 = max(0, int((xa - vp.x) // CW))
        c1 = min((vp.w - 1) // CW, int((xb - vp.x) // CW))
        uz0, uz1 = u0 * ia, u1 * ib
        tw = tex['tw']
        inv_w = 1.0 / (xb - xa)
        fy1, fy0 = F * (y1 - EYE), F * (y0 - EYE)
        for ci in range(c0, c1 + 1):
            s = (vp.x + ci * CW + CW * 0.5 - xa) * inv_w
            s = 0.0 if s < 0 else (1.0 if s > 1 else s)
            invz = ia + (ib - ia) * s
            z = 1.0 / invz
            u = (uz0 + (uz1 - uz0) * s) * z
            strips.append((z, ci, hor - fy1 * invz, hor - fy0 * invz, tex, side, int((u * u_scale + uoff) * tw) % tw, vs, vo, ground))

    def tk_add_box(self, strips, cx, cz, hw, hd, y0, y1, rot, tex, tile_w, tile_h=None, uoff=0.0):
        p = self.k['p']
        a = math.radians(rot)
        s, c = math.sin(a), math.cos(a)
        wc = [(cx + lx * c + lz * s, cz - lx * s + lz * c) for lx, lz in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
        nrm = ((0, -1), (1, 0), (0, 1), (-1, 0))
        if tile_h:
            vs, vo = 1.0 / tile_h, 0.0
        else:
            vs = 1.0 / (y1 - y0)
            vo = -y0 * vs
        for i in range(4):
            (x0, z0), (x1, z1) = wc[i], wc[(i + 1) % 4]
            nx, nz = nrm[i][0] * c + nrm[i][1] * s, -nrm[i][0] * s + nrm[i][1] * c
            if nx * (p['x'] - (x0 + x1) / 2) + nz * (p['z'] - (z0 + z1) / 2) <= 0:
                continue
            side = 0 if (nx * 0.55 + nz * 0.83) > -0.1 else 1
            self.tk_face(strips, x0, z0, x1, z1, y0, y1, tex, math.hypot(x1 - x0, z1 - z0) / tile_w, uoff + i * 0.37, vs, vo, side,
                         y0 <= 0.01)

    def tk_flush(self, cv, strips):
        vp = self.TK_VP
        CW, F, EYE, NL = self.TK_CW, self.TK_F, self.TK_EYE, TK_NL
        hor = vp.y + int(vp.h * 0.55)
        cover = [vp.bottom] * ((vp.w - 1) // CW + 1)
        strips.sort(key=lambda st: st[0])
        vy = vp.y
        vis = []
        ncol = len(cover)
        for st in strips:
            if st[1] is None:
                img, ix, iy = st[2:5]
                iw, ih = img.get_size()
                c0 = max(0, (ix - vp.x) // CW)
                c1 = min(ncol - 1, (ix + iw - 1 - vp.x) // CW)
                ci = c0
                while ci <= c1:
                    ct = cover[ci]
                    cj = ci
                    while cj < c1 and cover[cj + 1] == ct:
                        cj += 1
                    hc = ct - iy
                    if hc > 0:
                        bx0 = max(ix, vp.x + ci * CW)
                        bx1 = min(ix + iw, vp.x + (cj + 1) * CW)
                        if bx1 > bx0:
                            vis.append((st[0], -1, img, (bx0 - ix, 0, bx1 - bx0, min(ih, hc)), bx0, iy))
                    ci = cj + 1
                continue
            z, ci, top, bot, tex, side, tc, vs, vo, ground = st
            ct = cover[ci]
            if top >= ct:
                continue
            yt = top if top > vy else vy
            yb = bot if bot < ct else ct
            if yb - yt < 1:
                continue
            if ground:
                cover[ci] = yt
            vis.append((z, ci, yt, yb, tex, side, tc, vs, vo))
        scale = pygame.transform.scale
        blit = cv.blit
        old_clip = cv.get_clip()
        cv.set_clip(vp)
        for v in reversed(vis):
            if v[1] == -1:
                blit(v[2], (v[4], v[5]), v[3])
                continue
            z, ci, yt, yb, tex, side, tc, vs, vo = v
            th = tex['th']
            R = tex['reps'] * th
            r0 = R - ((EYE + (hor - yt) * z / F) * vs + vo) * th
            r1 = R - ((EYE + (hor - yb) * z / F) * vs + vo) * th
            i0 = int(r0) if r0 > 0 else 0
            if i0 >= R:
                i0 = R - 1
            n = int(r1) - i0
            if n < 1:
                n = 1
            if i0 + n > R:
                n = R - i0
            lvl = int(z * 0.0625)
            src = tex['var'][lvl if lvl < NL else NL - 1][side]
            blit(scale(src.subsurface((tc, i0, 1, n)), (CW, int(yb - yt) + 1)), (vp.x + ci * CW, int(yt)))
        cv.set_clip(old_clip)
        return len(vis)

    def tk_ground(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        cv.blit(self.tk_floor_bg, (vp.x, hor))
        s_, c_ = self._ks, self._kc
        T = 8.0
        ix0, iz0 = int(p['x'] // T), int(p['z'] // T)
        lim = self.TK_A + 8
        cells = []
        for di in range(-10, 11):
            for dj in range(-10, 11):
                cxw, czw = (ix0 + di + 0.5) * T, (iz0 + dj + 0.5) * T
                if abs(cxw) > lim or abs(czw) > lim:
                    continue
                dx, dz = cxw - p['x'], czw - p['z']
                ccz, ccx = dx * s_ + dz * c_, dx * c_ - dz * s_
                if ccz < -6 or ccz > 84 or abs(ccx) > ccz * 1.6 + 14:
                    continue
                cells.append((ccz, ix0 + di, iz0 + dj))
        cells.sort(reverse=True)
        fog = (110, 74, 100)
        for ccz, i, j in cells:
            h = ((i * 73856093) ^ (j * 19349663)) & 255
            b = 44 + h % 9 - 4
            f = clamp(ccz / 95.0, 0, 0.9)
            col = (int(lerp(b, fog[0], f)), int(lerp(b + 2, fog[1], f)), int(lerp(b + 9, fog[2], f)))
            edge = (int(lerp(b - 12, fog[0], f)), int(lerp(b - 10, fog[1], f)), int(lerp(b - 3, fog[2], f))) if ccz < 45 else None
            x0, z0 = i * T, j * T
            self.tk_ground_poly(cv, ((x0, z0), (x0 + T, z0), (x0 + T, z0 + T), (x0, z0 + T)), col, edge)
        for b in k['blds']:
            dx, dz = b['x'] - p['x'], b['z'] - p['z']
            if dx * s_ + dz * c_ < -30 or dx * dx + dz * dz > 100 ** 2:
                continue
            m = 2.6
            f = clamp(math.hypot(dx, dz) / 100.0, 0, 0.9)
            col = (int(lerp(112, fog[0], f)), int(lerp(112, fog[1], f)), int(lerp(120, fog[2], f)))
            self.tk_ground_poly(cv, ((b['x'] - b['hw'] - m, b['z'] - b['hd'] - m), (b['x'] + b['hw'] + m, b['z'] - b['hd'] - m),
                                     (b['x'] + b['hw'] + m, b['z'] + b['hd'] + m), (b['x'] - b['hw'] - m, b['z'] + b['hd'] + m)),
                                col, (int(col[0] * .75), int(col[1] * .75), int(col[2] * .78)))
        for sc in (-115, -69, -23, 23, 69, 115):
            for zz in range(-120, 121, 8):
                for horiz in (False, True):
                    a0, a1 = (sc, zz) if not horiz else (zz, sc), (sc, zz + 3.6) if not horiz else (zz + 3.6, sc)
                    dx, dz = a0[0] - p['x'], a0[1] - p['z']
                    ccz = dx * s_ + dz * c_
                    if ccz < -4 or ccz > 80 or dx * dx + dz * dz > 80 ** 2:
                        continue
                    w = 0.28
                    if horiz:
                        quad = ((a0[0], a0[1] - w), (a1[0], a1[1] - w), (a1[0], a1[1] + w), (a0[0], a0[1] + w))
                    else:
                        quad = ((a0[0] - w, a0[1]), (a1[0] - w, a1[1]), (a1[0] + w, a1[1]), (a0[0] + w, a0[1]))
                    f = clamp(ccz / 80.0, 0, 0.9)
                    self.tk_ground_poly(cv, quad, (int(lerp(214, fog[0], f)), int(lerp(184, fog[1], f)), int(lerp(70, fog[2], f))))

    def tk_sky(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        sky = k['sky']
        yaw = p['yaw']
        t = self.t
        cv.blit(self.tk_sky_bg, (vp.x, vp.y))
        for az, alt, sz in sky['stars']:
            rel = angle_diff(yaw, az)
            if abs(rel) < 60:
                sx = vp.centerx + self.TK_F * math.tan(math.radians(rel))
                sy = hor - 12 - alt * (hor - vp.y - 20)
                if vp.x < sx < vp.right and sy > vp.y and alt > 0.25:
                    v = 150 + int(90 * math.sin(t * 2 + az))
                    cv.fill((v, v, min(255, v + 20)), (int(sx), int(sy), sz, sz))
        rel = angle_diff(yaw, 42)
        if abs(rel) < 70:
            cv.blit(self.tk_moon, (int(vp.centerx + self.TK_F * math.tan(math.radians(rel)) - 60), hor - 210))
        pts = []
        for i in range(120):
            rel = angle_diff(yaw, i * 3.0)
            if abs(rel) < 75:
                pts.append((vp.centerx + self.TK_F * math.tan(math.radians(rel)), hor - sky['mount'][i] * 1.4))
        if len(pts) > 1:
            pts.sort()
            poly = pts + [(pts[-1][0], hor), (pts[0][0], hor)]
            pygame.draw.polygon(cv, (44, 30, 62), poly)
            pygame.draw.lines(cv, (120, 84, 126), False, pts, 2)
        for n, (az, wd, hh) in enumerate(sky['city']):
            rel = angle_diff(yaw, az)
            if abs(rel) < 75:
                sx = vp.centerx + self.TK_F * math.tan(math.radians(rel))
                ww = self.TK_F * math.radians(wd)
                r = pygame.Rect(int(sx - ww / 2), int(hor - hh), int(ww), int(hh))
                pygame.draw.rect(cv, (30, 22, 48), r)
                pygame.draw.line(cv, (84, 60, 100), r.topleft, r.topright, 1)
                for j in range(5):
                    if (n * 7 + j * 3) % 4 == 0 and r.w > 6:
                        cv.fill((255, 214, 120), (r.x + 2 + (j * 5) % max(1, r.w - 4), r.y + 4 + (j * 9) % max(1, r.h - 6), 2, 2))
        cv.fill((96, 64, 92), (vp.x, hor - 1, vp.w, 3))

    def tk_add_prism(self, strips, cx, cz, r, y0, y1, n, rot, tex, tile_w, uoff=0.0):
        p = self.k['p']
        a0 = math.radians(rot)
        pts = [(cx + math.sin(a0 - 2 * math.pi * i / n) * r, cz + math.cos(a0 - 2 * math.pi * i / n) * r) for i in range(n)]
        vs, vo = 1.0 / (y1 - y0), -y0 / (y1 - y0)
        for i in range(n):
            (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % n]
            mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
            nx, nz = mx - cx, mz - cz
            if nx * (p['x'] - mx) + nz * (p['z'] - mz) <= 0:
                continue
            nl = math.hypot(nx, nz) or 1.0
            side = 0 if (nx / nl * 0.55 + nz / nl * 0.83) > -0.1 else 1
            self.tk_face(strips, x0, z0, x1, z1, y0, y1, tex, math.hypot(x1 - x0, z1 - z0) / tile_w, uoff + i * 0.21, vs, vo, side,
                         y0 <= 0.01)

    def tk_add_tank(self, strips, e):
        """Agrega el sprite pre-renderizado del tanque (casco + torreta) como entrada ordenable por profundidad."""
        p = self.k['p']
        c = self.tk_cam(e['x'], 0, e['z'])
        z = c[2]
        if z < 2.5 or z > 190:
            return
        spr = self.tk_spr[e['kind']]
        sx, sy = self.tk_prj(c)
        scale = (self.TK_F / z) / spr['px'] * e.get('big', 1.0)
        step = 360.0 / TK_ANG
        hi = int(round(((e['h'] - p['yaw']) % 360) / step)) % TK_ANG
        ti = int(round(((e['tur'] - p['yaw']) % 360) / step)) % TK_ANG
        parts = (spr['hull'][hi], spr['tur'][ti])
        x0 = min(-a for _, a, _ in parts)
        x1 = max(im.get_width() - a for im, a, _ in parts)
        y0 = min(-b for _, _, b in parts)
        y1 = max(im.get_height() - b for im, _, b in parts)
        cvs = pygame.Surface((int(x1 - x0) + 1, int(y1 - y0) + 1), pygame.SRCALPHA)
        for im, a, b in parts:
            cvs.blit(im, (int(-x0 - a), int(-y0 - b)))
        # se escala solo la parte visible dentro del visor (de cerca el sprite sería enorme)
        vp = self.TK_VP
        dx, dy = sx + x0 * scale, sy + y0 * scale
        dw, dh = cvs.get_width() * scale, cvs.get_height() * scale
        vx0, vx1 = max(dx, vp.x), min(dx + dw, vp.right)
        vy0, vy1 = max(dy, vp.y), min(dy + dh, vp.bottom)
        if vx1 - vx0 < 1 or vy1 - vy0 < 1:
            return
        sw, sh = cvs.get_size()
        r = pygame.Rect(int((vx0 - dx) / scale), int((vy0 - dy) / scale), 0, 0)
        r.w = min(sw - r.x, int((vx1 - dx) / scale) - r.x + 2)
        r.h = min(sh - r.y, int((vy1 - dy) / scale) - r.y + 2)
        img = pygame.transform.scale(cvs.subsurface(r), (max(1, int(r.w * scale)), max(1, int(r.h * scale))))
        f = min(0.8, z / 170.0)
        img.fill((int(255 * (1 - f)),) * 3 + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        img.fill(tuple(int(q * f) for q in TK_FOG) + (0,), special_flags=pygame.BLEND_RGB_ADD)
        strips.append((z - 0.6, None, img, int(dx + r.x * scale), int(dy + r.y * scale)))

    def tk_scene(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        t = self.t
        self.tk_prep()
        cv.fill((0, 0, 0), vp)
        self.tk_sky(cv)
        self.tk_ground(cv)
        T = self.tk_tex
        strips = []
        for b in k['blds']:
            dx, dz = b['x'] - p['x'], b['z'] - p['z']
            if dx * dx + dz * dz > 170 ** 2:
                continue
            if b['hall']:
                self.tk_add_box(strips, b['x'], b['z'], b['hw'], b['hd'], 0, b['h'], 0, T['hall'], 8.0, 11.0)
            else:
                self.tk_add_box(strips, b['x'], b['z'], b['hw'], b['hd'], 0, b['h'], 0, T['bld'][b['tx']], 8.0, 8.0, b['uo'])
        for e in k['tanks']:
            self.tk_add_tank(strips, e)
        for m in k['missiles']:
            self.tk_add_box(strips, m['x'], m['z'], .35, 1.5, .6, 1.5, m['h'], T['missile'], 3.0)
        self.tk_flush(cv, strips)
        for b in k['blds']:
            if b['hall']:
                top = self.tk_cam(b['x'], b['h'] + 8, b['z'])
                base = self.tk_cam(b['x'], b['h'], b['z'])
                self.tk_line(cv, base, top, (210, 216, 230), 2)
                if top[2] > 1 and int(t * 2) % 2 == 0:
                    sx, sy = self.tk_prj(top)
                    glow(cv, sx, sy, min(120, max(8, int(220 / top[2]))), (255, 60, 50))
                    pygame.draw.circle(cv, (255, 120, 100), (int(sx), int(sy)), max(2, int(100 / top[2])))
        for m in k['missiles']:
            a = math.radians(m['h'])
            fl_ = self.tk_cam(m['x'] - math.sin(a) * 2.2, 1.0, m['z'] - math.cos(a) * 2.2)
            if fl_[2] > 1:
                fx_, fy_ = self.tk_prj(fl_)
                glow(cv, fx_, fy_, min(160, int(220 / fl_[2]) + 8), (255, 150, 50))
        for e in k['helis']:
            self.tk_heli(cv, e)
        for e in k['tanks'] + k['missiles']:
            if not self.tk_los(p['x'], p['z'], e['x'], e['z']):
                continue
            c = self.tk_cam(e['x'], (6.4 if e['kind'] == 'super' else 5.2) if e['kind'] != 'missile' else 3.0, e['z'])
            if 6 < c[2] < 110:
                sx, sy = self.tk_prj(c)
                if vp.x + 6 < sx < vp.right - 6:
                    sz = max(5, int(260 / c[2]))
                    col = (255, 70, 60) if e['kind'] == 'tank' else ((255, 190, 50) if e['kind'] == 'super' else (255, 236, 90))
                    if e.get('role') == 'kami':
                        col = (255, 120, 20)
                    elif e.get('role') == 'arty':
                        col = (190, 110, 255)
                    elif e.get('boss'):
                        col = (255, 40, 40)
                        sz *= 2
                    pygame.draw.polygon(cv, (20, 8, 8), [(sx - sz - 2, sy - sz - 2), (sx + sz + 2, sy - sz - 2), (sx, sy + 3)])
                    pygame.draw.polygon(cv, col, [(sx - sz, sy - sz), (sx + sz, sy - sz), (sx, sy)])
        for s in k['shells']:
            self.tk_shell(cv, s, (255, 140, 80))
        for s in k['pshells']:
            self.tk_shell(cv, s, (255, 236, 160))
        for d_ in k['debris']:
            a = self.tk_cam(d_['x'], d_['y'], d_['z'])
            b = self.tk_cam(d_['x'] - d_['vx'] * .07, d_['y'] - d_['vy'] * .07, d_['z'] - d_['vz'] * .07)
            self.tk_line(cv, a, b, (255, int(150 + 100 * clamp(d_['life'], 0, 1)), 60), 2)
        for bm in k['booms']:
            c = self.tk_cam(bm['x'], bm['y'], bm['z'])
            if c[2] < 1.5:
                continue
            sx, sy = self.tk_prj(c)
            age = bm['age'] / bm['life']
            r = min(170, int(self.TK_F * bm['size'] * (0.35 + age * 0.9) / c[2]))
            if r < 2:
                continue
            draw_circ(cv, sx, sy - r * 0.3, r, (40, 36, 40), 150 * (1 - age))
            glow(cv, sx, sy, int(r * 1.5), (255, 150, 60), 1 - age)
            if age < 0.45:
                glow(cv, sx, sy, int(r), (255, 240, 190), 1 - age * 2)
        wx = k['wx']
        if wx != 'clear':
            ov = pygame.Surface(vp.size, pygame.SRCALPHA)
            if wx == 'fog':
                ov.fill((170, 176, 186, 95))
                for yy in range(0, vp.h, 6):
                    ov.fill((190, 196, 206, int(95 + 85 * max(0.0, 1 - abs(yy / vp.h - 0.55) * 2.2))), (0, yy, vp.w, 6))
            else:
                ov.fill((4, 8, 30, 150))
            cv.blit(ov, vp.topleft)
            if wx == 'night':
                glow(cv, vp.centerx, vp.bottom - 20, 330, (255, 240, 190), 0.38)

    def tk_heli(self, cv, e):
        c = self.tk_cam(e['x'], 11.0, e['z'])
        if c[2] < 3 or c[2] > 150:
            return
        sx, sy = self.tk_prj(c)
        vp = self.TK_VP
        u = self.TK_F / c[2]
        if not (vp.x - 80 < sx < vp.right + 80):
            return
        sh = self.tk_cam(e['x'], 0.1, e['z'])
        if sh[2] > 1:
            qx, qy = self.tk_prj(sh)
            draw_circ(cv, qx, qy, max(3, int(u * 1.8)), (0, 0, 0), 60)
        a = math.radians(e['h'] - self.k['p']['yaw'])
        cs, sn = math.cos(a), math.sin(a)
        L, Hh = u * 2.6, u * 0.95
        body = (46, 56, 48)
        # cuerpo, cola y patín (vista aproximada según rumbo relativo)
        tx, ty = sx - sn * L * 1.5, sy + (-cs * 0.2) * Hh
        pygame.draw.line(cv, (36, 44, 38), (sx, sy), (tx, ty), max(2, int(u * 0.35)))
        pygame.draw.ellipse(cv, body, (sx - L * 0.6, sy - Hh * 0.55, L * 1.2, Hh * 1.1))
        pygame.draw.ellipse(cv, (130, 190, 210), (sx - L * 0.15 - (sn * L * 0.3), sy - Hh * 0.4, L * 0.55, Hh * 0.55))
        pygame.draw.line(cv, (20, 24, 22), (sx, sy - Hh * 0.6), (sx, sy - Hh * 0.9), 2)
        rl = L * 2.2
        for q in (0, 1.5708):
            ra = e['rot'] + q
            pygame.draw.line(cv, (200, 205, 200), (sx - math.cos(ra) * rl, sy - Hh * 0.9 - math.sin(ra) * rl * 0.12),
                             (sx + math.cos(ra) * rl, sy - Hh * 0.9 + math.sin(ra) * rl * 0.12), 2)
        glow(cv, sx, sy + Hh * 0.2, int(u * 0.9) + 6, (255, 70, 60), 0.5)
        if abs(sx - vp.centerx) < 200 and c[2] < 120:
            sz = max(5, int(260 / c[2]))
            pygame.draw.polygon(cv, (255, 120, 80), [(sx - sz, sy - Hh * 2 - sz), (sx + sz, sy - Hh * 2 - sz), (sx, sy - Hh * 2)])

    def tk_shell(self, cv, s, col):
        a = self.tk_cam(s['x'], s['y'], s['z'])
        if a[2] < 0.6:
            return
        sx, sy = self.tk_prj(a)
        r = min(40, max(2, int(70 / a[2])))
        glow(cv, sx, sy, r * 3 + 8, col, 0.8)
        b = self.tk_cam(s['x'] - s['vx'] * 0.05, s['y'], s['z'] - s['vz'] * 0.05)
        self.tk_line(cv, a, b, (255, 255, 255), 2)
        pygame.draw.circle(cv, col, (int(sx), int(sy)), r)

    def tk_overlay(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        cx = vp.centerx
        rec = clamp((p['cd'] - 0.5) / 0.2, 0, 1)
        if rec > 0.05:
            glow(cv, cx, vp.bottom - 6, 150, (255, 190, 90), rec * 0.9)
        rc = (255, 236, 160)
        pygame.draw.line(cv, rc, (cx - 26, hor), (cx - 8, hor), 1)
        pygame.draw.line(cv, rc, (cx + 8, hor), (cx + 26, hor), 1)
        pygame.draw.line(cv, rc, (cx, hor - 26), (cx, hor - 8), 1)
        pygame.draw.line(cv, rc, (cx, hor + 8), (cx, hor + 26), 1)
        pygame.draw.circle(cv, rc, (cx, hor), 2)

    def draw_tank(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        t = self.t
        cv.fill((8, 12, 10))
        cv.set_clip(vp)
        self.tk_scene(cv)
        self.tk_overlay(cv)
        for seg in k['cracks']:
            pygame.draw.lines(cv, (150, 220, 190), False, seg, 1)
            pygame.draw.lines(cv, (40, 70, 60), False, [(x + 2, y + 2) for x, y in seg], 1)
        if k['hurt'] > 0:
            ov = pygame.Surface(vp.size, pygame.SRCALPHA)
            ov.fill((255, 30, 20, int(120 * clamp(k['hurt'] * 1.6, 0, 1))))
            cv.blit(ov, vp.topleft)
        if p['blocked'] > 0:
            pygame.draw.rect(cv, (255, 200, 60), vp, 4)
        cv.set_clip(None)
        cv.blit(self.cockpit, (0, 0))
        G1, G2 = (90, 255, 150), (40, 150, 90)
        rx, ry, rr = W // 2, 62, 50
        pygame.draw.circle(cv, (0, 12, 6), (rx, ry), rr)
        for q in (rr, rr * 2 // 3, rr // 3):
            pygame.draw.circle(cv, (0, 90, 50), (rx, ry), q, 1)
        pygame.draw.line(cv, (0, 90, 50), (rx - rr, ry), (rx + rr, ry), 1)
        pygame.draw.line(cv, (0, 90, 50), (rx, ry - rr), (rx, ry + rr), 1)
        sw = k['sweep'] * 6.283
        pygame.draw.line(cv, (60, 255, 140), (rx, ry), (rx + math.sin(sw) * rr, ry - math.cos(sw) * rr), 2)
        rng = 95.0
        ya = math.radians(p['yaw'])
        sy_, cy_ = math.sin(ya), math.cos(ya)

        def blip(x, z, col, size, clampit=False):
            dx, dz = x - p['x'], z - p['z']
            cx_, cz_ = dx * cy_ - dz * sy_, dx * sy_ + dz * cy_
            d = math.hypot(cx_, cz_)
            if d > rng:
                if not clampit:
                    return
                cx_, cz_ = cx_ / d * rng, cz_ / d * rng
            pygame.draw.rect(cv, col, (rx + cx_ / rng * (rr - 3) - size // 2, ry - cz_ / rng * (rr - 3) - size // 2, size, size))
        for b in k['blds']:
            blip(b['x'], b['z'], (0, 110, 70), 2)
        blip(0, 0, (90, 255, 255), 4, True)
        for e in k['tanks']:
            blip(e['x'], e['z'], (255, 90, 60) if e['kind'] == 'tank' else (255, 190, 50), 7 if e.get('boss') else 4)
        for m in k['missiles']:
            blip(m['x'], m['z'], (255, 235, 90), 3)
        for e in k['helis']:
            blip(e['x'], e['z'], (120, 200, 255), 4)
        pygame.draw.polygon(cv, (90, 255, 150), [(rx, ry - 5), (rx - 3, ry + 3), (rx + 3, ry + 3)], 1)
        pygame.draw.circle(cv, (70, 120, 90), (rx, ry), rr, 2)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, G1, 40, 20)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, G2, 40, 52)
        self.text(cv, k['city']['name'], self.f_s, G1, 40, 78)
        left = len(k['queue']) + len(k['tanks']) + len(k['missiles']) + len(k['helis'])
        self.text(cv, 'ENEMIGOS %d' % left, self.f_m, (255, 130, 100), W - 40, 20, 'r')
        city = k['city']
        self.text(cv, 'CIUDAD', self.f_s, G2, W - 270, 56)
        self.bar(cv, W - 200, 52, 160, 18, city['hp'] / 100, (80, 230, 110) if city['hp'] > 50 else (240, 90, 70), '%d%%' % city['hp'])
        by = vp.bottom + 24
        self.text(cv, 'ARMADURA', self.f_s, G1, 40, by)
        self.bar(cv, 40, by + 22, 280, 24, p['hp'] / TK_HP, (80, 230, 110) if p['hp'] > TK_HP * 0.35 else (240, 80, 70), '%d' % max(0, p['hp']))
        self.text(cv, 'CAÑON', self.f_s, G1, 40, by + 56)
        rl = 1 - clamp(p['cd'] / 0.7, 0, 1)
        self.bar(cv, 40, by + 78, 280, 18, rl, (90, 255, 150) if rl >= 1 else (255, 190, 70), 'LISTO' if rl >= 1 else 'CARGANDO')
        hd = int(p['yaw']) % 360
        self.text(cv, 'RUMBO %03d' % hd, self.f_m, G1, W - 40, by, 'r')
        card = 'N NE E SE S SO O NO'.split()[int(((hd + 22.5) % 360) // 45)]
        self.text(cv, card, self.f_l, G1, W - 40, by + 28, 'r')
        self.text(cv, 'VELOCIDAD %2d' % abs(p['v']), self.f_s, G2, W - 40, by + 74, 'r')
        msg, mcol = '', (255, 200, 80)
        nearest = None
        for e in k['tanks']:
            d = math.hypot(e['x'] - p['x'], e['z'] - p['z'])
            if nearest is None or d < nearest[0]:
                nearest = (d, e)
        if k['inrange']:
            msg, mcol = 'ENEMIGO EN RANGO', (255, 90, 70)
        elif k['msg_t'] > 0:
            msg = k['msg']
        elif nearest and nearest[0] < 120:
            rel = angle_diff(p['yaw'], math.degrees(math.atan2(nearest[1]['x'] - p['x'], nearest[1]['z'] - p['z'])))
            if abs(rel) > 45:
                msg = 'ENEMIGO A LA %s' % ('DERECHA >>' if 0 < rel < 135 else ('<< IZQUIERDA' if -135 < rel < 0 else 'ESPALDA'))
                mcol = (255, 150, 70)
        if msg and (k['inrange'] or int(t * 4) % 2 == 0 or k['msg_t'] > 0):
            self.text(cv, msg, self.f_m, mcol, W // 2, vp.bottom + 56, 'c')
        self.text(cv, 'W/S avanzar | A/D girar | ESPACIO o clic: cañón', self.f_s, G2, W // 2, H - 28, 'c')
