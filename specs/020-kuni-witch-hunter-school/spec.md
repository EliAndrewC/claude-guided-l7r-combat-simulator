# Spec: Kuni Witch Hunter School

**Branch**: `020-kuni-witch-hunter-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Kuni Witch Hunter School"). BACKLOG flags "known engine gap — `NotImplementedError: spend_ap` per prior notes. Audit may surface engine work."

## Rules text (verbatim, from rules/04-schools.md)

> **Kuni Witch Hunter School**
>
> **School Ring:** Earth
>
> **School Knacks:** detect Taint, iaijutsu, presence
>
> **Special Ability:** You may never become Tainted. Roll an extra
> (X+1)k(X+1) on wound checks, where X is the Shadowlands Taint of
> the attacker, rounded down to the nearest whole number.
>
> **First Dan:** Roll one extra die on damage, interrogation, and
> wound checks.
>
> **Second Dan:** You get a free raise on interrogation rolls.
>
> **Third Dan:** Each adventure you get 2X free raises, where X is
> equal to your investigation skill, which may be applied to the
> following rolls: interrogation, intimidation, law, underworld,
> attack, and wound checks. You may also spend these free raises on
> damage rolls against targets with the Shadowlands Taint. You may
> not spend more than X of these free raises on a single roll.
>
> **Fourth Dan:** Raise your current and maximum Earth by 1. Raising
> your Earth now costs 5 fewer XP. Roll an extra action die in
> combat, which may not be used to attack targets without the
> Shadowlands Taint.
>
> **Fifth Dan:** After you take light wounds and resolve your wound
> check, you may choose to inflict that number of light wounds on
> the opponent who dealt them and take half that amount yourself.
> If the opponent has the Shadowlands Taint, then you may also use
> an attack in the current phase to add to that damage.

## Skeleton audit (pre-audit reading)

`simulation/schools/kuni_school.py` (84 lines), 10 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — never Tainted + extra (X+1)k(X+1) on WC | `apply_special_ability`: `_set_school_extra_kept("wound check", 1)` — adds +1 kept only | **Q1 BLOCKING**: simulator has no Taint system (X=0) so (X+1)k(X+1) = 1k1 = +1 rolled AND +1 kept. Skeleton only adds +1 kept — missing the +1 rolled. |
| 1st Dan — +1 die on damage, interrogation, WC | `extra_rolled()` returns `["damage", "wound check"]` | **Q2 BLOCKING**: missing `"interrogation"`. (Non-combat skill but rules-fidelity gap.) |
| 2nd Dan — free raise on interrogation | `free_raise_skills()` returns `["interrogation"]` | ✅ Correct |
| 3rd Dan — AP system: 2X raises on certain skills (X = investigation) | `apply_rank_three_ability` calls `apply_ap`; `ap_base_skill="investigation"`, `ap_skills=["attack", "wound check"]` | ✅ Mostly correct. Note: max-X-per-roll cap not visible in skeleton — verify the AP system enforces it. Other ap_skills (interrogation, intimidation, law, underworld) are non-combat → OK to omit per simulator scope. |
| 4th Dan — Earth +1 + discount + extra action die (non-Tainted attack restriction) | `apply_school_ring_raise_and_discount`; TODO for the extra die | **Q3 DEFERRED**: extra action die with usage restriction is complex; rules-text says "may not be used to attack targets without Taint" → in this simulator (no Taint) the extra die can only be used for non-attack actions (parry, WC). Defer to a follow-up branch. |
| 5th Dan — after WC, reflect LW on attacker AND take half yourself | `KuniWoundCheckSucceededListener.handle` reflects ALL damage back to attacker | **Q4 BLOCKING**: missing "take half that amount yourself" backlash. Currently the Kuni reflects damage to the attacker but takes NO additional damage themselves — over-powered vs rules. **Q5**: "may choose" — listener fires unconditionally, no strategy gate. |
| 5th Dan — Tainted attacker bonus attack | n/a (no Taint system) | OUT OF SCOPE — Taint-gated; can't fire. |

## Engine gap (BACKLOG-flagged)

`simulation/features.py:586` raises `NotImplementedError` for `SpendAdventurePointsEvent`. The Kuni's AP system fires `SpendAdventurePointsEvent` whenever AP is spent (on attacks or WCs at 3rd Dan+). The features collector crashes — empirical confirmation in Daidoji round-robin (Kuni was one of 5 opponents that crashed with this exact error).

**Fix**: implement or skip the AP-spend feature observation in `features.py:586`. Simplest: skip (return without observing) — AP spends are not features the engine currently tracks.

## Goals

1. **Fix Q1 (Special Ability +1 rolled)** — Taint=0 → 1k1 means +1 rolled AND +1 kept.
2. **Fix Q2 (1st Dan interrogation)** — add to extra_rolled list.
3. **Fix Q4 (5th Dan take half backlash)** — Kuni takes half the reflected damage themselves.
4. **Fix ENGINE GAP** — `features.py:586` handles `SpendAdventurePointsEvent` without crashing.
5. **Principle VII trace observability** for 5th Dan reflection.
6. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
7. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Rules-fidelity BLOCKING fixes (Priority: P1) 🎯 MVP
Q1 (SA +1 rolled), Q2 (1st Dan interrogation), Q4 (5th Dan take half).

### US2 — Engine gap fix (Priority: P1)
`features.py:586` no longer crashes on `SpendAdventurePointsEvent`.

### US3 — Identity-driven defaults (Priority: P1)
Kuni's defensive identity (WC tank + damage reflection) drives default strategies.

### US4 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US5 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: `apply_special_ability` MUST grant +1 rolled AND +1 kept on wound checks (Taint=0 baseline).

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` returns `["damage", "interrogation", "wound check"]`.
- **FR-003**: `free_raise_skills()` returns `["interrogation"]`.

### 3rd Dan
- **FR-004**: AP system installed with `investigation` as base skill and `["attack", "wound check"]` as the combat-relevant AP skills.

### 4th Dan
- **FR-005**: Earth ring raise + discount.
- **FR-006**: Extra action die — DEFERRED.

### 5th Dan (BLOCKING fixes)
- **FR-007**: After WC succeeds with damage > 0, the Kuni inflicts the LW amount on the attacker AND takes half that amount on themselves (rounded down).
- **FR-008**: The 5th Dan reflection MUST be tagged for trace attribution.

### Engine
- **FR-009**: `features.py:586` no longer raises `NotImplementedError` on `SpendAdventurePointsEvent` — must gracefully handle (skip observation is acceptable).

### Identity-driven defaults
- **FR-010**: `KUNI_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).
- **FR-011**: Strategy bindings reviewed by `school-strategy-designer`.

## Non-Functional Requirements

- **NFR-001**: 100% coverage (mechanically enforced).
- **NFR-002**: ≤ 5 existing-test updates outside new tests.

## Success Criteria

- **SC-001**: 450-XP Kuni wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `kuni_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.
- **SC-005**: Kuni round-robin against other validated schools no longer crashes on `spend_ap`.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
