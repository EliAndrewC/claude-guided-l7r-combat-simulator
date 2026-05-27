"""Tests for web.state per-session persistence module."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

# Cookie name must match the constant in web.state.
_COOKIE = "l7r_session_id"


class _CookiesRaising:
    """A cookies stand-in that raises whenever ``.get`` is called.

    Triggers the defensive ``except Exception`` branch in
    ``_get_session_id`` (web/state.py lines 42-43).
    """

    def get(self, _key: str) -> None:
        raise RuntimeError("simulated streamlit cookies failure")


@pytest.fixture(autouse=True)
def _mock_streamlit(tmp_path):
    """Mock streamlit so tests don't need a running Streamlit server."""
    mock_st = MagicMock()

    # session_state as a real dict
    session_state: dict = {}
    mock_st.session_state = session_state

    # context.cookies as a real dict (browser cookies sent on page load)
    cookies: dict = {}
    mock_st.context.cookies = cookies

    with patch.dict("sys.modules", {"streamlit": mock_st}):
        import importlib

        import web.state
        importlib.reload(web.state)
        # Point sessions dir to temp directory
        web.state._SESSIONS_DIR = tmp_path / ".sessions"
        yield mock_st, session_state, cookies


class TestSaveAndRestore:
    """save_state persists groups to disk; restore_state loads them back."""

    def test_save_and_restore(self, _mock_streamlit):
        _, session_state, cookies = _mock_streamlit
        from web.models import GroupConfig
        from web.state import restore_state, save_state

        cookies[_COOKIE] = "test-session-1"
        session_state["control_group"] = GroupConfig(
            name="ctrl", is_control=True, character_names=["A"],
        )
        session_state["test_group"] = GroupConfig(
            name="test", is_control=False, character_names=["B"],
        )

        save_state()

        # Clear session state, then restore (cookie provides session identity)
        session_state.clear()
        restore_state()

        assert isinstance(session_state["control_group"], GroupConfig)
        assert session_state["control_group"].character_names == ["A"]
        assert session_state["test_group"].character_names == ["B"]


class TestRestoreEmptyStore:
    """restore_state is a no-op when no session file exists."""

    def test_restore_no_file_is_noop(self, _mock_streamlit):
        _, session_state, cookies = _mock_streamlit
        from web.state import restore_state

        cookies[_COOKIE] = "nonexistent-session"
        session_state.clear()

        restore_state()

        assert "control_group" not in session_state
        assert "test_group" not in session_state


class TestDiskPersistence:
    """Groups persist to per-session disk files and survive simulated server restarts."""

    def test_groups_survive_session_state_clear(self, _mock_streamlit):
        """After clearing session_state (simulating restart), groups load from disk."""
        _, session_state, cookies = _mock_streamlit
        from web.models import GroupConfig
        from web.state import restore_state, save_state

        cookies[_COOKIE] = "persist-test"
        session_state["control_group"] = GroupConfig(
            name="ctrl", is_control=True, character_names=["A"],
        )
        session_state["test_group"] = GroupConfig(
            name="test", is_control=False, character_names=["B"],
        )
        save_state()

        # Simulate server restart: clear session state entirely
        session_state.clear()

        restore_state()
        assert isinstance(session_state["control_group"], GroupConfig)
        assert session_state["control_group"].character_names == ["A"]
        assert session_state["test_group"].character_names == ["B"]

    def test_validate_clears_stale_groups(self, _mock_streamlit):
        """Groups referencing deleted characters are cleared."""
        _, session_state, _ = _mock_streamlit
        from web.models import GroupConfig
        from web.state import _validate_groups

        session_state["control_group"] = GroupConfig(
            name="ctrl", is_control=True, character_names=["A"],
        )
        session_state["test_group"] = GroupConfig(
            name="test", is_control=False, character_names=["B"],
        )

        # Only "A" exists
        _validate_groups({"A": "a"})
        assert session_state["control_group"] is not None
        assert session_state["test_group"] is None

    def test_validate_keeps_valid_groups(self, _mock_streamlit):
        _, session_state, _ = _mock_streamlit
        from web.models import GroupConfig
        from web.state import _validate_groups

        session_state["control_group"] = GroupConfig(
            name="ctrl", is_control=True, character_names=["A"],
        )
        session_state["test_group"] = GroupConfig(
            name="test", is_control=False, character_names=["B"],
        )

        _validate_groups({"A": "a", "B": "b"})
        assert session_state["control_group"] is not None
        assert session_state["test_group"] is not None


