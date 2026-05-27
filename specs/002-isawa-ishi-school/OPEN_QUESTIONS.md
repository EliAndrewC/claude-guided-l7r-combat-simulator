# Open Questions for End-of-Run Review

This document accumulates every deferred decision, interpretation guess, architectural choice, and scope-creep finding from the autonomous Isawa Ishi implementation run. Each entry has:

- **What I decided** (the value used in the implementation)
- **Why** (the rationale, citing rules text or codebase precedent)
- **Alternatives considered** (and why I rejected them)
- **Where in the diff to look** (file paths so you can override quickly)
- **Severity for review** (HIGH if a different answer would meaningfully change behavior; MEDIUM if subjective; LOW if minor)

Run started: 2026-05-26 on branch `002-isawa-ishi-school`.

---

## Open architectural decisions (set during /speckit-plan)

- **OAD-1 — Negation short-circuit location**: BaseSchool per-`apply_*_ability` decorator (cleaner, single source of truth) vs. Character-level dispatch check (single check site). **Resolution**: BaseSchool decorator. Implementer will add `_check_negated_short_circuit` helper to `simulation/schools/base.py` and apply it to each `apply_*_ability` method. Rationale: school-side check is the natural semantic boundary.
- **OAD-2 — IshiAllyBoostStrategy / IshiNegateSchoolStrategy module location**: separate file at `simulation/strategies/ishi_dan_abilities.py` (per Mirumoto precedent — Principle V pluggability). **Resolution**: separate file.
- **OAD-3 — 5th Dan negation trigger event**: `YourMoveEvent` (matches rules-text "instantaneous, no action consumed") vs. `AttackDeclaredEvent` (reactive on threat). **Resolution**: `YourMoveEvent`. Sibling class `ReactiveNegationStrategy` documented as alternative for future tuning.
- **OAD-4 — Listener installation pattern for 3rd Dan**: install on each of 8 `*_rolled` slots vs. add a generic "post-roll" engine hook. **Resolution**: install on multiple slots (less engine surface change). Implementer may revise if it gets unwieldy.

## Scope-creep findings (collected during the run)

### SC-1 (T005/T006): `IshiMaxVPProvider.set_school_rank` is not auto-called during `apply_rank_N_ability`

**Found in**: T005+T006 implementer report.
**Issue**: The skeleton's `IshiMaxVPProvider` stores `_school_rank` internally and is read by `max_vp()`. But the per-rank `apply_rank_N_ability` methods don't call `vp_provider.set_school_rank(N)` to sync the rank. Net effect: an Ishi advancing dans doesn't see their max_vp grow — `max_vp` stays at `highest_ring + 1` regardless of actual dan rank.
**My decision**: Fix this during T012 (US3 wiring task) or T017 (US5 implementation). Add explicit `set_school_rank` calls in each per-rank method.
**Severity**: HIGH (the Special Ability VP capacity is the school's foundation and is broken in the skeleton).
**Where**: `simulation/schools/ishi_school.py::apply_rank_one_ability`, `apply_rank_two_ability`, ..., `apply_rank_five_ability`.
