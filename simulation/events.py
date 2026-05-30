#!/usr/bin/env python3

#
# events.py
#
# Events for the L7R combat simulator.
#

from collections.abc import Iterator
from typing import Any

from simulation.log import logger


class Event:
    """
    Events capture a moment in L7R combat mechanics when a character
    is affected, or a decision must be made.
    Examples:
     * new phase: characters with actions should decide what to do
     * attack rolled: characters should decide whether to parry
     * light wounds: character might decide to spend VP on wound check

    Events are basically messages. They should be treated as immutable.
    Other classes should never modify an event!

    Since we have the convention that events are immutable, we can also
    have the convention that other classes are expected to access members
    of events directly.

    Some events have a **play** method. This is a generator method that
    yields more events. This should only be done in exceptional
    circumstances.

    Every event can have different fields depending on the event,
    but there was some effort to have a kind of consistent vocabulary.
    **Subject**: if an event involves a character who is actively doing
                 something, the **subject** of the event is the active
                 character.
    **Target**:  if an event involves a character who is the direct
                 object of something - such as being attacked, or taking
                 damage - then the **target** of the event is that
                 character.
    **Damage**:  events about damage, whether they're for receiving light
                 wound, receiving serious wounds, or making a wound check,
                 have a **damage** member for the amount of damage.
    """

    def __init__(self, name: str) -> None:
        self.name = name


class TimingEvent(Event):
    pass


class NewRoundEvent(TimingEvent):
    def __init__(self, round: int) -> None:
        super().__init__("new_round")
        self.round = round


class NewPhaseEvent(TimingEvent):
    def __init__(self, phase: int) -> None:
        super().__init__("new_phase")
        self.phase = phase


class EndOfPhaseEvent(TimingEvent):
    def __init__(self, phase: int) -> None:
        super().__init__("end_of_phase")
        self.phase = phase


class EndOfRoundEvent(TimingEvent):
    def __init__(self, round: int) -> None:
        super().__init__("end_of_round")
        self.round = round


class YourMoveEvent(Event):
    """
    Played on characters to ask them if they will use an action.
    """

    def __init__(self, subject: Any) -> None:
        super().__init__("your_move")
        self.subject = subject


class InitiativeChangedEvent(Event):
    def __init__(self) -> None:
        super().__init__("initiative_changed")


class ActionEvent(Event):
    def __init__(self, name: str, action: Any) -> None:
        super().__init__(name)
        self.action = action


class ContestedActionEvent(Event):
    def __init__(self, name: str, contested_action: Any) -> None:
        super().__init__(name)
        self.action = contested_action


class TakeActionEvent(ActionEvent):
    def __init__(self, name: str, action: Any) -> None:
        super().__init__(name, action)


