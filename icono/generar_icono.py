"""Genera el ícono del juego (icono/retro_legacy.png y icono/retro_legacy.ico) con el mismo estilo cromado del título.

Uso:  python icono/generar_icono.py
"""
import io
import math
import os
import struct
import sys

import pygame

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
from finallegacy.title_art import _line     # noqa: E402  (las letras cromadas del título)

S = 512


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hacer_icono():
    img = pygame.Surface((S, S), pygame.SRCALPHA)
    fondo = pygame.Surface((S, S))
    hor = int(S * 0.62)
    for y in range(S):                                     # cielo violeta que baja al horizonte y mar oscuro
        if y < hor:
            c = _lerp((14, 10, 44), (96, 30, 122), y / hor)
        else:
            c = _lerp((20, 16, 70), (8, 8, 34), (y - hor) / (S - hor))
        pygame.draw.line(fondo, c, (0, y), (S, y))
    # sol retro con cortes horizontales
    sol = pygame.Surface((S, S), pygame.SRCALPHA)
    cx, cy, r = S // 2, hor - 6, int(S * 0.30)
    for y in range(cy - r, cy + 1):
        k = (y - (cy - r)) / r
        c = _lerp((255, 224, 96), (255, 70, 160), k)
        w = int(math.sqrt(max(0, r * r - (y - cy) ** 2)))
        pygame.draw.line(sol, (*c, 255), (cx - w, y), (cx + w, y))
    for i in range(1, 6):                                   # franjas que recortan la parte baja del sol
        y = cy - int(r * 0.50) + i * int(r * 0.11)
        pygame.draw.rect(sol, (0, 0, 0, 0), (0, y, S, max(2, i * 2)))
    fondo.blit(sol, (0, 0))
    # horizonte brillante y rejilla del mar
    pygame.draw.line(fondo, (120, 230, 255), (0, hor), (S, hor), 3)
    for i in range(1, 9):
        y = hor + int((i / 8) ** 2 * (S - hor))
        pygame.draw.line(fondo, (60, 130, 220), (0, y), (S, y), 2)
    for i in range(-8, 9):
        pygame.draw.line(fondo, (170, 70, 220), (cx + i * 14, hor), (cx + i * 90, S), 2)
    # silueta de un buque en el horizonte
    casco = [(cx - 118, hor - 2), (cx + 118, hor - 2), (cx + 92, hor - 22), (cx - 96, hor - 22)]
    pygame.draw.polygon(fondo, (10, 8, 30), casco)
    pygame.draw.rect(fondo, (10, 8, 30), (cx - 34, hor - 44, 70, 22))
    pygame.draw.rect(fondo, (10, 8, 30), (cx - 12, hor - 62, 24, 18))
    pygame.draw.line(fondo, (10, 8, 30), (cx + 2, hor - 62), (cx + 2, hor - 84), 3)
    pygame.draw.line(fondo, (10, 8, 30), (cx + 40, hor - 20), (cx + 100, hor - 30), 6)
    # letras "RL" cromadas
    fuente = pygame.font.Font(os.path.join(RAIZ, 'fonts', 'Orbitron.ttf'), 210)
    fuente.set_bold(True)
    letras, _ = _line(fuente, 'RL')
    k = min(S * 0.86 / letras.get_width(), S * 0.42 / letras.get_height())
    letras = pygame.transform.smoothscale(letras, (int(letras.get_width() * k), int(letras.get_height() * k)))
    fondo.convert_alpha()
    img.blit(fondo, (0, 0))
    img.blit(letras, ((S - letras.get_width()) // 2, int(S * 0.08)))
    # esquinas redondeadas y borde
    mask = pygame.Surface((S, S), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, S, S), border_radius=int(S * 0.19))
    img.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(img, (190, 225, 255, 255), (2, 2, S - 4, S - 4), 6, border_radius=int(S * 0.19))
    return img


def _entrada_bmp(img, t):
    """Imagen de t x t como DIB de 32 bits (el formato clásico de los .ico: lo entienden todas las versiones de Windows y PyInstaller)."""
    sup = pygame.transform.smoothscale(img, (t, t))
    bgra = pygame.image.tostring(sup, 'BGRA')
    filas = [bgra[y * t * 4:(y + 1) * t * 4] for y in range(t)][::-1]           # de abajo hacia arriba
    mascara = bytes(((t + 31) // 32) * 4 * t)                                  # máscara AND vacía (la transparencia va en el canal alfa)
    cab = struct.pack('<IiiHHIIiiII', 40, t, t * 2, 1, 32, 0, len(bgra) + len(mascara), 0, 0, 0, 0)
    return cab + b''.join(filas) + mascara


def guardar_ico(img, ruta, tamanos=(16, 24, 32, 48, 64, 128, 256)):
    """ICO con DIB de 32 bits para los tamaños chicos y PNG incrustado para 256 (como los que genera Windows)."""
    datos = []
    for t in tamanos:
        if t >= 256:
            buf = io.BytesIO()
            pygame.image.save(pygame.transform.smoothscale(img, (t, t)), buf, 'icon.png')
            datos.append(buf.getvalue())
        else:
            datos.append(_entrada_bmp(img, t))
    cab = struct.pack('<HHH', 0, 1, len(datos))
    off = 6 + 16 * len(datos)
    ent = b''
    for t, d in zip(tamanos, datos):
        ent += struct.pack('<BBBBHHII', 0 if t >= 256 else t, 0 if t >= 256 else t, 0, 0, 1, 32, len(d), off)
        off += len(d)
    with open(ruta, 'wb') as f:
        f.write(cab + ent + b''.join(datos))


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_mode((1, 1))
    icono = hacer_icono()
    pygame.image.save(pygame.transform.smoothscale(icono, (256, 256)), os.path.join(AQUI, 'retro_legacy.png'))
    guardar_ico(icono, os.path.join(AQUI, 'retro_legacy.ico'))
    print('Listo: icono/retro_legacy.png y icono/retro_legacy.ico')
