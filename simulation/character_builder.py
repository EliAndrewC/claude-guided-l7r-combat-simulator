#!/usr/bin/env python3

#
# character_builder.py
#
# Character builder for L7R combat simulator.
#

import uuid

from simulation.character import Character
from simulation.mechanics.advantages import Advantage
from simulation.mechanics.disadvantages import Disadvantage
from simulation.mechanics.skills import Skill
from simulation.professions import Profession, get_profession_ability
from simulation.schools.base import BaseSchool, School
from simulation.strategies.base import Strategy


class CharacterBuilder:
    """
    Initial character builder class.
    Supports choosing a school or profession and setting XP available.
    Any other operation should be done after choosing a profession or school.
    """

    def __init__(self, xp: int = 100) -> None:
        self._name: str | None = None
        self._xp = xp

    def generic(self) -> "_BaseCharacterBuilder":
        return _BaseCharacterBuilder(name=self.name(), xp=self.xp())

    def name(self) -> str | None:
        return self._name

    def with_name(self, name: str) -> "CharacterBuilder":
        self._name = name
        return self

    def with_profession(self) -> "_ProfessionCharacterBuilder":
        """
        with_profession() -> ProfessionCharacterBuilder

        Build a peasant character who can take profession abilities.
        """
        return _ProfessionCharacterBuilder(name=self.name(), xp=self.xp())

    def with_school(self, school: School) -> "_SchoolCharacterBuilder":
        """
        with_school(school) -> SchoolCharacterBuilder

        Build a character with a samurai school.
        """
        return _SchoolCharacterBuilder(school, name=self.name(), xp=self.xp())

    def with_xp(self, xp: int) -> "CharacterBuilder":
        """
        with_xp(xp) -> self
          xp (int): number of experience points for the character.

        Set the XP for this character.
        """
        self._xp = xp
        return self

    def xp(self) -> int:
        """
        xp() -> int

        Returns the XP available to build this character.
        """
        return self._xp


class _BaseCharacterBuilder:
    """
    Provides basic functions for building a character.
    """

    def __init__(self, name: str | None = None, xp: int = 100) -> None:
        if name is None:
            self._name: str = uuid.uuid4().hex
        else:
            if not isinstance(name, str):
                raise ValueError("CharacterBuilder name must be str")
            self._name = name
        self._character = Character(name, xp=xp)
        self._discounts: dict[str, int] = {}
        self._max_rings: dict[str, int] = {}
        self._xp = xp
        self._xp_spent = 0

    def afford_ring(self, ring: str, next_rank: int) -> bool:
        discount = self.character()._discounts.get(ring, 0)
        cost = (next_rank * 5) - discount
        return self.xp_available() >= cost

    def afford_skill(self, skill: str, next_rank: int) -> bool:
        return self.xp_available() >= self.calculate_skill_cost(skill, next_rank)

    def build(self) -> Character:
        return self.character()

    def buy_ring(self, ring: str, rank: int) -> "_BaseCharacterBuilder":
        if rank > self.max_ring(ring):
            raise ValueError(f"May not raise {ring} past {self.max_ring(ring)}")
        cost = self.calculate_ring_cost(ring, rank)
        if self.xp_available() >= cost:
            self.spend_xp(cost)
            self.character().set_ring(ring, rank)
            return self
        else:
            raise ValueError("Not enough XP")

    def buy_skill(self, skill: str, rank: int) -> "_BaseCharacterBuilder":
        if rank > 5:
            raise ValueError("May not raise skill past 5")
        # enforce special rule about Attack and Parry
        if skill == "parry":
            if rank > self.character().skill("attack") + 1:
                raise ValueError("May not raise Parry more than one rank above Attack")
        cost = self.calculate_skill_cost(skill, rank)
        if self.xp_available() >= cost:
            self.spend_xp(cost)
            self.character().set_skill(skill, rank)
            return self
        else:
            raise ValueError("Not enough XP")

    def calculate_ring_cost(self, ring: str, rank: int) -> int:
        discount = self.character()._discounts.get(ring, 0)
        if rank > self.max_ring(ring):
            raise ValueError(f"May not raise {ring} past {self.max_ring(ring)}")
        original_rank = self.character().ring(ring)
        return sum([(5 * i) for i in range(original_rank + 1, rank + 1)]) - discount

    def calculate_skill_cost(self, skill: str, rank: int) -> int:
        if rank > 5:
            raise ValueError("May not raise skill above 5")
        original_rank = self.character().skill(skill)
        return Skill(skill).get().cost(rank, original_rank)

    def character(self) -> Character:
        return self._character

    def max_ring(self, ring: str) -> int:
        return 5

    def name(self) -> str:
        return self._name

    def set_strategy(self, event: str, strategy: Strategy) -> "_BaseCharacterBuilder":
        if not isinstance(strategy, Strategy):
            raise ValueError("set_strategy requires a Strategy object")
        self.character().set_strategy(event, strategy)
        return self

    def spend_xp(self, amount: int) -> None:
        if self.xp() - self.xp_spent() < amount:
            raise ValueError("Not enough XP")
        self._xp_spent += amount

    def take_advantage(self, advantage: str) -> "_BaseCharacterBuilder":
        cost = Advantage(advantage).cost()
        self.spend_xp(cost)
        self.character().take_advantage(advantage)
        return self

    def take_disadvantage(self, disadvantage: str) -> "_BaseCharacterBuilder":
        cost = Disadvantage(disadvantage).cost()
        self.spend_xp(cost)
        self.character().take_disadvantage(disadvantage)
        return self

    def xp(self) -> int:
        return self._xp

    def xp_available(self) -> int:
        return self.xp() - self.xp_spent()

    def xp_spent(self) -> int:
        return self._xp_spent


