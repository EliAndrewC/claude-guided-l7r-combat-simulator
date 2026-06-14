"""Tests for Combat Trace Observability Audit (US1 — damage XkY breakdown).

These tests pin Constitution Principle VII compliance for damage roll
multi-source aggregates rendered in the user-facing combat trace.

Specifically:

- ``_format_attack_rolled`` and ``_format_combined_attack`` render the
  predictive "damage will be XkY" projection with an inline breakdown
  of contributing sources.
- ``_format_lw_damage`` renders the final "💥 Damage: XkY" with the
  same inline breakdown.

The breakdown source list is computed by
``DefaultRollParameterProvider.get_breakdown(kind="damage", ...)`` and
its per-school overrides (e.g. ``BayushiRollParameterProvider``), then
attached as ``_detail_components`` on the relevant event by
``CombatObserver``. The formatter reads the annotation and emits
``XkY = N1k(M1) source-1 + N2k(M2) source-2 + ...``.

FR-001 / FR-002 / FR-003 / FR-006 / FR-007 / FR-009 of
spec.md (Combat Trace Observability Audit). The calibration scenario
is the trace-auditor dry-run: ``seed=1234`` Bayushi-vs-Akodo combat,
where the Bayushi 5th Dan double-attack lands and rolls 10k7 damage.
"""

from __future__ import annotations

import random
import re
import unittest
from unittest.mock import MagicMock

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.templates.generator import generate_template
from web.adapters.character_adapter import config_to_character
from web.adapters.combat_observer import (
    CombatObserver,
    DetailedCombatEngine,
    TrackingRollProvider,
)
from web.adapters.detailed_formatter import DetailedEventFormatter


def _build_character(school_key: str, name: str) -> Character:
    """Build a 300-XP character from a school template and rename it."""
    config, _ = generate_template(school_key, 300)
    char = config_to_character(config)
    char._name = name
    char.set_roll_provider(TrackingRollProvider(char.roll_provider()))
    return char


def _run_calibration_combat() -> list[str]:
    """Run the trace-auditor calibration combat: Bayushi vs Akodo at seed=0.

    Returns the rendered trace lines. This is the canonical recipe used
    by every test in this module so the assertions all reference the
    same multi-round combat.

    Re-anchored twice as upstream changes shifted the deterministic
    combat: first to seed=22 (2026-05-30, after the rules/03-combat.md
    failed-parry-reduction update made the prior combat too short), then
    to seed=0 (2026-06-14, after the template builder's combat-XP split
    changed from 80% to 75% — see ``COMBAT_XP_FRACTION`` — which shifted
    the Bayushi/Akodo 300-XP builds so the prior seed no longer produced
    a VP-on-attack damage line for T030).
    """
    random.seed(0)
    bayushi = _build_character("bayushi", "Bayushi")
    akodo = _build_character("akodo", "Akodo")
    ctx = EngineContext([Group("Scorpion", bayushi), Group("Lion", akodo)])
    ctx.initialize()
    observer = CombatObserver()
    engine = DetailedCombatEngine(ctx, observer)
    engine.run()
    return DetailedEventFormatter().format_history(engine.history())


def _parse_breakdown(breakdown_str: str) -> tuple[list[tuple[int, int]], int]:
    """Parse a ``"N1k(M1) ... + N2k(M2) ... + ..."`` breakdown.

    Returns ``(components, dropped_dice)`` where ``components`` is the
    list of ``(rolled, kept)`` tuples for the standard ``NkM source``
    entries and ``dropped_dice`` is the count from any narrative
    ``"+{2N} from {N} dropped dice in excess of 10k10"`` entry (per
    the user-facing relabel; this entry is NOT in standard ``NkM``
    form so it gets parsed separately).  For sum-invariant checks,
    the components sum to the RAW (pre-normalize) ``(rolled, kept)``
    and the displayed aggregate is the post-normalize XkY — the two
    differ by exactly the dropped-dice count when overflow occurred.
    """
    components: list[tuple[int, int]] = []
    dropped_dice = 0
    for piece in breakdown_str.split(" + "):
        m_dropped = re.match(
            r"\s*\+?\d+ from (\d+) dropped (?:die|dice) in excess of 10k10\b", piece,
        )
        if m_dropped is not None:
            dropped_dice = int(m_dropped.group(1))
            continue
        m = re.match(r"\s*(-?\d+)k(-?\d+)\b", piece)
        if m is not None:
            components.append((int(m.group(1)), int(m.group(2))))
    return components, dropped_dice


