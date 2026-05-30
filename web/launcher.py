#!/usr/bin/env python3

#
# Streamlit launcher that patches the framework's URL-path regex
# builder so the ``_stcore/*`` HTTP endpoints (health, host-config,
# upload, etc.) also match when requested under a page-name prefix
# (``/Run_Simulation/_stcore/health``, etc.).
#
# Why: Streamlit's JS client constructs these endpoints with paths
# RELATIVE to ``window.location.href``. When the user is on a
# multi-page-app page like ``/Run_Simulation``, the browser resolves
# ``_stcore/health`` to ``/Run_Simulation/_stcore/health`` — which is
# not a registered route, producing 404s in the browser console on
# every health-check poll.
#
# This launcher MUST be the process entry point — Streamlit's server
# routes are registered when ``streamlit.web.server.server.Server``
# starts, so the patch has to land before the standard ``streamlit
# run`` CLI takes over.
#

from __future__ import annotations

import re
import sys
from typing import Any

import streamlit.web.server.server_util as _server_util

_ORIG_MAKE_URL_PATH_REGEX = _server_util.make_url_path_regex


def _patched_make_url_path_regex(*path: str, **kwargs: Any) -> str:
    """Wrap make_url_path_regex so ``_stcore/*`` routes also match
    a leading page-name prefix like ``/Run_Simulation``.

    For all other endpoints (page routes, static assets), behavior is
    unchanged — those are registered separately by Streamlit and
    already work for multi-page navigation.
    """
    pattern = _ORIG_MAKE_URL_PATH_REGEX(*path, **kwargs)
    if "_stcore" in pattern and pattern.startswith("^/"):
        # Insert ``(?:/[^/]+)*`` between the leading ``^`` and ``/``
        # so the regex tolerates zero-or-more leading path segments
        # before the canonical ``/_stcore/...`` portion.
        return "^" + r"(?:/[^/]+)*" + pattern[1:]
    return pattern


# Also patch already-imported references — server.py captures the
# function at module-import time via ``from server_util import
# make_url_path_regex``, so the rebound module attribute alone won't
# affect the already-bound name in server.py.
_server_util.make_url_path_regex = _patched_make_url_path_regex
try:
    import streamlit.web.server.server as _server_mod
    # mypy: server.py does ``from server_util import make_url_path_regex``
    # which is a re-import, not a re-export. The attribute is present at
    # runtime (we rely on it to monkey-patch the function reference the
    # Server class uses) but mypy refuses to acknowledge it. Suppressed
    # with an inline justification per CLAUDE.md's mypy policy.
    _server_mod.make_url_path_regex = _patched_make_url_path_regex  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover  # defensive: server module is always importable here
    pass


def _assert_patch_active() -> None:
    """Self-check: confirm the patched regex actually accepts the
    page-prefixed form. Run at startup so a Streamlit refactor that
    changes the regex shape produces a clear error rather than a
    silent regression to the 404 behavior we're fixing.
    """
    sample = _server_util.make_url_path_regex("", "_stcore/health")
    if not re.match(sample, "/Run_Simulation/_stcore/health"):
        raise RuntimeError(
            f"Streamlit launcher patch FAILED: regex {sample!r} does "
            f"not accept /Run_Simulation/_stcore/health. The framework "
            f"may have changed make_url_path_regex's shape — re-audit "
            f"web/launcher.py."
        )
    if not re.match(sample, "/_stcore/health"):  # pragma: no cover  # defensive: the patch is additive and the unprefixed path always matches
        raise RuntimeError(
            f"Streamlit launcher patch FAILED: regex {sample!r} no "
            f"longer accepts the canonical /_stcore/health form."
        )


_assert_patch_active()


def main() -> None:
    """Hand control to Streamlit's CLI with web/app.py as the script.

    Any extra args passed to the launcher are appended to the
    ``streamlit run web/app.py`` invocation so callers can override or
    add server flags (e.g. ``--server.headless=true``) without losing
    the default port / address bindings.
    """
    from streamlit.web.cli import main as _streamlit_cli

    extra_args = sys.argv[1:]
    sys.argv = [
        "streamlit", "run", "web/app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0",
        *extra_args,
    ]
    _streamlit_cli()


if __name__ == "__main__":
    main()
