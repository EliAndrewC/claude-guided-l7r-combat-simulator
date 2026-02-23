"""Tests for the Kakita parry strategy."""

from simulation import events
from simulation.actions import AttackAction, DoubleAttackAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import TestRollProvider
from simulation.schools.kakita_school import KakitaParryStrategy


def _make_context(target, attacker, phase=1):
    """Set up groups and context for parry testing."""
    attacker_group = Group("attacker", attacker)
    target_group = Group("target", target)
    return EngineContext([attacker_group, target_group], round=1, phase=phase)


def _make_target(initiative_dice=None):
    """Create a target character with initiative rolled."""
    target = Character("Kakita")
    roll_provider = TestRollProvider()
    if initiative_dice is None:
        initiative_dice = [1, 1, 1]
    roll_provider.put_initiative_roll(initiative_dice)
    target.set_roll_provider(roll_provider)
    target.roll_initiative()
    return target


class TestKakitaParryStrategyNeverInterruptParries:
    """A Kakita should never spend future actions to interrupt parry."""

    def test_no_interrupt_parry_even_if_fatal(self):
        """Even a fatal hit should not trigger interrupt parry."""
        target = _make_target(initiative_dice=[4, 6])
        attacker = Character("attacker")
        # Target has actions in phases 4 and 6, but we're in phase 2
        # so no current-phase action — only interrupt is available
        context = _make_context(target, attacker, phase=2)
        context.initialize()
        initiative_action = InitiativeAction([4], 4)

        # Massive hit that would be fatal
        attack = AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)

        strategy = KakitaParryStrategy()
        responses = list(strategy.recommend(target, event, context))

        # Should NOT parry — interrupt parry is never worth it
        assert responses == []

    def test_no_interrupt_parry_double_attack(self):
        """Should not interrupt parry even a double attack."""
        target = _make_target(initiative_dice=[5, 7])
        attacker = Character("attacker")
        context = _make_context(target, attacker, phase=2)
        context.initialize()
        initiative_action = InitiativeAction([5], 5)

        attack = DoubleAttackAction(
            attacker, target, "double attack", initiative_action, context,
        )
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)

        strategy = KakitaParryStrategy()
        responses = list(strategy.recommend(target, event, context))
        assert responses == []


class TestKakitaParryStrategyNormalParry:
    """When a Kakita has a current-phase action, parry only if fatal."""

    def test_parry_when_fatal(self):
        """Should parry when the hit would kill."""
        target = _make_target(initiative_dice=[1, 5, 8])
        attacker = Character("attacker")
        context = _make_context(target, attacker, phase=1)
        context.initialize()
        initiative_action = InitiativeAction([1], 1)

        # Put target near death
        target.take_sw(target.sw_remaining() - 1)

        # Massive hit
        attack = AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)

        strategy = KakitaParryStrategy()
        responses = list(strategy.recommend(target, event, context))

        # Should parry — this would be fatal
        assert len(responses) == 2
        assert isinstance(responses[0], events.SpendActionEvent)
        assert isinstance(responses[1], events.TakeParryActionEvent)

    def test_no_parry_moderate_damage(self):
        """Should NOT parry moderate damage even with current-phase action."""
        target = _make_target(initiative_dice=[1, 5, 8])
        attacker = Character("attacker")
        context = _make_context(target, attacker, phase=1)
        context.initialize()
        initiative_action = InitiativeAction([1], 1)

        # Target is healthy (full SW)
        # A moderate hit that would deal a couple SW but not kill
        attack = AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(20)
        event = events.AttackRolledEvent(attack, 20)

        strategy = KakitaParryStrategy()
        responses = list(strategy.recommend(target, event, context))

        # Should NOT parry — not dire enough for a Kakita
        assert responses == []

    def test_no_parry_miss(self):
        """Should not try to parry an attack that missed."""
        target = _make_target(initiative_dice=[1, 5, 8])
        attacker = Character("attacker")
        context = _make_context(target, attacker, phase=1)
        context.initialize()
        initiative_action = InitiativeAction([1], 1)

        attack = AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(1)
        event = events.AttackRolledEvent(attack, 1)

        strategy = KakitaParryStrategy()
        responses = list(strategy.recommend(target, event, context))
        assert responses == []

    def test_parry_when_two_sw_remaining(self):
        """Should parry when only 2 SW remaining and attack looks big."""
        target = _make_target(initiative_dice=[1, 5, 8])
        attacker = Character("attacker")
        context = _make_context(target, attacker, phase=1)
        context.initialize()
        initiative_action = InitiativeAction([1], 1)

        # Target has only 2 SW left
        target.take_sw(target.sw_remaining() - 2)

        # Big hit likely to deal 2+ SW
        attack = AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)

        strategy = KakitaParryStrategy()
        responses = list(strategy.recommend(target, event, context))

        # Should parry — would be fatal
        assert len(responses) == 2
        assert isinstance(responses[0], events.SpendActionEvent)
        assert isinstance(responses[1], events.TakeParryActionEvent)
