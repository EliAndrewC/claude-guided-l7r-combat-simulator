#!/usr/bin/env python3

#
# roll_params.py
#
# Class to calculate a character's roll parameters in L7R.
# "Roll parameters" is the tuple of (rolled, kept, modifier)
# for a roll.
#

from abc import ABC, abstractmethod


def normalize_roll_params(rolled, kept, bonus=0):
  '''
  normalize_roll_params(rolled, kept, bonus=0) -> tuple of ints
    rolled (int): number of rolled dice
    kept (int): number of kept dice
    bonus (int): flat bonus to roll

  Returns normalized roll parameters, which is the tuple of
  (rolled, kept, bonus) for a roll.
  The algorithm is that excess rolled dice above ten become
  extra kept dice, excess kept dice above ten become a bonus,
  and the bonus is added to the roll.
  '''
  # convert excess rolled dice to extra kept dice
  if rolled > 10:
    excess_rolled = rolled - 10
    rolled = 10
    kept += excess_rolled
  # convert extra kept dice to bonus
  if kept > 10:
    excess_kept = kept - 10
    kept = 10
    bonus += (2 * excess_kept)
  # check if there are fewer dice rolled than kept
  if rolled < kept:
    kept = rolled
  # rolled and kept may not be lower than zero
  rolled = max(rolled, 0)
  kept = max(kept, 0)
  return (rolled, kept, bonus)


class RollParameterProvider(ABC):
  @abstractmethod
  def get_damage_roll_params(self, character, target, skill, \
      attack_extra_rolled, vp=0):
    '''
    get_damage_roll_params(character, target, skill, \
        attack_extra_rolled, vp=0) -> tuple of three ints
      character (Character): character who is rolling damage
      target (Character): character who will be damaged
      skill (str): skill name being used
      attack_extra_rolled (int): number of extra rolled damage dice from the attack roll
      vp (int): number of Void Points spent on the attack roll

    Returns the parameters for the character's damage roll using
    the specified skill against the given target.
    '''
    pass

  @abstractmethod
  def get_initiative_roll_params(self, character):
    '''
    get_initiative_roll_params(character) -> tuple of ints
      character (Character): character who is rolling initiative

    Returns the roll parameters (rolled, kept, modifier) for the
    character's initiative roll.

    Modifiers do not apply to initiative rolls, so the modifier is
    always 0.
    '''
    pass

  @abstractmethod
  def get_skill_roll_params(self, character, target, skill, \
      contested_skill=None, ring=None, vp=0):
    '''
    get_skill_roll_params(character, target, skill, \
        contested_skill=None, ring=None, vp=0) -> tuple of ints
      character (Character): character who is rolling
      target (Character): target of the skill
      skill (str): skill name being used
      contested_skill (str): if given, this is a contested roll,
        and names the skill the other character is using to contest.
      ring (str): ring to use for the skill roll. Defaults to None,
        which means the character's default ring for that skill is
        used.
      vp (int): number of Void Points to spend on this roll

    Returns the parameters for the character's skill roll using the
    specified and skill as a tuple of three ints
    (rolled, kept, modifier).
    '''
    pass
 
  def get_wound_check_roll_params(self, character, vp=0):
    '''
    get_wound_check_roll_params(character, vp=0) -> tuple of ints
      character (Character): character who will be rolling for a Wound Check
      vp (int): number of Void Points to spend on this roll

    Returns the parameters for the character's wound check roll
    as a tuple of three ints (rolled, kept, modifier).
    '''
    pass


class DefaultRollParameterProvider(RollParameterProvider):
  def get_damage_roll_params(self, character, target, skill, \
      attack_extra_rolled, vp=0):
    # calculate extra rolled dice
    ring = character.ring(character.get_skill_ring('damage'))
    my_extra_rolled = character.extra_rolled('damage')
    rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled()
    # calculate extra kept dice
    my_extra_kept = character.extra_kept('damage')
    kept = character.weapon().kept() + character.extra_kept('damage')
    # calculate modifier
    mod = character.modifier(None, 'damage')
    return normalize_roll_params(rolled, kept, mod)

  def get_initiative_roll_params(self, character):
    ring = character.ring(character.get_skill_ring('initiative'))
    rolled = ring + 1 + character.extra_rolled('initiative')
    kept = ring + character.extra_kept('initiative')
    return (rolled, kept, 0)

  def get_skill_roll_params(self, character, target, skill, \
      contested_skill=None, ring=None, vp=0):
    if ring is None:
      ring = character.ring(character.get_skill_ring(skill))
    rolled = ring + character.skill(skill) + character.extra_rolled(skill) + vp
    kept = ring + character.extra_kept(skill) + vp
    modifier = character.modifier(target, skill)
    if contested_skill is not None:
      my_skill = character.skill(skill)
      your_skill = target.skill(contested_skill)
      if my_skill > your_skill:
        modifier += 5 * (my_skill - your_skill) 
    return normalize_roll_params(rolled, kept, modifier)

  def get_wound_check_roll_params(self, character, vp=0):
    ring = character.ring(character.get_skill_ring('wound check'))
    rolled = ring + 1 + character.extra_rolled('wound check') + vp
    kept = ring + character.extra_kept('wound check') + vp
    modifier = character.modifier(None, 'wound check')
    return normalize_roll_params(rolled, kept, modifier)


DEFAULT_ROLL_PARAMETER_PROVIDER = DefaultRollParameterProvider()

