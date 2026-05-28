# Feature Specification: Hida Bushi School

**Feature Branch**: `011-hida-bushi-school`

**Created**: 2026-05-28

**Status**: Draft (autonomous run)

**Input**: Implement the Hida Bushi School (skeleton at `simulation/schools/hida_school.py`). Three Dan abilities are TODO-marked; the knack list is wrong ("lunge" instead of rules-text "double attack") in three places; HIDA_PRIORITIES needs identity-driven revision; default strategy bindings need designer review. Completes the Principle IX playability baseline alongside Akodo (the other validated baseline).

**Run Mode**: Autonomous. Decisions logged in `OPEN_QUESTIONS.md` for end-of-run review.

## Clarifications

### Session 2026-05-28 (autonomous; pre-answered per project conventions)

- Q: 3rd Dan reroll — which dice are chosen? → A: lowest-value dice up to N, only if individually below 5.5 expected value (greedy, symmetric with `merchant_school._find_dice_to_reroll`). Implementer may refine.
- Q: 3rd Dan "X = attack skill" — interaction with impaired? → A: only the two carve-outs in the rules apply (extra dice halved + 10s reroll despite impairment); all other impaired penalties still apply normally.
- Q: 4th Dan SW-for-LW trade trigger when LW = 0? → A: NO — the trade only makes sense when there are LW to reduce. Strategy must short-circuit.
- Q: 4th Dan iaijutsu-phase guard scope — duelist only, or bystanders too? → A: only when the Hida IS in the iaijutsu duel's first-strike phase. Bystanders unaffected.
- Q: 5th Dan WC bonus — which character's WC gets the bonus? → A: the Hida's OWN WC on damage they took from the counterattacked attack. ("Add X to YOUR wound check.")
- Q: 5th Dan post-damage counterattack — pre-commit to interrupt or defer decision? → A: defer. Die is reserved (held) when entering "see damage first" mode but only spent on commit. Decline returns the die.
- Q: Identity-driven strategy mirror non-degeneracy? → A: school-strategy-designer agent verifies and proposes fix if needed (likely a TVP_SATURATION_CAP analog like Akodo). combat-simulator Scenario C verifies termination.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A playtester runs Hida vs Akodo and sees the full Dan ladder fire (Priority: P1)

A playtester builds two characters: a 5th-Dan Hida and a 5th-Dan Akodo, both with reasonable XP allocation per the school's progression list. They run a deterministic seeded combat and observe in the trace:

- The Hida's counterattack-interrupt fires repeatedly (Special Ability + CounterattackInterruptStrategy), with each interrupt costing 1 action die and the attacker receiving a +5 free raise per rules.
- The Hida's counterattack rolls show the 1st-Dan extra die AND the 2nd-Dan free raise (+5) applied with sourcing.
- The Hida's 3rd-Dan reroll fires on counterattacks (2X dice rerolled where X = attack skill) and on plain attacks (X dice rerolled), with the trace showing which dice were rerolled and the source.
- The Hida's 4th-Dan ability allows electing to take 2 SW to reset LW to 0 (instead of rolling WC) when LW is dangerous, and the trace shows the trade explicitly. (Outside iaijutsu phase.)
- The Hida's 5th-Dan ability adds the counterattack-excess margin X to the Hida's WC roll on the damage they took, sourced in the trace. The Hida may also elect to counterattack AFTER seeing opponent's damage roll, with the damage roll resolving first.

**Why this priority**: This is the core feature delivery — the school must operate end-to-end at all Dan tiers and the trace must explain every effect per Principle VII.

**Independent Test**: Run a deterministic combat (seeded provider) with a known-stat 5th-Dan Hida vs 5th-Dan Akodo. Assert that the trace contains lines matching each Dan effect with proper attribution, that the Hida's counterattack happens for 1 die when interrupting, that the attacker receives the +5 free raise, and that no `unsourced`/`reconciliation` artifacts appear in the trace.

**Acceptance Scenarios**:

