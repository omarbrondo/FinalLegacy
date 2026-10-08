"""Islas con arte dibujado (soldados/isla_N.png + islas.json). La costa del dibujo se deforma (en polares) para calzar exacto con el contorno que usa el juego
para las colisiones, así los barcos no se meten en tierra ni se frenan lejos. Si falta el arte o numpy, paint_island usa el dibujo por código."""
import json
import math
import os
import random
import pygame
from .common import coast_r

try:
    import numpy as np
except ImportError:                                           # sin numpy: se usa el dibujo por código
    np = None

_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados')
_ART = {}
_CACHE = {}


def _load():
    if _ART:
        return _ART
    try:
        meta = json.load(open(os.path.join(_BASE, 'islas.json')))
        for k, m in meta.items():
            img = pygame.image.load(os.path.join(_BASE, k + '.png')).convert_alpha()
            rgba = np.dstack([pygame.surfarray.array3d(img), pygame.surfarray.array_alpha(img)]).transpose(1, 0, 2).astype(np.float32)   # [y, x, canal]
            _ART[k] = (rgba, meta[k]['cx'], meta[k]['cy'], np.array(meta[k]['ra'], np.float32))
    except (OSError, ValueError, KeyError, pygame.error):
        _ART.clear()
        _ART['_none'] = None
    return _ART


def _pick(r, is_city):
    if is_city:
        return 'isla_4' if r < 100 else 'isla_5'
    return 'isla_0' if r < 63 else ('isla_1' if r < 81 else ('isla_2' if r < 100 else 'isla_3'))


def paint(land, x, y, r, seed, is_city):
    """Dibuja la isla con arte sobre 'land'; devuelve False si no hay arte (el llamador usa el dibujo por código)."""
    if np is None or r > 160:
        return False
    art = _load()
    if '_none' in art:
        return False
    key = (r, seed, is_city)
    spr = _CACHE.get(key)
    if spr is None:
        rgba, cx, cy, ra = art[_pick(r, is_city)]
        S = int(r * 3.4) // 2 * 2
        rnd = random.Random(seed)
        phase, mirror = rnd.randrange(360), rnd.random() < 0.5
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        dx, dy = xx - S / 2, yy - S / 2
        th = np.arctan2(dy, dx)
        rho = np.hypot(dx, dy)
        ang = np.degrees(th) % 360
        rb = np.array([coast_r(r, seed, math.radians(t), 1.04) for t in range(360)], np.float32)
        rbi = np.interp(ang, np.arange(361), np.append(rb, rb[0]))
        ths = (-ang if mirror else ang) + phase
        ths = ths % 360
        rai = np.interp(ths, np.arange(361), np.append(ra, ra[0]))
        k = rai / np.maximum(rbi, 1.0)
        rs = rho * k
        t2 = np.radians(ths)
        sx, sy = cx + rs * np.cos(t2), cy + rs * np.sin(t2)
        x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
        fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
        H, W = rgba.shape[:2]
        def g(ix, iy):
            ok = ((ix >= 0) & (ix < W) & (iy >= 0) & (iy < H))[..., None]
            v = rgba[np.clip(iy, 0, H - 1), np.clip(ix, 0, W - 1)]
            return np.where(ok, v, 0.0)
        out = (g(x0, y0) * (1 - fx) * (1 - fy) + g(x0 + 1, y0) * fx * (1 - fy) + g(x0, y0 + 1) * (1 - fx) * fy + g(x0 + 1, y0 + 1) * fx * fy)
        out[..., 3] *= np.clip((1.75 * r - rho) / (0.3 * r), 0, 1)                      # el halo se desvanece antes del borde del lienzo
        surf = pygame.Surface((S, S), pygame.SRCALPHA)
        pygame.surfarray.pixels3d(surf)[:] = out[..., :3].transpose(1, 0, 2).astype(np.uint8)
        pygame.surfarray.pixels_alpha(surf)[:] = out[..., 3].T.astype(np.uint8)
        spr = _CACHE[key] = surf
    land.blit(spr, (int(x - spr.get_width() / 2), int(y - spr.get_height() / 2)))
    return True
