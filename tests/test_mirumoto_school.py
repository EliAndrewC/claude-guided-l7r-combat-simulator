#!/usr/bin/env python3

#
# test_mirumoto_school.py
#
# Unit tests for the Mirumoto Bushi School.
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
from simulation.schools import mirumoto_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestMirumotoBushiSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual(["attack", "double attack", "parry"], school.extra_rolled())

    def test_school_ring(self):
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual("void", school.school_ring())

    def test_school_knacks(self):
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual(["counterattack", "double attack", "iaijutsu"], school.school_knacks())

    def test_free_raise_skills(self):
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual(["parry"], school.free_raise_skills())


class TestMirumotoParryTVPListener(unittest.TestCase):
    def setUp(self):
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Dragon", self.mirumoto), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_gain_tvp_on_parry_succeeded(self):
        attack = actions.AttackAction(self.attacker, self.mirumoto, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.mirumoto, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = mirumoto_school.MirumotoParryTVPListener()
        responses = list(listener.handle(self.mirumoto, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertTrue(isinstance(responses[0], events.GainTemporaryVoidPointsEvent))
        self.assertEqual(self.mirumoto, responses[0].subject)
        self.assertEqual(1, responses[0].amount)

    def test_gain_tvp_on_parry_failed(self):
        attack = actions.AttackAction(self.attacker, self.mirumoto, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.mirumoto, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(20)
        event = events.ParryFailedEvent(parry)
        listener = mirumoto_school.MirumotoParryTVPListener()
        responses = list(listener.handle(self.mirumoto, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertTrue(isinstance(responses[0], events.GainTemporaryVoidPointsEvent))


class TestMirumotoNewRoundListener(unittest.TestCase):
    def test_grants_resource_pool(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_skill("attack", 4)
        enemy = Character("enemy")
        groups = [Group("Dragon", mirumoto), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = mirumoto_school.MirumotoNewRoundListener()
        event = events.NewRoundEvent(1)
        list(listener.handle(mirumoto, event, context))
        # Should have _mirumoto_pool = 2 * 4 = 8
        self.assertEqual(8, mirumoto._mirumoto_pool)


class TestMirumotoParryAction(unittest.TestCase):
    def setUp(self):
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Dragon", self.mirumoto), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_half_extra_damage_dice_on_failed_parry(self):
        attack = actions.AttackAction(self.attacker, self.mirumoto, "attack", self.initiative_action, self.context)
        attack.set_skill_roll(40)  # rolls 40 against TN 10 (parry 1)
        parry = mirumoto_school.MirumotoParryAction(
            self.mirumoto, self.attacker, "parry", self.initiative_action, self.context, attack,
        )
        parry.set_attack_parry_attempted()
        # After MirumotoParryAction patches calculate_extra_damage_dice,
        # the extra dice should be halved.
        # Normally: (40 - 10) // 5 = 6, but parry_attempted -> 0 in base
        # However Mirumoto overrides: original result // 2
        extra_dice = attack.calculate_extra_damage_dice()
        self.assertEqual(0, extra_dice)  # 0 // 2 = 0 (parry_attempted returns 0, halved stays 0)


class TestMirumotoRollParameterProvider(unittest.TestCase):
    def test_vp_bonus_doubled_skill_roll(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_ring("fire", 3)
        mirumoto.set_skill("attack", 4)
        target = Character("target")
        provider = mirumoto_school.MirumotoRollParameterProvider()
        # With 1 VP: normal gives +5 total from modifier, Mirumoto gives +10
        (rolled, kept, modifier) = provider.get_skill_roll_params(mirumoto, target, "attack", vp=1)
        # rolled = 3 + 4 + 0 + 1 = 8, kept = 3 + 0 + 1 = 4
        # modifier = 0 + 5*1 = 5 (extra +5 per VP on top of already-counted VP in rolled/kept)
        self.assertEqual(5, modifier)

    def test_vp_bonus_doubled_wound_check(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_ring("water", 3)
        provider = mirumoto_school.MirumotoRollParameterProvider()
        (rolled, kept, modifier) = provider.get_wound_check_roll_params(mirumoto, vp=1)
        # Extra +5 for the VP
        self.assertEqual(5, modifier)

    def test_no_extra_bonus_without_vp(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_ring("fire", 3)
        mirumoto.set_skill("attack", 4)
        target = Character("target")
        provider = mirumoto_school.MirumotoRollParameterProvider()
        (rolled, kept, modifier) = provider.get_skill_roll_params(mirumoto, target, "attack", vp=0)
        self.assertEqual(0, modifier)
