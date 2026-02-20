#!/usr/bin/env python3

#
# listeners.py
#
# Implement event listeners for L7R combat simulator.
#

from abc import ABC, abstractmethod

from simulation import events, modifiers, modifier_listeners
from simulation.log import logger


class Listener(ABC):
  '''
  Class that responds to an Event for a Character.
  A Listener should be the only way that a Character's state is modified during a simulation.
  Listeners should not make decisions, they should only implement rules.
  If a Character has a choice about how to respond to an Event,
  then the Listener for that Event should consult a Strategy.
  '''
  @abstractmethod
  def handle(self, character, event, context):
    '''
    handle(character, event, context) -> yield one or more Event, or None
      character (Character): the Character that is responding to the Event
      event (Event): the Event that is being handled
      context (EngineContext): context about other Characters and groups of Characters

    Handles an Event for a Character. Yields one or more events if appropriate,
    or may return None.
    This function must determine if the Character needs to respond to the Event.
    If the Character needs to make a decision about how to respond -
    for example, what kind of action to take, or whether to parry or counterattack,
    or whether to spend resources like void points - then this
    function gets a Strategy from the Character and delegates the decision to the Strategy.
    '''
    pass


class NewRoundListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.NewRoundEvent):
      character.roll_initiative()
      yield from ()


class YourMoveListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.YourMoveEvent):
      if character == event.subject:
        yield from character.action_strategy().recommend(character, event, context)


class AddModifierListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.AddModifierEvent):
      if character == event.subject:
        character.add_modifier(event.modifier)
      else:
        character.knowledge().observe_modifier_added(event.subject, event.modifier)
      yield from ()


class RemoveModifierListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.AddModifierEvent):
      if character == event.subject:
        character.remove_modifier(event.modifier)
      else:
        character.knowledge().observe_modifier_removed(event.subject, event.modifier)
      yield from ()


class AttackDeclaredListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.AttackDeclaredEvent):
      if character != event.action.subject():
        # TODO: implement something for predeclaring parries
        if event.action.skill() == 'lunge':
          if event.action.subject() not in character.group():
            # gain expiring modifier for lunge
            modifier = modifiers.AnyAttackModifier(character, event.subject(), 5)
            attack_listener = modifier_listeners.ExpireAfterNextAttackByCharacterListener(modifier, event.action.subject())
            end_of_round_listener = modifier_listeners.ExpireAtEndOfRoundListener(modifier)
            modifier.register_listener('attack_failed', attack_listener)
            modifier.register_listener('attack_succeeded', attack_listener)
            modifier.register_listener('end_of_round', end_of_round_listener)
            yield events.AddModifierEvent(modifier)
          

class AttackRolledListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.AttackRolledEvent):
      if character != event.action.subject():
        character.knowledge().observe_attack_roll(event.action.subject(), event.roll)
        yield from character.parry_strategy().recommend(character, event, context)


class FeintSucceededListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.AttackSucceededEvent):
      if event.action.subject() == character:
        if event.action.skill() == 'feint':
          character.gain_tvp(1)
          if len(character.actions()) > 0:
            max_action = max(character.actions())
            character.actions().remove(max_action)
            character.actions().insert(context.phase())
            yield events.InitiativeChangedEvent()


class LightWoundsDamageListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.LightWoundsDamageEvent):
      if event.subject != character:
        # observe another character's damage roll
        character.knowledge().observe_damage_roll(event.subject, event.damage)
      if event.target == character:
        character.take_lw(event.damage)
        # continue with wound check if the damage roll was nonzero
        if event.damage > 0:
          yield from character.wound_check_strategy().recommend(character, event, context)


class SeriousWoundsDamageListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.SeriousWoundsDamageEvent):
      if event.target == character:
        character.take_sw(event.damage)
        if not character.is_alive():
          yield events.DeathEvent(character)
        elif not character.is_conscious():
          yield events.UnconsciousEvent(character)
        elif not character.is_fighting():
          yield events.SurrenderEvent(character)
      else:
        character.knowledge().observe_wounds(event.target, event.damage)


class TakeActionListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.TakeActionEvent):
      if character != event.subject:
        character.knowledge().observe_action(event.subject)
        yield from ()


class TakeSeriousWoundListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.TakeSeriousWoundEvent):
      if event.subject == character:
        character.reset_lw()
        yield events.SeriousWoundsDamageEvent(event.attacker, character, 1)


class GainTemporaryVoidPointsListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.GainTemporaryVoidPointsEvent):
      if event.subject == character:
        character.gain_tvp(event.amount)
        yield from ()

class SpendActionListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.SpendActionEvent):
      if event.subject == character:
        character.spend_action(event.initiative_action)
        yield from ()


class SpendAdventurePointsListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.SpendAdventurePointsEvent):
      if event.subject == character:
        character.spend_ap(event.amount)
        yield from ()


class SpendFloatingBonusListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.SpendFloatingBonusEvent):
      if event.subject == character:
        character.spend_floating_bonus(event.bonus)
        yield from ()


class SpendVoidPointsListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.SpendVoidPointsEvent):
      if event.subject == character:
        character.spend_vp(event.amount)
        yield from ()


class WoundCheckDeclaredListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.WoundCheckDeclaredEvent):
      if event.subject == character:
        roll = character.roll_wound_check(event.damage, event.vp)
        if event.vp > 0:
          yield events.SpendVoidPointsEvent(character, 'wound check', event.vp)
        initial_roll = events.WoundCheckRolledEvent(character, event.attacker, event.damage, roll, tn=event.tn)
        yield from character.wound_check_rolled_strategy().recommend(character, initial_roll, context)


class WoundCheckFailedListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.WoundCheckFailedEvent):
      if event.subject == character:
        sw = character.wound_check(event.roll)
        character.reset_lw()
        yield events.SeriousWoundsDamageEvent(event.attacker, character, sw)


class WoundCheckRolledListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.WoundCheckRolledEvent):
      if event.subject == character:
        logger.debug('{} rolled wound check {} against tn {}'.format(character.name(), event.roll, event.tn))
        if event.roll < event.tn:
          # wound check failed
          yield events.WoundCheckFailedEvent(character, event.attacker, event.damage, event.roll, tn=event.tn)
        else:
          yield events.WoundCheckSucceededEvent(character, event.attacker, event.damage, event.roll, tn=event.tn)


class WoundCheckSucceededListener(Listener):
  def handle(self, character, event, context):
    if isinstance(event, events.WoundCheckSucceededEvent):
      if event.subject == character:
        # if the character may keep LW, consult the character's light wounds strategy
        yield from character.light_wounds_strategy().recommend(character, event, context)

