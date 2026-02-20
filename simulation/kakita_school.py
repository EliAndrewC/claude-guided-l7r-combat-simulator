#!/usr/bin/env python3

#
# kakita_school.py
#
# Implement Kakita Bushi School.
#

import random

from simulation import events, target_finders
from simulation.actions import AttackAction, DoubleAttackAction, LungeAction
from simulation.action_factory import DefaultActionFactory
from simulation.contested_actions import ContestedAction
from simulation.events import Event, ContestedActionEvent, LightWoundsDamageEvent
from simulation.initiative_actions import InitiativeAction
from simulation.listeners import Listener
from simulation.roll import DieProvider, InitiativeRoll
from simulation.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.roll_provider import DefaultRollProvider
from simulation.schools import BaseSchool
from simulation.strategies import Strategy


class KakitaBushiSchool(BaseSchool):
  def ap_base_skill(self):
    return None

  def apply_rank_five_ability(self, character):
    character.set_listener('new_phase', KakitaNewPhaseListener())

  def apply_rank_four_ability(self, character):
    self.apply_school_ring_raise_and_discount(character)
    character.set_roll_parameter_provider(KAKITA_ROLL_PARAMETER_PROVIDER)

  def apply_rank_three_ability(self, character):
    character.set_action_factory(KAKITA_ACTION_FACTORY)

  def apply_special_ability(self, character):
    character.set_roll_provider(KAKITA_ROLL_PROVIDER)
    character.add_interrupt_skill('iaijutsu')

  def extra_rolled(self):
    return ['double attack', 'iaijutsu', 'initiative']

  def free_raise_skills(self):
    return [ 'iaijutsu' ]

  def name(self):
    return 'Kakita Bushi School'

  def school_knacks(self):
    return ['double attack', 'iaijutsu', 'lunge']

  def school_ring(self):
    return 'fire'

#
# duels
#
# Show Me Your Stance
#
# Roll Air+Iaijutsu
# Result / 5 discerns opponent's Fire with confidence level
# Result / 1 discerns TN to hit opponent with confidence level
#
# Contested Iaijutsu
#
# Roll Fire + Iaijutsu
# Winner choses to Focus or Strike first
#
# Focus
#
# Choose whether to Focus or Strike.
# Focus increases your TN to be hit by 5
#
# Strike
#
# Both characters roll Fire + Iaijutsu
#
# Damage
#
# Roll one extra die for each 1 by which you exceeded the TN
# Each extra rolled die after 10k10 is +5
#
# If neither hits: repeat.
#
# The character who rolled higher gets a Free Raise to future damage
#
# If either or both hit: continue in normal combat
#
# duels as events:
#
# IaijutsuDuelEvent with play method
#
# ShowMeYourStanceEvent with play method
#   ShowMeYourStanceDeclared
#   ShowMeYourStanceRolled
# 
# DuelInitiativeEvent with play method
#   DuelInitiativeDeclared (you do not know your opponent's skill yet)
#   DuelInitiativeRolled
# 
# play DuelFocusOrStrikeEvent on each character in turn
#   IaijutsuFocusEvent or IaijutsuStrikeEvent
#
# characters will respond to IaijutsuStrikeEvent with IaijutsuStrikeRolledEvent
#
# event responds by evaluating whether characters hit, rolling damage, and playing LWDEvent
#
# engine evaluates whether characters are alive and whether either hit
#
# then moves to end of combat or normal combat
#   