class TakeAttackActionEvent(TakeActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("take_attack", action)

    def play(self, context: Any) -> Iterator["Event"]:
        yield self._declare_attack()
        # Counterattack may have killed/incapacitated the attacker
        if not self.action.subject().is_fighting():
            return
        yield from self._roll_attack(context)
        if self.action.parried():
            yield self._failed()
            return
        if self.action.is_hit():
            yield self._succeeded()
            # A listener (e.g. Monk 5th Dan) may cancel the attack
            # after it succeeded but before damage is rolled.
            if self.action.parried():
                return
            direct_damage = self._direct_damage()
            if direct_damage is not None:
                yield direct_damage
            if self.action.target().is_fighting():
                yield self._roll_damage()
                # rules/04-schools.md "Hida Bushi School: Fifth Dan":
                # After the damage event resolves fully (LW added, WC
                # fired, SW potentially inflicted), give characters
                # whose interrupt strategy supports deferred decisions
                # (5th-Dan Hidas via HidaCounterattackInterruptStrategy)
                # a chance to counterattack now.  The event is a no-op
                # for other characters.  Only fires while the target is
                # still able to act.
                if self.action.target().is_fighting():
                    yield PostDamageInterruptCheckEvent(self.action)
        else:
            yield self._failed()

    def _declare_attack(self) -> "AttackDeclaredEvent":
        return AttackDeclaredEvent(self.action)

    def _direct_damage(self) -> Any:
        return self.action.direct_damage()

    def _failed(self) -> "AttackFailedEvent":
        logger.info(f"{self.action.subject().name()} failed to attack {self.action.target().name()} with {self.action.skill()}")
        return AttackFailedEvent(self.action)

    def _roll_attack(self, context: Any) -> Iterator["Event"]:
        attack_roll = self.action.roll_skill()
        # Apply any pending counterattack roll bonus (e.g. Hida school +5)
        bonus = getattr(self.action, '_counterattack_roll_bonus', 0)
        if bonus:
            attack_roll += bonus
            self.action.set_skill_roll(attack_roll)
        # Cap VP spending to what's actually available. VP may have been
        # consumed by intervening events (e.g. wound checks from counterattacks).
        vp_to_spend = min(self.action.vp(), self.action.subject().vp())
        if vp_to_spend > 0:
            yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), vp_to_spend)
        initial_event = AttackRolledEvent(self.action, attack_roll)
        yield from self.action.subject().attack_rolled_strategy().recommend(self.action.subject(), initial_event, context)

    def _roll_damage(self) -> "LightWoundsDamageEvent":
        damage_roll = self.action.roll_damage()
        return LightWoundsDamageEvent(
            self.action.subject(), self.action.target(), damage_roll,
            attack_action=self.action,
        )

    def _succeeded(self) -> "AttackSucceededEvent":
        logger.info(f"{self.action.subject().name()} successfully attacked {self.action.target().name()} with {self.action.skill()}")
        return AttackSucceededEvent(self.action)


class TakeParryActionEvent(TakeActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("take_parry", action)

    def play(self, context: Any) -> Iterator["Event"]:
        yield self._declare_parry()
        yield from self._roll_parry(context)
        if self.action.is_success():
            yield self._succeeded()
            return
        else:
            yield self._failed()

    def _declare_parry(self) -> "ParryDeclaredEvent":
        declaration = ParryDeclaredEvent(self.action)
        self.action.set_attack_parry_declared(declaration)
        return declaration

    def _failed(self) -> "ParryFailedEvent":
        logger.info(f"{self.action.subject().name()} failed to parry {self.action.target().name()}")
        return ParryFailedEvent(self.action)

    def _roll_parry(self, context: Any) -> Iterator["Event"]:
        parry_roll = self.action.roll_skill()
        self.action.set_attack_parry_attempted()
        # Cap VP spending to what's actually available.
        vp_to_spend = min(self.action.vp(), self.action.subject().vp())
        if vp_to_spend > 0:
            yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), vp_to_spend)
        initial_event = ParryRolledEvent(self.action, parry_roll)
        yield from self.action.subject().parry_rolled_strategy().recommend(self.action.subject(), initial_event, context)

    def _succeeded(self) -> "ParrySucceededEvent":
        logger.info(f"{self.action.subject().name()} successfully parried {self.action.target().name()}")
        self.action.set_attack_parried()
        return ParrySucceededEvent(self.action)


class AttackDeclaredEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("attack_declared", action)


class AttackRolledEvent(ActionEvent):
    def __init__(self, action: Any, roll: int) -> None:
        super().__init__("attack_rolled", action)
        self.roll = roll


class AttackSucceededEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("attack_succeeded", action)


class AttackFailedEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("attack_failed", action)


class ParryDeclaredEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("parry_declared", action)


class ParryPredeclaredEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("parry_predeclared", action)


class ParryRolledEvent(ActionEvent):
    def __init__(self, action: Any, roll: int) -> None:
        super().__init__("parry_rolled", action)
        self.roll = roll


class ParrySucceededEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("parry_succeeded", action)


class ParryFailedEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("parry_failed", action)


class TakeCounterattackActionEvent(TakeActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("take_counterattack", action)

    def play(self, context: Any) -> Iterator["Event"]:
        yield CounterattackDeclaredEvent(self.action)
        self.action.roll_skill()
        # Cap VP spending to what's actually available.
        vp_to_spend = min(self.action.vp(), self.action.subject().vp())
        if vp_to_spend > 0:
            yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), vp_to_spend)
        yield CounterattackRolledEvent(self.action, self.action.skill_roll())
        if self.action.is_hit():
            yield CounterattackSucceededEvent(self.action)
            if self.action.target().is_fighting():
                damage = self.action.roll_damage()
                yield LightWoundsDamageEvent(self.action.subject(), self.action.target(), damage)
        else:
            yield CounterattackFailedEvent(self.action)


class CounterattackDeclaredEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("counterattack_declared", action)


class CounterattackRolledEvent(ActionEvent):
    def __init__(self, action: Any, roll: int) -> None:
        super().__init__("counterattack_rolled", action)
        self.roll = roll


class CounterattackSucceededEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("counterattack_succeeded", action)


class CounterattackFailedEvent(ActionEvent):
    def __init__(self, action: Any) -> None:
        super().__init__("counterattack_failed", action)


class DamageEvent(Event):
    """
    Event used when a character takes damage.

    The "subject" is the character who inflicted the damage.
    The "target" is the character who is receiving the damage.
    The "damage" is the amount of damage inflicted.
    """

    def __init__(self, name: str, subject: Any, target: Any, damage: int) -> None:
        super().__init__(name)
        self.subject = subject
        self.target = target
        if not isinstance(damage, int):
            raise ValueError("damage parameter must be int")
        self.damage = damage


class LightWoundsDamageEvent(DamageEvent):
    """
    The LightWoundsDamageEvent also has the "wound_check_tn" field,
    which is the base TN to succeed at the Wound Check.

    Normally this is the character's Light Wound total, but there
    are certain abilities that modify the TN.

    The optional ``source`` field carries a human-readable attribution
    for the trace formatter (Constitution Principle VII).  When set,
    the user-facing combat trace renders the damage with the source
    name (e.g., ``"Akodo 5th Dan: spent 3 VP on counter-damage, 10
    LW × 3 = 30 LW dealt to <attacker>"``).  Emitters that do not set
    ``source`` get the generic primary-damage rendering.  See
    rules/04-schools.md "Akodo Bushi School: Fifth Dan".

    The optional ``attack_action`` field carries the originating
    ``AttackAction`` (or ``CounterattackAction``) reference so downstream
    listeners can consult per-action annotations such as
    ``_counterattack_excess_margin`` (set by the Hida 5th Dan ability)
    on the corresponding wound check.  rules/04-schools.md
    "Hida Bushi School: Fifth Dan".
    """

    def __init__(
        self,
        subject: Any,
        target: Any,
        damage: int,
        tn: int | None = None,
        duel: bool = False,
        source: str | None = None,
        attack_action: Any = None,
    ) -> None:
        super().__init__("lw_damage", subject, target, damage)
        if tn is None:
            self.wound_check_tn = damage
        else:
            if not isinstance(tn, int):
                raise ValueError("tn parameter must be int")
            self.wound_check_tn = tn
        self.duel = duel
        self.source = source
        self.attack_action = attack_action


class SeriousWoundsDamageEvent(DamageEvent):
    def __init__(self, subject: Any, target: Any, damage: int) -> None:
        super().__init__("sw_damage", subject, target, damage)


class StatusEvent(Event):
    def __init__(self, name: str, subject: Any) -> None:
        super().__init__(name)
        self.subject = subject


class CrippledEvent(StatusEvent):
    def __init__(self, name: str, subject: Any) -> None:
        super().__init__("crippled", subject)


class NotCrippledEvent(StatusEvent):
    def __init__(self, subject: Any) -> None:
        super().__init__("not_crippled", subject)


class DefeatEvent(StatusEvent):
    pass


class DeathEvent(DefeatEvent):
    def __init__(self, subject: Any) -> None:
        super().__init__("death", subject)


class SurrenderEvent(DefeatEvent):
    def __init__(self, subject: Any) -> None:
        super().__init__("surrender", subject)


class UnconsciousEvent(DefeatEvent):
    def __init__(self, subject: Any) -> None:
        super().__init__("unconscious", subject)


class NotMovingEvent(StatusEvent):
    pass


class HoldActionEvent(NotMovingEvent):
    """
    Response by characters to YourMoveEvent to indicate they are holding their action.
    """

    def __init__(self, subject: Any) -> None:
        super().__init__("hold_action", subject)


