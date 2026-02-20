#!/usr/bin/env python3

#
# strategies.py
#
# Classes that make decisions about how to respond to events.
#

from abc import ABC, abstractmethod
import itertools
import math

from simulation import actions, events
from simulation.exceptions import NotEnoughActions
from simulation.initiative_actions import InitiativeAction
from simulation.knowledge import TheoreticalCharacter
from simulation.log import logger
from simulation.roll import normalize_roll_params
from simulation.wound_check_optimizers import DefaultKeepLightWoundsOptimizer

class Strategy(ABC):
  '''
  Class that can choose between possible decisions to respond to an Event.

  The Strategy and Listener classes both respond to an Event by
  optionally returning another Event, which begs the question, why
  not just put strategy logic into Listeners?

  The idea behind separating Listener and Strategy is to keep the two classes simple.
  Listener is responsible for knowing when to mutate the Character's state
  (taking damage, spending resources, etc). The Strategy implements
  complex logic to choose between possible courses of action.

  Mixing the two classes would result in big Listener classes that
  would contain too much complexity. It would be difficult to write
  such a big class, or to test it effectively.

  Isolating decision making logic in the Strategy class also helps
  deal with the fact that different kinds of characters will have
  different strategies around certain aspects of their behavior, and
  it will be easier to write a lot of different little Strategy classes
  than it would be to write several big Listener classes.
  '''
  @abstractmethod
  def recommend(self, character, event, context):
    '''
    recommend(character, event, context) -> Event or None
      character (Character): Character deciding how to respond to the Event
      event (Event): an Event requiring a decision about how to act
      context (EngineContext): context about other Characters, groups, timing, etc

    Makes a decision about whether and how to respond to an Event.
    This should be used to deal with decisions like whether to spend
    Void Points or school abilities, or whether to parry an attack,
    or whether to hold actions or spend them immediately, etc.
    '''
    pass


class AlwaysAttackActionStrategy(Strategy):
  def recommend(self, character, event, context):
    if isinstance(event, events.YourMoveEvent):
      # try to attack if action available
      # TODO: evaluate whether to interrupt
      if character.has_action(context):
        yield from character.attack_strategy() \
          .recommend(character, event, context)
      else:
        yield events.NoActionEvent(character)


class HoldOneActionStrategy(Strategy):
  def recommend(self, character, event, context):
    if isinstance(event, events.YourMoveEvent):
      # try to hold an action in reserve until Phase 10
      if character.has_action(context):
        available_actions = [action for action in character.actions() if action <= context.phase()]
        if len(available_actions) > 1 or context.phase() == 10:
          yield from character.attack_strategy() \
            .recommend(character, event, context)
        else:
          logger.debug('{} is holding an action'.format(character.name()))
          yield events.HoldActionEvent(character)
      else:
        yield events.NoActionEvent(character)


class BaseAttackStrategy(Strategy):
  def choose_action(self, character, skill, context):
    if character.has_action(context):
      # choose earliest available action die
      # older action dice are usually more valuable
      action_die = min([die for die in character.actions() if die <= context.phase()])
      return InitiativeAction([action_die], action_die)
    elif character.has_interrupt_action(skill, context):
      cost = character.interrupt_cost(skill, context)
      action_dice = []
      unspent_action_dice = []
      unspent_action_dice.extend(character.actions())
      while len(action_dice) < cost:
        die = max(unspent_action_dice)
        unspent_action_dice.pop(die)
        action_dice.append(die)
      return InitaitiveAction(action_dice, context.phase(), is_interrupt=True) 
    else:
      raise NotEnoughActions()

  def spend_action(self, character, skill, initiative_action):
    '''
    spend_action(character, skill, initiative_action) -> SpendActionEvent

    Spend an action dice to take an attack.
    '''
    yield events.SpendActionEvent(character, skill, initiative_action)
 
  def try_skill(self, character, skill, initiative_action, threshold, context):
    '''
    try_skill(character, skill, initiative_action, threshold, context) -> TakeAttackActionEvent or None

    Returns a TakeAttackActionEvent if the strategy can successfully
    find a target and optimize an attack using the given skill.
    '''
    if character.skill(skill) > 0:
      target = character.target_finder().find_target(character, skill, initiative_action, context)
      if target is not None:
        attack = character.attack_optimizer_factory() \
          .get_optimizer(character, target, skill, \
            initiative_action, context) \
          .optimize(threshold)
        if attack is not None:
          logger.info('{} is attacking {} with {} and spending {} VP' \
            .format(character.name(), target.name(), skill, attack.vp()))
          return character.take_action_event_factory() \
            .get_take_attack_action_event(attack)

  def recommend(self, character, event, context):
    raise NotImplementedError()


