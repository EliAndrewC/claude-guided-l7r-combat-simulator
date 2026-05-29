#!/usr/bin/env python3

#
# test_kakita_school_playability.py
#
# Mirror-match non-degeneracy + win-feasibility tests for the Kakita
# Duelist School (US2 / US3).
#
# Added 2026-05-29 per spec branch 014.  Uses the standard
# ``_CappedCombatEngine`` OOM-trigger containment pattern from Hida.
#
# Combat-simulator measured Kakita's win-rate vs 450-XP Akodo at 90%
# under defaults — the 5th Dan contested iaijutsu + 3rd Dan tempo
# bonus + 4th Dan iaijutsu damage free raise stack into a highly
# lethal first-round opener.
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
    """CombatEngine subclass with a hard round cap (Hida/Matsu/
    Bayushi pattern)."""

    MAX_ROUNDS = 18

    def run_round(self) -> None:
        if self.context().round() >= self.MAX_ROUNDS:
            raise CombatEnded(
                f"safety cap: hit {self.MAX_ROUNDS} rounds without termination",
            )
        super().run_round()


def _build_300xp_kakita() -> Character:
    """Build a 300-XP Kakita via the canonical template pipeline."""
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("kakita", 300)
    return config_to_character(config)


def _build_450xp_kakita() -> Character:
    """Build a 450-XP Kakita via the canonical template pipeline."""
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("kakita", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    """Build a 450-XP Akodo via the canonical template pipeline."""
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


class TestKakitaMirrorMatchPlayability(unittest.TestCase):
    """Principle IX 2(a) + 2(b) — mirror match terminates AND identity
    engine fires across runs.

    The Kakita identity engine is the 5th Dan contested iaijutsu at
    Phase 0 every round.  In a mirror, both Kakitas yield contested
    events at Phase 0 and the engine sequences them cleanly per
    combat-simulator verification.
    """

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        kakita_a = _build_300xp_kakita()
        kakita_a._name = "KakitaA"
        kakita_b = _build_300xp_kakita()
        kakita_b._name = "KakitaB"
        groups = [Group("Crane-A", kakita_a), Group("Crane-B", kakita_b)]
        context = EngineContext(groups)
        context.initialize()
        engine = _CappedCombatEngine(context)
        try:
            engine.run()
        except CombatEnded:  # pragma: no cover  # defensive: engine.run catches CombatEnded internally
            pass
        return engine, context, kakita_a, kakita_b

    def test_mirror_match_terminates_within_safety_bound(self) -> None:
        """5 seeded Kakita mirror matches MUST terminate within
        ``_CappedCombatEngine.MAX_ROUNDS`` rounds via actual defeat."""
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                _, context, k_a, k_b = self._run_mirror_match(seed)
                final_round = context.round()
                self.assertLess(
                    final_round, _CappedCombatEngine.MAX_ROUNDS,
                    f"Seed {seed}: Kakita mirror match took {final_round} "
                    f"rounds (cap: {_CappedCombatEngine.MAX_ROUNDS}).",
                )
                self.assertFalse(
                    k_a.is_fighting() and k_b.is_fighting(),
                    f"Seed {seed}: combat hit the cap with both Kakitas "
                    f"still fighting; engine did not naturally terminate.",
                )

    def test_mirror_match_5th_dan_contested_fires(self) -> None:
        """Across the 5 mirror matches, the 5th Dan contested
        iaijutsu MUST fire at Phase 0 (the school's identity engine).
        Principle IX 2(b)."""
        from simulation.schools.kakita_school import (
            ContestedIaijutsuAttackDeclaredEvent,
        )
        any_contested = False
        for seed in self.SEEDS:
            engine, _, _, _ = self._run_mirror_match(seed)
            for e in engine.history():
                if isinstance(e, ContestedIaijutsuAttackDeclaredEvent):
                    any_contested = True
                    break
            if any_contested:
                break
        self.assertTrue(
            any_contested,
            "Principle IX 2(b): NO ContestedIaijutsuAttackDeclaredEvent "
            "fired across the mirror matches.  The Kakita 5th Dan "
            "identity engine is not firing.",
        )


class TestKakitaWinFeasibility(unittest.TestCase):
    """Principle IX 2(c) — win-feasibility floor.

    Per combat-simulator measurement: Kakita vs Akodo at 450 XP shows
    ~90% win-rate under defaults (the 5th Dan contested + 3rd Dan
    tempo + 4th Dan iaijutsu damage stack into round-1 lethal damage).
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

    def test_kakita_winrate_vs_akodo_at_450_xp_ge_35_percent(self) -> None:
        """20 seeds: 450-XP Kakita MUST win >= 35% vs 450-XP Akodo."""
        wins = 0
        for seed in self.SEEDS:
            kakita = _build_450xp_kakita()
            kakita._name = "Kakita"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            if self._run_match(kakita, akodo, seed) == kakita:
                wins += 1
        win_rate = wins / len(self.SEEDS)
        self.assertGreaterEqual(
            win_rate, self.WIN_RATE_THRESHOLD,
            f"FR-SC-001: Kakita won {wins}/{len(self.SEEDS)} "
            f"({win_rate:.0%}) vs Akodo at 450 XP; need >= "
            f"{self.WIN_RATE_THRESHOLD:.0%}.",
        )


class TestKakitaPriorities(unittest.TestCase):
    """US4 regression guard on KAKITA_PRIORITIES."""

    def test_kakita_priorities_includes_all_knacks(self) -> None:
        """KAKITA_PRIORITIES MUST reference all three school knacks
        (double attack, iaijutsu, lunge) per rules/04-schools.md."""
        from simulation.templates.strategies import KAKITA_PRIORITIES
        skill_names = {
            entry[1] for entry in KAKITA_PRIORITIES
            if len(entry) >= 2 and entry[0] == "skill"
        }
        for knack in ("double attack", "iaijutsu", "lunge"):
            self.assertIn(
                knack, skill_names,
                f"KAKITA_PRIORITIES must reference '{knack}' "
                f"(Kakita school knack per rules/04-schools.md); "
                f"got: {sorted(skill_names)}",
            )


class TestKakitaInterruptAttackStrategyInstalled(unittest.TestCase):
    """Regression guard for strategy-designer's HIGH-severity fix
    (specs/013 OPEN_QUESTIONS Q3): the default attack strategy MUST
    be `KakitaInterruptAttackStrategy` (NOT the base
    `KakitaAttackStrategy`).  Without the interrupt-aware variant,
    the Special Ability's interrupt-iaijutsu clause is structurally
    dead — a Constitution Principle VIII identity bug.
    """

    def test_default_attack_strategy_is_interrupt_attack(self) -> None:
        from simulation.character_builder import CharacterBuilder
        from simulation.schools.kakita_school import (
            KakitaBushiSchool,
            KakitaInterruptAttackStrategy,
        )
        school = KakitaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Kakita").with_school(school)
        kakita = builder.build()
        self.assertIsInstance(
            kakita.attack_strategy(),
            KakitaInterruptAttackStrategy,
            f"Default attack strategy must be KakitaInterruptAttackStrategy "
            f"(not the base KakitaAttackStrategy) so the Special "
            f"Ability's interrupt-iaijutsu clause produces behavior.  "
            f"Got: {type(kakita.attack_strategy()).__name__}.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
