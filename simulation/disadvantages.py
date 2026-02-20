#!/usr/bin/env python3

#
# disadvantages.py
#
# Defines disadvantages that a character may take in the L7R combat simulator.
#

DISADVANTAGES = {
  'bad reputation': -3,
  'clan animosity': -4,
  'contrary': -5,
  'dark secret': -6,
  'discordant': -12,
  'driven': -5,
  'emotional': -3,
  'family obligation': -2,
  'humble': -2,
  'jealousy': -3,
  'long temper': -5,
  'meddler': -2,
  'permanent wound': -12,
  'poor': -4,
  'proud': -2,
  'silk mouthed': -3,
  'slow healer': -3,
  'short temper': -8,
  'thoughtless': -5,
  'transparent': -12,
  'unconventional': -4,
  'unkempt': -4,
  'unlucky': -8,
  'vain': -2,
  'withdrawn': -4
}

class Disadvantage(object):
  def __init__(self, name):
    if name not in DISADVANTAGES.keys():
      raise ValueError('{} is not a valid Disadvantage'.format(name))
    self._name = name

  def cost(self):
    return DISADVANTAGES[self.name()]

  def name(self):
    return self._name

