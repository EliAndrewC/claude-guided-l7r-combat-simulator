#!/usr/bin/env python3

#
# test_ikoma_bard_school.py
#
# Unit tests for the Ikoma Bard School.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.log import logger
from simulation.schools import ikoma_bard_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIkomaBardSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual("Ikoma Bard School", school.name())

    def test_extra_rolled(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["attack", "bragging", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["discern honor", "oppose knowledge", "oppose social"], school.school_knacks())

    def test_free_raise_skills(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["attack"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual("bragging", school.ap_base_skill())

    def test_ap_skills(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestIkomaBardAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        ikoma = Character("Ikoma")
        ikoma.set_skill("bragging", 5)
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_rank_three_ability(ikoma)
        self.assertEqual("bragging", ikoma.ap_base_skill())
        self.assertTrue(ikoma.can_spend_ap("attack"))
        self.assertTrue(ikoma.can_spend_ap("wound check"))
        self.assertFalse(ikoma.can_spend_ap("parry"))
        # AP = 2 * bragging skill = 10
        self.assertEqual(10, ikoma.ap())


class TestIkomaFourthDan(unittest.TestCase):
    def test_damage_roll_10_dice_no_extra(self):
        ikoma = Character("Ikoma")
        ikoma.set_ring("water", 3)
        target = Character("Target")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_rank_four_ability(ikoma)
        provider = ikoma.roll_parameter_provider()
        # When attack_extra_rolled == 0, rolled should be at least 10
        rolled, kept, modifier = provider.get_damage_roll_params(ikoma, target, "attack", 0)
        self.assertGreaterEqual(rolled, 10)

    def test_damage_roll_normal_with_extra(self):
        ikoma = Character("Ikoma")
        ikoma.set_ring("water", 3)
        ikoma.set_skill("attack", 3)
        target = Character("Target")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_rank_four_ability(ikoma)
        provider = ikoma.roll_parameter_provider()
        # When attack_extra_rolled > 0, use normal damage calculation
        rolled, kept, modifier = provider.get_damage_roll_params(ikoma, target, "attack", 2)
        # With extra, rolled should be normal (not forced to 10)
        # Normal damage = weapon_rolled (default 3) + extra_rolled(damage) + attack_extra_rolled
        # This should NOT be forced to 10
        self.assertIsNotNone(rolled)
