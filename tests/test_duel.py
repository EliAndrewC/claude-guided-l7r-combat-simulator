#!/usr/bin/env python3

#
# test_duel.py
#
# Unit tests for the iaijutsu duel system.
#

import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.duel import (
    AlwaysStrikeDuelStrategy,
    DuelEndedEvent,
    DuelInitiativeRolledEvent,
    DuelResheathEvent,
    DuelState,
    DuelStrikeAction,
    DuelStrikeRolledEvent,
    FocusThenStrikeDuelStrategy,
    IaijutsuDuelEvent,
    IaijutsuFocusEvent,
    IaijutsuStrikeEvent,
    ShowMeYourStanceDeclaredEvent,
    ShowMeYourStanceRolledEvent,
    SurvivalDuelStrategy,
    normalize_duel_roll_params,
)
from simulation.engine import CombatEngine
from simulation.exceptions import DuelEnded
from simulation.groups import Group
from simulation.mechanics.roll_provider import CalvinistRollProvider


class TestDuelEnded(unittest.TestCase):
    def test_duel_ended_exception(self):
        with self.assertRaises(DuelEnded):
            raise DuelEnded("test")

    def test_duel_ended_default_message(self):
        exc = DuelEnded()
        self.assertEqual("Duel ended", exc.message)


class TestNormalizeDuelRollParams(unittest.TestCase):
    def test_no_excess(self):
        self.assertEqual((5, 3, 0), normalize_duel_roll_params(5, 3))

    def test_excess_rolled_becomes_kept(self):
        # 12k3 -> 10k5
        self.assertEqual((10, 5, 0), normalize_duel_roll_params(12, 3))

    def test_excess_kept_becomes_plus_five(self):
        # 10k12 -> 10k10 + 10 (2 excess * 5)
        self.assertEqual((10, 10, 10), normalize_duel_roll_params(10, 12))

    def test_excess_rolled_and_kept(self):
        # 14k9 -> 10k13 -> 10k10 + 15 (3 excess * 5)
        self.assertEqual((10, 10, 15), normalize_duel_roll_params(14, 9))

    def test_with_existing_bonus(self):
        # 10k12 with bonus 3 -> 10k10 + 13 (2*5 + 3)
        self.assertEqual((10, 10, 13), normalize_duel_roll_params(10, 12, 3))

    def test_differs_from_normal(self):
        """Duel normalization uses +5 per excess kept, not +2."""
        from simulation.mechanics.roll_params import normalize_roll_params
        # 10k12 -> normal: 10k10 + 4, duel: 10k10 + 10
        normal = normalize_roll_params(10, 12)
        duel = normalize_duel_roll_params(10, 12)
        self.assertEqual((10, 10, 4), normal)
        self.assertEqual((10, 10, 10), duel)


class TestDuelEvents(unittest.TestCase):
    def test_show_me_your_stance_declared(self):
        c = Character("Duelist")
        event = ShowMeYourStanceDeclaredEvent(c)
        self.assertEqual("duel_stance_declared", event.name)
        self.assertEqual(c, event.subject)

    def test_show_me_your_stance_rolled(self):
        c = Character("Duelist")
        event = ShowMeYourStanceRolledEvent(c, 25, 5, 5)
        self.assertEqual("duel_stance_rolled", event.name)
        self.assertEqual(25, event.roll)
        self.assertEqual(5, event.discerned_fire)
        self.assertEqual(5, event.discerned_tn)

    def test_duel_initiative_rolled(self):
        c = Character("Challenger")
        d = Character("Defender")
        event = DuelInitiativeRolledEvent(c, d, 30, 20, c)
        self.assertEqual("duel_initiative_rolled", event.name)
        self.assertEqual(30, event.challenger_roll)
        self.assertEqual(20, event.defender_roll)
        self.assertEqual(c, event.winner)

    def test_focus_event(self):
        c = Character("Focused")
        d = Character("Opponent")
        event = IaijutsuFocusEvent(c, c, d, 15, 10)
        self.assertEqual("duel_focus", event.name)
        self.assertEqual(15, event.challenger_tn)
        self.assertEqual(10, event.defender_tn)

    def test_strike_event(self):
        c = Character("Striker")
        d = Character("Opponent")
        event = IaijutsuStrikeEvent(c, c, d, 15, 10)
        self.assertEqual("duel_strike", event.name)
        self.assertEqual(15, event.challenger_tn)
        self.assertEqual(10, event.defender_tn)

    def test_strike_rolled_event(self):
        c = Character("Striker")
        d = Character("Target")
        event = DuelStrikeRolledEvent(c, d, 25, 10, True, 15)
        self.assertEqual("duel_strike_rolled", event.name)
        self.assertEqual(25, event.roll)
        self.assertEqual(10, event.tn)
        self.assertTrue(event.is_hit)
        self.assertEqual(15, event.extra_damage_dice)

    def test_resheath_event(self):
        c = Character("Challenger")
        d = Character("Defender")
        event = DuelResheathEvent(c, d, c)
        self.assertEqual("duel_resheath", event.name)
        self.assertEqual(c, event.higher_roller)

    def test_duel_ended_event(self):
        c = Character("Challenger")
        d = Character("Defender")
        event = DuelEndedEvent(c, d)
        self.assertEqual("duel_ended", event.name)


