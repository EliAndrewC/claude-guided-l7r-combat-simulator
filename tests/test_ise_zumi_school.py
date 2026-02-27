#!/usr/bin/env python3

#
# test_ise_zumi_school.py
#
# Unit tests for the Togashi Ise Zumi School.
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
from simulation.schools import ise_zumi_school, ishi_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIseZumiSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        self.assertEqual("Togashi Ise Zumi School", school.name())

    def test_extra_rolled(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        self.assertEqual(["attack", "parry", "athletics"], school.extra_rolled())

    def test_school_ring(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        self.assertEqual("void", school.school_ring())

    def test_school_knacks(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        self.assertEqual(["athletics", "conviction", "dragon tattoo"], school.school_knacks())

    def test_free_raise_skills(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        self.assertEqual(["athletics"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        self.assertEqual("precepts", school.ap_base_skill())

    def test_ap_skills(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        self.assertEqual(["athletics"], school.ap_skills())


class TestIseZumiSpecialAbility(unittest.TestCase):
    def test_extra_action_die_on_new_round(self):
        zumi = Character("Zumi")
        roll_provider = TestRollProvider()
        # Normal initiative: 2 dice
        roll_provider.put_initiative_roll([3, 7])
        # Extra initiative: 1 die
        roll_provider.put_initiative_roll([5])
        zumi.set_roll_provider(roll_provider)
        school = ise_zumi_school.TogashiIseZumiSchool()
        school.apply_special_ability(zumi)
        target = Character("Target")
        groups = [Group("Dragon", zumi), Group("Enemy", target)]
        context = EngineContext(groups)
        event = events.NewRoundEvent(1)
        list(zumi.event(event, context))
        # Should have 2 (normal) + 1 (extra) = 3 actions
        self.assertEqual(3, len(zumi.actions()))
        self.assertIn(3, zumi.actions())
        self.assertIn(5, zumi.actions())
        self.assertIn(7, zumi.actions())


class TestIseZumiThirdDan(unittest.TestCase):
    def test_4x_ap_multiplier(self):
        zumi = Character("Zumi")
        zumi.set_skill("precepts", 3)
        school = ise_zumi_school.TogashiIseZumiSchool()
        school.apply_rank_three_ability(zumi)
        # AP = 4 * precepts = 4 * 3 = 12
        self.assertEqual(12, zumi.ap())
        self.assertTrue(zumi.can_spend_ap("athletics"))
        self.assertFalse(zumi.can_spend_ap("attack"))

    def test_4x_ap_with_different_skill(self):
        zumi = Character("Zumi")
        zumi.set_skill("precepts", 5)
        school = ise_zumi_school.TogashiIseZumiSchool()
        school.apply_rank_three_ability(zumi)
        # AP = 4 * 5 = 20
        self.assertEqual(20, zumi.ap())


class TestIseZumiFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        zumi = Character("Zumi")
        zumi.set_ring("void", 3)
        school = ise_zumi_school.TogashiIseZumiSchool()
        school.apply_rank_four_ability(zumi)
        self.assertEqual(4, zumi.ring("void"))


class TestIseZumiFifthDan(unittest.TestCase):
    def setUp(self):
        self.zumi = Character("Zumi")
        self.zumi.set_ring("earth", 3)
        self.attacker = Character("Attacker")
        groups = [Group("Dragon", self.zumi), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)

    def test_heal_sw_on_wound_check_failed(self):
        school = ise_zumi_school.TogashiIseZumiSchool()
        school.apply_rank_five_ability(self.zumi)
        # Give the character some SW first
        self.zumi.take_sw(3)
        event = events.WoundCheckFailedEvent(self.zumi, self.attacker, 20, 10)
        responses = list(self.zumi.event(event, self.context))
        # Should have taken SW from wound check and then healed 2
        vp_events = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertTrue(len(vp_events) > 0)


class TestAPMultiplierInfrastructure(unittest.TestCase):
    """Test that _ap_multiplier infrastructure works correctly."""

    def test_default_ap_multiplier_is_2(self):
        char = Character("Test")
        char.set_skill("precepts", 3)
        char.set_ap_base_skill("precepts")
        # Default: 2 * 3 = 6
        self.assertEqual(6, char.ap())

    def test_set_ap_multiplier(self):
        char = Character("Test")
        char.set_skill("precepts", 3)
        char.set_ap_base_skill("precepts")
        char.set_ap_multiplier(4)
        # 4 * 3 = 12
        self.assertEqual(12, char.ap())

    def test_ap_multiplier_validates_int(self):
        char = Character("Test")
        with self.assertRaises(ValueError):
            char.set_ap_multiplier("four")


class TestMaxVPProviderInfrastructure(unittest.TestCase):
    """Test that _max_vp_provider infrastructure works correctly."""

    def test_default_max_vp_without_provider(self):
        char = Character("Test")
        char.set_ring("air", 2)
        char.set_ring("earth", 2)
        char.set_ring("fire", 2)
        char.set_ring("water", 2)
        char.set_ring("void", 2)
        # Standard: min(rings) + worldliness = 2 + 0 = 2
        self.assertEqual(2, char.max_vp())
        # Standard: min(rings) = 2
        self.assertEqual(2, char.max_vp_per_roll())

    def test_custom_max_vp_provider(self):
        char = Character("Test")
        char.set_ring("void", 5)
        provider = ishi_school.IshiMaxVPProvider(school_rank=3)
        char.set_max_vp_provider(provider)
        # Custom: highest ring(5) + school_rank(3) = 8
        self.assertEqual(8, char.max_vp())
        # Custom: lowest ring(2) - 1 = 1
        self.assertEqual(1, char.max_vp_per_roll())
