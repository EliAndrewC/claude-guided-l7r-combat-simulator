#!/usr/bin/env python3

#
# test_shinjo_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests
# for the Shinjo Bushi School (spec 017 T-D1).
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


def _build_300xp_shinjo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("shinjo", 300)
    return config_to_character(config)


def _build_450xp_shinjo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("shinjo", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestShinjoMirrorMatchPlayability(unittest.TestCase):
    """Spec 017 SC-002 — Principle IX 2(a) for the Shinjo Bushi
    School. Five seeded mirror matches at 300 XP."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        shinjo_a = _build_300xp_shinjo()
        shinjo_a._name = "ShinjoA"
        shinjo_b = _build_300xp_shinjo()
        shinjo_b._name = "ShinjoB"
        groups = [Group("Unicorn-A", shinjo_a), Group("Unicorn-B", shinjo_b)]
        context = EngineContext(groups)
        context.initialize()
        engine = _CappedCombatEngine(context)
        try:
            engine.run()
        except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
            pass
        return engine, context, shinjo_a, shinjo_b

    def test_mirror_match_terminates_within_safety_bound(self) -> None:
        """(a) Each mirror match MUST terminate within the safety
        bound via actual defeat (not cap saturation)."""
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                _, context, a, b = self._run_mirror_match(seed)
                final_round = context.round()
                self.assertLess(
                    final_round, MIRROR_MATCH_SAFETY_BOUND_ROUNDS,
                    f"Seed {seed}: Shinjo mirror took {final_round} rounds.",
                )
                self.assertFalse(
                    a.is_fighting() and b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Shinjos still "
                    f"fighting — Principle IX 2(a) violation.",
                )


class TestShinjoIdentityEngineFires(unittest.TestCase):
    """Spec 017 — Principle IX 2(b). The Special Ability hold-bonus
    modifier MUST fire at least once across a 10-seed sweep vs Akodo.
    Pre-fix combat-simulator measured ZERO consumption of the
    ``_shinjo_hold_bonus`` attribute."""

    def test_hold_bonus_modifier_fires_in_shinjo_vs_akodo(self) -> None:
        from simulation.events import AddModifierEvent
        any_hold_bonus = False
        for seed in range(1, 11):
            random.seed(seed)
            shinjo = _build_450xp_shinjo()
            shinjo._name = "Shinjo"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Unicorn", shinjo), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            for e in engine.history():
                if isinstance(e, AddModifierEvent):
                    modifier = e.modifier
                    if (
                        e.subject is shinjo
                        and getattr(modifier, "_shinjo_special_ability_hold_phases", 0) > 0
                    ):
                        any_hold_bonus = True
                        break
            if any_hold_bonus:
                break
        self.assertTrue(
            any_hold_bonus,
            "Spec 017 SC: Shinjo Special Ability hold-bonus MUST fire "
            "at least once across the 10-seed sweep vs Akodo (regression "
            "guard for Q4 BLOCKING IDENTITY fix).",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
