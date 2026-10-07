"""Constantes, utilidades matemáticas, helpers de dibujo y partículas."""
import math
import random

import pygame

from . import render_fx as fx

pygame.mixer.pre_init(22050, -16, 2, 512)
pygame.init()

W, H = 1100, 800
PLAYER_FEMALE = True          # la protagonista (y una aliada de cada dos) es mujer; poné False para volver al soldado de siempre
FEM_CHANCE = 0.4              # fracción de soldados enemigos que son mujeres


WORLD_W, WORLD_H = 4800, 3600


FPS = 60


SR = 22050


HZ = 590                      # horizonte en la escena de defensa


SKY_W = 640                   # ancho del skyline


WIN_WAVE = 6                  # oleadas para ganar


VMAX = 230.0                  # velocidad máx. del buque en el mapa (px/s)


BOSS_MOUNTS = (88, 52, -84)      # torres del acorazado (distancia al centro, + hacia la proa)


BOSS_NAMES = ('LEVIATAN', 'TIFON', 'COLOSO', 'ABISMO', 'TITAN', 'APOCALIPSIS')


SHIELD_R = 230                 # radio del escudo digital del jefe en el mapa
SHIELD_DPS_EDGE, SHIELD_DPS_CORE = 4.0, 13.0   # daño por segundo de la interferencia: en el borde del escudo / pegado al jefe


ANTENNA_ISLANDS = list(range(9))   # islas donde se puede desembarcar e instalar antena (índices de EXTRA_ISLANDS)


ARENA_R = 330                  # radio de la ciudad en la invasión de infantería


LAND_R = 560                   # radio de las islas de desembarco (la cámara sigue al soldado)


PLAYER_HP = 120.0              # vida del soldado


TK_HP = 140.0                  # armadura del tanque en el combate urbano


LANDING_ENEMIES = 12           # enemigos por desembarque


MAX_LANDING_ATTEMPTS = 3       # intentos máximos por isla


# (nombre, x, y, radio, semilla)
CITY_DEFS = [
    ("PUERTO BRONDO", 900, 800, 120, 11),
    ("NUEVA ESPERANZA", 3900, 900, 130, 22),
    ("BAHIA AZUL", 1000, 2800, 125, 33),
    ("FORT LEGACY", 3700, 2700, 135, 44),
]


# islas grandes donde se desembarca y se instalan antenas: (x, y, radio, semilla)
EXTRA_ISLANDS = [(2400, 1800, 150, 5), (420, 1800, 115, 6), (4400, 1800, 120, 7), (2400, 450, 135, 8),
                 (2400, 3150, 140, 9), (1750, 1250, 105, 12), (3050, 1300, 110, 16), (1700, 2450, 115, 13),
                 (3100, 2400, 105, 14)]


# puerto enemigo (asalto lateral estilo Metal Slug): (x, y, radio, semilla)
ENEMY_PORT = (3000, 1950, 110, 80)


# islotes decorativos (sin desembarco)
DECOR_ISLANDS = [(200, 300, 55, 50), (1500, 250, 45, 51), (3400, 300, 60, 52), (4600, 500, 50, 53), (250, 1200, 48, 54),
                 (4550, 1150, 52, 55), (1300, 1800, 40, 56), (3600, 1800, 44, 57), (300, 2500, 58, 58), (4500, 2450, 46, 59),
                 (2000, 3300, 50, 60), (2800, 2900, 42, 61), (1500, 3350, 38, 62), (4200, 3250, 55, 63), (2050, 700, 40, 64),
                 (2900, 700, 36, 65),
                 (1250, 1250, 60, 66), (850, 2150, 65, 67), (4000, 2200, 70, 68), (2400, 2550, 75, 69), (700, 3250, 50, 70),
                 (3750, 3400, 52, 71), (3800, 520, 48, 72), (1700, 3000, 55, 73), (3300, 3000, 60, 74), (2400, 1100, 70, 75)]


HELIPAD = DECOR_ISLANDS[16]       # isla con helipuerto y Blackhawk (1250, 1250)


