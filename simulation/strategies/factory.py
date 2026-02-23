#!/usr/bin/env python3

#
# strategy_factory.py
#
# Factory to get strategies by name.
# This is a convenience provided to the character builder.
#

from simulation.schools.kakita_school import (
    KakitaAttackStrategy,
    KakitaAttackStrategy05,
    KakitaInterruptAttackStrategy,
    KakitaInterruptAttackStrategy05,
    KakitaNoVPAttackStrategy,
    KakitaNoVPInterruptAttackStrategy,
    KakitaParryStrategy,
)
from simulation.strategies import base as strategies


def get_strategy(name):
    if name == "AlwaysAttackActionStrategy":
        return strategies.AlwaysAttackActionStrategy()
    if name == "AlwaysKeepLightWoundsStrategy":
        return strategies.AlwaysKeepLightWoundsStrategy()
    if name == "AlwaysParryStrategy":
        return strategies.AlwaysParryStrategy()
    if name == "HoldOneActionStrategy":
        return strategies.HoldOneActionStrategy()
    if name == "KakitaAttackStrategy":
        return KakitaAttackStrategy()
    if name == "KakitaAttackStrategy05":
        return KakitaAttackStrategy05()
    if name == "KakitaInterruptAttackStrategy":
        return KakitaInterruptAttackStrategy()
    if name == "KakitaInterruptAttackStrategy05":
        return KakitaInterruptAttackStrategy05()
    if name == "KakitaNoVPAttackStrategy":
        return KakitaNoVPAttackStrategy()
    if name == "KakitaNoVPInterruptAttackStrategy":
        return KakitaNoVPInterruptAttackStrategy()
    if name == "KakitaParryStrategy":
        return KakitaParryStrategy()
    if name == "KeepLightWoundsStrategy":
        return strategies.KeepLightWoundsStrategy()
    if name == "NeverKeepLightWoundsStrategy":
        return strategies.NeverKeepLightWoundsStrategy()
    if name == "NeverParryStrategy":
        return strategies.NeverParryStrategy()
    if name == "PlainAttackStrategy":
        return strategies.PlainAttackStrategy()
    if name == "ReluctantParryStrategy":
        return strategies.ReluctantParryStrategy()
    elif name == "StingyPlainAttackStrategy":
        return strategies.StingyPlainAttackStrategy()
    elif name == "StingyWoundCheckStrategy":
        return strategies.StingyWoundCheckStrategy()
    elif name == "UniversalAttackStrategy":
        return strategies.UniversalAttackStrategy()
    elif name == "WoundCheckStrategy":
        return strategies.WoundCheckStrategy()
    elif name == "WoundCheckStrategy02":
        return strategies.WoundCheckStrategy02()
    elif name == "WoundCheckStrategy05":
        return strategies.WoundCheckStrategy05()
    elif name == "WoundCheckStrategy04":
        return strategies.WoundCheckStrategy04()
    elif name == "WoundCheckStrategy08":
        return strategies.WoundCheckStrategy08()
    else:
        raise ValueError(f"Invalid strategy: {name}")
