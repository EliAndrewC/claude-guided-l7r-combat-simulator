#!/usr/bin/env python3

#
# test_hida_school_strategy.py
#
# Unit tests for the Hida Bushi School identity-driven default strategy
# bindings introduced in Batch E (T024, T026, T027).
#
# rules/04-schools.md "Hida Bushi School: Special Ability" + Constitution
# Principles VIII (school identity drives defaults) and IX (defaults
# must be playable + identity engine must fire in mirror).
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools import hida_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


def _make_hida_for_attack_strategy(
    *,
    attack_skill: int = 4,
    double_attack_skill: int = 3,
    counterattack_skill: int = 4,
    iaijutsu_skill: int = 3,
    actions_list: list[int] | None = None,
    apply_school: bool = True,
) -> Character:
    """Build a Hida character configured to exercise HidaAttackStrategy.

    The character has access to the three Hida school knacks
    (counterattack, double attack, iaijutsu) and attack/parry to drive
    the kill-shot, pressure, and reserve branches.
    """
    school = hida_school.HidaBushiSchool()
    hida = Character("Hida")
    if actions_list is None:
        actions_list = [1, 5]
    hida.set_actions(actions_list)
    hida.set_ring("water", 3)
    hida.set_ring("earth", 2)
    hida.set_skill("attack", attack_skill)
    hida.set_skill("double attack", double_attack_skill)
    hida.set_skill("counterattack", counterattack_skill)
    hida.set_skill("iaijutsu", iaijutsu_skill)
    hida.set_skill("parry", attack_skill)
    hida.set_skill("wound check", attack_skill)
    hida.set_school(school)
    if apply_school:
        school.apply_special_ability(hida)
    return hida


