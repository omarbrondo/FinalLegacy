"""Compositor de música por código: una pieza distinta por modo y por oleada (necesita numpy).

Cada pieza combina batería, bajo, acordes, arpegio y melodía; cambia el tempo, la tonalidad, el modo musical y la
densidad según la oleada, y la melodía se genera con una semilla propia de (modo, oleada).
"""
import random

try:
    import numpy as np
except ImportError:
    np = None

MODES = {
    'aeolian': [0, 2, 3, 5, 7, 8, 10], 'dorian': [0, 2, 3, 5, 7, 9, 10], 'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10], 'ionian': [0, 2, 4, 5, 7, 9, 11], 'harmonic': [0, 2, 3, 5, 7, 8, 11],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
}

# bpm, tonalidad (MIDI), modos por tramo de oleadas, progresiones (grados, 0 = tónica), batería, bajo, extras
SPECS = {
    'title': dict(bpm=96, root=45, modes=('aeolian', 'aeolian', 'harmonic'), prog=([0, 5, 2, 6], [0, 3, 5, 4]), drums='soft',
                  bass='sustain', pad=1, arp='8th', lead='sparse', leadw='tri'),
    'map': dict(bpm=88, root=50, modes=('dorian', 'mixolydian', 'aeolian'), prog=([0, 3, 4, 3], [0, 5, 3, 4]), drums='none',
                bass='sustain', pad=1, arp='8th', lead='sparse', leadw='sine'),
    'upgrade': dict(bpm=80, root=52, modes=('ionian', 'lydian', 'ionian'), prog=([0, 4, 5, 3], [0, 3, 4, 4]), drums='soft',
                    bass='sustain', pad=1, arp='8th', lead='sparse', leadw='tri'),
    'defense': dict(bpm=138, root=45, modes=('phrygian', 'harmonic', 'phrygian'), prog=([0, 0, 1, 0], [0, 5, 1, 4]),
                    drums='indus', bass='pulse', pad=1, arp='16th', lead='active', leadw='saw'),
    'combat': dict(bpm=120, root=43, modes=('aeolian', 'dorian', 'phrygian'), prog=([0, 5, 2, 6], [0, 0, 3, 4]), drums='rock',
                   bass='rf', pad=0, arp=None, lead='active', leadw='saw'),
    'boss': dict(bpm=146, root=41, modes=('phrygian', 'harmonic', 'phrygian'), prog=([0, 1, 0, 6], [0, 0, 1, 5]), drums='indus',
                 bass='gallop', pad=1, arp='16th', lead='active', leadw='saw'),
    'bossf': dict(bpm=162, root=41, modes=('phrygian', 'harmonic', 'phrygian'), prog=([0, 1, 0, 6], [0, 6, 1, 5]), drums='break',
                  bass='gallop', pad=1, arp='16th', lead='active', leadw='saw'),
    'aerial': dict(bpm=152, root=48, modes=('mixolydian', 'aeolian', 'dorian'), prog=([0, 5, 3, 4], [0, 6, 5, 4]), drums='four',
                   bass='eighth', pad=0, arp='16th', lead='active', leadw='square'),
    'ground': dict(bpm=106, root=46, modes=('dorian', 'aeolian', 'phrygian'), prog=([0, 0, 3, 4], [0, 5, 3, 1]), drums='march',
                   bass='pulse', pad=1, arp=None, lead='sparse', leadw='saw'),
    'tank': dict(bpm=110, root=40, modes=('phrygian', 'aeolian', 'harmonic'), prog=([0, 0, 1, 0], [0, 6, 5, 4]), drums='indus',
                 bass='gallop', pad=1, arp=None, lead='sparse', leadw='square'),
    'port': dict(bpm=132, root=45, modes=('mixolydian', 'dorian', 'aeolian'), prog=([0, 6, 3, 4], [0, 3, 6, 4]), drums='break',
                 bass='walk', pad=0, arp='8th', lead='active', leadw='square'),
    'heli': dict(bpm=126, root=43, modes=('aeolian', 'dorian', 'harmonic'), prog=([0, 5, 6, 4], [0, 3, 5, 6]), drums='four',
                 bass='eighth', pad=1, arp='8th', lead='sparse', leadw='saw'),
    'beach': dict(bpm=118, root=43, modes=('dorian', 'aeolian', 'phrygian'), prog=([0, 0, 3, 4], [0, 5, 3, 1]), drums='rock', bass='pulse',
                  pad=1, arp=None, lead='active', leadw='saw'),
    'infil': dict(bpm=84, root=45, modes=('aeolian', 'phrygian', 'aeolian'), prog=([0, 5, 2, 6], [0, 3, 5, 4]), drums='soft', bass='sustain',
                  pad=1, arp='8th', lead='sparse', leadw='tri'),
    'holdout': dict(bpm=148, root=44, modes=('phrygian', 'harmonic', 'phrygian'), prog=([0, 1, 0, 6], [0, 0, 1, 5]), drums='indus',
                    bass='gallop', pad=1, arp='16th', lead='active', leadw='saw'),
    'extract': dict(bpm=164, root=47, modes=('harmonic', 'phrygian', 'harmonic'), prog=([0, 6, 5, 4], [0, 1, 0, 6]), drums='break',
                    bass='eighth', pad=0, arp='16th', lead='active', leadw='square'),
    'hack': dict(bpm=124, root=45, modes=('aeolian', 'phrygian', 'aeolian'), prog=([0, 0, 5, 4], [0, 3, 0, 6]), drums='four',
                 bass='eighth', pad=0, arp='16th', lead='sparse', leadw='square'),
}

