"""Batalla aérea: jefes aéreos (uno por oleada), clima de cada oleada y misiles teledirigidos."""
import math
import pygame
import random
from .common import H, W, angle_diff, bearing, clamp, dist, draw_circ, glow, vec
from .air_art import ENG, make_air_boss, make_pod_turret

# nombre, aviso, multiplicador de vida, radio de impacto
AIR_BOSSES = [
    dict(name='COMANDANTE STEALTH', hint='Destruí al bombardero furtivo', hp=1.0, r=80),
    dict(name='NODRIZA TIFÓN', hint='Lanza drones kamikaze: derribalos antes de que te alcancen', hp=1.1, r=105),
    dict(name='FANTASMA', hint='Se vuelve invisible e invulnerable: dispará cuando reaparece', hp=0.9, r=72),
    dict(name='ARTILLERO PESADO', hint='Bombardeo en hileras: pasá por los huecos', hp=1.2, r=100),
    dict(name='TORMENTA', hint='Rayos verticales con aviso: salí de la línea', hp=1.0, r=88),
    dict(name='TITÁN AÉREO', hint='Destruí primero las dos torretas laterales: el núcleo está blindado', hp=1.4, r=110),
]
# tinte, (r, g, b, alpha) de cada oleada
AIR_AMBIENT = [None, (255, 150, 70, 44), (18, 26, 48, 105), (6, 10, 34, 125), (230, 70, 44, 56), (60, 0, 22, 100)]


