"""Tests for the absence of the ``"unsourced"`` literal (spec 008 FR-012/13/14 — Issue 5).

The trace-reader dry-run flagged the literal token ``"unsourced"`` in
user-visible modifier breakdowns as a Principle VII compliance marker
that read as a bug message.  Spec 005 FR-014 intentionally surfaced
unattributed modifier remainders, but the wording was alarming for
users.  Spec 008:

1. Identifies the specific ``+5 (unsourced)`` from the calibration
   trace as the Akodo 4th Dan VP-for-raise modifier and adds the
   case to ``explain_modifier`` so the trace shows
   ``"Akodo 4th Dan VP raises: +5"`` instead.
2. Replaces the bare ``"unsourced: +K"`` fallback with
   ``"see preceding line"`` for any genuinely-unattributable case.
3. ``grep -E "\bunsourced\b"`` on a calibration trace returns zero
   matches in both renderers.
"""

from __future__ import annotations

import random
import re
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.templates.generator import generate_template
from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.character_adapter import config_to_character
from web.adapters.combat_observer import (
    CombatObserver,
    DetailedCombatEngine,
    TrackingRollProvider,
)
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.adapters.text_renderer import TextRenderer


def _build_character(school_key: str, name: str) -> Character:
    """Build a 300-XP character from a school template and rename it."""
    config, _ = generate_template(school_key, 300)
    char = config_to_character(config)
    char._name = name
    char.set_roll_provider(TrackingRollProvider(char.roll_provider()))
    return char


def _run_calibration_combat() -> tuple[list[str], str]:
    """Run the seed=22 calibration combat (re-anchored 2026-05-30
    after the rules/03-combat.md failed-parry-reduction update made
    the seed=1234 combat too short to exercise Akodo 4th Dan VP
    raises)."""
    random.seed(75)
    bayushi = _build_character("bayushi", "Bayushi")
    akodo = _build_character("akodo", "Akodo")
    ctx = EngineContext([Group("Scorpion", bayushi), Group("Lion", akodo)])
    ctx.initialize()
    observer = CombatObserver()
    engine = DetailedCombatEngine(ctx, observer)
    engine.run()
    entries = DetailedEventFormatter().entries(engine.history())
    text_lines = TextRenderer().render_lines(entries)
    bulleted = BulletedRenderer().render(entries)
    return text_lines, bulleted


_UNSOURCED_RE = re.compile(r"\bunsourced\b")


class TestUnsourcedLiteralAbsence(unittest.TestCase):
    """Spec 008 Issue 5 — ``unsourced`` literal absent from user-facing traces."""

    def test_text_renderer_calibration_trace_has_no_unsourced(self) -> None:
        """FR-012: ``grep -E "\\bunsourced\\b"`` returns zero matches
        on TextRenderer output of the calibration combat.
        """
        text_lines, _ = _run_calibration_combat()
        text_joined = "\n".join(text_lines)
        matches = _UNSOURCED_RE.findall(text_joined)
        self.assertEqual(
            matches, [],
            f"TextRenderer trace still contains 'unsourced' literal: "
            f"matches={matches}",
        )

    def test_bulleted_renderer_calibration_trace_has_no_unsourced(self) -> None:
        """FR-012: ``grep -E "\\bunsourced\\b"`` returns zero matches
        on BulletedRenderer output of the calibration combat.
        """
        _, bulleted = _run_calibration_combat()
        matches = _UNSOURCED_RE.findall(bulleted)
        self.assertEqual(
            matches, [],
            f"BulletedRenderer trace still contains 'unsourced' literal: "
            f"matches={matches}",
        )

    def test_akodo_4th_dan_vp_modifier_has_real_attribution(self) -> None:
        """FR-013: The specific ``+5 (unsourced)`` flagged by the dry-run
        is now attributed to ``"Akodo 4th Dan VP raises"``.

        Calibration anchor: Phase 6 Round 1, Akodo's first wound check
        where she spends 1 VP via the Akodo 4th Dan strategy.  The
        modifier breakdown shows BOTH the 2nd Dan free raise AND the
        4th Dan VP-for-raise contribution.
        """
        text_lines, _ = _run_calibration_combat()
        text_joined = "\n".join(text_lines)
        self.assertIn(
            "Akodo 4th Dan VP raises:", text_joined,
            "Akodo 4th Dan VP-for-raise modifier attribution missing",
        )

    def test_fallback_omits_unattributable_remainder(self) -> None:
        """Updated 2026-05-30 per trace-reader sweep findings: the
        ``(see preceding line)`` fallback is no longer rendered — the
        sweep found it was the single most-flagged UX defect (a
        dangling pointer that almost never pointed at the actual
        source). When a modifier's breakdown is partial, only the
        attributed components render as their own segments; the
        unattributed remainder is omitted.

        The remainder value itself remains visible at the parent
        header level (e.g., the attack/WC line shows the modifier in
        its arithmetic), so Principle VII's "every value visible"
        guarantee is preserved at the line level even though the
        per-bullet attribution is incomplete.
        """
        from web.adapters.bulleted_renderer import (
            _modifier_bullets as bulleted_fmt,
        )
        from web.adapters.text_renderer import (
            _format_modifier_breakdown as text_fmt,
        )
        from web.adapters.trace_entries import ModifierDelta

        text_out = text_fmt(7, [ModifierDelta(source="Some Source", amount=5)])
        self.assertNotIn("unsourced", text_out)
        self.assertNotIn("see preceding line", text_out)
        self.assertIn("Some Source: +5", text_out)

        bullets = bulleted_fmt(
            7, [ModifierDelta(source="Some Source", amount=5)],
        )
        joined = "\n".join(bullets)
        self.assertNotIn("unsourced", joined)
        self.assertNotIn("see preceding line", joined)
        self.assertIn("Some Source", joined)
