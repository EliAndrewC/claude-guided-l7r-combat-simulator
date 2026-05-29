#!/usr/bin/env python3

#
# test_courtier_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests
# for the Courtier School (spec 026).  Combat-simulator pre-fix
# audit found Courtier is combat-competent: 6/10 wins vs Akodo 450,
# 14/26 round-robin, 0 crashes.
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


def _build_300xp_courtier() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("courtier", 300)
    return config_to_character(config)


def _build_450xp_courtier() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("courtier", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestCourtierMirrorMatchPlayability(unittest.TestCase):
    """Spec 026 SC-002 — Principle IX 2(a) mirror at 300 XP.
    Combat-simulator pre-fix found all 5 mirror seeds terminate in
    3-8 rounds (well under the 18-round cap)."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        a = _build_300xp_courtier()
        a._name = "CourtierA"
        b = _build_300xp_courtier()
        b._name = "CourtierB"
        groups = [Group("Court-A", a), Group("Court-B", b)]
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
                    f"Seed {seed}: Courtier mirror took {final_round} rounds.",
                )
                self.assertFalse(
                    a.is_fighting() and b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Courtiers "
                    f"still fighting — Principle IX 2(a) violation.",
                )


class TestCourtierIdentityEngineFires(unittest.TestCase):
    """Spec 026 Principle IX 2(b). 4th Dan TVP gain MUST fire across
    a 10-seed sweep vs Akodo. Combat-simulator pre-fix measured TVP
    firing in 10/10 vs-Akodo seeds + 24/26 round-robin matchups."""

    def test_4th_dan_tvp_fires_vs_akodo(self) -> None:
        from simulation.events import GainTemporaryVoidPointsEvent
        any_tvp = False
        for seed in range(1, 11):
            random.seed(seed)
            courtier = _build_450xp_courtier()
            courtier._name = "Courtier"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Court", courtier), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, GainTemporaryVoidPointsEvent):
                    if e.subject is courtier and getattr(e, "_courtier_4th_dan", False):
                        any_tvp = True
                        break
            if any_tvp:
                break
        self.assertTrue(
            any_tvp,
            "Spec 026 SC: Courtier 4th Dan TVP MUST fire at least "
            "once across the 10-seed sweep vs Akodo.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
