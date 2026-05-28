#!/usr/bin/env python3

#
# test_matsu_school_trace.py
#
# T020 / US5 -- Programmatic Principle VII trace assertions for the
# Matsu Bushi School.  Verifies each Matsu-specific effect renders with
# its required source-attributed sentinel substring in both the
# TextRenderer and BulletedRenderer output.
#
# Pattern follows ``tests/test_hida_school_trace.py``: each effect is
# tested via a synthetic ``TraceEntry`` constructed directly (not via
# a full combat run), then rendered in BOTH renderers.  Cross-renderer
# coverage per Constitution Principle VII.
#
# rules/04-schools.md "Matsu Bushi School" + Constitution Principle VII
# (combat trace self-explanation).
#

import unittest

from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.text_renderer import TextRenderer
from web.adapters.trace_entries import (
    AttackEntry,
    DamageProjection,
    GainFloatingBonusEntry,
    MatsuLwFloorEntry,
    SpendFloatingBonusEntry,
)


class TestMatsu3rdDanGainTraceAttribution(unittest.TestCase):
    """3rd Dan floating-bonus gain must surface ``"Matsu 3rd Dan"`` +
    the ``"3 ×"`` breakdown sentinel + the numeric ``+12`` amount in
    BOTH renderers' output.

    rules/04-schools.md "Matsu Bushi School: Third Dan" + FR-013.
    """

    def _make_entry(self) -> GainFloatingBonusEntry:
        # 3rd Dan emits ``breakdown=f"3 × attack {attack_skill}"`` (see
        # ``MatsuSpendVoidPointsListener``); attack=4 -> bonus=12.
        return GainFloatingBonusEntry(
            phase_prefix="| R1 | P5 |",
            character_name="Matsu",
            amount=12,
            source="Matsu 3rd Dan",
            breakdown="3 × attack 4",
        )

    def test_text_renderer_includes_sentinel(self) -> None:
        rendered = "\n".join(TextRenderer().render_lines([self._make_entry()]))
        self.assertIn("Matsu 3rd Dan", rendered)
        # "3 ×" breakdown sentinel surfaces the rules-text formula.
        self.assertIn("3 ×", rendered)
        self.assertIn("+12", rendered)

    def test_bulleted_renderer_includes_sentinel(self) -> None:
        rendered = BulletedRenderer().render([self._make_entry()])
        self.assertIn("Matsu 3rd Dan", rendered)
        self.assertIn("3 ×", rendered)
        self.assertIn("+12", rendered)


class TestMatsu3rdDanConsumptionTraceAttribution(unittest.TestCase):
    """3rd Dan floating-bonus consumption (later in the combat) must
    surface the ``"Matsu 3rd Dan"`` source label so the playtester
    sees the same attribution on both the gain AND the consumption
    line.

    rules/04-schools.md "Matsu Bushi School: Third Dan" + FR-013.
    """

    def _make_entry(self) -> SpendFloatingBonusEntry:
        return SpendFloatingBonusEntry(
            phase_prefix="| R2 | P3 |",
            character_name="Matsu",
            amount=12,
            source="Matsu 3rd Dan",
        )

    def test_text_renderer_includes_sentinel(self) -> None:
        rendered = "\n".join(TextRenderer().render_lines([self._make_entry()]))
        self.assertIn("Matsu 3rd Dan", rendered)
        self.assertIn("+12", rendered)

    def test_bulleted_renderer_includes_sentinel(self) -> None:
        rendered = BulletedRenderer().render([self._make_entry()])
        self.assertIn("Matsu 3rd Dan", rendered)
        self.assertIn("+12", rendered)


