"""Arte de la batalla aérea: jefes aéreos (uno por oleada), minas y tintes de aeronaves.
Cada pieza del casco se dibuja como una placa con bisel (luz arriba a la izquierda), juntas, remaches y luces; al final todo
el sprite recibe sombreado, luz de borde y contorno (polish)."""
import math
import pygame
import random


def _S():
    return 3


ENG = {}          # posiciones (relativas al centro del sprite) de las toberas de cada jefe, para los resplandores de los motores


def make_air_boss(k):
    """Jefe aéreo k (0 = el comandante stealth se construye aparte). Mira hacia abajo (sur)."""
    fn = [None, _nodriza, _fantasma, _artillero, _tormenta, _titan][k]
    return polish(fn())


def _surf(w, h):
    S = _S()
    return pygame.Surface((w * S, h * S), pygame.SRCALPHA), S


def _fin(s, w, h):
    return pygame.transform.smoothscale(s, (w, h))


def _sh(c, d):
    return tuple(max(0, min(255, v + d)) for v in c[:3])


def _mask_of(s, pts):
    m = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(m, (255, 255, 255, 255), pts)
    return pygame.mask.from_surface(m, 100)


def plate(s, S, pts, base, bevel=1.6, top=None, rivets=0, seam=None, soft=False):
    """Placa metálica: relleno con degradado vertical, bisel claro arriba-izquierda y sombra abajo-derecha."""
    P = [(x * S, y * S) for x, y in pts]
    m = _mask_of(s, P)
    ys = [p[1] for p in P]
    y0, y1 = int(min(ys)), int(max(ys)) + 1
    fill = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    c0 = top or _sh(base, 22)
    c1 = _sh(base, -26)
    for y in range(max(0, y0), min(s.get_height(), y1)):
        k = (y - y0) / max(1, y1 - y0)
        pygame.draw.line(fill, (int(c0[0] + (c1[0] - c0[0]) * k), int(c0[1] + (c1[1] - c0[1]) * k), int(c0[2] + (c1[2] - c0[2]) * k), 255), (0, y), (s.get_width(), y))
    fill.blit(m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(fill, (0, 0))
    d = max(1, int(bevel * S))
    for dx, dy, col in ((d, d, (255, 255, 255, 56 if soft else 90)), (-d, -d, (0, 0, 20, 84 if soft else 110))):
        sh = pygame.mask.Mask(s.get_size())
        sh.draw(m, (dx, dy))
        band = m.copy()
        band.erase(sh, (0, 0))
        s.blit(band.to_surface(setcolor=col, unsetcolor=(0, 0, 0, 0)), (0, 0))
    pygame.draw.polygon(s, seam or _sh(base, -60), P, max(1, S // 2))
    for i in range(rivets):
        a = (i + 0.5) / rivets
        x = P[0][0] + (P[1][0] - P[0][0]) * a
        y = P[0][1] + (P[1][1] - P[0][1]) * a
        pygame.draw.circle(s, _sh(base, 40), (int(x), int(y)), max(1, S // 2))


def nozzle(s, S, c, r, glow=(255, 170, 80)):
    """Tobera de motor vista desde atrás: anillo metálico, interior oscuro y llama."""
    x, y = c[0] * S, c[1] * S
    pygame.draw.circle(s, (14, 16, 20), (x, y), int((r + 1.2) * S))
    pygame.draw.circle(s, (92, 98, 110), (x, y), int(r * S))
    pygame.draw.circle(s, (46, 50, 60), (x, y), int(r * 0.78 * S))
    pygame.draw.circle(s, (20, 22, 28), (x, y), int(r * 0.62 * S))
    pygame.draw.circle(s, glow, (x, y), int(r * 0.46 * S))
    pygame.draw.circle(s, _sh(glow, 70), (x, y), int(r * 0.22 * S))
    for a in range(0, 360, 45):
        ra = math.radians(a)
        pygame.draw.line(s, (130, 136, 148), (x + math.cos(ra) * r * 0.78 * S, y + math.sin(ra) * r * 0.78 * S),
                         (x + math.cos(ra) * r * S, y + math.sin(ra) * r * S), max(1, S // 2))


def canopy(s, S, c, w, h, tint=(60, 150, 220)):
    """Cabina de cristal con degradado y reflejo."""
    x, y = c[0] * S, c[1] * S
    r = pygame.Rect(0, 0, w * S, h * S)
    r.center = (x, y)
    pygame.draw.ellipse(s, (10, 16, 28), r.inflate(2 * S, 2 * S))
    for i in range(int(h * S)):
        k = i / max(1, h * S)
        col = (int(tint[0] * (1.15 - 0.7 * k)), int(tint[1] * (1.15 - 0.6 * k)), int(tint[2] * (1.2 - 0.4 * k)))
        yy = r.top + i
        half = math.sqrt(max(0.0, 1 - ((i - h * S / 2) / (h * S / 2)) ** 2)) * w * S / 2
        pygame.draw.line(s, tuple(max(0, min(255, v)) for v in col), (x - half, yy), (x + half, yy))
    pygame.draw.ellipse(s, (235, 248, 255), (r.left + w * S * 0.2, r.top + h * S * 0.1, w * S * 0.3, h * S * 0.28))


def lights(s, S, pts, col, r=1.1):
    for x, y in pts:
        pygame.draw.circle(s, _sh(col, -90), (x * S, y * S), int((r + 0.8) * S))
        pygame.draw.circle(s, col, (x * S, y * S), int(r * S))
        pygame.draw.circle(s, (255, 255, 255), (x * S - S // 2, y * S - S // 2), max(1, int(r * 0.4 * S)))


def polish(spr, rim=(255, 236, 200)):
    """Sombreado general, luz de borde arriba-izquierda y contorno oscuro para cualquier sprite de aeronave."""
    w, h = spr.get_size()
    out = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    m = pygame.mask.from_surface(spr, 40)
    big = pygame.mask.Mask((w + 4, h + 4))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            big.draw(m, (2 + dx, 2 + dy))
    base = pygame.mask.Mask((w + 4, h + 4))
    base.draw(m, (2, 2))
    outline = big.copy()
    outline.erase(base, (0, 0))
    out.blit(outline.to_surface(setcolor=(8, 10, 18, 215), unsetcolor=(0, 0, 0, 0)), (0, 0))
    body = spr.copy()
    shade_ov = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        k = y / max(1, h - 1)
        pygame.draw.line(shade_ov, (255, 255, 255, int(46 * (1 - k))) if k < 0.5 else (0, 4, 24, int(70 * (k - 0.5) * 2)), (0, y), (w, y))
    shade_ov.blit(m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    body.blit(shade_ov, (0, 0))
    out.blit(body, (2, 2))
    top = pygame.mask.Mask((w, h))
    top.draw(m, (1, 1))
    lit = m.copy()
    lit.erase(top, (0, 0))
    out.blit(lit.to_surface(setcolor=(*rim, 150), unsetcolor=(0, 0, 0, 0)), (2, 2))
    return out


class _Ctx:
    """Lienzo de un jefe. Se dibuja con el morro hacia ARRIBA (y crece hacia la cola) y todo sale invertido: el jefe mira al sur."""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.S = _S()
        self.s = pygame.Surface((W * self.S, H * self.S), pygame.SRCALPHA)

    def fp(self, pts):
        return [(x, self.H - y) for x, y in pts]

    def plate(self, pts, base, bevel=1.0, top=None, seam=None):
        plate(self.s, self.S, self.fp(pts), base, bevel, top=top, seam=seam, soft=True)

    def both(self, pts, base, **kw):
        self.plate(pts, base, **kw)
        self.plate([(self.W - x, y) for x, y in pts], base, **kw)

    def line(self, a, b, col, w=0.5):
        (x0, y0), (x1, y1) = self.fp([a, b])
        pygame.draw.line(self.s, col, (x0 * self.S, y0 * self.S), (x1 * self.S, y1 * self.S), max(1, int(w * self.S)))

    def both_line(self, a, b, col, w=0.5):
        self.line(a, b, col, w)
        self.line((self.W - a[0], a[1]), (self.W - b[0], b[1]), col, w)

    def poly_mask(self, polys):
        m = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        for pts in polys:
            pygame.draw.polygon(m, (255, 255, 255, 255), [(x * self.S, y * self.S) for x, y in self.fp(pts)])
        return m

    def camo(self, polys, cols, seed, n=26, size=(10, 26)):
        """Manchas de camuflaje recortadas dentro de las piezas dadas."""
        rnd = random.Random(seed)
        lay = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        xs = [x for pts in polys for x, _ in pts]
        ys = [y for pts in polys for _, y in pts]
        for _ in range(n):
            cx, cy = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
            rw, rh = rnd.uniform(*size), rnd.uniform(size[0] * 0.5, size[1] * 0.8)
            pts = []
            for k in range(9):
                a = k / 9 * 6.283
                rr = rnd.uniform(0.6, 1.0)
                pts.append((cx + math.cos(a) * rw * rr, cy + math.sin(a) * rh * rr))
            pygame.draw.polygon(lay, (*rnd.choice(cols), 255), [(x * self.S, (self.H - y) * self.S) for x, y in pts])
        lay.blit(self.poly_mask(polys), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.s.blit(lay, (0, 0))

    def weather(self, polys, seed, n=60, alpha=34):
        """Manchas de suciedad y vetas de hollín en el sentido del vuelo."""
        rnd = random.Random(seed)
        lay = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        xs = [x for pts in polys for x, _ in pts]
        ys = [y for pts in polys for _, y in pts]
        for _ in range(n):
            x = rnd.uniform(min(xs), max(xs))
            y = rnd.uniform(min(ys), max(ys))
            ln = rnd.uniform(6, 26)
            pygame.draw.line(lay, (10, 8, 6, rnd.randint(alpha // 2, alpha)), (x * self.S, (self.H - y) * self.S), (x * self.S, (self.H - y - ln) * self.S), max(1, int(rnd.uniform(0.6, 1.8) * self.S)))
        lay.blit(self.poly_mask(polys), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.s.blit(lay, (0, 0))

    def nozzle(self, c, r, hot=(255, 120, 40)):
        x, y = c[0] * self.S, (self.H - c[1]) * self.S
        S = self.S
        pygame.draw.circle(self.s, (10, 10, 12), (x, y), int((r + 1.0) * S))
        pygame.draw.circle(self.s, (104, 106, 112), (x, y), int(r * S))
        pygame.draw.circle(self.s, (58, 58, 64), (x, y), int(r * 0.82 * S))
        pygame.draw.circle(self.s, (24, 20, 20), (x, y), int(r * 0.66 * S))
        pygame.draw.circle(self.s, hot, (x, y), int(r * 0.4 * S))
        pygame.draw.circle(self.s, (255, 214, 140), (x, y), int(r * 0.18 * S))
        for a in range(0, 360, 30):
            ra = math.radians(a)
            pygame.draw.line(self.s, (150, 152, 158), (x + math.cos(ra) * r * 0.82 * S, y + math.sin(ra) * r * 0.82 * S),
                             (x + math.cos(ra) * r * S, y + math.sin(ra) * r * S), max(1, S // 3))

    def cockpit(self, c, w, h, tint=(40, 62, 84)):
        """Cabina de cristal oscuro con degradado y un reflejo largo."""
        x, y = c[0] * self.S, (self.H - c[1]) * self.S
        S = self.S
        r = pygame.Rect(0, 0, w * S, h * S)
        r.center = (x, y)
        pygame.draw.ellipse(self.s, (8, 10, 14), r.inflate(1.6 * S, 1.6 * S))
        for i in range(int(h * S)):
            k = i / max(1, h * S)
            half = math.sqrt(max(0.0, 1 - ((i - h * S / 2) / (h * S / 2)) ** 2)) * w * S / 2
            col = tuple(max(0, min(255, int(v * (1.5 - 0.9 * k)))) for v in tint)
            pygame.draw.line(self.s, col, (x - half, r.top + i), (x + half, r.top + i))
        pygame.draw.line(self.s, (190, 214, 232), (x - w * S * 0.2, r.top + h * S * 0.18), (x - w * S * 0.2, r.top + h * S * 0.62), max(1, S // 2))

    def lights(self, pts, col, r=0.8):
        for x, y in pts:
            xx, yy = x * self.S, (self.H - y) * self.S
            pygame.draw.circle(self.s, _sh(col, -110), (xx, yy), int((r + 0.6) * self.S))
            pygame.draw.circle(self.s, col, (xx, yy), int(r * self.S))

    def star(self, c, r, col=(196, 40, 40)):
        x, y = c[0] * self.S, (self.H - c[1]) * self.S
        pts = []
        for k in range(10):
            a = -1.5708 + k * 0.6283
            rr = r if k % 2 == 0 else r * 0.42
            pts.append((x + math.cos(a) * rr * self.S, y + math.sin(a) * rr * self.S))
        pygame.draw.circle(self.s, (24, 26, 30), (x, y), int((r + 1.4) * self.S))
        pygame.draw.polygon(self.s, col, pts)

    def done(self, eng=None, key=None):
        if key is not None and eng is not None:
            ENG[key] = [(x - self.W / 2, self.H / 2 - y) for x, y in eng]
        return _fin(self.s, self.W, self.H)


def _nodriza():
    """Nodriza Tifón: transporte pesado de ala alta en flecha con cuatro turbofanes, deriva en T y rieles de drones."""
    c = _Ctx(300, 210)
    W = 300
    haze, dark = (126, 134, 142), (86, 94, 104)
    wing = [(162, 70), (294, 122), (294, 134), (162, 116)]
    fus = [(150, 4), (159, 14), (163, 38), (165, 150), (160, 186), (150, 206), (140, 186), (135, 150), (137, 38), (141, 14)]
    stab = [(160, 170), (216, 190), (216, 200), (160, 194)]
    # estabilizadores y alas
    c.both(stab, dark, top=(118, 126, 136))
    c.both(wing, haze, bevel=1.2, top=(168, 176, 184))
    # fuselaje
    c.plate([(150, 4), (159, 14), (163, 38), (165, 150), (160, 186), (150, 206), (140, 186), (135, 150), (137, 38), (141, 14)], haze, bevel=1.4, top=(176, 184, 192))
    c.camo([wing, [(W - x, y) for x, y in wing], fus, [(W - x, y) for x, y in stab], stab], [(110, 118, 126), (140, 148, 156)], 11, n=22, size=(8, 22))
    # radomo y cabina
    c.plate([(150, 4), (156, 12), (156, 24), (144, 24), (144, 12)], (52, 56, 62), 0.6, top=(74, 78, 86))
    c.cockpit((150, 34), 14, 14)
    # juntas de paneles y puertas de carga
    for yy in (44, 62, 84, 108, 130, 156):
        c.line((137, yy), (163, yy), (62, 70, 80), 0.4)
    c.line((150, 40), (150, 190), (74, 82, 92), 0.3)
    for yy in (96, 118):
        c.both_line((165, yy), (240 if yy == 96 else 230, yy + (36 if yy == 96 else 22) * 0.65 + 6), (74, 82, 92), 0.4)
    # rieles de drones en las puntas de las alas
    for sd in (-1, 1):
        for k, (dx, dy) in enumerate(((236, 120), (262, 131))):
            x = 150 + sd * (dx - 150)
            c.plate([(x, dy), (x + 6, dy + 8), (x, dy + 14), (x - 6, dy + 8)], (66, 72, 80), 0.5, top=(100, 108, 118))
    # motores bajo el ala
    eng = []
    for dx, yy in ((52, 90), (98, 109)):
        for sd in (-1, 1):
            x = 150 + sd * dx
            c.plate([(x - 6.5, yy - 18), (x + 6.5, yy - 18), (x + 6, yy + 12), (x - 6, yy + 12)], (74, 80, 90), 0.8, top=(116, 124, 134))
            c.plate([(x - 5.5, yy - 20), (x + 5.5, yy - 20), (x + 6, yy - 14), (x - 6, yy - 14)], (22, 22, 26), 0.4)
            c.nozzle((x, yy + 12), 4.6)
            eng.append((x, yy + 12))
    # marcas: franja de cola roja y estrellas
    c.plate([(140, 168), (160, 168), (160, 178), (140, 178)], (170, 34, 40), 0.4, top=(196, 52, 56))
    for sd in (-1, 1):
        c.star((150 + sd * 70, 95 + 0), 5.2)
    c.lights([(150, 200), (294 - 2, 122), (4, 122)], (255, 70, 60), 0.9)
    c.weather([wing, [(W - x, y) for x, y in wing], fus], 3, n=70)
    return c.done(eng, 1)


def _fantasma():
    """Fantasma: ala volante tipo bombardero furtivo, de negro mate, con borde de salida en dientes de sierra."""
    c = _Ctx(250, 220)
    W = 250
    half = [(125, 8), (244, 140), (238, 154), (206, 150), (190, 170), (160, 164), (146, 188), (125, 202)]
    full = half + [(W - x, y) for x, y in reversed(half)][1:-1]
    c.plate(full, (40, 44, 52), 1.2, top=(70, 76, 88), seam=(10, 12, 16))
    # cuerpo central elevado y facetas
    c.plate([(125, 14), (146, 70), (150, 150), (125, 200), (100, 150), (104, 70)], (50, 55, 64), 1.0, top=(78, 84, 96))
    c.plate([(125, 14), (146, 70), (125, 82), (104, 70)], (58, 63, 74), 0.7, top=(86, 92, 104))
    # tomas de aire y cabina
    for sd in (-1, 1):
        x = 125 + sd * 22
        c.plate([(x - 8, 66), (x + 8, 66), (x + 6, 74), (x - 6, 74)], (14, 15, 18), 0.4)
    c.cockpit((125, 34), 14, 12, tint=(36, 50, 66))
    c.both_line((125, 82), (232, 142), (26, 30, 36), 0.5)
    c.both_line((146, 90), (208, 150), (26, 30, 36), 0.4)
    for sd in (-1, 1):
        for k in range(3):
            c.line((125 + sd * (26 + k * 26), 104 + k * 12), (125 + sd * (42 + k * 26), 126 + k * 12), (28, 32, 38), 0.35)
    # toberas planas del borde de salida
    eng = []
    for dx in (30, 62):
        for sd in (-1, 1):
            x = 125 + sd * dx
            yy = 188 - dx * 0.5
            c.plate([(x - 12, yy - 3), (x + 12, yy - 3), (x + 12, yy + 3), (x - 12, yy + 3)], (22, 24, 28), 0.4)
            c.plate([(x - 9, yy), (x + 9, yy), (x + 9, yy + 3), (x - 9, yy + 3)], (190, 96, 40), 0.2, top=(255, 150, 60))
            eng.append((x, yy + 3))
    c.weather([full], 5, n=50, alpha=40)
    return c.done(eng, 2)


def _artillero():
    """Artillero Pesado: bombardero estratégico de alas largas en flecha, ocho motores en cuatro góndolas y camuflaje verde y tierra."""
    c = _Ctx(300, 230)
    W = 300
    wing = [(158, 70), (296, 152), (296, 164), (158, 118)]
    fus = [(150, 6), (156, 16), (159, 50), (160, 196), (155, 222), (150, 228), (145, 222), (140, 196), (141, 50), (144, 16)]
    stab = [(158, 192), (208, 212), (208, 222), (158, 218)]
    c.both(stab, (74, 82, 58), top=(108, 118, 84))
    c.both(wing, (88, 98, 64), bevel=1.2, top=(128, 140, 94))
    c.plate(fus, (92, 102, 70), bevel=1.3, top=(136, 148, 100))
    allp = [wing, [(W - x, y) for x, y in wing], fus, stab, [(W - x, y) for x, y in stab]]
    c.camo(allp, [(122, 108, 74), (58, 68, 44)], 17, n=34, size=(10, 28))
    # góndolas de motores con dos toberas
    eng = []
    for dx in (46, 82):
        for sd in (-1, 1):
            x = 150 + sd * (dx + 8)
            yy = 70 + (x - 150) * 0.0 + abs(x - 150) * (82 / 138) - 4
            c.plate([(x - 8, yy - 24), (x + 8, yy - 24), (x + 8, yy + 16), (x - 8, yy + 16)], (70, 78, 60), 0.9, top=(112, 120, 92))
            c.plate([(x - 8, yy - 26), (x + 8, yy - 26), (x + 8, yy - 20), (x - 8, yy - 20)], (20, 20, 22), 0.4)
            for ox in (-4, 4):
                c.nozzle((x + ox, yy + 16), 3.0)
                eng.append((x + ox, yy + 16))
    # cabina, bahía de bombas y detalles
    c.cockpit((150, 34), 12, 16)
    c.plate([(142, 120), (158, 120), (158, 176), (142, 176)], (50, 56, 40), 0.7, top=(70, 78, 56))
    for k in range(5):
        c.line((142, 128 + k * 11), (158, 128 + k * 11), (30, 34, 24), 0.4)
    for yy in (54, 78, 100, 186):
        c.line((141, yy), (159, yy), (50, 58, 40), 0.4)
    c.both_line((158, 78), (230, 124), (56, 64, 44), 0.4)
    for sd in (-1, 1):
        c.star((150 + sd * 96, 124 + abs(sd * 96) * 0.0 + 10), 5)
        c.lights([(150 + sd * 144, 156)], (255, 70, 60) if sd < 0 else (90, 255, 120), 0.9)
    c.weather(allp, 9, n=80)
    return c.done(eng, 3)


def _tormenta():
    """Tormenta: caza pesado de superioridad aérea con dos motores, derivas inclinadas y cabina de cristal dorado."""
    c = _Ctx(280, 220)
    W = 280
    wing = [(150, 78), (264, 142), (266, 156), (160, 160)]
    tail = [(156, 172), (214, 196), (216, 204), (160, 198)]
    c.both(tail, (120, 128, 140), top=(160, 168, 180))
    c.both(wing, (138, 146, 158), bevel=1.2, top=(182, 190, 200))
    # deriva inclinada (vista desde arriba: aleta fina)
    for sd in (-1, 1):
        x = 140 + sd * 30
        c.plate([(x - 3, 150), (x + 3, 150), (x + sd * 8 + 3, 200), (x + sd * 8 - 3, 200)], (110, 118, 130), 0.5, top=(150, 158, 170))
    # fuselaje central con dos góndolas
    body = [(140, 4), (148, 22), (156, 60), (162, 110), (162, 190), (150, 208), (130, 208), (118, 190), (118, 110), (124, 60), (132, 22)]
    c.plate(body, (146, 154, 166), bevel=1.4, top=(188, 196, 206))
    allp = [wing, [(W - x, y) for x, y in wing], body, tail, [(W - x, y) for x, y in tail]]
    c.camo(allp, [(112, 120, 134), (170, 178, 190)], 23, n=28, size=(8, 22))
    # tomas de aire, cabina y radomo
    for sd in (-1, 1):
        x = 140 + sd * 17
        c.plate([(x - 6, 82), (x + 6, 82), (x + 5, 98), (x - 5, 98)], (16, 18, 22), 0.5)
    c.plate([(140, 4), (146, 18), (134, 18)], (54, 58, 64), 0.5, top=(76, 80, 88))
    c.cockpit((140, 52), 15, 40, tint=(130, 96, 36))
    c.line((140, 34), (140, 70), (60, 44, 20), 0.4)
    # misiles en las puntas y bajo el ala
    for sd in (-1, 1):
        x = 140 + sd * 128
        c.plate([(x - 2.2, 126), (x + 2.2, 126), (x + 2.2, 158), (x - 2.2, 158)], (214, 218, 222), 0.4, top=(240, 242, 246))
        c.plate([(x - 2.2, 120), (x + 2.2, 120), (x, 112)], (60, 62, 68), 0.2)
        c.lights([(x, 151)], (255, 80, 70) if sd < 0 else (90, 255, 120), 0.8)
        x2 = 140 + sd * 68
        c.plate([(x2 - 2, 112), (x2 + 2, 112), (x2 + 2, 148), (x2 - 2, 148)], (200, 204, 210), 0.3, top=(236, 238, 242))
    c.both_line((150, 100), (252, 148), (92, 100, 112), 0.4)
    c.both_line((150, 130), (230, 152), (92, 100, 112), 0.4)
    c.line((140, 70), (140, 206), (96, 104, 116), 0.35)
    for yy in (90, 130, 170):
        c.line((120, yy), (160, yy), (96, 104, 116), 0.35)
    # toberas gemelas
    eng = []
    for x in (128, 152):
        c.nozzle((x, 208), 7.0, hot=(255, 140, 50))
        eng.append((x, 208))
    c.star((140 + 96, 150), 4.4)
    c.star((140 - 96, 150), 4.4)
    c.weather(allp, 13, n=60)
    return c.done(eng, 4)


def _titan():
    """Titán Aéreo: cañonero acorazado de cuatro motores con ventiladores carenados, casco gris pizarra y núcleo blindado."""
    c = _Ctx(340, 240)
    W = 340
    wing = [(170, 70), (336, 136), (336, 164), (170, 150)]
    body = [(170, 10), (190, 30), (200, 80), (204, 170), (194, 214), (170, 232), (146, 214), (136, 170), (140, 80), (150, 30)]
    c.both(wing, (70, 76, 86), bevel=1.6, top=(110, 118, 130))
    c.plate(body, (66, 72, 82), bevel=1.8, top=(108, 116, 128))
    allp = [wing, [(W - x, y) for x, y in wing], body]
    # placas blindadas y juntas
    c.both([(176, 84), (320, 138), (320, 158), (176, 138)], (58, 64, 74), bevel=0.8, top=(88, 96, 108))
    c.both_line((176, 90), (326, 140), (30, 34, 40), 0.5)
    c.both_line((176, 112), (326, 150), (30, 34, 40), 0.5)
    for yy in (44, 70, 100, 150, 186):
        c.line((142, yy), (198, yy), (36, 40, 48), 0.5)
    c.line((170, 20), (170, 226), (40, 44, 52), 0.4)
    # franjas de aviso en los extremos de las alas
    for sd in (-1, 1):
        for k in range(4):
            x = 170 + sd * (150 + k * 4)
            c.plate([(x, 138 + k * 5), (x + sd * 3, 136 + k * 5), (x + sd * 5, 141 + k * 5), (x + sd * 2, 143 + k * 5)], (200, 50, 52), 0.3)
    # ventiladores carenados (cuatro): anillo, aspas y cubo
    eng = []
    S = c.S
    for dx, yy in ((74, 100), (126, 120)):
        for sd in (-1, 1):
            x = 170 + sd * dx
            cx_, cy_ = x * S, (c.H - yy) * S
            pygame.draw.circle(c.s, (14, 14, 18), (cx_, cy_), int(25 * S))
            pygame.draw.circle(c.s, (104, 110, 120), (cx_, cy_), int(23 * S))
            pygame.draw.circle(c.s, (32, 34, 40), (cx_, cy_), int(19 * S))
            for a in range(0, 360, 36):
                ra = math.radians(a)
                pygame.draw.polygon(c.s, (84, 90, 102), [(cx_, cy_), (cx_ + math.cos(ra - 0.14) * 18 * S, cy_ + math.sin(ra - 0.14) * 18 * S), (cx_ + math.cos(ra + 0.14) * 18 * S, cy_ + math.sin(ra + 0.14) * 18 * S)])
            pygame.draw.circle(c.s, (26, 28, 34), (cx_, cy_), int(6 * S))
            pygame.draw.circle(c.s, (180, 60, 56), (cx_, cy_), int(2.4 * S))
            eng.append((x, yy + 22))
    # sponsones laterales: soportes blindados para las dos torretas (están en x = +-135 del centro)
    for sd in (-1, 1):
        x = 170 + sd * 135
        c.plate([(x - 18, 118), (x + 18, 118), (x + 14, 96), (x - 14, 96)], (60, 66, 76), 0.8, top=(96, 104, 116))
        cx2, cy2 = x * S, (c.H - 86) * S
        pygame.draw.circle(c.s, (12, 12, 16), (cx2, cy2), int(32 * S))
        pygame.draw.circle(c.s, (92, 98, 110), (cx2, cy2), int(29 * S))
        pygame.draw.circle(c.s, (50, 54, 64), (cx2, cy2), int(24 * S))
        for a in range(0, 360, 30):
            ra = math.radians(a)
            pygame.draw.line(c.s, (200, 60, 56) if (a // 30) % 2 else (22, 24, 28), (cx2 + math.cos(ra) * 25 * S, cy2 + math.sin(ra) * 25 * S), (cx2 + math.cos(ra) * 29 * S, cy2 + math.sin(ra) * 29 * S), max(2, S))
    # núcleo del reactor bajo una escotilla blindada
    cx_, cy_ = 170 * S, (c.H - 118) * S
    pygame.draw.circle(c.s, (14, 14, 18), (cx_, cy_), int(26 * S))
    pygame.draw.circle(c.s, (96, 102, 114), (cx_, cy_), int(23 * S))
    for a in range(0, 360, 20):
        ra = math.radians(a)
        pygame.draw.line(c.s, (200, 60, 56) if (a // 20) % 2 else (24, 26, 30), (cx_ + math.cos(ra) * 17 * S, cy_ + math.sin(ra) * 17 * S), (cx_ + math.cos(ra) * 23 * S, cy_ + math.sin(ra) * 23 * S), max(2, S))
    pygame.draw.circle(c.s, (36, 38, 46), (cx_, cy_), int(16 * S))
    for r_, col in ((13, (110, 26, 36)), (9.5, (214, 56, 50)), (5.5, (255, 140, 90)), (2.6, (255, 236, 210))):
        pygame.draw.circle(c.s, col, (cx_, cy_), int(r_ * S))
    # cabina, antenas y cañones de proa
    c.cockpit((170, 50), 22, 22, tint=(34, 52, 74))
    for sd in (-1, 1):
        c.plate([(170 + sd * 16 - 3, 40), (170 + sd * 16 + 3, 40), (170 + sd * 16 + 3, 6), (170 + sd * 16 - 3, 6)], (40, 44, 52), 0.4)
    c.star((170 + 96, 150), 6)
    c.star((170 - 96, 150), 6)
    c.lights([(8, 150), (332, 150), (170, 230)], (255, 70, 60), 1.0)
    c.weather(allp, 19, n=90, alpha=38)
    return c.done([], 5)


def make_pod_turret():
    """Torreta doble del Titán Aéreo, con los cañones hacia arriba (se rota hacia el jugador al dibujarla)."""
    S = 3
    W = H = 100
    s = pygame.Surface((W * S, H * S), pygame.SRCALPHA)
    cx, cy = W * S // 2, H * S // 2
    pygame.draw.circle(s, (10, 10, 14), (cx, cy), 27 * S)
    for sd in (-1, 1):                                              # cañones gemelos
        x0 = cx + sd * 7 * S
        pygame.draw.rect(s, (14, 14, 18), (x0 - 4 * S, cy - 44 * S, 8 * S, 46 * S), border_radius=S)
        for i in range(int(44 * S)):
            k = i / (44 * S)
            c = int(120 - 60 * k)
            pygame.draw.line(s, (c, c + 4, c + 12), (x0 - 3 * S, cy - 44 * S + i), (x0 + 3 * S, cy - 44 * S + i))
        pygame.draw.rect(s, (24, 24, 28), (x0 - 4.6 * S, cy - 46 * S, 9.2 * S, 7 * S), border_radius=S)
        pygame.draw.rect(s, (8, 8, 10), (x0 - 2 * S, cy - 46 * S, 4 * S, 3 * S))
    for r_, col in ((24, (86, 92, 104)), (20, (60, 66, 78))):
        pygame.draw.circle(s, col, (cx, cy), r_ * S)
    pygame.draw.circle(s, (118, 126, 138), (cx - 5 * S, cy - 6 * S), 8 * S)
    pygame.draw.circle(s, (74, 80, 92), (cx - 5 * S, cy - 6 * S), 8 * S, max(1, S // 2))
    pygame.draw.circle(s, (210, 54, 50), (cx + 9 * S, cy + 7 * S), 3 * S)
    pygame.draw.circle(s, (255, 190, 170), (cx + 9 * S - S // 2, cy + 7 * S - S // 2), S)
    return polish(pygame.transform.smoothscale(s, (W, H)))
