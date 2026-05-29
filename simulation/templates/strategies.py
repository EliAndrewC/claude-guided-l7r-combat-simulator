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
# NOTE (2026-05-29, Kakita spec branch 014): the school-progression-designer
# proposed a revision (iaijutsu first, attack second, parry capped at 3, fire
# promoted to Dan 3, void promoted to Dan 4, earth demoted) per specs/013
# OPEN_QUESTIONS Q6 — same identity-aligned pattern Bayushi and Matsu's
# reviews flagged.  The revision was NOT applied here — applying it shifts
# the 300-XP Kakita build composition, which cascades into 19 failing tests
# in tests/test_study.py and tests/test_analysis_scripts.py:
# web/analysis/definitions/kakita_vp_study.py and kakita_void_study.py
# encode the OLD priorities structure (parry-at-every-rank) into hard-coded
# transform anchors like ``("skill", "parry", 4)``.  The revision would
# require updating those definitions in addition to the priorities themselves.
# Per the audit framing, the revision is deferred to a follow-up branch that
# can also re-anchor the Kakita study transforms.  See
# specs/013-kakita-duelist-school/OPEN_QUESTIONS.md Q6.
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
# Identity-driven ordering per spec 004 design audit:
#   - feint is the TVP economy faucet (Special Ability gives +4 on success, +1 on
#     failure). Every higher-Dan ability is fueled by VP; raise feint first.
#   - attack skill is a *literal multiplier* in the 3rd-Dan floating-bonus
#     formula ((WC_roll - damage) // 5) * skill("attack"). Raise attack ahead
#     of parry at every Dan tier.
#   - water ring at rank 3 in the Dan-3 block: WC machinery (1st/2nd/3rd Dan)
#     is fully online by Dan 3. 4th-Dan auto-raises water +1, so water-3 is the
#     correct pre-4th-Dan stopping point. After 4th Dan, water gets the -5 XP
#     school-ring discount, which dominates the max-rings phase.
#   - void at Dan-4 (rank 3) and prioritized in max-rings: 4th Dan converts VP
#     to WC free raises, 5th Dan converts VP to counter-damage. Both scale
#     linearly with max_vp.
#   - iaijutsu LAST among knacks at every Dan tier: Akodo has no iaijutsu-duel-
#     specific Special Ability. It is a knack-of-record only.
AKODO_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2 — feint first (TVP faucet), then double attack, attack ahead of
    # parry (3rd Dan multiplier), iaijutsu last.
    ("skill", "feint", 2),
    ("skill", "double attack", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "iaijutsu", 2),
    # Dan 3 — school knacks to 3, then water ring 3 (WC backbone).
    ("skill", "feint", 3),
    ("skill", "double attack", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("skill", "iaijutsu", 3),
    ("ring", "water", 3),
    # Dan 4 — school knacks to 4. Then void ring 3 (VP fuel for 4th + 5th Dan),
    # then earth/air/fire to 3 for breadth. Water-4 is auto-raised by 4th Dan
    # (free), so we do NOT buy water-4 here.
    ("skill", "feint", 4),
    ("skill", "double attack", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("skill", "iaijutsu", 4),
    ("ring", "void", 3),
    ("ring", "earth", 3),
    ("ring", "air", 3),
    ("ring", "fire", 3),
    # Dan 5 — school knacks to 5.
    ("skill", "feint", 5),
    ("skill", "double attack", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    ("skill", "iaijutsu", 5),
    # Max rings — ordered by cost: 20 > 25. Water has the school-ring -5 XP
    # discount post-4th-Dan, so water-5 (20 XP discounted) and water-6 (25 XP
    # discounted) are bought first. Void next (5th Dan counter-damage scales
    # with max_vp). Earth/air/fire fill out at full cost.
    ("ring", "water", 5),      # school ring discounted: 20
    ("ring", "void", 4),
    ("ring", "earth", 4),
    ("ring", "air", 4),
    ("ring", "fire", 4),
    ("ring", "water", 6),      # school ring discounted: 25
    ("ring", "void", 5),
    ("ring", "earth", 5),
    ("ring", "air", 5),
    ("ring", "fire", 5),
]

# Bayushi Bushi School (school_ring: fire, knacks: double attack, feint, iaijutsu)
# NOTE (2026-05-28, Bayushi spec branch 013): the school-progression-
# designer proposed a feint-first identity-aligned revision of this list
# (parry capped at 3, fire promoted to Dan 3, void promoted to Dan 4,
# earth demoted) per specs/012 OPEN_QUESTIONS Q8.  The revision was
# NOT applied — applying it shifts the 300-XP Bayushi build composition,
# which shifts the seed=1234 Bayushi-vs-Akodo calibration combat used
# by ~10 trace-observability tests.  Per the user's framing ("audit the
# existing implementation"), the audit identified the priorities as
# anti-identity (parry at every rank, no parry-keyed rules text); the
# revision is deferred to a follow-up branch that can also re-calibrate
# the dependent tests.  See specs/012-bayushi-bushi-school/OPEN_QUESTIONS.md.
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

# Hida Bushi School (school_ring: water, knacks: counterattack, double attack, iaijutsu)
# Identity-driven order (school-progression-designer, 2026-05-28):
#   - counterattack is the keystone skill: Special Ability cheapens it to 1 AP,
#     2nd Dan grants a free raise, 3rd Dan rerolls 2X dice (X = attack skill),
#     5th Dan dumps excess onto the attacker's wound check. Buy first at every tier.
#   - water is the school ring, the wound-check ring (1st Dan extra die), and
#     gets a 4th-Dan auto-raise plus -5 XP discount. Front-load: water 3 in the
#     Dan-3 ring slot, then push the discounted maxes early in the max-rings phase.
#   - attack skill is a literal multiplier in the 3rd-Dan reroll formula
#     (X dice / 2X dice). Raise ahead of parry at every Dan tier.
#   - earth ring fuels the defender identity: more LW threshold + SW headroom
#     for the 4th-Dan "burn 2 SW to reset LW" trade. Priority above void/air/fire.
#   - double attack and iaijutsu are knacks-of-record only (no Hida ability
#     specifically references them). Bought after attack/parry each tier.
HIDA_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2 — counterattack first (school identity), attack ahead of parry
    # (3rd-Dan reroll multiplier), iaijutsu/double-attack last (knacks-of-record).
    ("skill", "counterattack", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    # Dan 3 — school knacks/identity skills to 3, then water-3 (wound-check
    # backbone; 1st Dan extra die is already live, water-3 powers the kept-dice
    # roll). Earth-3 follows for LW threshold (defender soak).
    ("skill", "counterattack", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("ring", "water", 3),
    ("ring", "earth", 3),
    # Dan 4 — school knacks/identity skills to 4. Note: 4th Dan auto-raises
    # water +1 (FREE) AND grants the -5 XP discount, so we deliberately do NOT
    # pre-buy water-4 here. After Dan-4 unlock, earth-4 first for the SW-trade
    # headroom (4th Dan: "spend 2 SW to clear LW" is much safer with a larger
    # SW pool), then void/air/fire-3 for breadth.
    ("skill", "counterattack", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("ring", "earth", 4),
    ("ring", "void", 3),
    ("ring", "air", 3),
    ("ring", "fire", 3),
    # Dan 5 — school knacks/identity skills to 5 (unlocks the excess-to-WC
    # counter-damage clause).
    ("skill", "counterattack", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    # Max rings — ordered by *effective* cost after the water discount.
    # Water-5 costs 20 - 5 = 15 (cheapest available ring bump).
    # Water-6 costs 25 - 5 = 20 (ties with rank-4 bumps).
    # Earth-5 leads the 25-XP tier as the defender HP cap.
    ("ring", "water", 5),      # 15 XP after discount — school ring + WC
    ("ring", "void", 4),       # 20 XP
    ("ring", "air", 4),        # 20 XP
    ("ring", "fire", 4),       # 20 XP
    ("ring", "water", 6),      # 20 XP after discount — discounted school cap
    ("ring", "earth", 5),      # 25 XP — defender HP cap
    ("ring", "void", 5),       # 25 XP
    ("ring", "air", 5),        # 25 XP
    ("ring", "fire", 5),       # 25 XP
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
# Offensive berserker identity: front-loaded damage via lunge / double attack /
# iaijutsu. Per school-progression-designer (specs/011 OPEN_QUESTIONS Q9):
#   * Parry deprioritized (capped at rank 3) — Matsu rules text never mentions
#     defensive mechanics; parry is mandatory only as a defensive floor.
#   * Fire (school ring) promoted to Dan 3 — drives attack rolls (which scale
#     the 3rd Dan +3X WC bonus) and the always-10 initiative.
#   * Void promoted to Dan 4 — required infrastructure for the 3rd Dan
#     trigger (the WC bonus fires only on VP spends, so void 3 = 3 VP/combat
#     is identity-critical, not generic stat-padding).
#   * Earth + Air demoted to max-rings tier — neither has a Matsu rules-text
#     hook; earth (max_sw) and air (parry) are pure stat-padding.
#   * Water added at Dan 4 — supplements 1st Dan +1 WC die + attack/DA pool.
MATSU_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2 — gate via all three school knacks; attack at 2 powers 3rd-Dan +3X
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "lunge", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),       # mandatory: parry capped at attack+1
    # Dan 3 — raise attack to 3 BEFORE 3rd Dan fires (+3X bonus = +9 WC then)
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "lunge", 3),
    ("skill", "attack", 3),
    ("ring", "fire", 3),         # school ring; fuels attack rolls + always-10
    # Dan 4 — 4th Dan auto-raises fire to 4 + unlocks -5 XP discount
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "lunge", 4),
    ("skill", "attack", 4),       # +3X bonus scales -> attack=4 = +12 WC
    ("ring", "water", 3),         # 1st-Dan extra WC die + supports attack/DA pool
    ("ring", "void", 3),          # VP supply for 3rd-Dan trigger (must spend VP)
    # Dan 5 — gate via knacks only; max the +3X scaling
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "lunge", 5),
    ("skill", "attack", 5),       # +3X = +15 WC — full 5th-Dan damage engine
    ("skill", "parry", 3),        # late floor bump; capped at attack
    # Max rings — fire first (discount), then water/void for offensive economy
    ("ring", "fire", 5),          # discounted: cost 20 instead of 25
    ("ring", "fire", 6),          # discounted: cost 25 instead of 30 (school cap=6)
    ("ring", "water", 4),
    ("ring", "void", 4),
    ("ring", "earth", 3),         # baseline max_sw bump (school identity none)
    ("ring", "air", 3),           # baseline air ring (school identity none)
    # Defensive baseline padding (Batch B tuning, 2026-05-28): the
    # original list ended at this point with ~93 XP unused at the 450-XP
    # tier, leaving Matsu with earth 3 / parry 3 / air 3 — too thin
    # vs a Wave-Man baseline (earth 5 / parry 5).  Combat-simulator-
    # equivalent observation: 0/20 vs Wave-Man before this padding.
    # The school's offensive identity is preserved (lunge / double
    # attack / iaijutsu maxed first); these entries only fire after
    # all offense + the school ring are saturated.
    ("ring", "earth", 4),         # max_sw 6 -> 8
    ("ring", "earth", 5),         # max_sw 8 -> 10 (parity with Wave-Man)
    ("ring", "air", 4),
    ("ring", "water", 5),
    ("ring", "void", 5),
]

# Mirumoto Bushi School (school_ring: void, knacks: counterattack, double attack, iaijutsu)
# Mirumoto is a parry-focused school; air (the parry ring) is prioritised above
# the other elemental rings at every rank. Water is prioritised next because it
# powers wound checks (1st-Dan extra die on wound check + 5th-Dan +10 modifier
# on wound check -- two explicit Mirumoto rules clauses); fire has no Mirumoto
# rules-text basis, so it goes last among the elementals at every rank.
MIRUMOTO_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2 -- school knacks gate dan-rank advancement
    ("skill", "counterattack", 2),
    ("skill", "double attack", 2),
    ("skill", "iaijutsu", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    # Dan 3 -- air ring (parry) first
    ("skill", "counterattack", 3),
    ("skill", "double attack", 3),
    ("skill", "iaijutsu", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "air", 3),
    # Dan 4 -- Fourth Dan free-bumps void to 4 and unlocks 5-XP discount;
    # buy void -> 5 here (cheap, fuels 5th Dan +10 economy)
    ("skill", "counterattack", 4),
    ("skill", "double attack", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "air", 4),
    ("ring", "water", 3),
    ("ring", "earth", 3),
    ("ring", "void", 5),
    ("ring", "fire", 3),
    # Dan 5 -- unlocks Fifth Dan +10 modifier
    ("skill", "counterattack", 5),
    ("skill", "double attack", 5),
    ("skill", "iaijutsu", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings -- cheapest first per file convention. Within each cost tier
    # the Mirumoto identity ordering is air > water > earth > fire; void 6
    # is the discounted school-ring cap at 25 XP.
    ("ring", "water", 4),   # 20 XP -- wound-check synergy
    ("ring", "earth", 4),   # 20 XP
    ("ring", "fire", 4),    # 20 XP
    ("ring", "air", 5),     # 25 XP -- parry ring cap
    ("ring", "water", 5),   # 25 XP
    ("ring", "void", 6),    # 25 XP discounted (school-ring cap)
    ("ring", "earth", 5),   # 25 XP
    ("ring", "fire", 5),    # 25 XP
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
# Water is the school's defining lever — Special Ability is +2*Water
# on every attack roll. Spec 030 progression-designer correctly
# elevates Water ahead of non-combat knack bumps. Investigation is
# the 3rd Dan AP base (combat-relevant indirectly).
KITSUKI_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2 — combat skills + investigation up to 3 (AP base floor).
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "iaijutsu", 2),  # only combat-relevant knack
    ("skill", "investigation", 2),
    ("skill", "investigation", 3),
    ("skill", "discern honor", 2),
    ("skill", "presence", 2),
    # Dan 3 — WATER ring first (school identity lever).
    ("ring", "water", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("skill", "iaijutsu", 3),
    # Dan 4 — water auto-raised to 4 + 5-XP discount on future ranks.
    # Investigation to 5 once AP system is live (3rd Dan).
    ("skill", "investigation", 4),
    ("skill", "investigation", 5),
    ("ring", "void", 3),  # void fuels free raises on attack
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("skill", "iaijutsu", 4),
    ("skill", "discern honor", 3),
    ("skill", "presence", 3),
    # Dan 5 — max combat; water max via discount.
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    ("ring", "water", 5),
    ("skill", "iaijutsu", 5),
    # Long-tail ring fillers.
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "earth", 3),
    ("ring", "void", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 4),
    ("ring", "void", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
    ("ring", "earth", 5),
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
# acting is the school's signature combat lever — Special Ability adds
# +acting rolled dice on attack, parry, AND wound check. Air is school ring
# (parry-keep, 4th Dan discount). 5th Dan adds lowest-3 dice to all
# non-initiative rolls, rewarding kept-dice ring ranks (water for WC).
SHOSURO_ACTOR_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2 — combat skills + acting (Special Ability lever) early.
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "acting", 2),
    ("skill", "acting", 3),
    ("skill", "sincerity", 2),
    ("skill", "sincerity", 3),
    ("skill", "athletics", 2),
    ("skill", "discern honor", 2),
    ("skill", "pontificate", 2),
    # Dan 3 — first ring bump (air = school ring + parry keep).
    ("ring", "air", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("skill", "acting", 4),
    ("skill", "sincerity", 4),
    # Dan 4 — air auto-raised to 4; water for WC kept dice (5th Dan).
    ("ring", "water", 3),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("skill", "acting", 5),
    ("skill", "sincerity", 5),
    ("skill", "athletics", 3),
    ("skill", "discern honor", 3),
    ("skill", "pontificate", 3),
    # Dan 5 — max combat; air discounted via school discount.
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    ("ring", "air", 5),
    ("ring", "water", 4),
    # Long tail filler rings.
    ("ring", "fire", 3),
    ("ring", "earth", 3),
    ("ring", "void", 3),
    ("ring", "water", 5),
    ("ring", "fire", 4),
    ("ring", "earth", 4),
    ("ring", "void", 4),
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
# Identity (per spec 031):
#   - Feint is the SA enabler — the school's offense hinges on it.
#   - Tact scales the 3rd Dan Xk1 attack-roll penalty on incoming attacks.
#   - Water is the school ring (auto-raised + discounted at 4th Dan).
#   - Void fuels both the 3rd Dan VP-spend AND every attack's free raises.
IDE_PRIORITIES: list[tuple[str, str, int]] = [
    # Dan 2 — feint first (SA enabler), then attack + tact (3rd Dan multiplier).
    ("skill", "feint", 2),
    ("skill", "attack", 2),
    ("skill", "tact", 2),
    ("skill", "double attack", 2),
    ("skill", "parry", 2),
    ("skill", "worldliness", 2),
    # Dan 3 — tact-3 before other Dan-3 bumps (Xk1 → 3k1 once 3rd Dan unlocks);
    # water-3 sets up the 4th Dan auto-raise + discount.
    ("skill", "tact", 3),
    ("ring", "water", 3),
    ("skill", "feint", 3),
    ("skill", "attack", 3),
    ("skill", "double attack", 3),
    ("skill", "parry", 3),
    # Dan 4 — tact-4 keeps Xk1 scaling; void-3 fuels VP-priced abilities;
    # 4th Dan auto-raises water to 4.
    ("skill", "tact", 4),
    ("ring", "void", 3),
    ("skill", "feint", 4),
    ("skill", "attack", 4),
    ("skill", "double attack", 4),
    ("skill", "parry", 4),
    ("skill", "worldliness", 3),
    # Dan 5 — tact-5 (3rd Dan engine never stops scaling) + combat skills max.
    ("skill", "tact", 5),
    ("skill", "feint", 5),
    ("skill", "attack", 5),
    ("skill", "double attack", 5),
    ("skill", "parry", 5),
    ("skill", "worldliness", 4),
    ("skill", "worldliness", 5),
    # Max rings — water + void first (school + VP economy).
    ("ring", "water", 5),
    ("ring", "void", 4),
    ("ring", "earth", 3),
    ("ring", "fire", 3),
    ("ring", "air", 3),
    ("ring", "void", 5),
    ("ring", "earth", 4),
    ("ring", "fire", 4),
    ("ring", "air", 4),
    ("ring", "earth", 5),
    ("ring", "fire", 5),
    ("ring", "air", 5),
]

# Isawa Ishi School (school_ring: void, knacks: absorb void, kharmic spin, otherworldliness)
# Identity-driven order:
#   - precepts is the X in the 3rd-Dan Xk1 ally boost -> max early (and it's basic, so cheap).
#   - void is the school ring AND the natural "highest ring" -> bump aggressively; once it is
#     the unique highest ring, every +1 also raises max_vp by +1 (Special Ability).
#   - water powers wound check (1st-Dan extra die clause); raise next among non-school rings.
#   - earth (HP) and air (1st-Dan extra die on initiative) tie for next; fire has no clause.
#   - lowest_ring drives per-roll cap, so the max-rings phase fans the non-school rings
#     up evenly rather than spiking one of them.
ISHI_PRIORITIES: list[tuple[str, str, int]] = [
    ("skill", "precepts", 2),
    ("skill", "precepts", 3),
    # Dan 2 -- school knacks gate dan-rank advancement
    ("skill", "absorb void", 2),
    ("skill", "kharmic spin", 2),
    ("skill", "otherworldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "precepts", 4),
    # Dan 3 -- bump void first (school ring + Special-Ability highest-ring driver)
    ("skill", "absorb void", 3),
    ("skill", "kharmic spin", 3),
    ("skill", "otherworldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "void", 3),
    ("ring", "water", 3),
    ("ring", "earth", 3),
    ("skill", "precepts", 5),
    # Dan 4
    ("skill", "absorb void", 4),
    ("skill", "kharmic spin", 4),
    ("skill", "otherworldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 5),
    ("ring", "air", 3),
    ("ring", "fire", 3),
    ("ring", "water", 4),
    ("ring", "earth", 4),
    # Dan 5 -- school knacks to 5 (unlocks negate-school)
    ("skill", "absorb void", 5),
    ("skill", "kharmic spin", 5),
    ("skill", "otherworldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings -- cheapest first per file convention
    ("ring", "air", 4),
    ("ring", "fire", 4),
    ("ring", "void", 6),
    ("ring", "water", 5),
    ("ring", "earth", 5),
    ("ring", "air", 5),
    ("ring", "fire", 5),
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
    "Shosuro Actor School": SHOSURO_ACTOR_PRIORITIES,
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
