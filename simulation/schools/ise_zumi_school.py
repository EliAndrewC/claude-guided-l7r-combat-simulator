#!/usr/bin/env python3

#
# ise_zumi_school.py
#
# Implement Togashi Ise Zumi School.
#
# School Ring: Void
# School Knacks: athletics, conviction, dragon tattoo
#
# Special Ability: Roll extra action dice per round (1 or 3, athletics-only).
#   Simplified: add 1 extra action die each round.
# 1st Dan: Extra rolled on attack, parry, athletics
# 2nd Dan: Free raise on athletics
# 3rd Dan: 4X daily free raises for athletics (X = precepts). Max X per roll.
#   Uses AP system with 4× multiplier, ap_base_skill = "precepts", ap_skills = ["athletics"]
# 4th Dan: Void+1/discount (+ reroll any contested roll once TODO)
# 5th Dan: Spend 1 VP to heal 2 SW after a wound check failure.
#

from simulation import events
from simulation.listeners import Listener
from simulation.schools.base import BaseSchool


class TogashiIseZumiSchool(BaseSchool):
    def __init__(self):
        super().__init__()
        self._ap_base_skill = "precepts"
        self._ap_skills = ["athletics"]

    def ap_base_skill(self):
        return "precepts"

    def ap_skills(self):
        return ["athletics"]

    def apply_special_ability(self, character):
        character.set_listener("new_round", IseZumiNewRoundListener())

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)
        character.set_ap_multiplier(4)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # TODO: reroll any contested roll once

    def apply_rank_five_ability(self, character):
        character.set_listener("wound_check_failed", IseZumiWoundCheckFailedListener())

    def extra_rolled(self):
        return ["attack", "parry", "athletics"]

    def free_raise_skills(self):
        return ["athletics"]

    def name(self):
        return "Togashi Ise Zumi School"

    def school_knacks(self):
        return ["athletics", "conviction", "dragon tattoo"]

    def school_ring(self):
        return "void"


class IseZumiNewRoundListener(Listener):
    """
    Special ability: Roll initiative and gain 1 extra action die.
    The extra die is placed at a random phase (rolled as 1d10).
    TODO: athletics-only restriction on extra action dice.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            # Roll 1 extra action die (1d10)
            extra_actions = character.roll_provider().get_initiative_roll(1, 1)
            if extra_actions:
                for phase in extra_actions:
                    character.gain_action(phase)
            yield from ()


class IseZumiWoundCheckFailedListener(Listener):
    """
    5th Dan: After a failed wound check, spend 1 VP to heal 2 SW.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.WoundCheckFailedEvent):
            if event.subject == character:
                sw = character.wound_check(event.roll)
                character.reset_lw()
                yield events.SeriousWoundsDamageEvent(event.attacker, character, sw)
                # After taking the SW, if character has VP and SW, heal 2 SW
                if character.vp() >= 1 and character.sw() >= 2:
                    yield events.SpendVoidPointsEvent(character, "wound check", 1)
                    character.take_sw(-2)
