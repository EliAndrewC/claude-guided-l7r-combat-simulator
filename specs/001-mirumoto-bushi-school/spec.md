# Feature Specification: Mirumoto Bushi School

**Feature Branch**: `001-mirumoto-bushi-school`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "Implement the Mirumoto Bushi school per the upstream rules file `rules/04-schools.md` in https://github.com/EliAndrewC/l7r (section 'Mirumoto Bushi School'), with all five dan ranks plus the school's special ability, wired into the simulator's existing factory and decision-strategy machinery so the school is end-to-end testable via the combat harness."

**Rules Source**: [`rules/04-schools.md`, section "Mirumoto Bushi School"](https://github.com/EliAndrewC/l7r/blob/master/rules/04-schools.md) — the authoritative specification per Constitution Principle III.

## Clarifications

### Session 2026-05-25

- Q: Special Ability — when is the temporary void point usable, and does it stack above the normal Void cap? → A: Usable immediately (same round); stacks above the normal Void cap; discarded at end of combat.
- Q: Third Dan — how do point-spends combine on the same action or roll? → A: Both modes stack freely; multiple phase-lower spends on one action lower it by that many phases (floor ≥ 1); multiple +2 spends on one roll add +2 per point; a phase-lowered action's parry roll can also receive +2 bonuses.
- Q: Fourth Dan — what does "Failed parries against your double attacks do not prevent the automatic serious wound" actually do? → A: Narrow scope. The auto-serious-wound lands on a defender who failed their parry against your double attack. Only the auto-SW prevention is removed; other failed-parry mitigation against the double attack (e.g., standard damage-dice handling) works as it normally does.
- Q: Fifth Dan — when multiple void points are spent on the same combat roll, does the +10 apply per point or per roll? → A: Per void point. Each void point spent on a combat roll provides +10 on top of its normal void-spend bonus (e.g., 2 points = +20, 3 points = +30).
- Q: Does the Fifth Dan +10 apply when a 5th-dan Mirumoto Bushi spends a temporary void point (from the Special Ability) on a combat roll? → A: Yes. A void point is a void point. Temporary voids are functionally identical to normal voids once granted; both provide the +10 on combat rolls. No provenance tracking required.

### Session 2026-05-26 (post-implementation review)

- Q: Fifth Dan — is the "+10" a flat modifier ON TOP OF the standard void-spend's +1 rolled / +1 kept, or does it REPLACE the standard with a +10-valued bonus? → A: ON TOP OF. The standard `+1r/+1k` from a void point still applies; the Fifth Dan adds a *separate* +10 to the roll's modifier per VP spent. Example: a Mirumoto Bushi spending a VP on a 6k4 wound check ends up rolling 7k5 + 10 total.
- Q: Fifth Dan — what exactly counts as a "combat roll" eligible for the +10? → A: Any attack-class skill roll (attack, double attack, counterattack, feint, iaijutsu, lunge), parry roll, or wound check roll — i.e., anything the Mirumoto rolls in the course of combat. The whitelist intentionally includes attack-class skills the Mirumoto might not have as school knacks (feint, lunge) in case the character acquires them later; the only thing excluded is genuinely non-combat skill checks.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Build and Run a Mirumoto Bushi with Passive Abilities (Priority: P1)

A simulator user constructs a character whose school is "Mirumoto Bushi" at any dan rank from 1 to 5, drops them into the existing combat harness against an arbitrary opponent, and observes that the Special Ability, First Dan, and Second Dan all take effect automatically without any per-action user intervention. This is the MVP: it establishes the school exists in the factory, its school ring and school knacks are correct, and the simpler passive modifiers fire when they should.

**Why this priority**: Without this slice, no Mirumoto Bushi can be instantiated at all. It also exercises the lowest-risk subset of the mechanics (purely passive bonuses), which is the right foundation for the harder abilities. It is also the prerequisite for every other story.

**Independent Test**: Construct a 1st-dan Mirumoto Bushi, schedule a series of parry actions against scripted attacks, and confirm via the existing combat trace that (a) the school is registered and selectable, (b) the school ring is Void, (c) school knacks counterattack, double attack, and iaijutsu are present, (d) every parry roll uses one extra die (1st Dan) and a free raise (2nd Dan), (e) wound checks and double attacks also roll one extra die (1st Dan), and (f) every parry attempt — success or failure — grants the character a temporary void point usable in subsequent rolls.

**Acceptance Scenarios**:

1. **Given** a freshly constructed 1st-dan Mirumoto Bushi, **When** the character is asked for its school ring, **Then** the answer is Void.
2. **Given** a 1st-dan Mirumoto Bushi, **When** the character is asked which school knacks they have, **Then** the set contains exactly counterattack, double attack, and iaijutsu.
3. **Given** a 1st-dan Mirumoto Bushi making a parry roll, **When** the parry roll is constructed, **Then** the number of dice rolled is one greater than the same character would roll without the school's First Dan bonus.
4. **Given** a 1st-dan Mirumoto Bushi making a double-attack roll or a wound check, **When** the roll is constructed, **Then** the number of dice rolled is one greater than the same character would roll without the school's First Dan bonus.
5. **Given** a 2nd-dan Mirumoto Bushi making a parry roll, **When** the parry roll is constructed, **Then** the roll includes one free raise that the character did not pay for and that did not consume any normal raise budget.
6. **Given** a Mirumoto Bushi (any dan) who attempts a parry, **When** the parry resolves (whether successfully or not), **Then** the character's available void point count is incremented by one temporary point, and that point is usable for any subsequent void-spending decision until end of combat.

---

### User Story 2 — Mirumoto Bushi at Third Dan with Active Point-Spending Decisions (Priority: P2)

A simulator user constructs a 3rd-dan-or-higher Mirumoto Bushi and runs combat. At the start of each round the character receives a per-round pool of 2 × attack-skill points; each point is spent either to lower the phase of one scheduled action by 1 (converting that action into a parry) or to add +2 to an attack or parry roll after the roll has been seen. The simulator's decision logic must make these spending choices automatically based on the active strategy, not by user prompt. Unused points are lost at end of round.

**Why this priority**: This is the first ability that requires Principle V (pluggable decisions) to do real work — it is not a passive modifier but an actively-spent resource pool with two distinct spending modes. It is also the ability most likely to interact subtly with phase scheduling and roll resolution, so isolating it as its own slice makes regressions easier to attribute. It is P2 (not P1) because a 1st- or 2nd-dan Mirumoto Bushi is already useful for testing without it.

**Independent Test**: Construct a 3rd-dan Mirumoto Bushi with attack skill 4 (so pool size = 8), schedule them against an opponent in a deterministic combat, and confirm via trace that (a) the pool is created with 8 points at the start of each round, (b) the active strategy spends some points to lower scheduled action phases (converting those actions to parries) and some points to apply +2 bonuses to specific rolls after those rolls are visible, (c) the pool is reset to 8 at the start of the next round regardless of how many points were unspent, and (d) any unspent points are discarded, not banked.

**Acceptance Scenarios**:

1. **Given** a 3rd-dan Mirumoto Bushi with attack skill X at the start of a round, **When** the round begins, **Then** their Third Dan point pool contains exactly 2 × X points.
2. **Given** a 3rd-dan Mirumoto Bushi with at least 1 point in their Third Dan pool and a scheduled action at phase P > 1, **When** the active strategy elects to spend a point to lower that action's phase, **Then** the action's phase becomes P − 1, the action is treated as a parry, and the pool is decremented by 1.
3. **Given** a 3rd-dan Mirumoto Bushi with at least 1 point in their Third Dan pool who has just rolled an attack or parry roll, **When** the active strategy elects to spend a point for the +2 bonus, **Then** the roll's total is increased by 2 and the pool is decremented by 1.
4. **Given** a 3rd-dan Mirumoto Bushi whose Third Dan pool has unspent points at the end of a round, **When** the next round begins, **Then** the pool is reset to 2 × attack-skill points (the unspent points are lost, not carried).
5. **Given** a 3rd-dan Mirumoto Bushi with attack skill 0, **When** the round begins, **Then** their Third Dan pool contains 0 points and no spending decisions are offered.

---

### User Story 3 — Mirumoto Bushi at Fourth Dan with Damage and Void Modifiers (Priority: P2)

A simulator user constructs a 4th-dan-or-higher Mirumoto Bushi and observes that (a) the character's current and maximum Void are each one higher than they would otherwise be, (b) raising Void via XP costs 5 less than the standard cost, (c) defenders who fail to parry the character's double attack still take the automatic serious wound that double attacks confer, and (d) defenders who fail to parry the character's regular attack receive only half (rounded down) the damage-die-count reduction that a failed parry normally provides.

**Why this priority**: Fourth Dan touches the damage and Void subsystems, both of which already exist in the engine. It is conceptually separable from Third Dan's point pool, so implementing it as a distinct slice lets us verify each subsystem in isolation. P2 because, like Third Dan, the school is already useful without it.

**Independent Test**: Construct a 4th-dan Mirumoto Bushi alongside a baseline character of equal stats and dan rank from a different school; confirm via stat-snapshot tests that the Mirumoto's Void is +1 in both current and maximum compared to baseline; confirm via XP-cost test that raising Void costs 5 less; run two scripted combats — one with the Mirumoto making a double attack and the defender failing to parry, and one with the Mirumoto making a regular attack and the defender failing to parry — and confirm the defender outcomes match the Fourth Dan modifications.

**Acceptance Scenarios**:

1. **Given** a 4th-dan Mirumoto Bushi constructed with otherwise-identical inputs to a 4th-dan character of any other school, **When** their current Void and maximum Void are queried, **Then** both are exactly 1 higher than the baseline character's.
2. **Given** a 4th-dan Mirumoto Bushi at any Void rank, **When** the XP cost to raise that character's Void by one is queried, **Then** the cost is 5 less than the standard L7R Void-raise cost for that rank (with a floor of 0 if subtraction would go negative).
3. **Given** a defender who fails to parry a 4th-dan Mirumoto Bushi's double attack, **When** the attack resolves, **Then** the defender receives the automatic serious wound that double attacks confer (the failed parry no longer prevents it); other defensive effects of the failed parry against the double attack apply as they normally would.
4. **Given** a defender who fails to parry a 4th-dan Mirumoto Bushi's regular attack, **When** the attack resolves, **Then** the number of damage dice the failed parry would normally remove from the attack roll is halved (rounded down via integer floor — e.g., 5 → 2, 3 → 1, 1 → 0).

---

### User Story 4 — Mirumoto Bushi at Fifth Dan with Void Bonus on Combat Rolls (Priority: P3)

A simulator user constructs a 5th-dan Mirumoto Bushi and observes that every time the character spends a void point on a combat roll, that roll's total is +10 higher than the standard void-spend bonus would provide on its own.

**Why this priority**: Fifth Dan is the simplest mechanic of the school (a single additive modifier on void-spending) and is the highest-rank ability, so it is the lowest-frequency in playtesting. P3 reflects that it is small in scope and the last to be reached in character progression.

**Independent Test**: Construct a 5th-dan Mirumoto Bushi, force the character to spend a void point on a combat roll in a scripted combat, and confirm via trace that the roll's total includes both the standard void-spend bonus and an additional +10. Repeat for a non-combat roll (e.g., a wound check is treated as a combat roll per the rules; a skill roll outside combat is not) and confirm the +10 does not apply to non-combat rolls.

**Acceptance Scenarios**:

1. **Given** a 5th-dan Mirumoto Bushi who spends a void point on an attack roll, **When** the roll's total is computed, **Then** it includes the standard void-spend bonus plus an additional +10.
2. **Given** a 5th-dan Mirumoto Bushi who spends a void point on a parry roll, **When** the roll's total is computed, **Then** it includes the standard void-spend bonus plus an additional +10.
3. **Given** a 5th-dan Mirumoto Bushi who spends a void point on a wound check, **When** the roll's total is computed, **Then** it includes the standard void-spend bonus plus an additional +10.
4. **Given** a 5th-dan Mirumoto Bushi who spends a void point on a non-combat roll, **When** the roll's total is computed, **Then** it includes only the standard void-spend bonus (no +10).

---

### Edge Cases

- A 3rd-dan Mirumoto Bushi with attack skill 0 has a Third Dan pool of 0 points; no spending decisions are offered. Pool initialization must not divide-by-zero or fail.
- A 3rd-dan Mirumoto Bushi's scheduled action is already at phase 1; spending a point to lower its phase is not a legal move (cannot go below 1). The decision logic must skip such actions when evaluating phase-lowering spends.
- A 4th-dan Mirumoto Bushi whose standard Void-raise cost is already at the floor (≤ 5); the 5-XP reduction must not produce a negative cost. Treat as 0 in that case.
- A 4th-dan Mirumoto Bushi's regular attack against a defender whose failed parry would remove 1 damage die: half of 1 rounded down is 0, so the failed parry removes 0 damage dice.
- A Mirumoto Bushi (any dan) whose normal Void pool is already at its cap when a parry resolves; the temporary void point granted by the Special Ability stacks on top of the cap (it is "temporary", lost at end of combat, not subject to the normal pool cap).
- Multiple parries in the same round each grant their own temporary void point — there is no per-round limit on the Special Ability.
- A 5th-dan Mirumoto Bushi who spends multiple void points on the same combat roll: the +10 applies once per void point spent (i.e., +20 if two are spent on the same roll), consistent with the additive nature of the standard void bonus.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST register a school named "Mirumoto Bushi" in the existing school factory so it is selectable by the same mechanism as the schools already implemented.
- **FR-002**: A Mirumoto Bushi character MUST report Void as its school ring.
- **FR-003**: A Mirumoto Bushi character MUST report exactly the set {counterattack, double attack, iaijutsu} as its school knacks.
- **FR-004**: A Mirumoto Bushi character of any dan, on any parry attempt (successful or failed), MUST gain one temporary void point that is usable for any subsequent void-consuming roll within the same combat. Temporary void points are not subject to the character's normal Void pool maximum and are discarded at end of combat. (Special Ability)
- **FR-004a**: Temporary void points granted by FR-004 MUST be functionally indistinguishable from normal void points once granted. They MAY be spent on any roll that accepts a void point, they participate in the Fifth Dan +10 bonus (FR-014) on combat rolls when their owner is at 5th dan, and the engine MUST NOT track void-point provenance after the grant. (Special Ability × Fifth Dan interaction)
- **FR-005**: A Mirumoto Bushi character of 1st dan or higher MUST roll one extra die on every parry roll, double-attack roll, and wound check. (First Dan)
- **FR-006**: A Mirumoto Bushi character of 2nd dan or higher MUST receive one free raise on every parry roll. The free raise is in addition to any raises the character pays for and does not consume any normal raise budget. (Second Dan)
- **FR-007**: A Mirumoto Bushi character of 3rd dan or higher MUST receive a pool of (2 × attack-skill) points at the start of every round. Points are spendable in two distinct modes (FR-008, FR-009). Unspent points are discarded at end of round. (Third Dan)
- **FR-008**: A point from the Third Dan pool MAY be spent to lower the phase of one of the character's scheduled actions by 1, converting that action into a parry. The spend is illegal if the target action is already at phase 1. (Third Dan, mode A)
- **FR-009**: A point from the Third Dan pool MAY be spent to add +2 to one of the character's attack rolls or parry rolls. The spend MUST be declarable *after* the roll's dice have been resolved and inspected. (Third Dan, mode B)
- **FR-009a**: Third Dan spends stack and combine without restriction: (i) multiple mode-A spends MAY target the same action, each lowering its phase by 1 further (floor: phase ≥ 1); (ii) multiple mode-B spends MAY target the same roll, each adding a further +2; (iii) the two modes MAY both be applied to the same action — phase-lowering the action via mode A, then adding mode-B bonuses to that action's parry roll after it is rolled. (Third Dan, stacking & combination)
- **FR-010**: A Mirumoto Bushi character of 4th dan or higher MUST have their current and maximum Void increased by 1, applied at character construction. (Fourth Dan, part 1)
- **FR-011**: A Mirumoto Bushi character of 4th dan or higher MUST have the XP cost of raising Void reduced by 5 relative to the standard cost, with a floor of 0. (Fourth Dan, part 2)
- **FR-012**: When a defender's parry against a 4th-dan-or-higher Mirumoto Bushi's double attack fails, the defender MUST receive the automatic serious wound that double attacks confer; the failed parry's other defensive effects against the double attack (e.g., any standard damage-dice handling) apply as they normally would. Only the prevention of the automatic serious wound is removed. (Fourth Dan, part 3)
- **FR-013**: When a defender's parry against a 4th-dan-or-higher Mirumoto Bushi's regular attack fails, the number of damage dice the failed parry would normally remove from the attack roll MUST be halved using integer floor (e.g., 5 → 2, 3 → 1, 1 → 0). (Fourth Dan, part 4)
- **FR-014**: When a 5th-dan Mirumoto Bushi spends a void point on a combat roll, the roll's total MUST include an additional +10 modifier on top of the standard void-spend bonus, per void point spent. The +10 is a flat modifier addition — it is *on top of* the standard `+1 rolled / +1 kept` dice that a spent void point provides per the base rules; it does not replace those dice. "Combat roll" means any attack-class skill roll (attack, double attack, counterattack, feint, iaijutsu, lunge), parry roll, or wound check roll — i.e., anything the Mirumoto rolls in the course of combat. Non-combat skill checks (investigation, courtier, etc.) do NOT receive the +10. (Fifth Dan)
- **FR-015**: All Mirumoto Bushi mechanics MUST be implemented as pluggable decision/strategy/ability components per Constitution Principle V, not by hardcoding branches into the combat loop. The Third Dan pool's spending choices MUST be selected by a strategy object that is interchangeable with strategies for other schools.
- **FR-016**: All Mirumoto Bushi mechanics MUST use the existing injectable-randomness providers (Constitution Principle IV); no new direct call to `random.*` is permitted in the school's implementation.
- **FR-017**: Every functional requirement above MUST cite the corresponding ability name from `rules/04-schools.md` so the mapping from rules text to implementation is auditable (Constitution Principle III).

### Key Entities

- **MirumotoBushiSchool**: A school registered with the existing school factory. Identifies its ring (Void), its school knacks (counterattack, double attack, iaijutsu), and the per-dan abilities it confers on its members.
- **MirumotoBushiSpecialAbility**: A passive observer that, every time a parry resolves for its owner, grants a temporary void point.
- **MirumotoBushiThirdDanPool**: A per-round resource owned by the character; tracks remaining points; supports two spend operations (phase-lowering, post-roll +2 bonus); reset to 2 × attack-skill at start of round; discarded at end of round.
- **MirumotoBushiThirdDanStrategy**: A pluggable decision component that chooses when and how to spend pool points; interchangeable with the analogous strategy objects of other schools.
- **MirumotoBushiFourthDanModifiers**: Static modifications to character stat construction (Void +1) and XP cost calculation (Void cost −5), plus combat-resolution hooks for the auto-serious-wound and halved-damage-die-reduction rules.
- **MirumotoBushiFifthDanModifier**: A modifier applied during combat-roll resolution whenever a void point is spent by a 5th-dan member.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Mirumoto Bushi character of any dan rank from 1 to 5 can be instantiated, dropped into the existing combat harness, and run to combat resolution without producing a runtime error or violating an engine invariant.
- **SC-002**: The school's mechanics-versus-rules-text mapping is 100% complete: every clause of the "Mirumoto Bushi School" section in `rules/04-schools.md` corresponds to at least one acceptance scenario and at least one functional requirement in this spec, and every acceptance scenario passes when its corresponding implementation lands.
- **SC-003**: All unit tests for the school pass deterministically (no flakes across 100 consecutive runs) when the engine's roll provider is configured with a fixed seed or a predestined die source.
- **SC-004**: Project-wide line coverage remains above the 90% floor mandated by the constitution after the school's implementation lands.
- **SC-005**: `env/bin/ruff check .`, `env/bin/mypy`, and `env/bin/pytest tests/ -v` all pass with zero errors / zero failures on the branch before merge (Constitution Quality Gates).
- **SC-006**: A combat trace of a Mirumoto Bushi (any dan) is interpretable by a reviewer who has the rules file open — every dan-specific effect appears in the trace with enough context that the reviewer can match it to a rules clause without consulting the source code.

## Assumptions

The five ambiguities the user explicitly flagged for clarification have been resolved and are recorded in the `## Clarifications` section above. The remaining items below are working defaults that the clarify pass deliberately did not surface as questions — either because the rule text was unambiguous (e.g., "rounded down" = integer floor), because they are out-of-scope boundaries, or because they are implementation-vocabulary choices best confirmed during `/speckit-plan` against the actual codebase.

- **First Dan — what counts as a "wound check"**: All wound-check rolls the character makes against incoming damage qualify, including those triggered by the automatic serious wound of a double attack against them.
- **Third Dan — action-priority ties**: When phase-lowering produces a tie between this character's action and another character's action at the same phase, the existing engine tie-breaker applies; this school introduces no new tie-breaker.
- **Fourth Dan — damage-die-reduction halving (clarify candidate 4)**: "Rounded down" is interpreted as standard integer floor (Python `//` on non-negative integers): 5 → 2, 3 → 1, 1 → 0.
- **Implementation surface**: The school is added alongside the existing implemented schools under whatever directory currently houses them (`simulation/schools/` per the constitution's description) and registered through the existing factory mechanism. Active-decision components (the Third Dan pool spends) live alongside the existing optimizer/strategy modules.
- **Out of scope for this feature**: No changes to the Between Place or Spirit Encounter rules (Constitution scope boundary). No new randomness provider (Principle IV — use existing ones). No UI/Streamlit changes are *required* for this feature to be considered complete, though a future feature may add a Streamlit page to inspect a Mirumoto Bushi character's per-round state.
- **Existing schools as a pattern reference**: The implementation follows the factory-registration and decision-strategy patterns established by previously-implemented schools; if those patterns prove inadequate for any Mirumoto-Bushi-specific concern, the gap is flagged in `/speckit-plan` rather than papered over.
