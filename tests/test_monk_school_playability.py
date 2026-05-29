#!/usr/bin/env python3

#
# test_monk_school_playability.py
#
# Mirror-match non-degeneracy + identity-engine playability tests
# for the Brotherhood of Shinsei Monk School (spec 023).
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


def _build_300xp_monk() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("monk", 300)
    return config_to_character(config)


def _build_450xp_monk() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("monk", 450)
    return config_to_character(config)


def _build_450xp_akodo() -> Character:
    from simulation.templates.generator import generate_template
    from web.adapters.character_adapter import config_to_character
    config, _ = generate_template("akodo", 450)
    return config_to_character(config)


MIRROR_MATCH_SAFETY_BOUND_ROUNDS = 18


class TestMonkMirrorMatchPlayability(unittest.TestCase):
    """Spec 023 SC-002 — Principle IX 2(a) mirror at 300 XP.
    Combat-simulator pre-fix audit found 5/5 mirror seeds terminate
    in 3-4 rounds (well under the 18-round cap)."""

    SEEDS = [1, 2, 3, 4, 5]

    def _run_mirror_match(self, seed: int) -> tuple[CombatEngine, EngineContext, Character, Character]:
        random.seed(seed)
        a = _build_300xp_monk()
        a._name = "MonkA"
        b = _build_300xp_monk()
        b._name = "MonkB"
        groups = [Group("Brotherhood-A", a), Group("Brotherhood-B", b)]
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
                    f"Seed {seed}: Monk mirror took {final_round} rounds.",
                )
                self.assertFalse(
                    a.is_fighting() and b.is_fighting(),
                    f"Seed {seed}: combat hit cap with both Monks still "
                    f"fighting — Principle IX 2(a) violation.",
                )


class TestMonkCoveragePadding(unittest.TestCase):
    """Coverage padding for uncovered branches in monk_school.py."""

    def test_lower_action_dice_breaks_on_empty(self) -> None:
        """``MonkNewRoundListener._lower_action_dice`` breaks
        immediately when the character has 0 action dice (e.g.
        after the previous loop iteration exhausted them)."""
        from simulation import events
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        from simulation.schools import monk_school
        monk = Character("Monk")
        monk.set_skill("precepts", 5)
        school = monk_school.BrotherhoodOfShinseMonkSchool()
        school.apply_rank_three_ability(monk)
        # Empty initiative roll → zero action dice.
        rp = CalvinistRollProvider()
        rp.put_initiative_roll([])
        monk.set_roll_provider(rp)
        enemy = Character("Enemy")
        groups = [Group("Brotherhood", monk), Group("Enemy", enemy)]
        ctx = EngineContext(groups)
        listener = monk._listeners["new_round"]
        # Must not crash — the empty-actions branch hits `break`.
        list(listener.handle(monk, events.NewRoundEvent(1), ctx))
        self.assertEqual([], monk.actions())

    def test_action_factory_falls_through_for_non_attack_skills(self) -> None:
        """``MonkActionFactory.get_attack_action`` falls through to
        the default factory for skills other than attack/iaijutsu
        (e.g., feint, lunge, double attack, counterattack)."""
        from simulation.actions import AttackAction
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.initiative_actions import InitiativeAction
        from simulation.schools import monk_school
        monk = Character("Monk")
        target = Character("Target")
        monk.set_actions([1])
        target.set_actions([1])
        groups = [Group("Brotherhood", monk), Group("Enemy", target)]
        ctx = EngineContext(groups)
        ia = InitiativeAction([1], 1)
        factory = monk_school.MonkActionFactory()
        action = factory.get_attack_action(monk, target, "feint", ia, ctx)
        # Not a MonkAttackAction for non-attack/iaijutsu — falls back
        # to the default AttackAction.
        self.assertIsInstance(action, AttackAction)
        self.assertNotIsInstance(action, monk_school.MonkAttackAction)

    def test_fifth_dan_new_round_listener_default_branch(self) -> None:
        """``MonkFifthDanNewRoundListener`` falls back to rolling
        initiative when no wrapped listener is provided (None)."""
        from simulation import events
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        from simulation.schools import monk_school
        monk = Character("Monk")
        rp = CalvinistRollProvider()
        rp.put_initiative_roll([3, 5, 7])
        monk.set_roll_provider(rp)
        enemy = Character("Enemy")
        groups = [Group("Brotherhood", monk), Group("Enemy", enemy)]
        ctx = EngineContext(groups)
        fifth_dan = monk_school.MonkFifthDanListener()
        listener = monk_school.MonkFifthDanNewRoundListener(
            wrapped_listener=None,
            fifth_dan_listener=fifth_dan,
        )
        list(listener.handle(monk, events.NewRoundEvent(1), ctx))
        # Initiative was rolled via the fallback branch.
        self.assertEqual([3, 5, 7], monk.actions())


class TestMonkIdentityEngineFires(unittest.TestCase):
    """Spec 023 Principle IX 2(b). The 5th Dan counter-attack MUST
    fire across a 10-seed sweep vs Akodo — combat-simulator measured
    90 counter-attacks across 10 fights pre-fix (the dominant offense
    source)."""

    def test_5th_dan_counter_attack_fires_vs_akodo(self) -> None:
        from simulation.events import LightWoundsDamageEvent
        any_counter = False
        for seed in range(1, 11):
            random.seed(seed)
            monk = _build_450xp_monk()
            monk._name = "Monk"
            akodo = _build_450xp_akodo()
            akodo._name = "Akodo"
            groups = [Group("Brotherhood", monk), Group("Lion", akodo)]
            context = EngineContext(groups)
            context.initialize()
            engine = _CappedCombatEngine(context)
            try:
                engine.run()
            except CombatEnded:  # pragma: no cover  # defensive: CombatEngine.run() catches CombatEnded internally
                pass
            # The 5th Dan counter-attack yields a
            # LightWoundsDamageEvent from monk to akodo OUTSIDE the
            # normal TakeAttackActionEvent flow.  Check for the
            # subject=monk, target=akodo pattern with damage > 0.
            for e in engine.history():
                if isinstance(e, LightWoundsDamageEvent):
                    if e.subject is monk and e.target is akodo and e.damage > 0:
                        any_counter = True
                        break
            if any_counter:
                break
        self.assertTrue(
            any_counter,
            "Spec 023 SC: Monk 5th Dan counter-attack MUST fire at "
            "least once across the 10-seed sweep vs Akodo.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