1. **Given** a 5th-Dan Hida being attacked, **When** the Hida elects to counterattack as an interrupt, **Then** 1 action die is spent and the attacker's attack roll gains +5 (sourced "Hida special ability: free raise to attacker").
2. **Given** a 3rd-Dan Hida with attack skill = 4 making a counterattack, **When** the counterattack roll resolves, **Then** up to 8 (2×4) low dice are rerolled with the trace showing which dice and the source ("Hida 3rd Dan: reroll 8 dice").
3. **Given** a 4th-Dan Hida at 30 LW with 0 SW out of 3 max SW, **When** facing a wound check, **Then** the Hida may choose to take 2 SW and reset LW to 0 (instead of rolling), with the trace showing the trade event.
4. **Given** a 5th-Dan Hida who successfully counterattacks an attack and the counterattack roll exceeded its TN by 7, **When** the Hida's WC fires on the damage they took, **Then** the WC roll has +7 added with source "Hida 5th Dan: counterattack excess +7".
5. **Given** a 5th-Dan Hida, **When** an opponent rolls damage, **Then** the Hida may elect to counterattack at that moment (deferred decision); the damage event resolves first (LW added + WC fires); then the counterattack roll happens against the original attacker, with the trace showing the temporal ordering.

### User Story 2 — Identity holds in mirror match (Priority: P1)

Two 5th-Dan Hidas face each other (the mirror match) and the combat terminates within the engine's safety bound (default 200 phases). No deadlock — both characters take damaging actions or are forced into them.

**Why this priority**: Principle IX (Strategy Defaults Must Be Playable). Hida's counterattack-heavy identity creates a degeneracy risk: two Hidas may both refuse to attack first, leading to action-die hoarding and infinite stalemate. The default strategy bindings MUST avoid this.

**Independent Test**: combat-simulator Scenario C (mirror non-degeneracy) — run 5 seeded mirror matches with deterministic rolls. Assert (a) all 5 terminate within the safety bound, (b) each character takes at least one attack action over the course of the match (identity engine fires), (c) no character ends with > 80% of starting action dice unspent (engagement criterion).

**Acceptance Scenarios**:

1. **Given** two 5th-Dan Hidas with identical builds, **When** combat begins, **Then** at least one attacks within the first 4 phases.
2. **Given** the mirror match, **When** the safety bound is reached or one character is impaired/killed, **Then** the match terminates (no infinite loop).

### User Story 3 — Hida wins ≥ 35% vs Akodo and Bushi baselines at matched XP (Priority: P1)

A 5th-Dan Hida at the spec-recommended XP allocation wins ≥ 35% of matches against a 5th-Dan Akodo and against the universal Bushi baseline at matched XP, across N seeds.

**Why this priority**: Principle IX (win-feasibility against baselines). Hida is itself a baseline (per BACKLOG.md), so its strategy bindings must be COMPETITIVE — not just "termination-safe". A 0% winrate against Akodo would indicate the school's defenses are over-tuned at the cost of offense.

**Independent Test**: combat-simulator Scenario B — run 20 seeds of {Hida vs Akodo, Hida vs Bushi-baseline} at matched XP (450 XP). Assert Hida wins ≥ 7/20 (35%) on both matchups.

**Acceptance Scenarios**:

1. **Given** 20 seeded Hida-vs-Akodo matches at 450 XP each, **When** all matches resolve, **Then** Hida wins ≥ 7 of them.
2. **Given** 20 seeded Hida-vs-Bushi-baseline matches at 450 XP each, **When** all matches resolve, **Then** Hida wins ≥ 7 of them.

### User Story 4 — Knack list correction propagates through the whole stack (Priority: P1)

`Hida Bushi School` rules text says the knacks are `counterattack, double attack, iaijutsu`. The skeleton currently says `counterattack, iaijutsu, lunge`. The wrong list propagates to `simulation/templates/generator.py` (XP template) and `HIDA_PRIORITIES` (progression order). All three sites must be fixed coherently.

**Why this priority**: Constitution Principle I (Engine Mirrors Rules Text). A wrong knack list is a rules-fidelity bug, not a polish item.

**Independent Test**: Grep for `lunge` in Hida-related code paths and assert zero matches. Build a Hida character via factory and assert its `school_knacks()` returns `["counterattack", "double attack", "iaijutsu"]`. The XP template generator must allocate XP into `double attack` for a Hida, not `lunge`.

**Acceptance Scenarios**:

1. **Given** a Hida character built via the factory, **When** `school_knacks()` is called, **Then** it returns `["counterattack", "double attack", "iaijutsu"]`.
2. **Given** the templates/strategies.py HIDA_PRIORITIES list, **When** parsed, **Then** every skill entry refers to a knack actually possessed by Hida (no "lunge").