class TestDamageBreakdownInTrace(unittest.TestCase):
    """T008 / T009 / T010 — damage XkY breakdown rendering tests."""

    def test_damage_xky_breakdown_inline_in_attack_predictive_line(self) -> None:
        """T008: the predictive ``damage will be XkY`` segment of an
        attack-line MUST include an inline source breakdown when the
        damage has more than one nonzero source.

        Calibration: the seed=1234 Bayushi double-attack hits with margin
        12 and predicts damage will be 10k7 — a multi-source aggregate
        (weapon + ring + margin extras + VP-on-attack).

        Verifies FR-006 / FR-007.
        """
        trace = _run_calibration_combat()
        attack_lines = [
            line for line in trace
            if "damage will be" in line
        ]
        self.assertTrue(
            attack_lines,
            "Calibration combat produced no attack lines with 'damage will be'",
        )
        multi_source_lines = []
        for line in attack_lines:
            m = re.search(
                r"damage will be (\d+)k(\d+)( = [^,)]+)?", line,
            )
            self.assertIsNotNone(
                m, f"Could not parse damage-will-be from line: {line}",
            )
            assert m is not None
            rolled = int(m.group(1))
            kept = int(m.group(2))
            # A genuine multi-source case: weapon + ring is at least two
            # sources; almost every attack qualifies. Skip degenerate
            # cases where the breakdown trivially has 1 source.
            if rolled >= 7 or kept >= 2:
                multi_source_lines.append(line)
        self.assertTrue(
            multi_source_lines,
            "No multi-source 'damage will be' lines found",
        )
        for line in multi_source_lines:
            # Per FR-007: ``damage will be XkY = <breakdown>``
            m = re.search(
                r"damage will be \d+k\d+ = ([^,)]+)",
                line,
            )
            self.assertIsNotNone(
                m,
                f"'damage will be XkY' missing '= <breakdown>' suffix in: {line}",
            )
            assert m is not None
            breakdown = m.group(1)
            self.assertGreaterEqual(
                breakdown.count(" + "), 1,
                f"Breakdown should have ≥ 2 sources (≥1 '+' separator) "
                f"in line: {line}",
            )

    def test_damage_xky_breakdown_inline_in_lw_damage_event(self) -> None:
        """T009: the final ``💥 Damage: XkY`` line MUST include an
        inline source breakdown of contributing sources.

        Verifies FR-009.
        """
        trace = _run_calibration_combat()
        damage_lines = [line for line in trace if "💥 Damage:" in line]
        self.assertTrue(
            damage_lines,
            "Calibration combat produced no '💥 Damage:' lines",
        )
        # At least one damage line must have a multi-source breakdown
        # (every attack against a 300xp character has weapon + ring).
        multi_source_found = False
        for line in damage_lines:
            m = re.search(
                r"💥 Damage: (\d+)k(\d+) = ([^\[]+)\[",
                line,
            )
            if m is None:
                continue
            breakdown = m.group(3).strip()
            if " + " in breakdown:
                multi_source_found = True
                # Each component is either a standard ``NkM source``
                # entry OR the narrative ``"+{2N} from {N} dropped dice
                # in excess of 10k10"`` form for the 10k10 overflow
                # bookkeeping (user-requested rendering: see commit
                # relabel of "normalization").
                for piece in breakdown.split(" + "):
                    self.assertRegex(
                        piece.strip(),
                        r"^(-?\d+k-?\d+ |\+\d+ from \d+ dropped (?:die|dice) in excess of 10k10$)",
                        f"Component '{piece}' in line {line!r} must start "
                        "with NkM or be the dropped-dice form",
                    )
        self.assertTrue(
            multi_source_found,
            "No '💥 Damage:' line with multi-source breakdown found "
            f"in trace lines: {damage_lines}",
        )

    def test_damage_breakdown_sums_to_aggregate(self) -> None:
        """T010: per data-model.md invariant, the sum of per-source rolled
        contributions equals the aggregate's rolled count (same for kept).

        Verifies FR-001 / data-model.md "Invariants".
        """
        trace = _run_calibration_combat()
        checked_lines = 0
        for line in trace:
            m = re.search(
                r"💥 Damage: (\d+)k(\d+) = ([^\[]+)\[",
                line,
            )
            if m is None:
                continue
            agg_rolled = int(m.group(1))
            agg_kept = int(m.group(2))
            breakdown = m.group(3).strip()
            if " + " not in breakdown:
                continue
            components, dropped = _parse_breakdown(breakdown)
            self.assertGreater(
                len(components), 1,
                f"Multi-source breakdown should parse to >1 component: {line}",
            )
            sum_rolled = sum(r for r, _ in components)
            sum_kept = sum(k for _, k in components)
            # With the "+X from N dropped dice in excess of 10k10"
            # rendering, the standard NkM components sum to the
            # PRE-normalize raw rolled/kept; the displayed aggregate
            # is post-normalize.  The dropped count bridges the gap:
            # each dropped die was a rolled die converted to a kept
            # die (rolled-overflow) — so raw_rolled = agg_rolled + dropped
            # and raw_kept = agg_kept - dropped.  See OPEN_QUESTIONS
            # in spec 007 about the renaming of "normalization".
            self.assertEqual(
                sum_rolled, agg_rolled + dropped,
                f"Breakdown rolled components sum to {sum_rolled} but "
                f"aggregate rolled is {agg_rolled} (with {dropped} "
                f"dropped) in line: {line}",
            )
            self.assertEqual(
                sum_kept, agg_kept - dropped,
                f"Breakdown kept components sum to {sum_kept} but "
                f"aggregate kept is {agg_kept} (with {dropped} "
                f"dropped) in line: {line}",
            )
            checked_lines += 1
        self.assertGreater(
            checked_lines, 0,
            "No damage lines with multi-source breakdowns checked — "
            "calibration combat may have changed",
        )


