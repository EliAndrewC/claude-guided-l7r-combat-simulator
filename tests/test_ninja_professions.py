#!/usr/bin/env python3

#
# test_ninja_professions.py
#
# Unit tests for Ninja profession abilities
#

import logging
import sys
import unittest

from simulation.actions import AttackAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import AttackSucceededEvent, NewRoundEvent
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.ninja_rolls import (
    NinjaDamageKeepRoll,
    NinjaDamageReductionRoll,
    NinjaWoundCheckRoll,
)
from simulation.mechanics.roll import TestDice
from simulation.mechanics.roll_provider import TestRollProvider
from simulation.professions import (
    ATTACK_BONUS,
    ATTACK_PENALTY,
    DAMAGE_KEEPING_BONUS,
    DAMAGE_REDUCTION,
    DEFENSE_BONUS,
    INITIATIVE_REDUCTION,
    SINCERITY_BONUS,
    STEALTH_INVISIBILITY,
    STEALTH_MEMORABILITY,
    WOUND_CHECK_NINJA_BONUS,
    NinjaRollProvider,
    Profession,
    get_profession_ability,
)

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestNinjaDamageReductionRoll(unittest.TestCase):
    """Tests for NinjaDamageReductionRoll."""

    def test_no_tens_no_reduction(self):
        test_dice = TestDice()
        test_dice.extend([3, 5, 7, 8, 9, 4])
        roll = NinjaDamageReductionRoll(6, 3, reduction=0, die_provider=test_dice)
        # top 3: 9, 8, 7 = 24
        self.assertEqual(24, roll.roll())

    def test_tens_no_reduction(self):
        # With 0 reduction, all tens should reroll (min 1 = all of them)
        test_dice = TestDice()
        # Initial rolls: 3, 5, 10, 10, 9, 4
        # Two 10s, reduction=0, reroll_count = max(1, 2-0) = 2
        # Both 10s reroll: 10+3=13, 10+5=15
        test_dice.extend([3, 5, 10, 10, 9, 4, 3, 5])
        roll = NinjaDamageReductionRoll(6, 3, reduction=0, die_provider=test_dice)
        # dice after: [15, 13, 9, 5, 4, 3], top 3: 15+13+9 = 37
        self.assertEqual(37, roll.roll())

    def test_tens_reduction_one(self):
        test_dice = TestDice()
        # Initial rolls: 3, 5, 10, 10, 9, 4
        # Two 10s, reduction=1, reroll_count = max(1, 2-1) = 1
        # Only one 10 rerolls: 10+3=13; other stays as 10
        test_dice.extend([3, 5, 10, 10, 9, 4, 3])
        roll = NinjaDamageReductionRoll(6, 3, reduction=1, die_provider=test_dice)
        # dice after: [13, 10, 9, 5, 4, 3], top 3: 13+10+9 = 32
        self.assertEqual(32, roll.roll())

    def test_tens_reduction_two(self):
        test_dice = TestDice()
        # Initial rolls: 3, 5, 10, 10, 9, 4
        # Two 10s, reduction=2, reroll_count = max(1, 2-2) = 1
        # Only one 10 rerolls (min 1): 10+3=13; other stays as 10
        test_dice.extend([3, 5, 10, 10, 9, 4, 3])
        roll = NinjaDamageReductionRoll(6, 3, reduction=2, die_provider=test_dice)
        # dice after: [13, 10, 9, 5, 4, 3], top 3: 13+10+9 = 32
        self.assertEqual(32, roll.roll())

    def test_single_ten_with_reduction(self):
        test_dice = TestDice()
        # Initial rolls: 3, 5, 10, 8, 9, 4
        # One 10, reduction=1, reroll_count = max(1, 1-1) = 1
        # The one 10 still rerolls (min 1): 10+6=16
        test_dice.extend([3, 5, 10, 8, 9, 4, 6])
        roll = NinjaDamageReductionRoll(6, 3, reduction=1, die_provider=test_dice)
        # dice after: [16, 9, 8, 5, 4, 3], top 3: 16+9+8 = 33
        self.assertEqual(33, roll.roll())

    def test_no_tens(self):
        test_dice = TestDice()
        test_dice.extend([3, 5, 7, 8, 9, 4])
        roll = NinjaDamageReductionRoll(6, 3, reduction=1, die_provider=test_dice)
        # No tens to reroll, top 3: 9+8+7 = 24
        self.assertEqual(24, roll.roll())


