"""TextRenderer — produce byte-identical text lines from TraceEntry objects.

Spec 007 Phase 4: consumes ``list[TraceEntry]`` from
``DetailedEventFormatter.entries(history)`` and produces the same
``list[str]`` that the pre-refactor ``format_history(history)`` produced.

Per FR-009 / FR-011 the output is byte-identical. The legacy
``_format_*`` methods (now soon to be removed) provided the reference
implementation; each renamed ``_render_<kind>`` method below carries the
body of the corresponding legacy method with ``event.attribute``
references replaced by ``entry.attribute`` references.
"""

from typing import Any

from web.adapters._breakdown_format import format_breakdown_component
from web.adapters.trace_entries import (
    AkodoFifthDanCounterEntry,
    AttackEntry,
    ComponentDelta,
    CounterattackEntry,
    CounterDamageDealtEntry,
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
    KitsukiRingReductionEntry,
    LightWoundsDamageEntry,
    MatsuLwFloorEntry,
    MerchantRerollEntry,
    ModifierDelta,
    ParryEntry,
    PhaseHeaderEntry,
    RawTextEntry,
    RoundHeaderEntry,
    SchoolNegatedEntry,
    SeriousWoundsDamageEntry,
    ShibaFifthDanTnReductionEntry,
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
    YogoThirdDanLwReductionEntry,
)


def _render_components(components: list[ComponentDelta]) -> str:
    """Inline ``"N1k(M1) source-1 + N2k(M2) source-2 + ..."`` breakdown.

    Returns "" when fewer than 2 nonzero-contribution components remain
    (single-source aggregates are redundant with the X-k-Y total).
    The synthetic ``"from dice in excess of 10k10"`` entry is rendered
    in narrative form via the shared
    :func:`web.adapters._breakdown_format.format_breakdown_component`
    helper (spec 008 FR-002).
    """
    if not components:
        return ""
    filtered = [c for c in components if c.rolled != 0 or c.kept != 0]
    if len(filtered) < 2:
        return ""
    return " + ".join(
        format_breakdown_component(c.rolled, c.kept, c.source) for c in filtered
    )


def _format_dice(dice: list[int], kept: int) -> str:
    """Format a dice list with kept dice **bold** and dropped dice ~~strikethrough~~."""
    if not dice:
        return "[]"
    parts = []
    for i, d in enumerate(dice):
        if i < kept:
            parts.append(f"**{d}**")
        else:
            parts.append(f"~~{d}~~")
    return "[" + ", ".join(parts) + "]"


_MAX_HEART_EMOJI = 3
"""Cap on the number of literal 💔 emojis rendered before falling back
to a short ``💔 × N`` form. See bulleted_renderer for the rationale —
trace-reader sweep 2026-05-30 flagged long heart strings as visually
overwhelming."""


def _hearts(n: int) -> str:
    """Render ``n`` heart emojis, capped at :data:`_MAX_HEART_EMOJI`."""
    if n <= _MAX_HEART_EMOJI:
        return "💔" * n
    return f"💔 × {n}"


def _format_tn(tn: int, base_tn: int, action_skill: str) -> str:
    """Format TN clause with raise-attribution.

    Renders the raise contribution as a single ``+N`` instead of
    spelling out the per-raise factoring — the reader rarely needs
    the ``raises × +5`` arithmetic.
    """
    if tn > base_tn:
        diff = tn - base_tn
        return f"TN {tn} (base TN {base_tn} + {diff} for {action_skill})"
    return f"TN {tn} (base TN {base_tn})"