DRUMS = {
    'none': dict(k='', s='', h=''),
    'soft': dict(k='1000000010000000', s='', h='0010001000100010'),
    'rock': dict(k='1000001010100000', s='0000100000001000', h='1010101010101010'),
    'four': dict(k='1000100010001000', s='0000100000001000', h='0010001000100010'),
    'break': dict(k='1000000110100000', s='0000100000001001', h='1011101110111011'),
    'march': dict(k='1000000010000000', s='0010001000100101', h='0000000000000000'),
    'indus': dict(k='1010001010100010', s='0000100000001000', h='0101010101010101'),
}


def _tone(sr, f, dur, wave, decay=3.0, duty=0.5, vib=0.0, atk=0.005, rel=0.02, f_end=None):
    n = max(8, int(dur * sr))
    t = np.arange(n, dtype=np.float32) / sr
    freq = f + (f_end - f) * (t / dur) if f_end else np.full(n, f, dtype=np.float32)
    if vib:
        freq = freq * (1 + vib * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t * 3))
    p = (np.cumsum(freq) / sr) % 1.0
    if wave == 'sine':
        w = np.sin(2 * np.pi * p)
    elif wave == 'tri':
        w = 4 * np.abs(p - 0.5) - 1
    elif wave == 'saw':
        w = 2 * p - 1
    else:
        w = np.where(p < duty, 1.0, -1.0)
    env = np.exp(-decay * t / dur) * np.minimum(1, t / atk) * np.minimum(1, np.maximum(0, (dur - t)) / rel)
    return (w * env).astype(np.float32)


def _noise(sr, dur, decay=6.0, hp=False):
    n = max(8, int(dur * sr))
    x = np.random.uniform(-1, 1, n).astype(np.float32)
    if hp:
        x = np.diff(x, prepend=0).astype(np.float32) * 0.6
    return x * np.exp(-decay * np.arange(n, dtype=np.float32) / n)


def _kick(sr):
    k = _tone(sr, 150, 0.22, 'sine', 5.0, f_end=42, rel=0.01)
    c = _noise(sr, 0.01, 2.0) * 0.3
    k[:len(c)] += c
    return k


def _snare(sr):
    x = _noise(sr, 0.17, 6.0) * 0.55
    b = _tone(sr, 190, 0.1, 'tri', 6.0, f_end=140) * 0.35
    x[:len(b)] += b
    return x


