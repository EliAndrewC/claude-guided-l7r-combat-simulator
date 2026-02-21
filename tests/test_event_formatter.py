from unittest.mock import MagicMock

from simulation.events import (
    AttackFailedEvent,
    AttackRolledEvent,
    AttackSucceededEvent,
    DeathEvent,
    EndOfPhaseEvent,
    HoldActionEvent,
    LightWoundsDamageEvent,
    NewPhaseEvent,
    NewRoundEvent,
    NoActionEvent,
    SeriousWoundsDamageEvent,
    SpendVoidPointsEvent,
    TakeAttackActionEvent,
    UnconsciousEvent,
    WoundCheckFailedEvent,
    WoundCheckSucceededEvent,
)
from web.adapters.event_formatter import format_event, format_history


def _mock_character(name):
    char = MagicMock()
    char.name.return_value = name
    return char


def _mock_action(subject_name, target_name, skill="attack"):
    action = MagicMock()
    action.subject.return_value = _mock_character(subject_name)
    action.target.return_value = _mock_character(target_name)
    action.skill.return_value = skill
    return action


class TestFormatEvent:
    def test_new_round(self):
        event = NewRoundEvent(1)
        result = format_event(event)
        assert result == "--- Round 1 ---"

    def test_new_phase(self):
        event = NewPhaseEvent(3)
        result = format_event(event)
        assert result == "  Phase 3"

    def test_take_attack_action(self):
        action = _mock_action("Akodo", "Bayushi", "attack")
        event = TakeAttackActionEvent(action)
        result = format_event(event)
        assert result == "Akodo attacks Bayushi with attack"

    def test_attack_rolled(self):
        action = _mock_action("Akodo", "Bayushi")
        event = AttackRolledEvent(action, 28)
        result = format_event(event)
        assert result == "  Roll: 28"

    def test_attack_succeeded(self):
        action = _mock_action("Akodo", "Bayushi")
        event = AttackSucceededEvent(action)
        result = format_event(event)
        assert result == "  Hit!"

    def test_attack_failed(self):
        action = _mock_action("Akodo", "Bayushi")
        event = AttackFailedEvent(action)
        result = format_event(event)
        assert result == "  Miss."

    def test_lw_damage(self):
        subject = _mock_character("Akodo")
        target = _mock_character("Bayushi")
        event = LightWoundsDamageEvent(subject, target, 22)
        result = format_event(event)
        assert result == "  Bayushi takes 22 light wounds"

    def test_sw_damage(self):
        subject = _mock_character("Akodo")
        target = _mock_character("Bayushi")
        event = SeriousWoundsDamageEvent(subject, target, 2)
        result = format_event(event)
        assert result == "  Bayushi takes 2 serious wounds"

    def test_wound_check_succeeded(self):
        subject = _mock_character("Bayushi")
        attacker = _mock_character("Akodo")
        event = WoundCheckSucceededEvent(subject, attacker, 22, 30)
        result = format_event(event)
        assert result == "  Bayushi passes wound check (rolled 30 vs 22)"

    def test_wound_check_failed(self):
        subject = _mock_character("Bayushi")
        attacker = _mock_character("Akodo")
        event = WoundCheckFailedEvent(subject, attacker, 22, 10)
        result = format_event(event)
        assert result == "  Bayushi fails wound check (rolled 10 vs 22)"

    def test_spend_void_points(self):
        subject = _mock_character("Akodo")
        event = SpendVoidPointsEvent(subject, "attack", 1)
        result = format_event(event)
        assert result == "  Akodo spends 1 VP on attack"

    def test_death(self):
        subject = _mock_character("Bayushi")
        event = DeathEvent(subject)
        result = format_event(event)
        assert result == "  Bayushi is killed!"

    def test_unconscious(self):
        subject = _mock_character("Bayushi")
        event = UnconsciousEvent(subject)
        result = format_event(event)
        assert result == "  Bayushi falls unconscious!"

    def test_irrelevant_events_return_none(self):
        event = EndOfPhaseEvent(3)
        assert format_event(event) is None
        event = HoldActionEvent(_mock_character("Akodo"))
        assert format_event(event) is None
        event = NoActionEvent(_mock_character("Akodo"))
        assert format_event(event) is None


class TestFormatHistory:
    def test_format_history_filters_none(self):
        events = [
            NewRoundEvent(1),
            NewPhaseEvent(0),
            HoldActionEvent(_mock_character("Akodo")),
            EndOfPhaseEvent(0),
        ]
        lines = format_history(events)
        assert "--- Round 1 ---" in lines
        assert "  Phase 0" in lines
        assert len(lines) == 2

    def test_format_history_empty(self):
        assert format_history([]) == []
