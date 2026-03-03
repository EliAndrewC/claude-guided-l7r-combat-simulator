#!/usr/bin/env python3

#
# strategies.py
#
# Classes that make decisions about how to respond to events.
#

import math
from abc import ABC, abstractmethod

from simulation import events
from simulation.exceptions import NotEnoughActions
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.knowledge import TheoreticalCharacter
from simulation.optimizers.wound_check_optimizers import DefaultKeepLightWoundsOptimizer


class Strategy(ABC):
    """
    Class that can choose between possible decisions to respond to an Event.

    The Strategy and Listener classes both respond to an Event by
    optionally returning another Event, which begs the question, why
    not just put strategy logic into Listeners?

    The idea behind separating Listener and Strategy is to keep the two classes simple.
    Listener is responsible for knowing when to mutate the Character's state
    (taking damage, spending resources, etc). The Strategy implements
    complex logic to choose between possible courses of action.

    Mixing the two classes would result in big Listener classes that
    would contain too much complexity. It would be difficult to write
    such a big class, or to test it effectively.

    Isolating decision making logic in the Strategy class also helps
    deal with the fact that different kinds of characters will have
    different strategies around certain aspects of their behavior, and
    it will be easier to write a lot of different little Strategy classes
    than it would be to write several big Listener classes.
    """

    @abstractmethod
    def recommend(self, character, event, context):
        """
        recommend(character, event, context) -> Event or None
          character (Character): Character deciding how to respond to the Event
          event (Event): an Event requiring a decision about how to act
          context (EngineContext): context about other Characters, groups, timing, etc

        Makes a decision about whether and how to respond to an Event.
        This should be used to deal with decisions like whether to spend
        Void Points or school abilities, or whether to parry an attack,
        or whether to hold actions or spend them immediately, etc.
        """
        pass


class AlwaysAttackActionStrategy(Strategy):
    def recommend(self, character, event, context):
        if isinstance(event, events.YourMoveEvent):
            # try to attack if action available
            # TODO: evaluate whether to interrupt
            if character.has_action(context):
                yield from character.attack_strategy().recommend(character, event, context)
            else:
                yield events.NoActionEvent(character)


class HoldOneActionStrategy(Strategy):
    def recommend(self, character, event, context):
        if isinstance(event, events.YourMoveEvent):
            # try to hold an action in reserve until Phase 10
            if character.has_action(context):
                available_actions = [action for action in character.actions() if action <= context.phase()]
                # Phase 0 action dice are bonus actions (e.g. Kakita school)
                # that should never be held in reserve
                has_phase_zero_actions = any(a == 0 for a in available_actions)
                normal_available = sum(1 for a in available_actions if a > 0)
                if normal_available > 1 or context.phase() == 10 or has_phase_zero_actions:
                    yield from character.attack_strategy().recommend(character, event, context)
                else:
                    logger.debug(f"{character.name()} is holding an action")
                    yield events.HoldActionEvent(character)
            else:
                yield events.NoActionEvent(character)


class BaseAttackStrategy(Strategy):
    def choose_action(self, character, skill, context):
        if character.has_action(context):
            # choose earliest available action die
            # older action dice are usually more valuable
            action_die = min([die for die in character.actions() if die <= context.phase()])
            return InitiativeAction([action_die], action_die)
        elif character.has_interrupt_action(skill, context):
            cost = character.interrupt_cost(skill, context)
            action_dice = []
            unspent_action_dice = []
            unspent_action_dice.extend(character.actions())
            while len(action_dice) < cost:
                die = max(unspent_action_dice)
                unspent_action_dice.remove(die)
                action_dice.append(die)
            return InitiativeAction(action_dice, context.phase(), is_interrupt=True)
        else:
            raise NotEnoughActions()

    def _get_optimizer(self, character, target, skill, initiative_action, context):
        """Return an attack optimizer for the given parameters.

        Subclasses can override this to control VP spending or other
        optimizer behaviour without duplicating try_skill logic.
        """
        return character.attack_optimizer_factory().get_optimizer(
            character, target, skill, initiative_action, context,
        )

    def spend_action(self, character, skill, initiative_action):
        """
        spend_action(character, skill, initiative_action) -> SpendActionEvent

        Spend an action dice to take an attack.
        """
        yield events.SpendActionEvent(character, skill, initiative_action)

    def try_skill(self, character, skill, initiative_action, threshold, context):
        """
        try_skill(character, skill, initiative_action, threshold, context) -> TakeAttackActionEvent or None

        Returns a TakeAttackActionEvent if the strategy can successfully
        find a target and optimize an attack using the given skill.
        """
        if character.skill(skill) > 0:
            target = character.target_finder().find_target(character, skill, initiative_action, context)
            if target is not None:
                attack = self._get_optimizer(character, target, skill, initiative_action, context).optimize(threshold)
                if attack is not None:
                    logger.info(f"{character.name()} is attacking {target.name()} with {skill} and spending {attack.vp()} VP")
                    return character.take_action_event_factory().get_take_attack_action_event(attack)

    def recommend(self, character, event, context):
        raise NotImplementedError()


