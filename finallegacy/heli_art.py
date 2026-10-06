"""Arte del Blackhawk y de los objetivos de las misiones aire-tierra: dibujados con degradados, sombras y detalle a mayor resolución
y reducidos con suavizado (solo pygame, sin numpy)."""
import math
import random
import pygame

BH_W, BH_H = 130, 152
BH_HUB = (65, 76)                 # centro del rotor dentro del sprite
BH_ROTOR_R = 61.0                 # radio del rotor principal (px del sprite)
BH_TAIL = (65, 76 + 76)           # extremo de la cola
BH_TAIL_ROTOR = (65, 76 + 70)     # centro del rotor de cola


def _lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def _grad(size, c0, c1, mode):
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    g = pygame.Surface((w, h), pygame.SRCALPHA)
    if mode == 'r':
        r = max(w, h) / 2
        for i in range(int(r), 0, -2):
            pygame.draw.circle(g, _lerp(c0, c1, 1 - i / r) + (255,), (w // 2 - w // 8, h // 2 - h // 8), i + int(r * 0.3))
        return g
    n = h if mode == 'v' else w
    for i in range(n):
        c = _lerp(c0, c1, i / max(1, n - 1)) + (255,)
        if mode == 'v':
            pygame.draw.line(g, c, (0, i), (w, i))
        else:
            pygame.draw.line(g, c, (i, 0), (i, h))
    return g


class _Art:
    """Pincel con supersampling: se dibuja en coordenadas finales y se escala por `ss`."""

    def __init__(self, w, h, ss=4, dx=0, dy=0):
        self.ss, self.dx, self.dy = ss, dx, dy
        self.surf = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA)
        self.size = (w, h)

    def P(self, x, y):
        return ((x + self.dx) * self.ss, (y + self.dy) * self.ss)

    def _fill(self, bbox_pts, mask_draw, c0, c1, mode):
        xs = [p[0] for p in bbox_pts]
        ys = [p[1] for p in bbox_pts]
        x0, y0 = max(0, int(min(xs)) - 1), max(0, int(min(ys)) - 1)
        x1, y1 = min(self.surf.get_width(), int(max(xs)) + 2), min(self.surf.get_height(), int(max(ys)) + 2)
        if x1 <= x0 or y1 <= y0:
            return
        g = _grad((x1 - x0, y1 - y0), c0, c1, mode)
        m = pygame.Surface((x1 - x0, y1 - y0), pygame.SRCALPHA)
        mask_draw(m, (x0, y0))
        g.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.surf.blit(g, (x0, y0))

    def poly(self, pts, c0, c1=None, mode='v', edge=None, ew=1):
        c1 = c1 or c0
        sp = [self.P(*p) for p in pts]
        self._fill(sp, lambda m, o: pygame.draw.polygon(m, (255, 255, 255, 255), [(x - o[0], y - o[1]) for x, y in sp]), c0, c1, mode)
        if edge:
            pygame.draw.polygon(self.surf, edge, sp, max(1, int(ew * self.ss)))

    def ell(self, rect, c0, c1=None, mode='v', edge=None, ew=1):
        c1 = c1 or c0
        x, y, w, h = rect
        a, b = self.P(x, y), self.P(x + w, y + h)
        r = pygame.Rect(int(a[0]), int(a[1]), int(b[0] - a[0]), int(b[1] - a[1]))
        self._fill([(r.x, r.y), (r.right, r.bottom)], lambda m, o: pygame.draw.ellipse(m, (255, 255, 255, 255), r.move(-o[0], -o[1])), c0, c1, mode)
        if edge:
            pygame.draw.ellipse(self.surf, edge, r, max(1, int(ew * self.ss)))

    def rrect(self, rect, c0, c1=None, mode='v', rad=2, edge=None, ew=1):
        c1 = c1 or c0
        x, y, w, h = rect
        a, b = self.P(x, y), self.P(x + w, y + h)
        r = pygame.Rect(int(a[0]), int(a[1]), int(b[0] - a[0]), int(b[1] - a[1]))
        rr = int(rad * self.ss)
        self._fill([(r.x, r.y), (r.right, r.bottom)], lambda m, o: pygame.draw.rect(m, (255, 255, 255, 255), r.move(-o[0], -o[1]), border_radius=rr), c0, c1, mode)
        if edge:
            pygame.draw.rect(self.surf, edge, r, max(1, int(ew * self.ss)), border_radius=rr)

    def line(self, a, b, col, w=1):
        pygame.draw.line(self.surf, col, self.P(*a), self.P(*b), max(1, int(w * self.ss)))

    def circ(self, c, r, col, w=0):
        pygame.draw.circle(self.surf, col, self.P(*c), int(r * self.ss), int(w * self.ss) if w else 0)

    def shadow(self, rect, alpha=70, blur=3):
        """Sombra suave: elipse negra desplazada, con bordes difusos por capas."""
        x, y, w, h = rect
        for i in range(blur, 0, -1):
            k = i / blur
            a, b = self.P(x - k * 2, y - k * 2), self.P(x + w + k * 2, y + h + k * 2)
            tmp = pygame.Surface((max(1, int(b[0] - a[0])), max(1, int(b[1] - a[1]))), pygame.SRCALPHA)
            pygame.draw.ellipse(tmp, (0, 0, 0, int(alpha / blur)), tmp.get_rect())
            self.surf.blit(tmp, a)

    def out(self):
        return pygame.transform.smoothscale(self.surf, self.size)


def _mirror(pts):
    """Lista de puntos de la mitad derecha (de arriba hacia abajo) -> contorno completo simétrico respecto de x=65."""
    return pts + [(130 - x, y) for x, y in reversed(pts)]


# ------------------------------------------------------------------ Blackhawk
def make_blackhawk():
    """UH-60 Blackhawk visto desde arriba, mirando al norte, con el centro del rotor en el centro del sprite (el rotor se dibuja aparte)."""
    a = _Art(BH_W, BH_H, 4, 0, 30)
    dark, mid, edge = (22, 26, 24), (44, 50, 46), (8, 10, 9)
    # ruedas del tren principal y de cola
    for sx in (-1, 1):
        a.ell((65 + sx * 17 - 4, 62, 8, 14), (30, 30, 32), (10, 10, 12), 'h')
        a.line((65 + sx * 17, 70), (65 + sx * 12, 66), (20, 20, 22), 2)
    a.ell((62, 100, 6, 8), (30, 30, 32), (10, 10, 12), 'h')
    # cola: viga, deriva y estabilizador
    a.poly(_mirror([(70, 86), (68, 98), (67, 118)]), mid, dark, 'v', edge)
    a.poly([(63, 100), (67, 100), (68, 124), (62, 124)], (60, 66, 62), (30, 34, 32), 'v', edge)
    a.rrect((49, 108, 32, 8), (70, 76, 72), (30, 34, 32), 'v', 3, edge)
    a.line((52, 110), (78, 110), (110, 116, 110), 1)
    a.circ((65, 124), 1.6, (255, 60, 50))
    # alas cortas con vainas de cohetes y misiles
    a.poly(_mirror([(96, 58), (97, 66), (82, 68)]), (50, 56, 52), (24, 28, 26), 'v', edge)
    for sx in (-1, 1):
        cx = 65 + sx * 33
        a.rrect((cx - 4, 52, 8, 26), (96, 100, 98), (40, 44, 42), 'h', 3, edge)
        a.circ((cx, 54.5), 2.2, (30, 32, 32))
        a.circ((cx, 60), 0.8, (210, 214, 210))
        a.circ((cx, 65), 0.8, (210, 214, 210))
        a.circ((cx, 70), 0.8, (210, 214, 210))
        a.poly([(cx - 2, 78), (cx + 2, 78), (cx, 83)], (150, 40, 36), (90, 20, 18), 'v')
    a.circ((65 - 36, 66), 1.6, (255, 40, 40))
    a.circ((65 + 36, 66), 1.6, (60, 255, 90))
    # fuselaje principal
    a.shadow((52, 22, 26, 66), 60, 3)
    body = _mirror([(65, 8), (69, 9), (73, 13), (76, 20), (78, 30), (79, 44), (79, 58), (77, 70), (74, 80), (71, 90)])
    a.poly(body, (70, 78, 72), (24, 28, 26), 'h', edge, 1.2)
    a.poly(_mirror([(65, 12), (69, 14), (72, 20), (74, 30), (74, 50), (73, 70), (70, 84)]), (92, 100, 94), (40, 46, 42), 'v')
    for yy in (26, 40, 56, 76):
        a.line((54, yy), (76, yy), (18, 22, 20), 0.8)
    # cabina: parabrisas y ventanas laterales con reflejos
    a.poly([(58.5, 12.5), (71.5, 12.5), (74, 23), (56, 23)], (28, 44, 62), (118, 160, 190), 'v', (10, 14, 18), 0.8)
    a.line((65, 12.5), (65, 23), (12, 16, 20), 0.9)
    a.line((59.5, 15), (62, 15), (210, 230, 245, 140), 0.7)
    a.poly([(54.5, 25), (57, 25), (57, 35), (54, 33)], (26, 40, 56), (96, 136, 168), 'v', (10, 14, 18), 0.6)
    a.poly([(73, 25), (75.5, 25), (76, 33), (73, 35)], (26, 40, 56), (96, 136, 168), 'v', (10, 14, 18), 0.6)
    # motores (nacelas) con tomas de aire y escapes
    for sx in (-1, 1):
        x = 65 + sx * 9 - 5
        a.rrect((x, 48, 10, 32), (76, 82, 80), (28, 32, 32), 'h', 4, edge)
        a.ell((x + 1.5, 47.5, 7, 5), (14, 14, 16), (60, 62, 64), 'v')
        a.ell((x + 1.5, 77, 7, 5), (50, 36, 30), (10, 10, 10), 'v')
        a.line((x + 3, 54), (x + 3, 74), (110, 116, 112), 0.6)
    # cubo del rotor y mástil
    a.ell((57, 61, 16, 16), (64, 70, 66), (18, 20, 20), 'r', edge)
    a.ell((61, 65, 8, 8), (120, 126, 120), (30, 32, 32), 'r', edge, 0.6)
    # ametralladoras de puerta, antenas y sensores
    for sx in (-1, 1):
        a.line((65 + sx * 14.5, 56), (65 + sx * 14.5, 46), (10, 10, 12), 1.1)
    a.rrect((62, 88, 6, 6), (110, 112, 114), (50, 52, 54), 'v', 1, edge, 0.5)
    a.line((65, 94), (65, 100), (20, 22, 22), 0.7)
    a.line((65, 4), (65, 9), (200, 200, 200), 0.6)
    a.circ((65, 8), 0.9, (230, 230, 230))
    return a.out()


def blackhawk_rotor_overlay(scale, rot, tail_rot):
    """Superficie con el disco de los rotores (aspas giratorias con estela difusa). Devuelve (superficie, centro_principal, centro_cola)."""
    R = BH_ROTOR_R * scale
    pad = 4
    size = int(2 * R) + 2 * pad
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    # disco difuso
    for i, al in enumerate((12, 18, 24)):
        pygame.draw.circle(s, (205, 210, 205, al), (c, c), int(R * (1 - i * 0.05)))
    pygame.draw.circle(s, (225, 230, 225, 70), (c, c), int(R), max(1, int(2 * scale)))
    for k in range(4):
        a = rot + k * math.pi / 2
        # estela detrás de cada aspa
        wedge = [(c, c)] + [(c + math.cos(a - t * 0.5) * R * 0.98, c + math.sin(a - t * 0.5) * R * 0.98) for t in (0, 0.2, 0.4, 0.6)]
        pygame.draw.polygon(s, (230, 235, 230, 26), wedge)
        r0 = 8 * scale
        w0, w1 = 2.6 * scale, 1.7 * scale
        nx, ny = -math.sin(a), math.cos(a)
        p0 = (c + math.cos(a) * r0, c + math.sin(a) * r0)
        p1 = (c + math.cos(a) * R, c + math.sin(a) * R)
        pygame.draw.polygon(s, (18, 20, 20, 235), [(p0[0] + nx * w0, p0[1] + ny * w0), (p1[0] + nx * w1, p1[1] + ny * w1),
                                                   (p1[0] - nx * w1, p1[1] - ny * w1), (p0[0] - nx * w0, p0[1] - ny * w0)])
        tip0 = (c + math.cos(a) * R * 0.9, c + math.sin(a) * R * 0.9)
        pygame.draw.line(s, (236, 200, 60, 230), tip0, p1, max(1, int(2.6 * scale)))
    pygame.draw.circle(s, (40, 44, 42), (c, c), max(2, int(5 * scale)))
    pygame.draw.circle(s, (130, 136, 130), (c, c), max(1, int(2.4 * scale)))
    return s, (c, c)


# ------------------------------------------------------------------ objetivos
def _sandbag_ring(a, cx, cy, r, n, col0=(176, 150, 104), col1=(116, 96, 64)):
    for i in range(n):
        ang = i * 2 * math.pi / n
        x, y = cx + math.cos(ang) * r, cy + math.sin(ang) * r
        a.ell((x - 3.4, y - 2.2, 6.8, 4.4), col0, col1, 'v', (70, 56, 38), 0.4)


def _ground_patch(a, cx, cy, rx, ry, col, alpha=200):
    for i in range(5, 0, -1):
        k = i / 5
        a.surf.blit(_blob(int(rx * 2 * a.ss * (0.7 + 0.3 * k)), int(ry * 2 * a.ss * (0.7 + 0.3 * k)), col, int(alpha / 5)),
                    ((cx + a.dx - rx * (0.7 + 0.3 * k)) * a.ss, (cy + a.dy - ry * (0.7 + 0.3 * k)) * a.ss))


def _blob(w, h, col, alpha):
    s = pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)
    pygame.draw.ellipse(s, col + (alpha,), s.get_rect())
    return s


