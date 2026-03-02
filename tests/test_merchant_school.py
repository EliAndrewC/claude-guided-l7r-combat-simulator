#!/usr/bin/env python3

#
# test_merchant_school.py
#
# Unit tests for the Merchant School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.actions import AttackAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll import CalvinistDice
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.optimizers.attack_optimizer_factory import AttackOptimizerFactory
from simulation.schools import merchant_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestMerchantSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual("Merchant School", school.name())

    def test_extra_rolled(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["interrogation", "sincerity", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["discern honor", "oppose knowledge", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["interrogation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual("sincerity", school.ap_base_skill())

    def test_ap_skills(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["commerce", "heraldry", "interrogation", "sincerity", "attack", "wound check"], school.ap_skills())


class TestMerchantAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        merchant = Character("Merchant")
        merchant.set_skill("sincerity", 5)
        school = merchant_school.MerchantSchool()
        school.apply_rank_three_ability(merchant)
        self.assertEqual("sincerity", merchant.ap_base_skill())
        self.assertTrue(merchant.can_spend_ap("attack"))
        self.assertTrue(merchant.can_spend_ap("wound check"))
        self.assertFalse(merchant.can_spend_ap("parry"))
        # AP = 2 * sincerity skill = 10
        self.assertEqual(10, merchant.ap())

    def test_ap_with_lower_skill(self):
        merchant = Character("Merchant")
        merchant.set_skill("sincerity", 2)
        school = merchant_school.MerchantSchool()
        school.apply_rank_three_ability(merchant)
        # AP = 2 * 2 = 4
        self.assertEqual(4, merchant.ap())


class TestMerchantFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        merchant = Character("Merchant")
        merchant.set_ring("water", 3)
        school = merchant_school.MerchantSchool()
        school.apply_rank_four_ability(merchant)
        # Ring raise: water should be +1
        self.assertEqual(4, merchant.ring("water"))


# ---------------------------------------------------------------
# Special Ability Tests: VP spending after initial roll
# ---------------------------------------------------------------

def _make_context(attacker, target):
    """Helper to create a minimal EngineContext for testing."""
    groups = [Group("A", attacker), Group("B", target)]
    context = EngineContext(groups, round=1, phase=1)
    context.initialize()
    return context


def _make_attack_action(attacker, target, context, skill_roll=None, vp=0):
    """Helper to create an AttackAction and optionally set its skill roll."""
    ia = InitiativeAction([1], 1)
    action = AttackAction(attacker, target, "attack", ia, context, vp=vp)
    if skill_roll is not None:
        action.set_skill_roll(skill_roll)
    return action


class TestMerchantOptimizerNoVPPreallocation(unittest.TestCase):
    """Verify the Merchant optimizer always passes max_vp=0."""

    def test_merchant_optimizer_no_vp_preallocation(self):
        merchant = Character("Merchant")
        merchant.set_ring("fire", 3)
        merchant.set_ring("void", 3)
        merchant.set_skill("attack", 3)
        merchant.set_actions([1])
        target = Character("Target")
        target.set_skill("parry", 3)
        merchant.knowledge().observe_tn_to_hit(target, target.tn_to_hit())
        school = merchant_school.MerchantSchool()
        school.apply_special_ability(merchant)
        # The Merchant's optimizer factory should be a MerchantAttackOptimizerFactory
        factory = merchant.attack_optimizer_factory()
        self.assertIsInstance(factory, merchant_school.MerchantAttackOptimizerFactory)
        self.assertIsInstance(factory, AttackOptimizerFactory)
        # Get an optimizer and verify it uses max_vp=0
        context = _make_context(merchant, target)
        ia = InitiativeAction([1], 1)
        optimizer = factory.get_optimizer(merchant, target, "attack", ia, context)
        self.assertEqual(0, optimizer.max_vp)


class TestMerchantAttackRolledSpendsVP(unittest.TestCase):
    """After the base strategy runs, if the roll still misses and the
    character has VP, spend VP post-roll adding +5 per VP."""

    def test_merchant_attack_rolled_spends_vp_when_roll_misses(self):
        merchant = Character("Merchant")
        merchant.set_ring("fire", 3)
        merchant.set_ring("void", 3)  # 3 VP available
        merchant.set_skill("attack", 3)
        merchant.set_actions([1])
        target = Character("Target")
        target.set_skill("parry", 4)  # TN = 5 * (1+4) = 25
        context = _make_context(merchant, target)
        school = merchant_school.MerchantSchool()
        school.apply_special_ability(merchant)
        # Create an attack that misses by 3: roll 22, TN 25
        action = _make_attack_action(merchant, target, context, skill_roll=22)
        event = events.AttackRolledEvent(action, 22)
        # Run the merchant's attack rolled strategy
        strategy = merchant.attack_rolled_strategy()
        result_events = list(strategy.recommend(merchant, event, context))
        # Should have spent 1 VP (which adds +5, enough to close the gap of 3)
        vp_events = [e for e in result_events if isinstance(e, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(vp_events))
        self.assertEqual(1, vp_events[0].amount)
        # The rolled event should show an improved roll
        rolled_events = [e for e in result_events if isinstance(e, events.AttackRolledEvent)]
        self.assertEqual(1, len(rolled_events))
        self.assertEqual(27, rolled_events[0].roll)  # 22 + 5 = 27

    def test_merchant_attack_rolled_no_vp_when_hits(self):
        merchant = Character("Merchant")
        merchant.set_ring("fire", 3)
        merchant.set_ring("void", 3)  # 3 VP available
        merchant.set_skill("attack", 3)
        merchant.set_actions([1])
        target = Character("Target")
        target.set_skill("parry", 4)  # TN = 25
        context = _make_context(merchant, target)
        school = merchant_school.MerchantSchool()
        school.apply_special_ability(merchant)
        # Create an attack that hits: roll 30, TN 25
        action = _make_attack_action(merchant, target, context, skill_roll=30)
        event = events.AttackRolledEvent(action, 30)
        strategy = merchant.attack_rolled_strategy()
        result_events = list(strategy.recommend(merchant, event, context))
        # Should NOT have spent VP since the roll already hits
        vp_events = [e for e in result_events if isinstance(e, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(vp_events))
        # Should still yield the event
        rolled_events = [e for e in result_events if isinstance(e, events.AttackRolledEvent)]
        self.assertEqual(1, len(rolled_events))
        self.assertEqual(30, rolled_events[0].roll)

    def test_merchant_attack_rolled_spends_multiple_vp(self):
        """If the miss margin is large, spend more VP."""
        merchant = Character("Merchant")
        merchant.set_ring("fire", 3)
        merchant.set_ring("void", 3)  # 3 VP available
        merchant.set_skill("attack", 3)
        merchant.set_actions([1])
        target = Character("Target")
        target.set_skill("parry", 4)  # TN = 25
        context = _make_context(merchant, target)
        school = merchant_school.MerchantSchool()
        school.apply_special_ability(merchant)
        # Miss by 8: roll 17, TN 25 -> need 2 VP (+10) to close gap
        action = _make_attack_action(merchant, target, context, skill_roll=17)
        event = events.AttackRolledEvent(action, 17)
        strategy = merchant.attack_rolled_strategy()
        result_events = list(strategy.recommend(merchant, event, context))
        vp_events = [e for e in result_events if isinstance(e, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(vp_events))
        self.assertEqual(2, vp_events[0].amount)
        rolled_events = [e for e in result_events if isinstance(e, events.AttackRolledEvent)]
        self.assertEqual(1, len(rolled_events))
        self.assertEqual(27, rolled_events[0].roll)  # 17 + 10 = 27


class TestMerchantWoundCheckNoVPPreallocation(unittest.TestCase):
    """The Merchant wound check strategy should never pre-allocate VP."""

    def test_merchant_wound_check_no_vp_preallocation(self):
        merchant = Character("Merchant")
        merchant.set_ring("void", 3)  # 3 VP available
        merchant.set_ring("water", 3)
        attacker = Character("Attacker")
        context = _make_context(attacker, merchant)
        school = merchant_school.MerchantSchool()
        school.apply_special_ability(merchant)
        # Simulate taking 15 LW damage
        merchant.take_lw(15)
        lw_event = events.LightWoundsDamageEvent(attacker, merchant, 15)
        strategy = merchant.wound_check_strategy()
        result_events = list(strategy.recommend(merchant, lw_event, context))
        # Should yield a WoundCheckDeclaredEvent with vp=0
        declared_events = [e for e in result_events if isinstance(e, events.WoundCheckDeclaredEvent)]
        self.assertEqual(1, len(declared_events))
        self.assertEqual(0, declared_events[0].vp)


class TestMerchantWoundCheckRolledSpendsVP(unittest.TestCase):
    """After base resource spending, if wound check still bad and VP
    is available, spend VP post-roll adding +5 per VP."""

    def test_merchant_wound_check_rolled_spends_vp_when_needed(self):
        merchant = Character("Merchant")
        merchant.set_ring("void", 3)  # 3 VP available
        merchant.set_ring("earth", 2)  # SW thresholds at multiples of 20 (earth*10)
        merchant.set_ring("water", 3)
        attacker = Character("Attacker")
        context = _make_context(attacker, merchant)
        school = merchant_school.MerchantSchool()
        school.apply_special_ability(merchant)
        # Give merchant 30 LW
        merchant.take_lw(30)
        # With earth 2, lw 30:
        #   wound_check(15) = 2 SW (bad: > tolerable 1)
        #   wound_check(25) = 1 SW (tolerable)
        # So spending 2 VP (+10) should bring roll from 15 to 25
        wc_event = events.WoundCheckRolledEvent(merchant, attacker, 30, 15, tn=30)
        strategy = merchant.wound_check_rolled_strategy()
        result_events = list(strategy.recommend(merchant, wc_event, context))
        # Should have spent VP to improve the roll
        vp_events = [e for e in result_events if isinstance(e, events.SpendVoidPointsEvent)]
        self.assertTrue(len(vp_events) > 0)
        self.assertEqual(2, vp_events[0].amount)
        # The improved roll should be better
        rolled_events = [e for e in result_events if isinstance(e, events.WoundCheckRolledEvent)]
        self.assertEqual(1, len(rolled_events))
        self.assertEqual(25, rolled_events[0].roll)

    def test_merchant_wound_check_rolled_no_vp_when_ok(self):
        """If the wound check is already passing or tolerable, don't spend VP."""
        merchant = Character("Merchant")
        merchant.set_ring("void", 3)
        merchant.set_ring("earth", 3)
        merchant.set_ring("water", 3)
        attacker = Character("Attacker")
        context = _make_context(attacker, merchant)
        school = merchant_school.MerchantSchool()
        school.apply_special_ability(merchant)
        merchant.take_lw(20)
        # Roll 25 against 20 LW: wound_check(25) with 20 LW -> 0 SW
        wc_event = events.WoundCheckRolledEvent(merchant, attacker, 20, 25, tn=20)
        strategy = merchant.wound_check_rolled_strategy()
        result_events = list(strategy.recommend(merchant, wc_event, context))
        # Should NOT have spent VP since wound check passes
        vp_events = [e for e in result_events if isinstance(e, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(vp_events))


# ---------------------------------------------------------------
# 5th Dan Tests: Reroll dice
# ---------------------------------------------------------------

class TestMerchantFifthDanRerollSkillDice(unittest.TestCase):
    """After non-initiative roll, reroll dice summing to >= 5*(X-1)."""

    def test_merchant_5th_dan_rerolls_low_die(self):
        """Dice [8, 7, 2] rolled 3 kept 2. Reroll the 2 (1 die, 5*0=0 threshold)
        and get a higher result."""
        merchant = Character("Merchant")
        merchant.set_ring("fire", 3)
        merchant.set_skill("attack", 3)
        school = merchant_school.MerchantSchool()
        # Set up CalvinistRollProvider with dice info
        roll_provider = CalvinistRollProvider()
        # Original roll: total 15, dice [8, 7, 2], rolled 3 kept 2
        roll_provider.put_skill_roll_with_dice("attack", 15, [8, 7, 2])
        merchant.set_roll_provider(roll_provider)
        # Set up CalvinistDice for reroll results
        reroll_dice = CalvinistDice()
        reroll_dice.append(7)  # rerolled die result
        # Apply 5th dan with reroll die provider
        school.apply_rank_five_ability(merchant)
        merchant.roll_provider()._reroll_die_provider = reroll_dice
        # Roll: original kept = sum(top 2 of [8,7,2]) = 15
        # After reroll: dice become [8, 7, 7], kept = sum(top 2) = 15
        # Actually rerolling the 2 and getting 7: [8, 7, 7] -> keep 2 = 15
        # With a better example: reroll the 2 and get 9
        reroll_dice.clear()
        reroll_dice.append(9)
        roll_provider.put_skill_roll_with_dice("attack", 15, [8, 7, 2])
        result = merchant.roll_provider().get_skill_roll("attack", 3, 2)
        # New dice: [9, 8, 7], keep top 2 = 17
        self.assertEqual(17, result)

    def test_merchant_5th_dan_no_reroll_when_all_high(self):
        """Dice [9, 8, 7], all high. Rerolling any single die costs >= the die's
        value and the expected gain is negative, so no reroll."""
        merchant = Character("Merchant")
        merchant.set_ring("fire", 3)
        merchant.set_skill("attack", 3)
        school = merchant_school.MerchantSchool()
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll_with_dice("attack", 17, [9, 8, 7])
        merchant.set_roll_provider(roll_provider)
        reroll_dice = CalvinistDice()
        school.apply_rank_five_ability(merchant)
        merchant.roll_provider()._reroll_die_provider = reroll_dice
        # All dice are high (> 5.5 expected), so no reroll should happen
        result = merchant.roll_provider().get_skill_roll("attack", 3, 2)
        # No reroll: kept top 2 of [9, 8, 7] = 17
        self.assertEqual(17, result)
        # CalvinistDice should not have been consumed
        self.assertEqual(0, len(reroll_dice))

    def test_merchant_5th_dan_reroll_multiple_dice(self):
        """Dice [8, 3, 2] rolled 3 kept 2. Reroll [3, 2] (2 dice, sum=5 >= 5*(2-1)=5)."""
        merchant = Character("Merchant")
        merchant.set_ring("fire", 3)
        merchant.set_skill("attack", 3)
        school = merchant_school.MerchantSchool()
        roll_provider = CalvinistRollProvider()
        # Original: dice [8, 3, 2], rolled 3, kept 2, total = 8+3 = 11
        roll_provider.put_skill_roll_with_dice("attack", 11, [8, 3, 2])
        merchant.set_roll_provider(roll_provider)
        reroll_dice = CalvinistDice()
        reroll_dice.extend([7, 6])  # reroll results for the 2 dice
        school.apply_rank_five_ability(merchant)
        merchant.roll_provider()._reroll_die_provider = reroll_dice
        result = merchant.roll_provider().get_skill_roll("attack", 3, 2)
        # New dice: [8, 7, 6], keep top 2 = 15
        self.assertEqual(15, result)

    def test_merchant_5th_dan_no_reroll_on_initiative(self):
        """Initiative rolls should NOT be rerolled."""
        merchant = Character("Merchant")
        school = merchant_school.MerchantSchool()
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([2, 5, 8])
        merchant.set_roll_provider(roll_provider)
        school.apply_rank_five_ability(merchant)
        result = merchant.roll_provider().get_initiative_roll(4, 3)
        # Initiative is passed through unchanged
        self.assertEqual([2, 5, 8], result)

    def test_merchant_5th_dan_reroll_on_wound_check(self):
        """Wound check dice should also be rerolled."""
        merchant = Character("Merchant")
        merchant.set_ring("water", 3)
        school = merchant_school.MerchantSchool()
        roll_provider = CalvinistRollProvider()
        # Wound check: dice [8, 6, 1], rolled 3 kept 2, total = 14
        roll_provider.put_wound_check_roll_with_dice(14, [8, 6, 1])
        merchant.set_roll_provider(roll_provider)
        reroll_dice = CalvinistDice()
        reroll_dice.append(9)  # reroll the 1
        school.apply_rank_five_ability(merchant)
        merchant.roll_provider()._reroll_die_provider = reroll_dice
        result = merchant.roll_provider().get_wound_check_roll(3, 2)
        # New dice: [9, 8, 6], keep top 2 = 17
        self.assertEqual(17, result)

    def test_merchant_5th_dan_reroll_on_damage(self):
        """Damage dice should also be rerolled."""
        merchant = Character("Merchant")
        school = merchant_school.MerchantSchool()
        roll_provider = CalvinistRollProvider()
        # Damage: dice [7, 6, 1], rolled 3 kept 2, total = 13
        roll_provider.put_damage_roll_with_dice(13, [7, 6, 1])
        merchant.set_roll_provider(roll_provider)
        reroll_dice = CalvinistDice()
        reroll_dice.append(8)  # reroll the 1
        school.apply_rank_five_ability(merchant)
        merchant.roll_provider()._reroll_die_provider = reroll_dice
        result = merchant.roll_provider().get_damage_roll(3, 2)
        # New dice: [8, 7, 6], keep top 2 = 15
        self.assertEqual(15, result)

    def test_merchant_5th_dan_reroll_constraint_respected(self):
        """When rerolling X dice, their sum must be >= 5*(X-1).
        Dice [8, 2, 1]: sum of [2, 1] = 3 < 5*(2-1)=5, so can't reroll both.
        But can reroll [1] since sum=1 >= 5*(1-1)=0."""
        merchant = Character("Merchant")
        school = merchant_school.MerchantSchool()
        roll_provider = CalvinistRollProvider()
        # dice [8, 2, 1], rolled 3 kept 2, total = 10
        roll_provider.put_skill_roll_with_dice("attack", 10, [8, 2, 1])
        merchant.set_roll_provider(roll_provider)
        reroll_dice = CalvinistDice()
        reroll_dice.append(6)  # only 1 reroll should happen (the 1)
        school.apply_rank_five_ability(merchant)
        merchant.roll_provider()._reroll_die_provider = reroll_dice
        result = merchant.roll_provider().get_skill_roll("attack", 3, 2)
        # New dice: [8, 6, 2], keep top 2 = 14
        self.assertEqual(14, result)
        # Exactly 1 reroll die should have been consumed
        self.assertEqual(0, len(reroll_dice))


class TestMerchantFifthDanRerollAlgorithm(unittest.TestCase):
    """Test the reroll algorithm directly."""

    def test_single_die_always_rerollable(self):
        """A single die always meets the 5*(1-1)=0 constraint."""
        # [8, 7, 3] kept 2: reroll the 3 since 3 >= 0 and 5.5 > 3
        result = merchant_school._find_dice_to_reroll([8, 7, 3], 2)
        self.assertEqual([2], result)  # index 2 is the die value 3

    def test_no_reroll_when_not_beneficial(self):
        """Dice [9, 8, 7] kept 2: all dice > 5.5, no reroll."""
        result = merchant_school._find_dice_to_reroll([9, 8, 7], 2)
        self.assertEqual([], result)

    def test_two_dice_reroll(self):
        """[8, 3, 2] kept 2: reroll [3, 2] since sum=5 >= 5*(2-1)=5
        and expected improvement is positive."""
        result = merchant_school._find_dice_to_reroll([8, 3, 2], 2)
        self.assertEqual([1, 2], result)

    def test_constraint_blocks_multi_reroll(self):
        """[8, 2, 1] kept 2: can't reroll [2, 1] since 3 < 5.
        Can only reroll [1]."""
        result = merchant_school._find_dice_to_reroll([8, 2, 1], 2)
        self.assertEqual([2], result)

    def test_all_dice_low_reroll_all(self):
        """[3, 3, 3] kept 2: sum of all 3 = 9 >= 5*(3-1)=10? No, 9 < 10.
        Try 2 dice: sum of [3, 3] = 6 >= 5*(2-1)=5. Expected: 2*5.5=11 > 6. Yes.
        Try 3 dice: 9 < 10, constraint not met.
        Best is 2 dice."""
        result = merchant_school._find_dice_to_reroll([3, 3, 3], 2)
        self.assertEqual([1, 2], result)


if __name__ == "__main__":
    unittest.main()
