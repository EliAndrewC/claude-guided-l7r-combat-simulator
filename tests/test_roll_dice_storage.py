"""Tests for dice storage on Roll/InitiativeRoll and last roll on RollProvider."""

import unittest

from simulation.mechanics.roll import CalvinistDice, InitiativeRoll, Roll
from simulation.mechanics.roll_provider import DefaultRollProvider
from simulation.professions import Profession, WaveManRoll, WaveManRollProvider
from simulation.schools.kakita_school import KakitaRollProvider


class TestRollDiceStorage(unittest.TestCase):
    def setUp(self):
        self.test_dice = CalvinistDice()

    def test_roll_stores_dice(self):
        self.test_dice.extend([7, 4, 2, 9])
        roll = Roll(4, 3, die_provider=self.test_dice)
        result = roll.roll()
        self.assertEqual([9, 7, 4, 2], roll.dice())
        self.assertEqual(9 + 7 + 4, result)

    def test_dice_returns_empty_list_before_roll(self):
        roll = Roll(3, 2, die_provider=self.test_dice)
        self.assertEqual([], roll.dice())

    def test_dice_sorted_descending(self):
        self.test_dice.extend([1, 5, 3])
        roll = Roll(3, 2, die_provider=self.test_dice)
        roll.roll()
        self.assertEqual([5, 3, 1], roll.dice())

    def test_dice_length_equals_rolled(self):
        self.test_dice.extend([6, 3, 8, 2, 5])
        roll = Roll(5, 3, die_provider=self.test_dice)
        roll.roll()
        self.assertEqual(5, len(roll.dice()))

    def test_initiative_roll_stores_all_dice(self):
        self.test_dice.extend([3, 7, 5])
        roll = InitiativeRoll(3, 2, die_provider=self.test_dice)
        roll.roll()
        self.assertEqual([3, 5, 7], roll.all_dice())

    def test_initiative_all_dice_empty_before_roll(self):
        roll = InitiativeRoll(3, 2, die_provider=self.test_dice)
        self.assertEqual([], roll.all_dice())

    def test_initiative_all_dice_length_equals_rolled(self):
        self.test_dice.extend([4, 8, 2, 6])
        roll = InitiativeRoll(4, 3, die_provider=self.test_dice)
        roll.roll()
        self.assertEqual(4, len(roll.all_dice()))


class TestDefaultRollProviderLastRoll(unittest.TestCase):
    def setUp(self):
        self.test_dice = CalvinistDice()
        self.provider = DefaultRollProvider(die_provider=self.test_dice)

    def test_last_skill_roll_none_initially(self):
        self.assertIsNone(self.provider.last_skill_roll())

    def test_last_skill_roll_after_get_skill_roll(self):
        self.test_dice.extend([7, 4, 2])
        self.provider.get_skill_roll("attack", 3, 2)
        last = self.provider.last_skill_roll()
        self.assertIsNotNone(last)
        self.assertIsInstance(last, Roll)
        self.assertEqual(3, len(last.dice()))

    def test_last_damage_roll_none_initially(self):
        self.assertIsNone(self.provider.last_damage_roll())

    def test_last_damage_roll_after_get_damage_roll(self):
        self.test_dice.extend([5, 8, 3])
        self.provider.get_damage_roll(3, 2)
        last = self.provider.last_damage_roll()
        self.assertIsNotNone(last)
        self.assertIsInstance(last, Roll)
        self.assertEqual(3, len(last.dice()))

    def test_last_wound_check_roll_none_initially(self):
        self.assertIsNone(self.provider.last_wound_check_roll())

    def test_last_wound_check_roll_after_get_wound_check_roll(self):
        self.test_dice.extend([9, 6, 5, 2])
        self.provider.get_wound_check_roll(4, 3)
        last = self.provider.last_wound_check_roll()
        self.assertIsNotNone(last)
        self.assertIsInstance(last, Roll)
        self.assertEqual(4, len(last.dice()))

    def test_last_initiative_roll_none_initially(self):
        self.assertIsNone(self.provider.last_initiative_roll())

    def test_last_initiative_roll_after_get_initiative_roll(self):
        self.test_dice.extend([7, 4, 2])
        self.provider.get_initiative_roll(3, 2)
        last = self.provider.last_initiative_roll()
        self.assertIsNotNone(last)
        self.assertIsInstance(last, InitiativeRoll)
        self.assertEqual(3, len(last.all_dice()))


class TestKakitaRollProviderLastRoll(unittest.TestCase):
    def test_last_initiative_roll_none_initially(self):
        provider = KakitaRollProvider()
        self.assertIsNone(provider.last_initiative_roll())

    def test_last_initiative_roll_after_get_initiative_roll(self):
        test_dice = CalvinistDice()
        provider = KakitaRollProvider(die_provider=test_dice)
        test_dice.extend([3, 7, 5])
        provider.get_initiative_roll(3, 2)
        last = provider.last_initiative_roll()
        self.assertIsNotNone(last)
        self.assertIsInstance(last, InitiativeRoll)
        self.assertEqual(3, len(last.all_dice()))


