#!/usr/bin/env python3

#
# schools.py
#
# Character Schools for L7R combat simulator.
#

from abc import ABC, abstractmethod

from simulation.modifiers import FreeRaise


class School(ABC):
  @abstractmethod
  def ap_base_skill(self):
    pass

  @abstractmethod
  def ap_skills(self):
    pass

  @abstractmethod
  def apply_ap(self, character):
    pass

  @abstractmethod
  def apply_special_ability(self, character):
    pass

  @abstractmethod
  def apply_rank_one_ability(self, character):
    pass

  @abstractmethod
  def apply_rank_two_ability(self, character):
    pass

  @abstractmethod
  def apply_rank_three_ability(self, character):
    pass

  @abstractmethod
  def apply_rank_four_ability(self, character):
    pass

  @abstractmethod
  def apply_rank_five_ability(self, character):
    pass

  @abstractmethod
  def extra_rolled(self):
    pass

  @abstractmethod
  def free_raise_skills(self):
    pass

  @abstractmethod
  def name(self):
    pass

  @abstractmethod
  def school_knacks(self):
    pass

  @abstractmethod
  def school_ring(self):
    pass


class BaseSchool(School):
  def __init__(self):
    self._ap_base_skill = None
    self._ap_skills = []
    self._free_raises_skills = []
    self._skills = dict([(skill, 1) for skill in self.school_knacks()])

  def ap_base_skill(self):
    '''
    ap_base_skill() -> str

    Return this school's base skill for calculating Adventure Points
    (Third Dan Free Raises).
    Returns None if the school does not use Adventure Points.
    '''
    return self._ap_base_skill

  def ap_skills(self):
    return self._ap_skills

  def apply_ap(self, character):
    if self.ap_base_skill() is not None:
      character.set_ap_base_skill(self.ap_base_skill())
      character.set_ap_skills(self.ap_skills())

  def apply_rank_one_ability(self, character):
    '''
    apply_rank_one_ability(character)

    Apply this school's extra rolled dice (the standard 1st Dan ability).
    '''
    for skill in self.extra_rolled():
      character.set_extra_rolled(skill, 1)

  def apply_rank_two_ability(self, character):
    '''
    apply_rank_two_ability(character)

    Apply this school's Free Raises (the standard 2nd Dan ability).
    '''
    for skill in self.free_raise_skills():
      character.add_modifier(FreeRaise(character, skill))

  def apply_school_ability(self, character, rank):
    '''
    apply_school_ability(character, rank)

    Apply this school's rank ability to a character.
    '''
    if rank == 1:
      self.apply_rank_one_ability(character)
    elif rank == 2:
      self.apply_rank_two_ability(character)
    elif rank == 3:
      self.apply_rank_three_ability(character)
    elif rank == 4:
      self.apply_rank_four_ability(character)
    elif rank == 5:
      self.apply_rank_five_ability(character)

  def apply_school_ring_raise_and_discount(self, character):
    '''
    apply_school_ring_raise_and_discount(character)

    Raise the character's school ring and apply a discount.
    This is a standard 4th Dan bonus.
    '''
    cur_rank = character.ring(self.school_ring())
    character.set_ring(self.school_ring(), cur_rank + 1)
    character.add_discount(self.school_ring(), 5)

  def apply_rank_three_ability(self, character):
    '''
    apply_rank_three_ability(character)

    Apply this school's 3rd Dan ability to the character.
    '''
    raise NotImplementedError()

  def apply_rank_four_ability(self, character):
    '''
    apply_rank_four_ability(character)

    Implementations should apply this school's 4th Dan ability to the character.
    '''
    raise NotImplementedError()

  def apply_rank_five_ability(self, character):
    '''
    apply_rank_five_ability(character)

    Implementations should apply the school's 5th Dan ability.
    '''
    raise NotImplementedError()

  def apply_school_ring(self, character):
    '''
    apply_school_ring(character)

    Raise this character's school ring from 2 to 3.
    '''
    if character.ring(self.school_ring()) != 2:
      raise ValueError('{}\'s {} ring is not 2, cannot apply school ring bonus'.format(character.name(), self.school_ring()))
    character.set_ring(self.school_ring(), 3)

  def apply_special_ability(self, character):
    '''
    apply_special_ability(character)

    Apply this school's special ability to the character.
    This usually involves setting special listeners or strategies.
    '''
    raise NotImplementedError()

  def free_raise_skills(self):
    '''
    free_raise_skills() -> list of str

    Implementations should return the list of skills that receive Free Raises from this school at 2nd Dan.
    '''
    raise NotImplementedError()

  def extra_rolled(self):
    '''
    extra_rolled() -> list of str

    Implementations should return the list of things where they get an extra rolled die.
    '''
    raise NotImplementedError()

  def name(self):
    '''
    name() -> str

    Implementations should return the name of the School.
    '''
    raise NotImplementedError()

  def school_knacks(self):
    '''
    school_knacks() -> list of str

    Implementations should return their list of School Knacks.
    '''
    raise NotImplementedError()

  def school_ring(self):
    '''
    school_ring() -> str

    Implementations should return the name of their School Ring.
    '''
    raise NotImplementedError()