class TestNinjaWoundCheckRoll(unittest.TestCase):
    """Tests for NinjaWoundCheckRoll."""

    def test_level_one_no_low_dice(self):
        test_dice = TestDice()
        test_dice.extend([5, 6, 7, 8])
        roll = NinjaWoundCheckRoll(4, 2, ability_level=1, die_provider=test_dice)
        # No dice < 5, top 2: 8+7 = 15
        self.assertEqual(15, roll.roll())

    def test_level_one_with_low_dice(self):
        test_dice = TestDice()
        test_dice.extend([1, 2, 3, 4])
        roll = NinjaWoundCheckRoll(4, 2, ability_level=1, die_provider=test_dice)
        # dice < 5 get bonus of 1*(5-X):
        # 1 -> 1+4=5, 2 -> 2+3=5, 3 -> 3+2=5, 4 -> 4+1=5
        # All become 5, top 2: 5+5 = 10
        self.assertEqual(10, roll.roll())

    def test_level_two_with_low_dice(self):
        test_dice = TestDice()
        test_dice.extend([1, 2, 3, 4])
        roll = NinjaWoundCheckRoll(4, 2, ability_level=2, die_provider=test_dice)
        # dice < 5 get bonus of 2*(5-X):
        # 1 -> 1+8=9, 2 -> 2+6=8, 3 -> 3+4=7, 4 -> 4+2=6
        # top 2: 9+8 = 17
        self.assertEqual(17, roll.roll())

    def test_level_one_mixed_dice(self):
        test_dice = TestDice()
        test_dice.extend([1, 7, 3, 9])
        roll = NinjaWoundCheckRoll(4, 2, ability_level=1, die_provider=test_dice)
        # 1 -> 1+4=5, 7 stays, 3 -> 3+2=5, 9 stays
        # top 2: 9+7 = 16
        self.assertEqual(16, roll.roll())


class TestNinjaDamageKeepRoll(unittest.TestCase):
    """Tests for NinjaDamageKeepRoll."""

    def test_no_extra(self):
        test_dice = TestDice()
        test_dice.extend([3, 5, 7, 8, 9, 4, 6])
        roll = NinjaDamageKeepRoll(7, 3, extra_lowest=0, die_provider=test_dice)
        # top 3: 9+8+7 = 24
        self.assertEqual(24, roll.roll())

    def test_extra_lowest_two(self):
        test_dice = TestDice()
        test_dice.extend([3, 5, 7, 8, 9, 4, 6])
        roll = NinjaDamageKeepRoll(7, 3, extra_lowest=2, die_provider=test_dice)
        # sorted desc: [9, 8, 7, 6, 5, 4, 3]
        # top 3: 9+8+7 = 24
        # unkept: [6, 5, 4, 3], bottom 2: [4, 3]
        # total: 24 + 4 + 3 = 31
        self.assertEqual(31, roll.roll())

    def test_extra_lowest_four(self):
        test_dice = TestDice()
        test_dice.extend([3, 5, 7, 8, 9, 4, 6])
        roll = NinjaDamageKeepRoll(7, 3, extra_lowest=4, die_provider=test_dice)
        # sorted desc: [9, 8, 7, 6, 5, 4, 3]
        # top 3: 9+8+7 = 24
        # unkept: [6, 5, 4, 3], bottom 4: all of them = [6, 5, 4, 3]
        # total: 24 + 6 + 5 + 4 + 3 = 42 (sum of all dice)
        self.assertEqual(42, roll.roll())

    def test_extra_lowest_exceeds_unkept(self):
        test_dice = TestDice()
        test_dice.extend([3, 5, 7, 8])
        roll = NinjaDamageKeepRoll(4, 3, extra_lowest=4, die_provider=test_dice)
        # sorted desc: [8, 7, 5, 3]
        # top 3: 8+7+5 = 20
        # unkept: [3], bottom 4 but only 1 available: [3]
        # total: 20 + 3 = 23 (sum of all dice)
        self.assertEqual(23, roll.roll())


