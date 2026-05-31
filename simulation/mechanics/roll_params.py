#!/usr/bin/env python3

#
# roll_params.py
#
# Class to calculate a character's roll parameters in L7R.
# "Roll parameters" is the tuple of (rolled, kept, modifier)
# for a roll.
#

from abc import ABC, abstractmethod
from typing import Any

from simulation.mechanics.skills import ATTACK_SKILLS


def normalize_roll_params(rolled: int, kept: int, bonus: int = 0) -> tuple[int, int, int]:
    """
    normalize_roll_params(rolled, kept, bonus=0) -> tuple of ints
      rolled (int): number of rolled dice
      kept (int): number of kept dice
      bonus (int): flat bonus to roll

    Returns normalized roll parameters, which is the tuple of
    (rolled, kept, bonus) for a roll.
    The algorithm is that excess rolled dice above ten become
    extra kept dice, excess kept dice above ten become a bonus,
    and the bonus is added to the roll.
    """
    # convert excess rolled dice to extra kept dice
    if rolled > 10:
        excess_rolled = rolled - 10
        rolled = 10
        kept += excess_rolled
    # convert extra kept dice to bonus
    if kept > 10:
        excess_kept = kept - 10
        kept = 10
        bonus += 2 * excess_kept
    # check if there are fewer dice rolled than kept
    if rolled < kept:
        kept = rolled
    # rolled and kept may not be lower than zero
    rolled = max(rolled, 0)
    kept = max(kept, 0)
    return (rolled, kept, bonus)


class RollParameterProvider(ABC):
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
        """
        get_breakdown(character, target, skill, kind, \
            attack_extra_rolled=0, vp=0, contested_skill=None, \
            ring=None) -> list of (label, +rolled, +kept)

        Returns a per-source decomposition of a roll's rolled and kept
        dice. Each tuple in the returned list is
        ``(source_label, +rolled, +kept)`` and the components sum (after
        an optional final ``"from dice in excess of 10k10"`` entry) to
        the same ``(rolled, kept)`` that ``get_damage_roll_params`` /
        ``get_skill_roll_params`` would return.

        This is the audit-trail counterpart to the aggregate roll-param
        methods. It is consumed by the trace formatter to render the
        inline Constitution-Principle-VII breakdown of each multi-source
        roll. ``CombatObserver`` calls it per-event and attaches the
        result to the event as ``_detail_components``.

        ``kind`` selects which roll type to decompose:

        - ``"damage"`` (Phase 3): mirror ``get_damage_roll_params``.
        - ``"attack"`` (Phase 4): mirror ``get_skill_roll_params``
          (skill rolls — attack, parry, etc.). The ``contested_skill``
          and ``ring`` arguments override the defaults the provider
          would otherwise pull from the character.

        Subclasses overriding ``get_damage_roll_params`` (e.g.
        ``BayushiRollParameterProvider``) MUST override
        ``get_breakdown`` correspondingly so the breakdown sums to the
        aggregate that was actually rolled.

        Returns an empty list when the provider has no decomposition
        for the given ``kind`` (the formatter then renders the aggregate
        without an inline breakdown — Edge Cases: "Aggregate with only
        ONE source").
        """
        return []

    @abstractmethod
    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        """
    get_damage_roll_params(character, target, skill, \
        attack_extra_rolled, vp=0) -> tuple of three ints
      character (Character): character who is rolling damage
      target (Character): character who will be damaged
      skill (str): skill name being used
      attack_extra_rolled (int): number of extra rolled damage dice from the attack roll
      vp (int): number of Void Points spent on the attack roll

    Returns the parameters for the character's damage roll using
    the specified skill against the given target.
    """
        pass  # pragma: no cover  # abstract method; subclasses must override

    @abstractmethod
    def get_initiative_roll_params(self, character: Any) -> tuple[int, int, int]:
        """
        get_initiative_roll_params(character) -> tuple of ints
          character (Character): character who is rolling initiative

        Returns the roll parameters (rolled, kept, modifier) for the
        character's initiative roll.

        Modifiers do not apply to initiative rolls, so the modifier is
        always 0.
        """
        pass  # pragma: no cover  # abstract method; subclasses must override

    @abstractmethod
    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        """
    get_skill_roll_params(character, target, skill, \
        contested_skill=None, ring=None, vp=0) -> tuple of ints
      character (Character): character who is rolling
      target (Character): target of the skill
      skill (str): skill name being used
      contested_skill (str): if given, this is a contested roll,
        and names the skill the other character is using to contest.
      ring (str): ring to use for the skill roll. Defaults to None,
        which means the character's default ring for that skill is
        used.
      vp (int): number of Void Points to spend on this roll

    Returns the parameters for the character's skill roll using the
    specified and skill as a tuple of three ints
    (rolled, kept, modifier).
    """
        pass  # pragma: no cover  # abstract method; subclasses must override

    @abstractmethod
    def get_wound_check_roll_params(self, character: Any, vp: int = 0) -> tuple[int, int, int]:
        """
        get_wound_check_roll_params(character, vp=0) -> tuple of ints
          character (Character): character who will be rolling for a Wound Check
          vp (int): number of Void Points to spend on this roll

        Returns the parameters for the character's wound check roll
        as a tuple of three ints (rolled, kept, modifier).
        """
        pass  # pragma: no cover  # abstract method; subclasses must override


