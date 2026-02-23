import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from web.analysis.aggregator import StudySummary, compute_study_summary_with_tags
from web.analysis.models import AnalysisDefinition, AnalysisResult
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


def _load_matchup_into_sim(matchup_id: str, matchup_configs: dict) -> None:
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
        st.switch_page("views/3_Run_Simulation.py")


# ── Simple comparison view (existing kakita_interrupt style) ───────────


def _show_simple_comparison(aid: str, result: AnalysisResult) -> None:
    """Display a simple two-strategy comparison (no variables metadata)."""
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
    groups = defaultdict(dict)
    for p in filtered:
        key = (p["kakita_xp"], p["opponent"], p["opponent_xp"], p["xp_delta"])
        groups[key][p["strategy"]] = p["result"]

    # Build matchup config lookup for Load buttons
    builder = get_builder(aid)
    definition = builder()
    matchup_configs = {m.matchup_id: m for m in definition.matchups}

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
                _load_matchup_into_sim(no_int.matchup_id, matchup_configs)
            if has_int and btn_cols[1].button("Int", key=f"load_int_{i}"):
                _load_matchup_into_sim(has_int.matchup_id, matchup_configs)

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


# ── Study view (multi-variable, 3-tier display) ───────────────────────


def _show_study_view(aid: str, result: AnalysisResult) -> None:
    """Display a study with summary dashboard, variable detail, and full table."""
    # Build the definition to access tags
    builder = get_builder(aid)
    definition = builder()
    matchup_configs = {m.matchup_id: m for m in definition.matchups}
    tags_by_id = {m.matchup_id: m.tags for m in definition.matchups}

    # Compute study summary
    summary = compute_study_summary_with_tags(
        result.matchup_results, tags_by_id, result.variables,
    )

    # Determine which view tier to show
    study_view = params.get("study_view", "summary")

    if study_view == "detail":
        _show_variable_detail(aid, result, summary, definition, matchup_configs, tags_by_id)
    elif study_view == "table":
        _show_full_results_table(aid, result, definition, matchup_configs, tags_by_id)
    else:
        _show_study_summary(aid, result, summary, definition)


# Human-readable descriptions for each recommended option, keyed by
# (variable_name, option_name).  Used by _show_recommended_strategy()
# to explain *what the choice means in practice*.
_RECOMMENDATION_DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("attack_vp", "threshold_07"): (
        "Spend VP on an attack roll when doing so gives you at least a "
        "70% chance of hitting your target number. This focuses your "
        "limited VP on attacks that are likely to connect."
    ),
    ("attack_vp", "threshold_05"): (
        "Spend VP on an attack roll when doing so gives you at least a "
        "50% chance of hitting. More aggressive than the 70% threshold "
        "-- useful against defensive opponents like the Shiba."
    ),
    ("attack_vp", "never"): (
        "Never spend VP on attack rolls, saving them entirely for "
        "wound checks or other uses."
    ),
    ("wound_check_vp", "threshold_05"): (
        "When you take wounds, spend a VP on the wound check if it "
        "gives you at least a 50% chance of avoiding an extra Serious "
        "Wound. This is worth doing every time."
    ),
    ("wound_check_vp", "never"): (
        "Never spend VP on wound checks, saving them for attacks."
    ),
    ("action_hold", "immediate"): (
        "Attack immediately whenever you have an action available. "
        "Don't hold actions in reserve -- the Kakita fighting style "
        "rewards aggression and early pressure."
    ),
    ("action_hold", "hold"): (
        "Hold one action in reserve until later in the round, keeping "
        "flexibility to react."
    ),
    ("interrupt", "on"): (
        "Use interrupt iaijutsu: spend 2 future action dice to make "
        "an out-of-turn strike when you've used your current action."
    ),
    ("interrupt", "off"): (
        "Don't use interrupt attacks. Only attack on your normal turns."
    ),
}