def _format_modifier_breakdown(
    modifier: int, breakdown: list[ModifierDelta],
) -> str:
    """Render the ``(Source: +N x M VP; ...)`` modifier-attribution suffix.

    When the modifier's sources don't fully account for the modifier
    value, the unattributed remainder is OMITTED rather than rendered
    as ``(see preceding line)``. The 2026-05-30 trace-reader sweep
    found that ``(see preceding line)`` was the single most-flagged
    UX defect across all 24 schools — a dangling pointer that almost
    never pointed at an actual source on the preceding line. The
    parent-header arithmetic still shows the bare number (e.g.,
    ``→ 25, +10 = 35``) so the reader sees the modifier; omitting the
    unsourced remainder removes the misleading promise of attribution
    without losing the value itself.
    """
    if modifier == 0:
        return ""
    nonzero = [m for m in breakdown if m.amount != 0]
    if nonzero and len(nonzero) == 1:
        m = nonzero[0]
        if m.source == "Mirumoto 5th Dan" and m.amount > 0 and m.amount % 10 == 0:
            vp_count = m.amount // 10
            return f" ({m.source}: +10 × {vp_count} VP)"
        sign = "+" if m.amount >= 0 else ""
        return f" ({m.source}: {sign}{m.amount})"
    parts: list[str] = []
    for m in nonzero:
        sign = "+" if m.amount >= 0 else ""
        parts.append(f"{m.source}: {sign}{m.amount}")
    if not parts:
        return ""
    return f" ({'; '.join(parts)})"


def _build_roll_str(
    dice: list[int], rolled: int, kept: int, mod: int,
    fallback_total: int, components: list[ComponentDelta] | None = None,
    consumed_floating_bonuses: list[ModifierDelta] | None = None,
) -> tuple[str, int]:
    """Build a roll description string and compute the total.

    Spec 008 FR-008/9: when ``consumed_floating_bonuses`` is non-empty,
    each bonus is integrated into the trailing arithmetic with its
    source attribution, e.g.::

        9k3 [...] → 19, +15 (Akodo 3rd Dan floating bonus) = 34
        10k4 [...] → 30, +5 = 35, +5 (Bayushi 4th Dan floating bonus) = 40

    The returned ``total`` reflects all integrations so the
    HIT/MISS determination uses the bonus-adjusted total.
    """
    kept_sum = sum(dice[:kept]) if dice else fallback_total
    total = kept_sum + mod
    breakdown = _render_components(components or [])
    xky = f"{rolled}k{kept}"
    if breakdown:
        xky = f"{rolled}k{kept} = {breakdown}"
    roll_str = f"{xky} {_format_dice(dice, kept)} → {kept_sum}"
    if mod > 0:
        roll_str += f", +{mod} = {total}"
    elif mod < 0:
        roll_str += f", {mod} = {total}"
    # Append each consumed floating bonus inline with source.
    # Skip zero-magnitude bonuses — the trace-reader sweep flagged
    # ``+0 (floating bonus) = N`` as a confusing arithmetic step
    # ("why was a bonus consumed if it added nothing?").
    if consumed_floating_bonuses:
        for fb in consumed_floating_bonuses:
            if fb.amount == 0:
                continue
            total += fb.amount
            label = fb.source or "floating bonus"
            sign = "+" if fb.amount >= 0 else ""
            roll_str += f", {sign}{fb.amount} ({label} floating bonus) = {total}"
    return roll_str, total


def _build_vp_infix_text(vp_spent: int, vp_skill: str) -> str:
    """Plain VP prefix: '⬛⬛ spends N VP on <skill> → '."""
    squares = "⬛" * vp_spent
    return f"{squares} spends {vp_spent} VP on {vp_skill} → "


def _build_vp_infix_akodo(
    vp_spent: int, vp_skill: str, vp_breakdown: str,
) -> str:
    """Akodo 4th Dan-attributed VP prefix:
    '⬛⬛ Akodo 4th Dan: spends N VP on wound check, +5 per VP = +10 (a→b) → '.
    """
    squares = "⬛" * vp_spent
    return (
        f"{squares} Akodo 4th Dan: spends {vp_spent} VP on {vp_skill}, "
        f"{vp_breakdown} → "
    )


