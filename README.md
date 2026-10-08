# RETRO LEGACY

Juego de guerra naval y de infantería hecho con **Python + pygame**. Todo el arte y el sonido se generan por código, así que no necesita archivos externos.

## Ejecutar

```
pip install -r requirements.txt
python retro_legacy.py
```

(El juego se llamaba *Final Legacy*: `python final_legacy_omar.py` sigue funcionando.)

## Estructura del código

`retro_legacy.py` es solo el punto de entrada. El juego vive en el paquete `finallegacy/`:

| Archivo | Contenido |
| --- | --- |
| `common.py` | Constantes, utilidades matemáticas, helpers de dibujo y partículas |
| `audio.py` | Síntesis de sonido y música |
| `sprites.py` | Naves, soldados cenitales, cazas, nubes, coberturas |
| `boss_art.py` | Los 6 jefes navales (siluetas y habilidades de cada uno) |
| `tk_art.py` | Texturas y modelo 3D del tanque (combate urbano) |
| `pt_art.py` | Arte del asalto lateral (soldados, tanque, fondo) |
| `core.py` | Recursos, UI común, partida, eventos y bucle principal |
| `wave_world.py` | Clima por oleada, corrientes marinas, roles de ciudades y eventos de oleada |
| `defense_art.py` | Arte de la defensa: skyline por capas y destructor de perfil |
| `comms.py` | Personajes con globo de cómic que comunican mensajes |
| `air_raid.py` | Incursiones de cazas sobre el barco (pasadas de bombardeo y antiaéreo) |
| `drone_art.py` | Dron de ataque del modo tanque (cuadricóptero) |
| `convoy.py` | Convoy épico: escoltas, emboscadas, antiaéreo y descarga que reabastece la ciudad |
| `map_mode.py` | Mapa: navegación, olas, ataques a ciudades, convoy, náufragos |
| `defense_mode.py` | Defensa de la ciudad contra misiles |
| `hack_mode.py` | Ciberataque al escudo del jefe |
| `naval_mode.py` | Combate naval (destructores, submarinos, baterías, acorazado) |
| `lifeboat.py` | Vidas (3 buques) y huida en lancha salvavidas hasta una ciudad |
| `lifeboat_art.py` | Arte de la huida: orillas, arrecifes, lancha, aviones y puerto visto desde arriba |
| `naval_combo.py` | Combate combinado: barco enemigo + batería costera cercana en un mismo combate |
| `aerial_mode.py` | Batalla aérea estilo Twinbee |
| `ground_mode.py` | Infantería cenital: invasión, desembarco con sigilo, defensa de antenas |
| `title_art.py` | Título cromado retrowave del menú (degradado, extrusión 3D, destellos y reflejo) |
| `menu.py` | Menú principal y opciones (pantalla completa, CRT, instrucciones, cheats) |
| `splash.py` | Videos MP4 de presentación (logo e intro) con salto por clic |
| `ground_city.py` | Distrito urbano de la invasión anfibia: manzanas, edificios y autos con colisión, navegación por calles |
| `landing.py` | Desembarco épico: escuadra aliada, fases, búnkeres, clima y informe de misión |
| `savegame.py` | Guardado/carga de partidas y modo inmortal |
| `radio_mode.py` | Radares enemigos en islotes y minijuego de intercepción de radio |
| `port_epic.py` | Asalto al puerto: combos, armas pesadas, suministros y apoyo aéreo |
| `landing_ops.py` | Desembarco: apoyo naval, minas, morteros, reflectores y bengalas |
| `port_mode.py` | Asalto al puerto enemigo (estilo Metal Slug) |
| `tank_mode.py` | Combate urbano con tanques en primera persona (estilo Battlezone) |
| `upgrade_mode.py` | Pantalla de mejoras entre oleadas (elegir 1 de 3) |
| `hazards.py` | Nubes tóxicas, máscara antigás y misil Tomahawk en infantería y puerto |
| `heli_mode.py` | Helipuerto, Blackhawk (bidón de combustible) y misiones aire-tierra |
| `heli_art.py` | Arte del Blackhawk (a escala de barco) y de los objetivos de las misiones aéreas |
| `naval_fx.py` | Efectos del combate naval: daños, hundimiento partido, clima, locutor |
| `naval_arms.py` | Descarga especial, torpedos, humo y control de daños |
| `naval_fleet.py` | Escoltas, aviones, aliado, flanqueo y artillería en las batallas navales |
| `war.py` | Huellas de la guerra en el mapa: restos, petróleo, islas dañadas y islotes que se mueven |
| `car_art.py` | Autos 3D pre-renderizados (intactos, quemados y aplastados) |
| `tk_props.py` | Farolas, autos y bicicletas en la ciudad del tanque (aplastables) |
| `music.py` | Compositor de música por modo y oleada |
| `render_fx.py` | Post-proceso (bloom, viñeta, color, grano) y sprites suaves de humo/fuego/brillo |
| `gamepad.py` | Mando Xbox y pantalla completa |
| `game.py` | Clase `Game` (une los modos) y `main()` |

