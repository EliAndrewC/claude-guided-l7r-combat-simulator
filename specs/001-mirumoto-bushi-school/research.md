# Phase 0 Research: Mirumoto Bushi School

This document resolves the three items the `/speckit-clarify` pass deferred to plan-time, plus an audit of the existing skeleton at `simulation/schools/mirumoto_school.py` that drives task decomposition.

## R1. "Wound check" string identifier

**Decision**: Use the literal string `"wound check"` (lowercase, space-separated) in `MirumotoBushiSchool.extra_rolled()`.

**Rationale**: `simulation/mechanics/roll_params.py` → `DefaultRollParameterProvider.get_wound_check_roll_params` calls `character.extra_rolled("wound check")`. The mechanism is purely string-keyed; any other string (e.g., `"wound_check"`, `"WoundCheck"`) silently no-ops. Other schools (e.g., Akodo, Hida) include `"wound check"` in their `extra_rolled()` list, confirming the convention.

**Alternatives considered**: Introducing an enum for skill names — rejected because it would touch every school. Out of scope for this feature.

## R2. Phase tie-breaker convention

**Decision**: No new tie-breaker. Phase-lowered actions use the existing engine convention.

**Rationale**: `simulation/context.py` → `EngineContext.reevaluate_initiative()` sorts characters by cached `initiative_priority`. When a Mirumoto's action is phase-lowered into a phase that already has another character's action, normal initiative ordering applies. This matches the spec's working assumption ("the existing engine tie-breaker applies; this school introduces no new tie-breaker") and avoids a school-specific carve-out in the combat loop.

**Alternatives considered**: Mirumoto acts first on phase-lowered actions (privileges aggressive parry timing). Rejected — no rules text supports it, and it would require touching the combat loop, violating Principle V's "no hardcoding into the combat loop."

## R3. Implementation directory layout

**Decision**: Extend the existing skeleton in `simulation/schools/mirumoto_school.py` and add one sibling module `simulation/strategies/mirumoto_third_dan.py` for the Third Dan spend-decision strategies.

**Rationale**:
- `simulation/schools/mirumoto_school.py` already exists with a partial implementation (see R4 below). Replacing it with a multi-file package would create migration noise without architectural benefit — every other implemented school is a single file under `simulation/schools/`.
- The Third Dan spend strategies are *decision components* per Principle V. They are tactical — when to phase-lower, when to spend +2 after seeing a roll — and playtesters need to swap them. Putting them in `simulation/strategies/` alongside the engine's other strategy classes makes them discoverable and swappable.

**Alternatives considered**: Put the Third Dan strategies inline in `mirumoto_school.py`. Rejected — couples decision logic to school definition, making it harder to A/B different spend policies (which is the whole point of the project).

## R4. Skeleton audit: `simulation/schools/mirumoto_school.py`

The existing file contains a partial implementation. This audit drives the task list. Each item is tagged **OK** (matches spec), **BUG** (diverges from spec/rules), or **GAP** (missing entirely).

### School class (`MirumotoBushiSchool`)

| Method | Status | Notes |
|---|---|---|
| `name()` returns `"Mirumoto Bushi School"` | **OK** | Matches factory registration in `simulation/schools/factory.py:75`. |
| `school_ring()` returns `"void"` | **OK** | Matches FR-002. |
| `school_knacks()` returns `["counterattack", "double attack", "iaijutsu"]` | **OK** | Matches FR-003 and the rules text. |
| `extra_rolled()` returns `["attack", "double attack", "parry"]` | **BUG** | Rules say "Roll one extra die on parry, double attack, and wound checks." Should return `["parry", "double attack", "wound check"]`. Skeleton has `"attack"` (not in rules) and is missing `"wound check"`. Fix is one-line. |
| `free_raise_skills()` returns `["parry"]` | **OK** | Matches FR-006 (2nd Dan free parry raise). |
| `ap_base_skill()` returns `None` | **OK** | Mirumoto does not use Adventure Points. |
| `apply_special_ability()` installs `MirumotoParryTVPListener` on `parry_succeeded` and `parry_failed`, sets `counterattack` interrupt cost = 1, sets interrupt strategy | **OK** | Matches FR-004 and FR-004a. (Counterattack interrupt support comes from school knacks — orthogonal to special ability but the engine entangles them.) |
| `apply_rank_one_ability()` | **OK (implicit)** | Inherits from `BaseSchool`; First Dan dice bonus flows through `extra_rolled()` (fixed in line above) — no override needed. |
| `apply_rank_two_ability()` | **OK (implicit)** | Inherits from `BaseSchool`; Free raise flows through `free_raise_skills()` — no override needed. |
| `apply_rank_three_ability()` registers `MirumotoNewRoundListener` | **OK as far as it goes** | Listener creates the pool, but no strategy machinery to spend it (see GAP-3 below). |
| `apply_rank_four_ability()` calls `apply_school_ring_raise_and_discount()` AND sets `MIRUMOTO_ACTION_FACTORY` | **PARTIAL** | The `apply_school_ring_raise_and_discount()` helper correctly handles FR-010 (Void +1) and FR-011 (-5 XP). The `MIRUMOTO_ACTION_FACTORY` swap installs `MirumotoParryAction`, which is **on the wrong side** (see BUG-2 below). |
| `apply_rank_five_ability()` installs `MIRUMOTO_ROLL_PARAMETER_PROVIDER` | **OK** | The provider adds +5 per VP on top of the standard +5, yielding the +10 per FR-014. Because it operates purely on the `vp` parameter passed into `get_*_roll_params`, it implicitly treats temporary VP and normal VP identically (matching FR-004a — no provenance tracking needed). |

