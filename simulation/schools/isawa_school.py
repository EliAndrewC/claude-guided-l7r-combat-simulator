#!/usr/bin/env python3

#
# isawa_school.py
#
# Implement Isawa Duelist School.
#
# School Ring: Water
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Uses Water ring for damage instead of Fire.
# 1st Dan: Extra rolled on double attack, lunge, wound check
# 2nd Dan: Free raise on wound check
# 3rd Dan: Custom attack actions add +3*attack_skill to modifier
#          AND lower own TN by 5 (add Modifier on self, "tn to hit", -5,
#          expires after next attack)
# 4th Dan: Ring+1/discount; interrupt lunge for 1 die, once per round
#          (reset via NewRoundListener)
# 5th Dan: After successful wound check, gain WoundCheckFloatingBonus(roll - damage)
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.actions import AttackAction, DoubleAttackAction, LungeAction
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.modifier_listeners import ExpireAfterNextAttackListener
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import Strategy, WoundCheckStrategy04


class IsawaDuelistSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Isawa Duelist School: Special Ability":
        # "You add your Water instead of Fire to your rolled damage
        # dice."  Wired via a custom RollParameterProvider that uses
        # water in get_damage_roll_params.
        #
        # Q1 (BACKLOG-flagged MINOR): the direct ``_skill_rings``
        # mutation isn't tracked in ``_school_owned_*`` so
        # school-negation (Isawa Ishi 5th Dan) doesn't revert it.
        # Cross-school refactor — DEFERRED.
        #
        # Spec 022 Q8 identity binding: WoundCheckStrategy04 (0.4
        # confidence threshold) — 1st Dan +1 WC die + 2nd Dan free
        # raise + 5th Dan WC floating bonus = deep WC pool. Matches
        # Hida/Shiba/Otaku/Shinjo/Daidoji/Kuni precedent.
        character._skill_rings["damage"] = "water"
        self._set_school_roll_parameter_provider(character, ISAWA_ROLL_PARAMETER_PROVIDER)
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_three_ability(self, character: Any) -> None:
        # rules/04-schools.md "Isawa Duelist School: Third Dan":
        # "After you make any type of attack roll, you may lower your
        # TN to be hit by 5 for the next time that you are attacked
        # this round to get a bonus of 3X on your attack roll, where
        # X is your attack skill.  If a successful or unsuccessful
        # parry is made against your attack, you do not suffer the
        # TN penalty."
        #
        # The +3X bonus is applied via ``ISAWA_ACTION_FACTORY``'s
        # custom attack actions (skill_roll_params adds +3*attack).
        # The TN penalty was the BACKLOG-flagged BLOCKING IDENTITY
        # gap (Q4): ``IsawaAttackResolvedListener`` (renamed from
        # the dead-code ``IsawaAttackDeclaredListener``) was defined
        # but never installed.  Now installed on attack_succeeded
        # AND attack_failed slots and gated on no-parry-attempted
        # (Q3 BLOCKING fix per rules-text "parry is made... you do
        # not suffer the TN penalty").
        self._set_school_action_factory(character, ISAWA_ACTION_FACTORY)
        resolved_listener = IsawaAttackResolvedListener()
        self._set_school_listener(character, "attack_succeeded", resolved_listener)
        self._set_school_listener(character, "attack_failed", resolved_listener)

    def apply_rank_four_ability(self, character: Any) -> None:
        # rules/04-schools.md "Isawa Duelist School: Fourth Dan":
        # "Once per round, you may lunge as an interrupt action at
        # the cost of 1 action die."
        #
        # Spec 022 Q5 + Q6 BLOCKING IDENTITY fixes: previously the
        # capability was wired (interrupt cost + add_interrupt_skill)
        # but no strategy was installed — same shape as Kakita/Otaku
        # Q1 identity bugs. Now installs ``IsawaInterruptLungeStrategy``
        # which fires on AttackDeclaredEvent against the Isawa, AND
        # tracks a per-round flag (Q5 "once per round") via the
        # ``IsawaNewRoundListener`` reset.
        self.apply_school_ring_raise_and_discount(character)
        character.set_interrupt_cost("lunge", 1)
        character.add_interrupt_skill("lunge")
        character._isawa_interrupt_lunge_used_this_round = False
        self._set_school_listener(character, "new_round", IsawaNewRoundListener())
        self._set_school_strategy(character, "interrupt", IsawaInterruptLungeStrategy())

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "wound_check_succeeded", IsawaWoundCheckSucceededListener())

    def extra_rolled(self) -> list[str]:
        return ["double attack", "lunge", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["wound check"]

    def name(self) -> str:
        return "Isawa Duelist School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self) -> str:
        return "water"


class IsawaRollParameterProvider(DefaultRollParameterProvider):
    """
    RollParameterProvider to implement the Isawa special ability:
    Uses Water ring for damage instead of Fire.
    """

    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        # Use water ring for damage
        ring = character.ring("water")
        my_extra_rolled = character.extra_rolled("damage")
        rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled()
        kept = character.weapon().kept() + character.extra_kept("damage")
        mod = character.modifier(None, "damage")
        return normalize_roll_params(rolled, kept, mod)


ISAWA_ROLL_PARAMETER_PROVIDER = IsawaRollParameterProvider()


class IsawaAttackAction(AttackAction):
    """
    Custom AttackAction for Isawa 3rd Dan:
    Add +3*attack_skill to skill roll modifier.
    After the attack, lower own TN by 5 (expires after next attack).
    """

    def skill_roll_params(self) -> tuple[int, int, int]:
        (rolled, kept, modifier) = self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())
        bonus = 3 * self.subject().skill("attack")
        return (rolled, kept, modifier + bonus)


