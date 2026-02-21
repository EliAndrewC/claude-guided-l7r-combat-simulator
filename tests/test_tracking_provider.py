"""Tests for TrackingRollProvider wrapper.

These tests verify that dice data is captured regardless of the underlying
provider implementation (DefaultRollProvider, KakitaRollProvider,
WaveManRollProvider, etc).
"""

import unittest

from simulation.mechanics.roll import TestDice
from simulation.mechanics.roll_provider import DefaultRollProvider
from simulation.professions import Profession, WaveManRollProvider
from simulation.schools.kakita_school import KAKITA_ROLL_PROVIDER, KakitaRollProvider
from web.adapters.combat_observer import TrackingRollProvider


class _NoInfoRollProvider(DefaultRollProvider):
    """Provider that doesn't store roll info, simulating older/custom providers.

    Forces TrackingRollProvider to fall back to recorded dice.
    """

    def last_skill_info(self):
        return None

    def last_damage_info(self):
        return None

    def last_wound_check_info(self):
        return None

    def last_initiative_info(self):
        return None


class TestTrackingRollProviderWithDefault(unittest.TestCase):
    """TrackingRollProvider wrapping a DefaultRollProvider."""

    def setUp(self):
        self.td = TestDice()
        self.inner = DefaultRollProvider(die_provider=self.td)
        self.provider = TrackingRollProvider(self.inner)

    def test_skill_roll_captures_dice(self):
        self.td.extend([9, 7, 4])
        result = self.provider.get_skill_roll("attack", 3, 2)
        info = self.provider.last_skill_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertTrue(len(info["dice"]) > 0)
        self.assertEqual(result, sum(sorted(info["dice"], reverse=True)[:2]))

    def test_damage_roll_captures_dice(self):
        self.td.extend([8, 5, 3])
        self.provider.get_damage_roll(3, 2)
        info = self.provider.last_damage_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertTrue(len(info["dice"]) > 0)

    def test_wound_check_roll_captures_dice(self):
        self.td.extend([9, 6, 5, 2])
        self.provider.get_wound_check_roll(4, 3)
        info = self.provider.last_wound_check_info()
        self.assertIsNotNone(info)
        self.assertEqual(4, info["rolled"])
        self.assertEqual(3, info["kept"])
        self.assertTrue(len(info["dice"]) > 0)

    def test_initiative_roll_captures_dice(self):
        self.td.extend([7, 4, 2])
        self.provider.get_initiative_roll(3, 2)
        info = self.provider.last_initiative_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertTrue(len(info["all_dice"]) > 0)

    def test_info_none_before_any_roll(self):
        self.assertIsNone(self.provider.last_skill_info())
        self.assertIsNone(self.provider.last_damage_info())
        self.assertIsNone(self.provider.last_wound_check_info())
        self.assertIsNone(self.provider.last_initiative_info())

    def test_delegates_to_inner_provider(self):
        """The inner provider's roll result should be returned."""
        self.td.extend([9, 7, 4])
        result = self.provider.get_skill_roll("attack", 3, 2)
        # Roll should be sum of top 2 = 9 + 7 = 16
        self.assertEqual(16, result)


class TestTrackingRollProviderWithWaveMan(unittest.TestCase):
    """TrackingRollProvider wrapping a WaveManRollProvider.

    WaveManRollProvider.get_skill_roll() overrides the parent without
    storing _last_skill_info. The wrapper must still capture dice.
    """

    def setUp(self):
        self.td = TestDice()
        self.profession = Profession()
        self.profession.take_ability("crippled bonus")
        self.inner = WaveManRollProvider(self.profession, die_provider=self.td)
        self.provider = TrackingRollProvider(self.inner)

    def test_skill_roll_captures_dice_with_waveman(self):
        """This is the key test - WaveMan's get_skill_roll doesn't store info."""
        self.td.extend([9, 7, 4])
        self.provider.get_skill_roll("attack", 3, 2)
        info = self.provider.last_skill_info()
        self.assertIsNotNone(info, "TrackingRollProvider must capture skill info even with WaveManRollProvider")
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertTrue(len(info["dice"]) > 0)

    def test_damage_roll_captures_dice_with_waveman(self):
        self.td.extend([8, 5, 3])
        self.provider.get_damage_roll(3, 2)
        info = self.provider.last_damage_info()
        self.assertIsNotNone(info)
        self.assertTrue(len(info["dice"]) > 0)

    def test_preserves_waveman_behavior(self):
        """The WaveMan's crippled bonus behavior should not be lost."""
        self.td.extend([9, 7, 4])
        # WaveManRollProvider uses WaveManRoll with always_explode from profession
        # Just verify the roll completes without error and returns a reasonable value
        result = self.provider.get_skill_roll("attack", 3, 2)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)