class NoActionEvent(NotMovingEvent):
    """
    Response by characters to YourMoveEvent to indicate they have no action.
    """

    def __init__(self, subject: Any) -> None:
        super().__init__("no_action", subject)


class WoundCheckEvent(Event):
    """
    Event for a character's wound check.

    The "subject" is the character making the wound check.
    The "attacker" is the character who inflicted the damage.
    The "damage" is the character's total Light Wounds for the
    wound check (including new damage as well as previous damage).
    The "tn" is the base TN for the wound check, which normally is
    the amount of damage.
    """

    def __init__(self, name: str, subject: Any, attacker: Any, damage: int, tn: int | None = None) -> None:
        super().__init__(name)
        self.subject = subject
        self.attacker = attacker
        self.damage = damage
        if tn is None:
            self.tn = damage
        else:
            self.tn = tn


class WoundCheckDeclaredEvent(WoundCheckEvent):
    def __init__(
        self,
        subject: Any,
        attacker: Any,
        damage: int,
        tn: int | None = None,
        vp: int = 0,
        duel: bool = False,
        attack_action: Any = None,
    ) -> None:
        super().__init__("wound_check_declared", subject, attacker, damage, tn=tn)
        self.vp = vp
        self.duel = duel
        # rules/04-schools.md "Hida Bushi School: Fifth Dan": when the
        # WC is on damage from a successfully counterattacked attack,
        # the WC listener consults
        # ``attack_action._counterattack_excess_margin`` to add the
        # excess to the roll.
        self.attack_action = attack_action


class WoundCheckFailedEvent(WoundCheckEvent):
    def __init__(self, subject: Any, attacker: Any, damage: int, roll: int, tn: int | None = None) -> None:
        super().__init__("wound_check_failed", subject, attacker, damage, tn=tn)
        self.roll = roll


class WoundCheckRolledEvent(WoundCheckEvent):
    def __init__(self, subject: Any, attacker: Any, damage: int, roll: int, tn: int | None = None) -> None:
        super().__init__("wound_check_rolled", subject, attacker, damage, tn=tn)
        self.roll = roll


class WoundCheckSucceededEvent(WoundCheckEvent):
    def __init__(self, subject: Any, attacker: Any, damage: int, roll: int, tn: int | None = None) -> None:
        super().__init__("wound_check_succeeded", subject, attacker, damage, tn=tn)
        self.roll = roll


class KeepLightWoundsEvent(WoundCheckEvent):
    def __init__(self, subject: Any, attacker: Any, damage: int, tn: int | None = None) -> None:
        super().__init__("keep_lw", subject, attacker, damage, tn=tn)


class TakeSeriousWoundEvent(WoundCheckEvent):
    def __init__(self, subject: Any, attacker: Any, damage: int, tn: int | None = None) -> None:
        super().__init__("take_sw", subject, attacker, damage, tn=tn)


class PostDamageInterruptCheckEvent(ActionEvent):
    """
    rules/04-schools.md "Hida Bushi School: Fifth Dan":
      "You may choose to counterattack after seeing an opponent's
       damage roll, but that roll goes through even if your
       counterattack impairs or kills the opponent."

    This event fires AFTER a ``LightWoundsDamageEvent`` has been fully
    resolved (LW added, WC fired, SW potentially inflicted) but BEFORE
    the attack flow concludes.  It exists to give a 5th-Dan Hida — or
    any future school with deferred-counterattack mechanics — a chance
    to counterattack with full information about the damage taken.

    The event carries the originating ``AttackAction`` so the interrupt
    strategy can wire the counterattack back to the original attacker.

    A character's ``interrupt_strategy().recommend(...)`` is consulted on
    this event via ``PostDamageInterruptCheckListener``.  Strategies that
    do not implement the post-damage decision (i.e., not a 5th-Dan Hida)
    simply yield no events — the event is a no-op for them.
    """

    def __init__(self, action: Any) -> None:
        super().__init__("post_damage_interrupt_check", action)


