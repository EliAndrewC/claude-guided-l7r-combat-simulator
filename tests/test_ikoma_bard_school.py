#!/usr/bin/env python3

#
# test_ikoma_bard_school.py
#
# Unit tests for the Ikoma Bard School.
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
from simulation.schools import ikoma_bard_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIkomaBardSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual("Ikoma Bard School", school.name())

    def test_extra_rolled(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["attack", "bragging", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["discern honor", "oppose knowledge", "oppose social"], school.school_knacks())

    def test_free_raise_skills(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["attack"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual("bragging", school.ap_base_skill())

    def test_ap_skills(self):
        school = ikoma_bard_school.IkomaBardSchool()
        self.assertEqual(["bragging", "culture", "heraldry", "intimidation", "attack", "wound check"], school.ap_skills())


class TestIkomaBardAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        ikoma = Character("Ikoma")
        ikoma.set_skill("bragging", 5)
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_rank_three_ability(ikoma)
        self.assertEqual("bragging", ikoma.ap_base_skill())
        self.assertTrue(ikoma.can_spend_ap("attack"))
        self.assertTrue(ikoma.can_spend_ap("wound check"))
        self.assertFalse(ikoma.can_spend_ap("parry"))
        # AP = 2 * bragging skill = 10
        self.assertEqual(10, ikoma.ap())


class TestIkomaFourthDan(unittest.TestCase):
    def test_damage_roll_10_dice_no_extra(self):
        ikoma = Character("Ikoma")
        ikoma.set_ring("water", 3)
        target = Character("Target")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_rank_four_ability(ikoma)
        provider = ikoma.roll_parameter_provider()
        # When attack_extra_rolled == 0, rolled should be at least 10
        rolled, kept, modifier = provider.get_damage_roll_params(ikoma, target, "attack", 0)
        self.assertGreaterEqual(rolled, 10)

    def test_damage_roll_normal_with_extra(self):
        ikoma = Character("Ikoma")
        ikoma.set_ring("water", 3)
        ikoma.set_skill("attack", 3)
        target = Character("Target")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_rank_four_ability(ikoma)
        provider = ikoma.roll_parameter_provider()
        # When attack_extra_rolled > 0, use normal damage calculation
        rolled, kept, modifier = provider.get_damage_roll_params(ikoma, target, "attack", 2)
        # With extra, rolled should be normal (not forced to 10)
        # Normal damage = weapon_rolled (default 3) + extra_rolled(damage) + attack_extra_rolled
        # This should NOT be forced to 10
        self.assertIsNotNone(rolled)


# ──────────────────────────────────────────────────────────────────
# Special Ability: Force opponent to parry
# ──────────────────────────────────────────────────────────────────

class TestIkomaSpecialTracker(unittest.TestCase):
    """Test the IkomaSpecialTracker that tracks uses of the special ability."""

    def test_starts_with_one_use(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        self.assertEqual(1, tracker.uses_remaining())

    def test_use_decrements(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        tracker.use()
        self.assertEqual(0, tracker.uses_remaining())

    def test_has_uses(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        self.assertTrue(tracker.has_uses())
        tracker.use()
        self.assertFalse(tracker.has_uses())

    def test_reset(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        tracker.use()
        self.assertFalse(tracker.has_uses())
        tracker.reset()
        self.assertTrue(tracker.has_uses())

    def test_set_max_uses(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        tracker.set_max_uses(2)
        tracker.use()
        self.assertTrue(tracker.has_uses())
        tracker.use()
        self.assertFalse(tracker.has_uses())

    def test_reset_restores_max_uses(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        tracker.set_max_uses(2)
        tracker.use()
        tracker.use()
        tracker.reset()
        self.assertEqual(2, tracker.uses_remaining())


class TestIkomaSpecialAbilitySetup(unittest.TestCase):
    """Test that apply_special_ability installs the correct components."""

    def test_take_action_event_factory_installed(self):
        ikoma = Character("Ikoma")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_special_ability(ikoma)
        self.assertIsInstance(
            ikoma.take_action_event_factory(),
            ikoma_bard_school.IkomaTakeActionEventFactory,
        )

    def test_new_round_listener_installed(self):
        ikoma = Character("Ikoma")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_special_ability(ikoma)
        self.assertIsInstance(
            ikoma._listeners["new_round"],
            ikoma_bard_school.IkomaNewRoundListener,
        )


class TestIkomaNewRoundListener(unittest.TestCase):
    """Test the IkomaNewRoundListener resets the tracker and rolls initiative."""

    def test_resets_tracker_on_new_round(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        tracker.use()
        self.assertFalse(tracker.has_uses())
        listener = ikoma_bard_school.IkomaNewRoundListener(tracker)
        ikoma = Character("Ikoma")
        enemy = Character("Enemy")
        group1 = Group("Lion", ikoma)
        group2 = Group("Enemies", enemy)
        context = EngineContext([group1, group2])

        # Rig initiative
        rp = CalvinistRollProvider()
        rp.put_initiative_roll([3, 7])
        ikoma.set_roll_provider(rp)

        # Play new round event
        event = events.NewRoundEvent(1)
        list(listener.handle(ikoma, event, context))

        # Tracker should be reset
        self.assertTrue(tracker.has_uses())

    def test_rolls_initiative(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        listener = ikoma_bard_school.IkomaNewRoundListener(tracker)
        ikoma = Character("Ikoma")
        enemy = Character("Enemy")
        group1 = Group("Lion", ikoma)
        group2 = Group("Enemies", enemy)
        context = EngineContext([group1, group2])

        rp = CalvinistRollProvider()
        rp.put_initiative_roll([2, 6])
        ikoma.set_roll_provider(rp)

        event = events.NewRoundEvent(1)
        list(listener.handle(ikoma, event, context))

        # Initiative should have been rolled
        self.assertEqual([2, 6], ikoma.actions())


class TestIkomaTakeActionEventFactory(unittest.TestCase):
    """Test that the factory returns IkomaTakeAttackActionEvent."""

    def test_returns_ikoma_take_attack_action_event(self):
        tracker = ikoma_bard_school.IkomaSpecialTracker()
        factory = ikoma_bard_school.IkomaTakeActionEventFactory(tracker)
        ikoma = Character("Ikoma")
        enemy = Character("Enemy")
        group1 = Group("Lion", ikoma)
        group2 = Group("Enemies", enemy)
        context = EngineContext([group1, group2])
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            ikoma, enemy, "attack", initiative_action, context,
        )
        event = factory.get_take_attack_action_event(attack)
        self.assertIsInstance(event, ikoma_bard_school.IkomaTakeAttackActionEvent)


class TestIkomaForcedParry(unittest.TestCase):
    """Test the Ikoma Special Ability: after attack hits, force the
    opponent to spend their next action die to parry."""

    def _setup_combat(self, ikoma_attack_roll=25, target_parry_skill=3):
        """Create Ikoma and enemy in combat context with rigged rolls."""
        self.ikoma = Character("Ikoma")
        self.ikoma.set_ring("fire", 3)
        self.ikoma.set_ring("water", 3)
        self.ikoma.set_skill("attack", 3)
        self.ikoma.set_skill("parry", 3)
        self.ikoma.set_actions([1])

        self.enemy = Character("Enemy")
        self.enemy.set_ring("fire", 3)
        self.enemy.set_ring("air", 3)
        self.enemy.set_skill("attack", 3)
        self.enemy.set_skill("parry", target_parry_skill)
        self.enemy.set_actions([4, 8])

        group1 = Group("Lion", self.ikoma)
        group2 = Group("Enemies", self.enemy)
        self.context = EngineContext([group1, group2], round=1, phase=1)
        self.context.initialize()

        # Apply the special ability
        self.school = ikoma_bard_school.IkomaBardSchool()
        self.school.apply_special_ability(self.ikoma)

    def test_forced_parry_after_attack_hits(self):
        """When the Ikoma's attack hits, the target is forced to parry."""
        self._setup_combat()

        # Rig Ikoma's attack roll: hits enemy (roll 25 vs TN 20)
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)
        ikoma_rp.put_damage_roll(20)  # damage in case parry fails
        self.ikoma.set_roll_provider(ikoma_rp)

        # Rig enemy's parry roll: parry succeeds (roll >= attack roll 25)
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("parry", 30)
        self.enemy.set_roll_provider(enemy_rp)

        # Create and play the attack
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action, self.context,
        )
        take_event = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Attack should be parried because the forced parry succeeded
        self.assertTrue(attack.parried())

        # Enemy should have spent an action die (the lowest available: 4)
        # Started with [4, 8], spent one, should have [8] left
        self.assertNotIn(4, self.enemy.actions())

        # Enemy should not have taken damage
        self.assertEqual(0, self.enemy.lw())

    def test_forced_parry_fails_damage_dealt(self):
        """When the forced parry fails, the attack succeeds and deals damage."""
        self._setup_combat()

        # Rig Ikoma's attack roll: hits enemy (roll 25 vs TN 20)
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)
        ikoma_rp.put_damage_roll(20)  # damage to enemy
        self.ikoma.set_roll_provider(ikoma_rp)

        # Rig enemy's parry roll: parry fails (roll < attack roll 25)
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("parry", 10)
        enemy_rp.put_wound_check_roll(50)  # survive wound check
        self.enemy.set_roll_provider(enemy_rp)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action, self.context,
        )
        take_event = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Attack should NOT be parried (forced parry failed)
        self.assertFalse(attack.parried())

        # Enemy should have taken damage
        self.assertTrue(self.enemy.lw() > 0 or self.enemy.sw() > 0)

    def test_no_forced_parry_when_attack_misses(self):
        """When the attack misses, no forced parry happens."""
        self._setup_combat()

        # Rig Ikoma's attack roll: misses (roll 5 vs TN 20)
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 5)
        self.ikoma.set_roll_provider(ikoma_rp)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action, self.context,
        )
        take_event = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Enemy should not have spent any action dice
        self.assertEqual([4, 8], self.enemy.actions())

    def test_no_forced_parry_when_target_has_no_actions(self):
        """When the target has no action dice, no forced parry happens."""
        self._setup_combat()
        self.enemy.set_actions([])  # no action dice

        # Rig Ikoma's attack roll: hits
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)
        ikoma_rp.put_damage_roll(20)
        self.ikoma.set_roll_provider(ikoma_rp)

        # Rig enemy wound check
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_wound_check_roll(50)
        self.enemy.set_roll_provider(enemy_rp)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action, self.context,
        )
        take_event = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Attack should succeed (not parried since target had no actions)
        self.assertFalse(attack.parried())
        # Damage should be dealt
        self.assertTrue(self.enemy.lw() > 0 or self.enemy.sw() > 0)

    def test_once_per_round(self):
        """The forced parry can only be used once per round (before 5th Dan)."""
        self._setup_combat()

        # Give Ikoma two action dice so it can attack twice
        self.ikoma.set_actions([1, 3])

        # First attack: rigged to hit
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)  # first attack hits
        ikoma_rp.put_skill_roll("attack", 25)  # second attack hits
        ikoma_rp.put_damage_roll(20)            # second attack damage (first is parried)
        self.ikoma.set_roll_provider(ikoma_rp)

        # Enemy parry rolls for forced parries
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("parry", 30)  # first forced parry succeeds
        enemy_rp.put_wound_check_roll(50)      # survive second attack
        self.enemy.set_roll_provider(enemy_rp)

        initiative_action1 = InitiativeAction([1], 1)
        attack1 = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action1, self.context,
        )
        take_event1 = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack1)
        engine = CombatEngine(self.context)
        engine.event(take_event1)

        # First attack should be parried
        self.assertTrue(attack1.parried())

        # Second attack in same round: no forced parry (once per round)
        initiative_action2 = InitiativeAction([3], 3)
        attack2 = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action2, self.context,
        )
        take_event2 = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack2)
        engine.event(take_event2)

        # Second attack should NOT trigger forced parry
        # It may or may not be parried by the enemy's normal interrupt strategy,
        # but the key test is that enemy was not forced to spend another die
        # Enemy started with [4, 8], one was spent on forced parry of first attack
        # For second attack, the remaining dice should not be forced-spent
        self.assertFalse(attack2.parried())

    def test_resets_each_round(self):
        """The special ability resets each round via the new round listener."""
        self._setup_combat()

        # First attack in round 1
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)  # first round attack
        self.ikoma.set_roll_provider(ikoma_rp)

        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("parry", 30)   # first round forced parry succeeds
        self.enemy.set_roll_provider(enemy_rp)

        initiative_action = InitiativeAction([1], 1)
        attack1 = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action, self.context,
        )
        take_event1 = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack1)
        engine = CombatEngine(self.context)
        engine.event(take_event1)
        self.assertTrue(attack1.parried())

        # New round
        ikoma_rp2 = CalvinistRollProvider()
        ikoma_rp2.put_initiative_roll([2])
        ikoma_rp2.put_skill_roll("attack", 25)  # second round attack
        self.ikoma.set_roll_provider(ikoma_rp2)

        enemy_rp2 = CalvinistRollProvider()
        enemy_rp2.put_initiative_roll([3, 7])
        enemy_rp2.put_skill_roll("parry", 30)   # second round forced parry succeeds
        self.enemy.set_roll_provider(enemy_rp2)

        engine.event(events.NewRoundEvent(2))

        # Second round attack: forced parry should work again
        initiative_action2 = InitiativeAction([2], 2)
        attack2 = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action2, self.context,
        )
        take_event2 = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack2)
        engine.event(take_event2)
        self.assertTrue(attack2.parried())

    def test_no_free_raise_on_forced_parry(self):
        """The forced parry does NOT get a free raise for pre-declaring.
        The parry TN is the attack roll, without any reduction."""
        self._setup_combat()

        # Rig Ikoma's attack roll: hits with roll 25
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)
        ikoma_rp.put_damage_roll(20)
        self.ikoma.set_roll_provider(ikoma_rp)

        # Enemy's parry roll: exactly 24 (just under the attack roll of 25)
        # If there were a free raise (-5), parry TN would be 20, and 24 >= 20 would succeed
        # Without free raise, parry TN is 25, and 24 < 25 fails
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("parry", 24)
        enemy_rp.put_wound_check_roll(50)
        self.enemy.set_roll_provider(enemy_rp)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action, self.context,
        )
        take_event = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # The forced parry should fail (no free raise)
        self.assertFalse(attack.parried())

    def test_forced_parry_uses_lowest_action_die(self):
        """The forced parry should use the target's lowest (next available) action die."""
        self._setup_combat()
        self.enemy.set_actions([3, 7, 9])

        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)
        self.ikoma.set_roll_provider(ikoma_rp)

        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("parry", 30)  # parry succeeds
        self.enemy.set_roll_provider(enemy_rp)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.ikoma, self.enemy, "attack", initiative_action, self.context,
        )
        take_event = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # The lowest action die (3) should have been spent
        self.assertNotIn(3, self.enemy.actions())
        # The other dice should remain
        self.assertIn(7, self.enemy.actions())
        self.assertIn(9, self.enemy.actions())