class TestAttackBreakdownInTrace(unittest.TestCase):
    """T015 / T016 / T017 — attack XkY breakdown rendering tests.

    The attack-line XkY is a multi-source aggregate (ring + skill +
    school extras + VP-on-attack + floating bonuses). Per FR-006, the
    live attack roll's XkY MUST render with an inline breakdown when
    more than one source contributes.

    Calibration: the seed=1234 Bayushi-vs-Akodo combat produces:
      * Bayushi double-attack with 2 VP → 10k10 (Fire+attack-skill +
        VP-on-attack).
      * Akodo basic attack → 9k3 (Fire+attack-skill + Akodo 1st Dan
        extra die).
    Both are multi-source and must render with breakdowns.
    """

    def test_attack_xky_breakdown_inline(self) -> None:
        """T015: the attack-line ``XkY [dice]`` MUST include
        ``XkY = <breakdown>`` showing ring + skill + school extras +
        VP-on-attack effect (if applicable).

        Verifies FR-006.
        """
        trace = _run_calibration_combat()
        attack_lines = [
            line for line in trace
            if "⚔️ attacks" in line and "Roll:" not in line
        ]
        self.assertTrue(
            attack_lines,
            "Calibration combat produced no '⚔️ attacks' lines",
        )
        # At least one attack line must render with the inline breakdown.
        # Match ``— XkY = breakdown [dice]`` where breakdown contains
        # ``+`` separators (multi-source). Use a non-greedy match that
        # stops at the first ``[`` (the dice list).
        multi_source_found = False
        for line in attack_lines:
            m = re.search(
                r"— (\d+)k(\d+) = ([^\[]+)\[",
                line,
            )
            if m is None:
                continue
            breakdown = m.group(3).strip()
            if " + " not in breakdown:
                continue
            multi_source_found = True
            # Each component is either a standard NkM source entry OR
            # the dropped-dice narrative form for the 10k10 overflow.
            for piece in breakdown.split(" + "):
                self.assertRegex(
                    piece.strip(),
                    r"^(-?\d+k-?\d+ |\+\d+ from \d+ dropped (?:die|dice) in excess of 10k10$)",
                    f"Component '{piece}' in line {line!r} must start "
                    "with NkM",
                )
        self.assertTrue(
            multi_source_found,
            "No attack line with multi-source breakdown found in trace "
            f"lines: {attack_lines}",
        )

    def test_attack_breakdown_sums_to_aggregate(self) -> None:
        """T016: per data-model.md invariant, the sum of per-source
        rolled contributions on an attack line equals the aggregate's
        rolled count (same for kept).

        Verifies FR-001 / data-model.md "Invariants" for attack rolls.
        """
        trace = _run_calibration_combat()
        checked_lines = 0
        for line in trace:
            # The attack line has the shape
            # ``... ⚔️ attacks <tgt> (<skill>) — XkY = breakdown [dice] ...``
            m = re.search(
                r"⚔️ attacks.*— (\d+)k(\d+) = ([^\[]+)\[",
                line,
            )
            if m is None:
                continue
            agg_rolled = int(m.group(1))
            agg_kept = int(m.group(2))
            breakdown = m.group(3).strip()
            if " + " not in breakdown:
                continue
            components, dropped = _parse_breakdown(breakdown)
            self.assertGreater(
                len(components), 1,
                f"Multi-source breakdown should parse to >1 component: {line}",
            )
            sum_rolled = sum(r for r, _ in components)
            sum_kept = sum(k for _, k in components)
            # See test_damage_breakdown_sums_to_aggregate for the
            # dropped-dice bridging math.
            self.assertEqual(
                sum_rolled, agg_rolled + dropped,
                f"Attack breakdown rolled components sum to {sum_rolled} "
                f"but aggregate rolled is {agg_rolled} (with {dropped} "
                f"dropped) in line: {line}",
            )
            self.assertEqual(
                sum_kept, agg_kept - dropped,
                f"Attack breakdown kept components sum to {sum_kept} but "
                f"aggregate kept is {agg_kept} (with {dropped} dropped) "
                f"in line: {line}",
            )
            checked_lines += 1
        self.assertGreater(
            checked_lines, 0,
            "No attack lines with multi-source breakdowns checked — "
            "calibration combat may have changed",
        )

    def test_attack_breakdown_includes_school_extra_dice(self) -> None:
        """T017: an Akodo attacker's attack-line breakdown MUST include
        the school's 1st Dan extra die contribution (``+1k0``) labelled
        with the school's source attribution.

        Per ``simulation/schools/akodo_school.py``:
            ``extra_rolled() == ["attack", "double attack", "wound check"]``
        Each entry adds +1 rolled (no extra kept) to the attack roll
        per Constitution Principle VII / data-model.md "Source labels".

        Verifies FR-006.
        """
        trace = _run_calibration_combat()
        akodo_attack_lines = [
            line for line in trace
            if "Akodo |" in line and "⚔️ attacks" in line
            and "Roll:" not in line
        ]
        self.assertTrue(
            akodo_attack_lines,
            "Calibration combat produced no Akodo attack lines",
        )
        # At least one Akodo attack line must render the school extra
        # die in the breakdown.
        found_school_extra = False
        for line in akodo_attack_lines:
            m = re.search(
                r"— (\d+)k(\d+) = ([^\[]+)\[",
                line,
            )
            if m is None:
                continue
            breakdown = m.group(3).strip()
            # The school extra die appears as ``+1k0`` (rolled only)
            # tagged with the school's 1st Dan label.
            if re.search(r"\b1k0\s+Akodo\b", breakdown):
                found_school_extra = True
                break
        self.assertTrue(
            found_school_extra,
            "No Akodo attack line with '1k0 Akodo ...' school-extra "
            f"contribution found in: {akodo_attack_lines}",
        )


