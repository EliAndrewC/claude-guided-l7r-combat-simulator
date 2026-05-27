"""Tests for feint damage suppression (spec 008 FR-005/6/7 — Issues 2/4/6).

The trace-reader dry-run found that feint attacks produced multiple
contradictory trace lines:

1. The attack line projects ``"damage will be: 9k2"`` even though
   feints always deal 0 LW.
2. A ``💥 Damage:`` line follows the attack showing the rolled damage
   (e.g. 10k2 → 17) and then says ``"takes 0 light wounds"``.
3. The BulletedRenderer additionally produced a bulleted damage
   breakdown for the same 0-LW event.

All three are noise: the engine correctly rolls 0 LW, but the
formatter exposes the redundant computation.  Spec 008 suppresses
the entire damage rendering for feint actions: no projection on the
attack line, no separate damage line, no breakdown.  The reader sees
the feint attack succeed + the school-ability event (Akodo TVP gain,
Bayushi floating bonus) and combat moves on.
"""

from __future__ import annotations

import random
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
    """Run the seed=1234 calibration combat.

    Returns ``(text_lines, bulleted_markdown)``: TextRenderer output as
    a list of lines and BulletedRenderer output as a Markdown string.
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


class TestFeintDamageSuppression(unittest.TestCase):
    """Spec 008 Issues 2/4/6 — feint outcomes render coherently."""

    def test_feint_attack_lines_have_no_damage_projection_in_text(self) -> None:
        """FR-005: TextRenderer's feint attack line MUST NOT contain a
        ``"damage will be"`` segment when the action is a standard
        zero-damage feint (``FeintAction.damage_roll_params == (0,0,0)``).

        Calibration: the Akodo school uses standard ``FeintAction`` so
        ALL Akodo feint lines should have no projection.  Bayushi's
        ``BayushiFeintAction`` overrides damage to non-zero so those
        feints DO show a projection — covered by
        :meth:`test_bayushi_feint_keeps_projection`.
        """
        text_lines, _ = _run_calibration_combat()
        akodo_feint_lines = [
            line for line in text_lines
            if "(feint)" in line and "Akodo |" in line
        ]
        self.assertTrue(
            akodo_feint_lines,
            "Calibration combat produced no Akodo feint attack lines",
        )
        for line in akodo_feint_lines:
            self.assertNotIn(
                "damage will be", line,
                f"Akodo feint attack line still has damage projection: {line!r}",
            )

    def test_akodo_feint_attack_no_damage_projection_in_bulleted(self) -> None:
        """FR-005: BulletedRenderer's Akodo feint attack must not emit
        a ``Damage will be:`` sub-bullet.  Bayushi's special feint is
        handled separately by ``test_bayushi_feint_keeps_projection``.
        """
        _, bulleted = _run_calibration_combat()
        # Walk each Akodo feint header and check the following sub-bullets.
        lines = bulleted.split("\n")
        feint_blocks: list[list[str]] = []
        for i, line in enumerate(lines):
            if (
                "(feint)" in line
                and "⚔️ attacks" in line
                and "Akodo |" in line
            ):
                # Capture sub-bullets (indented lines following the header).
                block = [line]
                j = i + 1
                while j < len(lines) and lines[j].startswith(" "):
                    block.append(lines[j])
                    j += 1
                feint_blocks.append(block)
        self.assertTrue(
            feint_blocks,
            "Calibration combat produced no bulleted Akodo feint blocks",
        )
        for block in feint_blocks:
            block_text = "\n".join(block)
            self.assertNotIn(
                "Damage will be", block_text,
                f"Akodo feint block still has damage projection bullets: "
                f"{block_text!r}",
            )

    def test_no_damage_line_follows_akodo_feint_attack(self) -> None:
        """FR-006: No ``💥 Damage:`` line follows an Akodo feint
        attack (standard zero-damage ``FeintAction``).

        Pre-fix, every Akodo feint attack was followed by a damage
        line showing ``Akodo | 💥 Damage: 10k2 ... → Bayushi takes 0
        light wounds``.  Post-fix, the LW damage event is silently
        absorbed.

        Bayushi's special feint deals real damage and IS expected to
        produce a damage line (see :meth:`test_bayushi_feint_keeps_projection`).
        """
        text_lines, _ = _run_calibration_combat()
        for i, line in enumerate(text_lines):
            if "(feint)" not in line or "Akodo |" not in line:
                continue
            # Scan the next 3 lines — pre-fix the damage line was
            # immediately or one event after the feint.
            for j in range(i + 1, min(i + 4, len(text_lines))):
                self.assertNotIn(
                    "💥 Damage:", text_lines[j],
                    f"Damage line {text_lines[j]!r} follows Akodo feint line "
                    f"{line!r}",
                )

    def test_no_zero_lw_damage_line_anywhere_in_calibration(self) -> None:
        """FR-006: Globally, no ``takes 0 light wounds`` line appears
        in the calibration trace (the only source of 0-LW lines was
        Akodo feint damage; suppressing those eliminates them).

        Bayushi's special feint deals real (non-zero) damage so it
        never produced a 0-LW line in the first place.

        If a non-feint 0-LW damage line ever appears in the future
        (e.g. a defensive ability reducing damage to 0), this test
        becomes a yellow flag — the feint-suppression rule may need
        to widen or to be replaced by a more specific predicate.
        """
        text_lines, bulleted = _run_calibration_combat()
        full_text = "\n".join(text_lines) + "\n" + bulleted
        self.assertNotIn(
            "takes 0 light wounds", full_text,
            "0-LW damage line still appears (feint suppression incomplete)",
        )

    def test_bayushi_feint_keeps_projection_and_damage(self) -> None:
        """Edge case (spec.md Edge Cases): when a feint DOES deal
        damage (Bayushi's ``BayushiFeintAction`` overrides
        ``damage_roll_params``), the projection AND the damage line
        must still appear.  Spec 008's suppression predicate is
        scoped to ``feint AND damage_roll_params == (0, 0, 0)``;
        Bayushi feints don't match and render normally.
        """
        text_lines, _ = _run_calibration_combat()
        bayushi_feint_lines = [
            line for line in text_lines
            if "(feint)" in line and "Bayushi |" in line
        ]
        self.assertTrue(
            bayushi_feint_lines,
            "Calibration combat produced no Bayushi feint attack lines",
        )
        # At least one Bayushi feint should HIT (and thus carry a
        # damage projection) — the seed=1234 combat has several.
        bayushi_hit_feints = [
            line for line in bayushi_feint_lines if "HIT!" in line
        ]
        self.assertTrue(
            bayushi_hit_feints,
            "Calibration combat produced no Bayushi feint HITs",
        )
        any_with_projection = any(
            "damage will be" in line for line in bayushi_hit_feints
        )
        self.assertTrue(
            any_with_projection,
            "Bayushi feint HITs should still show 'damage will be' "
            "projection (their special feint deals real damage)",
        )

    def test_school_ability_events_still_appear_after_feints(self) -> None:
        """FR-007: Feint suppression MUST NOT also suppress the
        school-ability events that fire on feints:
        - Akodo: ``"+4 TVP on successful feint"`` / ``"+1 TVP on failed
          feint"`` (TVP gain).
        - Bayushi: ``"floating bonus +5 (successful feint)"`` / similar.

        The reader needs to see the consequence of the feint even
        when the damage line is gone.
        """
        text_lines, _ = _run_calibration_combat()
        full_text = "\n".join(text_lines)
        # Akodo gets +4 TVP on a successful feint somewhere in the combat.
        self.assertIn(
            "Akodo Special Ability:", full_text,
            "Akodo TVP gain (feint consequence) is missing from trace",
        )
        self.assertIn(
            "successful feint", full_text,
            "'successful feint' annotation missing from trace",
        )
        # Bayushi gets a floating bonus on a feint (success OR fail).
        self.assertIn(
            "Bayushi 4th Dan: gained floating bonus", full_text,
            "Bayushi floating-bonus gain (feint consequence) is missing",
        )

    def test_non_feint_attacks_still_show_damage_projection(self) -> None:
        """Regression guard: feint suppression MUST be feint-scoped.
        Non-feint attacks (regular ``(attack)``, ``(double attack)``)
        still render their ``damage will be`` projection.
        """
        text_lines, _ = _run_calibration_combat()
        non_feint_hit_lines = [
            line for line in text_lines
            if "⚔️ attacks" in line
            and "— HIT!" in line
            and "(feint)" not in line
        ]
        self.assertTrue(
            non_feint_hit_lines,
            "Calibration combat produced no non-feint HIT attacks",
        )
        # At least one of these lines should still show a damage
        # projection (proves the suppression didn't over-fire).
        any_projection = any(
            "damage will be" in line for line in non_feint_hit_lines
        )
        self.assertTrue(
            any_projection,
            "Non-feint attack lines lost their damage projection — "
            "feint suppression is too aggressive",
        )
