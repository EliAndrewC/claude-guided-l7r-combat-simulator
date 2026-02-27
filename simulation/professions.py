#!/usr/bin/env python3

#
# professions.py
#
# Professions and profession abilities for the L7R combat simulator
#

from abc import ABC, abstractmethod

from simulation.actions import AttackAction
from simulation.events import AddModifierEvent, AttackSucceededEvent, LightWoundsDamageEvent, NewRoundEvent, TakeAttackActionEvent
from simulation.listeners import Listener
from simulation.mechanics.modifiers import FreeRaise, Modifier
from simulation.mechanics.ninja_rolls import NinjaDamageKeepRoll, NinjaWoundCheckRoll
from simulation.mechanics.roll import BaseRoll
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.roll_provider import DefaultRollProvider
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.modifier_listeners import ExpireAfterNextDamageByCharacterListener
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory

# supported ability names - Wave Man
CRIPPLED_BONUS = "crippled bonus"
DAMAGE_PENALTY = "damage penalty"
FAILED_PARRY_DAMAGE_BONUS = "failed parry damage bonus"
INITIATIVE_BONUS = "initiative bonus"
MISSED_ATTACK_BONUS = "missed attack bonus"
PARRY_PENALTY = "parry penalty"
ROLLED_DAMAGE_BONUS = "rolled damage bonus"
WEAPON_DAMAGE_BONUS = "weapon damage bonus"
WOUND_CHECK_BONUS = "wound check bonus"
WOUND_CHECK_PENALTY = "wound check penalty"

# supported ability names - Ninja
ATTACK_BONUS = "attack bonus"
ATTACK_PENALTY = "attack penalty"
DAMAGE_KEEPING_BONUS = "damage keeping bonus"
DAMAGE_REDUCTION = "damage reduction"
DEFENSE_BONUS = "defense bonus"
INITIATIVE_REDUCTION = "initiative reduction"
SINCERITY_BONUS = "sincerity bonus"
STEALTH_INVISIBILITY = "stealth (invisibility)"
STEALTH_MEMORABILITY = "stealth (memorability)"
WOUND_CHECK_NINJA_BONUS = "wound check ninja bonus"

# list of supported ability names
ABILITY_NAMES = [
    ATTACK_BONUS, ATTACK_PENALTY, CRIPPLED_BONUS,
    DAMAGE_KEEPING_BONUS, DAMAGE_PENALTY, DAMAGE_REDUCTION,
    DEFENSE_BONUS, FAILED_PARRY_DAMAGE_BONUS,
    INITIATIVE_BONUS, INITIATIVE_REDUCTION,
    MISSED_ATTACK_BONUS, PARRY_PENALTY,
    ROLLED_DAMAGE_BONUS, SINCERITY_BONUS,
    STEALTH_INVISIBILITY, STEALTH_MEMORABILITY,
    WEAPON_DAMAGE_BONUS, WOUND_CHECK_BONUS,
    WOUND_CHECK_NINJA_BONUS, WOUND_CHECK_PENALTY,
]


class Profession:
    """
    Class to represent a character's chosen abilities in a peasant
    profession.
    """

    def __init__(self):
        self._abilityd = {}

    def ability(self, name):
        """
        ability(name) -> int
          name (str): the name of the ability of interest

        Returns the number of times a character has taken the named
        ability (0, 1, or 2)
        """
        if not isinstance(name, str):
            raise ValueError("ability requires a str")
        if name not in ABILITY_NAMES:
            raise ValueError(f"{name} is not a valid profession ability")
        return self._abilityd.get(name, 0)

    def take_ability(self, name):
        """
        take_ability(name)
          name (str): the name of the ability to take

        Take the named ability. Abilities may be taken at most twice.
        """
        if not isinstance(name, str):
            raise ValueError("take_ability requires a str")
        if name not in ABILITY_NAMES:
            raise ValueError(f"{name} is not a valid profession ability")
        cur_rank = self.ability(name)
        if cur_rank == 2:
            raise RuntimeError(f"Profession ability {name} may not be raised above 2")
        self._abilityd[name] = cur_rank + 1

    def __len__(self):
        """
        __len__() -> int

        Returns the number of abilities taken.
        Multiple levels of an ability count as two abilities taken.
        """
        return sum(self._abilityd.values())


