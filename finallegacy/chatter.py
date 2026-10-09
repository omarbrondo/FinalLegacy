"""Charla aleatoria: los personajes comentan la partida con frases que cambian, la secretaría informa de la oleada, el comandante da órdenes y los enemigos provocan."""
import random
from .common import WIN_WAVE
from .radio_mode import LAND_RADARS, PORT_RADARS

# ---------------------------------------------------------------- frases de los aliados, por estado del juego
MAR_MAP = (
    'Mar en calma, capitán. Es justo cuando mejor hay que desconfiar.',
    'El radar está limpio por ahora. Que no se le suba a la cabeza.',
    'La tripulación está lista. El café, no tanto.',
    'Si ve una isla con antena, vale la pena visitarla: el jefe enemigo se pone nervioso.',
    'Recuerde: el reabastecimiento en puerto es gratis. Los errores de navegación, no.',
    'Los submarinos solo se dejan ver al emerger. Paciencia y torpedos.',
    'El mar siempre devuelve lo que se le da. Con intereses.',
    'Capitán, el casco aguanta, pero no le pida milagros.',
    'Rumbo despejado. Eso nunca dura mucho.',
    'Si necesita combustible, el Blackhawk puede dejarle un bidón: tecla C.',
)
MAR_COMBAT = (
    '¡Buen blanco, capitán! Siga así.',
    'Mantenga la distancia: los misiles del enemigo tardan en llegar, pero llegan.',
    'Si el casco se resiente, use el control de daños (G).',
    'Una descarga (Q) bien cargada vale más que diez disparos nerviosos.',
    'Cuidado con el humo: también esconde sus movimientos.',
    'Muévase, capitán. Un blanco quieto es un blanco muerto.',
    '¡El enemigo se está quedando sin paciencia... y sin casco!',
    'Si la cosa se pone fea, siempre queda la opción de huir (E). Nadie dirá nada.',
    'Los aviones enemigos no avisan: la cortina antiaérea es la tecla Z.',
)
ART_COMBAT = (
    'Artillería lista. Dígame a quién saludamos.',
    'Torpedo cargado. Siempre me ha gustado hacer entradas dramáticas.',
    '¡Impacto! Eso le va a doler en el seguro.',
    'Los cañones están calientes, capitán. Me encanta cuando están así.',
    'Munición al límite... pero hay para una más.',
    'Ese casco enemigo ya no se ve tan firme.',
)
PIL_AIR = (
    'Cielo a la vista. Y enemigos también, por desgracia.',
    'Recuerde: los potenciadores duran poco. Úselos mientras brillen.',
    'No se quede quieto, capitán. Los cazas leen la posición y le disparan adelantados.',
    'La bomba (B) sirve para las baterías y los barcos del suelo. Para los cazas, mejor el cañón.',
    '¡Ese caza nunca supo qué lo golpeó!',
    'Mantenga la formación... bueno, usted es la formación.',
    'Si ve una cápsula, vaya por ella. Un buen arma cambia la partida.',
    'Cuidado con los kamikazes: no disparan, solo embisten. Y no tienen seguro.',
)
PIL_JETS = (
    'Alas arriba, escuadrón. Que se noten los colores.',
    'Misiles guiados: apunte con el morro, fije el blanco y deje que la física haga el resto.',
    'Bengalas, capitán. Un misil entrante no es un buen momento para ser valiente.',
    'Postquemador: para huir y para presumir, pero gasta mucho.',
    'Mis alas cubren su cola. Usted cubra la mía.',
    'Los destructores tienen misiles antiaéreos. No pasen en línea recta sobre ellos.',
)
PIL_HELI = (
    'Rotores a máxima potencia. El suelo se ve diminuto desde aquí.',
    'Cuidado con las antiaéreas: les encanta un helicóptero lento.',
    'Los cohetes son limitados. Elija bien dónde dejarlos caer.',
    'Misión de ataque en curso. Que no quede nada en pie.',
)
TK_LINES = (
    'Blindado en marcha. La ciudad cuenta con nosotros.',
    'Los tanques enemigos no se rinden. Nosotros tampoco.',
    'Mantenga el casco hacia el enemigo: el frontal es lo que más aguanta.',
    'Si la armadura baja, aléjese y deje que la tripulación repare un poco.',
    'Los edificios son buena cobertura, pero también estorban el disparo.',
    'Atento a los drones: no hacen daño por sí solos, pero distraen.',
    'Cuidado con los tanques suicidas. Les falta instinto de conservación.',
)
SOL_GROUND = (
    'Soldados en posición. Esta ciudad no se toma sin pelea.',
    'Cubran los flancos. Y no se queden quietos bajo el fuego.',
    '¡Granada! Tiren la suya primero, si pueden.',
    'El ayuntamiento es el objetivo. Si cae, caemos todos.',
    'Recuerden: la cobertura salva vidas. Y las vidas salvan partidas.',
    'Cuando sientan la tentación de ser héroes, recuerden el dolor de una bala.',
)
SOL_PORT = (
    '¡Adelante, el puerto es nuestro! Pero con cuidado: hay francotiradores.',
    'Si ve un punto rojo en el suelo, un francotirador lo apunta. Muévase.',
    'Granaderos al frente: no les dé tiempo a cargar.',
    'Las armas pesadas del suelo valen oro: la escopeta y el lanzacohetes.',
    'Los prisioneros están aterrados. Libérelos y recibirá un regalo.',
    'Agáchese al recibir fuego: el que se agacha, cuenta el cuento.',
    '¡Combo! Cada baja seguida suma puntos. Ahora, no se descuide.',
)
ART_DEF = (
    'Defensa antimisiles activa. Ningún proyectil pasará... en teoría.',
    'Apunte con calma: los misiles son rápidos, pero no inteligentes.',
    'Los misiles pesados son los peores. Elíjalos primero.',
    'Cada misil que cae es una ciudad que se queda de pie.',
    '¡Eso! Uno menos para el listado.',
)
ART_BAT = (
    'Los cañones están a su orden, capitán. Que los invasores prueben suerte.',
    'La ametralladora se recalienta: dispare en ráfagas cortas.',
    'El proyectil pesado cae en el círculo. Ahí el enemigo va a bailar.',
    'Cortina antiaérea lista: úsela cuando se junten los aviones.',
    'Cada soldado que no desembarca es un soldado que no nos molesta.',
)
HK_MAP = (
    'Estoy escuchando las frecuencias enemigas. Mucho ruido, poca inteligencia.',
    'Si ve un radar enemigo, presione H. Entre amigos, hackear es de buena educación.',
    'Los ciberataques me ponen de buen humor.',
    'Cada radar interceptado es una puerta más abierta, capitán.',
    'Todavía no me han bloqueado el acceso. Lo cual es sospechoso.',
    'Recuerde: antenas en islas = escudo del jefe más débil.',
)
CMD_MAP = (
    'Mantenga la presión sobre la flota enemiga, capitán. Sin descanso.',
    'Las ciudades son prioridad. Cada una que cae pesa en esta guerra.',
    'No deje que lo rodeen. Un buque aislado es un buque perdido.',
    'Los refuerzos llegan solos. Los éxitos hay que ganarlos.',
    'Informe cualquier avistamiento de jefes. No se enfrente a ciegas.',
    'Utilice las baterías aliadas: con una buena defensa, ahorra casco.',
    'Recuerde la misión: neutralizar la flota y proteger el archipiélago.',
    'Esta guerra se gana con paciencia, pero se pierde con descuido.',
)

