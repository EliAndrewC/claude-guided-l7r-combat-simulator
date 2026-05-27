# Feature Specification: Action-Level Damage Breakdown

**Feature Branch**: `010-action-damage-breakdown`

**Created**: 2026-05-27

**Status**: Draft (autonomous run)

**Input**: Diagnostic investigation (2026-05-27) on two trace-reader flagged engine concerns:
1. **Floating bonus double-consumption** — diagnosed as NOT a bug (correct L7R behavior; rendering already clear post-spec-008).
2. **Feint damage variability** — diagnosed as a rendering bug, not an engine bug. The Bayushi feint engine correctly deals `5k1` damage per `BayushiFeintAction.damage_roll_params()`, but the formatter's "damage will be" projection and damage-breakdown attribution use the provider's `get_damage_roll_params()` (which returns `9k2` for default Bayushi damage). Projection contradicts actual; breakdown attribution claims components (katana, Fire ring) that don't apply.

This spec addresses concern #2. Concern #1 is already resolved.

**Run Mode**: Autonomous. Decisions logged in `OPEN_QUESTIONS.md` for end-of-run review.

## Clarifications

### Session 2026-05-27 (autonomous; pre-answered per project conventions)

- Q: `damage_breakdown` method placement — base `Action` vs `AttackAction`? → A: **`AttackAction`** (and its subclasses). Other Action types don't roll damage.
- Q: Component labels for Bayushi feint? → A: pre-resolution `"attack skill"` for the rolled portion and `"base feint kept die"` for the base kept. Implementer may refine during work; log changes in OPEN_QUESTIONS.md.
- Q: Should projection show "(Bayushi feint — rule)" rule-citation parenthetical? → A: **No**. Component source labels carry the attribution.
- Q: Reconciliation behavior when components don't sum exactly to `damage_roll_params()`? → A: spec 008's `_normalize_breakdown` reconciliation handles it. For correctly-implemented overrides, the reconciliation entry shouldn't fire.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A reader sees the projection match the actual damage for a Bayushi feint (Priority: P1)

A playtester runs a combat with a Bayushi character that successfully feints. The attack-line projection reads `"damage will be 5k1"` (matching the actual roll). The actual damage line reads `"💥 Damage: 5k1 = 5k0 attack skill + 0k1 base feint kept die [...]"` — no contradiction, no "-4k-1 reconciliation" absorbing a lie.

**Why this priority**: This is the core fix. Without it, the trace contradicts itself on every Bayushi feint.

**Independent Test**: Build a deterministic combat with a Bayushi character at known stats. Force a successful feint. Assert (a) the attack-line projection's `XkY` matches the action's `damage_roll_params()`, (b) the actual damage line's `XkY` equals the projection's `XkY`, (c) the damage breakdown contains the action's attribution (e.g., `"attack skill"`) and does NOT contain the inapplicable provider's components (e.g., `"katana"`, `"Fire ring"`).

### User Story 2 — Non-feint attacks render unchanged (Priority: P1)

A playtester observing an Akodo plain attack or double attack sees the same projection and breakdown as before this spec. The default `AttackAction` doesn't override `damage_roll_params`, so the formatter falls through to the provider's path — current behavior preserved.

**Why this priority**: Regression guard. The fix must not change behavior for the 95%+ of actions that don't override damage params.

**Independent Test**: Run the calibration combat (Bayushi vs Akodo, seed=1234). Assert that every Akodo attack's projection and breakdown match the pre-fix output byte-for-byte. Tests that asserted on these lines pre-fix continue to pass without modification.

### User Story 3 — `FeintAction` (default, zero-damage) suppresses the breakdown cleanly (Priority: P2)

A non-Bayushi character (e.g., Akodo) feints. Per spec 008, the damage line is suppressed entirely for zero-damage feints. The new `damage_breakdown()` method returns `[]` for `FeintAction`, reinforcing this behavior at the action layer.

