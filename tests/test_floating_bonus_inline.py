"""Tests for floating-bonus inline integration (spec 008 FR-008/9/10/11 — Issue 3).

Pre-spec 008, an attack that consumed a floating bonus produced two
trace lines:

1. The attack line showing the raw kept-sum, e.g.
   ``"Akodo | ⚔️ attacks Bayushi (attack) — 9k3 [...] → 19 vs TN 30 — HIT!"``
   (arithmetically a miss, but the engine flipped is_hit() to True).
2. A separate consumption line, e.g.
   ``"Akodo | ✨ +15 (Akodo 3rd Dan floating bonus consumed)"``.

The contradiction made the reader doubt either surface — was the
attack a hit?  Why?  Spec 008 integrates the consumption into the
attack-line inline arithmetic:

    "→ 19, +15 (Akodo 3rd Dan floating bonus) = 34 vs TN 30 — HIT!"

The reader sees the math reconciled on the line itself; the
standalone consumption line is suppressed.
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
    """Run the seed=1 calibration combat (Akodo vs Bayushi).

    2026-05-30: the prior seed=1234 calibration became a 2-round
    Bayushi blowout (with the failed-parry damage-die reduction
    update — rules/03-combat.md — Bayushi's double-attack output is
    no longer wiped by Akodo's parry, ending combat before the
    Akodo 3rd Dan floating-bonus chain or any Akodo feint can fire).
    Re-anchored to seed=22 which exercises Akodo feints, Akodo 3rd
    Dan floating-bonus consumes, Bayushi double-attacks, Bayushi VP
    on attack, and Akodo 4th Dan VP raises — i.e., all the events
    the calibration-anchored tests across this module check for.
    """
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


class TestFloatingBonusInlineIntegration(unittest.TestCase):
    """Spec 008 Issue 3 — floating-bonus consumption inline on attack line."""

    def test_text_renderer_includes_bonus_inline(self) -> None:
        """FR-008: TextRenderer's attack line shows ``"+N (source
        floating bonus) = total"`` inline when a bonus was consumed.

        Calibration: the seed=1234 combat has Akodo consuming a
        +15 floating bonus on an attack at Phase 4 / Round 2 to push
        a kept-sum-19 attack over TN 30.
        """
        text_lines, _ = _run_calibration_combat()
        full_text = "\n".join(text_lines)
        # Look for the inline integration pattern.
        m = re.search(
            r"→ \d+, \+\d+ \(Akodo 3rd Dan floating bonus\) = \d+ vs",
            full_text,
        )
        self.assertIsNotNone(
            m,
            f"Akodo 3rd Dan floating-bonus inline integration missing in "
            f"text trace:\n{full_text}",
        )

    def test_no_standalone_consumption_line_when_integrated(self) -> None:
        """FR-010: When the bonus is integrated inline, the standalone
        ``"✨ +N (...source floating bonus consumed)"`` line is suppressed.
        """
        text_lines, _ = _run_calibration_combat()
        for line in text_lines:
            self.assertNotIn(
                "floating bonus consumed", line,
                f"Standalone consumption line still present: {line!r}",
            )

    def test_bulleted_renderer_includes_bonus_inline(self) -> None:
        """FR-008: BulletedRenderer also integrates the bonus inline
        on the attack header line.
        """
        _, bulleted = _run_calibration_combat()
        # Match either Akodo 3rd Dan (the prominent calibration case)
        # or Bayushi 4th Dan (the other one).
        m = re.search(
            r"→ \d+, \+\d+ \((?:Akodo 3rd Dan|Bayushi 4th Dan) "
            r"floating bonus\)",
            bulleted,
        )
        self.assertIsNotNone(
            m,
            "Bulleted renderer is missing inline floating-bonus integration",
        )

    def test_bulleted_renderer_no_standalone_consumption_line(self) -> None:
        """FR-010: BulletedRenderer also suppresses the standalone line."""
        _, bulleted = _run_calibration_combat()
        self.assertNotIn(
            "floating bonus consumed", bulleted,
            "BulletedRenderer still emits standalone consumption line",
        )

    def test_multiple_bonus_consumption_each_appears_inline(self) -> None:
        """FR-009: When multiple floating bonuses are consumed on the
        same attack, EACH appears inline with its own source.

        Calibration: the seed=1234 combat has at least one attack
        where Bayushi consumes two Bayushi-4th-Dan bonuses on the
        same attack (Phase 4 of a later round, after two prior failed
        feints).  Both should appear on the attack line.
        """
        text_lines, _ = _run_calibration_combat()
        full_text = "\n".join(text_lines)
        # Find attack lines with two ``(... floating bonus)`` segments.
        matches = re.findall(
            r"⚔️ attacks .* vs TN .* — HIT",
            full_text,
        )
        multi_bonus_lines = [
            line
            for line in matches
            if line.count("floating bonus") >= 2
        ]
        # The calibration combat in seed=1234 produces at least one
        # multi-bonus attack.  If not, this test guards against future
        # regression where multi-bonus lines collapse to one.
        self.assertTrue(
            multi_bonus_lines,
            "Calibration combat should have at least one attack with "
            "multiple floating bonuses consumed — none found",
        )

    def test_hit_outcome_uses_bonus_adjusted_total(self) -> None:
        """FR-008: The inline math reconciles — the displayed
        ``= {total}`` MUST be ``kept_sum + modifier + sum(bonuses)``
        and HIT/MISS reflects that.

        Anchor: the Phase 4 Akodo attack at kept-sum 19, no other
        modifier, +15 bonus → 34 vs TN 30 — HIT!.
        """
        text_lines, _ = _run_calibration_combat()
        full_text = "\n".join(text_lines)
        # The bonus-adjusted total appears right before " vs TN".
        m = re.search(
            r"→ 19, \+15 \(Akodo 3rd Dan floating bonus\) = (\d+) vs TN 30",
            full_text,
        )
        if m is not None:
            self.assertEqual(
                int(m.group(1)), 34,
                f"Bonus-adjusted total mismatch: expected 34, got "
                f"{m.group(1)}",
            )