# ---------------------------------------------------------------- provocaciones de los enemigos
ENEMY_NAVAL = (
    '¿Eso es todo lo que tiene, capitán? Mi abuela maneja mejor un bote.',
    'Se hundirá como los demás. Es solo cuestión de tiempo.',
    'Nuestra flota es más grande. Nuestros cañones, también.',
    'Disparen sin piedad. No queremos supervivientes.',
    'Admirable resistencia. Lástima que sea inútil.',
    '¡Fuego! No dejen que escape.',
    'Su casco ya cruje. Lo oigo desde aquí.',
)
ENEMY_AIR = (
    'Tiene buenos reflejos... para un piloto de museo.',
    'Ya lo tengo en la mira. Nadie escapa de mí.',
    'El cielo es nuestro. Usted solo está de visita.',
    '¿Le molestó ese disparo? Hay más de donde vino.',
    'Escuadrón, ataquen en formación. ¡No dejen respirar a ese F-16!',
    'Sus alas están a punto de pasar a la historia... como un recuerdo.',
)
ENEMY_GROUND = (
    'Este terreno es nuestro. Retírense ahora.',
    '¡Disparen! No dejen que avancen ni un metro.',
    'Se están metiendo en la boca del lobo.',
    'Hoy defendemos esto con nuestra vida. ¿Usted qué defiende?',
    'Tres de los suyos ya cayeron. ¿Quiere ser el cuarto?',
    'Valientes, sí. Eficaces, no tanto.',
)
ENEMY_TANK = (
    'Mi blindaje no se rasga con juguetes.',
    'Este tanque ha aplastado cosas más grandes que usted.',
    'Apunten al frontal. Les enseñaremos qué es un blindado de verdad.',
    '¡Avancen! No dejen un solo edificio en pie.',
    'Su cañón me hace cosquillas. Ahora le toca a usted.',
)
ENEMY_BAT = (
    'Esta isla ya es nuestra. Retírense mientras puedan.',
    '¡Desembarquen! Nada ni nadie nos detendrá.',
    'Los cañones no tendrán dueño cuando acabemos.',
    '¡Ataquen por todos los frentes!',
)

