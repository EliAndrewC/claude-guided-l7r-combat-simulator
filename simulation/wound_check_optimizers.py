#!/usr/bin/env python3

#
# wound_check_optimizers.py
#
# Classes to optimize resources spent on wound checks.
#

from abc import ABC, abstractmethod

from simulation.events import LightWoundsDamageEvent, WoundCheckDeclaredEvent, WoundCheckRolledEvent
from simulation.knowledge import TheoreticalCharacter
from simulation.log import logger


class ProbabilityForResources(object):
  '''
  Container class to hold the probability of meeting the target number
  given an expenditure of vp and ap.
  '''
  def __init__(self, p, vp, ap):
    self.p = p
    self.vp = vp
    self.ap = ap

  def sort_key_by_cost(self):
    '''
    sort_by_cost() -> int

    Returns a number that values VP more than AP, but spends an extra VP before spending 4 or 5 AP.
    '''
    vp_value = 4 * self.vp if self.ap < 4 else (6 * (self.vp + 1)) - 2
    ap_value = self.ap if self.ap <= 3 else self.ap + 4
    return vp_value + ap_value


class WoundCheckOptimizer(ABC):
  '''
  Class that helps optimize spending resources on a wound check roll
  by calculating the probability of success when spending different
  amounts of VP and other available resources.
  '''
  @abstractmethod
  def declare(self, max_sw, threshold):
    ''''
    declare(max_sw, threshold) -> DeclareWoundCheckEvent
      max_sw (int): maximum SW the subject can tolerate
      threshold (float): probability of success desired

    Returns a WoundCheckDeclaredEvent that will spend the number
    of VP required to take the tolerable number of SW at the
    desired threshold for probability of success.
    '''
    pass


class DefaultWoundCheckOptimizer(object):
  '''
  Class that helps optimize spending resources on a wound check roll
  by calculating the probability of success when spending different
  amounts of VP and other available resources.
  '''
  def __init__(self, subject, event, context, max_vp=None, max_ap=None):
    '''
    __init__(subject, max_vp=None)
      subject (Character): character who is making the wound check
      event (Event): LightWoundsDamageEvent that led to this wound check
      context (EngineContext): context
      max_vp (int): maximum VP the character will spend. If None,
        will spend the maximum possible to improve the wound check.
      max_ap (int): maximum AP the character will spend. If None,
        will spend the maximum possible to improve the wound check.
    '''
    self.subject = subject
    self.event = event
    self.context = context
    self.max_vp = max_vp
    self.max_ap = max_ap
    self.original_max_vp = max_vp
    self.original_max_ap = max_ap
    self.sw_to_roll = {}
    self.p_for_resources = []
    self.initialize()
  
  def initialize(self):
    # reset state
    self.sw_to_roll.clear()
    self.p_for_resources.clear()
    # determine max vp that may be spent on this roll
    self.max_vp = self.original_max_vp
    if self.max_vp is None:
      # if no limit set: maximum is character's maximum allowed VP expenditure
      available_vp = self.subject.void_point_manager().vp('wound check')
      self.max_vp = min(self.subject.max_vp_per_roll(), available_vp)
    # determine max ap that may be spent on this roll
    self.max_ap = self.original_max_ap
    if self.max_ap is None:
      self.max_ap = min(self.subject.max_ap_per_roll(), self.subject.ap())
    # find the break points where the character takes fewer SW
    sw = 100
    prev_sw = sw
    roll = 0
    while sw > 0:
      sw = self.subject.wound_check(roll)
      if sw < prev_sw:
        self.sw_to_roll[sw] = roll
        prev_sw = sw
      if sw == 0:
        break
      roll += 1

  def declare(self, max_sw, threshold):
    '''
    declare(character, event, max_sw, theshold, context) -> WoundCheckDeclaredEvent
      character (Character): character who is making the wound check

    Returns a WoundCheckDeclaredEvent to spend VP for an acceptable
    level of risk on a wound check.
    '''
    # plan to use any available floating bonuses
    bonus = sum([b.bonus() for b in self.subject.floating_bonuses('wound check')])
    # get tn for desired SW
    if max_sw not in self.sw_to_roll.keys():
      # if the sw_to_roll mapping doesn't contain max_sw,
      # then there is no risk of taking max_sw and no resources should be used
      return WoundCheckDeclaredEvent(self.subject, self.event.subject, self.event.damage, 0, tn=self.event.wound_check_tn)
    tn = self.sw_to_roll[max_sw] - bonus
    # calculate probability of reaching this tn for various resource expenditures
    for vp in range(self.max_vp + 1):
      (rolled, kept, mod) = self.subject.get_wound_check_roll_params(vp)
      for ap in range(self.max_ap + 1):
        adjusted_tn = tn - (5 * ap) - mod
        p_tn = self.context.p(adjusted_tn, rolled, kept)
        self.p_for_resources.append(ProbabilityForResources(p_tn, vp, ap))
      if kept == 10:
        # do not spend additional vp after keeping 10 dice
        break
    # sort results by cost
    self.p_for_resources.sort(key=lambda x: x.sort_key_by_cost())
    # iterate through results until the first one is found that satisfies the threshold
    (vp, ap) = (0, 0)
    for result in self.p_for_resources:
      if result.p >= threshold:
        (vp, ap) = (result.vp, result.ap)
        logger.debug('{} declaring wound check with {} vp (planning to spend {} ap) to take {} SW with probability {}' \
          .format(self.subject.name(), vp, ap, max_sw, result.p))
        break
    return WoundCheckDeclaredEvent(self.subject, self.event.subject, self.event.damage, vp=vp, tn=self.event.wound_check_tn)