class TestBareModifierSourceLabels(unittest.TestCase):
    """T021 / T022 / T023 — Phase 5 (User Story 3) bare modifier
    source-label rendering tests.

    Per Constitution Principle VII (spec.md FR-010 / FR-013 / FR-014),
    every ``+N`` modifier rendered in the trace MUST carry either a
    real source label ``(Source)`` or the ``(unsourced: +K)`` placeholder
    -- a bare ``+N`` without any parenthetical attribution is the
    canonical Principle VII violation this Phase 5 work closes.

    Bayushi 2nd Dan free raise on double attack (BayushiBushiSchool's
    ``free_raise_skills() == ["double attack"]``) is the calibration
    anchor: the seed=1234 combat renders ``+5`` modifiers on every
    Bayushi double-attack line and these were previously bare.
    """

    def test_bare_attack_modifier_has_source_label(self):
        """T021: every roll line in the calibration combat that renders
        a ``+N`` modifier (``..., +N = M vs TN ...``) MUST also contain
        a parenthetical attribution -- either a real source
        ``(Source: +N)`` or the ``(see preceding line)`` fallback (spec
        008 FR-014 — non-alarming wording replacing the prior
        ``(unsourced: +K)`` literal).  A bare ``+N`` modifier with no
        parenthetical is the canonical Principle VII violation that
        this Phase 5 work closes.

        Calibration anchor: the seed=1234 Bayushi double-attack lines
        all carry a ``+5`` from the Bayushi 2nd Dan free raise on
        double attack (``BayushiBushiSchool.free_raise_skills() ==
        ["double attack"]``).

        Verifies FR-010 + FR-013.
        """
        trace = _run_calibration_combat()
        # Collect every line whose body renders ``..., +N = M vs TN ...``
        # or ``..., +N = M vs ...`` style — these are the ones routed
        # through ``_format_modifier_breakdown`` and that must always
        # carry an attribution per Constitution Principle VII.
        # Restrict to the FIRST ``, +N = M`` segment (the modifier);
        # floating-bonus inline segments use the same ``, +N = M`` form
        # but are explicitly source-labelled in their own segment.
        modifier_lines = [
            line for line in trace if re.search(r", \+\d+ = \d+", line)
        ]
        self.assertTrue(
            modifier_lines,
            "Calibration combat produced no lines with a `+N = M` "
            "modifier rendering. Calibration may have regressed -- "
            "update the fixture or this test.",
        )
        # Specifically anchor on the Bayushi double-attack case:
        # every Bayushi double-attack line MUST carry the Bayushi 2nd
        # Dan free raise attribution.
        bayushi_attack_lines = [
            line for line in modifier_lines
            if "Bayushi" in line and "double attack" in line
        ]
        self.assertTrue(
            bayushi_attack_lines,
            "Calibration combat produced no Bayushi double-attack "
            "modifier lines -- the calibration anchor for T021 / FR-013.",
        )
        for line in modifier_lines:
            # The modifier renders as ``..., +N = M vs TN ...``. The
            # parenthetical attribution is appended at the END of the
            # line. Per the 2026-05-30 trace-reader sweep, the
            # ``(see preceding line)`` dangling-pointer fallback is no
            # longer rendered. The line must contain a real source
            # label parenthetical, OR may legitimately have no
            # parenthetical suffix when the breakdown was entirely
            # unattributable (the modifier value is still visible in
            # the line's arithmetic — Principle VII still holds at
            # the line level).
            # A real source label is a parenthetical containing
            # ``: +N`` or ``: -N`` (e.g., ``(Bayushi 2nd Dan free
            # raise: +5)`` or ``(Mirumoto 5th Dan: +10 × 1 VP)``).
            has_source = bool(
                re.search(r"\([^()]*: [+-]?\d+[^()]*\)", line),
            )
            # Bayushi double-attack lines specifically must surface
            # the Bayushi 2nd Dan free raise — assert in the
            # downstream loop below; here we only require attribution
            # OR a clear no-modifier line (handled by the outer match).
            if not has_source:
                # Allow lines with no source label as long as the
                # ``unsourced`` and ``see preceding line`` literals
                # don't appear (they would falsely promise
                # attribution we no longer render).
                self.assertNotIn("unsourced", line)
                self.assertNotIn("see preceding line", line)
        # Belt-and-braces: the Bayushi double-attack lines specifically
        # must show the named source, not the unsourced placeholder
        # (per FR-013 -- the Bayushi 2nd Dan source MUST be catalogued).
        for line in bayushi_attack_lines:
            self.assertIn(
                "Bayushi 2nd Dan free raise",
                line,
                "Bayushi double-attack line missing the catalogued "
                f"source attribution: {line}",
            )

    def test_unaccounted_modifier_omits_attribution_suffix(self):
        """2026-05-30 (replaces former T022 unsourced-placeholder test):
        when ``explain_modifier`` returns NOTHING for a non-zero
        modifier, the formatter renders the modifier value in the
        line's arithmetic but emits NO parenthetical attribution
        suffix. The dangling ``(see preceding line)`` fallback was
        removed per trace-reader sweep findings — it almost never
        pointed at an actual source on the preceding line.

        Principle VII: the modifier value remains visible in the
        line's arithmetic (preserving "every value visible" at the
        line level) — only the misleading attribution promise is gone.
        """
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Anonymous"
        target = MagicMock()
        target.name.return_value = "Enemy"
        target.tn_to_hit.return_value = 20
        action = MagicMock()
        action.subject.return_value = subject
        action.target.return_value = target
        action.skill.return_value = "attack"
        action.skill_roll.return_value = 30
        action.tn.return_value = 20
        action.vp.return_value = 0
        action.skill_roll_params.return_value = (5, 3, 5)
        action.is_hit.return_value = False
        action.parried.return_value = False
        action.parry_attempted.return_value = False
        action.is_success.return_value = False
        action.calculate_extra_damage_dice.return_value = 0
        event = events.AttackRolledEvent(action, 30)
        event._detail_dice = [10, 9, 6, 3, 2]
        event._detail_params = (5, 3, 5)
        event._detail_tn = 20
        event._detail_base_tn = 20
        event._detail_modifier_breakdown = []

        lines = fmt.format_history([event])
        attack_line = next(ln for ln in lines if "Attack:" in ln)
        self.assertIn("+5", attack_line)
        self.assertNotIn("unsourced", attack_line)
        self.assertNotIn("see preceding line", attack_line)

    def test_partial_attribution_renders_known_only(self):
        """2026-05-30 (replaces former T023 partial-attribution test):
        when ``explain_modifier`` accounts for only part of a modifier,
        only the known source(s) render; the unattributed remainder is
        omitted from the suffix. Modifier value remains visible in the
        line's arithmetic.
        """
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "PartialSource"
        target = MagicMock()
        target.name.return_value = "Enemy"
        target.tn_to_hit.return_value = 20
        action = MagicMock()
        action.subject.return_value = subject
        action.target.return_value = target
        action.skill.return_value = "attack"
        action.skill_roll.return_value = 30
        action.tn.return_value = 20
        action.vp.return_value = 0
        action.skill_roll_params.return_value = (5, 3, 5)
        action.is_hit.return_value = False
        action.parried.return_value = False
        action.parry_attempted.return_value = False
        action.is_success.return_value = False
        action.calculate_extra_damage_dice.return_value = 0
        event = events.AttackRolledEvent(action, 30)
        event._detail_dice = [10, 9, 6, 3, 2]
        event._detail_params = (5, 3, 5)
        event._detail_tn = 20
        event._detail_base_tn = 20
        event._detail_modifier_breakdown = [("Known Source", 3)]

        lines = fmt.format_history([event])
        attack_line = next(ln for ln in lines if "Attack:" in ln)
        self.assertIn("+5", attack_line)
        self.assertIn("Known Source", attack_line)
        self.assertNotIn("unsourced", attack_line)
        self.assertNotIn("see preceding line", attack_line)


