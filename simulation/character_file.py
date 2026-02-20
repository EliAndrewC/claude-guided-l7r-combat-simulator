#!/usr/bin/env python3

#
# character_file.py
#
# Character file format for L7R combat simulator.
# Characters may be represented as a YAML file.
# YAML was selected because it is very human readable and human writable.
# If you wanted ASN.1 or XML instead, I'm not sorry.
#

import os
import yaml

from simulation.advantages import Advantage
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.disadvantages import Disadvantage
from simulation.professions import Profession
from simulation.school_factory import get_school
from simulation.skills import Skill
from simulation.strategy_factory import get_strategy


class CharacterReader(object):
  '''
  Read a Character from a YAML format file.
  Uses a CharacterBuilder to build the character. This will reject invalid characters,
  including characters that don't have enough XP for the indicated build.
  You can always give the character a large number of XP to avoid having to calculate
  the cost of the build!

  Character must have rings and skills.

  Characters may have a school, a profession, or neither.

  Name, xp, advantages, and disadvantages are optional.

  If no name is given, the character is assigned a random UUID for their name.
  If no xp is given, the character is assigned 100 xp.

  Here is an example character file. More examples are available in the data directory
  of this package.

  name: Kakita Haruo
  school: Courtier
  rings:
    air: 4
    earth: 3
    fire: 2
    void: 2
    water: 3
  skills:
    attack: 3
    culture: 3
    discern honor: 2
    etiquette: 3
    heraldry: 3
    law: 1
    parry: 4
    manipulation: 3
    oppose social: 3
    sincerity: 3
    tact: 5 
    worldliness: 5
  advantages:
    discerning
    genealogist
  disadvantages:
    permanent wound
    slow healer
  xp: 1000000
  '''
  def read(self, f):
    data = yaml.safe_load(f)
    xp = int(data.get('xp', 100))
    builder = CharacterBuilder().with_xp(xp)
    if 'name' in data.keys():
      builder.with_name(data['name']) 
    # take profession or school
    if 'school' in data.keys() and 'profession' in data.keys():
      raise IOError('Invalid Character (may not have both a profession and a school')
    elif 'profession' in data.keys():
      builder = builder.with_profession()
    elif 'school' in data.keys():
      school = get_school(data['school'])
      builder = builder.with_school(school)
    else:
      builder = builder.generic()
    # build character
    builder = self._take_disadvantages(data, builder)
    builder = self._take_advantages(data, builder)
    builder = self._buy_skills(data, builder)
    builder = self._buy_rings(data, builder)
    builder = self._set_strategies(data, builder)
    builder = self._take_abilities(data, builder)
    return builder.build()

  def _buy_rings(self, data, builder):
    # character must have rings
    if 'rings' not in data.keys():
      raise IOError('Invalid Character (no rings)')
    for (ring, rank) in data['rings'].items():
      builder.buy_ring(ring, rank)
    return builder

  def _buy_skills(self, data, builder):
    # character must have skills
    if 'skills' not in data.keys():
      raise IOError('Invalid Character (no skills)')
    # buy attack skill before other skills
    # this avoids getting ahead of parry
    if 'attack' in data['skills'].keys():
      rank = data['skills'].pop('attack')
      builder.buy_skill('attack', rank)
    # buy other skills
    for (skill, rank) in data['skills'].items():
      builder.buy_skill(skill, rank)
    return builder

  def _set_strategies(self, data, builder):
    # strategies are optional
    if 'strategies' in data.keys():
      for (event, strategy_name) in data['strategies'].items():
        strategy = get_strategy(strategy_name)
        builder.set_strategy(event, strategy)
    return builder

  def _take_abilities(self, data, builder):
    if 'abilities' in data.keys():
      abilityd = data['abilities']
      for name in abilityd.keys():
        if not isinstance(name, str):
          raise ValueError('Profession ability name must be str')
        level = int(abilityd[name])
        if level < 0 or level > 2:
          raise ValueError('Profession ability level requires 0 <= level <= 2')
        for i in range(level):
          builder.take_ability(name)
    return builder

  def _take_advantages(self, data, builder):
    # advantages are optional
    if 'advantages' in data.keys():
      for advantage in data['advantages']:
        builder.take_advantage(advantage.lower())
    return builder

  def _take_disadvantages(self, data, builder):
    # disadvantages are optional
    if 'disadvantages' in data.keys():
      for disadvantage in data['disadvantages']:
        builder.take_disadvantage(disadvantage.lower())
    return builder