# ------------------------------------------------------------------ utilidades
def clamp(v, a, b):
    return max(a, min(b, v))


def lerp(a, b, t):
    return a + (b - a) * t


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def vec(heading, length=1.0):
    """Rumbo en grados (0 = norte, horario) -> vector pantalla."""
    r = math.radians(heading)
    return math.sin(r) * length, -math.cos(r) * length


def bearing(dx, dy):
    return math.degrees(math.atan2(dx, -dy))


def angle_diff(a, b):
    return (b - a + 180) % 360 - 180


def shade(c, d):
    return (clamp(c[0] + d, 0, 255), clamp(c[1] + d, 0, 255), clamp(c[2] + d, 0, 255))


# ------------------------------------------------------------- caches gráficos
_circ = {}


_glow = {}


def draw_circ(dst, x, y, r, col, alpha, ring=0):
    r = max(2, int(r) // 2 * 2)
    key = (r, col, ring)
    s = _circ.get(key)
    if s is None:
        s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (r + 2, r + 2), r, ring)
        _circ[key] = s
    s.set_alpha(int(clamp(alpha, 0, 255)))
    dst.blit(s, (int(x) - r - 2, int(y) - r - 2))


def glow(dst, x, y, r, col, k=1.0):
    r = max(8, int(r) // 4 * 4)
    c = tuple(int(v * clamp(k, 0, 1)) // 16 * 16 for v in col)
    if c == (0, 0, 0):
        return
    key = (r, c)
    s = _glow.get(key)
    if s is None:
        s = fx.smooth_glow(r, c) if fx.np is not None else None
        if s is None:
            s = pygame.Surface((r * 2, r * 2))
            s.fill((0, 0, 0))
            for i in range(r, 0, -2):
                f = (1 - i / r) ** 2
                pygame.draw.circle(s, (int(c[0] * f), int(c[1] * f), int(c[2] * f)), (r, r), i)
        _glow[key] = s
    dst.blit(s, (int(x) - r, int(y) - r), special_flags=pygame.BLEND_RGB_ADD)


class Particles:
    def __init__(self):
        self.L = []

    def add(self, kind, x, y, vx=0.0, vy=0.0, life=1.0, r0=4.0, r1=10.0, col=(255, 255, 255), drag=0.0, grav=0.0):
        if len(self.L) < 900:
            self.L.append([kind, x, y, vx, vy, 0.0, life, r0, r1, col, drag, grav])

    def update(self, dt):
        out = []
        for p in self.L:
            p[5] += dt
            if p[5] < p[6]:
                p[1] += p[3] * dt
                p[2] += p[4] * dt
                if p[10]:
                    f = max(0.0, 1 - p[10] * dt)
                    p[3] *= f
                    p[4] *= f
                p[4] += p[11] * dt
                out.append(p)
        self.L = out

    def draw(self, dst, cx=0, cy=0):
        for kind, x, y, vx, vy, age, life, r0, r1, col, drag, grav in self.L:
            t = age / life
            r = lerp(r0, r1, t)
            sx, sy = int(x - cx), int(y - cy)
            if sx < -160 or sx > W + 160 or sy < -160 or sy > H + 160:
                continue
            if kind == 'smoke':
                if fx.np is not None:
                    draw_puff(dst, sx, sy, r, col, 175 * (1 - t) ** 1.3, int(life * 997) % 6)
                else:
                    draw_circ(dst, sx, sy, r, col, 150 * (1 - t) ** 1.3)
            elif kind == 'fire':
                draw_fire(dst, sx, sy, r, 1 - t, int(life * 997) % 3)
            elif kind == 'foam':
                draw_circ(dst, sx, sy, r, col, 110 * (1 - t))
            elif kind == 'glow':
                glow(dst, sx, sy, r, col, 1 - t)
            elif kind == 'ring':
                draw_circ(dst, sx, sy, r, col, 230 * (1 - t), 3)
            elif kind == 'spark':
                c = tuple(int(v * (1 - t)) for v in col)
                pygame.draw.line(dst, c, (sx, sy), (int(sx - vx * 0.04), int(sy - vy * 0.04)), 2)

    def explode(self, x, y, size=1.0, big=False):
        self.add('fire', x, y, life=0.55, r0=14 * size, r1=58 * size)
        self.add('glow', x, y, life=0.5, r0=24 * size, r1=84 * size, col=(255, 170, 70))
        self.add('glow', x, y, life=0.25, r0=10 * size, r1=40 * size, col=(255, 255, 220))
        self.add('ring', x, y, life=0.55, r0=6, r1=64 * size, col=(255, 220, 150))
        for _ in range(int((22 if big else 12) * size)):
            a = random.uniform(0, 6.28)
            s = random.uniform(60, 260) * size
            self.add('spark', x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.3, 0.8), col=(255, 200, 90),
                     drag=1.5)
        for _ in range(int((9 if big else 5) * size)):
            a = random.uniform(0, 6.28)
            s = random.uniform(10, 70) * size
            g = random.choice((50, 65, 80))
            self.add('smoke', x, y, math.cos(a) * s, math.sin(a) * s - 20, random.uniform(1.2, 2.6),
                     r0=8 * size, r1=26 * size, col=(g, g, g), drag=1.0)

    def splash(self, x, y, size=1.0):
        self.add('ring', x, y, life=0.8, r0=4, r1=48 * size, col=(220, 240, 255))
        for _ in range(int(14 * size)):
            a = random.uniform(0, 6.28)
            s = random.uniform(30, 150)
            self.add('foam', x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.4, 0.9), r0=3, r1=6,
                     col=(235, 248, 255), drag=2.2)


