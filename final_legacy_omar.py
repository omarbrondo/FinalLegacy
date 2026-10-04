#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FINAL LEGACY  -  Edición Omar Brondo  (remake mejorado)
Requisitos:  pip install pygame      Ejecutar:  python final_legacy_omar.py

Todo (gráficos y sonido) se genera por código: no necesita archivos externos.
"""
import array
import math
import os
import random
import sys

import pygame

pygame.mixer.pre_init(22050, -16, 2, 512)
pygame.init()

W, H = 1100, 800
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


# ------------------------------------------------------------ síntesis de audio
def osc(wave, p, duty=0.5):
    if wave == 'square':
        return 1.0 if p < duty else -1.0
    if wave == 'saw':
        return 2 * p - 1
    if wave == 'tri':
        return 4 * abs(p - 0.5) - 1
    if wave == 'noise':
        return random.uniform(-1, 1)
    return math.sin(2 * math.pi * p)


def tone(f0, f1, dur, wave='square', vol=0.5, decay=4.0, duty=0.5):
    n = int(SR * dur)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        ph += (f0 + (f1 - f0) * t) / SR
        env = math.exp(-decay * t) * min(1.0, i / (SR * 0.004)) * min(1.0, (n - i) / (SR * 0.006))
        out.append(osc(wave, ph % 1.0, duty) * vol * env)
    return out


def noise_burst(dur, vol=0.8, decay=4.0, a0=0.6, a1=0.03):
    n = int(SR * dur)
    out = []
    y = 0.0
    for i in range(n):
        t = i / n
        y += (a0 + (a1 - a0) * t) * (random.uniform(-1, 1) - y)
        out.append(y * vol * math.exp(-decay * t) * min(1.0, (n - i) / (SR * 0.006)))
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def seq(*tracks):
    out = []
    for t in tracks:
        out.extend(t)
    return out


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def add_note(buf, t0, dur, f, wave='square', vol=0.2, decay=2.0, duty=0.5):
    i0 = int(t0 * SR)
    n = int(dur * SR)
    ph = 0.0
    for i in range(n):
        j = i0 + i
        if j >= len(buf):
            break
        ph += f / SR
        t = i / n
        env = math.exp(-decay * t) * min(1.0, i / (SR * 0.004)) * min(1.0, (n - i) / (SR * 0.01))
        buf[j] += osc(wave, ph % 1.0, duty) * vol * env


def add_noise(buf, t0, dur, vol, decay, a=0.5):
    i0 = int(t0 * SR)
    n = int(dur * SR)
    y = 0.0
    for i in range(n):
        j = i0 + i
        if j >= len(buf):
            break
        y += a * (random.uniform(-1, 1) - y)
        buf[j] += y * vol * math.exp(-decay * i / n)


def add_kick(buf, t0):
    i0 = int(t0 * SR)
    n = int(0.16 * SR)
    ph = 0.0
    for i in range(n):
        j = i0 + i
        if j >= len(buf):
            break
        t = i / n
        ph += (130 - 90 * t) / SR
        buf[j] += math.sin(2 * math.pi * ph) * 0.45 * math.exp(-5 * t)


CH = {'Am': (57, 60, 64), 'F': (53, 57, 60), 'C': (48, 52, 55), 'G': (55, 59, 62), 'Em': (52, 55, 59),
      'Dm': (50, 53, 57)}


def build_music(style):
    if style == 'calm':
        bpm, prog = 96, ['Am', 'F', 'C', 'G', 'Am', 'F', 'G', 'Em']
    else:
        bpm, prog = 148, ['Am', 'Am', 'F', 'G', 'Am', 'Am', 'Dm', 'Em']
    beat = 60.0 / bpm
    bar = beat * 4
    bars = len(prog)
    buf = [0.0] * (int(SR * bar * bars) + 1)
    rnd = random.Random(7 if style == 'calm' else 13)
    penta = [0, 3, 5, 7, 10, 12, 15]
    for b, name in enumerate(prog):
        root, third, fifth = CH[name]
        t = b * bar
        if style == 'calm':
            add_note(buf, t, bar * 0.5, midi(root - 12), 'saw', 0.13, 1.4)
            add_note(buf, t + bar * 0.5, bar * 0.5, midi(root - 12), 'saw', 0.11, 1.4)
            add_note(buf, t, bar, midi(fifth), 'sine', 0.07, 0.4)
            for k in range(8):
                nt = [root, third, fifth, third][k % 4] + 12 + (12 if k >= 6 else 0)
                add_note(buf, t + k * beat / 2, beat * 0.42, midi(nt), 'square', 0.05, 5.0, 0.25)
            if b % 2 == 1:
                for k in range(2):
                    nt = 69 + rnd.choice(penta)
                    add_note(buf, t + (k * 2 + rnd.choice([0, 1])) * beat, beat * 1.6, midi(nt), 'tri', 0.10, 1.8)
        else:
            for k in range(8):
                add_note(buf, t + k * beat / 2, beat * 0.4, midi(root - 12), 'saw', 0.12, 6.0)
                add_noise(buf, t + k * beat / 2, 0.04, 0.10, 6.0, 0.9)
            for k in (0, 2):
                add_kick(buf, t + k * beat)
            for k in (1, 3):
                add_noise(buf, t + k * beat, 0.14, 0.22, 5.0, 0.5)
            for k in range(16):
                nt = [root, fifth, third, fifth][k % 4] + 24
                add_note(buf, t + k * beat / 4, beat * 0.2, midi(nt), 'square', 0.035, 6.0, 0.25)
            if b % 2 == 1:
                nt = 69 + rnd.choice(penta)
                add_note(buf, t + beat, beat * 1.5, midi(nt), 'saw', 0.07, 2.0)
    return buf


class Audio:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.sfx = {}
        self.cur = None
        self.ch = 2
        global SR
        try:
            info = pygame.mixer.get_init()
            if not info:
                pygame.mixer.init(22050, -16, 2, 512)
                info = pygame.mixer.get_init()
            SR, _, self.ch = info
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(2)
            self.ok = True
        except Exception:
            self.ok = False
            return
        self._build()

    def _snd(self, samples, vol=1.0):
        buf = array.array('h')
        for s in samples:
            v = int(clamp(s, -1, 1) * 32000 * vol)
            for _ in range(self.ch):
                buf.append(v)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _build(self):
        S = self._snd
        self.sfx = {
            'cannon': S(mix(tone(190, 45, 0.38, 'sine', 0.8, 5), noise_burst(0.32, 0.55, 6, 0.5, 0.05)), 0.9),
            'launch': S(mix(tone(300, 1500, 0.35, 'saw', 0.22, 3), noise_burst(0.3, 0.2, 4, 0.7, 0.2)), 0.8),
            'boom_s': S(mix(noise_burst(0.35, 0.7, 5, 0.5, 0.05), tone(120, 40, 0.35, 'sine', 0.5, 6)), 0.9),
            'boom_l': S(mix(noise_burst(1.1, 0.9, 3, 0.5, 0.02), tone(90, 25, 1.0, 'sine', 0.8, 3)), 1.0),
            'splash': S(noise_burst(0.4, 0.5, 6, 0.9, 0.15), 0.7),
            'hit': S(mix(noise_burst(0.3, 0.6, 7, 0.6, 0.08), tone(220, 60, 0.25, 'square', 0.3, 8)), 0.9),
            'alarm': S(seq(*[tone(f, f, 0.17, 'square', 0.22, 0.5) for f in (760, 520, 760, 520, 760, 520)]), 0.8),
            'pickup': S(seq(tone(523, 523, 0.07, 'square', 0.25, 2), tone(659, 659, 0.07, 'square', 0.25, 2),
                            tone(784, 784, 0.07, 'square', 0.25, 2), tone(1047, 1047, 0.16, 'square', 0.25, 3)), 0.8),
            'mg': S(mix(noise_burst(0.05, 0.4, 10, 0.9, 0.4), tone(300, 140, 0.05, 'square', 0.15, 8)), 0.5),
            'ping': S(tone(1500, 1500, 0.5, 'sine', 0.3, 6), 0.7),
            'blip': S(tone(880, 880, 0.05, 'square', 0.2, 2), 0.6),
            'dock': S(tone(440, 700, 0.09, 'tri', 0.3, 3), 0.7),
            'empty': S(tone(120, 90, 0.12, 'square', 0.25, 4), 0.7),
            'win': S(seq(*[tone(f, f, 0.14, 'square', 0.25, 2) for f in (523, 659, 784, 1047, 784, 1047, 1319)]), 0.9),
            'lose': S(seq(*[tone(f, f * 0.9, 0.3, 'saw', 0.25, 1.5) for f in (392, 349, 311, 262)]), 0.9),
        }
        eng = [0.0] * SR
        nz = noise_burst(1.0, 0.25, 0.0, 0.05, 0.05)
        for i in range(SR):
            eng[i] = (math.sin(2 * math.pi * 50 * i / SR) * 0.25 + math.sin(2 * math.pi * 75 * i / SR) * 0.15
                      + (nz[i] if i < len(nz) else 0))
        self.engine = S(eng, 0.6)
        self.music_s = {'calm': S(build_music('calm'), 0.8), 'battle': S(build_music('battle'), 0.8)}
        pygame.mixer.Channel(1).play(self.engine, loops=-1)
        pygame.mixer.Channel(1).set_volume(0.0)

    def play(self, name, vol=1.0):
        if self.ok and not self.muted and name in self.sfx:
            s = self.sfx[name]
            s.set_volume(clamp(vol, 0, 1))
            s.play()

    def music(self, style):
        if not self.ok or style == self.cur:
            return
        self.cur = style
        ch = pygame.mixer.Channel(0)
        ch.stop()
        if style:
            ch.play(self.music_s[style], loops=-1, fade_ms=500)
            ch.set_volume(0.0 if self.muted else 0.33)

    def engine_vol(self, v):
        if self.ok:
            pygame.mixer.Channel(1).set_volume(0.0 if self.muted else clamp(v, 0, 1) * 0.35)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.ok:
            pygame.mixer.Channel(0).set_volume(0.0 if self.muted else 0.33)


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
    r = max(8, int(r) // 8 * 8)
    c = tuple(int(v * clamp(k, 0, 1)) // 32 * 32 for v in col)
    if c == (0, 0, 0):
        return
    key = (r, c)
    s = _glow.get(key)
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
                draw_circ(dst, sx, sy, r, col, 150 * (1 - t) ** 1.3)
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
}
TEAM_COL = {
    'p': dict(uni=(72, 114, 102), vest=(46, 76, 70), helm=(86, 132, 114), trim=(255, 214, 90)),
    'e': dict(uni=(138, 74, 62), vest=(92, 50, 44), helm=(154, 88, 68), trim=(36, 32, 32)),
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


TK_FOG = (96, 64, 92)        # color de la bruma del atardecer
TK_NL = 10                   # niveles de bruma por distancia


def _grain(s, base, var, rnd, step=2):
    w, h = s.get_size()
    for y in range(0, h, step):
        for x in range(0, w, step):
            d = rnd.randint(-var, var)
            pygame.draw.rect(s, (clamp(base[0] + d, 0, 255), clamp(base[1] + d, 0, 255), clamp(base[2] + d, 0, 255)),
                             (x, y, step, step))


def _window(s, x, y, w, h, rnd, lit=None, frame=(150, 146, 140), arch=False):
    pygame.draw.rect(s, shade(frame, -60), (x - 2, y - 2, w + 4, h + 4), border_radius=3 if arch else 1)
    pygame.draw.rect(s, frame, (x - 1, y - 1, w + 2, h + 2), border_radius=3 if arch else 1)
    lit = rnd.random() < 0.34 if lit is None else lit
    for i in range(h):
        f = i / max(1, h - 1)
        if lit:
            c = (int(lerp(255, 214, f)), int(lerp(224, 150, f)), int(lerp(150, 70, f)))
        else:
            c = (int(lerp(60, 18, f)), int(lerp(86, 28, f)), int(lerp(124, 52, f)))
        pygame.draw.line(s, c, (x, y + i), (x + w - 1, y + i))
    if not lit:
        pygame.draw.line(s, (130, 160, 200), (x + 2, y + h - 3), (x + w // 2, y + 2), 1)
    pygame.draw.line(s, shade(frame, -40), (x + w // 2, y), (x + w // 2, y + h - 1), 1)
    pygame.draw.rect(s, shade(frame, 24), (x - 3, y + h, w + 6, 3))


def tex_brick(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    s.fill((78, 66, 60))
    base = rnd.choice(((150, 70, 52), (138, 82, 58), (120, 60, 56)))
    for r in range(0, 128, 8):
        off = 8 if (r // 8) % 2 else 0
        for c in range(-16, 128, 16):
            d = rnd.randint(-16, 16)
            pygame.draw.rect(s, (clamp(base[0] + d, 0, 255), clamp(base[1] + d // 2, 0, 255), clamp(base[2] + d // 2, 0, 255)),
                             (c + off, r, 15, 7))
    for wx in (16, 82):
        for wy in (12, 70):
            _window(s, wx, wy, 30, 40, rnd)
    return s


def tex_concrete(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    _grain(s, rnd.choice(((132, 134, 140), (150, 148, 142), (118, 124, 132))), 9, rnd)
    for x in (0, 64):
        pygame.draw.line(s, (80, 82, 88), (x, 0), (x, 127), 2)
    for y in (0, 64):
        pygame.draw.line(s, (80, 82, 88), (0, y), (127, y), 2)
    for by in (14, 78):
        for bx in range(8, 120, 38):
            _window(s, bx, by, 26, 30, rnd, frame=(196, 196, 200))
    return s


def tex_glass(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    for gy in range(0, 128, 32):
        for gx in range(0, 128, 32):
            lit = rnd.random() < 0.3
            for i in range(32):
                f = (gy + i) / 128
                if lit:
                    c = (int(lerp(255, 220, f)), int(lerp(230, 170, f)), int(lerp(160, 90, f)))
                else:
                    c = (int(lerp(88, 24, f)), int(lerp(150, 70, f)), int(lerp(180, 110, f)))
                pygame.draw.line(s, c, (gx, gy + i), (gx + 31, gy + i))
            if not lit:
                pygame.draw.line(s, (200, 230, 245), (gx + 4, gy + 28), (gx + 20, gy + 4), 2)
    for k in range(0, 128, 32):
        pygame.draw.line(s, (26, 32, 40), (k, 0), (k, 127), 3)
        pygame.draw.line(s, (26, 32, 40), (0, k), (127, k), 3)
    return s


def tex_sand(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    base = rnd.choice(((190, 164, 118), (176, 150, 108)))
    _grain(s, base, 8, rnd)
    for r in range(0, 128, 16):
        pygame.draw.line(s, shade(base, -46), (0, r), (127, r), 1)
        off = 0 if (r // 16) % 2 else 24
        for c in range(off, 128, 48):
            pygame.draw.line(s, shade(base, -46), (c, r), (c, r + 15), 1)
    for wx in (20, 80):
        for wy in (22, 78):
            _window(s, wx, wy, 26, 34, rnd, frame=(224, 214, 190), arch=True)
    return s


def tex_hall(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((128, 128))
    _grain(s, (206, 212, 226), 6, rnd)
    for x in range(0, 128, 32):
        pygame.draw.rect(s, (236, 240, 248), (x, 0, 8, 128))
        pygame.draw.rect(s, (150, 156, 172), (x + 8, 0, 2, 128))
        pygame.draw.rect(s, (252, 220, 140), (x - 2, 0, 12, 6))
        pygame.draw.rect(s, (252, 220, 140), (x - 2, 122, 12, 6))
    for x in range(8, 128, 32):
        for y in (14, 74):
            for i in range(44):
                f = i / 43
                pygame.draw.line(s, (int(lerp(255, 230, f)), int(lerp(236, 170, f)), int(lerp(170, 90, f))),
                                 (x + 3, y + i), (x + 22, y + i))
            pygame.draw.rect(s, (252, 220, 140), (x + 2, y - 1, 21, 46), 1)
    pygame.draw.line(s, (252, 220, 140), (0, 60), (127, 60), 3)
    return s


def tex_missile():
    s = pygame.Surface((64, 64))
    for y in range(64):
        v = int(lerp(236, 120, abs(y - 28) / 40))
        pygame.draw.line(s, (v, v, min(255, v + 10)), (0, y), (63, y))
    pygame.draw.rect(s, (214, 50, 40), (0, 20, 64, 8))
    pygame.draw.rect(s, (40, 40, 46), (0, 38, 64, 4))
    return s


def tk_entry(tile, reps):
    tw, th = tile.get_size()
    tall = pygame.Surface((tw, th * reps))
    for r in range(reps):
        tall.blit(tile, (0, r * th))
    tall = tall.convert()
    var = []
    for L in range(TK_NL):
        f = L / (TK_NL - 1) * 0.9
        row = []
        for side_shade in (1.0, 0.6):
            v = tall.copy()
            m = int(255 * side_shade * (1 - f))
            v.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
            v.fill(tuple(int(c * f) for c in TK_FOG), special_flags=pygame.BLEND_RGB_ADD)
            row.append(v)
        var.append(row)
    return dict(tw=tw, th=th, reps=reps, var=var)


def make_tk_textures():
    T = {}
    T['bld'] = [tk_entry(tex_brick(1), 4), tk_entry(tex_brick(2), 4), tk_entry(tex_concrete(3), 4),
                tk_entry(tex_concrete(4), 4), tk_entry(tex_glass(5), 4), tk_entry(tex_sand(6), 4)]
    T['hall'] = tk_entry(tex_hall(7), 4)
    T['missile'] = tk_entry(tex_missile(), 1)
    return T


TK_PXU = 32.0       # píxeles por unidad de mundo en los sprites pre-renderizados
TK_ANG = 32         # ángulos de vista pre-renderizados
TK_PITCH = 12.0     # inclinación de la cámara (grados)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


class Solid:
    """Sólido convexo: caras (vértices, color) con normales hacia afuera, más detalles planos."""

    def __init__(self, faces, details=()):
        pts = [v for f, _ in faces for v in f]
        self.c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), sum(p[2] for p in pts) / len(pts))
        self.faces = []
        for verts, col in faces:
            n = _unit(_cross(_sub(verts[1], verts[0]), _sub(verts[2], verts[0])))
            fc = (sum(v[0] for v in verts) / len(verts), sum(v[1] for v in verts) / len(verts), sum(v[2] for v in verts) / len(verts))
            if n[0] * (fc[0] - self.c[0]) + n[1] * (fc[1] - self.c[1]) + n[2] * (fc[2] - self.c[2]) < 0:
                n = (-n[0], -n[1], -n[2])
            self.faces.append((verts, col, n))
        self.details = list(details)


def s_box(x0, x1, y0, y1, z0, z1, col):
    v = lambda x, y, z: (x, y, z)
    f = [([v(x0, y0, z0), v(x1, y0, z0), v(x1, y1, z0), v(x0, y1, z0)], col), ([v(x0, y0, z1), v(x1, y0, z1), v(x1, y1, z1), v(x0, y1, z1)], col),
         ([v(x0, y0, z0), v(x0, y0, z1), v(x0, y1, z1), v(x0, y1, z0)], col), ([v(x1, y0, z0), v(x1, y0, z1), v(x1, y1, z1), v(x1, y1, z0)], col),
         ([v(x0, y0, z0), v(x1, y0, z0), v(x1, y0, z1), v(x0, y0, z1)], col), ([v(x0, y1, z0), v(x1, y1, z0), v(x1, y1, z1), v(x0, y1, z1)], col)]
    return Solid(f)


def s_extrude(profile, x0, x1, col, top_cols=None):
    """Perfil convexo (z, y) extruido a lo ancho entre x0 y x1."""
    n = len(profile)
    f = [([(x1, y, z) for z, y in profile], col), ([(x0, y, z) for z, y in profile], col)]
    for i in range(n):
        (za, ya), (zb, yb) = profile[i], profile[(i + 1) % n]
        c = top_cols[i] if top_cols else col
        f.append(([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)], c))
    return Solid(f)


def s_frustum(cx, cz, y0, y1, r0, r1, n, cols, rot=0.0, sx=1.0, sz=1.0):
    """Tronco de cono vertical (n lados); sx/sz lo achatan en elipse."""
    a = [(cx + math.cos(rot + 2 * math.pi * i / n) * r0 * sx, y0, cz + math.sin(rot + 2 * math.pi * i / n) * r0 * sz) for i in range(n)]
    b = [(cx + math.cos(rot + 2 * math.pi * i / n) * r1 * sx, y1, cz + math.sin(rot + 2 * math.pi * i / n) * r1 * sz) for i in range(n)]
    f = [(a, cols[0]), (b, cols[0])]
    for i in range(n):
        j = (i + 1) % n
        f.append(([a[i], a[j], b[j], b[i]], cols[i % len(cols)]))
    return Solid(f)


def s_cyl_z(cx, cy, z0, z1, r0, r1, n, col):
    """Cilindro/cono a lo largo del eje z (cañones)."""
    a = [(cx + math.cos(2 * math.pi * i / n) * r0, cy + math.sin(2 * math.pi * i / n) * r0, z0) for i in range(n)]
    b = [(cx + math.cos(2 * math.pi * i / n) * r1, cy + math.sin(2 * math.pi * i / n) * r1, z1) for i in range(n)]
    f = [(a, col), (b, col)]
    for i in range(n):
        j = (i + 1) % n
        f.append(([a[i], a[j], b[j], b[i]], col))
    return Solid(f)


def disc_x(x, y, z, r, n, col, nx):
    return ([(x, y + math.sin(2 * math.pi * i / n) * r, z + math.cos(2 * math.pi * i / n) * r) for i in range(n)], col, (nx, 0.0, 0.0))


def quad_x(x, y0, y1, z0, z1, col, nx):
    return ([(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)], col, (nx, 0.0, 0.0))


def quad_y(y, x0, x1, z0, z1, col):
    return ([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], col, (0.0, 1.0, 0.0))


def build_tank_model(heavy, seed):
    rnd = random.Random(seed)
    if heavy:
        base, camo = (74, 82, 96), [(74, 82, 96), (58, 64, 78), (90, 98, 112), (66, 72, 86)]
        trim, barrel_c, S = (232, 140, 36), (52, 56, 66), 1.22
    else:
        base, camo = (96, 104, 62), [(96, 104, 62), (74, 82, 48), (128, 112, 70), (84, 70, 50)]
        trim, barrel_c, S = (200, 190, 120), (58, 62, 50), 1.0
    track_c, rubber, hub = (34, 34, 36), (20, 20, 22), (110, 112, 104)
    hull, tur = [], []

    def camo_c():
        return rnd.choice(camo)
    # cascos: carrocería inclinada, cada franja de la cubierta con un parche de camuflaje distinto
    prof = [(-3.2, 0.40), (-3.2, 1.12), (-2.45, 1.40), (1.55, 1.40), (3.3, 0.98), (3.3, 0.50), (2.75, 0.40)]
    tops = [camo_c() for _ in prof]
    hull.append(s_extrude(prof, -1.40, 1.40, base, tops))
    for sd in (-1, 1):
        xa, xb = (1.38, 2.04) if sd > 0 else (-2.04, -1.38)
        tprof = [(-3.1, 0.0), (3.0, 0.0), (3.65, 0.42), (3.65, 0.78), (3.05, 1.16), (-3.05, 1.16), (-3.55, 0.82), (-3.55, 0.34)]
        det = []
        xo = xb + 0.012 if sd > 0 else xa - 0.012
        nx = 1.0 if sd > 0 else -1.0
        for zc in (-2.35, -1.4, -0.45, 0.5, 1.45, 2.4):
            det.append(disc_x(xo, 0.52, zc, 0.43, 14, rubber, nx))
            det.append(disc_x(xo + nx * 0.01, 0.52, zc, 0.26, 12, hub, nx))
            det.append(disc_x(xo + nx * 0.02, 0.52, zc, 0.08, 8, rubber, nx))
        det.append(disc_x(xo, 0.62, -3.15, 0.46, 14, rubber, nx))
        det.append(disc_x(xo + nx * 0.01, 0.62, -3.15, 0.3, 12, hub, nx))
        det.append(disc_x(xo, 0.58, 3.15, 0.40, 14, rubber, nx))
        det.append(disc_x(xo + nx * 0.01, 0.58, 3.15, 0.24, 12, hub, nx))
        for k in range(-13, 14):
            z = k * 0.235
            det.append(quad_x(xo, 1.0, 1.15, z - 0.04, z + 0.04, (14, 14, 16), nx))
            det.append(quad_x(xo, 0.0, 0.14, z - 0.04, z + 0.04, (14, 14, 16), nx))
        tr = s_extrude(tprof, xa, xb, track_c)
        tr.details = det
        hull.append(tr)
        fx0, fx1 = (1.3, 2.12) if sd > 0 else (-2.12, -1.3)
        hull.append(s_box(fx0, fx1, 1.13, 1.27, -3.0, 3.25, base))
        if heavy:
            skx0, skx1 = (2.1, 2.2) if sd > 0 else (-2.2, -2.1)
            sk = s_box(skx0, skx1, 0.30, 1.12, -2.9, 2.5, camo_c())
            for k in range(7):
                z = -2.5 + k * 0.8
                sk.details.append(quad_x(skx1 + 0.01 if sd > 0 else skx0 - 0.01, 0.35, 0.95, z, z + 0.04, (20, 20, 24), nx))
            hull.append(sk)
        bx0, bx1 = (1.55, 1.95) if sd > 0 else (-1.95, -1.55)
        hull.append(s_box(bx0, bx1, 1.27, 1.52, -2.2, -1.5, (50, 52, 46)))
        hull.append(s_cyl_z(1.05 * sd, 1.18, -3.28, -3.02, 0.14, 0.12, 8, (28, 28, 30)))
        hull.append(s_cyl_z(0.95 * sd, 0.92, 3.3, 3.36, 0.14, 0.14, 8, (255, 232, 160)))
    deck = [quad_y(1.405, -1.1, 1.1, -2.35 + k * 0.38, -2.35 + k * 0.38 + 0.2, (24, 24, 26)) for k in range(5)]
    hull[0].details += deck
    hull[0].details.append(quad_y(1.41, -0.5, 0.5, 1.0, 1.4, (60, 60, 56)))
    hull.append(s_box(-0.32, 0.32, 1.40, 1.58, 1.05, 1.5, base))
    hull.append(s_box(-0.9, 0.9, 0.62, 1.0, 3.2, 3.32, base))
    # torreta redonda con cúpula y cañón largo (todo girable aparte)
    tc = [camo_c() for _ in range(14)]
    tur.append(s_frustum(0.0, 0.1, 1.40, 1.78, 1.45 * S, 1.52 * S, 14, tc, 0.0, 1.0, 1.1))
    tur.append(s_frustum(0.0, 0.1, 1.78, 2.22, 1.52 * S, 1.30 * S, 14, tc, 0.0, 1.0, 1.1))
    tur.append(s_frustum(0.0, 0.1, 2.22, 2.58, 1.30 * S, 0.86 * S, 14, [camo_c() for _ in range(14)], 0.0, 1.0, 1.1))
    mant = s_box(-0.52 * S, 0.52 * S, 1.80, 2.34, 1.35 * S, 1.80 * S, base)
    tur.append(mant)
    tur.append(s_cyl_z(0.0, 2.08, 1.8 * S, 4.2 * S, 0.17 * S, 0.15 * S, 10, barrel_c))
    tur.append(s_cyl_z(0.0, 2.08, 2.9 * S, 3.2 * S, 0.215 * S, 0.215 * S, 10, (70, 74, 64)))
    tur.append(s_cyl_z(0.0, 2.08, 4.2 * S, 5.5 * S, 0.15 * S, 0.14 * S, 10, barrel_c))
    tur.append(s_cyl_z(0.0, 2.08, 5.25 * S, 5.55 * S, 0.22 * S, 0.22 * S, 10, (44, 48, 42)))
    tur.append(s_frustum(0.55, -0.25, 2.58, 2.86, 0.38, 0.34, 10, [(84, 90, 58)]))
    tur.append(s_cyl_z(0.55, 2.97, -0.15, 0.6, 0.045, 0.045, 6, (30, 30, 30)))
    tur.append(s_frustum(-0.5, -0.1, 2.58, 2.66, 0.34, 0.34, 10, [(60, 64, 50)]))
    tur.append(s_box(-0.95 * S, 0.95 * S, 1.78, 2.34, -2.1 * S, -1.5 * S, base))
    tur.append(s_box(-0.05, 0.05, 2.56, 4.5, -1.6 * S, -1.5 * S, (30, 30, 30)))
    for sd in (-1, 1):
        for k in range(3):
            tur.append(s_cyl_z(1.28 * S * sd, 2.05 + k * 0.1, 0.35, 0.65, 0.07, 0.07, 6, (40, 40, 40)))
    if heavy:
        tur.append(s_box(-0.7, 0.7, 2.58, 2.86, -1.2, -0.3, trim))
        tur.append(s_box(-1.52 * S, -1.34 * S, 1.6, 2.4, -0.6, 0.8, camo_c()))
        tur.append(s_box(1.34 * S, 1.52 * S, 1.6, 2.4, -0.6, 0.8, camo_c()))
    return hull, tur


def render_solids(solids, rel_deg, size, px, pitch=TK_PITCH, shadow=False):
    W_, H_ = size
    SS = 2
    surf = pygame.Surface((W_ * SS, H_ * SS), pygame.SRCALPHA)
    a, p = math.radians(rel_deg), math.radians(pitch)
    ca, sa, cp, sp_ = math.cos(a), math.sin(a), math.cos(p), math.sin(p)
    cx0, gy = W_ / 2.0, H_ * 0.80
    L = _unit((0.50, 0.72, -0.46))
    if shadow:
        sw, sh_ = 8.4 * px * SS, 8.4 * px * SS * math.sin(p) * 0.9
        sx0 = cx0 * SS - sw / 2
        pygame.draw.ellipse(surf, (0, 0, 0, 105), (sx0, gy * SS - sh_ / 2, sw, sh_))

    def tr(v):
        x1, z1 = v[0] * ca + v[2] * sa, -v[0] * sa + v[2] * ca
        return x1, v[1] * cp + z1 * sp_, z1 * cp - v[1] * sp_

    def trn(n):
        return tr(n)

    order = []
    for s in solids:
        order.append((tr(s.c)[2], s))
    order.sort(key=lambda q: -q[0])
    for _, s in order:
        items = [(f[0], f[1], f[2], False) for f in s.faces] + [(d[0], d[1], d[2], True) for d in s.details]
        for verts, col, n, is_detail in items:
            nv = trn(n)
            if nv[2] >= -0.02:
                continue
            sh = 0.36 + 0.64 * max(0.0, nv[0] * L[0] + nv[1] * L[1] + nv[2] * L[2])
            c = (min(255, int(col[0] * sh)), min(255, int(col[1] * sh)), min(255, int(col[2] * sh)))
            pts = []
            for v in verts:
                x, y, z = tr(v)
                pts.append(((cx0 + x * px) * SS, (gy - y * px) * SS))
            pygame.draw.polygon(surf, c, pts)
            if not is_detail:
                pygame.draw.lines(surf, (int(c[0] * .55), int(c[1] * .55), int(c[2] * .55)), True, pts, 1)
    out = pygame.transform.smoothscale(surf, (W_, H_))
    return out, cx0, gy


def make_tank_sprites():
    """Pre-renderiza cada tanque (casco y torreta por separado) desde TK_ANG ángulos."""
    size = (380, 250)
    out = {}
    for kind, heavy in (('tank', False), ('super', True)):
        hull, tur = build_tank_model(heavy, 11 if not heavy else 23)
        px = TK_PXU * (0.92 if heavy else 1.0)
        parts = {'px': px}
        for name, solids in (('hull', hull), ('tur', tur)):
            lst = []
            for i in range(TK_ANG):
                img, ax, ay = render_solids(solids, i * 360.0 / TK_ANG, size, px, shadow=(name == 'hull'))
                r = img.get_bounding_rect()
                if r.w < 2 or r.h < 2:
                    r = pygame.Rect(0, 0, 2, 2)
                lst.append((img.subsurface(r).copy().convert_alpha(), ax - r.x, ay - r.y))
            parts[name] = lst
        out[kind] = parts
    return out


# ------------------------------------------------------------------ arte del asalto (soldados pre-renderizados)
PT_S = 4                      # supersampling de los sprites
PT_K = 1.12                   # escala del personaje
PT_CW, PT_CH = 128, 120       # tamaño del lienzo de cada cuadro (px a 1x)
PT_AX, PT_AY = 64, 104        # ancla: pies del personaje

PT_LOOK = {
    # kind: (uniforme, chaleco, casco/cabeza, pantalón, mochila, piel)
    'player': dict(body=(46, 98, 146), vest=(36, 58, 78), helm=(78, 104, 76), pants=(52, 70, 62), pack=(70, 62, 50), skin=(232, 190, 150)),
    'rifle': dict(body=(150, 78, 60), vest=(92, 54, 46), helm=(106, 66, 54), pants=(90, 66, 56), pack=(80, 64, 48), skin=(226, 178, 140)),
    'knife': dict(body=(188, 120, 60), vest=(96, 62, 46), helm=(200, 50, 50), pants=(74, 62, 58), pack=(70, 56, 44), skin=(222, 172, 132)),
    'gren': dict(body=(112, 78, 140), vest=(66, 50, 82), helm=(86, 64, 104), pants=(66, 54, 80), pack=(90, 72, 56), skin=(214, 168, 134)),
    'sniper': dict(body=(70, 92, 62), vest=(52, 70, 48), helm=(58, 80, 52), pants=(60, 78, 56), pack=(64, 60, 44), skin=(220, 176, 140)),
    'shield': dict(body=(84, 92, 104), vest=(52, 58, 70), helm=(110, 118, 130), pants=(60, 66, 78), pack=(70, 64, 56), skin=(218, 172, 136)),
    'flame': dict(body=(204, 120, 44), vest=(120, 70, 36), helm=(150, 90, 40), pants=(96, 70, 50), pack=(210, 70, 40), skin=(222, 176, 138)),
    'pow': dict(body=(222, 214, 190), vest=(180, 170, 150), helm=(86, 62, 40), pants=(104, 96, 120), pack=(180, 170, 150), skin=(230, 188, 150)),
}


def _dk(c, d):
    return (clamp(c[0] - d, 0, 255), clamp(c[1] - d, 0, 255), clamp(c[2] - d, 0, 255))


class _Rig:
    """Dibuja formas en coordenadas locales (x adelante, y arriba) sobre un lienzo supersampleado."""

    def __init__(self, ang=0.0, w=PT_CW, h=PT_CH, ax=PT_AX, ay=PT_AY):
        self.S = PT_S
        self.surf = pygame.Surface((w * PT_S, h * PT_S), pygame.SRCALPHA)
        self.ax, self.ay = ax, ay
        a = math.radians(ang)
        self.ca, self.sa = math.cos(a), math.sin(a)

    def pt(self, x, y):
        xr = x * self.ca - y * self.sa
        yr = x * self.sa + y * self.ca
        return ((self.ax + xr * PT_K) * self.S, (self.ay - yr * PT_K) * self.S)

    def poly(self, pts, col, out=None, ow=0.9):
        P = [self.pt(*p) for p in pts]
        pygame.draw.polygon(self.surf, col, P)
        if out is not None:
            pygame.draw.polygon(self.surf, out, P, max(1, int(ow * self.S)))

    def circ(self, c, r, col, out=None, ow=0.9):
        x, y = self.pt(*c)
        pygame.draw.circle(self.surf, col, (x, y), r * self.S * PT_K)
        if out is not None:
            pygame.draw.circle(self.surf, out, (x, y), r * self.S * PT_K, max(1, int(ow * self.S)))

    def ell(self, c, rx, ry, col, out=None, rot=0.0):
        """Elipse como polígono (permite rotación)."""
        pts = []
        cr, sr = math.cos(rot), math.sin(rot)
        for i in range(24):
            t = 6.2832 * i / 24
            ex, ey = math.cos(t) * rx, math.sin(t) * ry
            pts.append((c[0] + ex * cr - ey * sr, c[1] + ex * sr + ey * cr))
        self.poly(pts, col, out)

    def cap(self, a, b, w, col, out=None):
        """Cápsula (miembro) entre a y b, con brillo."""
        if out is not None:
            self._cap(a, b, w + 1.7, out)
        self._cap(a, b, w, col)
        if w > 3.0:
            hi = (clamp(col[0] + 26, 0, 255), clamp(col[1] + 26, 0, 255), clamp(col[2] + 26, 0, 255))
            A, B = self.pt(*a), self.pt(*b)
            off = w * 0.2 * self.S * PT_K
            pygame.draw.line(self.surf, hi, (A[0], A[1] - off), (B[0], B[1] - off), max(1, int(w * 0.3 * self.S * PT_K)))

    def _cap(self, a, b, w, col):
        A, B = self.pt(*a), self.pt(*b)
        wk = w * PT_K * self.S
        pygame.draw.line(self.surf, col, A, B, max(1, int(wk)))
        pygame.draw.circle(self.surf, col, A, wk / 2)
        pygame.draw.circle(self.surf, col, B, wk / 2)

    def finish(self):
        return pygame.transform.smoothscale(self.surf, (self.surf.get_width() // PT_S, self.surf.get_height() // PT_S))


def _leg(hip, th, flex, L1=15.0, L2=15.0):
    t = math.radians(th)
    knee = (hip[0] + math.sin(t) * L1, hip[1] - math.cos(t) * L1)
    t2 = math.radians(th - flex)
    ankle = (knee[0] + math.sin(t2) * L2, knee[1] - math.cos(t2) * L2)
    return knee, ankle, t2


def _pose(pose, i):
    """Devuelve (leg1, leg2, lean, auto_hip, hip_y, fall_ang, crouch)  con leg=(thigh°, flex°)."""
    if pose == 'run':
        ph = 6.2832 * i / 8
        legs = []
        for k in (0, 1):
            pk = ph + k * 3.14159
            legs.append((46 * math.sin(pk), 10 + 78 * max(0.0, math.cos(pk))))
        return legs[0], legs[1], 8.0, True, 30.0, 0.0
    if pose == 'idle':
        br = math.sin(6.2832 * i / 4)
        return (7, 3 + br), (-7, 3), 0.0, True, 30.0, 0.0
    if pose == 'crouch':
        return (76, 100), (22, 108), 12.0, True, 18.0, 0.0
    if pose == 'jump':
        return (52, 84), (-14, 52), 4.0, False, 27.5, 0.0
    if pose == 'fall':
        return (14, 16), (-12, 8), -3.0, False, 29.5, 0.0
    if pose == 'die':
        ang = (0, 12, 32, 58, 80, 90)[min(i, 5)]
        return (6, 6), (-6, 6), -6.0 * min(i, 3) / 3, False, 30.0 - min(i, 5) * 1.0, float(ang)
    return (7, 3), (-7, 3), 0.0, True, 30.0, 0.0


def _body_frame(kind, pose, i, t=0.0):
    """Cuerpo (sin brazos) mirando a la derecha. Devuelve (surf, shoulder_dx, shoulder_dy)."""
    look = PT_LOOK[kind]
    leg1, leg2, lean, auto, hy, fall = _pose(pose, i)
    rig = _Rig(fall)
    line = (20, 18, 24)
    body, vest, helm, pants, pack, skin = look['body'], look['vest'], look['helm'], look['pants'], look['pack'], look['skin']
    heavy = kind == 'gren'
    hip = [0.0, hy]
    if auto:
        lows = []
        for th, fl in (leg1, leg2):
            kn, an, _ = _leg((0, 0), th, fl)
            lows.append(-an[1])
        hip[1] = max(lows) + 1.2
    hip = tuple(hip)
    # --- pierna trasera, mochila, torso, pierna delantera, cabeza
    legs = []
    for (th, fl), shade_d in ((leg1, 26), (leg2, 0)):
        kn, an, t2 = _leg(hip, th, fl)
        legs.append((kn, an, t2, shade_d))
    order = sorted(legs, key=lambda L: -L[3])        # primero la de atrás (más oscura)
    leaning = math.radians(lean)
    ux, uy = math.sin(leaning), math.cos(leaning)     # eje del torso
    px_, py_ = uy, -ux                                # perpendicular hacia adelante
    sh = (hip[0] + ux * 22, hip[1] + uy * 22)

    def torso_pt(f, a):
        return (hip[0] + ux * a + px_ * f, hip[1] + uy * a + py_ * f)

    def draw_leg(L):
        kn, an, t2, sd = L
        pc = _dk(pants, sd)
        rig.cap(hip, kn, 7.0, pc, line)
        rig.cap(kn, an, 6.0, pc, line)
        # rodillera y bota
        rig.circ(kn, 3.2, _dk(vest, sd // 2), None)
        toe = (an[0] + 7.0 + (1.2 if heavy else 0), an[1] - 1.8)
        heel = (an[0] - 3.0, an[1] - 1.8)
        rig.poly([(an[0] - 3, an[1] + 3), (an[0] + 3, an[1] + 3), (toe[0], toe[1] + 2.4), (toe[0], toe[1] - 2.2), (heel[0], heel[1] - 2.2)],
                 _dk((38, 34, 36), sd // 2), line)
        rig.poly([(heel[0], heel[1] - 2.2), (toe[0], toe[1] - 2.2), (toe[0], toe[1] - 3.2), (heel[0], heel[1] - 3.2)], (18, 16, 18), None)
    draw_leg(order[0])
    # mochila (atrás del torso)
    pk = [torso_pt(-5.4, 4), torso_pt(-10.5, 6), torso_pt(-11.5, 18), torso_pt(-6, 21)]
    rig.poly(pk, pack, line)
    rig.poly([torso_pt(-6.5, 10), torso_pt(-10.2, 10.6), torso_pt(-10.8, 16), torso_pt(-6.5, 17)], _dk(pack, 14), None)
    if kind == 'sniper':      # camuflaje: hojas
        rnd = random.Random(3)
        for _ in range(16):
            rig.ell(torso_pt(rnd.uniform(-10, 5), rnd.uniform(1, 21)), 2.6, 1.0, rnd.choice(((92, 118, 70), (50, 70, 44), (110, 126, 78))), None, rnd.uniform(0, 3))
    # torso
    torso = [torso_pt(-5.4, 0), torso_pt(5.4, 0), torso_pt(6.4, 12), torso_pt(5.8, 22), torso_pt(-5.8, 22), torso_pt(-6.2, 10)]
    rig.poly(torso, body, line)
    rig.poly([torso_pt(-5.2, 0.5), torso_pt(-1.5, 0.5), torso_pt(-1.5, 21.5), torso_pt(-5.6, 21.5)], _dk(body, 16), None)      # sombra espalda
    # chaleco / blindaje
    if kind == 'knife':
        rig.poly([torso_pt(-3, 4), torso_pt(5.6, 6), torso_pt(6.3, 12), torso_pt(5, 22), torso_pt(1, 22)], vest, line)
        rig.poly([torso_pt(5.4, 6), torso_pt(6.3, 12), torso_pt(5.5, 20), torso_pt(2.8, 21)], _dk(skin, 30), None)
    else:
        vf = 6.8 if heavy else 6.0
        rig.poly([torso_pt(-5.6, 3), torso_pt(vf, 3), torso_pt(vf + 0.6, 12), torso_pt(vf - 0.2, 21.5), torso_pt(-5.6, 21.5)], vest, line)
        for a_ in (6.5, 12.5):
            rig.poly([torso_pt(1.0, a_), torso_pt(vf - 0.3, a_), torso_pt(vf - 0.3, a_ + 4.2), torso_pt(1.0, a_ + 4.2)], _dk(vest, 14), line, 0.6)
            rig.poly([torso_pt(1.0, a_ + 3.2), torso_pt(vf - 0.3, a_ + 3.2), torso_pt(vf - 0.3, a_ + 4.2), torso_pt(1.0, a_ + 4.2)], shade(vest, 20), None)
    # cinturón y hebilla
    rig.poly([torso_pt(-5.6, 1.0), torso_pt(6.0, 1.0), torso_pt(6.0, 3.6), torso_pt(-5.6, 3.6)], (36, 30, 28), line, 0.6)
    rig.poly([torso_pt(2.4, 1.2), torso_pt(4.8, 1.2), torso_pt(4.8, 3.4), torso_pt(2.4, 3.4)], (200, 180, 90), None)
    # granadas al cinto / bandolera
    if heavy or kind == 'player' or kind == 'gren':
        for k_ in range(3 if heavy else 2):
            c_ = torso_pt(3.2 - k_ * 3.0, 6.0 + (k_ % 2) * 0.6)
            rig.circ(c_, 1.9, (70, 100, 56), line, 0.5)
            rig.circ((c_[0], c_[1] + 2.0), 0.7, (170, 170, 170), None)
    if heavy:
        rig.poly([torso_pt(-6, 22), torso_pt(8.5, 21), torso_pt(8.2, 17), torso_pt(-4, 18)], _dk(vest, 6), line, 0.7)      # hombrera
    # pierna delantera
    draw_leg(order[1])
    # cuello y cabeza
    neck = torso_pt(0.6, 22.5)
    head = (neck[0] + ux * 6.2 + px_ * 1.4, neck[1] + uy * 6.2 + py_ * 1.4)
    rig.cap((sh[0] + px_ * 0.5, sh[1] + py_ * 0.5), neck, 3.6, _dk(skin, 24), None)
    if kind == 'sniper':
        hood = [(head[0] - 7.4, head[1] - 7), (head[0] + 5.8, head[1] - 6), (head[0] + 7.4, head[1] + 1), (head[0] + 4, head[1] + 8.4),
                (head[0] - 3, head[1] + 9.6), (head[0] - 8.6, head[1] + 3)]
        rig.poly(hood, helm, line)
        rig.poly([(head[0] - 1, head[1] - 3), (head[0] + 6.3, head[1] - 2.6), (head[0] + 6.8, head[1] + 2), (head[0] - 0.5, head[1] + 2.4)], _dk(skin, 10), None)
        rig.poly([(head[0] - 1.5, head[1] - 7.2), (head[0] + 5.2, head[1] - 6), (head[0] + 6, head[1] - 2.6), (head[0] - 1.5, head[1] - 3.4)], (60, 70, 56), None)
        rnd = random.Random(8)
        for _ in range(9):
            rig.ell((head[0] + rnd.uniform(-8, 6), head[1] + rnd.uniform(-5, 9)), 2.4, 0.9, rnd.choice(((92, 118, 70), (50, 70, 44))), None, rnd.uniform(0, 3))
        rig.circ((head[0] + 3.4, head[1] + 0.2), 0.9, (20, 20, 22), None)
    else:
        rig.circ(head, 7.0, skin, line)
        rig.poly([(head[0] + 6.0, head[1] - 0.6), (head[0] + 8.3, head[1] - 2.0), (head[0] + 6.0, head[1] - 3.2)], skin, line, 0.5)       # nariz
        rig.ell((head[0] - 3.6, head[1] - 1.6), 1.6, 2.2, _dk(skin, 30), None)                                                          # oreja
        rig.circ((head[0] + 3.2, head[1] + 0.9), 0.95, (24, 22, 26), None)                                                             # ojo
        rig.poly([(head[0] + 1.6, head[1] + 2.6), (head[0] + 5.2, head[1] + 2.9), (head[0] + 5.2, head[1] + 3.5), (head[0] + 1.6, head[1] + 3.3)], _dk(skin, 70), None)
        if kind == 'pow':
            rig.poly([(head[0] - 7.2, head[1] + 2.4), (head[0] - 6.8, head[1] + 7.6), (head[0] - 1, head[1] + 9.6), (head[0] + 5.6, head[1] + 7.6), (head[0] + 6.4, head[1] + 3.6),
                      (head[0] + 1.6, head[1] + 4.6)], helm, line, 0.5)
            rig.poly([(head[0] - 1.4, head[1] - 7.0), (head[0] + 5.6, head[1] - 5.0), (head[0] + 6.8, head[1] - 1.2), (head[0] + 1.4, head[1] - 2.4)], (96, 74, 52), None)
            rig.poly([(head[0] + 0.6, head[1] + 3.0), (head[0] + 7.2, head[1] + 3.2), (head[0] + 7.2, head[1] + 4.6), (head[0] + 0.6, head[1] + 4.4)], (230, 230, 230), line, 0.4)
        elif kind == 'knife':
            # pañuelo rojo con cola ondeante
            fl = math.sin(t * 3.0) * 1.4
            rig.poly([(head[0] - 6.6, head[1] + 3.2), (head[0] + 6.4, head[1] + 3.8), (head[0] + 6.2, head[1] + 6.4), (head[0] - 6.4, head[1] + 6.0)], helm, line, 0.6)
            rig.poly([(head[0] - 6.4, head[1] + 4.4), (head[0] - 12.6, head[1] + 2.4 + fl), (head[0] - 13.6, head[1] + 4.6 + fl), (head[0] - 6.4, head[1] + 6.2)], _dk(helm, 16), line, 0.5)
            rig.poly([(head[0] - 5, head[1] + 6.2), (head[0] + 3, head[1] + 9.6), (head[0] + 5.6, head[1] + 6.4)], _dk(skin, 70), None)
            for k_ in range(5):
                rig.poly([(head[0] - 4 + k_ * 2.6, head[1] + 6.0), (head[0] - 3 + k_ * 2.6, head[1] + 9.6), (head[0] - 2 + k_ * 2.6, head[1] + 6.0)], (50, 34, 30), None)
        else:
            # casco
            hc = helm
            rig.poly([(head[0] - 7.8, head[1] + 1.2), (head[0] - 7.4, head[1] + 6.4), (head[0] - 3.6, head[1] + 9.8), (head[0] + 2.8, head[1] + 10.0),
                      (head[0] + 7.0, head[1] + 6.8), (head[0] + 7.6, head[1] + 3.2), (head[0] + 1.6, head[1] + 3.2)], hc, line)
            rig.poly([(head[0] - 6.6, head[1] + 6.0), (head[0] - 3.2, head[1] + 9.0), (head[0] + 2.0, head[1] + 9.2), (head[0] - 2.0, head[1] + 7.2)], shade(hc, 28), None)
            rig.poly([(head[0] - 8.2, head[1] + 1.0), (head[0] + 8.2, head[1] + 2.6), (head[0] + 8.0, head[1] + 3.6), (head[0] - 8.0, head[1] + 2.4)], _dk(hc, 22), line, 0.5)
            rig.cap((head[0] + 1.5, head[1] + 3.0), (head[0] + 1.8, head[1] - 4.4), 0.7, (30, 26, 24), None)           # correa
            if kind == 'player':
                rig.poly([(head[0] + 2.2, head[1] + 5.0), (head[0] + 6.6, head[1] + 5.4), (head[0] + 6.6, head[1] + 7.6), (head[0] + 2.2, head[1] + 7.4)], (60, 150, 210), (20, 30, 40), 0.5)
                rig.cap((head[0] + 1, head[1] - 3.4), (head[0] + 5.2, head[1] - 4.4), 0.7, (30, 30, 34), None)                  # micrófono
            elif heavy:
                rig.poly([(head[0] + 1.2, head[1] - 6.2), (head[0] + 7.2, head[1] - 5.8), (head[0] + 7.0, head[1] - 0.6), (head[0] + 1.0, head[1] - 1.4)], (96, 100, 104), line, 0.6)      # máscara
                rig.poly([(head[0] + 2.0, head[1] + 2.4), (head[0] + 7.4, head[1] + 2.6), (head[0] + 7.0, head[1] + 0.4), (head[0] + 2.0, head[1] + 0.2)], (230, 90, 70), None)      # visor
    surf = rig.finish()
    s_ang = math.radians(fall)
    sx_, sy_ = sh
    shx = sx_ * math.cos(s_ang) - sy_ * math.sin(s_ang)
    shy = sx_ * math.sin(s_ang) + sy_ * math.cos(s_ang)
    return surf, shx * PT_K, shy * PT_K


def _arm_layer(kind, mode):
    """Brazos + arma apuntando a +x con el hombro en (cx, cy) del lienzo."""
    look = PT_LOOK[kind]
    rig = _Rig(0.0, 170, 170, 85, 85)
    line = (20, 18, 24)
    body, skin = look['body'], look['skin']
    sl = _dk(body, 22)
    if mode == 'shield':
        rig.cap((0, 0), (5, -7), 4.6, sl, line)
        rig.cap((5, -7), (16, -3), 4.2, sl, line)
        rig.poly([(14, 16), (25, 14), (25, -54), (14, -52)], (92, 102, 116), line, 0.9)
        rig.poly([(14, 16), (17.4, 15.6), (17.4, -52), (14, -52)], (156, 166, 180), None)
        rig.poly([(17.6, 9.4), (23.4, 9.2), (23.4, 6.2), (17.6, 6.4)], (130, 200, 226), line, 0.4)
        for k_ in range(3):
            rig.poly([(17.6, -8 - k_ * 9), (23.4, -3 - k_ * 9), (23.4, -6.6 - k_ * 9), (17.6, -11.6 - k_ * 9)], (232, 196, 50), None)
        rig.circ((16, -3), 2.6, (34, 30, 30), line, 0.5)
    elif mode == 'gun' and kind == 'flame':
        rig.cap((0, 0), (3.5, -7.5), 4.6, _dk(sl, 28), line)
        rig.cap((3.5, -7.5), (13, -3.2), 4.2, _dk(sl, 28), line)
        rig.poly([(-6, -3.2), (4, -3.6), (4, 3.4), (-6, 3.6)], (60, 56, 52), line, 0.6)
        rig.poly([(4, -2.6), (40, -2.0), (40, 2.0), (4, 2.6)], (50, 52, 58), line, 0.6)
        rig.poly([(40, -3.4), (48, -4.2), (48, 4.2), (40, 3.4)], (210, 90, 40), line, 0.6)
        rig.circ((49, 0), 1.8, (255, 220, 120), None)
        rig.cap((0, 0.8), (9, -8.8), 4.8, sl, line)
        rig.cap((9, -8.8), (30, -2.0), 4.4, sl, line)
        rig.circ((30, -1.4), 2.7, (34, 30, 30), line, 0.5)
        rig.circ((13, -2.6), 2.5, (34, 30, 30), line, 0.5)
    elif mode == 'gun':
        long = kind == 'sniper'
        # brazo trasero (apoyo / gatillo) detrás del arma
        rig.cap((0, 0), (3.5, -7.5), 4.6, _dk(sl, 28), line)
        rig.cap((3.5, -7.5), (13, -3.2), 4.2, _dk(sl, 28), line)
        # arma
        if kind == 'player':
            wood, mc = (60, 64, 70), (30, 32, 36)
        elif kind == 'sniper':
            wood, mc = (86, 70, 50), (38, 40, 44)
        else:
            wood, mc = (112, 76, 44), (36, 36, 40)
        L = 74 if long else 52
        rig.poly([(-12, -4.2), (4, -3.0), (4, 3.2), (-12, 4.0)], wood, line, 0.6)                                         # culata
        rig.poly([(-12, -4.2), (-9.4, -4.4), (-9.4, 4.2), (-12, 4.0)], _dk(wood, 30), None)
        rig.poly([(4, -4), (26, -4), (26, 3.6), (4, 3.6)], mc, line, 0.6)                                                   # receptor
        rig.poly([(7, 3.6), (20, 3.6), (20, 5.2), (7, 5.2)], (22, 22, 26), None)                                            # riel
        rig.poly([(26, -3), (L - 6, -2.6), (L - 6, 2.0), (26, 2.4)], wood if kind != 'player' else (52, 56, 62), line, 0.6)      # guardamanos
        rig.poly([(L - 6, -1.2), (L + 6, -1.0), (L + 6, 0.8), (L - 6, 1.0)], (24, 24, 28), line, 0.5)                      # cañón
        rig.poly([(L + 6, -2.0), (L + 10, -2.0), (L + 10, 1.8), (L + 6, 1.8)], (20, 20, 24), None)                          # freno
        rig.poly([(12, -4), (19, -4), (21, -14), (14.4, -13)], _dk(mc, 4), line, 0.6)                                       # cargador
        rig.poly([(8, 5.2), (11, 5.2), (11, 8.6), (8, 8.6)], (24, 24, 30), None)                                            # mira
        if long:
            rig.poly([(14, 5.2), (32, 5.2), (32, 9.6), (14, 9.6)], (26, 28, 34), line, 0.6)                                 # mira telescópica
            rig.circ((32.5, 7.4), 2.6, (90, 170, 220), (20, 20, 24), 0.5)
            rig.cap((L - 10, 2), (L - 12, -7.5), 0.9, (30, 30, 34), None)                                                   # bípode
            rig.cap((L - 10, 2), (L - 6, -7.5), 0.9, (30, 30, 34), None)
        elif kind == 'player':
            rig.circ((17, 7.4), 1.8, (240, 70, 60), None)
        # brazo delantero sobre el arma
        gx = L - 18 if long else 33
        rig.cap((0, 0.8), (9, -8.8), 4.8, sl, line)
        rig.cap((9, -8.8), (gx, -1.8), 4.4, sl, line)
        rig.circ((gx, -1.2), 2.7, (34, 30, 30), line, 0.5)
        rig.circ((13, -2.6), 2.5, (34, 30, 30), line, 0.5)
    elif mode == 'knife':
        rig.cap((0, 0), (9, -6.5), 4.6, sl, line)
        rig.cap((9, -6.5), (22, -1.0), 4.2, sl, line)
        rig.circ((23.4, -0.6), 2.7, skin, line, 0.5)
        rig.poly([(24.4, -1.6), (27.6, -1.6), (27.6, 1.0), (24.4, 1.0)], (46, 36, 30), line, 0.4)
        rig.poly([(27.4, -1.4), (45.4, -0.6), (27.4, 1.0)], (206, 212, 220), line, 0.5)
        rig.poly([(27.4, -0.8), (42, -0.2), (27.4, 0.2)], (255, 255, 255), None)
        rig.cap((0, 0.5), (6, -9), 4.6, _dk(sl, 24), line)
        rig.circ((7, -9.6), 2.5, skin, line, 0.5)
    elif mode in ('wind', 'rel'):
        # lanzamiento de granada
        if mode == 'wind':
            rig.cap((0, 0), (-7, 8), 4.6, sl, line)
            rig.cap((-7, 8), (-5, 19), 4.2, sl, line)
            hand = (-4.4, 21.2)
        else:
            rig.cap((0, 0), (9, 5), 4.6, sl, line)
            rig.cap((9, 5), (19, 11), 4.2, sl, line)
            hand = (21, 12.2)
        rig.circ(hand, 2.8, skin, line, 0.5)
        rig.circ((hand[0] + 1, hand[1] + 3.4), 3.2, (70, 100, 56), line, 0.5)
        rig.cap((hand[0] + 1, hand[1] + 6.2), (hand[0] + 1, hand[1] + 7.6), 1.0, (180, 180, 180), None)
        rig.cap((0, 0.5), (4, -8), 4.6, _dk(sl, 24), line)
        rig.circ((5.2, -9.4), 2.4, skin, line, 0.5)
    return rig.finish()


def build_pt_art():
    """Pre-renderiza todos los cuadros de los soldados (lado derecho; el izquierdo se espeja)."""
    art = {'body': {}, 'arm': {}, 'rot': {}}
    for kind in PT_LOOK:
        frames = {}
        for pose, n in (('run', 8), ('idle', 4), ('crouch', 1), ('jump', 1), ('fall', 1), ('die', 6)):
            frames[pose] = [_body_frame(kind, pose, i, i * 0.5) for i in range(n)]
        art['body'][kind] = frames
        modes = {'shield': ['shield'], 'flame': ['gun'], 'pow': [], 'knife': ['knife', 'wind', 'rel']}.get(kind) or (['gun'] if kind in ('player', 'rifle', 'sniper') else ['gun', 'wind', 'rel'])
        if kind == 'pow':
            modes = []
        art['arm'][kind] = {m: _arm_layer(kind, m) for m in modes}
        if kind in ('shield', 'flame', 'pow'):
            continue
        if 'wind' not in art['arm'][kind]:
            art['arm'][kind]['wind'] = _arm_layer(kind, 'wind')
            art['arm'][kind]['rel'] = _arm_layer(kind, 'rel')
    return art


# ------------------------------------------------------------------ arte del asalto, parte 2: tanque, torreta, contenedores y decorado
def _smooth(surf, k):
    return pygame.transform.smoothscale(surf, (surf.get_width() // k, surf.get_height() // k))


def _lin_poly(s, pts, col, out=None, ow=2):
    pygame.draw.polygon(s, col, pts)
    if out is not None:
        pygame.draw.polygon(s, out, pts, ow)


def build_pt_tank():
    """Tanque lateral mirando a la derecha: 8 cuadros de orugas, torreta y cañón por separado."""
    K = 3
    TW, TH = 360, 190
    gx, gy = 190, 176                     # centro y suelo
    out = (16, 20, 16)
    base, dark, light = (88, 104, 80), (60, 74, 56), (122, 140, 106)
    tan = (150, 138, 96)
    hulls = []
    for fi in range(8):
        s = pygame.Surface((TW * K, TH * K), pygame.SRCALPHA)
        P = lambda x, y: ((gx + x) * K, (gy - y) * K)
        # sombra
        pygame.draw.ellipse(s, (0, 0, 0, 90), ((gx - 150) * K, (gy - 8) * K, 300 * K, 18 * K))
        # orugas: cuerpo
        tr = [P(-136, 14), P(-118, 2), P(118, 2), P(140, 14), P(140, 40), P(120, 52), P(-120, 52), P(-138, 40)]
        _lin_poly(s, tr, (30, 32, 30), out, 3 * K // 2)
        # eslabones animados
        off = fi * (14 / 8)
        for k in range(-20, 21):
            x = -140 + (k * 14 + off) % 280
            pygame.draw.line(s, (62, 66, 60), P(x, 4), P(x, 14), 2 * K)
            pygame.draw.line(s, (62, 66, 60), P(x, 40), P(x, 50), 2 * K)
        # ruedas
        for i in range(7):
            wx = -100 + i * 33
            pygame.draw.circle(s, (20, 22, 20), P(wx, 28), 17 * K)
            pygame.draw.circle(s, (54, 60, 54), P(wx, 28), 15 * K)
            pygame.draw.circle(s, (84, 92, 82), P(wx, 28), 8 * K)
            for a in range(6):
                ang = 1.0472 * a + fi * 0.18
                pygame.draw.circle(s, (30, 34, 30), (P(wx, 28)[0] + math.cos(ang) * 5 * K, P(wx, 28)[1] + math.sin(ang) * 5 * K), 1.6 * K)
        for wx in (-130, 128):          # rueda guía y motriz
            pygame.draw.circle(s, (20, 22, 20), P(wx, 30), 14 * K)
            pygame.draw.circle(s, (70, 76, 68), P(wx, 30), 9 * K)
            pygame.draw.circle(s, (30, 34, 30), P(wx, 30), 4 * K)
        for rx in (-70, 0, 70):         # rodillos superiores
            pygame.draw.circle(s, (46, 50, 46), P(rx, 50), 6 * K)
        # faldones
        sk = [P(-132, 52), P(124, 52), P(136, 60), P(-120, 64)]
        _lin_poly(s, sk, dark, out, K)
        # casco inferior y superior
        hull = [P(-134, 52), P(-126, 78), P(80, 84), P(132, 70), P(142, 56), P(130, 50)]
        _lin_poly(s, hull, base, out, 3 * K // 2)
        glacis = [P(80, 84), P(132, 70), P(140, 58), P(100, 62)]
        _lin_poly(s, glacis, light, out, K)
        deck = [P(-126, 78), P(80, 84), P(70, 90), P(-110, 88)]
        _lin_poly(s, deck, light, None)
        # camuflaje
        rnd = random.Random(4)
        for _ in range(9):
            cx, cy = rnd.uniform(-110, 100), rnd.uniform(58, 78)
            pygame.draw.ellipse(s, tan if rnd.random() < 0.6 else dark, (P(cx - 16, cy + 4)[0], P(cx, cy + 4)[1], 32 * K, 8 * K))
        # remaches y líneas de panel
        for rx in range(-120, 120, 18):
            pygame.draw.circle(s, shade(base, -34), P(rx, 64), 1.5 * K)
        pygame.draw.line(s, shade(base, -40), P(-60, 54), P(-56, 80), K)
        pygame.draw.line(s, shade(base, -40), P(40, 56), P(48, 82), K)
        # rejilla del motor y escapes (atrás = izquierda)
        for gxx in range(-118, -78, 7):
            pygame.draw.line(s, (26, 30, 26), P(gxx, 68), P(gxx + 3, 80), 2 * K)
        pygame.draw.rect(s, (36, 40, 36), (P(-142, 76)[0], P(-142, 76)[1], 12 * K, 8 * K))
        pygame.draw.rect(s, (36, 40, 36), (P(-142, 66)[0], P(-142, 66)[1], 12 * K, 8 * K))
        # eslabones de repuesto y faro
        for k in range(4):
            pygame.draw.rect(s, (46, 50, 44), (P(96 + k * 9, 74 - k * 3)[0], P(0, 74 - k * 3)[1], 7 * K, 5 * K))
        pygame.draw.circle(s, (255, 236, 160), P(136, 66), 3.5 * K)
        pygame.draw.circle(s, out, P(136, 66), 3.5 * K, K)
        # ametralladora del casco
        pygame.draw.line(s, (24, 26, 24), P(124, 72), P(150, 76), 3 * K)
        hulls.append(_smooth(s, K))
    # torreta
    s = pygame.Surface((TW * K, TH * K), pygame.SRCALPHA)
    P = lambda x, y: ((gx + x) * K, (gy - y) * K)
    tur = [P(-62, 86), P(-70, 100), P(-52, 126), P(-6, 138), P(40, 134), P(70, 120), P(84, 104), P(80, 88)]
    _lin_poly(s, tur, base, out, 3 * K // 2)
    top = [P(-52, 126), P(-6, 138), P(40, 134), P(70, 120), P(40, 124), P(-6, 130), P(-48, 120)]
    _lin_poly(s, top, light, None)
    low = [P(-62, 86), P(80, 88), P(84, 104), P(-70, 100)]
    _lin_poly(s, low, dark, out, K)
    pygame.draw.line(s, shade(base, -44), P(-66, 94), P(82, 96), 2 * K)
    for rx in range(-56, 76, 14):
        pygame.draw.circle(s, shade(base, -34), P(rx, 112), 1.4 * K)
    # cúpula del comandante + ametralladora
    pygame.draw.ellipse(s, dark, (P(-44, 150)[0], P(0, 150)[1], 36 * K, 14 * K))
    pygame.draw.rect(s, base, (P(-42, 144)[0], P(0, 144)[1], 32 * K, 12 * K), border_radius=3 * K)
    pygame.draw.rect(s, out, (P(-42, 144)[0], P(0, 144)[1], 32 * K, 12 * K), K, border_radius=3 * K)
    for bx in range(-40, -12, 7):
        pygame.draw.rect(s, (110, 180, 200), (P(bx, 142)[0], P(0, 142)[1], 4 * K, 4 * K))
    pygame.draw.line(s, (24, 26, 24), P(-20, 152), P(6, 158), 3 * K)
    pygame.draw.circle(s, (24, 26, 24), P(-22, 152), 3 * K)
    # escotilla del cargador, antena, lanzahumos
    pygame.draw.rect(s, shade(base, -10), (P(18, 138)[0], P(0, 138)[1], 26 * K, 6 * K), border_radius=2 * K)
    pygame.draw.line(s, (30, 30, 30), P(-58, 124), P(-62, 190 - 2), K)
    pygame.draw.polygon(s, (220, 60, 50), [P(-62, 180), P(-84, 175), P(-62, 170)])
    for k in range(3):
        pygame.draw.rect(s, (36, 40, 36), (P(-76, 118 - k * 5)[0], P(0, 118 - k * 5)[1], 7 * K, 3 * K))
    # mantelete
    man = [P(66, 94), P(92, 98), P(94, 124), P(66, 124)]
    _lin_poly(s, man, shade(base, -14), out, 2 * K)
    # compartimento de equipaje trasero
    bag = [P(-86, 90), P(-62, 90), P(-62, 108), P(-90, 106)]
    _lin_poly(s, bag, shade(tan, -20), out, K)
    turret = _smooth(s, K)
    # cañón
    s = pygame.Surface((TW * K, 60 * K), pygame.SRCALPHA)
    cy = 30 * K
    pygame.draw.rect(s, out, (0, cy - 8 * K, 150 * K, 16 * K), border_radius=2 * K)
    pygame.draw.rect(s, (62, 68, 62), (2 * K, cy - 6 * K, 146 * K, 12 * K))
    pygame.draw.rect(s, (96, 104, 94), (2 * K, cy - 6 * K, 146 * K, 4 * K))
    pygame.draw.rect(s, (46, 52, 46), (60 * K, cy - 10 * K, 28 * K, 20 * K), border_radius=3 * K)              # extractor de humos
    pygame.draw.rect(s, (80, 88, 78), (60 * K, cy - 10 * K, 28 * K, 6 * K), border_radius=3 * K)
    pygame.draw.rect(s, (30, 34, 30), (136 * K, cy - 11 * K, 24 * K, 22 * K), border_radius=2 * K)             # freno de boca
    for k in range(3):
        pygame.draw.line(s, (60, 66, 60), ((140 + k * 6) * K, cy - 11 * K), ((140 + k * 6) * K, cy + 11 * K), 2 * K)
    barrel = _smooth(s, K)
    return dict(hull=hulls, turret=turret, barrel=barrel, gx=gx, gy=gy, pivot=(gx + 80, gy - 111))


def build_pt_bunker():
    """Torreta de ametralladora tras sacos de arena; el cañón se rota aparte."""
    K = 3
    s = pygame.Surface((110 * K, 70 * K), pygame.SRCALPHA)
    out = (28, 22, 16)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (4 * K, 58 * K, 102 * K, 10 * K))
    # base de hormigón
    pygame.draw.rect(s, (110, 112, 112), (22 * K, 40 * K, 66 * K, 22 * K), border_radius=3 * K)
    pygame.draw.rect(s, out, (22 * K, 40 * K, 66 * K, 22 * K), K, border_radius=3 * K)
    # sacos de arena
    rnd = random.Random(2)
    for row in range(3):
        for i in range(5 - row):
            x = 8 * K + (i * 20 + row * 10) * K
            y = (60 - row * 11) * K
            col = rnd.choice(((186, 160, 108), (172, 146, 96), (196, 170, 118)))
            pygame.draw.ellipse(s, col, (x, y - 10 * K, 22 * K, 12 * K))
            pygame.draw.ellipse(s, out, (x, y - 10 * K, 22 * K, 12 * K), K)
            pygame.draw.line(s, shade(col, -30), (x + 4 * K, y - 4 * K), (x + 18 * K, y - 4 * K), K)
    base = _smooth(s, K)
    s = pygame.Surface((70 * K, 24 * K), pygame.SRCALPHA)
    pygame.draw.rect(s, out, (0, 6 * K, 66 * K, 12 * K), border_radius=2 * K)
    pygame.draw.rect(s, (64, 68, 64), (2 * K, 8 * K, 62 * K, 8 * K))
    pygame.draw.rect(s, (112, 118, 110), (2 * K, 8 * K, 62 * K, 3 * K))
    pygame.draw.rect(s, (26, 28, 26), (54 * K, 4 * K, 14 * K, 16 * K), border_radius=2 * K)
    pygame.draw.rect(s, (84, 90, 82), (-1 * K + 1, 3 * K, 20 * K, 18 * K), border_radius=3 * K)
    pygame.draw.rect(s, out, (0, 3 * K, 20 * K, 18 * K), K, border_radius=3 * K)
    gun = _smooth(s, K)
    return dict(base=base, gun=gun)


def build_pt_containers():
    """Contenedores de carga con ondulado, puertas y óxido (varios colores y largos)."""
    out = {}
    cols = [(176, 70, 56), (62, 112, 168), (214, 168, 56), (74, 140, 100), (150, 90, 60)]
    for ci, col in enumerate(cols):
        for w in (150, 225):
            K = 2
            s = pygame.Surface((w * K, 64 * K), pygame.SRCALPHA)
            rnd = random.Random(ci * 7 + w)
            for y in range(64 * K):
                f = y / (64 * K)
                c = shade(col, int(26 - 62 * f))
                pygame.draw.line(s, c, (0, y), (w * K, y))
            for x in range(8 * K, (w - 4) * K, 7 * K):          # ondulado
                pygame.draw.line(s, shade(col, -40), (x, 8 * K), (x, 58 * K), K)
                pygame.draw.line(s, shade(col, 26), (x + K, 8 * K), (x + K, 58 * K), K)
            pygame.draw.rect(s, shade(col, -52), (0, 0, w * K, 64 * K), 3 * K)
            pygame.draw.rect(s, shade(col, 34), (0, 0, w * K, 6 * K))
            pygame.draw.rect(s, shade(col, -64), (0, 58 * K, w * K, 6 * K))
            for cx in (0, w * K - 12 * K):                        # esquineros
                pygame.draw.rect(s, shade(col, -70), (cx, 0, 12 * K, 64 * K))
                pygame.draw.rect(s, (200, 200, 190), (cx + 3 * K, 5 * K, 6 * K, 5 * K))
            for hx in ((w - 40) * K, (w - 28) * K):               # manijas
                pygame.draw.line(s, (40, 40, 44), (hx, 14 * K), (hx, 52 * K), 2 * K)
            for _ in range(5):                                    # óxido
                rx = rnd.randint(14, w - 20) * K
                pygame.draw.line(s, (110, 62, 36), (rx, 8 * K), (rx + rnd.randint(-3, 3) * K, rnd.randint(20, 40) * K), 2 * K)
            pygame.draw.rect(s, (236, 236, 226), (18 * K, 16 * K, 36 * K, 10 * K))
            pygame.draw.rect(s, (30, 30, 34), (18 * K, 16 * K, 36 * K, 10 * K), K)
            out[(ci, w)] = _smooth(s, K)
    return out


def build_pt_decor():
    """Barriles, cajas, bolardos, farolas, vallas: elementos de decorado del muelle."""
    D = {}
    K = 3
    # barril
    s = pygame.Surface((34 * K, 46 * K), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 80), (2 * K, 42 * K, 30 * K, 4 * K))
    pygame.draw.rect(s, (150, 60, 40), (4 * K, 6 * K, 26 * K, 36 * K), border_radius=4 * K)
    pygame.draw.rect(s, (200, 96, 60), (6 * K, 6 * K, 7 * K, 36 * K))
    for y in (12, 24, 34):
        pygame.draw.line(s, (90, 36, 26), (4 * K, y * K), (30 * K, y * K), 2 * K)
    pygame.draw.ellipse(s, (170, 70, 46), (4 * K, 2 * K, 26 * K, 9 * K))
    pygame.draw.ellipse(s, (90, 36, 26), (4 * K, 2 * K, 26 * K, 9 * K), K)
    pygame.draw.rect(s, (240, 220, 80), (12 * K, 18 * K, 10 * K, 8 * K))
    D['barrel'] = _smooth(s, K)
    # cajas de madera apiladas
    s = pygame.Surface((70 * K, 66 * K), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 80), (0, 62 * K, 70 * K, 4 * K))
    for (bx, by, bw, bh) in ((0, 30, 36, 34), (34, 30, 36, 34), (14, 0, 38, 32)):
        pygame.draw.rect(s, (156, 116, 70), (bx * K, by * K, bw * K, bh * K))
        pygame.draw.rect(s, (96, 66, 38), (bx * K, by * K, bw * K, bh * K), 2 * K)
        pygame.draw.line(s, (110, 78, 46), (bx * K, by * K), ((bx + bw) * K, (by + bh) * K), 2 * K)
        pygame.draw.line(s, (110, 78, 46), (bx * K, (by + bh) * K), ((bx + bw) * K, by * K), 2 * K)
        pygame.draw.rect(s, (190, 150, 100), (bx * K, by * K, bw * K, 3 * K))
    D['crates'] = _smooth(s, K)
    # farola
    s = pygame.Surface((60 * K, 190 * K), pygame.SRCALPHA)
    pygame.draw.rect(s, (46, 48, 54), (28 * K, 20 * K, 5 * K, 168 * K))
    pygame.draw.rect(s, (70, 72, 80), (28 * K, 20 * K, 2 * K, 168 * K))
    pygame.draw.rect(s, (46, 48, 54), (22 * K, 180 * K, 17 * K, 8 * K))
    pygame.draw.polygon(s, (46, 48, 54), [(30 * K, 22 * K), (12 * K, 14 * K), (12 * K, 20 * K), (30 * K, 28 * K)])
    pygame.draw.ellipse(s, (255, 230, 150), (4 * K, 14 * K, 18 * K, 8 * K))
    D['lamp'] = _smooth(s, K)
    # bolardo / amarre
    s = pygame.Surface((30 * K, 28 * K), pygame.SRCALPHA)
    pygame.draw.rect(s, (60, 62, 66), (8 * K, 6 * K, 14 * K, 20 * K), border_radius=4 * K)
    pygame.draw.rect(s, (240, 200, 40), (8 * K, 10 * K, 14 * K, 5 * K))
    pygame.draw.ellipse(s, (84, 86, 92), (4 * K, 2 * K, 22 * K, 8 * K))
    D['bollard'] = _smooth(s, K)
    # valla con alambre de púas
    s = pygame.Surface((160 * K, 60 * K), pygame.SRCALPHA)
    for x in range(0, 161, 40):
        pygame.draw.rect(s, (60, 62, 64), (x * K - K, 6 * K, 3 * K, 54 * K))
    for y in range(12, 54, 9):
        pygame.draw.line(s, (120, 124, 130), (0, y * K), (160 * K, y * K), K)
    for x in range(0, 160, 10):
        pygame.draw.line(s, (90, 94, 100), (x * K, 12 * K), ((x + 10) * K, 54 * K), K)
    for x in range(4, 160, 12):
        pygame.draw.line(s, (170, 174, 180), (x * K, 3 * K), ((x + 4) * K, 8 * K), K)
        pygame.draw.line(s, (170, 174, 180), (x * K, 8 * K), ((x + 4) * K, 3 * K), K)
    pygame.draw.line(s, (160, 164, 170), (0, 5 * K), (160 * K, 5 * K), 2 * K)
    D['fence'] = _smooth(s, K)
    # sacos de arena (muro bajo)
    s = pygame.Surface((90 * K, 38 * K), pygame.SRCALPHA)
    rnd = random.Random(5)
    for row in range(2):
        for i in range(4 - row):
            x = (i * 22 + row * 11) * K
            y = (24 - row * 12) * K
            col = rnd.choice(((186, 160, 108), (172, 146, 96), (196, 170, 118)))
            pygame.draw.ellipse(s, col, (x, y, 24 * K, 14 * K))
            pygame.draw.ellipse(s, (60, 46, 30), (x, y, 24 * K, 14 * K), K)
    D['sandbags'] = _smooth(s, K)
    return D


def build_pt_bg(W, GR, L):
    """Capas del fondo: cielo, mar, siluetas lejanas, almacenes y grúas (con paralaje)."""
    rnd = random.Random(8)
    sky = pygame.Surface((W, GR))
    for y in range(GR):
        f = y / GR
        pygame.draw.line(sky, (int(lerp(34, 250, f ** 1.7)), int(lerp(26, 150, f ** 1.6)), int(lerp(80, 128, f))), (0, y), (W, y))
    for _ in range(70):
        pygame.draw.circle(sky, (255, 255, 255), (rnd.randrange(W), rnd.randrange(0, 280)), rnd.choice((1, 1, 2)))
    cl = pygame.Surface((W, GR), pygame.SRCALPHA)
    for _ in range(9):
        cx, cy = rnd.randrange(-100, W), rnd.randrange(120, 420)
        for k in range(6):
            pygame.draw.ellipse(cl, (255, 168, 140, 40), (cx + k * 30, cy + rnd.randint(-6, 6), rnd.randint(120, 260), rnd.randint(14, 26)))
    sky.blit(cl, (0, 0))
    glow_s = pygame.Surface((420, 420), pygame.SRCALPHA)
    for r in range(210, 0, -6):
        pygame.draw.circle(glow_s, (255, 190, 120, int(60 * (1 - r / 210) ** 1.5)), (210, 210), r)
    sky.blit(glow_s, (760 - 210, 392 - 210))
    pygame.draw.circle(sky, (255, 224, 170), (760, 392), 72)
    pygame.draw.circle(sky, (255, 244, 214), (760, 392), 52)
    sea = pygame.Surface((W, 230))
    for y in range(230):
        f = y / 230
        pygame.draw.line(sea, (int(lerp(168, 22, f ** 0.8)), int(lerp(112, 50, f ** 0.8)), int(lerp(126, 96, f))), (0, y), (W, y))
    # reflejo del sol (columna)
    for k in range(28):
        w = int(60 - k * 1.6)
        pygame.draw.line(sea, (255, 206, 150), (760 - w // 2, 8 + k * 7), (760 + w // 2, 8 + k * 7), 2)
    # capa lejana: montañas, barcos y faro
    fw = int(L * 0.18) + W
    far = pygame.Surface((fw, 230), pygame.SRCALPHA)
    for i in range(0, fw, 220):
        h = rnd.randint(40, 120)
        pygame.draw.polygon(far, (86, 62, 104, 255), [(i - 30, 230), (i + 90, 230 - h), (i + 230, 230)])
    for i in range(80, fw, 560):
        hw = rnd.randint(150, 220)
        pygame.draw.polygon(far, (52, 46, 76, 255), [(i, 176), (i + hw, 176), (i + hw - 30, 204), (i + 20, 204)])
        pygame.draw.rect(far, (62, 56, 88, 255), (i + hw // 2 - 30, 150, 60, 26))
        pygame.draw.rect(far, (72, 66, 98, 255), (i + hw // 2 - 14, 128, 28, 22))
        for wx in range(i + 20, i + hw - 20, 24):
            pygame.draw.rect(far, (250, 210, 130, 255), (wx, 188, 5, 4))
        pygame.draw.line(far, (62, 56, 88, 255), (i + hw // 2, 128), (i + hw // 2, 108), 2)
    for i in range(300, fw, 900):          # faro
        pygame.draw.polygon(far, (110, 90, 120, 255), [(i, 230), (i + 14, 230), (i + 11, 140), (i + 3, 140)])
        pygame.draw.rect(far, (255, 220, 130, 255), (i + 2, 130, 10, 10))
    # capa media: almacenes, tanques, grúas y pilas de contenedores
    mw = int(L * 0.5) + W
    mid = pygame.Surface((mw, 330), pygame.SRCALPHA)
    x = 0
    while x < mw:
        kind = rnd.choice(('wh', 'wh', 'crane', 'tank', 'stack'))
        if kind == 'wh':
            w, h = rnd.randint(220, 380), rnd.randint(100, 170)
            for y in range(h):
                c = int(lerp(98, 66, y / h))
                pygame.draw.line(mid, (c, int(c * 0.78), int(c * 1.1), 255), (x, 330 - h + y), (x + w, 330 - h + y))
            pygame.draw.polygon(mid, (70, 54, 88, 255), [(x - 8, 330 - h), (x + w + 8, 330 - h), (x + w - 14, 330 - h - 22), (x + 14, 330 - h - 22)])
            for wx in range(x + 16, x + w - 24, 40):
                lit = rnd.random() < 0.7
                pygame.draw.rect(mid, (252, 204, 116, 255) if lit else (46, 38, 62, 255), (wx, 330 - h + 26, 20, 16))
                pygame.draw.rect(mid, (40, 32, 56, 255), (wx, 330 - h + 26, 20, 16), 1)
            dw = min(80, w // 2)
            pygame.draw.rect(mid, (52, 42, 68, 255), (x + w // 2 - dw // 2, 330 - 64, dw, 64))
            for k in range(1, 8):
                pygame.draw.line(mid, (70, 58, 88, 255), (x + w // 2 - dw // 2, 330 - 64 + k * 8), (x + w // 2 + dw // 2, 330 - 64 + k * 8))
            pygame.draw.rect(mid, (60, 50, 78, 255), (x + w - 34, 330 - h - 40, 8, 40))
            x += w + rnd.randint(30, 110)
        elif kind == 'crane':
            pygame.draw.polygon(mid, (130, 78, 76, 255), [(x, 330), (x + 12, 330), (x + 18, 60), (x + 8, 60)])
            pygame.draw.polygon(mid, (130, 78, 76, 255), [(x + 90, 330), (x + 102, 330), (x + 96, 60), (x + 86, 60)])
            for yy in range(80, 320, 36):
                pygame.draw.line(mid, (110, 66, 64, 255), (x + 10, yy), (x + 94, yy + 36), 3)
                pygame.draw.line(mid, (110, 66, 64, 255), (x + 94, yy), (x + 10, yy + 36), 3)
            pygame.draw.rect(mid, (150, 92, 84, 255), (x - 90, 46, 330, 16))
            pygame.draw.rect(mid, (210, 100, 70, 255), (x + 36, 62, 34, 22))
            pygame.draw.line(mid, (220, 220, 230, 255), (x + 180, 62), (x + 180, 170), 2)
            pygame.draw.rect(mid, (220, 110, 70, 255), (x + 166, 170, 30, 22))
            pygame.draw.circle(mid, (255, 70, 60, 255), (x + 240, 46), 4)
            x += 280
        elif kind == 'tank':
            pygame.draw.ellipse(mid, (92, 76, 110, 255), (x, 190, 140, 120))
            pygame.draw.rect(mid, (92, 76, 110, 255), (x, 250, 140, 80))
            for k in range(1, 5):
                pygame.draw.line(mid, (70, 58, 88, 255), (x, 250 + k * 16), (x + 140, 250 + k * 16))
            pygame.draw.line(mid, (70, 58, 88, 255), (x + 70, 190), (x + 70, 160), 3)
            x += 190
        else:
            for row in range(3):
                for i in range(3 - row // 2):
                    col = rnd.choice(((130, 70, 66), (62, 86, 130), (150, 120, 62), (70, 110, 90)))
                    pygame.draw.rect(mid, (*col, 255), (x + i * 64 + row * 0, 330 - (row + 1) * 40, 62, 38))
                    pygame.draw.rect(mid, (30, 26, 40, 255), (x + i * 64, 330 - (row + 1) * 40, 62, 38), 2)
            x += 220
    fog = pygame.Surface((mw, 330), pygame.SRCALPHA)
    for y in range(330):
        a = int(70 * (y / 330) ** 2)
        pygame.draw.line(fog, (200, 120, 130, a), (0, y), (mw, y))
    mid.blit(fog, (0, 0))
    return dict(sky=sky, sea=sea, far=far, mid=mid)


def build_pt_wreck_fx():
    """Casquillos y destellos pequeños."""
    return {}


def make_shadow(surf):
    sh = surf.copy()
    sh.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return sh


# ======================================================================= JUEGO
class Game:
    def __init__(self):
        pygame.display.set_caption('FINAL LEGACY - Edición Omar Brondo')
        self.screen = pygame.display.set_mode((W, H))
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        names = 'couriernew,consolas,dejavusansmono,liberationmono,monospace'
        mk = lambda s: pygame.font.SysFont(names, s, bold=True)
        self.f_s, self.f_m, self.f_l, self.f_xl = mk(15), mk(20), mk(32), mk(80)
        self.screen.fill((6, 10, 22))
        self.text(self.screen, 'CARGANDO SONIDOS Y GRAFICOS...', self.f_m, (160, 200, 255), W // 2, H // 2 - 10, 'c')
        pygame.display.flip()
        self.audio = Audio()
        self.build_assets()
        self.panels = {}
        self.fade_surf = pygame.Surface((W, H))
        self.crt_on = True
        self.paused = False
        self.t = 0.0
        self.shake = 0.0
        self.fade = 1.0
        self.toasts = []
        self.banners = []
        self.pops = []
        self.aim = [W / 2, 260.0]
        self.mouse_moved = False
        self.hiscore = self.load_hi()
        self.state = 'title'
        self.end_msg = ''
        self.victory = False
        self.fx = Particles()
        self.fxm = Particles()
        self.reset()
        self.go('title')

    # ------------------------------------------------------------ assets
    def build_assets(self):
        base = pygame.Surface((W, H))
        for y in range(H):
            k = y / H
            pygame.draw.line(base, (int(lerp(18, 9, k)), int(lerp(62, 34, k)), int(lerp(116, 76, k))), (0, y), (W, y))
        self.ocean_base = base.convert()
        rnd = random.Random(5)

        def tile(n, col):
            s = pygame.Surface((256, 256), pygame.SRCALPHA)
            for _ in range(n):
                x, y, w = rnd.randint(8, 200), rnd.randint(8, 230), rnd.randint(14, 44)
                pygame.draw.arc(s, col, (x, y, w, max(4, w // 2)), 0.2, 2.9, 2)
            return s
        self.tileA = tile(50, (150, 205, 235, 62)).convert_alpha()
        self.tileB = tile(36, (255, 255, 255, 40)).convert_alpha()

        # ---- islas / ciudades (mundo)
        land = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        self.islands = []
        allisl = ([(x, y, r, s, True) for (_, x, y, r, s) in CITY_DEFS] + [(x, y, r, s, False) for (x, y, r, s) in EXTRA_ISLANDS]
                  + [(x, y, r, s, False) for (x, y, r, s) in DECOR_ISLANDS] + [(*ENEMY_PORT[:3], ENEMY_PORT[3], False)])
        for (x, y, r, seed, is_city) in allisl:
            self.islands.append((x, y, r, seed))
            self.paint_island(land, x, y, r, seed, is_city)
            if is_city:
                px, py = x, y + coast_r(r, seed, math.pi / 2, 1.0) * 0.96
                pygame.draw.rect(land, (112, 80, 48), (px - 9, py - 6, 18, 56))
                for k in range(6):
                    pygame.draw.rect(land, (70, 48, 30), (px - 11, py + k * 9, 4, 5))
                    pygame.draw.rect(land, (70, 48, 30), (px + 7, py + k * 9, 4, 5))
        self.land = land.convert_alpha()
        rc = random.Random(77)
        self.mclouds = [dict(x=rc.uniform(0, WORLD_W), y=rc.uniform(0, WORLD_H), i=k % 4, s=rc.uniform(1.8, 3.0))
                        for k in range(26)]
        sh_base = [make_cloud(s_)[1] for s_ in (1, 2, 3, 4)]
        for mc in self.mclouds:
            b_ = sh_base[mc['i']]
            mc['spr'] = pygame.transform.smoothscale(b_, (int(b_.get_width() * mc['s']), int(b_.get_height() * mc['s'])))
            mc['spr'].set_alpha(38)
        self.city_surf = {}
        for (name, x, y, r, seed) in CITY_DEFS:
            self.city_surf[name] = (self.make_city(r, seed, False), self.make_city(r, seed, True))

        # ---- naves
        self.ships = {}

        def reg(key, surf):
            self.ships[key] = (surf, make_shadow(surf))
        reg('p_map', make_ship(24, 66, (70, 140, 170), (110, 170, 190), (255, 210, 70)))
        reg('e_map', make_ship(22, 60, (150, 60, 60), (170, 90, 80), (30, 30, 30)))
        reg('p_hull', make_ship(46, 124, (70, 140, 170), (110, 170, 190), (255, 210, 70), False))
        reg('e_hull', make_ship(42, 112, (150, 60, 60), (170, 90, 80), (30, 30, 30), False))
        reg('s_map', make_sub(16, 62))
        reg('s_hull', make_sub(32, 128))
        reg('c_map', make_cargo(26, 70))
        self.tur_p = make_turret(8, (70, 140, 170))
        self.tur_e = make_turret(8, (150, 60, 60))
        self.tur_b = make_turret(12, (150, 160, 178))
        self.tur_b2 = make_turret(10, (150, 160, 178))
        reg('b_map', make_battleship(46, 126))
        reg('b_hull', make_battleship(98, 270))
        self.sol = {'p': make_soldier_frames('rifle', 'p')}
        for kd in ENEMY_TYPES:
            self.sol['e_' + kd] = make_soldier_frames(kd, 'e')
        hurt = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(70):
            pygame.draw.rect(hurt, (200, 0, 0, int(150 * (1 - i / 70) ** 2)), (i, i, W - 2 * i, H - 2 * i), 1)
        self.hurt_surf = hurt.convert_alpha()
        self.side_ship = self.make_side_ship()
        flip = lambda s: pygame.transform.flip(s, False, True)
        isl, isl_r = [], (55, 72, 90, 110)
        for k, r in enumerate(isl_r):
            sz = int(r * 4.4)
            s_ = pygame.Surface((sz, sz), pygame.SRCALPHA)
            self.paint_island(s_, sz / 2, sz / 2, r, 21 + k, False)
            isl.append(s_.convert_alpha())
        gb = pygame.Surface((80, 80), pygame.SRCALPHA)
        draw_cover(gb, dict(x=40, y=40, r=24, kind='sandbag', seed=3))
        self.air = dict(
            f16=make_f16((170, 182, 196), (108, 120, 138), (60, 100, 200), 0.9),
            viper=flip(make_f16((172, 100, 90), (112, 58, 54), (30, 30, 30), 0.72)),
            stealth=flip(make_f117((220, 70, 56), 0.62)),
            bomber=flip(make_f117((255, 150, 40), 1.7)),
            boss=flip(make_f117((255, 90, 60), 3.0)),
            shadows={}, isl=isl, isl_r=isl_r, gbase=gb.convert_alpha(),
            clouds=[make_cloud(s_) for s_ in (1, 2, 3, 4)])
        self.antenna_gfx = self.make_antenna()
        self.antenna_big = self.make_antenna(1.5)
        self.cockpit = self.make_cockpit()
        self.tk_tex = make_tk_textures()
        self.tk_spr = make_tank_sprites()
        self.tk_sky_bg, self.tk_floor_bg, self.tk_moon = self.make_tk_backdrops()

        # ---- cielo de defensa
        sky = pygame.Surface((W, HZ))
        for y in range(HZ):
            k = y / HZ
            if k < .7:
                c = (int(lerp(4, 40, k / .7)), int(lerp(6, 20, k / .7)), int(lerp(26, 64, k / .7)))
            else:
                kk = (k - .7) / .3
                c = (int(lerp(40, 190, kk)), int(lerp(20, 90, kk)), int(lerp(64, 70, kk)))
            pygame.draw.line(sky, c, (0, y), (W, y))
        pygame.draw.circle(sky, (240, 240, 220), (870, 120), 34)
        pygame.draw.circle(sky, (210, 210, 195), (860, 112), 8)
        pygame.draw.circle(sky, (210, 210, 195), (882, 134), 5)
        self.sky = sky.convert()
        r3 = random.Random(2)
        self.stars = [(r3.randint(0, W), r3.randint(0, 380), r3.uniform(0, 6.28)) for _ in range(130)]

        # ---- CRT
        crt = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(crt, (0, 0, 0, 40), (0, y), (W, y))
        for i in range(46):
            pygame.draw.rect(crt, (0, 0, 0, int(110 * (1 - i / 46) ** 2)), (i, i, W - 2 * i, H - 2 * i), 1)
        self.crt = crt.convert_alpha()

    def paint_island(self, land, x, y, r, seed, is_city):
        for sc, a in ((1.55, 30), (1.38, 45), (1.22, 65)):
            pygame.draw.polygon(land, (90, 205, 215, a), blob(x, y, r, seed, sc))
        pygame.draw.polygon(land, (236, 250, 255, 110), blob(x, y, r, seed, 1.1), 3)
        pygame.draw.polygon(land, (222, 204, 148), blob(x, y, r, seed, 1.04))
        pygame.draw.polygon(land, (92, 150, 74), blob(x, y, r, seed, .9))
        pygame.draw.polygon(land, (110, 168, 84), blob(x - 5, y - 5, r, seed, .78))
        pygame.draw.polygon(land, (62, 118, 62), blob(x, y, r, seed, .55))
        rnd2 = random.Random(seed)
        for _ in range(int(r * .55)):
            a, d = rnd2.uniform(0, 6.28), rnd2.uniform(0.2, 0.8) * r
            tx, ty = x + math.cos(a) * d, y + math.sin(a) * d
            if is_city and d < r * 0.5:
                continue
            tr = rnd2.randint(4, 8)
            pygame.draw.circle(land, (30, 80, 44), (int(tx + 2), int(ty + 3)), tr)
            pygame.draw.circle(land, (52, 112, 58), (int(tx), int(ty)), tr)
            pygame.draw.circle(land, (92, 158, 80), (int(tx - 1), int(ty - 2)), max(2, tr // 2))
        if not is_city and r >= 100:
            for _ in range(3):
                a, d = rnd2.uniform(0, 6.28), rnd2.uniform(0.3, 0.6) * r
                hx, hy, hr = x + math.cos(a) * d, y + math.sin(a) * d, rnd2.uniform(0.16, 0.26) * r
                pygame.draw.circle(land, (60, 98, 52), (int(hx + 3), int(hy + 4)), int(hr))
                pygame.draw.circle(land, (116, 124, 96), (int(hx), int(hy)), int(hr))
                pygame.draw.circle(land, (150, 156, 126), (int(hx - hr * .25), int(hy - hr * .3)), int(hr * .58))
                pygame.draw.circle(land, (214, 218, 204), (int(hx - hr * .3), int(hy - hr * .4)), max(2, int(hr * .22)))

    def make_city(self, r, seed, ruined):
        size = int(r * 2.6)
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        rnd = random.Random(seed + 100)
        pygame.draw.circle(s, (120, 120, 118) if not ruined else (60, 56, 52), (c, c), int(r * .56))
        for a in range(0, 360, 45):
            dx, dy = vec(a, r * .56)
            pygame.draw.line(s, (80, 80, 84), (c, c), (c + dx, c + dy), 3)
        blds = []
        for _ in range(60):
            a, d = rnd.uniform(0, 6.28), rnd.uniform(0, r * .46)
            bx, by = c + math.cos(a) * d, c + math.sin(a) * d
            bw, bd = rnd.randint(14, 28), rnd.randint(8, 14)
            hh = rnd.randint(14, 44)
            if all(abs(bx - q[0]) > (bw + q[2]) / 2 + 3 or abs(by - q[1]) > 16 for q in blds):
                blds.append((bx, by, bw, bd, hh))
            if len(blds) >= 16:
                break
        for bx, by, bw, bd, hh in blds:
            hh = hh if not ruined else hh // 5
            pygame.draw.rect(s, (0, 0, 0, 80), (bx - bw / 2 + 4 + hh * .4, by - bd, bw, bd + 8))
        for bx, by, bw, bd, hh in sorted(blds, key=lambda q: q[1]):
            hh = hh if not ruined else hh // 5
            wall = (92, 104, 128) if not ruined else (50, 46, 44)
            roof = (176, 190, 210) if not ruined else (80, 72, 66)
            pygame.draw.rect(s, wall, (bx - bw / 2, by - hh, bw, hh))
            pygame.draw.rect(s, roof, (bx - bw / 2, by - hh - bd, bw, bd))
            if not ruined:
                for wy in range(int(by - hh + 4), int(by - 3), 7):
                    for wx in range(int(bx - bw / 2 + 3), int(bx + bw / 2 - 3), 6):
                        pygame.draw.rect(s, (255, 226, 130) if rnd.random() < .6 else (40, 50, 76), (wx, wy, 3, 3))
        if ruined:
            for _ in range(8):
                pygame.draw.circle(s, (30, 26, 24), (int(c + rnd.uniform(-r * .4, r * .4)), int(c + rnd.uniform(-r * .4, r * .4))),
                                   rnd.randint(6, 14))
        return s

    def make_side_ship(self):
        s = pygame.Surface((300, 112), pygame.SRCALPHA)
        pygame.draw.polygon(s, (66, 76, 92), [(10, 70), (282, 70), (300, 58), (262, 106), (34, 106)])
        pygame.draw.polygon(s, (110, 40, 40), [(40, 98), (258, 98), (262, 106), (34, 106)])
        pygame.draw.line(s, (130, 145, 165), (10, 70), (282, 70), 3)
        pygame.draw.rect(s, (92, 104, 122), (110, 42, 76, 28))
        pygame.draw.rect(s, (120, 134, 154), (126, 26, 44, 16))
        for k in range(5):
            pygame.draw.rect(s, (250, 226, 130), (116 + k * 14, 50, 8, 6))
        pygame.draw.line(s, (150, 160, 175), (148, 26), (148, 6), 2)
        pygame.draw.rect(s, (150, 160, 175), (138, 5, 20, 3))
        pygame.draw.rect(s, (60, 66, 78), (192, 46, 18, 24))
        pygame.draw.rect(s, (255, 210, 70), (192, 54, 18, 4))
        pygame.draw.circle(s, (60, 70, 86), (232, 66), 11)
        return s

    def make_antenna(self, scale=1.0):
        S = 4
        w, h = 48 * S, 96 * S
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        base_y, top_y = h - 10 * S, 16 * S
        pygame.draw.ellipse(s, (0, 0, 0, 70), (cx - 20 * S, h - 11 * S, 40 * S, 9 * S))
        pygame.draw.rect(s, (118, 120, 128), (cx - 16 * S, base_y, 32 * S, 7 * S), border_radius=S * 2)
        pygame.draw.rect(s, (170, 172, 180), (cx - 16 * S, base_y, 32 * S, 2 * S), border_radius=S * 2)
        n = 8
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            y0, y1 = base_y + (top_y - base_y) * t0, base_y + (top_y - base_y) * t1
            hw0, hw1 = (12.5 - 10 * t0) * S, (12.5 - 10 * t1) * S
            c = (190, 196, 208)
            pygame.draw.line(s, c, (cx - hw0, y0), (cx + hw1, y1), S)
            pygame.draw.line(s, c, (cx + hw0, y0), (cx - hw1, y1), S)
            pygame.draw.line(s, (150, 156, 170), (cx - hw1, y1), (cx + hw1, y1), S)
        for side in (-1, 1):
            pygame.draw.line(s, (214, 220, 232), (cx + side * 12.5 * S, base_y), (cx + side * 2.5 * S, top_y), int(S * 1.6))
        pygame.draw.rect(s, (96, 100, 112), (cx - 7 * S, 30 * S, 14 * S, 3 * S), border_radius=S)
        pygame.draw.ellipse(s, (232, 236, 244), (cx - 21 * S, 22 * S, 18 * S, 14 * S))
        pygame.draw.ellipse(s, (170, 178, 194), (cx - 19 * S, 24 * S, 14 * S, 10 * S))
        pygame.draw.line(s, (90, 96, 110), (cx - 12 * S, 29 * S), (cx - 2 * S, 29 * S), int(S * 1.2))
        pygame.draw.circle(s, (255, 190, 70), (cx - 4 * S, 29 * S), int(S * 1.4))
        for dx in (3, 6):
            pygame.draw.rect(s, (228, 232, 240), (cx + dx * S, 18 * S, 2 * S, 12 * S), border_radius=S // 2)
        pygame.draw.line(s, (214, 220, 232), (cx, top_y), (cx, 6 * S), int(S * 1.2))
        pygame.draw.circle(s, (255, 70, 60), (cx, 6 * S), int(S * 2.2))
        pygame.draw.circle(s, (255, 190, 170), (cx - S // 2, 6 * S - S // 2), int(S * 0.9))
        return pygame.transform.smoothscale(s, (int(48 * scale), int(96 * scale)))

    def make_cockpit(self):
        vp = self.TK_VP
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(H):
            f = abs(y - vp.centery) / (H / 2)
            pygame.draw.line(s, (int(16 + 16 * (1 - f)), int(22 + 18 * (1 - f)), int(19 + 15 * (1 - f)), 255), (0, y), (W, y))
        for x in range(30, W, 70):
            for y in (10, H - 10):
                pygame.draw.circle(s, (8, 10, 9, 255), (x + 1, y + 1), 4)
                pygame.draw.circle(s, (110, 126, 116, 255), (x, y), 4)
                pygame.draw.circle(s, (170, 184, 174, 255), (x - 1, y - 1), 1)
        for rect in ((28, 14, 380, 92), (W - 408, 14, 380, 92), (28, vp.bottom + 16, 330, 118), (W - 358, vp.bottom + 16, 330, 118),
                     (W // 2 - 185, vp.bottom + 46, 370, 44)):
            pygame.draw.rect(s, (7, 11, 9, 255), rect, border_radius=8)
            pygame.draw.rect(s, (46, 96, 68, 255), rect, 2, border_radius=8)
        pygame.draw.circle(s, (9, 13, 11, 255), (W // 2, 62), 62)
        pygame.draw.circle(s, (30, 38, 33, 255), (W // 2, 62), 62, 8)
        pygame.draw.circle(s, (100, 118, 106, 255), (W // 2, 62), 62, 2)
        pygame.draw.rect(s, (0, 0, 0, 0), vp, border_radius=28)
        pygame.draw.rect(s, (100, 118, 106, 255), vp.inflate(10, 10), 4, border_radius=32)
        pygame.draw.rect(s, (28, 36, 31, 255), vp.inflate(26, 26), 10, border_radius=38)
        return s.convert_alpha()

    # ------------------------------------------------------------ util
    def text(self, dst, s, font, col, x, y, anchor='l', shadow=True, alpha=None):
        img = font.render(s, True, col)
        r = img.get_rect()
        if anchor == 'l':
            r.topleft = (x, y)
        elif anchor == 'c':
            r.midtop = (x, y)
        else:
            r.topright = (x, y)
        if shadow:
            sh = font.render(s, True, (0, 0, 0))
            if alpha is not None:
                sh.set_alpha(alpha)
            dst.blit(sh, (r.x + 2, r.y + 2))
        if alpha is not None:
            img.set_alpha(alpha)
        dst.blit(img, r)
        return r

    def panel(self, dst, rect, alpha=150):
        key = (rect[2], rect[3], alpha)
        s = self.panels.get(key)
        if s is None:
            s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
            pygame.draw.rect(s, (6, 12, 26, alpha), (0, 0, rect[2], rect[3]), border_radius=8)
            pygame.draw.rect(s, (90, 130, 180, 200), (0, 0, rect[2], rect[3]), 2, border_radius=8)
            self.panels[key] = s
        dst.blit(s, (rect[0], rect[1]))

    def dim(self, dst, v, rect=None):
        dst.fill((v, v, v), rect, special_flags=pygame.BLEND_RGB_SUB)

    def bar(self, dst, x, y, w, h, frac, col, label):
        frac = clamp(frac, 0, 1)
        pygame.draw.rect(dst, (8, 12, 24), (x, y, w, h), border_radius=4)
        if frac > 0:
            fw = max(2, int((w - 4) * frac))
            pygame.draw.rect(dst, col, (x + 2, y + 2, fw, h - 4), border_radius=3)
            pygame.draw.rect(dst, shade(col, 70), (x + 2, y + 2, fw, max(2, (h - 4) // 3)), border_radius=3)
        pygame.draw.rect(dst, (100, 125, 160), (x, y, w, h), 1, border_radius=4)
        self.text(dst, label, self.f_s, (235, 245, 255), x + 6, y + (h - 16) // 2)

    def toast(self, s, col=(255, 255, 255)):
        self.toasts.append([s, col, 3.0])
        self.toasts = self.toasts[-4:]

    def banner(self, title, sub='', col=(255, 220, 90), dur=2.6):
        self.banners.append([title, sub, col, dur, dur])

    def pop(self, s, x, y, col=(255, 255, 160)):
        self.pops.append([s, x, y, 1.0, col])

    def load_hi(self):
        try:
            with open(self.hi_path(), 'r') as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def hi_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'final_legacy_hiscore.txt')

    def save_hi(self):
        if self.score > self.hiscore:
            self.hiscore = self.score
            try:
                with open(self.hi_path(), 'w') as f:
                    f.write(str(self.score))
            except Exception:
                pass

    def on_land(self, x, y, margin=0):
        for ix, iy, ir, sd in self.islands:
            if dist(x, y, ix, iy) < coast_r(ir, sd, math.atan2(y - iy, x - ix), 1.1) + margin:
                return True
        return False

    def add_score(self, n):
        self.score += n

    # ------------------------------------------------------------ partida
    def reset(self):
        self.score = 0
        self.wave = 1
        self.sx, self.sy = 2400.0, 1350.0
        self.sh, self.sv = 0.0, 0.0
        self.hull, self.fuel, self.ammo = 100.0, 100.0, 30
        self.antennas = {i: False for i in ANTENNA_ISLANDS}
        self.landing_attempts = {i: 0 for i in range(len(EXTRA_ISLANDS))}
        self.cities = []
        for (name, x, y, r, seed) in CITY_DEFS:
            c = dict(name=name, x=x, y=y, r=r, hp=100.0, dead=False, seed=seed)
            c['sky'] = self.make_skyline(seed)
            c['dock'] = (x, y + coast_r(r, seed, math.pi / 2, 1.04) + 46)
            self.cities.append(c)
        self.enemies = []
        self.crates = []
        self.crate_t = 18.0
        self.strike_t = 50.0
        self.warned = False
        self.strike_city = None
        self.strike_kind = 'missile'
        self.strike_n = 0
        self.attack = None
        self.radar_t = 0.0
        self.nests = []
        self.spawn_nests()
        self.rescue = None
        self.rescue_t = 45.0
        self.convoy = None
        self.convoy_t = 100.0
        self.port_tries = 0
        self.port_done = False
        self.cam = [self.sx - W / 2, self.sy - H / 2]
        self.wake_t = 0.0
        self.dock_t = 0.0
        self.crash_t = 0.0
        self.ammo_acc = 0.0
        self.empty_fuel_aid = False
        self.fxm = Particles()
        self.toasts, self.banners, self.pops = [], [], []
        self.spawn_wave()

    def make_skyline(self, seed):
        rnd = random.Random(seed * 7)
        out = []
        x = 0
        while x < SKY_W - 30:
            w = rnd.randint(30, 62)
            mid = 1 - abs((x + w / 2) - SKY_W / 2) / (SKY_W / 2)
            h = int(rnd.randint(50, 110) + mid * rnd.randint(30, 120))
            out.append(dict(x=x, w=w, h=h, h0=h, s=rnd.randint(0, 99), ant=rnd.random() < .3))
            x += w + rnd.randint(0, 5)
        return out

    def rand_wp(self):
        for _ in range(40):
            x, y = random.uniform(120, WORLD_W - 120), random.uniform(120, WORLD_H - 120)
            if not self.on_land(x, y, 80):
                return [x, y]
        return [WORLD_W / 2, WORLD_H / 2]

    def spawn_nests(self):
        """Baterías costeras enemigas sobre algunos islotes pequeños (se renuevan cada oleada)."""
        hp = 14 + 4 * self.wave
        self.nests = [dict(x=x, y=y, r=r, hp=float(hp), max=float(hp), cool=0.0, ang=180.0, nest=True, alive=True, seen=False)
                      for (x, y, r, _s) in random.sample([i for i in DECOR_ISLANDS if dist(i[0], i[1], self.sx, self.sy) > 800], 10)]

    def spawn_wave(self):
        n = min(3 + self.wave, 9)
        for _ in range(n):
            x = y = 0
            for _ in range(60):
                x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
                if dist(x, y, self.sx, self.sy) > 700 and not self.on_land(x, y, 90):
                    break
            mh = 10 + 2 * (self.wave - 1)
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=mh, max=mh, state='patrol',
                                     wp=self.rand_wp(), cool=0.0, is_boss=False))
        for _ in range(0 if self.wave < 2 else (1 if self.wave < 4 else 2)):
            for _ in range(60):
                x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
                if dist(x, y, self.sx, self.sy) > 900 and not self.on_land(x, y, 90):
                    break
            mh = 8 + 2 * self.wave
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=mh, max=mh, state='patrol',
                                     wp=self.rand_wp(), cool=0.0, is_boss=False, sub=True))
        x = y = 0
        for _ in range(60):
            x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
            if dist(x, y, self.sx, self.sy) > 900 and not self.on_land(x, y, 120):
                break
        boss_hp = 36 + 16 * (self.wave - 1)
        self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=boss_hp, max=boss_hp,
                                 state='patrol', wp=self.rand_wp(), cool=0.0, is_boss=True, shield=True,
                                 hack_cd=0.0, seen=False, name=BOSS_NAMES[(self.wave - 1) % len(BOSS_NAMES)]))

    def go(self, state):
        self.state = state
        self.fade = 1.0
        pygame.mouse.set_visible(state not in ('defense', 'combat', 'aerial', 'ground', 'tank', 'port'))
        self.audio.music({'title': 'calm', 'map': 'calm', 'defense': 'battle', 'combat': 'battle',
                          'aerial': 'battle', 'ground': 'battle', 'hack': 'battle', 'tank': 'battle', 'port': 'battle', 'gameover': None}[state])
        if state not in ('map', 'combat'):
            self.audio.engine_vol(0)

    def start_game(self):
        self.reset()
        self.go('map')
        self.banner('OLEADA 1', 'Hundí la flota enemiga y defendé las ciudades', (120, 220, 255), 3.2)

    def game_over(self, msg, victory=False):
        self.end_msg = msg
        self.victory = victory
        self.save_hi()
        self.audio.play('win' if victory else 'lose')
        self.go('gameover')

    # ------------------------------------------------------------ eventos
    def handle(self, e):
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if e.type == pygame.MOUSEMOTION:
            self.mouse_moved = True
            self.aim = [float(e.pos[0]), float(e.pos[1])]
            if self.state == 'hack':
                self.h['kb'] = False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F1:
                self.crt_on = not self.crt_on
            elif e.key == pygame.K_m:
                self.audio.toggle_mute()
            elif e.key == pygame.K_F7 and self.state == 'map' and not self.paused:
                self.port_tries = min(self.port_tries, 1)
                self.start_port()
            elif e.key == pygame.K_F6 and self.state == 'map' and not self.paused:
                if self.convoy is None:
                    self.begin_convoy()
            elif e.key == pygame.K_F5 and self.state == 'map' and not self.paused:
                self.rescue = None
                self.begin_rescue()
            elif e.key in (pygame.K_F2, pygame.K_F3, pygame.K_F4) and self.state == 'map' and not self.paused:
                alive = [c for c in self.cities if not c['dead']]
                if alive:
                    self.strike_city = random.choice(alive)
                    self.warned = False
                    self.attack = None
                    {pygame.K_F2: self.start_tank, pygame.K_F3: self.start_aerial, pygame.K_F4: self.start_ground}[e.key](self.strike_city)
            elif e.key in (pygame.K_p, pygame.K_ESCAPE) and self.state in ('map', 'defense', 'combat', 'ground', 'aerial', 'hack', 'tank', 'port'):
                self.paused = not self.paused
            elif e.key == pygame.K_q and self.paused:
                pygame.quit()
                sys.exit()
            elif self.state in ('title', 'gameover') and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()
            elif self.state == 'defense' and e.key == pygame.K_SPACE and not self.paused:
                self.fire_interceptor()
            elif self.state == 'ground' and e.key in (pygame.K_SPACE, pygame.K_g) and not self.paused:
                self.throw_grenade_p()
            elif self.state == 'ground' and e.key == pygame.K_r and not self.paused:
                self.start_reload()
            elif self.state == 'map' and e.key == pygame.K_t and not self.paused:
                if self.nearest_port():
                    self.start_port()
            elif self.state == 'port' and not self.paused and e.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE):
                self.pt_jump()
            elif self.state == 'port' and not self.paused and e.key == pygame.K_g:
                self.pt_throw()
            elif self.state == 'map' and e.key == pygame.K_l and not self.paused:
                island = self.nearest_landing_island()
                if island:
                    self.start_landing(island[0])
            elif self.state == 'aerial' and e.key in (pygame.K_b, pygame.K_x) and not self.paused:
                self.air_bomb()
            elif self.state == 'tank' and e.key == pygame.K_SPACE and not self.paused:
                self.tk_fire()
            elif self.state == 'map' and e.key == pygame.K_h and not self.paused:
                self.try_hack()
            elif self.state == 'hack' and not self.paused:
                h = self.h
                if e.key == pygame.K_TAB and h['phase'] == 'play':
                    self.end_hack(False, abort=True)
                elif h['phase'] == 'fail':
                    if h['pt'] > 0.6 and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.hack_retry()
                    elif e.key == pygame.K_TAB:
                        self.end_hack(False)
                elif e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    dx = (e.key == pygame.K_RIGHT) - (e.key == pygame.K_LEFT)
                    dy = (e.key == pygame.K_DOWN) - (e.key == pygame.K_UP)
                    h['cur'] = (clamp(h['cur'][0] + dx, 0, h['cols'] - 1), clamp(h['cur'][1] + dy, 0, h['rows'] - 1))
                    h['kb'] = True
                elif e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                    h['kb'] = True
                    self.hack_rotate(h['cur'], 3 if e.key == pygame.K_z else 1)
            elif self.state == 'combat' and not self.paused:
                if e.key == pygame.K_SPACE:
                    self.fire_shell()
                elif e.key == pygame.K_e:
                    self.flee()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3) and self.state == 'hack' and not self.paused:
            if self.h['phase'] == 'fail':
                if self.h['pt'] > 0.6 and e.button == 1:
                    self.hack_retry()
            else:
                cell = self.hack_cell_at(e.pos)
                if cell:
                    self.hack_rotate(cell, 1 if e.button == 1 else 3)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'port' and not self.paused:
            self.pt_throw()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'ground' and not self.paused:
            self.throw_grenade_p()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'aerial' and not self.paused:
            self.air_bomb()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.paused:
            if self.state == 'title' or self.state == 'gameover':
                self.start_game()
            elif self.state == 'defense':
                self.fire_interceptor()
            elif self.state == 'tank':
                self.tk_fire()
            elif self.state == 'combat':
                self.fire_shell()

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                self.handle(e)
            if not self.paused:
                self.update(dt)
            self.draw()

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        self.fade = max(0.0, self.fade - dt * 2.2)
        self.shake *= 0.9 ** (dt * 60)
        for q in self.toasts:
            q[2] -= dt
        self.toasts = [q for q in self.toasts if q[2] > 0]
        for b in self.banners:
            b[3] -= dt
        self.banners = [b for b in self.banners if b[3] > 0]
        for p in self.pops:
            p[3] -= dt
            p[2] -= 30 * dt
        self.pops = [p for p in self.pops if p[3] > 0]
        if self.state == 'map':
            self.upd_map(dt)
        elif self.state == 'defense':
            self.upd_defense(dt)
        elif self.state == 'combat':
            self.upd_combat(dt)
        elif self.state == 'aerial':
            self.upd_aerial(dt)
        elif self.state == 'hack':
            self.upd_hack(dt)
        elif self.state == 'tank':
            self.upd_tank(dt)
        elif self.state == 'port':
            self.upd_port(dt)
        elif self.state == 'ground':
            self.upd_ground(dt)
        elif self.state in ('title', 'gameover'):
            self.fxm.update(dt)

    # ---------------------------------------------------------- MAPA
    def upd_map(self, dt):
        keys = pygame.key.get_pressed()
        thr = (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0) - (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0)
        turn = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
        docking = self.nearest_dock()
        if self.fuel <= 0:
            thr = 0
        if thr > 0:
            self.sv = min(VMAX, self.sv + 110 * dt)
        elif thr < 0:
            self.sv = max(-45, self.sv - 130 * dt)
        else:
            self.sv -= self.sv * 0.45 * dt
            self.sv -= math.copysign(min(abs(self.sv), 8 * dt), self.sv)
        if docking and keys[pygame.K_r]:
            self.sv -= self.sv * 3 * dt
        steer = 58 * clamp(abs(self.sv) / 70, 0.2, 1.0) * (1 if self.sv >= 0 else -1)
        self.sh = (self.sh + turn * steer * dt) % 360
        dx, dy = vec(self.sh, self.sv * dt)
        self.sx += dx
        self.sy += dy
        self.sx, self.sy = clamp(self.sx, 40, WORLD_W - 40), clamp(self.sy, 40, WORLD_H - 40)
        self.crash_t = max(0.0, self.crash_t - dt)
        for ix, iy, ir, sd in self.islands:                   # costa: no se puede entrar a tierra
            d = dist(self.sx, self.sy, ix, iy) or 1.0
            lim = coast_r(ir, sd, math.atan2(self.sy - iy, self.sx - ix), 1.06) + 14
            if d < lim:
                if abs(self.sv) > 110 and self.crash_t <= 0:
                    self.crash_t = 1.5
                    self.hull -= 4
                    self.audio.play('hit', .6)
                    self.toast('¡Encallaste! Casco dañado', (255, 120, 90))
                    self.shake = 6
                    if self.hull <= 0:
                        return self.game_over('Tu buque encalló y se hundió')
                self.sx = ix + (self.sx - ix) / d * lim
                self.sy = iy + (self.sy - iy) / d * lim
                self.sv *= 0.3
        self.fuel = max(0.0, self.fuel - abs(self.sv) / VMAX * 0.9 * dt)
        self.audio.engine_vol(abs(self.sv) / VMAX * 0.9 + 0.1)
        if self.fuel <= 0 and not self.empty_fuel_aid and abs(self.sv) < 5:
            self.empty_fuel_aid = True
            a = random.uniform(0, 6.28)
            self.crates.append(dict(x=self.sx + math.cos(a) * 140, y=self.sy + math.sin(a) * 140, kind='fuel', t=0))
            self.toast('Sin combustible: lanzaron un bidón de emergencia', (255, 200, 90))
        if self.fuel > 15:
            self.empty_fuel_aid = False
        # estela
        self.wake_t -= dt
        if abs(self.sv) > 15 and self.wake_t <= 0:
            self.wake_t = 0.05
            bx, by = vec(self.sh, -26)
            self.fxm.add('foam', self.sx + bx + random.uniform(-4, 4), self.sy + by + random.uniform(-4, 4), life=1.6,
                         r0=4, r1=13, col=(230, 245, 255))
        # humo si está dañado
        if self.hull < 45 and random.random() < dt * 8:
            self.fxm.add('smoke', self.sx, self.sy, 0, -20, 1.8, 5, 18, (60, 60, 60))
        # cámara
        tx, ty = self.sx - W / 2, self.sy - H / 2
        self.cam[0] += (tx - self.cam[0]) * min(1, dt * 4)
        self.cam[1] += (ty - self.cam[1]) * min(1, dt * 4)
        self.cam[0] = clamp(self.cam[0], 0, WORLD_W - W)
        self.cam[1] = clamp(self.cam[1], 0, WORLD_H - H)
        # reabastecer
        if docking:
            if keys[pygame.K_r] and abs(self.sv) < 40:
                self.dock_t -= dt
                changed = False
                if self.fuel < 100:
                    self.fuel = min(100, self.fuel + 25 * dt)
                    changed = True
                if self.hull < 100:
                    self.hull = min(100, self.hull + 8 * dt)
                    changed = True
                self.ammo_acc += 6 * dt
                if self.ammo < 40 and self.ammo_acc >= 1:
                    self.ammo += 1
                    self.ammo_acc = 0
                    changed = True
                if changed and self.dock_t <= 0:
                    self.dock_t = 0.28
                    self.audio.play('dock', .5)
        # enemigos
        for en in self.enemies:
            self.ai_map(en, dt)
            d = dist(self.sx, self.sy, en['x'], en['y'])
            if en.get('shield'):
                en['hack_cd'] = max(0.0, en['hack_cd'] - dt)
                if d < SHIELD_R:
                    k = d or 1.0
                    self.sx = en['x'] + (self.sx - en['x']) / k * SHIELD_R
                    self.sy = en['y'] + (self.sy - en['y']) / k * SHIELD_R
                    self.sv *= 0.6
                    if self.t - getattr(self, 'shield_toast', -9) > 3:
                        self.shield_toast = self.t
                        self.toast('Escudo digital: presioná H para hackearlo', (255, 120, 220))
                continue
            if d < 78 and en['cool'] <= 0:
                return self.start_combat(en)
        self.radar_t = max(0.0, self.radar_t - dt)
        if self.convoy is not None:
            self.upd_convoy(dt)
        elif self.attack is None and self.wave >= 2:
            self.convoy_t -= dt
            if self.convoy_t <= 0:
                self.begin_convoy()
        if self.rescue is not None:
            self.upd_rescue(dt)
        elif self.attack is None:
            self.rescue_t -= dt
            if self.rescue_t <= 0:
                self.begin_rescue()
        for nst in self.nests:
            if not nst['alive']:
                continue
            nst['cool'] = max(0.0, nst['cool'] - dt)
            d = dist(self.sx, self.sy, nst['x'], nst['y'])
            if d < 700:
                nst['ang'] = bearing(self.sx - nst['x'], self.sy - nst['y'])
                if not nst['seen'] and d < 520:
                    nst['seen'] = True
                    self.audio.play('ping')
                    self.toast('¡Batería costera enemiga!', (255, 120, 90))
            if d < 330 and nst['cool'] <= 0:
                return self.start_combat(nst)
        # cajas
        self.crate_t -= dt
        if self.crate_t <= 0 and len(self.crates) < 5:
            self.crate_t = 16.0
            for _ in range(30):
                x, y = random.uniform(100, WORLD_W - 100), random.uniform(100, WORLD_H - 100)
                if not self.on_land(x, y, 40):
                    self.crates.append(dict(x=x, y=y, kind=random.choice(['ammo', 'fuel', 'repair']), t=0))
                    break
        for c in self.crates[:]:
            c['t'] += dt
            if dist(self.sx, self.sy, c['x'], c['y']) < 42:
                self.crates.remove(c)
                self.audio.play('pickup')
                if c['kind'] == 'ammo':
                    self.ammo = min(40, self.ammo + 10)
                    self.toast('+10 munición', (255, 230, 90))
                elif c['kind'] == 'fuel':
                    self.fuel = min(100, self.fuel + 35)
                    self.toast('+35% combustible', (120, 255, 140))
                else:
                    self.hull = min(100, self.hull + 30)
                    self.toast('+30 casco', (255, 255, 255))
            elif c['t'] > 130:
                self.crates.remove(c)
        # ataque de misiles
        alive = [c for c in self.cities if not c['dead']]
        self.strike_t -= dt
        if self.attack is None and alive and self.strike_t <= 4.0 and not self.warned:
            self.strike_city = random.choice(alive)
            self.strike_n += 1
            rand = random.random()
            inst = [i for i, v in self.antennas.items() if v]
            if inst and self.strike_n >= 3 and random.random() < 0.25:
                self.begin_attack(self.antenna_city(random.choice(inst)), 'antenna')
            else:
                if self.strike_n == 2 or (self.strike_n > 2 and rand < 0.3):
                    self.strike_kind = 'tank' if random.random() < 0.65 else 'ground'
                elif rand < 0.35:
                    self.strike_kind = 'aerial'
                else:
                    self.strike_kind = 'missile'
                if self.strike_kind == 'missile':
                    self.warned = True
                    self.audio.play('alarm')
                    self.banner('¡ALERTA DE MISILES!', 'Objetivo: ' + self.strike_city['name'], (255, 80, 70), 3.8)
                else:
                    self.begin_attack(self.strike_city, self.strike_kind)
        if self.warned and self.strike_t <= 0:
            self.start_defense(self.strike_city)
            return
        if self.attack is not None and self.upd_attack(dt):
            return
        # ciudades dañadas echan humo
        for c in alive:
            if c['hp'] < 55 and random.random() < dt * 5:
                self.fxm.add('smoke', c['x'] + random.uniform(-30, 30), c['y'] + random.uniform(-30, 10), 0, -25, 2.5,
                             8, 28, (50, 50, 50))
        self.fxm.update(dt)
        # oleada completada
        if not self.enemies:
            self.wave_clear()

    def begin_convoy(self):
        """Convoy aliado entre dos ciudades: cazadores enemigos lo atacan; hay que escoltarlo."""
        alive = [c for c in self.cities if not c['dead']]
        if len(alive) < 2:
            return
        src = random.choice(alive)
        dst = max((c for c in alive if c is not src), key=lambda c: dist(c['x'], c['y'], src['x'], src['y']) + random.uniform(0, 600))
        sx, sy = src['dock']
        dx, dy = dst['dock']
        cv_ = dict(x=float(sx), y=float(sy), h=bearing(dx - sx, dy - sy), v=0.0, hp=100.0, src=src, dst=dst, t=0.0)
        self.convoy = cv_
        n_r = 2 if self.wave < 4 else 3
        mh = 9 + 2 * self.wave
        for i in range(n_r):
            f = random.uniform(0.35, 0.7)
            px, py = sx + (dx - sx) * f, sy + (dy - sy) * f
            for _ in range(40):
                x, y = px + random.uniform(-350, 350), py + random.uniform(-350, 350)
                if 100 < x < WORLD_W - 100 and 100 < y < WORLD_H - 100 and not self.on_land(x, y, 90) and dist(x, y, self.sx, self.sy) > 500:
                    break
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=mh, max=mh, state='patrol',
                                     wp=(px, py), cool=0.0, is_boss=False, raider=True))
        self.audio.play('alarm', .6)
        self.banner('¡CONVOY EN PELIGRO!', 'Carguero de %s a %s  |  Cazadores enemigos al acecho: escoltalo' % (src['name'], dst['name']),
                    (120, 255, 190), 4.4)

    def end_convoy(self, ok):
        cv_ = self.convoy
        self.convoy = None
        self.convoy_t = random.uniform(110, 150)
        for en in self.enemies:
            en.pop('raider', None)
        if ok:
            pts = 600 + 150 * self.wave
            self.add_score(pts)
            d = cv_['dst']
            d['hp'] = min(100.0, d['hp'] + 20)
            self.audio.play('win', .7)
            self.banner('¡CONVOY A SALVO!', '%s recibe suministros (+20%% ciudad)  |  +%d puntos' % (d['name'], pts), (120, 255, 160), 3.6)
        else:
            self.audio.play('boom_l')
            self.shake = 10
            self.ammo = max(0, self.ammo - 4)
            self.banner('¡CONVOY HUNDIDO!', 'Sin suministros: -4 munición', (255, 90, 70), 3.4)

    def upd_convoy(self, dt):
        cv_ = self.convoy
        cv_['t'] += dt
        dx, dy = cv_['dst']['dock']
        vx, vy = dx - cv_['x'], dy - cv_['y']
        d = math.hypot(vx, vy) or 1.0
        vx, vy = vx / d, vy / d
        for ix, iy, ir, sd in self.islands:
            dd = dist(cv_['x'], cv_['y'], ix, iy) or 1.0
            lim = coast_r(ir, sd, math.atan2(cv_['y'] - iy, cv_['x'] - ix), 1.1) + 120
            if dd < lim:
                k = (lim - dd) / 120
                vx += (cv_['x'] - ix) / dd * k * 2.6
                vy += (cv_['y'] - iy) / dd * k * 2.6
        want = bearing(vx, vy)
        cv_['h'] = (cv_['h'] + clamp(angle_diff(cv_['h'], want), -30 * dt, 30 * dt)) % 360
        cv_['v'] += ((70 if cv_['t'] > 3 else 0) - cv_['v']) * min(1, dt * 1.2)
        mx, my = vec(cv_['h'], cv_['v'] * dt)
        cv_['x'] += mx
        cv_['y'] += my
        if random.random() < dt * 12:
            bx, by = vec(cv_['h'], -30)
            self.fxm.add('foam', cv_['x'] + bx, cv_['y'] + by, life=1.3, r0=4, r1=12, col=(230, 245, 255))
        atk = [en for en in self.enemies if en.get('raider') and dist(en['x'], en['y'], cv_['x'], cv_['y']) < 170]
        if atk:
            cv_['hp'] -= 6.0 * len(atk) * dt
            if random.random() < dt * 8:
                self.fxm.add('glow', cv_['x'] + random.uniform(-10, 10), cv_['y'] + random.uniform(-25, 25), life=.4, r0=6, r1=18, col=(255, 150, 60))
            if int(cv_['t'] * 2) != int((cv_['t'] - dt) * 2):
                self.audio.play('hit', .25)
        if cv_['hp'] < 50 and random.random() < dt * 6:
            self.fxm.add('smoke', cv_['x'], cv_['y'], 0, -18, 1.8, 5, 18, (60, 60, 60))
        if cv_['hp'] <= 0:
            self.end_convoy(False)
        elif d < 160:
            self.end_convoy(True)

    def draw_convoy(self, cv, cx, cy, yy):
        c = self.convoy
        t = self.t
        sx, sy = c['x'] - cx, c['y'] - cy
        if -100 < sx < W + 100 and -100 < sy < H + 100:
            self.blit_ship(cv, 'c_map', c['x'], c['y'], c['h'], cx, cy)
            draw_circ(cv, sx, sy, 38, (120, 255, 190), 70, 2)
            pygame.draw.rect(cv, (8, 12, 24), (sx - 24, sy - 52, 48, 7))
            col = (80, 230, 110) if c['hp'] > 50 else ((255, 200, 70) if c['hp'] > 25 else (240, 80, 70))
            pygame.draw.rect(cv, col, (sx - 23, sy - 51, int(46 * c['hp'] / 100), 5))
        self.panel(cv, (W // 2 - 190, yy, 380, 46), 190)
        self.text(cv, 'CONVOY a %s  |  casco %d%%' % (c['dst']['name'], c['hp']), self.f_s,
                  (150, 255, 200) if c['hp'] > 40 else (255, 120, 100), W // 2, yy + 6, 'c')
        left = dist(c['x'], c['y'], c['dst']['dock'][0], c['dst']['dock'][1])
        self.text(cv, 'Faltan %d m  |  raiders vivos: %d' % (left, sum(1 for en in self.enemies if en.get('raider'))), self.f_s,
                  (200, 220, 240), W // 2, yy + 26, 'c')
        self.draw_pointer(cv, cx, cy, c['x'], c['y'], 'CONVOY', (120, 255, 190), 0.5 + 0.5 * math.sin(t * 5))

    def begin_rescue(self):
        """Náufragos: a veces bajo el alcance de una batería costera."""
        live = [n for n in self.nests if n['alive']]
        for _ in range(60):
            if live and random.random() < 0.6:
                n = random.choice(live)
                a = random.uniform(0, 6.28)
                d = random.uniform(235, 300)
                x, y = n['x'] + math.cos(a) * d, n['y'] + math.sin(a) * d
                guarded = True
            else:
                x, y = random.uniform(200, WORLD_W - 200), random.uniform(200, WORLD_H - 200)
                guarded = False
            if 100 < x < WORLD_W - 100 and 100 < y < WORLD_H - 100 and not self.on_land(x, y, 70) and dist(x, y, self.sx, self.sy) > 500:
                break
        t = clamp(dist(x, y, self.sx, self.sy) / (VMAX * 0.7) + 25, 45, 90)
        self.rescue = dict(x=x, y=y, t=t, total=t, prog=0.0, guarded=guarded)
        self.audio.play('alarm', .6)
        self.banner('¡SOS: NÁUFRAGOS!', ('Bajo el alcance de una batería costera | ' if guarded else '') + 'Llegá en %d s y quedate junto a la balsa' % t,
                    (255, 220, 90), 4.0)

    def upd_rescue(self, dt):
        r = self.rescue
        r['t'] -= dt
        d = dist(self.sx, self.sy, r['x'], r['y'])
        if d < 95 and abs(self.sv) < 70:
            r['prog'] += dt / 4.0
            if int(r['prog'] * 8) != int((r['prog'] - dt / 4.0) * 8):
                self.audio.play('blip', .4)
        else:
            r['prog'] = max(0.0, r['prog'] - dt / 6.0)
        if r['prog'] >= 1.0:
            reward = random.choice(('hull', 'fuel', 'ammo'))
            pts = 300 + 100 * self.wave
            self.add_score(pts)
            self.audio.play('win', .7)
            if reward == 'hull':
                self.hull = min(100, self.hull + 25)
                gift = '+25 casco (los náufragos ayudan con las reparaciones)'
            elif reward == 'fuel':
                self.fuel = min(100, self.fuel + 40)
                gift = '+40% combustible'
            else:
                self.ammo = min(40, self.ammo + 12)
                gift = '+12 munición'
            self.banner('¡NÁUFRAGOS RESCATADOS!', '+%d puntos  |  %s' % (pts, gift), (120, 255, 160), 3.6)
            self.rescue = None
            self.rescue_t = random.uniform(80, 120)
        elif r['t'] <= 0:
            self.toast('Los náufragos se perdieron en el mar...', (255, 160, 120))
            self.rescue = None
            self.rescue_t = random.uniform(70, 100)

    def antenna_city(self, i):
        """Pseudo-ciudad que representa una antena instalada (para el viaje y la defensa)."""
        x, y, r, sd = EXTRA_ISLANDS[i]
        return dict(name='ANTENA %s' % self.isl_name(i), x=x, y=y, r=r, hp=100.0, dead=False, seed=sd, dock=(x, y), antenna=i)

    ATTACK_TXT = {'antenna': ('Comandos enemigos asaltan tu antena', (120, 220, 255)), 'tank': ('Tanques enemigos entran en', (120, 255, 160)), 'ground': ('Desembarco enemigo en', (255, 150, 60)),
                  'aerial': ('Cazas enemigos sobre', (150, 100, 255))}

    def begin_attack(self, city, kind):
        """Ataque a una ciudad: hay que llegar con el barco antes de que se acabe el tiempo."""
        d = dist(self.sx, self.sy, city['x'], city['y'])
        limit = clamp(d / (VMAX * 0.7) + 14, 30, 80)
        self.attack = dict(city=city, kind=kind, t=limit, total=limit)
        self.strike_t = 1e9
        self.audio.play('alarm')
        txt, col = self.ATTACK_TXT[kind]
        self.banner('¡ATAQUE EN %s!' % city['name'], '%s | Llegá en %d s con tu barco' % (txt, limit), col, 4.2)

    def upd_attack(self, dt):
        at = self.attack
        c = at['city']
        if c['dead'] or (at['kind'] == 'antenna' and not self.antennas[c['antenna']]):
            self.attack = None
            self.strike_t = 30.0
            return False
        at['t'] -= dt
        near = dist(self.sx, self.sy, c['x'], c['y']) < c['r'] * 1.25 + 150 or dist(self.sx, self.sy, c['dock'][0], c['dock'][1]) < 130
        if near:
            self.attack = None
            if at['kind'] == 'antenna':
                self.start_ground(c, antenna=c['antenna'])
            else:
                {'tank': self.start_tank, 'ground': self.start_ground, 'aerial': self.start_aerial}[at['kind']](c)
            return True
        step = 0.5 if at['t'] < 5 else 1.0
        if at['t'] < 10 and int(at['t'] / step) != int((at['t'] + dt) / step):
            self.audio.play('blip', .5)
        if at['t'] <= 0 and at['kind'] == 'antenna':
            self.attack = None
            self.antennas[c['antenna']] = False
            self.audio.play('boom_l')
            self.shake = 14
            self.banner('¡ANTENA DESTRUIDA!', '%s cayó en manos enemigas' % c['name'], (255, 90, 70), 3.4)
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
            return False
        if at['t'] <= 0:
            self.attack = None
            c['hp'] = max(0.0, c['hp'] - 45)
            self.audio.play('boom_l')
            self.shake = 14
            if c['hp'] <= 0:
                c['dead'] = True
                self.banner('¡CIUDAD CAPTURADA!', c['name'], (255, 70, 60), 3.4)
            else:
                self.banner('¡LLEGASTE TARDE!', '%s sufrió daños graves (-45%%)' % c['name'], (255, 90, 70), 3.4)
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
            if all(x['dead'] for x in self.cities):
                self.game_over('Todas las ciudades fueron destruidas')
                return True
        return False

    def draw_pointer(self, cv, cx, cy, wx, wy, label, col, pul=0.5):
        """Flecha en el borde de la pantalla que apunta a un objetivo fuera de vista."""
        sx, sy = wx - cx, wy - cy
        if 40 < sx < W - 40 and 100 < sy < H - 40:
            return
        ang = math.atan2(wy - self.sy, wx - self.sx)
        ax = W / 2 + math.cos(ang) * min(W / 2 - 60, (H / 2 - 60) / max(0.01, abs(math.sin(ang))) * abs(math.cos(ang)))
        ay = H / 2 + math.sin(ang) * min(H / 2 - 60, (W / 2 - 60) / max(0.01, abs(math.cos(ang))) * abs(math.sin(ang)))
        pts = [(ax + math.cos(ang) * 26, ay + math.sin(ang) * 26),
               (ax + math.cos(ang + 2.5) * 22, ay + math.sin(ang + 2.5) * 22),
               (ax + math.cos(ang - 2.5) * 22, ay + math.sin(ang - 2.5) * 22)]
        glow(cv, ax, ay, 40, col, 0.5 + 0.4 * pul)
        pygame.draw.polygon(cv, col, pts)
        self.text(cv, label, self.f_s, col, ax, ay + 24, 'c')

    def draw_rescue(self, cv, cx, cy, y0=8):
        r = self.rescue
        t = self.t
        sx, sy = r['x'] - cx, r['y'] - cy
        pul = 0.5 + 0.5 * math.sin(t * 5)
        if -100 < sx < W + 100 and -100 < sy < H + 100:
            bob = math.sin(t * 2.2 + r['x']) * 3
            draw_circ(cv, sx, sy, 95, (255, 220, 90), 30 + 40 * pul, 2)
            pygame.draw.rect(cv, (120, 84, 50), (sx - 14, sy - 9 + bob, 28, 18), border_radius=4)
            pygame.draw.rect(cv, (200, 150, 90), (sx - 12, sy - 7 + bob, 24, 14), 1, border_radius=3)
            for k, off in enumerate((-8, 0, 8)):
                pygame.draw.circle(cv, (240, 120, 60) if k != 1 else (250, 230, 120), (int(sx + off), int(sy - 2 + bob)), 4)
            pygame.draw.line(cv, (230, 230, 230), (sx, sy + bob), (sx, sy - 24 + bob), 2)
            pygame.draw.polygon(cv, (255, 70, 60), [(sx, sy - 24 + bob), (sx + 13, sy - 19 + bob), (sx, sy - 14 + bob)])
            if r['prog'] > 0:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 32, sy + 22, 64, 9))
                pygame.draw.rect(cv, (120, 255, 160), (sx - 31, sy + 23, int(62 * r['prog']), 7))
                self.text(cv, 'RESCATANDO...', self.f_s, (180, 255, 200), sx, sy + 34, 'c')
        self.panel(cv, (W // 2 - 190, y0, 380, 46), 190)
        yy = y0 + 6
        sec = max(0.0, r['t'])
        self.text(cv, 'SOS NÁUFRAGOS  %02d.%03d' % (int(sec), int((sec % 1) * 1000)), self.f_m,
                  (255, 220, 90) if sec > 10 else (255, 90 + int(100 * pul), 70), W // 2, yy, 'c')
        self.draw_pointer(cv, cx, cy, r['x'], r['y'], 'NÁUFRAGOS', (255, 220, 90), pul)

    def draw_attack(self, cv, cx, cy):
        at = self.attack
        c = at['city']
        t = self.t
        low = at['t'] < 10
        pul = 0.5 + 0.5 * math.sin(t * (14 if at['t'] < 5 else 7))
        col = (255, int(80 + 130 * (1 - pul)), 60) if low else (255, 200, 90)
        sx, sy = c['x'] - cx, c['y'] - cy
        draw_circ(cv, sx, sy, c['r'] * 1.25 + 150, (255, 80, 60), 40 + 60 * pul, 3)
        self.panel(cv, (W // 2 - 215, 8, 430, 78), 200)
        self.text(cv, 'ATAQUE EN %s' % c['name'], self.f_m, col, W // 2, 14, 'c')
        sec = max(0.0, at['t'])
        self.text(cv, '%02d.%03d' % (int(sec), int((sec % 1) * 1000)), self.f_l, col, W // 2 - 70, 42, 'c')
        d = dist(self.sx, self.sy, c['x'], c['y'])
        self.text(cv, '%s  |  %d m' % ({'tank': 'TANQUES', 'ground': 'DESEMBARCO', 'aerial': 'CAZAS', 'antenna': 'COMANDOS'}[at['kind']], int(d)),
                  self.f_s, (210, 220, 240), W // 2 + 110, 52, 'c')
        self.draw_pointer(cv, cx, cy, c['x'], c['y'], c['name'], col, pul)
        if low:
            pygame.draw.rect(cv, (255, 40, 40), (0, 0, W, H), 4 + int(6 * pul))

    def nearest_dock(self):
        for c in self.cities:
            if not c['dead'] and dist(self.sx, self.sy, c['dock'][0], c['dock'][1]) < 120:
                return c
        return None

    def nearest_landing_island(self):
        best_dist = 280
        best_island = None
        for i, (x, y, r, s) in enumerate(EXTRA_ISLANDS):
            d = dist(self.sx, self.sy, x, y)
            if d < best_dist and i in ANTENNA_ISLANDS and not self.antennas[i]:
                best_dist = d
                best_island = (i, x, y, r, s)
        return best_island

    def wave_clear(self):
        bonus = 1000 * self.wave
        self.add_score(bonus)
        if self.wave >= WIN_WAVE:
            return self.game_over('¡Defendiste el archipiélago!', True)
        self.wave += 1
        for c in self.cities:
            if not c['dead']:
                c['hp'] = min(100, c['hp'] + 20)
        self.ammo = min(40, self.ammo + 12)
        self.spawn_nests()
        self.port_tries = 0
        self.port_done = False
        self.audio.play('win', .7)
        self.banner('OLEADA %d' % self.wave, 'Bonus +%d  |  Ciudades reparadas  |  +12 munición' % bonus, (120, 255, 160), 3.6)
        self.spawn_wave()

    def ai_map(self, en, dt):
        en['cool'] = max(0.0, en['cool'] - dt)
        d = dist(self.sx, self.sy, en['x'], en['y'])
        is_boss = en.get('is_boss', False)
        chase_dist = 520 if is_boss else (520 if en.get('sub') else 430)

        if is_boss and not en['seen'] and d < 700:
            en['seen'] = True
            self.audio.play('alarm')
            self.banner('¡BUQUE JEFE DETECTADO!', 'Escudo digital: necesitás %d antenas instaladas (L) para hackearlo (H)' % self.antennas_needed(), (255, 120, 220), 4.0)
        if en['state'] == 'patrol' and d < chase_dist and en['cool'] <= 0 and not en.get('shield'):
            en['state'] = 'chase'
            self.audio.play('ping')
            if is_boss:
                self.toast('¡JEFE ENEMIGO DETECTADO!', (255, 50, 50))
            else:
                self.toast('¡Contacto enemigo!', (255, 100, 90))
        elif en['state'] == 'chase' and (d > (1000 if is_boss else 680) or en['cool'] > 0):
            en['state'] = 'patrol'
        if en['state'] == 'chase':
            tx, ty = self.sx, self.sy
            sp = (66 + 4 * self.wave) if is_boss else (96 + 5 * self.wave)
        else:
            tx, ty = en['wp']
            sp = 32 if is_boss else 52
            if en.get('raider') and self.convoy is not None:
                tx, ty, sp = self.convoy['x'], self.convoy['y'], 80
            elif dist(en['x'], en['y'], tx, ty) < 50:
                en['wp'] = self.rand_wp()
        vx, vy = tx - en['x'], ty - en['y']
        n = math.hypot(vx, vy) or 1
        vx, vy = vx / n, vy / n
        for ix, iy, ir, sd in self.islands:
            dd = dist(en['x'], en['y'], ix, iy) or 1.0
            lim = coast_r(ir, sd, math.atan2(en['y'] - iy, en['x'] - ix), 1.1) + (170 if is_boss else 110)
            if dd < lim:
                k = (lim - dd) / (170 if is_boss else 110)
                vx += (en['x'] - ix) / dd * k * 2.4
                vy += (en['y'] - iy) / dd * k * 2.4
        want = bearing(vx, vy)
        en['h'] = (en['h'] + clamp(angle_diff(en['h'], want), -14 * dt if is_boss else -45 * dt, 14 * dt if is_boss else 45 * dt)) % 360
        en['v'] += (sp - en['v']) * min(1, dt * 1.5)
        dx, dy = vec(en['h'], en['v'] * dt)
        en['x'] = clamp(en['x'] + dx, 40, WORLD_W - 40)
        en['y'] = clamp(en['y'] + dy, 40, WORLD_H - 40)
        if random.random() < dt * (18 if is_boss else 14):
            bx, by = vec(en['h'], -62 if is_boss else -24)
            self.fxm.add('foam', en['x'] + bx, en['y'] + by, life=1.3, r0=4 if is_boss else 3, r1=14 if is_boss else 10, col=(230, 245, 255))

    # ---------------------------------------------------------- DEFENSA
    def start_defense(self, city):
        n = min(5 + 2 * self.wave, 16)
        self.fx = Particles()
        self.d = dict(city=city, missiles=[], inter=[], blasts=[], fires=[], t=0.0, total=n, killed=0, hits=0,
                      queue=sorted(random.uniform(0.6, 3.5 + n * 0.8) for _ in range(n)), cool=0.0, phase='play',
                      pt=0.0, shipx=W / 2, shipy=HZ + 100, sky_x=(W - SKY_W) / 2, destroyed=False, combo=0)
        self.aim = [W / 2, 280.0]
        self.go('defense')
        self.banner('DEFENDÉ ' + city['name'], 'Mouse/flechas: apuntar  |  Clic/ESPACIO: interceptor', (255, 120, 90), 3.0)

    def sky_target(self):
        d = self.d
        b = random.choice(d['city']['sky'])
        return d['sky_x'] + b['x'] + b['w'] / 2, HZ - b['h'], b

    def spawn_missile(self, split=False):
        d = self.d
        if random.random() < 0.16 and self.hull > 0:
            tx, ty, tb = d['shipx'], d['shipy'] - 20, None
            hit = 'ship'
        else:
            tx, ty, tb = self.sky_target()
            hit = 'city'
        sp = random.uniform(70, 105) + 9 * self.wave
        m = dict(x=random.uniform(60, W - 60), y=-10.0, tx=tx, ty=ty, sp=sp, trail=[], hit=hit, tb=tb,
                 split=(self.wave >= 2 and random.random() < 0.3), sy=random.uniform(160, 260))
        d['missiles'].append(m)

    def fire_interceptor(self):
        d = self.d
        if d['phase'] != 'play' or d['cool'] > 0:
            return
        if self.ammo <= 0:
            self.audio.play('empty')
            self.toast('¡Sin munición!', (255, 90, 80))
            return
        self.ammo -= 1
        d['cool'] = 0.16
        gx, gy = d['shipx'] + 82, d['shipy'] - 6
        d['inter'].append(dict(x=float(gx), y=float(gy), tx=self.aim[0], ty=min(self.aim[1], HZ + 20), trail=[]))
        self.audio.play('launch', .8)
        self.fx.add('glow', gx, gy, life=.18, r0=18, r1=40, col=(255, 230, 160))

    def upd_defense(self, dt):
        d = self.d
        keys = pygame.key.get_pressed()
        sp = 520 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.aim[0] -= sp
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.aim[0] += sp
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.aim[1] -= sp
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.aim[1] += sp
        self.aim[0], self.aim[1] = clamp(self.aim[0], 0, W), clamp(self.aim[1], 20, HZ + 20)
        d['t'] += dt
        d['cool'] = max(0.0, d['cool'] - dt)
        while d['queue'] and d['queue'][0] <= d['t']:
            d['queue'].pop(0)
            self.spawn_missile()
        for m in d['missiles'][:]:
            ang = math.atan2(m['ty'] - m['y'], m['tx'] - m['x'])
            m['x'] += math.cos(ang) * m['sp'] * dt
            m['y'] += math.sin(ang) * m['sp'] * dt
            m['trail'].append((m['x'], m['y']))
            m['trail'] = m['trail'][-28:]
            if random.random() < dt * 20:
                self.fx.add('smoke', m['x'], m['y'], 0, 0, 1.2, 3, 9, (90, 90, 96))
            if m['split'] and m['y'] > m['sy']:
                d['missiles'].remove(m)
                self.fx.add('glow', m['x'], m['y'], life=.3, r0=14, r1=40, col=(255, 120, 80))
                for _ in range(3):
                    tx, ty, tb = self.sky_target()
                    d['missiles'].append(dict(x=m['x'], y=m['y'], tx=tx, ty=ty, sp=m['sp'] * 1.1, trail=[], hit='city',
                                              tb=tb, split=False, sy=0))
                d['total'] += 2
                continue
            if m['y'] >= m['ty'] - 3 or dist(m['x'], m['y'], m['tx'], m['ty']) < 6:
                d['missiles'].remove(m)
                self.missile_impact(m)
        for it in d['inter'][:]:
            ang = math.atan2(it['ty'] - it['y'], it['tx'] - it['x'])
            it['x'] += math.cos(ang) * 640 * dt
            it['y'] += math.sin(ang) * 640 * dt
            it['trail'].append((it['x'], it['y']))
            it['trail'] = it['trail'][-14:]
            if dist(it['x'], it['y'], it['tx'], it['ty']) < 12:
                d['inter'].remove(it)
                d['blasts'].append(dict(x=it['tx'], y=it['ty'], age=0.0, R=64, chain=False))
                self.audio.play('boom_s', .55)
        for b in d['blasts'][:]:
            b['age'] += dt
            rad = b['R'] * min(1.0, b['age'] / 0.28)
            life = 0.9 if not b['chain'] else 0.6
            if b['age'] > life:
                d['blasts'].remove(b)
                continue
            if b['age'] < life * 0.62:
                for m in d['missiles'][:]:
                    if dist(m['x'], m['y'], b['x'], b['y']) < rad + 4:
                        d['missiles'].remove(m)
                        d['killed'] += 1
                        d['combo'] += 1
                        pts = 100 + (50 if b['chain'] else 0)
                        self.add_score(pts)
                        self.pop('+%d' % pts, m['x'], m['y'])
                        self.fx.explode(m['x'], m['y'], 0.8)
                        self.audio.play('boom_s', .5)
                        d['blasts'].append(dict(x=m['x'], y=m['y'], age=0.0, R=40, chain=True))
        for f in d['fires']:
            f[2] -= dt
            if random.random() < dt * 10:
                self.fx.add('smoke', f[0] + random.uniform(-6, 6), f[1], random.uniform(-6, 6), -30, 2.0, 4, 16, (40, 40, 44))
        d['fires'] = [f for f in d['fires'] if f[2] > 0]
        self.fx.update(dt)
        if self.hull <= 0:
            return self.game_over('Tu buque fue hundido por los misiles')
        if d['phase'] == 'play' and not d['queue'] and not d['missiles'] and not d['inter'] and not d['blasts']:
            d['phase'] = 'result'
            d['pt'] = 0.0
            if d['hits'] == 0:
                self.add_score(500)
                self.banner('¡DEFENSA PERFECTA!', '+500', (120, 255, 160), 2.6)
            else:
                self.banner('AMENAZA NEUTRALIZADA', 'Impactos: %d   Interceptados: %d' % (d['hits'], d['killed']),
                            (255, 220, 120), 2.6)
        if d['phase'] == 'result':
            d['pt'] += dt
            if d['pt'] > 2.8:
                self.end_defense()

    def missile_impact(self, m):
        d = self.d
        d['hits'] += 1
        self.fx.explode(m['x'], m['y'], 1.1, True)
        self.shake = max(self.shake, 9)
        if m['hit'] == 'ship':
            self.hull -= 14
            self.audio.play('hit')
            self.pop('-14 CASCO', m['x'], m['y'] - 20, (255, 110, 100))
        else:
            c = d['city']
            c['hp'] = max(0.0, c['hp'] - 11)
            self.audio.play('boom_l', .8)
            if m['tb'] is not None:
                m['tb']['h'] = max(10, int(m['tb']['h'] * 0.55))
            d['fires'].append([m['x'], m['y'], random.uniform(6, 10)])
            self.pop('-11% CIUDAD', m['x'], m['y'] - 20, (255, 110, 100))
            if c['hp'] <= 0 and not c['dead']:
                c['dead'] = True
                d['destroyed'] = True
                for b in c['sky']:
                    b['h'] = random.randint(6, 16)
                    self.fx.explode(d['sky_x'] + b['x'] + b['w'] / 2, HZ - 10, 1.4, True)
                self.shake = 20
                self.banner('¡CIUDAD DESTRUIDA!', c['name'], (255, 70, 60), 3.0)

    def end_defense(self):
        self.warned = False
        self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        if all(c['dead'] for c in self.cities):
            return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---------------------------------------------------------- CIBERATAQUE (minijuego de nodos)
    HACK_DIRS = ((0, -1, 1, 4), (1, 0, 2, 8), (0, 1, 4, 1), (-1, 0, 8, 2))

    @staticmethod
    def rot_mask(m, k=1):
        for _ in range(k % 4):
            m = ((m << 1) | (m >> 3)) & 15
        return m

    def hack_generate(self, cols, rows, nterm):
        while True:
            r0 = random.randrange(rows)
            masks = {(0, r0): 8}
            order = [(0, r0)]
            for _ in range(3000):
                if len(masks) >= int(cols * rows * 0.72):
                    break
                cx, cy = random.choice(order)
                dx, dy, bit, opp = random.choice(self.HACK_DIRS)
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in masks:
                    masks[(cx, cy)] |= bit
                    masks[(nx, ny)] = opp
                    order.append((nx, ny))
            leaves = [c for c, m in masks.items() if bin(m).count('1') == 1 and c != (0, r0)]
            if len(leaves) >= nterm:
                break
        terms = set(random.sample(leaves, nterm))
        tiles = {c: dict(m=m, sol=m, term=c in terms) for c, m in masks.items()}
        while True:
            for t in tiles.values():
                t['m'] = self.rot_mask(t['sol'], random.randrange(4))
            self.h = dict(tiles=tiles, root=(0, r0), cols=cols, rows=rows)
            if len(self.hack_power()[1]) < nterm:
                break
        return tiles, (0, r0), terms

    def hack_power(self):
        h = self.h
        tiles, root = h['tiles'], h['root']
        pw = set()
        if tiles[root]['m'] & 8:
            pw.add(root)
            stack = [root]
            while stack:
                cx, cy = stack.pop()
                m = tiles[(cx, cy)]['m']
                for dx, dy, bit, opp in self.HACK_DIRS:
                    nb = (cx + dx, cy + dy)
                    if m & bit and nb in tiles and nb not in pw and tiles[nb]['m'] & opp:
                        pw.add(nb)
                        stack.append(nb)
        return pw, [c for c in pw if tiles[c]['term']]

    def nearest_shield_boss(self, rng=520):
        best = None
        for en in self.enemies:
            if en.get('shield'):
                d = dist(self.sx, self.sy, en['x'], en['y'])
                if d < rng and (best is None or d < best[0]):
                    best = (d, en)
        return best[1] if best else None

    def antennas_needed(self):
        """Antenas mínimas para hackear al jefe: 2 al principio, +1 cada dos oleadas."""
        return min(len(self.antennas), 2 + (self.wave - 1) // 2)

    def try_hack(self):
        boss = self.nearest_shield_boss()
        n = sum(self.antennas.values())
        if boss is None:
            self.toast('No hay ningún escudo enemigo al alcance', (255, 200, 120))
        elif n < self.antennas_needed():
            self.toast('Faltan antenas: tenés %d y necesitás %d (desembarcá en las islas con L)' % (n, self.antennas_needed()), (255, 140, 100))
        elif boss['hack_cd'] > 0:
            self.toast('Sistemas enemigos reiniciando: %d s' % math.ceil(boss['hack_cd']), (255, 200, 120))
        else:
            self.start_hack(boss)

    def start_hack(self, boss):
        lvl, n = self.wave, sum(self.antennas.values())
        cols, rows = 5 + (lvl >= 3) + (lvl >= 5), 4 + (lvl >= 4)
        nterm = 2 + lvl // 3
        tiles, root, terms = self.hack_generate(cols, rows, nterm)
        total = max(22.0, 40.0 + 5 * n - 2 * (lvl - 1))
        csz = 86
        h = self.h
        h.update(boss=boss, n=n, nterm=nterm, t=total, total=total, base_total=total, fails=0, lvl=lvl, phase='play', pt=0.0, csz=csz,
                 gx=96, gy=(H - rows * csz) // 2 + 24, cur=root, kb=False, log=[], logt=0.0, done=set())
        h['rain'] = [[random.randrange(0, W, 18), random.uniform(-400, H), random.uniform(60, 160)] for _ in range(40)]
        if not hasattr(self, 'rain_gl'):
            self.rain_gl = [[self.f_s.render(ch, True, (0, g, int(g * .45))) for g in (35, 70, 130, 230)] for ch in '01']
        self.toasts, self.banners = [], []
        self.hack_say('> ENLACE CON %d ANTENA(S)' % n)
        self.hack_say('> OBJETIVO: ESCUDO DEL JEFE')
        self.hack_say('> ENERGIZA %d TERMINALES' % nterm)
        self.aim = [W / 2, H / 2]
        self.go('hack')

    def hack_retry(self):
        """Nuevo intento tras un fallo: puzzle distinto y un poco menos de tiempo."""
        old = self.h
        self.hack_generate(old['cols'], old['rows'], old['nterm'])
        new = self.h
        self.h = old
        old.update(tiles=new['tiles'], root=new['root'], cur=new['root'], done=set(), phase='play', pt=0.0)
        old['total'] = old['t'] = max(18.0, old['base_total'] - 3.0 * old['fails'])
        self.hack_say('> NUEVO ENLACE  (INTENTO %d)' % (old['fails'] + 1))
        self.hack_say('> RUTA REGENERADA')
        self.audio.play('pickup', .6)

    def hack_say(self, s):
        self.h['log'].append(s)
        self.h['log'] = self.h['log'][-9:]

    def hack_rotate(self, cell, k=1):
        h = self.h
        if h['phase'] != 'play' or cell not in h['tiles']:
            return
        t = h['tiles'][cell]
        t['m'] = self.rot_mask(t['m'], k)
        self.audio.play('blip', .5)
        tp = self.hack_power()[1]
        if len(tp) > len(h['done']):
            self.audio.play('pickup', .5)
        h['done'] = set(tp)
        if len(tp) == h['nterm']:
            h['phase'], h['pt'] = 'win', 0.0
            self.hack_say('> ACCESO CONCEDIDO')
            self.audio.play('win', .8)

    def hack_cell_at(self, pos):
        h = self.h
        cx, cy = (pos[0] - h['gx']) // h['csz'], (pos[1] - h['gy']) // h['csz']
        return (int(cx), int(cy)) if 0 <= cx < h['cols'] and 0 <= cy < h['rows'] else None

    def upd_hack(self, dt):
        h = self.h
        h['logt'] += dt
        for col in h['rain']:
            col[1] += col[2] * dt
            if col[1] - 15 * 16 > H:
                col[1] = random.uniform(-200, 0)
                col[2] = random.uniform(60, 160)
        if h['phase'] == 'play':
            h['t'] -= dt
            step = 0.5 if h['t'] < 5 else 1.0
            if h['t'] < 10 and int(h['t'] / step) != int((h['t'] + dt) / step):
                self.audio.play('blip', .5)
            if h['t'] <= 0:
                h['t'] = 0.0
                h['phase'], h['pt'] = 'fail', 0.0
                h['fails'] += 1
                self.hull = max(1.0, self.hull - 5)
                self.shake = 8
                self.hack_say('> INTRUSION DETECTADA')
                self.audio.play('lose', .6)
        else:
            h['pt'] += dt
            if h['phase'] == 'win' and h['pt'] > 1.8:
                self.end_hack(True)

    def end_hack(self, ok, abort=False):
        h = self.h
        boss = h['boss']
        self.go('map')
        if ok:
            boss['shield'] = False
            n = h['n']
            cut = min(0.4, 0.08 * n) * boss['max']
            boss['hp'] = max(1.0, boss['hp'] - cut)
            bonus = 300 + int(50 * h['t'])
            self.add_score(bonus)
            self.banner('¡ESCUDO DESTRUIDO!', 'Casco enemigo -%d%% por %d antena(s)  |  Bonus +%d' % (int(cut / boss['max'] * 100), n, bonus),
                        (110, 240, 255), 3.6)
        elif abort:
            boss['hack_cd'] = 6.0
            self.toast('Ciberataque abortado', (255, 200, 120))
        else:
            boss['hack_cd'] = 25.0
            self.toast('Ciberataque fallido. Sistemas enemigos reiniciando: 25 s', (255, 120, 100))

    def draw_hack_tile(self, cv, x, y, sz, tile, powered, hover, t):
        r = pygame.Rect(x + 3, y + 3, sz - 6, sz - 6)
        pygame.draw.rect(cv, (11, 19, 33), r, border_radius=10)
        pygame.draw.rect(cv, (64, 214, 244) if powered else (36, 58, 88), r, 2, border_radius=10)
        cx, cy = x + sz // 2, y + sz // 2
        col = (96, 246, 255) if powered else (72, 98, 132)
        if powered:
            glow(cv, cx, cy, 48, (30, 130, 170), 0.55)
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            if tile['m'] & bit:
                ex, ey = cx + dx * (sz // 2 - 3), cy + dy * (sz // 2 - 3)
                if powered:
                    pygame.draw.line(cv, (18, 86, 108), (cx, cy), (ex, ey), 14)
                pygame.draw.line(cv, col, (cx, cy), (ex, ey), 8)
        pygame.draw.circle(cv, col, (cx, cy), 7)
        if tile['term']:
            pts = [(cx + math.cos(math.radians(60 * k + 30)) * 19, cy + math.sin(math.radians(60 * k + 30)) * 19) for k in range(6)]
            pulse = 0.5 + 0.5 * math.sin(t * 6)
            ring = (90, 255, 150) if powered else (255, int(60 + 60 * pulse), int(60 + 40 * pulse))
            pygame.draw.polygon(cv, (11, 19, 33), pts)
            pygame.draw.polygon(cv, ring, pts, 3)
            pygame.draw.circle(cv, ring, (cx, cy), 6)
            if powered:
                glow(cv, cx, cy, 30, (40, 200, 110), 0.7)
        if hover:
            pygame.draw.rect(cv, (255, 255, 255), r.inflate(4, 4), 1, border_radius=11)

    def draw_hack(self, cv):
        h = self.h
        t = self.t
        cv.fill((4, 8, 14))
        for gx_, gy_, sp in h['rain']:
            for j in range(15):
                yy = gy_ - j * 16
                if 0 <= yy < H:
                    lv = 3 if j == 0 else (2 if j < 4 else (1 if j < 9 else 0))
                    cv.blit(self.rain_gl[(int(gx_) // 18 + j + int(t * 3)) % 2][lv], (gx_, yy))
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((4, 8, 14, 175))
        cv.blit(dark, (0, 0))
        cs, gx, gy = h['csz'], h['gx'], h['gy']
        self.text(cv, 'CIBERATAQUE  //  ESCUDO DIGITAL', self.f_l, (110, 240, 255), 96, 30)
        self.text(cv, 'Girá los nodos para llevar energía desde la fuente a todas las terminales', self.f_s, (150, 190, 220), 96, 72)
        pw = self.hack_power()[0]
        hover = h['cur'] if h['kb'] else self.hack_cell_at(pygame.mouse.get_pos())
        rx, ry = h['root']
        sy_ = gy + ry * cs + cs // 2
        glow(cv, gx - 40, sy_, 56, (40, 120, 255), 0.9 + 0.1 * math.sin(t * 5))
        pygame.draw.rect(cv, (16, 40, 90), (gx - 64, sy_ - 24, 44, 48), border_radius=8)
        pygame.draw.rect(cv, (90, 160, 255), (gx - 64, sy_ - 24, 44, 48), 2, border_radius=8)
        pygame.draw.polygon(cv, (255, 235, 120), [(gx - 40, sy_ - 16), (gx - 52, sy_ + 3), (gx - 42, sy_ + 3), (gx - 46, sy_ + 17), (gx - 30, sy_ - 4), (gx - 40, sy_ - 4)])
        pygame.draw.line(cv, (96, 246, 255) if (rx, ry) in pw else (72, 98, 132), (gx - 20, sy_), (gx + 4, sy_), 8)
        for c in range(h['cols']):
            for r in range(h['rows']):
                x, y = gx + c * cs, gy + r * cs
                tile = h['tiles'].get((c, r))
                if tile is None:
                    pygame.draw.rect(cv, (9, 14, 24), (x + 3, y + 3, cs - 6, cs - 6), border_radius=10)
                    pygame.draw.rect(cv, (22, 34, 52), (x + 3, y + 3, cs - 6, cs - 6), 1, border_radius=10)
                else:
                    self.draw_hack_tile(cv, x, y, cs, tile, (c, r) in pw, hover == (c, r), t)
        px = 780
        self.panel(cv, (px - 20, 100, 330, 320), 190)
        frac = clamp(h['t'] / h['total'], 0, 1)
        self.text(cv, 'TIEMPO', self.f_s, (170, 200, 230), px, 112)
        tcol = (90, 220, 255) if h['t'] > 10 else ((255, 210, 70) if h['t'] > 5 else (255, 70, 70))
        self.bar(cv, px, 134, 290, 24, frac, tcol, 'INTENTO %d' % (h['fails'] + 1))
        left = h['nterm'] - len(h['done'])
        self.text(cv, 'FIREWALL', self.f_s, (170, 200, 230), px, 170)
        self.bar(cv, px, 192, 290, 24, left / h['nterm'], (240, 90, 120), '%d%%' % int(100 * left / h['nterm']))
        self.text(cv, 'ANTENAS ENLAZADAS: %d' % h['n'], self.f_s, (150, 240, 255), px, 232)
        self.text(cv, 'TERMINALES: %d/%d' % (len(h['done']), h['nterm']), self.f_s, (150, 240, 255), px, 256)
        for i, ln in enumerate(h['log'][-6:]):
            self.text(cv, ln[:30], self.f_s, (90, 220, 150), px, 288 + i * 20, shadow=False)
        if int(t * 2) % 2 == 0:
            self.text(cv, '_', self.f_s, (90, 220, 150), px, 288 + min(6, len(h['log'])) * 20, shadow=False)
        sec = max(0.0, h['t'])
        low = h['t'] < 10 and h['phase'] == 'play'
        pul = 0.5 + 0.5 * math.sin(t * (14 if h['t'] < 5 else 8))
        big = (255, int(70 + 140 * (1 - pul)), 60) if low else tcol
        self.text(cv, '%02d.%03d' % (int(sec), int((sec % 1) * 1000)), self.f_xl, big, W - 44, 8, 'r')
        self.text(cv, 'SEG . MS', self.f_s, (150, 190, 220), W - 44, 86, 'r')
        if low:
            vg = pygame.Surface((W, H), pygame.SRCALPHA)
            a = int((40 + 90 * pul) * (1.4 if h['t'] < 5 else 1.0))
            for i in range(4):
                pygame.draw.rect(vg, (255, 30, 30, max(0, a - i * 28)), (i * 6, i * 6, W - i * 12, H - i * 12), 6)
            cv.blit(vg, (0, 0))
        self.text(cv, 'Clic izq.: girar  |  Clic der.: al revés  |  flechas+ESPACIO  |  TAB: abortar', self.f_s, (180, 205, 235), 96, H - 36)
        if h['phase'] != 'play':
            ok = h['phase'] == 'win'
            self.dim(cv, 90)
            self.text(cv, 'ACCESO CONCEDIDO' if ok else 'INTRUSION DETECTADA', self.f_xl, (110, 255, 170) if ok else (255, 90, 90), W // 2, H // 2 - 80, 'c')
            if not ok:
                self.text(cv, 'Contraataque: -5 casco', self.f_m, (255, 160, 140), W // 2, H // 2 + 20, 'c')
                if h['pt'] > 0.6:
                    nt = max(18.0, h['base_total'] - 3.0 * h['fails'])
                    if int(t * 2) % 2 == 0:
                        self.text(cv, 'ESPACIO / CLIC: REINTENTAR con puzzle nuevo (%.0f s)' % nt, self.f_m, (255, 255, 255), W // 2, H // 2 + 60, 'c')
                    self.text(cv, 'TAB: abandonar (reinicio de sistemas 25 s)', self.f_s, (190, 200, 220), W // 2, H // 2 + 96, 'c')

    # ---------------------------------------------------------- COMBATE
    def start_combat(self, en):
        self.fx = Particles()
        self.enemy_ref = en
        is_boss = en.get('is_boss', False)
        is_nest = en.get('nest', False)
        is_sub = en.get('sub', False)
        self.c = dict(
            p=dict(x=W / 2, y=H - 170.0, h=0.0, v=0.0, cool=0.0, wake=0.0, sink=None),
            e=dict(x=W / 2 + (random.uniform(-60, 60) if is_nest else random.uniform(-150, 150)),
                   y=130.0 if is_nest else (220.0 if is_boss else 170.0), h=180.0, v=0.0 if is_nest else (20.0 if is_boss else 40.0),
                   cool=3.0 if is_boss else 2.0,
                   orb=random.choice([-1, 1]), orb_t=5.0, burst=[], wake=0.0, sink=None, hp=en['hp'], max=en['max'], surf=False, ut=3.0),
            shells=[], t=0.0, is_boss=is_boss, nest=is_nest, sub=is_sub, name=en.get('name', ''))
        self.aim = [W / 2, 300.0]
        self.go('combat')
        if is_sub:
            self.audio.play('alarm')
            self.banner('¡SUBMARINO!', 'Solo es vulnerable cuando emerge a lanzar torpedos: esperalo y disparale  |  E: huir', (120, 220, 200), 4.0)
        elif is_nest:
            self.audio.play('alarm')
            self.banner('¡BATERÍA COSTERA!', 'Cañón fijo en el islote: esquivá sus misiles y destruilo  |  E: huir', (255, 140, 90), 3.6)
        elif is_boss:
            self.audio.play('alarm')
            self.banner('¡ACORAZADO %s!' % en['name'], 'Escudo digital caído  |  3 baterías de misiles  |  Hundilo o te hunde', (255, 60, 60), 4.0)
        else:
            self.banner('¡COMBATE NAVAL!', 'W/S/A/D: navegar  |  Mouse+Clic: disparar misil (vuela recto)  |  E: huir', (255, 150, 90), 3.4)

    def launch_missile(self, ship, ang, speed, own, off=0.0, dmg=(22, 12)):
        ox, oy = vec(ship['h'], off)
        fx_, fy_ = vec(ang, 30)
        vx, vy = vec(ang, speed)
        self.c['shells'].append(dict(x=ship['x'] + ox + fx_, y=ship['y'] + oy + fy_, vx=vx, vy=vy, ang=ang, own=own,
                                     life=3.0, dmg=dmg))

    def fire_shell(self):
        c = self.c
        p = c['p']
        if p['sink'] is not None or p['cool'] > 0:
            return
        if self.ammo <= 0:
            self.audio.play('empty')
            self.toast('¡Sin munición! Presioná E para huir', (255, 90, 80))
            return
        self.ammo -= 1
        p['cool'] = 0.9
        tx, ty = self.combat_aim()
        self.launch_missile(p, bearing(tx - p['x'], ty - p['y']), 400, 'p')
        self.audio.play('launch', .8)
        self.fx.add('glow', p['x'], p['y'], life=.2, r0=20, r1=44, col=(255, 220, 150))
        self.shake = max(self.shake, 3)

    def combat_aim(self):
        p = self.c['p']
        ax, ay = self.aim
        if not self.mouse_moved:
            fx, fy = vec(p['h'], 300)
            ax, ay = p['x'] + fx, p['y'] + fy
        d = dist(p['x'], p['y'], ax, ay)
        if d > 650:
            ax = p['x'] + (ax - p['x']) / d * 650
            ay = p['y'] + (ay - p['y']) / d * 650
        return clamp(ax, 20, W - 20), clamp(ay, 20, H - 20)

    def flee(self):
        c = self.c
        if c['p']['sink'] is not None or c['e']['sink'] is not None:
            return
        en = self.enemy_ref
        en['hp'] = c['e']['hp']
        if en.get('nest'):
            en['cool'] = 14.0
            bx, by = vec(bearing(self.sx - en['x'], self.sy - en['y']), 400)
            self.sx, self.sy = clamp(en['x'] + bx, 60, WORLD_W - 60), clamp(en['y'] + by, 60, WORLD_H - 60)
        else:
            en['cool'] = 6.0
            en['state'] = 'patrol'
            en['wp'] = self.rand_wp()
            bx, by = vec(bearing(en['x'] - self.sx, en['y'] - self.sy), 220)
            en['x'], en['y'] = clamp(self.sx + bx, 60, WORLD_W - 60), clamp(self.sy + by, 60, WORLD_H - 60)
        self.hull -= 8
        self.toast('Huiste bajo fuego: -8 casco', (255, 140, 90))
        self.audio.play('hit', .7)
        if self.hull <= 0:
            return self.game_over('Tu buque se hundió al huir')
        self.go('map')

    def upd_combat(self, dt):
        c = self.c
        p, e = c['p'], c['e']
        c['t'] += dt
        keys = pygame.key.get_pressed()
        alive_p = p['sink'] is None
        thr = ((1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0) - (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0)) if alive_p else 0
        turn = ((1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)) if alive_p else 0
        if self.fuel <= 0:
            thr = 0
        if thr > 0:
            p['v'] = min(125, p['v'] + 80 * dt)
        elif thr < 0:
            p['v'] = max(-35, p['v'] - 110 * dt)
        else:
            p['v'] -= p['v'] * 0.5 * dt
        p['h'] = (p['h'] + turn * 62 * clamp(abs(p['v']) / 50, 0.25, 1) * (1 if p['v'] >= 0 else -1) * dt) % 360
        dx, dy = vec(p['h'], p['v'] * dt)
        p['x'] += dx
        p['y'] += dy
        boss_c = c['is_boss']
        for ship in (p, e):
            mx_, my_ = (90, 150) if (ship is e and boss_c) else (50, 60)
            if ship['x'] < mx_ or ship['x'] > W - mx_ or ship['y'] < my_ or ship['y'] > H - my_:
                ship['x'], ship['y'] = clamp(ship['x'], mx_, W - mx_), clamp(ship['y'], my_, H - my_)
                ship['v'] *= 0.6
        self.fuel = max(0.0, self.fuel - abs(p['v']) / 125 * 0.35 * dt)
        self.audio.engine_vol(abs(p['v']) / 125 * 0.9 + 0.1)
        p['cool'] = max(0.0, p['cool'] - dt)
        # IA enemiga
        if e['sink'] is None and c['nest']:
            e['cool'] -= dt
            e['h'] = 180.0
            if e['cool'] <= 0 and p['sink'] is None:
                e['cool'] = random.uniform(2.2, 3.0) * max(0.6, 1 - 0.06 * self.wave)
                self.enemy_fire()
                if self.wave >= 2:
                    e['burst'].append([0.45, None])
                if self.wave >= 5:
                    e['burst'].append([0.9, None])
            e['burst'] = [[t_ - dt, m_] for t_, m_ in e['burst']]
            due = [b_ for b_ in e['burst'] if b_[0] <= 0]
            e['burst'] = [b_ for b_ in e['burst'] if b_[0] > 0]
            for _t, m_ in due:
                self.enemy_fire(m_)
        elif e['sink'] is None:
            dxp, dyp = p['x'] - e['x'], p['y'] - e['y']
            dd = math.hypot(dxp, dyp) or 1
            to_p = bearing(dxp, dyp)
            e['orb_t'] -= dt
            if e['orb_t'] <= 0:
                e['orb'] *= -1
                e['orb_t'] = random.uniform(4, 8)
            near, far = (260, 400) if c['is_boss'] else (260, 420)
            if dd > far:
                want = to_p
            elif dd < near:
                want = to_p + 180
            else:
                want = to_p + 90 * e['orb']
            edge = 190 if c['is_boss'] else 110
            if e['x'] < edge or e['x'] > W - edge or e['y'] < edge or e['y'] > H - edge:
                want = bearing(W / 2 - e['x'], H / 2 - e['y'])
            turn_rate = 17 if c['is_boss'] else 48
            e['h'] = (e['h'] + clamp(angle_diff(e['h'], want), -turn_rate * dt, turn_rate * dt)) % 360
            e['v'] += (((34 + 2 * self.wave) if c['is_boss'] else ((46 + 3 * self.wave) if c['sub'] else (62 + 5 * self.wave))) - e['v']) * min(1, dt * (0.8 if c['is_boss'] else 1.5))
            ex, ey = vec(e['h'], e['v'] * dt)
            e['x'] += ex
            e['y'] += ey
            e['cool'] -= dt
            is_boss = self.c.get('is_boss', False)
            if c['sub']:
                e['ut'] -= dt
                if not e['surf'] and random.random() < dt * 6:
                    self.fx.add('foam', e['x'] + random.uniform(-10, 10), e['y'] + random.uniform(-30, 30), life=1.2, r0=3, r1=11, col=(200, 235, 245))
                if e['ut'] <= 0 and p['sink'] is None:
                    e['surf'] = not e['surf']
                    if e['surf']:
                        e['ut'] = 3.4
                        self.sub_fire()
                        self.fx.splash(e['x'], e['y'], 1.0)
                        self.audio.play('ping', .6)
                    else:
                        e['ut'] = random.uniform(4.0, 5.5) * max(0.7, 1 - 0.05 * self.wave)
            elif e['cool'] <= 0 and p['sink'] is None:
                if is_boss:
                    e['cool'] = random.uniform(3.4, 4.4) * max(0.65, 1 - 0.05 * self.wave)
                    self.enemy_fire(0)
                    e['burst'] += [[0.35, 1], [0.7, 2]]
                else:
                    e['cool'] = random.uniform(2.1, 3.0) * max(0.55, 1 - 0.07 * self.wave)
                    self.enemy_fire()
                    if self.wave >= 3:
                        e['burst'].append([0.35, None])
            e['burst'] = [[t_ - dt, m_] for t_, m_ in e['burst']]
            due = [b_ for b_ in e['burst'] if b_[0] <= 0]
            e['burst'] = [b_ for b_ in e['burst'] if b_[0] > 0]
            for _t, m_ in due:
                self.enemy_fire(m_)
            if is_boss:
                if random.random() < dt * 9:
                    for sd in (-1, 1):
                        lx, ly = vec(e['h'] + 90, sd * 17)
                        fx_, fy_ = vec(e['h'], -38)
                        self.fx.add('smoke', e['x'] + lx + fx_, e['y'] + ly + fy_, -12, -22, 2.4, 5, 24, (46, 46, 52))
        # estelas
        for ship in (p, e):
            ship['wake'] -= dt
            if abs(ship['v']) > 15 and ship['wake'] <= 0 and ship['sink'] is None:
                ship['wake'] = 0.04
                bx, by = vec(ship['h'], -52)
                self.fx.add('foam', ship['x'] + bx + random.uniform(-5, 5), ship['y'] + by + random.uniform(-5, 5),
                            life=1.8, r0=6, r1=20, col=(230, 245, 255))
        for ship, hpf in ((p, self.hull / 100), (e, e['hp'] / e['max'])):
            if ship['sink'] is None:
                if hpf < .5 and random.random() < dt * 10:
                    self.fx.add('smoke', ship['x'], ship['y'], random.uniform(-8, 8), -25, 2.0, 6, 26, (50, 50, 50))
                if hpf < .25 and random.random() < dt * 14:
                    self.fx.add('glow', ship['x'] + random.uniform(-14, 14), ship['y'] + random.uniform(-30, 30), life=.4,
                                r0=8, r1=22, col=(255, 140, 50))
        # proyectiles
        self.update_missiles(dt)
        # hundimientos
        for ship, key in ((e, 'e'), (p, 'p')):
            if ship['sink'] is not None:
                ship['sink'] += dt
                ship['v'] *= 0.97
                if int(ship['sink'] * 5) != int((ship['sink'] - dt) * 5):
                    big_ = ship is e and c['is_boss']
                    self.fx.explode(ship['x'] + random.uniform(-30, 30) * (1.5 if big_ else 0.5), ship['y'] + random.uniform(-110, 110) if big_ else ship['y'] + random.uniform(-40, 40), 1.5 if big_ else 0.9, big_)
                    self.audio.play('boom_s', .6)
                    self.shake = max(self.shake, 7)
        if e['sink'] is None and e['hp'] <= 0:
            e['sink'] = 0.0
            self.audio.play('boom_l')
            self.fx.explode(e['x'], e['y'], 3.0 if c['is_boss'] else 1.8, True)
        if p['sink'] is None and self.hull <= 0:
            p['sink'] = 0.0
            self.audio.play('boom_l')
            self.fx.explode(p['x'], p['y'], 1.8, True)
        self.fx.update(dt)
        if e['sink'] is not None and e['sink'] > (4.0 if c['is_boss'] else 2.4):
            boss_kill = c.get('is_boss', False)
            if c['nest']:
                nst = self.enemy_ref
                nst['alive'] = False
                self.add_score(400 + 100 * self.wave)
                self.ammo = min(40, self.ammo + 8)
                self.radar_t = 60.0
                self.toast('¡Batería destruida! +%d  (+8 munición, radar enemigo 60 s)' % (400 + 100 * self.wave), (120, 255, 160))
                if self.hull <= 0:
                    return self.game_over('Tu buque no sobrevivió al combate')
                return self.go('map')
            self.add_score(500 + 100 * self.wave)
            self.ammo = min(40, self.ammo + (15 if boss_kill else 5))
            self.toast('¡%s hundido! +%d  (+%d munición)' % ('Buque jefe' if boss_kill else ('Submarino' if c['sub'] else 'Destructor'), 500 + 100 * self.wave, 15 if boss_kill else 5), (120, 255, 160))
            if self.enemy_ref in self.enemies:
                self.enemies.remove(self.enemy_ref)
            if self.hull <= 0:
                return self.game_over('Tu buque no sobrevivió al combate')
            self.go('map')
        elif p['sink'] is not None and p['sink'] > 2.6:
            self.game_over('Tu buque fue hundido en combate')

    def sub_fire(self):
        """Abanico de 3 torpedos lentos que apuntan a donde va a estar el jugador."""
        c = self.c
        p, e = c['p'], c['e']
        spd = 175 + 6 * self.wave
        T = dist(p['x'], p['y'], e['x'], e['y']) / spd
        vx, vy = vec(p['h'], p['v'])
        base = bearing(p['x'] + vx * T - e['x'], p['y'] + vy * T - e['y'])
        for d in (-8, 0, 8):
            self.launch_missile(e, base + d + random.uniform(-2, 2), spd, 'e', 0.0, (20, 12))
        self.audio.play('launch', .5)

    def enemy_fire(self, mount=None):
        c = self.c
        p, e = c['p'], c['e']
        boss = c['is_boss']
        spd = (232 + 7 * self.wave) if boss else (250 + 8 * self.wave)
        off = BOSS_MOUNTS[mount] if (boss and mount is not None) else 0.0
        ox, oy = vec(e['h'], off)
        T = dist(p['x'], p['y'], e['x'] + ox, e['y'] + oy) / spd
        vx, vy = vec(p['h'], p['v'])
        err = max(2.0, 11 - 1.2 * self.wave)
        ang = bearing(p['x'] + vx * T - e['x'] - ox, p['y'] + vy * T - e['y'] - oy) + random.uniform(-err, err)
        self.launch_missile(e, ang, spd, 'e', off, (18, 10) if boss else ((15, 9) if c['nest'] else (22, 12)))
        self.audio.play('launch', .5)
        self.fx.add('glow', e['x'] + ox, e['y'] + oy, life=.2, r0=22, r1=46, col=(255, 160, 120))

    def ship_hit(self, ship, x, y, boss):
        L, r, core = (108, 36, 56) if boss else (44, 17, 24)
        dx, dy = vec(ship['h'], 1)
        t = clamp((x - ship['x']) * dx + (y - ship['y']) * dy, -L, L)
        hit = dist(x, y, ship['x'] + dx * t, ship['y'] + dy * t) < r
        return hit, dist(x, y, ship['x'], ship['y']) < core

    def update_missiles(self, dt):
        c = self.c
        p, e = c['p'], c['e']
        for s in c['shells'][:]:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['life'] -= dt
            if random.random() < dt * 45:
                bx, by = vec(s['ang'], -14)
                self.fx.add('smoke', s['x'] + bx, s['y'] + by, 0, 0, 0.7, 2, 7, (200, 200, 205))
            tgt = e if s['own'] == 'p' else p
            if tgt['sink'] is None and not (tgt is e and c['sub'] and not e['surf']):
                if tgt is e and c['nest']:
                    dn = dist(s['x'], s['y'], e['x'], e['y'])
                    hit, full = dn < 46, dn < 26
                else:
                    hit, full = self.ship_hit(tgt, s['x'], s['y'], tgt is e and c['is_boss'])
                if hit:
                    c['shells'].remove(s)
                    self.missile_hit(s, tgt, full)
                    continue
            if s['life'] <= 0 or not (-60 < s['x'] < W + 60 and -60 < s['y'] < H + 60):
                c['shells'].remove(s)

    def missile_hit(self, s, tgt, full):
        c = self.c
        x, y = s['x'], s['y']
        if s['own'] == 'p':
            dmg = 3 if full else 2
            c['e']['hp'] -= dmg
            self.pop('-%d' % dmg, x, y - 20, (255, 255, 160))
        else:
            dmg = s['dmg'][0] if full else s['dmg'][1]
            self.hull -= dmg
            self.pop('-%d CASCO' % dmg, x, y - 20, (255, 110, 100))
            self.shake = max(self.shake, 12)
        self.fx.explode(x, y, 1.0 if full else 0.7)
        self.audio.play('hit')

    # ---------------------------------------------------------- BATALLA AÉREA (estilo Twinbee)
    AIR_SCROLL = 80.0

    def start_aerial(self, city=None):
        self.fx = Particles()
        w = self.wave
        kinds = ['vee', 'line', 'dive', 'vee', 'pair', 'line', 'bomber', 'dive', 'vee', 'pair']
        events, t = [], 2.0
        gap = max(3.4, 4.8 - 0.15 * w)
        for i in range(8 + w):
            k = kinds[i % len(kinds)]
            if k == 'bomber' and w < 2:
                k = 'line'
            events.append((t, k, random.uniform(200, W - 200)))
            t += gap + random.uniform(-0.4, 0.8)
        self.a = dict(city=city, t=0.0, scroll=0.0, phase='play', pt=0.0, fail=False, kills=0,
                      p=dict(x=W / 2, y=H - 140.0, hp=100.0, inv=0.0, cd=0.0, bcd=0.0, wl=1, shield=0.0, vx=0.0, dead=False),
                      foes=[], ebul=[], pbul=[], bombs=[], ground=[], caps=[], isl=[], clouds=[],
                      forms={}, fid=0, events=events, boss_t=t + 2.5, boss=None, boss_dead=False,
                      isl_t=0.0, boat_t=6.0, cloud_t=0.0)
        for yy in (-200, 100, 330, 560):
            self.air_spawn_island(random.uniform(80, W - 80), yy)
        for _ in range(9):
            self.air_spawn_cloud(random.uniform(0, H))
        self.go('aerial')
        self.banner('¡BATALLA AÉREA!', 'WASD mover | mantener ESPACIO/clic: disparar | B/clic der.: bomba a objetivos terrestres',
                    (100, 180, 255), 4.0)

    def air_spawn_island(self, x, y):
        a = self.a
        idx = random.randrange(len(self.air['isl']))
        r = self.air['isl_r'][idx]
        isl = dict(x=x, y=y, i=idx, r=r)
        a['isl'].append(isl)
        for _ in range(random.choice((0, 1, 1, 2))):
            ang, d = random.uniform(0, 6.28), random.uniform(0.1, 0.5) * r
            a['ground'].append(dict(kind='sam', x=x + math.cos(ang) * d, y=y + math.sin(ang) * d, vx=0.0, hp=3,
                                    cd=random.uniform(1.0, 3.0), ang=180.0))

    def air_spawn_cloud(self, y):
        self.a['clouds'].append(dict(x=random.uniform(-100, W + 100), y=y, v=random.uniform(125, 175),
                                     i=random.randrange(len(self.air['clouds'])),
                                     s=random.uniform(0.7, 1.3), tw=random.uniform(0, 6.28)))

    def air_foe(self, kind, x, y, fid=None, **kw):
        w = self.wave
        hp = {'viper': 2 + w // 3, 'stealth': 5 + w // 2, 'bomber': 16 + 3 * w}[kind]
        f = dict(kind=kind, x=x, y=y, bx=x, hp=float(hp), max=float(hp), t=0.0, ph=random.uniform(0, 6.28),
                 cd=random.uniform(1.2, 2.8), fid=fid, vx=0.0, vy=0.0, mode=0, hit=0.0)
        f.update(kw)
        self.a['foes'].append(f)
        return f

    def air_spawn_formation(self, kind, x):
        a = self.a
        a['fid'] += 1
        fid = a['fid']
        if kind == 'vee':
            offs = [(0, 0), (-50, -38), (50, -38), (-100, -76), (100, -76)]
            for ox, oy in offs:
                self.air_foe('viper', clamp(x + ox, 50, W - 50), -50 + oy, fid)
        elif kind == 'line':
            for i in range(6):
                self.air_foe('viper', x, -50 - i * 52, fid)
        elif kind == 'dive':
            side = random.choice((-1, 1))
            for i in range(3):
                self.air_foe('stealth', -60 if side < 0 else W + 60, 70 + i * 70, fid, mode=side)
        elif kind == 'pair':
            for ox in (-90, 90):
                self.air_foe('stealth', clamp(x + ox, 80, W - 80), -60, fid, mode=0)
        elif kind == 'bomber':
            self.air_foe('bomber', x, -90, fid)
        a['forms'][fid] = dict(n=sum(1 for f in a['foes'] if f['fid'] == fid), escaped=False)

    def air_ebul(self, x, y, ang, speed, r=5):
        spd = speed * (1 + 0.03 * self.wave)
        vx, vy = vec(ang, spd)
        self.a['ebul'].append(dict(x=x, y=y, vx=vx, vy=vy, r=r))

    def air_boom(self, x, y, size=1.0, big=False, snd='boom_s'):
        self.fx.explode(x, y, size, big)
        self.audio.play(snd, .5)

    def air_kill_foe(self, f):
        a = self.a
        if f not in a['foes']:
            return
        a['foes'].remove(f)
        a['kills'] += 1
        pts = {'viper': 100, 'stealth': 250, 'bomber': 800}[f['kind']]
        self.add_score(pts)
        self.pop('+%d' % pts, f['x'], f['y'] - 20)
        self.air_boom(f['x'], f['y'], {'viper': 0.9, 'stealth': 1.1, 'bomber': 2.0}[f['kind']], f['kind'] == 'bomber')
        form = a['forms'].get(f['fid'])
        if form:
            form['n'] -= 1
            if form['n'] <= 0 and not form['escaped']:
                a['caps'].append(dict(x=f['x'], y=f['y'], kind=random.choice(('W', 'W', 'H', 'S')), t=0.0))
        elif f['kind'] == 'bomber':
            a['caps'].append(dict(x=f['x'], y=f['y'], kind='W', t=0.0))

    def air_fire_player(self):
        a = self.a
        p = a['p']
        wl = p['wl']
        angs = {1: (0,), 2: (-3, 3), 3: (-9, 0, 9), 4: (-16, -8, 0, 8, 16)}[wl]
        for k, ang in enumerate(angs):
            off = (k - (len(angs) - 1) / 2) * (9 if wl == 2 else 5)
            vx, vy = vec(ang, 800)
            a['pbul'].append(dict(x=p['x'] + off, y=p['y'] - 36, vx=vx, vy=vy))
        self.audio.play('mg', .15)

    def air_bomb(self):
        a = self.a
        p = a['p']
        if p['dead'] or p['bcd'] > 0 or a['phase'] != 'play':
            return
        p['bcd'] = 0.55
        tx, ty = p['x'], max(60.0, p['y'] - 200)
        a['bombs'].append(dict(x0=p['x'], y0=p['y'], x1=tx, y1=ty, t=0.0, T=0.7))
        self.audio.play('launch', .35)

    def air_hit_ground(self, g, dmg):
        a = self.a
        g['hp'] -= dmg
        if g['hp'] <= 0 and g in a['ground']:
            a['ground'].remove(g)
            pts = 300 if g['kind'] == 'sam' else 400
            self.add_score(pts)
            self.pop('+%d' % pts, g['x'], g['y'] - 18)
            self.air_boom(g['x'], g['y'], 1.2, True)
            if random.random() < 0.5:
                a['caps'].append(dict(x=g['x'], y=g['y'], kind=random.choice(('W', 'H', 'S')), t=0.0))

    def air_hurt(self, dmg):
        a = self.a
        p = a['p']
        if p['dead'] or p['inv'] > 0 or a['phase'] != 'play':
            return
        if p['shield'] > 0:
            p['shield'] = max(0.0, p['shield'] - 1.2)
            p['inv'] = 0.25
            self.audio.play('hit', .3)
            return
        p['hp'] -= dmg
        p['inv'] = 1.3
        p['wl'] = max(1, p['wl'] - (1 if dmg >= 20 else 0))
        self.shake = max(self.shake, 8)
        self.audio.play('hit', .6)
        self.pop('-%d' % dmg, p['x'], p['y'] - 40, (255, 110, 100))

    def upd_aerial(self, dt):
        a = self.a
        p = a['p']
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        a['t'] += dt
        sc = self.AIR_SCROLL
        a['scroll'] += sc * dt
        p['cd'] = max(0.0, p['cd'] - dt)
        p['bcd'] = max(0.0, p['bcd'] - dt)
        p['inv'] = max(0.0, p['inv'] - dt)
        p['shield'] = max(0.0, p['shield'] - dt)
        if not p['dead']:
            mx = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            my = (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0) - (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0)
            n = math.hypot(mx, my) or 1.0
            p['vx'] += (mx / n * 320 - p['vx']) * min(1, dt * 12)
            p['x'] = clamp(p['x'] + p['vx'] * dt, 44, W - 44)
            p['y'] = clamp(p['y'] + my / n * 300 * dt, 150, H - 70)
            if (keys[pygame.K_SPACE] or keys[pygame.K_f] or mouse[0]) and p['cd'] <= 0 and a['phase'] == 'play':
                p['cd'] = 0.11
                self.air_fire_player()
            if random.random() < dt * 40:
                self.fx.add('glow', p['x'] + random.uniform(-3, 3), p['y'] + 42, 0, 60, 0.15, 8, 3, (255, 150, 60))
        # escenario
        for isl in a['isl'][:]:
            isl['y'] += sc * dt
            if isl['y'] > H + isl['r'] * 2.4:
                a['isl'].remove(isl)
        for g in a['ground'][:]:
            g['y'] += (sc if g['kind'] == 'sam' else sc * 0.7) * dt
            g['x'] += g['vx'] * dt
            if g['y'] > H + 60:
                a['ground'].remove(g)
                continue
            if 20 < g['y'] < H * 0.7 and not p['dead']:
                g['ang'] = bearing(p['x'] - g['x'], p['y'] - g['y'])
                g['cd'] -= dt
                if g['cd'] <= 0:
                    g['cd'] = random.uniform(2.2, 3.4)
                    self.air_ebul(g['x'], g['y'], g['ang'] + random.uniform(-4, 4), 190)
        for c in a['clouds'][:]:
            c['y'] += c['v'] * dt
            if c['y'] > H + 120:
                a['clouds'].remove(c)
        a['isl_t'] -= dt
        if a['isl_t'] <= 0:
            a['isl_t'] = random.uniform(4.0, 7.0)
            self.air_spawn_island(random.uniform(60, W - 60), -260)
        a['cloud_t'] -= dt
        if a['cloud_t'] <= 0:
            a['cloud_t'] = random.uniform(0.7, 1.6)
            self.air_spawn_cloud(-140)
        a['boat_t'] -= dt
        if a['boat_t'] <= 0 and a['phase'] == 'play' and not a['boss']:
            a['boat_t'] = random.uniform(8, 13)
            a['ground'].append(dict(kind='boat', x=random.uniform(120, W - 120), y=-50.0, vx=random.uniform(-25, 25),
                                    hp=4, cd=2.0, ang=180.0))
        # guion
        if a['phase'] == 'play':
            while a['events'] and a['events'][0][0] <= a['t']:
                _, kind, x = a['events'].pop(0)
                self.air_spawn_formation(kind, x)
            if a['boss'] is None and a['t'] >= a['boss_t']:
                hp = 80 + 20 * self.wave
                a['boss'] = dict(x=W / 2, y=-170.0, hp=float(hp), max=float(hp), t=0.0, pc=2.0, pi=0, stream=0, sd=0.0,
                                 wc=1.2, hit=0.0)
                self.audio.play('alarm')
                self.banner('¡ALERTA! COMANDANTE STEALTH', 'Destruí al bombardero furtivo', (255, 90, 70), 3.2)
        # enemigos
        for f in a['foes'][:]:
            f['t'] += dt
            f['hit'] = max(0.0, f['hit'] - dt)
            k = f['kind']
            if k == 'viper':
                f['y'] += (110 + 3 * self.wave) * dt
                f['x'] = f['bx'] + math.sin(f['t'] * 2.2 + f['ph']) * 55
            elif k == 'stealth' and f['mode'] != 0:
                if f['t'] < 1.3:
                    f['x'] += -f['mode'] * 230 * dt
                    f['y'] += 30 * dt
                else:
                    if f['t'] < 1.45:
                        f['vx'] = clamp((p['x'] - f['x']) * 1.4, -230, 230)
                    f['x'] += f['vx'] * dt
                    f['y'] += 270 * dt
            elif k == 'stealth':
                f['y'] += 150 * dt
                if f['t'] < 2.4:
                    f['x'] += clamp(p['x'] - f['x'], -1, 1) * 60 * dt
            elif k == 'bomber':
                f['y'] += (45 if f['y'] < 150 or f['t'] > 18 else 0) * dt
                f['x'] = f['bx'] + math.sin(f['t'] * 0.6) * 140
            f['cd'] -= dt
            if f['cd'] <= 0 and 30 < f['y'] < H * 0.65 and not p['dead'] and a['phase'] == 'play':
                aim = bearing(p['x'] - f['x'], p['y'] - f['y'])
                if k == 'viper':
                    f['cd'] = random.uniform(2.0, 3.6)
                    self.air_ebul(f['x'], f['y'] + 20, aim + random.uniform(-3, 3), 210)
                elif k == 'stealth':
                    f['cd'] = random.uniform(2.2, 3.0)
                    for da in (-14, 0, 14):
                        self.air_ebul(f['x'], f['y'] + 20, aim + da, 230)
                else:
                    f['cd'] = 1.15
                    f['mode'] += 1
                    if f['mode'] % 2:
                        for i in range(12):
                            self.air_ebul(f['x'], f['y'] + 10, i * 30 + f['t'] * 20, 150, 6)
                    else:
                        for da in (-18, -9, 0, 9, 18):
                            self.air_ebul(f['x'], f['y'] + 30, aim + da, 220)
            if f['y'] > H + 90 or f['x'] < -140 or f['x'] > W + 140:
                a['foes'].remove(f)
                form = a['forms'].get(f['fid'])
                if form:
                    form['escaped'] = True
        # jefe
        b = a['boss']
        if b and not a['boss_dead']:
            b['t'] += dt
            b['hit'] = max(0.0, b['hit'] - dt)
            if b['y'] < 175:
                b['y'] += 80 * dt
            else:
                b['x'] = W / 2 + math.sin(b['t'] * 0.55) * (W / 2 - 230)
                rage = b['hp'] < b['max'] * 0.5
                b['pc'] -= dt
                if b['pc'] <= 0 and not p['dead']:
                    pat = b['pi'] % 3
                    b['pi'] += 1
                    b['pc'] = 1.7 if rage else 2.5
                    aim = bearing(p['x'] - b['x'], p['y'] - b['y'])
                    if pat == 0:
                        for i in range(-3, 4):
                            self.air_ebul(b['x'], b['y'] + 60, aim + i * 11, 215)
                    elif pat == 1:
                        off = random.uniform(0, 360)
                        for i in range(20 if rage else 16):
                            self.air_ebul(b['x'], b['y'] + 20, off + i * (360 / (20 if rage else 16)), 150, 6)
                    else:
                        b['stream'], b['sd'] = 12 if rage else 9, 0.0
                if b['stream'] > 0:
                    b['sd'] -= dt
                    if b['sd'] <= 0 and not p['dead']:
                        b['stream'] -= 1
                        b['sd'] = 0.08
                        self.air_ebul(b['x'], b['y'] + 50, bearing(p['x'] - b['x'], p['y'] - b['y']) + random.uniform(-2, 2), 270)
                b['wc'] -= dt
                if b['wc'] <= 0 and not p['dead']:
                    b['wc'] = 1.2 if rage else 1.8
                    for sx in (-1, 1):
                        self.air_ebul(b['x'] + sx * 110, b['y'] + 30, bearing(p['x'] - b['x'] - sx * 110, p['y'] - b['y'] - 30), 230)
        # balas del jugador
        for bl in a['pbul'][:]:
            bl['x'] += bl['vx'] * dt
            bl['y'] += bl['vy'] * dt
            if bl['y'] < -30 or bl['x'] < -30 or bl['x'] > W + 30:
                a['pbul'].remove(bl)
                continue
            hit = None
            for f in a['foes']:
                if dist(bl['x'], bl['y'], f['x'], f['y']) < {'viper': 24, 'stealth': 30, 'bomber': 60}[f['kind']]:
                    hit = f
                    break
            if hit:
                hit['hp'] -= 1
                hit['hit'] = 0.08
                a['pbul'].remove(bl)
                self.fx.add('spark', bl['x'], bl['y'], random.uniform(-100, 100), random.uniform(-60, 60), 0.2, col=(255, 230, 150), drag=2)
                if hit['hp'] <= 0:
                    self.air_kill_foe(hit)
                continue
            if b and not a['boss_dead'] and dist(bl['x'], bl['y'], b['x'], b['y'] + 10) < 80:
                b['hp'] -= 1
                b['hit'] = 0.08
                a['pbul'].remove(bl)
                self.fx.add('spark', bl['x'], bl['y'], random.uniform(-100, 100), random.uniform(-60, 60), 0.2, col=(255, 230, 150), drag=2)
                continue
        # balas enemigas
        for eb in a['ebul'][:]:
            eb['x'] += eb['vx'] * dt
            eb['y'] += eb['vy'] * dt
            if not (-30 < eb['x'] < W + 30 and -30 < eb['y'] < H + 30):
                a['ebul'].remove(eb)
            elif not p['dead'] and dist(eb['x'], eb['y'], p['x'], p['y']) < eb['r'] + 8:
                a['ebul'].remove(eb)
                self.air_hurt(10)
        # bombas
        for bm in a['bombs'][:]:
            bm['t'] += dt
            if bm['t'] >= bm['T']:
                a['bombs'].remove(bm)
                self.fx.add('ring', bm['x1'], bm['y1'], life=0.5, r0=6, r1=60, col=(255, 230, 170))
                self.air_boom(bm['x1'], bm['y1'], 1.0)
                for g in a['ground'][:]:
                    if dist(g['x'], g['y'], bm['x1'], bm['y1']) < 58:
                        self.air_hit_ground(g, 3)
        # cápsulas
        for q in a['caps'][:]:
            q['t'] += dt
            q['y'] += 90 * dt
            if not p['dead'] and dist(q['x'], q['y'], p['x'], p['y']) < 34:
                a['caps'].remove(q)
                self.audio.play('pickup')
                if q['kind'] == 'W':
                    p['wl'] = min(4, p['wl'] + 1)
                    self.pop('ARMA %d' % p['wl'], p['x'], p['y'] - 40, (255, 200, 90))
                elif q['kind'] == 'H':
                    p['hp'] = min(100.0, p['hp'] + 30)
                    self.pop('+30 AVIÓN', p['x'], p['y'] - 40, (120, 255, 150))
                else:
                    p['shield'] = 7.0
                    self.pop('ESCUDO', p['x'], p['y'] - 40, (120, 220, 255))
            elif q['y'] > H + 30:
                a['caps'].remove(q)
        # choque contra enemigos
        if not p['dead']:
            for f in a['foes'][:]:
                if dist(f['x'], f['y'], p['x'], p['y']) < {'viper': 28, 'stealth': 32, 'bomber': 56}[f['kind']] and p['inv'] <= 0:
                    self.air_hurt(20)
                    if f['kind'] != 'bomber':
                        self.air_kill_foe(f)
        if b and not a['boss_dead'] and not p['dead'] and dist(b['x'], b['y'], p['x'], p['y']) < 85:
            self.air_hurt(20)
        # jefe derrotado / jugador caído
        if b and not a['boss_dead'] and b['hp'] <= 0:
            a['boss_dead'] = True
            self.add_score(4000)
            for _ in range(10):
                self.air_boom(b['x'] + random.uniform(-90, 90), b['y'] + random.uniform(-60, 60), 1.6, True, 'boom_l')
            for f in a['foes'][:]:
                self.air_boom(f['x'], f['y'], 1.0)
                a['foes'].remove(f)
            a['ebul'].clear()
            self.shake = 22
            if a['phase'] == 'play':
                a['phase'], a['pt'] = 'result', 0.0
                bonus = 500 + 100 * self.wave
                self.add_score(bonus)
                self.ammo = min(40, self.ammo + 8)
                self.audio.play('win', .7)
                self.banner('¡VICTORIA AÉREA!', 'Bajas: %d   Jefe +4000   Bonus +%d   (+8 munición)' % (a['kills'], bonus),
                            (120, 255, 160), 3.2)
        if not p['dead'] and p['hp'] <= 0:
            p['dead'] = True
            self.air_boom(p['x'], p['y'], 1.8, True, 'boom_l')
            self.shake = 16
            if a['phase'] == 'play':
                a['phase'], a['fail'], a['pt'] = 'result', True, -1.0
                self.banner('¡AVIÓN DERRIBADO!', 'El ataque aéreo daña la ciudad', (255, 80, 70), 3.0)
        self.fx.update(dt)
        if a['phase'] == 'result':
            a['pt'] += dt
            if a['pt'] > 3.0:
                self.end_aerial()

    def end_aerial(self):
        a = self.a
        city = a['city']
        if a['fail'] and city and not city['dead']:
            city['hp'] = max(0.0, city['hp'] - 25)
            self.toast('Los cazas bombardearon %s: -25%%' % city['name'], (255, 140, 90))
            if city['hp'] <= 0:
                city['dead'] = True
        self.warned = False
        self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        if all(c['dead'] for c in self.cities):
            return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---------------------------------------------------------- COMBATE DE INFANTERÍA
    def isl_name(self, i):
        return 'ISLA %d' % (i + 1)

    def make_ground(self, seed, R, city_seed=None, antenna=False):
        ext = int(R * 2.0)
        s = pygame.Surface((ext * 2, ext * 2), pygame.SRCALPHA)
        self.paint_island(s, ext, ext, R, seed, True)
        if antenna:
            cx, cy = ext, ext
            pygame.draw.circle(s, (0, 0, 0, 70), (cx + 5, cy + 7), 64)
            pygame.draw.circle(s, (150, 152, 150), (cx, cy), 60)
            pygame.draw.circle(s, (186, 190, 192), (cx, cy), 55)
            for k in range(8):
                a = 6.2832 * k / 8 + 0.4
                pygame.draw.line(s, (96, 100, 104), (cx, cy), (cx + math.cos(a) * 52, cy + math.sin(a) * 52), 3)
                pygame.draw.circle(s, (70, 74, 78), (int(cx + math.cos(a) * 52), int(cy + math.sin(a) * 52)), 5)
            pygame.draw.circle(s, (110, 116, 122), (cx, cy), 22)
            pygame.draw.circle(s, (230, 70, 60), (cx, cy), 9)
            pygame.draw.circle(s, (255, 190, 170), (cx - 2, cy - 2), 3)
            for rr in (30, 42):
                pygame.draw.circle(s, (120, 230, 255), (cx, cy), rr, 1)
        elif city_seed is not None:
            cs = self.make_city(int(R * 0.7), city_seed, False)
            s.blit(cs, (ext - cs.get_width() // 2, ext - cs.get_height() // 2))
        else:
            cx, cy = ext, ext
            pygame.draw.circle(s, (0, 0, 0, 60), (cx + 4, cy + 6), 50)
            pygame.draw.circle(s, (150, 152, 150), (cx, cy), 48)
            pygame.draw.circle(s, (196, 198, 194), (cx, cy), 44)
            for k in range(20):
                a0, a1 = 6.2832 * k / 20, 6.2832 * (k + 1) / 20
                pts = [(cx + math.cos(a) * rr, cy + math.sin(a) * rr) for rr in (36, 42) for a in (a0, a1)]
                pygame.draw.polygon(s, (240, 200, 40) if k % 2 else (40, 40, 44), [pts[0], pts[1], pts[3], pts[2]])
            pygame.draw.circle(s, (130, 134, 134), (cx, cy), 30)
            pygame.draw.circle(s, (92, 96, 98), (cx, cy), 30, 2)
            pygame.draw.line(s, (92, 96, 98), (cx - 24, cy), (cx + 24, cy), 2)
            pygame.draw.line(s, (92, 96, 98), (cx, cy - 24), (cx, cy + 24), 2)
        return s, (W // 2 - ext, H // 2 - ext)

    def gen_covers(self, seed, R, n, avoid):
        covers = []
        for _ in range(500):
            if len(covers) >= n:
                break
            a = random.uniform(0, 6.2832)
            d = random.uniform(0.24, 0.74) * coast_r(R, seed, a, 1.0)
            x, y = W / 2 + math.cos(a) * d, H / 2 + math.sin(a) * d
            kind = random.choice(('sandbag', 'sandbag', 'rock', 'crates'))
            r = 24 if kind == 'sandbag' else 22
            if any(dist(x, y, c['x'], c['y']) < c['r'] + r + 46 for c in covers):
                continue
            if any(dist(x, y, ax, ay) < r + ar for ax, ay, ar in avoid):
                continue
            covers.append(dict(x=x, y=y, r=r, kind=kind, seed=random.randrange(10 ** 6)))
        return covers

    def init_ground(self, mode, seed, city, covers_n, avoid, spawn, kinds, queue=None, island_idx=None, R=ARENA_R, antenna=None):
        land, off = self.make_ground(seed, R, seed if mode == 'invasion' else None, antenna is not None)
        covers = self.gen_covers(seed, R, covers_n, avoid + [(spawn[0], spawn[1], 90)])
        for c in covers:
            draw_cover(land, dict(c, x=c['x'] - off[0], y=c['y'] - off[1]))
        self.fx = Particles()
        self.g = dict(mode=mode, city=city, R=R, seed=seed, land=land.convert_alpha(), land_off=off, cam=[0.0, 0.0], covers=covers,
                      angs=[random.uniform(0, 6.28) for _ in range(3)], queue=queue or [], enemies=[], bullets=[],
                      nades=[], corpses=[], decals=[], boats=[], crates=[], t=0.0, total=len(kinds), kills=0,
                      phase='play', pt=0.0, city0=city['hp'], fail=False, island_idx=island_idx, hurt=0.0, antenna=antenna,
                      ant_t=0.0, spawn=spawn,
                      p=dict(x=float(spawn[0]), y=float(spawn[1]), h=0.0, vx=0.0, vy=0.0, hp=PLAYER_HP, mag=30, reload=0.0,
                             cd=0.0, gren=4, gcd=0.0, ph=0.0, flash=0.0, bloom=0.0, dead=False, dead_t=0.0))
        self.aim = [W / 2, 200.0]
        self.g_camera(0.0, True)
        self.go('ground')
        return covers

    def new_soldier(self, kind, x, y, h, state, mode, cover=None):
        hp = ENEMY_TYPES[kind]['hp'] + self.wave // 2
        return dict(x=x, y=y, h=h, h0=h, kind=kind, hp=float(hp), max=float(hp), cd=random.uniform(0.6, 1.6),
                    state=state, mode=mode, cover=cover, ph=0.0, ph0=random.uniform(0, 6.28), flash=0.0, hit=0.0,
                    burst=0, bcd=0.0, tele=0.0, aimlock=h, strafe=random.choice((-1, 1)), strafe_t=random.uniform(1, 3),
                    role='guard', wp=None, wpi=0, pause=0.0, excl=0.0)

    def start_landing(self, island_idx):
        x, y, r, s = EXTRA_ISLANDS[island_idx]
        if self.landing_attempts[island_idx] >= MAX_LANDING_ATTEMPTS:
            self.toast('Sin intentos de desembarco en esta isla', (255, 140, 90))
            return
        self.landing_attempts[island_idx] += 1
        n = LANDING_ENEMIES
        n_mg, n_gr = max(1, n // 5), max(1, n // 5)
        kinds = ['mg'] * n_mg + ['gren'] * n_gr + ['rifle'] * (n - n_mg - n_gr)
        sy = H / 2 + coast_r(LAND_R, s, math.pi / 2, 0.84)
        spawn = (W / 2, sy)
        city = dict(name=self.isl_name(island_idx), x=x, y=y, r=r, hp=100.0, dead=False, seed=s)
        covers = self.init_ground('landing', s, city, 16, [(W / 2, H / 2, 80)], spawn, kinds, island_idx=island_idx, R=LAND_R)
        g = self.g
        random.shuffle(kinds)
        order = sorted(range(len(covers)), key=lambda i: -dist(covers[i]['x'], covers[i]['y'], spawn[0], spawn[1]))
        for i, kd in enumerate(kinds):
            ci = order[i % len(order)] if covers else None
            if ci is not None:
                c = covers[ci]
                away = bearing(c['x'] - spawn[0], c['y'] - spawn[1]) + (0 if i < len(order) else random.choice((-55, 55)))
                ox, oy = vec(away, c['r'] + 12)
                ex, ey = c['x'] + ox, c['y'] + oy
            else:
                ex, ey = W / 2, H / 2 - 100
            d = dist(ex, ey, W / 2, H / 2) or 1.0
            lim = coast_r(LAND_R, s, math.atan2(ey - H / 2, ex - W / 2), 0.9)
            if d > lim:
                ex, ey = W / 2 + (ex - W / 2) / d * lim, H / 2 + (ey - H / 2) / d * lim
            mode = 'pusher' if kd == 'rifle' and random.random() < 0.35 else 'defender'
            e = self.new_soldier(kd, ex, ey, bearing(spawn[0] - ex, spawn[1] - ey), 'hold', mode, ci)
            g['enemies'].append(e)
        # centinelas: patrullan con un cono de visión; si te ven dan la alarma y llegan refuerzos
        rifles = [e for e in g['enemies'] if e['kind'] == 'rifle']
        random.shuffle(rifles)
        for e in rifles[:max(2, n // 3)]:
            e['role'] = 'sentry'
            L = random.uniform(130, 210)
            ox, oy = vec(random.uniform(0, 360), L)
            tx, ty = e['x'] + ox, e['y'] + oy
            d = dist(tx, ty, W / 2, H / 2) or 1.0
            lim = coast_r(LAND_R, s, math.atan2(ty - H / 2, tx - W / 2), 0.82)
            if d > lim:
                tx, ty = W / 2 + (tx - W / 2) / d * lim, H / 2 + (ty - H / 2) / d * lim
            e['wp'] = [(e['x'], e['y']), (tx, ty)]
            e['h0'] = e['h'] = bearing(tx - e['x'], ty - e['y'])
        g['total'] = len(g['enemies'])
        left = MAX_LANDING_ATTEMPTS - self.landing_attempts[island_idx]
        self.banner('¡DESEMBARCO EN %s!' % self.isl_name(island_idx),
                    'Eliminá a los %d soldados para instalar la antena  |  Intentos restantes: %d' % (n, left),
                    (100, 180, 255), 4.0)
        self.toast('Hay centinelas patrullando: si te ven, dan la alarma', (255, 220, 120))

    def start_ground(self, city, antenna=None):
        n = min(8 + 3 * self.wave, 26)
        if antenna is not None:
            n = max(7, int(n * 0.8))
        n_mg = min(n // 6, 1 + self.wave // 2)
        n_gr = min(n // 5, 1 + self.wave // 2)
        kinds = ['mg'] * n_mg + ['gren'] * n_gr + ['rifle'] * (n - n_mg - n_gr)
        random.shuffle(kinds)
        queue = sorted([(random.uniform(0.5, 6 + n * 1.1), k, random.randrange(3)) for k in kinds], key=lambda q: q[0])
        spawn = (W / 2, H / 2 + 175)
        self.init_ground('invasion', city['seed'], city, 7, [(W / 2, H / 2, 150)], spawn, kinds, queue, antenna=antenna)
        if antenna is not None:
            self.banner('¡ASALTO A LA ANTENA!', 'Defendé %s | Clic: disparar | ESPACIO: granada | R: recargar' % city['name'],
                        (120, 220, 255), 3.8)
        else:
            self.banner('¡INVASIÓN ANFIBIA!', 'Defendé %s | Clic: disparar | ESPACIO: granada | R: recargar' % city['name'],
                        (255, 150, 60), 3.8)

    def spawn_ground_enemy(self, kind, idx):
        g = self.g
        a = g['angs'][idx]
        r = coast_r(g['R'], g['seed'], a, 0.97)
        x, y = W / 2 + math.cos(a) * r, H / 2 + math.sin(a) * r
        e = self.new_soldier(kind, x, y, bearing(W / 2 - x, H / 2 - y), 'combat', 'pusher')
        g['enemies'].append(e)
        g['boats'].append([x + math.cos(a) * 55, y + math.sin(a) * 55, bearing(-math.cos(a), -math.sin(a)), 0.0])
        self.fx.splash(x + math.cos(a) * 40, y + math.sin(a) * 40, 0.8)

    def g_camera(self, dt, snap=False):
        g = self.g
        p, R = g['p'], g['R']
        cam = g['cam']
        for i, (c, lim, size) in enumerate(((p['x'], W / 2, W), (p['y'], H / 2, H))):
            lo, hi = lim - R * 1.1, lim + R * 1.1 - size
            tgt = (lo + hi) / 2 if hi < lo else clamp(c - size / 2, lo, hi)
            cam[i] = tgt if snap else cam[i] + (tgt - cam[i]) * min(1.0, dt * 6)

    def gpop(self, s, x, y, col=(255, 255, 160)):
        cam = self.g['cam']
        self.pop(s, x - cam[0], y - cam[1], col)

    def ground_aim(self):
        g = self.g
        p, cam = g['p'], g['cam']
        ax, ay = self.aim[0] + cam[0], self.aim[1] + cam[1]
        if not self.mouse_moved:
            fx, fy = vec(p['h'], 320)
            ax, ay = p['x'] + fx, p['y'] + fy
        lim = g['R'] * 1.1
        return clamp(ax, W / 2 - lim, W / 2 + lim), clamp(ay, H / 2 - lim, H / 2 + lim)

    def g_step(self, s, dx, dy, is_player=False):
        g = self.g
        s['x'] += dx
        s['y'] += dy
        for c in g['covers']:
            d = dist(s['x'], s['y'], c['x'], c['y']) or 1.0
            m = c['r'] + 11
            if d < m:
                s['x'] = c['x'] + (s['x'] - c['x']) / d * m
                s['y'] = c['y'] + (s['y'] - c['y']) / d * m
        cx, cy = W / 2, H / 2
        d = dist(s['x'], s['y'], cx, cy) or 1.0
        lim = coast_r(g['R'], g['seed'], math.atan2(s['y'] - cy, s['x'] - cx), 0.92)
        if d > lim:
            s['x'], s['y'] = cx + (s['x'] - cx) / d * lim, cy + (s['y'] - cy) / d * lim
        elif is_player and g['mode'] == 'invasion' and d < 62:
            s['x'], s['y'] = cx + (s['x'] - cx) / d * 62, cy + (s['y'] - cy) / d * 62

    def g_ign(self, x, y):
        return {i for i, c in enumerate(self.g['covers']) if dist(x, y, c['x'], c['y']) < c['r'] + 16}

    def g_los(self, x0, y0, x1, y1):
        ign = self.g_ign(x0, y0)
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy or 1.0
        for i, c in enumerate(self.g['covers']):
            if i in ign:
                continue
            t = clamp(((c['x'] - x0) * vx + (c['y'] - y0) * vy) / L2, 0, 1)
            if dist(c['x'], c['y'], x0 + vx * t, y0 + vy * t) < c['r'] * 0.85:
                return False
        return True

    def alert(self, e, alarm=False):
        g = self.g
        if e['state'] == 'combat':
            return
        e['state'] = 'combat'
        e['excl'] = 1.0
        e['cd'] = max(e['cd'], random.uniform(0.9, 1.7))
        for o in g['enemies']:
            if o['state'] == 'hold' and dist(o['x'], o['y'], e['x'], e['y']) < (300 if alarm else 110):
                o['state'] = 'combat'
                o['excl'] = 1.0
                o['cd'] = max(o['cd'], random.uniform(0.9, 2.4 if alarm else 1.7))
        if alarm and g['mode'] == 'landing' and not g.get('alarm'):
            g['alarm'] = True
            self.audio.play('alarm', .4)
            self.toast('¡ALARMA! Un centinela te vio: llegan refuerzos', (255, 110, 90))
            for i in range(2):
                g['queue'].append((g['t'] + 5.0 + 3.0 * i, 'rifle', random.randrange(3)))
            g['total'] += 2

    def start_reload(self):
        p = self.g['p']
        if p['dead'] or p['reload'] > 0 or p['mag'] >= 30:
            return
        p['reload'] = 1.3
        self.audio.play('blip', .6)

    def player_shoot(self):
        g = self.g
        p = g['p']
        if p['dead'] or p['reload'] > 0 or p['cd'] > 0 or g['phase'] != 'play':
            return
        if p['mag'] <= 0:
            self.start_reload()
            return
        p['mag'] -= 1
        p['cd'] = 0.1
        p['flash'] = 0.06
        p['bloom'] = min(6.0, p['bloom'] + 0.8)
        ang = p['h'] + random.uniform(-1, 1) * (1.0 + p['bloom'])
        mx, my = vec(p['h'], 40)
        vx, vy = vec(ang, 580)
        g['bullets'].append(dict(x=p['x'] + mx, y=p['y'] + my, vx=vx, vy=vy, own='p', dmg=1.0, life=0.85,
                                 ign=self.g_ign(p['x'], p['y'])))
        self.audio.play('mg', .3)
        ex, ey = vec(p['h'] + 90, 12)
        self.fx.add('spark', p['x'] + ex, p['y'] + ey, ex * 12, ey * 12 - 30, 0.4, col=(230, 190, 80), drag=2, grav=120)
        for e in g['enemies']:
            if e['state'] == 'hold' and dist(e['x'], e['y'], p['x'], p['y']) < 230:
                self.alert(e)

    def throw_grenade_p(self):
        g = self.g
        p = g['p']
        if p['dead'] or p['gren'] <= 0 or p['gcd'] > 0 or g['phase'] != 'play':
            return
        p['gren'] -= 1
        p['gcd'] = 0.7
        ax, ay = self.ground_aim()
        d = clamp(dist(p['x'], p['y'], ax, ay), 80, 330)
        tx, ty = vec(p['h'], d)
        g['nades'].append(dict(x0=p['x'], y0=p['y'], x1=p['x'] + tx, y1=p['y'] + ty, t=0.0, T=d / 240 + 0.35, own='p'))
        self.audio.play('blip', .8)
        for e in g['enemies']:
            if e['state'] == 'hold' and dist(e['x'], e['y'], p['x'], p['y']) < 300:
                self.alert(e)

    def enemy_shoot(self, e, aim, spread, speed, dmg):
        g = self.g
        a = aim + random.uniform(-spread, spread)
        mx, my = vec(a, 40)
        vx, vy = vec(a, speed)
        g['bullets'].append(dict(x=e['x'] + mx, y=e['y'] + my, vx=vx, vy=vy, own='e', dmg=dmg, life=1.3,
                                 ign=self.g_ign(e['x'], e['y'])))
        e['flash'] = 0.06
        e['h'] = aim
        if dist(e['x'], e['y'], g['p']['x'], g['p']['y']) < 560:
            self.audio.play('mg', .2)

    def enemy_throw(self, e):
        g = self.g
        p = g['p']
        lim_ = g['R'] * 1.0
        tx = clamp(p['x'] + p['vx'] * 0.5 + random.uniform(-24, 24), W / 2 - lim_, W / 2 + lim_)
        ty = clamp(p['y'] + p['vy'] * 0.5 + random.uniform(-24, 24), H / 2 - lim_, H / 2 + lim_)
        d = dist(e['x'], e['y'], tx, ty)
        g['nades'].append(dict(x0=e['x'], y0=e['y'], x1=tx, y1=ty, t=0.0, T=clamp(d / 230, 0.8, 1.7), own='e'))
        e['h'] = bearing(tx - e['x'], ty - e['y'])
        self.audio.play('blip', .5)

    def explode_nade(self, n):
        g = self.g
        p = g['p']
        x, y, R = n['x1'], n['y1'], 62
        self.fx.explode(x, y, 1.1, True)
        self.audio.play('boom_s', .7)
        self.shake = max(self.shake, 7)
        g['decals'].append((x, y, R * 0.55))
        g['decals'] = g['decals'][-40:]
        for e in g['enemies'][:]:
            d = dist(x, y, e['x'], e['y'])
            if d < R:
                e['hp'] -= (6.5 if n['own'] == 'p' else 2.0) * (1 - 0.45 * d / R)
                e['hit'] = 0.15
                if e['state'] == 'hold':
                    self.alert(e)
                if e['hp'] <= 0:
                    self.kill_ground_enemy(e)
        d = dist(x, y, p['x'], p['y'])
        if not p['dead'] and d < R:
            dmg = int(32 * (1 - 0.6 * d / R))
            self.hurt_player(dmg)

    def hurt_player(self, dmg):
        g = self.g
        p = g['p']
        if p['dead'] or g['phase'] != 'play':
            return
        p['hp'] -= dmg
        g['hurt'] = 0.5
        self.shake = max(self.shake, 4 + dmg * 0.5)
        self.audio.play('hit', .5)
        self.gpop('-%d' % dmg, p['x'], p['y'] - 22, (255, 110, 100))

    def kill_ground_enemy(self, e):
        g = self.g
        if e not in g['enemies']:
            return
        g['enemies'].remove(e)
        g['kills'] += 1
        pts = ENEMY_TYPES[e['kind']]['pts']
        self.add_score(pts)
        self.gpop('+%d' % pts, e['x'], e['y'] - 18)
        g['corpses'].append(dict(x=e['x'], y=e['y'], h=e['h'] + random.uniform(-60, 60), kind=e['kind'], age=0.0))
        g['corpses'] = g['corpses'][-30:]
        self.fx.add('glow', e['x'], e['y'], life=.25, r0=8, r1=22, col=(255, 160, 90))
        for _ in range(6):
            a = random.uniform(0, 6.28)
            self.fx.add('spark', e['x'], e['y'], math.cos(a) * 110, math.sin(a) * 110, 0.35, col=(255, 200, 120), drag=2)
        if random.random() < 0.28:
            g['crates'].append(dict(x=e['x'], y=e['y'], t=0.0, kind=random.choice(('med', 'gren'))))

    def mv(self, e, ang, speed, dt):
        dx, dy = vec(ang, speed * dt)
        self.g_step(e, dx, dy)
        e['ph'] += speed * dt / 9.0

    def ai_soldier(self, e, dt):
        g = self.g
        p = g['p']
        T = ENEMY_TYPES[e['kind']]
        alive = not p['dead']
        e['cd'] -= dt
        e['flash'] = max(0.0, e['flash'] - dt)
        e['hit'] = max(0.0, e['hit'] - dt)
        dp = dist(e['x'], e['y'], p['x'], p['y']) if alive else 9999.0
        e['excl'] = max(0.0, e['excl'] - dt)
        if e['state'] == 'hold':
            sentry = e['role'] == 'sentry'
            if sentry:
                e['pause'] -= dt
                if e['pause'] > 0:
                    e['h'] = (e['h'] + 55 * math.sin(g['t'] * 1.6 + e['ph0']) * dt) % 360
                else:
                    tx, ty = e['wp'][e['wpi']]
                    if dist(e['x'], e['y'], tx, ty) < 10:
                        e['wpi'] ^= 1
                        e['pause'] = random.uniform(1.0, 2.4)
                    else:
                        hd = bearing(tx - e['x'], ty - e['y'])
                        self.mv(e, hd, T['speed'] * 0.45, dt)
                        e['h'] = (e['h'] + clamp(angle_diff(e['h'], hd), -260 * dt, 260 * dt)) % 360
            else:
                e['h'] = (e['h0'] + 38 * math.sin(g['t'] * 0.7 + e['ph0'])) % 360
            if alive:
                rng, fov = (340, 110) if sentry else (240, 90)
                seen = dp < 95
                if not seen and dp < rng:
                    seen = (abs(angle_diff(e['h'], bearing(p['x'] - e['x'], p['y'] - e['y']))) < fov / 2
                            and self.g_los(e['x'], e['y'], p['x'], p['y']))
                if seen:
                    self.alert(e, alarm=sentry)
            return
        sp = T['speed'] * (1 + 0.03 * self.wave)
        los = alive and dp < T['range'] and self.g_los(e['x'], e['y'], p['x'], p['y'])
        to_p = bearing(p['x'] - e['x'], p['y'] - e['y']) if alive else e['h']
        e['strafe_t'] -= dt
        if e['strafe_t'] <= 0:
            e['strafe'] *= -1
            e['strafe_t'] = random.uniform(1.2, 3.2)
        moving = None
        if g['mode'] == 'invasion':
            dcx, dcy = W / 2 - e['x'], H / 2 - e['y']
            dc = math.hypot(dcx, dcy)
            if dc > 96:
                if not (los and dp < T['range'] * 0.75):
                    moving = bearing(dcx, dcy)
            elif not g['city']['dead'] and g['phase'] == 'play':
                g['city']['hp'] = max(0.0, g['city']['hp'] - {'rifle': 0.35, 'mg': 0.5, 'gren': 0.6}[e['kind']] * dt)
                if random.random() < dt * 3:
                    self.fx.add('glow', W / 2 + random.uniform(-60, 60), H / 2 + random.uniform(-50, 50), life=.25,
                                r0=8, r1=20, col=(255, 150, 70))
                if e['state'] == 'combat' and not los:
                    e['h'] = bearing(dcx, dcy)
        elif e['kind'] == 'gren':
            if dp < 185:
                moving = to_p + 180
            elif dp > 330:
                moving = to_p
            else:
                moving = to_p + 90 * e['strafe']
                sp *= 0.5
        elif e['kind'] == 'mg':
            if dp > T['range'] * 1.15:
                moving, sp = to_p, sp * 0.8
        elif e['mode'] == 'pusher':
            moving = to_p + 28 * e['strafe'] if dp > 165 else to_p + 90 * e['strafe']
        elif e['cover'] is not None:
            c = g['covers'][e['cover']]
            away = bearing(c['x'] - g['spawn'][0], c['y'] - g['spawn'][1])
            px_, py_ = vec(away + 90, math.sin(g['t'] * 1.1 + e['ph0']) * 28)
            ax_, ay_ = vec(away, c['r'] + 12)
            tx, ty = c['x'] + ax_ + px_, c['y'] + ay_ + py_
            if dist(e['x'], e['y'], tx, ty) > 4:
                moving, sp = bearing(tx - e['x'], ty - e['y']), sp * 0.85
        if moving is not None:
            self.mv(e, moving, sp, dt)
        if alive and (los or e['burst'] > 0 or e['tele'] > 0 or e['kind'] == 'gren'):
            target = to_p
        else:
            target = moving if moving is not None else e['h']
        e['h'] = (e['h'] + clamp(angle_diff(e['h'], target), -420 * dt, 420 * dt)) % 360
        if not alive:
            return
        wv = self.wave
        if e['burst'] > 0:
            e['bcd'] -= dt
            if e['bcd'] <= 0:
                e['burst'] -= 1
                if e['kind'] == 'mg':
                    self.enemy_shoot(e, e['aimlock'], 5.0, 390, T['dmg'])
                    e['bcd'] = 0.09
                else:
                    self.enemy_shoot(e, to_p, max(2.5, 6.5 - 0.5 * wv) + dp * 0.008, 300, T['dmg'])
                    e['bcd'] = 0.17
        elif e['tele'] > 0:
            e['tele'] -= dt
            if e['tele'] <= 0:
                e['burst'], e['bcd'] = 8, 0.0
        elif e['cd'] <= 0:
            if e['kind'] == 'gren':
                if 110 < dp < T['range']:
                    self.enemy_throw(e)
                    e['cd'] = random.uniform(*T['rate']) * max(0.6, 1 - 0.05 * wv)
            elif los:
                e['cd'] = random.uniform(*T['rate']) * max(0.6, 1 - 0.05 * wv)
                if e['kind'] == 'mg':
                    e['tele'] = 0.7
                    e['aimlock'] = to_p
                    self.audio.play('ping', .25)
                else:
                    e['burst'], e['bcd'] = (2 if wv >= 3 else 1), 0.0

    def upd_ground(self, dt):
        g = self.g
        p, city = g['p'], g['city']
        keys = pygame.key.get_pressed()
        g['t'] += dt
        g['hurt'] = max(0.0, g['hurt'] - dt)
        alive = not p['dead']
        if alive:
            mx = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            my = (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0) - (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0)
            n = math.hypot(mx, my) or 1.0
            sp = 135.0 if mx or my else 0.0
            ox, oy = p['x'], p['y']
            self.g_step(p, mx / n * sp * dt, my / n * sp * dt, True)
            p['vx'], p['vy'] = (p['x'] - ox) / max(dt, 1e-4), (p['y'] - oy) / max(dt, 1e-4)
            p['ph'] += math.hypot(p['vx'], p['vy']) * dt / 9.0
            ax, ay = self.ground_aim()
            p['h'] = bearing(ax - p['x'], ay - p['y'])
            p['cd'] = max(0.0, p['cd'] - dt)
            p['gcd'] = max(0.0, p['gcd'] - dt)
            p['flash'] = max(0.0, p['flash'] - dt)
            p['bloom'] = max(0.0, p['bloom'] - 7 * dt)
            if p['reload'] > 0:
                p['reload'] -= dt
                if p['reload'] <= 0:
                    p['mag'] = 30
            elif p['mag'] <= 0:
                self.start_reload()
            if (pygame.mouse.get_pressed()[0] or keys[pygame.K_f]) and g['phase'] == 'play':
                self.player_shoot()
        self.g_camera(dt)
        if g['phase'] == 'play':
            while g['queue'] and g['queue'][0][0] <= g['t']:
                _, kind, idx = g['queue'].pop(0)
                self.spawn_ground_enemy(kind, idx)
        for b in g['boats']:
            b[3] += dt
        g['boats'] = [b for b in g['boats'] if b[3] < 1.8]
        for e in g['enemies'][:]:
            self.ai_soldier(e, dt)
        for b in g['bullets'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if b['life'] <= 0 or dist(b['x'], b['y'], W / 2, H / 2) > g['R'] * 1.25:
                g['bullets'].remove(b)
                continue
            blocked = False
            for i, c in enumerate(g['covers']):
                if i not in b['ign'] and dist(b['x'], b['y'], c['x'], c['y']) < c['r'] * 0.9:
                    blocked = True
                    break
            if blocked:
                self.fx.add('smoke', b['x'], b['y'], 0, -10, 0.5, 3, 9, (190, 170, 130))
                for _ in range(3):
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-80, 80), random.uniform(-80, 80), 0.2,
                                col=(255, 220, 140), drag=2)
                g['bullets'].remove(b)
                continue
            if b['own'] == 'p':
                hit = next((e for e in g['enemies'] if dist(b['x'], b['y'], e['x'], e['y']) < 13), None)
                if hit:
                    hit['hp'] -= b['dmg']
                    hit['hit'] = 0.1
                    if hit['state'] == 'hold':
                        self.alert(hit)
                    self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25,
                                col=(255, 120, 90), drag=2)
                    g['bullets'].remove(b)
                    if hit['hp'] <= 0:
                        self.kill_ground_enemy(hit)
            elif alive and dist(b['x'], b['y'], p['x'], p['y']) < 12:
                g['bullets'].remove(b)
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-90, 90), 0.25,
                            col=(255, 120, 90), drag=2)
                self.hurt_player(int(b['dmg']))
        for n in g['nades'][:]:
            n['t'] += dt
            if n['t'] >= n['T']:
                g['nades'].remove(n)
                self.explode_nade(n)
        for q in g['crates'][:]:
            q['t'] += dt
            if alive and dist(q['x'], q['y'], p['x'], p['y']) < 24:
                g['crates'].remove(q)
                self.audio.play('pickup', .8)
                if q['kind'] == 'med':
                    p['hp'] = min(PLAYER_HP, p['hp'] + 40)
                    self.gpop('+40 SALUD', q['x'], q['y'] - 16, (120, 255, 150))
                else:
                    p['gren'] = min(6, p['gren'] + 2)
                    self.gpop('+2 GRANADAS', q['x'], q['y'] - 16, (255, 230, 90))
            elif q['t'] > 30:
                g['crates'].remove(q)
        for c in g['corpses']:
            c['age'] += dt
        if p['dead']:
            p['dead_t'] += dt
        elif p['hp'] <= 0:
            p['dead'] = True
            self.fx.explode(p['x'], p['y'], 0.9)
            self.audio.play('boom_s')
            self.shake = 10
            if g['phase'] == 'play':
                g['phase'], g['fail'], g['pt'] = 'result', True, -0.6
                self.banner('¡SOLDADO CAÍDO!', 'La misión fracasó', (255, 80, 70), 3.0)
        if g['mode'] == 'invasion' and city['hp'] <= 0 and not city['dead']:
            city['dead'] = True
            for _ in range(8):
                self.fx.explode(W / 2 + random.uniform(-80, 80), H / 2 + random.uniform(-60, 60), 1.3, True)
            self.audio.play('boom_l')
            self.shake = 20
            if g['phase'] == 'play':
                g['phase'], g['fail'], g['pt'] = 'result', True, 0.0
            self.banner('¡ANTENA DESTRUIDA!' if g['antenna'] is not None else '¡CIUDAD CAPTURADA!', city['name'], (255, 70, 60), 3.0)
        self.fx.update(dt)
        if g['phase'] == 'play' and not g['queue'] and not g['enemies']:
            g['phase'], g['pt'] = 'result', 0.0
            bonus = 300
            if g['mode'] == 'invasion' and city['hp'] >= g['city0'] - 0.01:
                bonus += 400
            self.add_score(bonus)
            self.audio.play('win', .7)
            if g['mode'] == 'landing':
                self.banner('¡ISLA ASEGURADA!', 'Instalando antena...  Bonus +%d' % bonus, (120, 255, 160), 3.2)
            else:
                self.banner('¡ANTENA DEFENDIDA!' if g['antenna'] is not None else '¡ISLA ASEGURADA!', 'Bajas enemigas: %d   Bonus +%d' % (g['kills'], bonus), (120, 255, 160), 2.8)
        if g['phase'] == 'result':
            g['pt'] += dt
            if not g['fail']:
                g['ant_t'] += dt
            if g['pt'] > (3.6 if g['mode'] == 'landing' and not g['fail'] else 2.8):
                self.end_ground()

    def end_ground(self):
        g = self.g
        city = g['city']
        if g['mode'] == 'landing':
            i = g['island_idx']
            if g['fail']:
                self.hull = max(0.0, self.hull - 25)
                self.ammo = max(0, self.ammo - 5)
                left = MAX_LANDING_ATTEMPTS - self.landing_attempts[i]
                self.toast('Desembarco fallido: -25 casco, -5 munición  (intentos: %d)' % left, (255, 140, 90))
                if self.hull <= 0:
                    return self.game_over('Tu barco se hundió')
            elif i in self.antennas and not self.antennas[i]:
                self.antennas[i] = True
                n = sum(self.antennas.values())
                self.toast('¡ANTENA INSTALADA en %s!' % self.isl_name(i), (120, 255, 160))
                self.banner('ANTENA OPERATIVA', '%d/%d antenas  |  El jefe de esta oleada exige %d' % (n, len(self.antennas), self.antennas_needed()),
                            (120, 220, 255), 3.4)
        elif g['antenna'] is not None:
            if g['fail']:
                self.antennas[g['antenna']] = False
                self.toast('Perdiste la antena de %s: hay que volver a instalarla' % self.isl_name(g['antenna']), (255, 120, 100))
            else:
                self.toast('Antena a salvo', (120, 255, 160))
            self.warned = False
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        else:
            if g['fail'] and not city['dead']:
                city['hp'] = max(0.0, city['hp'] - 30)
                if city['hp'] <= 0:
                    city['dead'] = True
            self.warned = False
            self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
            if all(c['dead'] for c in self.cities):
                return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---------------------------------------------------------- ASALTO AL PUERTO ENEMIGO (vista lateral, estilo Metal Slug)
    PT_GR = 640          # y del suelo del muelle
    PT_LEN = 6400        # largo del nivel

    def nearest_port(self):
        x, y, r, _s = ENEMY_PORT
        if self.port_done or self.port_tries >= 2:
            return None
        return ENEMY_PORT if dist(self.sx, self.sy, x, y) < r * 1.3 + 190 else None

    def start_port(self):
        if self.port_tries >= 2:
            self.toast('Sin intentos de asalto en esta oleada', (255, 140, 90))
            return
        self.port_tries += 1
        rnd = random.Random(self.wave * 977 + self.port_tries * 13)
        L, GR, w = self.PT_LEN, self.PT_GR, self.wave
        plats = []
        x = 700
        while x < L - 1800:
            hh = rnd.choice((1, 1, 2))
            plats.append(dict(x=x, w=rnd.choice((150, 150, 225)), top=GR - 64 * hh, h=64 * hh, ci=rnd.randrange(5)))
            x += rnd.randint(520, 780)
        ex = w // 2
        groups = []

        def grp(xt, spec, lock=False):
            groups.append(dict(x=xt, spec=spec, lock=lock, done=False, lx=0.0))
        grp(500, [('rifle', 'R'), ('rifle', 'R'), ('rifle', 'S')] + [('rifle', 'R')] * ex)
        grp(1450, [('rifle', 'R'), ('knife', 'R'), ('rifle', 'L'), ('shield', 'R')] + [('knife', 'R')] * ex)
        grp(2350, [('gren', 'R'), ('rifle', 'R'), ('rifle', 'S'), ('rifle', 'S'), ('knife', 'L')] + [('shield', 'R')] * (1 + ex // 2))
        grp(3250, [('knife', 'R'), ('flame', 'R'), ('gren', 'R'), ('rifle', 'L'), ('sniper', 'P')] + [('flame', 'R')] * (ex // 2) + [('rifle', 'R')] * ex, True)
        grp(4200, [('shield', 'R'), ('rifle', 'S'), ('rifle', 'S'), ('gren', 'R'), ('gren', 'L'), ('sniper', 'P'), ('flame', 'R')] + [('knife', 'L')] * ex, True)
        grp(L - 1500, [('tank', 'R')], True)
        self.pt = dict(
            plats=plats, groups=groups, cam=0.0, lock=None, t=0.0, phase='play', pt=0.0, fail=False, kills=0,
            p=dict(x=120.0, y=float(GR), vx=0.0, vy=0.0, ground=True, hp=PLAYER_HP, face=1, cd=0.0, gren=6, hmg=0.0, inv=0.0,
                   ph=0.0, crouch=False, dead=False, gcd=0.0, flash=0.0, thr=0.0, dead_t=0.0, dust=0.0),
            enemies=[], bul=[], ebul=[], nades=[], items=[], go_t=0.0, boss=None, hurt=0.0, score0=self.score,
            cas=[], corpses=[], wrecks=[], decor=[], puddles=[], barrels=[], pows=[], mort=[], freeze=0.0, taken=0, pow_n=0, rank=None)
        drnd = random.Random(self.wave * 31 + 5)
        dec = self.pt['decor']
        for lx in range(300, L, 640):
            dec.append(dict(kind='lamp', x=float(lx + drnd.randint(-60, 60))))
        for _ in range(46):
            kind = drnd.choice(('crates', 'bollard', 'sandbags', 'fence', 'fence'))
            dec.append(dict(kind=kind, x=float(drnd.randint(200, L - 200))))
        dec.sort(key=lambda d: {'fence': 0, 'lamp': 1}.get(d['kind'], 2))
        self.pt['puddles'] = [(float(drnd.randint(100, L - 100)), drnd.randint(70, 140)) for _ in range(26)]
        self.pt['barrels'] = [dict(x=float(bx), y=float(GR), hp=2, fuse=-1.0) for bx in sorted(drnd.sample(range(900, L - 1700, 60), 10))]
        for bx_, kind_ in zip((1250, 2900, 4500), ('hmg', 'gren', 'med')):
            self.pt['pows'].append(dict(x=float(bx_), state='tied', t=0.0, item=kind_))
        self.pt_art_init()
        for xi, kind in ((1000, 'med'), (1900, 'gren'), (2750, 'hmg'), (3700, 'med'), (4600, 'gren'), (5100, 'med')):
            self.pt['items'].append(dict(x=float(xi), y=float(GR - 30), kind=kind, t=0.0))
        for xt in (2650, 3900, 4800):
            self.pt['enemies'].append(self.pt_enemy('turret', xt, GR, -1))
        self.fx = Particles()
        self.aim = [W / 2, 300.0]
        self.go('port')
        self.banner('¡ASALTO AL PUERTO ENEMIGO!', 'A/D mover | W/ESPACIO saltar | S agacharse | Clic: disparar | G/clic der.: granada',
                    (255, 120, 90), 4.4)

    def pt_enemy(self, kind, x, y, face):
        hp = {'rifle': 3, 'knife': 2, 'gren': 3, 'sniper': 4, 'shield': 6, 'flame': 5, 'turret': 12, 'tank': 70 + 24 * self.wave}[kind]
        if kind in ('rifle', 'knife', 'gren', 'shield', 'flame'):
            hp += self.wave // 3
        return dict(kind=kind, x=float(x), y=float(y), vx=0.0, vy=0.0, hp=float(hp), max=float(hp), face=face, cd=random.uniform(0.6, 1.8),
                    burst=0, bcd=0.0, tele=0.0, ph=random.uniform(0, 6), hit=0.0, ground=True, plat=None, state='walk',
                    st=0.0, atk=0, mcd=0.0, ph0=random.uniform(0, 6), kneel=random.random() < 0.4, thr=0.0, slash=0.0, flash=0.0,
                    moving=False, recoil=0.0, fire=0.0, fcd=0.0, para=False, stag=0.0)

    def pt_spawn_group(self, g):
        pt = self.pt
        cam = pt['cam']
        for kind, side in g['spec']:
            if kind == 'tank':
                e = self.pt_enemy('tank', cam + W + 200, self.PT_GR, -1)
                e['state'] = 'enter'
                pt['boss'] = e
                pt['enemies'].append(e)
                self.audio.play('alarm')
                self.banner('¡TANQUE DE PUERTO!', 'Saltá sus proyectiles y no pares de disparar', (255, 90, 70), 3.4)
                continue
            if kind == 'sniper':
                ahead = [pl for pl in pt['plats'] if cam + 200 < pl['x'] < cam + W - 100] or pt['plats'][:1]
                pl = random.choice(ahead)
                e = self.pt_enemy('sniper', pl['x'] + pl['w'] / 2, pl['top'], -1)
                e['plat'] = pl
            elif side == 'S':
                e = self.pt_enemy(kind, cam + random.uniform(160, W - 160), -70.0, -1)
                e['para'] = True
            else:
                sx = cam + W + 40 + random.uniform(0, 160) if side == 'R' else cam - 40 - random.uniform(0, 120)
                e = self.pt_enemy(kind, sx, self.PT_GR, -1 if side == 'R' else 1)
            g.setdefault('ids', []).append(e)
            pt['enemies'].append(e)

    def pt_jump(self):
        p = self.pt['p']
        if p['ground'] and not p['dead'] and self.pt['phase'] == 'play':
            p['vy'] = -760.0
            p['ground'] = False
            self.audio.play('blip', .5)

    def pt_throw(self):
        pt = self.pt
        p = pt['p']
        if p['dead'] or p['gren'] <= 0 or p['gcd'] > 0 or pt['phase'] != 'play':
            return
        p['gren'] -= 1
        p['gcd'] = 0.5
        p['thr'] = 0.32
        sx = p['x'] - pt['cam']
        a = math.atan2(self.aim[1] - (p['y'] - 50), self.aim[0] - sx)
        sp = clamp(dist(sx, p['y'] - 50, self.aim[0], self.aim[1]) * 1.45, 260, 640)
        pt['nades'].append(dict(x=p['x'], y=p['y'] - 56, vx=math.cos(a) * sp, vy=math.sin(a) * sp - 120, t=0.0, own='p'))
        self.audio.play('blip', .8)

    def pt_hurt(self, dmg):
        pt = self.pt
        p = pt['p']
        if p['dead'] or p['inv'] > 0 or pt['phase'] != 'play':
            return
        p['hp'] -= dmg
        pt['taken'] += dmg
        p['inv'] = 0.55
        pt['hurt'] = 0.4
        self.shake = max(self.shake, 4 + dmg * 0.3)
        self.audio.play('hit', .5)
        self.pop('-%d' % dmg, p['x'] - pt['cam'], p['y'] - 80, (255, 110, 100))

    def pt_land(self, o, dt):
        """Gravedad y suelo/plataformas (de un solo sentido) para jugador y enemigos."""
        pt = self.pt
        prev = o['y']
        o['vy'] += 1900 * dt
        o['y'] += o['vy'] * dt
        o['ground'] = False
        if o['y'] >= self.PT_GR:
            o['y'], o['vy'], o['ground'] = float(self.PT_GR), 0.0, True
            return
        if o['vy'] >= 0:
            for pl in pt['plats']:
                if pl['x'] - 8 < o['x'] < pl['x'] + pl['w'] + 8 and prev <= pl['top'] + 6 and o['y'] >= pl['top']:
                    o['y'], o['vy'], o['ground'] = float(pl['top']), 0.0, True
                    return

    def pt_kill(self, e, blast=False):
        pt = self.pt
        if e not in pt['enemies']:
            return
        pt['enemies'].remove(e)
        pt['kills'] += 1
        big = e['kind'] in ('tank', 'turret')
        pts = {'rifle': 100, 'knife': 100, 'gren': 150, 'sniper': 200, 'shield': 150, 'flame': 200, 'turret': 250, 'tank': 2000}[e['kind']]
        if e['kind'] == 'tank':
            pt['wrecks'].append(dict(kind='tank', x=e['x'], y=e['y']))
            pt['freeze'] = 0.9
        elif e['kind'] == 'turret':
            pt['wrecks'].append(dict(kind='turret', x=e['x'], y=e['y']))
        else:
            c = dict(kind=e['kind'], x=e['x'], y=e['y'], face=e['face'], t=0.0, vx=-e['face'] * random.uniform(60, 150), air=False, vy=0.0, spin=0.0)
            if blast or e['kind'] == 'flame':
                c.update(air=True, vy=-random.uniform(380, 520), vx=(1 if e['x'] > pt['p']['x'] else -1) * random.uniform(120, 280), spin=random.uniform(-560, 560))
            pt['corpses'].append(c)
        if not blast or e['kind'] != 'tank':
            self.fx.explode(e['x'], e['y'] - (50 if e['kind'] == 'tank' else 24), 2.0 if e['kind'] == 'tank' else (1.1 if big else (0.7 if blast else 0.45)), big or blast)
        self.audio.play('boom_s', .6 if not big else .9)
        self.add_score(pts)
        self.pop('+%d' % pts, e['x'] - pt['cam'], e['y'] - 78, (255, 232, 150))
        if e['kind'] in ('rifle', 'gren', 'knife', 'shield', 'flame') and random.random() < 0.22:
            pt['items'].append(dict(x=e['x'], y=e['y'] - 30, kind=random.choice(('med', 'gren', 'gren')), t=0.0))
        if e['kind'] == 'flame':
            self.pt_blast(e['x'], e['y'] - 30, 80, 4, 14, 'b')
        if e['kind'] == 'tank':
            pt['boss'] = None
            self.shake = 22
            for _ in range(6):
                self.fx.explode(e['x'] + random.uniform(-110, 110), e['y'] - random.uniform(10, 90), 1.4, True)

    def pt_hit_enemy(self, e, dmg, blast=False):
        e['hp'] -= dmg
        e['hit'] = 0.1
        e['stag'] = 0.1
        if e['kind'] not in ('tank', 'turret') and not blast:
            e['x'] += (1 if e['x'] > self.pt['p']['x'] else -1) * 3
        if e['hp'] <= 0:
            self.pt_kill(e, blast)

    def pt_blast(self, x, y, R, dmg_e, dmg_p, own='p'):
        """Explosión: daña a enemigos (si no es de ellos), al jugador y enciende barriles cercanos."""
        pt = self.pt
        p = pt['p']
        self.fx.explode(x, y, R / 95.0, True)
        self.audio.play('boom_s', .8)
        self.shake = max(self.shake, 7)
        if own != 'm':
            for e in pt['enemies'][:]:
                d = dist(x, y, e['x'], e['y'] - 28) - (60 if e['kind'] == 'tank' else 0)
                if d < R and (own != 'e'):
                    self.pt_hit_enemy(e, dmg_e * (1.3 if e['kind'] == 'tank' else 1.0) * (1 - 0.35 * max(0.0, d) / R), True)
        d = dist(x, y, p['x'], p['y'] - 28)
        if not p['dead'] and d < R * (0.75 if own == 'p' else 1.0):
            self.pt_hurt(int(dmg_p * (1 - 0.5 * d / R)))
        for b in pt['barrels']:
            if b['fuse'] < 0 and dist(x, y, b['x'], b['y'] - 20) < R * 0.95:
                b['fuse'] = 0.14

    def pt_box(self, e):
        w, h = {'tank': (280, 140), 'turret': (62, 60), 'sniper': (28, 60), 'shield': (40, 64), 'flame': (34, 64)}.get(e['kind'], (28, 64))
        return e['x'] - w / 2, e['y'] - h, w, h

    def pt_ebullet(self, x, y, ang, sp, dmg, life=1.6):
        a = math.radians(ang)
        self.pt['ebul'].append(dict(x=x, y=y, vx=math.cos(a) * sp, vy=math.sin(a) * sp, dmg=dmg, life=life, big=dmg >= 20))

    def pt_casing(self, x, y, face):
        self.pt['cas'].append(dict(x=x, y=y, vx=-face * random.uniform(40, 120), vy=-random.uniform(140, 240), rot=random.uniform(0, 6), vr=random.uniform(-14, 14), t=0.0))

    def pt_ai(self, e, dt):
        pt = self.pt
        p = pt['p']
        alive = not p['dead']
        cam = pt['cam']
        k = e['kind']
        e['cd'] -= dt
        e['hit'] = max(0.0, e['hit'] - dt)
        e['flash'] = max(0.0, e['flash'] - dt)
        e['slash'] = max(0.0, e['slash'] - dt)
        e['recoil'] = max(0.0, e['recoil'] - 70 * dt)
        dx = p['x'] - e['x']
        ad = abs(dx)
        if alive and k != 'tank':
            e['face'] = 1 if dx > 0 else -1
        # fuera de la pantalla actúan poco (solo caminan hacia el jugador)
        onscreen = cam - 60 < e['x'] < cam + W + 60
        py = p['y'] - 30
        if e['para']:
            e['y'] += 150 * dt
            e['x'] += math.sin(pt['t'] * 1.7 + e['ph0']) * 22 * dt
            fl_ = self.pt_floor(e['x'], e['y'] - 4)
            if e['y'] >= fl_:
                e['y'], e['vy'], e['para'] = float(fl_), 0.0, False
                for _ in range(6):
                    self.fx.add('smoke', e['x'] + random.uniform(-16, 16), e['y'] - 3, random.uniform(-60, 60), random.uniform(-26, -6), 0.6, 4, 12, (190, 170, 150), drag=2)
            return
        e['stag'] = max(0.0, e['stag'] - dt)
        if k in ('rifle', 'knife', 'gren', 'shield', 'flame'):
            self.pt_land(e, dt)
            if k == 'knife':
                sp = 215.0
            elif k == 'shield':
                sp = 78.0 if ad > 70 else 0.0
            elif k == 'flame':
                sp = 88.0 if ad > 215 else (-60.0 if ad < 130 else 0.0)
                if e['fire'] > 0:
                    sp = 0.0
            elif k == 'rifle':
                sp = 95.0 if ad > 440 else (-70.0 if ad < 230 else 0.0)
            else:
                sp = 80.0 if ad > 560 else (-90.0 if ad < 330 else 0.0)
            if e['thr'] > 0:
                sp = 0.0
            if not onscreen:
                sp = 110.0
            e['x'] += sp * (1 if dx > 0 else -1) * dt
            if pt['lock'] is not None:
                e['x'] = clamp(e['x'], cam - 30, cam + W - 40)
            e['moving'] = sp != 0
            e['ph'] += abs(sp) * dt / 12.7
            if k == 'knife':
                if ad < 46 and abs(p['y'] - e['y']) < 50 and e['cd'] <= 0 and alive:
                    e['cd'] = 0.9
                    e['slash'] = 0.3
                    self.pt_hurt(14)
            elif k == 'shield':
                if ad < 84 and abs(p['y'] - e['y']) < 60 and e['cd'] <= 0 and alive:
                    e['cd'] = 1.1
                    e['slash'] = 0.3
                    self.pt_hurt(16)
                    p['vx'] += 0
                    self.audio.play('hit', .4)
            elif k == 'flame':
                if onscreen and alive:
                    if e['fire'] > 0:
                        e['fire'] -= dt
                        e['fcd'] -= dt
                        gy = e['y'] - 44
                        ang = math.atan2((p['y'] - 40) - gy, dx)
                        ang = clamp(ang, -0.6, 0.6) if dx > 0 else (ang if abs(ang) > 2.54 else math.copysign(2.54, ang))
                        for _ in range(3):
                            sp_ = random.uniform(200, 330)
                            a_ = ang + random.uniform(-0.12, 0.12)
                            self.fx.add('glow', e['x'] + math.cos(ang) * 44, gy + math.sin(ang) * 44, math.cos(a_) * sp_, math.sin(a_) * sp_ - 20, 0.42, 9, 26,
                                        random.choice(((255, 170, 60), (255, 120, 40), (255, 220, 120))), drag=1.4)
                        if random.random() < 0.3:
                            self.fx.add('smoke', e['x'] + e['face'] * 150, gy - 20, e['face'] * 40, -50, 0.9, 8, 22, (40, 36, 36))
                        if e['fcd'] <= 0:
                            e['fcd'] = 0.2
                            if ad < 240 and abs((p['y'] - 36) - gy) < 46:
                                self.pt_hurt(4)
                        e['flash'] = 0.06
                        if e['fire'] <= 0:
                            e['cd'] = random.uniform(1.8, 2.6)
                    elif e['cd'] <= 0 and ad < 280:
                        e['fire'] = 1.4
                        self.audio.play('launch', .3)
            elif onscreen and alive:
                if e['thr'] > 0:
                    e['thr'] -= dt
                    if e['thr'] <= 0:
                        T = clamp(ad / 380.0, 0.8, 1.5)
                        vx = dx / T
                        vy = (py - (e['y'] - 56) - 0.5 * 900 * T * T) / T
                        pt['nades'].append(dict(x=e['x'], y=e['y'] - 56, vx=vx, vy=vy, t=0.0, own='e'))
                elif e['burst'] > 0:
                    e['bcd'] -= dt
                    if e['bcd'] <= 0:
                        e['burst'] -= 1
                        e['bcd'] = 0.13
                        gy = e['y'] - (28 if (e['kneel'] and not e['moving']) else 44)
                        ang = math.degrees(math.atan2(py - gy, dx)) + random.uniform(-6, 6)
                        self.pt_ebullet(e['x'] + 30 * e['face'], gy, ang, 560, 7)
                        e['flash'] = 0.06
                        self.pt_casing(e['x'] + 14 * e['face'], gy, e['face'])
                        self.audio.play('mg', .15)
                elif e['cd'] <= 0 and k == 'rifle' and ad < 700:
                    e['cd'] = random.uniform(1.3, 2.3)
                    e['burst'], e['bcd'] = random.choice((2, 3)), 0.0
                elif e['cd'] <= 0 and k == 'gren' and 250 < ad < 760:
                    e['cd'] = random.uniform(2.6, 3.6)
                    e['thr'] = 0.45
        elif k == 'sniper':
            if onscreen and alive:
                if e['tele'] > 0:
                    e['tele'] -= dt
                    if e['tele'] <= 0:
                        ang = math.degrees(math.atan2(py - (e['y'] - 34), dx))
                        self.pt_ebullet(e['x'] + 40 * e['face'], e['y'] - 34, ang, 1100, 20, 2.0)
                        e['flash'] = 0.08
                        self.pt_casing(e['x'] + 14 * e['face'], e['y'] - 34, e['face'])
                        self.audio.play('cannon', .35)
                        e['cd'] = random.uniform(2.2, 3.0)
                elif e['cd'] <= 0:
                    e['tele'] = 0.9
        elif k == 'turret':
            if onscreen and alive and ad < 760:
                if e['burst'] > 0:
                    e['bcd'] -= dt
                    if e['bcd'] <= 0:
                        e['burst'] -= 1
                        e['bcd'] = 0.11
                        ang = math.degrees(math.atan2(py - (e['y'] - 50), dx)) + random.uniform(-5, 5)
                        self.pt_ebullet(e['x'] + (62 if dx > 0 else -62), e['y'] - 50, ang, 520, 7)
                        self.audio.play('mg', .15)
                elif e['cd'] <= 0:
                    e['cd'] = random.uniform(2.2, 3.2)
                    e['burst'], e['bcd'] = 6, 0.0
        elif k == 'tank':
            self.pt_ai_tank(e, dt)

    def pt_ai_tank(self, e, dt):
        pt = self.pt
        p = pt['p']
        alive = not p['dead']
        cam = pt['cam']
        home = (pt['lock'] if pt['lock'] is not None else cam) + W - 260
        e['st'] += dt
        ratio = e['hp'] / e['max']
        e['flash'] = max(0.0, e['flash'] - dt)
        if e['state'] == 'enter':
            e['x'] -= 140 * dt
            if e['x'] <= home:
                e['state'] = 'fight'
                e['st'] = 0.0
                e['cd'] = 1.4
        elif e['state'] == 'fight':
            e['mcd'] = e['mcd'] - dt if e['mcd'] > 0 else (e['mcd'] if ratio >= 0.6 else 0.0)
            if ratio < 0.6 and e['mcd'] <= 0 and e['burst'] == 0 and e['tele'] <= 0 and alive:
                e['mcd'] = 6.5
                for off in (-190, 0, 190):
                    pt['mort'].append(dict(x=p['x'] + off + random.uniform(-40, 40), t=0.0))
                self.pop('¡MORTEROS!', W / 2, 300, (255, 160, 60))
                self.audio.play('ping', .6)
            e['x'] = home + math.sin(e['st'] * 0.7) * 80
            e['x'] = max(e['x'], (pt['lock'] or cam) + 520)
            if e['burst'] > 0:
                e['bcd'] -= dt
                if e['bcd'] <= 0:
                    e['burst'] -= 1
                    e['bcd'] = 0.1
                    ang = math.degrees(math.atan2(p['y'] - 36 - (e['y'] - 74), p['x'] - (e['x'] - 152))) + random.uniform(-7, 7)
                    self.pt_ebullet(e['x'] - 152, e['y'] - 74, ang, 600, 7)
                    self.audio.play('mg', .2)
            if e['tele'] > 0:
                e['tele'] -= dt
                if e['tele'] <= 0:
                    self.pt_ebullet(e['x'] - 226, e['y'] - 111, 180, 640, 24, 2.4)
                    self.audio.play('cannon', .6)
                    e['recoil'] = 20.0
                    e['flash'] = 0.1
                    self.fx.explode(e['x'] - 230, e['y'] - 111, 0.6)
                    self.shake = max(self.shake, 6)
            elif e['burst'] == 0 and e['cd'] <= 0 and alive:
                e['atk'] += 1
                e['cd'] = random.uniform(1.8, 2.6) * (0.75 if ratio < 0.5 else 1.0)
                if ratio < 0.5 and e['atk'] % 3 == 0:
                    e['state'] = 'charge'
                    e['st'] = 0.0
                    self.pop('¡EMBISTE!', W / 2, 300, (255, 90, 70))
                elif e['atk'] % 2 == 0:
                    e['burst'], e['bcd'] = 9, 0.0
                else:
                    e['tele'] = 0.75
        elif e['state'] == 'charge':
            e['x'] -= 330 * dt
            if abs(p['x'] - e['x']) < 150 and p['y'] > e['y'] - 100 and alive:
                self.pt_hurt(28)
            if e['x'] < cam + 120 or e['st'] > 2.6:
                e['state'] = 'return'
        elif e['state'] == 'return':
            e['x'] += 190 * dt
            if e['x'] >= home:
                e['state'] = 'fight'
                e['st'] = 0.0

    def upd_port(self, dt):
        pt = self.pt
        p = pt['p']
        if pt['freeze'] > 0:
            pt['freeze'] -= dt
            dt *= 0.25
        keys = pygame.key.get_pressed()
        pt['t'] += dt
        pt['hurt'] = max(0.0, pt['hurt'] - dt)
        L = self.PT_LEN
        alive = not p['dead']
        p['inv'] = max(0.0, p['inv'] - dt)
        p['cd'] = max(0.0, p['cd'] - dt)
        p['gcd'] = max(0.0, p['gcd'] - dt)
        p['flash'] = max(0.0, p['flash'] - dt)
        p['hmg'] = max(0.0, p['hmg'] - dt)
        p['thr'] = max(0.0, p['thr'] - dt)
        pt['go_t'] = max(0.0, pt['go_t'] - dt)
        cam = pt['cam']
        if alive and pt['phase'] == 'play':
            mv = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            p['crouch'] = bool(keys[pygame.K_s] or keys[pygame.K_DOWN]) and p['ground']
            sp = 0.0 if p['crouch'] else 235.0
            p['vx'] = mv * sp
            p['x'] += p['vx'] * dt
            if mv:
                p['ph'] += abs(p['vx']) * dt / 12.7
            sx = p['x'] - cam
            p['face'] = 1 if self.aim[0] >= sx else -1
            if pygame.mouse.get_pressed()[0] or keys[pygame.K_j]:
                self.pt_shoot()
        was_air = not p['ground']
        vy0 = p['vy']
        self.pt_land(p, dt)
        if was_air and p['ground'] and vy0 > 380 and alive:
            for _ in range(7):
                self.fx.add('smoke', p['x'] + random.uniform(-14, 14), p['y'] - 3, random.uniform(-70, 70), random.uniform(-30, -6), 0.6, 5, 15, (190, 170, 150), drag=2)
        if alive and p['ground'] and abs(p['vx']) > 1:
            p['dust'] -= dt
            if p['dust'] <= 0:
                p['dust'] = 0.13
                self.fx.add('smoke', p['x'] - p['face'] * 14, p['y'] - 3, random.uniform(-20, 20) - p['vx'] * 0.2, random.uniform(-26, -8), 0.5, 3, 11, (190, 170, 150), drag=2)
        if p['dead']:
            p['dead_t'] += dt
        for c in pt['cas'][:]:
            c['t'] += dt
            c['vy'] += 1400 * dt
            c['x'] += c['vx'] * dt
            c['y'] += c['vy'] * dt
            c['rot'] += c['vr'] * dt
            if c['y'] > self.PT_GR - 2:
                c['y'] = self.PT_GR - 2
                c['vy'] *= -0.35
                c['vx'] *= 0.5
            if c['t'] > 1.6:
                pt['cas'].remove(c)
        for c in pt['corpses'][:]:
            if c['air']:
                c['vy'] += 1500 * dt
                c['y'] += c['vy'] * dt
                c['x'] += c['vx'] * dt
                c['spin'] *= 0.995
                fl_ = self.pt_floor(c['x'], c['y'] - 10)
                if c['y'] >= fl_ and c['vy'] > 0:
                    c['y'], c['air'], c['t'] = float(fl_), False, 0.0
                    self.fx.add('smoke', c['x'], c['y'] - 4, 0, -20, 0.6, 5, 16, (190, 170, 150), drag=2)
                continue
            c['t'] += dt
            c['x'] += c['vx'] * dt
            c['vx'] *= max(0.0, 1 - 5 * dt)
            if c['t'] > 4.8:
                pt['corpses'].remove(c)
        for w_ in pt['wrecks']:
            if random.random() < dt * 9:
                self.fx.add('smoke', w_['x'] + random.uniform(-40, 40) * (3 if w_['kind'] == 'tank' else 0.7), w_['y'] - (110 if w_['kind'] == 'tank' else 50),
                            random.uniform(-8, 8), -45, 2.2, 8, 30, (34, 34, 38))
        lo = cam + 24
        hi = (pt['lock'] + W - 30) if pt['lock'] is not None else min(L - 30, cam + W - 30)
        p['x'] = clamp(p['x'], lo, hi)
        # bloqueos de pantalla (estilo Metal Slug) y cámara
        for g in pt['groups']:
            if g['done']:
                continue
            if g['lock']:
                if pt['lock'] is None and p['x'] > g['x'] - 300:
                    pt['lock'] = pt['cam']
                    g['active'] = True
                    g['done'] = True
                    self.pt_spawn_group(g)
                    self.audio.play('ping', .6)
            elif pt['cam'] + W > g['x']:
                g['done'] = True
                self.pt_spawn_group(g)
        if pt['lock'] is not None:
            pending = [e for g in pt['groups'] if g.get('active') for e in g.get('ids', []) if e in pt['enemies']]
            if not pending and not any(e['kind'] == 'tank' for e in pt['enemies']):
                pt['lock'] = None
                pt['go_t'] = 4.0
        target = clamp(p['x'] - W * 0.38, 0, L - W)
        if pt['lock'] is not None:
            target = min(target, pt['lock'])
        if target > cam:
            pt['cam'] = cam + (target - cam) * min(1, dt * 6)
        pt['cam'] = clamp(pt['cam'], 0, L - W)
        # enemigos
        for e in pt['enemies'][:]:
            self.pt_ai(e, dt)
            if e['kind'] in ('knife', 'rifle', 'gren') and e['x'] < pt['cam'] - 700:
                pt['enemies'].remove(e)
        # balas del jugador
        for b in pt['bul'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            hit = None
            for e in pt['enemies']:
                x0, y0, w, h = self.pt_box(e)
                if x0 <= b['x'] <= x0 + w and y0 <= b['y'] <= y0 + h:
                    hit = e
                    break
            brl = None
            for br in pt['barrels']:
                if abs(b['x'] - br['x']) < 17 and br['y'] - 44 <= b['y'] <= br['y'] and br['fuse'] < 0:
                    brl = br
                    break
            if brl is not None:
                pt['bul'].remove(b)
                brl['hp'] -= 1
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-120, 0), 0.25, col=(255, 230, 150), drag=2, grav=300)
                if brl['hp'] <= 0:
                    brl['fuse'] = 0.1
            elif hit is not None and hit['kind'] == 'shield' and b['vx'] * hit['face'] < 0 and abs(b['vy']) < 0.8 * abs(b['vx']) and b['y'] > hit['y'] - 58:
                pt['bul'].remove(b)
                for _ in range(3):
                    self.fx.add('spark', b['x'], b['y'], hit['face'] * random.uniform(60, 200), random.uniform(-160, 40), 0.3, col=(200, 230, 255), drag=2, grav=500)
                self.audio.play('ping', .25)
            elif hit is not None:
                pt['bul'].remove(b)
                self.fx.add('spark', b['x'], b['y'], random.uniform(-90, 90), random.uniform(-120, 0), 0.25, col=(255, 230, 150), drag=2, grav=300)
                self.pt_hit_enemy(hit, b['dmg'])
            elif b['life'] <= 0 or b['y'] > self.PT_GR + 20:
                pt['bul'].remove(b)
        # balas enemigas
        pbox = (p['x'] - 14, p['y'] - (42 if p['crouch'] else 64), 28, 42 if p['crouch'] else 64)
        for b in pt['ebul'][:]:
            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['life'] -= dt
            if alive and pbox[0] <= b['x'] <= pbox[0] + pbox[2] and pbox[1] <= b['y'] <= pbox[1] + pbox[3]:
                pt['ebul'].remove(b)
                self.pt_hurt(int(b['dmg']))
            elif any(abs(b['x'] - br['x']) < 17 and br['y'] - 44 <= b['y'] <= br['y'] and br['fuse'] < 0 for br in pt['barrels']):
                pt['ebul'].remove(b)
                for br in pt['barrels']:
                    if abs(b['x'] - br['x']) < 17 and br['fuse'] < 0:
                        br['fuse'] = 0.1
            elif b['life'] <= 0 or b['y'] > self.PT_GR + 10 or b['x'] < pt['cam'] - 100 or b['x'] > pt['cam'] + W + 100:
                pt['ebul'].remove(b)
        # granadas
        for n in pt['nades'][:]:
            n['t'] += dt
            n['vy'] += 900 * dt
            n['x'] += n['vx'] * dt
            n['y'] += n['vy'] * dt
            boom = n['y'] >= self.PT_GR - 4 or n['t'] > 2.2
            if not boom:
                for pl in pt['plats']:
                    if pl['x'] < n['x'] < pl['x'] + pl['w'] and pl['top'] - 6 < n['y'] < pl['top'] + 10 and n['vy'] > 0:
                        boom = True
                if n['own'] == 'p':
                    for e in pt['enemies']:
                        x0, y0, w, h = self.pt_box(e)
                        if x0 <= n['x'] <= x0 + w and y0 <= n['y'] <= y0 + h:
                            boom = True
            if boom:
                pt['nades'].remove(n)
                if n['own'] == 'p':
                    self.pt_blast(n['x'], min(n['y'], self.PT_GR - 4), 95, 6, 10, 'p')
                else:
                    self.pt_blast(n['x'], min(n['y'], self.PT_GR - 4), 95, 0, 28, 'e')
        # barriles explosivos
        for br in pt['barrels'][:]:
            if br['fuse'] >= 0:
                br['fuse'] -= dt
                if br['fuse'] < 0:
                    pt['barrels'].remove(br)
                    self.pt_blast(br['x'], br['y'] - 22, 110, 7, 26, 'b')
            elif br['hp'] <= 1 and random.random() < dt * 8:
                self.fx.add('smoke', br['x'] + random.uniform(-6, 6), br['y'] - 44, 0, -50, 0.9, 4, 12, (40, 40, 44))
        # prisioneros
        for pw in pt['pows']:
            pw['t'] += dt
            if pw['state'] == 'tied' and alive and abs(p['x'] - pw['x']) < 46 and abs(p['y'] - self.PT_GR) < 80:
                pw['state'] = 'free'
                pw['t'] = 0.0
                pt['pow_n'] += 1
                self.add_score(500)
                self.audio.play('win', .6)
                self.pop('¡GRACIAS! +500', pw['x'] - pt['cam'], self.PT_GR - 110, (140, 255, 170))
                pt['items'].append(dict(x=pw['x'] + 30, y=float(self.PT_GR - 30), kind=pw['item'], t=0.0))
            elif pw['state'] == 'free':
                pw['x'] += 190 * dt
        # morteros del jefe
        for m in pt['mort'][:]:
            m['t'] += dt
            if m['t'] >= 1.45:
                pt['mort'].remove(m)
                self.pt_blast(m['x'], self.PT_GR - 4, 90, 0, 24, 'm')
        # objetos
        for it in pt['items'][:]:
            it['t'] += dt
            if alive and abs(p['x'] - it['x']) < 36 and abs((p['y'] - 30) - it['y']) < 60:
                pt['items'].remove(it)
                self.audio.play('pickup', .8)
                if it['kind'] == 'med':
                    p['hp'] = min(PLAYER_HP, p['hp'] + 40)
                    self.pop('+40 VIDA', p['x'] - pt['cam'], p['y'] - 80, (120, 255, 160))
                elif it['kind'] == 'gren':
                    p['gren'] = min(9, p['gren'] + 4)
                    self.pop('+4 GRANADAS', p['x'] - pt['cam'], p['y'] - 80, (255, 220, 120))
                else:
                    p['hmg'] = 14.0
                    self.pop('¡AMETRALLADORA!', p['x'] - pt['cam'], p['y'] - 80, (255, 160, 90))
        self.fx.update(dt)
        # fin de la misión
        if not p['dead'] and p['hp'] <= 0:
            p['dead'] = True
            self.audio.play('boom_s')
            self.shake = 12
            if pt['phase'] == 'play':
                pt['phase'], pt['fail'], pt['pt'] = 'result', True, -0.6
                self.banner('¡SOLDADO CAÍDO!', 'El asalto fracasó', (255, 80, 70), 3.0)
        boss_dead = pt['boss'] is None and pt['groups'][-1]['done'] and not any(e['kind'] == 'tank' for e in pt['enemies'])
        if pt['phase'] == 'play' and boss_dead:
            pt['phase'], pt['pt'] = 'result', 0.0
            hpf = p['hp'] / PLAYER_HP
            pts_ = (hpf >= 0.6) + (pt['t'] < 150) + (pt['pow_n'] >= 3) + (pt['taken'] < 80)
            rank = 'S' if pts_ >= 4 else ('A' if pts_ == 3 else ('B' if pts_ == 2 else 'C'))
            pt['rank'] = rank
            bonus = 1500 + 300 * self.wave + {'S': 1500, 'A': 800, 'B': 300, 'C': 0}[rank]
            pt['bonus'] = bonus
            self.add_score(bonus)
            self.audio.play('win', .8)
            self.banner('¡PUERTO TOMADO!', 'Rango %s  |  Bonus +%d' % (rank, bonus), (120, 255, 160), 3.4)
        if pt['phase'] == 'result':
            pt['pt'] += dt
            if pt['pt'] > (3.4 if pt['fail'] else 6.0):
                self.end_port()

    def pt_shoot(self):
        pt = self.pt
        p = pt['p']
        if p['cd'] > 0 or p['dead']:
            return
        hmg = p['hmg'] > 0
        p['cd'] = 0.075 if hmg else 0.115
        p['flash'] = 0.05
        sx = p['x'] - pt['cam']
        oy = p['y'] - (28 if p['crouch'] else 46)
        a = math.atan2(self.aim[1] - oy, self.aim[0] - sx)
        a += math.radians(random.uniform(-3.5, 3.5) if hmg else random.uniform(-1.2, 1.2))
        pt['bul'].append(dict(x=p['x'] + math.cos(a) * 34, y=oy + math.sin(a) * 34, vx=math.cos(a) * 980, vy=math.sin(a) * 980,
                              dmg=1.0, life=0.9))
        self.audio.play('mg', .3)
        if random.random() < 0.7:
            self.pt_casing(p['x'] + 10 * p['face'], oy, p['face'])

    def end_port(self):
        pt = self.pt
        if pt['fail']:
            self.hull = max(0.0, self.hull - 20)
            self.ammo = max(0, self.ammo - 4)
            left = 2 - self.port_tries
            self.toast('Asalto fallido: -20 casco, -4 munición (intentos: %d)' % left, (255, 140, 90))
            if self.hull <= 0:
                return self.game_over('Tu barco se hundió')
        else:
            self.port_done = True
            self.hull = min(100, self.hull + 30)
            self.fuel = 100.0
            self.ammo = 40
            for en in self.enemies:
                if en.get('is_boss'):
                    en['hp'] = max(1.0, en['hp'] * 0.75)
            self.toast('Puerto enemigo tomado: reabastecimiento total y el jefe pierde 25% de casco', (120, 255, 160))
        self.go('map')

    # ---- dibujo del asalto
    def pt_art_init(self):
        if hasattr(self, 'pt_art'):
            return
        self.pt_art = build_pt_art()
        self.pt_tk = build_pt_tank()
        self.pt_bk = build_pt_bunker()
        self.pt_ct = build_pt_containers()
        self.pt_dc = build_pt_decor()
        self.pt_bg = build_pt_bg(W, self.PT_GR, self.PT_LEN)
        self.pt_cache = {}
        g = self.pt_bk['gun']
        pad = pygame.Surface((g.get_width() * 2, g.get_height() * 2), pygame.SRCALPHA)
        pad.blit(g, (pad.get_width() // 2 - 8, pad.get_height() // 2 - 12))
        self.pt_bk['gunpad'] = pad
        sh = pygame.Surface((56, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), (0, 0, 56, 14))
        pygame.draw.ellipse(sh, (0, 0, 0, 50), (8, 3, 40, 8))
        self.pt_shadow = sh
        vg = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(60):
            a = int(60 * (1 - i / 60) ** 2)
            pygame.draw.rect(vg, (10, 6, 24, a), (i * 3, i * 2, W - i * 6, H - i * 4), 6)
        self.pt_vig = vg

    def pt_floor(self, x, y):
        """Altura de la superficie bajo (x, y): suelo o la plataforma más cercana por debajo."""
        best = self.PT_GR
        for pl in self.pt['plats']:
            if pl['x'] - 8 < x < pl['x'] + pl['w'] + 8 and y - 6 <= pl['top'] < best:
                best = pl['top']
        return best

    def pt_char(self, cv, kind, sx, fy, face, pose, fi, aim=None, arm='gun', hit=0.0, alpha=255, shadow=True, flash=False, rot_deg=0.0):
        """Dibuja un soldado pre-renderizado (cuerpo + brazos/arma rotados). aim=(dx, dy) hacia donde apunta."""
        art = self.pt_art
        frames = art['body'][kind][pose]
        fi %= len(frames)
        spr, shx, shy = frames[fi]
        if shadow:
            fl_ = self.pt_floor(sx + self.pt['cam'], fy)
            if fl_ - fy < 200:
                sh_ = self.pt_shadow
                if fl_ - fy > 4:
                    k_ = max(0.45, 1 - (fl_ - fy) / 260)
                    sh_ = pygame.transform.smoothscale(sh_, (int(56 * k_), int(14 * k_)))
                cv.blit(sh_, (sx - sh_.get_width() // 2, fl_ - 8 * sh_.get_height() // 14))
        right = face > 0
        key = (kind, pose, fi, right)
        img = self.pt_cache.get(key)
        if img is None:
            img = spr if right else pygame.transform.flip(spr, True, False)
            self.pt_cache[key] = img
        if hit > 0 or alpha < 255:
            img = img.copy()
            if hit > 0:
                img.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            if alpha < 255:
                img.set_alpha(alpha)
        if rot_deg:
            th = math.radians(rot_deg)
            rim = pygame.transform.rotate(img, rot_deg)
            cx_, cy_ = sx - 14 * math.sin(th), fy - 30 - 14 * math.cos(th)
            cv.blit(rim, (cx_ - rim.get_width() // 2, cy_ - rim.get_height() // 2))
            return None
        cv.blit(img, (sx - PT_AX, fy - PT_AY))
        if not arm or arm not in art['arm'][kind] or pose == 'die':
            return None
        layer = art['arm'][kind][arm]
        if aim is not None and arm in ('gun', 'knife'):
            dx, dy = aim
            rot = -math.degrees(math.atan2(dy, dx)) if right else math.degrees(math.atan2(dy, -dx))
            rot = clamp(rot, -80, 80)
        else:
            rot = 0.0
        rk = (kind, arm, right, int(rot / 3))
        rimg = self.pt_cache.get(rk)
        if rimg is None:
            base = layer if right else pygame.transform.flip(layer, True, False)
            rimg = pygame.transform.rotate(base, rot)
            self.pt_cache[rk] = rimg
        if hit > 0 or alpha < 255:
            rimg = rimg.copy()
            if hit > 0:
                rimg.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            if alpha < 255:
                rimg.set_alpha(alpha)
        px = sx + (shx if right else -shx)
        py = fy - shy
        cv.blit(rimg, (px - rimg.get_width() // 2, py - rimg.get_height() // 2))
        if flash and arm == 'gun':
            ln = 92 if kind == 'sniper' else 72
            ang = math.radians(rot if right else -rot)
            mx = px + (math.cos(ang) * ln if right else -math.cos(ang) * ln)
            my = py - math.sin(ang) * ln * (1 if right else -1) * (1 if right else 1)
            my = py - math.sin(math.radians(rot)) * ln
            self.pt_flash(cv, mx, my, -rot if right else rot, right)
        return px, py

    def pt_flash(self, cv, x, y, ang, right):
        a = math.radians(ang)
        d = 1 if right else -1
        glow(cv, x, y, 26, (255, 200, 110), 0.8)
        pts = []
        for i in range(10):
            r = random.uniform(16, 26) if i % 2 == 0 else 5
            t = -1.2 + 2.4 * i / 9
            pts.append((x + d * math.cos(a + t * d) * r, y + math.sin(a + t * d) * r))
        pygame.draw.polygon(cv, (255, 236, 160), pts)
        pygame.draw.circle(cv, (255, 255, 235), (int(x), int(y)), 5)

    def pt_tank_img(self, e):
        """Compone el tanque (mirando a la izquierda): orugas animadas, torreta y cañón con retroceso."""
        T = self.pt_tk
        hull = T['hull'][int((e['x'] % 14) / 14 * 8) % 8]
        comp = pygame.Surface((520, 190), pygame.SRCALPHA)
        ox = 70
        comp.blit(hull, (ox, 0))
        comp.blit(T['turret'], (ox, 0))
        px, py = T['pivot']
        comp.blit(T['barrel'], (ox + px - 6 - int(e.get('recoil', 0)), py - 30))
        img = pygame.transform.flip(comp, True, False)
        if e['hit'] > 0:
            img.fill((44, 44, 44, 0), special_flags=pygame.BLEND_RGB_ADD)
        return img

    def draw_port(self, cv):
        pt = self.pt
        p = pt['p']
        cam = pt['cam']
        bg = self.pt_bg
        GR = self.PT_GR
        t = self.t
        cv.blit(bg['sky'], (0, 0))
        cv.blit(bg['sea'], (0, 410))
        for i in range(10):
            yy = 430 + i * 20
            xx = (i * 191 + t * (9 + i * 2)) % (W + 160) - 80
            pygame.draw.line(cv, (255, 206, 160), (xx, yy), (xx + 40 + i * 5, yy), 2)
        cv.blit(bg['far'], (0, 330), area=pygame.Rect(int(cam * 0.18), 0, W, 230))
        cv.blit(bg['mid'], (0, GR - 330), area=pygame.Rect(int(cam * 0.5), 0, W, 330))
        # muelle
        for y in range(GR, H, 4):
            f = (y - GR) / (H - GR)
            pygame.draw.rect(cv, (int(lerp(112, 66, f)), int(lerp(108, 62, f)), int(lerp(122, 78, f))), (0, y, W, 4))
        pygame.draw.rect(cv, (150, 146, 156), (0, GR, W, 6))
        pygame.draw.rect(cv, (60, 58, 70), (0, GR + 6, W, 3))
        for x in range(-int(cam) % 130, W, 130):
            pygame.draw.line(cv, (62, 60, 72), (x, GR + 10), (x - 22, H), 2)
        for y in (GR + 56, GR + 112):
            pygame.draw.line(cv, (62, 60, 72), (0, y), (W, y), 1)
        for x in range(-int(cam) % 260, W, 260):
            pygame.draw.rect(cv, (240, 200, 50), (x, GR + 3, 70, 3))
        for px_, pw_ in pt['puddles']:
            xx = px_ - cam
            if -80 < xx < W:
                pygame.draw.ellipse(cv, (190, 130, 120), (xx, GR + 26, pw_, 12))
                pygame.draw.ellipse(cv, (240, 170, 130), (xx + pw_ * 0.2, GR + 29, pw_ * 0.4, 4))
        # decorado de fondo
        D = self.pt_dc
        for d in pt['decor']:
            sx = d['x'] - cam
            if not (-200 < sx < W + 200):
                continue
            spr = D[d['kind']]
            if d['kind'] == 'lamp':
                cv.blit(spr, (sx - 30, GR - 186))
            elif d['kind'] == 'fence':
                cv.blit(spr, (sx, GR - 56))
            else:
                cv.blit(spr, (sx - spr.get_width() // 2, GR - spr.get_height() + 4))
        # plataformas (contenedores)
        for pl in pt['plats']:
            x0 = pl['x'] - cam
            if x0 > W or x0 + pl['w'] < 0:
                continue
            spr = self.pt_ct[(pl['ci'], pl['w'])]
            for row in range(pl['h'] // 64):
                y0 = pl['top'] + row * 64
                cv.blit(spr, (x0, y0))
                if row:
                    sh_ = pygame.Surface((pl['w'], 64), pygame.SRCALPHA)
                    sh_.fill((0, 0, 20, 40))
                    cv.blit(sh_, (x0, y0))
            pygame.draw.rect(cv, (0, 0, 0), (x0, GR - 3, pl['w'], 3))
        # objetos
        for it in pt['items']:
            sx = it['x'] - cam
            if not (-40 < sx < W + 40):
                continue
            bob = math.sin(it['t'] * 5) * 3
            col = {'med': (236, 240, 236), 'gren': (96, 120, 70), 'hmg': (250, 170, 70)}[it['kind']]
            glow(cv, sx, it['y'] + bob, 32, (120, 255, 160) if it['kind'] == 'med' else (255, 210, 80), 0.5)
            pygame.draw.rect(cv, (24, 26, 30), (sx - 15, it['y'] - 15 + bob, 30, 30), border_radius=5)
            pygame.draw.rect(cv, col, (sx - 13, it['y'] - 13 + bob, 26, 26), border_radius=4)
            if it['kind'] == 'med':
                pygame.draw.rect(cv, (220, 50, 50), (sx - 8, it['y'] - 3 + bob, 16, 6))
                pygame.draw.rect(cv, (220, 50, 50), (sx - 3, it['y'] - 8 + bob, 6, 16))
            elif it['kind'] == 'gren':
                pygame.draw.circle(cv, (50, 70, 40), (sx, int(it['y'] + 2 + bob)), 8)
                pygame.draw.circle(cv, (150, 180, 110), (sx - 2, int(it['y'] + bob)), 2)
            else:
                self.text(cv, 'H', self.f_m, (60, 30, 10), sx, it['y'] - 12 + bob, 'c', shadow=False)
        # restos
        for w_ in pt['wrecks']:
            sx = w_['x'] - cam
            if not (-300 < sx < W + 300):
                continue
            if w_['kind'] == 'tank':
                img = self.pt_tank_img(dict(x=w_['x'], hit=0.0, recoil=0))
                img.fill((70, 64, 62, 255), special_flags=pygame.BLEND_RGBA_MULT)
                cv.blit(img, (sx - 260, w_['y'] - 176))
                for k in range(4):
                    ph = (t * 1.6 + k * 0.27) % 1
                    glow(cv, sx - 60 + k * 44, w_['y'] - 110 - ph * 40, 26 - 10 * ph, (255, 150, 60), 1 - ph)
            else:
                spr = self.pt_bk['base'].copy()
                spr.fill((60, 56, 54, 255), special_flags=pygame.BLEND_RGBA_MULT)
                cv.blit(spr, (sx - 55, w_['y'] - 66))
                ph = (t * 1.4 + w_['x']) % 1
                glow(cv, sx, w_['y'] - 50 - ph * 30, 18, (255, 140, 60), 1 - ph)
        for c in pt['corpses']:
            sx = c['x'] - cam
            if not (-100 < sx < W + 100):
                continue
            if c['air']:
                c['rot'] = c.get('rot', 0.0) + c['spin'] * 0.016
                self.pt_char(cv, c['kind'], int(sx), int(c['y']), c['face'], 'die', 1, None, None, 0.0, 255, False, False, c['rot'])
                continue
            fi = min(5, int(c['t'] * 12))
            al = 255 if c['t'] < 3.5 else int(255 * clamp(1 - (c['t'] - 3.5) / 1.2, 0, 1))
            self.pt_char(cv, c['kind'], int(sx), int(c['y']), c['face'], 'die', fi, None, None, 0.0, al)
        # barriles explosivos
        brl = D['barrel']
        for br in pt['barrels']:
            sx = br['x'] - cam
            if -40 < sx < W + 40:
                cv.blit(brl, (sx - brl.get_width() // 2, br['y'] - brl.get_height() + 4))
                pygame.draw.polygon(cv, (250, 210, 40), [(sx, br['y'] - 54), (sx - 9, br['y'] - 40), (sx + 9, br['y'] - 40)])
                self.text(cv, '!', self.f_s, (40, 30, 10), sx, br['y'] - 52, 'c', shadow=False)
                if br['fuse'] >= 0 and int(t * 30) % 2 == 0:
                    glow(cv, sx, br['y'] - 22, 34, (255, 230, 150), 0.9)
        # prisioneros de guerra
        for pw in pt['pows']:
            sx = pw['x'] - cam
            if not (-60 < sx < W + 60):
                continue
            if pw['state'] == 'tied':
                self.pt_char(cv, 'pow', int(sx), self.PT_GR, -1, 'crouch', 0, None, None)
                pygame.draw.line(cv, (140, 100, 56), (sx - 8, self.PT_GR - 36), (sx + 8, self.PT_GR - 30), 3)
                pygame.draw.line(cv, (140, 100, 56), (sx - 8, self.PT_GR - 30), (sx + 8, self.PT_GR - 36), 3)
                if int(t * 2.5) % 2 == 0:
                    self.text(cv, '¡AYUDA!', self.f_s, (255, 240, 150), sx, self.PT_GR - 82, 'c')
            elif pw['state'] == 'free' and pw['t'] < 2.4:
                self.pt_char(cv, 'pow', int(sx), self.PT_GR, 1, 'run', int(pw['t'] * 14), None, None, 0.0, int(255 * clamp(1 - (pw['t'] - 1.6) / 0.8, 0, 1)))
        # morteros
        for m in pt['mort']:
            sx = m['x'] - cam
            k_ = m['t'] / 1.45
            rr = 78 - 28 * k_
            pygame.draw.ellipse(cv, (255, 70, 60), (sx - rr, GR - 8, rr * 2, 16), 3)
            pygame.draw.ellipse(cv, (255, 70, 60, 90), (sx - 6, GR - 3, 12, 6))
            if m['t'] > 1.1:
                y = lerp(-70, GR, (m['t'] - 1.1) / 0.35)
                pygame.draw.line(cv, (255, 220, 160), (sx, y - 80), (sx, y), 5)
                pygame.draw.circle(cv, (255, 250, 220), (int(sx), int(y)), 7)
                glow(cv, sx, y, 24, (255, 170, 80), 0.8)
            else:
                self.text(cv, 'v', self.f_m, (255, 90, 70), sx, GR - 70 - (int(t * 6) % 2) * 6, 'c')
        # enemigos
        pcx = p['x'] - cam
        for e in pt['enemies']:
            sx = e['x'] - cam
            if not (-340 < sx < W + 340):
                continue
            k = e['kind']
            fy = int(e['y'])
            if k == 'tank':
                img = self.pt_tank_img(e)
                cv.blit(self.pt_shadow, (sx - 150, fy - 8)) if False else None
                cv.blit(img, (sx - 260, fy - 176))
                if e['tele'] > 0:
                    glow(cv, sx - 224, fy - 111, 30 + 12 * math.sin(e['st'] * 30), (255, 160, 70))
                if e['flash'] > 0:
                    self.pt_flash(cv, sx - 224, fy - 111, 0, False)
                if e['burst'] > 0 and e['bcd'] > 0.05:
                    self.pt_flash(cv, sx - 152, fy - 74, 0, False)
                if e['hp'] < e['max'] * 0.5 and random.random() < 0.3:
                    self.fx.add('smoke', e['x'] - 20 + random.uniform(-30, 30), fy - 140, random.uniform(-10, 10), -40, 1.6, 8, 26, (40, 40, 44))
                continue
            if k == 'turret':
                bk = self.pt_bk
                cv.blit(bk['base'], (sx - 55, fy - 66))
                right = p['x'] > e['x']
                dx, dy = p['x'] - e['x'], (p['y'] - 40) - (fy - 50)
                ang = clamp(-math.degrees(math.atan2(dy, abs(dx))), -60, 60)
                pad = bk['gunpad'] if right else pygame.transform.flip(bk['gunpad'], True, False)
                rimg = pygame.transform.rotate(pad, ang if right else -ang)
                gx, gy = sx + (6 if right else -6), fy - 50
                if e['hit'] > 0:
                    rimg = rimg.copy()
                    rimg.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
                cv.blit(rimg, (gx - rimg.get_width() // 2, gy - rimg.get_height() // 2))
                if e['burst'] > 0 and e['bcd'] > 0.05:
                    a_ = math.radians(ang)
                    self.pt_flash(cv, gx + (66 * math.cos(a_)) * (1 if right else -1), gy - 66 * math.sin(a_), ang if right else -ang, right)
                continue
            moving = e.get('moving', False)
            if e['stag'] > 0:
                sx -= e['face'] * 2
            if e['para']:
                self.pt_char(cv, 'rifle', int(sx), fy, e['face'], 'fall', 0, None, None, 0.0, 255, False)
                top = fy - 168
                pygame.draw.arc(cv, (236, 236, 226), (sx - 54, top, 108, 70), 0, 3.14159, 40)
                pygame.draw.polygon(cv, (226, 90, 70), [(sx - 54, top + 35), (sx - 18, top + 4), (sx - 6, top + 4), (sx - 22, top + 38)])
                pygame.draw.polygon(cv, (236, 236, 226), [(sx - 22, top + 38), (sx - 6, top + 4), (sx + 6, top + 4), (sx + 22, top + 38)])
                pygame.draw.polygon(cv, (226, 90, 70), [(sx + 22, top + 38), (sx + 6, top + 4), (sx + 18, top + 4), (sx + 54, top + 35)])
                pygame.draw.arc(cv, (40, 36, 40), (sx - 54, top, 108, 70), 0, 3.14159, 3)
                for ox in (-52, -20, 20, 52):
                    pygame.draw.line(cv, (40, 36, 40), (sx + ox, top + 36), (sx, fy - 54), 1)
                continue
            if k == 'shield':
                pose = 'run' if moving else 'idle'
                fi = int(e['ph']) if moving else int(t * 3 + e['ph0'])
                self.pt_char(cv, 'shield', int(sx + (e['face'] * 6 if e['slash'] > 0.15 else 0)), fy, e['face'], pose, fi, None, 'shield', e['hit'])
                if e['hp'] < e['max']:
                    pygame.draw.rect(cv, (8, 12, 24), (sx - 15, fy - 86, 30, 5))
                    pygame.draw.rect(cv, (240, 80, 70), (sx - 14, fy - 85, int(28 * e['hp'] / e['max']), 3))
                continue
            if k == 'knife':
                pose = 'run' if moving else 'idle'
                arm = 'knife'
                aim = (e['face'] * 1.0, -0.15 + (0.5 - e['slash'] / 0.3) * 1.6 if e['slash'] > 0 else 0.1)
            elif k == 'gren':
                pose = 'run' if moving else 'idle'
                arm = 'gun'
                aim = (p['x'] - e['x'], (p['y'] - 40) - (fy - 40))
                if e['thr'] > 0:
                    arm = 'wind' if e['thr'] > 0.14 else 'rel'
            elif k == 'sniper':
                pose = 'crouch'
                arm = 'gun'
                aim = (p['x'] - e['x'], (p['y'] - 40) - (fy - 30))
            else:
                pose = 'run' if moving else ('crouch' if e['kneel'] else 'idle')
                arm = 'gun'
                aim = (p['x'] - e['x'], (p['y'] - 40) - (fy - (28 if e['kneel'] and not moving else 40)))
            if k == 'flame':
                pose = 'run' if moving else 'idle'
                arm = 'gun'
                aim = (p['x'] - e['x'], (p['y'] - 40) - (fy - 44))
            fi = int(e['ph']) if pose == 'run' else int(t * 3 + e['ph0'])
            self.pt_char(cv, k, int(sx), fy, e['face'], pose, fi, aim, arm, e['hit'], 255, True, e['flash'] > 0 and k != 'flame')
            if k == 'sniper' and e['tele'] > 0:
                ay = e['y'] - 34
                pygame.draw.line(cv, (255, 40, 40), (sx, ay), (p['x'] - cam, p['y'] - 36), 1)
                self.text(cv, '!', self.f_m, (255, 70, 60), sx, fy - 92, 'c')
            if e['hp'] < e['max']:
                pygame.draw.rect(cv, (8, 12, 24), (sx - 15, fy - 84, 30, 5))
                pygame.draw.rect(cv, (240, 80, 70), (sx - 14, fy - 83, int(28 * e['hp'] / e['max']), 3))
        # jugador
        if not p['dead']:
            if not (p['inv'] > 0 and int(t * 20) % 2 == 0):
                oy = 28 if p['crouch'] else 48
                aim = (self.aim[0] - pcx, self.aim[1] - (p['y'] - oy))
                if not p['ground']:
                    pose, fi = ('jump' if p['vy'] < 0 else 'fall'), 0
                elif p['crouch']:
                    pose, fi = 'crouch', 0
                elif abs(p['vx']) > 1:
                    pose, fi = 'run', int(p['ph'])
                else:
                    pose, fi = 'idle', int(t * 3)
                arm = 'gun'
                if p['thr'] > 0:
                    arm = 'wind' if p['thr'] > 0.16 else 'rel'
                self.pt_char(cv, 'player', int(pcx - (p['face'] * 2 if p['flash'] > 0 else 0)), int(p['y']), p['face'], pose, fi, aim, arm, 0.0, 255, True, p['flash'] > 0)
        else:
            fi = min(5, int(p['dead_t'] * 12))
            self.pt_char(cv, 'player', int(pcx), int(p['y']), p['face'], 'die', fi, None, None)
        # proyectiles y casquillos
        for c in pt['cas']:
            sx, sy = c['x'] - cam, c['y']
            pygame.draw.line(cv, (240, 200, 90), (sx, sy), (sx + math.cos(c['rot']) * 4, sy + math.sin(c['rot']) * 4), 2)
        for b in pt['bul']:
            sx, sy = b['x'] - cam, b['y']
            ex, ey = sx - b['vx'] * 0.03, sy - b['vy'] * 0.03
            pygame.draw.line(cv, (255, 200, 90), (sx, sy), (ex, ey), 5)
            pygame.draw.line(cv, (255, 250, 210), (sx, sy), (sx - b['vx'] * 0.018, sy - b['vy'] * 0.018), 2)
        for b in pt['ebul']:
            sx, sy = b['x'] - cam, b['y']
            col = (255, 90, 70) if not b['big'] else (255, 170, 60)
            r = 4 if not b['big'] else 9
            glow(cv, sx, sy, 14 if not b['big'] else 26, col, 0.7)
            pygame.draw.line(cv, col, (sx, sy), (sx - b['vx'] * 0.03, sy - b['vy'] * 0.03), 3 if not b['big'] else 8)
            pygame.draw.circle(cv, col, (int(sx), int(sy)), r)
            pygame.draw.circle(cv, (255, 240, 220), (int(sx), int(sy)), max(1, r - 2))
        for n in pt['nades']:
            sx, sy = n['x'] - cam, n['y']
            pygame.draw.circle(cv, (24, 30, 20), (int(sx), int(sy)), 7)
            pygame.draw.circle(cv, (70, 100, 56), (int(sx), int(sy)), 6)
            pygame.draw.circle(cv, (250, 220, 90) if n['own'] == 'p' else (255, 90, 70), (int(sx), int(sy)), 7, 2)
            pygame.draw.circle(cv, (160, 190, 120), (int(sx - 2), int(sy - 2)), 2)
        self.fx.draw(cv, cam, 0)
        # luces de las farolas
        for d in pt['decor']:
            if d['kind'] == 'lamp':
                sx = d['x'] - cam
                if -120 < sx < W + 120:
                    glow(cv, sx - 18, GR - 170, 70, (255, 214, 140), 0.55)
        cv.blit(self.pt_vig, (0, 0))
        # HUD
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   BAJAS %d' % (self.wave, WIN_WAVE, pt['kills']), self.f_s, (160, 200, 240), 26, 42)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        self.text(cv, 'PUERTO ENEMIGO', self.f_m, (255, 140, 110), W // 2, 16, 'c')
        boss = pt['boss']
        if boss is not None:
            self.bar(cv, W // 2 - 210, 44, 420, 26, boss['hp'] / boss['max'], (240, 80, 70), 'TANQUE DE PUERTO')
        else:
            self.bar(cv, W // 2 - 210, 44, 420, 26, clamp(p['x'] / (self.PT_LEN - 1500), 0, 1), (255, 190, 90), 'AVANCE')
        self.panel(cv, (14, H - 126, 330, 112), 190)
        hp = clamp(p['hp'] / PLAYER_HP, 0, 1)
        self.bar(cv, 26, H - 114, 306, 22, hp, (80, 230, 110) if hp > 0.5 else ((255, 200, 70) if hp > 0.25 else (240, 80, 70)), 'SOLDADO %d' % max(0, p['hp']))
        self.text(cv, 'GRANADAS %d' % p['gren'], self.f_s, (255, 230, 150), 26, H - 84)
        if p['hmg'] > 0:
            self.bar(cv, 26, H - 56, 306, 16, p['hmg'] / 14.0, (255, 160, 80), 'AMETRALLADORA %.1f' % p['hmg'])
        if pt['go_t'] > 0 and pt['phase'] == 'play' and int(t * 3) % 2 == 0:
            self.text(cv, 'ADELANTE  >>>', self.f_l, (255, 230, 120), W - 180, 330, 'c')
        if pt['hurt'] > 0:
            hs = pygame.Surface((W, H), pygame.SRCALPHA)
            hs.fill((255, 30, 30, int(110 * pt['hurt'] / 0.4)))
            cv.blit(hs, (0, 0))
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (20, 20, 24), (ax, ay), 15, 4)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 14, 2)
        for dx_, dy_ in ((-22, 0), (22, 0), (0, -22), (0, 22)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx_ // 2, ay + dy_ // 2), (ax + dx_, ay + dy_), 2)
        if pt['phase'] == 'result' and pt['fail']:
            self.dim(cv, 60)
        elif pt['phase'] == 'result' and pt['rank'] and pt['pt'] > 0.8:
            k_ = clamp((pt['pt'] - 0.8) / 0.5, 0, 1)
            self.panel(cv, (W // 2 - 220, 230, 440, 250), int(215 * k_))
            self.text(cv, 'MISIÓN CUMPLIDA', self.f_l, (120, 255, 160), W // 2, 240, 'c', alpha=int(255 * k_))
            rows = [('Bajas', '%d' % pt['kills']), ('Prisioneros', '%d / 3' % pt['pow_n']), ('Tiempo', '%d s' % pt['t']),
                    ('Daño recibido', '%d' % pt['taken']), ('Bonus', '+%d' % pt.get('bonus', 0))]
            for i, (a_, b_) in enumerate(rows):
                self.text(cv, a_, self.f_m, (200, 215, 235), W // 2 - 190, 292 + i * 30, alpha=int(255 * k_))
                self.text(cv, b_, self.f_m, (255, 240, 170), W // 2 + 190, 292 + i * 30, 'r', alpha=int(255 * k_))
            rc = {'S': (255, 220, 90), 'A': (140, 255, 170), 'B': (150, 200, 255), 'C': (200, 200, 210)}[pt['rank']]
            self.text(cv, 'RANGO  %s' % pt['rank'], self.f_l, rc, W // 2, 440, 'c', alpha=int(255 * k_))

    # ---------------------------------------------------------- COMBATE URBANO CON TANQUES (estilo Battlezone)
    TK_EYE, TK_F, TK_NEAR, TK_A = 2.3, 560.0, 0.5, 125.0
    TK_VP = pygame.Rect(40, 118, 1020, 520)

    def tk_make_world(self, city):
        rnd = random.Random(city['seed'] * 31 + self.wave)
        blds = [dict(x=0.0, z=0.0, hw=15.0, hd=15.0, h=42.0, hall=True, tx=0, uo=0.0)]
        for i in range(-2, 3):
            for j in range(-2, 3):
                if i == 0 and j == 0 or rnd.random() < 0.1:
                    continue
                cx, cz = i * 46.0, j * 46.0
                if rnd.random() < 0.4:
                    for ox, oz in ((-9.5, -9.5), (9.5, 9.5)):
                        blds.append(dict(x=cx + ox + rnd.uniform(-1.5, 1.5), z=cz + oz + rnd.uniform(-1.5, 1.5),
                                         hw=rnd.uniform(5, 7.5), hd=rnd.uniform(5, 7.5), h=rnd.uniform(6, 24), hall=False,
                                         tx=rnd.randrange(6), uo=rnd.random()))
                else:
                    blds.append(dict(x=cx + rnd.uniform(-4, 4), z=cz + rnd.uniform(-4, 4), hw=rnd.uniform(8, 13),
                                     hd=rnd.uniform(8, 13), h=rnd.uniform(8, 30), hall=False, tx=rnd.randrange(6), uo=rnd.random()))
        mount = [rnd.uniform(14, 46) for _ in range(120)]
        for i in range(1, 119):
            mount[i] = (mount[i - 1] + mount[i] + mount[(i + 1) % 120]) / 3
        sky = dict(mount=mount, city=[(rnd.uniform(0, 360), rnd.uniform(1.2, 3.2), rnd.uniform(10, 70)) for _ in range(90)],
                   stars=[(rnd.uniform(0, 360), rnd.uniform(0.04, 0.9), rnd.randint(1, 2)) for _ in range(110)])
        return blds, sky

    def start_tank(self, city):
        w = self.wave
        blds, sky = self.tk_make_world(city)
        n = min(5 + 2 * w, 16)
        n_super = min(w // 2, 4)
        kinds = ['super'] * n_super + ['tank'] * (n - n_super) + ['missile'] * (w // 2 if w >= 3 else 0)
        random.shuffle(kinds)
        queue = sorted([(random.uniform(1.5, 10 + n * 2.2), kd) for kd in kinds], key=lambda q: q[0])
        self.fx = Particles()
        self.k = dict(city=city, blds=blds, sky=sky, t=0.0, tanks=[], missiles=[], shells=[], pshells=[], debris=[], booms=[],
                      cracks=[], queue=queue, total=len(kinds), kills=0, phase='play', pt=0.0, fail=False,
                      city0=city['hp'], hurt=0.0, sweep=0.0, inrange=False, msg_t=0.0, msg='',
                      p=dict(x=0.0, z=-112.0, yaw=0.0, v=0.0, hp=TK_HP, cd=0.0, blocked=0.0, dead=False))
        self.go('tank')
        self.banner('¡INVASIÓN BLINDADA!', 'Defendé %s desde tu tanque | W/S: avanzar | A/D: girar | ESPACIO: cañón' % city['name'],
                    (120, 255, 160), 4.2)

    def tk_free(self, x, z, r):
        for b in self.k['blds']:
            nx, nz = clamp(x, b['x'] - b['hw'], b['x'] + b['hw']), clamp(z, b['z'] - b['hd'], b['z'] + b['hd'])
            if (x - nx) ** 2 + (z - nz) ** 2 < r * r:
                return False
        return abs(x) < self.TK_A - 3 and abs(z) < self.TK_A - 3

    def tk_move(self, x, z, r):
        lim = self.TK_A - 3
        x, z = clamp(x, -lim, lim), clamp(z, -lim, lim)
        blocked = False
        for b in self.k['blds']:
            nx, nz = clamp(x, b['x'] - b['hw'], b['x'] + b['hw']), clamp(z, b['z'] - b['hd'], b['z'] + b['hd'])
            dx, dz = x - nx, z - nz
            d2 = dx * dx + dz * dz
            if d2 < r * r:
                blocked = True
                if d2 > 1e-9:
                    d = math.sqrt(d2)
                    x, z = nx + dx / d * r, nz + dz / d * r
                else:
                    ox, oz = b['hw'] - abs(x - b['x']), b['hd'] - abs(z - b['z'])
                    if ox < oz:
                        x = b['x'] + math.copysign(b['hw'] + r, x - b['x'])
                    else:
                        z = b['z'] + math.copysign(b['hd'] + r, z - b['z'])
        return x, z, blocked

    def tk_los(self, x0, z0, x1, z1):
        dx, dz = x1 - x0, z1 - z0
        for b in self.k['blds']:
            tmin, tmax = 0.0, 1.0
            for o, d, lo, hi in ((x0, dx, b['x'] - b['hw'], b['x'] + b['hw']), (z0, dz, b['z'] - b['hd'], b['z'] + b['hd'])):
                if abs(d) < 1e-9:
                    if o < lo or o > hi:
                        tmax = -1.0
                        break
                else:
                    t1, t2 = (lo - o) / d, (hi - o) / d
                    if t1 > t2:
                        t1, t2 = t2, t1
                    tmin, tmax = max(tmin, t1), min(tmax, t2)
                    if tmin > tmax:
                        break
            if tmin <= tmax:
                return False
        return True

    def tk_say(self, s):
        self.k['msg'], self.k['msg_t'] = s, 1.4

    def tk_fire(self):
        k = self.k
        p = k['p']
        if self.state != 'tank' or p['dead'] or p['cd'] > 0 or k['phase'] != 'play':
            return
        p['cd'] = 0.7
        sx, sz = math.sin(math.radians(p['yaw'])), math.cos(math.radians(p['yaw']))
        k['pshells'].append(dict(x=p['x'] + sx * 3, y=1.9, z=p['z'] + sz * 3, vx=sx * 95, vz=sz * 95, life=1.5))
        self.audio.play('cannon', .8)
        self.shake = max(self.shake, 3)

    def tk_enemy_shell(self, e, ang, tx=None, tz=None):
        k = self.k
        a = math.radians(ang)
        k['shells'].append(dict(x=e['x'] + math.sin(a) * 3.4, y=1.9, z=e['z'] + math.cos(a) * 3.4,
                                vx=math.sin(a) * 38, vz=math.cos(a) * 38, life=2.6))
        d = math.hypot(e['x'] - k['p']['x'], e['z'] - k['p']['z'])
        self.audio.play('launch', clamp(1.0 - d / 120, 0.1, 0.7))

    def tk_hurt(self, dmg):
        k = self.k
        p = k['p']
        if p['dead'] or k['phase'] != 'play':
            return
        p['hp'] -= dmg
        k['hurt'] = 0.7
        self.shake = max(self.shake, 10)
        self.audio.play('hit', .8)
        vp = self.TK_VP
        cx, cy = random.uniform(vp.x + 120, vp.right - 120), random.uniform(vp.y + 80, vp.bottom - 80)
        pts = []
        for _ in range(random.randint(5, 7)):
            a = random.uniform(0, 6.283)
            ln = random.uniform(40, 150)
            seg = [(cx, cy)]
            for s_ in range(1, 5):
                seg.append((cx + math.cos(a + random.uniform(-.25, .25)) * ln * s_ / 4, cy + math.sin(a + random.uniform(-.25, .25)) * ln * s_ / 4))
            pts.append(seg)
        k['cracks'] += pts
        self.tk_say('¡IMPACTO!  ARMADURA %d' % max(0, p['hp']))

    def tk_boom(self, x, z, size, life=1.1, y=1.4):
        self.k['booms'].append(dict(x=x, y=y, z=z, size=size, life=life, age=0.0))

    def tk_debris(self, x, z, n):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            sp = random.uniform(4, 15)
            self.k['debris'].append(dict(x=x, y=random.uniform(0.6, 2.2), z=z, vx=math.cos(a) * sp, vy=random.uniform(5, 16),
                                         vz=math.sin(a) * sp, life=random.uniform(0.9, 1.6)))

    def tk_kill(self, e, kind):
        k = self.k
        if e in k['tanks']:
            k['tanks'].remove(e)
        if e in k['missiles']:
            k['missiles'].remove(e)
        k['kills'] += 1
        pts = {'tank': 300, 'super': 600, 'missile': 150}[kind]
        self.add_score(pts)
        self.pop('+%d' % pts, W // 2, 180, (120, 255, 160))
        self.audio.play('boom_s', .8)
        self.shake = max(self.shake, 6)
        self.tk_debris(e['x'], e['z'], 22)
        self.tk_boom(e['x'], e['z'], 6.5)
        if kind == 'super':
            k['p']['hp'] = min(TK_HP, k['p']['hp'] + 20)
            self.tk_say('REPARACION: +20 ARMADURA')

    def tk_steer(self, e, want, speed, dt, rate):
        chosen = want
        if not self.tk_free(e['x'] + math.sin(math.radians(want)) * 8, e['z'] + math.cos(math.radians(want)) * 8, 3.2):
            for off in (30, 60, 95, 135, 180):
                h = (want + off * e['bias']) % 360
                if self.tk_free(e['x'] + math.sin(math.radians(h)) * 8, e['z'] + math.cos(math.radians(h)) * 8, 3.2):
                    chosen = h
                    break
        diff = angle_diff(e['h'], chosen)
        e['h'] = (e['h'] + clamp(diff, -rate * dt, rate * dt)) % 360
        if abs(diff) < 70:
            a = math.radians(e['h'])
            nx, nz, blk = self.tk_move(e['x'] + math.sin(a) * speed * dt, e['z'] + math.cos(a) * speed * dt, 3.4)
            e['stuck'] = e['stuck'] + dt if blk else max(0.0, e['stuck'] - dt)
            if e['stuck'] > 1.0:
                e['bias'] *= -1
                e['stuck'] = 0.0
            e['x'], e['z'] = nx, nz
            e['tread'] += speed * dt

    def tk_ai(self, e, dt):
        k = self.k
        p = k['p']
        w = self.wave
        alive = not p['dead']
        dx, dz = p['x'] - e['x'], p['z'] - e['z']
        d = math.hypot(dx, dz)
        to_p = math.degrees(math.atan2(dx, dz)) % 360
        to_h = math.degrees(math.atan2(-e['x'], -e['z'])) % 360
        dh = math.hypot(e['x'], e['z'])
        sieging = dh < 40
        los = alive and d < 85 and self.tk_los(e['x'], e['z'], p['x'], p['z'])
        spd = (8.5 if e['kind'] == 'tank' else 12.0) * (1 + 0.03 * w)
        rate = 42 if e['kind'] == 'tank' else 58
        e['cd'] -= dt
        if los:
            if d > 55:
                self.tk_steer(e, to_p, spd, dt, rate)
            elif d < 26:
                self.tk_steer(e, (to_p + 180) % 360, spd * 0.8, dt, rate)
            else:
                self.tk_steer(e, (to_p + 90 * e['sd']) % 360, spd * 0.55, dt, rate)
            e['tur'] = (e['tur'] + clamp(angle_diff(e['tur'], to_p), -95 * dt, 95 * dt)) % 360
            if e['cd'] <= 0 and abs(angle_diff(e['tur'], to_p)) < 4:
                e['cd'] = random.uniform(3.0, 4.6) / (1 + 0.07 * w)
                err = max(1.5, 5.0 - 0.4 * w)
                self.tk_enemy_shell(e, e['tur'] + random.uniform(-err, err))
        elif sieging:
            e['tur'] = (e['tur'] + clamp(angle_diff(e['tur'], to_h), -95 * dt, 95 * dt)) % 360
            k['city']['hp'] = max(0.0, k['city']['hp'] - (0.6 if e['kind'] == 'tank' else 0.9) * dt)
            if e['cd'] <= 0 and abs(angle_diff(e['tur'], to_h)) < 6:
                e['cd'] = random.uniform(2.2, 3.4)
                self.tk_enemy_shell(e, e['tur'])
        else:
            self.tk_steer(e, to_h, spd, dt, rate)
            e['tur'] = (e['tur'] + clamp(angle_diff(e['tur'], e['h']), -95 * dt, 95 * dt)) % 360
        e['sd_t'] -= dt
        if e['sd_t'] <= 0:
            e['sd'] *= -1
            e['sd_t'] = random.uniform(2, 5)

    def upd_tank(self, dt):
        k = self.k
        p = k['p']
        keys = pygame.key.get_pressed()
        k['t'] += dt
        k['hurt'] = max(0.0, k['hurt'] - dt)
        k['msg_t'] = max(0.0, k['msg_t'] - dt)
        k['sweep'] = (k['sweep'] + dt * 0.8) % 1.0
        p['cd'] = max(0.0, p['cd'] - dt)
        if not p['dead']:
            turn = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
            thr = (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0) - (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0)
            p['yaw'] = (p['yaw'] + turn * 68 * dt) % 360
            tgt = 15.0 if thr > 0 else (-8.0 if thr < 0 else 0.0)
            p['v'] += (tgt - p['v']) * min(1.0, dt * 4)
            a = math.radians(p['yaw'])
            nx, nz, blk = self.tk_move(p['x'] + math.sin(a) * p['v'] * dt, p['z'] + math.cos(a) * p['v'] * dt, 2.6)
            p['blocked'] = 0.3 if (blk and thr) else max(0.0, p['blocked'] - dt)
            if blk and thr:
                p['v'] *= 0.5
            p['x'], p['z'] = nx, nz
            self.audio.engine_vol(0.12 + abs(p['v']) / 15 * 0.6 + abs(turn) * 0.1)
            if p['blocked'] > 0:
                self.tk_say('MOVIMIENTO BLOQUEADO POR OBJETO')
        else:
            self.audio.engine_vol(0)
        if k['phase'] == 'play':
            while k['queue'] and k['queue'][0][0] <= k['t'] and len(k['tanks']) + len(k['missiles']) < 6:
                _, kd = k['queue'].pop(0)
                side = random.choice((0, 1, 2, 3))
                u = random.uniform(-100, 100)
                ex, ez = ((u, 118), (u, -118), (118, u), (-118, u))[side]
                if kd == 'missile':
                    k['missiles'].append(dict(x=ex, z=ez, h=0.0, t=0.0, kind='missile'))
                    self.audio.play('alarm', .5)
                    self.tk_say('¡MISIL GUIADO DETECTADO!')
                else:
                    hall = math.degrees(math.atan2(-ex, -ez)) % 360
                    k['tanks'].append(dict(x=ex, z=ez, h=hall, tur=hall, kind=kd, hp=1 if kd == 'tank' else 2, cd=random.uniform(1.5, 3.5),
                                           bias=random.choice((-1, 1)), sd=random.choice((-1, 1)), sd_t=random.uniform(1, 4),
                                           stuck=0.0, tread=0.0))
        for e in k['tanks']:
            self.tk_ai(e, dt)
        for i, a_ in enumerate(k['tanks']):
            for b_ in k['tanks'][i + 1:]:
                d = math.hypot(a_['x'] - b_['x'], a_['z'] - b_['z'])
                if 0 < d < 7.5:
                    push = (7.5 - d) / 2
                    ux, uz = (a_['x'] - b_['x']) / d, (a_['z'] - b_['z']) / d
                    a_['x'], a_['z'] = a_['x'] + ux * push, a_['z'] + uz * push
                    b_['x'], b_['z'] = b_['x'] - ux * push, b_['z'] - uz * push
        for m in k['missiles'][:]:
            m['t'] += dt
            dx, dz = p['x'] - m['x'], p['z'] - m['z']
            want = math.degrees(math.atan2(dx, dz)) + 28 * math.sin(m['t'] * 5)
            m['h'] = (m['h'] + clamp(angle_diff(m['h'], want), -150 * dt, 150 * dt)) % 360
            a = math.radians(m['h'])
            m['x'] += math.sin(a) * 23 * dt
            m['z'] += math.cos(a) * 23 * dt
            if any(abs(m['x'] - b['x']) < b['hw'] and abs(m['z'] - b['z']) < b['hd'] for b in k['blds']):
                k['missiles'].remove(m)
                self.tk_debris(m['x'], m['z'], 12)
                self.tk_boom(m['x'], m['z'], 3.5, 0.9)
                self.audio.play('boom_s', .5)
                continue
            if not p['dead'] and math.hypot(dx, dz) < 3.2:
                k['missiles'].remove(m)
                self.tk_hurt(30)
                self.audio.play('boom_s', .8)
        for s in k['shells'][:]:
            s['x'] += s['vx'] * dt
            s['z'] += s['vz'] * dt
            s['life'] -= dt
            hit_b = any(abs(s['x'] - b['x']) < b['hw'] and abs(s['z'] - b['z']) < b['hd'] for b in k['blds'])
            if s['life'] <= 0 or abs(s['x']) > 140 or abs(s['z']) > 140 or hit_b:
                k['shells'].remove(s)
                if hit_b:
                    self.tk_boom(s['x'], s['z'], 2.2, 0.6)
            elif not p['dead'] and math.hypot(s['x'] - p['x'], s['z'] - p['z']) < 2.9:
                k['shells'].remove(s)
                self.tk_hurt(18)
        for s in k['pshells'][:]:
            s['x'] += s['vx'] * dt
            s['z'] += s['vz'] * dt
            s['life'] -= dt
            gone = s['life'] <= 0 or abs(s['x']) > 140 or abs(s['z']) > 140
            if not gone and any(abs(s['x'] - b['x']) < b['hw'] and abs(s['z'] - b['z']) < b['hd'] for b in k['blds']):
                gone = True
                self.tk_boom(s['x'], s['z'], 2.2, 0.6, s['y'])
                for _ in range(8):
                    a = random.uniform(0, 6.283)
                    k['debris'].append(dict(x=s['x'], y=s['y'], z=s['z'], vx=math.cos(a) * 5, vy=random.uniform(2, 8),
                                            vz=math.sin(a) * 5, life=0.6))
            if not gone:
                for e in k['tanks'] + k['missiles']:
                    if math.hypot(s['x'] - e['x'], s['z'] - e['z']) < (4.4 if e['kind'] != 'missile' else 2.4):
                        gone = True
                        if e['kind'] == 'missile':
                            self.tk_kill(e, 'missile')
                        else:
                            e['hp'] -= 1
                            if e['hp'] <= 0:
                                self.tk_kill(e, e['kind'])
                            else:
                                self.audio.play('hit', .6)
                                self.tk_say('IMPACTO EN SUPERTANQUE')
                        break
            if gone and s in k['pshells']:
                k['pshells'].remove(s)
        for bm in k['booms'][:]:
            bm['age'] += dt
            if bm['age'] >= bm['life']:
                k['booms'].remove(bm)
        for d_ in k['debris'][:]:
            d_['life'] -= dt
            d_['x'] += d_['vx'] * dt
            d_['z'] += d_['vz'] * dt
            d_['vy'] -= 24 * dt
            d_['y'] = max(0.0, d_['y'] + d_['vy'] * dt)
            if d_['life'] <= 0:
                k['debris'].remove(d_)
        if len(k['debris']) > 260:
            del k['debris'][:60]
        near = [e for e in k['tanks'] if not p['dead'] and math.hypot(e['x'] - p['x'], e['z'] - p['z']) < 75]
        aligned = False
        for e in near:
            if abs(angle_diff(p['yaw'], math.degrees(math.atan2(e['x'] - p['x'], e['z'] - p['z'])))) < 10:
                aligned = True
        if aligned and not k['inrange']:
            self.audio.play('ping', .5)
        k['inrange'] = aligned
        city = k['city']
        if not p['dead'] and p['hp'] <= 0:
            p['dead'] = True
            self.audio.play('boom_l')
            self.shake = 18
            if k['phase'] == 'play':
                k['phase'], k['fail'], k['pt'] = 'result', True, -0.8
                self.banner('¡TANQUE DESTRUIDO!', 'La ciudad queda sin defensa', (255, 80, 70), 3.0)
        if city['hp'] <= 0 and not city['dead']:
            city['dead'] = True
            self.audio.play('boom_l')
            self.shake = 22
            if k['phase'] == 'play':
                k['phase'], k['fail'], k['pt'] = 'result', True, 0.0
            self.banner('¡CIUDAD CAPTURADA!', city['name'], (255, 70, 60), 3.0)
        if k['phase'] == 'play' and not k['queue'] and not k['tanks'] and not k['missiles']:
            k['phase'], k['pt'] = 'result', 0.0
            bonus = 400 + (400 if city['hp'] >= k['city0'] - 0.01 else 0)
            self.add_score(bonus)
            self.audio.play('win', .7)
            self.banner('¡CIUDAD DEFENDIDA!', 'Bajas: %d   Bonus +%d' % (k['kills'], bonus), (120, 255, 160), 3.0)
        if k['phase'] == 'result':
            k['pt'] += dt
            if k['pt'] > 3.0:
                self.end_tank()

    def end_tank(self):
        k = self.k
        city = k['city']
        if k['fail'] and not city['dead']:
            city['hp'] = max(0.0, city['hp'] - 30)
            if city['hp'] <= 0:
                city['dead'] = True
        self.warned = False
        self.strike_t = max(32.0, random.uniform(48, 62) - self.wave * 2)
        if all(c['dead'] for c in self.cities):
            return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---- dibujo en primera persona (texturizado)
    TK_CW = 3

    def make_tk_backdrops(self):
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        sh = hor - vp.y
        sky = pygame.Surface((vp.w, sh))
        for y in range(sh):
            f = y / sh
            if f < 0.55:
                g = f / 0.55
                c = (int(lerp(8, 52, g)), int(lerp(10, 28, g)), int(lerp(32, 78, g)))
            else:
                g = (f - 0.55) / 0.45
                c = (int(lerp(52, 236, g ** 1.4)), int(lerp(28, 124, g ** 1.4)), int(lerp(78, 92, g)))
            pygame.draw.line(sky, c, (0, y), (vp.w, y))
        fh = vp.bottom - hor
        floor = pygame.Surface((vp.w, fh))
        for y in range(fh):
            f = y / fh
            pygame.draw.line(floor, (int(lerp(122, 30, f ** 0.6)), int(lerp(80, 32, f ** 0.6)), int(lerp(104, 40, f ** 0.6))), (0, y), (vp.w, y))
        moon = pygame.Surface((120, 120), pygame.SRCALPHA)
        for r in range(58, 0, -2):
            pygame.draw.circle(moon, (255, 244, 210, int(46 * (1 - r / 58) ** 1.5)), (60, 60), r)
        pygame.draw.circle(moon, (236, 232, 210), (60, 60), 30)
        pygame.draw.circle(moon, (252, 250, 236), (54, 54), 26)
        for ox, oy, rr in ((-9, -6, 7), (10, 8, 9), (4, -14, 4), (-12, 12, 5)):
            pygame.draw.circle(moon, (200, 196, 176), (60 + ox, 60 + oy), rr)
            pygame.draw.circle(moon, (222, 218, 198), (60 + ox - 1, 60 + oy - 1), max(1, rr - 2))
        return sky.convert(), floor.convert(), moon.convert_alpha()

    def tk_prep(self):
        a = math.radians(self.k['p']['yaw'])
        self._ks, self._kc = math.sin(a), math.cos(a)

    def tk_cam(self, x, y, z):
        p = self.k['p']
        dx, dz = x - p['x'], z - p['z']
        return dx * self._kc - dz * self._ks, y - self.TK_EYE, dx * self._ks + dz * self._kc

    def tk_prj(self, c):
        vp = self.TK_VP
        return vp.centerx + self.TK_F * c[0] / c[2], vp.y + int(vp.h * 0.55) - self.TK_F * c[1] / c[2]

    def tk_clip(self, pts):
        near, out = self.TK_NEAR, []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            ain, bin_ = a[2] >= near, b[2] >= near
            if ain:
                out.append(a)
            if ain != bin_:
                t = (near - a[2]) / (b[2] - a[2])
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, near))
        return out

    def tk_clip_seg(self, a, b):
        near = self.TK_NEAR
        if a[2] < near and b[2] < near:
            return None
        if a[2] < near:
            t = (near - a[2]) / (b[2] - a[2])
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, near)
        elif b[2] < near:
            t = (near - b[2]) / (a[2] - b[2])
            b = (b[0] + (a[0] - b[0]) * t, b[1] + (a[1] - b[1]) * t, near)
        return a, b

    def tk_line(self, cv, a, b, col, w=1):
        seg = self.tk_clip_seg(a, b)
        if seg:
            pygame.draw.line(cv, col, self.tk_prj(seg[0]), self.tk_prj(seg[1]), w)

    def tk_ground_poly(self, cv, pts, col, edge=None):
        q = self.tk_clip([self.tk_cam(x, 0, z) for x, z in pts])
        if len(q) < 3:
            return
        sp = [self.tk_prj(v) for v in q]
        pygame.draw.polygon(cv, col, sp)
        if edge:
            pygame.draw.lines(cv, edge, True, sp, 1)

    def tk_face(self, strips, x0, z0, x1, z1, y0, y1, tex, u_scale, uoff, vs, vo, side, ground):
        vp = self.TK_VP
        F, NEAR = self.TK_F, self.TK_NEAR
        p = self.k['p']
        s_, c_ = self._ks, self._kc
        dx0, dz0, dx1, dz1 = x0 - p['x'], z0 - p['z'], x1 - p['x'], z1 - p['z']
        cx0, cz0 = dx0 * c_ - dz0 * s_, dx0 * s_ + dz0 * c_
        cx1, cz1 = dx1 * c_ - dz1 * s_, dx1 * s_ + dz1 * c_
        u0, u1 = 0.0, 1.0
        if cz0 < NEAR and cz1 < NEAR:
            return
        if cz0 < NEAR:
            t = (NEAR - cz0) / (cz1 - cz0)
            cx0, cz0, u0 = cx0 + (cx1 - cx0) * t, NEAR, t
        elif cz1 < NEAR:
            t = (NEAR - cz1) / (cz0 - cz1)
            cx1, cz1, u1 = cx1 + (cx0 - cx1) * t, NEAR, 1 - t
        xa, xb = vp.centerx + F * cx0 / cz0, vp.centerx + F * cx1 / cz1
        ia, ib = 1.0 / cz0, 1.0 / cz1
        if xa > xb:
            xa, xb, ia, ib, u0, u1 = xb, xa, ib, ia, u1, u0
        if xb <= vp.x or xa >= vp.right or xb - xa < 0.5:
            return
        CW = self.TK_CW
        hor = vp.y + int(vp.h * 0.55)
        EYE = self.TK_EYE
        c0 = max(0, int((xa - vp.x) // CW))
        c1 = min((vp.w - 1) // CW, int((xb - vp.x) // CW))
        uz0, uz1 = u0 * ia, u1 * ib
        tw = tex['tw']
        inv_w = 1.0 / (xb - xa)
        fy1, fy0 = F * (y1 - EYE), F * (y0 - EYE)
        for ci in range(c0, c1 + 1):
            s = (vp.x + ci * CW + CW * 0.5 - xa) * inv_w
            s = 0.0 if s < 0 else (1.0 if s > 1 else s)
            invz = ia + (ib - ia) * s
            z = 1.0 / invz
            u = (uz0 + (uz1 - uz0) * s) * z
            strips.append((z, ci, hor - fy1 * invz, hor - fy0 * invz, tex, side, int((u * u_scale + uoff) * tw) % tw, vs, vo, ground))

    def tk_add_box(self, strips, cx, cz, hw, hd, y0, y1, rot, tex, tile_w, tile_h=None, uoff=0.0):
        p = self.k['p']
        a = math.radians(rot)
        s, c = math.sin(a), math.cos(a)
        wc = [(cx + lx * c + lz * s, cz - lx * s + lz * c) for lx, lz in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
        nrm = ((0, -1), (1, 0), (0, 1), (-1, 0))
        if tile_h:
            vs, vo = 1.0 / tile_h, 0.0
        else:
            vs = 1.0 / (y1 - y0)
            vo = -y0 * vs
        for i in range(4):
            (x0, z0), (x1, z1) = wc[i], wc[(i + 1) % 4]
            nx, nz = nrm[i][0] * c + nrm[i][1] * s, -nrm[i][0] * s + nrm[i][1] * c
            if nx * (p['x'] - (x0 + x1) / 2) + nz * (p['z'] - (z0 + z1) / 2) <= 0:
                continue
            side = 0 if (nx * 0.55 + nz * 0.83) > -0.1 else 1
            self.tk_face(strips, x0, z0, x1, z1, y0, y1, tex, math.hypot(x1 - x0, z1 - z0) / tile_w, uoff + i * 0.37, vs, vo, side,
                         y0 <= 0.01)

    def tk_flush(self, cv, strips):
        vp = self.TK_VP
        CW, F, EYE, NL = self.TK_CW, self.TK_F, self.TK_EYE, TK_NL
        hor = vp.y + int(vp.h * 0.55)
        cover = [vp.bottom] * ((vp.w - 1) // CW + 1)
        strips.sort(key=lambda st: st[0])
        vy = vp.y
        vis = []
        ncol = len(cover)
        for st in strips:
            if st[1] is None:
                img, ix, iy = st[2:5]
                iw, ih = img.get_size()
                c0 = max(0, (ix - vp.x) // CW)
                c1 = min(ncol - 1, (ix + iw - 1 - vp.x) // CW)
                ci = c0
                while ci <= c1:
                    ct = cover[ci]
                    cj = ci
                    while cj < c1 and cover[cj + 1] == ct:
                        cj += 1
                    hc = ct - iy
                    if hc > 0:
                        bx0 = max(ix, vp.x + ci * CW)
                        bx1 = min(ix + iw, vp.x + (cj + 1) * CW)
                        if bx1 > bx0:
                            vis.append((st[0], -1, img, (bx0 - ix, 0, bx1 - bx0, min(ih, hc)), bx0, iy))
                    ci = cj + 1
                continue
            z, ci, top, bot, tex, side, tc, vs, vo, ground = st
            ct = cover[ci]
            if top >= ct:
                continue
            yt = top if top > vy else vy
            yb = bot if bot < ct else ct
            if yb - yt < 1:
                continue
            if ground:
                cover[ci] = yt
            vis.append((z, ci, yt, yb, tex, side, tc, vs, vo))
        scale = pygame.transform.scale
        blit = cv.blit
        old_clip = cv.get_clip()
        cv.set_clip(vp)
        for v in reversed(vis):
            if v[1] == -1:
                blit(v[2], (v[4], v[5]), v[3])
                continue
            z, ci, yt, yb, tex, side, tc, vs, vo = v
            th = tex['th']
            R = tex['reps'] * th
            r0 = R - ((EYE + (hor - yt) * z / F) * vs + vo) * th
            r1 = R - ((EYE + (hor - yb) * z / F) * vs + vo) * th
            i0 = int(r0) if r0 > 0 else 0
            if i0 >= R:
                i0 = R - 1
            n = int(r1) - i0
            if n < 1:
                n = 1
            if i0 + n > R:
                n = R - i0
            lvl = int(z * 0.0625)
            src = tex['var'][lvl if lvl < NL else NL - 1][side]
            blit(scale(src.subsurface((tc, i0, 1, n)), (CW, int(yb - yt) + 1)), (vp.x + ci * CW, int(yt)))
        cv.set_clip(old_clip)
        return len(vis)

    def tk_ground(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        cv.blit(self.tk_floor_bg, (vp.x, hor))
        s_, c_ = self._ks, self._kc
        T = 8.0
        ix0, iz0 = int(p['x'] // T), int(p['z'] // T)
        lim = self.TK_A + 8
        cells = []
        for di in range(-10, 11):
            for dj in range(-10, 11):
                cxw, czw = (ix0 + di + 0.5) * T, (iz0 + dj + 0.5) * T
                if abs(cxw) > lim or abs(czw) > lim:
                    continue
                dx, dz = cxw - p['x'], czw - p['z']
                ccz, ccx = dx * s_ + dz * c_, dx * c_ - dz * s_
                if ccz < -6 or ccz > 84 or abs(ccx) > ccz * 1.6 + 14:
                    continue
                cells.append((ccz, ix0 + di, iz0 + dj))
        cells.sort(reverse=True)
        fog = (110, 74, 100)
        for ccz, i, j in cells:
            h = ((i * 73856093) ^ (j * 19349663)) & 255
            b = 44 + h % 9 - 4
            f = clamp(ccz / 95.0, 0, 0.9)
            col = (int(lerp(b, fog[0], f)), int(lerp(b + 2, fog[1], f)), int(lerp(b + 9, fog[2], f)))
            edge = (int(lerp(b - 12, fog[0], f)), int(lerp(b - 10, fog[1], f)), int(lerp(b - 3, fog[2], f))) if ccz < 45 else None
            x0, z0 = i * T, j * T
            self.tk_ground_poly(cv, ((x0, z0), (x0 + T, z0), (x0 + T, z0 + T), (x0, z0 + T)), col, edge)
        for b in k['blds']:
            dx, dz = b['x'] - p['x'], b['z'] - p['z']
            if dx * s_ + dz * c_ < -30 or dx * dx + dz * dz > 100 ** 2:
                continue
            m = 2.6
            f = clamp(math.hypot(dx, dz) / 100.0, 0, 0.9)
            col = (int(lerp(112, fog[0], f)), int(lerp(112, fog[1], f)), int(lerp(120, fog[2], f)))
            self.tk_ground_poly(cv, ((b['x'] - b['hw'] - m, b['z'] - b['hd'] - m), (b['x'] + b['hw'] + m, b['z'] - b['hd'] - m),
                                     (b['x'] + b['hw'] + m, b['z'] + b['hd'] + m), (b['x'] - b['hw'] - m, b['z'] + b['hd'] + m)),
                                col, (int(col[0] * .75), int(col[1] * .75), int(col[2] * .78)))
        for sc in (-115, -69, -23, 23, 69, 115):
            for zz in range(-120, 121, 8):
                for horiz in (False, True):
                    a0, a1 = (sc, zz) if not horiz else (zz, sc), (sc, zz + 3.6) if not horiz else (zz + 3.6, sc)
                    dx, dz = a0[0] - p['x'], a0[1] - p['z']
                    ccz = dx * s_ + dz * c_
                    if ccz < -4 or ccz > 80 or dx * dx + dz * dz > 80 ** 2:
                        continue
                    w = 0.28
                    if horiz:
                        quad = ((a0[0], a0[1] - w), (a1[0], a1[1] - w), (a1[0], a1[1] + w), (a0[0], a0[1] + w))
                    else:
                        quad = ((a0[0] - w, a0[1]), (a1[0] - w, a1[1]), (a1[0] + w, a1[1]), (a0[0] + w, a0[1]))
                    f = clamp(ccz / 80.0, 0, 0.9)
                    self.tk_ground_poly(cv, quad, (int(lerp(214, fog[0], f)), int(lerp(184, fog[1], f)), int(lerp(70, fog[2], f))))

    def tk_sky(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        sky = k['sky']
        yaw = p['yaw']
        t = self.t
        cv.blit(self.tk_sky_bg, (vp.x, vp.y))
        for az, alt, sz in sky['stars']:
            rel = angle_diff(yaw, az)
            if abs(rel) < 60:
                sx = vp.centerx + self.TK_F * math.tan(math.radians(rel))
                sy = hor - 12 - alt * (hor - vp.y - 20)
                if vp.x < sx < vp.right and sy > vp.y and alt > 0.25:
                    v = 150 + int(90 * math.sin(t * 2 + az))
                    cv.fill((v, v, min(255, v + 20)), (int(sx), int(sy), sz, sz))
        rel = angle_diff(yaw, 42)
        if abs(rel) < 70:
            cv.blit(self.tk_moon, (int(vp.centerx + self.TK_F * math.tan(math.radians(rel)) - 60), hor - 210))
        pts = []
        for i in range(120):
            rel = angle_diff(yaw, i * 3.0)
            if abs(rel) < 75:
                pts.append((vp.centerx + self.TK_F * math.tan(math.radians(rel)), hor - sky['mount'][i] * 1.4))
        if len(pts) > 1:
            pts.sort()
            poly = pts + [(pts[-1][0], hor), (pts[0][0], hor)]
            pygame.draw.polygon(cv, (44, 30, 62), poly)
            pygame.draw.lines(cv, (120, 84, 126), False, pts, 2)
        for n, (az, wd, hh) in enumerate(sky['city']):
            rel = angle_diff(yaw, az)
            if abs(rel) < 75:
                sx = vp.centerx + self.TK_F * math.tan(math.radians(rel))
                ww = self.TK_F * math.radians(wd)
                r = pygame.Rect(int(sx - ww / 2), int(hor - hh), int(ww), int(hh))
                pygame.draw.rect(cv, (30, 22, 48), r)
                pygame.draw.line(cv, (84, 60, 100), r.topleft, r.topright, 1)
                for j in range(5):
                    if (n * 7 + j * 3) % 4 == 0 and r.w > 6:
                        cv.fill((255, 214, 120), (r.x + 2 + (j * 5) % max(1, r.w - 4), r.y + 4 + (j * 9) % max(1, r.h - 6), 2, 2))
        cv.fill((96, 64, 92), (vp.x, hor - 1, vp.w, 3))

    def tk_add_prism(self, strips, cx, cz, r, y0, y1, n, rot, tex, tile_w, uoff=0.0):
        p = self.k['p']
        a0 = math.radians(rot)
        pts = [(cx + math.sin(a0 - 2 * math.pi * i / n) * r, cz + math.cos(a0 - 2 * math.pi * i / n) * r) for i in range(n)]
        vs, vo = 1.0 / (y1 - y0), -y0 / (y1 - y0)
        for i in range(n):
            (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % n]
            mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
            nx, nz = mx - cx, mz - cz
            if nx * (p['x'] - mx) + nz * (p['z'] - mz) <= 0:
                continue
            nl = math.hypot(nx, nz) or 1.0
            side = 0 if (nx / nl * 0.55 + nz / nl * 0.83) > -0.1 else 1
            self.tk_face(strips, x0, z0, x1, z1, y0, y1, tex, math.hypot(x1 - x0, z1 - z0) / tile_w, uoff + i * 0.21, vs, vo, side,
                         y0 <= 0.01)

    def tk_add_tank(self, strips, e):
        """Agrega el sprite pre-renderizado del tanque (casco + torreta) como entrada ordenable por profundidad."""
        p = self.k['p']
        c = self.tk_cam(e['x'], 0, e['z'])
        z = c[2]
        if z < 2.5 or z > 190:
            return
        spr = self.tk_spr[e['kind']]
        sx, sy = self.tk_prj(c)
        scale = (self.TK_F / z) / spr['px']
        step = 360.0 / TK_ANG
        hi = int(round(((e['h'] - p['yaw']) % 360) / step)) % TK_ANG
        ti = int(round(((e['tur'] - p['yaw']) % 360) / step)) % TK_ANG
        parts = (spr['hull'][hi], spr['tur'][ti])
        x0 = min(-a for _, a, _ in parts)
        x1 = max(im.get_width() - a for im, a, _ in parts)
        y0 = min(-b for _, _, b in parts)
        y1 = max(im.get_height() - b for im, _, b in parts)
        cvs = pygame.Surface((int(x1 - x0) + 1, int(y1 - y0) + 1), pygame.SRCALPHA)
        for im, a, b in parts:
            cvs.blit(im, (int(-x0 - a), int(-y0 - b)))
        # se escala solo la parte visible dentro del visor (de cerca el sprite sería enorme)
        vp = self.TK_VP
        dx, dy = sx + x0 * scale, sy + y0 * scale
        dw, dh = cvs.get_width() * scale, cvs.get_height() * scale
        vx0, vx1 = max(dx, vp.x), min(dx + dw, vp.right)
        vy0, vy1 = max(dy, vp.y), min(dy + dh, vp.bottom)
        if vx1 - vx0 < 1 or vy1 - vy0 < 1:
            return
        sw, sh = cvs.get_size()
        r = pygame.Rect(int((vx0 - dx) / scale), int((vy0 - dy) / scale), 0, 0)
        r.w = min(sw - r.x, int((vx1 - dx) / scale) - r.x + 2)
        r.h = min(sh - r.y, int((vy1 - dy) / scale) - r.y + 2)
        img = pygame.transform.scale(cvs.subsurface(r), (max(1, int(r.w * scale)), max(1, int(r.h * scale))))
        f = min(0.8, z / 170.0)
        img.fill((int(255 * (1 - f)),) * 3 + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        img.fill(tuple(int(q * f) for q in TK_FOG) + (0,), special_flags=pygame.BLEND_RGB_ADD)
        strips.append((z - 0.6, None, img, int(dx + r.x * scale), int(dy + r.y * scale)))

    def tk_scene(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        t = self.t
        self.tk_prep()
        cv.fill((0, 0, 0), vp)
        self.tk_sky(cv)
        self.tk_ground(cv)
        T = self.tk_tex
        strips = []
        for b in k['blds']:
            dx, dz = b['x'] - p['x'], b['z'] - p['z']
            if dx * dx + dz * dz > 170 ** 2:
                continue
            if b['hall']:
                self.tk_add_box(strips, b['x'], b['z'], b['hw'], b['hd'], 0, b['h'], 0, T['hall'], 8.0, 11.0)
            else:
                self.tk_add_box(strips, b['x'], b['z'], b['hw'], b['hd'], 0, b['h'], 0, T['bld'][b['tx']], 8.0, 8.0, b['uo'])
        for e in k['tanks']:
            self.tk_add_tank(strips, e)
        for m in k['missiles']:
            self.tk_add_box(strips, m['x'], m['z'], .35, 1.5, .6, 1.5, m['h'], T['missile'], 3.0)
        self.tk_flush(cv, strips)
        for b in k['blds']:
            if b['hall']:
                top = self.tk_cam(b['x'], b['h'] + 8, b['z'])
                base = self.tk_cam(b['x'], b['h'], b['z'])
                self.tk_line(cv, base, top, (210, 216, 230), 2)
                if top[2] > 1 and int(t * 2) % 2 == 0:
                    sx, sy = self.tk_prj(top)
                    glow(cv, sx, sy, min(120, max(8, int(220 / top[2]))), (255, 60, 50))
                    pygame.draw.circle(cv, (255, 120, 100), (int(sx), int(sy)), max(2, int(100 / top[2])))
        for m in k['missiles']:
            a = math.radians(m['h'])
            fl_ = self.tk_cam(m['x'] - math.sin(a) * 2.2, 1.0, m['z'] - math.cos(a) * 2.2)
            if fl_[2] > 1:
                fx_, fy_ = self.tk_prj(fl_)
                glow(cv, fx_, fy_, min(160, int(220 / fl_[2]) + 8), (255, 150, 50))
        for e in k['tanks'] + k['missiles']:
            if not self.tk_los(p['x'], p['z'], e['x'], e['z']):
                continue
            c = self.tk_cam(e['x'], (6.4 if e['kind'] == 'super' else 5.2) if e['kind'] != 'missile' else 3.0, e['z'])
            if 6 < c[2] < 110:
                sx, sy = self.tk_prj(c)
                if vp.x + 6 < sx < vp.right - 6:
                    sz = max(5, int(260 / c[2]))
                    col = (255, 70, 60) if e['kind'] == 'tank' else ((255, 190, 50) if e['kind'] == 'super' else (255, 236, 90))
                    pygame.draw.polygon(cv, (20, 8, 8), [(sx - sz - 2, sy - sz - 2), (sx + sz + 2, sy - sz - 2), (sx, sy + 3)])
                    pygame.draw.polygon(cv, col, [(sx - sz, sy - sz), (sx + sz, sy - sz), (sx, sy)])
        for s in k['shells']:
            self.tk_shell(cv, s, (255, 140, 80))
        for s in k['pshells']:
            self.tk_shell(cv, s, (255, 236, 160))
        for d_ in k['debris']:
            a = self.tk_cam(d_['x'], d_['y'], d_['z'])
            b = self.tk_cam(d_['x'] - d_['vx'] * .07, d_['y'] - d_['vy'] * .07, d_['z'] - d_['vz'] * .07)
            self.tk_line(cv, a, b, (255, int(150 + 100 * clamp(d_['life'], 0, 1)), 60), 2)
        for bm in k['booms']:
            c = self.tk_cam(bm['x'], bm['y'], bm['z'])
            if c[2] < 1.5:
                continue
            sx, sy = self.tk_prj(c)
            age = bm['age'] / bm['life']
            r = min(170, int(self.TK_F * bm['size'] * (0.35 + age * 0.9) / c[2]))
            if r < 2:
                continue
            draw_circ(cv, sx, sy - r * 0.3, r, (40, 36, 40), 150 * (1 - age))
            glow(cv, sx, sy, int(r * 1.5), (255, 150, 60), 1 - age)
            if age < 0.45:
                glow(cv, sx, sy, int(r), (255, 240, 190), 1 - age * 2)

    def tk_shell(self, cv, s, col):
        a = self.tk_cam(s['x'], s['y'], s['z'])
        if a[2] < 0.6:
            return
        sx, sy = self.tk_prj(a)
        r = min(40, max(2, int(70 / a[2])))
        glow(cv, sx, sy, r * 3 + 8, col, 0.8)
        b = self.tk_cam(s['x'] - s['vx'] * 0.05, s['y'], s['z'] - s['vz'] * 0.05)
        self.tk_line(cv, a, b, (255, 255, 255), 2)
        pygame.draw.circle(cv, col, (int(sx), int(sy)), r)

    def tk_overlay(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        hor = vp.y + int(vp.h * 0.55)
        cx = vp.centerx
        rec = clamp((p['cd'] - 0.5) / 0.2, 0, 1)
        if rec > 0.05:
            glow(cv, cx, vp.bottom - 6, 150, (255, 190, 90), rec * 0.9)
        rc = (255, 236, 160)
        pygame.draw.line(cv, rc, (cx - 26, hor), (cx - 8, hor), 1)
        pygame.draw.line(cv, rc, (cx + 8, hor), (cx + 26, hor), 1)
        pygame.draw.line(cv, rc, (cx, hor - 26), (cx, hor - 8), 1)
        pygame.draw.line(cv, rc, (cx, hor + 8), (cx, hor + 26), 1)
        pygame.draw.circle(cv, rc, (cx, hor), 2)

    def draw_tank(self, cv):
        k = self.k
        p = k['p']
        vp = self.TK_VP
        t = self.t
        cv.fill((8, 12, 10))
        cv.set_clip(vp)
        self.tk_scene(cv)
        self.tk_overlay(cv)
        for seg in k['cracks']:
            pygame.draw.lines(cv, (150, 220, 190), False, seg, 1)
            pygame.draw.lines(cv, (40, 70, 60), False, [(x + 2, y + 2) for x, y in seg], 1)
        if k['hurt'] > 0:
            ov = pygame.Surface(vp.size, pygame.SRCALPHA)
            ov.fill((255, 30, 20, int(120 * clamp(k['hurt'] * 1.6, 0, 1))))
            cv.blit(ov, vp.topleft)
        if p['blocked'] > 0:
            pygame.draw.rect(cv, (255, 200, 60), vp, 4)
        cv.set_clip(None)
        cv.blit(self.cockpit, (0, 0))
        G1, G2 = (90, 255, 150), (40, 150, 90)
        rx, ry, rr = W // 2, 62, 50
        pygame.draw.circle(cv, (0, 12, 6), (rx, ry), rr)
        for q in (rr, rr * 2 // 3, rr // 3):
            pygame.draw.circle(cv, (0, 90, 50), (rx, ry), q, 1)
        pygame.draw.line(cv, (0, 90, 50), (rx - rr, ry), (rx + rr, ry), 1)
        pygame.draw.line(cv, (0, 90, 50), (rx, ry - rr), (rx, ry + rr), 1)
        sw = k['sweep'] * 6.283
        pygame.draw.line(cv, (60, 255, 140), (rx, ry), (rx + math.sin(sw) * rr, ry - math.cos(sw) * rr), 2)
        rng = 95.0
        ya = math.radians(p['yaw'])
        sy_, cy_ = math.sin(ya), math.cos(ya)

        def blip(x, z, col, size, clampit=False):
            dx, dz = x - p['x'], z - p['z']
            cx_, cz_ = dx * cy_ - dz * sy_, dx * sy_ + dz * cy_
            d = math.hypot(cx_, cz_)
            if d > rng:
                if not clampit:
                    return
                cx_, cz_ = cx_ / d * rng, cz_ / d * rng
            pygame.draw.rect(cv, col, (rx + cx_ / rng * (rr - 3) - size // 2, ry - cz_ / rng * (rr - 3) - size // 2, size, size))
        for b in k['blds']:
            blip(b['x'], b['z'], (0, 110, 70), 2)
        blip(0, 0, (90, 255, 255), 4, True)
        for e in k['tanks']:
            blip(e['x'], e['z'], (255, 90, 60) if e['kind'] == 'tank' else (255, 190, 50), 4)
        for m in k['missiles']:
            blip(m['x'], m['z'], (255, 235, 90), 3)
        pygame.draw.polygon(cv, (90, 255, 150), [(rx, ry - 5), (rx - 3, ry + 3), (rx + 3, ry + 3)], 1)
        pygame.draw.circle(cv, (70, 120, 90), (rx, ry), rr, 2)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, G1, 40, 20)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, G2, 40, 52)
        self.text(cv, k['city']['name'], self.f_s, G1, 40, 78)
        left = len(k['queue']) + len(k['tanks']) + len(k['missiles'])
        self.text(cv, 'ENEMIGOS %d' % left, self.f_m, (255, 130, 100), W - 40, 20, 'r')
        city = k['city']
        self.text(cv, 'CIUDAD', self.f_s, G2, W - 270, 56)
        self.bar(cv, W - 200, 52, 160, 18, city['hp'] / 100, (80, 230, 110) if city['hp'] > 50 else (240, 90, 70), '%d%%' % city['hp'])
        by = vp.bottom + 24
        self.text(cv, 'ARMADURA', self.f_s, G1, 40, by)
        self.bar(cv, 40, by + 22, 280, 24, p['hp'] / TK_HP, (80, 230, 110) if p['hp'] > TK_HP * 0.35 else (240, 80, 70), '%d' % max(0, p['hp']))
        self.text(cv, 'CAÑON', self.f_s, G1, 40, by + 56)
        rl = 1 - clamp(p['cd'] / 0.7, 0, 1)
        self.bar(cv, 40, by + 78, 280, 18, rl, (90, 255, 150) if rl >= 1 else (255, 190, 70), 'LISTO' if rl >= 1 else 'CARGANDO')
        hd = int(p['yaw']) % 360
        self.text(cv, 'RUMBO %03d' % hd, self.f_m, G1, W - 40, by, 'r')
        card = 'N NE E SE S SO O NO'.split()[int(((hd + 22.5) % 360) // 45)]
        self.text(cv, card, self.f_l, G1, W - 40, by + 28, 'r')
        self.text(cv, 'VELOCIDAD %2d' % abs(p['v']), self.f_s, G2, W - 40, by + 74, 'r')
        msg, mcol = '', (255, 200, 80)
        nearest = None
        for e in k['tanks']:
            d = math.hypot(e['x'] - p['x'], e['z'] - p['z'])
            if nearest is None or d < nearest[0]:
                nearest = (d, e)
        if k['inrange']:
            msg, mcol = 'ENEMIGO EN RANGO', (255, 90, 70)
        elif k['msg_t'] > 0:
            msg = k['msg']
        elif nearest and nearest[0] < 120:
            rel = angle_diff(p['yaw'], math.degrees(math.atan2(nearest[1]['x'] - p['x'], nearest[1]['z'] - p['z'])))
            if abs(rel) > 45:
                msg = 'ENEMIGO A LA %s' % ('DERECHA >>' if 0 < rel < 135 else ('<< IZQUIERDA' if -135 < rel < 0 else 'ESPALDA'))
                mcol = (255, 150, 70)
        if msg and (k['inrange'] or int(t * 4) % 2 == 0 or k['msg_t'] > 0):
            self.text(cv, msg, self.f_m, mcol, W // 2, vp.bottom + 56, 'c')
        self.text(cv, 'W/S avanzar | A/D girar | ESPACIO o clic: cañón', self.f_s, G2, W // 2, H - 28, 'c')

    # ------------------------------------------------------------ DIBUJO
    def blit_ship(self, dst, key, x, y, heading, cx=0, cy=0, alpha=255):
        surf, sh = self.ships[key]
        r = pygame.transform.rotate(surf, -heading)
        rs = pygame.transform.rotate(sh, -heading)
        sx, sy = int(x - cx), int(y - cy)
        rs.set_alpha(int(85 * alpha / 255))
        dst.blit(rs, (sx - rs.get_width() // 2 + 5, sy - rs.get_height() // 2 + 7))
        if alpha < 255:
            r.set_alpha(alpha)
        dst.blit(r, (sx - r.get_width() // 2, sy - r.get_height() // 2))

    def nest_gfx(self):
        if not hasattr(self, '_nest_gfx'):
            S = 150
            s = pygame.Surface((S, S), pygame.SRCALPHA)
            c = S // 2
            pygame.draw.circle(s, (0, 0, 0, 50), (c + 4, c + 6), 62)
            pygame.draw.circle(s, (60, 120, 170), (c, c), 68, 3)
            pygame.draw.circle(s, (214, 196, 140), (c, c), 60)
            pygame.draw.circle(s, (86, 128, 78), (c, c), 50)
            rnd = random.Random(5)
            for _ in range(26):
                a, d = rnd.uniform(0, 6.28), rnd.uniform(14, 46)
                pygame.draw.circle(s, (54, 100, 58), (int(c + math.cos(a) * d), int(c + math.sin(a) * d)), rnd.randint(3, 6))
            for k in range(10):
                a = 6.2832 * k / 10
                pygame.draw.circle(s, (176, 150, 100), (int(c + math.cos(a) * 30), int(c + math.sin(a) * 30)), 6)
                pygame.draw.circle(s, (120, 100, 66), (int(c + math.cos(a) * 30), int(c + math.sin(a) * 30)), 6, 1)
            pygame.draw.circle(s, (120, 124, 128), (c, c), 22)
            pygame.draw.circle(s, (80, 84, 90), (c, c), 22, 3)
            self._nest_gfx = s
        return self._nest_gfx

    def blit_turret(self, dst, surf, x, y, ang, alpha=255):
        r = pygame.transform.rotate(surf, -ang)
        if alpha < 255:
            r.set_alpha(alpha)
        dst.blit(r, (int(x) - r.get_width() // 2, int(y) - r.get_height() // 2))

    def draw_ocean(self, dst, cx, cy, t):
        dst.blit(self.ocean_base, (0, 0))
        for tile, sx, px, py in ((self.tileA, 1.0, t * 12, t * 5), (self.tileB, 0.8, -t * 8, t * 4)):
            ox = -((cx * sx + px) % 256)
            oy = -((cy * sx + py) % 256)
            x = ox
            while x < W:
                y = oy
                while y < H:
                    dst.blit(tile, (int(x), int(y)))
                    y += 256
                x += 256

    def draw(self):
        cv = self.canvas
        if self.state in ('title',):
            self.draw_title(cv)
        elif self.state == 'map':
            self.draw_map(cv)
        elif self.state == 'defense':
            self.draw_defense(cv)
        elif self.state == 'combat':
            self.draw_combat(cv)
        elif self.state == 'aerial':
            self.draw_aerial(cv)
        elif self.state == 'hack':
            self.draw_hack(cv)
        elif self.state == 'tank':
            self.draw_tank(cv)
        elif self.state == 'port':
            self.draw_port(cv)
        elif self.state == 'ground':
            self.draw_ground(cv)
        elif self.state == 'gameover':
            self.draw_gameover(cv)
        self.draw_overlays(cv)
        ox = oy = 0
        if self.shake > 0.5:
            ox, oy = int(random.uniform(-self.shake, self.shake)), int(random.uniform(-self.shake, self.shake))
        self.screen.fill((0, 0, 0))
        self.screen.blit(cv, (ox, oy))
        if self.crt_on:
            self.screen.blit(self.crt, (0, 0))
        pygame.display.flip()

    def draw_overlays(self, cv):
        for i, q in enumerate(self.toasts):
            self.text(cv, q[0], self.f_m, q[1], W // 2, 70 + i * 26, 'c', alpha=int(255 * clamp(q[2], 0, 1)))
        if self.banners:
            b = self.banners[0]
            k = b[3] / b[4]
            a = int(255 * clamp(min(k * 6, (1 - k) * 8 + 0.2, 1), 0, 1))
            self.text(cv, b[0], self.f_l, b[2], W // 2, 190, 'c', alpha=a)
            if b[1]:
                self.text(cv, b[1], self.f_m, (235, 240, 255), W // 2, 232, 'c', alpha=a)
        for s, x, y, life, col in self.pops:
            self.text(cv, s, self.f_m, col, int(x), int(y), 'c', alpha=int(255 * clamp(life * 1.5, 0, 1)))
        if self.paused:
            self.dim(cv, 130)
            self.text(cv, 'PAUSA', self.f_xl, (255, 255, 255), W // 2, 260, 'c')
            self.text(cv, 'P / ESC: continuar   |   M: sonido   |   F1: efecto CRT   |   Q: salir', self.f_m, (190, 210, 240),
                      W // 2, 380, 'c')
        if self.fade > 0:
            self.fade_surf.set_alpha(int(255 * self.fade))
            cv.blit(self.fade_surf, (0, 0))

    # ---- título
    def draw_title(self, cv):
        t = self.t
        self.draw_ocean(cv, t * 30, t * 8, t)
        self.dim(cv, 45)
        x = (t * 70) % (W + 300) - 150
        self.blit_ship(cv, 'p_map', x, 640, 90)
        x2 = W + 150 - (t * 55) % (W + 300)
        self.blit_ship(cv, 'e_map', x2, 700, 270)
        for ln, y, col in (('FINAL', 90, (255, 220, 110)), ('LEGACY', 175, (255, 160, 70))):
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-3, -3), (3, 3), (-3, 3), (3, -3)):
                self.text(cv, ln, self.f_xl, (30, 10, 0), W // 2 + dx, y + dy, 'c', shadow=False)
            self.text(cv, ln, self.f_xl, col, W // 2, y, 'c', shadow=False)
        self.text(cv, 'EDICIÓN OMAR BRONDO', self.f_l, (120, 220, 255), W // 2, 275, 'c')
        self.panel(cv, (W // 2 - 380, 325, 760, 240), 170)
        lines = ['MAPA   W/S acelerar-frenar   A/D girar   R (en puerto) reabastecer   L desembarcar',
                 'DEFENSA   Mouse o flechas apuntan   Clic/ESPACIO lanzan interceptor',
                 'COMBATE   Mouse apunta, clic lanza un misil recto (¡adelantate!)   E: huir',
                 'TIERRA   WASD soldado   Clic disparar   R recargar   ESPACIO granada',
                 'TANQUE   W/S avanzar   A/D girar   ESPACIO o clic: cañón',
                 'JEFE   Instalá antenas en las islas (L) y hackeá su escudo con H cerca del buque',
                 'AIRE   WASD mover   ESPACIO disparar   B bomba',
                 'P pausa   M sonido   F1 efecto CRT   F2 tanques   F3 aéreo   F4 desembarco   F5 náufragos   F6 convoy   F7 puerto (modo prueba)']
        for i, ln in enumerate(lines):
            self.text(cv, ln, self.f_s, (220, 232, 255), W // 2 - 360, 336 + i * 28)
        if int(t * 2) % 2 == 0:
            self.text(cv, 'PRESIONÁ ENTER PARA ZARPAR', self.f_l, (255, 255, 255), W // 2, 575, 'c')
        self.text(cv, 'Récord: %d' % self.hiscore, self.f_m, (255, 230, 120), W // 2, 640, 'c')
        self.text(cv, 'Hundí %d oleadas y salvá al menos una ciudad para ganar' % WIN_WAVE, self.f_s, (160, 190, 220), W // 2, 690, 'c')

    # ---- game over
    def draw_gameover(self, cv):
        self.draw_ocean(cv, self.t * 10, 0, self.t)
        self.dim(cv, 110)
        col = (120, 255, 160) if self.victory else (255, 90, 80)
        self.text(cv, '¡VICTORIA!' if self.victory else 'FIN DE LA PARTIDA', self.f_xl, col, W // 2, 180, 'c')
        self.text(cv, self.end_msg, self.f_l, (255, 255, 255), W // 2, 300, 'c')
        self.text(cv, 'Puntaje: %d' % self.score, self.f_l, (255, 230, 120), W // 2, 380, 'c')
        self.text(cv, 'Récord: %d' % self.hiscore, self.f_m, (200, 220, 255), W // 2, 430, 'c')
        alive = sum(1 for c in self.cities if not c['dead'])
        self.text(cv, 'Ciudades salvadas: %d/4   Oleada: %d' % (alive, self.wave), self.f_m, (200, 220, 255), W // 2, 470, 'c')
        if int(self.t * 2) % 2 == 0:
            self.text(cv, 'ENTER para jugar de nuevo', self.f_l, (255, 255, 255), W // 2, 560, 'c')

    # ---- HUD común
    def draw_hud(self, cv, show_fuel=True):
        self.panel(cv, (14, H - 126, 330, 112), 160)
        self.bar(cv, 26, H - 116, 306, 24, self.hull / 100, (80, 220, 110) if self.hull > 35 else (240, 80, 70), 'CASCO %d%%' % self.hull)
        if show_fuel:
            self.bar(cv, 26, H - 86, 306, 24, self.fuel / 100, (80, 180, 255) if self.fuel > 20 else (240, 80, 70), 'COMBUSTIBLE %d%%' % self.fuel)
        self.bar(cv, 26, H - 56, 306, 24, self.ammo / 40, (255, 210, 70) if self.ammo > 6 else (240, 80, 70), 'MUNICION %d' % self.ammo)
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, (160, 200, 240), 26, 42)

    def draw_cities_hud(self, cv):
        self.panel(cv, (W - 296, 12, 282, 56), 160)
        for i, c in enumerate(self.cities):
            x = W - 286 + i * 69
            col = (80, 230, 110) if c['hp'] > 60 else ((255, 200, 70) if c['hp'] > 30 else (240, 80, 70))
            if c['dead']:
                col = (90, 90, 90)
            pygame.draw.rect(cv, (8, 12, 24), (x, 22, 60, 12))
            pygame.draw.rect(cv, col, (x + 1, 23, int(58 * c['hp'] / 100), 10))
            self.text(cv, 'ABCD'[i] + ('X' if c['dead'] else ''), self.f_s, (230, 240, 255), x + 22, 38)

    # ---- mapa
    def draw_map(self, cv):
        cx, cy = int(self.cam[0]), int(self.cam[1])
        self.draw_ocean(cv, cx, cy, self.t)
        cv.blit(self.land, (0, 0), area=pygame.Rect(cx, cy, W, H))
        for c in self.cities:
            surf = self.city_surf[c['name']][1 if c['dead'] else 0]
            sx, sy = c['x'] - cx, c['y'] - cy
            if -300 < sx < W + 300 and -300 < sy < H + 300:
                cv.blit(surf, (sx - surf.get_width() // 2, sy - surf.get_height() // 2))
                if not c['dead']:
                    self.text(cv, c['name'], self.f_s, (255, 255, 255), sx, sy - c['r'] * 0.75 - 38, 'c')
                    pygame.draw.rect(cv, (8, 12, 24), (sx - 32, sy - c['r'] * 0.75 - 16, 64, 7))
                    col = (80, 230, 110) if c['hp'] > 60 else ((255, 200, 70) if c['hp'] > 30 else (240, 80, 70))
                    pygame.draw.rect(cv, col, (sx - 31, sy - c['r'] * 0.75 - 15, int(62 * c['hp'] / 100), 5))
                    dx_, dy_ = c['dock'][0] - cx, c['dock'][1] - cy
                    pulse = 0.5 + 0.5 * math.sin(self.t * 3)
                    draw_circ(cv, dx_, dy_, 112 + pulse * 8, (120, 255, 200), 80, 2)
                    self.text(cv, 'PUERTO', self.f_s, (150, 255, 210), dx_, dy_ - 8, 'c')
        px_, py_, pr_, _ps = ENEMY_PORT
        sx, sy = px_ - cx, py_ - cy
        if -200 < sx < W + 200 and -200 < sy < H + 200:
            done = self.port_done
            col = (120, 130, 140) if done else (255, 90, 80)
            pygame.draw.rect(cv, (96, 90, 100), (sx - 46, sy - 8, 92, 18), border_radius=3)
            for k in range(-1, 2):
                pygame.draw.rect(cv, (150, 70, 60) if not done else (110, 110, 116), (sx + k * 28 - 8, sy - 30, 16, 22))
            pygame.draw.line(cv, (210, 210, 220), (sx + 46, sy - 8), (sx + 46, sy - 50), 3)
            pygame.draw.line(cv, (210, 210, 220), (sx + 46, sy - 50), (sx + 8, sy - 38), 3)
            pygame.draw.line(cv, col, (sx - 40, sy - 8), (sx - 40, sy - 52), 2)
            pygame.draw.polygon(cv, col, [(sx - 40, sy - 52), (sx - 18, sy - 45), (sx - 40, sy - 38)])
            self.text(cv, 'PUERTO ENEMIGO - TOMADO' if done else 'PUERTO ENEMIGO (T)', self.f_s, (200, 205, 215) if done else (255, 170, 150),
                      sx, sy + pr_ * 0.95, 'c')
        for q in self.crates:
            sx, sy = q['x'] - cx, q['y'] - cy + math.sin(self.t * 2 + q['x']) * 3
            col = {'ammo': (255, 210, 70), 'fuel': (90, 230, 120), 'repair': (240, 240, 255)}[q['kind']]
            glow(cv, sx, sy, 34, col, 0.6)
            pygame.draw.rect(cv, (120, 84, 50), (sx - 11, sy - 11, 22, 22), border_radius=3)
            pygame.draw.rect(cv, col, (sx - 11, sy - 11, 22, 22), 2, border_radius=3)
            self.text(cv, {'ammo': 'M', 'fuel': 'C', 'repair': '+'}[q['kind']], self.f_s, (255, 255, 255), sx, sy - 9, 'c', shadow=False)
        for mc in self.mclouds:
            mx_ = (mc['x'] + self.t * 14) % (WORLD_W + 800) - 400
            my_ = (mc['y'] + self.t * 6) % (WORLD_H + 500) - 250
            w_, h_ = mc['spr'].get_size()
            if -w_ < mx_ - cx < W and -h_ < my_ - cy < H:
                cv.blit(mc['spr'], (mx_ - cx, my_ - cy))
        for i in ANTENNA_ISLANDS:
            ix, iy, ir, _sd = EXTRA_ISLANDS[i]
            sx, sy = ix - cx, iy - cy
            if not (-200 < sx < W + 200 and -200 < sy < H + 200):
                continue
            if self.antennas[i]:
                cv.blit(self.antenna_gfx, (sx - 24, sy - 82))
                if int(self.t * 1.6) % 2 == 0:
                    glow(cv, sx, sy - 76, 18, (255, 70, 60))
                for j in range(3):
                    ph = (self.t * 0.7 + j / 3) % 1
                    draw_circ(cv, sx, sy - 76, 8 + ph * 50, (120, 240, 255), 150 * (1 - ph), 2)
                self.text(cv, self.isl_name(i) + ' - ANTENA', self.f_s, (150, 240, 255), sx, sy + ir * 0.95, 'c')
            else:
                pulse = 0.5 + 0.5 * math.sin(self.t * 3 + i)
                draw_circ(cv, sx, sy, 26 + pulse * 6, (255, 220, 90), 150, 2)
                pygame.draw.line(cv, (230, 230, 230), (sx, sy + 8), (sx, sy - 34), 2)
                pygame.draw.polygon(cv, (255, 210, 70), [(sx, sy - 34), (sx + 20, sy - 27), (sx, sy - 20)])
                left = MAX_LANDING_ATTEMPTS - self.landing_attempts[i]
                self.text(cv, '%s - %s' % (self.isl_name(i), 'DESEMBARCO (%d)' % left if left > 0 else 'SIN INTENTOS'),
                          self.f_s, (255, 230, 140) if left > 0 else (200, 120, 110), sx, sy + ir * 0.95, 'c')
        self.fxm.draw(cv, cx, cy)
        for nst in self.nests:
            if not nst['alive']:
                continue
            nx_, ny_ = nst['x'] - cx, nst['y'] - cy
            if -80 < nx_ < W + 80 and -80 < ny_ < H + 80:
                pygame.draw.circle(cv, (150, 130, 96), (int(nx_), int(ny_)), 17)
                pygame.draw.circle(cv, (90, 94, 100), (int(nx_), int(ny_)), 11)
                ex_, ey_ = vec(nst['ang'], 18)
                pygame.draw.line(cv, (60, 62, 68), (nx_, ny_), (nx_ + ex_, ny_ + ey_), 4)
                if nst['seen'] or self.radar_t > 0:
                    pul = 0.5 + 0.5 * math.sin(self.t * 4 + nst['x'])
                    draw_circ(cv, nx_, ny_, 330, (255, 80, 70), 22 + 24 * pul, 2)
                    self.text(cv, 'BATERÍA', self.f_s, (255, 150, 130), nx_, ny_ + 24, 'c')
        for en in self.enemies:
            if en.get('sub'):
                if dist(en['x'], en['y'], self.sx, self.sy) < 420 or self.radar_t > 0:
                    self.blit_ship(cv, 's_map', en['x'], en['y'], en['h'], cx, cy, alpha=120)
                    if en['state'] == 'chase':
                        draw_circ(cv, en['x'] - cx, en['y'] - cy, 44, (255, 80, 70), 120, 2)
                continue
            self.blit_ship(cv, 'b_map' if en.get('is_boss') else 'e_map', en['x'], en['y'], en['h'], cx, cy)
            if en['state'] == 'chase':
                draw_circ(cv, en['x'] - cx, en['y'] - cy, 44, (255, 80, 70), 120, 2)
            if en.get('shield'):
                sx_, sy_ = en['x'] - cx, en['y'] - cy
                pulse = 0.5 + 0.5 * math.sin(self.t * 3)
                draw_circ(cv, sx_, sy_, SHIELD_R, (255, 90, 220), 20 + 20 * pulse)
                draw_circ(cv, sx_, sy_, SHIELD_R, (255, 130, 235), 150 + 80 * pulse, 3)
                draw_circ(cv, sx_, sy_, SHIELD_R - 14, (160, 90, 255), 70, 1)
                self.text(cv, 'ACORAZADO %s' % en['name'], self.f_s, (255, 150, 235), sx_, sy_ + 78, 'c')
        self.blit_ship(cv, 'p_map', self.sx, self.sy, self.sh, cx, cy)
        # HUD
        self.draw_hud(cv)
        self.draw_cities_hud(cv)
        self.draw_minimap(cv)
        if self.attack is not None:
            self.draw_attack(cv, cx, cy)
        yy = 92 if self.attack is not None else 8
        if self.rescue is not None:
            self.draw_rescue(cv, cx, cy, yy)
            yy += 52
        if self.convoy is not None:
            self.draw_convoy(cv, cx, cy, yy)
        thr = 1.0 if self.attack is not None else 1 - clamp(self.strike_t / 60.0, 0, 1)
        self.text(cv, 'AMENAZA ENEMIGA', self.f_s, (255, 190, 170), W - 296 + 8, 76)
        self.bar(cv, W - 296, 96, 282, 14, thr, (255, 90 + int(100 * (1 - thr)), 60), '')
        n_ant = sum(self.antennas.values())
        need = self.antennas_needed()
        self.text(cv, 'ANTENAS %d/%d  (jefe: %d)' % (n_ant, len(self.antennas), need), self.f_s,
                  (130, 235, 255) if n_ant >= need else (255, 190, 120), W - 296 + 8, 116)
        bs = self.nearest_shield_boss()
        if bs:
            if n_ant < self.antennas_needed():
                self.text(cv, 'ESCUDO DEL JEFE: necesitás %d antenas (tenés %d) - desembarcá en las islas (L)' % (self.antennas_needed(), n_ant),
                          self.f_m, (255, 150, 235), W // 2, H - 176, 'c')
            elif bs['hack_cd'] > 0:
                self.text(cv, 'Sistemas enemigos reiniciando: %d s' % math.ceil(bs['hack_cd']), self.f_m, (255, 200, 120), W // 2, H - 176, 'c')
            else:
                self.text(cv, 'H: CIBERATAQUE al escudo del jefe (%d antena%s)' % (n_ant, '' if n_ant == 1 else 's'), self.f_m,
                          (130, 240, 255), W // 2, H - 176, 'c')
        dk = self.nearest_dock()
        if dk:
            self.text(cv, 'PUERTO: mantené R para reabastecer y reparar',
                      self.f_m, (140, 255, 210), W // 2, H - 148, 'c')
        elif self.nearest_port():
            self.text(cv, 'PUERTO ENEMIGO: presioná T para asaltarlo  |  Intentos: %d/2' % self.port_tries,
                      self.f_m, (255, 150, 120), W // 2, H - 148, 'c')
        else:
            island = self.nearest_landing_island()
            if island:
                island_idx, x, y, r, s = island
                attempts = self.landing_attempts[island_idx]
                if attempts >= MAX_LANDING_ATTEMPTS:
                    self.text(cv, '%s: sin intentos de desembarco' % self.isl_name(island_idx),
                              self.f_m, (255, 140, 110), W // 2, H - 148, 'c')
                else:
                    self.text(cv, '%s CERCANA: presioná L para desembarcar (10 soldados enemigos)  |  Intentos: %d/%d' %
                              (self.isl_name(island_idx), attempts, MAX_LANDING_ATTEMPTS),
                              self.f_m, (100, 180, 255), W // 2, H - 148, 'c')
            elif self.fuel <= 0:
                self.text(cv, 'SIN COMBUSTIBLE', self.f_m, (255, 90, 80), W // 2, H - 148, 'c')
        if self.warned and int(self.t * 4) % 2 == 0:
            pygame.draw.rect(cv, (255, 40, 40), (0, 0, W, H), 8)

    def draw_minimap(self, cv):
        mw, mh = 240, 180
        x0, y0 = W - mw - 14, H - mh - 14
        self.panel(cv, (x0 - 4, y0 - 4, mw + 8, mh + 8), 190)
        sc = mw / WORLD_W
        pygame.draw.rect(cv, (12, 40, 78), (x0, y0, mw, mh))
        for ix, iy, ir, _sd in self.islands:
            pygame.draw.circle(cv, (70, 120, 70), (int(x0 + ix * sc), int(y0 + iy * sc)), max(2, int(ir * sc * 1.1)))
        for c in self.cities:
            pygame.draw.rect(cv, (90, 90, 90) if c['dead'] else (255, 220, 80), (x0 + c['x'] * sc - 3, y0 + c['y'] * sc - 3, 6, 6))
            if self.attack is not None and self.attack['city'] is c and int(self.t * 4) % 2 == 0:
                pygame.draw.circle(cv, (255, 60, 50), (int(x0 + c['x'] * sc), int(y0 + c['y'] * sc)), 9, 2)
        for i in ANTENNA_ISLANDS:
            mx_, my_ = int(x0 + EXTRA_ISLANDS[i][0] * sc), int(y0 + EXTRA_ISLANDS[i][1] * sc)
            if self.antennas[i]:
                pygame.draw.polygon(cv, (120, 240, 255), [(mx_, my_ - 5), (mx_ + 4, my_ + 3), (mx_ - 4, my_ + 3)])
            else:
                pygame.draw.circle(cv, (255, 220, 90), (mx_, my_), 5, 1)
        pygame.draw.rect(cv, (140, 140, 150) if self.port_done else (255, 90, 70), (int(x0 + ENEMY_PORT[0] * sc) - 4, int(y0 + ENEMY_PORT[1] * sc) - 4, 8, 8), 2)
        for nst in self.nests:
            if nst['alive'] and (nst['seen'] or self.radar_t > 0):
                pygame.draw.rect(cv, (255, 90, 70), (int(x0 + nst['x'] * sc) - 2, int(y0 + nst['y'] * sc) - 2, 5, 5))
        if self.attack is not None and self.attack['kind'] == 'antenna' and int(self.t * 4) % 2 == 0:
            ac = self.attack['city']
            pygame.draw.circle(cv, (255, 60, 50), (int(x0 + ac['x'] * sc), int(y0 + ac['y'] * sc)), 9, 2)
        if self.convoy is not None:
            pygame.draw.rect(cv, (120, 255, 190), (int(x0 + self.convoy['x'] * sc) - 3, int(y0 + self.convoy['y'] * sc) - 3, 6, 6))
        if self.rescue is not None and int(self.t * 3) % 2 == 0:
            pygame.draw.circle(cv, (255, 230, 90), (int(x0 + self.rescue['x'] * sc), int(y0 + self.rescue['y'] * sc)), 6, 2)
        for q in self.crates:
            pygame.draw.circle(cv, (120, 255, 255), (int(x0 + q['x'] * sc), int(y0 + q['y'] * sc)), 2)
        for en in self.enemies:
            if en.get('sub') and not (dist(en['x'], en['y'], self.sx, self.sy) < 420 or self.radar_t > 0):
                continue
            if dist(en['x'], en['y'], self.sx, self.sy) < 1100 or en.get('is_boss') or self.radar_t > 0:
                boss = en.get('is_boss')
                pygame.draw.circle(cv, (255, 90, 220) if boss else (255, 70, 60), (int(x0 + en['x'] * sc), int(y0 + en['y'] * sc)), 5 if boss else 3)
        pygame.draw.rect(cv, (255, 255, 255), (x0 + self.cam[0] * sc, y0 + self.cam[1] * sc, W * sc, H * sc), 1)
        pygame.draw.circle(cv, (80, 255, 255), (int(x0 + self.sx * sc), int(y0 + self.sy * sc)), 4)
        self.text(cv, 'RADAR', self.f_s, (150, 190, 230), x0 + 4, y0 + 2)

    # ---- defensa
    def draw_defense(self, cv):
        d = self.d
        t = self.t
        cv.blit(self.sky, (0, 0))
        for x, y, ph in self.stars:
            v = int(120 + 100 * math.sin(t * 2 + ph))
            cv.set_at((x, y), (v, v, v))
        # mar
        cv.set_clip(pygame.Rect(0, HZ, W, H - HZ))
        self.draw_ocean(cv, 0, 0, t)
        self.dim(cv, 30, pygame.Rect(0, HZ, W, H - HZ))
        cv.set_clip(None)
        pygame.draw.line(cv, (255, 150, 90), (0, HZ), (W, HZ), 2)
        # skyline
        city = d['city']
        for b in city['sky']:
            bx = int(d['sky_x'] + b['x'])
            top = HZ - b['h']
            pygame.draw.rect(cv, (16, 20, 38), (bx, top, b['w'], b['h']))
            pygame.draw.rect(cv, (28, 34, 58), (bx, top, 3, b['h']))
            if not city['dead']:
                for j in range(top + 8, HZ - 8, 13):
                    for i in range(bx + 6, bx + b['w'] - 6, 9):
                        if (i * 7 + j * 13 + b['s']) % 5 < 2 and b['h'] > 24:
                            cv.fill((255, 224, 130), (i, j, 4, 6))
            if b['ant'] and b['h'] > 60:
                pygame.draw.line(cv, (16, 20, 38), (bx + b['w'] // 2, top), (bx + b['w'] // 2, top - 22), 2)
                if int(t * 2) % 2 == 0:
                    pygame.draw.circle(cv, (255, 60, 60), (bx + b['w'] // 2, top - 22), 3)
            # reflejo
            cv.fill((14, 16, 34), (bx, HZ + 2, b['w'], min(60, b['h'] // 2)), special_flags=pygame.BLEND_RGB_ADD)
        for f in d['fires']:
            glow(cv, f[0], f[1], 34 + 6 * math.sin(t * 20 + f[0]), (255, 120, 40), 0.9)
        # buque
        bob = math.sin(t * 1.6) * 3
        sx, sy = d['shipx'], d['shipy'] + bob
        cv.blit(self.side_ship, (sx - 150, sy - 70))
        for k in range(10):
            fx = sx - 140 + k * 29 + math.sin(t * 3 + k) * 4
            pygame.draw.line(cv, (200, 225, 245), (fx, sy + 36), (fx + 14, sy + 36), 2)
        gx, gy = sx + 82, sy - 6
        ang = bearing(self.aim[0] - gx, self.aim[1] - gy)
        self.blit_turret(cv, self.tur_p, gx, gy, ang)
        # misiles
        for m in d['missiles']:
            pts = m['trail']
            for i in range(1, len(pts)):
                k = i / len(pts)
                pygame.draw.line(cv, (int(255 * k), int(120 * k), int(80 * k)), pts[i - 1], pts[i], 2)
            glow(cv, m['x'], m['y'], 16, (255, 90, 60))
            pygame.draw.circle(cv, (255, 235, 210), (int(m['x']), int(m['y'])), 3)
        for it in d['inter']:
            pts = it['trail']
            for i in range(1, len(pts)):
                k = i / len(pts)
                pygame.draw.line(cv, (int(160 * k), int(255 * k), int(200 * k)), pts[i - 1], pts[i], 2)
            glow(cv, it['x'], it['y'], 12, (120, 255, 200))
            pygame.draw.circle(cv, (255, 255, 255), (int(it['x']), int(it['y'])), 2)
        for b in d['blasts']:
            rad = b['R'] * min(1.0, b['age'] / 0.28)
            life = 0.9 if not b['chain'] else 0.6
            k = 1 - b['age'] / life
            glow(cv, b['x'], b['y'], rad * 1.5, (255, 190, 100), k)
            draw_circ(cv, b['x'], b['y'], rad, (255, 240, 200), 200 * k)
            draw_circ(cv, b['x'], b['y'], rad, (255, 255, 255), 255 * k, 3)
        self.fx.draw(cv)
        # mira
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (120, 255, 190), (ax, ay), 18, 2)
        pygame.draw.circle(cv, (120, 255, 190), (ax, ay), 3)
        for dx, dy in ((-30, 0), (30, 0), (0, -30), (0, 30)):
            pygame.draw.line(cv, (120, 255, 190), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        # HUD
        self.draw_hud(cv, False)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        self.text(cv, city['name'], self.f_m, (255, 255, 255), W // 2, 16, 'c')
        col = (80, 230, 110) if city['hp'] > 60 else ((255, 200, 70) if city['hp'] > 30 else (240, 80, 70))
        self.bar(cv, W // 2 - 210, 44, 420, 26, city['hp'] / 100, col, 'CIUDAD %d%%' % city['hp'])
        left = len(d['queue']) + len(d['missiles'])
        self.text(cv, 'MISILES: %d' % left, self.f_m, (255, 160, 140), W - 20, 90, 'r')
        self.text(cv, 'Clic / ESPACIO: lanzar interceptor', self.f_s, (200, 220, 255), W // 2, H - 30, 'c')

    # ---- terrestre (infantería)
    def draw_cone(self, cv, x, y, h, rng, fov):
        if not (-rng < x < W + rng and -rng < y < H + rng):
            return
        if not hasattr(self, '_cone'):
            self._cone = pygame.Surface((2 * rng + 4, 2 * rng + 4), pygame.SRCALPHA)
        c = self._cone
        c.fill((0, 0, 0, 0))
        mid = rng + 2
        pts = [(mid, mid)]
        for i in range(13):
            ax, ay = vec(h - fov / 2 + fov * i / 12, rng)
            pts.append((mid + ax, mid + ay))
        pygame.draw.polygon(c, (255, 225, 110, 50 + int(16 * math.sin(self.t * 4))), pts)
        pygame.draw.lines(c, (255, 225, 110, 90), False, [pts[1], pts[0], pts[-1]], 1)
        cv.blit(c, (x - mid, y - mid))

    def blit_soldier(self, dst, key, x, y, ang, frame, hit=0.0, dead=False):
        draw_circ(dst, x + 4, y + 5, 14, (0, 0, 0), 70)
        r = pygame.transform.rotate(self.sol[key][frame % 4], -ang)
        if hit > 0 or dead:
            r = r.copy()
            if dead:
                r.fill((95, 95, 95), special_flags=pygame.BLEND_RGB_MULT)
            else:
                r.fill((110, 110, 110, 0), special_flags=pygame.BLEND_RGB_ADD)
        dst.blit(r, (int(x) - r.get_width() // 2, int(y) - r.get_height() // 2))

    def draw_boat(self, cv, x, y, a):
        h = math.radians(a)
        sn, cs = math.sin(h), math.cos(h)
        pts = [(x + sn * (-ly) + cs * lx, y - cs * (-ly) + sn * lx) for lx, ly in ((0, -30), (15, -14), (15, 22), (-15, 22), (-15, -14))]
        pygame.draw.polygon(cv, (70, 82, 92), pts)
        pygame.draw.polygon(cv, (128, 142, 152), [(x + (px - x) * .78, y + (py - y) * .78) for px, py in pts])
        pygame.draw.polygon(cv, (210, 222, 232), pts, 2)

    def draw_ground(self, cv):
        g = self.g
        p, city = g['p'], g['city']
        t = self.t
        cam = g['cam']
        cx_, cy_ = int(cam[0]), int(cam[1])
        self.draw_ocean(cv, cx_, cy_, t)
        lo = g['land_off']
        cv.blit(g['land'], (lo[0] - cx_, lo[1] - cy_))
        for x, y, r in g['decals']:
            draw_circ(cv, x - cx_, y - cy_, r, (28, 24, 20), 140)
        if g['mode'] == 'landing':
            if g['phase'] == 'result' and not g['fail']:
                k = clamp(g['ant_t'] / 1.8, 0, 1)
                bw, bh = self.antenna_big.get_size()
                hh = int(bh * k)
                if hh > 0:
                    cv.blit(self.antenna_big, (W // 2 - cx_ - bw // 2, H // 2 - cy_ + 20 - hh), area=pygame.Rect(0, bh - hh, bw, hh))
                if k >= 1:
                    for j in range(3):
                        ph = (t * 0.8 + j / 3) % 1
                        draw_circ(cv, W // 2 - cx_, H // 2 - cy_ - bh + 30, 14 + ph * 80, (120, 240, 255), 170 * (1 - ph), 2)
            self.draw_boat(cv, g['spawn'][0] - cx_, g['spawn'][1] + 58 - cy_, 0)
        for x, y, a, _t in g['boats']:
            self.draw_boat(cv, x - cx_, y - cy_, a)
        for c in g['corpses']:
            if c['age'] < 14:
                self.blit_soldier(cv, 'e_' + c['kind'], c['x'] - cx_, c['y'] - cy_, c['h'], 0, dead=True)
        for q in g['crates']:
            qx, qy = q['x'] - cx_, q['y'] - cy_
            glow(cv, qx, qy, 28, (120, 255, 150) if q['kind'] == 'med' else (255, 210, 70), 0.6)
            pygame.draw.rect(cv, (236, 240, 236) if q['kind'] == 'med' else (96, 110, 70), (qx - 9, qy - 9, 18, 18), border_radius=3)
            if q['kind'] == 'med':
                pygame.draw.rect(cv, (220, 50, 50), (qx - 6, qy - 2, 12, 4))
                pygame.draw.rect(cv, (220, 50, 50), (qx - 2, qy - 6, 4, 12))
            else:
                pygame.draw.circle(cv, (60, 76, 50), (int(qx), int(qy)), 5)
                pygame.draw.circle(cv, (255, 210, 70), (int(qx), int(qy)), 8, 2)
        for e in g['enemies']:
            if e['role'] == 'sentry' and e['state'] == 'hold':
                self.draw_cone(cv, e['x'] - cx_, e['y'] - cy_, e['h'], 340, 110)
        actors = [(e['y'], 'e', e) for e in g['enemies']] + [(p['y'], 'p', p)]
        for _, who, s in sorted(actors, key=lambda a: a[0]):
            sx, sy = s['x'] - cx_, s['y'] - cy_
            if not (-120 < sx < W + 120 and -120 < sy < H + 120):
                continue
            if who == 'e':
                self.blit_soldier(cv, 'e_' + s['kind'], sx, sy, s['h'], int(s['ph']) % 4, s['hit'])
                if s['state'] == 'hold' and s['role'] == 'guard':
                    self.text(cv, 'z', self.f_s, (200, 210, 230), sx + 12, sy - 40, shadow=False, alpha=150)
                if s['excl'] > 0:
                    self.text(cv, '!', self.f_l, (255, 70, 60), sx, sy - 66, 'c')
                if s['hp'] < s['max']:
                    pygame.draw.rect(cv, (8, 12, 24), (sx - 14, sy - 34, 28, 5))
                    pygame.draw.rect(cv, (240, 80, 70), (sx - 13, sy - 33, int(26 * s['hp'] / s['max']), 3))
                if s['tele'] > 0:
                    mx, my = vec(s['aimlock'], 44)
                    ex, ey = vec(s['aimlock'], 430)
                    if int(t * 24) % 2 == 0:
                        pygame.draw.line(cv, (255, 50, 50), (sx + mx, sy + my), (sx + ex, sy + ey), 1)
                    self.text(cv, '!', self.f_m, (255, 70, 60), sx, sy - 58, 'c')
                if s['flash'] > 0:
                    fx_, fy_ = vec(s['h'], 46)
                    glow(cv, sx + fx_, sy + fy_, 20, (255, 200, 120))
            elif s['dead']:
                self.blit_soldier(cv, 'p', sx, sy, s['h'], 0, dead=True)
            else:
                self.blit_soldier(cv, 'p', sx, sy, s['h'], int(s['ph']) % 4)
                if s['flash'] > 0:
                    fx_, fy_ = vec(s['h'], 46)
                    glow(cv, sx + fx_, sy + fy_, 22, (255, 230, 150))
        for b in g['bullets']:
            col = (255, 240, 150) if b['own'] == 'p' else (255, 150, 110)
            bx, by = b['x'] - cx_, b['y'] - cy_
            pygame.draw.line(cv, col, (bx, by), (bx - b['vx'] * 0.035, by - b['vy'] * 0.035), 2)
            glow(cv, bx, by, 7, col, 0.7)
        for n in g['nades']:
            k = n['t'] / n['T']
            x, y = lerp(n['x0'], n['x1'], k) - cx_, lerp(n['y0'], n['y1'], k) - cy_
            hh = math.sin(math.pi * k) * 34
            pulse = 0.5 + 0.5 * math.sin(t * 14)
            tx_, ty_ = n['x1'] - cx_, n['y1'] - cy_
            if n['own'] == 'e':
                draw_circ(cv, tx_, ty_, 62, (255, 60, 50), 28 + 30 * pulse)
                draw_circ(cv, tx_, ty_, 62, (255, 90, 70), 150 + 80 * pulse, 2)
            else:
                draw_circ(cv, tx_, ty_, 62, (255, 255, 255), 60, 1)
            draw_circ(cv, x + 2, y + 3, 5, (0, 0, 0), 80)
            pygame.draw.circle(cv, (58, 74, 48), (int(x), int(y - hh)), 5)
            pygame.draw.circle(cv, (110, 128, 92), (int(x - 1), int(y - hh - 1)), 2)
        self.fx.draw(cv, cx_, cy_)
        ax, ay = self.ground_aim()
        ax, ay = int(ax - cx_), int(ay - cy_)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 14, 2)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 2)
        for dx, dy in ((-24, 0), (24, 0), (0, -24), (0, 24)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        if g['hurt'] > 0:
            self.hurt_surf.set_alpha(int(255 * clamp(g['hurt'] * 2, 0, 1)))
            cv.blit(self.hurt_surf, (0, 0))
        if g['mode'] == 'landing':
            mr = 64
            mcx, mcy = W - 14 - mr, 104 + mr
            sc = mr / (g['R'] * 1.08)
            pygame.draw.circle(cv, (6, 12, 26), (mcx, mcy), mr + 3)
            pygame.draw.circle(cv, (24, 70, 96), (mcx, mcy), mr)
            pygame.draw.circle(cv, (86, 140, 80), (mcx, mcy), int(g['R'] * 0.96 * sc))
            for c in g['covers']:
                pygame.draw.circle(cv, (150, 140, 110), (int(mcx + (c['x'] - W / 2) * sc), int(mcy + (c['y'] - H / 2) * sc)), 2)
            pygame.draw.circle(cv, (196, 198, 194), (mcx, mcy), 4, 1)
            for e in g['enemies']:
                pygame.draw.circle(cv, (255, 70, 60) if e['state'] == 'combat' else (170, 70, 60),
                                   (int(mcx + (e['x'] - W / 2) * sc), int(mcy + (e['y'] - H / 2) * sc)), 3)
            pygame.draw.rect(cv, (220, 230, 240), (mcx + (cam[0] - W / 2) * sc, mcy + (cam[1] - H / 2) * sc, W * sc, H * sc), 1)
            pygame.draw.circle(cv, (90, 255, 255), (int(mcx + (p['x'] - W / 2) * sc), int(mcy + (p['y'] - H / 2) * sc)), 3)
            pygame.draw.circle(cv, (110, 150, 190), (mcx, mcy), mr + 3, 2)
        self.panel(cv, (14, H - 126, 330, 112), 160)
        self.bar(cv, 26, H - 116, 306, 24, p['hp'] / PLAYER_HP, (80, 220, 110) if p['hp'] > 40 else (240, 80, 70), 'SOLDADO %d' % max(0, p['hp']))
        if p['reload'] > 0:
            self.bar(cv, 26, H - 86, 306, 24, 1 - p['reload'] / 1.3, (255, 160, 70), 'RECARGANDO...')
        else:
            self.bar(cv, 26, H - 86, 306, 24, p['mag'] / 30, (255, 210, 70) if p['mag'] > 8 else (240, 80, 70), 'CARGADOR %d/30' % p['mag'])
        self.text(cv, 'GRANADAS', self.f_s, (235, 245, 255), 26, H - 54)
        for i in range(p['gren']):
            pygame.draw.circle(cv, (58, 74, 48), (140 + i * 24, H - 45), 8)
            pygame.draw.circle(cv, (150, 170, 120), (138 + i * 24, H - 48), 3)
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, (160, 200, 240), 26, 42)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        self.text(cv, city['name'], self.f_m, (255, 255, 255), W // 2, 16, 'c')
        if g['mode'] == 'landing':
            left = len(g['enemies'])
            self.bar(cv, W // 2 - 210, 44, 420, 26, left / max(1, g['total']), (240, 80, 70), 'ENEMIGOS %d/%d' % (left, g['total']))
        else:
            col = (80, 230, 110) if city['hp'] > 60 else ((255, 200, 70) if city['hp'] > 30 else (240, 80, 70))
            self.bar(cv, W // 2 - 210, 44, 420, 26, city['hp'] / 100, col, '%s %d%%' % ('ANTENA' if g['antenna'] is not None else 'CIUDAD', city['hp']))
            self.text(cv, 'ENEMIGOS: %d' % (len(g['queue']) + len(g['enemies'])), self.f_m, (255, 160, 140), W - 20, 90, 'r')
        self.text(cv, 'WASD mover | Clic disparar | R recargar | ESPACIO granada', self.f_s, (200, 220, 255), W - 14, H - 30, 'r')

    # ---- combate
    def draw_combat(self, cv):
        c = self.c
        p, e = c['p'], c['e']
        is_boss = c.get('is_boss', False)
        self.draw_ocean(cv, 0, 0, self.t)
        if is_boss:
            glow(cv, e['x'], e['y'], 90 + 20 * math.sin(self.t * 2), (255, 80, 200), 0.35)
        self.fx.draw(cv)
        # buques
        ekey, etur = ('b_hull', self.tur_b) if is_boss else (('s_hull', self.tur_e) if c['sub'] else ('e_hull', self.tur_e))
        for ship, key, tur in ((e, ekey, etur), (p, 'p_hull', self.tur_p)):
            alpha = 255
            if ship['sink'] is not None:
                k0, k1 = (1.8, 2.2) if (ship is e and is_boss) else (1.0, 1.4)
                alpha = int(255 * clamp(1 - (ship['sink'] - k0) / k1, 0, 1))
            if ship is e and c['nest']:
                spr = self.nest_gfx()
                spr.set_alpha(255 if ship['sink'] is None else 255 - int(150 * clamp(ship['sink'] / 2.0, 0, 1)))
                cv.blit(spr, (e['x'] - spr.get_width() // 2, e['y'] - spr.get_height() // 2))
                if ship['sink'] is None:
                    self.blit_turret(cv, self.tur_e, e['x'], e['y'] - 4, bearing(p['x'] - e['x'], p['y'] - e['y']))
                continue
            if alpha > 0:
                if key == 's_hull':
                    alpha = int(alpha * (1.0 if e['surf'] else 0.3))
                    if not e['surf']:
                        draw_circ(cv, e['x'], e['y'], 70 + 6 * math.sin(self.t * 3), (120, 230, 220), 40, 2)
                self.blit_ship(cv, key, ship['x'], ship['y'], ship['h'], alpha=alpha)
                if key == 's_hull':
                    continue
                if key == 'b_hull':
                    for mi, off in enumerate(BOSS_MOUNTS):
                        mx_, my_ = vec(ship['h'], off)
                        ang = bearing(p['x'] - (ship['x'] + mx_), p['y'] - (ship['y'] + my_))
                        self.blit_turret(cv, self.tur_b2 if mi == 2 else self.tur_b, ship['x'] + mx_, ship['y'] + my_, ang, alpha)
                    if ship['sink'] is None:
                        rx, ry = vec(ship['h'], 6)
                        ra = math.radians(self.t * 130)
                        pygame.draw.line(cv, (150, 235, 255), (ship['x'] + rx, ship['y'] + ry),
                                         (ship['x'] + rx + math.cos(ra) * 22, ship['y'] + ry + math.sin(ra) * 22), 2)
                        pygame.draw.circle(cv, (150, 235, 255), (int(ship['x'] + rx), int(ship['y'] + ry)), 4)
                        if int(self.t * 2) % 2 == 0:
                            glow(cv, ship['x'] + rx, ship['y'] + ry, 22, (255, 60, 50))
                    continue
                fx_, fy_ = vec(ship['h'], {'p_hull': 124, 'e_hull': 112}[key] * 0.23)
                if ship is p:
                    tx_, ty_ = self.combat_aim()
                else:
                    tx_, ty_ = p['x'], p['y']
                ang = bearing(tx_ - (ship['x'] + fx_), ty_ - (ship['y'] + fy_))
                self.blit_turret(cv, tur, ship['x'] + fx_, ship['y'] + fy_, ang, alpha)
        # misiles (vuelan en línea recta)
        for s in c['shells']:
            col = (255, 240, 160) if s['own'] == 'p' else (255, 150, 120)
            hx, hy = vec(s['ang'], 16)
            tx_, ty_ = vec(s['ang'], -16)
            glow(cv, s['x'] + tx_, s['y'] + ty_, 16, (255, 170, 70))
            pygame.draw.line(cv, (70, 74, 84), (s['x'] + tx_, s['y'] + ty_), (s['x'] + hx, s['y'] + hy), 8)
            pygame.draw.line(cv, (226, 230, 236), (s['x'] + tx_, s['y'] + ty_), (s['x'] + hx, s['y'] + hy), 5)
            pygame.draw.circle(cv, (230, 70, 56) if s['own'] == 'e' else (255, 210, 70), (int(s['x'] + hx), int(s['y'] + hy)), 5)
            fx2, fy2 = vec(s['ang'] + 90, 5)
            pygame.draw.line(cv, col, (s['x'] + tx_ + fx2, s['y'] + ty_ + fy2), (s['x'] + tx_ - fx2, s['y'] + ty_ - fy2), 2)
        # mira
        ax, ay = self.combat_aim()
        pygame.draw.line(cv, (120, 150, 190), (p['x'], p['y']), (ax, ay), 1)
        pygame.draw.circle(cv, (255, 230, 120), (int(ax), int(ay)), 16, 2)
        pygame.draw.circle(cv, (255, 230, 120), (int(ax), int(ay)), 2)
        for dx, dy in ((-26, 0), (26, 0), (0, -26), (0, 26)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        pygame.draw.circle(cv, (70, 100, 135), (int(p['x']), int(p['y'])), 650, 1)
        # HUD
        self.draw_hud(cv)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        if is_boss:
            self.text(cv, 'ACORAZADO %s' % c['name'], self.f_m, (255, 110, 220), W // 2, 16, 'c')
        elif c['nest']:
            self.text(cv, 'BATERÍA COSTERA', self.f_m, (255, 140, 120), W // 2, 16, 'c')
        elif c['sub']:
            self.text(cv, 'SUBMARINO - %s' % ('EMERGIDO: ¡DISPARALE!' if e['surf'] else 'SUMERGIDO (invulnerable)'), self.f_m,
                      (255, 220, 120) if e['surf'] else (120, 230, 220), W // 2, 16, 'c')
        else:
            self.text(cv, 'DESTRUCTOR ENEMIGO', self.f_m, (255, 140, 120), W // 2, 16, 'c')
        self.bar(cv, W // 2 - 210, 44, 420, 26, e['hp'] / e['max'], (240, 80, 70), 'BATERÍA' if c['nest'] else 'CASCO ENEMIGO')
        rl = 1 - clamp(p['cool'] / 0.9, 0, 1)
        pygame.draw.rect(cv, (8, 12, 24), (W // 2 - 60, H - 40, 120, 10))
        pygame.draw.rect(cv, (120, 255, 160) if rl >= 1 else (255, 200, 80), (W // 2 - 59, H - 39, int(118 * rl), 8))
        self.text(cv, 'Clic/ESPACIO: misil recto (adelantate al objetivo)  |  E huir', self.f_s, (200, 220, 255), W // 2, H - 64, 'c')

    # ---- batalla aérea
    def draw_aerial(self, cv):
        a = self.a
        p = a['p']
        t = self.t
        A = self.air
        self.draw_ocean(cv, 0, -a['scroll'], t)
        for c in a['clouds']:
            cs, sh = A['clouds'][c['i']]
            w2, h2 = int(cs.get_width() * c['s']), int(cs.get_height() * c['s'])
            sh2 = pygame.transform.smoothscale(sh, (w2, h2)) if c['s'] != 1 else sh
            sh2.set_alpha(55)
            cv.blit(sh2, (c['x'] - w2 // 2 + 70, c['y'] - h2 // 2 + 110))
        for isl in a['isl']:
            spr = A['isl'][isl['i']]
            cv.blit(spr, (isl['x'] - spr.get_width() // 2, isl['y'] - spr.get_height() // 2))
        for g in a['ground']:
            if g['kind'] == 'sam':
                cv.blit(A['gbase'], (g['x'] - A['gbase'].get_width() // 2, g['y'] - A['gbase'].get_height() // 2))
                self.blit_turret(cv, self.tur_e, g['x'], g['y'], g['ang'])
            else:
                self.blit_ship(cv, 'e_map', g['x'], g['y'], 180 + g['vx'] * 0.3)
        if not p['dead']:
            tx, ty = int(p['x']), int(max(60, p['y'] - 200))
            draw_circ(cv, tx, ty, 26, (255, 230, 170), 70, 1)
            pygame.draw.line(cv, (255, 230, 170), (tx - 8, ty), (tx + 8, ty), 1)
            pygame.draw.line(cv, (255, 230, 170), (tx, ty - 8), (tx, ty + 8), 1)
        for bm in a['bombs']:
            k = bm['t'] / bm['T']
            x, y = lerp(bm['x0'], bm['x1'], k), lerp(bm['y0'], bm['y1'], k)
            draw_circ(cv, x, y, 5, (0, 0, 0), 90)
            r = int(7 - 3 * k)
            pygame.draw.ellipse(cv, (36, 40, 46), (x - r, y - 40 * (1 - k) - r * 1.6, r * 2, r * 3.2))
            pygame.draw.ellipse(cv, (110, 118, 128), (x - r * 0.5, y - 40 * (1 - k) - r * 1.4, r, r * 1.4))
        for c in a['clouds']:
            cs, _ = A['clouds'][c['i']]
            w2, h2 = int(cs.get_width() * c['s']), int(cs.get_height() * c['s'])
            spr = pygame.transform.smoothscale(cs, (w2, h2)) if c['s'] != 1 else cs
            spr.set_alpha(215)
            cv.blit(spr, (c['x'] - w2 // 2, c['y'] - h2 // 2))
        for q in a['caps']:
            col = {'W': (255, 150, 50), 'H': (80, 220, 110), 'S': (90, 190, 255)}[q['kind']]
            glow(cv, q['x'], q['y'], 30, col, 0.7)
            pygame.draw.circle(cv, shade(col, -70), (int(q['x']), int(q['y'])), 14)
            pygame.draw.circle(cv, col, (int(q['x']), int(q['y'])), 12)
            pygame.draw.circle(cv, (255, 255, 255), (int(q['x'] - 4), int(q['y'] - 4)), 3)
            self.text(cv, q['kind'], self.f_s, (255, 255, 255), q['x'], q['y'] - 8, 'c', shadow=False)
        sh_off = (34, 52)

        def shadow(spr, x, y):
            sh = A['shadows'].get(id(spr))
            if sh is None:
                sh = A['shadows'][id(spr)] = make_shadow(spr)
            sh.set_alpha(75)
            cv.blit(sh, (x - sh.get_width() // 2 + sh_off[0], y - sh.get_height() // 2 + sh_off[1]))
        for f in a['foes']:
            spr = A[{'viper': 'viper', 'stealth': 'stealth', 'bomber': 'bomber'}[f['kind']]]
            shadow(spr, f['x'], f['y'])
            if f['hit'] > 0:
                spr = spr.copy()
                spr.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            cv.blit(spr, (f['x'] - spr.get_width() // 2, f['y'] - spr.get_height() // 2))
            if f['kind'] == 'bomber':
                for sx in (-1, 1):
                    glow(cv, f['x'] + sx * 22, f['y'] - 18, 20, (255, 140, 60), 0.7)
                pygame.draw.rect(cv, (8, 12, 24), (f['x'] - 40, f['y'] - 80, 80, 6))
                pygame.draw.rect(cv, (240, 80, 70), (f['x'] - 39, f['y'] - 79, int(78 * f['hp'] / f['max']), 4))
            else:
                glow(cv, f['x'], f['y'] - 36 if f['kind'] == 'viper' else f['y'] - 28, 12, (255, 150, 70), 0.6)
        b = a['boss']
        if b and not a['boss_dead']:
            spr = A['boss']
            shadow(spr, b['x'], b['y'])
            if b['hit'] > 0:
                spr = spr.copy()
                spr.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
            cv.blit(spr, (b['x'] - spr.get_width() // 2, b['y'] - spr.get_height() // 2))
            for sx in (-1, 1):
                glow(cv, b['x'] + sx * 36, b['y'] - 54, 28 + 4 * math.sin(t * 20), (255, 120, 60), 0.8)
        if not p['dead']:
            shadow(A['f16'], p['x'], p['y'])
            spr = A['f16']
            bank = clamp(p['vx'] / 320, -1, 1)
            if abs(bank) > 0.05:
                spr = pygame.transform.smoothscale(spr, (int(spr.get_width() * (1 - 0.22 * abs(bank))), spr.get_height()))
            blink = p['inv'] > 0 and int(t * 18) % 2 == 0
            fl_ = 14 + 8 * math.sin(t * 60)
            pygame.draw.polygon(cv, (255, 170, 60), [(p['x'] - 4, p['y'] + 42), (p['x'] + 4, p['y'] + 42), (p['x'], p['y'] + 42 + fl_ * 2)])
            pygame.draw.polygon(cv, (255, 245, 200), [(p['x'] - 2, p['y'] + 42), (p['x'] + 2, p['y'] + 42), (p['x'], p['y'] + 42 + fl_)])
            glow(cv, p['x'], p['y'] + 48, 26, (255, 160, 70), 0.8)
            if not blink:
                cv.blit(spr, (p['x'] - spr.get_width() // 2, p['y'] - spr.get_height() // 2))
            if p['shield'] > 0:
                pulse = 0.6 + 0.4 * math.sin(t * 10)
                draw_circ(cv, p['x'], p['y'], 54, (110, 210, 255), 50 * pulse + 20)
                draw_circ(cv, p['x'], p['y'], 54, (170, 235, 255), 200, 2)
        for bl in a['pbul']:
            pygame.draw.line(cv, (255, 244, 170), (bl['x'], bl['y']), (bl['x'] - bl['vx'] * 0.03, bl['y'] - bl['vy'] * 0.03), 3)
            pygame.draw.line(cv, (255, 255, 255), (bl['x'], bl['y']), (bl['x'] - bl['vx'] * 0.015, bl['y'] - bl['vy'] * 0.015), 1)
        for eb in a['ebul']:
            glow(cv, eb['x'], eb['y'], eb['r'] * 3, (255, 90, 60), 0.8)
            pygame.draw.circle(cv, (255, 120, 70), (int(eb['x']), int(eb['y'])), eb['r'])
            pygame.draw.circle(cv, (255, 235, 200), (int(eb['x']), int(eb['y'])), max(2, eb['r'] - 2))
        self.fx.draw(cv)
        self.panel(cv, (14, 12, 250, 56), 160)
        self.text(cv, 'PUNTOS %07d' % self.score, self.f_m, (255, 255, 255), 26, 18)
        self.text(cv, 'OLEADA %d/%d   REC %d' % (self.wave, WIN_WAVE, self.hiscore), self.f_s, (160, 200, 240), 26, 42)
        self.panel(cv, (14, H - 100, 330, 86), 160)
        self.bar(cv, 26, H - 90, 306, 24, p['hp'] / 100, (80, 220, 110) if p['hp'] > 35 else (240, 80, 70), 'F-16 %d%%' % max(0, p['hp']))
        self.text(cv, 'ARMA', self.f_s, (235, 245, 255), 26, H - 56)
        for i in range(4):
            pygame.draw.rect(cv, (255, 190, 70) if i < p['wl'] else (50, 56, 70), (86 + i * 26, H - 54, 20, 12), border_radius=3)
        self.text(cv, 'BOMBA', self.f_s, (235, 245, 255), 206, H - 56)
        rdy = 1 - clamp(p['bcd'] / 0.55, 0, 1)
        pygame.draw.rect(cv, (8, 12, 24), (270, H - 54, 60, 12))
        pygame.draw.rect(cv, (120, 255, 160) if rdy >= 1 else (255, 200, 80), (271, H - 53, int(58 * rdy), 10))
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        b = a['boss']
        if b and not a['boss_dead']:
            self.text(cv, 'COMANDANTE STEALTH', self.f_m, (255, 110, 90), W // 2, 16, 'c')
            self.bar(cv, W // 2 - 210, 44, 420, 26, b['hp'] / b['max'], (240, 80, 70), 'JEFE')
        else:
            self.text(cv, '¡BATALLA AÉREA!', self.f_m, (100, 180, 255), W // 2, 16, 'c')
            self.bar(cv, W // 2 - 210, 44, 420, 26, a['t'] / a['boss_t'], (100, 180, 255), 'AVANCE')
        if p['shield'] > 0:
            self.text(cv, 'ESCUDO %.0f' % p['shield'], self.f_s, (150, 225, 255), W - 20, 90, 'r')
        self.text(cv, 'WASD mover | ESPACIO/clic disparar | B/clic der. bomba', self.f_s, (210, 225, 255), W - 14, H - 30, 'r')


if __name__ == '__main__':
    Game().run()
