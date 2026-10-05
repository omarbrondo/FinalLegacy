"""Combate combinado: si una batería costera y un barco enemigo están cerca, se pelea contra los dos en el mismo combate.
El barco es el blanco principal; la batería es un cañón fijo en un costado con su propia barra de vida. Hay que hundir a ambos."""
import math
import random
from .common import W, WORLD_H, WORLD_W, bearing, clamp, dist, glow, vec

COMBO_NEST_R = 450          # batería a menos de esto del jugador cuando un barco inicia el combate
COMBO_SHIP_R = 520          # barco a menos de esto del jugador cuando una batería inicia el combate
BAT_SLOW = 1.25             # el barco dispara más espaciado mientras la batería sigue en pie


class NavalComboMixin:
    # ------------------------------------------------------------------ búsqueda en el mapa
    def nb_find_nest(self):
        """Batería viva y lista cerca del jugador (para sumarla al combate contra un barco)."""
        best = None
        for n in self.nests:
            if n['alive'] and n['cool'] <= 0:
                d = dist(self.sx, self.sy, n['x'], n['y'])
                if d < COMBO_NEST_R and (best is None or d < best[0]):
                    best = (d, n)
        return best[1] if best else None

    def nb_find_ship(self):
        """Barco enemigo común (no jefe, sin escudo) y listo cerca del jugador (para sumarlo al combate contra una batería)."""
        best = None
        for en in self.enemies:
            if en.get('is_boss') or en.get('shield') or en['cool'] > 0:
                continue
            d = dist(self.sx, self.sy, en['x'], en['y'])
            if d < COMBO_SHIP_R and (best is None or d < best[0]):
                best = (d, en)
        return best[1] if best else None

    # ------------------------------------------------------------------ inicio
    def nb_init(self, nest):
        c = self.c
        c['bat'] = None
        self.bat_ref = None
        if nest is None:
            return
        side = random.choice((-1, 1))
        c['bat'] = dict(x=float(W - 150 if side > 0 else 150), y=125.0, h=180.0, hp=nest['hp'], max=nest['max'],
                        cool=random.uniform(3.2, 4.2), sink=None, burst=[])
        self.bat_ref = nest
        c['e']['cool'] = max(c['e']['cool'], 3.0)
        self.banner('¡COMBATE COMBINADO!', 'Barco enemigo + batería costera: hundí a los dos  |  E huir', (255, 120, 80), 4.2)

    def nb_alive(self):
        b = self.c.get('bat')
        return b is not None and b['sink'] is None

    def nb_busy(self):
        """True mientras la batería siga en pie o su hundimiento no haya terminado (el combate no puede cerrarse)."""
        b = self.c.get('bat')
        return b is not None and (b['sink'] is None or b['sink'] < 2.0)

    def nb_slow(self):
        return BAT_SLOW if self.nb_alive() else 1.0

    # ------------------------------------------------------------------ actualización
    def nb_update(self, dt):
        c = self.c
        b = c.get('bat')
        if b is None:
            return
        p, e = c['p'], c['e']
        if b['sink'] is not None:
            b['sink'] += dt
            if int(b['sink'] * 5) != int((b['sink'] - dt) * 5):
                self.fx.explode(b['x'] + random.uniform(-26, 26), b['y'] + random.uniform(-26, 26), 0.9)
                self.audio.play('boom_s', .5)
            return
        if e['sink'] is not None and not b.get('warned'):
            b['warned'] = True
            self.call_out('¡QUEDA LA BATERÍA!', (255, 170, 110), 'batleft', 6)
        hpf = b['hp'] / b['max']
        if hpf < .5 and random.random() < dt * 10:
            self.fx.add('smoke', b['x'], b['y'], random.uniform(-8, 8), -25, 2.0, 6, 26, (50, 50, 50))
        if hpf < .25 and random.random() < dt * 14:
            self.fx.add('glow', b['x'] + random.uniform(-14, 14), b['y'] + random.uniform(-14, 14), life=.4, r0=8, r1=22, col=(255, 140, 50))
        b['cool'] -= dt
        if b['cool'] <= 0 and p['sink'] is None:
            b['cool'] = random.uniform(3.4, 4.6) * max(0.8, 1 - 0.03 * self.wave)
            self.nb_fire()
            if self.wave >= 3 and random.random() < 0.4:
                b['burst'].append(0.5)
        b['burst'] = [t_ - dt for t_ in b['burst']]
        due = [t_ for t_ in b['burst'] if t_ <= 0]
        b['burst'] = [t_ for t_ in b['burst'] if t_ > 0]
        for _ in due:
            if p['sink'] is None:
                self.nb_fire()

    def nb_fire(self):
        c = self.c
        p, b = c['p'], c['bat']
        spd = 215 + 4 * self.wave
        T = dist(p['x'], p['y'], b['x'], b['y']) / spd
        vx, vy = vec(p['h'], p['v'])
        err = max(5.0, 13 - 1.0 * self.wave) * (0.5 if self.nv_lit() else 1.0)
        if self.na_smoked():
            err = err * 2.0 + 14
            T = 0.0
        ang = bearing(p['x'] + vx * T - b['x'], p['y'] + vy * T - b['y']) + random.uniform(-err, err)
        self.launch_missile(b, ang, spd, 'e', 0.0, (11, 6))
        self.audio.play('launch', .45)
        self.fx.add('glow', b['x'], b['y'], life=.2, r0=22, r1=46, col=(255, 160, 120))
        c['flashes'].append([b['x'], b['y'], 110, (255, 200, 140), 1.0])

    # ------------------------------------------------------------------ impactos
    def nb_shell_hit(self, s):
        """Misil del jugador contra la batería. Devuelve True si se consumió."""
        c = self.c
        b = c.get('bat')
        if b is None or b['sink'] is not None or s['own'] != 'p':
            return False
        dn = dist(s['x'], s['y'], b['x'], b['y'])
        if dn >= 46:
            return False
        full = dn < 26
        dmg = (3 if full else 2) * self.up_dmg() * s.get('f', 0.5 if s.get('ally') else 1.0)
        b['hp'] -= dmg
        self.pop('-%d' % round(dmg), s['x'], s['y'] - 20, (255, 255, 160))
        if not s.get('ally'):
            self.na_charge(20 if full else 10)
        c['flashes'].append([s['x'], s['y'], 100 if full else 64, (255, 190, 110), 1.0])
        for _ in range(8 if full else 4):
            a_ = random.uniform(0, 6.28)
            sp_ = random.uniform(80, 240)
            self.fx.add('spark', s['x'], s['y'], math.cos(a_) * sp_, math.sin(a_) * sp_, random.uniform(0.4, 0.9), col=(255, 190, 90), drag=1.2)
        self.fx.explode(s['x'], s['y'], 1.0 if full else 0.7)
        self.audio.play('hit')
        if b['hp'] <= 0:
            self.nb_kill()
        return True

    def nb_mg_hit(self, x, y):
        """Bala de la ametralladora contra la batería. Devuelve True si se consumió."""
        b = self.c.get('bat')
        if b is None or b['sink'] is not None or dist(x, y, b['x'], b['y']) >= 40:
            return False
        b['hp'] -= (0.13 if dist(x, y, b['x'], b['y']) < 22 else 0.1) * self.up_dmg()
        self.fx.add('spark', x, y, random.uniform(-90, 90), random.uniform(-90, 90), 0.25, col=(255, 220, 140), drag=2)
        self.na_charge(0.5)
        if b['hp'] <= 0:
            self.nb_kill()
        return True

    def nb_kill(self):
        c = self.c
        b = c['bat']
        b['sink'] = 0.0
        self.audio.play('boom_l')
        self.fx.explode(b['x'], b['y'], 2.2, True)
        c['flashes'].append([b['x'], b['y'], 200, (255, 200, 120), 1.0])
        self.fx.add('ring', b['x'], b['y'], life=0.9, r0=10, r1=170, col=(255, 230, 190))
        self.shake = max(self.shake, 8)
        nst = self.bat_ref
        nst['alive'] = False
        pts = 400 + 100 * self.wave
        self.add_score(pts)
        self.ammo = min(40, self.ammo + 8)
        self.radar_t = max(self.radar_t, 60.0)
        self.call_out('¡BATERÍA SILENCIADA!', (255, 230, 120), 'batkill', 5)
        self.toast('¡Batería destruida! +%d  (+8 munición, radar enemigo 60 s)' % pts, (120, 255, 160))

    def nb_bonus(self):
        """Premio extra al ganar un combate combinado (se llama al hundir el barco con la batería ya destruida)."""
        if self.c.get('bat') is None:
            return 0
        self.add_score(300)
        return 300

    # ------------------------------------------------------------------ huir
    def nb_flee(self):
        """Huir con la batería viva: queda en el mapa (herida y recargando) y el barco se aleja del jugador."""
        b = self.c['bat']
        nst = self.bat_ref
        nst['hp'] = max(1.0, b['hp'])
        nst['cool'] = 14.0
        bx, by = vec(bearing(self.sx - nst['x'], self.sy - nst['y']), 400)
        self.sx, self.sy = clamp(nst['x'] + bx, 60, WORLD_W - 60), clamp(nst['y'] + by, 60, WORLD_H - 60)

    # ------------------------------------------------------------------ dibujo
    def nb_draw(self, cv):
        c = self.c
        b = c.get('bat')
        if b is None:
            return
        p = c['p']
        spr = self.nest_gfx()
        spr.set_alpha(255 if b['sink'] is None else 255 - int(150 * clamp(b['sink'] / 2.0, 0, 1)))
        cv.blit(spr, (b['x'] - spr.get_width() // 2, b['y'] - spr.get_height() // 2))
        if b['sink'] is None:
            self.blit_turret(cv, self.tur_e, b['x'], b['y'] - 4, bearing(p['x'] - b['x'], p['y'] - b['y']))
            pulse = 0.5 + 0.5 * math.sin(self.t * 4)
            glow(cv, b['x'], b['y'], 46 + 10 * pulse, (255, 80, 60), 0.18)
            self.text(cv, 'BATERÍA', self.f_s, (255, 150, 130), b['x'], b['y'] + 52, 'c')
        else:
            glow(cv, b['x'], b['y'], 50, (255, 140, 50), 0.5 * clamp(1 - b['sink'] / 2.0, 0, 1))

    def nb_hud(self, cv):
        b = self.c.get('bat')
        if b is None:
            return
        self.panel(cv, (W // 2 - 230, 88, 460, 34), 170)
        self.bar(cv, W // 2 - 210, 94, 420, 22, max(0.0, b['hp']) / b['max'], (255, 150, 70), 'BATERÍA COSTERA')
