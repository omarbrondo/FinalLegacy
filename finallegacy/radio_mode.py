"""Radares enemigos en islotes vacíos: tras el hackeo de nodos se intercepta la señal de radio con un minijuego de
sintonía que va cambiando (estilo secuenciador criptográfico de Batman: calzar frecuencia, amplitud y fase)."""
import math
import pygame
import random
from .common import H, W, clamp, dist, draw_circ, glow
from .war import DECOR0

RADAR_IDX = (1, 5, 8, 10, 13, 15)                      # islotes decorativos que tienen un radar (no se mudan de lugar)
SCOPE = pygame.Rect(120, 170, 660, 300)
F_MIN, F_MAX = 0.8, 6.0
KIND_NAMES = {'tune': 'SINTONÍA', 'drift': 'SEÑAL A LA DERIVA', 'jam': 'INTERFERENCIA', 'dual': 'DOS CANALES', 'sweep': 'BARRIDO DE ESPECTRO'}
KIND_HINT = {
    'tune': 'A/D frecuencia  |  W/S amplitud: calzá la onda amarilla con la celeste',
    'drift': 'A/D frecuencia  |  W/S amplitud  |  Q/E fase: la señal se mueve, seguila',
    'jam': 'A/D frecuencia  |  W/S amplitud: el enemigo interfiere y te desajusta',
    'dual': 'A/D frecuencia  |  W/S amplitud  |  ESPACIO: cambiar de canal  |  calzá los dos',
    'sweep': 'ESPACIO cuando el cursor esté sobre la banda verde (se frena ahí)  |  3 aciertos',
}
PHRASES = ('FLOTA NORTE ATACA CIUDAD AMANECER', 'MISILES LISTOS ORDEN ESPERAR SEÑAL', 'REFUERZOS LLEGAN PUERTO MEDIANOCHE SILENCIO',
           'SUBMARINOS BAJO HIELO SEGUIR OBJETIVO', 'ANTENA ENEMIGA CAMBIAR CLAVE URGENTE', 'CONVOY SIN ESCOLTA RUTA SUR',
           'JEFE MARCHA ESCUDO ACTIVO FORTALEZA', 'BATERIAS COSTERAS APUNTAN BAHIA AZUL')
LAND_RADARS = 1                                       # radares interceptados (en la oleada) para desbloquear el desembarco
PORT_RADARS = 2                                       # ... y el asalto al puerto enemigo
LOOT = ('SUMINISTROS', 'REPARACIONES', 'INTELIGENCIA', 'BOTÍN')


