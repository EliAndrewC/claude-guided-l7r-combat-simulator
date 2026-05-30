#!/usr/bin/env python3

#
# actions.py
#
# Classes for combat actions in the L7R combat simulator.
#

from typing import Any

from simulation.events import SeriousWoundsDamageEvent
from simulation.mechanics.initiative_actions import InitiativeAction


class Action:
    """
    Action classes implement the details of making characters roll for
    an action, determining whether the action was successful, and
    providing a context for combat actions.

    Actions are played out using Event classes with play methods that
    generate events for the action. An Action class is set on the
    generated events, which is how it can serve as a context to
    coordinate between the characters and the playable event.
    """

    def __init__(self, subject: Any, target: Any, skill: str, initiative_action: InitiativeAction, context: Any, ring: str | None = None, vp: int = 0) -> None:
        """
        __init__(subject, target, skill, initiative_action, context, vp=0)
          subject (Character): character taking the action
          target (Character): target of the action
          skill (str): skill being used
          initiative_action (InitiativeAction): initiative action being used
          context (EngineContext): context for timing
          ring (str): ring used for skill roll. Defaults to None, which
            means the character's default skill ring is used.
          vp (int): Void Points spent on this action
        """
        self._subject = subject
        self._target = target
        if not isinstance(skill, str):
            raise ValueError("skill must be str")
        self._skill = skill
        if not isinstance(initiative_action, InitiativeAction):
            raise ValueError("initiative_action must be InitiativeAction")
        self._initiative_action = initiative_action
        self._context = context
        if ring is not None:
            if not isinstance(ring, str):
                raise ValueError("ring must be str")
        self._ring = ring
        if not isinstance(vp, int):
            raise ValueError("vp must be int")
        self._vp = vp
        self._skill_roll: int | None = None

    def context(self) -> Any:
        return self._context

    def damage_roll_params(self) -> Any:
        raise NotImplementedError()

    def initiative_action(self) -> InitiativeAction:
        return self._initiative_action

    def ring(self) -> str | None:
        return self._ring

    def roll_skill(self) -> int:
        self.set_skill_roll(self.subject().roll_skill(self.target(), self.skill(), ring=self.ring(), vp=self.vp()))
        roll = self.skill_roll()
        assert roll is not None
        # rules/04-schools.md "Hida Bushi School: Third Dan" — if the
        # subject's roll provider just performed a reroll on this
        # action's skill, capture the metadata on the action so the
        # trace formatter (Principle VII) can render the before/after
        # dice with source attribution next to the attack entry.
        provider = self.subject().roll_provider()
        get_reroll = getattr(provider, "last_hida_3rd_dan_reroll", None)
        if callable(get_reroll):
            info = get_reroll()
            if info is not None:
                self._hida_3rd_dan_reroll = info
        return roll

    def set_skill_roll(self, roll: int) -> None:
        if not isinstance(roll, int):
            raise ValueError("set_skill_roll requires int")
        self._skill_roll = roll

    def set_vp(self, vp: int) -> None:
        self._vp = vp

    def skill(self) -> str:
        return self._skill

    def skill_roll(self) -> int | None:
        return self._skill_roll

    def skill_roll_params(self) -> Any:
        return self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())

    def subject(self) -> Any:
        return self._subject

    def target(self) -> Any:
        return self._target

    def vp(self) -> int:
        return self._vp


