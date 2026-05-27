# L7R Combat Simulator Constitution

The simulator's purpose is to make the L7R tabletop combat system mechanically
testable: to play out individual combats, vary parameters that drive
combatant decisions, and compare character builds against optimal strategies.
Every principle below exists to keep that purpose attainable.

## Core Principles

### I. Test-First (Non-Negotiable)
A failing test is written before the code that makes it pass. Red → Green →
Refactor is the only legal cycle. Test files live under `tests/` and exercise
the public surface of the module under test. Bug fixes start with a regression
test that reproduces the bug. No production code lands without a test that
would have failed before the change.

### II. Rules-Engine Purity
The rules engine under `simulation/` is pure logic. It does not import from
`web/`, write to disk, read environment variables, or talk to a UI framework.
The UI consumes the engine; the engine never reaches into the UI. A change
that requires the engine to know about Streamlit, sessions, or rendering is a
design error and must be re-routed through a UI-side adapter.

### III. Upstream Rules Are Truth
The human-readable rules at
`https://github.com/EliAndrewC/l7r/tree/master/rules` are the specification
this simulator implements. When simulator behavior and the rules disagree,
the simulator is wrong by definition. Out of scope: everything outside the
`rules/` directory of that repository; the Between Place / Spirit Encounter
rules within it; and the **Shugenja School** in `rules/04-schools.md`
(deferred to a future project phase — this phase does not model the spell
subsystem its abilities depend on). Specs and plans that reference
mechanics MUST cite the relevant rules file.

Note: other schools whose abilities reference spells or shugenja-adjacent
mechanics (e.g., Yogo Warden's wards, Isawa Ishi's void mysticism) remain
in scope insofar as their combat-relevant abilities can be modeled without
the spell engine. When an in-scope school's ability genuinely requires the
spell subsystem, that specific ability is deferred — not the whole school.

### IV. Injectable Randomness
Engine logic does not call `random.*` directly. Every die roll flows through
a roll provider (`TrackingRollProvider`, `WoundCheckProvider`, and peers) so
tests can substitute deterministic or predestined die sources. This is what
makes property tests, regression tests, and the future strategy-tuning
experiments possible. New randomness in the engine MUST be introduced through
a provider, not by importing `random` at the use site.

### V. Pluggable Decisions
Combatant choices — attack selection, wound-check declaration, light-wounds
keeping, void-point spending, action timing — are interchangeable objects
behind factories (`optimizers/`, `strategies/`, `schools/`). Decision logic is
never hardcoded into the combat loop. This is load-bearing: the project's
stated goal is to vary these decisions across runs and measure outcomes, which
is only possible if every decision point is a swappable component.

### VI. Coverage Floor
Test coverage must stay above 90%. This is a floor, not a target. A change
that drops coverage below the floor is not done. Uncovered branches in newly
written code are a code-review blocker, not a follow-up.

### VII. Combat Trace Self-Explanation
Every applied ability, modifier, free raise, extra die, point spend, or
rules override that changes a roll's outcome MUST appear in the user-facing
combat trace with both its **source** and its **numeric effect**. "+30" is
insufficient; "+30 (Mirumoto 5th Dan, +10 per void point × 3)" is correct.
Debug logs (via `simulation/log.py`) are not sufficient — the trace a
rules-literate user sees in the UI must be self-explaining without
consulting the source code. When an implementer adds a school effect to the
engine, they MUST update the user-facing formatter alongside the engine
code; landing the engine change without the trace annotation is incomplete
work. SC-006 in feature specs ("trace interpretable by a reviewer") is
satisfied by user-visible annotations, not by `logger.debug` lines.

### VIII. School Identity Drives Defaults
Every school's progression priorities (ring/skill advancement order in
`simulation/templates/strategies.py`) and default strategy bindings (the
strategies installed by `apply_special_ability` and `apply_rank_N_ability`
in the school file) MUST be derived from the school's identity as expressed
in the rules text — not copied wholesale from a template school, not chosen
arbitrarily, not left to convention. A parry-focused school MUST prioritize
the parry ring in its advancement; a double-attack-oriented school MUST
default its attack strategy to favor double attack; a school whose Special
Ability rewards a specific kind of action MUST default to a strategy that
takes that action. When a school's mechanics and its defaults diverge
(e.g., a parry-focused school whose default interrupt strategy
counterattacks instead of parrying), the defaults are wrong by definition.

### IX. Strategy Defaults Must Be Playable
Identity-aligned (Principle VIII) is necessary but not sufficient. A
school's default strategy bindings MUST also be *playable* — they must
produce combats that terminate in winnable, non-degenerate states under
representative matchups. Concretely:

1. **Win-feasibility.** The school's defaults MUST be capable of winning
   against a generic equivalent-XP opponent (the canonical baselines are
   Akodo Bushi at the same XP tier and Hida Bushi at the same XP tier).
   A school that loses 100% of generic matchups under its own defaults is
   incomplete work.