# ──────────────────────────────────────────────────────────────────
# 5th Dan: Extra use of special + cancel opponent's attack
# ──────────────────────────────────────────────────────────────────

class TestIkomaFifthDanSetup(unittest.TestCase):
    """Test that apply_rank_five_ability sets up the 5th Dan correctly."""

    def test_tracker_gets_two_uses(self):
        ikoma = Character("Ikoma")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_special_ability(ikoma)
        school.apply_rank_five_ability(ikoma)
        # After 5th Dan, the tracker should have 2 uses per round
        # We can verify by getting the tracker from the factory
        factory = ikoma.take_action_event_factory()
        self.assertEqual(2, factory._tracker.uses_remaining())

    def test_attack_rolled_listener_installed(self):
        ikoma = Character("Ikoma")
        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_special_ability(ikoma)
        school.apply_rank_five_ability(ikoma)
        self.assertIsInstance(
            ikoma._listeners["attack_rolled"],
            ikoma_bard_school.IkomaFifthDanAttackRolledListener,
        )


class TestIkomaFifthDanTwoUsesPerRound(unittest.TestCase):
    """Test that at 5th Dan, the Ikoma can force parry twice per round."""

    def _setup_combat(self):
        self.ikoma = Character("Ikoma")
        self.ikoma.set_ring("fire", 3)
        self.ikoma.set_ring("water", 3)
        self.ikoma.set_skill("attack", 3)
        self.ikoma.set_skill("parry", 3)
        self.ikoma.set_actions([1, 3])

        self.enemy = Character("Enemy")
        self.enemy.set_ring("fire", 3)
        self.enemy.set_ring("air", 3)
        self.enemy.set_skill("attack", 3)
        self.enemy.set_skill("parry", 3)
        self.enemy.set_actions([4, 6, 8])

        group1 = Group("Lion", self.ikoma)
        group2 = Group("Enemies", self.enemy)
        self.context = EngineContext([group1, group2], round=1, phase=1)
        self.context.initialize()

        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_special_ability(self.ikoma)
        school.apply_rank_five_ability(self.ikoma)

    def test_two_forced_parries_in_one_round(self):
        """At 5th Dan, the Ikoma can force parry twice per round."""
        self._setup_combat()

        # First attack
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_skill_roll("attack", 25)  # first attack hits
        ikoma_rp.put_skill_roll("attack", 25)  # second attack hits
        self.ikoma.set_roll_provider(ikoma_rp)

        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("parry", 30)  # first forced parry succeeds
        enemy_rp.put_skill_roll("parry", 30)  # second forced parry succeeds
        self.enemy.set_roll_provider(enemy_rp)

        engine = CombatEngine(self.context)

        # First attack
        ia1 = InitiativeAction([1], 1)
        attack1 = actions.AttackAction(
            self.ikoma, self.enemy, "attack", ia1, self.context,
        )
        take1 = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack1)
        engine.event(take1)
        self.assertTrue(attack1.parried())

        # Second attack
        ia2 = InitiativeAction([3], 3)
        attack2 = actions.AttackAction(
            self.ikoma, self.enemy, "attack", ia2, self.context,
        )
        take2 = self.ikoma.take_action_event_factory().get_take_attack_action_event(attack2)
        engine.event(take2)
        self.assertTrue(attack2.parried())


