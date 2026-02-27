#!/usr/bin/env python3

#
# kuni_school.py
#
# Implement Kuni Witch Hunter School.
#
# School Ring: Earth
# School Knacks: detect taint, iaijutsu, presence
#
# Special Ability: Extra 1k1 on wound checks (Taint=0 is always true in simulator).
# 1st Dan: Extra rolled on damage, wound check
# 2nd Dan: Free raise on interrogation (no-op in combat)
# 3rd Dan: AP system — ap_base_skill = "investigation", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; TODO (extra action die vs non-Tainted)
# 5th Dan: After wound check, inflict same LW on attacker.
#

from simulation import events
from simulation.listeners import Listener
from simulation.schools.base import BaseSchool


class KuniWitchHunterSchool(BaseSchool):
    def ap_base_skill(self):
        return "investigation"

    def ap_skills(self):
        return ["attack", "wound check"]

    def apply_special_ability(self, character):
        # Taint=0 is always true in the simulator, so the extra 1k1 always applies.
        character.set_extra_kept("wound check", 1)

    def apply_rank_one_ability(self, character):
        # Standard 1st Dan: extra rolled on damage, wound check
        super().apply_rank_one_ability(character)
        # The special ability already adds +1 kept to wound check.
        # The 1st Dan extra_rolled for wound check stacks with the special.

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # TODO: extra action die restricted to non-Tainted targets (useless without Taint system)

    def apply_rank_five_ability(self, character):
        character.set_listener("wound_check_succeeded", KuniWoundCheckSucceededListener())

    def extra_rolled(self):
        return ["damage", "wound check"]

    def free_raise_skills(self):
        return ["interrogation"]

    def name(self):
        return "Kuni Witch Hunter School"

    def school_knacks(self):
        return ["detect taint", "iaijutsu", "presence"]

    def school_ring(self):
        return "earth"


class KuniWoundCheckSucceededListener(Listener):
    """
    Listener to implement the Kuni 5th Dan technique:
    After a successful wound check, inflict the same LW on the attacker.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                # Reflect LW damage back to the attacker
                damage = event.damage
                if damage > 0:
                    yield events.LightWoundsDamageEvent(character, event.attacker, damage)
                # Continue with normal wound check succeeded behavior (keep LW decision)
                yield from character.light_wounds_strategy().recommend(character, event, context)
