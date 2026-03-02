#!/usr/bin/env python3

#
# test_doji_artisan_school.py
#
# Unit tests for the Doji Artisan School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import doji_artisan_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestDojiArtisanSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual("Doji Artisan School", school.name())

    def test_extra_rolled(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["counterattack", "manipulation", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["counterattack", "oppose social", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["manipulation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual("culture", school.ap_base_skill())

    def test_ap_skills(self):
        school = doji_artisan_school.DojiArtisanSchool()
        self.assertEqual(["bragging", "culture", "heraldry", "manipulation", "counterattack", "wound check"], school.ap_skills())


class TestDojiArtisanSpecialAbility(unittest.TestCase):
    def test_counterattack_interrupt_cost(self):
        doji = Character("Doji")
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(doji)
        # Counterattack interrupt cost should be 1 (instead of default 2)
        target = Character("Target")
        groups = [Group("Doji", doji), Group("Target", target)]
        context = EngineContext(groups)
        self.assertEqual(1, doji.interrupt_cost("counterattack", context))

    def test_default_interrupt_cost_unchanged(self):
        doji = Character("Doji")
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(doji)
        target = Character("Target")
        groups = [Group("Doji", doji), Group("Target", target)]
        context = EngineContext(groups)
        # Non-counterattack skills should still have default interrupt cost (2)
        self.assertEqual(2, doji.interrupt_cost("parry", context))


class TestDojiArtisanAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        doji = Character("Doji")
        doji.set_skill("culture", 5)
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_three_ability(doji)
        self.assertEqual("culture", doji.ap_base_skill())
        self.assertTrue(doji.can_spend_ap("counterattack"))
        self.assertTrue(doji.can_spend_ap("wound check"))
        self.assertFalse(doji.can_spend_ap("attack"))
        # AP = 2 * culture skill = 10
        self.assertEqual(10, doji.ap())


# ── Special Ability: VP counterattack interrupt with attacker's roll bonus ──


class TestDojiArtisanCounterattackInterruptStrategy(unittest.TestCase):
    """Test that the Doji Artisan counterattack interrupt triggers on
    AttackRolledEvent (after seeing the roll) rather than AttackDeclaredEvent,
    spends 1 VP, and requires VP > 0."""

    def setUp(self):
        self.doji = Character("Doji")
        self.doji.set_skill("counterattack", 3)
        self.doji.set_skill("parry", 3)
        self.doji.set_actions([3, 7])
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 2)
        self.attacker.set_actions([1])
        groups = [
            Group("Crane", self.doji),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(self.doji)
        self.initiative_action = InitiativeAction([1], 1)

    def test_does_not_counterattack_on_attack_declared(self):
        """Doji Artisan should NOT counterattack on AttackDeclaredEvent
        because they need to see the attacker's roll first."""
        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            self.initiative_action, self.context,
        )
        event = events.AttackDeclaredEvent(attack)
        results = list(self.doji.interrupt_strategy().recommend(
            self.doji, event, self.context,
        ))
        # No counterattack events should be produced
        counterattack_events = [
            e for e in results
            if isinstance(e, events.TakeCounterattackActionEvent)
        ]
        self.assertEqual(0, len(counterattack_events))

    def test_counterattacks_on_attack_rolled(self):
        """Doji Artisan should counterattack on AttackRolledEvent."""
        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            self.initiative_action, self.context,
        )
        attack.set_skill_roll(25)
        event = events.AttackRolledEvent(attack, 25)
        results = list(self.doji.interrupt_strategy().recommend(
            self.doji, event, self.context,
        ))
        # Should produce a SpendActionEvent and a TakeCounterattackActionEvent
        counterattack_events = [
            e for e in results
            if isinstance(e, events.TakeCounterattackActionEvent)
        ]
        self.assertEqual(1, len(counterattack_events))

    def test_no_counterattack_without_vp(self):
        """Doji Artisan cannot counterattack as interrupt without VP."""
        # Drain all VP
        self.doji._vp_spent = self.doji.max_vp()
        self.doji._tvp = 0
        self.assertEqual(0, self.doji.vp())

        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            self.initiative_action, self.context,
        )
        attack.set_skill_roll(25)
        event = events.AttackRolledEvent(attack, 25)
        results = list(self.doji.interrupt_strategy().recommend(
            self.doji, event, self.context,
        ))
        # Should fall through to parry, not counterattack
        counterattack_events = [
            e for e in results
            if isinstance(e, events.TakeCounterattackActionEvent)
        ]
        self.assertEqual(0, len(counterattack_events))

    def test_counterattack_action_has_vp_1(self):
        """The counterattack action should be created with vp=1."""
        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            self.initiative_action, self.context,
        )
        attack.set_skill_roll(25)
        event = events.AttackRolledEvent(attack, 25)
        results = list(self.doji.interrupt_strategy().recommend(
            self.doji, event, self.context,
        ))
        counterattack_events = [
            e for e in results
            if isinstance(e, events.TakeCounterattackActionEvent)
        ]
        self.assertEqual(1, len(counterattack_events))
        self.assertEqual(1, counterattack_events[0].action.vp())