def _aa_base():
    a = _Art(64, 64, 4)
    _ground_patch(a, 32, 33, 26, 25, (40, 32, 22), 150)
    a.ell((10, 10, 44, 44), (150, 130, 96), (96, 80, 56), 'v', (60, 48, 34), 0.8)       # foso de tierra
    a.ell((15, 15, 34, 34), (92, 84, 66), (54, 50, 40), 'r')
    _sandbag_ring(a, 32, 32, 20, 16)
    for sx, sy in ((14, 40), (46, 42)):                                               # cajas de munición
        a.rrect((sx - 4, sy - 3, 8, 6), (96, 104, 76), (54, 60, 42), 'v', 1, (30, 34, 24), 0.5)
    return a.out()


def _aa_top():
    """Torreta con dos cañones apuntando hacia arriba (rumbo 0)."""
    a = _Art(64, 64, 4)
    for sx in (-4.2, 4.2):
        a.rrect((32 + sx - 1.6, 8, 3.2, 28), (80, 84, 82), (28, 30, 30), 'h', 1, (14, 14, 14), 0.5)
        a.rrect((32 + sx - 2.4, 6, 4.8, 5), (40, 42, 42), (16, 16, 16), 'h', 1)
        a.rrect((32 + sx - 2.6, 26, 5.2, 8), (110, 114, 110), (46, 50, 48), 'h', 1.5, (14, 14, 14), 0.5)
    a.shadow((22, 24, 20, 20), 60, 2)
    a.ell((23, 26, 18, 18), (112, 120, 100), (46, 52, 42), 'r', (22, 26, 20), 0.8)
    a.rrect((26, 36, 12, 8), (78, 84, 70), (40, 44, 36), 'v', 2, (20, 24, 18), 0.6)
    a.ell((28.5, 30, 7, 7), (150, 156, 140), (70, 76, 64), 'r', (20, 24, 18), 0.5)
    return a.out()


