import streamlit as st

from simulation.mechanics.advantages import ADVANTAGES
from simulation.mechanics.disadvantages import DISADVANTAGES
from simulation.mechanics.skills import ADVANCED_SKILLS, BASIC_SKILLS
from web.adapters.character_adapter import config_to_character
from web.models import CharacterConfig
from web.state import save_state

SCHOOL_NAMES = ["Akodo Bushi School", "Bayushi Bushi School", "Daidoji Yojimbo School", "Hida Bushi School", "Kakita Bushi School", "Shiba Bushi School"]
WEAPON_NAMES = ["katana", "wakizashi", "tanto", "yari", "club", "unarmed", "gongfu"]
PROFESSION_ABILITIES = [
    "crippled bonus", "damage penalty", "failed parry damage bonus",
    "initiative bonus", "missed attack bonus", "parry penalty",
    "rolled damage bonus", "weapon damage bonus", "wound check bonus",
    "wound check penalty",
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

st.title("Characters")

# --- Create new character ---
st.header("Create New Character")
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

# --- Character list ---
st.header("Current Characters")
if st.session_state.characters:
    for char_name, config in st.session_state.characters.items():
        with st.expander(f"{config.name} ({config.char_type}, {config.xp} XP)"):
            st.write(f"**Rings:** {config.rings}")
            st.write(f"**Skills:** {config.skills}")
            if config.school:
                st.write(f"**School:** {config.school}")
            if config.advantages:
                st.write(f"**Advantages:** {', '.join(config.advantages)}")
            if config.disadvantages:
                st.write(f"**Disadvantages:** {', '.join(config.disadvantages)}")
            if config.abilities:
                st.write(f"**Abilities:** {config.abilities}")
            if st.button(f"Delete {config.name}", key=f"del_{config.name}"):
                del st.session_state.characters[config.name]
                save_state()
                st.rerun()
else:
    st.info("No characters loaded. Load from data directory or create a new one.")
