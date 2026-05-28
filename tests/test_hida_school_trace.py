#!/usr/bin/env python3

#
# test_hida_school_trace.py
#
# T034 / US5 — Programmatic Principle VII trace assertions for the
# Hida Bushi School.  Verifies each Hida-specific effect renders with
# its required source-attributed sentinel substring in both the
# TextRenderer and BulletedRenderer output.
#
# rules/04-schools.md "Hida Bushi School" + Constitution Principle VII
# (combat trace self-explanation).
#

import unittest

from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.text_renderer import TextRenderer
from web.adapters.trace_entries import (
    HidaSWForLWTradeEntry,
    HidaThirdDanRerollEntry,
)


class TestHidaThirdDanRerollTraceAttribution(unittest.TestCase):
    """3rd Dan reroll must surface ``"Hida 3rd Dan: reroll"`` AND the
    before→after die pairs AND the before→after totals in BOTH
    renderers' output."""

    def _make_entry(self) -> HidaThirdDanRerollEntry:
        return HidaThirdDanRerollEntry(
            phase_prefix="| R1 | P5 |",
            actor_name="Hida",
            skill="attack",
            n=2,
            crippled=False,
            rerolls=[(2, 7), (1, 6)],
            before_total=10,
            after_total=23,
        )

    def test_text_renderer_includes_sentinel(self) -> None:
        rendered = "\n".join(TextRenderer().render_lines([self._make_entry()]))
        self.assertIn("Hida 3rd Dan: reroll", rendered)
        self.assertIn("2→7", rendered)
        self.assertIn("1→6", rendered)
        self.assertIn("10", rendered)  # before_total
        self.assertIn("23", rendered)  # after_total

    def test_bulleted_renderer_includes_sentinel(self) -> None:
        rendered = BulletedRenderer().render([self._make_entry()])
        self.assertIn("Hida 3rd Dan: reroll", rendered)
        self.assertIn("2→7", rendered)
        self.assertIn("1→6", rendered)

    def test_renders_kept_sum_label_not_total(self) -> None:
        """trace-reader #1 fix: the pair after "N=" must be labeled
        "kept-sum", not "total".  Post-roll modifiers (e.g., Hida 2nd
        Dan +5 free raise on counterattack) are not reflected in this
        sub-line; calling it "total" misleads readers into comparing
        against the parent ``Roll: N`` header and seeing a phantom
        mismatch.
        """
        rendered_text = "\n".join(
            TextRenderer().render_lines([self._make_entry()]),
        )
        rendered_bulleted = BulletedRenderer().render([self._make_entry()])
        for blob in (rendered_text, rendered_bulleted):
            self.assertIn("kept-sum 10→23", blob)
            self.assertNotIn("total 10→23", blob)

    def test_text_renderer_marks_impaired_when_crippled(self) -> None:
        """Per Principle VII, the crippled state must be surfaced — the
        rules-text carve-out (halved N + still-reroll-10s) is observable
        to a fresh reader only if the trace marks the crippled state."""
        entry = HidaThirdDanRerollEntry(
            phase_prefix="| R1 | P5 |",
            actor_name="Hida",
            skill="counterattack",
            n=2,
            crippled=True,
            rerolls=[(3, 10)],
            before_total=15,
            after_total=22,
        )
        rendered = "\n".join(TextRenderer().render_lines([entry]))
        self.assertIn("Hida 3rd Dan", rendered)
        self.assertIn("impaired", rendered)


class TestHidaFourthDanSWForLWTradeTraceAttribution(unittest.TestCase):
    """4th Dan SW-for-LW trade must surface ``"Hida 4th Dan"`` AND the
    "take 2 SW" cost AND the "reset LW from N → 0" effect in BOTH
    renderers' output."""

    def _make_entry(self) -> HidaSWForLWTradeEntry:
        return HidaSWForLWTradeEntry(
            phase_prefix="| R2 | P3 |",
            character_name="Hida",
            lw_reset_from=18,
            sw_taken=2,
        )

    def test_text_renderer_includes_sentinel(self) -> None:
        rendered = "\n".join(TextRenderer().render_lines([self._make_entry()]))
        self.assertIn("Hida 4th Dan", rendered)
        self.assertIn("take 2 SW", rendered)
        self.assertIn("18", rendered)
        self.assertIn("0", rendered)

    def test_bulleted_renderer_includes_sentinel(self) -> None:
        rendered = BulletedRenderer().render([self._make_entry()])
        self.assertIn("Hida 4th Dan", rendered)
        self.assertIn("take 2 SW", rendered)
        self.assertIn("18", rendered)