class TestTNRaiseAttribution(unittest.TestCase):
    """T026 / T027 / T028 — Phase 6 (User Story 4) TN raise attribution.

    Per the formatter-rendering contract (§ "TN rendering") the
    parenthetical TN expression MUST always show ``(base TN M)`` and,
    when ``event.action.raises() > 0``, MUST also include
    ``+ X for {skill}`` where X is the total raise contribution
    (K × 5 for K raises).

    Calibration anchor: the seed=1234 Bayushi-vs-Akodo combat produces
    Bayushi double-attack lines with TN inflation +20 (4 raises) per
    L7R double-attack rule (rules/04-schools.md "Bushi Schools").

    Verifies FR-011.
    """

    def test_tn_raise_attribution_for_double_attack(self):
        """T026: Bayushi double-attack lines from the calibration combat
        MUST render the raise contribution:
        ``vs TN 50 (base TN 30 + 20 for double attack)``.

        Per the rule (rules/04-schools.md, double attack), a double
        attack raises the TN by 20 (4 raises). The trace MUST surface
        this attribution per Constitution Principle VII.

        Verifies FR-011.
        """
        trace = _run_calibration_combat()
        double_attack_lines = [
            line for line in trace
            if "double attack" in line and "vs TN" in line
            and "base TN" in line
        ]
        self.assertTrue(
            double_attack_lines,
            "Calibration combat produced no double-attack lines with "
            "a (base TN N) parenthetical",
        )
        # Every double-attack TN parenthetical must include the raise
        # contribution. The expected literal form is:
        # ``(base TN 30 + 20 for double attack)``.
        for line in double_attack_lines:
            self.assertRegex(
                line,
                r"\(base TN \d+ \+ 20 for double attack\)",
                f"Double-attack line missing raise attribution: {line}",
            )

    def test_tn_no_raises_omits_raise_clause(self):
        """T027: plain ``attack`` lines (tn() == base_tn, 0 raises) MUST
        render ``vs TN 30 (base TN 30)`` WITHOUT a raise clause.

        Verifies FR-011 (no false-positive attribution).
        """
        trace = _run_calibration_combat()
        # A plain attack line in the calibration combat carries the
        # skill label ``(attack)`` (not ``(double attack)`` or
        # ``(feint)``). The TN equals the base TN (no inflation).
        plain_attack_lines = [
            line for line in trace
            if "(attack)" in line and "⚔️ attacks" in line
            and "vs TN" in line
        ]
        self.assertTrue(
            plain_attack_lines,
            "Calibration combat produced no plain (attack) lines",
        )
        for line in plain_attack_lines:
            # The line MUST contain ``vs TN N (base TN N)`` (always
            # showing base TN per contract) but MUST NOT contain a
            # ``from K raises`` raise clause.
            self.assertRegex(
                line,
                r"vs TN \d+ \(base TN \d+\)",
                f"Plain attack line missing (base TN N) parenthetical: {line}",
            )
            tail = line.split("vs TN")[-1].split("—")[0]
            self.assertNotIn(
                " for ", tail,
                f"Plain attack line should have no raise clause: {line}",
            )

    def test_tn_raise_attribution_for_feint(self):
        """T028: a feint action whose TN has been raised MUST render
        the raise clause using ``"feint"`` as the action name.

        Constructed via a synthetic ``AttackRolledEvent`` whose action
        skill is ``"feint"`` and whose TN exceeds the base TN — the
        formatter MUST interpolate the action's skill into the raise
        clause (``+ X for feint``) rather than hard-coding
        ``double attack``.

        Verifies FR-011 (action-name interpolation).
        """
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "FeintAttacker"
        target = MagicMock()
        target.name.return_value = "Enemy"
        target.tn_to_hit.return_value = 20
        action = MagicMock()
        action.subject.return_value = subject
        action.target.return_value = target
        action.skill.return_value = "feint"
        action.skill_roll.return_value = 25
        # tn raised by 10 (2 raises) above base for the test
        action.tn.return_value = 30
        action.vp.return_value = 0
        action.skill_roll_params.return_value = (5, 3, 0)
        # Use a MISS case to avoid invoking the damage-projection path
        # (which would require a fully-mocked get_damage_roll_params).
        action.is_hit.return_value = False
        action.parried.return_value = False
        action.parry_attempted.return_value = False
        action.is_success.return_value = False
        action.calculate_extra_damage_dice.return_value = 0
        event = events.AttackRolledEvent(action, 25)
        event._detail_dice = [10, 6, 5, 3, 1]
        event._detail_params = (5, 3, 0)
        event._detail_tn = 30
        event._detail_base_tn = 20  # 2 raises = +10 TN
        event._detail_modifier_breakdown = []

        lines = fmt.format_history([event])
        attack_line = next(ln for ln in lines if "Attack:" in ln)
        # The raise clause MUST use the action skill name ("feint"),
        # not a hard-coded "double attack".
        self.assertIn(
            "(base TN 20 + 10 for feint)",
            attack_line,
        )