**Why this priority**: Belt-and-suspenders for renderers that DO try to format the suppressed damage event. Low priority because spec 008's suppression already handles the user-visible behavior.

**Independent Test**: Verify `FeintAction().damage_breakdown()` returns an empty list. Verify the spec 008 suppression behavior for zero-damage feints continues to work end-to-end.

### User Story 4 — trace-reader re-validates the calibration combat (Priority: P1)

After the fix lands, re-running the `trace-reader` agent on the calibration combat reports zero `projection-vs-actual mismatch` issues. The Bayushi feint lines specifically read coherent: projection equals actual, breakdown attributes accurately.

**Why this priority**: Confirms the diagnosis-driven workflow worked. Closes the issue.

**Independent Test**: Dispatch `trace-reader` after the fix. Expected: Issue 2 from the original dry-run no longer reproduces.

### Edge Cases

- **Bayushi feint with VP spent**: `damage_roll_params` is `(attack_skill + vp, 1 + vp, modifier)`. The breakdown should include a `"VP on feint"` (or equivalent) entry for the VP contribution.
- **Bayushi feint with modifier**: the `modifier` from `damage_roll_params()` should appear in the trace as a `+N` modifier on the damage line (likely already handled by the existing modifier rendering).
- **A future action that overrides `damage_roll_params` but NOT `damage_breakdown`**: the default `damage_breakdown` falls through to the provider, producing a mismatched breakdown like the current Bayushi case. The fallback is graceful (a reconciliation entry absorbs the mismatch) but worth flagging to the implementer with `(unattributed override)` or similar — see FR-005.
- **Provider returns components that don't sum to `damage_roll_params()`**: spec 008's `_normalize_breakdown` reconciliation runs. The reconciliation entry has the `"reconciliation"` label per spec 008. After this spec, the action-level path SHOULD avoid this case for correctly-implemented overrides.
- **Counterattack damage rolls**: `CounterattackAction` doesn't currently override `damage_roll_params`, so the default action-level breakdown delegates to the provider — unchanged behavior.
- **Other action types** that might be candidates: `IaijutsuStrikeAction`, `LungeAction`. These currently inherit from `AttackAction` without overriding `damage_roll_params`, so unchanged behavior. If their behavior is wrong, that's a future spec.

## Requirements *(mandatory)*

### Functional Requirements

**Action-side accessor**

- **FR-001**: `AttackAction` MUST gain a `damage_breakdown(self) -> list[tuple[str, int, int]]` method. The default implementation returns the provider's `get_breakdown(kind="damage", ...)` result so existing behavior is preserved.
- **FR-002**: The signature of the default `damage_breakdown` matches the existing provider-side `get_breakdown` interface — same shape as the `list[tuple[source, +rolled, +kept]]` already used by `web/adapters/_breakdown_format.py`.
- **FR-003**: `FeintAction.damage_breakdown(self) -> list[tuple[str, int, int]]` MUST return `[]` (no damage; nothing to attribute).
- **FR-004**: `BayushiFeintAction.damage_breakdown(self)` MUST return per-source contributions matching `damage_roll_params()`:
  - `("attack skill", attack_skill, 0)` — the rolled portion.
  - `("base feint kept die", 0, 1)` — the kept-only base.
  - `("VP on feint", vp, vp)` when `vp > 0` — VP contribution to both rolled and kept.
  - Exact label text may be refined by the implementer; log changes in OPEN_QUESTIONS.md.
- **FR-005**: When a subclass overrides `damage_roll_params()` but NOT `damage_breakdown()`, the default `damage_breakdown` SHOULD still work — it delegates to the provider, which returns the default components. A reconciliation entry will absorb the mismatch (per spec 008), making the rendering still readable but flagging that the override is incomplete. No defensive error; let the reader see the reconciliation as a Principle VII signal.

**Formatter changes**

