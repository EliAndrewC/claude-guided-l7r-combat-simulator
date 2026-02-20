#!/usr/bin/env python3

#
# character.py
#
# Class to represent a character in L7R combat simulations.
#

import math
import uuid

from simulation import actions, kakita_school, listeners, strategies
from simulation.attack_optimizer_factory import AttackOptimizerFactory, DEFAULT_ATTACK_OPTIMIZER_FACTORY
from simulation.action_factory import ActionFactory, DEFAULT_ACTION_FACTORY
from simulation.knowledge import Knowledge
from simulation.log import logger
from simulation.modifiers import FreeRaise
from simulation.professions import Profession
from simulation.roll import normalize_roll_params
from simulation.roll_params import DEFAULT_ROLL_PARAMETER_PROVIDER, RollParameterProvider
from simulation.roll_provider import DEFAULT_ROLL_PROVIDER, RollProvider
from simulation.schools import School
from simulation.strategies import Strategy
from simulation.take_action_event_factory import DEFAULT_TAKE_ACTION_EVENT_FACTORY, TakeActionEventFactory
from simulation.target_finders import EasiestTargetFinder, TargetFinder
from simulation.weapons import KATANA, Weapon
from simulation.wound_check_optimizers import WoundCheckOptimizer
from simulation.wound_check_optimizer_factory import DEFAULT_WOUND_CHECK_OPTIMIZER_FACTORY, WoundCheckOptimizerFactory
from simulation.wound_check_provider import DEFAULT_WOUND_CHECK_PROVIDER, WoundCheckProvider
from simulation.void_point_manager import VoidPointManager


RING_NAMES = ['air', 'earth', 'fire', 'water', 'void']

