#!/usr/bin/env python3

#
# test_ishi_school.py
#
# Unit tests for the Isawa Ishi School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.formation import LineFormation
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_params import DefaultRollParameterProvider
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import akodo_school, ishi_school, mirumoto_school
from simulation.strategies.base import PlainAttackStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIshiSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual("Isawa Ishi School", school.name())

    def test_extra_rolled(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual(["precepts", "wound check", "initiative"], school.extra_rolled())

    def test_school_ring(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual("void", school.school_ring())

    def test_school_knacks(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual(["absorb void", "kharmic spin", "otherworldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        # rules/04-schools.md "Isawa Ishi School: 2nd Dan" — free raise on
        # the school's signature skill ``precepts`` (see specs/002 OPEN_QUESTIONS Q2).
        school = ishi_school.IsawaIshiSchool()
        self.assertEqual(["precepts"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = ishi_school.IsawaIshiSchool()
        self.assertIsNone(school.ap_base_skill())


class TestIshiMaxVPProvider(unittest.TestCase):
    def test_max_vp_uses_highest_ring_plus_school_rank(self):
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        provider = ishi_school.IshiMaxVPProvider(school_rank=2)
        # highest ring = 4 (void), school rank = 2 -> 6
        self.assertEqual(6, provider.max_vp(ishi))

    def test_max_vp_per_roll_uses_lowest_ring_minus_1(self):
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        provider = ishi_school.IshiMaxVPProvider()
        # lowest ring = 2, minus 1 -> 1
        self.assertEqual(1, provider.max_vp_per_roll(ishi))

    def test_max_vp_per_roll_never_negative(self):
        ishi = Character("Ishi")
        # All rings default to 2, so min is 2
        provider = ishi_school.IshiMaxVPProvider()
        # lowest ring = 2, minus 1 -> 1
        self.assertEqual(1, provider.max_vp_per_roll(ishi))

    def test_special_ability_sets_provider(self):
        ishi = Character("Ishi")
        ishi.set_ring("void", 4)
        school = ishi_school.IsawaIshiSchool()
        school.apply_special_ability(ishi)
        # Max VP should use Ishi formula
        # highest ring = 4 (void), school rank = 1 -> 5
        self.assertEqual(5, ishi.max_vp())
        # Max VP per roll = lowest ring - 1 = 2 - 1 = 1
        self.assertEqual(1, ishi.max_vp_per_roll())

    def test_vp_calculation_differs_from_standard(self):
        """Verify Ishi VP is different from standard calculation."""
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        # Standard: min(rings) + worldliness = 2 + 0 = 2
        self.assertEqual(2, ishi.max_vp())
        # Now apply Ishi special
        school = ishi_school.IsawaIshiSchool()
        school.apply_special_ability(ishi)
        # Ishi: max(rings) + school_rank = 4 + 1 = 5
        self.assertEqual(5, ishi.max_vp())


class TestIshiFirstDanExtraDice(unittest.TestCase):
    """1st Dan: +1 rolled die on precepts, wound check, initiative.

    rules/04-schools.md "Isawa Ishi School: 1st Dan" — extra rolled die on
    the school's signature skill (precepts) plus two more (wound check +
    initiative per specs/002 OPEN_QUESTIONS Q1).
    """

    def _build_first_dan_ishi(self) -> Character:
        ishi = Character("Ishi")
        # Use a uniform mid ring so rolled-dice deltas are easy to read.
        ishi.set_ring("air", 3)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 3)
        ishi.set_ring("void", 3)
        ishi.set_skill("precepts", 2)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_rank_one_ability(ishi)
        return ishi

    def _build_baseline(self) -> Character:
        """Same ring/skill profile, but with NO school applied."""
        plain = Character("Plain")
        plain.set_ring("air", 3)
        plain.set_ring("earth", 3)
        plain.set_ring("fire", 3)
        plain.set_ring("water", 3)
        plain.set_ring("void", 3)
        plain.set_skill("precepts", 2)
        return plain

    def test_precepts_extra_rolled_die(self):
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline()
        # extra_rolled is the public accessor used by the provider.
        self.assertEqual(1, ishi.extra_rolled("precepts"))
        self.assertEqual(0, baseline.extra_rolled("precepts"))

    def test_wound_check_extra_rolled_die(self):
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline()
        self.assertEqual(1, ishi.extra_rolled("wound check"))
        self.assertEqual(0, baseline.extra_rolled("wound check"))

    def test_initiative_extra_rolled_die(self):
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline()
        self.assertEqual(1, ishi.extra_rolled("initiative"))
        self.assertEqual(0, baseline.extra_rolled("initiative"))

    def test_precepts_roll_has_one_more_rolled_die_via_provider(self):
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline()
        provider = DefaultRollParameterProvider()
        # Use precepts' default ring (void). Target is irrelevant.
        ishi_rolled, _ishi_kept, _ = provider.get_skill_roll_params(
            ishi, None, "precepts", ring=ishi.ring("void"),
        )
        base_rolled, _base_kept, _ = provider.get_skill_roll_params(
            baseline, None, "precepts", ring=baseline.ring("void"),
        )
        self.assertEqual(base_rolled + 1, ishi_rolled)

    def test_initiative_roll_has_one_more_rolled_die_via_provider(self):
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline()
        provider = DefaultRollParameterProvider()
        ishi_rolled, _ishi_kept, _ = provider.get_initiative_roll_params(ishi)
        base_rolled, _base_kept, _ = provider.get_initiative_roll_params(baseline)
        self.assertEqual(base_rolled + 1, ishi_rolled)

    def test_wound_check_roll_has_one_more_rolled_die_via_provider(self):
        """Verify the dedicated wound-check path also picks up the +1 die."""
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline()
        provider = DefaultRollParameterProvider()
        ishi_rolled, _ishi_kept, _ = provider.get_wound_check_roll_params(ishi)
        base_rolled, _base_kept, _ = provider.get_wound_check_roll_params(baseline)
        self.assertEqual(base_rolled + 1, ishi_rolled)


class TestIshiAllyBoostListener(unittest.TestCase):
    """3rd Dan: spend 1 VP to add Xk1 to an ally's failing roll.

    rules/04-schools.md "Isawa Ishi School: 3rd Dan". The listener now
    delegates the decision to the pluggable ``ishi_ally_boost`` strategy
    (Constitution Principle V); these tests drive the full apply chain so
    both the strategy and the chained engine-default behavior are exercised.
    """

    def setUp(self):
        self.ishi = Character("Ishi")
        self.ishi.set_skill("precepts", 3)
        self.ishi.set_actions([1])
        # Apply the 3rd Dan ability to install both the strategy and the
        # chained listener — this is the integration surface that the
        # listener tests now exercise (not the bare listener with no
        # strategy installed).
        school = ishi_school.IsawaIshiSchool()
        self.ishi.set_school(school)
        school.apply_special_ability(self.ishi)
        school.apply_rank_three_ability(self.ishi)
        self.ally = Character("Ally")
        self.ally.set_actions([1])
        # Make the enemy easy to hit (parry 0 -> tn_to_hit = 5) so we can
        # set up rolls clearly above or below TN.
        self.enemy = Character("Enemy")
        self.enemy.set_skill("parry", 0)
        self.enemy.set_actions([1])
        groups = [Group("Phoenix", [self.ishi, self.ally]), Group("Enemy", self.enemy)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def _make_attack_event(self, subject, target, skill_roll):
        action = actions.AttackAction(
            subject, target, "attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(skill_roll)
        return action, events.AttackRolledEvent(action, skill_roll)

    def test_boost_ally_failing_attack(self):
        """Ally rolls below TN; Ishi spends 1 VP and adds Xk1 to push the
        roll up. The event's roll and the action's skill_roll are both
        mutated in-place."""
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("precepts", 8)
        self.ishi.set_roll_provider(roll_provider)
        # Enemy TN = 5 (parry=0); roll 3 fails.
        action, event = self._make_attack_event(self.ally, self.enemy, 3)
        # Use the slot the school installed (attack_rolled).
        listener = self.ishi._listeners["attack_rolled"]
        responses = list(listener.handle(self.ishi, event, self.context))
        # Among the responses, exactly one SpendVoidPointsEvent (1 VP) for
        # the ally boost.
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(spends))
        self.assertEqual(1, spends[0].amount)
        # The event's roll and the action's skill_roll were mutated.
        self.assertEqual(11, event.roll)  # 3 + 8 = 11
        self.assertEqual(11, action.skill_roll())
        # The action is tagged for the once-per-roll guard and trace
        # attribution (web/adapters/modifier_breakdown.py reads these).
        self.assertIs(self.ishi, action._ishi_boosted_by)
        self.assertEqual(8, action._ishi_boost_value)

    def test_no_boost_when_roll_already_succeeds(self):
        """If the ally's roll already meets/exceeds TN, the Ishi abstains
        — no point spending VP on a roll that doesn't need it."""
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("precepts", 8)
        self.ishi.set_roll_provider(roll_provider)
        # Enemy TN = 5; roll 25 already succeeds.
        _action, event = self._make_attack_event(self.ally, self.enemy, 25)
        listener = self.ishi._listeners["attack_rolled"]
        responses = list(listener.handle(self.ishi, event, self.context))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(spends))

    def test_no_boost_for_enemies(self):
        """Enemy attack — Ishi observes via chained listener but does NOT
        spend VP to boost (the rules-text "another character" is interpreted
        as ally-only per OPEN_QUESTIONS.md Q3)."""
        _action, event = self._make_attack_event(self.enemy, self.ally, 3)
        listener = self.ishi._listeners["attack_rolled"]
        responses = list(listener.handle(self.ishi, event, self.context))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(spends))

    def test_no_boost_for_self(self):
        """Self-attack — Ishi does not boost their own roll ("another
        character" excludes self)."""
        _action, event = self._make_attack_event(self.ishi, self.enemy, 3)
        listener = self.ishi._listeners["attack_rolled"]
        responses = list(listener.handle(self.ishi, event, self.context))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(spends))

    def test_no_boost_when_no_vp(self):
        """No VP available — listener abstains even when the ally's roll
        is failing."""
        self.ishi.spend_vp(self.ishi.vp())
        _action, event = self._make_attack_event(self.ally, self.enemy, 3)
        listener = self.ishi._listeners["attack_rolled"]
        responses = list(listener.handle(self.ishi, event, self.context))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(spends))

    def test_once_per_roll_guard_blocks_second_boost(self):
        """rules/04-schools.md "Isawa Ishi School: 3rd Dan": "may only be
        done once per roll". A second listener invocation on the same
        action must NOT spend VP again."""
        roll_provider = CalvinistRollProvider()
        # Two precepts rolls queued: first one fires, second must NOT.
        roll_provider.put_skill_roll("precepts", 8)
        roll_provider.put_skill_roll("precepts", 8)
        self.ishi.set_roll_provider(roll_provider)
        action, event = self._make_attack_event(self.ally, self.enemy, 3)
        listener = self.ishi._listeners["attack_rolled"]
        responses1 = list(listener.handle(self.ishi, event, self.context))
        # First fire: spent.
        spends1 = [r for r in responses1 if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(spends1))
        self.assertEqual(11, action.skill_roll())
        # Replay the event (e.g., a second Ishi observer would fire);
        # the guard MUST prevent a second spend.
        responses2 = list(listener.handle(self.ishi, event, self.context))
        spends2 = [r for r in responses2 if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(spends2))
        self.assertEqual(11, action.skill_roll())

    def test_no_adjacency_required(self):
        """rules/04-schools.md "Isawa Ishi School: 3rd Dan" has no
        adjacency requirement (OPEN_QUESTIONS.md Q3: the skeleton's
        ``is_adjacent`` check was an unfounded restriction and has been
        dropped). Non-adjacent in-group allies still benefit."""
        # Construct a 3-character formation where the Ishi is not adjacent
        # to the ally; verify the boost still fires.
        ishi = Character("Ishi")
        ishi.set_skill("precepts", 3)
        ishi.set_actions([1])
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_three_ability(ishi)
        filler = Character("Filler")
        filler.set_actions([1])
        ally = Character("Ally")
        ally.set_actions([1])
        enemy = Character("Enemy")
        enemy.set_skill("parry", 0)
        enemy.set_actions([1])
        formation = LineFormation([[ishi, filler, ally], [enemy]])
        groups = [
            Group("Phoenix", [ishi, filler, ally]),
            Group("Enemy", enemy),
        ]
        context = EngineContext(groups, formation=formation)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("precepts", 8)
        ishi.set_roll_provider(roll_provider)
        initiative_action = InitiativeAction([1], 1)
        action = actions.AttackAction(
            ally, enemy, "attack", initiative_action, context,
        )
        action.set_skill_roll(3)
        event = events.AttackRolledEvent(action, 3)
        listener = ishi._listeners["attack_rolled"]
        responses = list(listener.handle(ishi, event, context))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        # Adjacency is no longer required — the boost still fires.
        self.assertEqual(1, len(spends))
        self.assertEqual(11, action.skill_roll())


class TestIshiAllyBoostListenerChaining(unittest.TestCase):
    """The Ishi 3rd Dan listener must CHAIN to the engine default so the
    standard interrupt/observation cascade (parry-on-attack) still fires
    for non-attack-subject characters. This is bug #1 from
    OPEN_QUESTIONS.md Q4 audit ("listener REPLACED engine default ->
    broke interrupt cascade")."""

    def test_attack_rolled_chains_to_engine_default(self):
        """When an enemy attacks our ally, the chained listener (a) runs
        the engine default's interrupt-strategy delegation, (b) does NOT
        boost. The interrupt-strategy is consulted on the event so the
        Ishi can parry on behalf of the ally if their strategy chooses."""
        ishi = Character("Ishi")
        ishi.set_skill("precepts", 3)
        ishi.set_actions([1])
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_three_ability(ishi)
        ally = Character("Ally")
        ally.set_actions([1])
        enemy = Character("Enemy")
        enemy.set_skill("parry", 0)
        enemy.set_actions([1])
        groups = [Group("Phoenix", [ishi, ally]), Group("Enemy", enemy)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        action = actions.AttackAction(
            enemy, ally, "attack", initiative_action, context,
        )
        action.set_skill_roll(20)
        event = events.AttackRolledEvent(action, 20)
        listener = ishi._listeners["attack_rolled"]
        # Run the listener; just verify the chain calls the engine default
        # (knowledge.observe_attack_roll fires) and no boost is yielded.
        list(listener.handle(ishi, event, context))
        # No exception and no boost VP spend (since the attack is from an
        # enemy, not for an ally).
        # Verify that the chained listener observed the attack roll
        # (engine default's AttackRolledListener calls
        # ``knowledge().observe_attack_roll``; verify via the averaging
        # accessor which falls back to 27 if no observation exists).
        self.assertEqual(20, ishi.knowledge().average_attack_roll(enemy))


class TestEagerAllyBoostStrategy(unittest.TestCase):
    """Unit tests for the pluggable 3rd Dan decision strategy.

    rules/04-schools.md "Isawa Ishi School: 3rd Dan": "Spend 1 Void Point to
    add Xk1 to another character's roll, where X is your Precepts skill. May
    only be done once per roll."

    These tests exercise the strategy directly (no listener chaining) so
    the decision logic is isolated. Per Constitution Principle V, the
    strategy must be swappable; per Principle IV, dice flow through the
    injectable roll provider only.
    """

    def _build_ishi_with_strategy(self):
        from simulation.strategies.ishi_dan_abilities import EagerAllyBoostStrategy
        ishi = Character("Ishi")
        ishi.set_skill("precepts", 3)
        ally = Character("Ally")
        enemy = Character("Enemy")
        enemy.set_skill("parry", 0)  # tn_to_hit = 5
        groups = [Group("Phoenix", [ishi, ally]), Group("Enemy", enemy)]
        context = EngineContext(groups)
        roll_provider = CalvinistRollProvider()
        ishi.set_roll_provider(roll_provider)
        return ishi, ally, enemy, context, roll_provider, EagerAllyBoostStrategy()

    def _make_attack_event(self, subject, target, context, roll):
        action = actions.AttackAction(
            subject, target, "attack", InitiativeAction([1], 1), context,
        )
        action.set_skill_roll(roll)
        return action, events.AttackRolledEvent(action, roll)

    def test_fires_on_failing_attack(self):
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        _action, event = self._make_attack_event(ally, enemy, ctx, 3)
        responses = list(strat.recommend(ishi, event, ctx))
        # Strategy yields a single SpendVoidPointsEvent (1 VP).
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.SpendVoidPointsEvent)
        self.assertEqual(1, responses[0].amount)
        # Event roll mutated to 3 + 8 = 11.
        self.assertEqual(11, event.roll)

    def test_no_fire_when_already_succeeding(self):
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        _action, event = self._make_attack_event(ally, enemy, ctx, 25)
        responses = list(strat.recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))
        # Roll unchanged.
        self.assertEqual(25, event.roll)

    def test_no_fire_for_self_subject(self):
        ishi, _ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        _action, event = self._make_attack_event(ishi, enemy, ctx, 3)
        responses = list(strat.recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_for_enemy_subject(self):
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        _action, event = self._make_attack_event(enemy, ally, ctx, 3)
        responses = list(strat.recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_when_no_vp(self):
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        ishi.spend_vp(ishi.vp())
        rp.put_skill_roll("precepts", 8)
        _action, event = self._make_attack_event(ally, enemy, ctx, 3)
        responses = list(strat.recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_when_no_precepts(self):
        ishi, ally, enemy, ctx, _rp, strat = self._build_ishi_with_strategy()
        ishi.set_skill("precepts", 0)
        _action, event = self._make_attack_event(ally, enemy, ctx, 3)
        responses = list(strat.recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_when_already_boosted(self):
        """Once-per-roll guard: ``_ishi_boosted_by`` tag blocks re-fire."""
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        action, event = self._make_attack_event(ally, enemy, ctx, 3)
        # Pre-tag the action as if a prior Ishi already boosted.
        action._ishi_boosted_by = ishi
        responses = list(strat.recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_on_unrelated_event_type(self):
        """The strategy only handles supported combat roll events."""
        ishi, _ally, _enemy, ctx, _rp, strat = self._build_ishi_with_strategy()
        # NewRoundEvent is not a combat roll event.
        unrelated = events.NewRoundEvent(round=1)
        responses = list(strat.recommend(ishi, unrelated, ctx))
        self.assertEqual(0, len(responses))

    def test_fires_on_parry_rolled_event(self):
        """Ally's parry roll below TN — strategy fires on ParryRolledEvent."""
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        # Build a parry action: the ally parries an enemy attack.
        ia = InitiativeAction([1], 1)
        attack_action = actions.AttackAction(
            enemy, ally, "attack", ia, ctx,
        )
        attack_action.set_skill_roll(50)  # high attack roll, parry TN = 50
        parry_action = actions.ParryAction(
            ally, enemy, "parry", ia, ctx, attack_action,
        )
        parry_action.set_skill_roll(10)  # parry roll well below TN 50
        event = events.ParryRolledEvent(parry_action, 10)
        responses = list(strat.recommend(ishi, event, ctx))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(spends))
        self.assertEqual(18, event.roll)  # 10 + 8

    def test_fires_on_counterattack_rolled_event(self):
        """Ally's counterattack roll below TN — strategy fires on
        CounterattackRolledEvent."""
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        ia = InitiativeAction([1], 1)
        # Set the enemy's parry skill so the counterattack TN is high.
        enemy.set_skill("parry", 3)
        attack_action = actions.AttackAction(
            enemy, ally, "attack", ia, ctx,
        )
        ca_action = actions.CounterattackAction(
            ally, enemy, "counterattack", ia, ctx, attack_action,
        )
        ca_action.set_skill_roll(5)  # well below TN = 20 + 15 = 35
        event = events.CounterattackRolledEvent(ca_action, 5)
        responses = list(strat.recommend(ishi, event, ctx))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(spends))
        self.assertEqual(13, event.roll)

    def test_fires_on_wound_check_rolled_event(self):
        """Ally's wound check roll below TN — strategy fires on
        WoundCheckRolledEvent. The tags attach to the event itself
        because WoundCheckRolledEvent has no ``action`` attribute."""
        ishi, ally, enemy, ctx, rp, strat = self._build_ishi_with_strategy()
        rp.put_skill_roll("precepts", 8)
        event = events.WoundCheckRolledEvent(
            ally, enemy, damage=30, roll=10, tn=20,
        )
        responses = list(strat.recommend(ishi, event, ctx))
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(spends))
        self.assertEqual(18, event.roll)
        # Tags should be on the event since the wound-check event has no
        # action attribute.
        self.assertIs(ishi, event._ishi_boosted_by)
        self.assertEqual(8, event._ishi_boost_value)


class TestIshiUS3Integration(unittest.TestCase):
    """End-to-end integration: full apply chain + CombatEngine + Calvinist
    dice should cause the 3rd Dan boost to fire on a failing ally roll.

    rules/04-schools.md "Isawa Ishi School: 3rd Dan" (FR for US3).
    """

    def _build_third_dan_ishi(self) -> Character:
        ishi = Character("Ishi")
        ishi.set_ring("air", 3)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 3)
        ishi.set_ring("void", 4)
        ishi.set_skill("precepts", 3)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        school.apply_rank_three_ability(ishi)
        return ishi

    def test_boost_fires_on_failing_ally_attack_roll(self):
        """Ally attacks an enemy below TN; Ishi's strategy + chained
        listener spend 1 VP and add Xk1 to push the roll up."""
        ishi = self._build_third_dan_ishi()
        ally = Character("Ally")
        enemy = Character("Enemy")
        enemy.set_skill("parry", 0)  # tn_to_hit = 5
        groups = [Group("Phoenix", [ishi, ally]), Group("Enemy", enemy)]
        context = EngineContext(groups)
        # Pre-queue dice via CalvinistRollProvider for the Ishi's precepts
        # roll. The k1 result will be added to the ally's roll.
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("precepts", 9)
        ishi.set_roll_provider(roll_provider)
        # Construct a failing attack roll for the ally.
        ia = InitiativeAction([1], 1)
        action = actions.AttackAction(ally, enemy, "attack", ia, context)
        action.set_skill_roll(2)  # well below TN = 5
        event = events.AttackRolledEvent(action, 2)
        # Drive the integration path: invoke the listener installed on
        # the Ishi's attack_rolled slot.
        starting_vp = ishi.vp()
        responses = list(
            ishi._listeners["attack_rolled"].handle(ishi, event, context),
        )
        # Verify the SpendVoidPointsEvent was yielded.
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(spends), "Expected one VP spend for ally boost")
        self.assertEqual(1, spends[0].amount)
        # Verify the action's roll was bumped (2 + 9 = 11, above TN = 5).
        self.assertEqual(11, action.skill_roll())
        self.assertEqual(11, event.roll)
        # Apply the SpendVoidPointsEvent to verify it actually drains a VP.
        ishi.spend_vp(spends[0].amount)
        self.assertEqual(starting_vp - 1, ishi.vp())

    def test_second_invocation_blocked_by_once_per_roll_guard(self):
        """A second invocation of the listener on the same event must not
        spend again (rules/04-schools.md "may only be done once per roll").
        """
        ishi = self._build_third_dan_ishi()
        ally = Character("Ally")
        enemy = Character("Enemy")
        enemy.set_skill("parry", 0)
        groups = [Group("Phoenix", [ishi, ally]), Group("Enemy", enemy)]
        context = EngineContext(groups)
        roll_provider = CalvinistRollProvider()
        # Queue TWO precepts rolls; only the first should be consumed.
        roll_provider.put_skill_roll("precepts", 9)
        roll_provider.put_skill_roll("precepts", 9)
        ishi.set_roll_provider(roll_provider)
        ia = InitiativeAction([1], 1)
        action = actions.AttackAction(ally, enemy, "attack", ia, context)
        action.set_skill_roll(2)
        event = events.AttackRolledEvent(action, 2)
        # First invocation: should fire.
        first = list(
            ishi._listeners["attack_rolled"].handle(ishi, event, context),
        )
        first_spends = [r for r in first if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(first_spends))
        self.assertEqual(11, action.skill_roll())
        # Second invocation: must NOT fire (the once-per-roll guard).
        second = list(
            ishi._listeners["attack_rolled"].handle(ishi, event, context),
        )
        second_spends = [r for r in second if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertEqual(0, len(second_spends))
        # Roll unchanged from after the first boost.
        self.assertEqual(11, action.skill_roll())


class TestIshiFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        ishi = Character("Ishi")
        ishi.set_ring("void", 3)
        school = ishi_school.IsawaIshiSchool()
        school.apply_rank_four_ability(ishi)
        self.assertEqual(4, ishi.ring("void"))


class TestIshiMaxVPProviderEdgeCases(unittest.TestCase):
    """
    Edge case unit tests for IshiMaxVPProvider.

    Rules clause (rules/04-schools.md "Isawa Ishi School: Special Ability"):
      max_vp = highest_ring + school_rank
      max_vp_per_roll = lowest_ring - 1 (never negative)
    """

    def _make_ishi(self, air: int, earth: int, fire: int, water: int, void: int) -> Character:
        ishi = Character("Ishi")
        ishi.set_ring("air", air)
        ishi.set_ring("earth", earth)
        ishi.set_ring("fire", fire)
        ishi.set_ring("water", water)
        ishi.set_ring("void", void)
        return ishi

    def test_max_vp_balanced_rings(self):
        """Balanced 3/3/3/3/3 with school_rank=2 -> highest(3) + 2 = 5."""
        ishi = self._make_ishi(3, 3, 3, 3, 3)
        provider = ishi_school.IshiMaxVPProvider(school_rank=2)
        self.assertEqual(5, provider.max_vp(ishi))

    def test_max_vp_spiked_rings(self):
        """Spiked 5/2/2/2/2 with school_rank=3 -> highest(5) + 3 = 8."""
        ishi = self._make_ishi(5, 2, 2, 2, 2)
        provider = ishi_school.IshiMaxVPProvider(school_rank=3)
        self.assertEqual(8, provider.max_vp(ishi))

    def test_max_vp_void_led(self):
        """Void-led 4/3/3/3/3 with school_rank=3 -> highest(4) + 3 = 7."""
        ishi = self._make_ishi(3, 3, 3, 3, 4)
        provider = ishi_school.IshiMaxVPProvider(school_rank=3)
        self.assertEqual(7, provider.max_vp(ishi))

    def test_max_vp_per_roll_various_lowest(self):
        """max_vp_per_roll = lowest_ring - 1 (lowest = 2 -> 1, lowest = 3 -> 2)."""
        ishi_low_2 = self._make_ishi(2, 4, 3, 5, 4)
        provider = ishi_school.IshiMaxVPProvider()
        self.assertEqual(1, provider.max_vp_per_roll(ishi_low_2))

        ishi_low_3 = self._make_ishi(3, 4, 3, 5, 4)
        self.assertEqual(2, provider.max_vp_per_roll(ishi_low_3))

    def test_max_vp_per_roll_lowest_ring_one_yields_zero(self):
        """Boundary: lowest_ring = 1 -> max_vp_per_roll = max(0, 1-1) = 0."""
        ishi = self._make_ishi(1, 3, 3, 3, 3)
        provider = ishi_school.IshiMaxVPProvider()
        self.assertEqual(0, provider.max_vp_per_roll(ishi))

    def test_max_vp_school_rank_zero(self):
        """Edge case: school_rank=0 -> max_vp = highest_ring + 0 = highest_ring."""
        ishi = self._make_ishi(2, 2, 2, 2, 4)
        provider = ishi_school.IshiMaxVPProvider(school_rank=0)
        self.assertEqual(4, provider.max_vp(ishi))

    def test_set_school_rank_updates_max_vp(self):
        """set_school_rank(N) updates the school_rank used in max_vp."""
        ishi = self._make_ishi(2, 2, 2, 2, 4)
        provider = ishi_school.IshiMaxVPProvider(school_rank=1)
        # highest(4) + 1 = 5
        self.assertEqual(5, provider.max_vp(ishi))
        provider.set_school_rank(3)
        # highest(4) + 3 = 7
        self.assertEqual(7, provider.max_vp(ishi))
        provider.set_school_rank(5)
        # highest(4) + 5 = 9
        self.assertEqual(9, provider.max_vp(ishi))

    def test_set_school_rank_does_not_affect_max_vp_per_roll(self):
        """set_school_rank affects max_vp but not max_vp_per_roll (which uses lowest ring only)."""
        ishi = self._make_ishi(2, 3, 3, 3, 4)
        provider = ishi_school.IshiMaxVPProvider(school_rank=1)
        before = provider.max_vp_per_roll(ishi)
        provider.set_school_rank(5)
        after = provider.max_vp_per_roll(ishi)
        self.assertEqual(before, after)
        self.assertEqual(1, after)  # lowest(2) - 1 = 1


class TestIshiSpecialAbilityIntegration(unittest.TestCase):
    """
    End-to-end integration tests verifying that the Isawa Ishi Special
    Ability is correctly installed via the full apply chain and that
    Character.max_vp() / Character.max_vp_per_roll() route through
    IshiMaxVPProvider.

    Rules clause (rules/04-schools.md "Isawa Ishi School: Special Ability"):
      Replace the standard VP formulas with:
        max_vp = highest_ring + school_rank
        max_vp_per_roll = lowest_ring - 1
    """

    def _build_ishi(self, school_rank: int = 3) -> Character:
        """Build an Ishi via the full apply chain at the given school_rank.

        Per the task brief, we drive the school's apply chain directly
        (avoiding character_builder) so we can set rings explicitly.
        """
        ishi = Character("Ishi")
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        school.apply_rank_three_ability(ishi)
        # Sync the VP provider with the rank we want under test (the school
        # initializes the provider at rank 1; advance it explicitly).
        school.vp_provider().set_school_rank(school_rank)
        return ishi

    def test_character_max_vp_uses_ishi_formula(self):
        """character.max_vp() routes through IshiMaxVPProvider:
        highest_ring(4) + school_rank(3) = 7."""
        ishi = self._build_ishi(school_rank=3)
        ishi.set_ring("air", 3)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        self.assertEqual(7, ishi.max_vp())

    def test_character_max_vp_per_roll_uses_ishi_formula(self):
        """character.max_vp_per_roll() routes through IshiMaxVPProvider:
        max(0, lowest_ring(2) - 1) = 1."""
        ishi = self._build_ishi(school_rank=3)
        ishi.set_ring("air", 3)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        self.assertEqual(1, ishi.max_vp_per_roll())

    def test_character_max_vp_per_roll_zero_when_lowest_ring_one(self):
        """End-to-end boundary: lowest ring = 1 -> max_vp_per_roll = 0."""
        ishi = self._build_ishi(school_rank=3)
        ishi.set_ring("air", 1)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 3)
        ishi.set_ring("void", 4)
        self.assertEqual(0, ishi.max_vp_per_roll())

    def test_character_max_vp_scales_with_school_rank(self):
        """As school rank advances, max_vp grows by the same amount
        (highest_ring constant, school_rank increases)."""
        ishi = self._build_ishi(school_rank=1)
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        # highest(4) + rank(1) = 5
        self.assertEqual(5, ishi.max_vp())

        ishi.school().vp_provider().set_school_rank(2)
        self.assertEqual(6, ishi.max_vp())

        ishi.school().vp_provider().set_school_rank(3)
        self.assertEqual(7, ishi.max_vp())

        ishi.school().vp_provider().set_school_rank(5)
        self.assertEqual(9, ishi.max_vp())

    def test_max_vp_per_roll_cap_enforced_via_min(self):
        """
        Engine cap verification: when a caller attempts to spend more VP than
        max_vp_per_roll permits, the canonical clamp `min(available_vp,
        character.max_vp_per_roll())` (used throughout
        simulation/optimizers/* and simulation/schools/akodo_school.py)
        caps spend at max_vp_per_roll.

        Driving a full roll through CombatEngine is out of scope for this
        test; instead we verify the cap value the engine consults.
        """
        ishi = self._build_ishi(school_rank=3)
        ishi.set_ring("air", 2)  # lowest = 2 -> cap = 1
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 3)
        ishi.set_ring("void", 4)

        # Character has plenty of VP (max_vp = 4 + 3 = 7), but per-roll
        # cap is 1.
        self.assertEqual(7, ishi.max_vp())
        self.assertEqual(1, ishi.max_vp_per_roll())

        # Simulate an optimizer wanting to spend 5 VP; the engine-wide
        # clamp pattern caps at max_vp_per_roll.
        requested_spend = 5
        available_vp = ishi.vp()
        capped_spend = min(requested_spend, available_vp, ishi.max_vp_per_roll())
        self.assertEqual(1, capped_spend)

    def test_rank_one_ability_syncs_vp_provider_rank(self):
        """SC-1: apply_rank_one_ability bumps the IshiMaxVPProvider's
        internal rank, so character.max_vp() reflects rank 1.

        Rules clause (rules/04-schools.md "Isawa Ishi School: Special
        Ability"): max_vp = highest_ring + school_rank.
        """
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        # highest(4) + 1 = 5
        self.assertEqual(5, ishi.max_vp())

    def test_rank_two_ability_syncs_vp_provider_rank(self):
        """SC-1: applying rank 2 advances IshiMaxVPProvider to rank 2."""
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        # highest(4) + 2 = 6
        self.assertEqual(6, ishi.max_vp())

    def test_rank_three_ability_syncs_vp_provider_rank(self):
        """SC-1: applying rank 3 advances IshiMaxVPProvider to rank 3."""
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        school.apply_rank_three_ability(ishi)
        # highest(4) + 3 = 7
        self.assertEqual(7, ishi.max_vp())

    def test_rank_four_ability_syncs_after_ring_raise(self):
        """SC-1: rank 4 first raises the school ring (void +1) then
        syncs the VP provider rank — so max_vp must use BOTH the raised
        ring and the bumped school rank.
        """
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)  # gets bumped to 5 by rank-4 ring raise
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        school.apply_rank_three_ability(ishi)
        school.apply_rank_four_ability(ishi)
        # void raised to 5, highest_ring = 5, school_rank = 4 -> 9
        self.assertEqual(5, ishi.ring("void"))
        self.assertEqual(9, ishi.max_vp())

    def test_rank_five_ability_syncs_vp_provider_rank(self):
        """SC-1: rank 5 (even though 5th Dan logic is TODO) still bumps
        the provider's rank so max_vp reflects rank 5.
        """
        ishi = Character("Ishi")
        ishi.set_ring("air", 2)
        ishi.set_ring("earth", 2)
        ishi.set_ring("fire", 2)
        ishi.set_ring("water", 2)
        ishi.set_ring("void", 4)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        school.apply_rank_three_ability(ishi)
        school.apply_rank_four_ability(ishi)
        school.apply_rank_five_ability(ishi)
        # After rank-4 ring raise: void=5, school_rank=5 -> max_vp = 10
        self.assertEqual(10, ishi.max_vp())

    def test_max_vp_per_roll_cap_zero_blocks_spend(self):
        """When max_vp_per_roll = 0 (lowest ring = 1), the canonical clamp
        forbids spending any VP on a single roll even if available_vp > 0."""
        ishi = self._build_ishi(school_rank=3)
        ishi.set_ring("air", 1)  # lowest = 1 -> cap = 0
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 3)
        ishi.set_ring("void", 4)
        self.assertEqual(0, ishi.max_vp_per_roll())

        requested_spend = 3
        available_vp = ishi.vp()
        self.assertGreater(available_vp, 0)
        capped_spend = min(requested_spend, available_vp, ishi.max_vp_per_roll())
        self.assertEqual(0, capped_spend)


