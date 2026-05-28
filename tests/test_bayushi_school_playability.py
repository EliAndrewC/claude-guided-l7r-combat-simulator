#!/usr/bin/env python3

#
# test_bayushi_school_playability.py
#
# Mirror-match non-degeneracy + win-feasibility tests for the Bayushi
# Bushi School (US2 / US3).
#
# Added 2026-05-28 per spec branch 013 audit.  Uses the standard
# ``_CappedCombatEngine`` OOM-trigger containment pattern from Hida.
#
# IMPORTANT: per the spec's documented P0 deferral, the Bayushi
# default attack strategy is the engine default ``UniversalAttackStrategy``
# which rarely feints because of the ``vp() == 0`` gate.  These tests
# verify what IS playable under the current defaults (which is
# substantial — combat-simulator measured 80% win-rate vs Akodo at 450
# XP).  When the follow-up branch installs ``BayushiAttackStrategy``,
# these tests will need re-baselining to the new identity-engine
# behavior.
#
# Constitution Principle IX 2(a) + 2(b) + 2(c).
#

import random
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.exceptions import CombatEnded
from simulation.groups import Group


class _CappedCombatEngine(CombatEngine):
    """CombatEngine subclass with a hard round cap.

    The engine itself has no built-in termination guard — same
    OOM-trigger containment pattern as Hida + Matsu spec branches.
    """

    MAX_ROUNDS = 18

    def run_round(self) -> None:
        if self.context().round() >= self.MAX_ROUNDS:
            raise CombatEnded(
                f"safety cap: hit {self.MAX_ROUNDS} rounds without termination",
            )
        super().run_round()


def _build_300xp_bayushi() -> Character:
    """Build a 300-XP Bayushi via the canonical template pipeline."""
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("bayushi", 300)
    return config_to_character(config)