### Supporting classes

| Class | Status | Notes |
|---|---|---|
| `MirumotoParryTVPListener` (special ability) | **OK** | Yields `GainTemporaryVoidPointsEvent(character, 1)` on `ParrySucceededEvent` or `ParryFailedEvent` where the parrying character is its owner. Engine's existing `_tvp` machinery handles the rest: temp VP stacks above the normal cap and is reset only at end-of-combat via `Character.reset()` (called from `EngineContext.reset()`, which is invoked from `Engine.reset()` between combat runs — *not* every round). Matches FR-004 and Clarification Q1. |
| `MirumotoNewRoundListener` (3rd Dan pool creation) | **OK as far as it goes** | On `NewRoundEvent`, sets `character._mirumoto_pool = 2 * character.skill("attack")`. Correctly handles attack-skill-0 (yields 0). **GAP**: no API for spending, no strategy to drive spends, no event hookups for the two spend modes. |
| `MirumotoParryAction(ParryAction)` (4th Dan) | **BUG (wrong side of combat)** | The skeleton subclasses `ParryAction` — i.e., what runs when the Mirumoto *is parrying*. It wraps the *incoming* attack's `calculate_extra_damage_dice` to halve the result. But FR-012/FR-013 modify what happens when *defenders* fail to parry *the Mirumoto's* attacks — i.e., the modification belongs on `DoubleAttackAction` and `AttackAction`, not on `ParryAction`. Net effect today: a 4th-dan Mirumoto's *own* failed parries against incoming attacks halve their extra damage dice, which is **the opposite of what the rule says** and breaks FR-012/FR-013. |
| `MirumotoActionFactory(DefaultActionFactory)` | **PARTIAL** | Currently overrides `get_parry_action` only. Will need to also override `get_attack_action` and `get_double_attack_action` (or whichever is the actual factory method for double attacks in `ActionFactory`) so a 4th-dan Mirumoto's *attacks* carry the FR-012/FR-013 modifications. |
| `MirumotoRollParameterProvider` (5th Dan) | **OK** | Adds +5 per VP to skill rolls and wound check rolls when `vp > 0`. Operates purely on the `vp` integer, so it's agnostic to temp/normal provenance. Matches FR-014 and FR-004a. |

### Existing test file (`tests/test_mirumoto_school.py`)

| Test | Status | Notes |
|---|---|---|
| `test_extra_rolled` | **BUG** (asserts the buggy list) | Currently asserts `["attack", "double attack", "parry"]`. Must be flipped to `["parry", "double attack", "wound check"]` *first* (RED), then the code fix in `extra_rolled()` makes it GREEN. |
| `test_school_ring`, `test_school_knacks`, `test_free_raise_skills` | **OK** | Asserting correct values. |
| `TestMirumotoParryTVPListener.test_gain_tvp_on_parry_succeeded` | **OK (presumed)** | Need to read the rest of the file to confirm coverage of `parry_failed` path as well. |

### Summary of work

- **BUG fixes**: 2 (`extra_rolled` list; `MirumotoParryAction` wrong-side fix → split into Mirumoto-attack-side modifications).
- **GAP fills**: 3 (Third Dan spend strategies + spend API; Fourth Dan auto-serious-wound clause on double attacks; comprehensive tests for all the above).
- **OK as-is**: school metadata, special ability TVP, school ring +1, Void XP discount, Fifth Dan +10.

## R5. Decision: where the 4th Dan attack-side modifications hook in

