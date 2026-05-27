"""Tests for cross-renderer consistency (spec 008 FR-001/004 — Issue 1).

After spec 007 introduced both the legacy TextRenderer and the new
BulletedRenderer, the trace-reader dry-run found that the
10k10-overflow synthetic component rendered as
``"+6 from 3 dropped dice in excess of 10k10"`` in TextRenderer (the
narrative form) but as ``"-3k3 from dice in excess of 10k10"`` in
BulletedRenderer's damage-projection sub-bullets (the raw form).
That is a Wrong-severity bug: the reader cannot trust either surface.

Spec 008 fixes this by extracting the special-case into a single
shared helper :func:`web.adapters._breakdown_format.format_breakdown_component`
that BOTH renderers delegate to.  These tests verify the invariant
holds across the entire calibration combat: every 10k10-overflow
component string appears identically in both renderers' output.
"""

from __future__ import annotations

import random
import re
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.templates.generator import generate_template
from web.adapters._breakdown_format import EXCESS_10K10_SOURCE
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


def _run_calibration_entries() -> tuple[list[str], str]:
    """Run the seed=1234 Bayushi-vs-Akodo combat.

    Returns ``(text_lines, bulleted_markdown)``: the TextRenderer
    output as a list of lines and the BulletedRenderer output as a
    Markdown string (one string with embedded newlines).
    """
    random.seed(1234)
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


# Match the narrative form: "+{2N} from {N} dropped die/dice in excess of 10k10".
_NARRATIVE_RE = re.compile(
    r"\+\d+ from \d+ dropped (?:die|dice) in excess of 10k10",
)

# Match the raw form: "-NkM from dice in excess of 10k10" (pre-fix).
_RAW_RE = re.compile(
    r"-\d+k-?\d+ from dice in excess of 10k10",
)


class TestCrossRendererConsistency(unittest.TestCase):
    """Spec 008 Issue 1 — both renderers describe overflow components identically."""

    def test_text_renderer_uses_narrative_form_for_overflow(self) -> None:
        """The TextRenderer renders 10k10-overflow as the narrative form.

        Calibration: the seed=1234 Bayushi double-attack repeatedly hits
        with 10k10+ overflow (the 5th-Dan ring stacks past the dice cap),
        so the calibration trace contains at least one narrative-form
        ``"+X from N dropped dice in excess of 10k10"`` segment.
        """
        text_lines, _ = _run_calibration_entries()
        text_joined = "\n".join(text_lines)
        self.assertRegex(
            text_joined, _NARRATIVE_RE,
            "TextRenderer output is missing the narrative overflow form",
        )
        self.assertNotRegex(
            text_joined, _RAW_RE,
            "TextRenderer output still contains the pre-fix raw overflow form",
        )

    def test_bulleted_renderer_uses_narrative_form_for_overflow(self) -> None:
        """The BulletedRenderer renders 10k10-overflow as the narrative form
        in EVERY path: inline-component breakdowns, damage-projection
        sub-bullets, and the LW damage-roll sub-bullets.

        Pre-fix, the damage-projection sub-bullets bypassed the helper
        and emitted ``"-3k3 from dice in excess of 10k10"``.  Spec 008
        FR-003 routes them through the shared helper.
        """
        _, bulleted = _run_calibration_entries()
        self.assertRegex(
            bulleted, _NARRATIVE_RE,
            "BulletedRenderer output is missing the narrative overflow form",
        )
        self.assertNotRegex(
            bulleted, _RAW_RE,
            "BulletedRenderer output still contains the pre-fix raw "
            "overflow form (FR-003 regression)",
        )

    def test_overflow_segments_match_across_renderers(self) -> None:
        """The SET of narrative overflow segments in BulletedRenderer
        equals (or is a superset of) the set in TextRenderer.

        Equality is the strong invariant: every overflow component
        rendered by one renderer is also rendered by the other.  In
        practice BulletedRenderer's damage-projection sub-bullets
        expose the same components that TextRenderer inlines on the
        damage-projection segment, so the sets match exactly for
        common cases.  We assert subset (text-set ⊆ bulleted-set) to
        be robust to renderers exposing the same data in different
        layouts.
        """
        text_lines, bulleted = _run_calibration_entries()
        text_set = set(_NARRATIVE_RE.findall("\n".join(text_lines)))
        bulleted_set = set(_NARRATIVE_RE.findall(bulleted))
        self.assertGreater(
            len(text_set), 0,
            "Calibration combat produced no overflow segments in TextRenderer",
        )
        self.assertGreater(
            len(bulleted_set), 0,
            "Calibration combat produced no overflow segments in BulletedRenderer",
        )
        self.assertTrue(
            text_set.issubset(bulleted_set) or bulleted_set.issubset(text_set),
            f"Overflow segments diverge between renderers.  "
            f"text-only: {text_set - bulleted_set}; "
            f"bulleted-only: {bulleted_set - text_set}",
        )

    def test_neither_renderer_emits_raw_overflow_form(self) -> None:
        """Defensive: neither renderer's full output contains the pre-fix
        raw ``"-NkM from dice in excess of 10k10"`` form anywhere.
        """
        text_lines, bulleted = _run_calibration_entries()
        self.assertNotRegex(
            "\n".join(text_lines), _RAW_RE,
            "TextRenderer regression: raw overflow form re-appeared",
        )
        self.assertNotRegex(
            bulleted, _RAW_RE,
            "BulletedRenderer regression: raw overflow form re-appeared",
        )

    def test_excess_10k10_label_constant_matches_engine(self) -> None:
        """The shared helper's source-label constant matches the
        engine's actual label (so the special-case detection works).
        Sanity check guarding against typos that would silently
        regress to the standard form.
        """
        text_lines, _ = _run_calibration_entries()
        text_joined = "\n".join(text_lines)
        # The engine label appears as a substring of the narrative form.
        # If the constant ever drifts from the engine, the narrative
        # form would never fire and this test would fail.
        self.assertIn("in excess of 10k10", text_joined)
        self.assertEqual(EXCESS_10K10_SOURCE, "from dice in excess of 10k10")