class ProfessionAbility(ABC):
    """
    Class to represent a peasant profession ability. Its apply method
    should modify the given character object to add the ability to
    the character.
    """

    @abstractmethod
    def apply(self, character, profession):
        """
        apply(character, profession)
          character (Character): character who took the ability
          profession (Profession): the character's Profession object

        Updates the character to confer this profession ability.
        """
        pass


def get_profession_ability(name):
    """
    get_profession_ability(name) -> ProfessionAbility
      name (str): name of the desired ability

    Returns a ProfessionAbility instance capable of applying the
    named ability to a character.
    """
    if not isinstance(name, str):
        raise ValueError("get_profession_ability requires str")
    # Wave Man abilities
    if name == CRIPPLED_BONUS:
        return CrippledBonusAbility()
    elif name == DAMAGE_PENALTY:
        return DamagePenaltyAbility()
    elif name == FAILED_PARRY_DAMAGE_BONUS:
        return FailedParryDamageBonusAbility()
    elif name == INITIATIVE_BONUS:
        return InitiativeBonusAbility()
    elif name == MISSED_ATTACK_BONUS:
        return MissedAttackBonusAbility()
    elif name == PARRY_PENALTY:
        return ParryPenaltyAbility()
    elif name == ROLLED_DAMAGE_BONUS:
        return RolledDamageBonusAbility()
    elif name == WEAPON_DAMAGE_BONUS:
        return RolledDamageBonusAbility()
    elif name == WOUND_CHECK_BONUS:
        return WoundCheckBonusAbility()
    elif name == WOUND_CHECK_PENALTY:
        return WoundCheckPenaltyAbility()
    # Ninja abilities
    elif name == ATTACK_BONUS:
        return NinjaAttackBonusAbility()
    elif name == ATTACK_PENALTY:
        return NinjaAttackPenaltyAbility()
    elif name == DAMAGE_KEEPING_BONUS:
        return NinjaDamageKeepingBonusAbility()
    elif name == DAMAGE_REDUCTION:
        return NinjaDamageReductionAbility()
    elif name == DEFENSE_BONUS:
        return NinjaDefenseBonusAbility()
    elif name == INITIATIVE_REDUCTION:
        return NinjaInitiativeReductionAbility()
    elif name == SINCERITY_BONUS:
        return NinjaSincerityBonusAbility()
    elif name == STEALTH_INVISIBILITY:
        return NinjaStealthInvisibilityAbility()
    elif name == STEALTH_MEMORABILITY:
        return NinjaStealthMemorabilityAbility()
    elif name == WOUND_CHECK_NINJA_BONUS:
        return NinjaWoundCheckBonusAbility()
    else:
        raise ValueError(f"{name} is not a valid profession ability")


class CrippledBonusAbility(ProfessionAbility):
    """
    Represents the "crippled bonus" Wave Man profession ability:
    "You may reroll 10s on a single die when crippled."
    """

    def apply(self, character, profession):
        character.set_roll_provider(WaveManRollProvider(profession))


class DamagePenaltyAbility(ProfessionAbility):
    """
    Represents the "damage penalty" Wave Man profession ability:
    "When someone is keeping at least one extra die of damage from
    exceeding their attack roll TN, subtract 5 from the damage."
    """

    def apply(self, character, profession):
        character.set_listener("attack_succeeded", WAVE_MAN_ATTACK_SUCCEEDED_LISTENER)


class FailedParryDamageBonusAbility(ProfessionAbility):
    """
    Represents the "failed parry damage bonus" Wave Man profession
    ability:
    "When someone unsuccessfully tries to parry an attack, you may
    roll two of the extra damage dice that you would have rolled
    had they not attempted to parry."
    """

    def apply(self, character, profession):
        character.set_action_factory(WaveManActionFactory(profession))


