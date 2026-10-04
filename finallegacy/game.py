"""Clase Game: une el núcleo con los modos de juego (cada uno en su archivo) y define main()."""
from .core import CoreMixin
from .map_mode import MapMixin
from .defense_mode import DefenseMixin
from .hack_mode import HackMixin
from .naval_mode import NavalMixin
from .aerial_mode import AerialMixin
from .ground_mode import GroundMixin
from .port_mode import PortMixin
from .tank_mode import TankMixin


class Game(CoreMixin, MapMixin, DefenseMixin, HackMixin, NavalMixin, AerialMixin, GroundMixin, PortMixin, TankMixin):
    """Juego completo. El estado vive en 'self'; cada mixin aporta los métodos de un modo."""


def main():
    Game().run()
