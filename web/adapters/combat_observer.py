"""CombatObserver, TrackingRollProvider, and DetailedCombatEngine for rich combat output."""

from typing import Any

from simulation import events
from simulation.duel import (
    DuelInitiativeRolledEvent,
    DuelStrikeRolledEvent,
    ShowMeYourStanceRolledEvent,
)
from simulation.engine import CombatEngine
from simulation.events import CounterattackRolledEvent, TakeCounterattackActionEvent
from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER, DieProvider
from simulation.mechanics.roll_params import _normalize_breakdown
from simulation.mechanics.roll_provider import RollProvider
from simulation.schools.kakita_school import ContestedIaijutsuAttackRolledEvent
from web.adapters.modifier_breakdown import explain_modifier


def _reconcile_breakdown(
    components: list[tuple[str, int, int]], aggregate: tuple[int, int],
) -> list[tuple[str, int, int]]:
    """Adjust ``components`` so its summed ``(rolled, kept)`` equals the
    displayed ``aggregate``. When the components already sum correctly
    (the common case), the list is returned unchanged. Otherwise a
    synthetic ``"from dice in excess of 10k10"`` entry is appended
    (or the existing one updated) to absorb the delta — preserving
    the data-model.md invariant ``sum(components) == aggregate_*`` so
    the trace renders a per-line self-explaining breakdown (FR-017).
    """
    return _normalize_breakdown(components, aggregate[0], aggregate[1])