class TestMatsu4thDanNearMissTraceAttribution(unittest.TestCase):
    """4th Dan near-miss must surface ``"Matsu 4th Dan"`` AND
    ``"counts as hit"`` (trace-reader #1 explicit-mechanics fix) AND
    ``"N below TN"`` in BOTH renderers' output when
    ``matsu_4th_dan_near_miss_below_tn`` is non-zero.

    rules/04-schools.md "Matsu Bushi School: Fourth Dan" + FR-021.
    """

    def _make_entry(self, *, below_tn: int) -> AttackEntry:
        # Base TN 20, double-attack TN 40, skill_roll 30 -> 10 below TN
        # (within the near-miss carve-out band).  The renderer reads
        # ``matsu_4th_dan_near_miss_below_tn`` directly; the other
        # fields are filler for a minimally-valid ``AttackEntry``.
        return AttackEntry(
            phase_prefix="| R1 | P5 |",
            actor_name="Matsu",
            target_name="target",
            skill="double attack",
            vp_spent=None,
            vp_skill=None,
            rolled=8,
            kept=5,
            modifier=0,
            components=[],
            modifier_components=[],
            dice=[10, 9, 7, 3, 1],
            sum_of_kept=30,
            total=30,
            tn=40,
            base_tn=20,
            outcome="hit",
            damage_projection=DamageProjection(
                rolled=5, kept=3, components=[],
                extra_damage_dice=0, margin_over_tn=0,
            ),
            matsu_4th_dan_near_miss_below_tn=below_tn,
        )

    def test_text_renderer_includes_sentinel(self) -> None:
        rendered = "\n".join(
            TextRenderer().render_lines([self._make_entry(below_tn=10)]),
        )
        self.assertIn("Matsu 4th Dan", rendered)
        self.assertIn("counts as hit", rendered)
        self.assertIn("10 below TN", rendered)

    def test_bulleted_renderer_includes_sentinel(self) -> None:
        rendered = BulletedRenderer().render(
            [self._make_entry(below_tn=10)],
        )
        self.assertIn("Matsu 4th Dan", rendered)
        self.assertIn("counts as hit", rendered)
        self.assertIn("10 below TN", rendered)

    def test_zero_below_tn_does_not_surface_sentinel(self) -> None:
        """Default 0 -> clean hit (or non-Matsu double attack); the 4th
        Dan attribution must NOT appear.  FR-021."""
        rendered_text = "\n".join(
            TextRenderer().render_lines([self._make_entry(below_tn=0)]),
        )
        rendered_bulleted = BulletedRenderer().render(
            [self._make_entry(below_tn=0)],
        )
        for blob in (rendered_text, rendered_bulleted):
            self.assertNotIn("Matsu 4th Dan", blob)
            self.assertNotIn("near-miss", blob)


class TestMatsu5thDanLwFloorTraceAttribution(unittest.TestCase):
    """5th Dan LW-floor must surface ``"Matsu 5th Dan"`` + the numeric
    ``15`` LW-floor sentinel + the ``"instead of 0"`` contrast clause
    in BOTH renderers' output.

    rules/04-schools.md "Matsu Bushi School: Fifth Dan" + FR-023.
    """

    def _make_entry(self) -> MatsuLwFloorEntry:
        return MatsuLwFloorEntry(
            phase_prefix="| R3 | P7 |",
            defender_name="defender",
            lw_set_to=15,
        )

    def test_text_renderer_includes_sentinel(self) -> None:
        rendered = "\n".join(TextRenderer().render_lines([self._make_entry()]))
        self.assertIn("Matsu 5th Dan", rendered)
        self.assertIn("15", rendered)
        self.assertIn("instead of 0", rendered)
        # Defender name must appear so a fresh reader knows whose LW
        # was floored.
        self.assertIn("defender", rendered)

    def test_bulleted_renderer_includes_sentinel(self) -> None:
        rendered = BulletedRenderer().render([self._make_entry()])
        self.assertIn("Matsu 5th Dan", rendered)
        self.assertIn("15", rendered)
        self.assertIn("instead of 0", rendered)
        self.assertIn("defender", rendered)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
