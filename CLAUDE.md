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
1. **Core Engine**: Pure logic, implemented based on `./rules`, which has the human-readable rules
2. **API/UI**: Streamlit interface to visualize the dice rolls and outcomes.

## Project Rules
- **TDD First**: Always write a failing test in `tests/` before writing the code (linting should also always pass).
- **Logic Isolation**: Keep the rules engine 100% separate from the UI code.
- **Coverage**: Maintain >90% code coverage.

## Development Commands
- **Run unit tests**: `env/bin/pytest tests/ -v`
- **Run linting**: `env/bin/ruff check .`
- **Start web server**: `env/bin/streamlit run web/app.py`

## Post-Change Checklist
After every code change, run these steps in order:
1. **Lint**: `env/bin/ruff check .` — fix any errors before proceeding
2. **Test**: `env/bin/pytest tests/ -v` — all tests must pass
3. **Restart Streamlit**: Kill any running `streamlit` process and restart with `env/bin/streamlit run web/app.py`. Streamlit does not reliably hot-reload all changes (especially new modules, factory registrations, and sys.path fixes in page files), so a full restart is required after you've completed your implementation and testing of each change.

## Manual actions not done after every code change
4. **Deploy to Fly.io**: The app is deployed to Fly.io at https://l7r-combat-sim.fly.dev/. Do NOT deploy unless the user explicitly asks. Deploy command: `~/.fly/bin/flyctl deploy`
