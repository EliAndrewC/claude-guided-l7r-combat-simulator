# Open Questions & Pre-Resolutions — Kakita Duelist School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify` and the skeleton audit; logged here for end-of-run review. Per the Bayushi (specs/012) workflow, deviations encountered during implementation will also be appended below.

The skeleton at `simulation/schools/kakita_school.py` (610 lines, 16 passing tests) is the **largest skeleton of any remaining bushi school**. This is primarily an **audit + verification** run rather than a build-from-scratch run.

## Pre-resolutions from skeleton audit + rules-text reading

### Q1: Name discrepancy — `"Kakita Bushi School"` vs `"Kakita Duelist School"`

**Pre-resolution**: **Keep `"Kakita Bushi School"`** in `name()` for this branch. Document the rules-text title in the docstring + the spec, and flag a future renaming branch as out-of-scope here.

**Why**: The skeleton's `KakitaBushiSchool.name()` returns `"Kakita Bushi School"` and the school registers under that name in `simulation/templates/strategies.py:1386` (`"Kakita Bushi School": KAKITA_PRIORITIES`). The template YAMLs (`simulation/data/templates/kakita/*.yaml`) carry `school: Kakita Bushi School` strings. Renaming the school string would cascade through ~10+ files AND require regenerating + re-validating every committed YAML template. That's a multi-file rename better done as its own focused branch.

**What we DO fix here**: comment on the skeleton's class docstring (and any FR text) noting that the upstream rules title is "Kakita Duelist School" — so future readers don't get confused.

**Implementer latitude**: If a future branch wants to do the rename atomically, the canonical search-and-replace pattern is `Kakita Bushi School` → `Kakita Duelist School` across `simulation/`, `web/`, `tests/`, and the YAML templates.

### Q2: 5th Dan — "extra free raise" when opponent rolls attack instead of iaijutsu

**Pre-resolution**: **Audit the existing implementation** during `rules-auditor` dispatch. The skeleton's `KakitaNewPhaseListener.handle` correctly switches `target_skill` to "attack" when target's iaijutsu is 0, but **does not appear to grant the Kakita an extra free raise** to its own roll. This is likely a rules-fidelity gap.

**Why**: Rules text is explicit: "If the opponent doesn't have iaijutsu, they may roll attack instead, **and you get an extra free raise**." The "extra free raise" is a Kakita-side bonus on the Kakita's iaijutsu roll, typically rendered as +5 to the roll. Need to grep the skeleton for where this bonus is applied.

**Fix path (if confirmed missing)**: In `KakitaNewPhaseListener.handle`, when `target.skill("iaijutsu") == 0`, add a `+5` modifier OR a `FreeRaise` annotation to the Kakita's `ContestedIaijutsuAttackAction` that surfaces in the trace.

### Q3: 4 unused strategy variants — `KakitaAttackStrategy05`, `KakitaInterruptAttackStrategy05`, `KakitaNoVPAttackStrategy`, `KakitaNoVPInterruptAttackStrategy`

**Pre-resolution**: **Keep them and add coverage tests** so they hit 100% (now mechanically required by `fail_under = 100`). These appear to be **build-time player choices** — variants exposed for low-VP-spending or aggressive-threshold builds. Even if not installed today, they're trivially small (4 lines each) and removing them would be drive-by deletion.

**Why**: Adding tests is cheaper than wholesale removal. The variants are class-level configuration changes (different `attack_threshold` or `_get_optimizer` override) and the cost to write a 5-line test that instantiates each is minimal.

**Implementer latitude**: If reviewer agents flag these as dead code with no path-to-installation, we can remove with an OPEN_QUESTIONS deviation note. Default: keep + cover.

### Q4: 3rd Dan — "you know the next action of everyone within striking range"

**Pre-resolution**: **Implicit no-op in the engine's full-information model.** The combat engine doesn't model fog-of-war; every character has read-access to every other character's `actions()` field via the context. The Kakita 3rd Dan clause about "knowing" next actions is mechanically automatic.

**Why**: The skeleton's `KakitaAttackAction.skill_roll_params` reads `target.actions()` directly. Non-Kakita schools also have this access. The rules-text "you know" clause distinguishes Kakita from a hypothetical fog-of-war variant of the game, but in our full-info engine it's a no-op.

**Implementer latitude**: None — this is a rules-text-vs-engine-model gap that doesn't manifest as a code defect.

### Q5: Initiative dice 0-9 vs rules-text "10s on initiative rolls considered Phase 0"

