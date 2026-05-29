# Open Questions & Pre-Resolutions — Shinjo Bushi School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify`; logged here for end-of-run review.

The skeleton at `simulation/schools/shinjo_school.py` (152 lines, 13 passing tests) has **multiple BLOCKING rules-fidelity defects** including a dead identity ability.

## Pre-resolutions

### Q1: 1st Dan — wrong skill list — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "Roll one extra die on **initiative, parry, and wound checks**." Skeleton returns `["double attack", "initiative", "parry"]`. Replace with `["initiative", "parry", "wound check"]`.

**Why**: Direct rules-text contradiction. `double attack` is a knack, not a 1st-Dan boost. `wound check` is missing entirely.

### Q2: 4th Dan — double roll_initiative — BLOCKING

**Pre-resolution**: **Fix.** `ShinjoNewRoundListener.handle` calls `character.roll_initiative()` then mutates the actions list. But the engine's default `NewRoundListener` already rolls initiative on `NewRoundEvent`. Calling it a second time produces an incorrect roll.

**Why**: Engine flow already rolls initiative; the school listener should ONLY mutate the result, not re-roll.

**Fix**: Remove the `character.roll_initiative()` call; the listener should only set the highest die to 1 on the already-populated actions list. Listener ordering: ensure this runs AFTER the engine's NewRoundListener.

### Q3: 5th Dan listener duplicates 3rd Dan logic — MINOR

**Pre-resolution**: **Refactor.** `ShinjoFifthDanParryListener` inline-duplicates the 3rd Dan action-die decrease. Replace with a delegation or helper.

### Q4: Special Ability — bonus never consumed — BLOCKING IDENTITY

**Pre-resolution**: **Fix.** `ShinjoSpendActionListener` computes `2 * hold_phases` and stores on `character._shinjo_hold_bonus` — but nothing in the codebase reads this attribute. The +2X-per-phase-held bonus is the entire identity of the school and is structurally dead.

**Fix path**: Wire the bonus into the action's skill roll via a `Modifier` (transient, expires after the action) or via the `roll_parameter_provider` for the next skill roll. Need to apply to ALL action types (attack, double attack, lunge, iaijutsu, counterattack, feint), not just attack.

**Cleanest approach**: Set a `_shinjo_hold_bonus` attribute on the character that the `roll_parameter_provider` (or modifier system) reads when computing the NEXT skill roll. Clear after the roll consumes it.

Alternative: emit a temporary `Modifier(character, None, "<skill>", bonus)` with `ExpireAfterNextAttackByCharacterListener` so it gets cleaned up.

### Q5: Hold-phases math — BLOCKING

**Pre-resolution**: **Fix.** `hold_phases = current_phase - initiative_action.phase()`. For a held die (dice=[3], phase=8), this gives `current_phase - 8 = 0` instead of the actual hold of `current_phase - 3` (or `phase - 3 = 5`). Use `min(initiative_action.dice())` for the original die value.

### Q6: `SHINJO_PRIORITIES` revision

**Pre-resolution**: **Defer** like Bayushi/Kakita/Otaku/Shiba. Same parry-at-every-rank pattern — actually parry IS identity-aligned for Shinjo (2nd Dan free raise + 3rd Dan parry-tempo-engine + 5th Dan parry-margin-to-WC) so parry-at-every-rank is OK. But `double attack` / `iaijutsu` / `lunge` at every rank may be over-investment when `attack` is the 3rd-Dan multiplier.

### Q7: Trace observability gaps

**Pre-resolution**: Fix the most impactful via attribution tags + renderer paths. Priority:
- **Special Ability hold bonus** — once Q4 is wired, the +2X bonus on every "held" action needs trace surfacing.
- **3rd Dan action-die decrease** — currently silent mutation of action dice.
- **4th Dan highest-die-to-1** — currently silent mutation in NewRoundListener.

## To be answered during implementation

### Q8: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

### Q9: school-strategy-designer's bindings — accepted verbatim?

**Status**: Run during plan dispatch.

### Q10: school-progression-designer's revision — accepted verbatim?

**Status**: Run during plan dispatch (likely deferred per Q6).

## Audit confirmations (post-Phase 2)

### CONFIRMED BLOCKING

- **Q1**: `extra_rolled` returns `["double attack", "initiative", "parry"]` instead of rules-text `["initiative", "parry", "wound check"]`.
- **Q4**: `_shinjo_hold_bonus` is written but never read by anything in `simulation/` or `web/`. Special Ability is structurally dead. Combat-simulator confirmed empirically: 0/10 win rate vs Akodo at 450, 0/13 round-robin wins.

### NEW BLOCKING bug surfaced by combat-simulator

**4th Dan "highest die to 1" fails on TIES.** `ShinjoNewRoundListener` uses `actions.index(max(actions))` which returns only the FIRST occurrence. For `[2,3,5,5]` → only one 5 becomes 1 → `[1,2,3,5]` (other 5 survives). Rules intent: ALL dice tied at the max value should be reduced to 1 (or some explicit tie-break per rules text — pre-resolve: reduce ALL tied max dice since "the highest action die" reads ambiguously and reducing all matches "set highest to 1" spirit).

### REFUTED

- **Q2**: NOT a double-roll. `_set_school_listener` REPLACES the slot — engine's default `NewRoundListener` doesn't fire; Shinjo's is the only one. The internal `roll_initiative()` call is correct (the listener owns the new-round flow).
- **Q5**: hold-phases math IS correct. `InitiativeAction.phase()` returns the original die value for non-interrupt actions (engine constructs them with `InitiativeAction([die], die)`). The skeleton's `current_phase - initiative_action.phase()` is right.

### Q3 — 5th Dan inlining

Confirmed necessary (not redundant). `_set_school_listener` replaces the slot, so 5th Dan's `parry_succeeded` handler takes over from 3rd Dan's. Inlining the 3rd Dan logic is the only way to preserve it. Refactor by subclassing.

### Strategy bindings (school-strategy-designer)

- **Action slot**: `HoldOneActionStrategy` — Special Ability rewards holding dice.
- **Parry slot**: `AlwaysParryStrategy` (post 1st Dan) — parry triggers 3rd Dan tempo-decrease + 5th Dan margin-bonus.
- **Wound check slot**: `WoundCheckStrategy04` — 1st Dan +1 WC die (post Q1 fix) + 5th Dan margin-bonus = above-average WC pool.
- **Q4 fix approach**: use `Modifier(character, None, ATTACK_SKILLS, +2X)` with `ExpireAfterNextAttackByCharacterListener` (Daidoji precedent), not roll_parameter_provider. The modifier shows up in skill-roll modifier breakdown naturally.

### Progression-designer

`SHINJO_PRIORITIES` revision proposed (parry-first / attack-second / air-3 at Dan 3 / earth removed). **DEFER** per Bayushi/Kakita/Otaku/Shiba pattern.

## Deviations log (append during implementation)

(empty — to be populated batch-by-batch)
