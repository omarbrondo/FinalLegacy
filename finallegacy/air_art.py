"""Arte de la batalla aérea: jefes aéreos (uno por oleada), minas y tintes de aeronaves."""
import pygame


def _S():
    return 3


def make_air_boss(k):
    """Jefe aéreo k (0 = el comandante stealth se construye aparte). Mira hacia abajo (sur)."""
    fn = [None, _nodriza, _fantasma, _artillero, _tormenta, _titan][k]
    return fn()


def _surf(w, h):
    S = _S()
    return pygame.Surface((w * S, h * S), pygame.SRCALPHA), S


def _fin(s, w, h):
    return pygame.transform.smoothscale(s, (w, h))


def _nodriza():
    W, H = 300, 210
    s, S = _surf(W, H)
    P = lambda x, y: (x * S, y * S)
    body = [(150, 205), (210, 170), (292, 80), (298, 40), (240, 14), (150, 30), (60, 14), (2, 40), (8, 80), (90, 170)]
    pygame.draw.polygon(s, (22, 26, 34), [P(*q) for q in body])
    inner = [(150, 196), (206, 164), (284, 80), (288, 46), (238, 22), (150, 38), (62, 22), (12, 46), (16, 80), (94, 164)]
    pygame.draw.polygon(s, (84, 96, 112), [P(*q) for q in inner])
    pygame.draw.polygon(s, (120, 134, 152), [P(*q) for q in inner], 3 * S // 3)
    for k in range(1, 8):
        pygame.draw.line(s, (62, 72, 86), P(20 + k * 5, 40 + k * 12), P(280 - k * 5, 40 + k * 12), 2)
    # compuertas de hangar (resplandor naranja)
    for i in range(6):
        x = 56 + i * 38
        pygame.draw.rect(s, (20, 20, 24), (x * S, 150 * S - abs(i - 2.5) * 6 * S - 40 * S * 0, 24 * S, 14 * S), border_radius=3)
        pygame.draw.rect(s, (255, 150, 50), ((x + 3) * S, (152 - abs(i - 2.5) * 6) * S, 18 * S, 8 * S), border_radius=2)
    # puente central y antenas
    pygame.draw.ellipse(s, (30, 36, 46), P(110, 70) + (80 * S, 60 * S))
    pygame.draw.ellipse(s, (150, 206, 244), P(126, 84) + (48 * S, 30 * S))
    pygame.draw.ellipse(s, (232, 248, 255), P(134, 88) + (22 * S, 12 * S))
    # motores traseros
    for x in (54, 104, 196, 246):
        pygame.draw.circle(s, (16, 18, 22), P(x, 34), 15 * S)
        pygame.draw.circle(s, (60, 66, 78), P(x, 34), 11 * S)
        pygame.draw.circle(s, (255, 170, 80), P(x, 34), 6 * S)
    return _fin(s, W, H)


def _fantasma():
    W, H = 250, 220
    s, S = _surf(W, H)
    P = lambda x, y: (x * S, y * S)
    outline = [(125, 216), (150, 150), (246, 60), (200, 40), (160, 70), (125, 22), (90, 70), (50, 40), (4, 60), (100, 150)]
    pygame.draw.polygon(s, (10, 12, 16), [P(*q) for q in outline])
    inner = [(125, 206), (146, 148), (232, 62), (200, 48), (160, 78), (125, 34), (90, 78), (50, 48), (18, 62), (104, 148)]
    pygame.draw.polygon(s, (28, 32, 42), [P(*q) for q in inner])
    for sd in (-1, 1):
        pygame.draw.line(s, (80, 230, 255), P(125 + sd * 6, 200), P(125 + sd * 108, 66), 3)
        pygame.draw.line(s, (80, 230, 255), P(125 + sd * 26, 128), P(125 + sd * 64, 78), 2)
        pygame.draw.circle(s, (80, 230, 255), P(125 + sd * 36, 52), 6 * S // 2)
    pygame.draw.polygon(s, (14, 28, 46), [P(125, 176), P(136, 130), P(125, 96), P(114, 130)])
    pygame.draw.polygon(s, (70, 190, 230), [P(125, 168), P(131, 130), P(125, 104), P(119, 130)])
    pygame.draw.circle(s, (80, 230, 255), P(125, 28), 9 * S // 2)
    return _fin(s, W, H)


def _artillero():
    W, H = 300, 230
    s, S = _surf(W, H)
    P = lambda x, y: (x * S, y * S)
    pygame.draw.polygon(s, (20, 24, 18), [P(*q) for q in [(150, 226), (170, 190), (170, 60), (190, 40), (150, 18), (110, 40), (130, 60), (130, 190)]])
    pygame.draw.polygon(s, (92, 100, 70), [P(*q) for q in [(150, 214), (164, 186), (164, 62), (150, 40), (136, 62), (136, 186)]])
    # alas rectas con motores
    wing = [(4, 120), (296, 120), (286, 96), (14, 96)]
    pygame.draw.polygon(s, (20, 24, 18), [P(*q) for q in [(0, 124), (300, 124), (290, 92), (10, 92)]])
    pygame.draw.polygon(s, (112, 120, 84), [P(*q) for q in wing])
    for x in (30, 74, 118, 182, 226, 270):
        pygame.draw.circle(s, (16, 18, 14), P(x, 108), 12 * S // 2 + 6)
        pygame.draw.circle(s, (70, 76, 60), P(x, 108), 9 * S // 2 + 3)
        pygame.draw.circle(s, (255, 180, 80), P(x, 78), 5 * S // 2)
    # bahía de bombas
    pygame.draw.rect(s, (34, 38, 28), (138 * S, 128 * S, 24 * S, 44 * S), border_radius=3)
    for k in range(4):
        pygame.draw.circle(s, (220, 60, 50), P(150, 136 + k * 11), 4 * S // 2)
    pygame.draw.polygon(s, (14, 28, 46), [P(150, 206), P(158, 186), P(150, 172), P(142, 186)])
    pygame.draw.polygon(s, (60, 130, 190), [P(150, 202), P(155, 187), P(150, 177), P(145, 187)])
    pygame.draw.polygon(s, (70, 78, 56), [P(*q) for q in [(130, 44), (170, 44), (200, 22), (100, 22)]])
    return _fin(s, W, H)


def _tormenta():
    W, H = 280, 220
    s, S = _surf(W, H)
    P = lambda x, y: (x * S, y * S)
    outline = [(140, 214), (176, 140), (276, 66), (252, 36), (176, 52), (140, 20), (104, 52), (28, 36), (4, 66), (104, 140)]
    pygame.draw.polygon(s, (20, 28, 44), [P(*q) for q in outline])
    inner = [(140, 202), (172, 140), (262, 68), (246, 46), (176, 62), (140, 32), (104, 62), (34, 46), (18, 68), (108, 140)]
    pygame.draw.polygon(s, (186, 204, 226), [P(*q) for q in inner])
    pygame.draw.polygon(s, (110, 130, 160), [P(*q) for q in inner], 2)
    for sd in (-1, 1):
        for k in range(4):
            pygame.draw.line(s, (120, 150, 190), P(140 + sd * (20 + k * 18), 160 - k * 22), P(140 + sd * (42 + k * 22), 96 - k * 8), 2)
        pygame.draw.circle(s, (20, 28, 44), P(140 + sd * 118, 60), 18 * S // 2 + 6)
        pygame.draw.circle(s, (70, 220, 255), P(140 + sd * 118, 60), 12 * S // 2 + 3)
        pygame.draw.circle(s, (230, 250, 255), P(140 + sd * 118, 60), 5 * S // 2)
    pygame.draw.polygon(s, (16, 30, 54), [P(140, 190), P(152, 140), P(140, 100), P(128, 140)])
    pygame.draw.polygon(s, (90, 220, 255), [P(140, 180), P(146, 140), P(140, 110), P(134, 140)])
    return _fin(s, W, H)


def _titan():
    W, H = 340, 240
    s, S = _surf(W, H)
    P = lambda x, y: (x * S, y * S)
    outline = [(170, 236), (210, 190), (330, 110), (336, 60), (260, 30), (170, 48), (80, 30), (4, 60), (10, 110), (130, 190)]
    pygame.draw.polygon(s, (14, 10, 14), [P(*q) for q in outline])
    inner = [(170, 224), (206, 186), (318, 110), (324, 66), (258, 40), (170, 58), (82, 40), (16, 66), (22, 110), (134, 186)]
    pygame.draw.polygon(s, (62, 34, 40), [P(*q) for q in inner])
    pygame.draw.polygon(s, (230, 60, 70), [P(*q) for q in inner], 3)
    for sd in (-1, 1):
        for k in range(6):
            x0 = 170 + sd * (30 + k * 24)
            pygame.draw.polygon(s, (40, 22, 28), [P(x0, 70 + k * 6), P(x0 + sd * 14, 100 + k * 8), P(x0, 130 + k * 4)])
        pygame.draw.line(s, (230, 60, 70), P(170 + sd * 14, 210), P(170 + sd * 150, 100), 3)
    pygame.draw.circle(s, (12, 8, 12), P(170, 120), 44 * S // 2 + 6)
    pygame.draw.circle(s, (150, 24, 40), P(170, 120), 36 * S // 2 + 4)
    pygame.draw.circle(s, (255, 90, 80), P(170, 120), 24 * S // 2)
    pygame.draw.circle(s, (255, 235, 210), P(170, 120), 10 * S // 2)
    for x in (92, 248):
        pygame.draw.circle(s, (16, 12, 16), P(x, 50), 14 * S // 2 + 6)
        pygame.draw.circle(s, (255, 150, 70), P(x, 50), 8 * S // 2)
    pygame.draw.polygon(s, (14, 28, 46), [P(170, 214), P(180, 190), P(170, 168), P(160, 190)])
    pygame.draw.polygon(s, (70, 170, 220), [P(170, 210), P(176, 190), P(170, 174), P(164, 190)])
    return _fin(s, W, H)

