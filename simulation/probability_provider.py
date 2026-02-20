#!/usr/bin/env python3

#
# probability_provider.py
#
# Class to hold and provide information about probabilities to help make decisions.
#

from abc import ABC, abstractmethod
import os

from simulation.log import logger
from simulation.roll_params import normalize_roll_params

script_path = os.path.realpath(__file__)
script_dirpath = os.path.split(script_path)[0]


class ProbabilityProvider(ABC):
  @abstractmethod
  def initialize(self):
    '''
    initialize()

    Initialize this probability provider by generating or loading probability data.
    '''
    pass

  @abstractmethod
  def mean_roll(self, rolled, kept, explode=True):
    '''
    mean_roll(rolled, kept, explode=True) -> int
      rolled (int): rolled dice
      kept (int): kept dice
      explode (bool): whether or not tens reroll

    Returns the mean result of a roll with the given parameters.
    '''
    pass

  @abstractmethod
  def p(self, x, rolled, kept, explode=True):
    '''
    p(x, rolled, kept, explode=True) -> float
      x (int): target number
      rolled (int): number of rolled dice
      kept (int): number of kept dice
      explode (bool): whether or not tens reroll

    Return the probability of rolling Target Number x with the given parameters.
    '''
    pass


class DefaultProbabilityProvider(ProbabilityProvider):
  def __init__(self):
    self._mean_rolls = {}
    self._probabilities = {}
    # default probability chart data paths
    self._data_path_probabilities_rerolled = os.path.join(script_dirpath, 'probabilities_rerolled.txt')
    self._data_path_probabilities_not_rerolled = os.path.join(script_dirpath, 'probabilities_not_rerolled.txt')

  def initialize(self):
    '''
    initialize()

    Loads probability data to help calculate the probability of making rolls.
    '''
    self._probabilities = {}
    self._mean_rolls = { True: {}, False: {} }
    self._probabilities[True] = self._load_probability_file(self._data_path_probabilities_rerolled)
    self._probabilities[False] = self._load_probability_file(self._data_path_probabilities_not_rerolled)
    self._load_mean_roll_data(True)
    self._load_mean_roll_data(False)

  def _load_probability_file(self, path):
    data = {}
    with open(path, 'r') as f:
      for line in f:
        if line.startswith('Rolled'):
          continue
        line = line.strip()
        tokens = line.split('\t')
        roll = tokens[0]
        probabilities = [float(p) for p in tokens[1:-1]]
        probabilities.insert(0, 1.00)
        data[roll] = probabilities
    return data

  def _load_mean_roll_data(self, explode):
    for roll in self._probabilities[explode].keys():
      prev_i = 0
      for i, p in enumerate(self._probabilities[explode][roll]):
        if p < 0.50:
          self._mean_rolls[explode][roll] = prev_i
          break
        prev_i = i

  def mean_roll(self, rolled, kept, explode=True):
    '''
    mean_roll(rolled, kept, explode=True) -> int
      rolled (int): rolled dice
      kept (int): kept dice
      explode (bool): whether or not tens reroll

    Returns the mean result of a roll with the given parameters.
    '''
    rolled, kept, bonus = normalize_roll_params(rolled, kept)
    roll_str = '{}k{}'.format(rolled, kept)
    expected = self._mean_rolls[explode][roll_str] + bonus
    #logger.debug('Expected roll for {}: {}'.format(roll_str, expected))
    return expected

  def p(self, x, rolled, kept, explode=True):
    '''
    p(x, rolled, kept, explode=True) -> float
      x (int): target number
      rolled (int): number of rolled dice
      kept (int): number of kept dice
      explode (bool): whether or not tens reroll

    Return the probability of rolling Target Number x with the given parameters.
    '''
    roll_str = '{}k{}'.format(rolled, kept)
    max_x = len(self._probabilities[explode][roll_str]) - 1
    if x <=0:
      return 1.0
    elif x > max_x:
      return self._probabilities[explode][roll_str][max_x]
    else:
      return self._probabilities[explode][roll_str][x]