class CharacterWriter(object):
  '''
  Writes a character to a YAML format file.
  '''
  def write(self, character, f):
    if character.profession():
      return ProfessionCharacterWriter().write(character, f)
    elif character.school():
      return SchoolCharacterWriter().write(character, f)
    else:
      return GenericCharacterWriter().write(character, f)


# TODO: handle Honor, Rank, and Recognition
# TODO: support overrides for strategies and listeners
class GenericCharacterWriter(CharacterWriter):
  '''
  CharacterWriter for characters without a samurai school or a peasant profession.
  '''
  def write(self, character, f):
    yaml.dump(self.build_data(character), f)

  def build_data(self, character):
    data = { 'rings': {}, 'skills': {}, 'advantages': [], 'disadvantages': [] }
    data['name'] = character.name()
    for (ring, rank) in character.rings().items():
      data['rings'][ring] = rank
    for (skill, rank) in character.skills().items():
      data['skills'][skill] = rank
    for advantage in character.advantages():
      data['advantages'].append(advantage)
    for disadvantage in character.disadvantages():
      data['disadvantages'].append(disadvantage)
    xp_cost = self.calculate_xp_cost(character)
    data['xp'] = xp_cost
    return data

  def calculate_ring_cost(self, character, ring, rank):
    if rank == 2:
      return 0
    elif rank > 5:
      raise ValueError('May not raise ring above 5')
    else:
      return sum([(5 * i) for i in range(3, rank + 1)])

  def calculate_skill_cost(self, character, skill, rank):
    return Skill(skill).get().cost(rank)

  def calculate_xp_cost(self, character):
    xp_cost = 0
    for (skill, rank) in character.skills().items():
      xp_cost += self.calculate_skill_cost(character, skill, rank)
    for (ring, rank) in character.rings().items():
      xp_cost += self.calculate_ring_cost(character, ring, rank)
    for advantage in character.advantages():
      xp_cost += Advantage(advantage).get().cost()
    for disadvantage in character.disadvantages():
      xp_cost += Disadvantage(disadvantage).get().cost()
    return xp_cost


class ProfessionCharacterWriter(GenericCharacterWriter):
  '''
  CharacterWriter for characters with a peasant profession.
  # TODO: support profession abilities
  '''
  def build_data(self, character):
    data = super().build_data(character)
    data['profession'] = character.profession().name()
    return data


class SchoolCharacterWriter(GenericCharacterWriter):
  '''
  CharacterWriter for samurai characters.
  '''
  def build_data(self, character):
    data = super().build_data(character)
    data['school'] = character.school().name()
    return data

  def calculate_skill_cost(self, character, skill, rank):
    original_rank = 0
    if skill in ('attack', 'parry'):
      original_rank = 1
    elif skill in character.school().school_knacks():
      original_rank = 1
    return Skill(skill).get().cost(rank, original_rank)

  def calculate_ring_cost(self, character, ring, rank):
    original_rank = 2
    discount = 0
    if ring == character.school().school_ring():
      original_rank = 3
    else:
      if rank > 5:
        raise ValueError('May not raise {} above 5'.format(ring))
    if self.school_rank(character) >= 4 and ring == character.school().school_ring():
      original_rank = 4
      discount = 5
    return max(sum([(5 * i) - discount for i in range(original_rank + 1, rank + 1)]), 0)

  def school_rank(self, character):
    return min([character.skill(skill) for skill in character.school().school_knacks()])