class TestClearState:
    """clear_state wipes session state and removes the session file."""

    def test_clear_state(self, _mock_streamlit):
        _, session_state, cookies = _mock_streamlit
        from web.models import GroupConfig
        from web.state import _session_file, clear_state, save_state

        cookies[_COOKIE] = "clear-test"
        session_state["characters"] = {"Bayushi": "rogue"}
        session_state["control_group"] = GroupConfig(
            name="ctrl", is_control=True, character_names=["Bayushi"],
        )
        session_state["test_group"] = GroupConfig(
            name="test", is_control=False, character_names=["Bayushi"],
        )

        save_state()
        assert _session_file("clear-test").exists()

        clear_state()

        assert "characters" not in session_state
        assert "control_group" not in session_state
        assert "test_group" not in session_state
        assert not _session_file("clear-test").exists()


class TestSessionIsolation:
    """Two different session IDs produce independent state."""

    def test_sessions_are_independent(self, _mock_streamlit):
        _, session_state, cookies = _mock_streamlit
        from web.models import GroupConfig
        from web.state import restore_state, save_state

        # Session A saves its groups
        cookies[_COOKIE] = "session-a"
        session_state["_session_id"] = "session-a"
        session_state["control_group"] = GroupConfig(
            name="A-ctrl", is_control=True, character_names=["A1"],
        )
        session_state["test_group"] = GroupConfig(
            name="A-test", is_control=False, character_names=["A2"],
        )
        save_state()

        # Session B saves different groups
        session_state.clear()
        cookies[_COOKIE] = "session-b"
        session_state["control_group"] = GroupConfig(
            name="B-ctrl", is_control=True, character_names=["B1"],
        )
        session_state["test_group"] = GroupConfig(
            name="B-test", is_control=False, character_names=["B2"],
        )
        save_state()

        # Restore session A — should get A's groups, not B's
        session_state.clear()
        cookies[_COOKIE] = "session-a"
        restore_state()
        assert session_state["control_group"].name == "A-ctrl"
        assert session_state["test_group"].name == "A-test"

        # Restore session B — should get B's groups
        session_state.clear()
        cookies[_COOKIE] = "session-b"
        restore_state()
        assert session_state["control_group"].name == "B-ctrl"
        assert session_state["test_group"].name == "B-test"


class TestCleanupStaleSessions:
    """Old session files are deleted by _cleanup_stale_sessions."""

    def test_stale_files_are_deleted(self, _mock_streamlit):
        _, _, _ = _mock_streamlit
        from web.state import _SESSIONS_DIR, _cleanup_stale_sessions

        _SESSIONS_DIR.mkdir(exist_ok=True)

        # Create a "stale" session file with old mtime
        stale = _SESSIONS_DIR / "old-session.json"
        stale.write_text(json.dumps({"control_group": None, "test_group": None}))
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
        import os
        os.utime(stale, (old_time, old_time))

        # Create a "fresh" session file
        fresh = _SESSIONS_DIR / "new-session.json"
        fresh.write_text(json.dumps({"control_group": None, "test_group": None}))

        _cleanup_stale_sessions()

        assert not stale.exists()
        assert fresh.exists()

    def test_cleanup_handles_missing_dir(self, _mock_streamlit):
        """No error when sessions dir doesn't exist yet."""
        from web.state import _cleanup_stale_sessions

        # _SESSIONS_DIR points to a tmp subdir that doesn't exist yet
        _cleanup_stale_sessions()  # should not raise


