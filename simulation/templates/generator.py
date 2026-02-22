"""Template generator for standard character builds.

Uses CharacterBuilder to validate each purchase, producing CharacterConfig
objects that can be serialized to YAML template files.
"""

import os

import yaml

from simulation.character_builder import CharacterBuilder
from simulation.schools.factory import get_school
from simulation.templates.strategies import (
    SCHOOL_NAMES,
    SCHOOL_PRIORITIES,
    WAVE_MAN_ABILITIES,
    XP_TIERS,
)
from web.models import CharacterConfig


def generate_template(school_key: str, total_xp: int) -> CharacterConfig:
    """Generate a CharacterConfig for a school/profession at the given XP tier.

    Args:
        school_key: Short name (e.g. "kakita", "wave_man")
        total_xp: Total XP budget for the character

    Returns:
        CharacterConfig with the optimal build for that tier
    """
    school_name = SCHOOL_NAMES[school_key]
    priorities = SCHOOL_PRIORITIES[school_name]
    is_profession = school_key == "wave_man"

    name = f"{school_key.replace('_', ' ').title()} {total_xp}"
    builder = CharacterBuilder().with_xp(total_xp).with_name(name)

    if is_profession:
        builder = builder.with_profession()
    else:
        school = get_school(school_name)
        builder = builder.with_school(school)

    # Execute priority purchases
    for category, item_name, target_rank in priorities:
        if category == "skill":
            current = builder.character().skill(item_name)
            if current >= target_rank:
                continue
            try:
                builder.buy_skill(item_name, target_rank)
            except ValueError:
                continue
        elif category == "ring":
            current = builder.character().ring(item_name)
            if current >= target_rank:
                continue
            try:
                builder.buy_ring(item_name, target_rank)
            except ValueError:
                continue

    # For Wave Man, take profession abilities
    if is_profession:
        for ability_name in WAVE_MAN_ABILITIES:
            try:
                builder.take_ability(ability_name)
            except RuntimeError:
                break

    character = builder.build()

    # Extract final state into CharacterConfig
    rings = {}
    for ring_name in ["air", "earth", "fire", "water", "void"]:
        rings[ring_name] = character.ring(ring_name)

    skills: dict[str, int] = {}
    for skill_name in ["attack", "parry"]:
        rank = character.skill(skill_name)
        if rank > 0:
            skills[skill_name] = rank

    # Include school knacks and other combat skills
    combat_skills = [
        "counterattack", "double attack", "feint", "iaijutsu", "lunge",
    ]
    for skill_name in combat_skills:
        rank = character.skill(skill_name)
        if rank > 0:
            skills[skill_name] = rank

    # Build abilities dict for profession characters
    abilities: dict[str, int] = {}
    if is_profession and character.profession() is not None:
        for ability_name in WAVE_MAN_ABILITIES:
            level = character.profession().ability(ability_name)
            if level > 0:
                abilities[ability_name] = level

    config = CharacterConfig(
        name=name,
        xp=total_xp,
        char_type="profession" if is_profession else "school",
        school="" if is_profession else school_name,
        rings=rings,
        skills=skills,
        advantages=[],
        disadvantages=[],
        strategies={},
        abilities=abilities,
        template_tier=str(total_xp),
        template_earned_xp=total_xp,
        template_school=school_name if not is_profession else "Wave Man",
    )
    return config


def write_template_yaml(config: CharacterConfig, output_path: str) -> None:
    """Write a CharacterConfig to a YAML template file."""
    data: dict = {"name": config.name, "xp": config.xp}

    if config.char_type == "profession":
        data["profession"] = "Wave Man"
    elif config.school:
        data["school"] = config.school

    data["rings"] = dict(config.rings)
    if config.skills:
        data["skills"] = dict(config.skills)
    if config.advantages:
        data["advantages"] = list(config.advantages)
    if config.disadvantages:
        data["disadvantages"] = list(config.disadvantages)
    if config.strategies:
        data["strategies"] = dict(config.strategies)
    if config.abilities:
        data["abilities"] = dict(config.abilities)

    # Template metadata
    data["template_tier"] = config.template_tier
    data["template_earned_xp"] = config.template_earned_xp
    data["template_school"] = config.template_school

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def generate_all_templates(base_dir: str | None = None) -> list[CharacterConfig]:
    """Generate all 35 template files (5 schools x 7 XP tiers).

    Args:
        base_dir: Base directory for template output.
                  Defaults to simulation/data/templates/

    Returns:
        List of all generated CharacterConfig objects
    """
    if base_dir is None:
        base_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates"
        )

    configs: list[CharacterConfig] = []
    for school_key in SCHOOL_NAMES:
        for xp_tier in XP_TIERS:
            config = generate_template(school_key, xp_tier)
            filename = f"{school_key}_{xp_tier}.yaml"
            output_path = os.path.join(base_dir, school_key, filename)
            write_template_yaml(config, output_path)
            configs.append(config)

    return configs


if __name__ == "__main__":
    configs = generate_all_templates()
    print(f"Generated {len(configs)} templates")
    for config in configs:
        print(f"  {config.name}: {config.template_school} @ {config.template_tier} XP")