class IsawaDoubleAttackAction(DoubleAttackAction):
    """
    Custom DoubleAttackAction for Isawa 3rd Dan.
    """

    def skill_roll_params(self) -> tuple[int, int, int]:
        (rolled, kept, modifier) = self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())
        bonus = 3 * self.subject().skill("attack")
        return (rolled, kept, modifier + bonus)


class IsawaLungeAction(LungeAction):
    """
    Custom LungeAction for Isawa 3rd Dan.
    """

    def skill_roll_params(self) -> tuple[int, int, int]:
        (rolled, kept, modifier) = self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())
        bonus = 3 * self.subject().skill("attack")
        return (rolled, kept, modifier + bonus)


class IsawaActionFactory(DefaultActionFactory):
    """
    ActionFactory to return Isawa-specific attack actions.
    """

    def get_attack_action(self, subject: Any, target: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        if skill in ("attack", "iaijutsu"):
            return IsawaAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        elif skill == "double attack":
            return IsawaDoubleAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        elif skill == "lunge":
            return IsawaLungeAction(subject, target, skill, initiative_action, context, vp=vp)
        elif skill == "feint":
            return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)
        else:
            raise ValueError(f"Invalid attack skill: {skill}")


ISAWA_ACTION_FACTORY = IsawaActionFactory()


