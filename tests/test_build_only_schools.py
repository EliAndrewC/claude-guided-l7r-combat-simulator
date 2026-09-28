"""Build-only stub schools: Kitsune Warden, Mantis Wave-Treader, Suzume Overseer.

They must build through the template generator (the character sheet's NPC
generator depends on it) and must be refused by everything that fights.
"""

import os
import tempfile

import pytest

from simulation.character_builder import CharacterBuilder
from simulation.character_file import CharacterReader
from simulation.schools.build_only_schools import (
    KitsuneWardenSchool,
    MantisWaveTreaderSchool,
    SuzumeOverseerSchool,
)
from simulation.schools.factory import get_combat_school, get_school, is_build_only
from simulation.templates.generator import (
    SCHOOL_KNACK_LOOKUP,
    SCHOOL_RING_LOOKUP,
    build_only_school_keys,
    generate_all_templates,
    generate_template,
)
from simulation.templates.strategies import SCHOOL_NAMES, SCHOOL_PRIORITIES, XP_TIERS
from web.adapters.character_adapter import config_to_character

STUBS = {
    "kitsune_warden": (KitsuneWardenSchool, "Kitsune Warden School", ["absorb void", "commune", "iaijutsu"]),
    "mantis": (MantisWaveTreaderSchool, "Mantis Wave-Treader School", ["athletics", "iaijutsu", "worldliness"]),
    "suzume": (SuzumeOverseerSchool, "Suzume Overseer School", ["oppose social", "pontificate", "worldliness"]),
}


@pytest.mark.parametrize("key", list(STUBS))
def test_registered_everywhere_the_generator_looks(key: str) -> None:
    cls, name, knacks = STUBS[key]
    assert SCHOOL_NAMES[key] == name
    assert name in SCHOOL_PRIORITIES
    assert isinstance(get_school(name), cls)
    assert SCHOOL_KNACK_LOOKUP[name] == knacks
    assert SCHOOL_RING_LOOKUP[name] == get_school(name).school_ring()
    assert get_school(name).school_knacks() == knacks
    assert get_school(name).name() == name


def test_build_only_keys_are_exactly_the_stubs() -> None:
    assert build_only_school_keys() == frozenset(STUBS)


@pytest.mark.parametrize("key", list(STUBS))
def test_is_build_only_and_refused_for_combat(key: str) -> None:
    _, name, _ = STUBS[key]
    assert is_build_only(name)
    with pytest.raises(ValueError, match="build-only"):
        get_combat_school(name)


def test_real_schools_are_not_build_only() -> None:
    assert not is_build_only("Kakita Bushi School")
    assert get_combat_school("Kakita Bushi School").name() == "Kakita Bushi School"


@pytest.mark.parametrize("key", list(STUBS))
@pytest.mark.parametrize("xp", [150, 175, 200, 260, 300, 380, 450, 600])
def test_generates_at_any_xp(key: str, xp: int) -> None:
    config, breakdown = generate_template(key, xp)
    _, name, knacks = STUBS[key]
    assert config.school == name
    assert breakdown["combat_spent"] <= breakdown["combat_budget"]
    for knack in knacks:
        assert config.skills[knack] >= 1
    assert config.skills["attack"] >= 1
    assert config.skills["parry"] >= 1
    assert config.skills["parry"] <= config.skills["attack"] + 1


@pytest.mark.parametrize("key", list(STUBS))
def test_never_worse_at_higher_xp(key: str) -> None:
    previous = None
    for xp in range(150, 601, 10):
        config, _ = generate_template(key, xp)
        if previous is not None:
            for ring, rank in previous.rings.items():
                assert config.rings[ring] >= rank, (xp, ring)
            for skill, rank in previous.skills.items():
                assert config.skills.get(skill, 0) >= rank, (xp, skill)
        previous = config


@pytest.mark.parametrize("key", list(STUBS))
def test_fourth_dan_raises_the_school_ring(key: str) -> None:
    _, name, _ = STUBS[key]
    school = get_school(name)
    ring = school.school_ring()
    builder = CharacterBuilder().with_xp(1000).with_name("T").with_school(school)
    assert builder.character().ring(ring) == 3
    for knack in school.school_knacks():
        builder.buy_skill(knack, 4)
    assert builder.character().ring(ring) == 4


def test_config_to_character_refuses_a_stub() -> None:
    config, _ = generate_template("mantis", 300)
    with pytest.raises(ValueError, match="build-only"):
        config_to_character(config)


def test_character_file_refuses_a_stub() -> None:
    text = "name: Mantis\nxp: 200\nschool: Mantis Wave-Treader School\n"
    with pytest.raises(ValueError, match="build-only"):
        CharacterReader().read(text)


def test_generate_all_templates_skips_the_stubs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        configs = generate_all_templates(tmp)
        assert not any(c.school in {name for _, name, _ in STUBS.values()} for c in configs)
        assert len(configs) == (len(SCHOOL_NAMES) - len(STUBS)) * len(XP_TIERS)
        for key in STUBS:
            assert not os.path.exists(os.path.join(tmp, key))


class TestChoices:
    def test_school_ring_choice_is_honored(self) -> None:
        school = MantisWaveTreaderSchool()
        school.set_choice("school_ring", "void")
        assert school.school_ring() == "void"

    def test_kitsune_cannot_take_void(self) -> None:
        school = KitsuneWardenSchool()
        school.set_choice("school_ring", "void")
        with pytest.raises(ValueError):
            school.school_ring()

    def test_suzume_is_always_water(self) -> None:
        school = SuzumeOverseerSchool()
        school.set_choice("school_ring", "fire")
        with pytest.raises(ValueError):
            school.school_ring()

    def test_first_and_second_dan_defaults_follow_the_rules(self) -> None:
        assert MantisWaveTreaderSchool().extra_rolled() == ["initiative", "athletics", "wound check"]
        assert SuzumeOverseerSchool().extra_rolled() == ["precepts", "commerce", "wound check"]
        assert len(KitsuneWardenSchool().extra_rolled()) == 3
        for cls in (KitsuneWardenSchool, MantisWaveTreaderSchool, SuzumeOverseerSchool):
            assert len(cls().free_raise_skills()) == 1

    def test_dan_choices_are_overridable(self) -> None:
        school = KitsuneWardenSchool()
        school.set_choice("first_dan_extra_rolled", ["attack", "parry", "initiative"])
        school.set_choice("second_dan_free_raise", "parry")
        assert school.extra_rolled() == ["attack", "parry", "initiative"]
        assert school.free_raise_skills() == ["parry"]

    def test_unsimulated_abilities_are_no_ops(self) -> None:
        builder = CharacterBuilder().with_xp(1000).with_name("T").with_school(SuzumeOverseerSchool())
        character = builder.character()
        school = SuzumeOverseerSchool()
        school.apply_special_ability(character)
        school.apply_rank_three_ability(character)
        school.apply_rank_five_ability(character)