class TestDuelStrikeAction(unittest.TestCase):
    def _make_character(self, name, fire=3, iaijutsu=3, roll_provider=None):
        c = Character(name)
        c.set_ring("fire", fire)
        c.set_skill("iaijutsu", iaijutsu)
        if roll_provider:
            c.set_roll_provider(roll_provider)
        return c

    def test_is_hit_when_roll_meets_tn(self):
        rp = CalvinistRollProvider()
        rp.put_skill_roll("iaijutsu", 15)
        c = self._make_character("Striker", roll_provider=rp)
        d = self._make_character("Target")
        action = DuelStrikeAction(c, d, tn=15)
        action.roll_skill()
        self.assertTrue(action.is_hit())

    def test_is_miss_when_roll_below_tn(self):
        rp = CalvinistRollProvider()
        rp.put_skill_roll("iaijutsu", 14)
        c = self._make_character("Striker", roll_provider=rp)
        d = self._make_character("Target")
        action = DuelStrikeAction(c, d, tn=15)
        action.roll_skill()
        self.assertFalse(action.is_hit())

    def test_extra_damage_dice_per_one(self):
        """Extra damage dice = roll - TN, per 1 (not per 5 like normal attacks)."""
        rp = CalvinistRollProvider()
        rp.put_skill_roll("iaijutsu", 25)
        c = self._make_character("Striker", roll_provider=rp)
        d = self._make_character("Target")
        action = DuelStrikeAction(c, d, tn=10)
        action.roll_skill()
        self.assertEqual(15, action.extra_damage_dice())

    def test_extra_damage_dice_zero_on_miss(self):
        rp = CalvinistRollProvider()
        rp.put_skill_roll("iaijutsu", 5)
        c = self._make_character("Striker", roll_provider=rp)
        d = self._make_character("Target")
        action = DuelStrikeAction(c, d, tn=10)
        action.roll_skill()
        self.assertEqual(0, action.extra_damage_dice())

    def test_roll_skill_no_explode(self):
        """Duel strike skill roll should pass explode=False."""
        rp = CalvinistRollProvider()
        rp.put_skill_roll("iaijutsu", 20)
        c = self._make_character("Striker", roll_provider=rp)
        d = self._make_character("Target")
        action = DuelStrikeAction(c, d, tn=10)
        result = action.roll_skill()
        self.assertEqual(20, result)
        # Verify it consumed the queued roll
        self.assertEqual(0, len(rp._queues.get("iaijutsu", [])))

    def test_roll_damage(self):
        rp = CalvinistRollProvider()
        rp.put_skill_roll("iaijutsu", 20)
        rp.put_damage_roll(35)
        c = self._make_character("Striker", fire=3, iaijutsu=3, roll_provider=rp)
        d = self._make_character("Target")
        action = DuelStrikeAction(c, d, tn=10)
        action.roll_skill()
        damage = action.roll_damage()
        self.assertEqual(35, damage)

    def test_damage_roll_params_with_duel_normalization(self):
        """Damage uses duel normalization (+5 per excess kept, not +2)."""
        rp = CalvinistRollProvider()
        rp.put_skill_roll("iaijutsu", 30)
        # Fire 3: base damage = fire(3) + katana(4k2) = 7k2
        # Extra dice = 30 - 10 = 20 extra rolled => 27k2
        # normalize_duel: 27k2 -> 10k2 (rolled capped at 10, 17 excess rolled -> kept 19)
        # kept 19 -> 10 + 45 (9 * 5)
        # Actually: 27k2 -> excess rolled = 17, so 10k(2+17)=10k19
        # then excess kept = 9, so 10k10 + 45
        c = self._make_character("Striker", fire=3, iaijutsu=3, roll_provider=rp)
        d = self._make_character("Target")
        action = DuelStrikeAction(c, d, tn=10)
        action.roll_skill()
        rolled, kept, mod = action.damage_roll_params()
        self.assertEqual(10, rolled)
        self.assertEqual(10, kept)
        self.assertEqual(45, mod)