class TestSessionIdGeneration:
    """_get_session_id returns a UUID from session_state, cookies, or generates new."""

    def test_creates_new_session_id(self, _mock_streamlit):
        _, session_state, _ = _mock_streamlit
        from web.state import _get_session_id

        sid = _get_session_id()
        assert len(sid) == 32  # uuid4().hex is 32 hex chars
        assert session_state["_session_id"] == sid

    def test_reuses_from_session_state(self, _mock_streamlit):
        _, session_state, _ = _mock_streamlit
        from web.state import _get_session_id

        session_state["_session_id"] = "cached-id"
        assert _get_session_id() == "cached-id"

    def test_reads_from_cookie(self, _mock_streamlit):
        _, session_state, cookies = _mock_streamlit
        from web.state import _get_session_id

        cookies[_COOKIE] = "cookie-id"
        assert _get_session_id() == "cookie-id"
        assert session_state["_session_id"] == "cookie-id"

    def test_session_state_takes_priority_over_cookie(self, _mock_streamlit):
        _, session_state, cookies = _mock_streamlit
        from web.state import _get_session_id

        session_state["_session_id"] = "state-id"
        cookies[_COOKIE] = "cookie-id"
        assert _get_session_id() == "state-id"


class TestCookieBasedPersistence:
    """Session ID persists via browser cookies across page refreshes."""

    def test_refresh_restores_from_cookie(self, _mock_streamlit):
        """Groups survive page refresh: session_state cleared, cookie preserved."""
        _, session_state, cookies = _mock_streamlit
        from web.models import GroupConfig
        from web.state import _get_session_id, restore_state, save_state

        # Initial visit: generate session_id, configure groups
        sid = _get_session_id()
        session_state["control_group"] = GroupConfig(
            name="ctrl", is_control=True, character_names=["A"],
        )
        session_state["test_group"] = GroupConfig(
            name="test", is_control=False, character_names=["B"],
        )
        save_state()

        # Simulate page refresh: session_state cleared, cookie preserved
        session_state.clear()
        cookies[_COOKIE] = sid

        restore_state()
        assert isinstance(session_state.get("control_group"), GroupConfig)
        assert session_state["control_group"].character_names == ["A"]
        assert session_state["test_group"].character_names == ["B"]

    def test_navigation_preserves_session_via_session_state(self, _mock_streamlit):
        """Within a single browser tab, session_state keeps the session alive."""
        _, session_state, _ = _mock_streamlit
        from web.models import GroupConfig
        from web.state import _get_session_id, save_state

        sid = _get_session_id()
        session_state["control_group"] = GroupConfig(
            name="ctrl", is_control=True, character_names=["A"],
        )
        session_state["test_group"] = GroupConfig(
            name="test", is_control=False, character_names=["B"],
        )
        save_state()

        # Navigate to another page: session_state preserved, _session_id intact
        assert _get_session_id() == sid
        assert session_state["control_group"].character_names == ["A"]

    def test_set_session_cookie_injects_script(self, _mock_streamlit):
        """set_session_cookie calls st.html with the session ID in a cookie script."""
        mock_st, session_state, _ = _mock_streamlit
        from web.state import set_session_cookie

        session_state["_session_id"] = "test-sid"
        set_session_cookie()

        mock_st.html.assert_called_once()
        call_args = mock_st.html.call_args
        html_body = call_args[0][0]
        assert "test-sid" in html_body
        assert _COOKIE in html_body
        assert call_args[1]["unsafe_allow_javascript"] is True


