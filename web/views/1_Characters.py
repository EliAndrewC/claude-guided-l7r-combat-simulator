import streamlit as st

from simulation.mechanics.advantages import ADVANTAGES
from simulation.mechanics.disadvantages import DISADVANTAGES
from simulation.mechanics.skills import ADVANCED_SKILLS, BASIC_SKILLS
from simulation.schools.factory import get_school
from web.adapters.character_adapter import config_to_character
from web.models import CharacterConfig
from web.state import save_state
from web.views._chronicle import (
    clan_for,
    render_character_card,
    render_masthead,
    render_section_head,
)

_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}


def _school_rank(config: CharacterConfig) -> int | None:
    if not config.school:
        return None
    try:
        school = get_school(config.school)
    except ValueError:
        return None
    return min(config.skills.get(k, 0) for k in school.school_knacks())


def _character_card_dict(config: CharacterConfig) -> dict[str, object]:
    """Pack a CharacterConfig into the dict shape ``render_character_card``
    expects."""
    clan_name, clan_kanji = clan_for(config.school)
    rank = _school_rank(config)
    rank_str = _ORDINAL.get(rank, f"{rank}th Dan") if rank is not None else None
    if rank_str:
        rank_str = f"{rank_str} Dan"
    ribbon = []
    for s in ("attack", "parry", "iaijutsu", "counterattack",
              "double attack", "feint", "lunge"):
        if s in config.skills:
            ribbon.append(f"{s.upper().replace(' ', '·')} {config.skills[s]}")
    weapon = getattr(config, "weapon", None)
    if weapon:
        ribbon.append(weapon.upper())
    return {
        "clan": clan_name,
        "clan_kanji": clan_kanji,
        "name": config.name,
        "school": config.school or f"{config.char_type.title()} character",
        "rank": rank_str,
        "xp": config.xp,
        "rings": config.rings,
        "ribbon": ribbon,
        "advantages": config.advantages,
        "disadvantages": config.disadvantages,
    }

SCHOOL_NAMES = [
    "Akodo Bushi School", "Bayushi Bushi School",
    "Brotherhood of Shinsei Monk School", "Courtier School",
    "Daidoji Yojimbo School", "Doji Artisan School",
    "Hida Bushi School", "Hiruma Scout School",
    "Ide Diplomat School", "Ikoma Bard School",
    "Isawa Duelist School", "Isawa Ishi School",
    "Kakita Bushi School", "Kitsuki Magistrate School",
    "Kuni Witch Hunter School", "Matsu Bushi School",
    "Merchant School", "Mirumoto Bushi School",
    "Otaku Bushi School", "Priest School",
    "Shiba Bushi School", "Shinjo Bushi School",
    "Shosuro Actor School", "Togashi Ise Zumi School",
    "Yogo Warden School",
]
WEAPON_NAMES = ["katana", "wakizashi", "tanto", "yari", "club", "unarmed", "gongfu"]
PROFESSION_ABILITIES = [
    "attack bonus", "attack penalty", "crippled bonus",
    "damage keeping bonus", "damage penalty", "damage reduction",
    "defense bonus", "failed parry damage bonus",
    "initiative bonus", "initiative reduction",
    "missed attack bonus", "parry penalty",
    "rolled damage bonus", "sincerity bonus",
    "stealth (invisibility)", "stealth (memorability)",
    "weapon damage bonus", "wound check bonus",
    "wound check ninja bonus", "wound check penalty",
]
STRATEGIES_BY_EVENT = {
    "action": [
        "AlwaysAttackActionStrategy",
        "HoldOneActionStrategy",
        "PlainAttackStrategy",
        "StingyPlainAttackStrategy",
        "UniversalAttackStrategy",
    ],
    "attack": [
        "KakitaAttackStrategy",
        "KakitaAttackStrategy05",
        "KakitaInterruptAttackStrategy",
        "KakitaInterruptAttackStrategy05",
        "KakitaNoVPAttackStrategy",
        "KakitaNoVPInterruptAttackStrategy",
    ],
    "parry": [
        "AlwaysParryStrategy",
        "KakitaParryStrategy",
        "NeverParryStrategy",
        "ReluctantParryStrategy",
    ],
    "wound_check": [
        "StingyWoundCheckStrategy",
        "WoundCheckStrategy",
        "WoundCheckStrategy02",
        "WoundCheckStrategy04",
        "WoundCheckStrategy05",
        "WoundCheckStrategy08",
    ],
    "light_wounds": [
        "AlwaysKeepLightWoundsStrategy",
        "KeepLightWoundsStrategy",
        "NeverKeepLightWoundsStrategy",
    ],
}

render_masthead(active="Characters")
render_section_head("I", "Characters", "the roster")

