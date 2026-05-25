#!/usr/bin/env python3

#
# formation.py
#
# Formation classes for positional combat.
#
# Formations track which characters can attack which enemies (cross-side)
# and which allies are adjacent (same-side neighbors for parry/counterattack).
#

from typing import TYPE_CHECKING

from simulation.events import AddModifierEvent, ModifierEvent, RemoveModifierEvent
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.skills import ATTACK_SKILLS

if TYPE_CHECKING:
    from simulation.character import Character


class Formation:
    """Base class for formations.

    Stores two sides as ordered lists of Characters.
    Subclasses implement deploy() to calculate positions, attackable sets,
    and neighbor maps.
    """

    def __init__(self, sides: list[list["Character"]]):
        if len(sides) != 2:
            raise ValueError("Formation requires exactly two sides")
        self._original_sides: list[list[Character]] = [list(side) for side in sides]
        self._sides: list[list[Character]] = [list(side) for side in sides]
        self._attackable: dict[int, set[int]] = {}
        self._neighbors: dict[int, set[int]] = {}
        self.deploy()

    def can_attack(self, attacker: "Character", target: "Character") -> bool:
        """Return True if attacker can attack target based on position."""
        targets = self._attackable.get(id(attacker), set())
        return id(target) in targets

    def is_adjacent(self, a: "Character", b: "Character") -> bool:
        """Return True if a and b are same-side neighbors.

        Always returns True if a == b (self-parry is always OK).
        """
        if a is b:
            return True
        nbrs = self._neighbors.get(id(a), set())
        return id(b) in nbrs

    def attackable_targets(self, character: "Character") -> list["Character"]:
        """Return list of characters that character can attack."""
        targets = self._attackable.get(id(character), set())
        all_chars = self._sides[0] + self._sides[1]
        return [c for c in all_chars if id(c) in targets]

    def neighbors(self, character: "Character") -> list["Character"]:
        """Return same-side left/right neighbors."""
        nbrs = self._neighbors.get(id(character), set())
        all_chars = self._sides[0] + self._sides[1]
        return [c for c in all_chars if id(c) in nbrs]

    def remove(self, character: "Character") -> None:
        """Remove a defeated character and redeploy."""
        for side in self._sides:
            if character in side:
                side.remove(character)
                break
        self._attackable.pop(id(character), None)
        self._neighbors.pop(id(character), None)
        self.deploy()

    def reset(self) -> None:
        """Restore original sides and redeploy."""
        self._sides = [list(side) for side in self._original_sides]
        self._attackable = {}
        self._neighbors = {}
        self.deploy()

    def sides(self) -> list[list["Character"]]:
        return self._sides

    def deploy(self) -> None:
        """Calculate positions, attackable sets, and neighbor maps.

        Subclasses must override this.
        """
        raise NotImplementedError()


class NullFormation(Formation):
    """Backward-compatible formation where everyone can attack and is adjacent to everyone.

    Default when no formation is explicitly set, so all existing tests pass unchanged.
    """

    def __init__(self) -> None:
        # bypass parent __init__ since we have no sides
        self._original_sides = [[], []]
        self._sides = [[], []]
        self._attackable = {}
        self._neighbors = {}

    def can_attack(self, attacker: "Character", target: "Character") -> bool:
        return True

    def is_adjacent(self, a: "Character", b: "Character") -> bool:
        return True

    def attackable_targets(self, character: "Character") -> list["Character"]:
        return []

    def neighbors(self, character: "Character") -> list["Character"]:
        return []

    def remove(self, character: "Character") -> None:
        pass

    def reset(self) -> None:
        pass

    def deploy(self) -> None:
        pass


class LineFormation(Formation):
    """Line formation where characters face off in parallel lines.

    Position algorithm:
    - Side A: positions 0, 1, ..., n_a-1
    - Side B: positions j + (n_a - n_b) / 2 for j in 0..n_b-1
    - Pair (a, b) can attack if |pos_a - pos_b| <= 1
    - Same-side adjacency: linear chain (not circular)
    """

    def deploy(self) -> None:
        self._attackable = {}
        self._neighbors = {}

        side_a = self._sides[0]
        side_b = self._sides[1]
        n_a = len(side_a)
        n_b = len(side_b)

        if n_a == 0 or n_b == 0:
            return

        # Calculate positions
        positions_a = {id(c): float(i) for i, c in enumerate(side_a)}
        offset_b = (n_a - n_b) / 2.0
        positions_b = {id(c): float(j) + offset_b for j, c in enumerate(side_b)}

        # Calculate attackable pairs (cross-side only)
        for a in side_a:
            self._attackable.setdefault(id(a), set())
            for b in side_b:
                self._attackable.setdefault(id(b), set())
                if abs(positions_a[id(a)] - positions_b[id(b)]) <= 1.0:
                    self._attackable[id(a)].add(id(b))
                    self._attackable[id(b)].add(id(a))

        # Calculate same-side adjacency (linear chain)
        for side in [side_a, side_b]:
            for i, c in enumerate(side):
                self._neighbors.setdefault(id(c), set())
                if i > 0:
                    self._neighbors[id(c)].add(id(side[i - 1]))
                if i < len(side) - 1:
                    self._neighbors[id(c)].add(id(side[i + 1]))


