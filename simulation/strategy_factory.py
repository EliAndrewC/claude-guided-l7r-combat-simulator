#!/usr/bin/env python3

#
# strategy_factory.py
#
# Factory to get strategies by name.
# This is a convenience provided to the character builder.
#

from simulation import strategies

def get_strategy(name):
  if name == 'AlwaysAttackActionStrategy':
    return strategies.AlwaysAttackActionStrategy()
  if name == 'AlwaysKeepLightWoundsStrategy':
    return strategies.AlwaysKeepLightWoundsStrategy()
  if name == 'AlwaysParryStrategy':
    return strategies.AlwaysParryStrategy()
  if name == 'HoldOneActionStrategy':
    return strategies.HoldOneActionStrategy()
  if name == 'KeepLightWoundsStrategy':
    return strategies.KeepLightWoundsStrategy()
  if name == 'NeverKeepLightWoundsStrategy':
    return strategies.NeverKeepLightWoundsStrategy()
  if name == 'NeverParryStrategy':
    return strategies.NeverParryStrategy()
  if name == 'PlainAttackStrategy':
    return strategies.PlainAttackStrategy()
  if name == 'ReluctantParryStrategy':
    return strategies.ReluctantParryStrategy()
  elif name == 'StingyPlainAttackStrategy':
    return strategies.StingyPlainAttackStrategy()
  elif name == 'StingyWoundCheckStrategy':
    return strategies.StingyWoundCheckStrategy()
  elif name == 'UniversalAttackStrategy':
    return strategies.UniversalAttackStrategy()
  elif name == 'WoundCheckStrategy':
    return strategies.WoundCheckStrategy()
  else: 
    raise ValueError('Invalid strategy: {}'.format(name))

