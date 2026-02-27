#!/usr/bin/env python3

#
# test_merchant_school.py
#
# Unit tests for the Merchant School.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.log import logger
from simulation.schools import merchant_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestMerchantSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual("Merchant School", school.name())

    def test_extra_rolled(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["interrogation", "sincerity", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["discern honor", "oppose knowledge", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["interrogation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual("sincerity", school.ap_base_skill())

    def test_ap_skills(self):
        school = merchant_school.MerchantSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestMerchantAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        merchant = Character("Merchant")
        merchant.set_skill("sincerity", 5)
        school = merchant_school.MerchantSchool()
        school.apply_rank_three_ability(merchant)
        self.assertEqual("sincerity", merchant.ap_base_skill())
        self.assertTrue(merchant.can_spend_ap("attack"))
        self.assertTrue(merchant.can_spend_ap("wound check"))
        self.assertFalse(merchant.can_spend_ap("parry"))
        # AP = 2 * sincerity skill = 10
        self.assertEqual(10, merchant.ap())

    def test_ap_with_lower_skill(self):
        merchant = Character("Merchant")
        merchant.set_skill("sincerity", 2)
        school = merchant_school.MerchantSchool()
        school.apply_rank_three_ability(merchant)
        # AP = 2 * 2 = 4
        self.assertEqual(4, merchant.ap())


class TestMerchantFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        merchant = Character("Merchant")
        merchant.set_ring("water", 3)
        school = merchant_school.MerchantSchool()
        school.apply_rank_four_ability(merchant)
        # Ring raise: water should be +1
        self.assertEqual(4, merchant.ring("water"))
