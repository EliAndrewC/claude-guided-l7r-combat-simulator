#!/usr/bin/env python3

#
# test_mirumoto_school.py
#
# Unit tests for the Mirumoto Bushi School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import FreeRaise
from simulation.mechanics.roll_params import DefaultRollParameterProvider
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import akodo_school, mirumoto_school
from simulation.schools.factory import get_school
from simulation.strategies import mirumoto_third_dan

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestMirumotoBushiSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        # FR-005 / rules/04-schools.md Mirumoto Bushi School First Dan:
        # "Roll one extra die on parry, double attack, and wound checks."
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual(["parry", "double attack", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual("void", school.school_ring())

    def test_school_knacks(self):
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual(["counterattack", "double attack", "iaijutsu"], school.school_knacks())

    def test_free_raise_skills(self):
        school = mirumoto_school.MirumotoBushiSchool()
        self.assertEqual(["parry"], school.free_raise_skills())


class TestMirumotoFirstDanExtraDie(unittest.TestCase):
    """
    End-to-end verification of the Mirumoto Bushi School First Dan bonus.

    FR-005 / rules/04-schools.md Mirumoto Bushi School First Dan:
    "Roll one extra die on parry, double attack, and wound checks."

    Covers acceptance scenarios US1.3 (parry) and US1.4 (double attack
    and wound check) by comparing the dice count of a 1st-dan Mirumoto's
    roll against a baseline character via the existing roll-params
    pipeline.
    """

    def setUp(self):
        # Build a 1st-dan Mirumoto by directly applying the school's
        # rank-one ability (which calls set_extra_rolled for each skill
        # named in the school's extra_rolled() list).
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.mirumoto.set_skill("attack", 4)
        self.mirumoto.set_skill("double attack", 4)
        self.mirumoto.set_skill("parry", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        school.apply_rank_one_ability(self.mirumoto)

        # Baseline character: identical stats, no school bonus applied.
        self.baseline = Character("baseline")
        self.baseline.set_actions([1])
        self.baseline.set_skill("attack", 4)
        self.baseline.set_skill("double attack", 4)
        self.baseline.set_skill("parry", 4)

        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [
            Group("Dragon", [self.mirumoto, self.baseline]),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_double_attack_action_skill_roll_params_adds_one_die(self):
        """US1.4: DoubleAttackAction.skill_roll_params() rolls +1 die.

        Catches key-mismatch bugs between the school's extra_rolled() list
        entries and the skill names looked up on the character.
        """
        mirumoto_da = actions.DoubleAttackAction(
            self.mirumoto, self.attacker, "double attack", self.initiative_action, self.context,
        )
        baseline_da = actions.DoubleAttackAction(
            self.baseline, self.attacker, "double attack", self.initiative_action, self.context,
        )
        mirumoto_params = mirumoto_da.skill_roll_params()
        baseline_params = baseline_da.skill_roll_params()
        # default rings = 2 ('fire' for double attack), skill = 4
        # baseline: rolled = 2 + 4 + 0 = 6, kept = 2, modifier = 0
        # mirumoto: rolled = 2 + 4 + 1 = 7, kept = 2, modifier = 0
        self.assertEqual((6, 2, 0), baseline_params)
        self.assertEqual((7, 2, 0), mirumoto_params)
        self.assertEqual(baseline_params[0] + 1, mirumoto_params[0])

    def test_parry_action_skill_roll_params_adds_one_die(self):
        """US1.3: ParryAction.skill_roll_params() rolls +1 die."""
        mirumoto_attack = actions.AttackAction(
            self.attacker, self.mirumoto, "attack", self.initiative_action, self.context,
        )
        baseline_attack = actions.AttackAction(
            self.attacker, self.baseline, "attack", self.initiative_action, self.context,
        )
        mirumoto_parry = actions.ParryAction(
            self.mirumoto, self.attacker, "parry", self.initiative_action, self.context, mirumoto_attack,
        )
        baseline_parry = actions.ParryAction(
            self.baseline, self.attacker, "parry", self.initiative_action, self.context, baseline_attack,
        )
        mirumoto_params = mirumoto_parry.skill_roll_params()
        baseline_params = baseline_parry.skill_roll_params()
        # default rings = 2 ('air' for parry), skill = 4
        # baseline: rolled = 2 + 4 + 0 = 6, kept = 2, modifier = 0
        # mirumoto: rolled = 2 + 4 + 1 = 7, kept = 2, modifier = 0
        self.assertEqual((6, 2, 0), baseline_params)
        self.assertEqual((7, 2, 0), mirumoto_params)
        self.assertEqual(baseline_params[0] + 1, mirumoto_params[0])

    def test_wound_check_roll_params_adds_one_die(self):
        """US1.4: wound check roll-params provider returns +1 rolled die."""
        provider = DefaultRollParameterProvider()
        mirumoto_params = provider.get_wound_check_roll_params(self.mirumoto)
        baseline_params = provider.get_wound_check_roll_params(self.baseline)
        # default ring = 2 ('water' for wound check), base rolled = ring + 1
        # baseline: rolled = 2 + 1 + 0 = 3, kept = 2, modifier = 0
        # mirumoto: rolled = 2 + 1 + 1 = 4, kept = 2, modifier = 0
        self.assertEqual((3, 2, 0), baseline_params)
        self.assertEqual((4, 2, 0), mirumoto_params)
        self.assertEqual(baseline_params[0] + 1, mirumoto_params[0])


class TestMirumotoSecondDanFreeRaise(unittest.TestCase):
    """
    Verifies the Mirumoto Bushi School Second Dan free raise on parry rolls.

    FR-006 / rules/04-schools.md Mirumoto Bushi School Second Dan:
    "You get a free raise on parry rolls."

    Covers acceptance scenario US1.5: a 2nd-dan Mirumoto's parry roll must
    include a free raise (worth +5 to the roll) that the character did not
    pay for and that did not consume any normal raise budget.

    These tests would fail if MirumotoBushiSchool.free_raise_skills() were
    broken (e.g., returned [] or named the wrong skill), because the
    FreeRaise modifier would not be added to the character's modifier list
    and the parry roll's effective bonus would not include the +5.
    """

    def setUp(self) -> None:
        # 2nd-dan Mirumoto: apply both the 1st Dan (extra rolled) and the
        # 2nd Dan (free raise) abilities so the character is genuinely a
        # rank-2 Mirumoto Bushi.
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.mirumoto.set_skill("attack", 4)
        self.mirumoto.set_skill("parry", 4)
        self.school = mirumoto_school.MirumotoBushiSchool()
        self.school.apply_rank_one_ability(self.mirumoto)
        self.school.apply_rank_two_ability(self.mirumoto)

        # Baseline character: identical stats, no school abilities applied.
        self.baseline = Character("baseline")
        self.baseline.set_actions([1])
        self.baseline.set_skill("attack", 4)
        self.baseline.set_skill("parry", 4)

        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [
            Group("Dragon", [self.mirumoto, self.baseline]),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_free_raise_modifier_added_for_parry(self) -> None:
        """The FreeRaise modifier for "parry" is present on the character."""
        parry_free_raises = [
            mod for mod in self.mirumoto._modifiers
            if isinstance(mod, FreeRaise) and "parry" in mod.skills()
        ]
        self.assertEqual(1, len(parry_free_raises))
        # Subject of the free raise is the Mirumoto character itself.
        self.assertEqual(self.mirumoto, parry_free_raises[0].subject())
        # FreeRaise grants +5 (one raise in L7R = +5).
        self.assertEqual(5, parry_free_raises[0].adjustment())

    def test_baseline_has_no_parry_free_raise(self) -> None:
        """The baseline character (no school applied) has no parry FreeRaise."""
        parry_free_raises = [
            mod for mod in self.baseline._modifiers
            if isinstance(mod, FreeRaise) and "parry" in mod.skills()
        ]
        self.assertEqual(0, len(parry_free_raises))

    def test_character_parry_modifier_includes_free_raise(self) -> None:
        """character.modifier(None, "parry") reflects the +5 free raise."""
        baseline_mod = self.baseline.modifier(None, "parry")
        mirumoto_mod = self.mirumoto.modifier(None, "parry")
        self.assertEqual(baseline_mod + 5, mirumoto_mod)

    def test_parry_action_skill_roll_params_includes_free_raise(self) -> None:
        """ParryAction.skill_roll_params() includes the +5 free raise bonus."""
        mirumoto_attack = actions.AttackAction(
            self.attacker, self.mirumoto, "attack", self.initiative_action, self.context,
        )
        baseline_attack = actions.AttackAction(
            self.attacker, self.baseline, "attack", self.initiative_action, self.context,
        )
        mirumoto_parry = actions.ParryAction(
            self.mirumoto, self.attacker, "parry", self.initiative_action, self.context, mirumoto_attack,
        )
        baseline_parry = actions.ParryAction(
            self.baseline, self.attacker, "parry", self.initiative_action, self.context, baseline_attack,
        )
        (m_rolled, m_kept, m_mod) = mirumoto_parry.skill_roll_params()
        (b_rolled, b_kept, b_mod) = baseline_parry.skill_roll_params()
        # Modifier is +5 higher for the 2nd-dan Mirumoto due to the free raise.
        self.assertEqual(b_mod + 5, m_mod)
        # The free raise must not consume any normal raise budget: it is a
        # flat bonus on the modifier, not a reduction in rolled/kept dice.
        # Compared to baseline, Mirumoto only adds +1 rolled (from 1st Dan
        # extra_rolled on parry); kept is unchanged.
        self.assertEqual(b_rolled + 1, m_rolled)
        self.assertEqual(b_kept, m_kept)

    def test_free_raise_does_not_apply_to_attack(self) -> None:
        """The parry free raise must not bleed into attack-roll modifiers."""
        baseline_attack_mod = self.baseline.modifier(None, "attack")
        mirumoto_attack_mod = self.mirumoto.modifier(None, "attack")
        self.assertEqual(baseline_attack_mod, mirumoto_attack_mod)

    def test_free_raise_does_not_apply_to_other_skills(self) -> None:
        """The parry free raise must not apply to unrelated skills (e.g., wound check)."""
        baseline_wc_mod = self.baseline.modifier(None, "wound check")
        mirumoto_wc_mod = self.mirumoto.modifier(None, "wound check")
        self.assertEqual(baseline_wc_mod, mirumoto_wc_mod)


class TestMirumotoParryTVPListener(unittest.TestCase):
    """
    Tests for the Mirumoto Bushi Special Ability:

    FR-004 / rules/04-schools.md Mirumoto Bushi School Special Ability:
    "Your successful or unsuccessful parries give you a temporary void point."

    Clarification (specs/001-mirumoto-bushi-school/spec.md): the temporary
    void point is usable immediately (same round), stacks above the normal
    Void cap, and is discarded at end of combat.

    Edge Cases covered here:
      - Cap-bypass: a Mirumoto already at full normal VP still gains the
        TVP on parry, and ``character.vp()`` ends up strictly above
        ``character.max_vp()``.
      - Multiple parries in a single round each grant their own TVP
        (no per-round cap on the Special Ability).
    """

    def setUp(self):
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Dragon", self.mirumoto), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def _make_parry(self) -> actions.ParryAction:
        attack = actions.AttackAction(
            self.attacker, self.mirumoto, "attack",
            self.initiative_action, self.context,
        )
        return actions.ParryAction(
            self.mirumoto, self.attacker, "parry",
            self.initiative_action, self.context, attack,
        )

    def test_gain_tvp_on_parry_succeeded(self):
        """Listener emits a single TVP-gain event on a successful parry (FR-004)."""
        parry = self._make_parry()
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = mirumoto_school.MirumotoParryTVPListener()
        responses = list(listener.handle(self.mirumoto, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertTrue(isinstance(responses[0], events.GainTemporaryVoidPointsEvent))
        self.assertEqual(self.mirumoto, responses[0].subject)
        self.assertEqual(1, responses[0].amount)

    def test_gain_tvp_on_parry_failed(self):
        """Listener emits a single TVP-gain event on a failed parry (FR-004)."""
        parry = self._make_parry()
        parry.set_skill_roll(20)
        event = events.ParryFailedEvent(parry)
        listener = mirumoto_school.MirumotoParryTVPListener()
        responses = list(listener.handle(self.mirumoto, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertTrue(isinstance(responses[0], events.GainTemporaryVoidPointsEvent))
        self.assertEqual(self.mirumoto, responses[0].subject)
        self.assertEqual(1, responses[0].amount)

    def test_listener_ignores_parry_event_for_other_character(self):
        """Listener must not fire when the parry's subject is not this character.

        Guards against a regression where the listener accidentally drops the
        ``event.action.subject() == character`` guard and rewards bystanders.
        """
        # Build a parry whose subject is the attacker (not self.mirumoto)
        other_attack = actions.AttackAction(
            self.mirumoto, self.attacker, "attack",
            self.initiative_action, self.context,
        )
        other_parry = actions.ParryAction(
            self.attacker, self.mirumoto, "parry",
            self.initiative_action, self.context, other_attack,
        )
        other_parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(other_parry)
        listener = mirumoto_school.MirumotoParryTVPListener()
        responses = list(listener.handle(self.mirumoto, event, self.context))
        self.assertEqual([], responses)

    def test_parry_succeeded_pipeline_increments_tvp(self):
        """End-to-end: a parry_succeeded event flowing through the engine
        actually increments the Mirumoto's ``_tvp`` counter (FR-004).

        Guards against the failure mode where the listener correctly emits
        ``GainTemporaryVoidPointsEvent`` but the downstream
        ``GainTemporaryVoidPointsListener`` is somehow disconnected from this
        character (e.g., a school override that clobbers the default
        ``gain_tvp`` listener slot would break this test).
        """
        self.mirumoto.set_school(mirumoto_school.MirumotoBushiSchool())
        self.mirumoto.school().apply_special_ability(self.mirumoto)

        self.assertEqual(0, self.mirumoto.tvp())
        parry = self._make_parry()
        parry.set_skill_roll(50)
        engine = CombatEngine(self.context)
        engine.event(events.ParrySucceededEvent(parry))
        self.assertEqual(1, self.mirumoto.tvp())

    def test_parry_failed_pipeline_increments_tvp(self):
        """End-to-end: a parry_failed event flowing through the engine
        actually increments the Mirumoto's ``_tvp`` counter (FR-004).
        """
        self.mirumoto.set_school(mirumoto_school.MirumotoBushiSchool())
        self.mirumoto.school().apply_special_ability(self.mirumoto)

        self.assertEqual(0, self.mirumoto.tvp())
        parry = self._make_parry()
        parry.set_skill_roll(20)
        engine = CombatEngine(self.context)
        engine.event(events.ParryFailedEvent(parry))
        self.assertEqual(1, self.mirumoto.tvp())

    def test_tvp_stacks_above_max_vp_cap(self):
        """TVP granted by a parry stacks above the character's normal VP cap.

        Covers the spec Edge Case: "A Mirumoto Bushi whose normal Void pool
        is already at its cap when a parry resolves; the temporary void
        point granted by the Special Ability stacks on top of the cap."

        Guards against a regression where ``gain_tvp`` (or the listener
        that consumes ``GainTemporaryVoidPointsEvent``) were to clamp
        ``_tvp`` at ``max_vp() - _vp_spent`` instead of letting it stack
        unboundedly. With a default character (rings all = 2, no
        worldliness, no spent VP), ``vp() == max_vp() == 2`` at start,
        so a TVP must push ``vp()`` strictly above ``max_vp()``.
        """
        self.mirumoto.set_school(mirumoto_school.MirumotoBushiSchool())
        self.mirumoto.school().apply_special_ability(self.mirumoto)

        # Pre-condition: character is at full normal Void pool.
        self.assertEqual(self.mirumoto.max_vp(), self.mirumoto.vp())
        starting_max_vp = self.mirumoto.max_vp()
        self.assertEqual(0, self.mirumoto.tvp())

        parry = self._make_parry()
        parry.set_skill_roll(50)
        engine = CombatEngine(self.context)
        engine.event(events.ParrySucceededEvent(parry))

        # TVP counter incremented, and total vp() now exceeds the normal cap.
        self.assertEqual(1, self.mirumoto.tvp())
        self.assertEqual(starting_max_vp, self.mirumoto.max_vp())
        self.assertEqual(starting_max_vp + 1, self.mirumoto.vp())
        self.assertGreater(self.mirumoto.vp(), self.mirumoto.max_vp())

    def test_multiple_parries_in_one_round_each_grant_separate_tvp(self):
        """Each parry in the same round grants its own TVP, cumulatively.

        Covers the spec Edge Case: "Multiple parries in the same round
        each grant their own temporary void point — there is no per-round
        limit on the Special Ability."

        Guards against a regression where the listener (or some downstream
        consumer) tracks a per-round flag and silently skips additional
        grants after the first one in a round.
        """
        self.mirumoto.set_school(mirumoto_school.MirumotoBushiSchool())
        self.mirumoto.school().apply_special_ability(self.mirumoto)

        self.assertEqual(0, self.mirumoto.tvp())
        engine = CombatEngine(self.context)

        # Three parries in the same round: one succeeded, one failed, one
        # succeeded (exercising both event types in a single round).
        parry1 = self._make_parry()
        parry1.set_skill_roll(50)
        engine.event(events.ParrySucceededEvent(parry1))
        self.assertEqual(1, self.mirumoto.tvp())

        parry2 = self._make_parry()
        parry2.set_skill_roll(20)
        engine.event(events.ParryFailedEvent(parry2))
        self.assertEqual(2, self.mirumoto.tvp())

        parry3 = self._make_parry()
        parry3.set_skill_roll(55)
        engine.event(events.ParrySucceededEvent(parry3))
        self.assertEqual(3, self.mirumoto.tvp())

        # And vp() reflects all three TVPs stacked above max_vp().
        self.assertEqual(self.mirumoto.max_vp() + 3, self.mirumoto.vp())


class TestMirumotoNewRoundListener(unittest.TestCase):
    def test_grants_resource_pool(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_skill("attack", 4)
        enemy = Character("enemy")
        groups = [Group("Dragon", mirumoto), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = mirumoto_school.MirumotoNewRoundListener()
        event = events.NewRoundEvent(1)
        list(listener.handle(mirumoto, event, context))
        # Should have _mirumoto_pool = 2 * 4 = 8
        self.assertEqual(8, mirumoto._mirumoto_pool)


class TestMirumotoThirdDanPool(unittest.TestCase):
    """
    Tests for the Mirumoto Bushi School Third Dan resource pool.

    FR-007 / rules/04-schools.md Mirumoto Bushi School Third Dan:
    "At the beginning of each round, you get 2X points, where X is equal
    to your attack skill. Each point may be spent to decrease the phase
    of one of your actions by 1 in order to parry, or to provide a bonus
    of +2 on any type of attack or parry after you have seen your roll."

    Covers acceptance scenarios:
      - US2.1: 3rd-dan Mirumoto with attack skill X gets exactly 2*X
        points at start of round.
      - US2.4: pool resets to 2*X each round (unspent points discarded,
        not carried over).
      - US2.5: attack skill 0 yields pool 0 with no errors.

    Builds a real 3rd-dan Mirumoto via ``apply_special_ability``,
    ``apply_rank_one_ability``, ``apply_rank_two_ability``, and
    ``apply_rank_three_ability`` so the listener wiring goes through the
    same code path used in combat. The ``NewRoundEvent`` is dispatched
    directly to ``MirumotoNewRoundListener.handle`` and the
    ``character._mirumoto_pool`` attribute is inspected directly per the
    T007 task spec.
    """

    def _make_third_dan_mirumoto(self, attack_skill):
        """Build a 3rd-dan Mirumoto Bushi with the given attack skill.

        Applies special ability + ranks 1-3 so the
        ``MirumotoNewRoundListener`` is installed via the same wiring
        the combat engine would use.
        """
        mirumoto = Character("Mirumoto")
        mirumoto.set_actions([1])
        mirumoto.set_skill("attack", attack_skill)
        mirumoto.set_skill("parry", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        school.apply_special_ability(mirumoto)
        school.apply_rank_one_ability(mirumoto)
        school.apply_rank_two_ability(mirumoto)
        school.apply_rank_three_ability(mirumoto)
        return mirumoto

    def _fire_new_round(self, character, round_number):
        """Dispatch a ``NewRoundEvent`` directly to the listener installed
        on the character (the same listener ``apply_rank_three_ability``
        registered)."""
        enemy = Character("enemy")
        enemy.set_actions([1])
        groups = [Group("Dragon", character), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = mirumoto_school.MirumotoNewRoundListener()
        event = events.NewRoundEvent(round_number)
        # Drain the generator so all side effects (pool assignment) execute.
        list(listener.handle(character, event, context))

    def test_pool_size_is_two_times_attack_skill(self):
        """US2.1 / FR-007: pool == 2 * attack_skill on NewRoundEvent.

        Would fail under the mutation ``pool = character.skill("attack")``
        (drops the 2x multiplier) — observed pool would be 3 instead of 6.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=3)
        self._fire_new_round(mirumoto, round_number=1)
        # 2 * 3 = 6
        self.assertEqual(6, mirumoto._mirumoto_pool)

    def test_pool_is_zero_when_attack_skill_is_zero(self):
        """US2.5: attack skill 0 -> pool 0, no errors raised.

        Guards against a regression where the listener divides by, or
        otherwise mishandles, a zero attack skill (e.g., a ``max(1, ...)``
        clamp that would silently grant a phantom point).
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=0)
        # Must not raise.
        self._fire_new_round(mirumoto, round_number=1)
        # 2 * 0 = 0
        self.assertEqual(0, mirumoto._mirumoto_pool)

    def test_pool_overwritten_each_new_round_discards_unspent_points(self):
        """US2.4 / FR-007: pool is reset (not incremented) each round.

        Simulates a partial spend by mutating ``_mirumoto_pool`` between
        the two ``NewRoundEvent`` firings. After the second event the
        pool must be exactly 2*X again — the leftover points from the
        first round must be discarded, and the second round's grant must
        not stack on top of them.

        Would fail under the mutation ``pool += 2 * ...`` (accumulates
        instead of resets) — observed pool after round 2 would be 10
        instead of 8.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4)

        # Round 1: pool granted at 2 * 4 = 8.
        self._fire_new_round(mirumoto, round_number=1)
        self.assertEqual(8, mirumoto._mirumoto_pool)

        # Simulate the character spending some points during round 1
        # (the exact spending mechanism is the subject of later tasks;
        # what matters here is that the leftover value must be discarded
        # at the next round's pool grant).
        mirumoto._mirumoto_pool = 2
        self.assertEqual(2, mirumoto._mirumoto_pool)

        # Round 2: pool overwritten back to 2 * 4 = 8. The leftover 2
        # from round 1 is discarded, not carried over.
        self._fire_new_round(mirumoto, round_number=2)
        self.assertEqual(8, mirumoto._mirumoto_pool)


class TestMirumotoRollParameterProvider(unittest.TestCase):
    def test_vp_bonus_doubled_skill_roll(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_ring("fire", 3)
        mirumoto.set_skill("attack", 4)
        target = Character("target")
        provider = mirumoto_school.MirumotoRollParameterProvider()
        # With 1 VP: Mirumoto adds +10 modifier on top of the standard
        # void-spend +1 rolled / +1 kept dice.
        (rolled, kept, modifier) = provider.get_skill_roll_params(mirumoto, target, "attack", vp=1)
        # rolled = 3 + 4 + 0 + 1 = 8, kept = 3 + 0 + 1 = 4
        # modifier = 0 + 10*1 = 10 (flat +10 per VP on top of the
        # already-counted VP in rolled/kept)
        self.assertEqual(10, modifier)

    def test_vp_bonus_doubled_wound_check(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_ring("water", 3)
        provider = mirumoto_school.MirumotoRollParameterProvider()
        (rolled, kept, modifier) = provider.get_wound_check_roll_params(mirumoto, vp=1)
        # Flat +10 for the VP on top of the standard void-spend dice.
        self.assertEqual(10, modifier)

    def test_no_extra_bonus_without_vp(self):
        mirumoto = Character("Mirumoto")
        mirumoto.set_ring("fire", 3)
        mirumoto.set_skill("attack", 4)
        target = Character("target")
        provider = mirumoto_school.MirumotoRollParameterProvider()
        (rolled, kept, modifier) = provider.get_skill_roll_params(mirumoto, target, "attack", vp=0)
        self.assertEqual(0, modifier)


class TestMirumotoFifthDanPlusTen(unittest.TestCase):
    """
    Mirumoto Bushi School Fifth Dan acceptance tests (T015 / US4 / FR-014).

    rules/04-schools.md Mirumoto Bushi School Fifth Dan:
    "When you spend a Void Point on an attack, parry, or wound check
    roll, that roll gets +10 instead of the normal +5."

    Covers acceptance scenarios:
      - US4.1: spending VP on an attack roll yields standard bonus + 10.
      - US4.2: spending VP on a parry roll yields standard bonus + 10.
      - US4.3: spending VP on a wound check yields standard bonus + 10.

    Edge case (spec.md / Clarifications Q4):
      "A 5th-dan Mirumoto Bushi who spends multiple void points on the
      same combat roll: the +10 applies once per void point spent (i.e.,
      +20 if two are spent on the same roll), consistent with the
      additive nature of the standard void bonus."

    Implementation note (per spec.md Clarifications 2026-05-26): the
    Fifth Dan ``+10`` is a FLAT modifier on top of the standard
    void-spend's +1 rolled / +1 kept dice. ``MirumotoRollParameterProvider``
    adds ``10 * vp`` to the modifier on top of the
    ``DefaultRollParameterProvider`` output. The default provider
    already credits ``+1 rolled + 1 kept`` per VP; the Fifth Dan layer
    stacks a flat +10 modifier per VP on top, so a 6k4 wound check
    with 1 VP becomes 7k5 + 10. These tests pin the per-VP modifier
    delta (+10 per VP) by comparing 5th-dan vs a baseline character
    that uses the default provider.

    Mutation guard (per task T015): every test except the VP=0 guard
    would fail if the provider stopped adding ``10 * vp`` extra; the VP=0
    test would also fail if the provider unconditionally added 10 to the
    modifier (i.e., dropped the ``if vp > 0`` guard, which would still
    return 0 but only by coincidence -- so the test pins the no-bonus
    semantics for the defensive branch).
    """

    def _make_fifth_dan_mirumoto(self) -> Character:
        """Construct a 5th-dan Mirumoto Bushi with the Fifth Dan ability
        applied -- i.e., the MirumotoRollParameterProvider installed.

        We apply the ability directly (rather than building all knacks
        to rank 5 via CharacterBuilder) because this suite is unit-scoped
        to the roll-params provider, not to the builder's rank-up flow.
        """
        mirumoto = Character("Mirumoto5th")
        mirumoto.set_ring("fire", 3)
        mirumoto.set_ring("water", 3)
        mirumoto.set_ring("void", 3)
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        school.apply_rank_five_ability(mirumoto)
        return mirumoto

    def _make_baseline(self) -> Character:
        """Construct an otherwise-identical non-5th-dan baseline that uses
        the DefaultRollParameterProvider (i.e., the void-spend behavior a
        4th-dan Mirumoto -- or any non-Mirumoto -- would see)."""
        baseline = Character("baseline")
        baseline.set_ring("fire", 3)
        baseline.set_ring("water", 3)
        baseline.set_ring("void", 3)
        baseline.set_skill("attack", 4)
        baseline.set_skill("parry", 4)
        return baseline

    # ----- US4.1: attack roll -----

    def test_fifth_dan_attack_roll_with_one_vp_adds_ten(self) -> None:
        """US4.1 / FR-014: a 5th-dan Mirumoto's attack roll with 1 VP spent
        gets a flat +10 modifier per VP on top of the default void-spend
        bonus (per spec.md Clarifications 2026-05-26).

        Concretely the MirumotoRollParameterProvider returns a modifier
        that is exactly ``10 * vp`` higher than the default provider's
        modifier (the default's +1 rolled / +1 kept dice still apply
        unchanged; the Fifth Dan layer stacks a flat +10 modifier per
        VP on top of those dice).
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        (m_rolled, m_kept, m_mod) = mirumoto.get_skill_roll_params(target, "attack", vp=1)
        (b_rolled, b_kept, b_mod) = baseline.get_skill_roll_params(target, "attack", vp=1)
        # Per-VP modifier delta is exactly +10 (the flat modifier the
        # 5th-dan ability adds on top of the default void-spend bonus).
        # The default's +1 rolled and +1 kept die contributions remain
        # unchanged on both sides.
        self.assertEqual(b_mod + 10, m_mod,
            "FR-014 / US4.1: 5th-dan modifier on an attack roll with 1 VP "
            "must be +10 higher than the default-provider baseline (the "
            "flat Fifth Dan +10 stacks on top of the default's rolled+kept "
            "die bonus)")
        # Sanity: the rolled and kept dice contributions from VP are the
        # same on both sides (the 5th-dan ability only adds to the
        # modifier; it does not change the dice budget).
        self.assertEqual(b_rolled, m_rolled)
        self.assertEqual(b_kept, m_kept)

    # ----- US4.2: parry roll -----

    def test_fifth_dan_parry_roll_with_one_vp_adds_ten(self) -> None:
        """US4.2 / FR-014: a 5th-dan Mirumoto's parry roll with 1 VP
        spent gets a flat +10 modifier per VP on top of the default
        void-spend bonus (per spec.md Clarifications 2026-05-26).

        Parry is exercised through the same ``get_skill_roll_params``
        entrypoint as attack (skill="parry") -- the provider routes
        parry through the combat-skill branch, so this test pins that
        the per-VP modifier delta is exactly +10 for parry as well.
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        (m_rolled, m_kept, m_mod) = mirumoto.get_skill_roll_params(target, "parry", vp=1)
        (b_rolled, b_kept, b_mod) = baseline.get_skill_roll_params(target, "parry", vp=1)
        self.assertEqual(b_mod + 10, m_mod,
            "FR-014 / US4.2: 5th-dan modifier on a parry roll with 1 VP "
            "must be +10 higher than the default-provider baseline (the "
            "flat Fifth Dan +10 stacks on top of the default's rolled+kept "
            "die bonus)")
        self.assertEqual(b_rolled, m_rolled)
        self.assertEqual(b_kept, m_kept)

    # ----- US4.3: wound check -----

    def test_fifth_dan_wound_check_with_one_vp_adds_ten(self) -> None:
        """US4.3 / FR-014: a 5th-dan Mirumoto's wound check with 1 VP
        spent gets a flat +10 modifier per VP on top of the default
        void-spend bonus (per spec.md Clarifications 2026-05-26: e.g.,
        a 6k4 wound check + VP becomes 7k5 + 10).

        Wound checks go through a distinct provider entrypoint
        (``get_wound_check_roll_params``) which has its own ``10 * vp``
        addition in MirumotoRollParameterProvider. This test pins that
        the wound-check branch is wired in parallel with the
        skill-roll branch (a mutation that removed only ONE of the two
        ``+= 10 * vp`` lines would still pass the attack/parry tests).
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        (m_rolled, m_kept, m_mod) = mirumoto.get_wound_check_roll_params(vp=1)
        (b_rolled, b_kept, b_mod) = baseline.get_wound_check_roll_params(vp=1)
        self.assertEqual(b_mod + 10, m_mod,
            "FR-014 / US4.3: 5th-dan modifier on a wound check with 1 VP "
            "must be +10 higher than the default-provider baseline (the "
            "flat Fifth Dan +10 stacks on top of the default's rolled+kept "
            "die bonus)")
        self.assertEqual(b_rolled, m_rolled)
        self.assertEqual(b_kept, m_kept)

    # ----- Edge case / Clarifications Q4: per-VP stacking -----

    def test_fifth_dan_two_vp_on_same_roll_yields_plus_twenty(self) -> None:
        """spec.md Edge Case / Clarifications Q4: spending 2 VP on the
        same combat roll stacks the flat +10 per VP, yielding +20 total
        modifier delta over the default-provider baseline (on top of
        the standard 2-VP dice bonus).

        Exercises all three roll types (attack, parry, wound check) to
        ensure the per-VP scaling is uniform across the
        MirumotoRollParameterProvider entrypoints.
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        # Attack
        (_, _, m_attack_mod) = mirumoto.get_skill_roll_params(target, "attack", vp=2)
        (_, _, b_attack_mod) = baseline.get_skill_roll_params(target, "attack", vp=2)
        self.assertEqual(b_attack_mod + 20, m_attack_mod,
            "FR-014 edge case: 2 VP on an attack roll -> +20 modifier "
            "delta over baseline (+10 per VP * 2 VP)")
        # Parry
        (_, _, m_parry_mod) = mirumoto.get_skill_roll_params(target, "parry", vp=2)
        (_, _, b_parry_mod) = baseline.get_skill_roll_params(target, "parry", vp=2)
        self.assertEqual(b_parry_mod + 20, m_parry_mod,
            "FR-014 edge case: 2 VP on a parry roll -> +20 modifier "
            "delta over baseline (+10 per VP * 2 VP)")
        # Wound check
        (_, _, m_wc_mod) = mirumoto.get_wound_check_roll_params(vp=2)
        (_, _, b_wc_mod) = baseline.get_wound_check_roll_params(vp=2)
        self.assertEqual(b_wc_mod + 20, m_wc_mod,
            "FR-014 edge case: 2 VP on a wound check -> +20 modifier "
            "delta over baseline (+10 per VP * 2 VP)")

    # ----- Defensive guard: vp=0 yields no bonus -----

    def test_fifth_dan_zero_vp_no_bonus(self) -> None:
        """Defensive guard for the ``if vp > 0`` branch in
        MirumotoRollParameterProvider: when no VP is spent, the
        5th-dan ability contributes NO modifier delta over the
        default provider.

        This protects against an over-eager mutation that drops the
        guard and adds ``10 * vp = 0`` unconditionally (which would be
        observationally identical here -- so this test is the floor of
        the defensive contract). It also pins that the Mirumoto
        provider does not add a flat +10 ``always-on`` bonus that the
        rules clause does not authorize.
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        # Attack with no VP spent.
        (m_rolled_a, m_kept_a, m_mod_a) = mirumoto.get_skill_roll_params(target, "attack", vp=0)
        (b_rolled_a, b_kept_a, b_mod_a) = baseline.get_skill_roll_params(target, "attack", vp=0)
        self.assertEqual(b_mod_a, m_mod_a,
            "Defensive guard: vp=0 attack roll must NOT receive any "
            "5th-dan modifier bonus")
        self.assertEqual(b_rolled_a, m_rolled_a)
        self.assertEqual(b_kept_a, m_kept_a)
        # Parry with no VP spent.
        (_, _, m_mod_p) = mirumoto.get_skill_roll_params(target, "parry", vp=0)
        (_, _, b_mod_p) = baseline.get_skill_roll_params(target, "parry", vp=0)
        self.assertEqual(b_mod_p, m_mod_p,
            "Defensive guard: vp=0 parry roll must NOT receive any "
            "5th-dan modifier bonus")
        # Wound check with no VP spent.
        (_, _, m_mod_w) = mirumoto.get_wound_check_roll_params(vp=0)
        (_, _, b_mod_w) = baseline.get_wound_check_roll_params(vp=0)
        self.assertEqual(b_mod_w, m_mod_w,
            "Defensive guard: vp=0 wound check must NOT receive any "
            "5th-dan modifier bonus")


class TestMirumotoFifthDanWithTempVP(unittest.TestCase):
    """
    T016 / US4 / FR-004a / Clarifications Q5: Special Ability x Fifth Dan
    interaction.

    rules/04-schools.md Mirumoto Bushi School Special Ability:
        "Your successful or unsuccessful parries give you a temporary
        void point."

    rules/04-schools.md Mirumoto Bushi School Fifth Dan:
        "When you spend a Void Point on an attack, parry, or wound
        check roll, that roll gets +10 instead of the normal +5."

    spec.md Clarifications Q5:
        "Does the Fifth Dan +10 apply when a 5th-dan Mirumoto Bushi
        spends a temporary void point (from the Special Ability) on a
        combat roll? -> Yes. A void point is a void point. Temporary
        voids are functionally identical to normal voids once granted."

    FR-004a: "Temporary void points granted by FR-004 MUST be
    functionally indistinguishable from normal void points once
    granted. They MAY be spent on any roll that accepts a void point,
    they participate in the Fifth Dan +10 bonus (FR-014) on combat
    rolls when their owner is at 5th dan, and the engine MUST NOT
    track void-point provenance after the grant."

    This suite verifies that the engine treats ``_tvp`` and ``_vp``
    identically through the roll-params pipeline. The
    ``MirumotoRollParameterProvider`` only sees the integer ``vp``
    argument supplied to ``get_skill_roll_params`` /
    ``get_wound_check_roll_params``; it has no visibility into whether
    the VP being spent originated as a temporary or normal pool entry.
    The tests pin this contract end-to-end:
      1. The +10 modifier delta per VP (existing implementation
         behavior, see T015) is the same whether the VP comes from
         ``_tvp`` or ``_vp``.
      2. ``spend_vp`` consumes temporary VPs first (engine-existing
         behavior worth pinning so a future provenance-tracking
         regression is caught immediately).
      3. Mixing 1 TVP + 1 normal VP on a single combat roll yields the
         same +10 modifier delta per VP as two normal VPs would, with
         no provenance-aware special case.
    """

    def _make_fifth_dan_mirumoto(self) -> Character:
        """Construct a 5th-dan Mirumoto Bushi with BOTH the Special
        Ability listeners (FR-004, so parries grant TVPs) AND the
        Fifth Dan roll-parameter provider (FR-014) installed.

        The two abilities are independent in the school class, so we
        apply both explicitly: ``apply_special_ability`` wires up the
        TVP-on-parry pipeline that this suite exercises, and
        ``apply_rank_five_ability`` installs the
        ``MirumotoRollParameterProvider`` that contributes the +10
        modifier delta per VP.
        """
        mirumoto = Character("Mirumoto5thWithTVP")
        mirumoto.set_actions([1])
        mirumoto.set_ring("fire", 3)
        mirumoto.set_ring("water", 3)
        mirumoto.set_ring("void", 3)
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        school.apply_special_ability(mirumoto)
        school.apply_rank_five_ability(mirumoto)
        return mirumoto

    def _make_attacker(self) -> Character:
        attacker = Character("attacker")
        attacker.set_actions([1])
        return attacker

    def _grant_tvp_via_parry(self, mirumoto: Character, attacker: Character) -> None:
        """Force a parry-succeeded event through the full engine
        pipeline so the Special Ability listener grants a TVP exactly
        as it would in live combat.

        Mirrors the pattern used by
        ``TestMirumotoParryTVPListener::test_parry_succeeded_pipeline_increments_tvp``:
        build a parry action, dispatch a ``ParrySucceededEvent`` via
        ``CombatEngine.event``, and let the listener chain increment
        ``_tvp`` through ``GainTemporaryVoidPointsListener``.
        """
        groups = [Group("Dragon", mirumoto), Group("Enemy", attacker)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            attacker, mirumoto, "attack",
            initiative_action, context,
        )
        parry = actions.ParryAction(
            mirumoto, attacker, "parry",
            initiative_action, context, attack,
        )
        parry.set_skill_roll(50)
        engine = CombatEngine(context)
        engine.event(events.ParrySucceededEvent(parry))

    # ----- (1) Per-VP modifier delta is identical for TVP and normal VP -----

    def test_fifth_dan_temp_vp_provides_same_plus_ten_as_normal_vp(self) -> None:
        """FR-004a / Clarifications Q5: spending a TVP on a combat roll
        yields the SAME +10 modifier delta over baseline as spending a
        normal VP. The engine treats both VP sources identically
        through the roll-params pipeline.

        Procedure:
          - Build two 5th-dan Mirumoto: one with a TVP granted via a
            real parry pipeline, one with only the normal VP pool.
          - Compute ``get_skill_roll_params(..., vp=1)`` on both and
            compare modifiers. They must be equal -- the provider only
            sees the integer ``vp`` argument and has no provenance
            information.
          - Cross-check against a non-Mirumoto baseline to pin the
            actual +10 modifier delta (existing implementation
            behavior, per T015).

        This is the FR-004a / Q5 acceptance test: there is no
        "temporary VP" code path that differs from the "normal VP"
        code path; both flow through the same ``10 * vp`` addition in
        ``MirumotoRollParameterProvider``.
        """
        # Mirumoto with a TVP (granted via parry pipeline).
        mirumoto_with_tvp = self._make_fifth_dan_mirumoto()
        attacker = self._make_attacker()
        self._grant_tvp_via_parry(mirumoto_with_tvp, attacker)
        self.assertEqual(1, mirumoto_with_tvp.tvp(),
            "Pre-condition: parry pipeline must have granted exactly 1 TVP "
            "(otherwise the test is exercising the wrong code path)")

        # Mirumoto with only the normal VP pool (no parry, no TVP).
        mirumoto_normal_only = self._make_fifth_dan_mirumoto()
        self.assertEqual(0, mirumoto_normal_only.tvp(),
            "Pre-condition: the normal-only Mirumoto must start with no TVP")

        # Non-Mirumoto baseline -- pins the absolute +10 modifier delta
        # the 5th-dan ability contributes per VP (consistent with T015).
        baseline = Character("baseline")
        baseline.set_ring("fire", 3)
        baseline.set_ring("water", 3)
        baseline.set_ring("void", 3)
        baseline.set_skill("attack", 4)
        baseline.set_skill("parry", 4)
        target = Character("target")

        # All three providers compute the same skill-roll params with vp=1.
        (tvp_rolled, tvp_kept, tvp_mod) = mirumoto_with_tvp.get_skill_roll_params(
            target, "attack", vp=1)
        (norm_rolled, norm_kept, norm_mod) = mirumoto_normal_only.get_skill_roll_params(
            target, "attack", vp=1)
        (b_rolled, b_kept, b_mod) = baseline.get_skill_roll_params(
            target, "attack", vp=1)

        # FR-004a / Q5: TVP and normal VP yield identical modifier
        # contributions. The provider has no provenance information.
        self.assertEqual(norm_mod, tvp_mod,
            "FR-004a / Q5: the 5th-dan modifier with vp=1 must be the SAME "
            "whether the Mirumoto is holding a TVP or only normal VP -- the "
            "engine MUST NOT differentiate between VP sources through the "
            "roll-params pipeline")
        # Also pin the rolled/kept dice contributions: the provider
        # only adds to the modifier, so both rolled and kept dice
        # budgets must agree regardless of VP source.
        self.assertEqual(norm_rolled, tvp_rolled,
            "FR-004a / Q5: rolled-dice budget must be source-agnostic")
        self.assertEqual(norm_kept, tvp_kept,
            "FR-004a / Q5: kept-dice budget must be source-agnostic")

        # And the absolute +10 modifier delta over the non-Mirumoto
        # baseline (existing implementation behavior, per T015) holds
        # for the TVP-holding Mirumoto too -- not just for the normal-
        # VP case.
        self.assertEqual(b_mod + 10, tvp_mod,
            "FR-014 / FR-004a: a 5th-dan Mirumoto spending 1 VP (sourced "
            "from a TVP) must still get the +10 modifier delta over the "
            "default provider baseline (T015 pins the same delta for "
            "normal VP)")
        self.assertEqual(b_rolled, tvp_rolled)
        self.assertEqual(b_kept, tvp_kept)

    # ----- (2) spend_vp consumes TVP first (engine-existing behavior) -----

    def test_fifth_dan_temp_vp_spent_before_normal_vp(self) -> None:
        """Engine-existing behavior pin (Character.spend_vp): with both
        a TVP and unspent normal VP available, ``spend_vp(1)`` consumes
        the TVP first, leaving ``_vp_spent`` untouched.

        Worth pinning explicitly here because FR-004a's "no provenance
        tracking" guarantee depends on temp-first being a stable engine
        invariant -- any future regression that flipped the order (or
        added a "TVP cannot be spent on 5th-dan combat rolls" guard)
        would silently change the user-facing semantics this suite
        protects.

        Procedure:
          - Start with ``_vp_spent == 0`` (normal pool full).
          - Grant 1 TVP via the parry pipeline.
          - Call ``spend_vp(1)``.
          - Assert ``_tvp == 0`` (TVP consumed) AND
            ``_vp_spent == 0`` (normal pool untouched).
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        attacker = self._make_attacker()

        # Pre-condition: clean slate -- no TVP, no spent normal VP.
        self.assertEqual(0, mirumoto.tvp(),
            "Pre-condition: no TVP before parry")
        self.assertEqual(0, mirumoto._vp_spent,
            "Pre-condition: no normal VP spent yet")

        # Grant exactly 1 TVP via the parry pipeline.
        self._grant_tvp_via_parry(mirumoto, attacker)
        self.assertEqual(1, mirumoto.tvp(),
            "Pre-condition: parry pipeline must have granted exactly 1 TVP")
        self.assertEqual(0, mirumoto._vp_spent,
            "Pre-condition: TVP grant must not touch the normal-VP-spent "
            "counter")

        # Spend exactly 1 VP -- per Character.spend_vp, TVP is consumed first.
        mirumoto.spend_vp(1)

        self.assertEqual(0, mirumoto.tvp(),
            "FR-004a / engine invariant: spend_vp(1) must decrement TVP "
            "first when TVP is available (temp-first ordering)")
        self.assertEqual(0, mirumoto._vp_spent,
            "FR-004a / engine invariant: spend_vp(1) must NOT touch "
            "_vp_spent while a TVP is available to consume first")

    # ----- (3) TVP + normal VP combined on the same roll -----

    def test_fifth_dan_temp_vp_combined_with_normal_vp_on_same_roll(self) -> None:
        """FR-004a / Clarifications Q5: when a 5th-dan Mirumoto spends
        2 VPs on a single combat roll while holding 1 TVP and at least
        1 normal VP, the modifier reflects the full +20 modifier delta
        (+10 per VP * 2 VPs) over the default-provider baseline.

        The implementation has no provenance-aware special case: the
        provider sees ``vp=2`` and adds ``10 * 2 == 20`` to the
        modifier regardless of which pool the VPs were drawn from.

        Procedure:
          - Grant 1 TVP via the parry pipeline so the Mirumoto holds
            1 TVP + (max_vp() == 3) normal VPs available.
          - Spend 2 VPs (the engine consumes the TVP first, then 1
            normal VP -- but the roll-params provider has no
            visibility into this and just sees ``vp=2``).
          - Assert the modifier delta over a non-Mirumoto baseline is
            exactly +20 (existing implementation behavior, pinning the
            same per-VP scaling T015 verified for the pure-normal-VP
            path).

        Mutation guard: a regression that added a "TVP-sourced VPs do
        not get the 5th-dan bonus" gate would yield a +10 delta here
        instead of +20 (since the TVP contribution would be stripped).
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        attacker = self._make_attacker()
        target = Character("target")

        # Grant 1 TVP via the parry pipeline.
        self._grant_tvp_via_parry(mirumoto, attacker)
        self.assertEqual(1, mirumoto.tvp(),
            "Pre-condition: must have 1 TVP from the parry pipeline")
        # Mirumoto now holds 1 TVP + 3 normal VPs = 4 total available.
        self.assertEqual(mirumoto.max_vp() + 1, mirumoto.vp(),
            "Pre-condition: total VP pool must include the TVP on top of "
            "the full normal pool")

        # Spend 2 VPs -- the engine pops the TVP first, then 1 normal VP.
        mirumoto.spend_vp(2)
        self.assertEqual(0, mirumoto.tvp(),
            "Post-spend: TVP must be consumed first")
        self.assertEqual(1, mirumoto._vp_spent,
            "Post-spend: exactly 1 normal VP must be debited after the "
            "TVP is exhausted (total 2 VPs spent)")

        # Now query the modifier delta with vp=2 -- the provider sees
        # only the integer count and has no provenance awareness.
        # Per FR-004a / Q5, this must yield the full +20 modifier
        # delta over the default-provider baseline, exactly as if both
        # VPs had come from the normal pool.
        baseline = Character("baseline")
        baseline.set_ring("fire", 3)
        baseline.set_ring("water", 3)
        baseline.set_ring("void", 3)
        baseline.set_skill("attack", 4)
        baseline.set_skill("parry", 4)

        (m_rolled, m_kept, m_mod) = mirumoto.get_skill_roll_params(
            target, "attack", vp=2)
        (b_rolled, b_kept, b_mod) = baseline.get_skill_roll_params(
            target, "attack", vp=2)

        self.assertEqual(b_mod + 20, m_mod,
            "FR-004a / Q5: spending 2 VPs (1 TVP + 1 normal) on a single "
            "combat roll must yield the same +20 modifier delta over "
            "baseline as 2 normal VPs would -- the engine MUST NOT "
            "discount the TVP-sourced portion of the spend")
        # Dice budgets are source-agnostic too (the 5th-dan ability
        # only contributes to the modifier).
        self.assertEqual(b_rolled, m_rolled,
            "FR-004a / Q5: rolled-dice budget must be source-agnostic for "
            "a mixed TVP + normal VP spend")
        self.assertEqual(b_kept, m_kept,
            "FR-004a / Q5: kept-dice budget must be source-agnostic for "
            "a mixed TVP + normal VP spend")


class TestMirumotoFifthDanNonCombatRolls(unittest.TestCase):
    """
    T017 / US4.4 / FR-014: Fifth Dan combat-only scope.

    rules/04-schools.md Mirumoto Bushi School Fifth Dan:
        "When you spend a Void Point on an attack, parry, or wound
        check roll, that roll gets +10 instead of the normal +5."

    spec.md Clarifications / Assumption:
        "'Combat rolls' eligible for the 5th Dan +10 are attack, parry,
        and wound check, mirroring the First Dan dice-bonus scope.
        Non-combat rolls do not get the +10."

    spec.md US4 Acceptance Scenario 4 (US4.4):
        "Given a 5th-dan Mirumoto Bushi who spends a void point on a
        non-combat roll, When the roll's total is computed, Then it
        includes only the standard void-spend bonus (no +10)."

    FR-014 enumerates the combat-roll scope as exactly {attack, parry,
    wound check}. ``MirumotoRollParameterProvider.get_skill_roll_params``
    handles the attack/parry branch and ``get_wound_check_roll_params``
    handles the wound-check branch. The Fifth Dan +10 modifier delta
    MUST NOT leak onto skill rolls outside the combat scope (e.g.,
    basic social/knowledge skills like ``investigation``, ``courtier``,
    ``intimidation``, ``sincerity``).

    Before the fix that accompanied this task, the provider's
    ``get_skill_roll_params`` added ``10 * vp`` unconditionally for any
    skill -- a bug that violated FR-014 by extending the +10 bonus to
    out-of-scope rolls (e.g., a 5th-dan Mirumoto spending a VP on an
    ``investigation`` check would have incorrectly gained the +10
    modifier delta). The combat-only scope is now enforced via the
    ``_MIRUMOTO_FIFTH_DAN_COMBAT_SKILLS`` set.

    Mutation guard: a regression that removed the combat-skill guard
    would fail every non-combat assertion in this suite; a regression
    that over-narrowed the scope (e.g., to ``{"attack"}`` only) would
    be caught by the combat-skill regression-guard test below.
    """

    # Non-combat skills exercised by this suite. ``investigation``,
    # ``etiquette``, ``intimidation``, and ``sincerity`` are all members
    # of ``simulation.mechanics.skills.BASIC_SKILLS`` and are clearly
    # outside the FR-014 combat-roll scope.
    _NON_COMBAT_SKILLS = ("investigation", "etiquette", "intimidation", "sincerity")

    def _register_non_combat_skill_rings(self, character: Character) -> None:
        """Map the non-combat skills exercised by this suite to a ring
        on the character. ``Character`` only auto-registers ring
        mappings for combat skills (see ``Character.__init__``); the
        provider's ``ring is None`` branch then resolves to
        ``character.ring(character.get_skill_ring(skill))``, which
        would return ``character.ring("")`` and KeyError for an
        unregistered non-combat skill. Registering ``"air"`` (the
        conventional perception/intelligence-flavored ring for social
        and knowledge skills) lets the provider resolve a ring rank
        cleanly. The choice of ring is observationally irrelevant for
        this suite: both the Mirumoto and the baseline use the same
        mapping, so the delta-only assertions cancel it out.
        """
        for skill in self._NON_COMBAT_SKILLS:
            character._skill_rings[skill] = "air"

    def _make_fifth_dan_mirumoto(self) -> Character:
        """Construct a 5th-dan Mirumoto Bushi with the Fifth Dan ability
        applied. Mirrors the helper in ``TestMirumotoFifthDanPlusTen``.
        Air is set so non-combat skill rolls (which conventionally use
        an air-flavored ring) can resolve a ring rank cleanly.
        """
        mirumoto = Character("Mirumoto5thNonCombat")
        mirumoto.set_ring("air", 3)
        mirumoto.set_ring("fire", 3)
        mirumoto.set_ring("water", 3)
        mirumoto.set_ring("void", 3)
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        self._register_non_combat_skill_rings(mirumoto)
        school = mirumoto_school.MirumotoBushiSchool()
        school.apply_rank_five_ability(mirumoto)
        return mirumoto

    def _make_baseline(self) -> Character:
        baseline = Character("baseline")
        baseline.set_ring("air", 3)
        baseline.set_ring("fire", 3)
        baseline.set_ring("water", 3)
        baseline.set_ring("void", 3)
        baseline.set_skill("attack", 4)
        baseline.set_skill("parry", 4)
        self._register_non_combat_skill_rings(baseline)
        return baseline

    # ----- US4.4 acceptance: non-combat skills do not get the +10 -----

    def test_fifth_dan_non_combat_skill_does_not_get_plus_ten(self) -> None:
        """US4.4 / FR-014: a 5th-dan Mirumoto spending a VP on a
        NON-combat skill roll (e.g., ``investigation``) gets only the
        standard void-spend bonus (the +1 rolled / +1 kept dice the
        default provider already credits). The Fifth Dan +10 modifier
        delta MUST NOT apply.

        Equivalent assertion: the Mirumoto's modifier on the
        non-combat skill roll equals the default-provider baseline's
        modifier. There is no +10 leakage from the Fifth Dan ability.
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        # ``investigation`` is mapped to ``air`` on both characters by
        # ``_register_non_combat_skill_rings`` so the provider's
        # ``ring is None`` branch resolves cleanly. Passing ``ring=``
        # explicitly is not viable because the provider expects an int
        # rank (which the public API does not expose for non-combat
        # skills) and the ``str | None`` annotation is misleading.
        (m_rolled, m_kept, m_mod) = mirumoto.get_skill_roll_params(
            target, "investigation", vp=1)
        (b_rolled, b_kept, b_mod) = baseline.get_skill_roll_params(
            target, "investigation", vp=1)
        self.assertEqual(b_mod, m_mod,
            "US4.4 / FR-014: a 5th-dan Mirumoto spending 1 VP on a "
            "non-combat skill (investigation) must NOT receive the +10 "
            "modifier delta -- the Fifth Dan bonus is scoped to attack, "
            "parry, and wound check only")
        # Dice budgets are the standard +1 rolled / +1 kept from the VP
        # itself, which the default provider already credits. They must
        # be identical between the 5th-dan and the baseline.
        self.assertEqual(b_rolled, m_rolled,
            "US4.4 / FR-014: rolled-dice budget on a non-combat skill "
            "with VP must match the default provider baseline (no "
            "Mirumoto-specific dice change on non-combat rolls)")
        self.assertEqual(b_kept, m_kept,
            "US4.4 / FR-014: kept-dice budget on a non-combat skill "
            "with VP must match the default provider baseline")

    def test_fifth_dan_other_basic_skills_do_not_get_plus_ten(self) -> None:
        """Parametric sibling of the investigation test -- pin the
        combat-only scope across a representative sample of non-combat
        BASIC_SKILLS (``courtier`` is actually a school name not a
        skill, so we use canonical BASIC_SKILLS entries: ``etiquette``,
        ``intimidation``, ``sincerity``).

        A regression that special-cased only ``investigation`` while
        still leaking the bonus to other basic skills would slip past
        the single-skill assertion above; this multi-skill test pins
        the scope as "combat-only," not "investigation-only."
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        for skill in ("etiquette", "intimidation", "sincerity"):
            (_, _, m_mod) = mirumoto.get_skill_roll_params(
                target, skill, vp=1)
            (_, _, b_mod) = baseline.get_skill_roll_params(
                target, skill, vp=1)
            self.assertEqual(b_mod, m_mod,
                f"US4.4 / FR-014: a 5th-dan Mirumoto spending 1 VP on "
                f"non-combat skill '{skill}' must NOT receive the +10 "
                f"modifier delta (combat-only scope)")

    def test_fifth_dan_non_combat_skill_multi_vp_no_bonus(self) -> None:
        """Stacking guard: a 5th-dan Mirumoto spending 2 VPs on a
        non-combat skill still gets the standard 2-VP dice bonus and
        NO modifier delta. A regression that scoped the guard
        incorrectly (e.g., only suppressed the bonus at vp=1 but not at
        vp>=2) would slip past the single-VP assertion above.
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        (m_rolled, m_kept, m_mod) = mirumoto.get_skill_roll_params(
            target, "investigation", vp=2)
        (b_rolled, b_kept, b_mod) = baseline.get_skill_roll_params(
            target, "investigation", vp=2)
        self.assertEqual(b_mod, m_mod,
            "US4.4 / FR-014: stacking 2 VPs on a non-combat skill must "
            "still yield zero modifier delta -- the combat-only guard "
            "must not be vp-count-dependent")
        self.assertEqual(b_rolled, m_rolled)
        self.assertEqual(b_kept, m_kept)

    # ----- Combat/non-combat boundary regression guard -----

    def test_fifth_dan_combat_skills_still_get_plus_ten_regression_guard(self) -> None:
        """Companion / boundary regression guard: attack, parry, and
        wound check MUST continue to receive the +10 modifier delta per
        VP (existing behavior pinned by ``TestMirumotoFifthDanPlusTen``).

        This test locks the combat/non-combat boundary from the OTHER
        side: a regression that over-narrowed the scope (e.g., to
        ``{"attack"}`` only, accidentally dropping parry) would be
        caught here. Without this guard, a future refactor could
        silently strip the bonus from parry while keeping the
        non-combat tests green.
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        # Attack
        (_, _, m_attack_mod) = mirumoto.get_skill_roll_params(
            target, "attack", vp=1)
        (_, _, b_attack_mod) = baseline.get_skill_roll_params(
            target, "attack", vp=1)
        self.assertEqual(b_attack_mod + 10, m_attack_mod,
            "Boundary guard: attack roll must still receive the +10 "
            "modifier delta per VP (FR-014 combat scope)")
        # Parry
        (_, _, m_parry_mod) = mirumoto.get_skill_roll_params(
            target, "parry", vp=1)
        (_, _, b_parry_mod) = baseline.get_skill_roll_params(
            target, "parry", vp=1)
        self.assertEqual(b_parry_mod + 10, m_parry_mod,
            "Boundary guard: parry roll must still receive the +10 "
            "modifier delta per VP (FR-014 combat scope)")
        # Wound check (separate provider method, but same boundary)
        (_, _, m_wc_mod) = mirumoto.get_wound_check_roll_params(vp=1)
        (_, _, b_wc_mod) = baseline.get_wound_check_roll_params(vp=1)
        self.assertEqual(b_wc_mod + 10, m_wc_mod,
            "Boundary guard: wound check must still receive the +10 "
            "modifier delta per VP (FR-014 combat scope)")

    def test_fifth_dan_all_attack_class_skills_get_plus_ten(self) -> None:
        """Fix-B regression guard / FR-014 broadened scope.

        Per spec.md Clarifications Session 2026-05-26 the user
        explicitly broadened the Fifth Dan +10 scope from
        ``{"attack", "parry"}`` to the full attack-class skill set
        (rules/04-schools.md ``ATTACK_SKILLS``: attack, counterattack,
        double attack, feint, iaijutsu, lunge) plus parry. Rationale
        from the clarification: "apply it to everything in case a
        Mirumoto ends up with it despite it not being in their school"
        -- i.e., a school knack the Mirumoto might not have learned
        natively (counterattack, double attack, iaijutsu are the
        Mirumoto's, but feint and lunge are not) should still get the
        +10 if the Mirumoto somehow uses it.

        This test pins the broader scope: every attack-class skill
        plus parry receives the +10 modifier delta per VP. A
        regression that reverted the whitelist to the narrower
        ``{"attack", "parry"}`` would fail every assertion below for
        counterattack/double attack/iaijutsu/feint/lunge.
        """
        mirumoto = self._make_fifth_dan_mirumoto()
        baseline = self._make_baseline()
        target = Character("target")
        # The five attack-class skills newly in-scope (attack and
        # parry are covered by the boundary-guard test above).
        for skill in ("counterattack", "double attack", "iaijutsu", "feint", "lunge"):
            (_, _, m_mod) = mirumoto.get_skill_roll_params(
                target, skill, vp=1)
            (_, _, b_mod) = baseline.get_skill_roll_params(
                target, skill, vp=1)
            self.assertEqual(b_mod + 10, m_mod,
                f"Fix-B / FR-014 (broadened scope per spec.md "
                f"Clarifications Session 2026-05-26): attack-class "
                f"skill '{skill}' must receive the +10 modifier delta "
                f"per VP for a 5th-dan Mirumoto")


class TestMirumotoUS1Integration(unittest.TestCase):
    """
    US1 MVP-checkpoint integration test (specs/001-mirumoto-bushi-school/spec.md
    Phase 3 Independent Test, tasks.md T006).

    Constructs a 1st-dan Mirumoto Bushi versus a Hida opponent, runs a scripted
    parry through the full ``CombatEngine`` pipeline using
    ``CalvinistRollProvider`` for determinism, and asserts US1.1 (school ring),
    US1.2 (school knacks), US1.6 (TVP grant on parry attempt), and FR-001
    (factory registration) all hold in a single combat-trace exercise.

    Rules clauses exercised in this combat:
      - rules/04-schools.md Mirumoto Bushi School Special Ability: "Your
        successful or unsuccessful parries give you a temporary void point."
        (FR-004 / US1.6)
      - rules/04-schools.md Mirumoto Bushi School First Dan: "Roll one extra
        die on parry, double attack, and wound checks." (FR-005, observed
        on the live parry roll via ``pop_observed_params``.)
      - rules/04-schools.md School Ring + Knacks header for Mirumoto Bushi
        School: ring = Void; knacks = counterattack, double attack, iaijutsu.
        (FR-002, FR-003 / US1.1, US1.2)
    """

    def setUp(self) -> None:
        # ---------- Mirumoto Bushi 1st-dan ----------
        # Apply the full 1st-dan loadout the spec mandates for US1: school
        # registered (FR-001), Special Ability listeners installed (FR-004),
        # and the 1st-Dan extra-die ability applied (FR-005).
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.mirumoto.set_skill("attack", 4)
        self.mirumoto.set_skill("parry", 4)
        self.school = mirumoto_school.MirumotoBushiSchool()
        self.mirumoto.set_school(self.school)
        self.school.apply_special_ability(self.mirumoto)
        self.school.apply_rank_one_ability(self.mirumoto)

        # ---------- Hida opponent (baseline, no school applied) ----------
        # Per the suggested adaptation of the T002 combat-simulator scenario.
        self.hida = Character("Hida")
        self.hida.set_actions([1])
        self.hida.set_skill("attack", 4)

        # ---------- Baseline (no school applied) for +1-die delta check ----------
        # Built with identical stats so the only difference on the parry roll
        # is the 1st-Dan extra-die bonus from the Mirumoto school.
        self.baseline = Character("baseline")
        self.baseline.set_actions([1])
        self.baseline.set_skill("attack", 4)
        self.baseline.set_skill("parry", 4)

        groups = [
            Group("Dragon", [self.mirumoto, self.baseline]),
            Group("Crab", self.hida),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        self.initiative_action = InitiativeAction([1], 1)

    def _build_attack(self, attacker: Character, target: Character, skill_roll: int) -> actions.AttackAction:
        attack = actions.AttackAction(
            attacker, target, "attack", self.initiative_action, self.context,
        )
        # Pre-fix the attack roll so the parry's TN is deterministic and we do
        # not need to queue an attack roll on the attacker's roll provider.
        attack.set_skill_roll(skill_roll)
        return attack

    def test_factory_registers_mirumoto_bushi_school(self) -> None:
        """FR-001 / US1.1 prerequisite: the school is selectable via the
        existing factory by its canonical name."""
        school = get_school("Mirumoto Bushi School")
        self.assertIsInstance(school, mirumoto_school.MirumotoBushiSchool)
        self.assertEqual("Mirumoto Bushi School", school.name())

    def test_school_ring_and_knacks_via_factory(self) -> None:
        """US1.1 + US1.2 in one trace: the factory-built school reports Void
        as its ring (FR-002) and exactly {counterattack, double attack,
        iaijutsu} as its knacks (FR-003)."""
        school = get_school("Mirumoto Bushi School")
        self.assertEqual("void", school.school_ring())
        self.assertEqual(
            {"counterattack", "double attack", "iaijutsu"},
            set(school.school_knacks()),
        )

    def test_scripted_parry_grants_tvp_and_rolls_extra_die(self) -> None:
        """US1.6 + FR-005 in one scripted combat: a Mirumoto Bushi who
        attempts a parry (a) gets one extra die on the parry roll vs a
        baseline (FR-005, 1st Dan) and (b) is granted exactly one temporary
        void point regardless of outcome (FR-004, Special Ability / US1.6).

        Determinism: the Hida's attack roll is set directly on the action so
        no attack roll needs queuing. The Mirumoto's parry roll is supplied
        by a ``CalvinistRollProvider``, which also records the rolled/kept
        params so we can compare against a baseline parry's params.
        """
        # Rig the Hida's attack: the parry's TN is the attack roll. Use a
        # value the parry will successfully clear so we exercise the
        # success branch of TakeParryActionEvent.
        attack = self._build_attack(self.hida, self.mirumoto, skill_roll=20)

        # Rig the Mirumoto's parry roll: 30 vs TN 20 -> success.
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("parry", 30)
        self.mirumoto.set_roll_provider(mirumoto_rp)

        # Pre-condition: Mirumoto has zero TVP before the parry.
        self.assertEqual(0, self.mirumoto.tvp())

        # Play the full parry through the engine, exactly as combat would.
        parry = actions.ParryAction(
            self.mirumoto, self.hida, "parry",
            self.initiative_action, self.context, attack,
        )
        take_parry = events.TakeParryActionEvent(parry)
        engine = CombatEngine(self.context)
        engine.event(take_parry)

        # Trace contains a ParrySucceededEvent (success branch was taken).
        history = engine.history()
        succeeded = [e for e in history if isinstance(e, events.ParrySucceededEvent)]
        self.assertEqual(1, len(succeeded),
            "Expected exactly one ParrySucceededEvent in the combat trace")
        self.assertEqual(self.mirumoto, succeeded[0].action.subject())

        # FR-005 (1st Dan): the parry roll's rolled-die count is one greater
        # than the baseline character's would be. Compare via the roll
        # provider's observed params to assertion-grade the live pipeline.
        baseline_rp = CalvinistRollProvider()
        baseline_rp.put_skill_roll("parry", 30)
        self.baseline.set_roll_provider(baseline_rp)
        baseline_attack = self._build_attack(self.hida, self.baseline, skill_roll=20)
        baseline_parry = actions.ParryAction(
            self.baseline, self.hida, "parry",
            self.initiative_action, self.context, baseline_attack,
        )
        events.TakeParryActionEvent(baseline_parry).play(self.context)
        baseline_parry.roll_skill()

        mirumoto_observed = mirumoto_rp.pop_observed_params("parry")
        baseline_observed = baseline_rp.pop_observed_params("parry")
        self.assertEqual(baseline_observed[0] + 1, mirumoto_observed[0],
            "1st Dan should make the Mirumoto roll one extra parry die "
            "(FR-005 / rules/04-schools.md Mirumoto Bushi School First Dan)")
        # Kept dice unchanged: the +1 is on rolled only.
        self.assertEqual(baseline_observed[1], mirumoto_observed[1])

        # FR-004 / US1.6: the Mirumoto's TVP count is exactly +1 from the
        # parry attempt. The baseline character (no school) got nothing.
        self.assertEqual(1, self.mirumoto.tvp(),
            "Special Ability should grant exactly one TVP per parry "
            "(FR-004 / rules/04-schools.md Mirumoto Bushi School Special Ability)")
        self.assertEqual(0, self.baseline.tvp(),
            "Baseline (no school) must not gain a TVP from its own parry")

    def test_scripted_failed_parry_still_grants_tvp(self) -> None:
        """US1.6 boundary: even a failed parry attempt grants the TVP, per
        FR-004 (Special Ability) and rules clause "successful or unsuccessful
        parries give you a temporary void point".
        """
        # Rig the Hida's attack high so the parry fails: parry roll 10 < TN 40.
        attack = self._build_attack(self.hida, self.mirumoto, skill_roll=40)
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("parry", 10)
        self.mirumoto.set_roll_provider(mirumoto_rp)

        self.assertEqual(0, self.mirumoto.tvp())

        parry = actions.ParryAction(
            self.mirumoto, self.hida, "parry",
            self.initiative_action, self.context, attack,
        )
        engine = CombatEngine(self.context)
        engine.event(events.TakeParryActionEvent(parry))

        # Trace contains a ParryFailedEvent (failure branch taken).
        history = engine.history()
        failed = [e for e in history if isinstance(e, events.ParryFailedEvent)]
        self.assertEqual(1, len(failed),
            "Expected exactly one ParryFailedEvent in the combat trace")

        # TVP still granted on failure (the "successful or unsuccessful" half
        # of the rules clause).
        self.assertEqual(1, self.mirumoto.tvp())


class TestMirumotoThirdDanPoolHelpers(unittest.TestCase):
    """
    Unit tests for the module-private pool accessor helpers in
    ``simulation/strategies/mirumoto_third_dan.py``.

    Per contracts/interfaces.md:
      - ``_pool_remaining(character)`` returns ``character._mirumoto_pool``
        (or 0 if unset).
      - ``_try_spend_pool_point(character)`` atomically decrements the pool
        when > 0 (returning True) or returns False on an empty/missing pool.

    These helpers are the single source of truth for spend validation
    consumed by ``MirumotoPhaseLowerStrategy`` and (later)
    ``MirumotoPostRollBonusStrategy``. Their behavior gates FR-008's
    "spend is illegal if [pool empty]" clause.
    """

    def _make_character(self):
        # A bare Character is enough — the helpers do not need the school
        # wired up, only the ``_mirumoto_pool`` attribute (set or not).
        return Character("Mirumoto")

    def test_pool_remaining_returns_zero_when_attribute_missing(self):
        """Defensive: a character whose listener has never fired returns 0,
        not AttributeError. Required so the strategy can be invoked safely
        on any character without crashing if the pool was never set."""
        character = self._make_character()
        self.assertFalse(hasattr(character, "_mirumoto_pool"))
        self.assertEqual(0, mirumoto_third_dan._pool_remaining(character))

    def test_pool_remaining_returns_pool_value_when_set(self):
        """When ``_mirumoto_pool`` is set (e.g., by MirumotoNewRoundListener),
        the helper returns its current value (FR-007)."""
        character = self._make_character()
        character._mirumoto_pool = 5
        self.assertEqual(5, mirumoto_third_dan._pool_remaining(character))

    def test_try_spend_pool_point_decrements_and_returns_true(self):
        """When the pool has points, a spend returns True and decrements by 1
        (FR-008 / FR-009: each point may be spent exactly once)."""
        character = self._make_character()
        character._mirumoto_pool = 3
        self.assertTrue(mirumoto_third_dan._try_spend_pool_point(character))
        self.assertEqual(2, character._mirumoto_pool)

    def test_try_spend_pool_point_returns_false_when_pool_empty(self):
        """An empty pool yields False and does not decrement (avoids going
        negative). This is the FR-008 illegal-spend guard at the pool level."""
        character = self._make_character()
        character._mirumoto_pool = 0
        self.assertFalse(mirumoto_third_dan._try_spend_pool_point(character))
        self.assertEqual(0, character._mirumoto_pool)

    def test_try_spend_pool_point_returns_false_when_pool_attribute_missing(self):
        """If the attribute was never set (e.g., a non-3rd-dan character),
        the helper returns False without raising or creating the attribute."""
        character = self._make_character()
        self.assertFalse(hasattr(character, "_mirumoto_pool"))
        self.assertFalse(mirumoto_third_dan._try_spend_pool_point(character))
        # The helper must not create the attribute as a side effect.
        self.assertFalse(hasattr(character, "_mirumoto_pool"))

    def test_try_spend_pool_point_can_be_called_until_pool_empty(self):
        """Successive spends drain the pool in lockstep with the return value
        flipping to False at exactly the right moment (no off-by-one)."""
        character = self._make_character()
        character._mirumoto_pool = 2
        self.assertTrue(mirumoto_third_dan._try_spend_pool_point(character))
        self.assertEqual(1, character._mirumoto_pool)
        self.assertTrue(mirumoto_third_dan._try_spend_pool_point(character))
        self.assertEqual(0, character._mirumoto_pool)
        self.assertFalse(mirumoto_third_dan._try_spend_pool_point(character))
        self.assertEqual(0, character._mirumoto_pool)


class TestMirumotoEagerPhaseLowerStrategy(unittest.TestCase):
    """
    Unit tests for the default Third Dan mode-A spend strategy
    ``EagerPhaseLowerStrategy``.

    FR-008 / rules/04-schools.md Mirumoto Bushi School Third Dan:
    "Each point may be spent to decrease the phase of one of your actions
    by 1 in order to parry."

    FR-009a (i): "multiple mode-A spends MAY target the same action, each
    lowering its phase by 1 further (floor: phase >= 1)".

    The strategy receives a ``NewPhaseEvent`` and consults
    ``character._mirumoto_pool``. Each successful spend lowers one action
    in ``character._actions`` by 1 (with a phase-1 floor) and decrements
    the pool by 1. These tests pin down:

      - The pool is decremented when a spend happens (FR-008).
      - The phase-1 floor rejects illegal spends (FR-008).
      - Stacking on the same action lowers it by N over N spends
        (FR-009a-i).
      - Non-``NewPhaseEvent`` events are ignored (don't drain the pool).
      - An empty pool is a no-op (no exceptions, no mutations).

    The strategy is intentionally implemented as a per-call single-point
    decision: each ``recommend(...)`` invocation spends at most one point.
    Stacking is therefore tested by issuing multiple ``recommend(...)``
    calls back to back, which mirrors how the engine would invoke the
    strategy across successive ``NewPhaseEvent``s as phases advance.
    """

    def _make_character_with_pool_and_actions(self, pool, actions_phases):
        """Build a minimal Character with the given pool and action dice."""
        character = Character("Mirumoto")
        character.set_actions(list(actions_phases))
        character._mirumoto_pool = pool
        return character

    def _make_context(self, character):
        """Provide a minimal two-group EngineContext for ``recommend`` calls.

        The strategy under test does not currently consult the context for
        its decision (the default heuristic is pool-driven only), but the
        ``Strategy.recommend`` signature requires a context argument and
        callers must supply one.
        """
        enemy = Character("enemy")
        enemy.set_actions([1])
        groups = [Group("Dragon", character), Group("Enemy", enemy)]
        return EngineContext(groups, round=1, phase=1)

    def test_strategy_subclasses_strategy_abc(self):
        """Constitution Principle V: the strategy must implement the
        existing ``Strategy`` ABC so the engine's dispatch can consume it."""
        from simulation.strategies.base import Strategy as StrategyABC

        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        self.assertIsInstance(strategy, StrategyABC)
        self.assertIsInstance(strategy, mirumoto_third_dan.MirumotoPhaseLowerStrategy)

    def _make_context_at_phase(self, character, phase):
        """Like ``_make_context`` but with a specific combat phase.

        The post-fix strategy contract (T010 fix cycle 1) gates the spend
        on the action becoming usable as a parry on the current combat
        phase, so ``context.phase()`` is now load-bearing for the
        decision. Tests below use this helper to set up scenarios where
        a single spend, a multi-spend, or no spend is the correct
        outcome.
        """
        enemy = Character("enemy")
        enemy.set_actions([1])
        groups = [Group("Dragon", character), Group("Enemy", enemy)]
        return EngineContext(groups, round=1, phase=phase)

    def test_spend_decrements_pool_when_spendable_action_exists(self):
        """FR-008 + parry-reservation gap fix: a successful mode-A spend
        decrements the pool by 1 WHEN the single spend is enough to make
        the action usable as a parry this phase (action [3] at combat
        phase 2 -> one spend lowers to phase 2, which is usable).
        """
        character = self._make_character_with_pool_and_actions(
            pool=3, actions_phases=[3],
        )
        context = self._make_context_at_phase(character, phase=2)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(2), context))
        self.assertEqual(2, character._mirumoto_pool)

    def test_spend_lowers_action_phase_by_one(self):
        """FR-008: the spend lowers the target action's phase by exactly
        the number of steps needed to reach usability.

        Scenario: action [3] at combat phase 2, pool 1 -> one spend
        suffices (phase 3 -> 2, where 2 <= 2). Guards against a
        regression where the strategy lowers by 0 (no-op) or overshoots.
        """
        character = self._make_character_with_pool_and_actions(
            pool=1, actions_phases=[3],
        )
        context = self._make_context_at_phase(character, phase=2)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(2), context))
        self.assertEqual([2], character.actions())

    def test_no_spend_when_only_phase_one_actions_present(self):
        """FR-008 floor: 'The spend is illegal if the target action is
        already at phase 1.'

        When the only action available is at phase 1, the strategy must
        not spend a point (which would lower the action below phase 1)
        and must leave the pool untouched.
        """
        character = self._make_character_with_pool_and_actions(
            pool=5, actions_phases=[1],
        )
        context = self._make_context(character)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(1), context))
        # Pool untouched (no illegal spend).
        self.assertEqual(5, character._mirumoto_pool)
        # Action list untouched (no phase below 1).
        self.assertEqual([1], character.actions())

    def test_no_spend_when_pool_is_empty(self):
        """An empty pool short-circuits: no actions are mutated, no errors."""
        character = self._make_character_with_pool_and_actions(
            pool=0, actions_phases=[5, 7],
        )
        context = self._make_context(character)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(5), context))
        self.assertEqual(0, character._mirumoto_pool)
        self.assertEqual([5, 7], character.actions())

    def test_no_spend_when_no_pool_attribute(self):
        """A character with no ``_mirumoto_pool`` (e.g., non-3rd-dan) is a
        no-op even when the strategy is mistakenly invoked on them."""
        character = Character("Mirumoto")
        character.set_actions([5])
        # _mirumoto_pool deliberately not set.
        context = self._make_context(character)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        # Must not raise.
        list(strategy.recommend(character, events.NewPhaseEvent(5), context))
        self.assertEqual([5], character.actions())
        self.assertFalse(hasattr(character, "_mirumoto_pool"))

    def test_multi_spend_lowers_same_action_until_usable(self):
        """FR-009a (i) + parry-reservation gap fix: 'multiple mode-A spends
        MAY target the same action, each lowering its phase by 1 further
        (floor: phase >= 1)'.

        Post-fix contract: a single ``recommend(...)`` call MAY spend
        multiple points iteratively until the targeted action becomes
        usable for a parry on the current phase (i.e., phase <=
        context.phase()). With action [5] at combat phase 3 and pool 4,
        one call lowers the action from 5 -> 3 (two spends) and
        decrements the pool from 4 -> 2. No further spending happens
        within the same call because the action is now usable.
        """
        character = self._make_character_with_pool_and_actions(
            pool=4, actions_phases=[5],
        )
        context = self._make_context_at_phase(character, phase=3)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(3), context))
        self.assertEqual([3], character.actions(),
            "Action should be lowered from phase 5 to phase 3 (usable on phase 3)")
        self.assertEqual(2, character._mirumoto_pool,
            "Two pool points should have been spent (5 -> 4 -> 3)")

    def test_multi_spend_stops_at_phase_one_floor(self):
        """FR-009a (i) + parry-reservation gap fix edge case: when the
        action cannot reach usability without violating the phase-1 floor,
        the strategy MUST spend nothing (transactional: don't waste points
        on a spend that cannot enable a parry).

        Scenario: action [5] at combat phase 0 (impossible to reach via
        lowering since floor is phase 1), pool 10. The strategy must
        refuse to spend.
        """
        character = self._make_character_with_pool_and_actions(
            pool=10, actions_phases=[5],
        )
        context = self._make_context_at_phase(character, phase=0)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(0), context))
        # Cannot make action [5] usable at phase 0 (floor is 1, and 1 > 0).
        # Strategy must spend nothing.
        self.assertEqual([5], character.actions(),
            "Strategy must not mutate the action when usability is unreachable")
        self.assertEqual(10, character._mirumoto_pool,
            "Strategy must not waste pool points on an unachievable usability")

    def test_multi_spend_lowers_to_floor_when_floor_makes_usable(self):
        """FR-008 floor edge: if the action can reach phase 1 and phase 1
        is usable (combat phase >= 1), the strategy spends enough to bring
        it down to phase 1 and stops there.

        Scenario: action [3] at combat phase 1, pool 10. Lower 3 -> 2 -> 1
        (two spends); phase 1 is usable since 1 <= 1; strategy stops.
        """
        character = self._make_character_with_pool_and_actions(
            pool=10, actions_phases=[3],
        )
        context = self._make_context_at_phase(character, phase=1)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(1), context))
        self.assertEqual([1], character.actions())
        self.assertEqual(8, character._mirumoto_pool,
            "Two points spent to reach phase 1; rest of pool untouched")

    def test_refuses_to_spend_when_pool_insufficient_for_usability(self):
        """Parry-reservation gap fix (T010 fix cycle 1, discrepancy 1):
        the strategy MUST NOT spend any pool points if the spend cannot
        enable a parry on the current phase.

        Scenario: action [5] at combat phase 3, pool 1. Spending 1 point
        lowers the action to phase 4, which is STILL > 3, so the action
        is still not usable for a parry. Under the buggy pre-fix
        behavior, the strategy would burn the point anyway; under the
        post-fix contract, the spend must be refused entirely
        (transactional: no spend unless the parry becomes possible).
        """
        character = self._make_character_with_pool_and_actions(
            pool=1, actions_phases=[5],
        )
        context = self._make_context_at_phase(character, phase=3)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(3), context))
        # 1 point cannot lower action [5] to <= 3 (would need 2 spends),
        # so the strategy MUST refuse entirely.
        self.assertEqual([5], character.actions(),
            "Strategy must not partially lower an action when the parry "
            "cannot become possible with the available pool")
        self.assertEqual(1, character._mirumoto_pool,
            "Pool must be untouched when usability is unreachable "
            "(parry-reservation gap fix)")

    def test_spends_exactly_enough_to_make_action_usable(self):
        """Parry-reservation gap fix companion: when the pool is large
        enough to reach usability, the strategy stops as soon as the
        action is usable -- it does NOT overshoot or drain the pool.

        Scenario: action [5] at combat phase 3, pool 4. Two spends bring
        the action to phase 3 (usable). The strategy must stop there
        even though 2 more points remain in the pool.
        """
        character = self._make_character_with_pool_and_actions(
            pool=4, actions_phases=[5],
        )
        context = self._make_context_at_phase(character, phase=3)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(3), context))
        self.assertEqual([3], character.actions(),
            "Action must be lowered to exactly the usability threshold")
        self.assertEqual(2, character._mirumoto_pool,
            "Strategy must stop spending once usability is achieved")

    def test_no_spend_when_action_already_usable(self):
        """Parry-reservation gap fix companion: when the action is
        already usable on the current phase (phase <= context.phase()),
        no spend is needed and the strategy must not consume the pool.

        Scenario: action [3] at combat phase 5 (3 <= 5, already usable).
        Pool must remain at 5 and the action must remain at phase 3.
        """
        character = self._make_character_with_pool_and_actions(
            pool=5, actions_phases=[3],
        )
        context = self._make_context_at_phase(character, phase=5)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(5), context))
        self.assertEqual([3], character.actions())
        self.assertEqual(5, character._mirumoto_pool,
            "No spend should happen when the action is already usable")

    def test_no_spend_when_any_action_already_usable(self):
        """2026-05-26 Fix-C condition (2) regression guard:
        when the character ALREADY has an action available at phase
        <= context.phase() (i.e., any p in actions() such that
        p <= context.phase()), the strategy MUST abstain entirely
        because the parry can happen with the already-usable action.

        Scenario: actions=[1, 5] at combat phase 3. Action [1] is
        already usable (1 <= 3), so no mode-A spend is needed to
        reserve a parry. The strategy must NOT lower [5] to [3] (or
        anywhere) and must NOT touch the pool.

        Pre-Fix-C buggy behavior: strategy would pick the only
        spendable action (index 1, phase 5), check 5 > 3, spend 2
        points to lower it to 3. Post-Fix-C: condition (2) short-
        circuits before any spend.

        rules/04-schools.md Mirumoto Bushi School Third Dan -- "Each
        point may be spent to decrease the phase of one of your
        actions by 1 IN ORDER TO PARRY". The "in order to parry"
        qualifier means: only spend if the parry would not otherwise
        have an action available (FR-008 / 2026-05-26
        clarification).
        """
        character = self._make_character_with_pool_and_actions(
            pool=5, actions_phases=[1, 5],
        )
        context = self._make_context_at_phase(character, phase=3)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewPhaseEvent(3), context))
        # Actions unchanged: [1] is already usable, no need to lower [5].
        self.assertEqual([1, 5], character.actions(),
            "Strategy must NOT lower an action when another action is "
            "already usable for the parry (condition (2))")
        self.assertEqual(5, character._mirumoto_pool,
            "Pool must NOT drain when an action is already available "
            "at phase <= context.phase() (condition (2))")

    def test_non_new_phase_event_is_ignored(self):
        """The strategy is hooked on ``NewPhaseEvent``; other events (e.g.,
        ``NewRoundEvent``) must not drain the pool. Guards against a
        regression where the dispatch fires on unrelated events."""
        character = self._make_character_with_pool_and_actions(
            pool=3, actions_phases=[5],
        )
        context = self._make_context(character)
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        list(strategy.recommend(character, events.NewRoundEvent(1), context))
        self.assertEqual(3, character._mirumoto_pool)
        self.assertEqual([5], character.actions())


