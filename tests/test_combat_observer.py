"""Tests for CombatObserver and DetailedCombatEngine."""

import unittest
from unittest.mock import MagicMock

from simulation import events
from simulation.mechanics.roll import TestDice
from simulation.mechanics.roll_provider import DefaultRollProvider
from simulation.schools.kakita_school import ContestedIaijutsuAttackRolledEvent
from web.adapters.combat_observer import CombatObserver


def _make_character(name, lw=0, sw=0, max_sw=4, vp=3, max_vp=3, actions=None, crippled=False):
    """Create a mock character with standard accessors."""
    char = MagicMock()
    char.name.return_value = name
    char.lw.return_value = lw
    char.sw.return_value = sw
    char.max_sw.return_value = max_sw
    char.vp.return_value = vp
    char.max_vp.return_value = max_vp
    char.actions.return_value = actions if actions is not None else []
    char.crippled.return_value = crippled
    return char


def _make_provider_with_skill_roll(dice_values):
    """Create a DefaultRollProvider with TestDice that has a skill roll ready."""
    td = TestDice()
    td.extend(dice_values)
    provider = DefaultRollProvider(die_provider=td)
    return provider


class TestCombatObserverAttackRolled(unittest.TestCase):
    def test_annotates_attack_rolled_with_dice(self):
        observer = CombatObserver()
        td = TestDice()
        provider = DefaultRollProvider(die_provider=td)
        char = _make_character("Akodo")
        char.roll_provider.return_value = provider

        # Simulate a skill roll happening first
        td.extend([9, 8, 7, 6, 4, 3, 2])
        provider.get_skill_roll("attack", 7, 3)

        # Create event
        action = MagicMock()
        action.subject.return_value = char
        action.skill_roll_params.return_value = (7, 3, 5)
        target = _make_character("Bayushi")
        action.target.return_value = target
        target.tn_to_hit.return_value = 15
        event = events.AttackRolledEvent(action, 29)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual([9, 8, 7, 6, 4, 3, 2], event._detail_dice)
        self.assertEqual((7, 3, 5), event._detail_params)
        self.assertEqual(15, event._detail_tn)

    def test_no_annotation_when_no_last_roll(self):
        observer = CombatObserver()
        provider = DefaultRollProvider()
        char = _make_character("Akodo")
        char.roll_provider.return_value = provider

        action = MagicMock()
        action.subject.return_value = char
        action.skill_roll_params.return_value = (7, 3, 5)
        target = _make_character("Bayushi")
        action.target.return_value = target
        target.tn_to_hit.return_value = 15
        event = events.AttackRolledEvent(action, 29)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual([], event._detail_dice)


class TestCombatObserverParryRolled(unittest.TestCase):
    def test_annotates_parry_rolled_with_dice(self):
        observer = CombatObserver()
        td = TestDice()
        provider = DefaultRollProvider(die_provider=td)
        char = _make_character("Bayushi")
        char.roll_provider.return_value = provider

        # Simulate parry skill roll
        td.extend([8, 5, 3])
        provider.get_skill_roll("parry", 3, 2)

        action = MagicMock()
        action.subject.return_value = char
        action.skill_roll_params.return_value = (3, 2, 0)
        action.tn.return_value = 29
        event = events.ParryRolledEvent(action, 13)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual([8, 5, 3], event._detail_dice)
        self.assertEqual((3, 2, 0), event._detail_params)
        self.assertEqual(29, event._detail_tn)


class TestCombatObserverDamage(unittest.TestCase):
    def test_annotates_lw_damage_with_dice(self):
        observer = CombatObserver()
        td = TestDice()
        provider = DefaultRollProvider(die_provider=td)
        attacker = _make_character("Akodo")
        attacker.roll_provider.return_value = provider

        # Simulate damage roll
        td.extend([8, 7, 5, 4, 3, 1])
        provider.get_damage_roll(6, 2)

        target = _make_character("Bayushi", lw=0)
        event = events.LightWoundsDamageEvent(attacker, target, 15)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual([8, 7, 5, 4, 3, 1], event._detail_dice)
        self.assertEqual((6, 2), event._detail_params)


class TestCombatObserverWoundCheck(unittest.TestCase):
    def test_annotates_wound_check_with_dice(self):
        observer = CombatObserver()
        td = TestDice()
        provider = DefaultRollProvider(die_provider=td)
        char = _make_character("Bayushi")
        char.roll_provider.return_value = provider

        # Simulate wound check roll
        td.extend([9, 6, 5, 2])
        provider.get_wound_check_roll(4, 3)

        attacker = _make_character("Akodo")
        event = events.WoundCheckRolledEvent(char, attacker, 15, 20)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual([9, 6, 5, 2], event._detail_dice)
        self.assertEqual((4, 3), event._detail_params)


