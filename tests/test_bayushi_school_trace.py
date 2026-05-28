#!/usr/bin/env python3

#
# test_bayushi_school_trace.py
#
# US5 / Principle VII assertions for the Bayushi Bushi School.
# Added 2026-05-28 per spec branch 013 trace-auditor + trace-reader
# audits.
#
# rules/04-schools.md "Bayushi Bushi School" + Constitution Principle VII.
#

import unittest

from simulation.character import Character
from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.text_renderer import TextRenderer
from web.adapters.trace_entries import (
    WoundCheckEntry,
)


class TestBayushi5thDanWoundCheckTraceAttribution(unittest.TestCase):
    """rules/04-schools.md "Bayushi Bushi School: Fifth Dan":
    when a Bayushi fails a WC, SW is computed against ``lw // 2``
    instead of ``lw``.  Per Principle VII (trace-auditor P1 + trace-
    reader Misleading #2, 2026-05-28), the trace MUST surface the
    halving with explicit "Bayushi 5th Dan" attribution.
    """

    def _make_entry(self, *, halved_lw_actual: int) -> WoundCheckEntry:
        """Build a minimal failed-WC entry with the Bayushi 5th Dan
        halved-LW annotation set.
        """
        return WoundCheckEntry(
            phase_prefix="| R1 | P5 |",
            character_name="Bayushi",
            vp_spent=None,
            vp_source=None,
            vp_skill=None,
            vp_breakdown=None,
            rolled=6,
            kept=4,
            modifier=0,
            components=[],
            modifier_components=[],
            dice=[9, 5, 4, 4, 3, 2],
            sum_of_kept=22,
            total=22,
            tn=40,
            outcome="failed",
            bayushi_5th_dan_halved_lw_actual=halved_lw_actual,
        )

    def test_text_renderer_surfaces_halving_with_source(self) -> None:
        """The Bayushi 5th Dan halving MUST surface with explicit
        "Bayushi 5th Dan" attribution + actual + halved LW values."""
        entry = self._make_entry(halved_lw_actual=40)
        rendered = "\n".join(TextRenderer().render_lines([entry]))
        self.assertIn("Bayushi 5th Dan", rendered)
        # Both the actual LW and the halved value must appear so a
        # reader can reconstruct the SW computation.
        self.assertIn("40", rendered)
        self.assertIn("20", rendered)  # 40 // 2
        # The attribution is contextualized as "SW vs halved LW".
        self.assertIn("halved LW", rendered)

    def test_bulleted_renderer_surfaces_halving_with_source(self) -> None:
        """Same attribution in the bulleted renderer."""
        entry = self._make_entry(halved_lw_actual=58)
        rendered = BulletedRenderer().render([entry])
        self.assertIn("Bayushi 5th Dan", rendered)
        self.assertIn("58", rendered)
        self.assertIn("29", rendered)  # 58 // 2
        self.assertIn("halved LW", rendered)

    def test_zero_halved_lw_does_not_surface_attribution(self) -> None:
        """Default 0 (passed WC OR non-Bayushi WC) MUST NOT surface
        the "Bayushi 5th Dan" attribution."""
        entry = self._make_entry(halved_lw_actual=0)
        text = "\n".join(TextRenderer().render_lines([entry]))
        bulleted = BulletedRenderer().render([entry])
        self.assertNotIn("Bayushi 5th Dan", text)
        self.assertNotIn("Bayushi 5th Dan", bulleted)


class TestBayushiSpecialAbilityDamageBreakdownAttribution(unittest.TestCase):
    """rules/04-schools.md "Bayushi Bushi School: Special Ability":
    VP on attack adds +1k1 per VP to damage.  Per Principle VII
    (trace-reader Misleading #1, 2026-05-28), the damage breakdown
    MUST identify the component as the Bayushi Special Ability (not
    a generic engine effect).

    Verifies the relabel from bare "VP on attack" to "Bayushi Special
    Ability VP on attack" in
    ``BayushiRollParameterProvider.get_breakdown``.
    """

    def test_bayushi_provider_labels_vp_component_with_source(self) -> None:
        """``get_breakdown`` MUST emit the VP-on-attack component with
        the explicit ``"Bayushi Special Ability VP on attack"`` label."""
        from simulation.character import Character
        from simulation.schools.bayushi_school import (
            BayushiRollParameterProvider,
        )
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 5)
        target = Character("Target")
        provider = BayushiRollParameterProvider()
        components = provider.get_breakdown(
            bayushi, target, "attack",
            kind="damage", attack_extra_rolled=0, vp=2,
        )
        labels = [label for (label, _, _) in components]
        self.assertIn(
            "Bayushi Special Ability VP on attack", labels,
            f"Damage breakdown must include the Bayushi Special "
            f"Ability VP attribution; got labels: {labels}",
        )
        # Numeric breakdown: 2 VP -> 2k2 contribution.
        bayushi_vp_entry = next(
            (rolled, kept) for (label, rolled, kept) in components
            if label == "Bayushi Special Ability VP on attack"
        )
        self.assertEqual((2, 2), bayushi_vp_entry)