class TestDefensiveBranches:
    """Cover the defensive error-handling branches in web/state.py."""

    def test_get_session_id_cookies_raise_generates_new_id(self, _mock_streamlit):
        """When cookies.get raises, _get_session_id falls back and generates
        a new UUID (web/state.py lines 42-43)."""
        mock_st, session_state, _ = _mock_streamlit
        mock_st.context.cookies = _CookiesRaising()
        from web.state import _get_session_id

        sid = _get_session_id()
        assert len(sid) == 32

    def test_cleanup_stale_sessions_swallows_oserror(self, _mock_streamlit, tmp_path):
        """OSError on stat/unlink is swallowed silently (lines 86-87)."""
        import web.state as ws
        from web.state import _cleanup_stale_sessions

        ws._SESSIONS_DIR = tmp_path / "stale-osfail"
        ws._SESSIONS_DIR.mkdir()
        bad = ws._SESSIONS_DIR / "bad.json"
        bad.write_text("{}")

        # Patch unlink to raise OSError; cleanup should swallow.
        # First make sure the file appears stale.
        import os
        old_time = time.time() - (8 * 24 * 60 * 60)
        os.utime(bad, (old_time, old_time))

        from pathlib import Path
        with patch.object(Path, "unlink", side_effect=OSError):
            _cleanup_stale_sessions()  # Should not raise

    def test_validate_groups_handles_missing_group(self, _mock_streamlit):
        """If a group is None, _validate_groups skips it (line 95)."""
        _, session_state, _ = _mock_streamlit
        from web.state import _validate_groups

        # Neither group set → both skipped (the "group is None" branch)
        session_state["control_group"] = None
        session_state["test_group"] = None
        _validate_groups({})  # Should not crash
        assert session_state["control_group"] is None
        assert session_state["test_group"] is None

    def test_save_state_with_none_group_writes_null(self, _mock_streamlit, tmp_path):
        """When a group is missing/non-GroupConfig, data[key] = None (line 108)."""
        _, session_state, cookies = _mock_streamlit
        from web.state import _session_file, save_state

        cookies[_COOKIE] = "none-grp-test"
        session_state["control_group"] = None
        session_state["test_group"] = None
        save_state()

        path = _session_file("none-grp-test")
        data = json.loads(path.read_text())
        assert data["control_group"] is None
        assert data["test_group"] is None

    def test_save_state_swallows_oserror(self, _mock_streamlit, tmp_path):
        """OSError on write is swallowed silently (lines 112-113)."""
        _, session_state, cookies = _mock_streamlit
        from pathlib import Path

        from web.state import save_state
        cookies[_COOKIE] = "save-osfail"
        session_state["control_group"] = None
        session_state["test_group"] = None

        # Make _session_file return a path that will fail to write
        with patch.object(Path, "write_text", side_effect=OSError):
            save_state()  # should not raise

    def test_restore_state_returns_when_both_keys_present(self, _mock_streamlit, tmp_path):
        """When both control_group and test_group already in session_state,
        restore_state returns early (line 123)."""
        _, session_state, cookies = _mock_streamlit
        from web.models import GroupConfig
        from web.state import restore_state

        cookies[_COOKIE] = "no-need-restore"
        session_state["control_group"] = GroupConfig(
            name="x", is_control=True, character_names=["A"],
        )
        session_state["test_group"] = GroupConfig(
            name="y", is_control=False, character_names=["B"],
        )
        restore_state()  # early return; should not modify state
        assert session_state["control_group"].name == "x"
        assert session_state["test_group"].name == "y"

    def test_restore_state_handles_corrupt_json(self, _mock_streamlit, tmp_path):
        """When the session file is corrupt JSON, restore_state silently
        returns (lines 128-129)."""
        _, session_state, cookies = _mock_streamlit
        import web.state as ws
        from web.state import _session_file, restore_state

        ws._SESSIONS_DIR = tmp_path / "corrupt-json"
        ws._SESSIONS_DIR.mkdir()
        cookies[_COOKIE] = "corrupt-sess"
        path = _session_file("corrupt-sess")
        path.write_text("{ this is not valid json ")
        session_state.clear()
        cookies[_COOKIE] = "corrupt-sess"

        restore_state()
        # Should NOT have set control_group / test_group since JSON was bad
        assert "control_group" not in session_state
        assert "test_group" not in session_state

    def test_restore_state_sets_none_for_missing_key_in_file(self, _mock_streamlit, tmp_path):
        """When a key is present in the file but value is None, the session
        state key becomes None (line 136)."""
        _, session_state, cookies = _mock_streamlit
        import web.state as ws
        from web.state import _session_file, restore_state

        ws._SESSIONS_DIR = tmp_path / "missing-key"
        ws._SESSIONS_DIR.mkdir()
        cookies[_COOKIE] = "missing-key-sess"
        path = _session_file("missing-key-sess")
        # data has both keys, but their values are None
        path.write_text(json.dumps({"control_group": None, "test_group": None}))
        session_state.clear()
        cookies[_COOKIE] = "missing-key-sess"

        restore_state()
        assert session_state["control_group"] is None
        assert session_state["test_group"] is None

    def test_clear_state_swallows_oserror_on_unlink(self, _mock_streamlit, tmp_path):
        """OSError on unlink is swallowed silently (lines 143-144)."""
        _, session_state, cookies = _mock_streamlit
        from pathlib import Path

        from web.state import clear_state
        cookies[_COOKIE] = "clear-osfail"

        with patch.object(Path, "unlink", side_effect=OSError):
            clear_state()  # should not raise