def _show_recommended_strategy(
    result: AnalysisResult,
    summary: StudySummary,
    definition: AnalysisDefinition,
) -> None:
    """Show recommended strategy summary with human-readable explanations."""
    if not summary.marginal_effects or not definition.strategy_map:
        return

    school_name = (
        definition.title.split(" Comprehensive")[0]
        if "Comprehensive" in definition.title
        else "School"
    )

    st.markdown(f"### Recommended Strategy for {school_name}")
    st.markdown(
        "*Based on thousands of simulated duels. Each 'advantage' is how "
        "many more duels out of 100 the Kakita wins with this choice "
        "compared to the next-best alternative.*"
    )

    # Collect best choices, skipping the combined "attack_style" variable
    # since its components (interrupt + attack_vp) are shown separately.
    skip_vars = {"attack_style"}
    yaml_lines = ["strategies:"]
    per_opp_exceptions: list[str] = []

    for var in result.variables:
        if var.name in skip_vars:
            continue

        effects = summary.marginal_effects.get(var.name, [])
        best = next((e for e in effects if e.is_best), None)
        if not best:
            continue

        # Human-readable description of this recommendation
        desc = _RECOMMENDATION_DESCRIPTIONS.get(
            (var.name, best.option_name), "",
        )
        advantage_str = f"+{best.margin_over_next:.1f}" if best.margin_over_next >= 0.1 else "<0.1"

        st.markdown(
            f"- **{var.label}: {best.option_label}** "
            f"({advantage_str} wins per 100 duels)"
        )
        if desc:
            st.caption(f"  {desc}")

        # Look up strategy class name from strategy_map
        dim_map = definition.strategy_map.get(var.name, {})
        opt_overrides = dim_map.get(best.option_name, {})
        for strategy_key, class_name in opt_overrides.items():
            yaml_lines.append(
                f"  {strategy_key}: {class_name}    "
                f"# {var.label}: {best.option_label}"
            )

        # Check per-opponent exceptions
        opp_effects = summary.per_opponent_effects.get(var.name, {})
        for opp, opp_eff_list in sorted(opp_effects.items()):
            opp_best = next((e for e in opp_eff_list if e.is_best), None)
            if opp_best and opp_best.option_name != best.option_name:
                opp_label = opp.replace("_", " ").title()
                opp_desc = _RECOMMENDATION_DESCRIPTIONS.get(
                    (var.name, opp_best.option_name), "",
                )
                exc_text = (
                    f"- vs **{opp_label}**: prefer "
                    f"**{opp_best.option_label}** for {var.label}"
                )
                if opp_desc:
                    exc_text += f" -- {opp_desc.lower().rstrip('.')}"
                per_opp_exceptions.append(exc_text)

    if len(yaml_lines) > 1:
        st.markdown("**Strategy config (for simulator YAML):**")
        st.code("\n".join(yaml_lines), language="yaml")

    if per_opp_exceptions:
        st.markdown("**Opponent-specific adjustments:**")
        for exc in per_opp_exceptions:
            st.markdown(exc)

    st.divider()


def _show_per_opponent_breakdown(
    result: AnalysisResult,
    summary: StudySummary,
) -> None:
    """Show per-opponent breakdown table in the study summary."""
    if not summary.per_opponent_effects:
        return

    # Collect all opponents
    all_opponents: set[str] = set()
    for _var_name, opp_dict in summary.per_opponent_effects.items():
        all_opponents.update(opp_dict.keys())

    if not all_opponents:
        return

    with st.expander("Per-Opponent Breakdown", expanded=False):
        for opp in sorted(all_opponents):
            opp_label = opp.replace("_", " ").title()
            st.markdown(f"**vs {opp_label}**")

            rows = []
            for var in result.variables:
                global_effects = summary.marginal_effects.get(var.name, [])
                global_best = next((e for e in global_effects if e.is_best), None)
                opp_effects = summary.per_opponent_effects.get(var.name, {}).get(opp, [])
                opp_best = next((e for e in opp_effects if e.is_best), None)

                if not opp_best:
                    continue

                differs = ""
                if global_best and opp_best.option_name != global_best.option_name:
                    differs = "DIFFERS"

                rows.append({
                    "Decision": var.label,
                    "Best Option": opp_best.option_label,
                    "Win Rate": f"{opp_best.avg_win_rate:.1f}%",
                    "Advantage": f"+{opp_best.margin_over_next:.1f}%",
                    "": differs,
                })

            if rows:
                st.table(rows)


