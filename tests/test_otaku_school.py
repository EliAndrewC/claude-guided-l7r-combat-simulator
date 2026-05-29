#!/usr/bin/env python3

#
# test_otaku_school.py
#
# Unit tests for the Otaku Bushi School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools import otaku_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestOtakuBushiSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual(["iaijutsu", "lunge", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual("fire", school.school_ring())

    def test_school_knacks(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual(["double attack", "iaijutsu", "lunge"], school.school_knacks())

    def test_free_raise_skills(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual(["wound check"], school.free_raise_skills())

    def test_name(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertEqual("Otaku Bushi School", school.name())

    def test_ap_base_skill(self):
        school = otaku_school.OtakuBushiSchool()
        self.assertIsNone(school.ap_base_skill())


class TestOtakuSpecialAbility(unittest.TestCase):
    def test_interrupt_lunge_cost(self):
        otaku = Character("Otaku")
        school = otaku_school.OtakuBushiSchool()
        school.apply_special_ability(otaku)
        self.assertEqual(1, otaku.interrupt_cost("lunge", None))


class TestOtakuLightWoundsDamageListener(unittest.TestCase):
    def setUp(self):
        self.otaku = Character("Otaku")
        self.otaku.set_skill("attack", 4)
        self.target = Character("target")
        self.target.set_ring("fire", 3)
        self.target.set_actions([3, 6, 9])
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)

    def test_increase_target_action_dice(self):
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.otaku, self.target, 15)
        list(listener.handle(self.otaku, event, self.context))
        # increase = max(1, 6 - 3) = 3
        # target's actions: [3+3, 6+3, 9+3] = [6, 9, 10] (capped at 10)
        self.assertEqual([6, 9, 10], self.target.actions())

    def test_increase_min_1(self):
        self.target.set_ring("fire", 6)
        self.target.set_actions([5, 7])
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.otaku, self.target, 15)
        list(listener.handle(self.otaku, event, self.context))
        # increase = max(1, 6 - 6) = 1
        self.assertEqual([6, 8], self.target.actions())

    def test_observe_others_damage(self):
        """When another character deals damage, the Otaku observes the damage roll."""
        listener = otaku_school.OtakuLightWoundsDamageListener()
        # target attacks someone (not the Otaku), so event.subject != character (Otaku)
        event = events.LightWoundsDamageEvent(self.target, self.target, 20)
        list(listener.handle(self.otaku, event, self.context))
        # Otaku should have observed the damage roll
        avg = self.otaku.knowledge().average_damage_roll(self.target)
        self.assertEqual(20, avg)

    def test_otaku_is_target_takes_lw_and_wound_check(self):
        """When Otaku is the target, should take LW and trigger wound check."""
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        # need to initialize context for probability provider
        self.context.initialize()
        listener = otaku_school.OtakuLightWoundsDamageListener()
        # rig the wound check so the strategy can work
        roll_provider = CalvinistRollProvider()
        roll_provider.put_wound_check_roll(100)
        self.otaku.set_roll_provider(roll_provider)
        event = events.LightWoundsDamageEvent(self.target, self.otaku, 12)
        responses = list(listener.handle(self.otaku, event, self.context))
        # Otaku should have taken 12 LW
        self.assertEqual(12, self.otaku.lw())
        # Should have triggered wound check strategy (yielded wound check declared event)
        self.assertTrue(len(responses) >= 1)

    def test_otaku_is_target_zero_damage(self):
        """When Otaku is the target but damage is 0, no wound check should occur."""
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.target, self.otaku, 0)
        responses = list(listener.handle(self.otaku, event, self.context))
        # Otaku takes 0 LW
        self.assertEqual(0, self.otaku.lw())
        # No wound check for 0 damage
        self.assertEqual(0, len(responses))

    def test_only_next_X_action_dice_modified(self):
        """3rd Dan: only the NEXT X action dice are shifted (X = Otaku's attack skill).

        Per rules/04-schools.md Otaku 3rd Dan: "increase that character's
        next X action dice this turn by (6 - that character's Fire) min 1,
        where X is your attack skill". Fix for spec 014 Q2 BLOCKING.
        """
        self.otaku.set_skill("attack", 3)
        self.target.set_ring("fire", 4)
        self.target.set_actions([1, 2, 3, 4, 5])
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.otaku, self.target, 15)
        list(listener.handle(self.otaku, event, self.context))
        # increase = max(1, 6 - 4) = 2
        # Only the first 3 dice [1, 2, 3] are shifted to [3, 4, 5].
        # The remaining [4, 5] stay. After re-sort: [3, 4, 4, 5, 5].
        # The buggy (pre-fix) code would produce [3, 4, 5, 6, 7] (all 5 modified).
        self.assertEqual([3, 4, 4, 5, 5], self.target.actions())

    def test_attack_skill_exceeds_action_count(self):
        """3rd Dan: when attack skill > number of action dice, modify all dice.

        Edge case for Q2 fix — must not raise IndexError or skip dice.
        """
        self.otaku.set_skill("attack", 10)
        self.target.set_ring("fire", 4)
        self.target.set_actions([1, 2])
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.otaku, self.target, 15)
        list(listener.handle(self.otaku, event, self.context))
        # increase = max(1, 6 - 4) = 2 → [1+2, 2+2] = [3, 4]
        self.assertEqual([3, 4], self.target.actions())

    def test_empty_actions_list(self):
        """3rd Dan: empty target actions list is a no-op (no IndexError)."""
        self.otaku.set_skill("attack", 3)
        self.target.set_ring("fire", 4)
        self.target.set_actions([])
        listener = otaku_school.OtakuLightWoundsDamageListener()
        event = events.LightWoundsDamageEvent(self.otaku, self.target, 15)
        list(listener.handle(self.otaku, event, self.context))
        self.assertEqual([], self.target.actions())


