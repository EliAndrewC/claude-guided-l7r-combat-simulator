#!/usr/bin/env python3

#
# test_formation.py
#
# Unit tests for the formation system.
#

import unittest

from simulation.character import Character
from simulation.events import AddModifierEvent, RemoveModifierEvent
from simulation.formation import LineFormation, NullFormation, SurroundFormation


class TestNullFormation(unittest.TestCase):
    def test_can_attack_always_true(self):
        a = Character("A")
        b = Character("B")
        f = NullFormation()
        self.assertTrue(f.can_attack(a, b))
        self.assertTrue(f.can_attack(b, a))

    def test_is_adjacent_always_true(self):
        a = Character("A")
        b = Character("B")
        f = NullFormation()
        self.assertTrue(f.is_adjacent(a, b))
        self.assertTrue(f.is_adjacent(b, a))
        self.assertTrue(f.is_adjacent(a, a))

    def test_remove_does_nothing(self):
        f = NullFormation()
        a = Character("A")
        f.remove(a)  # should not raise

    def test_reset_does_nothing(self):
        f = NullFormation()
        f.reset()  # should not raise


class TestLineFormation1v1(unittest.TestCase):
    def setUp(self):
        self.a0 = Character("A0")
        self.b0 = Character("B0")
        self.formation = LineFormation([[self.a0], [self.b0]])

    def test_can_attack_each_other(self):
        self.assertTrue(self.formation.can_attack(self.a0, self.b0))
        self.assertTrue(self.formation.can_attack(self.b0, self.a0))

    def test_cannot_attack_same_side(self):
        self.assertFalse(self.formation.can_attack(self.a0, self.a0))

    def test_is_adjacent_self(self):
        self.assertTrue(self.formation.is_adjacent(self.a0, self.a0))

    def test_not_adjacent_cross_side(self):
        self.assertFalse(self.formation.is_adjacent(self.a0, self.b0))

    def test_attackable_targets(self):
        self.assertEqual([self.b0], self.formation.attackable_targets(self.a0))
        self.assertEqual([self.a0], self.formation.attackable_targets(self.b0))


class TestLineFormation2v2(unittest.TestCase):
    def setUp(self):
        self.a0 = Character("A0")
        self.a1 = Character("A1")
        self.b0 = Character("B0")
        self.b1 = Character("B1")
        self.formation = LineFormation(
            [[self.a0, self.a1], [self.b0, self.b1]],
        )

    def test_positions_symmetric(self):
        """2v2: A at 0,1 and B at 0,1 — each can attack the one across."""
        # A0 (pos 0) vs B0 (pos 0): |0-0| = 0 <= 1 -> yes
        self.assertTrue(self.formation.can_attack(self.a0, self.b0))
        # A0 (pos 0) vs B1 (pos 1): |0-1| = 1 <= 1 -> yes
        self.assertTrue(self.formation.can_attack(self.a0, self.b1))
        # A1 (pos 1) vs B0 (pos 0): |1-0| = 1 <= 1 -> yes
        self.assertTrue(self.formation.can_attack(self.a1, self.b0))
        # A1 (pos 1) vs B1 (pos 1): |1-1| = 0 <= 1 -> yes
        self.assertTrue(self.formation.can_attack(self.a1, self.b1))

    def test_adjacency(self):
        self.assertTrue(self.formation.is_adjacent(self.a0, self.a1))
        self.assertTrue(self.formation.is_adjacent(self.a1, self.a0))
        self.assertTrue(self.formation.is_adjacent(self.b0, self.b1))

    def test_not_adjacent_across_sides(self):
        self.assertFalse(self.formation.is_adjacent(self.a0, self.b0))