class InitiativeBonusAbility(ProfessionAbility):
    """
    Represents the "initiative bonus" Wave Man profession ability:
    "Roll one extra unkept die on initiative."
    """

    def apply(self, character, profession):
        character.set_extra_rolled("initiative", 1)


class MissedAttackBonusAbility(ProfessionAbility):
    """
    Represents the "missed attack bonus" Wave Man profession ability:
    "When you make an attack roll that would miss, raise it by 5. Any
    parry attempt against an attack that receives a free raise in this
    manner automatically succeeds."
    """

    def apply(self, character, profession):
        # implemented in WaveManAttackAction
        character.set_action_factory(WaveManActionFactory(profession))


class ParryPenaltyAbility(ProfessionAbility):
    """
    Represents the "parry penalty" Wave Man profession ability:
    "Raise the TN of someone trying to parry one of your attacks by 5."
    """

    def apply(self, character, profession):
        # implemented in WaveManAttackAction
        character.set_action_factory(WaveManActionFactory(profession))


class RolledDamageBonusAbility(ProfessionAbility):
    """
    Represents the "rolled damage bonus" Wave Man profession ability:
    "Round your damage rolls up to the nearest multiple of 5. If the
    roll is already a multiple of 5, then raise it by 3."
    """

    def apply(self, character, profession):
        # implemented in WaveManAttackAction
        character.set_action_factory(WaveManActionFactory(profession))


class WeaponDamageBonusAbility(ProfessionAbility):
    """
    Represents the "weapon damage bonus" Wave Man profession ability:
    "When using a weapon that deals less than 4k2 damage, add an extra
    rolled damage die to the weapon's base damage, to a maximum of 4k2
    base damage. Also, subtract 2 from your armor damage reduction
    penalty."
    """

    def apply(self, character, profession):
        # The weapon damage bonus is implemented in WaveManRollParameterProvider.
        # The armor damage reduction part of this ability is not implemented;
        # armor and damage reduction are planned for a later project phase.
        character.set_roll_parameter_provider(WaveManRollParameterProvider(profession))


class WoundCheckBonusAbility(ProfessionAbility):
    """
    Represents the "wound check bonus" Wave Man profession ability:
    "Roll two extra unkept dice on wound checks."
    """

    def apply(self, character, profession):
        character.set_extra_rolled("wound check", 2)


class WoundCheckPenaltyAbility(ProfessionAbility):
    """
    Represents the "wound check penalty" Wave Man profession ability:
    "Raise the TN of someone making a wound check from damage you
    dealt to them by 5. If they fail they take serious wounds as if
    the TN had not been raised."
    """

    def apply(self, character, profession):
        character.set_take_action_event_factory(WAVE_MAN_TAKE_ACTION_EVENT_FACTORY)


class WaveManActionFactory(DefaultActionFactory):
    """
    ActionFactory that can return a WaveManAttackAction.
    """

    def __init__(self, abilities):
        self._abilities = abilities

    def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
        if skill == "attack":
            return WaveManAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        else:
            return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


