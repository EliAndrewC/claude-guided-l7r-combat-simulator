#!/usr/bin/env python3

#
# initiative_actions.py
#
# Class to represent a character's unspent actions.
#

class InitiativeAction(object):
  '''
  Unspent action dice that a character is spending to take an
  action.

  A character may spend one or more action dice to take an action.

  The phase of the action is considered to be the action's tempo
  (the phase in which it was originally available). Some characters
  get a bonus for holding actions and spending them later.
  '''
  def __init__(self, dice, phase, is_interrupt=False):
    if not isinstance(dice, list):
      raise ValueError('InitiativeAction dice must be list of ints')
    for die in dice:
      if not isinstance(die, int):
        raise ValueError('InitiativeAction dice must be list of ints')
    if not isinstance(phase, int):
      raise ValueError('InitiativeAction phase must be int')
    if not isinstance(is_interrupt, bool):
      raise ValueError('InitiativeAction is_interrupt must be bool')
    self._dice = dice
    self._phase = phase
    self._is_interrupt = is_interrupt

  def dice(self):
    '''
    dice() -> list of ints

    Return the action dice that were spent for this action.
    '''
    return self._dice

  def is_interrupt(self):
    '''
    is_interrupt() -> bool

    Returns whether this is an interrupt action.
    '''
    return self._is_interrupt

  def phase(self):
    '''
    phase() -> int

    Return the phase for this action. An action from an earlier phase may be used in a later phase.
    '''
    return self._phase