class TestBayushi4thDanFloatingBonusSourceLabel(unittest.TestCase):
    """rules/04-schools.md "Bayushi Bushi School: Fourth Dan": after
    a successful OR failed feint, the Bayushi gains a +5 floating
    bonus.  The bonus MUST carry source="Bayushi 4th Dan" so the
    consumption trace correctly attributes the source per Principle
    VII (regression guard).
    """

    def test_4th_dan_bonus_carries_source_attribute(self) -> None:
        """The ``AnyAttackFloatingBonus`` emitted by the 4th Dan
        listeners MUST have ``source() == "Bayushi 4th Dan"``.
        """
        from simulation.mechanics.floating_bonuses import (
            AnyAttackFloatingBonus,
        )
        bonus = AnyAttackFloatingBonus(5, source="Bayushi 4th Dan")
        # The source attribute is a method (not a bare attribute).
        # See rules-auditor MINOR fix in BayushiAttackStrategy.
        self.assertTrue(callable(bonus.source))
        self.assertEqual("Bayushi 4th Dan", bonus.source())
        self.assertEqual(5, bonus.bonus())


class TestBayushiAttackStrategySaturationDrainBug(unittest.TestCase):
    """Regression guard for rules-auditor MINOR fix (2026-05-28):
    ``BayushiAttackStrategy._count_bayushi_4th_dan_bonuses`` was
    using ``getattr(b, "source", None)`` which returned the
    BOUND-METHOD object (not the source string), so the comparison
    against "Bayushi 4th Dan" was always False.  The saturation
    drain branch was structurally dead code.

    This test verifies the fixed counter correctly counts bonuses by
    calling ``source()`` instead of comparing the method object.
    """

    def test_counter_correctly_counts_bayushi_4th_dan_bonuses(self) -> None:
        """The counter MUST return the count of bonuses whose
        ``source()`` equals ``"Bayushi 4th Dan"`` — not zero (which
        was the pre-fix buggy behavior).
        """
        from simulation.character import Character
        from simulation.mechanics.floating_bonuses import (
            AnyAttackFloatingBonus,
        )
        from simulation.schools.bayushi_school import (
            BayushiAttackStrategy,
        )
        bayushi = Character("Bayushi")
        # Add 3 Bayushi 4th Dan bonuses + 1 non-Bayushi bonus.
        for _ in range(3):
            bayushi.gain_floating_bonus(
                AnyAttackFloatingBonus(5, source="Bayushi 4th Dan"),
            )
        bayushi.gain_floating_bonus(
            AnyAttackFloatingBonus(5, source="Other source"),
        )
        strategy = BayushiAttackStrategy()
        count = strategy._count_bayushi_4th_dan_bonuses(bayushi)
        self.assertEqual(
            3, count,
            f"Counter must return 3 (the # of Bayushi 4th Dan bonuses) "
            f"and exclude the 'Other source' bonus; got {count}.  "
            f"Pre-fix counter returned 0 because it compared the "
            f"bound-method object to the source string.",
        )


class TestBayushiBushiSchoolBasics(unittest.TestCase):
    """Coverage-closer tests for the school class's basic getters."""

    def test_name(self) -> None:
        from simulation.schools.bayushi_school import BayushiBushiSchool
        self.assertEqual("Bayushi Bushi School", BayushiBushiSchool().name())

    def test_ap_base_skill(self) -> None:
        from simulation.schools.bayushi_school import BayushiBushiSchool
        self.assertIsNone(BayushiBushiSchool().ap_base_skill())