def _normalize_breakdown(
    components: list[tuple[str, int, int]],
    aggregate_rolled: int,
    aggregate_kept: int,
    character: Any = None,
) -> list[tuple[str, int, int]]:
    """Adjust a raw breakdown so the components' summed rolled/kept equals
    the normalized aggregate.

    ``normalize_roll_params`` converts excess rolled→kept dice (when
    pre-normalize rolled > 10) and excess kept dice→bonus modifier
    (when pre-normalize kept > 10).  The pre-normalize breakdown
    components may therefore not sum to the displayed XkY.  To preserve
    the Principle VII invariant ``sum(rolled) == aggregate_rolled``
    AND ``sum(kept) == aggregate_kept``, append a synthetic
    ``"from dice in excess of 10k10"`` entry that absorbs the delta.
    The entry is a Principle VII compliance signal — a visible
    mechanism, not a hidden adjustment.  In the typical case (rolled
    overflow), the entry carries a negative rolled delta paired with a
    positive kept delta (e.g., ``(-3, +3)`` means "3 rolled dice in
    excess of 10 converted to 3 kept dice").

    Zero-delta cases produce no synthetic entry (the breakdown is
    already balanced).

    When ``character`` is provided and the non-overflow catch-all
    fires, the label is qualified with the character's school short
    name (e.g., ``"Shiba school formula"``) so a fresh reader can at
    least tell *which* school's override is contributing — even if
    the specific Dan ability is not pinpointed (trace-reader cat#10
    fix 2026-05-30).
    """
    sum_rolled = sum(r for _, r, _ in components)
    sum_kept = sum(k for _, _, k in components)
    delta_rolled = aggregate_rolled - sum_rolled
    delta_kept = aggregate_kept - sum_kept
    if delta_rolled == 0 and delta_kept == 0:
        return components
    # Distinguish two cases that produce a synthetic delta entry:
    #   (1) Genuine 10k10 overflow — the raw component sum exceeded
    #       the cap, so ``normalize_roll_params`` converted some
    #       rolled→kept or kept→bonus.  Label as "from dice in
    #       excess of 10k10" so the renderer can emit the
    #       "+{2N} from {N} dropped dice in excess of 10k10"
    #       narrative form.
    #   (2) Non-overflow reconciliation — the raw sum was already
    #       within the 10k10 cap; the delta comes from another
    #       mechanic the breakdown didn't capture (e.g., feint
    #       damage reduction, counterattack damage formula, Shiba
    #       3rd Dan parry-damage cap).  Trace-reader 2026-05-30
    #       sweep: name the school in the label when known so the
    #       reader can identify the source even without a full
    #       per-source breakdown.
    if sum_rolled > 10 or sum_kept > 10:
        label = "from dice in excess of 10k10"
    else:
        label = _school_formula_label(character)
    return [*components, (label, delta_rolled, delta_kept)]


def _school_formula_label(character: Any) -> str:
    """Render the non-overflow catch-all label, qualifying it with the
    character's school short name when available."""
    if character is None:
        return "school formula"
    school = character.school() if hasattr(character, "school") else None
    if school is None or not school.name():
        return "school formula"
    return f"{school.name().split()[0]} school formula"


