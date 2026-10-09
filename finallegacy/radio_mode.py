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
CHIP_NAMES = {'tune': 'SINTONÍA', 'drift': 'DERIVA', 'jam': 'INTERFERENCIA', 'dual': '2 CANALES', 'sweep': 'BARRIDO', 'simon': 'SECUENCIA', 'code': 'CLAVE', 'wire': 'CABLES', 'rhythm': 'RITMO', 'lock': 'CERRADURA'}
KIND_NAMES = {'tune': 'SINTONÍA', 'drift': 'SEÑAL A LA DERIVA', 'jam': 'INTERFERENCIA', 'dual': 'DOS CANALES', 'sweep': 'BARRIDO DE ESPECTRO',
              'simon': 'SECUENCIA DE TECLAS', 'code': 'DESCIFRAR LA CLAVE', 'wire': 'CORTAR EL CABLE CORRECTO', 'rhythm': 'RITMO DE DATOS', 'lock': 'CERRADURA GIRATORIA'}
KIND_HINT = {
    'tune': 'A/D frecuencia  |  W/S amplitud: calzá la onda amarilla con la celeste',
    'drift': 'A/D frecuencia  |  W/S amplitud  |  Q/E fase: la señal se mueve, seguila',
    'jam': 'A/D frecuencia  |  W/S amplitud: el enemigo interfiere y te desajusta',
    'dual': 'A/D frecuencia  |  W/S amplitud  |  ESPACIO: cambiar de canal  |  calzá los dos',
    'sweep': 'ESPACIO cuando el cursor esté sobre la banda verde  |  4 aciertos: la banda se achica y el cursor acelera',
    'simon': 'Mirá la secuencia y repetila con las flechas o WASD  |  un error la repite y cuesta 3 s',
    'code': 'Teclas 1-6: armá la clave de 4 símbolos  |  RETROCESO borra  |  ENTER prueba  |  verde: en su lugar, amarillo: está pero en otro lugar',
    'wire': 'Teclas 1-6: cortá el cable que indican las reglas  |  un error cuesta 8 s y 2 de casco',
    'rhythm': 'D F J K (o las flechas): pulsá cada nota justo cuando cruza la línea  |  acertá al menos el 70 %',
    'lock': 'ESPACIO cuando el indicador esté dentro de la zona brillante  |  3 zonas en orden  |  un error cuesta 3 s',
}
RH_KEYS = {pygame.K_d: 0, pygame.K_f: 1, pygame.K_j: 2, pygame.K_k: 3, pygame.K_LEFT: 0, pygame.K_DOWN: 1, pygame.K_UP: 2, pygame.K_RIGHT: 3}
PUZZLES = ('simon', 'code', 'wire', 'rhythm', 'lock')                    # minijuegos de lógica y reflejos (sin ondas)
SYMS = ((255, 90, 90), (90, 160, 255), (255, 215, 80), (100, 235, 140), (210, 120, 255), (255, 255, 255))   # colores de los 6 símbolos de la clave
WIRE_COLS = {'ROJO': (235, 70, 60), 'AZUL': (70, 130, 255), 'AMARILLO': (255, 215, 70), 'VERDE': (90, 225, 130), 'BLANCO': (235, 235, 235)}
WIRE_RULES = ('1) Si hay más de un cable ROJO: cortá el último rojo.',
              '2) Si no, y el serie termina en PAR y hay un AZUL: cortá el primer azul.',
              '3) Si no, y no hay cables AMARILLOS: cortá el segundo cable.',
              '4) Si no: cortá el primer cable.')
NUM_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
            pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2, pygame.K_KP4: 3, pygame.K_KP5: 4, pygame.K_KP6: 5}
ARROWS = {pygame.K_UP: 'U', pygame.K_w: 'U', pygame.K_DOWN: 'D', pygame.K_s: 'D', pygame.K_LEFT: 'L', pygame.K_a: 'L', pygame.K_RIGHT: 'R', pygame.K_d: 'R'}
PHRASES = ('FLOTA NORTE ATACA CIUDAD AMANECER', 'MISILES LISTOS ORDEN ESPERAR SEÑAL', 'REFUERZOS LLEGAN PUERTO MEDIANOCHE SILENCIO',
           'SUBMARINOS BAJO HIELO SEGUIR OBJETIVO', 'ANTENA ENEMIGA CAMBIAR CLAVE URGENTE', 'CONVOY SIN ESCOLTA RUTA SUR',
           'JEFE MARCHA ESCUDO ACTIVO FORTALEZA', 'BATERIAS COSTERAS APUNTAN BAHIA AZUL')
LAND_RADARS = 1                                       # radares interceptados (en la oleada) para desbloquear el desembarco
PORT_RADARS = 2                                       # ... y el asalto al puerto enemigo
LOOT = ('SUMINISTROS', 'REPARACIONES', 'INTELIGENCIA', 'BOTÍN')



