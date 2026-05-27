# Quickstart: Verifying the Coverage Audit

## Prerequisites

- Repository on branch `007-coverage-to-100` (or master after squash-merge).
- `env/bin/pytest tests/ -q` exit code 0.

## 1. Verify global coverage = 100%

```bash
env/bin/pytest tests/ --cov=simulation --cov=web --cov-report=term --no-header -q 2>&1 | tail -5
```

Expected last line: `TOTAL  ...  ...  100%`. Every file's `Missing` column empty.

## 2. Verify pragma discipline

```bash
env/bin/pytest tests/test_coverage_pragma_audit.py -v
```

Expected: all tests pass. Each pragma has a justification matching one of the four allowed categories.

## 3. Review pragma markers

```bash
grep -rn "# pragma: no cover" simulation/ web/
```

Each result line MUST show a justification (either same-line or on the line immediately above). A human scanner should be able to read each justification in <10 seconds and judge it as legitimate.

## 4. Verify analysis scripts (Category C)

```bash
env/bin/pytest tests/test_analysis_scripts.py -v
```

Expected: all tests pass. Each `main()` runs without exception.

## 5. Verify Streamlit page coverage (Category B)

```bash
env/bin/pytest tests/ --cov=web/views --cov-report=term --no-header -q 2>&1 | grep "web/views"
```

Each Streamlit page file shows 100% (because all lines are excluded via pragma).

## 6. Constitution gates

```bash
env/bin/ruff check .
env/bin/mypy
env/bin/pytest tests/ -q
```

All three must pass.

## When the quickstart fails

- **Coverage not at 100%**: a file has uncovered lines. Either write a test or add a documented pragma.
- **Pragma-audit test fails**: a pragma marker is missing a justification, or the justification doesn't match an allowed category. Fix per the failure message.
- **Streamlit page not at 100%**: the module-level pragma isn't taking effect. Add per-function pragmas as a fallback.
