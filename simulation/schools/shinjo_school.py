#!/usr/bin/env python3

#
# shinjo_school.py
#
# Implement Shinjo Bushi School.
#
# School Ring: Air
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Each action gains bonus of 2X where X = phases action die was held.
# 1st Dan: Extra rolled on double attack, initiative, parry
# 2nd Dan: Free raise on parry
# 3rd Dan: After parry (success/fail), decrease all remaining action dice by attack_skill.
#          Can go negative.
# 4th Dan: Ring+1/discount; NewRoundListener sets highest action die to 1
# 5th Dan: After successful parry, gain WoundCheckFloatingBonus(parry_roll - attack_roll)
#

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.schools.base import BaseSchool


class ShinjoBushiSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        # Track action die hold bonus via SpendActionListener
        character.set_listener("spend_action", ShinjoSpendActionListener())

    def apply_rank_three_ability(self, character):
        character.set_listener("parry_succeeded", ShinjoParryListener())
        character.set_listener("parry_failed", ShinjoParryListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_listener("new_round", ShinjoNewRoundListener())

    def apply_rank_five_ability(self, character):
        character.set_listener("parry_succeeded", ShinjoFifthDanParryListener())
        character.set_listener("parry_failed", ShinjoParryListener())

    def extra_rolled(self):
        return ["double attack", "initiative", "parry"]

    def free_raise_skills(self):
        return ["parry"]

    def name(self):
        return "Shinjo Bushi School"

    def school_knacks(self):
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self):
        return "air"


class ShinjoSpendActionListener(Listener):
    """
    Listener to implement the Shinjo special ability:
    Each action gains a bonus of 2X where X = phases the action die was held.
    Track original die phase and compute bonus when action is spent.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.SpendActionEvent):
            if event.subject == character:
                # Calculate hold bonus: 2 * (current_phase - die_phase)
                die_phase = event.initiative_action.phase()
                current_phase = context.phase()
                hold_phases = max(0, current_phase - die_phase)
                bonus = 2 * hold_phases
                if bonus > 0:
                    # Store the bonus as a temporary attribute for the next action
                    character._shinjo_hold_bonus = bonus
                character.spend_action(event.initiative_action)
        yield from ()


class ShinjoParryListener(Listener):
    """
    Listener to implement the Shinjo 3rd Dan technique:
    After parry (success/fail), decrease all remaining action dice by attack_skill.
    """

    def handle(self, character, event, context):
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                decrease = character.skill("attack")
                actions = character.actions()
                for i in range(len(actions)):
                    actions[i] = actions[i] - decrease
                actions.sort()
        yield from ()


class ShinjoNewRoundListener(Listener):
    """
    Listener to implement the Shinjo 4th Dan technique:
    After rolling initiative, set highest action die to 1.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            actions = character.actions()
            if len(actions) > 0:
                # Set the highest action die to 1
                max_idx = actions.index(max(actions))
                actions[max_idx] = 1
                actions.sort()
        yield from ()


class ShinjoFifthDanParryListener(Listener):
    """
    Listener to implement the Shinjo 5th Dan technique:
    After successful parry, gain WoundCheckFloatingBonus(parry_roll - attack_roll).
    Also includes 3rd Dan effect (decrease action dice).
    """

    def handle(self, character, event, context):
        if isinstance(event, events.ParrySucceededEvent):
            if event.action.subject() == character:
                # 3rd Dan: decrease action dice
                decrease = character.skill("attack")
                actions = character.actions()
                for i in range(len(actions)):
                    actions[i] = actions[i] - decrease
                actions.sort()
                # 5th Dan: gain wound check floating bonus
                parry_roll = event.action.skill_roll()
                attack_roll = event.action.attack().skill_roll()
                bonus = parry_roll - attack_roll
                if bonus > 0:
                    character.gain_floating_bonus(WoundCheckFloatingBonus(bonus))
        elif isinstance(event, events.ParryFailedEvent):
            if event.action.subject() == character:
                # 3rd Dan still applies on failed parries
                decrease = character.skill("attack")
                actions = character.actions()
                for i in range(len(actions)):
                    actions[i] = actions[i] - decrease
                actions.sort()
        yield from ()