class TestIshiSpecialAbilityInstallsPlainAttackStrategy(unittest.TestCase):
    """OPEN_QUESTIONS.md Q4 resolution: ``apply_special_ability`` installs
    ``PlainAttackStrategy`` so the engine's default ``UniversalAttackStrategy``
    (which opens by trying double attack and feint -- neither is an Ishi knack)
    is replaced by a default that cuts to plain attack.

    Per the school-strategy-designer audit: the Ishi school's knacks are
    ``absorb void``, ``kharmic spin``, ``otherworldliness`` -- no
    double-attack, no feint, no counterattack. Spending engine branches on
    those is wasted compute and clashes with the school's identity as a
    Void mystic (Constitution Principle VIII).
    """

    def test_apply_special_ability_sets_plain_attack_strategy(self):
        ishi = Character("Ishi")
        school = ishi_school.IsawaIshiSchool()
        school.apply_special_ability(ishi)
        self.assertIsInstance(ishi.attack_strategy(), PlainAttackStrategy)


class TestIshiFourthDanVoidRaiseAndDiscount(unittest.TestCase):
    """
    Isawa Ishi School Fourth Dan, Void portion.

    rules/04-schools.md "Isawa Ishi School: 4th Dan": the school's
    fourth-dan ability raises the school ring (Void) by 1 and reduces
    the XP cost to raise the school ring by 5.

    Covers the current+max Void +1 vs a baseline and the -5 XP cost
    floor at 0 — mirroring the Mirumoto 4th Dan tests in
    test_mirumoto_school.py::TestMirumotoFourthDanVoidRaiseAndDiscount.

    The implementation is shared with other 4th-dan schools through
    ``BaseSchool.apply_school_ring_raise_and_discount``; this suite
    pins the Void-specific behavior for Ishi.
    """

    def _build_fourth_dan_ishi(self, xp: int = 9001):
        """Construct a 4th-dan Ishi via the standard builder.

        Buying all three school knacks to rank 4 advances the school
        to 4th dan, which triggers ``IsawaIshiSchool.apply_rank_four_ability``
        and thus ``apply_school_ring_raise_and_discount`` on Void.
        """
        school = ishi_school.IsawaIshiSchool()
        builder = (
            CharacterBuilder()
            .with_name("Ishi")
            .with_xp(xp)
            .with_school(school)
            .buy_skill("absorb void", 4)
            .buy_skill("kharmic spin", 4)
            .buy_skill("otherworldliness", 4)
        )
        self.assertEqual(
            4, builder.school_rank(),
            "Test setup: expected school_rank=4 after buying all knacks to 4",
        )
        return builder

    def _build_fourth_dan_baseline(self, xp: int = 9001):
        """Construct a 4th-dan non-Ishi for the baseline comparison.

        Akodo Bushi School is used because its school ring is Water
        (not Void), so its own ``apply_rank_four_ability`` does NOT
        touch Void. This isolates the Ishi-specific Void modification.
        """
        school = akodo_school.AkodoBushiSchool()
        builder = (
            CharacterBuilder()
            .with_name("Akodo")
            .with_xp(xp)
            .with_school(school)
            .buy_skill("double attack", 4)
            .buy_skill("feint", 4)
            .buy_skill("iaijutsu", 4)
        )
        self.assertEqual(
            4, builder.school_rank(),
            "Test setup: expected baseline school_rank=4",
        )
        return builder

    def test_fourth_dan_raises_current_void_by_one_vs_baseline(self):
        """4th-dan Ishi's CURRENT Void ring rank is exactly 1 higher than an
        otherwise-identical 4th-dan baseline (non-Ishi) character's, on top
        of the standard school-ring bump that every school applies to its
        own ring at construction.
        """
        ishi_builder = self._build_fourth_dan_ishi()
        baseline_builder = self._build_fourth_dan_baseline()
        ishi = ishi_builder.build()
        baseline = baseline_builder.build()
        # Baseline non-Ishi's Void stays at the engine default of 2.
        self.assertEqual(
            2, baseline.ring("void"),
            "Baseline non-Ishi's Void must remain at the engine default of 2",
        )
        # Ishi: default 2 -> apply_school_ring +1 (to 3) -> 4th Dan +1 (to 4).
        self.assertEqual(
            4, ishi.ring("void"),
            "4th-dan Ishi's current Void should be 4 "
            "(default 2 + school-ring bump +1 + 4th Dan +1)",
        )
        # The 4th Dan ability contributes a +1 on top of the standard
        # +1 school-ring bump every school applies. Total delta vs Akodo
        # baseline (Water-ring school) is therefore 2.
        self.assertEqual(
            baseline.ring("void") + 2, ishi.ring("void"),
            "4th-dan Ishi Void is +2 over a non-Ishi baseline "
            "(school-ring bump +1, 4th Dan +1)",
        )

    def test_fourth_dan_raises_max_void_by_one_vs_baseline(self):
        """4th-dan Ishi's MAXIMUM Void rank is exactly 1 higher than an
        otherwise-identical 4th-dan baseline (non-Ishi) character's.

        ``_SchoolCharacterBuilder.max_ring`` returns 6 for the school's
        own ring at school rank >= 4 and 5 otherwise.
        """
        ishi_builder = self._build_fourth_dan_ishi()
        baseline_builder = self._build_fourth_dan_baseline()
        self.assertEqual(
            5, baseline_builder.max_ring("void"),
            "Baseline non-Ishi's max Void must be 5",
        )
        self.assertEqual(
            6, ishi_builder.max_ring("void"),
            "4th-dan Ishi's max Void should be 6 "
            "(4th Dan extends the school-ring cap from 5 to 6)",
        )

    def test_fourth_dan_reduces_void_xp_cost_by_five_vs_baseline(self):
        """The XP cost to raise a 4th-dan Ishi's Void by one rank is
        exactly 5 less than the standard L7R Void-raise cost for that
        rank, with a floor of 0.
        """
        ishi_builder = self._build_fourth_dan_ishi()
        baseline_builder = self._build_fourth_dan_baseline()
        ishi_char = ishi_builder.character()
        baseline_char = baseline_builder.character()
        ishi_cur = ishi_char.ring("void")  # 4
        baseline_cur = baseline_char.ring("void")  # 2
        # Standard L7R cost to raise from N to N+1 is 5*(N+1).
        std_ishi_raise = 5 * (ishi_cur + 1)
        std_baseline_raise = 5 * (baseline_cur + 1)
        # Sanity: baseline equals the engine formula.
        self.assertEqual(
            std_baseline_raise,
            baseline_builder.calculate_ring_cost("void", baseline_cur + 1),
            "Baseline non-Ishi's Void raise cost should equal "
            "the standard L7R formula 5*(N+1)",
        )
        ishi_cost = ishi_builder.calculate_ring_cost("void", ishi_cur + 1)
        self.assertEqual(
            std_ishi_raise - 5, ishi_cost,
            "4th-dan Ishi's XP cost to raise Void by one rank must be "
            f"exactly 5 less than the standard L7R cost "
            f"(standard {std_ishi_raise}, expected {std_ishi_raise - 5}, "
            f"got {ishi_cost})",
        )
        # Cross-check the discount is recorded on the character.
        self.assertEqual(
            5, ishi_char._discounts.get("void", 0),
            "the 5-XP Void discount must be recorded on the Ishi's _discounts",
        )
        self.assertEqual(
            0, baseline_char._discounts.get("void", 0),
            "baseline non-Ishi must not receive a Void discount",
        )

    def test_fourth_dan_void_xp_cost_floors_at_zero_when_discount_exceeds_cost(
        self,
    ):
        """When the standard Void-raise cost is <= 5, the 5-XP reduction
        must not produce a negative cost — treat as 0.
        """
        ishi_builder = self._build_fourth_dan_ishi()
        ishi_char = ishi_builder.character()
        self.assertEqual(
            5, ishi_char._discounts.get("void", 0),
            "Precondition: the 5-XP Void discount must be recorded",
        )
        # Force the scenario where standard cost equals the discount
        # by lowering Void to 0 (the floor). Raise to 1 then costs 5 std.
        ishi_char.set_ring("void", 0)
        cost_to_raise_to_one = ishi_builder.calculate_ring_cost("void", 1)
        self.assertEqual(
            0, cost_to_raise_to_one,
            "4th Dan floor: when the standard Void-raise cost (5) equals "
            "the Ishi 5-XP discount, the discounted cost MUST be 0 "
            f"(not negative); got {cost_to_raise_to_one}",
        )