class WaveManAttackAction(AttackAction):
    """
    AttackAction to implement the Wave Man profession abilities:

    "When you make an attack roll that would miss, raise it by 5.
    Any parry attempt against an attack that receives a free raise in
    this manner automatically succeeds."

    and:
    "Raise the TN of someone trying to parry one of your attacks by 5."

    and:
    "Round your damage rolls up to the nearest multiple of 5. If the
    roll is already a multiple of 5, then raise it by 3."

    and:
    "When someone unsuccessfully tries to parry an attack, you may
    roll two of the extra damage dice that you would have rolled
    had they not attempted to parry."
    """

    def __init__(self, subject, target, skill, initiative_action, context, vp=0):
        super().__init__(subject, target, skill, initiative_action, context, vp=vp)
        self._used_missed_attack_bonus = False

    def ability(self, name):
        return self.subject().profession().ability(name)

    def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        # calculate normal extra rolled damage dice
        extra_rolled = (skill_roll - self.tn()) // 5
        if self.parry_attempted():
            # failed parries usually cancel extra rolled damage dice
            # failed_parry_damage_bonus ability preserves some of
            # the extra rolled dice
            return min(extra_rolled, self.ability(FAILED_PARRY_DAMAGE_BONUS) * 2)
        else:
            return extra_rolled

    def parry_tn(self):
        if self.used_missed_attack_bonus():
            # parry automatically succeeds if the missed_attack_bonus
            # ability was used
            return 0
        else:
            # apply the parry penalty ability
            penalty = self.ability(PARRY_PENALTY) * 5
            return self.skill_roll() + penalty

    def roll_skill(self):
        roll = self.subject().roll_skill(self.target(), self.skill(), vp=self.vp())
        # apply missed_attack_bonus ability
        if roll < self.tn():
            for i in range(self.ability(MISSED_ATTACK_BONUS)):
                if roll < self.tn():
                    roll += 5
                    self.set_used_missed_attack_bonus()
        self.set_skill_roll(roll)
        return self.skill_roll()

    def roll_damage(self):
        extra_rolled = self.calculate_extra_damage_dice()
        roll = self.subject().roll_damage(self.target(), self.skill(), extra_rolled, self.vp())
        # apply damage_bonus ability
        for i in range(self.ability(ROLLED_DAMAGE_BONUS)):
            if roll % 5 == 0:
                roll += 3
            else:
                roll += 5 - (roll % 5)
        self._damage_roll = roll
        return self._damage_roll

    def set_used_missed_attack_bonus(self):
        """
        set_used_missed_attack_bonus()

        Sets the boolean flag to indicate that this attack used the
        "missed attack bonus" ability to hit.
        """
        self._used_missed_attack_bonus = True

    def used_missed_attack_bonus(self):
        """
        used_missed_attack_bonus() -> bool

        Returns whether the "missed attack bonus" ability was used
        to make this attack hit.
        """
        return self._used_missed_attack_bonus


class WaveManAttackSucceededListener(Listener):
    """
    Listener that implements the Wave Man profession ability
    "damage penalty":
    "When someone is keeping at least one extra die of damage from
    exceeding their attack roll TN, subtract 5 from the damage."
    """

    def handle(self, character, event, context):
        if isinstance(event, AttackSucceededEvent):
            if character == event.action.target():
                ability_level = character.profession().ability(DAMAGE_PENALTY)
                (rolled, kept, mod) = event.action.damage_roll_params()
                if kept > 2 and ability_level > 0:
                    penalty = ability_level * -5
                    modifier = Modifier(event.action.subject(), character, "damage", penalty)
                    modifier_listener = ExpireAfterNextDamageByCharacterListener(event.action.subject(), character)
                    modifier.register_listener("lw_damage", modifier_listener)
                    yield AddModifierEvent(event.action.subject(), modifier)


# singleton instance
WAVE_MAN_ATTACK_SUCCEEDED_LISTENER = WaveManAttackSucceededListener()


class WaveManRoll(BaseRoll):
    """
    Roll that implements the Wave Man profession ability
    "crippled bonus":
    "You may reroll 10s on a single die when crippled."
    """

    def __init__(self, rolled, kept, faces=10, explode=True, die_provider=None, always_explode=0):
        super().__init__(rolled, kept, faces, explode, die_provider)
        if not isinstance(always_explode, int):
            raise ValueError("WaveManRoll always_explode parameter must be int")
        if always_explode > 2:
            raise ValueError("WaveManRoll may not reroll more than two tens when crippled")
        self.always_explode = always_explode
        self._dice = []

    def dice(self):
        return self._dice

    def roll(self):
        dice = [self.roll_die(faces=self.faces(), explode=self.explode()) for n in range(self._rolled)]
        if not self.explode():
            for i in range(self.always_explode):
                if 10 in dice:
                    dice.remove(10)
                    rerolled = 10 + self.roll_die(faces=self.faces(), explode=True)
                    dice.append(rerolled)
        dice.sort(reverse=True)
        self._dice = dice
        return sum(dice[: self._kept]) + self._bonus


