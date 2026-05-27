# Phase 0 Research: Combat Trace Observability Audit

## Trace-auditor dry-run findings (cached)

The trace-auditor agent's dry-run (2026-05-27) on a 300-XP 5th-Dan Akodo vs 300-XP 5th-Dan Bayushi combat at `random.seed(1234)` produced this gap list:

| Gap | Severity | Where | Symptom |
|-----|----------|-------|---------|
| 1 | P1 | `web/adapters/detailed_formatter.py:417, 576, 1055` + `web/adapters/combat_observer.py:367` (annotator) + `simulation/mechanics/roll_params.py:115` (source) | Damage XkY expression rendered with NO breakdown of weapon base / ring / margin extras / VP-on-attack inflation / school-specific extras |
| 2 | P1 | `web/adapters/detailed_formatter.py:417, 1055` + `simulation/mechanics/roll_params.py:132` (source) | Attack XkY expression rendered with NO breakdown of ring + skill + school extras + VP-on-attack effect + floating bonuses |
| 3 | P1 | `web/adapters/modifier_breakdown.py::explain_modifier` (catalog gap) + `web/adapters/detailed_formatter.py:649` (silent suppression) | Bare `+5` modifier on attack with NO source label. Formatter's safety clause silently suppresses parenthetical when breakdown components don't sum to the modifier. |
| 4 | P1 | `web/adapters/detailed_formatter.py:1015` (`_format_tn`) | TN inflation from raises (`base TN 30 → TN 50`) not broken down. Reader sees the delta but not the `+20 from 4 raises for double attack` derivation. |
| 5 | P1 | `web/adapters/combat_observer.py:367` (`_annotate_damage`) + `web/adapters/detailed_formatter.py` (damage rendering) | VP-on-attack's effect on damage roll is invisible. Spend appears in trace at attack time, but the downstream damage line doesn't show that VP inflated its dice. |

Plus several P2/P3 recommendations:
- **P2**: "extra damage dice" count shown but not the `floor(margin/5)` derivation (`(+12 over TN, 2 extra damage dice)` — should be `2 extra damage dice (margin 12 ÷ 5)`).
- **P3**: Non-Akodo floating-bonus consumption shows the amount without a source label (gain event was untagged in those cases).
- **P3**: Akodo 5th Dan counter-damage shows `10 LW × N VP` arithmetic but doesn't cite the underlying rule.
- **P2**: Wound check modifier breakdown is inconsistent across lines.

## Pattern precedent from spec 004 (Akodo trace work)

Spec 004 established the `source` kwarg pattern on engine events (`GainTemporaryVoidPointsEvent`, `SpendVoidPointsEvent`, `LightWoundsDamageEvent`, `FloatingBonus` and subclasses). It also introduced the `_format_gain_tvp`, `_format_gain_floating_bonus`, `_format_spend_floating_bonus`, `_format_akodo_5th_dan_counter` formatter cases — the precedent this audit extends.

What worked:
- Optional `source` kwargs (backward-compatible).
- Per-formatter-case rendering with source labels.
- Tests asserting against the user-visible trace string (via `format_history`).

What changed mid-run (and why this audit revisits it):
- The `source` kwarg pattern handles per-event attribution but doesn't address multi-component aggregates within a single event (e.g., the attack roll itself).
- Spec 004's tests asserted on partial trace strings (e.g., `assertIn("Akodo Special Ability", trace)`), which remain valid post-audit. Full-line equality tests (if any) get updated.

## Current state of the observer pipeline

Per `web/adapters/combat_observer.py` (inspected during the dry-run):

- `CombatObserver` (no-arg constructor) attaches via `DetailedCombatEngine` (NOT plain `CombatEngine`).
- `_annotate_attack` already stashes `(rolled, kept)` totals. It does NOT currently stash per-source contributions.
- `_annotate_damage` (line ~367) similarly stashes `(rolled, kept)` totals only.
- The observer has access to the character, the action, the event, and the context at annotation time — all the data needed to compute the breakdown.

