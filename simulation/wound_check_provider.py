#!/usr/bin/env python3

from abc import ABC, abstractmethod


class WoundCheckProvider(ABC):
  '''
  Class to calculate wound checks for a character.
  '''
  @abstractmethod
  def wound_check(self, character, roll, lw=None):
    pass

class DefaultWoundCheckProvider(WoundCheckProvider):
  def wound_check(self, roll, lw):
    '''
    wound_check(roll, lw) -> int
      wound_check_roll (int): wound check roll
      lw (int): light wounds taken. Defaults to character's current lw total.

    Returns the number of Serious Wounds that would be taken
    from a wound check roll against a damage amount.

    This function is only a Serious Wound calculator. It does not
    cause the character to take Serious Wounds when used. To
    inflict Serious Wounds, use the take_sw function.
    '''
    if roll < lw:
      return 1 + ((lw - roll) // 10)
    else:
      return 0

DEFAULT_WOUND_CHECK_PROVIDER = DefaultWoundCheckProvider()

