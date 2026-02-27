"""Per-school XP spending priorities for character template generation.

Each school has an ordered list of (category, name, target_rank) tuples.
The generator iterates through these in order, attempting each purchase.
If a purchase is already satisfied or unaffordable, it is skipped.

Priority order:
  school knacks to next Dan > attack/parry > critical rings > max skills > max rings

Within the "max rings" section, purchases are ordered by cost (cheapest first)
to ensure monotonic progression: a higher XP tier always has stats >= a lower tier.
  rank 3 raises (15 XP) > rank 4 raises (20 XP) > rank 5 raises (25 XP) > rank 6 (30 XP)
"""

# Kakita Bushi School (school_ring: fire, knacks: double attack, iaijutsu, lunge)
KAKITA_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2: school knacks to 2
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "lunge", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3: school knacks to 3
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "lunge", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4: school knacks to 4 (triggers fire+1 auto-raise and 5 XP discount)
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "lunge", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "air", 3),
    ("ring", "water", 3),
    ("ring", "earth", 4),
    # Dan 5: school knacks to 5
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "lunge", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings — ordered by cost: 20 > 25
    ("ring", "fire", 5),       # school ring discounted: 20
    ("ring", "void", 4),
    ("ring", "air", 4),
    ("ring", "water", 4),
    ("ring", "earth", 5),
    ("ring", "fire", 6),       # school ring discounted: 25
    ("ring", "void", 5),
    ("ring", "air", 5),
    ("ring", "water", 5),
]

# Akodo Bushi School (school_ring: water, knacks: double attack, feint, iaijutsu)
AKODO_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "feint", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "feint", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "feint", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "feint", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings — ordered by cost: 20 > 25
    ("ring", "water", 5),      # school ring discounted: 20
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),      # school ring discounted: 25
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Bayushi Bushi School (school_ring: fire, knacks: double attack, feint, iaijutsu)
BAYUSHI_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "feint", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "feint", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "feint", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "feint", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings — ordered by cost: 20 > 25
    ("ring", "fire", 5),       # school ring discounted: 20
    ("ring", "void", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "fire", 6),       # school ring discounted: 25
    ("ring", "void", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Daidoji Yojimbo School (school_ring: water, knacks: counterattack, double attack, iaijutsu)
DAIDOJI_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "counterattack", 2),
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "counterattack", 3),
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "counterattack", 4),
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "counterattack", 5),
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings — ordered by cost: 20 > 25
    ("ring", "water", 5),      # school ring discounted: 20
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),      # school ring discounted: 25
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Hida Bushi School (school_ring: water, knacks: counterattack, iaijutsu, lunge)
HIDA_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "counterattack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "lunge", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "counterattack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "lunge", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "counterattack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "lunge", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "counterattack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "lunge", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings — ordered by cost: 20 > 25
    ("ring", "water", 5),      # school ring discounted: 20
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),      # school ring discounted: 25
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Shiba Bushi School (school_ring: air, knacks: counterattack, double attack, iaijutsu)
SHIBA_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "counterattack", 2),
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "counterattack", 3),
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "counterattack", 4),
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "counterattack", 5),
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings — ordered by cost: 20 > 25
    ("ring", "air", 5),        # school ring discounted: 20
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "earth", 5),
    ("ring", "air", 6),        # school ring discounted: 25
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "water", 5),
]

# Wave Man (profession, no school)
# Ordered to ensure monotonic progression: skills before rings at each tier,
# all rank-3 rings before rank-4, etc.
WAVE_MAN_PRIORITIES: list[tuple[str, str, int]] = [
    # Tier 1: skills to 2, rings to 3
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("ring", "earth", 3),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "void", 3),
    ("ring", "air", 3),
    # Tier 2: skills to 3, rings to 4
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 4),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "void", 4),
    ("ring", "air", 4),
    # Tier 3: skills to 4-5, rings to 5
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    ("ring", "earth", 5),
    ("ring", "fire", 5),
    ("ring", "water", 5),
    ("ring", "void", 5),
    ("ring", "air", 5),
]

# Wave Man profession ability priorities (taken in order as they become available)
WAVE_MAN_ABILITIES: list[str] = [
    "wound check bonus",
    "weapon damage bonus",
    "wound check bonus",
    "weapon damage bonus",
    "rolled damage bonus",
    "initiative bonus",
    "rolled damage bonus",
    "initiative bonus",
    "crippled bonus",
    "crippled bonus",
    "missed attack bonus",
    "missed attack bonus",
    "parry penalty",
    "parry penalty",
    "failed parry damage bonus",
    "failed parry damage bonus",
    "damage penalty",
    "damage penalty",
    "wound check penalty",
    "wound check penalty",
]

