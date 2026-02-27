#!/usr/bin/env python3

#
# test_monk_school.py
#
# Unit tests for the Brotherhood of Shinsei Monk School.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.log import logger
from simulation.schools import monk_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestMonkSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        self.assertEqual("Brotherhood of Shinsei Monk School", school.name())

    def test_extra_rolled(self):
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        self.assertEqual(["attack", "damage", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        self.assertEqual(["conviction", "otherworldliness", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        self.assertEqual(["attack"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        self.assertEqual("precepts", school.ap_base_skill())

    def test_ap_skills(self):
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestMonkSpecialAbility(unittest.TestCase):
    def test_extra_1k1_damage(self):
        monk = Character("Monk")
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        school.apply_special_ability(monk)
        # Extra 1k1 on damage rolls (unarmed fighting)
        self.assertEqual(1, monk.extra_rolled("damage"))
        self.assertEqual(1, monk.extra_kept("damage"))

    def test_no_extra_on_attack(self):
        monk = Character("Monk")
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        school.apply_special_ability(monk)
        # Attack should NOT get extra kept from special ability
        self.assertEqual(0, monk.extra_kept("attack"))


class TestMonkAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        monk = Character("Monk")
        monk.set_skill("precepts", 5)
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        school.apply_rank_three_ability(monk)
        self.assertEqual("precepts", monk.ap_base_skill())
        self.assertTrue(monk.can_spend_ap("attack"))
        self.assertTrue(monk.can_spend_ap("wound check"))
        self.assertFalse(monk.can_spend_ap("parry"))
        # AP = 2 * precepts skill = 10
        self.assertEqual(10, monk.ap())

    def test_ap_with_lower_skill(self):
        monk = Character("Monk")
        monk.set_skill("precepts", 3)
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        school.apply_rank_three_ability(monk)
        # AP = 2 * 3 = 6
        self.assertEqual(6, monk.ap())


class TestMonkFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        monk = Character("Monk")
        monk.set_ring("water", 3)
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        school.apply_rank_four_ability(monk)
        # Ring raise: water should be +1
        self.assertEqual(4, monk.ring("water"))