# --- Create new character ---
render_section_head("II", "Create New Character", "")
with st.form("new_character_form"):
    name = st.text_input("Name")
    xp = st.number_input("XP", min_value=1, value=200, step=10)
    char_type = st.selectbox("Type", ["generic", "school", "profession"])
    school = st.selectbox("School", [""] + SCHOOL_NAMES)
    weapon = st.selectbox("Weapon", WEAPON_NAMES)

    st.subheader("Rings")
    ring_cols = st.columns(5)
    rings = {}
    for i, ring_name in enumerate(["air", "earth", "fire", "water", "void"]):
        with ring_cols[i]:
            rings[ring_name] = st.slider(ring_name.capitalize(), 2, 6, 2)

    st.subheader("Combat Skills")
    combat_cols = st.columns(3)
    skills = {}
    combat_skills = ["attack", "parry", "counterattack", "double attack", "feint", "iaijutsu", "lunge"]
    for i, skill_name in enumerate(combat_skills):
        with combat_cols[i % 3]:
            val = st.number_input(skill_name, min_value=0, max_value=5, value=0, key=f"skill_{skill_name}")
            if val > 0:
                skills[skill_name] = val

    with st.expander("Other Skills"):
        other_skills = [s for s in BASIC_SKILLS + ADVANCED_SKILLS if s not in combat_skills]
        other_cols = st.columns(3)
        for i, skill_name in enumerate(other_skills):
            with other_cols[i % 3]:
                val = st.number_input(skill_name, min_value=0, max_value=5, value=0, key=f"skill_{skill_name}")
                if val > 0:
                    skills[skill_name] = val

    advantages = st.multiselect("Advantages", sorted(ADVANTAGES.keys()))
    disadvantages = st.multiselect("Disadvantages", sorted(DISADVANTAGES.keys()))

    with st.expander("Strategies"):
        strategies = {}
        for event_name, event_strategies in STRATEGIES_BY_EVENT.items():
            strat = st.selectbox(f"Strategy for {event_name}", ["(default)"] + event_strategies, key=f"strat_{event_name}")
            if strat != "(default)":
                strategies[event_name] = strat

    abilities = {}
    if char_type == "profession":
        with st.expander("Profession Abilities"):
            ability_cols = st.columns(2)
            for i, ability_name in enumerate(PROFESSION_ABILITIES):
                with ability_cols[i % 2]:
                    level = st.number_input(ability_name, min_value=0, max_value=2, value=0, key=f"ability_{ability_name}")
                    if level > 0:
                        abilities[ability_name] = level

    submitted = st.form_submit_button("Create Character")
    if submitted:
        if not name:
            st.error("Name is required")
        else:
            config = CharacterConfig(
                name=name,
                xp=xp,
                char_type=char_type,
                school=school if char_type == "school" else "",
                rings=rings,
                skills=skills,
                weapon=weapon,
                advantages=advantages,
                disadvantages=disadvantages,
                strategies=strategies,
                abilities=abilities,
            )
            try:
                config_to_character(config)
                st.session_state.characters[name] = config
                save_state()
                st.success(f"Created character: {name}")
            except Exception as e:
                st.error(f"Invalid character: {e}")

# --- Character list — grouped by clan, rendered as sumi-e cards ---
render_section_head(
    "III", "The Roster",
    f"{len(st.session_state.characters)} bushi" if st.session_state.characters else "",
)
if st.session_state.characters:
    # Group characters by clan so the roster reads like a clan registry.
    by_clan: dict[str, list[CharacterConfig]] = {}
    for char_name, config in st.session_state.characters.items():
        clan_name, _ = clan_for(config.school)
        by_clan.setdefault(clan_name, []).append(config)

    for clan_name in sorted(by_clan.keys()):
        members = by_clan[clan_name]
        clan_kanji = clan_for(members[0].school)[1]
        st.markdown(
            "<div style='margin-top:24px;display:flex;align-items:baseline;gap:12px;"
            "border-bottom:1px solid var(--ink-faded);padding-bottom:8px;'>"
            f"<span style='font-family:Shippori Mincho,serif;font-size:24px;color:var(--seal);'>{clan_kanji}</span>"
            f"<span style='font-family:Shippori Mincho,serif;font-size:14px;letter-spacing:0.36em;text-transform:uppercase;color:var(--ink);'>{clan_name}</span>"
            f"<span style='font-family:JetBrains Mono,monospace;font-size:11px;color:var(--ink-faded);'>{len(members)}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, config in enumerate(sorted(members, key=lambda c: c.name)):
            with cols[i % 2]:
                render_character_card(_character_card_dict(config))
                if st.button(f"⚔  Retire {config.name}", key=f"del_{config.name}"):
                    del st.session_state.characters[config.name]
                    save_state()
                    st.rerun()
else:
    st.info("No bushi mustered. Load from data directory or create a new one above.")