class TestOtakuLungeAction(unittest.TestCase):
    def setUp(self):
        self.otaku = Character("Otaku")
        self.otaku.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_extra_damage_die_when_parried(self):
        action = otaku_school.OtakuLungeAction(
            self.otaku, self.target, "lunge", self.initiative_action, self.context,
        )
        action.set_skill_roll(30)
        action.set_parry_attempted()
        # Even when parried, Otaku gets +1 extra damage die
        self.assertEqual(1, action.calculate_extra_damage_dice())

    def test_normal_extra_damage_dice(self):
        action = otaku_school.OtakuLungeAction(
            self.otaku, self.target, "lunge", self.initiative_action, self.context,
        )
        action.set_skill_roll(35)
        # TN = 20 (parry 3 -> 5*(1+3)=20)
        # Normal: (35-20)//5 + 1 = 3 + 1 = 4
        self.assertEqual(4, action.calculate_extra_damage_dice())


class TestOtakuActionFactory(unittest.TestCase):
    def setUp(self):
        self.otaku = Character("Otaku")
        self.otaku.set_actions([1])
        self.target = Character("target")
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_get_lunge_action(self):
        factory = otaku_school.OtakuActionFactory()
        action = factory.get_attack_action(self.otaku, self.target, "lunge", self.initiative_action, self.context)
        self.assertTrue(isinstance(action, otaku_school.OtakuLungeAction))

    def test_get_attack_action_default(self):
        factory = otaku_school.OtakuActionFactory()
        action = factory.get_attack_action(self.otaku, self.target, "attack", self.initiative_action, self.context)
        # Should be default AttackAction, not OtakuLungeAction
        self.assertFalse(isinstance(action, otaku_school.OtakuLungeAction))


