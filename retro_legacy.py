#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RETRO LEGACY  -  Edición Omar Brondo  (antes FINAL LEGACY)
Requisitos:  pip install -r requirements.txt      Ejecutar:  python retro_legacy.py

Todo (gráficos y sonido) se genera por código: no necesita archivos externos.
El código está dividido en el paquete 'finallegacy/' (un módulo por modo de juego).
Este archivo es el punto de entrada y reexporta los nombres públicos del paquete.
"""
from finallegacy.common import *       # noqa: F401,F403  (constantes y utilidades)
from finallegacy.audio import *        # noqa: F401,F403
from finallegacy.sprites import *      # noqa: F401,F403
from finallegacy.tk_art import *       # noqa: F401,F403
from finallegacy.pt_art import *       # noqa: F401,F403
from finallegacy.boss_art import *     # noqa: F401,F403
from finallegacy.air_boss import AIR_BOSSES   # noqa: F401
from finallegacy.game import Game, main

if __name__ == '__main__':
    main()
