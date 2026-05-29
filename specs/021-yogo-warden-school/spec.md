# Spec: Yogo Warden School

**Branch**: `021-yogo-warden-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Yogo Warden School"). User confirms: nothing in Yogo is shugenja-adjacent, but it has NO 5th Dan — stub as no-op (must not raise).

## Rules text (verbatim, from rules/04-schools.md)

> **Yogo Warden School**
>
> **School Ring:** Earth
>
> **School Knacks:** double attack, iaijutsu, feint
>
> **Special Ability:** Gain a temporary void point every time you
> take a serious wound.
>
> **First Dan:** Roll one extra die on attack, damage, and wound
> checks.
>
> **Second Dan:** You get a free raise on wound checks.
>
> **Third Dan:** Whenever you spend a void point, reduce your
> current light wound total by 2X, where X is your attack skill.
>
> **Fourth Dan:** Raise your current and maximum Earth by 1.
> Raising your Earth now costs 5 fewer XP. You get an extra free
> raise for each void point you spend on wound check rolls.
>
> **Fifth Dan:** TBD

## Skeleton audit (pre-audit reading)

`simulation/schools/yogo_school.py` (116 lines), 8 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — gain TVP per SW | `YogoSeriousWoundsDamageListener` yields `GainTemporaryVoidPointsEvent(character, 1)` per SW event (target=character) | ✅ Mostly correct. **Q1 MINOR**: yields 1 TVP per event regardless of `event.damage` (e.g., a 2-SW double attack still yields only 1 TVP). Rules text "every time you take a serious wound" is ambiguous — could be per-SW or per-event. Per-event is the conservative reading; keep. |
| Special Ability — replaces default `sw_damage` listener | Listener does `character.take_sw(event.damage)` + status checks + TVP gain | ✅ Correct (replaces default; listener owns SW application). |
| 1st Dan — +1 die on attack, damage, WC | `extra_rolled()` returns `["attack", "damage", "wound check"]` | ✅ Correct |
| 2nd Dan — free raise on WC | `free_raise_skills()` returns `["wound check"]` | ✅ Correct |
| 3rd Dan — VP spend → reduce LW by 2X (X = attack skill) | `YogoSpendVoidPointsListener` reduces LW by `2 * attack_skill` per spend_vp event | **Q2 BLOCKING**: rules say "Whenever you spend **a** void point" — implies per-VP, but the listener applies the reduction once per EVENT regardless of `event.amount`. A 2-VP spend should reduce LW by `2 * 2X = 4X`, but skeleton reduces by `2X`. |
| 4th Dan — Earth +1, discount, extra free raise per VP on WC | `apply_school_ring_raise_and_discount` + `YogoRollParameterProvider` adds `+5*vp` to WC modifier | ✅ Correct. The +5*vp modifier matches "extra free raise per VP" (1 free raise = +5). The default VP-spend grants +1k1 per VP via `rolled += vp; kept += vp` — the +5 modifier is the EXTRA free raise on top. |
| 5th Dan — TBD | `apply_rank_five_ability` is `pass` | ✅ Correct per user direction (rules text is "TBD"; stub as no-op). |

## Identity bindings (missing)

Engine defaults apply. No `wound_check` strategy is installed. The Yogo's identity is:
- Gain TVP from being hit (SA).
- Spend VP/TVP aggressively (3rd Dan rewards each spend with LW reduction).
- 4th Dan grants +5 per VP on WC.

→ `WoundCheckStrategy04` (0.4 threshold) is identity-aligned — encourages aggressive VP spending which compounds with 3rd Dan's LW reduction.

## Goals

1. **Fix Q2 (3rd Dan per-VP scaling)** — multiply reduction by `event.amount`.
2. **Identity binding** — install `WoundCheckStrategy04`.
3. **5th Dan stub** — keep as `pass` per user direction. Confirm the BaseSchool/character build pipeline doesn't raise on the no-op.
4. **Principle VII trace observability** — tag the 3rd Dan LW reduction.
5. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
6. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Rules-fidelity BLOCKING fix (Priority: P1) 🎯 MVP
Q2 (3rd Dan per-VP).

### US2 — Identity binding (Priority: P1)
`WoundCheckStrategy04` installed.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Trace observability (Priority: P2)

### US5 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: On `SeriousWoundsDamageEvent` (target=Yogo), gain 1 TVP per event.

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` returns `["attack", "damage", "wound check"]`.
- **FR-003**: `free_raise_skills()` returns `["wound check"]`.

### 3rd Dan (BLOCKING fix)
- **FR-004**: On `SpendVoidPointsEvent`, reduce LW by `2 * attack_skill * event.amount`.
- **FR-005**: The reduction MUST be tagged for trace attribution.

### 4th Dan
- **FR-006**: Earth ring raise + discount.
- **FR-007**: `YogoRollParameterProvider` adds +5 per VP on WC modifier.

### 5th Dan
- **FR-008**: `apply_rank_five_ability` is a no-op (rules text is "TBD"). MUST NOT raise.

### Identity-driven defaults
- **FR-009**: `WoundCheckStrategy04` installed in `apply_special_ability`.
- **FR-010**: `YOGO_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).

## Non-Functional Requirements

- **NFR-001**: 100% coverage (mechanically enforced).

## Success Criteria

- **SC-001**: 450-XP Yogo wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `yogo_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