class TestDuelStrategies(unittest.TestCase):
    def test_always_strike(self):
        strategy = AlwaysStrikeDuelStrategy()
        c = Character("Duelist")
        self.assertEqual("strike", strategy.recommend(c, None, None))

    def test_focus_then_strike(self):
        strategy = FocusThenStrikeDuelStrategy(focus_count=2)
        c = Character("Duelist")
        self.assertEqual("focus", strategy.recommend(c, None, None))
        self.assertEqual("focus", strategy.recommend(c, None, None))
        self.assertEqual("strike", strategy.recommend(c, None, None))


class TestIaijutsuDuelFlow(unittest.TestCase):
    """Test the full duel flow using rigged dice."""

    def _make_duelist(self, name, xp=100, fire=3, air=3, iaijutsu=3, roll_provider=None):
        c = Character(name, xp=xp)
        c.set_ring("fire", fire)
        c.set_ring("air", air)
        c.set_skill("iaijutsu", iaijutsu)
        if roll_provider:
            c.set_roll_provider(roll_provider)
        return c

    def test_duel_one_hits_immediately(self):
        """Challenger hits, defender misses -> DuelEnded raised."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance rolls (Air+Iaijutsu, no explode)
        c_rp.put_skill_roll("iaijutsu", 15)  # challenger stance
        d_rp.put_skill_roll("iaijutsu", 10)  # defender stance

        # Contested initiative rolls (Fire+Iaijutsu)
        c_rp.put_skill_roll("iaijutsu", 30)  # challenger wins initiative
        d_rp.put_skill_roll("iaijutsu", 20)

        # Strike rolls (no explode) - both use AlwaysStrike strategy
        # Challenger's TN = defender's XP/10 = 100/10 = 10
        # Defender's TN = challenger's XP/10 = 100/10 = 10
        c_rp.put_skill_roll("iaijutsu", 25)  # challenger hits (25 >= 10)
        d_rp.put_skill_roll("iaijutsu", 5)   # defender misses (5 < 10)

        # Damage roll for challenger (hits)
        c_rp.put_damage_roll(30)

        challenger = self._make_duelist("Challenger", xp=100, roll_provider=c_rp)
        challenger.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())
        defender = self._make_duelist("Defender", xp=100, roll_provider=d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        duel_event = IaijutsuDuelEvent(challenger, defender)
        events_list = []
        try:
            for event in duel_event.play(None):
                events_list.append(event)
        except DuelEnded:
            pass

        # Verify event sequence
        event_names = [e.name for e in events_list]
        self.assertIn("duel_stance_declared", event_names)
        self.assertIn("duel_stance_rolled", event_names)
        self.assertIn("duel_initiative_rolled", event_names)
        self.assertIn("duel_strike", event_names)
        self.assertIn("duel_strike_rolled", event_names)
        self.assertIn("lw_damage", event_names)
        self.assertIn("duel_ended", event_names)

        # Verify no resheath
        self.assertNotIn("duel_resheath", event_names)

    def test_duel_neither_hits_resheath_then_hit(self):
        """Neither hits -> resheath with free raise -> second round hit."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Round 1: Stance
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Round 1: Contested
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # Round 1: Strikes - both miss
        c_rp.put_skill_roll("iaijutsu", 5)  # miss (5 < 10)
        d_rp.put_skill_roll("iaijutsu", 3)  # miss (3 < 10)

        # Round 2: Contested
        c_rp.put_skill_roll("iaijutsu", 25)
        d_rp.put_skill_roll("iaijutsu", 15)

        # Round 2: Strikes - challenger hits
        c_rp.put_skill_roll("iaijutsu", 20)  # hit (20 >= 10)
        d_rp.put_skill_roll("iaijutsu", 2)   # miss

        # Damage
        c_rp.put_damage_roll(25)

        challenger = self._make_duelist("Challenger", xp=100, roll_provider=c_rp)
        challenger.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())
        defender = self._make_duelist("Defender", xp=100, roll_provider=d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        duel_event = IaijutsuDuelEvent(challenger, defender)
        events_list = []
        try:
            for event in duel_event.play(None):
                events_list.append(event)
        except DuelEnded:
            pass

        event_names = [e.name for e in events_list]
        self.assertIn("duel_resheath", event_names)
        self.assertIn("duel_ended", event_names)

        # Challenger rolled higher in round 1 (5 > 3), so should get free raise
        resheath = [e for e in events_list if e.name == "duel_resheath"][0]
        self.assertEqual(challenger, resheath.higher_roller)

        # Verify challenger got a floating bonus
        bonuses = challenger.floating_bonuses("damage")
        self.assertEqual(1, len(bonuses))

    def test_duel_with_focus_strategy(self):
        """Test that focus strategy increases TN before strikes."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Contested - challenger wins
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # Challenger focuses once, then strikes
        # Defender uses AlwaysStrike
        # Challenger focus adds +5 to challenger's TN (challenger's TN = 10 + 5 = 15)
        # Defender's TN = 10 (unchanged)

        # Strike rolls:
        # Challenger attacks defender at TN = defender's XP/10 = 10
        # Defender attacks challenger at TN = challenger's XP/10 + 5 (focus) = 15
        c_rp.put_skill_roll("iaijutsu", 12)  # hits (12 >= 10)
        d_rp.put_skill_roll("iaijutsu", 12)  # misses (12 < 15)

        c_rp.put_damage_roll(20)

        challenger = self._make_duelist("Challenger", xp=100, roll_provider=c_rp)
        challenger.set_strategy("duel_focus_or_strike", FocusThenStrikeDuelStrategy(focus_count=1))
        defender = self._make_duelist("Defender", xp=100, roll_provider=d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        duel_event = IaijutsuDuelEvent(challenger, defender)
        events_list = []
        try:
            for event in duel_event.play(None):
                events_list.append(event)
        except DuelEnded:
            pass

        event_names = [e.name for e in events_list]
        self.assertIn("duel_focus", event_names)
        self.assertIn("duel_ended", event_names)

        # Verify the focus event was for the challenger
        focus_events = [e for e in events_list if e.name == "duel_focus"]
        self.assertEqual(1, len(focus_events))
        self.assertEqual(challenger, focus_events[0].subject)

    def test_character_xp(self):
        """Test that Character stores and returns XP."""
        c = Character("Test", xp=150)
        self.assertEqual(150, c.xp())

    def test_character_xp_default(self):
        """Test that Character XP defaults to 0."""
        c = Character("Test")
        self.assertEqual(0, c.xp())


class TestRunDuel(unittest.TestCase):
    """Test CombatEngine.run_duel() integration."""

    def test_run_duel_lethal_damage_ends_combat(self):
        """Test that run_duel completes when duel damage kills defender."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance rolls
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Contested initiative
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # Strike rolls - only challenger hits
        c_rp.put_skill_roll("iaijutsu", 20)  # hits (>= 10)
        d_rp.put_skill_roll("iaijutsu", 5)   # misses (< 10)

        # Massive damage kills defender via wound check
        c_rp.put_damage_roll(100)
        d_rp.put_wound_check_roll(1)

        challenger = Character("Challenger", xp=100)
        challenger.set_ring("fire", 3)
        challenger.set_ring("air", 3)
        challenger.set_skill("iaijutsu", 3)
        challenger.set_skill("attack", 3)
        challenger.set_roll_provider(c_rp)
        challenger.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        defender = Character("Defender", xp=100)
        defender.set_ring("fire", 3)
        defender.set_ring("air", 3)
        defender.set_skill("iaijutsu", 3)
        defender.set_skill("attack", 3)
        defender.set_roll_provider(d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        control_group = Group("Control", [defender])
        test_group = Group("Test", [challenger])
        context = EngineContext([control_group, test_group])
        context.initialize()

        engine = CombatEngine(context)
        engine.run_duel()

        # Defender died during duel - CombatEnded was raised
        event_names = [e.name for e in engine.history()]
        self.assertIn("iaijutsu_duel", event_names)
        self.assertIn("lw_damage", event_names)
        self.assertIn("death", event_names)

    def test_run_duel_transitions_to_melee(self):
        """Test that run_duel transitions to melee when both survive duel damage."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance rolls
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Contested initiative
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # Strike rolls - challenger hits, defender misses
        c_rp.put_skill_roll("iaijutsu", 20)  # hits (>= 10)
        d_rp.put_skill_roll("iaijutsu", 5)   # misses (< 10)

        # Small damage so defender survives wound check
        c_rp.put_damage_roll(10)
        d_rp.put_wound_check_roll(50)  # defender passes wound check easily

        # Melee phase: initiative rolls
        c_rp.put_initiative_roll([3, 5])
        d_rp.put_initiative_roll([4, 6])

        # Melee: defender attempts to parry but fails
        d_rp.put_skill_roll("parry", 1)
        # Melee: challenger attacks and kills defender
        c_rp.put_skill_roll("attack", 30)
        c_rp.put_damage_roll(100)
        d_rp.put_wound_check_roll(1)  # defender fails wound check -> death

        challenger = Character("Challenger", xp=100)
        challenger.set_ring("fire", 3)
        challenger.set_ring("air", 3)
        challenger.set_skill("iaijutsu", 3)
        challenger.set_skill("attack", 3)
        challenger.set_roll_provider(c_rp)
        challenger.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        defender = Character("Defender", xp=100)
        defender.set_ring("fire", 3)
        defender.set_ring("air", 3)
        defender.set_skill("iaijutsu", 3)
        defender.set_skill("attack", 3)
        defender.set_roll_provider(d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        control_group = Group("Control", [defender])
        test_group = Group("Test", [challenger])
        context = EngineContext([control_group, test_group])
        context.initialize()

        engine = CombatEngine(context)
        engine.run_duel()

        event_names = [e.name for e in engine.history()]
        self.assertIn("iaijutsu_duel", event_names)
        self.assertIn("duel_ended", event_names)
        # Also has melee combat events
        self.assertIn("new_round", event_names)

    def test_run_duel_validates_groups(self):
        """Test that run_duel rejects non-1v1 setups."""
        c1 = Character("C1")
        c2 = Character("C2")
        c3 = Character("C3")
        g1 = Group("G1", [c1, c2])
        g2 = Group("G2", [c3])
        context = EngineContext([g1, g2])
        engine = CombatEngine(context)

        with self.assertRaises(RuntimeError):
            engine.run_duel()


class TestDuelNoVPOnWoundChecks(unittest.TestCase):
    """VP must not be spent on wound checks during duels."""

    def test_no_vp_spent_on_duel_wound_check(self):
        """During a duel, wound checks should not spend VP."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance rolls
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Contested initiative
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # Strike rolls - challenger hits
        c_rp.put_skill_roll("iaijutsu", 20)
        d_rp.put_skill_roll("iaijutsu", 5)

        # Lethal damage kills defender so no melee transition needed
        c_rp.put_damage_roll(100)
        d_rp.put_wound_check_roll(1)

        challenger = Character("Challenger", xp=100)
        challenger.set_ring("fire", 3)
        challenger.set_ring("air", 3)
        challenger.set_skill("iaijutsu", 3)
        challenger.set_skill("attack", 3)
        challenger.set_roll_provider(c_rp)
        challenger.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        defender = Character("Defender", xp=100)
        defender.set_ring("fire", 3)
        defender.set_ring("air", 3)
        defender.set_ring("water", 3)
        defender.set_skill("iaijutsu", 3)
        defender.set_skill("attack", 3)
        defender.set_roll_provider(d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        control_group = Group("Control", [defender])
        test_group = Group("Test", [challenger])
        context = EngineContext([control_group, test_group])
        context.initialize()

        engine = CombatEngine(context)
        engine.run_duel()

        # Verify no VP was spent on wound checks
        from simulation.events import SpendVoidPointsEvent
        vp_events = [
            e for e in engine.history()
            if isinstance(e, SpendVoidPointsEvent) and e.skill == "wound check"
        ]
        self.assertEqual(0, len(vp_events), "VP should not be spent on duel wound checks")

    def test_duel_wound_check_no_explosion(self):
        """Wound check rolls during duels should not have exploding 10s."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance rolls
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Contested initiative
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # Strike rolls - challenger hits
        c_rp.put_skill_roll("iaijutsu", 20)
        d_rp.put_skill_roll("iaijutsu", 5)

        # Lethal damage kills defender
        c_rp.put_damage_roll(100)
        d_rp.put_wound_check_roll(1)

        challenger = Character("Challenger", xp=100)
        challenger.set_ring("fire", 3)
        challenger.set_ring("air", 3)
        challenger.set_skill("iaijutsu", 3)
        challenger.set_skill("attack", 3)
        challenger.set_roll_provider(c_rp)
        challenger.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        defender = Character("Defender", xp=100)
        defender.set_ring("fire", 3)
        defender.set_ring("air", 3)
        defender.set_ring("water", 3)
        defender.set_skill("iaijutsu", 3)
        defender.set_skill("attack", 3)
        defender.set_roll_provider(d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        control_group = Group("Control", [defender])
        test_group = Group("Test", [challenger])
        context = EngineContext([control_group, test_group])
        context.initialize()

        engine = CombatEngine(context)
        engine.run_duel()

        # Verify LightWoundsDamageEvent has duel=True
        from simulation.events import LightWoundsDamageEvent
        lw_events = [e for e in engine.history() if isinstance(e, LightWoundsDamageEvent)]
        self.assertTrue(len(lw_events) > 0)
        for lw_event in lw_events:
            self.assertTrue(lw_event.duel, "LW damage during duel should have duel=True")


class TestDuelFocusStrikeEventsWithTNs(unittest.TestCase):
    """Focus/strike events should carry TN info."""

    def test_focus_event_has_tn_info(self):
        """IaijutsuFocusEvent should carry challenger and defender TNs."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Contested - challenger wins
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # Challenger focuses once, then strikes
        # Starting TNs: both 100/10 = 10
        # After challenger focuses: challenger TN = 15, defender TN = 10
        c_rp.put_skill_roll("iaijutsu", 20)
        d_rp.put_skill_roll("iaijutsu", 5)
        c_rp.put_damage_roll(20)

        challenger = Character("Challenger", xp=100)
        challenger.set_ring("fire", 3)
        challenger.set_ring("air", 3)
        challenger.set_skill("iaijutsu", 3)
        challenger.set_roll_provider(c_rp)
        challenger.set_strategy("duel_focus_or_strike", FocusThenStrikeDuelStrategy(focus_count=1))

        defender = Character("Defender", xp=100)
        defender.set_ring("fire", 3)
        defender.set_ring("air", 3)
        defender.set_skill("iaijutsu", 3)
        defender.set_roll_provider(d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        duel_event = IaijutsuDuelEvent(challenger, defender)
        events_list = []
        try:
            for event in duel_event.play(None):
                events_list.append(event)
        except DuelEnded:
            pass

        focus_events = [e for e in events_list if isinstance(e, IaijutsuFocusEvent)]
        self.assertEqual(1, len(focus_events))
        fe = focus_events[0]
        self.assertEqual(challenger, fe.challenger)
        self.assertEqual(defender, fe.defender)
        # Before focus: both TNs = 10. Focus adds 5 to challenger's TN.
        # The event records TNs after the focus.
        self.assertEqual(15, fe.challenger_tn)
        self.assertEqual(10, fe.defender_tn)

    def test_strike_event_has_tn_info(self):
        """IaijutsuStrikeEvent should carry challenger and defender TNs."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)
        c_rp.put_skill_roll("iaijutsu", 20)
        d_rp.put_skill_roll("iaijutsu", 5)
        c_rp.put_damage_roll(20)

        challenger = Character("Challenger", xp=100)
        challenger.set_ring("fire", 3)
        challenger.set_ring("air", 3)
        challenger.set_skill("iaijutsu", 3)
        challenger.set_roll_provider(c_rp)
        challenger.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        defender = Character("Defender", xp=100)
        defender.set_ring("fire", 3)
        defender.set_ring("air", 3)
        defender.set_skill("iaijutsu", 3)
        defender.set_roll_provider(d_rp)
        defender.set_strategy("duel_focus_or_strike", AlwaysStrikeDuelStrategy())

        duel_event = IaijutsuDuelEvent(challenger, defender)
        events_list = []
        try:
            for event in duel_event.play(None):
                events_list.append(event)
        except DuelEnded:
            pass

        strike_events = [e for e in events_list if isinstance(e, IaijutsuStrikeEvent)]
        self.assertTrue(len(strike_events) >= 2)
        for se in strike_events:
            self.assertEqual(challenger, se.challenger)
            self.assertEqual(defender, se.defender)
            self.assertTrue(hasattr(se, 'challenger_tn'))
            self.assertTrue(hasattr(se, 'defender_tn'))


class TestSurvivalDuelStrategy(unittest.TestCase):
    """Test the SurvivalDuelStrategy."""

    def _make_character(self, fire=3, iaijutsu=3):
        c = Character("Opponent")
        c.set_ring("fire", fire)
        c.set_skill("iaijutsu", iaijutsu)
        return c

    def test_focuses_when_tn_too_low(self):
        """Should focus when subject TN is well below opponent's expected roll."""
        strategy = SurvivalDuelStrategy()
        opponent = self._make_character(fire=4, iaijutsu=3)
        # opponent expected: 4k4 (fire=4) → 4*6=24 without context
        # subject (fire=1, iaijutsu=0) expected: 1*6=6 < opponent_tn=10 → can't hit
        # subject_tn=10 < opponent_expected=24 → focus
        state = DuelState(subject_tn=10, opponent=opponent, opponent_tn=10, focus_count=0)
        c = Character("Subject")
        result = strategy.recommend(c, state, None)
        self.assertEqual("focus", result)

    def test_strikes_when_tn_sufficient(self):
        """Should strike when subject TN is close to opponent's expected roll."""
        strategy = SurvivalDuelStrategy()
        opponent = self._make_character(fire=3, iaijutsu=3)
        # opponent expected: 3*6=18, subject expected: 3*6=18
        # my_expected (18) >= opponent_tn (10) → can hit
        # subject_tn (20) >= opponent_expected - 5 (13) → strike
        state = DuelState(subject_tn=20, opponent=opponent, opponent_tn=10, focus_count=0)
        c = Character("Subject")
        c.set_ring("fire", 3)
        c.set_skill("iaijutsu", 3)
        result = strategy.recommend(c, state, None)
        self.assertEqual("strike", result)

    def test_focuses_defensively_when_outmatched(self):
        """When character can't hit, focuses to minimize incoming damage."""
        strategy = SurvivalDuelStrategy()
        # Weak character (9k4 expected ~24) vs strong (10k6+mod expected ~40+)
        weak = Character("Weak")
        weak.set_ring("fire", 4)
        weak.set_skill("iaijutsu", 5)
        strong = Character("Strong")
        strong.set_ring("fire", 6)
        strong.set_skill("iaijutsu", 6)

        # Weak expected ~24, opponent_tn=40 → can't hit → focus defensively
        # strong is 10k8, no-context expected = 8*6 = 48
        # subject_tn=30 < 48 → focus
        state = DuelState(subject_tn=30, opponent=strong, opponent_tn=40, focus_count=2)
        result = strategy.recommend(weak, state, None)
        self.assertEqual("focus", result)

        # Once TN reaches opponent's expected roll (~48), strike even if can't hit
        state = DuelState(subject_tn=48, opponent=strong, opponent_tn=55, focus_count=4)
        result = strategy.recommend(weak, state, None)
        self.assertEqual("strike", result)

    def test_max_focuses_cap(self):
        """Should strike after reaching max focus count even if TN is low."""
        strategy = SurvivalDuelStrategy()
        opponent = self._make_character(fire=5, iaijutsu=5)
        state = DuelState(subject_tn=5, opponent=opponent, opponent_tn=10, focus_count=5)
        c = Character("Subject")
        result = strategy.recommend(c, state, None)
        self.assertEqual("strike", result)

    def test_fallback_when_no_event(self):
        """Should strike when no event info is available."""
        strategy = SurvivalDuelStrategy()
        c = Character("Subject")
        result = strategy.recommend(c, None, None)
        self.assertEqual("strike", result)

    def test_default_strategy_when_none(self):
        """Character with no duel strategy should use SurvivalDuelStrategy."""
        c_rp = CalvinistRollProvider()
        d_rp = CalvinistRollProvider()

        # Stance
        c_rp.put_skill_roll("iaijutsu", 15)
        d_rp.put_skill_roll("iaijutsu", 10)

        # Contested - challenger wins
        c_rp.put_skill_roll("iaijutsu", 30)
        d_rp.put_skill_roll("iaijutsu", 20)

        # With default survival strategy, characters with fire=3 iaijutsu=3
        # expected opponent roll = 3*6 = 18 (no context), so they focus
        # until TN >= 18-5 = 13 (can hit case).
        # Starting TN = 10, so at least one focus should happen.
        c_rp.put_skill_roll("iaijutsu", 20)
        d_rp.put_skill_roll("iaijutsu", 5)
        c_rp.put_damage_roll(20)

        challenger = Character("Challenger", xp=100)
        challenger.set_ring("fire", 3)
        challenger.set_ring("air", 3)
        challenger.set_skill("iaijutsu", 3)
        challenger.set_roll_provider(c_rp)
        # No strategy set — should use default SurvivalDuelStrategy

        defender = Character("Defender", xp=100)
        defender.set_ring("fire", 3)
        defender.set_ring("air", 3)
        defender.set_skill("iaijutsu", 3)
        defender.set_roll_provider(d_rp)

        duel_event = IaijutsuDuelEvent(challenger, defender)
        events_list = []
        try:
            for event in duel_event.play(None):
                events_list.append(event)
        except DuelEnded:
            pass

        # There should be at least one focus event from the survival strategy
        focus_events = [e for e in events_list if isinstance(e, IaijutsuFocusEvent)]
        self.assertTrue(len(focus_events) > 0, "Default survival strategy should focus at least once")

    def test_with_context_mean_roll(self):
        """Strategy should use context.mean_roll when available."""
        strategy = SurvivalDuelStrategy()
        opponent = self._make_character(fire=3, iaijutsu=3)

        context = EngineContext([
            Group("G1", [Character("C1")]),
            Group("G2", [Character("C2")]),
        ])
        context.initialize()

        # With context, the expected roll is context.mean_roll(rolled, kept)
        # which should be a real value from the probability tables
        state = DuelState(subject_tn=10, opponent=opponent, opponent_tn=10, focus_count=0)
        c = Character("Subject")
        result = strategy.recommend(c, state, context)
        # The result should be either "focus" or "strike" — we mainly test it doesn't crash
        self.assertIn(result, ["focus", "strike"])


class TestDuelFormatterDisplay(unittest.TestCase):
    """Test that the formatter displays focus/strike events with TNs."""

    def test_focus_event_formatted_with_tns(self):
        from web.adapters.detailed_formatter import DetailedEventFormatter
        challenger = Character("Kakita")
        defender = Character("Mirumoto")
        event = IaijutsuFocusEvent(challenger, challenger, defender, 15, 10)
        formatter = DetailedEventFormatter()
        lines = formatter.format_history([event])
        text = "\n".join(lines)
        self.assertIn("Kakita", text)
        self.assertIn("focuses", text)
        self.assertIn("15", text)
        self.assertIn("10", text)

    def test_strike_event_formatted(self):
        from web.adapters.detailed_formatter import DetailedEventFormatter
        challenger = Character("Kakita")
        defender = Character("Mirumoto")
        event = IaijutsuStrikeEvent(defender, challenger, defender, 15, 10)
        formatter = DetailedEventFormatter()
        lines = formatter.format_history([event])
        text = "\n".join(lines)
        self.assertIn("Mirumoto", text)
        self.assertIn("strike", text)
        self.assertIn("15", text)
        self.assertIn("10", text)


if __name__ == "__main__":
    unittest.main()
