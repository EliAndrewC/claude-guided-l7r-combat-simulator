#!/usr/bin/env python3

#
# test_doji_artisan_school.py
#
# Unit tests for the Doji Artisan School.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.log import logger
from simulation.schools import doji_artisan_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestDojiArtisanSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual("Doji Artisan School", school.name())

    def test_extra_rolled(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["counterattack", "manipulation", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["counterattack", "oppose social", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["manipulation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual("culture", school.ap_base_skill())

    def test_ap_skills(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["counterattack", "wound check"], school.ap_skills())


class TestDojiArtisanSpecialAbility(unittest.TestCase):
    def test_counterattack_interrupt_cost(self):
        doji = Character("Doji")
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(doji)
        # Counterattack interrupt cost should be 1 (instead of default 2)
        from simulation.context import EngineContext
        from simulation.groups import Group
        target = Character("Target")
        groups = [Group("Doji", doji), Group("Target", target)]
        context = EngineContext(groups)
        self.assertEqual(1, doji.interrupt_cost("counterattack", context))

    def test_default_interrupt_cost_unchanged(self):
        doji = Character("Doji")
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(doji)
        from simulation.context import EngineContext
        from simulation.groups import Group
        target = Character("Target")
        groups = [Group("Doji", doji), Group("Target", target)]
        context = EngineContext(groups)
        # Non-counterattack skills should still have default interrupt cost (2)
        self.assertEqual(2, doji.interrupt_cost("parry", context))


class TestDojiArtisanAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        doji = Character("Doji")
        doji.set_skill("culture", 5)
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_three_ability(doji)
        self.assertEqual("culture", doji.ap_base_skill())
        self.assertTrue(doji.can_spend_ap("counterattack"))
        self.assertTrue(doji.can_spend_ap("wound check"))
        self.assertFalse(doji.can_spend_ap("attack"))
        # AP = 2 * culture skill = 10
        self.assertEqual(10, doji.ap())


class TestDojiArtisanFifthDan(unittest.TestCase):
    def test_tn_bonus_on_attack(self):
        doji = Character("Doji")
        target = Character("Target")
        target.set_skill("parry", 3)
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(doji, target, "attack")
        # Target TN to hit = 5*(1+3) = 20; bonus = (20-10)//5 = 2
        self.assertEqual(2, modifier)

    def test_no_bonus_on_low_tn(self):
        doji = Character("Doji")
        target = Character("Target")
        # Default parry=0, TN to hit = 5*(1+0) = 5
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(doji, target, "attack")
        # TN=5, (5-10)//5 = -1, max(0, -1) = 0
        self.assertEqual(0, modifier)

    def test_wound_check_bonus(self):
        doji = Character("Doji")
        doji._lw = 25
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_wound_check_roll_params(doji)
        # LW=25, bonus = (25-10)//5 = 3
        self.assertEqual(3, modifier)

    def test_wound_check_bonus_zero_lw(self):
        doji = Character("Doji")
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_wound_check_roll_params(doji)
        # LW=0, (0-10)//5 = -2, max(0, -2) = 0
        self.assertEqual(0, modifier)
