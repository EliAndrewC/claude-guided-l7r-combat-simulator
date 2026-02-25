"""Tests for web.state per-session persistence module."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

# Cookie name must match the constant in web.state.
_COOKIE = "l7r_session_id"


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
