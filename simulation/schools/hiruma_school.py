#!/usr/bin/env python3

#
# hiruma_school.py
#
# Implement Hiruma Scout School.
#
# School Ring: Air
# School Knacks: double attack, feint, iaijutsu
#
# Special Ability: TODO (adjacency-based TN bonus for allies)
# 1st Dan: Extra rolled on initiative, parry, wound check
# 2nd Dan: Free raise on parry
# 3rd Dan: After parry (success/fail), gain AnyAttackFloatingBonus(2 * attack_skill).
#          TODO re: positioning.
# 4th Dan: Ring+1/discount; NewRoundListener subtracts 2 from all action dice (min 1) after initiative
# 5th Dan: After parry, AddModifierEvent on attacker: -10 damage,
#          expires after 2 damage rolls
#

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import AnyAttackFloatingBonus
from simulation.mechanics.modifiers import Modifier
from simulation.modifier_listeners import ExpireAfterNDamageRollsListener
from simulation.schools.base import BaseSchool


class HirumaScoutSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        # TODO: adjacency-based TN bonus for allies
        pass

    def apply_rank_three_ability(self, character):
        character.set_listener("parry_succeeded", HirumaParryListener())
        character.set_listener("parry_failed", HirumaParryListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_listener("new_round", HirumaNewRoundListener())

    def apply_rank_five_ability(self, character):
        character.set_listener("parry_succeeded", HirumaFifthDanParryListener())
        character.set_listener("parry_failed", HirumaFifthDanParryListener())

    def extra_rolled(self):
        return ["initiative", "parry", "wound check"]

    def free_raise_skills(self):
        return ["parry"]

    def name(self):
        return "Hiruma Scout School"

    def school_knacks(self):
        return ["double attack", "feint", "iaijutsu"]

    def school_ring(self):
        return "air"


class HirumaParryListener(Listener):
    """
    Listener to implement the Hiruma 3rd Dan technique:
    After parry (success or fail), gain AnyAttackFloatingBonus(2 * attack_skill).
    """

    def handle(self, character, event, context):
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                bonus = 2 * character.skill("attack")
                character.gain_floating_bonus(AnyAttackFloatingBonus(bonus))
        yield from ()


class HirumaNewRoundListener(Listener):
    """
    Listener to implement the Hiruma 4th Dan technique:
    After rolling initiative, subtract 2 from all action dice (min 1).
    """

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            new_actions = [max(1, die - 2) for die in character.actions()]
            new_actions.sort()
            character._actions = new_actions
        yield from ()


class HirumaFifthDanParryListener(Listener):
    """
    Listener to implement the Hiruma 5th Dan technique:
    After parry (success or fail), add modifier on attacker:
    -10 damage, expires after 2 damage rolls.
    """

    def handle(self, character, event, context):
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                attacker = event.action.target()
                # Grant floating bonus (3rd Dan still applies)
                bonus = 2 * character.skill("attack")
                character.gain_floating_bonus(AnyAttackFloatingBonus(bonus))
                # Apply -10 damage modifier on attacker, expires after 2 damage rolls
                modifier = Modifier(attacker, None, "damage", -10)
                listener = ExpireAfterNDamageRollsListener(attacker, 2)
                modifier.register_listener("lw_damage", listener)
                yield events.AddModifierEvent(attacker, modifier)
