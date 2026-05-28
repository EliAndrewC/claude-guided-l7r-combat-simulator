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
  * Isawa Ishi School Second Dan: "Free Raise on precepts." --
    standard 2nd-Dan free-raise = +5 modifier on precepts rolls
    (specs/002 OPEN_QUESTIONS Q2 — precepts is the school's signature
    skill and synergises with the 3rd Dan ally-boost ability).
  * Isawa Ishi School Third Dan: "Spend 1 Void Point to add Xk1 to
    another character's roll, where X is your Precepts skill." --
    when fired, the strategy tags the action with ``_ishi_boosted_by``
    (the Ishi source) and ``_ishi_boost_value`` (the rolled Xk1
    result). Attribution reads both fields off the action attached
    to the rolled event.
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


def _is_isawa_ishi(character: Any) -> bool:
    """True iff the character's school is the Isawa Ishi School."""
    school = character.school() if hasattr(character, "school") else None
    if school is None:
        return False
    return bool(school.name() == "Isawa Ishi School")


def _is_bayushi_bushi(character: Any) -> bool:
    """True iff the character's school is the Bayushi Bushi School."""
    school = character.school() if hasattr(character, "school") else None
    if school is None:
        return False
    return bool(school.name() == "Bayushi Bushi School")


def _is_akodo_bushi(character: Any) -> bool:
    """True iff the character's school is the Akodo Bushi School."""
    school = character.school() if hasattr(character, "school") else None
    if school is None:
        return False
    return bool(school.name() == "Akodo Bushi School")


def _is_hida_bushi(character: Any) -> bool:
    """True iff the character's school is the Hida Bushi School."""
    school = character.school() if hasattr(character, "school") else None
    if school is None:
        return False
    return bool(school.name() == "Hida Bushi School")