class PlainAttackStrategy(BaseAttackStrategy):
    def recommend(self, character, event, context):
        if isinstance(event, events.YourMoveEvent):
            if character.has_action(context):
                initiative_action = self.choose_action(character, "attack", context)
                # attempt to optimize for a good attack
                action_event = self.try_skill(character, "attack", initiative_action, 0.7, context)
                if action_event is not None:
                    yield from self.spend_action(character, "attack", initiative_action)
                    yield action_event
                    return
                # fell through: chance of success is low
                # try an attack anyway even if it's desperate
                action_event = self.try_skill(character, "attack", initiative_action, 0.01, context)
                if action_event is not None:
                    yield from self.spend_action(character, "attack", initiative_action)
                    yield action_event
                else:
                    yield events.HoldActionEvent(character)
            else:
                yield events.NoActionEvent(character)


class StingyPlainAttackStrategy(BaseAttackStrategy):
    """
    Always attack with available actions, never spend resources to optimize.
    """

    def recommend(self, character, event, context):
        if isinstance(event, events.YourMoveEvent):
            if character.has_action(context):
                initiative_action = self.choose_action(character, "attack", context)
                target = character.target_finder().find_target(character, "attack", initiative_action, context)
                if target is not None:
                    action = character.action_factory().get_attack_action(character, target, "attack", initiative_action, context)
                    logger.info(f"{character.name()} is attacking {target.name()}")
                    yield from self.spend_action(character, "attack", initiative_action)
                    yield character.take_action_event_factory().get_take_attack_action_event(action)
                else:
                    yield events.HoldActionEvent(character)
            else:
                yield events.NoActionEvent(character)


class UniversalAttackStrategy(BaseAttackStrategy):
    attack_threshold = 0.7

    def recommend(self, character, event, context):
        if isinstance(event, events.YourMoveEvent):
            # TODO: implement intelligence around interrupts
            if character.has_action(context):
                # try to double attack first
                initiative_action = self.choose_action(character, "double attack", context)
                double_attack_event = self.try_skill(character, "double attack", initiative_action, self.attack_threshold - 0.1, context)
                if double_attack_event is not None:
                    yield from self.spend_action(character, "double attack", initiative_action)
                    yield double_attack_event
                    return
                # TODO: consider a lunge (probably need a LungeStrategy)
                if character.vp() == 0 and len(character.actions()) > 1:
                    # if this character is out of VP and has more than one action in this round, a feint might be worth it
                    initiative_action = self.choose_action(character, "feint", context)
                    feint_event = self.try_skill(character, "feint", initiative_action, self.attack_threshold, context)
                    if feint_event is not None:
                        yield from self.spend_action(character, "feint", initiative_action)
                        yield feint_event
                        return
                # try a plain attack
                initiative_action = self.choose_action(character, "attack", context)
                attack_event = self.try_skill(character, "attack", initiative_action, self.attack_threshold, context)
                if attack_event is not None:
                    yield from self.spend_action(character, "attack", initiative_action)
                    yield attack_event
                    return
                # try a plain attack even if it's desperate
                initiative_action = self.choose_action(character, "attack", context)
                attack_event = self.try_skill(character, "attack", initiative_action, 0.01, context)
                if attack_event is not None:
                    yield from self.spend_action(character, "attack", initiative_action)
                    yield attack_event
                    return
                # fell through: do nothing
                yield events.HoldActionEvent(character)
            else:
                yield events.NoActionEvent(character)


