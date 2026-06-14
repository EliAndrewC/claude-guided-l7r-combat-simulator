#!/usr/bin/env python3

#
# test_launcher_patch.py
#
# Verifies that web/launcher.py's patch of Streamlit's route table
# relaxes ``_stcore/*`` endpoints to accept page-name prefixes —
# without this the browser sees 404s on every health-check poll from a
# multi-page navigation context like ``/Run_Simulation/_stcore/health``.
#
# Streamlit 1.55+ serves these endpoints from a Starlette route table,
# so the patch rewrites each ``_stcore`` route's compiled ``path_regex``
# rather than the old Tornado ``make_url_path_regex`` string builder.
#

import re
import sys
import unittest
from unittest import mock

from starlette.routing import Route, WebSocketRoute


async def _probe(_: object) -> None:  # pragma: no cover  # route metadata only; never invoked
    ...


class TestLauncherPatch(unittest.TestCase):
    def test_relax_accepts_page_prefixed_health_endpoint(self) -> None:
        # Import the launcher — applies the patch as a side effect
        # (idempotent; safe to import multiple times across tests).
        import web.launcher as launcher

        route = Route("/_stcore/health", _probe, methods=["GET"])
        launcher._relax_route(route)
        regex = route.path_regex.pattern
        # Canonical path must still match (regression guard).
        self.assertIsNotNone(re.match(regex, "/_stcore/health"))
        # Page-prefixed path must now also match (the fix).
        self.assertIsNotNone(re.match(regex, "/Run_Simulation/_stcore/health"))
        # Deeper prefixes (defensive — Streamlit could nest pages).
        self.assertIsNotNone(re.match(regex, "/foo/bar/_stcore/health"))
        # A different _stcore route must NOT be matched by this regex.
        self.assertIsNone(re.match(regex, "/_stcore/other"))

    def test_relax_preserves_named_groups_on_upload_route(self) -> None:
        import web.launcher as launcher

        route = Route(
            "/_stcore/upload_file/{session_id}/{file_id}", _probe, methods=["PUT"],
        )
        launcher._relax_route(route)
        m = route.path_regex.match(
            "/Characters/_stcore/upload_file/sess123/file456",
        )
        self.assertIsNotNone(m)
        assert m is not None  # narrow for the type checker
        self.assertEqual(m.group("session_id"), "sess123")
        self.assertEqual(m.group("file_id"), "file456")

    def test_relax_handles_websocket_stream_route(self) -> None:
        import web.launcher as launcher

        route = WebSocketRoute("/_stcore/stream", _probe)
        launcher._relax_route(route)
        regex = route.path_regex.pattern
        self.assertIsNotNone(re.match(regex, "/_stcore/stream"))
        self.assertIsNotNone(re.match(regex, "/Run_Simulation/_stcore/stream"))

    def test_relax_leaves_non_stcore_routes_unchanged(self) -> None:
        # The patch is scoped to ``_stcore``-bearing routes; any other
        # route the framework registers should be untouched.
        import web.launcher as launcher

        route = Route("/some/other/route", _probe, methods=["GET"])
        before = route.path_regex.pattern
        launcher._relax_route(route)
        self.assertEqual(route.path_regex.pattern, before)
        # No page-prefix tolerance should have been injected.
        self.assertIsNone(
            re.match(route.path_regex.pattern, "/page/some/other/route"),
        )

    def test_patched_route_builder_relaxes_all_stcore_routes(self) -> None:
        # The wrapper must relax every _stcore route returned by the
        # original builder while leaving the rest alone. Drive it with a
        # fake builder so no Streamlit runtime is required.
        import web.launcher as launcher

        fake_routes = [
            Route("/_stcore/health", _probe, methods=["GET"]),
            Route("/media/{file_id:path}", _probe, methods=["GET"]),
        ]
        orig = launcher._ORIG_CREATE_STREAMLIT_ROUTES
        launcher._ORIG_CREATE_STREAMLIT_ROUTES = lambda _runtime: fake_routes
        try:
            # The wrapper mutates the routes in place and returns them;
            # assert on the concretely-typed originals so mypy keeps the
            # ``Route.path_regex`` attribute in view.
            launcher._patched_create_streamlit_routes(object())
        finally:
            launcher._ORIG_CREATE_STREAMLIT_ROUTES = orig

        health, media = fake_routes
        self.assertIsNotNone(
            re.match(health.path_regex.pattern, "/Run_Simulation/_stcore/health"),
        )
        # Non-_stcore media route is untouched: no page prefix accepted.
        self.assertIsNone(
            re.match(media.path_regex.pattern, "/page/media/x.png"),
        )

    def test_main_invokes_streamlit_cli_with_app_and_flags(self) -> None:
        # main() hands off to Streamlit's CLI; mock the CLI so nothing
        # actually launches, and assert it builds the expected argv
        # (default port/address bindings plus any extra flags passed
        # through to the launcher).
        import streamlit.web.cli as cli

        import web.launcher as launcher

        captured: dict[str, list[str]] = {}

        def _fake_cli() -> None:
            captured["argv"] = list(sys.argv)

        orig_argv = sys.argv
        with mock.patch.object(cli, "main", _fake_cli):
            sys.argv = ["launcher.py", "--server.headless=true"]
            try:
                launcher.main()
            finally:
                sys.argv = orig_argv

        argv = captured["argv"]
        self.assertEqual(argv[:3], ["streamlit", "run", "web/app.py"])
        self.assertIn("--server.port=8501", argv)
        self.assertIn("--server.address=0.0.0.0", argv)
        # Extra launcher args are appended verbatim.
        self.assertIn("--server.headless=true", argv)

    def test_relax_pattern_passthrough_for_unanchored(self) -> None:
        # Pure-string helper: an already-relaxed or non-_stcore-shaped
        # pattern is returned unchanged when it lacks the ``^/`` anchor.
        import web.launcher as launcher

        self.assertEqual(launcher._relax_pattern("no-anchor$"), "no-anchor$")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
