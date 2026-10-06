"""Modo mapa: navegación, olas, ataques a ciudades, convoy, náufragos y radar."""
import math
import pygame
import random
from .radio_mode import LAND_RADARS, PORT_RADARS
from .common import (
    ANTENNA_ISLANDS, BOSS_NAMES, ENEMY_PORT,
    EXTRA_ISLANDS, H, HELIPAD, MAX_LANDING_ATTEMPTS, SHIELD_R,
    SKY_W, VMAX, W, WIN_WAVE,
    WORLD_H, WORLD_W, angle_diff, bearing,
    clamp, coast_r, dist, draw_circ,
    glow, vec)
from .boss_art import BOSS_TYPES


class MapMixin:
    def make_skyline(self, seed):
        rnd = random.Random(seed * 7)
        out = []
        x = 0
        while x < SKY_W - 30:
            w = rnd.randint(30, 62)
            mid = 1 - abs((x + w / 2) - SKY_W / 2) / (SKY_W / 2)
            h = int(rnd.randint(50, 110) + mid * rnd.randint(30, 120))
            out.append(dict(x=x, w=w, h=h, h0=h, s=rnd.randint(0, 99), ant=rnd.random() < .3))
            x += w + rnd.randint(0, 5)
        return out

    def rand_wp(self):
        for _ in range(40):
            x, y = random.uniform(120, WORLD_W - 120), random.uniform(120, WORLD_H - 120)
            if not self.on_land(x, y, 80):
                return [x, y]
        return [WORLD_W / 2, WORLD_H / 2]

    def spawn_nests(self):
        """Baterías costeras enemigas sobre algunos islotes pequeños (se renuevan cada oleada)."""
        hp = 14 + 4 * self.wave
        self.nests = [dict(x=x, y=y, r=r, hp=float(hp), max=float(hp), cool=0.0, ang=180.0, nest=True, alive=True, seen=False)
                      for (x, y, r, _s) in random.sample([i for i in self.decor_now() if dist(i[0], i[1], self.sx, self.sy) > 800], 10)]

    def spawn_wave(self):
        n = min(3 + self.wave, 9)
        for _ in range(n):
            x = y = 0
            for _ in range(60):
                x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
                if dist(x, y, self.sx, self.sy) > 700 and not self.on_land(x, y, 90):
                    break
            mh = 10 + 2 * (self.wave - 1)
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=mh, max=mh, state='patrol',
                                     wp=self.rand_wp(), cool=0.0, is_boss=False))
        for _ in range(0 if self.wave < 2 else (1 if self.wave < 4 else 2)):
            for _ in range(60):
                x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
                if dist(x, y, self.sx, self.sy) > 900 and not self.on_land(x, y, 90):
                    break
            mh = 8 + 2 * self.wave
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=mh, max=mh, state='patrol',
                                     wp=self.rand_wp(), cool=0.0, is_boss=False, sub=True))
        x = y = 0
        for _ in range(60):
            x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
            if dist(x, y, self.sx, self.sy) > 900 and not self.on_land(x, y, 120):
                break
        boss_hp = 36 + 16 * (self.wave - 1)
        self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=boss_hp, max=boss_hp,
                                 state='patrol', wp=self.rand_wp(), cool=0.0, is_boss=True, shield=True,
                                 hack_cd=0.0, seen=False, name=BOSS_NAMES[(self.wave - 1) % len(BOSS_NAMES)],
                                 btype=(self.wave - 1) % len(BOSS_TYPES)))

    # ---------------------------------------------------------- MAPA
    def upd_map(self, dt):
        keys = pygame.key.get_pressed()
        thr = (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0) - (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0)
        turn = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
        docking = self.nearest_dock()
        vmax = VMAX if self.fuel > 0 else 45.0          # sin combustible: motor auxiliar lento
        if thr > 0:
            self.sv = min(vmax, self.sv + 110 * dt)
        elif thr < 0:
            self.sv = max(-45, self.sv - 130 * dt)
        else:
            self.sv -= self.sv * 0.45 * dt
            self.sv -= math.copysign(min(abs(self.sv), 8 * dt), self.sv)
        if docking and keys[pygame.K_r]:
            self.sv -= self.sv * 3 * dt
        if self.fuel <= 0:
            self.sv = clamp(self.sv, -20.0, vmax)
        steer = 58 * clamp(abs(self.sv) / 70, 0.2, 1.0) * (1 if self.sv >= 0 else -1)
        self.sh = (self.sh + turn * steer * dt) % 360
        dx, dy = vec(self.sh, self.sv * dt)
        self.sx += dx
        self.sy += dy
        self.sx, self.sy = clamp(self.sx, 40, WORLD_W - 40), clamp(self.sy, 40, WORLD_H - 40)
        self.crash_t = max(0.0, self.crash_t - dt)
        for ix, iy, ir, sd in self.islands:                   # costa: no se puede entrar a tierra
            d = dist(self.sx, self.sy, ix, iy) or 1.0
            lim = coast_r(ir, sd, math.atan2(self.sy - iy, self.sx - ix), 1.06) + 14
            if d < lim:
                if abs(self.sv) > 110 and self.crash_t <= 0:
                    self.crash_t = 1.5
                    self.hull -= 4
                    self.audio.play('hit', .6)
                    self.toast('¡Encallaste! Casco dañado', (255, 120, 90))
                    self.shake = 6
                    if self.hull <= 0:
                        return self.lose_ship('Tu buque encalló y se hundió')
                self.sx = ix + (self.sx - ix) / d * lim
                self.sy = iy + (self.sy - iy) / d * lim
                self.sv *= 0.3
        self.fuel = max(0.0, self.fuel - abs(self.sv) / VMAX * 0.9 * dt)
        self.audio.engine_vol(abs(self.sv) / VMAX * 0.9 + 0.1)
        if self.fuel <= 0 and not self.empty_fuel_aid:
            self.empty_fuel_aid = True
            a = random.uniform(0, 6.28)
            self.crates.append(dict(x=self.sx + math.cos(a) * 170, y=self.sy + math.sin(a) * 170, kind='fuel', t=0))
            self.toast('Sin combustible: motor auxiliar lento. Recogé el bidón de emergencia', (255, 200, 90))
        if self.fuel > 15:
            self.empty_fuel_aid = False
        # estela
        self.wake_t -= dt
        if abs(self.sv) > 15 and self.wake_t <= 0:
            self.wake_t = 0.05
            bx, by = vec(self.sh, -26)
            self.fxm.add('foam', self.sx + bx + random.uniform(-4, 4), self.sy + by + random.uniform(-4, 4), life=1.6,
                         r0=4, r1=13, col=(230, 245, 255))
        # humo si está dañado
        if self.up_n('nano') and 0 < self.hull < self.hull_max:
            self.hull = min(self.hull_max, self.hull + 0.6 * self.up_n('nano') * dt)
        if self.hull < 45 and random.random() < dt * 8:
            self.fxm.add('smoke', self.sx, self.sy, 0, -20, 1.8, 5, 18, (60, 60, 60))
        # cámara
        tx, ty = self.sx - W / 2, self.sy - H / 2
        self.cam[0] += (tx - self.cam[0]) * min(1, dt * 4)
        self.cam[1] += (ty - self.cam[1]) * min(1, dt * 4)
        self.cam[0] = clamp(self.cam[0], 0, WORLD_W - W)
        self.cam[1] = clamp(self.cam[1], 0, WORLD_H - H)
        # reabastecer
        if docking:
            if keys[pygame.K_r] and abs(self.sv) < 40:
                self.dock_t -= dt
                changed = False
                st = docking['stock']                 # el puerto tiene suministros limitados hasta que se reponga
                empty = []
                if self.fuel < 100:
                    g = min(25 * dt, 100 - self.fuel, st['fuel'])
                    if g > 0:
                        self.fuel += g
                        st['fuel'] -= g
                        changed = True
                    else:
                        empty.append('combustible')
                if self.hull < self.hull_max:
                    g = min(8 * dt, self.hull_max - self.hull, st['repair'])
                    if g > 0:
                        self.hull += g
                        st['repair'] -= g
                        changed = True
                    else:
                        empty.append('reparaciones')
                if self.ammo < 40:
                    if st['ammo'] >= 1:
                        self.ammo_acc += 6 * dt
                        if self.ammo_acc >= 1:
                            self.ammo += 1
                            st['ammo'] -= 1
                            self.ammo_acc = 0
                            changed = True
                    else:
                        empty.append('munición')
                if empty and self.t - getattr(self, 'stock_toast', -9) > 4:
                    self.stock_toast = self.t
                    self.toast('%s sin %s hasta que se reponga' % (docking['name'], ', '.join(empty)), (255, 190, 120))
                if changed and self.dock_t <= 0:
                    self.dock_t = 0.28
                    self.audio.play('dock', .5)
        # enemigos
        for en in self.enemies:
            self.ai_map(en, dt)
            d = dist(self.sx, self.sy, en['x'], en['y'])
            if en.get('shield'):
                en['hack_cd'] = max(0.0, en['hack_cd'] - dt)
                if d < SHIELD_R:
                    k = d or 1.0
                    self.sx = en['x'] + (self.sx - en['x']) / k * SHIELD_R
                    self.sy = en['y'] + (self.sy - en['y']) / k * SHIELD_R
                    self.sv *= 0.6
                    if self.t - getattr(self, 'shield_toast', -9) > 3:
                        self.shield_toast = self.t
                        self.toast('Escudo digital: presioná H para hackearlo', (255, 120, 220))
                continue
            if d < 78 and en['cool'] <= 0:
                return self.start_combat(en, self.nb_find_nest())
        self.radar_t = max(0.0, self.radar_t - dt)
        self.city_regen(dt)
        self.radar_tick(dt)
        if self.convoy is not None:
            self.upd_convoy(dt)
        else:
            # el reloj corre siempre; si justo hay un ataque o alerta en curso, el convoy sale apenas termine
            self.convoy_t -= dt
            if self.convoy_t <= 0 and self.wave >= 2 and self.attack is None and not self.warned and self.rescue is None:
                self.begin_convoy()
        if self.rescue is not None:
            self.upd_rescue(dt)
        elif self.attack is None:
            self.rescue_t -= dt
            if self.rescue_t <= 0:
                self.begin_rescue()
        for nst in self.nests:
            if not nst['alive']:
                continue
            nst['cool'] = max(0.0, nst['cool'] - dt)
            d = dist(self.sx, self.sy, nst['x'], nst['y'])
            if d < 700:
                nst['ang'] = bearing(self.sx - nst['x'], self.sy - nst['y'])
                if not nst['seen'] and d < 520:
                    nst['seen'] = True
                    self.audio.play('ping')
                    self.toast('¡Batería costera enemiga!', (255, 120, 90))
            if d < 330 and nst['cool'] <= 0:
                ship = self.nb_find_ship()
                if ship is not None:
                    return self.start_combat(ship, nst)
                return self.start_combat(nst)
        # cajas
        self.crate_t -= dt
        if self.crate_t <= 0 and len(self.crates) < 5:
            self.crate_t = 16.0
            for _ in range(30):
                x, y = random.uniform(100, WORLD_W - 100), random.uniform(100, WORLD_H - 100)
                if not self.on_land(x, y, 40):
                    self.crates.append(dict(x=x, y=y, kind=random.choice(['ammo', 'fuel', 'repair']), t=0))
                    break
        for c in self.crates[:]:
            c['t'] += dt
            if dist(self.sx, self.sy, c['x'], c['y']) < 42:
                self.crates.remove(c)
                self.audio.play('pickup')
                if c['kind'] == 'ammo':
                    self.ammo = min(40, self.ammo + 10)
                    self.toast('+10 munición', (255, 230, 90))
                elif c['kind'] == 'fuel':
                    amt = 60 if c.get('big') else 35
                    self.fuel = min(100, self.fuel + amt)
                    self.toast('+%d%% combustible' % amt, (120, 255, 140))
                else:
                    self.hull = min(self.hull_max, self.hull + 30)
                    self.toast('+30 casco', (255, 255, 255))
            elif c['t'] > 130:
                self.crates.remove(c)
        # ataque de misiles
        alive = [c for c in self.cities if not c['dead']]
        self.strike_t -= dt
        if self.attack is None and alive and self.strike_t <= 4.0 and not self.warned:
            # nunca la misma ciudad dos veces seguidas (si queda más de una viva)
            self.strike_city = random.choice([c for c in alive if c is not self.last_strike] or alive)
            self.last_strike = self.strike_city
            self.strike_n += 1
            inst = [i for i, v in self.antennas.items() if v]
            if inst and self.strike_n >= 3 and random.random() < 0.25:
                self.begin_attack(self.antenna_city(random.choice(inst)), 'antenna')
            else:
                self.strike_kind = self.next_strike_kind()
                if self.strike_kind == 'missile':
                    self.warned = True
                    self.audio.play('alarm')
                    self.banner('¡ALERTA DE MISILES!', 'Objetivo: ' + self.strike_city['name'], (255, 80, 70), 3.8)
                else:
                    self.begin_attack(self.strike_city, self.strike_kind)
        if self.warned and self.strike_t <= 0:
            self.start_defense(self.strike_city)
            return
        if self.attack is not None and self.upd_attack(dt):
            return
        # ciudades dañadas echan humo
        for c in alive:
            if c['hp'] < 55 and random.random() < dt * 5:
                self.fxm.add('smoke', c['x'] + random.uniform(-30, 30), c['y'] + random.uniform(-30, 10), 0, -25, 2.5,
                             8, 28, (50, 50, 50))
        self.fxm.update(dt)
        self.war_update(dt)
        self.heli_map_update(dt)
        # oleada completada
        if not self.enemies:
            self.wave_clear()

    def next_strike_kind(self):
        """Baraja de ataques: sale cada tipo con frecuencia pareja y nunca repite el anterior."""
        if self.strike_n <= 1:
            return 'missile'
        if self.strike_n == 2 and self.wave == 1:        # el segundo ataque de la oleada 1 es aéreo, para conocerlo temprano
            return 'aerial'
        if not self.strike_deck:
            self.strike_deck = ['missile', 'aerial', 'tank', 'aerial', 'ground', 'missile']
            random.shuffle(self.strike_deck)
        for i, k in enumerate(self.strike_deck):
            if k != self.strike_kind:
                return self.strike_deck.pop(i)
        return self.strike_deck.pop()

    def begin_rescue(self):
        """Náufragos: a veces bajo el alcance de una batería costera."""
        live = [n for n in self.nests if n['alive']]
        for _ in range(60):
            if live and random.random() < 0.6:
                n = random.choice(live)
                a = random.uniform(0, 6.28)
                d = random.uniform(235, 300)
                x, y = n['x'] + math.cos(a) * d, n['y'] + math.sin(a) * d
                guarded = True
            else:
                x, y = random.uniform(200, WORLD_W - 200), random.uniform(200, WORLD_H - 200)
                guarded = False
            if 100 < x < WORLD_W - 100 and 100 < y < WORLD_H - 100 and not self.on_land(x, y, 70) and dist(x, y, self.sx, self.sy) > 500:
                break
        t = clamp(dist(x, y, self.sx, self.sy) / (VMAX * 0.7) + 25, 45, 90)
        self.rescue = dict(x=x, y=y, t=t, total=t, prog=0.0, guarded=guarded)
        self.audio.play('alarm', .6)
        self.banner('¡SOS: NÁUFRAGOS!', ('Bajo el alcance de una batería costera | ' if guarded else '') + 'Llegá en %d s y quedate junto a la balsa' % t,
                    (255, 220, 90), 4.0)

    def upd_rescue(self, dt):
        r = self.rescue
        r['t'] -= dt
        d = dist(self.sx, self.sy, r['x'], r['y'])
        if d < 95 and abs(self.sv) < 70:
            r['prog'] += dt / 4.0
            if int(r['prog'] * 8) != int((r['prog'] - dt / 4.0) * 8):
                self.audio.play('blip', .4)
        else:
            r['prog'] = max(0.0, r['prog'] - dt / 6.0)
        if r['prog'] >= 1.0:
            reward = random.choice(('hull', 'fuel', 'ammo'))
            pts = 300 + 100 * self.wave
            self.add_score(pts)
            self.audio.play('win', .7)
            if reward == 'hull':
                self.hull = min(self.hull_max, self.hull + 25)
                gift = '+25 casco (los náufragos ayudan con las reparaciones)'
            elif reward == 'fuel':
                self.fuel = min(100, self.fuel + 40)
                gift = '+40% combustible'
            else:
                self.ammo = min(40, self.ammo + 12)
                gift = '+12 munición'
            self.banner('¡NÁUFRAGOS RESCATADOS!', '+%d puntos  |  %s' % (pts, gift), (120, 255, 160), 3.6)
            self.rescue = None
            self.rescue_t = random.uniform(80, 120)
        elif r['t'] <= 0:
            self.toast('Los náufragos se perdieron en el mar...', (255, 160, 120))
            self.rescue = None
            self.rescue_t = random.uniform(70, 100)

    def antenna_city(self, i):
        """Pseudo-ciudad que representa una antena instalada (para el viaje y la defensa)."""
        x, y, r, sd = EXTRA_ISLANDS[i]
        return dict(name='ANTENA %s' % self.isl_name(i), x=x, y=y, r=r, hp=100.0, dead=False, seed=sd, dock=(x, y), antenna=i)

    ATTACK_TXT = {'antenna': ('Comandos enemigos asaltan tu antena', (120, 220, 255)), 'tank': ('Tanques enemigos entran en', (120, 255, 160)), 'ground': ('Desembarco enemigo en', (255, 150, 60)),
                  'aerial': ('Cazas enemigos sobre', (150, 100, 255))}

    def begin_attack(self, city, kind):
        """Ataque a una ciudad: hay que llegar con el barco antes de que se acabe el tiempo."""
        d = dist(self.sx, self.sy, city['x'], city['y'])
        limit = clamp(d / (VMAX * 0.7) + 14, 30, 80)
        self.attack = dict(city=city, kind=kind, t=limit, total=limit)
        self.strike_t = 1e9
        self.audio.play('alarm')
        txt, col = self.ATTACK_TXT[kind]
        self.banner('¡ATAQUE EN %s!' % city['name'], '%s | Llegá en %d s con tu barco' % (txt, limit), col, 4.2)

    def upd_attack(self, dt):
        at = self.attack
        c = at['city']
        if c['dead'] or (at['kind'] == 'antenna' and not self.antennas[c['antenna']]):
            self.attack = None
            self.strike_t = 30.0
            return False
        at['t'] -= dt
        near = dist(self.sx, self.sy, c['x'], c['y']) < c['r'] * 1.25 + 150 or dist(self.sx, self.sy, c['dock'][0], c['dock'][1]) < 130
        if near:
            self.attack = None
            if at['kind'] == 'antenna':
                self.start_ground(c, antenna=c['antenna'])
            else:
                {'tank': self.start_tank, 'ground': self.start_ground, 'aerial': self.start_aerial}[at['kind']](c)
            return True
        step = 0.5 if at['t'] < 5 else 1.0
        if at['t'] < 10 and int(at['t'] / step) != int((at['t'] + dt) / step):
            self.audio.play('blip', .5)
        if at['t'] <= 0 and at['kind'] == 'antenna':
            self.attack = None
            self.antennas[c['antenna']] = False
            self.audio.play('boom_l')
            self.shake = 14
            self.banner('¡ANTENA DESTRUIDA!', '%s cayó en manos enemigas' % c['name'], (255, 90, 70), 3.4)
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
            return False
        if at['t'] <= 0:
            self.attack = None
            c['hp'] = max(0.0, c['hp'] - 45)
            self.audio.play('boom_l')
            self.shake = 14
            if c['hp'] <= 0:
                c['dead'] = True
                self.banner('¡CIUDAD CAPTURADA!', c['name'], (255, 70, 60), 3.4)
            else:
                self.banner('¡LLEGASTE TARDE!', '%s sufrió daños graves (-45%%)' % c['name'], (255, 90, 70), 3.4)
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
            if all(x['dead'] for x in self.cities):
                self.game_over('Todas las ciudades fueron destruidas')
                return True
        return False

    def draw_pointer(self, cv, cx, cy, wx, wy, label, col, pul=0.5):
        """Flecha en el borde de la pantalla que apunta a un objetivo fuera de vista."""
        sx, sy = wx - cx, wy - cy
        if 40 < sx < W - 40 and 100 < sy < H - 40:
            return
        ang = math.atan2(wy - self.sy, wx - self.sx)
        ax = W / 2 + math.cos(ang) * min(W / 2 - 60, (H / 2 - 60) / max(0.01, abs(math.sin(ang))) * abs(math.cos(ang)))
        ay = H / 2 + math.sin(ang) * min(H / 2 - 60, (W / 2 - 60) / max(0.01, abs(math.cos(ang))) * abs(math.sin(ang)))
        pts = [(ax + math.cos(ang) * 26, ay + math.sin(ang) * 26),
               (ax + math.cos(ang + 2.5) * 22, ay + math.sin(ang + 2.5) * 22),
               (ax + math.cos(ang - 2.5) * 22, ay + math.sin(ang - 2.5) * 22)]
        glow(cv, ax, ay, 40, col, 0.5 + 0.4 * pul)
        pygame.draw.polygon(cv, col, pts)
        self.text(cv, label, self.f_s, col, ax, ay + 24, 'c')

    def draw_rescue(self, cv, cx, cy, y0=8):
        r = self.rescue
        t = self.t
        sx, sy = r['x'] - cx, r['y'] - cy
        pul = 0.5 + 0.5 * math.sin(t * 5)
        if -100 < sx < W + 100 and -100 < sy < H + 100:
            bob = math.sin(t * 2.2 + r['x']) * 3
            draw_circ(cv, sx, sy, 95, (255, 220, 90), 30 + 40 * pul, 2)
            pygame.draw.rect(cv, (120, 84, 50), (sx - 14, sy - 9 + bob, 28, 18), border_radius=4)
            pygame.draw.rect(cv, (200, 150, 90), (sx - 12, sy - 7 + bob, 24, 14), 1, border_radius=3)
            for k, off in enumerate((-8, 0, 8)):
                pygame.draw.circle(cv, (240, 120, 60) if k != 1 else (250, 230, 120), (int(sx + off), int(sy - 2 + bob)), 4)
            pygame.draw.line(cv, (230, 230, 230), (sx, sy + bob), (sx, sy - 24 + bob), 2)
            pygame.draw.polygon(cv, (255, 70, 60), [(sx, sy - 24 + bob), (sx + 13, sy - 19 + bob), (sx, sy - 14 + bob)])
            if r['prog'] > 0:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 32, sy + 22, 64, 9))
                pygame.draw.rect(cv, (120, 255, 160), (sx - 31, sy + 23, int(62 * r['prog']), 7))
                self.text(cv, 'RESCATANDO...', self.f_s, (180, 255, 200), sx, sy + 34, 'c')
        self.panel(cv, (W // 2 - 190, y0, 380, 46), 190)
        yy = y0 + 6
        sec = max(0.0, r['t'])
        self.text(cv, 'SOS NÁUFRAGOS  %02d.%03d' % (int(sec), int((sec % 1) * 1000)), self.f_m,
                  (255, 220, 90) if sec > 10 else (255, 90 + int(100 * pul), 70), W // 2, yy, 'c')
        self.draw_pointer(cv, cx, cy, r['x'], r['y'], 'NÁUFRAGOS', (255, 220, 90), pul)

    def draw_attack(self, cv, cx, cy):
        at = self.attack
        c = at['city']
        t = self.t
        low = at['t'] < 10
        pul = 0.5 + 0.5 * math.sin(t * (14 if at['t'] < 5 else 7))
        col = (255, int(80 + 130 * (1 - pul)), 60) if low else (255, 200, 90)
        sx, sy = c['x'] - cx, c['y'] - cy
        draw_circ(cv, sx, sy, c['r'] * 1.25 + 150, (255, 80, 60), 40 + 60 * pul, 3)
        self.panel(cv, (W // 2 - 215, 8, 430, 78), 200)
        self.text(cv, 'ATAQUE EN %s' % c['name'], self.f_m, col, W // 2, 14, 'c')
        sec = max(0.0, at['t'])
        self.text(cv, '%02d.%03d' % (int(sec), int((sec % 1) * 1000)), self.f_l, col, W // 2 - 70, 42, 'c')
        d = dist(self.sx, self.sy, c['x'], c['y'])
        self.text(cv, '%s  |  %d m' % ({'tank': 'TANQUES', 'ground': 'DESEMBARCO', 'aerial': 'CAZAS', 'antenna': 'COMANDOS'}[at['kind']], int(d)),
                  self.f_s, (210, 220, 240), W // 2 + 110, 52, 'c')
        self.draw_pointer(cv, cx, cy, c['x'], c['y'], c['name'], col, pul)
        if low:
            pygame.draw.rect(cv, (255, 40, 40), (0, 0, W, H), 4 + int(6 * pul))

    def city_stock(self, c):
        """Suministros que el puerto de la ciudad puede dar hasta que termine la oleada (menos si la ciudad está dañada)."""
        k = self.city_cap(c)
        return dict(fuel=k, repair=k, ammo=k)

    def city_cap(self, c):
        """Tope de suministros de una ciudad: 100 de cada cosa, menos si está dañada."""
        return 100.0 * (0.5 + 0.5 * clamp(c['hp'] / 100.0, 0.0, 1.0))

    def city_refill(self, c, amount):
        cap = self.city_cap(c)
        for k in c['stock']:
            c['stock'][k] = min(cap, c['stock'][k] + amount)

    def city_regen(self, dt):
        """Goteo pasivo: +1 de cada cosa cada 20 s (doble si no hay amenaza); la ciudad atacada o en alerta no recupera."""
        threat = self.attack['city'] if self.attack is not None else (self.strike_city if self.warned else None)
        rate = 0.1 if self.attack is None and not self.warned else 0.05
        for c in self.cities:
            if not c['dead'] and c is not threat:
                self.city_refill(c, rate * dt)

    def nearest_dock(self):
        for c in self.cities:
            if not c['dead'] and dist(self.sx, self.sy, c['dock'][0], c['dock'][1]) < 120:
                return c
        return None

    def nearest_landing_island(self):
        best_dist = 280
        best_island = None
        for i, (x, y, r, s) in enumerate(EXTRA_ISLANDS):
            d = dist(self.sx, self.sy, x, y)
            if d < best_dist and i in ANTENNA_ISLANDS and not self.antennas[i]:
                best_dist = d
                best_island = (i, x, y, r, s)
        return best_island

    def wave_clear(self):
        bonus = 1000 * self.wave
        self.add_score(bonus)
        if self.wave >= WIN_WAVE:
            return self.game_over('¡Defendiste el archipiélago!', True)
        self.wave += 1
        for c in self.cities:
            if not c['dead']:
                c['hp'] = min(100, c['hp'] + 20)
        self.ammo = min(40, self.ammo + 12)
        self.hull = min(self.hull_max, self.hull + 40)           # la tripulación repara el barco entre oleadas
        self.fuel = min(100.0, self.fuel + 40)
        for c in self.cities:
            if not c['dead']:
                self.city_refill(c, 40)
        self.radars_reset()                           # los radares enemigos vuelven a operar
        self.war_advance()
        self.spawn_nests()
        self.convoy_t = min(self.convoy_t, 35.0)       # cada oleada nueva trae un convoy pronto
        self.port_tries = 0
        self.port_done = False
        self.audio.play('win', .7)
        self.toast('Bonus +%d  |  Ciudades reparadas  |  +12 munición, +40 casco' % bonus, (120, 255, 160))
        self.autosave(True)                           # autoguardado al terminar la oleada
        self.start_upgrade()

    def ai_map(self, en, dt):
        en['cool'] = max(0.0, en['cool'] - dt)
        d = dist(self.sx, self.sy, en['x'], en['y'])
        is_boss = en.get('is_boss', False)
        chase_dist = 520 if is_boss else (520 if en.get('sub') else 430)

        if is_boss and not en['seen'] and d < 700:
            en['seen'] = True
            self.audio.play('alarm')
            self.banner('¡BUQUE JEFE DETECTADO!', 'Escudo digital: necesitás %d antenas instaladas (L) para hackearlo (H)' % self.antennas_needed(), (255, 120, 220), 4.0)
        if en['state'] == 'patrol' and d < chase_dist and en['cool'] <= 0 and not en.get('shield'):
            en['state'] = 'chase'
            self.audio.play('ping')
            if is_boss:
                self.toast('¡JEFE ENEMIGO DETECTADO!', (255, 50, 50))
            else:
                self.toast('¡Contacto enemigo!', (255, 100, 90))
        elif en['state'] == 'chase' and (d > (1000 if is_boss else 680) or en['cool'] > 0):
            en['state'] = 'patrol'
        if en['state'] == 'chase':
            tx, ty = self.sx, self.sy
            sp = (62 + 3 * self.wave) if is_boss else (88 + 3 * self.wave)
        else:
            tx, ty = en['wp']
            sp = 32 if is_boss else 52
            if en.get('raider') and self.convoy is not None:
                tx, ty, sp = self.convoy['x'], self.convoy['y'], 80
            elif dist(en['x'], en['y'], tx, ty) < 50:
                en['wp'] = self.rand_wp()
        vx, vy = tx - en['x'], ty - en['y']
        n = math.hypot(vx, vy) or 1
        vx, vy = vx / n, vy / n
        for ix, iy, ir, sd in self.islands:
            dd = dist(en['x'], en['y'], ix, iy) or 1.0
            lim = coast_r(ir, sd, math.atan2(en['y'] - iy, en['x'] - ix), 1.1) + (170 if is_boss else 110)
            if dd < lim:
                k = (lim - dd) / (170 if is_boss else 110)
                vx += (en['x'] - ix) / dd * k * 2.4
                vy += (en['y'] - iy) / dd * k * 2.4
        want = bearing(vx, vy)
        en['h'] = (en['h'] + clamp(angle_diff(en['h'], want), -14 * dt if is_boss else -45 * dt, 14 * dt if is_boss else 45 * dt)) % 360
        en['v'] += (sp - en['v']) * min(1, dt * 1.5)
        dx, dy = vec(en['h'], en['v'] * dt)
        en['x'] = clamp(en['x'] + dx, 40, WORLD_W - 40)
        en['y'] = clamp(en['y'] + dy, 40, WORLD_H - 40)
        if random.random() < dt * (18 if is_boss else 14):
            bx, by = vec(en['h'], -62 if is_boss else -24)
            self.fxm.add('foam', en['x'] + bx, en['y'] + by, life=1.3, r0=4 if is_boss else 3, r1=14 if is_boss else 10, col=(230, 245, 255))

    # ---- mapa
    def draw_map(self, cv):
        cx, cy = int(self.cam[0]), int(self.cam[1])
        self.draw_ocean(cv, cx, cy, self.t)
        cv.blit(self.land, (0, 0), area=pygame.Rect(cx, cy, W, H))
        self.war_draw(cv, cx, cy)
        for c in self.cities:
            surf = self.city_surf[c['name']][1 if c['dead'] else 0]
            sx, sy = c['x'] - cx, c['y'] - cy
            if -300 < sx < W + 300 and -300 < sy < H + 300:
                cv.blit(surf, (sx - surf.get_width() // 2, sy - surf.get_height() // 2))
                if not c['dead']:
                    self.text(cv, c['name'], self.f_s, (255, 255, 255), sx, sy - c['r'] * 0.75 - 38, 'c')
                    pygame.draw.rect(cv, (8, 12, 24), (sx - 32, sy - c['r'] * 0.75 - 16, 64, 7))
                    col = (80, 230, 110) if c['hp'] > 60 else ((255, 200, 70) if c['hp'] > 30 else (240, 80, 70))
                    pygame.draw.rect(cv, col, (sx - 31, sy - c['r'] * 0.75 - 15, int(62 * c['hp'] / 100), 5))
                    dx_, dy_ = c['dock'][0] - cx, c['dock'][1] - cy
                    pulse = 0.5 + 0.5 * math.sin(self.t * 3)
                    draw_circ(cv, dx_, dy_, 112 + pulse * 8, (120, 255, 200), 80, 2)
                    self.text(cv, 'PUERTO', self.f_s, (150, 255, 210), dx_, dy_ - 8, 'c')
                    lo = min(c['stock'].values())
                    self.text(cv, 'RESERVAS %d%%' % int(lo), self.f_s,
                              (110, 235, 130) if lo > 50 else ((255, 200, 70) if lo > 20 else (240, 80, 70)), dx_, dy_ + 10, 'c')
        px_, py_, pr_, _ps = ENEMY_PORT
        sx, sy = px_ - cx, py_ - cy
        if -200 < sx < W + 200 and -200 < sy < H + 200:
            done = self.port_done
            col = (120, 130, 140) if done else (255, 90, 80)
            pygame.draw.rect(cv, (96, 90, 100), (sx - 46, sy - 8, 92, 18), border_radius=3)
            for k in range(-1, 2):
                pygame.draw.rect(cv, (150, 70, 60) if not done else (110, 110, 116), (sx + k * 28 - 8, sy - 30, 16, 22))
            pygame.draw.line(cv, (210, 210, 220), (sx + 46, sy - 8), (sx + 46, sy - 50), 3)
            pygame.draw.line(cv, (210, 210, 220), (sx + 46, sy - 50), (sx + 8, sy - 38), 3)
            pygame.draw.line(cv, col, (sx - 40, sy - 8), (sx - 40, sy - 52), 2)
            pygame.draw.polygon(cv, col, [(sx - 40, sy - 52), (sx - 18, sy - 45), (sx - 40, sy - 38)])
            self.text(cv, 'PUERTO ENEMIGO - TOMADO' if done else 'PUERTO ENEMIGO (T)', self.f_s, (200, 205, 215) if done else (255, 170, 150),
                      sx, sy + pr_ * 0.95, 'c')
        for q in self.crates:
            sx, sy = q['x'] - cx, q['y'] - cy + math.sin(self.t * 2 + q['x']) * 3
            col = {'ammo': (255, 210, 70), 'fuel': (90, 230, 120), 'repair': (240, 240, 255)}[q['kind']]
            glow(cv, sx, sy, 34, col, 0.6)
            pygame.draw.rect(cv, (120, 84, 50), (sx - 11, sy - 11, 22, 22), border_radius=3)
            pygame.draw.rect(cv, col, (sx - 11, sy - 11, 22, 22), 2, border_radius=3)
            self.text(cv, {'ammo': 'M', 'fuel': 'C', 'repair': '+'}[q['kind']], self.f_s, (255, 255, 255), sx, sy - 9, 'c', shadow=False)
        for mc in self.mclouds:
            mx_ = (mc['x'] + self.t * 14) % (WORLD_W + 800) - 400
            my_ = (mc['y'] + self.t * 6) % (WORLD_H + 500) - 250
            w_, h_ = mc['spr'].get_size()
            if -w_ < mx_ - cx < W and -h_ < my_ - cy < H:
                cv.blit(mc['spr'], (mx_ - cx, my_ - cy))
        self.radar_draw_map(cv, cx, cy)
        for i in ANTENNA_ISLANDS:
            ix, iy, ir, _sd = EXTRA_ISLANDS[i]
            sx, sy = ix - cx, iy - cy
            if not (-200 < sx < W + 200 and -200 < sy < H + 200):
                continue
            if self.antennas[i]:
                cv.blit(self.antenna_gfx, (sx - 24, sy - 82))
                if int(self.t * 1.6) % 2 == 0:
                    glow(cv, sx, sy - 76, 18, (255, 70, 60))
                for j in range(3):
                    ph = (self.t * 0.7 + j / 3) % 1
                    draw_circ(cv, sx, sy - 76, 8 + ph * 50, (120, 240, 255), 150 * (1 - ph), 2)
                self.text(cv, self.isl_name(i) + ' - ANTENA', self.f_s, (150, 240, 255), sx, sy + ir * 0.95, 'c')
            else:
                pulse = 0.5 + 0.5 * math.sin(self.t * 3 + i)
                draw_circ(cv, sx, sy, 26 + pulse * 6, (255, 220, 90), 150, 2)
                pygame.draw.line(cv, (230, 230, 230), (sx, sy + 8), (sx, sy - 34), 2)
                pygame.draw.polygon(cv, (255, 210, 70), [(sx, sy - 34), (sx + 20, sy - 27), (sx, sy - 20)])
                left = MAX_LANDING_ATTEMPTS - self.landing_attempts[i]
                if i in self.cleared_isl:
                    left = -1
                self.text(cv, '%s - %s' % (self.isl_name(i), 'DESPEJADA: antena sin resistencia (L)' if left < 0 else ('DESEMBARCO (%d)' % left if left > 0 else 'SIN INTENTOS')),
                          self.f_s, (255, 230, 140) if left > 0 else (200, 120, 110), sx, sy + ir * 0.95, 'c')
        self.fxm.draw(cv, cx, cy)
        for nst in self.nests:
            if not nst['alive']:
                continue
            nx_, ny_ = nst['x'] - cx, nst['y'] - cy
            if -80 < nx_ < W + 80 and -80 < ny_ < H + 80:
                pygame.draw.circle(cv, (150, 130, 96), (int(nx_), int(ny_)), 17)
                pygame.draw.circle(cv, (90, 94, 100), (int(nx_), int(ny_)), 11)
                ex_, ey_ = vec(nst['ang'], 18)
                pygame.draw.line(cv, (60, 62, 68), (nx_, ny_), (nx_ + ex_, ny_ + ey_), 4)
                if nst['seen'] or self.radar_t > 0:
                    pul = 0.5 + 0.5 * math.sin(self.t * 4 + nst['x'])
                    draw_circ(cv, nx_, ny_, 330, (255, 80, 70), 22 + 24 * pul, 2)
                    self.text(cv, 'BATERÍA', self.f_s, (255, 150, 130), nx_, ny_ + 24, 'c')
        for en in self.enemies:
            if en.get('sub'):
                if dist(en['x'], en['y'], self.sx, self.sy) < 420 or self.radar_t > 0:
                    self.blit_ship(cv, 's_map', en['x'], en['y'], en['h'], cx, cy, alpha=120)
                    if en['state'] == 'chase':
                        draw_circ(cv, en['x'] - cx, en['y'] - cy, 44, (255, 80, 70), 120, 2)
                continue
            self.blit_ship(cv, ('b%d_map' % en.get('btype', 0)) if en.get('is_boss') else 'e_map', en['x'], en['y'], en['h'], cx, cy)
            if en['state'] == 'chase':
                draw_circ(cv, en['x'] - cx, en['y'] - cy, 44, (255, 80, 70), 120, 2)
            if en.get('shield'):
                sx_, sy_ = en['x'] - cx, en['y'] - cy
                pulse = 0.5 + 0.5 * math.sin(self.t * 3)
                draw_circ(cv, sx_, sy_, SHIELD_R, (255, 90, 220), 20 + 20 * pulse)
                draw_circ(cv, sx_, sy_, SHIELD_R, (255, 130, 235), 150 + 80 * pulse, 3)
                draw_circ(cv, sx_, sy_, SHIELD_R - 14, (160, 90, 255), 70, 1)
                self.text(cv, '%s %s' % (BOSS_TYPES[en.get('btype', 0)]['label'], en['name']), self.f_s, (255, 150, 235), sx_, sy_ + 78, 'c')
        self.draw_heli_map(cv, cx, cy)
        self.blit_ship(cv, 'p_map', self.sx, self.sy, self.sh, cx, cy)
        self.war_haze(cv)
        # HUD
        self.draw_hud(cv)
        self.draw_cities_hud(cv)
        self.draw_minimap(cv)
        if self.attack is not None:
            self.draw_attack(cv, cx, cy)
        yy = 92 if self.attack is not None else 8
        if self.rescue is not None:
            self.draw_rescue(cv, cx, cy, yy)
            yy += 52
        if self.convoy is not None:
            self.draw_convoy(cv, cx, cy, yy)
        thr = 1.0 if self.attack is not None else 1 - clamp(self.strike_t / 60.0, 0, 1)
        self.text(cv, 'AMENAZA ENEMIGA', self.f_s, (255, 190, 170), W - 296 + 8, 76)
        self.bar(cv, W - 296, 96, 282, 14, thr, (255, 90 + int(100 * (1 - thr)), 60), '')
        self.text(cv, 'BLACKHAWK: %d misión(es) | próxima a los %d pts | bidón (C): %s' % (
            self.heli_sorties, self.heli_next, 'en camino' if self.heli_fl else ('%ds' % math.ceil(self.heli_cd) if self.heli_cd > 0 else 'listo')),
            self.f_s, (130, 255, 190), 14, 96)
        n_ant = sum(self.antennas.values())
        need = self.antennas_needed()
        self.text(cv, 'ANTENAS %d/%d  (jefe: %d)' % (n_ant, len(self.antennas), need), self.f_s,
                  (130, 235, 255) if n_ant >= need else (255, 190, 120), W - 296 + 8, 116)
        nr = self.radars_done()
        self.text(cv, 'RADARES %d/%d  (L:%d P:%d)' % (nr, len(self.radars), LAND_RADARS, PORT_RADARS), self.f_s,
                  (130, 255, 190) if nr >= PORT_RADARS else ((255, 220, 120) if nr >= LAND_RADARS else (255, 150, 130)), W - 296 + 8, 136)
        bs = self.nearest_shield_boss()
        if bs:
            if n_ant < self.antennas_needed():
                self.text(cv, 'ESCUDO DEL JEFE: necesitás %d antenas (tenés %d) - desembarcá en las islas (L)' % (self.antennas_needed(), n_ant),
                          self.f_m, (255, 150, 235), W // 2, H - 176, 'c')
            elif bs['hack_cd'] > 0:
                self.text(cv, 'Sistemas enemigos reiniciando: %d s' % math.ceil(bs['hack_cd']), self.f_m, (255, 200, 120), W // 2, H - 176, 'c')
            else:
                self.text(cv, 'H: CIBERATAQUE al escudo del jefe (%d antena%s)' % (n_ant, '' if n_ant == 1 else 's'), self.f_m,
                          (130, 240, 255), W // 2, H - 176, 'c')
        dk = self.nearest_dock()
        if dk:
            st = dk['stock']
            if st['fuel'] < 1 and st['repair'] < 1 and st['ammo'] < 1:
                self.text(cv, '%s: suministros agotados hasta que se reponga' % dk['name'], self.f_m, (255, 170, 120), W // 2, H - 148, 'c')
            else:
                self.text(cv, 'PUERTO: mantené R para reabastecer  |  Combustible %d  Reparación %d  Munición %d' %
                          (st['fuel'], st['repair'], st['ammo']), self.f_m, (140, 255, 210), W // 2, H - 148, 'c')
        elif self.near_helipad(260) and self.heli_sorties > 0:
            self.text(cv, 'HELIPUERTO: presioná B para despegar en el BLACKHAWK (misiones: %d)' % self.heli_sorties,
                      self.f_m, (130, 255, 190), W // 2, H - 148, 'c')
        elif self.nearest_radar() is not None:
            self.text(cv, 'RADAR ENEMIGO: presioná H para hackearlo  |  1) nodos  2) señal de radio', self.f_m, (255, 190, 150), W // 2, H - 148, 'c')
        elif self.nearest_port():
            if self.invasion_locked(PORT_RADARS, 'Asalto', True):
                self.text(cv, 'PUERTO ENEMIGO BLOQUEADO: interceptá %d radares (tenés %d)' % (PORT_RADARS, self.radars_done()),
                          self.f_m, (255, 170, 120), W // 2, H - 148, 'c')
            else:
                self.text(cv, 'PUERTO ENEMIGO: presioná T para asaltarlo  |  Intentos: %d/2' % self.port_tries,
                          self.f_m, (255, 150, 120), W // 2, H - 148, 'c')
        else:
            island = self.nearest_landing_island()
            if island:
                island_idx, x, y, r, s = island
                attempts = self.landing_attempts[island_idx]
                if island_idx in self.cleared_isl:
                    self.text(cv, '%s DESPEJADA por el Blackhawk: presioná L para instalar la antena sin resistencia' % self.isl_name(island_idx),
                              self.f_m, (120, 255, 190), W // 2, H - 148, 'c')
                elif attempts >= MAX_LANDING_ATTEMPTS:
                    self.text(cv, '%s: sin intentos de desembarco' % self.isl_name(island_idx),
                              self.f_m, (255, 140, 110), W // 2, H - 148, 'c')
                elif self.invasion_locked(LAND_RADARS, 'Desembarco', True):
                    self.text(cv, '%s BLOQUEADA: interceptá %d radar enemigo para desembarcar (tenés %d)' % (self.isl_name(island_idx), LAND_RADARS, self.radars_done()),
                              self.f_m, (255, 170, 120), W // 2, H - 148, 'c')
                else:
                    self.text(cv, '%s CERCANA: presioná L para desembarcar (10 soldados enemigos)  |  Intentos: %d/%d' %
                              (self.isl_name(island_idx), attempts, MAX_LANDING_ATTEMPTS),
                              self.f_m, (100, 180, 255), W // 2, H - 148, 'c')
            elif self.fuel <= 0:
                self.text(cv, 'SIN COMBUSTIBLE - MOTOR AUXILIAR (lento)', self.f_m, (255, 90, 80), W // 2, H - 148, 'c')
        if self.warned and int(self.t * 4) % 2 == 0:
            pygame.draw.rect(cv, (255, 40, 40), (0, 0, W, H), 8)

    def draw_minimap(self, cv):
        mw, mh = 240, 180
        x0, y0 = W - mw - 14, H - mh - 14
        self.panel(cv, (x0 - 4, y0 - 4, mw + 8, mh + 8), 190)
        sc = mw / WORLD_W
        pygame.draw.rect(cv, (12, 40, 78), (x0, y0, mw, mh))
        for ix, iy, ir, _sd in self.islands:
            pygame.draw.circle(cv, (70, 120, 70), (int(x0 + ix * sc), int(y0 + iy * sc)), max(2, int(ir * sc * 1.1)))
        for c in self.cities:
            pygame.draw.rect(cv, (90, 90, 90) if c['dead'] else (255, 220, 80), (x0 + c['x'] * sc - 3, y0 + c['y'] * sc - 3, 6, 6))
            if self.attack is not None and self.attack['city'] is c and int(self.t * 4) % 2 == 0:
                pygame.draw.circle(cv, (255, 60, 50), (int(x0 + c['x'] * sc), int(y0 + c['y'] * sc)), 9, 2)
        for i in ANTENNA_ISLANDS:
            mx_, my_ = int(x0 + EXTRA_ISLANDS[i][0] * sc), int(y0 + EXTRA_ISLANDS[i][1] * sc)
            if self.antennas[i]:
                pygame.draw.polygon(cv, (120, 240, 255), [(mx_, my_ - 5), (mx_ + 4, my_ + 3), (mx_ - 4, my_ + 3)])
            else:
                pygame.draw.circle(cv, (255, 220, 90), (mx_, my_), 5, 1)
        self.radar_draw_mini(cv, x0, y0, sc)
        pygame.draw.rect(cv, (130, 255, 190), (int(x0 + HELIPAD[0] * sc) - 3, int(y0 + HELIPAD[1] * sc) - 3, 6, 6), 1)
        pygame.draw.rect(cv, (140, 140, 150) if self.port_done else (255, 90, 70), (int(x0 + ENEMY_PORT[0] * sc) - 4, int(y0 + ENEMY_PORT[1] * sc) - 4, 8, 8), 2)
        for nst in self.nests:
            if nst['alive'] and (nst['seen'] or self.radar_t > 0):
                pygame.draw.rect(cv, (255, 90, 70), (int(x0 + nst['x'] * sc) - 2, int(y0 + nst['y'] * sc) - 2, 5, 5))
        if self.attack is not None and self.attack['kind'] == 'antenna' and int(self.t * 4) % 2 == 0:
            ac = self.attack['city']
            pygame.draw.circle(cv, (255, 60, 50), (int(x0 + ac['x'] * sc), int(y0 + ac['y'] * sc)), 9, 2)
        if self.convoy is not None:
            pygame.draw.rect(cv, (120, 255, 190), (int(x0 + self.convoy['x'] * sc) - 3, int(y0 + self.convoy['y'] * sc) - 3, 6, 6))
        if self.rescue is not None and int(self.t * 3) % 2 == 0:
            pygame.draw.circle(cv, (255, 230, 90), (int(x0 + self.rescue['x'] * sc), int(y0 + self.rescue['y'] * sc)), 6, 2)
        for q in self.crates:
            pygame.draw.circle(cv, (120, 255, 255), (int(x0 + q['x'] * sc), int(y0 + q['y'] * sc)), 2)
        for en in self.enemies:
            if en.get('sub') and not (dist(en['x'], en['y'], self.sx, self.sy) < 420 or self.radar_t > 0):
                continue
            if dist(en['x'], en['y'], self.sx, self.sy) < 1100 or en.get('is_boss') or self.radar_t > 0:
                boss = en.get('is_boss')
                pygame.draw.circle(cv, (255, 90, 220) if boss else (255, 70, 60), (int(x0 + en['x'] * sc), int(y0 + en['y'] * sc)), 5 if boss else 3)
        pygame.draw.rect(cv, (255, 255, 255), (x0 + self.cam[0] * sc, y0 + self.cam[1] * sc, W * sc, H * sc), 1)
        pygame.draw.circle(cv, (80, 255, 255), (int(x0 + self.sx * sc), int(y0 + self.sy * sc)), 4)
        self.text(cv, 'RADAR', self.f_s, (150, 190, 230), x0 + 4, y0 + 2)
