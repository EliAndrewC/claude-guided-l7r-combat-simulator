#!/usr/bin/env python3

#
# test_shinjo_school.py
#
# Unit tests for the Shinjo Bushi School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import shinjo_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestShinjoBushiSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        """Spec 017 Q1 BLOCKING fix: rules text says 1st Dan grants
        extra die on 'initiative, parry, and wound checks'.  The
        previous skeleton incorrectly returned
        ``["double attack", "initiative", "parry"]``.
        """
        school = shinjo_school.ShinjoBushiSchool()
        self.assertEqual(
            ["initiative", "parry", "wound check"],
            school.extra_rolled(),
        )

    def test_school_ring(self):
        school = shinjo_school.ShinjoBushiSchool()
        self.assertEqual("air", school.school_ring())

    def test_school_knacks(self):
        school = shinjo_school.ShinjoBushiSchool()
        self.assertEqual(["double attack", "iaijutsu", "lunge"], school.school_knacks())

    def test_free_raise_skills(self):
        school = shinjo_school.ShinjoBushiSchool()
        self.assertEqual(["parry"], school.free_raise_skills())


class TestShinjoParryListener(unittest.TestCase):
    def setUp(self):
        self.shinjo = Character("Shinjo")
        self.shinjo.set_skill("attack", 3)
        self.shinjo.set_actions([1, 5, 8])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Unicorn", self.shinjo), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_decrease_action_dice_on_parry_succeeded(self):
        attack = actions.AttackAction(self.attacker, self.shinjo, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.shinjo, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = shinjo_school.ShinjoParryListener()
        list(listener.handle(self.shinjo, event, self.context))
        # attack_skill = 3
        # actions [1, 5, 8] -> [1-3, 5-3, 8-3] = [-2, 2, 5]
        self.assertEqual([-2, 2, 5], self.shinjo.actions())

    def test_decrease_action_dice_on_parry_failed(self):
        attack = actions.AttackAction(self.attacker, self.shinjo, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.shinjo, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(5)
        event = events.ParryFailedEvent(parry)
        listener = shinjo_school.ShinjoParryListener()
        list(listener.handle(self.shinjo, event, self.context))
        self.assertEqual([-2, 2, 5], self.shinjo.actions())


class TestShinjoNewRoundListener(unittest.TestCase):
    def test_set_highest_to_1(self):
        shinjo = Character("Shinjo")
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([3, 6, 9])
        shinjo.set_roll_provider(roll_provider)
        enemy = Character("enemy")
        groups = [Group("Unicorn", shinjo), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = shinjo_school.ShinjoNewRoundListener()
        event = events.NewRoundEvent(1)
        list(listener.handle(shinjo, event, context))
        # After initiative roll [3, 6, 9], highest (9) set to 1 -> [1, 3, 6]
        self.assertEqual([1, 3, 6], shinjo.actions())

    def test_set_highest_to_1_with_ties(self):
        """Spec 017 NEW BLOCKING bug fix (combat-simulator surfaced):
        when multiple dice tie at the max value, ALL of them are
        reduced to 1, not just the first occurrence.  Pre-fix
        ``actions.index(max(actions))`` reduced one tied die,
        leaving the rest as a stealth speed advantage."""
        shinjo = Character("Shinjo")
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([2, 3, 5, 5])
        shinjo.set_roll_provider(roll_provider)
        enemy = Character("enemy")
        groups = [Group("Unicorn", shinjo), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = shinjo_school.ShinjoNewRoundListener()
        event = events.NewRoundEvent(1)
        list(listener.handle(shinjo, event, context))
        # Both 5s become 1 → [2, 3, 1, 1] → sorted → [1, 1, 2, 3].
        self.assertEqual([1, 1, 2, 3], shinjo.actions())

    def test_empty_actions_no_op(self):
        """Edge case: empty initiative roll produces no mutation."""
        shinjo = Character("Shinjo")
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([])
        shinjo.set_roll_provider(roll_provider)
        enemy = Character("enemy")
        groups = [Group("Unicorn", shinjo), Group("Enemy", enemy)]
        context = EngineContext(groups)
        listener = shinjo_school.ShinjoNewRoundListener()
        event = events.NewRoundEvent(1)
        list(listener.handle(shinjo, event, context))
        self.assertEqual([], shinjo.actions())


class TestShinjoFifthDanParryListener(unittest.TestCase):
    def setUp(self):
        self.shinjo = Character("Shinjo")
        self.shinjo.set_skill("attack", 3)
        self.shinjo.set_actions([1, 5, 8])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Unicorn", self.shinjo), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_gain_wound_check_bonus_on_successful_parry(self):
        attack = actions.AttackAction(self.attacker, self.shinjo, "attack", self.initiative_action, self.context)
        attack.set_skill_roll(25)
        parry = actions.ParryAction(self.shinjo, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = shinjo_school.ShinjoFifthDanParryListener()
        list(listener.handle(self.shinjo, event, self.context))
        # Bonus = parry_roll (50) - attack_roll (25) = 25
        bonuses = self.shinjo.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(25, bonuses[0].bonus())
        self.assertTrue(isinstance(bonuses[0], WoundCheckFloatingBonus))

    def test_no_bonus_when_parry_roll_equals_attack_roll(self):
        attack = actions.AttackAction(self.attacker, self.shinjo, "attack", self.initiative_action, self.context)
        attack.set_skill_roll(30)
        parry = actions.ParryAction(self.shinjo, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(30)
        event = events.ParrySucceededEvent(parry)
        listener = shinjo_school.ShinjoFifthDanParryListener()
        list(listener.handle(self.shinjo, event, self.context))
        bonuses = self.shinjo.floating_bonuses("wound check")
        self.assertEqual(0, len(bonuses))

    def test_5th_dan_listener_ignores_failed_parry(self):
        """Spec 017 T-C1 refactor: at 5th Dan, ``apply_rank_five_ability``
        installs ``ShinjoFifthDanParryListener`` on the ``parry_succeeded``
        slot and KEEPS ``ShinjoParryListener`` on ``parry_failed``.
        So the 5th Dan listener never receives a ParryFailedEvent
        in production.  Calling it directly with one is a no-op
        (the previous skeleton's elif-branch was dead code that
        re-implemented 3rd Dan and was already covered by the
        ``parry_failed`` slot's listener).
        """
        attack = actions.AttackAction(self.attacker, self.shinjo, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.shinjo, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(5)
        event = events.ParryFailedEvent(parry)
        listener = shinjo_school.ShinjoFifthDanParryListener()
        list(listener.handle(self.shinjo, event, self.context))
        # No mutation — 5th Dan listener does not respond to
        # ParryFailedEvent.
        self.assertEqual([1, 5, 8], self.shinjo.actions())
        bonuses = self.shinjo.floating_bonuses("wound check")
        self.assertEqual(0, len(bonuses))


class TestShinjoSpendActionListener(unittest.TestCase):
    def setUp(self):
        self.shinjo = Character("Shinjo")
        self.shinjo.set_actions([3, 7])
        self.enemy = Character("enemy")
        groups = [Group("Unicorn", self.shinjo), Group("Enemy", self.enemy)]
        self.context = EngineContext(groups, round=1, phase=5)
        self.context.initialize()

    def test_hold_bonus_emits_add_modifier_event(self):
        """Spec 017 T-A3 (Q4 BLOCKING IDENTITY fix): spending a die
        held since phase 3 in phase 5 emits an AddModifierEvent with
        a +2*(5-3)=+4 bonus on attack skills, instead of the previous
        dead ``_shinjo_hold_bonus`` write.
        """
        initiative_action = InitiativeAction([3], 3)
        event = events.SpendActionEvent(self.shinjo, "attack", initiative_action)
        listener = shinjo_school.ShinjoSpendActionListener()
        emitted = list(listener.handle(self.shinjo, event, self.context))
        # Exactly one AddModifierEvent for the +4 bonus.
        add_events = [e for e in emitted if isinstance(e, events.AddModifierEvent)]
        self.assertEqual(1, len(add_events))
        modifier = add_events[0].modifier
        self.assertEqual(4, modifier.adjustment())
        # Hold-phases tag for trace observability (spec 017 T-C2).
        self.assertEqual(
            2, getattr(modifier, "_shinjo_special_ability_hold_phases", 0),
        )

    def test_no_bonus_when_same_phase(self):
        """Spending a die in the same phase it was rolled gives no
        bonus → no AddModifierEvent.
        """
        self.shinjo.set_actions([5, 7])
        initiative_action = InitiativeAction([5], 5)
        event = events.SpendActionEvent(self.shinjo, "attack", initiative_action)
        listener = shinjo_school.ShinjoSpendActionListener()
        emitted = list(listener.handle(self.shinjo, event, self.context))
        add_events = [e for e in emitted if isinstance(e, events.AddModifierEvent)]
        self.assertEqual(0, len(add_events))

    def test_no_bonus_for_other_character(self):
        """Listener should only affect the event's subject."""
        self.enemy.set_actions([3])
        initiative_action = InitiativeAction([3], 3)
        event = events.SpendActionEvent(self.enemy, "attack", initiative_action)
        listener = shinjo_school.ShinjoSpendActionListener()
        emitted = list(listener.handle(self.shinjo, event, self.context))
        # No events emitted — subject filter.
        self.assertEqual([], emitted)
