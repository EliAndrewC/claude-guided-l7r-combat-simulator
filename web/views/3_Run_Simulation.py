from typing import Any

import streamlit as st

from simulation.schools.factory import get_school
from web.adapters.chronicle_renderer import ChronicleRenderer
from web.adapters.engine_adapter import is_duel_eligible, run_batch, run_duel_batch, run_duel_single, run_single
from web.models import CharacterConfig
from web.views._chronicle import (
    clan_for,
    format_school_rank,
    render_fight_card,
    render_masthead,
    render_section_head,
)

RING_ORDER = ["air", "earth", "fire", "water", "void"]


def _school_rank(config: CharacterConfig) -> int | None:
    """Compute school rank (Dan) from config: min of school knack ranks."""
    if not config.school:
        return None
    try:
        school = get_school(config.school)
    except ValueError:
        return None
    return min(config.skills.get(k, 0) for k in school.school_knacks())


def _fight_card_side(config: CharacterConfig) -> dict[str, Any]:
    """Build a ``render_fight_card`` side dict from a CharacterConfig."""
    clan_name = clan_for(config.school)
    rank = _school_rank(config)
    school_line_parts = [config.school or "Ronin"]
    rank_str = format_school_rank(rank)
    if rank_str is not None:
        school_line_parts.append(rank_str)
    school_line_parts.append(f"{config.xp} xp")
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
        "school": " · ".join(school_line_parts),
        "rings": config.rings,
        "ribbon": ribbon,
    }


render_masthead(active="Run Simulation")
render_section_head("I", "Run Simulation", "single combat · batch · duel")

if not st.session_state.characters:
    st.warning("No characters loaded. Go to the Characters page to load or create characters.")
elif not st.session_state.control_group or not st.session_state.test_group:
    st.warning("Combat groups are not configured. Go to Combat Setup to select groups.")
