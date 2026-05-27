# Data Model: Structured Trace Refactor

## Shared types

```python
@dataclass(frozen=True)
class ComponentDelta:
    """One contribution to a multi-source dice aggregate.

    Used by attack/parry/counterattack/iaijutsu/WC roll entries (in
    `roll_components`) and damage entries (in `damage_components`).
    """
    source: str                   # e.g., "Fire ring", "Akodo 1st Dan"
    rolled: int                   # +rolled contribution
    kept: int                     # +kept contribution


@dataclass(frozen=True)
class ModifierDelta:
    """One contribution to a +N modifier on a roll."""
    source: str                   # e.g., "Akodo 2nd Dan free raise"
    amount: int                   # +N contribution
```

## TraceEntry hierarchy

All entries are `@dataclass(frozen=True)` with a `kind: Literal["..."]` discriminator. The concrete types:

```python
@dataclass(frozen=True)
class RoundHeaderEntry:
    kind: Literal["round_header"] = "round_header"
    round_number: int

@dataclass(frozen=True)
class PhaseHeaderEntry:
    kind: Literal["phase_header"] = "phase_header"
    phase: int

@dataclass(frozen=True)
class StatusBlockEntry:
    kind: Literal["status_block"] = "status_block"
    statuses: list[dict[str, Any]]    # per-character status snapshot

@dataclass(frozen=True)
class InitiativeEntry:
    kind: Literal["initiative"] = "initiative"
    character_name: str
    rolled: int
    kept: int
    dice: list[int]
    actions: list[int]
    components: list[ComponentDelta]   # ring etc.

@dataclass(frozen=True)
class AttackEntry:
    kind: Literal["attack"] = "attack"
    actor_name: str
    target_name: str
    skill: str
    vp_spent: int | None              # for the "spends N VP on attack" prefix
    vp_skill: str | None              # the skill the VP is spent on (usually == skill)
    rolled: int
    kept: int
    components: list[ComponentDelta]  # ring + skill + school + VP contributions
    dice: list[int]
    sum_of_kept: int
    modifier: int
    modifier_components: list[ModifierDelta]
    tn: int
    base_tn: int
    raise_count: int                  # (tn - base_tn) // 5
    outcome: Literal["hit", "miss"]
    extra_damage_dice: int            # extra rolled dice on damage from margin
    margin_over_tn: int               # numerical margin
    damage_projection: DamageProjection | None  # the inline "damage will be" sub-entry

@dataclass(frozen=True)
class DamageProjection:
    """Inline 'damage will be XkY' projection on an attack line."""
    rolled: int
    kept: int
    components: list[ComponentDelta]
    extra_damage_dice: int
    margin_over_tn: int

@dataclass(frozen=True)
class CounterattackEntry: ...
    # Same shape as AttackEntry but kind = "counterattack" and no damage projection
    # (counterattacks resolve immediately into LW damage).

@dataclass(frozen=True)
class ParryEntry: ...
    # Same shape but kind = "parry", no damage projection, outcome can be "parried"/"failed"

@dataclass(frozen=True)
class IaijutsuEntry: ...
    # Same shape but kind = "iaijutsu"

@dataclass(frozen=True)
class WoundCheckEntry:
    kind: Literal["wound_check"] = "wound_check"
    character_name: str
    vp_spent: int | None              # VP-prefix from 4th-Dan etc.
    vp_source: str | None             # the source label for the VP spend (e.g., "Akodo 4th Dan")
    rolled: int
    kept: int
    components: list[ComponentDelta]
    dice: list[int]
    sum_of_kept: int
    modifier: int
    modifier_components: list[ModifierDelta]
    damage: int                       # TN of the WC = incoming damage
    outcome: Literal["passed", "failed"]
    keep_lw: bool | None              # True if PASSED and chose to keep LW

@dataclass(frozen=True)
class LightWoundsDamageEntry:
    kind: Literal["lw_damage"] = "lw_damage"
    attacker_name: str
    target_name: str
    rolled: int
    kept: int
    components: list[ComponentDelta]
    dice: list[int]
    damage: int
    target_total_lw: int

@dataclass(frozen=True)
class SeriousWoundsDamageEntry: ...
@dataclass(frozen=True)
class KeepLightWoundsEntry: ...
@dataclass(frozen=True)
class TakeSeriousWoundEntry: ...

@dataclass(frozen=True)
class SpendVpEntry:
    kind: Literal["spend_vp"] = "spend_vp"
    character_name: str
    skill: str                        # the skill the VP is spent on
    amount: int
    source: str | None                # e.g., "Akodo 4th Dan"
    # Note: when emitted standalone. When the spend is composed into an attack
    # or wound check entry, the spend doesn't get its own entry.

@dataclass(frozen=True)
class GainTvpEntry:
    kind: Literal["gain_tvp"] = "gain_tvp"
    character_name: str
    amount: int
    source: str | None

@dataclass(frozen=True)
class GainFloatingBonusEntry:
    kind: Literal["gain_floating_bonus"] = "gain_floating_bonus"
    character_name: str
    amount: int
    source: str | None
    breakdown: str | None             # e.g., "margin 18 ÷ 5 × attack 5"

@dataclass(frozen=True)
class SpendFloatingBonusEntry:
    kind: Literal["spend_floating_bonus"] = "spend_floating_bonus"
    character_name: str
    amount: int
    source: str | None

@dataclass(frozen=True)
class SchoolNegatedEntry:
    kind: Literal["school_negated"] = "school_negated"
    by_name: str
    target_name: str
    vp_cost: int

@dataclass(frozen=True)
class AkodoFifthDanCounterEntry:
    kind: Literal["akodo_5th_dan_counter"] = "akodo_5th_dan_counter"
    akodo_name: str
    attacker_name: str
    vp_spent: int
    damage: int
```

