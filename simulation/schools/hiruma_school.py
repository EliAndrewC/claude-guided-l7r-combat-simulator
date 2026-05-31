#!/usr/bin/env python3

#
# hiruma_school.py
#
# Implement Hiruma Scout School.
#
# School Ring: Air
# School Knacks: double attack, counterattack, iaijutsu
#
# Special Ability: Left/right adjacent allies have their TN to be
#                  hit raised by +5 (spec 019 Q1 fix; was unimplemented).
# 1st Dan: Extra rolled on initiative, parry, wound check.
# 2nd Dan: Free raise on parry.
# 3rd Dan: After parry (success/fail):
#            (a) +2X to next attack AND damage roll vs the attacker
#                (X = attack skill).
#            (b) MAY immediately counterattack as an interrupt action
#                at the cost of 1 action die; this counterattack may
#                target anyone hittable (not limited to the attacker).
#          NOTE: rules-text "(a) or someone adjacent to them" deferred
#                — attacker-only scope for now (spec 019 Q2 partial).
#          NOTE: rules-text "(b) anyone you can hit" implemented as
#                target=attacker for now (simplest sensible choice in
#                1v1 — broader target selection is a future tweak).
# 4th Dan: Ring+1/discount; NewRoundListener subtracts 2 from all
#          action dice (min 1) after initiative.  ALSO refreshes
#          the Special Ability neighbor modifiers (chains via super).
# 5th Dan: After parry, attacker takes -10 damage on their next 2
#          damage rolls.  Delegates 3rd Dan effect via super.
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.modifier_listeners import (
    ExpireAfterNDamageRollsListener,
    ExpireAtEndOfRoundListener,
)
from simulation.schools.base import BaseSchool
from simulation.strategies.base import AlwaysParryStrategy, WoundCheckStrategy04


class HirumaScoutSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Hiruma Scout School: Special Ability":
        # "The two allies fighting on your left and right have their
        # TN to be hit raised by 5."
        #
        # Spec 019 Q1 BLOCKING IDENTITY fix — the previous skeleton
        # was a TODO `pass`.  Install a ``HirumaSpecialAbilityNewRound
        # Listener`` on the ``new_round`` slot that walks
        # ``context.formation().neighbors(hiruma)`` each round and
        # maintains +5 ``tn to hit`` modifiers on the current
        # neighbors (removing them from former neighbors as the
        # formation changes mid-combat).  At 4th Dan the slot is
        # replaced by ``HirumaNewRoundListener`` which subclasses the
        # Special Ability listener and adds the dice-2 trick.
        #
        # Identity bindings (spec 019 T-B1, per strategy-designer):
        # - ``AlwaysParryStrategy`` — 4 of 5 Dan-rank abilities key on
        #   parry; ``ReluctantParryStrategy`` (engine default) starves
        #   the identity engine.
        # - ``WoundCheckStrategy04`` — 1st Dan WC die + 5th Dan -10
        #   damage debuff = above-average WC pool, threshold 0.4.
        #
        # 2026-05-31: the 3rd Dan ability now grants an interrupt
        # counterattack option (1 action die) — set the cost here so
        # the listener can dispatch ``has_interrupt_action`` checks.
        self._set_school_listener(
            character, "new_round", HirumaSpecialAbilityNewRoundListener(character),
        )
        character.set_interrupt_cost("counterattack", 1)
        self._set_school_strategy(character, "parry", AlwaysParryStrategy())
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "parry_succeeded", HirumaParryListener())
        self._set_school_listener(character, "parry_failed", HirumaParryListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # Replace the Special Ability listener with the 4th Dan
        # listener (subclass that ALSO does the dice-2 trick).
        self._set_school_listener(
            character, "new_round", HirumaNewRoundListener(character),
        )

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "parry_succeeded", HirumaFifthDanParryListener())
        self._set_school_listener(character, "parry_failed", HirumaFifthDanParryListener())

    def extra_rolled(self) -> list[str]:
        return ["initiative", "parry", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["parry"]

    def name(self) -> str:
        return "Hiruma Scout School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "counterattack", "iaijutsu"]

    def school_ring(self) -> str:
        return "air"


class HirumaSpecialAbilityNewRoundListener(Listener):
    """rules/04-schools.md "Hiruma Scout School: Special Ability":

    "The two allies fighting on your left and right have their TN
    to be hit raised by 5."

    Fires on ``NewRoundEvent``.  Removes any modifiers previously
    installed by this listener (so former neighbors no longer carry
    the +5 TN bonus), then walks ``context.formation().neighbors
    (hiruma)`` to identify current left/right neighbors and installs
    +5 ``tn to hit`` modifiers on each.

    The 4th Dan listener subclasses this and additionally applies
    the action-die -2 trick.  Note: ``_set_school_listener`` REPLACES
    the engine default ``NewRoundListener``, so THIS listener owns
    the new-round flow including ``roll_initiative()``.

    Spec 019 T-A1 (Q1 BLOCKING IDENTITY fix) — previous skeleton was
    a TODO `pass`.
    """

    def __init__(self, hiruma: Any) -> None:
        self._hiruma = hiruma
        self._installed: list[tuple[Any, Modifier]] = []

    def _refresh_special_ability(self, context: Any) -> Iterator[Any]:
        """Remove previously-installed +5 TN modifiers, then walk
        the current formation's neighbors and install fresh ones."""
        # Remove old modifiers.
        for ally, modifier in self._installed:
            if modifier in ally._modifiers:
                yield events.RemoveModifierEvent(ally, modifier)
        self._installed = []
        # Skip if the Hiruma is defeated — Special Ability requires
        # the Hiruma to be "fighting on your left and right".
        if not self._hiruma.is_fighting():
            return
        # Install +5 ``tn to hit`` modifiers on the current left/right
        # neighbors.  NullFormation (engine default) returns [] from
        # neighbors() so this is a no-op when no real formation is
        # set — correct.
        formation = context.formation()
        neighbors = formation.neighbors(self._hiruma)
        for ally in neighbors:
            modifier = Modifier(ally, None, "tn to hit", 5)
            # Trace attribution tag for future renderer work (spec
            # 019 Q6).
            modifier._hiruma_special_ability = True  # type: ignore[attr-defined]
            self._installed.append((ally, modifier))
            yield events.AddModifierEvent(ally, modifier)

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            # Roll initiative (replaces engine default NewRoundListener).
            character.roll_initiative()
            # Refresh Special Ability neighbor modifiers.
            yield from self._refresh_special_ability(context)


class HirumaParryListener(Listener):
    """rules/04-schools.md "Hiruma Scout School: Third Dan":

    "After making a successful or unsuccessful parry, add 2X to your
    next attack and damage roll against the attacker or someone
    adjacent to them, where X is your attack skill.  After your
    successful or unsuccessful parry resolves, you may immediately
    counterattack as an interrupt action at the cost of 1 action die,
    and this counterattack may be directed at anyone you can hit
    rather than being limited to the attacker whose strike you
    parried." (2026-05-31 rules update.)

    Spec 019 T-A2 + T-A3 (Q2 + Q3 BLOCKING fixes):
    - Previous skeleton granted ``AnyAttackFloatingBonus(2X)`` which
      (a) applied to ANY target, contradicting the rules-text scope
      "against the attacker", AND (b) applied only to attack-skill
      rolls, NOT damage rolls.
    - Now emits a target-scoped ``Modifier`` with skills
      ``ATTACK_SKILLS + ["damage"]`` and ``target=attacker`` — the
      modifier's ``apply()`` (``modifiers.py:38-42``) returns the
      adjustment only when the roll target matches the modifier's
      target AND the skill is in the skills list.
    - "or someone adjacent to them" scope **DEFERRED** —
      attacker-only scope handles the dominant case in 1v1 (the
      common combat scenario for the simulator); full adjacency
      scoping is a follow-up.

    Expiry: ``ExpireAfterNDamageRollsListener(hiruma, 1)`` fires
    after Hiruma's next damage roll.  Combined with the end-of-round
    safety net.  Minor edge case: if Hiruma's next damage roll
    targets someone OTHER than the attacker (rare in 1v1), the
    modifier expires unused.

    Interrupt counterattack (2026-05-31): immediately after the parry
    resolves, if Hiruma has the counterattack skill and an
    interrupt-action die available, the listener yields the standard
    SpendAction + TakeCounterattack event pair so the counterattack
    runs inline.  Target defaults to the parried attacker — the
    rules-text "anyone you can hit" scope is preserved as future
    work (in 1v1 the attacker IS the only hittable target).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                yield from self._emit_third_dan_modifier(character, event, context)
                yield from self._maybe_interrupt_counterattack(character, event, context)

    def _maybe_interrupt_counterattack(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        # rules/04-schools.md "Hiruma Scout School: Third Dan"
        # (2026-05-31 update) — interrupt counterattack at 1 action
        # die cost.  Eager: always counterattack if the Hiruma can,
        # since the entire defensive identity is built around
        # converting parries into offense.
        if character.skill("counterattack") <= 0:
            return
        if not character.has_interrupt_action("counterattack", context):
            return
        cost = character.interrupt_cost("counterattack", context)
        unspent = list(character.actions())
        action_dice: list[int] = []
        while len(action_dice) < cost:
            die = max(unspent)
            unspent.remove(die)
            action_dice.append(die)
        initiative_action = InitiativeAction(
            action_dice, context.phase(), is_interrupt=True,
        )
        attacker = event.action.target()
        counterattack = character.action_factory().get_counterattack_action(
            character, attacker, event.action.attack(),
            "counterattack", initiative_action, context,
        )
        yield events.SpendActionEvent(character, "counterattack", initiative_action)
        yield character.take_action_event_factory().get_take_counterattack_action_event(counterattack)

    def _emit_third_dan_modifier(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        attacker = event.action.target()
        bonus = 2 * character.skill("attack")
        if bonus <= 0:
            return
        # Each parry adds one +2X stack against the attacker; the
        # registered ExpireAfterNDamageRollsListener consumes one
        # stack per damage roll, and ExpireAtEndOfRoundListener
        # clears the remainder at end of round.  Pre-2026-05-30 the
        # RemoveModifierListener was broken (wrong isinstance check
        # in listeners.py), so neither expiry actually fired and the
        # stacks grew unboundedly (trace-reader sweep reported +400
        # on Hiruma attacks).  With listeners.py fixed, the rules-
        # as-written stacking + per-damage expiry now works.
        # Target-scoped Modifier applies on character's attack-skill
        # rolls AND damage rolls vs the attacker.
        skills = list(ATTACK_SKILLS) + ["damage"]
        modifier = Modifier(character, attacker, skills, bonus)
        damage_listener = ExpireAfterNDamageRollsListener(character, 1)
        end_of_round_listener = ExpireAtEndOfRoundListener()
        modifier.register_listener("lw_damage", damage_listener)
        modifier.register_listener("end_of_round", end_of_round_listener)
        # Trace attribution tag for future renderer work.
        modifier._hiruma_3rd_dan = True  # type: ignore[attr-defined]
        yield events.AddModifierEvent(character, modifier)


class HirumaNewRoundListener(HirumaSpecialAbilityNewRoundListener):
    """rules/04-schools.md "Hiruma Scout School: Fourth Dan":

    "After rolling initiative, lower all of your action dice by 2,
    to a minimum of 1."

    Subclasses ``HirumaSpecialAbilityNewRoundListener`` and chains
    via super() so the Special Ability neighbor-modifier refresh
    still fires at 4th Dan (spec 019 T-A4 — clean subclass per
    Shinjo precedent).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            new_actions = [max(1, die - 2) for die in character.actions()]
            new_actions.sort()
            character._actions = new_actions
            # Refresh Special Ability neighbor modifiers (subclass
            # method).
            yield from self._refresh_special_ability(context)


class HirumaFifthDanParryListener(HirumaParryListener):
    """rules/04-schools.md "Hiruma Scout School: Fifth Dan":

    "After making a successful or unsuccessful parry roll, the
    attacker deals 10 fewer light wounds on their next 2 damage
    rolls."

    Subclasses ``HirumaParryListener`` so the 3rd Dan attack+damage
    bonus continues to fire (delegated via ``super()``).  Adds the
    5th Dan -10 damage modifier on the attacker with
    ``ExpireAfterNDamageRollsListener(attacker, 2)`` expiry.

    Spec 019 T-A5 (Q4 refactor) — previous skeleton duplicated the
    3rd Dan logic inline; now delegates via super.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                # 3rd Dan effects (super delegation, spec 019 T-A5).
                yield from self._emit_third_dan_modifier(character, event, context)
                yield from self._maybe_interrupt_counterattack(character, event, context)
                # 5th Dan attacker -10 damage modifier.
                attacker = event.action.target()
                modifier = Modifier(attacker, None, "damage", -10)
                damage_listener = ExpireAfterNDamageRollsListener(attacker, 2)
                modifier.register_listener("lw_damage", damage_listener)
                # Trace attribution tag.
                modifier._hiruma_5th_dan = True  # type: ignore[attr-defined]
                yield events.AddModifierEvent(attacker, modifier)