class BaseParryStrategy(Strategy):
    def recommend(self, character, event, context):
        if isinstance(event, events.AttackRolledEvent):
            # bail if no action
            if not (character.has_action(context) or character.has_interrupt_action("parry", context)):
                logger.debug(f"{character.name()} will not parry because no action")
                return
            # don't try to parry for enemies
            if event.action.target() not in character.group():
                logger.debug(f"{character.name()} will not parry for an enemy")
                return
            # don't try to parry for non-adjacent allies
            target = event.action.target()
            if target != character:
                if not context.formation().is_adjacent(character, target):
                    logger.debug(f"{character.name()} will not parry for non-adjacent {target.name()}")
                    return
            # don't try to parry a miss or an attack that is already parried
            if not event.action.is_hit():
                logger.debug(f"{character.name()} will not parry an attack that missed")
                return
            # don't try to parry an attack that is already parried
            if event.action.parried():
                logger.debug(f"{character.name()} will not parry an attack was already parried")
                return
            # delegate to specific parry strategy recommendation
            try:
                yield from self._recommend(character, event, context)
            except NotEnoughActions:
                raise RuntimeError("Not enough actions to parry")
                return

    def _can_shirk(self, character, event, context):
        """
        Returns whether this character can shirk and let somebody else parry.
        """
        target = event.action.target()
        # do my other friends have actions?
        others = character.group().friends_with_actions(context)
        for other_character in others:
            # can't pass the buck to myself
            if character != other_character:
                # must be adjacent to the target
                if not context.formation().is_adjacent(other_character, target):
                    continue
                # did they already decline the parry?
                if other_character not in event.action.parries_declined():
                    # are they willing to parry?
                    if not isinstance(other_character.parry_strategy(), NeverParryStrategy):
                        # shirk the parry
                        return True
        return False

    def _choose_action(self, character, skill, context):
        """
        _choose_action(character, skill, context) -> InitiativeAction

        Choose action dice to spend to parry.
        """
        if character.has_action(context):
            # spend the newest available action
            # older actions are usually more valuable
            die = max([die for die in character.actions() if die <= context.phase()])
            return InitiativeAction([die], die)
        elif character.has_interrupt_action(skill, context):
            # interrupt
            cost = character.interrupt_cost(skill, context)
            action_dice = []
            unspent_action_dice = []
            unspent_action_dice.extend(character.actions())
            while len(action_dice) < cost:
                die = max(unspent_action_dice)
                unspent_action_dice.remove(die)
                action_dice.append(die)
            return InitiativeAction(action_dice, context.phase(), is_interrupt=True)
        else:
            # somehow character is unable to parry
            raise NotEnoughActions()

    def _estimate_damage(self, character, event, context):
        """
        _estimate_damage(character, event, context) -> int

        Returns an estimate of how many SW this attack will inflict.
        """
        # how much damage do we expect?
        expected_fire = TheoreticalCharacter(character.knowledge(), event.action.subject().name()).ring("fire")
        extra_dice = event.action.calculate_extra_damage_dice()
        weapon_rolled = event.action.subject().weapon().rolled()
        weapon_kept = event.action.subject().weapon().kept()
        expected_damage = context.mean_roll(expected_fire + weapon_rolled + extra_dice, weapon_kept)
        # how many wounds do we expect the target to take from this?
        target = event.action.target()
        (wc_rolled, wc_kept, wc_bonus) = target.get_wound_check_roll_params()
        expected_roll = context.mean_roll(wc_rolled, wc_kept) + wc_bonus
        expected_sw = target.wound_check(expected_roll, target.lw() + expected_damage)
        return expected_sw

    def _recommend(self, character, event, context):
        raise NotImplementedError()

    def _spend_action(self, character, skill, initiative_action):
        """
        _spend_action(character, skill, initiative_action) -> SpendActionEvent

        Spend action dice to parry.
        """
        yield events.SpendActionEvent(character, skill, initiative_action)