class TestCombatObserverInitiative(unittest.TestCase):
    def test_captures_initiative_on_first_new_phase(self):
        observer = CombatObserver()

        # Set up two characters with roll providers that have initiative data
        td1 = TestDice()
        provider1 = DefaultRollProvider(die_provider=td1)
        td1.extend([7, 4, 2])
        provider1.get_initiative_roll(3, 2)
        char1 = _make_character("Akodo", actions=[4, 7])
        char1.roll_provider.return_value = provider1

        td2 = TestDice()
        provider2 = DefaultRollProvider(die_provider=td2)
        td2.extend([6, 5, 1])
        provider2.get_initiative_roll(3, 2)
        char2 = _make_character("Bayushi", actions=[5, 6])
        char2.roll_provider.return_value = provider2

        context = MagicMock()
        context.characters.return_value = [char1, char2]

        # First, observe a NewRoundEvent to reset tracking
        round_event = events.NewRoundEvent(1)
        observer.on_event(round_event, context)

        # Then first NewPhaseEvent of the round
        phase_event = events.NewPhaseEvent(0)
        observer.on_event(phase_event, context)

        self.assertTrue(hasattr(phase_event, "_detail_initiative"))
        init_data = phase_event._detail_initiative
        self.assertIn("Akodo", init_data)
        self.assertEqual([2, 4, 7], init_data["Akodo"]["all_dice"])
        self.assertEqual([4, 7], init_data["Akodo"]["actions"])

    def test_no_initiative_on_second_phase(self):
        observer = CombatObserver()

        char1 = _make_character("Akodo", actions=[4, 7])
        provider1 = DefaultRollProvider()
        char1.roll_provider.return_value = provider1

        context = MagicMock()
        context.characters.return_value = [char1]

        round_event = events.NewRoundEvent(1)
        observer.on_event(round_event, context)

        phase0 = events.NewPhaseEvent(0)
        observer.on_event(phase0, context)

        phase1 = events.NewPhaseEvent(1)
        observer.on_event(phase1, context)

        self.assertFalse(hasattr(phase1, "_detail_initiative"))


class TestCombatObserverStatus(unittest.TestCase):
    def test_captures_status_on_new_phase(self):
        observer = CombatObserver()

        char1 = _make_character("Akodo", lw=10, sw=1, max_sw=4, vp=2, max_vp=3, actions=[7], crippled=False)
        char1.roll_provider.return_value = DefaultRollProvider()
        char2 = _make_character("Bayushi", lw=5, sw=0, max_sw=4, vp=1, max_vp=2, actions=[5, 6], crippled=True)
        char2.roll_provider.return_value = DefaultRollProvider()

        context = MagicMock()
        context.characters.return_value = [char1, char2]

        event = events.NewPhaseEvent(3)
        observer.on_event(event, context)

        self.assertTrue(hasattr(event, "_detail_status"))
        status = event._detail_status
        self.assertEqual(10, status["Akodo"]["lw"])
        self.assertEqual(1, status["Akodo"]["sw"])
        self.assertEqual(4, status["Akodo"]["max_sw"])
        self.assertEqual(2, status["Akodo"]["vp"])
        self.assertEqual(3, status["Akodo"]["max_vp"])
        self.assertEqual([7], status["Akodo"]["actions"])
        self.assertFalse(status["Akodo"]["crippled"])
        self.assertTrue(status["Bayushi"]["crippled"])


class TestCombatObserverTakeAttackStatus(unittest.TestCase):
    def test_annotates_take_attack_with_status(self):
        observer = CombatObserver()

        char1 = _make_character("Akodo", lw=5, sw=0, max_sw=4, vp=2, max_vp=3, actions=[4, 7])
        char2 = _make_character("Bayushi", lw=0, sw=0, max_sw=4, vp=1, max_vp=2, actions=[5, 6])

        context = MagicMock()
        context.characters.return_value = [char1, char2]

        action = MagicMock()
        action.subject.return_value = char1
        action.target.return_value = char2
        event = events.TakeAttackActionEvent(action)

        observer.on_event(event, context)

        self.assertTrue(hasattr(event, "_detail_status"))
        status = event._detail_status
        self.assertEqual(5, status["Akodo"]["lw"])
        self.assertEqual(2, status["Akodo"]["vp"])
        self.assertEqual(0, status["Bayushi"]["lw"])
        self.assertEqual(1, status["Bayushi"]["vp"])


class TestCombatObserverAttackSucceeded(unittest.TestCase):
    def test_annotates_attack_succeeded_with_extra_dice_and_damage_params(self):
        observer = CombatObserver()
        action = MagicMock()
        action.calculate_extra_damage_dice.return_value = 2
        action.damage_roll_params.return_value = (6, 2, 0)
        action.skill_roll.return_value = 29
        action.tn.return_value = 15
        event = events.AttackSucceededEvent(action)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual(2, event._detail_extra_dice)
        self.assertEqual((6, 2, 0), event._detail_damage_params)
        self.assertEqual(29, event._detail_skill_roll)
        self.assertEqual(15, event._detail_tn)

    def test_annotates_attack_succeeded_zero_extra_dice(self):
        observer = CombatObserver()
        action = MagicMock()
        action.calculate_extra_damage_dice.return_value = 0
        action.damage_roll_params.return_value = (4, 2, 0)
        action.skill_roll.return_value = 16
        action.tn.return_value = 15
        event = events.AttackSucceededEvent(action)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual(0, event._detail_extra_dice)
        self.assertEqual((4, 2, 0), event._detail_damage_params)


