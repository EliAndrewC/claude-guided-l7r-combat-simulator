#!/usr/bin/env python3

#
# test_shiba_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests for
# the Shiba Bushi School (spec 016 T-D1).
#
# Per Constitution Principle IX:
#   (a) A mirror match between two same-school defaults MUST terminate.
#   (b) The school's identity engine MUST fire — at least one Shiba
#       interrupt-parry MUST fire per match.
#

import random
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.exceptions import CombatEnded
from simulation.groups import Group


class _CappedCombatEngine(CombatEngine):
    """Bounded engine for mirror-match safety (OOM containment
    pattern; see specs/010-hida-bushi-school)."""

    MAX_ROUNDS = 18

    def run_round(self) -> None:
        if self.context().round() >= self.MAX_ROUNDS:
            raise CombatEnded(
                f"safety cap: hit {self.MAX_ROUNDS} rounds without termination",
            )
        super().run_round()


def _build_300xp_shiba() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("shiba", 300)
    return config_to_character(config)


def _build_450xp_shiba() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("shiba", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestShibaMirrorMatchPlayability(unittest.TestCase):
    """Spec 016 SC-002 — Principle IX 2(a) for the Shiba Bushi School.
    Five seeded mirror matches at 300 XP."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        shiba_a = _build_300xp_shiba()
        shiba_a._name = "ShibaA"
        shiba_b = _build_300xp_shiba()
        shiba_b._name = "ShibaB"
        groups = [Group("Phoenix-A", shiba_a), Group("Phoenix-B", shiba_b)]
        context = EngineContext(groups)
        context.initialize()
        engine = _CappedCombatEngine(context)
        try:
            engine.run()
        except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
            pass
        return engine, context, shiba_a, shiba_b

    def test_mirror_match_terminates_within_safety_bound(self) -> None:
        """(a) Each mirror match MUST terminate within the safety
        bound via actual defeat (not cap saturation)."""
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                _, context, shiba_a, shiba_b = self._run_mirror_match(seed)
                final_round = context.round()
                self.assertLess(
                    final_round, MIRROR_MATCH_SAFETY_BOUND_ROUNDS,
                    f"Seed {seed}: Shiba mirror took {final_round} rounds "
                    f"(cap: {MIRROR_MATCH_SAFETY_BOUND_ROUNDS}).",
                )
                self.assertFalse(
                    shiba_a.is_fighting() and shiba_b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Shibas still "
                    f"fighting — Principle IX 2(a) violation.",
                )


class TestShibaIdentityEngineFires(unittest.TestCase):
    """Spec 016 — Principle IX 2(b) identity engine firing. The
    Shiba Special Ability interrupt-parry MUST fire at least once
    across a seed sweep."""

    def test_interrupt_parry_fires_in_shiba_vs_akodo(self) -> None:
        """A 450-XP Shiba vs 450-XP Akodo combat MUST produce at least
        one interrupt-parry across a 10-seed sweep.
        """
        from simulation.events import TakeParryActionEvent
        any_interrupt_parry = False
        for seed in range(1, 11):
            random.seed(seed)
            shiba = _build_450xp_shiba()
            shiba._name = "Shiba"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Phoenix", shiba), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, TakeParryActionEvent):
                    ia = e.action.initiative_action()
                    if (
                        e.action.subject() is shiba
                        and ia.is_interrupt()
                    ):
                        any_interrupt_parry = True
                        break
            if any_interrupt_parry:
                break
        self.assertTrue(
            any_interrupt_parry,
            "Spec 016 SC-005: Shiba Special Ability interrupt-parry "
            "MUST fire at least once across the 10-seed sweep.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
