#!/usr/bin/env python3

#
# shosuro_actor_school.py
#
# Implement Shosuro Actor School.
#
# School Ring: Air
# School Knacks: athletics, discern honor, pontificate
#
# Special Ability: Roll extra dice equal to acting on attack, parry, wound check.
# 1st Dan: Extra rolled on attack, sincerity, wound check
# 2nd Dan: Free raise on sincerity
# 3rd Dan: AP system — ap_base_skill = "sincerity", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; stipend bonus (no-op in combat)
# 5th Dan: After TN/contested roll, add lowest 3 dice to result.
#

from typing import Any

from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.roll_provider import RollProvider
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool
from simulation.strategies.base import AlwaysParryStrategy, WoundCheckStrategy04


class ShosuroActorSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return "sincerity"

    def ap_skills(self) -> list[str]:
        return ["acting", "heraldry", "sincerity", "sneaking", "attack", "wound check"]

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Shosuro Actor School: Special Ability":
        # "Roll extra dice equal to your acting on attack, parry, and
        # wound checks."  Implemented via a custom RollParameterProvider
        # so that increases to ``acting`` during character building feed
        # back into the rolled-dice count.
        #
        # Identity bindings (spec 029, strategy-designer):
        # - ``AlwaysParryStrategy`` — every parry receives +acting rolled
        #   dice, so declining "small" attacks (the engine default) wastes
        #   the school's chief defensive buff.
        # - ``WoundCheckStrategy04`` — the SA buffs WC by +acting rolled
        #   AND 5th Dan adds the lowest-3 dice; the resulting WC pool is
        #   structurally larger than baseline, so VP spending can lean
        #   more aggressive (threshold 0.4 vs the default 0.6).
        self._set_school_roll_parameter_provider(character, ShosuroRollParameterProvider())
        self._set_school_strategy(character, "parry", AlwaysParryStrategy())
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_three_ability(self, character: Any) -> None:
        self.apply_ap(character)

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # Rank 5.0 higher for stipend — no-op in combat

    def apply_rank_five_ability(self, character: Any) -> None:
        # After any TN or contested roll, add lowest 3 dice to result.
        self._set_school_roll_provider(character, ShosuroActorRollProvider(character.roll_provider()))

    def extra_rolled(self) -> list[str]:
        return ["attack", "sincerity", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["sincerity"]

    def name(self) -> str:
        return "Shosuro Actor School"

    def school_knacks(self) -> list[str]:
        return ["athletics", "discern honor", "pontificate"]

    def school_ring(self) -> str:
        return "air"


class ShosuroActorRollProvider(RollProvider):
    """Wrap an existing roll provider to add lowest 3 dice to non-initiative rolls.

    Implements the Shosuro Actor School 5th Dan ability:
    "After making any non-initiative roll, add your lowest three dice to
    the result. (Some dice may be counted twice.)"

    Applies to skill rolls, wound checks, damage rolls, and damage-reduction
    rolls. Initiative rolls are the sole exclusion per rules text.
    When fewer than 3 dice were rolled, the lowest die is repeated to pad
    to 3 ("some dice may be counted twice").
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def die_provider(self) -> Any:
        result: Any = self._inner.die_provider()
        return result

    def get_damage_reduction_roll(self, rolled: int, kept: int, reduction: int) -> int:
        result: int = self._inner.get_damage_reduction_roll(rolled, kept, reduction)
        bonus = self._lowest_three_bonus(self._inner.last_damage_info())
        return result + bonus

    def get_damage_roll(self, rolled: int, kept: int) -> int:
        result: int = self._inner.get_damage_roll(rolled, kept)
        bonus = self._lowest_three_bonus(self._inner.last_damage_info())
        return result + bonus

    def get_initiative_roll(self, rolled: int, kept: int) -> list[int]:
        result: list[int] = self._inner.get_initiative_roll(rolled, kept)
        return result

    def get_skill_roll(self, skill: str, rolled: int, kept: int, explode: bool = True) -> int:
        result: int = self._inner.get_skill_roll(skill, rolled, kept, explode)
        bonus = self._lowest_three_bonus(self._inner.last_skill_info())
        return result + bonus

    def get_wound_check_roll(self, rolled: int, kept: int, explode: bool = True) -> int:
        result: int = self._inner.get_wound_check_roll(rolled, kept, explode=explode)
        bonus = self._lowest_three_bonus(self._inner.last_wound_check_info())
        return result + bonus

    def last_damage_info(self) -> Any:
        return self._inner.last_damage_info()

    def last_skill_info(self) -> Any:
        return self._inner.last_skill_info()

    def last_wound_check_info(self) -> Any:
        return self._inner.last_wound_check_info()

    def set_die_provider(self, die_provider: Any) -> None:
        self._inner.set_die_provider(die_provider)

    @staticmethod
    def _lowest_three_bonus(info: Any) -> int:
        """Sum the lowest 3 dice; pad by repeating the lowest if <3 dice.

        Returns 0 only when no dice information is available — that case is
        defensive for plain-int test fixtures and never occurs in normal play.
        """
        if info is None:
            return 0
        dice = info.get("dice")
        if dice is None:
            return 0
        if not dice:  # pragma: no cover  # defensive: an empty dice list never reaches here in play
            return 0
        sorted_dice = sorted(dice)
        padded = sorted_dice[:3]
        while len(padded) < 3:
            padded.append(sorted_dice[0])
        return sum(padded)


class ShosuroRollParameterProvider(DefaultRollParameterProvider):
    """Add acting skill rank as extra rolled dice on attack, parry, and wound check."""

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        if skill in ATTACK_SKILLS or skill == "parry":
            rolled += character.skill("acting")
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character: Any, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_wound_check_roll_params(character, vp)
        rolled += character.skill("acting")
        return normalize_roll_params(rolled, kept, modifier)
