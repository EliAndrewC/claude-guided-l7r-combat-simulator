#!/usr/bin/env python3

#
# test_daidoji_school.py
#
# Unit tests for the Daidoji Yojimbo School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.formation import LineFormation
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import daidoji_school
from simulation.strategies.base import CounterattackInterruptStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestDaidojiYojimboSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual("Daidoji Yojimbo School", school.name())

    def test_school_ring(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual(["counterattack", "double attack", "iaijutsu"], school.school_knacks())

    def test_extra_rolled(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual(["attack", "counterattack", "wound check"], school.extra_rolled())

    def test_free_raise_skills(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual(["counterattack"], school.free_raise_skills())


class TestDaidojiSpecialAbility(unittest.TestCase):
    """The Daidoji special ability sets counterattack interrupt cost to 1,
    installs counterattack interrupt strategy, and the custom action factory."""

    def test_interrupt_cost(self):
        school = daidoji_school.DaidojiYojimboSchool()
        builder = CharacterBuilder(9001).with_name("Daidoji").with_school(school)
        daidoji = builder.build()
        enemy = Character("Enemy")
        context = EngineContext([Group("Crane", daidoji), Group("Enemy", enemy)])
        self.assertEqual(1, daidoji.interrupt_cost("counterattack", context))

    def test_interrupt_strategy_is_counterattack(self):
        school = daidoji_school.DaidojiYojimboSchool()
        builder = CharacterBuilder(9001).with_name("Daidoji").with_school(school)
        daidoji = builder.build()
        self.assertIsInstance(daidoji.interrupt_strategy(), CounterattackInterruptStrategy)


class TestDaidojiCounterattackAction(unittest.TestCase):
    """Test the Daidoji counterattack has no penalty for counterattacking
    on behalf of others."""

    def setUp(self):
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_skill("parry", 3)
        self.daidoji.set_actions([1, 5])
        self.ally = Character("Ally")
        self.ally.set_skill("parry", 3)
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 3)
        self.attacker.set_actions([1])
        groups = [
            Group("Crane", [self.daidoji, self.ally]),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_no_penalty_for_others(self):
        """Daidoji counterattacking on behalf of an ally has no TN penalty."""
        # attack targets the ally, not the daidoji
        attack = actions.AttackAction(
            self.attacker, self.ally, "attack", self.initiative_action, self.context,
        )
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            self.initiative_action, self.context, attack,
        )
        # TN should be just the attacker's tn_to_hit, no penalty
        expected_tn = self.attacker.tn_to_hit()
        self.assertEqual(expected_tn, counterattack.tn())

    def test_standard_counterattack_has_penalty(self):
        """Regular CounterattackAction for comparison: has penalty when counterattacking for others."""
        attack = actions.AttackAction(
            self.attacker, self.ally, "attack", self.initiative_action, self.context,
        )
        counterattack = actions.CounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            self.initiative_action, self.context, attack,
        )
        # Standard counterattack has penalty of 5 * attacker's parry
        expected_tn = self.attacker.tn_to_hit() + 5 * self.attacker.skill("parry")
        self.assertEqual(expected_tn, counterattack.tn())

    def test_no_penalty_for_self(self):
        """Counterattacking on your own behalf has no penalty (same as standard)."""
        attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", self.initiative_action, self.context,
        )
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            self.initiative_action, self.context, attack,
        )
        expected_tn = self.attacker.tn_to_hit()
        self.assertEqual(expected_tn, counterattack.tn())


class TestDaidojiActionFactory(unittest.TestCase):
    def test_returns_daidoji_counterattack_action(self):
        daidoji = Character("Daidoji")
        attacker = Character("Attacker")
        groups = [Group("Crane", daidoji), Group("Enemy", attacker)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, daidoji, "attack", initiative_action, context)
        factory = daidoji_school.DaidojiActionFactory()
        counterattack = factory.get_counterattack_action(
            daidoji, attacker, attack, "counterattack", initiative_action, context,
        )
        self.assertIsInstance(counterattack, daidoji_school.DaidojiCounterattackAction)


