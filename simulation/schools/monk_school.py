#!/usr/bin/env python3

#
# monk_school.py
#
# Implement Brotherhood of Shinsei Monk School.
#
# School Ring: Water (default; rules say "any non-Void")
# School Knacks: conviction, otherworldliness, worldliness
#
# Special Ability: Roll and keep 1 extra die for damage rolls (unarmed; always applied).
# 1st Dan: Extra rolled on attack, damage, wound check
# 2nd Dan: Free raise on attack
# 3rd Dan: AP system — ap_base_skill = "precepts", ap_skills = ["attack", "wound check"]
#          Also: AP may lower action dice by 5 phases (TODO)
# 4th Dan: Ring+1/discount; failed parry attempts don't lower rolled damage dice
# 5th Dan: After being attacked, spend action die to counter-attack;
#          if roll >= attacker's, cancel attack and hit attacker.
#

from simulation.schools.base import BaseSchool


class BrotherhoodOfShinseMonkSchool(BaseSchool):
    def ap_base_skill(self):
        return "precepts"

    def ap_skills(self):
        return ["attack", "wound check"]

    def apply_special_ability(self, character):
        # Extra 1k1 on damage (always applied — monks fight unarmed)
        character.set_extra_rolled("damage", 1)
        character.set_extra_kept("damage", 1)

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)
        # TODO: AP may also be spent to lower action dice by 5 phases

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Failed parry attempts don't lower rolled damage dice.
        # In the standard rules, a failed parry reduces the attacker's
        # rolled damage dice. This ability prevents that reduction.
        # TODO: implement via custom TakeActionEventFactory or listener

    def apply_rank_five_ability(self, character):
        # After being attacked (before damage), spend action die to counter-attack.
        # If counter-attack roll >= attacker's roll, cancel attack and continue
        # with counter-attack damage.
        # TODO: implement 5th Dan interrupt counter-attack
        pass

    def extra_rolled(self):
        return ["attack", "damage", "wound check"]

    def free_raise_skills(self):
        return ["attack"]

    def name(self):
        return "Brotherhood of Shinsei Monk School"

    def school_knacks(self):
        return ["conviction", "otherworldliness", "worldliness"]

    def school_ring(self):
        return "water"