2. **Mirror non-degeneracy.** Two characters of the same school in a
   mirror match MUST satisfy TWO conditions, not one:
   (a) the combat terminates within a reasonable round budget — "both
   parry forever waiting for the other to attack" or "both counterattack
   forever" or any equivalent never-act pattern is a defect; AND
   (b) the school's identity engine actually fires during the combat —
   if a school's Special Ability, Dan-rank abilities, or signature
   resource economy never engages in a mirror match, the school's
   defaults are degenerate even if the combat technically terminates via
   default-strategy bumbling. A combat that terminates by raw wound-check
   shootout while the school's identity machinery never activates is a
   Principle IX failure. Both conditions are required.
3. **Action-disadvantage handling.** When an opponent has more actions per
   round than the school's bearer (a common state mid-fight after action
   spending), the defaults MUST eventually take an offensive action — a
   pure-defense strategy that parries every incoming attack and never
   attacks is degenerate. The exact "when to switch to offense" trigger is
   a strategy-design choice, but having SOME trigger is required.

The `school-strategy-designer` agent verifies (1)–(3) by reading the
proposed Strategy classes and reasoning about their interaction in the
three scenarios. The `combat-simulator` agent verifies (1)–(3) at runtime
via scripted matchups. Defaults that pass identity review (Principle VIII)
but fail playability review (Principle IX) are incomplete work.

The verification ALSO applies to existing schools when their defaults are
modified — changing a strategy slot on a school requires re-verifying the
three scenarios still hold.

## Technical Constraints

- **Language**: Python 3.12 or newer. Type hints are required on all new
  public functions and methods; `from __future__ import annotations` is
  acceptable.
- **UI Framework**: Streamlit only. The engine remains framework-agnostic so a
  different UI could be added later without touching `simulation/`.
- **Style**: PEP 8, enforced by `ruff`. Lint must pass on every change.
- **Scope Boundary**: Between Place and Spirit Encounter rules are
  permanently out of scope and MUST NOT appear in specs, plans, or tasks.
  The Shugenja School in `rules/04-schools.md` is deferred to a future
  project phase and MUST NOT be implemented in the current phase; see
  Principle III for the carve-out covering other schools that brush
  against shugenja mechanics.

## Quality Gates

Every change, before it is considered complete:

1. `env/bin/ruff check .` passes with zero errors.
2. `env/bin/mypy` passes with zero errors. Strict mode is in effect for
   `simulation/` and `web/`; `tests/` uses a relaxed profile that still
   checks bodies but does not require annotations. Silencing errors with
   `# type: ignore` requires an inline justification.
3. `env/bin/pytest tests/ -v` passes with zero failures.
4. Coverage remains above 90% (see Principle VI).
5. If UI code changed, Streamlit has been restarted and the affected page
   has been exercised in a browser. Type-checking and unit tests verify code
   correctness, not feature correctness — UI changes require manual
   verification.
6. If engine code changed in a way that affects a roll's dice, modifiers,
   or outcomes (per Principle VII), the user-facing combat trace surfaces
   the change with explicit source attribution. Tests against `logger.debug`
   markers are insufficient; the test must assert against the user-visible
   trace string.
7. If a new school's progression priorities or default strategy bindings
   were authored (per Principle VIII), they have been reviewed against the
   school's rules text by either the `school-progression-designer` or
   `school-strategy-designer` agent, or by equivalent written rationale in
   the feature's design artifacts.
8. If a school's strategy bindings were authored OR modified (per
   Principle IX), the three playability scenarios — win-feasibility against
   a generic baseline, mirror non-degeneracy, and action-disadvantage
   handling — have been verified at runtime by `combat-simulator` or
   equivalent scripted scenarios committed alongside the change.

Operational details (exact commands, restart procedure, deploy steps) live in
`CLAUDE.md`, which is the operational companion to this constitution.

## Governance

This constitution supersedes ad-hoc decisions and prior conventions. When
`CLAUDE.md`, a spec, a plan, or in-code comments conflict with this document,
the constitution wins and the conflicting artifact must be updated.

Amendments require:
1. A written justification (commit message or PR description) explaining the
   motivating problem.
2. A version bump per the rules below.
3. A pass over `.specify/templates/` to confirm no template encodes a now-stale
   assumption.

**Versioning**: MAJOR for principle removal or backwards-incompatible
governance change; MINOR for a new principle or section; PATCH for wording,
clarification, or non-semantic edits.

**Compliance review**: `/speckit-plan` and `/speckit-analyze` MUST surface
constitution violations as blockers, not suggestions.

**Version**: 1.2.2 | **Ratified**: 2026-05-25 | **Last Amended**: 2026-05-27
