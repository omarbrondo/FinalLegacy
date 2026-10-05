"""Armas y habilidades del combate naval: descarga especial, torpedos, cortina de humo y control de daños."""
import math
import pygame
import random
from .common import H, W, bearing, clamp, dist, draw_circ, glow, vec


class NavalArmsMixin:
    def na_init(self):
        c = self.c
        c.update(charge=0.0, tcd=0.0, scd=0.0, torps=[], clouds=[], dc=2, fire_warn=False)

    # ------------------------------------------------------------ carga de la descarga
    def na_charge(self, n):
        self.c['charge'] = min(100.0, self.c['charge'] + n)
        if self.c['charge'] >= 100.0 and not self.c.get('ready_said'):
            self.c['ready_said'] = True
            self.call_out('¡DESCARGA LISTA! (Q)', (130, 255, 190), 'ready', 8)
            self.audio.play('pickup', .8)

    # ------------------------------------------------------------ Q: descarga especial (abanico de 5 misiles)
    def na_special(self):
        c = self.c
        p = c['p']
        if self.state != 'combat' or p['sink'] is not None or c['e']['sink'] is not None:
            return
        if c['charge'] < 100.0:
            self.toast('Descarga al %d%%: acertá disparos para cargarla' % c['charge'], (255, 220, 130))
            return
        if self.ammo < 3:
            self.audio.play('empty')
            self.toast('Hace falta munición (3) para la descarga', (255, 90, 80))
            return
        self.ammo -= 3
        c['charge'], c['ready_said'] = 0.0, False
        tx, ty = self.combat_aim()
        base = bearing(tx - p['x'], ty - p['y'])
        for d in (-12, -6, 0, 6, 12):
            self.launch_missile(p, base + d, 430, 'p')
        self.audio.play('boom_s', .7)
        self.audio.play('launch', .9)
        c['flashes'].append([p['x'], p['y'], 190, (255, 220, 160), 1.0])
        self.shake = max(self.shake, 9)
        self.call_out('¡DESCARGA!', (255, 220, 120), 'salvo_p', 1)

    # ------------------------------------------------------------ R: torpedo (el único que alcanza a un submarino sumergido)
    def na_torpedo(self):
        c = self.c
        p = c['p']
        if self.state != 'combat' or p['sink'] is not None or c['e']['sink'] is not None:
            return
        if c['nest']:
            self.toast('Los torpedos no sirven contra baterías en tierra', (255, 200, 120))
            return
        if c['tcd'] > 0:
            self.toast('Torpedo cargando: %d s' % math.ceil(c['tcd']), (255, 200, 120))
            return
        if self.ammo < 2:
            self.audio.play('empty')
            self.toast('Hace falta munición (2) para el torpedo', (255, 90, 80))
            return
        self.ammo -= 2
        c['tcd'] = 9.0
        tx, ty = self.combat_aim()
        ang = bearing(tx - p['x'], ty - p['y'])
        vx, vy = vec(ang, 175)
        ox, oy = vec(ang, 36)
        c['torps'].append(dict(x=p['x'] + ox, y=p['y'] + oy, vx=vx, vy=vy, ang=ang, life=7.0, trail=[]))
        self.audio.play('launch', .6)
        self.audio.play('splash', .6)
        self.fx.splash(p['x'] + ox, p['y'] + oy, 0.9)

    # ------------------------------------------------------------ F / clic derecho: cortina de humo
    def na_smoke(self):
        c = self.c
        p = c['p']
        if self.state != 'combat' or p['sink'] is not None:
            return
        if c['scd'] > 0:
            self.toast('Cortina de humo: %d s' % math.ceil(c['scd']), (255, 200, 120))
            return
        c['scd'] = 16.0
        for k in range(5):
            bx, by = vec(p['h'] + 180, 30 + k * 42)
            c['clouds'].append(dict(x=p['x'] + bx, y=p['y'] + by, t=0.0, life=9.0, r=96))
        self.audio.play('hit', .4)
        self.call_out('CORTINA DE HUMO', (200, 210, 225), 'smoke', 3)

    def na_smoked(self):
        """¿Estás dentro de la cortina de humo? Los enemigos fallan mucho más."""
        p = self.c['p']
        return any(cl['t'] < cl['life'] and dist(cl['x'], cl['y'], p['x'], p['y']) < cl['r'] for cl in self.c['clouds'])

    # ------------------------------------------------------------ G: control de daños
    def na_damage_control(self):
        c = self.c
        p = c['p']
        if self.state != 'combat' or p['sink'] is not None:
            return
        fires = [m for m in c['marks']['p'] if m['fire']]
        if c['dc'] <= 0:
            self.toast('Sin equipos de control de daños', (255, 150, 110))
            return
        if not fires and self.hull > 90:
            self.toast('No hay incendios a bordo', (255, 220, 130))
            return
        c['dc'] -= 1
        for m in c['marks']['p']:
            m['fire'] = False
        self.hull = min(self.hull_max, self.hull + 7)
        self.audio.play('pickup', .8)
        self.call_out('CONTROL DE DAÑOS', (130, 220, 255), 'dc', 2)
        for m in c['marks']['p'][:6]:
            ax, ay = vec(p['h'], m['f'])
            bx, by = vec(p['h'] + 90, m['l'])
            self.fx.add('foam', p['x'] + ax + bx, p['y'] + ay + by, 0, -10, 0.9, 6, 22, (235, 245, 255))

    # ------------------------------------------------------------ actualización
    def na_update(self, dt):
        c = self.c
        p, e = c['p'], c['e']
        c['tcd'] = max(0.0, c['tcd'] - dt)
        c['scd'] = max(0.0, c['scd'] - dt)
        # incendios a bordo: queman el casco hasta que los apagues
        fires = sum(1 for m in c['marks']['p'] if m['fire'])
        if fires and p['sink'] is None:
            self.hull -= 0.22 * min(3, fires) * dt
            if not c['fire_warn']:
                c['fire_warn'] = True
                self.toast('¡Incendio a bordo! G: control de daños (%d)' % c['dc'], (255, 160, 110))
        # humo
        for cl in c['clouds'][:]:
            cl['t'] += dt
            if cl['t'] > cl['life']:
                c['clouds'].remove(cl)
                continue
            if random.random() < dt * 14 and cl['t'] < cl['life'] - 2:
                self.fx.add('smoke', cl['x'] + random.uniform(-50, 50), cl['y'] + random.uniform(-50, 50), random.uniform(-6, 6),
                            random.uniform(-6, 6), random.uniform(3.0, 4.6), 28, 62, (206, 210, 216))
        # torpedos
        for tp in c['torps'][:]:
            tp['x'] += tp['vx'] * dt
            tp['y'] += tp['vy'] * dt
            tp['life'] -= dt
            tp['trail'] = (tp['trail'] + [(tp['x'], tp['y'])])[-24:]
            if random.random() < dt * 40:
                self.fx.add('foam', tp['x'], tp['y'], 0, 0, 1.0, 3, 9, (235, 248, 255))
            if e['sink'] is None:
                hit, full = self.ship_hit(e, tp['x'], tp['y'], c['is_boss'])
                if hit:
                    c['torps'].remove(tp)
                    dmg = (8 if full else 6) * self.up_dmg()
                    e['hp'] -= dmg
                    self.pop('TORPEDO -%d' % round(dmg), tp['x'], tp['y'] - 22, (130, 230, 255))
                    self.nv_mark('e', e, tp['x'], tp['y'], dmg)
                    ratio = clamp(e['hp'] / e['max'], 0.0, 1.0)
                    self.nv_mark_fires('e', ratio)
                    self.fx.explode(tp['x'], tp['y'], 1.6, True)
                    self.fx.add('ring', tp['x'], tp['y'], life=0.6, r0=8, r1=90, col=(200, 235, 255))
                    c['flashes'].append([tp['x'], tp['y'], 140, (160, 220, 255), 1.0])
                    self.audio.play('boom_l', .6)
                    self.shake = max(self.shake, 12)
                    c['hs'] = max(c['hs'], 0.06)
                    self.na_charge(25)
                    self.call_out('¡TORPEDO!', (130, 230, 255), 'torp', 2)
                    continue
            if tp['life'] <= 0 or not (-40 < tp['x'] < W + 40 and -40 < tp['y'] < H + 40):
                c['torps'].remove(tp)

    # ------------------------------------------------------------ dibujo
    def na_draw(self, cv):
        c = self.c
        for cl in c['clouds']:
            k = 1.0 if cl['t'] > 1.0 else cl['t']
            fade = clamp((cl['life'] - cl['t']) / 2.0, 0.0, 1.0)
            draw_circ(cv, cl['x'], cl['y'], cl['r'] * (0.8 + 0.2 * k), (190, 196, 204), 70 * fade * k)
        for tp in c['torps']:
            pts = tp['trail']
            for i in range(1, len(pts)):
                pygame.draw.line(cv, (200 + i, 230 + i // 2, 250), pts[i - 1], pts[i], max(1, i // 6))
            ux, uy = vec(tp['ang'], 1)
            pygame.draw.line(cv, (40, 46, 56), (tp['x'] - ux * 15, tp['y'] - uy * 15), (tp['x'] + ux * 15, tp['y'] + uy * 15), 7)
            pygame.draw.line(cv, (160, 170, 184), (tp['x'] - ux * 14, tp['y'] - uy * 14), (tp['x'] + ux * 14, tp['y'] + uy * 14), 4)
            pygame.draw.circle(cv, (230, 70, 56), (int(tp['x'] + ux * 15), int(tp['y'] + uy * 15)), 4)
            glow(cv, tp['x'] - ux * 16, tp['y'] - uy * 16, 12, (170, 230, 255), 0.7)

    def na_hud(self, cv):
        c = self.c
        x0, y0 = W - 262, H - 189
        self.panel(cv, (x0 - 8, y0 - 8, 256, 181), 165)
        rows = [('Q DESCARGA', c['charge'] / 100.0, (130, 255, 190) if c['charge'] >= 100 else (255, 200, 90), '%d%%' % c['charge']),
                ('R TORPEDO', 1 - c['tcd'] / 9.0, (130, 220, 255) if c['tcd'] <= 0 else (110, 130, 160), 'LISTO' if c['tcd'] <= 0 else '%ds' % math.ceil(c['tcd'])),
                ('F HUMO', 1 - c['scd'] / 16.0, (210, 214, 222) if c['scd'] <= 0 else (110, 114, 124), 'LISTO' if c['scd'] <= 0 else '%ds' % math.ceil(c['scd'])),
                ('G DAÑOS', c['dc'] / 2.0, (130, 220, 255) if c['dc'] else (110, 114, 124), 'x%d' % c['dc'])]
        ap = c.get('aplane')
        if ap is not None:
            rows.append(('APOYO AÉREO', 1.0, (130, 255, 190) if ap['dead'] is None else (255, 120, 100), 'EN ACCIÓN' if ap['dead'] is None else 'DERRIBADO'))
        else:
            rows.append(('APOYO AÉREO', 1 - c['air_cd'] / (35.0 if c['air_cd'] < 35 else 45.0), (130, 255, 190) if c['air_cd'] < 5 else (255, 200, 90),
                         '%ds' % math.ceil(max(0, c['air_cd']))))
        for i, (lab, fr, col, txt) in enumerate(rows):
            y = y0 + i * 33
            self.text(cv, lab, self.f_s, (200, 220, 245), x0, y)
            self.bar(cv, x0, y + 17, 236, 11, fr, col, '')
            self.text(cv, txt, self.f_s, col, x0 + 236, y, 'r')