def _show_study_summary(
    aid: str,
    result: AnalysisResult,
    summary: StudySummary,
    definition: AnalysisDefinition,
) -> None:
    """Tier 1: Summary dashboard showing best choice per variable."""
    # Recommended Strategy section at the top
    _show_recommended_strategy(result, summary, definition)

    st.subheader("Optimal Choices Summary")

    if not summary.marginal_effects:
        st.info("No marginal effects computed. Run the study first.")
        return

    # Summary table
    table_data = []
    for var in result.variables:
        effects = summary.marginal_effects.get(var.name, [])
        best = next((e for e in effects if e.is_best), None)
        if best:
            if best.consistency >= 0.8:
                consistent_label = "Yes"
            elif best.consistency >= 0.5:
                consistent_label = f"Mostly ({best.consistency:.0%})"
            else:
                consistent_label = f"No ({best.consistency:.0%})"

            table_data.append({
                "Decision": var.label,
                "Best Choice": best.option_label,
                "Avg Win Rate": f"{best.avg_win_rate:.1f}%",
                "Advantage": f"+{best.margin_over_next:.1f}%",
                "Consistent?": consistent_label,
            })

    if table_data:
        st.table(table_data)

    # Key findings per variable (brief summary with link to detail)
    if definition.findings:
        st.subheader("Key Findings")
        for var in result.variables:
            finding = definition.findings.get(var.name)
            if finding:
                with st.expander(f"{var.label}", expanded=False):
                    st.markdown(finding)

    # Interactions callout
    notable_interactions = [
        ix for ix in summary.interactions if ix.interaction_score > 5.0
    ]
    if notable_interactions:
        st.subheader("Notable Interactions")
        for ix in notable_interactions:
            a_label = ix.variable_a
            b_label = ix.variable_b
            for var in result.variables:
                if var.name == ix.variable_a:
                    a_label = var.label
                if var.name == ix.variable_b:
                    b_label = var.label
            st.info(
                f"**{a_label}** and **{b_label}** interact "
                f"(score: {ix.interaction_score:.1f}%). "
                f"The effect of one changes depending on the other."
            )

    # Per-opponent breakdown
    _show_per_opponent_breakdown(result, summary)

    # Navigation to detail views
    st.subheader("Drill Down")
    col_vars = st.columns(min(len(result.variables), 4))
    for i, var in enumerate(result.variables):
        col = col_vars[i % len(col_vars)]
        if col.button(f"Details: {var.label}", key=f"detail_{var.name}"):
            st.query_params["study_view"] = "detail"
            st.query_params["variable"] = var.name
            st.rerun()

    if st.button("View Full Results Table"):
        st.query_params["study_view"] = "table"
        st.rerun()


