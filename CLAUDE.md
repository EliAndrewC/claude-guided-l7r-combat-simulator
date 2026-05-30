# Tabletop RPG Combat Simulator Project

This is a project which was begun years ago and never completely finished.  Its
goal is to simulate the combat system of this game to facilitate playtesting.
This will eventually involve:
-> showing individual combats and how they play out
-> being able to test out what happens when we tweak the parameters / thresholds
    for the various decisions made by combatants to determine the optimal
    strategies for spending resources and applying bonuses
-> changing different decisions about how characters are built and which stats
    yield the most combat effectiveness given the various strategies

At present the codebase only does a fraction of this, though it has a robust
implementation of the rules engine.  Our goal is to gradually extend its
capabilities using a TDD philosophy.

The rules are at https://github.com/EliAndrewC/l7r/tree/master/rules
You should ignore everything outside of the "rules" directory of that git repo,
as none of it is relevant to this project.

## Tech Stack
- Language: Python 3.12+
- UI: Streamlit (Internal simulation dashboard)
- Testing: pytest, pytest-cov
- Style: PEP 8, Type Hints (Strict)

## Architecture
1. **Core Engine**: Pure logic, implemented based on the human-readable rules at
    https://github.com/EliAndrewC/l7r/tree/master/rules (all rules are in that
    directory, so you can ignore other directories in that Git repo and also
    ignore the Between Place and Spirit Encounter rules, which will never be
    covered by this simulator)
2. **API/UI**: Streamlit interface to visualize the dice rolls and outcomes.

## Project Rules
- **TDD First**: Always write a failing test in `tests/` before writing the code (linting should also always pass).
- **Logic Isolation**: Keep the rules engine 100% separate from the UI code.
- **Coverage**: 100% code coverage per Constitution Principle VI. Every uncovered line is either newly tested OR marked with `# pragma: no cover` and a one-line justification comment.