def _bunker_base():
    a = _Art(84, 84, 4)
    _ground_patch(a, 42, 44, 38, 36, (44, 36, 26), 150)
    a.shadow((10, 12, 66, 66), 70, 4)
    a.rrect((10, 10, 64, 64), (170, 168, 156), (110, 108, 98), 'v', 9, (54, 54, 50), 1.2)        # techo de hormigón
    a.rrect((14, 14, 56, 56), (150, 148, 138), (120, 118, 108), 'v', 6, (90, 88, 80), 0.6)
    for i in range(1, 4):
        a.line((14 + i * 14, 14), (14 + i * 14, 70), (96, 94, 86), 0.5)
        a.line((14, 14 + i * 14), (70, 14 + i * 14), (96, 94, 86), 0.5)
    rnd = random.Random(7)
    for _ in range(26):                                                                        # manchas de suciedad y vegetación
        x, y = rnd.uniform(14, 70), rnd.uniform(14, 70)
        col = rnd.choice(((72, 80, 56, 150), (60, 70, 46, 140), (90, 84, 70, 130)))
        a.ell((x, y, rnd.uniform(3, 8), rnd.uniform(2, 5)), col[:3], col[:3], 'v')
    a.rrect((22, 64, 22, 8), (46, 46, 42), (20, 20, 18), 'v', 2, (10, 10, 10), 0.5)          # abertura / entrada
    a.rrect((20, 18, 14, 10), (92, 100, 70), (60, 68, 46), 'v', 3, (36, 42, 28), 0.5)          # red de camuflaje
    _sandbag_ring(a, 42, 44, 36, 26)
    return a.out()