def _build_450xp_bayushi() -> Character:
    """Build a 450-XP Bayushi via the canonical template pipeline."""
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("bayushi", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    """Build a 450-XP Akodo via the canonical template pipeline."""
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


class TestBayushiMirrorMatchPlayability(unittest.TestCase):
    """Principle IX 2(a) + 2(b) — mirror match terminates AND identity
    engine (some form of attack action) fires across runs.

    Note: under the current defaults (no ``BayushiAttackStrategy``
    installed), Bayushi rarely feints, so the "identity engine" check
    here verifies that SOME attack action fires (the Bayushi default
    Special Ability + double-attack ladder is sufficient for combat
    termination).  When the follow-up branch installs the strategy,
    this test should be updated to explicitly verify ``feint`` events.
    """

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        bayushi_a = _build_300xp_bayushi()
        bayushi_a._name = "BayushiA"
        bayushi_b = _build_300xp_bayushi()
        bayushi_b._name = "BayushiB"
        groups = [Group("Scorpion-A", bayushi_a), Group("Scorpion-B", bayushi_b)]
        context = EngineContext(groups)
        context.initialize()
        engine = _CappedCombatEngine(context)
        try:
            engine.run()
        except CombatEnded:  # pragma: no cover  # defensive: engine.run catches CombatEnded internally
            pass
        return engine, context, bayushi_a, bayushi_b

    def test_mirror_match_terminates_within_safety_bound(self) -> None:
        """5 seeded Bayushi mirror matches MUST terminate within
        ``_CappedCombatEngine.MAX_ROUNDS`` rounds via actual defeat
        (strict less-than + both-fighting-False check per Hida lesson).
        """
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                _, context, b_a, b_b = self._run_mirror_match(seed)
                final_round = context.round()
                self.assertLess(
                    final_round, _CappedCombatEngine.MAX_ROUNDS,
                    f"Seed {seed}: Bayushi mirror match took {final_round} "
                    f"rounds (cap: {_CappedCombatEngine.MAX_ROUNDS}).  "
                    f"Principle IX 2(a) requires termination via actual "
                    f"defeat, not cap-saturation.",
                )
                self.assertFalse(
                    b_a.is_fighting() and b_b.is_fighting(),
                    f"Seed {seed}: combat hit the cap with both Bayushis "
                    f"still fighting; engine did not naturally terminate.  "
                    f"Principle IX 2(a) violation.",
                )

    def test_mirror_match_attack_engine_fires(self) -> None:
        """Across the 5 mirror matches, each Bayushi MUST take at
        least one attack action.  Principle IX 2(b)."""
        from simulation import events as ev
        any_attack_a = False
        any_attack_b = False
        for seed in self.SEEDS:
            engine, _, b_a, b_b = self._run_mirror_match(seed)
            for e in engine.history():
                if isinstance(e, ev.TakeAttackActionEvent):
                    subj = e.action.subject()
                    if subj == b_a:
                        any_attack_a = True
                    elif subj == b_b:
                        any_attack_b = True
        self.assertTrue(
            any_attack_a,
            "Principle IX 2(b): BayushiA took ZERO attack actions "
            "across the mirror matches.",
        )
        self.assertTrue(
            any_attack_b,
            "Principle IX 2(b): BayushiB took ZERO attack actions "
            "across the mirror matches.",
        )


class TestBayushiWinFeasibility(unittest.TestCase):
    """Principle IX 2(c) — win-feasibility floor.

    Per combat-simulator measurement: Bayushi vs Akodo at 450 XP shows
    ~80% win-rate under current defaults (Bayushi's Special Ability
    VP-on-damage is so strong it wins on damage spike).  This test
    asserts the conservative 35% floor.
    """

    SEEDS = list(range(1, 21))
    WIN_RATE_THRESHOLD = 0.35

    def _run_match(
        self, attacker: Character, defender: Character, seed: int,
    ) -> Character | None:
        random.seed(seed)
        groups = [
            Group("Attacker", attacker), Group("Defender", defender),
        ]
        context = EngineContext(groups)
        context.initialize()
        engine = _CappedCombatEngine(context)
        try:
            engine.run()
        except CombatEnded:  # pragma: no cover  # defensive
            pass
        if attacker.is_fighting() and not defender.is_fighting():
            return attacker
        if defender.is_fighting() and not attacker.is_fighting():
            return defender
        return None

    def test_bayushi_winrate_vs_akodo_at_450_xp_ge_35_percent(self) -> None:
        """20 seeds: 450-XP Bayushi MUST win >= 35% vs 450-XP Akodo.
        Combat-simulator measurement shows ~80% under current defaults,
        well above the floor."""
        wins = 0
        for seed in self.SEEDS:
            bayushi = _build_450xp_bayushi()
            bayushi._name = "Bayushi"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            if self._run_match(bayushi, akodo, seed) == bayushi:
                wins += 1
        win_rate = wins / len(self.SEEDS)
        self.assertGreaterEqual(
            win_rate, self.WIN_RATE_THRESHOLD,
            f"FR-SC-001: Bayushi won {wins}/{len(self.SEEDS)} "
            f"({win_rate:.0%}) vs Akodo at 450 XP; need >= "
            f"{self.WIN_RATE_THRESHOLD:.0%}.",
        )


class TestBayushiPriorities(unittest.TestCase):
    """US4 regression guard on BAYUSHI_PRIORITIES."""

    def test_bayushi_priorities_includes_all_knacks(self) -> None:
        """BAYUSHI_PRIORITIES MUST reference all three school knacks
        (double attack, feint, iaijutsu) per rules/04-schools.md."""
        from simulation.templates.strategies import BAYUSHI_PRIORITIES
        skill_names = {
            entry[1] for entry in BAYUSHI_PRIORITIES
            if len(entry) >= 2 and entry[0] == "skill"
        }
        for knack in ("double attack", "feint", "iaijutsu"):
            self.assertIn(
                knack, skill_names,
                f"BAYUSHI_PRIORITIES must reference '{knack}' "
                f"(Bayushi school knack per rules/04-schools.md); "
                f"got: {sorted(skill_names)}",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
