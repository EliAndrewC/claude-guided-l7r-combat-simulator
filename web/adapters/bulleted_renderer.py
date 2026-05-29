"""BulletedRenderer — produce Markdown output from TraceEntry objects.

Spec 007 Phase 6: consumes ``list[TraceEntry]`` from
``DetailedEventFormatter.entries(history)`` and produces a Markdown
string suitable for ``st.markdown(text)`` in the Streamlit UI.

Per FR-013 to FR-022:

- Multi-source aggregates (attack/parry/counterattack/iaijutsu/WC rolls
  and damage rolls with >1 nonzero-contribution component): emit a
  header line followed by a bulleted breakdown of contributions and a
  ``Dice:`` line.
- Single-source aggregates (or aggregates with 0 components): emit a
  single header line — no bullet sub-list.
- Modifier with attribution: emit its own bullet under the breakdown.
- Damage projection on an attack/counterattack: nested ``Damage will
  be:`` sub-bullet group.
- TN with raises: ``vs TN N (base TN M + K raises × +5 for {action})``
  on the header.
- Floating-bonus gain/consume: one line with source.
- VP-spend (standalone): one line.
- Round headers → ``## Round N`` Markdown headings.
- Status blocks: each character's status on its own line.

Markdown bullets use ``-`` (hyphen + space). Sub-bullets indent by two
spaces. Per Constitution Principle II (engine purity) this module MUST
NOT import from ``simulation/``; all input arrives as plain
``TraceEntry`` snapshots.
"""

from __future__ import annotations

from typing import Any

from web.adapters._breakdown_format import format_breakdown_component
from web.adapters.trace_entries import (
    AkodoFifthDanCounterEntry,
    AttackEntry,
    ComponentDelta,
    CounterattackEntry,
    DamageProjection,
    DeathEntry,
    DuelEndedEntry,
    DuelInitiativeRolledEntry,
    DuelResheathEntry,
    DuelStrikeRolledEntry,
    GainFloatingBonusEntry,
    GainTvpEntry,
    HidaSWForLWTradeEntry,
    HidaThirdDanRerollEntry,
    IaijutsuDuelHeaderEntry,
    IaijutsuEntry,
    IaijutsuFocusEntry,
    IaijutsuStrikeEntry,
    InitiativeEntry,
    KeepLightWoundsEntry,
    LightWoundsDamageEntry,
    MatsuLwFloorEntry,
    ModifierDelta,
    ParryEntry,
    PhaseHeaderEntry,
    RawTextEntry,
    RoundHeaderEntry,
    SchoolNegatedEntry,
    SeriousWoundsDamageEntry,
    ShowMeYourStanceDeclaredEntry,
    ShowMeYourStanceRolledEntry,
    SpendFloatingBonusEntry,
    SpendVpEntry,
    StatusBlockEntry,
    SurrenderEntry,
    TakeSeriousWoundEntry,
    TraceEntry,
    UnconsciousEntry,
    WoundCheckEntry,
)

# ── Shared formatting helpers ──────────────────────────────────────────


def _nonzero_components(components: list[ComponentDelta]) -> list[ComponentDelta]:
    """Filter component list to nonzero-contribution entries only."""
    return [c for c in components if c.rolled != 0 or c.kept != 0]


def _has_breakdown(components: list[ComponentDelta]) -> bool:
    """True iff the components warrant a bulleted breakdown (>= 2 nonzero)."""
    return len(_nonzero_components(components)) >= 2


def _format_dice_inline(dice: list[int], kept: int) -> str:
    """Format a dice list with kept dice **bold** and dropped dice ~~strikethrough~~."""
    if not dice:
        return "[]"
    parts: list[str] = []
    for i, d in enumerate(dice):
        if i < kept:
            parts.append(f"**{d}**")
        else:
            parts.append(f"~~{d}~~")
    return "[" + ", ".join(parts) + "]"


def _format_tn(tn: int, base_tn: int, action_skill: str) -> str:
    """Format TN clause with raise-attribution (FR-017)."""
    if tn > base_tn:
        diff = tn - base_tn
        raises = diff // 5
        return (
            f"TN {tn} (base TN {base_tn} + {raises} raises × +5 "
            f"for {action_skill})"
        )
    return f"TN {tn}"


def _format_component_bullet(c: ComponentDelta) -> str:
    """Per-component bullet content (without the leading ``- ``).

    Delegates to the shared
    :func:`web.adapters._breakdown_format.format_breakdown_component`
    helper so cross-renderer drift is impossible (spec 008 FR-003).
    """
    return format_breakdown_component(c.rolled, c.kept, c.source)