Cada modo es un *mixin*: una clase con los métodos de ese modo que `Game` hereda, de modo que todos comparten el mismo estado (`self`).

## Progresión por oleada

Cada modo suma contenido nuevo a medida que avanzan las oleadas:

- **Aéreo**: un jefe distinto por oleada, kamikazes, minas, helicópteros y clima. Sin potenciadores (no caen cápsulas de arma, salud, escudo ni ráfaga), así que el avión no mejora durante el combate. Los barcos enemigos avanzan con el mar y rebotan al llegar a una isla.
- **Ataques**: en la oleada 1 el primer ataque es de misiles y el segundo siempre aéreo; después la baraja mezcla todos los tipos sin repetir el anterior.
- **Defensa en tres olas** (unos 45 a 75 s en vez de 15): OLA 1/3, OLA 2/3 y ¡ASALTO FINAL! (la última con borde rojo palpitante), con pausas entre olas, **salvas masivas** (5 a 7 misiles a la vez), aviones durante las olas 2 y 3 y la ojiva nuclear en el asalto final (desde la oleada 3). Si una ola termina sin impactos ganás un bonus (+200, +300, +400), y al empezar la ola 2 y la 3 te reabastecen 8 de munición; cada 3 interceptores gastan 1 de munición.
- **Ataque de misiles a una ciudad**: como los demás ataques, hay que **llegar con el barco** a la ciudad antes de que se acabe el tiempo (si llegás tarde, la ciudad pierde 45 % de vida). El reloj sigue corriendo si por el camino caés en un combate contra un barco o una batería, y se muestra arriba a la derecha durante la pelea.
- **Comunicaciones con viñetas**: un personaje entra por un costado de la pantalla, dice su mensaje en un globo de cómic con el texto escribiéndose y se va por el mismo lado; los mensajes se encolan. Hablan el hacker, el piloto, el marinero, el tanquista, el artillero, el soldado (y Ramos, Díaz y Luna en el desembarco), la secretaría del comando y los jefes (aparecen con cara desafiante y se despiden con cara de derrota). Cubren hackeo, radio, convoy, combates naval, aéreo, de tanques, de tierra y de puerto, mapa, mejoras y guardado. Los bustos son PNG en `portraits/` (ver `portraits/LEEME.txt`: tres personajes por oficio, estados `_ok`, `_warn` y `_bad`); sin imagen se usa una silueta provisoria. Desde el código: `self.say('hacker', 'texto', 'ok'|'warn'|'bad'|'info', side='left'|'right', y=posición)`.
- **Volumen**: Opciones tiene MÚSICA y EFECTOS (de a 10 %); en partida `-` y `+` ajustan la música y `M` silencia todo. Arranca al 60 % y se guarda entre sesiones.
- **Soldados mujeres**: en cada batalla a pie (asalto al puerto, combate cenital y desembarco) el soldado protagonista es **hombre o mujer al azar** (mujer: coleta rubia castaña y hombros más angostos en la vista cenital); una de las tres aliadas del desembarco (LUNA) es mujer y cerca del 40 % de los soldados enemigos (fusileros, cuchilleros y francotiradores en el asalto al puerto; todos los tipos en el combate cenital) también. En `finallegacy/common.py`: `PLAYER_FEMALE` (`None` = al azar, `True` = siempre mujer, `False` = siempre hombre) y `FEM_CHANCE` (fracción de enemigas).
- **Buques**: el barco del jugador y los destructores enemigos (mapa y combate) tienen un diseño más detallado visto desde arriba: casco con volumen y reborde de espuma, planchas en cubierta, superestructura en niveles con puente iluminado, mástil con radar, chimenea, celdas de misiles, botes salvavidas y torretas; el enemigo suma franjas de combate.
- **Defensa con el clima de la oleada**: el ataque de misiles ahora respeta la hora y el clima del mapa: de día (oleadas 1, 2 y 4) cielo azul con sol y nubes, ciudad con vidrios que reflejan el cielo y sin luces; de noche (3, 5 y 6) el cielo estrellado de siempre con la ciudad iluminada; con niebla (2 y 5) bruma sobre la ciudad; con tormenta (4 y 6) nubes oscuras, lluvia y relámpagos. De día los misiles y los interceptores se dibujan con más contraste.
- **Defensa (arte)**: skyline por capas (siluetas lejanas y edificios con degradado, ventanas de varios tonos, remates, luces rojas y farolas de la costanera con reflejos en el agua) y un destructor de perfil detallado (casco con planchas y portillos, puente, mástil con radar, chimenea y celdas de misiles).
- **Defensa**: misiles rápidos, evasivos, señuelos, MIRV; desde la oleada 3, ALERTA NUCLEAR (ojiva con cuenta regresiva, flash y onda expansiva que derrumba edificios); ráfaga doble por combos; cielos distintos.
- **Tanques**: luna con relieve (mares, cráteres y fase) y bicicletas 3D con cuadro, ruedas con rayos, manubrio, asiento y a veces canasto o portaequipaje (6 colores; aplastadas quedan retorcidas en el piso). Kamikazes, artillería pesada, drones de ataque (cuadricópteros con hélices girando, cámara roja y luces de posición; desde la oleada 4), tanque jefe, niebla y noche; la ciudad tiene farolas (se encienden de noche), autos y bicicletas que los tanques aplastan (los proyectiles incendian los autos); cuanto más avanza la guerra, más autos quemados y farolas caídas.
- **Mapa**: cada oleada deja restos de barcos hundidos (algunos en llamas), manchas de petróleo, escombros flotantes, islas chamuscadas con humo y una bruma cada vez más densa; además algunos islotes cambian de lugar.
- **Infantería**: perros y francotiradores (láser de mira); desde la oleada 3, alertas químicas (nube verde que daña, máscara antigás de 14 s como ítem).
- **Desembarco** (cuatro fases): llegás en lancha con el buque tirando fuego de cobertura sobre los búnkeres; **1 PLAYA** (destruí los 2 búnkeres con granadas o avanzá tierra adentro: la ametralladora fija avisa con un cono rojo), **2 INTERIOR** (sigilo como siempre), **3 ANTENA** (al instalarla empieza a transmitir: defendé la posición 22 s contra tres oleadas de lanchas; si te alejás la señal retrocede), **4 EXTRACCIÓN** (volvé a la lancha antes de que se acabe el tiempo). Te acompañan 3 soldados aliados (RAMOS, DÍAZ, LUNA) que te siguen, se cubren y disparan; los enemigos también les disparan, y si caen quedan heridos 28 s: mantené E a su lado para auxiliarlos. **Apoyo naval** (T / RB, TAB / Back cambia el tipo): ARTILLERÍA (marca amarilla, 1,8 s después caen 6 proyectiles; también te dañan a vos y a tu escuadra si estás cerca) o HUMO (cortina de 16 s que corta la vista de los enemigos y ayuda a perder la persecución); recarga 45 s / 30 s. **Peligros**: campos minados con carteles amarillos «CAMPO MINADO» (las minas se ven como discos metálicos con una luz roja que parpadea más rápido al acercarte; explotan al pisarlas, al dispararles o con granadas y en cadena con las vecinas; la primera vez que te acercás a un cartel, Ramos avisa por radio), morteros fijos desde la oleada 2 (solo disparan con la alarma activa; se destruyen con granadas), reflectores nocturnos con haz ancho y una bengala enemiga que revela tu posición tras una alarma. Clima según la oleada (día, amanecer, noche con luz propia, tormenta con rayos), cámara lenta en noqueos y disparos de francotirador, música distinta por fase e informe final con bonus (fantasma, tiempo, escuadra a salvo).
- **Puerto** (estilo Metal Slug): jefe tanque u helicóptero según la oleada; noche y tormenta. El asalto es más largo (9600 px: 10 grupos de enemigos, 6 torretas, 5 prisioneros y 16 barriles explosivos, con el jefe al final). Los paracaidistas abatidos en el aire caen al piso (el paracaídas se desinfla) y los cuchilleros embisten, apuñalan una vez y retroceden. **Combos**: cada baja en menos de 2,6 s de la anterior encadena (TRIPLE, PENTA, MASACRE, IMPARABLE, con bonus). **Armas pesadas**: escopeta (S) y lanzacohetes (R) además de la ametralladora (H), en el nivel, en los prisioneros y en las bajas. **Suministros** que bajan en paracaídas cada ~35 s. **Apoyo aéreo** (E / Y): se carga con bajas y combos; un bombardero cruza la pantalla soltando 10 bombas.
- **Hackeo**: virus que corrompen nodos, cortafuegos y segunda fuente. El escudo digital del jefe (radio 230 px en el mapa) **no te frena**: si entrás, la interferencia daña el casco (4 por segundo en el borde, hasta 13 pegado al jefe), con ruido en pantalla y aviso; alejate o hackealo con H (alcance 520 px).
- **Tomahawk** (mejora): apoyo de fuego en infantería y puerto, tecla T / LB sobre el punto apuntado (1,7 s de demora, radio ~150, hace daño a quien esté cerca incluso a vos).
- **Vidas**: tenés 3 buques (se ven como iconos arriba a la izquierda, junto a los puntos). Si se hunde uno y te quedan más, huís en una **lancha salvavidas** hasta la ciudad viva más cercana: tenés un tiempo limitado (WASD mover, ESPACIO/SHIFT/clic derecho: motor a fondo, que avanza más rápido pero se recalienta; sin forzar el motor no llegás a tiempo; clic izquierdo: ráfaga corta de 3 balas hacia el mouse, que hunde a las lanchas enemigas en dos ráfagas y destruye minas) con vista desde arriba tipo River Raid: las orillas con palmeras se desplazan y te encierran en un canal, hay arrecifes (-8) y minas flotantes (-14; las lanchas enemigas las ven y las esquivan por arriba o por abajo, o frenan si no hay lugar; si una mina explota cerca de ellas, las daña: dispará a las minas para hundirlas), powerups flotantes (salud +30, nitro 5 s, escudo de 3 impactos) y en el camino lanchas rojas y aviones (los mismos modelos del combate aéreo, al azar) te disparan ráfagas de ametralladora (la lancha aguanta 100 de vida, cada bala resta 3; las ráfagas se esquivan cambiando de rumbo, los aviones avisan con una «!» y una línea roja apenas 0,4 s antes). Al final aparece el puerto de la ciudad visto desde arriba (manzanas, grúas, contenedores, faro) y ganás apenas la lancha toca el muelle (no hace falta subirse a la ciudad); la barra de avance sube según el tiempo recorrido o, si el puerto ya se ve, según qué tan cerca esté la proa del muelle, y llega al 100 % al tocarlo. Si llegás, recibís un buque nuevo en el puerto de esa ciudad (casco, combustible y munición repuestos). Si la lancha se hunde o se acaba el tiempo, termina la partida, y lo mismo si se hunde tu último buque. Cada **5000 puntos** ganás una vida extra (hasta 5 buques). Las vidas se guardan en las partidas.
- **Combate naval**: Q descarga especial (abanico de 5 misiles, se carga acertando), R torpedo (alcanza al submarino sumergido), F o clic derecho cortina de humo, G control de daños (apaga incendios). Los cascos muestran impactos y fuego, se parten al hundirse, hay cámara lenta en el golpe final, tormentas, noche con reflectores y un locutor. Mando: LB descarga, X torpedo, B/RB/LT humo, Y control de daños, Back huir. **Ametralladora automática**: el barco dispara ráfagas solo (la IA apunta) a aviones, cazas, escoltas, minas y al enemigo si está a menos de 380 px; hace poco daño (apoya a los misiles) y se recalienta (barra MG): tras ~2,5 s de fuego continuo se traba 2,6 s. **Combate combinado**: si una batería costera y un barco enemigo (destructor o submarino, no el jefe) están cerca, se pelea contra los dos a la vez: la batería queda como cañón fijo en un costado con su propia barra y hay que hundir a ambos (premios de los dos + 300 de «doble victoria»; el barco dispara algo más espaciado mientras la batería siga en pie). Huir (E) deja la batería herida en el mapa. Apoyo aéreo aliado: un contador (panel de habilidades) llega a cero cada ~35 s y un caza aliado pasa dos veces lanzando misiles al enemigo; los misiles enemigos pueden derribarlo (cae en llamas y el contador tarda más). Batallas a gran escala: escoltas enemigas (desde la oleada 3), ataques aéreos con bombas (desde la 4), escolta aliada, cañones de flanco y artillería con aviso rojo en las baterías costeras (desde la 3).
- **Radares enemigos** (6 islotes vacíos, rojos en el radar del mapa; H cerca de uno, o N para ir a probar): el hackeo tiene dos pasos. 1) el minijuego de nodos del jefe y 2) la **intercepción de radio**, un osciloscopio estilo Batman: calzar la onda amarilla con la celeste con A/D (frecuencia), W/S (amplitud) y Q/E (fase) hasta bloquear la señal (el joystick usa palanca/cruceta, LB/RB para la fase). El minijuego cambia en cada estación (3 a 5 según la oleada): SINTONÍA, SEÑAL A LA DERIVA (el objetivo se mueve), INTERFERENCIA (el enemigo te desajusta), DOS CANALES (ESPACIO cambia de canal) y BARRIDO DE ESPECTRO (ESPACIO al cruzar la banda). Cada señal bloqueada descifra una palabra de la transmisión enemiga. Recompensa: bonus, suministros, reparaciones, retraso del próximo ataque o botín, y toda la flota enemiga visible 90 s; los radares se reactivan en cada oleada. Si fallás 3 estaciones hay contrahackeo: -8 casco, 40 s de alerta y dos combates navales seguidos contra barcos que no son de la flota del mapa (no podés huir, no dan puntos ni bonus ni munición y no descuentan barcos de la oleada). **Los radares desbloquean las invasiones**: el desembarco a las islas de antena (L) necesita 1 radar interceptado en la oleada y el asalto al puerto enemigo (T) necesita 2 (las islas despejadas por el Blackhawk no lo exigen). El contador RADARES del mapa lo muestra y se reinicia en cada oleada.
- **Invasión anfibia a una ciudad**: ahora se pelea en un **distrito urbano** a escala de los soldados (isla grande con cámara que sigue al jugador): manzanas con torres, edificios bajos, parques con fuente, estacionamientos, muelles de contenedores, calles con autos y barricadas, y el **ayuntamiento** en el centro como objetivo (humo y llamas a medida que pierde vida). Edificios y autos bloquean el paso y las balas; los invasores avanzan por las calles y atacan al llegar al ayuntamiento. Hay minimapa y una flecha que señala el ayuntamiento si queda fuera de pantalla. Cada ciudad tiene su carácter: **Puerto Brondo** es portuaria (muelles de contenedores), **Nueva Esperanza** residencial (edificios bajos cálidos y parques), **Bahía Azul** turística (parques y edificios claros) y **Fort Legacy** militar (edificios grises, autos color oliva y el doble de barricadas); además cada una tiene su propia costa y distribución. Las islas de antena conservan su formato.
- **Convoy** (desde la oleada 2): el carguero zarpa hacia **la ciudad con menos reservas** con 2 corbetas de escolta que disparan a los cazadores y a los aviones. La ruta (punteada en el mapa) tiene emboscadas marcadas en la barra de progreso: cazadores enemigos, **bombarderos** (círculos rojos de impacto; apretá **F**, o A en el joystick, para el fuego antiaéreo de tu barco: destruye bombas y daña aviones, recarga 6 s), **torpedos** desde la oleada 3 (interponé tu barco o una escolta para frenarlos) y una emboscada junto al puerto; desde la oleada 5 hay un segundo ataque aéreo. Tu barco cerca del carguero atrae el fuego (-35 % de daño). La llegada se da por válida apenas el carguero **toca la costa o el muelle de la ciudad** (nunca se mete tierra adentro) y **descarga 1,6 s** (cajas volando al puerto) y las reservas de la ciudad suben hasta 100 de cada recurso según el casco que le quede (si lo hunden a mitad, igual entrega lo descargado), +20 % de ciudad, fuegos artificiales y bonus por escoltas vivas, aviones derribados y viaje sin daños.
- **Incursiones de cazas** (desde la oleada 2, cada 50 a 100 s si no hay ataque, convoy ni rescate en curso): 2 a 4 cazas vienen a bombardear **tu barco** en dos pasadas, con círculos rojos de aviso donde van a caer las bombas (cada impacto resta 5 de casco). Esquivalas moviéndote y derribalos con **F** (antiaéreo, también A en el mando; recarga 6 s; un disparo cerca de ellos los derriba): +150 por caza y +300 si caen todos. Los combates y minijuegos pausan la incursión.
- **Variedad por oleada** (clima y evento propios): 1 aguas calmas; 2 **niebla** (radar a la mitad) y **convoy doble**; 3 **noche** (oscuridad con luces en ciudades, barco y enemigos, reflejos de luna; los enemigos te detectan de más cerca) y el doble de incursiones de cazas; 4 **tormenta** (lluvia, oleaje que arrastra el barco, rayos con aviso: -6 de casco si te caen encima) y 4 baterías costeras más; 5 **niebla nocturna** con una manada de submarinos; 6 **tormenta nocturna**, asalto final con más barcos. El clima se ve en el rótulo del radar y un cartel avisa al empezar cada oleada.
- **Corrientes marinas** (desde la oleada 2, 2 a 4 por oleada): corredores con flechas animadas que empujan el barco (se ven también en el radar).
- **Ciudades con rol**: PUERTO BRONDO da combustible, NUEVA ESPERANZA reparaciones, FORT LEGACY munición y BAHIA AZUL **todo**. Cada ciudad tiene el 100 % de su recurso y el 40 % de los otros dos; el cartel del puerto dice el rol y el convoy elige la ciudad con menos reservas de lo suyo.
- **Puertos**: cada ciudad tiene 100 de combustible, 100 de reparaciones y 100 de munición (tope menor si la ciudad está dañada). Se agotan al reabastecerte y se reponen de tres formas: goteo lento (+1 de cada cosa cada 10 s; la mitad de rápido si hay alerta o ataque, y nada en la ciudad amenazada), +30 de cada cosa cuando un convoy llega a salvo y +40 al completar la oleada. El mapa muestra las reservas bajo cada puerto.
- **Guardar y cargar**: en la pausa (P / ESC) apretá S para guardar en una de las 3 ranuras (solo desde el mapa, no durante una misión) y C para cargar; también se carga desde el título con C. Al terminar cada oleada se hace un **autoguardado** (se carga con A en el menú). Se guarda: puntos, oleada, barco, mejoras, antenas, radares, ciudades, flota enemiga, nidos, islotes movidos y huellas de la guerra. Las partidas quedan en `final_legacy_saves.json`. Mando: en la pausa X guarda, Y carga y Back activa el modo inmortal; en el título Y carga.
- **Modo inmortal** (tecla I en el título, el mapa o la pausa; X en el título con mando): el barco, el soldado, el tanque, el avión, el helicóptero y las ciudades no pierden vida, así que no hay derrota por daño. Se recuerda entre partidas y muestra un cartel `* INMORTAL *` arriba.
- **Dificultad**: en las oleadas altas los enemigos navales disparan menos seguido, con menos precisión y con menos daño por impacto que al principio del desarrollo (los barcos aguantan más tiempo), los jefes sueltan menos cazas y minas, y al terminar cada oleada la tripulación repara +40 de casco y +40 de combustible.
- **Entre oleadas**: elegís 1 de 3 mejoras (daño +20%, recarga, explosivos, casco, misiles guiados, nano-reparación…); al completar las oleadas 3 y 5 elegís dos. El daño y la recarga valen en todos los modos.

