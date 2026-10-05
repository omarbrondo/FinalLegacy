"""Mando (Xbox 360 / One y compatibles) y pantalla completa.

El mando se traduce a teclado y mouse: palanca izquierda y cruceta = WASD/flechas, palanca derecha = mira,
RT/A = disparo (clic izquierdo), LT/B/RB = granada, bomba o acción secundaria (clic derecho).
"""
import math
import pygame
from .common import H, W, clamp

try:
    from pygame._sdl2 import controller as sdl_ctl
except Exception:                                   # pygame sin soporte de mandos
    sdl_ctl = None

DEAD = 0.22
PLAY_STATES = ('saves', 'map', 'defense', 'combat', 'ground', 'aerial', 'hack', 'radio', 'tank', 'port')


class _Keys:
    """Envuelve pygame.key.get_pressed() sumando las teclas virtuales del mando."""
    def __init__(self, real, virt):
        self.real, self.virt = real, virt

    def __getitem__(self, k):
        return self.real[k] or (k in self.virt)


class GamepadMixin:
    def pad_init(self):
        self.pad = None
        self.pad_virt = set()
        self.pad_btn = (False, False)
        self.pad_prev = {}
        self.pad_scan = 0.0
        self.pad_name = ''
        if sdl_ctl is None:
            return
        try:
            sdl_ctl.init()
        except Exception:
            return
        real_keys, real_mouse = pygame.key.get_pressed, pygame.mouse.get_pressed
        pygame.key.get_pressed = lambda: _Keys(real_keys(), self.pad_virt)

        def mouse_pressed(*a, **k):
            r = list(real_mouse(*a, **k))
            r[0] = r[0] or self.pad_btn[0]
            r[2] = r[2] or self.pad_btn[1]
            return tuple(r)
        pygame.mouse.get_pressed = mouse_pressed
        self.pad_scan_now()

    def pad_scan_now(self):
        try:
            if self.pad is not None and self.pad.attached():
                return
            self.pad = None
            for i in range(sdl_ctl.get_count()):
                if sdl_ctl.is_controller(i):
                    self.pad = sdl_ctl.Controller(i)
                    self.pad_name = self.pad.name
                    self.toast('Mando conectado: %s' % self.pad_name[:28], (120, 255, 190))
                    break
        except Exception:
            self.pad = None

    @staticmethod
    def _stick(x, y):
        m = math.hypot(x, y)
        if m < DEAD:
            return 0.0, 0.0
        k = min(1.0, (m - DEAD) / (1 - DEAD)) / m
        return x * k, y * k

    def pad_poll(self, dt):
        """Llamar una vez por cuadro: genera eventos de teclado/mouse a partir del mando."""
        if sdl_ctl is None:
            return
        self.pad_scan += dt
        if self.pad_scan > 1.0:
            self.pad_scan = 0.0
            self.pad_scan_now()
        pad = self.pad
        if pad is None:
            self.pad_virt.clear()
            self.pad_btn = (False, False)
            return
        C = sdl_ctl
        ax = lambda a: pad.get_axis(a) / 32767.0
        bt = lambda b: bool(pad.get_button(b))
        lx, ly = self._stick(ax(C.CONTROLLER_AXIS_LEFTX), ax(C.CONTROLLER_AXIS_LEFTY))
        rx, ry = self._stick(ax(C.CONTROLLER_AXIS_RIGHTX), ax(C.CONTROLLER_AXIS_RIGHTY))
        lt, rt = ax(C.CONTROLLER_AXIS_TRIGGERLEFT) > 0.4, ax(C.CONTROLLER_AXIS_TRIGGERRIGHT) > 0.4
        up, dn = bt(C.CONTROLLER_BUTTON_DPAD_UP), bt(C.CONTROLLER_BUTTON_DPAD_DOWN)
        lf, rg = bt(C.CONTROLLER_BUTTON_DPAD_LEFT), bt(C.CONTROLLER_BUTTON_DPAD_RIGHT)
        cur = {'A': bt(C.CONTROLLER_BUTTON_A), 'B': bt(C.CONTROLLER_BUTTON_B), 'X': bt(C.CONTROLLER_BUTTON_X),
               'Y': bt(C.CONTROLLER_BUTTON_Y), 'LB': bt(C.CONTROLLER_BUTTON_LEFTSHOULDER),
               'RB': bt(C.CONTROLLER_BUTTON_RIGHTSHOULDER), 'START': bt(C.CONTROLLER_BUTTON_START),
               'BACK': bt(C.CONTROLLER_BUTTON_BACK), 'LT': lt, 'RT': rt, 'UP': up, 'DN': dn, 'LF': lf, 'RG': rg}
        pressed = {k for k, v in cur.items() if v and not self.pad_prev.get(k)}
        self.pad_prev = cur
        st = self.state
        menu = st in ('title', 'gameover', 'saves')
        # teclas mantenidas: movimiento y acción de puerto/tierra
        v = set()
        if ly < -0.3 or up:
            v |= {pygame.K_w, pygame.K_UP}
        if ly > 0.3 or dn:
            v |= {pygame.K_s, pygame.K_DOWN}
        if lx < -0.3 or lf:
            v |= {pygame.K_a, pygame.K_LEFT}
        if lx > 0.3 or rg:
            v |= {pygame.K_d, pygame.K_RIGHT}
        if cur['X']:
            v.add(pygame.K_r)
        if st == 'radio':                            # fase de la señal en el minijuego de comunicaciones
            if cur['LB']:
                v.add(pygame.K_q)
            if cur['RB']:
                v.add(pygame.K_e)
        self.pad_virt = v
        self.pad_btn = (cur['A'] or rt, cur['B'] or lt or cur['RB'])
        # mira con la palanca derecha
        if rx or ry:
            self.mouse_moved = True
            self.aim = [clamp(self.aim[0] + rx * 640 * dt, 0, W), clamp(self.aim[1] + ry * 640 * dt, 0, H)]

        def key(k):
            self.handle(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode='', scancode=0))

        def click(b):
            self.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=b, pos=(int(self.aim[0]), int(self.aim[1]))))
        if self.paused:
            if 'START' in pressed or 'B' in pressed:
                key(pygame.K_p)
            for b, k in (('X', pygame.K_s), ('Y', pygame.K_c), ('BACK', pygame.K_i)):          # pausa: guardar, cargar, inmortal
                if b in pressed:
                    key(k)
            return
        if 'START' in pressed:
            key(pygame.K_RETURN if menu else pygame.K_p)
            return
        sup = st == 'ground' and bool(self.g.get('lz'))             # desembarco: RB llama al apoyo naval, Back cambia el tipo
        if 'BACK' in pressed:
            key(pygame.K_e if st == 'combat' else (pygame.K_TAB if sup else pygame.K_m))       # en combate naval, Back = huir
        if menu:
            if st == 'saves':
                for b, k in (('UP', pygame.K_UP), ('DN', pygame.K_DOWN), ('B', pygame.K_ESCAPE)):
                    if b in pressed:
                        key(k)
            elif st == 'title':
                for b, k in (('Y', pygame.K_c), ('X', pygame.K_i)):                          # título: cargar partida / inmortal
                    if b in pressed:
                        key(k)
            if 'A' in pressed:
                key(pygame.K_RETURN)
            return
        if st == 'upgrade':
            for b, k in (('X', pygame.K_1), ('A', pygame.K_2), ('B', pygame.K_3)):
                if b in pressed:
                    key(k)
            return
        if st == 'helisel':
            for b, k in (('X', pygame.K_1), ('A', pygame.K_2), ('Y', pygame.K_3), ('RB', pygame.K_4), ('B', pygame.K_ESCAPE)):
                if b in pressed:
                    key(k)
            return
        if st == 'radio':
            for b, k in (('A', pygame.K_SPACE), ('B', pygame.K_TAB)):
                if b in pressed:
                    key(k)
            return
        if st == 'hack':
            for b, k in (('UP', pygame.K_UP), ('DN', pygame.K_DOWN), ('LF', pygame.K_LEFT), ('RG', pygame.K_RIGHT),
                         ('A', pygame.K_SPACE), ('X', pygame.K_z), ('B', pygame.K_TAB)):
                if b in pressed:
                    key(k)
            return
        if 'A' in pressed or 'RT' in pressed:
            click(1)
        if sup and 'RB' in pressed:
            key(pygame.K_t)
        if 'B' in pressed or 'LT' in pressed or ('RB' in pressed and not sup):
            click(3)
            if st in ('aerial', 'ground'):
                key(pygame.K_b if st == 'aerial' else pygame.K_g)
        if st == 'map':
            for b, k in (('LB', pygame.K_l), ('RB', pygame.K_h), ('Y', pygame.K_t), ('B', pygame.K_b), ('LT', pygame.K_c), ('A', pygame.K_f)):
                if b in pressed:
                    key(k)
        else:
            if 'Y' in pressed:
                key(pygame.K_g if st == 'combat' else pygame.K_e)
            if 'X' in pressed:
                key(pygame.K_r)
            if 'LB' in pressed:
                key(pygame.K_t if (st == 'port' or (st == 'ground' and not self.g['stealth'])) else pygame.K_q)
