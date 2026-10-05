"""Asalto al puerto: combos, armas pesadas, suministros en paracaídas, apoyo aéreo y el tanque SV-001."""
import math
import pygame
import random
from .common import H, PLAYER_HP, W, clamp, draw_circ, glow

COMBO_WIN = 2.6
VEH_HP = 70.0
SV_POS = (1950, 3800)                          # lugares donde espera un SV-001
SV_SCALE = 0.64
SV_GROUND = int(176 * SV_SCALE)                # alto del suelo dentro del sprite
WEAPONS = {'shot': ('ESCOPETA', 14, (255, 200, 100)), 'rkt': ('LANZACOHETES', 9, (255, 140, 100))}
MILESTONES = {3: ('¡TRIPLE!', 0), 5: ('¡PENTA!  +300', 300), 8: ('¡MASACRE!  +600', 600), 12: ('¡IMPARABLE!  +1000', 1000)}
CRUSHABLE = ('rifle', 'knife', 'gren', 'flame', 'shield')


class PortEpicMixin:
    # ------------------------------------------------------------------ armado
    def pt_epic_setup(self):
        pt = self.pt
        p = pt['p']
        p.update(veh=None, wpn=None, wammo=0)
        pt.update(combo=dict(n=0, t=0.0, best=0, show=0.0, text='', max_n=0), chutes=[], drops=[], drop_t=random.uniform(18, 26),
                  air=dict(meter=0.0, bomber=None, bombs=[], ready_said=False), rockets=[],
                  svs=[dict(x=float(x), hp=VEH_HP, state='parked') for x in SV_POS])
        for it in pt['items']:
            if it['x'] == 2750:
                it['kind'] = 'rkt'
        for xi, kind in ((1500, 'shot'), (3500, 'hmg')):
            pt['items'].append(dict(x=float(xi), y=float(self.PT_GR - 30), kind=kind, t=0.0))
        for pw in pt['pows']:
            pw['item'] = {'hmg': 'shot', 'gren': 'rkt'}.get(pw['item'], pw['item'])

    # ------------------------------------------------------------------ cuchillero
    def pt_knife_move(self, e, dt, ad, alive):
        """Corre, mide la distancia, embiste, apuñala una vez y retrocede: nunca se queda pegado al jugador."""
        p = self.pt['p']
        near = alive and abs(p['y'] - e['y']) < 60
        sp = 215.0
        if e['atk'] == 0:
            if ad < 38:
                sp = 0.0
            if near and ad < 95 and e['cd'] <= 0:
                e['atk'], e['st'] = 1, 0.2
        elif e['atk'] == 1:                                 # prepara el golpe
            sp = 0.0
            e['st'] -= dt
            if e['st'] <= 0:
                e['atk'], e['st'], e['slash'], e['kdone'] = 2, 0.16, 0.3, False
        elif e['atk'] == 2:                                 # embestida
            sp = 430.0 if ad > 30 else 0.0
            e['st'] -= dt
            if not e['kdone'] and near and ad < 56:
                e['kdone'] = True
                self.pt_hurt(14)
            if e['st'] <= 0:
                e['atk'], e['st'], e['cd'] = 3, 0.5, 0.8
        else:                                               # retrocede
            sp = -160.0
            e['st'] -= dt
            if e['st'] <= 0:
                e['atk'] = 0
        return sp

    # ------------------------------------------------------------------ combos
    def pt_combo_kill(self, e):
        pt = self.pt
        cb = pt['combo']
        cb['n'] = cb['n'] + 1 if cb['t'] > 0 else 1
        cb['t'] = COMBO_WIN
        cb['max_n'] = max(cb['max_n'], cb['n'])
        n = cb['n']
        if n >= 2:
            self.add_score(min(200, 10 * n))
        ms = MILESTONES.get(n) or ((' ¡LEYENDA!  +1500', 1500) if n > 12 and n % 5 == 0 else None)
        if ms:
            cb['text'], cb['show'] = ms[0].strip(), 1.7
            if ms[1]:
                self.add_score(ms[1])
            self.audio.play('win', .4)
            if n >= 8:
                pt['freeze'] = max(pt['freeze'], 0.22)
        gain = {'tank': 30, 'turret': 20, 'sniper': 8}.get(e['kind'], 5)
        self.pt_air_charge(gain)

    def pt_air_charge(self, amount):
        air = self.pt['air']
        was = air['meter'] >= 100
        air['meter'] = min(100.0, air['meter'] + amount)
        if air['meter'] >= 100 and not was:
            self.toast('¡APOYO AÉREO LISTO!  Presioná E (Y en el joystick)', (140, 230, 255))
            self.audio.play('ping', .6)

    # ------------------------------------------------------------------ armas
    def pt_weapon_pick(self, kind):
        p = self.pt['p']
        name, ammo, col = WEAPONS[kind]
        p['wpn'], p['wammo'], p['hmg'] = kind, ammo, 0.0
        self.pop('¡%s!' % name, p['x'] - self.pt['cam'], p['y'] - 90, col)

    def pt_veh_muzzle(self):
        p = self.pt['p']
        f = 1 if p['face'] > 0 else -1
        ox, oy = p['x'] + f * 224 * SV_SCALE, p['y'] - 111 * SV_SCALE
        tx, ty = self.aim[0] + self.pt['cam'], self.aim[1]
        dx = max(10.0, (tx - ox) * f)
        th = clamp(math.atan2(ty - oy, dx), -math.radians(55), math.radians(55))
        return ox, oy, f * math.cos(th), math.sin(th)

    def pt_shoot_special(self):
        """Disparo del SV-001, la escopeta o el lanzacohetes (el fusil normal está en pt_shoot)."""
        pt = self.pt
        p = pt['p']
        if p['cd'] > 0 or p['dead']:
            return
        if p['veh']:
            ox, oy, dx, dy = self.pt_veh_muzzle()
            p['cd'] = 0.075 * self.up_reload()
            p['flash'] = 0.05
            a = math.atan2(dy, dx) + math.radians(random.uniform(-2.0, 2.0))
            pt['bul'].append(dict(x=ox, y=oy, vx=math.cos(a) * 1000, vy=math.sin(a) * 1000, dmg=1.5 * self.up_dmg(), life=0.9))
            self.audio.play('mg', .3)
            return
        pv = p.get('pv') or (p['x'], p['y'] - (50 if p['crouch'] else 67))
        mx, my, dx, dy = self.pt_muzzle('player', pv, p['face'], self.aim[0] + pt['cam'], self.aim[1])
        a0 = math.atan2(dy, dx)
        if p['wpn'] == 'shot':
            p['cd'] = 0.52 * self.up_reload()
            for _ in range(7):
                a = a0 + math.radians(random.uniform(-13, 13))
                sp = random.uniform(820, 960)
                pt['bul'].append(dict(x=mx, y=my, vx=math.cos(a) * sp, vy=math.sin(a) * sp, dmg=1.0 * self.up_dmg(), life=0.34))
            self.audio.play('boom_s', .35)
            self.shake = max(self.shake, 3)
            self.fx.add('glow', mx, my, life=.12, r0=10, r1=34, col=(255, 210, 120))
        else:
            p['cd'] = 0.6 * self.up_reload()
            pt['rockets'].append(dict(x=mx, y=my, vx=math.cos(a0) * 640, vy=math.sin(a0) * 640, t=0.0, life=1.6, R=100.0, dmg=7.0, pd=10, grav=0.0, kind='rkt'))
            self.audio.play('launch', .6)
            self.shake = max(self.shake, 3)
        p['flash'] = 0.06
        p['wammo'] -= 1
        if p['wammo'] <= 0:
            p['wpn'] = None
            self.pop('SIN MUNICIÓN', p['x'] - pt['cam'], p['y'] - 90, (255, 150, 120))

    def pt_veh_cannon(self):
        pt = self.pt
        p = pt['p']
        v = p['veh']
        if p['dead'] or v['cd'] > 0 or pt['phase'] != 'play':
            return
        v['cd'] = 0.85
        v['recoil'] = 14.0
        ox, oy, dx, dy = self.pt_veh_muzzle()
        pt['rockets'].append(dict(x=ox, y=oy, vx=dx * 720, vy=dy * 720, t=0.0, life=1.4, R=96.0, dmg=9.0, pd=6, grav=0.0, kind='shell'))
        self.audio.play('cannon', .5)
        self.shake = max(self.shake, 6)
        self.fx.add('glow', ox, oy, life=.15, r0=14, r1=44, col=(255, 210, 120))

    def pt_rockets_update(self, dt):
        pt = self.pt
        GR = self.PT_GR
        for r in pt['rockets'][:]:
            r['t'] += dt
            r['x'] += r['vx'] * dt
            r['y'] += r['vy'] * dt
            self.fx.add('smoke', r['x'] - r['vx'] * 0.02, r['y'] - r['vy'] * 0.02, 0, 0, 0.5, 3, 11, (200, 196, 190))
            boom = r['t'] > r['life'] or r['y'] >= GR - 4 or r['x'] < pt['cam'] - 80 or r['x'] > pt['cam'] + W + 80
            if not boom:
                for e in pt['enemies']:
                    x0, y0, w, h = self.pt_box(e)
                    if x0 <= r['x'] <= x0 + w and y0 <= r['y'] <= y0 + h:
                        boom = True
                        break
            if not boom:
                boom = any(br['fuse'] < 0 and abs(r['x'] - br['x']) < 17 and br['y'] - 44 <= r['y'] <= br['y'] for br in pt['barrels'])
            if not boom:
                boom = any(pl['x'] < r['x'] < pl['x'] + pl['w'] and pl['top'] < r['y'] < pl['top'] + pl['h'] for pl in pt['plats'])
            if boom:
                pt['rockets'].remove(r)
                self.pt_blast(r['x'], min(r['y'], GR - 4), r['R'] * self.up_blast(), r['dmg'] * self.up_dmg(), r['pd'], 'p')

    # ------------------------------------------------------------------ tanque SV-001
    def pt_try_mount(self):
        pt = self.pt
        p = pt['p']
        if p['dead'] or p['veh'] or not p['ground'] or pt['phase'] != 'play':
            return False
        for sv in pt['svs']:
            if sv['state'] == 'parked' and abs(p['x'] - sv['x']) < 95 and abs(p['y'] - self.PT_GR) < 20:
                sv['state'] = 'ridden'
                p['veh'] = dict(hp=sv['hp'], max=VEH_HP, cd=0.0, recoil=0.0, hit=0.0, ph=0.0)
                p['x'] = sv['x']
                p['wpn'] = None
                self.audio.play('win', .5)
                self.shake = max(self.shake, 6)
                self.banner('¡SV-001 A BORDO!', 'Clic: ametralladora | clic der./G: cañón | aplastá a la infantería', (140, 230, 255), 3.4)
                return True
        return False

    def pt_veh_hit(self, dmg):
        pt = self.pt
        p = pt['p']
        v = p['veh']
        v['hp'] -= dmg * 0.7
        v['hit'] = 0.15
        p['inv'] = 0.3
        pt['hurt'] = max(pt['hurt'], 0.2)
        self.shake = max(self.shake, 4 + dmg * 0.2)
        self.audio.play('hit', .5)
        self.fx.add('spark', p['x'] + random.uniform(-50, 50), p['y'] - random.uniform(20, 90), random.uniform(-90, 90), random.uniform(-140, 0), 0.3,
                    col=(255, 220, 140), drag=2, grav=400)
        if v['hp'] <= 0:
            self.pt_veh_explode()

    def pt_veh_explode(self):
        pt = self.pt
        p = pt['p']
        x, y = p['x'], p['y']
        p['veh'] = None
        pt['wrecks'].append(dict(kind='sv', x=x, y=y))
        self.pt_blast(x, y - 40, 125, 9, 1, 'b')
        for _ in range(4):
            self.fx.explode(x + random.uniform(-60, 60), y - random.uniform(10, 80), 1.3, True)
        self.shake = 18
        p['vy'], p['ground'], p['inv'] = -560.0, False, 1.6
        self.banner('¡SV-001 DESTRUIDO!', 'Saltaste a tiempo', (255, 140, 100), 2.4)

    def pt_veh_image(self, face, fi, hit):
        cache = self.__dict__.setdefault('_sv_cache', {})
        key = (face > 0, fi % 8, hit)
        img = cache.get(key)
        if img is None:
            base = self.pt_tank_img(dict(x=(fi % 8) * 14 / 8 + 0.01, hit=0.0, recoil=0))
            base.fill((10, 34, 56, 0), special_flags=pygame.BLEND_RGB_ADD)
            img = pygame.transform.smoothscale(base, (int(base.get_width() * SV_SCALE), int(base.get_height() * SV_SCALE)))
            if face > 0:
                img = pygame.transform.flip(img, True, False)
            if hit:
                img = img.copy()
                img.fill((70, 70, 70, 0), special_flags=pygame.BLEND_RGB_ADD)
            cache[key] = img
        return img

    # ------------------------------------------------------------------ apoyo aéreo
    def pt_airstrike(self):
        pt = self.pt
        air = pt['air']
        if pt['phase'] != 'play' or pt['p']['dead']:
            return
        if air['bomber'] is not None:
            return
        if air['meter'] < 100:
            self.toast('Apoyo aéreo cargándose: %d%%' % int(air['meter']), (255, 200, 120))
            return
        air['meter'] = 0.0
        air['bomber'] = dict(x=pt['cam'] - 260, y=110.0, left=10, cd=0.0)
        self.audio.play('alarm', .5)
        self.audio.play('launch', .7)
        self.banner('¡APOYO AÉREO EN CAMINO!', 'Un bombardero cruza la pantalla', (140, 230, 255), 2.4)

    def pt_air_update(self, dt):
        pt = self.pt
        air = pt['air']
        b = air['bomber']
        GR = self.PT_GR
        if b is not None:
            b['x'] += 1000 * dt
            b['cd'] -= dt
            if b['left'] > 0 and b['cd'] <= 0 and pt['cam'] - 20 < b['x'] < pt['cam'] + W + 20:
                b['cd'] = 0.15
                b['left'] -= 1
                air['bombs'].append(dict(x=b['x'], y=b['y'] + 12, vx=360.0, vy=0.0))
                self.audio.play('blip', .4)
            if b['x'] > pt['cam'] + W + 300:
                air['bomber'] = None
        for bm in air['bombs'][:]:
            bm['vy'] += 900 * dt
            bm['x'] += bm['vx'] * dt
            bm['y'] += bm['vy'] * dt
            fl = self.pt_floor(bm['x'], bm['y'] - 8)
            if bm['y'] >= fl - 6 and bm['vy'] > 0:
                air['bombs'].remove(bm)
                self.pt_blast(bm['x'], min(fl, GR - 4), 105, 8, 8, 'p')

    def pt_draw_bomber(self, cv, cam):
        b = self.pt['air']['bomber']
        if b is None:
            return
        sx, sy = b['x'] - cam, b['y']
        draw_circ(cv, sx, self.PT_GR + 6, 50, (0, 0, 0), 60)
        pygame.draw.polygon(cv, (88, 98, 112), [(sx - 70, sy - 4), (sx + 66, sy - 8), (sx + 84, sy + 2), (sx + 66, sy + 12), (sx - 70, sy + 10)])
        pygame.draw.polygon(cv, (126, 138, 154), [(sx - 70, sy - 4), (sx + 66, sy - 8), (sx + 84, sy + 2), (sx - 70, sy + 2)])
        pygame.draw.polygon(cv, (70, 80, 94), [(sx - 6, sy + 6), (sx - 34, sy + 38), (sx - 14, sy + 38), (sx + 22, sy + 6)])
        pygame.draw.polygon(cv, (70, 80, 94), [(sx - 70, sy - 4), (sx - 88, sy - 34), (sx - 70, sy - 34), (sx - 50, sy - 4)])
        pygame.draw.ellipse(cv, (150, 210, 235), (sx + 40, sy - 8, 24, 10))
        pygame.draw.polygon(cv, (214, 70, 60), [(sx - 70, sy - 4), (sx - 88, sy - 34), (sx - 80, sy - 34), (sx - 62, sy - 4)])
        glow(cv, sx - 76, sy + 4, 26, (255, 180, 90), 0.8)

    # ------------------------------------------------------------------ bucle
    def pt_epic_update(self, dt, alive, keys):
        pt = self.pt
        p = pt['p']
        cb = pt['combo']
        if cb['t'] > 0:
            cb['t'] -= dt
            if cb['t'] <= 0:
                cb['n'] = 0
        cb['show'] = max(0.0, cb['show'] - dt)
        if alive and p['veh']:
            v = p['veh']
            v['cd'] = max(0.0, v['cd'] - dt)
            v['recoil'] = max(0.0, v['recoil'] - 70 * dt)
            v['hit'] = max(0.0, v['hit'] - dt)
            v['ph'] += abs(p['vx']) * dt / 12.7
            p['crouch'] = False
            if abs(p['vx']) > 1:
                for e in pt['enemies'][:]:
                    if e['kind'] in CRUSHABLE and not e['para'] and abs(e['x'] - p['x']) < 74 and abs(e['y'] - p['y']) < 26:
                        self.pop('¡APLASTADO!', e['x'] - pt['cam'], e['y'] - 90, (255, 220, 120))
                        self.pt_kill(e, False)
                if random.random() < dt * 14:
                    self.fx.add('smoke', p['x'] - p['face'] * 80, p['y'] - 5, random.uniform(-30, 30), random.uniform(-30, -8), 0.5, 4, 14, (170, 150, 130), drag=2)
        # suministros en paracaídas
        pt['drop_t'] -= dt
        if pt['drop_t'] <= 0 and pt['phase'] == 'play':
            pt['drop_t'] = random.uniform(30, 44)
            need_med = p['hp'] < PLAYER_HP * 0.5
            kind = 'med' if need_med and random.random() < 0.7 else random.choices(('med', 'gren', 'shot', 'rkt', 'hmg'), (3, 2, 3, 2, 2))[0]
            pt['drops'].append(dict(x=pt['cam'] + random.uniform(260, W - 220), y=-90.0, kind=kind, t=0.0))
            self.audio.play('ping', .6)
            self.toast('¡Suministros en paracaídas!', (140, 255, 190))
        for d in pt['drops'][:]:
            d['t'] += dt
            d['y'] += 115 * dt
            d['x'] += math.sin(d['t'] * 1.6) * 18 * dt
            fl = self.pt_floor(d['x'], d['y'] - 8)
            if d['y'] >= fl - 4:
                pt['drops'].remove(d)
                pt['items'].append(dict(x=d['x'], y=float(fl - 30), kind=d['kind'], t=0.0))
                for _ in range(6):
                    self.fx.add('smoke', d['x'] + random.uniform(-16, 16), fl - 3, random.uniform(-60, 60), random.uniform(-26, -6), 0.6, 4, 12, (190, 170, 150), drag=2)
        for c in pt['chutes'][:]:
            c['t'] += dt
            c['y'] += 70 * dt
            c['x'] += c['vx'] * dt
            if c['t'] > 2.6 or c['y'] > self.PT_GR + 20:
                pt['chutes'].remove(c)
        self.pt_rockets_update(dt)
        self.pt_air_update(dt)

    # ------------------------------------------------------------------ dibujo
    def pt_draw_chute(self, cv, sx, top, collapse=0.0, alpha=255):
        k = 1 - 0.75 * collapse
        w = 54 * k
        h = 70 * (1 - 0.5 * collapse)
        if alpha < 255:
            s = pygame.Surface((int(w * 2 + 8), int(h + 10)), pygame.SRCALPHA)
            pygame.draw.arc(s, (236, 236, 226, alpha), (4, 4, w * 2, h), 0, 3.14159, 30)
            cv.blit(s, (sx - w - 4, top - 4))
            return
        pygame.draw.arc(cv, (236, 236, 226), (sx - w, top, w * 2, h), 0, 3.14159, 40)
        pygame.draw.polygon(cv, (226, 90, 70), [(sx - w, top + h / 2), (sx - w / 3, top + 4), (sx - w / 9, top + 4), (sx - w * 0.4, top + h * 0.54)])
        pygame.draw.polygon(cv, (236, 236, 226), [(sx - w * 0.4, top + h * 0.54), (sx - w / 9, top + 4), (sx + w / 9, top + 4), (sx + w * 0.4, top + h * 0.54)])
        pygame.draw.polygon(cv, (226, 90, 70), [(sx + w * 0.4, top + h * 0.54), (sx + w / 9, top + 4), (sx + w / 3, top + 4), (sx + w, top + h / 2)])
        pygame.draw.arc(cv, (40, 36, 40), (sx - w, top, w * 2, h), 0, 3.14159, 3)

    def pt_epic_draw_back(self, cv, cam):
        pt = self.pt
        p = pt['p']
        t = self.t
        GR = self.PT_GR
        for sv in pt['svs']:
            if sv['state'] != 'parked':
                continue
            sx = sv['x'] - cam
            if not (-200 < sx < W + 200):
                continue
            img = self.pt_veh_image(1, 0, False)
            cv.blit(img, (sx - img.get_width() // 2, GR - SV_GROUND))
            if abs(p['x'] - sv['x']) < 260 and not p['veh']:
                pul = 0.5 + 0.5 * math.sin(t * 5)
                self.text(cv, 'SV-001', self.f_m, (140, 230, 255), sx, GR - 150 - 6 * pul, 'c')
                self.text(cv, 'SALTÁ PARA SUBIR', self.f_s, (255, 240, 170), sx, GR - 124, 'c')
                draw_circ(cv, sx, GR - 50, 100 + 6 * pul, (140, 230, 255), 50, 2)
        for d in pt['drops']:
            sx = d['x'] - cam
            if not (-100 < sx < W + 100):
                continue
            self.pt_draw_chute(cv, sx, d['y'] - 96)
            pygame.draw.line(cv, (40, 36, 40), (sx - 24, d['y'] - 54), (sx - 10, d['y'] - 20), 1)
            pygame.draw.line(cv, (40, 36, 40), (sx + 24, d['y'] - 54), (sx + 10, d['y'] - 20), 1)
            pygame.draw.rect(cv, (40, 40, 30), (sx - 16, d['y'] - 22, 32, 26), border_radius=3)
            pygame.draw.rect(cv, (214, 180, 70), (sx - 14, d['y'] - 20, 28, 22), border_radius=3)
            self.text(cv, {'med': '+', 'gren': 'G', 'shot': 'S', 'rkt': 'R', 'hmg': 'H'}[d['kind']], self.f_m, (60, 40, 10), sx, d['y'] - 22, 'c', shadow=False)
        for c in pt['chutes']:
            sx = c['x'] - cam
            self.pt_draw_chute(cv, sx, c['y'], min(1.0, c['t'] / 0.5), int(255 * clamp(1 - (c['t'] - 1.6) / 1.0, 0, 1)))

    def pt_epic_draw_front(self, cv, cam):
        pt = self.pt
        p = pt['p']
        for r in pt['rockets']:
            sx, sy = r['x'] - cam, r['y']
            ang = math.degrees(math.atan2(-r['vy'], r['vx']))
            glow(cv, sx, sy, 18, (255, 190, 100), 0.8)
            ex, ey = sx - r['vx'] * 0.03, sy - r['vy'] * 0.03
            pygame.draw.line(cv, (230, 230, 220), (sx, sy), (ex, ey), 5 if r['kind'] == 'rkt' else 7)
            pygame.draw.circle(cv, (255, 120, 80), (int(sx), int(sy)), 4 if r['kind'] == 'rkt' else 6)
            del ang
        for bm in pt['air']['bombs']:
            sx = bm['x'] - cam
            pygame.draw.ellipse(cv, (40, 44, 48), (sx - 6, bm['y'] - 12, 12, 24))
            pygame.draw.ellipse(cv, (200, 70, 60), (sx - 5, bm['y'] - 4, 10, 6))
        self.pt_draw_bomber(cv, cam)
        if p['veh'] and not p['dead']:
            v = p['veh']
            img = self.pt_veh_image(p['face'], int(v['ph']), v['hit'] > 0)
            if not (p['inv'] > 0 and int(self.t * 20) % 2 == 0):
                sx = p['x'] - cam
                f = 1 if p['face'] > 0 else -1
                cv.blit(img, (sx - img.get_width() // 2 - f * v['recoil'] * 0.4, p['y'] - SV_GROUND))
                if p['flash'] > 0:
                    ox, oy, dx, dy = self.pt_veh_muzzle()
                    self.pt_flash(cv, ox - cam, oy, math.degrees(math.atan2(-dy, abs(dx))) * (1 if f > 0 else -1), f > 0)

    def pt_epic_hud(self, cv):
        pt = self.pt
        p = pt['p']
        t = self.t
        cb = pt['combo']
        if cb['n'] >= 2:
            k = clamp(cb['t'] / COMBO_WIN, 0, 1)
            sz = self.f_l
            self.text(cv, 'COMBO x%d' % cb['n'], sz, (255, 220 - int(80 * (1 - k)), 90), 26, 80)
            pygame.draw.rect(cv, (8, 12, 24), (26, 112, 150, 7))
            pygame.draw.rect(cv, (255, 190, 80), (27, 113, int(148 * k), 5))
        if cb['show'] > 0:
            a = int(255 * clamp(cb['show'] * 2, 0, 1))
            y = 150 - int((1.7 - cb['show']) * 12)
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                self.text(cv, cb['text'], self.f_l, (40, 14, 6), W // 2 + dx, y + dy, 'c', shadow=False, alpha=a)
            self.text(cv, cb['text'], self.f_l, (255, 220, 100), W // 2, y, 'c', shadow=False, alpha=a)
        x, y = 352, H - 126
        self.panel(cv, (x, y, 300, 112), 190)
        air = pt['air']
        ready = air['meter'] >= 100 and air['bomber'] is None
        col = (140, 235, 255) if ready else (120, 170, 210)
        self.bar(cv, x + 12, y + 10, 276, 20, air['meter'] / 100.0, col, 'APOYO AÉREO [E] LISTO' if ready and int(t * 3) % 2 == 0 else 'APOYO AÉREO %d%%' % int(air['meter']))
        if p['veh']:
            v = p['veh']
            hp = clamp(v['hp'] / v['max'], 0, 1)
            self.bar(cv, x + 12, y + 38, 276, 20, hp, (110, 220, 255) if hp > 0.4 else (240, 90, 70), 'SV-001  %d' % max(0, v['hp']))
            self.text(cv, 'CAÑÓN' if v['cd'] <= 0 else 'CAÑÓN...', self.f_s, (255, 230, 150) if v['cd'] <= 0 else (150, 150, 150), x + 12, y + 64)
        elif p['wpn']:
            name, ammo, wcol = WEAPONS[p['wpn']]
            self.bar(cv, x + 12, y + 38, 276, 20, p['wammo'] / float(ammo), wcol, '%s  %d' % (name, p['wammo']))
        else:
            self.text(cv, 'Combos y rescates cargan el apoyo aéreo', self.f_s, (150, 170, 200), x + 12, y + 42)
        n_sv = sum(1 for sv in pt['svs'] if sv['state'] == 'parked')
        if n_sv and not p['veh']:
            self.text(cv, 'SV-001 disponibles: %d' % n_sv, self.f_s, (140, 230, 255), x + 12, y + 84)
