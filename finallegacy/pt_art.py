"""Arte del asalto lateral: soldados articulados, tanque, torretas, contenedores y fondo."""
import math
import pygame
import random
from .common import clamp, lerp, shade


# ------------------------------------------------------------------ soldados realistas (asalto lateral)
PT_S = 5                      # supersampling


PT_K = 1.15                   # escala del personaje


PT_CW, PT_CH = 128, 120


PT_AX, PT_AY = 64, 104


PT_LOOK = {
    # uniforme, camuflaje(s), chaleco, casco, pantalón, camuflaje pantalón, piel, extra
    'player': dict(body=(92, 100, 78), camo=[(70, 80, 60), (116, 112, 84), (54, 62, 48)], vest=(66, 62, 52), helm=(104, 96, 72), pants=(86, 92, 72),
                   pcamo=[(66, 74, 56), (112, 108, 80)], skin=(214, 166, 130), acc=(70, 150, 200), mask=False),
    'rifle': dict(body=(86, 88, 94), camo=[(64, 66, 74), (112, 114, 120), (46, 48, 56)], vest=(44, 46, 52), helm=(60, 62, 70), pants=(70, 72, 80),
                  pcamo=[(54, 56, 66), (100, 102, 110)], skin=(206, 160, 126), acc=(200, 60, 56), mask=True),
    'knife': dict(body=(112, 104, 94), camo=[], vest=(52, 44, 40), helm=(180, 52, 50), pants=(62, 58, 58),
                  pcamo=[(52, 48, 50), (86, 80, 80)], skin=(208, 160, 124), acc=(200, 60, 56), mask=False),
    'gren': dict(body=(62, 60, 70), camo=[(48, 46, 58), (84, 82, 96)], vest=(38, 38, 46), helm=(54, 54, 62), pants=(56, 56, 66),
                 pcamo=[(44, 44, 54), (76, 76, 88)], skin=(200, 156, 124), acc=(220, 70, 60), mask=True),
    'sniper': dict(body=(76, 92, 66), camo=[(58, 74, 50), (110, 120, 80), (44, 58, 40)], vest=(58, 66, 50), helm=(70, 86, 60), pants=(72, 88, 62),
                   pcamo=[(54, 68, 46), (100, 112, 76)], skin=(206, 160, 126), acc=(90, 190, 90), mask=True),
    'shield': dict(body=(70, 76, 88), camo=[(54, 60, 72), (96, 102, 116)], vest=(40, 44, 54), helm=(96, 104, 116), pants=(56, 62, 74),
                   pcamo=[(46, 52, 64), (84, 90, 104)], skin=(204, 158, 124), acc=(230, 190, 60), mask=True),
    'flame': dict(body=(176, 128, 66), camo=[], vest=(104, 76, 44), helm=(150, 104, 52), pants=(98, 76, 56),
                  pcamo=[(84, 64, 46), (120, 94, 66)], skin=(206, 160, 126), acc=(230, 110, 50), mask=True),
    'pow': dict(body=(188, 180, 156), camo=[], vest=(160, 150, 130), helm=(86, 62, 40), pants=(96, 92, 112),
                pcamo=[], skin=(220, 176, 140), acc=(200, 200, 200), mask=False),
}


def _dk(c, d):
    return (clamp(c[0] - d, 0, 255), clamp(c[1] - d, 0, 255), clamp(c[2] - d, 0, 255))


def _lt(c, d):
    return (clamp(c[0] + d, 0, 255), clamp(c[1] + d, 0, 255), clamp(c[2] + d, 0, 255))


