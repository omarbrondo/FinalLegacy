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
from .hazards import HazardMixin
from .tk_props import TankPropsMixin
from .war import WarMixin
from .naval_fx import NavalFxMixin
from .naval_arms import NavalArmsMixin
from .naval_fleet import NavalFleetMixin
from .landing import LandingMixin
from .landing_ops import LandingOpsMixin
from .port_epic import PortEpicMixin
from .radio_mode import RadioMixin


class Game(CoreMixin, MapMixin, DefenseMixin, HackMixin, NavalMixin, AerialMixin, AirBossMixin, GroundMixin, PortMixin, TankMixin, UpgradeMixin, GamepadMixin, HeliMixin, HazardMixin, TankPropsMixin, WarMixin, NavalFxMixin, NavalArmsMixin, NavalFleetMixin, LandingMixin, LandingOpsMixin, PortEpicMixin, RadioMixin):
    """Juego completo. El estado vive en 'self'; cada mixin aporta los métodos de un modo."""


def main():
    g = Game()
    if '--fullscreen' in sys.argv or '-f' in sys.argv or os.environ.get('FL_FULLSCREEN'):
        g.toggle_fullscreen()
    g.run()