class TextRenderer:
    """Render a list of TraceEntry objects into byte-identical legacy text lines."""

    def render_lines(self, entries: list[TraceEntry]) -> list[str]:
        """Walk entries and emit the legacy text representation.

        Some entries (RoundHeaderEntry, InitiativeEntry, StatusBlockEntry)
        need to know whether they are the *first* visible output so the
        renderer can suppress / emit the leading blank line per the
        pre-refactor invariant.
        """
        lines: list[str] = []
        for entry in entries:
            lines.extend(self._dispatch(entry, lines))
        return lines

    def _dispatch(self, entry: TraceEntry, lines_so_far: list[str]) -> list[str]:
        if isinstance(entry, RoundHeaderEntry):
            return self._render_round_header(entry, lines_so_far)
        if isinstance(entry, PhaseHeaderEntry):  # pragma: no cover  # defensive: PhaseHeaderEntry is never emitted by entries() (phase headers are embedded into action-line prefixes via _phase_prefix)
            return []
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
        if isinstance(entry, CounterDamageDealtEntry):
            return self._render_counter_damage_dealt(entry)
        if isinstance(entry, YogoThirdDanLwReductionEntry):
            return self._render_yogo_3rd_dan_lw_reduction(entry)
        if isinstance(entry, ShibaFifthDanTnReductionEntry):
            return self._render_shiba_5th_dan_tn_reduction(entry)
        if isinstance(entry, KitsukiRingReductionEntry):
            return self._render_kitsuki_ring_reduction(entry)
        if isinstance(entry, MerchantRerollEntry):
            return self._render_merchant_reroll(entry)
        if isinstance(entry, HidaThirdDanRerollEntry):
            return self._render_hida_3rd_dan_reroll(entry)
        if isinstance(entry, HidaSWForLWTradeEntry):
            return self._render_hida_sw_for_lw_trade(entry)
        if isinstance(entry, MatsuLwFloorEntry):
            return self._render_matsu_lw_floor(entry)
        if isinstance(entry, IaijutsuDuelHeaderEntry):
            return self._render_iaijutsu_duel_header(lines_so_far)
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
        if isinstance(entry, RawTextEntry):  # pragma: no cover  # defensive: RawTextEntry is the FR-007 fallback for unknown event types and is never emitted in correct operation
            return list(entry.lines)
        raise NotImplementedError(  # pragma: no cover  # defensive: every TraceEntry concrete kind is handled above; this raise is unreachable unless a new kind is added without a renderer
            f"TextRenderer cannot render entry: {entry!r}"
        )

    # ── Per-entry renderers ───────────────────────────────────────────

    def _render_round_header(
        self, entry: RoundHeaderEntry, lines_so_far: list[str],
    ) -> list[str]:
        out: list[str] = []
        if lines_so_far:
            out.append("")
        out.append(f"═══ Round {entry.round_number} ═══")
        return out

    def _render_status_block(self, entry: StatusBlockEntry) -> list[str]:
        lines = ["  ─────"]
        for name, s in entry.statuses.items():
            crippled = " | CRIPPLED" if s["crippled"] else ""
            tvp = s.get("tvp", 0)
            base_vp = s["vp"] - tvp
            if tvp > 0:
                vp_str = f"Void {base_vp}/{s['max_vp']} (+{tvp} TVP)"
            else:
                vp_str = f"Void {s['vp']}/{s['max_vp']}"
            lines.append(
                f"  {name}:  Light {s['lw']} | Serious {s['sw']}/{s['max_sw']} | "
                f"{vp_str} | Actions: {s['actions']}{crippled}"
            )
        lines.append("  ─────")
        return lines

    def _render_initiative(self, entry: InitiativeEntry) -> list[str]:
        lines = ["", "🎲 Initiative:"]
        for item in entry.entries:
            dice_str = _format_dice(item["all_dice"], item["kept"])
            lines.append(
                f"  {item['name']}: {item['rolled']}k{item['kept']} "
                f"rolled {dice_str} → Actions: {item['actions']}"
            )
        return lines

    def _render_attack(self, entry: AttackEntry) -> list[str]:
        # take-only path: ``_format_take_attack`` legacy emits
        # "⚔️ attacks Target (skill)" with no roll info.
        if entry.is_take_only:
            return [
                f"{entry.phase_prefix} ⚔️ attacks {entry.target_name} "
                f"({entry.skill})"
            ]

        vp_infix = ""
        if entry.vp_spent is not None and entry.vp_skill is not None:
            vp_infix = _build_vp_infix_text(entry.vp_spent, entry.vp_skill)

        if not entry.has_detail:
            if entry.is_combined:
                # _format_combined_attack with no _detail_dice on rolled event.
                return [
                    f"{entry.phase_prefix} {vp_infix}⚔️ attacks "
                    f"{entry.target_name} ({entry.skill}) — "
                    f"Roll: {entry.fallback_roll}"
                ]
            # _format_attack_rolled standalone with no _detail_dice.
            return [f"  Roll: {entry.fallback_roll}"]

        tn_str = _format_tn(entry.tn, entry.base_tn, entry.skill)
        roll_str, _total = _build_roll_str(
            entry.dice, entry.rolled, entry.kept, entry.modifier,
            entry.sum_of_kept, components=entry.components,
            consumed_floating_bonuses=entry.consumed_floating_bonuses,
        )

        proj = entry.damage_projection
        extras: list[str] = []
        if entry.outcome == "hit":
            if proj is not None and proj.margin_over_tn > 0 and not entry.suppress_damage_projection:
                extras.append(f"+{proj.margin_over_tn} over TN")
            if proj is not None and proj.extra_damage_dice > 0 and not entry.suppress_damage_projection:
                noun = "die" if proj.extra_damage_dice == 1 else "dice"
                extras.append(
                    f"{proj.extra_damage_dice} extra damage {noun}"
                )
            # Spec 008 FR-005: feint attacks suppress the
            # "damage will be" projection (feints always deal 0 LW).
            if proj is not None and not entry.suppress_damage_projection:
                dr, dk = proj.rolled, proj.kept
                dmg_breakdown = _render_components(proj.components)
                if dmg_breakdown:
                    extras.append(f"damage will be {dr}k{dk} = {dmg_breakdown}")
                else:
                    extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            attribution = _format_modifier_breakdown(
                entry.modifier, entry.modifier_components,
            )
            # rules/04-schools.md "Matsu Bushi School: Fourth Dan":
            # surface the near-miss carve-out with explicit attribution
            # per Constitution Principle VII / FR-021.  Appended as a
            # follow-up line (kept off the headline so the HIT! result
            # stays readable for the playtester).
            near_miss_lines: list[str] = []
            if entry.matsu_4th_dan_near_miss_below_tn > 0:
                # trace-reader #1 (2026-05-28) — explicit mechanical
                # framing so a fresh reader doesn't see "HIT!" + "near-
                # miss" and assume the renderer is wrong.  The 4th Dan
                # carve-out CONVERTS a miss within 20 of TN into a hit
                # with no extra damage, so the line states the mechanic
                # rather than just the source label.
                near_miss_lines.append(
                    f"{entry.phase_prefix} Matsu 4th Dan: counts as hit "
                    f"({entry.matsu_4th_dan_near_miss_below_tn} below TN — "
                    f"within the near-miss carve-out)"
                )
            result = "HIT!"
            if entry.is_combined:
                return [
                    f"{entry.phase_prefix} {vp_infix}⚔️ attacks "
                    f"{entry.target_name} ({entry.skill}) — {roll_str} "
                    f"vs {tn_str} — {result}{extra_str}{attribution}",
                    *near_miss_lines,
                ]
            # standalone _format_attack_rolled — uses 🎯/❌ Attack: prefix
            return [
                f"{entry.phase_prefix} 🎯 Attack: {roll_str} vs {tn_str} "
                f"— {result}{extra_str}{attribution}",
                *near_miss_lines,
            ]
        # miss
        result = "MISS"
        attribution = _format_modifier_breakdown(
            entry.modifier, entry.modifier_components,
        )
        if entry.is_combined:
            return [
                f"{entry.phase_prefix} {vp_infix}⚔️ attacks "
                f"{entry.target_name} ({entry.skill}) — {roll_str} "
                f"vs {tn_str} — {result}{attribution}"
            ]
        return [
            f"{entry.phase_prefix} ❌ Attack: {roll_str} vs {tn_str} "
            f"— {result}{attribution}"
        ]

    def _render_counterattack(self, entry: CounterattackEntry) -> list[str]:
        if entry.is_take_only:
            return [
                f"{entry.phase_prefix} ⚔️ counterattacks {entry.target_name}"
            ]

        vp_infix = ""
        if entry.vp_spent is not None and entry.vp_skill is not None:
            vp_infix = _build_vp_infix_text(entry.vp_spent, entry.vp_skill)

        if not entry.has_detail:
            if entry.is_combined:
                return [
                    f"{entry.phase_prefix} {vp_infix}⚔️ counterattacks "
                    f"{entry.target_name} — Roll: {entry.fallback_roll}"
                ]
            # standalone _format_counterattack_rolled fallback (no detail)
            return [f"  Counterattack Roll: {entry.fallback_roll}"]

        roll_str, _total = _build_roll_str(
            entry.dice, entry.rolled, entry.kept, entry.modifier,
            entry.sum_of_kept, components=entry.components,
        )

        proj = entry.damage_projection
        extras: list[str] = []
        if entry.outcome == "hit":
            if proj is not None and proj.margin_over_tn > 0:
                extras.append(f"+{proj.margin_over_tn} over TN")
            if proj is not None and proj.extra_damage_dice > 0:
                noun = "die" if proj.extra_damage_dice == 1 else "dice"
                extras.append(
                    f"{proj.extra_damage_dice} extra damage {noun}"
                )
            if proj is not None:
                dr, dk = proj.rolled, proj.kept
                dmg_breakdown = _render_components(proj.components)
                if dmg_breakdown:
                    extras.append(f"damage will be {dr}k{dk} = {dmg_breakdown}")
                else:
                    extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            attribution = _format_modifier_breakdown(
                entry.modifier, entry.modifier_components,
            )
            result = "HIT!"
            if entry.is_combined:
                return [
                    f"{entry.phase_prefix} {vp_infix}⚔️ counterattacks "
                    f"{entry.target_name} — {roll_str} vs TN {entry.tn} — "
                    f"{result}{extra_str}{attribution}"
                ]
            return [
                f"{entry.phase_prefix} 🎯 Counterattack: {roll_str} vs "
                f"TN {entry.tn} — {result}{attribution}"
            ]
        # miss
        result = "MISS"
        attribution = _format_modifier_breakdown(
            entry.modifier, entry.modifier_components,
        )
        if entry.is_combined:
            return [
                f"{entry.phase_prefix} {vp_infix}⚔️ counterattacks "
                f"{entry.target_name} — {roll_str} vs TN {entry.tn} — "
                f"{result}{attribution}"
            ]
        return [
            f"{entry.phase_prefix} ❌ Counterattack: {roll_str} vs "
            f"TN {entry.tn} — {result}{attribution}"
        ]

    def _render_parry(self, entry: ParryEntry) -> list[str]:
        if entry.is_take_only:
            return [
                f"{entry.phase_prefix} 🛡️ parries {entry.target_name}"
            ]

        if not entry.has_detail:
            if entry.is_combined:
                return [
                    f"{entry.phase_prefix} 🛡️ parries {entry.target_name} — "
                    f"Roll: {entry.fallback_roll}"
                ]
            # standalone _format_parry_rolled fallback (no detail)
            return [
                f"{entry.phase_prefix} 🛡️ Parry roll: {entry.fallback_roll}"
            ]

        kept_sum = entry.sum_of_kept
        total = entry.total
        mod = entry.modifier
        rolled = entry.rolled
        kept = entry.kept
        roll_str = (
            f"{rolled}k{kept} {_format_dice(entry.dice, kept)} → {kept_sum}"
        )
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"
        result = "SUCCEEDED" if entry.outcome == "succeeded" else "FAILED"
        attribution = _format_modifier_breakdown(
            entry.modifier, entry.modifier_components,
        )
        if entry.is_combined:
            return [
                f"{entry.phase_prefix} 🛡️ parries {entry.target_name} — "
                f"{roll_str} vs TN {entry.tn} — {result}{attribution}"
            ]
        return [
            f"{entry.phase_prefix} 🛡️ Parry: {roll_str} "
            f"vs TN {entry.tn} — {result}{attribution}"
        ]

    def _render_iaijutsu(self, entry: IaijutsuEntry) -> list[str]:
        margin = abs(entry.skill_roll - entry.opponent_skill_roll)
        if entry.skill_roll > entry.opponent_skill_roll:
            result = "WON"
        elif entry.skill_roll < entry.opponent_skill_roll:
            result = "LOST"
        else:
            result = "TIED"

        if entry.has_detail:
            roll_str = (
                f"{entry.rolled}k{entry.kept} "
                f"{_format_dice(entry.dice, entry.kept)} → {entry.sum_of_kept}"
            )
            if entry.effective_modifier > 0:
                roll_str += (
                    f", +{entry.effective_modifier} = {entry.skill_roll}"
                )
            elif entry.effective_modifier < 0:
                roll_str += (
                    f", {entry.effective_modifier} = {entry.skill_roll}"
                )
        else:
            roll_str = str(entry.skill_roll)

        if entry.is_challenger:
            label = "⚔️ Contested Iaijutsu (5th Dan)"
            extras = [f"+{margin}" if margin > 0 else ""]
            if result == "WON" and entry.extra_damage_dice > 0:
                noun = "die" if entry.extra_damage_dice == 1 else "dice"
                extras.append(f"{entry.extra_damage_dice} extra damage {noun}")
            elif result == "LOST" and entry.extra_damage_dice < 0:
                extras.append(
                    f"{abs(entry.extra_damage_dice)} fewer damage dice"
                )
            extras = [e for e in extras if e]
            extra_str = f" ({', '.join(extras)})" if extras else ""
        else:
            label = f"⚔️ Contested Iaijutsu ({entry.skill})"
            extras = [f"+{margin}" if margin > 0 else ""]
            extras = [e for e in extras if e]
            extra_str = f" ({', '.join(extras)})" if extras else ""

        return [
            f"{entry.phase_prefix} {label}: {roll_str} vs "
            f"{entry.opponent_skill_roll} — {result}{extra_str}"
        ]

    def _render_lw_damage(self, entry: LightWoundsDamageEntry) -> list[str]:
        if not entry.has_detail:
            return [
                f"{entry.phase_prefix} 💥 takes {entry.damage} light wounds"
            ]
        breakdown_str = _render_components(entry.components)
        xky = f"{entry.rolled}k{entry.kept}"
        if breakdown_str:
            xky = f"{entry.rolled}k{entry.kept} = {breakdown_str}"
        total_str = (
            f" (total: {entry.lw_after})" if entry.lw_after is not None else ""
        )
        return [
            f"{entry.phase_prefix} 💥 Damage: {xky} "
            f"{_format_dice(entry.dice, entry.kept)} → {entry.sum_of_kept} → "
            f"{entry.target_name} takes {entry.damage} light wounds{total_str}"
        ]

    def _render_sw_damage(self, entry: SeriousWoundsDamageEntry) -> list[str]:
        hearts = _hearts(entry.damage)
        noun = "wound" if entry.damage == 1 else "wounds"
        if entry.from_mirumoto_4th_dan:
            suffix = (
                " (Mirumoto 4th Dan: auto-SW lands despite failed parry)"
            )
        elif entry.from_double_attack:
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
        # Build the VP-prefix text infix.
        vp_infix = ""
        if entry.vp_spent is not None and entry.vp_skill is not None:
            if entry.vp_source == "Akodo 4th Dan" and entry.vp_breakdown:
                vp_infix = _build_vp_infix_akodo(
                    entry.vp_spent, entry.vp_skill, entry.vp_breakdown,
                )
            else:
                vp_infix = _build_vp_infix_text(entry.vp_spent, entry.vp_skill)

        # Choose emoji based on the legacy rules:
        # - standalone passed → 💔
        # - standalone failed → 🖤
        # - keep_lw follow-up → 🖤
        # - take_sw follow-up → 💔 repeated per SW count
        if entry.follow_up == "keep_lw":
            emoji = "🖤"
        elif entry.follow_up == "take_sw":
            emoji = _hearts(entry.follow_up_sw_count)
        else:
            emoji = "💔" if entry.outcome == "passed" else "🖤"

        if not entry.has_detail:
            result = "PASSED" if entry.outcome == "passed" else "FAILED"
            wc_str = (
                f"{entry.phase_prefix} {vp_infix}{emoji} Wound Check: "
                f"rolled {entry.fallback_roll} vs TN {entry.tn} — {result}"
            )
        else:
            mod = entry.modifier
            roll_str = (
                f"{entry.rolled}k{entry.kept} "
                f"{_format_dice(entry.dice, entry.kept)} → {entry.sum_of_kept}"
            )
            if mod > 0:
                roll_str += f", +{mod} = {entry.total}"
            elif mod < 0:
                roll_str += f", {mod} = {entry.total}"
            result = "PASSED" if entry.outcome == "passed" else "FAILED"
            wc_str = (
                f"{entry.phase_prefix} {vp_infix}{emoji} Wound Check: "
                f"{roll_str} vs TN {entry.tn} — {result}"
            )
            wc_str += _format_modifier_breakdown(
                entry.modifier, entry.modifier_components,
            )

        # rules/04-schools.md "Hida Bushi School: Fifth Dan": surface
        # the counterattack-excess WC bonus on the WC line.  Principle VII
        # requires an explicit numeric breakdown with source attribution.
        if entry.hida_5th_dan_excess_bonus:
            wc_str += (
                f" [Hida 5th Dan: counterattack excess "
                f"+{entry.hida_5th_dan_excess_bonus}]"
            )

        # rules/04-schools.md "Bayushi Bushi School: Fifth Dan": surface
        # the half-LW SW computation on the WC line.  Principle VII
        # requires the trace to identify that the SW count was modified
        # by the school ability AND show the actual vs halved LW values.
        if entry.bayushi_5th_dan_halved_lw_actual:
            halved = entry.bayushi_5th_dan_halved_lw_actual // 2
            wc_str += (
                f" [Bayushi 5th Dan: SW vs halved LW "
                f"({entry.bayushi_5th_dan_halved_lw_actual} → {halved})]"
            )

        if entry.follow_up == "keep_lw":
            return [f"{wc_str} → keeping {entry.follow_up_lw_total} light wounds"]
        if entry.follow_up == "take_sw":
            noun = "wound" if entry.follow_up_sw_count == 1 else "wounds"
            voluntary = entry.follow_up_voluntary
            if voluntary:
                sw_str = (
                    f"chooses to take {entry.follow_up_sw_count} serious {noun}"
                )
            else:
                sw_str = f"takes {entry.follow_up_sw_count} serious {noun}"
            # Surface the silent LW reset so the next status block's
            # ``Light 0`` makes sense (trace-reader sweep 2026-05-30).
            if entry.lw_before_check > 0:
                sw_str = f"{sw_str} (LW {entry.lw_before_check} → 0)"
            return [f"{wc_str} → {sw_str}"]
        return [wc_str]

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
        return [
            f"{entry.phase_prefix} ✨ gains +{entry.amount} TVP"
        ]

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
        # Suppress zero-magnitude consume events — trace-reader sweep
        # flagged these as confusing ("why was a bonus spent if it
        # added nothing?"). See bulleted_renderer for matching change.
        if entry.amount == 0:
            return []
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

    def _render_counter_damage_dealt(
        self, entry: CounterDamageDealtEntry,
    ) -> list[str]:
        # Mirror standard ``💥 takes N light wounds (total: K)`` so
        # the counter-damaged character's LW total surfaces inline.
        return [
            f"{entry.phase_prefix} 💥 takes {entry.damage} light wounds "
            f"(total: {entry.lw_after})"
        ]

    def _render_yogo_3rd_dan_lw_reduction(
        self, entry: YogoThirdDanLwReductionEntry,
    ) -> list[str]:
        return [
            f"{entry.phase_prefix} 🩹 Yogo 3rd Dan: LW -{entry.reduction} "
            f"(= 2 × attack {entry.attack_skill} × {entry.vp_spent} VP) "
            f"→ total: {entry.lw_after}"
        ]

    def _render_shiba_5th_dan_tn_reduction(
        self, entry: ShibaFifthDanTnReductionEntry,
    ) -> list[str]:
        return [
            f"{entry.phase_prefix} 🔻 Shiba 5th Dan: TN to hit "
            f"{entry.target_name} lowered by {entry.margin} on next attack "
            f"(parry margin)"
        ]

    def _render_kitsuki_ring_reduction(
        self, entry: KitsukiRingReductionEntry,
    ) -> list[str]:
        deltas = ", ".join(
            f"{r.title()} {v}→{max(1, v - 1)}"
            for r, v in entry.ring_values_before.items()
        )
        return [
            f"{entry.phase_prefix} 🔻 Kitsuki 5th Dan: reduces "
            f"{entry.target_name}'s rings — {deltas}"
        ]

    def _render_merchant_reroll(
        self, entry: MerchantRerollEntry,
    ) -> list[str]:
        pairs = ", ".join(f"{b}→{a}" for (b, a) in entry.rerolled_pairs)
        return [
            f"{entry.phase_prefix} 🎲 Merchant 5th Dan: rerolled "
            f"{pairs} (on {entry.roll_type} roll)"
        ]

    def _render_akodo_5th_dan_counter(
        self, entry: AkodoFifthDanCounterEntry,
    ) -> list[str]:
        # See bulleted_renderer._render_akodo_5th_dan_counter for the
        # "per VP" rationale (trace-reader sweep 2026-05-30).
        squares = "⬛" * entry.vp_spent
        return [
            f"{entry.phase_prefix} {squares} Akodo 5th Dan: "
            f"spends {entry.vp_spent} VP on counter-damage, "
            f"10 LW per VP × {entry.vp_spent} VP = {entry.damage} LW "
            f"dealt to {entry.target_name}"
        ]

    def _render_hida_3rd_dan_reroll(
        self, entry: HidaThirdDanRerollEntry,
    ) -> list[str]:
        """Hida 3rd Dan reroll line.

        Format::

            <prefix> 🎲 Hida 3rd Dan: reroll 2→7, 1→6 (N=2; kept-sum 10→23)

        Includes "(impaired)" when the reroll fired in crippled state
        (the carve-out kept 10s exploding).  Per Constitution
        Principle VII, every die change is rendered with its before
        and after value, and the source label "Hida 3rd Dan" is
        explicit.

        Note (2026-05-28, trace-reader #1 fix): the trailing pair is
        labeled "kept-sum" (not "total") because post-roll modifiers
        like the Hida 2nd Dan +5 free raise on counterattack are
        applied AFTER the reroll-derived sum and therefore appear in
        the parent ``Roll: N`` header but NOT in this sub-line.  The
        explicit label prevents the reader from comparing the two
        numbers and seeing a phantom mismatch.
        """
        pairs = ", ".join(f"{b}→{a}" for (b, a) in entry.rerolls)
        impaired = " (impaired)" if entry.crippled else ""
        return [
            f"{entry.phase_prefix} 🎲 Hida 3rd Dan: reroll {pairs} "
            f"(N={entry.n}{impaired}; kept-sum {entry.before_total}→"
            f"{entry.after_total})"
        ]

    def _render_hida_sw_for_lw_trade(
        self, entry: HidaSWForLWTradeEntry,
    ) -> list[str]:
        """Hida 4th Dan SW-for-LW trade line.

        Format::

            <prefix> 🛡️ Hida 4th Dan: take 2 SW to reset LW from N → 0
                (alternative wound check)

        Per Constitution Principle VII the trade carries the explicit
        source label "Hida 4th Dan", the numeric SW cost ("take 2 SW"),
        and the LW value being reset ("reset LW from N").  No
        wound-check roll is rendered because the trade replaces it.

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
        """Matsu 5th Dan LW-floor attribution line.

        Format::

            <prefix> Matsu 5th Dan: defender LW set to 15 (instead of 0)

        Per Constitution Principle VII the line carries the explicit
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

    def _render_iaijutsu_duel_header(self, lines_so_far: list[str]) -> list[str]:
        return ["", "═══ Iaijutsu Duel ═══"]

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
                f"{_format_dice(entry.dice, entry.kept)})"
            )
        return [
            f"{entry.character_name} | 🔍 Stance: rolled {entry.roll}{dice_info}"
            f" — discerns Fire ~{entry.discerned_fire}, "
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
                f"{_format_dice(entry.dice, entry.kept)}"
            )
        if entry.is_hit:
            result = "HIT!"
            extra = (
                f" (+{entry.extra_damage_dice} extra damage dice)"
                if entry.extra_damage_dice > 0 else ""
            )
            return [
                f"{entry.character_name} | ⚔️ Strike vs {entry.target_name}:"
                f"{dice_info} {entry.roll} vs TN {entry.tn} — {result}{extra}"
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


_ = Any  # keep `Any` referenced in case future code needs it
