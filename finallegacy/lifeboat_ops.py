"""Huida en lancha: disparo en ráfagas cortas (mouse), minas flotantes, powerups (reparación, nitro, escudo) y choques de las lanchas enemigas."""
import math
import pygame
import random
from .common import H, W, bearing, dist, vec

LB_SHOT_SPD = 640.0
LB_BURST_N = 3                         # balas por ráfaga
LB_BURST_GAP = 0.07
LB_SHOT_CD = 0.9                       # pausa entre ráfagas
LB_SHOT_DMG = 1.0
LB_BOAT_HP = 5.0
MINE_DMG = 14.0
PUP_KINDS = ('repair', 'nitro', 'shield')
NITRO_T = 5.0
SHIELD_HITS = 3
SCORE_BOAT = 150


class LifeboatOpsMixin:
    def lb_ops_init(self):
        return dict(mines=[], pups=[], pshots=[], mine_t=7.0, pup_t=8.0, fire_cd=0.0, burst=0, burst_t=0.0, shield=0, nitro=0.0)

    # ------------------------------------------------------------------ daño con escudo
    def lb_hurt(self, dmg, x, y, label):
        lb = self.lb
        if lb['phase'] != 'sail':
            return False
        if lb['shield'] > 0:
            lb['shield'] -= 1
            self.fxm.add('ring', lb['x'], lb['y'], life=0.4, r0=14, r1=44, col=(130, 230, 255))
            self.audio.play('ping', .4)
            self.pop('ESCUDO', lb['x'], lb['y'] - 26, (140, 230, 255))
            return False
        lb['hp'] -= dmg
        lb['hurt'] = 0.25
        self.shake = max(self.shake, 5 if dmg < 8 else 9)
        self.pop('%s -%d' % (label, dmg) if label else '-%d' % dmg, lb['x'], lb['y'] - 24, (255, 120, 100))
        return True

    # ------------------------------------------------------------------ actualización
    def lb_ops_update(self, dt, playing):
        lb = self.lb
        spd = 70.0 * (1.7 if lb['boosting'] else 1.0)
        # --- aparición de minas y powerups (se desplazan con las orillas)
        if playing and lb['p'] < 0.86:
            lb['mine_t'] -= dt
            if lb['mine_t'] <= 0:
                lb['mine_t'] = random.uniform(4.2, 6.5)
                lo, hi = self.lb_channel(-30)
                lb['mines'].append(dict(x=random.uniform(lo + 50, hi - 50), y=-34.0, ph=random.uniform(0, 6.28)))
            lb['pup_t'] -= dt
            if lb['pup_t'] <= 0:
                lb['pup_t'] = random.uniform(7.0, 11.0)
                lo, hi = self.lb_channel(-30)
                lb['pups'].append(dict(x=random.uniform(lo + 50, hi - 50), y=-30.0, kind=random.choice(PUP_KINDS), ph=random.uniform(0, 6.28)))
        sailing = lb['phase'] == 'sail'
        for m in lb['mines'][:]:
            m['y'] += spd * dt
            m['x'] += math.sin(self.t * 1.6 + m['ph']) * 14 * dt
            if m['y'] > H + 50:
                lb['mines'].remove(m)
            elif sailing and dist(m['x'], m['y'], lb['x'], lb['y']) < 24:
                lb['mines'].remove(m)
                self.lb_mine_blast(m, True)
        for u in lb['pups'][:]:
            u['y'] += spd * dt
            if u['y'] > H + 50:
                lb['pups'].remove(u)
            elif sailing and dist(u['x'], u['y'], lb['x'], lb['y']) < 30:
                lb['pups'].remove(u)
                self.lb_take_pup(u)
        if lb['nitro'] > 0:
            lb['nitro'] = max(0.0, lb['nitro'] - dt)
        # --- disparo en ráfagas cortas con el mouse (o F)
        keys = pygame.key.get_pressed()
        fire = (pygame.mouse.get_pressed()[0] or keys[pygame.K_f]) and playing and sailing
        lb['fire_cd'] = max(0.0, lb['fire_cd'] - dt)
        if fire and lb['fire_cd'] <= 0 and lb['burst'] == 0:
            lb['burst'], lb['burst_t'] = LB_BURST_N, 0.0
            lb['fire_cd'] = LB_SHOT_CD
        if lb['burst'] > 0:
            lb['burst_t'] -= dt
            if lb['burst_t'] <= 0:
                lb['burst_t'] = LB_BURST_GAP
                lb['burst'] -= 1
                self.lb_shoot()
        self.lb_update_shots(dt)
        self.lb_boat_crashes()

    def lb_aim_angle(self):
        lb = self.lb
        ax, ay = self.aim
        if not self.mouse_moved or dist(ax, ay, lb['x'], lb['y']) < 30:
            return 0.0
        return bearing(ax - lb['x'], ay - lb['y'])

    def lb_shoot(self):
        lb = self.lb
        ang = self.lb_aim_angle() + random.uniform(-1.5, 1.5)
        ox, oy = vec(ang, 30)
        vx, vy = vec(ang, LB_SHOT_SPD)
        lb['pshots'].append(dict(x=lb['x'] + ox, y=lb['y'] + oy, vx=vx, vy=vy, life=1.1, ang=ang))
        self.audio.play('mg', .25)
        self.fxm.add('glow', lb['x'] + ox, lb['y'] + oy, life=.12, r0=6, r1=18, col=(255, 230, 150))

    def lb_update_shots(self, dt):
        lb = self.lb
        for s in lb['pshots'][:]:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['life'] -= dt
            if s['life'] <= 0 or not (-40 < s['x'] < W + 40 and -40 < s['y'] < H + 40):
                lb['pshots'].remove(s)
                continue
            hit = False
            for b in lb['boats'][:]:
                if dist(s['x'], s['y'], b['x'], b['y']) < 30:
                    b['hp'] -= LB_SHOT_DMG
                    hit = True
                    self.fxm.add('spark', s['x'], s['y'], random.uniform(-110, 110), random.uniform(-110, 110), 0.3, col=(255, 210, 120), drag=2)
                    self.audio.play('hit', .25)
                    if b['hp'] <= 0:
                        self.lb_boat_down(b, True)
                    break
            if not hit:
                for m in lb['mines'][:]:
                    if dist(s['x'], s['y'], m['x'], m['y']) < 20:
                        lb['mines'].remove(m)
                        self.lb_mine_blast(m, False)
                        hit = True
                        break
            if not hit:
                for rf in lb['reefs']:
                    if dist(s['x'], s['y'], rf['x'], rf['y']) < 20:
                        self.fxm.add('spark', s['x'], s['y'], random.uniform(-60, 60), random.uniform(-60, 60), 0.25, col=(200, 200, 200), drag=2)
                        hit = True
                        break
            if hit:
                lb['pshots'].remove(s)

    def lb_boat_down(self, b, by_player):
        lb = self.lb
        if b in lb['boats']:
            lb['boats'].remove(b)
        self.fxm.explode(b['x'], b['y'], 1.4, True)
        self.audio.play('boom_s', .6)
        self.shake = max(self.shake, 5)
        if by_player:
            self.add_score(SCORE_BOAT)
            self.pop('+%d' % SCORE_BOAT, b['x'], b['y'] - 20, (255, 255, 160))
            self.toast('¡Lancha enemiga hundida!', (255, 230, 130))

    def lb_boat_crashes(self):
        """Las lanchas enemigas chocan contra arrecifes y minas: se destruyen."""
        lb = self.lb
        for b in lb['boats'][:]:
            for rf in lb['reefs']:
                if dist(b['x'], b['y'], rf['x'], rf['y']) < 36:
                    self.fxm.splash(rf['x'], rf['y'], 1.4)
                    self.lb_boat_down(b, False)
                    self.pop('¡CHOCÓ!', b['x'], b['y'] - 24, (255, 200, 120))
                    break
            else:
                for m in lb['mines']:
                    if dist(b['x'], b['y'], m['x'], m['y']) < 34:
                        lb['mines'].remove(m)
                        self.lb_mine_blast(m, False)
                        self.lb_boat_down(b, False)
                        break

    def lb_mine_blast(self, m, hit_player):
        lb = self.lb
        self.fxm.explode(m['x'], m['y'], 1.6, True)
        self.fxm.splash(m['x'], m['y'], 1.6)
        self.audio.play('boom_s', .7)
        self.shake = max(self.shake, 7)
        for b in lb['boats'][:]:                                      # la onda expansiva alcanza a las lanchas enemigas
            if dist(b['x'], b['y'], m['x'], m['y']) < 70:
                b['hp'] -= 3.0
                if b['hp'] <= 0:
                    self.lb_boat_down(b, not hit_player)
        if hit_player:
            if self.lb_hurt(MINE_DMG, m['x'], m['y'], 'MINA'):
                lb['vx'] *= 0.2
                lb['vy'] *= 0.2
        elif lb['phase'] == 'sail' and dist(m['x'], m['y'], lb['x'], lb['y']) < 56:
            self.lb_hurt(MINE_DMG * 0.5, m['x'], m['y'], 'ONDA')

    def lb_take_pup(self, u):
        lb = self.lb
        self.audio.play('ping', .6)
        k = u['kind']
        if k == 'repair':
            lb['hp'] = min(100.0, lb['hp'] + 30)
            self.pop('+30 SALUD', lb['x'], lb['y'] - 26, (130, 255, 160))
        elif k == 'nitro':
            lb['nitro'] = NITRO_T
            lb['boost'] = 100.0
            lb['boost_lock'] = False
            self.pop('¡NITRO!', lb['x'], lb['y'] - 26, (140, 210, 255))
        else:
            lb['shield'] = SHIELD_HITS
            self.pop('ESCUDO x%d' % SHIELD_HITS, lb['x'], lb['y'] - 26, (140, 230, 255))
        self.fxm.add('ring', lb['x'], lb['y'], life=0.5, r0=10, r1=54, col=(255, 255, 255))
