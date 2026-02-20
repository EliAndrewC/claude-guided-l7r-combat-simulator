#!/usr/bin/env python3

#
# context.py
#
# Context class for L7R combat simulator.
#
# The context class is passed around to provide contextual
# information about timing and characters, to collect features
# for later analysis, and to provide data that is best initialized
# once and reused across many simulations, such as probability
# data.
#

from simulation import events
from simulation.exceptions import CombatEnded
from simulation.features import TrialFeatures
from simulation.probability_provider import DefaultProbabilityProvider


class EngineContext(object):
  '''
  Portable context for simulator engines.
  Mainly carries around the list of characters.
  '''

  def __init__(self, groups=[], round=0, phase=0):
    # initialize groups
    self._groups = groups
    if len(self._groups) < 2:
      raise ValueError("Must have at least two groups")
    # initialize characters
    self._characters = []
    for group in groups:
      if len(group) < 1:
        raise ValueError('A group must contain at least one character')
      for character in group:
        self._characters.append(character)
    if len(self._characters) < 2:
      raise ValueError("Must have at least two characters")
    # initialize list of characters who are "still moving"
    # characters are "still moving" until they have held an action in the current phase
    self._still_moving = []
    # features for analysis
    self._features = TrialFeatures()
    # probability data provider
    self._probability_provider = DefaultProbabilityProvider()
    # initialize timing
    self._round = round
    self._phase = phase

  def characters(self):
    return self._characters

  def groups(self):
    return self._groups

  def features(self):
    return self._features

  def initialize(self):
    self.probability_provider().initialize()

  def is_anybody_still_moving(self):
    return len(self._still_moving) > 0

  def is_still_moving(self, character):
    return character in self._still_moving

  def mean_roll(self, rolled, kept, explode=True):
    return self.probability_provider().mean_roll(rolled, kept, explode)

  def next_phase(self):
    if (self._phase == 10):
      raise RuntimeError('Cannot go to next phase after 10')
    self._phase += 1

  def next_round(self):
    self._round += 1
    self._phase = 0

  def phase(self):
    return self._phase

  def p(self, x, rolled, kept, explode=True):
    return self.probability_provider().p(x, rolled, kept, explode)

  def probability_provider(self):
    return self._probability_provider

  def reevaluate_initiative(self):
    max_actions = max([len(character.actions()) for character in self._characters if character.is_fighting()])
    self._characters.sort(key=lambda character: character.initiative_priority(max_actions))

  def reset(self):
    self._features.clear()
    self._phase = 0
    self._round = 0
    for character in self._characters:
      character.reset()
    self._still_moving.clear()

  def reset_still_moving(self):
    '''
    reset_still_moving()

    Builds a list of characters who are still fighting
    and who haven't held an action in the current phase.
    '''
    self._still_moving.clear()
    for character in self._characters:
      if character.is_fighting():
        self._still_moving.append(character)

  def round(self):
    return self._round

  def stop_moving(self, character):
    '''
    stop_moving(character)

    Observes that a character has stopped moving for the current phase.
    Should be called on a StatusEvent that indicates defeat
    
    '''
    if character in self._still_moving:
      self._still_moving.remove(character)

  def test_group(self):
    # the test group is supposed to be the second group
    return self._groups[1]

  def time(self):
    return (self._round, self._phase)

  def update_status(self, event):
    if isinstance(event, events.NotMovingEvent):
      self.stop_moving(event.subject)
    elif isinstance(event, events.DefeatEvent):
      self.stop_moving(event.subject)
      # TODO: support aiuchi (both sides defeated)
      for i, group in enumerate(self._groups):
        fighting = False
        for character in group:
          if character.is_fighting():
            fighting = True
            break
        if not fighting:
          if i == 0:
            # the test group won
            self.features().observe_winner(1)
          else:
            # the control group won
            self.features().observe_winner(-1)
          raise CombatEnded('Combat is over')