class TestLineFormation3v2(unittest.TestCase):
    """3v2 line formation.

    A: positions 0, 1, 2
    B: offset = (3-2)/2 = 0.5, positions 0.5, 1.5

    Attackable pairs:
      A0(0) vs B0(0.5): |0 - 0.5| = 0.5 <= 1 -> yes
      A0(0) vs B1(1.5): |0 - 1.5| = 1.5 > 1 -> no
      A1(1) vs B0(0.5): |1 - 0.5| = 0.5 <= 1 -> yes
      A1(1) vs B1(1.5): |1 - 1.5| = 0.5 <= 1 -> yes
      A2(2) vs B0(0.5): |2 - 0.5| = 1.5 > 1 -> no
      A2(2) vs B1(1.5): |2 - 1.5| = 0.5 <= 1 -> yes
    """

    def setUp(self):
        self.a0 = Character("A0")
        self.a1 = Character("A1")
        self.a2 = Character("A2")
        self.b0 = Character("B0")
        self.b1 = Character("B1")
        self.formation = LineFormation(
            [[self.a0, self.a1, self.a2], [self.b0, self.b1]],
        )

    def test_attackable_pairs(self):
        self.assertTrue(self.formation.can_attack(self.a0, self.b0))
        self.assertFalse(self.formation.can_attack(self.a0, self.b1))
        self.assertTrue(self.formation.can_attack(self.a1, self.b0))
        self.assertTrue(self.formation.can_attack(self.a1, self.b1))
        self.assertFalse(self.formation.can_attack(self.a2, self.b0))
        self.assertTrue(self.formation.can_attack(self.a2, self.b1))

    def test_symmetric(self):
        self.assertTrue(self.formation.can_attack(self.b0, self.a0))
        self.assertTrue(self.formation.can_attack(self.b1, self.a2))

    def test_same_side_not_attackable(self):
        self.assertFalse(self.formation.can_attack(self.a0, self.a1))
        self.assertFalse(self.formation.can_attack(self.b0, self.b1))

    def test_adjacency_side_a(self):
        self.assertTrue(self.formation.is_adjacent(self.a0, self.a1))
        self.assertTrue(self.formation.is_adjacent(self.a1, self.a2))
        # not adjacent: a0 and a2 (not neighbors in linear chain)
        self.assertFalse(self.formation.is_adjacent(self.a0, self.a2))

    def test_adjacency_side_b(self):
        self.assertTrue(self.formation.is_adjacent(self.b0, self.b1))

    def test_neighbors(self):
        self.assertEqual([self.a1], self.formation.neighbors(self.a0))
        nbrs_a1 = self.formation.neighbors(self.a1)
        self.assertEqual(2, len(nbrs_a1))
        self.assertIn(self.a0, nbrs_a1)
        self.assertIn(self.a2, nbrs_a1)
        self.assertEqual([self.a1], self.formation.neighbors(self.a2))


class TestLineFormation4v2(unittest.TestCase):
    """4v2 line formation.

    A: positions 0, 1, 2, 3
    B: offset = (4-2)/2 = 1.0, positions 1.0, 2.0

    Attackable pairs:
      A0(0) vs B0(1.0): |0 - 1.0| = 1.0 <= 1 -> yes
      A0(0) vs B1(2.0): |0 - 2.0| = 2.0 > 1 -> no
      A1(1) vs B0(1.0): |1 - 1.0| = 0.0 <= 1 -> yes
      A1(1) vs B1(2.0): |1 - 2.0| = 1.0 <= 1 -> yes
      A2(2) vs B0(1.0): |2 - 1.0| = 1.0 <= 1 -> yes
      A2(2) vs B1(2.0): |2 - 2.0| = 0.0 <= 1 -> yes
      A3(3) vs B0(1.0): |3 - 1.0| = 2.0 > 1 -> no
      A3(3) vs B1(2.0): |3 - 2.0| = 1.0 <= 1 -> yes
    """

    def setUp(self):
        self.a = [Character(f"A{i}") for i in range(4)]
        self.b = [Character(f"B{i}") for i in range(2)]
        self.formation = LineFormation([self.a, self.b])

    def test_attackable_pairs(self):
        self.assertTrue(self.formation.can_attack(self.a[0], self.b[0]))
        self.assertFalse(self.formation.can_attack(self.a[0], self.b[1]))
        self.assertTrue(self.formation.can_attack(self.a[1], self.b[0]))
        self.assertTrue(self.formation.can_attack(self.a[1], self.b[1]))
        self.assertTrue(self.formation.can_attack(self.a[2], self.b[0]))
        self.assertTrue(self.formation.can_attack(self.a[2], self.b[1]))
        self.assertFalse(self.formation.can_attack(self.a[3], self.b[0]))
        self.assertTrue(self.formation.can_attack(self.a[3], self.b[1]))