class KeepLightWoundsOptimizer(ABC):
  '''
  Class that helps make decisions about keeping Light Wounds after
  a successful Wound Check.
  '''
  @abstractmethod
  def should_keep(self, max_sw, threshold, max_vp=None):
    '''
    keep(max_sw, threshold) -> tuple
      max_sw (int): maximum number of Serious Wounds this character
        is willing to risk
      threshold (float): minimum probability desired of taking no
        more than the specified max_sw.
      max_vp (int): maximum number of Void Points the character
        would be willing to spend on a future Wound Check. If None,
        the character will consider spending the maximum possible
        number of VP. Default is None.

    Returns a tuple of (bool, int). The bool recommends whether this
    character should keep their current LW or take a Serious Wound
    instead, and the int recommends the number of Void Points that
    should be reserved with the character's Void Point Manager if
    the decision is to keep.
    '''
    pass


class DefaultKeepLightWoundsOptimizer(KeepLightWoundsOptimizer):
  '''
  KeepLightWoundsOptimizer implementation that will work for most
  characters.

  This implementation intentionally does not consider Adventure
  Points. Instead, characters who can spend AP on wound checks
  should optimize with a riskier threshold and use their AP if they
  fail the roll by too much. This decision may be revisited in the
  future.
  '''
  def __init__(self, subject, context):
    self.subject = subject
    self.context = context

  def should_keep(self, max_sw, threshold, max_vp=None):
    # how much damage do we expect to take in the future?
    # TODO: revisit whether this is a good prediction of
    # future damage
    expected_damage = 0
    if len(self.subject.lw_history()) == 0:
      expected_damage = self.context.mean_roll(7, 2)
    else:
      expected_damage = int(sum(self.subject.lw_history()) / len(self.subject.lw_history()))
    future_damage = self.subject.lw() + expected_damage
    # what TN is needed to take no more than max_sw?
    sw = 100
    prev_sw = sw
    roll = 0
    sw_to_roll = {}
    while sw > 0:
      sw = self.subject.wound_check(roll, lw=future_damage)
      if sw < prev_sw:
        sw_to_roll[sw] = roll
        prev_sw = sw
      if sw == 0:
        break
      roll += 1
    if max_sw not in sw_to_roll.keys():
      # if max_sw isn't in the sw_to_roll dictionary,
      # then we should be safe to keep
      return (True, 0)
    tn = sw_to_roll[max_sw]
    # plan to use any available floating bonuses
    bonus = sum([b.bonus() for b in self.subject.floating_bonuses('wound check')])
    tn -= bonus
    # determine how many VP are available
    vp_available = self.subject.void_point_manager().vp('wound check')
    vp_available = min(max_vp, self.subject.max_vp_per_roll())
    # find probability of making the TN with different VP spends 
    p_tn_d = {}
    for vp in range(vp_available + 1):
      (rolled, kept, modifier) = self.subject.get_wound_check_roll_params(vp=vp)
      p_tn = self.context.p(tn - modifier, rolled, kept)
      p_tn_d[vp] = p_tn
      if p_tn >= threshold:
        break
    # find the cheapest roll that meets the threshold
    for vp in range(max_vp + 1):
      if p_tn_d[vp] >= threshold:
        return (True, vp)
    # fell through: cannot make TN, should not keep
    return (False, 0)

class RiskyKeepLightWoundsOptimizer(KeepLightWoundsOptimizer):
  '''
  A KeepLightWoundsOptimizer designed to optimize based on a
  maximum risk instead of a minimum risk.

  The DefaultKeepLightWoundsOptimizer asks "given a maximum number
  of SW I am willing to take, what is my chance of making the Wound
  Check to take that many SW or fewer?"

  This class asks instead, "given a number of SW that I'm not
  willing to take, what is my chance of missing my TN and taking
  that many SW or worse?"
  '''
  def __init__(self, subject, context):
    self.subject = subject
    self.context = context

  def should_keep(self, max_sw, threshold, max_vp=None):
    expected_damage = 0
    if len(self.subject.lw_history()) == 0:
      expected_damage = self.context.mean_roll(7, 2)
    else:
      expected_damage = int(sum(self.subject.lw_history()) / len(self.subject.lw_history()))
    future_damage = self.subject.lw() + expected_damage
    # what are the TN break points where we take different numbers of SW?
    sw = 100
    prev_sw = sw
    roll = 0
    sw_to_roll = {}
    while sw > 0:
      sw = self.subject.wound_check(roll, lw=future_damage)
      if sw < prev_sw:
        sw_to_roll[sw] = roll
        prev_sw = sw
      if sw == 0:
        break
      roll += 1
    if max_sw not in sw_to_roll.keys():
      # if max_sw isn't in the sw_to_roll dictionary,
      # then we should be safe to keep
      return (True, 0)
    # determine the "break point" where we take unacceptable SW
    break_point = sw_to_roll[max_sw]
    # plan to use any available floating bonuses
    bonus = sum([b.bonus() for b in self.subject.floating_bonuses('wound check')])
    break_point -= bonus
    # determine how many VP are available
    vp_available = self.subject.void_point_manager().vp('wound check')
    vp_available = min(max_vp, self.subject.max_vp_per_roll())
    # find probability of rolling the break point or less, with different VP spends
    p_fail_d = {}
    for vp in range(vp_available + 1):
      (rolled, kept, modifier) = self.subject.get_wound_check_roll_params(vp=vp)
      p_fail = 1 - self.context.p(break_point - modifier, rolled, kept)
      if p_fail < threshold:
        return (True, vp)
    # fell through: fail
    return (False, 0)