class WaveManRollParameterProvider(DefaultRollParameterProvider):
    """
    RollParameterProvider that implements the Wave Man profession
    ability "weapon damage bonus":
    "When using a weapon that deals less than 4k2 damage, add an extra
    rolled damage die to the weapon's base damage, to a maximum of 4k2
    base damage. Also, subtract 2 from your armor damage reduction
    penalty."
    """

    def get_damage_roll_params(self, character, target, skill, attack_extra_rolled, vp=0):
        # calculate weapon dice
        weapon_rolled = character.weapon().rolled()
        ability_level = character.profession().ability(WEAPON_DAMAGE_BONUS)
        if weapon_rolled < 4:
            weapon_rolled = min(4, weapon_rolled + ability_level)
        # calculate extra rolled dice
        ring = character.ring(character.get_skill_ring("damage"))
        my_extra_rolled = character.extra_rolled("damage")
        rolled = ring + my_extra_rolled + attack_extra_rolled + weapon_rolled
        # calculate extra kept dice
        my_extra_kept = character.extra_kept("damage") + character.extra_kept("damage_" + skill)
        kept = character.weapon().kept() + my_extra_kept
        # calculate modifier
        mod = character.modifier("damage", None) + character.modifier("damage_" + skill, None)
        return normalize_roll_params(rolled, kept, mod)


class WaveManRollProvider(DefaultRollProvider):
    """
    RollProvider that implements the Wave Man profession ability
    "crippled bonus" to reroll some 10s when crippled.
    """

    def __init__(self, profession, die_provider=None):
        super().__init__(die_provider)
        if not isinstance(profession, Profession):
            raise ValueError("WaveManRollProvider __init__ requires Profession")
        self._profession = profession

    def ability(self, ability):
        return self._profession.ability(ability)

    def get_skill_roll(self, skill, rolled, kept, explode=True):
        """
        get_skill_roll(skill, rolled, kept) -> int
          skill (str): name of skill being used
          rolled (int): number of rolled dice
          kept (int): number of kept dice
          explode (bool): whether tens should be rerolled

        Return a skill roll using the specified number of rolled and kept dice.
        """
        always_explode = self.ability("crippled bonus")
        roll = WaveManRoll(rolled, kept, die_provider=self.die_provider(), explode=explode, always_explode=always_explode)
        result = roll.roll()
        self._last_skill_roll = roll
        self._last_skill_info = {"rolled": rolled, "kept": kept, "dice": list(roll.dice())}
        return result


class WaveManTakeAttackActionEvent(TakeAttackActionEvent):
    """
    TakeAttackActionEvent to implement the Wave Man profession
    ability "wound check penalty":
    "Raise the TN of someone making a Wound Check from damage you
    dealt to them by 5. If they fail, they take Serious Wounds as if
    the TN had not been raised."
    """

    def _roll_damage(self):
        damage_roll = self.action.roll_damage()
        wound_check_tn_penalty = 5 * self.action.subject().profession().ability(WOUND_CHECK_PENALTY)
        wound_check_tn = damage_roll + wound_check_tn_penalty
        return LightWoundsDamageEvent(self.action.subject(), self.action.target(), damage_roll, tn=wound_check_tn)


