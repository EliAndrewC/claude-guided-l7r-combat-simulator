#!/usr/bin/env python3

#
# contested_actions.py
#
# Classes for contested actions in the L7R combat simulator.
#

from simulation.actions import Action

class ContestedAction(Action):
  '''
  ContestedAction represents an action where two characters make
  skill rolls against each other, and success depends on outrolling
  the other character.

  Contested rolls sometimes use the same ring and skill, but there
  are cases when the characters use different rings or skills.

  The character with the higher skill is awarded a bonus, to reward
  investment in skills.

  ContestedAction events require the use of two ContestedAction
  instances: one for the challenger, and one for the other
  character. Listeners for contested action events need to check
  whether their character is the challenger or the target, and
  respond accordingly.

  The usual language of "subject" and "target" is still used,
  but there is an additional field that indicates whether the
  subject is the "challenger" in the contest.
  '''
  def __init__(self, subject, target, challenger, skill, \
      contested_skill, initiative_action, context, ring=None, vp=0):
    super().__init__(subject, target, skill, initiative_action, context, ring=ring, vp=vp)
    if challenger != subject and challenger != target:
      raise ValueError('ContestedAction challenger must be the subject or target')
    self._challenger = challenger
    if not isinstance(contested_skill, str):
      raise ValueError('challenger_skill must be str')
    if challenger is subject:
      self._defender = target
      self._challenger_skill = skill
      self._defender_skill = contested_skill
    else:
      self._defender = subject
      self._challenger_skill = contested_skill
      self._defender_skill = skill
    self._contested_skill = contested_skill
    self._opponent_roll = None

  def challenger(self):
    return self._challenger

  def challenger_skill(self):
    return self._challenger_skill

  def contested_skill(self):
    return self._contested_skill

  def defender(self):
    return self._defender

  def defender_skill(self):
    return self._defender_skill

  def opponent_skill_roll(self):
    return self._opponent_roll

  def set_opponent_skill_roll(self, roll):
    self._opponent_roll = roll