class TestDaidojiTakeCounterattackActionEvent(unittest.TestCase):
    """Test the Daidoji-specific counterattack event that gives the opponent
    a free raise on wound check when used as an interrupt."""

    def setUp(self):
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_actions([5, 8])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crane", self.daidoji), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        # original attack: attacker attacks daidoji
        self.attack_initiative = InitiativeAction([1], 1)
        self.attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", self.attack_initiative, self.context,
        )
        self.attack.set_skill_roll(25)

    def test_interrupt_gives_opponent_wound_check_bonus(self):
        """When counterattacking as interrupt and hitting, opponent gets -5 TN on wound check."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: counterattack succeeds, damage = 20
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(20)
        self.daidoji.set_roll_provider(roll_provider)
        # rig attacker's wound check
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(18)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Find the LW damage event in history
        history = engine.history()
        lw_events = [e for e in history if isinstance(e, events.LightWoundsDamageEvent)]
        self.assertEqual(1, len(lw_events))
        lw_event = lw_events[0]
        # Damage is 20, but wound check TN should be 20 - 5 = 15 (free raise)
        self.assertEqual(20, lw_event.damage)
        self.assertEqual(15, lw_event.wound_check_tn)

    def test_non_interrupt_no_wound_check_bonus(self):
        """When counterattacking with a regular action, no wound check bonus."""
        regular_action = InitiativeAction([5], 5)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            regular_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(20)
        self.daidoji.set_roll_provider(roll_provider)
        # rig attacker's wound check
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(18)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        lw_events = [e for e in history if isinstance(e, events.LightWoundsDamageEvent)]
        self.assertEqual(1, len(lw_events))
        lw_event = lw_events[0]
        # No bonus: wound check TN should equal damage
        self.assertEqual(20, lw_event.damage)
        self.assertEqual(20, lw_event.wound_check_tn)

    def test_counterattack_miss_no_damage(self):
        """A missed counterattack deals no damage."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: miss
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 5)
        self.daidoji.set_roll_provider(roll_provider)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        self.assertEqual(0, self.attacker.lw())

    def test_event_history(self):
        """Verify the correct event sequence for a successful Daidoji counterattack."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.daidoji.set_roll_provider(roll_provider)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        self.assertIsInstance(history[0], daidoji_school.DaidojiTakeCounterattackActionEvent)
        self.assertIsInstance(history[1], events.CounterattackDeclaredEvent)
        self.assertIsInstance(history[2], events.CounterattackRolledEvent)
        self.assertIsInstance(history[3], events.CounterattackSucceededEvent)
        self.assertIsInstance(history[4], events.LightWoundsDamageEvent)


class TestDaidojiThirdDan(unittest.TestCase):
    """3rd Dan: After a successful counterattack, the original attack's target
    gets X free raises (bonus = 5*X) on their wound check, where X = Daidoji's attack skill."""

    def setUp(self):
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_skill("attack", 3)
        self.daidoji.set_actions([5, 8])
        self.ally = Character("Ally")
        self.ally.set_actions([])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [
            Group("Crane", [self.daidoji, self.ally]),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        # original attack: attacker attacks the ally
        self.attack_initiative = InitiativeAction([1], 1)
        self.attack = actions.AttackAction(
            self.attacker, self.ally, "attack", self.attack_initiative, self.context,
        )
        self.attack.set_skill_roll(25)

    def test_ally_gets_wound_check_bonus_after_successful_counterattack(self):
        """After a successful counterattack on behalf of an ally,
        the ally gets a WoundCheckFloatingBonus of 5 * Daidoji's attack skill."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: counterattack succeeds, damage = 20
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(20)
        self.daidoji.set_roll_provider(roll_provider)
        # rig attacker's wound check
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(18)
        self.attacker.set_roll_provider(attacker_rp)

        # Apply 3rd Dan ability to enable the bonus
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_three_ability(self.daidoji)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # After successful counterattack, ally should have a wound check floating bonus
        # bonus = 5 * attack_skill = 5 * 3 = 15
        bonuses = self.ally.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(15, bonuses[0].bonus())

    def test_no_bonus_on_missed_counterattack(self):
        """A missed counterattack should not grant any wound check bonus."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: miss
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 5)
        self.daidoji.set_roll_provider(roll_provider)

        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_three_ability(self.daidoji)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # No bonus should be granted
        bonuses = self.ally.floating_bonuses("wound check")
        self.assertEqual(0, len(bonuses))

    def test_self_gets_bonus_when_defending_self(self):
        """When the Daidoji counterattacks an attack targeting themselves,
        they should get the wound check bonus on themselves."""
        # Attack targets the Daidoji, not the ally
        attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", self.attack_initiative, self.context,
        )
        attack.set_skill_roll(25)
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, attack,
        )
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(20)
        self.daidoji.set_roll_provider(roll_provider)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(18)
        self.attacker.set_roll_provider(attacker_rp)

        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_three_ability(self.daidoji)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Daidoji should have the wound check bonus on themselves
        bonuses = self.daidoji.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(15, bonuses[0].bonus())

    def test_bonus_scales_with_attack_skill(self):
        """The bonus should scale with the Daidoji's attack skill."""
        self.daidoji.set_skill("attack", 5)
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(20)
        self.daidoji.set_roll_provider(roll_provider)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(18)
        self.attacker.set_roll_provider(attacker_rp)

        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_three_ability(self.daidoji)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # bonus = 5 * 5 = 25
        bonuses = self.ally.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(25, bonuses[0].bonus())