class AlwaysParryStrategy(BaseParryStrategy):
    """
    Always parry for friends.
    """

    def _recommend(self, character, event, context):
        logger.debug(f"{character.name()} always parries")
        initiative_action = self._choose_action(character, "parry", context)
        parry = character.action_factory().get_parry_action(character, event.action.subject(), event.action, "parry", initiative_action, context)
        yield from self._spend_action(character, "parry", initiative_action)
        yield character.take_action_event_factory().get_take_parry_action_event(parry)


class NeverParryStrategy(Strategy):
    """
    Never parry.
    """

    def recommend(self, character, event, context):
        logger.debug(f"{character.name()} never parries")
        yield from ()


class ReluctantParryStrategy(BaseParryStrategy):
    """
    Parry if the hit is going to be bad and nobody else can parry.
    """

    def _recommend(self, character, event, context):
        # let somebody else parry if possible
        # TODO: implement some kind of team parry strategy
        if self._can_shirk(character, event, context):
            logger.debug(f"{character.name()} is reluctant and shirks the parry")
            return
        # if parry was already attempted, no need to try again
        elif event.action.parry_attempted():
            logger.debug(f"{character.name()} is reluctant and will not parry when it was already attempted")
            return
        else:
            # how many wounds do we expect?
            expected_sw = self._estimate_damage(character, event, context)
            if event.action.skill() == "double attack":
                expected_sw += 1
            # parry if it looks bad
            target = event.action.target()
            probably_fatal = target.sw_remaining() <= expected_sw
            probably_critical = expected_sw >= 2
            if probably_fatal or probably_critical:
                if probably_fatal:
                    logger.debug(f"{character.name()} reluctantly parries because the attack would probably be fatal")
                elif probably_critical:
                    logger.debug(f"{character.name()} reluctantly parries because the attack looks dangerous")
                initiative_action = self._choose_action(character, "parry", context)
                parry = character.action_factory().get_parry_action(character, event.action.subject(), event.action, "parry", initiative_action, context)
                yield from self._spend_action(character, "parry", initiative_action)
                yield character.take_action_event_factory().get_take_parry_action_event(parry)
            else:
                logger.debug(f"{character.name()} will not parry a small attack")


class SkillRolledStrategy(Strategy):
    """
    Strategy to decide how to spend resources after a roll.
    """

    def __init__(self):
        self._chosen_ap = 0
        self._chosen_bonuses = []
        self._chosen_conviction = 0

    def event_matches(self, character, event):
        """
        Return whether this event is relevant for the strategy and character.
        """
        raise NotImplementedError()

    def get_skill(self, event):
        """
        Returns the skill that can be used for floating bonuses for this skill roll.
        """
        raise NotImplementedError()

    def get_tn(self, event):
        """
        Return the desired TN.
        """
        raise NotImplementedError()

    def recommend(self, character, event, context):
        if self.event_matches(character, event):
            self.reset()
            skill = self.get_skill(event)
            tn = self.get_tn(event)
            margin = tn - event.action.skill_roll()
            if margin <= 0:
                # if the roll was successful, do nothing
                yield event
                return
            # use floating bonuses to try to make the TN
            self.use_floating_bonuses(character, skill, margin)
            margin = tn - event.action.skill_roll() - sum([b.bonus() for b in self._chosen_bonuses])
            if margin > 0:
                # use adventure points to try to make the TN
                self.use_ap(character, event.action.skill(), margin)
                margin -= 5 * self._chosen_ap
            if margin > 0:
                # use conviction points to try to close remaining gap
                self.use_conviction(character, margin)
                margin -= self._chosen_conviction
            if margin <= 0:
                # if we reached the TN, spend resources and update the event
                for bonus in self._chosen_bonuses:
                    yield events.SpendFloatingBonusEvent(character, bonus)
                if self._chosen_ap > 0:
                    yield events.SpendAdventurePointsEvent(character, skill, self._chosen_ap)
                if self._chosen_conviction > 0:
                    yield events.SpendConvictionEvent(character, skill, self._chosen_conviction)
                new_roll = event.action.skill_roll() + sum([b.bonus() for b in self._chosen_bonuses]) + (5 * self._chosen_ap) + self._chosen_conviction
                event.action.set_skill_roll(new_roll)
                event.roll = new_roll
            yield event

    def reset(self):
        """
        Reset this strategy. Should be called before each use.
        """
        self._chosen_ap = 0
        self._chosen_bonuses.clear()
        self._chosen_conviction = 0

    def use_ap(self, character, skill, margin):
        if character.ap() > 0:
            if character.can_spend_ap(skill):
                ap_needed = math.ceil(margin / 5)
                max_spend = min(character.ap(), character.max_ap_per_roll())
                self._chosen_ap = min(max_spend, ap_needed)

    def use_conviction(self, character, margin):
        if character.conviction() > 0:
            max_spend = min(character.conviction(), character.max_conviction_per_roll())
            self._chosen_conviction = min(max_spend, max(margin, 0))

    def use_floating_bonuses(self, character, skill, margin):
        available_bonuses = list(character.floating_bonuses(skill))
        available_bonuses.sort()
        while margin > 0 and len(available_bonuses) > 0:
            bonus = available_bonuses.pop(0)
            self._chosen_bonuses.append(bonus)
            margin -= bonus.bonus()


