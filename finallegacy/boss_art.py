"""Siluetas de los jefes navales (uno distinto por oleada), vistas desde arriba con la proa al norte."""
import math
import pygame
from .common import shade
from .sprites import make_battleship

# tipo -> datos del jefe: nombre del tipo, torres (distancia al centro; + hacia la proa), radio de impacto,
# texto de combate y habilidad especial
BOSS_TYPES = [
    dict(key='clasico', label='ACORAZADO', mounts=(88, 52, -84), r=36, hint='3 baterías de misiles  |  Hundilo o te hunde', special=None),
    dict(key='portaaviones', label='PORTAAVIONES', mounts=(-96, -52), r=46, hint='Lanza cazas teledirigidos: derribalos a tiros', special='jets'),
    dict(key='minador', label='MINADOR', mounts=(70, -40), r=34, hint='Siembra minas: no las toques, dispará para quitarlas', special='mines'),
    dict(key='laser', label='ACORAZADO LÁSER', mounts=(-70,), r=34, hint='Carga un rayo: salí de la línea roja antes de que dispare', special='laser'),
    dict(key='blindado', label='ACORAZADO BLINDADO', mounts=(104, 66, -22, -88), r=40, hint='Blindaje frontal: atacalo por los costados y la popa', special='armor'),
    dict(key='fortaleza', label='FORTALEZA FLOTANTE', mounts=(92, 20, -86), r=42, hint='Cambia de fase: cazas, minas y rayo láser', special='all'),
]


def _hull(s, w, l, outline, hull, deck, deck_inset=0.04):
    P = lambda fx, fy: (w * fx, l * fy)
    pygame.draw.polygon(s, shade(hull, -24), [P(*q) for q in outline])
    cx = .5
    inner = [(cx + (x - cx) * (1 - deck_inset * 2.2), .5 + (y - .5) * (1 - deck_inset * .9)) for x, y in outline]
    pygame.draw.polygon(s, deck, [P(*q) for q in inner])
    pygame.draw.polygon(s, shade(deck, 24), [P(*q) for q in inner], 3)
    return P


def make_carrier(wd, ln):
    S = 3
    w, l = wd * S, ln * S
    s = pygame.Surface((w, l), pygame.SRCALPHA)
    outline = [(.5, 0), (.78, .05), (.96, .14), (.98, .86), (.9, 1.0), (.1, 1.0), (.02, .86), (.04, .14), (.22, .05)]
    P = _hull(s, w, l, outline, (58, 68, 82), (92, 100, 114), 0.03)
    # pista central y señales
    for k in range(18):
        yy = .08 + k * .05
        pygame.draw.rect(s, (236, 220, 130), (w * .495, l * yy, w * .01, l * .028))
    pygame.draw.line(s, (236, 236, 236), P(.30, .10), P(.30, .95), 2)
    pygame.draw.line(s, (236, 236, 236), P(.70, .10), P(.70, .95), 2)
    pygame.draw.polygon(s, (74, 82, 96), [P(.04, .45), P(.28, .30), P(.34, .34), P(.06, .62)])        # cubierta oblicua
    for k in range(5):
        pygame.draw.line(s, (236, 236, 236), P(.07 + k * .045, .58 - k * .045), P(.12 + k * .045, .50 - k * .043), 2)
    # catapultas y ascensores
    for fx in (.4, .6):
        pygame.draw.line(s, (40, 44, 52), P(fx, .1), P(fx, .3), 3)
    for fy in (.40, .62):
        pygame.draw.rect(s, (52, 58, 70), (w * .62, l * fy, w * .24, l * .09), border_radius=3)
        pygame.draw.rect(s, (120, 130, 146), (w * .62, l * fy, w * .24, l * .09), 2, border_radius=3)
    # isla (torre de mando) a estribor
    pygame.draw.rect(s, (34, 38, 46), (w * .78, l * .44, w * .16, l * .17), border_radius=4)
    pygame.draw.rect(s, (76, 84, 98), (w * .79, l * .45, w * .13, l * .15), border_radius=3)
    pygame.draw.rect(s, (130, 220, 240), (w * .80, l * .47, w * .11, l * .02))
    pygame.draw.circle(s, (230, 70, 60), P(.86, .50), 6)
    pygame.draw.line(s, (200, 204, 214), P(.86, .50), P(.86, .44), 2)
    # aviones estacionados en la popa
    for k in range(6):
        fx = .16 + k * .13
        fy = .84 + (k % 2) * .05
        pygame.draw.polygon(s, (40, 44, 52), [P(fx, fy - .035), P(fx + .035, fy + .02), P(fx - .035, fy + .02)])
        pygame.draw.line(s, (40, 44, 52), P(fx - .05, fy + .005), P(fx + .05, fy + .005), 3)
    for sd in (-1, 1):
        for fy in (.12, .30, .52, .70, .88):
            pygame.draw.circle(s, (255, 170, 60), P(.5 + sd * .46, fy), 3)
    return pygame.transform.smoothscale(s, (wd, ln))


