import streamlit as st

from simulation.schools.factory import get_school
from web.adapters.engine_adapter import run_batch, run_single
from web.adapters.html_renderer import render_play_by_play_html
from web.models import CharacterConfig

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


def _format_character_stats(config: CharacterConfig) -> str:
    """Format a character's stats as a compact markdown string."""
    parts = []
    # Rings
    rings = " / ".join(f"{r.title()} {config.rings.get(r, 2)}" for r in RING_ORDER)
    parts.append(f"**Rings:** {rings}")
    # Attack and Parry
    combat = []
    if "attack" in config.skills:
        combat.append(f"Attack {config.skills['attack']}")
    if "parry" in config.skills:
        combat.append(f"Parry {config.skills['parry']}")
    if combat:
        parts.append(f"**Combat:** {' / '.join(combat)}")
    # School rank
    rank = _school_rank(config)
    if rank is not None:
        ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}
        parts.append(f"**School Rank:** {ordinals.get(rank, f'{rank}th')} Dan")
    return "  \n".join(parts)

st.title("Run Simulation")

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

    tab_batch, tab_single = st.tabs(["Batch Simulation", "Single Combat"])

    with tab_batch:
        num_trials = st.number_input("Number of trials", min_value=1, max_value=1000, value=100, step=10)
        if st.button("Run Batch Simulation"):
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
                    summary_items = {k: f"{v:.2f}" for k, v in sorted(result.summary.items())}
                    col1, col2 = st.columns(2)
                    keys = list(summary_items.keys())
                    mid = len(keys) // 2
                    with col1:
                        for k in keys[:mid]:
                            st.write(f"**{k}:** {summary_items[k]}")
                    with col2:
                        for k in keys[mid:]:
                            st.write(f"**{k}:** {summary_items[k]}")

    with tab_single:
        if st.button("Run Single Combat"):
            with st.spinner("Running combat..."):
                try:
                    result = run_single(characters, groups)
                except Exception as e:
                    st.error(f"Simulation error: {e}")
                    result = None

            if result:
                # Character stats
                st.subheader("Combatants")
                stat_cols = st.columns(len(characters))
                for col, config in zip(stat_cols, characters):
                    with col:
                        st.markdown(f"**{config.name}**")
                        st.markdown(_format_character_stats(config))
                st.divider()

                # Winner
                winner_label = test_label if result.winner == 1 else control_label
                st.subheader(f"Winner: {winner_label}")
                st.write(f"Duration: {result.duration_rounds} rounds, {result.duration_phases} phases")

                # Play-by-play
                with st.expander("Play-by-Play Log", expanded=True):
                    html = render_play_by_play_html(result.play_by_play, result.group_names)
                    st.markdown(html, unsafe_allow_html=True)

                # Features
                with st.expander("Trial Statistics"):
                    for k, v in sorted(result.features.items()):
                        st.write(f"**{k}:** {v}")
