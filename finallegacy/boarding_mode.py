"""Abordaje: botes enemigos intentan tomar el barco (minijuego cenital con ametralladora). Si llegan 3 o más, los invasores suben y se pelea en la cubierta (nivel lateral tipo Metal Slug).
Si se pierde en la cubierta se pierde una vida y empieza la lancha de escape; si se gana no hay puntos pero se sigue con vida."""
import math
import random
import pygame
from .common import H, PLAYER_HP, W, Particles, bearing, clamp, dist, draw_circ, glow, lerp, vec

C = (W // 2, H // 2 + 30)                 # el barco, en el centro
TUR = (C[0], C[1] - 28)                   # montaje de la torreta (el mismo que en el combate naval)
BOARD_MAX = 3                             # botes que pueden llegar antes de que haya invasión
DECK_LEN = 3400


class BoardMixin:
    # ------------------------------------------------------------------ evento en el mapa
    def board_init(self):
        self.board_t = random.uniform(150.0, 200.0)
        self.board_pend = 0.0

    def board_map_tick(self, dt):
        if getattr(self, 'board_pend', 0.0) > 0:
            self.board_pend -= dt
            if self.board_pend <= 0:
                self.start_boarding()
            return
        if self.wave < 2:
            return
        busy = (self.attack is not None or self.warned or self.rescue is not None or self.raid is not None or getattr(self, 'convoy', None) is not None
                or any(n.get('atk') for n in self.nests))
        self.board_t = getattr(self, 'board_t', 150.0) - dt
        if self.board_t <= 0 and not busy and self.state == 'map':
            self.board_pend = 3.0
            self.board_t = random.uniform(150.0, 210.0)
            self.audio.play('alarm', .7)
            self.banner('¡ABORDAJE ENEMIGO!', 'Botes con soldados se acercan: repelelos con ráfagas cortas', (255, 110, 80), 3.0)
            self.say('marinero', self.chat_pick('board_warn', (
                '¡Botes enemigos a babor y estribor, capitán! Quieren abordarnos.',
                '¡Alarma de abordaje! A las ametralladoras, que no suban a cubierta.',
                'Contacto de lanchas hostiles. Ráfagas cortas o se nos recalienta el arma.',
            )), 'warn')

    # ------------------------------------------------------------------ minijuego de los botes
    def start_boarding(self):
        w = self.wave
        n = min(12, 8 + w)
        self.fx = Particles()
        self.bo = dict(t=0.0, phase='intro', pt=0.0, boats=[], deck=[], n=n, spawned=0, spawn_t=1.0, boarded=0, kills=0, heat=0.0, locked=False, mg_cd=0.0,
                       bullets=[], ang=-1.57, flash=0.0, hit=0.0, gap=max(1.1, 1.8 - 0.05 * w))
        self.aim = [float(C[0]), float(C[1] - 240)]
        self.go('board')
        self.banner('¡REPELÉ EL ABORDAJE!', 'Clic: ráfagas cortas (la ametralladora se recalienta)', (255, 200, 110), 3.5)
        self.say('artillero', '¡Ametralladora a su mando, capitán! Que no lleguen tres botes a la cubierta.', 'warn')

    def bo_spawn(self):
        bo = self.bo
        a = random.uniform(0, 6.28)
        x, y = C[0] + math.cos(a) * 700, C[1] + math.sin(a) * 560
        hp = 4.0 + self.wave // 2
        bo['boats'].append(dict(x=x, y=y, hp=hp, max=hp, sp=82.0 + 4 * self.wave, h=0.0, sw=random.uniform(0, 6.28), dead=False))
        bo['spawned'] += 1

    def upd_board(self, dt):
        bo = self.bo
        bo['t'] += dt
        bo['hit'] = max(0.0, bo['hit'] - dt)
        bo['flash'] = max(0.0, bo['flash'] - dt)
        self.fx.update(dt)
        bo['ang'] = math.atan2(self.aim[1] - TUR[1], self.aim[0] - TUR[0])
        ph = bo['phase']
        if ph == 'intro':
            bo['pt'] += dt
            if bo['pt'] > 2.5:
                bo['phase'], bo['pt'] = 'play', 0.0
            return
        if ph in ('invaded', 'win'):
            bo['pt'] += dt
            self.bo_move(dt, False)
            if bo['pt'] > (2.8 if ph == 'invaded' else 2.4):
                self.start_deck() if ph == 'invaded' else self.end_boarding()
            return
        bo['spawn_t'] -= dt
        if bo['spawned'] < bo['n'] and bo['spawn_t'] <= 0:
            bo['spawn_t'] = bo['gap'] * random.uniform(0.7, 1.3)
            self.bo_spawn()
            if self.wave >= 4 and bo['spawned'] < bo['n'] and random.random() < 0.3:
                self.bo_spawn()
        self.bo_player(dt)
        self.bo_move(dt, True)
        if bo['boarded'] >= BOARD_MAX:
            bo['phase'], bo['pt'] = 'invaded', 0.0
            self.audio.play('alarm', 1.0)
            self.shake = 14
            self.banner('¡NOS ABORDAN!', 'Los invasores están en la cubierta: ¡a defenderla!', (255, 80, 70), 3.0)
            self.say('soldado', '¡Han subido a cubierta! ¡Todos a las armas!', 'bad')
        elif bo['spawned'] >= bo['n'] and not bo['boats']:
            bo['phase'], bo['pt'] = 'win', 0.0
            self.audio.play('win', .7)
            self.banner('¡ABORDAJE REPELIDO!', 'Ningún invasor llegó a cubierta', (130, 255, 190), 2.6)

    def bo_player(self, dt):
        bo = self.bo
        bo['mg_cd'] = max(0.0, bo['mg_cd'] - dt)
        bo['heat'] = max(0.0, bo['heat'] - dt * (0.34 if bo['locked'] else 0.24))
        if bo['locked'] and bo['heat'] < 0.3:
            bo['locked'] = False
        if (pygame.mouse.get_pressed()[0] or pygame.key.get_pressed()[pygame.K_SPACE]) and not bo['locked'] and bo['mg_cd'] <= 0:
            bo['mg_cd'] = 1 / 13.0
            bo['heat'] += 0.036
            if bo['heat'] >= 1.0:
                bo['locked'] = True
                self.audio.play('empty', .5)
            a = bo['ang'] + random.uniform(-0.05, 0.05)
            bo['bullets'].append(dict(x=TUR[0] + math.cos(a) * 30, y=TUR[1] + math.sin(a) * 30, vx=math.cos(a) * 980, vy=math.sin(a) * 980, life=0.9))
            bo['flash'] = 0.05
            if int(bo['t'] * 13) % 3 == 0:
                self.audio.play('mg', .22)

    def bo_move(self, dt, live):
        bo = self.bo
        for b in bo['bullets']:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            for e in bo['boats']:
                if dist(b['x'], b['y'], e['x'], e['y']) < 24:
                    e['hp'] -= 1.0
                    b['life'] = 0
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25, col=(255, 220, 130))
                    if e['hp'] <= 0:
                        e['dead'] = True
                        bo['kills'] += 1
                        self.fx.explode_art(e['x'], e['y'], 1.0, False)
                        self.fx.splash(e['x'], e['y'], 1.2)
                        self.audio.play('boom_s', .45)
                    break
        bo['bullets'] = [b for b in bo['bullets'] if b['life'] > 0]
        keep = []
        for e in bo['boats']:
            if e['dead']:
                continue
            if live:
                dx, dy = C[0] - e['x'], C[1] - e['y']
                d = math.hypot(dx, dy) or 1.0
                e['sw'] += dt * 2.4
                e['h'] = bearing(dx, dy)
                sx = -dy / d * math.sin(e['sw']) * 22
                sy = dx / d * math.sin(e['sw']) * 22
                e['x'] += (dx / d * e['sp'] + sx) * dt
                e['y'] += (dy / d * e['sp'] + sy) * dt
                if random.random() < dt * 6:
                    self.fx.add('foam', e['x'] - dx / d * 22, e['y'] - dy / d * 22, 0, 0, 0.7, 4, 9, (235, 244, 255))
                if d < 78:
                    bo['boarded'] += 1
                    bo['hit'] = 0.35
                    self.audio.play('hit', .6)
                    self.fx.splash(e['x'], e['y'], 1.0)
                    for i in range(3):
                        bo['deck'].append(dict(x=e['x'] + random.uniform(-10, 10), y=e['y'] + random.uniform(-10, 10), t=0.0, ph=random.uniform(0, 6)))
                    self.pop('¡ABORDAN! %d/%d' % (bo['boarded'], BOARD_MAX), C[0], C[1] - 120, (255, 110, 90))
                    continue
            keep.append(e)
        bo['boats'] = keep
        for s in bo['deck']:
            s['t'] += dt
            dx, dy = C[0] - s['x'], C[1] - s['y']
            d = math.hypot(dx, dy) or 1.0
            if d > 20:
                s['x'] += dx / d * 60 * dt
                s['y'] += dy / d * 60 * dt
        bo['deck'] = [s for s in bo['deck'] if s['t'] < 3.0]

    def end_boarding(self):
        self.go('map')
        self.board_t = random.uniform(150.0, 210.0)
        self.say('marinero', self.chat_pick('board_win', (
            'Abordaje repelido, capitán. Ni un invasor pisó la cubierta.',
            'Los botes se fueron al fondo. Buen trabajo en la ametralladora.',
        )), 'ok')

    # ------------------------------------------------------------------ dibujo del minijuego
    def draw_board(self, cv):
        bo = self.bo
        t = self.t
        self.draw_ocean(cv, t * 8, t * 3, t)
        self.blit_ship(cv, 'p_hull', C[0], C[1], 0.0)                              # el mismo buque y la misma torreta del combate naval
        if bo['hit'] > 0:
            draw_circ(cv, C[0], C[1], 120, (255, 80, 60), 110 * bo['hit'] / 0.35, 4)
        ang = bo['ang']
        self.blit_turret(cv, self.tur_p, TUR[0], TUR[1], bearing(self.aim[0] - TUR[0], self.aim[1] - TUR[1]))
        if bo['flash'] > 0:
            glow(cv, TUR[0] + math.cos(ang) * 40, TUR[1] + math.sin(ang) * 40, 36, (255, 220, 140), 0.9)
        for s in bo['deck']:
            self.blit_soldier(cv, 'e_rifle', s['x'], s['y'], bearing(C[0] - s['x'], C[1] - s['y']), int(s['t'] * 8 + s['ph']) % 4)
        for e in bo['boats']:
            self.draw_boat(cv, e['x'], e['y'], e['h'])
            if e['hp'] < e['max']:
                pygame.draw.rect(cv, (8, 12, 24), (e['x'] - 20, e['y'] - 32, 40, 5))
                pygame.draw.rect(cv, (240, 80, 70), (e['x'] - 19, e['y'] - 31, int(38 * max(0, e['hp']) / e['max']), 3))
        for b in bo['bullets']:
            pygame.draw.line(cv, (255, 240, 150), (b['x'], b['y']), (b['x'] - b['vx'] * 0.03, b['y'] - b['vy'] * 0.03), 3)
        self.fx.draw(cv, 0, 0)
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 14, 2)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 2)
        # HUD
        for i in range(BOARD_MAX):
            col = (255, 90, 70) if i < bo['boarded'] else (60, 70, 90)
            pygame.draw.rect(cv, col, (W // 2 - 84 + i * 60, 22, 48, 14), border_radius=4)
        self.text(cv, 'INVASORES A BORDO %d/%d' % (bo['boarded'], BOARD_MAX), self.f_s, (255, 190, 170), W // 2, 42, 'c')
        left = bo['n'] - bo['spawned'] + len(bo['boats'])
        self.text(cv, 'BOTES RESTANTES %d' % left, self.f_s, (200, 225, 250), W // 2, 66, 'c')
        self.bar(cv, 30, H - 54, 260, 18, min(1.0, bo['heat']), (255, 120, 70) if bo['locked'] else (255, 200, 90), 'SOBRECALENTADA' if bo['locked'] else 'AMETRALLADORA')
        if bo['phase'] == 'intro':
            self.text(cv, 'PREPARADOS...', self.f_xl, (255, 225, 130), W // 2, 170, 'c')
        elif bo['phase'] == 'invaded':
            self.text(cv, '¡INVASIÓN!', self.f_xl, (255, 90, 80), W // 2, 170, 'c')

    # ------------------------------------------------------------------ nivel en cubierta (reutiliza el del puerto)
    def start_deck(self):
        w = self.wave
        L = DECK_LEN
        self.PT_LEN = L                                             # largo corto del nivel (solo mientras dura la cubierta)
        GR = self.PT_GR
        rnd = random.Random(w * 313 + 7)
        plats = []
        x = 650
        while x < L - 900:
            hh = rnd.choice((1, 1, 2))
            plats.append(dict(x=x, w=rnd.choice((150, 225)), top=GR - 64 * hh, h=64 * hh, ci=rnd.randrange(5)))
            x += rnd.randint(520, 780)
        plats.append(dict(x=2500, w=225, top=GR - 64, h=64, ci=1))      # plataforma para el francotirador del último grupo
        ex = w // 2
        groups = []

        def grp(xt, spec, lock=False):
            groups.append(dict(x=xt, spec=spec, lock=lock, done=False, lx=0.0))
        grp(450, [('rifle', 'R'), ('rifle', 'R'), ('knife', 'R')] + [('rifle', 'L')] * (1 if w >= 3 else 0))
        grp(1150, [('rifle', 'R'), ('rifle', 'L'), ('knife', 'R'), ('gren', 'R')] + [('rifle', 'R')] * ex)
        grp(1850, [('shield', 'R'), ('rifle', 'R'), ('rifle', 'L'), ('knife', 'L'), ('knife', 'R')] + [('flame', 'R')] * (1 if w >= 3 else 0), True)
        grp(2650, [('gren', 'R'), ('gren', 'L'), ('rifle', 'R'), ('knife', 'R'), ('knife', 'L'), ('rifle', 'L')] + [('sniper', 'P')] * (1 if w >= 2 else 0) + [('rifle', 'R')] * ex, True)
        self.pt = dict(pfem=self.roll_player_fem(), deck=True,
            plats=plats, groups=groups, cam=0.0, lock=None, t=0.0, phase='play', pt=0.0, fail=False, kills=0,
            p=dict(x=120.0, y=float(GR), vx=0.0, vy=0.0, ground=True, hp=PLAYER_HP, face=1, cd=0.0, gren=6, hmg=0.0, inv=0.0,
                   ph=0.0, crouch=False, dead=False, gcd=0.0, flash=0.0, thr=0.0, dead_t=0.0, dust=0.0),
            enemies=[], bul=[], ebul=[], nades=[], items=[], go_t=0.0, boss=None, hurt=0.0, score0=self.score,
            cas=[], corpses=[], wrecks=[], decor=[], puddles=[], barrels=[], pows=[], mort=[], freeze=0.0, taken=0, pow_n=0, rank=None)
        drnd = random.Random(w * 17 + 3)
        dec = self.pt['decor']
        for lx in range(260, L, 700):
            dec.append(dict(kind='lamp', x=float(lx + drnd.randint(-60, 60))))
        for _ in range(24):
            dec.append(dict(kind=drnd.choice(('crates', 'bollard', 'sandbags')), x=float(drnd.randint(200, L - 200))))
        dec.sort(key=lambda d: {'fence': 0, 'lamp': 1}.get(d['kind'], 2))
        self.pt['barrels'] = [dict(x=float(bx), y=float(GR), hp=2, fuse=-1.0) for bx in sorted(drnd.sample(range(900, L - 700, 60), 4))]
        self.pt_art_init()
        self.pt_epic_setup()
        self.pt['items'] = [dict(x=float(xi), y=float(GR - 30), kind=kind, t=0.0)
                            for xi, kind in ((600, 'med'), (950, 'gren'), (1500, 'med'), (1950, 'hmg'), (2250, 'med'), (2500, 'shot'), (3000, 'med'))]
        self.fx = Particles()
        self.aim = [W / 2, 300.0]
        self.go('port')
        self.banner('¡DEFENDÉ LA CUBIERTA!', 'Repelé a los invasores: no dan puntos, pero te mantienen con vida', (255, 120, 90), 3.2)
        self.say('soldado', '¡Los invasores están en cubierta! A/D mover, W saltar, S agacharse, clic disparar, G granada. ¡Que no tomen el puente!', 'warn')

    def end_deck(self):
        pt = self.pt
        if 'PT_LEN' in self.__dict__:
            del self.PT_LEN
        self.score = pt['score0']                                   # repeler la invasión no da puntos
        if pt['fail']:
            self.board_t = random.uniform(150.0, 210.0)
            return self.lose_ship('Los invasores tomaron el barco')
        self.go('map')
        self.board_t = random.uniform(150.0, 210.0)
        self.banner('¡CUBIERTA LIBRE!', 'Repelida la invasión: seguimos con vida', (130, 255, 190), 3.4)
        self.say('secretaria', self.chat_pick('deck_win', (
            'Cubierta asegurada, capitán. Seguimos en operación.',
            'Informe: invasores neutralizados. El barco no sufrió bajas graves.',
        )), 'ok')

    # ------------------------------------------------------------------ fondo de la cubierta (lo usa draw_port)
    def deck_draw_back(self, cv, cam):
        bg = self.pt_bg
        GR = self.PT_GR
        t = self.t
        cv.blit(bg['sea'], (0, 410))
        for i in range(12):
            yy = 430 + i * 17
            xx = (i * 191 + t * (9 + i * 2)) % (W + 160) - 80
            pygame.draw.line(cv, (255, 206, 160), (xx, yy), (xx + 40 + i * 5, yy), 2)
        for i, (bx, bw, bh) in enumerate(((120, 220, 46), (520, 300, 34), (1040, 180, 52), (1400, 260, 38))):         # islotes lejanos
            xx = (bx - cam * 0.08) % (W + 500) - 250
            pygame.draw.polygon(cv, (58, 44, 76), [(xx, 414), (xx + bw * 0.3, 414 - bh), (xx + bw * 0.6, 414 - bh * 0.7), (xx + bw, 414)])
        # cubierta: chapas de acero con remaches y franjas de seguridad
        for y in range(GR, H, 4):
            f = (y - GR) / (H - GR)
            pygame.draw.rect(cv, (int(lerp(104, 58, f)), int(lerp(112, 66, f)), int(lerp(122, 80, f))), (0, y, W, 4))
        pygame.draw.rect(cv, (150, 156, 164), (0, GR, W, 6))
        pygame.draw.rect(cv, (50, 56, 66), (0, GR + 6, W, 3))
        for x in range(-int(cam) % 150, W, 150):
            pygame.draw.line(cv, (50, 56, 66), (x, GR + 9), (x, H), 2)
            for ry in (GR + 22, GR + 80, GR + 138):
                pygame.draw.circle(cv, (150, 156, 164), (x + 8, ry), 2)
        for y in (GR + 58, GR + 116):
            pygame.draw.line(cv, (50, 56, 66), (0, y), (W, y), 1)
        for x in range(-int(cam) % 320, W, 320):
            pygame.draw.rect(cv, (240, 200, 50), (x, GR + 3, 80, 3))
        # baranda del borde (al fondo, sobre el mar)
        pygame.draw.line(cv, (150, 156, 164), (0, GR - 58), (W, GR - 58), 3)
        for x in range(-int(cam) % 110, W, 110):
            pygame.draw.line(cv, (120, 126, 134), (x, GR - 58), (x, GR), 3)