class TestOtakuFifthDanTakeAttackActionEvent(unittest.TestCase):
    """Test the Otaku 5th Dan ability: trade 10 rolled damage dice for 1 auto SW."""

    def setUp(self):
        from simulation.mechanics.roll_provider import CalvinistRollProvider

        self.otaku = Character("Otaku")
        self.otaku.set_ring("fire", 5)
        self.otaku.set_skill("attack", 5)
        self.target = Character("target")
        self.target.set_skill("parry", 1)
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)
        self.roll_provider = CalvinistRollProvider()
        self.otaku.set_roll_provider(self.roll_provider)

    def _make_attack_action(self, skill="attack"):
        from simulation.actions import AttackAction
        action = AttackAction(
            self.otaku, self.target, skill, self.initiative_action, self.context,
        )
        return action

    def test_roll_damage_trades_10_dice_for_auto_sw(self):
        """When rolled damage dice >= OTAKU_5TH_DAN_TRADE_THRESHOLD,
        trade 10 for 1 auto SW and roll with reduced dice. Per spec 014
        Q3 (strategic-choice fix), the threshold was raised from the
        rules-floor of 12 to 20 to prevent over-aggressive triggering.
        """
        action = self._make_attack_action()
        # Set a high skill roll to get many extra damage dice.
        # TN to hit = 5 * (1 + target.parry) = 5 * (1 + 1) = 10.
        # Extra damage dice = (skill_roll - tn) // 5 = (80 - 10) // 5 = 14.
        action.set_skill_roll(80)
        # Damage roll params: fire(5) + weapon.rolled(4) + extra(14) = 23 rolled,
        # 23 >= 20 (threshold), so we trade 10 for 1 auto SW, leaving 13
        # rolled — which normalize_roll_params caps at 10k(2+3) = 10k5.
        self.roll_provider.put_damage_roll(25)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        # Should yield SeriousWoundsDamageEvent first, then LightWoundsDamageEvent.
        self.assertEqual(2, len(result_events))
        self.assertIsInstance(result_events[0], events.SeriousWoundsDamageEvent)
        self.assertEqual(1, result_events[0].damage)
        self.assertEqual(self.otaku, result_events[0].subject)
        self.assertEqual(self.target, result_events[0].target)
        # Trace attribution tag (spec 014 T-C2) — SW event must surface
        # with 'Otaku 5th Dan dice trade' source attribution.
        self.assertTrue(getattr(result_events[0], "_from_otaku_5th_dan", False))
        self.assertIsInstance(result_events[1], events.LightWoundsDamageEvent)
        self.assertEqual(25, result_events[1].damage)
        # Verify damage was rolled with reduced dice. Raw 13 normalized
        # to 10k(2+3) — observed[0] is the rolled count after normalize.
        observed = self.roll_provider.pop_observed_params("damage")
        self.assertEqual(10, observed[0])
        self.assertEqual(5, observed[1])  # weapon kept (2) + 3 excess from cap

    def test_roll_damage_normal_when_not_enough_dice(self):
        """When rolled damage dice < OTAKU_5TH_DAN_TRADE_THRESHOLD,
        roll damage normally without trading.
        """
        action = self._make_attack_action()
        # TN to hit = 10
        # Extra damage dice = (15 - 10) // 5 = 1
        action.set_skill_roll(15)
        # Damage roll params: fire(5) + weapon.rolled(4) + extra(1) = 10 rolled
        # 10 < 20, so no trade.
        self.roll_provider.put_damage_roll(18)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        # Should yield only LightWoundsDamageEvent.
        self.assertEqual(1, len(result_events))
        self.assertIsInstance(result_events[0], events.LightWoundsDamageEvent)
        self.assertEqual(18, result_events[0].damage)

    def test_roll_damage_at_threshold_trades(self):
        """When raw_rolled == 20 (the strategic threshold), trading
        leaves 10 rolled — well above the rules min-2 floor."""
        action = self._make_attack_action()
        # Want raw_rolled = 20. fire(5) + weapon.rolled(4) + extra = 20 → extra = 11.
        # extra_damage_dice = (skill_roll - tn) // 5 → (65 - 10) // 5 = 11.
        action.set_skill_roll(65)
        self.roll_provider.put_damage_roll(20)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        self.assertEqual(2, len(result_events))
        self.assertIsInstance(result_events[0], events.SeriousWoundsDamageEvent)
        self.assertEqual(1, result_events[0].damage)
        self.assertIsInstance(result_events[1], events.LightWoundsDamageEvent)
        # Verify 10 rolled dice (20 - 10).
        observed = self.roll_provider.pop_observed_params("damage")
        self.assertEqual(10, observed[0])

    def test_roll_damage_below_threshold_does_not_trade(self):
        """When raw_rolled is below the strategic threshold (e.g., at
        the old rules-floor of 12), the trade does NOT fire — Q3 fix.
        Also test raw_rolled = 19 (one below new threshold of 20)."""
        action = self._make_attack_action()
        # TN to hit = 10
        # Extra damage dice = (25 - 10) // 5 = 3 → raw_rolled = 5+4+3 = 12.
        action.set_skill_roll(25)
        self.roll_provider.put_damage_roll(15)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        # No trade: would have fired pre-Q3-fix, must not now.
        self.assertEqual(1, len(result_events))
        self.assertIsInstance(result_events[0], events.LightWoundsDamageEvent)
        self.assertEqual(15, result_events[0].damage)

    def test_roll_damage_just_below_threshold_does_not_trade(self):
        """When raw_rolled == 19 (one below the strategic threshold of
        20), the trade does NOT fire."""
        action = self._make_attack_action()
        # Want raw_rolled = 19. fire(5) + weapon(4) + extra = 19 → extra = 10.
        # extra_damage_dice = (skill_roll - tn) // 5 → (60 - 10) // 5 = 10.
        action.set_skill_roll(60)
        self.roll_provider.put_damage_roll(22)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        # Just verify no SW: trade did not fire at raw_rolled=19. The
        # exact damage value is not load-bearing (normalize_roll_params
        # converts excess rolled→kept→bonus).
        self.assertEqual(1, len(result_events))
        self.assertIsInstance(result_events[0], events.LightWoundsDamageEvent)
        self.assertNotIsInstance(result_events[0], events.SeriousWoundsDamageEvent)

    def test_roll_damage_action_tagged_when_traded(self):
        """The action MUST be tagged with _otaku_5th_dan_traded when
        the trade fires, so the damage-breakdown formatter can attribute
        the rolled-dice reduction to the 5th Dan trade (spec 014 T-C2).
        """
        action = self._make_attack_action()
        action.set_skill_roll(80)  # raw_rolled = 23, above threshold.
        self.roll_provider.put_damage_roll(25)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        list(take_event._roll_damage())
        self.assertTrue(getattr(action, "_otaku_5th_dan_traded", False))

    def test_roll_damage_action_not_tagged_when_not_traded(self):
        """No trade → no tag on the action."""
        action = self._make_attack_action()
        action.set_skill_roll(15)  # raw_rolled = 10, below threshold.
        self.roll_provider.put_damage_roll(18)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        list(take_event._roll_damage())
        self.assertFalse(getattr(action, "_otaku_5th_dan_traded", False))