class TestDojiArtisanTakeCounterattackActionEvent(unittest.TestCase):
    """Test the Doji Artisan-specific counterattack event that applies
    the attacker's roll // 5 as a bonus to the counterattack skill roll."""

    def setUp(self):
        self.doji = Character("Doji")
        self.doji.set_skill("counterattack", 3)
        self.doji.set_actions([5, 8])
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 2)
        self.attacker.set_actions([1])
        groups = [Group("Crane", self.doji), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(self.doji)
        # original attack
        self.attack_initiative = InitiativeAction([1], 1)
        self.attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            self.attack_initiative, self.context,
        )

    def test_attacker_roll_bonus_applied(self):
        """Counterattack skill roll should include attacker's roll // 5 as bonus."""
        self.attack.set_skill_roll(30)
        # attacker's roll = 30, bonus = 30 // 5 = 6
        interrupt_action = InitiativeAction([8], 1, is_interrupt=True)
        counterattack = self.doji.action_factory().get_counterattack_action(
            self.doji, self.attacker, self.attack,
            "counterattack", interrupt_action, self.context, vp=1,
        )
        counterattack._attacker_roll_bonus = 6  # 30 // 5

        # rig rolls: base counterattack roll = 20, plus bonus 6 = 26
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 20)
        roll_provider.put_damage_roll(15)
        self.doji.set_roll_provider(roll_provider)
        # rig attacker wound check
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = self.doji.take_action_event_factory().get_take_counterattack_action_event(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # The counterattack roll should have been boosted by the attacker's roll bonus
        self.assertEqual(26, counterattack.skill_roll())

    def test_attacker_roll_bonus_calculation(self):
        """Test that bonus = attacker_roll // 5 for various roll values."""
        # attacker roll 25 -> bonus 5
        self.attack.set_skill_roll(25)
        interrupt_action = InitiativeAction([8], 1, is_interrupt=True)
        counterattack = self.doji.action_factory().get_counterattack_action(
            self.doji, self.attacker, self.attack,
            "counterattack", interrupt_action, self.context, vp=1,
        )
        counterattack._attacker_roll_bonus = 25 // 5  # = 5

        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 10)
        roll_provider.put_damage_roll(10)
        self.doji.set_roll_provider(roll_provider)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = self.doji.take_action_event_factory().get_take_counterattack_action_event(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # base roll 10 + bonus 5 = 15
        self.assertEqual(15, counterattack.skill_roll())

    def test_vp_spent_on_counterattack(self):
        """VP should be spent when counterattacking."""
        self.attack.set_skill_roll(25)
        interrupt_action = InitiativeAction([8], 1, is_interrupt=True)
        counterattack = self.doji.action_factory().get_counterattack_action(
            self.doji, self.attacker, self.attack,
            "counterattack", interrupt_action, self.context, vp=1,
        )
        counterattack._attacker_roll_bonus = 5

        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.doji.set_roll_provider(roll_provider)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        initial_vp = self.doji.vp()
        take_event = self.doji.take_action_event_factory().get_take_counterattack_action_event(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # VP should have been spent
        history = engine.history()
        spend_vp_events = [e for e in history if isinstance(e, events.SpendVoidPointsEvent)]
        self.assertEqual(1, len(spend_vp_events))
        self.assertEqual(1, spend_vp_events[0].amount)
        self.assertEqual(initial_vp - 1, self.doji.vp())

    def test_counterattack_miss_no_damage(self):
        """A missed counterattack deals no damage."""
        self.attack.set_skill_roll(25)
        interrupt_action = InitiativeAction([8], 1, is_interrupt=True)
        counterattack = self.doji.action_factory().get_counterattack_action(
            self.doji, self.attacker, self.attack,
            "counterattack", interrupt_action, self.context, vp=1,
        )
        counterattack._attacker_roll_bonus = 5

        # rig rolls: miss (roll 5 + bonus 5 = 10 < tn 15)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 3)
        self.doji.set_roll_provider(roll_provider)

        take_event = self.doji.take_action_event_factory().get_take_counterattack_action_event(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        self.assertEqual(0, self.attacker.lw())

    def test_event_history_for_successful_counterattack(self):
        """Verify correct event sequence for a successful Doji Artisan counterattack."""
        self.attack.set_skill_roll(25)
        interrupt_action = InitiativeAction([8], 1, is_interrupt=True)
        counterattack = self.doji.action_factory().get_counterattack_action(
            self.doji, self.attacker, self.attack,
            "counterattack", interrupt_action, self.context, vp=1,
        )
        counterattack._attacker_roll_bonus = 5

        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.doji.set_roll_provider(roll_provider)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = self.doji.take_action_event_factory().get_take_counterattack_action_event(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        self.assertIsInstance(history[0], doji_artisan_school.DojiArtisanTakeCounterattackActionEvent)
        self.assertIsInstance(history[1], events.CounterattackDeclaredEvent)
        # VP should be spent before the rolled event
        self.assertIsInstance(history[2], events.SpendVoidPointsEvent)
        self.assertIsInstance(history[3], events.CounterattackRolledEvent)
        self.assertIsInstance(history[4], events.CounterattackSucceededEvent)
        self.assertIsInstance(history[5], events.LightWoundsDamageEvent)


class TestDojiArtisanFullCombatCounterattack(unittest.TestCase):
    """Integration test: Doji Artisan counterattacks during a full attack sequence."""

    def setUp(self):
        self.doji = Character("Doji")
        self.doji.set_skill("counterattack", 3)
        self.doji.set_skill("parry", 3)
        self.doji.set_actions([3, 7])
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 2)
        self.attacker.set_actions([1])
        groups = [Group("Crane", self.doji), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(self.doji)

    def test_counterattack_in_full_attack_sequence(self):
        """When an attacker attacks the Doji, the counterattack should happen
        after the attack roll, with the attacker's roll bonus applied."""
        # Rig the attacker's attack roll
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 25)  # attack roll
        attacker_rp.put_damage_roll(15)  # damage if attack hits
        attacker_rp.put_wound_check_roll(50)  # wound check from counterattack damage
        self.attacker.set_roll_provider(attacker_rp)

        # Rig the Doji's counterattack roll
        doji_rp = CalvinistRollProvider()
        doji_rp.put_skill_roll("counterattack", 20)  # base counterattack roll
        doji_rp.put_damage_roll(10)  # counterattack damage
        doji_rp.put_wound_check_roll(50)  # wound check if needed
        self.doji.set_roll_provider(doji_rp)

        # Create the attack action
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            initiative_action, self.context,
        )

        # Run the attack through the engine
        take_attack = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_attack)

        # The counterattack should have happened
        history = engine.history()
        counterattack_declared = [
            e for e in history
            if isinstance(e, events.CounterattackDeclaredEvent)
        ]
        self.assertEqual(1, len(counterattack_declared))

        # The counterattack roll should include the bonus from the attacker's roll
        # attacker roll = 25, bonus = 25 // 5 = 5
        # base counterattack roll = 20, final = 20 + 5 = 25
        counterattack_rolled = [
            e for e in history
            if isinstance(e, events.CounterattackRolledEvent)
        ]
        self.assertEqual(1, len(counterattack_rolled))
        self.assertEqual(25, counterattack_rolled[0].roll)


# ── 4th Dan: Phase bonus vs targets who haven't attacked you ──


class TestDojiArtisanFourthDanTracker(unittest.TestCase):
    """Test the tracker that records who attacked the artisan each round."""

    def test_tracker_records_attacker(self):
        tracker = doji_artisan_school.DojiArtisanAttackTracker()
        attacker = Character("Attacker")
        tracker.record_attacker(attacker)
        self.assertTrue(tracker.has_attacked(attacker))

    def test_tracker_unknown_attacker(self):
        tracker = doji_artisan_school.DojiArtisanAttackTracker()
        attacker = Character("Attacker")
        self.assertFalse(tracker.has_attacked(attacker))

    def test_tracker_reset(self):
        tracker = doji_artisan_school.DojiArtisanAttackTracker()
        attacker = Character("Attacker")
        tracker.record_attacker(attacker)
        tracker.reset()
        self.assertFalse(tracker.has_attacked(attacker))


class TestDojiArtisanFourthDanListener(unittest.TestCase):
    """Test that the 4th Dan listener tracks attacks against the artisan
    and resets each round."""

    def setUp(self):
        self.doji = Character("Doji")
        self.doji.set_skill("counterattack", 3)
        self.doji.set_skill("attack", 3)
        self.doji.set_skill("parry", 3)
        self.doji.set_actions([3, 7])
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 2)
        self.attacker.set_actions([1])
        self.attacker2 = Character("Attacker2")
        self.attacker2.set_skill("parry", 2)
        self.attacker2.set_actions([2])
        groups = [
            Group("Crane", self.doji),
            Group("Enemy", [self.attacker, self.attacker2]),
        ]
        self.context = EngineContext(groups, round=1, phase=3)
        self.context.initialize()
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(self.doji)
        school.apply_rank_four_ability(self.doji)

    def test_tracks_attacker_targeting_doji(self):
        """When someone attacks the Doji, the tracker records them."""
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            initiative_action, self.context,
        )
        event = events.AttackDeclaredEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(event)

        # The tracker should record this attacker
        tracker = self.doji._doji_artisan_attack_tracker
        self.assertTrue(tracker.has_attacked(self.attacker))
        self.assertFalse(tracker.has_attacked(self.attacker2))

    def test_tracker_resets_on_new_round(self):
        """The tracker should reset at the start of each new round."""
        # First, record an attacker
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            initiative_action, self.context,
        )
        event = events.AttackDeclaredEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(event)

        tracker = self.doji._doji_artisan_attack_tracker
        self.assertTrue(tracker.has_attacked(self.attacker))

        # Rig initiative rolls for new round
        doji_rp = CalvinistRollProvider()
        doji_rp.put_initiative_roll([3, 7])
        self.doji.set_roll_provider(doji_rp)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_initiative_roll([1])
        self.attacker.set_roll_provider(attacker_rp)
        attacker2_rp = CalvinistRollProvider()
        attacker2_rp.put_initiative_roll([2])
        self.attacker2.set_roll_provider(attacker2_rp)

        # Trigger new round
        new_round_event = events.NewRoundEvent(2)
        engine.event(new_round_event)

        # Tracker should be reset
        self.assertFalse(tracker.has_attacked(self.attacker))


