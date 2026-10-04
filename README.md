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
| `game.py` | Clase `Game` (une los modos) y `main()` |

Cada modo es un *mixin*: una clase con los métodos de ese modo que `Game` hereda, de modo que todos comparten el mismo estado (`self`).

## Atajos de prueba en el mapa

F2 tanques · F3 aéreo · F4 desembarco · F5 náufragos · F6 convoy · F7 asalto al puerto
