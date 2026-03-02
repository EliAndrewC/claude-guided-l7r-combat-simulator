#!/usr/bin/env python3

#
# merchant_school.py
#
# Implement Merchant School.
#
# School Ring: Water
# School Knacks: discern honor, oppose knowledge, worldliness
#
# Special Ability: May spend void points after initial roll.
# 1st Dan: Extra rolled on interrogation, sincerity, wound check
# 2nd Dan: Free raise on interrogation
# 3rd Dan: AP system — ap_base_skill = "sincerity", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; stipend bonus (no-op in combat)
# 5th Dan: After non-initiative roll, reroll dice summing to >= 5*(X-1).
#

import math

from simulation import events
from simulation.log import logger
from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER
from simulation.mechanics.roll_provider import RollProvider
from simulation.optimizers.attack_optimizer_factory import AttackOptimizerFactory
from simulation.optimizers.attack_optimizers import (
    AttackOptimizer,
    DamageOptimizer,
)
from simulation.schools.base import BaseSchool
from simulation.strategies.base import (
    AttackRolledStrategy,
    StingyWoundCheckStrategy,
    WoundCheckRolledStrategy,
)

# ---------------------------------------------------------------
# Special Ability: VP spending after initial roll
# ---------------------------------------------------------------

class MerchantAttackOptimizerFactory(AttackOptimizerFactory):
    """Attack optimizer factory that never pre-allocates VP.

    The Merchant's special ability lets them decide whether to spend VP
    after seeing the roll result, so the optimizer always passes max_vp=0.
    """

    def get_optimizer(self, character, target, skill, initiative_action, context):
        if skill == "feint":
            return AttackOptimizer(
                character, target, skill, initiative_action, context,
                max_vp=0, max_ap=2,
            )
        elif skill == "double attack":
            return DamageOptimizer(
                character, target, skill, initiative_action, context,
                max_vp=0, max_ap=2,
            )
        else:
            return DamageOptimizer(
                character, target, skill, initiative_action, context,
                max_vp=0, max_ap=2,
            )


class MerchantAttackRolledStrategy(AttackRolledStrategy):
    """After the base strategy runs (AP, floating bonuses, conviction),
    if the roll still misses and the character has VP, spend VP post-roll.

    Since +1k1 can't be retroactively added to the dice pool, we add
    a flat +5 per VP spent (conservative approximation of the expected
    value of keeping one additional die).
    """

    def recommend(self, character, event, context):
        # Let the base strategy handle AP, floating bonuses, conviction first
        result_events = list(super().recommend(character, event, context))
        # Find the (possibly updated) AttackRolledEvent from the results
        rolled_event = None
        other_events = []
        for e in result_events:
            if isinstance(e, events.AttackRolledEvent):
                rolled_event = e
            else:
                other_events.append(e)
        if rolled_event is None:
            yield from result_events
            return
        # Check if the roll still misses
        margin = rolled_event.action.tn() - rolled_event.roll
        if margin <= 0:
            # Already hits, yield everything as-is
            yield from result_events
            return
        # Try to spend VP to close the gap
        available_vp = character.vp()
        vp_needed = math.ceil(margin / 5)
        vp_to_spend = min(vp_needed, available_vp)
        if vp_to_spend > 0:
            bonus = vp_to_spend * 5
            new_roll = rolled_event.roll + bonus
            rolled_event.action.set_skill_roll(new_roll)
            new_rolled_event = events.AttackRolledEvent(rolled_event.action, new_roll)
            # Yield base strategy events (AP, bonuses, etc.) first
            yield from other_events
            yield events.SpendVoidPointsEvent(character, rolled_event.action.skill(), vp_to_spend)
            yield new_rolled_event
        else:
            yield from result_events


class MerchantWoundCheckStrategy(StingyWoundCheckStrategy):
    """Wound check strategy that never pre-allocates VP.

    Identical to StingyWoundCheckStrategy: the Merchant decides
    whether to spend VP after seeing the wound check roll.
    """
    pass