def make_minelayer(wd, ln):
    S = 3
    w, l = wd * S, ln * S
    s = pygame.Surface((w, l), pygame.SRCALPHA)
    outline = [(.5, 0), (.66, .06), (.8, .2), (.84, .5), (.84, .9), (.72, 1.0), (.28, 1.0), (.16, .9), (.16, .5), (.2, .2), (.34, .06)]
    P = _hull(s, w, l, outline, (56, 70, 52), (104, 120, 92), 0.04)
    # puente delantero
    pygame.draw.rect(s, (30, 38, 30), (w * .3, l * .16, w * .4, l * .16), border_radius=5)
    pygame.draw.rect(s, (90, 104, 84), (w * .33, l * .18, w * .34, l * .12), border_radius=4)
    for k in range(5):
        pygame.draw.rect(s, (255, 210, 90), (w * (.36 + k * .055), l * .22, w * .035, l * .02))
    # grúas
    for fy in (.40, .50):
        pygame.draw.line(s, (220, 190, 70), P(.5, fy), P(.8, fy + .02), 4)
        pygame.draw.circle(s, (60, 66, 56), P(.5, fy), 6)
    # rampa trasera con minas
    pygame.draw.rect(s, (36, 44, 34), (w * .24, l * .58, w * .52, l * .36), border_radius=4)
    for r_ in range(5):
        for c_ in range(5):
            cx, cy = w * (.31 + c_ * .095), l * (.62 + r_ * .062)
            pygame.draw.circle(s, (24, 26, 28), (cx, cy), 8)
            pygame.draw.circle(s, (196, 70, 56), (cx, cy), 5)
            for a in range(8):
                ang = a * .785
                pygame.draw.line(s, (24, 26, 28), (cx, cy), (cx + math.cos(ang) * 10, cy + math.sin(ang) * 10), 2)
    for k in range(10):
        pygame.draw.rect(s, (236, 200, 50) if k % 2 else (36, 36, 36), (w * (.26 + k * .048), l * .955, w * .04, l * .02))
    return pygame.transform.smoothscale(s, (wd, ln))


def make_laser_ship(wd, ln):
    S = 3
    w, l = wd * S, ln * S
    base = make_battleship(wd * 2, ln * 2, (24, 52, 64), (58, 96, 112), (90, 230, 255))
    s = pygame.transform.smoothscale(base, (w, l)).convert_alpha()
    # cañón láser central: antena parabólica + conductos de energía
    pygame.draw.circle(s, (12, 20, 28), (w * .5, l * .32), w * .24)
    for k in range(4):
        pygame.draw.circle(s, (40 + k * 10, 120 + k * 22, 150 + k * 22), (w * .5, l * .32), w * (.22 - k * .045), max(2, S))
    pygame.draw.circle(s, (210, 250, 255), (w * .5, l * .32), w * .05)
    for sd in (-1, 1):
        pygame.draw.line(s, (90, 230, 255), (w * (.5 + sd * .2), l * .32), (w * (.5 + sd * .33), l * .6), 3)
        pygame.draw.line(s, (90, 230, 255), (w * (.5 + sd * .33), l * .6), (w * (.5 + sd * .33), l * .9), 3)
    pygame.draw.line(s, (90, 230, 255), (w * .5, l * .08), (w * .5, l * .21), 4)
    return pygame.transform.smoothscale(s, (wd, ln))


