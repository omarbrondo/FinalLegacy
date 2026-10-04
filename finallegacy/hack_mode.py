"""Ciberataque al escudo del jefe: minijuego de nodos."""
import math
import pygame
import random
from .common import H, W, clamp, dist, glow


class HackMixin:
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
        tiles = {c: dict(m=m, sol=m, term=c in terms, src=False, fw=False) for c, m in masks.items()}
        free = [c for c, t_ in tiles.items() if not t_['term'] and c != (0, r0)]
        lvl = self.wave
        if lvl >= 5 and len(free) > 8:                  # segunda fuente de energía
            far = sorted(free, key=lambda c: -abs(c[0] - 0))[:max(3, len(free) // 3)]
            c = random.choice(far)
            tiles[c]['src'] = True
            free.remove(c)
        if lvl >= 4:                                    # cortafuegos: girarlos cuesta tiempo
            for c in random.sample(free, min(len(free), lvl // 3 + 1)):
                tiles[c]['fw'] = True
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
        seeds = [c for c, t_ in tiles.items() if t_.get('src')]
        if tiles[root]['m'] & 8:
            seeds.append(root)
        if seeds:
            pw.update(seeds)
            stack = list(seeds)
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
                 gx=96, gy=(H - rows * csz) // 2 + 24, cur=root, kb=False, log=[], logt=0.0, done=set(), vt=self.hack_virus_gap(), glitch=None)
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
        old.update(tiles=new['tiles'], root=new['root'], cur=new['root'], done=set(), phase='play', pt=0.0, vt=self.hack_virus_gap(), glitch=None)
        old['total'] = old['t'] = max(18.0, old['base_total'] - 3.0 * old['fails'])
        self.hack_say('> NUEVO ENLACE  (INTENTO %d)' % (old['fails'] + 1))
        self.hack_say('> RUTA REGENERADA')
        self.audio.play('pickup', .6)

    def hack_virus_gap(self):
        return random.uniform(6.5, 9.0) - min(3.0, 0.5 * self.wave) if self.wave >= 3 else 1e9

    def hack_say(self, s):
        self.h['log'].append(s)
        self.h['log'] = self.h['log'][-9:]

    def hack_rotate(self, cell, k=1):
        h = self.h
        if h['phase'] != 'play' or cell not in h['tiles']:
            return
        t = h['tiles'][cell]
        t['m'] = self.rot_mask(t['m'], k)
        if t.get('fw'):
            h['t'] = max(0.5, h['t'] - 1.5)
            self.hack_say('> CORTAFUEGOS: -1.5 s')
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
            h['vt'] -= dt
            if h['glitch'] is not None:
                h['glitch'][1] -= dt
                if h['glitch'][1] <= 0:
                    cell = h['glitch'][0]
                    h['glitch'] = None
                    h['tiles'][cell]['m'] = self.rot_mask(h['tiles'][cell]['m'], random.choice((1, 2, 3)))
                    h['done'] = set(self.hack_power()[1])
                    self.audio.play('hit', .4)
                    self.hack_say('> VIRUS: NODO CORRUPTO')
            elif h['vt'] <= 0:
                h['vt'] = self.hack_virus_gap()
                pw_ = list(self.hack_power()[0])
                cells = [c for c in pw_ if not h['tiles'][c]['term']] or list(h['tiles'])
                h['glitch'] = [random.choice(cells), 1.0]
                self.hack_say('> ALERTA: VIRUS DETECTADO')
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
        if tile.get('fw'):
            pygame.draw.rect(cv, (255, 90, 70), r, 2, border_radius=10)
            for k in range(4):
                pygame.draw.line(cv, (255, 90, 70), (x + 8 + k * 6, y + sz - 8), (x + 14 + k * 6, y + sz - 14), 2)
        if tile.get('src'):
            glow(cv, x + 14, y + 14, 22, (60, 130, 255), 0.9)
            pygame.draw.polygon(cv, (255, 235, 120), [(x + 14, y + 6), (x + 8, y + 16), (x + 13, y + 16), (x + 11, y + 24), (x + 20, y + 13), (x + 15, y + 13)])
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
                    if h['glitch'] is not None and h['glitch'][0] == (c, r) and int(t * 12) % 2 == 0:
                        pygame.draw.rect(cv, (255, 60, 220), (x + 3, y + 3, cs - 6, cs - 6), 4, border_radius=10)
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
