import streamlit as st

from web.adapters.engine_adapter import run_batch, run_single
from web.adapters.html_renderer import render_play_by_play_html

st.title("Run Simulation")

if not st.session_state.control_group or not st.session_state.test_group:
    st.warning("Please set up combat groups first on the Combat Setup page.")
else:
    control = st.session_state.control_group
    test = st.session_state.test_group
    all_names = control.character_names + test.character_names
    characters = [st.session_state.characters[n] for n in all_names]
    groups = [control, test]

    st.write(f"**Control:** {', '.join(control.character_names)} vs **Test:** {', '.join(test.character_names)}")

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
                col2.metric("Control Wins", result.control_victories)
                col3.metric("Test Wins", result.test_victories)

                test_rate = result.test_victories / result.num_trials * 100
                st.metric("Test Group Win Rate", f"{test_rate:.1f}%")

                # Victory bar chart
                st.bar_chart({"Control": result.control_victories, "Test": result.test_victories})

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
                # Winner
                winner_label = "Test Group" if result.winner == 1 else "Control Group"
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