# Ninja (profession, no school)
# Ordered to ensure monotonic progression: skills before rings at each tier,
# all rank-3 rings before rank-4, etc.
NINJA_PRIORITIES: list[tuple[str, str, int]] = [
    # Tier 1: skills to 2, rings to 3
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("ring", "earth", 3),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "void", 3),
    ("ring", "air", 3),
    # Tier 2: skills to 3, rings to 4
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 4),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "void", 4),
    ("ring", "air", 4),
    # Tier 3: skills to 4-5, rings to 5
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    ("ring", "earth", 5),
    ("ring", "fire", 5),
    ("ring", "water", 5),
    ("ring", "void", 5),
    ("ring", "air", 5),
]

# Ninja profession ability priorities (taken in order as they become available)
# Combat abilities first: defense, offense, then non-combat
NINJA_ABILITIES: list[str] = [
    "defense bonus",
    "attack bonus",
    "defense bonus",
    "attack bonus",
    "damage keeping bonus",
    "wound check ninja bonus",
    "damage keeping bonus",
    "wound check ninja bonus",
    "initiative reduction",
    "initiative reduction",
    "damage reduction",
    "damage reduction",
    "attack penalty",
    "attack penalty",
    "sincerity bonus",
    "sincerity bonus",
    "stealth (invisibility)",
    "stealth (invisibility)",
    "stealth (memorability)",
    "stealth (memorability)",
]

# Hiruma Scout School (school_ring: air, knacks: double attack, feint, iaijutsu)
HIRUMA_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "feint", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "feint", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "feint", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "feint", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "air", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "earth", 5),
    ("ring", "air", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "water", 5),
]

# Isawa Duelist School (school_ring: water, knacks: double attack, iaijutsu, lunge)
ISAWA_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "lunge", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "lunge", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "lunge", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "lunge", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Kuni Witch Hunter School (school_ring: earth, knacks: detect taint, iaijutsu, presence)
# investigation set to 5 at all tiers (non-combat but AP base skill)
KUNI_PRIORITIES: list[tuple[str, str, int]] = [
    # investigation for AP system (bought early)
    ("skill", "investigation", 2),
    ("skill", "investigation", 3),
    # Dan 2
    ("skill", "detect taint", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "presence", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "investigation", 4),
    # Dan 3
    ("skill", "detect taint", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "presence", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "void", 3),
    ("skill", "investigation", 5),
    # Dan 4
    ("skill", "detect taint", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "presence", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "void", 4),
    # Dan 5
    ("skill", "detect taint", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "presence", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "earth", 5),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "void", 5),
    ("ring", "earth", 6),
    ("ring", "fire", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Matsu Bushi School (school_ring: fire, knacks: double attack, iaijutsu, lunge)
MATSU_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "lunge", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "lunge", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "lunge", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "lunge", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "fire", 5),
    ("ring", "void", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "fire", 6),
    ("ring", "void", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Mirumoto Bushi School (school_ring: void, knacks: counterattack, double attack, iaijutsu)
MIRUMOTO_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "counterattack", 2),
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "counterattack", 3),
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "counterattack", 4),
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "counterattack", 5),
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "void", 5),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "void", 6),
    ("ring", "fire", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Otaku Bushi School (school_ring: fire, knacks: double attack, iaijutsu, lunge)
OTAKU_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "lunge", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "lunge", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "lunge", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "lunge", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "fire", 5),
    ("ring", "void", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "fire", 6),
    ("ring", "void", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Shinjo Bushi School (school_ring: air, knacks: double attack, iaijutsu, lunge)
SHINJO_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "lunge", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "lunge", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "lunge", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "lunge", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "air", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "earth", 5),
    ("ring", "air", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "water", 5),
]

