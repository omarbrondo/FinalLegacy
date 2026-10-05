"""Sprites procedurales: naves, soldados cenitales, cazas, nubes, coberturas."""
import math
import pygame
import random
from .common import shade


def make_ship(wd, ln, hull, deck, acc, fore_static=True):
    S = 3
    w, l = wd * S, ln * S
    s = pygame.Surface((w, l), pygame.SRCALPHA)
    hp = [(w * .5, 0), (w * .86, l * .22), (w * .95, l * .55), (w * .88, l * .93), (w * .7, l), (w * .3, l),
          (w * .12, l * .93), (w * .05, l * .55), (w * .14, l * .22)]
    pygame.draw.polygon(s, shade(hull, -45), hp)
    inner = [((px - w / 2) * .78 + w / 2, (py - l / 2) * .92 + l / 2) for px, py in hp]
    pygame.draw.polygon(s, deck, inner)
    pygame.draw.line(s, shade(deck, 25), (w * .5, l * .05), (w * .5, l * .95), max(1, S))
    pygame.draw.polygon(s, acc, [(w * .5, l * .02), (w * .62, l * .13), (w * .38, l * .13)])
    pygame.draw.rect(s, shade(hull, -5), (w * .3, l * .42, w * .4, l * .26), border_radius=S * 2)
    pygame.draw.rect(s, shade(hull, 35), (w * .36, l * .45, w * .28, l * .12), border_radius=S)
    for k in range(3):
        pygame.draw.rect(s, (250, 230, 140), (w * (.4 + k * .08), l * .47, w * .04, l * .03))
    pygame.draw.ellipse(s, shade(hull, -50), (w * .38, l * .6, w * .24, l * .1))
    pygame.draw.ellipse(s, acc, (w * .4, l * .62, w * .2, l * .05))
    pygame.draw.line(s, shade(hull, 60), (w * .5, l * .42), (w * .5, l * .3), max(1, S))
    for cy_ in ([l * .82] + ([l * .24] if fore_static else [])):
        pygame.draw.circle(s, shade(hull, -30), (int(w * .5), int(cy_)), int(w * .15))
        pygame.draw.circle(s, shade(hull, 25), (int(w * .5), int(cy_)), int(w * .1))
        for dx in (-.05, .05):
            pygame.draw.line(s, shade(hull, -60), (w * (.5 + dx), cy_), (w * (.5 + dx), cy_ - l * .13), S + 1)
    return pygame.transform.smoothscale(s, (wd, ln))


def make_sub(wd, ln):
    """Submarino visto desde arriba, proa al norte."""
    S = 3
    w, l = wd * S, ln * S
    s = pygame.Surface((w, l), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (26, 40, 48), (0, 0, w, l))
    pygame.draw.ellipse(s, (52, 78, 88), (w * .08, l * .03, w * .84, l * .94))
    pygame.draw.ellipse(s, (70, 100, 110), (w * .3, l * .06, w * .22, l * .84))
    for k in range(6):
        pygame.draw.line(s, (36, 56, 64), (w * .12, l * (.18 + k * .12)), (w * .88, l * (.18 + k * .12)), 2)
    pygame.draw.rect(s, (34, 52, 60), (w * .3, l * .36, w * .4, l * .2), border_radius=S * 3)
    pygame.draw.rect(s, (84, 116, 126), (w * .35, l * .39, w * .3, l * .14), border_radius=S * 2)
    pygame.draw.line(s, (20, 28, 32), (w * .5, l * .39), (w * .5, l * .28), S + 1)
    pygame.draw.circle(s, (230, 70, 56), (int(w * .5), int(l * .27)), S + 1)
    pygame.draw.polygon(s, (30, 46, 54), [(w * .5, l * .93), (w * .08, l * 1.0), (w * .92, l * 1.0)])
    return pygame.transform.smoothscale(s, (wd, ln))