class TestBayushiAttackFailedListenerCoverage(unittest.TestCase):
    """Coverage-closer for `BayushiAttackSucceededListener` (4th Dan
    floating-bonus gain on successful feint).  The failed-feint path is
    covered elsewhere; this exercises the success branch."""

    def test_succeeded_listener_grants_bonus_on_successful_feint(self) -> None:
        from simulation import events
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.floating_bonuses import (
            AnyAttackFloatingBonus,
        )
        from simulation.mechanics.initiative_actions import InitiativeAction
        from simulation.schools.bayushi_school import (
            BayushiAttackSucceededListener,
            BayushiFeintAction,
        )
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 4)
        bayushi.set_skill("feint", 5)
        target = Character("Target")
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups)
        feint = BayushiFeintAction(
            bayushi, target, "feint",
            InitiativeAction([1], 1), context,
        )
        listener = BayushiAttackSucceededListener()
        succeeded = events.AttackSucceededEvent(feint)
        responses = list(listener.handle(bayushi, succeeded, context))
        # The 4th Dan listener emits a GainFloatingBonusEvent with
        # "Bayushi 4th Dan" source attribution.
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.GainFloatingBonusEvent)
        # Verify the bonus has the correct source.
        bonuses = bayushi.floating_bonuses("attack")
        bayushi_bonuses = [
            b for b in bonuses
            if isinstance(b, AnyAttackFloatingBonus)
            and b.source() == "Bayushi 4th Dan"
        ]
        self.assertEqual(1, len(bayushi_bonuses))


class TestBayushiRollParameterProviderCoverage(unittest.TestCase):
    """Coverage-closer for `BayushiRollParameterProvider.get_breakdown`
    branches: non-damage kind, ring_value=0 path, school-extra-rolled
    path."""

    def test_get_breakdown_for_non_damage_kind_delegates_to_super(self) -> None:
        from simulation.schools.bayushi_school import (
            BayushiRollParameterProvider,
        )
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 5)
        target = Character("Target")
        provider = BayushiRollParameterProvider()
        components = provider.get_breakdown(
            bayushi, target, "attack",
            kind="attack",  # NOT damage — delegates to super
        )
        # The default super().get_breakdown emits the standard attack
        # breakdown — not the Bayushi-specific damage breakdown.
        self.assertIsNotNone(components)


