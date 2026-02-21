"""CombatObserver, TrackingRollProvider, and DetailedCombatEngine for rich combat output."""

from simulation import events
from simulation.engine import CombatEngine
from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER, DieProvider
from simulation.mechanics.roll_provider import RollProvider
from simulation.schools.kakita_school import ContestedIaijutsuAttackRolledEvent


class _RecordingDieProvider(DieProvider):
    """Wraps a DieProvider and records each top-level die result."""

    def __init__(self, inner):
        self._inner = inner
        self.recorded = []

    def roll_die(self, faces=10, explode=True):
        result = self._inner.roll_die(faces, explode)
        self.recorded.append(result)
        return result


class TrackingRollProvider(RollProvider):
    """Wrapper that delegates all rolls to an inner provider and captures dice data.

    Uses a recording die provider to intercept dice at the source, so dice
    are captured regardless of whether the inner Roll objects store them.
    """

    def __init__(self, inner):
        self._inner = inner
        self._last_skill_info = None
        self._last_damage_info = None
        self._last_wound_check_info = None
        self._last_initiative_info = None

    def die_provider(self):
        return self._inner.die_provider()

    def set_die_provider(self, die_provider):
        self._inner.set_die_provider(die_provider)

    def _with_recording(self, fn):
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

    def get_skill_roll(self, skill, rolled, kept, explode=True):
        result, recorded = self._with_recording(
            lambda: self._inner.get_skill_roll(skill, rolled, kept, explode)
        )
        # Prefer inner's stored dice (handles WaveManRoll transformations),
        # fall back to recorded raw dice
        inner_info = self._inner.last_skill_info() if hasattr(self._inner, "last_skill_info") else None
        dice = inner_info["dice"] if inner_info and inner_info.get("dice") else recorded
        self._last_skill_info = {"rolled": rolled, "kept": kept, "dice": sorted(dice, reverse=True)}
        return result

    def get_damage_roll(self, rolled, kept):
        result, recorded = self._with_recording(
            lambda: self._inner.get_damage_roll(rolled, kept)
        )
        inner_info = self._inner.last_damage_info() if hasattr(self._inner, "last_damage_info") else None
        dice = inner_info["dice"] if inner_info and inner_info.get("dice") else recorded
        self._last_damage_info = {"rolled": rolled, "kept": kept, "dice": sorted(dice, reverse=True)}
        return result

    def get_wound_check_roll(self, rolled, kept):
        result, recorded = self._with_recording(
            lambda: self._inner.get_wound_check_roll(rolled, kept)
        )
        inner_info = self._inner.last_wound_check_info() if hasattr(self._inner, "last_wound_check_info") else None
        dice = inner_info["dice"] if inner_info and inner_info.get("dice") else recorded
        self._last_wound_check_info = {"rolled": rolled, "kept": kept, "dice": sorted(dice, reverse=True)}
        return result

    def get_initiative_roll(self, rolled, kept):
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
        return result

    def _with_recording_initiative(self, fn):
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
        kakita_mod.KAKITA_INITIATIVE_DIE_PROVIDER = recorder
        try:
            result = fn()
        finally:
            kakita_mod.KAKITA_INITIATIVE_DIE_PROVIDER = original_kakita_dp
        return result, list(recorder.recorded)

    def last_skill_info(self):
        return self._last_skill_info

    def last_damage_info(self):
        return self._last_damage_info

    def last_wound_check_info(self):
        return self._last_wound_check_info

    def last_initiative_info(self):
        return self._last_initiative_info

    def __getattr__(self, name):
        """Delegate any other attribute access to the inner provider."""
        return getattr(self._inner, name)


class CombatObserver:
    """Observes combat events and annotates them with dice data and character snapshots."""

    def __init__(self):
        self._first_phase_of_round = True

    def on_event(self, event, context):
        if isinstance(event, events.NewRoundEvent):
            self._first_phase_of_round = True
        elif isinstance(event, events.NewPhaseEvent):
            self._annotate_phase(event, context)
        elif isinstance(event, events.TakeAttackActionEvent):
            self._annotate_take_attack(event, context)
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

    def _status_snapshot(self, context):
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

    def _annotate_phase(self, event, context):
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

    def _annotate_take_attack(self, event, context):
        """Annotate attack action with pre-action status snapshot."""
        event._detail_status = self._status_snapshot(context)

    def _annotate_attack_rolled(self, event):
        subject = event.action.subject()
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_params = event.action.skill_roll_params()
        event._detail_tn = event.action.target().tn_to_hit()

    def _annotate_parry_rolled(self, event):
        subject = event.action.subject()
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_params = event.action.skill_roll_params()
        event._detail_tn = event.action.tn()

    def _annotate_contested_iaijutsu_rolled(self, event):
        subject = event.action.subject()
        provider = subject.roll_provider()
        info = provider.last_skill_info() if hasattr(provider, "last_skill_info") else None
        event._detail_dice = info["dice"] if info else []
        event._detail_params = event.action.skill_roll_params()

    def _annotate_attack_succeeded(self, event):
        action = event.action
        event._detail_extra_dice = action.calculate_extra_damage_dice()
        event._detail_damage_params = action.damage_roll_params()
        event._detail_skill_roll = action.skill_roll()
        event._detail_tn = action.tn()

    def _annotate_attack_failed(self, event):
        action = event.action
        event._detail_skill_roll = action.skill_roll()
        event._detail_tn = action.tn()

    def _annotate_keep_lw(self, event):
        event._detail_lw_total = event.subject.lw()

    def _annotate_take_sw(self, event):
        event._detail_lw_total = event.subject.lw()

    def _annotate_damage(self, event):
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

    def _annotate_wound_check(self, event):
        subject = event.subject
        provider = subject.roll_provider()
        info = provider.last_wound_check_info() if hasattr(provider, "last_wound_check_info") else None
        if info:
            event._detail_dice = info["dice"]
            event._detail_params = (info["rolled"], info["kept"])
        else:
            event._detail_dice = []
            event._detail_params = (0, 0)


class DetailedCombatEngine(CombatEngine):
    """CombatEngine subclass that calls an observer before processing each event."""

    def __init__(self, context, observer):
        super().__init__(context)
        self._observer = observer

    def event(self, event):
        self._observer.on_event(event, self.context())
        super().event(event)