## Helicóptero Blackhawk

Una isla del mapa (con una H, también en el radar) tiene un helipuerto con un Blackhawk negro.

- **C** (LT en el mando): el Blackhawk viene volando, se detiene sobre tu barco y baja en paracaídas un barril de combustible (+60%). Espera de 80 s; no sirve con el tanque casi lleno.
- La primera misión llega a los **3000 puntos** y cada una siguiente pide el doble de distancia: +6000, +12000, +24000 y después +24000 por misión (a los 3000, 9000, 21000, 45000, 69000... puntos). Acercate al helipuerto y presioná **B**: elegís entre **despejar una isla de antena**, cazar un buque enemigo o destruir una batería costera.
- Si despejás una isla, al llegar con el barco y presionar **L** instalás la antena **sin combate**.
- Misión aire-tierra (vista cenital): WASD volar, mouse apuntar, clic ametralladora, ESPACIO o clic derecho cohetes. Esquivá los misiles tierra-aire.

## Música

Cada modo tiene su propia música compuesta por código (con numpy): mapa, defensa, combate naval, jefe, aéreo, tierra, tanques, puerto, helicóptero, hackeo, mejoras y portada. Dentro de cada modo la pieza cambia con la oleada (tempo, tonalidad, modo musical, batería y melodía). Mientras se compone suena la música básica. Sin numpy se usan solo las dos pistas básicas.