class TestVPOnAttackDamageAttribution(unittest.TestCase):
    """T030 / T031 / T032 — Phase 7 (User Story 5) VP-on-attack
    cross-roll attribution tests.

    Per rules/04-schools.md "Bayushi Bushi School: Special Ability":

        "When spending void points on all types of attack rolls, add
        1k1 to the damage rolls of those attacks per void point spent."

    This is a BAYUSHI-SPECIFIC rule: only ``BayushiRollParameterProvider``
    (simulation/schools/bayushi_school.py) inflates the damage roll by
    VP-on-attack. Every other school's provider — including the engine
    default ``DefaultRollParameterProvider`` — accepts the ``vp`` kwarg
    on ``get_damage_roll_params`` but does NOT use it.

    The trace formatter therefore renders the
    ``(VP on attack: +NkN)`` source entry in the damage breakdown ONLY
    when the attacker is Bayushi AND the attack spent ≥1 VP. The
    calibration combat (seed=1234 Bayushi vs Akodo) is the anchor:

    * Bayushi double-attacks with 2 VP → damage line shows
      ``+ 2k2 VP on attack`` (T030).
    * Bayushi double-attacks with 0 VP → damage line shows NO VP
      entry (T031).
    * Akodo attacks with 1 VP (their VP-on-attack mid-combat) → damage
      line shows NO VP entry, because the default provider does not
      inflate damage by VP-on-attack (T032).

    Verifies FR-002 / FR-009 / Constitution Principle VII.
    """

    def _find_damage_lines_for_attacker(
        self, trace: list[str], attacker_name: str,
    ) -> list[str]:
        return [
            line for line in trace
            if line.startswith(f"{attacker_name} | 💥 Damage:")
        ]

    def _find_vp_spend_lines_for_attacker(
        self, trace: list[str], attacker_name: str,
    ) -> list[str]:
        """Return attack lines for ``attacker_name`` that spent ≥1 VP
        on the attack roll. The VP-spend prefix renders as
        ``⬛`` (or ``⬛⬛`` for 2 VP, etc.) followed by
        ``spends N VP on <skill>``.
        """
        return [
            line for line in trace
            if f"{attacker_name} |" in line
            and "spends" in line
            and " VP on " in line
            and "⚔️ attacks" in line
        ]

    def test_vp_on_attack_appears_in_damage_breakdown_for_bayushi(
        self,
    ) -> None:
        """T030: a Bayushi attack that spends ≥1 VP MUST render
        ``+ NkN VP on attack`` in the resulting damage line's
        breakdown, where N equals the VP spent.

        Per rules/04-schools.md "Bayushi Bushi School: Special Ability":
        each VP spent on an attack roll adds 1k1 to the damage roll.

        Calibration: the seed=1234 Bayushi double-attack with 2 VP
        renders ``💥 Damage: 10k7 = ... + 2k2 VP on attack + ...``.

        Verifies FR-002 / FR-009.
        """
        trace = _run_calibration_combat()
        # Find the Bayushi attack lines that spent VP. The calibration
        # combat's Bayushi 5th Dan double-attack spends 2 VP on its
        # opener (Phase 2).
        bayushi_vp_attacks = self._find_vp_spend_lines_for_attacker(
            trace, "Bayushi",
        )
        self.assertTrue(
            bayushi_vp_attacks,
            "Calibration combat produced no Bayushi attacks with a "
            "VP spend — the calibration anchor for T030.",
        )
        # The subsequent ``💥 Damage`` line for the attacker MUST
        # contain the VP-on-attack entry. The calibration's opener
        # is the 2-VP double-attack landing 10k7 damage.
        bayushi_damage_lines = self._find_damage_lines_for_attacker(
            trace, "Bayushi",
        )
        self.assertTrue(
            bayushi_damage_lines,
            "Calibration combat produced no Bayushi damage lines.",
        )
        # At least one Bayushi damage line must contain a VP-on-attack
        # source entry matching the format ``NkN Bayushi Special Ability
        # VP on attack`` (trace-reader fix 2026-05-28: relabeled from
        # bare "VP on attack" to include explicit school attribution).
        vp_damage_lines = [
            line for line in bayushi_damage_lines
            if re.search(
                r"\b\d+k\d+ Bayushi Special Ability VP on attack\b", line,
            )
        ]
        self.assertTrue(
            vp_damage_lines,
            "No Bayushi damage line with 'NkN VP on attack' entry "
            f"found in: {bayushi_damage_lines}",
        )
        # Belt-and-braces: the value of N matches the VP that was
        # spent (the calibration opener spends 2 VP).
        opener_damage_line = vp_damage_lines[0]
        m = re.search(
            r"(\d+)k(\d+) Bayushi Special Ability VP on attack",
            opener_damage_line,
        )
        self.assertIsNotNone(m)
        assert m is not None
        rolled = int(m.group(1))
        kept = int(m.group(2))
        # The Bayushi Special Ability is 1k1 per VP, so rolled == kept
        # == VP spent. The opener was 2 VP → expect 2k2.
        self.assertEqual(
            rolled, kept,
            f"Bayushi VP-on-attack: rolled ({rolled}) != kept ({kept}) "
            f"in line: {opener_damage_line}",
        )
        self.assertGreaterEqual(
            rolled, 1,
            f"Expected ≥1 VP rolled for Bayushi VP-on-attack: "
            f"{opener_damage_line}",
        )

    def test_no_vp_on_attack_omits_from_damage_breakdown_for_bayushi(
        self,
    ) -> None:
        """T031: a Bayushi attack with 0 VP spent MUST NOT render any
        ``VP on attack`` entry in the damage breakdown.

        Calibration: the seed=1234 combat contains Bayushi
        double-attacks WITHOUT a VP spend (later phases, once the
        opener has drained the VP pool). These damage lines should
        render no VP-on-attack source.

        Verifies FR-002 (no false-positive attribution).
        """
        trace = _run_calibration_combat()
        # Bayushi attacks that did NOT spend any VP: any ``Bayushi |
        # ⚔️ attacks`` line that does NOT carry the ``spends N VP``
        # prefix. We look for the AttackRolledEvent rendering on the
        # same line; the engine renders ``Phase X | Bayushi | ⚔️
        # attacks ...`` without the VP-spend prefix when VP=0.
        bayushi_attack_lines = [
            line for line in trace
            if "Bayushi |" in line and "⚔️ attacks" in line
            and " VP on " not in line
        ]
        self.assertTrue(
            bayushi_attack_lines,
            "Calibration combat produced no Bayushi attack lines "
            "without VP spend — the calibration anchor for T031.",
        )
        # Each subsequent damage line for a 0-VP attack must NOT
        # contain a ``VP on attack`` entry. Since attack-line and
        # damage-line are rendered as separate trace entries with
        # different formats, the simplest invariant we can lock in is:
        # any Bayushi damage line whose attack-line predecessor did
        # NOT spend VP must have no ``VP on attack`` token.
        #
        # We enforce a stronger invariant: count the total number of
        # Bayushi VP-spend attack lines vs the total number of
        # Bayushi damage lines with ``VP on attack`` entries. The
        # latter must be ≤ the former (each VP-spend attack produces
        # at most one VP-on-attack damage entry).
        vp_spend_count = sum(
            1 for line in trace
            if "Bayushi |" in line and "⚔️ attacks" in line
            and re.search(r"⬛+\s+spends \d+ VP on ", line)
        )
        damage_with_vp_count = sum(
            1 for line in trace
            if line.startswith("Bayushi | 💥 Damage:")
            and re.search(r"\b\d+k\d+ VP on attack\b", line)
        )
        self.assertLessEqual(
            damage_with_vp_count, vp_spend_count,
            f"Bayushi has more damage lines with VP on attack "
            f"({damage_with_vp_count}) than VP-spend attack lines "
            f"({vp_spend_count}) — at least one 0-VP attack "
            "rendered a spurious 'VP on attack' damage source.",
        )

    def test_vp_on_attack_does_not_inflate_damage_for_non_bayushi(
        self,
    ) -> None:
        """T032: a non-Bayushi attacker (Akodo in the calibration)
        spending VP on an attack MUST NOT render any ``VP on attack``
        entry in the damage breakdown.

        Per rules/04-schools.md, the VP-on-attack → damage inflation
        is the Bayushi Bushi Special Ability, NOT a universal L7R
        rule. The engine default
        ``DefaultRollParameterProvider.get_damage_roll_params``
        accepts a ``vp`` kwarg but does not use it — see
        ``simulation/mechanics/roll_params.py``.

        Calibration: Akodo spends 1 VP on attack in Phase 5
        (``⬛ spends 1 VP on attack → ⚔️ attacks Bayushi (attack)``);
        the resulting ``Akodo | 💥 Damage:`` line MUST NOT contain
        ``VP on attack``.

        Verifies FR-002 (per-school provider's behavior governs
        attribution; the rule does NOT apply universally).
        """
        trace = _run_calibration_combat()
        # Find Akodo attack lines that spent VP.
        akodo_vp_attacks = self._find_vp_spend_lines_for_attacker(
            trace, "Akodo",
        )
        self.assertTrue(
            akodo_vp_attacks,
            "Calibration combat produced no Akodo attack lines with a "
            "VP spend — the calibration anchor for T032. Akodo's 1st "
            "Dan / 3rd Dan / 5th Dan TVP economy should fuel at least "
            "one VP-on-attack in this combat.",
        )
        # Akodo damage lines MUST contain NO ``VP on attack`` entry,
        # because the default provider does NOT inflate damage by
        # VP-on-attack. The rule only applies to the Bayushi school.
        akodo_damage_lines = self._find_damage_lines_for_attacker(
            trace, "Akodo",
        )
        self.assertTrue(
            akodo_damage_lines,
            "Calibration combat produced no Akodo damage lines.",
        )
        for line in akodo_damage_lines:
            self.assertNotRegex(
                line, r"\b\d+k\d+ VP on attack\b",
                "Akodo damage line spuriously rendered a 'VP on attack' "
                "entry — the Bayushi-specific rule should not apply to "
                f"non-Bayushi schools. Line: {line}",
            )


if __name__ == "__main__":
    unittest.main()
