# Feature Specification: Isawa Ishi School

**Feature Branch**: `002-isawa-ishi-school`

**Created**: 2026-05-26

**Status**: Draft (autonomous run — see `OPEN_QUESTIONS.md` for deferred decisions)

**Input**: User description: "Complete the Isawa Ishi School implementation per the upstream rules file `rules/04-schools.md`, with all five dan ranks plus the school's Special Ability. The existing skeleton is partially implemented and contains known bugs. Per Constitution Principle III, the upstream rules text is authoritative — cite for every ability. Per user authorization (2026-05-26) this is an autonomous run with deferred-question pattern: all ambiguities resolve via documented best-guess in `OPEN_QUESTIONS.md` for end-of-run review."

**Rules Source**: [`rules/04-schools.md`, section "Isawa Ishi School"](https://github.com/EliAndrewC/l7r/blob/master/rules/04-schools.md) — authoritative per Constitution Principle III.

**Run Mode**: Autonomous. All deferred questions and architectural decisions land in `specs/002-isawa-ishi-school/OPEN_QUESTIONS.md` for end-of-run user review.

## Clarifications

### Session 2026-05-26 (autonomous run — answers chosen by orchestrator; user review pending)

> **NOTE**: Per user authorization (2026-05-26), this run does not stop to ask the user. Every entry below was resolved by the orchestrator with the best-guess answer that's recorded here. The full rationale, alternatives, and reversal-instructions for each are in `OPEN_QUESTIONS.md`. **The user reviews these post-run; any answer can be revised.**

- Q: First Dan — which 2 skills get the extra die alongside `precepts`? → A: `wound check` + `initiative` (defensive Void-mystic identity). [Q1 in OPEN_QUESTIONS.md]
- Q: Does the per-roll VP cap (`lowest_ring - 1`) apply to the 3rd Dan ally-boost spend? → A: No — the cap constrains VP spent on the character's own roll; 3rd Dan spends on an ally's roll are exempt. [Q1b in OPEN_QUESTIONS.md]
- Q: Second Dan — which skill gets the free raise on all rolls? → A: `precepts` (synergizes with 3rd Dan X=precepts boost; the skeleton's `attack` is a poor fit for a Void mystic). [Q2 in OPEN_QUESTIONS.md]
- Q: Third Dan — does the boost apply to any character's roll, or only allies'? → A: Ally-restricted (in-group). The rules-text "another character" is generic but mechanically the buff only makes sense on allies. Drop the skeleton's adjacency requirement (no rules basis). [Q3 in OPEN_QUESTIONS.md]
- Q: Fifth Dan — how is the "negate the target's school" mechanism implemented? → A: Per-character flag `_school_negated_by: Optional[Character]` set by a successful negation; engine short-circuits the target's per-rank `apply_*_ability` dispatch when set; flag clears at combat end via the existing `Character.reset()` chain. Mutual negation is allowed. [Q5 in OPEN_QUESTIONS.md]
- Q: Fifth Dan — when does the negation strategy trigger? → A: On the Ishi's first `YourMoveEvent` of the combat where they have enough VP. Rules-text says "instantaneous, no action consumed" — the trigger event is the natural earliest reactive point. [Q5b in OPEN_QUESTIONS.md]

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Construct an Isawa Ishi at any dan with the custom VP machinery (Priority: P1)

A simulator user constructs a character whose school is "Isawa Ishi School" at any dan 1–5. The character's maximum void points are calculated as `highest_ring + school_rank` (not the engine default of `min_ring + worldliness`), and the per-roll cap on void-point spending is `lowest_ring - 1` (not the engine default's higher cap). The character runs in the existing combat harness without error.

**Why this priority**: Without the custom VP machinery firing, no Ishi-specific ability can manifest meaningfully in combat — the school's Special Ability is the foundation of its mechanical identity. P1 because it is a prerequisite for every other ability.

**Independent Test**: Construct an Isawa Ishi at school rank 3 with `rings = {void: 4, fire: 3, water: 2, air: 3, earth: 3}` (highest = void = 4, lowest = water = 2). Assert (a) `max_vp() == highest_ring + school_rank == 4 + 3 == 7`, (b) `max_vp_per_roll() == lowest_ring - 1 == 1`. Assert these via the engine's character API (e.g., `character.max_vp()`).

**Acceptance Scenarios**:

1. **Given** a freshly constructed Isawa Ishi at any school rank, **When** `max_vp()` is queried, **Then** the result equals `max(ring values) + school_rank`.
2. **Given** an Isawa Ishi with `rings = {void: 4, fire: 3, water: 2, air: 3, earth: 3}`, **When** `max_vp_per_roll()` is queried, **Then** the result equals `lowest_ring - 1 = 1`.
3. **Given** an Isawa Ishi with `lowest_ring = 1`, **When** `max_vp_per_roll()` is queried, **Then** the result is `max(0, 1 - 1) == 0` (no negative VP cap).
4. **Given** an Isawa Ishi attempts to spend 2 VP on a single roll while the per-roll cap is 1, **When** the spend is evaluated, **Then** the engine caps the spend at the per-roll limit (1).

---

### User Story 2 — Isawa Ishi at 1st & 2nd Dan with passive bonuses (Priority: P1)

A simulator user observes that a 1st-dan-or-higher Isawa Ishi rolls one extra die on `precepts`, `wound check`, and `initiative` rolls (the per-build choice of "any two additional rolls" defaults to `wound check` + `initiative` — see `OPEN_QUESTIONS.md` Q1). A 2nd-dan-or-higher character gets a free raise on every roll of the chosen skill (defaults to `precepts` per OPEN_QUESTIONS.md Q2).

**Why this priority**: Like Mirumoto US1, this is the MVP slice for the school's passive defensive bonuses — testable end-to-end without touching the harder per-roll-listener machinery of 3rd Dan or 5th Dan.

**Independent Test**: Construct an Isawa Ishi at 2nd dan; assert (a) `school.extra_rolled() == ["precepts", "wound check", "initiative"]`, (b) `school.free_raise_skills() == ["precepts"]`, (c) a parry roll constructed by this character has no extra die (parry not in extra_rolled list), and (d) a `precepts` roll has both the extra die AND the +5 free-raise modifier.

**Acceptance Scenarios**:

1. **Given** a 1st-dan Isawa Ishi making a `precepts` roll, **When** the roll is constructed, **Then** the number of dice rolled is one greater than baseline.
2. **Given** a 1st-dan Isawa Ishi making a `wound check` roll, **When** the roll is constructed, **Then** the number of dice rolled is one greater than baseline.
3. **Given** a 1st-dan Isawa Ishi making an `initiative` roll, **When** the roll is constructed, **Then** the number of dice rolled is one greater than baseline.
4. **Given** a 1st-dan Isawa Ishi making an `attack` roll, **When** the roll is constructed, **Then** the number of dice rolled equals baseline (no extra die — attack is not in the 1st Dan list).
5. **Given** a 2nd-dan Isawa Ishi making a `precepts` roll, **When** the roll is constructed, **Then** the roll's modifier includes the +5 free raise.

---

### User Story 3 — Isawa Ishi at 3rd Dan with the ally-roll-boost listener (Priority: P2)

A 3rd-dan-or-higher Isawa Ishi, when ANY combat-roll-bearing event resolves for an ally in their group, MAY spend 1 void point to roll `precepts.k1` (X = precepts skill) and add the resulting kept-die value to the ally's roll total. The spend is limited to once per roll. The buff applies only to allies (in-group), not to enemies. The buff applies to attack rolls, parry rolls, double-attack rolls, counterattack rolls, iaijutsu rolls, feint rolls, lunge rolls, and wound check rolls — i.e., every roll type for which void points are spendable.

**Why this priority**: 3rd Dan is the school's *active* contribution to combat — the resource-spending behavior that defines its tactical role as a support / void mystic. P2 because the school is shippable without it (1st/2nd Dan provide a meaningful passive presence) but it is the most distinctive ability.

**Independent Test**: Construct a 3rd-dan Isawa Ishi (precepts skill = 4, 5 VP available) and an ally in the same group. The ally rolls a parry that ends up below TN by 10. The Ishi's listener fires, spends 1 VP, rolls a Calvinist-deterministic `precepts.k1` returning (say) 12, and the ally's parry total becomes `original + 12 = original + 12`. Assert the ally's roll total includes the boost.

**Acceptance Scenarios**:

1. **Given** a 3rd-dan Isawa Ishi with ≥1 VP available, **When** an in-group ally completes any combat roll (attack/parry/double attack/counterattack/iaijutsu/feint/lunge/wound check), **Then** the Ishi MAY spend 1 VP to add a Xk1 (X=precepts) result to the ally's roll total. The decision to spend is made by a pluggable strategy.
2. **Given** a 3rd-dan Isawa Ishi who has already spent the per-roll bonus on a given roll, **When** another opportunity to spend on the SAME roll arises, **Then** no further spend is permitted (once-per-roll rule).
3. **Given** a 3rd-dan Isawa Ishi with 0 VP available, **When** an in-group ally completes a combat roll, **Then** the Ishi does NOT spend.
4. **Given** a 3rd-dan Isawa Ishi, **When** an OPPONENT (not in-group) completes a combat roll, **Then** the Ishi does NOT spend (ally-only restriction; opponent buffs make no sense per OPEN_QUESTIONS.md Q3).
5. **Given** a 3rd-dan Isawa Ishi with precepts=0, **When** an ally completes a combat roll, **Then** the Ishi does NOT spend (a precepts-0 boost would add 0; rules permit but it's pointless).

---

### User Story 4 — Isawa Ishi at 4th Dan with Void modifications (Priority: P2)

A 4th-dan-or-higher Isawa Ishi has current and maximum Void increased by 1, and XP cost of raising Void is reduced by 5 (with a floor of 0). The contested-roll-opponent-cannot-spend-VP clause is documented as out of scope (social contests are not modeled by the combat sim — see Assumptions).

**Why this priority**: Inherits the established Mirumoto 4th-Dan pattern (`apply_school_ring_raise_and_discount`). Most of the work is verification, not new code. P2 because the school is meaningfully complete without it but it shapes character build cost.

**Independent Test**: Construct a 4th-dan Isawa Ishi alongside an identical baseline. Assert (a) Void is +1 vs baseline (current and max), (b) XP cost to raise Void from any rank is 5 less than the standard cost (with floor 0).

**Acceptance Scenarios**:

1. **Given** a 4th-dan Isawa Ishi, **When** their Void ring is queried, **Then** it is +1 relative to what they would have at the same XP without the 4th Dan.
2. **Given** a 4th-dan Isawa Ishi, **When** the XP cost to raise Void by 1 from any rank ≤5 is queried, **Then** the cost is 5 less than the standard cost, floored at 0.
3. **Given** the contested-roll-opponent-cannot-spend-VP clause, **Then** combat-simulator scope does NOT model it (out of scope per Constitution III scope boundary — social contests are not in `rules/04-schools.md`'s combat scope).

---

### User Story 5 — Isawa Ishi at 5th Dan with school negation (Priority: P3)

A 5th-dan Isawa Ishi MAY spend void points equal to twice the target's school rank (or `floor(opponent_xp / 50)` for schoolless opponents) to completely negate the target's school's abilities for the remainder of the current combat. The negation is instantaneous and does not consume an action. While negated, the target's school's per-rank abilities (Special, 1st Dan ... 5th Dan) do not fire; only the target's base character stats remain.

**Why this priority**: This is the most powerful and most novel ability — it modifies another character's *school behavior* mid-combat. Implementation requires a new per-character negation flag + check points in every school's `apply_*_ability` (or equivalent). P3 because the school is broadly playable without it; this ability is endgame.

**Independent Test**: Construct a 5th-dan Isawa Ishi with VP available, and a 4th-dan Mirumoto Bushi as opponent. The Ishi spends `2 × 4 = 8` VP to negate the Mirumoto's school. After negation, the Mirumoto's 4th-Dan damage-die-reduction halving (FR-013 of Mirumoto) does NOT fire; its 1st Dan extra die does NOT fire; etc. The Mirumoto plays as a baseline character for the rest of combat.

**Acceptance Scenarios**:

1. **Given** a 5th-dan Isawa Ishi with `2 × opponent_school_rank` VP available, **When** the Ishi negates the opponent's school, **Then** the Ishi's VP pool decreases by `2 × opponent_school_rank` and the opponent's school is tagged as negated.
2. **Given** a 5th-dan Isawa Ishi with insufficient VP for negation, **When** negation is attempted, **Then** the negation does not fire (VP not spent, opponent school remains active).
3. **Given** an opponent whose school is negated by an Isawa Ishi, **When** the opponent makes a roll that would normally trigger a school ability (e.g., a Mirumoto's free parry raise), **Then** the school ability does NOT fire.
4. **Given** a 5th-dan Isawa Ishi against a schoolless opponent with 200 XP, **When** negation is attempted, **Then** the VP cost is `floor(200 / 50) = 4`.
5. **Given** an opponent whose school is negated, **When** the combat ends (or a new combat begins), **Then** the negation expires (the negation flag is reset per the rules-text "remainder of one fight").

---

### Edge Cases

- An Isawa Ishi with all rings equal (e.g., all 3): `max_vp = 3 + school_rank`, `max_vp_per_roll = 3 - 1 = 2`. Normal case.
- An Isawa Ishi at school rank 0: `max_vp = highest_ring + 0`. Effectively a baseline minimum (school-not-yet-applied case; depends on engine convention).
- The 3rd Dan listener firing against a character not in the Ishi's group (e.g., the Ishi has no group set, or the ally is in a different group): the listener MUST NOT fire — defensively check `character.group()` before evaluating ally-ness.
- A 5th-dan Isawa Ishi negates a target who is themselves negating another character: the negation chain — does the Ishi's own school's negation effect persist if their school is also negated by the same target? Unclear from rules. Default: the negation order is "first to land, sticks for the combat's duration"; mutual negation is allowed and both schools cease firing for the rest of combat. (See OPEN_QUESTIONS.md Q5.)
- A 5th-dan Isawa Ishi negates an opponent with school rank 0 (rare — implies 5th dan against a non-school character): the negation cost is `2 × 0 = 0` for schooled opponents at rank 0, which is implausible; fall back to the schoolless cost formula (`floor(xp/50)`) when target has no meaningful school rank.
- A 3rd-dan Isawa Ishi spends 1 VP for an ally boost; the per-roll guard prevents re-firing. If the same ally rolls AGAIN later in the same round (a different roll), the Ishi MAY spend again (per-roll, not per-round).
- Per-roll VP cap of 0 (when lowest_ring is 1): the character cannot spend any VP on a roll, regardless of how many they have. The 3rd Dan's "spend 1 VP" SHOULD still fire because the 3rd Dan spend is not constrained by the per-roll cap (the cap is on VP spent on THIS character's roll; 3rd Dan spends are on ANOTHER's roll). (See OPEN_QUESTIONS.md Q1b for interpretation note.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST register a school named "Isawa Ishi School" in the existing school factory, selectable by the same mechanism as other implemented schools.
- **FR-002**: An Isawa Ishi character MUST report Void as its school ring.
- **FR-003**: An Isawa Ishi character MUST report exactly the set `{absorb void, kharmic spin, otherworldliness}` as its school knacks.
- **FR-004**: An Isawa Ishi character MUST have `max_vp()` equal to `max(ring_value for ring in rings) + school_rank`. (Special Ability)
- **FR-005**: An Isawa Ishi character MUST have `max_vp_per_roll()` equal to `max(0, min(ring_value for ring in rings) - 1)`. (Special Ability)
- **FR-006**: An Isawa Ishi character of 1st dan or higher MUST roll one extra die on `precepts` rolls, `wound check` rolls, and `initiative` rolls. (First Dan + the "any two of choice" defaults documented in OPEN_QUESTIONS.md Q1.)
- **FR-007**: An Isawa Ishi character of 2nd dan or higher MUST receive one free raise on every roll of the skill `precepts`. (Second Dan + the "any skill of choice" default documented in OPEN_QUESTIONS.md Q2.)
- **FR-008**: An Isawa Ishi character of 3rd dan or higher, after an in-group ally completes any combat-relevant roll (attack, parry, double attack, counterattack, iaijutsu, feint, lunge, wound check), MAY spend 1 void point to roll Xk1 where X is the Ishi's `precepts` skill and add the kept-die result to the ally's roll total. (Third Dan)
- **FR-009**: The Third Dan spend MUST be limited to once per ally roll — the engine MUST track per-roll whether the Ishi has already spent on that roll. (Third Dan, "once per roll" clause)
- **FR-010**: The Third Dan spend MUST be ally-restricted — the listener does NOT fire for rolls completed by enemies or by non-grouped characters (defensive default per OPEN_QUESTIONS.md Q3).
- **FR-011**: An Isawa Ishi character of 4th dan or higher MUST have current and maximum Void increased by 1, applied at character construction. (Fourth Dan, ring raise)
- **FR-012**: An Isawa Ishi character of 4th dan or higher MUST have the XP cost of raising Void reduced by 5, with a floor of 0. (Fourth Dan, ring cost discount)
- **FR-013**: An Isawa Ishi character of 5th dan MUST be capable of spending `2 × opponent_school_rank` VP (or `floor(opponent_xp / 50)` for schoolless opponents) to mark the opponent's school as negated for the remainder of the current combat. (Fifth Dan)
- **FR-014**: When an opponent's school is negated by FR-013, the opponent's per-rank school abilities (Special, 1st Dan through 5th Dan) MUST NOT fire for the remainder of the current combat. The opponent's base character stats and non-school abilities are unaffected.
- **FR-015**: All Isawa Ishi mechanics MUST be implemented as pluggable decision/strategy/listener/provider components per Constitution Principle V; the 3rd Dan boost decision and the 5th Dan negation decision MUST be made by strategy objects, not hardcoded into the combat loop.
- **FR-016**: All Isawa Ishi mechanics MUST use the existing injectable-randomness providers (Constitution Principle IV); the 3rd Dan precepts.k1 roll, the 5th Dan VP-spend, etc. all flow through existing roll providers.
- **FR-017**: Every functional requirement above MUST cite the corresponding ability name from `rules/04-schools.md` (Constitution Principle III).
- **FR-018**: Per Constitution Principle VII, every Isawa Ishi ability application MUST appear in the user-facing combat trace with both its source and its numeric effect. Specifically:
  - The custom VP cap (Special Ability) must annotate when an attempted spend hits the per-roll cap.
  - The 1st Dan extra die must annotate `+1 die` events with the source "Isawa Ishi 1st Dan".
  - The 2nd Dan free raise on precepts must annotate the +5 modifier on precepts rolls with source "Isawa Ishi 2nd Dan free raise".
  - The 3rd Dan ally boost must annotate the bonus value with the source "Isawa Ishi 3rd Dan ally boost from `<Ishi name>`".
  - The 4th Dan Void+1 and XP discount must be reflected in stat lines.
  - The 5th Dan negate-school event must annotate clearly when an opponent's school is being negated, including the VP cost and the school being negated.
- **FR-019**: Per Constitution Principle VIII + IX, the school's default strategy bindings MUST be identity-aligned and playable. Specifically:
  - The school's default parry/interrupt strategies should reflect the school's defensive Void-mystic identity (Ishi is not a melee combat school — see OPEN_QUESTIONS.md Q4 for the strategy-designer's recommendation).
  - The 3rd Dan ally-boost decision MUST have a pluggable default strategy (e.g., `EagerAllyBoostStrategy` — fire whenever the ally's roll is below TN by ≥5 and the Ishi has ≥2 VP; "save VP for emergencies" alternative documented).
  - The 5th Dan negation MUST have a pluggable default strategy (e.g., `EagerNegationStrategy` — fire on the highest-rank opposing school as soon as the Ishi has enough VP).
  - Default bindings MUST pass Principle IX's three scenarios (win-feasibility vs Akodo/Hida, mirror non-degeneracy with identity engine firing, action-disadvantage handling).

### Key Entities

- **IsawaIshiSchool**: A school registered with the existing school factory. Identifies its ring (Void), school knacks, and the per-dan abilities it confers on its members.
- **IshiMaxVPProvider**: Custom VP provider already extant in the skeleton. Overrides `max_vp()` and `max_vp_per_roll()` per the Special Ability. Needs verification + trace annotation.
- **IshiAllyBoostListener**: Listener for the 3rd Dan ally-roll-boost. Fires on combat-relevant `*RolledEvent`s where the subject is an in-group ally; consults a strategy to decide whether to spend.
- **IshiAllyBoostStrategy** (new): Pluggable decision strategy for when to spend the 3rd Dan boost. Default: `EagerAllyBoostStrategy`.
- **IshiNegateSchoolStrategy** (new): Pluggable decision strategy for when to fire 5th Dan negation. Default: `EagerNegationStrategy`.
- **IshiNegationListener** (new): Per-combat tracker of negated schools. Resets at combat end.
- **Per-character negation flag** (new): Each character gains an attribute `_school_negated_by: Optional[Character]` set by a 5th-dan Ishi's negation. The engine checks this flag at every `apply_*_ability` call site (or equivalent), and short-circuits school ability dispatch when set.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An Isawa Ishi character of any dan rank from 1 to 5 can be instantiated, dropped into the existing combat harness, and run to combat resolution without runtime errors.
- **SC-002**: Every clause of the "Isawa Ishi School" section in `rules/04-schools.md` (in scope per Assumptions) corresponds to at least one acceptance scenario and one functional requirement in this spec.
- **SC-003**: All unit tests for the school pass deterministically (no flakes across 100 consecutive runs) when the roll provider is `CalvinistRollProvider` or a fixed seed.
- **SC-004**: Project-wide line coverage remains above 90% (Constitution Principle VI).
- **SC-005**: `env/bin/ruff check .`, `env/bin/mypy`, and `env/bin/pytest tests/ -v` all pass with zero errors / failures.
- **SC-006**: A combat trace of an Isawa Ishi (any dan) annotates each Ishi-specific effect with source attribution (Principle VII) — extra die, free raise, ally boost, VP cap, negation event all visible in the user-facing trace.
- **SC-007**: Principle IX playability is verified — the Isawa Ishi passes Scenarios A (win-feasibility vs Akodo/Hida at 300 XP), B (mirror non-degeneracy with identity-engine firing), C (action-disadvantage handling), and D (behavioral round-robin showing parry/attack/ally-boost frequencies consistent with the school's identity across opponents).

## Assumptions

(Working interpretations during the autonomous run — each is reviewed against the rules text and may be revised by the user after the run. Full details with alternatives in `OPEN_QUESTIONS.md`.)

- **1st Dan choices** (Q1): the "any two types of rolls of your choice" defaults to `wound check` + `initiative` — consistent with the existing skeleton and the school's defensive Void-mystic identity. Alternatives (e.g., `parry` + `wound check`) noted in OPEN_QUESTIONS.md.
- **2nd Dan choice** (Q2): the "any skill of your choice" defaults to `precepts` — synergizes with the 3rd Dan boost (X=precepts), so investing in precepts compounds across two abilities. Alternatives (e.g., `attack` from the skeleton, `parry`, `wound check`) noted in OPEN_QUESTIONS.md.
- **3rd Dan target scope** (Q3): ally-restricted (in-group, drop adjacency requirement). Rules-text says "another character" generically, but in a combat sim buffing opponents is mechanically meaningless. Adjacency requirement removed because rules-text does not require it.
- **3rd Dan roll scope**: all combat-eligible rolls (attack, parry, double attack, counterattack, iaijutsu, feint, lunge, wound check). Skeleton's attack-only restriction is too narrow per rules-text "any roll for which void points may be spent".
- **5th Dan implementation** (Q5): per-character `_school_negated_by` flag set by a 5th-dan Ishi's negation; engine's per-rank `apply_*_ability` short-circuits when set. Reset at combat end (engine-level reset via `Character.reset()` analog). Mutual negation allowed.
- **5th Dan strategy timing**: invoke a `IshiNegateSchoolStrategy` on the Ishi's `YourMoveEvent` (the first move where the Ishi has enough VP); the negation is "instantaneous" per rules-text but the engine needs a trigger event.
- **Out of scope** (per Constitution III and combat-sim boundaries):
  - Recovery mechanics (full/partial rest, regain VP, Absorb Void reset) — single-combat sim.
  - Absorb Void knack as a tactical ability — defer to a separate feature.
  - Kharmic Spin knack in combat — defer.
  - Otherworldliness on basic skills — non-combat scope.
  - 4th Dan's "opponents can't spend VP in contested rolls" — social contests not modeled.
- **Implementation surface**: extend the existing `simulation/schools/ishi_school.py`. New strategy classes live in `simulation/strategies/ishi_dan_abilities.py` (new file). Follow the Mirumoto-established Constitution Principle V pluggability pattern.
- **Existing skeleton bugs to fix** (per pre-run audit):
  - `IshiAllyBoostListener` only handles `AttackRolledEvent` — broaden.
  - `IshiAllyBoostListener` calls `interrupt_strategy().recommend()` on the non-ally fallthrough branch — that is wrong scope; remove.
  - `IshiAllyBoostListener` requires `formation().is_adjacent` — drop per OPEN_QUESTIONS.md Q3.
  - No per-roll guard for the 3rd Dan once-per-roll rule — add.
  - `apply_rank_five_ability` is a TODO — implement.