class AirBossMixin:
    # ---------------------------------------------------------- jefes aéreos
    def air_kind(self):
        return (self.wave - 1) % len(AIR_BOSSES)

    def air_boss_make(self):
        k = self.air_kind()
        spec = AIR_BOSSES[k]
        hp = (80 + 20 * self.wave) * spec['hp']
        b = dict(k=k, x=W / 2, y=-190.0, hp=float(hp), max=float(hp), t=0.0, hit=0.0, pc=2.0, pi=0, stream=0, sd=0.0, wc=1.2,
                 r=spec['r'], dc=3.0, rc=3.0, bc=3.5, beams=[], cloak='vis', ct=4.0, tx=W / 2, alpha=1.0, ring=0.0, pods=[])
        if k == 5:
            ph = 30 + 8 * self.wave
            b['pods'] = [dict(ox=sd * 135, oy=34, hp=float(ph), max=float(ph), cd=1.0, hit=0.0) for sd in (-1, 1)]
        if k > 0 and 'spr' not in self.air:
            self.air['spr'] = {}
        if k > 0 and k not in self.air['spr']:
            self.air['spr'][k] = make_air_boss(k)
        return b

    def air_boss_sprite(self, b):
        return self.air['boss'] if b['k'] == 0 else self.air['spr'][b['k']]

    def air_boss_invulnerable(self, b):
        if b['k'] == 2 and b['alpha'] < 0.5:
            return True
        return b['k'] == 5 and any(p_['hp'] > 0 for p_ in b['pods'])

    def air_boss_hit(self, bl):
        """Una bala del jugador toca al jefe. Devuelve True si la bala se consume."""
        a = self.a
        b = a['boss']
        dmg = bl.get('dmg', 1)
        if b['k'] == 5:
            for pod in b['pods']:
                if pod['hp'] > 0 and dist(bl['x'], bl['y'], b['x'] + pod['ox'], b['y'] + pod['oy']) < 46:
                    pod['hp'] -= dmg
                    pod['hit'] = 0.08
                    if pod['hp'] <= 0:
                        self.air_boom(b['x'] + pod['ox'], b['y'] + pod['oy'], 1.8, True, 'boom_l')
                        self.add_score(1000)
                        self.pop('+1000', b['x'] + pod['ox'], b['y'] + pod['oy'] - 30, (255, 230, 120))
                        if not any(p_['hp'] > 0 for p_ in b['pods']):
                            self.toast('¡Torretas destruidas! El núcleo quedó expuesto', (255, 220, 120))
                            self.say('piloto', '¡Torretas fuera! El núcleo quedó expuesto, ¡dale con todo!', 'ok')
                    return True
        if dist(bl['x'], bl['y'], b['x'], b['y'] + 10) < b['r']:
            if b['k'] == 2 and b['alpha'] < 0.5:
                return False
            if self.air_boss_invulnerable(b):
                self.fx.add('spark', bl['x'], bl['y'], random.uniform(-120, 120), random.uniform(-120, 0), 0.3, col=(180, 220, 255), drag=2)
                return True
            b['hp'] -= dmg
            b['hit'] = 0.08
            self.fx.add('spark', bl['x'], bl['y'], random.uniform(-100, 100), random.uniform(-60, 60), 0.2, col=(255, 230, 150), drag=2)
            return True
        return False

    def air_boss_update(self, dt):
        a = self.a
        p = a['p']
        b = a['boss']
        k = b['k']
        b['t'] += dt
        b['hit'] = max(0.0, b['hit'] - dt)
        for pod in b['pods']:
            pod['hit'] = max(0.0, pod['hit'] - dt)
        if b['y'] < 175:
            b['y'] += 80 * dt
            return
        rage = b['hp'] < b['max'] * 0.5
        alive_p = not p['dead']
        aim = bearing(p['x'] - b['x'], p['y'] - b['y'])
        if k == 0:
            b['x'] = W / 2 + math.sin(b['t'] * 0.55) * (W / 2 - 230)
            b['pc'] -= dt
            if b['pc'] <= 0 and alive_p:
                pat = b['pi'] % 3
                b['pi'] += 1
                b['pc'] = 1.7 if rage else 2.5
                if pat == 0:
                    for i in range(-3, 4):
                        self.air_ebul(b['x'], b['y'] + 60, aim + i * 11, 215)
                elif pat == 1:
                    off = random.uniform(0, 360)
                    for i in range(20 if rage else 16):
                        self.air_ebul(b['x'], b['y'] + 20, off + i * (360 / (20 if rage else 16)), 150, 6)
                else:
                    b['stream'], b['sd'] = 12 if rage else 9, 0.0
            if b['stream'] > 0:
                b['sd'] -= dt
                if b['sd'] <= 0 and alive_p:
                    b['stream'] -= 1
                    b['sd'] = 0.08
                    self.air_ebul(b['x'], b['y'] + 50, bearing(p['x'] - b['x'], p['y'] - b['y']) + random.uniform(-2, 2), 270)
            b['wc'] -= dt
            if b['wc'] <= 0 and alive_p:
                b['wc'] = 1.2 if rage else 1.8
                for sx in (-1, 1):
                    self.air_ebul(b['x'] + sx * 110, b['y'] + 30, bearing(p['x'] - b['x'] - sx * 110, p['y'] - b['y'] - 30), 230)
        elif k == 1:                                   # nodriza: drones kamikaze
            b['x'] = W / 2 + math.sin(b['t'] * 0.4) * (W / 2 - 190)
            b['dc'] -= dt
            if b['dc'] <= 0 and alive_p and sum(1 for f in a['foes'] if f['kind'] == 'kami') < 6:
                b['dc'] = 2.2 if rage else 3.2
                for sx in (-1, 1):
                    self.air_foe('kami', b['x'] + sx * 70, b['y'] + 70, None, a_=aim)
                self.audio.play('launch', .4)
            b['pc'] -= dt
            if b['pc'] <= 0 and alive_p:
                b['pc'] = 1.8 if rage else 2.6
                for i in range(-2, 3):
                    self.air_ebul(b['x'], b['y'] + 70, aim + i * 9, 220)
        elif k == 2:                                   # fantasma: se oculta
            b['ct'] -= dt
            ph = b['cloak']
            if ph == 'vis':
                b['alpha'] = 1.0
                b['x'] += clamp(math.sin(b['t'] * 0.9) * (W / 2 - 220) + W / 2 - b['x'], -160, 160) * dt
                b['wc'] -= dt
                if b['wc'] <= 0 and alive_p:
                    b['wc'] = 0.6 if rage else 0.85
                    for da in (-12, 0, 12):
                        self.air_ebul(b['x'], b['y'] + 50, aim + da, 235)
                if b['ct'] <= 0:
                    b['cloak'], b['ct'] = 'fade', 0.6
            elif ph == 'fade':
                b['alpha'] = max(0.12, b['ct'] / 0.6)
                if b['ct'] <= 0:
                    b['cloak'], b['ct'], b['tx'] = 'cloak', 3.0, random.uniform(200, W - 200)
            elif ph == 'cloak':
                b['alpha'] = 0.12
                b['x'] += clamp(b['tx'] - b['x'], -520, 520) * dt * 2.2
                if b['ct'] <= 0:
                    b['cloak'], b['ct'] = 'appear', 0.6
            else:
                b['alpha'] = 0.12 + 0.88 * (1 - b['ct'] / 0.6)
                if b['ct'] <= 0:
                    b['cloak'], b['ct'] = 'vis', 4.0 if not rage else 3.2
                    if alive_p:
                        for i in range(14):
                            self.air_ebul(b['x'], b['y'] + 20, i * (360 / 14), 160, 6)
        elif k == 3:                                   # artillero: bombardeo en hileras
            b['x'] = W / 2 + math.sin(b['t'] * 0.3) * (W / 2 - 200)
            b['rc'] -= dt
            if b['rc'] <= 0 and alive_p:
                b['rc'] = 2.0 if rage else 2.8
                gaps = [random.uniform(120, W - 120) for _ in range(2 if not rage else 3)]
                for x in range(30, W - 20, 40):
                    if all(abs(x - g) > 62 for g in gaps):
                        self.air_ebul(x, b['y'] + 60, 180, 165, 7)
                self.toast('¡Bombardeo! Pasá por los huecos', (255, 190, 100)) if b['pi'] == 0 else None
                if b['pi'] == 0:
                    self.say('piloto', '¡Bombardeo en camino! Pasá por los huecos.', 'warn')
                b['pi'] += 1
            b['pc'] -= dt
            if b['pc'] <= 0 and alive_p:
                b['pc'] = 1.4
                for sx in (-1, 1):
                    self.air_ebul(b['x'] + sx * 120, b['y'] + 20, bearing(p['x'] - b['x'] - sx * 120, p['y'] - b['y'] - 20), 235)
        elif k == 4:                                   # tormenta: rayos verticales
            b['x'] = W / 2 + math.sin(b['t'] * 0.5) * (W / 2 - 220)
            b['bc'] -= dt
            if b['bc'] <= 0 and alive_p:
                b['bc'] = 2.4 if rage else 3.4
                xs = [p['x']] + ([clamp(p['x'] + random.choice((-160, 160)), 60, W - 60)] if rage else [])
                for x in xs:
                    b['beams'].append(dict(x=x, st='charge', t=1.15, hit=False))
                self.audio.play('ping', .6)
            b['pc'] -= dt
            if b['pc'] <= 0 and alive_p:
                b['pc'] = 2.3
                for da in (-20, -10, 0, 10, 20):
                    self.air_ebul(b['x'], b['y'] + 60, aim + da, 215)
        else:                                          # titán aéreo
            b['x'] = W / 2 + math.sin(b['t'] * 0.35) * (W / 2 - 250)
            pods_alive = [pd for pd in b['pods'] if pd['hp'] > 0]
            for pod in pods_alive:
                pod['cd'] -= dt
                if pod['cd'] <= 0 and alive_p:
                    pod['cd'] = 1.5
                    px, py = b['x'] + pod['ox'], b['y'] + pod['oy']
                    base = bearing(p['x'] - px, p['y'] - py)
                    for da in (-9, 0, 9):
                        self.air_ebul(px, py + 20, base + da, 230)
            b['pc'] -= dt
            if b['pc'] <= 0 and alive_p:
                b['pc'] = 2.2 if pods_alive else 1.5
                if pods_alive:
                    for da in (-24, -12, 0, 12, 24):
                        self.air_ebul(b['x'], b['y'] + 70, aim + da, 215)
                else:
                    off = random.uniform(0, 360)
                    for i in range(18):
                        self.air_ebul(b['x'], b['y'] + 20, off + i * 20, 150, 6)
            if not pods_alive:
                b['dc'] -= dt
                if b['dc'] <= 0 and alive_p and sum(1 for f in a['foes'] if f['kind'] == 'kami') < 5:
                    b['dc'] = 3.0
                    for sx in (-1, 1):
                        self.air_foe('kami', b['x'] + sx * 90, b['y'] + 60, None, a_=aim)
                b['bc'] -= dt
                if b['bc'] <= 0 and alive_p:
                    b['bc'] = 3.4
                    b['beams'].append(dict(x=p['x'], st='charge', t=1.15, hit=False))
        # rayos (tormenta / titán)
        for bm in b['beams'][:]:
            bm['t'] -= dt
            if bm['st'] == 'charge' and bm['t'] <= 0:
                bm['st'], bm['t'] = 'fire', 0.55
                self.audio.play('boom_l', .4)
                self.shake = max(self.shake, 6)
            elif bm['st'] == 'fire':
                if not bm['hit'] and alive_p and abs(p['x'] - bm['x']) < 24:
                    bm['hit'] = True
                    self.air_hurt(22)
                if bm['t'] <= 0:
                    b['beams'].remove(bm)

    def air_boss_draw(self, cv, shadow):
        a = self.a
        b = a['boss']
        t = self.t
        spr = self.air_boss_sprite(b)
        if b['alpha'] > 0.5:
            shadow(spr, b['x'], b['y'])
        img = spr
        if b['hit'] > 0 or b['alpha'] < 1.0:
            img = spr.copy()
            if b['hit'] > 0:
                img.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            if b['alpha'] < 1.0:
                img.set_alpha(int(255 * b['alpha']))
        cv.blit(img, (b['x'] - img.get_width() // 2, b['y'] - img.get_height() // 2))
        if b['k'] == 0:
            for sx in (-1, 1):
                glow(cv, b['x'] + sx * 36, b['y'] - 54, 28 + 4 * math.sin(t * 20), (255, 120, 60), 0.8)
        elif b['k'] in ENG:
            hot = {1: (255, 170, 90), 2: (255, 150, 70), 3: (255, 170, 90), 4: (255, 160, 70)}.get(b['k'], (255, 160, 80))
            rr = {1: 15, 2: 12, 3: 11, 4: 17}.get(b['k'], 14)
            for ex, ey in ENG[b['k']]:
                glow(cv, b['x'] + ex, b['y'] + ey, rr + 2 * math.sin(t * 22 + ex), hot, 0.6)
        if b['k'] == 5:
            if self.air.get('pod') is None:
                self.air['pod'] = make_pod_turret()
            for pod in b['pods']:
                px, py = b['x'] + pod['ox'], b['y'] + pod['oy']
                if pod['hp'] <= 0:                                           # torreta destruida: cráter humeante
                    pygame.draw.circle(cv, (14, 12, 12), (int(px), int(py)), 24)
                    pygame.draw.circle(cv, (44, 30, 26), (int(px), int(py)), 17)
                    glow(cv, px, py, 22 + 4 * math.sin(t * 9 + px), (255, 110, 50), 0.35)
                    continue
                pl = a['p']
                ang = -math.degrees(math.atan2(pl['x'] - px, -(pl['y'] - py))) if not pl.get('dead') else 0.0
                img = pygame.transform.rotate(self.air['pod'], ang)
                if pod['hit'] > 0:
                    img = img.copy()
                    img.fill((120, 120, 120, 0), special_flags=pygame.BLEND_RGB_ADD)
                cv.blit(img, (px - img.get_width() // 2, py - img.get_height() // 2))
                pygame.draw.rect(cv, (8, 12, 24), (px - 34, py - 54, 68, 6))
                pygame.draw.rect(cv, (240, 80, 70), (px - 33, py - 53, int(66 * pod['hp'] / pod['max']), 4))
            if self.air_boss_invulnerable(b):
                draw_circ(cv, b['x'], b['y'], 70, (120, 200, 255), 24 + 14 * math.sin(t * 6), 3)
        for bm in b['beams']:
            if bm['st'] == 'charge':
                k = 1 - bm['t'] / 1.15
                pygame.draw.line(cv, (255, 80, 70), (bm['x'], b['y'] + 40), (bm['x'], H), 1 + int(3 * k))
                if int(t * 14) % 2 == 0:
                    pygame.draw.line(cv, (255, 210, 210), (bm['x'], b['y'] + 40), (bm['x'], H), 1)
            else:
                pygame.draw.line(cv, (70, 210, 255), (bm['x'], b['y'] + 40), (bm['x'], H), 40)
                pygame.draw.line(cv, (200, 250, 255), (bm['x'], b['y'] + 40), (bm['x'], H), 22)
                pygame.draw.line(cv, (255, 255, 255), (bm['x'], b['y'] + 40), (bm['x'], H), 8)
                glow(cv, bm['x'], b['y'] + 60, 50, (150, 240, 255), 0.9)

    # ---------------------------------------------------------- clima de cada oleada
    def air_ambient_update(self, dt):
        a = self.a
        amb = self.air_kind()
        if amb == 2:                                   # tormenta: lluvia y relámpagos
            rain = a.setdefault('rain', [[random.uniform(0, W), random.uniform(0, H)] for _ in range(70)])
            for r_ in rain:
                r_[1] += 900 * dt
                r_[0] -= 120 * dt
                if r_[1] > H:
                    r_[0], r_[1] = random.uniform(0, W + 150), random.uniform(-80, 0)
            a['lt'] = a.get('lt', random.uniform(3, 6)) - dt
            if a['lt'] <= 0:
                a['lt'] = random.uniform(4, 8)
                a['flash'] = 0.22
            a['flash'] = max(0.0, a.get('flash', 0.0) - dt)
        elif amb == 5 and random.random() < dt * 14:
            self.fx.add('glow', random.uniform(0, W), H + 10, random.uniform(-20, 20), -random.uniform(60, 140), 2.0, 6, 2, (255, 120, 60))

    def air_ambient_draw(self, cv):
        a = self.a
        amb = self.air_kind()
        tint = AIR_AMBIENT[amb]
        if tint is None:
            return
        if 'amb_surf' not in a:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill(tint)
            a['amb_surf'] = s
        cv.blit(a['amb_surf'], (0, 0))
        if amb == 2:
            for r_ in a['rain']:
                pygame.draw.line(cv, (170, 200, 235), (r_[0], r_[1]), (r_[0] + 6, r_[1] - 22), 1)
            if a.get('flash', 0) > 0:
                fs = pygame.Surface((W, H), pygame.SRCALPHA)
                fs.fill((235, 240, 255, int(170 * a['flash'] / 0.22)))
                cv.blit(fs, (0, 0))
        elif amb == 3:
            rnd = random.Random(7)
            for _ in range(40):
                x, y = rnd.uniform(0, W), rnd.uniform(0, H)
                if int(self.t * 2 + x) % 3:
                    pygame.draw.circle(cv, (200, 215, 255), (int(x), int(y)), 1)

    # ---------------------------------------------------------- misiles teledirigidos
    def air_homing(self, bl, dt):
        a = self.a
        best, bd = None, 9e9
        for f in a['foes']:
            if f['kind'] == 'mine':
                continue
            d = dist(bl['x'], bl['y'], f['x'], f['y'])
            if d < bd:
                best, bd = (f['x'], f['y']), d
        b = a['boss']
        if b and not a['boss_dead'] and not (b['k'] == 2 and b['alpha'] < 0.5):
            d = dist(bl['x'], bl['y'], b['x'], b['y'])
            if d < bd:
                best, bd = (b['x'], b['y']), d
        if best is None:
            return
        cur = bearing(bl['vx'], bl['vy'])
        want = bearing(best[0] - bl['x'], best[1] - bl['y'])
        cur = (cur + clamp(angle_diff(cur, want), -260 * dt, 260 * dt)) % 360
        bl['vx'], bl['vy'] = vec(cur, 440)
