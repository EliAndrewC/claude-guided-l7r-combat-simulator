#!/usr/bin/env python3

#
# test_wound_check_provider.py
#
# Unit tests for L7R combat simulator wound check provider module
#

import unittest

from simulation.wound_check_provider import DefaultWoundCheckProvider

provider = DefaultWoundCheckProvider()

class TestWoundCheckProvider(unittest.TestCase):
  def test_wound_check(self):
    # roll >= lw: 0 SW
    self.assertEqual(0, provider.wound_check(31, 30))
    self.assertEqual(0, provider.wound_check(30, 30))
    # 0 < sw - roll < 10: 1 SW
    self.assertEqual(1, provider.wound_check(21, 30))
    # 10 < sw - roll < 20: 2 SW
    self.assertEqual(2, provider.wound_check(20, 30))
    self.assertEqual(2, provider.wound_check(11, 30))
    # 20 < sw - roll < 30: 3 SW
    self.assertEqual(3, provider.wound_check(10, 30))
    self.assertEqual(3, provider.wound_check(1, 30))


if (__name__ == '__main__'):
  unittest.main()

