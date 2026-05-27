# Feature Specification: Akodo Bushi School

**Feature Branch**: `005-akodo-bushi-school`

**Created**: 2026-05-27

**Status**: Draft (autonomous run)

**Input**: User direction (2026-05-27): "implement the next school" with reference to BACKLOG.md (Akodo Bushi is topmost unchecked, also a Principle IX playability baseline).

**Rules Source**: `rules/04-schools.md` § "Akodo Bushi School" at
`https://github.com/EliAndrewC/l7r/blob/master/rules/04-schools.md` —
authoritative per Constitution Principle III. The full verbatim text
is mirrored in `specs/004-akodo-bushi-school/research.md` for offline
reference once `/speckit-plan` runs.

**Run Mode**: Autonomous. Decisions logged in `OPEN_QUESTIONS.md` for end-of-run user review.

**Why this school matters**: Akodo Bushi is one of two Principle IX playability baselines (alongside Hida Bushi). Every other school's win-feasibility test in `combat-simulator` Scenario B assumes Akodo behaves correctly. A bug here propagates silently to every downstream school audit. Treat correctness defects as P0.

## Clarifications

### Session 2026-05-27 (autonomous; pre-answered per project conventions)

- Q: When the 4th Dan WC-raise strategy has multiple VP spend amounts that yield the same minimum expected SW (i.e., further spending does not improve the outcome), which amount does it pick? → A: **The smallest** — preserve VP for later. Wasted VP would erode the late-game economy. (FR-018 amended.)
- Q: What is the exact definition of "tolerable SW" in the 4th Dan WC strategy? → A: `tolerable_sw = min(1, sw_remaining())` — tolerate up to 1 SW unless the character has 0 SW left to spare (in which case 0). This matches the skeleton's existing formula and is the minimal-risk threshold. (FR-018 amended.)
- Q: When a 5th-Dan Akodo counter-damages a 5th-Dan attacker in a mirror match, the recursion can chain. Is there a defensive depth cap? → A: **No explicit cap** — natural termination via VP exhaustion and the `damage < 10` cutoff is sufficient. Add a regression test that confirms termination in a self-mirror 5th-Dan scenario where both characters spend max VP each round.
- Q: When is a floating bonus considered "consumed" by an attack? → A: **On `AttackRolledEvent`** (the attack actually rolled). If the attack is interrupted before rolling (e.g., parry strategy preempts), the bonus is NOT consumed. (FR-012 amended.)
- Q: When the Akodo holds multiple floating bonuses, which one is consumed first? → A: **FIFO** (oldest first), matching the existing `AnyAttackFloatingBonus` collection semantics. If the existing engine's order is different (LIFO or arbitrary), document and align tests with engine behavior rather than over-specifying. (Edge case added.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A 1st–2nd Dan Akodo plays out a combat with the feint TVP economy firing correctly (Priority: P1)

A simulator user creates a 1st-Dan Akodo and runs them in a combat against a non-Akodo opponent. The Akodo character chooses to feint as their primary attack. When the feint succeeds, the user sees in the combat trace that the Akodo gained 4 TVP, with the source ("Akodo Special Ability") attributed. When the feint fails, the user sees +1 TVP, with the same attribution. The Akodo's 1st Dan extra die on attack/double attack/wound check is visible in the trace as well.

**Why this priority**: This is the school's foundational economy. If feint TVP doesn't fire correctly, every higher-Dan ability that depends on having VP to spend (4th Dan WC raises, 5th Dan counter-damage) breaks downstream.

**Independent Test**: Build a 1st-Dan Akodo with attack=4, feint=4. Set up a deterministic combat where the Akodo feints once and rolls high enough to succeed (use `CalvinistRollProvider`). Assert the combat trace contains a line attributing +4 TVP to the Akodo Special Ability, and that the Akodo's `temporary_vp` count incremented by 4 after the feint resolves. Repeat for a failed feint, asserting +1 TVP and the corresponding trace line.

### User Story 2 — A 3rd Dan Akodo accumulates floating attack bonuses from successful wound checks (Priority: P1)

After surviving an opponent's damage roll (wound check succeeds with a margin), the Akodo character gains a floating attack bonus equal to `((roll − damage) ÷ 5) × attack_skill`. The bonus is visible in the trace at the moment of acquisition AND at the moment of consumption (when applied to a future attack), with both source and numeric breakdown shown.

