#!/usr/bin/env python3

#
# test_launcher_patch.py
#
# Verifies that web/launcher.py's monkey-patch of Streamlit's
# ``make_url_path_regex`` actually accepts page-name prefixes on
# ``_stcore/*`` endpoints — without this the browser sees 404s on
# every health-check poll from a multi-page navigation context like
# ``/Run_Simulation/_stcore/health``.
#

import re
import unittest


class TestLauncherPatch(unittest.TestCase):
    def test_patch_accepts_page_prefixed_health_endpoint(self) -> None:
        # Import the launcher — applies the patch as a side effect
        # (idempotent; safe to import multiple times across tests).
        import web.launcher as launcher

        regex = launcher._OWNER_MODULE.make_url_path_regex("", "_stcore/health")
        # Canonical path must still match (regression guard).
        self.assertIsNotNone(re.match(regex, "/_stcore/health"))
        # Page-prefixed path must now also match (the fix).
        self.assertIsNotNone(re.match(regex, "/Run_Simulation/_stcore/health"))
        # Deeper prefixes (defensive — Streamlit could nest pages).
        self.assertIsNotNone(re.match(regex, "/foo/bar/_stcore/health"))

    def test_patch_accepts_page_prefixed_host_config(self) -> None:
        import web.launcher as launcher

        regex = launcher._OWNER_MODULE.make_url_path_regex("", "_stcore/host-config")
        self.assertIsNotNone(re.match(regex, "/_stcore/host-config"))
        self.assertIsNotNone(re.match(regex, "/Characters/_stcore/host-config"))

    def test_patch_leaves_non_stcore_routes_unchanged(self) -> None:
        # The patch is scoped to ``_stcore``-bearing patterns; any
        # other route the framework registers should be untouched.
        import web.launcher as launcher

        unrelated = launcher._OWNER_MODULE.make_url_path_regex(
            "base", "some/other/route",
        )
        # Original behavior: ``^/base/some/other/route/?$``. No
        # page-prefix tolerance should have been injected.
        self.assertEqual(unrelated, "^/base/some/other/route/?$")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
