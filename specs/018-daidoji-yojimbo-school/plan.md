# Plan: Daidoji Yojimbo School

**Branch**: `018-daidoji-yojimbo-school`
**Specs**: [spec.md](spec.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## Architecture

The Daidoji skeleton is the most-developed remaining bushi (237 lines, 34 tests), but has 4 BLOCKING rules-fidelity defects in the 4th and 5th Dan effects (timing, choice, expiry scope, counterattack-history tracking) plus a MINOR ad-hoc-attribute tracking concern.

## Phases

### Phase 1: Setup ✓
- [x] Branch created (`018-daidoji-yojimbo-school`).
- [x] 34 baseline tests confirmed passing.

### Phase 2: Dispatch designers + the 4 review agents in parallel.

### Phase 3: Apply must-fix findings
1. Q2 — 4th Dan damage redirect timing.
2. Q4 — 5th Dan expiry scope.
3. Q5 — 5th Dan "for whom you've counterattacked" tracking.
4. Q3 — 4th Dan strategic choice.
5. Q1 — 3rd Dan tracking (slot/listener-based replacement).
6. Trace observability tags.

### Phase 4: New test files + coverage.

### Phase 5: Final gates + squash-merge + BACKLOG.