# ---------------------------------------------------------------- variantes extra para los jefes (se suman a la frase original)
BOSS_APPEAR_X = (
    'Prepárese, capitán. Esta es mi zona y yo pongo las reglas.',
    'Otro visitante sin invitación. Qué descortés.',
    'No hemos terminado con usted, y usted no terminó con nosotros.',
    'Mis cañones llevan años esperando por alguien como usted.',
)
BOSS_DEFEAT_X = (
    'No puede ser... la flota entera depende de mí.',
    'Mi casco... cede... Díganles que luché hasta el final.',
    'Me hundo... pero no solo.',
    'Impresionante... para ser un buque tan pequeño.',
)
AIR_APPEAR_X = (
    'Un piloto menos para el cielo. Ya sabe lo que le espera.',
    'Mis alas no conocen el miedo. ¿Y las suyas?',
    'Tengo órdenes de derribarlo. Con gusto.',
)
AIR_DEFEAT_X = (
    'Mi cabina... se llena de humo... ¡eyección!',
    'Me derribó... pero seguirán más.',
    'Un vuelo magnífico. El suyo, no el mío.',
)
PORT_APPEAR_X = (
    'Este puerto lleva años sin caer. No será usted quien lo logre.',
    'Defiendan la posición. ¡Hasta el último hombre!',
    'Se ha metido donde no debía.',
)
PORT_DEFEAT_X = (
    'No... esto no puede estar pasando...',
    'Perdimos el puerto. Pero la guerra sigue.',
    'Mi unidad... se rinde. Han ganado hoy.',
)

# ---------------------------------------------------------------- pistas por oleada para la secretaría
WAVE_HINT = {
    1: 'Los primeros buques enemigos ya están en el mapa. Empiece por los más cercanos a las ciudades.',
    2: 'Se esperan convoyes y cazas más agresivos. Aparecen cápsulas de potenciador en la batalla aérea.',
    3: 'Hay buques jefe con escudo digital: instale antenas en las islas para poder hackearlos.',
    4: 'Los destructores traen apoyo aéreo. Tenga a mano la cortina antiaérea (Z).',
    5: 'La resistencia enemiga se endurece. Revise sus reservas antes de cada combate.',
    6: 'Es la última oleada. Cada ciudad que aguante vale doble.',
}