## Generar el .exe (Windows)

Con PyInstaller se arma una carpeta que se puede pasar a otra persona sin que instale Python. Hay que compilar en Windows.

```
pip install pyinstaller
python -m PyInstaller --noconsole --onedir --name RetroLegacy --collect-all imageio_ffmpeg --add-data "videos;videos" --add-data "fonts;fonts" --add-data "portraits;portraits" --add-data "aviones;aviones" --add-data "icono;icono" --icon icono/retro_legacy.ico retro_legacy.py
```

- **Atajo**: ejecutá `compilar.bat` (doble clic o desde la consola): instala PyInstaller, limpia `build/` y `dist/`, compila con todas las opciones (incluido el ícono) y refresca la caché de íconos de Windows.
- Se llama con `python -m PyInstaller` (y no `pyinstaller` a secas) porque `pip` instala el programa en una carpeta de usuario que muchas veces no está en el PATH ("command not found"); así funciona igual.
- En una consola MSYS2/Git Bash, que traduce los argumentos con `;` como si fueran rutas de Linux, anteponé `MSYS2_ARG_CONV_EXCL="*"` al comando, o ejecutalo desde PowerShell o el CMD de Windows.

- El resultado queda en `dist/RetroLegacy/` (ejecutable: `RetroLegacy.exe`). Para compartirlo, comprimí **toda la carpeta** en un ZIP.
- `--collect-all imageio_ffmpeg` incluye el decodificador de los videos; `--add-data "videos;videos"`, `--add-data "fonts;fonts"` y `--add-data "portraits;portraits"` incluyen los MP4, la fuente Orbitron y los retratos de los personajes (sin esa última opción el `.exe` usa siluetas provisorias). `--icon icono/retro_legacy.ico` le pone el ícono del juego al `.exe` y `--add-data "icono;icono"` lo incluye para la ventana y la barra de tareas. Para regenerar el ícono: `python icono/generar_icono.py`.
- Si el `.exe` sigue mostrando el ícono de Python: (1) verificá que exista la carpeta `icono/` (si no, hacé `git pull origin main`); (2) borrá las carpetas `build/` y `dist/` y el archivo `RetroLegacy.spec` y agregá `--clean` al comando; (3) Windows guarda los íconos en una caché: renombrá el `.exe` o ejecutá `ie4uinit.exe -show` (o reiniciá el Explorador) para que lo recargue.
- Se usa `--onedir` (carpeta) y no `--onefile`, porque abre más rápido y guarda bien las partidas.
- Las partidas (`final_legacy_saves.json`) y el récord (`final_legacy_hiscore.txt`) quedan dentro de `dist/RetroLegacy/_internal/`: copialos antes de recompilar, porque la compilación nueva los reemplaza.
- A veces el antivirus de Windows marca el `.exe` como sospechoso (falso positivo conocido de PyInstaller); hay que permitirlo.

