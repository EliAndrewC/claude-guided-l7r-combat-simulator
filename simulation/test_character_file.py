#!/usr/bin/env python3

#
# test_character_file.py
#
# Unit tests for L7R combat simulator character file IO module
#

import io
import os
import unittest

from simulation import professions
from simulation.akodo_school import AkodoBushiSchool
from simulation.bayushi_school import BayushiBushiSchool
from simulation.character import Character
from simulation.character_file import CharacterReader, CharacterWriter, GenericCharacterWriter, SchoolCharacterWriter

script_path = os.path.realpath(__file__)
script_dirpath = os.path.split(script_path)[0]


class TestCharacterReader(unittest.TestCase):
  def test_read_akodo(self):
    character = None
    path = os.path.join(script_dirpath, 'data/akodo.yaml')
    with open(path, 'r') as f:
      character = CharacterReader().read(f)
    # name
    self.assertEqual('Akodo', character.name())
    # assert expected rings
    self.assertEqual(3, character.ring('air'))
    self.assertEqual(5, character.ring('earth'))
    self.assertEqual(5, character.ring('fire'))
    self.assertEqual(6, character.ring('water'))
    self.assertEqual(5, character.ring('void'))
    # assert expected skills
    self.assertEqual(4, character.skill('attack'))
    self.assertEqual(5, character.skill('double attack'))
    self.assertEqual(5, character.skill('feint'))
    self.assertEqual(5, character.skill('iaijutsu'))
    self.assertEqual(5, character.skill('parry'))
    # assert expected school
    self.assertTrue(isinstance(character.school(), AkodoBushiSchool))

  def test_read_bayushi(self):
    character = None
    path = os.path.join(script_dirpath, 'data/bayushi.yaml')
    with open(path, 'r') as f:
      character = CharacterReader().read(f)
    # name
    self.assertEqual('Bayushi', character.name())
    # assert expected rings
    self.assertEqual(3, character.ring('air'))
    self.assertEqual(5, character.ring('earth'))
    self.assertEqual(6, character.ring('fire'))
    self.assertEqual(5, character.ring('water'))
    self.assertEqual(5, character.ring('void'))
    # assert expected skills
    self.assertEqual(4, character.skill('attack'))
    self.assertEqual(5, character.skill('double attack'))
    self.assertEqual(5, character.skill('feint'))
    self.assertEqual(5, character.skill('iaijutsu'))
    self.assertEqual(5, character.skill('parry'))
    # assert expected school
    self.assertTrue(isinstance(character.school(), BayushiBushiSchool))

  def test_read_mighty_kyoude(self):
    character = None
    path = os.path.join(script_dirpath, 'data/mighty_kyoude.yaml')
    with open(path, 'r') as f:
      character = CharacterReader().read(f)
    # name
    self.assertEqual('Mighty Kyō\'ude', character.name())
    # assert expected rings
    self.assertEqual(3, character.ring('air'))
    self.assertEqual(5, character.ring('earth'))
    self.assertEqual(5, character.ring('fire'))
    self.assertEqual(5, character.ring('water'))
    self.assertEqual(5, character.ring('void'))
    # assert expected skills
    self.assertEqual(5, character.skill('attack'))
    self.assertEqual(5, character.skill('parry'))
    # assert expected abilities
    self.assertEqual(2, character.profession().ability(professions.CRIPPLED_BONUS))
    self.assertEqual(2, character.profession().ability(professions.FAILED_PARRY_DAMAGE_BONUS))
    self.assertEqual(2, character.profession().ability(professions.INITIATIVE_BONUS))
    self.assertEqual(2, character.profession().ability(professions.MISSED_ATTACK_BONUS))
    self.assertEqual(2, character.profession().ability(professions.PARRY_PENALTY))
    self.assertEqual(2, character.profession().ability(professions.ROLLED_DAMAGE_BONUS))
    self.assertEqual(2, character.profession().ability(professions.WEAPON_DAMAGE_BONUS))
    self.assertEqual(2, character.profession().ability(professions.WOUND_CHECK_BONUS))


