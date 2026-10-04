"""Combate naval: destructores, submarinos, baterías costeras y acorazados."""
import math
import pygame
import random
from .common import (
    BOSS_MOUNTS, H, Particles, W,
    WORLD_H, WORLD_W, angle_diff, bearing,
    clamp, dist, draw_circ, glow,
    vec)


class NavalMixin:
    # ---------------------------------------------------------- COMBATE
    def start_combat(self, en):
        self.fx = Particles()
        self.enemy_ref = en
        is_boss = en.get('is_boss', False)
        is_nest = en.get('nest', False)
        is_sub = en.get('sub', False)
        self.c = dict(
            p=dict(x=W / 2, y=H - 170.0, h=0.0, v=0.0, cool=0.0, wake=0.0, sink=None),
            e=dict(x=W / 2 + (random.uniform(-60, 60) if is_nest else random.uniform(-150, 150)),
                   y=130.0 if is_nest else (220.0 if is_boss else 170.0), h=180.0, v=0.0 if is_nest else (20.0 if is_boss else 40.0),
                   cool=3.0 if is_boss else 2.0,
                   orb=random.choice([-1, 1]), orb_t=5.0, burst=[], wake=0.0, sink=None, hp=en['hp'], max=en['max'], surf=False, ut=3.0),
            shells=[], t=0.0, is_boss=is_boss, nest=is_nest, sub=is_sub, name=en.get('name', ''))
        self.aim = [W / 2, 300.0]
        self.go('combat')
        if is_sub:
            self.audio.play('alarm')
            self.banner('¡SUBMARINO!', 'Solo es vulnerable cuando emerge a lanzar torpedos: esperalo y disparale  |  E: huir', (120, 220, 200), 4.0)
        elif is_nest:
            self.audio.play('alarm')
            self.banner('¡BATERÍA COSTERA!', 'Cañón fijo en el islote: esquivá sus misiles y destruilo  |  E: huir', (255, 140, 90), 3.6)
        elif is_boss:
            self.audio.play('alarm')
            self.banner('¡ACORAZADO %s!' % en['name'], 'Escudo digital caído  |  3 baterías de misiles  |  Hundilo o te hunde', (255, 60, 60), 4.0)
        else:
            self.banner('¡COMBATE NAVAL!', 'W/S/A/D: navegar  |  Mouse+Clic: disparar misil (vuela recto)  |  E: huir', (255, 150, 90), 3.4)

    def launch_missile(self, ship, ang, speed, own, off=0.0, dmg=(22, 12)):
        ox, oy = vec(ship['h'], off)
        fx_, fy_ = vec(ang, 30)
        vx, vy = vec(ang, speed)
        self.c['shells'].append(dict(x=ship['x'] + ox + fx_, y=ship['y'] + oy + fy_, vx=vx, vy=vy, ang=ang, own=own,
                                     life=3.0, dmg=dmg))

    def fire_shell(self):
        c = self.c
        p = c['p']
        if p['sink'] is not None or p['cool'] > 0:
            return
        if self.ammo <= 0:
            self.audio.play('empty')
            self.toast('¡Sin munición! Presioná E para huir', (255, 90, 80))
            return
        self.ammo -= 1
        p['cool'] = 0.9
        tx, ty = self.combat_aim()
        self.launch_missile(p, bearing(tx - p['x'], ty - p['y']), 400, 'p')
        self.audio.play('launch', .8)
        self.fx.add('glow', p['x'], p['y'], life=.2, r0=20, r1=44, col=(255, 220, 150))
        self.shake = max(self.shake, 3)

    def combat_aim(self):
        p = self.c['p']
        ax, ay = self.aim
        if not self.mouse_moved:
            fx, fy = vec(p['h'], 300)
            ax, ay = p['x'] + fx, p['y'] + fy
        d = dist(p['x'], p['y'], ax, ay)
        if d > 650:
            ax = p['x'] + (ax - p['x']) / d * 650
            ay = p['y'] + (ay - p['y']) / d * 650
        return clamp(ax, 20, W - 20), clamp(ay, 20, H - 20)

    def flee(self):
        c = self.c
        if c['p']['sink'] is not None or c['e']['sink'] is not None:
            return
        en = self.enemy_ref
        en['hp'] = c['e']['hp']
        if en.get('nest'):
            en['cool'] = 14.0
            bx, by = vec(bearing(self.sx - en['x'], self.sy - en['y']), 400)
            self.sx, self.sy = clamp(en['x'] + bx, 60, WORLD_W - 60), clamp(en['y'] + by, 60, WORLD_H - 60)
        else:
            en['cool'] = 6.0
            en['state'] = 'patrol'
            en['wp'] = self.rand_wp()
            bx, by = vec(bearing(en['x'] - self.sx, en['y'] - self.sy), 220)
            en['x'], en['y'] = clamp(self.sx + bx, 60, WORLD_W - 60), clamp(self.sy + by, 60, WORLD_H - 60)
        self.hull -= 8
        self.toast('Huiste bajo fuego: -8 casco', (255, 140, 90))
        self.audio.play('hit', .7)
        if self.hull <= 0:
            return self.game_over('Tu buque se hundió al huir')
        self.go('map')

    def upd_combat(self, dt):
        c = self.c
        p, e = c['p'], c['e']
        c['t'] += dt
        keys = pygame.key.get_pressed()
        alive_p = p['sink'] is None
        thr = ((1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0) - (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0)) if alive_p else 0
        turn = ((1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)) if alive_p else 0
        if self.fuel <= 0:
            thr = 0
        if thr > 0:
            p['v'] = min(125, p['v'] + 80 * dt)
        elif thr < 0:
            p['v'] = max(-35, p['v'] - 110 * dt)
        else:
            p['v'] -= p['v'] * 0.5 * dt
        p['h'] = (p['h'] + turn * 62 * clamp(abs(p['v']) / 50, 0.25, 1) * (1 if p['v'] >= 0 else -1) * dt) % 360
        dx, dy = vec(p['h'], p['v'] * dt)
        p['x'] += dx
        p['y'] += dy
        boss_c = c['is_boss']
        for ship in (p, e):
            mx_, my_ = (90, 150) if (ship is e and boss_c) else (50, 60)
            if ship['x'] < mx_ or ship['x'] > W - mx_ or ship['y'] < my_ or ship['y'] > H - my_:
                ship['x'], ship['y'] = clamp(ship['x'], mx_, W - mx_), clamp(ship['y'], my_, H - my_)
                ship['v'] *= 0.6
        self.fuel = max(0.0, self.fuel - abs(p['v']) / 125 * 0.35 * dt)
        self.audio.engine_vol(abs(p['v']) / 125 * 0.9 + 0.1)
        p['cool'] = max(0.0, p['cool'] - dt)
        # IA enemiga
        if e['sink'] is None and c['nest']:
            e['cool'] -= dt
            e['h'] = 180.0
            if e['cool'] <= 0 and p['sink'] is None:
                e['cool'] = random.uniform(2.2, 3.0) * max(0.6, 1 - 0.06 * self.wave)
                self.enemy_fire()
                if self.wave >= 2:
                    e['burst'].append([0.45, None])
                if self.wave >= 5:
                    e['burst'].append([0.9, None])
            e['burst'] = [[t_ - dt, m_] for t_, m_ in e['burst']]
            due = [b_ for b_ in e['burst'] if b_[0] <= 0]
            e['burst'] = [b_ for b_ in e['burst'] if b_[0] > 0]
            for _t, m_ in due:
                self.enemy_fire(m_)
        elif e['sink'] is None:
            dxp, dyp = p['x'] - e['x'], p['y'] - e['y']
            dd = math.hypot(dxp, dyp) or 1
            to_p = bearing(dxp, dyp)
            e['orb_t'] -= dt
            if e['orb_t'] <= 0:
                e['orb'] *= -1
                e['orb_t'] = random.uniform(4, 8)
            near, far = (260, 400) if c['is_boss'] else (260, 420)
            if dd > far:
                want = to_p
            elif dd < near:
                want = to_p + 180
            else:
                want = to_p + 90 * e['orb']
            edge = 190 if c['is_boss'] else 110
            if e['x'] < edge or e['x'] > W - edge or e['y'] < edge or e['y'] > H - edge:
                want = bearing(W / 2 - e['x'], H / 2 - e['y'])
            turn_rate = 17 if c['is_boss'] else 48
            e['h'] = (e['h'] + clamp(angle_diff(e['h'], want), -turn_rate * dt, turn_rate * dt)) % 360
            e['v'] += (((34 + 2 * self.wave) if c['is_boss'] else ((46 + 3 * self.wave) if c['sub'] else (62 + 5 * self.wave))) - e['v']) * min(1, dt * (0.8 if c['is_boss'] else 1.5))
            ex, ey = vec(e['h'], e['v'] * dt)
            e['x'] += ex
            e['y'] += ey
            e['cool'] -= dt
            is_boss = self.c.get('is_boss', False)
            if c['sub']:
                e['ut'] -= dt
                if not e['surf'] and random.random() < dt * 6:
                    self.fx.add('foam', e['x'] + random.uniform(-10, 10), e['y'] + random.uniform(-30, 30), life=1.2, r0=3, r1=11, col=(200, 235, 245))
                if e['ut'] <= 0 and p['sink'] is None:
                    e['surf'] = not e['surf']
                    if e['surf']:
                        e['ut'] = 3.4
                        self.sub_fire()
                        self.fx.splash(e['x'], e['y'], 1.0)
                        self.audio.play('ping', .6)
                    else:
                        e['ut'] = random.uniform(4.0, 5.5) * max(0.7, 1 - 0.05 * self.wave)
            elif e['cool'] <= 0 and p['sink'] is None:
                if is_boss:
                    e['cool'] = random.uniform(3.4, 4.4) * max(0.65, 1 - 0.05 * self.wave)
                    self.enemy_fire(0)
                    e['burst'] += [[0.35, 1], [0.7, 2]]
                else:
                    e['cool'] = random.uniform(2.1, 3.0) * max(0.55, 1 - 0.07 * self.wave)
                    self.enemy_fire()
                    if self.wave >= 3:
                        e['burst'].append([0.35, None])
            e['burst'] = [[t_ - dt, m_] for t_, m_ in e['burst']]
            due = [b_ for b_ in e['burst'] if b_[0] <= 0]
            e['burst'] = [b_ for b_ in e['burst'] if b_[0] > 0]
            for _t, m_ in due:
                self.enemy_fire(m_)
            if is_boss:
                if random.random() < dt * 9:
                    for sd in (-1, 1):
                        lx, ly = vec(e['h'] + 90, sd * 17)
                        fx_, fy_ = vec(e['h'], -38)
                        self.fx.add('smoke', e['x'] + lx + fx_, e['y'] + ly + fy_, -12, -22, 2.4, 5, 24, (46, 46, 52))
        # estelas
        for ship in (p, e):
            ship['wake'] -= dt
            if abs(ship['v']) > 15 and ship['wake'] <= 0 and ship['sink'] is None:
                ship['wake'] = 0.04
                bx, by = vec(ship['h'], -52)
                self.fx.add('foam', ship['x'] + bx + random.uniform(-5, 5), ship['y'] + by + random.uniform(-5, 5),
                            life=1.8, r0=6, r1=20, col=(230, 245, 255))
        for ship, hpf in ((p, self.hull / 100), (e, e['hp'] / e['max'])):
            if ship['sink'] is None:
                if hpf < .5 and random.random() < dt * 10:
                    self.fx.add('smoke', ship['x'], ship['y'], random.uniform(-8, 8), -25, 2.0, 6, 26, (50, 50, 50))
                if hpf < .25 and random.random() < dt * 14:
                    self.fx.add('glow', ship['x'] + random.uniform(-14, 14), ship['y'] + random.uniform(-30, 30), life=.4,
                                r0=8, r1=22, col=(255, 140, 50))
        # proyectiles
        self.update_missiles(dt)
        # hundimientos
        for ship, key in ((e, 'e'), (p, 'p')):
            if ship['sink'] is not None:
                ship['sink'] += dt
                ship['v'] *= 0.97
                if int(ship['sink'] * 5) != int((ship['sink'] - dt) * 5):
                    big_ = ship is e and c['is_boss']
                    self.fx.explode(ship['x'] + random.uniform(-30, 30) * (1.5 if big_ else 0.5), ship['y'] + random.uniform(-110, 110) if big_ else ship['y'] + random.uniform(-40, 40), 1.5 if big_ else 0.9, big_)
                    self.audio.play('boom_s', .6)
                    self.shake = max(self.shake, 7)
        if e['sink'] is None and e['hp'] <= 0:
            e['sink'] = 0.0
            self.audio.play('boom_l')
            self.fx.explode(e['x'], e['y'], 3.0 if c['is_boss'] else 1.8, True)
        if p['sink'] is None and self.hull <= 0:
            p['sink'] = 0.0
            self.audio.play('boom_l')
            self.fx.explode(p['x'], p['y'], 1.8, True)
        self.fx.update(dt)
        if e['sink'] is not None and e['sink'] > (4.0 if c['is_boss'] else 2.4):
            boss_kill = c.get('is_boss', False)
            if c['nest']:
                nst = self.enemy_ref
                nst['alive'] = False
                self.add_score(400 + 100 * self.wave)
                self.ammo = min(40, self.ammo + 8)
                self.radar_t = 60.0
                self.toast('¡Batería destruida! +%d  (+8 munición, radar enemigo 60 s)' % (400 + 100 * self.wave), (120, 255, 160))
                if self.hull <= 0:
                    return self.game_over('Tu buque no sobrevivió al combate')
                return self.go('map')
            self.add_score(500 + 100 * self.wave)
            self.ammo = min(40, self.ammo + (15 if boss_kill else 5))
            self.toast('¡%s hundido! +%d  (+%d munición)' % ('Buque jefe' if boss_kill else ('Submarino' if c['sub'] else 'Destructor'), 500 + 100 * self.wave, 15 if boss_kill else 5), (120, 255, 160))
            if self.enemy_ref in self.enemies:
                self.enemies.remove(self.enemy_ref)
            if self.hull <= 0:
                return self.game_over('Tu buque no sobrevivió al combate')
            self.go('map')
        elif p['sink'] is not None and p['sink'] > 2.6:
            self.game_over('Tu buque fue hundido en combate')

    def sub_fire(self):
        """Abanico de 3 torpedos lentos que apuntan a donde va a estar el jugador."""
        c = self.c
        p, e = c['p'], c['e']
        spd = 175 + 6 * self.wave
        T = dist(p['x'], p['y'], e['x'], e['y']) / spd
        vx, vy = vec(p['h'], p['v'])
        base = bearing(p['x'] + vx * T - e['x'], p['y'] + vy * T - e['y'])
        for d in (-8, 0, 8):
            self.launch_missile(e, base + d + random.uniform(-2, 2), spd, 'e', 0.0, (20, 12))
        self.audio.play('launch', .5)

    def enemy_fire(self, mount=None):
        c = self.c
        p, e = c['p'], c['e']
        boss = c['is_boss']
        spd = (232 + 7 * self.wave) if boss else (250 + 8 * self.wave)
        off = BOSS_MOUNTS[mount] if (boss and mount is not None) else 0.0
        ox, oy = vec(e['h'], off)
        T = dist(p['x'], p['y'], e['x'] + ox, e['y'] + oy) / spd
        vx, vy = vec(p['h'], p['v'])
        err = max(2.0, 11 - 1.2 * self.wave)
        ang = bearing(p['x'] + vx * T - e['x'] - ox, p['y'] + vy * T - e['y'] - oy) + random.uniform(-err, err)
        self.launch_missile(e, ang, spd, 'e', off, (18, 10) if boss else ((15, 9) if c['nest'] else (22, 12)))
        self.audio.play('launch', .5)
        self.fx.add('glow', e['x'] + ox, e['y'] + oy, life=.2, r0=22, r1=46, col=(255, 160, 120))

    def ship_hit(self, ship, x, y, boss):
        L, r, core = (108, 36, 56) if boss else (44, 17, 24)
        dx, dy = vec(ship['h'], 1)
        t = clamp((x - ship['x']) * dx + (y - ship['y']) * dy, -L, L)
        hit = dist(x, y, ship['x'] + dx * t, ship['y'] + dy * t) < r
        return hit, dist(x, y, ship['x'], ship['y']) < core

    def update_missiles(self, dt):
        c = self.c
        p, e = c['p'], c['e']
        for s in c['shells'][:]:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['life'] -= dt
            if random.random() < dt * 45:
                bx, by = vec(s['ang'], -14)
                self.fx.add('smoke', s['x'] + bx, s['y'] + by, 0, 0, 0.7, 2, 7, (200, 200, 205))
            tgt = e if s['own'] == 'p' else p
            if tgt['sink'] is None and not (tgt is e and c['sub'] and not e['surf']):
                if tgt is e and c['nest']:
                    dn = dist(s['x'], s['y'], e['x'], e['y'])
                    hit, full = dn < 46, dn < 26
                else:
                    hit, full = self.ship_hit(tgt, s['x'], s['y'], tgt is e and c['is_boss'])
                if hit:
                    c['shells'].remove(s)
                    self.missile_hit(s, tgt, full)
                    continue
            if s['life'] <= 0 or not (-60 < s['x'] < W + 60 and -60 < s['y'] < H + 60):
                c['shells'].remove(s)

    def missile_hit(self, s, tgt, full):
        c = self.c
        x, y = s['x'], s['y']
        if s['own'] == 'p':
            dmg = 3 if full else 2
            c['e']['hp'] -= dmg
            self.pop('-%d' % dmg, x, y - 20, (255, 255, 160))
        else:
            dmg = s['dmg'][0] if full else s['dmg'][1]
            self.hull -= dmg
            self.pop('-%d CASCO' % dmg, x, y - 20, (255, 110, 100))
            self.shake = max(self.shake, 12)
        self.fx.explode(x, y, 1.0 if full else 0.7)
        self.audio.play('hit')

    # ---- combate
    def draw_combat(self, cv):
        c = self.c
        p, e = c['p'], c['e']
        is_boss = c.get('is_boss', False)
        self.draw_ocean(cv, 0, 0, self.t)
        if is_boss:
            glow(cv, e['x'], e['y'], 90 + 20 * math.sin(self.t * 2), (255, 80, 200), 0.35)
        self.fx.draw(cv)
        # buques
        ekey, etur = ('b_hull', self.tur_b) if is_boss else (('s_hull', self.tur_e) if c['sub'] else ('e_hull', self.tur_e))
        for ship, key, tur in ((e, ekey, etur), (p, 'p_hull', self.tur_p)):
            alpha = 255
            if ship['sink'] is not None:
                k0, k1 = (1.8, 2.2) if (ship is e and is_boss) else (1.0, 1.4)
                alpha = int(255 * clamp(1 - (ship['sink'] - k0) / k1, 0, 1))
            if ship is e and c['nest']:
                spr = self.nest_gfx()
                spr.set_alpha(255 if ship['sink'] is None else 255 - int(150 * clamp(ship['sink'] / 2.0, 0, 1)))
                cv.blit(spr, (e['x'] - spr.get_width() // 2, e['y'] - spr.get_height() // 2))
                if ship['sink'] is None:
                    self.blit_turret(cv, self.tur_e, e['x'], e['y'] - 4, bearing(p['x'] - e['x'], p['y'] - e['y']))
                continue
            if alpha > 0:
                if key == 's_hull':
                    alpha = int(alpha * (1.0 if e['surf'] else 0.3))
                    if not e['surf']:
                        draw_circ(cv, e['x'], e['y'], 70 + 6 * math.sin(self.t * 3), (120, 230, 220), 40, 2)
                self.blit_ship(cv, key, ship['x'], ship['y'], ship['h'], alpha=alpha)
                if key == 's_hull':
                    continue
                if key == 'b_hull':
                    for mi, off in enumerate(BOSS_MOUNTS):
                        mx_, my_ = vec(ship['h'], off)
                        ang = bearing(p['x'] - (ship['x'] + mx_), p['y'] - (ship['y'] + my_))
                        self.blit_turret(cv, self.tur_b2 if mi == 2 else self.tur_b, ship['x'] + mx_, ship['y'] + my_, ang, alpha)
                    if ship['sink'] is None:
                        rx, ry = vec(ship['h'], 6)
                        ra = math.radians(self.t * 130)
                        pygame.draw.line(cv, (150, 235, 255), (ship['x'] + rx, ship['y'] + ry),
                                         (ship['x'] + rx + math.cos(ra) * 22, ship['y'] + ry + math.sin(ra) * 22), 2)
                        pygame.draw.circle(cv, (150, 235, 255), (int(ship['x'] + rx), int(ship['y'] + ry)), 4)
                        if int(self.t * 2) % 2 == 0:
                            glow(cv, ship['x'] + rx, ship['y'] + ry, 22, (255, 60, 50))
                    continue
                fx_, fy_ = vec(ship['h'], {'p_hull': 124, 'e_hull': 112}[key] * 0.23)
                if ship is p:
                    tx_, ty_ = self.combat_aim()
                else:
                    tx_, ty_ = p['x'], p['y']
                ang = bearing(tx_ - (ship['x'] + fx_), ty_ - (ship['y'] + fy_))
                self.blit_turret(cv, tur, ship['x'] + fx_, ship['y'] + fy_, ang, alpha)
        # misiles (vuelan en línea recta)
        for s in c['shells']:
            col = (255, 240, 160) if s['own'] == 'p' else (255, 150, 120)
            hx, hy = vec(s['ang'], 16)
            tx_, ty_ = vec(s['ang'], -16)
            glow(cv, s['x'] + tx_, s['y'] + ty_, 16, (255, 170, 70))
            pygame.draw.line(cv, (70, 74, 84), (s['x'] + tx_, s['y'] + ty_), (s['x'] + hx, s['y'] + hy), 8)
            pygame.draw.line(cv, (226, 230, 236), (s['x'] + tx_, s['y'] + ty_), (s['x'] + hx, s['y'] + hy), 5)
            pygame.draw.circle(cv, (230, 70, 56) if s['own'] == 'e' else (255, 210, 70), (int(s['x'] + hx), int(s['y'] + hy)), 5)
            fx2, fy2 = vec(s['ang'] + 90, 5)
            pygame.draw.line(cv, col, (s['x'] + tx_ + fx2, s['y'] + ty_ + fy2), (s['x'] + tx_ - fx2, s['y'] + ty_ - fy2), 2)
        # mira
        ax, ay = self.combat_aim()
        pygame.draw.line(cv, (120, 150, 190), (p['x'], p['y']), (ax, ay), 1)
        pygame.draw.circle(cv, (255, 230, 120), (int(ax), int(ay)), 16, 2)
        pygame.draw.circle(cv, (255, 230, 120), (int(ax), int(ay)), 2)
        for dx, dy in ((-26, 0), (26, 0), (0, -26), (0, 26)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        pygame.draw.circle(cv, (70, 100, 135), (int(p['x']), int(p['y'])), 650, 1)
        # HUD
        self.draw_hud(cv)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        if is_boss:
            self.text(cv, 'ACORAZADO %s' % c['name'], self.f_m, (255, 110, 220), W // 2, 16, 'c')
        elif c['nest']:
            self.text(cv, 'BATERÍA COSTERA', self.f_m, (255, 140, 120), W // 2, 16, 'c')
        elif c['sub']:
            self.text(cv, 'SUBMARINO - %s' % ('EMERGIDO: ¡DISPARALE!' if e['surf'] else 'SUMERGIDO (invulnerable)'), self.f_m,
                      (255, 220, 120) if e['surf'] else (120, 230, 220), W // 2, 16, 'c')
        else:
            self.text(cv, 'DESTRUCTOR ENEMIGO', self.f_m, (255, 140, 120), W // 2, 16, 'c')
        self.bar(cv, W // 2 - 210, 44, 420, 26, e['hp'] / e['max'], (240, 80, 70), 'BATERÍA' if c['nest'] else 'CASCO ENEMIGO')
        rl = 1 - clamp(p['cool'] / 0.9, 0, 1)
        pygame.draw.rect(cv, (8, 12, 24), (W // 2 - 60, H - 40, 120, 10))
        pygame.draw.rect(cv, (120, 255, 160) if rl >= 1 else (255, 200, 80), (W // 2 - 59, H - 39, int(118 * rl), 8))
        self.text(cv, 'Clic/ESPACIO: misil recto (adelantate al objetivo)  |  E huir', self.f_s, (200, 220, 255), W // 2, H - 64, 'c')
