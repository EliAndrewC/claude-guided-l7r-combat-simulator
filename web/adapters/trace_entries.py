"""Structured TraceEntry intermediate representation for combat trace output.

This module defines the discriminated-union of dataclasses that sit between
observer-annotated engine events and rendered output. ``DetailedEventFormatter.entries()``
walks the event history and emits these structured entries; ``TextRenderer``
(and future ``BulletedRenderer``, ``JsonRenderer``, ...) consume the same
entries to produce per-view output.

Per Constitution Principle II (engine purity), this module MUST NOT import
from ``simulation/``. All fields are plain values (str/int/list/dict) so the
entries are self-contained snapshots.

Per spec 007 (Structured Trace Refactor) data-model.md, every entry is
``@dataclass(frozen=True)`` with a ``kind: Literal["..."]`` discriminator.
"""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ComponentDelta:
    """One contribution to a multi-source dice aggregate.

    Used by attack/parry/counterattack/iaijutsu/WC roll entries (in
    ``roll_components``) and damage entries (in ``damage_components``).
    """

    source: str
    rolled: int
    kept: int


@dataclass(frozen=True)
class ModifierDelta:
    """One contribution to a +N modifier on a roll."""

    source: str
    amount: int


@dataclass(frozen=True)
class RoundHeaderEntry:
    """Round-boundary header line (``═══ Round N ═══``)."""

    round_number: int
    kind: Literal["round_header"] = "round_header"


@dataclass(frozen=True)
class PhaseHeaderEntry:
    """Phase-boundary header (embedded into action-line prefix in text form)."""

    phase: int
    kind: Literal["phase_header"] = "phase_header"


@dataclass(frozen=True)
class StatusBlockEntry:
    """Multi-line per-character status snapshot."""

    statuses: dict[str, dict[str, Any]]
    kind: Literal["status_block"] = "status_block"


@dataclass(frozen=True)
class InitiativeEntry:
    """Round-opening initiative roll block (one line per character)."""

    entries: list[dict[str, Any]]
    kind: Literal["initiative"] = "initiative"


@dataclass(frozen=True)
class DamageProjection:
    """Inline 'damage will be XkY' projection on an attack line."""

    rolled: int
    kept: int
    components: list[ComponentDelta]
    extra_damage_dice: int
    margin_over_tn: int


@dataclass(frozen=True)
class AttackEntry:
    """Composite attack-action + attack-roll entry.

    Composes ``TakeAttackActionEvent`` and ``AttackRolledEvent`` (plus any
    immediately-preceding ``SpendVoidPointsEvent``) into one entry per the
    composition rules in data-model.md.

    ``is_combined`` distinguishes the legacy ``_format_combined_attack``
    path (``⚔️ attacks Target ...``) from the standalone
    ``_format_attack_rolled`` path (``🎯 Attack: ...`` or ``❌ Attack: ...``).
    """

    phase_prefix: str
    actor_name: str
    target_name: str
    skill: str
    vp_spent: int | None
    vp_skill: str | None
    rolled: int
    kept: int
    modifier: int
    components: list[ComponentDelta]
    modifier_components: list[ModifierDelta]
    dice: list[int]
    sum_of_kept: int
    total: int
    tn: int
    base_tn: int
    outcome: Literal["hit", "miss"]
    damage_projection: DamageProjection | None
    has_detail: bool = True
    fallback_roll: int = 0
    is_combined: bool = True
    is_take_only: bool = False
    kind: Literal["attack"] = "attack"


@dataclass(frozen=True)
class CounterattackEntry:
    """Composite counterattack-action + counterattack-roll entry."""

    phase_prefix: str
    actor_name: str
    target_name: str
    vp_spent: int | None
    vp_skill: str | None
    rolled: int
    kept: int
    modifier: int
    components: list[ComponentDelta]
    modifier_components: list[ModifierDelta]
    dice: list[int]
    sum_of_kept: int
    total: int
    tn: int
    outcome: Literal["hit", "miss"]
    damage_projection: DamageProjection | None
    has_detail: bool = True
    fallback_roll: int = 0
    is_combined: bool = True
    is_take_only: bool = False
    kind: Literal["counterattack"] = "counterattack"


@dataclass(frozen=True)
class ParryEntry:
    """Composite parry-action + parry-roll entry."""

    phase_prefix: str
    actor_name: str
    target_name: str
    rolled: int
    kept: int
    modifier: int
    components: list[ComponentDelta]
    modifier_components: list[ModifierDelta]
    dice: list[int]
    sum_of_kept: int
    total: int
    tn: int
    outcome: Literal["succeeded", "failed"]
    has_detail: bool = True
    fallback_roll: int = 0
    is_combined: bool = True
    is_take_only: bool = False
    kind: Literal["parry"] = "parry"


