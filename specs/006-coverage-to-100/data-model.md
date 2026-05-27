# Data Model: Coverage to 100%

This audit introduces NO new engine entities.

## New test infrastructure (only)

### `tests/test_coverage_pragma_audit.py` (meta-test)

Walks the source tree under `simulation/` and `web/`. For each `# pragma: no cover` occurrence:

1. Verify a justification comment exists (same line OR line immediately above).
2. Verify the justification matches one of four allowed categories (token-based grep):
   - `Streamlit page module` / `UI entry point`
   - `defensive` / `unreachable` / `precondition`
   - `abstract method` / `subclasses must override`
   - `re-raise` / `preserve stack`

Failure modes:
- Pragma with no comment → fail with file:line reference.
- Pragma with comment that doesn't match an allowed category → fail with file:line + comment text.

### `tests/test_analysis_scripts.py` (Category C)

Invokes `main()` from each refactored analysis script. Asserts no exception. Uses mocks for filesystem / stdout if needed.

### `tests/test_coverage_audit_*.py` (Category A)

Audit-driven test files, one per area:
- `tests/test_coverage_audit_adapters.py` — tests for `web/adapters/*` gaps
- `tests/test_coverage_audit_strategies.py` — tests for `simulation/strategies/*` gaps
- `tests/test_coverage_audit_schools.py` — tests for per-school gaps (small clusters)
- `tests/test_coverage_audit_misc.py` — tests for `simulation/character.py`, `events.py`, `listeners.py`, `templates/generator.py`, `web/state.py`, etc.

## Invariants

- Coverage on `simulation/` + `web/` (excluding `tests/`) = 100%.
- Every pragma has a paired justification.
- Every justification matches one of four allowed categories.
- Existing test count grows by 200-500 tests (estimate).
