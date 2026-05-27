#!/usr/bin/env python3

#
# test_coverage_pragma_audit.py
#
# Meta-test enforcing Constitution Principle VI v1.3.0 pragma discipline.
#
# Walks the source tree under simulation/ and web/ for every
# `# pragma: no cover` marker and verifies:
#   1. A justification comment exists (same line or line immediately above).
#   2. The justification matches one of four allowed categories per
#      Principle VI: UI entry point (Streamlit), defensive branch,
#      abstract method, re-raise block.
#

import pathlib
import re
import unittest

# Token patterns matched against the justification text.  At least one
# must match for a pragma to be valid.  All matching is case-insensitive
# and is done on a stripped-of-whitespace lowercase form.
ALLOWED_CATEGORY_TOKENS = (
    # (a) UI entry point (Streamlit page modules + web/app.py)
    "streamlit page",
    "streamlit module",
    "ui entry point",
    "loaded by streamlit",
    "loaded by st",
    # (b) defensive branch with reasoning
    "defensive",
    "unreachable",
    "precondition",
    "exhaustive",
    # (c) abstract base class method
    "abstract method",
    "subclasses must override",
    "not implemented",
    # (d) re-raise block
    "re-raise",
    "preserve stack",
    "preserve traceback",
)

PRAGMA_RE = re.compile(r"#\s*pragma:\s*no\s*cover\b(.*)$", re.IGNORECASE)


def _justification_is_valid(text: str) -> bool:
    """Return True if the given justification text matches at least one
    allowed-category token.  Case-insensitive substring match."""
    normalized = text.strip().lower()
    return any(token in normalized for token in ALLOWED_CATEGORY_TOKENS)


def _collect_pragmas() -> list[tuple[str, int, str, str]]:
    """Walk simulation/ and web/ for pragma markers.

    Returns a list of (path, line_number, full_line, justification_text)
    tuples.  ``justification_text`` is whatever appears on the pragma
    line AFTER ``# pragma: no cover``, OR the comment line immediately
    above it (stripped of leading ``#`` and whitespace).
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    results: list[tuple[str, int, str, str]] = []
    for subdir in ("simulation", "web"):
        for path in (root / subdir).rglob("*.py"):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:  # pragma: no cover  # defensive: unreadable file is a CI/filesystem error, never seen in practice
                continue
            for i, line in enumerate(lines):
                match = PRAGMA_RE.search(line)
                if match is None:
                    continue
                same_line_justification = match.group(1).strip().lstrip("#").strip()
                if same_line_justification:
                    justification = same_line_justification
                else:
                    prev_line = lines[i - 1].strip() if i > 0 else ""
                    if prev_line.startswith("#"):
                        justification = prev_line.lstrip("#").strip()
                    else:
                        justification = ""
                rel_path = str(path.relative_to(root))
                results.append((rel_path, i + 1, line, justification))
    return results


class TestPragmaDiscipline(unittest.TestCase):
    """Enforce Constitution Principle VI v1.3.0: every `# pragma: no
    cover` MUST have a paired justification comment matching one of
    four allowed categories."""

    def test_every_pragma_has_justification(self) -> None:
        offenders: list[str] = []
        for path, lineno, line, justification in _collect_pragmas():
            if not justification:
                offenders.append(f"{path}:{lineno}: {line.strip()}")
        self.assertEqual(
            [], offenders,
            "The following `# pragma: no cover` markers lack a "
            "justification comment (Principle VI requires every "
            "pragma to be paired with a same-line or above-line "
            "comment explaining the skip):\n"
            + "\n".join(f"  - {o}" for o in offenders),
        )

    def test_every_pragma_justification_matches_allowed_category(self) -> None:
        offenders: list[str] = []
        for path, lineno, line, justification in _collect_pragmas():
            if not justification:
                # Already flagged by the previous test.
                continue
            if not _justification_is_valid(justification):
                offenders.append(
                    f"{path}:{lineno}: justification {justification!r} "
                    f"does not match any allowed category "
                    f"(Principle VI categories: UI entry point, "
                    f"defensive, abstract method, re-raise)."
                )
        self.assertEqual(
            [], offenders,
            "The following pragma justifications don't match an "
            "allowed Principle VI category:\n"
            + "\n".join(f"  - {o}" for o in offenders),
        )


if __name__ == "__main__":
    unittest.main()
