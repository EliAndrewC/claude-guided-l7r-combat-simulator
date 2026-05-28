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

    The 10k10-overflow synthetic source is rendered via the shared
    :func:`web.adapters._breakdown_format.format_breakdown_component`
    helper (spec 008 FR-002).
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
        format_breakdown_component(r, k, label) for label, r, k in filtered
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
        # Spec 008 Issue 2/4/6: track each attacker's most recent attack
        # skill so we can recognize the LightWoundsDamageEvent that
        # follows a feint and suppress it (FR-005/6/7).
        self._last_attack_skill: dict[str, str] = {}
        # Dedupe Hida 3rd Dan reroll entries within a single
        # ``entries()`` call.  Tracks action ``id()`` values that have
        # already had their reroll emitted (e.g., to avoid duplicating
        # when both the take-action and the rolled event hit the
        # ``_maybe_append_hida_3rd_dan_reroll`` hook).
        self._hida_3rd_dan_emitted: set[int] = set()

    def format_history(self, history: list[Any]) -> list[str]:
        """Main entry point — processes full history after combat.

        Spec 007 T013 / T023: thin wrapper that delegates to
        ``entries()`` plus ``TextRenderer().render_lines()``. The new
        structured-trace path is the single source of truth for the
        composition logic. The legacy private ``_format_*`` methods
        were deleted in spec 007 Phase 8 (the byte-identical roundtrip
        tests in ``test_text_renderer_roundtrip.py`` cover the same
        rendering logic at the correct layer).
        """
        from web.adapters.text_renderer import TextRenderer
        return TextRenderer().render_lines(self.entries(history))


    # ── Structured entries (spec 007 — TraceEntry refactor) ────────────

    def entries(self, history: list[Any]) -> list[TraceEntry]:
        """Walk the event history and emit a list of structured TraceEntry
        instances.  Mirrors the composition logic of ``format_history``
        one-for-one so that ``TextRenderer().render_lines(entries(h))``
        produces byte-identical output to the legacy
        ``format_history(h)`` (FR-006 / FR-010).
        """
        # Reset state to support repeated calls / parallel walks.
        self._current_phase = 0
        self._current_round = 0
        self._phase_shown = False
        self._last_wc_passed = {}
        self._last_take_sw_target = None
        self._last_attack_skill = {}
        self._hida_3rd_dan_emitted = set()

        out: list[TraceEntry] = []
        shown_opening_status = False
        last_status: dict[str, Any] | None = None
        combat_output_since_status = False
        consumed: set[int] = set()
        any_entry_emitted = False

        for i, event in enumerate(history):
            if i in consumed:
                continue

            if isinstance(event, _SKIP_EVENTS):
                continue

            if isinstance(event, events.NewRoundEvent):
                self._current_round = event.round
                out.append(RoundHeaderEntry(round_number=event.round + 1))
                any_entry_emitted = True
                shown_opening_status = False

            elif isinstance(event, events.NewPhaseEvent):
                self._current_phase = event.phase
                self._phase_shown = False
                if hasattr(event, "_detail_status"):
                    last_status = event._detail_status
                if hasattr(event, "_detail_initiative"):
                    out.append(self._entry_initiative(event))
                if not shown_opening_status and last_status:
                    out.append(StatusBlockEntry(statuses=last_status))
                    shown_opening_status = True
                    combat_output_since_status = False

            elif isinstance(event, events.TakeAttackActionEvent):
                status = getattr(event, "_detail_status", last_status)
                if status and combat_output_since_status:
                    out.append(StatusBlockEntry(statuses=status))
                    self._phase_shown = False
                    combat_output_since_status = False
                rolled_idx = self._find_attack_rolled(history, i + 1, event.action)
                if rolled_idx is not None:
                    has_counter = self._has_counterattack_between(
                        history, i + 1, rolled_idx,
                    )
                    if has_counter:
                        out.append(self._entry_take_attack(event))
                    else:
                        vp_events: list[Any] = []
                        # Spec 008 FR-008/9/10: floating-bonus
                        # consumption events appear BETWEEN the
                        # TakeAttackActionEvent and the AttackRolledEvent
                        # (the engine yields them inside
                        # ``SkillRolledStrategy.recommend`` before
                        # re-yielding the rolled event).  Absorb them
                        # into the AttackEntry so the inline arithmetic
                        # on the attack line shows the bonus integration.
                        fb_events: list[Any] = []
                        attacker = event.action.subject()
                        for j in range(i + 1, rolled_idx):
                            if j in consumed:  # pragma: no cover  # defensive
                                continue
                            ev_j = history[j]
                            if isinstance(ev_j, events.SpendVoidPointsEvent):
                                if ev_j.subject == attacker:
                                    vp_events.append(ev_j)
                                    consumed.add(j)
                            elif isinstance(ev_j, events.SpendFloatingBonusEvent):
                                if ev_j.subject == attacker:
                                    fb_events.append(ev_j)
                                    consumed.add(j)
                        out.append(self._entry_combined_attack(
                            event, history[rolled_idx], vp_events, fb_events,
                        ))
                        consumed.add(rolled_idx)
                        self._maybe_append_hida_3rd_dan_reroll(out, event.action)
                else:
                    out.append(self._entry_take_attack(event))
                    self._maybe_append_hida_3rd_dan_reroll(out, event.action)
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, TakeCounterattackActionEvent):
                rolled_idx = self._find_counterattack_rolled(
                    history, i + 1, event.action,
                )
                if rolled_idx is not None:
                    vp_events_ca: list[Any] = []
                    for j in range(i + 1, rolled_idx):
                        if j in consumed:  # pragma: no cover  # defensive
                            continue
                        if isinstance(history[j], events.SpendVoidPointsEvent):
                            vp_events_ca.append(history[j])
                            consumed.add(j)
                    out.append(self._entry_combined_counterattack(
                        event, history[rolled_idx], vp_events_ca,
                    ))
                    consumed.add(rolled_idx)
                    self._maybe_append_hida_3rd_dan_reroll(out, event.action)
                else:
                    out.append(self._entry_take_counterattack(event))
                    self._maybe_append_hida_3rd_dan_reroll(out, event.action)
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, CounterattackRolledEvent):
                out.append(self._entry_counterattack_rolled(event))
                self._maybe_append_hida_3rd_dan_reroll(out, event.action)
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.AttackRolledEvent):
                out.append(self._entry_attack_rolled(event))
                self._maybe_append_hida_3rd_dan_reroll(out, event.action)
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, ContestedIaijutsuAttackRolledEvent):
                out.append(self._entry_contested_iaijutsu_rolled(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.TakeParryActionEvent):
                rolled_idx = self._find_parry_rolled(history, i + 1, event.action)
                if rolled_idx is not None:
                    out.append(self._entry_combined_parry(event, history[rolled_idx]))
                    consumed.add(rolled_idx)
                else:
                    out.append(self._entry_take_parry(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.ParryRolledEvent):
                out.append(self._entry_parry_rolled(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.LightWoundsDamageEvent):
                # Spec 008 FR-006: when an attack action was a feint with
                # zero damage_roll_params AND the resulting damage is 0,
                # suppress the entry entirely.  The reader sees the
                # feint attack line + school-ability event without a
                # redundant 0-LW damage rendering.  ``_last_attack_skill``
                # was set to ``"feint"`` ONLY for zero-damage feints —
                # Bayushi's special feint clears it so its damage
                # rendering is preserved.
                attacker_name = event.subject.name()
                last_skill = self._last_attack_skill.get(attacker_name)
                if last_skill == "feint" and event.damage == 0:
                    self._last_attack_skill.pop(attacker_name, None)
                    continue
                self._last_attack_skill.pop(attacker_name, None)
                out.append(self._entry_lw_damage(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.SeriousWoundsDamageEvent):
                if self._last_take_sw_target == event.target.name():
                    self._last_take_sw_target = None
                    continue
                self._last_take_sw_target = None
                out.append(self._entry_sw_damage(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.WoundCheckRolledEvent):
                out.append(self._process_wound_check_entry(history, i, consumed))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.SpendVoidPointsEvent):
                if event.skill == "wound check":
                    wc_idx = self._find_wound_check_rolled(
                        history, i + 1, event.subject.name(),
                    )
                    if wc_idx is not None:
                        out.append(self._process_wound_check_entry(
                            history, wc_idx, consumed,
                            vp_prefix_events=[event],
                            wc_event_for_vp=history[wc_idx],
                        ))
                        consumed.add(wc_idx)
                        combat_output_since_status = True
                        any_entry_emitted = True
                        continue
                if (
                    event.skill == "damage"
                    and getattr(event, "source", None) == "Akodo 5th Dan"
                ):
                    counter_idx = self._find_akodo_5th_counter_damage(
                        history, i + 1, event.subject,
                    )
                    if counter_idx is not None:
                        out.append(self._entry_akodo_5th_dan_counter(
                            event, history[counter_idx],
                        ))
                        consumed.add(counter_idx)
                        combat_output_since_status = True
                        any_entry_emitted = True
                        continue
                out.append(self._entry_spend_vp(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.KeepLightWoundsEvent):
                out.append(self._entry_keep_lw(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.TakeSeriousWoundEvent):
                self._last_take_sw_target = event.subject.name()
                out.append(self._entry_take_sw(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.HidaSWForLWTradeEvent):
                # Hida 4th Dan alternative wound check (rules/04-schools.md
                # "Hida Bushi School: Fourth Dan").  The trade replaces
                # the wound check entirely; the SeriousWoundsDamageEvent
                # yielded by the trade's play() handles the 2-SW status
                # bookkeeping (handled by the generic SW dispatch below
                # / above).  This entry is the trade's user-visible
                # attribution per Constitution Principle VII.
                name = event.character.name()
                out.append(HidaSWForLWTradeEntry(
                    phase_prefix=self._phase_prefix(name),
                    character_name=name,
                    lw_reset_from=int(event.lw_reset_from),
                    sw_taken=int(event.sw_taken),
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.MatsuLightWoundsFloorEvent):
                # Matsu 5th Dan LW-floor (rules/04-schools.md "Matsu
                # Bushi School: Fifth Dan").  Pure observability marker:
                # the listener already set the defender's LW to 15; this
                # entry surfaces the attribution per Constitution
                # Principle VII / FR-023.
                defender_name = event.defender.name()
                out.append(MatsuLwFloorEntry(
                    phase_prefix=self._phase_prefix(defender_name),
                    defender_name=defender_name,
                    lw_set_to=int(event.lw_set_to),
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, IaijutsuDuelEvent):
                out.append(IaijutsuDuelHeaderEntry())
                self._phase_shown = True
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, ShowMeYourStanceDeclaredEvent):
                out.append(ShowMeYourStanceDeclaredEntry(
                    character_name=event.subject.name(),
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, ShowMeYourStanceRolledEvent):
                rolled = None
                kept = None
                dice: list[int] = []
                if hasattr(event, "_detail_dice") and event._detail_dice:
                    rp = getattr(event, "_detail_roll_params", None)
                    if rp:
                        rolled = rp["rolled"]
                        kept = rp["kept"]
                        dice = list(event._detail_dice)
                out.append(ShowMeYourStanceRolledEntry(
                    character_name=event.subject.name(),
                    roll=event.roll,
                    discerned_fire=event.discerned_fire,
                    discerned_tn=event.discerned_tn,
                    rolled=rolled,
                    kept=kept,
                    dice=dice,
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, DuelInitiativeRolledEvent):
                out.append(DuelInitiativeRolledEntry(
                    challenger_name=event.challenger.name(),
                    defender_name=event.defender.name(),
                    challenger_roll=event.challenger_roll,
                    defender_roll=event.defender_roll,
                    winner_name=event.winner.name(),
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, IaijutsuFocusEvent):
                out.append(IaijutsuFocusEntry(
                    character_name=event.subject.name(),
                    challenger_name=event.challenger.name(),
                    defender_name=event.defender.name(),
                    challenger_tn=event.challenger_tn,
                    defender_tn=event.defender_tn,
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, IaijutsuStrikeEvent):
                out.append(IaijutsuStrikeEntry(
                    character_name=event.subject.name(),
                    challenger_name=event.challenger.name(),
                    defender_name=event.defender.name(),
                    challenger_tn=event.challenger_tn,
                    defender_tn=event.defender_tn,
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, DuelStrikeRolledEvent):
                ds_rolled = None
                ds_kept = None
                ds_dice: list[int] = []
                if hasattr(event, "_detail_dice") and event._detail_dice:
                    rp = getattr(event, "_detail_roll_params", None)
                    if rp:
                        ds_rolled = rp["rolled"]
                        ds_kept = rp["kept"]
                        ds_dice = list(event._detail_dice)
                out.append(DuelStrikeRolledEntry(
                    character_name=event.subject.name(),
                    target_name=event.target.name(),
                    roll=event.roll,
                    tn=event.tn,
                    is_hit=event.is_hit,
                    extra_damage_dice=event.extra_damage_dice,
                    rolled=ds_rolled,
                    kept=ds_kept,
                    dice=ds_dice,
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, DuelResheathEvent):
                out.append(DuelResheathEntry(
                    higher_roller_name=event.higher_roller.name(),
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, DuelEndedEvent):
                out.append(DuelEndedEntry())
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.DeathEvent):
                name = event.subject.name()
                out.append(DeathEntry(
                    phase_prefix=self._phase_prefix(name),
                    character_name=name,
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.UnconsciousEvent):
                name = event.subject.name()
                out.append(UnconsciousEntry(
                    phase_prefix=self._phase_prefix(name),
                    character_name=name,
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.SurrenderEvent):
                name = event.subject.name()
                out.append(SurrenderEntry(
                    phase_prefix=self._phase_prefix(name),
                    character_name=name,
                ))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.SchoolNegatedEvent):
                out.append(self._entry_school_negated(event))
                combat_output_since_status = True
                any_entry_emitted = True

            elif isinstance(event, events.GainTemporaryVoidPointsEvent):
                tvp_entry = self._entry_gain_tvp(event)
                if tvp_entry is not None:
                    out.append(tvp_entry)
                    combat_output_since_status = True
                    any_entry_emitted = True

            elif isinstance(event, events.GainFloatingBonusEvent):
                gfb_entry = self._entry_gain_floating_bonus(event)
                if gfb_entry is not None:
                    out.append(gfb_entry)
                    combat_output_since_status = True
                    any_entry_emitted = True

            elif isinstance(event, events.SpendFloatingBonusEvent):
                sfb_entry = self._entry_spend_floating_bonus(event)
                out.append(sfb_entry)
                combat_output_since_status = True
                any_entry_emitted = True

        _ = any_entry_emitted  # for symmetry with format_history's tracking
        return out

    def _phase_prefix(self, char_name: str) -> str:
        """Returns 'Phase X | Name |' on first call per phase, then 'Name |'."""
        if not self._phase_shown:
            self._phase_shown = True
            return f"Phase {self._current_phase} | {char_name} |"
        return f"{char_name} |"

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

    # ── Structured-entry builders (spec 007) ──────────────────────────

    @staticmethod
    def _to_components(
        raw: list[tuple[str, int, int]] | None,
    ) -> list[ComponentDelta]:
        if not raw:
            return []
        return [ComponentDelta(source=s, rolled=r, kept=k) for s, r, k in raw]

    @staticmethod
    def _to_modifier_components(
        raw: list[tuple[str, int]] | None,
    ) -> list[ModifierDelta]:
        if not raw:
            return []
        return [ModifierDelta(source=s, amount=v) for s, v in raw]

    def _entry_initiative(self, event: Any) -> InitiativeEntry:
        entries_list: list[dict[str, Any]] = []
        for name, data in event._detail_initiative.items():
            rolled, kept = data["roll_params"]
            entries_list.append({
                "name": name,
                "rolled": rolled,
                "kept": kept,
                "all_dice": list(data["all_dice"]),
                "actions": list(data["actions"]),
            })
        return InitiativeEntry(entries=entries_list)

    def _entry_take_attack(self, event: Any) -> AttackEntry:
        """Standalone TakeAttackActionEvent (no AttackRolledEvent yet)."""
        action = event.action
        subj = action.subject().name()
        tgt = action.target().name()
        skill = action.skill()
        return AttackEntry(
            phase_prefix=self._phase_prefix(subj),
            actor_name=subj, target_name=tgt, skill=skill,
            vp_spent=None, vp_skill=None,
            rolled=0, kept=0, modifier=0,
            components=[], modifier_components=[],
            dice=[], sum_of_kept=0, total=0,
            tn=0, base_tn=0, outcome="miss",
            damage_projection=None,
            has_detail=False, fallback_roll=0,
            is_combined=True, is_take_only=True,
        )

    def _entry_take_counterattack(self, event: Any) -> CounterattackEntry:
        action = event.action
        subj = action.subject().name()
        tgt = action.target().name()
        return CounterattackEntry(
            phase_prefix=self._phase_prefix(subj),
            actor_name=subj, target_name=tgt,
            vp_spent=None, vp_skill=None,
            rolled=0, kept=0, modifier=0,
            components=[], modifier_components=[],
            dice=[], sum_of_kept=0, total=0,
            tn=0, outcome="miss", damage_projection=None,
            has_detail=False, fallback_roll=0,
            is_combined=True, is_take_only=True,
        )

    def _entry_take_parry(self, event: Any) -> ParryEntry:
        action = event.action
        subj = action.subject().name()
        tgt = action.target().name()
        return ParryEntry(
            phase_prefix=self._phase_prefix(subj),
            actor_name=subj, target_name=tgt,
            rolled=0, kept=0, modifier=0,
            components=[], modifier_components=[],
            dice=[], sum_of_kept=0, total=0,
            tn=0, outcome="failed",
            has_detail=False, fallback_roll=0,
            is_combined=True, is_take_only=True,
        )

    def _entry_attack_rolled(self, event: Any) -> AttackEntry:
        """Standalone AttackRolledEvent (no take_attack preceded it)."""
        action = event.action
        subj = action.subject().name()
        tgt = action.target().name()
        skill = action.skill()
        phase_prefix = self._phase_prefix(subj)

        if not hasattr(event, "_detail_dice"):
            # Spec 008 FR-005: a feint with zero damage params has its
            # projection suppressed.  We don't have detail here so we
            # use the action's damage_roll_params directly.
            no_detail_suppress = (
                skill == "feint"
                and tuple(action.damage_roll_params()) == (0, 0, 0)
            )
            # Track skill so the upcoming LW damage event can be
            # suppressed for zero-damage feints (FR-006).
            self._last_attack_skill[subj] = skill
            return AttackEntry(
                phase_prefix=phase_prefix,
                actor_name=subj, target_name=tgt, skill=skill,
                vp_spent=None, vp_skill=None,
                rolled=0, kept=0, modifier=0,
                components=[], modifier_components=[],
                dice=[], sum_of_kept=0, total=0,
                tn=0, base_tn=0, outcome="miss",
                damage_projection=None,
                has_detail=False, fallback_roll=event.roll,
                is_combined=False,
                suppress_damage_projection=no_detail_suppress,
            )

        dice = list(event._detail_dice)
        rolled, kept, mod = event._detail_params
        tn = event._detail_tn
        base_tn = getattr(event, "_detail_base_tn", tn)
        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod

        hit = action.is_hit() and not action.parried()
        outcome: Any = "hit" if hit else "miss"
        damage_projection = None
        # Spec 008 FR-005/6: a feint whose damage_roll_params are
        # (0, 0, 0) deals 0 LW deterministically; suppress its
        # projection AND the followup LW damage event.  Bayushi's
        # special feint has non-zero damage params (the school's
        # ``BayushiFeintAction`` overrides ``damage_roll_params``) so
        # those continue to render normally.
        is_zero_damage_feint = False
        if hit:
            extra_dice = action.calculate_extra_damage_dice(tn=base_tn)
            damage_params = action.damage_roll_params()
            margin = total - tn
            if damage_params:
                dr, dk, _dm = damage_params
                damage_breakdown_raw = action.damage_breakdown()
                damage_projection = DamageProjection(
                    rolled=dr, kept=dk,
                    components=self._to_components(damage_breakdown_raw),
                    extra_damage_dice=extra_dice,
                    margin_over_tn=margin,
                )
            if (
                skill == "feint"
                and tuple(action.damage_roll_params()) == (0, 0, 0)
            ):  # pragma: no cover  # defensive: standalone AttackRolledEvent without a preceding TakeAttackActionEvent is the FR-007 fallback; engine always emits the take-action event first
                is_zero_damage_feint = True
        else:
            # Even on a miss, feints can fire (Bayushi 4th Dan fires
            # on failed feint).  No damage event will follow because
            # the attack didn't hit.  No suppression state needed.
            pass

        # Record the skill so the following LW damage event can be
        # absorbed when this is a zero-damage feint (FR-006).
        if is_zero_damage_feint:  # pragma: no cover  # defensive: only reachable from the standalone-rolled-event feint path above
            self._last_attack_skill[subj] = "feint"
        else:
            self._last_attack_skill.pop(subj, None)

        return AttackEntry(
            phase_prefix=phase_prefix,
            actor_name=subj, target_name=tgt, skill=skill,
            vp_spent=None, vp_skill=None,
            rolled=rolled, kept=kept, modifier=mod,
            components=self._to_components(getattr(event, "_detail_components", None)),
            modifier_components=self._to_modifier_components(
                getattr(event, "_detail_modifier_breakdown", None),
            ),
            dice=dice, sum_of_kept=kept_sum, total=total,
            tn=tn, base_tn=base_tn, outcome=outcome,
            damage_projection=damage_projection,
            is_combined=False,
            suppress_damage_projection=is_zero_damage_feint,
        )

    def _entry_combined_attack(
        self,
        take_event: Any,
        rolled_event: Any,
        vp_events: list[Any],
        fb_events: list[Any] | None = None,
    ) -> AttackEntry:
        action = take_event.action
        subj = action.subject().name()
        tgt = action.target().name()
        skill = action.skill()
        phase_prefix = self._phase_prefix(subj)

        vp_total = sum(e.amount for e in vp_events) if vp_events else None
        vp_skill = vp_events[0].skill if vp_events else None

        # Spec 008 FR-008/9: floating-bonus consumption integrated
        # into the attack line.  Build the consumed_floating_bonuses
        # list from the absorbed SpendFloatingBonusEvent(s).
        consumed_fb: list[ModifierDelta] = []
        if fb_events:
            for fb_ev in fb_events:
                bonus = fb_ev.bonus
                amount = bonus.bonus() if hasattr(bonus, "bonus") else 0
                src = bonus.source() if hasattr(bonus, "source") else None
                consumed_fb.append(ModifierDelta(
                    source=src or "floating bonus", amount=amount,
                ))

        if not hasattr(rolled_event, "_detail_dice"):
            no_detail_suppress = (
                skill == "feint"
                and tuple(action.damage_roll_params()) == (0, 0, 0)
            )
            if no_detail_suppress:  # pragma: no cover  # defensive: ``AttackRolledEvent`` without ``_detail_dice`` is the fallback path for un-annotated events; combat-observer-annotated events always carry the detail
                self._last_attack_skill[subj] = "feint"
            else:
                self._last_attack_skill.pop(subj, None)
            return AttackEntry(
                phase_prefix=phase_prefix,
                actor_name=subj, target_name=tgt, skill=skill,
                vp_spent=vp_total, vp_skill=vp_skill,
                rolled=0, kept=0, modifier=0,
                components=[], modifier_components=[],
                dice=[], sum_of_kept=0, total=0,
                tn=0, base_tn=0, outcome="miss",
                damage_projection=None,
                has_detail=False, fallback_roll=rolled_event.roll,
                suppress_damage_projection=no_detail_suppress,
                consumed_floating_bonuses=consumed_fb,
            )

        dice = list(rolled_event._detail_dice)
        rolled, kept, mod = rolled_event._detail_params
        tn = rolled_event._detail_tn
        base_tn = getattr(rolled_event, "_detail_base_tn", tn)
        kept_sum = sum(dice[:kept]) if dice else rolled_event.roll
        total = kept_sum + mod

        hit = action.is_hit() and not action.parried()
        outcome: Any = "hit" if hit else "miss"
        damage_projection = None
        # Spec 008 FR-005/6: a feint whose damage_roll_params are
        # (0, 0, 0) deals 0 LW deterministically (the standard
        # ``FeintAction``); suppress its projection AND the followup
        # LW damage event.  Bayushi's ``BayushiFeintAction`` overrides
        # damage_roll_params to non-zero so those keep rendering.
        is_zero_damage_feint = (
            skill == "feint"
            and tuple(action.damage_roll_params()) == (0, 0, 0)
        )
        if hit:
            extra_dice = action.calculate_extra_damage_dice(tn=base_tn)
            damage_params = action.damage_roll_params()
            margin = total - tn
            if damage_params:
                dr, dk, _dm = damage_params
                damage_breakdown_raw = action.damage_breakdown()
                damage_projection = DamageProjection(
                    rolled=dr, kept=dk,
                    components=self._to_components(damage_breakdown_raw),
                    extra_damage_dice=extra_dice,
                    margin_over_tn=margin,
                )

        # Record the skill so the following LW damage event can be
        # absorbed when this is a zero-damage feint.
        if is_zero_damage_feint:
            self._last_attack_skill[subj] = "feint"
        else:
            self._last_attack_skill.pop(subj, None)

        # rules/04-schools.md "Matsu Bushi School: Fourth Dan":
        # ``MatsuDoubleAttackAction`` may hit on skill_roll < tn (a
        # near-miss in the carve-out tn-20 <= roll < tn).  Surface the
        # attribution per Constitution Principle VII / FR-021.  We
        # detect the near-miss via the action's ``_is_near_miss``
        # property (set only by ``MatsuDoubleAttackAction``), avoiding a
        # direct import dependency on the school module.  The check
        # is ``is True`` so a MagicMock action in tests (whose attribute
        # access returns a truthy MagicMock by default) does NOT
        # accidentally enable the attribution path.  The "below TN"
        # margin is reported relative to the action's full TN
        # (i.e., ``base_tn + 20`` for double attack).
        near_miss_below_tn = 0
        if hit and getattr(action, "_is_near_miss", False) is True:
            skill_roll_val = action.skill_roll()
            if skill_roll_val is not None and skill_roll_val < tn:
                near_miss_below_tn = tn - skill_roll_val

        return AttackEntry(
            phase_prefix=phase_prefix,
            actor_name=subj, target_name=tgt, skill=skill,
            vp_spent=vp_total, vp_skill=vp_skill,
            rolled=rolled, kept=kept, modifier=mod,
            components=self._to_components(
                getattr(rolled_event, "_detail_components", None),
            ),
            modifier_components=self._to_modifier_components(
                getattr(rolled_event, "_detail_modifier_breakdown", None),
            ),
            dice=dice, sum_of_kept=kept_sum, total=total,
            tn=tn, base_tn=base_tn, outcome=outcome,
            damage_projection=damage_projection,
            suppress_damage_projection=is_zero_damage_feint,
            consumed_floating_bonuses=consumed_fb,
            matsu_4th_dan_near_miss_below_tn=near_miss_below_tn,
        )

    def _entry_counterattack_rolled(self, event: Any) -> CounterattackEntry:
        action = event.action
        subj = action.subject().name()
        tgt = action.target().name()
        phase_prefix = self._phase_prefix(subj)

        if not hasattr(event, "_detail_dice"):
            return CounterattackEntry(
                phase_prefix=phase_prefix,
                actor_name=subj, target_name=tgt,
                vp_spent=None, vp_skill=None,
                rolled=0, kept=0, modifier=0,
                components=[], modifier_components=[],
                dice=[], sum_of_kept=0, total=0,
                tn=0, outcome="miss", damage_projection=None,
                has_detail=False, fallback_roll=event.roll,
                is_combined=False,
            )

        dice = list(event._detail_dice)
        rolled, kept, mod = event._detail_params
        tn = event._detail_tn
        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod
        hit = action.is_hit()
        outcome: Any = "hit" if hit else "miss"
        return CounterattackEntry(
            phase_prefix=phase_prefix,
            actor_name=subj, target_name=tgt,
            vp_spent=None, vp_skill=None,
            rolled=rolled, kept=kept, modifier=mod,
            components=self._to_components(getattr(event, "_detail_components", None)),
            modifier_components=self._to_modifier_components(
                getattr(event, "_detail_modifier_breakdown", None),
            ),
            dice=dice, sum_of_kept=kept_sum, total=total,
            tn=tn, outcome=outcome, damage_projection=None,
            is_combined=False,
        )

    def _entry_combined_counterattack(
        self, take_event: Any, rolled_event: Any, vp_events: list[Any],
    ) -> CounterattackEntry:
        action = take_event.action
        subj = action.subject().name()
        tgt = action.target().name()
        phase_prefix = self._phase_prefix(subj)

        vp_total = sum(e.amount for e in vp_events) if vp_events else None
        vp_skill = vp_events[0].skill if vp_events else None

        if not hasattr(rolled_event, "_detail_dice"):
            return CounterattackEntry(
                phase_prefix=phase_prefix,
                actor_name=subj, target_name=tgt,
                vp_spent=vp_total, vp_skill=vp_skill,
                rolled=0, kept=0, modifier=0,
                components=[], modifier_components=[],
                dice=[], sum_of_kept=0, total=0,
                tn=0, outcome="miss", damage_projection=None,
                has_detail=False, fallback_roll=rolled_event.roll,
            )

        dice = list(rolled_event._detail_dice)
        rolled, kept, mod = rolled_event._detail_params
        tn = rolled_event._detail_tn
        kept_sum = sum(dice[:kept]) if dice else rolled_event.roll
        total = kept_sum + mod

        hit = action.is_hit()
        outcome: Any = "hit" if hit else "miss"
        damage_projection = None
        if hit:
            extra_dice = action.calculate_extra_damage_dice(tn=tn)
            damage_params = action.damage_roll_params()
            margin = total - tn
            if damage_params:
                dr, dk, _dm = damage_params
                damage_breakdown_raw = action.damage_breakdown()
                damage_projection = DamageProjection(
                    rolled=dr, kept=dk,
                    components=self._to_components(damage_breakdown_raw),
                    extra_damage_dice=extra_dice,
                    margin_over_tn=margin,
                )

        return CounterattackEntry(
            phase_prefix=phase_prefix,
            actor_name=subj, target_name=tgt,
            vp_spent=vp_total, vp_skill=vp_skill,
            rolled=rolled, kept=kept, modifier=mod,
            components=self._to_components(
                getattr(rolled_event, "_detail_components", None),
            ),
            modifier_components=self._to_modifier_components(
                getattr(rolled_event, "_detail_modifier_breakdown", None),
            ),
            dice=dice, sum_of_kept=kept_sum, total=total,
            tn=tn, outcome=outcome, damage_projection=damage_projection,
        )

    def _entry_parry_rolled(self, event: Any) -> ParryEntry:
        action = event.action
        subj = action.subject().name()
        tgt = action.target().name()
        phase_prefix = self._phase_prefix(subj)

        if not hasattr(event, "_detail_dice"):
            return ParryEntry(
                phase_prefix=phase_prefix,
                actor_name=subj, target_name=tgt,
                rolled=0, kept=0, modifier=0,
                components=[], modifier_components=[],
                dice=[], sum_of_kept=0, total=0,
                tn=0, outcome="failed",
                has_detail=False, fallback_roll=event.roll,
                is_combined=False,
            )

        dice = list(event._detail_dice)
        rolled, kept, mod = event._detail_params
        tn = event._detail_tn
        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod
        succeeded = action.is_success()
        outcome: Any = "succeeded" if succeeded else "failed"
        return ParryEntry(
            phase_prefix=phase_prefix,
            actor_name=subj, target_name=tgt,
            rolled=rolled, kept=kept, modifier=mod,
            components=self._to_components(getattr(event, "_detail_components", None)),
            modifier_components=self._to_modifier_components(
                getattr(event, "_detail_modifier_breakdown", None),
            ),
            dice=dice, sum_of_kept=kept_sum, total=total,
            tn=tn, outcome=outcome,
            is_combined=False,
        )

    def _entry_combined_parry(
        self, take_event: Any, rolled_event: Any,
    ) -> ParryEntry:
        action = take_event.action
        subj = action.subject().name()
        tgt = action.target().name()
        phase_prefix = self._phase_prefix(subj)

        if not hasattr(rolled_event, "_detail_dice"):
            return ParryEntry(
                phase_prefix=phase_prefix,
                actor_name=subj, target_name=tgt,
                rolled=0, kept=0, modifier=0,
                components=[], modifier_components=[],
                dice=[], sum_of_kept=0, total=0,
                tn=0, outcome="failed",
                has_detail=False, fallback_roll=rolled_event.roll,
            )

        dice = list(rolled_event._detail_dice)
        rolled, kept, mod = rolled_event._detail_params
        tn = rolled_event._detail_tn
        kept_sum = sum(dice[:kept]) if dice else rolled_event.roll
        total = kept_sum + mod
        succeeded = action.is_success()
        outcome: Any = "succeeded" if succeeded else "failed"
        return ParryEntry(
            phase_prefix=phase_prefix,
            actor_name=subj, target_name=tgt,
            rolled=rolled, kept=kept, modifier=mod,
            components=self._to_components(
                getattr(rolled_event, "_detail_components", None),
            ),
            modifier_components=self._to_modifier_components(
                getattr(rolled_event, "_detail_modifier_breakdown", None),
            ),
            dice=dice, sum_of_kept=kept_sum, total=total,
            tn=tn, outcome=outcome,
        )

    def _entry_contested_iaijutsu_rolled(self, event: Any) -> IaijutsuEntry:
        action = event.action
        name = action.subject().name()
        is_challenger = action.challenger() == action.subject()
        skill_roll = action.skill_roll()
        opponent_roll = action.opponent_skill_roll()
        extra_dice = action.calculate_extra_damage_dice()

        rolled_val = 0
        kept_val = 0
        dice: list[int] = []
        kept_sum = skill_roll
        effective_mod = 0
        has_detail = False
        if hasattr(event, "_detail_dice") and hasattr(event, "_detail_params"):
            dice = list(event._detail_dice)
            rolled_val, kept_val, _mod = event._detail_params
            kept_sum = sum(dice[:kept_val]) if dice else skill_roll
            effective_mod = skill_roll - kept_sum
            has_detail = True

        return IaijutsuEntry(
            phase_prefix=self._phase_prefix(name),
            actor_name=name,
            is_challenger=is_challenger,
            skill=action.skill(),
            skill_roll=skill_roll,
            opponent_skill_roll=opponent_roll,
            extra_damage_dice=extra_dice,
            rolled=rolled_val,
            kept=kept_val,
            dice=dice,
            sum_of_kept=kept_sum,
            effective_modifier=effective_mod,
            has_detail=has_detail,
        )

    def _entry_lw_damage(self, event: Any) -> LightWoundsDamageEntry:
        attacker = event.subject.name()
        target = event.target.name()

        if not hasattr(event, "_detail_dice"):
            return LightWoundsDamageEntry(
                phase_prefix=self._phase_prefix(target),
                attacker_name=attacker, target_name=target,
                rolled=0, kept=0, components=[],
                dice=[], sum_of_kept=0,
                damage=event.damage, lw_after=None,
                has_detail=False,
            )

        dice = list(event._detail_dice)
        rolled, kept = event._detail_params
        kept_sum = sum(dice[:kept]) if dice else event.damage
        return LightWoundsDamageEntry(
            phase_prefix=self._phase_prefix(attacker),
            attacker_name=attacker, target_name=target,
            rolled=rolled, kept=kept,
            components=self._to_components(getattr(event, "_detail_components", None)),
            dice=dice, sum_of_kept=kept_sum,
            damage=event.damage,
            lw_after=getattr(event, "_detail_lw_after", None),
        )

    def _entry_sw_damage(self, event: Any) -> SeriousWoundsDamageEntry:
        target = event.target.name()
        return SeriousWoundsDamageEntry(
            phase_prefix=self._phase_prefix(target),
            target_name=target,
            damage=event.damage,
            from_double_attack=bool(getattr(event, "_from_double_attack", False)),
        )

    def _build_wound_check_entry(
        self,
        event: Any,
        *,
        vp_spent: int | None,
        vp_source: str | None,
        vp_skill: str | None,
        vp_breakdown: str | None,
        follow_up: str,
        follow_up_sw_count: int,
        follow_up_lw_total: int,
        follow_up_voluntary: bool,
    ) -> WoundCheckEntry:
        name = event.subject.name()
        passed = event.roll >= event.tn
        outcome: Any = "passed" if passed else "failed"

        # rules/04-schools.md "Hida Bushi School: Fifth Dan":
        # the WC roll on damage from a counterattacked attack carries an
        # ``_hida_5th_dan_excess_bonus`` annotation (set by
        # ``WoundCheckDeclaredListener``).  Surface it on the entry so the
        # renderer can attribute the bonus per Principle VII.
        hida_5th_dan_excess_bonus = int(
            getattr(event, "_hida_5th_dan_excess_bonus", 0) or 0,
        )

        if not hasattr(event, "_detail_dice"):
            return WoundCheckEntry(
                phase_prefix=self._phase_prefix(name),
                character_name=name,
                vp_spent=vp_spent, vp_source=vp_source, vp_skill=vp_skill,
                vp_breakdown=vp_breakdown,
                rolled=0, kept=0, modifier=0,
                components=[], modifier_components=[],
                dice=[], sum_of_kept=0, total=0,
                tn=event.tn, outcome=outcome,
                has_detail=False, fallback_roll=event.roll,
                follow_up=follow_up,  # type: ignore[arg-type]
                follow_up_sw_count=follow_up_sw_count,
                follow_up_lw_total=follow_up_lw_total,
                follow_up_voluntary=follow_up_voluntary,
                hida_5th_dan_excess_bonus=hida_5th_dan_excess_bonus,
            )

        dice = list(event._detail_dice)
        rolled, kept, mod = self._unpack_wound_check_params(event._detail_params)
        kept_sum = sum(dice[:kept]) if dice else event.roll
        total = kept_sum + mod
        return WoundCheckEntry(
            phase_prefix=self._phase_prefix(name),
            character_name=name,
            vp_spent=vp_spent, vp_source=vp_source, vp_skill=vp_skill,
            vp_breakdown=vp_breakdown,
            rolled=rolled, kept=kept, modifier=mod,
            components=self._to_components(getattr(event, "_detail_components", None)),
            modifier_components=self._to_modifier_components(
                getattr(event, "_detail_modifier_breakdown", None),
            ),
            dice=dice, sum_of_kept=kept_sum, total=total,
            tn=event.tn, outcome=outcome,
            follow_up=follow_up,  # type: ignore[arg-type]
            follow_up_sw_count=follow_up_sw_count,
            follow_up_lw_total=follow_up_lw_total,
            follow_up_voluntary=follow_up_voluntary,
            hida_5th_dan_excess_bonus=hida_5th_dan_excess_bonus,
        )

    def _process_wound_check_entry(
        self,
        history: list[Any],
        wc_idx: int,
        consumed: set[int],
        *,
        vp_prefix_events: list[Any] | None = None,
        wc_event_for_vp: Any | None = None,
    ) -> WoundCheckEntry:
        event = history[wc_idx]
        passed = event.roll >= event.tn
        self._last_wc_passed[event.subject.name()] = passed

        # Resolve VP-prefix (Akodo 4th Dan or plain VP-on-wound-check).
        vp_spent: int | None = None
        vp_source: str | None = None
        vp_skill: str | None = None
        vp_breakdown: str | None = None
        if vp_prefix_events:
            vp_spent = sum(e.amount for e in vp_prefix_events)
            vp_skill = vp_prefix_events[0].skill
            akodo_sources = [
                e for e in vp_prefix_events
                if getattr(e, "source", None) == "Akodo 4th Dan"
            ]
            if (
                akodo_sources
                and vp_skill == "wound check"
                and wc_event_for_vp is not None
            ):
                vp_source = "Akodo 4th Dan"
                akodo_total = sum(e.amount for e in akodo_sources)
                new_roll = wc_event_for_vp.roll
                orig_roll = new_roll - (5 * akodo_total)
                vp_breakdown = (
                    f"+5 per VP = +{5 * akodo_total} ({orig_roll}→{new_roll})"
                )

        # Look ahead for matching TakeSW/KeepLW to compose follow-up.
        sw_idx = self._find_take_sw(history, wc_idx + 1, event.subject.name())
        if sw_idx is not None:
            self._last_take_sw_target = event.subject.name()
            consumed.add(sw_idx)
            sw_count = 1
            sw_dmg_idx = self._find_sw_damage(
                history, sw_idx + 1, event.subject.name(),
            )
            if sw_dmg_idx is not None:
                sw_count = history[sw_dmg_idx].damage
                consumed.add(sw_dmg_idx)
            voluntary = self._last_wc_passed.get(event.subject.name(), False)
            return self._build_wound_check_entry(
                event, vp_spent=vp_spent, vp_source=vp_source,
                vp_skill=vp_skill, vp_breakdown=vp_breakdown,
                follow_up="take_sw",
                follow_up_sw_count=sw_count,
                follow_up_lw_total=0,
                follow_up_voluntary=voluntary,
            )

        keep_idx = self._find_keep_lw(history, wc_idx + 1, event.subject.name())
        if keep_idx is not None:
            consumed.add(keep_idx)
            lw_total = getattr(
                history[keep_idx], "_detail_lw_total", history[keep_idx].damage,
            )
            return self._build_wound_check_entry(
                event, vp_spent=vp_spent, vp_source=vp_source,
                vp_skill=vp_skill, vp_breakdown=vp_breakdown,
                follow_up="keep_lw",
                follow_up_sw_count=0,
                follow_up_lw_total=lw_total,
                follow_up_voluntary=False,
            )

        return self._build_wound_check_entry(
            event, vp_spent=vp_spent, vp_source=vp_source,
            vp_skill=vp_skill, vp_breakdown=vp_breakdown,
            follow_up="none",
            follow_up_sw_count=0,
            follow_up_lw_total=0,
            follow_up_voluntary=False,
        )

    def _entry_spend_vp(self, event: Any) -> SpendVpEntry:
        name = event.subject.name()
        return SpendVpEntry(
            phase_prefix=self._phase_prefix(name),
            character_name=name,
            amount=event.amount,
            skill=event.skill,
        )

    def _entry_gain_tvp(self, event: Any) -> GainTvpEntry | None:
        if event.amount <= 0:
            return None
        name = event.subject.name()
        return GainTvpEntry(
            phase_prefix=self._phase_prefix(name),
            character_name=name,
            amount=event.amount,
            source=getattr(event, "source", None),
        )

    def _entry_gain_floating_bonus(
        self, event: Any,
    ) -> GainFloatingBonusEntry | None:
        bonus_value = event.bonus.bonus() if hasattr(event.bonus, "bonus") else 0
        if bonus_value <= 0:
            return None
        name = event.subject.name()
        return GainFloatingBonusEntry(
            phase_prefix=self._phase_prefix(name),
            character_name=name,
            amount=bonus_value,
            source=event.source,
            breakdown=event.breakdown,
        )

    def _entry_spend_floating_bonus(self, event: Any) -> SpendFloatingBonusEntry:
        bonus = event.bonus
        bonus_value = bonus.bonus() if hasattr(bonus, "bonus") else 0
        source = bonus.source() if hasattr(bonus, "source") else None
        name = event.subject.name()
        return SpendFloatingBonusEntry(
            phase_prefix=self._phase_prefix(name),
            character_name=name,
            amount=bonus_value,
            source=source,
        )

    def _entry_school_negated(self, event: Any) -> SchoolNegatedEntry:
        negator = event.negator.name()
        return SchoolNegatedEntry(
            phase_prefix=self._phase_prefix(negator),
            negator_name=negator,
            target_name=event.target.name(),
            target_school_name=event.target_school_name,
            vp_cost=event.vp_cost,
        )

    def _entry_keep_lw(self, event: Any) -> KeepLightWoundsEntry:
        name = event.subject.name()
        return KeepLightWoundsEntry(
            phase_prefix=self._phase_prefix(name),
            character_name=name,
            lw_total=getattr(event, "_detail_lw_total", event.damage),
        )

    def _entry_take_sw(self, event: Any) -> TakeSeriousWoundEntry:
        name = event.subject.name()
        voluntary = self._last_wc_passed.get(name, False)
        return TakeSeriousWoundEntry(
            phase_prefix=self._phase_prefix(name),
            character_name=name,
            voluntary=voluntary,
        )

    def _entry_akodo_5th_dan_counter(
        self, spend_event: Any, counter_event: Any,
    ) -> AkodoFifthDanCounterEntry:
        name = spend_event.subject.name()
        return AkodoFifthDanCounterEntry(
            phase_prefix=self._phase_prefix(name),
            akodo_name=name,
            vp_spent=spend_event.amount,
            damage=counter_event.damage,
            target_name=counter_event.target.name(),
        )

    def _maybe_append_hida_3rd_dan_reroll(
        self, out: list[TraceEntry], action: Any,
    ) -> None:
        """If the action carries a ``_hida_3rd_dan_reroll`` annotation
        (set by ``Action.roll_skill`` when the subject is a 3rd-Dan
        Hida), append a ``HidaThirdDanRerollEntry`` to ``out`` so the
        renderer can surface the before→after dice with the source
        label (Constitution Principle VII).

        Idempotent within a single ``entries()`` call: tracks
        already-emitted actions by ``id`` so the reroll isn't
        rendered twice (e.g., both the take-action and the rolled
        event reach this hook).  Does NOT mutate the action — re-
        calls to ``entries(history)`` will re-emit the same entry.

        Defensively gated on ``isinstance(info, dict)`` so MagicMock
        actions in tests don't synthesize spurious entries (a bare
        ``getattr`` would return a MagicMock).
        """
        info = getattr(action, "_hida_3rd_dan_reroll", None)
        if not isinstance(info, dict):
            return
        action_id = id(action)
        if action_id in self._hida_3rd_dan_emitted:  # pragma: no cover  # defensive: the formatter consumes the rolled-event index when a take_attack event has a paired rolled event, so the second hook (on AttackRolledEvent alone) is unreachable on the standard flow.  Kept to protect against future flow changes.
            return
        self._hida_3rd_dan_emitted.add(action_id)
        name = action.subject().name()
        entry = HidaThirdDanRerollEntry(
            phase_prefix=self._phase_prefix(name),
            actor_name=name,
            skill=str(info["skill"]),
            n=int(info["n"]),
            crippled=bool(info["crippled"]),
            rerolls=[(int(b), int(a)) for (b, a) in info["rerolls"]],
            before_total=int(info["before_total"]),
            after_total=int(info["after_total"]),
        )
        out.append(entry)