def _component_bullets(
    components: list[ComponentDelta], indent: str = "  ",
) -> list[str]:
    """Render each nonzero component as ``  - NkM source`` bullet.

    The synthetic 10k10-excess entry renders in narrative form
    (see ``_format_component_bullet``).
    """
    return [
        f"{indent}- {_format_component_bullet(c)}"
        for c in _nonzero_components(components)
    ]


def _modifier_bullets(
    modifier: int, breakdown: list[ModifierDelta], indent: str = "  ",
) -> list[str]:
    """Render modifier as one bullet per source (and one for unattributed remainder).

    Returns an empty list when modifier == 0. When the modifier is
    nonzero but partly unattributed, renders the gap as
    ``Modifier: +K (see preceding line)`` per spec 008 FR-014 — the
    Principle VII signal is preserved (the gap is visible) but the
    wording is non-alarming.
    """
    if modifier == 0:
        return []
    nonzero = [m for m in breakdown if m.amount != 0]
    known_total = sum(m.amount for m in nonzero)
    remainder = modifier - known_total
    out: list[str] = []
    for m in nonzero:
        sign = "+" if m.amount >= 0 else ""
        out.append(f"{indent}- Modifier: {sign}{m.amount} ({m.source})")
    if remainder != 0:
        sign = "+" if remainder >= 0 else ""
        out.append(
            f"{indent}- Modifier: {sign}{remainder} (see preceding line)",
        )
    if not out:  # pragma: no cover  # defensive: nonzero modifier always renders something
        return []
    return out


def _damage_projection_bullets(
    proj: DamageProjection, indent: str = "  ",
) -> list[str]:
    """Render the nested ``Damage will be:`` sub-bullet group (FR-018).

    The component sub-bullets route through
    :func:`_format_component_bullet` so the 10k10-overflow narrative
    form matches TextRenderer's output (spec 008 FR-001/004 — Issue 1
    fix: the damage-projection sub-bullets previously bypassed the
    special-case helper and emitted the raw ``-3k3`` form).
    """
    out: list[str] = [f"{indent}- Damage will be: {proj.rolled}k{proj.kept}"]
    sub_indent = indent + "  "
    if _has_breakdown(proj.components):
        for c in _nonzero_components(proj.components):
            out.append(f"{sub_indent}- {_format_component_bullet(c)}")
    if proj.margin_over_tn > 0:
        out.append(f"{sub_indent}- +{proj.margin_over_tn} over TN")
    if proj.extra_damage_dice > 0:
        noun = "die" if proj.extra_damage_dice == 1 else "dice"
        out.append(
            f"{sub_indent}- {proj.extra_damage_dice} extra damage {noun}"
        )
    return out


def _vp_prefix(vp_spent: int | None, vp_skill: str | None) -> str:
    """Render the ``⬛⬛ spends N VP on <skill> →`` leading text (or empty)."""
    if vp_spent is None or vp_skill is None:
        return ""
    squares = "⬛" * vp_spent
    return f"{squares} spends {vp_spent} VP on {vp_skill} → "


def _floating_bonus_inline_segment(
    bonuses: list[ModifierDelta],
) -> str:
    """Render the inline ``", +N (source floating bonus), +M (source2)"``
    segment for an attack-line header (spec 008 FR-008/9).

    Returns an empty string when no bonuses are consumed.  Each bonus
    is rendered as ``", +{amount} ({source} floating bonus)"`` and the
    caller appends ``" = {total}"`` to close the arithmetic.
    """
    if not bonuses:
        return ""
    parts: list[str] = []
    for fb in bonuses:
        label = fb.source or "floating bonus"
        sign = "+" if fb.amount >= 0 else ""
        parts.append(f", {sign}{fb.amount} ({label} floating bonus)")
    return "".join(parts)


# ── BulletedRenderer ────────────────────────────────────────────────────


