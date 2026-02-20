#!/usr/bin/env python3

#
# weapons.py
#
# Character weapons for the L7R combat simulator.
# Different weapons have different base damage.
#

from abc import ABC, abstractmethod

class Weapon(object):
  def __init__(self, name, rolled, kept):
    self._name = name
    self._rolled = rolled
    self._kept = kept

  def name(self):
    return self._name

  def kept(self):
    return self._kept

  def rolled(self):
    return self._rolled


CLUB = Weapon('club', 2, 2)

GONGFU = Weapon('gongfu', 0, 3)

KATANA = Weapon('katana', 4, 2)
SWORD = KATANA

TANTO = Weapon('tanto', 2, 2)
KNIFE = TANTO

UNARMED = Weapon('unarmed', 0, 2)

WAKIZASHI = Weapon('wakizashi', 3, 2)

YARI = Weapon('yari', 3, 2)
SPEAR = YARI

