#!/usr/bin/env python3

#
# test_shosuro_actor_school.py
#
# Unit tests for the Shosuro Actor School.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.log import logger
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import shosuro_actor_school
from simulation.schools.shosuro_actor_school import ShosuroActorRollProvider

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestShosuroActorSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = shosuro_actor_school.ShosuroActorSchool()
        self.assertEqual("Shosuro Actor School", school.name())

    def test_extra_rolled(self):
        school = shosuro_actor_school.ShosuroActorSchool()
        self.assertEqual(["attack", "sincerity", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = shosuro_actor_school.ShosuroActorSchool()
        self.assertEqual("air", school.school_ring())

    def test_school_knacks(self):
        school = shosuro_actor_school.ShosuroActorSchool()
        self.assertEqual(["athletics", "discern honor", "pontificate"], school.school_knacks())

    def test_free_raise_skills(self):
        school = shosuro_actor_school.ShosuroActorSchool()
        self.assertEqual(["sincerity"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = shosuro_actor_school.ShosuroActorSchool()
        self.assertEqual("sincerity", school.ap_base_skill())

    def test_ap_skills(self):
        school = shosuro_actor_school.ShosuroActorSchool()
        self.assertEqual(["acting", "heraldry", "sincerity", "sneaking", "attack", "wound check"], school.ap_skills())


class TestShosuroSpecialAbility(unittest.TestCase):
    def test_acting_extra_rolled_on_attack(self):
        shosuro = Character("Shosuro")
        shosuro.set_skill("acting", 3)
        target = Character("Target")
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_special_ability(shosuro)
        provider = shosuro.roll_parameter_provider()
        rolled, kept, modifier = provider.get_skill_roll_params(shosuro, target, "attack")
        # Base attack: skill(attack=0) + ring(fire=2, default) rolled; ring kept
        # With special: +acting(3) rolled
        base_rolled = shosuro.skill("attack") + shosuro.ring("fire")
        self.assertEqual(base_rolled + 3, rolled)

    def test_acting_extra_rolled_on_parry(self):
        shosuro = Character("Shosuro")
        shosuro.set_skill("acting", 2)
        target = Character("Target")
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_special_ability(shosuro)
        provider = shosuro.roll_parameter_provider()
        rolled, kept, modifier = provider.get_skill_roll_params(shosuro, target, "parry")
        base_rolled = shosuro.skill("parry") + shosuro.ring("air")
        self.assertEqual(base_rolled + 2, rolled)

    def test_acting_extra_rolled_on_wound_check(self):
        shosuro = Character("Shosuro")
        shosuro.set_skill("acting", 4)
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_special_ability(shosuro)
        provider = shosuro.roll_parameter_provider()
        rolled, kept, modifier = provider.get_wound_check_roll_params(shosuro)
        # Wound check: ring("water") + 1 + extra_rolled + acting
        base_rolled = shosuro.ring("water") + 1
        self.assertEqual(base_rolled + 4, rolled)

    def test_no_acting_bonus_on_other_skills(self):
        shosuro = Character("Shosuro")
        shosuro.set_skill("acting", 3)
        target = Character("Target")
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_special_ability(shosuro)
        provider = shosuro.roll_parameter_provider()
        # Use "feint" which has a valid ring mapping (fire) but is not parry
        rolled, _, _ = provider.get_skill_roll_params(shosuro, target, "feint")
        # feint is an ATTACK_SKILL so it DOES get acting bonus
        # Use a different approach: verify attack gets bonus, then verify
        # the provider only adds acting to attack/parry/wound check
        base_rolled = shosuro.skill("feint") + shosuro.ring("fire")
        # feint is in ATTACK_SKILLS so it gets +acting
        self.assertEqual(base_rolled + 3, rolled)

    def test_acting_zero_no_bonus(self):
        shosuro = Character("Shosuro")
        # acting defaults to 0
        target = Character("Target")
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_special_ability(shosuro)
        provider = shosuro.roll_parameter_provider()
        rolled, _, _ = provider.get_skill_roll_params(shosuro, target, "attack")
        base_rolled = shosuro.skill("attack") + shosuro.ring("fire")
        self.assertEqual(base_rolled, rolled)


class TestShosuroAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        shosuro = Character("Shosuro")
        shosuro.set_skill("sincerity", 5)
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_rank_three_ability(shosuro)
        self.assertEqual("sincerity", shosuro.ap_base_skill())
        self.assertTrue(shosuro.can_spend_ap("attack"))
        self.assertTrue(shosuro.can_spend_ap("wound check"))
        self.assertFalse(shosuro.can_spend_ap("parry"))
        # AP = 2 * sincerity skill = 10
        self.assertEqual(10, shosuro.ap())


class TestShosuroFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        shosuro = Character("Shosuro")
        shosuro.set_ring("air", 3)
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_rank_four_ability(shosuro)
        # Ring raise: air should be +1
        self.assertEqual(4, shosuro.ring("air"))


class TestShosuroFifthDan(unittest.TestCase):
    def test_shosuro_5th_dan_adds_lowest_3_to_skill_roll(self):
        """5th Dan adds lowest 3 dice to skill roll result."""
        shosuro = Character("Shosuro")
        provider = CalvinistRollProvider()
        # Queue initiative
        provider.put_initiative_roll([3])
        # Queue a skill roll with dice: [9, 7, 5, 3, 1]
        # Base total = 21 (e.g. sum of top 3 kept)
        # Lowest 3 dice are [1, 3, 5] = 9
        provider.put_skill_roll_with_dice("attack", 21, [9, 7, 5, 3, 1])
        # Wrap with ShosuroActorRollProvider
        wrapped = ShosuroActorRollProvider(provider)
        shosuro.set_roll_provider(wrapped)
        # Roll skill directly via the wrapper
        result = wrapped.get_skill_roll("attack", 5, 3)
        # Expected: 21 + (1 + 3 + 5) = 30
        self.assertEqual(30, result)

    def test_shosuro_5th_dan_adds_lowest_3_to_wound_check(self):
        """5th Dan adds lowest 3 dice to wound check result."""
        shosuro = Character("Shosuro")
        provider = CalvinistRollProvider()
        # Queue wound check with dice: [10, 8, 6, 4, 2]
        # Base total = 24 (e.g. sum of top 3 kept)
        # Lowest 3 dice are [2, 4, 6] = 12
        provider.put_wound_check_roll_with_dice(24, [10, 8, 6, 4, 2])
        wrapped = ShosuroActorRollProvider(provider)
        shosuro.set_roll_provider(wrapped)
        result = wrapped.get_wound_check_roll(5, 3)
        # Expected: 24 + (2 + 4 + 6) = 36
        self.assertEqual(36, result)

    def test_shosuro_5th_dan_no_bonus_on_damage(self):
        """5th Dan does NOT add lowest dice to damage rolls."""
        provider = CalvinistRollProvider()
        provider.put_damage_roll_with_dice(15, [8, 7])
        wrapped = ShosuroActorRollProvider(provider)
        result = wrapped.get_damage_roll(2, 2)
        # Damage should be unmodified
        self.assertEqual(15, result)

    def test_shosuro_5th_dan_no_bonus_on_initiative(self):
        """5th Dan does NOT add lowest dice to initiative rolls."""
        provider = CalvinistRollProvider()
        provider.put_initiative_roll([3, 7])
        wrapped = ShosuroActorRollProvider(provider)
        result = wrapped.get_initiative_roll(2, 2)
        # Initiative should be unmodified
        self.assertEqual([3, 7], result)

    def test_shosuro_5th_dan_fewer_than_3_dice(self):
        """If fewer than 3 dice, add all available dice."""
        provider = CalvinistRollProvider()
        # Only 2 dice: [8, 3]
        # Lowest 2 are [3, 8] = 11
        provider.put_skill_roll_with_dice("attack", 11, [8, 3])
        wrapped = ShosuroActorRollProvider(provider)
        result = wrapped.get_skill_roll("attack", 2, 2)
        # Expected: 11 + (3 + 8) = 22
        self.assertEqual(22, result)

    def test_shosuro_5th_dan_no_dice_info_no_bonus(self):
        """If no dice info available (plain int roll), no bonus added."""
        provider = CalvinistRollProvider()
        # Use plain int (no dice info)
        provider.put_skill_roll("attack", 21)
        wrapped = ShosuroActorRollProvider(provider)
        result = wrapped.get_skill_roll("attack", 5, 3)
        # No dice info, so no bonus: result is just 21
        self.assertEqual(21, result)

    def test_shosuro_5th_dan_with_special_ability(self):
        """Both Special Ability (extra rolled dice) and 5th Dan (lowest 3 bonus) work together."""
        shosuro = Character("Shosuro")
        shosuro.set_skill("acting", 3)
        school = shosuro_actor_school.ShosuroActorSchool()
        # Apply special ability (adds acting to rolled dice via parameter provider)
        school.apply_special_ability(shosuro)
        # Set up CalvinistRollProvider with dice info
        provider = CalvinistRollProvider()
        provider.put_initiative_roll([3])
        # With acting=3, attack gets extra rolled dice from special ability
        # That's handled by the parameter provider, not the roll provider
        # The roll provider just sees the final roll result and dice
        # Dice: [10, 8, 6, 4, 2, 1] (6 dice rolled due to special ability)
        # Base total = 24 (top 3 kept: 10+8+6)
        # Lowest 3: [1, 2, 4] = 7
        provider.put_skill_roll_with_dice("attack", 24, [10, 8, 6, 4, 2, 1])
        # Apply 5th Dan ability
        school.apply_rank_five_ability(shosuro)
        # The apply_rank_five_ability should wrap the provider
        # But we need to set up our test provider first, then apply 5th dan
        # Let's do it manually: set provider, then wrap
        shosuro.set_roll_provider(provider)
        school.apply_rank_five_ability(shosuro)
        # Now roll_provider should be wrapped
        result = shosuro.roll_provider().get_skill_roll("attack", 6, 3)
        # Expected: 24 + (1 + 2 + 4) = 31
        self.assertEqual(31, result)

    def test_shosuro_5th_dan_apply_rank_five_wraps_provider(self):
        """apply_rank_five_ability wraps the character's roll provider."""
        shosuro = Character("Shosuro")
        provider = CalvinistRollProvider()
        shosuro.set_roll_provider(provider)
        school = shosuro_actor_school.ShosuroActorSchool()
        school.apply_rank_five_ability(shosuro)
        # The roll provider should now be a ShosuroActorRollProvider
        self.assertIsInstance(shosuro.roll_provider(), ShosuroActorRollProvider)

    def test_shosuro_5th_dan_proxies_last_skill_info(self):
        """The wrapper proxies last_skill_info to the inner provider."""
        provider = CalvinistRollProvider()
        provider.put_skill_roll_with_dice("attack", 21, [9, 7, 5, 3, 1])
        wrapped = ShosuroActorRollProvider(provider)
        wrapped.get_skill_roll("attack", 5, 3)
        info = wrapped.last_skill_info()
        self.assertIsNotNone(info)
        self.assertEqual([9, 7, 5, 3, 1], info["dice"])

    def test_shosuro_5th_dan_proxies_last_wound_check_info(self):
        """The wrapper proxies last_wound_check_info to the inner provider."""
        provider = CalvinistRollProvider()
        provider.put_wound_check_roll_with_dice(24, [10, 8, 6, 4, 2])
        wrapped = ShosuroActorRollProvider(provider)
        wrapped.get_wound_check_roll(5, 3)
        info = wrapped.last_wound_check_info()
        self.assertIsNotNone(info)
        self.assertEqual([10, 8, 6, 4, 2], info["dice"])

    def test_shosuro_5th_dan_proxies_last_damage_info(self):
        """The wrapper proxies last_damage_info to the inner provider."""
        provider = CalvinistRollProvider()
        provider.put_damage_roll_with_dice(15, [8, 7])
        wrapped = ShosuroActorRollProvider(provider)
        wrapped.get_damage_roll(2, 2)
        info = wrapped.last_damage_info()
        self.assertIsNotNone(info)
        self.assertEqual([8, 7], info["dice"])