## Gráficos HD

Instalá las dependencias con `pip install -r requirements.txt` (pygame-ce y numpy; numpy es opcional pero da humo, fuego y brillos más suaves). Si ya tenés pygame-ce instalado (el juego anda también con pygame clásico), alcanza con `pip install numpy`; no instales los dos pygame a la vez. Se ejecuta con `python retro_legacy.py`.
La tecla **V** cambia la calidad: BÁSICA, HD (resplandor/bloom, gradación de color y viñeta, por defecto) y ULTRA (más bloom y grano de película). La elección se guarda.

## Menú, fuentes y pantalla completa

- **Menú principal**: NUEVO JUEGO, CARGAR PARTIDA, OPCIONES y SALIR (flechas o W/S, mouse con clic, o mando con cruceta y A). En **OPCIONES**: pantalla completa y modo CRT (sí/no), INSTRUCCIONES (controles de cada modo) y CHEATS (atajos de prueba F2-F12 y N, y el modo inmortal). ESC o clic derecho vuelven atrás.
- **Fuente**: Orbitron (licencia SIL OFL, en `fonts/`). Si falta el archivo se usa una fuente monoespaciada del sistema. Al compilar con PyInstaller agregá `--add-data "fonts;fonts"`.


- El juego **siempre abre en pantalla completa** (F11 o Alt+Enter alternan; `python retro_legacy.py --windowed` o `-w` lo abre en ventana).
- **Videos de presentación**: si hay `videos/logo.mp4` y `videos/intro.mp4`, se reproducen con sonido antes del título (logo, después intro). Se saltan con clic, ESPACIO, ENTER, ESC o un botón del mando. Necesitan `pip install imageio-ffmpeg` (o ffmpeg instalado); si falta algo, el juego arranca sin ellos.
- **Mando Xbox 360 / One** (y compatibles SDL): se detecta solo, también si lo conectás con el juego abierto.
  Palanca izq./cruceta: mover · palanca der.: apuntar · RT o A: disparar · LT, B o RB: granada/bomba ·
  X: recargar/reabastecer · Y: acción · LB: sigilo (mapa: desembarcar) · RB en el mapa: hackear · Start: pausa/empezar · Back: sonido.
  En mejoras: X/A/B eligen la 1.ª/2.ª/3.ª; en hackeo: cruceta + A girar, X al revés, B abortar.

## Atajos de prueba en el mapa

F2 tanques · F3 aéreo · F4 desembarco · F5 náufragos · F6 convoy · F7 asalto al puerto · F8 defensa de misiles
F9 subir una oleada (hasta la 6, que es la última) · F10 +3000 puntos (gana una misión del Blackhawk) · F12 reabastecer casco, combustible, munición y ciudades

El juego tiene 6 oleadas: al completar la 6.ª ganás. Con F9 subís de oleada y después F2-F8 muestran cada modo con la dificultad de esa oleada.
