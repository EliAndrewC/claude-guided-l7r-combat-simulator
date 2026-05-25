#!/usr/bin/env python3

#
# character.py
#
# Class to represent a character in L7R combat simulations.
#

import math
import uuid
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from simulation import events, listeners
from simulation.log import logger
from simulation.mechanics.knowledge import Knowledge
from simulation.mechanics.modifiers import FreeRaise
from simulation.mechanics.roll_params import DEFAULT_ROLL_PARAMETER_PROVIDER, RollParameterProvider
from simulation.mechanics.roll_provider import DEFAULT_ROLL_PROVIDER, RollProvider
from simulation.mechanics.void_point_manager import VoidPointManager
from simulation.mechanics.weapons import KATANA, Weapon
from simulation.optimizers.attack_optimizer_factory import DEFAULT_ATTACK_OPTIMIZER_FACTORY, AttackOptimizerFactory
from simulation.optimizers.wound_check_optimizer_factory import DEFAULT_WOUND_CHECK_OPTIMIZER_FACTORY, WoundCheckOptimizerFactory
from simulation.optimizers.wound_check_provider import DEFAULT_WOUND_CHECK_PROVIDER, WoundCheckProvider
from simulation.professions import Profession
from simulation.schools import kakita_school
from simulation.schools.base import School
from simulation.strategies import base as strategies
from simulation.strategies.action_factory import DEFAULT_ACTION_FACTORY, ActionFactory
from simulation.strategies.base import Strategy
from simulation.strategies.take_action_event_factory import DEFAULT_TAKE_ACTION_EVENT_FACTORY, TakeActionEventFactory
from simulation.strategies.target_finders import EasiestTargetFinder

if TYPE_CHECKING:
    from simulation.groups import Group

RING_NAMES = ["air", "earth", "fire", "water", "void"]


