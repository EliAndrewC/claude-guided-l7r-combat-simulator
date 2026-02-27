#!/usr/bin/env python3

#
# test_kuni_school.py
#
# Unit tests for the Kuni Witch Hunter School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.schools import kuni_school
from simulation.strategies.base import AlwaysKeepLightWoundsStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestKuniWitchHunterSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(["damage", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual("earth", school.school_ring())

    def test_school_knacks(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(["detect taint", "iaijutsu", "presence"], school.school_knacks())

    def test_free_raise_skills(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(["interrogation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual("investigation", school.ap_base_skill())

    def test_ap_skills(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestKuniSpecialAbility(unittest.TestCase):
    def test_extra_kept_wound_check(self):
        kuni = Character("Kuni")
        school = kuni_school.KuniWitchHunterSchool()
        school.apply_special_ability(kuni)
        # Special ability grants extra 1k1 on wound checks (kept part)
        self.assertEqual(1, kuni.extra_kept("wound check"))


class TestKuniAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        kuni = Character("Kuni")
        kuni.set_skill("investigation", 5)
        school = kuni_school.KuniWitchHunterSchool()
        school.apply_rank_three_ability(kuni)
        self.assertEqual("investigation", kuni.ap_base_skill())
        self.assertTrue(kuni.can_spend_ap("attack"))
        self.assertTrue(kuni.can_spend_ap("wound check"))
        self.assertFalse(kuni.can_spend_ap("parry"))
        # AP = 2 * investigation skill = 10
        self.assertEqual(10, kuni.ap())


class TestKuniWoundCheckSucceededListener(unittest.TestCase):
    def setUp(self):
        self.kuni = Character("Kuni")
        self.kuni.set_strategy("light_wounds", AlwaysKeepLightWoundsStrategy())
        self.attacker = Character("attacker")
        groups = [Group("Crab", self.kuni), Group("Attacker", self.attacker)]
        self.context = EngineContext(groups)

    def test_reflect_damage(self):
        self.kuni._lw = 15
        listener = kuni_school.KuniWoundCheckSucceededListener()
        event = events.WoundCheckSucceededEvent(self.kuni, self.attacker, 15, 25)
        responses = list(listener.handle(self.kuni, event, self.context))
        # First response should be LightWoundsDamageEvent reflecting damage back
        self.assertTrue(len(responses) >= 1)
        first = responses[0]
        self.assertTrue(isinstance(first, events.LightWoundsDamageEvent))
        self.assertEqual(self.kuni, first.subject)
        self.assertEqual(self.attacker, first.target)
        self.assertEqual(15, first.damage)

    def test_no_reflect_zero_damage(self):
        listener = kuni_school.KuniWoundCheckSucceededListener()
        event = events.WoundCheckSucceededEvent(self.kuni, self.attacker, 0, 25)
        responses = list(listener.handle(self.kuni, event, self.context))
        # No LW reflection for zero damage, but should still get KeepLightWoundsEvent
        lw_damage_events = [r for r in responses if isinstance(r, events.LightWoundsDamageEvent)]
        self.assertEqual(0, len(lw_damage_events))
