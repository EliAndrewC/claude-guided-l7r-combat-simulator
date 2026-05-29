#!/usr/bin/env python3

#
# test_daidoji_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests
# for the Daidoji Yojimbo School (spec 018 T-C1).
#

import random
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.exceptions import CombatEnded
from simulation.groups import Group


class _CappedCombatEngine(CombatEngine):
    """Bounded engine for mirror-match safety."""

    MAX_ROUNDS = 18

    def run_round(self) -> None:
        if self.context().round() >= self.MAX_ROUNDS:
            raise CombatEnded(
                f"safety cap: hit {self.MAX_ROUNDS} rounds without termination",
            )
        super().run_round()


def _build_300xp_daidoji() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("daidoji", 300)
    return config_to_character(config)


def _build_450xp_daidoji() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("daidoji", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestDaidojiMirrorMatchPlayability(unittest.TestCase):
    """Spec 018 SC-002 — Principle IX 2(a). Five seeded mirror
    matches at 300 XP."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        a = _build_300xp_daidoji()
        a._name = "DaidojiA"
        b = _build_300xp_daidoji()
        b._name = "DaidojiB"
        groups = [Group("Crane-A", a), Group("Crane-B", b)]
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
                    f"Seed {seed}: Daidoji mirror took {final_round} rounds.",
                )
                self.assertFalse(
                    a.is_fighting() and b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Daidojis still "
                    f"fighting — Principle IX 2(a) violation.",
                )


class TestDaidojiIdentityEngineFires(unittest.TestCase):
    """Spec 018 Principle IX 2(b). Interrupt-counterattack + 5th Dan
    TN modifier MUST fire across a 10-seed sweep vs Akodo."""

    def test_interrupt_counterattack_fires_vs_akodo(self) -> None:
        from simulation.events import TakeCounterattackActionEvent
        any_interrupt = False
        for seed in range(1, 11):
            random.seed(seed)
            daidoji = _build_450xp_daidoji()
            daidoji._name = "Daidoji"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Crane", daidoji), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, TakeCounterattackActionEvent):
                    ia = e.action.initiative_action()
                    if e.action.subject() is daidoji and ia.is_interrupt():
                        any_interrupt = True
                        break
            if any_interrupt:
                break
        self.assertTrue(
            any_interrupt,
            "Spec 018 SC: Daidoji Special Ability 1-die interrupt-"
            "counterattack MUST fire at least once across the 10-seed "
            "sweep vs Akodo.",
        )

    def test_5th_dan_tn_modifier_fires_vs_akodo(self) -> None:
        """Regression guard for spec 018 T-A1 (5th Dan modifier
        on the correct stat). The modifier MUST appear with a
        ``_daidoji_5th_dan_excess`` tag attribute."""
        from simulation.events import AddModifierEvent
        any_modifier = False
        for seed in range(1, 11):
            random.seed(seed)
            daidoji = _build_450xp_daidoji()
            daidoji._name = "Daidoji"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Crane", daidoji), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, AddModifierEvent):
                    if getattr(e.modifier, "_daidoji_5th_dan_excess", 0) > 0:
                        any_modifier = True
                        break
            if any_modifier:
                break
        self.assertTrue(
            any_modifier,
            "Spec 018 SC: Daidoji 5th Dan TN-to-hit modifier MUST fire "
            "at least once across the 10-seed sweep vs Akodo.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