class TestEagerNegationStrategy(unittest.TestCase):
    """Unit tests for the pluggable 5th Dan school-negation decision strategy.

    rules/04-schools.md "Isawa Ishi School: 5th Dan": the Ishi may spend
    VP equal to 2 × opponent's school rank (or floor(xp/50) for schoolless)
    to negate an opponent's school/profession for the duration of a fight.

    These tests exercise the strategy directly (no listener chaining) so
    the decision logic is isolated. Per Constitution Principle V, the
    strategy must be swappable.
    """

    def _build_fifth_dan_ishi(self) -> Character:
        ishi = Character("Ishi")
        ishi.set_ring("void", 5)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 3)
        ishi.set_ring("air", 3)
        ishi.set_skill("precepts", 5)
        # Bring all school knacks to 5 so the derived school_rank = 5.
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        for knack in school.school_knacks():
            ishi.set_skill(knack, 5)
        school.apply_special_ability(ishi)
        # Sync the VP provider's rank so max_vp = highest_ring + 5 (else
        # the Ishi's max_vp is too low to afford the 2*opponent_rank cost).
        school.vp_provider().set_school_rank(5)
        return ishi

    def _build_fourth_dan_mirumoto(self) -> Character:
        mirumoto = Character("Mirumoto")
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        # Bring all school knacks to 4 so derived school_rank = 4.
        for knack in school.school_knacks():
            mirumoto.set_skill(knack, 4)
        return mirumoto

    def test_fires_on_your_move_with_schooled_enemy(self):
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        event = events.YourMoveEvent(ishi)
        strat = EagerNegationStrategy()
        responses = list(strat.recommend(ishi, event, ctx))
        # Must yield SpendVoidPointsEvent (cost 2*4 = 8) then SchoolNegatedEvent.
        self.assertEqual(2, len(responses))
        self.assertIsInstance(responses[0], events.SpendVoidPointsEvent)
        self.assertEqual(8, responses[0].amount)
        self.assertIs(ishi, responses[0].subject)
        self.assertIsInstance(responses[1], events.SchoolNegatedEvent)
        self.assertIs(ishi, responses[1].negator)
        self.assertIs(mirumoto, responses[1].target)
        self.assertEqual(8, responses[1].vp_cost)
        self.assertEqual("Mirumoto Bushi School", responses[1].target_school_name)
        # Mirumoto's _school_negated_by is now set.
        self.assertIs(ishi, mirumoto._school_negated_by)
        # The Ishi's done-flag is set so the strategy will not refire.
        self.assertTrue(getattr(ishi, "_ishi_negation_done", False))

    def test_no_fire_when_already_done(self):
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        ishi._ishi_negation_done = True
        strat = EagerNegationStrategy()
        event = events.YourMoveEvent(ishi)
        responses = list(strat.recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_when_school_rank_below_five(self):
        """The 5th Dan ability requires school_rank >= 5."""
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy
        ishi = self._build_fifth_dan_ishi()
        # Lower one knack so derived school_rank < 5.
        ishi.set_skill("absorb void", 4)
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        event = events.YourMoveEvent(ishi)
        responses = list(EagerNegationStrategy().recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_on_unrelated_event(self):
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        event = events.NewRoundEvent(round=1)
        responses = list(EagerNegationStrategy().recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_no_fire_when_insufficient_vp(self):
        """If the Ishi cannot afford the cost (2 * opponent rank), abstain."""
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        # Drain the Ishi's VP below the cost (cost is 2*4 = 8).
        # Ishi max_vp = highest_ring(5) + school_rank(1, special ability default) = 6.
        # But school_rank in IshiMaxVPProvider is 1 (not synced because we didn't apply ranks).
        # Drain everything just to be safe.
        ishi.spend_vp(ishi.vp())
        event = events.YourMoveEvent(ishi)
        responses = list(EagerNegationStrategy().recommend(ishi, event, ctx))
        self.assertEqual(0, len(responses))

    def test_targets_highest_rank_schooled_enemy(self):
        """When multiple enemies exist, target the highest-rank schooled one."""
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy
        ishi = self._build_fifth_dan_ishi()
        # Two enemies: a 2nd-dan Akodo and a 4th-dan Mirumoto.
        weak_akodo = Character("Akodo2nd")
        akodo = akodo_school.AkodoBushiSchool()
        weak_akodo.set_school(akodo)
        for knack in akodo.school_knacks():
            weak_akodo.set_skill(knack, 2)
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [
            Group("Phoenix", [ishi]),
            Group("Dragon", [mirumoto, weak_akodo]),
        ]
        ctx = EngineContext(groups)
        event = events.YourMoveEvent(ishi)
        responses = list(EagerNegationStrategy().recommend(ishi, event, ctx))
        # The 4th-dan Mirumoto is the target, not the 2nd-dan Akodo.
        negate_events = [r for r in responses if isinstance(r, events.SchoolNegatedEvent)]
        self.assertEqual(1, len(negate_events))
        self.assertIs(mirumoto, negate_events[0].target)


class TestIshiFifthDanNegation(unittest.TestCase):
    """5th Dan ability integration: a 5th-dan Ishi vs a 4th-dan Mirumoto.

    rules/04-schools.md "Isawa Ishi School: 5th Dan".

    Verifies the wiring of ``apply_rank_five_ability``: the strategy
    ``EagerNegationStrategy`` is installed on ``"ishi_negate_school"``,
    and an ``IshiYourMoveListener`` is installed on ``"your_move"`` so
    the engine's YourMoveEvent dispatch consults the strategy before
    the normal action handling proceeds.
    """

    def _build_fifth_dan_ishi(self) -> Character:
        ishi = Character("Ishi")
        ishi.set_ring("air", 3)
        ishi.set_ring("earth", 3)
        ishi.set_ring("fire", 3)
        ishi.set_ring("water", 3)
        ishi.set_ring("void", 5)
        ishi.set_skill("precepts", 5)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        for knack in school.school_knacks():
            ishi.set_skill(knack, 5)
        school.apply_special_ability(ishi)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        school.apply_rank_three_ability(ishi)
        school.apply_rank_four_ability(ishi)
        school.apply_rank_five_ability(ishi)
        return ishi

    def _build_fourth_dan_mirumoto(self) -> Character:
        mirumoto = Character("Mirumoto")
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        for knack in school.school_knacks():
            mirumoto.set_skill(knack, 4)
        school.apply_special_ability(mirumoto)
        school.apply_rank_one_ability(mirumoto)
        school.apply_rank_two_ability(mirumoto)
        school.apply_rank_three_ability(mirumoto)
        school.apply_rank_four_ability(mirumoto)
        return mirumoto

    def test_fifth_dan_negation_spends_eight_vp_against_fourth_dan_target(self):
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        starting_vp = ishi.vp()
        event = events.YourMoveEvent(ishi)
        # Invoke the listener installed on the ishi's your_move slot.
        responses = list(ishi._listeners["your_move"].handle(ishi, event, ctx))
        # Among the responses there is exactly one SpendVoidPointsEvent of 8.
        spends = [r for r in responses if isinstance(r, events.SpendVoidPointsEvent)]
        self.assertGreaterEqual(len(spends), 1)
        # The negation spend should be 2 * 4 = 8.
        negation_spends = [s for s in spends if s.skill == "ishi_negate_school"]
        self.assertEqual(1, len(negation_spends))
        self.assertEqual(8, negation_spends[0].amount)
        # Verify the Mirumoto is flagged as negated.
        self.assertIs(ishi, mirumoto._school_negated_by)
        # Apply the spend event to verify VP actually drains.
        ishi.spend_vp(negation_spends[0].amount)
        self.assertEqual(starting_vp - 8, ishi.vp())

    def test_fifth_dan_negation_fires_once_per_combat(self):
        """A second YourMoveEvent must not trigger a second negation."""
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        event = events.YourMoveEvent(ishi)
        # First invocation: negation fires.
        first = list(ishi._listeners["your_move"].handle(ishi, event, ctx))
        first_negations = [
            r for r in first
            if isinstance(r, events.SpendVoidPointsEvent) and r.skill == "ishi_negate_school"
        ]
        self.assertEqual(1, len(first_negations))
        # Second invocation: must NOT fire negation again.
        second = list(ishi._listeners["your_move"].handle(ishi, event, ctx))
        second_negations = [
            r for r in second
            if isinstance(r, events.SpendVoidPointsEvent) and r.skill == "ishi_negate_school"
        ]
        self.assertEqual(0, len(second_negations))

    def test_fifth_dan_negation_emits_school_negated_event(self):
        """The negation must yield a SchoolNegatedEvent for trace observability."""
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        event = events.YourMoveEvent(ishi)
        responses = list(ishi._listeners["your_move"].handle(ishi, event, ctx))
        negated_events = [r for r in responses if isinstance(r, events.SchoolNegatedEvent)]
        self.assertEqual(1, len(negated_events))
        sne = negated_events[0]
        self.assertIs(ishi, sne.negator)
        self.assertIs(mirumoto, sne.target)
        self.assertEqual(8, sne.vp_cost)
        self.assertEqual("Mirumoto Bushi School", sne.target_school_name)

    def test_reset_clears_negation_flags(self):
        """After Character.reset(), both _school_negated_by (on target) and
        _ishi_negation_done (on Ishi) are cleared so the negation can occur
        again in a new combat."""
        ishi = self._build_fifth_dan_ishi()
        mirumoto = self._build_fourth_dan_mirumoto()
        # Manually set the flags so we don't depend on the listener firing.
        mirumoto._school_negated_by = ishi
        ishi._ishi_negation_done = True
        ishi.reset()
        mirumoto.reset()
        self.assertIsNone(mirumoto._school_negated_by)
        self.assertFalse(getattr(ishi, "_ishi_negation_done", False))

    def test_your_move_listener_delegates_to_default_when_no_negation(self):
        """When the negation strategy abstains (e.g., already done), the
        listener must still delegate to the engine's standard YourMoveListener
        behavior so the Ishi still acts normally."""
        ishi = self._build_fifth_dan_ishi()
        ishi._ishi_negation_done = True  # block negation
        ishi.set_actions([])  # no actions so listener will respond NoAction
        mirumoto = self._build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", [ishi]), Group("Dragon", [mirumoto])]
        ctx = EngineContext(groups)
        event = events.YourMoveEvent(ishi)
        responses = list(ishi._listeners["your_move"].handle(ishi, event, ctx))
        # No negation events but the default YourMoveListener still fired
        # (a NoActionEvent is yielded since the Ishi has no actions).
        negations = [r for r in responses if isinstance(r, events.SchoolNegatedEvent)]
        self.assertEqual(0, len(negations))
        no_actions = [r for r in responses if isinstance(r, events.NoActionEvent)]
        self.assertEqual(1, len(no_actions))


class TestIshiTraceClarity(unittest.TestCase):
    """Constitution Principle VII regression guard: every Ishi-school
    ability that touches a combat roll must surface in the user-facing
    combat trace with a source attribution (or, for the +1 die, with a
    rolled-dice count that visibly differs from baseline).

    This class is a composite regression suite covering the five Ishi
    abilities listed in T022:

      1. Special Ability ``max_vp_per_roll`` cap -- SKIPPED.  The cap is
         enforced silently via ``min()`` in the attack/wound-check
         optimizers (``simulation/optimizers/{attack,wound_check}_optimizers.py``)
         and never emits a dedicated trace event.  Testing it via the
         user-facing trace is too engine-specific to be a clean regression
         guard; the cap arithmetic itself is fully covered by
         ``TestIshiMaxVPProviderEdgeCases`` /
         ``TestIshiSpecialAbilityIntegration::test_max_vp_per_roll_*``.
      2. 1st Dan extra die -- a 1st-dan Ishi's precepts / wound-check /
         initiative roll rolls one MORE die than a same-stats baseline.
         The dice count is rendered as ``{rolled}k{kept}`` by the
         formatter so the +1 is directly visible without separate
         attribution.
      3. 2nd Dan free raise on precepts -- ``explain_modifier`` attributes
         the +5 to ``"Isawa Ishi 2nd Dan free raise"``.  (Covered fully by
         ``tests/test_combat_trace_attribution.py::TestExplainModifierIshiSecondDan``;
         we re-verify the contract locally as a regression guard.)
      4. 3rd Dan ally boost -- the formatter renders the boost line with
         ``"Isawa Ishi 3rd Dan ally boost from {ishi_name}"``.  (Covered
         fully by ``TestExplainModifierIshiThirdDanAllyBoost`` +
         ``TestFormatterShowsIshiThirdDanBoostAttribution``; re-verified
         locally.)
      5. 5th Dan negation -- the formatter renders ``SchoolNegatedEvent``
         with ``"Isawa Ishi 5th Dan"``, the negator name, the target
         name, the target's school name, and the VP cost.  (Covered fully
         by ``TestFormatterRendersSchoolNegatedEvent``; re-verified
         locally.)

    rules/04-schools.md "Isawa Ishi School" + Constitution Principle VII.
    """

    def _build_first_dan_ishi(self) -> Character:
        """A 1st-dan Ishi for the +1-die comparison (item 2)."""
        ishi = Character("Ishi1stTrace")
        for ring in ("air", "earth", "fire", "water", "void"):
            ishi.set_ring(ring, 3)
        ishi.set_skill("precepts", 2)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        school.apply_rank_one_ability(ishi)
        return ishi

    def _build_baseline_non_ishi(self) -> Character:
        """A plain (no-school) character with the same rings/skills as the
        1st-dan Ishi for baseline comparison."""
        plain = Character("PlainTrace")
        for ring in ("air", "earth", "fire", "water", "void"):
            plain.set_ring(ring, 3)
        plain.set_skill("precepts", 2)
        return plain

    def _build_second_dan_ishi(self) -> Character:
        """A 2nd-dan Ishi for the precepts free-raise attribution check."""
        ishi = Character("Ishi2ndTrace")
        ishi.set_ring("void", 3)
        ishi.set_skill("precepts", 2)
        school = ishi_school.IsawaIshiSchool()
        ishi.set_school(school)
        for knack in school.school_knacks():
            ishi.set_skill(knack, 2)
        school.apply_rank_one_ability(ishi)
        school.apply_rank_two_ability(ishi)
        return ishi

    # ------------------------------------------------------------------
    # Item 2 -- 1st Dan extra die surfaces via dice-count delta.
    # ------------------------------------------------------------------

    def test_first_dan_precepts_rolls_one_more_die_than_baseline(self):
        """A 1st-dan Ishi's precepts roll rolls ``baseline_rolled + 1``
        dice.  The formatter renders ``{rolled}k{kept}`` so this +1 is
        directly visible in the trace without needing a separate
        attribution line.

        rules/04-schools.md "Isawa Ishi School: 1st Dan" +
        Constitution Principle VII.
        """
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline_non_ishi()
        provider = DefaultRollParameterProvider()
        ishi_rolled, _ishi_kept, _ = provider.get_skill_roll_params(
            ishi, None, "precepts", ring=ishi.ring("void"),
        )
        base_rolled, _base_kept, _ = provider.get_skill_roll_params(
            baseline, None, "precepts", ring=baseline.ring("void"),
        )
        self.assertEqual(
            base_rolled + 1,
            ishi_rolled,
            "1st-dan Ishi must roll +1 die on precepts so the trace's "
            "rolled-dice count surfaces the bonus without attribution.",
        )

    def test_first_dan_wound_check_rolls_one_more_die_than_baseline(self):
        """Wound-check version of the +1-die surfacing test.

        rules/04-schools.md "Isawa Ishi School: 1st Dan".
        """
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline_non_ishi()
        provider = DefaultRollParameterProvider()
        ishi_rolled, _ishi_kept, _ = provider.get_wound_check_roll_params(ishi)
        base_rolled, _base_kept, _ = provider.get_wound_check_roll_params(baseline)
        self.assertEqual(base_rolled + 1, ishi_rolled)

    def test_first_dan_initiative_rolls_one_more_die_than_baseline(self):
        """Initiative version of the +1-die surfacing test.

        rules/04-schools.md "Isawa Ishi School: 1st Dan".
        """
        ishi = self._build_first_dan_ishi()
        baseline = self._build_baseline_non_ishi()
        provider = DefaultRollParameterProvider()
        ishi_rolled, _ishi_kept, _ = provider.get_initiative_roll_params(ishi)
        base_rolled, _base_kept, _ = provider.get_initiative_roll_params(baseline)
        self.assertEqual(base_rolled + 1, ishi_rolled)

    # ------------------------------------------------------------------
    # Item 3 -- 2nd Dan free raise on precepts attribution.
    # ------------------------------------------------------------------

    def test_second_dan_precepts_free_raise_attributed_in_breakdown(self):
        """``explain_modifier`` attributes the +5 precepts free-raise to
        ``"Isawa Ishi 2nd Dan free raise"``.  Regression guard for the
        primary coverage in ``tests/test_combat_trace_attribution.py``.

        rules/04-schools.md "Isawa Ishi School: 2nd Dan".
        """
        # Imported lazily so this test file remains usable when web/ is
        # unavailable (the import lives inside the function body).
        from web.adapters.modifier_breakdown import explain_modifier

        ishi = self._build_second_dan_ishi()
        breakdown = explain_modifier(ishi, "precepts", modifier=5, vp=0)
        self.assertIn(
            ("Isawa Ishi 2nd Dan free raise", 5),
            breakdown,
            "2nd-dan Ishi precepts roll must attribute the +5 free raise "
            "in the breakdown so the trace can render it.",
        )

    # ------------------------------------------------------------------
    # Item 4 -- 3rd Dan ally boost attribution (by Ishi name).
    # ------------------------------------------------------------------

    def test_third_dan_ally_boost_attributed_by_ishi_name(self):
        """When ``EagerAllyBoostStrategy`` tags an action with
        ``_ishi_boosted_by`` + ``_ishi_boost_value``,
        ``explain_modifier`` produces a
        ``"Isawa Ishi 3rd Dan ally boost from {name}"`` contribution.
        Regression guard for ``TestExplainModifierIshiThirdDanAllyBoost`` +
        ``TestFormatterShowsIshiThirdDanBoostAttribution``.

        rules/04-schools.md "Isawa Ishi School: 3rd Dan".
        """
        from unittest.mock import MagicMock

        from web.adapters.modifier_breakdown import explain_modifier

        # Named Ishi so the attribution string carries the source name.
        named_ishi = Character("Hoshi")
        rolling_ally = Character("Bushi")
        action = MagicMock()
        action._ishi_boosted_by = named_ishi
        action._ishi_boost_value = 7
        breakdown = explain_modifier(
            rolling_ally, "attack", modifier=7, vp=0, action=action,
        )
        self.assertIn(
            ("Isawa Ishi 3rd Dan ally boost from Hoshi", 7),
            breakdown,
            "3rd Dan ally boost must attribute by Ishi name so the "
            "playtester knows which Ishi's boost fired.",
        )

    # ------------------------------------------------------------------
    # Item 5 -- 5th Dan negation rendered with source attribution.
    # ------------------------------------------------------------------

    def test_fifth_dan_negation_event_rendered_with_source_in_trace(self):
        """``DetailedEventFormatter`` renders ``SchoolNegatedEvent`` with
        all of: negator name, target name, target school name, VP cost,
        and ``"Isawa Ishi 5th Dan"`` source attribution.  Regression
        guard for ``TestFormatterRendersSchoolNegatedEvent``.

        rules/04-schools.md "Isawa Ishi School: 5th Dan".
        """
        from web.adapters.detailed_formatter import DetailedEventFormatter

        ishi = Character("Hoshi")
        akodo = Character("Toturi")
        negated_event = events.SchoolNegatedEvent(
            negator=ishi,
            target=akodo,
            vp_cost=8,
            target_school_name="Akodo Bushi School",
        )
        phase_event = events.NewPhaseEvent(phase=3)
        fmt = DetailedEventFormatter()
        joined = "\n".join(fmt.format_history([phase_event, negated_event]))
        # All five trace elements must be present.
        self.assertIn("Hoshi", joined)
        self.assertIn("Toturi", joined)
        self.assertIn("Akodo Bushi School", joined)
        self.assertIn("8", joined)
        self.assertIn("Isawa Ishi 5th Dan", joined)
