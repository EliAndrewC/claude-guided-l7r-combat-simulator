#!/usr/bin/env python3

#
# bayushi_school.py
# Implement Bayushi Bushi School.
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.actions import FeintAction
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import AnyAttackFloatingBonus
from simulation.mechanics.roll_params import (
    DefaultRollParameterProvider,
    _normalize_breakdown,
    normalize_roll_params,
)
from simulation.optimizers.wound_check_provider import DEFAULT_WOUND_CHECK_PROVIDER, WoundCheckProvider
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory


class BayushiBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_wound_check_provider(character, BayushiWoundCheckProvider())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_listener(character, "attack_failed", BayushiAttackFailedListener())
        self._set_school_listener(character, "attack_succeeded", BayushiAttackSucceededListener())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_action_factory(character, BAYUSHI_ACTION_FACTORY)

    def apply_special_ability(self, character: Any) -> None:
        self._set_school_roll_parameter_provider(character, BAYUSHI_ROLL_PARAMETER_PROVIDER)

    def extra_rolled(self) -> list[str]:
        return ["double attack", "iaijutsu", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["double attack"]

    def name(self) -> str:
        return "Bayushi Bushi School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "feint", "iaijutsu"]

    def school_ring(self) -> str:
        return "fire"


class BayushiRollParameterProvider(DefaultRollParameterProvider):
    """
    Custom RollParameterProvider to implement the Bayushi special ability
    to apply Void Points spent on attack rolls to damage rolls.
    """

    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        # calculate extra rolled dice
        ring = character.ring(character.get_skill_ring("damage"))
        my_extra_rolled = character.extra_rolled("damage")
        rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled() + vp
        # calculate extra kept dice
        kept = character.weapon().kept() + character.extra_kept("damage") + vp
        # calculate modifier
        mod = character.modifier(None, "damage")
        return normalize_roll_params(rolled, kept, mod)

    def get_breakdown(
        self,
        character: Any,
        target: Any,
        skill: str,
        kind: str = "damage",
        attack_extra_rolled: int = 0,
        vp: int = 0,
        contested_skill: str | None = None,
        ring: str | None = None,
    ) -> list[tuple[str, int, int]]:
        """Mirror ``get_damage_roll_params`` for the Bayushi
        Special Ability (VP on attack inflates damage rolled AND kept
        — rules/04-schools.md "Bayushi Bushi School: Special Ability").

        For non-damage ``kind`` values, delegate to ``super`` so the
        default attack-roll breakdown (Phase 4: FR-006) is still
        attached. Bayushi's only roll-parameter override is the damage
        roll; attack rolls follow the default ``get_skill_roll_params``
        formula.
        """
        if kind != "damage":
            return super().get_breakdown(
                character, target, skill,
                kind=kind,
                attack_extra_rolled=attack_extra_rolled,
                vp=vp,
                contested_skill=contested_skill,
                ring=ring,
            )
        weapon = character.weapon()
        ring_name = character.get_skill_ring("damage")
        ring_value = character.ring(ring_name)
        my_extra_rolled = character.extra_rolled("damage")
        my_extra_kept = character.extra_kept("damage")
        components: list[tuple[str, int, int]] = []
        components.append(
            (weapon.name(), weapon.rolled(), weapon.kept()),
        )
        if ring_value > 0:
            components.append(
                (f"{ring_name.capitalize()} ring", ring_value, 0),
            )
        if attack_extra_rolled > 0:
            margin = attack_extra_rolled * 5
            components.append(
                (f"margin (+{margin} over TN)", attack_extra_rolled, 0),
            )
        # Bayushi Special Ability: each VP spent on the attack roll
        # adds +1 rolled AND +1 kept to the damage roll.
        if vp > 0:
            components.append(("VP on attack", vp, vp))
        if my_extra_rolled > 0 or my_extra_kept > 0:
            school = character.school() if hasattr(character, "school") else None
            label = (
                school.name() if school is not None and school.name()
                else "character bonus"
            )
            components.append((label, my_extra_rolled, my_extra_kept))
        aggregate_rolled, aggregate_kept, _ = self.get_damage_roll_params(
            character, target, skill, attack_extra_rolled, vp=vp,
        )
        return _normalize_breakdown(components, aggregate_rolled, aggregate_kept)


BAYUSHI_ROLL_PARAMETER_PROVIDER = BayushiRollParameterProvider()


class BayushiWoundCheckProvider(WoundCheckProvider):
    """
    WoundCheckProvider to implement the Bayushi 5th Dan ability
    to take Serious Wounds as if the character had half as many light wounds.

    A failed wound check (roll < actual LW) always results in at least 1 SW.
    The halving only reduces severity but cannot eliminate SW entirely.
    """

    def wound_check(self, roll: int, lw: int) -> int:
        halved_lw = lw // 2
        result = DEFAULT_WOUND_CHECK_PROVIDER.wound_check(roll, halved_lw)
        # A failed wound check always results in at least 1 SW
        if result == 0 and roll < lw:
            return 1
        return result


class BayushiFeintAction(FeintAction):
    def damage_roll_params(self) -> tuple[int, int, int]:
        rolled = self.subject().skill("attack") + self.vp()
        kept = 1 + self.vp()
        modifier = self.subject().modifier(self.target(), self.skill())
        return (rolled, kept, modifier)

    def roll_damage(self) -> int:
        (rolled, kept, modifier) = self.damage_roll_params()
        damage_roll: int = self.subject().roll_provider().get_damage_roll(rolled, kept) + modifier
        self.set_damage_roll(damage_roll)
        return damage_roll


class BayushiActionFactory(DefaultActionFactory):
    def get_attack_action(self, subject: Any, target: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        if skill == "feint":
            return BayushiFeintAction(subject, target, skill, initiative_action, context, vp=vp)
        else:
            return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


BAYUSHI_ACTION_FACTORY = BayushiActionFactory()


class BayushiAttackFailedListener(Listener):
    """
    Listener to implement the Bayushi 4th Dan ability
    to gain a floating bonus to any attack after a Feint.

    rules/04-schools.md "Bayushi Bushi School: Fourth Dan".  Tags the
    bonus with ``source="Bayushi 4th Dan"`` and yields a
    ``GainFloatingBonusEvent`` so the trace formatter renders the
    acquisition with source attribution per Constitution Principle VII.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackFailedEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    bonus = AnyAttackFloatingBonus(5, source="Bayushi 4th Dan")
                    character.gain_floating_bonus(bonus)
                    yield events.GainFloatingBonusEvent(
                        character,
                        bonus,
                        source="Bayushi 4th Dan",
                        breakdown="failed feint",
                    )


class BayushiAttackSucceededListener(Listener):
    """
    Listener to implement the Bayushi 4th Dan ability
    to gain a floating bonus to any attack after a Feint.

    rules/04-schools.md "Bayushi Bushi School: Fourth Dan".  Tags the
    bonus with ``source="Bayushi 4th Dan"`` and yields a
    ``GainFloatingBonusEvent`` so the trace formatter renders the
    acquisition with source attribution per Constitution Principle VII.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    bonus = AnyAttackFloatingBonus(5, source="Bayushi 4th Dan")
                    character.gain_floating_bonus(bonus)
                    yield events.GainFloatingBonusEvent(
                        character,
                        bonus,
                        source="Bayushi 4th Dan",
                        breakdown="successful feint",
                    )