class PlainAttackStrategy(BaseAttackStrategy):
  def recommend(self, character, event, context):
    if isinstance(event, events.YourMoveEvent):
      if character.has_action(context):
        initiative_action = self.choose_action(character, 'attack', context)
        # attempt to optimize for a good attack
        action_event = self.try_skill(character, 'attack', initiative_action, 0.7, context)
        if action_event is not None:
          yield from self.spend_action(character, 'attack',  initiative_action)
          yield action_event
          return
        # fell through: chance of success is low
        # try an attack anyway even if it's desperate
        action_event = self.try_skill(character, 'attack', initiative_action, 0.01, context)
        if action_event is not None:
          yield from self.spend_action(character, 'attack', initiative_action)
          yield action_event
        else:
          yield events.HoldActionEvent(character)
      else:
        yield events.NoActionEvent(character)


class StingyPlainAttackStrategy(BaseAttackStrategy):
  '''
  Always attack with available actions, never spend resources to optimize.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.YourMoveEvent):
      # TODO: implement intelligence around interrupts
      if character.has_action(context):
        initiative_action = self.choose_action(character, 'attack', context)
        target = character.target_finder() \
          .find_target(character, 'attack', context)
        if target is not None:
          action = subject.action_factory() \
            .get_attack_action(subject, target, skill, \
              initiative_action, context)
          logger.info('{} is attacking {}'.format(character.name(), target.name()))
          yield from self.spend_action(character, 'attack', initiative_action)
          yield character.take_action_event_factory() \
            .get_take_attack_action_event(attack)
        else:
          yield events.HoldActionEvent(character)
      else:
        yield events.NoActionEvent(character)


class UniversalAttackStrategy(BaseAttackStrategy):
  def recommend(self, character, event, context):
    if isinstance(event, events.YourMoveEvent):
      # TODO: implement intelligence around interrupts
      if character.has_action(context):
        # try to double attack first
        initiative_action = self.choose_action(character, 'double attack', context)
        double_attack_event = self.try_skill(character, 'double attack', initiative_action, 0.6, context)
        if double_attack_event is not None:
          yield from self.spend_action(character, 'double attack', initiative_action)
          yield double_attack_event
          return
        # TODO: consider a lunge (probably need a LungeStrategy)
        if character.vp() == 0 and len(character.actions()) > 1:
          # if this character is out of VP and has more than one action in this round, a feint might be worth it
          initiative_action = self.choose_action(character, 'feint', context)
          feint_event = self.try_skill(character, 'feint', initiative_action, 0.7, context)
          if feint_event is not None:
            yield from self.spend_action(character, 'feint', initiative_action)
            yield feint_event
            return
        # try a plain attack
        initiative_action = self.choose_action(character, 'attack', context)
        attack_event = self.try_skill(character, 'attack', initiative_action, 0.7, context)
        if attack_event is not None:
          yield from self.spend_action(character, 'attack', initiative_action)
          yield attack_event
          return
        # try a plain attack even if it's desperate
        initiative_action = self.choose_action(character, 'attack', context)
        attack_event = self.try_skill(character, 'attack', initiative_action, 0.01, context)
        if attack_event is not None:
          yield from self.spend_action(character, 'attack', initiative_action)
          yield attack_event
          return
        # fell through: do nothing
        yield events.HoldActionEvent(character)
      else:
        yield events.NoActionEvent(character)


class BaseParryStrategy(Strategy):
  def recommend(self, character, event, context):
    if isinstance(event, events.AttackRolledEvent):
      # bail if no action
      if not (character.has_action(context) or character.has_interrupt_action('parry', context)):
        logger.debug('{} will not parry because no action'.format(character.name()))
        return
      # don't try to parry for enemies
      if event.action.target() not in character.group():
        logger.debug('{} will not parry for an enemy'.format(character.name()))
        return
      # don't try to parry a miss or an attack that is already parried
      if not event.action.is_hit():
        logger.debug('{} will not parry an attack that missed'.format(character.name()))
        return
      # don't try to parry an attack that is already parried
      if event.action.parried():
        logger.debug('{} will not parry an attack was already parried'.format(character.name()))
        return
      # delegate to specific parry strategy recommendation
      try:
        yield from self._recommend(character, event, context)
      except NotEnoughActions:
        raise RuntimeError('Not enough actions to parry')
        return

  def _can_shirk(self, character, event, context):
    '''
    Returns whether this character can shirk and let somebody else parry.
    '''
    # do my other friends have actions?
    others = character.group().friends_with_actions(context)
    for other_character in others:
      # can't pass the buck to myself
      if character != other_character:
        # did they already decline the parry?
        if other_character not in event.action.parries_declined():
          # are they willing to parry?
          if not isinstance(other_character.parry_strategy(), NeverParryStrategy):
            # shirk the parry
            return True
    return False

  def _choose_action(self, character, skill, context):
    '''
    _choose_action(character, skill, context) -> InitiativeAction

    Choose action dice to spend to parry.
    '''
    if character.has_action(context):
      # spend the newest available action
      # older actions are usually more valuable
      die = max([die for die in character.actions() if die <= context.phase()])
      return InitiativeAction([die], die)
    elif character.has_interrupt_action(skill, context):
      # interrupt
      cost = character.interrupt_cost(skill, context)
      action_dice = []
      unspent_action_dice = []
      unspent_action_dice.extend(character.actions())
      while len(action_dice) < cost:
        die = max(unspent_action_dice)
        unspent_action_dice.remove(die)
        action_dice.append(die)
      return InitiativeAction(action_dice, context.phase(), is_interrupt=True)
    else:
      # somehow character is unable to parry
      raise NotEnoughActions()

  def _estimate_damage(self, character, event, context):
    '''
    _estimate_damage(character, event, context) -> int

    Returns an estimate of how many SW this attack will inflict.
    '''
    # how much damage do we expect?
    expected_fire = TheoreticalCharacter(character.knowledge(), event.action.subject().name()).ring('fire')
    extra_dice = event.action.calculate_extra_damage_dice()
    weapon_rolled = event.action.subject().weapon().rolled()
    weapon_kept = event.action.subject().weapon().kept()
    expected_damage = context.mean_roll(expected_fire + weapon_rolled + extra_dice, weapon_kept)
    # how many wounds do we expect the target to take from this?
    target = event.action.target()
    (wc_rolled, wc_kept, wc_bonus) = target.get_wound_check_roll_params()
    expected_roll = context.mean_roll(wc_rolled, wc_kept) + wc_bonus
    expected_sw = target.wound_check(expected_roll, target.lw() + expected_damage)
    return expected_sw

  def _recommend(self, character, event, context):
    raise NotImplementedError()

  def _spend_action(self, character, skill, initiative_action):
    '''
    _spend_action(character, skill, initiative_action) -> SpendActionEvent

    Spend action dice to parry.
    '''
    yield events.SpendActionEvent(character, skill, initiative_action)
 

class AlwaysParryStrategy(BaseParryStrategy):
  '''
  Always parry for friends.
  '''
  def _recommend(self, character, event, context):
    logger.debug('{} always parries'.format(character.name()))
    initiative_action = self._choose_action(character, 'parry', context)
    parry = character.action_factory() \
      .get_parry_action(character, event.action.subject(), \
        event.action, 'parry', initiative_action, context)
    yield from self._spend_action(character, 'parry', initiative_action)
    yield character.take_action_event_factory().get_take_parry_action_event(parry)


class NeverParryStrategy(Strategy):
  '''
  Never parry.
  '''
  def recommend(self, character, event, context):
    logger.debug('{} never parries'.format(character.name()))
    yield from ()


class ReluctantParryStrategy(BaseParryStrategy):
  '''
  Parry if the hit is going to be bad and nobody else can parry.
  '''
  def _recommend(self, character, event, context):
    # let somebody else parry if possible
    # TODO: implement some kind of team parry strategy
    if self._can_shirk(character, event, context):
      logger.debug('{} is reluctant and shirks the parry'.format(character.name()))
      return
    # if parry was already attempted, no need to try again
    elif event.action.parry_attempted():
      logger.debug('{} is reluctant and will not parry when it was already attempted'.format(character.name()))
      return
    else:
      # how many wounds do we expect?
      expected_sw = self._estimate_damage(character, event, context)
      if event.action.skill() == 'double attack':
        expected_sw += 1
      # parry if it looks bad
      target = event.action.target()
      probably_fatal = target.sw_remaining() <= expected_sw
      probably_critical = expected_sw >= 2
      if probably_fatal or probably_critical:
        if probably_fatal:
          logger.debug('{} reluctantly parries because the attack would probably be fatal'.format(character.name()))
        elif probably_critical:
          logger.debug('{} reluctantly parries because the attack looks dangerous'.format(character.name()))
        initiative_action = self._choose_action(character, 'parry', context)
        parry = character.action_factory() \
          .get_parry_action(character, event.action.subject(), \
            event.action, 'parry', initiative_action, context)
        yield from self._spend_action(character, 'parry', initiative_action)
        yield character.take_action_event_factory().get_take_parry_action_event(parry)
      else:
        logger.debug('{} will not parry a small attack'.format(character.name()))


class SkillRolledStrategy(Strategy):
  '''
  Strategy to decide how to spend resources after a roll.
  '''
  def __init__(self):
    self._chosen_ap = 0
    self._chosen_bonuses = []

  def event_matches(self, character, event):
    '''
    Return whether this event is relevant for the strategy and character.
    '''
    raise NotImplementedError()

  def get_skill(self, event):
    '''
    Returns the skill that can be used for floating bonuses for this skill roll.
    '''
    raise NotImplementedError()

  def get_tn(self, event):
    '''
    Return the desired TN.
    '''
    raise NotImplementedError()

  def recommend(self, character, event, context):
    if self.event_matches(character, event):
      self.reset()
      tn = self.get_tn(event)
      margin = tn - event.action.skill_roll()
      if margin <= 0:
        # if the roll was successful, do nothing
        yield event
        return
      # use floating bonuses to try to make the TN
      self.use_floating_bonuses(character, self.get_skill(event), margin)
      margin = tn - event.action.skill_roll() - sum([b.bonus() for b in self._chosen_bonuses])
      if margin > 0:
        # use adventure points to try to make the TN
        self.use_ap(character, event.action.skill(), margin)
        margin -= (5 * self._chosen_ap)
      if margin <= 0:
        # if we reached the TN, spend resources and update the event
        for bonus in self._chosen_bonuses:
          yield events.SpendFloatingBonusEvent(character, bonus)
        if self._chosen_ap > 0:
          yield events.SpendAdventurePointsEvent(character, skill, self._chosen_ap)
        new_roll = event.action.skill_roll() - sum([b.bonus() for b in self._chosen_bonuses]) - (5 * self._chosen_ap)
        event.action.set_skill_roll(new_roll)
        event.roll = new_roll
      yield event
    
  def reset(self):
    '''
    Reset this strategy. Should be called before each use.
    '''
    self._chosen_ap = 0
    self._chosen_bonuses.clear()

  def use_ap(self, character, skill, margin):
    if character.ap() > 0:
      if skill in character.ap_skills():
        ap_needed = math.ceil(margin / 5)
        max_spend = min(character.ap(), character.max_ap_per_roll())
        self._chosen_ap = min(max_spend, ap_needed)
       
  def use_floating_bonuses(self, character, skill, margin):
    available_bonuses = list(character.floating_bonuses(skill))
    available_bonuses.sort()
    while margin > 0 and len(available_bonuses) > 0:
      bonus = available_bonuses.pop(0)
      self._chosen_bonuses.append(bonus)
      margin -= bonus.bonus()


class AttackRolledStrategy(SkillRolledStrategy):
  def event_matches(self, character, event):
    return isinstance(event, events.AttackRolledEvent) and character == event.action.subject()

  def get_skill(self, event):
    return event.action.skill()

  def get_tn(self, event):
    return event.action.tn()


class ParryRolledStrategy(SkillRolledStrategy):
  def event_matches(self, character, event):
    return isinstance(event, events.ParryRolledEvent) and character == event.action.subject()

  def get_skill(self, event):
    return event.action.skill()

  def get_tn(self, event):
    return event.action.tn()


class WoundCheckRolledStrategy(SkillRolledStrategy):
  '''
  Strategy to decide how to spend resources to improve
  a wound check roll.

  This strategy is written to only spend resources to avoid
  defeat or taking more than 1 SW. It will not spend resources
  to try to succeed at the Wound Check.
  '''
  def __init__(self):
    self._chosen_ap = 0
    self._chosen_bonuses = []

  def recommend(self, character, event, context):
    if isinstance(event, events.WoundCheckRolledEvent):
      if event.subject == character:
        self.reset()
        # how many wounds would I take?
        expected_sw = character.wound_check(event.roll)
        if expected_sw == 0:
          # ignore it if no SW expected
          yield event
        else:
          # calculate how many SW are tolerable
          # normally 1 SW is tolerable
          # but if one wound means defeat, then only 0 SW is tolerable
          tolerable_sw = min(1, character.sw_remaining() - 1)
          # use wound check specific floating bonuses
          new_event = self.use_floating_bonuses(character, event, tolerable_sw, 'wound check')
          new_expected_sw = character.wound_check(new_event.roll)
          if new_expected_sw > tolerable_sw:
            # use adventure points
            new_event = self.use_ap(character, new_event, tolerable_sw, 'wound check')
          new_expected_sw = character.wound_check(new_event.roll)
          # check if anything changed
          new_expected_sw = character.wound_check(new_event.roll)
          if new_expected_sw < expected_sw:
            # progress: spend resources and use the new roll
            for bonus in self._chosen_bonuses:
              yield events.SpendFloatingBonusEvent(character, bonus)
            yield events.SpendAdventurePointsEvent(character, skill, self._chosen_ap)
            yield new_event
          else:
            # but the future refused to change
            # spend nothing and take the hit
            yield event

  def reset(self):
    self._chosen_ap = 0
    self._chosen_bonuses.clear()

  def use_ap(self, character, event, tolerable_sw, skill):
    ap = character.ap()
    max_spend = min(ap, character.max_ap_per_roll())
    new_roll = event.roll
    if character.can_spend_ap('wound check'):
      new_expected_sw = character.wound_check(new_roll)
      while self._chosen_ap < max_spend:
        self._chosen_ap += 1
        new_roll += 5
        new_expected_sw = character.wound_check(new_roll)
        if new_expected_sw == tolerable_sw:
          break
    return events.WoundCheckRolledEvent(event.subject, event.attacker, event.damage, new_roll, tn=event.tn)

  def use_floating_bonuses(self, character, event, tolerable_sw, skill):
    available_bonuses = character.floating_bonuses(skill)
    available_bonuses.sort()
    new_roll = event.roll
    new_expected_sw = character.wound_check(new_roll)
    for bonus in available_bonuses:
      self._chosen_bonuses.append(bonus)
      new_roll += bonus.bonus()
      new_expected_sw = character.wound_check(new_roll)
      if new_expected_sw == tolerable_sw:
        break
    return events.WoundCheckRolledEvent(event.subject, event.attacker, event.damage, new_roll, tn=event.tn)


class AlwaysKeepLightWoundsStrategy(Strategy):
  '''
  Strategy that always keeps LW.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.WoundCheckSucceededEvent):
      if event.subject == character:
        logger.info('{} always keeps light wounds'.format(character.name()))
        yield events.KeepLightWoundsEvent(event.subject, event.attacker, event.damage, tn=event.tn)