class IsawaAttackResolvedListener(Listener):
    """rules/04-schools.md "Isawa Duelist School: Third Dan":

    "After you make any type of attack roll, you may lower your TN
    to be hit by 5 for the next time that you are attacked this
    round to get a bonus of 3X on your attack roll, where X is your
    attack skill.  If a successful or unsuccessful parry is made
    against your attack, you do not suffer the TN penalty."

    Spec 022 Q3 + Q4 BLOCKING fixes (renamed from the dead-code
    ``IsawaAttackDeclaredListener``):

    * **Q4**: previously the listener was defined but never
      installed.  Now installed on ``attack_succeeded`` and
      ``attack_failed`` slots.
    * **Q3**: previously the listener fired unconditionally on
      ``AttackDeclaredEvent`` (pre-resolution — too early to know
      about parry).  Now fires on post-resolution events and gates
      on ``not event.action.parry_attempted()`` — matches the
      rules-text "If a successful or unsuccessful parry is made
      against your attack, you do not suffer the TN penalty".

    The +3X bonus side of the trade comes from ``IsawaAttackAction``
    / ``IsawaDoubleAttackAction`` / ``IsawaLungeAction``
    (skill_roll_params adds +3*attack to the modifier).  This
    listener applies the OTHER side of the trade — the -5 ``tn to
    hit`` modifier on the Isawa.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, (events.AttackSucceededEvent, events.AttackFailedEvent)):
            if event.action.subject() == character:
                # Q3 fix: skip TN penalty if a parry was attempted.
                if event.action.parry_attempted():
                    return
                modifier = Modifier(character, None, "tn to hit", -5)
                expiry = ExpireAfterNextAttackListener()
                modifier.register_listener("attack_failed", expiry)
                modifier.register_listener("attack_succeeded", expiry)
                # Trace attribution tag for future renderer work.
                modifier._isawa_3rd_dan_tn_penalty = True  # type: ignore[attr-defined]
                yield events.AddModifierEvent(character, modifier)


class IsawaInterruptLungeStrategy(Strategy):
    """rules/04-schools.md "Isawa Duelist School: Fourth Dan":

    "Once per round, you may lunge as an interrupt action at the
    cost of 1 action die."

    Spec 022 Q5 + Q6 BLOCKING IDENTITY fix.  Fires on
    ``AttackDeclaredEvent`` against the Isawa (pre-roll trigger —
    rules text "lunge as an interrupt action" is the standard
    interrupt-attack semantics: pre-empt the incoming attack).

    Gates:

    * Once-per-round flag (Q5) — ``character._isawa_interrupt_lunge
      _used_this_round`` reset by ``IsawaNewRoundListener``.
    * Standard interrupt-action availability via
      ``character.has_interrupt_action("lunge", context)``.
    * SW-saturation gate (Principle IX): decline at ``sw_remaining
      () <= 1`` — don't burn the interrupt die on offense when
      WC is the survival path.
    * Mirror anti-recursion gate: decline against incoming interrupt
      lunges (prevent two Isawas volleying lunges forever).
    * Adjacency check.
    """

    THRESHOLD = 0.5  # Modest confidence — lunge gets +1 die (1st
                     # Dan) + 3*X bonus from Isawa attack actions.

    def _should_lunge(self, character: Any, event: Any, context: Any) -> bool:
        # Once-per-round gate.
        if getattr(character, "_isawa_interrupt_lunge_used_this_round", False):
            return False
        # Target must be the Isawa.
        if event.action.target() != character:
            return False
        attacker = event.action.subject()
        if attacker == character:  # pragma: no cover  # defensive: subject != target guaranteed by engine
            return False
        # Need lunge skill.
        if character.skill("lunge") <= 0:
            return False
        # Need available interrupt action.
        if not character.has_interrupt_action("lunge", context):
            return False
        # SW-saturation gate.
        if character.sw_remaining() <= 1:
            return False
        # Mirror anti-recursion: decline against incoming interrupt-lunge.
        if event.action.skill() == "lunge":
            if event.action.initiative_action().is_interrupt():
                return False
        # Adjacency check.
        if not context.formation().is_adjacent(character, attacker):  # pragma: no cover  # defensive: NullFormation default returns True
            return False
        return True

    def _choose_action(self, character: Any, context: Any) -> InitiativeAction:
        cost = character.interrupt_cost("lunge", context)
        unspent = list(character.actions())
        action_dice: list[int] = []
        while len(action_dice) < cost:
            die = max(unspent)
            unspent.remove(die)
            action_dice.append(die)
        return InitiativeAction(action_dice, context.phase(), is_interrupt=True)

    def _do_lunge(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        attacker = event.action.subject()
        ia = self._choose_action(character, context)
        optimizer = character.attack_optimizer_factory().get_optimizer(
            character, attacker, "lunge", ia, context,
        )
        attack = optimizer.optimize(self.THRESHOLD)
        if attack is None:
            return
        # Trace attribution + mark once-per-round used.
        attack._isawa_4th_dan_interrupt_lunge = True
        character._isawa_interrupt_lunge_used_this_round = True
        logger.info(
            f"{character.name()} interrupt-lunges (Isawa 4th Dan) at "
            f"{attacker.name()}"
        )
        yield events.SpendActionEvent(character, "lunge", ia)
        yield character.take_action_event_factory().get_take_attack_action_event(attack)

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackDeclaredEvent):
            if self._should_lunge(character, event, context):
                yield from self._do_lunge(character, event, context)


class IsawaNewRoundListener(Listener):
    """rules/04-schools.md "Isawa Duelist School: Fourth Dan" — reset
    helpers per round.

    ``_set_school_listener`` REPLACES the engine default
    ``NewRoundListener`` at the ``new_round`` slot, so THIS listener
    owns the new-round flow including ``roll_initiative()``.

    Per-round reset of:
      - interrupt cost for ``lunge`` (defense-in-depth; cost should
        already be 1 from ``apply_rank_four_ability``).
      - Once-per-round used flag for the interrupt-lunge strategy
        (spec 022 Q5).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            character.set_interrupt_cost("lunge", 1)
            # Q5 fix: reset once-per-round flag.
            character._isawa_interrupt_lunge_used_this_round = False
        yield from ()


class IsawaWoundCheckSucceededListener(Listener):
    """
    Listener to implement the Isawa 5th Dan technique:
    After successful wound check, gain WoundCheckFloatingBonus(roll - damage).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                bonus = event.roll - event.damage
                if bonus > 0:
                    character.gain_floating_bonus(WoundCheckFloatingBonus(bonus))
                # Continue with normal wound check succeeded behavior
                yield from character.light_wounds_strategy().recommend(character, event, context)