class TestDojiArtisanFourthDanPhaseBonus(unittest.TestCase):
    """Test the 4th Dan phase bonus when attacking a target who hasn't
    attacked the artisan this round."""

    def setUp(self):
        self.doji = Character("Doji")
        self.doji.set_skill("counterattack", 3)
        self.doji.set_skill("attack", 3)
        self.doji.set_skill("parry", 3)
        self.doji.set_actions([3, 7])
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 2)
        self.attacker.set_actions([1])
        self.attacker2 = Character("Attacker2")
        self.attacker2.set_skill("parry", 2)
        self.attacker2.set_actions([2])
        groups = [
            Group("Crane", self.doji),
            Group("Enemy", [self.attacker, self.attacker2]),
        ]
        self.context = EngineContext(groups, round=1, phase=5)
        self.context.initialize()
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_special_ability(self.doji)
        school.apply_rank_four_ability(self.doji)

    def test_phase_bonus_against_non_attacker(self):
        """When attacking a target who has NOT attacked the Doji this round,
        the Doji gets a bonus equal to the current phase."""
        # attacker2 has NOT attacked the Doji
        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.doji, self.attacker2, "attack",
            initiative_action, self.context,
        )

        # Rig the roll
        doji_rp = CalvinistRollProvider()
        doji_rp.put_skill_roll("attack", 20)  # base roll
        doji_rp.put_damage_roll(10)
        self.doji.set_roll_provider(doji_rp)
        attacker2_rp = CalvinistRollProvider()
        attacker2_rp.put_wound_check_roll(50)
        self.attacker2.set_roll_provider(attacker2_rp)

        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Attack roll should have the phase bonus applied
        # base roll = 20, phase bonus = 5, final roll = 25
        attack_rolled_events = [
            e for e in engine.history()
            if isinstance(e, events.AttackRolledEvent)
        ]
        self.assertEqual(1, len(attack_rolled_events))
        self.assertEqual(25, attack_rolled_events[0].roll)

    def test_no_phase_bonus_against_attacker(self):
        """When attacking a target who HAS attacked the Doji this round,
        no phase bonus is applied."""
        # First, have the attacker attack the Doji (just declare, to register)
        atk_initiative = InitiativeAction([1], 1)
        atk = actions.AttackAction(
            self.attacker, self.doji, "attack",
            atk_initiative, self.context,
        )
        declare_event = events.AttackDeclaredEvent(atk)
        engine = CombatEngine(self.context)
        engine.event(declare_event)

        # Now the Doji attacks the attacker
        doji_initiative = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.doji, self.attacker, "attack",
            doji_initiative, self.context,
        )
        doji_rp = CalvinistRollProvider()
        doji_rp.put_skill_roll("attack", 20)
        doji_rp.put_damage_roll(10)
        self.doji.set_roll_provider(doji_rp)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = events.TakeAttackActionEvent(attack)
        engine.event(take_event)

        # Attack roll should NOT have the phase bonus
        attack_rolled_events = [
            e for e in engine.history()
            if isinstance(e, events.AttackRolledEvent)
            and e.action.subject() == self.doji
        ]
        self.assertEqual(1, len(attack_rolled_events))
        self.assertEqual(20, attack_rolled_events[0].roll)

    def test_phase_bonus_scales_with_phase(self):
        """Phase bonus should equal the current phase number."""
        # Set phase to 8
        while self.context.phase() < 8:
            self.context.next_phase()

        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.doji, self.attacker2, "attack",
            initiative_action, self.context,
        )
        doji_rp = CalvinistRollProvider()
        doji_rp.put_skill_roll("attack", 20)
        doji_rp.put_damage_roll(10)
        self.doji.set_roll_provider(doji_rp)
        attacker2_rp = CalvinistRollProvider()
        attacker2_rp.put_wound_check_roll(50)
        self.attacker2.set_roll_provider(attacker2_rp)

        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # base 20 + phase 8 = 28
        attack_rolled_events = [
            e for e in engine.history()
            if isinstance(e, events.AttackRolledEvent)
        ]
        self.assertEqual(1, len(attack_rolled_events))
        self.assertEqual(28, attack_rolled_events[0].roll)

    def test_phase_bonus_does_not_apply_to_non_doji_attacks(self):
        """The phase bonus should only apply when the Doji attacks,
        not when the attacker attacks."""
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.attacker, self.doji, "attack",
            initiative_action, self.context,
        )

        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 20)
        attacker_rp.put_damage_roll(10)
        self.attacker.set_roll_provider(attacker_rp)
        doji_rp = CalvinistRollProvider()
        doji_rp.put_wound_check_roll(50)
        # Also need counterattack roll since Doji has interrupt strategy
        doji_rp.put_skill_roll("counterattack", 5)  # miss the counterattack
        self.doji.set_roll_provider(doji_rp)

        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # The attacker's roll should be unmodified
        attack_rolled_events = [
            e for e in engine.history()
            if isinstance(e, events.AttackRolledEvent)
            and e.action.subject() == self.attacker
        ]
        self.assertEqual(1, len(attack_rolled_events))
        self.assertEqual(20, attack_rolled_events[0].roll)


