"""Dron de ataque (cuadricóptero) del modo tanque: casco gris metálico con brazos de carbono, motores, cámara roja y luces de posición.
El cuerpo se dibuja una vez en alta resolución; las hélices (borrosas y girando) se dibujan en cada cuadro sobre los cuatro motores."""
import math
import pygame

SW, SH = 520, 300               # tamaño del sprite (supersampleado al doble al construirlo)
MOTORS = ((-215, -78), (215, -78), (-170, 80), (170, 80))     # posición de los 4 motores respecto del centro (vista 3/4 desde arriba)


def make_drone_sprite():
    S = 2
    w, h = SW * S, SH * S
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2 + 8 * S

    def P(x, y):
        return (cx + x * S, cy + y * S)

    def poly(col, pts, width=0):
        pygame.draw.polygon(s, col, [P(*p) for p in pts], width)

    def ell(col, x, y, rw, rh, width=0):
        pygame.draw.ellipse(s, col, (cx + (x - rw) * S, cy + (y - rh) * S, 2 * rw * S, 2 * rh * S), width)

    ell((0, 0, 0, 60), 0, 118, 190, 20)                                                   # sombra suave
    for sx_ in (-1, 1):                                                                   # patas de aterrizaje
        pygame.draw.line(s, (26, 30, 34), P(sx_ * 46, 36), P(sx_ * 78, 92), 9 * S)
        pygame.draw.line(s, (60, 66, 74), P(sx_ * 46, 34), P(sx_ * 76, 90), 4 * S)
        pygame.draw.line(s, (26, 30, 34), P(sx_ * 62, 94), P(sx_ * 96, 94), 8 * S)
    for mx, my in MOTORS:                                                                 # brazos de carbono
        tx, ty = mx * 0.82, my * 0.82
        sgn = 1 if mx > 0 else -1
        poly((22, 26, 30), [(0, -10), (tx, ty - 11), (tx, ty + 11), (0, 14)])
        poly((52, 58, 66), [(0, -10), (tx, ty - 11), (tx, ty - 5), (0, -2)])
        pygame.draw.line(s, (92, 100, 112), P(sgn * 20, -9), P(tx, ty - 10), 2 * S)
    for mx, my in MOTORS:                                                                 # motores
        ell((14, 16, 18), mx, my + 10, 38, 17)
        ell((40, 46, 54), mx, my + 2, 38, 17)
        ell((84, 92, 104), mx, my - 4, 30, 12)
        ell((130, 140, 156), mx - 8, my - 6, 12, 4)
        ell((18, 20, 24), mx, my - 4, 7, 3)
    ell((16, 18, 22), 0, 12, 112, 56)                                                     # cuerpo
    ell((44, 50, 60), 0, 0, 112, 56)
    ell((72, 80, 94), 0, -8, 98, 44)
    ell((104, 114, 130), -12, -16, 66, 24)
    ell((150, 162, 182), -26, -22, 34, 9)
    poly((38, 44, 54), [(-70, 6), (70, 6), (92, 24), (-92, 24)])                          # panel inferior
    pygame.draw.ellipse(s, (22, 26, 32), (cx - 100 * S, cy - 50 * S, 200 * S, 100 * S), 3 * S)
    for k in (-1, 1):                                                                     # rejillas de ventilación
        for i in range(4):
            pygame.draw.line(s, (30, 34, 42), P(k * (38 + i * 11), -2), P(k * (34 + i * 11), 14), 2 * S)
    ell((12, 14, 18), 0, 34, 34, 18)                                                      # cámara (cardán)
    ell((40, 44, 52), 0, 32, 30, 15)
    ell((20, 22, 26), 0, 34, 20, 10)
    ell((170, 24, 26), 0, 34, 13, 6)
    ell((255, 120, 110), -3, 32, 6, 2)
    ell((230, 60, 60), -92, 6, 7, 5)                                                      # luces de posición
    ell((70, 255, 130), 92, 6, 7, 5)
    return pygame.transform.smoothscale(s, (SW, SH)).convert_alpha()


def draw_drone(cv, sprite, sx, sy, u, t, rot, glow_fn):
    """Dibuja el dron centrado en (sx, sy); u = tamaño en pantalla de una unidad de mundo."""
    w = max(20, int(u * 4.4))
    h = int(w * SH / SW)
    spr = pygame.transform.smoothscale(sprite, (w, h)) if w != SW else sprite
    cv.blit(spr, (sx - w // 2, sy - h // 2))
    k = w / SW
    cx, cy = sx, sy + 8 * k
    for i, (mx, my) in enumerate(MOTORS):
        px, py = cx + mx * k, cy + (my - 4) * k
        rw, rh = 78 * k, 24 * k
        disc = pygame.Surface((int(rw * 2) + 4, int(rh * 2) + 4), pygame.SRCALPHA)
        c0, c1 = disc.get_width() // 2, disc.get_height() // 2
        pygame.draw.ellipse(disc, (210, 220, 235, 46), (c0 - rw, c1 - rh, rw * 2, rh * 2))
        pygame.draw.ellipse(disc, (230, 238, 250, 90), (c0 - rw, c1 - rh, rw * 2, rh * 2), max(1, int(2 * k)))
        for b in range(2):
            a = rot * (1.0 if i % 2 else -1.0) + b * math.pi / 2 + i
            bx, by = math.cos(a) * rw, math.sin(a) * rh
            pygame.draw.line(disc, (236, 242, 252, 190), (c0 - bx, c1 - by), (c0 + bx, c1 + by), max(2, int(5 * k)))
        cv.blit(disc, (px - c0, py - c1))
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    glow_fn(cv, sx, cy + 34 * k, int(46 * k) + 8, (255, 60, 50), 0.35 + 0.35 * pulse)
    if int(t * 2.5) % 2 == 0:
        glow_fn(cv, cx + 92 * k, cy + 6 * k, int(18 * k) + 6, (70, 255, 130), 0.7)
        glow_fn(cv, cx - 92 * k, cy + 6 * k, int(18 * k) + 6, (255, 70, 70), 0.7)