class TestOtakuFifthDanTakeAttackActionEventPlay(unittest.TestCase):
    """Test the full play() method of OtakuFifthDanTakeAttackActionEvent."""

    def setUp(self):
        from simulation.mechanics.roll_provider import CalvinistRollProvider

        self.otaku = Character("Otaku")
        self.otaku.set_ring("fire", 5)
        self.otaku.set_skill("attack", 5)
        self.otaku.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 1)
        self.target.set_actions([2])
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        self.initiative_action = InitiativeAction([1], 1)
        self.roll_provider = CalvinistRollProvider()
        self.otaku.set_roll_provider(self.roll_provider)

    def _make_attack_action(self, skill="attack"):
        from simulation.actions import AttackAction
        return AttackAction(
            self.otaku, self.target, skill, self.initiative_action, self.context,
        )

    def test_play_hit_with_trade(self):
        """Full play() flow: hit with enough dice to trigger the 5th Dan trade.
        Skill roll 80 → 14 extra dice → raw_rolled = 5+4+14 = 23 ≥ 22 threshold.
        """
        action = self._make_attack_action()
        # rig skill roll to hit (TN=10) with many extra damage dice; need
        # raw_rolled >= 22 to trigger the strategic-threshold trade (spec 014 Q3).
        self.roll_provider.put_skill_roll("attack", 80)
        self.roll_provider.put_damage_roll(25)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event.play(self.context))
        # Should include: AttackDeclaredEvent, AttackRolledEvent, AttackSucceededEvent,
        #                 SeriousWoundsDamageEvent, LightWoundsDamageEvent
        event_types = [type(e).__name__ for e in result_events]
        self.assertIn("AttackDeclaredEvent", event_types)
        self.assertIn("AttackSucceededEvent", event_types)
        self.assertIn("SeriousWoundsDamageEvent", event_types)
        self.assertIn("LightWoundsDamageEvent", event_types)

    def test_play_hit_normal_damage(self):
        """Full play() flow: hit but not enough dice for trade."""
        action = self._make_attack_action()
        # rig skill roll just barely above TN
        self.roll_provider.put_skill_roll("attack", 15)
        self.roll_provider.put_damage_roll(12)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event.play(self.context))
        event_types = [type(e).__name__ for e in result_events]
        self.assertIn("AttackDeclaredEvent", event_types)
        self.assertIn("AttackSucceededEvent", event_types)
        self.assertIn("LightWoundsDamageEvent", event_types)
        # Should NOT have auto SW
        self.assertNotIn("SeriousWoundsDamageEvent", event_types)

    def test_play_miss(self):
        """Full play() flow: miss should yield AttackFailedEvent."""
        action = self._make_attack_action()
        # rig skill roll to miss (TN=10)
        self.roll_provider.put_skill_roll("attack", 1)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event.play(self.context))
        event_types = [type(e).__name__ for e in result_events]
        self.assertIn("AttackDeclaredEvent", event_types)
        self.assertIn("AttackFailedEvent", event_types)
        self.assertNotIn("AttackSucceededEvent", event_types)

    def test_play_attack_parried_yields_failed_and_returns(self):
        """When the action is parried (set via set_parried before
        play() consults the parried() check), play() MUST yield
        AttackFailedEvent and return without rolling damage.
        Coverage for OtakuFifthDanTakeAttackActionEvent.play parried
        branch (spec 014 T-E1)."""
        action = self._make_attack_action()
        self.roll_provider.put_skill_roll("attack", 30)
        # Directly mark the action as parried so the play() parried
        # check fires after the attack-roll step.
        action.set_parried()
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event.play(self.context))
        event_types = [type(e).__name__ for e in result_events]
        self.assertIn("AttackDeclaredEvent", event_types)
        # Parried → AttackFailedEvent emitted; no SW, no LW damage.
        self.assertIn("AttackFailedEvent", event_types)
        self.assertNotIn("AttackSucceededEvent", event_types)
        self.assertNotIn("SeriousWoundsDamageEvent", event_types)
        self.assertNotIn("LightWoundsDamageEvent", event_types)

    def test_play_subject_not_fighting(self):
        """If subject is defeated before roll, play() should return early."""
        action = self._make_attack_action()
        self.roll_provider.put_skill_roll("attack", 60)
        # defeat the Otaku before playing
        self.otaku.take_sw(self.otaku.max_sw())
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event.play(self.context))
        # Should only yield the declare event then stop
        event_types = [type(e).__name__ for e in result_events]
        self.assertIn("AttackDeclaredEvent", event_types)
        self.assertNotIn("AttackRolledEvent", event_types)
        self.assertNotIn("AttackSucceededEvent", event_types)


