# FINAL LEGACY - Edición Omar Brondo

Juego de guerra naval y de infantería hecho con **Python + pygame**. Todo el arte y el sonido se generan por código, así que no necesita archivos externos.

## Ejecutar

```
pip install pygame
python final_legacy_omar.py
```

## Estructura del código

`final_legacy_omar.py` es solo el punto de entrada. El juego vive en el paquete `finallegacy/`:

| Archivo | Contenido |
| --- | --- |
| `common.py` | Constantes, utilidades matemáticas, helpers de dibujo y partículas |
| `audio.py` | Síntesis de sonido y música |
| `sprites.py` | Naves, soldados cenitales, cazas, nubes, coberturas |
| `boss_art.py` | Los 6 jefes navales (siluetas y habilidades de cada uno) |
| `tk_art.py` | Texturas y modelo 3D del tanque (combate urbano) |
| `pt_art.py` | Arte del asalto lateral (soldados, tanque, fondo) |
| `core.py` | Recursos, UI común, partida, eventos y bucle principal |
| `map_mode.py` | Mapa: navegación, olas, ataques a ciudades, convoy, náufragos |
| `defense_mode.py` | Defensa de la ciudad contra misiles |
| `hack_mode.py` | Ciberataque al escudo del jefe |
| `naval_mode.py` | Combate naval (destructores, submarinos, baterías, acorazado) |
| `aerial_mode.py` | Batalla aérea estilo Twinbee |
| `ground_mode.py` | Infantería cenital: invasión, desembarco con sigilo, defensa de antenas |
| `port_mode.py` | Asalto al puerto enemigo (estilo Metal Slug) |
| `tank_mode.py` | Combate urbano con tanques en primera persona (estilo Battlezone) |
| `upgrade_mode.py` | Pantalla de mejoras entre oleadas (elegir 1 de 3) |
| `heli_mode.py` | Helipuerto, Blackhawk (bidón de combustible) y misiones aire-tierra |
| `gamepad.py` | Mando Xbox y pantalla completa |
| `game.py` | Clase `Game` (une los modos) y `main()` |

Cada modo es un *mixin*: una clase con los métodos de ese modo que `Game` hereda, de modo que todos comparten el mismo estado (`self`).

## Progresión por oleada

Cada modo suma contenido nuevo a medida que avanzan las oleadas:

- **Aéreo**: un jefe distinto por oleada, cápsulas de ráfaga/misiles guiados, kamikazes, minas, helicópteros y clima.
- **Defensa**: misiles rápidos, evasivos, señuelos, MIRV, misil nuclear jefe; ráfaga doble y escudo por combos; cielos distintos.
- **Tanques**: kamikazes, artillería pesada, helicópteros, tanque jefe, niebla y noche.
- **Infantería**: perros y francotiradores (láser de mira).
- **Puerto**: jefe tanque u helicóptero según la oleada; noche y tormenta.
- **Hackeo**: virus que corrompen nodos, cortafuegos y segunda fuente.
- **Entre oleadas**: elegís 1 de 3 mejoras (casco, recarga, misiles guiados, nano-reparación…).

## Helicóptero Blackhawk

Una isla del mapa (con una H, también en el radar) tiene un helipuerto con un Blackhawk negro.

- **C** (LT en el mando): el Blackhawk viene volando, se detiene sobre tu barco y baja en paracaídas un barril de combustible (+60%). Espera de 80 s; no sirve con el tanque casi lleno.
- Cada **3000 puntos** (y cada vez más) ganás una misión. Acercate al helipuerto y presioná **B**: elegís entre **despejar una isla de antena**, cazar un buque enemigo o destruir una batería costera.
- Si despejás una isla, al llegar con el barco y presionar **L** instalás la antena **sin combate**.
- Misión aire-tierra (vista cenital): WASD volar, mouse apuntar, clic ametralladora, ESPACIO o clic derecho cohetes. Esquivá los misiles tierra-aire.

## Pantalla completa y mando

- **F11** o **Alt+Enter**: pantalla completa (se escala conservando la proporción). También `python final_legacy_omar.py --fullscreen`.
- **Mando Xbox 360 / One** (y compatibles SDL): se detecta solo, también si lo conectás con el juego abierto.
  Palanca izq./cruceta: mover · palanca der.: apuntar · RT o A: disparar · LT, B o RB: granada/bomba ·
  X: recargar/reabastecer · Y: acción · LB: sigilo (mapa: desembarcar) · RB en el mapa: hackear · Start: pausa/empezar · Back: sonido.
  En mejoras: X/A/B eligen la 1.ª/2.ª/3.ª; en hackeo: cruceta + A girar, X al revés, B abortar.

## Atajos de prueba en el mapa

F2 tanques · F3 aéreo · F4 desembarco · F5 náufragos · F6 convoy · F7 asalto al puerto
