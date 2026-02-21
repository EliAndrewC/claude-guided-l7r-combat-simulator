"""Tests for web.state persistence module."""

from unittest.mock import MagicMock, patch

import pytest


def _make_cache_resource():
    """Create a cache_resource mock that actually caches the return value."""
    cache = {}

    def cache_resource(func):
        def wrapper(*args, **kwargs):
            if func not in cache:
                cache[func] = func(*args, **kwargs)
            return cache[func]
        return wrapper

    return cache_resource


@pytest.fixture(autouse=True)
def _mock_streamlit():
    """Mock streamlit so tests don't need a running Streamlit server."""
    mock_st = MagicMock()

    # session_state as a real dict so __contains__, __getitem__, __setitem__ work
    session_state = {}

    mock_st.session_state = session_state
    mock_st.cache_resource = _make_cache_resource()

    with patch.dict("sys.modules", {"streamlit": mock_st}):
        # Re-import so the module picks up our mock
        import importlib

        import web.state
        importlib.reload(web.state)
        yield mock_st, session_state


class TestSaveAndRestore:
    """save_state copies session values to store; restore_state copies them back."""

    def test_save_and_restore(self, _mock_streamlit):
        _, session_state = _mock_streamlit
        from web.state import _get_store, restore_state, save_state

        # Populate session state
        session_state["characters"] = {"Akodo": "fighter"}
        session_state["control_group"] = "group_a"
        session_state["test_group"] = "group_b"

        save_state()

        # Verify store has the values
        store = _get_store()
        assert store["characters"] == {"Akodo": "fighter"}
        assert store["control_group"] == "group_a"
        assert store["test_group"] == "group_b"

        # Clear session state, then restore
        session_state.clear()
        restore_state()

        assert session_state["characters"] == {"Akodo": "fighter"}
        assert session_state["control_group"] == "group_a"
        assert session_state["test_group"] == "group_b"


class TestRestoreEmptyStore:
    """restore_state is a no-op when the store is empty."""

    def test_restore_empty_store_is_noop(self, _mock_streamlit):
        _, session_state = _mock_streamlit
        from web.state import _get_store, restore_state

        _get_store().clear()
        session_state.clear()

        restore_state()

        assert "characters" not in session_state
        assert "control_group" not in session_state
        assert "test_group" not in session_state


class TestClearState:
    """clear_state wipes both the persistent store and session state."""

    def test_clear_state(self, _mock_streamlit):
        _, session_state = _mock_streamlit
        from web.state import _get_store, clear_state, save_state

        session_state["characters"] = {"Bayushi": "rogue"}
        session_state["control_group"] = "ctrl"
        session_state["test_group"] = "tst"

        save_state()

        clear_state()

        assert _get_store() == {}
        assert "characters" not in session_state
        assert "control_group" not in session_state
        assert "test_group" not in session_state