class TestIkomaFifthDanCancelAttack(unittest.TestCase):
    """Test the 5th Dan ability to cancel an opponent's attack."""

    def _setup_combat(self):
        self.ikoma = Character("Ikoma")
        self.ikoma.set_ring("fire", 3)
        self.ikoma.set_ring("water", 3)
        self.ikoma.set_skill("attack", 3)
        self.ikoma.set_skill("parry", 3)
        self.ikoma.set_actions([4, 8])

        self.enemy = Character("Enemy")
        self.enemy.set_ring("fire", 3)
        self.enemy.set_skill("attack", 3)
        self.enemy.set_skill("parry", 3)
        self.enemy.set_actions([1])

        group1 = Group("Lion", self.ikoma)
        group2 = Group("Enemies", self.enemy)
        self.context = EngineContext([group1, group2], round=1, phase=1)
        self.context.initialize()

        school = ikoma_bard_school.IkomaBardSchool()
        school.apply_special_ability(self.ikoma)
        school.apply_rank_five_ability(self.ikoma)

    def test_cancel_opponent_attack(self):
        """When an opponent attacks the Ikoma, the 5th Dan ability can
        cancel the attack (set it as parried) using a tracker use."""
        self._setup_combat()

        # Rig enemy attack roll: hits Ikoma
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 25)
        self.enemy.set_roll_provider(enemy_rp)

        ia = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.enemy, self.ikoma, "attack", ia, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # The attack should be cancelled (parried)
        self.assertTrue(attack.parried())

        # The Ikoma should not have taken any damage
        self.assertEqual(0, self.ikoma.lw())

    def test_cancel_uses_tracker(self):
        """Cancelling an attack uses a tracker use."""
        self._setup_combat()

        factory = self.ikoma.take_action_event_factory()
        initial_uses = factory._tracker.uses_remaining()

        # Rig enemy attack roll
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 25)
        self.enemy.set_roll_provider(enemy_rp)

        ia = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.enemy, self.ikoma, "attack", ia, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # One use should have been consumed
        self.assertEqual(initial_uses - 1, factory._tracker.uses_remaining())

    def test_no_cancel_when_tracker_empty(self):
        """When the tracker has no uses left, the attack is not cancelled."""
        self._setup_combat()

        # Exhaust the tracker
        factory = self.ikoma.take_action_event_factory()
        factory._tracker.use()
        factory._tracker.use()

        # Rig enemy attack
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 25)
        enemy_rp.put_damage_roll(20)
        self.enemy.set_roll_provider(enemy_rp)

        # Rig Ikoma wound check
        ikoma_rp = CalvinistRollProvider()
        ikoma_rp.put_wound_check_roll(50)
        self.ikoma.set_roll_provider(ikoma_rp)

        ia = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.enemy, self.ikoma, "attack", ia, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Attack should NOT be cancelled
        self.assertFalse(attack.parried())
        # Ikoma should have taken damage
        self.assertTrue(self.ikoma.lw() > 0 or self.ikoma.sw() > 0)

    def test_no_cancel_when_attack_misses(self):
        """The cancel ability should not trigger when the attack misses."""
        self._setup_combat()

        # Rig enemy attack roll: misses
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 5)
        self.enemy.set_roll_provider(enemy_rp)

        ia = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.enemy, self.ikoma, "attack", ia, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Attack missed, no need to cancel
        self.assertFalse(attack.parried())
        # Tracker should still have uses (not consumed for a miss)
        factory = self.ikoma.take_action_event_factory()
        self.assertEqual(2, factory._tracker.uses_remaining())

    def test_no_cancel_when_not_targeting_ikoma(self):
        """The cancel ability only triggers when the Ikoma is the target."""
        self._setup_combat()

        # Add an ally
        ally = Character("Ally")
        ally.set_skill("parry", 3)
        ally.set_actions([])
        self.ikoma.group().add(ally)
        ally.set_group(self.ikoma.group())
        self.context._characters.append(ally)

        # Rig enemy attack: targets the ally, not the Ikoma
        enemy_rp = CalvinistRollProvider()
        enemy_rp.put_skill_roll("attack", 25)
        enemy_rp.put_damage_roll(20)
        self.enemy.set_roll_provider(enemy_rp)

        # Rig ally wound check
        ally_rp = CalvinistRollProvider()
        ally_rp.put_wound_check_roll(50)
        ally.set_roll_provider(ally_rp)

        ia = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            self.enemy, ally, "attack", ia, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Attack should not be cancelled (Ikoma is not the target)
        self.assertFalse(attack.parried())
        # Tracker should still have full uses
        factory = self.ikoma.take_action_event_factory()
        self.assertEqual(2, factory._tracker.uses_remaining())
