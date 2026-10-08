"""Batalla aérea estilo Twinbee con F-16 / F-117."""
import math
import pygame
import random
from .common import H, Particles, W, WIN_WAVE, angle_diff, bearing, clamp, coast_r, dist, draw_circ, glow, lerp, shade, vec
from .sprites import make_shadow


from .comms import AIR_LINES


from .air_art import load_png_sprite


class AerialMixin:
    # ---------------------------------------------------------- BATALLA AÉREA (estilo Twinbee)
    AIR_SCROLL = 80.0

    def start_aerial(self, city=None):
        self.fx = Particles()
        w = self.wave
        pool = ['vee', 'line', 'dive', 'pair', 'vee', 'line']
        if w >= 2:
            pool += ['kami', 'bomber']
        if w >= 3:
            pool += ['mines', 'spiral']
        if w >= 4:
            pool += ['gunship']
        events, t = [], 2.0
        gap = max(3.2, 4.8 - 0.15 * w)
        for i in range(min(16, 8 + w)):
            k = pool[i % len(pool)] if i < len(pool) else random.choice(pool)
            events.append((t, k, random.uniform(200, W - 200)))
            t += gap + random.uniform(-0.4, 0.8)
        self.a = dict(city=city, t=0.0, scroll=0.0, phase='play', pt=0.0, fail=False, kills=0,
                      p=dict(x=W / 2, y=H - 140.0, hp=100.0, inv=0.0, cd=0.0, bcd=0.0, wl=1, shield=0.0, vx=0.0, dead=False, rapid=0.0, homing=0.0, mcd=0.0),
                      foes=[], ebul=[], pbul=[], bombs=[], ground=[], isl=[], clouds=[],
                      forms={}, fid=0, events=events, boss_t=t + 2.5, boss=None, boss_dead=False,
                      isl_t=0.0, boat_t=6.0, cloud_t=0.0)
        for yy in (-200, 100, 330, 560):
            self.air_spawn_island(random.uniform(80, W - 80), yy)
        for _ in range(9):
            self.air_spawn_cloud(random.uniform(0, H))
        self.go('aerial')
        self.banner('¡BATALLA AÉREA!', 'Derribá a los cazas enemigos', (100, 180, 255), 3.0)
        self.say('piloto', 'Despegamos. WASD para moverte, ESPACIO para disparar y B para bombardear objetivos en tierra.', 'info')

    def air_spawn_island(self, x, y):
        a = self.a
        idx = random.randrange(len(self.air['isl']))
        r = self.air['isl_r'][idx]
        isl = dict(x=x, y=y, i=idx, r=r)
        a['isl'].append(isl)
        for _ in range(random.choice((0, 1, 1, 2))):
            ang, d = random.uniform(0, 6.28), random.uniform(0.1, 0.5) * r
            a['ground'].append(dict(kind='sam', x=x + math.cos(ang) * d, y=y + math.sin(ang) * d, vx=0.0, hp=3,
                                    cd=random.uniform(1.0, 3.0), ang=180.0))

    def air_on_land(self, x, y, margin=0.0):
        """True si el punto cae sobre una isla (costa exacta con la arena) más un margen."""
        for isl in self.a['isl']:
            ang = math.atan2(y - isl['y'], x - isl['x'])
            if dist(x, y, isl['x'], isl['y']) < coast_r(isl['r'], 21 + isl['i'], ang, 1.06) + margin:
                return True
        return False

    def air_spawn_cloud(self, y):
        self.a['clouds'].append(dict(x=random.uniform(-100, W + 100), y=y, v=random.uniform(125, 175),
                                     i=random.randrange(len(self.air['clouds'])),
                                     s=random.uniform(0.7, 1.3), tw=random.uniform(0, 6.28)))

    def air_foe(self, kind, x, y, fid=None, **kw):
        w = self.wave
        hp = {'viper': 2 + w // 3, 'stealth': 5 + w // 2, 'bomber': 16 + 3 * w, 'kami': 2, 'gunship': 10 + w, 'mine': 3}[kind]
        f = dict(kind=kind, x=x, y=y, bx=x, hp=float(hp), max=float(hp), t=0.0, ph=random.uniform(0, 6.28),
                 cd=random.uniform(1.2, 2.8), fid=fid, vx=0.0, vy=0.0, mode=0, hit=0.0)
        f.update(kw)
        if kind == 'kami':
            f['a'] = kw.get('a_', 180.0)
        self.a['foes'].append(f)
        return f

    def air_spawn_formation(self, kind, x):
        a = self.a
        a['fid'] += 1
        fid = a['fid']
        if kind == 'vee':
            offs = [(0, 0), (-50, -38), (50, -38), (-100, -76), (100, -76)]
            for ox, oy in offs:
                self.air_foe('viper', clamp(x + ox, 50, W - 50), -50 + oy, fid)
        elif kind == 'line':
            for i in range(6):
                self.air_foe('viper', x, -50 - i * 52, fid)
        elif kind == 'dive':
            side = random.choice((-1, 1))
            for i in range(3):
                self.air_foe('stealth', -60 if side < 0 else W + 60, 70 + i * 70, fid, mode=side)
        elif kind == 'pair':
            for ox in (-90, 90):
                self.air_foe('stealth', clamp(x + ox, 80, W - 80), -60, fid, mode=0)
        elif kind == 'bomber':
            self.air_foe('bomber', x, -90, fid)
        elif kind == 'kami':
            for i in range(3):
                self.air_foe('kami', clamp(x + (i - 1) * 70, 50, W - 50), -50 - i * 40, fid, a_=180.0)
        elif kind == 'spiral':
            for i in range(6):
                self.air_foe('viper', clamp(x, 150, W - 150), -50 - i * 46, fid, spiral=i)
        elif kind == 'mines':
            gap = random.randrange(5)
            for i in range(6):
                if i not in (gap, gap + 1):
                    self.air_foe('mine', 80 + i * 188, -40.0, fid)
        elif kind == 'gunship':
            self.air_foe('gunship', clamp(x, 200, W - 200), -80, fid)
        a['forms'][fid] = dict(n=sum(1 for f in a['foes'] if f['fid'] == fid), escaped=False)

    def air_ebul(self, x, y, ang, speed, r=5):
        spd = speed * (1 + 0.03 * self.wave)
        vx, vy = vec(ang, spd)
        self.a['ebul'].append(dict(x=x, y=y, vx=vx, vy=vy, r=r))

    def air_boom(self, x, y, size=1.0, big=False, snd='boom_s'):
        self.fx.explode(x, y, size, big)
        self.audio.play(snd, .5)

    def air_kill_foe(self, f):
        a = self.a
        if f not in a['foes']:
            return
        a['foes'].remove(f)
        a['kills'] += 1
        pts = {'viper': 100, 'stealth': 250, 'bomber': 800, 'kami': 150, 'gunship': 500, 'mine': 100}[f['kind']]
        self.add_score(pts)
        self.pop('+%d' % pts, f['x'], f['y'] - 20)
        self.air_boom(f['x'], f['y'], {'viper': 0.9, 'stealth': 1.1, 'bomber': 2.0, 'kami': 0.8, 'gunship': 1.4, 'mine': 1.0}[f['kind']], f['kind'] in ('bomber', 'gunship'))
        if f['kind'] == 'mine':
            for i in range(8):
                self.air_ebul(f['x'], f['y'], i * 45, 120, 5)
        form = a['forms'].get(f['fid'])
        if form:
            form['n'] -= 1                              # sin potenciadores: ya no se sueltan cápsulas

    def air_fire_player(self):
        a = self.a
        p = a['p']
        wl = p['wl']
        angs = {1: (0,), 2: (-3, 3), 3: (-9, 0, 9), 4: (-16, -8, 0, 8, 16)}[wl]
        for k, ang in enumerate(angs):
            off = (k - (len(angs) - 1) / 2) * (9 if wl == 2 else 5)
            vx, vy = vec(ang, 800)
            a['pbul'].append(dict(x=p['x'] + off, y=p['y'] - 36, vx=vx, vy=vy, dmg=self.up_dmg()))
        self.audio.play('mg', .15)

    def air_bomb(self):
        a = self.a
        p = a['p']
        if p['dead'] or p['bcd'] > 0 or a['phase'] != 'play':
            return
        p['bcd'] = 0.55
        tx, ty = p['x'], max(60.0, p['y'] - 200)
        a['bombs'].append(dict(x0=p['x'], y0=p['y'], x1=tx, y1=ty, t=0.0, T=0.7))
        self.audio.play('launch', .35)

    def air_hit_ground(self, g, dmg):
        a = self.a
        g['hp'] -= dmg
        if g['hp'] <= 0 and g in a['ground']:
            a['ground'].remove(g)
            pts = 300 if g['kind'] == 'sam' else 400
            self.add_score(pts)
            self.pop('+%d' % pts, g['x'], g['y'] - 18)
            self.air_boom(g['x'], g['y'], 1.2, True)

    def air_hurt(self, dmg):
        a = self.a
        p = a['p']
        if p['dead'] or p['inv'] > 0 or a['phase'] != 'play':
            return
        if p['shield'] > 0:
            p['shield'] = max(0.0, p['shield'] - 1.2)
            p['inv'] = 0.25
            self.audio.play('hit', .3)
            return
        p['hp'] -= dmg
        p['inv'] = 1.3
        p['wl'] = max(1, p['wl'] - (1 if dmg >= 20 else 0))
        self.shake = max(self.shake, 8)
        self.audio.play('hit', .6)
        self.pop('-%d' % dmg, p['x'], p['y'] - 40, (255, 110, 100))

    def upd_aerial(self, dt):
        a = self.a
        p = a['p']
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        a['t'] += dt
        sc = self.AIR_SCROLL
        a['scroll'] += sc * dt
        p['cd'] = max(0.0, p['cd'] - dt)
        p['bcd'] = max(0.0, p['bcd'] - dt)
        p['inv'] = max(0.0, p['inv'] - dt)
        p['shield'] = max(0.0, p['shield'] - dt)
        if not p['dead']:
            mx = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            my = (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0) - (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0)
            n = math.hypot(mx, my) or 1.0
            p['vx'] += (mx / n * 320 - p['vx']) * min(1, dt * 12)
            p['x'] = clamp(p['x'] + p['vx'] * dt, 44, W - 44)
            p['y'] = clamp(p['y'] + my / n * 300 * dt, 150, H - 70)
            p['rapid'] = max(0.0, p['rapid'] - dt)
            p['homing'] = max(0.0, p['homing'] - dt)
            if self.up_n('homing'):
                p['homing'] = max(p['homing'], 5.0)
            p['mcd'] = max(0.0, p['mcd'] - dt)
            if (keys[pygame.K_SPACE] or keys[pygame.K_f] or mouse[0]) and p['cd'] <= 0 and a['phase'] == 'play':
                p['cd'] = (0.07 if p['rapid'] > 0 else 0.11) * self.up_reload()
                self.air_fire_player()
                if p['homing'] > 0 and p['mcd'] <= 0:
                    p['mcd'] = 0.45
                    for sd in (-1, 1):
                        vx_, vy_ = vec(sd * 28, 440)
                        a['pbul'].append(dict(x=p['x'] + sd * 20, y=p['y'] - 10, vx=vx_, vy=-abs(vy_), dmg=2 * self.up_dmg(), hom=True))
            if random.random() < dt * 40:
                self.fx.add('glow', p['x'] + random.uniform(-3, 3), p['y'] + 42, 0, 60, 0.15, 8, 3, (255, 150, 60))
        # escenario
        for isl in a['isl'][:]:
            isl['y'] += sc * dt
            if isl['y'] > H + isl['r'] * 2.4:
                a['isl'].remove(isl)
        for g in a['ground'][:]:
            g['y'] += sc * dt                              # el mar y las islas avanzan juntos
            if g['kind'] == 'boat':
                nx = g['x'] + g['vx'] * dt
                if self.air_on_land(nx, g['y'], 34) or not 60 < nx < W - 60:
                    g['vx'] = -g['vx']                     # los barcos no atraviesan las islas: rebotan
                else:
                    g['x'] = nx
            else:
                g['x'] += g['vx'] * dt
            if g['y'] > H + 60:
                a['ground'].remove(g)
                continue
            if 20 < g['y'] < H * 0.7 and not p['dead']:
                g['ang'] = bearing(p['x'] - g['x'], p['y'] - g['y'])
                g['cd'] -= dt
                if g['cd'] <= 0:
                    g['cd'] = random.uniform(2.2, 3.4)
                    self.air_ebul(g['x'], g['y'], g['ang'] + random.uniform(-4, 4), 190)
        for c in a['clouds'][:]:
            c['y'] += c['v'] * dt
            if c['y'] > H + 120:
                a['clouds'].remove(c)
        a['isl_t'] -= dt
        if a['isl_t'] <= 0:
            a['isl_t'] = random.uniform(4.0, 7.0)
            self.air_spawn_island(random.uniform(60, W - 60), -260)
        a['cloud_t'] -= dt
        if a['cloud_t'] <= 0:
            a['cloud_t'] = random.uniform(0.7, 1.6)
            self.air_spawn_cloud(-140)
        a['boat_t'] -= dt
        if a['boat_t'] <= 0 and a['phase'] == 'play' and not a['boss']:
            a['boat_t'] = random.uniform(8, 13)
            xs = [random.uniform(120, W - 120) for _ in range(40)]
            x = next((x_ for x_ in xs if not any(self.air_on_land(x_, y_, 50) for y_ in (-50.0, -90.0, -10.0))), None)
            if x is None:
                a['boat_t'] = 1.0                          # todo el frente es tierra: reintenta enseguida
            else:
                a['ground'].append(dict(kind='boat', x=x, y=-50.0, vx=random.uniform(-25, 25), hp=4, cd=2.0, ang=180.0))
        # guion
        if a['phase'] == 'play':
            while a['events'] and a['events'][0][0] <= a['t']:
                _, kind, x = a['events'].pop(0)
                self.air_spawn_formation(kind, x)
            if a['boss'] is None and a['t'] >= a['boss_t']:
                a['boss'] = self.air_boss_make()
                self.audio.play('alarm')
                from .air_boss import AIR_BOSSES
                spec = AIR_BOSSES[a['boss']['k']]
                self.banner('¡ALERTA! %s' % spec['name'], '', (255, 90, 70), 2.6)
                self.say('jefe_avion', AIR_LINES[a['boss']['k'] % 6][0], 'bad', pose='', v=a['boss']['k'] % 6 + 1, name=spec['name'])
                self.say('piloto', '¡Jefe a la vista! ' + spec['hint'], 'bad')
        # enemigos
        for f in a['foes'][:]:
            f['t'] += dt
            f['hit'] = max(0.0, f['hit'] - dt)
            k = f['kind']
            if k == 'viper' and f.get('spiral') is not None:
                f['y'] += (96 + 3 * self.wave) * dt
                f['x'] = f['bx'] + math.cos(f['t'] * 2.6 + f['spiral'] * 1.05) * 120
            elif k == 'viper':
                f['y'] += (110 + 3 * self.wave) * dt
                f['x'] = f['bx'] + math.sin(f['t'] * 2.2 + f['ph']) * 55
            elif k == 'kami':
                if f['t'] > 0.45 and not p['dead']:
                    f['a'] = (f['a'] + clamp(angle_diff(f['a'], bearing(p['x'] - f['x'], p['y'] - f['y'])), -105 * dt, 105 * dt)) % 360
                vx_, vy_ = vec(f['a'], (220 if f['t'] < 0.45 else 270) * dt)
                f['x'] += vx_
                f['y'] += vy_
            elif k == 'mine':
                f['y'] += self.AIR_SCROLL * dt
                if not p['dead'] and dist(f['x'], f['y'], p['x'], p['y']) < 40:
                    self.air_hurt(15)
                    self.air_kill_foe(f)
                    continue
            elif k == 'gunship':
                f['y'] += (70 if (f['y'] < 190 and f['t'] < 8) else (0 if f['t'] < 8 else 120)) * dt
                f['x'] = f['bx'] + math.sin(f['t'] * 0.6) * 110
            elif k == 'stealth' and f['mode'] != 0:
                if f['t'] < 1.3:
                    f['x'] += -f['mode'] * 230 * dt
                    f['y'] += 30 * dt
                else:
                    if f['t'] < 1.45:
                        f['vx'] = clamp((p['x'] - f['x']) * 1.4, -230, 230)
                    f['x'] += f['vx'] * dt
                    f['y'] += 270 * dt
            elif k == 'stealth':
                f['y'] += 150 * dt
                if f['t'] < 2.4:
                    f['x'] += clamp(p['x'] - f['x'], -1, 1) * 60 * dt
            elif k == 'bomber':
                f['y'] += (45 if f['y'] < 150 or f['t'] > 18 else 0) * dt
                f['x'] = f['bx'] + math.sin(f['t'] * 0.6) * 140
            f['cd'] -= dt
            if f['cd'] <= 0 and 30 < f['y'] < H * 0.65 and not p['dead'] and a['phase'] == 'play':
                aim = bearing(p['x'] - f['x'], p['y'] - f['y'])
                if k == 'viper':
                    f['cd'] = random.uniform(2.0, 3.6)
                    self.air_ebul(f['x'], f['y'] + 20, aim + random.uniform(-3, 3), 210)
                elif k == 'stealth':
                    f['cd'] = random.uniform(2.2, 3.0)
                    for da in (-14, 0, 14):
                        self.air_ebul(f['x'], f['y'] + 20, aim + da, 230)
                elif k in ('kami', 'mine'):
                    f['cd'] = 99.0
                elif k == 'gunship':
                    f['cd'] = 1.7
                    for da in (-16, -8, 0, 8, 16):
                        self.air_ebul(f['x'], f['y'] + 30, aim + da, 215)
                    for sx in (-1, 1):
                        self.air_ebul(f['x'] + sx * 30, f['y'] + 10, 180, 190)
                else:
                    f['cd'] = 1.15
                    f['mode'] += 1
                    if f['mode'] % 2:
                        for i in range(12):
                            self.air_ebul(f['x'], f['y'] + 10, i * 30 + f['t'] * 20, 150, 6)
                    else:
                        for da in (-18, -9, 0, 9, 18):
                            self.air_ebul(f['x'], f['y'] + 30, aim + da, 220)
            if f['y'] > H + 90 or f['x'] < -140 or f['x'] > W + 140:
                a['foes'].remove(f)
                form = a['forms'].get(f['fid'])
                if form:
                    form['escaped'] = True
        # jefe
        b = a['boss']
        if b and not a['boss_dead']:
            self.air_boss_update(dt)
        self.air_ambient_update(dt)
        # balas del jugador
        for bl in a['pbul'][:]:
            if bl.get('hom'):
                self.air_homing(bl, dt)
            bl['x'] += bl['vx'] * dt
            bl['y'] += bl['vy'] * dt
            if bl['y'] < -30 or bl['x'] < -30 or bl['x'] > W + 30:
                a['pbul'].remove(bl)
                continue
            hit = None
            for f in a['foes']:
                if dist(bl['x'], bl['y'], f['x'], f['y']) < {'viper': 24, 'stealth': 30, 'bomber': 60, 'kami': 20, 'gunship': 38, 'mine': 20}[f['kind']]:
                    hit = f
                    break
            if hit:
                hit['hp'] -= bl.get('dmg', 1)
                hit['hit'] = 0.08
                a['pbul'].remove(bl)
                self.fx.add('spark', bl['x'], bl['y'], random.uniform(-100, 100), random.uniform(-60, 60), 0.2, col=(255, 230, 150), drag=2)
                if hit['hp'] <= 0:
                    self.air_kill_foe(hit)
                continue
            if b and not a['boss_dead'] and self.air_boss_hit(bl):
                a['pbul'].remove(bl)
                continue
        # balas enemigas
        for eb in a['ebul'][:]:
            eb['x'] += eb['vx'] * dt
            eb['y'] += eb['vy'] * dt
            if not (-30 < eb['x'] < W + 30 and -30 < eb['y'] < H + 30):
                a['ebul'].remove(eb)
            elif not p['dead'] and dist(eb['x'], eb['y'], p['x'], p['y']) < eb['r'] + 8:
                a['ebul'].remove(eb)
                self.air_hurt(10)
        # bombas
        for bm in a['bombs'][:]:
            bm['t'] += dt
            if bm['t'] >= bm['T']:
                a['bombs'].remove(bm)
                self.fx.add('ring', bm['x1'], bm['y1'], life=0.5, r0=6, r1=60, col=(255, 230, 170))
                self.air_boom(bm['x1'], bm['y1'], 1.0)
                for g in a['ground'][:]:
                    if dist(g['x'], g['y'], bm['x1'], bm['y1']) < 58:
                        self.air_hit_ground(g, 3)
        # choque contra enemigos
        if not p['dead']:
            for f in a['foes'][:]:
                if dist(f['x'], f['y'], p['x'], p['y']) < {'viper': 28, 'stealth': 32, 'bomber': 56, 'kami': 24, 'gunship': 40, 'mine': 26}[f['kind']] and p['inv'] <= 0:
                    self.air_hurt(20)
                    if f['kind'] not in ('bomber', 'gunship'):
                        self.air_kill_foe(f)
        if b and not a['boss_dead'] and not p['dead'] and b['alpha'] > 0.5 and dist(b['x'], b['y'], p['x'], p['y']) < b['r'] * 0.9:
            self.air_hurt(20)
        # jefe derrotado / jugador caído
        if b and not a['boss_dead'] and b['hp'] <= 0:
            a['boss_dead'] = True
            from .air_boss import AIR_BOSSES
            self.say('jefe_avion', AIR_LINES[b['k'] % 6][1], 'warn', pose='bad', v=b['k'] % 6 + 1, name=AIR_BOSSES[b['k']]['name'])
            self.add_score(4000)
            for _ in range(10):
                self.air_boom(b['x'] + random.uniform(-90, 90), b['y'] + random.uniform(-60, 60), 1.6, True, 'boom_l')
            for f in a['foes'][:]:
                self.air_boom(f['x'], f['y'], 1.0)
                a['foes'].remove(f)
            a['ebul'].clear()
            self.shake = 22
            if a['phase'] == 'play':
                a['phase'], a['pt'] = 'result', 0.0
                bonus = 500 + 100 * self.wave
                self.add_score(bonus)
                self.ammo = min(40, self.ammo + 8)
                self.audio.play('win', .7)
                self.banner('¡VICTORIA AÉREA!', 'Bajas: %d   Jefe +4000   Bonus +%d   (+8 munición)' % (a['kills'], bonus),
                            (120, 255, 160), 3.2)
                self.say('piloto', '¡Cielo despejado! Volvemos a la base.', 'ok')
        if not p['dead'] and p['hp'] <= 0:
            p['dead'] = True
            self.air_boom(p['x'], p['y'], 1.8, True, 'boom_l')
            self.shake = 16
            if a['phase'] == 'play':
                a['phase'], a['fail'], a['pt'] = 'result', True, -1.0
                self.banner('¡AVIÓN DERRIBADO!', 'El ataque aéreo daña la ciudad', (255, 80, 70), 3.0)
                self.say('piloto', '¡Me dieron! Perdí el avión... la ciudad queda expuesta.', 'bad')
        self.fx.update(dt)
        if a['phase'] == 'result':
            a['pt'] += dt
            if a['pt'] > 3.0:
                self.end_aerial()

    def end_aerial(self):
        a = self.a
        city = a['city']
        if a['fail'] and city and not city['dead']:
            city['hp'] = max(0.0, city['hp'] - 25)
            self.toast('Los cazas bombardearon %s: -25%%' % city['name'], (255, 140, 90))
            if city['hp'] <= 0:
                city['dead'] = True
        self.warned = False
        self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        if all(c['dead'] for c in self.cities):
            return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---- batalla aérea
    def draw_aerial(self, cv):
        a = self.a
        p = a['p']
        t = self.t
        A = self.air
        self.draw_ocean(cv, 0, -a['scroll'], t)
        for c in a['clouds']:
            cs, sh = A['clouds'][c['i']]
            w2, h2 = int(cs.get_width() * c['s']), int(cs.get_height() * c['s'])
            sh2 = pygame.transform.smoothscale(sh, (w2, h2)) if c['s'] != 1 else sh
            sh2.set_alpha(55)
            cv.blit(sh2, (c['x'] - w2 // 2 + 70, c['y'] - h2 // 2 + 110))
        for isl in a['isl']:
            spr = A['isl'][isl['i']]
            cv.blit(spr, (isl['x'] - spr.get_width() // 2, isl['y'] - spr.get_height() // 2))
        for g in a['ground']:
            if g['kind'] == 'sam':
                cv.blit(A['gbase'], (g['x'] - A['gbase'].get_width() // 2, g['y'] - A['gbase'].get_height() // 2))
                self.blit_turret(cv, self.tur_e, g['x'], g['y'], g['ang'])
            else:
                self.blit_ship(cv, 'e_map', g['x'], g['y'], 180 + g['vx'] * 0.3)
        if not p['dead']:
            tx, ty = int(p['x']), int(max(60, p['y'] - 200))
            draw_circ(cv, tx, ty, 26, (255, 230, 170), 70, 1)
            pygame.draw.line(cv, (255, 230, 170), (tx - 8, ty), (tx + 8, ty), 1)
            pygame.draw.line(cv, (255, 230, 170), (tx, ty - 8), (tx, ty + 8), 1)
        for bm in a['bombs']:
            k = bm['t'] / bm['T']
            x, y = lerp(bm['x0'], bm['x1'], k), lerp(bm['y0'], bm['y1'], k)
            draw_circ(cv, x, y, 5, (0, 0, 0), 90)
            r = int(7 - 3 * k)
            pygame.draw.ellipse(cv, (36, 40, 46), (x - r, y - 40 * (1 - k) - r * 1.6, r * 2, r * 3.2))
            pygame.draw.ellipse(cv, (110, 118, 128), (x - r * 0.5, y - 40 * (1 - k) - r * 1.4, r, r * 1.4))
        for c in a['clouds']:
            cs, _ = A['clouds'][c['i']]
            w2, h2 = int(cs.get_width() * c['s']), int(cs.get_height() * c['s'])
            spr = pygame.transform.smoothscale(cs, (w2, h2)) if c['s'] != 1 else cs
            spr.set_alpha(215)
            cv.blit(spr, (c['x'] - w2 // 2, c['y'] - h2 // 2))
        sh_off = (34, 52)

        def shadow(spr, x, y):
            sh = A['shadows'].get(id(spr))
            if sh is None:
                sh = A['shadows'][id(spr)] = make_shadow(spr)
            sh.set_alpha(75)
            cv.blit(sh, (x - sh.get_width() // 2 + sh_off[0], y - sh.get_height() // 2 + sh_off[1]))
        for f in a['foes']:
            if f['kind'] == 'mine':
                mx_, my_ = int(f['x']), int(f['y'])
                if 'mine' not in A:
                    A['mine'] = load_png_sprite('mina', width=54, flip=False) or False
                if A['mine']:
                    ms = pygame.transform.rotate(A['mine'], -t * 28)
                    cv.blit(ms, (mx_ - ms.get_width() // 2, my_ - ms.get_height() // 2))
                    continue
                for ang_ in range(8):
                    a2 = ang_ * 0.785 + t * 0.5
                    pygame.draw.line(cv, (24, 26, 30), (mx_, my_), (mx_ + math.cos(a2) * 24, my_ + math.sin(a2) * 24), 4)
                pygame.draw.circle(cv, (20, 22, 26), (mx_, my_), 17)
                pygame.draw.circle(cv, (92, 98, 108), (mx_, my_), 14)
                pygame.draw.circle(cv, (255, 70, 60) if int(t * 4 + f['x']) % 2 == 0 else (110, 30, 30), (mx_, my_), 5)
                continue
            if f['kind'] == 'kami' and 'kami' not in A:
                kv = load_png_sprite('avion_kamikaze', width=48)
                if kv is None:
                    kv = A['viper'].copy()
                    kv.fill((255, 90, 70, 0), special_flags=pygame.BLEND_RGB_ADD)
                A['kami'] = kv
            if f['kind'] == 'gunship' and 'gunship' not in A:
                gb_ = A['bomber']
                A['gunship'] = load_png_sprite('avion_artillera_pequena', width=110) or pygame.transform.smoothscale(gb_, (int(gb_.get_width() * 0.62), int(gb_.get_height() * 0.62)))
            spr = A[{'viper': 'viper', 'stealth': 'stealth', 'bomber': 'bomber', 'kami': 'kami', 'gunship': 'gunship'}[f['kind']]]
            if f['kind'] == 'kami':
                spr = pygame.transform.rotate(spr, -(f['a'] - 180))
            shadow(spr, f['x'], f['y'])
            if f['hit'] > 0:
                spr = spr.copy()
                spr.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            cv.blit(spr, (f['x'] - spr.get_width() // 2, f['y'] - spr.get_height() // 2))
            if f['kind'] in ('bomber', 'gunship'):
                for sx in (-1, 1):
                    glow(cv, f['x'] + sx * 22, f['y'] - 18, 20, (255, 140, 60), 0.7)
                pygame.draw.rect(cv, (8, 12, 24), (f['x'] - 40, f['y'] - 80, 80, 6))
                pygame.draw.rect(cv, (240, 80, 70), (f['x'] - 39, f['y'] - 79, int(78 * f['hp'] / f['max']), 4))
            else:
                glow(cv, f['x'], f['y'] - 36 if f['kind'] == 'viper' else f['y'] - 28, 12, (255, 150, 70), 0.6)
        b = a['boss']
        if b and not a['boss_dead']:
            self.air_boss_draw(cv, shadow)
        if not p['dead']:
            shadow(A['f16'], p['x'], p['y'])
            spr = A['f16']
            bank = clamp(p['vx'] / 320, -1, 1)
            if abs(bank) > 0.05:
                spr = pygame.transform.smoothscale(spr, (int(spr.get_width() * (1 - 0.22 * abs(bank))), spr.get_height()))
            blink = p['inv'] > 0 and int(t * 18) % 2 == 0
            fl_ = 14 + 8 * math.sin(t * 60)
            pygame.draw.polygon(cv, (255, 170, 60), [(p['x'] - 4, p['y'] + 42), (p['x'] + 4, p['y'] + 42), (p['x'], p['y'] + 42 + fl_ * 2)])
            pygame.draw.polygon(cv, (255, 245, 200), [(p['x'] - 2, p['y'] + 42), (p['x'] + 2, p['y'] + 42), (p['x'], p['y'] + 42 + fl_)])
            glow(cv, p['x'], p['y'] + 48, 26, (255, 160, 70), 0.8)
            if not blink:
                cv.blit(spr, (p['x'] - spr.get_width() // 2, p['y'] - spr.get_height() // 2))
            if p['shield'] > 0:
                pulse = 0.6 + 0.4 * math.sin(t * 10)
                draw_circ(cv, p['x'], p['y'], 54, (110, 210, 255), 50 * pulse + 20)
                draw_circ(cv, p['x'], p['y'], 54, (170, 235, 255), 200, 2)
        self.air_ambient_draw(cv)
        for bl in a['pbul']:
            if bl.get('hom'):
                glow(cv, bl['x'], bl['y'], 14, (190, 130, 255), 0.8)
                pygame.draw.line(cv, (200, 150, 255), (bl['x'], bl['y']), (bl['x'] - bl['vx'] * 0.04, bl['y'] - bl['vy'] * 0.04), 5)
                continue
            pygame.draw.line(cv, (255, 244, 170), (bl['x'], bl['y']), (bl['x'] - bl['vx'] * 0.03, bl['y'] - bl['vy'] * 0.03), 3)
            pygame.draw.line(cv, (255, 255, 255), (bl['x'], bl['y']), (bl['x'] - bl['vx'] * 0.015, bl['y'] - bl['vy'] * 0.015), 1)
        for eb in a['ebul']:
            glow(cv, eb['x'], eb['y'], eb['r'] * 3, (255, 90, 60), 0.8)
            pygame.draw.circle(cv, (255, 120, 70), (int(eb['x']), int(eb['y'])), eb['r'])
            pygame.draw.circle(cv, (255, 235, 200), (int(eb['x']), int(eb['y'])), max(2, eb['r'] - 2))
        self.fx.draw(cv)
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, (160, 200, 240), 26, 42)
        self.panel(cv, (14, H - 100, 330, 86), 160)
        self.bar(cv, 26, H - 90, 306, 24, p['hp'] / 100, (80, 220, 110) if p['hp'] > 35 else (240, 80, 70), 'F-16 %d%%' % max(0, p['hp']))
        self.text(cv, 'ARMA', self.f_s, (235, 245, 255), 26, H - 56)
        for i in range(4):
            pygame.draw.rect(cv, (255, 190, 70) if i < p['wl'] else (50, 56, 70), (86 + i * 26, H - 54, 20, 12), border_radius=3)
        self.text(cv, 'BOMBA', self.f_s, (235, 245, 255), 206, H - 56)
        rdy = 1 - clamp(p['bcd'] / 0.55, 0, 1)
        pygame.draw.rect(cv, (8, 12, 24), (270, H - 54, 60, 12))
        pygame.draw.rect(cv, (120, 255, 160) if rdy >= 1 else (255, 200, 80), (271, H - 53, int(58 * rdy), 10))
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        b = a['boss']
        if b and not a['boss_dead']:
            from .air_boss import AIR_BOSSES
            self.text(cv, AIR_BOSSES[b['k']]['name'], self.f_m, (255, 110, 90), W // 2, 16, 'c')
            self.bar(cv, W // 2 - 210, 44, 420, 26, b['hp'] / b['max'], (240, 80, 70), 'JEFE')
        else:
            self.text(cv, '¡BATALLA AÉREA!', self.f_m, (100, 180, 255), W // 2, 16, 'c')
            self.bar(cv, W // 2 - 210, 44, 420, 26, a['t'] / a['boss_t'], (100, 180, 255), 'AVANCE')
        yy_ = 90
        if p['shield'] > 0:
            self.text(cv, 'ESCUDO %.0f' % p['shield'], self.f_s, (150, 225, 255), W - 20, yy_, 'r')
            yy_ += 20
        if p['rapid'] > 0:
            self.text(cv, 'RÁFAGA %.0f' % p['rapid'], self.f_s, (255, 235, 110), W - 20, yy_, 'r')
            yy_ += 20
        if p['homing'] > 0 and not self.up_n('homing'):
            self.text(cv, 'MISILES GUÍA %.0f' % p['homing'], self.f_s, (200, 150, 255), W - 20, yy_, 'r')
        self.text(cv, 'WASD mover | ESPACIO/clic disparar | B/clic der. bomba', self.f_s, (210, 225, 255), W - 14, H - 30, 'r')
