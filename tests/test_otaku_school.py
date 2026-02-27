#!/usr/bin/env python3

#
# test_otaku_school.py
#
# Unit tests for the Otaku Bushi School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools import otaku_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestOtakuBushiSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual(["iaijutsu", "lunge", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual("fire", school.school_ring())

    def test_school_knacks(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual(["double attack", "iaijutsu", "lunge"], school.school_knacks())

    def test_free_raise_skills(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual(["wound check"], school.free_raise_skills())


class TestOtakuSpecialAbility(unittest.TestCase):
    def test_interrupt_lunge_cost(self):
        otaku = Character("Otaku")
        school = otaku_school.OtakuBushiSchool()
        school.apply_special_ability(otaku)
        self.assertEqual(1, otaku.interrupt_cost("lunge", None))


class TestOtakuLightWoundsDamageListener(unittest.TestCase):
    def setUp(self):
        self.otaku = Character("Otaku")
        self.otaku.set_skill("attack", 4)
        self.target = Character("target")
        self.target.set_ring("fire", 3)
        self.target.set_actions([3, 6, 9])
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)

    def test_increase_target_action_dice(self):
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.otaku, self.target, 15)
        list(listener.handle(self.otaku, event, self.context))
        # increase = max(1, 6 - 3) = 3
        # target's actions: [3+3, 6+3, 9+3] = [6, 9, 10] (capped at 10)
        self.assertEqual([6, 9, 10], self.target.actions())

    def test_increase_min_1(self):
        self.target.set_ring("fire", 6)
        self.target.set_actions([5, 7])
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.otaku, self.target, 15)
        list(listener.handle(self.otaku, event, self.context))
        # increase = max(1, 6 - 6) = 1
        self.assertEqual([6, 8], self.target.actions())


class TestOtakuLungeAction(unittest.TestCase):
    def setUp(self):
        self.otaku = Character("Otaku")
        self.otaku.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_extra_damage_die_when_parried(self):
        action = otaku_school.OtakuLungeAction(
            self.otaku, self.target, "lunge", self.initiative_action, self.context,
        )
        action.set_skill_roll(30)
        action.set_parry_attempted()
        # Even when parried, Otaku gets +1 extra damage die
        self.assertEqual(1, action.calculate_extra_damage_dice())

    def test_normal_extra_damage_dice(self):
        action = otaku_school.OtakuLungeAction(
            self.otaku, self.target, "lunge", self.initiative_action, self.context,
        )
        action.set_skill_roll(35)
        # TN = 20 (parry 3 -> 5*(1+3)=20)
        # Normal: (35-20)//5 + 1 = 3 + 1 = 4
        self.assertEqual(4, action.calculate_extra_damage_dice())


class TestOtakuActionFactory(unittest.TestCase):
    def setUp(self):
        self.otaku = Character("Otaku")
        self.otaku.set_actions([1])
        self.target = Character("target")
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_get_lunge_action(self):
        factory = otaku_school.OtakuActionFactory()
        action = factory.get_attack_action(self.otaku, self.target, "lunge", self.initiative_action, self.context)
        self.assertTrue(isinstance(action, otaku_school.OtakuLungeAction))

    def test_get_attack_action_default(self):
        factory = otaku_school.OtakuActionFactory()
        action = factory.get_attack_action(self.otaku, self.target, "attack", self.initiative_action, self.context)
        # Should be default AttackAction, not OtakuLungeAction
        self.assertFalse(isinstance(action, otaku_school.OtakuLungeAction))
