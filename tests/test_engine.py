
import logging
import sys
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.exceptions import CombatEnded
from simulation.groups import Group
from simulation.log import logger


# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestCombatEngine(unittest.TestCase):
  def test_combat(self):
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    context = EngineContext([Group('Lion', akodo), Group('Scorpion', bayushi)])
    context.initialize()
    engine = CombatEngine(context)
    engine.run()

