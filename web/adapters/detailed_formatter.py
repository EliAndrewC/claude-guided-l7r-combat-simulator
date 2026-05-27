"""DetailedEventFormatter for rich combat play-by-play output with emojis and combined events."""

from typing import Any

from simulation import events
from simulation.duel import (
    DuelEndedEvent,
    DuelInitiativeRolledEvent,
    DuelResheathEvent,
    DuelStrikeRolledEvent,
    IaijutsuDuelEvent,
    IaijutsuFocusEvent,
    IaijutsuStrikeEvent,
    ShowMeYourStanceDeclaredEvent,
    ShowMeYourStanceRolledEvent,
)
from simulation.events import (
    CounterattackDeclaredEvent,
    CounterattackFailedEvent,
    CounterattackRolledEvent,
    CounterattackSucceededEvent,
    TakeCounterattackActionEvent,
)
from simulation.schools.kakita_school import (
    ContestedIaijutsuAttackDeclaredEvent,
    ContestedIaijutsuAttackRolledEvent,
    TakeContestedIaijutsuAttackAction,
)


def _compute_damage_breakdown(
    subject: Any, target: Any, action: Any, attack_extra_rolled: int,
) -> list[tuple[str, int, int]]:
    """Compute the predictive damage breakdown for the attack-line
    "damage will be XkY" projection (FR-007).

    Calls the subject's roll-parameter provider's ``get_breakdown`` with
    the same ``attack_extra_rolled`` and ``vp`` the engine will use for
    the damage roll. Returns an empty list when the provider doesn't
    implement ``get_breakdown`` (legacy providers) — the formatter then
    omits the breakdown.
    """
    provider = subject.roll_parameter_provider()
    if not hasattr(provider, "get_breakdown"):
        return []
    try:
        result: list[tuple[str, int, int]] = provider.get_breakdown(
            subject, target, action.skill(),
            kind="damage",
            attack_extra_rolled=attack_extra_rolled,
            vp=action.vp(),
        )
    except Exception:
        return []
    if not isinstance(result, list):
        return []
    return result