def _hat(sr, open_=False):
    return _noise(sr, 0.16 if open_ else 0.04, 5.0 if open_ else 12.0, hp=True) * 0.5


def _tom(sr, f):
    return _tone(sr, f, 0.25, 'sine', 5.0, f_end=f * 0.6) * 0.8


def _lowpass(x, k):
    return np.convolve(x, np.ones(k, dtype=np.float32) / k, mode='same')


class _Mix:
    def __init__(self, sr, seconds):
        self.sr = sr
        self.buf = np.zeros(int(sr * seconds) + sr, dtype=np.float32)

    def add(self, t0, arr, vol=1.0):
        i = int(t0 * self.sr)
        if i >= len(self.buf):
            return
        j = min(len(self.buf), i + len(arr))
        self.buf[i:j] += arr[:j - i] * vol


def compose(ctx, wave, sr):
    """Devuelve un arreglo float32 mono (loop) con la pieza de ese modo y oleada."""
    spec = SPECS.get(ctx) or SPECS['map']
    wave = max(1, int(wave))
    rng = random.Random(hash((ctx, wave)) & 0xFFFFFF)
    np.random.seed(rng.randrange(1 << 30))
    bpm = spec['bpm'] + 3 * min(wave - 1, 5)
    root = spec['root'] + (0, 2, 5, -2, 3, 7)[(wave - 1) % 6]
    mode = MODES[spec['modes'][min(2, (wave - 1) // 2)]]
    level = 1 + (wave >= 3) + (wave >= 5)
    beat = 60.0 / bpm
    bar = beat * 4
    bars = 32
    m = _Mix(sr, bar * bars)
    prog_a, prog_b = spec['prog']
    drums = DRUMS[spec['drums']]
    step = beat / 4
    kick, snare, hat, hat_o = _kick(sr), _snare(sr), _hat(sr), _hat(sr, True)

    def note(d, octave=0):
        return root + mode[d % 7] + 12 * (d // 7) + 12 * octave

    def freq(n):
        return 440.0 * 2 ** ((n - 69) / 12.0)

    def chord(d):
        return [note(d), note(d + 2), note(d + 4)]

    # motivos de melodía de 2 compases, por tramo
    def motif(seedoff):
        r = random.Random(rng.randrange(1 << 20) + seedoff)
        pos, notes = r.choice((2, 4, 7)), []
        rhythm = r.choice(([0, 3, 4, 6, 8, 11, 12, 14], [0, 2, 4, 7, 8, 10, 12, 15], [0, 4, 6, 8, 12, 14], [0, 3, 6, 8, 11, 14]))
        for st in rhythm:
            pos = max(0, min(13, pos + r.choice((-2, -1, -1, 0, 1, 1, 2))))
            notes.append((st, pos, r.choice((1.5, 2, 3))))
        return notes
    motifs = [motif(0), motif(100), motif(200)]
    for b in range(bars):
        sec = b // 8                                   # 0 = A, 1 = B, 2 = A', 3 = C
        prog = prog_a if sec in (0, 2) else prog_b
        d = prog[b % 4]
        t = b * bar
        ch = chord(d)
        full = sec >= 1
        # --- batería
        dens = 0.55 if sec == 0 else 1.0
        for si in range(16):
            tt = t + si * step
            if drums['k'] and drums['k'][si] == '1' and (sec > 0 or si in (0, 8) or level > 1):
                m.add(tt, kick, 0.9 * dens)
            elif level >= 3 and si in (6, 14) and sec >= 2 and drums['k']:
                m.add(tt, kick, 0.55)
            if drums['s'] and drums['s'][si] == '1' and sec > 0:
                m.add(tt, snare, 0.75)
            if drums['h'] and drums['h'][si] == '1':
                m.add(tt, hat_o if (si % 8 == 2 and spec['drums'] in ('four',)) else hat, 0.35 * dens)
            elif level >= 2 and drums['h'] and si % 2 == 1 and sec >= 2:
                m.add(tt, hat, 0.18)
        if drums['k'] and b % 8 == 7 and level >= 2:                       # relleno de toms cada 8 compases
            for q, f in enumerate((220, 180, 150, 120)):
                m.add(t + bar - (4 - q) * beat / 2, _tom(sr, f), 0.7)
        # --- bajo
        bn = note(d, -2)
        bs = spec['bass']
        bv = 0.34
        if bs == 'sustain':
            m.add(t, _tone(sr, freq(bn), bar * 0.98, 'saw', 1.4) * 0.5, bv * 0.8)
        elif bs == 'eighth':
            for k in range(8):
                m.add(t + k * beat / 2, _tone(sr, freq(bn + (12 if k % 4 == 3 else 0)), beat * 0.45, 'saw', 5.0), bv)
        elif bs == 'rf':
            for k, n_ in enumerate((0, 0, 7, 0, 0, 7, 5, 7)):
                m.add(t + k * beat / 2, _tone(sr, freq(bn + n_), beat * 0.45, 'saw', 4.0), bv)
        elif bs == 'gallop':
            for q in range(4):
                for k in (0, 2, 3):
                    m.add(t + q * beat + k * step, _tone(sr, freq(bn), step * 0.9, 'saw', 5.0), bv)
        elif bs == 'pulse':
            for k in range(16):
                m.add(t + k * step, _tone(sr, freq(bn), step * 0.85, 'square', 6.0, 0.4), bv * 0.55)
        elif bs == 'walk':
            for k, n_ in enumerate((0, 2, 4, 5)):
                m.add(t + k * beat, _tone(sr, freq(bn + mode[n_ % 7]), beat * 0.9, 'tri', 2.5), bv * 1.1)
        # --- acordes
        if spec['pad']:
            for n_ in ch:
                pad = _tone(sr, freq(n_ + 12), bar, 'saw', 0.3, atk=0.25, rel=0.3) + _tone(sr, freq(n_ + 12) * 1.004, bar, 'saw', 0.3, atk=0.3, rel=0.3)
                m.add(t, _lowpass(pad, 24), 0.075 if sec else 0.05)
        # --- arpegio
        if spec['arp'] and (full or level > 1):
            sub = 16 if spec['arp'] == '16th' else 8
            for k in range(sub):
                n_ = ch[[0, 1, 2, 1][k % 4]] + 24
                m.add(t + k * bar / sub, _tone(sr, freq(n_), bar / sub * 0.8, 'square', 5.5, 0.25), 0.05)
        # --- melodía
        if spec['lead'] != 'none' and (sec >= 1 or spec['lead'] == 'active'):
            mt = motifs[0 if sec in (0, 2) else 1] if b % 4 < 2 else motifs[2 if sec == 3 else 0]
            if b % 2 == 0 and not (spec['lead'] == 'sparse' and sec == 0):
                oct_ = 1 if level < 3 else 2
                for st, pos, ln in mt:
                    if spec['lead'] == 'sparse' and st % 8 == 5:
                        continue
                    nn = note(d + pos - 7, oct_)
                    m.add(t + st * step, _tone(sr, freq(nn), step * ln * 1.2, spec['leadw'], 2.2, 0.35, vib=0.012), 0.11)
    out = m.buf
    # eco corto (espacio) y normalización con compresión suave
    d1, d2 = int(beat * 0.75 * sr), int(beat * 1.5 * sr)
    echo = out.copy()
    echo[d1:] += out[:-d1] * 0.25
    echo[d2:] += out[:-d2] * 0.12
    n_loop = int(bar * bars * sr)
    body = echo[:n_loop].copy()
    body[:len(echo) - n_loop] += echo[n_loop:][:len(body)]          # la cola del eco cierra el bucle
    pk = float(np.max(np.abs(body))) or 1.0
    body = np.tanh(body / pk * 1.6) * 0.85
    return body.astype(np.float32)
