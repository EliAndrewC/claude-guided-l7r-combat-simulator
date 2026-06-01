"""ChronicleRenderer — sumi-e HTML rendering for the Streamlit trace.

This is the "Iteration 3" companion to ``BulletedRenderer``.  It walks
the same ``list[TraceEntry]`` snapshot and produces a single HTML
string suitable for ``st.markdown(html, unsafe_allow_html=True)`` —
each entry becomes a styled sumi-e "event card" with phase badge,
actor name, dice tiles (kept / dropped / crit), outcome stamp, and
attributed modifier pills.

Design rationale (matches the ``web/views/_chronicle.py`` theme):

  * Combat events with rolls (attack / counterattack / parry /
    iaijutsu / damage / wound-check) get bespoke HTML cards.
  * Structural entries (round header, status block, initiative) get
    their own ink-on-paper presentation matching the surrounding
    chronicle.
  * Terminal outcome entries (death / unconscious / surrender) get
    a dramatic ink-block treatment.
  * Anything else (school-identity events, floating-bonus consume,
    take-SW, etc.) delegates to ``BulletedRenderer._dispatch`` and
    is wrapped in a low-weight "generic" event row so unrendered
    entries still appear in the trace without breaking flow.

This module imports from ``web.adapters.bulleted_renderer`` (same
adapter layer) but never from ``simulation/`` — Constitution
Principle II is preserved.
"""

from __future__ import annotations

import html
from typing import Any

from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.trace_entries import (
    AttackEntry,
    ComponentDelta,
    CounterattackEntry,
    DeathEntry,
    InitiativeEntry,
    LightWoundsDamageEntry,
    ModifierDelta,
    ParryEntry,
    RoundHeaderEntry,
    SeriousWoundsDamageEntry,
    StatusBlockEntry,
    SurrenderEntry,
    TraceEntry,
    UnconsciousEntry,
    WoundCheckEntry,
)

_ROMAN_NUMERALS = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
    6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
    11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
    16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX",
}

# Modifier sources whose names contain these substrings get the
# "school" pill class (vermillion outline + colour) instead of the
# default ink-on-paper pill.  All current school-attribution labels
# follow the "<School> Nth Dan" / "<School> Special Ability" naming
# convention, so a single substring whitelist is sufficient.
_SCHOOL_SOURCE_HINTS = (
    "Dan", "Special Ability", "free raise", "post-parry bonus",
    "ally boost", "school formula", "tempo bonus", "VP raises",
)

# Weapon names (lower-case) that trigger the "weapon" pill class on
# damage breakdowns — heavy black border to distinguish from rings
# and school contributions.
_WEAPONS = {
    "katana", "wakizashi", "tanto", "yari", "club", "unarmed",
    "gongfu", "knife", "sword", "spear",
}


def _esc(s: Any) -> str:
    """Escape a value for safe HTML interpolation."""
    return html.escape(str(s))


def _pill_class_for(source: str) -> str:
    """Pick the CSS class for a modifier/component pill based on its
    source label."""
    if any(h in source for h in _SCHOOL_SOURCE_HINTS):
        return "pill school"
    if source.lower() in _WEAPONS:
        return "pill weapon"
    return "pill"


def _phase_badge(prefix: str) -> str:
    """Extract the "Phase N" prefix into a compact badge.  Falls back
    to the literal prefix if the shape doesn't match — the events
    that lack a phase prefix render empty here, which is fine."""
    p = prefix.strip().rstrip("|").strip()
    if p.lower().startswith("phase "):
        return p.split(" ", 1)[1].rstrip(" |").strip()
    return p  # pragma: no cover  # defensive: every detail-formatter entry uses "Phase N" form


def _render_dice(dice: list[int], kept: int) -> str:
    """Render the dice list as a row of tiles, kept dice bold, dropped
    dice struck-through, 10s as 'crit'.  ``dice`` is assumed sorted
    descending (the formatter's convention)."""
    if not dice:
        return ""
    cells = []
    for i, d in enumerate(dice):
        classes = ["die"]
        if i >= kept:
            classes.append("dropped")
        elif d >= 10:
            classes.append("crit")
        cells.append(f'<span class="{" ".join(classes)}">{_esc(d)}</span>')
    return "".join(cells)