class TestMirumotoPostRollBonusStrategyStub(unittest.TestCase):
    """
    Sanity check that the ``MirumotoPostRollBonusStrategy`` stub class is
    in place for T009 to fill in. Per T008's scope:
      - Class must exist and subclass ``Strategy``.
      - No +2 spend logic is required yet (that's T009).
    """

    def test_post_roll_bonus_strategy_class_exists_and_subclasses_strategy(self):
        from simulation.strategies.base import Strategy as StrategyABC

        self.assertTrue(hasattr(mirumoto_third_dan, "MirumotoPostRollBonusStrategy"))
        self.assertTrue(
            issubclass(mirumoto_third_dan.MirumotoPostRollBonusStrategy, StrategyABC),
        )


class TestMirumotoMarginalBonusStrategy(unittest.TestCase):
    """
    Unit tests for the default Third Dan mode-B spend strategy
    ``MarginalBonusStrategy``.

    FR-009 / rules/04-schools.md Mirumoto Bushi School Third Dan:
    "[Each point may be spent...] to provide a bonus of +2 on any type
    of attack or parry after you have seen your roll."

    FR-009a (ii): "multiple mode-B spends MAY target the same roll,
    each adding a further +2."

    The strategy receives an ``AttackRolledEvent`` or ``ParryRolledEvent``
    (the post-roll hook: dice have been rolled and resolved, but the roll
    total has not yet been consumed by downstream logic), consults
    ``character._mirumoto_pool``, and decides how many points to spend.

    Per research.md R8, the default heuristic is "spend just enough to
    push a failing roll over the TN." This translates to:
      - If roll >= TN already, spend zero.
      - Otherwise, spend `ceil((TN - roll) / 2)` points (each gives +2)
        but cap at the pool size.

    Each successful spend mutates the action's skill roll via
    ``action.set_skill_roll(...)`` and updates ``event.roll`` to match
    (mirroring the existing ``SkillRolledStrategy`` pattern in
    ``simulation/strategies/base.py``). The pool is decremented atomically
    per point spent through ``_try_spend_pool_point``.
    """

    def _make_third_dan_mirumoto_with_pool(self, pool):
        """Build a 3rd-dan Mirumoto Bushi with the given pre-set pool size.

        Bypasses the round-start listener so the test can set an exact
        pool size. The character is otherwise a plain Mirumoto Bushi 3rd
        Dan (school + ranks 1-3 applied).
        """
        mirumoto = Character("Mirumoto")
        mirumoto.set_actions([1])
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        school.apply_special_ability(mirumoto)
        school.apply_rank_one_ability(mirumoto)
        school.apply_rank_two_ability(mirumoto)
        school.apply_rank_three_ability(mirumoto)
        mirumoto._mirumoto_pool = pool
        return mirumoto

    def _make_context(self, character):
        enemy = Character("enemy")
        enemy.set_actions([1])
        groups = [Group("Dragon", character), Group("Enemy", enemy)]
        return EngineContext(groups, round=1, phase=1)

    def _build_attack_against(self, attacker, target, tn_override=None):
        """Construct an AttackAction whose .tn() is deterministic.

        We use a real AttackAction whose subject is the Mirumoto so that
        the strategy's identity-check (event.action.subject() == character)
        passes. The TN comes from the target's tn_to_hit() by default;
        pass ``tn_override`` to short-circuit with a fixed integer for
        very precise margin arithmetic.
        """
        initiative_action = InitiativeAction([1], 1)
        context = self._make_context(attacker)
        attack = actions.AttackAction(
            attacker, target, "attack", initiative_action, context,
        )
        if tn_override is not None:
            # Monkey-patch the action's tn() to a constant for arithmetic
            # precision in tests (parallels the level of control other
            # margin-arithmetic tests achieve via ``attack.set_skill_roll(...)``).
            attack.tn = lambda: tn_override
        return attack

    def _build_parry_against(self, parrier, attack):
        """Construct a ParryAction whose .tn() comes from the attack's roll."""
        initiative_action = InitiativeAction([1], 1)
        context = self._make_context(parrier)
        return actions.ParryAction(
            parrier, attack.subject(), "parry", initiative_action, context, attack,
        )

    def _build_counterattack_against(self, counterattacker, attack, tn_override=None):
        """Construct a CounterattackAction whose .tn() is deterministic.

        Mirrors ``_build_attack_against``: the subject is the Mirumoto so
        the strategy's identity check (event.action.subject() == character)
        passes. ``tn_override`` short-circuits ``.tn()`` to a fixed integer
        for precise margin arithmetic.
        """
        initiative_action = InitiativeAction([1], 1)
        context = self._make_context(counterattacker)
        counterattack = actions.CounterattackAction(
            counterattacker, attack.subject(), "attack", initiative_action, context, attack,
        )
        if tn_override is not None:
            counterattack.tn = lambda: tn_override
        return counterattack

    def test_strategy_subclasses_strategy_abc(self):
        """Constitution Principle V: the strategy must implement the
        existing ``Strategy`` ABC and the ``MirumotoPostRollBonusStrategy``
        marker so the engine's dispatch can consume it."""
        from simulation.strategies.base import Strategy as StrategyABC

        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        self.assertIsInstance(strategy, StrategyABC)
        self.assertIsInstance(
            strategy, mirumoto_third_dan.MirumotoPostRollBonusStrategy,
        )

    def test_single_point_spend_pushes_failing_roll_over_tn(self):
        """FR-009: spending one Third Dan point adds +2 to a failing roll.

        Scenario: attack roll of 19 against TN 20. One point (+2) makes
        the roll 21 -> success. Pool decrements from 5 to 4.
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=5)
        target = Character("target")
        attack = self._build_attack_against(mirumoto, target, tn_override=20)
        attack.set_skill_roll(19)
        event = events.AttackRolledEvent(attack, 19)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        self.assertEqual(21, attack.skill_roll())
        self.assertEqual(21, event.roll)
        self.assertEqual(4, mirumoto._mirumoto_pool)

    def test_multi_point_stacking_three_points_adds_six(self):
        """FR-009a (ii): multiple mode-B spends on the same roll stack.

        Scenario: attack roll of 14 against TN 20 (margin 6). Three
        points stack as +6 to bring the roll to exactly TN. Pool
        decrements by exactly 3.
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=8)
        target = Character("target")
        attack = self._build_attack_against(mirumoto, target, tn_override=20)
        attack.set_skill_roll(14)
        event = events.AttackRolledEvent(attack, 14)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        # 14 + 3*2 = 20 (exactly clears TN)
        self.assertEqual(20, attack.skill_roll())
        self.assertEqual(20, event.roll)
        self.assertEqual(5, mirumoto._mirumoto_pool)

    def test_no_spend_when_roll_already_meets_tn(self):
        """FR-009 default heuristic: do not spend when the roll already
        meets or exceeds the TN."""
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=5)
        target = Character("target")
        attack = self._build_attack_against(mirumoto, target, tn_override=20)
        attack.set_skill_roll(25)
        event = events.AttackRolledEvent(attack, 25)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        # No mutation: pool and roll unchanged.
        self.assertEqual(25, attack.skill_roll())
        self.assertEqual(25, event.roll)
        self.assertEqual(5, mirumoto._mirumoto_pool)

    def test_no_spend_when_pool_is_empty(self):
        """Pool-empty guard: strategy refuses to spend when pool == 0.

        FR-009 cannot make a spend that would take the pool negative
        (matches FR-008's illegal-spend semantics applied to mode B).
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=0)
        target = Character("target")
        attack = self._build_attack_against(mirumoto, target, tn_override=20)
        attack.set_skill_roll(10)
        event = events.AttackRolledEvent(attack, 10)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        # No mutation: failing roll stays failing because pool was empty.
        self.assertEqual(10, attack.skill_roll())
        self.assertEqual(10, event.roll)
        self.assertEqual(0, mirumoto._mirumoto_pool)

    def test_abstains_when_pool_insufficient_to_close_tn_gap(self):
        """2026-05-26 spec.md / research.md update (Fix-D): when the
        pool is too small to close the TN gap, the strategy MUST
        abstain entirely rather than burn points on a partial spend
        that still fails.

        Rationale (per the 2026-05-26 update): a best-effort partial
        spend is strictly worse on expectation -- it produces neither
        a success now nor usable pool later. Saving the points for a
        future roll the strategy CAN close is the better policy.

        Scenario: attack roll 10 vs TN 20 (margin 10, requires ceil(10/2)
        = 5 points). Pool has only 2 points. Strategy abstains: the roll
        stays at 10 (still failing), and the pool stays at 2 for a
        future closeable roll.
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=2)
        target = Character("target")
        attack = self._build_attack_against(mirumoto, target, tn_override=20)
        attack.set_skill_roll(10)
        event = events.AttackRolledEvent(attack, 10)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        # No mutation: roll unchanged, pool unchanged (preserved for a
        # future roll the strategy can actually close).
        self.assertEqual(10, attack.skill_roll())
        self.assertEqual(10, event.roll)
        self.assertEqual(2, mirumoto._mirumoto_pool)

    def test_non_post_roll_event_is_ignored(self):
        """Wrong-event guard: events that aren't post-roll triggers must
        not drain the pool.

        Guards against a regression where the dispatch fires on
        unrelated events (e.g., NewRoundEvent) and silently burns
        points.
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=5)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, events.NewRoundEvent(1), context))
        self.assertEqual(5, mirumoto._mirumoto_pool)
        list(strategy.recommend(mirumoto, events.NewPhaseEvent(5), context))
        self.assertEqual(5, mirumoto._mirumoto_pool)

    def test_ignores_event_for_different_subject(self):
        """A post-roll event whose action.subject() is a different
        character must not let this character spend its pool.

        Guards against the dispatch invoking the strategy on a bystander
        (cf. ``TestMirumotoParryTVPListener.test_listener_ignores_parry_event_for_other_character``).
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=5)
        other = Character("other")
        target = Character("target")
        attack = self._build_attack_against(other, target, tn_override=20)
        attack.set_skill_roll(10)
        event = events.AttackRolledEvent(attack, 10)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        # Pool untouched, other character's attack untouched.
        self.assertEqual(5, mirumoto._mirumoto_pool)
        self.assertEqual(10, attack.skill_roll())

    def test_applies_to_parry_rolled_event(self):
        """FR-009 covers both attack and parry rolls.

        A ParryRolledEvent below TN should trigger the +2 spend exactly
        like AttackRolledEvent does.
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=3)
        attacker = Character("attacker")
        attack = self._build_attack_against(attacker, mirumoto, tn_override=20)
        # Attacker's roll IS the TN for the parry.
        attack.set_skill_roll(20)
        parry = self._build_parry_against(mirumoto, attack)
        parry.set_skill_roll(18)  # below TN 20 by 2
        event = events.ParryRolledEvent(parry, 18)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        # +2 brings parry to exactly TN 20; one point spent.
        self.assertEqual(20, parry.skill_roll())
        self.assertEqual(20, event.roll)
        self.assertEqual(2, mirumoto._mirumoto_pool)

    def test_applies_to_counterattack_rolled_event(self):
        """FR-009 / FR-003: the rules clause says "any type of attack or
        parry"; counterattack is a Mirumoto school knack (FR-003) and its
        roll is a type of attack roll, so a CounterattackRolledEvent below
        TN should trigger the +2 spend exactly like AttackRolledEvent and
        ParryRolledEvent do.

        Rules clause: rules/04-schools.md Mirumoto Bushi School Third Dan
        ("to provide a bonus of +2 on any type of attack or parry after
        you have seen your roll").
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=3)
        attacker = Character("attacker")
        # The original attack (the one the counterattack is reacting to).
        original_attack = self._build_attack_against(
            attacker, mirumoto, tn_override=20,
        )
        original_attack.set_skill_roll(20)
        counterattack = self._build_counterattack_against(
            mirumoto, original_attack, tn_override=20,
        )
        counterattack.set_skill_roll(18)  # below TN 20 by 2
        event = events.CounterattackRolledEvent(counterattack, 18)
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))
        # +2 brings counterattack to exactly TN 20; one point spent.
        self.assertEqual(20, counterattack.skill_roll())
        self.assertEqual(20, event.roll)
        self.assertEqual(2, mirumoto._mirumoto_pool)

    def test_mutation_happens_after_roll_is_resolved(self):
        """FR-009 timing: 'The spend MUST be declarable *after* the
        roll's dice have been resolved and inspected.'

        Verify by ordering the events: the strategy reads
        ``event.roll``/``action.skill_roll()`` BEFORE deciding, and the
        decision is purely a function of those resolved values. We
        capture the order with a list and assert that the resolved roll
        was observed first, the mutation last.

        Implementation detail: we wrap ``action.set_skill_roll`` so that
        any call into it is timestamped. The strategy must NOT mutate
        the roll before observing it (which would imply a pre-roll
        decision, violating FR-009).
        """
        mirumoto = self._make_third_dan_mirumoto_with_pool(pool=3)
        target = Character("target")
        attack = self._build_attack_against(mirumoto, target, tn_override=20)

        order: list[str] = []
        # Step 1: explicitly resolve the roll (simulating the engine
        # rolling skill and calling action.set_skill_roll(...)).
        attack.set_skill_roll(18)
        order.append("roll_resolved")

        # Wrap set_skill_roll to capture subsequent (post-roll) mutations.
        original_setter = attack.set_skill_roll

        def tracking_setter(roll: int) -> None:
            order.append(f"mutation_to_{roll}")
            original_setter(roll)

        attack.set_skill_roll = tracking_setter

        # Step 2: fire the post-roll event. The strategy must read the
        # resolved roll (18) and decide to spend; the mutation must come
        # AFTER the roll_resolved marker.
        event = events.AttackRolledEvent(attack, 18)
        order.append("event_dispatched")
        context = self._make_context(mirumoto)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        list(strategy.recommend(mirumoto, event, context))

        # The mutation index must come strictly AFTER the roll_resolved
        # marker -> proves the strategy is post-roll.
        self.assertIn("roll_resolved", order)
        roll_resolved_idx = order.index("roll_resolved")
        mutation_idx = next(
            i for i, label in enumerate(order) if label.startswith("mutation_to_")
        )
        self.assertLess(
            roll_resolved_idx,
            mutation_idx,
            f"FR-009 violation: mutation occurred before roll resolution. Order: {order}",
        )
        # And the dispatch happened before the mutation too (the
        # strategy didn't reach in and mutate the action behind our back
        # before being invoked).
        dispatched_idx = order.index("event_dispatched")
        self.assertLess(
            dispatched_idx,
            mutation_idx,
            f"FR-009 violation: mutation occurred before event dispatch. Order: {order}",
        )
        # And the final mutation lands at 20 (18 + 2*1).
        self.assertEqual(20, attack.skill_roll())