class BulletedRenderer:
    """Render a list of TraceEntry objects into a Markdown string.

    Produces output suitable for ``st.markdown(text)`` (NOT
    ``unsafe_allow_html=True``). The dispatcher mirrors
    ``TextRenderer._dispatch`` so every TraceEntry kind has a handler.
    """

    def render(self, entries: list[TraceEntry]) -> str:
        """Walk entries and produce the full Markdown trace as one string."""
        lines: list[str] = []
        for entry in entries:
            lines.extend(self._dispatch(entry))
        return "\n".join(lines)

    def _dispatch(self, entry: TraceEntry) -> list[str]:
        if isinstance(entry, RoundHeaderEntry):
            return self._render_round_header(entry)
        if isinstance(entry, PhaseHeaderEntry):  # pragma: no cover  # defensive: PhaseHeaderEntry is never emitted by entries() (phase headers are embedded into action-line prefixes)
            return [f"### Phase {entry.phase}"]
        if isinstance(entry, StatusBlockEntry):
            return self._render_status_block(entry)
        if isinstance(entry, InitiativeEntry):
            return self._render_initiative(entry)
        if isinstance(entry, AttackEntry):
            return self._render_attack(entry)
        if isinstance(entry, CounterattackEntry):
            return self._render_counterattack(entry)
        if isinstance(entry, ParryEntry):
            return self._render_parry(entry)
        if isinstance(entry, IaijutsuEntry):
            return self._render_iaijutsu(entry)
        if isinstance(entry, LightWoundsDamageEntry):
            return self._render_lw_damage(entry)
        if isinstance(entry, SeriousWoundsDamageEntry):
            return self._render_sw_damage(entry)
        if isinstance(entry, WoundCheckEntry):
            return self._render_wound_check(entry)
        if isinstance(entry, KeepLightWoundsEntry):
            return self._render_keep_lw(entry)
        if isinstance(entry, TakeSeriousWoundEntry):
            return self._render_take_sw(entry)
        if isinstance(entry, SpendVpEntry):
            return self._render_spend_vp(entry)
        if isinstance(entry, GainTvpEntry):
            return self._render_gain_tvp(entry)
        if isinstance(entry, GainFloatingBonusEntry):
            return self._render_gain_floating_bonus(entry)
        if isinstance(entry, SpendFloatingBonusEntry):
            return self._render_spend_floating_bonus(entry)
        if isinstance(entry, SchoolNegatedEntry):
            return self._render_school_negated(entry)
        if isinstance(entry, AkodoFifthDanCounterEntry):
            return self._render_akodo_5th_dan_counter(entry)
        if isinstance(entry, HidaThirdDanRerollEntry):
            return self._render_hida_3rd_dan_reroll(entry)
        if isinstance(entry, HidaSWForLWTradeEntry):
            return self._render_hida_sw_for_lw_trade(entry)
        if isinstance(entry, MatsuLwFloorEntry):
            return self._render_matsu_lw_floor(entry)
        if isinstance(entry, IaijutsuDuelHeaderEntry):
            return self._render_iaijutsu_duel_header()
        if isinstance(entry, ShowMeYourStanceDeclaredEntry):
            return self._render_stance_declared(entry)
        if isinstance(entry, ShowMeYourStanceRolledEntry):
            return self._render_stance_rolled(entry)
        if isinstance(entry, DuelInitiativeRolledEntry):
            return self._render_duel_initiative(entry)
        if isinstance(entry, IaijutsuFocusEntry):
            return self._render_iaijutsu_focus(entry)
        if isinstance(entry, IaijutsuStrikeEntry):
            return self._render_iaijutsu_strike(entry)
        if isinstance(entry, DuelStrikeRolledEntry):
            return self._render_duel_strike_rolled(entry)
        if isinstance(entry, DuelResheathEntry):
            return self._render_duel_resheath(entry)
        if isinstance(entry, DuelEndedEntry):
            return self._render_duel_ended()
        if isinstance(entry, DeathEntry):
            return self._render_death(entry)
        if isinstance(entry, UnconsciousEntry):
            return self._render_unconscious(entry)
        if isinstance(entry, SurrenderEntry):
            return self._render_surrender(entry)
        if isinstance(entry, RawTextEntry):  # pragma: no cover  # defensive: RawTextEntry is the FR-007 fallback and never emitted in correct operation
            return list(entry.lines)
        raise NotImplementedError(  # pragma: no cover  # defensive: every TraceEntry concrete kind is handled above
            f"BulletedRenderer cannot render entry: {entry!r}"
        )

    # ── Headers / blocks ──────────────────────────────────────────────

    def _render_round_header(self, entry: RoundHeaderEntry) -> list[str]:
        return ["", f"## Round {entry.round_number}", ""]

    def _render_status_block(self, entry: StatusBlockEntry) -> list[str]:
        lines: list[str] = ["", "**Status:**"]
        for name, s in entry.statuses.items():
            crippled = " | **CRIPPLED**" if s["crippled"] else ""
            lines.append(
                f"- **{name}**: Light {s['lw']} | Serious {s['sw']}/{s['max_sw']} | "
                f"Void {s['vp']}/{s['max_vp']} | Actions: {s['actions']}{crippled}"
            )
        lines.append("")
        return lines

    def _render_initiative(self, entry: InitiativeEntry) -> list[str]:
        lines: list[str] = ["", "**🎲 Initiative:**"]
        for item in entry.entries:
            dice_str = _format_dice_inline(item["all_dice"], item["kept"])
            lines.append(
                f"- **{item['name']}**: {item['rolled']}k{item['kept']} "
                f"rolled {dice_str} → Actions: {item['actions']}"
            )
        return lines

    # ── Attack/Counterattack/Parry/Iaijutsu ──────────────────────────

    def _render_attack(self, entry: AttackEntry) -> list[str]:
        # take-only path (no roll info yet)
        if entry.is_take_only:
            return [
                f"{entry.phase_prefix} ⚔️ attacks {entry.target_name} "
                f"({entry.skill})"
            ]

        vp_prefix = _vp_prefix(entry.vp_spent, entry.vp_skill)

        if not entry.has_detail:
            if entry.is_combined:
                return [
                    f"{entry.phase_prefix} {vp_prefix}⚔️ attacks "
                    f"{entry.target_name} ({entry.skill}) — "
                    f"Roll: {entry.fallback_roll}"
                ]
            return [f"- Roll: {entry.fallback_roll}"]

        tn_str = _format_tn(entry.tn, entry.base_tn, entry.skill)
        result = "HIT!" if entry.outcome == "hit" else "MISS"

        # Spec 008 FR-008/9: integrate consumed floating bonuses into
        # the header's inline arithmetic.  ``entry.total`` is the
        # pre-bonus total; add each bonus's value to get the displayed
        # final total.
        total_with_bonuses = entry.total + sum(
            fb.amount for fb in entry.consumed_floating_bonuses
        )
        bonus_segment = _floating_bonus_inline_segment(
            entry.consumed_floating_bonuses,
        )
        # Show the running displayed total: pre-bonus, then post-bonus.
        if bonus_segment:
            total_display = f"{entry.total}{bonus_segment} = {total_with_bonuses}"
        else:
            total_display = str(entry.total)

        if entry.is_combined:
            header = (
                f"{entry.phase_prefix} {vp_prefix}⚔️ attacks "
                f"{entry.target_name} ({entry.skill}) — "
                f"{entry.rolled}k{entry.kept} → {total_display} "
                f"vs {tn_str} — {result}"
            )
        else:
            emoji = "🎯" if entry.outcome == "hit" else "❌"
            header = (
                f"{entry.phase_prefix} {emoji} Attack: "
                f"{entry.rolled}k{entry.kept} → {total_display} "
                f"vs {tn_str} — {result}"
            )

        # Spec 008 FR-005: feint attacks suppress the damage projection.
        proj = (
            entry.damage_projection
            if (
                entry.outcome == "hit"
                and not entry.suppress_damage_projection
            )
            else None
        )
        lines = self._roll_body(
            header, entry.components, entry.modifier,
            entry.modifier_components, entry.dice, entry.kept,
            entry.sum_of_kept, total_with_bonuses,
            damage_projection=proj,
        )
        # rules/04-schools.md "Matsu Bushi School: Fourth Dan":
        # surface the near-miss carve-out with explicit attribution
        # per Constitution Principle VII / FR-021.  Appended as a
        # follow-up bullet so the HIT! result stays at the headline.
        # trace-reader #1 (2026-05-28) — explicit mechanical framing so a
        # fresh reader doesn't see "HIT!" + "near-miss" and assume the
        # renderer is wrong (see TextRenderer for the same fix).
        if entry.matsu_4th_dan_near_miss_below_tn > 0:
            lines.append(
                f"{entry.phase_prefix} Matsu 4th Dan: counts as hit "
                f"({entry.matsu_4th_dan_near_miss_below_tn} below TN — "
                f"within the near-miss carve-out)"
            )
        return lines

    def _render_counterattack(self, entry: CounterattackEntry) -> list[str]:
        if entry.is_take_only:
            return [
                f"{entry.phase_prefix} ⚔️ counterattacks "
                f"{entry.target_name}"
            ]

        vp_prefix = _vp_prefix(entry.vp_spent, entry.vp_skill)

        if not entry.has_detail:
            if entry.is_combined:
                return [
                    f"{entry.phase_prefix} {vp_prefix}⚔️ counterattacks "
                    f"{entry.target_name} — Roll: {entry.fallback_roll}"
                ]
            return [f"- Counterattack Roll: {entry.fallback_roll}"]

        result = "HIT!" if entry.outcome == "hit" else "MISS"
        if entry.is_combined:
            header = (
                f"{entry.phase_prefix} {vp_prefix}⚔️ counterattacks "
                f"{entry.target_name} — "
                f"{entry.rolled}k{entry.kept} → {entry.total} "
                f"vs TN {entry.tn} — {result}"
            )
        else:
            emoji = "🎯" if entry.outcome == "hit" else "❌"
            header = (
                f"{entry.phase_prefix} {emoji} Counterattack: "
                f"{entry.rolled}k{entry.kept} → {entry.total} "
                f"vs TN {entry.tn} — {result}"
            )
        return self._roll_body(
            header, entry.components, entry.modifier,
            entry.modifier_components, entry.dice, entry.kept,
            entry.sum_of_kept, entry.total,
            damage_projection=entry.damage_projection
            if entry.outcome == "hit" else None,
        )

    def _render_parry(self, entry: ParryEntry) -> list[str]:
        if entry.is_take_only:
            return [
                f"{entry.phase_prefix} 🛡️ parries {entry.target_name}"
            ]

        if not entry.has_detail:
            if entry.is_combined:
                return [
                    f"{entry.phase_prefix} 🛡️ parries "
                    f"{entry.target_name} — Roll: {entry.fallback_roll}"
                ]
            return [
                f"{entry.phase_prefix} 🛡️ Parry roll: {entry.fallback_roll}"
            ]

        result = "SUCCEEDED" if entry.outcome == "succeeded" else "FAILED"
        if entry.is_combined:
            header = (
                f"{entry.phase_prefix} 🛡️ parries {entry.target_name} — "
                f"{entry.rolled}k{entry.kept} → {entry.total} "
                f"vs TN {entry.tn} — {result}"
            )
        else:
            header = (
                f"{entry.phase_prefix} 🛡️ Parry: "
                f"{entry.rolled}k{entry.kept} → {entry.total} "
                f"vs TN {entry.tn} — {result}"
            )
        return self._roll_body(
            header, entry.components, entry.modifier,
            entry.modifier_components, entry.dice, entry.kept,
            entry.sum_of_kept, entry.total,
        )

    def _render_iaijutsu(self, entry: IaijutsuEntry) -> list[str]:
        margin = abs(entry.skill_roll - entry.opponent_skill_roll)
        if entry.skill_roll > entry.opponent_skill_roll:
            result = "WON"
        elif entry.skill_roll < entry.opponent_skill_roll:
            result = "LOST"
        else:
            result = "TIED"

        if entry.is_challenger:
            label = "⚔️ Contested Iaijutsu (5th Dan)"
            extras: list[str] = [f"+{margin}"] if margin > 0 else []
            if result == "WON" and entry.extra_damage_dice > 0:
                noun = "die" if entry.extra_damage_dice == 1 else "dice"
                extras.append(
                    f"{entry.extra_damage_dice} extra damage {noun}"
                )
            elif result == "LOST" and entry.extra_damage_dice < 0:
                extras.append(
                    f"{abs(entry.extra_damage_dice)} fewer damage dice"
                )
        else:
            label = f"⚔️ Contested Iaijutsu ({entry.skill})"
            extras = [f"+{margin}"] if margin > 0 else []

        extra_str = f" ({', '.join(extras)})" if extras else ""

        if entry.has_detail:
            header = (
                f"{entry.phase_prefix} {label}: "
                f"{entry.rolled}k{entry.kept} → {entry.skill_roll} "
                f"vs {entry.opponent_skill_roll} — {result}{extra_str}"
            )
            return self._roll_body(
                header, [], entry.effective_modifier, [],
                entry.dice, entry.kept, entry.sum_of_kept, entry.skill_roll,
            )
        return [
            f"{entry.phase_prefix} {label}: "
            f"{entry.skill_roll} vs {entry.opponent_skill_roll} "
            f"— {result}{extra_str}"
        ]

    def _render_lw_damage(self, entry: LightWoundsDamageEntry) -> list[str]:
        if not entry.has_detail:
            return [
                f"{entry.phase_prefix} 💥 takes {entry.damage} light wounds"
            ]
        total_str = (
            f" (total: {entry.lw_after})" if entry.lw_after is not None else ""
        )
        header = (
            f"{entry.phase_prefix} 💥 Damage: "
            f"{entry.rolled}k{entry.kept} → {entry.target_name} takes "
            f"{entry.damage} light wounds{total_str}"
        )
        out: list[str] = [header]
        if _has_breakdown(entry.components):
            out.append(f"  - Roll: {entry.rolled}k{entry.kept}")
            for c in _nonzero_components(entry.components):
                # Route through the shared helper so the 10k10-overflow
                # narrative form is identical to TextRenderer's (spec 008
                # FR-001 — Issue 1 fix).
                out.append(f"    - {_format_component_bullet(c)}")
            out.append(
                f"  - Dice: {_format_dice_inline(entry.dice, entry.kept)} "
                f"→ {entry.sum_of_kept} kept"
            )
        else:
            out.append(
                f"  - Dice: {_format_dice_inline(entry.dice, entry.kept)} "
                f"→ {entry.sum_of_kept} kept"
            )
        return out

    def _render_sw_damage(self, entry: SeriousWoundsDamageEntry) -> list[str]:
        hearts = "💔" * entry.damage
        noun = "wound" if entry.damage == 1 else "wounds"
        if entry.from_double_attack:
            suffix = " (double attack penalty)"
        elif entry.from_otaku_5th_dan:
            suffix = " (Otaku 5th Dan: traded 10 rolled damage dice for 1 SW)"
        else:
            suffix = ""
        return [
            f"{entry.phase_prefix} {hearts} {entry.target_name} takes "
            f"{entry.damage} serious {noun}{suffix}"
        ]

    def _render_wound_check(self, entry: WoundCheckEntry) -> list[str]:
        # VP-prefix (Akodo 4th Dan or plain) on the leading header.
        if entry.vp_source == "Akodo 4th Dan" and entry.vp_breakdown:
            squares = "⬛" * (entry.vp_spent or 0)
            vp_prefix = (
                f"{squares} Akodo 4th Dan: spends {entry.vp_spent} VP on "
                f"{entry.vp_skill}, {entry.vp_breakdown} → "
            )
        elif entry.vp_spent is not None and entry.vp_skill is not None:
            vp_prefix = _vp_prefix(entry.vp_spent, entry.vp_skill)
        else:
            vp_prefix = ""

        if entry.follow_up == "keep_lw":
            emoji = "🖤"
        elif entry.follow_up == "take_sw":
            emoji = "💔" * entry.follow_up_sw_count
        else:
            emoji = "💔" if entry.outcome == "passed" else "🖤"

        result = "PASSED" if entry.outcome == "passed" else "FAILED"

        if not entry.has_detail:
            header = (
                f"{entry.phase_prefix} {vp_prefix}{emoji} Wound Check: "
                f"rolled {entry.fallback_roll} vs TN {entry.tn} — {result}"
            )
            lines = [header]
        else:
            header = (
                f"{entry.phase_prefix} {vp_prefix}{emoji} Wound Check: "
                f"{entry.rolled}k{entry.kept} → {entry.total} "
                f"vs TN {entry.tn} — {result}"
            )
            lines = self._roll_body(
                header, entry.components, entry.modifier,
                entry.modifier_components, entry.dice, entry.kept,
                entry.sum_of_kept, entry.total,
            )

        # rules/04-schools.md "Hida Bushi School: Fifth Dan": render
        # the counterattack-excess WC bonus as a bullet on the WC line
        # so the reader sees the +X with explicit source attribution
        # per Principle VII.
        if entry.hida_5th_dan_excess_bonus:
            lines.append(
                f"  - Hida 5th Dan: counterattack excess "
                f"+{entry.hida_5th_dan_excess_bonus}"
            )

        # rules/04-schools.md "Bayushi Bushi School: Fifth Dan": render
        # the half-LW SW computation as a bullet so the reader sees
        # that the SW count was computed against the halved LW per
        # Principle VII (trace-auditor + trace-reader fix 2026-05-28).
        if entry.bayushi_5th_dan_halved_lw_actual:
            halved = entry.bayushi_5th_dan_halved_lw_actual // 2
            lines.append(
                f"  - Bayushi 5th Dan: SW vs halved LW "
                f"({entry.bayushi_5th_dan_halved_lw_actual} → {halved})"
            )

        if entry.follow_up == "keep_lw":
            lines.append(
                f"  - keeping {entry.follow_up_lw_total} light wounds"
            )
        elif entry.follow_up == "take_sw":
            noun = "wound" if entry.follow_up_sw_count == 1 else "wounds"
            verb = "chooses to take" if entry.follow_up_voluntary else "takes"
            lines.append(
                f"  - {verb} {entry.follow_up_sw_count} serious {noun}"
            )
        return lines

    def _render_keep_lw(self, entry: KeepLightWoundsEntry) -> list[str]:
        return [
            f"{entry.phase_prefix} 🖤 keeping {entry.lw_total} light wounds"
        ]

    def _render_take_sw(self, entry: TakeSeriousWoundEntry) -> list[str]:
        if entry.voluntary:
            return [
                f"{entry.phase_prefix} 💔 chooses to take 1 serious wound"
            ]
        return [f"{entry.phase_prefix} 💔 takes 1 serious wound"]

    # ── Simple one-line entries ─────────────────────────────────────────

    def _render_spend_vp(self, entry: SpendVpEntry) -> list[str]:
        squares = "⬛" * entry.amount
        return [
            f"{entry.phase_prefix} {squares} spends {entry.amount} VP on "
            f"{entry.skill}"
        ]

    def _render_gain_tvp(self, entry: GainTvpEntry) -> list[str]:
        if entry.source == "Akodo Special Ability":
            outcome = "successful feint" if entry.amount == 4 else "failed feint"
            return [
                f"{entry.phase_prefix} ✨ {entry.source}: "
                f"+{entry.amount} TVP on {outcome}"
            ]
        if entry.source:
            return [
                f"{entry.phase_prefix} ✨ {entry.source}: +{entry.amount} TVP"
            ]
        return [f"{entry.phase_prefix} ✨ gains +{entry.amount} TVP"]

    def _render_gain_floating_bonus(
        self, entry: GainFloatingBonusEntry,
    ) -> list[str]:
        if entry.source:
            if entry.breakdown:
                return [
                    f"{entry.phase_prefix} ✨ {entry.source}: gained "
                    f"floating bonus +{entry.amount} ({entry.breakdown})"
                ]
            return [
                f"{entry.phase_prefix} ✨ {entry.source}: gained "
                f"floating bonus +{entry.amount}"
            ]
        return [
            f"{entry.phase_prefix} ✨ gains floating bonus +{entry.amount}"
        ]

    def _render_spend_floating_bonus(
        self, entry: SpendFloatingBonusEntry,
    ) -> list[str]:
        if entry.source:
            return [
                f"{entry.phase_prefix} ✨ +{entry.amount} "
                f"({entry.source} floating bonus consumed)"
            ]
        return [
            f"{entry.phase_prefix} ✨ +{entry.amount} "
            f"(floating bonus consumed)"
        ]

    def _render_school_negated(self, entry: SchoolNegatedEntry) -> list[str]:
        return [
            f"{entry.phase_prefix} ⛔ negates {entry.target_name}'s "
            f"{entry.target_school_name} "
            f"({entry.vp_cost} VP — Isawa Ishi 5th Dan)"
        ]

    def _render_akodo_5th_dan_counter(
        self, entry: AkodoFifthDanCounterEntry,
    ) -> list[str]:
        squares = "⬛" * entry.vp_spent
        return [
            f"{entry.phase_prefix} {squares} Akodo 5th Dan: "
            f"spends {entry.vp_spent} VP on counter-damage, "
            f"10 LW × {entry.vp_spent} = {entry.damage} LW dealt to "
            f"{entry.target_name}"
        ]

    def _render_hida_3rd_dan_reroll(
        self, entry: HidaThirdDanRerollEntry,
    ) -> list[str]:
        """Hida 3rd Dan reroll line in Markdown bulleted form.

        Constitution Principle VII — surface each rerolled die's
        before/after value AND the source label "Hida 3rd Dan".
        """
        pairs = ", ".join(f"{b}→{a}" for (b, a) in entry.rerolls)
        impaired = " (impaired)" if entry.crippled else ""
        # See TextRenderer._render_hida_3rd_dan_reroll for the rationale
        # behind "kept-sum" (vs "total"): post-roll modifiers like the
        # Hida 2nd Dan +5 free raise on counterattack are not reflected
        # in this sub-line, only in the parent Roll: N header.
        return [
            f"{entry.phase_prefix} 🎲 Hida 3rd Dan: reroll {pairs} "
            f"(N={entry.n}{impaired}; kept-sum {entry.before_total}→"
            f"{entry.after_total})"
        ]

    def _render_hida_sw_for_lw_trade(
        self, entry: HidaSWForLWTradeEntry,
    ) -> list[str]:
        """Hida 4th Dan SW-for-LW trade line in Markdown bulleted form.

        Constitution Principle VII — the trade carries the explicit
        source label "Hida 4th Dan", the numeric SW cost, and the LW
        value being reset.  No wound check is rendered because the
        trade replaces it.

        rules/04-schools.md "Hida Bushi School: Fourth Dan".
        """
        return [
            f"{entry.phase_prefix} 🛡️ Hida 4th Dan: "
            f"take {entry.sw_taken} SW to reset LW from "
            f"{entry.lw_reset_from} → 0 (alternative wound check)"
        ]

    def _render_matsu_lw_floor(
        self, entry: MatsuLwFloorEntry,
    ) -> list[str]:
        """Matsu 5th Dan LW-floor attribution in Markdown bulleted form.

        Constitution Principle VII — the line carries the explicit
        source label "Matsu 5th Dan", the numeric LW value (15), and
        the contrast clause "(instead of 0)" so the playtester sees
        what changed relative to the standard rules-as-written
        baseline.

        rules/04-schools.md "Matsu Bushi School: Fifth Dan".
        """
        return [
            f"{entry.phase_prefix} 🩸 Matsu 5th Dan: "
            f"{entry.defender_name} LW set to {entry.lw_set_to} "
            f"(instead of 0)"
        ]

    # ── Duel entries ────────────────────────────────────────────────────

    def _render_iaijutsu_duel_header(self) -> list[str]:
        return ["", "## Iaijutsu Duel", ""]

    def _render_stance_declared(
        self, entry: ShowMeYourStanceDeclaredEntry,
    ) -> list[str]:
        return [
            f"{entry.character_name} | 🔍 prepares to assess opponent's stance"
        ]

    def _render_stance_rolled(
        self, entry: ShowMeYourStanceRolledEntry,
    ) -> list[str]:
        dice_info = ""
        if entry.dice and entry.rolled is not None and entry.kept is not None:
            dice_info = (
                f" ({entry.rolled}k{entry.kept} "
                f"{_format_dice_inline(entry.dice, entry.kept)})"
            )
        return [
            f"{entry.character_name} | 🔍 Stance: rolled {entry.roll}"
            f"{dice_info} — discerns Fire ~{entry.discerned_fire}, "
            f"TN ~{entry.discerned_tn}"
        ]

    def _render_duel_initiative(
        self, entry: DuelInitiativeRolledEntry,
    ) -> list[str]:
        return [
            f"⚔️ Contested Iaijutsu: "
            f"{entry.challenger_name} {entry.challenger_roll} vs "
            f"{entry.defender_name} {entry.defender_roll} "
            f"— {entry.winner_name} chooses first"
        ]

    def _render_iaijutsu_focus(self, entry: IaijutsuFocusEntry) -> list[str]:
        return [
            f"{entry.character_name} | 🎯 focuses — "
            f"TNs: {entry.challenger_name} {entry.challenger_tn}, "
            f"{entry.defender_name} {entry.defender_tn}"
        ]

    def _render_iaijutsu_strike(
        self, entry: IaijutsuStrikeEntry,
    ) -> list[str]:
        return [
            f"{entry.character_name} | ⚔️ declares strike — "
            f"TNs: {entry.challenger_name} {entry.challenger_tn}, "
            f"{entry.defender_name} {entry.defender_tn}"
        ]

    def _render_duel_strike_rolled(
        self, entry: DuelStrikeRolledEntry,
    ) -> list[str]:
        dice_info = ""
        if entry.dice and entry.rolled is not None and entry.kept is not None:
            dice_info = (
                f" {entry.rolled}k{entry.kept} "
                f"{_format_dice_inline(entry.dice, entry.kept)}"
            )
        if entry.is_hit:
            extra = (
                f" (+{entry.extra_damage_dice} extra damage dice)"
                if entry.extra_damage_dice > 0 else ""
            )
            return [
                f"{entry.character_name} | ⚔️ Strike vs {entry.target_name}:"
                f"{dice_info} {entry.roll} vs TN {entry.tn} — HIT!{extra}"
            ]
        return [
            f"{entry.character_name} | ❌ Strike vs {entry.target_name}:"
            f"{dice_info} {entry.roll} vs TN {entry.tn} — MISS"
        ]

    def _render_duel_resheath(self, entry: DuelResheathEntry) -> list[str]:
        return [
            f"🔄 Neither hit — resheathe. "
            f"{entry.higher_roller_name} gains a free raise on damage."
        ]

    def _render_duel_ended(self) -> list[str]:
        return ["⚔️ Duel ended — transitioning to melee combat"]

    def _render_death(self, entry: DeathEntry) -> list[str]:
        return [f"{entry.phase_prefix} ☠️ is killed!"]

    def _render_unconscious(self, entry: UnconsciousEntry) -> list[str]:
        return [f"{entry.phase_prefix} 💀 falls unconscious!"]

    def _render_surrender(self, entry: SurrenderEntry) -> list[str]:
        return [f"{entry.phase_prefix} 🏳️ surrenders!"]

    # ── Shared roll-body composition ────────────────────────────────────

    def _roll_body(
        self,
        header: str,
        components: list[ComponentDelta],
        modifier: int,
        modifier_components: list[ModifierDelta],
        dice: list[int],
        kept: int,
        sum_of_kept: int,
        total: int,
        *,
        damage_projection: DamageProjection | None = None,
    ) -> list[str]:
        """Render header + bulleted breakdown + modifier + dice + damage proj.

        Per FR-013 / FR-014 the bullets only appear when there's a real
        multi-source breakdown OR a modifier OR a damage projection.
        Otherwise the header is emitted alone (single-line form).
        """
        has_components = _has_breakdown(components)
        mod_bullets = _modifier_bullets(modifier, modifier_components)
        proj_bullets = (
            _damage_projection_bullets(damage_projection)
            if damage_projection is not None else []
        )

        if not (has_components or mod_bullets or proj_bullets):
            return [header]

        out: list[str] = [header]
        if has_components:
            out.extend(_component_bullets(components))
        if mod_bullets:
            out.extend(mod_bullets)
        # Always show dice when we've expanded into a breakdown.
        out.append(
            f"  - Dice: {_format_dice_inline(dice, kept)} → {sum_of_kept} kept"
            + (f", +{modifier} = {total}" if modifier > 0 else "")
            + (f", {modifier} = {total}" if modifier < 0 else ""),
        )
        if proj_bullets:
            out.extend(proj_bullets)
        return out


_ = Any  # keep `Any` referenced in case future code needs it