def make_cargo(wd, ln):
    """Carguero aliado (convoy) visto desde arriba, proa al norte."""
    S = 3
    w, l = wd * S, ln * S
    s = pygame.Surface((w, l), pygame.SRCALPHA)
    hp = [(w * .5, 0), (w * .88, l * .14), (w * .94, l * .5), (w * .9, l * .97), (w * .1, l * .97), (w * .06, l * .5), (w * .12, l * .14)]
    pygame.draw.polygon(s, (36, 70, 56), hp)
    inner = [((px - w / 2) * .8 + w / 2, (py - l / 2) * .94 + l / 2) for px, py in hp]
    pygame.draw.polygon(s, (92, 120, 104), inner)
    cols = [(196, 84, 62), (70, 126, 196), (226, 184, 66), (150, 60, 60), (80, 160, 120)]
    rnd = random.Random(9)
    for row in range(5):
        for col in range(2):
            x0 = w * (.2 + col * .31)
            y0 = l * (.2 + row * .125)
            pygame.draw.rect(s, rnd.choice(cols), (x0, y0, w * .28, l * .1))
            pygame.draw.rect(s, (30, 34, 36), (x0, y0, w * .28, l * .1), 1)
    pygame.draw.rect(s, (236, 238, 240), (w * .22, l * .84, w * .56, l * .11), border_radius=S)
    pygame.draw.rect(s, (90, 150, 220), (w * .26, l * .86, w * .48, l * .035))
    pygame.draw.circle(s, (60, 200, 90), (int(w * .5), int(l * .04)), S + 1)
    return pygame.transform.smoothscale(s, (wd, ln))