def _show_variable_detail(
    aid: str,
    result: AnalysisResult,
    summary: StudySummary,
    definition: AnalysisDefinition,
    matchup_configs: dict,
    tags_by_id: dict[str, dict[str, str]],
) -> None:
    """Tier 2: Detailed view for a single variable."""
    var_name = params.get("variable", "")

    if st.button("Back to Summary"):
        st.query_params["study_view"] = "summary"
        if "variable" in st.query_params:
            del st.query_params["variable"]
        st.rerun()

    # Find variable metadata — prefer definition (has descriptions)
    def_var = next((v for v in definition.variables if v.name == var_name), None)
    var_meta = def_var or next(
        (v for v in result.variables if v.name == var_name), None,
    )
    if var_meta is None:
        st.error(f"Variable '{var_name}' not found.")
        return

    st.subheader(f"Variable Detail: {var_meta.label}")

    # Show variable description
    if var_meta.description:
        st.markdown(f"*{var_meta.description}*")

    # Show findings at the top
    finding = definition.findings.get(var_name, "")
    if finding:
        st.markdown(finding)
        st.divider()

    # Show marginal effects with option descriptions
    effects = summary.marginal_effects.get(var_name, [])
    if effects:
        # Build option description lookup
        opt_descriptions = {o.name: o.description for o in var_meta.options}

        effect_data = []
        for e in effects:
            row: dict[str, str] = {
                "Option": e.option_label,
                "Avg Win Rate": f"{e.avg_win_rate:.1f}%",
                "Best?": "Yes" if e.is_best else "",
            }
            effect_data.append(row)
        st.table(effect_data)

        # Show option descriptions below the table
        has_descriptions = any(opt_descriptions.get(e.option_name) for e in effects)
        if has_descriptions:
            st.markdown("**What each option does:**")
            for e in effects:
                desc = opt_descriptions.get(e.option_name, "")
                if desc:
                    st.markdown(f"- **{e.option_label}**: {desc}")

    # Per-opponent summary for this variable
    opp_effects = summary.per_opponent_effects.get(var_name, {})
    global_best = next((e for e in effects if e.is_best), None) if effects else None
    if opp_effects and global_best:
        st.subheader("Per-Opponent Summary")
        opp_rows = []
        for opp in sorted(opp_effects.keys()):
            opp_eff_list = opp_effects[opp]
            opp_best = next((e for e in opp_eff_list if e.is_best), None)
            if not opp_best:
                continue
            consistent = "Yes" if opp_best.option_name == global_best.option_name else "No"
            opp_rows.append({
                "Opponent": opp.replace("_", " ").title(),
                "Best Option": opp_best.option_label,
                "Win Rate": f"{opp_best.avg_win_rate:.1f}%",
                "Advantage": f"+{opp_best.margin_over_next:.1f}%",
                "Consistent?": consistent,
            })
        if opp_rows:
            st.table(opp_rows)

    # Breakdown by opponent and XP tier
    detail = summary.variable_details.get(var_name)
    if detail and detail.breakdown:
        st.subheader("Breakdown by Opponent and XP Tier")

        option_names = [o.name for o in var_meta.options]
        option_labels = {o.name: o.label for o in var_meta.options}

        for opp_key in sorted(detail.breakdown.keys()):
            opp_data = detail.breakdown[opp_key]
            opp_label = opp_key.replace("_", " ").title()
            st.markdown(f"**vs {opp_label}**")

            # Build a table: rows = XP tiers, columns = options + diff
            rows = []
            for xp_tier in sorted(opp_data.keys(), key=int):
                opt_rates = opp_data[xp_tier]
                row: dict[str, str | int] = {"XP": int(xp_tier)}
                rates_for_diff = []
                for opt_name in option_names:
                    rate = opt_rates.get(opt_name, 0.0)
                    row[option_labels.get(opt_name, opt_name)] = f"{rate:.1f}%"
                    rates_for_diff.append(rate)
                if len(rates_for_diff) >= 2:
                    diff = max(rates_for_diff) - min(rates_for_diff)
                    row["Spread"] = f"{diff:.1f}%"
                rows.append(row)

            if rows:
                st.table(rows)

    # Average effect by XP tier (bar chart)
    if detail and detail.breakdown:
        st.subheader("Average Effect by XP Tier")
        tier_effects: dict[str, list[float]] = defaultdict(list)

        for opp_key, opp_data in detail.breakdown.items():
            for xp_tier, opt_rates in opp_data.items():
                rates = [opt_rates.get(o, 0.0) for o in option_names]
                if len(rates) >= 2:
                    tier_effects[xp_tier].append(max(rates) - min(rates))

        if tier_effects:
            chart_rows = []
            for tier in sorted(tier_effects.keys(), key=int):
                spreads = tier_effects[tier]
                avg_spread = sum(spreads) / len(spreads) if spreads else 0
                chart_rows.append({
                    "XP Tier": int(tier),
                    "Avg Spread (%)": avg_spread,
                })
            st.bar_chart(chart_rows, x="XP Tier", y="Avg Spread (%)")