# Brotherhood of Shinsei Monk School (school_ring: water, knacks: conviction, otherworldliness, worldliness)
# precepts set to 5 at all tiers (non-combat but AP base skill)
MONK_PRIORITIES: list[tuple[str, str, int]] = [
    # precepts for AP system (bought early)
    ("skill", "precepts", 2),
    ("skill", "precepts", 3),
    # Dan 2
    ("skill", "conviction", 2),
    ("skill", "otherworldliness", 2),
    ("skill", "worldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "precepts", 4),
    # Dan 3
    ("skill", "conviction", 3),
    ("skill", "otherworldliness", 3),
    ("skill", "worldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "precepts", 5),
    # Dan 4
    ("skill", "conviction", 4),
    ("skill", "otherworldliness", 4),
    ("skill", "worldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "conviction", 5),
    ("skill", "otherworldliness", 5),
    ("skill", "worldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Courtier School (school_ring: air, knacks: discern honor, oppose social, worldliness)
# tact set to 5 at all tiers (non-combat but AP base skill)
COURTIER_PRIORITIES: list[tuple[str, str, int]] = [
    # tact for AP system (bought early)
    ("skill", "tact", 2),
    ("skill", "tact", 3),
    # Dan 2
    ("skill", "discern honor", 2),
    ("skill", "oppose social", 2),
    ("skill", "worldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "tact", 4),
    # Dan 3
    ("skill", "discern honor", 3),
    ("skill", "oppose social", 3),
    ("skill", "worldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "tact", 5),
    # Dan 4
    ("skill", "discern honor", 4),
    ("skill", "oppose social", 4),
    ("skill", "worldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "discern honor", 5),
    ("skill", "oppose social", 5),
    ("skill", "worldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "air", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "earth", 5),
    ("ring", "air", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "water", 5),
]

# Doji Artisan School (school_ring: water, knacks: counterattack, oppose social, worldliness)
# culture set to 5 at all tiers (non-combat but AP base skill)
DOJI_ARTISAN_PRIORITIES: list[tuple[str, str, int]] = [
    # culture for AP system (bought early)
    ("skill", "culture", 2),
    ("skill", "culture", 3),
    # Dan 2
    ("skill", "counterattack", 2),
    ("skill", "oppose social", 2),
    ("skill", "worldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "culture", 4),
    # Dan 3
    ("skill", "counterattack", 3),
    ("skill", "oppose social", 3),
    ("skill", "worldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "culture", 5),
    # Dan 4
    ("skill", "counterattack", 4),
    ("skill", "oppose social", 4),
    ("skill", "worldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "counterattack", 5),
    ("skill", "oppose social", 5),
    ("skill", "worldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Ikoma Bard School (school_ring: water, knacks: discern honor, oppose knowledge, oppose social)
# bragging set to 5 at all tiers (non-combat but AP base skill)
IKOMA_BARD_PRIORITIES: list[tuple[str, str, int]] = [
    # bragging for AP system (bought early)
    ("skill", "bragging", 2),
    ("skill", "bragging", 3),
    # Dan 2
    ("skill", "discern honor", 2),
    ("skill", "oppose knowledge", 2),
    ("skill", "oppose social", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "bragging", 4),
    # Dan 3
    ("skill", "discern honor", 3),
    ("skill", "oppose knowledge", 3),
    ("skill", "oppose social", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "bragging", 5),
    # Dan 4
    ("skill", "discern honor", 4),
    ("skill", "oppose knowledge", 4),
    ("skill", "oppose social", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "discern honor", 5),
    ("skill", "oppose knowledge", 5),
    ("skill", "oppose social", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Kitsuki Magistrate School (school_ring: water, knacks: discern honor, iaijutsu, presence)
# investigation set to 5 at all tiers (non-combat but AP base skill)
KITSUKI_PRIORITIES: list[tuple[str, str, int]] = [
    # investigation for AP system (bought early)
    ("skill", "investigation", 2),
    ("skill", "investigation", 3),
    # Dan 2
    ("skill", "discern honor", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "presence", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "investigation", 4),
    # Dan 3
    ("skill", "discern honor", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "presence", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "investigation", 5),
    # Dan 4
    ("skill", "discern honor", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "presence", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "discern honor", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "presence", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Merchant School (school_ring: water, knacks: discern honor, oppose knowledge, worldliness)
# sincerity set to 5 at all tiers (non-combat but AP base skill)
MERCHANT_PRIORITIES: list[tuple[str, str, int]] = [
    # sincerity for AP system (bought early)
    ("skill", "sincerity", 2),
    ("skill", "sincerity", 3),
    # Dan 2
    ("skill", "discern honor", 2),
    ("skill", "oppose knowledge", 2),
    ("skill", "worldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "sincerity", 4),
    # Dan 3
    ("skill", "discern honor", 3),
    ("skill", "oppose knowledge", 3),
    ("skill", "worldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "sincerity", 5),
    # Dan 4
    ("skill", "discern honor", 4),
    ("skill", "oppose knowledge", 4),
    ("skill", "worldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "discern honor", 5),
    ("skill", "oppose knowledge", 5),
    ("skill", "worldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Shosuro Actor School (school_ring: air, knacks: athletics, discern honor, pontificate)
# sincerity set to 5 at all tiers (non-combat but AP base skill)
# acting bought early (combat-relevant: extra rolled dice on attack/parry/wound check)
SHOSURO_PRIORITIES: list[tuple[str, str, int]] = [
    # sincerity for AP system (bought early)
    ("skill", "sincerity", 2),
    ("skill", "sincerity", 3),
    # acting is combat-relevant (extra rolled dice from special ability)
    ("skill", "acting", 2),
    # Dan 2
    ("skill", "athletics", 2),
    ("skill", "discern honor", 2),
    ("skill", "pontificate", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "sincerity", 4),
    ("skill", "acting", 3),
    # Dan 3
    ("skill", "athletics", 3),
    ("skill", "discern honor", 3),
    ("skill", "pontificate", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "sincerity", 5),
    ("skill", "acting", 4),
    # Dan 4
    ("skill", "athletics", 4),
    ("skill", "discern honor", 4),
    ("skill", "pontificate", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "earth", 4),
    ("skill", "acting", 5),
    # Dan 5
    ("skill", "athletics", 5),
    ("skill", "discern honor", 5),
    ("skill", "pontificate", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "air", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "earth", 5),
    ("ring", "air", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "water", 5),
]

# Yogo Warden School (school_ring: earth, knacks: double attack, feint, iaijutsu)
YOGO_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "feint", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "feint", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "void", 3),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "feint", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "void", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "feint", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "earth", 5),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "void", 5),
    ("ring", "earth", 6),
    ("ring", "fire", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Ide Diplomat School (school_ring: water, knacks: double attack, feint, worldliness)
# tact bought early (needed for 3rd dan VP-subtract mechanic)
IDE_PRIORITIES: list[tuple[str, str, int]] = [
    # tact for 3rd dan (bought early)
    ("skill", "tact", 2),
    ("skill", "tact", 3),
    # Dan 2
    ("skill", "double attack", 2),
    ("skill", "feint", 2),
    ("skill", "worldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "tact", 4),
    # Dan 3
    ("skill", "double attack", 3),
    ("skill", "feint", 3),
    ("skill", "worldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "tact", 5),
    # Dan 4
    ("skill", "double attack", 4),
    ("skill", "feint", 4),
    ("skill", "worldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "double attack", 5),
    ("skill", "feint", 5),
    ("skill", "worldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Isawa Ishi School (school_ring: void, knacks: absorb void, kharmic spin, otherworldliness)
# precepts bought early (needed for 3rd dan ally boost)
ISHI_PRIORITIES: list[tuple[str, str, int]] = [
    # precepts for 3rd dan (bought early)
    ("skill", "precepts", 2),
    ("skill", "precepts", 3),
    # Dan 2
    ("skill", "absorb void", 2),
    ("skill", "kharmic spin", 2),
    ("skill", "otherworldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "precepts", 4),
    # Dan 3
    ("skill", "absorb void", 3),
    ("skill", "kharmic spin", 3),
    ("skill", "otherworldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "precepts", 5),
    # Dan 4
    ("skill", "absorb void", 4),
    ("skill", "kharmic spin", 4),
    ("skill", "otherworldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "absorb void", 5),
    ("skill", "kharmic spin", 5),
    ("skill", "otherworldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "void", 5),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "void", 6),
    ("ring", "fire", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Priest School (school_ring: water, knacks: conviction, otherworldliness, pontificate)
# precepts bought early (needed for 3rd dan dice pool size)
PRIEST_PRIORITIES: list[tuple[str, str, int]] = [
    # precepts for 3rd dan (bought early)
    ("skill", "precepts", 2),
    ("skill", "precepts", 3),
    # Dan 2
    ("skill", "conviction", 2),
    ("skill", "otherworldliness", 2),
    ("skill", "pontificate", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "precepts", 4),
    # Dan 3
    ("skill", "conviction", 3),
    ("skill", "otherworldliness", 3),
    ("skill", "pontificate", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "precepts", 5),
    # Dan 4
    ("skill", "conviction", 4),
    ("skill", "otherworldliness", 4),
    ("skill", "pontificate", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "conviction", 5),
    ("skill", "otherworldliness", 5),
    ("skill", "pontificate", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "water", 6),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Togashi Ise Zumi School (school_ring: void, knacks: athletics, conviction, dragon tattoo)
# precepts bought early (AP base skill for 3rd dan 4x athletics AP)
ISE_ZUMI_PRIORITIES: list[tuple[str, str, int]] = [
    # precepts for AP system (bought early)
    ("skill", "precepts", 2),
    ("skill", "precepts", 3),
    # Dan 2
    ("skill", "athletics", 2),
    ("skill", "conviction", 2),
    ("skill", "dragon tattoo", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "precepts", 4),
    # Dan 3
    ("skill", "athletics", 3),
    ("skill", "conviction", 3),
    ("skill", "dragon tattoo", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "earth", 3),
    ("skill", "precepts", 5),
    # Dan 4
    ("skill", "athletics", 4),
    ("skill", "conviction", 4),
    ("skill", "dragon tattoo", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "fire", 3),
    ("ring", "water", 3),
    ("ring", "air", 3),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "athletics", 5),
    ("skill", "conviction", 5),
    ("skill", "dragon tattoo", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings
    ("ring", "void", 5),
    ("ring", "fire", 4),
    ("ring", "water", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "void", 6),
    ("ring", "fire", 5),
    ("ring", "water", 5),
    ("ring", "air", 5),
]

# Map school names to their priority lists
SCHOOL_PRIORITIES: dict[str, list[tuple[str, str, int]]] = {
    "Akodo Bushi School": AKODO_PRIORITIES,
    "Bayushi Bushi School": BAYUSHI_PRIORITIES,
    "Brotherhood of Shinsei Monk School": MONK_PRIORITIES,
    "Courtier School": COURTIER_PRIORITIES,
    "Daidoji Yojimbo School": DAIDOJI_PRIORITIES,
    "Doji Artisan School": DOJI_ARTISAN_PRIORITIES,
    "Hida Bushi School": HIDA_PRIORITIES,
    "Hiruma Scout School": HIRUMA_PRIORITIES,
    "Ide Diplomat School": IDE_PRIORITIES,
    "Ikoma Bard School": IKOMA_BARD_PRIORITIES,
    "Isawa Duelist School": ISAWA_PRIORITIES,
    "Isawa Ishi School": ISHI_PRIORITIES,
    "Kakita Bushi School": KAKITA_PRIORITIES,
    "Kitsuki Magistrate School": KITSUKI_PRIORITIES,
    "Kuni Witch Hunter School": KUNI_PRIORITIES,
    "Matsu Bushi School": MATSU_PRIORITIES,
    "Merchant School": MERCHANT_PRIORITIES,
    "Mirumoto Bushi School": MIRUMOTO_PRIORITIES,
    "Otaku Bushi School": OTAKU_PRIORITIES,
    "Priest School": PRIEST_PRIORITIES,
    "Shiba Bushi School": SHIBA_PRIORITIES,
    "Shinjo Bushi School": SHINJO_PRIORITIES,
    "Shosuro Actor School": SHOSURO_PRIORITIES,
    "Togashi Ise Zumi School": ISE_ZUMI_PRIORITIES,
    "Ninja": NINJA_PRIORITIES,
    "Wave Man": WAVE_MAN_PRIORITIES,
    "Yogo Warden School": YOGO_PRIORITIES,
}

# Short name to full school/profession name
SCHOOL_NAMES: dict[str, str] = {
    "akodo": "Akodo Bushi School",
    "bayushi": "Bayushi Bushi School",
    "courtier": "Courtier School",
    "daidoji": "Daidoji Yojimbo School",
    "doji_artisan": "Doji Artisan School",
    "hida": "Hida Bushi School",
    "hiruma": "Hiruma Scout School",
    "ide": "Ide Diplomat School",
    "ikoma_bard": "Ikoma Bard School",
    "isawa": "Isawa Duelist School",
    "ishi": "Isawa Ishi School",
    "kakita": "Kakita Bushi School",
    "kitsuki": "Kitsuki Magistrate School",
    "kuni": "Kuni Witch Hunter School",
    "matsu": "Matsu Bushi School",
    "merchant": "Merchant School",
    "mirumoto": "Mirumoto Bushi School",
    "monk": "Brotherhood of Shinsei Monk School",
    "otaku": "Otaku Bushi School",
    "priest": "Priest School",
    "shiba": "Shiba Bushi School",
    "shinjo": "Shinjo Bushi School",
    "shosuro": "Shosuro Actor School",
    "ise_zumi": "Togashi Ise Zumi School",
    "ninja": "Ninja",
    "wave_man": "Wave Man",
    "yogo": "Yogo Warden School",
}

XP_TIERS: list[int] = [150, 200, 250, 300, 350, 400, 450]