else:
    control = st.session_state.control_group
    test = st.session_state.test_group
    all_names = control.character_names + test.character_names
    characters = [st.session_state.characters[n] for n in all_names]
    groups = [control, test]

    control_label = control.name or "Control"
    test_label = test.name or "Test"
    st.write(f"**{control_label}:** {', '.join(control.character_names)} vs **{test_label}:** {', '.join(test.character_names)}")

    duel_eligible = is_duel_eligible(characters, groups)
    tab_names = ["Batch Simulation", "Single Combat"]
    if duel_eligible:
        tab_names.extend(["Iaijutsu Duel", "Duel Batch"])
    tabs = st.tabs(tab_names)
    tab_batch = tabs[0]
    tab_single = tabs[1]

    with tab_batch:
        num_trials = st.number_input("Number of trials", min_value=1, max_value=1000, value=100, step=10)
        if st.button("Run Batch Simulation"):
            result: Any
            with st.spinner(f"Running {num_trials} trials..."):
                try:
                    result = run_batch(characters, groups, num_trials)
                except Exception as e:
                    st.error(f"Simulation error: {e}")
                    result = None

            if result:
                # Win rates
                st.subheader("Results")
                col1, col2, col3 = st.columns(3)
                col1.metric("Trials", result.num_trials)
                col2.metric(f"{control_label} Wins", result.control_victories)
                col3.metric(f"{test_label} Wins", result.test_victories)

                test_rate = result.test_victories / result.num_trials * 100
                st.metric(f"{test_label} Win Rate", f"{test_rate:.1f}%")

                # Victory bar chart
                st.bar_chart({control_label: result.control_victories, test_label: result.test_victories})

                # Summary stats
                if result.summary:
                    st.subheader("Summary Statistics")

                    # Duration stats (not group-specific) at the top
                    duration_keys = sorted(
                        k for k in result.summary if k.startswith("duration_")
                    )
                    if duration_keys:
                        for k in duration_keys:
                            st.write(f"**{k}:** {result.summary[k]:.2f}")
                        st.markdown(
                            '<hr style="margin-top:0.5em;margin-bottom:0.5em">',
                            unsafe_allow_html=True,
                        )

                    # Group-specific stats
                    group_items = {
                        k: f"{v:.2f}"
                        for k, v in sorted(result.summary.items())
                        if not k.startswith("duration_")
                    }
                    col1, col2 = st.columns(2)
                    keys = list(group_items.keys())
                    mid = len(keys) // 2
                    with col1:
                        for k in keys[:mid]:
                            st.write(f"**{k}:** {group_items[k]}")
                    with col2:
                        for k in keys[mid:]:
                            st.write(f"**{k}:** {group_items[k]}")

    with tab_single:
        # Streamlit reruns the entire script on every widget interaction,
        # so the result of `run_single` must live in session_state — if it
        # were a local variable bound inside the `if st.button(...)` block,
        # clicking any other widget (e.g. the trace's per-roll modal button)
        # would discard it and blank the page.
        if st.button("Run Single Combat"):
            with st.spinner("Running combat..."):
                try:
                    st.session_state.single_combat_result = run_single(characters, groups)
                except Exception as e:
                    st.error(f"Simulation error: {e}")
                    st.session_state.single_combat_result = None

        result = st.session_state.get("single_combat_result")
        if result:
            # Fight card — only meaningful for 1v1 combats; for
            # multi-character groups, fall back to a compact roster.
            if len(characters) == 2:
                render_fight_card(
                    _fight_card_side(characters[0]),
                    _fight_card_side(characters[1]),
                    sub_label="single combat",
                    stamp="I",
                )
            else:
                st.subheader("Combatants")
                stat_cols = st.columns(len(characters))
                for col, config in zip(stat_cols, characters):
                    with col:
                        st.markdown(f"**{config.name}**")
                        side = _fight_card_side(config)
                        st.markdown(
                            f"_{side['clan']}_  \n"
                            f"_{side['school']}_  \n"
                            f"_{' · '.join(side['ribbon'])}_"
                        )

            # Verdict — section-head treatment instead of a plain st.subheader
            winner_label = test_label if result.winner == 1 else control_label
            render_section_head(
                "II",
                f"Victor — {winner_label}",
                f"{result.duration_rounds} rounds · {result.duration_phases} phases",
            )

            # Play-by-play — sumi-e chronicle event cards rendered
            # as HTML.  Iteration 3 (2026-06-01) replaces the legacy
            # BulletedRenderer + modal-click pattern with bespoke
            # event cards for each combat moment.
            with st.expander("Battle Chronicle", expanded=True):
                html = ChronicleRenderer().render(result.trace_entries)
                st.markdown(html, unsafe_allow_html=True)

            # Features
            with st.expander("Trial Statistics"):
                for k, v in sorted(result.features.items()):
                    st.write(f"**{k}:** {v}")

    if duel_eligible:
        with tabs[2]:
            if st.button("Run Single Duel"):
                with st.spinner("Running duel..."):
                    try:
                        st.session_state.single_duel_result = run_duel_single(characters, groups)
                    except Exception as e:
                        st.error(f"Duel error: {e}")
                        st.session_state.single_duel_result = None

            duel_result = st.session_state.get("single_duel_result")
            if duel_result:
                if len(characters) == 2:
                    render_fight_card(
                        _fight_card_side(characters[0]),
                        _fight_card_side(characters[1]),
                        sub_label="iaijutsu duel",
                        stamp="D",
                    )
                winner_label = test_label if duel_result.winner == 1 else control_label
                render_section_head("II", f"Victor — {winner_label}")

                with st.expander("Battle Chronicle", expanded=True):
                    html = ChronicleRenderer().render(duel_result.trace_entries)
                    st.markdown(html, unsafe_allow_html=True)

                with st.expander("Trial Statistics"):
                    for k, v in sorted(duel_result.features.items()):
                        st.write(f"**{k}:** {v}")

        with tabs[3]:
            duel_trials = st.number_input(
                "Number of duel trials", min_value=1, max_value=1000, value=100, step=10,
                key="duel_trials",
            )
            if st.button("Run Duel Batch"):
                with st.spinner(f"Running {duel_trials} duel trials..."):
                    try:
                        result = run_duel_batch(characters, groups, duel_trials)
                    except Exception as e:
                        st.error(f"Duel batch error: {e}")
                        result = None

                if result:
                    st.subheader("Results")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Trials", result.num_trials)
                    col2.metric(f"{control_label} Wins", result.control_victories)
                    col3.metric(f"{test_label} Wins", result.test_victories)

                    test_rate = result.test_victories / result.num_trials * 100
                    st.metric(f"{test_label} Win Rate", f"{test_rate:.1f}%")
