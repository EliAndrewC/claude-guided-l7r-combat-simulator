# Open Questions for End-of-Run Review (Akodo Bushi School)

This document accumulates deferred decisions for the Akodo Bushi School autonomous run. Run started 2026-05-27 on `005-akodo-bushi-school`.

## Q1 — "One void point" on failed feint: TVP or regular VP?

**Rules text**: "You get four temporary void points after a successful feint and one void point after an unsuccessful feint."

**What I decided**: Both are **TVPs** (the skeleton's interpretation).

**Why**: The asymmetric phrasing ("temporary" only on success) is probably editorial — gaining a regular VP would be a stronger reward for the failure case than for the success case, which would be backwards. In the L7R combat economy, "gaining" a VP from an ability is conventionally temporary; regular VPs come from your Void ring. Treating the failure-case "one void point" as TVP matches both conventions.

**Alternatives**: (b) success gives 4 TVP, failure gives 1 regular VP that persists across combats. Would require a separate `GainPermanentVoidPointEvent` and a different lifecycle hook. Easy to implement if rule-reading favors interpretation (b) — flag this for user verification.

**Where**: `AkodoAttackFailedListener.handle` in `simulation/schools/akodo_school.py`.

## Q2 — 4th Dan VP-spending heuristic: minimum-sufficient vs. ladder-search

**What I decided**: Minimum-sufficient strategy — find the smallest VP spend that brings expected SW into `min(1, sw_remaining())`. If no spend achieves tolerable, pick the smallest spend that minimizes expected SW (do not over-spend if extra VP doesn't help).

**Why**: Wasted VP erodes the late-game economy. Akodo's whole identity is "use VP efficiently" — the strategy should reflect that. The skeleton iterates `for vp in range(1, max_spend)` (off-by-one bug; should be `+1`) and updates `chosen_spend` only when strictly improving, then breaks on tolerable. The behavior is mostly correct after fixing the off-by-one.

**Alternatives**: Ladder-search (try every spend amount, pick the global minimum). More expensive but exhaustive. Probably equivalent for the small spend ranges typical in combat.

**Where**: `AkodoWoundCheckRolledStrategy.recommend` in `simulation/schools/akodo_school.py`.

## Q3 — 5th Dan VP-spending: always-max vs. damage-threshold heuristic

**What I decided**: Keep "always spend max" as the v1 default (matches skeleton's behavior).

**Why**: Simpler and matches the rule's pure interpretation ("you may spend ... up to the amount of damage you took"). The intelligent heuristic — "only spend up to the amount that meaningfully threatens the attacker" — is a follow-up optimization, not a correctness fix.

**Alternatives**: (b) only spend if the counter-damage will likely cause an SW on the attacker. (c) reserve VP for own wound checks first, then counter. Both improve VP efficiency but require modeling the opponent's WC threshold.

**Follow-up flag**: If Principle IX win-feasibility (SC-004) fails because Akodo's VP gets drained too aggressively, revisit and add the threshold heuristic.

**Where**: `AkodoFifthDanStrategy.recommend` in `simulation/schools/akodo_school.py`.

## Q4 — Floating bonus consumption point: declaration vs. roll

**What I decided**: Consumed at `AttackRolledEvent` (the attack actually rolled).

**Why**: If an attack is interrupted before rolling (e.g., a parry strategy preempts the action, or the action is canceled), the bonus shouldn't be consumed. Anchoring consumption to the roll event matches the rule's intent ("add ... to any future attack") — the bonus modifies the roll, so it should only apply when the roll happens.

**Alternatives**: (b) Consumed at `AttackDeclaredEvent` (when the attack is announced). Would burn the bonus on attacks that don't actually roll. (c) Consumed at hit/miss resolution. Even later, might leave the bonus available for free reaction-cancels.

**Where**: `AnyAttackFloatingBonus.apply` (engine entity, not Akodo-specific). Verify the existing implementation matches; if it doesn't, the test is the documentation of engine behavior, not a place to refactor the engine.

## Q5 — 5th Dan mirror recursion: depth cap?

**What I decided**: No explicit depth cap. Rely on natural termination via VP exhaustion (`available_vp == 0`) and the `damage < 10` cutoff.

**Why**: An explicit cap would be defensive against an impossible scenario (both characters with infinite VP and damage), which doesn't occur in practice. Termination via the existing cutoffs is mathematically guaranteed for finite VP.

**Alternatives**: (b) Cap recursion at 5 layers as a safety. Adds defensive complexity without practical benefit.

**Where**: `AkodoFifthDanStrategy.recommend`. Add a regression test that confirms termination in a self-mirror 5th-Dan scenario with maxed VP on both sides.

## Q6 — Floating bonus consumption order: FIFO vs. engine-defined

**What I decided**: FIFO (oldest-first), or whatever `AnyAttackFloatingBonus` semantics already implement. Tests align with engine behavior rather than over-specifying the rule.

**Why**: The rules text says "any future attack" without ordering. The natural mental model is "they queue up", but the engine may have a different implementation. Tests should lock the actual engine behavior to avoid hidden regressions.

**Where**: `simulation/mechanics/floating_bonuses.py` (verify existing semantics).

## Q7 — Action-disadvantage offensive trigger — **RESOLVED by strategy-designer**

**Resolution (2026-05-27, school-strategy-designer)**: Akodo's default behavior is OFFENSE-FIRST already — `AkodoAttackStrategy` (new class to be implemented) always tries feint at threshold 0.6, plain attack at 0.7. The action-disadvantage problem reduces to "which offensive skill?" with the answer:

- **Kill-shot branch**: when target's `sw_remaining() <= 1` AND character has `vp() >= 1`, prefer `double attack` (threshold 0.6) then `attack` (threshold 0.7). Finishing damage > TVP fuel.
- **Feint-first branch**: otherwise, try `feint` at threshold 0.6 (drives the TVP economy).
- **Plain-attack fallback**: `attack` at 0.7, then desperation 0.01, then `HoldActionEvent`.

The school never defaults to defense (no `AlwaysParryStrategy`-equivalent install); the engine's `ReluctantParryStrategy` at the parry slot fires only when an incoming attack is genuinely dangerous (>=2 expected SW). This means action-disadvantage doesn't trigger a defense-loop — the Akodo just keeps attacking with whichever skill makes sense.

**Original best-guess**: when TVP ≥ 4 AND opponent SW > 0, switch to offense. Superseded by the simpler "always offense, kill-shot prefers damage over fuel" heuristic.

**Where**: `AkodoAttackStrategy.recommend` (new class, will be implemented in tasks T-NN per tasks.md).

**Why**: This is a Principle IX 3 requirement — the school needs SOME trigger to switch from defense to offense or it'll loop forever parrying. The exact trigger is a design choice. The proposed heuristic uses the school's own economy (TVP) and the opponent's state (SW) as signals.

**Alternatives**: (b) Round-based (offensive every other round). (c) Health-based (switch when own LW > X%).

**Where**: Default attack strategy installed by `apply_special_ability` (or a wrapper around the default attack optimizer).

**Follow-up flag**: school-strategy-designer to validate; combat-simulator Scenario B.2 to confirm at runtime.

## Q8 — TVP-saturation cap on AkodoAttackStrategy feint-first branch (2026-05-27)

**Discovered during T055 (Phase 7 implementation)**.

**Problem**: With the strategy-designer's bare 3-branch policy (kill-shot > feint-first > plain-attack), a 300-XP-Akodo mirror match at random.seed(7) ran 30 rounds with 238 feints, 2 attacks, 0 double-attacks — and the test runner hit the multi-minute hang threshold (Principle IX 2(a) failure). Both sides saturate VP/TVP from feinting but never deal damage because feint never reduces the opponent's sw_remaining(), and the kill-shot branch never engages.

**Resolution**: Added a `TVP_SATURATION_CAP = 4` class attribute on `AkodoAttackStrategy`. When `character.tvp() >= TVP_SATURATION_CAP`, the feint-first branch is skipped and the strategy falls through to plain-attack. This bounds the feinting at "one successful feint's worth of fuel banked" before forcing the Akodo to convert TVP into damage.

**Why 4**: A successful feint generates 4 TVP, which is the natural saturation point — enough to fuel one full higher-Dan ability spend. Lower caps (e.g., 1) starved the TVP economy in non-mirror combats; the cap=4 value passes all four Principle IX scenarios (T048-T051). The cap is a class attribute so playtesters can override without touching the strategy logic (Constitution Principle V).

**Tests**:
- `test_akodo_300xp_wins_at_least_one_of_five_vs_hida_300xp` (T048): PASS with cap=4.
- `test_akodo_mirror_300xp_terminates_within_20_rounds` (T049, seed=42): PASS with cap=4.
- `test_akodo_mirror_identity_engine_fires` (T050, seed=7): PASS with cap=4 (without it: infinite loop).
- `test_akodo_action_disadvantage_eventually_attacks` (T051): PASS with cap=4.

**Alternative considered**: raise feint threshold from 0.6 to 0.7 per the strategy-designer's original tuning recommendation. Rejected because the empirical issue isn't that feints are succeeding "too easily" (a 0.6 threshold is appropriate — failure still generates TVP), it's that the strategy keeps choosing to feint when more fuel is wasted. The cap targets the wasted-fuel symptom directly.

**Where**: `AkodoAttackStrategy._try_feint_first` and `AkodoAttackStrategy.TVP_SATURATION_CAP` in `simulation/schools/akodo_school.py`. Flag for end-of-run user review.

## Scope-creep findings

### Pre-existing skeleton defects — FIXED (2026-05-27 follow-up)

The rules-auditor's cumulative-diff review flagged four defects in `AkodoWoundCheckDeclaredListener` and `AkodoLightWoundsDamageListener` that predated this spec. They have been **fixed in a follow-up commit** with regression tests in `tests/test_akodo_school_defects.py` (8 tests, all PASS). Test count 2954 → 2962.

1. **VP swallowed without deduction — FIXED.** `AkodoWoundCheckDeclaredListener.handle` now mirrors the engine default at `simulation/listeners.py::WoundCheckDeclaredListener`: emits `SpendVoidPointsEvent(character, "wound check", event.vp)` when `event.vp > 0` so pre-declared VP is actually deducted from the pool. Regression: `TestDefect1AkodoWcDeclaredEmitsSpendVpEvent`.

2. **`tn` and `duel/explode` not propagated — FIXED.** The listener now passes `explode=not duel` to `roll_wound_check` and `tn=event.tn` to the constructed `WoundCheckRolledEvent`. Custom-TN paths (iaijutsu duels, etc.) now work. Regression: `TestDefect2AkodoWcDeclaredPropagatesTnAndDuel`.

3. **`wound_check_rolled_strategy()` bypassed — FIXED.** Two coordinated changes:
   - The listener now dispatches via `character.wound_check_rolled_strategy().recommend(...)` instead of holding a direct reference.
   - `AkodoWoundCheckRolledStrategy` now inherits from the engine default `WoundCheckRolledStrategy`; its `recommend()` chains `super().recommend()` for FB/AP/conviction selection FIRST, then layers Akodo VP-for-raise on top.
   - `apply_rank_four_ability` now installs `AkodoWoundCheckRolledStrategy` at the `wound_check_rolled` strategy slot via `_set_school_strategy` (so the listener's slot lookup picks it up).
   - Result: a Dan-4+ Akodo retains access to AP/conviction/floating-bonus on WC; the 4th Dan VP-for-raise is ADDITIVE rather than REPLACING. Regression: `TestDefect3AkodoUsesWoundCheckRolledStrategySlot` (3 tests).

4. **`AkodoLightWoundsDamageListener` damage-gate — FIXED.** Added `if event.damage > 0:` gate before dispatching `wound_check_strategy().recommend(...)` and the 5th Dan strategy. Mirrors the engine default at `simulation/listeners.py::LightWoundsDamageListener`. Regression: `TestDefect4AkodoLwDamageGatesOnDamageGreaterThanZero` (2 tests).

**Implementation notes for chaining (defect #3)**:
- The Akodo strategy's tolerance formula `min(1, sw_remaining())` is preserved per FR-018. The engine default uses `min(1, sw_remaining() - 1)` (stricter near-death). When chained, the engine default spends FB/AP/conviction first under its own tolerance; if expected SW is then still above Akodo's tolerance, Akodo's VP-for-raise fires on top.
- In typical setups (no FB/AP/conviction), the chain reduces to the same behavior as the standalone Akodo logic. All 6 pre-existing 4th-Dan tests (T022–T027) continue to pass.
- The chain preserves the per-call freshness: each `recommend()` invocation gets a fresh `_chosen_ap`/`_chosen_bonuses`/`_chosen_conviction` via the super's `reset()` call.

Quality gates after the follow-up: ruff PASS, mypy PASS (195 source files), pytest 2962/2962 PASS.

### Per-matchup feint-ratio dip (combat-simulator finding)

Scenario D round-robin shows Akodo's feint ratio at 29.2% vs Hida (just below the 30% strategy-designer's behavioral fingerprint threshold) while the global average is 37.5%. Root cause: `TVP_SATURATION_CAP = 4` correctly converts TVP fuel to damage in longer combats (Hida fight = 5 rounds). Not a defect — designed behavior. If the user wants strict per-matchup ≥30%, options are (a) raise cap to 5–6 (regressing mirror termination), (b) make cap consumer-aware (skip feint-after-saturation only when opponent in finishing range). Recommended: leave as-is; revisit only if cross-school tuning is needed for a later school.