class AttackRolledStrategy(SkillRolledStrategy):
    def event_matches(self, character, event):
        return isinstance(event, events.AttackRolledEvent) and character == event.action.subject()

    def get_skill(self, event):
        return event.action.skill()

    def get_tn(self, event):
        return event.action.tn()


class ParryRolledStrategy(SkillRolledStrategy):
    def event_matches(self, character, event):
        return isinstance(event, events.ParryRolledEvent) and character == event.action.subject()

    def get_skill(self, event):
        return event.action.skill()

    def get_tn(self, event):
        return event.action.tn()


class WoundCheckRolledStrategy(SkillRolledStrategy):
    """
    Strategy to decide how to spend resources to improve
    a wound check roll.

    This strategy is written to only spend resources to avoid
    defeat or taking more than 1 SW. It will not spend resources
    to try to succeed at the Wound Check.
    """

    def __init__(self):
        self._chosen_ap = 0
        self._chosen_bonuses = []
        self._chosen_conviction = 0

    def recommend(self, character, event, context):
        if isinstance(event, events.WoundCheckRolledEvent):
            if event.subject == character:
                self.reset()
                # how many wounds would I take?
                expected_sw = character.wound_check(event.roll)
                if expected_sw == 0:
                    # ignore it if no SW expected
                    yield event
                else:
                    # calculate how many SW are tolerable
                    # normally 1 SW is tolerable
                    # but if one wound means defeat, then only 0 SW is tolerable
                    tolerable_sw = min(1, character.sw_remaining() - 1)
                    # use wound check specific floating bonuses
                    new_event = self.use_floating_bonuses(character, event, tolerable_sw, "wound check")
                    new_expected_sw = character.wound_check(new_event.roll)
                    if new_expected_sw > tolerable_sw:
                        # use adventure points
                        new_event = self.use_ap(character, new_event, tolerable_sw, "wound check")
                    new_expected_sw = character.wound_check(new_event.roll)
                    if new_expected_sw > tolerable_sw:
                        # use conviction points
                        new_event = self.use_conviction_wc(character, new_event, tolerable_sw)
                    new_expected_sw = character.wound_check(new_event.roll)
                    if new_expected_sw < expected_sw:
                        # progress: spend resources and use the new roll
                        for bonus in self._chosen_bonuses:
                            yield events.SpendFloatingBonusEvent(character, bonus)
                        if self._chosen_ap > 0:
                            yield events.SpendAdventurePointsEvent(character, "wound check", self._chosen_ap)
                        if self._chosen_conviction > 0:
                            yield events.SpendConvictionEvent(character, "wound check", self._chosen_conviction)
                        yield new_event
                    else:
                        # but the future refused to change
                        # spend nothing and take the hit
                        yield event

    def reset(self):
        self._chosen_ap = 0
        self._chosen_bonuses.clear()
        self._chosen_conviction = 0

    def use_ap(self, character, event, tolerable_sw, skill):
        ap = character.ap()
        max_spend = min(ap, character.max_ap_per_roll())
        new_roll = event.roll
        if character.can_spend_ap("wound check"):
            new_expected_sw = character.wound_check(new_roll)
            while self._chosen_ap < max_spend:
                self._chosen_ap += 1
                new_roll += 5
                new_expected_sw = character.wound_check(new_roll)
                if new_expected_sw == tolerable_sw:
                    break
        return events.WoundCheckRolledEvent(event.subject, event.attacker, event.damage, new_roll, tn=event.tn)

    def use_conviction_wc(self, character, event, tolerable_sw):
        max_spend = min(character.conviction(), character.max_conviction_per_roll())
        new_roll = event.roll
        while self._chosen_conviction < max_spend:
            self._chosen_conviction += 1
            new_roll += 1
            new_expected_sw = character.wound_check(new_roll)
            if new_expected_sw == tolerable_sw:
                break
        return events.WoundCheckRolledEvent(event.subject, event.attacker, event.damage, new_roll, tn=event.tn)

    def use_floating_bonuses(self, character, event, tolerable_sw, skill):
        available_bonuses = character.floating_bonuses(skill)
        available_bonuses.sort()
        new_roll = event.roll
        new_expected_sw = character.wound_check(new_roll)
        for bonus in available_bonuses:
            self._chosen_bonuses.append(bonus)
            new_roll += bonus.bonus()
            new_expected_sw = character.wound_check(new_roll)
            if new_expected_sw == tolerable_sw:
                break
        return events.WoundCheckRolledEvent(event.subject, event.attacker, event.damage, new_roll, tn=event.tn)