def _show_full_results_table(
    aid: str,
    result: AnalysisResult,
    definition: AnalysisDefinition,
    matchup_configs: dict,
    tags_by_id: dict[str, dict[str, str]],
) -> None:
    """Tier 3: Full results table with multi-dimensional filters."""
    if st.button("Back to Summary"):
        st.query_params["study_view"] = "summary"
        st.rerun()

    st.subheader("Full Results Table")

    # Collect all tag values for filters
    all_tag_values: dict[str, set[str]] = defaultdict(set)
    for tags in tags_by_id.values():
        for k, v in tags.items():
            all_tag_values[k].add(v)

    # Build filter controls
    filter_columns = st.columns(min(len(all_tag_values), 4))
    selected_filters: dict[str, list[str]] = {}

    tag_labels = {
        "build": "Build",
        "opponent": "Opponent",
        "subject_xp": "Subject XP",
        "opponent_xp": "Opponent XP",
        "xp_delta": "XP Delta",
    }
    # Add variable names as labels
    for var in result.variables:
        tag_labels[var.name] = var.label

    # Sort tag keys: variables first, then conditions
    var_names = {v.name for v in result.variables}
    sorted_tags = sorted(
        all_tag_values.keys(),
        key=lambda k: (0 if k in var_names else 1, k),
    )

    for i, tag_key in enumerate(sorted_tags):
        col = filter_columns[i % len(filter_columns)]
        tag_values = sorted(all_tag_values[tag_key])
        label = tag_labels.get(tag_key, tag_key)
        selected = col.multiselect(
            label, tag_values, default=tag_values,
            key=f"filter_{tag_key}",
        )
        selected_filters[tag_key] = selected

    # Filter matchups
    filtered_results = []
    for r in result.matchup_results:
        tags = tags_by_id.get(r.matchup_id, {})
        match = True
        for tag_key, selected_values in selected_filters.items():
            tag_val = tags.get(tag_key, "")
            if tag_val not in selected_values:
                match = False
                break
        if match:
            filtered_results.append(r)

    st.write(f"Showing {len(filtered_results)} of {len(result.matchup_results)} matchups")

    # Display results
    if not filtered_results:
        st.info("No results match the selected filters.")
        return

    # Column headers
    hdr = st.columns([3, 1, 1])
    hdr[0].markdown("**Matchup**")
    hdr[1].markdown("**Win Rate**")
    hdr[2].markdown("**Load**")
    st.divider()

    # Limit display to avoid performance issues
    max_display = 100
    display_results = filtered_results[:max_display]
    if len(filtered_results) > max_display:
        st.warning(
            f"Showing first {max_display} of {len(filtered_results)} results. "
            f"Use filters to narrow down."
        )

    for i, r in enumerate(display_results):
        tags = tags_by_id.get(r.matchup_id, {})
        win_rate = (
            r.control_victories / r.num_trials * 100
            if r.num_trials > 0
            else 0
        )

        # Build label from tags
        parts = []
        for var in result.variables:
            val = tags.get(var.name, "")
            if val:
                parts.append(f"{var.label}={val}")
        opp = tags.get("opponent", "").replace("_", " ").title()
        subj_xp = tags.get("subject_xp", "")
        opp_xp = tags.get("opponent_xp", "")
        label = f"vs {opp} ({subj_xp}/{opp_xp}XP) | {', '.join(parts)}"

        cols = st.columns([3, 1, 1])
        cols[0].write(label)
        cols[1].write(f"{win_rate:.1f}%")

        if cols[2].button("Load", key=f"load_full_{i}"):
            _load_matchup_into_sim(r.matchup_id, matchup_configs)


# ── Main routing ───────────────────────────────────────────────────────


def _show_analysis(aid: str) -> None:
    """Display a single analysis's results, routing to appropriate view."""
    if st.button("Back to all analyses"):
        # Clean up all query params
        for key in ["analysis", "study_view", "variable"]:
            if key in st.query_params:
                del st.query_params[key]
        st.rerun()

    if not has_result(aid):
        builder = get_builder(aid)
        definition = builder()
        st.subheader(definition.title)
        st.write(f"**Question:** {definition.question}")
        st.write(definition.description)
        st.warning(
            "Results not yet available. Run from the command line:\n\n"
            f"`env/bin/python -m web.analysis.run_{aid} --trials 100`"
        )
        st.stop()

    result = load_result(aid)
    if result is None:
        st.error("Failed to load results.")
        st.stop()

    st.subheader(result.title)
    st.write(f"**Question:** {result.question}")
    st.write(result.description)

    # Route based on whether this is a study (has variables) or simple comparison
    if result.variables:
        _show_study_view(aid, result)
    else:
        _show_simple_comparison(aid, result)


# Route based on query params
if selected_id and selected_id in analysis_ids:
    _show_analysis(selected_id)
else:
    _show_table_of_contents()
