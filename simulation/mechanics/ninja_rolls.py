#!/usr/bin/env python3

#
# ninja_rolls.py
#
# Custom Roll classes for Ninja profession abilities.
#

from simulation.mechanics.roll import BaseRoll
from simulation.mechanics.roll_params import normalize_roll_params


class NinjaDamageReductionRoll(BaseRoll):
    """
    Roll that implements the Ninja "damage reduction" ability:
    "Attacker rerolls 1 fewer 10 on damage (min 1 rerolled)."

    Rolls all dice without explosion. Counts the number of 10s.
    Only rerolls max(1, tens_count - reduction) of them.
    Non-rerolled 10s stay as 10.
    """

    def __init__(self, rolled, kept, reduction=0, faces=10, die_provider=None):
        super().__init__(rolled, kept, faces, True, die_provider)
        if not isinstance(reduction, int) or reduction < 0:
            raise ValueError("reduction must be a non-negative int")
        self._reduction = reduction
        self._dice = []

    def dice(self):
        return self._dice

    def roll(self):
        # Roll all dice without explosion first
        dice = [self.roll_die(faces=self.faces(), explode=False) for _ in range(self._rolled)]
        # Count tens and determine how many to reroll
        tens_count = dice.count(10)
        if tens_count > 0:
            reroll_count = max(1, tens_count - self._reduction)
            # Remove tens that will be rerolled
            for _ in range(reroll_count):
                dice.remove(10)
                rerolled = 10 + self.roll_die(faces=self.faces(), explode=True)
                dice.append(rerolled)
            # Remaining tens (not rerolled) stay as 10
        dice.sort(reverse=True)
        self._dice = dice
        return sum(dice[:self._kept]) + self._bonus


class NinjaWoundCheckRoll(BaseRoll):
    """
    Roll that implements the Ninja "wound check bonus" ability:
    "Dice < 5 on wound checks get bonus of ability_level * (5 - X)."

    At level 1, all dice effectively have minimum 5.
    At level 2, die rolling 1 becomes 1 + 2*(5-1) = 9, etc.
    """

    def __init__(self, rolled, kept, ability_level=1, faces=10, explode=True, die_provider=None):
        super().__init__(rolled, kept, faces, explode, die_provider)
        if not isinstance(ability_level, int) or ability_level < 1:
            raise ValueError("ability_level must be a positive int")
        self._ability_level = ability_level
        self._dice = []

    def dice(self):
        return self._dice

    def roll(self):
        dice = [self.roll_die(faces=self.faces(), explode=self.explode()) for _ in range(self._rolled)]
        # Apply wound check bonus: dice < 5 get bonus of ability_level * (5 - X)
        adjusted = []
        for d in dice:
            if d < 5:
                bonus = self._ability_level * (5 - d)
                adjusted.append(d + bonus)
            else:
                adjusted.append(d)
        adjusted.sort(reverse=True)
        self._dice = adjusted
        return sum(adjusted[:self._kept]) + self._bonus


class NinjaDamageKeepRoll(BaseRoll):
    """
    Roll that implements the Ninja "damage keeping bonus" ability:
    "Keep 2 extra lowest unkept dice on damage rolls."

    Keeps the highest K dice (normal) PLUS the extra_lowest lowest
    from the remaining unkept dice.
    E.g., rolling 7 keeping 3 with extra_lowest=2:
    keep the top 3 + bottom 2 of the remaining 4.
    """

    def __init__(self, rolled, kept, extra_lowest=0, faces=10, explode=True, die_provider=None):
        # Normalize before storing extra_lowest so we know the real kept count
        (norm_rolled, norm_kept, norm_bonus) = normalize_roll_params(rolled, kept)
        super().__init__(norm_rolled, norm_kept, faces, explode, die_provider)
        if not isinstance(extra_lowest, int) or extra_lowest < 0:
            raise ValueError("extra_lowest must be a non-negative int")
        self._extra_lowest = extra_lowest
        self._dice = []

    def dice(self):
        return self._dice

    def roll(self):
        dice = [self.roll_die(faces=self.faces(), explode=self.explode()) for _ in range(self._rolled)]
        dice.sort(reverse=True)
        self._dice = dice
        # Keep normal top dice
        kept_dice = dice[:self._kept]
        # Keep extra lowest from the unkept dice
        unkept = dice[self._kept:]
        if self._extra_lowest > 0 and len(unkept) > 0:
            # Take the lowest N from unkept (unkept is sorted descending, so take from end)
            extra_count = min(self._extra_lowest, len(unkept))
            extra_dice = unkept[-extra_count:]
            kept_dice.extend(extra_dice)
        return sum(kept_dice) + self._bonus
