"""Batallas navales a gran escala: escoltas enemigas, ataques aéreos, escolta aliada y fortaleza costera con artillería."""
import math
import pygame
import random
from .common import H, W, angle_diff, bearing, clamp, dist, draw_circ, glow, vec


class NavalFleetMixin:
    def nf_init(self):
        c = self.c
        w = self.wave
        c.update(boats=[], planes=[], bombs=[], barrage=[], ally=None, air_t=random.uniform(9, 14), bar_t=random.uniform(5, 8),
                 air_cd=22.0, aplane=None)
        if not self.ships.get('g_boat'):
            for key, src, k in (('g_boat', 'e_map', 1.55), ('a_ally', 'p_map', 1.5)):
                s, sh = self.ships[src]
                self.ships[key] = (pygame.transform.rotozoom(s, 0, k).convert_alpha(), pygame.transform.rotozoom(sh, 0, k).convert_alpha())
        e = c['e']
        n_boats = 0
        if c['nest']:
            if w >= 2:
                for sd in (-1, 1):
                    c['boats'].append(dict(kind='gun', x=e['x'] + sd * 165, y=e['y'] + 28, h=180.0, v=0.0, hp=7.0 + w, max=7.0 + w,
                                           cd=random.uniform(2, 4), orb=0.0))
                self.call_out('¡CAÑONES DE FLANCO!', (255, 170, 110), 'flank', 9)
        elif c['is_boss']:
            n_boats = 2 if w >= 5 else (1 if w >= 3 else 0)
        elif not c['sub']:
            n_boats = 0 if w < 3 else (1 + (w >= 5))
        for i in range(n_boats):
            c['boats'].append(dict(kind='boat', x=random.choice((90, W - 90)), y=random.uniform(60, 220), h=180.0, v=60.0, hp=6.0 + 1.5 * w,
                                   max=6.0 + 1.5 * w, cd=random.uniform(1.5, 3.5), orb=random.uniform(0, 360)))
        if n_boats:
            self.call_out('¡ESCOLTAS ENEMIGAS!', (255, 150, 120), 'escorts', 9)
        if not c['nest'] and ((c['is_boss'] and w >= 2) or (w >= 3 and random.random() < 0.7)):
            side = random.choice((-1, 1))
            c['ally'] = dict(x=c['p']['x'] + side * 150, y=c['p']['y'] + 30, h=0.0, v=0.0, hp=34.0, max=34.0, cd=2.0, side=side, sink=None)
            self.call_out('ESCOLTA ALIADA', (130, 255, 190), 'ally', 9)

    # ------------------------------------------------------------ actualización
    def nf_update(self, dt):
        c = self.c
        p, e = c['p'], c['e']
        w = self.wave
        over = e['sink'] is not None
        # --- botes enemigos / cañones de flanco
        for b in c['boats'][:]:
            if over:
                c['boats'].remove(b)
                self.fx.explode(b['x'], b['y'], 1.0, True)
                continue
            b['cd'] -= dt
            if b['kind'] == 'boat':
                b['orb'] = (b['orb'] + 22 * dt) % 360
                tx, ty = vec(b['orb'], 300)
                want = bearing(p['x'] + tx - b['x'], p['y'] + ty - b['y'])
                b['h'] = (b['h'] + clamp(angle_diff(b['h'], want), -80 * dt, 80 * dt)) % 360
                b['v'] += (115 - b['v']) * min(1, dt * 1.5)
                dx, dy = vec(b['h'], b['v'] * dt)
                b['x'] = clamp(b['x'] + dx, 40, W - 40)
                b['y'] = clamp(b['y'] + dy, 40, H - 40)
                if random.random() < dt * 20:
                    bx, by = vec(b['h'], -26)
                    self.fx.add('foam', b['x'] + bx, b['y'] + by, life=1.0, r0=4, r1=12, col=(230, 245, 255))
            if b['cd'] <= 0 and p['sink'] is None:
                b['cd'] = random.uniform(3.0, 4.2) * max(0.8, 1 - 0.03 * w)
                spd = 225 + 4 * w
                T = dist(p['x'], p['y'], b['x'], b['y']) / spd
                vx, vy = vec(p['h'], p['v'])
                err = 7.0 + (14 if self.na_smoked() else 0)
                ang = bearing(p['x'] + vx * T - b['x'], p['y'] + vy * T - b['y']) + random.uniform(-err, err)
                self.launch_missile(b, ang, spd, 'e', 0.0, (8, 5))
                self.audio.play('launch', .3)
                c['flashes'].append([b['x'], b['y'], 80, (255, 190, 130), 1.0])
        # --- escolta aliada
        a = c['ally']
        if a is not None:
            if a['sink'] is not None:
                a['sink'] += dt
                if int(a['sink'] * 6) != int((a['sink'] - dt) * 6):
                    self.fx.explode(a['x'] + random.uniform(-14, 14), a['y'] + random.uniform(-26, 26), 0.7)
                if a['sink'] > 1.6:
                    c['ally'] = None
            else:
                tx, ty = vec(p['h'] + 90 * a['side'], 150)
                want = bearing(p['x'] + tx - a['x'], p['y'] + ty - a['y'])
                dd = dist(p['x'] + tx, p['y'] + ty, a['x'], a['y'])
                a['h'] = (a['h'] + clamp(angle_diff(a['h'], want), -90 * dt, 90 * dt)) % 360
                a['v'] += ((clamp(dd * 1.2, 0, 140)) - a['v']) * min(1, dt * 2)
                dx, dy = vec(a['h'], a['v'] * dt)
                a['x'], a['y'] = clamp(a['x'] + dx, 40, W - 40), clamp(a['y'] + dy, 40, H - 40)
                a['cd'] -= dt
                if a['cd'] <= 0 and not over and dist(a['x'], a['y'], e['x'], e['y']) < 620:
                    a['cd'] = 3.2
                    ang = bearing(e['x'] - a['x'], e['y'] - a['y'])
                    n0 = len(c['shells'])
                    self.launch_missile(a, ang, 400, 'p')
                    for s_ in c['shells'][n0:]:
                        s_['ally'] = True
                    self.audio.play('launch', .3)
                    c['flashes'].append([a['x'], a['y'], 70, (200, 255, 220), 1.0])
        # --- ataques aéreos: destructores y submarinos desde la oleada 2, jefes desde la 3
        c['flak_cd'] = max(0.0, c.get('flak_cd', 0.0) - dt)
        for fk in c.setdefault('flak', [])[:]:
            fk['t'] += dt
            if fk['t'] >= 0.45:
                c['flak'].remove(fk)
                self.fx.add('glow', fk['x'], fk['y'], life=0.35, r0=20, r1=110, col=(255, 230, 150))
                self.fx.add('ring', fk['x'], fk['y'], life=0.45, r0=10, r1=115, col=(255, 240, 190))
                self.audio.play('boom_s', .4)
                for pl in c['planes'][:]:
                    if dist(pl['x'], pl['y'], fk['x'], fk['y']) < 115:
                        c['planes'].remove(pl)
                        self.fx.explode(pl['x'], pl['y'], 0.8)
                        self.add_score(60)
                        self.pop('+60', pl['x'], pl['y'] - 16, (255, 255, 160))
                c['bombs'] = [bm for bm in c['bombs'] if dist(bm['x'], bm['y'], fk['x'], fk['y']) > 115]
        if (w >= (3 if c['is_boss'] else 2)) and not c['nest'] and not over and p['sink'] is None:
            c['air_t'] -= dt
            if c['air_t'] <= 0:
                c['air_t'] = random.uniform(18, 26)
                side = random.choice((-1, 1))
                y0 = clamp(p['y'] + random.uniform(-160, 60), 120, H - 140)
                for i in range(2 + (w >= 7)):
                    c['planes'].append(dict(x=-50 - i * 90 if side > 0 else W + 50 + i * 90, y=y0 + (i - 1) * 70, vx=300.0 * side, hp=1.0, bt=0.0))
                self.call_out('¡ATAQUE AÉREO!', (255, 190, 110), 'air', 6)
                self.audio.play('alarm', .4)
        for pl in c['planes'][:]:
            pl['x'] += pl['vx'] * dt
            pl['bt'] -= dt
            if random.random() < dt * 28:
                self.fx.add('smoke', pl['x'] - math.copysign(18, pl['vx']), pl['y'], 0, 0, 0.5, 2, 6, (220, 220, 226))
            if pl['bt'] <= 0 and abs(pl['x'] - p['x']) < 230:
                pl['bt'] = 0.34
                c['bombs'].append(dict(x=pl['x'] + random.uniform(-6, 6), y=pl['y'], t=0.0))
            if (pl['vx'] > 0 and pl['x'] > W + 80) or (pl['vx'] < 0 and pl['x'] < -80):
                c['planes'].remove(pl)
        for bm in c['bombs'][:]:
            bm['t'] += dt
            if bm['t'] >= 0.9:
                c['bombs'].remove(bm)
                self.fx.explode(bm['x'], bm['y'], 0.9, True)
                self.fx.splash(bm['x'], bm['y'], 1.0)
                self.audio.play('boom_s', .45)
                if p['sink'] is None and dist(bm['x'], bm['y'], p['x'], p['y']) < 42:
                    self.hull -= 7
                    self.shake = max(self.shake, 9)
                    self.pop('-7 CASCO', p['x'], p['y'] - 24, (255, 110, 100))
        # --- fortaleza costera: andanadas con aviso rojo
        if c['nest'] and w >= 3 and not over and p['sink'] is None:
            c['bar_t'] -= dt
            if c['bar_t'] <= 0:
                c['bar_t'] = max(7.0, 11.0 - 0.5 * w)
                vx, vy = vec(p['h'], p['v'] * 1.4)
                for d in (-90, 0, 90):
                    ox, oy = vec(p['h'] + 90, d)
                    c['barrage'].append(dict(x=clamp(p['x'] + vx + ox, 40, W - 40), y=clamp(p['y'] + vy + oy, 140, H - 40), t=0.0, delay=1.5))
                self.call_out('¡ARTILLERÍA!', (255, 130, 100), 'barrage', 6)
                self.audio.play('alarm', .35)
        for br in c['barrage'][:]:
            br['t'] += dt
            if br['t'] >= br['delay']:
                c['barrage'].remove(br)
                self.fx.explode(br['x'], br['y'], 1.4, True)
                self.fx.splash(br['x'], br['y'], 1.6)
                self.audio.play('boom_s', .6)
                self.shake = max(self.shake, 7)
                if p['sink'] is None and dist(br['x'], br['y'], p['x'], p['y']) < 62:
                    self.hull -= 11
                    self.shake = max(self.shake, 11)
                    self.pop('-11 CASCO', p['x'], p['y'] - 24, (255, 110, 100))
        # --- apoyo aéreo aliado: cuando el contador llega a cero, un caza pasa lanzando misiles al enemigo (puede ser derribado)
        ap = c['aplane']
        if ap is None:
            if not over and p['sink'] is None:
                c['air_cd'] -= dt
                if c['air_cd'] <= 0:
                    self.nf_spawn_air(1)
        else:
            if ap['dead'] is not None:
                ap['dead'] += dt
                ap['h'] = (ap['h'] + 420 * dt) % 360
                dx_, dy_ = vec(ap['h'], 120 * dt)
                ap['x'] += dx_
                ap['y'] += dy_ + 90 * dt
                if random.random() < dt * 40:
                    self.fx.add('smoke', ap['x'], ap['y'], 0, 0, 0.9, 4, 14, (40, 38, 38))
                if ap['dead'] > 1.3 or ap['y'] > H + 60:
                    self.fx.explode(ap['x'], min(ap['y'], H - 20), 1.4, True)
                    self.audio.play('boom_s', .6)
                    c['aplane'] = None
                    c['air_cd'] = 45.0
            else:
                ap['x'] += ap['vx'] * dt
                ap['cdw'] -= dt
                if random.random() < dt * 30:
                    self.fx.add('smoke', ap['x'] - math.copysign(20, ap['vx']), ap['y'], 0, 0, 0.6, 2, 7, (230, 230, 236))
                if (not over and ap['shots'] < (4 if ap.get('pw', 1.0) == 1.0 else 6) and ap['cdw'] <= 0 and abs(ap['x'] - e['x']) < 430 and 0 < ap['x'] < W):
                    ap['cdw'] = 0.38
                    ap['shots'] += 1
                    ang = bearing(e['x'] - ap['x'], e['y'] - ap['y'])
                    n0 = len(c['shells'])
                    self.launch_missile(ap, ang, 440, 'p')
                    for s_ in c['shells'][n0:]:
                        s_['ally'] = True
                        s_['f'] = 0.5 * ap.get('pw', 1.0)
                    self.audio.play('launch', .35)
                    c['flashes'].append([ap['x'], ap['y'], 60, (200, 255, 220), 1.0])
                if (ap['vx'] > 0 and ap['x'] > W + 110) or (ap['vx'] < 0 and ap['x'] < -110):
                    if ap['passes'] == 1 and not over:
                        self.nf_spawn_air(2, ap['hp'], ap.get('pw', 1.0))
                    else:
                        c['aplane'] = None
                        c['air_cd'] = 35.0
        if over:
            c['planes'].clear()
            c['barrage'].clear()
            c['bombs'].clear()

    def na_flak(self):
        """Z: cortina antiaérea en el cursor; derriba aviones y detona bombas dentro del radio."""
        c = self.c
        if c.get('flak_cd', 0) > 0 or self.c['p']['sink'] is not None:
            return
        c['flak_cd'] = 5.0
        c['flak'].append(dict(x=self.aim[0], y=self.aim[1], t=0.0))
        self.audio.play('launch', .45)

    def na_call_jets(self):
        """X: llama a tu escuadrón F-16 desde la base (gasta una salida): dos pasadas con misiles más potentes."""
        c = self.c
        if c['aplane'] is not None:
            self.toast('Ya hay un avión aliado sobre el combate', (255, 220, 130))
        elif getattr(self, 'jet_sorties', 0) <= 0:
            self.toast('Sin salidas de F-16 disponibles', (255, 200, 120))
        elif self.c['p']['sink'] is not None or c['e']['sink'] is not None:
            return
        else:
            self.jet_sorties -= 1
            c['air_cd'] = max(c['air_cd'], 30.0)
            self.nf_spawn_air(1, 5.0, 2.0)

    def nf_spawn_air(self, passes, hp=3.0, pw=1.0):
        c = self.c
        e = c['e']
        side = random.choice((-1, 1))
        y = clamp(e['y'] + random.uniform(-110, 170), 90, H - 230)
        c['aplane'] = dict(x=-70.0 if side > 0 else W + 70.0, y=y, vx=330.0 * side, h=90.0 if side > 0 else 270.0, hp=hp, shots=0,
                           cdw=0.0, dead=None, passes=passes, pw=pw)
        if passes == 1:
            self.call_out('¡APOYO AÉREO EN CAMINO!', (130, 255, 190), 'airsup', 4)
            self.audio.play('ping', .6)

    # ------------------------------------------------------------ impactos de misiles sobre botes, aviones y aliado
    def nf_shell_hit(self, s):
        """Devuelve True si el misil se consumió contra un bote enemigo, un avión o la escolta aliada."""
        c = self.c
        if s['own'] == 'p':
            for b in c['boats']:
                if dist(b['x'], b['y'], s['x'], s['y']) < (26 if b['kind'] == 'boat' else 30):
                    dmg = (2.2 if not s.get('ally') else 1.2) * self.up_dmg()
                    b['hp'] -= dmg
                    self.fx.explode(s['x'], s['y'], 0.8)
                    self.audio.play('hit', .5)
                    self.pop('-%d' % round(dmg), s['x'], s['y'] - 18, (255, 255, 160))
                    if not s.get('ally'):
                        self.na_charge(8)
                    if b['hp'] <= 0:
                        c['boats'].remove(b)
                        self.fx.explode(b['x'], b['y'], 1.5, True)
                        self.audio.play('boom_s', .7)
                        self.add_score(120)
                        self.pop('+120', b['x'], b['y'] - 20, (255, 255, 160))
                        self.call_out('¡ESCOLTA HUNDIDA!', (255, 230, 130), 'boatkill', 2.5)
                    return True
            for pl in c['planes']:
                if dist(pl['x'], pl['y'], s['x'], s['y']) < 22:
                    c['planes'].remove(pl)
                    self.fx.explode(pl['x'], pl['y'], 0.8)
                    self.audio.play('boom_s', .4)
                    self.add_score(60)
                    self.pop('+60', pl['x'], pl['y'] - 16, (255, 255, 160))
                    return True
        else:
            ap = c['aplane']
            if ap is not None and ap['dead'] is None and dist(ap['x'], ap['y'], s['x'], s['y']) < 24:
                ap['hp'] -= 1
                self.fx.explode(s['x'], s['y'], 0.8)
                self.audio.play('hit', .5)
                self.pop('AVIÓN -1', s['x'], s['y'] - 18, (130, 255, 190))
                if ap['hp'] <= 0:
                    ap['dead'] = 0.0
                    self.call_out('¡AVIÓN ALIADO DERRIBADO!', (255, 120, 100), 'apk', 4)
                return True
            a = c['ally']
            if a is not None and a['sink'] is None and dist(a['x'], a['y'], s['x'], s['y']) < 26:
                dmg = s['dmg'][0]
                a['hp'] -= dmg
                self.fx.explode(s['x'], s['y'], 0.8)
                self.audio.play('hit', .5)
                self.pop('ALIADO -%d' % dmg, s['x'], s['y'] - 18, (130, 255, 190))
                if a['hp'] <= 0:
                    a['sink'] = 0.0
                    self.fx.explode(a['x'], a['y'], 1.5, True)
                    self.call_out('¡ESCOLTA ALIADA HUNDIDA!', (255, 120, 100), 'allyk', 4)
                return True
        return False

    # ------------------------------------------------------------ dibujo
    def nf_draw(self, cv):
        c = self.c
        t = self.t
        for fk in c.get('flak', ()):
            draw_circ(cv, fk['x'], fk['y'], 115 * (0.4 + fk['t'] * 1.3), (255, 235, 170), 80, 1)
        if getattr(self, 'jet_sorties', 0) > 0 and c['aplane'] is None:
            self.text(cv, 'APOYO F-16 (X): %d salida(s)' % self.jet_sorties, self.f_s, (150, 220, 255), W // 2, H - 152, 'c')
        if c.get('planes') or c.get('bombs') or c.get('flak_cd', 0) > 0:
            self.text(cv, 'CORTINA ANTIAÉREA (Z): %s' % ('lista' if c.get('flak_cd', 0) <= 0 else '%d s' % math.ceil(c['flak_cd'])), self.f_s,
                      (255, 235, 170) if c.get('flak_cd', 0) <= 0 else (170, 170, 170), W // 2, H - 130, 'c')
        for b in c['boats']:
            if b['kind'] == 'boat':
                self.blit_ship(cv, 'g_boat', b['x'], b['y'], b['h'])
            else:
                draw_circ(cv, b['x'] + 3, b['y'] + 4, 24, (0, 0, 0), 60)
                pygame.draw.circle(cv, (150, 130, 96), (int(b['x']), int(b['y'])), 22)
                pygame.draw.circle(cv, (90, 94, 100), (int(b['x']), int(b['y'])), 14)
                self.blit_turret(cv, self.tur_e, b['x'], b['y'], bearing(c['p']['x'] - b['x'], c['p']['y'] - b['y']))
            pygame.draw.rect(cv, (8, 12, 24), (b['x'] - 18, b['y'] - 32, 36, 5))
            pygame.draw.rect(cv, (240, 80, 70), (b['x'] - 17, b['y'] - 31, int(34 * clamp(b['hp'] / b['max'], 0, 1)), 3))
        a = c['ally']
        if a is not None:
            if a['sink'] is None:
                self.blit_ship(cv, 'a_ally', a['x'], a['y'], a['h'])
                pygame.draw.rect(cv, (8, 12, 24), (a['x'] - 18, a['y'] - 34, 36, 5))
                pygame.draw.rect(cv, (110, 255, 170), (a['x'] - 17, a['y'] - 33, int(34 * clamp(a['hp'] / a['max'], 0, 1)), 3))
            else:
                self.blit_ship(cv, 'a_ally', a['x'], a['y'], a['h'], alpha=int(255 * clamp(1 - a['sink'] / 1.6, 0, 1)))
                glow(cv, a['x'], a['y'], 30, (255, 140, 50), 0.7)
        for br in c['barrage']:
            k = br['t'] / br['delay']
            pulse = 0.5 + 0.5 * math.sin(t * 18)
            draw_circ(cv, br['x'], br['y'], 62, (255, 60, 50), 40 + 70 * k * pulse)
            draw_circ(cv, br['x'], br['y'], 62, (255, 120, 90), 200, 2)
            draw_circ(cv, br['x'], br['y'], 62 * (1 - k), (255, 220, 200), 160, 1)
            yy = br['y'] - 480 * (1 - k) ** 2
            pygame.draw.line(cv, (255, 235, 200), (br['x'], yy - 28), (br['x'], yy), 4)
            glow(cv, br['x'], yy, 18, (255, 170, 80), 0.8)
        for bm in c['bombs']:
            k = bm['t'] / 0.9
            draw_circ(cv, bm['x'], bm['y'], 46, (255, 70, 50), 60, 1)
            yy = bm['y'] - 200 * (1 - k) ** 1.5
            pygame.draw.circle(cv, (40, 44, 50), (int(bm['x']), int(yy)), 5)
            draw_circ(cv, bm['x'] + 4, bm['y'] + 6, 7, (0, 0, 0), 60 * k)
        ap = c['aplane']
        if ap is not None:
            if 'ap_spr' not in self.air:
                f = self.air['f16']
                self.air['ap_spr'] = pygame.transform.smoothscale(f, (int(f.get_width() * 0.7), int(f.get_height() * 0.7)))
            spr = pygame.transform.rotate(self.air['ap_spr'], -ap['h'])
            sh = pygame.mask.from_surface(spr).to_surface(setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0))
            cv.blit(sh, (ap['x'] - sh.get_width() // 2 + 14, ap['y'] - sh.get_height() // 2 + 20))
            cv.blit(spr, (ap['x'] - spr.get_width() // 2, ap['y'] - spr.get_height() // 2))
            if ap['dead'] is None:
                bx, by = vec(ap['h'], -26)
                glow(cv, ap['x'] + bx, ap['y'] + by, 14, (140, 200, 255), 0.8)
            else:
                glow(cv, ap['x'], ap['y'], 26, (255, 120, 40), 0.7)
        for pl in c['planes']:
            d = 1 if pl['vx'] > 0 else -1
            pts = [(pl['x'] + d * 22, pl['y']), (pl['x'] - d * 14, pl['y'] - 18), (pl['x'] - d * 6, pl['y']), (pl['x'] - d * 14, pl['y'] + 18)]
            draw_circ(cv, pl['x'] + 10, pl['y'] + 16, 18, (0, 0, 0), 50)
            pygame.draw.polygon(cv, (46, 52, 62), pts)
            pygame.draw.polygon(cv, (210, 216, 226), pts, 2)
            glow(cv, pl['x'] - d * 18, pl['y'], 12, (255, 170, 80), 0.7)
