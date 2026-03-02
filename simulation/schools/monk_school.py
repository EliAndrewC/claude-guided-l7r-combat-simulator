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
# 3rd Dan: AP system -- ap_base_skill = "precepts", ap_skills = ["attack", "wound check"]
#          Also: AP may lower action dice by 5 phases
# 4th Dan: Ring+1/discount; failed parry attempts don't lower rolled damage dice
# 5th Dan: After being attacked, spend action die to counter-attack;
#          if roll >= attacker's, cancel attack and hit attacker.
#

from simulation import actions, events
from simulation.listeners import Listener, NewRoundListener
from simulation.log import logger
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory


class BrotherhoodOfShinseMonkSchool(BaseSchool):
    def ap_base_skill(self):
        return "precepts"

    def ap_skills(self):
        return ["history", "law", "precepts", "wound check", "attack"]

    def apply_special_ability(self, character):
        # Extra 1k1 on damage (always applied -- monks fight unarmed)
        character.set_extra_rolled("damage", 1)
        character.set_extra_kept("damage", 1)

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)
        # AP may also be spent to lower action dice by 5 phases
        character.set_listener("new_round", MonkNewRoundListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Failed parry attempts don't lower rolled damage dice.
        # Install MonkActionFactory so attacks use MonkAttackAction.
        character.set_action_factory(MONK_ACTION_FACTORY)

    def apply_rank_five_ability(self, character):
        # After being attacked (before damage), spend action die to counter-attack.
        # If counter-attack roll >= attacker's roll, cancel attack and
        # counter-attack damage is applied to the attacker.
        fifth_dan_listener = MonkFifthDanListener()
        character.set_listener("attack_succeeded", fifth_dan_listener)
        # Wrap the existing new_round listener to also reset the 5th Dan flag.
        existing_new_round_listener = character._listeners.get("new_round")
        character.set_listener(
            "new_round",
            MonkFifthDanNewRoundListener(existing_new_round_listener, fifth_dan_listener),
        )

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


# ──────────────────────────────────────────────────────────────────
# 3rd Dan: MonkNewRoundListener
# After rolling initiative, spend AP to lower action dice by 5 phases.
# ──────────────────────────────────────────────────────────────────

class MonkNewRoundListener(NewRoundListener):
    """After rolling initiative, spend AP to lower action dice by 5 phases.

    For each available AP, the highest action die above phase 5 is
    lowered by 5 (minimum phase 1). This happens automatically after
    the initiative roll.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            # Roll initiative first (standard behavior)
            character.roll_initiative()
            # Then spend AP to lower action dice
            self._lower_action_dice(character)
            yield from ()

    def _lower_action_dice(self, character):
        while character.ap() > 0:
            action_dice = character.actions()
            if len(action_dice) == 0:
                break
            highest = max(action_dice)
            # Only lower dice that are above phase 5 (lowering saves at least 1 phase)
            if highest <= 5:
                break
            # Lower the highest die by 5, minimum 1
            new_phase = max(1, highest - 5)
            action_dice.remove(highest)
            action_dice.append(new_phase)
            action_dice.sort()
            # Spend 1 AP for the lowering
            character.spend_ap("attack", 1)
            logger.info(
                f"{character.name()} spends 1 AP to lower action die "
                f"from phase {highest} to phase {new_phase}"
            )


# ──────────────────────────────────────────────────────────────────
# 4th Dan: MonkAttackAction and MonkActionFactory
# Failed parries don't lower the monk's rolled damage dice.
# ──────────────────────────────────────────────────────────────────

class MonkAttackAction(actions.AttackAction):
    """Attack action for monks that ignores parry_attempted when
    calculating extra damage dice.

    In the standard rules, when a parry is attempted (and fails),
    the attacker gets 0 extra damage dice. The Monk 4th Dan ability
    removes this penalty -- the monk always gets full extra damage dice.
    """

    def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        # Ignore parry_attempted -- always calculate normally
        return (skill_roll - tn) // 5


class MonkActionFactory(DefaultActionFactory):
    """ActionFactory that returns MonkAttackAction for attack skills."""

    def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
        if skill in ("attack", "iaijutsu"):
            return MonkAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        else:
            return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


MONK_ACTION_FACTORY = MonkActionFactory()


# ──────────────────────────────────────────────────────────────────
# 5th Dan: MonkFifthDanListener and MonkFifthDanNewRoundListener
# Once per round after being attacked but before damage is rolled,
# spend an action die to counter-attack the attacker.
# ──────────────────────────────────────────────────────────────────

class MonkFifthDanListener(Listener):
    """Listener for the Monk 5th Dan ability.

    When the monk is the target of a successful attack:
    1. If the monk has an action die and hasn't used this ability this round,
       spend the highest-phase action die.
    2. Roll the monk's attack (Fire + attack skill) vs attacker's TN to hit.
    3. If the monk's roll >= attacker's attack roll, cancel the original attack
       (set_parried) and deal damage to the attacker.
    4. If the monk's roll < attacker's roll, the original attack continues.

    The once-per-round flag (_used_this_round) is reset by the
    MonkFifthDanNewRoundListener each new round.
    """

    def __init__(self):
        self._used_this_round = False

    def reset_round(self):
        """Reset the once-per-round flag."""
        self._used_this_round = False

    def handle(self, character, event, context):
        if isinstance(event, events.AttackSucceededEvent):
            # Only trigger when the monk is the target
            if event.action.target() != character:
                yield from ()
                return
            # Only once per round
            if self._used_this_round:
                yield from ()
                return
            # Must have at least one action die
            if len(character.actions()) == 0:
                yield from ()
                return
            # Spend highest action die (least valuable)
            highest_die = max(character.actions())
            character.actions().remove(highest_die)
            logger.info(
                f"{character.name()} (Monk 5th Dan) spends action die "
                f"from phase {highest_die} to counter-attack "
                f"{event.action.subject().name()}"
            )
            # Mark as used this round
            self._used_this_round = True
            # Roll the monk's attack
            counter_roll = character.roll_skill(
                event.action.subject(), "attack",
            )
            attacker_roll = event.action.skill_roll()
            if counter_roll >= attacker_roll:
                # Cancel the original attack
                event.action.set_parried()
                logger.info(
                    f"{character.name()} counter-attack roll {counter_roll} "
                    f">= attacker roll {attacker_roll}: attack cancelled"
                )
                # Roll damage against the attacker
                damage = character.roll_damage(
                    event.action.subject(), "attack", 0,
                )
                yield events.LightWoundsDamageEvent(
                    character, event.action.subject(), damage,
                )
            else:
                logger.info(
                    f"{character.name()} counter-attack roll {counter_roll} "
                    f"< attacker roll {attacker_roll}: attack continues"
                )
                yield from ()


class MonkFifthDanNewRoundListener(Listener):
    """New round listener that wraps an existing new_round listener
    and also resets the MonkFifthDanListener's once-per-round flag."""

    def __init__(self, wrapped_listener, fifth_dan_listener):
        self._wrapped = wrapped_listener
        self._fifth_dan_listener = fifth_dan_listener

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            # Reset the 5th Dan once-per-round flag
            self._fifth_dan_listener.reset_round()
        # Delegate to the wrapped listener
        if self._wrapped is not None:
            yield from self._wrapped.handle(character, event, context)
        else:
            # Default new round behavior: roll initiative
            if isinstance(event, events.NewRoundEvent):
                character.roll_initiative()
                yield from ()
