import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from web.analysis.registry import get_builder, has_result, list_analyses, load_result
from web.state import save_state

st.title("Analysis")

analysis_ids = list_analyses()
if not analysis_ids:
    st.info("No analyses registered.")
    st.stop()

# Use query params to track which analysis is selected (if any)
params = st.query_params
selected_id = params.get("analysis")


def _show_table_of_contents() -> None:
    """Display a listing of all available analyses."""
    st.write("Select an analysis to view results.")
    for aid in analysis_ids:
        builder = get_builder(aid)
        definition = builder()
        ready = has_result(aid)
        status = "Results available" if ready else "Not yet run"

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.subheader(definition.title)
            st.write(f"**Question:** {definition.question}")
            st.write(definition.description)
            st.caption(status)
        with col_btn:
            st.write("")  # spacer
            if st.button("View", key=f"view_{aid}"):
                st.query_params["analysis"] = aid
                st.rerun()
        st.divider()


def _show_analysis(aid: str) -> None:
    """Display a single analysis's results."""
    if st.button("Back to all analyses"):
        del st.query_params["analysis"]
        st.rerun()

    if not has_result(aid):
        builder = get_builder(aid)
        definition = builder()
        st.subheader(definition.title)
        st.write(f"**Question:** {definition.question}")
        st.write(definition.description)
        st.warning(
            "Results not yet available. Run from the command line:\n\n"
            f"`env/bin/python -m web.analysis.run_{aid} --trials 1000`"
        )
        st.stop()

    result = load_result(aid)
    if result is None:
        st.error("Failed to load results.")
        st.stop()

    st.subheader(result.title)
    st.write(f"**Question:** {result.question}")
    st.write(result.description)

    # Parse matchup structure from IDs
    # Format: kakita_{xp}_vs_{opponent}_{opp_xp}_{strategy}
    parsed = []
    for r in result.matchup_results:
        parts = r.matchup_id.split("_vs_")
        if len(parts) != 2:
            continue
        kakita_part = parts[0]  # kakita_{xp}
        rest = parts[1]  # {opponent}_{opp_xp}_{strategy}
        kakita_xp = kakita_part.split("_")[-1]

        # Parse strategy (last token)
        if rest.endswith("_no_interrupt"):
            strategy = "no_interrupt"
            opponent_part = rest[: -len("_no_interrupt")]
        elif rest.endswith("_interrupt"):
            strategy = "interrupt"
            opponent_part = rest[: -len("_interrupt")]
        else:
            continue

        # Parse opponent and xp (opponent may have underscores, e.g. wave_man)
        opp_xp = opponent_part.split("_")[-1]
        opponent = opponent_part[: -len(f"_{opp_xp}")]

        delta = int(opp_xp) - int(kakita_xp)
        parsed.append({
            "kakita_xp": kakita_xp,
            "opponent": opponent,
            "opponent_xp": opp_xp,
            "xp_delta": str(delta),
            "strategy": strategy,
            "result": r,
        })

    # Filters
    col_filter1, col_filter2 = st.columns(2)
    all_tiers = sorted(set(p["kakita_xp"] for p in parsed))
    all_opponents = sorted(set(p["opponent"] for p in parsed))

    with col_filter1:
        selected_tiers = st.multiselect("XP Tier", all_tiers, default=all_tiers)
    with col_filter2:
        selected_opponents = st.multiselect("Opponent", all_opponents, default=all_opponents)

    filtered = [
        p for p in parsed
        if p["kakita_xp"] in selected_tiers and p["opponent"] in selected_opponents
    ]

    # Build comparison table: pair up no_interrupt vs interrupt results
    # Group by (kakita_xp, opponent, opponent_xp)
    groups = defaultdict(dict)
    for p in filtered:
        key = (p["kakita_xp"], p["opponent"], p["opponent_xp"], p["xp_delta"])
        groups[key][p["strategy"]] = p["result"]

    # Build matchup config lookup for Load buttons
    builder = get_builder(aid)
    definition = builder()
    matchup_configs = {m.matchup_id: m for m in definition.matchups}

    def _load_matchup(matchup_id: str) -> None:
        """Load a matchup into session state and switch to the simulation page."""
        matchup = matchup_configs.get(matchup_id)
        if matchup:
            chars = {}
            for c in matchup.control_characters + matchup.test_characters:
                chars[c.name] = c
            st.session_state.characters = chars
            st.session_state.control_group = matchup.control_group
            st.session_state.test_group = matchup.test_group
            save_state()
            st.switch_page("pages/3_Run_Simulation.py")

    # Display results table with inline Load buttons
    st.subheader("Results")
    if groups:
        # Column headers
        hdr = st.columns([1, 1.5, 1, 1, 1.5, 1.5, 1.2, 1.8])
        hdr[0].markdown("**XP Tier**")
        hdr[1].markdown("**Opponent**")
        hdr[2].markdown("**Opp XP**")
        hdr[3].markdown("**Delta**")
        hdr[4].markdown("**No-Int Win%**")
        hdr[5].markdown("**Int Win%**")
        hdr[6].markdown("**Diff**")
        hdr[7].markdown("**Load**")
        st.divider()

        for i, ((kakita_xp, opponent, opp_xp, delta), strats) in enumerate(sorted(groups.items())):
            no_int = strats.get("no_interrupt")
            has_int = strats.get("interrupt")

            no_int_pct = ""
            int_pct = ""
            diff = ""
            if no_int:
                no_int_pct = f"{no_int.control_victories / no_int.num_trials * 100:.1f}%"
            if has_int:
                int_pct = f"{has_int.control_victories / has_int.num_trials * 100:.1f}%"
            if no_int and has_int:
                no_rate = no_int.control_victories / no_int.num_trials * 100
                int_rate = has_int.control_victories / has_int.num_trials * 100
                d = int_rate - no_rate
                diff = f"{d:+.1f}%"

            cols = st.columns([1, 1.5, 1, 1, 1.5, 1.5, 1.2, 1.8])
            cols[0].write(kakita_xp)
            cols[1].write(opponent.replace("_", " ").title())
            cols[2].write(opp_xp)
            cols[3].write(delta)
            cols[4].write(no_int_pct)
            cols[5].write(int_pct)
            cols[6].write(diff)

            # Two small load buttons side by side in the last column
            btn_cols = cols[7].columns(2)
            if no_int and btn_cols[0].button("No Int", key=f"load_no_{i}"):
                _load_matchup(no_int.matchup_id)
            if has_int and btn_cols[1].button("Int", key=f"load_int_{i}"):
                _load_matchup(has_int.matchup_id)

        # Summary chart: average win rate difference by XP tier
        st.subheader("Interrupt Advantage by XP Tier")
        chart_data = defaultdict(list)
        for (kakita_xp, opponent, opp_xp, delta), strats in sorted(groups.items()):
            no_int = strats.get("no_interrupt")
            has_int = strats.get("interrupt")
            if no_int and has_int:
                no_rate = no_int.control_victories / no_int.num_trials * 100
                int_rate = has_int.control_victories / has_int.num_trials * 100
                chart_data[kakita_xp].append(int_rate - no_rate)

        if chart_data:
            chart_rows = []
            for tier in sorted(chart_data.keys()):
                diffs = chart_data[tier]
                avg_diff = sum(diffs) / len(diffs) if diffs else 0
                chart_rows.append({"XP Tier": int(tier), "Avg Win% Difference": avg_diff})
            st.bar_chart(chart_rows, x="XP Tier", y="Avg Win% Difference")
    else:
        st.info("No results match the selected filters.")

    # Interpretation
    if result.interpretation:
        st.subheader("Interpretation")
        st.markdown(result.interpretation)


# Route based on query params
if selected_id and selected_id in analysis_ids:
    _show_analysis(selected_id)
else:
    _show_table_of_contents()