### User Story 5 — trace-reader and trace-auditor approve the Hida trace (Priority: P2)

After implementation, a re-run of trace-reader (UX intuitiveness, 8 categories) and trace-auditor (Principle VII attribution audit) on a calibration combat involving Hida reports zero blockers and at most documented minor issues.

**Why this priority**: These are the new agents the user wants to exercise. Approving the Hida trace closes the validation loop.

**Independent Test**: After implementation, dispatch both agents on a calibration combat (Hida vs Akodo, seeded). Expected: zero "engine bug" or "Principle VII violation" reports.

**Acceptance Scenarios**:

1. **Given** the post-implementation calibration combat, **When** trace-auditor runs, **Then** it reports zero unattributed aggregates.
2. **Given** the post-implementation calibration combat, **When** trace-reader runs, **Then** it reports zero engine-bug suspicions.

### Edge Cases

- **3rd Dan reroll when impaired**: extra dice are halved (round up), but 10s still reroll despite impairment. Tested for both counterattack (N=2X) and other attack (N=X) cases.
- **3rd Dan reroll when no dice are below 5.5**: no dice are rerolled (the greedy chooser short-circuits). Trace should still record "Hida 3rd Dan reroll considered (no dice eligible)".
- **3rd Dan reroll: result of reroll is ALSO low**: no chain-reroll. One reroll per die per roll.
- **3rd Dan reroll on wound check, parry, feint**: NOT eligible. Rules say "counterattack or any other attack".
- **4th Dan SW-for-LW with LW = 0**: short-circuit; no trade.
- **4th Dan SW-for-LW with < 2 SW available (would kill character)**: not allowed; fall back to normal WC.
- **4th Dan SW-for-LW during iaijutsu first-strike phase, Hida IS the duelist**: NOT allowed (rules explicit). Falls back to normal WC.
- **4th Dan SW-for-LW during iaijutsu first-strike phase, Hida is bystander**: allowed (Hida is not the one in the duel phase).
- **5th Dan WC bonus stacking**: if the original attacker is also a Hida 5th Dan who successfully counterattacks-the-counterattack, only the outermost counterattack's margin counts.
- **5th Dan post-damage counterattack: defender dies BEFORE counterattacking**: the counterattack does not fire (defender unable to act).
- **5th Dan post-damage counterattack: counterattack kills the original attacker AFTER damage resolved**: the defender's already-taken damage stands; attacker dies; combat continues with remaining combatants.
- **Knack-list correction**: a Hida character that previously had XP spent into "lunge" (via cached YAML configs) should NOT silently swallow the wrong skill. Strategy: warn-and-default per `BaseSchool.choice()` semantics if encountered; tests will exercise the corrected list.

## Requirements *(mandatory)*

### Functional Requirements

**Special Ability (re-verify, mostly already implemented)**

- **FR-001**: Hida MUST be able to counterattack as an interrupt for exactly 1 action die (vs the engine default of 2). Engine wiring: `set_interrupt_cost("counterattack", 1)` + `CounterattackInterruptStrategy` already in skeleton.
- **FR-002**: When the Hida uses the 1-die interrupt counterattack, the attacker MUST receive +5 to their attack roll (a free raise per L7R), sourced in the trace as "Hida special ability: free raise to attacker (+5) for 1-die interrupt counterattack". The +5 MUST appear on the attack-roll trace line, not buried in an aggregate.

**1st Dan + 2nd Dan (verify only)**

- **FR-003**: A 1st-Dan Hida MUST roll one extra die on attack, counterattack, and wound check rolls. The existing `extra_rolled()` returns these three already; test coverage must verify the dice are actually added at roll time, with attribution in the trace ("Hida 1st Dan: +1k0 attack" etc.).
- **FR-004**: A 2nd-Dan Hida MUST get a free raise on counterattack rolls. Existing `free_raise_skills()` returns `["counterattack"]`; verify via tests that the +5 is applied to counterattack rolls and sourced in the trace.

**3rd Dan (NEW)**

