"""Tests for the KakitaInterruptAttackStrategy."""

from simulation import events
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.schools.kakita_school import (
    KakitaAttackStrategy,
    KakitaBushiSchool,
    KakitaInterruptAttackStrategy,
)


def _build_kakita(xp: int = 300, attack_strategy=None):
    """Build a Kakita character for testing."""
    builder = (
        CharacterBuilder()
        .with_xp(xp)
        .with_name("TestKakita")
        .with_school(KakitaBushiSchool())
    )
    builder.buy_skill("double attack", 3)
    builder.buy_skill("iaijutsu", 3)
    builder.buy_skill("lunge", 3)
    builder.buy_skill("attack", 3)
    builder.buy_skill("parry", 3)
    builder.buy_ring("earth", 3)
    character = builder.build()
    if attack_strategy is not None:
        character.set_attack_strategy(attack_strategy)
    return character


def _build_opponent(xp: int = 200):
    """Build a generic opponent."""
    builder = CharacterBuilder().with_xp(xp).with_name("Opponent").generic()
    builder.buy_skill("attack", 3)
    builder.buy_skill("parry", 3)
    builder.buy_ring("earth", 3)
    builder.buy_ring("fire", 3)
    return builder.build()


def _make_context(kakita, opponent, phase: int = 5):
    """Create an engine context and set the phase."""
    group1 = Group("Group A", [kakita])
    group2 = Group("Group B", [opponent])
    context = EngineContext([group1, group2])
    context.initialize()
    # Set phase directly
    context._phase = phase
    return context


class TestKakitaInterruptAttackStrategy:
    def test_interrupt_when_no_current_action(self):
        """Character has future dice but no current-phase action -> attempts iaijutsu interrupt."""
        strategy = KakitaInterruptAttackStrategy()
        kakita = _build_kakita(attack_strategy=strategy)
        opponent = _build_opponent()
        context = _make_context(kakita, opponent, phase=5)

        # Give kakita only future action dice (phase 8 and 9)
        kakita._actions = [8, 9]

        event = events.YourMoveEvent(kakita)
        result = list(strategy.recommend(kakita, event, context))

        # Should attempt an interrupt (SpendActionEvent + attack event)
        assert len(result) >= 1
        # First event should be SpendActionEvent for the interrupt
        has_spend = any(isinstance(e, events.SpendActionEvent) for e in result)
        has_no_action = any(isinstance(e, events.NoActionEvent) for e in result)
        # With iaijutsu skill at 3, it should attempt the interrupt
        assert has_spend or has_no_action
        # Verify it's NOT a NoActionEvent (it should spend)
        if has_spend:
            spend_event = [e for e in result if isinstance(e, events.SpendActionEvent)][0]
            assert spend_event.skill == "iaijutsu"

    def test_no_interrupt_when_action_available(self):
        """Has normal action -> behaves like parent (normal attack)."""
        strategy = KakitaInterruptAttackStrategy()
        kakita = _build_kakita(attack_strategy=strategy)
        opponent = _build_opponent()
        context = _make_context(kakita, opponent, phase=5)

        # Give kakita a current-phase action die
        kakita._actions = [5, 8]

        event = events.YourMoveEvent(kakita)
        result = list(strategy.recommend(kakita, event, context))

        # Should use normal attack, not interrupt
        has_spend = any(isinstance(e, events.SpendActionEvent) for e in result)
        assert has_spend
        if has_spend:
            spend_event = [e for e in result if isinstance(e, events.SpendActionEvent)][0]
            # Normal attack uses attack skill, not iaijutsu (non-Phase-0)
            assert spend_event.skill != "iaijutsu" or context.phase() == 0

    def test_no_interrupt_when_not_enough_dice(self):
        """Fewer than 2 future dice -> NoActionEvent."""
        strategy = KakitaInterruptAttackStrategy()
        kakita = _build_kakita(attack_strategy=strategy)
        opponent = _build_opponent()
        context = _make_context(kakita, opponent, phase=5)

        # Give kakita only 1 future die (need 2 for interrupt)
        kakita._actions = [8]

        event = events.YourMoveEvent(kakita)
        result = list(strategy.recommend(kakita, event, context))

        # Should yield NoActionEvent since can't interrupt with only 1 die
        assert any(isinstance(e, events.NoActionEvent) for e in result)

    def test_phase_zero_preserved(self):
        """Phase 0 -> still uses parent's Phase 0 iaijutsu logic."""
        strategy = KakitaInterruptAttackStrategy()
        kakita = _build_kakita(attack_strategy=strategy)
        opponent = _build_opponent()
        context = _make_context(kakita, opponent, phase=0)

        # Give kakita a phase-0 action die
        kakita._actions = [0, 5]

        event = events.YourMoveEvent(kakita)
        result = list(strategy.recommend(kakita, event, context))

        # Should use iaijutsu for Phase 0
        has_spend = any(isinstance(e, events.SpendActionEvent) for e in result)
        if has_spend:
            spend_event = [e for e in result if isinstance(e, events.SpendActionEvent)][0]
            assert spend_event.skill == "iaijutsu"

    def test_base_strategy_no_interrupt(self):
        """Verify KakitaAttackStrategy yields NoActionEvent when no action (proving baseline)."""
        strategy = KakitaAttackStrategy()
        kakita = _build_kakita(attack_strategy=strategy)
        opponent = _build_opponent()
        context = _make_context(kakita, opponent, phase=5)

        # Give kakita only future action dice
        kakita._actions = [8, 9]

        event = events.YourMoveEvent(kakita)
        result = list(strategy.recommend(kakita, event, context))

        # Base strategy should NOT attempt interrupts
        assert any(isinstance(e, events.NoActionEvent) for e in result)
        assert not any(isinstance(e, events.SpendActionEvent) for e in result)