class MatsuLightWoundsFloorEvent(Event):
    """
    Trace-observability event emitted by ``MatsuSeriousWoundsDamageListener``
    when the Matsu 5th Dan LW-floor activates: instead of the standard
    "defender LW reset to 0" after a failed wound check, the defender's
    LW is set to 15.

    rules/04-schools.md "Matsu Bushi School: Fifth Dan":
      "When you cause a defender to take one or more serious wounds,
       their light wound total is reset to 15 instead of 0."

    The engine has NO handler for this event -- the listener already
    set the defender's LW to 15 directly.  Its sole purpose is to
    surface the LW-floor with explicit "Matsu 5th Dan" attribution in
    the user-facing combat trace (Constitution Principle VII / FR-023).

    ``attacker``: the Matsu whose attack caused the failed wound check.
    ``defender``: the character whose LW was set to 15.
    ``lw_set_to``: always 15 (per rules text), kept as a field for
                   forward-compatibility and explicit numeric breakdown.
    """

    def __init__(self, attacker: Any, defender: Any, lw_set_to: int = 15) -> None:
        super().__init__("matsu_lw_floor")
        self.attacker = attacker
        self.defender = defender
        self.lw_set_to = lw_set_to


class HidaSWForLWTradeEvent(Event):
    """
    Hida 4th Dan alternative wound check: trade 2 Serious Wounds for
    reducing the character's Light Wounds to 0.

    rules/04-schools.md "Hida Bushi School: Fourth Dan":
      "Instead of making a wound check, you may choose to take 2
       serious wounds to reduce your light wounds to 0.  You may not
       do this during the iaijutsu phase of a duel."

    The event FULLY REPLACES the wound check.  When the strategy
    elects the trade, NO ``WoundCheckDeclaredEvent`` / ``...Rolled`` /
    ``...Succeeded`` etc. is emitted on the trade path.

    ``character``: the Hida taking the trade.
    ``attacker``: the character whose damage triggered this trade (so
                  downstream SW + status events have a consistent
                  attacker subject — used by knowledge / observation).
    ``lw_reset_from``: the LW value BEFORE the trade (for trace
                  attribution per Constitution Principle VII).
    ``sw_taken``: always 2 (per rules text).

    On ``play``:
      1. Resets the character's LW to 0 directly.
      2. Yields a ``SeriousWoundsDamageEvent`` so the standard SW
         listener pipeline handles ``take_sw(2)`` plus the resulting
         crippled / unconscious / death checks.
    """

    def __init__(self, character: Any, attacker: Any, lw_reset_from: int) -> None:
        super().__init__("hida_sw_for_lw_trade")
        self.character = character
        self.attacker = attacker
        self.lw_reset_from = lw_reset_from
        self.sw_taken = 2

    def play(self, context: Any) -> Iterator["Event"]:
        # Reset LW directly (the LW total was already updated by the
        # LightWoundsDamageListener before the strategy was consulted).
        self.character.reset_lw()
        # Yield a SeriousWoundsDamageEvent so the standard SW listener
        # adds 2 SW and runs status checks (crippled / unconscious /
        # death) — the trade should NOT be exempt from those.
        yield SeriousWoundsDamageEvent(self.attacker, self.character, 2)


class GainResourcesEvent(Event):
    def __init__(self, name: str, subject: Any, amount: int) -> None:
        super().__init__(name)
        self.subject = subject
        self.amount = amount


class GainTemporaryVoidPointsEvent(GainResourcesEvent):
    """
    Event emitted when a character gains temporary void points (TVP),
    a stackable above-cap pool that resets at combat boundaries.

    The optional ``source`` field carries the human-readable attribution
    for the trace formatter (Constitution Principle VII): when set, the
    user-facing combat trace renders the gain with the source name
    (e.g., ``"Akodo Special Ability: +4 TVP on successful feint"``).
    Emitters that do not set ``source`` get a generic rendering.
    """

    def __init__(self, subject: Any, amount: int, source: str | None = None) -> None:
        super().__init__("gain_tvp", subject, amount)
        self.source = source


class SpendActionEvent(Event):
    """
    Event for when a character spends an action die.
    """

    def __init__(self, subject: Any, skill: str, initiative_action: Any) -> None:
        super().__init__("spend_action")
        self.subject = subject
        self.skill = skill
        self.initiative_action = initiative_action


