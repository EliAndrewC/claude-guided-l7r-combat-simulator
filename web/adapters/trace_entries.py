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

    Spec 008 fields:

    - ``suppress_damage_projection``: when ``True`` (set for feint
      attacks per FR-005), the renderer omits the
      ``"damage will be: XkY"`` segment from the line.
    - ``consumed_floating_bonuses``: when a ``SpendFloatingBonusEvent``
      immediately follows this attack's outcome events (same actor, same
      skill), the formatter absorbs the bonus(es) into this list and
      skips emitting a standalone ``SpendFloatingBonusEntry`` (FR-008/9/10).
      Renderers integrate these into the attack-line inline arithmetic.
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
    suppress_damage_projection: bool = False
    consumed_floating_bonuses: list[ModifierDelta] = field(default_factory=list)
    # rules/04-schools.md "Matsu Bushi School: Fourth Dan": a
    # ``MatsuDoubleAttackAction`` may hit on a skill_roll below TN (a
    # "near-miss" carve-out: tn - 20 <= roll < tn).  Renderers surface
    # the attribution "Matsu 4th Dan: near-miss (N below TN)" on the
    # attack line, where ``N`` is this field.  Default 0 = not a
    # near-miss (clean hit or non-Matsu double attack), no attribution
    # rendered.  Constitution Principle VII.
    matsu_4th_dan_near_miss_below_tn: int = 0
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
    # rules/04-schools.md "Otaku Bushi School: Fifth Dan" — the SW
    # event emitted by ``OtakuFifthDanTakeAttackActionEvent`` carries
    # ``_from_otaku_5th_dan = True``.  Surfaced in both renderers
    # (spec 014 T-C2) so the reader can attribute the otherwise-
    # unexplained extra SW to the 5th Dan dice-trade ability per
    # Principle VII.
    from_otaku_5th_dan: bool = False
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
    # rules/04-schools.md "Hida Bushi School: Fifth Dan": when the
    # Hida's WC fires on damage from a previously counterattacked
    # attack, the counterattack-excess margin (roll - TN) is added to
    # the WC roll.  Renderers surface this with explicit attribution
    # ("Hida 5th Dan: counterattack excess +X") on the WC line per
    # Constitution Principle VII.  Default 0 = no bonus applied.
    hida_5th_dan_excess_bonus: int = 0
    # rules/04-schools.md "Bayushi Bushi School: Fifth Dan": when a
    # Bayushi fails a WC, SW is computed against ``lw // 2`` instead
    # of ``lw``.  Renderers surface the halving with explicit
    # attribution ("Bayushi 5th Dan: SW computed against halved LW
    # (actual N -> halved M)") on the WC line per Constitution
    # Principle VII (trace-auditor + trace-reader fix 2026-05-28).
    # Default 0 = halving did not apply (the WC was not Bayushi 5th
    # Dan's path, or the WC passed and halving was a no-op).
    bayushi_5th_dan_halved_lw_actual: int = 0
    # 2026-05-30: LW value at the moment the WC was declared. When a
    # WC fails and the defender takes SW, the engine resets LW to 0
    # silently; surfacing the pre-WC value lets renderers append
    # ``(LW {N} → 0)`` to a failed WC line so the reader can see why
    # the next status block shows ``Light 0``.
    lw_before_check: int = 0
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
class KitsukiRingReductionEntry:
    """Kitsuki 5th Dan round-start ring debuff.

    Rendered as a single line surfacing the school identity ability
    so the reader can see WHICH opponent was chosen and WHAT the
    pre-reduction ring values were (so the post-reduction values in
    the next status block are reconcilable).
    """

    phase_prefix: str
    subject_name: str
    target_name: str
    ring_values_before: dict[str, int]
    kind: Literal["kitsuki_ring_reduction"] = "kitsuki_ring_reduction"


@dataclass(frozen=True)
class MerchantRerollEntry:
    """Merchant 5th Dan dice-reroll event.

    Rendered alongside the roll that prompted the reroll so the
    reader can see what changed: ``Merchant 5th Dan: reroll
    {before}→{after}, ... (on skill/wound check/damage roll)``.
    """

    phase_prefix: str
    subject_name: str
    roll_type: str
    rerolled_pairs: tuple[tuple[int, int], ...]
    kind: Literal["merchant_reroll"] = "merchant_reroll"


@dataclass(frozen=True)
class CounterDamageDealtEntry:
    """Discrete LW-applied event for Akodo 5th Dan counter-damage.

    Companion to :class:`AkodoFifthDanCounterEntry` — the counter
    entry shows the formula and the source; this entry mirrors the
    standard ``💥 takes N LW (total: K)`` pattern of normal damage
    so the reader can see the target's running LW total inline
    rather than having to infer it from the next wound check's TN.
    """

    phase_prefix: str
    subject_name: str
    damage: int
    lw_after: int
    kind: Literal["counter_damage_dealt"] = "counter_damage_dealt"


@dataclass(frozen=True)
class HidaThirdDanRerollEntry:
    """Hida 3rd Dan reroll annotation, emitted alongside an attack /
    counterattack entry whose action has a ``_hida_3rd_dan_reroll``
    annotation set by ``Action.roll_skill``.

    Constitution Principle VII: each rerolled die appears with its
    before-value and after-value, and the entry carries an explicit
    ``"Hida 3rd Dan"`` source label.

    rules/04-schools.md "Hida Bushi School: Third Dan".
    """

    phase_prefix: str
    actor_name: str
    skill: str
    n: int  # effective reroll cap after crippled halving
    crippled: bool
    rerolls: list[tuple[int, int]]  # list of (before, after) die values
    before_total: int
    after_total: int
    kind: Literal["hida_3rd_dan_reroll"] = "hida_3rd_dan_reroll"


@dataclass(frozen=True)
class MatsuLwFloorEntry:
    """Matsu 5th Dan LW-floor attribution -- when a Matsu's attack
    causes the defender's WC to fail, the defender's LW is set to 15
    instead of 0.

    Emitted alongside the resulting ``SeriousWoundsDamageEntry`` (the
    LW-floor itself happens in the listener; this entry surfaces the
    attribution).  Constitution Principle VII / FR-023.

    rules/04-schools.md "Matsu Bushi School: Fifth Dan".
    """

    phase_prefix: str
    defender_name: str
    lw_set_to: int = 15
    kind: Literal["matsu_lw_floor"] = "matsu_lw_floor"


@dataclass(frozen=True)
class HidaSWForLWTradeEntry:
    """Hida 4th Dan SW-for-LW trade — the alternative wound check
    that takes 2 SW to reset LW to 0.

    Emitted when a ``HidaSWForLWTradeEvent`` appears in the engine
    history.  The entry carries the explicit ``"Hida 4th Dan"`` source
    label, the LW value being reset (``lw_reset_from``), and the 2-SW
    cost (per rules text).

    Constitution Principle VII: the trade replaces the wound check
    entirely, so its rendering must clearly attribute the action to
    the Hida 4th Dan ability AND state the cost-to-benefit numerically
    (take 2 SW; reset LW from N to 0).

    rules/04-schools.md "Hida Bushi School: Fourth Dan".
    """

    phase_prefix: str
    character_name: str
    lw_reset_from: int
    sw_taken: int = 2
    kind: Literal["hida_sw_for_lw_trade"] = "hida_sw_for_lw_trade"


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
    | CounterDamageDealtEntry
    | KitsukiRingReductionEntry
    | MerchantRerollEntry
    | HidaThirdDanRerollEntry
    | HidaSWForLWTradeEntry
    | MatsuLwFloorEntry
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