class RadioMixin:
    # ------------------------------------------------------------------ radares en el mapa
    def radar_pos(self, k):
        x, y, r, _s = self.islands[DECOR0 + k]
        return x, y, r

    def nearest_radar(self, extra=180):
        best = None
        for k in RADAR_IDX:
            if self.radars[k]['hacked']:
                continue
            x, y, r = self.radar_pos(k)
            d = dist(self.sx, self.sy, x, y)
            if d < r * 1.1 + extra and (best is None or d < best[0]):
                best = (d, k)
        return best[1] if best else None

    def radars_done(self):
        return sum(1 for rd in self.radars.values() if rd['hacked'])

    def invasion_locked(self, need, what, quiet=False):
        """True si faltan radares interceptados para esta invasión (y avisa)."""
        n = self.radars_done()
        if n >= need:
            return False
        if not quiet:
            self.toast('%s bloqueado: interceptá %d radar(es) enemigo(s) (%d/%d)' % (what, need, n, need), (255, 170, 120))
            self.audio.play('blip', .5)
        return True

    def radar_tick(self, dt):
        for rd in self.radars.values():
            rd['cd'] = max(0.0, rd['cd'] - dt)

    def radars_reset(self):
        self.radars = {k: dict(hacked=False, cd=0.0) for k in RADAR_IDX}

    def try_radar(self):
        k = self.nearest_radar()
        if k is None:
            return False
        rd = self.radars[k]
        if rd['cd'] > 0:
            self.toast('Radar en alerta (contraataque): %d s' % math.ceil(rd['cd']), (255, 200, 120))
        else:
            self.start_hack(None, radar=k)
        return True

    def radar_draw_map(self, cv, cx, cy):
        t = self.t
        for k in RADAR_IDX:
            x, y, r = self.radar_pos(k)
            sx, sy = x - cx, y - cy
            if not (-220 < sx < W + 220 and -220 < sy < H + 220):
                continue
            rd = self.radars[k]
            hacked = rd['hacked']
            col = (110, 255, 170) if hacked else (255, 90, 80)
            draw_circ(cv, sx + 4, sy + 6, 24, (0, 0, 0), 70)
            pygame.draw.circle(cv, (92, 96, 100), (int(sx), int(sy)), 23)
            pygame.draw.circle(cv, (150, 154, 158), (int(sx), int(sy)), 19)
            pygame.draw.line(cv, (70, 74, 80), (sx, sy), (sx, sy - 32), 5)
            ang = t * (0.5 if hacked else 1.5)
            w = 30 * abs(math.cos(ang)) + 7
            pygame.draw.ellipse(cv, (206, 210, 214), (sx - w / 2, sy - 52, w, 22))
            pygame.draw.ellipse(cv, (86, 90, 96), (sx - w / 2, sy - 52, w, 22), 2)
            pygame.draw.line(cv, (70, 74, 80), (sx, sy - 41), (sx + math.sin(ang) * 14, sy - 30), 2)
            if int(t * 2) % 2 == 0:
                glow(cv, sx, sy - 34, 14, col)
            for j in range(2):
                ph = (t * 0.45 + j / 2) % 1
                draw_circ(cv, sx, sy - 30, 14 + ph * 150, col, (60 if hacked else 120) * (1 - ph), 2)
            if hacked:
                self.text(cv, 'RADAR INTERCEPTADO', self.f_s, (130, 255, 190), sx, sy - 82, 'c')
            elif rd['cd'] > 0:
                self.text(cv, 'EN ALERTA %ds' % math.ceil(rd['cd']), self.f_s, (255, 190, 120), sx, sy - 82, 'c')
            else:
                self.text(cv, 'RADAR ENEMIGO', self.f_s, (255, 150, 130), sx, sy - 82, 'c')

    def radar_draw_mini(self, cv, x0, y0, sc):
        for k in RADAR_IDX:
            x, y, _r = self.radar_pos(k)
            mx, my = int(x0 + x * sc), int(y0 + y * sc)
            col = (110, 255, 170) if self.radars[k]['hacked'] else (255, 90, 80)
            pygame.draw.polygon(cv, col, [(mx, my - 4), (mx + 4, my + 3), (mx - 4, my + 3)], 1)

    # ------------------------------------------------------------------ armado de una intercepción
    def start_radio(self, radar):
        n = min(5, 3 + self.wave // 2)
        kinds = ['tune']
        pool = ['jam', 'dual', 'sweep'] + (['drift'] if self.wave >= 2 else [])
        while len(kinds) < n:
            k = random.choice(pool)
            if k != kinds[-1]:
                kinds.append(k)
        words = random.choice(PHRASES).split()
        self.rd = dict(radar=radar, kinds=kinds, stage=0, fails=0, phase='play', pt=0.0, words=words, t=0.0, time_left=0.0,
                       calls=[], bonus=0, loot='', hold={}, blip=0.0, beep=0.0)
        self.rd_stage_init(first=True)
        self.aim = [W / 2, H / 2]
        self.go('radio')

    def rd_tol(self):
        return max(0.62, 1.0 - 0.05 * self.wave)

    def rd_rand_par(self):
        return dict(f=random.uniform(1.4, 5.2), a=random.uniform(0.3, 0.95), p=random.uniform(0, 6.28))

    def rd_stage_init(self, first=False):
        rd = self.rd
        kind = rd['kinds'][rd['stage']]
        tol = self.rd_tol()
        st = dict(kind=kind, lock=0.0, flash=0.0, jam_t=3.0, jam_fl=0.0, miss=0.0, tol=dict(f=0.22 * tol, a=0.09 * tol, p=0.42 * tol), ch=0)
        total = {'tune': 32.0, 'drift': 38.0, 'jam': 36.0, 'dual': 42.0, 'sweep': 34.0}[kind] - 1.5 * rd['fails']
        st['total'] = st['time'] = max(18.0, total)
        st['need'] = {'tune': 1.0, 'drift': 1.5, 'jam': 1.4, 'dual': 1.2}.get(kind, 1.0)
        if kind == 'sweep':
            st.update(pos=0.0, dir=1.0, speed=0.26 + 0.012 * self.wave, bw=0.22, bc=random.uniform(0.2, 0.8), hits=0, bars=[random.random() for _ in range(44)])
        elif kind == 'dual':
            st['tgt'] = [self.rd_rand_par(), self.rd_rand_par()]
            st['cur'] = [self.rd_far(st['tgt'][0]), self.rd_far(st['tgt'][1])]
        else:
            st['tgt'] = self.rd_rand_par()
            if kind == 'drift':
                st['base'] = dict(st['tgt'])
            st['cur'] = self.rd_far(st['tgt'])
        rd['st'] = st
        rd['time_left'] = st['time']
        if not first:
            self.audio.play('ping', .6)

    def rd_far(self, tgt):
        """Parámetros de arranque lejos del objetivo."""
        while True:
            c = self.rd_rand_par()
            if abs(c['f'] - tgt['f']) > 1.0 and abs(c['a'] - tgt['a']) > 0.25:
                return c

    # ------------------------------------------------------------------ entrada
    def radio_key(self, key):
        rd = self.rd
        st = rd['st']
        if rd['phase'] != 'play':
            return
        if key == pygame.K_TAB:
            return self.end_radio('abort')
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if st['kind'] == 'dual':
                st['ch'] ^= 1
                self.audio.play('blip', .5)
            elif st['kind'] == 'sweep':
                self.rd_sweep_hit()

    def rd_sweep_hit(self):
        rd = self.rd
        st = rd['st']
        if abs(st['pos'] - st['bc']) <= st['bw'] / 2 + 0.02:                        # un poco de margen a favor del jugador
            st['hits'] += 1
            st['flash'] = 0.35
            self.audio.play('pickup', .7)
            if st['hits'] >= 3:
                self.rd_stage_ok()
                return
            st['bw'] = max(0.14, st['bw'] - 0.02)
            st['speed'] *= 1.06
            for _ in range(20):
                nb = random.uniform(0.12, 0.88)
                if abs(nb - st['bc']) > 0.25:
                    st['bc'] = nb
                    break
        else:
            st['hits'] = max(0, st['hits'] - 1)
            st['miss'] = 0.4
            st['time'] = max(1.0, st['time'] - 1.0)
            self.audio.play('hit', .5)
            self.shake = max(self.shake, 4)

    # ------------------------------------------------------------------ actualización
    def rd_axis(self, name, keys, neg, pos, speed, dt):
        rd = self.rd
        d = (1 if any(keys[k] for k in pos) else 0) - (1 if any(keys[k] for k in neg) else 0)
        if d:
            rd['hold'][name] = rd['hold'].get(name, 0.0) + dt
            return d * speed * (0.25 + 0.75 * min(1.0, rd['hold'][name] / 0.6)) * dt
        rd['hold'][name] = 0.0
        return 0.0

    def rd_match(self, cur, tgt, st):
        tol = st['tol']
        dp = abs((cur['p'] - tgt['p'] + math.pi) % (2 * math.pi) - math.pi)
        return abs(cur['f'] - tgt['f']) < tol['f'] and abs(cur['a'] - tgt['a']) < tol['a'] and (not st.get('use_p') or dp < tol['p'])

    def rd_closeness(self, cur, tgt, st):
        """Cercanía de cada parámetro: 2 = calzado, 1 = cerca, 0 = lejos."""
        tol = st['tol']
        out = {}
        dp = abs((cur['p'] - tgt['p'] + math.pi) % (2 * math.pi) - math.pi)
        for k, d in (('f', abs(cur['f'] - tgt['f'])), ('a', abs(cur['a'] - tgt['a'])), ('p', dp)):
            out[k] = 2 if d < tol[k] else (1 if d < tol[k] * 2.6 else 0)
        return out

    def rd_stage_ok(self):
        rd = self.rd
        rd['phase'], rd['pt'] = 'ok', 0.0
        rd['st']['flash'] = 1.0
        self.audio.play('win', .6)
        self.add_score(150 + 40 * self.wave)

    def upd_radio(self, dt):
        rd = self.rd
        st = rd['st']
        rd['t'] += dt
        for c in rd['calls']:
            c[1] -= dt
        rd['calls'] = [c for c in rd['calls'] if c[1] > 0]
        st['flash'] = max(0.0, st['flash'] - dt)
        st['jam_fl'] = max(0.0, st['jam_fl'] - dt)
        st['miss'] = max(0.0, st['miss'] - dt)
        if rd['phase'] != 'play':
            rd['pt'] += dt
            if rd['phase'] == 'ok' and rd['pt'] > 1.1:
                rd['stage'] += 1
                if rd['stage'] >= len(rd['kinds']):
                    rd['phase'], rd['pt'] = 'win', 0.0
                    self.audio.play('win', .8)
                else:
                    rd['phase'] = 'play'
                    self.rd_stage_init()
            elif rd['phase'] == 'retry' and rd['pt'] > 1.3:
                rd['phase'] = 'play'
                self.rd_stage_init()
            elif rd['phase'] == 'win' and rd['pt'] > 3.4:
                self.end_radio('ok')
            elif rd['phase'] == 'lost' and rd['pt'] > 2.6:
                self.end_radio('lost')
            return
        keys = pygame.key.get_pressed()
        kind = st['kind']
        st['time'] -= dt
        if kind == 'sweep':
            slow = 0.6 if abs(st['pos'] - st['bc']) < st['bw'] / 2 + 0.04 else 1.0       # el cursor se frena al pasar por la banda
            st['pos'] += st['dir'] * st['speed'] * slow * dt
            if st['pos'] > 1:
                st['pos'], st['dir'] = 1.0, -1.0
            elif st['pos'] < 0:
                st['pos'], st['dir'] = 0.0, 1.0
        else:
            st['use_p'] = kind == 'drift'
            cur = st['cur'][st['ch']] if kind == 'dual' else st['cur']
            df = self.rd_axis('f', keys, (pygame.K_a, pygame.K_LEFT), (pygame.K_d, pygame.K_RIGHT), 1.3, dt)
            moved = abs(df)
            cur['f'] = clamp(cur['f'] + df, F_MIN, F_MAX)
            cur['a'] = clamp(cur['a'] + self.rd_axis('a', keys, (pygame.K_s, pygame.K_DOWN), (pygame.K_w, pygame.K_UP), 0.6, dt), 0.12, 1.0)
            if kind == 'drift':
                cur['p'] = (cur['p'] + self.rd_axis('p', keys, (pygame.K_q,), (pygame.K_e,), 2.4, dt)) % (2 * math.pi)
                b = st['base']
                st['tgt'] = dict(f=clamp(b['f'] + 0.35 * math.sin(rd['t'] * 0.9), F_MIN, F_MAX), a=clamp(b['a'] + 0.08 * math.sin(rd['t'] * 1.3 + 1), 0.15, 1.0),
                                 p=(b['p'] + rd['t'] * 0.8) % (2 * math.pi))
            if kind == 'jam':
                st['jam_t'] -= dt
                if st['jam_t'] <= 0:
                    st['jam_t'] = random.uniform(3.0, 4.5)
                    st['jam_fl'] = 0.5
                    cur['f'] = clamp(cur['f'] + random.choice((-1, 1)) * random.uniform(0.5, 0.9), F_MIN, F_MAX)
                    cur['a'] = clamp(cur['a'] + random.choice((-1, 1)) * random.uniform(0.12, 0.25), 0.12, 1.0)
                    self.audio.play('hit', .4)
                    self.shake = max(self.shake, 3)
            if moved > 0:
                rd['blip'] -= dt
                if rd['blip'] <= 0:
                    rd['blip'] = 0.11
                    self.audio.play('blip', .12)
            if kind == 'dual':
                ok = all(self.rd_match(st['cur'][i], st['tgt'][i], st) for i in (0, 1))
            else:
                ok = self.rd_match(cur, st['tgt'], st)
            st['matched'] = ok
            if ok:
                st['lock'] += dt / st['need']
                rd['beep'] -= dt
                if rd['beep'] <= 0:
                    rd['beep'] = 0.25
                    self.audio.play('ping', .18)
                if st['lock'] >= 1.0:
                    st['lock'] = 1.0
                    self.rd_stage_ok()
                    return
            else:
                st['lock'] = max(0.0, st['lock'] - dt * 1.5)
        if st['time'] <= 0:
            st['time'] = 0.0
            rd['fails'] += 1
            self.hull = max(1.0, self.hull - 4)
            self.shake = 8
            self.audio.play('lose', .6)
            if rd['fails'] >= 3:
                rd['phase'], rd['pt'] = 'lost', 0.0
            else:
                rd['phase'], rd['pt'] = 'retry', 0.0

    # ------------------------------------------------------------------ cierre y recompensa
    def end_radio(self, how):
        rd = self.rd
        k = rd['radar']
        self.go('map')
        if how == 'ok':
            self.radars[k]['hacked'] = True
            n = len(rd['kinds'])
            bonus = 400 + 100 * self.wave + 100 * n - 80 * rd['fails']
            self.add_score(max(200, bonus))
            loot = random.choice(LOOT)
            if loot == 'SUMINISTROS':
                self.fuel = 100.0
                self.ammo = min(40, self.ammo + 10)
                txt = 'Combustible lleno y +10 munición'
            elif loot == 'REPARACIONES':
                self.hull = min(self.hull_max, self.hull + 30)
                txt = 'Casco +30'
            elif loot == 'INTELIGENCIA':
                if self.attack is None and not self.warned:
                    self.strike_t += 25.0
                txt = 'Próximo ataque enemigo retrasado 25 s'
            else:
                self.add_score(600)
                txt = '+600 puntos'
            self.radar_t = max(self.radar_t, 90.0)
            self.banner('¡RADAR INTERCEPTADO!', '%s  |  Bonus +%d' % (txt, max(200, bonus)), (120, 255, 190), 4.2)
            self.toast('Flota enemiga visible 90 s', (160, 230, 255))
            nr = self.radars_done()
            if nr == LAND_RADARS:
                self.toast('¡DESEMBARCO DESBLOQUEADO! (L junto a una isla de antena)', (140, 230, 255))
            if nr == PORT_RADARS:
                self.toast('¡ASALTO AL PUERTO DESBLOQUEADO! (T junto al puerto enemigo)', (140, 230, 255))
        elif how == 'lost':
            self.radars[k]['cd'] = 40.0
            self.hull = max(1.0, self.hull - 8)
            self.banner('¡CONTRAHACKEO!', 'El radar detectó la intrusión: -8 casco y en alerta 40 s', (255, 110, 90), 3.4)
        else:
            self.radars[k]['cd'] = 8.0
            self.toast('Intercepción abortada', (255, 200, 120))

    # ------------------------------------------------------------------ dibujo
    def rd_wave(self, cv, par, col, width=3, noise=0.0, phase_shift=0.0):
        pts = []
        n = 150
        sy = SCOPE.h * 0.42
        for i in range(n + 1):
            u = i / n
            y = par['a'] * math.sin(2 * math.pi * par['f'] * u + par['p'] + phase_shift)
            if noise:
                y += random.uniform(-noise, noise)
            pts.append((SCOPE.x + u * SCOPE.w, SCOPE.centery - y * sy))
        pygame.draw.lines(cv, tuple(int(c * 0.35) for c in col), False, pts, width + 6)
        pygame.draw.lines(cv, col, False, pts, width)
        pygame.draw.lines(cv, (255, 255, 255), False, pts, 1)

    def rd_led(self, cv, x, y, level):
        col = ((70, 76, 84), (255, 200, 70), (90, 255, 150))[level]
        pygame.draw.circle(cv, (10, 14, 20), (x, y), 9)
        pygame.draw.circle(cv, col, (x, y), 7)
        if level == 2:
            glow(cv, x, y, 18, (60, 220, 120), 0.8)

    def rd_knob(self, cv, x, y, val, label, active=True):
        pygame.draw.circle(cv, (8, 16, 24), (x, y), 30)
        pygame.draw.circle(cv, (60, 120, 150) if active else (40, 70, 90), (x, y), 30, 3)
        for i in range(11):
            a = math.radians(-225 + 270 * i / 10)
            pygame.draw.line(cv, (70, 110, 130), (x + math.cos(a) * 23, y + math.sin(a) * 23), (x + math.cos(a) * 28, y + math.sin(a) * 28), 1)
        a = math.radians(-225 + 270 * clamp(val, 0, 1))
        pygame.draw.line(cv, (255, 210, 90) if active else (150, 140, 100), (x, y), (x + math.cos(a) * 24, y + math.sin(a) * 24), 4)
        pygame.draw.circle(cv, (30, 44, 56), (x, y), 7)
        self.text(cv, label, self.f_s, (150, 180, 210), x, y + 36, 'c')

    def draw_radio(self, cv):
        rd = self.rd
        st = rd['st']
        t = self.t
        kind = st['kind']
        cv.fill((3, 9, 14))
        for i in range(0, H, 6):
            pygame.draw.line(cv, (6, 16, 22), (0, i), (W, i))
        self.text(cv, 'INTERCEPCIÓN DE RADIO', self.f_l, (110, 240, 255), 56, 24)
        self.text(cv, 'RADAR ENEMIGO', self.f_s, (255, 150, 130), 56, 100)
        self.text(cv, 'ESTACIÓN %d/%d  |  %s' % (rd['stage'] + 1, len(rd['kinds']), KIND_NAMES[kind]), self.f_m, (255, 220, 120), 56, 68)
        # pantalla del osciloscopio
        pygame.draw.rect(cv, (6, 20, 28), SCOPE.inflate(24, 24), border_radius=14)
        pygame.draw.rect(cv, (40, 110, 130), SCOPE.inflate(24, 24), 3, border_radius=14)
        pygame.draw.rect(cv, (4, 14, 20), SCOPE)
        for i in range(1, 10):
            x = SCOPE.x + i * SCOPE.w // 10
            pygame.draw.line(cv, (14, 44, 56), (x, SCOPE.y), (x, SCOPE.bottom))
        for j in range(1, 6):
            y = SCOPE.y + j * SCOPE.h // 6
            pygame.draw.line(cv, (14, 44, 56) if j != 3 else (24, 80, 96), (SCOPE.x, y), (SCOPE.right, y))
        matched = bool(st.get('matched')) and rd['phase'] == 'play'
        ok_col = (90, 255, 150)
        if kind == 'sweep':
            self.draw_sweep(cv, st)
        else:
            if kind == 'dual':
                self.rd_wave(cv, st['tgt'][0], (90, 220, 255))
                self.rd_wave(cv, st['tgt'][1], (255, 110, 230))
                for i, col in ((0, (255, 200, 80)), (1, (255, 150, 90))):
                    self.rd_wave(cv, st['cur'][i], ok_col if matched else col, 5 if st['ch'] == i else 2)
            else:
                self.rd_wave(cv, st['tgt'], (90, 220, 255))
                self.rd_wave(cv, st['cur'], ok_col if matched else (255, 200, 80), 4, noise=0.35 if st['jam_fl'] > 0 else 0.0)
            if st['jam_fl'] > 0 and int(t * 30) % 2 == 0:
                for _ in range(8):
                    y = random.randint(SCOPE.y, SCOPE.bottom)
                    pygame.draw.line(cv, (255, 70, 70), (SCOPE.x, y), (SCOPE.right, y), 1)
                self.text(cv, '¡INTERFERENCIA!', self.f_l, (255, 90, 90), SCOPE.centerx, SCOPE.y + 12, 'c')
            # indicadores de cercanía
            rows = []
            if kind == 'dual':
                for i in (0, 1):
                    rows.append(('CANAL %s' % 'AB'[i], self.rd_closeness(st['cur'][i], st['tgt'][i], st), i == st['ch']))
            else:
                rows.append(('SEÑAL', self.rd_closeness(st['cur'], st['tgt'], st), True))
            x0, y0 = 830, 190
            self.panel(cv, (x0 - 16, y0 - 14, 250, 40 + 70 * len(rows)), 170)
            kn = st['cur'][st['ch']] if kind == 'dual' else st['cur']
            ky = y0 + 70 * len(rows) + 70
            knobs = [(kn['f'] - F_MIN) / (F_MAX - F_MIN), (kn['a'] - 0.12) / 0.88] + ([kn['p'] / (2 * math.pi)] if kind == 'drift' else [])
            for ki, (kv, kl) in enumerate(zip(knobs, ('FREC', 'AMP', 'FASE'))):
                self.rd_knob(cv, x0 + 36 + ki * (150 if len(knobs) == 2 else 78), ky, kv, kl)
            for ri, (nm, cl, act) in enumerate(rows):
                yy = y0 + ri * 70
                self.text(cv, nm + ('  <' if act and kind == 'dual' else ''), self.f_s, (200, 225, 250), x0, yy)
                for ci, (lab, key) in enumerate((('FREC', 'f'), ('AMP', 'a'), ('FASE', 'p'))):
                    if key == 'p' and kind != 'drift':
                        continue
                    self.rd_led(cv, x0 + 22 + ci * 70, yy + 36, cl[key])
                    self.text(cv, lab, self.f_s, (150, 180, 210), x0 + 22 + ci * 70, yy + 48, 'c')
        # barra de bloqueo
        if kind == 'sweep':
            frac = st['hits'] / 3.0
            lab = 'ACIERTOS %d/3' % st['hits']
        else:
            frac = st['lock']
            lab = 'BLOQUEO DE SEÑAL'
        self.bar(cv, SCOPE.x, SCOPE.bottom + 34, SCOPE.w, 26, frac, ok_col if frac > 0 else (60, 90, 110), lab)
        # reloj
        low = st['time'] < 8 and rd['phase'] == 'play'
        tcol = (255, 90, 80) if low else ((255, 210, 80) if st['time'] < 15 else (110, 240, 255))
        self.text(cv, '%02d.%02d' % (int(st['time']), int((st['time'] % 1) * 100)), self.f_clk, tcol, W - 44, 10, 'r')
        self.text(cv, 'INTENTOS %d/3' % (rd['fails'] + 1 if rd['fails'] < 3 else 3), self.f_s, (150, 190, 220), W - 44, 86, 'r')
        # estaciones y mensaje descifrado
        for i, kd in enumerate(rd['kinds']):
            x = 56 + i * 150
            done = i < rd['stage'] or (i == rd['stage'] and rd['phase'] in ('ok', 'win'))
            cur_ = i == rd['stage']
            pygame.draw.rect(cv, (10, 28, 38), (x, 560, 138, 34), border_radius=6)
            pygame.draw.rect(cv, (90, 255, 150) if done else ((255, 220, 100) if cur_ else (50, 80, 100)), (x, 560, 138, 34), 2, border_radius=6)
            self.text(cv, KIND_NAMES[kd][:14], self.f_s, (200, 225, 250) if (done or cur_) else (110, 130, 150), x + 69, 568, 'c')
        shown = []
        n_ok = rd['stage'] + (1 if rd['phase'] in ('ok', 'win') else 0)
        for i, w in enumerate(rd['words']):
            if i < n_ok:
                shown.append(w)
            else:
                shown.append(''.join(random.choice('#%&$@?01') if int(t * 8 + i + j) % 3 else '.' for j in range(len(w))))
        self.panel(cv, (40, 620, W - 80, 70), 180)
        self.text(cv, 'TRANSMISIÓN ENEMIGA', self.f_s, (150, 190, 220), 60, 628)
        self.text(cv, '  '.join(shown), self.f_l, (90, 255, 170), 60, 650, shadow=False)
        self.text(cv, KIND_HINT[kind] + '  |  TAB: abortar', self.f_s, (180, 205, 235), 56, H - 40)
        if rd['phase'] == 'ok':
            k = clamp(rd['pt'] / 0.25, 0, 1)
            self.dim(cv, int(60 * k))
            self.text(cv, '¡SEÑAL BLOQUEADA!', self.f_xl, (110, 255, 170), W // 2, 300, 'c', alpha=int(255 * k))
        elif rd['phase'] == 'retry':
            self.dim(cv, 60)
            self.text(cv, 'SEÑAL PERDIDA', self.f_xl, (255, 120, 90), W // 2, 300, 'c')
            self.text(cv, 'Nueva frecuencia  |  contraataque -4 casco', self.f_m, (255, 190, 160), W // 2, 370, 'c')
        elif rd['phase'] == 'lost':
            self.dim(cv, 80)
            self.text(cv, 'INTRUSIÓN DETECTADA', self.f_xl, (255, 90, 90), W // 2, 300, 'c')
            self.text(cv, 'El radar activó el contrahackeo', self.f_m, (255, 190, 160), W // 2, 370, 'c')
        elif rd['phase'] == 'win':
            self.dim(cv, 90)
            self.text(cv, 'COMUNICACIONES', self.f_xl, (110, 255, 170), W // 2, 215, 'c')
            self.text(cv, 'INTERCEPTADAS', self.f_xl, (110, 255, 170), W // 2, 295, 'c')
            self.text(cv, '"%s"' % ' '.join(rd['words']), self.f_l, (255, 240, 170), W // 2, 395, 'c')
            self.text(cv, 'Descifrando recompensa...', self.f_m, (170, 210, 240), W // 2, 450, 'c')

    def draw_sweep(self, cv, st):
        n = len(st['bars'])
        bw = SCOPE.w / n
        t = self.t
        for i in range(n):
            u = (i + 0.5) / n
            near = abs(u - st['bc']) < st['bw'] / 2
            h = (0.18 + 0.5 * abs(math.sin(t * (1.3 + (i % 5) * 0.3) + st['bars'][i] * 9))) * SCOPE.h * 0.8
            if near:
                h = max(h, SCOPE.h * 0.78 * (0.7 + 0.3 * math.sin(t * 9)))
            col = (90, 255, 150) if near else (40, 130, 160)
            pygame.draw.rect(cv, col, (SCOPE.x + i * bw + 2, SCOPE.bottom - h, bw - 4, h))
        pygame.draw.rect(cv, (60, 255, 150), (SCOPE.x + (st['bc'] - st['bw'] / 2) * SCOPE.w, SCOPE.y, st['bw'] * SCOPE.w, SCOPE.h), 2)
        cx = SCOPE.x + st['pos'] * SCOPE.w
        glow(cv, cx, SCOPE.centery, 90, (255, 230, 120), 0.5)
        pygame.draw.line(cv, (255, 245, 170), (cx, SCOPE.y), (cx, SCOPE.bottom), 4)
        if st['flash'] > 0:
            pygame.draw.rect(cv, (90, 255, 150), SCOPE, 4)
        if st['miss'] > 0:
            pygame.draw.rect(cv, (255, 70, 70), SCOPE, 4)