class ChatterMixin:
    def chat_init(self):
        self._chat_hist = {}
        self._chat_t = 24.0
        self._chat_st = None
        self._chat_warn = {}

    # ------------------------------------------------------------ elección sin repetir
    def chat_pick(self, key, options):
        hist = self.__dict__.setdefault('_chat_hist', {})
        last = hist.get(key, [])
        pool = [o for o in options if o not in last] or list(options)
        o = random.choice(pool)
        hist[key] = (last + [o])[-max(1, min(4, len(options) // 2)):]
        return o

    def var(self, key, base, extra):
        """Una frase fija del juego mezclada con variantes para que no se repita siempre igual."""
        return self.chat_pick(key, (base,) + tuple(extra))

    # ------------------------------------------------------------ partes de la secretaría
    def chat_report(self):
        """Informe de la secretaría con datos reales de la partida."""
        w = self.wave
        alive = [c for c in self.cities if not c['dead']]
        n_en = len([e for e in self.enemies if not e.get('is_boss')])
        bosses = len([e for e in self.enemies if e.get('is_boss')])
        n_ant = sum(self.antennas.values())
        need = self.antennas_needed()
        nr = self.radars_done()
        out = [
            'Oleada %d de %d. Quedan %d buques enemigos%s en el mapa.' % (w, WIN_WAVE, n_en, (' y %d jefe' % bosses + ('s' if bosses > 1 else '')) if bosses else ''),
            'Faltan %d oleada%s para ganar la guerra.' % (WIN_WAVE - w, '' if WIN_WAVE - w == 1 else 's'),
            'Antenas instaladas: %d. El escudo del jefe pide al menos %d.' % (n_ant, need),
            'Radares interceptados: %d. El desembarco pide %d y el asalto al puerto, %d.' % (nr, LAND_RADARS, PORT_RADARS),
            'Ciudades en pie: %d de %d.' % (len(alive), len(self.cities)),
            'Reservas: casco al %d%%, combustible al %d%%, munición %d.' % (round(100 * self.hull / max(1, self.hull_max)), round(self.fuel), self.ammo),
            'Puntaje actual: %d. El récord de la casa es %d.' % (self.score, self.hiscore),
            WAVE_HINT.get(w, 'Siga atento al radar y a las ciudades.'),
            'Recordatorio: en la base aérea (isla con la H) puede despegar el Blackhawk con B y el F-16 con J.',
            'Recordatorio: una batería aliada invadida se defiende con la tecla E al acercarse.',
        ]
        if alive:
            worst = min(alive, key=lambda c: c['hp'])
            out.append('La ciudad más dañada es %s, al %d%% de integridad.' % (worst['name'], round(worst['hp'])))
        return self.chat_pick('sec_report', out)

    def chat_wave_start(self):
        """Al empezar cada oleada: la secretaría informa y el comandante da la orden."""
        w = self.wave
        n_en = len([e for e in self.enemies if not e.get('is_boss')])
        self.say('secretaria', self.chat_pick('sec_wave', (
            'Comienza la oleada %d de %d. %s' % (w, WIN_WAVE, WAVE_HINT.get(w, '')),
            'Oleada %d. Detectamos %d buques enemigos. %s' % (w, n_en, WAVE_HINT.get(w, '')),
            'Atención, capitán: oleada %d de %d. %s' % (w, WIN_WAVE, WAVE_HINT.get(w, '')),
        )), 'info', 'right', 640)
        self.say('comandante', self.chat_pick('cmd_wave', (
            'Aquí el comando. Esta oleada decide el rumbo de la guerra. No me defraude.',
            'Capitán, los ojos del archipiélago están sobre usted. Adelante.',
            'Órdenes claras: proteja las ciudades y hunda lo que se cruce.',
            'Que cada disparo cuente. Éxitos, capitán.',
        )), 'info', 'right', 640)

    def chat_city_lost(self, city):
        self.say('comandante', self.chat_pick('cmd_city', (
            '¡Perdimos %s! El enemigo pagará por esto, capitán.' % city['name'],
            '%s ha caído. Concéntrese en proteger las que quedan.' % city['name'],
            'Mala noticia: %s ya no responde. Sigamos adelante.' % city['name'],
        )), 'bad')

    # ------------------------------------------------------------ charla ambiental
    def chat_tick(self, dt):
        st = self.state
        if self.paused:
            return
        if st != self._chat_st:
            self._chat_st = st
            self._chat_t = random.uniform(14.0, 24.0)             # al entrar a un modo se espera un rato antes de hablar
        cm = self.cm
        if st not in ('map', 'combat', 'aerial', 'jets', 'heli', 'tank', 'ground', 'port', 'defense', 'batdef'):
            return
        # avisos de estado (casco, combustible, munición) en el mapa, con enfriamiento
        if st == 'map':
            for k in list(self._chat_warn):
                self._chat_warn[k] -= dt
            low = None
            if self.hull < 0.3 * self.hull_max and self._chat_warn.get('hull', 0) <= 0:
                low = ('hull', 'comandante', ('Capitán, el casco está por debajo del 30%. Repare en un puerto o no pelee más.', 'Su barco está al límite. Un puerto cercano le vendría muy bien.'))
            elif self.fuel < 20 and self._chat_warn.get('fuel', 0) <= 0:
                low = ('fuel', 'marinero', ('Combustible bajo, capitán. El Blackhawk puede dejarle un bidón: tecla C.', 'Los tanques casi vacíos. Otro tanto y remamos.'))
            elif self.ammo <= 4 and self._chat_warn.get('ammo', 0) <= 0:
                low = ('ammo', 'artillero', ('Munición casi agotada. Reponga en un puerto antes de pelear.', 'Quedan muy pocos proyectiles. No los gaste en falsas alarmas.'))
            if low and cm['cur'] is None and not cm['queue']:
                self._chat_warn[low[0]] = 70.0
                self.say(low[1], self.chat_pick('warn_' + low[0], low[2]), 'warn')
                return
        self._chat_t -= dt
        if self._chat_t > 0 or cm['cur'] is not None or cm['queue'] or self.t - cm.get('end', -99) < 6.0:
            return
        self._chat_t = random.uniform(26.0, 44.0)
        enemy_states = ('combat', 'aerial', 'jets', 'tank', 'ground', 'port', 'batdef')
        if st in enemy_states and random.random() < 0.35:
            return self.chat_enemy()
        if st == 'map':
            who = random.choice(('secretaria', 'secretaria', 'comandante', 'marinero', 'hacker'))
            if who == 'secretaria':
                return self.say('secretaria', self.chat_report(), 'info', 'right', 640)
            pool = {'comandante': CMD_MAP, 'marinero': MAR_MAP, 'hacker': HK_MAP}[who]
            return self.say(who, self.chat_pick('map_' + who, pool), 'info')
        spec = {'combat': (('marinero', MAR_COMBAT), ('artillero', ART_COMBAT)), 'aerial': (('piloto', PIL_AIR),), 'jets': (('piloto', PIL_JETS),),
                'heli': (('piloto', PIL_HELI),), 'tank': (('tanquista', TK_LINES),), 'ground': (('soldado', SOL_GROUND),), 'port': (('soldado', SOL_PORT),),
                'defense': (('artillero', ART_DEF),), 'batdef': (('artillero', ART_BAT),)}.get(st)
        if spec:
            who, pool = random.choice(spec)
            self.say(who, self.chat_pick(st + '_' + who, pool), 'info')

    def chat_enemy(self):
        """Provocación de un enemigo (cambia al azar)."""
        st = self.state
        boss = None
        if st == 'combat':
            ref = getattr(self, 'enemy_ref', None) or {}
            boss = ref.get('is_boss')
            name = ref.get('name') if boss else 'CAPITÁN ENEMIGO'
            v = (self.c.get('btype', self.wave) % 6 + 1) if boss else self.wave % 6 + 1
            return self.say('jefe_barco', self.chat_pick('en_naval', ENEMY_NAVAL), 'bad', pose='', v=v, name=name or 'CAPITÁN ENEMIGO')
        if st in ('aerial', 'jets'):
            return self.say('jefe_avion', self.chat_pick('en_air', ENEMY_AIR), 'bad', pose='', v=self.wave % 6 + 1, name='PILOTO ENEMIGO')
        if st == 'tank':
            return self.say('jefe_puerto_tanque', self.chat_pick('en_tank', ENEMY_TANK), 'bad', pose='', v=self.wave // 2 % 2 + 1, name='TANQUISTA ENEMIGO')
        if st == 'batdef':
            return self.say('jefe_barco', self.chat_pick('en_bat', ENEMY_BAT), 'bad', pose='', v=self.wave % 6 + 1, name='CAPITÁN INVASOR')
        return self.say('jefe_puerto_tanque', self.chat_pick('en_ground', ENEMY_GROUND), 'bad', pose='', v=self.wave // 2 % 2 + 1, name='OFICIAL ENEMIGO')
