"""Arte de la batalla aérea: jefes aéreos (uno por oleada), minas y tintes de aeronaves.
Cada pieza del casco se dibuja como una placa con bisel (luz arriba a la izquierda), juntas, remaches y luces; al final todo
el sprite recibe sombreado, luz de borde y contorno (polish)."""
import math
import pygame


def _S():
    return 3


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


def plate(s, S, pts, base, bevel=1.6, top=None, rivets=0, seam=None):
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
    for dx, dy, col in ((d, d, (255, 255, 255, 90)), (-d, -d, (0, 0, 20, 110))):
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


def _nodriza():
    """Nave nodriza: casco en cuña con cubiertas, hangares con luz naranja, puente de cristal y cuatro motores."""
    W, H = 300, 210
    s, S = _surf(W, H)
    hull = [(150, 205), (210, 170), (292, 80), (298, 40), (240, 14), (150, 30), (60, 14), (2, 40), (8, 80), (90, 170)]
    plate(s, S, hull, (70, 78, 92), 2.2, top=(124, 136, 154))
    plate(s, S, [(150, 194), (204, 162), (280, 80), (284, 48), (238, 24), (150, 40), (62, 24), (16, 48), (20, 80), (96, 162)], (92, 102, 120), 1.6, rivets=0)
    # franjas de aviso en los bordes de las alas
    for sd in (-1, 1):
        for i in range(5):
            x0 = 150 + sd * (96 + i * 8)
            plate(s, S, [(x0, 54 + i * 12), (x0 + sd * 5, 50 + i * 12), (x0 + sd * 8, 56 + i * 12), (x0 + sd * 3, 60 + i * 12)], (232, 190, 50), 0.5)
    # juntas de paneles
    for k in range(1, 8):
        pygame.draw.line(s, (50, 58, 72), (int((24 + k * 5) * S), int((44 + k * 12) * S)), (int((276 - k * 5) * S), int((44 + k * 12) * S)), max(1, S // 2))
    for x in (60, 100, 200, 240):
        pygame.draw.line(s, (50, 58, 72), (x * S, 46 * S), (int((150 + (x - 150) * 0.62) * S), 150 * S), max(1, S // 2))
    # hangares
    for i in range(6):
        x = 56 + i * 38
        y = 150 - abs(i - 2.5) * 6
        pygame.draw.rect(s, (12, 12, 16), (x * S, y * S, 24 * S, 14 * S), border_radius=3)
        pygame.draw.rect(s, (60, 66, 78), (x * S, y * S, 24 * S, 14 * S), max(1, S // 2), border_radius=3)
        pygame.draw.rect(s, (255, 150, 50), ((x + 3) * S, (y + 2) * S, 18 * S, 8 * S), border_radius=2)
        pygame.draw.rect(s, (255, 222, 150), ((x + 5) * S, (y + 3) * S, 14 * S, 2 * S), border_radius=1)
    # puente central de cristal
    plate(s, S, [(108, 72), (192, 72), (204, 100), (192, 128), (108, 128), (96, 100)], (40, 46, 58), 1.4)
    canopy(s, S, (150, 100), 78, 46, (110, 190, 240))
    # radares laterales
    for sd in (-1, 1):
        cx = 150 + sd * 120
        pygame.draw.circle(s, (20, 24, 32), (cx * S, 116 * S), 12 * S)
        pygame.draw.circle(s, (120, 130, 148), (cx * S, 116 * S), 10 * S)
        pygame.draw.circle(s, (70, 78, 92), (cx * S, 116 * S), 6 * S)
        pygame.draw.line(s, (200, 210, 224), (cx * S, 116 * S), ((cx + sd * 6) * S, 110 * S), max(1, S // 2))
    for x in (54, 104, 196, 246):
        nozzle(s, S, (x, 34), 11)
    lights(s, S, [(150, 190), (22, 52), (278, 52), (150, 46)], (255, 80, 70), 1.0)
    return _fin(s, W, H)


def _fantasma():
    W, H = 250, 220
    s, S = _surf(W, H)
    outline = [(125, 216), (150, 150), (246, 60), (200, 40), (160, 70), (125, 22), (90, 70), (50, 40), (4, 60), (100, 150)]
    plate(s, S, outline, (22, 26, 38), 1.8, top=(46, 54, 74), seam=(8, 10, 16))
    # facetas
    plate(s, S, [(125, 206), (146, 148), (232, 62), (200, 48), (160, 78), (125, 34)], (30, 36, 52), 1.2, seam=(8, 10, 16))
    plate(s, S, [(125, 206), (104, 148), (18, 62), (50, 48), (90, 78), (125, 34)], (24, 30, 44), 1.2, seam=(8, 10, 16))
    for sd in (-1, 1):
        pygame.draw.line(s, (80, 230, 255), ((125 + sd * 6) * S, 200 * S), ((125 + sd * 108) * S, 66 * S), 3)
        pygame.draw.line(s, (40, 130, 170), ((125 + sd * 8) * S, 196 * S), ((125 + sd * 104) * S, 70 * S), 1)
        pygame.draw.line(s, (80, 230, 255), ((125 + sd * 26) * S, 128 * S), ((125 + sd * 64) * S, 78 * S), 2)
        pygame.draw.line(s, (80, 230, 255), ((125 + sd * 14) * S, 86 * S), ((125 + sd * 46) * S, 56 * S), 2)
        lights(s, S, [(125 + sd * 36, 52)], (80, 230, 255), 2.2)
    canopy(s, S, (125, 132), 16, 52, (70, 190, 235))
    for x in (-18, 18):
        nozzle(s, S, (125 + x, 40), 6, (80, 200, 255))
    return _fin(s, W, H)


def _artillero():
    """Bombardero pesado: fuselaje, alas rectas con seis motores, deriva doble y bahía de bombas."""
    W, H = 300, 230
    s, S = _surf(W, H)
    plate(s, S, [(0, 124), (300, 124), (290, 90), (10, 90)], (96, 106, 74), 2.0, top=(142, 152, 108), rivets=0)
    for x in range(20, 290, 24):
        pygame.draw.line(s, (60, 68, 46), (x * S, 94 * S), (x * S, 120 * S), max(1, S // 2))
    for sd in (-1, 1):                                    # puntas de ala con luz de posición
        lights(s, S, [(150 + sd * 140, 107)], (255, 70, 60) if sd < 0 else (90, 255, 120), 1.4)
    # fuselaje
    plate(s, S, [(150, 226), (172, 194), (174, 60), (190, 40), (150, 14), (110, 40), (126, 60), (128, 194)], (88, 98, 68), 2.0, top=(134, 146, 102))
    # timones de cola
    plate(s, S, [(120, 46), (180, 46), (206, 20), (94, 20)], (76, 86, 58), 1.4)
    for x in (108, 192):
        plate(s, S, [(x - 7, 56), (x + 7, 56), (x + 5, 16), (x - 5, 16)], (70, 80, 54), 1.0)
    # motores a reacción
    for x in (30, 74, 118, 182, 226, 270):
        pygame.draw.ellipse(s, (14, 16, 12), ((x - 9) * S, 94 * S, 18 * S, 40 * S))
        plate(s, S, [(x - 7, 98), (x + 7, 98), (x + 6, 126), (x - 6, 126)], (62, 70, 52), 0.9)
        nozzle(s, S, (x, 82), 6.5)
        pygame.draw.circle(s, (210, 220, 200), (x * S, 134 * S), int(5 * S))
        pygame.draw.circle(s, (30, 34, 28), (x * S, 134 * S), int(3.4 * S))
    # bahía de bombas
    plate(s, S, [(136, 132), (164, 132), (164, 180), (136, 180)], (40, 44, 32), 0.9)
    for k in range(4):
        lights(s, S, [(150, 140 + k * 10)], (230, 60, 50), 1.3)
    canopy(s, S, (150, 198), 14, 26, (80, 160, 210))
    # ametralladoras de las alas
    for sd in (-1, 1):
        pygame.draw.rect(s, (24, 26, 20), ((150 + sd * 62 - 3) * S, 120 * S, 6 * S, 12 * S), border_radius=2)
    return _fin(s, W, H)


def _tormenta():
    """Ala delta blanca con bobinas de energía en las puntas y rayos grabados en el casco."""
    W, H = 280, 220
    s, S = _surf(W, H)
    outline = [(140, 214), (176, 140), (276, 66), (252, 36), (176, 52), (140, 20), (104, 52), (28, 36), (4, 66), (104, 140)]
    plate(s, S, outline, (178, 196, 220), 2.0, top=(238, 246, 255), seam=(52, 70, 100))
    plate(s, S, [(140, 202), (172, 140), (262, 68), (246, 46), (176, 62), (140, 32)], (200, 214, 232), 1.4, top=(246, 250, 255), seam=(70, 90, 124))
    plate(s, S, [(140, 202), (108, 140), (18, 68), (34, 46), (104, 62), (140, 32)], (170, 188, 214), 1.4, top=(226, 236, 250), seam=(70, 90, 124))
    for sd in (-1, 1):
        for k in range(4):
            pygame.draw.line(s, (96, 124, 170), ((140 + sd * (20 + k * 18)) * S, (160 - k * 22) * S), ((140 + sd * (42 + k * 22)) * S, (96 - k * 8) * S), max(1, S // 2))
        # rayos grabados
        pts = [(140 + sd * 70, 96), (140 + sd * 80, 104), (140 + sd * 72, 108), (140 + sd * 86, 122)]
        pygame.draw.lines(s, (60, 200, 255), False, [(x * S, y * S) for x, y in pts], max(1, S // 2 + 1))
        # bobina de energía en la punta
        cx, cy = 140 + sd * 118, 60
        pygame.draw.circle(s, (16, 24, 40), (cx * S, cy * S), int(15 * S))
        pygame.draw.circle(s, (60, 80, 110), (cx * S, cy * S), int(12 * S))
        for r_, c_ in ((9, (36, 150, 200)), (6.5, (80, 220, 255)), (3.4, (230, 252, 255))):
            pygame.draw.circle(s, c_, (cx * S, cy * S), int(r_ * S))
        for a in range(0, 360, 60):
            ra = math.radians(a)
            pygame.draw.line(s, (200, 240, 255), (cx * S, cy * S), ((cx + math.cos(ra) * 12) * S, (cy + math.sin(ra) * 12) * S), max(1, S // 3))
    canopy(s, S, (140, 144), 16, 62, (70, 190, 240))
    for x in (-14, 14):
        nozzle(s, S, (140 + x, 30), 6, (110, 220, 255))
    return _fin(s, W, H)


def _titan():
    """Cañonero acorazado: casco rojo oscuro con costillas, núcleo de reactor en el centro y dos motores."""
    W, H = 340, 240
    s, S = _surf(W, H)
    outline = [(170, 236), (210, 190), (330, 110), (336, 60), (260, 30), (170, 48), (80, 30), (4, 60), (10, 110), (130, 190)]
    plate(s, S, outline, (58, 28, 36), 2.4, top=(112, 56, 68), seam=(10, 6, 10))
    plate(s, S, [(170, 224), (206, 186), (318, 110), (324, 66), (258, 40), (170, 58), (82, 40), (16, 66), (22, 110), (134, 186)], (78, 36, 46), 1.8, top=(132, 66, 78), seam=(230, 60, 70))
    for sd in (-1, 1):
        for k in range(6):
            x0 = 170 + sd * (30 + k * 24)
            plate(s, S, [(x0, 70 + k * 6), (x0 + sd * 14, 100 + k * 8), (x0, 130 + k * 4)], (44, 20, 26), 0.8, seam=(14, 8, 12))
        pygame.draw.line(s, (230, 60, 70), ((170 + sd * 14) * S, 210 * S), ((170 + sd * 150) * S, 100 * S), 3)
        pygame.draw.line(s, (120, 30, 40), ((170 + sd * 18) * S, 208 * S), ((170 + sd * 146) * S, 104 * S), 1)
        # cañones laterales
        plate(s, S, [(170 + sd * 128, 70), (170 + sd * 140, 70), (170 + sd * 140, 36), (170 + sd * 128, 36)], (52, 54, 62), 0.8)
    # núcleo del reactor
    pygame.draw.circle(s, (12, 8, 12), (170 * S, 120 * S), int((44 * S) / 2 + 8 * S / 2 + 6))
    for r_, c_ in ((48, (60, 30, 36)), (40, (110, 24, 40)), (32, (190, 40, 56)), (22, (255, 100, 80)), (11, (255, 232, 200))):
        pygame.draw.circle(s, c_, (170 * S, 120 * S), int(r_ * S / 2.2))
    for a in range(0, 360, 30):
        ra = math.radians(a)
        pygame.draw.line(s, (40, 16, 22), (170 * S + math.cos(ra) * 14 * S, 120 * S + math.sin(ra) * 14 * S), (170 * S + math.cos(ra) * 24 * S, 120 * S + math.sin(ra) * 24 * S), max(1, S))
    for x in (92, 248):
        nozzle(s, S, (x, 50), 8, (255, 150, 70))
    canopy(s, S, (170, 190), 14, 36, (80, 170, 220))
    lights(s, S, [(30, 90), (310, 90), (170, 70)], (255, 70, 60), 1.2)
    return _fin(s, W, H)