- **FR-006**: The formatter MUST consult `action.damage_breakdown()` instead of `subject.roll_parameter_provider().get_breakdown(...)` at the three damage-rendering call sites in `web/adapters/detailed_formatter.py`:
  - **Attack-line projection** (~line 878-886): the `"damage will be: XkY = ..."` projection uses `action.damage_roll_params()` for the XkY total AND `action.damage_breakdown()` for the components.
  - **LightWoundsDamageEntry production** (~line 1002): same fix.
  - **Counterattack projection** (~line 1119): same fix.
- **FR-007**: The XkY total on the damage line MUST come from `action.damage_roll_params()` (which the engine has used all along). The breakdown components MUST sum to that total via the action's `damage_breakdown()`.
- **FR-008**: The formatter MUST NOT bypass `action.damage_breakdown()` when an action is available. The provider's `get_breakdown(kind="damage", ...)` becomes an internal implementation detail of the default `AttackAction.damage_breakdown()`.

**Cross-cutting**

- **FR-009**: `simulation/` modules MUST NOT import from `web/`. `damage_breakdown()` on AttackAction is engine-side; it returns a list of tuples (no web-specific types).
- **FR-010**: Coverage on the new `damage_breakdown` overrides (in `BayushiFeintAction` and `FeintAction`) MUST be 100% per Constitution Principle VI v1.3.0.
- **FR-011**: Existing trace-assertion tests MUST continue to pass for non-Bayushi-feint scenarios. Tests asserting on the OLD Bayushi feint trace (with the `katana + Fire ring + reconciliation` breakdown) MUST be updated. Expected impact: 2-4 test updates.

### Key Entities

- **`AttackAction.damage_breakdown()`**: new method. Returns the per-source damage contribution list. Default delegates to the provider.
- **`FeintAction.damage_breakdown()`**: override returning `[]`.
- **`BayushiFeintAction.damage_breakdown()`**: override returning attack-skill + base-kept + (optional) VP contributions.
- **detailed_formatter call sites**: three locations updated to consult action's `damage_breakdown` instead of the provider directly.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every Bayushi feint in the calibration combat, the attack-line projection's `XkY` MATCHES the subsequent damage line's `XkY` (no mismatch).
- **SC-002**: The Bayushi feint damage breakdown contains `"attack skill"` (not `"katana"` or `"Fire ring"`) and does NOT contain a `"reconciliation"` entry.
- **SC-003**: Existing tests for non-Bayushi-feint scenarios continue to pass. Expected test updates: ≤ 5; flag for review if > 5.
- **SC-004**: trace-reader re-validation on the calibration combat reports zero `projection-vs-actual mismatch` issues for Bayushi feints.
- **SC-005**: `env/bin/ruff check .` PASS; `env/bin/mypy` PASS; 100% coverage maintained.
- **SC-006**: No regressions on the 3773 existing tests beyond the 5-update cap.

## Assumptions

- The `BayushiFeintAction.damage_roll_params()` semantics are correct per the Bayushi rules text (engine deals attack-skill-based damage on feints). The fix is rendering only; engine math unchanged.
- The default `AttackAction.damage_breakdown()` implementation can safely delegate to the provider's existing `get_breakdown(kind="damage", ...)` — the migration is transparent for ~30 other actions.
- The three formatter call sites can be migrated independently; no cross-site state.
- The number of existing tests that fail due to this change is ≤ 5 (all relating to Bayushi feint trace expectations).

## Out of scope

- Engine changes (Bayushi feint mechanics unchanged).
- Per-action overrides for actions that don't currently exist or aren't currently incorrect (e.g., a future school-specific lunge would get its own override only when needed).
- Refactoring the provider's `get_breakdown` to be action-aware.
- Streamlit UI changes beyond what naturally flows from the corrected formatter output.
- Renaming existing methods (`damage_roll_params` stays, `get_damage_roll_params` stays).
- Adding `damage_breakdown()` to non-attack actions (parry, wound check, etc.).
