"""Defensa de la ciudad contra misiles (interceptores)."""
import math
import pygame
import random
from .common import H, HZ, Particles, SKY_W, W, bearing, clamp, dist, draw_circ, glow


class DefenseMixin:
    # ---------------------------------------------------------- DEFENSA
    def start_defense(self, city):
        w = self.wave
        n = min(9 + 2 * w, 24)
        self.fx = Particles()
        plan = []
        for i in range(min(1 + w // 2, 4)):
            plan.append((random.uniform(2.5, 5.0 + n * 0.45) + i * 1.5,
                         'bomber' if (w >= 3 and random.random() < 0.4) else 'jet', random.choice((-1, 1))))
        plan.sort()
        self.d = dict(city=city, missiles=[], inter=[], blasts=[], fires=[], t=0.0, total=n, killed=0, hits=0,
                      queue=sorted(random.uniform(0.6, 3.0 + n * 0.55) for _ in range(n)), cool=0.0, phase='play', planes=[], plan=plan, shots=0, pkilled=0,
                      pt=0.0, shipx=W / 2, shipy=HZ + 100, sky_x=(W - SKY_W) / 2, destroyed=False, combo=0, dbl=0.0, shield=0.0,
                      bosst=(random.uniform(7, 12) if self.wave >= 3 else None), flash=0.0, shock=None, alarm=0.0)
        self.aim = [W / 2, 280.0]
        self.go('defense')
        self.banner('DEFENDÉ ' + city['name'], 'Mouse/flechas: apuntar  |  Clic/ESPACIO: interceptor', (255, 120, 90), 3.0)

    def sky_target(self):
        d = self.d
        b = random.choice(d['city']['sky'])
        return d['sky_x'] + b['x'] + b['w'] / 2, HZ - b['h'], b

    def def_kinds(self):
        w = self.wave
        ks = ['std'] * 4
        if w >= 2:
            ks += ['cluster'] * 2
        if w >= 3:
            ks += ['fast', 'decoy']
        if w >= 4:
            ks += ['evasive'] * 2
        if w >= 5:
            ks += ['mirv'] * 2
        return ks

    def spawn_missile(self, kind=None, x0=None, y0=None):
        d = self.d
        kind = kind or random.choice(self.def_kinds())
        if kind != 'decoy' and random.random() < 0.16 and self.hull > 0:
            tx, ty, tb = d['shipx'], d['shipy'] - 20, None
            hit = 'ship'
        else:
            tx, ty, tb = self.sky_target()
            hit = 'city'
        sp = random.uniform(70, 105) + 9 * self.wave
        hp = 1
        if kind == 'fast':
            sp *= 1.6
        elif kind == 'boss':
            sp, hp = 52, 5 + self.wave // 2
        elif kind == 'decoy':
            sp *= 0.9
        m = dict(x=random.uniform(60, W - 60) if x0 is None else x0, y=-10.0 if y0 is None else y0, tx=tx, ty=ty, sp=sp, trail=[], hit=hit, tb=tb, k=kind, hp=hp,
                 split=(kind in ('cluster', 'mirv')), sy=random.uniform(160, 260), ph=random.uniform(0, 6.28),
                 ox=0.0, flash=0.0)
        d['missiles'].append(m)

    # ---- aviones enemigos: cruzan el cielo y lanzan misiles (como en el Missile Command de Atari)
    def def_planes(self, dt):
        d = self.d
        while d['plan'] and d['plan'][0][0] <= d['t']:
            _, kind, side = d['plan'].pop(0)
            y = random.uniform(110, 270)
            vx = (random.uniform(150, 190) if kind == 'jet' else random.uniform(95, 120)) * (1 + 0.03 * self.wave)
            d['planes'].append(dict(kind=kind, x=-60.0 if side > 0 else W + 60.0, y=y, y0=y, vx=vx * side, hp=1 if kind == 'jet' else 3,
                                    cd=random.uniform(0.6, 1.2), flash=0.0, ph=random.uniform(0, 6)))
            self.audio.play('alarm', .35)
            self.toast('¡AVIÓN ENEMIGO!', (255, 210, 120))
        for pl in d['planes'][:]:
            pl['x'] += pl['vx'] * dt
            pl['ph'] += dt * 2.2
            pl['y'] = pl['y0'] + math.sin(pl['ph']) * 14
            pl['flash'] = max(0.0, pl['flash'] - dt)
            pl['cd'] -= dt
            if random.random() < dt * 14:
                self.fx.add('smoke', pl['x'] - math.copysign(24, pl['vx']), pl['y'], 0, 0, 0.9, 2, 7, (200, 200, 205))
            if pl['cd'] <= 0 and 70 < pl['x'] < W - 70:
                pl['cd'] = random.uniform(1.3, 2.0) if pl['kind'] == 'jet' else random.uniform(1.8, 2.5)
                for _ in range(1 if pl['kind'] == 'jet' else 2):
                    self.spawn_missile(None if self.wave > 1 else 'std', pl['x'] + random.uniform(-14, 14), pl['y'] + 10)
                    d['total'] += 1
                self.audio.play('launch', .3)
            if (pl['vx'] > 0 and pl['x'] > W + 90) or (pl['vx'] < 0 and pl['x'] < -90):
                d['planes'].remove(pl)

    def def_blast_planes(self, b, rad):
        d = self.d
        for pl in d['planes'][:]:
            if dist(pl['x'], pl['y'], b['x'], b['y']) < rad + 22 and pl['flash'] <= 0:
                pl['hp'] -= 1
                pl['flash'] = 0.3
                self.fx.explode(pl['x'], pl['y'], 0.6)
                if pl['hp'] <= 0:
                    d['planes'].remove(pl)
                    d['pkilled'] += 1
                    pts = 250 if pl['kind'] == 'jet' else 450
                    self.add_score(pts)
                    self.pop('+%d' % pts, pl['x'], pl['y'], (255, 230, 130))
                    self.fx.explode(pl['x'], pl['y'], 1.6, True)
                    self.audio.play('boom_l', .5)
                    self.shake = max(self.shake, 5)
                    d['blasts'].append(dict(x=pl['x'], y=pl['y'], age=0.0, R=55, chain=True))

    def def_draw_planes(self, cv):
        d = self.d
        A = self.air
        if 'dp_jet' not in A:
            j = A['viper']
            A['dp_jet'] = (pygame.transform.rotate(j, 90), pygame.transform.rotate(j, -90))
            b = A['bomber']
            b = pygame.transform.smoothscale(b, (int(b.get_width() * 0.5), int(b.get_height() * 0.5)))
            A['dp_bomber'] = (pygame.transform.rotate(b, 90), pygame.transform.rotate(b, -90))
        for pl in d['planes']:
            spr = A['dp_' + pl['kind']][0 if pl['vx'] > 0 else 1]
            if pl['flash'] > 0:
                spr = spr.copy()
                spr.fill((120, 120, 120, 0), special_flags=pygame.BLEND_RGB_ADD)
            cv.blit(spr, (pl['x'] - spr.get_width() // 2, pl['y'] - spr.get_height() // 2))
            if int(self.t * 4) % 2 == 0:
                glow(cv, pl['x'] - math.copysign(8, pl['vx']), pl['y'] - 4, 10, (255, 60, 50), 0.8)

    def fire_interceptor(self):
        d = self.d
        if d['phase'] != 'play' or d['cool'] > 0:
            return
        if self.ammo <= 0:
            self.audio.play('empty')
            self.toast('¡Sin munición!', (255, 90, 80))
            return
        d['shots'] += 1
        if d['shots'] % 2:                      # los interceptores gastan medio cargador: hay el doble de misiles
            self.ammo -= 1
        d['cool'] = 0.16 * self.up_reload()
        gx, gy = d['shipx'] + 82, d['shipy'] - 6
        d['inter'].append(dict(x=float(gx), y=float(gy), tx=self.aim[0], ty=min(self.aim[1], HZ + 20), trail=[]))
        if d['dbl'] > 0:
            for off in (-70, 70):
                d['inter'].append(dict(x=float(gx), y=float(gy), tx=clamp(self.aim[0] + off, 0, W),
                                       ty=min(self.aim[1], HZ + 20), trail=[]))
        self.audio.play('launch', .8)
        self.fx.add('glow', gx, gy, life=.18, r0=18, r1=40, col=(255, 230, 160))

    def upd_defense(self, dt):
        d = self.d
        keys = pygame.key.get_pressed()
        sp = 520 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.aim[0] -= sp
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.aim[0] += sp
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.aim[1] -= sp
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.aim[1] += sp
        self.aim[0], self.aim[1] = clamp(self.aim[0], 0, W), clamp(self.aim[1], 20, HZ + 20)
        d['t'] += dt
        d['cool'] = max(0.0, d['cool'] - dt)
        while d['queue'] and d['queue'][0] <= d['t']:
            d['queue'].pop(0)
            self.spawn_missile()
        d['dbl'] = max(0.0, d['dbl'] - dt)
        d['flash'] = max(0.0, d['flash'] - dt * 0.8)
        if d['shock'] is not None:
            d['shock']['age'] += dt
            if d['shock']['age'] > 1.6:
                d['shock'] = None
        if any(m['k'] == 'boss' for m in d['missiles']):
            d['alarm'] -= dt
            if d['alarm'] <= 0:
                d['alarm'] = 1.1
                self.audio.play('alarm', .35)
        d['shield'] = max(0.0, d['shield'] - dt)
        if d['bosst'] is not None:
            d['bosst'] -= dt
            if d['bosst'] <= 0:
                d['bosst'] = None
                d['total'] += 1
                self.spawn_missile('boss')
                self.banner('¡ALERTA NUCLEAR!', 'Ojiva en camino: interceptala antes de que llegue a la ciudad', (255, 80, 60), 3.4)
                self.audio.play('alarm')
        for m in d['missiles'][:]:
            m['flash'] = max(0.0, m['flash'] - dt)
            ang = math.atan2(m['ty'] - m['y'], m['tx'] - m['x'])
            m['x'] += math.cos(ang) * m['sp'] * dt
            m['y'] += math.sin(ang) * m['sp'] * dt
            if m['k'] == 'evasive':
                # zigzag y esquiva las explosiones cercanas
                m['ph'] += dt * 3.2
                m['x'] += math.sin(m['ph']) * 70 * dt
                for b in d['blasts']:
                    if b['age'] < 0.4 and dist(m['x'], m['y'], b['x'], b['y']) < b['R'] + 55:
                        m['x'] += (1 if m['x'] >= b['x'] else -1) * 210 * dt
            m['trail'].append((m['x'], m['y']))
            m['trail'] = m['trail'][-28:]
            if random.random() < dt * 20:
                self.fx.add('smoke', m['x'], m['y'], 0, 0, 1.2, 3, 9, (90, 90, 96))
            if m['split'] and m['y'] > m['sy']:
                d['missiles'].remove(m)
                n = 5 if m['k'] == 'mirv' else 3
                self.fx.add('glow', m['x'], m['y'], life=.3, r0=14, r1=40, col=(255, 120, 80))
                for _ in range(n):
                    tx, ty, tb = self.sky_target()
                    d['missiles'].append(dict(x=m['x'], y=m['y'], tx=tx, ty=ty, sp=m['sp'] * 1.1, trail=[], hit='city',
                                              tb=tb, k='std', hp=1, split=False, sy=0, ph=0.0, ox=0.0, flash=0.0))
                d['total'] += n - 1
                continue
            if m['y'] >= m['ty'] - 3 or dist(m['x'], m['y'], m['tx'], m['ty']) < 6:
                d['missiles'].remove(m)
                if m['k'] == 'decoy':
                    self.fx.add('glow', m['x'], m['y'], life=.4, r0=10, r1=34, col=(255, 230, 120))
                else:
                    self.missile_impact(m)
        self.def_planes(dt)
        for it in d['inter'][:]:
            ang = math.atan2(it['ty'] - it['y'], it['tx'] - it['x'])
            it['x'] += math.cos(ang) * 640 * dt
            it['y'] += math.sin(ang) * 640 * dt
            it['trail'].append((it['x'], it['y']))
            it['trail'] = it['trail'][-14:]
            if dist(it['x'], it['y'], it['tx'], it['ty']) < 12:
                d['inter'].remove(it)
                d['blasts'].append(dict(x=it['tx'], y=it['ty'], age=0.0, R=64 * (1 + 0.2 * self.up_n('blast')), chain=False))
                self.audio.play('boom_s', .55)
        for b in d['blasts'][:]:
            b['age'] += dt
            rad = b['R'] * min(1.0, b['age'] / 0.28)
            life = 0.9 if not b['chain'] else 0.6
            if b['age'] > life:
                d['blasts'].remove(b)
                continue
            if b['age'] < life * 0.62:
                self.def_blast_planes(b, rad)
                for m in d['missiles'][:]:
                    if dist(m['x'], m['y'], b['x'], b['y']) < rad + (14 if m['k'] == 'boss' else 4):
                        if m['k'] == 'boss' and m['flash'] <= 0:
                            m['hp'] -= self.up_dmg()
                            m['flash'] = 0.25
                            self.fx.explode(m['x'], m['y'], 0.6)
                            if m['hp'] > 0:
                                continue
                        elif m['k'] == 'boss':
                            continue
                        d['missiles'].remove(m)
                        d['killed'] += 1
                        d['combo'] += 1
                        pts = (100 if m['k'] != 'boss' else 1000) + (50 if b['chain'] else 0)
                        if m['k'] == 'decoy':
                            pts, d['combo'] = 20, d['combo'] - 1
                        self.add_score(pts)
                        self.pop('+%d' % pts, m['x'], m['y'])
                        self.fx.explode(m['x'], m['y'], 0.8 if m['k'] != 'boss' else 2.0)
                        self.audio.play('boom_s', .5)
                        d['blasts'].append(dict(x=m['x'], y=m['y'], age=0.0, R=40 if m['k'] != 'boss' else 110, chain=True))
                        if m['k'] == 'boss':
                            d['flash'] = 0.9
                            d['shock'] = dict(x=m['x'], y=m['y'], age=0.0)
                            self.shake = max(self.shake, 16)
                            self.audio.play('boom_l')
                            self.banner('¡OJIVA NEUTRALIZADA!', '+1000 puntos', (120, 255, 190), 3.0)
                        if d['combo'] and d['combo'] % 6 == 0:
                            if (d['combo'] // 6) % 2:
                                d['dbl'] = 9.0
                                self.toast('RÁFAGA DOBLE', (120, 255, 190))
                            else:
                                d['shield'] = 10.0
                                self.toast('ESCUDO ANTIMISIL', (120, 200, 255))
        for f in d['fires']:
            f[2] -= dt
            if random.random() < dt * 10:
                self.fx.add('smoke', f[0] + random.uniform(-6, 6), f[1], random.uniform(-6, 6), -30, 2.0, 4, 16, (40, 40, 44))
        d['fires'] = [f for f in d['fires'] if f[2] > 0]
        self.fx.update(dt)
        if self.hull <= 0:
            return self.game_over('Tu buque fue hundido por los misiles')
        if d['phase'] == 'play' and not d['queue'] and not d['missiles'] and not d['inter'] and not d['blasts'] \
                and not d['planes'] and not d['plan']:
            d['phase'] = 'result'
            d['pt'] = 0.0
            if d['hits'] == 0:
                self.add_score(500)
                self.banner('¡DEFENSA PERFECTA!', '+500', (120, 255, 160), 2.6)
            else:
                self.banner('AMENAZA NEUTRALIZADA', 'Impactos: %d   Interceptados: %d' % (d['hits'], d['killed']),
                            (255, 220, 120), 2.6)
        if d['phase'] == 'result':
            d['pt'] += dt
            if d['pt'] > 2.8:
                self.end_defense()

    def nuke_blast(self, m):
        """La ojiva llega al suelo: flash, onda expansiva y edificios derrumbados."""
        d = self.d
        d['flash'] = 1.0
        d['shock'] = dict(x=m['x'], y=m['y'], age=0.0)
        self.shake = 30
        self.audio.play('boom_l')
        for b in (d['city']['sky'] if m['hit'] == 'city' else []):
            bx = d['sky_x'] + b['x'] + b['w'] / 2
            if abs(bx - m['x']) < 270:
                b['h'] = max(8, int(b['h'] * 0.28))
                d['fires'].append([bx, HZ - 6, random.uniform(10, 16)])
                self.fx.explode(bx, HZ - 20, 1.2, True)
        self.banner('¡IMPACTO NUCLEAR!', 'Parte de la ciudad quedó en ruinas', (255, 90, 60), 3.0)

    def missile_impact(self, m):
        d = self.d
        if d['shield'] > 0 and m['k'] != 'boss':
            self.fx.explode(m['x'], m['y'], 0.9)
            self.fx.add('glow', m['x'], m['y'], life=.4, r0=20, r1=80, col=(120, 200, 255))
            self.pop('BLOQUEADO', m['x'], m['y'] - 20, (140, 210, 255))
            return
        d['hits'] += 1
        dmg = 3 if m['k'] == 'boss' else 1
        if m['k'] == 'boss':
            self.nuke_blast(m)
        self.fx.explode(m['x'], m['y'], 1.1, True)
        self.shake = max(self.shake, 9)
        if m['hit'] == 'ship':
            self.hull -= 14 * dmg
            self.audio.play('hit')
            self.pop('-14 CASCO', m['x'], m['y'] - 20, (255, 110, 100))
        else:
            c = d['city']
            c['hp'] = max(0.0, c['hp'] - 11 * dmg)
            self.audio.play('boom_l', .8)
            if m['tb'] is not None:
                m['tb']['h'] = max(10, int(m['tb']['h'] * 0.55))
            d['fires'].append([m['x'], m['y'], random.uniform(6, 10)])
            self.pop('-%d%% CIUDAD' % (11 * dmg), m['x'], m['y'] - 20, (255, 110, 100))
            if c['hp'] <= 0 and not c['dead']:
                c['dead'] = True
                d['destroyed'] = True
                for b in c['sky']:
                    b['h'] = random.randint(6, 16)
                    self.fx.explode(d['sky_x'] + b['x'] + b['w'] / 2, HZ - 10, 1.4, True)
                self.shake = 20
                self.banner('¡CIUDAD DESTRUIDA!', c['name'], (255, 70, 60), 3.0)

    def end_defense(self):
        self.warned = False
        self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        if all(c['dead'] for c in self.cities):
            return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---- defensa
    def draw_defense(self, cv):
        d = self.d
        t = self.t
        cv.blit(self.sky, (0, 0))
        for x, y, ph in self.stars:
            v = int(120 + 100 * math.sin(t * 2 + ph))
            cv.set_at((x, y), (v, v, v))
        # mar
        cv.set_clip(pygame.Rect(0, HZ, W, H - HZ))
        self.draw_ocean(cv, 0, 0, t)
        self.dim(cv, 30, pygame.Rect(0, HZ, W, H - HZ))
        cv.set_clip(None)
        pygame.draw.line(cv, (255, 150, 90), (0, HZ), (W, HZ), 2)
        # skyline
        city = d['city']
        for b in city['sky']:
            bx = int(d['sky_x'] + b['x'])
            top = HZ - b['h']
            pygame.draw.rect(cv, (16, 20, 38), (bx, top, b['w'], b['h']))
            pygame.draw.rect(cv, (28, 34, 58), (bx, top, 3, b['h']))
            if not city['dead']:
                for j in range(top + 8, HZ - 8, 13):
                    for i in range(bx + 6, bx + b['w'] - 6, 9):
                        if (i * 7 + j * 13 + b['s']) % 5 < 2 and b['h'] > 24:
                            cv.fill((255, 224, 130), (i, j, 4, 6))
            if b['ant'] and b['h'] > 60:
                pygame.draw.line(cv, (16, 20, 38), (bx + b['w'] // 2, top), (bx + b['w'] // 2, top - 22), 2)
                if int(t * 2) % 2 == 0:
                    pygame.draw.circle(cv, (255, 60, 60), (bx + b['w'] // 2, top - 22), 3)
            # reflejo
            cv.fill((14, 16, 34), (bx, HZ + 2, b['w'], min(60, b['h'] // 2)), special_flags=pygame.BLEND_RGB_ADD)
        for f in d['fires']:
            glow(cv, f[0], f[1], 34 + 6 * math.sin(t * 20 + f[0]), (255, 120, 40), 0.9)
        # buque
        bob = math.sin(t * 1.6) * 3
        sx, sy = d['shipx'], d['shipy'] + bob
        cv.blit(self.side_ship, (sx - 150, sy - 70))
        for k in range(10):
            fx = sx - 140 + k * 29 + math.sin(t * 3 + k) * 4
            pygame.draw.line(cv, (200, 225, 245), (fx, sy + 36), (fx + 14, sy + 36), 2)
        gx, gy = sx + 82, sy - 6
        ang = bearing(self.aim[0] - gx, self.aim[1] - gy)
        self.blit_turret(cv, self.tur_p, gx, gy, ang)
        self.def_draw_planes(cv)
        # misiles
        for m in d['missiles']:
            pts = m['trail']
            for i in range(1, len(pts)):
                k = i / len(pts)
                pygame.draw.line(cv, (int(255 * k), int(120 * k), int(80 * k)), pts[i - 1], pts[i], 2)
            k = m['k']
            col = {'fast': (255, 220, 80), 'decoy': (120, 200, 255), 'evasive': (200, 120, 255),
                   'mirv': (255, 150, 40), 'boss': (255, 40, 40)}.get(k, (255, 90, 60))
            rr = 3 if k != 'boss' else 11
            glow(cv, m['x'], m['y'], 16 if k != 'boss' else 48, col)
            pygame.draw.circle(cv, (255, 235, 210) if m['flash'] <= 0 else (255, 255, 255), (int(m['x']), int(m['y'])), rr)
            if k == 'mirv':
                pygame.draw.circle(cv, (255, 230, 120), (int(m['x']), int(m['y'])), 7, 1)
            if k == 'boss':
                self.bar(cv, int(m['x']) - 30, int(m['y']) - 26, 60, 8, m['hp'] / (5 + self.wave // 2), (255, 80, 60), '')
                secs = max(0.0, (m['ty'] - m['y']) / m['sp'])
                self.text(cv, 'IMPACTO NUCLEAR %.0f s' % secs, self.f_m, (255, 90, 70) if int(t * 4) % 2 == 0 else (255, 220, 120),
                          int(m['x']), int(m['y']) - 52, 'c')
        for it in d['inter']:
            pts = it['trail']
            for i in range(1, len(pts)):
                k = i / len(pts)
                pygame.draw.line(cv, (int(160 * k), int(255 * k), int(200 * k)), pts[i - 1], pts[i], 2)
            glow(cv, it['x'], it['y'], 12, (120, 255, 200))
            pygame.draw.circle(cv, (255, 255, 255), (int(it['x']), int(it['y'])), 2)
        for b in d['blasts']:
            rad = b['R'] * min(1.0, b['age'] / 0.28)
            life = 0.9 if not b['chain'] else 0.6
            k = 1 - b['age'] / life
            glow(cv, b['x'], b['y'], rad * 1.5, (255, 190, 100), k)
            draw_circ(cv, b['x'], b['y'], rad, (255, 240, 200), 200 * k)
            draw_circ(cv, b['x'], b['y'], rad, (255, 255, 255), 255 * k, 3)
        self.fx.draw(cv)
        if d['shield'] > 0:
            a = 90 if d['shield'] > 2 or int(t * 8) % 2 else 30
            draw_circ(cv, sx, sy - 10, 170, (110, 190, 255), a * 0.5)
            draw_circ(cv, sx, sy - 10, 170, (170, 225, 255), a * 2, 2)
        kk = (self.wave - 1) % 4
        if kk:
            tint = {1: (255, 140, 60, 36), 2: (10, 16, 50, 70), 3: (80, 90, 110, 60)}[kk]
            ov = pygame.Surface((W, HZ), pygame.SRCALPHA)
            ov.fill(tint)
            cv.blit(ov, (0, 0))
            if kk == 3 and random.random() < 0.012:
                cv.fill((70, 70, 90), (0, 0, W, HZ), special_flags=pygame.BLEND_RGB_ADD)
        # mira
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (120, 255, 190), (ax, ay), 18, 2)
        pygame.draw.circle(cv, (120, 255, 190), (ax, ay), 3)
        for dx, dy in ((-30, 0), (30, 0), (0, -30), (0, 30)):
            pygame.draw.line(cv, (120, 255, 190), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        if d['shock'] is not None:
            a_ = d['shock']['age'] / 1.6
            draw_circ(cv, d['shock']['x'], d['shock']['y'], 40 + 520 * a_, (255, 240, 200), 160 * (1 - a_), 5)
        if d['flash'] > 0:
            v = int(255 * min(1.0, d['flash']))
            cv.fill((v, v, v), special_flags=pygame.BLEND_RGB_ADD)
        if any(m['k'] == 'boss' for m in d['missiles']) and int(t * 3) % 2 == 0:
            pygame.draw.rect(cv, (255, 40, 40), (0, 0, W, H), 6)
        # HUD
        self.draw_hud(cv, False)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        self.text(cv, city['name'], self.f_m, (255, 255, 255), W // 2, 16, 'c')
        col = (80, 230, 110) if city['hp'] > 60 else ((255, 200, 70) if city['hp'] > 30 else (240, 80, 70))
        self.bar(cv, W // 2 - 210, 44, 420, 26, city['hp'] / 100, col, 'CIUDAD %d%%' % city['hp'])
        left = len(d['queue']) + len(d['missiles'])
        self.text(cv, 'MISILES: %d' % left, self.f_m, (255, 160, 140), W - 20, 90, 'r')
        if d['planes'] or d['plan']:
            self.text(cv, 'AVIONES: %d' % (len(d['planes']) + len(d['plan'])), self.f_m, (255, 210, 120), W - 20, 116, 'r')
        if d['dbl'] > 0:
            self.text(cv, 'RÁFAGA DOBLE %.0fs' % d['dbl'], self.f_s, (120, 255, 190), 20, 90, 'l')
        if d['shield'] > 0:
            self.text(cv, 'ESCUDO %.0fs' % d['shield'], self.f_s, (130, 205, 255), 20, 110, 'l')
        self.text(cv, 'Clic / ESPACIO: lanzar interceptor', self.f_s, (200, 220, 255), W // 2, H - 30, 'c')
