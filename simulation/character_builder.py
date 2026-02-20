#!/usr/bin/env python3

#
# character_builder.py
#
# Character builder for L7R combat simulator.
#

import os
import uuid
import yaml

from simulation.advantages import Advantage
from simulation.character import Character
from simulation.disadvantages import Disadvantage
from simulation.professions import Profession, get_profession_ability
from simulation.skills import Skill
from simulation.strategies import Strategy


class CharacterBuilder(object):
  '''
  Initial character builder class.
  Supports choosing a school or profession and setting XP available.
  Any other operation should be done after choosing a profession or school.
  '''
  def __init__(self, xp=100):
    self._name = None
    self._xp = xp

  def generic(self):
    return _BaseCharacterBuilder(name=self.name(), xp=self.xp())

  def name(self):
    return self._name

  def with_name(self, name):
    self._name = name
    return self

  def with_profession(self):
    '''
    with_profession() -> ProfessionCharacterBuilder

    Build a peasant character who can take profession abilities.
    '''
    return _ProfessionCharacterBuilder(name=self.name(), xp=self.xp())

  def with_school(self, school):
    '''
    with_school(school) -> SchoolCharacterBuilder

    Build a character with a samurai school.
    '''
    return _SchoolCharacterBuilder(school, name=self.name(), xp=self.xp())

  def with_xp(self, xp):
    '''
    with_xp(xp) -> self
      xp (int): number of experience points for the character.

    Set the XP for this character.
    '''
    self._xp = xp
    return self

  def xp(self):
    '''
    xp() -> int

    Returns the XP available to build this character.
    '''
    return self._xp


class _BaseCharacterBuilder(object):
  '''
  Provides basic functions for building a character.
  '''
  def __init__(self, name=None, xp=100):
    if name is None:
      self.name = uuid.uuid4().hex
    else:
      if not isinstance(name, str):
        raise ValueError('CharacterBuilder name must be str')
      self._name = name
    self._character = Character(name)
    self._discounts = {}
    self._max_rings = {}
    self._xp = xp
    self._xp_spent = 0

  def afford_ring(self, ring, next_rank):
    discount = self.character()._discounts.get(ring, 0)
    cost = (next_rank * 5) - discount
    return self.xp_available() >= cost

  def afford_skill(self, skill, next_rank):
    return self.xp_available() >= get_skill_cost(next_rank)

  def build(self):
    return self.character()

  def buy_ring(self, ring, rank):
    if rank > self.max_ring(ring):
      raise ValueError('May not raise {} past {}'.format(ring, self.max_ring(ring)))
    cost = self.calculate_ring_cost(ring, rank)
    if self.xp_available() >= cost:
      self.spend_xp(cost)
      self.character().set_ring(ring, rank)
      return self
    else:
      raise ValueError('Not enough XP')

  def buy_skill(self, skill, rank):
    if rank > 5:
      raise ValueError('May not raise skill past 5')
    # enforce special rule about Attack and Parry
    if skill == 'parry':
      if rank > self.character().skill('attack') + 1:
        raise ValueError('May not raise Parry more than one rank above Attack')
    cost = self.calculate_skill_cost(skill, rank)
    if self.xp_available() >= cost:
      self.spend_xp(cost)
      self.character().set_skill(skill, rank)
      return self
    else:
      raise ValueError('Not enough XP')
  
  def calculate_ring_cost(self, ring, rank):
    discount = self.character()._discounts.get(ring, 0)
    if rank > self.max_ring(ring):
      raise ValueError('May not raise {} past {}'.format(ring, self.max_ring(ring)))
    original_rank = self.character().ring(ring)
    return sum([(5 * i) for i in range(original_rank, rank)]) - discount

  def calculate_skill_cost(self, skill, rank):
    if rank > 5:
      raise ValueError('May not raise skill above 5')
    original_rank = self.character().skill(skill)
    return Skill(skill).get().cost(rank, original_rank)

  def character(self):
    return self._character

  def max_ring(self, ring):
    return 5

  def name(self):
    return self._name

  def set_strategy(self, event, strategy):
    if not isinstance(strategy, Strategy):
      raise ValueError('set_strategy requires a Strategy object')
    self.character().set_strategy(event, strategy)
    return self

  def spend_xp(self, amount):
    if self.xp() - self.xp_spent() < amount:
      raise ValueError('Not enough XP')
    self._xp_spent += amount

  def take_advantage(self, advantage):
    cost = Advantage(advantage).cost()
    self.spend_xp(cost)
    self.character().take_advantage(advantage)
    return self

  def take_disadvantage(self, disadvantage):
    cost = Disadvantage(disadvantage).cost()
    self.spend_xp(cost)
    self.character().take_disadvantage(disadvantage)
    return self

  def xp(self):
    return self._xp

  def xp_available(self):
    return self.xp() - self.xp_spent()

  def xp_spent(self):
    return self._xp_spent


class _ProfessionCharacterBuilder(_BaseCharacterBuilder):
  '''
  Builder for a character with a peasant profession.
  '''
  def __init__(self, name=None, xp=100):
    super().__init__(name, xp)
    self._profession = Profession()
    self.character().set_profession(self._profession)

  def profession(self):
    '''
    profession() -> Profession

    Returns the Profession instance for this character.
    '''
    return self._profession

  def take_ability(self, name):
    '''
    take_ability(name) -> _ProfessionCharacterBuilder
      name (str): name of ability to take

    Take a level in the named ability.
    '''
    abilities_available = ((self.xp() - 100) // 15) + 1
    if len(self.profession()) >= abilities_available:
      raise RuntimeError('May not take any more abilities')
    self.profession().take_ability(name)
    get_profession_ability(name).apply(self.character(), self.profession())
    return self


class _SchoolCharacterBuilder(_BaseCharacterBuilder):
  '''
  Builder for a character with a samurai school.
  '''
  def __init__(self, school, name=None, xp=100):
    super().__init__(name, xp)
    self._school = school
    self._school_rank = 1
    self.initialize_school()

  def buy_skill(self, skill, rank):
    super().buy_skill(skill, rank)
    if skill in self.school().school_knacks():
      self.update_school_rank()
    return self

  def initialize_school(self):
    self.character().set_school(self.school())
    self.school().apply_school_ring(self.character())
    self.school().apply_special_ability(self.character())
    for skill in self.school().school_knacks():
      self.character().set_skill(skill, 1)
    self.school().apply_rank_one_ability(self.character())

  def max_ring(self, ring):
    if ring == self.school().school_ring() and self.school_rank() >= 4:
      return 6
    else:
      return 5

  def school(self):
    return self._school

  def school_rank(self):
    return self._school_rank

  def update_school_rank(self):
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

