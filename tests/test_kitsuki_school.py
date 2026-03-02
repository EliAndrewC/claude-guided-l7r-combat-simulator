#!/usr/bin/env python3

#
# test_kitsuki_school.py
#
# Unit tests for the Kitsuki Magistrate School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import kitsuki_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestKitsukiSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual("Kitsuki Magistrate School", school.name())

    def test_extra_rolled(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["interrogation", "investigation", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["discern honor", "iaijutsu", "presence"], school.school_knacks())

    def test_free_raise_skills(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["interrogation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual("investigation", school.ap_base_skill())

    def test_ap_skills(self):
        school = kitsuki_school.KitsukiMagistrateSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestKitsukiSpecialAbility(unittest.TestCase):
    def test_water_added_to_attack_roll(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 4)
        target = Character("Target")
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_special_ability(kitsuki)
        provider = kitsuki.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(kitsuki, target, "attack")
        # Special: 2 * Water (4) = 8
        self.assertEqual(8, modifier)

    def test_no_bonus_on_non_attack(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 4)
        target = Character("Target")
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_special_ability(kitsuki)
        provider = kitsuki.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(kitsuki, target, "parry")
        # Non-attack should not get the bonus
        self.assertEqual(0, modifier)

    def test_water_scales_with_ring(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 2)
        target = Character("Target")
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_special_ability(kitsuki)
        provider = kitsuki.roll_parameter_provider()
        _, _, modifier = provider.get_skill_roll_params(kitsuki, target, "attack")
        # 2 * Water (2) = 4
        self.assertEqual(4, modifier)


class TestKitsukiAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_skill("investigation", 5)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_three_ability(kitsuki)
        self.assertEqual("investigation", kitsuki.ap_base_skill())
        self.assertTrue(kitsuki.can_spend_ap("attack"))
        self.assertTrue(kitsuki.can_spend_ap("wound check"))
        self.assertFalse(kitsuki.can_spend_ap("parry"))
        # AP = 2 * investigation skill = 10
        self.assertEqual(10, kitsuki.ap())

    def test_ap_with_lower_skill(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_skill("investigation", 3)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_three_ability(kitsuki)
        # AP = 2 * 3 = 6
        self.assertEqual(6, kitsuki.ap())


class TestKitsukiFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        kitsuki = Character("Kitsuki")
        kitsuki.set_ring("water", 3)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_four_ability(kitsuki)
        # Ring raise: water should be +1
        self.assertEqual(4, kitsuki.ring("water"))


class TestKitsukiFifthDan(unittest.TestCase):
    """Test the Kitsuki 5th Dan ability: reduce opponents' Air, Fire,
    and Water rings by 1 on the first round of combat."""

    def _setup_combat(self, opponent_air=3, opponent_fire=3, opponent_water=3):
        """Create a Kitsuki and an opponent in a combat context."""
        self.kitsuki = Character("Kitsuki")
        self.kitsuki.set_ring("air", 3)
        self.kitsuki.set_ring("fire", 3)
        self.kitsuki.set_ring("water", 3)

        self.opponent = Character("Opponent")
        self.opponent.set_ring("air", opponent_air)
        self.opponent.set_ring("fire", opponent_fire)
        self.opponent.set_ring("water", opponent_water)

        # Use CalvinistRollProvider for deterministic initiative rolls
        kitsuki_rp = CalvinistRollProvider()
        kitsuki_rp.put_initiative_roll([3, 7])
        kitsuki_rp.put_initiative_roll([3, 7])  # for round 2
        self.kitsuki.set_roll_provider(kitsuki_rp)

        opponent_rp = CalvinistRollProvider()
        opponent_rp.put_initiative_roll([4, 8])
        opponent_rp.put_initiative_roll([4, 8])  # for round 2
        self.opponent.set_roll_provider(opponent_rp)

        group1 = Group("Kitsuki Side", self.kitsuki)
        group2 = Group("Opponent Side", self.opponent)
        self.context = EngineContext([group1, group2])
        self.context.initialize()

    def test_listener_installed(self):
        """apply_rank_five_ability should install a KitsukiFifthDanNewRoundListener."""
        kitsuki = Character("Kitsuki")
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(kitsuki)
        self.assertIsInstance(
            kitsuki._listeners["new_round"],
            kitsuki_school.KitsukiFifthDanNewRoundListener,
        )

    def test_reduces_opponent_rings_on_round_one(self):
        """On the first NewRoundEvent, opponents' Air, Fire, Water should be reduced by 1."""
        self._setup_combat(opponent_air=3, opponent_fire=4, opponent_water=3)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        # Play a NewRoundEvent (round 1)
        new_round = events.NewRoundEvent(1)
        # Play the event on the Kitsuki (triggers initiative + ring reduction)
        list(self.kitsuki.event(new_round, self.context))
        # Also play on opponent so they roll initiative
        list(self.opponent.event(new_round, self.context))

        # Opponent's rings should be reduced by 1
        self.assertEqual(2, self.opponent.ring("air"))
        self.assertEqual(3, self.opponent.ring("fire"))
        self.assertEqual(2, self.opponent.ring("water"))

    def test_does_not_reduce_own_rings(self):
        """The Kitsuki's own rings should not be affected by the 5th Dan ability."""
        self._setup_combat()
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        new_round = events.NewRoundEvent(1)
        list(self.kitsuki.event(new_round, self.context))
        list(self.opponent.event(new_round, self.context))

        # Kitsuki's rings should be unchanged
        self.assertEqual(3, self.kitsuki.ring("air"))
        self.assertEqual(3, self.kitsuki.ring("fire"))
        self.assertEqual(3, self.kitsuki.ring("water"))

    def test_does_not_reduce_earth_or_void(self):
        """Earth and Void rings should not be affected."""
        self._setup_combat()
        self.opponent.set_ring("earth", 4)
        self.opponent.set_ring("void", 4)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        new_round = events.NewRoundEvent(1)
        list(self.kitsuki.event(new_round, self.context))
        list(self.opponent.event(new_round, self.context))

        # Earth and Void should be unchanged
        self.assertEqual(4, self.opponent.ring("earth"))
        self.assertEqual(4, self.opponent.ring("void"))

    def test_reduction_only_happens_once(self):
        """The ring reduction should only happen on the first round, not on subsequent rounds."""
        self._setup_combat(opponent_air=4, opponent_fire=4, opponent_water=4)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        # Round 1
        round1 = events.NewRoundEvent(1)
        list(self.kitsuki.event(round1, self.context))
        list(self.opponent.event(round1, self.context))

        # After round 1, opponent rings should be reduced by 1
        self.assertEqual(3, self.opponent.ring("air"))
        self.assertEqual(3, self.opponent.ring("fire"))
        self.assertEqual(3, self.opponent.ring("water"))

        # Round 2
        round2 = events.NewRoundEvent(2)
        list(self.kitsuki.event(round2, self.context))
        list(self.opponent.event(round2, self.context))

        # After round 2, rings should not be reduced again
        self.assertEqual(3, self.opponent.ring("air"))
        self.assertEqual(3, self.opponent.ring("fire"))
        self.assertEqual(3, self.opponent.ring("water"))

    def test_rings_minimum_one(self):
        """Rings should not go below 1 even if they are already at 1."""
        self._setup_combat(opponent_air=1, opponent_fire=1, opponent_water=1)
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        new_round = events.NewRoundEvent(1)
        list(self.kitsuki.event(new_round, self.context))
        list(self.opponent.event(new_round, self.context))

        # Rings at 1 should stay at 1
        self.assertEqual(1, self.opponent.ring("air"))
        self.assertEqual(1, self.opponent.ring("fire"))
        self.assertEqual(1, self.opponent.ring("water"))

    def test_reduces_multiple_opponents(self):
        """The reduction should apply to all opponents, not just one."""
        self.kitsuki = Character("Kitsuki")
        self.kitsuki.set_ring("air", 3)
        self.kitsuki.set_ring("fire", 3)
        self.kitsuki.set_ring("water", 3)

        opponent1 = Character("Opponent1")
        opponent1.set_ring("air", 3)
        opponent1.set_ring("fire", 3)
        opponent1.set_ring("water", 3)

        opponent2 = Character("Opponent2")
        opponent2.set_ring("air", 4)
        opponent2.set_ring("fire", 4)
        opponent2.set_ring("water", 4)

        # Use CalvinistRollProvider for all
        kitsuki_rp = CalvinistRollProvider()
        kitsuki_rp.put_initiative_roll([3, 7])
        self.kitsuki.set_roll_provider(kitsuki_rp)

        opp1_rp = CalvinistRollProvider()
        opp1_rp.put_initiative_roll([4, 8])
        opponent1.set_roll_provider(opp1_rp)

        opp2_rp = CalvinistRollProvider()
        opp2_rp.put_initiative_roll([5, 9])
        opponent2.set_roll_provider(opp2_rp)

        group1 = Group("Kitsuki Side", self.kitsuki)
        group2 = Group("Opponent Side", [opponent1, opponent2])
        context = EngineContext([group1, group2])
        context.initialize()

        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        new_round = events.NewRoundEvent(1)
        list(self.kitsuki.event(new_round, context))
        list(opponent1.event(new_round, context))
        list(opponent2.event(new_round, context))

        # Both opponents should have reduced rings
        self.assertEqual(2, opponent1.ring("air"))
        self.assertEqual(2, opponent1.ring("fire"))
        self.assertEqual(2, opponent1.ring("water"))

        self.assertEqual(3, opponent2.ring("air"))
        self.assertEqual(3, opponent2.ring("fire"))
        self.assertEqual(3, opponent2.ring("water"))

    def test_does_not_reduce_ally_rings(self):
        """Allies in the same group as the Kitsuki should not have rings reduced."""
        self.kitsuki = Character("Kitsuki")
        self.kitsuki.set_ring("air", 3)
        self.kitsuki.set_ring("fire", 3)
        self.kitsuki.set_ring("water", 3)

        ally = Character("Ally")
        ally.set_ring("air", 3)
        ally.set_ring("fire", 3)
        ally.set_ring("water", 3)

        opponent = Character("Opponent")
        opponent.set_ring("air", 3)
        opponent.set_ring("fire", 3)
        opponent.set_ring("water", 3)

        # Use CalvinistRollProvider for all
        kitsuki_rp = CalvinistRollProvider()
        kitsuki_rp.put_initiative_roll([3, 7])
        self.kitsuki.set_roll_provider(kitsuki_rp)

        ally_rp = CalvinistRollProvider()
        ally_rp.put_initiative_roll([4, 8])
        ally.set_roll_provider(ally_rp)

        opp_rp = CalvinistRollProvider()
        opp_rp.put_initiative_roll([5, 9])
        opponent.set_roll_provider(opp_rp)

        group1 = Group("Kitsuki Side", [self.kitsuki, ally])
        group2 = Group("Opponent Side", opponent)
        context = EngineContext([group1, group2])
        context.initialize()

        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        new_round = events.NewRoundEvent(1)
        list(self.kitsuki.event(new_round, context))
        list(ally.event(new_round, context))
        list(opponent.event(new_round, context))

        # Ally's rings should be unchanged
        self.assertEqual(3, ally.ring("air"))
        self.assertEqual(3, ally.ring("fire"))
        self.assertEqual(3, ally.ring("water"))

        # Opponent's rings should be reduced
        self.assertEqual(2, opponent.ring("air"))
        self.assertEqual(2, opponent.ring("fire"))
        self.assertEqual(2, opponent.ring("water"))

    def test_initiative_still_rolled(self):
        """The wrapped listener should still roll initiative properly."""
        self._setup_combat()
        school = kitsuki_school.KitsukiMagistrateSchool()
        school.apply_rank_five_ability(self.kitsuki)

        new_round = events.NewRoundEvent(1)
        list(self.kitsuki.event(new_round, self.context))

        # Kitsuki should have rolled initiative and gotten [3, 7]
        self.assertEqual([3, 7], self.kitsuki.actions())