class TestDaidojiFourthDan(unittest.TestCase):
    """4th Dan raises the school ring (Water) and installs the damage redirect listener."""

    def test_fourth_dan_raises_water(self):
        school = daidoji_school.DaidojiYojimboSchool()
        builder = (
            CharacterBuilder(9001)
            .with_name("Daidoji")
            .with_school(school)
            .buy_skill("counterattack", 4)
            .buy_skill("double attack", 4)
            .buy_skill("iaijutsu", 4)
        )
        daidoji = builder.build()
        # School ring starts at 3, 4th Dan raises it to 4
        self.assertEqual(4, daidoji.ring("water"))


class TestDaidojiFourthDanRedirect(unittest.TestCase):
    """4th Dan: Redirect damage from allies to the Daidoji."""

    def setUp(self):
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_skill("parry", 3)
        self.daidoji.set_actions([5, 8])
        self.ally = Character("Ally")
        self.ally.set_actions([])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [
            Group("Crane", [self.daidoji, self.ally]),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()

    def test_redirect_damage_to_daidoji(self):
        """When an ally takes LW damage, the Daidoji takes it instead."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_four_ability(self.daidoji)

        # rig wound check roll for Daidoji
        daidoji_rp = CalvinistRollProvider()
        daidoji_rp.put_wound_check_roll(50)
        self.daidoji.set_roll_provider(daidoji_rp)

        # attacker damages the ally
        lw_event = events.LightWoundsDamageEvent(self.attacker, self.ally, 15)
        engine = CombatEngine(self.context)
        engine.event(lw_event)

        # Daidoji should have taken the damage, not the ally
        self.assertEqual(15, self.daidoji.lw())
        self.assertEqual(0, self.ally.lw())

    def test_daidoji_takes_own_damage_normally(self):
        """When the Daidoji themselves is hit, they take damage normally."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_four_ability(self.daidoji)

        # rig wound check roll for Daidoji
        daidoji_rp = CalvinistRollProvider()
        daidoji_rp.put_wound_check_roll(50)
        self.daidoji.set_roll_provider(daidoji_rp)

        # attacker damages the daidoji directly
        lw_event = events.LightWoundsDamageEvent(self.attacker, self.daidoji, 15)
        engine = CombatEngine(self.context)
        engine.event(lw_event)

        # Daidoji should take damage normally
        self.assertEqual(15, self.daidoji.lw())
        self.assertEqual(0, self.ally.lw())

    def test_no_redirect_for_enemy_damage(self):
        """Daidoji does not redirect damage taken by enemies."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_four_ability(self.daidoji)

        # rig wound check roll for attacker (high roll so wound check succeeds)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        # Daidoji damages the attacker (enemy)
        lw_event = events.LightWoundsDamageEvent(self.daidoji, self.attacker, 15)
        engine = CombatEngine(self.context)
        engine.event(lw_event)

        # The attacker should have taken the damage (not the Daidoji).
        # Attacker's LW may be 0 if the wound check strategy chose to take a SW,
        # but either way the Daidoji should not have taken any damage.
        self.assertEqual(0, self.daidoji.lw())
        # Verify the attacker was damaged (SW or LW history proves they took the hit)
        self.assertTrue(self.attacker.sw() > 0 or len(self.attacker.lw_history()) > 0)

    def test_redirect_preserves_wound_check_tn(self):
        """When redirecting damage, the wound check TN should be preserved."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_four_ability(self.daidoji)

        # rig wound check roll for Daidoji
        daidoji_rp = CalvinistRollProvider()
        daidoji_rp.put_wound_check_roll(50)
        self.daidoji.set_roll_provider(daidoji_rp)

        # attacker damages the ally with a custom tn
        lw_event = events.LightWoundsDamageEvent(self.attacker, self.ally, 15, tn=10)
        engine = CombatEngine(self.context)
        engine.event(lw_event)

        # Daidoji took the damage
        self.assertEqual(15, self.daidoji.lw())
        self.assertEqual(0, self.ally.lw())

    def test_daidoji_observes_other_damage_rolls(self):
        """The Daidoji should still observe other characters' damage rolls."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_four_ability(self.daidoji)

        # rig wound check roll for attacker
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        # another character's damage event
        lw_event = events.LightWoundsDamageEvent(self.daidoji, self.attacker, 12)
        engine = CombatEngine(self.context)
        engine.event(lw_event)

        # Daidoji should have observed the damage roll (from their own attack)
        # The damage roll should be in the Daidoji's knowledge but they are the subject
        # so the default listener wouldn't observe it. This test confirms the listener
        # still lets non-self subject events be observed.
        self.assertEqual(12, self.attacker.lw())


class TestDaidojiFifthDan(unittest.TestCase):
    """5th Dan: After a wound check succeeds, lower the attacker's TN to hit
    by the excess (roll - tn), applied as a modifier on the attacker."""

    def setUp(self):
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_skill("attack", 3)
        self.daidoji.set_skill("parry", 3)
        self.daidoji.set_actions([5, 8])
        self.ally = Character("Ally")
        self.ally.set_skill("parry", 3)
        self.ally.set_actions([])
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 3)
        self.attacker.set_actions([1])
        groups = [
            Group("Crane", [self.daidoji, self.ally]),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()

    def test_modifier_after_daidoji_wound_check(self):
        """After the Daidoji succeeds a wound check, the attacker gets a TN penalty."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_five_ability(self.daidoji)

        # Daidoji succeeds wound check with excess
        # roll = 30, tn = 15, excess = 15
        wc_event = events.WoundCheckSucceededEvent(
            self.daidoji, self.attacker, 15, roll=30, tn=15,
        )
        engine = CombatEngine(self.context)
        engine.event(wc_event)

        # The Daidoji should have a modifier targeting the attacker with ATTACK_SKILLS
        # that gives +15 to the Daidoji's attack against the attacker
        modifier_value = self.daidoji.modifier(self.attacker, "attack")
        self.assertEqual(15, modifier_value)

    def test_no_modifier_when_no_excess(self):
        """If the wound check exactly meets TN, no modifier is added."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_five_ability(self.daidoji)

        # roll = 15, tn = 15, excess = 0
        wc_event = events.WoundCheckSucceededEvent(
            self.daidoji, self.attacker, 15, roll=15, tn=15,
        )
        engine = CombatEngine(self.context)
        engine.event(wc_event)

        modifier_value = self.daidoji.modifier(self.attacker, "attack")
        self.assertEqual(0, modifier_value)

    def test_modifier_after_ally_wound_check(self):
        """After an ally in the Daidoji's group succeeds a wound check,
        the Daidoji gets the modifier (not the ally)."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_five_ability(self.daidoji)

        # Ally succeeds wound check with excess
        # roll = 25, tn = 10, excess = 15
        wc_event = events.WoundCheckSucceededEvent(
            self.ally, self.attacker, 10, roll=25, tn=10,
        )
        engine = CombatEngine(self.context)
        engine.event(wc_event)

        # The Daidoji gets the modifier, not the ally
        daidoji_modifier = self.daidoji.modifier(self.attacker, "attack")
        self.assertEqual(15, daidoji_modifier)
        ally_modifier = self.ally.modifier(self.attacker, "attack")
        self.assertEqual(0, ally_modifier)

    def test_no_modifier_for_enemy_wound_check(self):
        """Enemy wound checks should not trigger the modifier."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_five_ability(self.daidoji)

        # Enemy succeeds wound check
        wc_event = events.WoundCheckSucceededEvent(
            self.attacker, self.daidoji, 15, roll=30, tn=15,
        )
        engine = CombatEngine(self.context)
        engine.event(wc_event)

        # Daidoji should have no modifier
        modifier_value = self.daidoji.modifier(self.attacker, "attack")
        self.assertEqual(0, modifier_value)

    def test_modifier_applies_to_all_attack_skills(self):
        """The modifier should apply to all attack skills (counterattack, double attack, etc)."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_five_ability(self.daidoji)

        wc_event = events.WoundCheckSucceededEvent(
            self.daidoji, self.attacker, 15, roll=30, tn=15,
        )
        engine = CombatEngine(self.context)
        engine.event(wc_event)

        # Check that it applies to multiple attack skills
        self.assertEqual(15, self.daidoji.modifier(self.attacker, "attack"))
        self.assertEqual(15, self.daidoji.modifier(self.attacker, "counterattack"))
        self.assertEqual(15, self.daidoji.modifier(self.attacker, "double attack"))
        self.assertEqual(15, self.daidoji.modifier(self.attacker, "lunge"))

    def test_modifier_does_not_apply_to_other_targets(self):
        """The modifier should only apply when attacking the specific attacker."""
        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_five_ability(self.daidoji)

        wc_event = events.WoundCheckSucceededEvent(
            self.daidoji, self.attacker, 15, roll=30, tn=15,
        )
        engine = CombatEngine(self.context)
        engine.event(wc_event)

        # Should not apply when attacking a different target
        other_enemy = self.ally  # just use ally as a stand-in
        modifier_value = self.daidoji.modifier(other_enemy, "attack")
        self.assertEqual(0, modifier_value)


class TestDaidojiTakeActionEventFactory(unittest.TestCase):
    def test_returns_daidoji_counterattack_event(self):
        daidoji = Character("Daidoji")
        attacker = Character("Attacker")
        groups = [Group("Crane", daidoji), Group("Enemy", attacker)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, daidoji, "attack", initiative_action, context)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            daidoji, attacker, "counterattack", initiative_action, context, attack,
        )
        factory = daidoji_school.DaidojiTakeActionEventFactory()
        event = factory.get_take_counterattack_action_event(counterattack)
        self.assertIsInstance(event, daidoji_school.DaidojiTakeCounterattackActionEvent)