def explain_modifier(
    character: Any,
    skill: str,
    modifier: int,
    vp: int = 0,
    action: Any = None,
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

    And Isawa Ishi School contributions:

      * **Isawa Ishi 2nd Dan free raise** -- ``+5`` on precepts rolls.
      * **Isawa Ishi 3rd Dan ally boost from {source_name}** --
        ``+_ishi_boost_value`` on any combat roll whose ``action``
        carries the ``_ishi_boosted_by`` tag (set by
        ``EagerAllyBoostStrategy`` when it fires). The contribution is
        attributable to ANY rolling character (not just the
        boosted-from one) because the boost is rendered on the rolled
        event the boosted ally produced -- the trace credit goes to
        the Ishi source, not the rolling ally.

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
        action: The ``Action`` (or wound-check event) the roll
            originated from, if available. Used to read the
            ``_ishi_boosted_by`` / ``_ishi_boost_value`` tags that the
            Ishi 3rd Dan ally-boost strategy writes when it fires.
            ``None`` skips that attribution path (back-compat for
            existing callers).
    """
    # ``modifier`` is consulted by the caller's safety check; most
    # school-specific mechanics produce fixed-value contributions
    # (e.g. ``+5`` for a free raise) and don't need the modifier
    # value itself.  Spec 008 FR-013 (Akodo 4th Dan VP-for-raise on
    # wound check) is the exception — that contribution's value is
    # the residual after fixed sources, so we keep ``modifier`` in
    # scope under a renamed local for clarity.
    modifier_arg = modifier
    contributions: list[tuple[str, int]] = []

    if _is_mirumoto_bushi(character):
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

    elif _is_isawa_ishi(character):
        rank = _school_rank(character)

        # Isawa Ishi 2nd Dan free raise: +5 on precepts rolls
        # (rules/04-schools.md "Isawa Ishi School: 2nd Dan"; see
        # specs/002 OPEN_QUESTIONS Q2). Unconditional free raise: no
        # VP cost, always contributes once the character is rank >= 2.
        if rank >= 2 and skill == "precepts":
            contributions.append(("Isawa Ishi 2nd Dan free raise", 5))

    elif _is_bayushi_bushi(character):
        rank = _school_rank(character)

        # Bayushi Bushi 2nd Dan free raise on double attack
        # (rules/04-schools.md "Bayushi Bushi School: Second Dan"; the
        # school's ``free_raise_skills() == ["double attack"]`` --
        # apply_rank_two_ability installs a FreeRaise(+5) modifier).
        # spec.md FR-013 (Combat Trace Observability Audit): the
        # calibration combat surfaces this as a bare +5 on every
        # Bayushi double-attack line.
        if rank >= 2 and skill == "double attack":
            contributions.append(("Bayushi 2nd Dan free raise", 5))

    elif _is_hida_bushi(character):
        rank = _school_rank(character)

        # Hida Bushi 2nd Dan free raise on counterattack
        # (rules/04-schools.md "Hida Bushi School: Second Dan"; the
        # school's ``free_raise_skills() == ["counterattack"]`` --
        # apply_rank_two_ability installs a FreeRaise(+5) modifier on
        # counterattack rolls).
        if rank >= 2 and skill == "counterattack":
            contributions.append(("Hida 2nd Dan free raise", 5))

    elif _is_akodo_bushi(character):
        rank = _school_rank(character)

        # Akodo Bushi 2nd Dan free raise on wound check
        # (rules/04-schools.md "Akodo Bushi School: Second Dan"; the
        # school's ``free_raise_skills() == ["wound check"]`` --
        # apply_rank_two_ability installs a FreeRaise(+5) modifier on
        # wound-check rolls).
        akodo_2nd_dan_amount = 0
        if rank >= 2 and skill == "wound check":
            akodo_2nd_dan_amount = 5
            contributions.append(("Akodo 2nd Dan free raise", 5))

        # Akodo Bushi 4th Dan VP-for-raise on wound check (spec 008
        # FR-013 — Issue 5).  When the ``AkodoWoundCheckRolledStrategy``
        # spends N VP after the initial roll, it folds ``5 * N`` into
        # the rolled total via ``new_roll = wc_event.roll + 5 * N``.
        # The trace observer computes modifier = ``event.roll - kept_sum``,
        # so the Akodo 4th Dan VP raise contributes ``5 * N`` to the
        # modifier.  Once the 2nd Dan free raise (if any) is accounted
        # for, the residual ``modifier - (2nd Dan amount)`` is the
        # Akodo 4th Dan VP raise — divisible by 5 (in fives, one per VP).
        #
        # rules/04-schools.md "Akodo Bushi School: Fourth Dan".
        if rank >= 4 and skill == "wound check":
            residual = modifier_arg - akodo_2nd_dan_amount
            if residual > 0 and residual % 5 == 0:
                contributions.append(("Akodo 4th Dan VP raises", residual))

    # Isawa Ishi 3rd Dan ally boost attribution: applies to the BOOSTED
    # roll regardless of the rolling character's school
    # (rules/04-schools.md "Isawa Ishi School: 3rd Dan"). The
    # ``EagerAllyBoostStrategy`` tags the rolled action with
    # ``_ishi_boosted_by`` (the Ishi source character) and
    # ``_ishi_boost_value`` (the rolled Xk1 result). Attribution goes to
    # the Ishi source, not the rolling character.
    if action is not None:
        ishi_source = getattr(action, "_ishi_boosted_by", None)
        boost_value = getattr(action, "_ishi_boost_value", None)
        if ishi_source is not None and isinstance(boost_value, int) and boost_value > 0:
            source_name = ishi_source.name() if hasattr(ishi_source, "name") else "unknown"
            contributions.append((
                f"Isawa Ishi 3rd Dan ally boost from {source_name}",
                boost_value,
            ))

    # Hida Bushi School Special Ability attribution: applies to the
    # ATTACKER's attack roll regardless of the attacker's own school
    # (rules/04-schools.md "Hida Bushi School: Special Ability").
    # ``HidaTakeCounterattackActionEvent`` tags the attack action with
    # ``_counterattack_roll_bonus`` when the Hida counterattacks as a
    # 1-die interrupt; the engine then adds that value directly to the
    # attacker's roll. The trace must show the +5 with a source label
    # so the reader understands why the attack's modifier is +5
    # higher than expected (Principle VII).
    if action is not None:
        ca_bonus = getattr(action, "_counterattack_roll_bonus", 0)
        if isinstance(ca_bonus, int) and ca_bonus > 0:
            contributions.append((
                "Hida special ability free raise",
                ca_bonus,
            ))

    # Order by descending value so the formatter renders the most
    # significant source first.
    contributions.sort(key=lambda item: -item[1])
    return contributions