class TestNinjaCharacterAttributes(unittest.TestCase):
    """Tests for attack_rolled_penalty and damage_reroll_reduction on Character."""

    def test_attack_rolled_penalty_default(self):
        character = Character("ninja")
        self.assertEqual(0, character.attack_rolled_penalty())

    def test_set_attack_rolled_penalty(self):
        character = Character("ninja")
        character.set_attack_rolled_penalty(1)
        self.assertEqual(1, character.attack_rolled_penalty())
        character.set_attack_rolled_penalty(2)
        self.assertEqual(2, character.attack_rolled_penalty())

    def test_damage_reroll_reduction_default(self):
        character = Character("ninja")
        self.assertEqual(0, character.damage_reroll_reduction())

    def test_set_damage_reroll_reduction(self):
        character = Character("ninja")
        character.set_damage_reroll_reduction(1)
        self.assertEqual(1, character.damage_reroll_reduction())
        character.set_damage_reroll_reduction(2)
        self.assertEqual(2, character.damage_reroll_reduction())


class TestNinjaAttackPenaltyInRollParams(unittest.TestCase):
    """Test that attack_rolled_penalty reduces attacker's rolled dice."""

    def test_no_penalty(self):
        attacker = Character("attacker")
        attacker.set_ring("fire", 3)
        attacker.set_skill("attack", 3)
        target = Character("ninja")
        # attacker rolls 6k3 on attack
        rolled, kept, mod = attacker.get_skill_roll_params(target, "attack")
        self.assertEqual(6, rolled)

    def test_penalty_one(self):
        attacker = Character("attacker")
        attacker.set_ring("fire", 3)
        attacker.set_skill("attack", 3)
        target = Character("ninja")
        target.set_attack_rolled_penalty(1)
        # attacker should roll 5k3 instead of 6k3
        rolled, kept, mod = attacker.get_skill_roll_params(target, "attack")
        self.assertEqual(5, rolled)

    def test_penalty_two(self):
        attacker = Character("attacker")
        attacker.set_ring("fire", 3)
        attacker.set_skill("attack", 3)
        target = Character("ninja")
        target.set_attack_rolled_penalty(2)
        # attacker should roll 4k3 instead of 6k3
        rolled, kept, mod = attacker.get_skill_roll_params(target, "attack")
        self.assertEqual(4, rolled)

    def test_penalty_capped_at_fire_ring(self):
        attacker = Character("attacker")
        attacker.set_ring("fire", 3)
        attacker.set_skill("attack", 3)
        target = Character("ninja")
        target.set_attack_rolled_penalty(5)
        # penalty 5 would give 1, but min is fire ring (3)
        rolled, kept, mod = attacker.get_skill_roll_params(target, "attack")
        self.assertEqual(3, rolled)

    def test_penalty_does_not_apply_to_non_attack(self):
        attacker = Character("attacker")
        attacker.set_ring("fire", 3)
        attacker.set_ring("air", 3)
        attacker.set_skill("parry", 3)
        target = Character("ninja")
        target.set_attack_rolled_penalty(2)
        # parry is not an attack skill, no penalty applied
        rolled, kept, mod = attacker.get_skill_roll_params(target, "parry")
        self.assertEqual(6, rolled)


