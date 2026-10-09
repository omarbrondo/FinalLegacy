"""Baterías aliadas: de vez en cuando una es invadida y el jugador toma su mando. Defensa en 4 tandas contra lanchas con soldados,
cazas y bombarderos, destructores y un crucero. Si cae, la batería pasa a ser enemiga; si la destruyen queda un islote desierto con ruinas."""
import math
import random
import pygame
from .common import H, W, Particles, bearing, clamp, dist, draw_circ, glow, vec

C = (W // 2, H // 2 + 6)                  # posición de la batería en pantalla
ISL_R = 118                               # radio del islote dibujado
SHORE = 150                               # distancia a la que las lanchas varan en la playa
BAT_R = 34                                # radio del búnker
STAGES = 4
ATTACK_WARN = 80.0                        # segundos que hay para llegar a una batería invadida
TAKE_R = 230                              # distancia para tomar el mando (tecla E)


class BatDefMixin:
    # ------------------------------------------------------------------ en el mapa
    def ally_nest_tick(self, nst, dt):
        """Batería aliada: ayuda con fuego a distancia contra barcos enemigos y avisa si la están invadiendo."""
        nst['cool'] = max(0.0, nst['cool'] - dt)
        nst['fire'] = max(0.0, nst.get('fire', 0.0) - dt)
        if nst['fire'] <= 0:
            for en in self.enemies:
                if en.get('sub') or en.get('is_boss') or en.get('shield'):
                    continue
                if dist(en['x'], en['y'], nst['x'], nst['y']) < 330:
                    en['hp'] -= 2.0 + 0.2 * nst.get('vet', 0)
                    nst['fire'] = 3.2
                    nst['ang'] = bearing(en['x'] - nst['x'], en['y'] - nst['y'])
                    nst['flash'] = 0.25
                    break
        nst['flash'] = max(0.0, nst.get('flash', 0.0) - dt)

    def bat_tick(self, dt):
        """Programa las invasiones a baterías aliadas, cuenta el tiempo que queda y avisa cuando el jugador está cerca."""
        allies = [n for n in self.nests if n['alive'] and n.get('ally')]
        attacked = [n for n in allies if n.get('atk')]
        self.bat_atk_t = getattr(self, 'bat_atk_t', 70.0) - dt
        busy = self.attack is not None or self.warned or self.rescue is not None or self.raid is not None
        if self.bat_atk_t <= 0 and allies and not attacked and not busy:
            far = [n for n in allies if dist(n['x'], n['y'], self.sx, self.sy) > 500] or allies
            n = random.choice(far)
            n['atk'] = dict(t=ATTACK_WARN)
            self.bat_atk_t = random.uniform(130, 190) - 6 * self.wave
            self.audio.play('alarm', .6)
            self.banner('¡BATERÍA ALIADA INVADIDA!', 'Llegá en %d s y presioná E para tomar el mando' % ATTACK_WARN, (255, 120, 90), 4.0)
            self.say('marinero', '¡Capitán, invaden una batería aliada! Si llegamos, podemos tomar los cañones y defenderla.', 'warn')
        for n in attacked:
            n['atk']['t'] -= dt
            if n['atk']['t'] <= 0:
                self.bat_lost(n, 'No llegamos a tiempo')
            elif dist(n['x'], n['y'], self.sx, self.sy) < TAKE_R and int(self.t * 2) % 2 == 0:
                pass
        self.bat_near = next((n for n in attacked if dist(n['x'], n['y'], self.sx, self.sy) < TAKE_R), None)

    def bat_lost(self, n, why):
        """La batería cae: pasa a ser enemiga (con su vida completa) y ataca a quien se acerque."""
        n['ally'] = False
        n['atk'] = None
        n['seen'] = True
        hp = float(14 + 4 * self.wave)
        n['hp'] = n['max'] = hp
        n['cool'] = 10.0
        self.audio.play('lose', .5)
        self.banner('¡BATERÍA PERDIDA!', '%s: ahora es enemiga' % why, (255, 110, 90), 3.6)
        self.say('marinero', 'La batería cayó en manos enemigas. Cuidado al acercarse, capitán.', 'bad')

    def try_batdef(self):
        n = getattr(self, 'bat_near', None)
        if n is None or not n.get('atk'):
            return False
        self.start_batdef(n)
        return True

    def draw_ally_nest(self, cv, nst, nx_, ny_):
        t = self.t
        pygame.draw.circle(cv, (118, 140, 108), (int(nx_), int(ny_)), 17)
        pygame.draw.circle(cv, (70, 100, 84), (int(nx_), int(ny_)), 11)
        ex_, ey_ = vec(nst['ang'], 18)
        pygame.draw.line(cv, (52, 80, 70), (nx_, ny_), (nx_ + ex_, ny_ + ey_), 4)
        if nst.get('flash', 0) > 0:
            glow(cv, nx_ + ex_, ny_ + ey_, 30, (255, 220, 140), 0.8)
        if nst.get('atk'):
            pul = 0.5 + 0.5 * math.sin(t * 8)
            draw_circ(cv, nx_, ny_, 60 + 14 * pul, (255, 80, 70), 60 + 70 * pul, 3)
            glow(cv, nx_, ny_, 70, (255, 90, 70), 0.5 + 0.3 * pul)
            self.text(cv, '¡INVADIDA! %d s' % math.ceil(nst['atk']['t']), self.f_s, (255, 150, 130), nx_, ny_ + 26, 'c')
            if getattr(self, 'bat_near', None) is nst:
                self.text(cv, 'E: TOMAR EL MANDO', self.f_m, (255, 235, 130), nx_, ny_ - 54, 'c')
        else:
            draw_circ(cv, nx_, ny_, 330, (110, 255, 160), 18, 1)
            self.text(cv, 'BATERÍA ALIADA', self.f_s, (150, 255, 190), nx_, ny_ + 24, 'c')

    def draw_nest_ruin(self, cv, nst, nx_, ny_):
        """Islote desierto: cráter, restos del cañón y marcas de quemado (no se regenera)."""
        x, y = int(nx_), int(ny_)
        rnd = random.Random(int(nst.get('s', 7)) * 31 + 5)
        pygame.draw.ellipse(cv, (36, 32, 28), (x - 22, y - 15, 44, 30))
        pygame.draw.ellipse(cv, (18, 16, 14), (x - 15, y - 10, 30, 20))
        pygame.draw.ellipse(cv, (86, 76, 62), (x - 22, y - 15, 44, 30), 2)
        for _ in range(8):
            a = rnd.uniform(0, 6.28)
            d = rnd.uniform(14, 34)
            pygame.draw.circle(cv, (rnd.randint(40, 70),) * 3, (int(x + math.cos(a) * d), int(y + math.sin(a) * d * 0.7)), rnd.randint(2, 4))
        a = rnd.uniform(0, 6.28)
        pygame.draw.line(cv, (62, 64, 68), (x + math.cos(a) * 8, y + math.sin(a) * 6), (x + math.cos(a) * 32, y + math.sin(a) * 22), 4)       # cañón caído
        if random.random() < 0.04:
            self.fxm.add('smoke', nst['x'] + random.uniform(-8, 8), nst['y'], 0, -16, 2.0, 4, 14, (50, 48, 46))

    # ------------------------------------------------------------------ inicio
    def start_batdef(self, nst):
        w = self.wave
        hp = 110 + 9 * w
        self.fx = Particles()
        self.bd = dict(nst=nst, hp=float(hp), max=float(hp), stage=0, phase='intro', pt=0.0, t=0.0, spawns=[], enemies=[], bullets=[], shells=[],
                       eshells=[], bombs=[], flaks=[], tracers=[], ang=-1.57, heat=0.0, locked=False, mg_cd=0.0, sh_cd=0.0, fl_cd=0.0, rmb=False, spc=False,
                       recoil=0.0, flash=0.0, hit=0.0, kills=0, pts=0, sd=int(nst.get('s', 11)), end_t=0.0, soldiers_in=0)
        self.aim = [float(C[0]), float(C[1] - 220)]
        self.bd_stage_setup()
        self.go('batdef')
        self.banner('¡DEFENDÉ LA BATERÍA!', 'Clic: ametralladora  |  Clic derecho: proyectil pesado  |  ESPACIO: cortina antiaérea', (255, 215, 120), 4.5)
        self.say('artillero', '¡Cañones a su mando, capitán! Lanchas de desembarco, cazas y destructores en camino. ¡No dejemos que tomen la isla!', 'warn')

    def bd_stage_setup(self):
        bd = self.bd
        w, s = self.wave, bd['stage']
        sp = []
        def boats(n, t0, gap):
            base = random.uniform(0, 6.28)
            for i in range(n):
                sp.append((t0 + i * gap, 'boat', base + i * 2.1 + random.uniform(-0.5, 0.5)))
        def planes(n, t0, gap):
            for i in range(n):
                sp.append((t0 + i * gap, 'plane', random.uniform(0, 6.28)))
        if s == 0:
            boats(3 + w // 2, 1.0, 2.6)
        elif s == 1:
            boats(2 + w // 2, 1.0, 3.2)
            planes(2 + w // 3, 4.0, 3.5)
        elif s == 2:
            sp.append((1.0, 'destroyer', random.uniform(0, 6.28)))
            if w >= 3:
                sp.append((5.0, 'destroyer', random.uniform(0, 6.28)))
            boats(3, 3.0, 3.0)
            planes(2 + w // 4, 6.0, 3.0)
        else:
            sp.append((1.0, 'cruiser', random.uniform(0, 6.28)))
            boats(2 + w // 4, 4.0, 4.0)
            planes(3, 7.0, 3.0)
        bd['spawns'] = sorted(sp)
        bd['stage_t'] = 0.0

    # ------------------------------------------------------------------ enemigos
    def bd_spawn(self, kind, a):
        bd = self.bd
        w = self.wave
        R = 640
        if kind == 'boat':
            x, y = C[0] + math.cos(a) * R, C[1] + math.sin(a) * R * 0.8
            hp = 6 + w
            bd['enemies'].append(dict(kind='boat', x=x, y=y, a=a, hp=float(hp), max=float(hp), sp=72.0 + 3 * w, n=min(6, 3 + w // 3), h=0.0, r=24))
        elif kind == 'plane':
            sx = random.choice((-80, W + 80))
            sy = random.uniform(120, H - 120)
            tx, ty = C[0] + random.uniform(-110, 110), C[1] + random.uniform(-90, 90)
            h = bearing(tx - sx, ty - sy)
            hp = 2 + w // 3
            bd['enemies'].append(dict(kind='plane', x=float(sx), y=float(sy), h=h, hp=float(hp), max=float(hp), sp=330.0 + 8 * w, bombed=False, r=22, gun=0.0, fighter=(w >= 3 and random.random() < 0.5)))
        elif kind == 'destroyer':
            x, y = C[0] + math.cos(a) * R, C[1] + math.sin(a) * R * 0.8
            hp = 30 + 4 * w
            bd['enemies'].append(dict(kind='destroyer', x=x, y=y, a=a, hp=float(hp), max=float(hp), cd=3.5, h=0.0, r=38, sp=60.0))
        elif kind == 'cruiser':
            x, y = C[0] + math.cos(a) * 700, C[1] + math.sin(a) * 560
            hp = 60 + 10 * w
            bd['enemies'].append(dict(kind='cruiser', x=x, y=y, a=a, hp=float(hp), max=float(hp), cd=4.0, bt=7.0, h=0.0, r=56, sp=42.0))

    def bd_damage(self, e, dmg, src='mg'):
        if e['kind'] == 'destroyer':
            dmg *= 0.22 if src == 'mg' else 1.0
        elif e['kind'] == 'cruiser':
            dmg *= 0.14 if src == 'mg' else 1.0
        e['hp'] -= dmg
        e['flash'] = 0.12
        if e['hp'] <= 0 and not e.get('dead'):
            self.bd_kill(e)

    def bd_kill(self, e):
        bd = self.bd
        e['dead'] = True
        bd['kills'] += 1
        k = e['kind']
        if k == 'soldier':
            bd['pts'] += 20
            self.fx.add('spark', e['x'], e['y'], random.uniform(-40, 40), random.uniform(-40, 40), 0.3, col=(255, 200, 120))
            return
        pts = {'boat': 60, 'plane': 90, 'destroyer': 220, 'cruiser': 700}[k]
        bd['pts'] += pts
        big = k in ('destroyer', 'cruiser')
        self.fx.explode_art(e['x'], e['y'], 1.5 if k == 'cruiser' else (1.2 if big else 0.9), big or k == 'plane')
        self.audio.play('boom_l' if big else 'boom_s', .8 if big else .55)
        self.shake = max(self.shake, 10 if big else 4)
        if k == 'boat':                                   # la lancha hundida se lleva a los soldados
            self.fx.splash(e['x'], e['y'], 1.0)
        for _ in range(6 if big else 2):
            self.fx.add('smoke', e['x'] + random.uniform(-20, 20), e['y'] + random.uniform(-14, 14), random.uniform(-14, 14), -24, random.uniform(1.4, 2.6), 6, 22, (46, 44, 44))

    def bd_aoe(self, x, y, rad, dmg, air=False):
        for e in self.bd['enemies']:
            if e.get('dead') or (e['kind'] == 'plane') != air:
                continue
            d = dist(x, y, e['x'], e['y']) - e['r'] * 0.5
            if d < rad:
                self.bd_damage(e, dmg * (1.0 - 0.55 * clamp(d / rad, 0, 1)), 'shell')

    # ------------------------------------------------------------------ actualización
    def bd_hurt(self, n, why=''):
        bd = self.bd
        bd['hp'] -= n
        bd['hit'] = 0.25
        self.shake = max(self.shake, 3 + n * 0.4)

    def upd_batdef(self, dt):
        bd = self.bd
        bd['t'] += dt
        bd['hit'] = max(0.0, bd['hit'] - dt)
        bd['flash'] = max(0.0, bd['flash'] - dt)
        bd['recoil'] = max(0.0, bd['recoil'] - dt * 6)
        self.fx.update(dt)
        ax, ay = self.aim
        bd['ang'] = math.atan2(ay - C[1], ax - C[0])
        ph = bd['phase']
        if ph == 'intro':
            bd['pt'] += dt
            if bd['pt'] > 3.0:
                bd['phase'], bd['pt'] = 'play', 0.0
            self.bd_player(dt, False)
            return
        if ph == 'break':
            bd['pt'] += dt
            self.bd_player(dt, True)
            self.bd_move(dt)
            if bd['pt'] > 4.0:
                bd['stage'] += 1
                bd['phase'], bd['pt'] = 'play', 0.0
                bd['hp'] = min(bd['max'], bd['hp'] + 14)
                self.bd_stage_setup()
                self.banner('TANDA %d/%d' % (bd['stage'] + 1, STAGES), ('¡Crucero enemigo a la vista!' if bd['stage'] == STAGES - 1 else 'Más enemigos por mar y aire'), (255, 200, 110), 2.4)
            return
        if ph in ('win', 'lose'):
            bd['pt'] += dt
            if ph == 'lose' and random.random() < dt * 10:
                self.fx.explode_art(C[0] + random.uniform(-40, 40), C[1] + random.uniform(-30, 30), 1.0, True)
            if bd['pt'] > 3.2:
                self.end_batdef(ph == 'win')
            return
        bd['stage_t'] += dt
        while bd['spawns'] and bd['spawns'][0][0] <= bd['stage_t']:
            _, kind, a = bd['spawns'].pop(0)
            self.bd_spawn(kind, a)
        self.bd_player(dt, True)
        self.bd_move(dt)
        if bd['hp'] <= 0:
            bd['hp'] = 0.0
            bd['phase'], bd['pt'] = 'lose', 0.0
            self.audio.play('boom_l', 1.0)
            self.banner('¡LA BATERÍA CAYÓ!', 'Los enemigos tomaron el islote', (255, 100, 90), 3.0)
            return
        if not bd['spawns'] and not [e for e in bd['enemies'] if not e.get('dead')]:
            if bd['stage'] >= STAGES - 1:
                bd['phase'], bd['pt'] = 'win', 0.0
                self.audio.play('fanfare', .8)
                self.banner('¡BATERÍA DEFENDIDA!', 'El islote es nuestro', (130, 255, 190), 3.0)
            else:
                bd['phase'], bd['pt'] = 'break', 0.0
                self.audio.play('win', .6)
                self.banner('TANDA %d SUPERADA' % (bd['stage'] + 1), 'Reparaciones: +14 de vida de la batería', (130, 255, 190), 2.6)

    def bd_player(self, dt, live):
        bd = self.bd
        ang = bd['ang']
        bd['mg_cd'] = max(0.0, bd['mg_cd'] - dt)
        bd['sh_cd'] = max(0.0, bd['sh_cd'] - dt)
        bd['fl_cd'] = max(0.0, bd['fl_cd'] - dt)
        bd['heat'] = max(0.0, bd['heat'] - dt * (0.22 if bd['locked'] else 0.16))
        if bd['locked'] and bd['heat'] < 0.3:
            bd['locked'] = False
        btn = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()
        tip = (C[0] + math.cos(ang) * 58, C[1] + math.sin(ang) * 58)
        if live and btn[0] and not bd['locked'] and bd['mg_cd'] <= 0:
            bd['mg_cd'] = 1 / 14.0
            bd['heat'] += 0.032
            if bd['heat'] >= 1.0:
                bd['locked'] = True
                self.audio.play('empty', .5)
            a = ang + random.uniform(-0.04, 0.04)
            bd['bullets'].append(dict(x=C[0] + math.cos(ang) * 14, y=C[1] + math.sin(ang) * 14, vx=math.cos(a) * 960, vy=math.sin(a) * 960, life=0.8))
            bd['flash'] = 0.06
            bd['recoil'] = 0.5
            if int(bd['t'] * 14) % 3 == 0:
                self.audio.play('mg', .22)
        rmb = btn[2]
        if live and rmb and not bd['rmb'] and bd['sh_cd'] <= 0:
            bd['sh_cd'] = 1.5
            tx, ty = self.aim
            dd = dist(C[0], C[1], tx, ty)
            if dd > 600:
                tx, ty = C[0] + (tx - C[0]) / dd * 600, C[1] + (ty - C[1]) / dd * 600
            bd['shells'].append(dict(x=tip[0], y=tip[1], tx=tx, ty=ty, sx=tip[0], sy=tip[1], t=0.0, T=max(0.35, dist(tip[0], tip[1], tx, ty) / 560.0)))
            bd['recoil'] = 1.0
            bd['flash'] = 0.12
            self.audio.play('cannon', .8)
            self.fx.add('smoke', tip[0], tip[1], math.cos(ang) * 30, math.sin(ang) * 30, 0.8, 5, 18, (170, 170, 170))
            self.shake = max(self.shake, 3)
        bd['rmb'] = rmb
        spc = bool(keys[pygame.K_SPACE])
        if live and spc and not bd['spc'] and bd['fl_cd'] <= 0:
            bd['fl_cd'] = 4.5
            tx, ty = self.aim
            bd['flaks'].append(dict(x=tx, y=ty, t=0.0))
            self.audio.play('launch', .5)
        bd['spc'] = spc

    def bd_move(self, dt):
        bd = self.bd
        w = self.wave
        # balas de la ametralladora
        for b in bd['bullets']:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            for e in bd['enemies']:
                if e.get('dead'):
                    continue
                if dist(b['x'], b['y'], e['x'], e['y']) < e['r']:
                    self.bd_damage(e, 1.0, 'mg')
                    b['life'] = 0
                    if e['kind'] in ('destroyer', 'cruiser') and random.random() < 0.3:
                        self.fx.add('spark', b['x'], b['y'], random.uniform(-80, 80), random.uniform(-80, 80), 0.25, col=(255, 210, 120))
                    break
        bd['bullets'] = [b for b in bd['bullets'] if b['life'] > 0]
        # proyectiles pesados
        for s in bd['shells']:
            s['t'] += dt
            k = clamp(s['t'] / s['T'], 0, 1)
            s['x'] = s['sx'] + (s['tx'] - s['sx']) * k
            s['y'] = s['sy'] + (s['ty'] - s['sy']) * k
            if s['t'] >= s['T']:
                s['done'] = True
                self.fx.explode_art(s['tx'], s['ty'], 0.9, False)
                self.audio.play('boom_s', .5)
                self.bd_aoe(s['tx'], s['ty'], 86, 14.0)
                self.shake = max(self.shake, 4)
        bd['shells'] = [s for s in bd['shells'] if not s.get('done')]
        # cortina antiaérea
        for f in bd['flaks']:
            f['t'] += dt
            if f['t'] >= 0.45 and not f.get('done'):
                f['done'] = True
                self.fx.add('glow', f['x'], f['y'], life=0.35, r0=20, r1=110, col=(255, 230, 150))
                self.fx.add('ring', f['x'], f['y'], life=0.45, r0=10, r1=115, col=(255, 240, 190))
                self.audio.play('boom_s', .4)
                for e in bd['enemies']:
                    if e['kind'] == 'plane' and not e.get('dead') and dist(f['x'], f['y'], e['x'], e['y']) < 115:
                        self.bd_damage(e, 6.0, 'shell')
                bd['bombs'] = [bm for bm in bd['bombs'] if dist(f['x'], f['y'], bm['x'], bm['y']) > 115]      # la cortina detona las bombas en el aire
        bd['flaks'] = [f for f in bd['flaks'] if f['t'] < 0.6]
        # enemigos
        new = []
        for e in bd['enemies']:
            e['flash'] = max(0.0, e.get('flash', 0.0) - dt)
            if e.get('dead'):
                continue
            k = e['kind']
            if k == 'boat':
                dx, dy = C[0] - e['x'], C[1] - e['y']
                d = math.hypot(dx, dy) or 1.0
                e['h'] = bearing(dx, dy)
                e['x'] += dx / d * e['sp'] * dt
                e['y'] += dy / d * e['sp'] * dt
                if int(self.t * 6) % 2 == 0 and random.random() < 0.3:
                    self.fx.add('foam', e['x'] - dx / d * 24, e['y'] - dy / d * 24, 0, 0, 0.7, 4, 9, (230, 240, 255))
                if d <= SHORE:
                    e['dead'] = True
                    self.fx.splash(e['x'], e['y'], 0.8)
                    self.audio.play('splash', .5)
                    for i in range(e['n']):
                        a = math.radians(e['h'] + random.uniform(-40, 40))
                        new.append(dict(kind='soldier', x=e['x'] + math.sin(a) * 10 + random.uniform(-8, 8), y=e['y'] - math.cos(a) * 10 + random.uniform(-8, 8),
                                        hp=float(1 + (1 if w >= 4 else 0)), max=1.0, sp=52.0 + random.uniform(-8, 12), r=10, ph=random.uniform(0, 6), h=e['h']))
                    self.say('artillero', '¡Desembarcan soldados en la playa! ¡Fuego sobre ellos!', 'warn') if random.random() < 0.5 else None
            elif k == 'soldier':
                dx, dy = C[0] - e['x'], C[1] - e['y']
                d = math.hypot(dx, dy) or 1.0
                e['h'] = bearing(dx, dy)
                e['ph'] += dt * 9
                if d > BAT_R + 8:
                    e['x'] += dx / d * e['sp'] * dt
                    e['y'] += dy / d * e['sp'] * dt
                else:
                    self.bd_hurt((1.3 + 0.08 * w) * dt)
                    if random.random() < dt * 4:
                        self.fx.add('spark', e['x'], e['y'], random.uniform(-50, 50), random.uniform(-50, 50), 0.25, col=(255, 220, 140))
            elif k == 'plane':
                dx, dy = vec(e['h'], 1.0)
                e['x'] += dx * e['sp'] * dt
                e['y'] += dy * e['sp'] * dt
                d = dist(e['x'], e['y'], C[0], C[1])
                if not e['bombed'] and d < 120:
                    e['bombed'] = True
                    bd['bombs'].append(dict(x=e['x'] + dx * 40, y=e['y'] + dy * 40, t=0.0))
                    self.audio.play('launch', .4)
                if e['fighter'] and d < 330:
                    e['gun'] -= dt
                    if e['gun'] <= 0:
                        e['gun'] = 0.28
                        bd['tracers'].append(dict(x=e['x'], y=e['y'], tx=C[0] + random.uniform(-30, 30), ty=C[1] + random.uniform(-30, 30), t=0.0))
                        self.bd_hurt(0.7)
                        self.audio.play('mg', .15)
                if e['x'] < -160 or e['x'] > W + 160 or e['y'] < -160 or e['y'] > H + 160:
                    e['dead'] = True
            elif k in ('destroyer', 'cruiser'):
                orbit = 400 if k == 'destroyer' else 440
                d = dist(e['x'], e['y'], C[0], C[1])
                if d > orbit + 8:
                    dx, dy = C[0] - e['x'], C[1] - e['y']
                    e['x'] += dx / d * e['sp'] * dt
                    e['y'] += dy / d * e['sp'] * dt
                    e['h'] = bearing(dx, dy)
                else:
                    e['a'] += 0.05 * dt * (1 if k == 'destroyer' else -1)
                    nx_, ny_ = C[0] + math.cos(e['a']) * orbit, C[1] + math.sin(e['a']) * orbit * 0.8
                    e['h'] = bearing(nx_ - e['x'], ny_ - e['y'])
                    e['x'], e['y'] = nx_, ny_
                e['cd'] -= dt
                if e['cd'] <= 0:
                    e['cd'] = (3.8 - 0.1 * w) if k == 'destroyer' else (4.4 - 0.1 * w)
                    for _ in range(1 if k == 'destroyer' else 2):
                        bd['eshells'].append(dict(x=e['x'], y=e['y'], tx=C[0] + random.uniform(-48, 48), ty=C[1] + random.uniform(-40, 40), t=0.0, T=1.3))
                    self.audio.play('cannon', .5)
                if k == 'cruiser':
                    e['bt'] -= dt
                    if e['bt'] <= 0:
                        e['bt'] = 9.0
                        new.append(dict(kind='boat', x=e['x'], y=e['y'], a=0.0, hp=float(6 + w), max=float(6 + w), sp=72.0 + 3 * w, n=min(6, 3 + w // 3), h=0.0, r=24))
            new.append(e)
        bd['enemies'] = new
        # bombas
        for bm in bd['bombs']:
            bm['t'] += dt
            if bm['t'] >= 0.9:
                bm['done'] = True
                self.fx.explode_art(bm['x'], bm['y'], 0.8, True)
                self.audio.play('boom_s', .6)
                if dist(bm['x'], bm['y'], C[0], C[1]) < 62:
                    self.bd_hurt(9.0)
        bd['bombs'] = [bm for bm in bd['bombs'] if not bm.get('done')]
        # proyectiles enemigos
        for s in bd['eshells']:
            s['t'] += dt
            if s['t'] >= s['T']:
                s['done'] = True
                self.fx.explode_art(s['tx'], s['ty'], 1.0, True)
                self.audio.play('boom_l', .6)
                if dist(s['tx'], s['ty'], C[0], C[1]) < 58:
                    self.bd_hurt(11.0)
        bd['eshells'] = [s for s in bd['eshells'] if not s.get('done')]
        for tr in bd['tracers']:
            tr['t'] += dt
        bd['tracers'] = [tr for tr in bd['tracers'] if tr['t'] < 0.12]

    # ------------------------------------------------------------------ cierre
    def end_batdef(self, won):
        bd = self.bd
        nst = bd['nst']
        self.go('map')
        if won:
            bonus = 500 + 150 * self.wave + bd['pts']
            self.add_score(bonus)
            frac = bd['hp'] / bd['max']
            self.ammo = min(40, self.ammo + 10)
            self.hull = min(self.hull_max, self.hull + 25)
            self.fuel = min(100.0, self.fuel + 30)
            nst['atk'] = None
            nst['vet'] = nst.get('vet', 0) + 1
            nst['cool'] = 0.0
            self.bat_atk_t = max(getattr(self, 'bat_atk_t', 60.0), random.uniform(120, 170))
            self.banner('¡BATERÍA DEFENDIDA!', '+%d puntos  |  +10 munición, +25 casco, +30 combustible' % bonus, (130, 255, 190), 4.4)
            self.say('marinero', 'Gran trabajo, capitán. La batería es nuestra y sus cañones apoyarán a la flota.' if frac > 0.4 else 'Por poco, capitán... pero la batería resistió.', 'ok')
        else:
            self.bat_lost(nst, 'Los invasores la tomaron')

    # ------------------------------------------------------------------ dibujo
    def bd_island(self):
        cache = self.__dict__.setdefault('_bd_isl', {})
        sd = self.bd['sd']
        if sd not in cache:
            s = pygame.Surface((int(ISL_R * 3.6), int(ISL_R * 3.6)), pygame.SRCALPHA)
            self.paint_island(s, s.get_width() / 2, s.get_height() / 2, ISL_R, sd, False)
            cache[sd] = s
        return cache[sd]

    def bd_ship(self, cv, key, x, y, h, k):
        surf, sh = self.ships[key]
        r = pygame.transform.rotozoom(surf, -h, k)
        rs = pygame.transform.rotozoom(sh, -h, k)
        rs.set_alpha(80)
        cv.blit(rs, (int(x) - rs.get_width() // 2 + 5, int(y) - rs.get_height() // 2 + 7))
        cv.blit(r, (int(x) - r.get_width() // 2, int(y) - r.get_height() // 2))

    def draw_batdef(self, cv):
        bd = self.bd
        t = self.t
        self.draw_ocean(cv, t * 8, t * 3, t)
        isl = self.bd_island()
        cv.blit(isl, (C[0] - isl.get_width() // 2, C[1] - isl.get_height() // 2))
        # búnker y cañón
        draw_circ(cv, C[0] + 5, C[1] + 7, BAT_R + 4, (0, 0, 0), 80)
        pygame.draw.circle(cv, (110, 112, 108), C, BAT_R + 2)
        pygame.draw.circle(cv, (76, 80, 78), C, BAT_R - 4)
        for k in range(10):
            a = 6.2832 * k / 10
            pygame.draw.circle(cv, (150, 130, 90), (int(C[0] + math.cos(a) * (BAT_R + 2)), int(C[1] + math.sin(a) * (BAT_R + 2))), 6)
        ang = bd['ang']
        rec = bd['recoil'] * 7
        for off in (-5, 5):
            ox, oy = -math.sin(ang) * off, math.cos(ang) * off
            x0, y0 = C[0] + ox - math.cos(ang) * rec, C[1] + oy - math.sin(ang) * rec
            pygame.draw.line(cv, (40, 44, 46), (x0, y0), (x0 + math.cos(ang) * 56, y0 + math.sin(ang) * 56), 7)
            pygame.draw.line(cv, (96, 102, 104), (x0, y0), (x0 + math.cos(ang) * 56, y0 + math.sin(ang) * 56), 3)
        pygame.draw.circle(cv, (58, 64, 66), C, 17)
        pygame.draw.circle(cv, (120, 128, 128), C, 11)
        if bd['flash'] > 0:
            glow(cv, C[0] + math.cos(ang) * 62, C[1] + math.sin(ang) * 62, 40, (255, 220, 140), 0.9)
        if bd['hp'] < bd['max'] * 0.5 and random.random() < 0.3:
            self.fx.add('smoke', C[0] + random.uniform(-18, 18), C[1] + random.uniform(-14, 14), random.uniform(-8, 8), -26, 1.6, 6, 22, (46, 44, 44))
        if bd['hit'] > 0:
            draw_circ(cv, C[0], C[1], BAT_R + 12, (255, 80, 60), 120 * bd['hit'] / 0.25, 3)
        # enemigos
        for e in bd['enemies']:
            k = e['kind']
            if k == 'boat':
                self.draw_boat(cv, e['x'], e['y'], e['h'])
            elif k == 'soldier':
                self.blit_soldier(cv, 'e_rifle', e['x'], e['y'], e['h'], int(e['ph']) % 4)
            elif k == 'destroyer':
                self.bd_ship(cv, 'e_map', e['x'], e['y'], e['h'], 1.7)
            elif k == 'cruiser':
                self.bd_ship(cv, 'b0_map', e['x'], e['y'], e['h'], 1.35)
            if k != 'soldier' and k != 'boat' and e['hp'] < e['max']:
                pygame.draw.rect(cv, (8, 12, 24), (e['x'] - 28, e['y'] - e['r'] - 12, 56, 6))
                pygame.draw.rect(cv, (240, 80, 70), (e['x'] - 27, e['y'] - e['r'] - 11, int(54 * max(0, e['hp']) / e['max']), 4))
            if e.get('flash', 0) > 0 and k != 'plane':
                glow(cv, e['x'], e['y'], e['r'] + 14, (255, 255, 255), 0.4)
        # sombras y aviones por encima
        for e in bd['enemies']:
            if e['kind'] == 'plane':
                spr = self.air['viper'] if not e['fighter'] else self.air['stealth']
                r = pygame.transform.rotozoom(spr, 180 - e['h'], 0.85)
                sh = pygame.mask.from_surface(r).to_surface(setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0))
                cv.blit(sh, (int(e['x']) - r.get_width() // 2 + 26, int(e['y']) - r.get_height() // 2 + 34))
                cv.blit(r, (int(e['x']) - r.get_width() // 2, int(e['y']) - r.get_height() // 2))
        for bm in bd['bombs']:
            k = bm['t'] / 0.9
            draw_circ(cv, bm['x'], bm['y'], 62 * (1.1 - 0.4 * k), (255, 70, 60), 60 + 100 * k, 2)
            pygame.draw.circle(cv, (30, 32, 30), (int(bm['x']), int(bm['y'] - (1 - k) * 90)), 5)
        for s in bd['eshells']:
            k = s['t'] / s['T']
            draw_circ(cv, s['tx'], s['ty'], 58 * (1.15 - 0.25 * k), (255, 70, 60), 40 + 120 * k, 2)
            ex = s['x'] + (s['tx'] - s['x']) * k
            ey = s['y'] + (s['ty'] - s['y']) * k - math.sin(math.pi * k) * 70
            pygame.draw.circle(cv, (40, 40, 44), (int(ex), int(ey)), 5)
            pygame.draw.circle(cv, (255, 190, 100), (int(ex), int(ey)), 7, 1)
        for tr in bd['tracers']:
            k = tr['t'] / 0.12
            pygame.draw.line(cv, (255, 210, 110), (tr['x'] + (tr['tx'] - tr['x']) * k * 0.6, tr['y'] + (tr['ty'] - tr['y']) * k * 0.6), (tr['x'] + (tr['tx'] - tr['x']) * k, tr['y'] + (tr['ty'] - tr['y']) * k), 2)
        for b in bd['bullets']:
            pygame.draw.line(cv, (255, 240, 150), (b['x'], b['y']), (b['x'] - b['vx'] * 0.03, b['y'] - b['vy'] * 0.03), 3)
        for s in bd['shells']:
            pygame.draw.circle(cv, (30, 30, 34), (int(s['x']), int(s['y'])), 6)
            pygame.draw.circle(cv, (255, 200, 120), (int(s['x']), int(s['y'])), 8, 1)
            draw_circ(cv, s['tx'], s['ty'], 86, (255, 255, 255), 40, 1)
        for f in bd['flaks']:
            draw_circ(cv, f['x'], f['y'], 115 * (0.4 + f['t']), (255, 235, 170), 70, 1)
        self.fx.draw(cv, 0, 0)
        # puntería
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 14, 2)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 2)
        for dx, dy in ((-22, 0), (22, 0), (0, -22), (0, 22)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        # HUD
        self.bar(cv, W // 2 - 220, 22, 440, 26, max(0.0, bd['hp']) / bd['max'], (110, 235, 150) if bd['hp'] > bd['max'] * 0.35 else (255, 110, 90), 'BATERÍA')
        self.text(cv, 'TANDA %d/%d' % (bd['stage'] + 1, STAGES), self.f_m, (255, 225, 140), W // 2, 56, 'c')
        left = len([e for e in bd['enemies'] if not e.get('dead')]) + len(bd['spawns'])
        self.text(cv, 'ENEMIGOS %d' % left, self.f_s, (255, 160, 140), W // 2, 84, 'c')
        self.bar(cv, 30, H - 110, 320, 18, min(1.0, bd['heat']), (255, 120, 70) if bd['locked'] else (255, 200, 90), 'SOBRECALENTADA' if bd['locked'] else 'AMETRALLADORA')
        self.bar(cv, 30, H - 82, 320, 18, 1.0 - bd['sh_cd'] / 1.5, (130, 220, 255), 'PROYECTIL PESADO (CLIC DER.)')
        self.bar(cv, 30, H - 54, 320, 18, 1.0 - bd['fl_cd'] / 4.5, (255, 235, 170), 'CORTINA ANTIAÉREA (ESPACIO)')
        self.text(cv, 'Puntos de la defensa: %d' % bd['pts'], self.f_s, (200, 225, 250), W - 30, H - 40, 'r')
        ph = bd['phase']
        if ph == 'intro':
            self.text(cv, 'PREPARADOS...', self.f_xl, (255, 225, 130), W // 2, 330, 'c', alpha=int(255 * clamp(1.2 - bd['pt'] / 3.0, 0.3, 1)))
        elif ph == 'break':
            self.text(cv, 'RECARGANDO...', self.f_l, (150, 230, 255), W // 2, 330, 'c')
        if bd['hit'] > 0:
            self.hurt_surf.set_alpha(int(255 * clamp(bd['hit'] * 3, 0, 1) * 0.5))
            cv.blit(self.hurt_surf, (0, 0))