def _render_pills(
    components: list[ComponentDelta] | None,
    modifier_components: list[ModifierDelta] | None = None,
) -> str:
    """Render the per-source breakdown as a horizontal row of pills."""
    parts: list[str] = []
    if components:
        for c in components:
            if c.rolled == 0 and c.kept == 0:
                continue
            cls = _pill_class_for(c.source)
            value = f"{c.rolled}k{c.kept}"
            parts.append(
                f'<span class="{cls}">'
                f'<span class="src">{_esc(c.source)}</span>'
                f'<span class="v">{_esc(value)}</span>'
                '</span>'
            )
    if modifier_components:
        for m in modifier_components:
            if m.amount == 0:
                continue
            cls = _pill_class_for(m.source)
            sign = "+" if m.amount > 0 else ""
            parts.append(
                f'<span class="{cls}">'
                f'<span class="src">{_esc(m.source)}</span>'
                f'<span class="v">{sign}{_esc(m.amount)}</span>'
                '</span>'
            )
    if not parts:
        return ""
    return f'<div class="pills">{"".join(parts)}</div>'


class ChronicleRenderer:
    """Render a list of TraceEntries into a single sumi-e HTML string."""

    def __init__(self) -> None:
        self._fallback = BulletedRenderer()

    def render(self, entries: list[TraceEntry]) -> str:
        """Walk entries and return the concatenated HTML string."""
        out: list[str] = []
        for entry in entries:
            out.append(self._dispatch(entry))
        return "\n".join(p for p in out if p)

    def _dispatch(self, entry: TraceEntry) -> str:
        if isinstance(entry, RoundHeaderEntry):
            return self._render_round(entry)
        if isinstance(entry, StatusBlockEntry):
            return self._render_status(entry)
        if isinstance(entry, InitiativeEntry):
            return self._render_initiative(entry)
        if isinstance(entry, AttackEntry):
            return self._render_attack(entry)
        if isinstance(entry, CounterattackEntry):
            return self._render_counterattack(entry)
        if isinstance(entry, ParryEntry):
            return self._render_parry(entry)
        if isinstance(entry, LightWoundsDamageEntry):
            return self._render_lw_damage(entry)
        if isinstance(entry, SeriousWoundsDamageEntry):
            return self._render_sw_damage(entry)
        if isinstance(entry, WoundCheckEntry):
            return self._render_wound_check(entry)
        if isinstance(entry, DeathEntry):
            return self._render_terminal(entry, "death", "✖ falls", entry.character_name)
        if isinstance(entry, UnconsciousEntry):
            return self._render_terminal(entry, "fall", "✶ falls unconscious", entry.character_name)
        if isinstance(entry, SurrenderEntry):
            return self._render_terminal(entry, "fall", "❋ surrenders", entry.character_name)
        return self._render_generic(entry)

    # ── Specific renderers ──────────────────────────────────────

    def _render_round(self, entry: RoundHeaderEntry) -> str:
        n = entry.round_number
        roman = _ROMAN_NUMERALS.get(n, str(n))
        return (
            '<div class="chronicle-round-divider">'
            f'<span class="roman-numeral">{_esc(roman)}</span>'
            f'<span class="roman">Round {_esc(n)}</span>'
            '<span class="line"></span>'
            '</div>'
        )

    def _render_status(self, entry: StatusBlockEntry) -> str:
        cells = []
        for name, status in entry.statuses.items():
            lw = status.get("lw", 0)
            sw = status.get("sw", 0)
            sw_threshold = status.get("sw_threshold", 1)
            vp = status.get("vp", 0)
            vp_max = status.get("vp_max", 1)
            actions = status.get("actions", [])
            crippled = bool(status.get("crippled", False))
            who_cls = "crippled" if crippled else ""
            # widths: LW saturates at 50 (visual approximation), SW at threshold,
            # VP at max.
            lw_pct = min(100, int(lw * 100 / 50)) if lw else 0
            sw_pct = int(sw * 100 / sw_threshold) if sw_threshold else 0
            vp_pct = int(vp * 100 / vp_max) if vp_max else 0
            actions_html = (
                f'<div class="bar"><div class="label">Actions</div>'
                f'<div class="num">{_esc(str(actions))}</div></div>'
                if actions is not None else ""
            )
            cells.append(
                '<div>'
                f'<div class="who {who_cls}">{_esc(name)}</div>'
                '<div class="meta-bars">'
                f'<div class="bar lw"><div class="label">LW</div>'
                f'<div class="track"><div class="fill" style="width:{lw_pct}%"></div></div>'
                f'<div class="num">{_esc(lw)}</div></div>'
                f'<div class="bar sw"><div class="label">SW</div>'
                f'<div class="track"><div class="fill" style="width:{sw_pct}%"></div></div>'
                f'<div class="num">{_esc(sw)}/{_esc(sw_threshold)}</div></div>'
                f'<div class="bar void"><div class="label">VP</div>'
                f'<div class="track"><div class="fill" style="width:{vp_pct}%"></div></div>'
                f'<div class="num">{_esc(vp)}/{_esc(vp_max)}</div></div>'
                f'{actions_html}'
                '</div>'
                '</div>'
            )
        return f'<div class="chronicle-evt-status">{"".join(cells)}</div>'

    def _render_initiative(self, entry: InitiativeEntry) -> str:
        rows = []
        for e in entry.entries:
            name = e.get("name", "")
            rolled = e.get("rolled", 0)
            kept = e.get("kept", 0)
            dice = e.get("dice", [])
            actions = e.get("actions", [])
            dice_row = _render_dice(dice, kept)
            rows.append(
                '<div class="row">'
                f'<span class="who">{_esc(name)}</span>'
                f'<span class="dim">{_esc(rolled)}k{_esc(kept)}</span>'
                f'<div class="dice" style="margin-top:0">{dice_row}</div>'
                f'<span class="actions">→ Actions {_esc(actions)}</span>'
                '</div>'
            )
        return (
            '<div class="chronicle-evt-initiative">'
            '<div class="h">🎲 Initiative</div>'
            f'{"".join(rows)}'
            '</div>'
        )

    def _render_attack(self, entry: AttackEntry) -> str:
        is_crit = entry.outcome == "hit" and (
            entry.damage_projection is not None
            and entry.damage_projection.extra_damage_dice >= 4
        )
        klass = "crit" if is_crit else ""
        skill = entry.skill
        vp_squares = "⬛" * (entry.vp_spent or 0)
        vp_clause = (
            f'<span class="dim"> {vp_squares} {entry.vp_spent} VP </span>'
            if entry.vp_spent else ""
        )
        margin = ""
        if entry.outcome == "hit" and entry.damage_projection is not None:
            extra = entry.damage_projection.extra_damage_dice
            extra_clause = f", <span class='red'>{extra} extra dmg dice</span>" if extra > 0 else ""
            margin = (
                f' (<span class="strong">+{entry.damage_projection.margin_over_tn}</span> over TN'
                f'{extra_clause})'
            )
        body = (
            f"{vp_clause}⚔  attacks <span class='strong'>{_esc(entry.target_name)}</span> "
            f"<span class='dim'>·</span> <span class='strong'>{_esc(skill)}</span>{margin}"
        )
        dice_row = _render_dice(entry.dice, entry.kept)
        modifier_clause = ""
        if entry.modifier:
            sign = "+" if entry.modifier > 0 else ""
            modifier_clause = f' <span class="dim">{sign}{entry.modifier}</span>'
        total = (
            f'<span class="total">{entry.rolled}k{entry.kept} → '
            f'{entry.sum_of_kept}{modifier_clause} = {entry.total}'
            f'<span class="vs-tn">vs TN {entry.tn}</span></span>'
        )
        outcome_label = "HIT" if entry.outcome == "hit" else "MISS"
        outcome_class = "hit" if entry.outcome == "hit" else "miss"
        pills = _render_pills(entry.components, entry.modifier_components)
        proj_pills = ""
        if entry.damage_projection is not None and not entry.suppress_damage_projection:
            dp = entry.damage_projection
            proj_pills = (
                f'<div class="pills"><span class="pill" style="border-style:dashed">'
                f'<span class="src">damage will be</span>'
                f'<span class="v">{dp.rolled}k{dp.kept}</span></span>'
                + "".join(
                    f'<span class="{_pill_class_for(c.source)}">'
                    f'<span class="src">{_esc(c.source)}</span>'
                    f'<span class="v">{c.rolled}k{c.kept}</span>'
                    '</span>'
                    for c in dp.components if c.rolled or c.kept
                )
                + '</div>'
            )
        dice_block = (
            f'<div class="dice">{dice_row}<span class="arrow">→</span>'
            f'{total}<span class="outcome {outcome_class}">{outcome_label}</span></div>'
        )
        return (
            f'<div class="chronicle-evt {klass}">'
            f'<div class="meta">'
            f'<span class="phase">P{_phase_badge(entry.phase_prefix)}</span>'
            f'<span class="actor">{_esc(entry.actor_name)}</span>'
            f'</div>'
            f'<div class="body">{body}</div>'
            f'{dice_block}'
            f'{pills}'
            f'{proj_pills}'
            '</div>'
        )

    def _render_counterattack(self, entry: CounterattackEntry) -> str:
        vp_squares = "⬛" * (entry.vp_spent or 0)
        vp_clause = (
            f'<span class="dim"> {vp_squares} {entry.vp_spent} VP </span>'
            if entry.vp_spent else ""
        )
        body = (
            f"{vp_clause}⚔  counter-attacks "
            f"<span class='strong'>{_esc(entry.target_name)}</span>"
        )
        dice_row = _render_dice(entry.dice, entry.kept)
        modifier_clause = ""
        if entry.modifier:
            sign = "+" if entry.modifier > 0 else ""
            modifier_clause = f' <span class="dim">{sign}{entry.modifier}</span>'
        total = (
            f'<span class="total">{entry.rolled}k{entry.kept} → '
            f'{entry.sum_of_kept}{modifier_clause} = {entry.total}'
            f'<span class="vs-tn">vs TN {entry.tn}</span></span>'
        )
        outcome_label = "HIT" if entry.outcome == "hit" else "MISS"
        outcome_class = "hit" if entry.outcome == "hit" else "miss"
        pills = _render_pills(entry.components, entry.modifier_components)
        dice_block = (
            f'<div class="dice">{dice_row}<span class="arrow">→</span>'
            f'{total}<span class="outcome {outcome_class}">{outcome_label}</span></div>'
        )
        return (
            f'<div class="chronicle-evt">'
            f'<div class="meta">'
            f'<span class="phase">P{_phase_badge(entry.phase_prefix)}</span>'
            f'<span class="actor">{_esc(entry.actor_name)}</span>'
            '</div>'
            f'<div class="body">{body}</div>'
            f'{dice_block}'
            f'{pills}'
            '</div>'
        )

    def _render_parry(self, entry: ParryEntry) -> str:
        body = (
            f"🛡  parries <span class='strong'>{_esc(entry.target_name)}</span>"
        )
        dice_row = _render_dice(entry.dice, entry.kept)
        modifier_clause = ""
        if entry.modifier:
            sign = "+" if entry.modifier > 0 else ""
            modifier_clause = f' <span class="dim">{sign}{entry.modifier}</span>'
        total = (
            f'<span class="total">{entry.rolled}k{entry.kept} → '
            f'{entry.sum_of_kept}{modifier_clause} = {entry.total}'
            f'<span class="vs-tn">vs TN {entry.tn}</span></span>'
        )
        outcome_label = entry.outcome.upper()
        outcome_class = entry.outcome
        pills = _render_pills(entry.components, entry.modifier_components)
        dice_block = (
            f'<div class="dice">{dice_row}<span class="arrow">→</span>'
            f'{total}<span class="outcome {outcome_class}">{outcome_label}</span></div>'
        )
        return (
            f'<div class="chronicle-evt">'
            f'<div class="meta">'
            f'<span class="phase">P{_phase_badge(entry.phase_prefix)}</span>'
            f'<span class="actor">{_esc(entry.actor_name)}</span>'
            '</div>'
            f'<div class="body">{body}</div>'
            f'{dice_block}'
            f'{pills}'
            '</div>'
        )

    def _render_lw_damage(self, entry: LightWoundsDamageEntry) -> str:
        lw_clause = (
            f"(total {entry.lw_after})" if entry.lw_after is not None else ""
        )
        body = (
            f"💥 damage <span class='strong'>{entry.rolled}k{entry.kept}</span> "
            f"→ <span class='strong'>{_esc(entry.target_name)}</span> takes "
            f"<span class='red'>{entry.damage} LW</span> "
            f"<span class='dim'>{_esc(lw_clause)}</span>"
        )
        dice_row = _render_dice(entry.dice, entry.kept)
        total = (
            f'<span class="total">→ {entry.sum_of_kept}</span>'
        )
        pills = _render_pills(entry.components, None)
        dice_block = (
            f'<div class="dice">{dice_row}<span class="arrow">→</span>{total}</div>'
            if entry.dice else ""
        )
        return (
            f'<div class="chronicle-evt crit">'
            f'<div class="meta">'
            f'<span class="phase">P{_phase_badge(entry.phase_prefix)}</span>'
            f'<span class="actor">{_esc(entry.attacker_name)}</span>'
            '</div>'
            f'<div class="body">{body}</div>'
            f'{dice_block}'
            f'{pills}'
            '</div>'
        )

    def _render_sw_damage(self, entry: SeriousWoundsDamageEntry) -> str:
        from_da = " <span class='dim'>(from double attack)</span>" if entry.from_double_attack else ""
        body = (
            f"💔 <span class='strong'>{_esc(entry.target_name)}</span> takes "
            f"<span class='red'>{entry.damage} serious wound"
            f"{'s' if entry.damage != 1 else ''}</span>{from_da}"
        )
        return (
            f'<div class="chronicle-evt crit">'
            f'<div class="meta">'
            f'<span class="phase">P{_phase_badge(entry.phase_prefix)}</span>'
            f'<span class="actor">{_esc(entry.target_name)}</span>'
            '</div>'
            f'<div class="body">{body}</div>'
            '</div>'
        )

    def _render_wound_check(self, entry: WoundCheckEntry) -> str:
        body = (
            f"🖤 wound check <span class='strong'>{entry.rolled}k{entry.kept}</span> "
            f"vs TN <span class='strong'>{entry.tn}</span>"
        )
        dice_row = _render_dice(entry.dice, entry.kept)
        modifier_clause = ""
        if entry.modifier:
            sign = "+" if entry.modifier > 0 else ""
            modifier_clause = f' <span class="dim">{sign}{entry.modifier}</span>'
        total = (
            f'<span class="total">{entry.sum_of_kept}{modifier_clause} = {entry.total}'
            f'<span class="vs-tn">vs TN {entry.tn}</span></span>'
        )
        outcome_label = "PASSED" if entry.outcome == "passed" else "FAILED"
        outcome_class = "passed" if entry.outcome == "passed" else "failed"
        pills = _render_pills(None, entry.modifier_components)
        if entry.dice:
            dice_block = (
                f'<div class="dice">{dice_row}<span class="arrow">→</span>'
                f'{total}<span class="outcome {outcome_class}">{outcome_label}</span></div>'
            )
        else:
            # No dice rolled (zero-dice fallback path): still show the
            # outcome stamp so the reader sees PASSED/FAILED.
            dice_block = (
                f'<div class="dice">'
                f'<span class="outcome {outcome_class}">{outcome_label}</span></div>'
            )
        return (
            f'<div class="chronicle-evt">'
            f'<div class="meta">'
            f'<span class="phase">P{_phase_badge(entry.phase_prefix)}</span>'
            f'<span class="actor">{_esc(entry.character_name)}</span>'
            '</div>'
            f'<div class="body">{body}</div>'
            f'{dice_block}'
            f'{pills}'
            '</div>'
        )

    def _render_terminal(
        self, entry: Any, klass: str, kind_label: str, character: str,
    ) -> str:
        phase = _phase_badge(getattr(entry, "phase_prefix", ""))
        return (
            f'<div class="chronicle-evt {klass}">'
            f'<div class="meta">'
            f'<span class="phase">P{_esc(phase)}</span>'
            f'<span class="actor">{_esc(character)}</span>'
            f' <span class="kind">{kind_label}</span>'
            '</div>'
            f'<div class="body">{_esc(character)} {kind_label}.</div>'
            '</div>'
        )

    def _render_generic(self, entry: TraceEntry) -> str:
        """Fallback: delegate to BulletedRenderer's markdown output and
        wrap each line in a low-weight generic event row.  Empty
        delegate output is skipped silently."""
        lines = self._fallback._dispatch(entry)
        rendered = [
            f'<div class="chronicle-evt-generic">{line}</div>'
            for line in lines if line.strip()
        ]
        return "".join(rendered)