class TestNinjaDefenseBonusAbility(unittest.TestCase):
    """Tests for the defense bonus ability (+5 TN to hit)."""

    def test_tn_to_hit_level_one(self):
        ninja = Character("ninja")
        ninja.set_skill("parry", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(DEFENSE_BONUS)
        ability = get_profession_ability(DEFENSE_BONUS)
        ability.apply(ninja, ninja.profession())
        # base TN = 5*(1+3) = 20, +5 from defense bonus = 25
        self.assertEqual(25, ninja.tn_to_hit())

    def test_tn_to_hit_level_two(self):
        ninja = Character("ninja")
        ninja.set_skill("parry", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(DEFENSE_BONUS)
        ninja.profession().take_ability(DEFENSE_BONUS)
        ability = get_profession_ability(DEFENSE_BONUS)
        ability.apply(ninja, ninja.profession())
        # base TN = 20, +10 from defense bonus = 30
        self.assertEqual(30, ninja.tn_to_hit())


class TestNinjaDefenseBonusDamageListener(unittest.TestCase):
    """Tests for the defense bonus damage listener (+1 rolled damage die to attacker)."""

    def setUp(self):
        attacker = Character("attacker")
        attacker.set_ring("fire", 4)
        attacker.set_skill("attack", 4)
        ninja = Character("ninja")
        ninja.set_skill("parry", 4)
        ninja.set_profession(Profession())
        groups = [Group("ninja", ninja), Group("attackers", attacker)]
        context = EngineContext(groups)
        self.attacker = attacker
        self.ninja = ninja
        self.context = context
        self.initiative_action = InitiativeAction([1], 1)

    def test_extra_damage_triggered(self):
        self.ninja.profession().take_ability(DEFENSE_BONUS)
        ability = get_profession_ability(DEFENSE_BONUS)
        ability.apply(self.ninja, self.ninja.profession())
        # Set up attack that hit with extra damage dice
        attack = AttackAction(self.attacker, self.ninja, "attack", self.initiative_action, self.context)
        attack.set_skill_roll(35)  # exceeds TN by at least 5
        event = AttackSucceededEvent(attack)
        # check initial extra_rolled
        initial_extra = self.attacker.extra_rolled("damage")
        responses = list(self.ninja.event(event, self.context))
        # Attacker should have extra_rolled("damage") incremented by 1
        self.assertEqual(initial_extra + 1, self.attacker.extra_rolled("damage"))
        # Should yield AddModifierEvent
        self.assertTrue(len(responses) > 0)

    def test_no_extra_damage_when_no_extra_dice(self):
        self.ninja.profession().take_ability(DEFENSE_BONUS)
        ability = get_profession_ability(DEFENSE_BONUS)
        ability.apply(self.ninja, self.ninja.profession())
        # Attack that exactly hits (no extra damage dice)
        attack = AttackAction(self.attacker, self.ninja, "attack", self.initiative_action, self.context)
        attack.set_skill_roll(25)  # TN to hit is 25, so 0 extra dice
        event = AttackSucceededEvent(attack)
        initial_extra = self.attacker.extra_rolled("damage")
        responses = list(self.ninja.event(event, self.context))
        # No change to attacker's extra_rolled
        self.assertEqual(initial_extra, self.attacker.extra_rolled("damage"))
        self.assertEqual(0, len(responses))


class TestNinjaAttackBonusAbility(unittest.TestCase):
    """Tests for the attack bonus ability (add fire ring to attack rolls)."""

    def test_attack_modifier_level_one(self):
        ninja = Character("ninja")
        ninja.set_ring("fire", 4)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(ATTACK_BONUS)
        ability = get_profession_ability(ATTACK_BONUS)
        ability.apply(ninja, ninja.profession())
        target = Character("target")
        # modifier should be fire ring * 1 = 4
        mod = ninja.modifier(target, "attack")
        self.assertEqual(4, mod)

    def test_attack_modifier_level_two(self):
        ninja = Character("ninja")
        ninja.set_ring("fire", 4)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(ATTACK_BONUS)
        ninja.profession().take_ability(ATTACK_BONUS)
        ability = get_profession_ability(ATTACK_BONUS)
        ability.apply(ninja, ninja.profession())
        target = Character("target")
        # modifier should be fire ring * 2 = 8
        mod = ninja.modifier(target, "attack")
        self.assertEqual(8, mod)

    def test_applies_to_all_attack_skills(self):
        ninja = Character("ninja")
        ninja.set_ring("fire", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(ATTACK_BONUS)
        ability = get_profession_ability(ATTACK_BONUS)
        ability.apply(ninja, ninja.profession())
        target = Character("target")
        for skill in ["attack", "counterattack", "double attack", "feint", "iaijutsu", "lunge"]:
            mod = ninja.modifier(target, skill)
            self.assertEqual(3, mod, f"Expected 3 for {skill}")

    def test_does_not_apply_to_parry(self):
        ninja = Character("ninja")
        ninja.set_ring("fire", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(ATTACK_BONUS)
        ability = get_profession_ability(ATTACK_BONUS)
        ability.apply(ninja, ninja.profession())
        target = Character("target")
        self.assertEqual(0, ninja.modifier(target, "parry"))


class TestNinjaAttackPenaltyAbility(unittest.TestCase):
    """Tests for the attack penalty ability."""

    def test_level_one(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(ATTACK_PENALTY)
        ability = get_profession_ability(ATTACK_PENALTY)
        ability.apply(ninja, ninja.profession())
        self.assertEqual(1, ninja.attack_rolled_penalty())

    def test_level_two(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(ATTACK_PENALTY)
        ninja.profession().take_ability(ATTACK_PENALTY)
        ability = get_profession_ability(ATTACK_PENALTY)
        ability.apply(ninja, ninja.profession())
        self.assertEqual(2, ninja.attack_rolled_penalty())


class TestNinjaDamageReductionAbility(unittest.TestCase):
    """Tests for the damage reduction ability."""

    def test_level_one(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(DAMAGE_REDUCTION)
        ability = get_profession_ability(DAMAGE_REDUCTION)
        ability.apply(ninja, ninja.profession())
        self.assertEqual(1, ninja.damage_reroll_reduction())

    def test_level_two(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(DAMAGE_REDUCTION)
        ninja.profession().take_ability(DAMAGE_REDUCTION)
        ability = get_profession_ability(DAMAGE_REDUCTION)
        ability.apply(ninja, ninja.profession())
        self.assertEqual(2, ninja.damage_reroll_reduction())


class TestNinjaInitiativeReductionAbility(unittest.TestCase):
    """Tests for the initiative reduction ability."""

    def test_level_one(self):
        ninja = Character("ninja")
        ninja.set_ring("void", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(INITIATIVE_REDUCTION)
        ability = get_profession_ability(INITIATIVE_REDUCTION)
        ability.apply(ninja, ninja.profession())
        # Set up a rigged initiative roll
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([3, 5, 7])
        ninja.set_roll_provider(roll_provider)
        dummy = Character("dummy")
        groups = [Group("ninja", ninja), Group("dummy", dummy)]
        context = EngineContext(groups)
        event = NewRoundEvent(1)
        list(ninja.event(event, context))
        # Actions should be reduced by 2: [3-2, 5-2, 7-2] = [1, 3, 5]
        self.assertEqual([1, 3, 5], ninja.actions())

    def test_level_two(self):
        ninja = Character("ninja")
        ninja.set_ring("void", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(INITIATIVE_REDUCTION)
        ninja.profession().take_ability(INITIATIVE_REDUCTION)
        ability = get_profession_ability(INITIATIVE_REDUCTION)
        ability.apply(ninja, ninja.profession())
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([3, 5, 7])
        ninja.set_roll_provider(roll_provider)
        dummy = Character("dummy")
        groups = [Group("ninja", ninja), Group("dummy", dummy)]
        context = EngineContext(groups)
        event = NewRoundEvent(1)
        list(ninja.event(event, context))
        # Actions should be reduced by 4: [max(1,3-4), max(1,5-4), max(1,7-4)] = [1, 1, 3]
        self.assertEqual([1, 1, 3], ninja.actions())

    def test_minimum_one(self):
        ninja = Character("ninja")
        ninja.set_ring("void", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(INITIATIVE_REDUCTION)
        ability = get_profession_ability(INITIATIVE_REDUCTION)
        ability.apply(ninja, ninja.profession())
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([1, 2, 3])
        ninja.set_roll_provider(roll_provider)
        dummy = Character("dummy")
        groups = [Group("ninja", ninja), Group("dummy", dummy)]
        context = EngineContext(groups)
        event = NewRoundEvent(1)
        list(ninja.event(event, context))
        # [max(1,1-2), max(1,2-2), max(1,3-2)] = [1, 1, 1]
        self.assertEqual([1, 1, 1], ninja.actions())


class TestNinjaDamageKeepingBonusAbility(unittest.TestCase):
    """Tests for the damage keeping bonus ability."""

    def test_level_one(self):
        ninja = Character("ninja")
        ninja.set_ring("fire", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(DAMAGE_KEEPING_BONUS)
        ability = get_profession_ability(DAMAGE_KEEPING_BONUS)
        ability.apply(ninja, ninja.profession())
        # Rig damage roll with test dice
        test_dice = TestDice()
        provider = NinjaRollProvider(ninja.profession(), die_provider=test_dice)
        ninja.set_roll_provider(provider)
        # Roll 6k2 with extra_lowest=2
        # dice: [9, 8, 7, 6, 5, 3]
        test_dice.extend([3, 5, 7, 8, 9, 6])
        result = provider.get_damage_roll(6, 2)
        # top 2: 9+8 = 17, bottom 2 of unkept [7,6,5,3]: [5,3]
        # total: 17 + 5 + 3 = 25
        self.assertEqual(25, result)

    def test_level_two(self):
        ninja = Character("ninja")
        ninja.set_ring("fire", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(DAMAGE_KEEPING_BONUS)
        ninja.profession().take_ability(DAMAGE_KEEPING_BONUS)
        ability = get_profession_ability(DAMAGE_KEEPING_BONUS)
        ability.apply(ninja, ninja.profession())
        test_dice = TestDice()
        provider = NinjaRollProvider(ninja.profession(), die_provider=test_dice)
        ninja.set_roll_provider(provider)
        # Roll 6k2 with extra_lowest=4
        test_dice.extend([3, 5, 7, 8, 9, 6])
        result = provider.get_damage_roll(6, 2)
        # top 2: 9+8 = 17, all unkept [7,6,5,3] bottom 4: [7,6,5,3]
        # total: 17 + 7 + 6 + 5 + 3 = 38
        self.assertEqual(38, result)


class TestNinjaWoundCheckBonusAbility(unittest.TestCase):
    """Tests for the wound check ninja bonus ability."""

    def test_level_one(self):
        ninja = Character("ninja")
        ninja.set_ring("water", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(WOUND_CHECK_NINJA_BONUS)
        ability = get_profession_ability(WOUND_CHECK_NINJA_BONUS)
        ability.apply(ninja, ninja.profession())
        test_dice = TestDice()
        provider = NinjaRollProvider(ninja.profession(), die_provider=test_dice)
        ninja.set_roll_provider(provider)
        # Roll wound check 4k3
        # dice: [1, 2, 8, 3]
        # adjusted: [5, 5, 8, 5], sorted: [8, 5, 5, 5]
        # top 3: 8+5+5 = 18
        test_dice.extend([1, 2, 8, 3])
        result = provider.get_wound_check_roll(4, 3)
        self.assertEqual(18, result)

    def test_level_two(self):
        ninja = Character("ninja")
        ninja.set_ring("water", 3)
        ninja.set_profession(Profession())
        ninja.profession().take_ability(WOUND_CHECK_NINJA_BONUS)
        ninja.profession().take_ability(WOUND_CHECK_NINJA_BONUS)
        ability = get_profession_ability(WOUND_CHECK_NINJA_BONUS)
        ability.apply(ninja, ninja.profession())
        test_dice = TestDice()
        provider = NinjaRollProvider(ninja.profession(), die_provider=test_dice)
        ninja.set_roll_provider(provider)
        # Roll wound check 4k3
        # dice: [1, 2, 8, 3]
        # level 2: 1 -> 1+2*(5-1)=9, 2 -> 2+2*(5-2)=8, 3 -> 3+2*(5-3)=7
        # adjusted: [9, 8, 8, 7], sorted: [9, 8, 8, 7]
        # top 3: 9+8+8 = 25
        test_dice.extend([1, 2, 8, 3])
        result = provider.get_wound_check_roll(4, 3)
        self.assertEqual(25, result)


class TestNinjaSincerityBonusAbility(unittest.TestCase):
    """Tests for the sincerity bonus ability."""

    def test_level_one(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(SINCERITY_BONUS)
        ability = get_profession_ability(SINCERITY_BONUS)
        ability.apply(ninja, ninja.profession())
        # Should have 4 free raises on sincerity = +20 modifier
        mod = ninja.modifier(None, "sincerity")
        self.assertEqual(20, mod)

    def test_level_two(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(SINCERITY_BONUS)
        ability = get_profession_ability(SINCERITY_BONUS)
        ability.apply(ninja, ninja.profession())
        ninja.profession().take_ability(SINCERITY_BONUS)
        ability.apply(ninja, ninja.profession())
        # Level 1 adds 4, level 2 adds 4 more = 8 free raises = +40
        mod = ninja.modifier(None, "sincerity")
        self.assertEqual(40, mod)


class TestNinjaStealthAbilities(unittest.TestCase):
    """Tests for the stealth abilities."""

    def test_stealth_invisibility_level_one(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(STEALTH_INVISIBILITY)
        ability = get_profession_ability(STEALTH_INVISIBILITY)
        ability.apply(ninja, ninja.profession())
        # 4 free raises on sneaking = +20
        mod = ninja.modifier(None, "sneaking")
        self.assertEqual(20, mod)

    def test_stealth_memorability_level_one(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(STEALTH_MEMORABILITY)
        ability = get_profession_ability(STEALTH_MEMORABILITY)
        ability.apply(ninja, ninja.profession())
        # 4 free raises on sneaking = +20
        mod = ninja.modifier(None, "sneaking")
        self.assertEqual(20, mod)

    def test_both_stealth_abilities(self):
        ninja = Character("ninja")
        ninja.set_profession(Profession())
        ninja.profession().take_ability(STEALTH_INVISIBILITY)
        invisibility = get_profession_ability(STEALTH_INVISIBILITY)
        invisibility.apply(ninja, ninja.profession())
        ninja.profession().take_ability(STEALTH_MEMORABILITY)
        memorability = get_profession_ability(STEALTH_MEMORABILITY)
        memorability.apply(ninja, ninja.profession())
        # 4+4 = 8 free raises on sneaking = +40
        mod = ninja.modifier(None, "sneaking")
        self.assertEqual(40, mod)


class TestNinjaRollProvider(unittest.TestCase):
    """Tests for the NinjaRollProvider class."""

    def test_normal_damage_roll_without_keeping_bonus(self):
        profession = Profession()
        test_dice = TestDice()
        provider = NinjaRollProvider(profession, die_provider=test_dice)
        # No keeping bonus ability, should behave like normal
        test_dice.extend([3, 5, 7, 8, 9, 6])
        result = provider.get_damage_roll(6, 2)
        # top 2: 9+8 = 17
        self.assertEqual(17, result)

    def test_normal_wound_check_without_bonus(self):
        profession = Profession()
        test_dice = TestDice()
        provider = NinjaRollProvider(profession, die_provider=test_dice)
        # No wound check bonus, should behave like normal
        test_dice.extend([3, 5, 7, 8])
        result = provider.get_wound_check_roll(4, 2)
        # top 2: 8+7 = 15
        self.assertEqual(15, result)


class TestGetProfessionAbility(unittest.TestCase):
    """Test that all ninja ability names work with the factory."""

    def test_all_ninja_abilities_exist(self):
        ninja_abilities = [
            ATTACK_BONUS, ATTACK_PENALTY, DAMAGE_KEEPING_BONUS,
            DAMAGE_REDUCTION, DEFENSE_BONUS, INITIATIVE_REDUCTION,
            SINCERITY_BONUS, STEALTH_INVISIBILITY, STEALTH_MEMORABILITY,
            WOUND_CHECK_NINJA_BONUS,
        ]
        for name in ninja_abilities:
            ability = get_profession_ability(name)
            self.assertIsNotNone(ability)