class TestTrackingRollProviderWithKakita(unittest.TestCase):
    """TrackingRollProvider wrapping a KakitaRollProvider."""

    def setUp(self):
        self.provider = TrackingRollProvider(KakitaRollProvider())

    def test_initiative_roll_captures_dice_with_kakita(self):
        """Kakita uses special die provider for initiative."""
        self.provider.get_initiative_roll(3, 2)
        info = self.provider.last_initiative_info()
        self.assertIsNotNone(info)
        self.assertEqual(3, info["rolled"])
        self.assertEqual(2, info["kept"])
        self.assertTrue(len(info["all_dice"]) > 0)

    def test_kakita_initiative_dice_count_matches_rolled(self):
        """Kakita initiative should capture exactly 'rolled' dice."""
        self.provider.get_initiative_roll(7, 5)
        info = self.provider.last_initiative_info()
        self.assertEqual(7, len(info["all_dice"]),
                         f"Expected 7 dice, got {info['all_dice']}")

    def test_kakita_initiative_dice_in_range(self):
        """Kakita initiative dice should be in [0, 9] range."""
        self.provider.get_initiative_roll(5, 3)
        info = self.provider.last_initiative_info()
        for die in info["all_dice"]:
            self.assertGreaterEqual(die, 0)
            self.assertLessEqual(die, 9)

    def test_kakita_initiative_dice_sorted_ascending(self):
        """Kakita initiative dice should be sorted ascending."""
        self.provider.get_initiative_roll(5, 3)
        info = self.provider.last_initiative_info()
        self.assertEqual(info["all_dice"], sorted(info["all_dice"]))

    def test_kakita_singleton_initiative_captures_dice(self):
        """Test with the actual KAKITA_ROLL_PROVIDER singleton."""
        provider = TrackingRollProvider(KAKITA_ROLL_PROVIDER)
        provider.get_initiative_roll(7, 5)
        info = provider.last_initiative_info()
        self.assertIsNotNone(info)
        self.assertEqual(7, len(info["all_dice"]),
                         f"Kakita singleton should capture 7 dice, got: {info['all_dice']}")

    def test_kakita_initiative_captured_without_inner_info(self):
        """Dice must be captured even if inner doesn't store _last_initiative_info.

        This simulates the case where the Streamlit process has an old cached
        version of KakitaRollProvider that doesn't store initiative info.
        The TrackingRollProvider must capture dice independently by intercepting
        at the KAKITA_INITIATIVE_DIE_PROVIDER level.
        """
        inner = KakitaRollProvider()
        provider = TrackingRollProvider(inner)

        # Simulate old code that doesn't store _last_initiative_info
        inner.last_initiative_info = lambda: None

        provider.get_initiative_roll(5, 3)
        info = provider.last_initiative_info()
        self.assertEqual(5, len(info["all_dice"]),
                         f"Should capture 5 dice even without inner info, got: {info['all_dice']}")
        for die in info["all_dice"]:
            self.assertGreaterEqual(die, 0)
            self.assertLessEqual(die, 9)


class TestTrackingRollProviderDiceSorting(unittest.TestCase):
    """Verify dice are always sorted in info dicts, even via recorded fallback.

    Uses _NoInfoRollProvider to force the recorded-dice fallback path,
    where dice arrive in roll order (unsorted). TrackingRollProvider must
    sort them so that sum(dice[:kept]) gives the correct (highest-k) result.
    """

    def setUp(self):
        self.td = TestDice()
        self.inner = _NoInfoRollProvider(die_provider=self.td)
        self.provider = TrackingRollProvider(self.inner)

    def test_skill_dice_sorted_descending(self):
        self.td.extend([2, 9, 4, 7, 6])
        self.provider.get_skill_roll("attack", 5, 3)
        info = self.provider.last_skill_info()
        self.assertEqual(info["dice"], sorted(info["dice"], reverse=True),
                         f"Skill dice should be sorted descending, got: {info['dice']}")

    def test_damage_dice_sorted_descending(self):
        self.td.extend([3, 8, 1, 6])
        self.provider.get_damage_roll(4, 2)
        info = self.provider.last_damage_info()
        self.assertEqual(info["dice"], sorted(info["dice"], reverse=True),
                         f"Damage dice should be sorted descending, got: {info['dice']}")

    def test_wound_check_dice_sorted_descending(self):
        self.td.extend([5, 2, 9, 3])
        self.provider.get_wound_check_roll(4, 3)
        info = self.provider.last_wound_check_info()
        self.assertEqual(info["dice"], sorted(info["dice"], reverse=True),
                         f"Wound check dice should be sorted descending, got: {info['dice']}")

    def test_initiative_dice_sorted_ascending(self):
        self.td.extend([7, 2, 5])
        self.provider.get_initiative_roll(3, 2)
        info = self.provider.last_initiative_info()
        self.assertEqual(info["all_dice"], sorted(info["all_dice"]),
                         f"Initiative dice should be sorted ascending, got: {info['all_dice']}")

    def test_kept_sum_correct_with_unsorted_input(self):
        """sum(dice[:kept]) should equal sum of highest 'kept' dice."""
        self.td.extend([2, 9, 4, 7, 6])
        result = self.provider.get_skill_roll("attack", 5, 3)
        info = self.provider.last_skill_info()
        dice = info["dice"]
        # dice[:3] should be the top 3 after sorting: [9, 7, 6]
        kept_sum = sum(dice[:3])
        self.assertEqual(kept_sum, 9 + 7 + 6,
                         f"Top 3 dice should sum to 22, got {kept_sum} from {dice}")
        self.assertEqual(result, kept_sum)

    def test_damage_kept_sum_correct(self):
        """Damage dice[:kept] sum should equal sum of highest kept dice."""
        self.td.extend([1, 8, 3, 7])
        result = self.provider.get_damage_roll(4, 2)
        info = self.provider.last_damage_info()
        dice = info["dice"]
        kept_sum = sum(dice[:2])
        self.assertEqual(kept_sum, 8 + 7,
                         f"Top 2 dice should sum to 15, got {kept_sum} from {dice}")
        self.assertEqual(result, kept_sum)


if __name__ == "__main__":
    unittest.main()
