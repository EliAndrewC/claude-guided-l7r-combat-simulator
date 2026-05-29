#!/usr/bin/env python3

#
# test_hiruma_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests
# for the Hiruma Scout School (spec 019).
#

import random
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.exceptions import CombatEnded
from simulation.groups import Group


class _CappedCombatEngine(CombatEngine):
    MAX_ROUNDS = 18

    def run_round(self) -> None:
        if self.context().round() >= self.MAX_ROUNDS:
            raise CombatEnded(
                f"safety cap: hit {self.MAX_ROUNDS} rounds without termination",
            )
        super().run_round()


def _build_300xp_hiruma() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("hiruma", 300)
    return config_to_character(config)


def _build_450xp_hiruma() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("hiruma", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestHirumaMirrorMatchPlayability(unittest.TestCase):
    """Spec 019 SC-002 — Principle IX 2(a) mirror at 300 XP."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        a = _build_300xp_hiruma()
        a._name = "HirumaA"
        b = _build_300xp_hiruma()
        b._name = "HirumaB"
        groups = [Group("Crab-A", a), Group("Crab-B", b)]
        context = EngineContext(groups)
        context.initialize()
        engine = _CappedCombatEngine(context)
        try:
            engine.run()
        except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
            pass
        return engine, context, a, b

    def test_mirror_match_terminates_within_safety_bound(self) -> None:
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                _, context, a, b = self._run_mirror_match(seed)
                final_round = context.round()
                self.assertLess(
                    final_round, MIRROR_MATCH_SAFETY_BOUND_ROUNDS,
                    f"Seed {seed}: Hiruma mirror took {final_round} rounds.",
                )
                self.assertFalse(
                    a.is_fighting() and b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Hirumas still "
                    f"fighting — Principle IX 2(a) violation.",
                )


class TestHirumaIdentityEngineFires(unittest.TestCase):
    """Spec 019 Principle IX 2(b). The 3rd Dan target-scoped modifier
    MUST fire across a 10-seed sweep vs Akodo (regression guard for
    the Q2 + Q3 fix)."""

    def test_3rd_dan_modifier_fires_vs_akodo(self) -> None:
        from simulation.events import AddModifierEvent
        any_3rd_dan = False
        for seed in range(1, 11):
            random.seed(seed)
            hiruma = _build_450xp_hiruma()
            hiruma._name = "Hiruma"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Crab", hiruma), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, AddModifierEvent):
                    if getattr(e.modifier, "_hiruma_3rd_dan", False):
                        any_3rd_dan = True
                        break
            if any_3rd_dan:
                break
        self.assertTrue(
            any_3rd_dan,
            "Spec 019 SC: Hiruma 3rd Dan target-scoped modifier MUST "
            "fire at least once vs Akodo across the 10-seed sweep.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
