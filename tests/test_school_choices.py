"""Tests for the generic school-choices override mechanism.

Phase 1 (infrastructure): adds a per-character build-time choice store on
``BaseSchool`` plus YAML round-tripping via ``CharacterConfig.school_choices``.
No school actually consumes the stored choices yet -- that is Phase 2 / 3.

Spec: specs/003-school-choices/spec.md (FR-001, FR-002, FR-003, FR-008).
"""

from dataclasses import fields

from simulation.schools.akodo_school import AkodoBushiSchool
from simulation.schools.base import BaseSchool
from simulation.schools.ide_school import IdeDiplomatSchool
from simulation.schools.ishi_school import IsawaIshiSchool
from web.adapters.character_adapter import config_to_character
from web.models import CharacterConfig


class TestCharacterConfigSchoolChoices:
    """FR-001: CharacterConfig gains ``school_choices: dict[str, Any]``."""

    def test_school_choices_field_exists(self) -> None:
        # Verifies the dataclass field is present so YAML can populate it.
        names = {f.name for f in fields(CharacterConfig)}
        assert "school_choices" in names

    def test_school_choices_defaults_to_empty_dict(self) -> None:
        # FR-001 default factory; backward compatible with existing YAMLs.
        config = CharacterConfig()
        assert config.school_choices == {}

    def test_school_choices_independent_between_instances(self) -> None:
        # Default-factory protects against shared-mutable-default footgun.
        a = CharacterConfig()
        b = CharacterConfig()
        a.school_choices["first_dan_extra_rolled"] = ["parry", "wound check"]
        assert b.school_choices == {}

    def test_school_choices_round_trips_through_construction(self) -> None:
        # FR-001: the field must round-trip arbitrary keys/values.
        choices = {
            "first_dan_extra_rolled": ["parry", "wound check"],
            "school_ring": "fire",
        }
        config = CharacterConfig(school_choices=choices)
        assert config.school_choices == choices


class TestBaseSchoolChoices:
    """FR-002: BaseSchool exposes set_choice/choice/has_choice per instance."""

    def test_set_and_read_choice(self) -> None:
        school = AkodoBushiSchool()
        school.set_choice("first_dan_extra_rolled", ["parry", "wound check"])
        assert school.choice("first_dan_extra_rolled") == ["parry", "wound check"]

    def test_choice_returns_default_when_unset(self) -> None:
        school = AkodoBushiSchool()
        assert school.choice("nonexistent_key") is None
        assert school.choice("nonexistent_key", "fallback") == "fallback"
        assert school.choice("nonexistent_key", []) == []

    def test_has_choice_reports_membership(self) -> None:
        school = AkodoBushiSchool()
        assert not school.has_choice("first_dan_extra_rolled")
        school.set_choice("first_dan_extra_rolled", ["parry", "wound check"])
        assert school.has_choice("first_dan_extra_rolled")

    def test_multiple_set_choice_calls_overwrite(self) -> None:
        school = IsawaIshiSchool()
        school.set_choice("school_ring", "fire")
        school.set_choice("school_ring", "air")
        assert school.choice("school_ring") == "air"

    def test_set_choice_stores_multiple_keys(self) -> None:
        school = IdeDiplomatSchool()
        school.set_choice("school_ring", "fire")
        school.set_choice("second_dan_free_raise", "parry")
        assert school.choice("school_ring") == "fire"
        assert school.choice("second_dan_free_raise") == "parry"

    def test_choices_are_isolated_between_school_instances(self) -> None:
        # Critical: two Ide characters in the same combat must not share choices.
        first = IdeDiplomatSchool()
        second = IdeDiplomatSchool()
        first.set_choice("school_ring", "fire")
        assert second.choice("school_ring") is None
        assert not second.has_choice("school_ring")

    def test_choices_initialized_on_construction(self) -> None:
        # The _choices dict must exist on a freshly constructed school so
        # ``has_choice`` works before any set_choice call.
        school = AkodoBushiSchool()
        assert school.has_choice("anything") is False
        assert school.choice("anything", "default") == "default"


class TestAdapterPassesChoicesToSchool:
    """FR-003: config_to_character forwards school_choices to school.set_choice
    BEFORE the school's apply_*_ability chain runs.
    """

    def test_choices_applied_to_school_instance(self) -> None:
        config = CharacterConfig(
            name="ChoiceIshi",
            xp=200,
            char_type="school",
            school="Isawa Ishi School",
            rings={"air": 2, "earth": 2, "fire": 3, "water": 3, "void": 2},
            skills={"precepts": 1},
            school_choices={
                "first_dan_extra_rolled": ["parry", "wound check"],
                "second_dan_free_raise": "parry",
            },
        )
        character = config_to_character(config)
        school = character.school()
        assert isinstance(school, BaseSchool)
        assert school.choice("first_dan_extra_rolled") == ["parry", "wound check"]
        assert school.choice("second_dan_free_raise") == "parry"

    def test_empty_school_choices_is_noop(self) -> None:
        # FR-008 backward compatibility: an empty / missing school_choices
        # must behave identically to existing YAMLs.
        config = CharacterConfig(
            name="DefaultAkodo",
            xp=200,
            char_type="school",
            school="Akodo Bushi School",
            rings={"air": 2, "earth": 2, "fire": 3, "water": 3, "void": 2},
            skills={"attack": 1, "parry": 1},
        )
        character = config_to_character(config)
        school = character.school()
        assert isinstance(school, BaseSchool)
        # No choices were set => has_choice returns False for every key.
        assert not school.has_choice("first_dan_extra_rolled")
        assert not school.has_choice("school_ring")

    def test_choices_set_before_apply_special_ability(self) -> None:
        # FR-003: choices must be visible to the school *during* the
        # apply_*_ability chain so subclass overrides (Phase 2/3) can read
        # them. We verify by patching apply_special_ability to capture the
        # state of self._choices at the moment it runs.
        captured: dict[str, object] = {}

        class _RecordingIshi(IsawaIshiSchool):
            def apply_special_ability(self, character: object) -> None:
                captured.update(self._choices)
                super().apply_special_ability(character)

        # We inject our subclass into the adapter through a monkey-patch of
        # the module-level ``get_school`` name.
        import web.adapters.character_adapter as adapter_mod

        original_get_school = getattr(adapter_mod, "get_school")

        def fake_get_school(name: str) -> object:
            if name == "Isawa Ishi School":
                return _RecordingIshi()
            return original_get_school(name)

        setattr(adapter_mod, "get_school", fake_get_school)
        try:
            config = CharacterConfig(
                name="EarlyChoiceIshi",
                xp=200,
                char_type="school",
                school="Isawa Ishi School",
                rings={"air": 2, "earth": 2, "fire": 3, "water": 3, "void": 2},
                skills={"precepts": 1},
                school_choices={"first_dan_extra_rolled": ["parry", "wound check"]},
            )
            config_to_character(config)
        finally:
            setattr(adapter_mod, "get_school", original_get_school)

        assert captured.get("first_dan_extra_rolled") == ["parry", "wound check"]