class AlwaysKeepLightWoundsStrategy(Strategy):
    """
    Strategy that always keeps LW.
    """

    def recommend(self, character, event, context):
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                logger.info(f"{character.name()} always keeps light wounds")
                yield events.KeepLightWoundsEvent(event.subject, event.attacker, event.damage, tn=event.tn)


class KeepLightWoundsStrategy(Strategy):
    """
    Strategy to decide whether to keep LW or take SW.
    """

    def recommend(self, character, event, context):
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                if event.tn > event.roll:
                    raise RuntimeError("KeepLightWoundsStrategy should not be consulted for a failed wound check")
                # keep LW to avoid defeat
                if character.sw_remaining() == 1:
                    logger.info(f"{character.name()} keeping light wounds to avoid defeat.")
                    yield events.KeepLightWoundsEvent(character, event.attacker, event.damage, tn=event.tn)
                    return
                # consult KeepLightWoundsOptimizer
                optimizer = DefaultKeepLightWoundsOptimizer(character, context)
                (should_keep, reserve_vp) = optimizer.should_keep(1, 0.6, max_vp=1)
                if should_keep:
                    logger.info(f"{character.name()} keeping {character.lw()} LW and reserving {reserve_vp} VP for a future Wound Check")
                    character.void_point_manager().reserve("wound check", reserve_vp)
                    yield events.KeepLightWoundsEvent(character, event.attacker, event.damage, tn=event.tn)
                else:
                    logger.info(f"{character.name()} taking a serious wound because the next wound check might be bad.")
                    yield events.TakeSeriousWoundEvent(character, event.attacker, event.damage, tn=event.tn)


class NeverKeepLightWoundsStrategy(Strategy):
    """
    Strategy that never keeps LW, always takes SW.
    """

    def recommend(self, character, event, context):
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                logger.info(f"{character.name()} never keeps light wounds")
                yield events.SeriousWoundsDamageEvent(event.attacker, character, 1)


