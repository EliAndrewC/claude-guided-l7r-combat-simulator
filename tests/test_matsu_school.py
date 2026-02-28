#!/usr/bin/env python3

#
# test_matsu_school.py
#
# Unit tests for the Matsu Bushi School.
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
from simulation.schools import matsu_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestMatsuBushiSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual(["double attack", "iaijutsu", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual("fire", school.school_ring())

    def test_school_knacks(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual(["double attack", "iaijutsu", "lunge"], school.school_knacks())

    def test_free_raise_skills(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual(["iaijutsu"], school.free_raise_skills())


class TestMatsuRollProvider(unittest.TestCase):
    def test_initiative_always_10_dice(self):
        provider = matsu_school.MatsuRollProvider()
        # Even with rolled=3, should use 10
        result = provider.get_initiative_roll(3, 2)
        # Result is a list of action dice
        self.assertTrue(isinstance(result, list))


class TestMatsuSpendVoidPointsListener(unittest.TestCase):
    def setUp(self):
        self.matsu = Character("Matsu")
        self.matsu.set_skill("attack", 4)
        self.matsu.gain_tvp(5)
        self.enemy = Character("enemy")
        groups = [Group("Lion", self.matsu), Group("Enemy", self.enemy)]
        self.context = EngineContext(groups)

    def test_gain_wound_check_bonus_on_vp_spend(self):
        listener = matsu_school.MatsuSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        list(listener.handle(self.matsu, event, self.context))
        # Should gain WoundCheckFloatingBonus(3 * 4 = 12)
        bonuses = self.matsu.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(12, bonuses[0].bonus())
        self.assertTrue(isinstance(bonuses[0], WoundCheckFloatingBonus))


class TestMatsuDoubleAttackAction(unittest.TestCase):
    def setUp(self):
        self.matsu = Character("Matsu")
        self.matsu.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Lion", self.matsu), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_near_miss_is_hit(self):
        # TN = target TN + 20 = 20 + 20 = 40
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # Below TN of 40 but within 20
        self.assertTrue(action.is_hit())

    def test_near_miss_zero_extra_dice(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # Below TN of 40
        self.assertEqual(0, action.calculate_extra_damage_dice())

    def test_near_miss_no_direct_damage(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # Below TN of 40
        self.assertIsNone(action.direct_damage())

    def test_normal_hit_has_direct_damage(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(45)  # Above TN of 40
        self.assertIsNotNone(action.direct_damage())

    def test_miss_not_hit(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(19)  # Below TN-20 of 20
        self.assertFalse(action.is_hit())


class TestMatsuWoundCheckFailedListener(unittest.TestCase):
    def setUp(self):
        self.matsu = Character("Matsu")
        self.defender = Character("defender")
        self.defender._lw = 20
        groups = [Group("Lion", self.matsu), Group("Enemy", self.defender)]
        self.context = EngineContext(groups)

    def test_set_defender_lw_to_15(self):
        listener = matsu_school.MatsuWoundCheckFailedListener()
        event = events.WoundCheckFailedEvent(self.defender, self.matsu, 20, 10)
        responses = list(listener.handle(self.matsu, event, self.context))
        # Should have a SeriousWoundsDamageEvent
        self.assertTrue(len(responses) >= 1)
        sw_event = responses[0]
        self.assertTrue(isinstance(sw_event, events.SeriousWoundsDamageEvent))
        # Defender's LW should be set to 15
        self.assertEqual(15, self.defender.lw())

    def test_matsu_own_wound_check_failure_standard_behavior(self):
        """When Matsu is the defender, standard wound check failure applies."""
        attacker = Character("attacker")
        self.matsu._lw = 20
        groups = [Group("Lion", self.matsu), Group("Enemy", attacker)]
        context = EngineContext(groups)
        listener = matsu_school.MatsuWoundCheckFailedListener()
        event = events.WoundCheckFailedEvent(self.matsu, attacker, 20, 10)
        responses = list(listener.handle(self.matsu, event, context))
        # Should yield SeriousWoundsDamageEvent with standard behavior
        self.assertEqual(1, len(responses))
        sw_event = responses[0]
        self.assertTrue(isinstance(sw_event, events.SeriousWoundsDamageEvent))
        # LW should be reset to 0 (standard), not 15
        self.assertEqual(0, self.matsu.lw())


class TestMatsuDoubleAttackParried(unittest.TestCase):
    def setUp(self):
        self.matsu = Character("Matsu")
        self.matsu.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Lion", self.matsu), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_parried_not_hit(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)
        # Simulate successful parry
        action.set_parried()
        self.assertFalse(action.is_hit())

    def test_parry_attempted_no_direct_damage(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(45)  # Above TN
        action.set_parry_attempted()
        self.assertIsNone(action.direct_damage())

    def test_normal_hit_extra_dice(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        tn = action.tn()
        action.set_skill_roll(tn + 10)  # Exceed TN by 10
        # Normal hit: extra dice = (roll - tn) // 5 = 10 // 5 = 2
        self.assertEqual(2, action.calculate_extra_damage_dice())