class SurroundFormation(LineFormation):
    """Formation that transitions to surround mode when one side has 1 vs >= 2.

    In surround mode:
    - Every outer combatant can attack the inner (and vice-versa)
    - Outer forms circular adjacency ring
    - Each outer combatant gets +5 * (1 + N) attack bonus where N = number of surrounding enemies

    Transitions:
    - Line -> Surround when one side drops to 1 vs >= 2
    - Surround -> Line when 1v1 (bonuses removed)
    """

    def __init__(self, sides: list[list["Character"]]):
        self._surround_modifiers: list[tuple[Character, Modifier]] = []  # (character, modifier) pairs
        super().__init__(sides)

    def _is_surround(self) -> bool:
        """Check if one side has exactly 1 and the other has >= 2."""
        sizes = [len(s) for s in self._sides]
        return (sizes[0] == 1 and sizes[1] >= 2) or (sizes[1] == 1 and sizes[0] >= 2)

    def _surround_events(self) -> list[ModifierEvent]:
        """Return AddModifierEvent/RemoveModifierEvent list for surround bonuses."""
        return_events: list[ModifierEvent] = []
        # Remove old surround modifiers
        for character, modifier in self._surround_modifiers:
            return_events.append(RemoveModifierEvent(character, modifier))
        self._surround_modifiers.clear()

        if self._is_surround():
            # Determine inner and outer sides
            if len(self._sides[0]) == 1:
                outer = self._sides[1]
                inner_char = self._sides[0][0]
            else:
                outer = self._sides[0]
                inner_char = self._sides[1][0]

            n_surrounding = len(outer)
            bonus = 5 * (1 + n_surrounding)

            for c in outer:
                modifier = Modifier(c, inner_char, ATTACK_SKILLS, bonus)
                self._surround_modifiers.append((c, modifier))
                return_events.append(AddModifierEvent(c, modifier))

        return return_events

    def deploy(self) -> None:
        if self._is_surround():
            self._deploy_surround()
        else:
            super().deploy()

    def _deploy_surround(self) -> None:
        """Deploy in surround mode."""
        self._attackable = {}
        self._neighbors = {}

        if len(self._sides[0]) == 1:
            inner_char = self._sides[0][0]
            outer = self._sides[1]
        else:
            inner_char = self._sides[1][0]
            outer = self._sides[0]

        # Inner can attack all outer and vice-versa
        self._attackable[id(inner_char)] = {id(c) for c in outer}
        for c in outer:
            self._attackable[id(c)] = {id(inner_char)}

        # Outer forms circular adjacency ring
        n = len(outer)
        for i, c in enumerate(outer):
            self._neighbors.setdefault(id(c), set())
            if n > 1:
                self._neighbors[id(c)].add(id(outer[(i - 1) % n]))
                self._neighbors[id(c)].add(id(outer[(i + 1) % n]))

        # Inner has no neighbors (alone on their side)
        self._neighbors[id(inner_char)] = set()

    def remove(self, character: "Character") -> None:
        """Remove a defeated character and redeploy, returning surround events."""
        for side in self._sides:
            if character in side:
                side.remove(character)
                break
        self._attackable.pop(id(character), None)
        self._neighbors.pop(id(character), None)
        # Remove any surround modifiers belonging to the removed character
        self._surround_modifiers = [
            (c, m) for c, m in self._surround_modifiers if c is not character
        ]
        self.deploy()

    def reset(self) -> None:
        """Restore original sides, clear surround modifiers, and redeploy."""
        self._surround_modifiers.clear()
        super().reset()

    def pending_events(self) -> list[ModifierEvent]:
        """Return any pending AddModifier/RemoveModifier events from surround transitions.

        Call this after deploy/remove to get the modifier events that need to be
        processed by the engine.
        """
        return self._surround_events()