class TestLineFormation5v3(unittest.TestCase):
    """5v3 line formation.

    A: positions 0, 1, 2, 3, 4
    B: offset = (5-3)/2 = 1.0, positions 1.0, 2.0, 3.0

    Attackable:
      A0(0) vs B0(1): yes  B1(2): no   B2(3): no
      A1(1) vs B0(1): yes  B1(2): yes  B2(3): no
      A2(2) vs B0(1): yes  B1(2): yes  B2(3): yes
      A3(3) vs B0(1): no   B1(2): yes  B2(3): yes
      A4(4) vs B0(1): no   B1(2): no   B2(3): yes
    """

    def setUp(self):
        self.a = [Character(f"A{i}") for i in range(5)]
        self.b = [Character(f"B{i}") for i in range(3)]
        self.formation = LineFormation([self.a, self.b])

    def test_attackable_pairs(self):
        expected = {
            (0, 0): True, (0, 1): False, (0, 2): False,
            (1, 0): True, (1, 1): True, (1, 2): False,
            (2, 0): True, (2, 1): True, (2, 2): True,
            (3, 0): False, (3, 1): True, (3, 2): True,
            (4, 0): False, (4, 1): False, (4, 2): True,
        }
        for (ai, bi), can in expected.items():
            result = self.formation.can_attack(self.a[ai], self.b[bi])
            self.assertEqual(can, result, f"A{ai} vs B{bi}: expected {can}, got {result}")

    def test_adjacency_side_a(self):
        # Linear chain: 0-1, 1-2, 2-3, 3-4
        self.assertTrue(self.formation.is_adjacent(self.a[0], self.a[1]))
        self.assertTrue(self.formation.is_adjacent(self.a[1], self.a[2]))
        self.assertTrue(self.formation.is_adjacent(self.a[2], self.a[3]))
        self.assertTrue(self.formation.is_adjacent(self.a[3], self.a[4]))
        # Not adjacent: 0-2, 0-3, 0-4, 1-3, etc.
        self.assertFalse(self.formation.is_adjacent(self.a[0], self.a[2]))
        self.assertFalse(self.formation.is_adjacent(self.a[0], self.a[4]))


class TestLineFormationRemove(unittest.TestCase):
    """Test that removing a character re-centers the formation."""

    def test_remove_recenters_3v2_to_2v2(self):
        a0 = Character("A0")
        a1 = Character("A1")
        a2 = Character("A2")
        b0 = Character("B0")
        b1 = Character("B1")
        formation = LineFormation([[a0, a1, a2], [b0, b1]])

        # Before removal, A0 cannot attack B1
        self.assertFalse(formation.can_attack(a0, b1))

        # Remove A2 -> 2v2
        formation.remove(a2)

        # Now 2v2: both A0 and A1 can attack both B0 and B1
        self.assertTrue(formation.can_attack(a0, b0))
        self.assertTrue(formation.can_attack(a0, b1))
        self.assertTrue(formation.can_attack(a1, b0))
        self.assertTrue(formation.can_attack(a1, b1))

    def test_remove_from_side_b(self):
        a0 = Character("A0")
        a1 = Character("A1")
        b0 = Character("B0")
        b1 = Character("B1")
        formation = LineFormation([[a0, a1], [b0, b1]])

        formation.remove(b1)
        # 2v1: A positions 0,1; B position 0.5
        # A0(0) vs B0(0.5): yes; A1(1) vs B0(0.5): yes
        self.assertTrue(formation.can_attack(a0, b0))
        self.assertTrue(formation.can_attack(a1, b0))


class TestLineFormationReset(unittest.TestCase):
    def test_reset_restores_original(self):
        a0 = Character("A0")
        a1 = Character("A1")
        b0 = Character("B0")
        b1 = Character("B1")
        formation = LineFormation([[a0, a1], [b0, b1]])

        formation.remove(a1)
        # After remove, only a0 left on side A
        self.assertEqual(1, len(formation.sides()[0]))

        formation.reset()
        # After reset, both a0 and a1 restored
        self.assertEqual(2, len(formation.sides()[0]))
        self.assertEqual(2, len(formation.sides()[1]))
        # And attackable pairs restored
        self.assertTrue(formation.can_attack(a0, b0))
        self.assertTrue(formation.can_attack(a1, b1))


