#!/usr/bin/env python3

#
# otaku_school.py
#
# Implement Otaku Bushi School.
#
# School Ring: Fire
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Interrupt lunge for 1 die after being attacked.
# 1st Dan: Extra rolled on iaijutsu, lunge, wound check
# 2nd Dan: Free raise on wound check
# 3rd Dan: After damage roll, increase target's next X action dice
#          by (6 - target.fire, min 1), max phase 10.
# 4th Dan: Ring+1/discount; custom OtakuLungeAction where
#          calculate_extra_damage_dice always adds 1 even when parried.
# 5th Dan: Strategy: compare expected SW with/without trading 10 rolled dice
#          for 1 automatic SW. Custom damage action that reduces rolled dice
#          by 10 (min 2) and yields SeriousWoundsDamageEvent.
#

from simulation import events
from simulation.actions import LungeAction
from simulation.listeners import Listener
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory


class OtakuBushiSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_interrupt_cost("lunge", 1)
        character.add_interrupt_skill("lunge")

    def apply_rank_three_ability(self, character):
        character.set_listener("lw_damage", OtakuLightWoundsDamageListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_action_factory(OTAKU_ACTION_FACTORY)

    def apply_rank_five_ability(self, character):
        # TODO: Strategy for trading 10 rolled dice for 1 automatic SW
        pass

    def extra_rolled(self):
        return ["iaijutsu", "lunge", "wound check"]

    def free_raise_skills(self):
        return ["wound check"]

    def name(self):
        return "Otaku Bushi School"

    def school_knacks(self):
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self):
        return "fire"


class OtakuLightWoundsDamageListener(Listener):
    """
    Listener to implement the Otaku 3rd Dan technique:
    After dealing damage, increase target's next X action dice
    by (6 - target.fire, min 1), max phase 10.
    X is the number of action dice affected.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.subject == character and event.target != character:
                target = event.target
                increase = max(1, 6 - target.ring("fire"))
                # Modify target's action dice
                actions = target.actions()
                for i in range(len(actions)):
                    actions[i] = min(10, actions[i] + increase)
                actions.sort()
            if event.subject != character:
                # observe another character's damage roll
                character.knowledge().observe_damage_roll(event.subject, event.damage)
            if event.target == character:
                character.take_lw(event.damage)
                if event.damage > 0:
                    yield from character.wound_check_strategy().recommend(character, event, context)


class OtakuLungeAction(LungeAction):
    """
    Custom LungeAction for Otaku 4th Dan:
    calculate_extra_damage_dice always adds 1 even when parried.
    """

    def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        if self.parry_attempted():
            # Still get +1 even when parried
            return 1
        return ((skill_roll - tn) // 5) + 1


class OtakuActionFactory(DefaultActionFactory):
    """
    ActionFactory to return Otaku-specific attack actions.
    """

    def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
        if skill == "lunge":
            return OtakuLungeAction(subject, target, skill, initiative_action, context, vp=vp)
        return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


OTAKU_ACTION_FACTORY = OtakuActionFactory()
