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

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.actions import AttackAction, LungeAction
from simulation.events import LightWoundsDamageEvent, SeriousWoundsDamageEvent, TakeAttackActionEvent
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import Strategy, WoundCheckStrategy04
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory

# rules/04-schools.md Otaku 5th Dan strategic threshold (spec 014 Q3).
# Rules-floor for the trade is raw_rolled >= 12 (subtract 10, min 2);
# combat-simulator (2026-05-29) measured 5-13 trades/combat at the
# rules floor — over-aggressive. The "may" choice is encoded as a
# threshold raise to 20, so the trade only fires when rolling would
# deliver many overflow dice we're better trading down for a
# guaranteed SW.
OTAKU_5TH_DAN_TRADE_THRESHOLD = 20


class OtakuBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Otaku Bushi School: Special Ability":
        # "After an attack against you is completely resolved, you may
        # make a lunge attack at your attacker as an interrupt action
        # at the cost of one action die."
        #
        # Wire the cost + register lunge as an interrupt skill so the
        # action-die accounting in BaseAttackStrategy.choose_action
        # works, then install the strategy that actually FIRES the
        # interrupt-lunge on post-resolution events (spec 014 Q1 fix
        # — combat-simulator confirmed the engine default
        # ``CounterattackInterruptStrategy`` never produces a lunge,
        # so the wired capability was structurally dead).
        #
        # WoundCheckStrategy04 (0.4 confidence threshold) — the 1st
        # Dan +1 WC die + 2nd Dan free raise on wound checks let the
        # Otaku tolerate a more aggressive (lower) WC threshold.
        # Matches the Hida/Matsu/Bayushi default for WC-boosting
        # bushi schools.
        character.set_interrupt_cost("lunge", 1)
        character.add_interrupt_skill("lunge")
        self._set_school_strategy(character, "interrupt", OtakuInterruptLungeStrategy())
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())
        # The engine's built-in listener slots only dispatch
        # interrupt_strategy() on AttackDeclaredEvent / AttackRolledEvent
        # / PostDamageInterruptCheckEvent. Otaku's rules-text trigger
        # is "after an attack against you is completely resolved" —
        # AttackSucceededEvent / AttackFailedEvent. Install a school-
        # owned dispatch listener on those two slots so the strategy
        # actually fires.
        resolved_listener = OtakuAttackResolvedListener()
        self._set_school_listener(character, "attack_succeeded", resolved_listener)
        self._set_school_listener(character, "attack_failed", resolved_listener)

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "lw_damage", OtakuLightWoundsDamageListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_action_factory(character, OTAKU_ACTION_FACTORY)

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_take_action_event_factory(character, OTAKU_FIFTH_DAN_TAKE_ACTION_EVENT_FACTORY)

    def extra_rolled(self) -> list[str]:
        return ["iaijutsu", "lunge", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["wound check"]

    def name(self) -> str:
        return "Otaku Bushi School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self) -> str:
        return "fire"


class OtakuAttackResolvedListener(Listener):
    """Dispatches the Otaku interrupt-lunge strategy on attack
    resolution events.

    rules/04-schools.md "Otaku Bushi School: Special Ability":
    "After an attack against you is completely resolved, you may
    make a lunge attack at your attacker as an interrupt action..."

    The engine's default listener wiring dispatches
    ``interrupt_strategy()`` on ``AttackDeclaredEvent`` (pre-roll) and
    ``AttackRolledEvent`` (post-roll, pre-parry-resolution), but NOT
    on ``AttackSucceededEvent`` / ``AttackFailedEvent`` — which are
    the events that semantically match the rules text "completely
    resolved". This Otaku-specific listener fills that gap and is
    installed by ``apply_special_ability``.
    """

    def handle(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        if isinstance(event, (events.AttackSucceededEvent, events.AttackFailedEvent)):
            yield from character.interrupt_strategy().recommend(character, event, context)


class OtakuInterruptLungeStrategy(Strategy):
    """rules/04-schools.md "Otaku Bushi School: Special Ability":

    "After an attack against you is completely resolved, you may
    make a lunge attack at your attacker as an interrupt action at
    the cost of one action die."

    Fires on ``AttackSucceededEvent`` / ``AttackFailedEvent`` (the
    rules-text "completely resolved" trigger — post-resolution, unlike
    Hida's pre-roll counterattack which fires on
    ``AttackDeclaredEvent``).

    Includes two playability gates (Constitution Principle IX,
    confirmed essential by spec 014 school-strategy-designer audit):

    * **Mirror-recursion gate** — decline against an incoming attack
      that is itself an interrupt-lunge. Without this, two Otakus
      ricochet interrupt-lunges into each other forever; with it,
      Otaku-A attacks → Otaku-B interrupt-lunges → Otaku-A's slot
      sees B's lunge skill + is_interrupt → declines.
    * **SW-saturation gate** — decline at ``sw_remaining() <= 1``.
      Don't burn interrupt dice on offense when the next incoming
      damage is going to defeat us; let the WC strategy handle it.

    Per spec 014 T-C4, when the lunge fires the resulting action is
    tagged with ``_otaku_special_ability_interrupt = True`` so the
    trace can attribute the interrupt to the Special Ability.
    """

    THRESHOLD = 0.5  # Lunge gets +1 die (1st Dan) + 4th Dan parry-proof
                     # damage die, so modest confidence is workable.

    def _should_lunge(self, character: Any, event: Any, context: Any) -> bool:
        # Must be the target of the attack.
        if event.action.target() != character:
            return False
        attacker = event.action.subject()
        # Don't lunge at self.
        if attacker == character:  # pragma: no cover  # defensive: subject != target gate already ensured by target() check above
            return False
        # Must have the lunge skill.
        if character.skill("lunge") <= 0:
            return False
        # Must have an interrupt action available.
        if not character.has_interrupt_action("lunge", context):
            return False
        # SW-saturation gate.
        if character.sw_remaining() <= 1:
            return False
        # Mirror-recursion gate: decline against incoming interrupt-lunge.
        incoming_skill = event.action.skill()
        if incoming_skill == "lunge":
            incoming_ia = event.action.initiative_action()
            if incoming_ia.is_interrupt():
                return False
        # Adjacency check.  Under the engine-default ``NullFormation``
        # ``is_adjacent`` always returns True, so this branch only
        # affects tests / future Formation implementations.
        if not context.formation().is_adjacent(character, attacker):  # pragma: no cover  # defensive: NullFormation (engine default) returns True; only Formation subclasses exercise this branch
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
        initiative_action = self._choose_action(character, context)
        optimizer = character.attack_optimizer_factory().get_optimizer(
            character, attacker, "lunge", initiative_action, context,
        )
        attack = optimizer.optimize(self.THRESHOLD)
        if attack is None:
            return
        # Trace attribution tag (spec 014 T-C4).
        attack._otaku_special_ability_interrupt = True
        logger.info(
            f"{character.name()} interrupt-lunges at {attacker.name()} (Otaku Special Ability)"
        )
        yield events.SpendActionEvent(character, "lunge", initiative_action)
        yield character.take_action_event_factory().get_take_attack_action_event(attack)

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[Any]:
        if isinstance(event, (events.AttackSucceededEvent, events.AttackFailedEvent)):
            if self._should_lunge(character, event, context):
                yield from self._do_lunge(character, event, context)


class OtakuLightWoundsDamageListener(Listener):
    """
    Listener to implement the Otaku 3rd Dan technique:
    After dealing damage, increase target's next X action dice
    by (6 - target.fire, min 1), max phase 10.
    X is the number of action dice affected.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.subject == character and event.target != character:
                target = event.target
                increase = max(1, 6 - target.ring("fire"))
                # Rules/04-schools.md Otaku 3rd Dan: "next X action dice this turn"
                # where X = Otaku's attack skill. Sort so we modify the
                # chronologically-earliest X dice (the "next" ones), cap each at
                # phase 10, then re-sort to preserve phase order.
                actions = target.actions()
                actions.sort()
                attack_skill = character.skill("attack")
                for i in range(min(attack_skill, len(actions))):
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

    def calculate_extra_damage_dice(self, skill_roll: int | None = None, tn: int | None = None) -> int:
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        if self.parry_attempted():
            # Still get +1 even when parried
            return 1
        assert skill_roll is not None
        return ((skill_roll - tn) // 5) + 1


class OtakuActionFactory(DefaultActionFactory):
    """
    ActionFactory to return Otaku-specific attack actions.
    """

    def get_attack_action(self, subject: Any, target: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        if skill == "lunge":
            return OtakuLungeAction(subject, target, skill, initiative_action, context, vp=vp)
        return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


OTAKU_ACTION_FACTORY = OtakuActionFactory()


class OtakuFifthDanTakeAttackActionEvent(TakeAttackActionEvent):
    """
    Custom TakeAttackActionEvent for the Otaku 5th Dan ability:
    After a successful attack or lunge roll, decrease the number of
    rolled damage dice by 10 (to a minimum of 2) to automatically
    deal 1 serious wound to the opponent.
    """

    def play(self, context: Any) -> Iterator[Any]:
        yield self._declare_attack()
        if not self.action.subject().is_fighting():
            return
        yield from self._roll_attack(context)
        if self.action.parried():
            yield self._failed()
            return
        if self.action.is_hit():
            yield self._succeeded()
            direct_damage = self._direct_damage()
            if direct_damage is not None:
                yield direct_damage
            if self.action.target().is_fighting():
                yield from self._roll_damage()
        else:
            yield self._failed()

    def _roll_damage(self) -> Any:
        subject = self.action.subject()
        target = self.action.target()
        extra_rolled = self.action.calculate_extra_damage_dice()

        # Calculate raw rolled dice before normalization.
        ring = subject.ring(subject.get_skill_ring("damage"))
        my_extra_rolled = subject.extra_rolled("damage")
        raw_rolled = ring + my_extra_rolled + extra_rolled + subject.weapon().rolled()

        # rules/04-schools.md Otaku 5th Dan: "you may decrease the
        # number of rolled damage dice by 10, to a minimum of 2".
        # The "may" is a strategic CHOICE (spec 014 Q3): combat-simulator
        # at the rules-floor gate (raw_rolled >= 12) produced 5-13
        # trades/combat — over-aggressive. The strategic threshold of
        # 22 reserves the trade for rolls where the resulting damage
        # would already deliver overwhelming overflow; the trade also
        # locks in 1 guaranteed SW regardless of the target's WC.
        # The rules-floor of 12 is a strict subset of >= 22, so we
        # don't need both gates.
        if raw_rolled >= OTAKU_5TH_DAN_TRADE_THRESHOLD:
            # Trade 10 rolled dice for 1 automatic serious wound.
            # Tag the SW event for trace attribution (spec 014 T-C2).
            sw_event = SeriousWoundsDamageEvent(subject, target, 1)
            sw_event._from_otaku_5th_dan = True  # type: ignore[attr-defined]
            yield sw_event
            # Roll damage with reduced rolled dice. The algebra is
            # `(ring + weapon + my_extra) + (extra_rolled - 10)` which
            # equals `raw_rolled - 10`. Since raw_rolled >= 20 here
            # (T-A3 strategic threshold above the rules-floor of 12),
            # the result is always >= 10 — well above the rules-text
            # "minimum of 2" floor.
            reduced_extra = extra_rolled - 10
            # Mark the action so the damage breakdown formatter can
            # attribute the dice reduction to the 5th Dan trade
            # (spec 014 T-C2).
            self.action._otaku_5th_dan_traded = True
            damage_roll = subject.roll_damage(target, self.action.skill(), reduced_extra, self.action.vp())
            damage_roll = max(0, damage_roll)
            self.action.set_damage_roll(damage_roll)
            yield LightWoundsDamageEvent(subject, target, damage_roll)
        else:
            # Standard damage roll.
            damage_roll = self.action.roll_damage()
            yield LightWoundsDamageEvent(subject, target, damage_roll)


class OtakuFifthDanTakeActionEventFactory(DefaultTakeActionEventFactory):
    """
    TakeActionEventFactory for the Otaku 5th Dan ability.
    Returns OtakuFifthDanTakeAttackActionEvent for attacks.
    """

    def get_take_attack_action_event(self, action: Any) -> Any:
        if isinstance(action, AttackAction):
            return OtakuFifthDanTakeAttackActionEvent(action)
        else:
            raise ValueError("get_take_attack_action_event only supports AttackAction")


OTAKU_FIFTH_DAN_TAKE_ACTION_EVENT_FACTORY = OtakuFifthDanTakeActionEventFactory()