class TestDefaultRollProviderInfoDicts(unittest.TestCase):
    """Tests for the last_*_info() methods that return dicts with rolled/kept/dice."""

    def setUp(self):
        self.test_dice = CalvinistDice()
        self.provider = DefaultRollProvider(die_provider=self.test_dice)

    def test_last_skill_info_none_initially(self):
        self.assertIsNone(self.provider.last_skill_info())

    def test_last_skill_info_after_roll(self):
        self.test_dice.extend([9, 7, 4])
        self.provider.get_skill_roll("attack", 3, 2)
        info = self.provider.last_skill_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertEqual([9, 7, 4], info["dice"])

    def test_last_damage_info_none_initially(self):
        self.assertIsNone(self.provider.last_damage_info())

    def test_last_damage_info_after_roll(self):
        self.test_dice.extend([8, 5, 3])
        self.provider.get_damage_roll(3, 2)
        info = self.provider.last_damage_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertEqual([8, 5, 3], info["dice"])

    def test_last_wound_check_info_none_initially(self):
        self.assertIsNone(self.provider.last_wound_check_info())

    def test_last_wound_check_info_after_roll(self):
        self.test_dice.extend([9, 6, 5, 2])
        self.provider.get_wound_check_roll(4, 3)
        info = self.provider.last_wound_check_info()
        self.assertIsNotNone(info)
        self.assertEqual(4, info["rolled"])
        self.assertEqual(3, info["kept"])
        self.assertEqual([9, 6, 5, 2], info["dice"])

    def test_last_initiative_info_none_initially(self):
        self.assertIsNone(self.provider.last_initiative_info())

    def test_last_initiative_info_after_roll(self):
        self.test_dice.extend([7, 4, 2])
        self.provider.get_initiative_roll(3, 2)
        info = self.provider.last_initiative_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertEqual([2, 4, 7], info["all_dice"])


class TestKakitaRollProviderInfoDict(unittest.TestCase):
    def test_last_initiative_info_none_initially(self):
        provider = KakitaRollProvider()
        self.assertIsNone(provider.last_initiative_info())

    def test_last_initiative_info_after_roll(self):
        test_dice = CalvinistDice()
        provider = KakitaRollProvider(die_provider=test_dice)
        test_dice.extend([3, 7, 5])
        provider.get_initiative_roll(3, 2)
        info = provider.last_initiative_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertIsInstance(info["all_dice"], list)
        self.assertEqual(3, len(info["all_dice"]))


class TestWaveManRollDiceStorage(unittest.TestCase):
    """Tests that WaveManRoll stores dice like Roll does."""

    def setUp(self):
        self.test_dice = CalvinistDice()

    def test_waveman_roll_stores_dice(self):
        self.test_dice.extend([7, 4, 2])
        roll = WaveManRoll(3, 2, die_provider=self.test_dice, always_explode=0)
        result = roll.roll()
        self.assertEqual([7, 4, 2], roll.dice())
        self.assertEqual(7 + 4, result)

    def test_waveman_roll_dice_empty_before_roll(self):
        roll = WaveManRoll(3, 2, die_provider=self.test_dice, always_explode=0)
        self.assertEqual([], roll.dice())

    def test_waveman_roll_dice_sorted_descending(self):
        self.test_dice.extend([1, 5, 3])
        roll = WaveManRoll(3, 2, die_provider=self.test_dice, always_explode=0)
        roll.roll()
        self.assertEqual([5, 3, 1], roll.dice())


class TestWaveManRollProviderInfoDicts(unittest.TestCase):
    """Tests that WaveManRollProvider stores _last_skill_info."""

    def setUp(self):
        self.test_dice = CalvinistDice()
        self.profession = Profession()
        self.profession.take_ability("crippled bonus")
        self.provider = WaveManRollProvider(self.profession, die_provider=self.test_dice)

    def test_last_skill_info_none_initially(self):
        self.assertIsNone(self.provider.last_skill_info())

    def test_last_skill_info_after_roll(self):
        self.test_dice.extend([9, 7, 4])
        self.provider.get_skill_roll("attack", 3, 2)
        info = self.provider.last_skill_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertEqual([9, 7, 4], info["dice"])

    def test_last_skill_info_dice_length(self):
        self.test_dice.extend([6, 3, 8, 2, 5])
        self.provider.get_skill_roll("attack", 5, 3)
        info = self.provider.last_skill_info()
        self.assertEqual(5, len(info["dice"]))


if __name__ == "__main__":
    unittest.main()
