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

from simulation.schools.base import BaseSchool


class MerchantSchool(BaseSchool):
    def ap_base_skill(self):
        return "sincerity"

    def ap_skills(self):
        return ["attack", "wound check"]

    def apply_special_ability(self, character):
        # VP after initial roll: the optimizer already pre-allocates VP, but
        # the merchant can wait to see the roll first. In the simulator this
        # means the post-roll strategy can spend VP to close gaps.
        # TODO: implement post-roll VP spending via a custom strategy
        pass

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Rank 5.0 higher for stipend — no-op in combat

    def apply_rank_five_ability(self, character):
        # After non-initiative roll, reroll dice summing to >= 5*(X-1).
        # Requires dice-tracking roll provider.
        # TODO: implement reroll mechanic
        pass

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