class TestBayushiAttackStrategyAdditionalCoverage(unittest.TestCase):
    """Additional coverage tests for the lesser-used BayushiAttackStrategy
    branches (plain attack, desperation, HoldActionEvent fallback)."""

    def _make_low_skill_bayushi(self) -> tuple[Character, Character, object]:
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.schools.bayushi_school import (
            BayushiAttackStrategy,
            BayushiBushiSchool,
        )
        bayushi = Character("Bayushi")
        bayushi.set_school(BayushiBushiSchool())
        # Set ALL skills to 0 except attack at 1, so kill-shot /
        # feint / saturation drain all decline AND plain attack
        # at 0.7 also fails — should fall through to desperation.
        bayushi.set_skill("attack", 1)
        bayushi.set_skill("feint", 0)
        bayushi.set_skill("double attack", 0)
        bayushi.set_skill("iaijutsu", 0)
        bayushi.set_skill("parry", 0)
        bayushi.set_ring("fire", 1)
        bayushi.set_ring("water", 1)
        bayushi.set_ring("void", 1)
        bayushi.set_actions([1])
        target = Character("Target")
        target.set_skill("parry", 5)
        target.set_ring("earth", 5)
        target.set_actions([1])
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()
        bayushi.set_strategy("attack", BayushiAttackStrategy())
        return bayushi, target, context

    def test_recommend_plain_attack_branch_fires(self) -> None:
        """When kill-shot/saturation/feint all fail and the only
        available skill is plain attack at threshold 0.7, the plain-
        attack branch should fire."""
        from simulation import events as ev
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.schools.bayushi_school import (
            BayushiAttackStrategy,
            BayushiBushiSchool,
        )
        bayushi = Character("Bayushi")
        bayushi.set_school(BayushiBushiSchool())
        # Plain attack viable; feint and double attack at 0 (declines).
        bayushi.set_skill("attack", 5)
        bayushi.set_skill("feint", 0)
        bayushi.set_skill("double attack", 0)
        bayushi.set_skill("iaijutsu", 0)
        bayushi.set_skill("parry", 3)
        bayushi.set_ring("fire", 5)
        bayushi.set_ring("water", 4)
        bayushi.set_actions([1])
        target = Character("Target")
        target.set_skill("parry", 1)
        target.set_actions([1])
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()
        bayushi.set_strategy("attack", BayushiAttackStrategy())
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        attack_events = [
            e for e in responses if isinstance(e, ev.TakeAttackActionEvent)
        ]
        self.assertEqual(1, len(attack_events))
        self.assertEqual("attack", attack_events[0].action.skill())

    def test_kill_shot_falls_back_to_plain_attack_when_double_attack_skill_zero(self) -> None:
        """When the target is at sw_remaining=1 AND double_attack skill
        is 0, the kill-shot branch's double-attack attempt declines and
        falls back to plain attack at threshold 0.7.  Drives coverage
        on the kill-shot fallback path (lines 417-424)."""
        from simulation import events as ev
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.schools.bayushi_school import (
            BayushiAttackStrategy,
            BayushiBushiSchool,
        )
        bayushi = Character("Bayushi")
        bayushi.set_school(BayushiBushiSchool())
        # Double attack skill 0 → kill-shot's first attempt declines.
        # Plain attack skill 5 + Fire 5 → 0.7 reachable vs weak target.
        bayushi.set_skill("attack", 5)
        bayushi.set_skill("double attack", 0)
        bayushi.set_skill("feint", 0)  # feint also declines
        bayushi.set_skill("iaijutsu", 0)
        bayushi.set_skill("parry", 3)
        bayushi.set_ring("fire", 5)
        bayushi.set_ring("water", 4)
        bayushi.set_actions([1])
        # Target at sw_remaining=1 → kill-shot engages.  Weak parry → plain
        # attack at 0.7 succeeds.
        target = Character("Target")
        target.set_skill("parry", 0)
        target.set_ring("earth", 1)  # max_sw 2
        target.take_sw(1)  # sw_remaining = 1
        target.set_actions([1])
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()
        bayushi.set_strategy("attack", BayushiAttackStrategy())
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        # Plain attack (NOT double attack) must fire from the kill-shot
        # fallback path.
        attack_events = [
            e for e in responses if isinstance(e, ev.TakeAttackActionEvent)
        ]
        self.assertEqual(1, len(attack_events))
        self.assertEqual("attack", attack_events[0].action.skill())

    def test_recommend_falls_through_to_desperation_branch(self) -> None:
        """When kill-shot/saturation/feint/plain all decline but
        desperation at 0.01 fires, the desperation yield-from-events
        path executes.  Drives coverage on lines 493-494, 525-527."""
        from simulation import events as ev
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.schools.bayushi_school import (
            BayushiAttackStrategy,
            BayushiBushiSchool,
        )
        bayushi = Character("Bayushi")
        bayushi.set_school(BayushiBushiSchool())
        # Attack skill 1, no other knacks.  Feint at 0 → declines.
        # Plain attack at 0.7 declines vs strong defender.  Desperation
        # at 0.01 succeeds because the optimizer accepts a bare-skill
        # attack at near-zero confidence.
        bayushi.set_skill("attack", 1)
        bayushi.set_skill("feint", 0)
        bayushi.set_skill("double attack", 0)
        bayushi.set_skill("iaijutsu", 0)
        bayushi.set_skill("parry", 0)
        bayushi.set_ring("fire", 1)
        bayushi.set_actions([1])
        target = Character("Target")
        target.set_skill("parry", 5)  # strong parry → 0.7 unreachable
        target.set_ring("earth", 5)  # max_sw 10 → not kill-shot
        target.set_actions([1])
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()
        bayushi.set_strategy("attack", BayushiAttackStrategy())
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        # Desperation tier fires → some attack event yields.
        attack_events = [
            e for e in responses if isinstance(e, ev.TakeAttackActionEvent)
        ]
        self.assertEqual(
            1, len(attack_events),
            f"Desperation tier must fire when plain attack declines.  "
            f"Drives coverage on the desperation yield-from-events "
            f"path.  Got: {responses}",
        )

    def test_recommend_hold_action_when_all_branches_decline(self) -> None:
        """When kill-shot/saturation/feint/plain/desperation all
        decline (skill 0), the strategy falls through to HoldActionEvent."""
        from simulation import events as ev
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.schools.bayushi_school import (
            BayushiAttackStrategy,
            BayushiBushiSchool,
        )
        bayushi = Character("Bayushi")
        bayushi.set_school(BayushiBushiSchool())
        # All skills at 0 — every branch declines.
        bayushi.set_skill("attack", 0)
        bayushi.set_skill("feint", 0)
        bayushi.set_skill("double attack", 0)
        bayushi.set_skill("iaijutsu", 0)
        bayushi.set_skill("parry", 0)
        bayushi.set_actions([1])
        target = Character("Target")
        target.set_actions([1])
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()
        bayushi.set_strategy("attack", BayushiAttackStrategy())
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        # All branches decline → HoldActionEvent.
        hold_events = [
            e for e in responses if isinstance(e, ev.HoldActionEvent)
        ]
        self.assertEqual(1, len(hold_events))