class DefaultRollParameterProvider(RollParameterProvider):
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
        if kind == "damage":
            return self._damage_breakdown(
                character, target, skill, attack_extra_rolled, vp,
            )
        if kind == "attack":
            return self._attack_breakdown(
                character, target, skill, vp=vp,
                contested_skill=contested_skill, ring_override=ring,
            )
        return []

    def _damage_breakdown(
        self,
        character: Any,
        target: Any,
        skill: str,
        attack_extra_rolled: int,
        vp: int,
    ) -> list[tuple[str, int, int]]:
        # Mirror ``get_damage_roll_params`` exactly. Each contributor
        # gets its own (label, +rolled, +kept) entry; the post-normalize
        # delta (if any) becomes a final "from dice in excess of 10k10"
        # entry so the components sum to the aggregate displayed in the
        # trace.
        weapon = character.weapon()
        ring_name = character.get_skill_ring("damage")
        ring_value = character.ring(ring_name)
        my_extra_rolled = character.extra_rolled("damage")
        my_extra_kept = character.extra_kept("damage")
        components: list[tuple[str, int, int]] = []
        # Weapon base (e.g., "katana" → +4 rolled, +2 kept).
        components.append(
            (weapon.name(), weapon.rolled(), weapon.kept()),
        )
        # Ring contribution (e.g., "Fire ring" → +5 rolled, +0 kept).
        if ring_value > 0:
            components.append(
                (f"{ring_name.capitalize()} ring", ring_value, 0),
            )
        # Margin extras from the attack roll (floor(margin/5) extras).
        if attack_extra_rolled > 0:
            margin = attack_extra_rolled * 5
            components.append(
                (f"margin (+{margin} over TN)", attack_extra_rolled, 0),
            )
        # Character-level extra rolled/kept (school-conferred, profession,
        # etc.). The default provider walks ``character.extra_rolled``
        # which already incorporates the school's ``extra_rolled``
        # accessor — per data-model.md "Per-school breakdown
        # contribution" (1). Trace-reader cat#10 fix (2026-05-30):
        # use the "<School> 1st Dan" short form (matching the attack
        # breakdown) instead of the full school name, so the reader
        # can see WHICH Dan ability is contributing rather than just
        # "Kuni Witch Hunter School".
        if my_extra_rolled > 0 or my_extra_kept > 0:
            school = character.school() if hasattr(character, "school") else None
            if school is not None and school.name():
                label = f"{school.name().split()[0]} 1st Dan"
            else:
                label = "character bonus"
            components.append((label, my_extra_rolled, my_extra_kept))
        # Reconcile against the actual aggregate (handles normalize_roll_params
        # rolled→kept conversion). Bonus/modifier dice are NOT part of the
        # rolled/kept breakdown — they appear in the modifier-breakdown
        # rendering instead.
        aggregate_rolled, aggregate_kept, _ = self.get_damage_roll_params(
            character, target, skill, attack_extra_rolled, vp=vp,
        )
        return _normalize_breakdown(
            components, aggregate_rolled, aggregate_kept, character=character,
        )

    def _attack_breakdown(
        self,
        character: Any,
        target: Any,
        skill: str,
        vp: int,
        contested_skill: str | None,
        ring_override: str | None,
    ) -> list[tuple[str, int, int]]:
        """Mirror ``get_skill_roll_params`` for skill rolls (attack,
        parry, feint, double-attack, etc.).

        Per the formula in ``get_skill_roll_params``:

            rolled = ring + skill + extra_rolled(skill) + vp
            kept   = ring + extra_kept(skill) + vp

        The ring contributes to BOTH rolled and kept; the skill
        contributes to rolled only; ``vp`` contributes to BOTH per
        L7R rules. The school's ``extra_rolled``/``extra_kept`` map
        (the 1st Dan ability for every implemented school) is labelled
        with the school's source attribution per data-model.md
        "Source labels".

        ``contested_skill`` adds to the modifier (not rolled/kept) and
        is therefore not part of this breakdown. The target's
        ``attack_rolled_penalty`` (Ninja ability) would reduce rolled
        dice; if non-zero, the synthetic ``"from dice in excess of
        10k10"`` entry absorbs the delta so the breakdown still sums
        to the aggregate.
        """
        ring_name = ring_override if ring_override is not None else character.get_skill_ring(skill)
        ring_value = character.ring(ring_name)
        skill_value = character.skill(skill)
        my_extra_rolled = character.extra_rolled(skill)
        my_extra_kept = character.extra_kept(skill)
        components: list[tuple[str, int, int]] = []
        # Ring (e.g., "Fire ring" → +3 rolled, +3 kept for a Fire-3
        # attacker). Ring contributes to BOTH rolled AND kept.
        if ring_value > 0:
            components.append(
                (f"{ring_name.capitalize()} ring", ring_value, ring_value),
            )
        # Skill (e.g., "attack skill" → +5 rolled, +0 kept). Skill is
        # rolled-only per L7R skill-roll formula.
        if skill_value > 0:
            components.append(
                (f"{skill} skill", skill_value, 0),
            )
        # School-conferred extra dice (the standard 1st Dan ability).
        # Per data-model.md "Source labels" the convention is
        # "<school-short-name> 1st Dan" — e.g., "Akodo 1st Dan".
        # Extract the first word of the school name for the label.
        if my_extra_rolled > 0 or my_extra_kept > 0:
            school = character.school() if hasattr(character, "school") else None
            if school is not None and school.name():
                label = f"{school.name().split()[0]} 1st Dan"
            else:
                label = "character bonus"
            components.append((label, my_extra_rolled, my_extra_kept))
        # VP-on-attack inflation: each VP adds +1 rolled AND +1 kept
        # (the default skill-roll formula).
        if vp > 0:
            components.append((f"VP on {skill}", vp, vp))
        # Reconcile against the actual aggregate. This absorbs:
        #   * ``normalize_roll_params`` rolled→kept conversion (e.g.,
        #     13/7 → 10/10).
        #   * Target's ``attack_rolled_penalty`` (Ninja ability),
        #     which subtracts from rolled before normalization.
        # The synthetic "from dice in excess of 10k10" entry is a
        # visible signal (Principle VII) — not a hidden adjustment.
        #
        # We pass ``ring=None`` to ``get_skill_roll_params`` here even
        # when ``ring_override`` is set, because that method's ``ring``
        # parameter is signed as ``str`` but its arithmetic treats it
        # as ``int`` (a latent typing inconsistency that crashes when
        # the override is a string). Since we've already pre-computed
        # the ring value above, the default-lookup path produces the
        # correct aggregate.
        aggregate_rolled, aggregate_kept, _ = self.get_skill_roll_params(
            character, target, skill,
            contested_skill=contested_skill, ring=None, vp=vp,
        )
        return _normalize_breakdown(
            components, aggregate_rolled, aggregate_kept, character=character,
        )

    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        # calculate extra rolled dice
        ring = character.ring(character.get_skill_ring("damage"))
        my_extra_rolled = character.extra_rolled("damage")
        rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled()
        # calculate extra kept dice
        kept = character.weapon().kept() + character.extra_kept("damage")
        # calculate modifier
        mod = character.modifier(None, "damage")
        return normalize_roll_params(rolled, kept, mod)

    def get_initiative_roll_params(self, character: Any) -> tuple[int, int, int]:
        ring = character.ring(character.get_skill_ring("initiative"))
        rolled = ring + 1 + character.extra_rolled("initiative")
        kept = ring + character.extra_kept("initiative")
        return (rolled, kept, 0)

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        if ring is None:
            ring = character.ring(character.get_skill_ring(skill))
        rolled = ring + character.skill(skill) + character.extra_rolled(skill) + vp
        kept = ring + character.extra_kept(skill) + vp
        modifier = character.modifier(target, skill)
        if contested_skill is not None:
            my_skill = character.skill(skill)
            your_skill = target.skill(contested_skill)
            if my_skill > your_skill:
                modifier += 5 * (my_skill - your_skill)
        # Apply attack rolled penalty from target (Ninja ability)
        if target is not None and skill in ATTACK_SKILLS:
            penalty = target.attack_rolled_penalty()
            if penalty > 0:
                rolled = max(rolled - penalty, character.ring("fire"))
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character: Any, vp: int = 0) -> tuple[int, int, int]:
        ring = character.ring(character.get_skill_ring("wound check"))
        rolled = ring + 1 + character.extra_rolled("wound check") + vp
        kept = ring + character.extra_kept("wound check") + vp
        modifier = character.modifier(None, "wound check")
        return normalize_roll_params(rolled, kept, modifier)


DEFAULT_ROLL_PARAMETER_PROVIDER = DefaultRollParameterProvider()
