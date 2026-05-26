import os
from typing import Any

import yaml

from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.schools.factory import get_school
from simulation.strategies.factory import get_strategy
from web.models import CharacterConfig


def config_to_character(config: CharacterConfig) -> Character:
    """Build a Character from a CharacterConfig, replicating CharacterReader.read() sequence."""
    builder: Any = CharacterBuilder().with_xp(config.xp)
    builder.with_name(config.name)

    # choose type
    if config.char_type == "profession":
        builder = builder.with_profession()
    elif config.char_type == "school":
        school = get_school(config.school)
        # Apply per-character school choices BEFORE with_school() triggers
        # initialize_school(), which runs apply_special_ability and
        # apply_rank_one_ability.  See specs/003-school-choices/spec.md FR-003.
        for key, value in config.school_choices.items():
            school.set_choice(key, value)
        builder = builder.with_school(school)
    else:
        builder = builder.generic()

    # take disadvantages first (they refund XP)
    for disadvantage in config.disadvantages:
        builder.take_disadvantage(disadvantage.lower())

    # take advantages
    for advantage in config.advantages:
        builder.take_advantage(advantage.lower())

    # buy skills (attack first to avoid parry constraint)
    skills = dict(config.skills)
    if "attack" in skills:
        attack_rank = skills.pop("attack")
        builder.buy_skill("attack", attack_rank)
    for skill, rank in skills.items():
        builder.buy_skill(skill, rank)

    # buy rings one rank at a time so per-purchase discounts apply correctly
    for ring, rank in config.rings.items():
        current = builder.character().ring(ring)
        for target in range(current + 1, rank + 1):
            builder.buy_ring(ring, target)

    # set strategies
    for event, strategy_name in config.strategies.items():
        strategy = get_strategy(strategy_name)
        builder.set_strategy(event, strategy)

    # take profession abilities
    for name, level in config.abilities.items():
        for _ in range(level):
            builder.take_ability(name)

    character: Character = builder.build()
    return character


def yaml_to_config(yaml_str: str) -> CharacterConfig:
    """Parse a YAML string into a CharacterConfig."""
    data = yaml.safe_load(yaml_str)
    config = CharacterConfig()
    config.name = data.get("name", "")
    config.xp = int(data.get("xp", 100))

    if "profession" in data:
        config.char_type = "profession"
    elif "school" in data:
        config.char_type = "school"
        config.school = data["school"]
    else:
        config.char_type = "generic"

    config.rings = data.get("rings", {"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2})
    config.skills = data.get("skills", {})
    config.advantages = data.get("advantages", [])
    config.disadvantages = data.get("disadvantages", [])
    config.strategies = data.get("strategies", {})
    config.abilities = data.get("abilities", {})
    # Per-character build-time school choices (see FR-001 of
    # specs/003-school-choices/spec.md).  Absent => empty dict => all defaults.
    config.school_choices = data.get("school_choices", {})

    # Optional template metadata
    config.template_tier = str(data.get("template_tier", ""))
    config.template_earned_xp = int(data.get("template_earned_xp", 0))
    config.template_school = str(data.get("template_school", ""))

    return config


def load_data_directory(path: str) -> list[CharacterConfig]:
    """Load all character YAML files from a directory (excluding groups.yaml)."""
    configs = []
    for fname in os.listdir(path):
        if fname == "groups.yaml":
            continue
        fpath = os.path.join(path, fname)
        if not os.path.isfile(fpath):
            continue
        if not fname.endswith((".yaml", ".yml")):
            continue
        with open(fpath) as f:
            yaml_str = f.read()
        config = yaml_to_config(yaml_str)
        configs.append(config)
    return configs


def load_template_directory(path: str) -> list[CharacterConfig]:
    """Load all character YAML files from a directory tree recursively."""
    configs = []
    for dirpath, _dirnames, filenames in os.walk(path):
        for fname in sorted(filenames):
            if not fname.endswith((".yaml", ".yml")):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath) as f:
                yaml_str = f.read()
            config = yaml_to_config(yaml_str)
            configs.append(config)
    return configs