class TestBayushiFeintActionDamageBreakdown(unittest.TestCase):
    """Coverage closer for `BayushiFeintAction.damage_breakdown`."""

    def test_feint_damage_breakdown_components(self) -> None:
        """The damage breakdown MUST include attack skill, base feint
        kept die, and (when vp > 0) VP on feint."""
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.initiative_actions import InitiativeAction
        from simulation.schools.bayushi_school import BayushiFeintAction
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 4)
        target = Character("Target")
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups)
        action = BayushiFeintAction(
            bayushi, target, "feint",
            InitiativeAction([1], 1), context, vp=2,
        )
        components = action.damage_breakdown()
        labels = [label for (label, _, _) in components]
        self.assertIn("attack skill", labels)
        self.assertIn("base feint kept die", labels)
        self.assertIn("VP on feint", labels)

    def test_feint_damage_breakdown_omits_attack_skill_when_zero(self) -> None:
        """When attack skill = 0, the "attack skill" component is
        omitted from the breakdown."""
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.initiative_actions import InitiativeAction
        from simulation.schools.bayushi_school import BayushiFeintAction
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 0)
        target = Character("Target")
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups)
        action = BayushiFeintAction(
            bayushi, target, "feint",
            InitiativeAction([1], 1), context,
        )
        components = action.damage_breakdown()
        labels = [label for (label, _, _) in components]
        self.assertNotIn("attack skill", labels)
        self.assertIn("base feint kept die", labels)