## Current state of the formatter

Per `web/adapters/detailed_formatter.py` (1026 lines, inspected during the dry-run):

- `_format_attack_rolled` (~line 417): renders the attack roll XkY + modifier + TN. Currently renders bare XkY.
- `_format_combined_attack` (~line 1055): combined-attack-line variant. Same gap.
- `_format_lw_damage` (~line 576): renders the final damage event. Same gap.
- `_format_modifier_breakdown` (~line 649): the silent-suppression safety clause. Replace with `(unsourced: +K)` placeholder.
- `_format_tn` (~line 1015): renders TN. Add raise-count attribution.
- `_build_vp_infix` (~line 216 area): renders VP-spend pre-line. Already supports source attribution for "Akodo 4th Dan" pattern; extend for other school sources as needed.

## Per-school override audit (preview)

Per a quick survey of `simulation/schools/*.py`:

- **Bayushi**: `bayushi_school.py:61` has a damage-related override (per the dry-run finding mentioning Bayushi as a potential bare-+5 source).
- **Akodo**: No roll-param overrides for damage (the school's extra dice come via `extra_rolled` which the default provider already handles).
- **Mirumoto**: parry-focused; may have parry-roll-param overrides.
- **Ishi**: VP-related overrides via the IshiMaxVPProvider (affects VP availability, not the breakdown of roll components directly).

Each school's contribution to the breakdown comes through `extra_rolled()` (the standard school accessor) — the default provider already incorporates this. The breakdown computation thus needs to either: (a) call back into `school.extra_rolled(skill)` to label school extras, OR (b) have schools tag their contributions via a new `breakdown_components()` accessor.

**Decision**: use option (a) for simplicity. The default provider can compute the breakdown from existing accessors (`character.school_ring()`, `character.skill(...)`, `character.school().extra_rolled(...)`, `character.weapon().rolled()`, etc.). No per-school provider changes needed unless a school has a non-standard contribution that doesn't go through `extra_rolled`.

## DefaultRollParameterProvider return-shape options

Currently returns `(rolled, kept)` tuples. Options for exposing breakdown:

**Option A**: Return `(rolled, kept, breakdown)` 3-tuple. Backward-compat-breaking for any caller that unpacks the 2-tuple.

**Option B**: Add a new method `get_breakdown(...)` returning a list of `(source, +rolled, +kept)` tuples. Backward-compat. The observer queries both methods.

**Option C**: Return the existing 2-tuple but attach the breakdown as an attribute on a returned dataclass. More refactor work.

**Decision**: Option B — backward-compat, easy to roll out, easy to test. The observer queries `get_breakdown` ONLY when annotating events (not in the hot path of dice rolling).

## Existing test churn estimate

Surveying the test files:
- `tests/test_akodo_school.py`: 35+ tests. Many assert on `assertIn(...)` of partial trace strings — should not break. A few assert on specific trace lines that include XkY expressions — those might need updates.
- `tests/test_mirumoto_school.py`, `tests/test_ishi_school.py`: similar shape.
- Trace integration tests in other files: review during implementation.

Estimated test updates: ≤ 10. Below the OPEN_QUESTIONS Q8 threshold of 20 (which would trigger user verification).

## Conclusion

The audit is achievable with the planned approach:
1. `CombatObserver` gains `_detail_components` annotation, computed via a new `DefaultRollParameterProvider.get_breakdown` method that walks the existing accessors.
2. Formatter renders the breakdown inline.
3. `_format_modifier_breakdown` replaces silent suppression with `(unsourced: +K)`.
4. `explain_modifier` audit catalogs missing cases (bare-+5 from Bayushi is the known one).
5. `_format_tn` extends with raise attribution.
6. Cross-roll-effect attribution requires the damage breakdown to include VP-on-attack as a contributing source.
