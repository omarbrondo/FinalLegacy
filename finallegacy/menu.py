"""Menú principal: Nuevo juego, Cargar partida, Opciones (pantalla completa, CRT, instrucciones, cheats) y Salir."""
import pygame
import sys
from .common import H, W, WIN_WAVE

MAIN_ITEMS = ('NUEVO JUEGO', 'CARGAR PARTIDA', 'OPCIONES', 'SALIR')
OPT_ITEMS = ('PANTALLA COMPLETA', 'MODO CRT', 'INSTRUCCIONES', 'CHEATS', 'VOLVER')
HELP_LINES = [
    ('MAPA', 'W/S acelerar y frenar | A/D girar | R en puerto reabastece | L desembarca | H hackea | F disparo antiaéreo'),
    ('DEFENSA', 'Mouse o flechas apuntan | clic o ESPACIO lanzan el interceptor'),
    ('COMBATE NAVAL', 'Mouse apunta | clic lanza un misil recto (¡adelantate!) | clic derecho humo | E huir'),
    ('TIERRA', 'WASD mover | clic disparar | R recargar | ESPACIO o clic derecho granada'),
    ('SIGILO', 'SHIFT agachado | Q pistola o fusil | E noquear o instalar la antena'),
    ('TANQUE', 'W/S avanzar | A/D girar | ESPACIO o clic: cañón'),
    ('AIRE', 'WASD mover | ESPACIO disparar | B bomba'),
    ('JEFE', 'Instalá antenas en las islas (L) y hackeá su escudo con H cerca del buque'),
    ('MANDO', 'Izq. mover | Der. apuntar | RT/A disparar | LT/B granada | X recargar | Y acción'),
    ('GENERAL', 'P o ESC pausa (S guarda, C carga) | M sonido | V gráficos | F11 pantalla completa | F1 CRT'),
    ('OBJETIVO', 'Hundí %d oleadas y salvá al menos una ciudad para ganar' % WIN_WAVE),
]
CHEAT_LINES = [
    ('F2', 'Combate de tanque'), ('F3', 'Combate aéreo'), ('F4', 'Invasión anfibia'), ('F5', 'Rescate de náufragos'),
    ('F6', 'Convoy'), ('F7', 'Puerto enemigo'), ('F8', 'Defensa contra misiles'), ('F9', 'Subir de oleada'),
    ('F10', '+3000 puntos'), ('F12', 'Reabastecer todo'), ('N', 'Ir a un radar enemigo'),
]