class ContestedIaijutsuAttackAction(ContestedAction):
  '''
  ContestedAction for the Kakita Duelist School 5th Dan ability:

  "At the beginning of phase 0 in each combat round, make a
  contested iaijutsu roll against an opponent. If the opponent
  doesn't have iaijutsu, they may roll attack instead, and you get
  an extra free raise. Make a damage roll against this opponent; if
  you won the contested roll then roll 1 extra damage die for every
  5 by which your roll exceeded your opponent's, and if you lost
  then roll 1 fewer damage die for every 5 by which their roll
  exceeded yours."
  '''
  def calculate_extra_damage_dice(self, opponent_skill_roll=None, skill_roll=None):
    if skill_roll is None:
      skill_roll = self.skill_roll()
    if opponent_skill_roll is None:
      opponent_skill_roll = self.opponent_skill_roll()
    return (skill_roll - opponent_skill_roll) // 5

  def damage_roll(self):
    return self._damage_roll

  def is_hit(self):
    extra_rolled = self.calculate_extra_damage_dice()
    (rolled, kept, bonus) = self.challenger() \
      .get_damage_roll_params(self.defender(), self.challenger_skill(), extra_rolled)
    return kept > 0

  def roll_damage(self):
    extra_rolled = self.calculate_extra_damage_dice()
    damage_roll = self.challenger().roll_damage(self.defender(), self.skill(), extra_rolled, vp=self.vp())
    damage_roll = max(0, damage_roll)
    self.set_damage_roll(damage_roll)
    return damage_roll

  def set_damage_roll(self, damage):
    if not isinstance(damage, int):
      raise ValueError('set_damage_roll requires int')
    self._damage_roll = damage

  def skill_roll_params(self):
    (rolled, kept, modifier) = super().skill_roll_params()
    if self.skill() == 'attack':
      # TODO: consider rewriting this as an expiring Modifier instead
      modifier -= 5
    return (rolled, kept, modifier)


class TakeContestedIaijutsuAttackAction(Event):
  '''
  Playable event to run the contested attack action from the Kakita 5th Dan ability.
  '''
  def __init__(self, challenger, defender, challenger_action, \
      defender_action):
    super().__init__('take_contested_iaijutsu_attack_action')
    self._challenger = challenger
    self._defender = defender
    self._challenger_action = challenger_action
    self._defender_action = defender_action

  def play(self, context):
    yield from self.declare(context)
    yield from self.roll_skill(context)
    if self.challenger_action().is_hit():
      yield from self.roll_damage()

  def challenger(self):
    return self._challenger
     
  def challenger_action(self):
    return self._challenger_action

  def declare(self, context):
    yield ContestedIaijutsuAttackDeclaredEvent(self.challenger_action())
    yield ContestedIaijutsuAttackDeclaredEvent(self.defender_action())

  def defender(self):
    return self._defender
     
  def defender_action(self):
    return self._defender_action

  def roll_damage(self):
    damage_roll = self.challenger_action().roll_damage()
    yield LightWoundsDamageEvent(self.challenger(), self.defender(), \
      damage_roll, tn=self.defender_action().skill_roll())

  def roll_skill(self, context):
    # challenger rolls
    challenger_roll = self.challenger_action().roll_skill()
    # spend challenger VP
    if self.challenger_action().vp() > 0:
      yield SpendVoidPointsEvent(self.challenger(), \
        self.challenger_action().skill(), self.challenger_action().vp())
    # defender rolls
    defender_roll = self.defender_action().roll_skill()
    # spend defender VP
    if self.defender_action().vp() > 0:
      yield SpendVoidPointsEvent(self.defender(), \
        self.defender_action().skill(), self.defender_action().vp())
    # set opposing character's roll on each side's action
    self.challenger_action().set_opponent_skill_roll(defender_roll)
    self.defender_action().set_opponent_skill_roll(challenger_roll)
    # yield rolled events
    yield ContestedIaijutsuAttackRolledEvent(self.challenger_action())
    yield ContestedIaijutsuAttackRolledEvent(self.defender_action())


class ContestedIaijutsuAttackDeclaredEvent(ContestedActionEvent):
  def __init__(self, action):
    super().__init__('contested_iaijutsu_attack_declared', action)


class ContestedIaijutsuAttackRolledEvent(ContestedActionEvent):
  def __init__(self, action):
    super().__init__('contested_iaijutsu_attack_rolled', action)


class ContestedIaijutsuAttackDeclaredListener(Listener):
  '''
  Listener to respond to ContestedIaijutsuAttackDeclaredEvent.
  Character needs to decide how many VP to spend.
  '''
  def handle(self, character, event, context):
    if isinstance(event, ContestedIaijutsuAttackDeclaredEvent):
      if event.action.subject() == character:
        character.contested_iaijutsu_attack_declared_strategy() \
          .handle(character, event, context)
        yield from ()


