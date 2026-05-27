# Open Questions for End-of-Run Review (Action-Level Damage Breakdown)

Run started 2026-05-27 on `010-action-damage-breakdown`.

## Q1 — Component labels for `BayushiFeintAction.damage_breakdown()`

**Decision (default)**: `"attack skill"` for the rolled portion and `"base feint kept die"` for the kept-only base. `"VP on feint"` for VP contribution.

**Why**: matches existing convention from `BayushiRollParameterProvider.get_breakdown` (which uses `"katana"`, `"<Ring> ring"`, `"VP on attack"`).

**If the implementer finds better wording during the work, update and document here.**

## Q2 — `damage_breakdown` on `AttackAction` vs base `Action`

**Decision**: on `AttackAction`. Other Action types (Parry, WoundCheck, etc.) don't roll damage.

## Q3 — Default behavior when subclass overrides `damage_roll_params` but NOT `damage_breakdown`

**Decision**: default `AttackAction.damage_breakdown()` delegates to the provider. The mismatch produces a `"reconciliation"` entry per spec 008's `_normalize_breakdown`. Reader sees the gap as a Principle VII signal.

**Why**: graceful degradation. Future actions that override `damage_roll_params` without realizing they should also override `damage_breakdown` produce a readable-but-flagged trace, not a crash.

## Q4 — Bayushi feint TRUE breakdown components

The trace pre-fix shows damage components claim "katana + Fire ring", but `BayushiFeintAction.damage_roll_params` returns `(attack_skill + vp, 1 + vp, modifier)` — using NEITHER katana NOR Fire ring. Investigation confirmed: a Bayushi feint deals damage based on attack skill, not on weapon or ring.

This is consistent with the Bayushi school's signature feint ability (per rules/04-schools.md). Document the breakdown decision in OPEN_QUESTIONS.md if a different interpretation surfaces.

## Q5 — Are there other actions that need overrides?

**Decision**: just `FeintAction` and `BayushiFeintAction` for this spec. A future scan of all AttackAction subclasses for `damage_roll_params` overrides could surface more candidates; deferred to a follow-up.

## Scope-creep findings

(Populated during the run if substantial out-of-scope work surfaces.)
