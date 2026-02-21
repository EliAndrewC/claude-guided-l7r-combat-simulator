"""Persistent state management for the Streamlit web interface.

Uses @st.cache_resource to maintain state across browser refreshes,
persisting as long as the Streamlit server process is alive.
"""

import streamlit as st


@st.cache_resource
def _get_store() -> dict:
    """Return a mutable dict that survives browser refreshes."""
    return {}


def save_state() -> None:
    """Copy characters, control_group, and test_group from session_state into the persistent store."""
    store = _get_store()
    for key in ("characters", "control_group", "test_group"):
        if key in st.session_state:
            store[key] = st.session_state[key]


def restore_state() -> None:
    """Copy stored values back into session_state if they exist."""
    store = _get_store()
    for key in ("characters", "control_group", "test_group"):
        if key in store:
            st.session_state[key] = store[key]


def clear_state() -> None:
    """Clear the persistent store and remove keys from session_state."""
    store = _get_store()
    store.clear()
    for key in ("characters", "control_group", "test_group"):
        if key in st.session_state:
            del st.session_state[key]