class WaveManTakeActionEventFactory(DefaultTakeActionEventFactory):
    """
    TakeActionEventFactory to implement the Wave Man profession
    ability "wound check penalty":
    "Raise the TN of someone making a Wound Check from damage you
    dealt to them by 5. If they fail, they take Serious Wounds as if
    the TN had not been raised."
    """

    def get_take_attack_action_event(self, action):
        """
        get_take_attack_action_event(action)
          -> WaveManTakeAttackActionEvent
          action (Action): an AttackAction

        Returns a WaveManTakeAttackActionEvent to run an attack.
        """
        if isinstance(action, AttackAction):
            return WaveManTakeAttackActionEvent(action)
        else:
            raise ValueError("get_take_attack_action_event only supports TakeAttackAction")


WAVE_MAN_TAKE_ACTION_EVENT_FACTORY = WaveManTakeActionEventFactory()


# ── Ninja profession abilities ──────────────────────────────────────────


class NinjaAttackBonusAbility(ProfessionAbility):
    """
    Ninja ability: "Add Fire ring value to attack rolls."
    """

    def apply(self, character, profession):
        modifier = NinjaFireAttackModifier(character, profession)
        character.add_modifier(modifier)


class NinjaAttackPenaltyAbility(ProfessionAbility):
    """
    Ninja ability: "Attacker rolls 1 fewer die on attacks, min Fire ring."
    Sets the target's attack_rolled_penalty.
    """

    def apply(self, character, profession):
        character.set_attack_rolled_penalty(profession.ability(ATTACK_PENALTY))


class NinjaDamageKeepingBonusAbility(ProfessionAbility):
    """
    Ninja ability: "Keep 2 extra lowest unkept dice on damage rolls."
    """

    def apply(self, character, profession):
        character.set_roll_provider(NinjaRollProvider(profession))


class NinjaDamageReductionAbility(ProfessionAbility):
    """
    Ninja ability: "Attacker rerolls 1 fewer 10 on damage (min 1 rerolled)."
    """

    def apply(self, character, profession):
        character.set_damage_reroll_reduction(profession.ability(DAMAGE_REDUCTION))


class NinjaDefenseBonusAbility(ProfessionAbility):
    """
    Ninja ability: "+5 TN to hit ninja; if hit with extra damage,
    attacker gets +1 rolled damage die."
    """

    def apply(self, character, profession):
        modifier = NinjaTNModifier(character, profession)
        character.add_modifier(modifier)
        character.set_listener("attack_succeeded", NinjaDefenseBonusDamageListener(profession))


class NinjaInitiativeReductionAbility(ProfessionAbility):
    """
    Ninja ability: "Lower all action dice by 2 after rolling."
    """

    def apply(self, character, profession):
        character.set_listener("new_round", NinjaNewRoundListener(profession))


class NinjaSincerityBonusAbility(ProfessionAbility):
    """
    Ninja ability: "4 free raises on sincerity."
    """

    def apply(self, character, profession):
        for _ in range(4):
            character.add_modifier(FreeRaise(character, "sincerity"))


class NinjaStealthInvisibilityAbility(ProfessionAbility):
    """
    Ninja ability: "4 free raises on sneaking (not seen)."
    """

    def apply(self, character, profession):
        for _ in range(4):
            character.add_modifier(FreeRaise(character, "sneaking"))


class NinjaStealthMemorabilityAbility(ProfessionAbility):
    """
    Ninja ability: "4 free raises on sneaking (not memorable)."
    """

    def apply(self, character, profession):
        for _ in range(4):
            character.add_modifier(FreeRaise(character, "sneaking"))


class NinjaWoundCheckBonusAbility(ProfessionAbility):
    """
    Ninja ability: "Dice < 5 on wound checks get bonus of (5-X)."
    """

    def apply(self, character, profession):
        character.set_roll_provider(NinjaRollProvider(profession))


# ── Ninja support classes ───────────────────────────────────────────────


class NinjaTNModifier(Modifier):
    """
    Dynamic modifier returning 5 * level for "tn to hit" skill.
    Uses profession object for dynamic level lookup.
    """

    def __init__(self, subject, profession):
        super().__init__(subject, None, "tn to hit", 0)
        self._profession = profession

    def apply(self, target, skill):
        if skill in self.skills():
            return 5 * self._profession.ability(DEFENSE_BONUS)
        return 0