class ContestedIaijutsuAttackDeclaredStrategy(Listener):
  '''
  Strategy to decide how many VP to spend when declaring the
  contested iaijutsu attack for the Kakita Bushi School 5th Dan
  ability.

  Generally the Kakita should not spend VP, but the target might
  need to spend VP to reduce damage.
  '''
  def handle(self, character, event, context):
    if isinstance(event, ContestedIaijutsuAttackDeclaredEvent):
      challenger = event.action.challenger()
      if challenger != character:
        # the challenger is a 5th Dan Kakita Bushi
        # iaijutsu must be 5, fire is at least 4, probably higher
        character.knowledge().observe_skill(challenger, 'double attack', 5)
        character.knowledge().observe_skill(challenger, 'iaijutsu', 5)
        character.knowledge().observe_skill(challenger, 'lunge', 5)
        character.knowledge().observe_ring(challenger, 'fire', 5)
      if event.subject == character and challenger != character \
          and character.void_point_manager().vp('attack') > 0:
        # estimate challenger's roll
        challenger_roll = context.mean_roll(10, 6, 5)
        # estimate my roll
        my_roll_params = character.get_skill_roll_params(challenger, \
          event.action.skill(), \
          contested_skill=event.action.contested_skill(), \
          ring=event.action.ring(), vp=event.action.vp())
        my_roll = context.mean_roll(my_roll_params)
        # estimate damage params
        extra_rolled = (challenger_roll - my_roll) // 5
        (damage_rolled, damage_kept, damage_mod) \
          = normalize_roll_params(10 + extra_rolled, 2, 5)
        # spend VP if too many kept damage dice
        vp = 1 if damage_kept > 3 else 0
        event.action.set_vp(vp)
    yield from ()


class KakitaAttackAction(AttackAction):
  '''
  AttackAction to implement the Kakita Bushi School Third Dan
  ability:

  "Your attacks get a bonus of X for each phase before the
  defender's next action they occur, where X is equal to your
  attack skill. If a defender does not have an action remaining in
  this round, they are considered to act in phase 11. This applies
  to all types of attacks, and you know the next action of everyone
  within striking range."
  '''
  def skill_roll_params(self):
    (rolled, kept, modifier) = self.subject().get_skill_roll_params( \
      self.target(), self.skill(), vp=self.vp())
    # calculate tempo bonus
    subject_tempo = self.context().phase()
    target_tempo = 11
    if len(self.target().actions()) > 0:
      target_tempo = min(self.target().actions())
    tempo_diff = max(0, target_tempo - subject_tempo)
    tempo_bonus = self.subject().skill('attack') * tempo_diff
    return (rolled, kept, modifier + tempo_bonus)


class KakitaDoubleAttackAction(DoubleAttackAction):
  '''
  DoubleAttackAction to implement the Kakita Bushi School Third Dan
  ability.
  '''
  def skill_roll_params(self):
    (rolled, kept, modifier) = self.subject().get_skill_roll_params( \
      self.target(), self.skill(), vp=self.vp())
    # calculate tempo bonus
    subject_tempo = self.context().phase()
    target_tempo = 11
    if len(self.target().actions()) > 0:
      target_tempo = min(self.target().actions())
    tempo_diff = min(0, target_tempo - subject_tempo)
    tempo_bonus = self.subject().skill('attack') * tempo_diff
    return (rolled, kept, modifier + tempo_bonus)


class KakitaLungeAction(LungeAction):
  '''
  LungeAction to implement the Kakita Bushi School Third Dan
  ability.
  '''
  def skill_roll_params(self):
    (rolled, kept, modifier) = self.subject().get_skill_roll_params( \
      self.target(), self.skill(), vp=self.vp())
    # calculate tempo bonus
    subject_tempo = self.context().phase()
    target_tempo = 11
    if len(self.target().actions()) > 0:
      target_tempo = min(self.target().actions())
    tempo_diff = min(0, target_tempo - subject_tempo)
    tempo_bonus = self.subject().skill('attack') * tempo_diff
    return (rolled, kept, modifier + tempo_bonus)


