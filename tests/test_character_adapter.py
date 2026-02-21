import os

import pytest

from simulation.schools.kakita_school import KakitaRollParameterProvider
from web.adapters.character_adapter import config_to_character, load_data_directory, yaml_to_config
from web.models import CharacterConfig


class TestConfigToCharacter:
    def test_generic_character(self):
        config = CharacterConfig(
            name="TestGeneric",
            xp=200,
            char_type="generic",
            rings={"air": 3, "earth": 3, "fire": 2, "water": 2, "void": 2},
            skills={"attack": 3, "parry": 3},
        )
        character = config_to_character(config)
        assert character.name() == "TestGeneric"
        assert character.ring("air") == 3
        assert character.ring("earth") == 3
        assert character.skill("attack") == 3
        assert character.skill("parry") == 3
        assert character.school() is None
        assert character.profession() is None

    def test_school_character(self):
        config = CharacterConfig(
            name="TestAkodo",
            xp=370,
            char_type="school",
            school="Akodo Bushi School",
            rings={"air": 3, "earth": 5, "fire": 5, "water": 6, "void": 5},
            skills={"attack": 5, "double attack": 5, "feint": 5, "iaijutsu": 5, "parry": 5},
        )
        character = config_to_character(config)
        assert character.name() == "TestAkodo"
        assert character.ring("water") == 6
        assert character.skill("attack") == 5
        assert character.school() is not None
        assert character.school().name() == "Akodo Bushi School"

    def test_profession_character(self):
        config = CharacterConfig(
            name="TestWaveMan",
            xp=9001,
            char_type="profession",
            rings={"air": 3, "earth": 5, "fire": 5, "water": 5, "void": 5},
            skills={"attack": 5, "parry": 5},
            abilities={"crippled bonus": 2, "wound check bonus": 2},
        )
        character = config_to_character(config)
        assert character.name() == "TestWaveMan"
        assert character.profession() is not None
        assert character.skill("attack") == 5

    def test_character_with_advantages(self):
        config = CharacterConfig(
            name="TestAdvantaged",
            xp=1000,
            char_type="generic",
            rings={"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2},
            skills={"attack": 1},
            advantages=["fierce", "great destiny"],
        )
        character = config_to_character(config)
        assert "fierce" in character.advantages()
        assert "great destiny" in character.advantages()

    def test_character_with_disadvantages(self):
        config = CharacterConfig(
            name="TestDisadvantaged",
            xp=1000,
            char_type="generic",
            rings={"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2},
            skills={"attack": 1},
            disadvantages=["proud", "contrary"],
        )
        character = config_to_character(config)
        assert "proud" in character.disadvantages()
        assert "contrary" in character.disadvantages()

    def test_character_with_strategies(self):
        config = CharacterConfig(
            name="TestStrategies",
            xp=1000,
            char_type="generic",
            rings={"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2},
            skills={"attack": 1},
            strategies={"wound_check": "NeverKeepLightWoundsStrategy"},
        )
        character = config_to_character(config)
        assert character is not None

    def test_kakita_fifth_dan_abilities_applied(self):
        """Verify Kakita 2nd Dan free raise and 4th Dan damage provider are applied."""
        config = CharacterConfig(
            name="TestKakita",
            xp=370,
            char_type="school",
            school="Kakita Bushi School",
            rings={"air": 3, "earth": 4, "fire": 5, "water": 4, "void": 5},
            skills={
                "attack": 5,
                "double attack": 5,
                "iaijutsu": 5,
                "lunge": 5,
                "parry": 5,
            },
        )
        character = config_to_character(config)
        # 2nd Dan: free raise on iaijutsu rolls (+5 modifier)
        assert character.modifier(None, "iaijutsu") >= 5
        # 4th Dan: KakitaRollParameterProvider set for iaijutsu damage
        assert isinstance(character.roll_parameter_provider(), KakitaRollParameterProvider)

    def test_not_enough_xp_raises(self):
        config = CharacterConfig(
            name="TestBroke",
            xp=1,
            char_type="generic",
            rings={"air": 5, "earth": 5, "fire": 5, "water": 5, "void": 5},
            skills={"attack": 5},
        )
        with pytest.raises(ValueError):
            config_to_character(config)


class TestYamlToConfig:
    def test_school_yaml(self):
        yaml_str = """name: Akodo
school: Akodo Bushi School
xp: 370
rings:
  air: 3
  earth: 5
  fire: 5
  water: 6
  void: 5
skills:
  attack: 5
  double attack: 5
  feint: 5
  iaijutsu: 5
  parry: 5
"""
        config = yaml_to_config(yaml_str)
        assert config.name == "Akodo"
        assert config.char_type == "school"
        assert config.school == "Akodo Bushi School"
        assert config.xp == 370
        assert config.rings["water"] == 6
        assert config.skills["attack"] == 5

    def test_profession_yaml(self):
        yaml_str = """name: Mighty Kyō'ude
profession: Wave Man
xp: 9001
rings:
  air: 3
  earth: 5
  fire: 5
  water: 5
  void: 5
skills:
  attack: 5
  parry: 5
abilities:
  crippled bonus: 2
  wound check bonus: 2
advantages:
  - fierce
  - great destiny
disadvantages:
  - contrary
  - proud
"""
        config = yaml_to_config(yaml_str)
        assert config.name == "Mighty Kyō'ude"
        assert config.char_type == "profession"
        assert config.xp == 9001
        assert config.abilities["crippled bonus"] == 2
        assert "fierce" in config.advantages
        assert "contrary" in config.disadvantages

    def test_generic_yaml(self):
        yaml_str = """name: Generic
xp: 200
rings:
  air: 3
  earth: 3
  fire: 2
  water: 2
  void: 2
skills:
  attack: 3
  parry: 3
"""
        config = yaml_to_config(yaml_str)
        assert config.name == "Generic"
        assert config.char_type == "generic"


class TestKakitaYamlData:
    def test_kakita_yaml_builds_fifth_dan(self):
        """Regression test: kakita.yaml should have all school knacks at 5."""
        data_dir = os.path.join(os.path.dirname(__file__), "..", "simulation", "data")
        configs = load_data_directory(data_dir)
        kakita_configs = [c for c in configs if c.name == "Kakita"]
        assert len(kakita_configs) == 1
        config = kakita_configs[0]
        # All Kakita school knacks must be present
        assert config.skills.get("double attack") == 5
        assert config.skills.get("iaijutsu") == 5
        assert config.skills.get("lunge") == 5
        # Build and verify rank abilities are applied
        character = config_to_character(config)
        assert character.modifier(None, "iaijutsu") >= 5
        assert isinstance(character.roll_parameter_provider(), KakitaRollParameterProvider)


class TestLoadDataDirectory:
    def test_load_data_directory(self):
        data_dir = os.path.join(os.path.dirname(__file__), "..", "simulation", "data")
        configs = load_data_directory(data_dir)
        assert len(configs) >= 1
        names = [c.name for c in configs]
        assert "Akodo" in names or "Bayushi" in names

    def test_all_configs_have_names(self):
        data_dir = os.path.join(os.path.dirname(__file__), "..", "simulation", "data")
        configs = load_data_directory(data_dir)
        for config in configs:
            assert config.name != ""

    def test_all_configs_buildable(self):
        data_dir = os.path.join(os.path.dirname(__file__), "..", "simulation", "data")
        configs = load_data_directory(data_dir)
        for config in configs:
            character = config_to_character(config)
            assert character.name() == config.name