## Composition rules (per research.md)

The `entries()` method on `DetailedEventFormatter` walks the history and applies these compositions before emitting entries:

| Engine event sequence | Resulting TraceEntry |
|-----------------------|----------------------|
| SpendVoidPointsEvent(skill="attack") → TakeAttackActionEvent → AttackRolledEvent | One `AttackEntry` with `vp_spent` populated |
| TakeAttackActionEvent → AttackRolledEvent (no VP) | One `AttackEntry` with `vp_spent=None` |
| TakeParryActionEvent → ParryRolledEvent | One `ParryEntry` |
| TakeCounterattackActionEvent → CounterattackRolledEvent | One `CounterattackEntry` |
| SpendVoidPointsEvent(source="Akodo 5th Dan", skill="damage") → LightWoundsDamageEvent(source="Akodo 5th Dan") | One `AkodoFifthDanCounterEntry` |
| SpendVoidPointsEvent(skill="wound check", source="Akodo 4th Dan") → WoundCheckRolledEvent | One `WoundCheckEntry` with `vp_spent`+`vp_source` populated |
| GainFloatingBonusEvent | One `GainFloatingBonusEntry` |
| SpendFloatingBonusEvent | One `SpendFloatingBonusEntry` |
| etc. (one entry per emit) | (per-event entry) |

## Invariants

- **I1**: Every event in a representative combat's history produces at least one TraceEntry (no silent drops). Verified by FR-007 + FR-032.
- **I2**: TextRenderer's output equals the pre-refactor `format_history()` byte-for-byte. Verified by US2.
- **I3**: BulletedRenderer's output for any entry never depends on the engine's event objects directly — only on the entry's fields. (Verified by static inspection / mypy: BulletedRenderer never imports from `simulation/`.)
- **I4**: `simulation/` imports zero from `web/adapters/trace_entries.py` and zero from any renderer module. Verified by FR-031 / SC-008.
- **I5**: Round-trip property: `TextRenderer().render_lines(formatter.entries(history)) == formatter.format_history(history)` for every supported event type. Verified by FR-030.
