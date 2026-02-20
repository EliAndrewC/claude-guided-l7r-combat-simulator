
class Knowledge(object):
  '''
  Store and return information based on observations of the capabilities and status of other characters.
  Does not make decisions with the knowledge - it only stores and returns observations.
  Strategy classes should use the information from a character or group's Knowledge to help make decisions.
  '''
  def __init__(self):
    self._actions_per_round = {}
    self._actions_this_round = {}
    self._attack_rolls = {}
    self._damage_rolls = {}
    self._modifiers = {}
    self._parry_rolls = {}
    self._rings = {}
    self._skills = {}
    self._tn_to_hit = {}
    self._wounds = {}

  def actions_per_round(self, character):
    '''
    actions_per_round(character) -> int
      character (Character): character of interest

    Returns the number of actions per round a character is believed to have.
    '''
    return self._actions_per_round.get(character.name(), 2)

  def actions_remaining(self, character):
    '''
    actions_remaining(character) -> int
      character (Character): character of interest

    Returns the number of actions believed to be remaining this round for a character.
    '''
    return max(0, self.actions_per_round(character) - self.actions_taken(character))

  def actions_taken(self, character):
    '''
    actions_taken(character) -> int
      character (Character): character of interest

    Return the number of actions taken this round by a character.
    '''
    return self._actions_this_round.get(character.name(), 0)

  def average_attack_roll(self, character):
    '''
    average_attack_roll(character) -> int
      character (Character): character of interest

    Return the average attack roll this character can do according to past observations.
    '''
    name = character.name()
    if name in self._attack_rolls.keys():
      return int(sum(self._attack_rolls[name]) / len(self._attack_rolls[name]))
    else:
      # Most characters will roll at least 8k3 attack, which averages 27
      return 27

  def average_damage_roll(self, character):
    '''
    average_damage_roll(character) -> int
      character (Character): character of interest

    Return the average damage roll this character will get according to past observations.
    '''
    name = character.name()
    if name in self._damage_rolls.keys():
      return int(sum(self._damage_rolls[name]) / len(self._damage_rolls[name]))
    else:
      # Most characters will roll at least 7k2 for damage, which averages 18
      return 18

  def clear(self):
    self._actions_per_round.clear()
    self._actions_this_round.clear()
    self._attack_rolls.clear()
    self._damage_rolls.clear()
    self._modifiers.clear()
    self._parry_rolls.clear()
    self._rings.clear()
    self._skills.clear()
    self._tn_to_hit.clear()
    self._wounds.clear()

  def end_of_round(self):
    '''
    end_of_round()

    Observe the end of the round. Resets any per round state and makes summary observations where necessary.
    This should be called on a character or group's knowledge when an EndOfRoundEvent is observed.
    '''
    for name, n in self._actions_this_round.items():
      prev_n = self._actions_per_round.get(name, 0)
      self._actions_per_round[name] = max(prev_n, n)
      self._actions_this_round[name] = 0

  def lw(self, character):
    '''
    lw(character) -> int

    Returns knowledge of a character's Light Wound total.
    This implementation gives all characters perfect knowledge of others' LW total.
    '''
    return character.lw()

  def modifier(self, character, target, skill):
    '''
    modifier(character, target, skill) -> int

    Returns the modifier penalty applied to some character for
    a skill or other thing (such as 'tn to be hit').
    '''
    name = character.name()
    if name in self._modifiers.keys():
      return sum([m.apply(target, skill) for m in self._modifiers[name]])
    else:
      return 0

  def observe_action(self, character):
    '''
    observe_action(character)
    
    Observe that a character has taken an action.
    '''
    name = character.name()
    # update actions this round for this character
    if name in self._actions_this_round.keys():
      self._actions_this_round[name] += 1
    else:
      self._actions_this_round[name] = 1
    # update actions per round for this character if necessary
    if name not in self._actions_per_round.keys():
      self._actions_per_round[name] = self._actions_this_round[name]
    else:
      if self._actions_this_round[name] > self._actions_per_round[name]:
        self._actions_per_round[name] = self._actions_this_round[name]

  def observe_attack_roll(self, character, roll):
    '''
    observe_attack_roll(character, roll)
      character (Character): character who made the attack
      roll (int): the attack roll
    
    Observe an attack roll by a character.
    '''
    name = character.name()
    if name in self._attack_rolls.keys():
      self._attack_rolls[name].append(roll)
    else:
      self._attack_rolls[name] = [roll]

  def observe_damage_roll(self, character, damage):
    '''
    observe_damage_roll(character, roll)
      character (Character): character who dealt the damage
      damage (int): damage roll
    
    Observe a damage roll by a character.
    '''
    name = character.name()
    if name in self._damage_rolls.keys():
      self._damage_rolls[name].append(damage)
    else:
      self._damage_rolls[name] = [damage]

  def observe_modifier_added(self, character, modifier):
    '''
    observe_modifier_added(character, modifier)
      character (Character): character receiving the modifier
      modifier (Modifier): modifier being added to character

    Observe a character getting an expiring modifier.
    '''
    name = character.name()
    if name not in self._modifiers.keys():
      self._modifiers[name] = [modifier]
    else:
      self._modifiers[name].append(modifier)

  def observe_modifier_removed(self, character, modifier):
    '''
    observe_modifier_removed(character, modifier)
      character (Character): character losing the modifier
      modifier (Modifier): modifier being removed from the character

    Observe a modifier being removed from a character.
    '''
    self._modifiers[character.name()].remove(modifier)

  def observe_ring(self, character, ring, rank):
    '''
    observe_ring(character, ring, rank)
      character (Character): character of interest
      ring (str): name of a ring being observed
      rank (int): observed rank of the ring

    Observe that a character's named ring is at the given rank.
    '''
    name = character.name()
    if not isinstance(ring, str):
      raise ValueError('observe_ring ring must be str')
    if not isinstance(rank, int):
      raise ValueError('observe_ring rank must be int')
    if name not in self._rings.keys():
      self._rings[name] = {}
    self._rings[name][ring] = rank

  def observe_skill(self, character, skill, rank):
    '''
    observe_skill(character, skill, rank)
      character (Character): character of interest
      skill (str): name of a skill being observed
      rank (int): observed rank of the skill

    Observe that a character's named skill is at the given rank.
    '''
    name = character.name()
    if not isinstance(skill, str):
      raise ValueError('observe_skill skill must be str')
    if not isinstance(rank, int):
      raise ValueError('observe_skill rank must be int')
    if name not in self._skills.keys():
      self._skills[name] = {}
    self._skills[name][skill] = rank

  def observe_tn_to_hit(self, character, tn):
    '''
    observe_tn_to_hit(character, tn)
      character (Character): character of interest
      tn (int): TN to hit a character with an attack
    
    Observe a character's TN to be hit.
    '''
    name = character.name()
    adjustment = self.modifier(character, None, 'tn to hit')
    if name not in self._tn_to_hit.keys():
      self._tn_to_hit[name] = tn - adjustment

  def observe_wounds(self, character, damage):
    '''
    observe_wounds(character, damage)
      character (Character): character of interest
      damage (int): number of Serious Wounds taken by the character
   
    Observe Serious Wounds taken by a character.
    '''
    name = character.name()
    if name in self._wounds.keys():
      self._wounds[name] += damage
    else:
      self._wounds[name] = damage

  def sw(self, character):
    '''
    sw(character) -> int

    Returns knowledge of a character's Serious Wounds taken.
    This implementation gives all characters perfect knowledge of others' SW.
    '''
    return character.sw()

  def tn_to_hit(self, target):
    '''
    tn_to_hit(target) -> int
      target (Character): character of interest
    
    Return the best known TN to hit a character.
    '''
    return self._tn_to_hit.get(target.name(), 20)

  def weapon(self, character):
    return character.weapon()

  def wounds(self, character):
    '''
    wounds(character) -> int
      character (Character): character of interest
    
    Return the number of Serious Wounds a character has taken (according to observations).
    '''
    return self._wounds.get(character.name(), 0)


class TheoreticalCharacter(object):
  '''
  A partial implementation of the Character API that uses knowledge of a character.
  Used when speculating about the character as a target of attacks, parries, etc, in strategy classes.
  '''
  def __init__(self, knowledge, character):
    self._knowledge = knowledge
    self._character = character

  def actions(self):
    return self._character.actions()

  def lw(self):
    return self._character.lw()

  def ring(self, ring):
    # TODO: figure out how to estimate rings
    return 3

  def sw(self):
    return self._character.sw()

  def tn_to_hit(self):
    return self._knowledge.tn_to_hit(self._character) + self._knowledge.modifier(self._character, None, 'tn to hit')

  def weapon(self):
    return self_knowledge.weapon(self._character)

