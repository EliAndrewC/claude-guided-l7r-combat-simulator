#!/usr/bin/env python3

#
# test_ide_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests
# for the Ide Diplomat School (spec 031).
#

import random
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.events import AddModifierEvent
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


def _build_300xp_ide() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("ide", 300)
    return config_to_character(config)


def _build_450xp_ide() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("ide", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestIdeMirrorMatchPlayability(unittest.TestCase):
    """Spec 031 SC-002 — Principle IX 2(a) mirror at 300 XP."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        a = _build_300xp_ide()
        a._name = "IdeA"
        b = _build_300xp_ide()
        b._name = "IdeB"
        groups = [Group("Uni-A", a), Group("Uni-B", b)]
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
                    f"Seed {seed}: Ide mirror took {final_round} rounds.",
                )
                self.assertFalse(
                    a.is_fighting() and b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Ides still "
                    f"fighting — Principle IX 2(a) violation.",
                )


class TestIdeIdentityEngineFires(unittest.TestCase):
    """Spec 031 Principle IX 2(b). The Ide SA — feint that meets
    TN installs a −10 TN modifier on the target via
    AddModifierEvent. Verify at least one such modifier installation
    fires across a 10-seed sweep vs Akodo."""

    def test_ide_feint_modifier_fires_vs_akodo(self) -> None:
        any_modifier = False
        for seed in range(1, 11):
            random.seed(seed)
            ide = _build_450xp_ide()
            ide._name = "Ide"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Uni", ide), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, AddModifierEvent):
                    # Ide SA installs an AnyAttackModifier on akodo
                    if getattr(e, "subject", None) is akodo:
                        any_modifier = True
                        break
            if any_modifier:
                break
        self.assertTrue(
            any_modifier,
            "Spec 031 SC: Ide SA feint→-10 modifier MUST install on "
            "Akodo at least once across the 10-seed sweep at 450 XP.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