class _RecordingDieProvider(DieProvider):
    """Wraps a DieProvider and records each top-level die result."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.recorded: list[int] = []

    def roll_die(self, faces: int = 10, explode: bool = True) -> int:
        result: int = self._inner.roll_die(faces, explode)
        self.recorded.append(result)
        result_int: int = result
        return result_int


class TrackingRollProvider(RollProvider):
    """Wrapper that delegates all rolls to an inner provider and captures dice data.

    Uses a recording die provider to intercept dice at the source, so dice
    are captured regardless of whether the inner Roll objects store them.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._last_skill_info: dict[str, Any] | None = None
        self._last_damage_info: dict[str, Any] | None = None
        self._last_wound_check_info: dict[str, Any] | None = None
        self._last_initiative_info: dict[str, Any] | None = None

    def die_provider(self) -> Any:
        return self._inner.die_provider()

    def set_die_provider(self, die_provider: Any) -> None:
        self._inner.set_die_provider(die_provider)

    def _with_recording(self, fn: Any) -> tuple[Any, list[int]]:
        """Call fn() with a recording die provider temporarily installed on inner.

        Returns (result, recorded_dice).
        """
        original_dp = self._inner._die_provider
        recorder = _RecordingDieProvider(original_dp or DEFAULT_DIE_PROVIDER)
        self._inner._die_provider = recorder
        try:
            result = fn()
        finally:
            self._inner._die_provider = original_dp
        return result, list(recorder.recorded)

    def get_skill_roll(self, skill: str, rolled: int, kept: int, explode: bool = True) -> int:
        result, recorded = self._with_recording(
            lambda: self._inner.get_skill_roll(skill, rolled, kept, explode)
        )
        # Prefer inner's stored dice (handles WaveManRoll transformations),
        # fall back to recorded raw dice
        inner_info = self._inner.last_skill_info() if hasattr(self._inner, "last_skill_info") else None
        dice = inner_info["dice"] if inner_info and inner_info.get("dice") else recorded
        self._last_skill_info = {"rolled": rolled, "kept": kept, "dice": sorted(dice, reverse=True)}
        result_int: int = result
        return result_int

    def get_damage_roll(self, rolled: int, kept: int) -> int:
        result, recorded = self._with_recording(
            lambda: self._inner.get_damage_roll(rolled, kept)
        )
        inner_info = self._inner.last_damage_info() if hasattr(self._inner, "last_damage_info") else None
        dice = inner_info["dice"] if inner_info and inner_info.get("dice") else recorded
        self._last_damage_info = {"rolled": rolled, "kept": kept, "dice": sorted(dice, reverse=True)}
        result_int: int = result
        return result_int

    def get_damage_reduction_roll(self, rolled: int, kept: int, reduction: int) -> int:
        result, recorded = self._with_recording(
            lambda: self._inner.get_damage_reduction_roll(rolled, kept, reduction)
        )
        inner_info = self._inner.last_damage_info() if hasattr(self._inner, "last_damage_info") else None
        dice = inner_info["dice"] if inner_info and inner_info.get("dice") else recorded
        self._last_damage_info = {"rolled": rolled, "kept": kept, "dice": sorted(dice, reverse=True)}
        result_int: int = result
        return result_int

    def get_wound_check_roll(self, rolled: int, kept: int, explode: bool = True) -> int:
        result, recorded = self._with_recording(
            lambda: self._inner.get_wound_check_roll(rolled, kept, explode=explode)
        )
        inner_info = self._inner.last_wound_check_info() if hasattr(self._inner, "last_wound_check_info") else None
        dice = inner_info["dice"] if inner_info and inner_info.get("dice") else recorded
        self._last_wound_check_info = {"rolled": rolled, "kept": kept, "dice": sorted(dice, reverse=True)}
        result_int: int = result
        return result_int

    def get_initiative_roll(self, rolled: int, kept: int) -> list[int]:
        result, recorded = self._with_recording_initiative(
            lambda: self._inner.get_initiative_roll(rolled, kept)
        )
        # Prefer recorded dice (most reliable), fall back to inner's stored info
        all_dice = recorded
        if not all_dice:
            inner_info = self._inner.last_initiative_info() if hasattr(self._inner, "last_initiative_info") else None
            if inner_info and inner_info.get("all_dice"):
                all_dice = inner_info["all_dice"]
        self._last_initiative_info = {"rolled": rolled, "kept": kept, "all_dice": sorted(all_dice)}
        result_list: list[int] = result
        return result_list

    def _with_recording_initiative(self, fn: Any) -> tuple[Any, list[int]]:
        """Call fn() with recording for initiative rolls.

        Handles KakitaRollProvider's hardcoded KAKITA_INITIATIVE_DIE_PROVIDER
        by temporarily replacing it at the module level with a recorder.
        For non-Kakita providers, falls back to the standard _with_recording.
        """
        import simulation.schools.kakita_school as kakita_mod
        from simulation.schools.kakita_school import KakitaRollProvider

        if not isinstance(self._inner, KakitaRollProvider):
            return self._with_recording(fn)

        # Wrap the module-level KAKITA_INITIATIVE_DIE_PROVIDER so that even
        # old cached KakitaRollProvider code (which hardcodes this constant)
        # has its dice intercepted.
        original_kakita_dp = kakita_mod.KAKITA_INITIATIVE_DIE_PROVIDER
        recorder = _RecordingDieProvider(original_kakita_dp)
        kakita_mod.KAKITA_INITIATIVE_DIE_PROVIDER = recorder  # type: ignore[assignment]
        try:
            result = fn()
        finally:
            kakita_mod.KAKITA_INITIATIVE_DIE_PROVIDER = original_kakita_dp
        return result, list(recorder.recorded)

    def last_skill_info(self) -> Any:
        return self._last_skill_info

    def last_damage_info(self) -> Any:
        return self._last_damage_info

    def last_wound_check_info(self) -> Any:
        return self._last_wound_check_info

    def last_initiative_info(self) -> Any:
        return self._last_initiative_info

    def __getattr__(self, name: str) -> Any:
        """Delegate any other attribute access to the inner provider."""
        return getattr(self._inner, name)


