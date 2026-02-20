#!/usr/bin/env python3

#
# roll_provider.py
#
# Alternate roll providers for L7R combat simulations.
#

from abc import ABC, abstractmethod

from simulation.roll import InitiativeRoll, Roll


class RollProvider(ABC):
  @abstractmethod
  def die_provider(self):
    pass

  @abstractmethod
  def get_damage_roll(self, rolled, kept):
    pass

  @abstractmethod
  def get_initiative_roll(self, rolled, kept):
    pass

  @abstractmethod
  def get_skill_roll(self, skill, rolled, kept, explode=True):
    pass

  @abstractmethod
  def get_wound_check_roll(self):
    pass

  @abstractmethod
  def set_die_provider(self, die_provider):
    pass


class DefaultRollProvider(RollProvider):
  def __init__(self, die_provider=None):
    self._die_provider = die_provider

  def die_provider(self):
    return self._die_provider

  def get_damage_roll(self, rolled, kept):
    '''
    get_damage_roll(rolled, kept) -> int
      rolled (int): number of rolled dice
      kept (int): number of kept dice
    
    Return a damage roll using the specified number of rolled and kept dice.
    '''
    return Roll(rolled, kept, die_provider=self.die_provider()).roll()

  def get_initiative_roll(self, rolled, kept):
    '''
    get_skill_roll(skill, rolled, kept) -> int
      skill (str): name of skill being used
      rolled (int): number of rolled dice
      kept (int): number of kept dice
    
    Return a skill roll using the specified number of rolled and kept dice.
    '''
    return InitiativeRoll(rolled, kept, die_provider=self.die_provider()).roll()

  def get_skill_roll(self, skill, rolled, kept, explode=True):
    '''
    get_skill_roll(skill, rolled, kept) -> int
      skill (str): name of skill being used
      rolled (int): number of rolled dice
      kept (int): number of kept dice
      explode (bool): whether tens should be rerolled
    
    Return a skill roll using the specified number of rolled and kept dice.
    '''
    return Roll(rolled, kept, die_provider=self.die_provider(), explode=explode).roll()

  def get_wound_check_roll(self, rolled, kept):
    '''
    get_wound_check_roll(rolled, kept) -> int
      rolled (int): number of rolled dice
      kept (int): number of kept dice
    
    Return a Wound Check roll using the specified number of rolled and kept dice.
    '''
    return Roll(rolled, kept, die_provider=self.die_provider()).roll()

  def set_die_provider(self, die_provider):
    if not isinstance(die_provider, DieProvider):
      raise ValueError('set_die_provider requires DieProvider')
    self._die_provider = die_provider


DEFAULT_ROLL_PROVIDER = DefaultRollProvider()


class TestRollProvider(RollProvider):
  '''
  TestRollProvider
  Class to provide predictable rolls for use in testing.
  '''
  def __init__(self):
    self._queues = {
      'damage': [],
      'initiative': [],
      'wound_check': []
    }
    self._observed_params = {
      'damage': [],
      'initiative': [],
      'wound_check': []
    }

  def die_provider(self):
    return None

  def get_damage_roll(self, rolled, kept):
    if len(self._queues['damage']) == 0:
      raise IndexError('No roll queued for damage')
    self._observed_params['damage'].append((rolled, kept))
    return self._queues['damage'].pop(0)

  def get_initiative_roll(self, rolled, kept):
    if len(self._queues['initiative']) == 0:
      raise IndexError('No roll queued for initiative')
    self._observed_params['initiative'].append((rolled, kept))
    return self._queues['initiative'].pop(0)

  def get_skill_roll(self, skill, rolled, kept, explode=True):
    if skill not in self._queues.keys():
      raise KeyError('No roll queued for ' + skill)
    elif len(self._queues[skill]) == 0:
      raise IndexError('No roll queued for ' + skill)
    if skill not in self._observed_params.keys():
      self._observed_params[skill] = []
    self._observed_params[skill].append((rolled, kept))
    return self._queues[skill].pop(0)

  def get_wound_check_roll(self, rolled, kept):
    if len(self._queues['wound_check']) == 0:
      raise IndexError('No roll queued for wound_check')
    self._observed_params['wound_check'].append((rolled, kept))
    return self._queues['wound_check'].pop(0)

  def pop_observed_params(self, roll_type):
    '''
    pop_observed_params(roll_type) -> tuple of ints
      roll_type (str): the type of roll of interest
        (either damage, initiative, wound_check,
        or a skill name)

    Pops and returns the oldest observed parameters for
    the given roll type.
    '''
    return self._observed_params[roll_type].pop(0)

  def put_damage_roll(self, result):
    self._queues['damage'].append(result)

  def put_initiative_roll(self, result):
    if isinstance(result, list):
      self._queues['initiative'].append(result)
    else:
      raise ValueError('Initiative rolls should be sequences of ints')

  def put_skill_roll(self, skill, result):
    if skill in self._queues.keys():
      self._queues[skill].append(result)
    else:
      self._queues[skill] = [result]

  def put_wound_check_roll(self, result):
    self._queues['wound_check'].append(result)

  def set_die_provider(self, die_provider):
    raise NotImplementedError()

