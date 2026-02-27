#!/usr/bin/env python3

#
# test_ishi_school.py
#
# Unit tests for the Isawa Ishi School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import TestRollProvider
from simulation.schools import ishi_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIshiSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual("Isawa Ishi School", school.name())

    def test_extra_rolled(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual(["precepts", "wound check", "initiative"], school.extra_rolled())

    def test_school_ring(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual("void", school.school_ring())

    def test_school_knacks(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual(["absorb void", "kharmic spin", "otherworldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual(["attack"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertIsNone(school.ap_base_skill())


class TestIshiMaxVPProvider(unittest.TestCase):
    def test_max_vp_uses_highest_ring_plus_school_rank(self):
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        provider = ishi_school.IshiMaxVPProvider(school_rank=2)
        # highest ring = 4 (void), school rank = 2 -> 6
        self.assertEqual(6, provider.max_vp(ishi))

    def test_max_vp_per_roll_uses_lowest_ring_minus_1(self):
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        provider = ishi_school.IshiMaxVPProvider()
        # lowest ring = 2, minus 1 -> 1
        self.assertEqual(1, provider.max_vp_per_roll(ishi))

    def test_max_vp_per_roll_never_negative(self):
        ishi = Character("Ishi")
        # All rings default to 2, so min is 2
        provider = ishi_school.IshiMaxVPProvider()
        # lowest ring = 2, minus 1 -> 1
        self.assertEqual(1, provider.max_vp_per_roll(ishi))

    def test_special_ability_sets_provider(self):
        ishi = Character("Ishi")
        ishi.set_ring("void", 4)
        school = ishi_school.IsawaIshiSchool()
        school.apply_special_ability(ishi)
        # Max VP should use Ishi formula
        # highest ring = 4 (void), school rank = 1 -> 5
        self.assertEqual(5, ishi.max_vp())
        # Max VP per roll = lowest ring - 1 = 2 - 1 = 1
        self.assertEqual(1, ishi.max_vp_per_roll())

    def test_vp_calculation_differs_from_standard(self):
        """Verify Ishi VP is different from standard calculation."""
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        # Standard: min(rings) + worldliness = 2 + 0 = 2
        self.assertEqual(2, ishi.max_vp())
        # Now apply Ishi special
        school = ishi_school.IsawaIshiSchool()
        school.apply_special_ability(ishi)
        # Ishi: max(rings) + school_rank = 4 + 1 = 5
        self.assertEqual(5, ishi.max_vp())


class TestIshiAllyBoostListener(unittest.TestCase):
    def setUp(self):
        self.ishi = Character("Ishi")
        self.ishi.set_skill("precepts", 3)
        self.ishi.set_actions([1])
        self.ally = Character("Ally")
        self.ally.set_actions([1])
        self.enemy = Character("Enemy")
        self.enemy.set_actions([1])
        groups = [Group("Phoenix", [self.ishi, self.ally]), Group("Enemy", self.enemy)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_boost_ally_attack(self):
        roll_provider = TestRollProvider()
        roll_provider.put_skill_roll("precepts", 8)
        self.ishi.set_roll_provider(roll_provider)
        action = actions.AttackAction(self.ally, self.enemy, "attack", self.initiative_action, self.context)
        action.set_skill_roll(25)
        event = events.AttackRolledEvent(action, 25)
        listener = ishi_school.IshiAllyBoostListener()
        responses = list(listener.handle(self.ishi, event, self.context))
        # Should spend VP then yield new AttackRolledEvent
        self.assertEqual(2, len(responses))
        self.assertIsInstance(responses[0], events.SpendVoidPointsEvent)
        self.assertEqual(1, responses[0].amount)
        self.assertIsInstance(responses[1], events.AttackRolledEvent)
        self.assertEqual(33, responses[1].roll)  # 25 + 8 = 33

    def test_no_boost_for_enemies(self):
        action = actions.AttackAction(self.enemy, self.ally, "attack", self.initiative_action, self.context)
        action.set_skill_roll(25)
        event = events.AttackRolledEvent(action, 25)
        listener = ishi_school.IshiAllyBoostListener()
        responses = list(listener.handle(self.ishi, event, self.context))
        # Enemy attack - Ishi should observe, not boost
        for response in responses:
            self.assertNotIsInstance(response, events.SpendVoidPointsEvent)

    def test_no_boost_for_self(self):
        action = actions.AttackAction(self.ishi, self.enemy, "attack", self.initiative_action, self.context)
        action.set_skill_roll(25)
        event = events.AttackRolledEvent(action, 25)
        listener = ishi_school.IshiAllyBoostListener()
        responses = list(listener.handle(self.ishi, event, self.context))
        self.assertEqual(0, len(responses))

    def test_no_boost_when_no_vp(self):
        self.ishi.spend_vp(self.ishi.vp())
        action = actions.AttackAction(self.ally, self.enemy, "attack", self.initiative_action, self.context)
        action.set_skill_roll(25)
        event = events.AttackRolledEvent(action, 25)
        listener = ishi_school.IshiAllyBoostListener()
        responses = list(listener.handle(self.ishi, event, self.context))
        self.assertEqual(0, len(responses))


class TestIshiFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        ishi = Character("Ishi")
        ishi.set_ring("void", 3)
        school = ishi_school.IsawaIshiSchool()
        school.apply_rank_four_ability(ishi)
        self.assertEqual(4, ishi.ring("void"))
