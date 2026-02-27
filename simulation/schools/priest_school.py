#!/usr/bin/env python3

#
# priest_school.py
#
# Implement Priest School.
#
# School Ring: Water
# School Knacks: conviction, otherworldliness, pontificate
#
# Special Ability: Has all 10 rituals — no combat effect.
# 1st Dan: Extra rolled on precepts, initiative, wound check
# 2nd Dan: Free raise on bragging, precepts, sincerity (self + allies TODO)
# 3rd Dan: Roll X dice at combat start (X = precepts). Store as pool.
#          Each die can be spent as a flat bonus to attack/parry/WC/damage.
# 4th Dan: Ring+1/discount (+ contested roll free raises TODO)
# 5th Dan: Conviction on allies + refresh + lower action dice (TODO)
#

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import FloatingBonus
from simulation.schools.base import BaseSchool

PRIEST_POOL_SKILLS = ["attack", "parry", "wound check", "damage",
                      "double attack", "feint", "iaijutsu", "lunge",
                      "counterattack"]


class PriestSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        # All 10 rituals — no combat effect
        pass

    def apply_rank_three_ability(self, character):
        character.set_listener("new_round", PriestNewRoundListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # TODO: free raise on contested rolls vs equal/higher skill (self + allies)

    def apply_rank_five_ability(self, character):
        # TODO: conviction on allies' rolls + refresh each round + lower action dice
        pass

    def extra_rolled(self):
        return ["precepts", "initiative", "wound check"]

    def free_raise_skills(self):
        return ["bragging", "precepts", "sincerity"]

    def name(self):
        return "Priest School"

    def school_knacks(self):
        return ["conviction", "otherworldliness", "pontificate"]

    def school_ring(self):
        return "water"


class PriestNewRoundListener(Listener):
    """
    3rd Dan: At the start of each round, roll initiative and then roll X dice
    (X = precepts skill). Each die is stored as a floating bonus that can be
    applied to attack, parry, wound check, or damage rolls.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            precepts = character.skill("precepts")
            if precepts > 0:
                for _ in range(precepts):
                    die_value = character.roll_provider().get_skill_roll("precepts", 1, 1, True)
                    bonus = FloatingBonus(PRIEST_POOL_SKILLS, die_value)
                    character.gain_floating_bonus(bonus)
            yield from ()
