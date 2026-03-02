"""DetailedEventFormatter for rich combat play-by-play output with emojis and combined events."""

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


def _format_dice(dice: list, kept: int) -> str:
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

    def __init__(self):
        self._current_phase = 0
        self._current_round = 0
        self._phase_shown: bool = False
        self._last_wc_passed: dict[str, bool] = {}
        self._last_take_sw_target: str | None = None

    def format_history(self, history: list) -> list[str]:
        """Main entry point — processes full history after combat."""
        lines = []
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
                        vp_events: list = []
                        attacker = event.action.subject()
                        for j in range(i + 1, rolled_idx):
                            if j in consumed:
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
                    vp_events: list = []
                    for j in range(i + 1, rolled_idx):
                        if j in consumed:
                            continue
                        if isinstance(history[j], events.SpendVoidPointsEvent):
                            vp_events.append(history[j])
                            consumed.add(j)
                    vp_infix = self._build_vp_infix(vp_events)
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
                        vp_infix = self._build_vp_infix([event])
                        lines.extend(self._process_wound_check(history, wc_idx, consumed, vp_infix))
                        consumed.add(wc_idx)
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

        return lines

    def _phase_prefix(self, char_name: str) -> str:
        """Returns 'Phase X | Name |' on first call per phase, then 'Name |'."""
        if not self._phase_shown:
            self._phase_shown = True
            return f"Phase {self._current_phase} | {char_name} |"
        return f"{char_name} |"

    def _format_status_block(self, status: dict) -> list[str]:
        """Format a status snapshot as a block of lines."""
        lines = []
        for name, s in status.items():
            crippled = " | CRIPPLED" if s["crippled"] else ""
            lines.append(
                f"  {name}:  Light {s['lw']} | Serious {s['sw']}/{s['max_sw']} | "
                f"Void {s['vp']}/{s['max_vp']} | Actions: {s['actions']}{crippled}"
            )
        return lines

    def _format_initiative(self, event) -> list[str]:
        lines = ["", "🎲 Initiative:"]
        for name, data in event._detail_initiative.items():
            rolled, kept = data["roll_params"]
            all_dice = data["all_dice"]
            actions = data["actions"]
            dice_str = _format_dice(all_dice, kept)
            lines.append(f"  {name}: {rolled}k{kept} rolled {dice_str} → Actions: {actions}")
        return lines

    def _format_take_attack(self, event) -> list[str]:
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        skill = event.action.skill()
        return [f"{self._phase_prefix(subj)} ⚔️ attacks {tgt} ({skill})"]

    def _format_take_counterattack(self, event) -> list[str]:
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        return [f"{self._phase_prefix(subj)} ⚔️ counterattacks {tgt}"]

    def _format_take_parry(self, event) -> list[str]:
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        return [f"{self._phase_prefix(subj)} 🛡️ parries {tgt}"]

    def _format_attack_rolled(self, event) -> list[str]:
        """Combine attack roll with hit/miss result."""
        if not hasattr(event, "_detail_dice"):
            return [f"  Roll: {event.roll}"]

        dice = event._detail_dice
        rolled, kept, mod = event._detail_params
        tn = event._detail_tn
        base_tn = getattr(event, "_detail_base_tn", tn)
        tn_str = self._format_tn(tn, base_tn)
        name = event.action.subject().name()

        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod

        # Build roll description
        roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
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
                dr, dk, dm = damage_params
                extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            return [f"{self._phase_prefix(name)} {emoji} Attack: {roll_str} vs {tn_str} — {result}{extra_str}"]
        else:
            emoji = "❌"
            result = "MISS"
            return [f"{self._phase_prefix(name)} {emoji} Attack: {roll_str} vs {tn_str} — {result}"]

    def _format_counterattack_rolled(self, event) -> list[str]:
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
        return [f"{self._phase_prefix(name)} {emoji} Counterattack: {roll_str} vs TN {tn} — {result}"]

    def _format_contested_iaijutsu_rolled(self, event) -> list[str]:
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

    def _format_parry_rolled(self, event) -> list[str]:
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
        return [f"{self._phase_prefix(name)} 🛡️ Parry: {roll_str} vs TN {tn} — {result}"]

    def _format_lw_damage(self, event) -> list[str]:
        name = event.target.name()
        attacker = event.subject.name()

        if not hasattr(event, "_detail_dice"):
            return [f"{self._phase_prefix(name)} 💥 takes {event.damage} light wounds"]

        dice = event._detail_dice
        rolled, kept = event._detail_params
        kept_sum = sum(dice[:kept]) if dice else event.damage

        lw_after = getattr(event, "_detail_lw_after", None)
        total_str = f" (total: {lw_after})" if lw_after is not None else ""

        return [
            f"{self._phase_prefix(attacker)} 💥 Damage: {rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
            f" → {name} takes {event.damage} light wounds{total_str}",
        ]

    def _format_sw_damage(self, event) -> list[str]:
        name = event.target.name()
        hearts = "💔" * event.damage
        noun = "wound" if event.damage == 1 else "wounds"
        suffix = " (double attack penalty)" if getattr(event, "_from_double_attack", False) else ""
        return [f"{self._phase_prefix(name)} {hearts} {name} takes {event.damage} serious {noun}{suffix}"]

    def _format_wound_check_rolled(self, event, emoji: str | None = None, vp_infix: str = "") -> list[str]:
        """Combine wound check roll with pass/fail."""
        name = event.subject.name()

        passed = event.roll >= event.tn
        if emoji is None:
            emoji = "💔" if passed else "🖤"
        result = "PASSED" if passed else "FAILED"

        if not hasattr(event, "_detail_dice"):
            return [f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: rolled {event.roll} vs TN {event.tn} — {result}"]

        dice = event._detail_dice
        rolled, kept = event._detail_params
        kept_sum = sum(dice[:kept]) if dice else event.roll

        return [f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: {rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum} vs TN {event.tn} — {result}"]

    def _format_spend_vp(self, event) -> list[str]:
        name = event.subject.name()
        squares = "⬛" * event.amount
        return [f"{self._phase_prefix(name)} {squares} spends {event.amount} VP on {event.skill}"]

    def _format_keep_lw(self, event) -> list[str]:
        name = event.subject.name()
        lw_total = getattr(event, "_detail_lw_total", event.damage)
        return [f"{self._phase_prefix(name)} 🖤 keeping {lw_total} light wounds"]

    def _format_take_sw(self, event) -> list[str]:
        name = event.subject.name()
        voluntary = self._last_wc_passed.get(name, False)
        if voluntary:
            return [f"{self._phase_prefix(name)} 💔 chooses to take 1 serious wound"]
        return [f"{self._phase_prefix(name)} 💔 takes 1 serious wound"]

    # ── Lookahead helpers ──────────────────────────────────────────────

    @staticmethod
    def _has_counterattack_between(history: list, start: int, end: int) -> bool:
        """Check if any TakeCounterattackActionEvent exists in [start, end)."""
        for j in range(start, end):
            if isinstance(history[j], TakeCounterattackActionEvent):
                return True
        return False

    def _find_attack_rolled(
        self, history: list, start: int, action: object,
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
        self, history: list, start: int, action: object,
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
        self, history: list, start: int, action: object,
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

    def _find_take_sw(
        self, history: list, start: int, subject_name: str,
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
        self, history: list, start: int, subject_name: str,
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
        self, history: list, start: int, subject_name: str,
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
        self, history: list, start: int, subject_name: str,
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
        self, history: list, wc_idx: int, consumed: set[int], vp_infix: str = "",
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
    def _build_roll_str(dice: list, rolled: int, kept: int, mod: int, fallback_total: int = 0) -> tuple[str, int]:
        """Build a roll description string and compute the total.

        Returns (roll_str, total) where *roll_str* looks like
        ``'10k6 [...] → 24'`` or ``'10k6 [...] → 24, +5 = 29'``.
        """
        kept_sum = sum(dice[:kept]) if dice else fallback_total
        total = kept_sum + mod
        roll_str = f"{rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum}"
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"
        return roll_str, total

    @staticmethod
    def _format_tn(tn: int, base_tn: int | None = None) -> str:
        """Format TN for display, showing base TN when it differs (e.g. double attack)."""
        if base_tn is not None and base_tn != tn:
            return f"TN {tn} (base TN {base_tn})"
        return f"TN {tn}"

    @staticmethod
    def _build_vp_infix(vp_events: list) -> str:
        """Build a VP prefix like '⬛ spends 1 VP on attack → ' (or '' if empty)."""
        if not vp_events:
            return ""
        total = sum(e.amount for e in vp_events)
        squares = "⬛" * total
        skill = vp_events[0].skill
        return f"{squares} spends {total} VP on {skill} → "

    def _format_combined_attack(self, take_event: object, rolled_event: object, vp_infix: str = "") -> list[str]:
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
        tn_str = self._format_tn(tn, base_tn)

        roll_str, total = self._build_roll_str(dice, rolled, kept, mod, rolled_event.roll)

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
                extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ attacks {tgt} ({skill}) — {roll_str} vs {tn_str} — {result}{extra_str}"]
        else:
            result = "MISS"
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ attacks {tgt} ({skill}) — {roll_str} vs {tn_str} — {result}"]

    def _format_combined_counterattack(self, take_event: object, rolled_event: object, vp_infix: str = "") -> list[str]:
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
                extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ counterattacks {tgt} — {roll_str} vs TN {tn} — {result}{extra_str}"]
        else:
            result = "MISS"
            return [f"{self._phase_prefix(subj)} {vp_infix}⚔️ counterattacks {tgt} — {roll_str} vs TN {tn} — {result}"]

    def _format_combined_parry(self, take_event: object, rolled_event: object) -> list[str]:
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
        return [f"{self._phase_prefix(subj)} 🛡️ parries {tgt} — {roll_str} vs TN {tn} — {result}"]

    def _format_combined_wound_check_lw(self, wc_event: object, lw_event: object, vp_infix: str = "") -> list[str]:
        """Build a combined 'Wound Check … — PASSED → keeping N light wounds' line."""
        name = wc_event.subject.name()
        emoji = "🖤"

        if not hasattr(wc_event, "_detail_dice"):
            passed = wc_event.roll >= wc_event.tn
            result = "PASSED" if passed else "FAILED"
            wc_str = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: rolled {wc_event.roll} vs TN {wc_event.tn} — {result}"
        else:
            dice = wc_event._detail_dice
            rolled, kept = wc_event._detail_params
            kept_sum = sum(dice[:kept]) if dice else wc_event.roll
            passed = wc_event.roll >= wc_event.tn
            result = "PASSED" if passed else "FAILED"
            wc_str = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: {rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum} vs TN {wc_event.tn} — {result}"

        lw_total = getattr(lw_event, "_detail_lw_total", lw_event.damage)
        return [f"{wc_str} → keeping {lw_total} light wounds"]

    def _format_combined_wound_check_sw(self, wc_event: object, sw_event: object, sw_count: int = 1, vp_infix: str = "") -> list[str]:
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
            rolled, kept = wc_event._detail_params
            kept_sum = sum(dice[:kept]) if dice else wc_event.roll
            passed = wc_event.roll >= wc_event.tn
            result = "PASSED" if passed else "FAILED"
            wc_str = f"{self._phase_prefix(name)} {vp_infix}{emoji} Wound Check: {rolled}k{kept} {_format_dice(dice, kept)} → {kept_sum} vs TN {wc_event.tn} — {result}"

        # Build serious wound suffix
        noun = "wound" if sw_count == 1 else "wounds"
        voluntary = self._last_wc_passed.get(name, False)
        if voluntary:
            sw_str = f"chooses to take {sw_count} serious {noun}"
        else:
            sw_str = f"takes {sw_count} serious {noun}"

        return [f"{wc_str} → {sw_str}"]