class TestOtakuFifthDanTakeActionEventFactory(unittest.TestCase):
    """Test the Otaku 5th Dan TakeActionEventFactory."""

    def setUp(self):
        self.otaku = Character("Otaku")
        self.otaku.set_actions([1])
        self.target = Character("target")
        groups = [Group("Unicorn", self.otaku), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_returns_fifth_dan_event(self):
        from simulation.actions import AttackAction
        factory = otaku_school.OtakuFifthDanTakeActionEventFactory()
        action = AttackAction(
            self.otaku, self.target, "attack", self.initiative_action, self.context,
        )
        event = factory.get_take_attack_action_event(action)
        self.assertIsInstance(event, otaku_school.OtakuFifthDanTakeAttackActionEvent)

    def test_rejects_non_attack_action(self):
        factory = otaku_school.OtakuFifthDanTakeActionEventFactory()
        with self.assertRaises(ValueError):
            factory.get_take_attack_action_event("not an action")


class TestOtakuApplyRankFiveAbility(unittest.TestCase):
    """Test that apply_rank_five_ability installs the 5th Dan factory."""

    def test_sets_take_action_event_factory(self):
        otaku = Character("Otaku")
        school = otaku_school.OtakuBushiSchool()
        school.apply_rank_five_ability(otaku)
        self.assertIsInstance(
            otaku.take_action_event_factory(),
            otaku_school.OtakuFifthDanTakeActionEventFactory,
        )