- **FR-005**: A 3rd-Dan Hida MAY reroll up to `2 × attack_skill` dice on a counterattack roll, or up to `attack_skill` dice on any other attack roll.
- **FR-006**: The 3rd-Dan reroll selects the lowest-value dice (greedy), only rerolling dice that came up below 5.5 expected value, up to the N cap.
- **FR-007**: When impaired, the 3rd-Dan reroll's N (the dice count) MUST be halved rounding up. Separately, the 3rd-Dan reroll MUST allow 10s to reroll on these specific rolls even when impaired (overriding the normal impaired no-explode rule). Other impaired penalties (e.g., dice cuts on the base roll) still apply.
- **FR-008**: The 3rd-Dan reroll MUST NOT apply to wound check, parry, feint, or non-attack rolls.
- **FR-009**: The 3rd-Dan reroll MUST NOT chain — if a die's reroll yields another low value, that die is NOT rerolled again on the same roll.
- **FR-010**: Each invocation of the 3rd-Dan reroll MUST appear in the trace with: (a) the source ("Hida 3rd Dan: reroll N dice on counterattack/attack"), (b) the dice values rerolled (before → after), (c) the new total. Per Principle VII.

**4th Dan (PARTIAL → COMPLETE)**

- **FR-011**: A 4th-Dan Hida's current Water ring AND maximum Water ring are raised by 1 at the moment of attaining 4th Dan. Raising Water costs 5 fewer XP for them. Existing `apply_school_ring_raise_and_discount` handles this — verify coverage.
- **FR-012**: A 4th-Dan Hida MAY, instead of making a wound check, elect to take 2 serious wounds to reset light wounds to 0.
- **FR-013**: The 4th-Dan SW-for-LW trade MUST NOT be available during the iaijutsu first-strike phase if the Hida is the duelist. Bystanders watching a duel are unaffected.
- **FR-014**: The 4th-Dan SW-for-LW trade MUST NOT be selected if LW = 0 (nothing to reduce) or if SW + 2 ≥ max_sw (would kill the Hida).
- **FR-015**: The 4th-Dan SW-for-LW trade MUST produce a distinct trace event ("Hida 4th Dan: take 2 SW to reset LW from N → 0") instead of a normal wound check event.
- **FR-016**: A Hida-specific subclass of `WoundCheckStrategy` MUST decide when to take the trade — using the existing "tolerable_sw" heuristic plus the pre-conditions in FR-013/FR-014. Implementer may refine the heuristic; log to OPEN_QUESTIONS.md.

**5th Dan (NEW)**

- **FR-017**: A 5th-Dan Hida MAY elect to counterattack AFTER the opponent's damage roll has been rolled (but before its damage is applied to the Hida's LW). Implementation: a new post-damage-roll interrupt slot. The action die is reserved on entering "see damage first" mode and committed on counterattack-decision.
- **FR-018**: If the 5th-Dan Hida elects to counterattack post-damage-roll, the damage event MUST resolve fully (LW added, WC fires, SW may be inflicted) BEFORE the counterattack roll happens. The counterattack's effect on the original attacker (impair/kill) does NOT retroactively cancel the damage to the Hida.
- **FR-019**: When a 5th-Dan Hida's counterattack roll succeeds (≥ TN), the excess (`roll - TN`) MUST be stored on the originating attack action and added to the Hida's wound check roll on the damage from that attack. The bonus MUST be sourced in the trace ("Hida 5th Dan: counterattack excess +X").
- **FR-020**: The 5th-Dan WC bonus applies ONLY to the Hida's OWN wound check on the damage they took from the counterattacked attack. It does NOT apply to other wound checks they make.
- **FR-021**: If a counterattacked attacker is themselves a Hida 5th-Dan who counterattacks-the-counterattack and wins, only the outermost counterattack's margin counts (stacking limit).

**Knack list correction (Constitution Principle I)**

- **FR-022**: `HidaBushiSchool.school_knacks()` MUST return `["counterattack", "double attack", "iaijutsu"]`.
- **FR-023**: `simulation/templates/generator.py:35` MUST list `["counterattack", "double attack", "iaijutsu"]` for the Hida entry.
- **FR-024**: `HIDA_PRIORITIES` in `simulation/templates/strategies.py` MUST refer only to skills Hida actually has (no `"lunge"`); the school-progression-designer agent's proposal is applied verbatim.

**Identity-driven strategy bindings (Constitution Principle VIII + IX)**

