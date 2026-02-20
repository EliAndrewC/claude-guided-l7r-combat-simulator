#!/usr/bin/env python3

#
# attack_optimizers.py
#
# Classes to optimize resources spent on attack actions.
#

from simulation.knowledge import TheoreticalCharacter


class ExpectedAttackRoll(object):
  '''
  Container class to hold an expected attack roll given
  resource expenditure parameters and a lot of other
  context.
  '''
  def __init__(self, roll, vp, ap, p):
    self.roll = roll
    self.ap = ap
    self.vp = vp
    self.p = p

  def value(self, unoptimized_roll):
    return self.roll - unoptimized_roll


class AttackOptimizer(object):
  '''
  Class that helps optimize spending resources on an attack roll
  by calculating the probability of success when spending different
  amounts of VP and other available resources.

  This class should be used to optimize attack rolls when the goal
  is to hit a TN, and there isn't benefit from exceeding the TN.

  Feint is the typical example of an attack where there is no
  benefit for exceeding the TN.
  '''
  def __init__(self, subject, target, skill, initiative_action, \
      context, max_vp=None, max_ap=None):
    self.subject = subject
    self.target = target
    self.theoretical_target = TheoreticalCharacter(subject.knowledge(), target)
    self.skill = skill
    self.initiative_action = initiative_action
    self.context = context
    self.explode = not self.subject.crippled()
    # set this information later
    self.original_max_ap = max_ap
    self.original_max_vp = max_vp
    self.action = None
    self.tn = 0
    self.expected_rolls = []
    self.initialize()

  def get_action(self, vp):
    return self.subject.action_factory() \
      .get_attack_action(self.subject, self.target, self.skill, \
        self.initiative_action, self.context, vp=vp)

  def initialize(self):
    # determine possible expenditures of ap and vp
    self.max_ap = self.original_max_ap
    self.max_vp = self.original_max_vp
    available_vp = self.subject.void_point_manager().vp(self.skill)
    if self.max_ap is None:
      self.max_ap = min(self.subject.max_ap_per_roll(), self.subject.ap())
    if self.max_vp is None:
      self.max_vp = min(self.subject.max_vp_per_roll(), available_vp)
    self.max_ap = min(self.max_ap, self.subject.ap())
    self.max_vp = min(self.max_vp, available_vp)
    # determine expected tn
    self.action = self.subject.action_factory() \
      .get_attack_action(self.subject, self.theoretical_target, \
        self.skill, self.initiative_action, self.context)
    self.tn = self.action.tn()
    # consider using available floating bonuses, if any
    bonus = sum([b.bonus() for b in self.subject.floating_bonuses(self.skill)])
    # determine expected value of possible vp spends
    for vp in range(self.max_vp + 1):
      self.action.set_vp(vp)
      (rolled, kept, mod) = self.action.skill_roll_params()
      roll = self.context.mean_roll(rolled, kept) + mod + bonus
      for ap in range(self.max_ap +  1):
        adjusted_roll = roll + (5 * ap)
        adjusted_tn = self.tn - (5 * ap) - bonus
        p = self.context.p(adjusted_tn, rolled, kept, explode=self.explode)
        self.expected_rolls.append(ExpectedAttackRoll(adjusted_roll, vp, ap, p))
    # sort expected rolls in ascending order
    self.expected_rolls.sort(key=lambda x: x.roll)

  def optimize(self, threshold=0):
    '''
    optimize(threshold=0) -> AttackAction or None
      threshold (float): threshold for probability of hitting desired
    
    Returns an AttackAction that will use enough VP to succeed with the
    provided threshold, or None if the threshold can't be achieved.
    '''
    recommendation = None
    for r in self.expected_rolls:
      if r.p >= threshold:
        recommendation = (r.vp, r.ap)
        break
    if recommendation is not None:
      return self.get_action(recommendation[0])
    else:
      return None


class DamageOptimizer(AttackOptimizer):
  '''
  Utility class to optimize an attack to get extra kept damage dice
  after reaching the desired threshold for probability of success.

  This class should be used to decide when to spend resources to get
  a better damage roll.
  '''
  def initialize(self):
    super().initialize()
    self.expected_kept_damage = {}
    for r in self.expected_rolls:
      extra_rolled = self.action \
        .calculate_extra_damage_dice(r.roll, self.tn)
      (rolled, kept, bonus) = self.subject.get_damage_roll_params(self.target, \
        self.skill, extra_rolled)
      self.expected_kept_damage[(r.vp, r.ap)] = kept

  def optimize(self, threshold=0):
    '''
    optimize(threshold=0) -> AttackAction or None
      threshold (float): threshold for probability of hitting desired
    
    Returns the tuple of (vp, ap) that will get the most kept damage
    dice, that will also succeed at the attack with the provided
    threshold, or None if the threshold can't be achieved.

    Returns an AttackAction that will use enough VP to keep the most
    damage dice and also succeed at the attack with the provided threshold,
    or None if the threshold can't be achieved.
    '''
    recommendation = None
    recommendation_expected_roll = None
    # check expected kept damage dice at each expenditure
    # until an extra kept die is achieved
    prev_kept = 0
    for r in self.expected_rolls:
      if r.p < threshold:
        # ignore rolls that don't reach the desired threshold 
        continue
      (vp, ap) = (r.vp, r.ap)
      kept = self.expected_kept_damage[(vp, ap)]
      if kept > prev_kept:
        # after reaching the threshold, only spend extra resources
        # to get extra kept damage dice
        recommendation = (vp, ap)
        recommendation_expected_roll = r
        prev_kept = kept
      if kept >= 6:
        # don't spend resources after six kept dice
        # the marginal benefit drops off after six
        break
    # reject recommendation if probability of success is under threshold
    if recommendation is not None:
      p = recommendation_expected_roll.p
      if p < threshold:
        recommendation = None
    # return recommendation or None
    if recommendation is not None:
      return self.get_action(recommendation[0])
    else:
      return None