class TestHidaFifthDanWoundCheckExcessTraceAttribution(unittest.TestCase):
    """5th Dan WC bonus must surface ``"Hida 5th Dan: counterattack
    excess"`` on the wound-check line when ``hida_5th_dan_excess_bonus``
    is non-zero."""

    def _make_entry(self, *, excess_bonus: int):
        # Use a minimal WoundCheckEntry with the bonus field set.
        from web.adapters.trace_entries import WoundCheckEntry
        return WoundCheckEntry(
            phase_prefix="| R1 | P5 |",
            character_name="Hida",
            vp_spent=None,
            vp_source=None,
            vp_skill=None,
            vp_breakdown=None,
            rolled=6,
            kept=5,
            modifier=0,
            components=[],
            modifier_components=[],
            dice=[10, 8, 7, 6, 5, 4],
            sum_of_kept=36,
            total=36 + excess_bonus,
            tn=30,
            outcome="passed",
            hida_5th_dan_excess_bonus=excess_bonus,
        )

    def test_text_renderer_surfaces_excess_bonus(self) -> None:
        rendered = "\n".join(TextRenderer().render_lines(
            [self._make_entry(excess_bonus=7)],
        ))
        self.assertIn("Hida 5th Dan: counterattack excess", rendered)
        self.assertIn("+7", rendered)

    def test_bulleted_renderer_surfaces_excess_bonus(self) -> None:
        rendered = BulletedRenderer().render(
            [self._make_entry(excess_bonus=7)],
        )
        self.assertIn("Hida 5th Dan: counterattack excess", rendered)
        self.assertIn("+7", rendered)

    def test_zero_bonus_does_not_surface_sentinel(self) -> None:
        """Default 0 bonus → no 5th Dan attribution should appear (the
        WC didn't actually receive a Hida 5th Dan bonus)."""
        rendered = "\n".join(TextRenderer().render_lines(
            [self._make_entry(excess_bonus=0)],
        ))
        self.assertNotIn("Hida 5th Dan", rendered)


class TestHidaSpecialAbilityFreeRaiseTraceAttribution(unittest.TestCase):
    """The +5 free raise from the Hida Special Ability must surface
    on the attacker's attack-roll modifier breakdown with the
    explicit ``"Hida special ability free raise"`` source label per
    Constitution Principle VII.

    The contribution is computed by ``modifier_breakdown.py`` reading
    the ``_counterattack_roll_bonus`` attribute that
    ``HidaTakeCounterattackActionEvent.play`` sets on the original
    attack action.
    """

    def test_modifier_breakdown_attributes_free_raise(self) -> None:
        from unittest.mock import MagicMock

        from web.adapters.modifier_breakdown import explain_modifier
        # Attacker (non-Hida — the Hida being attacked tagged the
        # action with the free-raise bonus).
        attacker = MagicMock()
        attacker.school_rank.return_value = 0
        attacker.school.return_value = None
        # Attack action carries the +5 bonus that the Hida set when
        # interrupt-counterattacking.
        action = MagicMock()
        action.subject.return_value = attacker
        action.skill.return_value = "attack"
        action._counterattack_roll_bonus = 5
        contributions = explain_modifier(
            attacker, "attack", modifier=5, vp=0, action=action,
        )
        labels = [c[0] for c in contributions]
        self.assertIn(
            "Hida special ability free raise", labels,
            f"+5 free raise from the Hida special ability must surface "
            f"with explicit source label in the modifier breakdown per "
            f"Principle VII; got labels: {labels}.",
        )
        # Verify the value is +5.
        hida_contributions = [
            v for label, v in contributions
            if label == "Hida special ability free raise"
        ]
        self.assertEqual([5], hida_contributions)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