_puffs = {}
_fires = {}


def draw_puff(dst, x, y, r, col, alpha, variant):
    """Bocanada de humo suave y tintada (sprites generados una vez)."""
    rb = max(8, int(r) // 4 * 4)
    ck = (col[0] // 16, col[1] // 16, col[2] // 16)
    key = (variant, rb, ck)
    s = _puffs.get(key)
    if s is None:
        base = _puffs.get(('base', variant))
        if base is None:
            base = _puffs[('base', variant)] = fx.soft_blob_sprite(64, 11 + variant)
        s = pygame.transform.smoothscale(base, (rb * 2, rb * 2))
        s.fill((min(255, ck[0] * 16 + 8), min(255, ck[1] * 16 + 8), min(255, ck[2] * 16 + 8), 255), special_flags=pygame.BLEND_RGBA_MULT)
        _puffs[key] = s
    s.set_alpha(int(clamp(alpha, 0, 255)))
    dst.blit(s, (int(x) - rb, int(y) - rb))


def draw_fire(dst, x, y, r, k, variant):
    """Bola de fuego con degradado de calor (suma de color)."""
    rb = max(8, int(r) // 4 * 4)
    lv = int(clamp(k, 0, 1) * 7 + 0.5)
    if lv <= 0:
        return
    key = (rb, lv, variant)
    s = _fires.get(key)
    if s is None:
        s = fx.fireball_sprite(rb, lv / 7.0, variant)
        if s is None:
            return
        _fires[key] = s
    dst.blit(s, (int(x) - rb, int(y) - rb), special_flags=pygame.BLEND_RGB_ADD)


# ----------------------------------------------------------------- dibujo base
_phases = {}


def coast_r(r, seed, a, scale=1.0):
    """Radio exacto de la costa de una isla en el ángulo a (misma fórmula que el dibujo)."""
    ph = _phases.get(seed)
    if ph is None:
        rnd = random.Random(seed)
        ph = _phases[seed] = [rnd.uniform(0, 6.28) for _ in range(3)]
    return r * (1 + 0.13 * math.sin(2 * a + ph[0]) + 0.08 * math.sin(3 * a + ph[1])
                + 0.05 * math.sin(7 * a + ph[2])) * scale


def blob(cx, cy, r, seed, scale=1.0, n=40):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = coast_r(r, seed, a, scale)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts
