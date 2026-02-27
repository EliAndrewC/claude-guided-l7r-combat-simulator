#!/usr/bin/env python3

#
# test_priest_school.py
#
# Unit tests for the Priest School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.roll_provider import TestRollProvider
from simulation.schools import priest_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestPriestSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = priest_school.PriestSchool()
        self.assertEqual("Priest School", school.name())

    def test_extra_rolled(self):
        school = priest_school.PriestSchool()
        self.assertEqual(["precepts", "initiative", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = priest_school.PriestSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = priest_school.PriestSchool()
        self.assertEqual(["conviction", "otherworldliness", "pontificate"], school.school_knacks())

    def test_free_raise_skills(self):
        school = priest_school.PriestSchool()
        self.assertEqual(["bragging", "precepts", "sincerity"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = priest_school.PriestSchool()
        self.assertIsNone(school.ap_base_skill())


class TestPriestSpecialAbility(unittest.TestCase):
    def test_no_combat_effect(self):
        priest = Character("Priest")
        school = priest_school.PriestSchool()
        # apply_special_ability should be a no-op
        school.apply_special_ability(priest)
        # Character state unchanged
        self.assertEqual(0, priest.extra_rolled("attack"))
        self.assertEqual(0, priest.extra_kept("attack"))


class TestPriestThirdDan(unittest.TestCase):
    def setUp(self):
        self.priest = Character("Priest")
        self.priest.set_skill("precepts", 3)
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([2, 5])
        # Queue 3 skill rolls for pool dice (one per precepts rank)
        roll_provider.put_skill_roll("precepts", 7)
        roll_provider.put_skill_roll("precepts", 7)
        roll_provider.put_skill_roll("precepts", 7)
        self.priest.set_roll_provider(roll_provider)
        self.target = Character("Target")
        groups = [Group("Phoenix", self.priest), Group("Enemy", self.target)]
        self.context = EngineContext(groups)

    def test_pool_dice_created_on_new_round(self):
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(self.priest)
        event = events.NewRoundEvent(1)
        list(self.priest.event(event, self.context))
        # Should have 3 floating bonuses (one per precepts skill rank)
        bonuses = self.priest.floating_bonuses("attack")
        self.assertEqual(3, len(bonuses))
        # Each bonus should be 7 (from queued roll provider)
        for bonus in bonuses:
            self.assertEqual(7, bonus.bonus())

    def test_pool_dice_applicable_to_multiple_skills(self):
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(self.priest)
        event = events.NewRoundEvent(1)
        list(self.priest.event(event, self.context))
        # Bonuses should be applicable to attack, parry, wound check, damage
        for skill in ["attack", "parry", "wound check", "damage"]:
            bonuses = self.priest.floating_bonuses(skill)
            self.assertEqual(3, len(bonuses), f"Expected 3 bonuses for {skill}")

    def test_no_pool_with_zero_precepts(self):
        self.priest.set_skill("precepts", 0)
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([2, 5])
        self.priest.set_roll_provider(roll_provider)
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(self.priest)
        event = events.NewRoundEvent(1)
        list(self.priest.event(event, self.context))
        bonuses = self.priest.floating_bonuses("attack")
        self.assertEqual(0, len(bonuses))


class TestPriestFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        priest = Character("Priest")
        priest.set_ring("water", 3)
        school = priest_school.PriestSchool()
        school.apply_rank_four_ability(priest)
        self.assertEqual(4, priest.ring("water"))