class CombatObserver:
    """Observes combat events and annotates them with dice data and character snapshots."""

    def __init__(self) -> None:
        self._first_phase_of_round = True
        # Per Constitution Principle VII: track recent wound-check
        # declarations so the wound-check annotator can attribute the
        # modifier to the VP spent. The engine yields a
        # ``WoundCheckDeclaredEvent`` (carrying ``vp``) immediately
        # before each ``WoundCheckRolledEvent``; we cache the most
        # recent declaration per subject name to bridge that gap
        # without modifying the engine.
        self._pending_wound_check_vp: dict[str, int] = {}
        # Per spec FR-002 / FR-007: the ``LightWoundsDamageEvent`` does
        # NOT carry the attack action that produced it, but the damage
        # breakdown needs the attack's ``attack_extra_rolled`` (margin
        # extras), ``vp`` (VP-on-attack inflation, e.g. Bayushi), AND
        # the originating action object (so spec 009's
        # ``action.damage_breakdown()`` can be consulted by
        # ``_annotate_damage`` — actions that override
        # ``damage_roll_params()`` like ``BayushiFeintAction`` produce
        # different component attributions than the provider's default).
        # ``AttackRolledEvent`` carries the action; we cache the most
        # recent attack per attacker name so the matching
        # ``LightWoundsDamageEvent`` annotation can recover the inputs
        # without re-walking history.
        self._pending_damage_context: dict[str, tuple[int, int, Any]] = {}
        # 2026-05-30 fix: ``SpendActionEvent`` is processed BEFORE the
        # subsequent ``TakeAttackActionEvent`` and mutates the
        # character's ``actions()`` list. If we snapshot status on the
        # TakeAttackActionEvent (as before), the status block displayed
        # immediately before the attack shows the POST-spend actions
        # list — making it look like the character is attacking with
        # no actions remaining.  Stash a pre-spend snapshot here so
        # ``_annotate_take_attack`` can use it.
        self._pre_spend_status_snapshot: dict[str, Any] | None = None

    def on_event(self, event: Any, context: Any) -> None:
        if isinstance(event, events.NewRoundEvent):
            self._first_phase_of_round = True
        elif isinstance(event, events.WoundCheckDeclaredEvent):
            self._pending_wound_check_vp[event.subject.name()] = event.vp
        elif isinstance(event, events.NewPhaseEvent):
            self._annotate_phase(event, context)
        elif isinstance(event, events.SpendActionEvent):
            # Capture status BEFORE the engine spends the die so the
            # TakeAttackActionEvent annotation can show the actions
            # list as it stood at the moment the attack was declared.
            self._pre_spend_status_snapshot = self._status_snapshot(context)
        elif isinstance(event, TakeCounterattackActionEvent):
            self._annotate_take_attack(event, context)
        elif isinstance(event, events.TakeAttackActionEvent):
            self._annotate_take_attack(event, context)
        elif isinstance(event, CounterattackRolledEvent):
            self._annotate_counterattack_rolled(event)
        elif isinstance(event, events.AttackRolledEvent):
            self._annotate_attack_rolled(event)
        elif isinstance(event, events.AttackSucceededEvent):
            self._annotate_attack_succeeded(event)
        elif isinstance(event, events.AttackFailedEvent):
            self._annotate_attack_failed(event)
        elif isinstance(event, events.ParryRolledEvent):
            self._annotate_parry_rolled(event)
        elif isinstance(event, events.LightWoundsDamageEvent):
            self._annotate_damage(event)
        elif isinstance(event, events.WoundCheckRolledEvent):
            self._annotate_wound_check(event)
        elif isinstance(event, ContestedIaijutsuAttackRolledEvent):
            self._annotate_contested_iaijutsu_rolled(event)
        elif isinstance(event, events.KeepLightWoundsEvent):
            self._annotate_keep_lw(event)
        elif isinstance(event, events.TakeSeriousWoundEvent):
            self._annotate_take_sw(event)
        elif isinstance(event, DuelStrikeRolledEvent):
            self._annotate_duel_strike_rolled(event)
        elif isinstance(event, ShowMeYourStanceRolledEvent):
            self._annotate_stance_rolled(event)
        elif isinstance(event, DuelInitiativeRolledEvent):
            self._annotate_duel_initiative(event, context)

    def _status_snapshot(self, context: Any) -> dict[str, Any]:
        """Capture a dict of character status keyed by name."""
        status = {}
        for char in context.characters():
            status[char.name()] = {
                "lw": char.lw(),
                "sw": char.sw(),
                "max_sw": char.max_sw(),
                "vp": char.vp(),
                "max_vp": char.max_vp(),
                "actions": list(char.actions()),
                "crippled": char.crippled(),
            }
        return status

    def _annotate_phase(self, event: Any, context: Any) -> None:
        # Status snapshot on every phase (formatter decides when to display)
        event._detail_status = self._status_snapshot(context)

        # Initiative data only on first phase of round
        if self._first_phase_of_round:
            self._first_phase_of_round = False
            initiative = {}
            for char in context.characters():
                provider = char.roll_provider()
                info = provider.last_initiative_info() if hasattr(provider, "last_initiative_info") else None
                if info is not None:
                    initiative[char.name()] = {
                        "all_dice": info["all_dice"],
                        "actions": list(char.actions()),
                        "roll_params": (info["rolled"], info["kept"]),
                    }
            if initiative:
                event._detail_initiative = initiative

    def _annotate_take_attack(self, event: Any, context: Any) -> None:
        """Annotate attack action with pre-action status snapshot.

        Uses the snapshot captured on the immediately preceding
        ``SpendActionEvent`` when available (so the actions list shows
        the die that's about to be spent rather than the post-spend
        state). Falls back to a live snapshot if no spend was observed
        — e.g. for cost-free actions that don't yield SpendActionEvent.
        """
        if self._pre_spend_status_snapshot is not None:
            event._detail_status = self._pre_spend_status_snapshot
            self._pre_spend_status_snapshot = None
        else:
            event._detail_status = self._status_snapshot(context)

    def _annotate_attack_rolled(self, event: Any) -> None:
        subject = event.action.subject()
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_params = self._adjust_params_for_ishi_boost(
            event.action.skill_roll_params(), event.action,
        )
        # Per rules/04-schools.md "Hida Bushi School: Special Ability":
        # a 1-die interrupt counterattack grants the attacker a free
        # raise (+5) on their attack roll.  The engine adds the bonus
        # directly into ``set_skill_roll`` (events.py::_roll_attack),
        # so ``skill_roll_params()`` returns the pre-bonus modifier.
        # Fold the bonus into the modifier slot here so the trace's
        # ``total = kept_sum + modifier`` arithmetic accounts for it,
        # and ``explain_modifier`` will attribute it to a source label.
        event._detail_params = self._adjust_params_for_counterattack_bonus(
            event._detail_params, event.action,
        )
        event._detail_tn = event.action.tn()
        event._detail_base_tn = event.action.target().tn_to_hit()
        event._detail_modifier_breakdown = self._build_modifier_breakdown(
            subject, event.action.skill(), event._detail_params,
            event.action.vp(), action=event.action,
        )
        # Per FR-001 / FR-006: attach the per-source ``_detail_components``
        # breakdown for the attack roll's XkY so the formatter can render
        # the multi-source decomposition (e.g.,
        # ``10k10 = 5k5 Fire ring + 5k0 double attack skill +
        # 1k0 Bayushi 1st Dan + 2k2 VP on double attack +
        # -3k3 from dice in excess of 10k10``).
        event._detail_components = self._skill_breakdown(
            subject, event.action.target(), event.action.skill(),
            event._detail_params, event.action.vp(),
        )

    def _annotate_counterattack_rolled(self, event: Any) -> None:
        subject = event.action.subject()
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_params = self._adjust_params_for_ishi_boost(
            event.action.skill_roll_params(), event.action,
        )
        event._detail_tn = event.action.tn()
        event._detail_modifier_breakdown = self._build_modifier_breakdown(
            subject, event.action.skill(), event._detail_params,
            event.action.vp(), action=event.action,
        )
        event._detail_components = self._skill_breakdown(
            subject, event.action.target(), event.action.skill(),
            event._detail_params, event.action.vp(),
        )

    def _annotate_parry_rolled(self, event: Any) -> None:
        subject = event.action.subject()
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_params = self._adjust_params_for_ishi_boost(
            event.action.skill_roll_params(), event.action,
        )
        event._detail_tn = event.action.tn()
        event._detail_modifier_breakdown = self._build_modifier_breakdown(
            subject, event.action.skill(), event._detail_params,
            event.action.vp(), action=event.action,
        )
        event._detail_components = self._skill_breakdown(
            subject, event.action.target(), event.action.skill(),
            event._detail_params, event.action.vp(),
        )

    @staticmethod
    def _adjust_params_for_ishi_boost(params: Any, action: Any) -> Any:
        """Augment the (rolled, kept, modifier) tuple with an Isawa Ishi
        3rd Dan ally boost when the action has been tagged with
        ``_ishi_boost_value``.

        The boost is rolled separately by the Ishi (not part of the
        rolling character's ``skill_roll_params``), but the trace's
        modifier safety check requires breakdown sources to sum to the
        rendered modifier (Constitution Principle VII). So we fold the
        boost value into the modifier slot here; the matching breakdown
        contribution is then attached by ``explain_modifier`` with the
        action passed in.

        rules/04-schools.md "Isawa Ishi School: 3rd Dan".
        """
        if not params or len(params) < 3:
            return params
        boost_value = getattr(action, "_ishi_boost_value", None)
        if not isinstance(boost_value, int) or boost_value <= 0:
            return params
        adjusted = (params[0], params[1], params[2] + boost_value)
        return adjusted

    @staticmethod
    def _adjust_params_for_counterattack_bonus(
        params: Any, action: Any,
    ) -> Any:
        """Augment the (rolled, kept, modifier) tuple with the Hida
        Bushi School special-ability free raise: when an attack action
        carries ``_counterattack_roll_bonus`` (set by
        ``HidaTakeCounterattackActionEvent`` on a 1-die interrupt
        counterattack), the attacker gets that bonus added to the
        attack roll.

        The engine adds the bonus directly into the rolled value (see
        ``events.py::_roll_attack``), so ``skill_roll_params()``
        returns the pre-bonus modifier.  Fold the bonus into the
        modifier slot here so the trace's ``total = kept_sum + mod``
        arithmetic stays consistent with the engine's hit
        determination, and ``explain_modifier`` will then attribute
        the contribution to "Hida special ability free raise" per
        Principle VII.

        rules/04-schools.md "Hida Bushi School: Special Ability".
        """
        if not params or len(params) < 3:  # pragma: no cover  # defensive: ``skill_roll_params()`` always returns a 3-tuple
            return params
        bonus = getattr(action, "_counterattack_roll_bonus", 0)
        if not isinstance(bonus, int) or bonus <= 0:
            return params
        adjusted = (params[0], params[1], params[2] + bonus)
        return adjusted

    @staticmethod
    def _build_modifier_breakdown(
        subject: Any, skill: str, params: Any, vp: int, action: Any = None,
    ) -> list[tuple[str, int]]:
        """Compute the source-attribution breakdown for a skill roll's modifier.

        Returns an empty list when the modifier is zero (no need to
        attribute zero) or when ``explain_modifier`` does not recognise
        any school-specific source. The formatter applies a secondary
        safety check (must sum to the modifier) before rendering, so
        any mismatch produces silent suppression of the attribution.
        """
        if not params or len(params) < 3:
            return []
        modifier = params[2]
        if modifier == 0:
            return []
        return explain_modifier(subject, skill, modifier, vp=vp, action=action)

    def _annotate_contested_iaijutsu_rolled(self, event: Any) -> None:
        subject = event.action.subject()
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_params = event.action.skill_roll_params()

    def _annotate_attack_succeeded(self, event: Any) -> None:
        action = event.action
        event._detail_extra_dice = action.calculate_extra_damage_dice()
        event._detail_damage_params = action.damage_roll_params()
        event._detail_skill_roll = action.skill_roll()
        event._detail_tn = action.tn()
        # Stash the actually-applied ``attack_extra_rolled`` and ``vp``
        # for the matching ``LightWoundsDamageEvent`` so its breakdown
        # mirrors the engine's damage-roll inputs (FR-002 / FR-009).
        # ``AttackSucceededEvent`` runs after parry resolution but
        # before the damage roll, so ``calculate_extra_damage_dice()``
        # returns the post-parry value the engine will pass to
        # ``get_damage_roll_params``.
        self._pending_damage_context[action.subject().name()] = (
            action.calculate_extra_damage_dice(), action.vp(), action,
        )

    def _annotate_attack_failed(self, event: Any) -> None:
        action = event.action
        event._detail_skill_roll = action.skill_roll()
        event._detail_tn = action.tn()

    def _annotate_keep_lw(self, event: Any) -> None:
        event._detail_lw_total = event.subject.lw()

    def _annotate_take_sw(self, event: Any) -> None:
        event._detail_lw_total = event.subject.lw()

    def _annotate_damage(self, event: Any) -> None:
        attacker = event.subject
        provider = attacker.roll_provider()
        info = provider.last_damage_info() if hasattr(provider, "last_damage_info") else None
        if info:
            event._detail_dice = info["dice"]
            event._detail_params = (info["rolled"], info["kept"])
        else:
            event._detail_dice = []
            event._detail_params = (0, 0)
        event._detail_lw_after = event.target.lw() + event.damage
        # Per FR-002 / FR-009: attach the per-source ``_detail_components``
        # breakdown so the formatter can render the multi-source damage
        # XkY decomposition (e.g.,
        # ``10k7 = 4k2 katana + 5k0 Fire ring + 2k0 margin + 2k2 VP on attack``).
        # The inputs (``attack_extra_rolled``, ``vp``) come from the
        # matching attack action stashed by ``_annotate_attack_succeeded``
        # (which runs AFTER parry resolution but BEFORE the damage roll —
        # the correct vantage to capture the values the engine will use).
        # If missing (e.g., cross-school direct-damage paths), fall back
        # to zero.
        extra_dice, vp, action = self._pending_damage_context.pop(
            attacker.name(), (0, 0, None),
        )
        # Spec 009: when we have the originating action, ask it for the
        # breakdown — this routes through any subclass override (e.g.,
        # BayushiFeintAction.damage_breakdown returns "attack skill" +
        # "base feint kept die" instead of the default katana + ring
        # the provider would attribute).  Fall back to the provider-
        # based breakdown when no action is available (e.g., direct-
        # damage paths that bypass the attack-action flow).
        if action is not None and hasattr(action, "damage_breakdown"):
            try:
                components = action.damage_breakdown()
            except Exception:  # pragma: no cover  # defensive: subclass override raises -> fall back to provider
                components = self._damage_breakdown(
                    attacker, event.target, "damage", extra_dice, vp,
                )
        else:
            components = self._damage_breakdown(
                attacker, event.target, "damage", extra_dice, vp,
            )
        # Reconcile the breakdown against the actually-rolled aggregate.
        # ``last_damage_info`` may carry stale state when the damage
        # path is a feint or other non-rolling action (the engine still
        # emits a ``LightWoundsDamageEvent`` with ``damage=0`` even
        # though no new roll happened). In that case the breakdown
        # would not sum to the displayed XkY; reconciling against the
        # captured ``(rolled, kept)`` preserves the
        # ``sum(components) == aggregate`` invariant from data-model.md.
        components = _reconcile_breakdown(components, event._detail_params)
        event._detail_components = components

    @staticmethod
    def _damage_breakdown(
        character: Any, target: Any, skill: str,
        attack_extra_rolled: int, vp: int,
    ) -> list[tuple[str, int, int]]:
        """Query the character's roll-parameter provider for the damage
        breakdown. Falls back to an empty list when the provider does
        not implement ``get_breakdown`` (legacy providers) — the
        formatter then renders the aggregate without the inline
        breakdown, preserving backward compatibility.

        Per FR-003 / data-model.md "Per-school breakdown contribution":
        per-school overrides (e.g. ``BayushiRollParameterProvider``)
        contribute their own breakdown via ``get_breakdown``.
        """
        provider = character.roll_parameter_provider()
        if not hasattr(provider, "get_breakdown"):
            return []
        try:
            result = provider.get_breakdown(
                character, target, skill,
                kind="damage",
                attack_extra_rolled=attack_extra_rolled,
                vp=vp,
            )
        except Exception:
            return []
        # Defensive: ensure shape.
        if not isinstance(result, list):
            return []
        return result

    @staticmethod
    def _skill_breakdown(
        character: Any, target: Any, skill: str,
        params: Any, vp: int,
    ) -> list[tuple[str, int, int]]:
        """Query the character's roll-parameter provider for the
        attack-skill breakdown. Returns an empty list when the provider
        does not implement ``get_breakdown(..., kind="attack")``
        (legacy providers) — the formatter then renders the aggregate
        without the inline breakdown, preserving backward compatibility.

        The returned breakdown is reconciled against the actual
        (rolled, kept) tuple captured on the event so it always sums
        to the aggregate displayed in the trace, per data-model.md
        invariants I1 / I2 / FR-001.

        Per FR-003: per-school overrides (e.g.
        ``MirumotoRollParameterProvider``) contribute their own
        breakdown via ``get_breakdown``.
        """
        provider = character.roll_parameter_provider()
        if not hasattr(provider, "get_breakdown"):
            return []
        try:
            raw = provider.get_breakdown(
                character, target, skill,
                kind="attack",
                vp=vp,
            )
        except Exception:
            return []
        if not isinstance(raw, list):
            return []
        result: list[tuple[str, int, int]] = list(raw)
        # Reconcile against the event's actual ``(rolled, kept)`` tuple.
        # The provider's ``get_breakdown`` already calls
        # ``_normalize_breakdown`` against ``get_skill_roll_params``;
        # however the event's ``_detail_params`` may have been adjusted
        # (e.g., Ishi 3rd Dan boost folded into the modifier slot — see
        # ``_adjust_params_for_ishi_boost``). Re-reconciling here
        # preserves ``sum(components) == aggregate`` for the rendered
        # XkY.
        if params and len(params) >= 2:
            result = _reconcile_breakdown(result, (params[0], params[1]))
        return result

    def _annotate_wound_check(self, event: Any) -> None:
        # Per Constitution Principle VII: capture the modifier so the
        # formatter can render it. The modifier is derived as
        # ``event.roll - sum(dice[:kept])`` -- the wound-check roll
        # provider returns ``kept_sum`` (no modifier), so any gap
        # between that sum and ``event.roll`` is attributable to a
        # modifier injected upstream (e.g., the Mirumoto 5th Dan
        # ``+10 per VP`` -- rules/04-schools.md Mirumoto Bushi School
        # Fifth Dan).
        subject = event.subject
        provider = subject.roll_provider()
        info = provider.last_wound_check_info() if hasattr(provider, "last_wound_check_info") else None
        if info:
            event._detail_dice = info["dice"]
            rolled = info["rolled"]
            kept = info["kept"]
            dice = info["dice"]
            kept_sum = sum(dice[:kept]) if dice else event.roll
            modifier = event.roll - kept_sum
            event._detail_params = (rolled, kept, modifier)
        else:
            event._detail_dice = []
            event._detail_params = (0, 0, 0)
        # Source attribution: pull the VP from the most recent
        # ``WoundCheckDeclaredEvent`` for this subject (the engine
        # always emits the declaration immediately before the
        # rolled event; we cached it on receipt).
        subject_name = subject.name()
        vp = self._pending_wound_check_vp.pop(subject_name, 0)
        # Per rules/04-schools.md "Isawa Ishi School: 3rd Dan": the boost
        # for a wound-check roll is tagged on the event itself (wound
        # check events have no action). Fold the boost value into the
        # modifier slot so the formatter's safety check (Principle VII)
        # accepts the matching breakdown contribution.
        boost_value = getattr(event, "_ishi_boost_value", None)
        if isinstance(boost_value, int) and boost_value > 0:
            r, k, m = event._detail_params
            event._detail_params = (r, k, m + boost_value)
        modifier = event._detail_params[2]
        if modifier != 0:
            event._detail_modifier_breakdown = explain_modifier(
                subject, "wound check", modifier, vp=vp, action=event,
            )
        else:
            event._detail_modifier_breakdown = []

    def _annotate_duel_strike_rolled(self, event: Any) -> None:
        subject = event.subject
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_roll_params = info if info else None

    def _annotate_stance_rolled(self, event: Any) -> None:
        subject = event.subject
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_roll_params = info if info else None

    def _annotate_duel_initiative(self, event: Any, context: Any) -> None:
        event._detail_status = self._status_snapshot(context)


class DetailedCombatEngine(CombatEngine):
    """CombatEngine subclass that calls an observer before processing each event."""

    def __init__(self, context: Any, observer: Any) -> None:
        super().__init__(context)
        self._observer = observer

    def event(self, event: Any) -> None:
        self._observer.on_event(event, self.context())
        super().event(event)


class DetailedDuelEngine(DetailedCombatEngine):
    """DetailedCombatEngine subclass that uses run_duel() instead of run()."""
    pass