# ── 5th Dan: TN/contested roll bonus ──


class TestDojiArtisanFifthDan(unittest.TestCase):
    def test_tn_bonus_on_attack(self):
        doji = Character("Doji")
        target = Character("Target")
        target.set_skill("parry", 3)
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(doji, target, "attack")
        # Target TN to hit = 5*(1+3) = 20; bonus = (20-10)//5 = 2
        self.assertEqual(2, modifier)

    def test_no_bonus_on_low_tn(self):
        doji = Character("Doji")
        target = Character("Target")
        # Default parry=0, TN to hit = 5*(1+0) = 5
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(doji, target, "attack")
        # TN=5, (5-10)//5 = -1, max(0, -1) = 0
        self.assertEqual(0, modifier)

    def test_wound_check_bonus(self):
        doji = Character("Doji")
        doji._lw = 25
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_wound_check_roll_params(doji)
        # LW=25, bonus = (25-10)//5 = 3
        self.assertEqual(3, modifier)

    def test_wound_check_bonus_zero_lw(self):
        doji = Character("Doji")
        school = doji_artisan_school.DojiArtisanSchool()
        school.apply_rank_five_ability(doji)
        provider = doji.roll_parameter_provider()
        _, _, modifier = provider.get_wound_check_roll_params(doji)
        # LW=0, (0-10)//5 = -2, max(0, -2) = 0
        self.assertEqual(0, modifier)