class KakitaActionFactory(DefaultActionFactory):
  '''
  ActionFactory to return Kakita specific attack action implementations.
  '''
  def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
    if skill in ('attack', 'iaijutsu'):
      return KakitaAttackAction(subject, target, skill, initiative_action, context, vp=vp)
    elif skill == 'double attack':
      return KakitaDoubleAttackAction(subject, target, skill, initiative_action, context, vp=vp)
    elif skill == 'lunge':
      return KakitaLungeAction(subject, target, skill, initiative_action, context, vp=vp)
    else:
      raise ValueError('Invalid attack skill: {}'.format(skill))

# singleton instance
KAKITA_ACTION_FACTORY = KakitaActionFactory()


class KakitaInitiativeDieProvider(DieProvider):
  '''
  DieProvider that rolls dice with ten faces from 0 to 9,
  used for Kakita initiative rolls.
  '''
  def roll_die(self, faces=10, explode=True):
    '''
    roll_die(faces=10, explode=True) -> int
      faces (int): ignored
      explode (bool): ignored
    
    Returns the result of rolling a ten sided die with faces
    from 0 to 9.

    This DieProvider provides results on the interval
    [0,faces), and never explodes.
    '''
    return random.randint(0, 9)

# singleton instance
KAKITA_INITIATIVE_DIE_PROVIDER = KakitaInitiativeDieProvider()


class KakitaNewPhaseListener(Listener):
  '''
  Listener to implement the Kakita Bushi School 5th Dan ability:

  "At the beginning of phase 0 in each combat round, make a
  contested iaijutsu roll against an opponent. If the opponent
  doesn't have iaijutsu, they may roll attack instead, and you get
  an extra free raise. Make a damage roll against this opponent; if
  you won the contested roll then roll 1 extra damage die for every
  5 by which your roll exceeded your opponent's, and if you lost
  then roll 1 fewer damage die for every 5 by which their roll
  exceeded yours."
  '''
  def __init__(self):
    self._target_finder = target_finders.FinishHimTargetFinder()

  def handle(self, character, event, context):
    if isinstance(event, events.NewPhaseEvent) and event.phase == 0:
      initiative_action = InitiativeAction([], 0)
      target = self._target_finder \
        .find_target(character, 'iaijutsu', initiative_action, \
          context)
      for other_character in context.characters():
        if other_character != character:
          target = other_character
      if target is not None:
        # determine target's skill (iaijutsu or attack)
        target_skill = 'iaijutsu'
        if target.skill('iaijutsu') == 0:
          target_skill = 'attack'
        # set up contested actions
        my_action = ContestedIaijutsuAttackAction(character, target, character, 'iaijutsu', target_skill, initiative_action, context)
        target_action = ContestedIaijutsuAttackAction(target, character, character, target_skill, 'iaijutsu', initiative_action, context)
        # set up take attack event and yield
        event = TakeContestedIaijutsuAttackAction(character, target, my_action, target_action)
        yield event


class KakitaRollParameterProvider(DefaultRollParameterProvider):
  '''
  RollParameterProvider to implement the Kakita Bushi School
  Fourth Dan ability:

  "You get a free raise to all damage rolls from attacks using
  iaijutsu."
  '''
  def get_damage_roll_params(self, character, target, skill, \
      attack_extra_rolled, vp=0):
    # calculate extra rolled dice
    ring = character.ring(character.get_skill_ring('damage'))
    my_extra_rolled = character.extra_rolled('damage')
    rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled()
    # calculate extra kept dice
    kept = character.weapon().kept() + character.extra_kept('damage')
    # calculate modifier
    mod = character.modifier(None, 'damage')
    if skill == 'iaijutsu':
      mod += 5
    return normalize_roll_params(rolled, kept, mod)

# singleton instance
KAKITA_ROLL_PARAMETER_PROVIDER = KakitaRollParameterProvider()


class KakitaRollProvider(DefaultRollProvider):
  '''
  RollProvider to implement the Kakita Bushi School special ability:
  "Your tens on initiative rolls are considered to be in a special
  Phase 0."
  '''
  def get_initiative_roll(self, rolled, kept):
    return InitiativeRoll(rolled, kept, \
      die_provider=KAKITA_INITIATIVE_DIE_PROVIDER).roll()

# singleton instance
KAKITA_ROLL_PROVIDER = KakitaRollProvider()