- **FR-025**: Default Hida initiative, attack, parry, counterattack-interrupt, wound-check, and floating-bonus strategies MUST be selected by the school-strategy-designer agent's proposal (subject to mirror non-degeneracy verification per Principle IX). Implementer applies the proposal verbatim or flags disagreement to OPEN_QUESTIONS.md.
- **FR-026**: The default strategy bindings MUST satisfy mirror non-degeneracy: two default Hidas in a mirror match MUST terminate within 200 phases AND each MUST take at least one attack-action during the match.
- **FR-027**: The default strategy bindings MUST satisfy win-feasibility: a default Hida at 450 XP MUST win ≥ 35% of matches vs default Akodo (450 XP) and vs universal Bushi baseline (450 XP) across 20 seeds.

**XP progression (Constitution Principle VIII)**

- **FR-028**: `HIDA_PRIORITIES` MUST be revised per the school-progression-designer agent's proposal, with per-entry rationale citing Hida's mechanics (Water ring priority, counterattack/wound-check skill priority, Earth ring for defender HP buffer, etc.).

**Trace observability (Constitution Principle VII)**

- **FR-029**: Every Hida-specific effect (special ability +5, 1st-Dan extra dice, 2nd-Dan free raise, 3rd-Dan reroll, 4th-Dan SW-for-LW trade, 5th-Dan WC bonus, 5th-Dan post-damage counterattack timing) MUST be visible in the trace with explicit attribution. No aggregate values without source attribution.
- **FR-030**: The 5th-Dan post-damage counterattack timing MUST appear in the trace as discrete events: (a) damage roll, (b) damage application + WC, (c) Hida elects to counterattack, (d) counterattack roll resolves against the original attacker.

**Engine touch-points (implementer-flagged)**

- **FR-031**: A new "reroll N selected dice" capability MUST be added to the roll-extension pipeline (for 3rd Dan). Implementation hooks into roll-params normalization without breaking existing reroll mechanisms.
- **FR-032**: A `context.in_iaijutsu_phase() -> bool` accessor MUST be exposed if not already, for the 4th-Dan iaijutsu-phase guard. If the iaijutsu duel engine doesn't currently set this, add the setter at the appropriate iaijutsu-duel phase boundary.
- **FR-033**: A new event type or extension to existing wound-check event MUST capture the 4th-Dan SW-for-LW trade — a distinct trace event, not a wound-check event with overrides.
- **FR-034**: The originating attack action MUST be able to store a "counterattack excess" margin (analogous to the existing `_counterattack_roll_bonus`) that the WC roll on the resulting damage can consult.
- **FR-035**: A new interrupt slot (or refactored interrupt sequencing) MUST allow a counterattack to fire AFTER a damage roll has been made but BEFORE the damage is applied to the defender's LW. (For 5th Dan.)

**Cross-cutting**

- **FR-036**: `simulation/` modules MUST NOT import from `web/`.
- **FR-037**: Coverage on all new Hida-specific code MUST reach 100% per Constitution Principle VI v1.3.0, with any pragma skips documented (per `tests/test_coverage_pragma_audit.py`).
- **FR-038**: ≤ 5 existing tests may be updated; flag for review if exceeded.

### Key Entities