class AttackAction(Action):
    def __init__(self, subject: Any, target: Any, skill: str, initiative_action: InitiativeAction, context: Any, ring: str | None = None, vp: int = 0) -> None:
        super().__init__(subject, target, skill, initiative_action, context, ring=ring, vp=vp)
        self._damage_roll: int | None = None
        self._damage_roll_params: Any = None
        self._parries_declared: list[Any] = []
        self._parries_declined: list[Any] = []
        self._parries_predeclared: list[Any] = []
        self._parried = False
        self._parry_attempted = False

    def add_parry_declared(self, event: Any) -> None:
        self._parries_declared.append(event)

    def add_parry_predeclared(self, event: Any) -> None:
        self._parries_predeclared.append(event)
        self.add_parry_declared(event)

    def add_parry_declined(self, character: Any) -> None:
        self._parries_declined.append(character)

    def calculate_extra_damage_dice(self, skill_roll: int | None = None, tn: int | None = None) -> int:
        """Extra damage dice from exceeding TN, modulated by parry.

        rules/03-combat.md "Damage":
            "you roll an extra die for every 5 by which your attack roll
            exceeded its TN.  If the defender attempted and failed to
            parry, the number of these extra damage dice roll is
            decreased by the defender's parry skill."

        Updated 2026-05-30: the rules text used to read "you don't roll
        these extra damage dice" — i.e., a failed parry zeroed the
        entire margin extras. The new rule reduces by the defender's
        parry-skill rank (min 0), so a high-parry defender can still
        wipe out the extras but a low-parry defender only blunts them.
        """
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        assert skill_roll is not None
        extras = (skill_roll - tn) // 5
        # Failed-parry reduction (rules-text: "the defender attempted
        # AND FAILED to parry"). Successful parries make the attack
        # fail entirely so damage isn't normally computed; gate on
        # ``not parried`` for the hypothetical-evaluation case.
        if self.parry_attempted() and not self.parried():
            reduction: int = self.target().skill("parry")
            extras = max(0, extras - reduction)
        return int(extras)

    def damage_roll(self) -> int | None:
        return self._damage_roll

    def damage_roll_params(self) -> Any:
        if self.skill_roll() is None:
            return None
        extra_rolled = self.calculate_extra_damage_dice()
        rolled, kept, mod = self.subject().get_damage_roll_params(self.target(), self.skill(), extra_rolled, self.vp())
        return (rolled, kept, mod)

    def damage_breakdown(self) -> list[tuple[str, int, int]]:
        """Per-source breakdown of this action's damage roll parameters.

        Default: delegates to the subject's ``RollParameterProvider``
        with ``kind='damage'`` and the same ``attack_extra_rolled`` /
        ``vp`` arguments used by ``damage_roll_params``.  Subclasses
        that override ``damage_roll_params`` (e.g. ``FeintAction``,
        ``BayushiFeintAction``) MUST override this method too so the
        formatter's projection breakdown agrees with the actual roll —
        spec 009 (Action-Level Damage Breakdown).

        Returns ``[]`` when the provider has no decomposition for the
        damage roll (legacy providers without ``get_breakdown`` or
        providers that raise).  The formatter then omits the inline
        breakdown rather than emitting a misleading one.
        """
        provider = self.subject().roll_parameter_provider()
        if not hasattr(provider, "get_breakdown"):
            return []
        try:
            extra_rolled = self.calculate_extra_damage_dice()
        except (AssertionError, TypeError):
            # No skill_roll set yet — the formatter call-sites only
            # invoke this after the attack has rolled.  Defensive
            # fallback: treat as zero margin extras.
            extra_rolled = 0
        try:
            result = provider.get_breakdown(
                self.subject(), self.target(), self.skill(),
                kind="damage",
                attack_extra_rolled=extra_rolled,
                vp=self.vp(),
            )
        except Exception:
            return []
        if not isinstance(result, list):
            return []
        return result

    def direct_damage(self) -> Any:
        return None

    def is_hit(self) -> bool:
        roll = self.skill_roll()
        assert roll is not None
        return roll >= self.tn() and not self.parried()

    def parried(self) -> bool:
        return self._parried

    def parry_attempted(self) -> bool:
        return self._parry_attempted

    def parries_declared(self) -> list[Any]:
        return self._parries_declared

    def parries_declined(self) -> list[Any]:
        return self._parries_declined

    def parries_predeclared(self) -> list[Any]:
        return self._parries_predeclared

    def parry_tn(self) -> int:
        roll = self.skill_roll()
        assert roll is not None
        return roll

    def roll_damage(self) -> int:
        extra_rolled = self.calculate_extra_damage_dice()
        damage_roll: int = self.subject().roll_damage(self.target(), self.skill(), extra_rolled, self.vp())
        damage_roll = max(0, damage_roll)
        self.set_damage_roll(damage_roll)
        return damage_roll

    def set_damage_roll(self, damage: int) -> None:
        if not isinstance(damage, int):
            raise ValueError("set_damage_roll requires int")
        self._damage_roll = damage

    def set_parry_attempted(self) -> None:
        self._parry_attempted = True

    def set_parried(self) -> None:
        self._parried = True

    def tn(self) -> int:
        result: int = self.target().tn_to_hit()
        return result


class CounterattackAction(AttackAction):
    def __init__(self, subject: Any, target: Any, skill: str, initiative_action: InitiativeAction, context: Any, attack: Any, ring: str | None = None, vp: int = 0) -> None:
        super().__init__(subject, target, skill, initiative_action, context, ring=ring, vp=vp)
        self._original_attack = attack

    def attack(self) -> Any:
        return self._original_attack

    def tn(self) -> int:
        penalty = 0 if self.attack().target() == self.subject() else 5 * self.attack().subject().skill("parry")
        result: int = self.target().tn_to_hit() + penalty
        return result