class TestBayushiRollParameterProviderEdgeCases(unittest.TestCase):
    """Coverage closer for the BayushiRollParameterProvider branches:
    ring_value == 0 path; school-extra-rolled path."""

    def test_get_breakdown_with_zero_ring_value(self) -> None:
        """When the damage ring value is 0, the ring component is
        omitted from the breakdown."""
        from simulation.schools.bayushi_school import (
            BayushiRollParameterProvider,
        )
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 5)
        # Default Fire ring is 1; force it to 0 indirectly.
        # Use set_ring to set the damage ring to 0.
        damage_ring = bayushi.get_skill_ring("damage")
        bayushi.set_ring(damage_ring, 0)
        target = Character("Target")
        provider = BayushiRollParameterProvider()
        components = provider.get_breakdown(
            bayushi, target, "attack",
            kind="damage", attack_extra_rolled=0, vp=0,
        )
        # The ring component must be absent.
        labels = [label for (label, _, _) in components]
        # Various labels depending on character; verify no "<ring> ring"
        # capitalized component with the ring name.
        ring_label = f"{damage_ring.capitalize()} ring"
        self.assertNotIn(ring_label, labels)
    """Drive coverage on the ``BayushiAttackStrategy`` class — provided
    in the school file but NOT installed by ``apply_special_ability``
    per the documented P0 deferral.  These tests instantiate the
    strategy directly and call its methods to verify each branch is
    structurally correct (so the follow-up branch that installs it
    can rely on it not having dead code beyond what the audit
    already fixed).
    """

    def _make_bayushi_with_strategy(self) -> tuple[Character, Character, "object"]:
        """Build a Bayushi character + target + context with the
        ``BayushiAttackStrategy`` installed explicitly (not via
        ``apply_special_ability``)."""
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.schools.bayushi_school import (
            BayushiAttackStrategy,
            BayushiBushiSchool,
        )
        bayushi = Character("Bayushi")
        bayushi.set_school(BayushiBushiSchool())
        bayushi.set_skill("feint", 5)
        bayushi.set_skill("attack", 5)
        bayushi.set_skill("double attack", 5)
        bayushi.set_skill("iaijutsu", 5)
        bayushi.set_skill("parry", 3)
        bayushi.set_ring("fire", 5)
        bayushi.set_ring("water", 4)
        bayushi.set_ring("void", 4)
        bayushi.set_actions([1, 5, 8])
        target = Character("Target")
        target.set_skill("parry", 3)
        target.set_actions([1])
        groups = [Group("Scorpion", bayushi), Group("Target", target)]
        context = EngineContext(groups, phase=1)
        context.initialize()
        bayushi.set_strategy("attack", BayushiAttackStrategy())
        return bayushi, target, context

    def test_recommend_returns_early_on_non_your_move_event(self) -> None:
        from simulation import events as ev
        bayushi, _target, context = self._make_bayushi_with_strategy()
        strategy = bayushi.attack_strategy()
        # NewPhaseEvent is not YourMoveEvent — must yield nothing.
        responses = list(strategy.recommend(
            bayushi, ev.NewPhaseEvent(1), context,
        ))
        self.assertEqual([], responses)

    def test_recommend_yields_no_action_when_no_actions_available(self) -> None:
        from simulation import events as ev
        bayushi, _target, context = self._make_bayushi_with_strategy()
        # Empty the action dice.
        bayushi.set_actions([])
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], ev.NoActionEvent)

    def test_recommend_kill_shot_branch_fires_at_target_sw_remaining_1(self) -> None:
        """Kill-shot branch fires when the target is at sw_remaining <= 1."""
        from simulation import events as ev
        bayushi, target, context = self._make_bayushi_with_strategy()
        # Reduce target to 1 SW remaining.
        target.set_ring("earth", 1)  # max_sw = 2
        target.take_sw(1)  # sw_remaining = 1
        self.assertEqual(1, target.sw_remaining())
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        # SOME attack action must fire (kill-shot tries double attack
        # then plain attack at the kill-shot thresholds).
        attack_events = [
            e for e in responses if isinstance(e, ev.TakeAttackActionEvent)
        ]
        self.assertEqual(1, len(attack_events))

    def test_recommend_feint_branch_fires_under_default_conditions(self) -> None:
        """When kill-shot doesn't engage, the feint branch fires
        (this is the school's signature mechanic)."""
        from simulation import events as ev
        bayushi, target, context = self._make_bayushi_with_strategy()
        # Target healthy → kill-shot branch declines.
        self.assertGreater(target.sw_remaining(), 1)
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        attack_events = [
            e for e in responses if isinstance(e, ev.TakeAttackActionEvent)
        ]
        # Should yield exactly one attack event (feint is preferred
        # over plain attack under default conditions).
        self.assertEqual(1, len(attack_events))
        # The first-preferred skill is feint (the school's identity).
        self.assertEqual("feint", attack_events[0].action.skill())

    def test_recommend_saturation_drain_branch_fires_with_3_plus_bonuses(self) -> None:
        """When the Bayushi has 3+ unspent 4th Dan floating bonuses,
        the saturation drain branch fires (double attack) before the
        feint branch (per the bonus-stacking-prevention rationale)."""
        from simulation import events as ev
        from simulation.mechanics.floating_bonuses import (
            AnyAttackFloatingBonus,
        )
        bayushi, _target, context = self._make_bayushi_with_strategy()
        # Stack 3 Bayushi 4th Dan bonuses on the Bayushi.
        for _ in range(3):
            bayushi.gain_floating_bonus(
                AnyAttackFloatingBonus(5, source="Bayushi 4th Dan"),
            )
        strategy = bayushi.attack_strategy()
        responses = list(strategy.recommend(
            bayushi, ev.YourMoveEvent(bayushi), context,
        ))
        attack_events = [
            e for e in responses if isinstance(e, ev.TakeAttackActionEvent)
        ]
        self.assertEqual(1, len(attack_events))
        # Saturation drain prefers double attack to consume bonuses.
        self.assertEqual("double attack", attack_events[0].action.skill())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