@dataclass(frozen=True)
class IaijutsuEntry:
    """ContestedIaijutsuAttackRolledEvent — challenger vs defender roll."""

    phase_prefix: str
    actor_name: str
    is_challenger: bool
    skill: str
    skill_roll: int
    opponent_skill_roll: int
    extra_damage_dice: int
    rolled: int
    kept: int
    dice: list[int]
    sum_of_kept: int
    effective_modifier: int
    has_detail: bool = True
    kind: Literal["iaijutsu"] = "iaijutsu"


@dataclass(frozen=True)
class LightWoundsDamageEntry:
    """LightWoundsDamageEvent — damage roll + total LW tally."""

    phase_prefix: str
    attacker_name: str
    target_name: str
    rolled: int
    kept: int
    components: list[ComponentDelta]
    dice: list[int]
    sum_of_kept: int
    damage: int
    lw_after: int | None
    has_detail: bool = True
    kind: Literal["lw_damage"] = "lw_damage"


@dataclass(frozen=True)
class SeriousWoundsDamageEntry:
    """SeriousWoundsDamageEvent — N serious wounds dealt."""

    phase_prefix: str
    target_name: str
    damage: int
    from_double_attack: bool
    kind: Literal["sw_damage"] = "sw_damage"


@dataclass(frozen=True)
class WoundCheckEntry:
    """WoundCheckRolledEvent (possibly composed with VP-spend + TakeSW/KeepLW)."""

    phase_prefix: str
    character_name: str
    vp_spent: int | None
    vp_source: str | None
    vp_skill: str | None
    vp_breakdown: str | None  # rendered prefix when source-attributed
    rolled: int
    kept: int
    modifier: int
    components: list[ComponentDelta]
    modifier_components: list[ModifierDelta]
    dice: list[int]
    sum_of_kept: int
    total: int
    tn: int
    outcome: Literal["passed", "failed"]
    has_detail: bool = True
    fallback_roll: int = 0
    # Composition: when followed by TakeSW or KeepLW, render the result inline.
    follow_up: Literal["take_sw", "keep_lw", "none"] = "none"
    follow_up_sw_count: int = 0
    follow_up_lw_total: int = 0
    follow_up_voluntary: bool = False
    kind: Literal["wound_check"] = "wound_check"


@dataclass(frozen=True)
class KeepLightWoundsEntry:
    """Standalone KeepLightWoundsEvent (when not composed into a WC entry)."""

    phase_prefix: str
    character_name: str
    lw_total: int
    kind: Literal["keep_lw"] = "keep_lw"


@dataclass(frozen=True)
class TakeSeriousWoundEntry:
    """Standalone TakeSeriousWoundEvent (when not composed into a WC entry)."""

    phase_prefix: str
    character_name: str
    voluntary: bool
    kind: Literal["take_sw"] = "take_sw"


@dataclass(frozen=True)
class SpendVpEntry:
    """Standalone SpendVoidPointsEvent (when not composed)."""

    phase_prefix: str
    character_name: str
    amount: int
    skill: str
    kind: Literal["spend_vp"] = "spend_vp"


@dataclass(frozen=True)
class GainTvpEntry:
    """GainTemporaryVoidPointsEvent."""

    phase_prefix: str
    character_name: str
    amount: int
    source: str | None
    kind: Literal["gain_tvp"] = "gain_tvp"


@dataclass(frozen=True)
class GainFloatingBonusEntry:
    """GainFloatingBonusEvent."""

    phase_prefix: str
    character_name: str
    amount: int
    source: str | None
    breakdown: str | None
    kind: Literal["gain_floating_bonus"] = "gain_floating_bonus"


@dataclass(frozen=True)
class SpendFloatingBonusEntry:
    """SpendFloatingBonusEvent."""

    phase_prefix: str
    character_name: str
    amount: int
    source: str | None
    kind: Literal["spend_floating_bonus"] = "spend_floating_bonus"


@dataclass(frozen=True)
class SchoolNegatedEntry:
    """SchoolNegatedEvent (Isawa Ishi 5th Dan)."""

    phase_prefix: str
    negator_name: str
    target_name: str
    target_school_name: str
    vp_cost: int
    kind: Literal["school_negated"] = "school_negated"


@dataclass(frozen=True)
class AkodoFifthDanCounterEntry:
    """Combined Akodo 5th Dan spend-VP-on-damage + LW counter-damage."""

    phase_prefix: str
    akodo_name: str
    vp_spent: int
    damage: int
    target_name: str
    kind: Literal["akodo_5th_dan_counter"] = "akodo_5th_dan_counter"