class KeepLightWoundsStrategy(Strategy):
  '''
  Strategy to decide whether to keep LW or take SW.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.WoundCheckSucceededEvent):
      if event.subject == character:
        if event.tn > event.roll:
          raise RuntimeError('KeepLightWoundsStrategy should not be consulted for a failed wound check')
        # keep LW to avoid defeat
        if character.sw_remaining() == 1:
          logger.info('{} keeping light wounds to avoid defeat.'.format(character.name()))
          yield events.KeepLightWoundsEvent(character, event.attacker, event.damage, tn=event.tn)
          return
        # consult KeepLightWoundsOptimizer
        optimizer = DefaultKeepLightWoundsOptimizer(character, context)
        (should_keep, reserve_vp) = optimizer.should_keep(1, 0.6, max_vp=1)
        if should_keep:
          logger.info('{} keeping {} LW and reserving {} VP for a future Wound Check' \
            .format(character.name(), character.lw(), reserve_vp))
          character.void_point_manager().reserve('wound check', reserve_vp)
          yield events.KeepLightWoundsEvent(character, event.attacker, event.damage, tn=event.tn)
        else:
          logger.info('{} taking a serious wound because the next wound check might be bad.'.format(character.name()))
          yield events.TakeSeriousWoundEvent(character, event.attacker, event.damage, tn=event.tn)


class NeverKeepLightWoundsStrategy(Strategy):
  '''
  Strategy that never keeps LW, always takes SW.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.WoundCheckSucceededEvent):
      if event.subject == character:
        logger.info('{} never keeps light wounds'.format(character.name()))
        yield events.SeriousWoundsDamageEvent(event.attacker, character, 1)


class WoundCheckStrategy(Strategy):
  '''
  Strategy to decide how many VP to spend on a wound check.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.LightWoundsDamageEvent):
      if event.target == character:
        # calculate maximum tolerable SW
        max_sw = min(1, character.sw_remaining() - 1)
        optimizer = character.wound_check_optimizer_factory().get_wound_check_optimizer(character, event, context)
        yield optimizer.declare(max_sw, 0.6)


class StingyWoundCheckStrategy(Strategy):
  '''
  Never spend VP on wound checks.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.LightWoundsDamageEvent):
      if event.target == character:
        logger.info('{} never spends VP on wound checks.'.format(character.name()))
        yield events.WoundCheckDeclaredEvent(character, event.subject, event.damage, tn=event.tn)