class WoundCheckStrategy(Strategy):
    """
    Strategy to decide how many VP to spend on a wound check.
    """

    threshold = 0.6

    def recommend(self, character, event, context):
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.target == character:
                if getattr(event, 'duel', False):
                    yield events.WoundCheckDeclaredEvent(
                        character, event.subject, event.damage,
                        tn=event.wound_check_tn, vp=0, duel=True,
                    )
                    return
                # calculate maximum tolerable SW
                max_sw = min(1, character.sw_remaining() - 1)
                optimizer = character.wound_check_optimizer_factory().get_wound_check_optimizer(character, event, context)
                yield optimizer.declare(max_sw, self.threshold)


class WoundCheckStrategy02(WoundCheckStrategy):
    """Wound check optimizer with 0.2 confidence threshold (very aggressive spending)."""

    threshold = 0.2


class WoundCheckStrategy05(WoundCheckStrategy):
    """Wound check optimizer with 0.5 confidence threshold."""

    threshold = 0.5


class WoundCheckStrategy04(WoundCheckStrategy):
    """Wound check optimizer with 0.4 confidence threshold."""

    threshold = 0.4


class WoundCheckStrategy08(WoundCheckStrategy):
    """Wound check optimizer with 0.8 confidence threshold (very conservative spending)."""

    threshold = 0.8


class StingyWoundCheckStrategy(Strategy):
    """
    Never spend VP on wound checks.
    """

    def recommend(self, character, event, context):
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.target == character:
                logger.info(f"{character.name()} never spends VP on wound checks.")
                yield events.WoundCheckDeclaredEvent(character, event.subject, event.damage, tn=event.wound_check_tn)


class DefaultInterruptStrategy(Strategy):
    """Unified interrupt strategy that delegates to the parry strategy.

    Used by characters who do not have counterattack capability.
    """

    def recommend(self, character, event, context):
        if isinstance(event, events.AttackRolledEvent):
            yield from character.parry_strategy().recommend(character, event, context)


class CounterattackInterruptStrategy(Strategy):
    """Unified interrupt strategy for counterattack schools.

    Considers counterattacking when attacked, falls back to parry otherwise.
    Only characters with the counterattack school knack may counterattack.
    """

    def _should_counterattack(self, character, event, context):
        """Decide whether to counterattack."""
        # Must have counterattack skill
        if character.skill("counterattack") <= 0:
            return False
        # Target must be in our group (defend friends)
        target = event.action.target()
        if target not in character.group():
            return False
        # Must be adjacent to the target (can always counterattack for self)
        if target != character:
            if not context.formation().is_adjacent(character, target):
                return False
        # Must have action dice available
        if not (character.has_action(context) or character.has_interrupt_action("counterattack", context)):
            return False
        return True

    def _choose_action(self, character, context):
        """Choose action dice for the counterattack."""
        if character.has_action(context):
            die = max([d for d in character.actions() if d <= context.phase()])
            return InitiativeAction([die], die)
        elif character.has_interrupt_action("counterattack", context):
            cost = character.interrupt_cost("counterattack", context)
            action_dice = []
            unspent = list(character.actions())
            while len(action_dice) < cost:
                die = max(unspent)
                unspent.remove(die)
                action_dice.append(die)
            return InitiativeAction(action_dice, context.phase(), is_interrupt=True)
        else:
            raise NotEnoughActions()

    def _do_counterattack(self, character, event, context):
        """Execute the counterattack."""
        initiative_action = self._choose_action(character, context)
        counterattack = character.action_factory().get_counterattack_action(
            character, event.action.subject(), event.action,
            "counterattack", initiative_action, context,
        )
        logger.info(f"{character.name()} is counterattacking {event.action.subject().name()}")
        yield events.SpendActionEvent(character, "counterattack", initiative_action)
        yield character.take_action_event_factory().get_take_counterattack_action_event(counterattack)

    def recommend(self, character, event, context):
        if isinstance(event, events.AttackDeclaredEvent):
            if self._should_counterattack(character, event, context):
                try:
                    yield from self._do_counterattack(character, event, context)
                    return
                except NotEnoughActions:
                    pass
        elif isinstance(event, events.AttackRolledEvent):
            # Counterattack already handled at declaration time; only parry here
            yield from character.parry_strategy().recommend(character, event, context)
