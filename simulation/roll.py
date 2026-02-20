#!/usr/bin/env python3

#
# roll.py
#
# Class to roll dice using L7R homebrew rules.
#

from abc import ABC, abstractmethod
import random

from simulation.roll_params import normalize_roll_params


class DieProvider(ABC):
  '''
  Simulated dice for the L7R combat simulator.
  '''
  @abstractmethod
  def roll_die(self, faces=10, explode=True):
    '''
    roll_die(faces=10, explode=True) -> int
      faces (int): number of die faces
      explode (bool): whether to explode dice (see below)
    
    Returns the result of rolling a simulated die with the given
    number of faces.

    An "exploding" die adds to the result through recursion if the
    number of faces is rolled.
    '''
    pass


class DefaultDieProvider(DieProvider):
  '''
  Simulated dice for the L7R combat simulator.

  Use the singleton instance of this class to avoid excessive
  object creation during simulations.
  '''
  def roll_die(self, faces=10, explode=True):
    '''
    roll_die(faces=10, explode=True) -> int
      faces (int): number of die faces
      explode (bool): whether to explode dice (see below)
    
    Returns the result of rolling a simulated die with the given
    number of faces.

    An "exploding" die adds to the result through recursion if the
    number of faces is rolled.
    '''
    result = random.randint(1, faces)
    if (explode and result == faces):
      return result + self.roll_die(faces, explode)
    else:
      return result

# singleton DefaultDieProvider instance
DEFAULT_DIE_PROVIDER = DefaultDieProvider()


class TestDice(DieProvider):
  '''
  Die source that provides rigged dice for testing.
  Acts as a FIFO queue. You append or extend the die source with
  rolled dice (ints), and when a Roll gets results from this source,
  it pops the earliest queued results.
  '''
  def __init__(self):
    self._dice = []

  def clear(self):
    '''
    clear()

    Clears the dice queue to reset for a new test case.
    '''
    self._dice.clear()

  def extend(self, dice):
    '''
    extend(dice)
      dice: list of int

      Extend this die source's results with a list of rolled dice.
    '''
    self._dice.extend(dice)

  def append(self, die):
    '''
    append(die)
      die: int

      Append a rolled die to this die source.
    '''
    self._dice.append(die)

  def roll_die(self, faces=10, explode=True):
    die = self._dice.pop(0)
    if explode and die == faces:
      return die + self.roll_die(faces, explode)
    else:
      return die

  def __len__(self):
    return len(self._dice)


class BaseRoll(object):
  def __init__(self, rolled, kept, faces=10, explode=True, die_provider=None):
    # normalize roll parameters
    (self._rolled, self._kept, self._bonus) = normalize_roll_params(rolled, kept)
    # set die faces
    self._faces = faces
    # set exploding behavior
    self._explode = explode
    # set die source
    if die_provider is not None:
      if not isinstance(die_provider, DieProvider):
        raise ValueError('die_provider must be a DieProvider')
      self._die_provider = die_provider
    else:
      self._die_provider = DEFAULT_DIE_PROVIDER

  def die_provider(self):
    return self._die_provider

  def explode(self):
    return self._explode

  def faces(self):
    return self._faces

  def roll_die(self, faces=10, explode=True):
    '''
    roll_die(faces=10, explode=True) -> int
      faces (int): number of die faces
      explode (bool): whether to explode dice (see below)
    
    Returns the result of rolling a simulated die with the given
    number of faces.

    An "exploding" die adds to the result through recursion if the
    number of faces is rolled.
    '''
    return self.die_provider().roll_die(faces, explode)

  def set_die_provider(self, die_provider):
    if not isinstance(die_provider, DieProvider):
      raise ValueError('set_die_provider requires a DieProvider')
    self._die_provider = die_provider


class Roll(BaseRoll):
  def __init__(self, rolled, kept, faces=10, explode=True, die_provider=None):
    super().__init__(rolled, kept, faces, explode, die_provider)

  def roll(self):
    dice = [self.die_provider().roll_die(faces=self.faces(), explode=self.explode()) for n in range(self._rolled)]
    dice.sort(reverse=True)
    return sum(dice[:self._kept]) + self._bonus


class InitiativeRoll(BaseRoll):
  def __init__(self, rolled, kept, faces=10, die_provider=None):
    super().__init__(rolled, kept, faces, False, die_provider)

  def roll(self):
    dice = sorted([self.roll_die(faces=self.faces(), explode=False) for n in range(self._rolled)])
    return dice[:self._kept]