class TestSurroundFormation(unittest.TestCase):
    """Test SurroundFormation transitions and behavior."""

    def test_line_mode_when_balanced(self):
        """3v3 should behave like line formation."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character(f"B{i}") for i in range(3)]
        formation = SurroundFormation([a, b])
        # Same as LineFormation 3v3 (symmetric, offset=0)
        self.assertTrue(formation.can_attack(a[0], b[0]))
        self.assertTrue(formation.can_attack(a[1], b[1]))
        self.assertTrue(formation.can_attack(a[2], b[2]))

    def test_surround_mode_3v1(self):
        """3v1: all three on one side can attack the single fighter."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character("B0")]
        formation = SurroundFormation([a, b])
        for ai in a:
            self.assertTrue(formation.can_attack(ai, b[0]))
            self.assertTrue(formation.can_attack(b[0], ai))

    def test_surround_circular_adjacency(self):
        """In surround mode, outer ring has circular adjacency."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character("B0")]
        formation = SurroundFormation([a, b])
        # Circular: A0-A1, A1-A2, A2-A0
        self.assertTrue(formation.is_adjacent(a[0], a[1]))
        self.assertTrue(formation.is_adjacent(a[1], a[2]))
        self.assertTrue(formation.is_adjacent(a[2], a[0]))

    def test_surround_inner_no_neighbors(self):
        """In surround mode, the inner character has no neighbors."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character("B0")]
        formation = SurroundFormation([a, b])
        self.assertEqual([], formation.neighbors(b[0]))

    def test_surround_bonus_value(self):
        """Surround bonus should be +5 * (1 + N) where N = number of surrounding enemies."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character("B0")]
        formation = SurroundFormation([a, b])
        modifier_events = formation.pending_events()
        # Should have 3 AddModifierEvents (one per outer)
        add_events = [e for e in modifier_events if isinstance(e, AddModifierEvent)]
        self.assertEqual(3, len(add_events))
        # Bonus = 5 * (1 + 3) = 20
        for event in add_events:
            self.assertEqual(20, event.modifier.adjustment())

    def test_surround_bonus_2v1(self):
        """2v1 surround: bonus = 5 * (1 + 2) = 15."""
        a = [Character(f"A{i}") for i in range(2)]
        b = [Character("B0")]
        formation = SurroundFormation([a, b])
        modifier_events = formation.pending_events()
        add_events = [e for e in modifier_events if isinstance(e, AddModifierEvent)]
        self.assertEqual(2, len(add_events))
        for event in add_events:
            self.assertEqual(15, event.modifier.adjustment())

    def test_transition_line_to_surround(self):
        """3v3 -> kill 2 on side B -> 3v1 surround."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character(f"B{i}") for i in range(3)]
        formation = SurroundFormation([a, b])

        # Initially line mode, no surround modifiers
        events = formation.pending_events()
        add_events = [e for e in events if isinstance(e, AddModifierEvent)]
        self.assertEqual(0, len(add_events))

        # Remove B1 -> 3v2 (still line)
        formation.remove(b[1])
        events = formation.pending_events()
        add_events = [e for e in events if isinstance(e, AddModifierEvent)]
        self.assertEqual(0, len(add_events))

        # Remove B2 -> 3v1 (surround!)
        formation.remove(b[2])
        events = formation.pending_events()
        add_events = [e for e in events if isinstance(e, AddModifierEvent)]
        self.assertEqual(3, len(add_events))
        # Bonus = 5 * (1 + 3) = 20
        for event in add_events:
            self.assertEqual(20, event.modifier.adjustment())

    def test_revert_surround_to_1v1(self):
        """3v1 surround -> kill 2 outer -> 1v1 line (bonuses removed)."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character("B0")]
        formation = SurroundFormation([a, b])

        # Start in surround mode
        events_initial = formation.pending_events()
        add_events = [e for e in events_initial if isinstance(e, AddModifierEvent)]
        self.assertEqual(3, len(add_events))

        # Remove A1 -> 2v1 (still surround)
        formation.remove(a[1])
        events_2v1 = formation.pending_events()
        remove_events = [e for e in events_2v1 if isinstance(e, RemoveModifierEvent)]
        add_events_2 = [e for e in events_2v1 if isinstance(e, AddModifierEvent)]
        # Should remove old modifiers and add new ones
        self.assertTrue(len(remove_events) > 0)
        self.assertEqual(2, len(add_events_2))
        # New bonus = 5 * (1 + 2) = 15
        for event in add_events_2:
            self.assertEqual(15, event.modifier.adjustment())

        # Remove A2 -> 1v1 (back to line)
        formation.remove(a[2])
        events_1v1 = formation.pending_events()
        remove_events_final = [e for e in events_1v1 if isinstance(e, RemoveModifierEvent)]
        add_events_final = [e for e in events_1v1 if isinstance(e, AddModifierEvent)]
        # Should remove surround modifiers, add none
        self.assertTrue(len(remove_events_final) > 0)
        self.assertEqual(0, len(add_events_final))

    def test_surround_with_side_b_outer(self):
        """1v3: side A has 1, side B has 3 — B surrounds A."""
        a = [Character("A0")]
        b = [Character(f"B{i}") for i in range(3)]
        formation = SurroundFormation([a, b])
        # All B can attack A0
        for bi in b:
            self.assertTrue(formation.can_attack(bi, a[0]))
            self.assertTrue(formation.can_attack(a[0], bi))
        # B has circular adjacency
        self.assertTrue(formation.is_adjacent(b[0], b[1]))
        self.assertTrue(formation.is_adjacent(b[1], b[2]))
        self.assertTrue(formation.is_adjacent(b[2], b[0]))

    def test_reset_clears_surround(self):
        """Reset should restore original sides and clear surround modifiers."""
        a = [Character(f"A{i}") for i in range(3)]
        b = [Character("B0")]
        formation = SurroundFormation([a, b])
        # Consume initial events
        formation.pending_events()

        formation.remove(a[1])
        formation.reset()

        # After reset, all 3 A characters should be back
        self.assertEqual(3, len(formation.sides()[0]))
        self.assertEqual(1, len(formation.sides()[1]))