class TestGenericCharacterWriter(unittest.TestCase):
  def test_calculate_ring_cost(self):
    character = Character()
    writer = GenericCharacterWriter()
    self.assertEqual(0, writer.calculate_ring_cost(character, 'earth', 2))
    self.assertEqual(15, writer.calculate_ring_cost(character, 'earth', 3))
    self.assertEqual(35, writer.calculate_ring_cost(character, 'earth', 4))
    self.assertEqual(60, writer.calculate_ring_cost(character, 'earth', 5))
    with self.assertRaises(ValueError):
      writer.calculate_ring_cost(character, 'earth', 6)

  def test_calculate_advanced_skill_cost(self):
    character = Character()
    writer = GenericCharacterWriter()
    self.assertEqual(0, writer.calculate_skill_cost(character, 'attack', 0))
    self.assertEqual(4, writer.calculate_skill_cost(character, 'attack', 1))
    self.assertEqual(8, writer.calculate_skill_cost(character, 'attack', 2))
    self.assertEqual(14, writer.calculate_skill_cost(character, 'attack', 3))
    self.assertEqual(22, writer.calculate_skill_cost(character, 'attack', 4))
    self.assertEqual(32, writer.calculate_skill_cost(character, 'attack', 5))
    with self.assertRaises(ValueError):
      writer.calculate_skill_cost(character, 'attack', 6)
    
  def test_calculate_basic_skill_cost(self):
    character = Character()
    writer = GenericCharacterWriter()
    self.assertEqual(0, writer.calculate_skill_cost(character, 'sincerity', 0))
    self.assertEqual(2, writer.calculate_skill_cost(character, 'sincerity', 1))
    self.assertEqual(4, writer.calculate_skill_cost(character, 'sincerity', 2))
    self.assertEqual(7, writer.calculate_skill_cost(character, 'sincerity', 3))
    self.assertEqual(10, writer.calculate_skill_cost(character, 'sincerity', 4))
    self.assertEqual(13, writer.calculate_skill_cost(character, 'sincerity', 5))
    with self.assertRaises(ValueError):
      writer.calculate_skill_cost(character, 'sincerity', 6)


class TestSchoolCharacterWriter(unittest.TestCase):
  def test_calculate_ring_cost(self):
    character = Character()
    school = AkodoBushiSchool()
    character.set_school(school)
    school.apply_school_ring(character)
    writer = SchoolCharacterWriter()
    # non school ring costs are normal
    self.assertEqual(0, writer.calculate_ring_cost(character, 'earth', 2))
    self.assertEqual(15, writer.calculate_ring_cost(character, 'earth', 3))
    self.assertEqual(35, writer.calculate_ring_cost(character, 'earth', 4))
    self.assertEqual(60, writer.calculate_ring_cost(character, 'earth', 5))
    with self.assertRaises(ValueError):
      writer.calculate_ring_cost(character, 'earth', 6)
    # school ring starts at 3
    self.assertEqual(0, writer.calculate_ring_cost(character, 'water', 2))
    self.assertEqual(0, writer.calculate_ring_cost(character, 'water', 3))
    self.assertEqual(20, writer.calculate_ring_cost(character, 'water', 4))
    self.assertEqual(45, writer.calculate_ring_cost(character, 'water', 5))
    self.assertEqual(75, writer.calculate_ring_cost(character, 'water', 6))
    # if 4th dan, school ring is boosted and discounted
    for skill in school.school_knacks():
      character.set_skill(skill, 4)
    school.apply_rank_four_ability(character)
    self.assertEqual(0, writer.calculate_ring_cost(character, 'water', 2))
    self.assertEqual(0, writer.calculate_ring_cost(character, 'water', 3))
    self.assertEqual(0, writer.calculate_ring_cost(character, 'water', 4))
    self.assertEqual(20, writer.calculate_ring_cost(character, 'water', 5))
    self.assertEqual(45, writer.calculate_ring_cost(character, 'water', 6))
    
  def test_write_akodo(self):
    character = Character('Akodo')
    character.set_ring('air', 3)
    character.set_ring('earth', 5)
    character.set_ring('fire', 5)
    character.set_ring('water', 6)
    character.set_ring('void', 5)
    character.set_skill('attack', 4)
    character.set_skill('double attack', 5)
    character.set_skill('feint', 5)
    character.set_skill('iaijutsu', 5)
    character.set_skill('parry', 5)
    character.set_school(AkodoBushiSchool())
    f = io.StringIO()
    CharacterWriter().write(character, f)
    expected = '''advantages: []
disadvantages: []
name: Akodo
rings:
  air: 3
  earth: 5
  fire: 5
  void: 5
  water: 6
school: Akodo Bushi School
skills:
  attack: 4
  double attack: 5
  feint: 5
  iaijutsu: 5
  parry: 5
xp: 370
'''
    self.assertEqual(expected, f.getvalue())