**Pre-resolution**: **Mechanically equivalent.** `KakitaInitiativeDieProvider` rolls `random.randint(0, 9)` (range [0, 9], no explode). The result `0` corresponds to "would have been a 10" → represents Phase 0.

**Why**: In L7R, a standard d10 explodes on a 10 (you get 10 + another roll). The Kakita Special Ability says "Your 10s on initiative rolls are considered to be in a special Phase 0" — i.e., 10s do NOT explode AND become Phase 0 actions. The skeleton's solution: roll 0-9 with no explode, so:
- Result 0 → Phase 0 (was-a-10)
- Result 1-9 → Phases 1-9 (normal)

This is mechanically equivalent to "roll d10, on 10 → don't explode, treat as 0". The implementation is cleaner because it avoids the explosion branch.

**Edge case**: Phase 10 actions cannot occur because the rolled value is always < 10. Standard L7R players might expect a phase-10 action sometimes. Per rules text, "10s → Phase 0", so this is intentional.

### Q6: `KAKITA_PRIORITIES` parry-at-every-rank pattern

**Pre-resolution**: **DEFER like Bayushi.** The same anti-identity pattern Bayushi/Matsu's reviews flagged. The school-progression-designer's likely revision (parry capped at 3, fire promoted, void promoted) was deferred on the Bayushi branch because applying it shifts the seed=1234 calibration combat used by ~10 trace-observability tests. The same calibration concern applies here.

**Why**: Kakita's `KakitaParryStrategy` (the school's actual parry behavior) already deprioritizes parry — it only fires when the hit would be fatal. So even with parry-at-every-rank in the priorities, the strategy rarely uses it. The cost of the anti-identity pattern is mostly XP-wasted-on-parry-skill, not actual defensive behavior change. Lower stakes than Bayushi.

**Implementer latitude**: If the progression-designer's revision can be applied WITHOUT breaking the calibration combat (e.g., if the trace tests don't currently use Kakita), apply it. Otherwise, document the deferral with the same reasoning as Bayushi.

### Q7: Trace observability gaps

**Pre-resolution**: Investigate via `trace-auditor` + `trace-reader` dispatch. Areas of concern:
- **3rd Dan tempo bonus**: the modifier added by `KakitaAttackAction.skill_roll_params` needs to surface as `"Kakita 3rd Dan: tempo bonus +X (skill * tempo_diff)"` in the modifier breakdown. Check whether `modifier_breakdown.py` has a Kakita-specific clause.
- **4th Dan iaijutsu damage free raise**: the +5 modifier added by `KakitaRollParameterProvider` needs to surface as "Kakita 4th Dan free raise" in the damage breakdown.
- **5th Dan contested damage swing**: the +N or -N extra damage dice from `ContestedIaijutsuAttackAction` need explicit "Kakita 5th Dan: contested win/loss margin" attribution.
- **Phase 0 / interrupt iaijutsu**: when the Kakita attacks at Phase 0 or via interrupt, the trace should make the timing explicit.

## To be answered during implementation

### Q8: Mirror non-degeneracy — does the iaijutsu-duel + tempo bonus + phase-0 attacks combine into a clean termination?

**Status**: To verify via `combat-simulator` Scenario C.

**Hypothesis**: Both 5th-Dan Kakitas fire contested-iaijutsu at every Phase 0, dealing damage symmetrically. Combined with tempo bonuses and Phase 0 attacks, combat should terminate quickly. But the contested-iaijutsu is at Phase 0 EVERY round, so damage stacks fast.

### Q9: Win-feasibility vs Akodo

**Status**: To verify via `combat-simulator`. Kakita's tempo bonus is potentially massive (e.g., attack-skill 5 × tempo-diff 8 = +40 to the attack roll); should overpower most defenders.

## Deviations log (append during implementation)

### Batch A: designers + audit + fixes — 2026-05-29

**Applied (committed)**:

1. **Strategy-designer HIGH-severity fix** (Q3 follow-up): swapped the default attack strategy from `KakitaAttackStrategy` to `KakitaInterruptAttackStrategy` in `apply_special_ability`. Without the swap, `add_interrupt_skill("iaijutsu")` was wired but never produced behavior — a clear Constitution Principle VIII identity bug. Regression-guarded by `TestKakitaInterruptAttackStrategyInstalled`.