**Decision**: Subclass `DoubleAttackAction` (for the auto-SW clause and the per-FR-012 narrow scope of "only the auto-SW prevention is removed") and `AttackAction` (for FR-013's halving of damage-die reduction), and have `MirumotoActionFactory` return those subclasses instead of `MirumotoParryAction`.

**Rationale**: The rule modifies how *defenders* fail to parry the Mirumoto's attacks. The cleanest hook is the attack object itself (which already knows whether a parry was attempted and whether it succeeded — see `actions.AttackAction.parries_declared()`). A subclass that overrides `direct_damage()` (for double attacks, to bypass the `parry_attempted()` short-circuit on auto-SW) and `calculate_extra_damage_dice()` (for regular attacks, to halve the post-failed-parry reduction) is local, testable, and doesn't touch the combat loop.

**Alternatives considered**:
- Listener on `ParryFailedEvent` that mutates the attack post-hoc — rejected, harder to test and creates an event-ordering subtlety.
- Engine-loop branch — rejected, violates Principle II/V.

## R6. Decision: Third Dan pool storage and access pattern

**Decision**: Pool is a plain integer attribute `character._mirumoto_pool` set by the listener on `NewRoundEvent`. Access is through two thin helpers on the school (or a small accessor module) that read/decrement the attribute, raising on illegal spends (FR-008's "spend is illegal if the target action is already at phase 1").

**Rationale**: Matches the existing engine pattern for per-round resources (e.g., the Akodo TVP-tracking; the Monk action insertion). Adding a typed wrapper class (`ThirdDanPool`) was considered but rejected as ceremony — the data is a single nonneg integer and the operations are increment-on-round-start, decrement-on-spend, read-for-decisions. The wrapper would not add type safety mypy doesn't already give us.

**Pool reset semantics**: The listener overwrites `_mirumoto_pool` on every `NewRoundEvent`, which discards unspent points (FR-007). No separate "end of round, lose points" code path is needed.

## R7. Decision: Third Dan strategy interfaces

**Decision**: Two new strategy classes in `simulation/strategies/mirumoto_third_dan.py`, each implementing a small protocol:

1. `MirumotoPhaseLowerStrategy.decide(character, scheduled_actions, context) -> list[(action_idx, points_to_spend)]` — returns the spending plan for mode A.
2. `MirumotoPostRollBonusStrategy.decide(character, roll_result, roll_context) -> int` — returns the number of points to spend on the +2 bonus mode B for a roll that has already been resolved.

Both consult `character._mirumoto_pool` and never exceed it. The engine invokes them at the appropriate hook points (`NewPhaseEvent` for mode A — to decide before actions of that phase resolve; immediately after a roll for mode B — before the roll's total is consumed).

**Rationale**: Two distinct decision points → two distinct strategy interfaces. Principle V demands these be swappable; baking both into one strategy would couple decisions that are semantically independent.

**Alternatives considered**: A single `MirumotoThirdDanStrategy` with both methods on one object. Rejected — couples the two decisions and makes it harder to A/B one mode while holding the other fixed.

## R8. Decision: default strategies for first implementation

**Decision**: Ship narrow, conservative defaults that never burn pool points for no benefit (revised 2026-05-26 after first implementation review):

- `EagerPhaseLowerStrategy` (mode A): spend the minimum number of points to convert an action into a parry, but ONLY when (a) the character's parry strategy actually wants to parry this incoming attack, AND (b) the character has no action currently available at phase ≤ context.phase() to parry with, AND (c) lowering an available action via the pool would actually make one available. If any of these conditions fail, abstain. In particular: do NOT lower actions whose current phase is already ≤ context.phase() (already usable); do NOT spend if the parry strategy wouldn't have chosen to parry anyway.
- `MarginalBonusStrategy` (mode B): spend `ceil(margin / 2)` points to push a failing roll over the TN, but ONLY if the pool has at least that many points. If the pool is short of `ceil(margin / 2)`, abstain entirely — never burn points on a partial spend that can't close the gap.

**Rationale**: The Third Dan pool is a scarce per-round resource (2 × attack-skill points). Burning points for no benefit (lowering already-usable actions, partial spends that can't change the outcome) makes the default strategy strictly worse than holding the points. A conservative default better represents how a real player using this school would spend.

**Alternatives considered**: Greedy defaults (spend whenever a spend is legal). Rejected — measured in practice (T010 simulator review) to burn points wastefully, e.g., lowering a phase-2 action to phase-1 when the parry strategy could have used the phase-2 action directly.
