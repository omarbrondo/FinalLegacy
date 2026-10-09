"""Comunicaciones: un personaje (busto) entra por un costado de la pantalla, dice su mensaje en un globo de cómic y se va por el mismo costado.
Los bustos salen de portraits/<personaje>.png (y portraits/<personaje>_<ánimo>.png si existe); si falta la imagen se dibuja una silueta provisoria."""
import math
import os
import random
import re
import pygame
from .common import H, W, clamp

PW, PH = 112, 137                     # tamaño máximo de la viñeta del personaje (el ancho se ajusta a la imagen)
_PW0, _PH0 = 150, 176                 # tamaño con el que se dibujan las siluetas provisorias (después se reducen)
CROP_TOP = {'secretaria': 0.08}      # fracción del alto de la imagen que se omite arriba al mostrar el busto (por personaje)
BW = 340                              # ancho máximo del globo
ENTER, HOLD_MIN, EXIT, GAP = 0.5, 1.8, 0.45, 0.12
TYPE_CPS = 42.0                       # caracteres por segundo del texto
MOOD_COL = {'info': (90, 160, 240), 'ok': (70, 200, 130), 'warn': (240, 180, 60), 'bad': (230, 80, 70)}
ROLES = {
    'hacker': dict(name='HACKER', col=(60, 220, 160), skin=(214, 176, 140), hat=(26, 30, 40), body=(40, 48, 60), kind='hood', side='left'),
    'piloto': dict(name='PILOTO', col=(110, 180, 255), skin=(220, 180, 146), hat=(70, 90, 120), body=(80, 92, 70), kind='visor', side='right'),
    'marinero': dict(name='MARINERO', col=(100, 170, 230), skin=(216, 172, 138), hat=(236, 238, 244), body=(40, 70, 120), kind='cap', side='left'),
    'tanquista': dict(name='TANQUISTA', col=(210, 170, 80), skin=(212, 168, 132), hat=(84, 90, 62), body=(92, 86, 60), kind='helmet', side='right'),
    'soldado': dict(name='SOLDADO', col=(130, 200, 120), skin=(214, 170, 134), hat=(72, 92, 60), body=(66, 86, 60), kind='helmet', side='left'),
    'comandante': dict(name='COMANDANTE', col=(240, 200, 90), skin=(206, 160, 126), hat=(30, 40, 70), body=(34, 44, 74), kind='cap', side='right'),
    'secretaria': dict(name='SECRETARÍA', col=(190, 160, 255), skin=(228, 186, 156), hat=(60, 44, 70), body=(52, 56, 88), kind='cap', side='right'),
    'jefe_barco': dict(name='JEFE', col=(255, 90, 80), skin=(196, 150, 118), hat=(70, 20, 24), body=(80, 28, 32), kind='cap', side='right'),
    'jefe_avion': dict(name='JEFE', col=(255, 130, 70), skin=(206, 160, 126), hat=(60, 62, 72), body=(70, 72, 84), kind='helmet', side='left'),
    'jefe_puerto_tanque': dict(name='JEFE', col=(255, 100, 70), skin=(190, 146, 112), hat=(74, 64, 40), body=(86, 76, 48), kind='helmet', side='right'),
    'jefe_puerto_heli': dict(name='JEFE', col=(255, 100, 70), skin=(200, 154, 120), hat=(40, 56, 74), body=(48, 66, 86), kind='helmet', side='right'),
    'artillero': dict(name='ARTILLERO', col=(255, 150, 70), skin=(204, 158, 122), hat=(150, 90, 40), body=(120, 84, 50), kind='helmet', side='left'),
    'soldada': dict(name='SOLDADO', col=(130, 200, 120), skin=(222, 180, 148), hat=(72, 92, 60), body=(66, 86, 60), kind='helmet', side='left'),
    'ramos': dict(name='RAMOS', col=(120, 190, 255), skin=(210, 166, 130), hat=(74, 96, 84), body=(70, 100, 90), kind='helmet', side='left'),
    'diaz': dict(name='DÍAZ', col=(240, 190, 100), skin=(196, 150, 114), hat=(120, 104, 70), body=(130, 112, 74), kind='helmet', side='left'),
    'luna': dict(name='LUNA', col=(250, 130, 170), skin=(226, 182, 150), hat=(90, 80, 100), body=(84, 74, 96), kind='helmet', side='left'),
}
# cómo se elige cuál de las imágenes de cada oficio habla: 'mission' = una por misión (se mantiene hasta volver al mapa),
# 'random' = al azar en cada mensaje (sin repetir la anterior); el resto usa siempre la primera
POLICY = {'hacker': 'mission', 'piloto': 'mission', 'marinero': 'random', 'tanquista': 'random', 'artillero': 'random', 'secretaria': 'random'}
MULTI = ('hacker', 'piloto', 'marinero', 'tanquista', 'artillero', 'secretaria')
BOSS_VARIANTS = {'jefe_barco': 6, 'jefe_avion': 6, 'jefe_puerto_tanque': 2, 'jefe_puerto_heli': 2}               # un personaje por oleada (se pasa v= al hablar)       # oficios con varias imágenes (o 3 siluetas provisorias)
FILE_RE = re.compile(r'^([a-z_]+?)(?:_(\d+))?(?:_(info|ok|warn|bad))?\.png$')
LANE_Y = 440


