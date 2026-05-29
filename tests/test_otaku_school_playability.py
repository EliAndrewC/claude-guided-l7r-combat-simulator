#!/usr/bin/env python3

#
# test_otaku_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests for
# the Otaku Bushi School (spec 014 T-D1).
#
# Per Constitution Principle IX:
#   (a) A mirror match between two same-school defaults MUST terminate
#       within the safety bound.
#   (b) Across the mirror matches, the school's identity engine MUST
#       fire — at least one Otaku interrupt-lunge MUST fire per match.
#
# rules/04-schools.md "Otaku Bushi School: Special Ability" + Constitution
# Principle IX.
#

import random
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.exceptions import CombatEnded
from simulation.groups import Group


class _CappedCombatEngine(CombatEngine):
    """Bounded CombatEngine for mirror-match safety (OOM containment
    pattern introduced in Hida specs/010)."""

    MAX_ROUNDS = 18

    def run_round(self) -> None:
        if self.context().round() >= self.MAX_ROUNDS:
            raise CombatEnded(
                f"safety cap: hit {self.MAX_ROUNDS} rounds without termination",
            )
        super().run_round()


def _build_300xp_otaku() -> Character:
    """Build a 300-XP Otaku via the canonical template pipeline."""
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("otaku", 300)
    return config_to_character(config)


def _build_450xp_otaku() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("otaku", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestOtakuMirrorMatchPlayability(unittest.TestCase):
    """Spec 014 SC-002 — Principle IX 2(a) + 2(b) for the Otaku
    Bushi School. Five seeded mirror matches at 300 XP."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        otaku_a = _build_300xp_otaku()
        otaku_a._name = "OtakuA"
        otaku_b = _build_300xp_otaku()
        otaku_b._name = "OtakuB"
        groups = [Group("Unicorn-A", otaku_a), Group("Unicorn-B", otaku_b)]
        context = EngineContext(groups)
        context.initialize()
        engine = _CappedCombatEngine(context)
        try:
            engine.run()
        except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
            pass
        return engine, context, otaku_a, otaku_b

    def test_mirror_match_terminates_within_safety_bound(self) -> None:
        """(a) Each of 5 seeded mirror matches MUST terminate within
        the safety bound via ACTUAL defeat (not cap saturation)."""
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                _, context, otaku_a, otaku_b = self._run_mirror_match(seed)
                final_round = context.round()
                self.assertLess(
                    final_round, MIRROR_MATCH_SAFETY_BOUND_ROUNDS,
                    f"Seed {seed}: Otaku mirror took {final_round} rounds "
                    f"(cap: {MIRROR_MATCH_SAFETY_BOUND_ROUNDS}). "
                    f"Principle IX 2(a) requires termination within the "
                    f"safety bound.",
                )
                # Combat must have actually ended via defeat.
                self.assertFalse(
                    otaku_a.is_fighting() and otaku_b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Otakus still "
                    f"fighting. Principle IX 2(a) violation.",
                )


class TestOtakuIdentityEngineFires(unittest.TestCase):
    """Spec 014 — Principle IX 2(b) identity engine firing.

    Across seeded combats, the Otaku Special Ability interrupt-lunge
    MUST fire at least once — this was the Q1 IDENTITY BUG that
    combat-simulator empirically measured 0 firings across 23 combats
    before the strategy was wired.
    """

    def test_interrupt_lunge_fires_in_otaku_vs_akodo(self) -> None:
        """A 450-XP Otaku vs 450-XP Akodo combat MUST produce at least
        one interrupt-lunge across a 10-seed sweep. Before spec 014's
        T-B1+T-B2 fix, combat-simulator measured zero across 20 seeds.
        """
        from simulation.events import TakeAttackActionEvent
        any_interrupt_lunge = False
        for seed in range(1, 11):
            random.seed(seed)
            otaku = _build_450xp_otaku()
            otaku._name = "Otaku"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Unicorn", otaku), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, TakeAttackActionEvent):
                    ia = e.action.initiative_action()
                    if (
                        e.action.skill() == "lunge"
                        and e.action.subject() is otaku
                        and ia.is_interrupt()
                    ):
                        any_interrupt_lunge = True
                        break
            if any_interrupt_lunge:
                break
        self.assertTrue(
            any_interrupt_lunge,
            "Spec 014 SC-005: Otaku Special Ability interrupt-lunge "
            "MUST fire at least once across the 10-seed sweep. Before "
            "the Q1 fix, combat-simulator measured zero interrupt-"
            "lunges; this test guards against regression of the "
            "default-strategy installation.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