def _bunker_top():
    a = _Art(84, 84, 4)
    a.rrect((39, 8, 6, 36), (70, 72, 70), (22, 24, 24), 'h', 2, (10, 10, 10), 0.5)
    a.rrect((38, 6, 8, 7), (40, 42, 42), (14, 14, 14), 'h', 2)
    a.shadow((31, 36, 22, 18), 60, 2)
    a.ell((32, 36, 20, 18), (116, 118, 108), (52, 54, 48), 'r', (22, 24, 22), 0.8)
    a.ell((37, 40, 10, 10), (150, 152, 142), (70, 72, 66), 'r', (22, 24, 22), 0.5)
    return a.out()


def _sam_base():
    a = _Art(76, 64, 4)
    _ground_patch(a, 38, 34, 34, 28, (44, 36, 26), 120)
    a.shadow((8, 12, 60, 44), 70, 3)
    for x in (16, 28, 44, 56):                                                                 # ruedas
        a.rrect((x - 4, 7, 8, 5), (30, 30, 32), (10, 10, 12), 'v', 2)
        a.rrect((x - 4, 51, 8, 5), (30, 30, 32), (10, 10, 12), 'v', 2)
    a.rrect((8, 12, 60, 40), (104, 116, 88), (60, 70, 52), 'v', 4, (30, 36, 26), 0.9)           # chasis
    a.rrect((10, 15, 16, 34), (92, 104, 80), (50, 58, 44), 'v', 3, (28, 32, 24), 0.7)           # cabina
    a.poly([(11, 20), (14, 17), (14, 47), (11, 44)], (28, 44, 60), (96, 136, 168), 'v')
    a.rrect((30, 16, 34, 32), (86, 96, 74), (48, 56, 42), 'v', 3, (28, 32, 24), 0.6)
    return a.out()