def _capsule(a, b, r0, r1, steps=9):
    """Polígono de un miembro que se afina de r0 (en a) a r1 (en b)."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    pts = []
    for i in range(steps + 1):
        t = ang + 1.5708 - 3.14159 * i / steps
        pts.append((b[0] + math.cos(t) * r1, b[1] + math.sin(t) * r1))
    for i in range(steps + 1):
        t = ang - 1.5708 - 3.14159 * i / steps
        pts.append((a[0] + math.cos(t) * r0, a[1] + math.sin(t) * r0))
    return pts


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

    def fill(self, pts, col, camo=None, seed=0, out=None, folds=0):
        """Rellena un polígono; opcionalmente con camuflaje recortado a su forma y pliegues de tela."""
        P = [self.pt(*p) for p in pts]
        xs, ys = [q[0] for q in P], [q[1] for q in P]
        x0, y0 = int(min(xs)) - 3, int(min(ys)) - 3
        w, h = int(max(xs)) - x0 + 4, int(max(ys)) - y0 + 4
        if w < 2 or h < 2:
            return
        sh = [(q[0] - x0, q[1] - y0) for q in P]
        tmp = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(tmp, col, sh)
        if camo or folds:
            rnd = random.Random(seed * 7919 + len(pts))
            if camo:
                n = max(4, int(w * h / (self.S * self.S * 26)))
                for _ in range(n):
                    cx, cy = rnd.uniform(0, w), rnd.uniform(0, h)
                    r = rnd.uniform(2.0, 5.0) * self.S
                    blob = [(cx + math.cos(t) * r * rnd.uniform(0.6, 1.3), cy + math.sin(t) * r * rnd.uniform(0.4, 1.0)) for t in [k * 0.9 + rnd.uniform(0, 0.3) for k in range(7)]]
                    pygame.draw.polygon(tmp, rnd.choice(camo), blob)
            for _ in range(folds):
                cx, cy = rnd.uniform(w * 0.2, w * 0.8), rnd.uniform(h * 0.2, h * 0.8)
                L = rnd.uniform(3, 7) * self.S
                a = rnd.uniform(-0.6, 0.6) + 1.2
                pygame.draw.line(tmp, _dk(col, 22) + (170,), (cx, cy), (cx + math.cos(a) * L, cy + math.sin(a) * L), max(1, int(self.S * 0.35)))
            msk = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.polygon(msk, (255, 255, 255, 255), sh)
            tmp.blit(msk, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.surf.blit(tmp, (x0, y0))
        if out is not None:
            pygame.draw.polygon(self.surf, out, P, max(1, int(self.S * 0.35)))

    def line(self, a, b, w, col):
        A, B = self.pt(*a), self.pt(*b)
        pygame.draw.line(self.surf, col, A, B, max(1, int(w * self.S * PT_K)))

    def circ(self, c, r, col):
        x, y = self.pt(*c)
        pygame.draw.circle(self.surf, col, (x, y), r * self.S * PT_K)

    def finish(self):
        """Iluminación: contorno fino, luz cálida de atardecer por la derecha y sombra por abajo/izquierda."""
        S = self.S
        base = self.surf
        w, h = base.get_size()
        m = pygame.mask.from_surface(base, 12)
        # degradado vertical (más claro arriba)
        grad = pygame.Surface((w, h))
        for y in range(h):
            v = int(255 - 70 * (y / h) ** 1.2)
            pygame.draw.line(grad, (v, v, v), (0, y), (w, y))
        base.blit(grad, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        lay = pygame.Surface((w, h), pygame.SRCALPHA)
        t = max(1, int(S * 0.55))
        # sombra interior (abajo / izquierda)
        sh = pygame.mask.Mask((w, h))
        for k in range(1, int(S * 1.6) + 1):
            e = m.copy()
            e.erase(m, (k, -k))
            sh.draw(e, (0, 0))
        lay.blit(sh.to_surface(setcolor=(18, 14, 30, 120), unsetcolor=(0, 0, 0, 0)), (0, 0))
        # luz de borde (arriba / derecha), cálida
        rim = pygame.mask.Mask((w, h))
        for k in range(1, int(S * 0.8) + 1):
            e = m.copy()
            e.erase(m, (-k, k))
            rim.draw(e, (0, 0))
        lay.blit(rim.to_surface(setcolor=(255, 196, 140, 70), unsetcolor=(0, 0, 0, 0)), (0, 0))
        # contorno fino oscuro
        ol = pygame.mask.Mask((w, h))
        for dx, dy in ((t, 0), (-t, 0), (0, t), (0, -t)):
            e = m.copy()
            e.erase(m, (-dx, -dy))
            ol.draw(e, (0, 0))
        lay.blit(ol.to_surface(setcolor=(16, 12, 20, 190), unsetcolor=(0, 0, 0, 0)), (0, 0))
        base.blit(lay, (0, 0))
        return pygame.transform.smoothscale(base, (w // S, h // S))


def _leg(hip, th, flex, L1=16.5, L2=16.5):
    t = math.radians(th)
    knee = (hip[0] + math.sin(t) * L1, hip[1] - math.cos(t) * L1)
    t2 = math.radians(th - flex)
    ankle = (knee[0] + math.sin(t2) * L2, knee[1] - math.cos(t2) * L2)
    return knee, ankle, t2


def _pose(pose, i):
    """(pierna1, pierna2, inclinación, cadera automática, altura de cadera, ángulo de caída)  pierna=(muslo°, flexión°)."""
    if pose == 'run':
        ph = 6.2832 * i / 8
        legs = []
        for k in (0, 1):
            pk = ph + k * 3.14159
            legs.append((46 * math.sin(pk), 10 + 78 * max(0.0, math.cos(pk))))
        return legs[0], legs[1], 9.0, True, 33.0, 0.0
    if pose == 'idle':
        br = math.sin(6.2832 * i / 4)
        return (7, 3 + br), (-7, 3), 0.0, True, 33.0, 0.0
    if pose == 'crouch':
        return (76, 100), (22, 108), 13.0, True, 20.0, 0.0
    if pose == 'jump':
        return (52, 84), (-14, 52), 4.0, False, 30.0, 0.0
    if pose == 'fall':
        return (14, 16), (-12, 8), -3.0, False, 32.5, 0.0
    if pose == 'die':
        ang = (0, 12, 32, 58, 80, 90)[min(i, 5)]
        return (6, 6), (-6, 6), -6.0 * min(i, 3) / 3, False, 33.0 - min(i, 5) * 1.1, float(ang)
    return (7, 3), (-7, 3), 0.0, True, 33.0, 0.0


def _body_frame(kind, pose, i, t=0.0):
    """Cuerpo (sin brazos) mirando a la derecha. Devuelve (surf, shoulder_dx, shoulder_dy)."""
    fem = kind.endswith('_f')
    if fem:
        kind = kind[:-2]
    look = PT_LOOK[kind]
    leg1, leg2, lean, auto, hy, fall = _pose(pose, i)
    rig = _Rig(fall)
    body, vest, helm, pants, skin = look['body'], look['vest'], look['helm'], look['pants'], look['skin']
    camo, pcamo, acc = look['camo'], look['pcamo'], look['acc']
    heavy = kind in ('gren', 'shield')
    boot = (36, 32, 32)
    hip = [0.0, hy]
    if auto:
        lows = []
        for th, fl in (leg1, leg2):
            kn, an, _ = _leg((0, 0), th, fl)
            lows.append(-an[1])
        hip[1] = max(lows) + 1.4
    hip = tuple(hip)
    legs = []
    for (th, fl), sd in ((leg1, 30), (leg2, 0)):
        kn, an, t2 = _leg(hip, th, fl)
        legs.append((kn, an, t2, sd, th))
    order = sorted(legs, key=lambda L: -L[3])
    lr = math.radians(lean)
    ux, uy = math.sin(lr), math.cos(lr)
    px_, py_ = uy, -ux
    sh = (hip[0] + ux * 24, hip[1] + uy * 24)

    def tp(f, a):
        return (hip[0] + ux * a + px_ * f, hip[1] + uy * a + py_ * f)

    def draw_leg(L, idx):
        kn, an, t2, sd, th = L
        pc = _dk(pants, sd)
        pcm = [_dk(c, sd) for c in pcamo]
        rig.fill(_capsule(hip, kn, 5.0, 3.7), pc, pcm, 11 + idx)
        rig.fill(_capsule(kn, an, 3.5, 2.7), pc, pcm, 21 + idx)
        # bolsillo cargo y rodillera
        d = (kn[0] - hip[0], kn[1] - hip[1])
        dl = math.hypot(*d) or 1.0
        dx_, dy_ = d[0] / dl, d[1] / dl
        nx_, ny_ = -dy_, dx_
        c0 = (hip[0] + d[0] * 0.45 + nx_ * 3.0, hip[1] + d[1] * 0.45 + ny_ * 3.0)
        rig.fill([(c0[0] - dx_ * 3.4, c0[1] - dy_ * 3.4), (c0[0] + dx_ * 3.4, c0[1] + dy_ * 3.4),
                  (c0[0] + dx_ * 3.4 + nx_ * 2.1, c0[1] + dy_ * 3.4 + ny_ * 2.1), (c0[0] - dx_ * 3.4 + nx_ * 2.1, c0[1] - dy_ * 3.4 + ny_ * 2.1)], _dk(pc, 14))
        rig.fill(_capsule((kn[0] + dx_ * 0.6, kn[1] + dy_ * 0.6), (kn[0] + dx_ * 1.0, kn[1] + dy_ * 1.0), 3.7, 3.7), _dk(vest, sd // 2))
        # bota con caña, suela y cordones
        toe = 8.4 + (1.0 if heavy else 0.0)
        ax_, ay_ = an
        rig.fill([(ax_ - 3.7, ay_ + 5.2), (ax_ + 3.4, ay_ + 5.2), (ax_ + 3.8, ay_ + 0.6), (ax_ + toe - 2.0, ay_ - 0.5), (ax_ + toe, ay_ - 2.6),
                  (ax_ + toe - 0.2, ay_ - 4.4), (ax_ - 4.2, ay_ - 4.4)], _dk(boot, sd // 3))
        rig.fill([(ax_ - 4.4, ay_ - 3.6), (ax_ + toe + 0.1, ay_ - 3.6), (ax_ + toe + 0.1, ay_ - 4.8), (ax_ - 4.4, ay_ - 4.8)], (18, 16, 16))
        for k in range(4):
            rig.line((ax_ + 0.2, ay_ + 3.6 - k * 1.2), (ax_ + 3.0, ay_ + 3.0 - k * 1.2), 0.35, (130, 124, 110))
        rig.fill([(ax_ - 3.4, ay_ + 5.8), (ax_ + 3.2, ay_ + 5.8), (ax_ + 3.4, ay_ + 4.6), (ax_ - 3.6, ay_ + 4.6)], _dk(pc, 24 + sd // 3))

    draw_leg(order[0], 0)
    # mochila / camelbak
    pk = [tp(-6.4, 3), tp(-12.4, 5), tp(-13.4, 19), tp(-7.4, 22)]
    rig.fill(pk, look['vest'] if kind != 'pow' else (150, 140, 120))
    rig.fill([tp(-7.0, 8), tp(-11.0, 8.6), tp(-11.6, 16), tp(-7.0, 17)], _dk(look['vest'], 16))
    if kind == 'flame':
        rig.fill([tp(-6.2, 4), tp(-12.6, 4), tp(-13.2, 20), tp(-6.2, 21)], (186, 70, 44))
        rig.fill([tp(-12.2, 6), tp(-13.4, 6), tp(-13.8, 19), tp(-12.2, 19)], (130, 44, 28))
        rig.line(tp(-9, 21), tp(-9, 24), 1.0, (210, 210, 210))
    # torso (camisa de combate)
    shirt = [tp(-6.4, 0), tp(6.4, 0), tp(7.2, 11), tp(6.8, 23), tp(-6.4, 23), tp(-7.4, 11)]
    if kind == 'knife':
        rig.fill(shirt, _dk(skin, 18), None, 5)
    else:
        rig.fill(shirt, body, camo, 1, None, 3)
    # cinturón táctico
    rig.fill([tp(-5.8, 0.4), tp(6.0, 0.4), tp(6.0, 3.2), tp(-5.8, 3.2)], (34, 30, 28))
    rig.fill([tp(2.2, 0.6), tp(4.4, 0.6), tp(4.4, 2.9), tp(2.2, 2.9)], (176, 160, 100))
    # funda de pistola y bolsas
    rig.fill([tp(-1.0, -1.6), tp(3.6, -1.6), tp(3.6, 1.4), tp(-1.0, 1.4)], (40, 38, 38))
    # chaleco portaplacas
    if kind == 'knife':
        rig.fill([tp(-2.0, 5), tp(5.6, 6), tp(6.0, 12), tp(5.2, 22), tp(1.0, 22)], vest, None, 2)
    elif kind != 'pow':
        vf = 8.0 if heavy else 7.4
        rig.fill([tp(-6.6, 3.5), tp(vf, 3.5), tp(vf + 0.4, 12), tp(vf - 0.4, 22.5), tp(-6.6, 22.5)], vest, None, 3, None, 2)
        for a_ in (7.0, 12.2):
            rig.fill([tp(1.2, a_), tp(vf - 0.2, a_), tp(vf - 0.2, a_ + 4.4), tp(1.2, a_ + 4.4)], _dk(vest, 14))
            rig.fill([tp(1.2, a_ + 3.4), tp(vf - 0.2, a_ + 3.4), tp(vf - 0.2, a_ + 4.4), tp(1.2, a_ + 4.4)], _lt(vest, 16))
            rig.line(tp(2.6, a_ + 0.6), tp(2.6, a_ + 3.6), 0.35, (20, 18, 20))
            rig.line(tp(4.6, a_ + 0.6), tp(4.6, a_ + 3.6), 0.35, (20, 18, 20))
        for k_ in range(3):                          # fila MOLLE
            rig.line(tp(-4.4, 5.5 + k_ * 5.0), tp(-0.6, 5.5 + k_ * 5.0), 0.35, _dk(vest, 26))
        rig.circ(tp(vf - 1.0, 19.4), 1.5, acc if kind in ('player', 'rifle', 'gren') else _dk(vest, 8))     # parche / radio
        if kind in ('player', 'gren', 'shield'):
            for k_ in range(2):                      # granadas
                c_ = tp(-1.4 - k_ * 2.6, 4.6)
                rig.circ(c_, 1.8, (74, 92, 62))
                rig.circ((c_[0], c_[1] + 1.9), 0.6, (180, 180, 170))
    else:
        rig.fill([tp(-5.8, 3.5), tp(6.0, 3.5), tp(6.4, 12), tp(5.8, 22.5), tp(-5.8, 22.5)], _dk(body, 12), None, 3, None, 2)
    if heavy:
        rig.fill([tp(-6.4, 23), tp(8.8, 22), tp(8.6, 18), tp(-4.4, 19.4)], _lt(vest, 6))      # hombrera blindada
    draw_leg(order[1], 1)
    # cuello y cabeza
    neck = tp(0.8, 23)
    head = (neck[0] + ux * 6.0 + px_ * 1.6, neck[1] + uy * 6.0 + py_ * 1.6)
    hx, hy_ = head
    rig.fill(_capsule((sh[0] + px_ * 0.6, sh[1] + py_ * 0.6), (neck[0], neck[1] + 2.0), 3.0, 2.7), _dk(skin, 22))

    def hp_(x, y):
        return (hx + x, hy_ + y)
    face = [hp_(3.6, 4.4), hp_(5.0, 2.2), hp_(5.4, 0.8), hp_(6.3, -0.4), hp_(5.2, -1.4), hp_(5.2, -2.8), hp_(4.4, -5.0), hp_(1.4, -6.2),
            hp_(-2.6, -5.0), hp_(-5.0, -1.4), hp_(-4.8, 3.0), hp_(-2.4, 5.8), hp_(1.6, 6.2)]
    sniper = kind == 'sniper'
    if kind == 'pow':
        rig.fill(face, skin)
        rig.fill([hp_(1.0, -2.6), hp_(5.2, -2.6), hp_(4.6, -6.4), hp_(0.6, -7.2), hp_(-2.6, -5.4)], (88, 66, 44))               # barba
        rig.fill([hp_(-5.0, 1.0), hp_(-4.4, 6.0), hp_(0.6, 7.6), hp_(4.8, 5.4), hp_(5.2, 3.0), hp_(1.4, 3.8), hp_(-2.0, 1.6)], helm)          # pelo
        rig.fill([hp_(2.2, -0.4), hp_(5.4, 0.2), hp_(5.2, 1.0), hp_(2.2, 0.6)], (230, 230, 230))                                          # venda
    else:
        rig.fill(face, skin)
        # sombra de barba / mascarilla
        if look['mask']:
            rig.fill([hp_(0.6, -0.8), hp_(5.4, -1.2), hp_(5.6, -2.8), hp_(4.6, -5.2), hp_(1.4, -6.6), hp_(-2.8, -5.4), hp_(-5.0, -1.6), hp_(-2.0, -1.0)], (34, 32, 38))
            rig.fill([hp_(-5.0, -1.6), hp_(-4.4, -7.2), hp_(0, -9.4), hp_(3.0, -7.4)], (34, 32, 38))
        else:
            rig.fill([hp_(1.2, -2.4), hp_(5.2, -2.6), hp_(4.6, -5.0), hp_(1.4, -6.2), hp_(-1.8, -5.0)], _dk(skin, 26))
        # ojo, ceja, oreja
        rig.fill([hp_(2.4, 1.6), hp_(4.6, 1.6), hp_(4.6, 0.7), hp_(2.4, 0.5)], (236, 232, 224))
        rig.circ(hp_(3.9, 1.1), 0.6, (24, 22, 28))
        rig.line(hp_(2.0, 2.5), hp_(5.2, 2.3), 0.55, _dk(skin, 78))
        rig.fill(_capsule(hp_(-2.6, 0.2), hp_(-2.6, -1.6), 1.1, 0.9), _dk(skin, 34))
        if kind == 'knife':
            fl = math.sin(t * 3.0) * 1.4
            rig.fill([hp_(-5.2, 3.4), hp_(5.6, 4.2), hp_(5.4, 6.4), hp_(-5.0, 5.6)], helm)
            rig.fill([hp_(-5.0, 4.0), hp_(-12.4, 2.4 + fl), hp_(-13.6, 4.8 + fl), hp_(-5.0, 5.6)], _dk(helm, 18))
            for k_ in range(5):
                rig.fill([hp_(-4 + k_ * 2.4, 5.4), hp_(-3 + k_ * 2.4, 9.4), hp_(-2 + k_ * 2.4, 5.4)], (36, 28, 26))
        elif sniper:
            hood = [hp_(-6.6, -3.8), hp_(-5.8, 5.4), hp_(0, 8.8), hp_(5.6, 6.2), hp_(6.4, 3.0), hp_(2.6, 3.4), hp_(2.6, -0.2), hp_(5.6, -1.2), hp_(5.2, -5.4), hp_(0.4, -7.6)]
            rig.fill(hood, helm, [(50, 70, 44), (104, 120, 76), (40, 54, 36)], 5)
            rig.fill([hp_(-6.0, 2.0), hp_(-9.6, 0), hp_(-9.0, -3.6), hp_(-6.6, -3.8)], _dk(helm, 12), [(50, 70, 44)], 6)
        else:
            # casco con cubierta, riel y soportes
            shell = [hp_(5.8, 3.6), hp_(5.2, 5.8), hp_(2.6, 8.6), hp_(-2.0, 9.0), hp_(-6.0, 6.4), hp_(-7.2, 1.6), hp_(-6.6, -2.4), hp_(-4.6, -3.0), hp_(-3.6, 1.2), hp_(0.6, 3.0)]
            if kind == 'player':
                rig.fill(shell, helm, [(86, 80, 60), (122, 112, 86)], 8)
            else:
                rig.fill(shell, helm, [_dk(helm, 12), _lt(helm, 14)], 8)
            rig.fill([hp_(5.8, 3.6), hp_(7.6, 3.2), hp_(7.4, 4.6), hp_(5.4, 5.4)], _dk(helm, 30))               # visera
            rig.line(hp_(-6.4, 1.8), hp_(5.4, 3.4), 0.6, _dk(helm, 38))
            rig.line(hp_(1.4, 3.2), hp_(2.0, -4.8), 0.5, (22, 20, 20))                                           # barboquejo
            rig.fill(_capsule(hp_(-2.4, 0.4), hp_(-2.4, -1.4), 2.0, 1.8), (30, 30, 34))                          # auricular
            if kind == 'player':
                rig.fill([hp_(5.4, 5.4), hp_(8.4, 5.6), hp_(8.4, 8.0), hp_(5.4, 8.0)], (24, 26, 30))              # soporte de visión nocturna
                rig.fill([hp_(5.2, 3.9), hp_(8.0, 3.7), hp_(8.0, 5.3), hp_(5.2, 5.5)], acc)                      # gafas sobre el casco
                rig.line(hp_(-1.0, -2.0), hp_(3.6, -3.2), 0.45, (24, 24, 28))                                    # micrófono
            elif kind in ('gren', 'shield', 'flame'):
                rig.fill([hp_(2.2, 2.4), hp_(7.4, 2.8), hp_(7.2, 0.0), hp_(2.2, -0.2)], acc if kind != 'shield' else (130, 200, 226))
            else:
                rig.fill([hp_(3.0, 2.2), hp_(6.6, 2.4), hp_(6.4, 0.4), hp_(3.0, 0.2)], acc)
    if fem:                                                                      # coleta de las soldados (+y es hacia arriba en este lienzo)
        hair = (176, 118, 62) if kind == 'player' else (44, 30, 26)
        sway = math.sin(t * 3.0) * 1.2 + (i % 4) * 0.2
        rig.fill([hp_(-4.2, 4.0), hp_(-7.4, 2.4), hp_(-9.8 - sway, -3.4), hp_(-10.4 - sway, -15.0), hp_(-7.4 - sway * 0.6, -14.0), hp_(-6.4, -3.0), hp_(-3.6, -0.4)], hair)
        rig.fill([hp_(-6.4, 1.2), hp_(-8.2 - sway * 0.5, -2.8), hp_(-8.8 - sway, -13.0), hp_(-7.4, -3.0)], _lt(hair, 26))
        rig.circ(hp_(-5.4, 2.8), 1.2, (210, 70, 90))                              # moño
    surf = rig.finish()
    s_ang = math.radians(fall)
    sx_, sy_ = sh
    shx = sx_ * math.cos(s_ang) - sy_ * math.sin(s_ang)
    shy = sx_ * math.sin(s_ang) + sy_ * math.cos(s_ang)
    return surf, shx * PT_K, shy * PT_K


def _arm(rig, sh, elbow, wrist, sleeve, camo, skin, glove, bare=False, seed=0):
    """Brazo cónico con manga de camuflaje, coderera y guante."""
    col = skin if bare else sleeve
    rig.fill(_capsule(sh, elbow, 3.8, 3.0), col, None if bare else camo, seed, None, 0 if bare else 2)
    rig.fill(_capsule(elbow, wrist, 2.9, 2.3), skin if bare else _dk(sleeve, 4), None if bare else camo, seed + 1)
    if not bare:
        rig.fill(_capsule((elbow[0], elbow[1]), (elbow[0] + 0.5, elbow[1] - 0.2), 3.0, 3.0), _dk(sleeve, 30))
    rig.fill(_capsule(wrist, (wrist[0] + (wrist[0] - elbow[0]) * 0.18, wrist[1] + (wrist[1] - elbow[1]) * 0.18), 2.5, 2.2), glove)


def _arm_layer(kind, mode):
    """Brazos + arma apuntando a +x con el hombro en el centro del lienzo (pivote)."""
    look = PT_LOOK[kind]
    rig = _Rig(0.0, 170, 170, 85, 85)
    body, skin, camo = look['body'], look['skin'], look['camo']
    bare = kind == 'knife'
    glove = (36, 34, 36)
    sleeve = body
    if mode == 'shield':
        _arm(rig, (0, 0), (5, -7), (16, -3), sleeve, camo, skin, glove, bare, 2)
        plate = [(14, 17), (26, 15), (26.4, -52), (14, -55)]
        rig.fill(plate, (74, 82, 96))
        rig.fill([(14, 17), (17.4, 16.6), (17.4, -55), (14, -55)], (122, 132, 148))
        rig.fill([(17.8, 10.4), (24.4, 10.0), (24.4, 5.6), (17.8, 6.0)], (120, 190, 220))
        rig.fill([(17.8, 9.4), (24.4, 9.0), (24.4, 7.4), (17.8, 7.8)], (200, 235, 250))
        for k_ in range(3):
            rig.fill([(17.8, -8 - k_ * 9), (24.4, -3 - k_ * 9), (24.4, -6.8 - k_ * 9), (17.8, -11.8 - k_ * 9)], (222, 188, 50))
        for k_ in range(6):
            rnd = random.Random(k_ * 5)
            rig.line((15 + rnd.uniform(0, 8), -2 - rnd.uniform(0, 40)), (18 + rnd.uniform(0, 8), -6 - rnd.uniform(0, 40)), 0.35, (50, 56, 68))
        rig.fill(_capsule((16, -3), (16.2, -3.2), 2.6, 2.6), glove)
        return rig.finish()
    if mode == 'knife':
        _arm(rig, (0, 0.4), (6, -9), (7.6, -9.4), _dk(sleeve, 16), camo, skin, glove, True, 4)
        _arm(rig, (0, 0), (9, -6.5), (22, -1.0), sleeve, camo, skin, glove, True, 3)
        rig.fill([(23.4, -2.2), (28, -2.2), (28, 1.2), (23.4, 1.2)], (44, 36, 32))
        rig.fill([(27.6, -1.8), (46, -0.4), (27.6, 1.2)], (196, 202, 210))
        rig.fill([(27.6, -0.8), (43, 0), (27.6, 0.2)], (248, 250, 252))
        for k_ in range(5):
            rig.line((30 + k_ * 3, 1.0), (31 + k_ * 3, 2.0), 0.4, (150, 156, 164))
        return rig.finish()
    if mode in ('wind', 'rel'):
        if mode == 'wind':
            el, wr = (-7, 8), (-4.4, 20)
            gp = (-3.4, 22.4)
        else:
            el, wr = (9, 5), (20, 11)
            gp = (22, 12.6)
        _arm(rig, (0, 0), el, wr, sleeve, camo, skin, glove, bare, 5)
        rig.fill(_capsule(gp, (gp[0] + 0.3, gp[1] + 0.3), 2.6, 2.6), glove)
        rig.fill(_capsule((gp[0] + 1.0, gp[1] + 3.0), (gp[0] + 1.0, gp[1] + 5.6), 3.2, 3.0), (72, 92, 60))       # granada de fragmentación
        rig.fill(_capsule((gp[0] + 1.0, gp[1] + 7.6), (gp[0] + 1.0, gp[1] + 8.6), 1.4, 1.2), (150, 150, 146))
        rig.line((gp[0] + 2.2, gp[1] + 8.6), (gp[0] + 5.0, gp[1] + 5.0), 0.5, (170, 170, 165))
        _arm(rig, (0, 0.6), (4, -8), (5.4, -9.4), _dk(sleeve, 16), camo, skin, glove, bare, 6)
        return rig.finish()
    # ---- armas de fuego
    if kind == 'flame':
        _arm(rig, (0, 0), (3.5, -7.5), (13, -3.2), _dk(sleeve, 14), camo, skin, glove, bare, 7)
        rig.fill([(-6, -3.4), (4, -3.8), (4, 3.6), (-6, 3.8)], (58, 54, 50))
        rig.fill([(4, -2.8), (42, -2.2), (42, 2.2), (4, 2.8)], (56, 58, 64))
        rig.fill([(4, 1.4), (42, 1.6), (42, 2.2), (4, 2.8)], (110, 114, 124))
        rig.fill([(42, -3.8), (50, -4.6), (50, 4.6), (42, 3.8)], (200, 84, 42))
        rig.circ((51, 0), 1.9, (255, 230, 150))
        rig.line((-6, -2), (-14, -9), 1.3, (30, 30, 34))
        _arm(rig, (0, 0.8), (9, -8.8), (30, -2.0), sleeve, camo, skin, glove, bare, 8)
        return rig.finish()
    long = kind == 'sniper'
    ak = kind in ('rifle', 'gren', 'shield')
    _arm(rig, (0, 0), (3.5, -7.5), (13, -3.2), _dk(sleeve, 14), camo, skin, glove, bare, 7)
    if long:
        L = 78
        wood, mc = (92, 74, 54), (40, 42, 46)
        rig.fill([(-14, -5.0), (6, -3.4), (6, 3.6), (-14, 4.6)], wood)                      # culata de madera
        rig.fill([(-14, -5.0), (-11.4, -5.2), (-11.4, 4.8), (-14, 4.6)], _dk(wood, 34))
        rig.fill([(6, -4.0), (30, -4.0), (30, 3.0), (6, 3.0)], mc)
        rig.fill([(30, -3.0), (L - 12, -2.6), (L - 12, 2.0), (30, 2.4)], wood)
        rig.fill([(L - 12, -1.4), (L - 4, -1.2), (L - 4, 1.0), (L - 12, 1.2)], (26, 26, 30))
        rig.fill([(L - 4, -2.4), (L + 14, -2.4), (L + 14, 2.2), (L - 4, 2.2)], (30, 32, 36))     # silenciador
        rig.fill([(L - 4, 0.6), (L + 14, 0.6), (L + 14, 2.2), (L - 4, 2.2)], (62, 64, 70))
        rig.fill([(14, 3.0), (36, 3.0), (36, 9.6), (14, 9.6)], (30, 32, 38))                  # mira telescópica
        rig.fill([(34, 2.4), (40, 3.0), (40, 10.2), (34, 9.8)], (22, 24, 28))
        rig.circ((40.6, 6.4), 2.8, (86, 160, 210))
        rig.circ((40.8, 6.8), 1.0, (210, 240, 255))
        rig.line((L - 12, 1), (L - 15, -9), 0.8, (30, 30, 34))
        rig.line((L - 12, 1), (L - 8, -9), 0.8, (30, 30, 34))
        gx = L - 22
    elif ak:
        L = 56
        wood, mc = (118, 78, 44), (36, 36, 40)
        rig.fill([(-13, -5.4), (4, -3.0), (4, 3.0), (-13, 2.8)], wood)                         # culata
        rig.fill([(-13, -5.4), (-10.6, -5.6), (-10.6, 2.8), (-13, 2.8)], _dk(wood, 34))
        rig.fill([(4, -4.2), (26, -4.0), (26, 3.0), (4, 3.2)], mc)                            # receptor
        rig.fill([(5, 3.0), (25, 3.0), (25, 4.4), (5, 4.4)], (28, 28, 32))
        rig.fill([(26, -3.4), (40, -3.0), (40, 2.4), (26, 2.4)], wood)                        # guardamanos
        rig.fill([(40, -2.4), (L - 4, -2.0), (L - 4, 1.4), (40, 1.8)], (46, 44, 40))
        rig.fill([(26, 2.4), (L - 8, 2.2), (L - 8, 3.4), (26, 3.6)], (50, 50, 52))               # tubo de gases
        rig.fill([(L - 4, -1.0), (L + 6, -0.8), (L + 6, 0.8), (L - 4, 1.0)], (24, 24, 28))
        rig.fill([(L + 4, 0.8), (L + 5.4, 0.8), (L + 5.4, 3.4), (L + 4, 3.4)], (30, 30, 34))     # punto de mira
        rig.fill([(14, -4.0), (21, -4.0), (24, -16), (16.4, -15)], (78, 52, 34))                # cargador curvo
        rig.fill([(8, -4.0), (11.6, -4.0), (12.4, -10.4), (8.6, -10.4)], (30, 30, 34))
        gx = 40
    else:
        L = 52
        mc = (44, 46, 50)
        rig.fill([(-15, -5.4), (2, -3.0), (2, 2.4), (-15, 1.4)], (52, 54, 58))                # culata telescópica
        rig.fill([(-15, -5.4), (-12.4, -5.6), (-12.4, 1.4), (-15, 1.4)], (30, 30, 34))
        rig.fill([(2, -4.6), (26, -4.6), (26, 2.8), (2, 2.8)], mc)                            # cajón
        rig.fill([(8, 2.8), (24, 2.8), (24, 4.2), (8, 4.2)], (30, 30, 34))                    # riel superior
        rig.fill([(26, -3.4), (44, -3.2), (44, 2.2), (26, 2.4)], (56, 58, 62))                # guardamanos
        for k_ in range(5):
            rig.line((28 + k_ * 3.4, -3.0), (28 + k_ * 3.4, 2.0), 0.35, (30, 32, 36))
        rig.fill([(44, -1.4), (L, -1.2), (L, 1.0), (44, 1.2)], (28, 28, 32))
        rig.fill([(L, -2.2), (L + 6, -2.0), (L + 6, 1.8), (L, 2.0)], (22, 22, 26))              # supresor / apagallamas
        rig.fill([(12, -4.6), (18.6, -4.6), (20.4, -15), (14.2, -14.4)], (36, 38, 42))         # cargador
        rig.fill([(6.2, -4.6), (9.6, -4.6), (11.2, -12.6), (8, -12.6)], (40, 42, 46))          # empuñadura
        rig.fill([(8, 4.2), (20, 4.2), (20, 7.4), (8, 7.4)], (28, 30, 34))                    # mira
        rig.circ((19.2, 5.9), 1.7, (230, 70, 60))
        gx = 33
    _arm(rig, (0, 0.8), (9, -8.8), (gx, -1.8), sleeve, camo, skin, glove, bare, 8)
    rig.fill(_capsule((13, -2.6), (13.4, -2.8), 2.5, 2.5), glove)
    return rig.finish()


POSE_MAP = {'run': 'correr', 'idle': 'reposo', 'crouch': 'agachado', 'jump': 'salto', 'fall': 'caida', 'die': 'muerte',
            'wind': 'granada_preparar', 'rel': 'granada_lanzar', 'up': 'arriba', 'down': 'abajo', 'attack': 'ataque'}
BAKED_FILES = {'player': 'soldado', 'player_f': 'soldada', 'knife': 'cuchillero', 'knife_f': 'cuchillera', 'sniper': 'francotirador', 'sniper_f': 'francotiradora',
               'gren': 'granadero', 'rifle': 'fusilero', 'rifle_f': 'fusilera', 'shield': 'escudero'}


def load_baked_soldier(art, kind):
    """Soldado dibujado a mano (soldados/<nombre>.png + .json): cuadros ya con el arma incluida. Si falta, se usa el dibujo por código."""
    import json
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'soldados', BAKED_FILES[kind])
    try:
        meta = json.load(open(base + '.json'))
        atlas = pygame.image.load(base + '.png').convert_alpha()
    except (OSError, ValueError, pygame.error):
        return
    cw, ch, ax, ay = meta['_canvas']
    frames, mz = {}, {}
    for pose, key in POSE_MAP.items():
        m = meta.get(key)
        if not m:
            continue
        frames[pose] = [(atlas.subsurface(pygame.Rect(i * cw, m['row'] * ch, cw, ch)).copy(), 0, 0) for i in range(m['n'])]
        mz[pose] = m['muzzle']
    for key, m in meta.items():                              # cuadros extra (apuntar_0..4: arma a 30° abajo, horizontal y 20°, 35° y 55° arriba)
        if key.startswith(('apuntar_', 'correr_a_')):
            frames[key] = [(atlas.subsurface(pygame.Rect(i * cw, m['row'] * ch, cw, ch)).copy(), 0, 0) for i in range(m['n'])]
            mz[key] = m['muzzle']
    if not all(p in frames for p in ('run', 'idle', 'crouch', 'jump', 'fall', 'die')):
        return
    art['body'][kind] = frames
    art.setdefault('baked', {})[kind] = dict(mz=mz, anchor=(ax, ay))


def build_pt_art():
    """Pre-renderiza todos los cuadros de los soldados (lado derecho; el izquierdo se espeja)."""
    art = {'body': {}, 'arm': {}, 'rot': {}}
    for fk in ('player_f', 'rifle_f', 'knife_f', 'sniper_f'):                       # variantes femeninas (los brazos y el arma son iguales)
        art['body'][fk] = {pose: [_body_frame(fk, pose, i, i * 0.5) for i in range(n)]
                           for pose, n in (('run', 8), ('idle', 4), ('crouch', 1), ('jump', 1), ('fall', 1), ('die', 6))}
    for kind in PT_LOOK:
        frames = {}
        for pose, n in (('run', 8), ('idle', 4), ('crouch', 1), ('jump', 1), ('fall', 1), ('die', 6)):
            frames[pose] = [_body_frame(kind, pose, i, i * 0.5) for i in range(n)]
        art['body'][kind] = frames
        modes = {'shield': ['shield'], 'flame': ['gun'], 'pow': [], 'knife': ['knife', 'wind', 'rel']}.get(kind) or (['gun'] if kind in ('player', 'rifle', 'sniper') else ['gun', 'wind', 'rel'])
        art['arm'][kind] = {m: _arm_layer(kind, m) for m in modes}
        if kind in ('shield', 'flame', 'pow'):
            continue
        if 'wind' not in art['arm'][kind]:
            art['arm'][kind]['wind'] = _arm_layer(kind, 'wind')
            art['arm'][kind]['rel'] = _arm_layer(kind, 'rel')
    for fk in ('player_f', 'rifle_f', 'knife_f', 'sniper_f'):
        art['arm'][fk] = art['arm'][fk[:-2]]
    for kd in BAKED_FILES:
        load_baked_soldier(art, kd)
    for kd in ('knife',):                                  # mientras no exista la versión mujer, usa el dibujo del hombre
        if kd in art.get('baked', {}) and kd + '_f' not in art['baked']:
            art['body'][kd + '_f'] = art['body'][kd]
            art['baked'][kd + '_f'] = art['baked'][kd]
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


def _vgrad_rect(s, rect, c0, c1, radius=0):
    """Rectángulo con degradado vertical (arriba c0, abajo c1)."""
    x, y, w, h = [int(v) for v in rect]
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(h):
        k = i / max(1, h - 1)
        pygame.draw.line(tmp, (int(c0[0] + (c1[0] - c0[0]) * k), int(c0[1] + (c1[1] - c0[1]) * k), int(c0[2] + (c1[2] - c0[2]) * k), 255), (0, i), (w, i))
    if radius:
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        tmp.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(tmp, (x, y))


def build_pt_bunker():
    """Nido de ametralladora: sacos de arena, pedestal de hormigón con franjas de aviso y una cúpula blindada giratoria;
    el cañón automático (con ventilación, freno de boca y cajón de munición) se rota aparte."""
    K = 4
    out = (24, 20, 18)
    s = pygame.Surface((110 * K, 70 * K), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 100), (2 * K, 59 * K, 106 * K, 10 * K))
    # pedestal de hormigón con paneles
    ped = [(34 * K, 64 * K), (76 * K, 64 * K), (70 * K, 30 * K), (40 * K, 30 * K)]
    pygame.draw.polygon(s, (104, 108, 110), ped)
    _vgrad_rect(s, (40 * K, 30 * K, 30 * K, 34 * K), (132, 136, 138), (78, 82, 86))
    pygame.draw.polygon(s, out, ped, K)
    for yy in (40, 50):
        pygame.draw.line(s, (62, 66, 70), (37 * K, yy * K), (73 * K, yy * K), K)
    for xx in (46, 64):
        pygame.draw.circle(s, (58, 62, 66), (xx * K, 35 * K), int(1.2 * K))
    # franja de aviso amarilla y negra en la base
    for i in range(0, 38, 8):
        pygame.draw.polygon(s, (232, 192, 40), [((34 + i) * K, 64 * K), ((42 + i) * K, 64 * K), ((46 + i) * K, 58 * K), ((38 + i) * K, 58 * K)])
    pygame.draw.rect(s, out, (34 * K, 58 * K, 42 * K, 6 * K), K)
    # sacos de arena a ambos lados (con sombra inferior, brillo y costuras)
    rnd = random.Random(2)
    for side in (-1, 1):
        for row in range(3):
            n = 4 - row
            for i in range(n):
                bx = (35 - 21 * (i + 1) - row * 7) if side < 0 else (75 + 21 * i + row * 7)
                by = 62 - row * 10
                base_c = rnd.choice(((190, 164, 112), (176, 150, 100), (200, 174, 122)))
                r = (bx * K, (by - 12) * K, 22 * K, 13 * K)
                pygame.draw.ellipse(s, shade(base_c, -46), (r[0], r[1] + K, r[2], r[3]))
                pygame.draw.ellipse(s, base_c, r)
                pygame.draw.ellipse(s, shade(base_c, 26), (r[0] + 3 * K, r[1] + K, 14 * K, 4 * K))
                pygame.draw.ellipse(s, out, r, K)
                pygame.draw.line(s, shade(base_c, -34), (r[0] + 6 * K, r[1] + 7 * K), (r[0] + 16 * K, r[1] + 7 * K), K)
                for t in (8, 11, 14):
                    pygame.draw.line(s, shade(base_c, -34), (r[0] + t * K, r[1] + 5 * K), (r[0] + t * K, r[1] + 9 * K), max(1, K // 2))
    # faldón blindado y cúpula giratoria
    _vgrad_rect(s, (36 * K, 20 * K, 38 * K, 14 * K), (96, 102, 100), (58, 62, 62), 3 * K)
    pygame.draw.rect(s, out, (36 * K, 20 * K, 38 * K, 14 * K), K, border_radius=3 * K)
    cx, cy, rr = 55 * K, 16 * K, 17 * K
    pygame.draw.circle(s, (46, 50, 52), (cx, cy + K), rr)
    dome = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
    for i in range(rr * 2):                                              # esfera con degradado vertical y brillo a la derecha
        k = i / (rr * 2 - 1)
        c = (int(150 - 90 * k), int(156 - 92 * k), int(156 - 90 * k))
        pygame.draw.line(dome, (*c, 255), (0, i), (rr * 2, i))
    mk = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
    pygame.draw.circle(mk, (255, 255, 255, 255), (rr, rr), rr)
    dome.blit(mk, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(dome, (cx - rr, cy - rr))
    pygame.draw.circle(s, out, (cx, cy), rr, K)
    pygame.draw.arc(s, (212, 218, 214), (cx - rr + 3 * K, cy - rr + 3 * K, rr * 2 - 6 * K, rr * 2 - 6 * K), 0.5, 1.9, K)
    for ang in (0.9, 2.3, 3.7, 5.2):                                     # remaches
        pygame.draw.circle(s, (40, 44, 46), (int(cx + math.cos(ang) * rr * 0.62), int(cy + math.sin(ang) * rr * 0.62)), int(1.2 * K))
    pygame.draw.circle(s, (30, 34, 36), (cx, cy), 5 * K)                  # rótula del cañón
    pygame.draw.circle(s, (86, 92, 92), (cx - K, cy - K), 2 * K)
    # cajón de munición y cinta a un costado
    pygame.draw.rect(s, (74, 86, 58), (82 * K, 40 * K, 14 * K, 10 * K), border_radius=K)
    pygame.draw.rect(s, out, (82 * K, 40 * K, 14 * K, 10 * K), K, border_radius=K)
    pygame.draw.line(s, (120, 134, 96), (84 * K, 42 * K), (94 * K, 42 * K), K)
    for i in range(5):
        pygame.draw.rect(s, (214, 170, 60), ((83 + i * 2) * K, 36 * K, int(1.4 * K), 4 * K))
    base = _smooth(s, K)
    # cañón automático: apunta a la derecha, eje de giro en (8, 12)
    g = pygame.Surface((70 * K, 24 * K), pygame.SRCALPHA)
    pygame.draw.rect(g, out, (2 * K, 7 * K, 58 * K, 10 * K), border_radius=K)               # camisa del cañón
    _vgrad_rect(g, (3 * K, 8 * K, 56 * K, 8 * K), (118, 124, 122), (50, 54, 54))
    for i in range(6):                                                                      # ranuras de ventilación
        pygame.draw.rect(g, (20, 22, 22), ((16 + i * 6) * K, 9 * K, int(2.4 * K), 6 * K), border_radius=K // 2)
    pygame.draw.rect(g, (28, 30, 30), (56 * K, 8 * K, 10 * K, 8 * K), border_radius=K)       # freno de boca
    pygame.draw.rect(g, out, (56 * K, 8 * K, 10 * K, 8 * K), K, border_radius=K)
    pygame.draw.line(g, (6, 6, 6), (64 * K, 9 * K), (64 * K, 15 * K), K)
    pygame.draw.rect(g, (20, 20, 22), (66 * K, 10 * K, 4 * K, 4 * K))
    _vgrad_rect(g, (0, 4 * K, 24 * K, 16 * K), (104, 110, 106), (56, 60, 60), 3 * K)         # recámara
    pygame.draw.rect(g, out, (0, 4 * K, 24 * K, 16 * K), K, border_radius=3 * K)
    pygame.draw.rect(g, (190, 196, 190), (3 * K, 5 * K, 14 * K, int(1.6 * K)))
    pygame.draw.rect(g, (24, 26, 26), (19 * K, 9 * K, 3 * K, 6 * K))
    pygame.draw.rect(g, (74, 86, 58), (7 * K, 19 * K, 12 * K, 5 * K), border_radius=K)       # cajón de alimentación
    pygame.draw.rect(g, out, (7 * K, 19 * K, 12 * K, 5 * K), K, border_radius=K)
    pygame.draw.circle(g, (206, 60, 50), (21 * K, 6 * K), int(1.3 * K))                        # piloto rojo de "armado"
    gun = _smooth(g, K)
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


def rim_light(img, col=(255, 214, 160), a_top=150, a_front=110):
    """Luz de borde: ilumina el contorno superior y el derecho del sprite (la luz del atardecer viene de la derecha y de arriba)."""
    m = pygame.mask.from_surface(img, 90)
    w, h = img.get_size()
    out = img.copy()
    for (dx, dy), alpha in (((0, 1), a_top), ((-1, 0), a_front)):
        sh = pygame.mask.Mask((w, h))
        sh.draw(m, (dx, dy))
        edge = m.copy()
        edge.erase(sh, (0, 0))
        out.blit(edge.to_surface(setcolor=(*col, alpha), unsetcolor=(0, 0, 0, 0)), (0, 0))
    return out