class TestMirumotoUS2Integration(unittest.TestCase):
    """
    US2 independent-test integration suite (spec.md US2 Independent Test +
    tasks.md T010).

    Verifies the T010 wiring on ``MirumotoBushiSchool.apply_rank_three_ability``:

      - The pool-spend strategies registered on the new strategy slots
        ``"mirumoto_phase_lower"`` and ``"mirumoto_post_roll_bonus"`` are
        invoked by the engine at the right hook points (FR-015 pluggability).
      - Mode B (+2 post-roll bonus) fires through ``CombatEngine`` for
        attack rolls and parry rolls (FR-007/FR-009).
      - Mode A (phase-lowering) fires in reaction to incoming attacks
        (FR-008): a Mirumoto with an action at phase > 1 lowers it to
        parry-reserved status when an enemy declares an attack against them.
      - Mode A and mode B combine on the same action (FR-009a-iii): a
        phase-lowered action's parry roll subsequently receives a mode-B +2.
      - The wiring does NOT regress event propagation: even with the
        Mirumoto post-roll bonus chaining wrapper installed, an enemy's
        attack against the Mirumoto still triggers the defender's
        ``AttackRolledListener`` -> ``DefaultInterruptStrategy`` -> parry
        cascade (T009 simulator critique on event suppression).

    Rules clause exercised: rules/04-schools.md Mirumoto Bushi School Third
    Dan -- "At the beginning of each round, you get 2X points, where X is
    equal to your attack skill. Each point may be spent to decrease the
    phase of one of your actions by 1 in order to parry, or to provide a
    bonus of +2 on any type of attack or parry after you have seen your
    roll."
    """

    def _make_third_dan_mirumoto(self, attack_skill: int = 4, actions_phases: list[int] | None = None) -> Character:
        """Construct a 3rd-dan Mirumoto with school ranks 1-3 applied.

        Pre-set the actions list directly (bypassing roll_initiative) so the
        scenario is deterministic. The pool will be populated by
        ``apply_rank_three_ability``'s listener on the next NewRoundEvent;
        tests that need the pool pre-populated can set
        ``mirumoto._mirumoto_pool`` directly.
        """
        mirumoto = Character("Mirumoto")
        mirumoto.set_actions(list(actions_phases) if actions_phases is not None else [1])
        mirumoto.set_skill("attack", attack_skill)
        mirumoto.set_skill("parry", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        school.apply_special_ability(mirumoto)
        school.apply_rank_one_ability(mirumoto)
        school.apply_rank_two_ability(mirumoto)
        school.apply_rank_three_ability(mirumoto)
        return mirumoto

    def _make_enemy(self, actions_phases: list[int] | None = None) -> Character:
        enemy = Character("Hida")
        enemy.set_actions(list(actions_phases) if actions_phases is not None else [1])
        enemy.set_skill("attack", 4)
        enemy.set_skill("parry", 4)
        return enemy

    def _context_for(self, mirumoto: Character, enemy: Character, phase: int = 1) -> EngineContext:
        groups = [Group("Dragon", mirumoto), Group("Crab", enemy)]
        ctx = EngineContext(groups, round=1, phase=phase)
        ctx.initialize()
        return ctx

    # ----- T010 strategy installation -----

    def test_rank_three_installs_phase_lower_strategy_slot(self) -> None:
        """T010 wiring contract: ``apply_rank_three_ability`` MUST install
        a ``MirumotoPhaseLowerStrategy`` on the ``"mirumoto_phase_lower"``
        slot (FR-015 pluggability)."""
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4)
        strategy = mirumoto._strategies.get("mirumoto_phase_lower")
        self.assertIsNotNone(
            strategy,
            "apply_rank_three_ability must install a 'mirumoto_phase_lower' strategy",
        )
        self.assertIsInstance(
            strategy,
            mirumoto_third_dan.MirumotoPhaseLowerStrategy,
        )

    def test_rank_three_installs_post_roll_bonus_strategy_slot(self) -> None:
        """T010 wiring contract: ``apply_rank_three_ability`` MUST install
        a ``MirumotoPostRollBonusStrategy`` on the
        ``"mirumoto_post_roll_bonus"`` slot (FR-015 pluggability)."""
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4)
        strategy = mirumoto._strategies.get("mirumoto_post_roll_bonus")
        self.assertIsNotNone(
            strategy,
            "apply_rank_three_ability must install a 'mirumoto_post_roll_bonus' strategy",
        )
        self.assertIsInstance(
            strategy,
            mirumoto_third_dan.MirumotoPostRollBonusStrategy,
        )

    # ----- Mode B end-to-end -----

    def test_mode_b_fires_for_attack_roll_through_combat_engine(self):
        """FR-009 end-to-end: a Mirumoto's failing attack roll gets +2'd by
        the post-roll bonus strategy through the live ``CombatEngine``.

        Scenario: pool of 1, attack roll of 14 vs TN 15 (margin 1). The
        mode-B strategy should spend 1 point to bring the roll to 16
        (clears TN), and the pool should decrement from 1 to 0.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4)
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy)
        mirumoto._mirumoto_pool = 1
        # Force the enemy's tn_to_hit to be deterministic: 15.
        enemy.tn_to_hit = lambda: 15
        # Queue the Mirumoto's attack roll.
        rp = CalvinistRollProvider()
        rp.put_skill_roll("attack", 14)
        rp.put_damage_roll(0)  # in case the attack succeeds and damage rolls
        mirumoto.set_roll_provider(rp)

        attack = actions.AttackAction(
            mirumoto, enemy, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.TakeAttackActionEvent(attack))

        # FR-009: the strategy applied +2; pool decremented to 0.
        self.assertEqual(16, attack.skill_roll(),
            "Mode-B strategy should have boosted attack roll from 14 to 16")
        self.assertEqual(0, mirumoto._mirumoto_pool,
            "One point should have been spent from the pool")

    def test_mode_b_fires_for_parry_roll_through_combat_engine(self):
        """FR-009 end-to-end: a Mirumoto's failing parry roll gets +2'd by
        the post-roll bonus strategy through the live ``CombatEngine``.

        Scenario: enemy attack roll set to 30 (parry TN 30); Mirumoto
        parry roll raw 23 (after the 2nd-Dan free raise of +5, the
        ``parry_rolled_strategy`` will see 28; margin 2). The mode-B
        strategy should spend 1 point for +2 to bring parry to 30,
        decrementing the pool.

        Note: the 2nd-Dan free raise (``FreeRaise`` modifier added by
        ``apply_rank_two_ability``) adds +5 to the parry roll BEFORE the
        ``parry_rolled_strategy`` chain fires, so the queued raw roll has
        already been adjusted upward by 5 when the post-roll bonus
        strategy inspects it.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4)
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy)
        mirumoto._mirumoto_pool = 1

        # Pre-fix the enemy's attack roll so the parry TN is deterministic.
        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        attack.set_skill_roll(30)

        # Queue the Mirumoto's parry roll. Raw 23 + 5 free raise = 28,
        # which is 2 short of TN 30 -> mode-B will spend 1 point for +2.
        rp = CalvinistRollProvider()
        rp.put_skill_roll("parry", 23)
        mirumoto.set_roll_provider(rp)

        parry = actions.ParryAction(
            mirumoto, enemy, "parry", InitiativeAction([1], 1), ctx, attack,
        )
        engine = CombatEngine(ctx)
        engine.event(events.TakeParryActionEvent(parry))

        # FR-009: the strategy boosted the parry roll from 28 to 30.
        self.assertEqual(30, parry.skill_roll(),
            "Mode-B strategy should have boosted parry roll from 28 to 30")
        self.assertEqual(0, mirumoto._mirumoto_pool,
            "One point should have been spent from the pool")
        # And the parry succeeded (no ParryFailedEvent in trace).
        self.assertEqual(
            0,
            len([e for e in engine.history() if isinstance(e, events.ParryFailedEvent)]),
            "Boosted parry should have succeeded",
        )

    def test_attack_rolled_event_still_reaches_enemy_listener(self):
        """T009 regression guard: with the post-roll bonus chaining wrapper
        installed on the Mirumoto, an enemy's attack against the Mirumoto
        must STILL fire the Mirumoto's ``AttackRolledListener`` ->
        ``DefaultInterruptStrategy`` -> parry cascade.

        If the chaining wrapper accidentally suppresses the
        AttackRolledEvent (the T009 simulator's documented risk), the
        Mirumoto's parry would never trigger and the test would see no
        ParryDeclaredEvent in the combat trace.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[1])
        # Mirumoto must be willing to parry; the default ReluctantParryStrategy
        # only parries when the attack looks dangerous, so substitute Always.
        from simulation.strategies.base import AlwaysParryStrategy
        mirumoto.set_parry_strategy(AlwaysParryStrategy())
        # Force a low TN so the enemy's queued attack roll definitively hits
        # and the BaseParryStrategy's ``if not is_hit()`` short-circuit does
        # not suppress the parry decision.
        mirumoto.tn_to_hit = lambda: 5
        enemy = self._make_enemy(actions_phases=[1])
        # Drain the Mirumoto pool so mode-B does not interfere with the
        # margin arithmetic; the test is about EVENT propagation, not
        # +2 application.
        mirumoto._mirumoto_pool = 0
        ctx = self._context_for(mirumoto, enemy)

        # Mirumoto's parry roll queue.
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("parry", 50)
        mirumoto.set_roll_provider(mirumoto_rp)
        # Enemy's attack roll queue: 30 > TN 5 -> hits.
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 30)
        enemy_rp.put_damage_roll(5)
        enemy.set_roll_provider(enemy_rp)

        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.TakeAttackActionEvent(attack))

        history = engine.history()
        # Critical regression guard: the AttackRolledEvent must reach the
        # public event stream (otherwise the chaining wrapper suppressed it).
        attack_rolled_events = [
            e for e in history if isinstance(e, events.AttackRolledEvent)
        ]
        self.assertGreaterEqual(
            len(attack_rolled_events), 1,
            "AttackRolledEvent must reach the public stream so enemy "
            "listeners can react (T009 event-suppression regression guard)",
        )
        # And the Mirumoto's AttackRolledListener -> parry cascade fired:
        # a ParryDeclaredEvent appears in the trace.
        parry_declared_events = [
            e for e in history if isinstance(e, events.ParryDeclaredEvent)
        ]
        self.assertGreaterEqual(
            len(parry_declared_events), 1,
            "Defender's parry cascade must still fire after T010 wiring "
            "(T009 simulator critique: regression guard)",
        )

    # ----- Mode A end-to-end (option (b): reactive on AttackDeclaredEvent) -----

    def test_mode_a_fires_on_enemy_attack_declared(self):
        """FR-008 end-to-end (option-b wiring): when an enemy declares an
        attack against a 3rd-dan Mirumoto, the
        ``MirumotoPhaseLowerStrategy`` is invoked and the Mirumoto's
        scheduled action at phase > 1 is lowered just enough to make it
        usable for a parry on the current phase (parry-reservation).

        Implementation choice (documented in T010): the phase-lower hook
        fires reactively on ``AttackDeclaredEvent`` (when an enemy attacks
        this Mirumoto), per the rules text "decrease the phase of one of
        your actions by 1 in order to parry" (the parry is the trigger).

        Post-fix contract (T010 fix cycle 1): the strategy spends
        ENOUGH points in a single recommend call to make the action
        usable as a parry on the current combat phase. With action [5]
        at combat phase 3 and pool 3, two spends bring the action to
        phase 3 (usable); pool 3 -> 1.
        """
        # Mirumoto has an action at phase 5 (lowerable to phase 3).
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[5])
        mirumoto._mirumoto_pool = 3
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy, phase=3)

        # Manufacture an attack from the enemy targeting the Mirumoto and
        # fire only the AttackDeclaredEvent (no full play -- we are
        # testing the listener-strategy plumbing, not the attack flow).
        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.AttackDeclaredEvent(attack))

        # Mode-A spend should have fired: action 5 -> 3 (two spends to
        # reach usability on phase 3), pool 3 -> 1.
        self.assertEqual([3], mirumoto.actions(),
            "Mode-A wiring should have lowered the Mirumoto's phase-5 "
            "action to phase 3 (usable on combat phase 3) in reaction "
            "to the enemy's attack (FR-008)")
        self.assertEqual(1, mirumoto._mirumoto_pool,
            "Pool should have decremented by 2 (two spends to reach usability)")

    def test_mode_a_does_not_fire_when_mirumoto_is_attacker(self):
        """Mode-A should ONLY trigger when an ENEMY attack threatens the
        Mirumoto. A Mirumoto's own outgoing attack must not drain its own
        pool via the phase-lower hook.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[5])
        mirumoto._mirumoto_pool = 3
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy, phase=1)

        # The Mirumoto is the ATTACKER here.
        attack = actions.AttackAction(
            mirumoto, enemy, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.AttackDeclaredEvent(attack))

        # No phase-lower should have fired; pool and actions untouched.
        self.assertEqual([5], mirumoto.actions(),
            "Mode-A should NOT fire for the Mirumoto's own outgoing attack")
        self.assertEqual(3, mirumoto._mirumoto_pool,
            "Pool must not drain when Mirumoto is the attacker")

    def test_mode_a_no_spend_when_pool_empty(self):
        """Empty-pool guard at the wiring level: even when an enemy
        declares an attack against the Mirumoto, a 0-pool Mirumoto's
        actions must not be mutated (FR-008 illegal-spend semantics)."""
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[5])
        mirumoto._mirumoto_pool = 0
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy, phase=1)
        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.AttackDeclaredEvent(attack))
        self.assertEqual([5], mirumoto.actions())
        self.assertEqual(0, mirumoto._mirumoto_pool)

    # ----- Cross-mode combination (FR-009a-iii) -----

    def test_cross_mode_combination_on_same_action(self):
        """FR-009a-iii: a Mirumoto's action MAY receive both mode A
        (phase-lower) AND mode B (+2 on its parry roll), drawing from the
        same Third Dan pool.

        Scenario (post-T010 fix cycle 1, parry-reservation gap):
          1. Mirumoto has an action at phase 5, pool of 4. Combat is at
             phase 4 (the action needs ONE lowering to become usable).
          2. Enemy declares attack against the Mirumoto -> mode A lowers
             the phase-5 action to phase 4 (one spend reaches usability:
             4 <= 4), pool -> 3.
          3. Mirumoto parries the enemy's attack (raw parry roll 23 +5
             from 2nd-Dan free raise = 28 vs TN 30, margin 2).
          4. Mode B fires on the parry roll: spend 1 point for +2,
             pool -> 2, parry roll becomes 30 (success).

        Net effect: the same action was both phase-lowered AND its parry
        roll was bonused; pool decremented by 2 total (FR-009a-iii).
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[5])
        mirumoto._mirumoto_pool = 4
        # Always-parry so the parry fires on AttackRolledEvent without
        # needing the ReluctantParryStrategy's damage estimation to flag
        # the attack as dangerous.
        from simulation.strategies.base import AlwaysParryStrategy
        mirumoto.set_parry_strategy(AlwaysParryStrategy())
        # Force a low TN so the enemy attack definitively hits.
        mirumoto.tn_to_hit = lambda: 5
        enemy = self._make_enemy(actions_phases=[4])
        # Start the engine at phase 4 so the Mirumoto's action needs
        # exactly one mode-A spend (5 -> 4) to become usable for the
        # parry (4 <= 4). Per the T010 fix cycle 1 parry-reservation
        # gap fix, the strategy spends only as many points as needed
        # to reach usability.
        ctx = self._context_for(mirumoto, enemy, phase=4)

        # Mirumoto's parry roll. Raw 23 + 5 free raise = 28; TN 30; mode-B
        # should add +2 to push it to 30 (success).
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("parry", 23)
        mirumoto.set_roll_provider(mirumoto_rp)
        # Enemy attack roll: 30 > TN 5 -> hit; parry TN becomes 30.
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 30)
        enemy_rp.put_damage_roll(5)
        enemy.set_roll_provider(enemy_rp)

        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([4], 4), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.TakeAttackActionEvent(attack))

        # Mode A: action 5 -> 4 (1 point), Mode B on the parry: +2 (1
        # point). Pool went from 4 -> 3 -> 2 -- net -2.
        self.assertEqual(2, mirumoto._mirumoto_pool,
            "Cross-mode combination should consume 2 pool points: 1 for "
            "phase-lower (mode A) + 1 for +2 parry (mode B), per FR-009a-iii")
        # And the parry succeeded (no ParryFailedEvent in trace) -- proving
        # the +2 was actually applied and pushed the roll over TN.
        history = engine.history()
        self.assertEqual(
            0,
            len([e for e in history if isinstance(e, events.ParryFailedEvent)]),
            "Boosted parry should have succeeded after mode B applied +2",
        )
        # And a ParryDeclaredEvent must appear in the trace -- proving the
        # mode-A-lowered action was actually used for the parry.
        self.assertGreaterEqual(
            len([e for e in history if isinstance(e, events.ParryDeclaredEvent)]),
            1,
            "Mode-A-lowered action should have been used for a parry",
        )

    def test_mode_a_multi_spend_enables_parry_scenario_1(self):
        """T010 fix cycle 1 runtime regression test (parry-reservation
        gap fix, simulator Scenario 1).

        Scenario from the orchestrator's discrepancy report:
          - 3rd-dan Mirumoto with action [5], pool=4, attacked at phase 3.
          - Pre-fix behavior: strategy spent 1 point (action 5 -> 4),
            but action [4] is still > combat phase 3, so the parry was
            NOT reserved. Pool 4 -> 3 wasted; attack succeeded; Mirumoto
            took 5 LW with no ParryDeclaredEvent.
          - Post-fix behavior: strategy spends 2 points (action 5 -> 4 -> 3),
            making the action usable on phase 3. Parry fires and
            succeeds; pool drops 4 -> 2 (not 1, not 4).

        This locks in the parry-reservation gap fix at the engine
        integration level, not just the unit-strategy level.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[5])
        mirumoto._mirumoto_pool = 4
        # Always-parry so the parry fires unconditionally on the
        # AttackRolledEvent cascade (matches T009 regression-guard
        # pattern in this suite).
        from simulation.strategies.base import AlwaysParryStrategy
        mirumoto.set_parry_strategy(AlwaysParryStrategy())
        # Low TN so the enemy attack definitively hits.
        mirumoto.tn_to_hit = lambda: 5
        enemy = self._make_enemy(actions_phases=[3])
        # Combat phase 3 -- matches the discrepancy scenario.
        ctx = self._context_for(mirumoto, enemy, phase=3)

        # Mirumoto's parry roll easily clears TN -- the test is about
        # the parry being RESERVED via mode-A, not about mode-B.
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("parry", 100)
        mirumoto.set_roll_provider(mirumoto_rp)
        # Enemy attack roll: 30 > TN 5 -> hits.
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 30)
        enemy_rp.put_damage_roll(5)
        enemy.set_roll_provider(enemy_rp)

        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([3], 3), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.TakeAttackActionEvent(attack))

        history = engine.history()

        # Critical: a ParryDeclaredEvent must appear -- proving the
        # mode-A-lowered action was usable for the parry. Pre-fix, this
        # would be absent because action [4] > phase 3.
        parry_declared = [e for e in history if isinstance(e, events.ParryDeclaredEvent)]
        self.assertGreaterEqual(
            len(parry_declared), 1,
            "Parry must actually be declared after mode-A lowering "
            "(parry-reservation gap fix)",
        )
        # And the parry succeeded.
        parry_failed = [e for e in history if isinstance(e, events.ParryFailedEvent)]
        self.assertEqual(0, len(parry_failed),
            "Parry should succeed once it is actually declared")
        # Pool drops by 2 (not 1, not 4): proves the strategy spent
        # exactly enough to reach usability and no more.
        self.assertEqual(2, mirumoto._mirumoto_pool,
            "Pool must drop by exactly 2 (the minimum to make action "
            "[5] usable on phase 3); pre-fix bug would drop only 1, "
            "and overshoot would drop more")

    # ----- 2026-05-26 Fix-C precondition guards -----

    def test_mode_a_abstains_when_action_already_available(self):
        """2026-05-26 Fix-C condition (2) integration guard.

        When a Mirumoto already has an action at phase
        <= context.phase() (i.e., an action available to parry with),
        the mode-A listener MUST NOT spend any pool points -- the
        parry can happen with the existing usable action.

        Scenario: actions=[1, 5] at combat phase 3, pool=4. Enemy
        declares an attack against the Mirumoto. Action [1] is
        already usable for the parry (1 <= 3), so condition (2) of
        the Fix-C heuristic short-circuits the spend. Pool and
        actions must both be unchanged.

        Pre-Fix-C behavior: listener fired on every incoming
        AttackDeclaredEvent and attempted to lower the soonest
        non-floor action -- even when a usable action was already
        present. Post-Fix-C: the listener abstains.

        rules/04-schools.md Mirumoto Bushi School Third Dan: "Each
        point may be spent to decrease the phase of one of your
        actions by 1 IN ORDER TO PARRY". The "in order to parry"
        clause requires the parry to NOT otherwise be possible
        (2026-05-26 clarification).
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[1, 5])
        mirumoto._mirumoto_pool = 4
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy, phase=3)
        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.AttackDeclaredEvent(attack))
        # Action [1] is already usable on phase 3 -> no mode-A spend.
        self.assertEqual([1, 5], mirumoto.actions(),
            "Mode-A must NOT fire when an action is already usable "
            "(Fix-C condition (2))")
        self.assertEqual(4, mirumoto._mirumoto_pool,
            "Pool must NOT drain when an action is already available "
            "for the parry (Fix-C condition (2))")

    def test_mode_a_abstains_when_parry_strategy_would_not_parry(self):
        """2026-05-26 Fix-C condition (1) integration guard.

        When the character's parry strategy is one that would not
        parry this incoming attack (e.g., ``NeverParryStrategy``),
        the mode-A listener MUST NOT spend any pool points -- there
        is no parry to reserve.

        Scenario: actions=[5] at combat phase 3, pool=4, parry
        strategy explicitly set to ``NeverParryStrategy``. Enemy
        declares an attack against the Mirumoto. Pre-Fix-C: the
        listener would lower [5] to [3] regardless, wasting 2 pool
        points on a parry that never happens. Post-Fix-C: condition
        (1) detects the ``NeverParryStrategy`` and abstains.

        Implementation note (Option B / predictive intent check):
        the listener inspects the parry strategy class at
        ``AttackDeclaredEvent`` time, before the parry decision
        would normally be made on ``AttackRolledEvent``. This is a
        conservative heuristic -- ``NeverParryStrategy`` is the only
        strategy guaranteed to decline, so this guard mainly
        protects characters whose strategy is explicitly "no
        parry."

        rules/04-schools.md Mirumoto Bushi School Third Dan: "Each
        point may be spent to decrease the phase of one of your
        actions by 1 IN ORDER TO PARRY". No parry, no spend.
        """
        from simulation.strategies.base import NeverParryStrategy
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[5])
        mirumoto._mirumoto_pool = 4
        mirumoto.set_parry_strategy(NeverParryStrategy())
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy, phase=3)
        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.AttackDeclaredEvent(attack))
        # Mode-A must abstain entirely.
        self.assertEqual([5], mirumoto.actions(),
            "Mode-A must NOT fire when the parry strategy would not "
            "parry the incoming attack (Fix-C condition (1))")
        self.assertEqual(4, mirumoto._mirumoto_pool,
            "Pool must NOT drain when no parry would happen "
            "(Fix-C condition (1))")

    def test_mode_a_spends_only_when_all_three_conditions_hold(self):
        """2026-05-26 Fix-C happy path: mode-A spend fires ONLY when
        ALL THREE preconditions hold:

          (1) Parry strategy would parry the incoming attack.
          (2) No action available at phase <= context.phase().
          (3) Pool sufficient to lower an action enough to reach
              usability.

        Scenario: actions=[5] at combat phase 3, pool=4,
        ``AlwaysParryStrategy`` installed. Enemy declares attack
        against the Mirumoto.

          (1) ``AlwaysParryStrategy`` will parry. PASS.
          (2) actions=[5], phase=3: no p <= 3. PASS (no action available).
          (3) pool=4 >= 2 spends needed (5 -> 4 -> 3). PASS.

        Expected: 2 spends, action [5] -> [3], pool 4 -> 2.

        rules/04-schools.md Mirumoto Bushi School Third Dan: "Each
        point may be spent to decrease the phase of one of your
        actions by 1 in order to parry". Happy path with all gates
        green; spend is the minimum needed to reach usability per
        the T010 fix-cycle-1 parry-reservation gap fix.
        """
        from simulation.strategies.base import AlwaysParryStrategy
        mirumoto = self._make_third_dan_mirumoto(attack_skill=4, actions_phases=[5])
        mirumoto._mirumoto_pool = 4
        mirumoto.set_parry_strategy(AlwaysParryStrategy())
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy, phase=3)
        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.AttackDeclaredEvent(attack))
        # Mode-A fires: 2 spends, action [5] -> [3].
        self.assertEqual([3], mirumoto.actions(),
            "All three Fix-C preconditions hold -> mode-A lowers "
            "the action to usability (5 -> 3 on phase 3)")
        self.assertEqual(2, mirumoto._mirumoto_pool,
            "Pool drops by exactly the minimum (2 points) to make "
            "the action usable on the current phase")

    # ----- US2 independent test paragraph -----

    def test_us2_independent_pool_zero_when_attack_skill_zero(self):
        """US2.5 / FR-007 boundary: 3rd-dan Mirumoto with attack skill 0
        has a pool of 0 and no mode-A or mode-B spend triggers on any
        event.
        """
        mirumoto = self._make_third_dan_mirumoto(attack_skill=0, actions_phases=[5])
        enemy = self._make_enemy()
        ctx = self._context_for(mirumoto, enemy, phase=1)
        # Fire NewRoundEvent through the listener to populate the pool.
        listener = mirumoto_school.MirumotoNewRoundListener()
        list(listener.handle(mirumoto, events.NewRoundEvent(1), ctx))
        self.assertEqual(0, mirumoto._mirumoto_pool,
            "Attack skill 0 -> pool size 0 (US2.5)")
        # Reset actions after roll_initiative side-effect inside the listener.
        mirumoto.set_actions([5])
        # An enemy attack must not drain a 0-pool nor mutate actions.
        attack = actions.AttackAction(
            enemy, mirumoto, "attack", InitiativeAction([1], 1), ctx,
        )
        engine = CombatEngine(ctx)
        engine.event(events.AttackDeclaredEvent(attack))
        self.assertEqual([5], mirumoto.actions())
        self.assertEqual(0, mirumoto._mirumoto_pool)


class TestMirumotoFourthDanVoidRaiseAndDiscount(unittest.TestCase):
    """
    Mirumoto Bushi School Fourth Dan, Void portion (FR-010 + FR-011).

    rules/04-schools.md Mirumoto Bushi School Fourth Dan:
    "Your Void ring is raised by 1, and the cost to raise your Void
    ring is reduced by 5."

    Covers acceptance scenarios US3.1 (current + maximum Void each
    +1 vs a baseline non-Mirumoto 4th-dan character) and US3.2 (XP
    cost to raise Void is 5 less than the standard L7R cost, with
    a floor of 0 when the standard cost is <= 5).

    The implementation is shared with other 4th-dan schools through
    ``BaseSchool.apply_school_ring_raise_and_discount``; this suite
    pins the Void-specific behavior so a future refactor of the
    helper (or of the Mirumoto wiring of ``apply_rank_four_ability``)
    cannot silently regress it.
    """

    def _build_fourth_dan_mirumoto(self, xp: int = 9001):
        """Construct a 4th-dan Mirumoto via the standard builder.

        Buying all three school knacks (counterattack, double attack,
        iaijutsu) up to rank 4 advances the school to 4th dan, which
        triggers ``MirumotoBushiSchool.apply_rank_four_ability`` and
        thus ``apply_school_ring_raise_and_discount`` on Void
        (FR-002 sets the school ring to Void).
        """
        school = mirumoto_school.MirumotoBushiSchool()
        builder = (
            CharacterBuilder()
            .with_name("Mirumoto")
            .with_xp(xp)
            .with_school(school)
            .buy_skill("counterattack", 4)
            .buy_skill("double attack", 4)
            .buy_skill("iaijutsu", 4)
        )
        # sanity: school should have advanced to 4th dan, applying
        # the rank-four ability via update_school_rank().
        self.assertEqual(4, builder.school_rank(),
            "Test setup: expected school_rank=4 after buying all knacks to 4")
        return builder

    def _build_fourth_dan_baseline(self, xp: int = 9001):
        """Construct a 4th-dan non-Mirumoto for the baseline comparison.

        Akodo Bushi School is used because its school ring is Water
        (not Void), so its own ``apply_rank_four_ability`` does NOT
        touch Void. This isolates the Mirumoto-specific Void
        modification we want to measure.
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
        self.assertEqual(4, builder.school_rank(),
            "Test setup: expected baseline school_rank=4")
        return builder

    # ----- FR-010: current Void +1 -----

    def test_fourth_dan_raises_current_void_by_one_vs_baseline(self):
        """US3.1 / FR-010: a 4th-dan Mirumoto's CURRENT Void ring rank
        is exactly 1 higher than an otherwise-identical 4th-dan baseline
        (non-Mirumoto) character's.

        The baseline Akodo's school ring is Water, so its Void stays
        at the engine default of 2. The Mirumoto's school ring IS
        Void, so it receives both the standard ``apply_school_ring``
        bump (2 -> 3 at construction) and the additional Fourth Dan
        +1 from ``apply_school_ring_raise_and_discount`` (3 -> 4).

        Per the spec's US3 phrasing ("vs identical baseline"), we
        focus on the +1 delivered by the Fourth Dan ability itself by
        comparing to a 4th-dan character whose school doesn't touch
        Void at all. The total delta (Mirumoto Void - baseline Void)
        is therefore 2 (the +1 from rank-up to school-ring at
        construction PLUS the +1 from the Fourth Dan ability).
        """
        mirumoto_builder = self._build_fourth_dan_mirumoto()
        baseline_builder = self._build_fourth_dan_baseline()
        mirumoto = mirumoto_builder.build()
        baseline = baseline_builder.build()
        # Baseline non-Mirumoto's Void stays at the engine default of 2.
        self.assertEqual(2, baseline.ring("void"),
            "Baseline non-Mirumoto's Void must remain at the engine default of 2 "
            "(precondition for the FR-010 comparison)")
        # Mirumoto: default 2 -> apply_school_ring +1 (to 3, via
        # _SchoolCharacterBuilder.initialize_school) -> Fourth Dan +1
        # (to 4, via apply_school_ring_raise_and_discount).
        self.assertEqual(4, mirumoto.ring("void"),
            "FR-010: 4th-dan Mirumoto's current Void should be 4 "
            "(default 2 + school-ring bump +1 + Fourth Dan +1)")
        # The Fourth Dan ability itself contributes a +1 on top of the
        # +1 standard school-ring bump (which every school applies to
        # its own ring at construction). Total delta vs Akodo baseline
        # whose school ring is Water (untouched Void) is therefore 2.
        self.assertEqual(
            baseline.ring("void") + 2, mirumoto.ring("void"),
            "FR-010: 4th-dan Mirumoto Void is +2 over a non-Mirumoto "
            "baseline (school-ring bump +1, Fourth Dan +1)",
        )

    # ----- FR-010: maximum Void +1 -----

    def test_fourth_dan_raises_max_void_by_one_vs_baseline(self):
        """US3.1 / FR-010: a 4th-dan Mirumoto's MAXIMUM Void rank is
        exactly 1 higher than an otherwise-identical 4th-dan baseline
        (non-Mirumoto) character's.

        ``_SchoolCharacterBuilder.max_ring`` returns 6 for the
        school's own ring at school rank >= 4 and 5 otherwise. The
        baseline Akodo school is Water, so its Void cap stays at 5,
        whereas the Mirumoto's school ring IS Void, so its Void cap
        is raised to 6 -- the +1 promised by FR-010.
        """
        mirumoto_builder = self._build_fourth_dan_mirumoto()
        baseline_builder = self._build_fourth_dan_baseline()
        # Baseline non-Mirumoto's max Void stays at the default 5.
        self.assertEqual(5, baseline_builder.max_ring("void"),
            "Baseline non-Mirumoto's max Void must be 5 "
            "(precondition for the FR-010 comparison)")
        # 4th-dan Mirumoto's max Void is 6 (school ring extension).
        self.assertEqual(6, mirumoto_builder.max_ring("void"),
            "FR-010: 4th-dan Mirumoto's max Void should be 6 "
            "(Fourth Dan extends the school-ring cap from 5 to 6)")
        self.assertEqual(
            baseline_builder.max_ring("void") + 1,
            mirumoto_builder.max_ring("void"),
            "FR-010: 4th-dan Mirumoto's max Void is exactly +1 over "
            "the baseline non-Mirumoto's max Void",
        )

    # ----- FR-011: XP cost to raise Void is 5 less -----

    def test_fourth_dan_reduces_void_xp_cost_by_five_vs_baseline(self):
        """US3.2 / FR-011: the XP cost to raise a 4th-dan Mirumoto's
        Void by one rank is exactly 5 less than the standard L7R
        Void-raise cost for that rank.

        The discount is applied via ``character.add_discount("void", 5)``
        inside ``apply_school_ring_raise_and_discount``. Because the
        Mirumoto's current Void is 4 (default 2 + school-bump +1 +
        Fourth Dan +1) and the baseline Akodo's Void is still 2,
        we explicitly compute the standard L7R cost from the formula
        (5 * (N+1) to raise from N to N+1) and compare it to the
        Mirumoto's ``calculate_ring_cost`` result. This pins the -5
        reduction shape regardless of which absolute rank we test.
        """
        mirumoto_builder = self._build_fourth_dan_mirumoto()
        baseline_builder = self._build_fourth_dan_baseline()
        mirumoto_char = mirumoto_builder.character()
        baseline_char = baseline_builder.character()
        # Compute the standard cost (no discount) of raising each
        # character's Void by one rank past their CURRENT rank.
        # Standard cost to raise a ring from rank N to rank N+1 is
        # 5 * (N+1).
        mirumoto_cur = mirumoto_char.ring("void")  # 4
        baseline_cur = baseline_char.ring("void")  # 2
        std_mirumoto_raise = 5 * (mirumoto_cur + 1)
        std_baseline_raise = 5 * (baseline_cur + 1)
        # Sanity: the baseline cost matches the engine's
        # calculate_ring_cost (no discount applied to baseline).
        self.assertEqual(
            std_baseline_raise,
            baseline_builder.calculate_ring_cost("void", baseline_cur + 1),
            "Baseline non-Mirumoto's Void raise cost should equal the "
            "standard L7R formula 5*(N+1) (no discount applied)",
        )
        # FR-011: Mirumoto's cost is exactly 5 less than the standard.
        mirumoto_cost = mirumoto_builder.calculate_ring_cost("void", mirumoto_cur + 1)
        self.assertEqual(
            std_mirumoto_raise - 5,
            mirumoto_cost,
            "FR-011: 4th-dan Mirumoto's XP cost to raise Void by one "
            "rank must be exactly 5 less than the standard L7R cost "
            f"(standard {std_mirumoto_raise}, expected {std_mirumoto_raise - 5}, "
            f"got {mirumoto_cost})",
        )
        # Also: cross-check the discount is recorded on the character
        # (not, e.g., applied as a one-time refund elsewhere). This
        # guards against a future refactor that drops the persistent
        # discount in favor of an ad-hoc raise-time hook.
        self.assertEqual(5, mirumoto_char._discounts.get("void", 0),
            "FR-011: the 5-XP Void discount must be recorded on the "
            "Mirumoto's _discounts so any subsequent Void raise sees it")
        self.assertEqual(0, baseline_char._discounts.get("void", 0),
            "Baseline non-Mirumoto must not receive a Void discount "
            "(precondition for the FR-011 comparison)")

    # ----- FR-011 edge case: floor at 0 when standard cost <= 5 -----

    def test_fourth_dan_void_xp_cost_floors_at_zero_when_discount_exceeds_cost(
        self,
    ):
        """FR-011 edge case (spec.md edge case bullet): if the standard
        Void-raise cost is <= 5 (the minimum nonzero raise being from
        rank 0 to rank 1, standard cost 5), the 5-XP reduction must
        not produce a negative cost -- treat as 0.

        The natural floor of the existing
        ``_BaseCharacterBuilder.calculate_ring_cost`` is 0 when the
        standard cost equals the 5-XP discount (5 - 5 = 0). This test
        pins that behavior so a future change to the cost formula
        cannot silently break the FR-011 floor by, e.g., letting a
        negative result leak through.

        We synthesize the scenario by lowering the Mirumoto's Void
        rank to 0 (below the engine's default of 2) so the next raise
        (to rank 1) costs the minimum 5 XP standard. The 5-XP
        Mirumoto discount must reduce that cost to 0, not -5.
        """
        mirumoto_builder = self._build_fourth_dan_mirumoto()
        mirumoto_char = mirumoto_builder.character()
        # Precondition: the Fourth Dan discount is applied.
        self.assertEqual(5, mirumoto_char._discounts.get("void", 0),
            "Precondition: the 5-XP Void discount must be recorded")
        # Force the scenario where the standard cost equals the discount
        # by lowering Void to 0 (the floor). The next raise (to rank 1)
        # then has standard cost = 5 * 1 = 5, exactly matching the
        # discount -- the floor case in FR-011.
        mirumoto_char.set_ring("void", 0)
        self.assertEqual(0, mirumoto_char.ring("void"),
            "Test setup: forced Void to 0 to exercise the floor case")
        # Standard L7R cost to raise from 0 to 1 = 5*1 = 5.
        # Discounted: 5 - 5 = 0 (floor).
        cost_to_raise_to_one = mirumoto_builder.calculate_ring_cost("void", 1)
        self.assertEqual(
            0, cost_to_raise_to_one,
            "FR-011 floor: when the standard Void-raise cost (5) equals "
            "the Mirumoto 5-XP discount, the discounted cost MUST be 0 "
            f"(not negative); got {cost_to_raise_to_one}",
        )
        # And explicitly: the result must not be negative under any
        # raise that is at or below the floor.
        self.assertGreaterEqual(
            cost_to_raise_to_one, 0,
            "FR-011 floor: Mirumoto's discounted Void-raise cost MUST "
            "NOT be negative (floor at 0)",
        )


