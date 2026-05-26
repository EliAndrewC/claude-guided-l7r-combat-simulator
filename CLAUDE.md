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
- **Coverage**: Maintain >90% code coverage.

## Development Commands
- **Run unit tests**: `env/bin/pytest tests/ -v`
- **Run linting**: `env/bin/ruff check .`
- **Run type check**: `env/bin/mypy` (uses `[tool.mypy]` in `pyproject.toml`: strict on `simulation/` and `web/`, relaxed on `tests/`)
- **Start web server**: `env/bin/streamlit run web/app.py`

## Post-Change Checklist
After every code change, run these steps in order:
1. **Lint**: `env/bin/ruff check .` — fix any errors before proceeding
2. **Type check**: `env/bin/mypy` — must report zero errors. Strict mode is enabled for `simulation/` and `web/`; do not add `# type: ignore` to silence errors without an inline justification.
3. **Test**: `env/bin/pytest tests/ -v` — all tests must pass
4. **Restart Streamlit**: Streamlit does not reliably hot-reload all changes (especially new modules, factory registrations, and sys.path fixes in page files), so a full restart is required after you've completed your implementation and testing of each change. Since `streamlit run` is a long-running server that never exits on its own:
   - Start: Run `env/bin/streamlit run web/app.py --server.headless true` using the Bash tool with `run_in_background: true`
   - Verify: After a few seconds, read the background task output file to confirm "You can now view your Streamlit app" appears

## Secrets and credentials

Secrets live in a project-root `.env` file (gitignored — never commit). Currently the only secret is:

- `FLY_API_TOKEN` — auth for `flyctl` deploys

If `.env` is missing in a fresh container, the user has the canonical copy and will paste it back. New secrets we adopt go into the same `.env` and should be documented here.

To use the secrets in a shell session: `set -a && source .env && set +a` (the `set -a` makes sourced assignments exported). Values containing whitespace (the Fly token does) MUST be quoted in `.env`.

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
Active feature plan: [specs/002-isawa-ishi-school/plan.md](specs/002-isawa-ishi-school/plan.md)
(Branch `002-isawa-ishi-school`. See sibling files in the same directory
for spec, research, data model, contracts, quickstart, and OPEN_QUESTIONS.)
<!-- SPECKIT END -->
