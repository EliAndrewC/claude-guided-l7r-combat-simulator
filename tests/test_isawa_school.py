#!/usr/bin/env python3

#
# test_isawa_school.py
#
# Unit tests for the Isawa Duelist School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools import isawa_school
from simulation.strategies.base import AlwaysKeepLightWoundsStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIsawaDuelistSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = isawa_school.IsawaDuelistSchool()
        self.assertEqual(["double attack", "lunge", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = isawa_school.IsawaDuelistSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = isawa_school.IsawaDuelistSchool()
        self.assertEqual(["double attack", "iaijutsu", "lunge"], school.school_knacks())

    def test_free_raise_skills(self):
        school = isawa_school.IsawaDuelistSchool()
        self.assertEqual(["wound check"], school.free_raise_skills())


class TestIsawaSpecialAbility(unittest.TestCase):
    def test_water_for_damage(self):
        isawa = Character("Isawa")
        school = isawa_school.IsawaDuelistSchool()
        school.apply_special_ability(isawa)
        # Should use water ring for damage
        self.assertEqual("water", isawa.get_skill_ring("damage"))


class TestIsawaRollParameterProvider(unittest.TestCase):
    def test_uses_water_for_damage(self):
        isawa = Character("Isawa")
        isawa.set_ring("water", 4)
        isawa.set_ring("fire", 2)
        target = Character("target")
        provider = isawa_school.IsawaRollParameterProvider()
        (rolled, kept, mod) = provider.get_damage_roll_params(isawa, target, "attack", 0)
        # Should use water (4) not fire (2) for rolled
        # rolled = water(4) + extra_rolled(0) + attack_extra(0) + weapon.rolled(4) = 8
        self.assertEqual(8, rolled)


class TestIsawaAttackAction(unittest.TestCase):
    def setUp(self):
        self.isawa = Character("Isawa")
        self.isawa.set_skill("attack", 4)
        self.isawa.set_ring("fire", 3)
        self.isawa.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Phoenix", self.isawa), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_attack_bonus(self):
        action = isawa_school.IsawaAttackAction(
            self.isawa, self.target, "attack", self.initiative_action, self.context,
        )
        (rolled, kept, modifier) = action.skill_roll_params()
        # bonus = 3 * attack_skill(4) = 12
        # normal modifier = 0
        self.assertEqual(12, modifier)


class TestIsawaWoundCheckSucceededListener(unittest.TestCase):
    def setUp(self):
        self.isawa = Character("Isawa")
        self.isawa.set_strategy("light_wounds", AlwaysKeepLightWoundsStrategy())
        self.attacker = Character("attacker")
        groups = [Group("Phoenix", self.isawa), Group("Attacker", self.attacker)]
        self.context = EngineContext(groups)

    def test_gain_wound_check_bonus(self):
        self.isawa._lw = 20
        listener = isawa_school.IsawaWoundCheckSucceededListener()
        # roll=30, damage=20, so bonus = 30-20 = 10
        event = events.WoundCheckSucceededEvent(self.isawa, self.attacker, 20, 30)
        list(listener.handle(self.isawa, event, self.context))
        bonuses = self.isawa.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(10, bonuses[0].bonus())
        self.assertTrue(isinstance(bonuses[0], WoundCheckFloatingBonus))

    def test_no_bonus_when_roll_equals_damage(self):
        listener = isawa_school.IsawaWoundCheckSucceededListener()
        event = events.WoundCheckSucceededEvent(self.isawa, self.attacker, 20, 20)
        list(listener.handle(self.isawa, event, self.context))
        bonuses = self.isawa.floating_bonuses("wound check")
        self.assertEqual(0, len(bonuses))


class TestIsawaActionFactory(unittest.TestCase):
    def setUp(self):
        self.isawa = Character("Isawa")
        self.isawa.set_actions([1])
        self.target = Character("target")
        groups = [Group("Phoenix", self.isawa), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_get_attack_action(self):
        factory = isawa_school.IsawaActionFactory()
        action = factory.get_attack_action(self.isawa, self.target, "attack", self.initiative_action, self.context)
        self.assertTrue(isinstance(action, isawa_school.IsawaAttackAction))

    def test_get_double_attack_action(self):
        factory = isawa_school.IsawaActionFactory()
        action = factory.get_attack_action(self.isawa, self.target, "double attack", self.initiative_action, self.context)
        self.assertTrue(isinstance(action, isawa_school.IsawaDoubleAttackAction))

    def test_get_lunge_action(self):
        factory = isawa_school.IsawaActionFactory()
        action = factory.get_attack_action(self.isawa, self.target, "lunge", self.initiative_action, self.context)
        self.assertTrue(isinstance(action, isawa_school.IsawaLungeAction))
