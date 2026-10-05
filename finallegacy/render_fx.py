"""Mejoras gráficas: resplandor (bloom), viñeta y gradación de color, más sprites suaves de humo, fuego y brillo.

Calidad (tecla V): 0 = básica, 1 = HD (bloom + color + viñeta), 2 = ULTRA (además grano de película y bloom amplio).
Todo se resuelve con operaciones nativas de pygame (rápidas); numpy, si está instalado, genera sprites más suaves.
"""
import random

import pygame

try:
    import numpy as np
except ImportError:                                  # sin numpy el juego funciona igual, con degradados más simples
    np = None

LEVELS = ('BÁSICA', 'HD', 'ULTRA')

# gradación de color por estado: (multiplicador RGB, intensidad del bloom, umbral)
GRADE = {
    'map': ((246, 250, 255), 0.85, 180),
    'defense': ((255, 246, 240), 1.15, 170),
    'combat': ((252, 248, 244), 1.0, 180),
    'aerial': ((250, 250, 255), 1.0, 180),
    'ground': ((255, 252, 246), 0.95, 185),
    'port': ((255, 246, 238), 1.1, 170),
    'tank': ((248, 250, 248), 1.0, 180),
    'heli': ((252, 252, 250), 1.0, 180),
    'hack': ((240, 255, 250), 1.1, 160),
    'radio': ((240, 255, 250), 1.1, 160),
}


