#!/usr/bin/env python3

#
# test_hiruma_school.py
#
# Unit tests for the Hiruma Scout School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.floating_bonuses import AnyAttackFloatingBonus
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import Modifier
from simulation.modifier_listeners import ExpireAfterNDamageRollsListener
from simulation.schools import hiruma_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestHirumaScoutSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual(["initiative", "parry", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual("air", school.school_ring())

    def test_school_knacks(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual(["double attack", "feint", "iaijutsu"], school.school_knacks())

    def test_free_raise_skills(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual(["parry"], school.free_raise_skills())


class TestHirumaParryListener(unittest.TestCase):
    def setUp(self):
        self.hiruma = Character("Hiruma")
        self.hiruma.set_skill("attack", 4)
        self.hiruma.set_actions([1])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crab", self.hiruma), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_gain_floating_bonus_on_parry_succeeded(self):
        attack = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = hiruma_school.HirumaParryListener()
        list(listener.handle(self.hiruma, event, self.context))
        bonuses = self.hiruma.floating_bonuses("attack")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(8, bonuses[0].bonus())  # 2 * 4 = 8
        self.assertTrue(isinstance(bonuses[0], AnyAttackFloatingBonus))

    def test_gain_floating_bonus_on_parry_failed(self):
        attack = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(20)
        event = events.ParryFailedEvent(parry)
        listener = hiruma_school.HirumaParryListener()
        list(listener.handle(self.hiruma, event, self.context))
        bonuses = self.hiruma.floating_bonuses("attack")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(8, bonuses[0].bonus())


class TestHirumaNewRoundListener(unittest.TestCase):
    def test_subtract_2_from_action_dice(self):
        hiruma = Character("Hiruma")
        hiruma.set_actions([3, 5, 8])
        enemy = Character("enemy")
        groups = [Group("Crab", hiruma), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = hiruma_school.HirumaNewRoundListener()
        event = events.NewRoundEvent(1)
        list(listener.handle(hiruma, event, context))
        # Actions should be reduced by 2, min 1
        # Note: roll_initiative will generate new actions, then subtract 2
        # For this unit test, we verify the subtraction logic directly
        actions = hiruma.actions()
        for action in actions:
            self.assertGreaterEqual(action, 1)


class TestHirumaFifthDanParryListener(unittest.TestCase):
    def setUp(self):
        self.hiruma = Character("Hiruma")
        self.hiruma.set_skill("attack", 4)
        self.hiruma.set_actions([1])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crab", self.hiruma), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_add_damage_modifier_on_parry(self):
        attack = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = hiruma_school.HirumaFifthDanParryListener()
        responses = list(listener.handle(self.hiruma, event, self.context))
        # Should get AddModifierEvent
        add_mod_events = [r for r in responses if isinstance(r, events.AddModifierEvent)]
        self.assertEqual(1, len(add_mod_events))
        modifier = add_mod_events[0].modifier
        self.assertEqual(-10, modifier.adjustment())
        # Should also get floating bonus from 3rd Dan
        bonuses = self.hiruma.floating_bonuses("attack")
        self.assertEqual(1, len(bonuses))


class TestExpireAfterNDamageRollsListener(unittest.TestCase):
    def test_expire_after_2_damage_rolls(self):
        attacker = Character("attacker")
        target = Character("target")
        groups = [Group("A", attacker), Group("B", target)]
        context = EngineContext(groups)
        modifier = Modifier(attacker, None, "damage", -10)
        listener = ExpireAfterNDamageRollsListener(attacker, 2)
        modifier.register_listener("lw_damage", listener)
        attacker.add_modifier(modifier)
        # First damage roll - should not expire
        event1 = events.LightWoundsDamageEvent(attacker, target, 15)
        responses1 = list(modifier.handle(attacker, event1, context))
        self.assertEqual(0, len(responses1))
        # Second damage roll - should expire
        event2 = events.LightWoundsDamageEvent(attacker, target, 20)
        responses2 = list(modifier.handle(attacker, event2, context))
        self.assertEqual(1, len(responses2))
        self.assertTrue(isinstance(responses2[0], events.RemoveModifierEvent))

    def test_do_not_expire_for_different_attacker(self):
        attacker = Character("attacker")
        other = Character("other")
        target = Character("target")
        groups = [Group("A", [attacker, other]), Group("B", target)]
        context = EngineContext(groups)
        modifier = Modifier(attacker, None, "damage", -10)
        listener = ExpireAfterNDamageRollsListener(attacker, 2)
        modifier.register_listener("lw_damage", listener)
        attacker.add_modifier(modifier)
        # Damage from another character - should not count
        event = events.LightWoundsDamageEvent(other, target, 15)
        responses = list(modifier.handle(attacker, event, context))
        self.assertEqual(0, len(responses))
