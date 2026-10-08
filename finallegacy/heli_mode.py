"""Blackhawk: helipuerto en el mapa, bidón de combustible desde el aire y misiones aire-tierra."""
import math
import pygame
import random
from .common import EXTRA_ISLANDS, H, HELIPAD, W, Particles, angle_diff, bearing, clamp, dist, draw_circ, glow, vec
from .heli_art import BH_TAIL_ROTOR, BH_HUB, blackhawk_rotor_overlay, make_blackhawk, make_heli_targets

HELI_SORTIE_PTS = 3000          # puntaje para la primera misión de combate; cada una siguiente pide el doble de distancia (tope HELI_GAP_MAX)
HELI_GAP_MAX = 24000
HELI_FUEL_CD = 80.0             # espera entre bidones
TURN = 260.0


class HeliMixin:
    # ------------------------------------------------------------ MAPA: helipuerto y llamadas
    def heli_init(self):
        self.heli_sorties = 0
        self.heli_earned = 0
        self.heli_next = HELI_SORTIE_PTS
        self.heli_cd = 0.0
        self.heli_fl = None
        self.heli_cands = []
        self.cleared_isl = set()
        if not hasattr(self, 'bh_img'):
            self.bh_img = make_blackhawk()
            self.bh_small = pygame.transform.smoothscale(self.bh_img, (72, 84))
            self.ht_art = make_heli_targets()
            self.ht_flash = {}

    def near_helipad(self, rng=300):
        return dist(self.sx, self.sy, HELIPAD[0], HELIPAD[1]) < rng

    def heli_map_update(self, dt):
        self.heli_cd = max(0.0, self.heli_cd - dt)
        while self.score >= self.heli_next:
            self.heli_sorties += 1
            self.heli_next += min(HELI_SORTIE_PTS * 2 ** (self.heli_earned + 1), HELI_GAP_MAX)
            self.heli_earned += 1
            self.audio.play('win', .6)
            self.banner('¡BLACKHAWK LISTO PARA COMBATE!', 'Helipuerto disponible', (130, 255, 190), 2.8)
            self.say('piloto', 'Blackhawk listo. Acercate al helipuerto y presioná B para elegir la misión.', 'ok')
        f = self.heli_fl
        if f is None:
            return
        f['rot'] += dt * 30
        if f['ph'] == 'go':
            tx, ty = self.sx, self.sy
        elif f['ph'] == 'drop':
            tx, ty = f['dx'], f['dy']
        else:
            tx, ty = HELIPAD[0], HELIPAD[1]
        d = dist(f['x'], f['y'], tx, ty) or 1.0
        sp = 300.0 if f['ph'] != 'drop' else 180.0
        f['x'] += (tx - f['x']) / d * min(d, sp * dt)
        f['y'] += (ty - f['y']) / d * min(d, sp * dt)
        if d > 6:
            f['h'] = bearing(tx - f['x'], ty - f['y'])
        if f['ph'] == 'go' and d < 160:
            for _ in range(12):
                a = random.uniform(0, 6.28)
                px, py = self.sx + math.cos(a) * 150, self.sy + math.sin(a) * 150
                if not self.on_land(px, py, 40):
                    break
            f['dx'], f['dy'], f['ph'], f['bt'] = px, py, 'drop', None
            self.toast('¡El Blackhawk está sobre tu posición!', (130, 255, 190))
        elif f['ph'] == 'drop':
            if f['bt'] is None and d < 14:
                f['bt'] = 0.0
                self.audio.play('ping', .6)
            if f['bt'] is not None:
                f['bt'] += dt
                if f['bt'] >= 2.0:
                    self.crates.append(dict(x=f['dx'], y=f['dy'], kind='fuel', t=0, big=True))
                    self.audio.play('pickup', .8)
                    self.toast('Bidón de combustible en el agua: ¡recogelo!', (120, 255, 150))
                    f['ph'] = 'back'
        elif f['ph'] == 'back' and d < 30:
            self.heli_fl = None

    def heli_call(self):
        """C: llamar al Blackhawk para que venga volando y arroje un bidón de combustible."""
        if self.heli_fl is not None:
            self.toast('El Blackhawk ya está en camino', (255, 220, 130))
        elif self.heli_cd > 0:
            self.toast('Blackhawk reabasteciéndose: %d s' % math.ceil(self.heli_cd), (255, 200, 120))
        elif self.fuel > 90:
            self.toast('Tu tanque está casi lleno: llamalo cuando necesites combustible', (255, 220, 130))
        else:
            self.heli_fl = dict(x=float(HELIPAD[0]), y=float(HELIPAD[1]), h=0.0, rot=0.0, ph='go', dx=0.0, dy=0.0, bt=None)
            self.heli_cd = HELI_FUEL_CD
            self.audio.play('alarm', .5)
            self.banner('BLACKHAWK EN CAMINO', 'Va a lanzarte un bidón de combustible', (130, 255, 190), 2.6)

    def heli_candidates(self):
        """Objetivos que el Blackhawk puede atacar, de a lo sumo cuatro."""
        from .common import ANTENNA_ISLANDS
        ref = (self.sx, self.sy)
        isl = [dict(kind='island', idx=i, x=EXTRA_ISLANDS[i][0], y=EXTRA_ISLANDS[i][1], name=self.isl_name(i))
               for i in ANTENNA_ISLANDS if not self.antennas[i] and i not in self.cleared_isl]
        isl.sort(key=lambda c: dist(c['x'], c['y'], *ref))
        ships = sorted([dict(kind='ship', tg=en, x=en['x'], y=en['y'], name='Buque enemigo') for en in self.enemies if not en.get('is_boss')],
                       key=lambda c: dist(c['x'], c['y'], *ref))
        nests = sorted([dict(kind='nest', tg=n, x=n['x'], y=n['y'], name='Batería costera') for n in self.nests if n['alive'] and not n.get('ally')],
                       key=lambda c: dist(c['x'], c['y'], *ref))
        return (isl[:2] + ships[:1] + nests[:1] + isl[2:] + ships[1:] + nests[1:])[:4]

    def heli_launch(self):
        """B junto al helipuerto: elegir misión y despegar."""
        if not self.near_helipad():
            self.toast('Acercate al helipuerto (isla con la H) para despegar', (255, 220, 130))
            return
        if self.heli_sorties <= 0:
            self.toast('Sin misiones: conseguí %d puntos para el próximo Blackhawk' % max(0, self.heli_next - self.score), (255, 200, 120))
            return
        if self.attack is not None or self.warned:
            self.toast('Hay un ataque en curso: no es momento de despegar', (255, 150, 110))
            return
        self.heli_cands = self.heli_candidates()
        if not self.heli_cands:
            self.toast('No hay objetivos enemigos para el Blackhawk', (255, 200, 120))
            return
        self.go('helisel')

    def heli_pick(self, i):
        if self.state != 'helisel' or not 0 <= i < len(self.heli_cands):
            return
        c = self.heli_cands[i]
        self.heli_sorties -= 1
        self.start_heli(c['kind'], c.get('tg', c))

    def heli_sel_rect(self, i):
        return pygame.Rect(W // 2 - 500, 190 + i * 118, 1000, 104)

    def draw_helisel(self, cv):
        t = self.t
        self.draw_ocean(cv, t * 20, t * 6, t)
        self.dim(cv, 45)
        self.text(cv, 'ELEGÍ LA MISIÓN DEL BLACKHAWK', self.f_l, (130, 255, 190), W // 2, 70, 'c')
        self.text(cv, 'Misiones disponibles: %d   |   1-4 o clic para despegar   |   ESC volver' % self.heli_sorties, self.f_s,
                  (200, 225, 255), W // 2, 130, 'c')
        mx, my = pygame.mouse.get_pos()
        for i, c in enumerate(self.heli_cands):
            r = self.heli_sel_rect(i)
            hov = r.collidepoint(mx, my)
            self.panel(cv, r.move(0, -4 if hov else 0), 215 if hov else 175)
            if c['kind'] == 'island':
                title, desc, col = 'DESPEJAR %s' % c['name'].upper(), 'Elimina la guarnición: después instalás la antena sin resistencia (L)', (120, 220, 255)
            elif c['kind'] == 'ship':
                title, desc, col = 'CAZAR BUQUE ENEMIGO', 'Hundilo desde el aire: cuenta para terminar la oleada', (255, 150, 120)
            else:
                title, desc, col = 'DESTRUIR BATERÍA COSTERA', 'Antiaéreas, búnkeres y depósito de combustible', (255, 210, 110)
            d = dist(c['x'], c['y'], HELIPAD[0], HELIPAD[1])
            self.text(cv, str(i + 1), self.f_l, col, r.x + 22, r.y + 28)
            self.text(cv, title, self.f_m, (255, 255, 255), r.x + 80, r.y + 18)
            self.text(cv, desc, self.f_s, (210, 225, 245), r.x + 80, r.y + 52)
            self.text(cv, '%d m' % d, self.f_s, col, r.right - 24, r.y + 18, 'r')
            pygame.draw.rect(cv, col, r.move(0, -4 if hov else 0), 2, border_radius=6)

    def draw_heli_map(self, cv, cx, cy):
        hx, hy, hr, _s = HELIPAD
        sx, sy = hx - cx, hy - cy
        if -300 < sx < W + 300 and -300 < sy < H + 300:
            pygame.draw.circle(cv, (92, 96, 90), (int(sx), int(sy)), 34)
            pygame.draw.circle(cv, (150, 154, 150), (int(sx), int(sy)), 31)
            pygame.draw.circle(cv, (240, 210, 60), (int(sx), int(sy)), 27, 2)
            self.text(cv, 'H', self.f_l, (240, 210, 60), sx, sy - 18, 'c', shadow=False)
            pygame.draw.rect(cv, (96, 100, 106), (sx + 30, sy + 18, 34, 22), border_radius=3)
            pygame.draw.rect(cv, (60, 64, 70), (sx + 30, sy + 18, 34, 22), 2, border_radius=3)
            ready = self.heli_sorties > 0
            if self.heli_fl is None:
                cv.blit(self.bh_small, (sx - 36, sy - 42))
            lab = 'HELIPUERTO - BLACKHAWK%s' % (' LISTO (B)' if ready else '')
            self.text(cv, lab, self.f_s, (130, 255, 190) if ready else (190, 215, 205), sx, sy + hr * 0.95, 'c')
            if self.near_helipad(420) and ready:
                pulse = 0.5 + 0.5 * math.sin(self.t * 4)
                draw_circ(cv, sx, sy, 44 + pulse * 8, (130, 255, 190), 90, 2)
        f = self.heli_fl
        if f is not None:
            fx_, fy_ = f['x'] - cx, f['y'] - cy
            if f['ph'] == 'drop' and f['bt'] is not None:
                k = clamp(f['bt'] / 2.0, 0, 1)
                bx_, by_ = f['dx'] - cx, f['dy'] - cy
                draw_circ(cv, bx_, by_ + 4, 10 + 8 * k, (0, 0, 0), 70)
                hgt = (1 - k) * 150
                by2 = by_ - hgt
                pygame.draw.circle(cv, (240, 130, 50), (int(bx_), int(by2 - 36)), 26, draw_top_left=True, draw_top_right=True)
                pygame.draw.circle(cv, (250, 240, 230), (int(bx_), int(by2 - 36)), 26, 2, draw_top_left=True, draw_top_right=True)
                pygame.draw.line(cv, (230, 230, 230), (bx_ - 24, by2 - 34), (bx_, by2), 1)
                pygame.draw.line(cv, (230, 230, 230), (bx_ + 24, by2 - 34), (bx_, by2), 1)
                pygame.draw.rect(cv, (60, 130, 70), (bx_ - 9, by2 - 8, 18, 22), border_radius=3)
                pygame.draw.rect(cv, (230, 220, 90), (bx_ - 9, by2 - 2, 18, 4))
            if -140 < fx_ < W + 140 and -140 < fy_ < H + 140:
                self.draw_blackhawk(cv, fx_, fy_, f['h'], f['rot'], 0.6, True)
            else:
                ang = math.atan2(fy_ - H / 2, fx_ - W / 2)
                ax_, ay_ = W / 2 + math.cos(ang) * 340, H / 2 + math.sin(ang) * 270
                pygame.draw.polygon(cv, (130, 255, 190), [(ax_ + math.cos(ang) * 18, ay_ + math.sin(ang) * 18),
                                                          (ax_ + math.cos(ang + 2.5) * 14, ay_ + math.sin(ang + 2.5) * 14),
                                                          (ax_ + math.cos(ang - 2.5) * 14, ay_ + math.sin(ang - 2.5) * 14)])
                self.text(cv, 'BLACKHAWK %d m' % dist(f['x'], f['y'], self.sx, self.sy), self.f_s, (130, 255, 190), ax_, ay_ - 26, 'c')

    def draw_blackhawk(self, cv, x, y, h, rot, scale, shadow=True):
        img = self.bh_img
        if scale != 1.0:
            img = pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
        r = pygame.transform.rotate(img, -h)
        if shadow:
            sh = pygame.mask.from_surface(r).to_surface(setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0))
            cv.blit(sh, (x - r.get_width() // 2 + 14 * scale + 3, y - r.get_height() // 2 + 20 * scale + 3))
        cv.blit(r, (x - r.get_width() // 2, y - r.get_height() // 2))
        ov, (ox, oy) = blackhawk_rotor_overlay(scale, rot, rot * 1.7)
        cv.blit(ov, (x - ox, y - oy))
        tx, ty = vec(h + 180, (BH_TAIL_ROTOR[1] - BH_HUB[1]) * scale)
        tr = 11 * scale
        draw_circ(cv, x + tx, y + ty, tr, (200, 205, 200), 34)
        a2 = rot * 1.7
        for q in (0.0, 1.5708):
            pygame.draw.line(cv, (28, 30, 28), (x + tx - math.cos(a2 + q) * tr, y + ty - math.sin(a2 + q) * tr),
                             (x + tx + math.cos(a2 + q) * tr, y + ty + math.sin(a2 + q) * tr), max(1, int(2 * scale)))

    # ------------------------------------------------------------ MISIÓN AIRE-TIERRA
    def start_heli(self, kind, tg):
        w = self.wave
        self.fx = Particles()
        T = []
        land = off = None
        if kind in ('nest', 'island'):
            R = 250
            seed = EXTRA_ISLANDS[tg['idx']][3] if kind == 'island' else int(tg['x']) % 997 + 11
            land, off = self.make_ground(seed, R)
            land = land.convert_alpha()
            rnd = random.Random(int(tg['x'] * 7 + tg['y']))

            def spot(minr, maxr):
                for _ in range(60):
                    a, r = rnd.uniform(0, 6.283), rnd.uniform(minr, maxr)
                    x, y = W / 2 + math.cos(a) * r, H / 2 + math.sin(a) * r
                    if all(dist(x, y, t['x'], t['y']) > 70 for t in T):
                        return x, y
                return W / 2, H / 2
            for _ in range(min(2 + w // 2, 5)):
                x, y = spot(60, 190)
                T.append(self.heli_target('aa', x, y))
            for _ in range(3 if kind == 'island' else 2):
                x, y = spot(40, 170)
                T.append(self.heli_target('bunker', x, y))
            for _ in range(min(w // 3, 2) if w >= 3 else 0):
                x, y = spot(70, 190)
                T.append(self.heli_target('sam', x, y))
            x, y = spot(0, 90)
            T.append(self.heli_target('depot' if kind == 'nest' else 'radar', x, y))
            x, y = spot(40, 170)
            T.append(self.heli_target('radar', x, y))
            title = 'ASALTO A BATERÍA COSTERA' if kind == 'nest' else 'DESPEJAR ' + tg['name'].upper()
            ship = None
        else:
            title = 'CAZA DE BUQUE ENEMIGO'
            ship = dict(x=W / 2 + 280, y=H / 2, h=0.0, a=random.uniform(0, 6.28), hp=float(40 + 8 * w), max=float(40 + 8 * w), dead=False,
                        dt=0.0)
            for rel in (-62, 4, 64) if w < 3 else (-66, -22, 22, 66):
                m = self.heli_target('aa', 0, 0)
                m['rel'] = rel
                T.append(m)
            if w >= 4:
                m = self.heli_target('sam', 0, 0)
                m['rel'] = 0
                T.append(m)
        self.hm = dict(kind=kind, tg=tg, T=T, land=land, off=off, ship=ship, title=title, t=0.0, phase='play', pt=0.0, ok=False,
                       p=dict(x=W / 2 - 360.0, y=H / 2 + 200.0, vx=0.0, vy=0.0, h=45.0, hp=100.0, rk=10, cd=0.0, rcd=0.0, flash=0.0,
                              dead=False, rot=0.0, side=1),
                       pb=[], rk=[], eb=[], sam=[], n0=len(T) + (1 if ship else 0))
        self.aim = [W / 2, H / 2]
        self.go('heli')
        self.banner(title, 'Blackhawk en misión', (130, 255, 190), 2.8)
        self.say('piloto', 'En el aire. WASD para volar, mouse para apuntar, clic para la ametralladora y ESPACIO para los cohetes.', 'info')

    def heli_target(self, kd, x, y):
        hp, r = {'aa': (6, 17), 'bunker': (16, 28), 'sam': (9, 20), 'depot': (10, 26), 'radar': (6, 20)}[kd]
        hp += self.wave // 3 if kd in ('aa', 'bunker') else 0
        return dict(k=kd, x=float(x), y=float(y), hp=float(hp), max=float(hp), r=r, cd=random.uniform(1.0, 3.0), burst=0, bcd=0.0,
                    ang=random.uniform(0, 360), dead=False, flash=0.0, rel=None)

    def upd_heli(self, dt):
        m = self.hm
        p = m['p']
        keys = pygame.key.get_pressed()
        m['t'] += dt
        p['flash'] = max(0.0, p['flash'] - dt)
        p['rot'] += dt * 28
        ship = m['ship']
        if ship and not ship['dead']:
            ship['a'] += 0.16 * dt
            ship['x'] = W / 2 + math.cos(ship['a']) * 290
            ship['y'] = H / 2 + math.sin(ship['a']) * 190
            ship['h'] = bearing(-math.sin(ship['a']) * 290, math.cos(ship['a']) * 190)
            for t in m['T']:
                if t['rel'] is not None and not t['dead']:
                    ox, oy = vec(ship['h'], t['rel'])
                    t['x'], t['y'] = ship['x'] + ox, ship['y'] + oy
        if not p['dead'] and m['phase'] == 'play':
            mx = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            my = (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0) - (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0)
            n = math.hypot(mx, my) or 1.0
            p['vx'] += (mx / n * 250 - p['vx']) * min(1.0, dt * 3.2)
            p['vy'] += (my / n * 250 - p['vy']) * min(1.0, dt * 3.2)
            p['x'] = clamp(p['x'] + p['vx'] * dt, 50, W - 50)
            p['y'] = clamp(p['y'] + p['vy'] * dt, 60, H - 50)
            want = bearing(self.aim[0] - p['x'], self.aim[1] - p['y'])
            p['h'] = (p['h'] + clamp(angle_diff(p['h'], want), -TURN * dt, TURN * dt)) % 360
            p['cd'] = max(0.0, p['cd'] - dt)
            p['rcd'] = max(0.0, p['rcd'] - dt)
            if (pygame.mouse.get_pressed()[0] or keys[pygame.K_f]) and p['cd'] <= 0:
                p['cd'] = 0.065 * self.up_reload()
                p['side'] *= -1
                ox, oy = vec(p['h'] + 90 * p['side'], 14)
                nx, ny = vec(p['h'], 50)
                a = p['h'] + random.uniform(-1.8, 1.8)
                vx, vy = vec(a, 760)
                m['pb'].append(dict(x=p['x'] + ox + nx, y=p['y'] + oy + ny, vx=vx + p['vx'] * 0.3, vy=vy + p['vy'] * 0.3, life=0.7))
                if random.random() < 0.35:
                    self.audio.play('mg', .15)
                self.fx.add('glow', p['x'] + ox + nx, p['y'] + oy + ny, life=.05, r0=8, r1=16, col=(255, 220, 140))
            if keys[pygame.K_SPACE]:
                self.heli_rocket()
        # balas del jugador
        for b in m['pb'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            hit = False
            for t in self.heli_hit_list(m):
                if dist(b['x'], b['y'], t['x'], t['y']) < t['r'] + 4:
                    self.heli_damage(t, (1.0 if t['k'] != 'bunker' else 0.6) * self.up_dmg())
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-80, 80), random.uniform(-80, 80), 0.25, col=(255, 210, 120), drag=2)
                    hit = True
                    break
            if not hit and ship and not ship['dead'] and self.heli_on_ship(ship, b['x'], b['y']):
                self.heli_ship_damage(0.5 * self.up_dmg())
                self.fx.add('spark', b['x'], b['y'], random.uniform(-80, 80), random.uniform(-80, 80), 0.25, col=(255, 210, 120), drag=2)
                hit = True
            if not hit:
                for s in m['sam']:
                    if dist(b['x'], b['y'], s['x'], s['y']) < 12:
                        s['hp'] = 0
                        hit = True
                        break
            if hit or b['life'] <= 0 or not (-20 < b['x'] < W + 20 and -20 < b['y'] < H + 20):
                m['pb'].remove(b)
        # cohetes
        for r in m['rk'][:]:
            r['sp'] = min(640.0, r['sp'] + 520 * dt)
            vx, vy = vec(r['h'], r['sp'])
            r['x'] += vx * dt
            r['y'] += vy * dt
            r['life'] -= dt
            r['trail'] = (r['trail'] + [(r['x'], r['y'])])[-10:]
            if random.random() < dt * 40:
                self.fx.add('smoke', r['x'], r['y'], 0, 0, 0.6, 3, 9, (170, 170, 176))
            boom = r['life'] <= 0 or not (-30 < r['x'] < W + 30 and -30 < r['y'] < H + 30)
            if not boom:
                for t in self.heli_hit_list(m):
                    if dist(r['x'], r['y'], t['x'], t['y']) < t['r'] + 6:
                        boom = True
                        break
                if ship and not ship['dead'] and self.heli_on_ship(ship, r['x'], r['y']):
                    boom = True
            if boom:
                m['rk'].remove(r)
                self.heli_blast(r['x'], r['y'], 70 * self.up_blast(), 9.0 * self.up_dmg(), 5.0 * self.up_dmg(), 1.0)
        # enemigos
        if m['phase'] == 'play' and not p['dead']:
            for t in m['T']:
                if t['dead']:
                    continue
                self.heli_enemy_ai(t, dt)
        # balas enemigas
        for b in m['eb'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if not p['dead'] and dist(b['x'], b['y'], p['x'], p['y']) < 24:
                m['eb'].remove(b)
                self.heli_hurt(b['dmg'])
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.3, col=(255, 160, 90), drag=2)
            elif b['life'] <= 0 or not (-40 < b['x'] < W + 40 and -40 < b['y'] < H + 40):
                m['eb'].remove(b)
        for s in m['sam'][:]:
            want = bearing(p['x'] - s['x'], p['y'] - s['y'])
            s['h'] = (s['h'] + clamp(angle_diff(s['h'], want), -95 * dt, 95 * dt)) % 360
            vx, vy = vec(s['h'], 235)
            s['x'] += vx * dt
            s['y'] += vy * dt
            s['life'] -= dt
            s['trail'] = (s['trail'] + [(s['x'], s['y'])])[-14:]
            if random.random() < dt * 30:
                self.fx.add('smoke', s['x'], s['y'], 0, 0, 0.8, 3, 10, (200, 200, 205))
            if s['hp'] <= 0 or s['life'] <= 0:
                m['sam'].remove(s)
                self.fx.explode(s['x'], s['y'], 0.6)
                self.audio.play('boom_s', .3)
            elif not p['dead'] and dist(s['x'], s['y'], p['x'], p['y']) < 24:
                m['sam'].remove(s)
                self.fx.explode(s['x'], s['y'], 1.0, True)
                self.heli_hurt(22)
        self.fx.update(dt)
        # resultado
        if m['phase'] == 'play':
            alive_t = [t for t in m['T'] if not t['dead']]
            done = not alive_t and (not ship or ship['dead'])
            if p['dead']:
                m['phase'], m['pt'] = 'result', 0.0
                m['ok'] = False
                self.banner('BLACKHAWK DERRIBADO', 'La misión fracasó', (255, 80, 70), 3.0)
                self.say('piloto', '¡Nos derribaron! Mayday, mayday...', 'bad')
            elif done:
                m['phase'], m['pt'] = 'result', 0.0
                m['ok'] = True
                bonus = 1200 + 300 * self.wave
                self.add_score(bonus)
                self.audio.play('win', .8)
                self.banner('¡MISIÓN CUMPLIDA!', 'Bonus +%d  |  +8 munición  |  +25 combustible' % bonus, (120, 255, 160), 3.2)
        else:
            m['pt'] += dt
            if m['pt'] > 3.2:
                self.end_heli()

    def heli_hit_list(self, m):
        return [t for t in m['T'] if not t['dead']]

    @staticmethod
    def heli_on_ship(ship, x, y):
        ax, ay = vec(ship['h'], 80)
        bx, by = -ax, -ay
        px, py = x - (ship['x'] + bx), y - (ship['y'] + by)
        vx, vy = ax - bx, ay - by
        l2 = vx * vx + vy * vy or 1.0
        t = clamp((px * vx + py * vy) / l2, 0, 1)
        return math.hypot(px - vx * t, py - vy * t) < 30

    def heli_ship_damage(self, dmg):
        ship = self.hm['ship']
        ship['hp'] -= dmg
        ship['dt'] = 0.1
        if ship['hp'] <= 0 and not ship['dead']:
            ship['dead'] = True
            self.add_score(800)
            self.shake = 18
            self.audio.play('boom_l')
            for _ in range(8):
                self.fx.explode(ship['x'] + random.uniform(-70, 70), ship['y'] + random.uniform(-70, 70), 1.4, True)
            for t in self.hm['T']:
                if t['rel'] is not None and not t['dead']:
                    t['dead'] = True

    def heli_damage(self, t, dmg):
        t['hp'] -= dmg
        t['flash'] = 0.08
        if t['hp'] <= 0 and not t['dead']:
            t['dead'] = True
            pts = {'aa': 150, 'bunker': 250, 'sam': 200, 'depot': 300, 'radar': 100}[t['k']]
            self.add_score(pts)
            self.pop('+%d' % pts, t['x'], t['y'] - 20)
            self.audio.play('boom_s', .6)
            if t['k'] == 'depot':
                self.fx.explode(t['x'], t['y'], 2.2, True)
                self.shake = max(self.shake, 14)
                self.heli_blast(t['x'], t['y'], 130, 10.0, 6.0, 0.6, source=t)
            else:
                self.fx.explode(t['x'], t['y'], 1.1, True)
                self.shake = max(self.shake, 6)

    def heli_blast(self, x, y, R, direct, splash, selfd, source=None):
        m = self.hm
        self.fx.explode(x, y, R / 60.0, True)
        self.fx.add('glow', x, y, life=.35, r0=R * 0.4, r1=R * 1.1, col=(255, 200, 120))
        self.audio.play('boom_s', .6)
        self.shake = max(self.shake, 6)
        for t in self.heli_hit_list(m):
            if t is source:
                continue
            d = dist(x, y, t['x'], t['y'])
            if d < t['r'] + 6:
                self.heli_damage(t, direct)
            elif d < R + t['r']:
                self.heli_damage(t, splash * (1 - d / (R + t['r'])))
        ship = m['ship']
        if ship and not ship['dead'] and (self.heli_on_ship(ship, x, y) or dist(x, y, ship['x'], ship['y']) < R + 40):
            self.heli_ship_damage(direct if self.heli_on_ship(ship, x, y) else splash * 0.5)
        p = m['p']
        if not p['dead'] and dist(x, y, p['x'], p['y']) < R * 0.8 and selfd < 1.0 and source is not None:
            self.heli_hurt(8)

    def heli_hurt(self, dmg):
        p = self.hm['p']
        if p['dead'] or self.hm['phase'] != 'play':
            return
        p['hp'] -= dmg
        p['flash'] = 0.25
        self.shake = max(self.shake, 7)
        self.audio.play('hit', .6)
        if p['hp'] <= 0:
            p['dead'] = True
            self.fx.explode(p['x'], p['y'], 2.2, True)
            self.audio.play('boom_l')
            self.shake = 20

    def heli_rocket(self):
        m = self.hm
        p = m['p']
        if self.state != 'heli' or p['dead'] or m['phase'] != 'play' or p['rcd'] > 0:
            return
        if p['rk'] <= 0:
            self.audio.play('empty')
            return
        p['rk'] -= 1
        p['rcd'] = 0.38 * self.up_reload()
        ox, oy = vec(p['h'] + 90 * (1 if p['rk'] % 2 else -1), 52)
        m['rk'].append(dict(x=p['x'] + ox, y=p['y'] + oy, h=p['h'], sp=330.0, life=1.5, trail=[]))
        self.audio.play('launch', .7)
        self.fx.add('glow', p['x'] + ox, p['y'] + oy, life=.15, r0=14, r1=34, col=(255, 210, 140))

    def heli_enemy_ai(self, t, dt):
        m = self.hm
        p = m['p']
        d = dist(t['x'], t['y'], p['x'], p['y'])
        k = t['k']
        t['flash'] = max(0.0, t['flash'] - dt)
        t['cd'] -= dt
        if k in ('aa', 'bunker', 'sam'):
            want = bearing(p['x'] - t['x'], p['y'] - t['y'])
            t['ang'] = (t['ang'] + clamp(angle_diff(t['ang'], want), -200 * dt, 200 * dt)) % 360
        w = self.wave
        if k == 'aa' and d < 560:
            if t['burst'] > 0:
                t['bcd'] -= dt
                if t['bcd'] <= 0:
                    t['burst'] -= 1
                    t['bcd'] = 0.11
                    lead = d / 360.0
                    a = bearing(p['x'] + p['vx'] * lead * 0.8 - t['x'], p['y'] + p['vy'] * lead * 0.8 - t['y']) + random.uniform(-3, 3)
                    vx, vy = vec(a, 360)
                    ox, oy = vec(a, 22)
                    m['eb'].append(dict(x=t['x'] + ox, y=t['y'] + oy, vx=vx, vy=vy, life=1.7, dmg=5, flak=True))
                    self.audio.play('mg', .12)
            elif t['cd'] <= 0:
                t['burst'], t['bcd'] = 4, 0.0
                t['cd'] = random.uniform(1.8, 3.0) * max(0.6, 1 - 0.05 * w)
        elif k == 'bunker' and d < 430:
            if t['burst'] > 0:
                t['bcd'] -= dt
                if t['bcd'] <= 0:
                    t['burst'] -= 1
                    t['bcd'] = 0.09
                    a = bearing(p['x'] - t['x'], p['y'] - t['y']) + random.uniform(-6, 6)
                    vx, vy = vec(a, 400)
                    ox, oy = vec(a, 28)
                    m['eb'].append(dict(x=t['x'] + ox, y=t['y'] + oy, vx=vx, vy=vy, life=1.2, dmg=3, flak=False))
            elif t['cd'] <= 0:
                t['burst'] = 6
                t['cd'] = random.uniform(2.4, 3.6)
        elif k == 'sam' and d < 700 and t['cd'] <= 0 and len(m['sam']) < 3:
            t['cd'] = random.uniform(5.5, 8.0)
            m['sam'].append(dict(x=t['x'], y=t['y'], h=bearing(p['x'] - t['x'], p['y'] - t['y']), hp=1, life=5.0, trail=[]))
            self.audio.play('alarm', .3)
            self.pop('¡MISIL!', p['x'], p['y'] - 40, (255, 90, 70))
        elif k == 'radar':
            t['ang'] = (t['ang'] + 90 * dt) % 360

    def end_heli(self):
        m = self.hm
        tg = m['tg']
        if m['ok']:
            if m['kind'] == 'ship':
                if tg in self.enemies:
                    self.enemies.remove(tg)
            elif m['kind'] == 'island':
                self.cleared_isl.add(tg['idx'])
                self.banner('¡ISLA DESPEJADA!', 'Antena sin resistencia', (120, 220, 255), 3.0)
                self.say('piloto', '¡Isla despejada! Acercate con el barco y presioná L: instalás la antena sin resistencia.', 'ok')
            else:
                tg['alive'] = False
            self.ammo = min(40, self.ammo + 8)
            self.fuel = min(100.0, self.fuel + 25)
        else:
            self.heli_cd = max(self.heli_cd, 60.0)
        self.go('map')

    # ------------------------------------------------------------ DIBUJO
    def heli_flash_img(self, key, surf):
        im = self.ht_flash.get(key)
        if im is None:
            im = surf.copy()
            im.fill((120, 120, 110, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.ht_flash[key] = im
        return im

    def draw_heli_target(self, cv, t, tt):
        x, y = int(t['x']), int(t['y'])
        k = t['k']
        art = self.ht_art[k]
        base = art['base']
        if t['dead']:
            w = art['wreck']
            cv.blit(w, (x - w.get_width() // 2, y - w.get_height() // 2))
            if random.random() < 0.15:
                self.fx.add('smoke', x + random.uniform(-8, 8), y, random.uniform(-6, 6), -28, 1.8, 5, 18, (40, 40, 44))
            glow(cv, x, y, 18 + 5 * math.sin(tt * 9 + x), (255, 110, 40), 0.6)
            return
        hit = t['flash'] > 0
        cv.blit(self.heli_flash_img(k, base) if hit else base, (x - base.get_width() // 2, y - base.get_height() // 2))
        top = art['top']
        if top is not None:
            head = t['ang'] + 90 if k == 'radar' else t['ang']
            rt = pygame.transform.rotate(self.heli_flash_img(k + 't', top) if hit else top, -head)
            cv.blit(rt, (x - rt.get_width() // 2, y - rt.get_height() // 2))
        if t['hp'] < t['max'] and t['rel'] is None or (t['rel'] is not None and t['hp'] < t['max']):
            pygame.draw.rect(cv, (8, 12, 24), (x - 16, y - t['r'] - 12, 32, 5))
            pygame.draw.rect(cv, (240, 80, 70), (x - 15, y - t['r'] - 11, int(30 * t['hp'] / t['max']), 3))

    def draw_heli(self, cv):
        m = self.hm
        p = m['p']
        tt = self.t
        self.draw_ocean(cv, tt * 10, tt * 4, tt)
        self.dim(cv, 14)
        if m['land'] is not None:
            cv.blit(m['land'], m['off'])
        ship = m['ship']
        if ship:
            key = 'e_hull'
            surf, sh = self.ships[key]
            if not hasattr(self, 'bh_ship'):
                self.bh_ship = (pygame.transform.rotozoom(surf, 0, 1.6), pygame.transform.rotozoom(sh, 0, 1.6))
            s0, s1 = self.bh_ship
            r = pygame.transform.rotate(s0, -ship['h'])
            rs = pygame.transform.rotate(s1, -ship['h'])
            if ship['dead']:
                r = r.copy()
                r.fill((70, 66, 64), special_flags=pygame.BLEND_RGB_MULT)
                cv.blit(r, (ship['x'] - r.get_width() // 2, ship['y'] - r.get_height() // 2))
                for k in range(5):
                    glow(cv, ship['x'] + math.sin(k * 2.1) * 40, ship['y'] + math.cos(k * 1.7) * 55, 26 + 6 * math.sin(tt * 8 + k), (255, 120, 40), 0.7)
            else:
                rs.set_alpha(85)
                cv.blit(rs, (ship['x'] - rs.get_width() // 2 + 6, ship['y'] - rs.get_height() // 2 + 9))
                if ship['dt'] > 0:
                    ship['dt'] -= 0.016
                    r = r.copy()
                    r.fill((70, 70, 70, 0), special_flags=pygame.BLEND_RGB_ADD)
                cv.blit(r, (ship['x'] - r.get_width() // 2, ship['y'] - r.get_height() // 2))
                if ship['hp'] < ship['max'] * 0.5 and random.random() < 0.3:
                    self.fx.add('smoke', ship['x'] + random.uniform(-30, 30), ship['y'] + random.uniform(-50, 50), 0, -30, 1.8, 6, 22, (40, 40, 44))
                pygame.draw.rect(cv, (8, 12, 24), (ship['x'] - 40, ship['y'] - 110, 80, 8))
                pygame.draw.rect(cv, (240, 80, 70), (ship['x'] - 39, ship['y'] - 109, int(78 * ship['hp'] / ship['max']), 6))
        for t in m['T']:
            self.draw_heli_target(cv, t, tt)
        for s in m['sam']:
            pts = s['trail']
            for i in range(1, len(pts)):
                pygame.draw.line(cv, (230, 230, 235), pts[i - 1], pts[i], 2)
            ex, ey = vec(s['h'], 9)
            pygame.draw.line(cv, (240, 80, 60), (s['x'] - ex, s['y'] - ey), (s['x'] + ex, s['y'] + ey), 5)
            glow(cv, s['x'], s['y'], 14, (255, 140, 80))
        for b in m['eb']:
            col = (255, 170, 90) if b['flak'] else (255, 230, 150)
            glow(cv, b['x'], b['y'], 9, col, 0.8)
            pygame.draw.circle(cv, (255, 250, 220), (int(b['x']), int(b['y'])), 3)
        for r in m['rk']:
            pts = r['trail']
            for i in range(1, len(pts)):
                pygame.draw.line(cv, (255, int(120 + 8 * i), 60), pts[i - 1], pts[i], 3)
            glow(cv, r['x'], r['y'], 16, (255, 190, 110))
            pygame.draw.circle(cv, (255, 255, 230), (int(r['x']), int(r['y'])), 3)
        for b in m['pb']:
            pygame.draw.line(cv, (255, 240, 160), (b['x'], b['y']), (b['x'] - b['vx'] * 0.03, b['y'] - b['vy'] * 0.03), 2)
        if not p['dead']:
            self.draw_blackhawk(cv, p['x'], p['y'], p['h'], p['rot'], 0.8)
            if p['flash'] > 0:
                glow(cv, p['x'], p['y'], 60, (255, 90, 70), p['flash'] * 2)
        self.fx.draw(cv)
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (120, 255, 190), (ax, ay), 16, 2)
        pygame.draw.circle(cv, (120, 255, 190), (ax, ay), 2)
        for dx, dy in ((-26, 0), (26, 0), (0, -26), (0, 26)):
            pygame.draw.line(cv, (120, 255, 190), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        # HUD
        self.panel(cv, (14, 12, 300, 92), 170)
        self.text(cv, 'BLACKHAWK', self.f_s, (130, 255, 190), 26, 18)
        hpf = clamp(p['hp'] / 100.0, 0, 1)
        self.bar(cv, 26, 40, 276, 22, hpf, (80, 230, 110) if hpf > 0.4 else (240, 80, 70), 'CASCO %d' % max(0, p['hp']))
        self.text(cv, 'COHETES %d' % p['rk'], self.f_s, (255, 220, 140), 26, 70)
        left = len([t for t in m['T'] if not t['dead']]) + (1 if ship and not ship['dead'] else 0)
        self.panel(cv, (W // 2 - 230, 12, 460, 56), 170)
        self.text(cv, m['title'], self.f_m, (255, 255, 255), W // 2, 16, 'c')
        self.text(cv, 'OBJETIVOS RESTANTES: %d' % left, self.f_s, (255, 190, 150), W // 2, 42, 'c')
        self.text(cv, 'Clic: ametralladora | ESPACIO o clic der.: cohetes | Esquivá los misiles', self.f_s, (200, 225, 255), W // 2, H - 28, 'c')