def _sam_top():
    """Lanzador con dos misiles apuntando hacia arriba (rumbo 0)."""
    a = _Art(76, 64, 4)
    for sx in (-6, 6):
        a.shadow((38 + sx - 3, 6, 6, 40), 50, 2)
        a.rrect((38 + sx - 3.2, 6, 6.4, 40), (236, 238, 232), (150, 154, 148), 'h', 3, (60, 64, 60), 0.6)
        a.rrect((38 + sx - 3.2, 18, 6.4, 3), (214, 60, 46), (160, 40, 30), 'h', 0)
        a.poly([(38 + sx - 3.2, 6), (38 + sx + 3.2, 6), (38 + sx, 0)], (220, 70, 50), (140, 30, 24), 'v', (60, 20, 16), 0.4)
    a.rrect((26, 32, 24, 14), (90, 100, 80), (48, 54, 42), 'v', 3, (24, 28, 20), 0.6)
    a.ell((33, 36, 10, 10), (130, 140, 120), (60, 66, 54), 'r', (24, 28, 20), 0.5)
    return a.out()


def _depot_base():
    a = _Art(92, 84, 4)
    _ground_patch(a, 46, 44, 42, 38, (36, 30, 24), 160)
    a.shadow((6, 8, 80, 70), 60, 4)
    a.rrect((6, 8, 80, 70), (120, 112, 98), (86, 80, 68), 'v', 8, (50, 46, 40), 1.2)            # dique de contención
    a.rrect((10, 12, 72, 62), (86, 82, 74), (70, 66, 60), 'v', 6)
    for (cx, cy, r, st) in ((29, 33, 15, 0), (63, 33, 15, 1), (46, 58, 15, 0)):
        a.circ((cx + 2.5, cy + 3.5), r, (0, 0, 0, 70))
        a.ell((cx - r, cy - r, 2 * r, 2 * r), (212, 214, 208), (110, 112, 106), 'r', (60, 62, 58), 0.8)
        a.ell((cx - r + 3, cy - r + 3, 2 * r - 6, 2 * r - 6), (186, 188, 182), (126, 128, 122), 'r', (90, 92, 88), 0.5)
        for ang in range(0, 360, 45):
            x2, y2 = cx + math.cos(math.radians(ang)) * (r - 3), cy + math.sin(math.radians(ang)) * (r - 3)
            a.line((cx, cy), (x2, y2), (150, 152, 146), 0.4)
        col = (196, 52, 44) if st == 0 else (230, 230, 226)
        a.rrect((cx - r + 2, cy - 2, 2 * r - 4, 4), col, tuple(int(c * 0.7) for c in col), 'v', 0)
        a.ell((cx - 3.5, cy - 3.5, 7, 7), (90, 94, 90), (40, 42, 40), 'r', (20, 22, 20), 0.5)
    a.line((29, 33), (63, 33), (70, 74, 70), 2)
    a.line((29, 33), (46, 58), (70, 74, 70), 2)
    a.line((63, 33), (46, 58), (70, 74, 70), 2)
    return a.out()