class MerchantWoundCheckRolledStrategy(WoundCheckRolledStrategy):
    """After base resource spending on wound check, if the wound check
    is still bad and VP is available, spend VP post-roll adding +5 per VP.
    """

    def recommend(self, character, event, context):
        # Let the base strategy handle floating bonuses, AP, conviction first
        result_events = list(super().recommend(character, event, context))
        # Find the (possibly updated) WoundCheckRolledEvent
        rolled_event = None
        other_events = []
        for e in result_events:
            if isinstance(e, events.WoundCheckRolledEvent):
                rolled_event = e
            else:
                other_events.append(e)
        if rolled_event is None:
            yield from result_events
            return
        # How many SW would result from the current roll?
        expected_sw = character.wound_check(rolled_event.roll)
        if expected_sw == 0:
            # Wound check passes, no need for VP
            yield from result_events
            return
        # Calculate tolerable SW (same logic as base strategy)
        tolerable_sw = min(1, character.sw_remaining() - 1)
        if expected_sw <= tolerable_sw:
            yield from result_events
            return
        # Try spending VP to improve the roll
        available_vp = character.vp()
        if available_vp <= 0:
            yield from result_events
            return
        new_roll = rolled_event.roll
        vp_to_spend = 0
        while vp_to_spend < available_vp:
            vp_to_spend += 1
            new_roll += 5
            new_sw = character.wound_check(new_roll)
            if new_sw <= tolerable_sw:
                break
        # Only spend VP if it improves the outcome
        new_sw = character.wound_check(new_roll)
        if new_sw < expected_sw:
            yield from other_events
            yield events.SpendVoidPointsEvent(character, "wound check", vp_to_spend)
            yield events.WoundCheckRolledEvent(
                rolled_event.subject, rolled_event.attacker,
                rolled_event.damage, new_roll, tn=rolled_event.tn,
            )
        else:
            yield from result_events


# ---------------------------------------------------------------
# 5th Dan: Reroll dice
# ---------------------------------------------------------------

def _find_dice_to_reroll(dice, kept):
    """Find optimal dice indices to reroll.

    Args:
        dice: list of die values sorted descending
        kept: number of dice kept in the roll

    Returns:
        list of indices into dice to reroll (may be empty)

    The rule is: "you may reroll some of the dice so long as the dice
    being rerolled add up to at least 5*(X-1) where X is the number
    of dice being rerolled."

    The algorithm only considers rerolling dice that are individually
    below the expected value of a die (5.5), since rerolling a high
    die to meet the sum constraint would be counterproductive.
    It tries groups of X = 1, 2, ..., N low dice (from lowest up)
    and picks the group that maximizes expected gain.
    """
    # Identify dice below expected value (candidates for reroll)
    # dice is sorted descending, so low dice are at the end
    low_indices = [i for i in range(len(dice)) if dice[i] < 5.5]
    if not low_indices:
        return []

    best_indices = []
    best_expected_gain = 0

    for x in range(1, len(low_indices) + 1):
        # Take the x lowest-value dice from the candidates
        # Since dice are sorted descending, the lowest are at the end
        indices = low_indices[len(low_indices) - x:]
        reroll_values = [dice[i] for i in indices]
        reroll_sum = sum(reroll_values)

        # Check constraint: sum >= 5*(X-1)
        if reroll_sum < 5 * (x - 1):
            continue

        # Check benefit: expected value of x dice at 5.5 each vs current sum
        expected_new = x * 5.5
        expected_gain = expected_new - reroll_sum
        if expected_gain <= 0:
            continue

        if expected_gain > best_expected_gain:
            best_expected_gain = expected_gain
            best_indices = sorted(indices)

    return best_indices


