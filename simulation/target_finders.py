#!/usr/bin/env python3

#
# target_finders.py
#
# Classes to select targets for abilities and attack actions.
#

from simulation.knowledge import TheoreticalCharacter


class TargetFinder(object):
  '''
  Utility class to identify targets to attack.
  '''
  def find_enemies(self, subject, context):
    '''
    find_enemies(subject, context) -> list of Character
      subject (Character): character who is making a list of enemies
      context (EngineContext): context

    Returns a list of the characters who are still fighting
    who are enemies of the subject.
    '''
    enemies = []
    for other_character in context.characters():
      if other_character not in subject.group():
        if other_character.is_fighting():
          enemies.append(other_character)
    return enemies

  def find_easiest_target(self, subject, skill, initiative_action, context):
    '''
    find_easiest_target(subject, skill, initiative_action, context) -> Character
      subject (Character): character who would be attacking
      skill (str): skill the subject will use to attack
      initiative_action (InitiativeAction): initiative action being used to attack
      context (EngineContext): context

    Returns the enemy where the subject has the best chance
    of attacking successfully with the given skill.
    '''
    targets = []
    explode = not subject.crippled()
    for other_character in self.find_enemies(subject, context):
      # can I hit this character with this skill?
      proxy_target = TheoreticalCharacter(subject.knowledge(), other_character)
      action = subject.action_factory() \
        .get_attack_action(subject, proxy_target, skill, initiative_action, context)
      (rolled, kept, modifier) = subject.get_skill_roll_params(other_character, skill)
      p_hit = context.p(action.tn() - modifier, rolled, kept, explode=explode)
      targets.append((other_character, p_hit))
    # sort targets in order of probability of hitting
    targets.sort(key=lambda t: t[1], reverse=True)
    # return the easiest target to hit
    if len(targets) > 0:
      return targets[0][0]
    else:
      return None

  def find_most_dangerous_target(self, subject, skill, initiative_action, context):
    '''
    find_most_dangerous_target(subject, skill, initiative_action, context) -> Character
      subject (Character): character who would be attacking
      skill (str): skill the subject will use to attack
      initiative_action (InitiativeAction): initiative action being used to attack
      context (EngineContext): context

    Returns the enemy who has inflicted the most damage.
    '''
    targets = [c for c in self.find_enemies(subject, context)]
    targets.sort(key=lambda x: self.subject.knowledge().average_damage_roll(x), reverse=True)
    if len(targets) > 0:
      return targets[0]
    else:
      return None

  def find_most_wounded_target(self, subject, skill, initiative_action, context):
    '''
    find_most_wounded_target(subject, skill, context) -> Character
      subject (Character): character who would be attacking
      skill (str): skill the subject will use to attack
      initiative_action (InitiativeAction): initiative action being used to attack
      context (EngineContext): context

    Returns the enemy who is carrying the most Serious Wounds.
    '''
    targets = [c for c in self.find_enemies(subject, context)]
    targets.sort(key=lambda x: subject.knowledge().lw(x), reverse=True)
    targets.sort(key=lambda x: subject.knowledge().wounds(x), reverse=True)
    if len(targets) > 0:
      return targets[0]
    else:
      return None


class EasiestTargetFinder(TargetFinder):
  def find_target(self, subject, skill, initiative_action, context):
    return self.find_easiest_target(subject, skill, initiative_action, context)


class FinishHimTargetFinder(TargetFinder):
  def find_target(self, subject, skill, initiative_action, context):
    return self.find_most_wounded_target(subject, skill, initiative_action, context)


class MostDangerousTargetFinder(TargetFinder):
  def find_target(self, subject, skill, initiative_action, context):
    return self.find_most_dangerous_target(subject, skill, initiative_action, context)