class _ProfessionCharacterBuilder(_BaseCharacterBuilder):
    """
    Builder for a character with a peasant profession.
    """

    def __init__(self, name: str | None = None, xp: int = 100) -> None:
        super().__init__(name, xp)
        self._profession = Profession()
        self.character().set_profession(self._profession)

    def profession(self) -> Profession:
        """
        profession() -> Profession

        Returns the Profession instance for this character.
        """
        return self._profession

    def take_ability(self, name: str) -> "_ProfessionCharacterBuilder":
        """
        take_ability(name) -> _ProfessionCharacterBuilder
          name (str): name of ability to take

        Take a level in the named ability.
        """
        abilities_available = ((self.xp() - 100) // 15) + 1
        if len(self.profession()) >= abilities_available:
            raise RuntimeError("May not take any more abilities")
        self.profession().take_ability(name)
        get_profession_ability(name).apply(self.character(), self.profession())
        return self


class _SchoolCharacterBuilder(_BaseCharacterBuilder):
    """
    Builder for a character with a samurai school.
    """

    def __init__(self, school: School, name: str | None = None, xp: int = 100) -> None:
        super().__init__(name, xp)
        self._school = school
        self._school_rank = 1
        self.initialize_school()

    def buy_skill(self, skill: str, rank: int) -> "_SchoolCharacterBuilder":
        super().buy_skill(skill, rank)
        if skill in self.school().school_knacks():
            self.update_school_rank()
        return self

    def initialize_school(self) -> None:
        self.character().set_school(self.school())
        school = self.school()
        if isinstance(school, BaseSchool):
            school.apply_school_ring(self.character())
        school.apply_special_ability(self.character())
        for skill in school.school_knacks():
            self.character().set_skill(skill, 1)
        school.apply_rank_one_ability(self.character())

    def max_ring(self, ring: str) -> int:
        if ring == self.school().school_ring() and self.school_rank() >= 4:
            return 6
        else:
            return 5

    def school(self) -> School:
        return self._school

    def school_rank(self) -> int:
        return self._school_rank

    def update_school_rank(self) -> None:
        cur_rank = min([self.character().skill(skill) for skill in self.school().school_knacks()])
        if cur_rank >= 2 and self.school_rank() < 2:
            self.school().apply_rank_two_ability(self.character())
        if cur_rank >= 3 and self.school_rank() < 3:
            self.school().apply_rank_three_ability(self.character())
        if cur_rank >= 4 and self.school_rank() < 4:
            self.school().apply_rank_four_ability(self.character())
        if cur_rank == 5 and self.school_rank() < 5:
            self.school().apply_rank_five_ability(self.character())
        self._school_rank = cur_rank