def make_armored(wd, ln):
    S = 3
    base = make_battleship(wd * 2, ln * 2, (84, 80, 66), (128, 120, 96), (222, 180, 70))
    w, l = wd * S, ln * S
    s = pygame.transform.smoothscale(base, (w, l)).convert_alpha()
    # placas blindadas en la proa (chevrones dorados) y a los costados
    for k in range(5):
        y0 = l * (.03 + k * .045)
        pygame.draw.polygon(s, (170, 140, 56), [(w * .5, y0), (w * (.78 - k * .02), y0 + l * .06), (w * (.78 - k * .02), y0 + l * .095), (w * .5, y0 + l * .035),
                                                (w * (.22 + k * .02), y0 + l * .095), (w * (.22 + k * .02), y0 + l * .06)])
        pygame.draw.polygon(s, (60, 52, 30), [(w * .5, y0), (w * (.78 - k * .02), y0 + l * .06), (w * (.78 - k * .02), y0 + l * .095), (w * .5, y0 + l * .035),
                                              (w * (.22 + k * .02), y0 + l * .095), (w * (.22 + k * .02), y0 + l * .06)], 2)
    for sd in (-1, 1):
        for k in range(8):
            pygame.draw.rect(s, (150, 124, 52), (w * (.5 + sd * .405 - .03), l * (.30 + k * .08), w * .06, l * .06), border_radius=3)
            pygame.draw.rect(s, (60, 52, 30), (w * (.5 + sd * .405 - .03), l * (.30 + k * .08), w * .06, l * .06), 2, border_radius=3)
    return pygame.transform.smoothscale(s, (wd, ln))


def make_fortress(wd, ln):
    S = 3
    base = make_battleship(wd * 2, ln * 2, (24, 20, 26), (52, 44, 54), (230, 40, 56))
    w, l = wd * S, ln * S
    s = pygame.transform.smoothscale(base, (w, l)).convert_alpha()
    # púas laterales
    for sd in (-1, 1):
        for k in range(9):
            y = l * (.12 + k * .095)
            x = w * (.5 + sd * .46)
            pygame.draw.polygon(s, (60, 52, 64), [(x, y), (x + sd * w * .08, y + l * .035), (x, y + l * .07)])
            pygame.draw.polygon(s, (230, 40, 56), [(x, y), (x + sd * w * .08, y + l * .035), (x, y + l * .07)], 2)
    # reactor central con brillo
    pygame.draw.circle(s, (14, 10, 16), (w * .5, l * .5), w * .2)
    pygame.draw.circle(s, (160, 24, 40), (w * .5, l * .5), w * .16)
    pygame.draw.circle(s, (255, 90, 80), (w * .5, l * .5), w * .1)
    pygame.draw.circle(s, (255, 230, 200), (w * .5, l * .5), w * .045)
    for a in range(6):
        ang = a * 1.047
        pygame.draw.line(s, (60, 52, 64), (w * .5, l * .5), (w * .5 + math.cos(ang) * w * .34, l * .5 + math.sin(ang) * w * .34), 4)
    # silos de misiles
    for r_ in range(2):
        for c_ in range(6):
            pygame.draw.rect(s, (14, 12, 16), (w * (.27 + c_ * .08), l * (.72 + r_ * .05), w * .06, l * .035), border_radius=3)
            pygame.draw.rect(s, (230, 40, 56), (w * (.27 + c_ * .08), l * (.72 + r_ * .05), w * .06, l * .035), 1, border_radius=3)
    return pygame.transform.smoothscale(s, (wd, ln))


def make_boss_sprite(btype, wd, ln):
    return [lambda a, b: make_battleship(a, b), make_carrier, make_minelayer, make_laser_ship, make_armored, make_fortress][btype](wd, ln)
