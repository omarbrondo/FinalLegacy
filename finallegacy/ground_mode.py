"""Combate de infantería cenital: invasión, desembarco con sigilo y defensa de antenas."""
import math
import pygame
import random
from .common import (
    ARENA_R, EXTRA_ISLANDS, H, LANDING_ENEMIES,
    LAND_R, MAX_LANDING_ATTEMPTS, PLAYER_HP, Particles,
    W, WIN_WAVE, angle_diff, bearing,
    clamp, coast_r, dist, draw_circ,
    glow, lerp, vec)
from .sprites import ENEMY_TYPES, draw_cover


class GroundMixin:
    # ---------------------------------------------------------- COMBATE DE INFANTERÍA
    def isl_name(self, i):
        return 'ISLA %d' % (i + 1)

    def make_ground(self, seed, R, city_seed=None, antenna=False):
        ext = int(R * 2.0)
        s = pygame.Surface((ext * 2, ext * 2), pygame.SRCALPHA)
        self.paint_island(s, ext, ext, R, seed, True)
        if antenna:
            cx, cy = ext, ext
            pygame.draw.circle(s, (0, 0, 0, 70), (cx + 5, cy + 7), 64)
            pygame.draw.circle(s, (150, 152, 150), (cx, cy), 60)
            pygame.draw.circle(s, (186, 190, 192), (cx, cy), 55)
            for k in range(8):
                a = 6.2832 * k / 8 + 0.4
                pygame.draw.line(s, (96, 100, 104), (cx, cy), (cx + math.cos(a) * 52, cy + math.sin(a) * 52), 3)
                pygame.draw.circle(s, (70, 74, 78), (int(cx + math.cos(a) * 52), int(cy + math.sin(a) * 52)), 5)
            pygame.draw.circle(s, (110, 116, 122), (cx, cy), 22)
            pygame.draw.circle(s, (230, 70, 60), (cx, cy), 9)
            pygame.draw.circle(s, (255, 190, 170), (cx - 2, cy - 2), 3)
            for rr in (30, 42):
                pygame.draw.circle(s, (120, 230, 255), (cx, cy), rr, 1)
        elif city_seed is not None:
            cs = self.make_city(int(R * 0.7), city_seed, False)
            s.blit(cs, (ext - cs.get_width() // 2, ext - cs.get_height() // 2))
        else:
            cx, cy = ext, ext
            pygame.draw.circle(s, (0, 0, 0, 60), (cx + 4, cy + 6), 50)
            pygame.draw.circle(s, (150, 152, 150), (cx, cy), 48)
            pygame.draw.circle(s, (196, 198, 194), (cx, cy), 44)
            for k in range(20):
                a0, a1 = 6.2832 * k / 20, 6.2832 * (k + 1) / 20
                pts = [(cx + math.cos(a) * rr, cy + math.sin(a) * rr) for rr in (36, 42) for a in (a0, a1)]
                pygame.draw.polygon(s, (240, 200, 40) if k % 2 else (40, 40, 44), [pts[0], pts[1], pts[3], pts[2]])
            pygame.draw.circle(s, (130, 134, 134), (cx, cy), 30)
            pygame.draw.circle(s, (92, 96, 98), (cx, cy), 30, 2)
            pygame.draw.line(s, (92, 96, 98), (cx - 24, cy), (cx + 24, cy), 2)
            pygame.draw.line(s, (92, 96, 98), (cx, cy - 24), (cx, cy + 24), 2)
        return s, (W // 2 - ext, H // 2 - ext)

    def gen_covers(self, seed, R, n, avoid):
        covers = []
        for _ in range(500):
            if len(covers) >= n:
                break
            a = random.uniform(0, 6.2832)
            d = random.uniform(0.24, 0.74) * coast_r(R, seed, a, 1.0)
            x, y = W / 2 + math.cos(a) * d, H / 2 + math.sin(a) * d
            kind = random.choice(('sandbag', 'sandbag', 'rock', 'crates'))
            r = 24 if kind == 'sandbag' else 22
            if any(dist(x, y, c['x'], c['y']) < c['r'] + r + 46 for c in covers):
                continue
            if any(dist(x, y, ax, ay) < r + ar for ax, ay, ar in avoid):
                continue
            covers.append(dict(x=x, y=y, r=r, kind=kind, seed=random.randrange(10 ** 6)))
        return covers

    def init_ground(self, mode, seed, city, covers_n, avoid, spawn, kinds, queue=None, island_idx=None, R=ARENA_R, antenna=None):
        land, off = self.make_ground(seed, R, seed if mode == 'invasion' else None, antenna is not None)
        covers = self.gen_covers(seed, R, covers_n, avoid + [(spawn[0], spawn[1], 90)])
        for c in covers:
            draw_cover(land, dict(c, x=c['x'] - off[0], y=c['y'] - off[1]))
        self.fx = Particles()
        self.g = dict(mode=mode, city=city, R=R, seed=seed, land=land.convert_alpha(), land_off=off, cam=[0.0, 0.0], covers=covers,
                      angs=[random.uniform(0, 6.28) for _ in range(3)], queue=queue or [], enemies=[], bullets=[],
                      nades=[], corpses=[], decals=[], boats=[], crates=[], t=0.0, total=len(kinds), kills=0,
                      phase='play', pt=0.0, city0=city['hp'], fail=False, island_idx=island_idx, hurt=0.0, antenna=antenna,
                      stealth=(mode == 'landing'), last_seen=(W / 2, H / 2), alert_t=0.0, alerts=0, cams=[], inst=0.0, takedowns=0, info_t=0.0,
                      limit=0.0, tleft=0.0, reinf_t=0.0, reinf_n=0,
                      ant_t=0.0, spawn=spawn,
                      p=dict(x=float(spawn[0]), y=float(spawn[1]), h=0.0, vx=0.0, vy=0.0, hp=PLAYER_HP, mag=30, reload=0.0,
                             cd=0.0, gren=4, gcd=0.0, ph=0.0, flash=0.0, bloom=0.0, dead=False, dead_t=0.0,
                             wpn='rifle', pmag=12, sneak=False, noise=0.0, noise_r=0.0, noise_t=0.0))
        self.aim = [W / 2, 200.0]
        self.g_camera(0.0, True)
        self.go('ground')
        return covers

    def new_soldier(self, kind, x, y, h, state, mode, cover=None):
        hp = ENEMY_TYPES[kind]['hp'] + self.wave // 2
        return dict(x=x, y=y, h=h, h0=h, kind=kind, hp=float(hp), max=float(hp), cd=random.uniform(0.6, 1.6),
                    state=state, mode=mode, cover=cover, ph=0.0, ph0=random.uniform(0, 6.28), flash=0.0, hit=0.0,
                    burst=0, bcd=0.0, tele=0.0, aimlock=h, strafe=random.choice((-1, 1)), strafe_t=random.uniform(1, 3),
                    role='guard', wp=None, wpi=0, pause=0.0, excl=0.0, det=0.0, spot=None, st=0.0)

    def start_landing(self, island_idx):
        x, y, r, s = EXTRA_ISLANDS[island_idx]
        if self.landing_attempts[island_idx] >= MAX_LANDING_ATTEMPTS:
            self.toast('Sin intentos de desembarco en esta isla', (255, 140, 90))
            return
        self.landing_attempts[island_idx] += 1
        n = LANDING_ENEMIES
        n_mg, n_gr = max(1, n // 5), max(1, n // 5)
        n_sn = min(self.wave - 2, 2) if self.wave >= 3 else 0
        kinds = ['mg'] * n_mg + ['gren'] * n_gr + ['sniper'] * n_sn + ['rifle'] * (n - n_mg - n_gr - n_sn)
        sy = H / 2 + coast_r(LAND_R, s, math.pi / 2, 0.84)
        spawn = (W / 2, sy)
        city = dict(name=self.isl_name(island_idx), x=x, y=y, r=r, hp=100.0, dead=False, seed=s)
        covers = self.init_ground('landing', s, city, 16, [(W / 2, H / 2, 80)], spawn, kinds, island_idx=island_idx, R=LAND_R)
        self.g['limit'] = self.g['tleft'] = float(max(110, 190 - 12 * (self.wave - 1)))
        self.g['reinf_t'] = 30.0
        g = self.g
        random.shuffle(kinds)
        order = sorted(range(len(covers)), key=lambda i: -dist(covers[i]['x'], covers[i]['y'], spawn[0], spawn[1]))
        for i, kd in enumerate(kinds):
            ci = order[i % len(order)] if covers else None
            if ci is not None:
                c = covers[ci]
                away = bearing(c['x'] - spawn[0], c['y'] - spawn[1]) + (0 if i < len(order) else random.choice((-55, 55)))
                ox, oy = vec(away, c['r'] + 12)
                ex, ey = c['x'] + ox, c['y'] + oy
            else:
                ex, ey = W / 2, H / 2 - 100
            d = dist(ex, ey, W / 2, H / 2) or 1.0
            lim = coast_r(LAND_R, s, math.atan2(ey - H / 2, ex - W / 2), 0.9)
            if d > lim:
                ex, ey = W / 2 + (ex - W / 2) / d * lim, H / 2 + (ey - H / 2) / d * lim
            mode = 'pusher' if kd == 'rifle' and random.random() < 0.35 else 'defender'
            e = self.new_soldier(kd, ex, ey, bearing(spawn[0] - ex, spawn[1] - ey), 'hold', mode, ci)
            g['enemies'].append(e)
        # centinelas: patrullan con un cono de visión; si te ven dan la alarma y llegan refuerzos
        rifles = [e for e in g['enemies'] if e['kind'] == 'rifle']
        random.shuffle(rifles)
        for e in rifles[:max(2, n // 3)]:
            e['role'] = 'sentry'
            L = random.uniform(130, 210)
            ox, oy = vec(random.uniform(0, 360), L)
            tx, ty = e['x'] + ox, e['y'] + oy
            d = dist(tx, ty, W / 2, H / 2) or 1.0
            lim = coast_r(LAND_R, s, math.atan2(ty - H / 2, tx - W / 2), 0.82)
            if d > lim:
                tx, ty = W / 2 + (tx - W / 2) / d * lim, H / 2 + (ty - H / 2) / d * lim
            e['wp'] = [(e['x'], e['y']), (tx, ty)]
            e['h0'] = e['h'] = bearing(tx - e['x'], ty - e['y'])
        for k_ in range(2):
            a_ = random.uniform(0, 6.28)
            rr = coast_r(LAND_R, s, a_, 0.62)
            cx0, cy0 = W / 2 + math.cos(a_) * rr, H / 2 + math.sin(a_) * rr
            base_ = bearing(W / 2 - cx0, H / 2 - cy0)
            g['cams'].append(dict(x=cx0, y=cy0, base=base_, h=base_, sw=random.uniform(0, 6.28), det=0.0, hp=3, on=True))
        g['total'] = len(g['enemies'])
        left = MAX_LANDING_ATTEMPTS - self.landing_attempts[island_idx]
        self.banner('¡DESEMBARCO EN %s!' % self.isl_name(island_idx),
                    'Tenés %d s: llegá a la antena (centro) y mantené E, o eliminá a los %d soldados  |  Intentos: %d' % (self.g['limit'], n, left),
                    (100, 180, 255), 4.6)
        self.toast('SHIFT: sigilo | Q: pistola silenciada | E: noquear por la espalda / instalar antena', (255, 220, 120))

    def start_ground(self, city, antenna=None):
        n = min(8 + 3 * self.wave, 26)
        if antenna is not None:
            n = max(7, int(n * 0.8))
        n_mg = min(n // 6, 1 + self.wave // 2)
        n_gr = min(n // 5, 1 + self.wave // 2)
        n_sn = min(self.wave - 2, 3) if self.wave >= 3 else 0
        n_dog = min(self.wave, 5) if self.wave >= 2 else 0
        kinds = ['mg'] * n_mg + ['gren'] * n_gr + ['sniper'] * n_sn + ['dog'] * n_dog + ['rifle'] * max(2, n - n_mg - n_gr - n_sn - n_dog)
        random.shuffle(kinds)
        queue = sorted([(random.uniform(0.5, 6 + n * 1.1), k, random.randrange(3)) for k in kinds], key=lambda q: q[0])
        spawn = (W / 2, H / 2 + 175)
        self.init_ground('invasion', city['seed'], city, 7, [(W / 2, H / 2, 150)], spawn, kinds, queue, antenna=antenna)
        if antenna is not None:
            self.banner('¡ASALTO A LA ANTENA!', 'Defendé %s | Clic: disparar | ESPACIO: granada | R: recargar' % city['name'],
                        (120, 220, 255), 3.8)
        else:
            self.banner('¡INVASIÓN ANFIBIA!', 'Defendé %s | Clic: disparar | ESPACIO: granada | R: recargar' % city['name'],
                        (255, 150, 60), 3.8)

    def spawn_ground_enemy(self, kind, idx):
        g = self.g
        a = g['angs'][idx]
        r = coast_r(g['R'], g['seed'], a, 0.97)
        x, y = W / 2 + math.cos(a) * r, H / 2 + math.sin(a) * r
        e = self.new_soldier(kind, x, y, bearing(W / 2 - x, H / 2 - y), 'combat', 'pusher')
        g['enemies'].append(e)
        g['boats'].append([x + math.cos(a) * 55, y + math.sin(a) * 55, bearing(-math.cos(a), -math.sin(a)), 0.0])
        self.fx.splash(x + math.cos(a) * 40, y + math.sin(a) * 40, 0.8)

    def g_camera(self, dt, snap=False):
        g = self.g
        p, R = g['p'], g['R']
        cam = g['cam']
        for i, (c, lim, size) in enumerate(((p['x'], W / 2, W), (p['y'], H / 2, H))):
            lo, hi = lim - R * 1.1, lim + R * 1.1 - size
            tgt = (lo + hi) / 2 if hi < lo else clamp(c - size / 2, lo, hi)
            cam[i] = tgt if snap else cam[i] + (tgt - cam[i]) * min(1.0, dt * 6)

    def gpop(self, s, x, y, col=(255, 255, 160)):
        cam = self.g['cam']
        self.pop(s, x - cam[0], y - cam[1], col)

    def ground_aim(self):
        g = self.g
        p, cam = g['p'], g['cam']
        ax, ay = self.aim[0] + cam[0], self.aim[1] + cam[1]
        if not self.mouse_moved:
            fx, fy = vec(p['h'], 320)
            ax, ay = p['x'] + fx, p['y'] + fy
        lim = g['R'] * 1.1
        return clamp(ax, W / 2 - lim, W / 2 + lim), clamp(ay, H / 2 - lim, H / 2 + lim)

    def g_step(self, s, dx, dy, is_player=False):
        g = self.g
        s['x'] += dx
        s['y'] += dy
        for c in g['covers']:
            d = dist(s['x'], s['y'], c['x'], c['y']) or 1.0
            m = c['r'] + 11
            if d < m:
                s['x'] = c['x'] + (s['x'] - c['x']) / d * m
                s['y'] = c['y'] + (s['y'] - c['y']) / d * m
        cx, cy = W / 2, H / 2
        d = dist(s['x'], s['y'], cx, cy) or 1.0
        lim = coast_r(g['R'], g['seed'], math.atan2(s['y'] - cy, s['x'] - cx), 0.92)
        if d > lim:
            s['x'], s['y'] = cx + (s['x'] - cx) / d * lim, cy + (s['y'] - cy) / d * lim
        elif is_player and g['mode'] == 'invasion' and d < 62:
            s['x'], s['y'] = cx + (s['x'] - cx) / d * 62, cy + (s['y'] - cy) / d * 62

    def g_ign(self, x, y):
        return {i for i, c in enumerate(self.g['covers']) if dist(x, y, c['x'], c['y']) < c['r'] + 16}

    def g_los(self, x0, y0, x1, y1):
        ign = self.g_ign(x0, y0)
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy or 1.0
        for i, c in enumerate(self.g['covers']):
            if i in ign:
                continue
            t = clamp(((c['x'] - x0) * vx + (c['y'] - y0) * vy) / L2, 0, 1)
            if dist(c['x'], c['y'], x0 + vx * t, y0 + vy * t) < c['r'] * 0.85:
                return False
        return True

    def alert(self, e, alarm=False):
        g = self.g
        if e['state'] == 'combat':
            return
        e['state'] = 'combat'
        e['excl'] = 1.0
        e['det'] = 1.0
        e['cd'] = max(e['cd'], random.uniform(0.9, 1.7))
        if g['stealth'] and alarm:
            if g['alert_t'] <= 0:
                g['alerts'] += 1
                self.audio.play('alarm', .5)
                self.banner('¡ALERTA!', 'Te descubrieron: escondete para recuperar el sigilo', (255, 90, 70), 2.6)
            g['alert_t'] = 30.0
        for o in g['enemies']:
            if o['state'] in ('hold', 'susp') and dist(o['x'], o['y'], e['x'], e['y']) < ((520 if g['stealth'] else 300) if alarm else 110):
                o['state'] = 'combat'
                o['excl'] = 1.0
                o['det'] = 1.0
                o['cd'] = max(o['cd'], random.uniform(0.9, 2.4 if alarm else 1.7))
        if alarm and g['mode'] == 'landing' and not g.get('alarm'):
            g['alarm'] = True
            self.audio.play('alarm', .4)
            self.toast('¡ALARMA! Llegan refuerzos', (255, 110, 90))
            for i in range(2):
                g['queue'].append((g['t'] + 5.0 + 3.0 * i, 'rifle', random.randrange(3)))
            g['total'] += 2

    def g_noise(self, radius, secs=0.3):
        """El jugador hace ruido: los enemigos dentro del radio lo oyen."""
        p = self.g['p']
        if radius >= p['noise_r'] or p['noise_t'] <= 0:
            p['noise_r'], p['noise_t'] = radius, secs

    def takedown(self):
        """Noqueo silencioso por la espalda."""
        g = self.g
        p = g['p']
        if p['dead'] or g['phase'] != 'play' or not g['stealth']:
            return False
        best = None
        for e in g['enemies']:
            if e['state'] == 'combat':
                continue
            d = dist(e['x'], e['y'], p['x'], p['y'])
            if d < 46 and abs(angle_diff(e['h'], bearing(p['x'] - e['x'], p['y'] - e['y']))) > 105 and (best is None or d < best[0]):
                best = (d, e)
        if best is None:
            return False
        e = best[1]
        g['takedowns'] += 1
        g['tleft'] += 8.0
        self.gpop('+8 s', p['x'], p['y'] - 44, (140, 255, 200))
        self.audio.play('blip', .6)
        self.gpop('SILENCIOSO', e['x'], e['y'] - 28, (140, 255, 200))
        self.kill_ground_enemy(e)
        p['h'] = bearing(e['x'] - p['x'], e['y'] - p['y'])
        return True

    def start_reload(self):
        p = self.g['p']
        full = 12 if p['wpn'] == 'pistol' else 30
        if p['dead'] or p['reload'] > 0 or (p['pmag'] if p['wpn'] == 'pistol' else p['mag']) >= full:
            return
        p['reload'] = 1.0 if p['wpn'] == 'pistol' else 1.3
        self.audio.play('blip', .6)

    def player_shoot(self):
        g = self.g
        p = g['p']
        if p['dead'] or p['reload'] > 0 or p['cd'] > 0 or g['phase'] != 'play':
            return
        if p['wpn'] == 'pistol':
            if p['pmag'] <= 0:
                self.start_reload()
                return
            p['pmag'] -= 1
            p['cd'] = 0.34
            ang = p['h'] + random.uniform(-1, 1) * 1.2
            mx, my = vec(p['h'], 34)
            vx, vy = vec(ang, 640)
            g['bullets'].append(dict(x=p['x'] + mx, y=p['y'] + my, vx=vx, vy=vy, own='p', dmg=2.2, life=0.7, silent=True, ign=self.g_ign(p['x'], p['y'])))
            self.audio.play('blip', .18)
            self.g_noise(85, 0.25)
            return
        if p['mag'] <= 0:
            self.start_reload()
            return
        self.g_noise(430, 0.4)
        p['mag'] -= 1
        p['cd'] = 0.1
        p['flash'] = 0.06
        p['bloom'] = min(6.0, p['bloom'] + 0.8)
        ang = p['h'] + random.uniform(-1, 1) * (1.0 + p['bloom'])
        mx, my = vec(p['h'], 40)
        vx, vy = vec(ang, 580)
        g['bullets'].append(dict(x=p['x'] + mx, y=p['y'] + my, vx=vx, vy=vy, own='p', dmg=1.0, life=0.85,
                                 ign=self.g_ign(p['x'], p['y'])))
        self.audio.play('mg', .3)
        ex, ey = vec(p['h'] + 90, 12)
        self.fx.add('spark', p['x'] + ex, p['y'] + ey, ex * 12, ey * 12 - 30, 0.4, col=(230, 190, 80), drag=2, grav=120)
        for e in g['enemies']:
            if e['state'] in ('hold', 'susp') and dist(e['x'], e['y'], p['x'], p['y']) < 230:
                self.alert(e, alarm=g['stealth'])

    def throw_grenade_p(self):
        g = self.g
        p = g['p']
        if p['dead'] or p['gren'] <= 0 or p['gcd'] > 0 or g['phase'] != 'play':
            return
        p['gren'] -= 1
        p['gcd'] = 0.7
        self.g_noise(300, 0.4)
        ax, ay = self.ground_aim()
        d = clamp(dist(p['x'], p['y'], ax, ay), 80, 330)
        tx, ty = vec(p['h'], d)
        g['nades'].append(dict(x0=p['x'], y0=p['y'], x1=p['x'] + tx, y1=p['y'] + ty, t=0.0, T=d / 240 + 0.35, own='p'))
        self.audio.play('blip', .8)
        for e in g['enemies']:
            if e['state'] in ('hold', 'susp') and dist(e['x'], e['y'], p['x'], p['y']) < 300:
                self.alert(e, alarm=g['stealth'])

    def enemy_shoot(self, e, aim, spread, speed, dmg):
        g = self.g
        a = aim + random.uniform(-spread, spread)
        mx, my = vec(a, 40)
        vx, vy = vec(a, speed)
        g['bullets'].append(dict(x=e['x'] + mx, y=e['y'] + my, vx=vx, vy=vy, own='e', dmg=dmg, life=1.3,
                                 ign=self.g_ign(e['x'], e['y'])))
        e['flash'] = 0.06
        e['h'] = aim
        if dist(e['x'], e['y'], g['p']['x'], g['p']['y']) < 560:
            self.audio.play('mg', .2)

    def enemy_throw(self, e):
        g = self.g
        p = g['p']
        lim_ = g['R'] * 1.0
        tx = clamp(p['x'] + p['vx'] * 0.5 + random.uniform(-24, 24), W / 2 - lim_, W / 2 + lim_)
        ty = clamp(p['y'] + p['vy'] * 0.5 + random.uniform(-24, 24), H / 2 - lim_, H / 2 + lim_)
        d = dist(e['x'], e['y'], tx, ty)
        g['nades'].append(dict(x0=e['x'], y0=e['y'], x1=tx, y1=ty, t=0.0, T=clamp(d / 230, 0.8, 1.7), own='e'))
        e['h'] = bearing(tx - e['x'], ty - e['y'])
        self.audio.play('blip', .5)

    def explode_nade(self, n):
        g = self.g
        p = g['p']
        x, y, R = n['x1'], n['y1'], 62
        self.fx.explode(x, y, 1.1, True)
        self.audio.play('boom_s', .7)
        self.shake = max(self.shake, 7)
        g['decals'].append((x, y, R * 0.55))
        g['decals'] = g['decals'][-40:]
        for e in g['enemies'][:]:
            d = dist(x, y, e['x'], e['y'])
            if d < R:
                e['hp'] -= (6.5 if n['own'] == 'p' else 2.0) * (1 - 0.45 * d / R)
                e['hit'] = 0.15
                if e['state'] in ('hold', 'susp'):
                    self.alert(e)
                if e['hp'] <= 0:
                    self.kill_ground_enemy(e)
        d = dist(x, y, p['x'], p['y'])
        if not p['dead'] and d < R:
            dmg = int(32 * (1 - 0.6 * d / R))
            self.hurt_player(dmg)

    def hurt_player(self, dmg):
        g = self.g
        p = g['p']
        if p['dead'] or g['phase'] != 'play':
            return
        p['hp'] -= dmg
        g['hurt'] = 0.5
        self.shake = max(self.shake, 4 + dmg * 0.5)
        self.audio.play('hit', .5)
        self.gpop('-%d' % dmg, p['x'], p['y'] - 22, (255, 110, 100))

    def kill_ground_enemy(self, e):
        g = self.g
        if e not in g['enemies']:
            return
        g['enemies'].remove(e)
        g['kills'] += 1
        pts = ENEMY_TYPES[e['kind']]['pts']
        self.add_score(pts)
        self.gpop('+%d' % pts, e['x'], e['y'] - 18)
        if e['kind'] != 'dog':
            g['corpses'].append(dict(x=e['x'], y=e['y'], h=e['h'] + random.uniform(-60, 60), kind=e['kind'], age=0.0))
            g['corpses'] = g['corpses'][-30:]
        self.fx.add('glow', e['x'], e['y'], life=.25, r0=8, r1=22, col=(255, 160, 90))
        for _ in range(6):
            a = random.uniform(0, 6.28)
            self.fx.add('spark', e['x'], e['y'], math.cos(a) * 110, math.sin(a) * 110, 0.35, col=(255, 200, 120), drag=2)
        if random.random() < 0.28:
            g['crates'].append(dict(x=e['x'], y=e['y'], t=0.0, kind=random.choice(('med', 'gren'))))

    def mv(self, e, ang, speed, dt):
        dx, dy = vec(ang, speed * dt)
        self.g_step(e, dx, dy)
        e['ph'] += speed * dt / 9.0

    def ai_soldier(self, e, dt):
        g = self.g
        p = g['p']
        T = ENEMY_TYPES[e['kind']]
        alive = not p['dead']
        e['cd'] -= dt
        e['flash'] = max(0.0, e['flash'] - dt)
        e['hit'] = max(0.0, e['hit'] - dt)
        dp = dist(e['x'], e['y'], p['x'], p['y']) if alive else 9999.0
        e['excl'] = max(0.0, e['excl'] - dt)
        if e['kind'] == 'dog':
            tx, ty = (p['x'], p['y']) if alive else (W / 2, H / 2)
            hd = bearing(tx - e['x'], ty - e['y'])
            e['h'] = (e['h'] + clamp(angle_diff(e['h'], hd), -600 * dt, 600 * dt)) % 360
            if dp > 26 or not alive:
                if not alive and dist(e['x'], e['y'], tx, ty) < 90:
                    if g['mode'] == 'invasion' and not g['city']['dead'] and g['phase'] == 'play':
                        g['city']['hp'] = max(0.0, g['city']['hp'] - 0.4 * dt)
                else:
                    self.mv(e, hd + 20 * math.sin(g['t'] * 7 + e['ph0']), T['speed'] * (1 + 0.02 * self.wave), dt)
            elif e['cd'] <= 0:
                e['cd'] = random.uniform(*T['rate'])
                self.hurt_player(T['dmg'])
                self.audio.play('hit', .4)
            return
        if e['state'] in ('hold', 'susp'):
            sentry = e['role'] == 'sentry'
            if e['state'] == 'susp':
                e['st'] -= dt
                tx, ty = e['spot']
                if dist(e['x'], e['y'], tx, ty) > 16:
                    hd = bearing(tx - e['x'], ty - e['y'])
                    self.mv(e, hd, T['speed'] * 0.55, dt)
                    e['h'] = (e['h'] + clamp(angle_diff(e['h'], hd), -320 * dt, 320 * dt)) % 360
                else:
                    e['h'] = (e['h'] + 80 * math.sin(g['t'] * 2.4 + e['ph0']) * dt) % 360
                if e['st'] <= 0 and e['det'] < 0.25:
                    e['state'] = 'hold'
            elif sentry:
                e['pause'] -= dt
                if e['pause'] > 0:
                    e['h'] = (e['h'] + 55 * math.sin(g['t'] * 1.6 + e['ph0']) * dt) % 360
                else:
                    tx, ty = e['wp'][e['wpi']]
                    if dist(e['x'], e['y'], tx, ty) < 10:
                        e['wpi'] ^= 1
                        e['pause'] = random.uniform(1.0, 2.4)
                    else:
                        hd = bearing(tx - e['x'], ty - e['y'])
                        self.mv(e, hd, T['speed'] * 0.45, dt)
                        e['h'] = (e['h'] + clamp(angle_diff(e['h'], hd), -260 * dt, 260 * dt)) % 360
            else:
                e['h'] = (e['h0'] + 38 * math.sin(g['t'] * 0.7 + e['ph0'])) % 360
            if alive:
                rng, fov = (340, 110) if sentry else (240, 90)
                if p['sneak']:
                    rng *= 0.7
                seen = False
                q = 0.0
                if dp < rng:
                    if dp < 60 or (abs(angle_diff(e['h'], bearing(p['x'] - e['x'], p['y'] - e['y']))) < fov / 2
                                   and self.g_los(e['x'], e['y'], p['x'], p['y'])):
                        seen = True
                        q = 1.0 - dp / rng
                if not g['stealth']:
                    if seen:
                        self.alert(e, alarm=sentry)
                    return
                if seen:
                    e['det'] += dt * (0.55 + 1.9 * q) * (1.7 if g['alert_t'] > 0 else 1.0)
                    e['spot'] = (p['x'], p['y'])
                    e['st'] = 7.0
                else:
                    e['det'] = max(0.0, e['det'] - dt * 0.3)
                    if p['noise'] > dp and p['noise_t'] > 0:
                        e['det'] += dt * 0.7
                        e['spot'] = (p['x'], p['y'])
                        e['st'] = 7.0
                if e['det'] >= 1.0:
                    self.alert(e, alarm=True)
                elif e['det'] > 0.3 and e['state'] == 'hold':
                    e['state'] = 'susp'
                    e['spot'] = e['spot'] or (p['x'], p['y'])
                    e['st'] = 7.0
                    e['excl'] = 0.0
                    self.audio.play('ping', .3)
            return
        px, py = p['x'], p['y']
        if g['stealth'] and alive and e['state'] == 'combat' and not (dp < 560 and self.g_los(e['x'], e['y'], px, py)):
            px, py = g['last_seen']
            dp = dist(e['x'], e['y'], px, py)
            sp0 = T['speed'] * (1 + 0.03 * self.wave) * 0.8
            if dp > 36:
                hd = bearing(px - e['x'], py - e['y'])
                self.mv(e, hd, sp0, dt)
                e['h'] = (e['h'] + clamp(angle_diff(e['h'], hd), -420 * dt, 420 * dt)) % 360
            else:
                e['h'] = (e['h'] + 110 * math.sin(g['t'] * 2.0 + e['ph0']) * dt) % 360
            return
        sp = T['speed'] * (1 + 0.03 * self.wave)
        los = alive and dp < T['range'] and self.g_los(e['x'], e['y'], px, py)
        to_p = bearing(px - e['x'], py - e['y']) if alive else e['h']
        e['strafe_t'] -= dt
        if e['strafe_t'] <= 0:
            e['strafe'] *= -1
            e['strafe_t'] = random.uniform(1.2, 3.2)
        moving = None
        if e['kind'] == 'sniper':
            if dp < 340:
                moving, sp = to_p + 180, sp * 1.4
            elif dp > 520 or not los:
                moving = to_p
            else:
                sp = 0
        elif g['mode'] == 'invasion':
            dcx, dcy = W / 2 - e['x'], H / 2 - e['y']
            dc = math.hypot(dcx, dcy)
            if dc > 96:
                if not (los and dp < T['range'] * 0.75):
                    moving = bearing(dcx, dcy)
            elif not g['city']['dead'] and g['phase'] == 'play':
                g['city']['hp'] = max(0.0, g['city']['hp'] - {'rifle': 0.35, 'mg': 0.5, 'gren': 0.6}[e['kind']] * dt)
                if random.random() < dt * 3:
                    self.fx.add('glow', W / 2 + random.uniform(-60, 60), H / 2 + random.uniform(-50, 50), life=.25,
                                r0=8, r1=20, col=(255, 150, 70))
                if e['state'] == 'combat' and not los:
                    e['h'] = bearing(dcx, dcy)
        elif e['kind'] == 'gren':
            if dp < 185:
                moving = to_p + 180
            elif dp > 330:
                moving = to_p
            else:
                moving = to_p + 90 * e['strafe']
                sp *= 0.5
        elif e['kind'] == 'mg':
            if dp > T['range'] * 1.15:
                moving, sp = to_p, sp * 0.8
        elif e['mode'] == 'pusher':
            moving = to_p + 28 * e['strafe'] if dp > 165 else to_p + 90 * e['strafe']
        elif e['cover'] is not None:
            c = g['covers'][e['cover']]
            away = bearing(c['x'] - g['spawn'][0], c['y'] - g['spawn'][1])
            px_, py_ = vec(away + 90, math.sin(g['t'] * 1.1 + e['ph0']) * 28)
            ax_, ay_ = vec(away, c['r'] + 12)
            tx, ty = c['x'] + ax_ + px_, c['y'] + ay_ + py_
            if dist(e['x'], e['y'], tx, ty) > 4:
                moving, sp = bearing(tx - e['x'], ty - e['y']), sp * 0.85
        if moving is not None:
            self.mv(e, moving, sp, dt)
        if alive and (los or e['burst'] > 0 or e['tele'] > 0 or e['kind'] == 'gren'):
            target = to_p
        else:
            target = moving if moving is not None else e['h']
        e['h'] = (e['h'] + clamp(angle_diff(e['h'], target), -420 * dt, 420 * dt)) % 360
        if not alive:
            return
        wv = self.wave
        if e['burst'] > 0:
            e['bcd'] -= dt
            if e['bcd'] <= 0:
                e['burst'] -= 1
                if e['kind'] == 'mg':
                    self.enemy_shoot(e, e['aimlock'], 5.0, 390, T['dmg'])
                    e['bcd'] = 0.09
                elif e['kind'] == 'sniper':
                    self.enemy_shoot(e, e['aimlock'], 0.6, 760, T['dmg'])
                    self.audio.play('cannon', .35)
                    e['bcd'] = 0.5
                else:
                    self.enemy_shoot(e, to_p, max(2.5, 6.5 - 0.5 * wv) + dp * 0.008, 300, T['dmg'])
                    e['bcd'] = 0.17
        elif e['tele'] > 0:
            e['tele'] -= dt
            if e['tele'] <= 0:
                e['burst'], e['bcd'] = (1 if e['kind'] == 'sniper' else 8), 0.0
        elif e['cd'] <= 0:
            if e['kind'] == 'gren':
                if 110 < dp < T['range']:
                    self.enemy_throw(e)
                    e['cd'] = random.uniform(*T['rate']) * max(0.6, 1 - 0.05 * wv)
            elif los:
                e['cd'] = random.uniform(*T['rate']) * max(0.6, 1 - 0.05 * wv)
                if e['kind'] in ('mg', 'sniper'):
                    e['tele'] = 0.7 if e['kind'] == 'mg' else 1.25
                    e['aimlock'] = to_p
                    self.audio.play('ping', .25)
                else:
                    e['burst'], e['bcd'] = (2 if wv >= 3 else 1), 0.0

    def upd_ground(self, dt):
        g = self.g
        p, city = g['p'], g['city']
        keys = pygame.key.get_pressed()
        g['t'] += dt
        g['hurt'] = max(0.0, g['hurt'] - dt)
        alive = not p['dead']
        if alive:
            mx = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            my = (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0) - (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0)
            n = math.hypot(mx, my) or 1.0
            p['sneak'] = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and g['stealth']
            sp = (72.0 if p['sneak'] else 135.0) if mx or my else 0.0
            if g['inst'] > 0 and (mx or my):
                g['inst'] = 0.0
            ox, oy = p['x'], p['y']
            self.g_step(p, mx / n * sp * dt, my / n * sp * dt, True)
            p['vx'], p['vy'] = (p['x'] - ox) / max(dt, 1e-4), (p['y'] - oy) / max(dt, 1e-4)
            p['ph'] += math.hypot(p['vx'], p['vy']) * dt / 9.0
            if mx or my:
                self.g_noise(34 if p['sneak'] else 125, 0.12)
            p['noise_t'] = max(0.0, p['noise_t'] - dt)
            p['noise'] = p['noise_r'] if p['noise_t'] > 0 else 0.0
            ax, ay = self.ground_aim()
            p['h'] = bearing(ax - p['x'], ay - p['y'])
            p['cd'] = max(0.0, p['cd'] - dt)
            p['gcd'] = max(0.0, p['gcd'] - dt)
            p['flash'] = max(0.0, p['flash'] - dt)
            p['bloom'] = max(0.0, p['bloom'] - 7 * dt)
            if p['reload'] > 0:
                p['reload'] -= dt
                if p['reload'] <= 0:
                    if p['wpn'] == 'pistol':
                        p['pmag'] = 12
                    else:
                        p['mag'] = 30
            elif (p['pmag'] if p['wpn'] == 'pistol' else p['mag']) <= 0:
                self.start_reload()
            if (pygame.mouse.get_pressed()[0] or keys[pygame.K_f]) and g['phase'] == 'play':
                self.player_shoot()
        if g['stealth'] and g['phase'] == 'play':
            self.upd_stealth(dt, alive, keys)
        self.g_camera(dt)
        if g['phase'] == 'play':
            while g['queue'] and g['queue'][0][0] <= g['t']:
                _, kind, idx = g['queue'].pop(0)
                self.spawn_ground_enemy(kind, idx)
        for b in g['boats']:
            b[3] += dt
        g['boats'] = [b for b in g['boats'] if b[3] < 1.8]
        for e in g['enemies'][:]:
            self.ai_soldier(e, dt)
        for b in g['bullets'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if b['life'] <= 0 or dist(b['x'], b['y'], W / 2, H / 2) > g['R'] * 1.25:
                g['bullets'].remove(b)
                continue
            blocked = False
            for i, c in enumerate(g['covers']):
                if i not in b['ign'] and dist(b['x'], b['y'], c['x'], c['y']) < c['r'] * 0.9:
                    blocked = True
                    break
            if blocked:
                self.fx.add('smoke', b['x'], b['y'], 0, -10, 0.5, 3, 9, (190, 170, 130))
                for _ in range(3):
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-80, 80), random.uniform(-80, 80), 0.2,
                                col=(255, 220, 140), drag=2)
                g['bullets'].remove(b)
                continue
            if b['own'] == 'p':
                cm = next((c_ for c_ in g['cams'] if c_['on'] and dist(b['x'], b['y'], c_['x'], c_['y']) < 14), None)
                if cm is not None:
                    cm['hp'] -= b['dmg']
                    g['bullets'].remove(b)
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.3, col=(120, 230, 255), drag=2)
                    if cm['hp'] <= 0:
                        cm['on'] = False
                        g['tleft'] += 10.0
                        self.gpop('+10 s', cm['x'], cm['y'] - 40, (140, 255, 200))
                        self.fx.explode(cm['x'], cm['y'], 0.5)
                        self.audio.play('boom_s', .4)
                        self.gpop('CÁMARA DESTRUIDA', cm['x'], cm['y'] - 20, (140, 255, 200))
                    continue
                hit = next((e for e in g['enemies'] if dist(b['x'], b['y'], e['x'], e['y']) < 13), None)
                if hit:
                    hit['hp'] -= b['dmg']
                    hit['hit'] = 0.1
                    if hit['state'] in ('hold', 'susp') and hit['hp'] > 0:
                        if b.get('silent'):
                            hit['state'], hit['det'], hit['spot'], hit['st'] = 'susp', max(hit['det'], 0.6), (p['x'], p['y']), 7.0
                        else:
                            self.alert(hit, alarm=g['stealth'])
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25,
                                col=(255, 120, 90), drag=2)
                    g['bullets'].remove(b)
                    if hit['hp'] <= 0:
                        self.kill_ground_enemy(hit)
            elif alive and dist(b['x'], b['y'], p['x'], p['y']) < 12:
                g['bullets'].remove(b)
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25,
                            col=(255, 120, 90), drag=2)
                self.hurt_player(int(b['dmg']))
        for n in g['nades'][:]:
            n['t'] += dt
            if n['t'] >= n['T']:
                g['nades'].remove(n)
                self.explode_nade(n)
        for q in g['crates'][:]:
            q['t'] += dt
            if alive and dist(q['x'], q['y'], p['x'], p['y']) < 24:
                g['crates'].remove(q)
                self.audio.play('pickup', .8)
                if q['kind'] == 'med':
                    p['hp'] = min(PLAYER_HP, p['hp'] + 40)
                    self.gpop('+40 SALUD', q['x'], q['y'] - 16, (120, 255, 150))
                else:
                    p['gren'] = min(6, p['gren'] + 2)
                    self.gpop('+2 GRANADAS', q['x'], q['y'] - 16, (255, 230, 90))
            elif q['t'] > 30:
                g['crates'].remove(q)
        for c in g['corpses']:
            c['age'] += dt
        if p['dead']:
            p['dead_t'] += dt
        elif p['hp'] <= 0:
            p['dead'] = True
            self.fx.explode(p['x'], p['y'], 0.9)
            self.audio.play('boom_s')
            self.shake = 10
            if g['phase'] == 'play':
                g['phase'], g['fail'], g['pt'] = 'result', True, -0.6
                self.banner('¡SOLDADO CAÍDO!', 'La misión fracasó', (255, 80, 70), 3.0)
        if g['mode'] == 'invasion' and city['hp'] <= 0 and not city['dead']:
            city['dead'] = True
            for _ in range(8):
                self.fx.explode(W / 2 + random.uniform(-80, 80), H / 2 + random.uniform(-60, 60), 1.3, True)
            self.audio.play('boom_l')
            self.shake = 20
            if g['phase'] == 'play':
                g['phase'], g['fail'], g['pt'] = 'result', True, 0.0
            self.banner('¡ANTENA DESTRUIDA!' if g['antenna'] is not None else '¡CIUDAD CAPTURADA!', city['name'], (255, 70, 60), 3.0)
        self.fx.update(dt)
        if g['phase'] == 'play' and not g['queue'] and not g['enemies']:
            g['phase'], g['pt'] = 'result', 0.0
            bonus = 300
            if g['mode'] == 'invasion' and city['hp'] >= g['city0'] - 0.01:
                bonus += 400
            self.add_score(bonus)
            self.audio.play('win', .7)
            if g['mode'] == 'landing':
                self.banner('¡ISLA ASEGURADA!', 'Instalando antena...  Bonus +%d' % bonus, (120, 255, 160), 3.2)
            else:
                self.banner('¡ANTENA DEFENDIDA!' if g['antenna'] is not None else '¡ISLA ASEGURADA!', 'Bajas enemigas: %d   Bonus +%d' % (g['kills'], bonus), (120, 255, 160), 2.8)
        if g['phase'] == 'result':
            g['pt'] += dt
            if not g['fail']:
                g['ant_t'] += dt
            if g['pt'] > (3.6 if g['mode'] == 'landing' and not g['fail'] else 2.8):
                self.end_ground()

    def upd_stealth(self, dt, alive, keys):
        g = self.g
        p = g['p']
        # tiempo límite y refuerzos en lancha
        g['tleft'] -= dt
        if g['tleft'] < 10 and int(g['tleft']) != int(g['tleft'] + dt):
            self.audio.play('blip', .45)
        elif g['tleft'] < 30 and int(g['tleft']) != int(g['tleft'] + dt) and int(g['tleft']) == 29:
            self.toast('¡Quedan 30 segundos!', (255, 200, 90))
        g['reinf_t'] -= dt
        if g['reinf_t'] <= 0 and g['tleft'] > 8:
            g['reinf_t'] = max(16.0, 30.0 - 3.0 * self.wave)
            for _ in range(2):
                self.spawn_ground_enemy('rifle', random.randrange(3))
                e = g['enemies'][-1]
                e['state'], e['spot'], e['st'], e['det'] = 'susp', (W / 2, H / 2), 14.0, 0.2
                e['excl'] = 0.0
                g['total'] += 1
            self.toast('¡Refuerzos enemigos llegan en lancha!', (255, 140, 100))
        if g['tleft'] <= 0:
            g['tleft'] = 0.0
            g['phase'], g['fail'], g['pt'] = 'result', True, 0.0
            self.audio.play('lose', .6)
            self.banner('¡TIEMPO AGOTADO!', 'No lograste tomar la isla a tiempo', (255, 80, 70), 3.0)
            return
        # cámaras de seguridad
        for cam in g['cams']:
            if not cam['on']:
                continue
            cam['sw'] += dt * 0.7
            cam['h'] = cam['base'] + 48 * math.sin(cam['sw'])
            seen = (alive and dist(cam['x'], cam['y'], p['x'], p['y']) < 290 * (0.75 if p['sneak'] else 1.0)
                    and abs(angle_diff(cam['h'], bearing(p['x'] - cam['x'], p['y'] - cam['y']))) < 28
                    and self.g_los(cam['x'], cam['y'], p['x'], p['y']))
            if seen:
                cam['det'] += dt * 1.1
                if cam['det'] >= 1.0:
                    cam['det'] = 0.3
                    near = min(g['enemies'], key=lambda e: dist(e['x'], e['y'], cam['x'], cam['y']), default=None)
                    if near is not None:
                        self.alert(near, alarm=True)
                    else:
                        g['alerts'] += 1
                        g['alert_t'] = 30.0
            else:
                cam['det'] = max(0.0, cam['det'] - dt * 0.5)
        if alive and any(dist(e['x'], e['y'], p['x'], p['y']) < 480 and self.g_los(e['x'], e['y'], p['x'], p['y']) and e['state'] == 'combat' for e in g['enemies']):
            g['last_seen'] = (p['x'], p['y'])
        # evasión
        if g['alert_t'] > 0 and alive:
            seen = any(e['state'] == 'combat' and dist(e['x'], e['y'], p['x'], p['y']) < 480 and self.g_los(e['x'], e['y'], p['x'], p['y'])
                       for e in g['enemies'])
            if seen:
                g['alert_t'] = 30.0
            else:
                g['alert_t'] -= dt
                if g['alert_t'] <= 0:
                    g['alert_t'] = 0.0
                    for e in g['enemies']:
                        if e['state'] == 'combat':
                            e['state'], e['det'], e['spot'], e['st'] = 'susp', 0.5, (p['x'], p['y']), 8.0
                    self.banner('EVASIÓN LOGRADA', 'Los enemigos te buscan por la zona', (120, 255, 190), 2.6)
        # instalación silenciosa de la antena
        pad_d = dist(p['x'], p['y'], W / 2, H / 2)
        if alive and keys[pygame.K_e] and pad_d < 56 and not p['sneak'] and not any(e['state'] == 'combat' and dist(e['x'], e['y'], p['x'], p['y']) < 260 for e in g['enemies']):
            g['inst'] += dt / 4.0
            self.g_noise(60, 0.15)
            if g['inst'] >= 1.0:
                g['phase'], g['pt'] = 'result', 0.0
                bonus = (800 if g['alerts'] == 0 else 300) + 120 * g['takedowns']
                self.add_score(bonus)
                self.audio.play('win', .7)
                self.banner('¡ANTENA INSTALADA EN SILENCIO!' if g['alerts'] == 0 else '¡ANTENA INSTALADA!',
                            ('FANTASMA  ' if g['alerts'] == 0 else 'Infiltrado  ') + 'Bonus +%d' % bonus, (120, 255, 160), 3.4)
        elif g['inst'] > 0 and not keys[pygame.K_e]:
            g['inst'] = max(0.0, g['inst'] - dt * 0.5)

    def end_ground(self):
        g = self.g
        city = g['city']
        if g['mode'] == 'landing':
            i = g['island_idx']
            if g['fail']:
                self.hull = max(0.0, self.hull - 25)
                self.ammo = max(0, self.ammo - 5)
                left = MAX_LANDING_ATTEMPTS - self.landing_attempts[i]
                self.toast('Desembarco fallido: -25 casco, -5 munición  (intentos: %d)' % left, (255, 140, 90))
                if self.hull <= 0:
                    return self.game_over('Tu barco se hundió')
            elif i in self.antennas and not self.antennas[i]:
                self.antennas[i] = True
                n = sum(self.antennas.values())
                self.toast('¡ANTENA INSTALADA en %s!' % self.isl_name(i), (120, 255, 160))
                self.banner('ANTENA OPERATIVA', '%d/%d antenas  |  El jefe de esta oleada exige %d' % (n, len(self.antennas), self.antennas_needed()),
                            (120, 220, 255), 3.4)
        elif g['antenna'] is not None:
            if g['fail']:
                self.antennas[g['antenna']] = False
                self.toast('Perdiste la antena de %s: hay que volver a instalarla' % self.isl_name(g['antenna']), (255, 120, 100))
            else:
                self.toast('Antena a salvo', (120, 255, 160))
            self.warned = False
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        else:
            if g['fail'] and not city['dead']:
                city['hp'] = max(0.0, city['hp'] - 30)
                if city['hp'] <= 0:
                    city['dead'] = True
            self.warned = False
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
            if all(c['dead'] for c in self.cities):
                return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---- terrestre (infantería)
    def draw_cone(self, cv, x, y, h, rng, fov, col=(255, 225, 110)):
        if not (-rng < x < W + rng and -rng < y < H + rng):
            return
        if not hasattr(self, '_cone'):
            self._cone = pygame.Surface((2 * 340 + 4, 2 * 340 + 4), pygame.SRCALPHA)
        c = self._cone
        c.fill((0, 0, 0, 0))
        mid = 340 + 2
        pts = [(mid, mid)]
        for i in range(13):
            ax, ay = vec(h - fov / 2 + fov * i / 12, rng)
            pts.append((mid + ax, mid + ay))
        pygame.draw.polygon(c, (*col, 44 + int(14 * math.sin(self.t * 4))), pts)
        pygame.draw.lines(c, (*col, 90), False, [pts[1], pts[0], pts[-1]], 1)
        cv.blit(c, (x - mid, y - mid))

    def blit_soldier(self, dst, key, x, y, ang, frame, hit=0.0, dead=False):
        draw_circ(dst, x + 4, y + 5, 14, (0, 0, 0), 70)
        r = pygame.transform.rotate(self.sol[key][frame % 4], -ang)
        if hit > 0 or dead:
            r = r.copy()
            if dead:
                r.fill((95, 95, 95), special_flags=pygame.BLEND_RGB_MULT)
            else:
                r.fill((110, 110, 110, 0), special_flags=pygame.BLEND_RGB_ADD)
        dst.blit(r, (int(x) - r.get_width() // 2, int(y) - r.get_height() // 2))

    def draw_dog(self, cv, x, y, s):
        draw_circ(cv, x + 3, y + 4, 11, (0, 0, 0), 70)
        fx, fy = vec(s['h'], 1.0)
        sx_, sy_ = -fy, fx
        body = (214, 214, 214) if s['hit'] > 0 else (96, 66, 44)
        dark = (60, 40, 28)
        sw = math.sin(s['ph'] * 1.8)
        for i, off in enumerate((-9, 8)):
            for side in (-1, 1):
                lx = x + fx * (off + (4 * sw if (i + (side > 0)) % 2 else -4 * sw)) + sx_ * side * 5
                ly = y + fy * (off + (4 * sw if (i + (side > 0)) % 2 else -4 * sw)) + sy_ * side * 5
                pygame.draw.circle(cv, dark, (int(lx), int(ly)), 3)
        pts = []
        for k in range(14):
            a = 6.2832 * k / 14
            u, v = math.cos(a) * 14, math.sin(a) * 6
            pts.append((x + fx * u + sx_ * v, y + fy * u + sy_ * v))
        pygame.draw.polygon(cv, body, pts)
        pygame.draw.polygon(cv, dark, pts, 1)
        hx, hy = x + fx * 14, y + fy * 14
        pygame.draw.circle(cv, body, (int(hx), int(hy)), 6)
        pygame.draw.line(cv, dark, (hx, hy), (hx + fx * 6, hy + fy * 6), 3)
        pygame.draw.line(cv, dark, (x - fx * 13, y - fy * 13), (x - fx * 20 + sx_ * 3 * sw, y - fy * 20 + sy_ * 3 * sw), 2)
        if s['hp'] < s['max']:
            pygame.draw.rect(cv, (8, 12, 24), (x - 10, y - 20, 20, 4))
            pygame.draw.rect(cv, (240, 80, 70), (x - 9, y - 19, int(18 * s['hp'] / s['max']), 2))

    def draw_boat(self, cv, x, y, a):
        h = math.radians(a)
        sn, cs = math.sin(h), math.cos(h)
        pts = [(x + sn * (-ly) + cs * lx, y - cs * (-ly) + sn * lx) for lx, ly in ((0, -30), (15, -14), (15, 22), (-15, 22), (-15, -14))]
        pygame.draw.polygon(cv, (70, 82, 92), pts)
        pygame.draw.polygon(cv, (128, 142, 152), [(x + (px - x) * .78, y + (py - y) * .78) for px, py in pts])
        pygame.draw.polygon(cv, (210, 222, 232), pts, 2)

    def draw_ground(self, cv):
        g = self.g
        p, city = g['p'], g['city']
        t = self.t
        cam = g['cam']
        cx_, cy_ = int(cam[0]), int(cam[1])
        self.draw_ocean(cv, cx_, cy_, t)
        lo = g['land_off']
        cv.blit(g['land'], (lo[0] - cx_, lo[1] - cy_))
        for x, y, r in g['decals']:
            draw_circ(cv, x - cx_, y - cy_, r, (28, 24, 20), 140)
        if g['mode'] == 'landing':
            if g['phase'] == 'result' and not g['fail']:
                k = clamp(g['ant_t'] / 1.8, 0, 1)
                bw, bh = self.antenna_big.get_size()
                hh = int(bh * k)
                if hh > 0:
                    cv.blit(self.antenna_big, (W // 2 - cx_ - bw // 2, H // 2 - cy_ + 20 - hh), area=pygame.Rect(0, bh - hh, bw, hh))
                if k >= 1:
                    for j in range(3):
                        ph = (t * 0.8 + j / 3) % 1
                        draw_circ(cv, W // 2 - cx_, H // 2 - cy_ - bh + 30, 14 + ph * 80, (120, 240, 255), 170 * (1 - ph), 2)
            self.draw_boat(cv, g['spawn'][0] - cx_, g['spawn'][1] + 58 - cy_, 0)
        for x, y, a, _t in g['boats']:
            self.draw_boat(cv, x - cx_, y - cy_, a)
        for c in g['corpses']:
            if c['age'] < 14:
                self.blit_soldier(cv, 'e_' + c['kind'], c['x'] - cx_, c['y'] - cy_, c['h'], 0, dead=True)
        for q in g['crates']:
            qx, qy = q['x'] - cx_, q['y'] - cy_
            glow(cv, qx, qy, 28, (120, 255, 150) if q['kind'] == 'med' else (255, 210, 70), 0.6)
            pygame.draw.rect(cv, (236, 240, 236) if q['kind'] == 'med' else (96, 110, 70), (qx - 9, qy - 9, 18, 18), border_radius=3)
            if q['kind'] == 'med':
                pygame.draw.rect(cv, (220, 50, 50), (qx - 6, qy - 2, 12, 4))
                pygame.draw.rect(cv, (220, 50, 50), (qx - 2, qy - 6, 4, 12))
            else:
                pygame.draw.circle(cv, (60, 76, 50), (int(qx), int(qy)), 5)
                pygame.draw.circle(cv, (255, 210, 70), (int(qx), int(qy)), 8, 2)
        for e in g['enemies']:
            if g['stealth'] and e['state'] in ('hold', 'susp'):
                sen = e['role'] == 'sentry'
                self.draw_cone(cv, e['x'] - cx_, e['y'] - cy_, e['h'], (340 if sen else 240) * (0.7 if p['sneak'] else 1.0), 110 if sen else 90,
                               (255, 200, 90) if e['state'] == 'hold' else (255, 120, 60))
        if g['stealth']:
            pad = (W // 2 - cx_, H // 2 - cy_)
            if g['phase'] == 'play':
                pul = 0.5 + 0.5 * math.sin(t * 3)
                draw_circ(cv, pad[0], pad[1], 54 + pul * 4, (110, 230, 255), 60 + 40 * pul, 2)
                self.text(cv, 'ANTENA (E)', self.f_s, (150, 240, 255), pad[0], pad[1] - 78, 'c')
                if g['inst'] > 0:
                    pygame.draw.rect(cv, (8, 12, 24), (pad[0] - 34, pad[1] - 60, 68, 9))
                    pygame.draw.rect(cv, (110, 230, 255), (pad[0] - 33, pad[1] - 59, int(66 * g['inst']), 7))
            for cm_ in g['cams']:
                if not cm_['on']:
                    continue
                kx, ky = cm_['x'] - cx_, cm_['y'] - cy_
                col = (255, 80, 70) if cm_['det'] > 0.2 else (110, 230, 255)
                self.draw_cone(cv, kx, ky, cm_['h'], 290 * (0.75 if p['sneak'] else 1.0), 56, col)
                pygame.draw.circle(cv, (40, 44, 52), (int(kx), int(ky)), 9)
                pygame.draw.circle(cv, col, (int(kx), int(ky)), 5)
                ex2, ey2 = vec(cm_['h'], 13)
                pygame.draw.line(cv, (200, 205, 215), (kx, ky), (kx + ex2, ky + ey2), 4)
                if cm_['det'] > 0.05:
                    pygame.draw.rect(cv, (8, 12, 24), (kx - 14, ky - 22, 28, 5))
                    pygame.draw.rect(cv, (255, 90 + int(100 * (1 - cm_['det'])), 60), (kx - 13, ky - 21, int(26 * cm_['det']), 3))
            if p['noise_t'] > 0 and p['noise'] > 40:
                draw_circ(cv, p['x'] - cx_, p['y'] - cy_, p['noise'], (255, 255, 255), 22 * clamp(p['noise_t'] / 0.3, 0, 1), 1)
        actors = [(e['y'], 'e', e) for e in g['enemies']] + [(p['y'], 'p', p)]
        for _, who, s in sorted(actors, key=lambda a: a[0]):
            sx, sy = s['x'] - cx_, s['y'] - cy_
            if not (-120 < sx < W + 120 and -120 < sy < H + 120):
                continue
            if who == 'e' and s['kind'] == 'dog':
                self.draw_dog(cv, sx, sy, s)
                continue
            if who == 'e':
                self.blit_soldier(cv, 'e_' + s['kind'], sx, sy, s['h'], int(s['ph']) % 4, s['hit'])
                if s['state'] == 'hold' and s['role'] == 'guard':
                    self.text(cv, 'z', self.f_s, (200, 210, 230), sx + 12, sy - 40, shadow=False, alpha=150)
                if s['excl'] > 0:
                    self.text(cv, '!', self.f_l, (255, 70, 60), sx, sy - 66, 'c')
                elif g['stealth'] and s['state'] in ('hold', 'susp') and s['det'] > 0.04:
                    k_ = clamp(s['det'], 0, 1)
                    col_ = (255, int(220 - 150 * k_), 60)
                    self.text(cv, '?', self.f_l, col_, sx, sy - 70, 'c', alpha=int(120 + 135 * k_))
                    pygame.draw.rect(cv, (8, 12, 24), (sx - 14, sy - 40, 28, 5))
                    pygame.draw.rect(cv, col_, (sx - 13, sy - 39, int(26 * k_), 3))
                if s['hp'] < s['max']:
                    pygame.draw.rect(cv, (8, 12, 24), (sx - 14, sy - 34, 28, 5))
                    pygame.draw.rect(cv, (240, 80, 70), (sx - 13, sy - 33, int(26 * s['hp'] / s['max']), 3))
                if s['tele'] > 0:
                    mx, my = vec(s['aimlock'], 44)
                    ex, ey = vec(s['aimlock'], 430)
                    if int(t * 24) % 2 == 0:
                        pygame.draw.line(cv, (255, 50, 50), (sx + mx, sy + my), (sx + ex, sy + ey), 1)
                    self.text(cv, '!', self.f_m, (255, 70, 60), sx, sy - 58, 'c')
                if s['flash'] > 0:
                    fx_, fy_ = vec(s['h'], 46)
                    glow(cv, sx + fx_, sy + fy_, 20, (255, 200, 120))
            elif s['dead']:
                self.blit_soldier(cv, 'p', sx, sy, s['h'], 0, dead=True)
            else:
                self.blit_soldier(cv, 'p', sx, sy, s['h'], int(s['ph']) % 4)
                if s['flash'] > 0:
                    fx_, fy_ = vec(s['h'], 46)
                    glow(cv, sx + fx_, sy + fy_, 22, (255, 230, 150))
        for b in g['bullets']:
            col = (255, 240, 150) if b['own'] == 'p' else (255, 150, 110)
            bx, by = b['x'] - cx_, b['y'] - cy_
            pygame.draw.line(cv, col, (bx, by), (bx - b['vx'] * 0.035, by - b['vy'] * 0.035), 2)
            glow(cv, bx, by, 7, col, 0.7)
        for n in g['nades']:
            k = n['t'] / n['T']
            x, y = lerp(n['x0'], n['x1'], k) - cx_, lerp(n['y0'], n['y1'], k) - cy_
            hh = math.sin(math.pi * k) * 34
            pulse = 0.5 + 0.5 * math.sin(t * 14)
            tx_, ty_ = n['x1'] - cx_, n['y1'] - cy_
            if n['own'] == 'e':
                draw_circ(cv, tx_, ty_, 62, (255, 60, 50), 28 + 30 * pulse)
                draw_circ(cv, tx_, ty_, 62, (255, 90, 70), 150 + 80 * pulse, 2)
            else:
                draw_circ(cv, tx_, ty_, 62, (255, 255, 255), 60, 1)
            draw_circ(cv, x + 2, y + 3, 5, (0, 0, 0), 80)
            pygame.draw.circle(cv, (58, 74, 48), (int(x), int(y - hh)), 5)
            pygame.draw.circle(cv, (110, 128, 92), (int(x - 1), int(y - hh - 1)), 2)
        self.fx.draw(cv, cx_, cy_)
        ax, ay = self.ground_aim()
        ax, ay = int(ax - cx_), int(ay - cy_)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 14, 2)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 2)
        for dx, dy in ((-24, 0), (24, 0), (0, -24), (0, 24)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        if g['hurt'] > 0:
            self.hurt_surf.set_alpha(int(255 * clamp(g['hurt'] * 2, 0, 1)))
            cv.blit(self.hurt_surf, (0, 0))
        if g['mode'] == 'landing':
            mr = 64
            mcx, mcy = W - 14 - mr, 104 + mr
            sc = mr / (g['R'] * 1.08)
            pygame.draw.circle(cv, (6, 12, 26), (mcx, mcy), mr + 3)
            pygame.draw.circle(cv, (24, 70, 96), (mcx, mcy), mr)
            pygame.draw.circle(cv, (86, 140, 80), (mcx, mcy), int(g['R'] * 0.96 * sc))
            for c in g['covers']:
                pygame.draw.circle(cv, (150, 140, 110), (int(mcx + (c['x'] - W / 2) * sc), int(mcy + (c['y'] - H / 2) * sc)), 2)
            pygame.draw.circle(cv, (196, 198, 194), (mcx, mcy), 4, 1)
            if g['stealth']:
                rs = pygame.Surface((mr * 2, mr * 2), pygame.SRCALPHA)
                for e in g['enemies']:
                    if e['state'] in ('hold', 'susp'):
                        ex_, ey_ = mr + (e['x'] - W / 2) * sc, mr + (e['y'] - H / 2) * sc
                        rng_ = (340 if e['role'] == 'sentry' else 240) * sc
                        fov_ = 110 if e['role'] == 'sentry' else 90
                        pts_ = [(ex_, ey_)] + [(ex_ + vec(e['h'] - fov_ / 2 + fov_ * i / 6, rng_)[0], ey_ + vec(e['h'] - fov_ / 2 + fov_ * i / 6, rng_)[1]) for i in range(7)]
                        pygame.draw.polygon(rs, (255, 210, 90, 70) if e['state'] == 'hold' else (255, 120, 60, 90), pts_)
                for cm in g['cams']:
                    if cm['on']:
                        ex_, ey_ = mr + (cm['x'] - W / 2) * sc, mr + (cm['y'] - H / 2) * sc
                        pts_ = [(ex_, ey_)] + [(ex_ + vec(cm['h'] - 28 + 56 * i / 6, 290 * sc)[0], ey_ + vec(cm['h'] - 28 + 56 * i / 6, 290 * sc)[1]) for i in range(7)]
                        pygame.draw.polygon(rs, (110, 230, 255, 70), pts_)
                cv.blit(rs, (mcx - mr, mcy - mr))
            for e in g['enemies']:
                pygame.draw.circle(cv, (255, 70, 60) if e['state'] == 'combat' else (170, 70, 60),
                                   (int(mcx + (e['x'] - W / 2) * sc), int(mcy + (e['y'] - H / 2) * sc)), 3)
            pygame.draw.rect(cv, (220, 230, 240), (mcx + (cam[0] - W / 2) * sc, mcy + (cam[1] - H / 2) * sc, W * sc, H * sc), 1)
            pygame.draw.circle(cv, (90, 255, 255), (int(mcx + (p['x'] - W / 2) * sc), int(mcy + (p['y'] - H / 2) * sc)), 3)
            pygame.draw.circle(cv, (110, 150, 190), (mcx, mcy), mr + 3, 2)
        self.panel(cv, (14, H - 126, 330, 112), 160)
        self.bar(cv, 26, H - 116, 306, 24, p['hp'] / PLAYER_HP, (80, 220, 110) if p['hp'] > 40 else (240, 80, 70), 'SOLDADO %d' % max(0, p['hp']))
        if p['reload'] > 0:
            self.bar(cv, 26, H - 86, 306, 24, 1 - p['reload'] / (1.0 if p['wpn'] == 'pistol' else 1.3), (255, 160, 70), 'RECARGANDO...')
        elif p['wpn'] == 'pistol':
            self.bar(cv, 26, H - 86, 306, 24, p['pmag'] / 12, (120, 220, 255) if p['pmag'] > 3 else (240, 80, 70), 'PISTOLA SILENCIADA %d/12' % p['pmag'])
        else:
            self.bar(cv, 26, H - 86, 306, 24, p['mag'] / 30, (255, 210, 70) if p['mag'] > 8 else (240, 80, 70), 'CARGADOR %d/30' % p['mag'])
        self.text(cv, 'GRANADAS', self.f_s, (235, 245, 255), 26, H - 54)
        for i in range(p['gren']):
            pygame.draw.circle(cv, (58, 74, 48), (140 + i * 24, H - 45), 8)
            pygame.draw.circle(cv, (150, 170, 120), (138 + i * 24, H - 48), 3)
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, (160, 200, 240), 26, 42)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        self.text(cv, city['name'], self.f_m, (255, 255, 255), W // 2, 16, 'c')
        if g['mode'] == 'landing':
            left = len(g['enemies'])
            self.bar(cv, W // 2 - 210, 44, 420, 26, left / max(1, g['total']), (240, 80, 70), 'ENEMIGOS %d/%d' % (left, g['total']))
        else:
            col = (80, 230, 110) if city['hp'] > 60 else ((255, 200, 70) if city['hp'] > 30 else (240, 80, 70))
            self.bar(cv, W // 2 - 210, 44, 420, 26, city['hp'] / 100, col, '%s %d%%' % ('ANTENA' if g['antenna'] is not None else 'CIUDAD', city['hp']))
            self.text(cv, 'ENEMIGOS: %d' % (len(g['queue']) + len(g['enemies'])), self.f_m, (255, 160, 140), W - 20, 90, 'r')
        if g['stealth']:
            self.text(cv, 'SHIFT sigilo | Q pistola/fusil | E noquear o instalar | clic disparar | ESPACIO granada', self.f_s, (200, 220, 255), W - 14, H - 30, 'r')
            tl = max(0.0, g['tleft'])
            tcol = (140, 230, 255) if tl > 60 else ((255, 210, 80) if tl > 30 else (255, 90 + int(100 * (0.5 + 0.5 * math.sin(t * 10))), 70))
            self.panel(cv, (W // 2 - 110, 130, 220, 44), 190)
            self.text(cv, 'TIEMPO', self.f_s, (170, 200, 230), W // 2 - 96, 138)
            self.text(cv, '%d:%04.1f' % (int(tl) // 60, tl % 60), self.f_l, tcol, W // 2 + 100, 134, 'r')
            if g['alert_t'] > 0:
                pul = 0.5 + 0.5 * math.sin(t * 9)
                self.panel(cv, (W // 2 - 150, 88, 300, 40), 190)
                self.text(cv, 'ALERTA  %04.1f s' % g['alert_t'], self.f_m, (255, int(80 + 100 * pul), 70), W // 2, 96, 'c')
                pygame.draw.rect(cv, (255, 40, 40), (0, 0, W, H), 3 + int(4 * pul))
            else:
                state = 'SIGILO' if not any(e['state'] == 'susp' for e in g['enemies']) else 'SOSPECHA'
                self.text(cv, state + ('  (agachado)' if p['sneak'] else ''), self.f_s, (140, 255, 200) if state == 'SIGILO' else (255, 210, 100), W // 2, 92, 'c')
        else:
            self.text(cv, 'WASD mover | Clic disparar | R recargar | ESPACIO granada', self.f_s, (200, 220, 255), W - 14, H - 30, 'r')