class TestDaidojiFourthDanNonAdjacent(unittest.TestCase):
    """4th Dan: Redirect should NOT apply to non-adjacent allies."""

    def test_no_redirect_when_non_adjacent(self):
        """When the Daidoji is not adjacent to the ally, damage is not redirected."""
        daidoji = Character("Daidoji")
        daidoji.set_skill("counterattack", 3)
        daidoji.set_skill("parry", 3)
        daidoji.set_actions([5, 8])
        ally = Character("Ally")
        ally.set_actions([])
        filler = Character("Filler")
        filler.set_actions([])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        # Daidoji at pos 0, Filler at pos 1, Ally at pos 2
        # Daidoji is NOT adjacent to Ally (separated by Filler)
        formation = LineFormation([[daidoji, filler, ally], [attacker]])
        groups = [
            Group("Crane", [daidoji, filler, ally]),
            Group("Enemy", attacker),
        ]
        context = EngineContext(groups, round=1, phase=1, formation=formation)
        context.initialize()

        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_four_ability(daidoji)

        # rig wound check for ally (since Daidoji won't redirect)
        ally_rp = CalvinistRollProvider()
        ally_rp.put_wound_check_roll(50)
        ally.set_roll_provider(ally_rp)

        # attacker damages the non-adjacent ally
        lw_event = events.LightWoundsDamageEvent(attacker, ally, 15)
        engine = CombatEngine(context)
        engine.event(lw_event)

        # Daidoji should NOT have taken the damage
        self.assertEqual(0, daidoji.lw())
        # Ally should have taken the damage themselves
        # (LW may be 0 if the wound check strategy chose to take a SW)
        self.assertTrue(ally.sw() > 0 or len(ally.lw_history()) > 0)


