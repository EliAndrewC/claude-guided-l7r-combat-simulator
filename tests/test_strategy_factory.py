#!/usr/bin/env python3

#
# test_strategy_factory.py
#
# Unit tests for strategy factory name lookups.
#

import unittest

from simulation.schools.kakita_school import (
    KakitaAttackStrategy,
    KakitaAttackStrategy05,
    KakitaInterruptAttackStrategy,
    KakitaInterruptAttackStrategy05,
    KakitaNoVPAttackStrategy,
    KakitaNoVPInterruptAttackStrategy,
    KakitaParryStrategy,
)
from simulation.strategies.base import (
    AlwaysAttackActionStrategy,
    AlwaysKeepLightWoundsStrategy,
    AlwaysParryStrategy,
    HoldOneActionStrategy,
    KeepLightWoundsStrategy,
    NeverKeepLightWoundsStrategy,
    NeverParryStrategy,
    PlainAttackStrategy,
    ReluctantParryStrategy,
    StingyPlainAttackStrategy,
    StingyWoundCheckStrategy,
    UniversalAttackStrategy,
    WoundCheckStrategy,
    WoundCheckStrategy02,
    WoundCheckStrategy04,
    WoundCheckStrategy05,
    WoundCheckStrategy08,
)
from simulation.strategies.factory import get_strategy


class TestGetStrategy(unittest.TestCase):
    """Test get_strategy returns the correct strategy type for every name."""

    def test_always_attack_action_strategy(self):
        self.assertIsInstance(get_strategy("AlwaysAttackActionStrategy"), AlwaysAttackActionStrategy)

    def test_always_keep_light_wounds_strategy(self):
        self.assertIsInstance(get_strategy("AlwaysKeepLightWoundsStrategy"), AlwaysKeepLightWoundsStrategy)

    def test_always_parry_strategy(self):
        self.assertIsInstance(get_strategy("AlwaysParryStrategy"), AlwaysParryStrategy)

    def test_hold_one_action_strategy(self):
        self.assertIsInstance(get_strategy("HoldOneActionStrategy"), HoldOneActionStrategy)

    def test_kakita_attack_strategy(self):
        self.assertIsInstance(get_strategy("KakitaAttackStrategy"), KakitaAttackStrategy)

    def test_kakita_attack_strategy_05(self):
        self.assertIsInstance(get_strategy("KakitaAttackStrategy05"), KakitaAttackStrategy05)

    def test_kakita_interrupt_attack_strategy(self):
        self.assertIsInstance(get_strategy("KakitaInterruptAttackStrategy"), KakitaInterruptAttackStrategy)

    def test_kakita_interrupt_attack_strategy_05(self):
        self.assertIsInstance(get_strategy("KakitaInterruptAttackStrategy05"), KakitaInterruptAttackStrategy05)

    def test_kakita_no_vp_attack_strategy(self):
        self.assertIsInstance(get_strategy("KakitaNoVPAttackStrategy"), KakitaNoVPAttackStrategy)

    def test_kakita_no_vp_interrupt_attack_strategy(self):
        self.assertIsInstance(get_strategy("KakitaNoVPInterruptAttackStrategy"), KakitaNoVPInterruptAttackStrategy)

    def test_kakita_parry_strategy(self):
        self.assertIsInstance(get_strategy("KakitaParryStrategy"), KakitaParryStrategy)

    def test_keep_light_wounds_strategy(self):
        self.assertIsInstance(get_strategy("KeepLightWoundsStrategy"), KeepLightWoundsStrategy)

    def test_never_keep_light_wounds_strategy(self):
        self.assertIsInstance(get_strategy("NeverKeepLightWoundsStrategy"), NeverKeepLightWoundsStrategy)

    def test_never_parry_strategy(self):
        self.assertIsInstance(get_strategy("NeverParryStrategy"), NeverParryStrategy)

    def test_plain_attack_strategy(self):
        self.assertIsInstance(get_strategy("PlainAttackStrategy"), PlainAttackStrategy)

    def test_reluctant_parry_strategy(self):
        self.assertIsInstance(get_strategy("ReluctantParryStrategy"), ReluctantParryStrategy)

    def test_stingy_plain_attack_strategy(self):
        self.assertIsInstance(get_strategy("StingyPlainAttackStrategy"), StingyPlainAttackStrategy)

    def test_stingy_wound_check_strategy(self):
        self.assertIsInstance(get_strategy("StingyWoundCheckStrategy"), StingyWoundCheckStrategy)

    def test_universal_attack_strategy(self):
        self.assertIsInstance(get_strategy("UniversalAttackStrategy"), UniversalAttackStrategy)

    def test_wound_check_strategy(self):
        self.assertIsInstance(get_strategy("WoundCheckStrategy"), WoundCheckStrategy)

    def test_wound_check_strategy_02(self):
        self.assertIsInstance(get_strategy("WoundCheckStrategy02"), WoundCheckStrategy02)

    def test_wound_check_strategy_04(self):
        self.assertIsInstance(get_strategy("WoundCheckStrategy04"), WoundCheckStrategy04)

    def test_wound_check_strategy_05(self):
        self.assertIsInstance(get_strategy("WoundCheckStrategy05"), WoundCheckStrategy05)

    def test_wound_check_strategy_08(self):
        self.assertIsInstance(get_strategy("WoundCheckStrategy08"), WoundCheckStrategy08)

    def test_invalid_strategy_raises(self):
        with self.assertRaises(ValueError):
            get_strategy("NonExistentStrategy")


if __name__ == "__main__":
    unittest.main()
