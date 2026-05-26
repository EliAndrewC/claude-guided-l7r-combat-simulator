#!/usr/bin/env python3

#
# schools.py
#
# Character Schools for L7R combat simulator.
#

from abc import ABC, abstractmethod
from typing import Any

from simulation.mechanics.modifiers import FreeRaise


class School(ABC):
    @abstractmethod
    def ap_base_skill(self) -> str | None:
        pass

    @abstractmethod
    def ap_skills(self) -> list[str]:
        pass

    @abstractmethod
    def apply_ap(self, character: Any) -> None:
        pass

    @abstractmethod
    def apply_special_ability(self, character: Any) -> None:
        pass

    @abstractmethod
    def apply_rank_one_ability(self, character: Any) -> None:
        pass

    @abstractmethod
    def apply_rank_two_ability(self, character: Any) -> None:
        pass

    @abstractmethod
    def apply_rank_three_ability(self, character: Any) -> None:
        pass

    @abstractmethod
    def apply_rank_four_ability(self, character: Any) -> None:
        pass

    @abstractmethod
    def apply_rank_five_ability(self, character: Any) -> None:
        pass

    @abstractmethod
    def extra_rolled(self) -> list[str]:
        pass

    @abstractmethod
    def free_raise_skills(self) -> list[str]:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def school_knacks(self) -> list[str]:
        pass

    @abstractmethod
    def school_ring(self) -> str:
        pass


