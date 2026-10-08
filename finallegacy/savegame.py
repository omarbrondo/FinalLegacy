"""Guardado y carga de partidas (3 ranuras y autoguardado por oleada) y modo inmortal para probar todo sin morir."""
import json
import os
import time
import pygame
from .common import ANTENNA_ISLANDS, EXTRA_ISLANDS, H, PLAYER_HP, TK_HP, W, Particles

SAVE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'final_legacy_saves.json')
SLOT_KEYS = ('1', '2', '3', 'auto')
SAVE_VER = 1


class SaveMixin:
    # ------------------------------------------------------------------ archivo
    def sv_read(self):
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def sv_write(self, data):
        try:
            tmp = SAVE_FILE + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            os.replace(tmp, SAVE_FILE)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def sv_slots(self):
        return self.sv_read().get('slots', {})

    # ------------------------------------------------------------------ volumen
    def vol_load(self):
        d = self.sv_read()
        self.audio.set_vols(float(d.get('vol_music', 0.6)), float(d.get('vol_sfx', 0.6)))

    def vol_step(self, kind, delta, wrap=False):
        """kind = 'music' o 'sfx'; sube o baja 10 %. Con wrap, pasa de 100 % a 0 %."""
        cur = round((self.audio.mvol if kind == 'music' else self.audio.svol) * 10)
        new = cur + delta
        new = (new % 11) if wrap else max(0, min(10, new))
        v = new / 10.0
        if kind == 'music':
            self.audio.set_vols(mvol=v)
        else:
            self.audio.set_vols(svol=v)
        d = self.sv_read()
        d['vol_music'], d['vol_sfx'] = self.audio.mvol, self.audio.svol
        self.sv_write(d)
        self.audio.play('blip', .4)
        return int(new * 10)

    # ------------------------------------------------------------------ modo inmortal
    def set_god(self, on):
        self.god = bool(on)
        d = self.sv_read()
        d['god'] = self.god
        self.sv_write(d)
        self.toast('MODO INMORTAL: %s' % ('ACTIVADO' if self.god else 'desactivado'), (255, 220, 120))
        self.audio.play('ping', .6)

    def god_apply(self):
        """Mantiene al jugador (y a las ciudades) al máximo mientras el modo inmortal está activo."""
        if not self.god or self.state in ('title', 'gameover', 'saves'):
            return
        self.hull = max(self.hull, float(self.hull_max))
        for c in self.cities:
            if not c['dead']:
                c['hp'] = 100.0
        st = self.state
        try:
            if st == 'tank':
                p = self.k['p']
                p['hp'] = TK_HP
            elif st == 'aerial':
                p = self.a['p']
                p['hp'] = max(p['hp'], 100.0)
            elif st == 'ground':
                g = self.g
                g['p']['hp'] = PLAYER_HP
                if g['city'].get('hp', 100) < 100 and not g['city'].get('dead'):
                    g['city']['hp'] = 100.0
                for a in g.get('allies', ()):
                    if a['down'] or a['hp'] < a['max']:
                        a['down'], a['kia'], a['hp'] = False, False, a['max']
            elif st == 'port':
                p = self.pt['p']
                p['hp'] = PLAYER_HP
            elif st == 'heli':
                self.hm['p']['hp'] = 100.0
            elif st == 'lifeboat':
                self.lb['hp'] = 100.0
        except (AttributeError, KeyError, TypeError):
            pass

    def draw_god_tag(self, cv):
        if self.god and self.state not in ('title', 'saves'):
            if int(self.t * 2) % 2 == 0:
                self.text(cv, '* INMORTAL *', self.f_s, (255, 220, 110), W // 2, 6, 'c')

    # ------------------------------------------------------------------ instantánea de la partida
    def sv_snapshot(self, pending_upgrade=False):
        cities = [dict(hp=c['hp'], dead=c['dead'], stock=c['stock']) for c in self.cities]
        li = self.last_strike
        return dict(
            v=SAVE_VER, stamp=time.time(), score=self.score, wave=self.wave, lives=self.lives, next_life=self.next_life, pending_upgrade=bool(pending_upgrade),
            ship=dict(x=self.sx, y=self.sy, h=self.sh, v=self.sv), hull=self.hull, hull_max=self.hull_max, fuel=self.fuel, ammo=self.ammo,
            up=self.up, up_left=self.up_left, antennas=self.antennas, landing=self.landing_attempts, radars=self.radars,
            cleared=sorted(self.cleared_isl), cities=cities, port_tries=self.port_tries, port_done=self.port_done,
            strike=dict(t=self.strike_t, n=self.strike_n, deck=self.strike_deck, kind=self.strike_kind,
                        last=self.cities.index(li) if li in self.cities else -1),
            timers=dict(convoy=self.convoy_t, rescue=self.rescue_t, crate=self.crate_t, radar=self.radar_t),
            enemies=self.enemies, nests=self.nests, crates=self.crates,
            war=dict(moved=self.war['moved'], wrecks=self.war['wrecks'], slicks=self.war['slicks'], debris=self.war['debris'], scars=self.war['scars']),
            heli=dict(sorties=self.heli_sorties, next=self.heli_next, cd=self.heli_cd, earned=self.heli_earned, jets=self.jet_sorties))

    def sv_apply(self, d):
        self.reset()
        self.score, self.wave = int(d['score']), int(d['wave'])
        self.lives, self.next_life = int(d.get('lives', 3)), int(d.get('next_life', 5000))
        s = d['ship']
        self.sx, self.sy, self.sh, self.sv = s['x'], s['y'], s['h'], s['v']
        self.hull, self.hull_max, self.fuel, self.ammo = d['hull'], d['hull_max'], d['fuel'], d['ammo']
        self.up, self.up_left = dict(d['up']), int(d.get('up_left', 0))
        self.antennas = {i: bool(d['antennas'].get(str(i), False)) for i in ANTENNA_ISLANDS}
        self.landing_attempts = {i: int(d['landing'].get(str(i), 0)) for i in range(len(EXTRA_ISLANDS))}
        for k, rd in d.get('radars', {}).items():
            if int(k) in self.radars:
                self.radars[int(k)] = dict(hacked=bool(rd['hacked']), cd=float(rd['cd']))
        self.cleared_isl = set(d.get('cleared', []))
        for c, cd in zip(self.cities, d['cities']):
            c['hp'], c['dead'], c['stock'] = cd['hp'], cd['dead'], cd['stock']
            for k in c['stock']:
                c['stock'][k] = min(c['stock'][k], self.city_cap(c, k))
        st = d['strike']
        self.strike_t, self.strike_n, self.strike_deck, self.strike_kind = st['t'], st['n'], list(st['deck']), st['kind']
        self.last_strike = self.cities[st['last']] if st['last'] >= 0 else None
        tm = d['timers']
        self.convoy_t, self.rescue_t, self.crate_t, self.radar_t = tm['convoy'], tm['rescue'], tm['crate'], tm['radar']
        self.warned, self.attack, self.strike_city, self.convoy, self.rescue = False, None, None, None, None
        self.raid = None
        self.wx_reset()
        self.wx_wave_start(banner=False)
        self.enemies = d['enemies']
        for en in self.enemies:
            if isinstance(en.get('wp'), list):
                en['wp'] = tuple(en['wp'])
        self.nests, self.crates = d['nests'], d['crates']
        w = d['war']
        for k, pos in w['moved'].items():
            self.war_move_island(int(k), pos[0], pos[1])
        self.war.update(wrecks=w['wrecks'], slicks=w['slicks'], debris=w['debris'], scars=w['scars'])
        hl = d['heli']
        self.heli_sorties, self.heli_next, self.heli_cd = hl['sorties'], hl['next'], hl['cd']
        self.heli_earned = int(hl.get('earned', hl['sorties']))
        self.jet_sorties = int(hl.get('jets', 1))
        self.port_tries, self.port_done = int(d['port_tries']), bool(d['port_done'])
        self.cam = [self.sx - W / 2, self.sy - H / 2]
        self.fxm = Particles()
        self.paused = False
        if d.get('pending_upgrade'):
            self.enemies = []
            self.start_upgrade()
        else:
            self.go('map')

    # ------------------------------------------------------------------ guardar / cargar
    def sv_save(self, slot, pending_upgrade=False):
        data = self.sv_read()
        data.setdefault('slots', {})[slot] = self.sv_snapshot(pending_upgrade)
        return self.sv_write(data)

    def autosave(self, pending_upgrade=False):
        self.sv_save('auto', pending_upgrade)

    def sv_load(self, slot):
        d = self.sv_slots().get(slot)
        if not d or d.get('v') != SAVE_VER:
            return False
        try:
            self.sv_apply(d)
        except (KeyError, TypeError, ValueError, IndexError):
            self.toast('La partida guardada está dañada', (255, 130, 110))
            return False
        self.banner('PARTIDA CARGADA', 'Oleada %d  |  %d puntos' % (self.wave, self.score), (140, 230, 255), 3.0)
        return True

    # ------------------------------------------------------------------ menú de ranuras
    def open_saves(self, mode):
        if mode == 'save' and self.state != 'map':
            self.toast('Guardá desde el mapa (no durante una misión)', (255, 190, 120))
            return
        self.sv_menu = dict(mode=mode, cur=0, prev=self.state, was_paused=self.paused, msg='')
        self.paused = False
        self.state = 'saves'
        pygame.mouse.set_visible(True)

    def close_saves(self):
        m = self.sv_menu
        self.state = m['prev']
        self.paused = m['was_paused']

    def saves_key(self, key):
        m = self.sv_menu
        n = 3 if m['mode'] == 'save' else 4
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            return self.close_saves()
        if key in (pygame.K_UP, pygame.K_w):
            m['cur'] = (m['cur'] - 1) % n
        elif key in (pygame.K_DOWN, pygame.K_s):
            m['cur'] = (m['cur'] + 1) % n
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            m['cur'] = key - pygame.K_1
            self.saves_confirm()
        elif key == pygame.K_a and m['mode'] == 'load':
            m['cur'] = 3
            self.saves_confirm()
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self.saves_confirm()

    def saves_confirm(self):
        """Pide confirmación antes de guardar o cargar la ranura elegida."""
        m = self.sv_menu
        slot = SLOT_KEYS[m['cur']]
        d = self.sv_slots().get(slot)
        name = 'AUTOGUARDADO' if slot == 'auto' else 'la ranura %s' % slot
        if m['mode'] == 'save':
            if d:
                lines = ['%s ya tiene una partida: oleada %d, %d puntos.' % (name.capitalize(), d['wave'], d['score']), 'Se va a sobrescribir.']
            else:
                lines = ['Se guardará en %s.' % name]
            self.confirm_open('¿GUARDAR PARTIDA?', lines, self.saves_do)
        else:
            if not d:
                m['msg'] = 'Esa ranura está vacía'
                self.audio.play('hit', .4)
                return
            m['msg'] = ''
            self.confirm_open('¿CARGAR PARTIDA?', ['Cargar %s: oleada %d, %d puntos.' % (name, d['wave'], d['score']), 'Se pierde el progreso actual que no hayas guardado.'], self.saves_do)

    def saves_do(self):
        m = self.sv_menu
        slot = SLOT_KEYS[m['cur']]
        if m['mode'] == 'save':
            ok = self.sv_save(slot)
            self.toast('Partida guardada en la ranura %s' % slot if ok else 'No se pudo guardar la partida', (140, 255, 190) if ok else (255, 130, 110))
            self.say('secretaria', ('Progreso archivado en la ranura %s, capitán.' % slot) if ok else 'No pude archivar su progreso. Intente nuevamente.', 'ok' if ok else 'bad')
            self.audio.play('win' if ok else 'lose', .5)
            self.close_saves()
        elif self.sv_load(slot):
            self.audio.play('win', .6)
            self.say('secretaria', 'Partida cargada. Retomamos donde la dejó, capitán.', 'info')

    # ratón en el menú de ranuras: pasar el cursor selecciona, clic pide confirmación, clic derecho vuelve
    def saves_rects(self):
        n = 3 if self.sv_menu['mode'] == 'save' else 4
        return [pygame.Rect(W // 2 - 400, 200 + i * 110, 800, 92) for i in range(n)], pygame.Rect(W // 2 - 100, 636, 200, 42)

    def saves_mouse(self, e):
        if self.state != 'saves' or not hasattr(self, 'sv_menu'):
            return False
        rows, back = self.saves_rects()
        m = self.sv_menu
        if e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(rows):
                if r.collidepoint(e.pos):
                    m['cur'] = i
            return False
        if e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 3:
                self.close_saves()
                return True
            if e.button == 1:
                if back.collidepoint(e.pos):
                    self.close_saves()
                    return True
                for i, r in enumerate(rows):
                    if r.collidepoint(e.pos):
                        m['cur'] = i
                        self.saves_confirm()
                        return True
        return False

    def draw_saves(self, cv):
        m = self.sv_menu
        t = self.t
        self.draw_ocean(cv, t * 10, 0, t)
        self.dim(cv, 120)
        save = m['mode'] == 'save'
        self.text(cv, 'GUARDAR PARTIDA' if save else 'CARGAR PARTIDA', self.f_xl, (255, 230, 130) if save else (140, 220, 255), W // 2, 70, 'c')
        slots = self.sv_slots()
        rows = SLOT_KEYS[:3] if save else SLOT_KEYS
        for i, k in enumerate(rows):
            y = 200 + i * 110
            sel = i == m['cur']
            self.panel(cv, (W // 2 - 400, y, 800, 92), 200 if sel else 140)
            if sel:
                pygame.draw.rect(cv, (255, 230, 130), (W // 2 - 400, y, 800, 92), 3, border_radius=8)
            self.text(cv, 'AUTOGUARDADO' if k == 'auto' else 'RANURA %s' % k, self.f_m, (255, 255, 255) if sel else (190, 205, 230), W // 2 - 380, y + 10)
            d = slots.get(k)
            if d:
                n_ant = sum(1 for v in d['antennas'].values() if v)
                n_rad = sum(1 for r in d.get('radars', {}).values() if r['hacked'])
                alive = sum(1 for c in d['cities'] if not c['dead'])
                self.text(cv, 'OLEADA %d/6  |  %d puntos  |  %d ciudades  |  %d antenas  |  %d radares' % (d['wave'], d['score'], alive, n_ant, n_rad), self.f_s, (210, 230, 250), W // 2 - 380, y + 46)
                self.text(cv, time.strftime('%d/%m/%Y %H:%M', time.localtime(d.get('stamp', 0))) + ('  |  al terminar la oleada' if d.get('pending_upgrade') else ''),
                          self.f_s, (150, 175, 205), W // 2 - 380, y + 66)
            else:
                self.text(cv, '(vacía)', self.f_s, (130, 145, 170), W // 2 - 380, y + 52)
        if m['msg']:
            self.text(cv, m['msg'], self.f_m, (255, 140, 120), W // 2, 690, 'c')
        _, back = self.saves_rects()
        self.panel(cv, (back.x, back.y, back.w, back.h), 170)
        self.text(cv, 'VOLVER', self.f_m, (230, 240, 255), back.centerx, back.y + 8, 'c')
        self.text(cv, 'CLIC EN UNA RANURA O ARRIBA/ABAJO + ENTER  |  1-3' + ('' if save else '  |  A: autoguardado') + '  |  ESC o clic derecho: volver',
                  self.f_s, (190, 210, 240), W // 2, 740, 'c')