def _wrap(font, text, maxw):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if font.size(t)[0] <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _placeholder(role, v=1):
    """Busto provisorio con el uniforme del oficio (se reemplaza al subir portraits/<personaje>_<n>.png). La variante v cambia rasgos."""
    r = dict(ROLES[role])
    r['skin'] = [r['skin'], tuple(int(c * 0.82) for c in r['skin']), tuple(min(255, int(c * 1.08)) for c in r['skin'])][(v - 1) % 3]
    r['hat'] = tuple(max(0, min(255, int(c * f))) for c, f in zip(r['hat'], ((1, 1, 1), (0.78, 0.78, 0.78), (1.22, 1.22, 1.22))[(v - 1) % 3]))
    s = pygame.Surface((_PW0, _PH0), pygame.SRCALPHA)
    cx = _PW0 // 2
    pygame.draw.polygon(s, r['body'], [(cx - 62, _PH0), (cx - 54, _PH0 - 54), (cx - 20, _PH0 - 66), (cx + 20, _PH0 - 66), (cx + 54, _PH0 - 54), (cx + 62, _PH0)])
    pygame.draw.polygon(s, tuple(min(255, c + 30) for c in r['body']), [(cx - 20, _PH0 - 66), (cx, _PH0 - 44), (cx + 20, _PH0 - 66)])
    pygame.draw.rect(s, r['skin'], (cx - 9, _PH0 - 80, 18, 18), border_radius=4)
    pygame.draw.ellipse(s, r['skin'], (cx - 27, 40, 54, 70))
    kind = r['kind']
    if kind == 'hood':
        pygame.draw.ellipse(s, r['hat'], (cx - 38, 20, 76, 96))
        pygame.draw.ellipse(s, r['skin'], (cx - 24, 44, 48, 62))
        pygame.draw.rect(s, (30, 255, 190), (cx - 22, 66, 44, 11), border_radius=5)
        pygame.draw.rect(s, (8, 40, 30), (cx - 22, 66, 44, 11), 2, border_radius=5)
    elif kind == 'visor':
        pygame.draw.ellipse(s, r['hat'], (cx - 34, 22, 68, 62))
        pygame.draw.rect(s, (255, 200, 80), (cx - 28, 58, 56, 20), border_radius=9)
        pygame.draw.rect(s, (60, 40, 10), (cx - 28, 58, 56, 20), 2, border_radius=9)
    elif kind == 'cap':
        pygame.draw.rect(s, r['hat'], (cx - 30, 28, 60, 20), border_radius=8)
        pygame.draw.rect(s, tuple(max(0, c - 40) for c in r['hat']), (cx - 36, 46, 72, 8), border_radius=3)
        pygame.draw.circle(s, (230, 190, 70), (cx, 38), 5)
    else:
        pygame.draw.ellipse(s, r['hat'], (cx - 33, 24, 66, 52))
        pygame.draw.rect(s, tuple(max(0, c - 40) for c in r['hat']), (cx - 34, 56, 68, 10), border_radius=3)
    if kind != 'hood':
        pygame.draw.circle(s, (30, 30, 36), (cx - 10, 80), 3)
        pygame.draw.circle(s, (30, 30, 36), (cx + 10, 80), 3)
    pygame.draw.arc(s, (120, 60, 50), (cx - 9, 92, 18, 10), 3.5, 5.9, 2)
    if v % 3 == 2 and kind != 'hood':                                       # anteojos
        pygame.draw.circle(s, (20, 20, 26), (cx - 10, 80), 7, 2)
        pygame.draw.circle(s, (20, 20, 26), (cx + 10, 80), 7, 2)
        pygame.draw.line(s, (20, 20, 26), (cx - 3, 80), (cx + 3, 80), 2)
    elif v % 3 == 0:                                                         # bigote
        pygame.draw.rect(s, (50, 36, 30), (cx - 10, 90, 20, 4), border_radius=2)
    return pygame.transform.smoothscale(s, (PW, PH))