# frases del hacker por minijuego (tono mezcla de militar e irónico); se sortea una de cada lista
SAY_INTRO = {
    'tune': ('Interceptando la transmisión enemiga. Calzá la onda amarilla con la celeste.', 'Radar a la vista, soldado. Frecuencia y amplitud hasta que calcen.',
             'Sintonía fina: como encontrar una radio buena en una ruta desierta. Calzá las ondas.'),
    'drift': ('La señal se mueve: el enemigo no quiere que lo escuchemos. Seguila.', 'Objetivo en movimiento. Frecuencia, amplitud y fase a la vez. Fácil, ¿no?'),
    'jam': ('Nos están interfiriendo. Mantené la señal aunque te la muevan.', 'Interferencia enemiga. Si se corre, la volvés a poner. Así de simple... y de molesto.'),
    'dual': ('Dos canales a la vez. Espacio cambia de uno al otro. Dos canales, un solo cerebro.', 'Doble canal. Calzá los dos, uno por vez. Sin pánico.'),
    'sweep': ('Barrido de espectro. Frená el cursor sobre la banda verde, con calma y sin parpadear.', 'Banda verde: ahí. Pulsá cuando el cursor pase. Cuatro veces y la banda se achica.'),
    'simon': ('Secuencia de acceso. Memorizá el orden y repetilo. La memoria de pez no sirve.', 'Atento a las luces: lo que ves es lo que repetís. Sin trampa.',
              'Prueba de memoria. El enemigo confía en que no seas capaz. Demostrale lo contrario.'),
    'code': ('Clave de cuatro símbolos, sin repetir. Verde: en su lugar. Amarillo: está pero mal ubicado. Deducí.',
             'Descifrar clave: siete intentos y cuatro símbolos. Dicen que la lógica es un arma. Usala.',
             'Una contraseña. Alguien la eligió en cinco segundos. Rompámosla en seis.'),
    'wire': ('Hay una carga con cables. Leé las reglas en orden y cortá el correcto. Sin apuro, pero con apuro.',
             'Desactivá el mecanismo: el cable equivocado sale caro. Leé bien las reglas antes de cortar.',
             'Cables de colores y un manual. Parece un cumpleaños, pero con explosivos.'),
    'rhythm': ('Flujo de datos enemigo. Pulsá cada nota justo en la línea. Acertá el setenta por ciento.',
               'Ritmo de datos. Si bailás tan bien como disparás, esto es un paseo.'),
    'lock': ('Cerradura giratoria. Tres zonas, en orden. Pulsá espacio cuando el indicador entre.', 'Cerradura de combinación: pulso firme, paciencia y un poco de suerte.'),
}
SAY_OK = {
    'tune': ('¡Señal bloqueada!', 'Frecuencia calzada. Buen trabajo, soldado.'),
    'drift': ('La seguiste hasta el final. ¡Señal bloqueada!', 'Se movía, pero no se escapó.'),
    'jam': ('Interferencia superada. El enemigo está desconcertado.', '¡Señal bloqueada! Que sigan interfiriendo.'),
    'dual': ('Los dos canales calzados. ¡Señal bloqueada!', 'Doble sintonía lograda. Impecable.'),
    'sweep': ('Cuatro de cuatro. Pulso de cirujano.', '¡Señal bloqueada! Ni un temblor.'),
    'simon': ('Secuencia correcta. Acceso concedido.', 'Esa memoria sirve. Siguiente.'),
    'code': ('Clave descifrada. Lógica pura.', 'Código roto. El enemigo cambiará la contraseña... tarde.'),
    'wire': ('Cable cortado. Mecanismo desactivado.', 'Ni un segundo de sobra. Bien cortado.'),
    'rhythm': ('Datos sincronizados. Buen pulso.', 'Ritmo cumplido. Solo te falta el micrófono.'),
    'lock': ('Cerradura abierta. Trabajo limpio.', 'Tres de tres. Abierto.'),
}
SAY_LAST = ('¡Comunicaciones interceptadas! Ya tenemos todo.', 'Transmisión completa. Les arruinamos el día.', 'Todo interceptado. Que se pregunten qué pasó.')
SAY_TIME = {
    'simon': ('Se acabó el tiempo. Repetimos, y esta vez sin distraerte.',), 'code': ('Sin intentos y sin tiempo. Cambiaron la clave: otra vez.',),
    'wire': ('Se agotó el tiempo con los cables. Respirá y otra vez.',), 'rhythm': ('No llegamos al ritmo mínimo. Otra pasada, y con el pie.',),
    'lock': ('Cerradura trabada. Otra vez, con pulso firme.',),
}
SAY_TIME_GENERIC = ('Se cortó la señal. Nueva frecuencia, ¡otra vez!', 'Tiempo agotado. Reajustamos y probamos de nuevo.', 'Perdimos el enlace. Concentrate, soldado.')
SAY_LOST = ('Perdimos la señal... ¡nos detectaron, contraataque!', 'Intrusión detectada. Prepárate: viene el contrahackeo.', 'Demasiados fallos. Nos descubrieron, ¡a pelear!')
SAY_MISS = {
    'simon': ('Esa no era. Atención a las luces.', 'Error de secuencia. Respirá y repetí.'),
    'wire': ('¡Cable equivocado! Casi nos descubren.', 'Ese no era. Leé las reglas, soldado.', 'Boom... no, todavía no. Ojo con el siguiente.'),
    'lock': ('Te pasaste de la zona. Con calma.', 'Fuera de la zona. El pulso, soldado.'),
    'sweep': ('Fuera de la banda. Más paciencia.', 'Ese no cuenta. Esperá el momento.'),
    'code': ('Ni un símbolo en su lugar. Eso también es información.', 'Nada acertó. Descartamos esos y seguimos.'),
}
SAY_LOW = ('Quedan diez segundos. ¡Apurate!', 'Diez segundos, soldado. El reloj no negocia.')
SAY_COMBO = ('Racha de diez. Buen pulso.', 'Diez seguidas. Mantenelo.')


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
        pool = ['jam', 'dual', 'sweep', 'simon', 'code', 'wire', 'rhythm', 'lock'] + (['drift'] if self.wave >= 2 else [])
        while len(kinds) < n:
            k = random.choice(pool)
            if k != kinds[-1]:
                kinds.append(k)
        words = random.choice(PHRASES).split()
        self.rd = dict(radar=radar, kinds=kinds, stage=0, fails=0, phase='play', pt=0.0, words=words, t=0.0, time_left=0.0,
                       calls=[], bonus=0, loot='', hold={}, blip=0.0, beep=0.0, boot=0.0)
        self.rd_stage_init(first=True)
        self.rd_say(SAY_INTRO, kinds[0], 'info')
        self.aim = [W / 2, H / 2]
        self.fx_pulse('cyan', .5)
        self.go('radio')

    def rd_say(self, table, kind, mood, cooldown=0.0):
        """El hacker dice una frase de 'table' (dict por minijuego o tupla). Con 'cooldown' evita hablar demasiado seguido."""
        rd = self.rd
        if cooldown and rd.get('say_cd', 0.0) > rd['t']:
            return
        opts = table.get(kind) if isinstance(table, dict) else table
        if not opts:
            return
        self.say('hacker', random.choice(opts), mood, 'right', 470)
        if cooldown:
            rd['say_cd'] = rd['t'] + cooldown

    def rd_tol(self):
        return max(0.62, 1.0 - 0.05 * self.wave)

    def rd_rand_par(self):
        return dict(f=random.uniform(1.4, 5.2), a=random.uniform(0.3, 0.95), p=random.uniform(0, 6.28))

    def rd_stage_init(self, first=False):
        rd = self.rd
        kind = rd['kinds'][rd['stage']]
        tol = self.rd_tol()
        st = dict(kind=kind, lock=0.0, flash=0.0, jam_t=3.0, jam_fl=0.0, miss=0.0, tol=dict(f=0.22 * tol, a=0.09 * tol, p=0.42 * tol), ch=0)
        total = {'tune': 32.0, 'drift': 38.0, 'jam': 36.0, 'dual': 42.0, 'sweep': 34.0, 'simon': 36.0, 'code': 70.0, 'wire': 45.0, 'rhythm': 50.0, 'lock': 36.0}[kind] - 1.5 * rd['fails']
        st['total'] = st['time'] = max(18.0, total)
        st['need'] = {'tune': 1.0, 'drift': 1.5, 'jam': 1.4, 'dual': 1.2}.get(kind, 1.0)
        if kind in PUZZLES:
            self.rd_puzzle_init(st, kind)
        elif kind == 'sweep':
            st.update(pos=0.0, dir=1.0, speed=0.55 + 0.035 * self.wave, bw=max(0.15, 0.24 - 0.012 * self.wave), bc=random.uniform(0.2, 0.8), hits=0, bars=[random.random() for _ in range(44)])
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
            self.rd_say(SAY_INTRO, kind, 'info')

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
        if st['kind'] in PUZZLES:
            return self.rd_puzzle_key(st, key)
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if st['kind'] == 'dual':
                st['ch'] ^= 1
                self.audio.play('blip', .5)
            elif st['kind'] == 'sweep':
                self.rd_sweep_hit()

    def rd_sweep_hit(self):
        rd = self.rd
        st = rd['st']
        if abs(st['pos'] - st['bc']) <= st['bw'] / 2:
            st['hits'] += 1
            st['flash'] = 0.35
            self.audio.play('pickup', .7)
            if st['hits'] >= 4:
                self.rd_stage_ok()
                return
            st['bw'] = max(0.055, st['bw'] * 0.7)                     # la caja se achica en cada acierto
            st['speed'] *= 1.2
            for _ in range(20):
                nb = random.uniform(0.12, 0.88)
                if abs(nb - st['bc']) > 0.25:
                    st['bc'] = nb
                    break
        else:
            st['hits'] = max(0, st['hits'] - 1)
            st['bw'] = min(0.24, st['bw'] / 0.8)                         # fallar agranda la banda un poco pero cuesta tiempo
            st['miss'] = 0.4
            st['time'] = max(1.0, st['time'] - 2.0)
            self.audio.play('hit', .5)
            self.rd_say(SAY_MISS, 'sweep', 'warn', 6.0)
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
        self.fx_pulse('green', .9)
        if self.rd['stage'] + 1 < len(self.rd['kinds']):
            self.rd_say(SAY_OK, self.rd['st']['kind'], 'ok')
        else:
            self.say('hacker', random.choice(SAY_LAST), 'ok', 'right', 470)
        self.add_score(150 + 40 * self.wave)

    def upd_radio(self, dt):
        rd = self.rd
        st = rd['st']
        rd['t'] += dt
        if rd['boot'] < 1.4:
            rd['boot'] += dt
            return
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
        if st['time'] < 10 and not st.get('low_said') and st['total'] > 20:
            st['low_said'] = True
            self.say('hacker', random.choice(SAY_LOW), 'warn', 'right', 470)
        if kind in PUZZLES:
            self.rd_puzzle_update(st, dt)
            if rd['phase'] != 'play':
                return
        elif kind == 'sweep':
            st['pos'] += st['dir'] * st['speed'] * dt                                      # velocidad constante, aunque pase por la banda
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
            self.fx_pulse('red', 1.2)
            if rd['fails'] >= 3:
                rd['phase'], rd['pt'] = 'lost', 0.0
                self.say('hacker', random.choice(SAY_LOST), 'bad', 'right', 470)
            else:
                rd['phase'], rd['pt'] = 'retry', 0.0
                self.say('hacker', random.choice(SAY_TIME.get(kind, SAY_TIME_GENERIC)), 'warn', 'right', 470)

    # ------------------------------------------------------------------ cierre y recompensa
    def start_penalty_combat(self, left=2, total=2):
        """Contrahackeo: combates forzados contra barcos que no pertenecen a la flota del mapa. No se puede huir,
        no dan puntos ni bonus y no descuentan barcos de la oleada."""
        mh = 10 + 2 * (self.wave - 1)
        en = dict(x=self.sx, y=self.sy, h=0.0, v=0.0, hp=mh, max=mh, state='chase', cool=0.0, is_boss=False, pen=left, tot=total)
        self.start_combat(en)
        self.c['pen'] = True
        self.banners = []
        self.banner('¡CONTRAHACKEO! BARCO %d/%d' % (total - left + 1, total), 'No podés huir y no da puntos ni bonus: sobreviví', (255, 110, 90), 4.0)

    def penalty_next(self):
        """Termina un combate de contrahackeo: pasa al siguiente barco o vuelve al mapa."""
        en = self.enemy_ref
        if self.hull <= 0:
            return self.lose_ship('Tu buque no sobrevivió al contrahackeo')
        if en['pen'] > 1:
            self.start_penalty_combat(en['pen'] - 1, en['tot'])
        else:
            self.toast('Contrahackeo superado (sin puntos ni bonus)', (255, 200, 120))
            self.go('map')

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
            self.start_penalty_combat(2, 2)
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
        bad = rd['phase'] in ('retry', 'lost') or st.get('miss', 0) > 0 or st.get('jam_fl', 0) > 0
        good = rd['phase'] in ('ok', 'win') or st.get('flash', 0) > 0
        self.fx_rain(cv, 'red' if bad else ('green' if good else 'cyan'), 1.0 + (1.0 if st['time'] < 10 and rd['phase'] == 'play' else 0), 150, (3, 9, 14))
        for i in range(0, H, 6):
            pygame.draw.line(cv, (6, 16, 22), (0, i), (W, i))
        self.fx_title(cv, 'INTERCEPCIÓN DE RADIO', self.f_l, (110, 240, 255), 56, 24)
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
        if kind in PUZZLES:
            self.draw_puzzle(cv, st)
        elif kind == 'sweep':
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
        if kind in PUZZLES:
            frac, lab = st['prog'], st['lab']
        elif kind == 'sweep':
            frac = st['hits'] / 4.0
            lab = 'ACIERTOS %d/4' % st['hits']
        else:
            frac = st['lock']
            lab = 'BLOQUEO DE SEÑAL'
        self.bar(cv, SCOPE.x, SCOPE.bottom + 34, SCOPE.w, 26, frac, ok_col if frac > 0 else (60, 90, 110), lab)
        # reloj
        low = st['time'] < 8 and rd['phase'] == 'play'
        tcol = (255, 90, 80) if low else ((255, 210, 80) if st['time'] < 15 else (110, 240, 255))
        self.text(cv, '%02d.%02d' % (int(st['time']), int((st['time'] % 1) * 100)), self.f_clk, tcol, W - 44, 10, 'r')
        self.text(cv, 'INTENTOS %d/3' % (rd['fails'] + 1 if rd['fails'] < 3 else 3), self.f_s, (150, 190, 220), W - 44, 72, 'r')
        # estaciones y mensaje descifrado
        x = 56
        for i, kd in enumerate(rd['kinds']):
            done = i < rd['stage'] or (i == rd['stage'] and rd['phase'] in ('ok', 'win'))
            cur_ = i == rd['stage']
            name = CHIP_NAMES[kd]
            cw = self.f_s.size(name)[0] + 28
            pygame.draw.rect(cv, (10, 28, 38), (x, 560, cw, 34), border_radius=6)
            pygame.draw.rect(cv, (90, 255, 150) if done else ((255, 220, 100) if cur_ else (50, 80, 100)), (x, 560, cw, 34), 2, border_radius=6)
            self.text(cv, name, self.f_s, (200, 225, 250) if (done or cur_) else (110, 130, 150), x + cw // 2, 566, 'c')
            x += cw + 10
        shown = []
        n_ok = rd['stage'] + (1 if rd['phase'] in ('ok', 'win') else 0)
        for i, w in enumerate(rd['words']):
            if i < n_ok:
                shown.append(w)
            else:
                shown.append(''.join(random.choice('#%&$@?01') if int(t * 8 + i + j) % 3 else '.' for j in range(len(w))))
        self.panel(cv, (40, 620, W - 80, 70), 180)
        self.text(cv, 'TRANSMISIÓN ENEMIGA', self.f_s, (150, 190, 220), 60, 628)
        msg = '  '.join(shown)
        self.text(cv, msg, self.fit_font(msg, W - 160, self.f_l, self.f_m, self.f_s), (90, 255, 170), 60, 650, shadow=False)
        self.text(cv, KIND_HINT[kind] + '  |  TAB: abortar', self.f_s, (180, 205, 235), 56, H - 40)
        if rd['phase'] == 'ok':
            k = clamp(rd['pt'] / 0.25, 0, 1)
            self.dim(cv, int(60 * k))
            self.text(cv, '¡SEÑAL BLOQUEADA!', self.f_xl, (110, 255, 170), W // 2, 300, 'c', alpha=int(255 * k))
        elif rd['phase'] == 'retry':
            self.dim(cv, 60)
            self.fx_stamp(cv, 'SEÑAL PERDIDA', (255, 120, 90), 300, clamp(rd['pt'] / 0.5, 0, 1), 3)
            self.text(cv, 'Nueva frecuencia  |  contraataque -4 casco', self.f_m, (255, 190, 160), W // 2, 370, 'c')
        elif rd['phase'] == 'lost':
            self.dim(cv, 80)
            self.fx_stamp(cv, 'ACCESO DENEGADO', (255, 90, 90), 300, clamp(rd['pt'] / 0.5, 0, 1), 3)
            self.text(cv, 'El radar activó el contrahackeo', self.f_m, (255, 190, 160), W // 2, 370, 'c')
        elif rd['phase'] == 'win':
            self.dim(cv, 90)
            kd = clamp(rd['pt'] / 1.0, 0, 1)
            self.text(cv, self.fx_scramble('COMUNICACIONES', kd), self.f_xl, (110, 255, 170), W // 2, 215, 'c')
            self.text(cv, self.fx_scramble('INTERCEPTADAS', kd * 1.3 - .3), self.f_xl, (110, 255, 170), W // 2, 295, 'c')
            full = '"%s"' % ' '.join(rd['words'])
            full = self.fx_scramble(full, rd['pt'] / 2.0)
            self.text(cv, full, self.fit_font(full, W - 100, self.f_l, self.f_m, self.f_s), (255, 240, 170), W // 2, 395, 'c')
            self.text(cv, 'Descifrando recompensa...', self.f_m, (170, 210, 240), W // 2, 450, 'c')
        self.fx_frame(cv, (255, 90, 90) if bad else ((110, 255, 170) if good else (80, 200, 230)))
        if rd['boot'] < 1.4:
            self.fx_boot(cv, ['> SINTONIZANDO RECEPTOR...', '> BARRIENDO FRECUENCIAS ENEMIGAS...', '> SEÑAL DETECTADA'], rd['boot'])
        if rd['phase'] in ('retry', 'lost'):
            self.fx_shake(cv, 8 * clamp(1 - rd['pt'] / 0.45, 0, 1))


    # ------------------------------------------------------------------ minijuegos de lógica: secuencia, clave y cables
    def rd_puzzle_init(self, st, kind):
        st['prog'], st['lab'] = 0.0, ''
        if kind == 'simon':
            n = min(8, 4 + self.wave // 2)
            st.update(seq=[random.choice('UDLR') for _ in range(n)], mode='show', mt=0.8, idx=0, inp=[], lit=None, press=None, press_t=0.0, lab_='')
            st['lab'] = 'SECUENCIA 0/%d' % n
        elif kind == 'code':
            st.update(secret=random.sample(range(6), 4), guesses=[], cur=[], tries=7, shake=0.0)
            st['lab'] = 'INTENTOS 0/7'
        elif kind == 'rhythm':
            n = min(36, 18 + 2 * self.wave)
            gap = max(0.36, 0.62 - 0.03 * self.wave)
            notes, tt, last, run = [], 1.8, -1, 0
            while len(notes) < n:
                lane = random.randrange(4)
                if lane == last and run >= 2:
                    lane = (lane + random.randint(1, 3)) % 4
                run = run + 1 if lane == last else 1
                last = lane
                notes.append(dict(t=tt, lane=lane, hit=None))
                if self.wave >= 3 and random.random() < 0.18 and len(notes) < n:                 # nota doble
                    notes.append(dict(t=tt, lane=(lane + random.randint(1, 3)) % 4, hit=None))
                tt += gap * random.choice((1.0, 1.0, 1.0, 0.5, 1.5))
            st.update(notes=notes, now=0.0, fall=1.5, hits=0, combo=0, best=0, judge='', judge_t=0.0, press=[0.0] * 4, end=tt + 0.8, need=int(0.7 * len(notes) + 0.999))
            st['time'] = st['total'] = tt + 14.0
            st['lab'] = 'ACIERTOS 0/%d' % st['need']
        elif kind == 'lock':
            zw = max(0.34, 0.62 - 0.03 * self.wave)
            zones, a0 = [], random.uniform(0, 6.28)
            for i in range(3):
                zones.append((a0 + i * 2.1 + random.uniform(-0.35, 0.35)) % 6.28318)
            st.update(zones=zones, zw=zw, cur=0, ang=random.uniform(0, 6.28), dir=1.0, speed=1.5 + 0.12 * self.wave, flash=0.0, done=[False] * 3)
            st['lab'] = 'ZONAS 0/3'
        else:
            n = min(6, 4 + self.wave // 3)
            wires = [random.choice(tuple(WIRE_COLS)) for _ in range(n)]
            serial = ''.join(random.choice('0123456789') for _ in range(5))
            st.update(wires=wires, serial=serial, cut=[False] * n, ans=self.rd_wire_answer(wires, serial), done=False)
            st['lab'] = 'CABLES'

    @staticmethod
    def rd_wire_answer(wires, serial):
        """Índice del cable a cortar según WIRE_RULES."""
        if wires.count('ROJO') > 1:
            return max(i for i, w in enumerate(wires) if w == 'ROJO')
        if int(serial[-1]) % 2 == 0 and 'AZUL' in wires:
            return wires.index('AZUL')
        if 'AMARILLO' not in wires:
            return 1
        return 0

    def rd_puzzle_key(self, st, key):
        rd = self.rd
        kind = st['kind']
        if kind == 'simon':
            if st['mode'] != 'input' or key not in ARROWS:
                return
            sym = ARROWS[key]
            st['press'], st['press_t'] = sym, 0.25
            i = len(st['inp'])
            if sym == st['seq'][i]:
                st['inp'].append(sym)
                self.audio.play('blip', .6)
                st['prog'] = len(st['inp']) / len(st['seq'])
                st['lab'] = 'SECUENCIA %d/%d' % (len(st['inp']), len(st['seq']))
                if len(st['inp']) == len(st['seq']):
                    self.rd_stage_ok()
            else:
                st['inp'] = []
                st['mode'], st['mt'], st['idx'] = 'show', 1.0, 0
                st['miss'] = 0.5
                st['time'] = max(1.0, st['time'] - 3.0)
                st['prog'], st['lab'] = 0.0, 'SECUENCIA 0/%d' % len(st['seq'])
                self.audio.play('hit', .5)
                self.shake = max(self.shake, 4)
                self.rd_say(SAY_MISS, 'simon', 'warn', 5.0)
        elif kind == 'rhythm':
            if key not in RH_KEYS:
                return
            lane = RH_KEYS[key]
            st['press'][lane] = 0.18
            best = None
            for nt in st['notes']:
                if nt['lane'] == lane and nt['hit'] is None:
                    d = abs(nt['t'] - st['now'])
                    if d <= 0.14 and (best is None or d < best[0]):
                        best = (d, nt)
            if best is None:
                st['combo'] = 0
                return
            d, nt = best
            nt['hit'] = 'perfect' if d <= 0.05 else 'good'
            st['hits'] += 1
            st['combo'] += 1
            st['best'] = max(st['best'], st['combo'])
            if st['combo'] in (10, 20):
                self.say('hacker', random.choice(SAY_COMBO), 'ok', 'right', 470)
            st['judge'], st['judge_t'] = ('¡PERFECTO!' if nt['hit'] == 'perfect' else 'BIEN'), 0.4
            st['prog'] = min(1.0, st['hits'] / st['need'])
            st['lab'] = 'ACIERTOS %d/%d' % (st['hits'], st['need'])
            self.audio.play('blip' if nt['hit'] == 'good' else 'ping', .35)
        elif kind == 'lock':
            if key not in (pygame.K_SPACE, pygame.K_RETURN):
                return
            tgt = st['zones'][st['cur']]
            d = abs((st['ang'] - tgt + math.pi) % (2 * math.pi) - math.pi)
            if d <= st['zw'] / 2:
                st['done'][st['cur']] = True
                st['cur'] += 1
                st['dir'] = -st['dir']
                st['speed'] *= 1.12
                st['flash'] = 0.35
                st['prog'] = st['cur'] / 3.0
                st['lab'] = 'ZONAS %d/3' % st['cur']
                self.audio.play('pickup', .6)
                if st['cur'] >= 3:
                    self.rd_stage_ok()
            else:
                st['time'] = max(1.0, st['time'] - 3.0)
                st['miss'] = 0.4
                self.audio.play('hit', .5)
                self.shake = max(self.shake, 4)
                self.rd_say(SAY_MISS, 'lock', 'warn', 5.0)
        elif kind == 'code':
            if key in NUM_KEYS:
                if len(st['cur']) < 4:
                    st['cur'].append(NUM_KEYS[key])
                    self.audio.play('blip', .4)
            elif key == pygame.K_BACKSPACE:
                if st['cur']:
                    st['cur'].pop()
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and len(st['cur']) == 4:
                g = list(st['cur'])
                exact = sum(1 for a, b in zip(g, st['secret']) if a == b)
                common = sum(min(g.count(c), st['secret'].count(c)) for c in range(6))
                st['guesses'].append((g, exact, common - exact))
                st['cur'] = []
                st['prog'] = exact / 4.0
                st['lab'] = 'INTENTOS %d/%d' % (len(st['guesses']), st['tries'])
                if exact == 4:
                    self.rd_stage_ok()
                elif len(st['guesses']) >= st['tries']:
                    st['time'] = 0.0                                  # sin intentos: se cuenta como fallo
                else:
                    self.audio.play('ping' if exact else 'blip', .4)
                    if exact == 0 and common == 0:
                        self.rd_say(SAY_MISS, 'code', 'info', 8.0)
        else:
            if st['done'] or key not in NUM_KEYS or NUM_KEYS[key] >= len(st['wires']):
                return
            i = NUM_KEYS[key]
            if st['cut'][i]:
                return
            st['cut'][i] = True
            if i == st['ans']:
                st['done'] = True
                st['prog'] = 1.0
                self.rd_stage_ok()
            else:
                st['time'] = max(1.0, st['time'] - 8.0)
                self.hull = max(1.0, self.hull - 2)
                st['miss'] = 0.5
                self.audio.play('hit', .6)
                self.shake = max(self.shake, 6)
                self.rd_say(SAY_MISS, 'wire', 'warn', 4.0)

    def rd_puzzle_update(self, st, dt):
        st['press_t'] = max(0.0, st.get('press_t', 0.0) - dt)
        if st['kind'] == 'rhythm':
            st['now'] += dt
            st['judge_t'] = max(0.0, st['judge_t'] - dt)
            st['press'] = [max(0.0, v - dt) for v in st['press']]
            for nt in st['notes']:
                if nt['hit'] is None and st['now'] - nt['t'] > 0.14:
                    nt['hit'] = 'miss'
                    st['combo'] = 0
                    st['judge'], st['judge_t'] = 'FALLO', 0.4
                    st['time'] = max(1.0, st['time'] - 0.8)
            if st['now'] >= st['end']:
                if st['hits'] >= st['need']:
                    self.rd_stage_ok()
                else:
                    st['time'] = 0.0                                   # no llegó al mínimo: se cuenta como fallo
                    self.audio.play('hit', .5)
            return
        if st['kind'] == 'lock':
            st['ang'] = (st['ang'] + st['dir'] * st['speed'] * dt) % (2 * math.pi)
            st['flash'] = max(0.0, st['flash'] - dt)
            st['miss'] = max(0.0, st.get('miss', 0.0) - dt)
            return
        if st['kind'] == 'simon' and st['mode'] == 'show':
            st['mt'] -= dt
            if st['mt'] <= 0:
                if st['lit'] is None:                              # enciende el siguiente símbolo
                    if st['idx'] >= len(st['seq']):
                        st['mode'], st['lit'] = 'input', None
                        return
                    st['lit'] = st['seq'][st['idx']]
                    st['mt'] = max(0.3, 0.55 - 0.02 * self.wave)
                    self.audio.play('ping', .3)
                else:                                              # lo apaga y deja un respiro
                    st['lit'] = None
                    st['idx'] += 1
                    st['mt'] = 0.2

    def rd_draw_sym(self, cv, kind, cx, cy, r, col):
        if kind == 0:
            pygame.draw.circle(cv, col, (cx, cy), r)
        elif kind == 1:
            pygame.draw.rect(cv, col, (cx - r, cy - r, 2 * r, 2 * r))
        elif kind == 2:
            pygame.draw.polygon(cv, col, [(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)])
        elif kind == 3:
            pygame.draw.polygon(cv, col, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])
        elif kind == 4:
            pygame.draw.polygon(cv, col, [(cx + math.cos(math.radians(60 * i)) * r, cy + math.sin(math.radians(60 * i)) * r) for i in range(6)])
        else:
            pygame.draw.rect(cv, col, (cx - r, cy - r // 3, 2 * r, 2 * r // 3))
            pygame.draw.rect(cv, col, (cx - r // 3, cy - r, 2 * r // 3, 2 * r))

    def draw_puzzle(self, cv, st):
        kind = st['kind']
        t = self.t
        if kind == 'simon':
            cx, cy = SCOPE.centerx, SCOPE.centery
            pads = {'U': (0, -78, (0, -1)), 'D': (0, 78, (0, 1)), 'L': (-110, 0, (-1, 0)), 'R': (110, 0, (1, 0))}
            on = st['lit'] if st['mode'] == 'show' else (st['press'] if st['press_t'] > 0 else None)
            for sym, (ox, oy, (dx, dy)) in pads.items():
                x, y = cx + ox, cy + oy
                lit = on == sym
                col = (90, 255, 150) if lit and st['mode'] != 'show' else ((255, 220, 90) if lit else (30, 70, 90))
                pygame.draw.rect(cv, (8, 22, 30), (x - 44, y - 34, 88, 68), border_radius=10)
                pygame.draw.rect(cv, col, (x - 44, y - 34, 88, 68), 4 if lit else 2, border_radius=10)
                if lit:
                    glow(cv, x, y, 70, col, 0.6)
                pygame.draw.polygon(cv, col if lit else (60, 120, 145), [(x + dx * 22 + dy * 0, y + dy * 18 + dx * 0), (x - dx * 14 + dy * 22, y - dy * 14 + dx * 22), (x - dx * 14 - dy * 22, y - dy * 14 - dx * 22)])
            msg = 'MIRÁ LA SECUENCIA...' if st['mode'] == 'show' else 'REPETILA  (%d/%d)' % (len(st['inp']), len(st['seq']))
            self.text(cv, msg, self.f_m, (255, 225, 130) if st['mode'] == 'show' else (130, 255, 190), SCOPE.centerx, SCOPE.y + 14, 'c')
            if st.get('miss', 0) > 0:
                pygame.draw.rect(cv, (255, 70, 70), SCOPE, 4)
        elif kind == 'rhythm':
            lw = 110
            lx0 = SCOPE.centerx - 2 * lw
            line_y = SCOPE.bottom - 52
            top_y = SCOPE.y + 6
            for ln in range(4):
                x = lx0 + ln * lw
                pygame.draw.rect(cv, (8, 22, 30), (x + 3, SCOPE.y + 2, lw - 6, SCOPE.h - 4))
                pygame.draw.rect(cv, (30, 80, 100), (x + 3, SCOPE.y + 2, lw - 6, SCOPE.h - 4), 1)
                pr = st['press'][ln] > 0
                pygame.draw.rect(cv, (255, 235, 130) if pr else (40, 100, 125), (x + 10, line_y - 14, lw - 20, 28), 0 if pr else 2, border_radius=8)
                self.text(cv, 'DFJK'[ln], self.f_s, (10, 20, 30) if pr else (150, 200, 225), x + lw // 2, line_y - 9, 'c')
            for nt in st['notes']:
                y = line_y - (nt['t'] - st['now']) / st['fall'] * (line_y - top_y)
                if y < SCOPE.y - 20 or y > SCOPE.bottom + 10:
                    continue
                x = lx0 + nt['lane'] * lw + lw // 2
                if nt['hit'] in ('perfect', 'good'):
                    continue
                col = (255, 90, 90) if nt['hit'] == 'miss' else (110, 235, 255)
                pygame.draw.rect(cv, col, (x - 38, y - 10, 76, 20), border_radius=6)
                pygame.draw.rect(cv, (255, 255, 255), (x - 38, y - 10, 76, 20), 2, border_radius=6)
            if st['judge_t'] > 0:
                jc = (255, 230, 120) if st['judge'] == '¡PERFECTO!' else ((130, 255, 190) if st['judge'] == 'BIEN' else (255, 100, 100))
                self.text(cv, st['judge'], self.f_l, jc, SCOPE.centerx, SCOPE.centery - 30, 'c', alpha=int(255 * min(1.0, st['judge_t'] / 0.25)))
            if st['combo'] >= 3:
                self.text(cv, 'RACHA %d' % st['combo'], self.f_m, (255, 225, 130), SCOPE.right - 10, SCOPE.y + 8, 'r')
        elif kind == 'lock':
            cx, cy, R = SCOPE.centerx, SCOPE.centery, 118
            pygame.draw.circle(cv, (8, 22, 30), (cx, cy), R + 22)
            pygame.draw.circle(cv, (40, 110, 130), (cx, cy), R + 22, 3)
            pygame.draw.circle(cv, (24, 60, 76), (cx, cy), R, 2)
            for i, zc in enumerate(st['zones']):
                cur = i == st['cur']
                done = st['done'][i]
                col = (90, 255, 150) if done else ((255, 225, 90) if cur else (60, 110, 130))
                pts = [(cx + math.cos(zc + (k / 12 - 0.5) * st['zw']) * (R + 16), cy + math.sin(zc + (k / 12 - 0.5) * st['zw']) * (R + 16)) for k in range(13)]
                pts += [(cx + math.cos(zc + (k / 12 - 0.5) * st['zw']) * (R - 16), cy + math.sin(zc + (k / 12 - 0.5) * st['zw']) * (R - 16)) for k in range(12, -1, -1)]
                pygame.draw.polygon(cv, col, pts)
                if cur and not done:
                    glow(cv, cx + math.cos(zc) * R, cy + math.sin(zc) * R, 46, col, 0.6)
                self.text(cv, str(i + 1), self.f_m, (10, 20, 30) if (cur or done) else (170, 200, 220), cx + math.cos(zc) * (R - 36) - 6, cy + math.sin(zc) * (R - 36) - 12)
            a = st['ang']
            pygame.draw.line(cv, (255, 245, 170), (cx, cy), (cx + math.cos(a) * (R + 20), cy + math.sin(a) * (R + 20)), 5)
            pygame.draw.circle(cv, (255, 245, 170), (cx, cy), 9)
            glow(cv, cx + math.cos(a) * R, cy + math.sin(a) * R, 36, (255, 230, 120), 0.5)
            self.text(cv, 'ZONA %d/3' % min(3, st['cur'] + 1), self.f_m, (255, 225, 130), cx, cy - 74, 'c')
            if st['flash'] > 0:
                pygame.draw.rect(cv, (90, 255, 150), SCOPE, 4)
            if st.get('miss', 0) > 0:
                pygame.draw.rect(cv, (255, 70, 70), SCOPE, 4)
        elif kind == 'code':
            x0, y0 = SCOPE.x + 20, SCOPE.y + 8
            self.text(cv, 'CLAVE DE 4 SÍMBOLOS (sin repetir)', self.f_s, (150, 190, 220), x0, y0)
            rows = st['guesses'] + [None]
            for ri in range(st['tries']):
                y = y0 + 26 + ri * 37
                cur = ri == len(st['guesses'])
                pygame.draw.rect(cv, (10, 34, 46) if cur else (8, 22, 30), (x0, y - 2, 330, 34), border_radius=6)
                if cur:
                    pygame.draw.rect(cv, (255, 220, 100), (x0, y - 2, 330, 34), 2, border_radius=6)
                row = st['guesses'][ri] if ri < len(st['guesses']) else None
                glyphs = row[0] if row else (st['cur'] if cur else [])
                for k in range(4):
                    sx = x0 + 28 + k * 50
                    pygame.draw.rect(cv, (24, 52, 66), (sx - 16, y + 1, 32, 28), 1)
                    if k < len(glyphs):
                        self.rd_draw_sym(cv, glyphs[k], sx, y + 15, 11, SYMS[glyphs[k]])
                if row:
                    for k in range(4):
                        col = (90, 255, 150) if k < row[1] else ((255, 210, 80) if k < row[1] + row[2] else (50, 70, 84))
                        pygame.draw.circle(cv, col, (x0 + 245 + k * 22, y + 15), 7)
            # paleta de símbolos
            px, py = SCOPE.x + 400, SCOPE.y + 40
            self.text(cv, 'SÍMBOLOS', self.f_s, (150, 190, 220), px, py - 28)
            for i in range(6):
                sx, sy = px + (i % 3) * 82 + 30, py + (i // 3) * 80 + 30
                pygame.draw.rect(cv, (8, 22, 30), (sx - 32, sy - 32, 64, 64), border_radius=8)
                pygame.draw.rect(cv, (50, 100, 125), (sx - 32, sy - 32, 64, 64), 2, border_radius=8)
                self.rd_draw_sym(cv, i, sx, sy - 4, 15, SYMS[i])
                self.text(cv, str(i + 1), self.f_s, (200, 225, 250), sx, sy + 12, 'c')
            self.text(cv, 'verde: en su lugar', self.f_s, (90, 255, 150), px, py + 150)
            self.text(cv, 'amarillo: otro lugar', self.f_s, (255, 210, 80), px, py + 168)
        else:
            x0, y0 = SCOPE.x + 20, SCOPE.y + 14
            n = len(st['wires'])
            gap = min(42, (SCOPE.h - 40) // n)
            L = 165                                                      # largo de cada cable
            for i, w in enumerate(st['wires']):
                y = y0 + 12 + i * gap
                col = WIRE_COLS[w]
                self.text(cv, str(i + 1), self.f_m, (200, 225, 250), x0, y - 12)
                pygame.draw.circle(cv, (40, 60, 70), (x0 + 40, y), 8)
                pygame.draw.circle(cv, (40, 60, 70), (x0 + 40 + L, y), 8)
                if st['cut'][i]:
                    ok = i == st['ans']
                    pygame.draw.line(cv, col, (x0 + 40, y), (x0 + 40 + L // 2 - 22, y + (4 if ok else 9)), 6)
                    pygame.draw.line(cv, col, (x0 + 40 + L, y), (x0 + 40 + L // 2 + 22, y + (5 if ok else -9)), 6)
                    if ok:
                        glow(cv, x0 + 40 + L // 2, y, 40, (120, 255, 170), 0.7)
                else:
                    pygame.draw.line(cv, tuple(int(c * 0.4) for c in col), (x0 + 40, y), (x0 + 40 + L, y), 11)
                    pygame.draw.line(cv, col, (x0 + 40, y - 1), (x0 + 40 + L, y - 1), 6)
                self.text(cv, w, self.f_s, tuple(int(c * 0.85) for c in col), x0 + 40 + L + 18, y - 9)
            rx = SCOPE.x + 372
            self.text(cv, 'SERIE:', self.f_s, (150, 190, 220), rx, y0 - 4)
            self.text(cv, st['serial'], self.f_l, (255, 225, 130), rx + 110, y0 - 12)
            self.text(cv, 'REGLAS (en este orden)', self.f_s, (150, 190, 220), rx, y0 + 34)
            yy = y0 + 58
            for rule in WIRE_RULES:
                line = ''
                for word in rule.split():
                    probe = (line + ' ' + word).strip()
                    if self.f_s.size(probe)[0] > SCOPE.right - rx - 20:
                        self.text(cv, line, self.f_s, (200, 225, 250), rx, yy)
                        yy += 20
                        line = word
                    else:
                        line = probe
                self.text(cv, line, self.f_s, (200, 225, 250), rx, yy)
                yy += 30
            if st.get('miss', 0) > 0:
                pygame.draw.rect(cv, (255, 70, 70), SCOPE, 4)

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
