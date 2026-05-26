"""UI-side helper that attributes a roll modifier to known school sources.

Constitution Principle VII: every applied ability/modifier/free-raise/
extra-die that contributes to a user-facing combat trace must include
BOTH a numeric value AND a source attribution. This module gives the
formatter a way to map a raw modifier integer back to the school
mechanics that produced it -- for now scoped to the Mirumoto Bushi
School modifiers the user explicitly flagged as missing attribution.

Per Constitution Principle II (UI-side observability does not leak
into the rules engine), this module lives under ``web/adapters/`` and
imports from ``simulation/`` -- never the other way around.

References (all from ``rules/04-schools.md``):
  * Mirumoto Bushi School Fifth Dan: "When you spend a Void Point on
    an attack, parry, or wound check roll, that roll gets +10 instead
    of the normal +5." -- implemented as a flat +10 per VP on top of
    the standard void-spend, applied to all combat rolls (attack-class
    skills + parry + wound check) per the spec.md 2026-05-26 scope
    clarification.
  * Mirumoto Bushi School Second Dan: "Free Raise on parry." --
    standard 2nd-Dan free-raise = +5 modifier on parry rolls.
"""

from __future__ import annotations

from typing import Any

from simulation.mechanics.skills import ATTACK_SKILLS

# Skill scope for the Mirumoto Fifth Dan +10/VP modifier (FR-014 / per
# spec.md Clarifications Session 2026-05-26). Mirrors the whitelist on
# ``MirumotoRollParameterProvider`` plus ``wound check`` (which the
# engine routes through a separate provider method but is in the same
# combat-roll scope for attribution purposes).
_MIRUMOTO_FIFTH_DAN_COMBAT_SKILLS = frozenset(ATTACK_SKILLS) | {"parry", "wound check"}


def _school_rank(character: Any) -> int:
    """Compute the character's school rank as ``min(skill rank)`` across
    school knacks.

    Mirrors ``simulation/character_file.py::CharacterFile.school_rank``.
    Returns 0 when no school is set or the school has no knacks.
    """
    school = character.school() if hasattr(character, "school") else None
    if school is None:
        return 0
    knacks = school.school_knacks()
    if not knacks:
        return 0
    result: int = min(character.skill(s) for s in knacks)
    return result


def _is_mirumoto_bushi(character: Any) -> bool:
    """True iff the character's school is the Mirumoto Bushi School."""
    school = character.school() if hasattr(character, "school") else None
    if school is None:
        return False
    return bool(school.name() == "Mirumoto Bushi School")


def explain_modifier(
    character: Any,
    skill: str,
    modifier: int,
    vp: int = 0,
) -> list[tuple[str, int]]:
    """Return a list of ``(source_label, value)`` contributions that
    explain (some or all of) the given roll ``modifier``.

    The returned list is ordered by descending contribution value so
    the formatter can render the most-significant source first.

    Returns an empty list when no school-specific source is
    recognizable -- the formatter's downstream contract is to suppress
    attribution rendering in that case (better silent than wrong).

    Currently recognizes Mirumoto Bushi School contributions:

      * **Mirumoto 5th Dan** -- ``+10 * vp`` on combat rolls
        (attack-class skills + parry + wound check). Triggers when
        the character has Mirumoto Bushi School at rank >= 5, ``vp`` > 0,
        and the skill is in the combat-roll set.
      * **Mirumoto 2nd Dan free raise** -- ``+5`` on parry rolls.
        Triggers when the character has Mirumoto Bushi School at rank
        >= 2 and ``skill == "parry"``.

    Args:
        character: The acting character (the roll's subject).
        skill: The skill name being rolled (``"attack"``, ``"parry"``,
            ``"wound check"``, etc.).
        modifier: The modifier value attached to the roll. This is the
            number the formatter is about to display; the helper does
            not validate that contributions sum to this value (the
            formatter's safety check covers that), but the returned
            contributions reflect the mechanics' EXPECTED values.
        vp: Number of void points spent on this roll. Defaults to 0.
            Used to size the 5th Dan ``+10 * vp`` contribution.
    """
    # ``modifier`` is consulted by the caller's safety check; the
    # helper itself only needs to know which school-specific
    # mechanics fired, not the actual numeric the engine produced.
    del modifier  # documented but unused by the dispatch
    contributions: list[tuple[str, int]] = []
    if not _is_mirumoto_bushi(character):
        return contributions
    rank = _school_rank(character)

    # Mirumoto 5th Dan: +10 per VP on combat rolls.
    if (
        rank >= 5
        and vp > 0
        and skill in _MIRUMOTO_FIFTH_DAN_COMBAT_SKILLS
    ):
        contributions.append(("Mirumoto 5th Dan", 10 * vp))

    # Mirumoto 2nd Dan free raise: +5 on parry rolls. The free raise
    # is unconditional (no VP cost) so it always contributes when the
    # character has rank >= 2 and the skill is parry.
    if rank >= 2 and skill == "parry":
        contributions.append(("Mirumoto 2nd Dan free raise", 5))

    # Order by descending value so the formatter renders the most
    # significant source first.
    contributions.sort(key=lambda item: -item[1])
    return contributions