def make_battleship(wd, ln, hull=(46, 50, 60), deck=(88, 94, 108), acc=(226, 64, 52)):
    """Acorazado visto desde arriba, proa al norte (las torres giratorias se dibujan aparte)."""
    S = 3
    w, l = wd * S, ln * S
    s = pygame.Surface((w, l), pygame.SRCALPHA)

    def P(fx, fy):
        return (w * fx, l * fy)

    outline = [(.5, 0), (.70, .07), (.86, .20), (.93, .40), (.93, .80), (.86, .95), (.70, 1.0), (.30, 1.0), (.14, .95),
               (.07, .80), (.07, .40), (.14, .20), (.30, .07)]
    pygame.draw.polygon(s, shade(hull, -22), [P(*q) for q in outline])
    pygame.draw.polygon(s, hull, [P(.5 + (x - .5) * .96, .5 + (y - .5) * .985) for x, y in outline])
    inner = [(.5, .035), (.66, .09), (.80, .21), (.855, .40), (.855, .80), (.80, .93), (.66, .975), (.34, .975), (.20, .93),
             (.145, .80), (.145, .40), (.20, .21), (.34, .09)]
    pygame.draw.polygon(s, deck, [P(*q) for q in inner])
    pygame.draw.polygon(s, shade(deck, 26), [P(*q) for q in inner], max(1, S))
    for k in range(6, 33):
        yy = .05 + k * .028
        if yy < .97:
            pygame.draw.line(s, shade(deck, -14), P(.17, yy), P(.83, yy), 1)
    pygame.draw.line(s, shade(deck, 22), P(.5, .04), P(.5, .97), max(1, S // 2))
    for sd in (-1, 1):
        pygame.draw.line(s, acc, P(.5 + sd * .20, .13), P(.5 + sd * .33, .30), max(2, S * 2))
        pygame.draw.line(s, acc, P(.5 + sd * .18, .16), P(.5 + sd * .31, .33), max(2, S * 2))
    for fy, rr in ((.175, .20), (.307, .20), (.815, .165)):
        pygame.draw.circle(s, (20, 22, 28), P(.5, fy), int(w * (rr + .03)))
        pygame.draw.circle(s, (48, 52, 62), P(.5, fy), int(w * rr))
        pygame.draw.circle(s, shade((48, 52, 62), 22), P(.5, fy), int(w * rr), max(1, S))
    pygame.draw.rect(s, (22, 24, 30), (w * .27, l * .40, w * .46, l * .24), border_radius=S * 3)
    pygame.draw.rect(s, (66, 72, 86), (w * .29, l * .415, w * .42, l * .21), border_radius=S * 2)
    pygame.draw.rect(s, (82, 90, 106), (w * .34, l * .44, w * .32, l * .13), border_radius=S * 2)
    for k in range(6):
        pygame.draw.rect(s, (130, 220, 240), (w * (.355 + k * .048), l * .452, w * .032, l * .016))
        pygame.draw.rect(s, (130, 220, 240), (w * (.355 + k * .048), l * .50, w * .032, l * .016))
    pygame.draw.rect(s, (96, 104, 120), (w * .43, l * .47, w * .14, l * .06), border_radius=S)
    for sd in (-1, 1):
        pygame.draw.rect(s, (30, 32, 38), (w * (.5 + sd * .17 - .07), l * .60, w * .14, l * .075), border_radius=S * 2)
        pygame.draw.ellipse(s, (8, 8, 10), (w * (.5 + sd * .17 - .055), l * .605, w * .11, l * .035))
        pygame.draw.rect(s, shade(acc, -40), (w * (.5 + sd * .17 - .07), l * .605 + l * .06, w * .14, l * .012))
    pygame.draw.rect(s, (26, 28, 34), (w * .27, l * .68, w * .46, l * .095), border_radius=S)
    for r_ in range(3):
        for c_ in range(8):
            pygame.draw.rect(s, (12, 14, 18), (w * (.295 + c_ * .052), l * (.69 + r_ * .028), w * .04, l * .02))
            pygame.draw.rect(s, shade(acc, -20), (w * (.295 + c_ * .052), l * (.69 + r_ * .028), w * .04, l * .02), 1)
    for sd in (-1, 1):
        for fy in (.37, .74):
            pygame.draw.circle(s, (30, 32, 38), P(.5 + sd * .33, fy), int(w * .045))
            pygame.draw.circle(s, (120, 128, 142), P(.5 + sd * .33, fy), int(w * .028))
            pygame.draw.line(s, (20, 22, 26), P(.5 + sd * .33, fy), P(.5 + sd * .33, fy - .035), S)
    pygame.draw.circle(s, (60, 64, 72), P(.5, .905), int(w * .115))
    pygame.draw.circle(s, (240, 200, 60), P(.5, .905), int(w * .115), max(2, S))
    pygame.draw.line(s, (240, 200, 60), P(.45, .885), P(.45, .925), max(2, S))
    pygame.draw.line(s, (240, 200, 60), P(.55, .885), P(.55, .925), max(2, S))
    pygame.draw.line(s, (240, 200, 60), P(.45, .905), P(.55, .905), max(2, S))
    for sd in (-1, 1):
        for fy in (.12, .30, .52, .70, .88):
            pygame.draw.circle(s, (255, 70, 60), P(.5 + sd * .43, fy), max(2, S))
    return pygame.transform.smoothscale(s, (wd, ln))


def make_turret(r, col):
    S = 3
    size = int(r * 6)
    s = pygame.Surface((size * S, size * S), pygame.SRCALPHA)
    c = size * S // 2
    for dx in (-.4, .4):
        pygame.draw.line(s, shade(col, -70), (c + dx * r * S, c), (c + dx * r * S, c - 2.7 * r * S), 4 * S // 2)
    pygame.draw.circle(s, shade(col, -35), (c, c), int(r * S * 1.15))
    pygame.draw.circle(s, shade(col, 30), (c, c), int(r * S * .8))
    pygame.draw.circle(s, shade(col, 70), (c - r * S // 4, c - r * S // 4), int(r * S * .3))
    return pygame.transform.smoothscale(s, (size, size))


ENEMY_TYPES = {
    'rifle': dict(hp=4, speed=58, range=280, dmg=5, rate=(1.1, 1.9), pts=100),
    'mg': dict(hp=7, speed=34, range=360, dmg=4, rate=(2.2, 3.2), pts=200),
    'gren': dict(hp=4, speed=46, range=380, dmg=0, rate=(4.8, 6.8), pts=150),
    'sniper': dict(hp=3, speed=24, range=620, dmg=16, rate=(3.6, 5.2), pts=250),
    'dog': dict(hp=2, speed=150, range=40, dmg=7, rate=(0.9, 1.2), pts=120),
}


TEAM_COL = {
    'p': dict(uni=(72, 114, 102), vest=(46, 76, 70), helm=(86, 132, 114), trim=(255, 214, 90)),
    'e': dict(uni=(138, 74, 62), vest=(92, 50, 44), helm=(154, 88, 68), trim=(36, 32, 32)),
    'a': dict(uni=(160, 138, 88), vest=(104, 88, 58), helm=(184, 160, 104), trim=(110, 190, 255)),
}


def make_soldier_frames(kind, team):
    """4 cuadros de caminata de un soldado visto desde arriba, mirando al norte."""
    S, N = 4, 56
    C = N * S // 2
    col = TEAM_COL[team]
    skin, dark, steel = (226, 188, 154), (30, 30, 34), (44, 46, 52)
    frames = []

    def rc(s, c, x, y, w, h, r=0):
        pygame.draw.rect(s, c, (C + x * S, C + y * S, w * S, h * S), border_radius=int(r * S))

    def el(s, c, x, y, w, h):
        pygame.draw.ellipse(s, c, (C + x * S, C + y * S, w * S, h * S))

    def ci(s, c, x, y, r):
        pygame.draw.circle(s, c, (int(C + x * S), int(C + y * S)), max(1, int(r * S)))

    def ln(s, c, x0, y0, x1, y1, w):
        pygame.draw.line(s, c, (C + x0 * S, C + y0 * S), (C + x1 * S, C + y1 * S), max(1, int(w * S)))

    for sw in (0, 9, 0, -9):
        s = pygame.Surface((N * S, N * S), pygame.SRCALPHA)
        k = sw * 0.45
        for side, off in ((-1, k), (1, -k)):
            ln(s, shade(col['uni'], -35), side * 4.5, 2, side * 4.5, 5 + off, 4.2)
            el(s, dark, side * 4.5 - 2.9, 3.5 + off, 5.8, 9)
            el(s, (70, 66, 62), side * 4.5 - 2.2, 4.2 + off, 4.4, 4)
        rc(s, shade(col['vest'], -25), -7.5, 2.5, 15, 11, 3)
        rc(s, shade(col['vest'], 15), -7.5, 2.5, 15, 3, 2)
        if kind == 'mg':
            rc(s, (88, 96, 70), 6, 4, 6, 9, 1)
            rc(s, (122, 130, 98), 6, 4, 6, 2, 1)
        elif kind == 'gren':
            for px in (-6.5, 2.5):
                rc(s, shade(col['vest'], -10), px, 8, 4, 6, 1)
                ci(s, (70, 84, 56), px + 2, 9, 1.5)
        el(s, shade(col['uni'], -30), -10.4, -6.2, 20.8, 15)
        el(s, col['uni'], -9.6, -5.6, 19.2, 13.4)
        el(s, col['vest'], -7.4, -4.4, 14.8, 10.4)
        for px in (-5.5, -1.6, 2.4):
            rc(s, shade(col['vest'], -35), px, -2.8, 3.2, 3.6, 0.7)
            rc(s, shade(col['vest'], 25), px, -2.8, 3.2, 0.9, 0.5)
        if kind == 'mg':
            for i in range(5):
                rc(s, (214, 178, 70), 2.5 + i * 0.9, -9 + i * 1.5, 1.6, 1.8, 0.4)
            ln(s, (150, 150, 156), -4.4, -22, -7.4, -16.5, 0.9)
            ln(s, (150, 150, 156), 5.0, -22, 8.0, -16.5, 0.9)
            rc(s, steel, -1.6, -31, 3.2, 20, 0.8)
            rc(s, dark, -2.6, -22, 5.2, 4, 1)
            rc(s, (110, 76, 48), -2.2, -9, 4.4, 8, 1.4)
            rc(s, (84, 88, 94), -3.6, -17, 7.2, 3.2, 1)
        elif kind == 'gren':
            rc(s, steel, -0.5, -22, 2.2, 12, 0.6)
            rc(s, dark, -1.8, -14, 4.6, 7, 1)
            rc(s, (110, 76, 48), -1.8, -8, 4.2, 6, 1.2)
            rc(s, dark, -0.9, -12, 2.6, 5.5, 0.6)
        else:
            rc(s, steel, -0.4, -29, 1.9, 17, 0.5)
            rc(s, dark, -1.8, -17, 4.6, 9, 1)
            rc(s, (110, 76, 48), -2.0, -9, 4.6, 8, 1.6)
            rc(s, dark, -1.0, -13.5, 2.6, 5.5, 0.6)
            ci(s, dark, 0.5, -29.6, 0.9)
        hand_l = (-3.4, -15) if kind != 'gren' else (-7.4, -11.5)
        hand_r = (3.4, -6.6)
        ln(s, shade(col['uni'], -25), -8.4, -2.4, hand_l[0], hand_l[1], 4.4)
        ln(s, shade(col['uni'], -25), 8.4, -2.4, hand_r[0], hand_r[1], 4.4)
        ci(s, skin, hand_l[0], hand_l[1], 2.3)
        ci(s, skin, hand_r[0], hand_r[1], 2.3)
        if kind == 'gren':
            ci(s, (60, 76, 50), hand_l[0] - 0.3, hand_l[1] - 1.2, 2.8)
            ci(s, (96, 112, 78), hand_l[0] - 1.0, hand_l[1] - 2.0, 1.1)
            ln(s, (190, 190, 196), hand_l[0] + 1.2, hand_l[1] - 3.6, hand_l[0] + 2.8, hand_l[1] - 1.6, 0.7)
        ci(s, shade(col['helm'], -55), 0, -1.4, 6.5)
        ci(s, col['helm'], 0, -1.6, 5.7)
        ci(s, shade(col['helm'], 38), -1.6, -3.2, 2.5)
        pygame.draw.arc(s, shade(col['helm'], -70), (C - 5.7 * S, C - 7.3 * S, 11.4 * S, 11.4 * S), 0, 6.3, int(S * 0.7))
        for cx_, cy_, cr in ((-2.4, 0.6, 1.5), (2.2, -0.4, 1.3), (0.4, 2.6, 1.1), (3.0, -3.0, 0.9)):
            ci(s, shade(col['helm'], -34), cx_, cy_, cr)
        rc(s, col['trim'], -5.4, -2.2, 10.8, 1.3, 0.5)
        for side in (-1, 1):
            rc(s, col['trim'], side * 8.6 - 1.6, -4.4, 3.2, 3.6, 0.8)
        el(s, skin, -2.6, -8.1, 5.2, 2.6)
        rc(s, (40, 60, 80), -3.0, -7.6, 6.0, 1.3, 0.5)
        frames.append(pygame.transform.smoothscale(s, (84, 84)))
    return frames


def draw_cover(surf, c):
    x, y, r, kind = int(c['x']), int(c['y']), c['r'], c['kind']
    rnd = random.Random(c['seed'])
    sh = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
    pygame.draw.circle(sh, (0, 0, 0, 70), (r * 2 + 5, r * 2 + 7), int(r * 1.05))
    surf.blit(sh, (x - r * 2, y - r * 2))
    if kind == 'sandbag':
        pygame.draw.circle(surf, (118, 98, 62), (x, y), r)
        for ring, rad, n in ((0, r - 5, 11), (1, r - 13, 7)):
            for i in range(n):
                a = 6.2832 * i / n + ring * 0.4 + rnd.uniform(-.06, .06)
                bx, by = x + math.cos(a) * rad, y + math.sin(a) * rad
                pygame.draw.circle(surf, (150, 126, 84), (int(bx), int(by)), 7 - ring)
                pygame.draw.circle(surf, (196, 172, 120), (int(bx - 1), int(by - 2)), 4 - ring)
                pygame.draw.circle(surf, (120, 100, 66), (int(bx), int(by)), 7 - ring, 1)
        pygame.draw.circle(surf, (96, 80, 52), (x, y), 5)
    elif kind == 'rock':
        pts = [(x + math.cos(a) * r * rnd.uniform(.8, 1.1), y + math.sin(a) * r * rnd.uniform(.8, 1.1))
               for a in [6.2832 * i / 9 for i in range(9)]]
        pygame.draw.polygon(surf, (84, 88, 92), pts)
        pygame.draw.polygon(surf, (126, 130, 132), [(px * .8 + x * .2 - 3, py * .8 + y * .2 - 3) for px, py in pts])
        pygame.draw.polygon(surf, (160, 164, 164), [(px * .45 + x * .55 - 5, py * .45 + y * .55 - 5) for px, py in pts])
        pygame.draw.polygon(surf, (58, 62, 66), pts, 2)
    else:
        for ox, oy in ((-9, -8), (7, 6)):
            bx, by = x + ox, y + oy
            pygame.draw.rect(surf, (88, 62, 36), (bx - 15, by - 15, 30, 30), border_radius=3)
            pygame.draw.rect(surf, (150, 108, 62), (bx - 13, by - 13, 26, 26), border_radius=2)
            for k in (-8, 0, 8):
                pygame.draw.line(surf, (112, 80, 46), (bx - 13, by + k), (bx + 13, by + k), 2)
            pygame.draw.line(surf, (88, 62, 36), (bx - 13, by - 13), (bx + 13, by + 13), 3)
            pygame.draw.line(surf, (88, 62, 36), (bx + 13, by - 13), (bx - 13, by + 13), 3)


def make_f16(body, dark, accent, scale=0.9):
    """F-16 visto desde arriba, morro al norte."""
    S, WU, HU = 4, 88, 96
    s = pygame.Surface((WU * S, HU * S), pygame.SRCALPHA)
    cx, cy = WU * S / 2, HU * S / 2

    def P(x, y):
        return (cx + x * S, cy + y * S)

    def poly(c, pts, mirror=False, w=0):
        pygame.draw.polygon(s, c, [P(x, y) for x, y in pts], w)
        if mirror:
            pygame.draw.polygon(s, c, [P(-x, y) for x, y in pts], w)

    def line(c, a, b, w, mirror=False):
        pygame.draw.line(s, c, P(*a), P(*b), max(1, int(w * S)))
        if mirror:
            pygame.draw.line(s, c, P(-a[0], a[1]), P(-b[0], b[1]), max(1, int(w * S)))

    poly(shade(dark, -25), [(5, 25), (20, 41), (20, 46), (5, 39)], True)
    poly(dark, [(5, 26), (18, 40), (18, 43), (5, 37)], True)
    poly(shade(dark, -30), [(4, -5), (36, 20), (36, 28), (5, 25)], True)
    poly(dark, [(5, -2), (34, 20), (34, 26), (6, 23)], True)
    poly(shade(body, -8), [(5.5, 0), (31, 20), (31, 24), (6.5, 21)], True)
    line(shade(body, 28), (5, -4), (35, 20), 0.9, True)
    line(shade(dark, -40), (7, 6), (30, 22), 0.5, True)
    line((190, 194, 202), (36.2, 11), (36.2, 31), 1.7, True)
    poly((220, 60, 50), [(35.3, 7), (37.1, 7), (37.1, 12), (35.3, 12)], True)
    pygame.draw.circle(s, (240, 240, 244), P(22, 17), int(3.2 * S))
    pygame.draw.circle(s, accent, P(22, 17), int(2.2 * S))
    pygame.draw.circle(s, (240, 240, 244), P(22, 17), int(0.9 * S))
    pygame.draw.circle(s, (240, 240, 244), P(-22, 17), int(3.2 * S))
    pygame.draw.circle(s, accent, P(-22, 17), int(2.2 * S))
    pygame.draw.circle(s, (240, 240, 244), P(-22, 17), int(0.9 * S))
    poly(shade(dark, -35), [(0, -44), (2.4, -34), (4.8, -18), (6.6, -4), (7.4, 12), (6.6, 30), (5, 42), (0, 45)], True)
    poly(body, [(0, -42), (2, -33), (4, -17), (5.6, -4), (6.2, 12), (5.6, 30), (4, 41), (0, 43)], True)
    poly(shade(body, 22), [(0, -40), (1.2, -32), (2.4, -14), (3.2, 4), (3.4, 20), (2.6, 38), (0, 40)], True)
    for sx in (-1, 1):
        pygame.draw.ellipse(s, shade(dark, -45), (cx + (sx * 6.9 - 1.6) * S, cy - 2 * S, 3.2 * S, 15 * S))
        pygame.draw.ellipse(s, (22, 22, 26), (cx + (sx * 6.9 - 0.9) * S, cy - 1 * S, 1.8 * S, 4 * S))
    line(shade(body, -30), (0, 8), (0, 37), 0.7)
    for yy in (-8, 4, 16, 28):
        line(shade(body, -22), (-5.2, yy), (5.2, yy), 0.35)
    pygame.draw.ellipse(s, (16, 36, 66), (cx - 3.9 * S, cy - 33 * S, 7.8 * S, 20 * S))
    pygame.draw.ellipse(s, (36, 86, 142), (cx - 3.2 * S, cy - 32 * S, 6.4 * S, 18 * S))
    pygame.draw.ellipse(s, (120, 180, 232), (cx - 2.2 * S, cy - 31 * S, 3.2 * S, 11 * S))
    pygame.draw.line(s, (236, 246, 255), P(-1.2, -29), P(-1.2, -22), max(1, int(0.6 * S)))
    pygame.draw.circle(s, (34, 34, 40), P(0, 43.5), int(3.8 * S))
    pygame.draw.circle(s, (92, 92, 100), P(0, 43.5), int(3.8 * S), max(1, S // 2))
    pygame.draw.circle(s, (16, 16, 18), P(0, 43.5), int(2.4 * S))
    return pygame.transform.smoothscale(s, (int(WU * scale), int(HU * scale)))


def make_f117(accent, scale=0.9):
    """F-117 facetado visto desde arriba, morro al norte."""
    S, WU, HU = 4, 100, 96
    s = pygame.Surface((WU * S, HU * S), pygame.SRCALPHA)
    cx, cy = WU * S / 2, HU * S / 2

    def P(x, y):
        return (cx + x * S, cy + y * S)

    def poly(c, pts, mirror=0):
        pygame.draw.polygon(s, c, [P(x, y) for x, y in pts])
        if mirror:
            pygame.draw.polygon(s, shade(c, mirror), [P(-x, y) for x, y in pts])

    outline = [(0, -44), (9, -29), (42, 17), (32, 19), (26, 36), (13, 26), (0, 42)]
    poly((14, 15, 18), [(x * 1.03, y * 1.03 + (0.6 if y > 0 else -0.6)) for x, y in outline], 0)
    pygame.draw.polygon(s, (14, 15, 18), [P(-x * 1.03, y * 1.03 + (0.6 if y > 0 else -0.6)) for x, y in outline])
    poly((82, 86, 98), [(0, -44), (9, -29), (0, -12)], -14)
    poly((50, 53, 62), [(0, -12), (9, -29), (42, 17), (17, 8)], -12)
    poly((36, 38, 45), [(17, 8), (42, 17), (32, 19), (26, 36), (13, 26)], -10)
    poly((62, 66, 76), [(0, -12), (17, 8), (13, 26), (0, 42)], -16)
    for sx in (1, -1):
        pts = [P(sx * 9, -29), P(sx * 42, 17), P(sx * 32, 19), P(sx * 26, 36), P(sx * 13, 26), P(0, 42), P(0, -44)]
        pygame.draw.lines(s, shade(accent, -60), True, pts, max(1, S // 2))
        pygame.draw.line(s, shade((82, 86, 98), 30), P(sx * 9, -29), P(sx * 42, 17), max(1, int(S * 0.5)))
        pygame.draw.line(s, shade((50, 53, 62), -20), P(sx * 17, 8), P(sx * 42, 17), max(1, int(S * 0.4)))
        pygame.draw.rect(s, accent, (cx + (sx * 9.5 - 2.6) * S, cy + 31.2 * S, 5.2 * S, 1.6 * S))
    pygame.draw.polygon(s, (14, 28, 46), [P(0, -27), (P(4.2, -18)), P(0, -9), P(-4.2, -18)])
    pygame.draw.polygon(s, (52, 112, 170), [P(0, -25), P(3, -18), P(0, -11), P(-3, -18)])
    pygame.draw.polygon(s, (150, 206, 244), [P(-0.4, -23), P(1.6, -18), P(-0.4, -14)])
    return pygame.transform.smoothscale(s, (int(WU * scale), int(HU * scale)))


def make_cloud(seed):
    rnd = random.Random(seed)
    w, h = 260, 140
    S = 2
    puffs = [(rnd.uniform(52, w - 52), rnd.uniform(48, h - 40), rnd.uniform(26, 46)) for _ in range(11)]
    s = pygame.Surface((w * S, h * S), pygame.SRCALPHA)
    sh = pygame.Surface((w * S, h * S), pygame.SRCALPHA)
    for x, y, r in puffs:
        pygame.draw.circle(s, (170, 186, 212, 235), (x * S, (y + 9) * S), r * S)
        pygame.draw.circle(sh, (0, 14, 40, 255), (x * S, (y + 9) * S), r * S)
    for x, y, r in puffs:
        pygame.draw.circle(s, (230, 238, 250, 240), (x * S, y * S), r * S * .93)
    for x, y, r in puffs:
        pygame.draw.circle(s, (255, 255, 255, 245), ((x - r * .2) * S, (y - r * .3) * S), r * S * .62)
    return (pygame.transform.smoothscale(s, (w, h)).convert_alpha(),
            pygame.transform.smoothscale(sh, (w, h)).convert_alpha())


def make_shadow(surf):
    sh = surf.copy()
    sh.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return sh
