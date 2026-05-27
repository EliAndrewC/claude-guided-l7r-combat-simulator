# Phase 0 Research: Structured Trace Refactor

## Current formatter inventory (per `grep "def _format_" web/adapters/detailed_formatter.py`)

28 `_format_*` methods in `DetailedEventFormatter`. Each maps to a `TraceEntry` type. The mapping is:

| Formatter method | Source event type | Proposed `TraceEntry` |
|------------------|-------------------|----------------------|
| `_format_status_block` | (state snapshot, not an event) | `StatusBlockEntry` |
| `_format_initiative` | `InitiativeRolledEvent` | `InitiativeEntry` |
| `_format_take_attack` | `TakeAttackActionEvent` | merged into `AttackEntry` |
| `_format_take_counterattack` | `TakeCounterattackActionEvent` | merged into `CounterattackEntry` |
| `_format_take_parry` | `TakeParryActionEvent` | merged into `ParryEntry` |
| `_format_attack_rolled` | `AttackRolledEvent` | `AttackEntry` (or part of `AttackEntry` if combined with take_attack) |
| `_format_counterattack_rolled` | `CounterattackRolledEvent` | `CounterattackEntry` |
| `_format_contested_iaijutsu_rolled` | `ContestedIaijutsuRolledEvent` | `IaijutsuEntry` |
| `_format_parry_rolled` | `ParryRolledEvent` | `ParryEntry` |
| `_format_lw_damage` | `LightWoundsDamageEvent` | `LightWoundsDamageEntry` |
| `_format_sw_damage` | `SeriousWoundsDamageEvent` | `SeriousWoundsDamageEntry` |
| `_format_wound_check_rolled` | `WoundCheckRolledEvent` | `WoundCheckEntry` |
| `_format_modifier_breakdown` | (helper for embedded modifier rendering) | not an entry — used by renderers |
| `_format_spend_vp` | `SpendVoidPointsEvent` | `SpendVpEntry` (or merged into the action entry) |
| `_format_gain_tvp` | `GainTemporaryVoidPointsEvent` | `GainTvpEntry` |
| `_format_gain_floating_bonus` | `GainFloatingBonusEvent` | `GainFloatingBonusEntry` |
| `_format_spend_floating_bonus` | `SpendFloatingBonusEvent` | `SpendFloatingBonusEntry` |
| `_format_school_negated` | `SchoolNegatedEvent` | `SchoolNegatedEntry` |
| `_format_keep_lw` | `KeepLightWoundsEvent` | `KeepLightWoundsEntry` |
| `_format_take_sw` | `TakeSeriousWoundEvent` | `TakeSeriousWoundEntry` |
| `_format_akodo_5th_dan_counter` | combined SpendVoidPointsEvent + LightWoundsDamageEvent for the Akodo 5th Dan combined render | `AkodoFifthDanCounterEntry` |
| `_format_tn` | (helper for embedded TN rendering) | not an entry — fields go into the action entry |
| `_format_combined_attack` | composed (TakeAttack + AttackRolled) | `AttackEntry` (composite) |
| `_format_combined_counterattack` | composed (TakeCounterattack + CounterattackRolled) | `CounterattackEntry` (composite) |
| `_format_dice` | (helper) | not an entry |
| `_build_vp_infix` | (helper for VP-prefix on roll lines) | not an entry — fields go into the action entry |
| Round header (string emit in `format_history`) | (synthetic from round boundary) | `RoundHeaderEntry` |
| Phase header (string emit in `format_history`) | (synthetic from phase boundary) | `PhaseHeaderEntry` |

## Composition rules from `format_history`

The existing `format_history` does these compositions:

1. **TakeAttackAction + AttackRolledEvent → one trace line via `_format_combined_attack`** — the take_attack adds the "⚔️ attacks X" prefix; the attack_rolled adds the dice + TN + outcome. The combined entry is `AttackEntry`.
2. **SpendVoidPointsEvent immediately followed by TakeAttackAction → VP prefix on the combined attack line** — the spend VP becomes a `vp_spent` field on the `AttackEntry` rather than a separate `SpendVpEntry`.
3. **Akodo 5th Dan: SpendVoidPointsEvent(source="Akodo 5th Dan", skill="damage") followed by LightWoundsDamageEvent(source="Akodo 5th Dan") → one combined line** — captured as `AkodoFifthDanCounterEntry`.
4. **Wound-check VP prefix**: SpendVoidPointsEvent(skill="wound check") immediately before a WoundCheckRolledEvent → VP fields on the `WoundCheckEntry`.

These compositions live in `format_history`'s walking loop. The new `entries()` method replicates them.

## Strategy for byte-identical text output

The TextRenderer must produce IDENTICAL bytes to the current formatter. To guarantee this:

1. Each `_format_*` method becomes a `TextRenderer._render_<type>(entry: SomeEntry) -> list[str]` method. The migration is mechanical: replace `event.attribute` with `entry.attribute`.
2. The new `entries()` method on `DetailedEventFormatter` is built first (Phase 3), then the TextRenderer is migrated (Phase 4), then `format_history` becomes a thin wrapper.
3. Round-trip tests (FR-030) verify byte-identical output per event type.

## What CAN'T be byte-identical (the migration backstop)

Per OPEN_QUESTIONS Q[g]: if the text output diverges cosmetically (e.g., a missing space, a more-consistent bullet character), document the diff and flag for user review. Substantive changes (different content) require manual approval.

## Per-school provider impact

None. The refactor lives entirely in `web/adapters/`. Per-school RollParameterProviders (e.g., `BayushiRollParameterProvider`) already produce structured breakdown via `get_breakdown()`; the new `entries()` method consumes this via the existing `_detail_components` annotation.

## Existing tests that might break

About 50+ tests across `tests/test_*_school.py`, `tests/test_trace_observability.py`, `tests/test_coverage_audit_*.py`, etc., assert against specific trace strings via `assertIn` or full equality. The refactor's byte-identical invariant means they should all pass. The risk is small-but-possible cosmetic drift (e.g., a `_build_vp_infix` corner case that doesn't survive the migration).

Mitigation: write the round-trip tests (FR-030) FIRST so any divergence is caught immediately by the most specific test, before the broader test suite runs.
