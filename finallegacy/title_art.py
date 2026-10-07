"""Título "RETRO LEGACY" cromado estilo retrowave de los 80: degradado celeste a rosa con línea de horizonte,
extrusión 3D violeta, contorno claro, brillo en los bordes superiores, resplandor, destellos y un reflejo que cruza."""
import math
import random
import pygame
from .common import W, glow, lerp

TOP, MID_BLUE, HORIZON, PINK, BOTTOM = (214, 244, 255), (64, 138, 238), (255, 255, 255), (255, 150, 220), (150, 40, 176)
OUTLINE = (232, 244, 255)
EXT_NEAR, EXT_FAR = (126, 70, 190), (36, 20, 92)
PAD, EXT, THICK = 14, 18, 4


def _lerp3(a, b, t):
    return tuple(int(lerp(a[i], b[i], t)) for i in range(3))


def _gradient(w, h):
    g = pygame.Surface((w, h))
    for y in range(h):
        k = y / max(1, h - 1)
        if k < 0.50:
            c = _lerp3(TOP, MID_BLUE, k / 0.50)
        elif k < 0.54:
            c = HORIZON
        else:
            c = _lerp3(PINK, BOTTOM, (k - 0.54) / 0.46)
        pygame.draw.line(g, c, (0, y), (w, y))
    return g


def _thick(txt, r):
    """Letras más gruesas: la máscara se copia en un disco de radio r."""
    w, h = txt.get_size()
    out = pygame.Surface((w + 2 * r, h + 2 * r), pygame.SRCALPHA)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + 1:
                out.blit(txt, (r + dx, r + dy))
    return out


def _tint(mask, col, alpha=255):
    s = mask.copy()
    s.fill((*col, 255), special_flags=pygame.BLEND_RGBA_MULT)
    if alpha < 255:
        s.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def _blur(s, k=5):
    w, h = s.get_size()
    small = pygame.transform.smoothscale(s, (max(2, w // k), max(2, h // k)))
    return pygame.transform.smoothscale(small, (w, h))


def _line(font, text):
    txt = font.render(text, True, (255, 255, 255)).convert_alpha()
    txt = txt.subsurface(txt.get_bounding_rect()).copy()
    m = _thick(txt, THICK)
    w, h = m.get_size()
    cw, ch = w + 2 * PAD + EXT, h + 2 * PAD + EXT
    canvas = pygame.Surface((cw, ch), pygame.SRCALPHA)
    glow_s = pygame.Surface((cw, ch), pygame.SRCALPHA)
    glow_s.blit(_tint(m, (150, 130, 255), 200), (PAD, PAD))
    canvas.blit(_blur(_blur(glow_s, 6), 3), (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    for d in range(EXT, 0, -1):                                      # extrusión 3D de lejos a cerca
        c = _lerp3(EXT_NEAR, EXT_FAR, d / EXT)
        canvas.blit(_tint(m, c), (PAD + d * 0.7, PAD + d))
    outline = _thick(m, 2)
    canvas.blit(_tint(outline, OUTLINE), (PAD - 2, PAD - 2))
    fill = m.copy()
    fill.blit(_gradient(w, h), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    canvas.blit(fill, (PAD, PAD))
    mk = pygame.mask.from_surface(m)
    edge = mk.copy()
    edge.erase(mk, (0, 4))                                           # bordes superiores de cada letra
    hl = edge.to_surface(setcolor=(255, 255, 255, 235), unsetcolor=(0, 0, 0, 0))
    canvas.blit(hl, (PAD, PAD))
    shine_mask = pygame.Surface((cw, ch), pygame.SRCALPHA)
    shine_mask.blit(_tint(m, (255, 255, 255)), (PAD, PAD))
    return canvas, shine_mask


def make_logo(font):
    """Devuelve el título ya compuesto, la máscara de las letras (para el reflejo) y las posiciones de los destellos."""
    a, ma = _line(font, 'RETRO')
    b, mb = _line(font, 'LEGACY')
    gap = -26
    w = max(a.get_width(), b.get_width())
    h = a.get_height() + b.get_height() + gap
    logo = pygame.Surface((w, h), pygame.SRCALPHA)
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    ax, bx = (w - a.get_width()) // 2, (w - b.get_width()) // 2
    by = a.get_height() + gap
    logo.blit(a, (ax, 0))
    logo.blit(b, (bx, by))
    mask.blit(ma, (ax, 0))
    mask.blit(mb, (bx, by))
    sparks = [(ax + PAD + 6, PAD + 8, 34, 0.0), (bx + b.get_width() - PAD - 4, by + PAD + 12, 28, 2.1), (ax + a.get_width() - PAD - 30, PAD + 2, 20, 4.0)]
    return dict(img=logo, mask=mask, sparks=sparks)


def _star(cv, x, y, r, a=255):
    glow(cv, x, y, r * 1.4, (200, 230, 255), a / 255 * 0.9)
    for ang, k in ((0, 1.0), (90, 1.0), (45, 0.45), (135, 0.45)):
        rad = math.radians(ang)
        dx, dy = math.cos(rad) * r * k, math.sin(rad) * r * k
        nx, ny = -dy * 0.10, dx * 0.10
        pygame.draw.polygon(cv, (255, 255, 255), [(x - dx, y - dy), (x + nx, y + ny), (x + dx, y + dy), (x - nx, y - ny)])


def draw_logo(cv, logo, cx, top, t):
    img = logo['img']
    x, y = cx - img.get_width() // 2, top
    cv.blit(img, (x, y))
    w, h = img.get_size()
    ph = (t % 5.0) / 1.3                                             # reflejo diagonal cada 5 s
    if ph < 1.0:
        band = pygame.Surface((w, h), pygame.SRCALPHA)
        bx = int(-120 + ph * (w + 240))
        pygame.draw.polygon(band, (255, 255, 255, 170), [(bx, 0), (bx + 70, 0), (bx + 20, h), (bx - 50, h)])
        band.blit(logo['mask'], (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        cv.blit(band, (x, y))
    for sx, sy, r, ph0 in logo['sparks']:
        k = 0.55 + 0.45 * math.sin(t * 2.6 + ph0)
        if k > 0.12:
            _star(cv, x + sx, y + sy, r * k, 255)