class MerchantRollProvider(RollProvider):
    """Roll provider that wraps an existing provider and adds the
    Merchant 5th Dan reroll ability.

    After any non-initiative roll, finds optimal dice to reroll
    and replaces them with new rolls.
    """

    def __init__(self, inner, reroll_die_provider=None):
        self._inner = inner
        if reroll_die_provider is not None:
            self._reroll_die_provider = reroll_die_provider
        else:
            self._reroll_die_provider = DEFAULT_DIE_PROVIDER

    def die_provider(self):
        return self._inner.die_provider()

    def get_damage_reduction_roll(self, rolled, kept, reduction):
        result = self._inner.get_damage_reduction_roll(rolled, kept, reduction)
        info = self._inner.last_damage_info()
        return self._maybe_reroll(result, info, rolled, kept, "damage")

    def get_damage_roll(self, rolled, kept):
        result = self._inner.get_damage_roll(rolled, kept)
        info = self._inner.last_damage_info()
        return self._maybe_reroll(result, info, rolled, kept, "damage")

    def get_initiative_roll(self, rolled, kept):
        # No reroll on initiative
        return self._inner.get_initiative_roll(rolled, kept)

    def get_skill_roll(self, skill, rolled, kept, explode=True):
        result = self._inner.get_skill_roll(skill, rolled, kept, explode=explode)
        info = self._inner.last_skill_info()
        return self._maybe_reroll(result, info, rolled, kept, "skill")

    def get_wound_check_roll(self, rolled, kept, explode=True):
        result = self._inner.get_wound_check_roll(rolled, kept, explode=explode)
        info = self._inner.last_wound_check_info()
        return self._maybe_reroll(result, info, rolled, kept, "wound_check")

    def last_damage_info(self):
        return self._inner.last_damage_info()

    def last_damage_roll(self):
        return self._inner.last_damage_roll()

    def last_initiative_info(self):
        return self._inner.last_initiative_info()

    def last_initiative_roll(self):
        return self._inner.last_initiative_roll()

    def last_skill_info(self):
        return self._inner.last_skill_info()

    def last_skill_roll(self):
        return self._inner.last_skill_roll()

    def last_wound_check_info(self):
        return self._inner.last_wound_check_info()

    def last_wound_check_roll(self):
        return self._inner.last_wound_check_roll()

    def set_die_provider(self, die_provider):
        self._inner.set_die_provider(die_provider)

    def _maybe_reroll(self, original_total, info, rolled, kept, roll_type):
        """Apply the Merchant 5th Dan reroll if beneficial.

        Returns the new total after potential rerolls.
        """
        if info is None or info.get("dice") is None:
            return original_total

        dice = list(info["dice"])
        # Ensure dice are sorted descending
        dice.sort(reverse=True)

        # Find indices to reroll
        indices = _find_dice_to_reroll(dice, kept)
        if not indices:
            return original_total

        # Reroll those dice
        for i in indices:
            old_value = dice[i]
            new_value = self._reroll_die_provider.roll_die()
            logger.debug(
                f"Merchant 5th Dan: rerolling die {old_value} -> {new_value}"
            )
            dice[i] = new_value

        # Recompute total: sort descending, sum the kept best
        dice.sort(reverse=True)

        # Compute bonus from the original info if it exists in the roll params
        # The info tracks rolled/kept but not bonus; we derive the bonus
        # from the original total vs what the kept dice summed to
        original_dice = list(info["dice"])
        original_dice.sort(reverse=True)
        original_kept_sum = sum(original_dice[:kept])
        bonus = original_total - original_kept_sum

        new_total = sum(dice[:kept]) + bonus
        return new_total


class MerchantSchool(BaseSchool):
    def ap_base_skill(self):
        return "sincerity"

    def ap_skills(self):
        return ["commerce", "heraldry", "interrogation", "sincerity", "attack", "wound check"]

    def apply_special_ability(self, character):
        # VP after initial roll: install custom optimizer and strategies
        # that never pre-allocate VP, but can spend VP post-roll.
        character.set_attack_optimizer_factory(MerchantAttackOptimizerFactory())
        character.set_strategy("attack_rolled", MerchantAttackRolledStrategy())
        character.set_strategy("wound_check", MerchantWoundCheckStrategy())
        character.set_strategy("wound_check_rolled", MerchantWoundCheckRolledStrategy())

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Rank 5.0 higher for stipend — no-op in combat

    def apply_rank_five_ability(self, character):
        # After non-initiative roll, reroll dice summing to >= 5*(X-1).
        # Wrap current roll provider with MerchantRollProvider.
        inner = character.roll_provider()
        character.set_roll_provider(MerchantRollProvider(inner))

    def extra_rolled(self):
        return ["interrogation", "sincerity", "wound check"]

    def free_raise_skills(self):
        return ["interrogation"]

    def name(self):
        return "Merchant School"

    def school_knacks(self):
        return ["discern honor", "oppose knowledge", "worldliness"]

    def school_ring(self):
        return "water"