@dataclass(frozen=True)
class IaijutsuDuelHeaderEntry:
    """IaijutsuDuelEvent — '═══ Iaijutsu Duel ═══' header."""

    kind: Literal["iaijutsu_duel_header"] = "iaijutsu_duel_header"


@dataclass(frozen=True)
class ShowMeYourStanceDeclaredEntry:
    """ShowMeYourStanceDeclaredEvent."""

    character_name: str
    kind: Literal["stance_declared"] = "stance_declared"


@dataclass(frozen=True)
class ShowMeYourStanceRolledEntry:
    """ShowMeYourStanceRolledEvent."""

    character_name: str
    roll: int
    discerned_fire: int
    discerned_tn: int
    rolled: int | None
    kept: int | None
    dice: list[int]
    kind: Literal["stance_rolled"] = "stance_rolled"


@dataclass(frozen=True)
class DuelInitiativeRolledEntry:
    """DuelInitiativeRolledEvent."""

    challenger_name: str
    defender_name: str
    challenger_roll: int
    defender_roll: int
    winner_name: str
    kind: Literal["duel_initiative"] = "duel_initiative"


@dataclass(frozen=True)
class IaijutsuFocusEntry:
    """IaijutsuFocusEvent."""

    character_name: str
    challenger_name: str
    defender_name: str
    challenger_tn: int
    defender_tn: int
    kind: Literal["iaijutsu_focus"] = "iaijutsu_focus"


@dataclass(frozen=True)
class IaijutsuStrikeEntry:
    """IaijutsuStrikeEvent (the strike-declaration, not the roll)."""

    character_name: str
    challenger_name: str
    defender_name: str
    challenger_tn: int
    defender_tn: int
    kind: Literal["iaijutsu_strike"] = "iaijutsu_strike"


@dataclass(frozen=True)
class DuelStrikeRolledEntry:
    """DuelStrikeRolledEvent."""

    character_name: str
    target_name: str
    roll: int
    tn: int
    is_hit: bool
    extra_damage_dice: int
    rolled: int | None
    kept: int | None
    dice: list[int]
    kind: Literal["duel_strike_rolled"] = "duel_strike_rolled"


@dataclass(frozen=True)
class DuelResheathEntry:
    """DuelResheathEvent."""

    higher_roller_name: str
    kind: Literal["duel_resheath"] = "duel_resheath"


@dataclass(frozen=True)
class DuelEndedEntry:
    """DuelEndedEvent."""

    kind: Literal["duel_ended"] = "duel_ended"


@dataclass(frozen=True)
class DeathEntry:
    """DeathEvent."""

    phase_prefix: str
    character_name: str
    kind: Literal["death"] = "death"


@dataclass(frozen=True)
class UnconsciousEntry:
    """UnconsciousEvent."""

    phase_prefix: str
    character_name: str
    kind: Literal["unconscious"] = "unconscious"


@dataclass(frozen=True)
class SurrenderEntry:
    """SurrenderEvent."""

    phase_prefix: str
    character_name: str
    kind: Literal["surrender"] = "surrender"


@dataclass(frozen=True)
class RawTextEntry:
    """Defensive fallback when an event type has no dedicated entry.

    In correct operation, ``DetailedEventFormatter.entries()`` should never
    emit this — every event has a real entry type. If a ``RawTextEntry``
    ever appears, it's a defect (spec 007 edge case).
    """

    lines: list[str] = field(default_factory=list)
    kind: Literal["raw_text"] = "raw_text"


# The discriminated union — every concrete TraceEntry kind.
TraceEntry = (
    RoundHeaderEntry
    | PhaseHeaderEntry
    | StatusBlockEntry
    | InitiativeEntry
    | AttackEntry
    | CounterattackEntry
    | ParryEntry
    | IaijutsuEntry
    | LightWoundsDamageEntry
    | SeriousWoundsDamageEntry
    | WoundCheckEntry
    | KeepLightWoundsEntry
    | TakeSeriousWoundEntry
    | SpendVpEntry
    | GainTvpEntry
    | GainFloatingBonusEntry
    | SpendFloatingBonusEntry
    | SchoolNegatedEntry
    | AkodoFifthDanCounterEntry
    | IaijutsuDuelHeaderEntry
    | ShowMeYourStanceDeclaredEntry
    | ShowMeYourStanceRolledEntry
    | DuelInitiativeRolledEntry
    | IaijutsuFocusEntry
    | IaijutsuStrikeEntry
    | DuelStrikeRolledEntry
    | DuelResheathEntry
    | DuelEndedEntry
    | DeathEntry
    | UnconsciousEntry
    | SurrenderEntry
    | RawTextEntry
)
