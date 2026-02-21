"""DetailedEventFormatter for rich combat play-by-play output with emojis and combined events."""

from simulation import events
from simulation.schools.kakita_school import (
    ContestedIaijutsuAttackDeclaredEvent,
    ContestedIaijutsuAttackRolledEvent,
    TakeContestedIaijutsuAttackAction,
)

# Event types that are silently skipped in format_history (info merged elsewhere)
_SKIP_EVENTS = (
    events.AttackDeclaredEvent,
    events.AttackSucceededEvent,
    events.AttackFailedEvent,
    events.ParryDeclaredEvent,
    events.WoundCheckDeclaredEvent,
    events.WoundCheckSucceededEvent,
    events.WoundCheckFailedEvent,
    events.EndOfPhaseEvent,
    events.EndOfRoundEvent,
    events.YourMoveEvent,
    events.HoldActionEvent,
    events.NoActionEvent,
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
        self._last_wc_passed: dict[str, bool] = {}
        self._last_take_sw_target: str | None = None

    def format_history(self, history: list) -> list[str]:
        """Main entry point — processes full history after combat."""
        lines = []
        shown_opening_status = False
        last_status = None

        for event in history:
            if isinstance(event, _SKIP_EVENTS):
                continue

            if isinstance(event, events.NewRoundEvent):
                self._current_round = event.round
                if lines:
                    lines.append("")
                lines.append(f"═══ Round {event.round + 1} ═══")

            elif isinstance(event, events.NewPhaseEvent):
                self._current_phase = event.phase
                if hasattr(event, "_detail_status"):
                    last_status = event._detail_status
                if hasattr(event, "_detail_initiative"):
                    lines.extend(self._format_initiative(event))
                if not shown_opening_status and last_status:
                    lines.append("  ─────")
                    lines.extend(self._format_status_block(last_status))
                    lines.append("  ─────")
                    shown_opening_status = True

            elif isinstance(event, events.TakeAttackActionEvent):
                status = getattr(event, "_detail_status", last_status)
                if status:
                    lines.append("  ─────")
                    lines.extend(self._format_status_block(status))
                    lines.append("  ─────")
                lines.extend(self._format_take_attack(event))

            elif isinstance(event, events.AttackRolledEvent):
                lines.extend(self._format_attack_rolled(event))

            elif isinstance(event, ContestedIaijutsuAttackRolledEvent):
                lines.extend(self._format_contested_iaijutsu_rolled(event))

            elif isinstance(event, events.TakeParryActionEvent):
                lines.extend(self._format_take_parry(event))

            elif isinstance(event, events.ParryRolledEvent):
                lines.extend(self._format_parry_rolled(event))

            elif isinstance(event, events.LightWoundsDamageEvent):
                lines.extend(self._format_lw_damage(event))

            elif isinstance(event, events.SeriousWoundsDamageEvent):
                # Skip if redundant with preceding TakeSeriousWoundEvent
                if self._last_take_sw_target == event.target.name():
                    self._last_take_sw_target = None
                    continue
                self._last_take_sw_target = None
                lines.extend(self._format_sw_damage(event))

            elif isinstance(event, events.WoundCheckRolledEvent):
                passed = event.roll >= event.tn
                self._last_wc_passed[event.subject.name()] = passed
                lines.extend(self._format_wound_check_rolled(event))

            elif isinstance(event, events.SpendVoidPointsEvent):
                lines.extend(self._format_spend_vp(event))

            elif isinstance(event, events.KeepLightWoundsEvent):
                lines.extend(self._format_keep_lw(event))

            elif isinstance(event, events.TakeSeriousWoundEvent):
                self._last_take_sw_target = event.subject.name()
                lines.extend(self._format_take_sw(event))

            elif isinstance(event, events.DeathEvent):
                name = event.subject.name()
                lines.append(f"{self._phase_prefix(name)} ☠️ is killed!")

            elif isinstance(event, events.UnconsciousEvent):
                name = event.subject.name()
                lines.append(f"{self._phase_prefix(name)} 💀 falls unconscious!")

            elif isinstance(event, events.SurrenderEvent):
                name = event.subject.name()
                lines.append(f"{self._phase_prefix(name)} 🏳️ surrenders!")

        return lines

    def _phase_prefix(self, char_name: str) -> str:
        """Returns 'Phase X | Name |' prefix."""
        return f"Phase {self._current_phase} | {char_name} |"

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
            lines.append(f"  {name}: {rolled}k{kept} rolled {all_dice} → Actions: {actions}")
        return lines

    def _format_take_attack(self, event) -> list[str]:
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        skill = event.action.skill()
        return [f"{self._phase_prefix(subj)} ⚔️ attacks {tgt} ({skill})"]

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
        name = event.action.subject().name()

        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod

        # Build roll description
        roll_str = f"{rolled}k{kept} {dice} → {kept_sum}"
        if mod > 0:
            roll_str += f", +{mod} = {total}"
        elif mod < 0:
            roll_str += f", {mod} = {total}"

        # Determine hit/miss
        hit = event.action.is_hit() and not event.action.parried()
        if hit:
            emoji = "🎯"
            result = "HIT!"
            # Add extra info for hits
            # Pass captured TN so extra dice are computed against the TN at roll
            # time, not the target's current (possibly changed) tn_to_hit().
            extra_dice = event.action.calculate_extra_damage_dice(tn=tn)
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
                extras.append(f"{extra_dice} extra damage dice")
            if damage_params:
                dr, dk, dm = damage_params
                extras.append(f"damage will be {dr}k{dk}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            return [f"{self._phase_prefix(name)} {emoji} Attack: {roll_str} vs TN {tn} — {result}{extra_str}"]
        else:
            emoji = "❌"
            result = "MISS"
            return [f"{self._phase_prefix(name)} {emoji} Attack: {roll_str} vs TN {tn} — {result}"]

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

            roll_str = f"{rolled}k{kept} {dice} → {kept_sum}"
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
                extras.append(f"{extra_dice} extra damage dice")
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

        roll_str = f"{rolled}k{kept} {dice} → {kept_sum}"
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
            f"{self._phase_prefix(attacker)} 💥 Damage: {rolled}k{kept} {dice} → {kept_sum}",
            f"{self._phase_prefix(name)} 💥 takes {event.damage} light wounds{total_str}",
        ]

    def _format_sw_damage(self, event) -> list[str]:
        name = event.target.name()
        hearts = "🖤" * event.damage
        return [f"{self._phase_prefix(name)} {hearts} {name} takes {event.damage} serious wounds"]

    def _format_wound_check_rolled(self, event) -> list[str]:
        """Combine wound check roll with pass/fail."""
        name = event.subject.name()

        if not hasattr(event, "_detail_dice"):
            passed = event.roll >= event.tn
            emoji = "💔" if passed else "🖤"
            result = "PASSED" if passed else "FAILED"
            return [f"{self._phase_prefix(name)} {emoji} Wound Check: rolled {event.roll} vs TN {event.tn} — {result}"]

        dice = event._detail_dice
        rolled, kept = event._detail_params
        kept_sum = sum(dice[:kept]) if dice else event.roll

        passed = event.roll >= event.tn
        emoji = "💔" if passed else "🖤"
        result = "PASSED" if passed else "FAILED"
        return [f"{self._phase_prefix(name)} {emoji} Wound Check: {rolled}k{kept} {dice} → {kept_sum} vs TN {event.tn} — {result}"]

    def _format_spend_vp(self, event) -> list[str]:
        name = event.subject.name()
        squares = "⬛" * event.amount
        return [f"{self._phase_prefix(name)} {squares} spends {event.amount} VP on {event.skill}"]

    def _format_keep_lw(self, event) -> list[str]:
        name = event.subject.name()
        lw_total = getattr(event, "_detail_lw_total", event.damage)
        return [f"{self._phase_prefix(name)} 💔 keeping {lw_total} light wounds"]

    def _format_take_sw(self, event) -> list[str]:
        name = event.subject.name()
        voluntary = self._last_wc_passed.get(name, False)
        if voluntary:
            return [f"{self._phase_prefix(name)} 🖤 chooses to take 1 serious wound"]
        return [f"{self._phase_prefix(name)} 🖤 takes 1 serious wound"]
