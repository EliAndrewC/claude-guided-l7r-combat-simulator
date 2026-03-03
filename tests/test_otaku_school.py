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
        """When rolled damage dice >= 12, trade 10 for 1 auto SW and roll with reduced dice."""
        action = self._make_attack_action()
        # Set a high skill roll to get many extra damage dice
        # TN to hit = 5 * (1 + target.parry) = 5 * (1 + 1) = 10
        # Extra damage dice = (skill_roll - tn) // 5 = (60 - 10) // 5 = 10
        action.set_skill_roll(60)
        # Damage roll params: fire(5) + weapon.rolled(4) + extra(10) = 19 rolled
        # 19 >= 12, so we trade 10 for 1 auto SW, leaving 9 rolled
        self.roll_provider.put_damage_roll(25)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        # Should yield SeriousWoundsDamageEvent first, then LightWoundsDamageEvent
        self.assertEqual(2, len(result_events))
        self.assertIsInstance(result_events[0], events.SeriousWoundsDamageEvent)
        self.assertEqual(1, result_events[0].damage)
        self.assertEqual(self.otaku, result_events[0].subject)
        self.assertEqual(self.target, result_events[0].target)
        self.assertIsInstance(result_events[1], events.LightWoundsDamageEvent)
        self.assertEqual(25, result_events[1].damage)
        # Verify damage was rolled with reduced dice (19 - 10 = 9 rolled)
        observed = self.roll_provider.pop_observed_params("damage")
        self.assertEqual(9, observed[0])

    def test_roll_damage_normal_when_not_enough_dice(self):
        """When rolled damage dice < 12, roll damage normally without trading."""
        action = self._make_attack_action()
        # TN to hit = 10
        # Extra damage dice = (15 - 10) // 5 = 1
        action.set_skill_roll(15)
        # Damage roll params: fire(5) + weapon.rolled(4) + extra(1) = 10 rolled
        # 10 < 12, so no trade
        self.roll_provider.put_damage_roll(18)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        # Should yield only LightWoundsDamageEvent
        self.assertEqual(1, len(result_events))
        self.assertIsInstance(result_events[0], events.LightWoundsDamageEvent)
        self.assertEqual(18, result_events[0].damage)

    def test_roll_damage_exactly_12_rolled_trades(self):
        """When rolled damage dice == 12 exactly, trading leaves 2 (the minimum)."""
        action = self._make_attack_action()
        # TN to hit = 10
        # Extra damage dice = (25 - 10) // 5 = 3
        action.set_skill_roll(25)
        # Damage roll params: fire(5) + weapon.rolled(4) + extra(3) = 12 rolled
        # 12 >= 12, so we trade 10, leaving 2 rolled
        self.roll_provider.put_damage_roll(10)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        self.assertEqual(2, len(result_events))
        self.assertIsInstance(result_events[0], events.SeriousWoundsDamageEvent)
        self.assertEqual(1, result_events[0].damage)
        self.assertIsInstance(result_events[1], events.LightWoundsDamageEvent)
        # Verify 2 rolled dice (the minimum after trading 10)
        observed = self.roll_provider.pop_observed_params("damage")
        self.assertEqual(2, observed[0])

    def test_roll_damage_11_rolled_does_not_trade(self):
        """When rolled damage dice == 11, do not trade (would leave only 1, below minimum 2)."""
        action = self._make_attack_action()
        # TN to hit = 10
        # Extra damage dice = (20 - 10) // 5 = 2
        action.set_skill_roll(20)
        # Damage roll params: fire(5) + weapon.rolled(4) + extra(2) = 11 rolled
        # 11 < 12, so no trade
        self.roll_provider.put_damage_roll(15)
        take_event = otaku_school.OtakuFifthDanTakeAttackActionEvent(action)
        result_events = list(take_event._roll_damage())
        self.assertEqual(1, len(result_events))
        self.assertIsInstance(result_events[0], events.LightWoundsDamageEvent)
        self.assertEqual(15, result_events[0].damage)


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
        """Full play() flow: hit with enough dice to trigger the 5th Dan trade."""
        action = self._make_attack_action()
        # rig skill roll to hit (TN=10) with many extra damage dice
        self.roll_provider.put_skill_roll("attack", 60)
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