**Why this priority**: The 3rd Dan is the school's first non-trivial state-tracking ability — it puts a floating bonus into the character's state that persists across rounds within combat. Floating-bonus correctness (single-use, combat-scoped, properly attributed) is a recurring failure mode in school implementations.

**Independent Test**: Build a 3rd-Dan Akodo with attack=5. Force a deterministic combat: opponent rolls 30 damage, Akodo rolls 50 wound check. Assert (a) the Akodo gained one floating bonus equal to `((50 − 30) ÷ 5) × 5 = 20`; (b) the trace contains a line at the moment of WC success attributing `+20 (Akodo 3rd Dan, ((50−30)÷5)×5)` to the floating-bonus addition; (c) the next attack the Akodo makes shows `+20` applied with the same attribution; (d) the floating bonus is consumed (not available for the attack after that); (e) at combat end, the Akodo's floating-bonus state is empty.

### User Story 3 — A 4th Dan Akodo spends VP on a marginal wound check and survives a hit that would otherwise drop them (Priority: P1)

After rolling a wound check, the Akodo may spend void points for a free raise per VP (each VP = +5 to the WC roll). The strategy must choose to spend up to the exact amount that brings expected SW into the tolerable range, without over-spending.

**Why this priority**: This is the WC-survivability backbone for late-Dan Akodo. The skeleton has a confirmed off-by-one bug (`range(1, max_spend)` excludes `max_spend`). Fixing it must produce a meaningful behavioral change visible in the spend-decision trace.

**Independent Test**: Build a 4th-Dan Akodo with water=5, max_vp=5, current_vp=5. Force a deterministic damage event where the Akodo would otherwise take 3 SW. Verify the strategy spends VP equal to the exact `max_spend` (e.g., 5) to bring expected SW to 0 or 1. Assert the trace shows the VP spend with attribution ("Akodo 4th Dan: spent 5 VP on wound check, +5 per VP = +25 to roll"). Construct a regression test that exercises `max_spend` exactly (the off-by-one fix path).

### User Story 4 — A 5th Dan Akodo counter-damages an attacker correctly without double-applying their own incoming damage (Priority: P1)

When a 5th-Dan Akodo takes damage, the engine applies the damage exactly once (no double-counting from the override listener), then dispatches the wound check, then offers the 5th Dan VP-spending decision. The counter-damage event deals exactly `10 × VP_spent` light wounds to the attacker, capped at the damage taken.

**Why this priority**: The skeleton's lw_damage listener replicates default LW handling. If the listener slot stacks rather than overrides, the Akodo takes 2× damage per attack. This is P0 — silent damage doubling would make Akodo unwinnable as a baseline, invalidating every downstream school's Principle IX check.

**Independent Test**: Build a 5th-Dan Akodo at full LW=0. Force an attacker to deal exactly 30 LW. Assert (a) Akodo's LW = 30 (not 60); (b) one and only one wound check event was dispatched; (c) the 5th-Dan strategy spent 3 VP (30 ÷ 10) and dealt 30 LW to the attacker; (d) the trace shows the counter-damage with attribution.

### User Story 5 — A 1st-Dan Akodo wins a Principle IX win-feasibility check against the canonical Hida baseline at matched XP (Priority: P1)

At matched XP (300 XP), an Akodo built with the school's default strategies and progression priorities defeats a Hida Bushi built with its default strategies at a reasonable rate (at least one win across 5 sampled-RNG combats). Mirror non-degeneracy: two Akodos in a mirror match terminate within a reasonable round budget AND the school's identity engine (feint TVP → spend on WC → counter-damage) actually fires during the combat (Principle IX 2(b)).

**Why this priority**: Akodo IS the canonical Principle IX baseline that every other school is compared against. The Hida-vs-Akodo and Akodo-vs-Akodo matchups are the explicit reference scenarios in Constitution Principle IX. If Akodo can't win against Hida at matched XP under its own defaults, the constitution's baseline assumption is violated and every downstream school's compliance check becomes meaningless.

**Independent Test**: `combat-simulator` Scenario B: build a 300-XP Akodo and a 300-XP Hida using `simulation/templates/strategies.py` defaults. Run 5 combats with different deterministic RNG seeds. Assert Akodo wins ≥ 1. Scenario C (mirror): build two 300-XP Akodos, run a deterministic combat, assert (a) it terminates within 20 rounds, (b) the trace contains at least one Akodo Special Ability TVP gain (proving feints fired) AND at least one 4th-or-5th-Dan ability firing (proving the late-Dan economy engaged) — depending on Dan rank in the build. For lower-Dan builds, only the available-rank abilities need to fire.

