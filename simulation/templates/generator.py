"""Template generator for standard character builds.

Uses CharacterBuilder to validate each purchase, producing CharacterConfig
objects that can be serialized to YAML template files.

Reserves 20% of XP for non-combat skills and tracks spending by category
to produce XP breakdown comments in the output YAML.
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

COMBAT_XP_FRACTION = 0.8

SCHOOL_KNACK_LOOKUP: dict[str, list[str]] = {
    "Akodo Bushi School": ["double attack", "feint", "iaijutsu"],
    "Bayushi Bushi School": ["double attack", "feint", "iaijutsu"],
    "Kakita Bushi School": ["double attack", "iaijutsu", "lunge"],
    "Shiba Bushi School": ["counterattack", "double attack", "iaijutsu"],
}

SCHOOL_RING_LOOKUP: dict[str, str] = {
    "Akodo Bushi School": "water",
    "Bayushi Bushi School": "fire",
    "Kakita Bushi School": "fire",
    "Shiba Bushi School": "air",
}


def _consolidate_details(
    details: list[tuple[str, int, int, int]],
) -> list[tuple[str, int, int, int]]:
    """Consolidate incremental purchases into final ranges per item."""
    by_name: dict[str, list[int]] = {}
    order: list[str] = []
    for name, from_rank, to_rank, cost in details:
        if name not in by_name:
            by_name[name] = [from_rank, to_rank, cost]
            order.append(name)
        else:
            by_name[name][1] = to_rank
            by_name[name][2] += cost
    return [(name, vals[0], vals[1], vals[2]) for name, vals in
            ((n, by_name[n]) for n in order)]


def _format_breakdown_comments(breakdown: dict) -> str:
    """Format XP breakdown as YAML comment lines."""
    lines = []
    total = breakdown["total_xp"]
    budget = breakdown["combat_budget"]
    non_combat = breakdown["non_combat_xp"]
    spent = breakdown["combat_spent"]

    lines.append(f"# XP Breakdown ({total} XP total):")
    lines.append(
        f"#   Combat budget: {budget} XP (80%), "
        f"Non-combat reserve: {non_combat} XP (20%)"
    )

    for note in breakdown["free_notes"]:
        lines.append(f"#   Free: {note}")

    ring_xp = breakdown["ring_xp"]
    consolidated_rings = _consolidate_details(breakdown["ring_details"])
    if consolidated_rings:
        parts = [
            f"{n} {fr}\u2192{tr} ({c})" for n, fr, tr, c in consolidated_rings
        ]
        lines.append(f"#   Rings ({ring_xp} XP): {', '.join(parts)}")

    knack_xp = breakdown["knack_xp"]
    consolidated_knacks = _consolidate_details(breakdown["knack_details"])
    if consolidated_knacks:
        parts = [
            f"{n} {fr}\u2192{tr} ({c})" for n, fr, tr, c in consolidated_knacks
        ]
        lines.append(f"#   School knacks ({knack_xp} XP): {', '.join(parts)}")

    ap_xp = breakdown["ap_xp"]
    consolidated_ap = _consolidate_details(breakdown["ap_details"])
    if consolidated_ap:
        parts = [
            f"{n} {fr}\u2192{tr} ({c})" for n, fr, tr, c in consolidated_ap
        ]
        lines.append(f"#   Attack/Parry ({ap_xp} XP): {', '.join(parts)}")

    lines.append(f"#   Combat total: {spent} XP")
    lines.append("#")
    return "\n".join(lines) + "\n"


def generate_template(
    school_key: str,
    total_xp: int,
    priorities: list[tuple[str, str, int]] | None = None,
) -> tuple[CharacterConfig, dict]:
    """Generate a CharacterConfig for a school/profession at the given XP tier.

    Reserves 20% of XP for non-combat skills. School characters get attack
    and parry at rank 1 for free.

    Args:
        school_key: Short name (e.g. "kakita", "wave_man")
        total_xp: Total XP budget for the character
        priorities: Optional custom priority list. If None, uses the
            default school priorities from SCHOOL_PRIORITIES.

    Returns:
        Tuple of (CharacterConfig, breakdown dict with XP tracking)
    """
    school_name = SCHOOL_NAMES[school_key]
    if priorities is None:
        priorities = SCHOOL_PRIORITIES[school_name]
    is_profession = school_key == "wave_man"

    combat_budget = int(total_xp * COMBAT_XP_FRACTION)
    non_combat_xp = total_xp - combat_budget

    name = school_key.replace("_", " ").title()
    builder = CharacterBuilder().with_xp(total_xp).with_name(name)

    if is_profession:
        builder = builder.with_profession()
        school_knacks: list[str] = []
        school_ring = None
    else:
        school = get_school(school_name)
        builder = builder.with_school(school)
        school_knacks = SCHOOL_KNACK_LOOKUP.get(school_name, [])
        school_ring = SCHOOL_RING_LOOKUP.get(school_name)

    # Track XP spending by category
    ring_details: list[tuple[str, int, int, int]] = []
    knack_details: list[tuple[str, int, int, int]] = []
    ap_details: list[tuple[str, int, int, int]] = []
    free_notes: list[str] = []

    if not is_profession and school_ring:
        free_notes.append(
            f"{school_ring} ring starts at 3 (school ring); "
            "school knacks start at 1; attack/parry start at 1"
        )
    else:
        free_notes.append("attack/parry start at 1")

    initial_school_ring_val = (
        builder.character().ring(school_ring) if school_ring else None
    )

    # Execute priority purchases within combat budget
    for category, item_name, target_rank in priorities:
        if category == "skill":
            current = builder.character().skill(item_name)
            if current >= target_rank:
                continue
            cost = builder.calculate_skill_cost(item_name, target_rank)
            if builder.xp_spent() + cost > combat_budget:
                continue
            try:
                builder.buy_skill(item_name, target_rank)
            except ValueError:
                continue
            if item_name in ("attack", "parry"):
                ap_details.append((item_name, current, target_rank, cost))
            elif item_name in school_knacks:
                knack_details.append((item_name, current, target_rank, cost))

        elif category == "ring":
            current = builder.character().ring(item_name)
            if current >= target_rank:
                continue
            try:
                cost = builder.calculate_ring_cost(item_name, target_rank)
            except ValueError:
                continue
            if builder.xp_spent() + cost > combat_budget:
                continue
            try:
                builder.buy_ring(item_name, target_rank)
            except ValueError:
                continue
            ring_details.append((item_name, current, target_rank, cost))

    # Detect free 4th Dan ring raise
    if school_ring and initial_school_ring_val is not None:
        final_school_ring_val = builder.character().ring(school_ring)
        bought_ranks = sum(
            tr - fr
            for n, fr, tr, _ in ring_details
            if n == school_ring
        )
        free_ranks = (
            final_school_ring_val - initial_school_ring_val - bought_ranks
        )
        if free_ranks > 0:
            free_notes.append(f"{school_ring} +1 free at 4th Dan")

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

    ring_xp = sum(c for _, _, _, c in ring_details)
    knack_xp = sum(c for _, _, _, c in knack_details)
    ap_xp = sum(c for _, _, _, c in ap_details)

    breakdown = {
        "total_xp": total_xp,
        "combat_budget": combat_budget,
        "non_combat_xp": non_combat_xp,
        "ring_xp": ring_xp,
        "knack_xp": knack_xp,
        "ap_xp": ap_xp,
        "combat_spent": ring_xp + knack_xp + ap_xp,
        "ring_details": ring_details,
        "knack_details": knack_details,
        "ap_details": ap_details,
        "free_notes": free_notes,
    }

    return config, breakdown


def write_template_yaml(
    config: CharacterConfig,
    output_path: str,
    breakdown: dict | None = None,
) -> None:
    """Write a CharacterConfig to a YAML template file with XP breakdown."""
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
        if breakdown:
            f.write(_format_breakdown_comments(breakdown))
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
            config, breakdown = generate_template(school_key, xp_tier)
            filename = f"{school_key}_{xp_tier}.yaml"
            output_path = os.path.join(base_dir, school_key, filename)
            write_template_yaml(config, output_path, breakdown)
            configs.append(config)

    return configs


if __name__ == "__main__":
    configs = generate_all_templates()
    print(f"Generated {len(configs)} templates")
    for config in configs:
        print(
            f"  {config.name}: {config.template_school} "
            f"@ {config.template_tier} XP"
        )