class CommsMixin:
    def comms_reset(self):
        self.cm = dict(queue=[], cur=None, last=('', -9.0), mission={}, lastv={}, st=None, end=-99.0)
        self._cm_img = getattr(self, '_cm_img', {})
        self._cm_files = None
        self.chat_init()
        self.board_init()

    def comms_files(self):
        """Imágenes disponibles en portraits/: {personaje: {variante: {ánimo o '': ruta}}}."""
        if self._cm_files is None:
            found = {}
            base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'portraits')
            try:
                names = os.listdir(base)
            except OSError:
                names = []
            for fn in names:
                m = FILE_RE.match(fn.lower())
                if m and m.group(1) in ROLES:
                    found.setdefault(m.group(1), {}).setdefault(int(m.group(2) or 1), {})[m.group(3) or ''] = os.path.join(base, fn)
            self._cm_files = found
        return self._cm_files

    def comms_variants(self, who):
        found = self.comms_files().get(who)
        if found:
            return sorted(found)
        return list(range(1, BOSS_VARIANTS.get(who, 3 if who in MULTI else 1) + 1))

    def comms_pick(self, who):
        """Elige qué imagen del oficio habla: una por misión (hacker, piloto) o al azar sin repetir (marinero, tanquista)."""
        cm = self.cm
        vs = self.comms_variants(who)
        pol = POLICY.get(who)
        if pol == 'mission':
            if who not in cm['mission']:
                cm['mission'][who] = random.choice(vs)
            return cm['mission'][who]
        if pol == 'random' and len(vs) > 1:
            v = random.choice([x for x in vs if x != cm['lastv'].get(who)] or vs)
            cm['lastv'][who] = v
            return v
        return vs[0]

    def comms_image(self, who, v, mood):
        key = (who, v, mood)
        img = self._cm_img.get(key)
        if img is None:
            moods = self.comms_files().get(who, {}).get(v, {})
            for path in (moods.get(mood), moods.get('')):
                if path:
                    try:
                        raw = pygame.image.load(path).convert_alpha()
                        bb = pygame.mask.from_surface(raw, 24).get_bounding_rects()                # se recortan los márgenes transparentes de la imagen
                        if bb:
                            box = bb[0].unionall(bb[1:]) if len(bb) > 1 else bb[0]
                            raw = raw.subsurface(box).copy()
                        if raw.get_height() > 1.22 * raw.get_width():                                # imágenes muy altas: se muestra el busto (parte de arriba) para que llenen el recuadro sin bandas
                            y0 = int(CROP_TOP.get(who, 0.0) * raw.get_height())                    # algunos retratos tienen la cabeza más abajo: se salta parte del borde de arriba
                            hh = int(1.22 * raw.get_width())
                            raw = raw.subsurface((0, min(y0, raw.get_height() - hh), raw.get_width(), hh)).copy()
                        k = min(PW / raw.get_width(), PH / raw.get_height())
                        img = pygame.transform.smoothscale(raw, (max(1, int(raw.get_width() * k)), max(1, int(raw.get_height() * k))))
                        break
                    except pygame.error:
                        img = None
            if img is None:
                img = _placeholder(who, v).convert_alpha()
            self._cm_img[key] = img
        return img

    def say(self, who, text, mood='info', side=None, y=None, v=None, name=None, pose=None, urgent=False):
        """pose: ánimo de la imagen si difiere del color del globo ('' = imagen normal)."""
        """Un personaje comunica algo: aparece por un costado, lo dice en un globo y se retira por el mismo costado."""
        cm = self.cm
        if who not in ROLES:
            who = 'comandante'
        if who == 'soldado':                                                       # el soldado habla con el sexo del protagonista de la batalla
            fem = (getattr(self, 'pt', None) or {}).get('pfem') if self.state == 'port' else (getattr(self, 'g', None) or {}).get('pfem')
            who = 'soldada' if fem else 'soldado'
        if (cm['cur'] and cm['cur']['text'] == text) or any(q['text'] == text for q in cm['queue']):
            return
        prio = 2 if urgent else (1 if mood in ('bad', 'warn') else 0)              # urgente > aviso (peligro) > información
        item = dict(who=who, v=v if v is not None else self.comms_pick(who), name=name, pose=mood if pose is None else pose, text=text, mood=mood, side=side or ROLES[who]['side'], y=LANE_Y if y is None else y,
                    prio=prio, born=self.t)
        cur = cm['cur']
        if prio > 0 and cur is not None and prio > cur.get('prio', 0):               # algo más importante: corta de golpe el globo actual y pasa primero
            cm['cur'] = None
            cm['queue'] = [q for q in cm['queue'] if q.get('prio', 0) >= prio]
            cm['queue'].insert(0, item)
            return
        i = next((j for j, q in enumerate(cm['queue']) if q.get('prio', 0) < prio), len(cm['queue']))
        cm['queue'].insert(i, item)
        while len(cm['queue']) > 4:                                                  # demasiados pendientes: se descarta el más viejo de menor importancia
            lo = min(q.get('prio', 0) for q in cm['queue'])
            cm['queue'].pop(next(j for j, q in enumerate(cm['queue']) if q.get('prio', 0) == lo))

    def comms_cut_old(self):
        """Cambio de modo: se corta el globo que se estaba mostrando y se descartan los pendientes (salvo los dichos en este mismo instante)."""
        cm = self.cm
        now = self.t
        if cm['cur'] is not None and now - cm['cur'].get('born', -9.0) > 0.05:
            cm['cur'] = None
        cm['queue'] = [q for q in cm['queue'] if now - q.get('born', -9.0) <= 0.05]

    def comms_purge(self):
        """Descarta los globos pendientes y el que se está mostrando (al cambiar de pantalla, para que no aparezcan mensajes viejos)."""
        self.cm['queue'].clear()
        self.cm['cur'] = None

    def comms_update(self, dt):
        cm = self.cm
        if self.paused:                                                            # en pausa los globos se congelan (y no se dibujan)
            return
        if self.state != cm['st']:                                                 # al volver al mapa termina la misión: se sortean otros pilotos y hackers
            cm['st'] = self.state
            if self.state in ('map', 'title'):
                cm['mission'].clear()
        c = cm['cur']
        if c is None:
            if cm['queue']:
                q = cm['queue'].pop(0)
                font = self.cm_font()
                lines = _wrap(font, q['text'], BW - 36)
                total = sum(len(l) for l in lines)
                q.update(t=0.0, lines=lines, total=total, hold=max(HOLD_MIN, total / TYPE_CPS + 1.5))
                cm['cur'] = q
                self.audio.play('blip', .35)
            return
        c['t'] += dt
        if c['t'] > ENTER + c['hold'] + EXIT + GAP:
            cm['cur'] = None
            cm['end'] = self.t

    def cm_font(self):
        """Fuente monoespañada de los globos (estilo terminal); si falta el archivo se usa la del juego."""
        f = getattr(self, '_cm_font', None)
        if f is None:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts', 'DejaVuSansMono-Bold.ttf')
            try:
                f = pygame.font.Font(path, 17)
            except Exception:
                f = self.f_m
            self._cm_font = f
        return f

    def comms_draw(self, cv):
        c = self.cm['cur']
        if c is None or self.paused:
            return
        t = c['t']
        r = ROLES[c['who']]
        left = c['side'] == 'left'
        if t < ENTER:                                                      # entra con un pequeño rebote
            k = t / ENTER
            e = 1 + 2.4 * (k - 1) ** 3 + 1.4 * (k - 1) ** 2
            off = (1 - e)
        elif t < ENTER + c['hold']:
            off = 0.0
        else:
            k = clamp((t - ENTER - c['hold']) / EXIT, 0, 1)
            off = k * k
        img = self.comms_image(c['who'], c['v'], c['pose'])
        pw = img.get_width()
        ph = img.get_height()                                      # el recuadro se ajusta al ancho de la imagen: sin bandas de relleno a los costados
        x = 14 - off * (pw + 40) if left else W - 14 - pw + off * (pw + 40)
        y = int(c['y'] - ph / 2)
        col = MOOD_COL.get(c['mood'], MOOD_COL['info'])
        # viñeta del personaje
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        for yy in range(ph):
            kk = yy / ph
            pygame.draw.line(panel, (int(r['col'][0] * (0.22 + 0.2 * kk)), int(r['col'][1] * (0.22 + 0.2 * kk)), int(r['col'][2] * (0.3 + 0.2 * kk)), 255), (0, yy), (pw, yy))
        for i in range(0, ph, 7):                                          # trama de semitono estilo cómic
            pygame.draw.line(panel, (255, 255, 255, 14), (0, i), (pw, i - 14), 1)
        bob = math.sin(self.t * 3.0) * 1.5
        panel.blit(img, ((pw - img.get_width()) // 2, int(ph - img.get_height() + bob)))
        out = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(out, (255, 255, 255, 255), (0, 0, pw, ph), border_radius=10)
        panel.blit(out, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        shadow = pygame.Surface((pw + 10, ph + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), (0, 0, pw + 10, ph + 10), border_radius=12)
        cv.blit(shadow, (x + 4, y + 6))
        cv.blit(panel, (x, y))
        pygame.draw.rect(cv, (12, 14, 22), (x - 2, y - 2, pw + 4, ph + 4), 4, border_radius=11)
        pygame.draw.rect(cv, col, (x, y, pw, ph), 2, border_radius=10)
        tag = pygame.Surface((pw, 22), pygame.SRCALPHA)
        pygame.draw.rect(tag, (10, 12, 20, 210), (0, 0, pw, 22), border_bottom_left_radius=10, border_bottom_right_radius=10)
        cv.blit(tag, (x, y + ph - 22))
        nm = c.get('name') or r['name']
        if self.f_s.size(nm)[0] <= pw - 10:
            self.text(cv, nm, self.f_s, col, x + pw // 2, y + ph - 20, 'c', shadow=False)
        else:                                                              # nombres largos (COMANDANTE STEALTH): se achican para entrar en la etiqueta
            ts = self.f_s.render(nm, True, col)
            k = (pw - 10) / ts.get_width()
            ts = pygame.transform.smoothscale(ts, (pw - 10, max(1, int(ts.get_height() * k))))
            cv.blit(ts, (x + 5, y + ph - 20 + (self.f_s.get_height() - ts.get_height()) // 2))
        # globo
        bt = t - ENTER * 0.7
        if bt <= 0 or t > ENTER + c['hold']:
            return
        pop = clamp(bt / 0.18, 0, 1)
        shown = int(clamp((t - ENTER) * TYPE_CPS, 0, c['total']))
        fm = self.cm_font()
        lh = fm.get_height() + 2
        bw = max(fm.size(l)[0] for l in c['lines']) + 36
        bh = len(c['lines']) * lh + 24
        bx = x + pw + 16 if left else x - 16 - bw
        by = y + 14
        bub = pygame.Surface((bw + 24, bh + 12), pygame.SRCALPHA)
        ox = 12
        pygame.draw.rect(bub, (12, 14, 22), (ox - 3, 3, bw + 6, bh + 6), border_radius=16)
        pygame.draw.rect(bub, (250, 251, 255), (ox, 6, bw, bh), border_radius=14)
        pygame.draw.rect(bub, col, (ox, 6, bw, bh), 3, border_radius=14)
        tipy = 6 + 30
        if left:
            pts = [(ox, tipy - 10), (ox - 14, tipy), (ox, tipy + 10)]
        else:
            pts = [(ox + bw, tipy - 10), (ox + bw + 14, tipy), (ox + bw, tipy + 10)]
        pygame.draw.polygon(bub, (250, 251, 255), pts)
        pygame.draw.lines(bub, col, False, pts, 3)
        n = shown
        for i, line in enumerate(c['lines']):
            seg = line[:max(0, n)]
            n -= len(line)
            if seg:
                img_t = fm.render(seg, True, (22, 26, 40))
                bub.blit(img_t, (ox + 18, 6 + 12 + i * lh))
        if pop < 1:
            s2 = pygame.transform.smoothscale(bub, (max(1, int(bub.get_width() * pop)), max(1, int(bub.get_height() * pop))))
            px = bx - ox if left else bx - ox + (bub.get_width() - s2.get_width())
            cv.blit(s2, (px, by - 6 + (bub.get_height() - s2.get_height()) // 2))
        else:
            cv.blit(bub, (bx - ox, by - 6))


# frases de los jefes: (al aparecer, al ser derrotado); el índice es la oleada (1 a 6)
BOSS_LINES = (
    ('Soy LEVIATAN. Ningún buque pasa por mis aguas.', 'Mi casco... se hunde... imposible.'),
    ('TIFÓN ha llegado. Rece lo que sepa, capitán.', 'La tormenta... se apaga...'),
    ('Soy COLOSO. Su flota no es más que chatarra.', 'Un gigante... caído por un simple barco.'),
    ('ABISMO lo espera. Nadie vuelve de las profundidades.', 'Las profundidades... me reclaman...'),
    ('Soy TITÁN. Se atrevió a desafiarme. Error fatal.', 'Titán... derrotado... no puede ser.'),
    ('APOCALIPSIS ha llegado. Este es su final, capitán.', 'Ganaron... esta vez. Pero esto no termina.'),
)
AIR_LINES = (
    ('Comandante Stealth al mando. No me verá venir.', 'Me detectaron... maldición.'),
    ('Soy la Nodriza Tifón. Mis drones lo cazarán.', 'Mis drones... todos perdidos...'),
    ('Soy el Fantasma. No se puede matar lo que no se ve.', 'Me alcanzó... incluso un fantasma cae.'),
    ('Artillero Pesado en posición. Prepárese para el bombardeo.', 'Mis bombas... se acabaron.'),
    ('Soy la Tormenta. Caerá un rayo sobre usted.', 'La tormenta... se disipa...'),
    ('Titán Aéreo al ataque. El cielo es mío.', 'Titán cae... el cielo ya no es mío.'),
)
PORT_LINES = {
    'heli': ('Desde el aire no tienen escapatoria. ¡Abran fuego!', '¡Me derribaron! ¡Mayday!'),
    'tank': ('Este puerto es nuestro. Será aplastado.', 'Mi tanque... destruido. Retirada...'),
}