### Edge Cases

- **Feint against an unparriable target** (rare in combat sim, but possible if a parry-immune mechanic exists): the Special Ability fires regardless of opponent's parry posture — the rule is about feint success/failure, not feint vs. parry. Confirm the engine emits AttackSucceededEvent/AttackFailedEvent for feints uniformly.
- **3rd Dan WC margin of exactly 0 (roll equals damage)**: rules text says "exceed the TN". The skeleton's listener fires on `WoundCheckSucceededEvent` — what does the engine emit when roll == damage? If "success" includes the equality case, the floating bonus would be `(0 ÷ 5) × attack = 0` — harmless. If success requires strict `roll > damage`, this listener wouldn't fire at all on equality. Either is fine for the rule but tests must lock the actual engine behavior.
- **4th Dan with insufficient VP**: when `max_spend = 0` (no available VP), the loop doesn't execute. Assert no SpendVoidPointsEvent is yielded and the original WoundCheckRolledEvent passes through unchanged.
- **5th Dan with damage < 10**: `event.damage // 10 = 0`, so `max_vp = 0`, no counter-damage. Assert the WC still proceeds normally.
- **5th Dan counter-damage triggers another 5th Dan in a mirror match (recursion)**: the counter-damage event is a new LightWoundsDamageEvent targeting the attacker. If the attacker is also a 5th-Dan Akodo, their lw_damage listener fires. Recursion terminates naturally when VP runs out OR damage < 10. **No explicit depth cap** per Clarifications. A regression test in self-mirror 5th-Dan must confirm termination.
- **TVP overflow**: if `gain_temporary_vp(4)` is called when `current_tvp + 4 > max_tvp`, what happens? Either capped at max or banked beyond. The engine likely caps at max; the trace should still show "+4 TVP (capped at MAX)" if so.
- **Multiple 3rd Dan floating bonuses accumulating in one combat**: per pre-resolution (g), each WC success creates a separate floating bonus and each subsequent attack consumes at most one. Three WC successes → three independent floating bonuses → consumed across the next three attacks.
- **Floating bonus carryover across combats**: per pre-resolution (d), floating bonuses MUST NOT persist across combats. Test that an Akodo character entering a second combat has an empty floating-bonus list.
- **Iaijutsu knack but not a duel**: Akodo lists iaijutsu as a school knack. In a non-duel combat (the only combat type this school is tested in), this means the character can use the iaijutsu skill, but the rules don't confer any unique iaijutsu Special Ability. Tests must NOT assume iaijutsu-duel mechanics on a standard combat.

## Requirements *(mandatory)*

### Functional Requirements

**Identity (already in skeleton; verify only)**

- **FR-001**: `AkodoBushiSchool.name()` MUST return `"Akodo Bushi School"`.
- **FR-002**: `AkodoBushiSchool.school_ring()` MUST return `"water"`.
- **FR-003**: `AkodoBushiSchool.school_knacks()` MUST return `["double attack", "feint", "iaijutsu"]` in that order.

**Special Ability**

- **FR-004**: When a character with `AkodoBushiSchool` succeeds on a feint attack (`AttackSucceededEvent` for an attack whose `skill() == "feint"` and whose subject is the character), the engine MUST emit a `GainTemporaryVoidPointsEvent(character, 4)`.
- **FR-005**: When the same character fails a feint attack (`AttackFailedEvent`), the engine MUST emit `GainTemporaryVoidPointsEvent(character, 1)`.
- **FR-006**: Both TVP gain events MUST be surfaced in the user-facing combat trace with the attribution string identifying the Akodo Special Ability as the source AND the numeric value (e.g., `"Akodo Special Ability: +4 TVP on successful feint"`). Trace lines that show only `"+4 TVP"` without source attribution are insufficient per Principle VII.

**1st Dan: extra rolled dice**

