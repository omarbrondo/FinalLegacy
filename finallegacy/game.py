"""Clase Game: une el núcleo con los modos de juego (cada uno en su archivo) y define main()."""
import os
import sys
from .core import CoreMixin
from .map_mode import MapMixin
from .defense_mode import DefenseMixin
from .hack_mode import HackMixin
from .naval_mode import NavalMixin
from .aerial_mode import AerialMixin
from .air_boss import AirBossMixin
from .ground_mode import GroundMixin
from .port_mode import PortMixin
from .tank_mode import TankMixin
from .upgrade_mode import UpgradeMixin
from .gamepad import GamepadMixin
from .heli_mode import HeliMixin


class Game(CoreMixin, MapMixin, DefenseMixin, HackMixin, NavalMixin, AerialMixin, AirBossMixin, GroundMixin, PortMixin, TankMixin, UpgradeMixin, GamepadMixin, HeliMixin):
    """Juego completo. El estado vive en 'self'; cada mixin aporta los métodos de un modo."""


def main():
    g = Game()
    if '--fullscreen' in sys.argv or '-f' in sys.argv or os.environ.get('FL_FULLSCREEN'):
        g.toggle_fullscreen()
    g.run()
