"""Efectos compartidos de las pantallas de hackeo: lluvia Matrix, marco de terminal, sellos, arranque y descifrado."""
import math
import random
import pygame
from .common import H, W, clamp

TINTS = {'green': (30, 255, 110), 'red': (255, 55, 55), 'cyan': (70, 225, 255)}
LEVELS = (0.22, 0.42, 0.72, 1.0)          # cola tenue -> cabeza
LAYERS = ((7, 10, 0.6, 12, 0.6), (10, 14, 0.85, 17, 0.45), (14, 19, 1.0, 24, 0.30))   # ancho, alto, brillo, paso x, densidad
SCRAMBLE = '#%&$@?01<>/\\|+=*'


def _make_glyphs(n=26):
    rnd = random.Random(77)
    pts = [(x, y) for x in range(3) for y in range(4)]
    out = []
    for _ in range(n):
        segs = []
        p = rnd.choice(pts)
        for _ in range(rnd.randint(3, 5)):
            q = rnd.choice(pts)
            if q != p:
                segs.append((p, q))
            p = q if rnd.random() < .6 else rnd.choice(pts)
        out.append(('s', segs))
    out += [('0', None), ('1', None), ('0', None), ('1', None)]
    return out


class HackFxMixin:
    def fx_init(self):
        self.hfx = dict(glyphs=_make_glyphs(), cache={}, cols=None, last=self.t, pulse=None, until=0.0, dimsurf={}, bright=1.0)
        cols = []
        for li, (gw, gh, br, step, dens) in enumerate(LAYERS):
            for x in range(0, W, step):
                if random.random() < dens:
                    cols.append(self.fx_col(li, x, True))
        self.hfx['cols'] = cols

    def fx_col(self, li, x, first=False):
        gw, gh, br, step, dens = LAYERS[li]
        return dict(l=li, x=x + random.randint(0, 3), y=random.uniform(-H, H) if first else random.uniform(-300, 0),
                    sp=random.uniform(55, 150) * (0.55 + 0.5 * li), n=random.randint(9, 20), s=random.randrange(1000))

    def fx_glyph(self, li, gi, lv, tint):
        key = (li, gi, lv, tint)
        c = self.hfx['cache'].get(key)
        if c is None:
            gw, gh, br, step, dens = LAYERS[li]
            col = TINTS[tint]
            f = LEVELS[lv] * br
            if lv == 3:
                col = tuple(min(255, int(v * .45 + 150)) for v in col)
            rgb = tuple(int(v * f) for v in col)
            c = pygame.Surface((gw, gh))
            kind, segs = self.hfx['glyphs'][gi]
            lw = 2 if li == 2 else 1
            if kind == 's':
                for (a, b) in segs:
                    pa = (a[0] * (gw - 1) // 2, a[1] * (gh - 1) // 3)
                    pb = (b[0] * (gw - 1) // 2, b[1] * (gh - 1) // 3)
                    pygame.draw.line(c, rgb, pa, pb, lw)
            elif kind == '0':
                pygame.draw.ellipse(c, rgb, (0, 0, gw, gh), lw)
            else:
                pygame.draw.line(c, rgb, (gw // 2, 0), (gw // 2, gh - 1), lw)
                pygame.draw.line(c, rgb, (gw // 2, 0), (max(0, gw // 2 - 3), 3), lw)
            c.set_colorkey((0, 0, 0))
            self.hfx['cache'][key] = c
        return c

    def fx_pulse(self, tint, secs=0.7):
        if not hasattr(self, 'hfx'):
            self.fx_init()
        self.hfx['pulse'], self.hfx['until'] = tint, self.t + secs

    def fx_rain(self, cv, tint='green', speed=1.0, dim=165, bg=(3, 8, 12)):
        """Lluvia Matrix de 3 capas con cabeza brillante; `tint` y `speed` reaccionan al juego."""
        if not hasattr(self, 'hfx'):
            self.fx_init()
        hf = self.hfx
        t = self.t
        dt = clamp(t - hf['last'], 0.0, 0.05)
        hf['last'] = t
        if t < hf['until']:
            tint, speed = hf['pulse'], speed * 1.7
        cv.fill(bg)
        ng = len(hf['glyphs'])
        for c in hf['cols']:
            gw, gh, br, step, dens = LAYERS[c['l']]
            c['y'] += c['sp'] * speed * dt
            sh = gh + 3
            if c['y'] - c['n'] * sh > H:
                c.update(self.fx_col(c['l'], c['x'] - 3))
                c['x'] = c['x']
                continue
            for j in range(c['n']):
                yy = int(c['y'] - j * sh)
                if yy < -gh or yy >= H:
                    continue
                lv = 3 if j == 0 else (2 if j < 3 else (1 if j < c['n'] * .6 else 0))
                gi = (c['s'] + j * 13 + int(t * 5 + j * .37 + c['s'])) % ng
                cv.blit(self.fx_glyph(c['l'], gi, lv, tint), (c['x'], yy))
        if dim > 0:
            d = hf['dimsurf'].get(dim)
            if d is None:
                d = pygame.Surface((W, H), pygame.SRCALPHA)
                d.fill(bg + (dim,))
                hf['dimsurf'][dim] = d
            cv.blit(d, (0, 0))

    def fx_frame(self, cv, col=(80, 200, 230), ln=38, inset=12):
        a = (*col, )
        dimc = tuple(int(v * .35) for v in col)
        pygame.draw.rect(cv, dimc, (inset, inset, W - 2 * inset, H - 2 * inset), 1)
        for (x, y, sx, sy) in ((inset, inset, 1, 1), (W - inset, inset, -1, 1), (inset, H - inset, 1, -1), (W - inset, H - inset, -1, -1)):
            pygame.draw.line(cv, a, (x, y), (x + sx * ln, y), 3)
            pygame.draw.line(cv, a, (x, y), (x, y + sy * ln), 3)
            pygame.draw.rect(cv, a, (x + sx * 8 - 2, y + sy * 8 - 2, 4, 4))

    def fx_title(self, cv, s, font, col, x, y):
        """Título con falla de señal ocasional (fantasmas rojo/cian)."""
        ph = (self.t % 3.1)
        if ph < 0.16:
            o = random.choice((3, 4, 6))
            self.text(cv, s, font, (255, 60, 90), x + o, y, shadow=False, alpha=150)
            self.text(cv, s, font, (60, 240, 255), x - o, y + 1, shadow=False, alpha=150)
        self.text(cv, s, font, col, x, y)

    def fx_scramble(self, s, k):
        """Texto que se descifra: k 0..1 es la fracción ya revelada."""
        n = int(len(s) * clamp(k, 0, 1))
        return s[:n] + ''.join(ch if ch == ' ' else random.choice(SCRAMBLE) for ch in s[n:])

    def fx_stamp(self, cv, s, col, cy, k=1.0, tilt=-3.0):
        """Sello grande ACCESO CONCEDIDO / DENEGADO que 'cae' al inicio."""
        txt = self.fx_scramble(s, k * 2.2) if k < 0.45 else s
        im = self.f_xl.render(txt, True, col)
        pad = 22
        box = pygame.Surface((im.get_width() + pad * 2, im.get_height() + pad), pygame.SRCALPHA)
        box.fill((*(int(v * .12) for v in col), 190))
        pygame.draw.rect(box, col, box.get_rect(), 4, border_radius=6)
        pygame.draw.rect(box, tuple(int(v * .5) for v in col), box.get_rect().inflate(-12, -12), 1, border_radius=4)
        box.blit(im, (pad, pad // 2))
        sc = 1.0 + max(0.0, 1.0 - k * 4) * 1.4
        box = pygame.transform.rotozoom(box, tilt, sc)
        box.set_alpha(int(255 * clamp(k * 5, 0, 1)))
        cv.blit(box, box.get_rect(center=(W // 2, cy)))

    def fx_boot(self, cv, lines, age, col=(90, 255, 150)):
        """Secuencia de arranque tecleada; devuelve True mientras siga activa."""
        per = 0.36
        dur = per * len(lines) + 0.3
        if age >= dur:
            return False
        d = pygame.Surface((W, H), pygame.SRCALPHA)
        d.fill((2, 6, 8, 215))
        cv.blit(d, (0, 0))
        x, y = W // 2 - 280, H // 2 - 20 * len(lines) // 2 - 10
        for i, ln in enumerate(lines):
            a = age - i * per
            if a < 0:
                break
            n = int(a * 70)
            s = ln[:n]
            self.text(cv, s + ('_' if n < len(ln) or int(self.t * 6) % 2 == 0 else ''), self.f_m, col, x, y + i * 30, shadow=False)
            if 0 < n < len(ln) and int(a * 70) % 3 == 0 and not self.paused:
                self.audio.play('blip', .05)
        return True

    def fx_shake(self, cv, amt):
        """Sacudida corta de pantalla (se llama al final del dibujo)."""
        if amt < 0.5:
            return
        cp = cv.copy()
        cv.fill((0, 0, 0))
        cv.blit(cp, (random.randint(-int(amt), int(amt)), random.randint(-int(amt), int(amt))))