- **FR-007**: `AkodoBushiSchool.extra_rolled()` MUST return `["attack", "double attack", "wound check"]` so that the engine adds one extra die to each of these rolls per Constitution Principle V (pluggable decisions consult the school's roll-parameter contract).
- **FR-008**: The extra die MUST appear in the combat trace at every relevant roll with source attribution (e.g., `"+1k0 (Akodo 1st Dan)"`).

**2nd Dan: free raise**

- **FR-009**: `AkodoBushiSchool.free_raise_skills()` MUST return `["wound check"]`. The free raise MUST surface in the wound-check trace as `"FR (Akodo 2nd Dan)"` or equivalent attribution.

**3rd Dan: post-WC floating attack bonus**

- **FR-010**: When `WoundCheckSucceededEvent` fires with `subject == character` (where character is a ≥3rd-Dan Akodo), the engine MUST compute `bonus = ((event.roll - event.damage) // 5) * character.skill("attack")` and call `character.gain_floating_bonus(AnyAttackFloatingBonus(bonus))`. The formula uses floor division by 5 ("rounding down" per rules text).
- **FR-011**: Each successful wound check creates an independent floating bonus instance. If the Akodo succeeds N wound checks in one combat, the character has N independent floating bonuses available for the next N attacks.
- **FR-012**: Each floating bonus is consumed by exactly one subsequent attack — specifically, at `AttackRolledEvent` (the moment the attack actually rolls). Once consumed, it MUST NOT apply again. If an attack is interrupted before rolling (e.g., a parry strategy preempts the action), the bonus is NOT consumed and remains available for the next rolled attack. When multiple floating bonuses are available, they are consumed in FIFO order (oldest-first) matching the existing `AnyAttackFloatingBonus` collection semantics; if the engine implements a different order, tests align with the engine, not the rule.
- **FR-013**: Floating bonuses MUST NOT persist across combats. `Character.reset()` (or equivalent combat-boundary lifecycle hook) MUST clear them.
- **FR-014**: Floating-bonus acquisition AND consumption MUST both appear in the trace with source attribution and numeric breakdown (e.g., `"Akodo 3rd Dan: gained floating bonus +20 (margin 20 ÷ 5 × attack skill 5)"` at acquisition; `"+20 (Akodo 3rd Dan floating bonus consumed)"` at consumption).

**4th Dan: Water ring raise + VP-for-WC-raise**

- **FR-015**: `apply_rank_four_ability` MUST call `apply_school_ring_raise_and_discount(character)` which raises current and maximum Water by 1 and discounts further Water ring purchases by 5 XP.
- **FR-016**: When `WoundCheckDeclaredEvent` fires for a ≥4th-Dan Akodo, the engine MUST allow the character to spend void points after rolling, with each VP equivalent to one free raise (+5 to the roll).
- **FR-017**: `AkodoWoundCheckRolledStrategy` MUST consider spending VP up to and including `max_spend = min(available_vp_for_wc, max_vp_per_roll)`. The current `range(1, max_spend)` MUST become `range(1, max_spend + 1)` to include `max_spend` itself.
- **FR-018**: The strategy MUST select the SMALLEST spend that brings expected SW into the tolerable range, NOT the largest. Tolerable SW is defined as `min(1, sw_remaining())` — tolerate up to 1 SW unless the character has 0 SW left to spare. If no spend amount achieves tolerable, the strategy spends the amount that minimizes expected SW; when multiple spends yield the same minimum, the strategy picks the SMALLEST (preserve VP).
- **FR-019**: VP spending on a WC MUST surface in the trace with source attribution and breakdown (e.g., `"Akodo 4th Dan: spent 2 VP on wound check, +5 per VP = +10 to roll (50→60)"`).

**5th Dan: counter-damage from VP spend**

- **FR-020**: When `LightWoundsDamageEvent` fires with `target == character` (where character is a ≥5th-Dan Akodo), the engine MUST apply the damage exactly once to the character (no double-counting).
- **FR-021**: The engine MUST dispatch the character's wound check strategy exactly once per damage event.
- **FR-022**: After the WC dispatch, the 5th Dan strategy MUST compute `max_vp = min(available_vp_for_damage, max_vp_per_roll, event.damage // 10)` and, if positive, yield `SpendVoidPointsEvent(character, "damage", max_vp)` followed by `LightWoundsDamageEvent(character, event.subject, 10 * max_vp)` targeting the attacker.
- **FR-023**: The counter-damage event MUST be a NEW `LightWoundsDamageEvent` with the original attacker as the target (not a wrapped or modified version of the incoming event). This ensures the attacker's own school listeners can react to it (e.g., mirror-match recursion).
- **FR-024**: Counter-damage MUST surface in the trace with source attribution and numeric breakdown (e.g., `"Akodo 5th Dan: spent 3 VP on counter-damage, 10 LW × 3 = 30 LW to <attacker>"`).
- **FR-025**: The 5th Dan listener's "observe damage roll" branch (knowledge tracking when `event.subject != character`) MUST be retained. This is a non-rules-text behavior but is part of the engine's character-knowledge subsystem and is independent of the 5th Dan rule itself.

**Strategy defaults & progression (Principle VIII + IX)**

- **FR-026**: The school's default strategy bindings (set in `apply_special_ability` and/or `apply_rank_N_ability`) MUST be designed such that the school's signature mechanics (feint → TVP, WC survivability → 4th Dan VP raises, damage → 5th Dan counter) actually fire in representative combats. School-strategy-designer must verify identity firing in three scenarios: (1) generic non-Akodo opponent, (2) mirror match, (3) action-disadvantage.
- **FR-027**: The school's progression priorities (added to `simulation/templates/strategies.py`) MUST prioritize water ring (WC survivability), attack skill (multiplier in 3rd Dan formula), and feint skill (drives the TVP economy that fuels every other Dan ability) in the early progression. Wound check is already free-raised so it's a lower priority than attack and feint. Iaijutsu is a knack but is less central in non-duel combat — low priority.
- **FR-028**: A 300-XP Akodo built from the school's defaults MUST win ≥ 1 of 5 deterministic-RNG combats against a 300-XP Hida built from Hida's defaults (Principle IX win-feasibility). This is intentionally a low bar — the goal is "not obviously broken", not "definitively wins". If win rate is 0/5, the defaults are wrong.
- **FR-029**: Two 300-XP Akodos in a mirror match MUST terminate within 20 rounds (Principle IX 2(a)) AND the trace MUST contain evidence that the Akodo identity engine fired at least once (TVP gain from feint, OR 4th Dan VP spend on WC, OR 5th Dan counter-damage, depending on Dan rank in build) per Principle IX 2(b).
- **FR-030**: When the Akodo has fewer actions per round than the opponent (action-disadvantage state per Principle IX 3), the defaults MUST eventually take an offensive action (not parry every incoming attack forever). The trigger for switching from defense to offense is an open design question — document the chosen heuristic.

**Trace observability sweep (Principle VII)**

- **FR-031**: After implementation, a sample 1st-Dan-vs-1st-Dan combat MUST be runnable via `combat-simulator` and the resulting trace MUST be self-explaining for every Akodo-sourced numeric effect: extra die, free raise on WC, TVP gain on feint. A trace reviewer unfamiliar with the codebase must be able to read the trace and understand WHY each Akodo modifier appears.
- **FR-032**: Same observability sweep at higher Dan: a 5th-Dan-vs-5th-Dan combat MUST show 3rd Dan floating bonuses, 4th Dan VP-for-WC raises, and 5th Dan counter-damage events, each with source attribution.

### Key Entities

- **`AkodoBushiSchool`** (`simulation/schools/akodo_school.py`): the school class itself. Owns identity (name/ring/knacks/extra_rolled/free_raise_skills) and the `apply_*_ability` methods that install listeners and strategies onto character instances.
- **`AkodoAttackSucceededListener` / `AkodoAttackFailedListener`**: Special Ability listeners that emit TVP-gain events on feint outcomes.
- **`AkodoWoundCheckSucceededListener`**: 3rd Dan listener that gains a floating attack bonus on WC margin.
- **`AnyAttackFloatingBonus`**: existing engine entity in `simulation/mechanics/floating_bonuses.py`. Represents a single-use bonus applicable to any future attack. Verify scope (single-use, combat-scoped, attribution-tagged).
- **`AkodoWoundCheckDeclaredListener` + `AkodoWoundCheckRolledStrategy`**: 4th Dan listener-strategy pair that decides whether to spend VP for WC free raises after rolling.
- **`AkodoLightWoundsDamageListener` + `AkodoFifthDanStrategy`**: 5th Dan listener-strategy pair for counter-damage. The listener's correctness (single-application of LW + single WC dispatch) is the highest-impact P0 verification.
- **Combat trace** (rendered via `web/formatters/` and `simulation/log.py` per Principle VII): the user-visible event log. Every FR ending in "in the trace" or "surface ... attribution" lands here, not in `logger.debug`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing tests (2919 baseline as of commit `89dc0bb`) continue to pass after the Akodo refactor. Zero regressions.
- **SC-002**: New tests in `tests/test_akodo_school.py` cover every FR-NNN above. Coverage on `simulation/schools/akodo_school.py` ≥ 95%.
- **SC-003**: `combat-simulator` Scenario A (clause exercise): every Akodo ability (Special, 1st–5th Dan) fires in a scripted scenario that triggers each clause exactly once.
- **SC-004**: `combat-simulator` Scenario B (win-feasibility): a 300-XP default Akodo wins ≥ 1 of 5 deterministic combats vs. a 300-XP default Hida. Same vs. a 300-XP default opponent of any other implemented school (Mirumoto, Ishi) — at least one win per opponent.
- **SC-005**: `combat-simulator` Scenario C (mirror non-degeneracy): two 300-XP default Akodos terminate a combat within 20 rounds, AND the trace contains at least one Akodo identity-engine firing per Principle IX 2(b).
- **SC-006**: `combat-simulator` Scenario B.2 (action-disadvantage): when the Akodo enters an action-disadvantage state, the defaults eventually take an offensive action (verified by a scripted scenario that puts the Akodo at -1 action and verifies the next round's action selection).
- **SC-007**: `combat-simulator` Scenario D (behavioral round-robin): the Akodo plays a combat against each currently-implemented school (Mirumoto, Ishi) and the combat trace shows the Akodo's identity machinery firing in each matchup.
- **SC-008**: Trace observability check (Principle VII): a manual sweep of a 5th-Dan combat trace identifies, for every Akodo-sourced numeric effect, both source attribution and numeric breakdown without consulting source code. Items missing attribution are blockers, not follow-up.
- **SC-009**: `env/bin/ruff check .` PASS. `env/bin/mypy` PASS with zero strict-mode errors. `env/bin/pytest tests/ -v` PASS.
- **SC-010**: BACKLOG.md is updated: Akodo Bushi School moves from "Skeleton present — needs full audit + completion" to "Validated via speckit workflow" with the merge commit hash.

## Assumptions

- The skeleton's interpretation of "one void point" for failed feint as TVP (not regular VP) is adopted per pre-resolution (a). Logged in `OPEN_QUESTIONS.md` for end-of-run user verification. Alternative interpretation: failure gives a regular VP that persists across combats — would require a separate `GainPermanentVoidPointEvent` and a different lifecycle hook.
- The 4th Dan range off-by-one fix per pre-resolution (b) does not require compensating changes elsewhere in the codebase. Verification: grep for any callers that compute `max_spend - 1` as a defensive workaround. Expected: none.
- The 5th Dan strategy keeps "always spend max VP" as the v1 heuristic per pre-resolution (c). Smarter heuristics (e.g., only spend if it threatens the attacker's WC range) deferred to `OPEN_QUESTIONS.md` as a follow-up.
- `AnyAttackFloatingBonus` already implements single-use + combat-scoped semantics. Verification will confirm or surface a bug; this spec does NOT mandate changes to the floating-bonus subsystem unless a defect is found.
- The 5th Dan listener overrides the default `lw_damage` listener (does not stack). Per the negation refactor (commit `89dc0bb`), `_set_school_listener` writes to a single slot in the character's listener dict, so this assumption is structurally guaranteed. Test SC-002 / FR-020 / FR-021 will lock this behavior.
- The school-strategy-designer agent will propose default strategy bindings consistent with Principle VIII (feint-driven attack, WC-raise aware) and pass Principle IX playability. If the agent cannot find a binding that satisfies all of (1)–(3), this is a P0 issue and the spec must be revisited.
- The school-progression-designer agent will propose ring/skill priorities consistent with Principle VIII. The initial proposal is water > attack > feint > double attack > others, but the designer agent has final say.
- The autonomous run does NOT batch this school with subsequent schools. Per the workflow codified in CLAUDE.md, the user reviews each completed school before the next starts.

## Out of scope

- Non-combat use of TVP (RP / story rewards).
- Iaijutsu-duel-specific Special Abilities (Akodo's iaijutsu is a knack, not a duel-mechanic; the iaijutsu duel engine is a separate subsystem and is not enhanced by Akodo's school).
- Refactoring `AnyAttackFloatingBonus` or the floating-bonus subsystem beyond what's needed to verify FR-011–FR-014 hold.
- Smarter 5th Dan VP-spending heuristics beyond "always spend max". Marked as a follow-up.
- Multi-target damage events (e.g., AOE) — the 5th Dan rules text assumes a 1:1 attacker-target relationship. AOE is out of scope.
- Adding new schools — this spec is Akodo-only. Cross-school interaction tests use only currently-implemented schools.
