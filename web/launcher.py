#!/usr/bin/env python3

#
# Streamlit launcher that patches the framework's route table so the
# ``_stcore/*`` HTTP/WebSocket endpoints (health, host-config, stream,
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
# This launcher MUST be the process entry point — Streamlit builds its
# route table when the server starts, so the patch has to land before
# the standard ``streamlit run`` CLI takes over.
#
# Streamlit 1.55 migrated its web server from Tornado to Starlette.
# The pre-1.55 launcher wrapped ``make_url_path_regex`` (Tornado route
# strings); that function no longer exists. The current strategy wraps
# ``create_streamlit_routes`` and relaxes the compiled ``path_regex``
# of each ``_stcore`` route so it tolerates leading path segments. The
# extra segments are ignored by the handlers, so the canonical and
# page-prefixed forms both hit the same endpoint.
#

from __future__ import annotations

import importlib
import re
import sys
from collections.abc import Sequence
from typing import Any

from starlette.routing import BaseRoute

# Regex fragment matching zero-or-more leading path segments
# (``/Run_Simulation``, ``/foo/bar``, or nothing at all).
_PAGE_PREFIX = r"(?:/[^/]+)*"

# Locate ``create_streamlit_routes`` across Streamlit versions. As of
# 1.55+ it lives in ``streamlit.web.server.starlette.starlette_app``;
# we search candidate locations rather than hard-coding one so a
# Streamlit upgrade that moves it gives a clear "couldn't find it"
# error instead of a silent attribute miss during patch application.
_CANDIDATE_MODULES: tuple[str, ...] = (
    "streamlit.web.server.starlette.starlette_app",
)


def _find_route_builder() -> tuple[Any, str]:
    for module_name in _CANDIDATE_MODULES:
        try:
            mod = importlib.import_module(module_name)
        except ImportError:  # pragma: no cover  # defensive: candidate modules are version-specific
            continue
        if hasattr(mod, "create_streamlit_routes"):
            return mod, module_name
    raise RuntimeError(  # pragma: no cover  # defensive: would only fire after a Streamlit refactor that relocates the function
        f"Streamlit launcher patch FAILED: ``create_streamlit_routes`` "
        f"not found in any of {_CANDIDATE_MODULES}. The Streamlit "
        f"framework may have relocated it; re-audit web/launcher.py."
    )


_OWNER_MODULE, _OWNER_NAME = _find_route_builder()
_ORIG_CREATE_STREAMLIT_ROUTES = _OWNER_MODULE.create_streamlit_routes


def _relax_pattern(pattern: str) -> str:
    """Return ``pattern`` with page-prefix tolerance injected.

    A compiled route regex like ``^/_stcore/health$`` becomes
    ``^(?:/[^/]+)*/_stcore/health$`` so it also accepts a leading
    page-name prefix. Named groups (e.g. the upload route's
    ``session_id``/``file_id``) live after the leading ``/`` and are
    left untouched.
    """
    if pattern.startswith("^/"):
        return "^" + _PAGE_PREFIX + pattern[1:]
    return pattern


def _relax_route(route: BaseRoute) -> None:
    """Relax a single route's ``path_regex`` in place if it is an
    ``_stcore`` endpoint. Non-``_stcore`` routes (page routes, media,
    static assets) are left untouched — those are registered with the
    correct absolute paths and already work for multi-page navigation.
    """
    path = getattr(route, "path", "")
    compiled = getattr(route, "path_regex", None)
    if "_stcore" not in path or not isinstance(compiled, re.Pattern):
        return
    relaxed = _relax_pattern(compiled.pattern)
    if relaxed != compiled.pattern:
        # ``setattr`` (vs. direct assignment) keeps mypy strict happy:
        # ``BaseRoute`` doesn't declare ``path_regex`` on the base class,
        # but the ``isinstance`` guard above proves it exists here.
        setattr(route, "path_regex", re.compile(relaxed))


def _patched_create_streamlit_routes(runtime: Any) -> Sequence[BaseRoute]:
    """Wrap ``create_streamlit_routes`` so every ``_stcore`` route also
    matches a leading page-name prefix.
    """
    routes: Sequence[BaseRoute] = _ORIG_CREATE_STREAMLIT_ROUTES(runtime)
    for route in routes:
        _relax_route(route)
    return routes


# Patch the owning module. ``create_streamlit_routes`` is called by
# same-module helpers (``create_starlette_app`` / ``App._build_starlette_app``)
# via the module global, so rebinding the attribute is sufficient — the
# calls resolve the patched function at server-start time.
_OWNER_MODULE.create_streamlit_routes = _patched_create_streamlit_routes


def _assert_patch_active() -> None:
    """Self-check: confirm the relax logic actually accepts the
    page-prefixed form. Run at startup so a Streamlit refactor that
    changes the route-regex shape produces a clear error rather than a
    silent regression to the 404 behavior we're fixing.

    Built against a synthetic Starlette route so the check needs no
    Streamlit runtime.
    """
    from starlette.routing import Route

    async def _probe(_: Any) -> None: ...  # pragma: no cover  # defensive: probe body never runs; only its route metadata is inspected

    route = Route("/_stcore/health", _probe, methods=["GET"])
    _relax_route(route)
    sample = route.path_regex.pattern
    if not re.match(sample, "/Run_Simulation/_stcore/health"):  # pragma: no cover  # defensive: only fires if a Streamlit refactor changes the route-regex shape
        raise RuntimeError(
            f"Streamlit launcher patch FAILED: regex {sample!r} does "
            f"not accept /Run_Simulation/_stcore/health. The framework "
            f"may have changed the route-regex shape — re-audit "
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


if __name__ == "__main__":  # pragma: no cover  # ui entry point: only runs when launched as a script
    main()