## Development Commands
- **Run unit tests**: `env/bin/pytest tests/ -v`
- **Run linting**: `env/bin/ruff check .`
- **Run type check**: `env/bin/mypy` (uses `[tool.mypy]` in `pyproject.toml`: strict on `simulation/` and `web/`, relaxed on `tests/`)
- **Start web server**: `env/bin/python web/launcher.py` (the launcher patches Streamlit's URL-path regex so `_stcore/*` endpoints resolve under page-name prefixes — see `web/launcher.py`)

## Post-Change Checklist
After every code change, run these steps in order:
1. **Lint**: `env/bin/ruff check .` — fix any errors before proceeding
2. **Type check**: `env/bin/mypy` — must report zero errors. Strict mode is enabled for `simulation/` and `web/`; do not add `# type: ignore` to silence errors without an inline justification.
3. **Test**: `env/bin/pytest tests/ -v` — all tests must pass
4. **Restart Streamlit**: Streamlit does not reliably hot-reload all changes (especially new modules, factory registrations, and sys.path fixes in page files), so a full restart is required after you've completed your implementation and testing of each change. Since `streamlit run` is a long-running server that never exits on its own:
   - Start: Run `env/bin/python web/launcher.py --server.headless true` using the Bash tool with `run_in_background: true`
   - Verify: After a few seconds, read the background task output file to confirm "You can now view your Streamlit app" appears

## Secrets and credentials

Secrets live in a project-root `.env` file (gitignored — never commit). Currently the only secret is:

- `FLY_API_TOKEN` — auth for `flyctl` deploys

If `.env` is missing in a fresh container, the user has the canonical copy and will paste it back. New secrets we adopt go into the same `.env` and should be documented here.

To use the secrets in a shell session: `set -a && source .env && set +a` (the `set -a` makes sourced assignments exported). Values containing whitespace (the Fly token does) MUST be quoted in `.env`.

## New school implementation workflow

The queue of unimplemented schools lives in [BACKLOG.md](BACKLOG.md) at
repo root. When asked to "implement the next school", pick the topmost
unchecked entry under **Skeleton present — needs full audit + completion**
and run this workflow:

1. **Verify scope.** Confirm the school is not in BACKLOG.md's "Out of
   scope" section. Shugenja School and any ability that requires the
   (deferred) spell subsystem are excluded per Constitution Principle III.

2. **Specify.** `/speckit-specify` with: (a) the verbatim rules text from
   `https://github.com/EliAndrewC/l7r/blob/master/rules/04-schools.md` for
   the chosen school, (b) an audit of the existing skeleton file in
   `simulation/schools/`, (c) the list of known ambiguities with your
   pre-resolution of each, and (d) the autonomous-run authorization
   (decisions logged to `OPEN_QUESTIONS.md` for end-of-run review).

3. **Clarify.** `/speckit-clarify` — in autonomous mode, pre-answer each
   question per the spec's pre-resolutions; log any non-trivial choices
   to `OPEN_QUESTIONS.md`.

4. **Plan + design review.** `/speckit-plan`, then dispatch
   `school-progression-designer` and `school-strategy-designer` (in
   parallel) for ring/skill priorities and default-strategy bindings.
   Apply their proposals to `simulation/templates/strategies.py` and the
   school file respectively.

5. **Tasks.** `/speckit-tasks`.

6. **Implement.** `/speckit-implement` — batches of 3–6 tasks per
   `school-implementer` call. After every substantial batch:
   - `rules-auditor` reviews the diff against the upstream rules clause.
   - `combat-simulator` runs scenarios A (clause exercise), B
     (win-feasibility vs Akodo + Hida baselines at matched XP), B.2
     (action-disadvantage), C (mirror non-degeneracy with both
     termination AND identity-engine-firing checks per Principle IX), and
     D (behavioral round-robin against other schools).
   - `trace-auditor` reviews the user-visible combat trace for
     Principle VII compliance. Catches aggregates rendered without
     source attribution or numeric breakdown (e.g., `XkY` rolls,
     bare `+N` modifiers, sourceless floating-bonus consume lines).
     New school work that adds modifiers, floating bonuses, or
     extra dice MUST surface them in the trace with source labels.
   - `trace-reader` reviews the same trace for UX intuitiveness —
     does the rendering read coherently to a fresh playtester? Catches
     contradictory inline math, cross-renderer disagreements, redundant
     0-LW damage lines on feints, separated floating-bonus consumption
     lines that should be inline, and alarming "unsourced" literal labels.
     `trace-reader` complements `trace-auditor`: they review the same
     output but check different properties (Principle VII compliance
     vs. UX intuitiveness). A line can pass one and fail the other.

7. **Validate constitution gates** per the 8-point checklist in the
   constitution: ruff, mypy, pytest, coverage = 100% (Principle VI;
   pragma skips allowed with justification), Streamlit smoke if
   UI touched, trace observability per Principle VII, identity-driven
   defaults per Principle VIII, playability per Principle IX.

8. **Squash-merge** the feature branch into `master`. User handles
   `git push` (per durable constraint — never run `git push` yourself).

9. **Update BACKLOG.md** — move the school's entry from "Skeleton
   present" to "Validated via speckit workflow" with the merge commit
   reference.

The user reviews after each school before the next starts. Do not
batch multiple schools without a checkpoint — the methodology kept
evolving across Mirumoto and Ishi (Principles VII/VIII/IX were added
mid-run), and per-school review is what catches identity/playability
defects before they propagate.

## School player choices (build-time, via YAML)

Schools whose rules text gives players a build-time choice (e.g., Ishi 1st Dan "any two skills of your choice", Ide Diplomat "Any non-Void Ring") expose those as `school_choices` in the character YAML:

```yaml
school: Isawa Ishi School
school_choices:
  first_dan_extra_rolled: [parry, wound check]   # list of 2 skill names; precepts auto-prepended
  second_dan_free_raise: parry                    # single skill name
```

```yaml
school: Ide Diplomat School
school_choices:
  first_dan_extra_rolled: [feint, parry]
  second_dan_free_raise: feint
  school_ring: fire                               # any non-Void (air, earth, fire, water)
```

How to add a new school's choices:
1. The school's relevant methods (`extra_rolled`, `free_raise_skills`, `school_ring`, etc.) read `self.choice(key, default)` and validate the shape.
2. Document the accepted keys in the school class's docstring.
3. Invalid choices log a warning via `simulation.log.logger` and fall back to the default — never crash the build.

Implementation lives in `simulation/schools/base.py::BaseSchool.set_choice/choice/has_choice`. The adapter wiring is in `web/adapters/character_adapter.py::config_to_character` (choices are applied to the school instance BEFORE `apply_*_ability` runs).

## Manual actions not done after every code change
5. **Deploy to Fly.io**: The app is deployed to Fly.io at https://l7r-combat-sim.fly.dev/. Do NOT deploy unless the user explicitly asks.
   - **Install flyctl** (if not present at `~/.fly/bin/flyctl`): `curl -L https://fly.io/install.sh | sh`. Installs to the canonical path `~/.fly/bin/flyctl`.
   - **Deploy**: `set -a && source .env && set +a && ~/.fly/bin/flyctl deploy` from the repo root. Picks up `FLY_API_TOKEN` from `.env`.

<!-- SPECKIT START -->
Active feature plan: [specs/009-action-damage-breakdown/plan.md](specs/009-action-damage-breakdown/plan.md)
(Branch `010-action-damage-breakdown`. See sibling files in the same directory
for spec, research, data model, quickstart, and OPEN_QUESTIONS.)
<!-- SPECKIT END -->