class BaseSchool(School):
    def __init__(self) -> None:
        self._ap_base_skill: str | None = None
        self._ap_skills: list[str] = []
        self._free_raises_skills: list[str] = []
        self._skills: dict[str, int] = dict([(skill, 1) for skill in self.school_knacks()])
        # Per-character build-time choices populated by the adapter before any
        # apply_*_ability runs.  See specs/003-school-choices/spec.md FR-002.
        self._choices: dict[str, Any] = {}

    def set_choice(self, key: str, value: Any) -> None:
        """Store a per-character build-time choice for a school ability.

        Called by the web adapter BEFORE ``apply_*_ability`` methods run so
        subclass overrides can consult ``self.choice(key, default)`` from
        ``extra_rolled``, ``school_ring``, ``free_raise_skills``, etc.

        Subclasses that have no player choices ignore this transparently
        because they never read the key.

        See specs/003-school-choices/spec.md FR-002.
        """
        if not hasattr(self, "_choices"):
            # Defensive: a subclass that overrides ``__init__`` without
            # calling ``super().__init__()`` would skip the field init above.
            self._choices = {}
        self._choices[key] = value

    def choice(self, key: str, default: Any = None) -> Any:
        """Read a per-character build-time choice; return ``default`` if unset.

        See specs/003-school-choices/spec.md FR-002.
        """
        return getattr(self, "_choices", {}).get(key, default)

    def has_choice(self, key: str) -> bool:
        """Return True iff a choice has been set for ``key`` on this instance.

        See specs/003-school-choices/spec.md FR-002.
        """
        return key in getattr(self, "_choices", {})

    def _set_school_listener(self, character: Any, slot: str, listener: Any) -> None:
        """Install a school-owned listener on the given character.

        Subclasses MUST use this helper (instead of calling
        ``character.set_listener`` directly) when installing a listener as
        part of an ``apply_*_ability`` method.  The helper tracks the slot
        in ``character._school_owned_listener_slots`` so the engine-side
        dispatch gate in ``Character.event()`` can skip school-installed
        listeners while the character is school-negated
        (rules/04-schools.md "Isawa Ishi School: 5th Dan").
        """
        character.set_listener(slot, listener)
        character._school_owned_listener_slots.add(slot)

    def _set_school_strategy(self, character: Any, slot: str, strategy: Any) -> None:
        """Install a school-owned strategy on the given character.

        Subclasses MUST use this helper (instead of calling
        ``character.set_strategy`` / ``set_attack_strategy`` /
        ``set_parry_strategy`` / ``set_action_strategy`` directly) when
        installing a strategy as part of an ``apply_*_ability`` method.
        The helper:

          1. Caches the current strategy at ``slot`` in
             ``character._pre_school_strategies[slot]`` so
             ``Character.negate_school`` can restore the engine default
             when the character is school-negated.  The cache is
             populated on the FIRST school install per slot, so chained
             school replacements (rare) still revert to the original
             engine default.
          2. Tracks the slot in
             ``character._school_owned_strategy_slots`` so the active
             revert can find school-owned slots.
          3. Calls ``character.set_strategy`` to install the new
             strategy.

        rules/04-schools.md "Isawa Ishi School: 5th Dan".
        """
        if slot not in character._school_owned_strategy_slots:
            # Capture the engine default on first install so callers can
            # revert to the original (not a previous school override).
            character._pre_school_strategies[slot] = character._strategies.get(slot)
        character.set_strategy(slot, strategy)
        character._school_owned_strategy_slots.add(slot)

    def _set_school_max_vp_provider(self, character: Any, provider: Any) -> None:
        """Install a school-owned ``max_vp_provider`` (rules/04-schools.md
        "Isawa Ishi School: 5th Dan" -- the active-revert machinery needs
        to know that the school installed this provider so it can restore
        the engine default on negation)."""
        if "max_vp" not in character._school_owned_provider_slots:
            character._pre_school_max_vp_provider = character._max_vp_provider
        character.set_max_vp_provider(provider)
        character._school_owned_provider_slots.add("max_vp")

    def _set_school_action_factory(self, character: Any, factory: Any) -> None:
        """School-aware variant of ``character.set_action_factory``.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        if "action_factory" not in character._school_owned_provider_slots:
            character._pre_school_action_factory = character.action_factory()
        character.set_action_factory(factory)
        character._school_owned_provider_slots.add("action_factory")

    def _set_school_roll_parameter_provider(self, character: Any, provider: Any) -> None:
        """School-aware variant of ``character.set_roll_parameter_provider``.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        if "roll_parameter_provider" not in character._school_owned_provider_slots:
            character._pre_school_roll_parameter_provider = character.roll_parameter_provider()
        character.set_roll_parameter_provider(provider)
        character._school_owned_provider_slots.add("roll_parameter_provider")

    def _set_school_take_action_event_factory(self, character: Any, factory: Any) -> None:
        """School-aware variant of ``character.set_take_action_event_factory``.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        if "take_action_event_factory" not in character._school_owned_provider_slots:
            character._pre_school_take_action_event_factory = character.take_action_event_factory()
        character.set_take_action_event_factory(factory)
        character._school_owned_provider_slots.add("take_action_event_factory")

    def _set_school_roll_provider(self, character: Any, provider: Any) -> None:
        """School-aware variant of ``character.set_roll_provider``.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        if "roll_provider" not in character._school_owned_provider_slots:
            character._pre_school_roll_provider = character.roll_provider()
        character.set_roll_provider(provider)
        character._school_owned_provider_slots.add("roll_provider")

    def _set_school_wound_check_provider(self, character: Any, provider: Any) -> None:
        """School-aware variant of ``character.set_wound_check_provider``.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        if "wound_check_provider" not in character._school_owned_provider_slots:
            character._pre_school_wound_check_provider = character.wound_check_provider()
        character.set_wound_check_provider(provider)
        character._school_owned_provider_slots.add("wound_check_provider")

    def _set_school_attack_optimizer_factory(self, character: Any, factory: Any) -> None:
        """School-aware variant of ``character.set_attack_optimizer_factory``.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        if "attack_optimizer_factory" not in character._school_owned_provider_slots:
            character._pre_school_attack_optimizer_factory = character.attack_optimizer_factory()
        character.set_attack_optimizer_factory(factory)
        character._school_owned_provider_slots.add("attack_optimizer_factory")

    def _add_school_modifier(self, character: Any, modifier: Any) -> None:
        """Add a modifier to the character AND track it as school-owned so
        ``Character.negate_school`` can remove it on negation.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        character.add_modifier(modifier)
        character._school_owned_modifiers.append(modifier)

    def _set_school_extra_rolled(self, character: Any, skill: str, n: int = 1) -> None:
        """Grant a school-owned ``+n`` extra rolled die on ``skill`` AND
        track ``(skill, n)`` so ``Character.negate_school`` can subtract
        the bonus on negation.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        character.set_extra_rolled(skill, n)
        current = character._school_owned_extra_rolled.get(skill, 0)
        character._school_owned_extra_rolled[skill] = current + n

    def _set_school_extra_kept(self, character: Any, skill: str, n: int = 1) -> None:
        """Grant a school-owned ``+n`` extra kept die on ``skill`` AND track
        ``(skill, n)`` so ``Character.negate_school`` can subtract the
        bonus on negation.

        rules/04-schools.md "Isawa Ishi School: 5th Dan"."""
        # ``set_extra_kept`` assigns rather than increments, so we apply
        # the same accumulation semantics here that ``set_extra_rolled``
        # uses (current + n).
        current_char = character._extra_kept.get(skill, 0)
        character.set_extra_kept(skill, current_char + n)
        current_school = character._school_owned_extra_kept.get(skill, 0)
        character._school_owned_extra_kept[skill] = current_school + n

    def _is_school_negated(self, character: Any) -> bool:
        """
        _is_school_negated(character) -> bool

        Helper consumed by `apply_*_ability` methods to honor the Isawa Ishi
        5th Dan school-negation ability (rules/04-schools.md "Isawa Ishi
        School: 5th Dan").  When the target character has been marked as
        negated by an Ishi (via the `_school_negated_by` attribute), every
        rank-ability dispatch must become a no-op so the negated school's
        abilities never land.  For the overwhelming common case of an
        un-negated character this is a single attribute read and comparison.

        Subclasses that override `apply_special_ability`,
        `apply_rank_three_ability`, `apply_rank_four_ability`, or
        `apply_rank_five_ability` may call this helper at the top of their
        override to honor the same contract.
        """
        return getattr(character, "_school_negated_by", None) is not None

    def ap_base_skill(self) -> str | None:
        """
        ap_base_skill() -> str

        Return this school's base skill for calculating Adventure Points
        (Third Dan Free Raises).
        Returns None if the school does not use Adventure Points.
        """
        return self._ap_base_skill

    def ap_skills(self) -> list[str]:
        return self._ap_skills

    def apply_ap(self, character: Any) -> None:
        if self.ap_base_skill() is not None:
            character.set_ap_base_skill(self.ap_base_skill())
            character.set_ap_skills(self.ap_skills())

    def apply_rank_one_ability(self, character: Any) -> None:
        """
        apply_rank_one_ability(character)

        Apply this school's extra rolled dice (the standard 1st Dan ability).
        Short-circuits to a no-op when the character's school has been negated
        by an Isawa Ishi 5th Dan (rules/04-schools.md "Isawa Ishi School:
        5th Dan").
        """
        if self._is_school_negated(character):
            return
        for skill in self.extra_rolled():
            self._set_school_extra_rolled(character, skill, 1)

    def apply_rank_two_ability(self, character: Any) -> None:
        """
        apply_rank_two_ability(character)

        Apply this school's Free Raises (the standard 2nd Dan ability).
        Short-circuits to a no-op when the character's school has been negated
        by an Isawa Ishi 5th Dan (rules/04-schools.md "Isawa Ishi School:
        5th Dan").
        """
        if self._is_school_negated(character):
            return
        for skill in self.free_raise_skills():
            self._add_school_modifier(character, FreeRaise(character, skill))

    def apply_school_ability(self, character: Any, rank: int) -> None:
        """
        apply_school_ability(character, rank)

        Apply this school's rank ability to a character.
        """
        if rank == 1:
            self.apply_rank_one_ability(character)
        elif rank == 2:
            self.apply_rank_two_ability(character)
        elif rank == 3:
            self.apply_rank_three_ability(character)
        elif rank == 4:
            self.apply_rank_four_ability(character)
        elif rank == 5:
            self.apply_rank_five_ability(character)

    def apply_school_ring_raise_and_discount(self, character: Any) -> None:
        """
        apply_school_ring_raise_and_discount(character)

        Raise the character's school ring and apply a discount.
        This is a standard 4th Dan bonus.
        """
        cur_rank = character.ring(self.school_ring())
        character.set_ring(self.school_ring(), cur_rank + 1)
        character.add_discount(self.school_ring(), 5)

    def apply_rank_three_ability(self, character: Any) -> None:
        """
        apply_rank_three_ability(character)

        Apply this school's 3rd Dan ability to the character.
        """
        raise NotImplementedError()

    def apply_rank_four_ability(self, character: Any) -> None:
        """
        apply_rank_four_ability(character)

        Implementations should apply this school's 4th Dan ability to the character.
        """
        raise NotImplementedError()

    def apply_rank_five_ability(self, character: Any) -> None:
        """
        apply_rank_five_ability(character)

        Implementations should apply the school's 5th Dan ability.
        """
        raise NotImplementedError()

    def apply_school_ring(self, character: Any) -> None:
        """
        apply_school_ring(character)

        Raise this character's school ring from 2 to 3.
        """
        if character.ring(self.school_ring()) != 2:
            raise ValueError(f"{character.name()}'s {self.school_ring()} ring is not 2, cannot apply school ring bonus")
        character.set_ring(self.school_ring(), 3)

    def apply_special_ability(self, character: Any) -> None:
        """
        apply_special_ability(character)

        Apply this school's special ability to the character.
        This usually involves setting special listeners or strategies.
        """
        raise NotImplementedError()

    def free_raise_skills(self) -> list[str]:
        """
        free_raise_skills() -> list of str

        Implementations should return the list of skills that receive Free Raises from this school at 2nd Dan.
        """
        raise NotImplementedError()

    def extra_rolled(self) -> list[str]:
        """
        extra_rolled() -> list of str

        Implementations should return the list of things where they get an extra rolled die.
        """
        raise NotImplementedError()

    def name(self) -> str:
        """
        name() -> str

        Implementations should return the name of the School.
        """
        raise NotImplementedError()

    def school_knacks(self) -> list[str]:
        """
        school_knacks() -> list of str

        Implementations should return their list of School Knacks.
        """
        raise NotImplementedError()

    def school_ring(self) -> str:
        """
        school_ring() -> str

        Implementations should return the name of their School Ring.
        """
        raise NotImplementedError()