class Character(object):

  def __init__(self, name=None):
    # initialize a character ID
    self._character_id = uuid.uuid4().hex
    # initialize name
    if name is None:
      self._name = self._character_id
    elif not isinstance(name, str):
      raise ValueError('Character name must be str')
    else:
      self._name = name
    # initialize rings
    self._rings = {
      'air': 2,
      'earth': 2,
      'fire': 2,
      'void': 2,
      'water': 2 }
    # everything else
    self._actions = []
    self._action_factory = DEFAULT_ACTION_FACTORY
    self._advantages = []
    self._ap_base_skill = None
    self._ap_skills = []
    self._ap_spent = 0
    self._attack_optimizer_factory = DEFAULT_ATTACK_OPTIMIZER_FACTORY
    self._disadvantages = []
    self._discounts = {}
    self._extra_kept = {}
    self._extra_rolled = {}
    self._floating_bonuses = []
    self._group = None
    self._interrupt_skills = ['counterattack', 'parry']
    self._interrupt_costs = {}
    self._knowledge = Knowledge()
    self._modifiers = []
    # default listeners
    action_taken_listener = listeners.TakeActionListener()
    self._listeners = {
      'add_modifier': listeners.AddModifierListener(),
      'attack_declared': listeners.AttackDeclaredListener(),
      'attack_rolled': listeners.AttackRolledListener(),
      'contested_iaijutsu_attack_declared': kakita_school. \
        ContestedIaijutsuAttackDeclaredListener(),
      'gain_tvp': listeners.GainTemporaryVoidPointsListener(),
      'lw_damage': listeners.LightWoundsDamageListener(),
      'new_round': listeners.NewRoundListener(),
      'remove_modifier': listeners.RemoveModifierListener(),
      'spend_action': listeners.SpendActionListener(),
      'spend_ap': listeners.SpendAdventurePointsListener(),
      'spend_floating_bonus': listeners.SpendFloatingBonusListener(),
      'spend_vp': listeners.SpendVoidPointsListener(),
      'sw_damage': listeners.SeriousWoundsDamageListener(),
      'take_attack': action_taken_listener,
      'take_parry': action_taken_listener,
      'take_sw': listeners.TakeSeriousWoundListener(),
      'wound_check_declared': listeners.WoundCheckDeclaredListener(),
      'wound_check_failed': listeners.WoundCheckFailedListener(),
      'wound_check_rolled': listeners.WoundCheckRolledListener(),
      'wound_check_succeeded': listeners.WoundCheckSucceededListener(),
      'your_move': listeners.YourMoveListener()
    }
    self._lw = 0
    self._lw_history = []
    self._profession = None
    self._roll_parameter_provider = DEFAULT_ROLL_PARAMETER_PROVIDER
    self._roll_provider = DEFAULT_ROLL_PROVIDER
    self._school = None
    self._skills = { 'attack': 1, 'parry': 1 }
    self._skill_rings = {
      'attack': 'fire',
      'counterattack': 'fire',
      'damage': 'fire',
      'double attack': 'fire',
      'feint': 'fire',
      'iaijutsu': 'fire',
      'initiative': 'void',
      'lunge': 'fire',
      'parry': 'air',
      'wound check': 'water'
    }
    # default strategies
    self._strategies = {
      'action': strategies.HoldOneActionStrategy(),
      'attack': strategies.UniversalAttackStrategy(),
      'attack_rolled': strategies.AttackRolledStrategy(),
      'contested_iaijutsu_attack_declared': kakita_school \
        .ContestedIaijutsuAttackDeclaredStrategy(),
      'light_wounds': strategies.KeepLightWoundsStrategy(),
      'parry': strategies.ReluctantParryStrategy(),
      'parry_rolled': strategies.ParryRolledStrategy(),
      'wound_check': strategies.WoundCheckStrategy(),
      'wound_check_rolled': strategies.WoundCheckRolledStrategy()
    }
    self._sw = 0
    self._take_action_event_factory = DEFAULT_TAKE_ACTION_EVENT_FACTORY
    self._target_finder = EasiestTargetFinder()
    self._tvp = 0
    self._vp_spent = 0
    self._weapon = KATANA
    self._wound_check_optimizer_factory = DEFAULT_WOUND_CHECK_OPTIMIZER_FACTORY
    self._wound_check_provider = DEFAULT_WOUND_CHECK_PROVIDER
    self._void_point_manager = VoidPointManager(self)

  def actions(self):
    '''
    actions() -> list of int

    Returns the actions this character has remaining for the round.
    '''
    return self._actions

  def action_factory(self):
    '''
    action_factory() -> ActionFactory

    Returns this character's action factory, which is used to generate attack, counterattack, and parry actions.
    Delegating this to a factory helps us support special abilities.
    '''
    return self._action_factory

  def action_strategy(self):
    return self._strategies['action']

  def add_discount(self, item, discount):
    '''
    add_discount(item, discount)
      item (str): thing to discount
      discount (int): amount to discount the item

    Grant this character a future discount for buying something (a ring or skill).
    '''
    if item in self._discounts:
      self._discounts[item] += discount
    else:
      self._discounts[item] = discount

  def add_interrupt_skill(self, skill):
    if not isinstance(skill, str):
      raise ValueError('add_interrupt_skill skill argument must be str')
    if skill not in self._interrupt_skills:
      self._interrupt_skills.append(skill)

  def add_modifier(self, modifier):
    '''
    add_modifier(modifier)

    Add a modifier to this character.
    '''
    # TODO: register modifier listeners
    self._modifiers.append(modifier)

  def advantages(self):
    return self._advantages

  def ap(self):
    '''
    ap() -> int

    Return the number of Adventure Points (Third Dan Free Raises) this character has available to spend.
    '''
    return (2 * self.skill(self.ap_base_skill())) - self._ap_spent

  def ap_base_skill(self):
    '''
    ap_base_skill() -> str

    Return the base skill used to calculate this character's
    Adventure Points (3rd Dan Free Raises), or None.
    '''
    return self._ap_base_skill

  def attack_optimizer_factory(self):
    return self._attack_optimizer_factory

  def attack_rolled_strategy(self):
    return self._strategies['attack_rolled']

  def attack_strategy(self):
    return self._strategies['attack']

  def can_spend_ap(self, skill):
    '''
    can_spend_ap(skill) -> bool
      skill (str): name of a skill to check

    Returns whether this character can spend Adventure Points
    (Third Dan Free Raises) on the given skill.
    '''
    return skill in self._ap_skills

  def character_id(self):
    return self._character_id

  def contested_iaijutsu_attack_declared_strategy(self):
    return self._strategies['contested_iaijutsu_attack_declared']

  def crippled(self):
    '''
    crippled() -> bool

    Return whether this Character is crippled.
    Crippled characters do not reroll tens on skill rolls.
    '''
    # TODO: does anything change this threshold?
    return self.sw() >= self.ring('earth')

  def disadvantages(self):
    return self._disadvantages

  def event(self, event, context):
    if event.name in self._listeners.keys():
      logger.debug('{} handling {}'.format(self._name, event.name))
      # play event on modifiers first
      for modifier in self._modifiers:
        yield from modifier.handle(self, event, context)
      # then play event on self
      yield from self._listeners[event.name].handle(self, event, context)
    else:
      logger.debug('{} ignoring {}'.format(self._name, event.name))

  def extra_kept(self, skill):
    return self._extra_kept.get(skill, 0)

  def extra_rolled(self, skill):
    return self._extra_rolled.get(skill, 0)

  def floating_bonuses(self, skill):
    '''
    floating_bonuses(skill) -> list of FloatingBonus
      skill (str): skill or thing on which the bonuses may be spent

    Returns the list of "floating bonuses" that may be spend on a skill or action. 
    '''
    return [bonus for bonus in self._floating_bonuses if bonus.is_applicable(skill)]

  def friends(self):
    return self.group()

  def gain_action(self, phase):
    '''
    gain_action(phase)
      phase (int): phase of action die

    Gain an action in the given phase.
    '''
    if not isinstance(phase, int):
      raise ValueError('gain_action phase must be int')
    self._actions.append(phase)
    self._actions.sort()

  def gain_floating_bonus(self, floating_bonus):
    '''
    gain_floating_bonus(floating_bonus):
      floating_bonus (FloatingBonus): a floating bonus

    Gain a "floating bonus" that may be applied to future skill rolls.
    The floating bonus is an object that knows the skills on whcih it may be used.
    '''
    self._floating_bonuses.append(floating_bonus)

  def gain_tvp(self, n=1):
    '''
    gain_tvp(n=1)
      n (int): number of Temporary Void Points to gain

    Gain the specified number of Temporary Void Points.
    '''
    self._tvp += n

  def get_damage_roll_params(self, target, skill, attack_extra_rolled, vp=0):
    return self.roll_parameter_provider() \
      .get_damage_roll_params(self, target, skill, attack_extra_rolled, vp=vp)

  def get_initiative_roll_params(self):
    return self.roll_parameter_provider() \
      .get_initiative_roll_params(self)

  def get_skill_ring(self, skill):
    '''
    get_skill_ring(skill) -> str
      skill (str): skill of interest
    
    Returns the ring used to use the given skill.
    '''
    if not isinstance(skill, str):
      raise ValueError('skill must be str')
    return self._skill_rings.get(skill, 0)

  def get_skill_roll_params(self, target, skill, contested_skill=None, ring=None, vp=0):
    return self.roll_parameter_provider() \
      .get_skill_roll_params(self, target, skill, \
        contested_skill=contested_skill, ring=ring, vp=vp)

  def get_wound_check_roll_params(self, vp=0):
    return self.roll_parameter_provider() \
      .get_wound_check_roll_params(self, vp=vp)

  def group(self):
    return self._group

  def has_action(self, context):
    '''
    has_action(context) -> bool
      context (EngineContext): context to provide timing

    Return whether this character has an available action in the current phase.
    Does not consider interrupt actions.
    '''
    if len(self.actions()) == 0:
      return False
    else:
      return min(self.actions()) <= context.phase()

  def has_interrupt_action(self, skill, context):
    '''
    has_interrupt_action(skill, context) -> bool
      skill (str): name of the skill that would be used
      context (EngineContext): context to provide timing

    Return whether this character could do an interrupt action in the current phase.
    '''
    if skill in self._interrupt_skills:
      if self.interrupt_cost(skill, context) <= len(self.actions()):
        return True
    return False

  def interrupt_cost(self, skill, context):
    '''
    interrupt_cost(skill, context) -> int
      skill (str): skill to be used
      context (EngineContext): context to provide timing

    Return the number of actions that must be spent to interrupt
    using the given skill.
    '''
    return self._interrupt_costs.get(skill, 2)

  def initiative_priority(self, max_actions):
    '''
    initiative_priority(max_actions) -> int

    Calculate the initiative priority for this character.
    '''
    priority = 0
    exponent = max_actions + 1
    # initiative priority rewards lower actions
    for action in self._actions:
      priority += (10 - action) * math.pow(10, exponent)
      exponent -= 1
    # break ties with void ring
    priority += self.ring('void')
    return priority

  def is_alive(self):
    '''
    is_alive() -> bool

    Return whether this character is alive.
    '''
    return self.sw() <= self.max_sw()

  def is_conscious(self):
    '''
    is_conscious() -> bool

    Return whether this character is still conscious.
    '''
    return self.sw() < self.max_sw()

  def is_fighting(self):
    '''
    is_fighting() -> bool

    Return whether this character is still fighting.
    '''
    # TODO: implement a surrender strategy
    return self.is_conscious()

  def is_friend(self, character):
    '''
    is_friend(character) -> bool

    Returns whether a character is a friend (in the same group).
    '''
    return character in self._group

  def knowledge(self):
    '''
    knowledge() -> Knowledge

    Returns this character's Knowledge instance.
    '''
    return self._knowledge

  def light_wounds_strategy(self):
    '''
    light_wounds_strategy(self) -> KeepLightWoundsStrategy

    Return the KeepLightWoundsStrategy that recommends whether this character should keep light wounds or take a serious wound.
    '''
    return self._strategies['light_wounds']

  def lw(self):
    '''
    lw() -> int

    Return this character's current Light Wound total.
    '''
    return self._lw

  def lw_history(self):
    '''
    lw_history() -> list of ints

    Return the amounts of damage this character has taken in the past.
    Used to predict future damage.
    '''
    return self._lw_history

  def max_ap_per_roll(self):
    '''
    max_ap_per_roll() -> int

    Return the maximum number of Adventure Points (3rd Dan Free Raises)
    this character may spend on a single roll.
    '''
    if self.ap_base_skill() is not None:
      return self.skill(self.ap_base_skill())
    else:
      return 0

  def max_sw(self):
    '''
    max_sw() -> int

    Return the number of Serious Wounds this character can take
    before unconsciousness.
    '''
    if 'great destiny' in self._advantages:
      bonus = 1
    elif 'permanent wound' in self._disadvantages:
      bonus = -1
    else:
      bonus = 0
    return (self.ring('earth') * 2) + bonus

  def max_vp(self):
    '''
    max_vp() -> int

    Return this character's capacity for Void Points, not including Temporary Void Points.
    '''
    return min([self.ring(ring) for ring in RING_NAMES]) + self.skill('worldliness')

  def max_vp_per_roll(self):
    '''
    max_vp_per_roll() -> int

    Return the maximum number of VP this character may spend on a single roll.
    '''
    return min([self.ring(ring) for ring in RING_NAMES])

  def modifier(self, target, skill):
    '''
    modifier(target, skill) -> int

    Returns the modifier (positive or negative) for using the given skill on a target.
    '''
    applicable_modifiers = [mod.apply(target, skill) for mod in self._modifiers]
    return sum(applicable_modifiers) if len(applicable_modifiers) > 0 else 0

  def name(self):
    return self._name

  def parry_strategy(self):
    return self._strategies['parry']

  def parry_rolled_strategy(self):
    return self._strategies['parry_rolled']

  def profession(self):
    return self._profession

  def remove_modifier(self, modifier):
    self._modifiers.remove(modifier)

  def reset(self):
    self._actions = []
    self._ap_spent = 0
    self._floating_bonuses.clear()
    self._knowledge.clear()
    self._lw = 0
    self._lw_history.clear()
    for modifier in self._modifiers:
      if len(modifier._listeners) > 0:
        self._modifiers.remove(modifier)
    self._sw = 0
    self._tvp = 0
    self._vp_spent = 0

  def reset_lw(self):
    '''
    reset_lw()

    Reset this character's Light Wound total to zero.
    '''
    self._lw = 0

  def ring(self, ring):
    '''
    ring(ring) -> int
      ring (str):  name of ring of interest

    Return this character's rank in the named ring.
    '''
    return self._rings[ring]

  def rings(self):
    return self._rings

  def roll_damage(self, target, skill, attack_extra_rolled=0, vp=0):
    '''
    roll_damage(target, skill, attack_extra_rolled, vp=0) -> int
      target (Character): target of the damage roll
      skill (str): name of the skill used for the attack
      attack_extra_rolled (int): number of extra rolled dice from the attack roll
      vp (int): number of Void Points to spend on the roll

    Roll damage for this Character against the specified target,
    using the specified skill, with the given number of extra rolled
    dice because of the attack, with the given number of VP.

    This is the function that should be used by other classes to
    make a Character roll damage.
    '''
    rolled, kept, mod = self.get_damage_roll_params(target, skill, attack_extra_rolled, vp)
    roll = self.roll_provider().get_damage_roll(rolled, kept) + mod
    logger.info('{} rolled damage: {}'.format(self._name, roll))
    return roll

  def roll_initiative(self):
    '''
    roll_initiative() -> list of ints

    Roll Initiative for this character.

    This is the function that should be used by other classes to
    make a Character roll initiative.
    '''
    (rolled, kept, mod) = self.get_initiative_roll_params()
    self._actions = self.roll_provider().get_initiative_roll(rolled, kept)
    logger.info('{} rolled initiative: {}'.format(self._name, self._actions))
    return self._actions

  def roll_parameter_provider(self):
    return self._roll_parameter_provider

  def roll_provider(self):
    return self._roll_provider

  def roll_skill(self, target, skill, contested_skill=None, ring=None, vp=0):
    '''
    roll_skill(skill, vp=0) -> int
      target (Character): character targeted with the skill
      skill (str): skill used for this roll
      contested_skill (str): if provided, names the skill the target
        is using to contest.
      ring (str): ring used for this roll. Defaults to None, which
        means the character's default ring for this skill is used,
        but may be specified to use another ring.
      vp (int): number of Void Points to spend on the roll

    Roll a skill for this character against the specified target.
    '''
    (rolled, kept, mod) = self.get_skill_roll_params(target, skill, contested_skill, ring, vp)
    explode = not self.crippled()
    roll = self.roll_provider().get_skill_roll(skill, rolled, kept, explode) + mod
    logger.info('{} rolled {}: {}'.format(self._name, skill, roll))
    return roll

  def roll_wound_check(self, damage, vp=0):
    '''
    roll_wound_check(damage, vp=0, ap=0) -> int
      damage (int): light wound total for the wound check
      vp (int): number of Void Points to spend on the roll

    Roll a Wound Check for this character.
    '''
    (rolled, kept, mod) = self.get_wound_check_roll_params(vp)
    roll = self.roll_provider().get_wound_check_roll(rolled, kept) + mod
    logger.info('{} rolled wound check {} against {} LW'.format(self._name, roll, damage))
    return roll

  def school(self):
    return self._school

  def set_action_factory(self, factory):
    if not isinstance(factory, ActionFactory):
      raise ValueError('Character action factory must be an ActionFactory')
    self._action_factory = factory

  def set_action_strategy(self, strategy):
    if not isinstance(strategy, Strategy):
      raise ValueError('Character action strategy must be a Strategy')
    self._strategies['action'] = strategy

  def set_attack_strategy(self, strategy):
    if not isinstance(strategy, Strategy):
      raise ValueError('Character attack strategy must be a Strategy')
    self._strategies['attack'] = strategy

  def set_actions(self, actions):
    if not isinstance(actions, list):
      raise ValueError('Character set_actions requires list of ints')
    for action in actions:
      if not isinstance(action, int):
        raise ValueError('Character set_actions requires list of ints')
    self._actions = actions

  def set_attack_optimizer_factory(self, factory):
    if not isinstance(factory, AttackOptimizerFactory):
      raise ValueError('set_attack_optimizer_factory requires AttackOptimizerFactory')
    self._attack_optimizer_factory = factory

  def set_extra_rolled(self, skill, extra_rolled=1):
    '''
    set_extra_rolled(skill, extra_rolled)
      skill (str): skill name
      extra_rolled (int): number of extra rolled dice.

    Set extra rolled dice for the given skill.
    '''
    if skill in self._extra_rolled.keys():
      self._extra_rolled[skill] += extra_rolled
    else:
      self._extra_rolled[skill] = extra_rolled

  def set_extra_kept(self, skill, extra_kept):
    '''
    set_extra_kept(skill, extra_rolled)
      skill (str): skill name
      extra_kept (int): number of extra kept dice.

    Set extra kept dice for the given skill.
    '''
    self._extra_kept[skill] = extra_kept

  def set_group(self, group):
    self._group = group

  def set_interrupt_cost(self, skill, actions):
    '''
    set_interrupt_cost(skill, action)
      skill (str): skill to set
      actions (int): number of actions to interrupt

    Set the interrupt cost for this character to use an action.
    '''
    self._interrupt_costs[skill] = actions

  def set_listener(self, event_name, listener):
    '''
    set_listener(event_name, listener)
      event_name (str): name of the event to listen for
      listener (Listener): listener to handle this event

    Set this character's listener for a named event.
    '''
    self._listeners[event_name] = listener

  def set_parry_strategy(self, strategy):
    if not isinstance(strategy, Strategy):
      raise ValueError('Character parry strategy must be a Strategy')
    self._strategies['parry'] = strategy

  def set_profession(self, profession):
    if not isinstance(profession, Profession):
      raise ValueError('Character set_profession function requires a Profession')
    self._profession = profession

  def set_ring(self, ring, rank):
    '''
    set_ring(ring, rank)
      ring (str): name of ring to set
      rank (int): new ring rank

    Set this character's ring at a new rank.
    '''
    if ring not in RING_NAMES:
      raise ValueError('{} is not a ring'.format(ring))
    self._rings[ring.lower()] = rank

  def set_roll_parameter_provider(self, provider):
    '''
    set_roll_parameter_provider(provider)
      provider (RollParameterProvider): a RollParameterProvider

    Set an alternative roll parameter provider for this character.
    Intended to support special schools.
    '''
    if not isinstance(provider, RollParameterProvider):
      raise ValueError('provider must be a RollParameterProvider')
    self._roll_parameter_provider = provider

  def set_roll_provider(self, provider):
    '''
    set_roll_provider(provider)
      provider (RollProvider): a RollProvider capable of doing
        rolls for damage, initiative, skills, and wound checks.

    Set an alternate roll provider for this character.
    Intended for use in testing to rig rolls for predictable outcomes.
    '''
    # verify the given roll_provider satisfies the roll provider API
    if not isinstance(provider, RollProvider):
      raise ValueError('provider must be a RollProvider')
    self._roll_provider = provider

  def set_school(self, school):
    if not isinstance(school, School):
      raise ValueError('Character set_school function requires a School')
    self._school = school

  def set_skill(self, skill, rank):
    '''
    set_skill(skill, rank)
      skill (str): name of skill to set
      rank (int): new skill rank

    Set this character's skill at a new rank.
    '''
    self._skills[skill.lower()] = rank

  def set_strategy(self, name, strategy):
    self._strategies[name] = strategy

  def set_take_action_event_factory(self, factory):
    if not isinstance(factory, TakeActionEventFactory):
      raise ValueError('Character take action event factory must be a TakeActionEventFactory')
    self._take_action_event_factory = factory

  def set_weapon(self, weapon):
    if not isinstance(weapon, Weapon):
      raise ValueError('set_weapon requires Weapon')
    self._weapon = weapon

  def set_wound_check_optimizer_factory(self, factory):
    if not isinstance(factory, WoundCheckOptimizerFactory):
      raise ValueError('set_wound_check_optimizer_factory requires WoundCheckOptimizerFactory')
    self._wound_check_optimizer_factory = factory

  def set_wound_check_provider(self, provider):
    if not isinstance(provider, WoundCheckProvider):
      raise ValueError('Provider is not a WoundCheckProvider')
    self._wound_check_provider = provider

  def skill(self, skill):
    '''
    skill(skill) -> int
      skill (str): name of skill of interest

    Returns this character's rank in the given skill.
    '''
    return self._skills.get(skill, 0)

  def skills(self):
    return self._skills

  def spend_action(self, initiative_action):
    '''
    spend_action(phase)
      initiative_action (InitiativeAction): initiative action being spent

    Spend a character's action dice.
    '''
    for die in initiative_action.dice():
      if die not in self._actions:
        raise ValueError('{} does not have an action in phase {}'.format(self.name(), die))
      self._actions.remove(die)

  def spend_ap(self, skill, n):
    '''
    spend_ap(skill, n)
      skill (str): name of the skill for which points are being spent
      n (int): number of points being spent

    Spend Adventure Points (Third Dan Free Raises) if allowed.
    '''
    if not self.can_spend_ap(skill):
      raise ValueError('{} may not spend Adventure Points on {}'.format(self.name(), skill))
    if n > 0:
      if self.ap() < n:
        raise ValueError('{} does not have enough Adventure Points')
      self._ap_spent += n

  def spend_floating_bonus(self, bonus):
    '''
    spend_floating_bonus(bonus)
      bonus (FloatingBonus): floating bonus being spent
    
    Spend a floating bonus.
    '''
    self._floating_bonuses.remove(bonus)

  def spend_vp(self, n):
    '''
    spend_vp(n)
      n (int): number of Void Points to spend

    Spend Void Points.
    '''
    if self.vp() < n:
      raise ValueError('Not enough Void Points')
    still_unspent = n
    while still_unspent > 0:
      if self._tvp > 0:
        self._tvp -= 1
        still_unspent -= 1
      elif self.vp() > 0:
        self._vp_spent += 1
        still_unspent -= 1
      else:
        raise ValueError('Not enough Void Points')

  def sw(self):
    '''
    sw() -> int

    Return the number of Serious Wounds this character has taken.
    '''
    return self._sw

  def sw_remaining(self):
    '''
    sw_remaining() -> int

    Return the number of Serious Wounds this character has remaining
    before unconsciousness.
    '''
    return self.max_sw() - self.sw() 

  def take_action_event_factory(self):
    return self._take_action_event_factory

  def take_advantage(self, advantage):
    self._advantages.append(advantage)
    if advantage == 'strength of the earth':
      self.add_modifier(FreeRaise(self, 'wound check'))

  def take_disadvantage(self, disadvantage):
    self._disadvantages.append(disadvantage)

  def take_lw(self, amount):
    '''
    take_lw(amount)
      amount (int): amount of Light Wounds to take

    Add the given amount of Light Wounds to this character's Light
    Wound total.
    '''
    logger.info('{} takes {} Light Wounds (new total: {})'.format(self._name, amount, amount + self.lw()))
    self._lw += amount
    self._lw_history.append(amount)

  def take_sw(self, amount):
    logger.info('{} takes {} Serious Wounds'.format(self._name, amount))
    self._sw += amount

  def target_finder(self):
    return self._target_finder

  def tn_to_hit(self):
    return (5 * (1 + self.skill('parry'))) + self.modifier(None, 'tn to hit')

  def tvp(self):
    '''
    tvp() -> int

    Return the number of Temporary Void Points this character has available to spend.
    Characters should spend TVP very freely.
    '''
    return self._tvp

  def void_point_manager(self):
    return self._void_point_manager

  def vp(self):
    '''
    vp() -> int

    Return the number of Void Points this character has available to spend.
    '''
    return self.max_vp() - self._vp_spent + self._tvp

  def weapon(self):
    return self._weapon

  def wound_check(self, roll, lw=None):
    if lw is None:
      lw = self.lw()
    return self.wound_check_provider().wound_check(roll, lw)

  def wound_check_optimizer_factory(self):
    return self._wound_check_optimizer_factory

  def wound_check_rolled_strategy(self):
    return self._strategies['wound_check_rolled']

  def wound_check_provider(self):
    return self._wound_check_provider

  def wound_check_strategy(self):
    '''
    wound_check_strategy() -> WoundCheckStrategy
    Return a WoundCheckStrategy that recommends how this character will spend VP on wound checks.
    '''
    return self._strategies['wound_check']

