#!/usr/bin/env python3

#
# events.py
#
# Events for the L7R combat simulator.
#

from simulation.log import logger


class Event(object):
  '''
  Events capture a moment in L7R combat mechanics when a character
  is affected, or a decision must be made.
  Examples:
   * new phase: characters with actions should decide what to do
   * attack rolled: characters should decide whether to parry
   * light wounds: character might decide to spend VP on wound check

  Events are basically messages. They should be treated as immutable.
  Other classes should never modify an event!

  Since we have the convention that events are immutable, we can also
  have the convention that other classes are expected to access members
  of events directly.

  Some events have a **play** method. This is a generator method that
  yields more events. This should only be done in exceptional
  circumstances.

  Every event can have different fields depending on the event,
  but there was some effort to have a kind of consistent vocabulary.
  **Subject**: if an event involves a character who is actively doing
               something, the **subject** of the event is the active
               character.
  **Target**:  if an event involves a character who is the direct
               object of something - such as being attacked, or taking
               damage - then the **target** of the event is that
               character.
  **Damage**:  events about damage, whether they're for receiving light
               wound, receiving serious wounds, or making a wound check,
               have a **damage** member for the amount of damage.
  '''
  def __init__(self, name):
    self.name = name


class TimingEvent(Event):
  pass

class NewRoundEvent(TimingEvent):
  def __init__(self, round):
    super().__init__('new_round')
    self.round = round

class NewPhaseEvent(TimingEvent):
  def __init__(self, phase):
    super().__init__('new_phase')
    self.phase = phase

class EndOfPhaseEvent(TimingEvent):
  def __init__(self, phase):
    super().__init__('end_of_phase')
    self.phase = phase

class EndOfRoundEvent(TimingEvent):
  def __init__(self, round):
    super().__init__('end_of_round')
    self.round = round


class YourMoveEvent(Event):
  '''
  Played on characters to ask them if they will use an action.
  '''
  def __init__(self, subject):
    super().__init__('your_move')
    self.subject = subject


class InitiativeChangedEvent(Event):
  def __init__(self):
    super().__init__('initiative_changed')


class ActionEvent(Event):
  def __init__(self, name, action):
    super().__init__(name)
    self.action = action

class ContestedActionEvent(Event):
  def __init__(self, name, contested_action):
    super().__init__(name)
    self.action = contested_action

class TakeActionEvent(ActionEvent):
  def __init__(self, name, action):
    super().__init__(name, action)


class TakeAttackActionEvent(TakeActionEvent):
  def __init__(self, action):
    super().__init__('take_attack', action)

  def play(self, context):
    yield self._declare_attack()
    yield from self._roll_attack(context)
    if self.action.parried():
      yield self._failed()
      return
    if self.action.is_hit():
      yield self._succeeded()
      direct_damage = self._direct_damage()
      if direct_damage is not None:
        yield direct_damage
      if self.action.target().is_fighting():
        yield self._roll_damage()
    else:
      yield self._failed()

  def _declare_attack(self):
    return AttackDeclaredEvent(self.action)
  
  def _direct_damage(self):
    return self.action.direct_damage()

  def _failed(self):
    logger.info('{} failed to attack {} with {}'.format(self.action.subject().name(), self.action.target().name(), self.action.skill()))
    return AttackFailedEvent(self.action)

  def _roll_attack(self,  context):
    attack_roll = self.action.roll_skill()
    if self.action.vp() > 0:
      yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), self.action.vp())
    initial_event = AttackRolledEvent(self.action, attack_roll)
    yield from self.action.subject().attack_rolled_strategy().recommend(self.action.subject(), initial_event, context)

  def _roll_damage(self):
    damage_roll = self.action.roll_damage()
    return LightWoundsDamageEvent(self.action.subject(), self.action.target(), damage_roll)

  def _succeeded(self):
    logger.info('{} successfully attacked {} with {}'.format(self.action.subject().name(), self.action.target().name(), self.action.skill()))
    return AttackSucceededEvent(self.action)


