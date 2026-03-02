#!/usr/bin/env python3

#
# ishi_school.py
#
# Implement Isawa Ishi School.
#
# School Ring: Void
# School Knacks: absorb void, kharmic spin, otherworldliness
#
# Special Ability: Custom VP calculation.
#   Max VP = highest ring + school rank (instead of min ring + worldliness)
#   Max VP per roll = lowest ring - 1 (instead of min ring)
# 1st Dan: Extra rolled on precepts, wound check, initiative
# 2nd Dan: Free raise on attack
# 3rd Dan: Spend 1 VP to add Xk1 to ally's roll (X = precepts). Once per roll.
# 4th Dan: Void+1/discount (+ opponents can't spend VP in contested rolls TODO)
# 5th Dan: Negate opponent's school/profession for a fight (TODO)
#

from simulation import events
from simulation.character import RING_NAMES
from simulation.listeners import Listener
from simulation.schools.base import BaseSchool


class IshiMaxVPProvider:
    """Custom VP provider for the Isawa Ishi School special ability."""

    def __init__(self, school_rank=1):
        self._school_rank = school_rank

    def set_school_rank(self, rank):
        self._school_rank = rank

    def max_vp(self, character):
        highest_ring = max(character.ring(ring) for ring in RING_NAMES)
        return highest_ring + self._school_rank

    def max_vp_per_roll(self, character):
        lowest_ring = min(character.ring(ring) for ring in RING_NAMES)
        return max(0, lowest_ring - 1)


class IsawaIshiSchool(BaseSchool):
    def __init__(self):
        self._vp_provider = IshiMaxVPProvider()
        super().__init__()

    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_max_vp_provider(self._vp_provider)

    def apply_rank_three_ability(self, character):
        character.set_listener("attack_rolled", IshiAllyBoostListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Contested roll VP restriction is a social ability, not applicable in combat simulation

    def apply_rank_five_ability(self, character):
        # TODO: negate opponent's school/profession for a fight
        pass

    def extra_rolled(self):
        return ["precepts", "wound check", "initiative"]

    def free_raise_skills(self):
        return ["attack"]

    def name(self):
        return "Isawa Ishi School"

    def school_knacks(self):
        return ["absorb void", "kharmic spin", "otherworldliness"]

    def school_ring(self):
        return "void"

    def vp_provider(self):
        return self._vp_provider


class IshiAllyBoostListener(Listener):
    """
    3rd Dan: When an ally makes an attack roll, spend 1 VP to add Xk1
    (X = precepts) to the ally's roll.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.AttackRolledEvent):
            subject = event.action.subject()
            if subject != character and character.group() is not None and subject in character.group() and context.formation().is_adjacent(character, subject):
                # Adjacent ally is attacking — boost their roll
                precepts = character.skill("precepts")
                if precepts > 0 and character.vp() >= 1:
                    yield events.SpendVoidPointsEvent(character, "precepts", 1)
                    bonus = character.roll_provider().get_skill_roll("precepts", precepts, 1, True)
                    new_roll = event.roll + bonus
                    event.action.set_skill_roll(new_roll)
                    yield events.AttackRolledEvent(event.action, new_roll)
            elif character != event.action.subject():
                # Default behavior for non-allies: observe and consider interrupt
                character.knowledge().observe_attack_roll(event.action.subject(), event.roll)
                yield from character.interrupt_strategy().recommend(character, event, context)