class DoubleAttackAction(AttackAction):
    def calculate_extra_damage_dice(self, skill_roll: int | None = None, tn: int | None = None) -> int:
        """Double-attack extra damage dice.

        Rules text (rules/05-school_knacks.md "Double Attack"):
            "If successful, roll extra damage dice as if the TN hadn't
            been raised, and inflict a serious wound in addition to the
            normal damage roll. On an unsuccessful parry, this extra
            serious wound becomes 2 extra rolled damage dice, or 4
            extra rolled damage dice if someone else unsuccessfully
            parried for the target."

        Combined with rules/03-combat.md "Damage" (updated 2026-05-30):
            "If the defender attempted and failed to parry, the number
            of these extra damage dice roll is decreased by the
            defender's parry skill."

        So on a failed-parry double attack:
          (a) margin extras (as if TN hadn't been raised) decreased by
              defender's parry skill (min 0) — the general failed-parry
              rule applies to double attacks too.
          (b) PLUS the SW-replacement: 2 (target parried) or 4 (ally
              parried for the target).

        Pre-2026-05-30 this returned only the SW-replacement on parry
        attempted, silently dropping the margin contribution entirely.
        """
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn() - 20
        assert skill_roll is not None
        margin_extras = (skill_roll - tn) // 5
        if self.parry_attempted() and not self.parried():
            # General failed-parry reduction (rules/03-combat.md).
            reduction: int = self.target().skill("parry")
            margin_extras = max(0, margin_extras - reduction)
            # SW-replacement: 4 if a third party parried on the
            # target's behalf, else 2.
            sw_replacement = 2
            for parry_event in self.parries_declared():
                if parry_event.action.subject() != self.target():
                    sw_replacement = 4
                    break
            return int(margin_extras + sw_replacement)
        return int(margin_extras)

    def direct_damage(self) -> Any:
        if self.parry_attempted():
            return None
        event = SeriousWoundsDamageEvent(self.subject(), self.target(), 1)
        event._from_double_attack = True  # type: ignore[attr-defined]
        return event

    def tn(self) -> int:
        result: int = self.target().tn_to_hit() + 20
        return result


class FeintAction(AttackAction):
    def calculate_extra_damage_dice(self, skill_roll: int | None = None, tn: int | None = None) -> int:
        return 0

    def damage_roll_params(self) -> Any:
        return (0, 0, 0)

    def damage_breakdown(self) -> list[tuple[str, int, int]]:
        """Standard feints deal zero deterministic damage
        (``damage_roll_params`` is ``(0, 0, 0)``); they have no
        per-source breakdown to display.  The formatter suppresses
        their damage projection entirely (spec 008 FR-005/6).
        """
        return []

    def roll_damage(self) -> int:
        self.set_damage_roll(0)
        return 0


class LungeAction(AttackAction):
    def calculate_extra_damage_dice(self, skill_roll: int | None = None, tn: int | None = None) -> int:
        return super().calculate_extra_damage_dice(skill_roll, tn) + 1


class ParryAction(Action):
    def __init__(self, subject: Any, target: Any, skill: str, initiative_action: InitiativeAction, context: Any, attack: Any, predeclared: bool = False, ring: str | None = None, vp: int = 0) -> None:
        super().__init__(subject, target, skill, initiative_action, context, ring=ring, vp=vp)
        self._attack = attack
        self._predeclared = predeclared

    def attack(self) -> Any:
        return self._attack

    def is_success(self) -> bool:
        roll = self.skill_roll()
        assert roll is not None
        return roll >= self.tn()

    def roll_skill(self) -> int:
        penalty = 0
        if self._attack.target() != self.subject():
            # parry on behalf of others has a penalty of 5 * attacker's attack skill
            penalty = 5 * self._attack.subject().skill("attack")
        # roll parry
        self.set_skill_roll(self.subject().roll_skill(self.target(), self.skill(), ring=self.ring(), vp=self.vp()) - penalty)
        roll = self.skill_roll()
        assert roll is not None
        return roll

    def set_attack_parry_declared(self, event: Any) -> None:
        self._attack.add_parry_declared(event)

    def set_attack_parried(self) -> None:
        self._attack.set_parried()

    def set_attack_parry_attempted(self) -> None:
        self._attack.set_parry_attempted()

    def tn(self) -> int:
        result: int = self._attack.parry_tn()
        return result