def soft_blob_sprite(size, seed):
    """Bocanada de humo suave (RGBA blanco con alfa irregular)."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    if np is None:
        pygame.draw.circle(s, (255, 255, 255, 120), (size // 2, size // 2), size // 2 - 1)
        return s
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[-1:1:size * 1j, -1:1:size * 1j]
    d = np.sqrt(xx * xx + yy * yy)
    base = np.clip(1 - d, 0, 1) ** 1.1
    noise = np.zeros_like(base)
    for _ in range(7):
        cx, cy = rng.uniform(-0.45, 0.45, 2)
        w = rng.uniform(0.22, 0.45)
        noise += rng.uniform(0.25, 0.6) * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * w * w)))
    a = np.clip(base * (0.35 + noise), 0, 1) * (d < 1)
    rgb = np.full((size, size, 3), 255, dtype=np.uint8)
    out = np.dstack([rgb, (a * 255).astype(np.uint8)])
    surf = pygame.image.frombuffer(out.tobytes(), (size, size), 'RGBA').convert_alpha()
    return surf


def smooth_glow(r, c):
    """Degradado radial suave (sin bandas) para mezclar con suma de color."""
    s = pygame.Surface((r * 2, r * 2))
    if np is None:
        return None
    yy, xx = np.mgrid[0:r * 2, 0:r * 2]
    d = np.sqrt((xx - r + 0.5) ** 2 + (yy - r + 0.5) ** 2) / r
    f = np.clip(1 - d, 0, 1) ** 2.2
    arr = (f[:, :, None] * np.array(c, dtype=np.float32)[None, None, :]).astype(np.uint8)
    pygame.surfarray.blit_array(s, arr.swapaxes(0, 1))
    return s


def fireball_sprite(r, level, seed=0):
    """Bola de fuego: núcleo blanco-amarillo, borde naranja/rojo. level 0..1 = brillo."""
    s = pygame.Surface((r * 2, r * 2))
    if np is None:
        return None
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:r * 2, 0:r * 2]
    ux, uy = (xx - r + 0.5) / r, (yy - r + 0.5) / r
    d = np.sqrt(ux * ux + uy * uy)
    ang = np.arctan2(uy, ux)
    wob = 1 + 0.16 * np.sin(ang * 3 + rng.uniform(0, 6)) + 0.1 * np.sin(ang * 5 + rng.uniform(0, 6))
    d = d / wob
    k = np.clip(1 - d, 0, 1)
    heat = k ** 0.8
    rch = np.clip(heat * 2.0, 0, 1)
    gch = np.clip(heat * 1.55 - 0.25, 0, 1) ** 1.2
    bch = np.clip(heat * 1.2 - 0.62, 0, 1) ** 1.5
    arr = np.dstack([rch, gch, bch]) * (255 * level * (k[:, :, None] ** 0.35))
    pygame.surfarray.blit_array(s, np.clip(arr, 0, 255).astype(np.uint8).swapaxes(0, 1))
    return s


class PostFX:
    def __init__(self, W, H, level=1):
        self.W, self.H = W, H
        self.level = level
        self._noise = None
        self._tint = {}

    def cycle(self):
        self.level = (self.level + 1) % 3
        return LEVELS[self.level]

    # ---------------------------------------------------------------- viñeta + color (una sola mezcla multiplicativa)
    def vignette(self, tint):
        v = self._tint.get(tint)
        if v is None:
            W, H = self.W, self.H
            v = pygame.Surface((W, H))
            if np is not None:
                yy, xx = np.mgrid[0:H, 0:W]
                d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 1.41
                k = 1 - 0.38 * np.clip((d - 0.45) / 0.55, 0, 1) ** 1.6
                arr = (k[:, :, None] * np.array(tint, dtype=np.float32)[None, None, :]).clip(0, 255).astype(np.uint8)
                pygame.surfarray.blit_array(v, arr.swapaxes(0, 1))
            else:
                v.fill(tint)
                for i in range(40):
                    c = 255 - int(70 * (1 - i / 40) ** 2)
                    pygame.draw.rect(v, (c * tint[0] // 255, c * tint[1] // 255, c * tint[2] // 255), (i * 3, i * 3, W - i * 6, H - i * 6), 4)
            v = self._tint[tint] = v.convert()
        return v

    def grain(self):
        if self._noise is None:
            W, H = self.W, self.H
            n = pygame.Surface((W + 64, H + 64))
            if np is not None:
                a = np.random.RandomState(7).randint(0, 14, (W + 64, H + 64)).astype(np.uint8)
                pygame.surfarray.blit_array(n, np.dstack([a, a, a]))
            else:
                n.fill((6, 6, 6))
            self._noise = n.convert()
        return self._noise

    # ---------------------------------------------------------------- aplicación
    def apply(self, cv, state, shake=0.0):
        if self.level <= 0:
            return
        W, H = self.W, self.H
        tint, gain, thr = GRADE.get(state, ((255, 255, 255), 0.8, 190))
        # resplandor: zonas brillantes -> desenfoque barato por reescalado -> suma
        sm = pygame.transform.smoothscale(cv, (W // 4, H // 4))
        sm.fill((thr, thr, thr), special_flags=pygame.BLEND_RGB_SUB)
        sm.blit(sm, (0, 0), special_flags=pygame.BLEND_RGB_ADD)          # x2
        sm.blit(sm, (0, 0), special_flags=pygame.BLEND_RGB_ADD)          # x4
        m = int(255 * min(1.0, gain * (0.5 if self.level == 1 else 0.62)))
        sm.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)          # intensidad (en baja resolución)
        b1 = pygame.transform.smoothscale(sm, (W // 16, H // 16))
        b1 = pygame.transform.smoothscale(b1, (W // 8, H // 8))
        b1 = pygame.transform.smoothscale(b1, (W // 3, H // 3))
        big = pygame.transform.smoothscale(b1, (W, H))
        cv.blit(big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if self.level >= 2:
            w2 = pygame.transform.smoothscale(sm, (W // 32, H // 32))
            w2 = pygame.transform.smoothscale(w2, (W // 6, H // 6))
            w2 = pygame.transform.smoothscale(w2, (W, H))
            cv.blit(w2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        # color y viñeta
        cv.blit(self.vignette(tint), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if self.level >= 2:
            ox, oy = random.randint(0, 63), random.randint(0, 63)
            cv.blit(self.grain(), (0, 0), area=pygame.Rect(ox, oy, W, H), special_flags=pygame.BLEND_RGB_ADD)