def _radar_base():
    a = _Art(64, 64, 4)
    _ground_patch(a, 32, 34, 28, 26, (40, 34, 26), 130)
    a.shadow((9, 10, 46, 46), 70, 3)
    a.ell((9, 9, 46, 46), (176, 176, 168), (110, 110, 102), 'v', (60, 60, 56), 1)               # edificio base
    a.ell((13, 13, 38, 38), (150, 152, 146), (116, 118, 112), 'r', (80, 82, 78), 0.6)
    for ang in range(0, 360, 30):
        x2, y2 = 32 + math.cos(math.radians(ang)) * 18, 32 + math.sin(math.radians(ang)) * 18
        a.line((32, 32), (x2, y2), (104, 106, 100), 0.4)
    a.rrect((38, 40, 12, 8), (70, 74, 70), (40, 42, 40), 'v', 1, (20, 22, 20), 0.5)
    return a.out()


def _radar_top():
    """Antena parabólica vista de lado/arriba, con el alimentador apuntando hacia arriba (rumbo 0)."""
    a = _Art(64, 64, 4)
    a.shadow((8, 14, 50, 22), 55, 3)
    a.ell((8, 22, 48, 20), (232, 234, 230), (130, 134, 130), 'v', (60, 64, 60), 0.9)
    a.ell((12, 25, 40, 14), (176, 180, 176), (96, 100, 96), 'r')
    for i in range(-2, 3):
        a.line((32 + i * 8, 24), (32 + i * 8, 40), (110, 114, 110), 0.4)
    a.line((32, 32), (32, 6), (60, 64, 60), 1.2)
    a.circ((32, 6), 2.2, (200, 60, 50))
    a.circ((32, 32), 3, (50, 54, 50))
    return a.out()


def _wreck(sprite, size, seed):
    """Restos: la imagen del objetivo ennegrecida, con cráter, escombros y hollín."""
    w, h = size
    out = pygame.Surface(size, pygame.SRCALPHA)
    rnd = random.Random(seed)
    for i in range(6, 0, -1):
        k = i / 6
        out.blit(_blob(int(w * (0.5 + 0.45 * k)), int(h * (0.5 + 0.45 * k)), (16, 14, 12), int(46 + 22 * (1 - k))),
                 (w / 2 - w * (0.25 + 0.225 * k), h / 2 - h * (0.25 + 0.225 * k)))
    burnt = sprite.copy()
    burnt.fill((60, 56, 52, 255), special_flags=pygame.BLEND_RGBA_MULT)
    burnt.fill((8, 8, 8, 0), special_flags=pygame.BLEND_RGB_ADD)
    out.blit(pygame.transform.rotozoom(burnt, rnd.uniform(-10, 10), 0.86), (w * 0.07, h * 0.07))
    for _ in range(16):
        x, y = rnd.uniform(w * 0.15, w * 0.85), rnd.uniform(h * 0.15, h * 0.85)
        pts = [(x + rnd.uniform(-4, 4), y + rnd.uniform(-3, 3)) for _ in range(4)]
        pygame.draw.polygon(out, rnd.choice(((30, 30, 32, 255), (50, 46, 42, 255), (74, 68, 60, 255))), pts)
    return out


def make_heli_targets():
    """{tipo: dict(base, top, wreck)}; `top` es la parte que gira (se dibuja rotada sobre `base`)."""
    out = {}
    for k, (base, top, seed) in {'aa': (_aa_base(), _aa_top(), 1), 'bunker': (_bunker_base(), _bunker_top(), 2), 'sam': (_sam_base(), _sam_top(), 3),
                                 'depot': (_depot_base(), None, 4), 'radar': (_radar_base(), _radar_top(), 5)}.items():
        full = base.copy()
        if top is not None:
            full.blit(top, (0, 0))
        out[k] = dict(base=base, top=top, wreck=_wreck(full, base.get_size(), seed))
    return out
