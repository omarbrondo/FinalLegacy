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
WORLD_W, WORLD_H = 2400, 1800
FPS = 60
SR = 22050
HZ = 590                      # horizonte en la escena de defensa
SKY_W = 640                   # ancho del skyline
WIN_WAVE = 6                  # oleadas para ganar
VMAX = 170.0                  # velocidad máx. del buque en el mapa (px/s)
BOSS_WAVE = 3                 # cada cuántas oleadas aparece jefe final
ANTENNA_ISLANDS = [0, 1, 2, 3, 4]   # islas donde se puede desembarcar e instalar antena (índices de EXTRA_ISLANDS)
ARENA_R = 330                  # radio de la isla en el combate de infantería
LANDING_ENEMIES = 10           # enemigos por desembarque
MAX_LANDING_ATTEMPTS = 3       # intentos máximos por isla

# (nombre, x, y, radio, semilla)
CITY_DEFS = [
    ("PUERTO BRONDO", 520, 430, 110, 11),
    ("NUEVA ESPERANZA", 1880, 470, 120, 22),
    ("BAHIA AZUL", 560, 1330, 115, 33),
    ("FORT LEGACY", 1800, 1320, 125, 44),
]
EXTRA_ISLANDS = [(1200, 900, 95, 5), (230, 900, 70, 6), (2170, 900, 75, 7),
                 (1200, 320, 85, 8), (1200, 1480, 90, 9)]


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
    'rifle': dict(hp=4, speed=58, range=310, dmg=7, rate=(0.9, 1.5), pts=100),
    'mg': dict(hp=7, speed=34, range=380, dmg=5, rate=(1.5, 2.3), pts=200),
    'gren': dict(hp=4, speed=46, range=380, dmg=0, rate=(3.4, 4.8), pts=150),
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
        allisl = [(x, y, r, s, True) for (_, x, y, r, s) in CITY_DEFS] + [(x, y, r, s, False) for (x, y, r, s) in EXTRA_ISLANDS]
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
        self.tur_p = make_turret(8, (70, 140, 170))
        self.tur_e = make_turret(8, (150, 60, 60))
        self.sol = {'p': make_soldier_frames('rifle', 'p')}
        for kd in ENEMY_TYPES:
            self.sol['e_' + kd] = make_soldier_frames(kd, 'e')
        hurt = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(70):
            pygame.draw.rect(hurt, (200, 0, 0, int(150 * (1 - i / 70) ** 2)), (i, i, W - 2 * i, H - 2 * i), 1)
        self.hurt_surf = hurt.convert_alpha()
        self.side_ship = self.make_side_ship()
        self.plane_p = self.make_plane(32, 48, (70, 140, 170))
        self.plane_e = self.make_plane(32, 48, (150, 60, 60))
        self.missile_gfx = self.make_missile()
        self.antenna_gfx = self.make_antenna()
        self.antenna_big = self.make_antenna(1.5)

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

    def make_plane(self, wd, ln, col):
        S = 3
        w, l = wd * S, ln * S
        s = pygame.Surface((w, l), pygame.SRCALPHA)
        fuselaje = [(w * .5, 0), (w * .65, l * .2), (w * .68, l * .5), (w * .65, l * .8), (w * .5, l), (w * .35, l * .8), (w * .32, l * .5), (w * .35, l * .2)]
        pygame.draw.polygon(s, shade(col, -40), fuselaje)
        pygame.draw.polygon(s, col, [(w * .48, l * .15), (w * .62, l * .35), (w * .63, l * .65), (w * .5, l * .9), (w * .38, l * .65), (w * .37, l * .35)])
        alas = [(w * .2, l * .45), (w * .35, l * .4), (w * .5, l * .42), (w * .65, l * .4), (w * .8, l * .45), (w * .75, l * .55), (w * .5, l * .58), (w * .25, l * .55)]
        pygame.draw.polygon(s, shade(col, -20), alas)
        pygame.draw.polygon(s, shade(col, 20), alas, 2)
        for x in (w * .3, w * .7):
            pygame.draw.circle(s, (50, 50, 50), (int(x), int(l * .5)), int(w * .1))
            pygame.draw.circle(s, shade(col, -80), (int(x), int(l * .5)), int(w * .08))
        pygame.draw.circle(s, (255, 220, 150), (int(w * .5), int(l * .15)), int(w * .07))
        pygame.draw.line(s, shade(col, 60), (int(w * .5), int(l * .6)), (int(w * .5), int(l * .85)), int(w * .04))
        return pygame.transform.smoothscale(s, (wd, ln))

    def make_missile(self):
        s = pygame.Surface((8, 32), pygame.SRCALPHA)
        pygame.draw.polygon(s, (255, 200, 100), [(4, 0), (7, 8), (7, 24), (4, 32), (1, 24), (1, 8)])
        pygame.draw.polygon(s, (255, 255, 255), [(3, 4), (5, 4), (5, 28), (3, 28)])
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
        self.sx, self.sy = 1200.0, 760.0
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
        self.strike_t = 30.0
        self.warned = False
        self.strike_city = None
        self.strike_kind = 'missile'
        self.strike_n = 0
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

    def spawn_wave(self):
        n = min(2 + self.wave, 7)
        for _ in range(n):
            x = y = 0
            for _ in range(60):
                x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
                if dist(x, y, self.sx, self.sy) > 700 and not self.on_land(x, y, 90):
                    break
            mh = 10 + 2 * (self.wave - 1)
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=mh, max=mh, state='patrol',
                                     wp=self.rand_wp(), cool=0.0, is_boss=False))
        if self.wave % BOSS_WAVE == 0:
            x = y = 0
            for _ in range(60):
                x, y = random.uniform(150, WORLD_W - 150), random.uniform(150, WORLD_H - 150)
                if dist(x, y, self.sx, self.sy) > 900 and not self.on_land(x, y, 120):
                    break
            boss_hp = 35 + 15 * ((self.wave // BOSS_WAVE) - 1)
            self.enemies.append(dict(x=x, y=y, h=random.uniform(0, 360), v=0.0, hp=boss_hp, max=boss_hp,
                                     state='patrol', wp=self.rand_wp(), cool=0.0, is_boss=True,
                                     burst=[], orb=1, orb_t=3.0))

    def go(self, state):
        self.state = state
        self.fade = 1.0
        pygame.mouse.set_visible(state not in ('defense', 'combat', 'aerial', 'ground'))
        self.audio.music({'title': 'calm', 'map': 'calm', 'defense': 'battle', 'combat': 'battle',
                          'aerial': 'battle', 'ground': 'battle', 'gameover': None}[state])
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
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F1:
                self.crt_on = not self.crt_on
            elif e.key == pygame.K_m:
                self.audio.toggle_mute()
            elif e.key in (pygame.K_p, pygame.K_ESCAPE) and self.state in ('map', 'defense', 'combat', 'ground'):
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
            elif self.state == 'map' and e.key == pygame.K_l and not self.paused:
                island = self.nearest_landing_island()
                if island:
                    self.start_landing(island[0])
            elif self.state == 'aerial' and e.key == pygame.K_SPACE and not self.paused:
                self.fire_aerial()
            elif self.state == 'combat' and not self.paused:
                if e.key == pygame.K_SPACE:
                    self.fire_shell()
                elif e.key == pygame.K_e:
                    self.flee()
                elif e.key == pygame.K_c:
                    self.cyber_attack()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.state == 'ground' and not self.paused:
            self.throw_grenade_p()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.paused:
            if self.state == 'title' or self.state == 'gameover':
                self.start_game()
            elif self.state == 'defense':
                self.fire_interceptor()
            elif self.state == 'aerial':
                self.fire_aerial()
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
            self.sv = min(VMAX, self.sv + 85 * dt)
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
            if d < 78 and en['cool'] <= 0:
                return self.start_combat(en)
        # cajas
        self.crate_t -= dt
        if self.crate_t <= 0 and len(self.crates) < 3:
            self.crate_t = 22.0
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
        if alive and self.strike_t <= 4.0 and not self.warned:
            self.warned = True
            self.strike_city = random.choice(alive)
            self.strike_n += 1
            rand = random.random()
            if self.strike_n == 2 or (self.strike_n > 2 and rand < 0.3):
                self.strike_kind = 'ground'
            elif rand < 0.35:
                self.strike_kind = 'aerial'
            else:
                self.strike_kind = 'missile'
            self.audio.play('alarm')
            if self.strike_kind == 'ground':
                self.banner('¡INVASIÓN ANFIBIA!', 'Desembarco en ' + self.strike_city['name'], (255, 150, 60), 3.8)
            elif self.strike_kind == 'aerial':
                self.banner('¡ATAQUE AÉREO!', 'Cazas enemigos en aproximación', (150, 100, 255), 3.8)
            else:
                self.banner('¡ALERTA DE MISILES!', 'Objetivo: ' + self.strike_city['name'], (255, 80, 70), 3.8)
        if self.warned and self.strike_t <= 0:
            if self.strike_kind == 'ground':
                self.start_ground(self.strike_city)
            elif self.strike_kind == 'aerial':
                self.start_aerial()
            else:
                self.start_defense(self.strike_city)
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
        self.audio.play('win', .7)
        self.banner('OLEADA %d' % self.wave, 'Bonus +%d  |  Ciudades reparadas  |  +12 munición' % bonus, (120, 255, 160), 3.6)
        self.spawn_wave()

    def ai_map(self, en, dt):
        en['cool'] = max(0.0, en['cool'] - dt)
        d = dist(self.sx, self.sy, en['x'], en['y'])
        is_boss = en.get('is_boss', False)
        chase_dist = 520 if is_boss else 430

        if en['state'] == 'patrol' and d < chase_dist and en['cool'] <= 0:
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
            sp = (120 + 8 * self.wave) if is_boss else (96 + 5 * self.wave)
        else:
            tx, ty = en['wp']
            sp = 60 if is_boss else 52
            if dist(en['x'], en['y'], tx, ty) < 50:
                en['wp'] = self.rand_wp()
        vx, vy = tx - en['x'], ty - en['y']
        n = math.hypot(vx, vy) or 1
        vx, vy = vx / n, vy / n
        for ix, iy, ir, sd in self.islands:
            dd = dist(en['x'], en['y'], ix, iy) or 1.0
            lim = coast_r(ir, sd, math.atan2(en['y'] - iy, en['x'] - ix), 1.1) + (130 if is_boss else 110)
            if dd < lim:
                k = (lim - dd) / (130 if is_boss else 110)
                vx += (en['x'] - ix) / dd * k * 2.4
                vy += (en['y'] - iy) / dd * k * 2.4
        want = bearing(vx, vy)
        en['h'] = (en['h'] + clamp(angle_diff(en['h'], want), -30 * dt if is_boss else -45 * dt, 30 * dt if is_boss else 45 * dt)) % 360
        en['v'] += (sp - en['v']) * min(1, dt * 1.5)
        dx, dy = vec(en['h'], en['v'] * dt)
        en['x'] = clamp(en['x'] + dx, 40, WORLD_W - 40)
        en['y'] = clamp(en['y'] + dy, 40, WORLD_H - 40)
        if random.random() < dt * (18 if is_boss else 14):
            bx, by = vec(en['h'], -30 if is_boss else -24)
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
        self.strike_t = max(22.0, random.uniform(30, 42) - self.wave * 2)
        if all(c['dead'] for c in self.cities):
            return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

    # ---------------------------------------------------------- COMBATE
    def start_combat(self, en):
        self.fx = Particles()
        self.enemy_ref = en
        is_boss = en.get('is_boss', False)
        antennas_active = sum(1 for i, active in self.antennas.items() if active)
        self.c = dict(
            p=dict(x=W / 2, y=H - 170.0, h=0.0, v=0.0, cool=0.0, wake=0.0, sink=None),
            e=dict(x=W / 2 + random.uniform(-150, 150), y=170.0, h=180.0, v=40.0, cool=1.5 if is_boss else 2.0,
                   orb=random.choice([-1, 1]), orb_t=5.0, burst=[], wake=0.0, sink=None, hp=en['hp'], max=en['max']),
            shells=[], t=0.0, is_boss=is_boss, cyber_available=(is_boss and antennas_active > 0),
            cyber_used=False, cyber_cooldown=0.0)
        self.aim = [W / 2, 300.0]
        self.go('combat')
        if is_boss:
            msg = 'Este es un combate peligroso. Derrótalo para avanzar'
            if antennas_active > 0:
                msg += ' | C: ciberataque (%d antenas)' % antennas_active
            self.banner('¡JEFE FINAL!', msg, (255, 50, 50), 3.2)
        else:
            self.banner('¡COMBATE NAVAL!', 'W/S/A/D: navegar  |  Mouse+Clic: disparar  |  E: huir', (255, 150, 90), 3.0)

    def cyber_attack(self):
        c = self.c
        if not c.get('cyber_available', False) or c.get('cyber_used', False) or c['e']['sink'] is not None:
            return
        c['cyber_used'] = True
        e = c['e']
        dmg = 20 + 5 * (self.wave // BOSS_WAVE)
        e['hp'] -= dmg
        self.audio.play('ping')
        self.shake = max(self.shake, 15)
        self.pop('CIBERATAQUE\n-%d' % dmg, e['x'], e['y'] - 30, (100, 200, 255))
        for _ in range(15):
            a = random.uniform(0, 6.28)
            self.fx.add('spark', e['x'], e['y'], math.cos(a) * 200, math.sin(a) * 200, 0.4, col=(100, 200, 255), drag=1.8)
        self.banner('CIBERATAQUE', '-%d daño al enemigo' % dmg, (100, 200, 255), 2.0)

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
        d = dist(p['x'], p['y'], tx, ty)
        T = clamp(d / 380, 0.7, 2.0)
        accurate = random.random() < 0.65
        c['shells'].append(dict(x0=p['x'], y0=p['y'], x1=tx, y1=ty, t=0.0, T=T, own='p', accurate=accurate))
        self.audio.play('cannon', .8)
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
        for ship in (p, e):
            if ship['x'] < 50 or ship['x'] > W - 50 or ship['y'] < 60 or ship['y'] > H - 60:
                ship['x'], ship['y'] = clamp(ship['x'], 50, W - 50), clamp(ship['y'], 60, H - 60)
                ship['v'] *= 0.6
        self.fuel = max(0.0, self.fuel - abs(p['v']) / 125 * 0.35 * dt)
        self.audio.engine_vol(abs(p['v']) / 125 * 0.9 + 0.1)
        p['cool'] = max(0.0, p['cool'] - dt)
        # IA enemiga
        if e['sink'] is None:
            dxp, dyp = p['x'] - e['x'], p['y'] - e['y']
            dd = math.hypot(dxp, dyp) or 1
            to_p = bearing(dxp, dyp)
            e['orb_t'] -= dt
            if e['orb_t'] <= 0:
                e['orb'] *= -1
                e['orb_t'] = random.uniform(4, 8)
            if dd > 420:
                want = to_p
            elif dd < 260:
                want = to_p + 180
            else:
                want = to_p + 90 * e['orb']
            if e['x'] < 110 or e['x'] > W - 110 or e['y'] < 110 or e['y'] > H - 110:
                want = bearing(W / 2 - e['x'], H / 2 - e['y'])
            e['h'] = (e['h'] + clamp(angle_diff(e['h'], want), -48 * dt, 48 * dt)) % 360
            e['v'] += ((62 + 5 * self.wave) - e['v']) * min(1, dt * 1.5)
            ex, ey = vec(e['h'], e['v'] * dt)
            e['x'] += ex
            e['y'] += ey
            e['cool'] -= dt
            is_boss = self.c.get('is_boss', False)
            if e['cool'] <= 0 and p['sink'] is None:
                if is_boss:
                    e['cool'] = random.uniform(1.2, 1.8)
                    self.enemy_fire(1.0)
                    e['burst'].append(0.4)
                else:
                    e['cool'] = random.uniform(2.1, 3.0) * max(0.55, 1 - 0.07 * self.wave)
                    self.enemy_fire(1.0)
                    if self.wave >= 3:
                        e['burst'].append(0.35)
            e['burst'] = [b - dt for b in e['burst']]
            if e['burst'] and e['burst'][0] <= 0:
                e['burst'].pop(0)
                self.enemy_fire(1.0)
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
        for s in c['shells'][:]:
            s['t'] += dt
            if s['t'] >= s['T']:
                c['shells'].remove(s)
                self.shell_land(s)
        # hundimientos
        for ship, key in ((e, 'e'), (p, 'p')):
            if ship['sink'] is not None:
                ship['sink'] += dt
                ship['v'] *= 0.97
                if int(ship['sink'] * 5) != int((ship['sink'] - dt) * 5):
                    self.fx.explode(ship['x'] + random.uniform(-16, 16), ship['y'] + random.uniform(-40, 40), 0.9)
                    self.audio.play('boom_s', .6)
                    self.shake = max(self.shake, 7)
        if e['sink'] is None and e['hp'] <= 0:
            e['sink'] = 0.0
            self.audio.play('boom_l')
            self.fx.explode(e['x'], e['y'], 1.8, True)
        if p['sink'] is None and self.hull <= 0:
            p['sink'] = 0.0
            self.audio.play('boom_l')
            self.fx.explode(p['x'], p['y'], 1.8, True)
        self.fx.update(dt)
        if e['sink'] is not None and e['sink'] > 2.4:
            self.add_score(500 + 100 * self.wave)
            self.ammo = min(40, self.ammo + 5)
            self.toast('¡Destructor hundido! +%d  (+5 munición)' % (500 + 100 * self.wave), (120, 255, 160))
            if self.enemy_ref in self.enemies:
                self.enemies.remove(self.enemy_ref)
            if self.hull <= 0:
                return self.game_over('Tu buque no sobrevivió al combate')
            self.go('map')
        elif p['sink'] is not None and p['sink'] > 2.6:
            self.game_over('Tu buque fue hundido en combate')

    def enemy_fire(self, _):
        c = self.c
        p, e = c['p'], c['e']
        d = dist(p['x'], p['y'], e['x'], e['y'])
        T = clamp(d / 320, 1.0, 2.2)
        vx, vy = vec(p['h'], p['v'])
        spread = max(26, 80 - 8 * self.wave)
        a, r = random.uniform(0, 6.28), random.uniform(0, spread)
        tx = clamp(p['x'] + vx * T + math.cos(a) * r, 20, W - 20)
        ty = clamp(p['y'] + vy * T + math.sin(a) * r, 20, H - 20)
        accurate = random.random() < 0.6
        c['shells'].append(dict(x0=e['x'], y0=e['y'], x1=tx, y1=ty, t=0.0, T=T, own='e', accurate=accurate))
        self.audio.play('cannon', .5)
        self.fx.add('glow', e['x'], e['y'], life=.2, r0=20, r1=40, col=(255, 160, 120))

    def shell_land(self, s):
        c = self.c
        p, e = c['p'], c['e']
        x, y = s['x1'], s['y1']
        tgt = e if s['own'] == 'p' else p

        if not s.get('accurate', True):
            x += random.uniform(-120, 120)
            y += random.uniform(-100, 100)

        d = dist(x, y, tgt['x'], tgt['y'])
        if d <= 54 and tgt['sink'] is None:
            full = d <= 24
            if s['own'] == 'p':
                e['hp'] -= 3 if full else 1.5
                self.pop('-%s' % ('3' if full else '1.5'), x, y - 20, (255, 255, 160))
            else:
                dmg = 24 if full else 12
                self.hull -= dmg
                self.pop('-%d CASCO' % dmg, x, y - 20, (255, 110, 100))
                self.shake = max(self.shake, 12)
            self.fx.explode(x, y, 1.0 if full else 0.7)
            self.audio.play('hit')
        else:
            self.fx.splash(x, y, 1.0)
            self.audio.play('splash', .6)

    # ---------------------------------------------------------- BATALLA AÉREA
    def start_aerial(self):
        self.fx = Particles()
        n = min(6 + self.wave, 16)
        self.a = dict(
            p=dict(x=W / 2, y=H - 80.0, h=0.0, v=0.0, cool=0.0, hp=100.0, sink=None),
            enemies=[], missiles=[], t=0.0, total=n, killed=0, phase='play', pt=0.0,
            queue=sorted(random.uniform(0.4, 2.0 + n * 0.6) for _ in range(n)))
        self.aim = [W / 2, 200.0]
        self.go('aerial')
        self.banner('¡BATALLA AÉREA!', 'Mouse: apuntar  |  Clic/ESPACIO: disparar  |  W/S: mover', (100, 180, 255), 3.0)

    def spawn_aerial_enemy(self):
        a = self.a
        y = random.uniform(80, 200)
        x = random.choice([-40, W + 40])
        hp = 3 + self.wave // 2
        a['enemies'].append(dict(x=x, y=y, vx=random.uniform(80 + self.wave * 8, 140 + self.wave * 12) * (1 if x < W / 2 else -1),
                                 h=180 if x < W / 2 else 0, hp=hp, max=hp, cool=random.uniform(0.8, 1.8)))

    def fire_aerial(self):
        a = self.a
        p = a['p']
        if p['sink'] is not None or p['cool'] > 0:
            return
        if self.ammo <= 0:
            self.audio.play('empty')
            self.toast('¡Sin munición!', (255, 90, 80))
            return
        self.ammo -= 1
        p['cool'] = 0.4
        angle = bearing(self.aim[0] - p['x'], self.aim[1] - p['y'])
        directions = [0, 30, -30, 60, -60]
        for d in directions[:min(3, (self.wave // 2) + 1)]:
            ang = angle + d
            vx, vy = vec(ang, 500)
            a['missiles'].append(dict(x=p['x'], y=p['y'], vx=vx, vy=vy, life=2.0, own='p'))
        self.audio.play('launch', .8)
        self.fx.add('glow', p['x'], p['y'], life=.15, r0=16, r1=32, col=(120, 200, 255))

    def upd_aerial(self, dt):
        a = self.a
        p = a['p']
        keys = pygame.key.get_pressed()

        a['t'] += dt
        p['cool'] = max(0.0, p['cool'] - dt)
        p['hp'] = max(0.0, p['hp'] - random.random() * dt * 2 if p['hp'] > 0 else 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            p['y'] = max(40, p['y'] - 300 * dt)
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            p['y'] = min(H - 40, p['y'] + 300 * dt)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            p['x'] = max(20, p['x'] - 300 * dt)
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            p['x'] = min(W - 20, p['x'] + 300 * dt)

        while a['queue'] and a['queue'][0] <= a['t']:
            a['queue'].pop(0)
            self.spawn_aerial_enemy()

        for e in a['enemies'][:]:
            e['x'] += e['vx'] * dt
            e['y'] += random.uniform(-1, 1) * 30 * dt
            e['cool'] -= dt
            if e['cool'] <= 0:
                e['cool'] = random.uniform(1.0, 2.0)
                vx, vy = vec(bearing(p['x'] - e['x'], p['y'] - e['y']), 300)
                a['missiles'].append(dict(x=e['x'], y=e['y'], vx=vx, vy=vy, life=2.5, own='e'))
                self.audio.play('launch', .3)

            if e['x'] < -60 or e['x'] > W + 60 or e['y'] < 0 or e['y'] > H:
                a['enemies'].remove(e)

        for m in a['missiles'][:]:
            m['x'] += m['vx'] * dt
            m['y'] += m['vy'] * dt
            m['life'] -= dt

            if m['own'] == 'p':
                hit = None
                for e in a['enemies']:
                    if dist(m['x'], m['y'], e['x'], e['y']) < 16:
                        hit = e
                        break
                if hit:
                    hit['hp'] -= 1
                    self.fx.add('glow', m['x'], m['y'], life=.25, r0=8, r1=20, col=(255, 180, 100))
                    self.audio.play('boom_s', .4)
                    a['missiles'].remove(m)
                    if hit['hp'] <= 0:
                        a['enemies'].remove(hit)
                        a['killed'] += 1
                        pts = 150
                        self.add_score(pts)
                        self.pop('+%d' % pts, hit['x'], hit['y'])
                        self.fx.explode(hit['x'], hit['y'], 0.9)
                    continue
            else:
                if p['sink'] is None and dist(m['x'], m['y'], p['x'], p['y']) < 18:
                    p['hp'] -= 15
                    self.shake = max(self.shake, 6)
                    self.audio.play('hit', .6)
                    self.fx.add('glow', m['x'], m['y'], life=.3, r0=12, r1=28, col=(255, 140, 80))
                    a['missiles'].remove(m)
                    continue

            if m['life'] <= 0 or m['x'] < -40 or m['x'] > W + 40 or m['y'] < -40 or m['y'] > H + 40:
                if m in a['missiles']:
                    a['missiles'].remove(m)

        self.fx.update(dt)

        if p['sink'] is None and p['hp'] <= 0:
            p['sink'] = 0.0
            self.fx.explode(p['x'], p['y'], 1.5, True)
            self.audio.play('boom_l')
            self.shake = 14
            a['phase'] = 'result'
            a['pt'] = -2.0
            self.banner('¡AVIÓN DERRIBADO!', 'Derrota', (255, 80, 70), 3.0)

        if a['phase'] == 'play' and not a['queue'] and not a['enemies'] and not a['missiles']:
            a['phase'] = 'result'
            a['pt'] = 0.0
            bonus = 500 + 100 * self.wave
            self.add_score(bonus)
            self.audio.play('win', .7)
            self.banner('¡VICTORIA AÉREA!', 'Bajas: %d   Bonus +%d' % (a['killed'], bonus), (120, 255, 160), 2.8)

        if a['phase'] == 'result':
            a['pt'] += dt
            if a['pt'] > 2.8:
                self.warned = False
                self.strike_t = max(22.0, random.uniform(30, 42) - self.wave * 2)
                self.go('map')

    # ---------------------------------------------------------- COMBATE DE INFANTERÍA
    def isl_name(self, i):
        return 'ISLA %d' % (i + 1)

    def make_ground(self, seed, R, city_seed=None):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        self.paint_island(s, W / 2, H / 2, R, seed, True)
        if city_seed is not None:
            cs = self.make_city(int(R * 0.7), city_seed, False)
            s.blit(cs, (W // 2 - cs.get_width() // 2, H // 2 - cs.get_height() // 2))
        else:
            cx, cy = W // 2, H // 2
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
        return s

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

    def init_ground(self, mode, seed, city, covers_n, avoid, spawn, kinds, queue=None, island_idx=None):
        R = ARENA_R
        land = self.make_ground(seed, R, seed if mode == 'invasion' else None)
        covers = self.gen_covers(seed, R, covers_n, avoid + [(spawn[0], spawn[1], 90)])
        for c in covers:
            draw_cover(land, c)
        self.fx = Particles()
        self.g = dict(mode=mode, city=city, R=R, seed=seed, land=land.convert_alpha(), covers=covers,
                      angs=[random.uniform(0, 6.28) for _ in range(3)], queue=queue or [], enemies=[], bullets=[],
                      nades=[], corpses=[], decals=[], boats=[], crates=[], t=0.0, total=len(kinds), kills=0,
                      phase='play', pt=0.0, city0=city['hp'], fail=False, island_idx=island_idx, hurt=0.0,
                      ant_t=0.0, spawn=spawn,
                      p=dict(x=float(spawn[0]), y=float(spawn[1]), h=0.0, vx=0.0, vy=0.0, hp=100.0, mag=30, reload=0.0,
                             cd=0.0, gren=4, gcd=0.0, ph=0.0, flash=0.0, bloom=0.0, dead=False, dead_t=0.0))
        self.aim = [W / 2, 200.0]
        self.go('ground')
        return covers

    def new_soldier(self, kind, x, y, h, state, mode, cover=None):
        hp = ENEMY_TYPES[kind]['hp'] + self.wave // 2
        return dict(x=x, y=y, h=h, h0=h, kind=kind, hp=float(hp), max=float(hp), cd=random.uniform(0.6, 1.6),
                    state=state, mode=mode, cover=cover, ph=0.0, ph0=random.uniform(0, 6.28), flash=0.0, hit=0.0,
                    burst=0, bcd=0.0, tele=0.0, aimlock=h, strafe=random.choice((-1, 1)), strafe_t=random.uniform(1, 3))

    def start_landing(self, island_idx):
        x, y, r, s = EXTRA_ISLANDS[island_idx]
        if self.landing_attempts[island_idx] >= MAX_LANDING_ATTEMPTS:
            self.toast('Sin intentos de desembarco en esta isla', (255, 140, 90))
            return
        self.landing_attempts[island_idx] += 1
        n = LANDING_ENEMIES
        n_mg, n_gr = max(1, n // 5), max(1, n // 5)
        kinds = ['mg'] * n_mg + ['gren'] * n_gr + ['rifle'] * (n - n_mg - n_gr)
        sy = H / 2 + coast_r(ARENA_R, s, math.pi / 2, 0.84)
        spawn = (W / 2, sy)
        city = dict(name=self.isl_name(island_idx), x=x, y=y, r=r, hp=100.0, dead=False, seed=s)
        covers = self.init_ground('landing', s, city, 10, [(W / 2, H / 2, 80)], spawn, kinds, island_idx=island_idx)
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
            lim = coast_r(ARENA_R, s, math.atan2(ey - H / 2, ex - W / 2), 0.9)
            if d > lim:
                ex, ey = W / 2 + (ex - W / 2) / d * lim, H / 2 + (ey - H / 2) / d * lim
            mode = 'pusher' if kd == 'rifle' and random.random() < 0.35 else 'defender'
            e = self.new_soldier(kd, ex, ey, bearing(spawn[0] - ex, spawn[1] - ey), 'hold', mode, ci)
            g['enemies'].append(e)
        g['total'] = len(g['enemies'])
        left = MAX_LANDING_ATTEMPTS - self.landing_attempts[island_idx]
        self.banner('¡DESEMBARCO EN %s!' % self.isl_name(island_idx),
                    'Eliminá a los %d soldados para instalar la antena  |  Intentos restantes: %d' % (n, left),
                    (100, 180, 255), 4.0)

    def start_ground(self, city):
        n = min(8 + 3 * self.wave, 26)
        n_mg = min(n // 6, 1 + self.wave // 2)
        n_gr = min(n // 5, 1 + self.wave // 2)
        kinds = ['mg'] * n_mg + ['gren'] * n_gr + ['rifle'] * (n - n_mg - n_gr)
        random.shuffle(kinds)
        queue = sorted([(random.uniform(0.5, 6 + n * 1.1), k, random.randrange(3)) for k in kinds], key=lambda q: q[0])
        spawn = (W / 2, H / 2 + 175)
        self.init_ground('invasion', city['seed'], city, 7, [(W / 2, H / 2, 150)], spawn, kinds, queue)
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

    def ground_aim(self):
        p = self.g['p']
        ax, ay = self.aim
        if not self.mouse_moved:
            fx, fy = vec(p['h'], 320)
            ax, ay = p['x'] + fx, p['y'] + fy
        return clamp(ax, 10, W - 10), clamp(ay, 10, H - 10)

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

    def alert(self, e):
        if e['state'] == 'combat':
            return
        e['state'] = 'combat'
        for o in self.g['enemies']:
            if o['state'] == 'hold' and dist(o['x'], o['y'], e['x'], e['y']) < 170:
                o['state'] = 'combat'

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
            if e['state'] == 'hold' and dist(e['x'], e['y'], p['x'], p['y']) < 340:
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
        tx = clamp(p['x'] + p['vx'] * 0.5 + random.uniform(-24, 24), 60, W - 60)
        ty = clamp(p['y'] + p['vy'] * 0.5 + random.uniform(-24, 24), 60, H - 60)
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
            dmg = int(38 * (1 - 0.6 * d / R))
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
        self.pop('-%d' % dmg, p['x'], p['y'] - 22, (255, 110, 100))

    def kill_ground_enemy(self, e):
        g = self.g
        if e not in g['enemies']:
            return
        g['enemies'].remove(e)
        g['kills'] += 1
        pts = ENEMY_TYPES[e['kind']]['pts']
        self.add_score(pts)
        self.pop('+%d' % pts, e['x'], e['y'] - 18)
        g['corpses'].append(dict(x=e['x'], y=e['y'], h=e['h'] + random.uniform(-60, 60), kind=e['kind'], age=0.0))
        g['corpses'] = g['corpses'][-30:]
        self.fx.add('glow', e['x'], e['y'], life=.25, r0=8, r1=22, col=(255, 160, 90))
        for _ in range(6):
            a = random.uniform(0, 6.28)
            self.fx.add('spark', e['x'], e['y'], math.cos(a) * 110, math.sin(a) * 110, 0.35, col=(255, 200, 120), drag=2)
        if random.random() < 0.18:
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
        if e['state'] == 'hold':
            e['h'] = (e['h0'] + 38 * math.sin(g['t'] * 0.7 + e['ph0'])) % 360
            if alive and dp < 235:
                self.alert(e)
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
                    self.enemy_shoot(e, to_p, max(2.5, 6.5 - 0.5 * wv) + dp * 0.008, 340, T['dmg'])
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
                    e['tele'] = 0.55
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
            if b['life'] <= 0 or not (-40 < b['x'] < W + 40 and -40 < b['y'] < H + 40):
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
                    p['hp'] = min(100.0, p['hp'] + 30)
                    self.pop('+30 SALUD', q['x'], q['y'] - 16, (120, 255, 150))
                else:
                    p['gren'] = min(6, p['gren'] + 2)
                    self.pop('+2 GRANADAS', q['x'], q['y'] - 16, (255, 230, 90))
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
            self.banner('¡CIUDAD CAPTURADA!', city['name'], (255, 70, 60), 3.0)
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
                self.banner('¡ISLA ASEGURADA!', 'Bajas enemigas: %d   Bonus +%d' % (g['kills'], bonus), (120, 255, 160), 2.8)
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
                self.banner('ANTENA OPERATIVA', '%d/%d antenas  |  Ciberataque disponible contra el jefe' % (n, len(self.antennas)),
                            (120, 220, 255), 3.4)
        else:
            if g['fail'] and not city['dead']:
                city['hp'] = max(0.0, city['hp'] - 30)
                if city['hp'] <= 0:
                    city['dead'] = True
            self.warned = False
            self.strike_t = max(22.0, random.uniform(30, 42) - self.wave * 2)
            if all(c['dead'] for c in self.cities):
                return self.game_over('Todas las ciudades fueron destruidas')
        self.go('map')

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
        self.panel(cv, (W // 2 - 380, 335, 760, 215), 170)
        lines = ['MAPA   W/S acelerar-frenar   A/D girar   R (en puerto) reabastecer',
                 'DEFENSA   Mouse o flechas apuntan   Clic/ESPACIO lanzan interceptor',
                 'COMBATE   Mouse apunta y dispara (el proyectil tarda: ¡adelantate!)',
                 '          Esquivá los círculos rojos   E: huir',
                 'TIERRA   WASD soldado   Clic disparar   R recargar   ESPACIO granada   L: desembarcar',
                 'P pausa   M sonido   F1 efecto CRT']
        for i, ln in enumerate(lines):
            self.text(cv, ln, self.f_s, (220, 232, 255), W // 2 - 360, 350 + i * 30)
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
        for q in self.crates:
            sx, sy = q['x'] - cx, q['y'] - cy + math.sin(self.t * 2 + q['x']) * 3
            col = {'ammo': (255, 210, 70), 'fuel': (90, 230, 120), 'repair': (240, 240, 255)}[q['kind']]
            glow(cv, sx, sy, 34, col, 0.6)
            pygame.draw.rect(cv, (120, 84, 50), (sx - 11, sy - 11, 22, 22), border_radius=3)
            pygame.draw.rect(cv, col, (sx - 11, sy - 11, 22, 22), 2, border_radius=3)
            self.text(cv, {'ammo': 'M', 'fuel': 'C', 'repair': '+'}[q['kind']], self.f_s, (255, 255, 255), sx, sy - 9, 'c', shadow=False)
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
        for en in self.enemies:
            self.blit_ship(cv, 'e_map', en['x'], en['y'], en['h'], cx, cy)
            if en['state'] == 'chase':
                draw_circ(cv, en['x'] - cx, en['y'] - cy, 44, (255, 80, 70), 120, 2)
        self.blit_ship(cv, 'p_map', self.sx, self.sy, self.sh, cx, cy)
        # HUD
        self.draw_hud(cv)
        self.draw_cities_hud(cv)
        self.draw_minimap(cv)
        thr = 1 - clamp(self.strike_t / 30.0, 0, 1)
        self.text(cv, 'AMENAZA ENEMIGA', self.f_s, (255, 190, 170), W - 296 + 8, 76)
        self.bar(cv, W - 296, 96, 282, 14, thr, (255, 90 + int(100 * (1 - thr)), 60), '')
        dk = self.nearest_dock()
        if dk:
            self.text(cv, 'PUERTO: mantené R para reabastecer y reparar',
                      self.f_m, (140, 255, 210), W // 2, H - 60, 'c')
        else:
            island = self.nearest_landing_island()
            if island:
                island_idx, x, y, r, s = island
                attempts = self.landing_attempts[island_idx]
                if attempts >= MAX_LANDING_ATTEMPTS:
                    self.text(cv, '%s: sin intentos de desembarco' % self.isl_name(island_idx),
                              self.f_m, (255, 140, 110), W // 2, H - 60, 'c')
                else:
                    self.text(cv, '%s CERCANA: presioná L para desembarcar (10 soldados enemigos)  |  Intentos: %d/%d' %
                              (self.isl_name(island_idx), attempts, MAX_LANDING_ATTEMPTS),
                              self.f_m, (100, 180, 255), W // 2, H - 60, 'c')
            elif self.fuel <= 0:
                self.text(cv, 'SIN COMBUSTIBLE', self.f_m, (255, 90, 80), W // 2, H - 60, 'c')
        if self.warned and int(self.t * 4) % 2 == 0:
            pygame.draw.rect(cv, (255, 40, 40), (0, 0, W, H), 8)

    def draw_minimap(self, cv):
        mw, mh = 190, 143
        x0, y0 = W - mw - 14, H - mh - 14
        self.panel(cv, (x0 - 4, y0 - 4, mw + 8, mh + 8), 190)
        sc = mw / WORLD_W
        pygame.draw.rect(cv, (12, 40, 78), (x0, y0, mw, mh))
        for ix, iy, ir, _sd in self.islands:
            pygame.draw.circle(cv, (70, 120, 70), (int(x0 + ix * sc), int(y0 + iy * sc)), max(2, int(ir * sc * 1.1)))
        for c in self.cities:
            pygame.draw.rect(cv, (90, 90, 90) if c['dead'] else (255, 220, 80), (x0 + c['x'] * sc - 3, y0 + c['y'] * sc - 3, 6, 6))
        for i in ANTENNA_ISLANDS:
            mx_, my_ = int(x0 + EXTRA_ISLANDS[i][0] * sc), int(y0 + EXTRA_ISLANDS[i][1] * sc)
            if self.antennas[i]:
                pygame.draw.polygon(cv, (120, 240, 255), [(mx_, my_ - 5), (mx_ + 4, my_ + 3), (mx_ - 4, my_ + 3)])
            else:
                pygame.draw.circle(cv, (255, 220, 90), (mx_, my_), 5, 1)
        for q in self.crates:
            pygame.draw.circle(cv, (120, 255, 255), (int(x0 + q['x'] * sc), int(y0 + q['y'] * sc)), 2)
        for en in self.enemies:
            if dist(en['x'], en['y'], self.sx, self.sy) < 1100:
                pygame.draw.circle(cv, (255, 70, 60), (int(x0 + en['x'] * sc), int(y0 + en['y'] * sc)), 3)
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
        self.draw_ocean(cv, 0, 0, t)
        cv.blit(g['land'], (0, 0))
        for x, y, r in g['decals']:
            draw_circ(cv, x, y, r, (28, 24, 20), 140)
        if g['mode'] == 'landing':
            if g['phase'] == 'result' and not g['fail']:
                k = clamp(g['ant_t'] / 1.8, 0, 1)
                bw, bh = self.antenna_big.get_size()
                hh = int(bh * k)
                if hh > 0:
                    cv.blit(self.antenna_big, (W // 2 - bw // 2, H // 2 + 20 - hh), area=pygame.Rect(0, bh - hh, bw, hh))
                if k >= 1:
                    for j in range(3):
                        ph = (t * 0.8 + j / 3) % 1
                        draw_circ(cv, W // 2, H // 2 - bh + 30, 14 + ph * 80, (120, 240, 255), 170 * (1 - ph), 2)
            self.draw_boat(cv, g['spawn'][0], g['spawn'][1] + 58, 0)
        for x, y, a, _t in g['boats']:
            self.draw_boat(cv, x, y, a)
        for c in g['corpses']:
            if c['age'] < 14:
                self.blit_soldier(cv, 'e_' + c['kind'], c['x'], c['y'], c['h'], 0, dead=True)
        for q in g['crates']:
            glow(cv, q['x'], q['y'], 28, (120, 255, 150) if q['kind'] == 'med' else (255, 210, 70), 0.6)
            pygame.draw.rect(cv, (236, 240, 236) if q['kind'] == 'med' else (96, 110, 70), (q['x'] - 9, q['y'] - 9, 18, 18), border_radius=3)
            if q['kind'] == 'med':
                pygame.draw.rect(cv, (220, 50, 50), (q['x'] - 6, q['y'] - 2, 12, 4))
                pygame.draw.rect(cv, (220, 50, 50), (q['x'] - 2, q['y'] - 6, 4, 12))
            else:
                pygame.draw.circle(cv, (60, 76, 50), (int(q['x']), int(q['y'])), 5)
                pygame.draw.circle(cv, (255, 210, 70), (int(q['x']), int(q['y'])), 8, 2)
        actors = [(e['y'], 'e', e) for e in g['enemies']] + [(p['y'], 'p', p)]
        for _, who, s in sorted(actors, key=lambda a: a[0]):
            if who == 'e':
                self.blit_soldier(cv, 'e_' + s['kind'], s['x'], s['y'], s['h'], int(s['ph']) % 4, s['hit'])
                if s['state'] == 'hold':
                    self.text(cv, 'z', self.f_s, (200, 210, 230), s['x'] + 12, s['y'] - 40, shadow=False, alpha=150)
                if s['hp'] < s['max']:
                    pygame.draw.rect(cv, (8, 12, 24), (s['x'] - 14, s['y'] - 34, 28, 5))
                    pygame.draw.rect(cv, (240, 80, 70), (s['x'] - 13, s['y'] - 33, int(26 * s['hp'] / s['max']), 3))
                if s['tele'] > 0:
                    mx, my = vec(s['aimlock'], 44)
                    ex, ey = vec(s['aimlock'], 430)
                    if int(t * 24) % 2 == 0:
                        pygame.draw.line(cv, (255, 50, 50), (s['x'] + mx, s['y'] + my), (s['x'] + ex, s['y'] + ey), 1)
                    self.text(cv, '!', self.f_m, (255, 70, 60), s['x'], s['y'] - 58, 'c')
                if s['flash'] > 0:
                    fx_, fy_ = vec(s['h'], 46)
                    glow(cv, s['x'] + fx_, s['y'] + fy_, 20, (255, 200, 120))
            elif s['dead']:
                self.blit_soldier(cv, 'p', s['x'], s['y'], s['h'], 0, dead=True)
            else:
                self.blit_soldier(cv, 'p', s['x'], s['y'], s['h'], int(s['ph']) % 4)
                if s['flash'] > 0:
                    fx_, fy_ = vec(s['h'], 46)
                    glow(cv, s['x'] + fx_, s['y'] + fy_, 22, (255, 230, 150))
        for b in g['bullets']:
            col = (255, 240, 150) if b['own'] == 'p' else (255, 150, 110)
            pygame.draw.line(cv, col, (b['x'], b['y']), (b['x'] - b['vx'] * 0.035, b['y'] - b['vy'] * 0.035), 2)
            glow(cv, b['x'], b['y'], 7, col, 0.7)
        for n in g['nades']:
            k = n['t'] / n['T']
            x, y = lerp(n['x0'], n['x1'], k), lerp(n['y0'], n['y1'], k)
            hh = math.sin(math.pi * k) * 34
            pulse = 0.5 + 0.5 * math.sin(t * 14)
            if n['own'] == 'e':
                draw_circ(cv, n['x1'], n['y1'], 62, (255, 60, 50), 28 + 30 * pulse)
                draw_circ(cv, n['x1'], n['y1'], 62, (255, 90, 70), 150 + 80 * pulse, 2)
            else:
                draw_circ(cv, n['x1'], n['y1'], 62, (255, 255, 255), 60, 1)
            draw_circ(cv, x + 2, y + 3, 5, (0, 0, 0), 80)
            pygame.draw.circle(cv, (58, 74, 48), (int(x), int(y - hh)), 5)
            pygame.draw.circle(cv, (110, 128, 92), (int(x - 1), int(y - hh - 1)), 2)
        self.fx.draw(cv)
        ax, ay = self.ground_aim()
        ax, ay = int(ax), int(ay)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 14, 2)
        pygame.draw.circle(cv, (255, 230, 120), (ax, ay), 2)
        for dx, dy in ((-24, 0), (24, 0), (0, -24), (0, 24)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        if g['hurt'] > 0:
            self.hurt_surf.set_alpha(int(255 * clamp(g['hurt'] * 2, 0, 1)))
            cv.blit(self.hurt_surf, (0, 0))
        self.panel(cv, (14, H - 126, 330, 112), 160)
        self.bar(cv, 26, H - 116, 306, 24, p['hp'] / 100, (80, 220, 110) if p['hp'] > 35 else (240, 80, 70), 'SOLDADO %d%%' % max(0, p['hp']))
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
            self.bar(cv, W // 2 - 210, 44, 420, 26, city['hp'] / 100, col, 'CIUDAD %d%%' % city['hp'])
            self.text(cv, 'ENEMIGOS: %d' % (len(g['queue']) + len(g['enemies'])), self.f_m, (255, 160, 140), W - 20, 90, 'r')
        self.text(cv, 'WASD mover | Mouse apuntar | Clic disparar | R recargar | ESPACIO/clic der. granada | las coberturas frenan balas',
                  self.f_s, (200, 220, 255), W // 2, H - 30, 'c')

    # ---- combate
    def draw_combat(self, cv):
        c = self.c
        p, e = c['p'], c['e']
        is_boss = c.get('is_boss', False)
        self.draw_ocean(cv, 0, 0, self.t)
        # anillos de impacto
        for s in c['shells']:
            k = s['t'] / s['T']
            col = (120, 255, 160) if s['own'] == 'p' else (255, 80, 70)
            draw_circ(cv, s['x1'], s['y1'], 54, col, 70 + 60 * math.sin(self.t * 12), 2)
            draw_circ(cv, s['x1'], s['y1'], max(4, 54 * (1 - k)), col, 220, 3)
        if is_boss:
            glow(cv, e['x'], e['y'], 80 + 20 * math.sin(self.t * 2), (255, 80, 60), 0.4)
        self.fx.draw(cv)
        # buques
        for ship, key, tur, tcol in ((e, 'e_hull', self.tur_e, None), (p, 'p_hull', self.tur_p, None)):
            alpha = 255
            if ship['sink'] is not None:
                alpha = int(255 * clamp(1 - (ship['sink'] - 1.0) / 1.4, 0, 1))
            if alpha > 0:
                self.blit_ship(cv, key, ship['x'], ship['y'], ship['h'], alpha=alpha)
                fx_, fy_ = vec(ship['h'], 124 * 0.23 if key == 'p_hull' else 112 * 0.23)
                if ship is p:
                    tx_, ty_ = self.combat_aim()
                else:
                    tx_, ty_ = p['x'], p['y']
                ang = bearing(tx_ - (ship['x'] + fx_), ty_ - (ship['y'] + fy_))
                self.blit_turret(cv, tur, ship['x'] + fx_, ship['y'] + fy_, ang, alpha)
        # proyectiles en el aire
        for s in c['shells']:
            k = s['t'] / s['T']
            x = lerp(s['x0'], s['x1'], k)
            y = lerp(s['y0'], s['y1'], k)
            h = math.sin(math.pi * k)
            draw_circ(cv, x, y, 5, (0, 0, 0), 70)
            sz = 4 + 3 * h
            col = (255, 240, 160) if s['own'] == 'p' else (255, 150, 120)
            glow(cv, x, y - 26 * h, 16, col)
            pygame.draw.circle(cv, (255, 255, 255), (int(x), int(y - 26 * h)), int(sz))
            if random.random() < 0.6:
                self.fx.add('smoke', x, y - 26 * h, 0, 0, 0.6, 2, 6, (180, 180, 180))
        # mira
        ax, ay = self.combat_aim()
        pygame.draw.circle(cv, (255, 230, 120), (int(ax), int(ay)), 16, 2)
        pygame.draw.circle(cv, (255, 230, 120), (int(ax), int(ay)), 2)
        for dx, dy in ((-26, 0), (26, 0), (0, -26), (0, 26)):
            pygame.draw.line(cv, (255, 230, 120), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        pygame.draw.circle(cv, (70, 100, 135), (int(p['x']), int(p['y'])), 650, 1)
        # HUD
        self.draw_hud(cv)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        if is_boss:
            self.text(cv, '¡JEFE FINAL!', self.f_m, (255, 80, 60), W // 2, 16, 'c')
        else:
            self.text(cv, 'DESTRUCTOR ENEMIGO', self.f_m, (255, 140, 120), W // 2, 16, 'c')
        self.bar(cv, W // 2 - 210, 44, 420, 26, e['hp'] / e['max'], (240, 80, 70), 'CASCO ENEMIGO')
        rl = 1 - clamp(p['cool'] / 0.9, 0, 1)
        pygame.draw.rect(cv, (8, 12, 24), (W // 2 - 60, H - 40, 120, 10))
        pygame.draw.rect(cv, (120, 255, 160) if rl >= 1 else (255, 200, 80), (W // 2 - 59, H - 39, int(118 * rl), 8))
        if c.get('cyber_available', False):
            cyber_text = 'C: ciberataque' if not c.get('cyber_used', False) else 'Ciberataque (usado)'
            self.text(cv, 'Clic/ESPACIO disparar  |  E huir  |  ' + cyber_text, self.f_s, (200, 220, 255), W // 2, H - 64, 'c')
        else:
            self.text(cv, 'Clic/ESPACIO disparar  |  E huir', self.f_s, (200, 220, 255), W // 2, H - 64, 'c')

    # ---- batalla aérea
    def draw_aerial(self, cv):
        a = self.a
        p = a['p']
        for y in range(H):
            k = y / H
            c = (int(10 + k * 40), int(20 + k * 60), int(80 + k * 60))
            pygame.draw.line(cv, c, (0, y), (W, y))
        px = (self.t * 30) % 256
        for x in range(int(-px), W, 256):
            for y in range(0, H, 60):
                pts = [(x + 20, y + 20), (x + 60, y), (x + 100, y + 20), (x + 80, y + 50), (x + 40, y + 40)]
                pygame.draw.polygon(cv, (180, 200, 220), pts)
                pygame.draw.polygon(cv, (200, 220, 240), pts, 1)
        for y in range(0, H, 40):
            pygame.draw.line(cv, (40, 70, 140), (0, y), (W, y), 1)
        for x in range(0, W, 60):
            pygame.draw.line(cv, (40, 70, 140), (x, 0), (x, H), 1)
        for e in a['enemies']:
            r = pygame.transform.rotate(self.plane_e, -e['h'])
            cv.blit(r, (int(e['x']) - r.get_width() // 2, int(e['y']) - r.get_height() // 2))
            if e['hp'] < e['max']:
                pygame.draw.rect(cv, (8, 12, 24), (int(e['x']) - 16, int(e['y']) - 28, 32, 5))
                pygame.draw.rect(cv, (240, 80, 70), (int(e['x']) - 15, int(e['y']) - 27, int(30 * e['hp'] / e['max']), 3))
        for m in a['missiles']:
            h = math.atan2(m['vy'], m['vx']) * 180 / math.pi
            r = pygame.transform.rotate(self.missile_gfx, -h)
            col = (100, 200, 255) if m['own'] == 'p' else (255, 150, 100)
            glow(cv, m['x'], m['y'], 10, col, 0.6)
            cv.blit(r, (int(m['x']) - r.get_width() // 2, int(m['y']) - r.get_height() // 2))
        if p['sink'] is None or p['sink'] < 0.2:
            r = pygame.transform.rotate(self.plane_p, -p['h'])
            cv.blit(r, (int(p['x']) - r.get_width() // 2, int(p['y']) - r.get_height() // 2))
        ax, ay = int(self.aim[0]), int(self.aim[1])
        pygame.draw.circle(cv, (100, 255, 200), (ax, ay), 16, 2)
        pygame.draw.circle(cv, (100, 255, 200), (ax, ay), 3)
        for dx, dy in ((-30, 0), (30, 0), (0, -30), (0, 30)):
            pygame.draw.line(cv, (100, 255, 200), (ax + dx // 2, ay + dy // 2), (ax + dx, ay + dy), 2)
        self.draw_hud(cv, False)
        self.panel(cv, (W // 2 - 230, 12, 460, 70), 170)
        self.text(cv, '¡BATALLA AÉREA!', self.f_m, (100, 180, 255), W // 2, 16, 'c')
        self.bar(cv, W // 2 - 210, 44, 420, 26, p['hp'] / 100, (80, 220, 110) if p['hp'] > 35 else (240, 80, 70), 'AVIÓN %d%%' % max(0, p['hp']))
        left = len(a['queue']) + len(a['enemies'])
        self.text(cv, 'ENEMIGOS: %d' % left, self.f_m, (255, 160, 140), W - 20, 90, 'r')
        self.text(cv, 'W/S/A/D mover | Clic/ESPACIO disparar (múltiples direcciones)', self.f_s, (200, 220, 255), W // 2, H - 30, 'c')


if __name__ == '__main__':
    Game().run()
