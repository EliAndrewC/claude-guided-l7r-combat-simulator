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

import importlib
import re
import sys
from typing import Any

# Locate ``make_url_path_regex`` across Streamlit versions. As of
# 1.54 it lives in ``streamlit.web.server.server_util``; older /
# newer versions may relocate it. We search candidate locations
# rather than hard-coding one, so a Streamlit upgrade that moves
# the function gives a clear "couldn't find it" error instead of
# a silent attribute miss during patch application.
_CANDIDATE_MODULES: tuple[str, ...] = (
    "streamlit.web.server.server_util",
    "streamlit.web.server.routes",
    "streamlit.web.server.server",
)


def _find_make_url_path_regex() -> tuple[Any, str]:
    for module_name in _CANDIDATE_MODULES:
        try:
            mod = importlib.import_module(module_name)
        except ImportError:  # pragma: no cover  # defensive: candidate modules are version-specific
            continue
        if hasattr(mod, "make_url_path_regex"):
            return mod, module_name
    raise RuntimeError(  # pragma: no cover  # defensive: would only fire after a Streamlit refactor that relocates the function
        f"Streamlit launcher patch FAILED: ``make_url_path_regex`` "
        f"not found in any of {_CANDIDATE_MODULES}. The Streamlit "
        f"framework may have relocated it; re-audit web/launcher.py."
    )


_OWNER_MODULE, _OWNER_NAME = _find_make_url_path_regex()
_ORIG_MAKE_URL_PATH_REGEX = _OWNER_MODULE.make_url_path_regex


def _patched_make_url_path_regex(*path: str, **kwargs: Any) -> str:
    """Wrap make_url_path_regex so ``_stcore/*`` routes also match
    a leading page-name prefix like ``/Run_Simulation``.

    For all other endpoints (page routes, static assets), behavior is
    unchanged — those are registered separately by Streamlit and
    already work for multi-page navigation.
    """
    pattern: str = _ORIG_MAKE_URL_PATH_REGEX(*path, **kwargs)
    if "_stcore" in pattern and pattern.startswith("^/"):
        # Insert ``(?:/[^/]+)*`` between the leading ``^`` and ``/``
        # so the regex tolerates zero-or-more leading path segments
        # before the canonical ``/_stcore/...`` portion.
        return "^" + r"(?:/[^/]+)*" + pattern[1:]
    return pattern


# Patch the owning module AND every module that re-imported the
# function via ``from … import make_url_path_regex`` (Python rebinds
# the name in the importing module's namespace, so patching the
# owner alone leaves stale references in re-importers).
_OWNER_MODULE.make_url_path_regex = _patched_make_url_path_regex
for _candidate in _CANDIDATE_MODULES:
    try:
        _mod = importlib.import_module(_candidate)
    except ImportError:  # pragma: no cover  # defensive: candidate may not exist in older/newer Streamlit
        continue
    # ``getattr`` + identity check rebinds the patched function only on
    # modules that re-imported the original from elsewhere. Using
    # ``getattr`` with default avoids mypy attr-defined on candidates
    # that don't expose the symbol at all.
    _bound = getattr(_mod, "make_url_path_regex", None)
    if _bound is not None and _bound is _ORIG_MAKE_URL_PATH_REGEX:
        # mypy: ``_mod`` is statically typed as a module without the
        # symbol because the candidate list spans Streamlit versions;
        # the runtime ``hasattr`` guard above proves the attribute
        # exists here. Suppressed with inline justification per
        # CLAUDE.md's mypy policy.
        _mod.make_url_path_regex = _patched_make_url_path_regex  # type: ignore[attr-defined]


def _assert_patch_active() -> None:
    """Self-check: confirm the patched regex actually accepts the
    page-prefixed form. Run at startup so a Streamlit refactor that
    changes the regex shape produces a clear error rather than a
    silent regression to the 404 behavior we're fixing.
    """
    sample = _OWNER_MODULE.make_url_path_regex("", "_stcore/health")
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