class MenuMixin:
    # ------------------------------------------------------------------ estado y geometría
    def menu_reset(self):
        self.tm = dict(page='main', sel=0)

    def menu_items(self):
        p = self.tm['page']
        return MAIN_ITEMS if p == 'main' else (OPT_ITEMS if p == 'opts' else (('MODO INMORTAL', 'VOLVER') if p == 'cheats' else ('VOLVER',)))

    def menu_rects(self):
        p = self.tm['page']
        items = self.menu_items()
        if p == 'main':
            x0, w, y0, h, gap = W // 2 - 240, 480, 330, 62, 14
        elif p == 'opts':
            x0, w, y0, h, gap = W // 2 - 300, 600, 250, 62, 14
        elif p == 'cheats':
            x0, w, y0, h, gap = W // 2 - 300, 600, 590, 52, 12
            return [pygame.Rect(x0, y0 + i * (h + gap), w, h) for i in range(len(items))]
        else:
            x0, w, y0, h, gap = W // 2 - 160, 320, 700, 52, 12
        return [pygame.Rect(x0, y0 + i * (h + gap), w, h) for i in range(len(items))]

    def menu_value(self, name):
        if name == 'PANTALLA COMPLETA':
            try:
                return 'SÍ' if pygame.display.is_fullscreen() else 'NO'
            except Exception:
                return 'NO'
        if name == 'MODO CRT':
            return 'SÍ' if self.crt_on else 'NO'
        if name == 'MODO INMORTAL':
            return 'SÍ' if self.god else 'NO'
        return None

    # ------------------------------------------------------------------ acciones
    def menu_go(self, page):
        self.tm = dict(page=page, sel=0)
        self.audio.play('blip', .4)

    def menu_activate(self):
        tm = self.tm
        name = self.menu_items()[tm['sel']]
        if name == 'NUEVO JUEGO':
            self.start_game()
        elif name == 'CARGAR PARTIDA':
            self.open_saves('load')
        elif name == 'OPCIONES':
            self.menu_go('opts')
        elif name == 'SALIR':
            pygame.quit()
            sys.exit()
        elif name == 'VOLVER':
            self.menu_go('main' if tm['page'] == 'opts' else 'opts')
        elif name == 'INSTRUCCIONES':
            self.menu_go('help')
        elif name == 'CHEATS':
            self.menu_go('cheats')
        else:
            self.menu_toggle(name)

    def menu_toggle(self, name):
        if name == 'PANTALLA COMPLETA':
            self.toggle_fullscreen()
        elif name == 'MODO CRT':
            self.crt_on = not self.crt_on
        elif name == 'MODO INMORTAL':
            self.set_god(not self.god)
        else:
            return
        self.audio.play('ping', .4)

    def menu_back(self):
        p = self.tm['page']
        if p == 'opts':
            self.menu_go('main')
        elif p in ('help', 'cheats'):
            self.menu_go('opts')

    # ------------------------------------------------------------------ eventos (devuelve True si los consume)
    def menu_event(self, e):
        if self.state != 'title' or not hasattr(self, 'tm'):
            return False
        tm = self.tm
        n = len(self.menu_items())
        if e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.menu_rects()):
                if r.collidepoint(e.pos) and tm['sel'] != i:
                    tm['sel'] = i
                    self.audio.play('blip', .15)
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            if e.button == 3:
                self.menu_back()
                return True
            for i, r in enumerate(self.menu_rects()):
                if r.collidepoint(e.pos):
                    tm['sel'] = i
                    self.menu_activate()
            return True
        if e.type != pygame.KEYDOWN or e.mod & pygame.KMOD_ALT:
            return False
        k = e.key
        if k in (pygame.K_UP, pygame.K_w):
            tm['sel'] = (tm['sel'] - 1) % n
            self.audio.play('blip', .25)
        elif k in (pygame.K_DOWN, pygame.K_s):
            tm['sel'] = (tm['sel'] + 1) % n
            self.audio.play('blip', .25)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.menu_activate()
        elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
            name = self.menu_items()[tm['sel']]
            if self.menu_value(name) is not None:
                self.menu_toggle(name)
        elif k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.menu_back()
        else:
            return False
        return True

    # ------------------------------------------------------------------ dibujo
    def menu_button(self, cv, r, label, sel, value=None):
        self.panel(cv, (r.x, r.y, r.w, r.h), 215 if sel else 150)
        if sel:
            pygame.draw.rect(cv, (255, 220, 110), r, 3, border_radius=8)
            pygame.draw.polygon(cv, (255, 220, 110), [(r.x - 26, r.centery - 10), (r.x - 26, r.centery + 10), (r.x - 8, r.centery)])
            pygame.draw.polygon(cv, (255, 220, 110), [(r.right + 26, r.centery - 10), (r.right + 26, r.centery + 10), (r.right + 8, r.centery)])
        col = (255, 244, 200) if sel else (190, 208, 236)
        if value is None:
            self.text(cv, label, self.f_l, col, r.centerx, r.y + (r.h - self.f_l.get_height()) // 2, 'c')
        else:
            y = r.y + (r.h - self.f_m.get_height()) // 2
            self.text(cv, label, self.f_m, col, r.x + 22, y)
            self.text(cv, value, self.f_m, (120, 255, 170) if value == 'SÍ' else (255, 150, 130), r.right - 22, y, 'r')

    def draw_title(self, cv):
        t = self.t
        tm = getattr(self, 'tm', None) or dict(page='main', sel=0)
        self.draw_ocean(cv, t * 30, t * 8, t)
        self.dim(cv, 45 if tm['page'] == 'main' else 90)
        if tm['page'] == 'main':
            x = (t * 70) % (W + 300) - 150
            self.blit_ship(cv, 'p_map', x, 700, 90)
            x2 = W + 150 - (t * 55) % (W + 300)
            self.blit_ship(cv, 'e_map', x2, 760, 270)
        big = tm['page'] == 'main'
        if big:
            for ln, y, col in (('RETRO', 90, (255, 220, 110)), ('LEGACY', 185, (255, 160, 70))):
                for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-3, -3), (3, 3), (-3, 3), (3, -3)):
                    self.text(cv, ln, self.f_ttl, (30, 10, 0), W // 2 + dx, y + dy, 'c', shadow=False)
                self.text(cv, ln, self.f_ttl, col, W // 2, y, 'c', shadow=False)
        else:
            title = {'opts': 'OPCIONES', 'help': 'INSTRUCCIONES', 'cheats': 'CHEATS'}[tm['page']]
            self.text(cv, title, self.f_ttl, (255, 220, 110), W // 2, 50, 'c')
        rects = self.menu_rects()
        items = self.menu_items()
        if tm['page'] == 'help':
            self.panel(cv, (W // 2 - 500, 170, 1000, 500), 190)
            y = 186
            for head, txt in HELP_LINES:
                self.text(cv, head, self.f_s, (255, 200, 110), W // 2 - 480, y)
                self.text(cv, txt, self.f_s, (220, 232, 255), W // 2 - 480, y + 20)
                y += 43
        elif tm['page'] == 'cheats':
            self.panel(cv, (W // 2 - 400, 150, 800, 410), 190)
            self.text(cv, 'En el mapa, durante una partida:', self.f_s, (255, 200, 110), W // 2 - 380, 160)
            for i, (k, d) in enumerate(CHEAT_LINES):
                col, row = divmod(i, 6)
                x = W // 2 - 380 + col * 390
                y = 196 + row * 52
                self.text(cv, k, self.f_m, (255, 230, 130), x, y)
                self.text(cv, d, self.f_s, (220, 232, 255), x + 80, y + 4)
            self.text(cv, 'Modo inmortal: no perdés casco ni vidas. Se guarda entre partidas.', self.f_s, (160, 190, 220), W // 2, 524, 'c')
        for i, (r, name) in enumerate(zip(rects, items)):
            self.menu_button(cv, r, name, i == tm['sel'], self.menu_value(name))
        if tm['page'] == 'main':
            self.text(cv, 'Récord: %d' % self.hiscore, self.f_m, (255, 230, 120), W // 2, H - 52, 'c')
            self.text(cv, 'Flechas o mouse | ENTER elegir', self.f_s, (150, 180, 215), W // 2, H - 24, 'c')
        else:
            self.text(cv, 'ESC o clic derecho: volver', self.f_s, (150, 180, 215), W // 2, H - 24, 'c')