class Character:
    def __init__(self, name: str | None = None, xp: int = 0) -> None:
        # initialize a character ID
        self._character_id = uuid.uuid4().hex
        # initialize name
        if name is None:
            self._name = self._character_id
        elif not isinstance(name, str):
            raise ValueError("Character name must be str")
        else:
            self._name = name
        # initialize xp
        self._xp = xp
        # initialize rings
        self._rings: dict[str, int] = {"air": 2, "earth": 2, "fire": 2, "void": 2, "water": 2}
        # everything else
        self._actions: list[int] = []
        self._action_factory: ActionFactory = DEFAULT_ACTION_FACTORY
        self._attack_rolled_penalty = 0
        self._advantages: list[str] = []
        self._ap_base_skill: str | None = None
        self._ap_multiplier = 2
        self._ap_skills: list[str] = []
        self._ap_spent = 0
        self._attack_optimizer_factory: AttackOptimizerFactory = DEFAULT_ATTACK_OPTIMIZER_FACTORY
        self._conviction_spent = 0
        self._damage_reroll_reduction = 0
        self._disadvantages: list[str] = []
        self._discounts: dict[str, int] = {}
        self._extra_kept: dict[str, int] = {}
        self._extra_rolled: dict[str, int] = {}
        self._floating_bonuses: list[Any] = []
        self._group: Group | None = None
        self._interrupt_skills = ["counterattack", "parry"]
        self._interrupt_costs: dict[str, int] = {}
        self._knowledge = Knowledge()
        self._modifiers: list[Any] = []
        # default listeners
        action_taken_listener = listeners.TakeActionListener()
        self._listeners: dict[str, listeners.Listener] = {
            "add_modifier": listeners.AddModifierListener(),
            "attack_declared": listeners.AttackDeclaredListener(),
            "attack_rolled": listeners.AttackRolledListener(),
            "contested_iaijutsu_attack_declared": kakita_school.ContestedIaijutsuAttackDeclaredListener(),
            "gain_tvp": listeners.GainTemporaryVoidPointsListener(),
            "lw_damage": listeners.LightWoundsDamageListener(),
            "new_round": listeners.NewRoundListener(),
            "remove_modifier": listeners.RemoveModifierListener(),
            "spend_action": listeners.SpendActionListener(),
            "spend_ap": listeners.SpendAdventurePointsListener(),
            "spend_conviction": listeners.SpendConvictionListener(),
            "spend_floating_bonus": listeners.SpendFloatingBonusListener(),
            "spend_vp": listeners.SpendVoidPointsListener(),
            "sw_damage": listeners.SeriousWoundsDamageListener(),
            "take_attack": action_taken_listener,
            "take_counterattack": action_taken_listener,
            "take_parry": action_taken_listener,
            "take_sw": listeners.TakeSeriousWoundListener(),
            "wound_check_declared": listeners.WoundCheckDeclaredListener(),
            "wound_check_failed": listeners.WoundCheckFailedListener(),
            "wound_check_rolled": listeners.WoundCheckRolledListener(),
            "wound_check_succeeded": listeners.WoundCheckSucceededListener(),
            "your_move": listeners.YourMoveListener(),
        }
        self._lw = 0
        self._lw_history: list[int] = []
        self._max_vp_provider: Any = None
        self._profession: Profession | None = None
        self._roll_parameter_provider: RollParameterProvider = DEFAULT_ROLL_PARAMETER_PROVIDER
        self._roll_provider: RollProvider = DEFAULT_ROLL_PROVIDER
        self._school: School | None = None
        self._skills: dict[str, int] = {"attack": 1, "parry": 1}
        self._skill_rings: dict[str, str] = {"attack": "fire", "counterattack": "fire", "damage": "fire", "double attack": "fire", "feint": "fire", "iaijutsu": "fire", "initiative": "void", "lunge": "fire", "parry": "air", "wound check": "water"}
        # default strategies (values may be a Strategy or a Listener-backed strategy)
        self._strategies: dict[str, Any] = {
            "action": strategies.HoldOneActionStrategy(),
            "attack": strategies.UniversalAttackStrategy(),
            "attack_rolled": strategies.AttackRolledStrategy(),
            "contested_iaijutsu_attack_declared": kakita_school.ContestedIaijutsuAttackDeclaredStrategy(),
            "duel_focus_or_strike": None,
            "interrupt": strategies.DefaultInterruptStrategy(),
            "light_wounds": strategies.KeepLightWoundsStrategy(),
            "parry": strategies.ReluctantParryStrategy(),
            "parry_rolled": strategies.ParryRolledStrategy(),
            "wound_check": strategies.WoundCheckStrategy(),
            "wound_check_rolled": strategies.WoundCheckRolledStrategy(),
        }
        self._sw = 0
        self._take_action_event_factory: TakeActionEventFactory = DEFAULT_TAKE_ACTION_EVENT_FACTORY
        self._target_finder = EasiestTargetFinder()
        self._tvp = 0
        self._vp_spent = 0
        self._weapon: Weapon = KATANA
        self._wound_check_optimizer_factory: WoundCheckOptimizerFactory = DEFAULT_WOUND_CHECK_OPTIMIZER_FACTORY
        self._wound_check_provider: WoundCheckProvider = DEFAULT_WOUND_CHECK_PROVIDER
        self._void_point_manager = VoidPointManager(self)

    def actions(self) -> list[int]:
        return self._actions

    def action_factory(self) -> ActionFactory:
        return self._action_factory

    def action_strategy(self) -> Any:
        return self._strategies["action"]

    def add_discount(self, item: str, discount: int) -> None:
        if item in self._discounts:
            self._discounts[item] += discount
        else:
            self._discounts[item] = discount

    def add_interrupt_skill(self, skill: str) -> None:
        if not isinstance(skill, str):
            raise ValueError("add_interrupt_skill skill argument must be str")
        if skill not in self._interrupt_skills:
            self._interrupt_skills.append(skill)

    def add_modifier(self, modifier: Any) -> None:
        # TODO: register modifier listeners
        self._modifiers.append(modifier)

    def advantages(self) -> list[str]:
        return self._advantages

    def ap(self) -> int:
        base = self.ap_base_skill()
        if base is None:
            return 0
        return (self._ap_multiplier * self.skill(base)) - self._ap_spent

    def ap_base_skill(self) -> str | None:
        return self._ap_base_skill

    def attack_optimizer_factory(self) -> AttackOptimizerFactory:
        return self._attack_optimizer_factory

    def attack_rolled_penalty(self) -> int:
        return self._attack_rolled_penalty

    def attack_rolled_strategy(self) -> Any:
        return self._strategies["attack_rolled"]

    def attack_strategy(self) -> Any:
        return self._strategies["attack"]

    def can_spend_ap(self, skill: str) -> bool:
        return skill in self._ap_skills

    def character_id(self) -> str:
        return self._character_id

    def conviction(self) -> int:
        return (2 * self.skill("conviction")) - self._conviction_spent

    def max_conviction_per_roll(self) -> int:
        return self.skill("conviction")

    def contested_iaijutsu_attack_declared_strategy(self) -> Any:
        return self._strategies["contested_iaijutsu_attack_declared"]

    def duel_focus_or_strike_strategy(self) -> Any:
        return self._strategies["duel_focus_or_strike"]

    def damage_reroll_reduction(self) -> int:
        return self._damage_reroll_reduction

    def crippled(self) -> bool:
        return self.sw() >= self.ring("earth")

    def disadvantages(self) -> list[str]:
        return self._disadvantages

    def event(self, event: events.Event, context: Any) -> Iterator[events.Event]:
        if event.name in self._listeners.keys():
            logger.debug(f"{self._name} handling {event.name}")
            # play event on modifiers first
            for modifier in self._modifiers:
                yield from modifier.handle(self, event, context)
            # then play event on self
            yield from self._listeners[event.name].handle(self, event, context)
        else:
            logger.debug(f"{self._name} ignoring {event.name}")

    def extra_kept(self, skill: str) -> int:
        return self._extra_kept.get(skill, 0)

    def extra_rolled(self, skill: str) -> int:
        return self._extra_rolled.get(skill, 0)

    def floating_bonuses(self, skill: str) -> list[Any]:
        return [bonus for bonus in self._floating_bonuses if bonus.is_applicable(skill)]

    def friends(self) -> Any:
        return self.group()

    def gain_action(self, phase: int) -> None:
        if not isinstance(phase, int):
            raise ValueError("gain_action phase must be int")
        self._actions.append(phase)
        self._actions.sort()

    def gain_floating_bonus(self, floating_bonus: Any) -> None:
        self._floating_bonuses.append(floating_bonus)

    def gain_tvp(self, n: int = 1) -> None:
        self._tvp += n

    def get_damage_roll_params(self, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> Any:
        return self.roll_parameter_provider().get_damage_roll_params(self, target, skill, attack_extra_rolled, vp=vp)

    def get_initiative_roll_params(self) -> Any:
        return self.roll_parameter_provider().get_initiative_roll_params(self)

    def get_skill_ring(self, skill: str) -> str:
        if not isinstance(skill, str):
            raise ValueError("skill must be str")
        return self._skill_rings.get(skill, "")

    def get_skill_roll_params(self, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> Any:
        return self.roll_parameter_provider().get_skill_roll_params(self, target, skill, contested_skill=contested_skill, ring=ring, vp=vp)

    def get_wound_check_roll_params(self, vp: int = 0) -> Any:
        return self.roll_parameter_provider().get_wound_check_roll_params(self, vp=vp)

    def group(self) -> "Group | None":
        return self._group

    def has_action(self, context: Any) -> bool:
        if len(self.actions()) == 0:
            return False
        else:
            result: bool = min(self.actions()) <= context.phase()
            return result

    def has_interrupt_action(self, skill: str, context: Any) -> bool:
        if skill in self._interrupt_skills:
            if self.interrupt_cost(skill, context) <= len(self.actions()):
                return True
        return False

    def interrupt_cost(self, skill: str, context: Any) -> int:
        return self._interrupt_costs.get(skill, 2)

    def interrupt_strategy(self) -> Any:
        return self._strategies["interrupt"]

    def initiative_priority(self, max_actions: int) -> float:
        priority = 0.0
        exponent = max_actions + 1
        # initiative priority rewards lower actions
        for action in self._actions:
            priority += (10 - action) * math.pow(10, exponent)
            exponent -= 1
        # break ties with void ring
        priority += self.ring("void")
        return priority

    def is_alive(self) -> bool:
        return self.sw() <= self.max_sw()

    def is_conscious(self) -> bool:
        return self.sw() < self.max_sw()

    def is_fighting(self) -> bool:
        return self.is_conscious()

    def is_friend(self, character: "Character") -> bool:
        if self._group is None:
            return False
        return character in self._group

    def knowledge(self) -> Knowledge:
        return self._knowledge

    def light_wounds_strategy(self) -> Any:
        return self._strategies["light_wounds"]

    def lw(self) -> int:
        return self._lw

    def lw_history(self) -> list[int]:
        return self._lw_history

    def max_ap_per_roll(self) -> int:
        base = self.ap_base_skill()
        if base is not None:
            return self.skill(base)
        else:
            return 0

    def max_sw(self) -> int:
        if "great destiny" in self._advantages:
            bonus = 1
        elif "permanent wound" in self._disadvantages:
            bonus = -1
        else:
            bonus = 0
        return (self.ring("earth") * 2) + bonus

    def max_vp(self) -> int:
        if self._max_vp_provider is not None:
            result = self._max_vp_provider.max_vp(self)
            assert isinstance(result, int)
            return result
        return min([self.ring(ring) for ring in RING_NAMES]) + self.skill("worldliness")

    def max_vp_per_roll(self) -> int:
        if "discordant" in self._disadvantages:
            return 0
        if self._max_vp_provider is not None:
            result = self._max_vp_provider.max_vp_per_roll(self)
            assert isinstance(result, int)
            return result
        return min([self.ring(ring) for ring in RING_NAMES])

    def modifier(self, target: Any, skill: str) -> int:
        applicable_modifiers = [mod.apply(target, skill) for mod in self._modifiers]
        return sum(applicable_modifiers) if len(applicable_modifiers) > 0 else 0

    def name(self) -> str:
        return self._name

    def xp(self) -> int:
        return self._xp

    def parry_strategy(self) -> Any:
        return self._strategies["parry"]

    def parry_rolled_strategy(self) -> Any:
        return self._strategies["parry_rolled"]

    def profession(self) -> Profession | None:
        return self._profession

    def remove_modifier(self, modifier: Any) -> None:
        self._modifiers.remove(modifier)

    def reset(self) -> None:
        self._actions = []
        self._ap_spent = 0
        self._conviction_spent = 0
        self._floating_bonuses.clear()
        self._knowledge.clear()
        self._lw = 0
        self._lw_history.clear()
        for modifier in self._modifiers:
            if len(modifier._listeners) > 0:
                self._modifiers.remove(modifier)
        self._sw = 0
        self._tvp = 0
        self._vp_spent = 0

    def reset_lw(self) -> None:
        self._lw = 0

    def ring(self, ring: str) -> int:
        return self._rings[ring]

    def rings(self) -> dict[str, int]:
        return self._rings

    def roll_damage(self, target: Any, skill: str, attack_extra_rolled: int = 0, vp: int = 0) -> int:
        rolled, kept, mod = self.get_damage_roll_params(target, skill, attack_extra_rolled, vp)
        reduction = target.damage_reroll_reduction() if target is not None else 0
        if reduction > 0:
            roll = self.roll_provider().get_damage_reduction_roll(rolled, kept, reduction) + mod
        else:
            roll = self.roll_provider().get_damage_roll(rolled, kept) + mod
        logger.info(f"{self._name} rolled damage: {roll}")
        assert isinstance(roll, int)
        return roll

    def roll_initiative(self) -> list[int]:
        (rolled, kept, mod) = self.get_initiative_roll_params()
        self._actions = self.roll_provider().get_initiative_roll(rolled, kept)
        logger.info(f"{self._name} rolled initiative: {self._actions}")
        return self._actions

    def roll_parameter_provider(self) -> RollParameterProvider:
        return self._roll_parameter_provider

    def roll_provider(self) -> RollProvider:
        return self._roll_provider

    def roll_skill(self, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> int:
        (rolled, kept, mod) = self.get_skill_roll_params(target, skill, contested_skill, ring, vp)
        explode = not self.crippled()
        roll = self.roll_provider().get_skill_roll(skill, rolled, kept, explode) + mod
        logger.info(f"{self._name} rolled {skill}: {roll}")
        assert isinstance(roll, int)
        return roll

    def roll_wound_check(self, damage: int, vp: int = 0, explode: bool = True) -> int:
        (rolled, kept, mod) = self.get_wound_check_roll_params(vp)
        roll = self.roll_provider().get_wound_check_roll(rolled, kept, explode=explode) + mod
        logger.info(f"{self._name} rolled wound check {roll} against {damage} LW")
        assert isinstance(roll, int)
        return roll

    def school(self) -> School | None:
        return self._school

    def set_action_factory(self, factory: ActionFactory) -> None:
        if not isinstance(factory, ActionFactory):
            raise ValueError("Character action factory must be an ActionFactory")
        self._action_factory = factory

    def set_ap_base_skill(self, skill: str) -> None:
        if not isinstance(skill, str):
            raise ValueError("set_ap_base_skill requires str")
        self._ap_base_skill = skill

    def set_ap_multiplier(self, n: int) -> None:
        if not isinstance(n, int):
            raise ValueError("set_ap_multiplier requires int")
        self._ap_multiplier = n

    def set_ap_skills(self, skills: list[str]) -> None:
        if not isinstance(skills, list):
            raise ValueError("set_ap_skills requires list")
        self._ap_skills = skills

    def set_action_strategy(self, strategy: Strategy) -> None:
        if not isinstance(strategy, Strategy):
            raise ValueError("Character action strategy must be a Strategy")
        self._strategies["action"] = strategy

    def set_attack_strategy(self, strategy: Strategy) -> None:
        if not isinstance(strategy, Strategy):
            raise ValueError("Character attack strategy must be a Strategy")
        self._strategies["attack"] = strategy

    def set_actions(self, actions: list[int]) -> None:
        if not isinstance(actions, list):
            raise ValueError("Character set_actions requires list of ints")
        for action in actions:
            if not isinstance(action, int):
                raise ValueError("Character set_actions requires list of ints")
        self._actions = actions

    def set_attack_rolled_penalty(self, n: int) -> None:
        if not isinstance(n, int):
            raise ValueError("set_attack_rolled_penalty requires int")
        self._attack_rolled_penalty = n

    def set_attack_optimizer_factory(self, factory: AttackOptimizerFactory) -> None:
        if not isinstance(factory, AttackOptimizerFactory):
            raise ValueError("set_attack_optimizer_factory requires AttackOptimizerFactory")
        self._attack_optimizer_factory = factory

    def set_damage_reroll_reduction(self, n: int) -> None:
        if not isinstance(n, int):
            raise ValueError("set_damage_reroll_reduction requires int")
        self._damage_reroll_reduction = n

    def set_extra_rolled(self, skill: str, extra_rolled: int = 1) -> None:
        if skill in self._extra_rolled.keys():
            self._extra_rolled[skill] += extra_rolled
        else:
            self._extra_rolled[skill] = extra_rolled

    def set_extra_kept(self, skill: str, extra_kept: int) -> None:
        self._extra_kept[skill] = extra_kept

    def set_group(self, group: "Group") -> None:
        self._group = group

    def set_interrupt_cost(self, skill: str, actions: int) -> None:
        self._interrupt_costs[skill] = actions

    def set_max_vp_provider(self, provider: Any) -> None:
        self._max_vp_provider = provider

    def set_listener(self, event_name: str, listener: listeners.Listener) -> None:
        self._listeners[event_name] = listener

    def set_parry_strategy(self, strategy: Strategy) -> None:
        if not isinstance(strategy, Strategy):
            raise ValueError("Character parry strategy must be a Strategy")
        self._strategies["parry"] = strategy

    def set_profession(self, profession: Profession) -> None:
        if not isinstance(profession, Profession):
            raise ValueError("Character set_profession function requires a Profession")
        self._profession = profession

    def set_ring(self, ring: str, rank: int) -> None:
        if ring not in RING_NAMES:
            raise ValueError(f"{ring} is not a ring")
        self._rings[ring.lower()] = rank

    def set_roll_parameter_provider(self, provider: RollParameterProvider) -> None:
        if not isinstance(provider, RollParameterProvider):
            raise ValueError("provider must be a RollParameterProvider")
        self._roll_parameter_provider = provider

    def set_roll_provider(self, provider: RollProvider) -> None:
        if not isinstance(provider, RollProvider):
            raise ValueError("provider must be a RollProvider")
        self._roll_provider = provider

    def set_school(self, school: School) -> None:
        if not isinstance(school, School):
            raise ValueError("Character set_school function requires a School")
        self._school = school

    def set_skill(self, skill: str, rank: int) -> None:
        self._skills[skill.lower()] = rank

    def set_strategy(self, name: str, strategy: Any) -> None:
        self._strategies[name] = strategy

    def set_take_action_event_factory(self, factory: TakeActionEventFactory) -> None:
        if not isinstance(factory, TakeActionEventFactory):
            raise ValueError("Character take action event factory must be a TakeActionEventFactory")
        self._take_action_event_factory = factory

    def set_weapon(self, weapon: Weapon) -> None:
        if not isinstance(weapon, Weapon):
            raise ValueError("set_weapon requires Weapon")
        self._weapon = weapon

    def set_wound_check_optimizer_factory(self, factory: WoundCheckOptimizerFactory) -> None:
        if not isinstance(factory, WoundCheckOptimizerFactory):
            raise ValueError("set_wound_check_optimizer_factory requires WoundCheckOptimizerFactory")
        self._wound_check_optimizer_factory = factory

    def set_wound_check_provider(self, provider: WoundCheckProvider) -> None:
        if not isinstance(provider, WoundCheckProvider):
            raise ValueError("Provider is not a WoundCheckProvider")
        self._wound_check_provider = provider

    def skill(self, skill: str) -> int:
        return self._skills.get(skill, 0)

    def skills(self) -> dict[str, int]:
        return self._skills

    def spend_action(self, initiative_action: Any) -> None:
        for die in initiative_action.dice():
            if die not in self._actions:
                raise ValueError(f"{self.name()} does not have an action in phase {die}")
            self._actions.remove(die)

    def spend_ap(self, skill: str, n: int) -> None:
        if not self.can_spend_ap(skill):
            raise ValueError(f"{self.name()} may not spend Adventure Points on {skill}")
        if n > 0:
            if self.ap() < n:
                raise ValueError("{} does not have enough Adventure Points")
            self._ap_spent += n

    def spend_conviction(self, n: int) -> None:
        if n > 0:
            if self.conviction() < n:
                raise ValueError("Not enough conviction points")
            self._conviction_spent += n

    def spend_floating_bonus(self, bonus: Any) -> None:
        self._floating_bonuses.remove(bonus)

    def spend_vp(self, n: int) -> None:
        if self.vp() < n:
            raise ValueError("Not enough Void Points")
        still_unspent = n
        while still_unspent > 0:
            if self._tvp > 0:
                self._tvp -= 1
                still_unspent -= 1
            elif self.vp() > 0:
                self._vp_spent += 1
                still_unspent -= 1
            else:
                raise ValueError("Not enough Void Points")

    def sw(self) -> int:
        return self._sw

    def sw_remaining(self) -> int:
        return self.max_sw() - self.sw()

    def take_action_event_factory(self) -> TakeActionEventFactory:
        return self._take_action_event_factory

    def take_advantage(self, advantage: str) -> None:
        self._advantages.append(advantage)
        if advantage == "strength of the earth":
            self.add_modifier(FreeRaise(self, "wound check"))

    def take_disadvantage(self, disadvantage: str) -> None:
        self._disadvantages.append(disadvantage)

    def take_lw(self, amount: int) -> None:
        logger.info(f"{self._name} takes {amount} Light Wounds (new total: {amount + self.lw()})")
        self._lw += amount
        self._lw_history.append(amount)

    def take_sw(self, amount: int) -> None:
        logger.info(f"{self._name} takes {amount} Serious Wounds")
        self._sw += amount

    def target_finder(self) -> EasiestTargetFinder:
        return self._target_finder

    def tn_to_hit(self) -> int:
        return (5 * (1 + self.skill("parry"))) + self.modifier(None, "tn to hit")

    def tvp(self) -> int:
        return self._tvp

    def void_point_manager(self) -> VoidPointManager:
        return self._void_point_manager

    def vp(self) -> int:
        return self.max_vp() - self._vp_spent + self._tvp

    def weapon(self) -> Weapon:
        return self._weapon

    def wound_check(self, roll: int, lw: int | None = None) -> int:
        if lw is None:
            lw = self.lw()
        return self.wound_check_provider().wound_check(roll, lw)

    def wound_check_optimizer_factory(self) -> WoundCheckOptimizerFactory:
        return self._wound_check_optimizer_factory

    def wound_check_rolled_strategy(self) -> Any:
        return self._strategies["wound_check_rolled"]

    def wound_check_provider(self) -> WoundCheckProvider:
        return self._wound_check_provider

    def wound_check_strategy(self) -> Any:
        return self._strategies["wound_check"]