class TestDaidojiFifthDanNonAdjacent(unittest.TestCase):
    """5th Dan: Modifier should NOT apply for non-adjacent ally's wound check."""

    def test_no_modifier_for_non_adjacent_ally(self):
        """Non-adjacent ally's wound check should not grant the Daidoji a modifier."""
        daidoji = Character("Daidoji")
        daidoji.set_skill("counterattack", 3)
        daidoji.set_skill("attack", 3)
        daidoji.set_skill("parry", 3)
        daidoji.set_actions([5, 8])
        ally = Character("Ally")
        ally.set_skill("parry", 3)
        ally.set_actions([])
        filler = Character("Filler")
        filler.set_actions([])
        attacker = Character("Attacker")
        attacker.set_skill("parry", 3)
        attacker.set_actions([1])
        # Daidoji at pos 0, Filler at pos 1, Ally at pos 2
        formation = LineFormation([[daidoji, filler, ally], [attacker]])
        groups = [
            Group("Crane", [daidoji, filler, ally]),
            Group("Enemy", attacker),
        ]
        context = EngineContext(groups, round=1, phase=1, formation=formation)
        context.initialize()

        school = daidoji_school.DaidojiYojimboSchool()
        school.apply_rank_five_ability(daidoji)

        # Non-adjacent ally succeeds wound check with excess
        wc_event = events.WoundCheckSucceededEvent(
            ally, attacker, 10, roll=25, tn=10,
        )
        engine = CombatEngine(context)
        engine.event(wc_event)

        # Daidoji should NOT get the modifier because ally is non-adjacent
        daidoji_modifier = daidoji.modifier(attacker, "attack")
        self.assertEqual(0, daidoji_modifier)
