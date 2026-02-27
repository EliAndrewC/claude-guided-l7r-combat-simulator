#!/usr/bin/env python3

#
# test_kitsuki_school.py
#
# Unit tests for the Kitsuki Magistrate School.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.log import logger
from simulation.schools import kitsuki_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestKitsukiSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual("Kitsuki Magistrate School", school.name())

    def test_extra_rolled(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["interrogation", "investigation", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["discern honor", "iaijutsu", "presence"], school.school_knacks())

    def test_free_raise_skills(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["interrogation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual("investigation", school.ap_base_skill())

    def test_ap_skills(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestKitsukiSpecialAbility(unittest.TestCase):
    def test_water_added_to_attack_roll(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 4)
        target = Character("Target")
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_special_ability(kitsuki)
        provider = kitsuki.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(kitsuki, target, "attack")
        # Special: 2 * Water (4) = 8
        self.assertEqual(8, modifier)

    def test_no_bonus_on_non_attack(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 4)
        target = Character("Target")
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_special_ability(kitsuki)
        provider = kitsuki.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(kitsuki, target, "parry")
        # Non-attack should not get the bonus
        self.assertEqual(0, modifier)

    def test_water_scales_with_ring(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 2)
        target = Character("Target")
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_special_ability(kitsuki)
        provider = kitsuki.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(kitsuki, target, "attack")
        # 2 * Water (2) = 4
        self.assertEqual(4, modifier)


class TestKitsukiAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_skill("investigation", 5)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_three_ability(kitsuki)
        self.assertEqual("investigation", kitsuki.ap_base_skill())
        self.assertTrue(kitsuki.can_spend_ap("attack"))
        self.assertTrue(kitsuki.can_spend_ap("wound check"))
        self.assertFalse(kitsuki.can_spend_ap("parry"))
        # AP = 2 * investigation skill = 10
        self.assertEqual(10, kitsuki.ap())

    def test_ap_with_lower_skill(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_skill("investigation", 3)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_three_ability(kitsuki)
        # AP = 2 * 3 = 6
        self.assertEqual(6, kitsuki.ap())


class TestKitsukiFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 3)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_four_ability(kitsuki)
        # Ring raise: water should be +1
        self.assertEqual(4, kitsuki.ring("water"))