2. **Trace-auditor P0 #1 + trace-reader Wrong #1 — 3rd Dan tempo bonus**: previously rendered as a bare unsourced +N modifier with broken `(see preceding line)` cross-reference. Fixed via two changes:
   - Tagged the action with `_kakita_3rd_dan_tempo = (bonus, diff, attack_skill)` in `_kakita_tempo_bonus` helper (refactored from the 3 duplicated `skill_roll_params` blocks).
   - Added Kakita-specific attribution clauses to `web/adapters/modifier_breakdown.py::explain_modifier` that read the tag and emit `"Kakita 3rd Dan tempo bonus (attack X × Y phases)"` with the numeric breakdown.

3. **Trace-auditor P0 #2 / trace-reader part — 2nd Dan iaijutsu free raise**: previously unsourced on iaijutsu modifier breakdowns. Fixed by adding a `_is_kakita_bushi` clause to `explain_modifier` that emits `"Kakita 2nd Dan free raise"` attribution when skill is "iaijutsu" and rank >= 2.

**Deferred (documented as known gaps)**:

- **Trace-auditor P0 #3 — 4th Dan iaijutsu damage free raise invisible**: the `+5` modifier added by `KakitaRollParameterProvider.get_damage_roll_params` is silently rolled into the damage total with no source attribution. Fixing requires either (a) a damage-modifier breakdown system (which doesn't exist today; the existing modifier breakdown is for attack/parry/WC rolls only) OR (b) re-architecting how damage roll components are propagated to the renderer. Out of scope for this audit; the 4th Dan effect still APPLIES correctly (rules-fidelity PASS per rules-auditor), it just isn't trace-attributed.

- **Trace-auditor P1 #1 — "reconciliation" label on contested iaijutsu damage**: the 5th Dan extra damage dice show as `0k6 reconciliation` rather than `0k6 from Kakita 5th Dan margin`. The label is generated by `simulation/mechanics/roll_params.py::_normalize_breakdown` as a generic fallback for "we don't know what produced this delta". Fixing requires plumbing source attribution through `normalize_roll_params` — a broader refactor than this audit can absorb.

- **Trace-reader Confusing — Phase 0 / interrupt iaijutsu timing not explicit**: Phase 0 iaijutsu attacks render as `Phase 0 | Kakita | ⚔️ attacks Akodo (iaijutsu)` without an explicit "Phase 0 (Kakita Special Ability)" label. The reader has to infer it from the phase prefix. Low-priority UX polish.

- **Rules-auditor MINOR — 5th Dan extra free raise encoded as -5 on opponent's "attack" branch instead of +5 on Kakita's iaijutsu**: mechanically equivalent (the delta in `(skill_roll - opponent_skill_roll) // 5` is identical), so the rules-text outcome is correct. The trace observability concern (the -5 has no source attribution) overlaps with the P0 4th Dan deferral above and would be fixed by the same damage-modifier-breakdown infrastructure.

- **Q1 name discrepancy** ("Kakita Bushi School" vs "Kakita Duelist School"): deferred per the spec; needs an atomic rename branch.

- **Q6 KAKITA_PRIORITIES revision**: deferred — applying the school-progression-designer's revision (parry capped at 3, fire promoted, etc.) shifts the 300-XP Kakita build composition, which cascades into 19 failing tests across `tests/test_study.py` and `tests/test_analysis_scripts.py`. `web/analysis/definitions/kakita_vp_study.py` and `kakita_void_study.py` encode the OLD priorities structure (parry-at-every-rank) into hard-coded transform anchors like `("skill", "parry", 4)`. Same calibration-combat pattern as Bayushi; follow-up branch must re-anchor the Kakita study transforms.

**Audit results** (all four review agents):
- `rules-auditor`: PASS (1 MINOR — see above)
- `combat-simulator`: PASS — 90% win-rate vs Akodo, mirror terminates cleanly, no regression from strategy swap
- `trace-auditor`: 2 P0 fixed, 1 P0 + 1 P1 deferred (see above)
- `trace-reader`: 2 issues fixed (3rd Dan attribution + 2nd Dan attribution); 3 issues deferred

**Tests added** (net new):
- `tests/test_kakita_school_trace.py` — 12 tests (2nd Dan + 3rd Dan attribution + tempo-bonus tagging)
- `tests/test_kakita_school_playability.py` — 5 tests (mirror, win-feasibility, priorities, strategy install)

**Total**: 3963 → 3968 passing tests; 100% coverage maintained; ruff + mypy clean; Streamlit serves HTTP 200.
