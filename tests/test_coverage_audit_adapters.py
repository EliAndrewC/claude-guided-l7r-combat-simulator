"""Coverage audit tests for web/adapters/*.

Target the uncovered branches and untested code paths in
``web/adapters/*.py`` modules per the Coverage to 100% audit
(specs/006-coverage-to-100).  Each test docstring cites the file:line
it covers.
"""

import os

import pytest

from web.adapters.character_adapter import (
    config_to_character,
    load_data_directory,
    load_template_directory,
)
from web.adapters.engine_adapter import (
    is_duel_eligible,
    run_duel_batch,
    run_duel_single,
)
from web.adapters.event_formatter import format_event, format_history
from web.adapters.modifier_breakdown import explain_modifier
from web.models import BatchResult, CharacterConfig, GroupConfig, SingleCombatResult


def _load_test_configs():
    data_dir = os.path.join(
        os.path.dirname(__file__), "..", "simulation", "data",
    )
    return load_data_directory(data_dir)


def _find(configs, name):
    for c in configs:
        if c.name == name:
            return c
    raise KeyError(name)


class TestEngineAdapterDuelPaths:
    """Cover the duel-mode branches in web/adapters/engine_adapter.py
    (lines 125-133, 138-161, 173-199)."""

    def test_is_duel_eligible_requires_two_groups(self):
        """A single-group config is not eligible."""
        configs = _load_test_configs()
        kakita = _find(configs, "Kakita")
        ctrl = GroupConfig(name="ctrl", is_control=True, character_names=["Kakita"])
        assert is_duel_eligible([kakita], [ctrl]) is False

    def test_is_duel_eligible_requires_one_character_per_group(self):
        configs = _load_test_configs()
        kakita = _find(configs, "Kakita")
        bayushi = _find(configs, "Bayushi")
        ctrl = GroupConfig(
            name="ctrl", is_control=True, character_names=["Kakita", "Bayushi"],
        )
        test = GroupConfig(
            name="test", is_control=False, character_names=["Bayushi"],
        )
        assert is_duel_eligible([kakita, bayushi], [ctrl, test]) is False

    def test_is_duel_eligible_requires_iaijutsu_skill(self):
        configs = _load_test_configs()
        kakita = _find(configs, "Kakita")
        # Build an opponent without iaijutsu by setting skills.iaijutsu = 0
        no_iai = CharacterConfig(
            name="NoIai", xp=200, char_type="generic",
            rings={"air": 3, "earth": 3, "fire": 3, "water": 3, "void": 2},
            skills={"attack": 3, "parry": 3, "iaijutsu": 0},
        )
        ctrl = GroupConfig(name="ctrl", is_control=True, character_names=["Kakita"])
        test = GroupConfig(name="test", is_control=False, character_names=["NoIai"])
        assert is_duel_eligible([kakita, no_iai], [ctrl, test]) is False

    def test_is_duel_eligible_true_for_two_iaijutsu_duelists(self):
        configs = _load_test_configs()
        kakita = _find(configs, "Kakita")
        bayushi = _find(configs, "Bayushi")
        ctrl = GroupConfig(name="ctrl", is_control=True, character_names=["Kakita"])
        test = GroupConfig(name="test", is_control=False, character_names=["Bayushi"])
        assert is_duel_eligible([kakita, bayushi], [ctrl, test]) is True

    def test_run_duel_single_returns_single_combat_result(self):
        configs = _load_test_configs()
        kakita = _find(configs, "Kakita")
        bayushi = _find(configs, "Bayushi")
        ctrl = GroupConfig(name="ctrl", is_control=True, character_names=["Kakita"])
        test = GroupConfig(name="test", is_control=False, character_names=["Bayushi"])
        result = run_duel_single([kakita, bayushi], [ctrl, test])
        assert isinstance(result, SingleCombatResult)
        assert result.winner in (-1, 1)
        assert len(result.play_by_play) > 0

    def test_run_duel_batch_returns_batch_result(self):
        configs = _load_test_configs()
        kakita = _find(configs, "Kakita")
        bayushi = _find(configs, "Bayushi")
        ctrl = GroupConfig(name="ctrl", is_control=True, character_names=["Kakita"])
        test = GroupConfig(name="test", is_control=False, character_names=["Bayushi"])
        result = run_duel_batch([kakita, bayushi], [ctrl, test], num_trials=3)
        assert isinstance(result, BatchResult)
        assert result.num_trials == 3
        assert result.control_victories + result.test_victories == 3