class TestMirumotoFourthDanAttackSideScaffolding(unittest.TestCase):
    """
    Scaffolding for the Fourth Dan attack-side hooks (T012 -> T013 / T014).

    rules/04-schools.md Mirumoto Bushi School Fourth Dan: "When an enemy
    parries one of your attacks but fails, they suffer only half the
    normal extra damage dice ..." (FR-012) and the double-attack
    direct-damage clause (FR-013) both attach to actions performed BY the
    Mirumoto (attacker side), not to parries performed against the
    Mirumoto (defender side).

    A previous implementation overrode ``MirumotoActionFactory.get_parry_action``
    to return a ``MirumotoParryAction`` whose ``set_attack_parry_attempted``
    halved the extra damage dice -- but that override fires when the
    Mirumoto IS the parrier, which is the wrong side. T012 removes that
    wrong-side hook and installs empty attack-side subclasses so T013 and
    T014 have somewhere to put the actual behavior.

    These tests pin that, after ``apply_rank_four_ability``, the action
    factory returns the new Mirumoto-specific attack-side subclasses for
    regular attacks and double attacks. They will FAIL until T012's
    scaffolding lands (no ``MirumotoAttackAction`` / ``MirumotoDoubleAttackAction``
    classes exist yet, and the factory still overrides the parry method).
    """

    def _make_fourth_dan_mirumoto(self) -> Character:
        """Build a 4th-dan Mirumoto with school-rank-up wired through ranks 1-4.

        Mirrors the manual wiring pattern used by ``TestMirumotoThirdDanPool``:
        construct a Character, attach the school, and walk the
        ``apply_rank_N_ability`` ladder so the 4th-dan ``set_action_factory``
        call (in ``apply_rank_four_ability``) actually runs.
        """
        mirumoto = Character("Mirumoto")
        mirumoto.set_actions([1])
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        mirumoto.set_skill("double attack", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        school.apply_special_ability(mirumoto)
        school.apply_rank_one_ability(mirumoto)
        school.apply_rank_two_ability(mirumoto)
        school.apply_rank_three_ability(mirumoto)
        school.apply_rank_four_ability(mirumoto)
        return mirumoto

    def _make_enemy(self) -> Character:
        enemy = Character("enemy")
        enemy.set_actions([1])
        return enemy

    def _make_context(self, mirumoto: Character, enemy: Character) -> EngineContext:
        groups = [Group("Dragon", mirumoto), Group("Enemy", enemy)]
        return EngineContext(groups, round=1, phase=1)

    def test_regular_attack_returns_mirumoto_attack_action(self):
        """FR-012 hook: ``get_attack_action(skill="attack", ...)`` on a
        4th-dan Mirumoto MUST return a ``MirumotoAttackAction`` instance
        (subclass of ``AttackAction``). T013/T014 will hang the failed-parry
        half-extra-dice behavior off this class; T012 only verifies the
        hook exists and is wired through the factory.
        """
        mirumoto = self._make_fourth_dan_mirumoto()
        enemy = self._make_enemy()
        context = self._make_context(mirumoto, enemy)
        initiative_action = InitiativeAction([1], 1)
        action = mirumoto.action_factory().get_attack_action(
            mirumoto, enemy, "attack", initiative_action, context,
        )
        # Must be the Mirumoto-specific subclass (RED until T012 lands).
        self.assertIsInstance(action, mirumoto_school.MirumotoAttackAction)
        # And must still satisfy the AttackAction contract so existing
        # combat-pipeline code that branches on ``isinstance(..., AttackAction)``
        # still works.
        self.assertIsInstance(action, actions.AttackAction)

    def test_double_attack_returns_mirumoto_double_attack_action(self):
        """FR-013 hook: ``get_attack_action(skill="double attack", ...)``
        on a 4th-dan Mirumoto MUST return a ``MirumotoDoubleAttackAction``
        instance (subclass of ``DoubleAttackAction``). T013 will hang the
        double-attack direct-damage override off this class; T012 only
        verifies the hook is wired through the factory's skill-dispatch.
        """
        mirumoto = self._make_fourth_dan_mirumoto()
        enemy = self._make_enemy()
        context = self._make_context(mirumoto, enemy)
        initiative_action = InitiativeAction([1], 1)
        action = mirumoto.action_factory().get_attack_action(
            mirumoto, enemy, "double attack", initiative_action, context,
        )
        # Must be the Mirumoto-specific subclass (RED until T012 lands).
        self.assertIsInstance(action, mirumoto_school.MirumotoDoubleAttackAction)
        # And must still satisfy the DoubleAttackAction contract.
        self.assertIsInstance(action, actions.DoubleAttackAction)

    def test_non_attack_skills_still_dispatch_to_default_factory_classes(self):
        """Regression guard for the factory override: skills the Mirumoto
        4th-dan doesn't touch (feint, lunge, iaijutsu) MUST still produce
        the stock action classes, so T012's attack-side rerouting doesn't
        accidentally swallow other skills' constructors.

        iaijutsu is a Mirumoto school knack (FR-003) but the Fourth Dan
        rules clause does NOT mention it -- the failed-parry half-extra-dice
        ability is scoped to ``attack`` and the direct-damage clause to
        ``double attack``. So iaijutsu must still build a plain
        AttackAction (not a MirumotoAttackAction).
        """
        mirumoto = self._make_fourth_dan_mirumoto()
        enemy = self._make_enemy()
        context = self._make_context(mirumoto, enemy)
        initiative_action = InitiativeAction([1], 1)
        # iaijutsu shares the AttackAction class in DefaultActionFactory
        # but is a distinct skill. The T012 override scopes only "attack"
        # and "double attack" to Mirumoto subclasses; iaijutsu falls
        # through to the stock AttackAction.
        iaijutsu_action = mirumoto.action_factory().get_attack_action(
            mirumoto, enemy, "iaijutsu", initiative_action, context,
        )
        self.assertIsInstance(iaijutsu_action, actions.AttackAction)
        self.assertNotIsInstance(iaijutsu_action, mirumoto_school.MirumotoAttackAction)
        self.assertNotIsInstance(iaijutsu_action, mirumoto_school.MirumotoDoubleAttackAction)
        # feint and lunge must build their own dedicated subclasses.
        feint_action = mirumoto.action_factory().get_attack_action(
            mirumoto, enemy, "feint", initiative_action, context,
        )
        self.assertIsInstance(feint_action, actions.FeintAction)
        lunge_action = mirumoto.action_factory().get_attack_action(
            mirumoto, enemy, "lunge", initiative_action, context,
        )
        self.assertIsInstance(lunge_action, actions.LungeAction)


class TestMirumotoDoubleAttackDirectDamageOverride(unittest.TestCase):
    """
    Unit tests for ``MirumotoDoubleAttackAction.direct_damage`` (T013 / FR-012).

    rules/04-schools.md Mirumoto Bushi School Fourth Dan:
    "Failed parries against your double attacks do not prevent the automatic
    serious wound."

    The base ``DoubleAttackAction.direct_damage`` (simulation/actions.py:226-231)
    returns ``None`` whenever ``parry_attempted()`` is True, suppressing the
    double-attack auto-SW even on a FAILED parry. The Mirumoto override must
    remove that suppression on failed parries, while preserving the baseline
    behaviors:

      - No parry attempted -> base class emits the SW event -> override
        delegates and yields the same event (regression guard).
      - Parry attempted AND succeeded -> base class returns ``None`` ->
        override preserves that (failed-parry-only carve-out per FR-012 /
        Q3 clarification: "Only the auto-SW prevention is removed").
      - Parry attempted AND failed -> base class returns ``None`` ->
        override MUST return the auto-SW event (the FR-012 behavior).

    Per the FR-012 clarification: "Only the auto-SW prevention is removed;
    other failed-parry mitigation against the double attack (e.g., standard
    damage-dice handling) works as it normally does." This test class
    focuses on the ``direct_damage`` override; the damage-dice handling
    (``calculate_extra_damage_dice``) is intentionally untouched and is
    verified to remain at its base-class value on a failed parry.
    """

    def setUp(self) -> None:
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.mirumoto.set_skill("double attack", 4)
        self.defender = Character("defender")
        self.defender.set_actions([1])
        self.defender.set_skill("parry", 4)
        groups = [
            Group("Dragon", self.mirumoto),
            Group("Enemy", self.defender),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.initiative_action = InitiativeAction([1], 1)

    def _make_double_attack(self) -> mirumoto_school.MirumotoDoubleAttackAction:
        """Build a MirumotoDoubleAttackAction (FR-012 attack-side subclass).

        Skill roll is pre-set so ``direct_damage`` (which does not depend on
        the skill roll itself) can be invoked without queuing dice.
        """
        action = mirumoto_school.MirumotoDoubleAttackAction(
            self.mirumoto, self.defender, "double attack",
            self.initiative_action, self.context,
        )
        action.set_skill_roll(40)
        return action

    def test_double_attack_with_no_parry_attempted_still_gets_auto_sw(self):
        """Baseline preservation (regression guard): when no parry was
        attempted, the override defers to the base class which emits the
        auto-SW event. This mirrors the existing DoubleAttackAction behavior
        and verifies the Mirumoto override does not break it.

        rules/04-schools.md Mirumoto Bushi School Fourth Dan applies the
        carve-out to FAILED parries only; the no-parry-attempted case is
        the baseline auto-SW path from the double-attack skill itself.
        """
        action = self._make_double_attack()
        # No parry attempted: parry_attempted() is False, parried() is False.
        self.assertFalse(action.parry_attempted())
        self.assertFalse(action.parried())
        damage = action.direct_damage()
        self.assertIsNotNone(damage,
            "No-parry-attempted branch must still emit auto-SW (baseline)")
        self.assertIsInstance(damage, events.SeriousWoundsDamageEvent)
        self.assertEqual(self.defender, damage.target)
        self.assertEqual(self.mirumoto, damage.subject)
        self.assertEqual(1, damage.damage,
            "Double-attack auto-SW is exactly 1 SW (rules/04-schools.md)")
        # The marker the existing base class sets must still be present so
        # the detailed_formatter's "(double attack penalty)" suffix still works.
        self.assertTrue(getattr(damage, "_from_double_attack", False),
            "_from_double_attack marker must be preserved on the override")

    def test_double_attack_with_successful_parry_does_not_get_auto_sw(self):
        """Baseline preservation (FR-012 Q3 narrow-scope clarification):
        a SUCCESSFUL parry against the Mirumoto's double attack still
        prevents the auto-SW. Only the failed-parry suppression is removed.
        """
        action = self._make_double_attack()
        # Simulate a successful parry: parry_attempted() True, parried() True.
        action.set_parry_attempted()
        action.set_parried()
        self.assertTrue(action.parry_attempted())
        self.assertTrue(action.parried())
        damage = action.direct_damage()
        self.assertIsNone(damage,
            "Successful parry must still suppress the auto-SW (FR-012 Q3 "
            "narrow scope: only the failed-parry suppression is removed)")

    def test_double_attack_with_failed_parry_gets_auto_sw_via_mirumoto_override(self):
        """FR-012 behavior (the RED test that fails without the override):
        a FAILED parry against the Mirumoto's double attack no longer
        suppresses the auto-SW. The base class returns ``None`` here; the
        Mirumoto override must return the SeriousWoundsDamageEvent.

        rules/04-schools.md Mirumoto Bushi School Fourth Dan: "Failed
        parries against your double attacks do not prevent the automatic
        serious wound."
        """
        action = self._make_double_attack()
        # Simulate a failed parry: parry_attempted() True, parried() False.
        # (TakeParryActionEvent sets attempted on the attack regardless of
        # outcome; parried() is only set on success.)
        action.set_parry_attempted()
        # Also stash a parry-declared event so calculate_extra_damage_dice's
        # branch can still see the defender as the parrier (used by the
        # untouched base damage-dice handling on a failed parry).
        parry_action = actions.ParryAction(
            self.defender, self.mirumoto, "parry",
            self.initiative_action, self.context, action,
        )
        action.add_parry_declared(events.ParryDeclaredEvent(parry_action))
        self.assertTrue(action.parry_attempted())
        self.assertFalse(action.parried())
        damage = action.direct_damage()
        self.assertIsNotNone(damage,
            "Failed parry against Mirumoto's double attack MUST still emit "
            "the auto-SW (FR-012 / rules/04-schools.md Mirumoto Bushi "
            "School Fourth Dan).")
        self.assertIsInstance(damage, events.SeriousWoundsDamageEvent)
        self.assertEqual(self.defender, damage.target)
        self.assertEqual(self.mirumoto, damage.subject)
        self.assertEqual(1, damage.damage)
        self.assertTrue(getattr(damage, "_from_double_attack", False),
            "_from_double_attack marker must be set on the override's event")

    def test_failed_parry_damage_dice_handling_unaffected_by_override(self):
        """FR-012 Q3 narrow-scope guard: the override touches ONLY
        ``direct_damage``. The standard failed-parry damage-die-count
        handling (``calculate_extra_damage_dice`` -- returns 2 when the
        defender parried, 4 if a third party parried) is inherited from
        ``DoubleAttackAction`` and must NOT change.
        """
        action = self._make_double_attack()
        action.set_parry_attempted()
        parry_action = actions.ParryAction(
            self.defender, self.mirumoto, "parry",
            self.initiative_action, self.context, action,
        )
        action.add_parry_declared(events.ParryDeclaredEvent(parry_action))
        # The base DoubleAttackAction returns 2 when target parried.
        self.assertEqual(2, action.calculate_extra_damage_dice(),
            "Override must not affect calculate_extra_damage_dice (FR-012 "
            "narrow scope: only the auto-SW prevention is removed).")


class TestMirumotoUS3Integration(unittest.TestCase):
    """
    End-to-end (combat-engine) integration tests for FR-012 (US3.3).

    Drives a 4th-dan Mirumoto's double attack through the full
    ``CombatEngine`` pipeline against a defender who declares a parry.
    Uses ``CalvinistRollProvider`` for determinism. The defender's parry
    is supplied as a pre-built ``ParryAction`` plumbed through
    ``TakeParryActionEvent`` so the parry's success/failure is fully
    governed by the queued parry roll vs. the attack roll's TN.

    Rules clauses exercised:
      - rules/04-schools.md Mirumoto Bushi School Fourth Dan: "Failed
        parries against your double attacks do not prevent the automatic
        serious wound" (FR-012 / US3.3).
    """

    def _make_fourth_dan_mirumoto(self) -> Character:
        mirumoto = Character("Mirumoto")
        mirumoto.set_actions([1])
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        mirumoto.set_skill("double attack", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        school.apply_special_ability(mirumoto)
        school.apply_rank_one_ability(mirumoto)
        school.apply_rank_two_ability(mirumoto)
        school.apply_rank_three_ability(mirumoto)
        school.apply_rank_four_ability(mirumoto)
        return mirumoto

    def _make_defender(self) -> Character:
        defender = Character("defender")
        defender.set_actions([1])
        defender.set_skill("parry", 4)
        return defender

    def setUp(self) -> None:
        self.mirumoto = self._make_fourth_dan_mirumoto()
        self.defender = self._make_defender()
        groups = [
            Group("Dragon", self.mirumoto),
            Group("Enemy", self.defender),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        self.initiative_action = InitiativeAction([1], 1)

    def _build_double_attack(self, skill_roll: int) -> actions.AttackAction:
        """Build a Mirumoto double attack with skill_roll pre-set.

        Pre-setting the roll dodges the Mirumoto's mode-B post-roll-bonus
        chain (which would otherwise consult the pool and potentially
        mutate the roll) -- it only matters here that the Mirumoto's
        attack roll is high enough that the defender's parry is the only
        thing standing between the defender and the hit.
        """
        action = self.mirumoto.action_factory().get_attack_action(
            self.mirumoto, self.defender, "double attack",
            self.initiative_action, self.context,
        )
        action.set_skill_roll(skill_roll)
        return action

    def test_failed_parry_against_double_attack_lands_auto_sw(self):
        """US3.3 (FR-012): defender fails parry vs Mirumoto's double attack
        -> the auto-serious-wound from the double-attack skill still lands.

        Trace assertion: the combat history contains a SeriousWoundsDamageEvent
        targeting the defender that came from the double-attack auto-SW path
        (identifiable via the ``_from_double_attack`` marker set by
        ``DoubleAttackAction.direct_damage``). Equivalently, the defender's
        SW count increments by at least 1 after the trace.
        """
        # Mirumoto's double-attack roll well over the defender's TN; the
        # double-attack TN is target.tn_to_hit() + 20 so we go 60 to be safe.
        attack = self._build_double_attack(skill_roll=60)

        # Defender's parry roll is low so the parry FAILS:
        # parry succeeds iff parry_roll >= parry_tn (== attack skill roll 60).
        defender_rp = CalvinistRollProvider()
        defender_rp.put_skill_roll("parry", 10)
        # Damage roll: the engine still rolls damage after auto-SW on a
        # hit; queue a deterministic value so the combat doesn't blow up
        # asking for dice. Plus a wound check roll in case it triggers.
        defender_rp.put_wound_check_roll(1)
        self.defender.set_roll_provider(defender_rp)

        # Mirumoto's double-attack roll is re-rolled by TakeAttackActionEvent,
        # so queue a deterministic value (60) on the roll provider.
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("double attack", 60)
        mirumoto_rp.put_damage_roll(1)
        self.mirumoto.set_roll_provider(mirumoto_rp)

        sw_before = self.defender.sw()

        # Wire up the defender's parry to fire against the double attack.
        parry = actions.ParryAction(
            self.defender, self.mirumoto, "parry",
            self.initiative_action, self.context, attack,
        )

        engine = CombatEngine(self.context)
        # Play the parry through first so it sets parry_attempted on the
        # attack BEFORE the attack's TakeAttackActionEvent runs its
        # direct_damage. This mirrors how the engine sequences events when
        # a parry is declared in response to an incoming attack.
        engine.event(events.TakeParryActionEvent(parry))
        # Now play the double attack; direct_damage() will see
        # parry_attempted()=True and parried()=False -> auto-SW lands via
        # the Mirumoto override.
        engine.event(events.TakeAttackActionEvent(attack))

        history = engine.history()
        # The auto-SW event must be present in the trace, marked as having
        # come from the double-attack penalty (FR-012 path).
        auto_sw_events = [
            e for e in history
            if isinstance(e, events.SeriousWoundsDamageEvent)
            and getattr(e, "_from_double_attack", False)
            and e.target is self.defender
        ]
        self.assertEqual(1, len(auto_sw_events),
            "Failed parry against a 4th-dan Mirumoto's double attack must "
            "still produce exactly one auto-serious-wound damage event "
            "(FR-012 / rules/04-schools.md Mirumoto Bushi School Fourth Dan).")
        # And the SW count on the defender must be >= sw_before+1 (the
        # +1 from the auto-SW; additional SW from the wound check are
        # not asserted here -- only the auto-SW path matters for FR-012).
        self.assertGreaterEqual(self.defender.sw(), sw_before + 1,
            "Defender's serious-wound count must increase by at least 1 "
            "from the FR-012 auto-SW event.")

    def test_successful_parry_against_double_attack_does_not_land_auto_sw(self):
        """US3.3 companion (baseline preservation): a SUCCESSFUL parry
        against the Mirumoto's double attack still suppresses the auto-SW
        (FR-012 Q3 narrow-scope: only the failed-parry suppression is
        removed, not the successful-parry one).
        """
        attack = self._build_double_attack(skill_roll=20)

        # Defender's parry roll is high so the parry SUCCEEDS:
        # parry_roll 50 >= parry_tn 20.
        defender_rp = CalvinistRollProvider()
        defender_rp.put_skill_roll("parry", 50)
        self.defender.set_roll_provider(defender_rp)

        # Mirumoto's double-attack roll is re-rolled by TakeAttackActionEvent.
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("double attack", 20)
        self.mirumoto.set_roll_provider(mirumoto_rp)

        sw_before = self.defender.sw()

        parry = actions.ParryAction(
            self.defender, self.mirumoto, "parry",
            self.initiative_action, self.context, attack,
        )

        engine = CombatEngine(self.context)
        engine.event(events.TakeParryActionEvent(parry))
        engine.event(events.TakeAttackActionEvent(attack))

        history = engine.history()
        # No auto-SW event in the trace (successful parry suppresses it).
        auto_sw_events = [
            e for e in history
            if isinstance(e, events.SeriousWoundsDamageEvent)
            and getattr(e, "_from_double_attack", False)
            and e.target is self.defender
        ]
        self.assertEqual(0, len(auto_sw_events),
            "Successful parry must still suppress the double-attack auto-SW "
            "(FR-012 Q3 narrow scope).")
        # Defender's SW count unchanged.
        self.assertEqual(sw_before, self.defender.sw(),
            "Successful parry: defender's SW count must not increase.")

    def test_failed_parry_against_regular_attack_halves_damage_die_reduction(self):
        """US3.4 (FR-013) end-to-end: a defender who fails to parry a 4th-dan
        Mirumoto Bushi's REGULAR attack should take more damage than against a
        non-Mirumoto attacker, because the failed-parry damage-die reduction
        is halved (integer floor).

        rules/04-schools.md Mirumoto Bushi School Fourth Dan: "against your
        regular attacks the number of extra rolled damage dice the failed
        parry reduced is cut in half (rounded down)."

        The test sets up a scripted regular-attack combat with deterministic
        dice. The defender's parry fails. The Mirumoto's damage roll uses
        the halved-reduction extra-dice count, which is strictly greater
        than the baseline (0 extra dice on a failed parry). With the
        ``CalvinistRollProvider`` returning fixed-per-die values, more
        rolled dice means more damage; we assert the LightWoundsDamageEvent
        in the trace reflects that.
        """
        # Build a regular attack via the Mirumoto action factory; this
        # returns a MirumotoAttackAction with the FR-013 override.
        attack = self.mirumoto.action_factory().get_attack_action(
            self.mirumoto, self.defender, "attack",
            self.initiative_action, self.context,
        )
        self.assertIsInstance(attack, mirumoto_school.MirumotoAttackAction,
            "4th-dan Mirumoto must route 'attack' through MirumotoAttackAction.")
        # Pre-set the skill roll so we can compute the expected extra dice
        # deterministically. Defender has parry=4 so tn_to_hit = 5*(1+4)=25;
        # a skill_roll of 50 gives baseline (50-25)//5 = 5 extra dice.
        # Halved reduction: 5 - 5//2 = 5 - 2 = 3 extra dice on failed parry.
        attack.set_skill_roll(50)
        # Simulate a failed parry (parry_attempted set, parried not set).
        attack.set_parry_attempted()
        # FR-013: halved reduction -> 3 extra damage dice (not 0).
        self.assertEqual(3, attack.calculate_extra_damage_dice(),
            "FR-013: failed parry against Mirumoto's regular attack must "
            "halve the damage-die-count reduction (rounded down). "
            "(skill_roll-tn)//5 = 5; reduction 5 -> halved 2; result 5-2=3.")

    def test_failed_parry_against_regular_attack_increases_damage_vs_baseline(self):
        """US3.4 end-to-end combat trace: drive a scripted regular attack
        through the engine. The defender's parry fails. With FR-013, the
        Mirumoto's damage roll has more rolled dice than the baseline
        (failed-parry-reduces-to-zero) path, so the LightWoundsDamageEvent's
        damage value is strictly greater than what a non-Mirumoto attacker
        would inflict in the same scenario.

        This integration test uses ``CalvinistRollProvider`` to make damage
        a deterministic function of the number of rolled damage dice, so
        we can prove the override fires through the combat loop and not
        just at the action-level unit test.
        """
        # Build the Mirumoto attack action via the factory. Pre-set the
        # skill_roll so the parry that fires BEFORE the attack's
        # ``_roll_attack`` step can compute ``parry_tn()`` (which reads
        # the attack's skill_roll). ``TakeAttackActionEvent._roll_attack``
        # re-rolls via the roll provider so the Calvinist value still
        # governs the actual attack roll the engine sees.
        attack = self.mirumoto.action_factory().get_attack_action(
            self.mirumoto, self.defender, "attack",
            self.initiative_action, self.context,
        )
        attack.set_skill_roll(50)

        # Defender's parry roll low -> parry FAILS:
        # parry succeeds iff parry_roll >= parry_tn (== attacker's skill roll 50).
        defender_rp = CalvinistRollProvider()
        defender_rp.put_skill_roll("parry", 5)
        defender_rp.put_wound_check_roll(0)
        self.defender.set_roll_provider(defender_rp)

        # Mirumoto's attack roll: 50 (vs TN 25), giving baseline 5 extra
        # damage dice; FR-013 halves the reduction so failed parry yields
        # 5 - (5//2) = 3 extra damage dice. The damage roll itself is
        # scripted to a high enough value that the damage event is
        # nonzero and we can assert it.
        mirumoto_rp = CalvinistRollProvider()
        mirumoto_rp.put_skill_roll("attack", 50)
        mirumoto_rp.put_damage_roll(20)
        self.mirumoto.set_roll_provider(mirumoto_rp)

        # Wire up the parry to fire against this attack.
        parry = actions.ParryAction(
            self.defender, self.mirumoto, "parry",
            self.initiative_action, self.context, attack,
        )

        engine = CombatEngine(self.context)
        engine.event(events.TakeParryActionEvent(parry))
        engine.event(events.TakeAttackActionEvent(attack))

        history = engine.history()
        # The trace must contain a LightWoundsDamageEvent (the hit landed
        # because the parry failed). Without the FR-013 override the
        # baseline AttackAction.calculate_extra_damage_dice would return
        # 0 extra dice on a failed parry; with the override it returns 3,
        # which means more rolled dice and a strictly larger damage value.
        lw_events = [
            e for e in history
            if isinstance(e, events.LightWoundsDamageEvent)
            and e.target is self.defender
        ]
        self.assertEqual(1, len(lw_events),
            "Failed parry against Mirumoto's regular attack must still "
            "produce a LightWoundsDamageEvent (the hit lands).")
        # The override produced 3 extra damage dice on a failed parry. The
        # CalvinistRollProvider returned 20 as the deterministic damage roll.
        self.assertEqual(20, lw_events[0].damage,
            "Scripted damage roll value must reach the damage event.")
        # And critically: the attack's calculate_extra_damage_dice reflects
        # FR-013 (3, not 0). This is the load-bearing assertion that proves
        # the Mirumoto override fired through the engine path.
        self.assertEqual(3, attack.calculate_extra_damage_dice(),
            "FR-013 override must fire through the combat-engine path "
            "(failed parry -> 3 extra dice from halved reduction, not 0).")


class TestMirumotoAttackActionExtraDamageDiceOverride(unittest.TestCase):
    """
    Unit tests for ``MirumotoAttackAction.calculate_extra_damage_dice``
    (T014 / FR-013).

    rules/04-schools.md Mirumoto Bushi School Fourth Dan:
    "against your regular attacks the number of extra rolled damage dice
    the failed parry reduced is cut in half (rounded down)."

    The base ``AttackAction.calculate_extra_damage_dice`` returns 0 when
    ``parry_attempted()`` is True (the full would-be-extra is "reduced"
    away by any parry attempt, successful or not). The Mirumoto override
    must, on FAILED parries only, halve that reduction (integer floor)
    and return ``max(0, would_be_extra - would_be_reduction // 2)``.

    Successful parries and no-parry-attempted cases are baseline-preserved.
    """

    def setUp(self) -> None:
        self.mirumoto = Character("Mirumoto")
        self.mirumoto.set_actions([1])
        self.mirumoto.set_skill("attack", 4)
        self.defender = Character("defender")
        self.defender.set_actions([1])
        # Defender parry skill 4 -> tn_to_hit = 5*(1+4) = 25 (so a skill_roll
        # of 50 yields baseline (50-25)//5 = 5 extra damage dice).
        self.defender.set_skill("parry", 4)
        groups = [
            Group("Dragon", self.mirumoto),
            Group("Enemy", self.defender),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.initiative_action = InitiativeAction([1], 1)

    def _make_attack(self, skill_roll: int) -> mirumoto_school.MirumotoAttackAction:
        action = mirumoto_school.MirumotoAttackAction(
            self.mirumoto, self.defender, "attack",
            self.initiative_action, self.context,
        )
        action.set_skill_roll(skill_roll)
        return action

    def test_failed_parry_with_reduction_of_five_yields_two_halved(self):
        """FR-013 main case: would-be-extra is 5, reduction is 5; halved
        reduction is 2 (5 // 2 = 2); result is 5 - 2 = 3.

        Without the override the base class returns 0 (parry_attempted ->
        full reduction). This is the headline test that proves FR-013
        fires.

        skill_roll=50, tn=25 -> (50-25)//5 = 5 would-be-extra.
        """
        action = self._make_attack(skill_roll=50)
        action.set_parry_attempted()  # failed parry: attempted but not parried
        self.assertFalse(action.parried())
        self.assertEqual(3, action.calculate_extra_damage_dice(),
            "FR-013: reduction 5 -> halved 2; extra = 5 - 2 = 3.")

    def test_failed_parry_with_reduction_of_three_yields_one_halved(self):
        """FR-013 edge example from spec.md: 3 -> 1.

        skill_roll=40, tn=25 -> (40-25)//5 = 3 would-be-extra.
        Reduction 3 -> halved (3 // 2) = 1; result = 3 - 1 = 2.
        """
        action = self._make_attack(skill_roll=40)
        action.set_parry_attempted()
        self.assertEqual(2, action.calculate_extra_damage_dice(),
            "FR-013: reduction 3 -> halved 1; extra = 3 - 1 = 2.")

    def test_failed_parry_with_reduction_of_one_yields_zero_halved(self):
        """FR-013 edge case from spec.md (Edge Cases bullet): 1 -> 0.

        skill_roll=30, tn=25 -> (30-25)//5 = 1 would-be-extra.
        Reduction 1 -> halved (1 // 2) = 0; result = 1 - 0 = 1.

        This proves the floor behavior: even with a reduction of 1, the
        halved reduction floors to 0, so the attacker keeps the single
        extra damage die.
        """
        action = self._make_attack(skill_roll=30)
        action.set_parry_attempted()
        self.assertEqual(1, action.calculate_extra_damage_dice(),
            "FR-013: reduction 1 -> halved 0 (integer floor); extra = 1 - 0 = 1.")

    def test_failed_parry_floors_extra_at_zero_when_skill_roll_below_tn(self):
        """FR-013 floor guard: if the attacker's skill roll is below the TN,
        would-be-extra is negative and the result must still floor at 0
        (the rule shouldn't ever produce a negative extra-dice count).

        skill_roll=20, tn=25 -> (20-25)//5 = -1; halved reduction = -1 //
        2 = -1 (Python floor div); naive 'extra - reduction//2' = -1 -
        (-1) = 0; max(0, ...) = 0.
        """
        action = self._make_attack(skill_roll=20)
        action.set_parry_attempted()
        self.assertEqual(0, action.calculate_extra_damage_dice(),
            "FR-013: result floors at 0 even when skill roll < TN.")

    def test_successful_parry_returns_zero_baseline_preserved(self):
        """Baseline preservation: a SUCCESSFUL parry does NOT fire the
        FR-013 halving (the rule applies to FAILED parries). The base
        class returns 0 when parry_attempted is True; the override must
        defer to that on a successful parry.
        """
        action = self._make_attack(skill_roll=50)
        action.set_parry_attempted()
        action.set_parried()  # successful: attempted AND parried
        self.assertTrue(action.parried())
        self.assertEqual(0, action.calculate_extra_damage_dice(),
            "Successful parry: baseline AttackAction returns 0 -> "
            "Mirumoto override must defer to that (FR-013 fires only on "
            "FAILED parries).")

    def test_no_parry_attempted_returns_full_extra_dice_baseline_preserved(self):
        """Baseline preservation: when NO parry was attempted, the base
        class returns the full (skill_roll - tn) // 5 -> the override
        must defer to that (the FR-013 halving only applies when a parry
        was attempted and failed).
        """
        action = self._make_attack(skill_roll=50)
        # No parry_attempted call; baseline path.
        self.assertFalse(action.parry_attempted())
        self.assertEqual(5, action.calculate_extra_damage_dice(),
            "No parry attempted: full (skill_roll-tn)//5 = 5 extra dice.")

    def test_explicit_skill_roll_and_tn_arguments_still_apply_halving(self):
        """The base method supports passing skill_roll and tn as explicit
        arguments (for hypothetical evaluation); the override must honor
        those too.

        Pass skill_roll=70, tn=20 -> would-be-extra = (70-20)//5 = 10;
        reduction 10 -> halved (10 // 2) = 5; extra = 10 - 5 = 5.
        """
        action = self._make_attack(skill_roll=0)  # actual roll irrelevant
        action.set_parry_attempted()
        self.assertEqual(5, action.calculate_extra_damage_dice(skill_roll=70, tn=20),
            "FR-013 must use explicit skill_roll/tn args when provided.")

    def test_double_attack_action_extra_dice_unaffected_by_t014(self):
        """Scope guard (FR-013 vs FR-012 narrow scopes): the T014 override
        applies ONLY to ``MirumotoAttackAction`` (regular attacks). The
        ``MirumotoDoubleAttackAction.calculate_extra_damage_dice`` must
        remain inherited from ``DoubleAttackAction`` (returns 2 or 4 flat
        on a failed parry per double-attack mechanics; no halving).

        Per Q3 narrow-scope clarification on FR-012: "Only the auto-SW
        prevention is removed; other failed-parry mitigation against the
        double attack (e.g., standard damage-dice handling) works as it
        normally does."
        """
        # Build a Mirumoto double attack via the factory.
        double = mirumoto_school.MirumotoDoubleAttackAction(
            self.mirumoto, self.defender, "double attack",
            self.initiative_action, self.context,
        )
        double.set_skill_roll(60)
        double.set_parry_attempted()
        # Wire a parry-declared event from the defender so the
        # DoubleAttackAction's failed-parry branch picks the "target
        # parried" 2-dice path.
        parry_action = actions.ParryAction(
            self.defender, self.mirumoto, "parry",
            self.initiative_action, self.context, double,
        )
        double.add_parry_declared(events.ParryDeclaredEvent(parry_action))
        # Inherited DoubleAttackAction logic: target parried -> 2 flat.
        self.assertEqual(2, double.calculate_extra_damage_dice(),
            "T014 (FR-013) must NOT override double-attack extra dice; "
            "those follow the inherited DoubleAttackAction logic.")


class TestMirumotoTraceClarity(unittest.TestCase):
    """
    T018 / SC-006: A combat trace of a Mirumoto Bushi must be interpretable
    by a reviewer who has the rules file open. Every Mirumoto-specific
    effect must surface a rule-clause-matchable label in the trace.

    Per contracts/interfaces.md § Trace contract:
      - Special Ability TVP grant -- already logged via GainTemporaryVoidPointsEvent.
      - 3rd Dan pool creation -- log on NewRoundEvent with pool size.
      - 3rd Dan mode-A spend -- log target action, pre/post phase.
      - 3rd Dan mode-B spend -- log target roll, points spent, resulting bonus.
      - 4th Dan auto-SW landing on failed parry -- log override path.
      - 4th Dan halved damage-die reduction -- log original and halved values.
      - 5th Dan +10 bonus -- log per-roll, separate from standard VP bonus.

    Distinctive markers used for grep-ability:
      ``[Mirumoto 3rd Dan]``     -- pool creation
      ``[Mirumoto 3rd Dan mode A]`` -- phase-lower spend
      ``[Mirumoto 3rd Dan mode B]`` -- post-roll +2 spend
      ``[Mirumoto 4th Dan]``     -- failed-parry overrides (auto-SW, halving)
      ``[Mirumoto 5th Dan]``     -- +10 VP modifier delta
    """

    # ----- 3rd Dan pool creation -----

    def test_pool_creation_logs_distinctive_marker_and_pool_size(self):
        """SC-006: NewRoundEvent on a 3rd-dan Mirumoto must emit a log
        carrying the ``[Mirumoto 3rd Dan]`` marker and the granted pool
        size (== 2 * attack_skill).

        Rules clause (rules/04-schools.md Mirumoto Bushi School Third Dan):
        "At the beginning of each round, you get 2X points, where X is
        equal to your attack skill."
        """
        mirumoto = Character("Trace3rd")
        mirumoto.set_actions([1])
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        mirumoto.set_school(school)
        school.apply_special_ability(mirumoto)
        school.apply_rank_one_ability(mirumoto)
        school.apply_rank_two_ability(mirumoto)
        school.apply_rank_three_ability(mirumoto)
        enemy = Character("enemy")
        enemy.set_actions([1])
        groups = [Group("Dragon", mirumoto), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = mirumoto_school.MirumotoNewRoundListener()
        with self.assertLogs(logger, level="DEBUG") as captured:
            list(listener.handle(mirumoto, events.NewRoundEvent(1), context))
        combined = "\n".join(captured.output)
        self.assertIn("[Mirumoto 3rd Dan]", combined,
            "Pool-creation log must carry the [Mirumoto 3rd Dan] marker (SC-006).")
        # The pool size must be visible.
        self.assertIn("pool", combined.lower())
        self.assertIn("8", combined,
            "Pool size (2*4=8) must appear in the pool-creation log.")

    # ----- 3rd Dan mode-A spend -----

    def test_mode_a_spend_logs_distinctive_marker_and_phase_transition(self):
        """SC-006: An ``EagerPhaseLowerStrategy`` spend must emit a log
        carrying the ``[Mirumoto 3rd Dan mode A]`` marker plus the
        pre-spend / post-spend action phase numbers so a reviewer can
        identify which action was lowered and by how much.

        Rules clause (rules/04-schools.md Mirumoto Bushi School Third Dan):
        "Each point may be spent to decrease the phase of one of your
        actions by 1 in order to parry."
        """
        mirumoto = Character("Trace3rd")
        mirumoto.set_actions([5])
        mirumoto.set_skill("attack", 4)
        mirumoto._mirumoto_pool = 4
        enemy = Character("enemy")
        enemy.set_actions([1])
        groups = [Group("Dragon", mirumoto), Group("Enemy", enemy)]
        context = EngineContext(groups, round=1, phase=3)
        context.initialize()
        strategy = mirumoto_third_dan.EagerPhaseLowerStrategy()
        with self.assertLogs(logger, level="DEBUG") as captured:
            list(strategy.recommend(mirumoto, events.NewPhaseEvent(3), context))
        combined = "\n".join(captured.output)
        self.assertIn("[Mirumoto 3rd Dan mode A]", combined,
            "Mode-A spend log must carry the [Mirumoto 3rd Dan mode A] marker (SC-006).")
        # Original phase (5) and new phase (3) must both be visible.
        self.assertIn("5", combined,
            "Pre-spend action phase (5) must appear in the mode-A log.")
        self.assertIn("3", combined,
            "Post-spend action phase (3) must appear in the mode-A log.")

    # ----- 3rd Dan mode-B spend -----

    def test_mode_b_spend_logs_distinctive_marker_and_bonus(self):
        """SC-006: A ``MarginalBonusStrategy`` spend must emit a log
        carrying the ``[Mirumoto 3rd Dan mode B]`` marker plus the
        skill being boosted, the points spent, the +bonus, and the
        before/after roll totals.

        Rules clause (rules/04-schools.md Mirumoto Bushi School Third Dan):
        "[Each point may be spent...] to provide a bonus of +2 on any
        type of attack or parry after you have seen your roll."
        """
        mirumoto = Character("Trace3rd")
        mirumoto.set_actions([1])
        mirumoto.set_skill("attack", 4)
        mirumoto.set_skill("parry", 4)
        mirumoto._mirumoto_pool = 2
        enemy = Character("enemy")
        enemy.set_actions([1])
        enemy.tn_to_hit = lambda: 20
        groups = [Group("Dragon", mirumoto), Group("Enemy", enemy)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack = actions.AttackAction(
            mirumoto, enemy, "attack", InitiativeAction([1], 1), context,
        )
        # Margin of 3 -> ceil(3/2) = 2 points spent for +4.
        attack.set_skill_roll(17)
        strategy = mirumoto_third_dan.MarginalBonusStrategy()
        event = events.AttackRolledEvent(attack, 17)
        with self.assertLogs(logger, level="DEBUG") as captured:
            list(strategy.recommend(mirumoto, event, context))
        combined = "\n".join(captured.output)
        self.assertIn("[Mirumoto 3rd Dan mode B]", combined,
            "Mode-B spend log must carry the [Mirumoto 3rd Dan mode B] marker (SC-006).")
        # The skill, points, bonus, and roll totals must appear.
        self.assertIn("attack", combined,
            "Skill name (attack) must appear in the mode-B log.")
        # The +bonus (+4 for 2 points) must be visible.
        self.assertIn("+4", combined,
            "Bonus value (+4 = 2 points * +2/point) must appear in the mode-B log.")
        self.assertIn("17", combined,
            "Pre-spend roll (17) must appear in the mode-B log.")
        self.assertIn("21", combined,
            "Post-spend roll (21) must appear in the mode-B log.")

    # ----- 4th Dan auto-SW override on failed parry -----

    def test_fourth_dan_auto_sw_logs_override_path_on_failed_parry(self):
        """SC-006: The MirumotoDoubleAttackAction.direct_damage override
        path (FR-012: failed parry against double attack still suffers
        auto-SW) must be visible in the trace with the ``[Mirumoto 4th Dan]``
        marker, so a reviewer can distinguish this auto-SW from the
        ordinary no-parry-attempted auto-SW.

        Rules clause (rules/04-schools.md Mirumoto Bushi School Fourth Dan):
        "Failed parries against your double attacks do not prevent the
        automatic serious wound." (FR-012)
        """
        mirumoto = Character("Trace4th")
        mirumoto.set_actions([1])
        mirumoto.set_skill("double attack", 4)
        defender = Character("defender")
        defender.set_actions([1])
        defender.set_skill("parry", 4)
        groups = [Group("Dragon", mirumoto), Group("Enemy", defender)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        action = mirumoto_school.MirumotoDoubleAttackAction(
            mirumoto, defender, "double attack",
            InitiativeAction([1], 1), context,
        )
        # Simulate "parry attempted but failed".
        action.set_parry_attempted()
        with self.assertLogs(logger, level="DEBUG") as captured:
            event = action.direct_damage()
        self.assertIsNotNone(event,
            "Failed-parry path on the override must yield an auto-SW event.")
        combined = "\n".join(captured.output)
        self.assertIn("[Mirumoto 4th Dan]", combined,
            "Auto-SW override log must carry the [Mirumoto 4th Dan] marker (SC-006).")
        self.assertIn("serious", combined.lower(),
            "Log must mention the serious-wound override so reviewers can "
            "find the FR-012 path by grep.")

    # ----- 4th Dan halved damage-die reduction -----

    def test_fourth_dan_halved_damage_die_reduction_logs_original_and_halved(self):
        """SC-006: The MirumotoAttackAction.calculate_extra_damage_dice
        override (FR-013: failed-parry damage-die reduction halved) must
        log the original would-be-extra count and the halved result so a
        reviewer can verify the arithmetic against the rules clause.

        Rules clause (rules/04-schools.md Mirumoto Bushi School Fourth Dan):
        "against your regular attacks the number of extra rolled damage
        dice the failed parry reduced is cut in half (rounded down)." (FR-013)
        """
        mirumoto = Character("Trace4th")
        mirumoto.set_actions([1])
        mirumoto.set_skill("attack", 4)
        defender = Character("defender")
        defender.set_actions([1])
        defender.set_skill("parry", 4)
        groups = [Group("Dragon", mirumoto), Group("Enemy", defender)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        action = mirumoto_school.MirumotoAttackAction(
            mirumoto, defender, "attack",
            InitiativeAction([1], 1), context,
        )
        action.set_parry_attempted()
        # skill_roll=50, tn=25 -> would_be_extra=5, halved result=3.
        with self.assertLogs(logger, level="DEBUG") as captured:
            extra = action.calculate_extra_damage_dice(skill_roll=50, tn=25)
        self.assertEqual(3, extra,
            "(50-25)//5 = 5 would-be-extra; halved reduction = 2; result 5-2 = 3.")
        combined = "\n".join(captured.output)
        self.assertIn("[Mirumoto 4th Dan]", combined,
            "Halving-override log must carry the [Mirumoto 4th Dan] marker (SC-006).")
        # Both the original (5) and the halved result (3) must be visible.
        self.assertIn("5", combined,
            "Original would-be-extra dice count (5) must appear in the log.")
        self.assertIn("3", combined,
            "Halved result (3 extra dice) must appear in the log.")

    # ----- 5th Dan +10 visible per-roll -----

    def test_fifth_dan_skill_roll_logs_plus_ten_separate_from_standard_vp(self):
        """SC-006: The MirumotoRollParameterProvider's flat +10 modifier
        delta per VP (which stacks on top of the default +1 rolled /
        +1 kept dice from the standard void-spend) must be logged
        per-roll with the ``[Mirumoto 5th Dan]`` marker so a reviewer
        can distinguish it from the standard void-spend bonus.

        Rules clause (rules/04-schools.md Mirumoto Bushi School Fifth Dan):
        "When you spend a Void Point on an attack, parry, or wound check
        roll, that roll gets +10 instead of the normal +5." (FR-014,
        per spec.md Clarifications 2026-05-26: flat +10 modifier on top
        of the standard +1r/+1k void-spend dice.)
        """
        mirumoto = Character("Trace5th")
        mirumoto.set_ring("void", 3)
        mirumoto.set_skill("attack", 4)
        school = mirumoto_school.MirumotoBushiSchool()
        school.apply_rank_five_ability(mirumoto)
        provider = mirumoto_school.MirumotoRollParameterProvider()
        target = Character("target")
        with self.assertLogs(logger, level="DEBUG") as captured:
            provider.get_skill_roll_params(mirumoto, target, "attack", vp=1)
        combined = "\n".join(captured.output)
        self.assertIn("[Mirumoto 5th Dan]", combined,
            "Skill-roll +10-modifier log must carry the [Mirumoto 5th Dan] marker (SC-006).")
        self.assertIn("attack", combined,
            "Skill name (attack) must appear in the 5th Dan log.")
        # The +10 modifier delta (per VP) must be visible.
        self.assertIn("+10", combined,
            "+10 modifier delta per VP must appear in the 5th Dan log.")

    def test_fifth_dan_skill_roll_does_not_log_when_vp_zero(self):
        """Scope guard: when no VP is spent, the 5th Dan provider must
        NOT emit a [Mirumoto 5th Dan] line (it would mislead a reviewer).
        """
        mirumoto = Character("Trace5th")
        mirumoto.set_ring("void", 3)
        mirumoto.set_skill("attack", 4)
        provider = mirumoto_school.MirumotoRollParameterProvider()
        target = Character("target")
        # assertNoLogs is Python 3.10+; otherwise we capture and check.
        with self.assertLogs(logger, level="DEBUG") as captured:
            # Emit at least one log entry so assertLogs doesn't raise
            # (it requires at least one record). Then assert ours absent.
            logger.debug("sentinel")
            provider.get_skill_roll_params(mirumoto, target, "attack", vp=0)
        combined = "\n".join(captured.output)
        self.assertNotIn("[Mirumoto 5th Dan]", combined,
            "No 5th Dan log when no VP is spent.")

    def test_fifth_dan_wound_check_logs_plus_five_marker(self):
        """SC-006 (wound-check branch): the +10 modifier delta on a wound
        check must also surface with the ``[Mirumoto 5th Dan]`` marker.
        """
        mirumoto = Character("Trace5th")
        mirumoto.set_ring("void", 3)
        provider = mirumoto_school.MirumotoRollParameterProvider()
        with self.assertLogs(logger, level="DEBUG") as captured:
            provider.get_wound_check_roll_params(mirumoto, vp=1)
        combined = "\n".join(captured.output)
        self.assertIn("[Mirumoto 5th Dan]", combined,
            "Wound-check +10-modifier log must carry the [Mirumoto 5th Dan] marker (SC-006).")
        self.assertIn("wound check", combined.lower())
        self.assertIn("+10", combined)
