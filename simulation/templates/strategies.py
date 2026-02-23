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

# Map school names to their priority lists
SCHOOL_PRIORITIES: dict[str, list[tuple[str, str, int]]] = {
    "Akodo Bushi School": AKODO_PRIORITIES,
    "Bayushi Bushi School": BAYUSHI_PRIORITIES,
    "Kakita Bushi School": KAKITA_PRIORITIES,
    "Shiba Bushi School": SHIBA_PRIORITIES,
    "Wave Man": WAVE_MAN_PRIORITIES,
}

# Short name to full school/profession name
SCHOOL_NAMES: dict[str, str] = {
    "akodo": "Akodo Bushi School",
    "bayushi": "Bayushi Bushi School",
    "kakita": "Kakita Bushi School",
    "shiba": "Shiba Bushi School",
    "wave_man": "Wave Man",
}

XP_TIERS: list[int] = [150, 200, 250, 300, 350, 400, 450]