class TestCombatObserverAttackFailed(unittest.TestCase):
    def test_annotates_attack_failed_with_skill_roll_and_tn(self):
        observer = CombatObserver()
        action = MagicMock()
        action.skill_roll.return_value = 12
        action.tn.return_value = 20
        event = events.AttackFailedEvent(action)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual(12, event._detail_skill_roll)
        self.assertEqual(20, event._detail_tn)


class TestCombatObserverKeepLightWounds(unittest.TestCase):
    def test_annotates_keep_lw_with_lw_total(self):
        observer = CombatObserver()
        char = _make_character("Bayushi", lw=30)
        attacker = _make_character("Akodo")
        event = events.KeepLightWoundsEvent(char, attacker, 30)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual(30, event._detail_lw_total)


class TestCombatObserverTakeSeriousWound(unittest.TestCase):
    def test_annotates_take_sw_with_lw_total(self):
        observer = CombatObserver()
        char = _make_character("Bayushi", lw=30)
        attacker = _make_character("Akodo")
        event = events.TakeSeriousWoundEvent(char, attacker, 30)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual(30, event._detail_lw_total)


class TestCombatObserverLightWoundsDamageAfter(unittest.TestCase):
    def test_annotates_lw_damage_with_lw_after(self):
        observer = CombatObserver()
        td = TestDice()
        provider = DefaultRollProvider(die_provider=td)
        attacker = _make_character("Akodo")
        attacker.roll_provider.return_value = provider

        td.extend([8, 7, 5, 4, 3, 1])
        provider.get_damage_roll(6, 2)

        # Target currently has 15 LW, taking 15 more
        target = _make_character("Bayushi", lw=15)
        event = events.LightWoundsDamageEvent(attacker, target, 15)

        context = MagicMock()
        observer.on_event(event, context)

        # lw_after should be current lw + new damage
        self.assertEqual(30, event._detail_lw_after)


class TestCombatObserverContestedIaijutsu(unittest.TestCase):
    def test_annotates_contested_iaijutsu_rolled_with_dice(self):
        observer = CombatObserver()
        td = TestDice()
        provider = DefaultRollProvider(die_provider=td)
        char = _make_character("Kakita")
        char.roll_provider.return_value = provider

        # Simulate a skill roll happening first (no 10s to avoid explosion)
        td.extend([9, 8, 7, 6, 5, 4, 3, 2, 1, 1])
        provider.get_skill_roll("iaijutsu", 10, 6)

        action = MagicMock()
        action.subject.return_value = char
        action.skill_roll_params.return_value = (10, 6, 5)
        event = ContestedIaijutsuAttackRolledEvent(action)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual([9, 8, 7, 6, 5, 4, 3, 2, 1, 1], event._detail_dice)
        self.assertEqual((10, 6, 5), event._detail_params)

    def test_no_annotation_when_no_last_skill_roll(self):
        observer = CombatObserver()
        provider = DefaultRollProvider()
        char = _make_character("Kakita")
        char.roll_provider.return_value = provider

        action = MagicMock()
        action.subject.return_value = char
        action.skill_roll_params.return_value = (10, 6, 5)
        event = ContestedIaijutsuAttackRolledEvent(action)

        context = MagicMock()
        observer.on_event(event, context)

        self.assertEqual([], event._detail_dice)


class TestDetailedCombatEngine(unittest.TestCase):
    def test_calls_observer_before_processing(self):
        from simulation.character import Character
        from simulation.context import EngineContext
        from simulation.groups import Group
        from web.adapters.combat_observer import DetailedCombatEngine
        char1 = Character("A")
        char1.set_ring("fire", 3)
        char1.set_ring("water", 3)
        char1.set_ring("earth", 3)
        char1.set_ring("air", 3)
        char1.set_ring("void", 3)
        char1.set_skill("attack", 3)

        char2 = Character("B")
        char2.set_ring("fire", 3)
        char2.set_ring("water", 3)
        char2.set_ring("earth", 3)
        char2.set_ring("air", 3)
        char2.set_ring("void", 3)
        char2.set_skill("attack", 3)

        group1 = Group("G1", [char1])
        group2 = Group("G2", [char2])
        context = EngineContext([group1, group2])
        context.initialize()

        # Track observed events
        observed = []
        observer = MagicMock()
        observer.on_event = lambda event, ctx: observed.append(event.name)

        engine = DetailedCombatEngine(context, observer)

        # Fire a single event
        event = events.NewRoundEvent(1)
        engine.event(event)

        # Observer should have been called (new_round will be in the list)
        self.assertIn("new_round", observed)


if __name__ == "__main__":
    unittest.main()