class NinjaFireAttackModifier(Modifier):
    """
    Dynamic modifier returning character.ring("fire") * level for attack skills.
    """

    def __init__(self, subject, profession):
        super().__init__(subject, None, ATTACK_SKILLS, 0)
        self._profession = profession

    def apply(self, target, skill):
        if skill in self.skills():
            return self._subject.ring("fire") * self._profession.ability(ATTACK_BONUS)
        return 0


class NinjaDefenseBonusDamageListener(Listener):
    """
    Listener on AttackSucceededEvent. When ninja is target and
    action.calculate_extra_damage_dice() > 0: temporarily increments
    attacker's extra_rolled("damage") by level.
    """

    def __init__(self, profession):
        self._profession = profession

    def handle(self, character, event, context):
        if isinstance(event, AttackSucceededEvent):
            if character == event.action.target():
                level = self._profession.ability(DEFENSE_BONUS)
                if level > 0 and event.action.calculate_extra_damage_dice() > 0:
                    event.action.subject().set_extra_rolled("damage", level)
                    modifier = NinjaDefenseBonusModifier(event.action.subject(), character, level)
                    modifier_listener = ExpireAfterNextDamageByCharacterListener(event.action.subject(), character)
                    modifier.register_listener("lw_damage", modifier_listener)
                    yield AddModifierEvent(event.action.subject(), modifier)


class NinjaDefenseBonusModifier(Modifier):
    """
    Modifier with value=0 that restores attacker's extra_rolled("damage")
    when the modifier expires after the damage roll.
    """

    def __init__(self, subject, target, level):
        super().__init__(subject, target, "damage", 0)
        self._level = level

    def handle(self, character, event, context):
        if event.name in self._listeners.keys():
            # Restore extra_rolled before yielding the remove event
            self._subject.set_extra_rolled("damage", -self._level)
            yield from self._listeners[event.name].handle(character, event, self, context)


class NinjaNewRoundListener(Listener):
    """
    Handles NewRoundEvent. Rolls initiative normally, then subtracts
    2 * level from each action die (minimum 1).
    """

    def __init__(self, profession):
        self._profession = profession

    def handle(self, character, event, context):
        if isinstance(event, NewRoundEvent):
            character.roll_initiative()
            level = self._profession.ability(INITIATIVE_REDUCTION)
            reduction = 2 * level
            new_actions = [max(1, a - reduction) for a in character.actions()]
            character.set_actions(sorted(new_actions))
            yield from ()


class NinjaRollProvider(DefaultRollProvider):
    """
    RollProvider for Ninja profession abilities.
    Overrides damage and wound check rolls.
    """

    def __init__(self, profession, die_provider=None):
        super().__init__(die_provider)
        if not isinstance(profession, Profession):
            raise ValueError("NinjaRollProvider __init__ requires Profession")
        self._profession = profession

    def get_damage_roll(self, rolled, kept):
        level = self._profession.ability(DAMAGE_KEEPING_BONUS)
        if level > 0:
            extra_lowest = 2 * level
            roll = NinjaDamageKeepRoll(rolled, kept, extra_lowest=extra_lowest, die_provider=self.die_provider())
            result = roll.roll()
            self._last_damage_roll = roll
            self._last_damage_info = {"rolled": rolled, "kept": kept, "dice": list(roll.dice())}
            return result
        return super().get_damage_roll(rolled, kept)

    def get_wound_check_roll(self, rolled, kept):
        level = self._profession.ability(WOUND_CHECK_NINJA_BONUS)
        if level > 0:
            roll = NinjaWoundCheckRoll(rolled, kept, ability_level=level, die_provider=self.die_provider())
            result = roll.roll()
            self._last_wound_check_roll = roll
            self._last_wound_check_info = {"rolled": rolled, "kept": kept, "dice": list(roll.dice())}
            return result
        return super().get_wound_check_roll(rolled, kept)