- **HidaBushiSchool**: school class. Existing skeleton at `simulation/schools/hida_school.py`. Needs knack-list fix + 3 new Dan ability implementations + 4th-Dan WC strategy override + 5th-Dan counterattack interrupt strategy override.
- **HidaThirdDanReroll**: new mechanism (likely a roll-extension or roll-params modifier) that reroll-selects up to N dice on counterattacks (N=2X) and other attacks (N=X) per Hida 3rd Dan.
- **HidaWoundCheckStrategy** (or `Hida4thDanWoundCheckStrategy`): new subclass of `WoundCheckStrategy`. Decides between rolling the WC and taking the 2-SW-for-LW-reset trade.
- **HidaSWForLWTradeEvent** (or extension to existing wound-check event): records the 4th-Dan trade in the trace.
- **HidaCounterattackInterruptStrategy** (or extension to `CounterattackInterruptStrategy`): adds the 5th-Dan post-damage-roll interrupt point and the WC-excess-bonus storage.
- **HIDA_PRIORITIES**: XP progression list in `simulation/templates/strategies.py`. Currently uses wrong "lunge" knack — must be revised per school-progression-designer proposal.
- **Knack template entry**: `simulation/templates/generator.py:35` — fix the knack list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 3 currently-TODO Dan abilities (3rd, 4th alternative WC, 5th) are implemented, with each producing distinct trace events.
- **SC-002**: Knack list reads `["counterattack", "double attack", "iaijutsu"]` in all three call sites (school class, generator template, HIDA_PRIORITIES). Zero `grep -r '"lunge"'` matches in Hida-relevant code paths.
- **SC-003**: 100% test coverage on the new Hida code (Constitution Principle VI v1.3.0). All pragma skips documented per the coverage-audit meta-test.
- **SC-004**: combat-simulator Scenario A (3rd/4th/5th Dan rules exercise) — for each of the 3 new Dan abilities, at least one scripted combat shows the ability firing with correct trace attribution.
- **SC-005**: combat-simulator Scenario B (win-feasibility) — default Hida wins ≥ 7/20 (35%) vs default Akodo at 450 XP AND ≥ 7/20 vs universal Bushi baseline at 450 XP.
- **SC-006**: combat-simulator Scenario B.2 (action-disadvantage) — Hida defeated to single-die starvation eventually loses but does not deadlock; combat terminates within safety bound.
- **SC-007**: combat-simulator Scenario C (mirror non-degeneracy) — 5 seeded Hida-vs-Hida mirror matches all terminate within safety bound AND each character takes ≥ 1 attack action.
- **SC-008**: combat-simulator Scenario D (round-robin) — Hida finishes with ≥ 30% winrate across schools-already-validated (Mirumoto, Ishi, Akodo) at 450 XP each.
- **SC-009**: rules-auditor reports zero rules-fidelity discrepancies in the final implementation diff.
- **SC-010**: trace-auditor reports zero Principle VII violations in the Hida-involved trace.
- **SC-011**: trace-reader reports zero engine-bug suspicions on the Hida calibration combat.
- **SC-012**: `env/bin/ruff check .` PASS; `env/bin/mypy` strict PASS; `env/bin/pytest tests/ -v` all 3784+ tests PASS.
- **SC-013**: New test count: 50-80 tests added (per estimate); existing tests updated: ≤ 5 (per Constitution updates cap). Flag if either bound is exceeded.

## Assumptions

- The L7R "free raise" mechanic = +5 to the affected roll (well-established in the existing engine; see `simulation/strategies/base.py` "free raise" handling).
- The iaijutsu duel engine (committed 2026-05-26 per `5d67a78`) exposes (or can be extended to expose) the first-strike phase via context.
- The roll-extension pipeline supports adding a new "reroll N selected dice" capability without breaking existing reroll mechanisms (Merchant 5th Dan, WaveMan, Ninja).
- The `WoundCheckStrategy` base class is extensible (it has subclasses like `WoundCheckStrategy02`, `WoundCheckStrategy04`, `WoundCheckStrategy05`, `WoundCheckStrategy08`, `StingyWoundCheckStrategy`).
- The `CounterattackInterruptStrategy` base class is extensible to a 5th-Dan variant (it's a Strategy subclass at `simulation/strategies/base.py:743`).
- The existing `_counterattack_roll_bonus` pattern on attack actions is reusable for the 5th-Dan "counterattack excess → WC bonus" mechanism.
- 50-80 new tests is feasible within the spec's scope; ≤ 5 existing-test updates is achievable given the additive nature of the changes (only knack-list and HIDA_PRIORITIES updates touch existing data; the rest are new behavior).
- The school-strategy-designer and school-progression-designer agent proposals are accepted verbatim unless the implementer finds a concrete reason to deviate (logged to OPEN_QUESTIONS.md).

## Out of scope

- Engine refactors not directly motivated by Hida's mechanics (e.g., overhauling the roll-extension pipeline beyond adding "reroll N selected dice").
- Iaijutsu duel engine internals beyond exposing the phase via `context.in_iaijutsu_phase()`.
- Re-validating other schools' implementations after the knack-list correction propagates through `templates/generator.py`. (The fix is isolated to the Hida entry; no other school is affected.)
- Changes to the existing Special Ability handling beyond the docstring/sourcing wording.
- Constitution amendments.
- Adding new agents or pipelines.
- Streamlit UI changes beyond what naturally flows from the corrected trace output.
- Re-implementing or revising Mirumoto, Ishi, or Akodo schools.
