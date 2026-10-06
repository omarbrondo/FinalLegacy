"""Vidas: cuando se hunde tu buque (y te quedan más), huís en una lancha salvavidas hasta la ciudad más cercana.
Hay que llegar antes de que se acabe el tiempo esquivando ráfagas de ametralladora de lanchas rojas y de aviones.
Si la lancha cae o no llegás a tiempo, se acaba la partida. Cada LIFE_STEP puntos ganás una vida (hasta MAX_LIVES)."""
import math
import pygame
import random
from .common import H, W, bearing, clamp, dist, vec
from .lifeboat_art import LB_INTRO_DRAW, PLANE_KEYS, LifeboatArtMixin

START_LIVES = 3
MAX_LIVES = 5
LIFE_STEP = 5000                      # puntos por cada vida extra
LB_NEED = 1.16                        # camino necesario / camino que hace el motor normal en el tiempo dado (hace falta forzar el motor)
LB_SPEED, LB_BOOST_SPEED = 215.0, 265.0
LB_RATE, LB_BOOST_RATE = 1.0, 1.8
LB_BULLET_DMG = 3.0
LB_INTRO = LB_INTRO_DRAW
PLAY_Y0, PLAY_Y1 = 190, H - 70
LB_SCROLL = 70.0                      # velocidad de desplazamiento de las orillas
REEF_DMG = 8.0


class LifeboatMixin(LifeboatArtMixin):
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
                       phase='sail', pt=0.0, hurt=0.0, wake=0.0, low_warned=False, scroll=0.0, reefs=[],
                       reef_t=LB_INTRO + 4.5, bank_k=1.0, dock_y=322.0)
        self.go('lifeboat')
        self.banners = []
        self.shake = 14
        self.audio.play('boom_l')
        self.banner('¡BUQUE HUNDIDO!', 'Llegá a %s en la lancha antes de que se acabe el tiempo' % city['name'],
                    (255, 110, 90), 4.4)

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
            lb['x'] += (W / 2 - lb['x']) * min(1, dt * 1.6)
            lb['y'] += (lb['dock_y'] + 36 - lb['y']) * min(1, dt * 1.6)
            lb['vx'], lb['vy'] = 0.0, -20.0
            lb['scroll'] += LB_SCROLL * 0.3 * dt
            lb['p'] = 1.0
            if lb['pt'] > 3.0:
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
        lb['bank_k'] = 1.0 - 0.88 * clamp((lb['p'] - 0.7) / 0.3, 0, 1)
        lb['scroll'] += LB_SCROLL * (1.7 if lb['boosting'] else 1.0) * (1.0 if playing else 0.5) * dt
        lb['y'] = clamp(lb['y'] + lb['vy'] * dt, PLAY_Y0, PLAY_Y1)
        lo, hi = self.lb_channel(lb['y'])
        lb['x'] = clamp(lb['x'] + lb['vx'] * dt, lo + 30, hi - 30)
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
        self.lb_update_reefs(dt, playing)
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
            lb['warns'].append(dict(side=side, y=clamp(lb['y'] + random.uniform(-150, 40), 130, H - 120), t=1.4, key=random.choice(PLANE_KEYS)))
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

    def lb_update_reefs(self, dt, playing):
        lb = self.lb
        spd = LB_SCROLL * (1.7 if lb['boosting'] else 1.0)
        if playing and lb['p'] < 0.86:
            lb['reef_t'] -= dt
            if lb['reef_t'] <= 0:
                lb['reef_t'] = random.uniform(2.6, 4.0)
                lo, hi = self.lb_channel(-30)
                lb['reefs'].append(dict(x=random.uniform(lo + 44, hi - 44), y=-34.0))
        for rf in lb['reefs'][:]:
            rf['y'] += spd * dt
            if rf['y'] > H + 50:
                lb['reefs'].remove(rf)
            elif lb['phase'] == 'sail' and dist(rf['x'], rf['y'], lb['x'], lb['y']) < 26:
                lb['reefs'].remove(rf)
                lb['hp'] -= REEF_DMG
                lb['hurt'] = 0.25
                lb['vx'] *= 0.3
                lb['vy'] *= 0.3
                self.shake = max(self.shake, 8)
                self.fxm.splash(rf['x'], rf['y'], 1.3)
                self.audio.play('hit', .5)
                self.pop('ARRECIFE -%d' % REEF_DMG, lb['x'], lb['y'] - 26, (255, 150, 100))

    def lb_update_planes(self, dt, w):
        lb = self.lb
        for wn in lb['warns'][:]:
            wn['t'] -= dt
            if wn['t'] <= 0:
                lb['warns'].remove(wn)
                s = wn['side']
                lb['planes'].append(dict(x=-80.0 if s > 0 else W + 80.0, y=wn['y'], vx=520.0 * s, side=s, key=wn['key'], shots=0, burst=0, bt=0.0, nxt=random.uniform(0.9, 1.2) * 0.45))
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
