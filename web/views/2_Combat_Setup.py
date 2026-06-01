from typing import Any

import streamlit as st

from simulation.schools.factory import get_school
from web.models import CharacterConfig, GroupConfig
from web.state import save_state
from web.views._chronicle import (
    clan_for,
    format_school_rank,
    render_fight_card,
    render_masthead,
    render_section_head,
)


def _school_rank(config: CharacterConfig) -> int | None:
    if not config.school:
        return None
    try:
        school = get_school(config.school)
    except ValueError:
        return None
    return min(config.skills.get(k, 0) for k in school.school_knacks())


def _fight_card_side(config: CharacterConfig) -> dict[str, Any]:
    clan_name = clan_for(config.school)
    rank = _school_rank(config)
    parts = [config.school or "Ronin"]
    rank_str = format_school_rank(rank)
    if rank_str is not None:
        parts.append(rank_str)
    parts.append(f"{config.xp} xp")
    ribbon = []
    if "attack" in config.skills:
        ribbon.append(f"ATK {config.skills['attack']}")
    if "parry" in config.skills:
        ribbon.append(f"PARRY {config.skills['parry']}")
    if "iaijutsu" in config.skills:
        ribbon.append(f"IAI {config.skills['iaijutsu']}")
    weapon = getattr(config, "weapon", None) or "katana"
    weapon_dice = {"katana": "4k2", "wakizashi": "3k2", "tanto": "2k2",
                   "yari": "3k2", "club": "2k2", "unarmed": "0k2",
                   "gongfu": "0k3"}
    ribbon.append(f"{weapon.upper()} {weapon_dice.get(weapon, '?k?')}")
    return {
        "clan": clan_name,
        "name": config.name.upper(),
        "school": " · ".join(parts),
        "rings": config.rings,
        "ribbon": ribbon,
    }


render_masthead(active="Combat Setup")
render_section_head("I", "Combat Setup", "muster the bushi")

available_names = sorted(st.session_state.characters.keys())

if not available_names:
    st.warning("No characters available. Go to the Characters page to load or create characters first.")
else:
    default_control = [
        n for n in (st.session_state.control_group.character_names if st.session_state.control_group else [])
        if n in available_names
    ]
    default_test = [
        n for n in (st.session_state.test_group.character_names if st.session_state.test_group else [])
        if n in available_names
    ]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "<div style='font-family:Shippori Mincho,serif;font-size:14px;"
            "letter-spacing:0.32em;text-transform:uppercase;color:var(--ink);"
            "margin-bottom:6px;'>← Control Side</div>",
            unsafe_allow_html=True,
        )
        control_names = st.multiselect(
            "Control group characters", available_names,
            default=default_control, key="control_chars",
            label_visibility="collapsed",
        )

    test_options = [n for n in available_names if n not in control_names]
    adjusted_default_test = [n for n in default_test if n in test_options]

    with col2:
        st.markdown(
            "<div style='font-family:Shippori Mincho,serif;font-size:14px;"
            "letter-spacing:0.32em;text-transform:uppercase;color:var(--seal);"
            "margin-bottom:6px;text-align:right;'>Test Side →</div>",
            unsafe_allow_html=True,
        )
        test_names = st.multiselect(
            "Test group characters", test_options,
            default=adjusted_default_test, key="test_chars",
            label_visibility="collapsed",
        )

    if not control_names or not test_names:
        if not control_names:
            st.info("Select at least one bushi for the Control side.")
        if not test_names:
            st.info("Select at least one bushi for the Test side.")
        st.session_state.control_group = None
        st.session_state.test_group = None
        save_state()
    else:
        st.session_state.control_group = GroupConfig(name="control", is_control=True, character_names=control_names)
        st.session_state.test_group = GroupConfig(name="test", is_control=False, character_names=test_names)
        save_state()
        st.success("Groups configured — ready to muster.")

    # Fight card preview for the 1v1 case (the common single-combat scenario).
    if (st.session_state.control_group and st.session_state.test_group
            and len(control_names) == 1 and len(test_names) == 1):
        render_section_head("II", "The Matchup", "preview")
        render_fight_card(
            _fight_card_side(st.session_state.characters[control_names[0]]),
            _fight_card_side(st.session_state.characters[test_names[0]]),
            sub_label="muster",
            stamp="1",
        )
    elif st.session_state.control_group and st.session_state.test_group:
        # Multi-character: show side rosters as compact lines.
        render_section_head("II", "The Muster", "rosters")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                "<div style='font-family:Shippori Mincho,serif;font-size:11px;"
                "letter-spacing:0.36em;text-transform:uppercase;color:var(--ink-faded);"
                "margin-bottom:8px;'>Control Side</div>",
                unsafe_allow_html=True,
            )
            for n in control_names:
                cfg = st.session_state.characters[n]
                clan_name = clan_for(cfg.school)
                st.markdown(
                    f"<div style='font-family:Cormorant Garamond,serif;font-size:17px;'>"
                    f"<b>{cfg.name}</b> <span style='color:var(--ink-faded)'>· {clan_name} · {cfg.school or 'Ronin'}</span></div>",
                    unsafe_allow_html=True,
                )
        with c2:
            st.markdown(
                "<div style='font-family:Shippori Mincho,serif;font-size:11px;"
                "letter-spacing:0.36em;text-transform:uppercase;color:var(--seal);"
                "margin-bottom:8px;text-align:right;'>Test Side</div>",
                unsafe_allow_html=True,
            )
            for n in test_names:
                cfg = st.session_state.characters[n]
                clan_name = clan_for(cfg.school)
                st.markdown(
                    f"<div style='text-align:right;font-family:Cormorant Garamond,serif;font-size:17px;'>"
                    f"<span style='color:var(--ink-faded)'>{cfg.school or 'Ronin'} · {clan_name} ·</span> "
                    f"<b>{cfg.name}</b></div>",
                    unsafe_allow_html=True,
                )