def _render_components(components: list[tuple[str, int, int]] | None) -> str:
    """Render a ``_detail_components`` annotation as an inline breakdown.

    Format: ``"N1k(M1) source-1 + N2k(M2) source-2 + ..."``. Per FR-006:

    - Returns an empty string when there are no components, when fewer
      than 2 entries have nonzero contributions, or when the annotation
      is missing entirely. A trivial single-source case is the same as
      the aggregate and is omitted (Edge Cases: "Aggregate with only
      ONE source").
    - Filters zero-contribution entries (both ``rolled == 0`` AND
      ``kept == 0``) — OPEN_QUESTIONS Q6 (Zero-contribution component
      omission). Entries with nonzero rolled OR kept are retained
      (e.g., a kept-only contribution like ``+0k2`` is meaningful).
    """
    if not components:
        return ""
    filtered = [
        (label, r, k) for label, r, k in components
        if r != 0 or k != 0
    ]
    if len(filtered) < 2:
        return ""
    return " + ".join(
        f"{r}k{k} {label}" for label, r, k in filtered
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

# Event types that are silently skipped in format_history (info merged elsewhere)
_SKIP_EVENTS = (
    events.AttackDeclaredEvent,
    events.AttackSucceededEvent,
    events.AttackFailedEvent,
    events.ParryDeclaredEvent,
    events.SpendActionEvent,
    events.WoundCheckDeclaredEvent,
    events.WoundCheckSucceededEvent,
    events.WoundCheckFailedEvent,
    events.EndOfPhaseEvent,
    events.EndOfRoundEvent,
    events.YourMoveEvent,
    events.HoldActionEvent,
    events.NoActionEvent,
    CounterattackDeclaredEvent,
    CounterattackSucceededEvent,
    CounterattackFailedEvent,
    ContestedIaijutsuAttackDeclaredEvent,
    TakeContestedIaijutsuAttackAction,
)


class DetailedEventFormatter:
    """Formats annotated combat events into rich human-readable output.

    Stateful processor that tracks current phase/round and combines
    related events (attack roll + hit/miss, wound check + pass/fail)
    onto single lines with emoji prefixes.
    """

    def __init__(self) -> None:
        self._current_phase = 0
        self._current_round = 0
        self._phase_shown: bool = False
        self._last_wc_passed: dict[str, bool] = {}
        self._last_take_sw_target: str | None = None

    def format_history(self, history: list[Any]) -> list[str]:
        """Main entry point — processes full history after combat."""
        lines: list[str] = []
        shown_opening_status = False
        last_status = None
        # Track whether any visible combat output occurred since the last
        # status block, so we don't render duplicate status blocks with
        # nothing between them (e.g. when Phase 0 has no 5th Dan strike).
        combat_output_since_status = False
        consumed: set[int] = set()

        for i, event in enumerate(history):
            if i in consumed:
                continue

            if isinstance(event, _SKIP_EVENTS):
                continue

            if isinstance(event, events.NewRoundEvent):
                self._current_round = event.round
                if lines:
                    lines.append("")
                lines.append(f"═══ Round {event.round + 1} ═══")
                shown_opening_status = False

            elif isinstance(event, events.NewPhaseEvent):
                self._current_phase = event.phase
                self._phase_shown = False
                if hasattr(event, "_detail_status"):
                    last_status = event._detail_status
                if hasattr(event, "_detail_initiative"):
                    lines.extend(self._format_initiative(event))
                if not shown_opening_status and last_status:
                    lines.append("  ─────")
                    lines.extend(self._format_status_block(last_status))
                    lines.append("  ─────")
                    shown_opening_status = True
                    combat_output_since_status = False

            elif isinstance(event, events.TakeAttackActionEvent):
                status = getattr(event, "_detail_status", last_status)
                if status and combat_output_since_status:
                    lines.append("  ─────")
                    lines.extend(self._format_status_block(status))
                    lines.append("  ─────")
                    self._phase_shown = False
                    combat_output_since_status = False
                # Lookahead for matching AttackRolledEvent
                rolled_idx = self._find_attack_rolled(history, i + 1, event.action)
                if rolled_idx is not None:
                    # Check if counterattack events are interleaved
                    has_counter = self._has_counterattack_between(history, i + 1, rolled_idx)
                    if has_counter:
                        # Don't combine — show declaration only; counterattack
                        # and AttackRolledEvent will render in order
                        lines.extend(self._format_take_attack(event))
                    else:
                        # Collect VP events between, filtering by attacker subject
                        # to avoid consuming counterattacker's VP events
                        vp_events: list[Any] = []
                        attacker = event.action.subject()
                        for j in range(i + 1, rolled_idx):
                            if j in consumed:  # pragma: no cover  # defensive: VP events in this narrow window are never pre-consumed
                                continue
                            if isinstance(history[j], events.SpendVoidPointsEvent):
                                if history[j].subject == attacker:
                                    vp_events.append(history[j])
                                    consumed.add(j)
                        vp_infix = self._build_vp_infix(vp_events)
                        lines.extend(self._format_combined_attack(event, history[rolled_idx], vp_infix=vp_infix))
                        consumed.add(rolled_idx)
                else:
                    lines.extend(self._format_take_attack(event))
                combat_output_since_status = True

            elif isinstance(event, TakeCounterattackActionEvent):
                # Lookahead for matching CounterattackRolledEvent
                rolled_idx = self._find_counterattack_rolled(history, i + 1, event.action)
                if rolled_idx is not None:
                    vp_events_ca: list[Any] = []
                    for j in range(i + 1, rolled_idx):
                        if j in consumed:  # pragma: no cover  # defensive: VP events in this narrow window are never pre-consumed
                            continue
                        if isinstance(history[j], events.SpendVoidPointsEvent):
                            vp_events_ca.append(history[j])
                            consumed.add(j)
                    vp_infix = self._build_vp_infix(vp_events_ca)
                    lines.extend(self._format_combined_counterattack(event, history[rolled_idx], vp_infix=vp_infix))
                    consumed.add(rolled_idx)
                else:
                    lines.extend(self._format_take_counterattack(event))
                combat_output_since_status = True

            elif isinstance(event, CounterattackRolledEvent):
                lines.extend(self._format_counterattack_rolled(event))
                combat_output_since_status = True

            elif isinstance(event, events.AttackRolledEvent):
                lines.extend(self._format_attack_rolled(event))
                combat_output_since_status = True

            elif isinstance(event, ContestedIaijutsuAttackRolledEvent):
                lines.extend(self._format_contested_iaijutsu_rolled(event))
                combat_output_since_status = True

            elif isinstance(event, events.TakeParryActionEvent):
                rolled_idx = self._find_parry_rolled(history, i + 1, event.action)
                if rolled_idx is not None:
                    lines.extend(self._format_combined_parry(event, history[rolled_idx]))
                    consumed.add(rolled_idx)
                else:
                    lines.extend(self._format_take_parry(event))
                combat_output_since_status = True

            elif isinstance(event, events.ParryRolledEvent):
                lines.extend(self._format_parry_rolled(event))
                combat_output_since_status = True

            elif isinstance(event, events.LightWoundsDamageEvent):
                lines.extend(self._format_lw_damage(event))
                combat_output_since_status = True

            elif isinstance(event, events.SeriousWoundsDamageEvent):
                # Skip if redundant with preceding TakeSeriousWoundEvent
                if self._last_take_sw_target == event.target.name():
                    self._last_take_sw_target = None
                    continue
                self._last_take_sw_target = None
                lines.extend(self._format_sw_damage(event))
                combat_output_since_status = True

            elif isinstance(event, events.WoundCheckRolledEvent):
                lines.extend(self._process_wound_check(history, i, consumed))
                combat_output_since_status = True

            elif isinstance(event, events.SpendVoidPointsEvent):
                if event.skill == "wound check":
                    wc_idx = self._find_wound_check_rolled(history, i + 1, event.subject.name())
                    if wc_idx is not None:
                        vp_infix = self._build_vp_infix([event], wc_event=history[wc_idx])
                        lines.extend(self._process_wound_check(history, wc_idx, consumed, vp_infix))
                        consumed.add(wc_idx)
                        combat_output_since_status = True
                        continue
                # Akodo 5th Dan counter-damage: the spend is paired with
                # the next LightWoundsDamageEvent (also tagged
                # ``source="Akodo 5th Dan"``).  Render both as a single
                # combined line per FR-024.
                if (
                    event.skill == "damage"
                    and getattr(event, "source", None) == "Akodo 5th Dan"
                ):
                    counter_idx = self._find_akodo_5th_counter_damage(
                        history, i + 1, event.subject,
                    )
                    if counter_idx is not None:
                        lines.extend(self._format_akodo_5th_dan_counter(
                            event, history[counter_idx],
                        ))
                        consumed.add(counter_idx)
                        combat_output_since_status = True
                        continue
                lines.extend(self._format_spend_vp(event))
                combat_output_since_status = True

            elif isinstance(event, events.KeepLightWoundsEvent):
                lines.extend(self._format_keep_lw(event))
                combat_output_since_status = True

            elif isinstance(event, events.TakeSeriousWoundEvent):
                self._last_take_sw_target = event.subject.name()
                lines.extend(self._format_take_sw(event))
                combat_output_since_status = True

            elif isinstance(event, IaijutsuDuelEvent):
                lines.append("")
                lines.append("═══ Iaijutsu Duel ═══")
                self._phase_shown = True
                combat_output_since_status = True

            elif isinstance(event, ShowMeYourStanceDeclaredEvent):
                name = event.subject.name()
                lines.append(f"{name} | 🔍 prepares to assess opponent's stance")
                combat_output_since_status = True

            elif isinstance(event, ShowMeYourStanceRolledEvent):
                name = event.subject.name()
                dice_info = ""
                if hasattr(event, "_detail_dice") and event._detail_dice:
                    rp = getattr(event, "_detail_roll_params", None)
                    if rp:
                        dice_info = f" ({rp['rolled']}k{rp['kept']} {_format_dice(event._detail_dice, rp['kept'])})"
                lines.append(
                    f"{name} | 🔍 Stance: rolled {event.roll}{dice_info}"
                    f" — discerns Fire ~{event.discerned_fire}, TN ~{event.discerned_tn}"
                )
                combat_output_since_status = True

            elif isinstance(event, DuelInitiativeRolledEvent):
                winner_name = event.winner.name()
                lines.append(
                    f"⚔️ Contested Iaijutsu: "
                    f"{event.challenger.name()} {event.challenger_roll} vs "
                    f"{event.defender.name()} {event.defender_roll} "
                    f"— {winner_name} chooses first"
                )
                combat_output_since_status = True

            elif isinstance(event, IaijutsuFocusEvent):
                name = event.subject.name()
                c_name = event.challenger.name()
                d_name = event.defender.name()
                lines.append(
                    f"{name} | 🎯 focuses — "
                    f"TNs: {c_name} {event.challenger_tn}, {d_name} {event.defender_tn}"
                )
                combat_output_since_status = True

            elif isinstance(event, IaijutsuStrikeEvent):
                name = event.subject.name()
                c_name = event.challenger.name()
                d_name = event.defender.name()
                lines.append(
                    f"{name} | ⚔️ declares strike — "
                    f"TNs: {c_name} {event.challenger_tn}, {d_name} {event.defender_tn}"
                )
                combat_output_since_status = True

            elif isinstance(event, DuelStrikeRolledEvent):
                name = event.subject.name()
                target_name = event.target.name()
                dice_info = ""
                if hasattr(event, "_detail_dice") and event._detail_dice:
                    rp = getattr(event, "_detail_roll_params", None)
                    if rp:
                        dice_info = f" {rp['rolled']}k{rp['kept']} {_format_dice(event._detail_dice, rp['kept'])}"
                if event.is_hit:
                    result = "HIT!"
                    extra = f" (+{event.extra_damage_dice} extra damage dice)" if event.extra_damage_dice > 0 else ""
                    lines.append(f"{name} | ⚔️ Strike vs {target_name}:{dice_info} {event.roll} vs TN {event.tn} — {result}{extra}")
                else:
                    lines.append(f"{name} | ❌ Strike vs {target_name}:{dice_info} {event.roll} vs TN {event.tn} — MISS")
                combat_output_since_status = True

            elif isinstance(event, DuelResheathEvent):
                higher = event.higher_roller.name()
                lines.append(f"🔄 Neither hit — resheathe. {higher} gains a free raise on damage.")
                combat_output_since_status = True

            elif isinstance(event, DuelEndedEvent):
                lines.append("⚔️ Duel ended — transitioning to melee combat")
                combat_output_since_status = True

            elif isinstance(event, events.DeathEvent):
                name = event.subject.name()
                lines.append(f"{self._phase_prefix(name)} ☠️ is killed!")
                combat_output_since_status = True

            elif isinstance(event, events.UnconsciousEvent):
                name = event.subject.name()
                lines.append(f"{self._phase_prefix(name)} 💀 falls unconscious!")
                combat_output_since_status = True

            elif isinstance(event, events.SurrenderEvent):
                name = event.subject.name()
                lines.append(f"{self._phase_prefix(name)} 🏳️ surrenders!")
                combat_output_since_status = True

            elif isinstance(event, events.SchoolNegatedEvent):
                lines.extend(self._format_school_negated(event))
                combat_output_since_status = True

            elif isinstance(event, events.GainTemporaryVoidPointsEvent):
                rendered = self._format_gain_tvp(event)
                if rendered:
                    lines.extend(rendered)
                    combat_output_since_status = True

            elif isinstance(event, events.GainFloatingBonusEvent):
                rendered = self._format_gain_floating_bonus(event)
                if rendered:
                    lines.extend(rendered)
                    combat_output_since_status = True

            elif isinstance(event, events.SpendFloatingBonusEvent):
                rendered = self._format_spend_floating_bonus(event)
                if rendered:
                    lines.extend(rendered)
                    combat_output_since_status = True

        return lines

    def _phase_prefix(self, char_name: str) -> str:
        """Returns 'Phase X | Name |' on first call per phase, then 'Name |'."""
        if not self._phase_shown:
            self._phase_shown = True
            return f"Phase {self._current_phase} | {char_name} |"
        return f"{char_name} |"

    def _format_status_block(self, status: dict[str, Any]) -> list[str]:
        """Format a status snapshot as a block of lines."""
        lines: list[str] = []
        for name, s in status.items():
            crippled = " | CRIPPLED" if s["crippled"] else ""
            lines.append(
                f"  {name}:  Light {s['lw']} | Serious {s['sw']}/{s['max_sw']} | "
                f"Void {s['vp']}/{s['max_vp']} | Actions: {s['actions']}{crippled}"
            )
        return lines

    def _format_initiative(self, event: Any) -> list[str]:
        lines = ["", "🎲 Initiative:"]
        for name, data in event._detail_initiative.items():
            rolled, kept = data["roll_params"]
            all_dice = data["all_dice"]
            actions = data["actions"]
            dice_str = _format_dice(all_dice, kept)
            lines.append(f"  {name}: {rolled}k{kept} rolled {dice_str} → Actions: {actions}")
        return lines

    def _format_take_attack(self, event: Any) -> list[str]:
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        skill = event.action.skill()
        return [f"{self._phase_prefix(subj)} ⚔️ attacks {tgt} ({skill})"]

    def _format_take_counterattack(self, event: Any) -> list[str]:
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        return [f"{self._phase_prefix(subj)} ⚔️ counterattacks {tgt}"]

    def _format_take_parry(self, event: Any) -> list[str]:
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        return [f"{self._phase_prefix(subj)} 🛡️ parries {tgt}"]

    def _format_attack_rolled(self, event: Any) -> list[str]:
        """Combine attack roll with hit/miss result."""
        if not hasattr(event, "_detail_dice"):
            return [f"  Roll: {event.roll}"]

        dice = event._detail_dice
        rolled, kept, mod = event._detail_params
        tn = event._detail_tn
        base_tn = getattr(event, "_detail_base_tn", tn)
        # Per FR-011: pass the action's skill to _format_tn so the
        # raise clause carries the action name (e.g., "double attack",
        # "feint") rather than a generic placeholder.
        tn_str = self._format_tn(tn, base_tn, event.action.skill())
        name = event.action.subject().name()

        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod

        # Per FR-006: render the inline attack-XkY source breakdown
        # when the observer attached ``_detail_components`` with more
        # than one nonzero entry. The breakdown precedes the dice list,
        # matching the damage-line convention (``XkY = <breakdown>
        # [dice]``).
        attack_breakdown = _render_components(
            getattr(event, "_detail_components", None),
        )
        xky = f"{rolled}k{kept}"
        if attack_breakdown:
            xky = f"{rolled}k{kept} = {attack_breakdown}"

        # Build roll description
        roll_str = f"{xky} {_format_dice(dice, kept)} → {kept_sum}"
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"

        # Determine hit/miss
        hit = event.action.is_hit() and not event.action.parried()
        if hit:
            emoji = "🎯"
            result = "HIT!"
            # Use base TN for extra dice calculation (double attack computes
            # extra dice against the base TN, not the inflated +20 TN).
            extra_dice = event.action.calculate_extra_damage_dice(tn=base_tn)
            subject = event.action.subject()
            target = event.action.target()
            damage_params = subject.get_damage_roll_params(
                target, event.action.skill(), extra_dice, event.action.vp()
            )
            extras = []
            margin = total - tn
            if margin > 0:
                extras.append(f"+{margin} over TN")
            if extra_dice > 0:
                extras.append(f"{extra_dice} extra damage {'die' if extra_dice == 1 else 'dice'}")
            if damage_params:
                dr, dk, _dm = damage_params
                damage_breakdown = _render_components(
                    _compute_damage_breakdown(subject, target, event.action, extra_dice),
                )
                if damage_breakdown:
                    extras.append(f"damage will be {dr}k{dk} = {damage_breakdown}")
                else:
                    extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            attribution = self._format_modifier_breakdown(event, mod)
            return [f"{self._phase_prefix(name)} {emoji} Attack: {roll_str} vs {tn_str} — {result}{extra_str}{attribution}"]
        else:
            emoji = "❌"
            result = "MISS"
            attribution = self._format_modifier_breakdown(event, mod)
            return [f"{self._phase_prefix(name)} {emoji} Attack: {roll_str} vs {tn_str} — {result}{attribution}"]

    def _format_counterattack_rolled(self, event: Any) -> list[str]:
        """Standalone counterattack roll with hit/miss result."""
        if not hasattr(event, "_detail_dice"):
            return [f"  Counterattack Roll: {event.roll}"]

        dice = event._detail_dice
        rolled, kept, mod = event._detail_params
        tn = event._detail_tn
        name = event.action.subject().name()

        roll_str, total = self._build_roll_str(dice, rolled, kept, mod, event.roll)

        hit = event.action.is_hit()
        if hit:
            emoji = "🎯"
            result = "HIT!"
        else:
            emoji = "❌"
            result = "MISS"
        attribution = self._format_modifier_breakdown(event, mod)
        return [f"{self._phase_prefix(name)} {emoji} Counterattack: {roll_str} vs TN {tn} — {result}{attribution}"]

    def _format_contested_iaijutsu_rolled(self, event: Any) -> list[str]:
        """Format a contested iaijutsu attack rolled event."""
        action = event.action
        name = action.subject().name()
        is_challenger = action.challenger() == action.subject()
        skill_roll = action.skill_roll()
        opponent_roll = action.opponent_skill_roll()
        extra_dice = action.calculate_extra_damage_dice()

        # Determine WON/LOST/TIED
        if skill_roll > opponent_roll:
            result = "WON"
        elif skill_roll < opponent_roll:
            result = "LOST"
        else:
            result = "TIED"

        margin = abs(skill_roll - opponent_roll)

        # Build dice string if annotations present
        # Use skill_roll() as the authoritative total — the modifier from
        # skill_roll_params() may include action-level adjustments that
        # weren't actually applied during the roll (e.g. the -5 penalty
        # for using "attack" instead of "iaijutsu").
        if hasattr(event, "_detail_dice") and hasattr(event, "_detail_params"):
            dice = event._detail_dice
            rolled, kept, _mod = event._detail_params
            kept_sum = sum(dice[:kept]) if dice else skill_roll
            effective_mod = skill_roll - kept_sum

            roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
            if effective_mod > 0:
                roll_str += f", +{effective_mod} = {skill_roll}"
            elif effective_mod < 0:
                roll_str += f", {effective_mod} = {skill_roll}"
        else:
            roll_str = str(skill_roll)

        # Build label and extras
        if is_challenger:
            label = "⚔️ Contested Iaijutsu (5th Dan)"
            extras = [f"+{margin}" if margin > 0 else ""]
            if result == "WON" and extra_dice > 0:
                extras.append(f"{extra_dice} extra damage {'die' if extra_dice == 1 else 'dice'}")
            elif result == "LOST" and extra_dice < 0:
                extras.append(f"{abs(extra_dice)} fewer damage dice")
            extras = [e for e in extras if e]
            extra_str = f" ({', '.join(extras)})" if extras else ""
        else:
            skill = action.skill()
            label = f"⚔️ Contested Iaijutsu ({skill})"
            extras = [f"+{margin}" if margin > 0 else ""]
            extras = [e for e in extras if e]
            extra_str = f" ({', '.join(extras)})" if extras else ""

        return [
            f"{self._phase_prefix(name)} {label}: {roll_str} vs {opponent_roll} — {result}{extra_str}"
        ]

    def _format_parry_rolled(self, event: Any) -> list[str]:
        """Combine parry roll with succeeded/failed result."""
        name = event.action.subject().name()

        if not hasattr(event, "_detail_dice"):
            return [f"{self._phase_prefix(name)} 🛡️ Parry roll: {event.roll}"]

        dice = event._detail_dice
        rolled, kept, mod = event._detail_params
        tn = event._detail_tn

        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod

        roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"

        succeeded = event.action.is_success()
        result = "SUCCEEDED" if succeeded else "FAILED"
        attribution = self._format_modifier_breakdown(event, mod)
        return [f"{self._phase_prefix(name)} 🛡️ Parry: {roll_str} vs TN {tn} — {result}{attribution}"]

    def _format_lw_damage(self, event: Any) -> list[str]:
        name = event.target.name()
        attacker = event.subject.name()

        if not hasattr(event, "_detail_dice"):
            return [f"{self._phase_prefix(name)} 💥 takes {event.damage} light wounds"]

        dice = event._detail_dice
        rolled, kept = event._detail_params
        kept_sum = sum(dice[:kept]) if dice else event.damage

        lw_after = getattr(event, "_detail_lw_after", None)
        total_str = f" (total: {lw_after})" if lw_after is not None else ""

        # Per FR-009: render the inline source breakdown when the
        # observer attached ``_detail_components`` and the breakdown has
        # more than one nonzero entry. Zero-contribution entries are
        # filtered out (Edge Cases: "Zero-contribution sources").
        breakdown_str = _render_components(getattr(event, "_detail_components", None))
        xky = f"{rolled}k{kept}"
        if breakdown_str:
            xky = f"{rolled}k{kept} = {breakdown_str}"

        return [
            f"{self._phase_prefix(attacker)} 💥 Damage: {xky} {_format_dice(dice, kept)} → {kept_sum}"
            f" → {name} takes {event.damage} light wounds{total_str}",
        ]

    def _format_sw_damage(self, event: Any) -> list[str]:
        name = event.target.name()
        hearts = "💔" * event.damage
        noun = "wound" if event.damage == 1 else "wounds"
        suffix = " (double attack penalty)" if getattr(event, "_from_double_attack", False) else ""
        return [f"{self._phase_prefix(name)} {hearts} {name} takes {event.damage} serious {noun}{suffix}"]

    def _format_wound_check_rolled(self, event: Any, emoji: str | None = None, vp_infix: str = "") -> list[str]:
        """Combine wound check roll with pass/fail.

        Per Constitution Principle VII the rendered line shows BOTH
        the kept-sum and the modifier (when non-zero), plus a source
        attribution line when a school-specific breakdown is known
        and sums correctly to the modifier.
        """
        name = event.subject.name()

        passed = event.roll >= event.tn
        if emoji is None:
            emoji = "💔" if passed else "🖤"
        result = "PASSED" if passed else "FAILED"

        if not hasattr(event, "_detail_dice"):
            return [f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: rolled {event.roll} vs TN {event.tn} — {result}"]

        dice = event._detail_dice
        rolled, kept, mod = self._unpack_wound_check_params(event._detail_params)
        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod

        roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"

        line = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: {roll_str} vs TN {event.tn} — {result}"
        line += self._format_modifier_breakdown(event, mod)
        return [line]

    @staticmethod
    def _unpack_wound_check_params(params: Any) -> tuple[int, int, int]:
        """Accept both new 3-tuple ``(rolled, kept, modifier)`` and the
        legacy 2-tuple ``(rolled, kept)`` form used by older tests
        and historical callers. Legacy callers get an implicit
        ``modifier=0``.
        """
        if params is None:
            return (0, 0, 0)
        if len(params) >= 3:
            return (params[0], params[1], params[2])
        return (params[0], params[1], 0)

    @staticmethod
    def _format_modifier_breakdown(event: Any, modifier: int) -> str:
        """Return a parenthetical ``" (Source: +N x M VP; Source2: +K)"``
        suffix attributing the rendered ``modifier`` to its source(s).

        Per spec.md FR-010 / FR-014 (Combat Trace Observability Audit):
        a non-zero modifier MUST always carry an attribution. When the
        ``event._detail_modifier_breakdown`` accounts for only part
        (or none) of the modifier, the remainder is rendered as
        ``(unsourced: +K)`` -- a visible Principle VII violation rather
        than silently suppressing the attribution. This makes the gap
        flag-able by tests (``test_unaccounted_modifier_renders_unsourced_placeholder``)
        instead of hidden behind a "better silent than wrong" guard.

        Returns an empty string only when ``modifier == 0`` (nothing to
        attribute).
        """
        if modifier == 0:
            return ""
        breakdown = getattr(event, "_detail_modifier_breakdown", None) or []
        # Filter out zero-value contributions per the audit's edge-case
        # rule ("Zero-contribution sources").
        breakdown = [(label, value) for label, value in breakdown if value != 0]
        known_total = sum(value for _label, value in breakdown)
        remainder = modifier - known_total
        # Special-case the single-source "Mirumoto 5th Dan" rendering
        # so it explicitly shows the "x N VP" multiplier (matching the
        # user's expected trace format). All other single-source
        # renderings show "Label: +N".
        if breakdown and remainder == 0 and len(breakdown) == 1:
            label, value = breakdown[0]
            if label == "Mirumoto 5th Dan" and value > 0 and value % 10 == 0:
                vp_count = value // 10
                return f" ({label}: +10 × {vp_count} VP)"
            sign = "+" if value >= 0 else ""
            return f" ({label}: {sign}{value})"
        parts: list[str] = []
        for label, value in breakdown:
            sign = "+" if value >= 0 else ""
            parts.append(f"{label}: {sign}{value}")
        if remainder != 0:
            sign = "+" if remainder >= 0 else ""
            parts.append(f"unsourced: {sign}{remainder}")
        if not parts:  # pragma: no cover  # defensive: unreachable when modifier != 0 (remainder forces unsourced part); modifier == 0 short-circuits earlier
            return ""
        return f" ({'; '.join(parts)})"

    def _format_spend_vp(self, event: Any) -> list[str]:
        name = event.subject.name()
        squares = "⬛" * event.amount
        return [f"{self._phase_prefix(name)} {squares} spends {event.amount} VP on {event.skill}"]

    def _format_gain_tvp(self, event: Any) -> list[str]:
        """Render ``GainTemporaryVoidPointsEvent`` with optional source
        attribution per Constitution Principle VII.

        Specifically supports the Akodo Bushi School Special Ability
        (rules/04-schools.md "Akodo Bushi School: Special Ability") whose
        listeners tag the event with ``source="Akodo Special Ability"`` —
        the renderer disambiguates success (+4) vs. failure (+1) by the
        ``amount`` field. Per FR-006, both the source string AND the
        numeric value must appear in the user-facing trace.

        Events with no ``source`` attribute are rendered with a generic
        ``"+N TVP"`` line. Returns an empty list for non-positive
        amounts (defensive guard; the engine should never emit ≤0).
        """
        if event.amount <= 0:
            return []
        name = event.subject.name()
        source = getattr(event, "source", None)
        if source == "Akodo Special Ability":
            outcome = "successful feint" if event.amount == 4 else "failed feint"
            return [
                f"{self._phase_prefix(name)} ✨ {source}: "
                f"+{event.amount} TVP on {outcome}"
            ]
        if source:
            return [
                f"{self._phase_prefix(name)} ✨ {source}: +{event.amount} TVP"
            ]
        return [f"{self._phase_prefix(name)} ✨ gains +{event.amount} TVP"]

    def _format_gain_floating_bonus(self, event: Any) -> list[str]:
        """Render ``GainFloatingBonusEvent`` with source attribution per
        Constitution Principle VII.

        rules/04-schools.md "Akodo Bushi School: Third Dan" -- the
        emitter (``AkodoWoundCheckSucceededListener``) tags the event
        with ``source="Akodo 3rd Dan"`` and an optional
        ``breakdown`` (e.g. ``"margin 20 ÷ 5 × attack 5"``).  When the
        bonus value is positive the formatter renders both source and
        breakdown; a zero-valued bonus is silently skipped (it's inert
        and would clutter the trace).

        Events with no ``source`` get a generic rendering.  When the
        bonus value is zero, returns an empty list -- the bonus is
        inert and doesn't deserve a trace line.
        """
        bonus_value = event.bonus.bonus() if hasattr(event.bonus, "bonus") else 0
        if bonus_value <= 0:
            return []
        name = event.subject.name()
        source = event.source
        breakdown = event.breakdown
        if source:
            if breakdown:
                return [
                    f"{self._phase_prefix(name)} ✨ {source}: gained "
                    f"floating bonus +{bonus_value} ({breakdown})"
                ]
            return [
                f"{self._phase_prefix(name)} ✨ {source}: gained "
                f"floating bonus +{bonus_value}"
            ]
        return [
            f"{self._phase_prefix(name)} ✨ gains floating bonus +{bonus_value}"
        ]

    def _format_spend_floating_bonus(self, event: Any) -> list[str]:
        """Render ``SpendFloatingBonusEvent`` with source attribution.

        The bonus's ``source()`` (set when the school created the
        bonus) carries the attribution per Constitution Principle VII.
        Untagged bonuses get a generic rendering.

        rules/04-schools.md "Akodo Bushi School: Third Dan" tags every
        Akodo-sourced bonus with ``source="Akodo 3rd Dan"`` so the
        consumption line is identifiable in the user-facing trace.
        """
        bonus = event.bonus
        bonus_value = bonus.bonus() if hasattr(bonus, "bonus") else 0
        source = bonus.source() if hasattr(bonus, "source") else None
        name = event.subject.name()
        if source:
            return [
                f"{self._phase_prefix(name)} ✨ +{bonus_value} "
                f"({source} floating bonus consumed)"
            ]
        return [
            f"{self._phase_prefix(name)} ✨ +{bonus_value} "
            f"(floating bonus consumed)"
        ]

    def _format_school_negated(self, event: Any) -> list[str]:
        """Render ``SchoolNegatedEvent`` with the Isawa Ishi 5th Dan
        source attribution per Constitution Principle VII.

        rules/04-schools.md "Isawa Ishi School: 5th Dan": the Ishi spends
        VP equal to ``2 * opponent.school_rank()`` (or ``floor(xp/50)``
        for schoolless opponents) to negate the opponent's school /
        profession for the duration of a fight.
        """
        negator_name = event.negator.name()
        target_name = event.target.name()
        return [
            f"{self._phase_prefix(negator_name)} ⛔ negates {target_name}'s "
            f"{event.target_school_name} "
            f"({event.vp_cost} VP — Isawa Ishi 5th Dan)"
        ]

    def _format_keep_lw(self, event: Any) -> list[str]:
        name = event.subject.name()
        lw_total = getattr(event, "_detail_lw_total", event.damage)
        return [f"{self._phase_prefix(name)} 🖤 keeping {lw_total} light wounds"]

    def _format_take_sw(self, event: Any) -> list[str]:
        name = event.subject.name()
        voluntary = self._last_wc_passed.get(name, False)
        if voluntary:
            return [f"{self._phase_prefix(name)} 💔 chooses to take 1 serious wound"]
        return [f"{self._phase_prefix(name)} 💔 takes 1 serious wound"]

    # ── Lookahead helpers ──────────────────────────────────────────────

    @staticmethod
    def _has_counterattack_between(history: list[Any], start: int, end: int) -> bool:
        """Check if any TakeCounterattackActionEvent exists in [start, end)."""
        for j in range(start, end):
            if isinstance(history[j], TakeCounterattackActionEvent):
                return True
        return False

    def _find_attack_rolled(
        self, history: list[Any], start: int, action: object,
    ) -> int | None:
        """Scan forward for a matching AttackRolledEvent.

        With counterattack events now interleaved between TakeAttackActionEvent
        and AttackRolledEvent, we scan up to 40 events and stop only at
        round/phase boundaries.
        """
        limit = min(start + 40, len(history))
        for j in range(start, limit):
            evt = history[j]
            if isinstance(evt, events.AttackRolledEvent) and evt.action is action:
                return j
            if isinstance(evt, (events.NewRoundEvent, events.NewPhaseEvent)):
                break
        return None

    def _find_counterattack_rolled(
        self, history: list[Any], start: int, action: object,
    ) -> int | None:
        """Scan forward up to 5 events for a matching CounterattackRolledEvent."""
        limit = min(start + 5, len(history))
        for j in range(start, limit):
            evt = history[j]
            if isinstance(evt, CounterattackRolledEvent) and evt.action is action:
                return j
            if isinstance(evt, _SKIP_EVENTS) or isinstance(evt, events.SpendVoidPointsEvent):
                continue
            break
        return None

    def _find_parry_rolled(
        self, history: list[Any], start: int, action: object,
    ) -> int | None:
        """Scan forward up to 5 events for a matching ParryRolledEvent."""
        limit = min(start + 5, len(history))
        for j in range(start, limit):
            evt = history[j]
            if isinstance(evt, events.ParryRolledEvent) and evt.action is action:
                return j
            if isinstance(evt, _SKIP_EVENTS) or isinstance(evt, events.SpendVoidPointsEvent):
                continue
            break
        return None

    def _find_akodo_5th_counter_damage(
        self, history: list[Any], start: int, akodo_subject: Any,
    ) -> int | None:
        """Scan forward up to 5 events for the counter-damage
        ``LightWoundsDamageEvent`` paired with an Akodo 5th Dan
        ``SpendVoidPointsEvent``.

        rules/04-schools.md "Akodo Bushi School: Fifth Dan": the strategy
        yields the SpendVoidPointsEvent IMMEDIATELY followed by the
        counter LightWoundsDamageEvent (``subject == akodo``,
        ``source == "Akodo 5th Dan"``).
        """
        limit = min(start + 5, len(history))
        for j in range(start, limit):
            evt = history[j]
            if (
                isinstance(evt, events.LightWoundsDamageEvent)
                and evt.subject == akodo_subject
                and getattr(evt, "source", None) == "Akodo 5th Dan"
            ):
                return j
            if isinstance(evt, _SKIP_EVENTS):
                continue
            break
        return None

    def _format_akodo_5th_dan_counter(
        self, spend_event: Any, counter_event: Any,
    ) -> list[str]:
        """Render an Akodo 5th Dan counter-damage spend+damage pair as a
        single combined line per FR-024 / Constitution Principle VII.

        Format: ``"Akodo 5th Dan: spends N VP on counter-damage,
        10 LW × N = +N0 LW dealt to <attacker>"`` with the source
        attribution AND the numeric breakdown both visible.

        rules/04-schools.md "Akodo Bushi School: Fifth Dan".
        """
        name = spend_event.subject.name()
        squares = "⬛" * spend_event.amount
        n = spend_event.amount
        damage = counter_event.damage
        target_name = counter_event.target.name()
        return [
            f"{self._phase_prefix(name)} {squares} Akodo 5th Dan: "
            f"spends {n} VP on counter-damage, "
            f"10 LW × {n} = {damage} LW dealt to {target_name}"
        ]

    def _find_take_sw(
        self, history: list[Any], start: int, subject_name: str,
    ) -> int | None:
        """Scan forward up to 5 events for a matching TakeSeriousWoundEvent."""
        limit = min(start + 5, len(history))
        for j in range(start, limit):
            evt = history[j]
            if isinstance(evt, events.TakeSeriousWoundEvent) and evt.subject.name() == subject_name:
                return j
            if isinstance(evt, events.KeepLightWoundsEvent):
                return None
            if isinstance(evt, _SKIP_EVENTS):
                continue
            break
        return None

    def _find_sw_damage(
        self, history: list[Any], start: int, subject_name: str,
    ) -> int | None:
        """Scan forward up to 5 events for a matching SeriousWoundsDamageEvent."""
        limit = min(start + 5, len(history))
        for j in range(start, limit):
            evt = history[j]
            if isinstance(evt, events.SeriousWoundsDamageEvent) and evt.target.name() == subject_name:
                return j
            if isinstance(evt, _SKIP_EVENTS):
                continue
            break
        return None

    def _find_keep_lw(
        self, history: list[Any], start: int, subject_name: str,
    ) -> int | None:
        """Scan forward up to 5 events for a matching KeepLightWoundsEvent."""
        limit = min(start + 5, len(history))
        for j in range(start, limit):
            evt = history[j]
            if isinstance(evt, events.KeepLightWoundsEvent) and evt.subject.name() == subject_name:
                return j
            if isinstance(evt, events.TakeSeriousWoundEvent):
                return None
            if isinstance(evt, _SKIP_EVENTS):
                continue
            break
        return None

    def _find_wound_check_rolled(
        self, history: list[Any], start: int, subject_name: str,
    ) -> int | None:
        """Scan forward up to 5 events for a matching WoundCheckRolledEvent."""
        limit = min(start + 5, len(history))
        for j in range(start, limit):
            evt = history[j]
            if isinstance(evt, events.WoundCheckRolledEvent) and evt.subject.name() == subject_name:
                return j
            if isinstance(evt, _SKIP_EVENTS):
                continue
            break
        return None

    def _process_wound_check(
        self, history: list[Any], wc_idx: int, consumed: set[int], vp_infix: str = "",
    ) -> list[str]:
        """Process a WoundCheckRolledEvent with lookahead for TakeSW/KeepLW."""
        event = history[wc_idx]
        passed = event.roll >= event.tn
        self._last_wc_passed[event.subject.name()] = passed
        # Lookahead for matching TakeSeriousWoundEvent
        sw_idx = self._find_take_sw(history, wc_idx + 1, event.subject.name())
        if sw_idx is not None:
            self._last_take_sw_target = event.subject.name()
            consumed.add(sw_idx)
            # Also consume the following SeriousWoundsDamageEvent to get the count
            sw_count = 1
            sw_dmg_idx = self._find_sw_damage(history, sw_idx + 1, event.subject.name())
            if sw_dmg_idx is not None:
                sw_count = history[sw_dmg_idx].damage
                consumed.add(sw_dmg_idx)
            return self._format_combined_wound_check_sw(event, history[sw_idx], sw_count=sw_count, vp_infix=vp_infix)
        # Peek for KeepLW to combine onto one line
        keep_idx = self._find_keep_lw(history, wc_idx + 1, event.subject.name())
        if keep_idx is not None:
            consumed.add(keep_idx)
            return self._format_combined_wound_check_lw(event, history[keep_idx], vp_infix=vp_infix)
        return self._format_wound_check_rolled(event, vp_infix=vp_infix)

    # ── Combined-line formatters ───────────────────────────────────────

    @staticmethod
    def _build_roll_str(
        dice: list[int], rolled: int, kept: int, mod: int,
        fallback_total: int = 0,
        components: list[tuple[str, int, int]] | None = None,
    ) -> tuple[str, int]:
        """Build a roll description string and compute the total.

        Returns (roll_str, total) where *roll_str* looks like
        ``'10k6 [...] → 24'`` or ``'10k6 [...] → 24, +5 = 29'``.

        When ``components`` carries a multi-source breakdown (per
        FR-006), the leading XkY is augmented with
        ``= <component-list>`` (e.g.,
        ``'10k10 = 5k5 Fire ring + 5k0 double attack skill + ...
        [...] → 24'``).
        """
        kept_sum = sum(dice[:kept]) if dice else fallback_total
        total = kept_sum + mod
        breakdown = _render_components(components)
        xky = f"{rolled}k{kept}"
        if breakdown:
            xky = f"{rolled}k{kept} = {breakdown}"
        roll_str = f"{xky} {_format_dice(dice, kept)} → {kept_sum}"
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"
        return roll_str, total

    @staticmethod
    def _format_tn(
        tn: int,
        base_tn: int | None = None,
        action_skill: str | None = None,
    ) -> str:
        """Format TN for display with full raise-attribution breakdown.

        Per the formatter-rendering contract (§ "TN rendering") for
        Combat Trace Observability Audit FR-011:
        - Always show ``(base TN M)`` when ``base_tn`` is provided.
        - When ``tn > base_tn`` (raises were taken), append
          ``+X from K raises for {action_skill}`` where K = (tn - base_tn) / 5
          and X = K * 5. This is the L7R raise rule (each raise = +5 TN).

        The raise count is derived from ``(tn - base_tn) // 5`` since
        ``Action`` does not expose an ``Action.raises()`` accessor in
        the rules engine; this matches the in-rules invariant that
        only raises inflate the TN above its base.
        """
        if base_tn is None:
            return f"TN {tn}"
        if tn > base_tn:
            diff = tn - base_tn
            raises = diff // 5
            skill = action_skill or "raises"
            return (
                f"TN {tn} (base TN {base_tn}, "
                f"+{diff} from {raises} raises for {skill})"
            )
        return f"TN {tn} (base TN {base_tn})"

    @staticmethod
    def _build_vp_infix(vp_events: list[Any], wc_event: Any | None = None) -> str:
        """Build a VP prefix like '⬛ spends 1 VP on attack → ' (or '' if empty).

        When ``vp_events`` includes an ``Akodo 4th Dan``-sourced
        ``SpendVoidPointsEvent`` on "wound check" AND ``wc_event`` is the
        accompanying ``WoundCheckRolledEvent``, the prefix is augmented
        with the school attribution AND the per-VP breakdown
        (e.g. ``"⬛⬛ Akodo 4th Dan: spends 2 VP on wound check,
        +5 per VP = +10 (15→25) → "``) per FR-019 / Constitution
        Principle VII.
        """
        if not vp_events:
            return ""
        total = sum(e.amount for e in vp_events)
        squares = "⬛" * total
        skill = vp_events[0].skill
        # Akodo 4th Dan attribution: when the spend is tagged with the
        # source, surface the source + the per-VP breakdown so the user
        # sees both attribution AND arithmetic.
        akodo_sources = [
            e for e in vp_events
            if getattr(e, "source", None) == "Akodo 4th Dan"
        ]
        if akodo_sources and skill == "wound check" and wc_event is not None:
            akodo_total = sum(e.amount for e in akodo_sources)
            new_roll = wc_event.roll
            orig_roll = new_roll - (5 * akodo_total)
            return (
                f"{squares} Akodo 4th Dan: spends {total} VP on {skill}, "
                f"+5 per VP = +{5 * akodo_total} ({orig_roll}→{new_roll}) → "
            )
        return f"{squares} spends {total} VP on {skill} → "

    def _format_combined_attack(self, take_event: Any, rolled_event: Any, vp_infix: str = "") -> list[str]:
        """Build a combined 'attacks … — emoji roll vs TN — RESULT' line."""
        action = take_event.action
        subj = action.subject().name()
        tgt = action.target().name()
        skill = action.skill()

        if not hasattr(rolled_event, "_detail_dice"):
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ attacks {tgt} ({skill}) — Roll: {rolled_event.roll}"]

        dice = rolled_event._detail_dice
        rolled, kept, mod = rolled_event._detail_params
        tn = rolled_event._detail_tn
        base_tn = getattr(rolled_event, "_detail_base_tn", tn)
        # Per FR-011: thread the action skill into _format_tn so the
        # raise clause carries the action name.
        tn_str = self._format_tn(tn, base_tn, skill)

        # Per FR-006 / FR-008: pass the attack-roll breakdown into
        # ``_build_roll_str`` so the combined attack-line renders the
        # multi-source XkY decomposition inline.
        attack_components = getattr(rolled_event, "_detail_components", None)
        roll_str, total = self._build_roll_str(
            dice, rolled, kept, mod, rolled_event.roll,
            components=attack_components,
        )

        hit = action.is_hit() and not action.parried()
        if hit:
            result = "HIT!"
            extra_dice = action.calculate_extra_damage_dice(tn=base_tn)
            subject = action.subject()
            target = action.target()
            damage_params = subject.get_damage_roll_params(
                target, action.skill(), extra_dice, action.vp()
            )
            extras = []
            margin = total - tn
            if margin > 0:
                extras.append(f"+{margin} over TN")
            if extra_dice > 0:
                extras.append(f"{extra_dice} extra damage {'die' if extra_dice == 1 else 'dice'}")
            if damage_params:
                dr, dk, _dm = damage_params
                damage_breakdown = _render_components(
                    _compute_damage_breakdown(subject, target, action, extra_dice),
                )
                if damage_breakdown:
                    extras.append(f"damage will be {dr}k{dk} = {damage_breakdown}")
                else:
                    extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            attribution = self._format_modifier_breakdown(rolled_event, mod)
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ attacks {tgt} ({skill}) — {roll_str} vs {tn_str} — {result}{extra_str}{attribution}"]
        else:
            result = "MISS"
            attribution = self._format_modifier_breakdown(rolled_event, mod)
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ attacks {tgt} ({skill}) — {roll_str} vs {tn_str} — {result}{attribution}"]

    def _format_combined_counterattack(self, take_event: Any, rolled_event: Any, vp_infix: str = "") -> list[str]:
        """Build a combined 'counterattacks TARGET — roll vs TN — RESULT' line."""
        action = take_event.action
        subj = action.subject().name()
        tgt = action.target().name()

        if not hasattr(rolled_event, "_detail_dice"):
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ counterattacks {tgt} — Roll: {rolled_event.roll}"]

        dice = rolled_event._detail_dice
        rolled, kept, mod = rolled_event._detail_params
        tn = rolled_event._detail_tn

        roll_str, total = self._build_roll_str(dice, rolled, kept, mod, rolled_event.roll)

        hit = action.is_hit()
        if hit:
            result = "HIT!"
            extra_dice = action.calculate_extra_damage_dice(tn=tn)
            subject = action.subject()
            target = action.target()
            damage_params = subject.get_damage_roll_params(
                target, action.skill(), extra_dice, action.vp()
            )
            extras = []
            margin = total - tn
            if margin > 0:
                extras.append(f"+{margin} over TN")
            if extra_dice > 0:
                extras.append(f"{extra_dice} extra damage {'die' if extra_dice == 1 else 'dice'}")
            if damage_params:
                dr, dk, _dm = damage_params
                damage_breakdown = _render_components(
                    _compute_damage_breakdown(subject, target, action, extra_dice),
                )
                if damage_breakdown:
                    extras.append(f"damage will be {dr}k{dk} = {damage_breakdown}")
                else:
                    extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            attribution = self._format_modifier_breakdown(rolled_event, mod)
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ counterattacks {tgt} — {roll_str} vs TN {tn} — {result}{extra_str}{attribution}"]
        else:
            result = "MISS"
            attribution = self._format_modifier_breakdown(rolled_event, mod)
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ counterattacks {tgt} — {roll_str} vs TN {tn} — {result}{attribution}"]

    def _format_combined_parry(self, take_event: Any, rolled_event: Any) -> list[str]:
        """Build a combined 'parries TARGET — roll vs TN — RESULT' line."""
        action = take_event.action
        subj = action.subject().name()
        tgt = action.target().name()

        if not hasattr(rolled_event, "_detail_dice"):
            return [f"{self._phase_prefix(subj)} 🛡️ parries {tgt} — Roll: {rolled_event.roll}"]

        dice = rolled_event._detail_dice
        rolled, kept, mod = rolled_event._detail_params
        tn = rolled_event._detail_tn

        kept_sum = sum(dice[:kept]) if dice else rolled_event.roll
        total = kept_sum + mod

        roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"

        succeeded = action.is_success()
        result = "SUCCEEDED" if succeeded else "FAILED"
        attribution = self._format_modifier_breakdown(rolled_event, mod)
        return [f"{self._phase_prefix(subj)} 🛡️ parries {tgt} — {roll_str} vs TN {tn} — {result}{attribution}"]

    def _format_combined_wound_check_lw(self, wc_event: Any, lw_event: Any, vp_infix: str = "") -> list[str]:
        """Build a combined 'Wound Check … — PASSED → keeping N light wounds' line."""
        name = wc_event.subject.name()
        emoji = "🖤"

        if not hasattr(wc_event, "_detail_dice"):
            passed = wc_event.roll >= wc_event.tn
            result = "PASSED" if passed else "FAILED"
            wc_str = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: rolled {wc_event.roll} vs TN {wc_event.tn} — {result}"
        else:
            dice = wc_event._detail_dice
            rolled, kept, mod = self._unpack_wound_check_params(wc_event._detail_params)
            kept_sum = sum(dice[:kept]) if dice else wc_event.roll
            total = kept_sum + mod
            passed = wc_event.roll >= wc_event.tn
            result = "PASSED" if passed else "FAILED"
            roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
            if mod > 0:
                roll_str += f", +{mod} = {total}"
            elif mod < 0:
                roll_str += f", {mod} = {total}"
            wc_str = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: {roll_str} vs TN {wc_event.tn} — {result}"
            wc_str += self._format_modifier_breakdown(wc_event, mod)

        lw_total = getattr(lw_event, "_detail_lw_total", lw_event.damage)
        return [f"{wc_str} → keeping {lw_total} light wounds"]

    def _format_combined_wound_check_sw(self, wc_event: Any, sw_event: Any, sw_count: int = 1, vp_infix: str = "") -> list[str]:
        """Build a combined 'Wound Check … — RESULT → SW text' line."""
        name = wc_event.subject.name()

        # Build wound check portion — 💔 repeated per serious wound
        emoji = "💔" * sw_count
        if not hasattr(wc_event, "_detail_dice"):
            passed = wc_event.roll >= wc_event.tn
            result = "PASSED" if passed else "FAILED"
            wc_str = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: rolled {wc_event.roll} vs TN {wc_event.tn} — {result}"
        else:
            dice = wc_event._detail_dice
            rolled, kept, mod = self._unpack_wound_check_params(wc_event._detail_params)
            kept_sum = sum(dice[:kept]) if dice else wc_event.roll
            total = kept_sum + mod
            passed = wc_event.roll >= wc_event.tn
            result = "PASSED" if passed else "FAILED"
            roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
            if mod > 0:
                roll_str += f", +{mod} = {total}"
            elif mod < 0:
                roll_str += f", {mod} = {total}"
            wc_str = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: {roll_str} vs TN {wc_event.tn} — {result}"
            wc_str += self._format_modifier_breakdown(wc_event, mod)

        # Build serious wound suffix
        noun = "wound" if sw_count == 1 else "wounds"
        voluntary = self._last_wc_passed.get(name, False)
        if voluntary:
            sw_str = f"chooses to take {sw_count} serious {noun}"
        else:
            sw_str = f"takes {sw_count} serious {noun}"

        return [f"{wc_str} → {sw_str}"]