class TakeParryActionEvent(TakeActionEvent):
  def __init__(self, action):
    super().__init__('take_parry', action)

  def play(self, context):
    yield self._declare_parry()
    yield from self._roll_parry(context)
    if self.action.is_success():
      yield self._succeeded()
      return
    else:
      yield self._failed()
    
  def _declare_parry(self):
    declaration = ParryDeclaredEvent(self.action)
    self.action.set_attack_parry_declared(declaration)
    return declaration

  def _failed(self):
    logger.info('{} failed to parry {}'.format(self.action.subject().name(), self.action.target().name()))
    return ParryFailedEvent(self.action)

  def _roll_parry(self, context):
    parry_roll = self.action.roll_skill()
    self.action.set_attack_parry_attempted()
    if self.action.vp() > 0:
      yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), self.action.vp())
    initial_event = ParryRolledEvent(self.action, parry_roll)
    yield from self.action.subject().parry_rolled_strategy().recommend(self.action.subject(), initial_event, context)

  def _succeeded(self):
    logger.info('{} successfully parried {}'.format(self.action.subject().name(), self.action.target().name()))
    self.action.set_attack_parried()
    return ParrySucceededEvent(self.action)


class AttackDeclaredEvent(ActionEvent):
  def __init__(self, action):
    super().__init__('attack_declared', action)

class AttackRolledEvent(ActionEvent):
  def __init__(self, action, roll):
    super().__init__('attack_rolled', action)
    self.roll = roll

class AttackSucceededEvent(ActionEvent):
  def __init__(self, action):
    super().__init__('attack_succeeded', action)

class AttackFailedEvent(ActionEvent):
  def __init__(self, action):
    super().__init__('attack_failed', action)


class ParryDeclaredEvent(ActionEvent):
  def __init__(self, action):
    super().__init__('parry_declared', action)

class ParryPredeclaredEvent(ActionEvent):
  def __init__(self, action):
    super().__init__('parry_predeclared', action)

class ParryRolledEvent(ActionEvent):
  def __init__(self, action, roll):
    super().__init__('parry_rolled', action)
    self.roll = roll

class ParrySucceededEvent(ActionEvent):
  def __init__(self, action):
    super().__init__('parry_succeeded', action)

class ParryFailedEvent(ActionEvent):
  def __init__(self, action):
    super().__init__('parry_failed', action)


class DamageEvent(Event):
  '''
  Event used when a character takes damage.

  The "subject" is the character who inflicted the damage.
  The "target" is the character who is receiving the damage.
  The "damage" is the amount of damage inflicted.
  '''
  def __init__(self, name, subject, target, damage):
    super().__init__(name)
    self.subject = subject
    self.target = target
    if not isinstance(damage, int):
      raise ValueError('damage parameter must be int')
    self.damage = damage
 
class LightWoundsDamageEvent(DamageEvent):
  '''
  The LightWoundsDamageEvent also has the "wound_check_tn" field,
  which is the base TN to succeed at the Wound Check.

  Normally this is the character's Light Wound total, but there
  are certain abilities that modify the TN.
  '''
  def __init__(self, subject, target, damage, tn=None):
    super().__init__('lw_damage', subject, target, damage)
    if tn is None:
      self.wound_check_tn = damage
    else:
      if not isinstance(tn, int):
        raise ValueError('tn parameter must be int')
      self.wound_check_tn = tn

class SeriousWoundsDamageEvent(DamageEvent):
  def __init__(self, subject, target, damage):
    super().__init__('sw_damage', subject, target, damage)


class StatusEvent(Event):
  def __init__(self, name, subject):
    super().__init__(name)
    self.subject = subject

class CrippledEvent(StatusEvent):
  def __init__(self, name, subject):
    super().__init__('crippled', subject)

class NotCrippledEvent(Event):
  def __init__(self, name, subject):
    super().__init__('not_crippled', subject)


class DefeatEvent(StatusEvent):
  pass

class DeathEvent(DefeatEvent):
  def __init__(self, subject):
    super().__init__('death', subject)

class SurrenderEvent(DefeatEvent):
  def __init__(self, subject):
    super().__init__('surrender', subject)

class UnconsciousEvent(DefeatEvent):
  def __init__(self, subject):
    super().__init__('unconscious', subject)


class NotMovingEvent(StatusEvent):
  pass

class HoldActionEvent(NotMovingEvent):
  '''
  Response by characters to YourMoveEvent to indicate they are holding their action.
  '''
  def __init__(self, subject):
    super().__init__('hold_action', subject)

class NoActionEvent(NotMovingEvent):
  '''
  Response by characters to YourMoveEvent to indicate they have no action.
  '''
  def __init__(self, subject):
    super().__init__('no_action', subject)