class SpendResourcesEvent(Event):
    """
    Event for when a character spends resources that can be measured in an amount.

    The "subject" is the character spending resources.
    The "skill" is the skill the resources are being spent on.
    This may be something that is not really a skill, such as "wound check" or "damage".
    The "amount" is the amount of the resource being spent.
    """

    def __init__(self, name: str, subject: Any, skill: str, amount: int) -> None:
        super().__init__(name)
        self.subject = subject
        self.skill = skill
        self.amount = amount


class SpendAdventurePointsEvent(SpendResourcesEvent):
    def __init__(self, subject: Any, skill: str, amount: int) -> None:
        super().__init__("spend_ap", subject, skill, amount)


class SpendConvictionEvent(SpendResourcesEvent):
    def __init__(self, subject: Any, skill: str, amount: int) -> None:
        super().__init__("spend_conviction", subject, skill, amount)


class SpendVoidPointsEvent(SpendResourcesEvent):
    """
    Event emitted when a character spends Void Points on a roll or
    other action.

    The optional ``source`` field carries the human-readable attribution
    for the trace formatter (Constitution Principle VII).  When set,
    the user-facing combat trace renders the spend with the source
    name (e.g. ``"Akodo 4th Dan: spent 2 VP on wound check, +5 per
    VP = +10 to roll"``).  Emitters that do not set ``source`` get the
    generic rendering.
    """

    def __init__(
        self, subject: Any, skill: str, amount: int, source: str | None = None,
    ) -> None:
        super().__init__("spend_vp", subject, skill, amount)
        self.source = source


class SpendFloatingBonusEvent(Event):
    """
    Event for when a character spends a floating bonus.
    Since floating bonuses are discrete and not measured in an "amount",
    they aren't a good fit for a SpendResourcesEvent.
    """

    def __init__(self, subject: Any, bonus: Any) -> None:
        super().__init__("spend_floating_bonus")
        self.subject = subject
        self.bonus = bonus


class GainFloatingBonusEvent(Event):
    """
    Trace-observability event emitted when a character gains a floating
    bonus from a school ability.  The engine does NOT need to handle
    this event -- the bonus is appended directly via
    ``Character.gain_floating_bonus`` in the same listener that emits
    this event.  Its sole purpose is to surface the acquisition in the
    user-facing combat trace per Constitution Principle VII.

    ``source`` is the human-readable attribution (e.g.
    ``"Akodo 3rd Dan"``).  ``breakdown`` is an optional explanatory
    string (e.g. ``"margin 20 ÷ 5 × attack 5"``) -- when set, the
    formatter MAY render it for the numeric breakdown clause of
    Principle VII.
    """

    def __init__(
        self,
        subject: Any,
        bonus: Any,
        source: str | None = None,
        breakdown: str | None = None,
    ) -> None:
        super().__init__("gain_floating_bonus")
        self.subject = subject
        self.bonus = bonus
        self.source = source
        self.breakdown = breakdown


class ModifierEvent(Event):
    """
    Event for when a character is affected by a Modifier.
    """

    def __init__(self, name: str, subject: Any, modifier: Any) -> None:
        super().__init__(name)
        self.subject = subject
        self.modifier = modifier


class AddModifierEvent(ModifierEvent):
    """
    Event for when a character gains a modifier.
    """

    def __init__(self, subject: Any, modifier: Any) -> None:
        super().__init__("add_modifier", subject, modifier)


class RemoveModifierEvent(ModifierEvent):
    """
    Event for when a character loses a modifier.
    """

    def __init__(self, subject: Any, modifier: Any) -> None:
        super().__init__("remove_modifier", subject, modifier)


class SchoolNegatedEvent(Event):
    """
    Event emitted when the Isawa Ishi 5th Dan ability negates an opposing
    character's school for the duration of a fight (rules/04-schools.md
    "Isawa Ishi School: 5th Dan").

    The ``negator`` is the Ishi character spending VP to negate.
    The ``target`` is the character whose school is being negated.
    The ``vp_cost`` is the amount of VP the negator paid.
    The ``target_school_name`` is the human-readable name of the negated
    school, captured at emit time for the trace/UI adapters.
    """

    def __init__(
        self,
        negator: Any,
        target: Any,
        vp_cost: int,
        target_school_name: str,
    ) -> None:
        super().__init__("school_negated")
        self.negator = negator
        self.target = target
        if not isinstance(vp_cost, int):
            raise ValueError("vp_cost parameter must be int")
        self.vp_cost = vp_cost
        if not isinstance(target_school_name, str):
            raise ValueError("target_school_name parameter must be str")
        self.target_school_name = target_school_name