def _make_dummy_target(*, max_sw: int | None = None, sw_already: int = 0) -> Character:
    """Build a dummy target character.

    Parameters
    ----------
    max_sw:
        If provided, set the earth ring so ``max_sw()`` returns this
        value.  Default leaves earth at its default (2 → max_sw = 2).
    sw_already:
        Take this many SW so ``sw_remaining()`` decreases accordingly.
    """
    target = Character("Target")
    target.set_actions([1])
    target.set_skill("parry", 1)
    if max_sw is not None:
        target.set_ring("earth", max(1, max_sw // 2))
    for _ in range(sw_already):
        target.take_sw(1)
    return target


class TestHidaAttackStrategy(unittest.TestCase):
    """T024 — HidaAttackStrategy three-branch policy.

    Per the strategy-designer's resolution (OPEN_QUESTIONS Q12) and
    rules/04-schools.md "Hida Bushi School" knacks (counterattack,
    double attack, iaijutsu — NOT lunge), the strategy MUST:

      1. Kill-shot branch: target.sw_remaining() <= 1 → try double
         attack (Hida knack), then plain attack.  NEVER lunge.
      2. Pressure branch: full health AND ≥ 2 action dice → attack.
      3. Reserve branch: otherwise → HoldActionEvent (reserve dice
         for counterattack-interrupt).
    """

    def test_kill_shot_branch_attempts_double_attack_when_target_near_death(self) -> None:
        """Kill-shot: target at 1 SW remaining + double attack skill > 0
        → strategy returns a double-attack TakeAttackActionEvent.
        """
        # Build the Hida + a near-death target.
        hida = _make_hida_for_attack_strategy(
            attack_skill=4, double_attack_skill=3,
            actions_list=[1, 5],
        )
        target = _make_dummy_target(max_sw=4, sw_already=3)
        # max_sw = 2*earth = 4; sw=3 → sw_remaining = 1.
        self.assertEqual(1, target.sw_remaining())
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()

        strategy = hida.attack_strategy()
        responses = list(strategy.recommend(
            hida, events.YourMoveEvent(hida), context,
        ))
        attack_events = [
            e for e in responses if isinstance(e, events.TakeAttackActionEvent)
        ]
        self.assertEqual(
            1, len(attack_events),
            f"Kill-shot branch must yield exactly one TakeAttackActionEvent; "
            f"got {len(attack_events)}: {responses}",
        )
        skill = attack_events[0].action.skill()
        self.assertEqual(
            "double attack", skill,
            f"Kill-shot branch must use double attack (NOT {skill} — "
            f"finishing damage > defensive reserve).",
        )

    def test_kill_shot_branch_falls_back_to_attack_when_double_attack_skill_zero(self) -> None:
        """Kill-shot fallback: double attack skill = 0 → use plain attack."""
        hida = _make_hida_for_attack_strategy(
            attack_skill=4, double_attack_skill=0,
            actions_list=[1, 5],
        )
        target = _make_dummy_target(max_sw=4, sw_already=3)
        self.assertEqual(1, target.sw_remaining())
        self.assertEqual(0, hida.skill("double attack"))
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()

        strategy = hida.attack_strategy()
        responses = list(strategy.recommend(
            hida, events.YourMoveEvent(hida), context,
        ))
        attack_events = [
            e for e in responses if isinstance(e, events.TakeAttackActionEvent)
        ]
        self.assertEqual(1, len(attack_events))
        skill = attack_events[0].action.skill()
        self.assertEqual(
            "attack", skill,
            f"Kill-shot fallback must use plain attack when "
            f"double-attack skill is 0; got {skill}.",
        )

    def test_pressure_branch_attacks_when_full_health_with_spare_actions(self) -> None:
        """Pressure: sw_remaining == max_sw AND len(actions) >= 2 →
        strategy yields a TakeAttackActionEvent (NOT HoldActionEvent).
        """
        hida = _make_hida_for_attack_strategy(
            attack_skill=4, double_attack_skill=3,
            actions_list=[1, 5],  # two actions; current phase=1
        )
        target = _make_dummy_target(max_sw=4)
        # Target is not near death, so kill-shot branch should NOT fire.
        self.assertGreater(target.sw_remaining(), 1)
        # Hida at full health.
        self.assertEqual(hida.sw_remaining(), hida.max_sw())
        # Hida has 2+ actions.
        self.assertGreaterEqual(len(hida.actions()), 2)
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()

        strategy = hida.attack_strategy()
        responses = list(strategy.recommend(
            hida, events.YourMoveEvent(hida), context,
        ))
        # Should yield a TakeAttackActionEvent, NOT a HoldActionEvent.
        attack_events = [
            e for e in responses if isinstance(e, events.TakeAttackActionEvent)
        ]
        hold_events = [
            e for e in responses if isinstance(e, events.HoldActionEvent)
        ]
        self.assertEqual(
            1, len(attack_events),
            f"Pressure branch must yield a TakeAttackActionEvent; "
            f"got {responses}",
        )
        self.assertEqual(
            0, len(hold_events),
            f"Pressure branch must NOT hold the action; got {responses}",
        )

    def test_reserve_branch_holds_action_when_mid_fight(self) -> None:
        """Reserve: NOT kill-shot, NOT full-health-with-spare-actions →
        strategy yields HoldActionEvent (reserve for counterattack).

        We simulate "mid-fight" by giving the Hida only 1 action die
        AND putting the target NOT in kill-shot range.  Both the kill-
        shot branch and the pressure branch should reject; the reserve
        branch yields HoldActionEvent.
        """
        hida = _make_hida_for_attack_strategy(
            attack_skill=4, double_attack_skill=3,
            actions_list=[1],  # only ONE action — pressure branch declines
        )
        target = _make_dummy_target(max_sw=4)
        self.assertGreater(target.sw_remaining(), 1)  # NOT kill-shot
        self.assertEqual(1, len(hida.actions()))  # NOT pressure (< 2 actions)
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()

        strategy = hida.attack_strategy()
        responses = list(strategy.recommend(
            hida, events.YourMoveEvent(hida), context,
        ))
        hold_events = [
            e for e in responses if isinstance(e, events.HoldActionEvent)
        ]
        attack_events = [
            e for e in responses if isinstance(e, events.TakeAttackActionEvent)
        ]
        self.assertEqual(
            0, len(attack_events),
            f"Reserve branch must NOT attack; got {responses}",
        )
        self.assertEqual(
            1, len(hold_events),
            f"Reserve branch must yield exactly one HoldActionEvent; "
            f"got {responses}",
        )

    def test_recommend_ignores_non_your_move_event(self) -> None:
        """``recommend`` must yield nothing when the event isn't
        ``YourMoveEvent`` — the strategy is only consulted on the
        character's own move slot.
        """
        hida = _make_hida_for_attack_strategy(actions_list=[1, 5])
        target = _make_dummy_target(max_sw=4)
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()

        strategy = hida.attack_strategy()
        # NewPhaseEvent is a non-YME event the strategy must ignore.
        responses = list(strategy.recommend(
            hida, events.NewPhaseEvent(1), context,
        ))
        self.assertEqual(
            [], responses,
            f"recommend must yield nothing on a non-YME event; got {responses}.",
        )

    def test_recommend_yields_no_action_when_character_has_no_action(self) -> None:
        """When ``character.has_action(context)`` is False, recommend
        must yield ``NoActionEvent`` immediately (no kill-shot/pressure
        branches checked)."""
        hida = _make_hida_for_attack_strategy(actions_list=[])
        target = _make_dummy_target(max_sw=4)
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()
        self.assertFalse(hida.has_action(context))

        strategy = hida.attack_strategy()
        responses = list(strategy.recommend(
            hida, events.YourMoveEvent(hida), context,
        ))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.NoActionEvent)

    def test_kill_shot_desperation_fires_when_primary_thresholds_fail(self) -> None:
        """Kill-shot desperation: target at sw_remaining=1 AND primary
        0.6/0.7 thresholds both return None → retry at 0.05 desperation
        threshold.  Forces this by giving the Hida a deliberately weak
        attack skill (1) and the target high parry (so the optimizer
        can't reach the primary threshold) while still letting the
        ``target.sw_remaining() == 1`` gate engage.
        """
        hida = _make_hida_for_attack_strategy(
            attack_skill=1, double_attack_skill=0,
            counterattack_skill=1, iaijutsu_skill=0,
            actions_list=[1, 5],
        )
        # Strong target with high parry — primary thresholds unreachable.
        target = Character("StrongTarget")
        target.set_actions([1])
        target.set_skill("parry", 5)
        target.set_ring("earth", 2)
        target.take_sw(3)  # max_sw=4, sw_remaining=1 → kill-shot engages
        self.assertEqual(1, target.sw_remaining())
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()

        strategy = hida.attack_strategy()
        responses = list(strategy.recommend(
            hida, events.YourMoveEvent(hida), context,
        ))
        attack_events = [
            e for e in responses if isinstance(e, events.TakeAttackActionEvent)
        ]
        # Desperation must fire — at 0.05 confidence the optimizer
        # accepts a bare-skill attack.
        self.assertEqual(
            1, len(attack_events),
            f"Kill-shot desperation must fire (target at sw_remaining=1 "
            f"AND primary thresholds unreachable); got {responses}.",
        )
        # Must be plain attack (double_attack skill is 0; the loop skips
        # it and falls through to plain attack).
        self.assertEqual("attack", attack_events[0].action.skill())

    def test_strategy_avoids_lunge_skill(self) -> None:
        """The strategy NEVER selects 'lunge' (which is NOT a Hida knack
        per rules/04-schools.md "Hida Bushi School").

        We exercise both the kill-shot and pressure branches, with the
        Hida having a high lunge skill, and assert no TakeAttackActionEvent
        for the lunge action is emitted.
        """
        # Hida with a HIGH lunge skill (to tempt a buggy implementation
        # into using it).  But lunge is not a Hida knack, so the strategy
        # must not pick it.
        hida = _make_hida_for_attack_strategy(
            attack_skill=4, double_attack_skill=3,
            actions_list=[1, 5],
        )
        hida.set_skill("lunge", 5)
        # Run two scenarios: kill-shot and pressure.
        for target_sw_already, expected_branch in [
            (3, "kill-shot"),  # target near death (sw_remaining=1)
            (0, "pressure"),   # target full health, Hida full health + 2 actions
        ]:
            with self.subTest(branch=expected_branch):
                target = _make_dummy_target(max_sw=4, sw_already=target_sw_already)
                groups = [Group("Crab", hida), Group("Enemy", target)]
                context = EngineContext(groups, phase=1)
                context.initialize()

                strategy = hida.attack_strategy()
                responses = list(strategy.recommend(
                    hida, events.YourMoveEvent(hida), context,
                ))
                attack_events = [
                    e for e in responses if isinstance(e, events.TakeAttackActionEvent)
                ]
                for e in attack_events:
                    self.assertNotEqual(
                        "lunge", e.action.skill(),
                        f"Strategy must NEVER use lunge (not a Hida knack); "
                        f"branch={expected_branch}, skill={e.action.skill()}.",
                    )


class TestHidaAttackStrategyInstalled(unittest.TestCase):
    """T026/T027 — verify apply_special_ability installs HidaAttackStrategy
    + HidaCounterattackInterruptStrategy + WoundCheckStrategy04.

    Per OPEN_QUESTIONS Q12 strategy-designer's accepted bindings.
    """

    def test_apply_special_ability_installs_hida_attack_strategy(self) -> None:
        """The attack slot holds HidaAttackStrategy after apply_special_ability."""
        from simulation.character_builder import CharacterBuilder
        school = hida_school.HidaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Hida").with_school(school)
        hida = builder.build()
        self.assertIsInstance(hida.attack_strategy(), hida_school.HidaAttackStrategy)

    def test_apply_special_ability_installs_hida_counterattack_interrupt(self) -> None:
        """The interrupt slot holds HidaCounterattackInterruptStrategy
        (not vanilla CounterattackInterruptStrategy)."""
        from simulation.character_builder import CharacterBuilder
        school = hida_school.HidaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Hida").with_school(school)
        hida = builder.build()
        self.assertIsInstance(
            hida.interrupt_strategy(),
            hida_school.HidaCounterattackInterruptStrategy,
        )

    def test_apply_special_ability_installs_wound_check_strategy04(self) -> None:
        """The wound_check slot holds WoundCheckStrategy04 (0.4 threshold)
        after apply_special_ability (with 1st Dan +1 WC die in extra_rolled).
        """
        from simulation.character_builder import CharacterBuilder
        from simulation.strategies.base import WoundCheckStrategy04
        school = hida_school.HidaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Hida").with_school(school)
        hida = builder.build()
        self.assertIsInstance(hida.wound_check_strategy(), WoundCheckStrategy04)

    def test_apply_rank_four_ability_overrides_wound_check_strategy(self) -> None:
        """At 4th Dan, HidaWoundCheckStrategy replaces WoundCheckStrategy04
        (per OPEN_QUESTIONS Q12).
        """
        from simulation.character_builder import CharacterBuilder
        school = hida_school.HidaBushiSchool()
        builder = (
            CharacterBuilder(9001)
            .with_name("Hida")
            .with_school(school)
            .buy_skill("counterattack", 4)
            .buy_skill("double attack", 4)
            .buy_skill("iaijutsu", 4)
        )
        hida = builder.build()
        self.assertIsInstance(
            hida.wound_check_strategy(), hida_school.HidaWoundCheckStrategy,
        )


class TestHidaCounterattackInterruptStrategyGates(unittest.TestCase):
    """T025 — recursion and SW-saturation gates on the Hida counterattack
    interrupt strategy.

    Per OPEN_QUESTIONS Q12 strategy-designer's resolution:
      * Recursion gate: do NOT counterattack an incoming counterattack
        (prevents mirror-match counterattack-of-counterattack spiral).
      * SW-saturation gate: do NOT counterattack when sw_remaining <= 1
        AND the incoming attack has _counterattack_roll_bonus > 0
        (better to parry/eat hit and use 4th Dan SW-for-LW).
    """

    def _build_5th_dan_hida(self) -> Character:
        """Helper: 5th-Dan Hida with 5th-Dan ability applied."""
        school = hida_school.HidaBushiSchool()
        hida = Character("Hida")
        hida.set_actions([5, 8])
        hida.set_ring("water", 4)
        hida.set_ring("earth", 3)
        hida.set_skill("attack", 5)
        hida.set_skill("counterattack", 5)
        hida.set_skill("double attack", 5)
        hida.set_skill("iaijutsu", 5)
        hida.set_skill("parry", 5)
        hida.set_skill("wound check", 5)
        hida.set_school(school)
        school.apply_special_ability(hida)
        school.apply_rank_three_ability(hida)
        school.apply_rank_four_ability(hida)
        school.apply_rank_five_ability(hida)
        return hida

    def test_recursion_gate_declines_counterattacking_a_counterattack(self) -> None:
        """When the incoming attack action's skill is 'counterattack',
        the HidaCounterattackInterruptStrategy MUST decline (recursion
        gate)."""
        hida = self._build_5th_dan_hida()
        attacker = Character("Attacker")
        attacker.set_actions([1])
        attacker.set_skill("counterattack", 4)
        attacker.set_skill("attack", 4)
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()

        # Build an INCOMING counterattack action targeting the Hida.
        # The incoming "attack" is itself a counterattack — we synthesize
        # this by using CounterattackAction with skill="counterattack".
        attack_init = InitiativeAction([1], 1)

        # Use AttackDeclaredEvent which is the pre-damage decision path.
        # For 5th-Dan Hida this would normally DEFER, but the recursion
        # gate is global (applies to all Dans). To test the recursion
        # gate cleanly, use a Hida that ISN'T 5th Dan (so the strategy
        # falls into the standard pre-damage path).
        pre_5th_dan_hida = Character("Hida2Dan")
        pre_5th_dan_hida.set_actions([5, 8])
        pre_5th_dan_hida.set_skill("attack", 2)
        pre_5th_dan_hida.set_skill("counterattack", 2)
        pre_5th_dan_hida.set_skill("double attack", 2)
        pre_5th_dan_hida.set_skill("iaijutsu", 2)
        pre_5th_dan_hida.set_skill("parry", 2)
        pre_5th_dan_hida.set_skill("wound check", 2)
        pre_5th_dan_hida.set_ring("water", 3)
        pre_5th_dan_hida.set_ring("earth", 2)
        school = hida_school.HidaBushiSchool()
        pre_5th_dan_hida.set_school(school)
        school.apply_special_ability(pre_5th_dan_hida)

        groups2 = [Group("Crab", pre_5th_dan_hida), Group("Enemy", attacker)]
        context2 = EngineContext(groups2, round=1, phase=1)
        context2.initialize()
        placeholder2 = actions.AttackAction(
            pre_5th_dan_hida, attacker, "attack", attack_init, context2,
        )
        incoming2 = actions.CounterattackAction(
            attacker, pre_5th_dan_hida, "counterattack",
            attack_init, context2, placeholder2,
        )

        declared = events.AttackDeclaredEvent(incoming2)
        strategy = pre_5th_dan_hida.interrupt_strategy()
        emitted = list(strategy.recommend(pre_5th_dan_hida, declared, context2))
        # The recursion gate must reject — no SpendActionEvent (no
        # counterattack fired).
        spend_events = [
            e for e in emitted if isinstance(e, events.SpendActionEvent)
        ]
        self.assertEqual(
            0, len(spend_events),
            f"Recursion gate must prevent counterattacking a counterattack; "
            f"got {[type(e).__name__ for e in emitted]}",
        )
        # Defensive: also check no TakeCounterattackActionEvent.
        from simulation.events import TakeCounterattackActionEvent
        ca_events = [
            e for e in emitted if isinstance(e, TakeCounterattackActionEvent)
        ]
        self.assertEqual(0, len(ca_events))

    def test_sw_saturation_gate_declines_at_low_sw_with_inflated_attacker_tn(self) -> None:
        """When the Hida has sw_remaining <= 1 AND the incoming attack
        has _counterattack_roll_bonus > 0 (i.e., the attacker was
        previously raised by a Hida counterattack), the strategy MUST
        decline — better to use 4th Dan SW-for-LW.
        """
        # Build a 2nd-Dan Hida (so the strategy uses the pre-5th-Dan
        # pre-damage decision path).
        hida = Character("Hida")
        hida.set_actions([5, 8])
        hida.set_ring("water", 3)
        hida.set_ring("earth", 2)
        hida.set_skill("attack", 2)
        hida.set_skill("counterattack", 2)
        hida.set_skill("double attack", 2)
        hida.set_skill("iaijutsu", 2)
        hida.set_skill("parry", 2)
        hida.set_skill("wound check", 2)
        school = hida_school.HidaBushiSchool()
        hida.set_school(school)
        school.apply_special_ability(hida)

        # Reduce the Hida to sw_remaining <= 1.
        # max_sw = 2 * earth = 4; take 3 SW → sw_remaining = 1.
        for _ in range(3):
            hida.take_sw(1)
        self.assertEqual(1, hida.sw_remaining())

        attacker = Character("Attacker")
        attacker.set_actions([1])
        attacker.set_skill("attack", 4)
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()

        # Build an incoming ATTACK (not counterattack) with the
        # _counterattack_roll_bonus signal set — i.e., the Hida had
        # previously raised this attacker via the Hida special ability.
        attack_init = InitiativeAction([1], 1)
        incoming = actions.AttackAction(
            attacker, hida, "attack", attack_init, context,
        )
        incoming._counterattack_roll_bonus = 5  # type: ignore[attr-defined]

        declared = events.AttackDeclaredEvent(incoming)
        strategy = hida.interrupt_strategy()
        emitted = list(strategy.recommend(hida, declared, context))
        # SW-saturation gate must reject — no SpendActionEvent.
        spend_events = [
            e for e in emitted if isinstance(e, events.SpendActionEvent)
        ]
        self.assertEqual(
            0, len(spend_events),
            f"SW-saturation gate must prevent counterattacking at low SW "
            f"vs raised attacker; got {[type(e).__name__ for e in emitted]}",
        )

    def test_gates_do_not_block_normal_counterattack(self) -> None:
        """Baseline: a 2nd-Dan Hida at full health receiving a normal,
        non-counterattack incoming attack with NO _counterattack_roll_bonus
        MUST counterattack normally — gates do not over-fire.
        """
        hida = Character("Hida")
        hida.set_actions([5, 8])
        hida.set_ring("water", 3)
        hida.set_ring("earth", 2)
        hida.set_skill("attack", 2)
        hida.set_skill("counterattack", 2)
        hida.set_skill("double attack", 2)
        hida.set_skill("iaijutsu", 2)
        hida.set_skill("parry", 2)
        hida.set_skill("wound check", 2)
        school = hida_school.HidaBushiSchool()
        hida.set_school(school)
        school.apply_special_ability(hida)
        # Full health, full actions — no gate should engage.
        self.assertEqual(hida.sw_remaining(), hida.max_sw())

        attacker = Character("Attacker")
        attacker.set_actions([1])
        attacker.set_skill("attack", 4)
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()

        attack_init = InitiativeAction([1], 1)
        incoming = actions.AttackAction(
            attacker, hida, "attack", attack_init, context,
        )
        # NO _counterattack_roll_bonus set — normal attack.

        declared = events.AttackDeclaredEvent(incoming)
        strategy = hida.interrupt_strategy()
        emitted = list(strategy.recommend(hida, declared, context))
        # Counterattack SHOULD fire — at least one SpendActionEvent.
        spend_events = [
            e for e in emitted if isinstance(e, events.SpendActionEvent)
        ]
        self.assertGreaterEqual(
            len(spend_events), 1,
            f"Baseline counterattack must fire when no gates engage; "
            f"got {[type(e).__name__ for e in emitted]}",
        )