class WoundCheckEvent(Event):
  '''
  Event for a character's wound check.

  The "subject" is the character making the wound check.
  The "attacker" is the character who inflicted the damage.
  The "damage" is the character's total Light Wounds for the
  wound check (including new damage as well as previous damage).
  The "tn" is the base TN for the wound check, which normally is
  the amount of damage.
  '''
  def __init__(self, name, subject, attacker, damage, tn=None):
    super().__init__(name)
    self.subject = subject
    self.attacker = attacker
    self.damage = damage
    if tn is None:
      self.tn = damage
    else:
      self.tn = tn

class WoundCheckDeclaredEvent(WoundCheckEvent):
  def __init__(self, subject, attacker, damage, tn=None, vp=0):
    super().__init__('wound_check_declared', subject, attacker, damage, tn=tn)
    self.vp = vp

class WoundCheckFailedEvent(WoundCheckEvent):
  def __init__(self, subject, attacker, damage, roll, tn=None):
    super().__init__('wound_check_failed', subject, attacker, damage, tn=tn)
    self.roll = roll

class WoundCheckRolledEvent(WoundCheckEvent):
  def __init__(self, subject, attacker, damage, roll, tn=None):
    super().__init__('wound_check_rolled', subject, attacker, damage, tn=tn)
    self.roll = roll

class WoundCheckSucceededEvent(WoundCheckEvent):
  def __init__(self, subject, attacker, damage, roll, tn=None):
    super().__init__('wound_check_succeeded', subject, attacker, damage, tn=tn)
    self.roll = roll

class KeepLightWoundsEvent(WoundCheckEvent):
  def __init__(self, subject, attacker, damage, tn=None):
    super().__init__('keep_lw', subject, attacker, damage, tn=tn)

class TakeSeriousWoundEvent(WoundCheckEvent):
  def __init__(self, subject, attacker, damage, tn=None):
    super().__init__('take_sw', subject, attacker, damage, tn=tn)


class GainResourcesEvent(Event):
  def __init__(self, name, subject, amount):
    super().__init__(name)
    self.subject = subject
    self.amount = amount

class GainTemporaryVoidPointsEvent(GainResourcesEvent):
  def __init__(self, subject, amount):
    super().__init__('gain_tvp', subject, amount)


class SpendActionEvent(Event):
  '''
  Event for when a character spends an action die.
  '''
  def __init__(self, subject, skill, initiative_action):
    super().__init__('spend_action')
    self.subject = subject
    self.skill = skill
    self.initiative_action = initiative_action


class SpendResourcesEvent(Event):
  '''
  Event for when a character spends resources that can be measured in an amount.

  The "subject" is the character spending resources.
  The "skill" is the skill the resources are being spent on.
  This may be something that is not really a skill, such as "wound check" or "damage".
  The "amount" is the amount of the resource being spent.
  '''
  def __init__(self, name, subject, skill, amount):
    super().__init__(name)
    self.subject = subject
    self.skill = skill
    self.amount = amount

class SpendAdventurePointsEvent(SpendResourcesEvent):
  def __init__(self, subject, skill, amount):
    super().__init__('spend_ap', subject, skill, amount)


class SpendVoidPointsEvent(SpendResourcesEvent):
  def __init__(self, subject, skill, amount):
    super().__init__('spend_vp', subject, skill, amount)

  
class SpendFloatingBonusEvent(Event):
  '''
  Event for when a character spends a floating bonus.
  Since floating bonuses are discrete and not measured in an "amount",
  they aren't a good fit for a SpendResourcesEvent.
  '''
  def __init__(self, subject,bonus):
    super().__init__('spend_floating_bonus')
    self.subject = subject
    self.bonus = bonus


class ModifierEvent(Event):
  '''
  Event for when a character is affected by a Modifier.
  '''
  def __init__(self, name, subject, modifier):
    super().__init__(name)
    self.subject = subject
    self.modifier = modifier

class AddModifierEvent(ModifierEvent):
  '''
  Event for when a character gains a modifier.
  '''
  def __init__(self, subject, modifier):
    super().__init__('add_modifier', subject, modifier)

class RemoveModifierEvent(ModifierEvent):
  '''
  Event for when a character loses a modifier.
  '''
  def __init__(self, subject, modifier):
    super().__init__('remove_modifier', subject, modifier)

