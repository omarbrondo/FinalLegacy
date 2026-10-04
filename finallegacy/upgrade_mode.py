"""Pantalla de mejoras entre oleadas: se elige 1 de 3."""
import math
import pygame
import random
from .common import W

UPGRADES = {
    'hull': ('CASCO REFORZADO', 'Casco máximo +25 y reparación completa', (110, 220, 140)),
    'repair': ('TALLER DE CAMPAÑA', 'Casco y combustible al 100%', (120, 200, 255)),
    'ammo': ('ARSENAL', '+20 de munición', (255, 210, 90)),
    'reload': ('RECARGA RÁPIDA', 'Cañones, interceptores y tanque -20% de recarga', (255, 150, 90)),
    'homing': ('MISILES TELEDIRIGIDOS', 'En combate aéreo tus misiles guiados son permanentes', (200, 150, 255)),
    'nano': ('NANO-REPARACIÓN', 'El casco se regenera lentamente en el mar', (130, 255, 210)),
    'blast': ('INTERCEPTORES DE ÁREA', 'Explosiones de defensa +20% de radio', (255, 120, 120)),
}


class UpgradeMixin:
    def up_n(self, key):
        return self.up.get(key, 0)

    def up_reload(self):
        return 0.8 ** self.up_n('reload')

    def start_upgrade(self):
        pool = [k for k in UPGRADES if not (k == 'homing' and self.up_n('homing')) and self.up_n(k) < 4]
        random.shuffle(pool)
        self.up_cards = pool[:3]
        self.up_t = 0.0
        self.banners = []
        self.go('upgrade')

    def pick_upgrade(self, i):
        if self.state != 'upgrade' or not 0 <= i < len(self.up_cards) or self.up_t < 0.35:
            return
        k = self.up_cards[i]
        self.up[k] = self.up_n(k) + 1
        if k == 'hull':
            self.hull_max += 25
            self.hull = self.hull_max
        elif k == 'repair':
            self.hull, self.fuel = float(self.hull_max), 100.0
        elif k == 'ammo':
            self.ammo += 20
        self.audio.play('win', .6)
        self.go('map')
        self.banner('OLEADA %d' % self.wave, UPGRADES[k][0] + ' instalado', UPGRADES[k][2], 3.2)
        self.spawn_wave()

    def upd_upgrade(self, dt):
        self.up_t += dt

    def up_card_rect(self, i):
        return pygame.Rect(W // 2 - 510 + i * 350, 250, 320, 340)

    def draw_upgrade(self, cv):
        t = self.t
        self.draw_ocean(cv, t * 20, t * 6, t)
        self.dim(cv, 45)
        self.text(cv, 'MEJORÁ TU FLOTA', self.f_xl, (255, 230, 140), W // 2, 90, 'c')
        self.text(cv, 'Oleada %d  -  elegí 1 de 3  (clic o teclas 1-2-3)' % self.wave, self.f_m, (200, 225, 255), W // 2, 190, 'c')
        mx, my = pygame.mouse.get_pos()
        for i, k in enumerate(self.up_cards):
            name, desc, col = UPGRADES[k]
            r = self.up_card_rect(i)
            hov = r.collidepoint(mx, my)
            rr = r.move(0, -10 if hov else 0)
            self.panel(cv, rr, 215 if hov else 175)
            pygame.draw.rect(cv, col, rr, 3 if hov else 1, border_radius=8)
            ic = (rr.centerx, rr.y + 90)
            pygame.draw.circle(cv, col, ic, 42, 3)
            pygame.draw.circle(cv, col, ic, 6 + int(3 * math.sin(t * 4 + i)))
            self.text(cv, str(i + 1), self.f_l, col, rr.x + 18, rr.y + 12)
            self.text(cv, name, self.f_m, (255, 255, 255), rr.centerx, rr.y + 160, 'c')
            words, line, y = desc.split(), '', rr.y + 205
            for w_ in words:
                if len(line) + len(w_) > 24:
                    self.text(cv, line, self.f_s, (210, 225, 245), rr.centerx, y, 'c')
                    line, y = '', y + 26
                line += (' ' if line else '') + w_
            self.text(cv, line, self.f_s, (210, 225, 245), rr.centerx, y, 'c')
            if self.up_n(k):
                self.text(cv, 'Nivel actual: %d' % self.up_n(k), self.f_s, col, rr.centerx, rr.bottom - 34, 'c')
