#!/usr/bin/env python3

#
# test_kuni_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests
# for the Kuni Witch Hunter School (spec 020).
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


def _build_300xp_kuni() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("kuni", 300)
    return config_to_character(config)


def _build_450xp_kuni() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("kuni", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestKuniMirrorMatchPlayability(unittest.TestCase):
    """Spec 020 SC-002 — mirror at 300 XP."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        a = _build_300xp_kuni()
        a._name = "KuniA"
        b = _build_300xp_kuni()
        b._name = "KuniB"
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
                    f"Seed {seed}: Kuni mirror took {final_round} rounds.",
                )
                self.assertFalse(
                    a.is_fighting() and b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Kunis still "
                    f"fighting — Principle IX 2(a) violation.",
                )


class TestKuniIdentityEngineFires(unittest.TestCase):
    """Spec 020 Principle IX 2(b). The 5th Dan reflection MUST fire
    across a 10-seed sweep vs Akodo (regression guard for Q4 fix +
    the features.py:586 engine gap fix)."""

    def test_5th_dan_reflection_fires_vs_akodo(self) -> None:
        from simulation.events import LightWoundsDamageEvent
        any_reflection = False
        for seed in range(1, 11):
            random.seed(seed)
            kuni = _build_450xp_kuni()
            kuni._name = "Kuni"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Crab", kuni), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, LightWoundsDamageEvent):
                    if getattr(e, "_kuni_5th_dan_reflection", False):
                        any_reflection = True
                        break
            if any_reflection:
                break
        self.assertTrue(
            any_reflection,
            "Spec 020 SC: Kuni 5th Dan reflection MUST fire at least "
            "once across the 10-seed sweep vs Akodo (regression guard "
            "for Q4 take-half fix).",
        )


class TestKuniEngineGapFix(unittest.TestCase):
    """Spec 020 FR-009 — features.py:586 must not crash on
    SpendAdventurePointsEvent.  Previously raised NotImplementedError
    which made Kuni unable to participate in any combat the features
    collector observes."""

    def test_features_collector_handles_spend_ap_event(self) -> None:
        """Regression guard: a SpendAdventurePointsEvent MUST NOT
        cause the features collector's observe_event() to raise.

        Spec 020 FR-009: ``features.py:586`` previously raised
        ``NotImplementedError("Collecting features for spend_ap
        events is not yet supported")`` which made Kuni unable to
        participate in any combat the features collector observed.
        Now it skips observation with ``pass``.
        """
        from simulation import events
        from simulation.context import EngineContext
        from simulation.features import TrialFeatures
        from simulation.groups import Group
        kuni = Character("Kuni")
        kuni.set_skill("investigation", 5)
        attacker = Character("Attacker")
        groups = [Group("Crab", kuni), Group("Enemy", attacker)]
        context = EngineContext(groups)
        features = TrialFeatures()
        spend_event = events.SpendAdventurePointsEvent(
            kuni, "attack", 5,
        )
        # Must NOT raise — previously raised NotImplementedError.
        try:
            features.observe_event(spend_event, context)
        except NotImplementedError:
            self.fail(
                "spec 020 FR-009: features.py:586 must not raise on "
                "SpendAdventurePointsEvent (Kuni 3rd+ Dan combat was "
                "previously crashing the features collector)",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