class TestCharacterAdapterFileFilter:
    """Cover the non-yaml filename filter branches (lines 111, 125)."""

    def test_load_data_directory_skips_non_yaml(self, tmp_path):
        """Non-.yaml files are ignored (line 111)."""
        # Create a directory with one yaml file and one .txt file
        d = tmp_path / "chars"
        d.mkdir()
        (d / "foo.txt").write_text("not yaml")
        (d / "akodo.yaml").write_text(
            "name: Akodo\nxp: 100\nschool: Akodo Bushi School\n",
        )
        configs = load_data_directory(str(d))
        names = [c.name for c in configs]
        assert "Akodo" in names
        assert len(configs) == 1

    def test_load_template_directory_skips_non_yaml(self, tmp_path):
        """Non-.yaml files in template tree are ignored (line 125)."""
        d = tmp_path / "templates"
        d.mkdir()
        sub = d / "tier1"
        sub.mkdir()
        (sub / "info.txt").write_text("not yaml")
        (sub / "kakita.yaml").write_text(
            "name: Kakita\nxp: 100\nschool: Kakita Bushi School\n",
        )
        configs = load_template_directory(str(d))
        assert len(configs) == 1
        assert configs[0].name == "Kakita"

    def test_config_to_character_profession_branch(self):
        """char_type=profession exercises the with_profession() branch."""
        from simulation.character import Character
        config = CharacterConfig(
            name="Prof", xp=100, char_type="profession",
            rings={"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2},
            skills={},
        )
        char = config_to_character(config)
        assert isinstance(char, Character)

    def test_config_to_character_generic_branch(self):
        """char_type='generic' (and anything else) exercises the generic() branch."""
        from simulation.character import Character
        config = CharacterConfig(
            name="Gen", xp=100, char_type="generic",
            rings={"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2},
            skills={},
        )
        char = config_to_character(config)
        assert isinstance(char, Character)


class TestModifierBreakdownDefensiveBranches:
    """Cover the early-return defensive branches in modifier_breakdown.py
    (lines 58, 61)."""

    def test_school_rank_no_school(self):
        """When character has no school, _school_rank returns 0 (line 58)."""
        from web.adapters.modifier_breakdown import _school_rank

        class NoSchool:
            def school(self) -> None:
                return None

        assert _school_rank(NoSchool()) == 0

    def test_school_rank_no_knacks(self):
        """When the school has no knacks, _school_rank returns 0 (line 61)."""
        from web.adapters.modifier_breakdown import _school_rank

        class EmptySchool:
            def school_knacks(self) -> list[str]:
                return []

        class Character:
            def school(self) -> EmptySchool:
                return EmptySchool()

        assert _school_rank(Character()) == 0

    def test_explain_modifier_unknown_school_returns_empty(self):
        """A character whose school isn't in the recognized list returns
        an empty contribution list."""

        class UnknownSchool:
            def name(self) -> str:
                return "Unknown School"

            def school_knacks(self) -> list[str]:
                return ["attack"]

        class Char:
            def school(self) -> UnknownSchool:
                return UnknownSchool()

            def skill(self, _name: str) -> int:
                return 1

        contribs = explain_modifier(Char(), "attack", 5)
        assert contribs == []

    def test_explain_modifier_action_without_ishi_tags_returns_empty(self):
        """Action without _ishi_boosted_by tag adds no contributions."""

        class Char:
            def school(self) -> None:
                return None

        class Action:
            pass  # no ishi tags

        contribs = explain_modifier(Char(), "attack", 5, action=Action())
        assert contribs == []


class TestEventFormatterFormatHistory:
    """Cover format_history with surrender event (lines 38, 40-42, 44, 46, 48)."""

    def test_format_history_with_all_event_kinds(self):
        """All previously-uncovered event branches return non-None."""
        from unittest.mock import MagicMock

        from simulation.events import (
            ParryFailedEvent,
            ParryRolledEvent,
            ParrySucceededEvent,
            SurrenderEvent,
            TakeParryActionEvent,
        )

        def _char(name):
            c = MagicMock()
            c.name.return_value = name
            return c

        def _action(s, t, skill="parry"):
            a = MagicMock()
            a.subject.return_value = _char(s)
            a.target.return_value = _char(t)
            a.skill.return_value = skill
            return a

        history = [
            TakeParryActionEvent(_action("B", "A")),
            ParryRolledEvent(_action("B", "A"), 12),
            ParrySucceededEvent(_action("B", "A")),
            ParryFailedEvent(_action("B", "A")),
            SurrenderEvent(_char("B")),
        ]
        lines = format_history(history)
        assert len(lines) == 5
        assert any("attempts to parry" in line for line in lines)
        assert any("Parry roll: 12" in line for line in lines)
        assert any("Parry succeeded" in line for line in lines)
        assert any("Parry failed" in line for line in lines)
        assert any("surrenders" in line for line in lines)


class TestTrackingRollProvider:
    """Cover TrackingRollProvider methods 63, 66, 105-112, 131-133, 177."""

    def _make_inner_provider(self):
        from simulation.mechanics.roll_provider import DefaultRollProvider
        return DefaultRollProvider()

    def test_die_provider_delegates_to_inner(self):
        from web.adapters.combat_observer import TrackingRollProvider
        inner = self._make_inner_provider()
        tracker = TrackingRollProvider(inner)
        # die_provider returns whatever inner has
        assert tracker.die_provider() is inner.die_provider()

    def test_set_die_provider_delegates_to_inner(self):
        from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER
        from web.adapters.combat_observer import TrackingRollProvider
        inner = self._make_inner_provider()
        tracker = TrackingRollProvider(inner)
        tracker.set_die_provider(DEFAULT_DIE_PROVIDER)
        # set_die_provider should not raise; verify by reading back
        assert tracker.die_provider() is DEFAULT_DIE_PROVIDER

    def test_get_damage_reduction_roll(self):
        from web.adapters.combat_observer import TrackingRollProvider
        inner = self._make_inner_provider()
        tracker = TrackingRollProvider(inner)
        # Damage reduction rolls work and update last_damage_info
        result = tracker.get_damage_reduction_roll(rolled=3, kept=2, reduction=5)
        assert isinstance(result, int)
        info = tracker.last_damage_info()
        assert info is not None
        assert info["rolled"] == 3
        assert info["kept"] == 2

    def test_get_initiative_roll_falls_back_to_inner_info(self):
        """When recorded dice list is empty, falls back to inner.last_initiative_info."""
        from web.adapters.combat_observer import TrackingRollProvider

        class StubInner:
            def __init__(self):
                self._die_provider = None

            def get_initiative_roll(self, rolled, kept):
                # Don't record via _die_provider; that simulates the
                # "recorded is empty" case.
                return [10, 8]

            def last_initiative_info(self):
                return {"all_dice": [7, 6, 5], "rolled": 3, "kept": 2}

            def die_provider(self):
                return None

            def set_die_provider(self, dp):
                pass

        tracker = TrackingRollProvider(StubInner())
        result = tracker.get_initiative_roll(3, 2)
        info = tracker.last_initiative_info()
        # Should use the inner's last_initiative_info["all_dice"]
        assert info["all_dice"] == sorted([7, 6, 5])
        assert result == [10, 8]

    def test_getattr_delegates_to_inner(self):
        """Access to an arbitrary attribute is forwarded to the inner provider."""
        from web.adapters.combat_observer import TrackingRollProvider

        class Inner:
            custom_attribute = "hello"

            def __init__(self):
                self._die_provider = None

            def die_provider(self):
                return None

            def set_die_provider(self, dp):
                pass

        tracker = TrackingRollProvider(Inner())
        assert tracker.custom_attribute == "hello"


class TestCombatObserverPartial:
    """Cover combat_observer.CombatObserver branches that aren't naturally
    hit by run_single tests (305-317, 357, 361-362, 377, 471, 479-480, 508,
    515-516, 553-554, 568-569, 211, 215)."""

    def test_adjust_params_for_ishi_boost_short_params_returns_unchanged(self):
        """When params is too short, _adjust_params_for_ishi_boost returns it
        unchanged (line 357)."""
        from web.adapters.combat_observer import CombatObserver

        class Action:
            _ishi_boost_value = 7

        # An empty params tuple
        result = CombatObserver._adjust_params_for_ishi_boost((), Action())
        assert result == ()
        # A short tuple
        result = CombatObserver._adjust_params_for_ishi_boost((5, 3), Action())
        assert result == (5, 3)

    def test_adjust_params_for_ishi_boost_no_boost(self):
        """When no _ishi_boost_value tag, params returned unchanged (361-362)."""
        from web.adapters.combat_observer import CombatObserver

        class Action:
            pass

        result = CombatObserver._adjust_params_for_ishi_boost((5, 3, 2), Action())
        assert result == (5, 3, 2)

        class Action2:
            _ishi_boost_value = "not_an_int"
        result = CombatObserver._adjust_params_for_ishi_boost((5, 3, 2), Action2())
        assert result == (5, 3, 2)

        class Action3:
            _ishi_boost_value = 0
        result = CombatObserver._adjust_params_for_ishi_boost((5, 3, 2), Action3())
        assert result == (5, 3, 2)

    def test_adjust_params_for_ishi_boost_applies_when_tagged(self):
        from web.adapters.combat_observer import CombatObserver

        class Action:
            _ishi_boost_value = 5

        result = CombatObserver._adjust_params_for_ishi_boost((5, 3, 2), Action())
        assert result == (5, 3, 7)

    def test_build_modifier_breakdown_zero_modifier(self):
        """When modifier is zero, returns [] (line 379-380, hits line 377 too if params too short)."""
        from web.adapters.combat_observer import CombatObserver

        class Char:
            def school(self) -> None:
                return None

        result = CombatObserver._build_modifier_breakdown(Char(), "attack", (5, 3, 0), vp=0)
        assert result == []
        result = CombatObserver._build_modifier_breakdown(Char(), "attack", (), vp=0)
        assert result == []

    def test_damage_breakdown_no_get_breakdown(self):
        """A provider without get_breakdown returns an empty list (line 471)."""
        from web.adapters.combat_observer import CombatObserver

        class NoGetBreakdownProvider:
            pass

        class Char:
            def roll_parameter_provider(self):
                return NoGetBreakdownProvider()

        result = CombatObserver._damage_breakdown(
            Char(), Char(), "damage", attack_extra_rolled=0, vp=0,
        )
        assert result == []

    def test_damage_breakdown_provider_raises(self):
        """When the provider raises, the helper returns an empty list (lines 479-480)."""
        from web.adapters.combat_observer import CombatObserver

        class RaisingProvider:
            def get_breakdown(self, *a, **kw):
                raise RuntimeError("boom")

        class Char:
            def roll_parameter_provider(self):
                return RaisingProvider()

        result = CombatObserver._damage_breakdown(
            Char(), Char(), "damage", attack_extra_rolled=0, vp=0,
        )
        assert result == []

    def test_damage_breakdown_provider_returns_non_list(self):
        """A non-list return from get_breakdown is treated as empty."""
        from web.adapters.combat_observer import CombatObserver

        class NonListProvider:
            def get_breakdown(self, *a, **kw):
                return "not a list"

        class Char:
            def roll_parameter_provider(self):
                return NonListProvider()

        result = CombatObserver._damage_breakdown(
            Char(), Char(), "damage", attack_extra_rolled=0, vp=0,
        )
        assert result == []

    def test_skill_breakdown_no_get_breakdown(self):
        """Provider without get_breakdown → empty list (line 508)."""
        from web.adapters.combat_observer import CombatObserver

        class NoGetBreakdownProvider:
            pass

        class Char:
            def roll_parameter_provider(self):
                return NoGetBreakdownProvider()

        result = CombatObserver._skill_breakdown(
            Char(), Char(), "attack", (5, 3, 0), vp=0,
        )
        assert result == []

    def test_skill_breakdown_provider_raises(self):
        """get_breakdown raising → empty list (lines 515-516)."""
        from web.adapters.combat_observer import CombatObserver

        class RaisingProvider:
            def get_breakdown(self, *a, **kw):
                raise RuntimeError("boom")

        class Char:
            def roll_parameter_provider(self):
                return RaisingProvider()

        result = CombatObserver._skill_breakdown(
            Char(), Char(), "attack", (5, 3, 0), vp=0,
        )
        assert result == []

    def test_skill_breakdown_provider_returns_non_list(self):
        """Non-list return from get_breakdown → empty list."""
        from web.adapters.combat_observer import CombatObserver

        class NonListProvider:
            def get_breakdown(self, *a, **kw):
                return "not a list"

        class Char:
            def roll_parameter_provider(self):
                return NonListProvider()

        result = CombatObserver._skill_breakdown(
            Char(), Char(), "attack", (5, 3, 0), vp=0,
        )
        assert result == []

    def test_annotate_wound_check_no_info(self):
        """When the provider has no last_wound_check_info, the annotator
        sets _detail_dice = [] and zero params (lines 553-554)."""
        from web.adapters.combat_observer import CombatObserver

        class StubProvider:
            def last_wound_check_info(self):
                return None

        class Char:
            def name(self):
                return "Stub"

            def roll_provider(self):
                return StubProvider()

            def school(self):
                return None

        class Event:
            subject = Char()
            roll = 10

        observer = CombatObserver()
        evt = Event()
        # Call the private annotator directly so we hit _annotate_wound_check
        observer._annotate_wound_check(evt)
        assert evt._detail_dice == []
        assert evt._detail_params == (0, 0, 0)

    def test_annotate_wound_check_with_ishi_boost(self):
        """When _ishi_boost_value tag is set on the event, modifier is
        adjusted (lines 568-569)."""
        from web.adapters.combat_observer import CombatObserver

        class StubProvider:
            def last_wound_check_info(self):
                return {"dice": [10, 8], "rolled": 2, "kept": 1}

        class Char:
            def name(self):
                return "Stub"

            def roll_provider(self):
                return StubProvider()

            def school(self):
                return None

        class Event:
            subject = Char()
            roll = 10
            _ishi_boost_value = 5

        observer = CombatObserver()
        # Call the private annotator directly to focus the test
        evt = Event()
        observer._annotate_wound_check(evt)
        # event.roll=10, kept_sum = dice[:1] = 10 → modifier = 0
        # + ishi_boost 5 → modifier = 5
        assert evt._detail_params[2] == 5


class TestCombatObserverTakesCounterattackEvent:
    """Cover lines 211, 215, 305-317: the counterattack event branches."""

    def test_take_counterattack_action_event_triggers_annotate_take_attack(self):
        """A TakeCounterattackActionEvent fires the _annotate_take_attack branch."""
        from unittest.mock import MagicMock

        from simulation.events import TakeCounterattackActionEvent
        from web.adapters.combat_observer import CombatObserver

        action = MagicMock()
        action.subject.return_value = MagicMock(name=lambda: "Subj")
        event = TakeCounterattackActionEvent(action)
        observer = CombatObserver()
        context = MagicMock()
        context.characters.return_value = []
        observer.on_event(event, context)
        assert hasattr(event, "_detail_status")

    def test_counterattack_rolled_event_triggers_annotation(self):
        """A CounterattackRolledEvent calls _annotate_counterattack_rolled (lines 215, 305-317)."""
        from unittest.mock import MagicMock

        from simulation.events import CounterattackRolledEvent
        from web.adapters.combat_observer import CombatObserver

        action = MagicMock()
        subject = MagicMock()
        subject.name.return_value = "Subj"
        # provider with last_skill_info returning a fake dict
        provider = MagicMock()
        provider.last_skill_info.return_value = {"dice": [9, 8, 7], "rolled": 3, "kept": 2}
        subject.roll_provider.return_value = provider
        subject.school = MagicMock(return_value=None)
        subject.roll_parameter_provider = MagicMock(return_value=MagicMock(spec=[]))
        action.subject.return_value = subject

        target = MagicMock()
        target.name.return_value = "Targ"
        action.target.return_value = target

        action.skill.return_value = "counterattack"
        action.skill_roll_params.return_value = (5, 3, 0)
        action.tn.return_value = 20
        action.vp.return_value = 0
        action._ishi_boost_value = None  # ensure no ishi tag

        event = CounterattackRolledEvent(action, 25)
        observer = CombatObserver()
        observer.on_event(event, context=None)
        assert event._detail_dice == [9, 8, 7]
        assert event._detail_params == (5, 3, 0)


# Silence unused imports
_ = format_event, pytest
