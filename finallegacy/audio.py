"""Síntesis de audio por código y reproductor de efectos/música."""
import array
import math
import pygame
import random
from .common import SR, clamp


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