class KitsukiRingReductionEvent(Event):
    """Event emitted when the Kitsuki 5th Dan ability reduces a
    target's Air, Fire, and Water rings by 1 each at the start of
    combat (rules/04-schools.md "Kitsuki Magistrate School: 5th
    Dan").

    Surfaced as its own event so the trace observer/formatter can
    render an explicit line — pre-2026-05-30 the ability fired via a
    bare ``logger.info`` that observers never saw, making the most
    important Kitsuki ability invisible in the trace (trace-reader
    sweep finding).

    The ``subject`` is the Kitsuki character. The ``target`` is the
    chosen opponent. ``ring_values_before`` is a dict mapping the
    three affected ring names to their pre-reduction value so the
    reader can see what changed.
    """

    def __init__(
        self,
        subject: Any,
        target: Any,
        ring_values_before: dict[str, int],
    ) -> None:
        super().__init__("kitsuki_ring_reduction")
        self.subject = subject
        self.target = target
        if not isinstance(ring_values_before, dict):
            raise ValueError("ring_values_before must be a dict")
        self.ring_values_before = dict(ring_values_before)


class MerchantRerollEvent(Event):
    """Event emitted when the Merchant 5th Dan ability rerolls dice
    (rules/04-schools.md "Merchant School: 5th Dan": after any
    non-initiative roll, may reroll some dice so long as the rerolled
    dice sum to at least 5×(X-1) where X is the number being
    rerolled).

    Surfaced as its own event so the trace can show which dice were
    rerolled and what they became — pre-2026-05-30 the reroll fired
    via ``logger.debug`` inside the roll provider and was invisible
    in the trace (trace-reader sweep finding).

    ``subject`` is the Merchant. ``roll_type`` is a short label for
    which roll the reroll applied to (``"skill"``, ``"wound_check"``,
    ``"damage"``). ``rerolled_pairs`` is a list of ``(before, after)``
    tuples — one per rerolled die.
    """

    def __init__(
        self,
        subject: Any,
        roll_type: str,
        rerolled_pairs: list[tuple[int, int]],
    ) -> None:
        super().__init__("merchant_reroll")
        self.subject = subject
        if not isinstance(roll_type, str):
            raise ValueError("roll_type must be a str")
        self.roll_type = roll_type
        if not isinstance(rerolled_pairs, list):
            raise ValueError("rerolled_pairs must be a list")
        self.rerolled_pairs = list(rerolled_pairs)


class CounterDamageDealtEvent(Event):
    """Event emitted when the Akodo 5th Dan ability deals
    counter-damage as raw LW to the original attacker
    (rules/04-schools.md "Akodo Bushi School: 5th Dan").

    Companion to the ``Akodo 5th Dan: spends N VP on counter-damage``
    line — emitted right after so the trace shows a discrete
    ``💥 takes M LW (total: K)`` event with running total, matching
    the rendering pattern of normal damage events. Pre-2026-05-30
    the counter-damage was asserted inline (``10 LW × N = M LW
    dealt to <target>``) but no follow-up LW-applied event fired,
    forcing the reader to infer the target's new LW total from the
    next wound check's TN (trace-reader sweep finding).

    ``subject`` is the counter-damaged character (the one taking
    LW). ``source`` is the Akodo dealing the damage. ``damage`` is
    the LW count. ``lw_after`` is the target's LW total AFTER the
    damage lands, for inline rendering as ``(total: K)``.
    """

    def __init__(
        self,
        subject: Any,
        source: Any,
        damage: int,
        lw_after: int,
    ) -> None:
        super().__init__("counter_damage_dealt")
        self.subject = subject
        self.source = source
        if not isinstance(damage, int):
            raise ValueError("damage must be int")
        self.damage = damage
        if not isinstance(lw_after, int):
            raise ValueError("lw_after must be int")
        self.lw_after = lw_after
