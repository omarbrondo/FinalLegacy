"""Vidas: cuando se hunde tu buque (y te quedan más), huís en una lancha salvavidas hasta la ciudad más cercana.
Hay que llegar antes de que se acabe el tiempo esquivando ráfagas de ametralladora de lanchas rojas y de aviones.
Si la lancha cae o no llegás a tiempo, se acaba la partida. Cada LIFE_STEP puntos ganás una vida (hasta MAX_LIVES)."""
import math
import pygame
import random
from .common import H, W, bearing, clamp, dist, draw_circ, glow, vec

START_LIVES = 3
MAX_LIVES = 5
LIFE_STEP = 5000                      # puntos por cada vida extra
LB_NEED = 1.16                        # camino necesario / camino que hace el motor normal en el tiempo dado (hace falta forzar el motor)
LB_SPEED, LB_BOOST_SPEED = 215.0, 265.0
LB_RATE, LB_BOOST_RATE = 1.0, 1.8
LB_BULLET_DMG = 3.0
LB_INTRO = 2.4
PLAY_X0, PLAY_X1, PLAY_Y0, PLAY_Y1 = 60, W - 60, 190, H - 70


class LifeboatMixin:
    # ------------------------------------------------------------------ vidas
    def lives_reset(self):
        self.lives = START_LIVES
        self.next_life = LIFE_STEP

    def check_life(self):
        while self.score >= self.next_life:
            self.next_life += LIFE_STEP
            if self.lives < MAX_LIVES:
                self.lives += 1
                self.banner('¡VIDA EXTRA!', 'Buques disponibles: %d' % self.lives, (130, 255, 190), 3.0)
                self.audio.play('win', .6)

    def lose_ship(self, msg):
        """El buque se hundió: si quedan vidas, huís en la lancha; si no, fin de la partida."""
        if self.god or self.lives <= 1:
            return self.game_over(msg)
        self.lives -= 1
        self.lb_start()

    def draw_lives(self, cv, x, y):
        for i in range(self.lives):
            xx = x + i * 17
            pygame.draw.polygon(cv, (120, 215, 255), [(xx, y + 5), (xx + 4, y), (xx + 13, y), (xx + 16, y + 5), (xx + 12, y + 9), (xx + 3, y + 9)])
            pygame.draw.polygon(cv, (10, 20, 34), [(xx, y + 5), (xx + 4, y), (xx + 13, y), (xx + 16, y + 5), (xx + 12, y + 9), (xx + 3, y + 9)], 1)

    # ------------------------------------------------------------------ inicio
    def lb_start(self):
        alive = [c for c in self.cities if not c['dead']]
        city = min(alive, key=lambda c: dist(self.sx, self.sy, c['x'], c['y'])) if alive else self.cities[0]
        d = dist(self.sx, self.sy, city['x'], city['y'])
        T = clamp(38 + d / 90.0, 46.0, 76.0)
        self.warned, self.attack, self.strike_city = False, None, None
        ref = getattr(self, 'enemy_ref', None)
        if ref is not None and 'cool' in ref:
            ref['cool'] = max(ref['cool'], 20.0)
        self.lb = dict(city=city, T=T, t=0.0, p=0.0, x=W / 2 + 80.0, y=H - 150.0, vx=0.0, vy=0.0, hp=100.0, boost=100.0, boost_lock=False,
                       boosting=False, boats=[], planes=[], bullets=[], warns=[], boat_t=LB_INTRO + 3.5, plane_t=LB_INTRO + 7.0,
                       phase='sail', pt=0.0, hurt=0.0, wake=0.0, low_warned=False, skyline=self.lb_skyline(city))
        self.go('lifeboat')
        self.banners = []
        self.shake = 14
        self.audio.play('boom_l')
        self.banner('¡BUQUE HUNDIDO!', 'Huí en la lancha hasta %s antes de que se acabe el tiempo  |  Buques disponibles: %d' % (city['name'], self.lives),
                    (255, 110, 90), 4.4)

    def lb_skyline(self, city):
        rnd = random.Random(city['seed'] + 7)
        out, x = [], 0
        while x < 420:
            w = rnd.randint(22, 46)
            out.append((x, w, rnd.randint(34, 120)))
            x += w + rnd.randint(2, 6)
        return out

    # ------------------------------------------------------------------ disparos
    def lb_fire_bullet(self, x, y, spd, err):
        lb = self.lb
        T = dist(lb['x'], lb['y'], x, y) / spd
        ang = bearing(lb['x'] + lb['vx'] * T - x, lb['y'] + lb['vy'] * T - y) + random.uniform(-err, err)
        vx, vy = vec(ang, spd)
        lb['bullets'].append(dict(x=x, y=y, vx=vx, vy=vy, life=2.4, ang=ang))
        self.audio.play('mg', .12)

    # ------------------------------------------------------------------ actualización
    def upd_lifeboat(self, dt):
        lb = self.lb
        lb['t'] += dt
        lb['hurt'] = max(0.0, lb['hurt'] - dt)
        self.fxm.update(dt)
        w = self.wave
        phase = lb['phase']
        if phase in ('dead', 'late'):
            lb['pt'] += dt
            if random.random() < dt * 8:
                self.fx_burst(lb['x'] + random.uniform(-14, 14), lb['y'] + random.uniform(-14, 14))
            if lb['pt'] > 3.0:
                return self.game_over('Tu lancha salvavidas fue hundida' if phase == 'dead' else 'No llegaste a tiempo a la ciudad')
            return
        if phase == 'arrive':
            lb['pt'] += dt
            lb['x'] += (W / 2 - lb['x']) * min(1, dt * 1.5)
            lb['y'] -= 110 * dt
            lb['p'] = 1.0
            if lb['pt'] > 2.6:
                return self.lb_finish()
            self.lb_move_bullets(dt, harmless=True)
            return
        keys = pygame.key.get_pressed()
        playing = lb['t'] > LB_INTRO
        dx = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
        dy = (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0) - (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0)
        want = (keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or pygame.mouse.get_pressed()[0]) and playing
        if lb['boost_lock'] and lb['boost'] > 30:
            lb['boost_lock'] = False
        lb['boosting'] = bool(want) and lb['boost'] > 0 and not lb['boost_lock']
        if lb['boosting']:
            lb['boost'] = max(0.0, lb['boost'] - 38 * dt)
            if lb['boost'] <= 0:
                lb['boost_lock'] = True
        else:
            lb['boost'] = min(100.0, lb['boost'] + 14 * dt)
        sp = LB_BOOST_SPEED if lb['boosting'] else LB_SPEED
        n = math.hypot(dx, dy) or 1.0
        tx, ty = (dx / n * sp, dy / n * sp) if playing else (0.0, -30.0)
        lb['vx'] += (tx - lb['vx']) * min(1, dt * 7)
        lb['vy'] += (ty - lb['vy']) * min(1, dt * 7)
        lb['x'] = clamp(lb['x'] + lb['vx'] * dt, PLAY_X0, PLAY_X1)
        lb['y'] = clamp(lb['y'] + lb['vy'] * dt, PLAY_Y0, PLAY_Y1)
        if playing:
            lb['p'] += dt * (LB_BOOST_RATE if lb['boosting'] else LB_RATE) / (lb['T'] * LB_NEED)
        left = lb['T'] - max(0.0, lb['t'] - LB_INTRO)
        if playing and left <= 10 and not lb['low_warned']:
            lb['low_warned'] = True
            self.toast('¡Quedan 10 segundos! Forzá el motor (ESPACIO)', (255, 200, 110))
        lb['wake'] -= dt
        if lb['wake'] <= 0 and (abs(lb['vx']) + abs(lb['vy'])) > 30:
            lb['wake'] = 0.05
            self.fxm.add('foam', lb['x'] - lb['vx'] * 0.1, lb['y'] - lb['vy'] * 0.1 + 18, life=1.2, r0=4, r1=13, col=(235, 246, 255))
        # llegada o fin del tiempo
        if lb['p'] >= 1.0:
            lb['phase'], lb['pt'] = 'arrive', 0.0
            lb['boats'].clear()
            lb['planes'].clear()
            lb['warns'].clear()
            self.audio.play('win', .6)
            return
        if playing and left <= 0:
            lb['phase'], lb['pt'] = 'late', 0.0
            self.audio.play('lose')
            self.banner('SIN TIEMPO', 'La lancha no llegó a la ciudad', (255, 90, 80), 3.0)
            return
        # ataques (se detienen cerca de la costa)
        if playing and lb['p'] < 0.9:
            self.lb_spawn(dt, w)
        self.lb_update_boats(dt, w)
        self.lb_update_planes(dt, w)
        self.lb_move_bullets(dt)
        if lb['hp'] <= 0:
            lb['phase'], lb['pt'] = 'dead', 0.0
            self.fx_burst(lb['x'], lb['y'], True)
            self.audio.play('boom_l')
            self.shake = 14
            self.banner('LANCHA HUNDIDA', 'No hubo rescate', (255, 90, 80), 3.0)

    def fx_burst(self, x, y, big=False):
        self.fxm.add('glow', x, y, life=0.5, r0=10, r1=44 if big else 26, col=(255, 170, 80))
        self.fxm.add('smoke', x, y, random.uniform(-20, 20), -30, 1.4, 6, 22, (60, 60, 64))
        if big:
            self.fxm.add('ring', x, y, life=0.7, r0=10, r1=120, col=(255, 230, 190))

    def lb_spawn(self, dt, w):
        lb = self.lb
        lb['boat_t'] -= dt
        lb['plane_t'] -= dt
        if lb['boat_t'] <= 0 and len(lb['boats']) < 2:
            lb['boat_t'] = max(4.6, 7.2 - 0.35 * w) + random.uniform(0, 2.0)
            side = random.choice((-1, 1))
            lb['boats'].append(dict(x=-70.0 if side > 0 else W + 70.0, y=random.uniform(110, 330), vx=side * random.uniform(62, 88), side=side,
                                    cd=random.uniform(1.2, 2.0), burst=0, bt=0.0))
        if lb['plane_t'] <= 0 and not lb['planes'] and not lb['warns']:
            lb['plane_t'] = max(7.0, 10.5 - 0.4 * w) + random.uniform(0, 3.0)
            side = random.choice((-1, 1))
            lb['warns'].append(dict(side=side, y=clamp(lb['y'] + random.uniform(-150, 40), 130, H - 120), t=1.4))
            self.audio.play('alarm', .3)

    def lb_update_boats(self, dt, w):
        lb = self.lb
        for b in lb['boats'][:]:
            b['x'] += b['vx'] * dt
            if (b['vx'] > 0 and b['x'] > W + 90) or (b['vx'] < 0 and b['x'] < -90):
                lb['boats'].remove(b)
                continue
            if random.random() < dt * 14:
                self.fxm.add('foam', b['x'] - math.copysign(30, b['vx']), b['y'], life=1.2, r0=5, r1=15, col=(235, 246, 255))
            if lb['phase'] != 'sail':
                continue
            if b['burst'] > 0:
                b['bt'] -= dt
                if b['bt'] <= 0:
                    b['bt'] = 0.11
                    b['burst'] -= 1
                    self.lb_fire_bullet(b['x'], b['y'], 400.0, max(5.0, 8.5 - 0.35 * w))
            else:
                b['cd'] -= dt
                if b['cd'] <= 0 and 40 < b['x'] < W - 40:
                    b['cd'] = random.uniform(3.0, 4.2)
                    b['burst'], b['bt'] = 5, 0.0

    def lb_update_planes(self, dt, w):
        lb = self.lb
        for wn in lb['warns'][:]:
            wn['t'] -= dt
            if wn['t'] <= 0:
                lb['warns'].remove(wn)
                s = wn['side']
                lb['planes'].append(dict(x=-80.0 if s > 0 else W + 80.0, y=wn['y'], vx=520.0 * s, side=s, shots=0, burst=0, bt=0.0, nxt=random.uniform(0.9, 1.2) * 0.45))
        for pl in lb['planes'][:]:
            pl['x'] += pl['vx'] * dt
            if (pl['vx'] > 0 and pl['x'] > W + 120) or (pl['vx'] < 0 and pl['x'] < -120):
                lb['planes'].remove(pl)
                continue
            if random.random() < dt * 30:
                self.fxm.add('smoke', pl['x'] - math.copysign(24, pl['vx']), pl['y'], 0, 0, 0.5, 2, 7, (225, 225, 230))
            if lb['phase'] != 'sail':
                continue
            if pl['burst'] > 0:
                pl['bt'] -= dt
                if pl['bt'] <= 0:
                    pl['bt'] = 0.07
                    pl['burst'] -= 1
                    self.lb_fire_bullet(pl['x'], pl['y'], 470.0, max(4.5, 7.5 - 0.3 * w))
            elif pl['shots'] < 2 and 0 < pl['x'] < W and abs(pl['x'] - lb['x']) < (330 if pl['shots'] == 0 else 140) \
                    and (pl['vx'] > 0) == (pl['x'] < lb['x'] + 330):
                pl['shots'] += 1
                pl['burst'], pl['bt'] = 6, 0.0

    def lb_move_bullets(self, dt, harmless=False):
        lb = self.lb
        for b in lb['bullets'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if b['life'] <= 0 or not (-60 < b['x'] < W + 60 and -60 < b['y'] < H + 60):
                lb['bullets'].remove(b)
                continue
            if harmless:
                continue
            if dist(b['x'], b['y'], lb['x'], lb['y']) < 17 and lb['phase'] == 'sail':
                lb['bullets'].remove(b)
                lb['hp'] -= LB_BULLET_DMG
                lb['hurt'] = 0.25
                self.shake = max(self.shake, 5)
                self.fxm.add('spark', b['x'], b['y'], random.uniform(-100, 100), random.uniform(-100, 100), 0.3, col=(255, 220, 140), drag=2)
                self.audio.play('hit', .35)
                self.pop('-%d' % LB_BULLET_DMG, lb['x'], lb['y'] - 22, (255, 110, 100))

    # ------------------------------------------------------------------ rescate
    def lb_finish(self):
        city = self.lb['city']
        self.sx, self.sy = city['dock']
        self.sh, self.sv = 0.0, 0.0
        self.hull, self.fuel = float(self.hull_max), 100.0
        self.ammo = max(self.ammo, 25)
        self.cam = [self.sx - W / 2, self.sy - H / 2]
        self.crash_t = 0.0
        self.fxm = type(self.fxm)()
        self.autosave(False)
        self.go('map')
        self.banner('¡RESCATADO EN %s!' % city['name'].upper(), 'Nuevo buque listo  |  Buques disponibles: %d' % self.lives, (130, 255, 190), 3.6)
        self.audio.play('win', .7)

    # ------------------------------------------------------------------ dibujo
    def lb_sprites(self):
        if getattr(self, '_lb_spr', None) is None:
            s = pygame.Surface((30, 58), pygame.SRCALPHA)
            hull = [(15, 2), (24, 14), (26, 44), (20, 56), (10, 56), (4, 44), (6, 14)]
            pygame.draw.polygon(s, (240, 130, 40), hull)
            pygame.draw.polygon(s, (250, 245, 235), [(15, 8), (21, 18), (22, 42), (8, 42), (9, 18)])
            pygame.draw.polygon(s, (30, 40, 56), hull, 2)
            pygame.draw.rect(s, (240, 130, 40), (11, 22, 8, 14), border_radius=2)
            for i, yy in enumerate((26, 34, 42)):
                pygame.draw.circle(s, (232, 190, 150), (15 + (i % 2) * 4 - 2, yy), 3)
            self._lb_spr = s
            if not self.ships.get('g_boat'):
                for key, src, k in (('g_boat', 'e_map', 1.55), ('a_ally', 'p_map', 1.5)):
                    sf, sh = self.ships[src]
                    self.ships[key] = (pygame.transform.rotozoom(sf, 0, k).convert_alpha(), pygame.transform.rotozoom(sh, 0, k).convert_alpha())
        return self._lb_spr

    def draw_lifeboat(self, cv):
        lb = self.lb
        t = self.t
        spr = self.lb_sprites()
        self.draw_ocean(cv, 0, -lb['t'] * 70 * (1.6 if lb['boosting'] else 1.0), t)
        # costa de la ciudad
        if lb['p'] > 0.72:
            k = clamp((lb['p'] - 0.72) / 0.28, 0, 1)
            base = -160 + 330 * k
            pygame.draw.rect(cv, (196, 178, 128), (0, base - 190, W, 190 + 26))
            pygame.draw.rect(cv, (170, 150, 104), (0, base + 10, W, 16))
            for i in range(0, W, 38):
                draw_circ(cv, i + (t * 20) % 38, base + 28, 14, (240, 250, 255), 90)
            x0 = (W - 420) // 2
            for bx, bw, bh in lb['skyline']:
                col = (88, 100, 124)
                pygame.draw.rect(cv, col, (x0 + bx, base - bh, bw, bh))
                pygame.draw.rect(cv, (60, 70, 92), (x0 + bx, base - bh, bw, bh), 2)
                for wy in range(int(base - bh + 8), int(base - 6), 14):
                    for wx in range(x0 + bx + 5, x0 + bx + bw - 6, 11):
                        pygame.draw.rect(cv, (255, 226, 140) if (wx + wy) % 3 else (60, 70, 92), (wx, wy, 5, 7))
            self.text(cv, lb['city']['name'], self.f_l, (255, 255, 255), W // 2, base + 34, 'c')
        # hundimiento del buque en la introducción
        if lb['t'] < LB_INTRO + 1.2:
            k = clamp(lb['t'] / (LB_INTRO + 1.0), 0, 1)
            self.blit_ship(cv, 'p_map', W / 2 - 40, H - 120 + 40 * k, 8 + 40 * k, alpha=int(255 * (1 - k)))
            glow(cv, W / 2 - 40, H - 120 + 40 * k, 60 * (1 - 0.5 * k), (255, 140, 50), 0.7 * (1 - k))
            if random.random() < 0.5:
                self.fxm.add('smoke', W / 2 - 40 + random.uniform(-20, 20), H - 120, random.uniform(-10, 10), -40, 2.0, 6, 26, (40, 40, 44))
        self.fxm.draw(cv)
        # avisos de avión
        for wn in lb['warns']:
            x = 40 if wn['side'] > 0 else W - 40
            if int(t * 8) % 2 == 0:
                pygame.draw.line(cv, (255, 80, 70), (0, wn['y']), (W, wn['y']), 2)
                pygame.draw.polygon(cv, (255, 210, 70), [(x, wn['y'] - 22), (x - 18, wn['y'] + 10), (x + 18, wn['y'] + 10)])
                self.text(cv, '!', self.f_m, (40, 30, 24), x, wn['y'] - 14, 'c', shadow=False)
        # lanchas enemigas
        for b in lb['boats']:
            self.blit_ship(cv, 'g_boat', b['x'], b['y'], 90 if b['vx'] > 0 else 270)
            if b['burst'] > 0:
                glow(cv, b['x'] + math.copysign(10, b['vx']), b['y'], 14, (255, 220, 140), 0.9)
        # aviones
        for pl in lb['planes']:
            d = 1 if pl['vx'] > 0 else -1
            pts = [(pl['x'] + d * 30, pl['y']), (pl['x'] - d * 18, pl['y'] - 26), (pl['x'] - d * 8, pl['y']), (pl['x'] - d * 18, pl['y'] + 26)]
            draw_circ(cv, pl['x'] + 12, pl['y'] + 20, 24, (0, 0, 0), 55)
            pygame.draw.polygon(cv, (46, 52, 62), pts)
            pygame.draw.polygon(cv, (210, 216, 226), pts, 2)
            glow(cv, pl['x'] - d * 24, pl['y'], 12, (255, 170, 80), 0.7)
            if pl['burst'] > 0:
                glow(cv, pl['x'] + d * 32, pl['y'], 14, (255, 220, 140), 0.9)
        # balas trazadoras
        for b in lb['bullets']:
            pygame.draw.line(cv, (255, 235, 140), (b['x'], b['y']), (b['x'] - b['vx'] * 0.035, b['y'] - b['vy'] * 0.035), 3)
            pygame.draw.circle(cv, (255, 120, 80), (int(b['x']), int(b['y'])), 3)
        # lancha salvavidas
        if lb['phase'] != 'dead' or lb['pt'] < 0.15:
            ang = bearing(lb['vx'], lb['vy'] - 1) if (abs(lb['vx']) + abs(lb['vy'])) > 8 else 0.0
            ang = clamp(((ang + 180) % 360) - 180, -35, 35)
            r = pygame.transform.rotate(spr, -ang)
            draw_circ(cv, lb['x'] + 5, lb['y'] + 7, 20, (0, 0, 0), 60)
            cv.blit(r, (lb['x'] - r.get_width() // 2, lb['y'] - r.get_height() // 2))
            if lb['hurt'] > 0:
                glow(cv, lb['x'], lb['y'], 30, (255, 80, 60), 0.7)
            if lb['boosting']:
                glow(cv, lb['x'], lb['y'] + 28, 26, (140, 210, 255), 0.8)
        # HUD
        if lb['hurt'] > 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.rect(ov, (255, 40, 30, int(120 * lb['hurt'] / 0.25)), (0, 0, W, H), 14)
            cv.blit(ov, (0, 0))
        self.panel(cv, (W // 2 - 260, 12, 520, 76), 170)
        left = max(0.0, lb['T'] - max(0.0, lb['t'] - LB_INTRO))
        col = (255, 90, 80) if left < 10 else (255, 235, 150)
        self.text(cv, 'RUMBO A %s' % lb['city']['name'].upper(), self.f_m, (160, 220, 255), W // 2 - 244, 18)
        self.text(cv, '%d:%02d' % (int(left) // 60, int(left) % 60), self.f_m, col, W // 2 + 244, 18, 'r')
        pygame.draw.rect(cv, (8, 12, 24), (W // 2 - 244, 52, 488, 20), border_radius=4)
        pygame.draw.rect(cv, (255, 160, 60), (W // 2 - 243, 53, int(486 * clamp(lb['p'], 0, 1)), 18), border_radius=4)
        mx = W // 2 - 243 + int(486 * clamp(lb['p'], 0, 1))
        pygame.draw.polygon(cv, (255, 255, 255), [(mx, 50), (mx - 6, 40), (mx + 6, 40)])
        self.panel(cv, (14, H - 96, 330, 82), 160)
        self.bar(cv, 26, H - 86, 306, 24, lb['hp'] / 100.0, (80, 220, 110) if lb['hp'] > 35 else (240, 80, 70), 'LANCHA %d%%' % max(0, lb['hp']))
        bcol = (255, 120, 80) if lb['boost_lock'] else (140, 210, 255)
        self.bar(cv, 26, H - 56, 306, 24, lb['boost'] / 100.0, bcol, 'MOTOR A FONDO' if not lb['boost_lock'] else 'MOTOR RECALENTADO')
        self.panel(cv, (W - 190, H - 52, 176, 38), 160)
        self.text(cv, 'BUQUES', self.f_s, (170, 200, 235), W - 182, H - 44)
        self.draw_lives(cv, W - 112, H - 42)
        if lb['t'] > LB_INTRO and lb['phase'] == 'sail':
            self.text(cv, 'WASD mover  |  ESPACIO / SHIFT / clic: motor a fondo (avanzás más rápido)  |  esquivá las ráfagas', self.f_s, (200, 220, 255), W // 2, H - 26, 'c')
