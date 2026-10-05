"""Mobiliario urbano del combate de tanques: farolas, autos y bicicletas (los tanques los aplastan)."""
import math
import pygame
import random
from .common import glow
from .tk_art import TK_ANG, TK_FOG, TK_PXU

CRUSH_R = {'car': 3.4, 'bike': 2.2, 'lamp': 1.9}
POINTS = {'car': 25, 'bike': 10, 'lamp': 5}


class TankPropsMixin:
    def tk_make_props(self, blds, city, wave):
        """Genera autos, bicicletas y farolas sobre las calles. A más oleadas, más destrozos de guerra previos."""
        rnd = random.Random(city['seed'] * 17 + wave * 5)
        war = min(0.7, 0.12 * (wave - 1))                       # fracción ya destruida por la guerra

        def clear(x, z, m):
            for b in blds:
                if abs(x - b['x']) < b['hw'] + m and abs(z - b['z']) < b['hd'] + m:
                    return False
            return abs(x) < 112 and abs(z) < 112
        props = []
        lines = (-69.0, -23.0, 23.0, 69.0)

        def add(kind, x, z, rot, **kw):
            if any(math.hypot(x - q['x'], z - q['z']) < (4.6 if kind == 'car' else 2.4) for q in props if q['kind'] == kind):
                return False
            if math.hypot(x, z + 112) < 9:                      # no encima del punto de partida del jugador
                return False
            st = 'ok'
            if rnd.random() < war:
                st = 'burnt' if kind == 'car' else ('down' if kind == 'lamp' else 'crushed')
            props.append(dict(kind=kind, x=x, z=z, rot=rot, st=st, var=rnd.randrange(6), r=CRUSH_R[kind], t=0.0, **kw))
            return True
        # autos estacionados junto al cordón
        n = 0
        for _ in range(400):
            if n >= 15:
                break
            ln = rnd.choice(lines)
            along = rnd.uniform(-105, 105)
            off = rnd.choice((-2.7, 2.7)) + rnd.uniform(-0.3, 0.3)
            if rnd.random() < 0.5:
                x, z, rot = ln + off, along, 0.0 + rnd.uniform(-3, 3)
            else:
                x, z, rot = along, ln + off, 90.0 + rnd.uniform(-3, 3)
            if clear(x, z, 3.0) and add('car', x, z, rot):
                n += 1
        # bicicletas
        n = 0
        for _ in range(300):
            if n >= 8:
                break
            ln = rnd.choice(lines)
            along = rnd.uniform(-105, 105)
            off = rnd.choice((-4.7, 4.7))
            x, z, rot = (ln + off, along, rnd.uniform(-20, 20)) if rnd.random() < 0.5 else (along, ln + off, 90 + rnd.uniform(-20, 20))
            if clear(x, z, 1.3) and add('bike', x, z, rot):
                n += 1
        # farolas en las esquinas y a lo largo de las veredas
        n = 0
        for _ in range(500):
            if n >= 22:
                break
            ln = rnd.choice(lines)
            along = rnd.choice((-92.0, -69.0, -46.0, -23.0, 0.0, 23.0, 46.0, 69.0, 92.0))
            off = rnd.choice((-4.9, 4.9))
            x, z = (ln + off, along + rnd.choice((-4.9, 4.9))) if rnd.random() < 0.5 else (along + rnd.choice((-4.9, 4.9)), ln + off)
            if clear(x, z, 0.9) and add('lamp', x, z, rnd.uniform(0, 360), dirn=rnd.uniform(0, 360)):
                n += 1
        return props

    def tk_prop_crush(self, pr, who, x, z):
        k = self.k
        pr['st'] = 'down' if pr['kind'] == 'lamp' else 'crushed'
        pr['t'] = 0.0
        self.tk_debris(pr['x'], pr['z'], 8 if pr['kind'] == 'car' else 4)
        self.audio.play('hit', .45 if who == 'p' else .25)
        if who == 'p':
            k['crushed'] = k.get('crushed', 0) + 1
            self.add_score(POINTS[pr['kind']])
            self.tk_say({'car': '¡AUTO APLASTADO! +%d' % POINTS['car'], 'bike': '¡BICICLETA APLASTADA!',
                         'lamp': 'FAROLA DERRIBADA'}[pr['kind']])
            k['p']['v'] *= 0.88

    def tk_props_update(self, dt):
        k = self.k
        p = k['p']
        for pr in k['props']:
            pr['t'] += dt
            if pr['st'] not in ('ok', 'burnt'):
                continue
            if pr['st'] == 'burnt':
                continue
            for who, ax, az in [('p', p['x'], p['z'])] + [('e', e['x'], e['z']) for e in k['tanks']]:
                if who == 'p' and p['dead']:
                    continue
                if abs(pr['x'] - ax) < pr['r'] and abs(pr['z'] - az) < pr['r'] and math.hypot(pr['x'] - ax, pr['z'] - az) < pr['r']:
                    self.tk_prop_crush(pr, who, ax, az)
                    break

    def tk_prop_shot(self, x, z):
        """Un proyectil impacta cerca de un auto: lo incendia."""
        for pr in self.k['props']:
            if pr['kind'] == 'car' and pr['st'] == 'ok' and abs(pr['x'] - x) < 2.6 and abs(pr['z'] - z) < 2.6:
                pr['st'] = 'burnt'
                pr['t'] = 0.0
                self.tk_boom(pr['x'], pr['z'], 3.2, 0.9)
                self.tk_debris(pr['x'], pr['z'], 12)
                self.audio.play('boom_s', .5)
                return True
        return False

    # ------------------------------------------------------------ dibujo
    def tk_props_draw(self, strips):
        k = self.k
        p = k['p']
        T = self.tk_tex
        add = self.tk_add_box
        ya = math.radians(p['yaw'])
        sy_, cy_ = math.sin(ya), math.cos(ya)
        for pr in k['props']:
            dx, dz = pr['x'] - p['x'], pr['z'] - p['z']
            cz, cx = dx * sy_ + dz * cy_, dx * cy_ - dz * sy_
            lim = 105 if pr['kind'] == 'lamp' else (80 if pr['kind'] == 'car' else 70)
            if cz < -6 or cz > lim or abs(cx) > cz * 0.95 + 9:        # fuera de cámara o muy lejos: no se dibuja
                continue
            kind, st, x, z = pr['kind'], pr['st'], pr['x'], pr['z']
            if kind == 'car':
                self.tk_add_car(strips, pr)
            elif kind == 'bike':
                key = (pr['var'] % 2, 'crushed') if st == 'crushed' else (pr['var'] % 6, 'ok')
                self.tk_add_spr(strips, pr, self.bike_spr.get(key) or self.bike_spr[(0, 'ok')])
            else:                                                       # farola
                if st == 'down':
                    d = math.radians(pr['dirn'])
                    add(strips, x + 3.4 * math.sin(d), z + 3.4 * math.cos(d), 0.13, 3.5, 0, 0.26, pr['dirn'], T['pole'], 0.5)
                    add(strips, x + 6.7 * math.sin(d), z + 6.7 * math.cos(d), 0.3, 0.7, 0, 0.3, pr['dirn'], T['lamp'], 1.0)
                else:
                    add(strips, x, z, 0.13, 0.13, 0, 7.0, 0, T['pole'], 0.26)
                    d = math.radians(pr['dirn'])
                    add(strips, x + 0.9 * math.sin(d), z + 0.9 * math.cos(d), 0.28, 0.9, 6.85, 7.15, pr['dirn'], T['lamp'], 1.8)

    def tk_add_car(self, strips, pr):
        """Auto como sprite 3D pre-renderizado (como los tanques), ordenado por profundidad con el resto de la escena."""
        c = self.tk_cam(pr['x'], 0, pr['z'])
        z = c[2]
        if z < 2.5 or z > 190:
            return
        st = pr['st']
        key = (0, 'burnt') if st == 'burnt' else ((0 if pr['var'] % 2 else 3, 'crushed') if st == 'crushed' else (pr['var'] % 8, 'ok'))
        self.tk_add_spr(strips, pr, self.car_spr.get(key) or self.car_spr[(0, 'ok')])

    def tk_add_spr(self, strips, pr, frames):
        """Sprite 3D pre-renderizado (auto o bicicleta) en su ángulo de vista, con niebla y orden de profundidad."""
        p = self.k['p']
        c = self.tk_cam(pr['x'], 0, pr['z'])
        z = c[2]
        if z < 2.5 or z > 190:
            return
        hi = int(round(((pr['rot'] - p['yaw']) % 360) / (360.0 / TK_ANG))) % TK_ANG
        img0, ax, ay = frames[hi]
        sx, sy = self.tk_prj(c)
        scale = (self.TK_F / z) / TK_PXU
        vp = self.TK_VP
        dx, dy = sx - ax * scale, sy - ay * scale
        dw, dh = img0.get_width() * scale, img0.get_height() * scale
        vx0, vx1 = max(dx, vp.x), min(dx + dw, vp.right)
        vy0, vy1 = max(dy, vp.y), min(dy + dh, vp.bottom)
        if vx1 - vx0 < 1 or vy1 - vy0 < 1:
            return
        sw, sh = img0.get_size()
        r = pygame.Rect(int((vx0 - dx) / scale), int((vy0 - dy) / scale), 0, 0)
        r.w = min(sw - r.x, int((vx1 - dx) / scale) - r.x + 2)
        r.h = min(sh - r.y, int((vy1 - dy) / scale) - r.y + 2)
        img = pygame.transform.scale(img0.subsurface(r), (max(1, int(r.w * scale)), max(1, int(r.h * scale))))
        f = min(0.8, z / 170.0)
        img.fill((int(255 * (1 - f)),) * 3 + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        img.fill(tuple(int(q * f) for q in TK_FOG) + (0,), special_flags=pygame.BLEND_RGB_ADD)
        strips.append((z - 0.4, None, img, int(dx + r.x * scale), int(dy + r.y * scale)))

    def tk_props_glow(self, cv):
        """Luz de las farolas (más intensa de noche y con niebla) y fuego de los autos incendiados."""
        k = self.k
        p = k['p']
        t = self.t
        k_ = {'clear': 0.35, 'fog': 0.8, 'night': 1.0}[k['wx']]
        for pr in k['props']:
            dx, dz = pr['x'] - p['x'], pr['z'] - p['z']
            if dx * dx + dz * dz > 100 ** 2:
                continue
            if pr['kind'] == 'lamp' and pr['st'] == 'ok':
                d = math.radians(pr['dirn'])
                c = self.tk_cam(pr['x'] + 0.9 * math.sin(d), 7.0, pr['z'] + 0.9 * math.cos(d))
                tag = 'l'
            elif pr['kind'] == 'car' and pr['st'] == 'burnt':
                c = self.tk_cam(pr['x'], 1.0, pr['z'])
                tag = 'f'
            else:
                continue
            if c[2] < 2:
                continue
            sx, sy = self.tk_prj(c)
            if not (self.TK_VP.x - 60 < sx < self.TK_VP.right + 60):
                continue
            if tag == 'l':
                glow(cv, sx, sy, min(110, max(8, int(320 / c[2]))), (255, 226, 150), k_)
            else:
                fl = 0.7 + 0.3 * math.sin(t * 11 + pr['x'])
                glow(cv, sx, sy, min(90, max(8, int(240 / c[2]))), (255, 120, 40), 0.7 * fl)
